"""
Anthropic client — AWS Bedrock via boto3 Converse API.

Uses AWS Bedrock API key (bearer token) authentication.
Set AWS_BEARER_TOKEN_BEDROCK env var with the key.

Required env vars:
    AWS_BEARER_TOKEN_BEDROCK   short or long-term Bedrock API key
    AWS_REGION                 (default: us-east-1)
    BEDROCK_MODEL_ID           (default: us.anthropic.claude-sonnet-4-6)
"""

import logging
import os
from typing import Any

import boto3

from beacon.core.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def _make_client():
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = settings.bedrock_api_key
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


_client = None


def get_client():
    global _client
    if _client is None:
        _client = _make_client()
    return _client


def estimate_cost(input_tokens: int, output_tokens: int, model: str | None = None) -> float:
    """Rough USD cost estimate. Treat as approximation for dashboard display."""
    resolved_model = model or settings.bedrock_model_id

    pricing = {
        "us.anthropic.claude-sonnet-4-6": (3.00, 15.00),
        "us.anthropic.claude-3-5-haiku-20241022-v1:0": (0.80, 4.00),
        "us.anthropic.claude-3-5-sonnet-20241022-v2:0": (3.00, 15.00),
    }

    input_price, output_price = pricing.get(resolved_model, (3.00, 15.00))
    return (input_tokens / 1_000_000 * input_price) + (output_tokens / 1_000_000 * output_price)


async def call_agent(
    *,
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Call the agent via Bedrock Converse API. Returns text, cost, token counts.

    conversation_history: list of {"role": "user"|"assistant", "content": "..."}
    representing prior turns. The current user_message is appended automatically.
    """
    import asyncio
    resolved_model = model or settings.bedrock_model_id

    # Build full message list: history + current message
    messages = []
    for turn in (conversation_history or []):
        messages.append({
            "role": turn["role"],
            "content": [{"text": turn["content"]}],
        })
    messages.append({"role": "user", "content": [{"text": user_message}]})

    # boto3 is sync — run in executor to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: get_client().converse(
            modelId=resolved_model,
            system=[{"text": system_prompt}],
            messages=messages,
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        )
    )

    text = response["output"]["message"]["content"][0]["text"]
    input_tokens = response["usage"]["inputTokens"]
    output_tokens = response["usage"]["outputTokens"]

    logger.debug("bedrock_agent_call", extra={
        "model": resolved_model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    })

    return {
        "text": text,
        "cost_usd": estimate_cost(input_tokens, output_tokens, resolved_model),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }

async def complete(
    *,
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> dict:
    """Single-turn completion. Returns dict with text and usage."""
    return await call_agent(
        system_prompt=system or "You are a helpful assistant.",
        user_message=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )


async def complete_structured(
    *,
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Returns just the text string. Used by judges."""
    result = await complete(
        prompt=prompt,
        system=system,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        metadata=metadata,
    )
    return result["text"]

