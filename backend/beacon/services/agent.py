import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.agent import Agent, AgentVersion
from beacon.repositories.agent import AgentRepository, AgentVersionRepository
from beacon.schemas.agent import (
    AgentCreate, AgentResponse, AgentUpdate,
    AgentVersionCreate, AgentVersionResponse,
)
from beacon.schemas.base import PaginatedResponse


class AgentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AgentRepository(session)
        self.version_repo = AgentVersionRepository(session)

    async def list(
        self, program_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[AgentResponse]:
        rows, total = await self.repo.list_by_program(program_id, limit=limit, offset=offset)
        items = []
        for agent in rows:
            latest = await self.version_repo.get_latest_for_agent(agent.id)
            items.append(self._to_response(agent, latest))
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get(self, agent_id: uuid.UUID) -> AgentResponse:
        agent = await self.repo.get_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        latest = await self.version_repo.get_latest_for_agent(agent_id)
        return self._to_response(agent, latest)

    async def create(self, data: AgentCreate) -> AgentResponse:
        agent = Agent(**data.model_dump())
        agent = await self.repo.create(agent)
        return self._to_response(agent, None)

    async def update(self, agent_id: uuid.UUID, data: AgentUpdate) -> AgentResponse:
        agent = await self.repo.get_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(agent, field, value)
        await self.repo.flush()
        return await self.get(agent_id)

    async def delete(self, agent_id: uuid.UUID) -> None:
        agent = await self.repo.get_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        await self.repo.delete(agent)

    # ── Versions ──────────────────────────────────────────────────────────────

    async def list_versions(
        self, agent_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[AgentVersionResponse]:
        rows, total = await self.version_repo.list_by_agent(agent_id, limit=limit, offset=offset)
        items = [self._version_to_response(v) for v in rows]
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get_version(self, version_id: uuid.UUID) -> AgentVersionResponse:
        version = await self.version_repo.get_by_id(version_id)
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent version not found")
        return self._version_to_response(version)

    async def create_version(
        self, agent_id: uuid.UUID, data: AgentVersionCreate, created_by_id: uuid.UUID | None = None
    ) -> AgentVersionResponse:
        import structlog
        logger = structlog.get_logger(__name__)

        agent = await self.repo.get_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

        # Get the current latest version before creating the new one
        # This becomes the baseline for regression comparison
        previous_version = await self.version_repo.get_latest_for_agent(agent_id)
        previous_version_id = previous_version.id if previous_version else None

        next_version = await self.version_repo.get_next_version_number(agent_id)
        version = AgentVersion(
            agent_id=agent_id,
            version_number=next_version,
            created_by_id=created_by_id,
            **data.model_dump(),
        )
        version = await self.version_repo.create(version)

        # ── Trigger regression testing ────────────────────────────────────────
        # Only run regression if there's a previous version to compare against.
        # First version creation just runs a baseline eval with no comparison.
        if previous_version_id:
            try:
                from beacon.services.regression import RegressionService
                regression = RegressionService(self.version_repo.session)
                run_ids = await regression.trigger_regression(
                    agent_id=agent_id,
                    new_version_id=version.id,
                    previous_version_id=previous_version_id,
                )
                if run_ids:
                    logger.info(
                        "regression_runs_triggered",
                        agent_id=str(agent_id),
                        new_version=next_version,
                        previous_version=previous_version.version_number,
                        runs=len(run_ids),
                    )
            except Exception as exc:
                # Regression is best-effort — never block version creation
                logger.warning(
                    "regression_trigger_error",
                    agent_id=str(agent_id),
                    error=str(exc),
                )
        else:
            # First version — run baseline eval with no comparison
            try:
                from beacon.services.regression import RegressionService
                regression = RegressionService(self.version_repo.session)
                run_ids = await regression.trigger_regression(
                    agent_id=agent_id,
                    new_version_id=version.id,
                    previous_version_id=None,
                )
                if run_ids:
                    logger.info(
                        "baseline_eval_triggered",
                        agent_id=str(agent_id),
                        version=next_version,
                        runs=len(run_ids),
                    )
            except Exception as exc:
                logger.warning(
                    "baseline_eval_trigger_error",
                    agent_id=str(agent_id),
                    error=str(exc),
                )

        return self._version_to_response(version)

    def _to_response(self, agent: Agent, latest: AgentVersion | None) -> AgentResponse:
        return AgentResponse(
            **{c.name: getattr(agent, c.name) for c in agent.__table__.columns},
            latest_version_id=latest.id if latest else None,
        )

    def _version_to_response(self, v: AgentVersion) -> AgentVersionResponse:
        return AgentVersionResponse(
            **{c.name: getattr(v, c.name) for c in v.__table__.columns}
        )

# import uuid

# from fastapi import HTTPException, status
# from sqlalchemy.ext.asyncio import AsyncSession

# from beacon.models.agent import Agent, AgentVersion
# from beacon.repositories.agent import AgentRepository, AgentVersionRepository
# from beacon.schemas.agent import (
#     AgentCreate, AgentResponse, AgentUpdate,
#     AgentVersionCreate, AgentVersionResponse,
# )
# from beacon.schemas.base import PaginatedResponse


# class AgentService:
#     def __init__(self, session: AsyncSession) -> None:
#         self.repo = AgentRepository(session)
#         self.version_repo = AgentVersionRepository(session)

#     async def list(
#         self, program_id: uuid.UUID, limit: int = 20, offset: int = 0
#     ) -> PaginatedResponse[AgentResponse]:
#         rows, total = await self.repo.list_by_program(program_id, limit=limit, offset=offset)
#         items = []
#         for agent in rows:
#             latest = await self.version_repo.get_latest_for_agent(agent.id)
#             items.append(self._to_response(agent, latest))
#         return PaginatedResponse(
#             items=items, total=total, limit=limit, offset=offset,
#             has_more=(offset + limit) < total,
#         )

#     async def get(self, agent_id: uuid.UUID) -> AgentResponse:
#         agent = await self.repo.get_by_id(agent_id)
#         if not agent:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
#         latest = await self.version_repo.get_latest_for_agent(agent_id)
#         return self._to_response(agent, latest)

#     async def create(self, data: AgentCreate) -> AgentResponse:
#         agent = Agent(**data.model_dump())
#         agent = await self.repo.create(agent)
#         return self._to_response(agent, None)

#     async def update(self, agent_id: uuid.UUID, data: AgentUpdate) -> AgentResponse:
#         agent = await self.repo.get_by_id(agent_id)
#         if not agent:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
#         for field, value in data.model_dump(exclude_none=True).items():
#             setattr(agent, field, value)
#         await self.repo.flush()
#         return await self.get(agent_id)

#     async def delete(self, agent_id: uuid.UUID) -> None:
#         agent = await self.repo.get_by_id(agent_id)
#         if not agent:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
#         await self.repo.delete(agent)

#     # ── Versions ──────────────────────────────────────────────────────────────

#     async def list_versions(
#         self, agent_id: uuid.UUID, limit: int = 20, offset: int = 0
#     ) -> PaginatedResponse[AgentVersionResponse]:
#         rows, total = await self.version_repo.list_by_agent(agent_id, limit=limit, offset=offset)
#         items = [self._version_to_response(v) for v in rows]
#         return PaginatedResponse(
#             items=items, total=total, limit=limit, offset=offset,
#             has_more=(offset + limit) < total,
#         )

#     async def get_version(self, version_id: uuid.UUID) -> AgentVersionResponse:
#         version = await self.version_repo.get_by_id(version_id)
#         if not version:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent version not found")
#         return self._version_to_response(version)

#     async def create_version(
#         self, agent_id: uuid.UUID, data: AgentVersionCreate, created_by_id: uuid.UUID | None = None
#     ) -> AgentVersionResponse:
#         agent = await self.repo.get_by_id(agent_id)
#         if not agent:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
#         next_version = await self.version_repo.get_next_version_number(agent_id)
#         version = AgentVersion(
#             agent_id=agent_id,
#             version_number=next_version,
#             created_by_id=created_by_id,
#             **data.model_dump(),
#         )
#         version = await self.version_repo.create(version)
#         return self._version_to_response(version)

#     def _to_response(self, agent: Agent, latest: AgentVersion | None) -> AgentResponse:
#         return AgentResponse(
#             **{c.name: getattr(agent, c.name) for c in agent.__table__.columns},
#             latest_version_id=latest.id if latest else None,
#         )

#     def _version_to_response(self, v: AgentVersion) -> AgentVersionResponse:
#         return AgentVersionResponse(
#             **{c.name: getattr(v, c.name) for c in v.__table__.columns}
#         )
