"""
Test Langfuse trace creation directly.
Run from D:\beacon\backend with venv active.
"""
import asyncio
from beacon.core.settings import get_settings
from beacon.integrations.langfuse_client import get_langfuse_client

def test():
    settings = get_settings()
    print("host:", settings.langfuse_host)
    print("public key:", settings.langfuse_public_key[:10] + "...")
    
    lf = get_langfuse_client()
    print("enabled:", lf._enabled)
    
    if not lf._enabled:
        print("ERROR: Langfuse not enabled")
        return

    client = lf._client

    # Test 1: auth check
    try:
        client.auth_check()
        print("auth: OK")
    except Exception as e:
        print("auth FAILED:", e)
        return

    # Test 2: create a trace with a generation
    try:
        trace_id = client.create_trace_id(seed="beacon-test-123")
        print("trace_id:", trace_id)

        obs = client.start_observation(
            name="test_generation",
            as_type="generation",
            model="claude-sonnet-4-5",
            input=[{"role": "user", "content": "Hello test"}],
            output="Hello back",
            model_parameters={"temperature": 0.0, "max_tokens": 100},
            usage_details={"input": 10, "output": 5},
            cost_details={"total": 0.0001},
            trace_context={"trace_id": trace_id},
        )
        obs.end()
        print("observation created OK")

        # Test 3: score it
        client.create_score(
            trace_id=trace_id,
            name="test_score",
            value=0.95,
            data_type="NUMERIC",
            comment="test from beacon",
        )
        print("score created OK")

        # Flush
        client.flush()
        print("flushed OK")

        trace_url = client.get_trace_url(trace_id=trace_id)
        print("trace URL:", trace_url)
        print("\nCheck Langfuse — trace should appear within 10 seconds")

    except Exception as e:
        import traceback
        print("FAILED:", e)
        traceback.print_exc()

test()
