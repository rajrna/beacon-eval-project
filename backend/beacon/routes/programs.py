import uuid
from fastapi import APIRouter, Query
from beacon.auth.dependencies import CurrentUser, require_engineer_or_above
from beacon.core.database import DbSession
from beacon.schemas.institution import ProgramCreate, ProgramResponse, ProgramUpdate
from beacon.schemas.base import PaginatedResponse
from beacon.services.institution import ProgramService

router = APIRouter()

@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(program_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await ProgramService(session).get(program_id)

@router.post("", response_model=ProgramResponse, status_code=201, dependencies=[require_engineer_or_above()])
async def create_program(data: ProgramCreate, session: DbSession, current_user: CurrentUser):
    return await ProgramService(session).create(data)

@router.patch("/{program_id}", response_model=ProgramResponse, dependencies=[require_engineer_or_above()])
async def update_program(program_id: uuid.UUID, data: ProgramUpdate, session: DbSession, current_user: CurrentUser):
    return await ProgramService(session).update(program_id, data)

@router.delete("/{program_id}", status_code=204, dependencies=[require_engineer_or_above()])
async def delete_program(program_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    await ProgramService(session).delete(program_id)
