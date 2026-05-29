import uuid
from fastapi import APIRouter, Query
from beacon.auth.dependencies import CurrentUser, require_engineer_or_above
from beacon.core.database import DbSession
from beacon.schemas.judge import JudgeCreate, JudgeResponse, JudgeUpdate, JudgeVersionCreate, JudgeVersionResponse, JudgeVersionApproval
from beacon.schemas.base import PaginatedResponse
from beacon.services.judge import JudgeService

router = APIRouter()

@router.get("", response_model=PaginatedResponse[JudgeResponse])
async def list_judges(session: DbSession, current_user: CurrentUser, limit: int = Query(default=50, le=100), offset: int = Query(default=0, ge=0)):
    return await JudgeService(session).list(limit=limit, offset=offset)

@router.get("/{judge_id}", response_model=JudgeResponse)
async def get_judge(judge_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await JudgeService(session).get(judge_id)

@router.post("", response_model=JudgeResponse, status_code=201, dependencies=[require_engineer_or_above()])
async def create_judge(data: JudgeCreate, session: DbSession, current_user: CurrentUser):
    return await JudgeService(session).create(data)

@router.patch("/{judge_id}", response_model=JudgeResponse, dependencies=[require_engineer_or_above()])
async def update_judge(judge_id: uuid.UUID, data: JudgeUpdate, session: DbSession, current_user: CurrentUser):
    return await JudgeService(session).update(judge_id, data)

@router.get("/{judge_id}/versions", response_model=PaginatedResponse[JudgeVersionResponse])
async def list_versions(judge_id: uuid.UUID, session: DbSession, current_user: CurrentUser, limit: int = Query(default=20, le=100), offset: int = Query(default=0, ge=0)):
    return await JudgeService(session).list_versions(judge_id, limit=limit, offset=offset)

@router.get("/{judge_id}/versions/{version_id}", response_model=JudgeVersionResponse)
async def get_version(judge_id: uuid.UUID, version_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await JudgeService(session).get_version(version_id)

@router.post("/{judge_id}/versions", response_model=JudgeVersionResponse, status_code=201, dependencies=[require_engineer_or_above()])
async def create_version(judge_id: uuid.UUID, data: JudgeVersionCreate, session: DbSession, current_user: CurrentUser):
    return await JudgeService(session).create_version(judge_id, data, created_by_id=current_user.id)

@router.post("/{judge_id}/versions/{version_id}/approve", response_model=JudgeVersionResponse, dependencies=[require_engineer_or_above()])
async def approve_version(judge_id: uuid.UUID, version_id: uuid.UUID, data: JudgeVersionApproval, session: DbSession, current_user: CurrentUser):
    return await JudgeService(session).approve_version(version_id, data, reviewer_id=current_user.id)
