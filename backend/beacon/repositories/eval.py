from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from beacon.models.eval import EvalResult, EvalRun
from beacon.models.trace import Annotation, ProductionTrace, ReviewQueueItem
from beacon.models.user import AuditLog, User
from beacon.repositories.base import BaseRepository


class EvalRunRepository(BaseRepository[EvalRun]):
    model = EvalRun

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_agent_version(
        self, agent_version_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[EvalRun], int]:
        count_q = (
            select(func.count())
            .select_from(EvalRun)
            .where(EvalRun.agent_version_id == agent_version_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()
        q = (
            select(EvalRun)
            .where(EvalRun.agent_version_id == agent_version_id)
            .order_by(EvalRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total

    async def get_results(
        self, eval_run_id: UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[EvalResult], int]:
        count_q = (
            select(func.count())
            .select_from(EvalResult)
            .where(EvalResult.eval_run_id == eval_run_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()
        q = (
            select(EvalResult)
            .where(EvalResult.eval_run_id == eval_run_id)
            .order_by(EvalResult.created_at)
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total


class TraceRepository(BaseRepository[ProductionTrace]):
    model = ProductionTrace

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_agent_version(
        self,
        agent_version_id: UUID,
        limit: int = 50,
        offset: int = 0,
        needs_review: bool | None = None,
    ) -> tuple[list[ProductionTrace], int]:
        filters = [ProductionTrace.agent_version_id == agent_version_id]
        if needs_review is not None:
            filters.append(ProductionTrace.needs_review == needs_review)

        count_q = select(func.count()).select_from(ProductionTrace)
        q = select(ProductionTrace)
        for f in filters:
            count_q = count_q.where(f)
            q = q.where(f)

        total = (await self.session.execute(count_q)).scalar_one()
        rows = (
            await self.session.execute(
                q.order_by(ProductionTrace.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return list(rows), total

    async def get_by_langfuse_id(self, langfuse_trace_id: str) -> ProductionTrace | None:
        result = await self.session.execute(
            select(ProductionTrace).where(
                ProductionTrace.langfuse_trace_id == langfuse_trace_id
            )
        )
        return result.scalar_one_or_none()


class AnnotationRepository(BaseRepository[Annotation]):
    model = Annotation

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_trace_and_reviewer(
        self, trace_id: UUID, reviewer_id: UUID
    ) -> Annotation | None:
        result = await self.session.execute(
            select(Annotation).where(
                Annotation.trace_id == trace_id,
                Annotation.reviewer_id == reviewer_id,
            )
        )
        return result.scalar_one_or_none()


class ReviewQueueRepository(BaseRepository[ReviewQueueItem]):
    model = ReviewQueueItem

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_queue(
        self,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ReviewQueueItem], int]:
        filters = []
        if status:
            filters.append(ReviewQueueItem.status == status)
        if priority:
            filters.append(ReviewQueueItem.priority == priority)

        count_q = select(func.count()).select_from(ReviewQueueItem)
        q = select(ReviewQueueItem).options(
            selectinload(ReviewQueueItem.trace)
        )
        for f in filters:
            count_q = count_q.where(f)
            q = q.where(f)

        # Crisis first, then by age
        q = q.order_by(
            ReviewQueueItem.priority.desc(),
            ReviewQueueItem.created_at.asc(),
        )

        total = (await self.session.execute(count_q)).scalar_one()
        rows = (
            await self.session.execute(q.offset(offset).limit(limit))
        ).scalars().all()
        return list(rows), total

    async def get_breached_sla_items(self) -> list[ReviewQueueItem]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(ReviewQueueItem).where(
                ReviewQueueItem.sla_deadline < now,
                ReviewQueueItem.acknowledged_at.is_(None),
                ReviewQueueItem.status == "queued",
            )
        )
        return list(result.scalars().all())


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_entra_oid(self, entra_oid: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.entra_oid == entra_oid)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def log(
        self,
        actor_id: UUID | None,
        actor_email: str | None,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
        metadata: dict | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            before_state=before_state,
            after_state=after_state,
            metadata_=metadata,
            correlation_id=correlation_id,
            ip_address=ip_address,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry
