"""
Anthropic client wrapper.
Handles retries, structured-output parsing, cost accounting, and logging.
All LLM calls in Beacon go through this module — never call the SDK directly.
"""
import json
import re
from typing import Any

import anthropic
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from beacon.core.settings import get_settings

logger = structlog.get_logger(__name__)

# Cost per million tokens (USD) — update when Anthropic changes pricing
_COST_PER_M_INPUT = {
    "claude-sonnet-4-5": 3.00,
    "claude-opus-4-5": 15.00,
}
_COST_PER_M_OUTPUT = {
    "claude-sonnet-4-5": 15.00,
    "claude-opus-4-5": 75.00,
}


def _compute_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    input_rate = _COST_PER_M_INPUT.get(model_id, 3.00)
    output_rate = _COST_PER_M_OUTPUT.get(model_id, 15.00)
    return (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate


def _extract_json(text: str) -> dict:
    """Extract JSON from model output, tolerating markdown fences."""
    text = text.strip()
    # Strip ```json ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


class AnthropicClient:
    """Singleton-style wrapper around the Anthropic SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            max_retries=0,  # We handle retries with tenacity
        )
        self._default_model = settings.anthropic_default_model
        self._safety_model = settings.anthropic_safety_model

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIStatusError)),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send a completion request and return a dict with:
        - text: str
        - input_tokens: int
        - output_tokens: int
        - cost_usd: float
        - model: str
        """
        model_id = model or self._default_model
        settings = get_settings()

        if not settings.anthropic_api_key:
            logger.warning("anthropic_key_missing_returning_mock")
            return {
                "text": '{"score": 0.8, "passed": true, "reasoning": "Mock response — no API key configured"}',
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "model": model_id,
            }

        kwargs: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        logger.debug(
            "anthropic_request",
            model=model_id,
            message_count=len(messages),
            max_tokens=max_tokens,
        )

        response = await self._client.messages.create(**kwargs)

        text = response.content[0].text if response.content else ""
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = _compute_cost(model_id, input_tokens, output_tokens)

        logger.debug(
            "anthropic_response",
            model=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 6),
        )

        return {
            "text": text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "model": model_id,
        }

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """
        Like complete() but parses the response as JSON.
        Returns the same dict with an extra 'parsed' key containing the JSON object.
        Retries once on JSON parse failure.
        """
        result = await self.complete(
            messages=messages,
            system=system,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        try:
            result["parsed"] = _extract_json(result["text"])
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("structured_output_parse_failed", text=result["text"][:200])
            # One retry with an explicit correction prompt
            messages_with_correction = messages + [
                {"role": "assistant", "content": result["text"]},
                {
                    "role": "user",
                    "content": "Your response was not valid JSON. Please respond with only a valid JSON object, no markdown fences.",
                },
            ]
            result = await self.complete(
                messages=messages_with_correction,
                system=system,
                model=model,
                max_tokens=max_tokens,
                temperature=0.0,
            )
            result["parsed"] = _extract_json(result["text"])
        return result

    async def call_agent(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        tool_definitions: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Call a student agent under test. Returns same shape as complete()."""
        messages = [{"role": "user", "content": user_message}]
        return await self.complete(
            messages=messages,
            system=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )


# Module-level singleton
_client: AnthropicClient | None = None


def get_anthropic_client() -> AnthropicClient:
    global _client
    if _client is None:
        _client = AnthropicClient()
    return _client
