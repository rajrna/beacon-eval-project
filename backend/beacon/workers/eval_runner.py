"""
Eval Runner Worker.
Picked up by RQ workers. Executes one EvalRun end-to-end:
  1. Load dataset examples in batches
  2. For each example: call agent -> call judges concurrently
  3. Write EvalResult rows to Postgres + scores to Langfuse
  4. Compute aggregates and update EvalRun
  5. Fire Teams webhook if pass rate below threshold
"""
import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from beacon.core.settings import get_settings

logger = structlog.get_logger(__name__)


def run_eval_job(run_id: str) -> None:
    """Synchronous RQ job entrypoint."""
    asyncio.run(_run_eval_async(run_id))


def enqueue_eval_run(run_id: str):
    """Enqueue an eval run to RQ. Returns the RQ job."""
    from redis import Redis
    from rq import Queue

    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url_str)
    q = Queue("beacon-eval", connection=redis_conn)
    job = q.enqueue(run_eval_job, run_id, job_timeout=600)
    logger.info("eval_run_enqueued", run_id=run_id, job_id=job.id)
    return job


async def _run_eval_async(run_id: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url_str, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        try:
            await _execute_run(session, uuid.UUID(run_id))
        except Exception as exc:
            logger.exception("eval_run_crashed", run_id=run_id, error=str(exc))
            await _mark_run_failed(session, uuid.UUID(run_id), str(exc))
        finally:
            await session.close()
    await engine.dispose()


async def _execute_run(session: AsyncSession, run_id: uuid.UUID) -> None:
    from sqlalchemy import select
    from beacon.models.eval import EvalResult, EvalRun
    from beacon.models.agent import AgentVersion
    from beacon.models.judge import Judge, JudgeVersion
    from beacon.repositories.eval import EvalRunRepository
    from beacon.repositories.dataset import ExampleRepository
    from beacon.judges import get_judge
    from beacon.integrations.anthropic_client import get_anthropic_client
    from beacon.integrations.langfuse_client import get_langfuse_client

    settings = get_settings()
    run_repo = EvalRunRepository(session)
    example_repo = ExampleRepository(session)
    langfuse = get_langfuse_client()
    client = get_anthropic_client()

    run = await run_repo.get_by_id(run_id)
    if not run:
        raise ValueError(f"EvalRun {run_id} not found")

    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    await session.flush()

    langfuse_run_id = langfuse.create_run(
        dataset_name=str(run.dataset_id),
        run_name=str(run_id),
        metadata={"agent_version_id": str(run.agent_version_id)},
    )
    if langfuse_run_id:
        run.langfuse_run_id = langfuse_run_id
        await session.flush()

    av_result = await session.execute(
        select(AgentVersion).where(AgentVersion.id == run.agent_version_id)
    )
    agent_version = av_result.scalar_one_or_none()
    if not agent_version:
        raise ValueError(f"AgentVersion {run.agent_version_id} not found")

    examples, _ = await example_repo.list_by_dataset(run.dataset_id, limit=1000, offset=0)

    judges = []
    for jv_id_str in run.judge_version_ids:
        try:
            jv_result = await session.execute(
                select(JudgeVersion).where(JudgeVersion.id == uuid.UUID(jv_id_str))
            )
            jv = jv_result.scalar_one_or_none()
            if jv:
                j_result = await session.execute(
                    select(Judge).where(Judge.id == jv.judge_id)
                )
                j = j_result.scalar_one_or_none()
                if j:
                    judge = get_judge(j.slug)
                    judge.pass_threshold = jv.pass_threshold
                    judges.append(judge)
        except Exception as exc:
            logger.warning("judge_load_failed", jv_id=jv_id_str, error=str(exc))

    batch_size = settings.eval_batch_size
    total_cost = 0.0
    total_latency = 0
    passed_count = 0
    error_count = 0
    all_judge_scores: dict[str, list[float]] = {j.slug: [] for j in judges}

    run.total_examples = len(examples)
    await session.flush()

    for i in range(0, len(examples), batch_size):
        batch = examples[i: i + batch_size]
        results = await asyncio.gather(
            *[_evaluate_example(session, run, ex, agent_version, judges, client, langfuse) for ex in batch],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                error_count += 1
                continue
            if result:
                total_cost += result.cost_usd or 0.0
                total_latency += result.latency_ms or 0
                if result.passed:
                    passed_count += 1
                for j in judges:
                    if result.judge_scores and j.slug in result.judge_scores:
                        all_judge_scores[j.slug].append(result.judge_scores[j.slug].get("score", 0))
        await session.flush()

    total_evaluated = len(examples) - error_count
    pass_rate = passed_count / total_evaluated if total_evaluated > 0 else 0.0
    aggregate_scores = {
        slug: sum(scores) / len(scores) if scores else 0.0
        for slug, scores in all_judge_scores.items()
    }

    run.passed_examples = passed_count
    run.pass_rate = pass_rate
    run.aggregate_scores = aggregate_scores
    run.total_cost_usd = total_cost
    run.total_latency_ms = total_latency
    run.status = "partial" if error_count > 0 else "succeeded"
    run.completed_at = datetime.now(timezone.utc)
    await session.flush()
    await session.commit()

    logger.info("eval_run_complete", run_id=str(run_id), status=run.status, pass_rate=round(pass_rate, 3))
    langfuse.flush()

    if pass_rate < settings.eval_pass_rate_threshold and settings.teams_default_webhook_url:
        from beacon.integrations.teams_webhook import send_teams_alert
        await send_teams_alert(
            webhook_url=settings.teams_default_webhook_url,
            title="Eval Run Below Pass Threshold",
            message=f"Pass rate {pass_rate:.1%} is below {settings.eval_pass_rate_threshold:.1%}.",
            severity="warning",
            facts=[
                {"title": "Run ID", "value": str(run_id)},
                {"title": "Pass Rate", "value": f"{pass_rate:.1%}"},
                {"title": "Examples", "value": str(len(examples))},
            ],
        )


async def _evaluate_example(session, run, example, agent_version, judges, client, langfuse):
    import time
    from beacon.models.eval import EvalResult

    start = time.monotonic()
    try:
        agent_result = await client.call_agent(
            system_prompt=agent_version.system_prompt,
            user_message=example.query,
            model=agent_version.model_id,
            max_tokens=agent_version.max_tokens,
            temperature=agent_version.temperature,
        )
        agent_response = agent_result["text"]
        agent_cost = agent_result["cost_usd"]
        input_tokens = agent_result["input_tokens"]
        output_tokens = agent_result["output_tokens"]
    except Exception as exc:
        result = EvalResult(eval_run_id=run.id, example_id=example.id, error_message=str(exc))
        session.add(result)
        return result

    judge_results = await asyncio.gather(
        *[j.evaluate(
            query=example.query,
            agent_response=agent_response,
            expected_behaviors=list(example.expected_behaviors or []),
            prohibited_behaviors=list(example.prohibited_behaviors or []),
            persona=example.persona,
            reference_answer=example.reference_answer,
        ) for j in judges],
        return_exceptions=True,
    )

    judge_scores: dict = {}
    safety_flags: list[str] = []
    judge_cost = 0.0
    all_passed = True

    for judge, jr in zip(judges, judge_results):
        if isinstance(jr, Exception):
            judge_scores[judge.slug] = {"score": 0.0, "passed": False, "error": str(jr)}
            all_passed = False
        else:
            judge_scores[judge.slug] = {"score": jr.score, "passed": jr.passed, "reasoning": jr.reasoning, "flags": jr.flags}
            judge_cost += jr.cost_usd
            if not jr.passed:
                all_passed = False
            if jr.flags:
                safety_flags.extend(jr.flags)
            if run.langfuse_run_id:
                langfuse.score(trace_id=run.langfuse_run_id, name=judge.slug, value=jr.score, comment=jr.reasoning[:500] if jr.reasoning else None)

    latency_ms = int((time.monotonic() - start) * 1000)
    result = EvalResult(
        eval_run_id=run.id,
        example_id=example.id,
        agent_response=agent_response,
        judge_scores=judge_scores,
        safety_flags=safety_flags,
        passed=all_passed,
        latency_ms=latency_ms,
        cost_usd=agent_cost + judge_cost,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    session.add(result)
    return result


async def _mark_run_failed(session: AsyncSession, run_id: uuid.UUID, error: str) -> None:
    from beacon.repositories.eval import EvalRunRepository
    repo = EvalRunRepository(session)
    run = await repo.get_by_id(run_id)
    if run:
        run.status = "failed"
        run.error_message = error[:1000]
        run.completed_at = datetime.now(timezone.utc)
        await session.flush()
        await session.commit()
