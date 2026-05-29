import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.judge import Judge, JudgeVersion
from beacon.repositories.judge import JudgeRepository, JudgeVersionRepository
from beacon.schemas.base import PaginatedResponse
from beacon.schemas.judge import (
    JudgeCreate, JudgeResponse, JudgeUpdate,
    JudgeVersionApproval, JudgeVersionCreate, JudgeVersionResponse,
)


class JudgeService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = JudgeRepository(session)
        self.version_repo = JudgeVersionRepository(session)

    async def list(self, limit: int = 50, offset: int = 0) -> PaginatedResponse[JudgeResponse]:
        rows, total = await self.repo.list_active(limit=limit, offset=offset)
        items = [self._to_response(j) for j in rows]
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get(self, judge_id: uuid.UUID) -> JudgeResponse:
        judge = await self.repo.get_by_id(judge_id)
        if not judge:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Judge not found")
        return self._to_response(judge)

    async def create(self, data: JudgeCreate) -> JudgeResponse:
        existing = await self.repo.get_by_slug(data.slug)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Judge slug already in use")
        judge = Judge(**data.model_dump())
        judge = await self.repo.create(judge)
        return self._to_response(judge)

    async def update(self, judge_id: uuid.UUID, data: JudgeUpdate) -> JudgeResponse:
        judge = await self.repo.get_by_id(judge_id)
        if not judge:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Judge not found")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(judge, field, value)
        await self.repo.flush()
        return self._to_response(judge)

    # ── Versions ──────────────────────────────────────────────────────────────

    async def list_versions(
        self, judge_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[JudgeVersionResponse]:
        rows, total = await self.version_repo.list_by_judge(judge_id, limit=limit, offset=offset)
        items = [self._version_to_response(v) for v in rows]
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get_version(self, version_id: uuid.UUID) -> JudgeVersionResponse:
        version = await self.version_repo.get_by_id(version_id)
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Judge version not found")
        return self._version_to_response(version)

    async def create_version(
        self, judge_id: uuid.UUID, data: JudgeVersionCreate, created_by_id: uuid.UUID | None = None
    ) -> JudgeVersionResponse:
        judge = await self.repo.get_by_id(judge_id)
        if not judge:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Judge not found")

        next_version = await self.version_repo.get_next_version_number(judge_id)
        # Non-safety-critical judges are auto-approved
        is_approved = not judge.is_safety_critical

        version = JudgeVersion(
            judge_id=judge_id,
            version_number=next_version,
            created_by_id=created_by_id,
            is_approved=is_approved,
            **data.model_dump(),
        )
        version = await self.version_repo.create(version)
        return self._version_to_response(version)

    async def approve_version(
        self, version_id: uuid.UUID, data: JudgeVersionApproval, reviewer_id: uuid.UUID
    ) -> JudgeVersionResponse:
        version = await self.version_repo.get_by_id(version_id)
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Judge version not found")

        if data.reviewer_slot == 1:
            if version.reviewer_1_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reviewer 1 already set")
            version.reviewer_1_id = reviewer_id
        else:
            if version.reviewer_2_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reviewer 2 already set")
            version.reviewer_2_id = reviewer_id

        # Approve when both reviewers have signed off
        if version.reviewer_1_id and version.reviewer_2_id:
            version.is_approved = True

        await self.version_repo.flush()
        return self._version_to_response(version)

    def _to_response(self, j: Judge) -> JudgeResponse:
        return JudgeResponse(
            **{c.name: getattr(j, c.name) for c in j.__table__.columns}
        )

    def _version_to_response(self, v: JudgeVersion) -> JudgeVersionResponse:
        return JudgeVersionResponse(
            **{c.name: getattr(v, c.name) for c in v.__table__.columns}
        )
