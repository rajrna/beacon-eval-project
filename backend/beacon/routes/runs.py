import uuid
from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse
from beacon.auth.dependencies import CurrentUser, require_engineer_or_above
from beacon.core.database import DbSession
from beacon.schemas.eval import EvalRunTrigger, EvalRunResponse, EvalResultResponse
from beacon.schemas.base import PaginatedResponse
from beacon.services.eval import EvalRunService

router = APIRouter()

@router.post("", status_code=202, dependencies=[require_engineer_or_above()])
async def trigger_eval_run(
    data: EvalRunTrigger,
    session: DbSession,
    current_user: CurrentUser,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    run = await EvalRunService(session).trigger(data, triggered_by_id=current_user.id)
    return run

@router.get("/{run_id}", response_model=EvalRunResponse)
async def get_run(run_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await EvalRunService(session).get(run_id)

@router.get("/{run_id}/results", response_model=PaginatedResponse[EvalResultResponse])
async def list_results(
    run_id: uuid.UUID, session: DbSession, current_user: CurrentUser,
    limit: int = Query(default=50, le=200), offset: int = Query(default=0, ge=0),
):
    return await EvalRunService(session).list_results(run_id, limit=limit, offset=offset)


@router.get("", response_model=PaginatedResponse[EvalRunResponse])
async def list_runs(
    session: DbSession,
    current_user: CurrentUser,
    agent_version_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    from beacon.repositories.eval import EvalRunRepository
    from sqlalchemy import select
    from beacon.models.eval import EvalRun

    repo = EvalRunRepository(session)
    if agent_version_id:
        rows, total = await repo.list_by_agent_version(agent_version_id, limit=limit, offset=offset)
    else:
        # List all runs
        from sqlalchemy import select, desc
        q = select(EvalRun).order_by(desc(EvalRun.created_at)).offset(offset).limit(limit)
        from sqlalchemy import func
        count_q = select(func.count()).select_from(EvalRun)
        result = await session.execute(q)
        rows = list(result.scalars().all())
        total = (await session.execute(count_q)).scalar_one()

    from beacon.schemas.base import PaginatedResponse
    from beacon.schemas.eval import EvalRunResponse
    items = [EvalRunResponse(**{c.name: getattr(r, c.name) for c in r.__table__.columns}) for r in rows]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset, has_more=(offset + limit) < total)