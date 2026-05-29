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
