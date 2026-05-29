import uuid
from fastapi import APIRouter
from beacon.auth.dependencies import CurrentUser, require_sme_or_above
from beacon.core.database import DbSession
from beacon.schemas.eval import AnnotationCreate, AnnotationResponse, AnnotationUpdate, PromoteToGoldenRequest
from beacon.services.eval import AnnotationService

router = APIRouter()

@router.post("/traces/{trace_id}", response_model=AnnotationResponse, status_code=201, dependencies=[require_sme_or_above()])
async def create_annotation(trace_id: uuid.UUID, data: AnnotationCreate, session: DbSession, current_user: CurrentUser):
    return await AnnotationService(session).create(trace_id, data, reviewer_id=current_user.id)

@router.patch("/{annotation_id}", response_model=AnnotationResponse, dependencies=[require_sme_or_above()])
async def update_annotation(annotation_id: uuid.UUID, data: AnnotationUpdate, session: DbSession, current_user: CurrentUser):
    return await AnnotationService(session).update(annotation_id, data, reviewer_id=current_user.id)

@router.post("/traces/{trace_id}/promote/{annotation_id}", status_code=201, dependencies=[require_sme_or_above()])
async def promote_to_golden(
    trace_id: uuid.UUID, annotation_id: uuid.UUID,
    data: PromoteToGoldenRequest, session: DbSession, current_user: CurrentUser,
):
    await AnnotationService(session).promote_to_golden(
        trace_id, annotation_id, data, created_by_id=current_user.id
    )
    return {"status": "promoted"}
