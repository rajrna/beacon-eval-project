"""
Embeddings client — AWS Bedrock Titan Embed v2.

Uses the same bearer token auth as the Converse API.
Titan Embed v2 produces 1536-dimensional vectors.

Usage:
    from beacon.integrations.embeddings_client import embed_text, embed_texts
    vector = await embed_text("What is the tuition?")
    vectors = await embed_texts(["text1", "text2"])
"""
import asyncio
import json
import logging
import os
from typing import Any

import boto3

from beacon.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMS = 1024


def _make_embeddings_client():
    if settings.aws_bearer_token_bedrock:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = settings.aws_bearer_token_bedrock
    session = boto3.Session()
    return session.client("bedrock-runtime", region_name=settings.aws_region)


def _embed_sync(client, text: str) -> list[float]:
    """Synchronous embedding call — runs in executor."""
    response = client.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=json.dumps({
            "inputText": text,
        }),
        contentType="application/json",
        accept="application/json",
    )
    body = json.loads(response["body"].read())
    return body["embedding"]


async def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns a 1536-dim vector."""
    client = _make_embeddings_client()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _embed_sync, client, text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts concurrently."""
    tasks = [embed_text(t) for t in texts]
    return await asyncio.gather(*tasks)
