import uuid
from fastapi import APIRouter, Query
from beacon.auth.dependencies import CurrentUser, require_sme_or_above
from beacon.core.database import DbSession
from beacon.schemas.eval import TraceIngest, TraceResponse, TraceSummary
from beacon.schemas.base import PaginatedResponse
from beacon.services.eval import TraceService

router = APIRouter()

@router.post("", response_model=TraceResponse, status_code=201)
async def ingest_trace(data: TraceIngest, session: DbSession, current_user: CurrentUser):
    return await TraceService(session).ingest(data)

@router.get("", response_model=PaginatedResponse[TraceSummary])
async def list_traces(
    session: DbSession, current_user: CurrentUser,
    agent_version_id: uuid.UUID = Query(...),
    needs_review: bool | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    return await TraceService(session).list(
        agent_version_id=agent_version_id, needs_review=needs_review,
        limit=limit, offset=offset,
    )

@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(trace_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await TraceService(session).get(trace_id)
