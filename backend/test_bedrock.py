"""
Direct Bedrock test — bypasses all Beacon code.
Run from D:\beacon\backend with venv activated.
"""
import asyncio
import os
import sys

async def test():
    from beacon.core.settings import get_settings
    settings = get_settings()

    print(f"Region: {settings.aws_region}")
    print(f"Model: {settings.bedrock_model_id}")
    print(f"Bearer token set: {bool(settings.aws_bearer_token_bedrock)}")
    print(f"Bearer token prefix: {settings.aws_bearer_token_bedrock[:10]}...")
    print()

    # Set the env var explicitly
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = settings.aws_bearer_token_bedrock

    import boto3
    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    print(f"Testing model: {settings.bedrock_model_id}")
    try:
        response = client.converse(
            modelId=settings.bedrock_model_id,
            system=[{"text": "You are a helpful assistant."}],
            messages=[{"role": "user", "content": [{"text": "Say hello in one word."}]}],
            inferenceConfig={"maxTokens": 50, "temperature": 0.0},
        )
        print(f"✅ SUCCESS: {response['output']['message']['content'][0]['text']}")
        print(f"   Tokens: {response['usage']}")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")

    # Also try fallback models
    fallback_models = [
        "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        "us.anthropic.claude-sonnet-4-5-20251001-v1:0",
        "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    ]

    if settings.bedrock_model_id not in fallback_models:
        print("\nTrying fallback models...")
        for model in fallback_models:
            try:
                response = client.converse(
                    modelId=model,
                    messages=[{"role": "user", "content": [{"text": "Say hello."}]}],
                    inferenceConfig={"maxTokens": 50},
                )
                print(f"✅ WORKS: {model}")
                print(f"   → Update BEDROCK_MODEL_ID to this value")
                break
            except Exception as e:
                print(f"❌ {model}: {str(e)[:80]}")

asyncio.run(test())