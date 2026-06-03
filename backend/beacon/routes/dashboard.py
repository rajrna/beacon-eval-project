"""Dashboard metrics endpoint — aggregates key platform stats."""
from fastapi import APIRouter
from pydantic import BaseModel
from beacon.core.database import DbSession
from beacon.auth.dependencies import CurrentUser

router = APIRouter()


class DashboardMetrics(BaseModel):
    # Runs
    total_runs: int
    runs_this_week: int
    avg_pass_rate: float | None
    # Traces
    total_traces: int
    traces_this_week: int
    crisis_pending: int
    # Cost
    cost_this_week: float
    cost_all_time: float
    # Agents & datasets
    total_agents: int
    total_datasets: int
    total_examples: int
    # Recent runs summary
    recent_runs: list[dict]


@router.get("", response_model=DashboardMetrics)
async def get_dashboard(session: DbSession, current_user: CurrentUser) -> DashboardMetrics:
    from sqlalchemy import text

    # ── Runs ──────────────────────────────────────────────────────────────────
    runs_result = await session.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') as this_week,
            AVG(pass_rate) FILTER (WHERE status = 'succeeded' AND pass_rate IS NOT NULL) as avg_pass_rate,
            COALESCE(SUM(total_cost_usd) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days'), 0) as cost_week,
            COALESCE(SUM(total_cost_usd), 0) as cost_all_time
        FROM eval_runs
    """))
    runs_row = runs_result.fetchone()

    # ── Traces ────────────────────────────────────────────────────────────────
    traces_result = await session.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') as this_week
        FROM production_traces
    """))
    traces_row = traces_result.fetchone()

    crisis_result = await session.execute(text("""
        SELECT COUNT(*) FROM review_queue_items
        WHERE status IN ('queued', 'acknowledged')
    """))
    crisis_pending = crisis_result.scalar() or 0

    # ── Agents & datasets ─────────────────────────────────────────────────────
    counts_result = await session.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM agents) as agents,
            (SELECT COUNT(*) FROM datasets) as datasets,
            (SELECT COUNT(*) FROM examples) as examples
    """))
    counts_row = counts_result.fetchone()

    # ── Recent runs ───────────────────────────────────────────────────────────
    recent_result = await session.execute(text("""
        SELECT
            er.id, er.status, er.pass_rate, er.total_examples,
            er.total_cost_usd, er.created_at, er.aggregate_scores,
            av.version_number, a.name as agent_name
        FROM eval_runs er
        LEFT JOIN agent_versions av ON av.id = er.agent_version_id
        LEFT JOIN agents a ON a.id = av.agent_id
        ORDER BY er.created_at DESC
        LIMIT 8
    """))
    recent_rows = recent_result.fetchall()
    recent_runs = [
        {
            "id": str(row[0]),
            "status": row[1],
            "pass_rate": row[2],
            "total_examples": row[3],
            "total_cost_usd": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "aggregate_scores": row[6],
            "version_number": row[7],
            "agent_name": row[8],
        }
        for row in recent_rows
    ]

    return DashboardMetrics(
        total_runs=runs_row[0] or 0,
        runs_this_week=runs_row[1] or 0,
        avg_pass_rate=float(runs_row[2]) if runs_row[2] is not None else None,
        cost_this_week=float(runs_row[3] or 0),
        cost_all_time=float(runs_row[4] or 0),
        total_traces=traces_row[0] or 0,
        traces_this_week=traces_row[1] or 0,
        crisis_pending=int(crisis_pending),
        total_agents=counts_row[0] or 0,
        total_datasets=counts_row[1] or 0,
        total_examples=counts_row[2] or 0,
        recent_runs=recent_runs,
    )
