from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from beacon.models.agent import Agent, AgentVersion
from beacon.repositories.base import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    model = Agent

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_program(
        self, program_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Agent], int]:
        count_q = (
            select(func.count())
            .select_from(Agent)
            .where(Agent.program_id == program_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()
        q = (
            select(Agent)
            .where(Agent.program_id == program_id)
            .order_by(Agent.name)
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total

    async def get_with_versions(self, agent_id: UUID) -> Agent | None:
        result = await self.session.execute(
            select(Agent)
            .options(selectinload(Agent.versions))
            .where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()


class AgentVersionRepository(BaseRepository[AgentVersion]):
    model = AgentVersion

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_agent(
        self, agent_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[AgentVersion], int]:
        count_q = (
            select(func.count())
            .select_from(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()
        q = (
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version_number.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total

    async def get_latest_for_agent(self, agent_id: UUID) -> AgentVersion | None:
        result = await self.session.execute(
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_next_version_number(self, agent_id: UUID) -> int:
        result = await self.session.execute(
            select(func.max(AgentVersion.version_number)).where(
                AgentVersion.agent_id == agent_id
            )
        )
        max_version = result.scalar_one_or_none()
        return (max_version or 0) + 1

    async def lock(self, version: AgentVersion) -> AgentVersion:
        version.is_locked = True
        await self.session.flush()
        return version
