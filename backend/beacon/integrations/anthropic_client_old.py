"""
Anthropic client wrapper.
Handles retries, structured-output parsing, cost accounting, and Langfuse instrumentation.
All LLM calls in Beacon go through this module.
"""
import json
import re
from typing import Any

import anthropic
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from beacon.core.settings import get_settings

logger = structlog.get_logger(__name__)

_COST_PER_M_INPUT = {
    "claude-sonnet-4-5": 3.00,
    "claude-opus-4-5": 15.00,
    "claude-sonnet-4-6": 3.00,
}
_COST_PER_M_OUTPUT = {
    "claude-sonnet-4-5": 15.00,
    "claude-opus-4-5": 75.00,
    "claude-sonnet-4-6": 15.00,
}


def _compute_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    input_rate = _COST_PER_M_INPUT.get(model_id, 3.00)
    output_rate = _COST_PER_M_OUTPUT.get(model_id, 15.00)
    return (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _get_langfuse_observe():
    """Lazily import observe to avoid hard dependency."""
    try:
        from langfuse import observe
        return observe
    except ImportError:
        return None


class AnthropicClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            max_retries=0,
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
        observation_name: str = "llm_call",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        model_id = model or self._default_model
        settings = get_settings()

        if not settings.anthropic_api_key:
            logger.warning("anthropic_key_missing_returning_mock")
            return {
                "text": '{"score": 0.8, "passed": true, "reasoning": "Mock response — no API key configured"}',
                "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "model": model_id,
            }

        kwargs: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        # Try to use Langfuse instrumentation
        lf_client = None
        trace_id = None
        try:
            from beacon.integrations.langfuse_client import get_langfuse_client
            lf = get_langfuse_client()
            if lf._enabled and lf._client:
                lf_client = lf._client
                trace_id = lf._client.create_trace_id()
        except Exception:
            pass

        # Start Langfuse generation observation if available
        obs = None
        if lf_client and trace_id:
            try:
                obs = lf_client.start_observation(
                    name=observation_name,
                    as_type="generation",
                    model=model_id,
                    model_parameters={"temperature": temperature, "max_tokens": max_tokens},
                    input=messages,
                    metadata=metadata or {},
                    trace_context={"trace_id": trace_id},
                )
            except Exception:
                obs = None

        logger.debug("anthropic_request", model=model_id, message_count=len(messages))
        response = await self._client.messages.create(**kwargs)

        text = response.content[0].text if response.content else ""
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = _compute_cost(model_id, input_tokens, output_tokens)

        logger.debug("anthropic_response", model=model_id, input_tokens=input_tokens,
                     output_tokens=output_tokens, cost_usd=round(cost, 6))

        # End Langfuse observation with output and cost
        if obs:
            try:
                obs.update(
                    output=text,
                    usage_details={"input": input_tokens, "output": output_tokens},
                    cost_details={"total": cost},
                )
                obs.end()
            except Exception:
                pass

        return {
            "text": text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "model": model_id,
            "langfuse_trace_id": trace_id,
        }

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        observation_name: str = "judge_call",
    ) -> dict[str, Any]:
        result = await self.complete(
            messages=messages, system=system, model=model,
            max_tokens=max_tokens, temperature=temperature,
            observation_name=observation_name,
        )
        try:
            result["parsed"] = _extract_json(result["text"])
        except (json.JSONDecodeError, ValueError):
            logger.warning("structured_output_parse_failed", text=result["text"][:200])
            messages_with_correction = messages + [
                {"role": "assistant", "content": result["text"]},
                {"role": "user", "content": "Your response was not valid JSON. Please respond with only a valid JSON object, no markdown fences."},
            ]
            result = await self.complete(
                messages=messages_with_correction, system=system, model=model,
                max_tokens=max_tokens, temperature=0.0,
                observation_name=observation_name,
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
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        messages = [{"role": "user", "content": user_message}]
        return await self.complete(
            messages=messages, system=system_prompt, model=model,
            max_tokens=max_tokens, temperature=temperature,
            observation_name="agent_call",
            metadata=metadata or {},
        )


_client: AnthropicClient | None = None


def get_anthropic_client() -> AnthropicClient:
    global _client
    if _client is None:
        _client = AnthropicClient()
    return _client
