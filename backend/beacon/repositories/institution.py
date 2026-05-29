from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from beacon.models.institution import Institution, Program
from beacon.repositories.base import BaseRepository


class InstitutionRepository(BaseRepository[Institution]):
    model = Institution

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_slug(self, slug: str) -> Institution | None:
        result = await self.session.execute(
            select(Institution).where(Institution.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_ipeds(self, ipeds_id: str) -> Institution | None:
        result = await self.session.execute(
            select(Institution).where(Institution.ipeds_id == ipeds_id)
        )
        return result.scalar_one_or_none()

    async def list_with_counts(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[tuple[Institution, int]], int]:
        count_q = select(func.count()).select_from(Institution)
        total = (await self.session.execute(count_q)).scalar_one()

        q = (
            select(Institution, func.count(Program.id).label("program_count"))
            .outerjoin(Program, Program.institution_id == Institution.id)
            .group_by(Institution.id)
            .order_by(Institution.name)
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(q)).all()
        return [(row[0], row[1]) for row in rows], total


class ProgramRepository(BaseRepository[Program]):
    model = Program

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_institution(
        self,
        institution_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Program], int]:
        count_q = (
            select(func.count())
            .select_from(Program)
            .where(Program.institution_id == institution_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()

        q = (
            select(Program)
            .where(Program.institution_id == institution_id)
            .order_by(Program.name)
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total

    async def get_with_institution(self, program_id: UUID) -> Program | None:
        result = await self.session.execute(
            select(Program)
            .options(selectinload(Program.institution))
            .where(Program.id == program_id)
        )
        return result.scalar_one_or_none()
