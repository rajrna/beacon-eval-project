import uuid
from fastapi import APIRouter, Query
from beacon.auth.dependencies import CurrentUser, require_engineer_or_above
from beacon.core.database import DbSession
from beacon.schemas.agent import AgentCreate, AgentResponse, AgentUpdate, AgentVersionCreate, AgentVersionResponse
from beacon.schemas.base import PaginatedResponse
from beacon.services.agent import AgentService

router = APIRouter()

@router.get("", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    session: DbSession, current_user: CurrentUser,
    program_id: uuid.UUID = Query(...),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await AgentService(session).list(program_id, limit=limit, offset=offset)

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await AgentService(session).get(agent_id)

@router.post("", response_model=AgentResponse, status_code=201, dependencies=[require_engineer_or_above()])
async def create_agent(data: AgentCreate, session: DbSession, current_user: CurrentUser):
    return await AgentService(session).create(data)

@router.patch("/{agent_id}", response_model=AgentResponse, dependencies=[require_engineer_or_above()])
async def update_agent(agent_id: uuid.UUID, data: AgentUpdate, session: DbSession, current_user: CurrentUser):
    return await AgentService(session).update(agent_id, data)

@router.delete("/{agent_id}", status_code=204, dependencies=[require_engineer_or_above()])
async def delete_agent(agent_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    await AgentService(session).delete(agent_id)

# ── Versions ──────────────────────────────────────────────────────────────────

@router.get("/{agent_id}/versions", response_model=PaginatedResponse[AgentVersionResponse])
async def list_versions(
    agent_id: uuid.UUID, session: DbSession, current_user: CurrentUser,
    limit: int = Query(default=20, le=100), offset: int = Query(default=0, ge=0),
):
    return await AgentService(session).list_versions(agent_id, limit=limit, offset=offset)

@router.get("/{agent_id}/versions/{version_id}", response_model=AgentVersionResponse)
async def get_version(agent_id: uuid.UUID, version_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await AgentService(session).get_version(version_id)

@router.post("/{agent_id}/versions", response_model=AgentVersionResponse, status_code=201, dependencies=[require_engineer_or_above()])
async def create_version(agent_id: uuid.UUID, data: AgentVersionCreate, session: DbSession, current_user: CurrentUser):
    return await AgentService(session).create_version(agent_id, data, created_by_id=current_user.id)
