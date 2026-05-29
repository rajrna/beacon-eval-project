from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.judge import Judge, JudgeVersion
from beacon.repositories.base import BaseRepository


class JudgeRepository(BaseRepository[Judge]):
    model = Judge

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_slug(self, slug: str) -> Judge | None:
        result = await self.session.execute(
            select(Judge).where(Judge.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_active(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[Judge], int]:
        count_q = (
            select(func.count()).select_from(Judge).where(Judge.is_active == True)  # noqa: E712
        )
        total = (await self.session.execute(count_q)).scalar_one()
        q = (
            select(Judge)
            .where(Judge.is_active == True)  # noqa: E712
            .order_by(Judge.name)
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total


class JudgeVersionRepository(BaseRepository[JudgeVersion]):
    model = JudgeVersion

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_judge(
        self, judge_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[JudgeVersion], int]:
        count_q = (
            select(func.count())
            .select_from(JudgeVersion)
            .where(JudgeVersion.judge_id == judge_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()
        q = (
            select(JudgeVersion)
            .where(JudgeVersion.judge_id == judge_id)
            .order_by(JudgeVersion.version_number.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total

    async def get_next_version_number(self, judge_id: UUID) -> int:
        result = await self.session.execute(
            select(func.max(JudgeVersion.version_number)).where(
                JudgeVersion.judge_id == judge_id
            )
        )
        return (result.scalar_one_or_none() or 0) + 1

    async def get_latest_approved(self, judge_id: UUID) -> JudgeVersion | None:
        result = await self.session.execute(
            select(JudgeVersion)
            .where(
                JudgeVersion.judge_id == judge_id,
                JudgeVersion.is_approved == True,  # noqa: E712
            )
            .order_by(JudgeVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
