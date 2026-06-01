"""
Test Langfuse observation creation inside async context (mimics eval runner).
Run from D:\beacon\backend with venv active.
"""
import asyncio
from beacon.integrations.langfuse_client import get_langfuse_client

async def test_async():
    lf = get_langfuse_client()
    if not lf._enabled:
        print("Langfuse not enabled")
        return

    client = lf._client

    # Mimic exactly what anthropic_client.py does
    try:
        trace_id = client.create_trace_id(seed="async-test-456")
        print("trace_id created:", trace_id)

        obs = client.start_observation(
            name="agent_call",
            as_type="generation",
            model="claude-sonnet-4-5",
            model_parameters={"temperature": 0.0, "max_tokens": 1024},
            input=[{"role": "user", "content": "Test query"}],
            metadata={},
            trace_context={"trace_id": trace_id},
        )
        print("observation created:", type(obs).__name__)

        obs.end(
            output="Test response",
            usage_details={"input": 100, "output": 50},
            cost_details={"total": 0.002},
        )
        print("observation ended OK")

        client.create_score(
            trace_id=trace_id,
            name="accuracy",
            value=0.9,
            data_type="NUMERIC",
            comment="async test score",
        )
        print("score created OK")

        client.flush()
        print("flushed OK")
        print("\nCheck Langfuse for trace:", trace_id)

    except Exception as e:
        import traceback
        print("FAILED:", e)
        traceback.print_exc()

asyncio.run(test_async())
