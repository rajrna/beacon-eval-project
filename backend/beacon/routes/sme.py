import uuid
from fastapi import APIRouter, Query
from beacon.auth.dependencies import CurrentUser, require_sme_or_above
from beacon.core.database import DbSession
from beacon.schemas.eval import ReviewQueueItemResponse, QueueAcknowledge, QueueResolve
from beacon.schemas.base import PaginatedResponse
from beacon.services.eval import SMEService

router = APIRouter()

@router.get("/queue", response_model=PaginatedResponse[ReviewQueueItemResponse], dependencies=[require_sme_or_above()])
async def list_queue(
    session: DbSession, current_user: CurrentUser,
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    return await SMEService(session).list_queue(status=status, priority=priority, limit=limit, offset=offset)

@router.get("/queue/{item_id}", response_model=ReviewQueueItemResponse, dependencies=[require_sme_or_above()])
async def get_queue_item(item_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await SMEService(session).get_queue_item(item_id)

@router.post("/queue/{item_id}/acknowledge", response_model=ReviewQueueItemResponse, dependencies=[require_sme_or_above()])
async def acknowledge(item_id: uuid.UUID, data: QueueAcknowledge, session: DbSession, current_user: CurrentUser):
    return await SMEService(session).acknowledge(item_id, current_user.id, data)

@router.post("/queue/{item_id}/resolve", response_model=ReviewQueueItemResponse, dependencies=[require_sme_or_above()])
async def resolve(item_id: uuid.UUID, data: QueueResolve, session: DbSession, current_user: CurrentUser):
    return await SMEService(session).resolve(item_id, data)
