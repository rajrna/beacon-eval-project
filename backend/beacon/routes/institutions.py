import uuid
from fastapi import APIRouter, Query
from beacon.auth.dependencies import CurrentUser, require_engineer_or_above, require_admin
from beacon.core.database import DbSession
from beacon.schemas.institution import (
    InstitutionCreate, InstitutionResponse, InstitutionUpdate,
    ProgramCreate, ProgramResponse, ProgramUpdate,
)
from beacon.schemas.base import PaginatedResponse
from beacon.services.institution import InstitutionService, ProgramService

router = APIRouter()

@router.get("", response_model=PaginatedResponse[InstitutionResponse])
async def list_institutions(
    session: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await InstitutionService(session).list(limit=limit, offset=offset)

@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(institution_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await InstitutionService(session).get(institution_id)

@router.post("", response_model=InstitutionResponse, status_code=201, dependencies=[require_admin()])
async def create_institution(data: InstitutionCreate, session: DbSession, current_user: CurrentUser):
    return await InstitutionService(session).create(data)

@router.patch("/{institution_id}", response_model=InstitutionResponse, dependencies=[require_admin()])
async def update_institution(institution_id: uuid.UUID, data: InstitutionUpdate, session: DbSession, current_user: CurrentUser):
    return await InstitutionService(session).update(institution_id, data)

@router.delete("/{institution_id}", status_code=204, dependencies=[require_admin()])
async def delete_institution(institution_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    await InstitutionService(session).delete(institution_id)

# ── Programs nested under institutions ────────────────────────────────────────

@router.get("/{institution_id}/programs", response_model=PaginatedResponse[ProgramResponse])
async def list_programs(
    institution_id: uuid.UUID, session: DbSession, current_user: CurrentUser,
    limit: int = Query(default=20, le=100), offset: int = Query(default=0, ge=0),
):
    return await ProgramService(session).list(institution_id, limit=limit, offset=offset)
