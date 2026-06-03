"""
Agent Version Comparison endpoint.
GET /v1/agents/:id/compare?version_a=:id&version_b=:id&dataset_id=:id

Returns both versions' aggregate scores side by side across the same dataset.
Finds the most recent succeeded run for each version against the dataset.
"""
import uuid
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from beacon.core.database import DbSession
from beacon.auth.dependencies import CurrentUser

router = APIRouter()


class JudgeComparison(BaseModel):
    judge_slug: str
    score_a: float | None
    score_b: float | None
    delta: float | None          # score_b - score_a (positive = B improved)
    winner: str | None           # "a", "b", or "tie"


class VersionComparisonResult(BaseModel):
    agent_id: str
    agent_name: str

    version_a_id: str
    version_a_number: int
    version_a_run_id: str | None
    version_a_pass_rate: float | None
    version_a_cost: float | None
    version_a_latency_ms: int | None
    version_a_total_examples: int | None

    version_b_id: str
    version_b_number: int
    version_b_run_id: str | None
    version_b_pass_rate: float | None
    version_b_cost: float | None
    version_b_latency_ms: int | None
    version_b_total_examples: int | None

    dataset_id: str
    dataset_name: str

    pass_rate_delta: float | None    # version_b - version_a
    overall_winner: str | None       # "a", "b", "tie", or None if no data

    judge_comparisons: list[JudgeComparison]

    # Per-example breakdown
    examples_a_better: int           # examples where A scored higher overall
    examples_b_better: int           # examples where B scored higher overall
    examples_tied: int


@router.get("/compare", response_model=VersionComparisonResult)
async def compare_versions(
    id: str,
    session: DbSession,
    current_user: CurrentUser,
    version_a: str = Query(..., description="Agent version ID for version A"),
    version_b: str = Query(..., description="Agent version ID for version B"),
    dataset_id: str | None = Query(default=None, description="Dataset ID to compare on. Uses most recent shared dataset if not specified."),
) -> VersionComparisonResult:
    from sqlalchemy import text

    # ── Load agent ────────────────────────────────────────────────────────────
    agent_result = await session.execute(text(
        "SELECT id, name FROM agents WHERE id = :id"
    ), {"id": id})
    agent_row = agent_result.fetchone()
    if not agent_row:
        raise HTTPException(status_code=404, detail="Agent not found")

    # ── Load versions ─────────────────────────────────────────────────────────
    versions_result = await session.execute(text("""
        SELECT id, version_number FROM agent_versions
        WHERE id = ANY(:ids) AND agent_id = :agent_id
    """), {"ids": [version_a, version_b], "agent_id": id})
    versions = {str(row[0]): row[1] for row in versions_result.fetchall()}

    if version_a not in versions:
        raise HTTPException(status_code=404, detail=f"Version A ({version_a}) not found for this agent")
    if version_b not in versions:
        raise HTTPException(status_code=404, detail=f"Version B ({version_b}) not found for this agent")

    # ── Find dataset ──────────────────────────────────────────────────────────
    if dataset_id:
        ds_result = await session.execute(text(
            "SELECT id, name FROM datasets WHERE id = :id"
        ), {"id": dataset_id})
        ds_row = ds_result.fetchone()
        if not ds_row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        ds_id = str(ds_row[0])
        ds_name = ds_row[1]
    else:
        # Find the most recent dataset used by both versions
        shared_result = await session.execute(text("""
            SELECT er.dataset_id, d.name, MAX(er.created_at) as last_run
            FROM eval_runs er
            JOIN datasets d ON d.id = er.dataset_id
            WHERE er.agent_version_id = ANY(:ids)
              AND er.status = 'succeeded'
            GROUP BY er.dataset_id, d.name
            HAVING COUNT(DISTINCT er.agent_version_id) = 2
            ORDER BY last_run DESC
            LIMIT 1
        """), {"ids": [version_a, version_b]})
        shared_row = shared_result.fetchone()
        if not shared_row:
            raise HTTPException(
                status_code=404,
                detail="No shared dataset found. Both versions must have at least one succeeded run against the same dataset. Specify dataset_id to compare."
            )
        ds_id = str(shared_row[0])
        ds_name = shared_row[1]

    # ── Find best run for each version against the dataset ───────────────────
    async def get_best_run(ver_id: str) -> dict | None:
        result = await session.execute(text("""
            SELECT id, pass_rate, aggregate_scores, total_cost_usd,
                   total_latency_ms, total_examples
            FROM eval_runs
            WHERE agent_version_id = :ver_id
              AND dataset_id = :ds_id
              AND status = 'succeeded'
            ORDER BY created_at DESC
            LIMIT 1
        """), {"ver_id": ver_id, "ds_id": ds_id})
        row = result.fetchone()
        if not row:
            return None
        return {
            "run_id": str(row[0]),
            "pass_rate": row[1],
            "aggregate_scores": row[2] or {},
            "cost": row[3],
            "latency_ms": row[4],
            "total_examples": row[5],
        }

    run_a = await get_best_run(version_a)
    run_b = await get_best_run(version_b)

    # ── Per-example comparison ────────────────────────────────────────────────
    examples_a_better = examples_b_better = examples_tied = 0

    if run_a and run_b:
        examples_result = await session.execute(text("""
            SELECT
                ra.example_id,
                ra.passed as passed_a,
                rb.passed as passed_b,
                ra.judge_scores as scores_a,
                rb.judge_scores as scores_b
            FROM eval_results ra
            JOIN eval_results rb ON rb.example_id = ra.example_id
                AND rb.eval_run_id = :run_b_id
            WHERE ra.eval_run_id = :run_a_id
        """), {"run_a_id": run_a["run_id"], "run_b_id": run_b["run_id"]})

        for row in examples_result.fetchall():
            passed_a = row[1]
            passed_b = row[2]
            if passed_a and not passed_b:
                examples_a_better += 1
            elif passed_b and not passed_a:
                examples_b_better += 1
            else:
                examples_tied += 1

    # ── Build judge comparisons ───────────────────────────────────────────────
    all_judge_slugs: set[str] = set()
    scores_a = run_a["aggregate_scores"] if run_a else {}
    scores_b = run_b["aggregate_scores"] if run_b else {}
    all_judge_slugs.update(scores_a.keys())
    all_judge_slugs.update(scores_b.keys())

    judge_comparisons = []
    for slug in sorted(all_judge_slugs):
        sa = scores_a.get(slug)
        sb = scores_b.get(slug)
        delta = (sb - sa) if (sa is not None and sb is not None) else None
        if delta is None:
            winner = None
        elif abs(delta) < 0.02:
            winner = "tie"
        elif delta > 0:
            winner = "b"
        else:
            winner = "a"
        judge_comparisons.append(JudgeComparison(
            judge_slug=slug, score_a=sa, score_b=sb, delta=delta, winner=winner
        ))

    # ── Overall winner ────────────────────────────────────────────────────────
    pr_a = run_a["pass_rate"] if run_a else None
    pr_b = run_b["pass_rate"] if run_b else None
    pr_delta = (pr_b - pr_a) if (pr_a is not None and pr_b is not None) else None

    if pr_delta is None:
        overall_winner = None
    elif abs(pr_delta) < 0.02:
        overall_winner = "tie"
    elif pr_delta > 0:
        overall_winner = "b"
    else:
        overall_winner = "a"

    return VersionComparisonResult(
        agent_id=id,
        agent_name=agent_row[1],
        version_a_id=version_a,
        version_a_number=versions[version_a],
        version_a_run_id=run_a["run_id"] if run_a else None,
        version_a_pass_rate=pr_a,
        version_a_cost=run_a["cost"] if run_a else None,
        version_a_latency_ms=run_a["latency_ms"] if run_a else None,
        version_a_total_examples=run_a["total_examples"] if run_a else None,
        version_b_id=version_b,
        version_b_number=versions[version_b],
        version_b_run_id=run_b["run_id"] if run_b else None,
        version_b_pass_rate=pr_b,
        version_b_cost=run_b["cost"] if run_b else None,
        version_b_latency_ms=run_b["latency_ms"] if run_b else None,
        version_b_total_examples=run_b["total_examples"] if run_b else None,
        dataset_id=ds_id,
        dataset_name=ds_name,
        pass_rate_delta=pr_delta,
        overall_winner=overall_winner,
        judge_comparisons=judge_comparisons,
        examples_a_better=examples_a_better,
        examples_b_better=examples_b_better,
        examples_tied=examples_tied,
    )
