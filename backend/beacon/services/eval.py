import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.dataset import Example
from beacon.models.eval import EvalRun
from beacon.models.trace import Annotation, ProductionTrace, ReviewQueueItem
from beacon.repositories.dataset import DatasetRepository, ExampleRepository
from beacon.repositories.eval import (
    AnnotationRepository, EvalRunRepository, ReviewQueueRepository, TraceRepository,
)
from beacon.schemas.base import PaginatedResponse
from beacon.schemas.eval import (
    AnnotationCreate, AnnotationResponse, AnnotationUpdate,
    EvalResultResponse, EvalRunResponse, EvalRunSummary, EvalRunTrigger,
    PromoteToGoldenRequest, QueueAcknowledge, QueueResolve,
    ReviewQueueItemResponse, TraceIngest, TraceResponse, TraceSummary,
)
from beacon.core.settings import get_settings


class EvalRunService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = EvalRunRepository(session)
        self.dataset_repo = DatasetRepository(session)

    async def trigger(
        self, data: EvalRunTrigger, triggered_by_id: uuid.UUID | None = None
    ) -> EvalRunResponse:
        dataset = await self.dataset_repo.get_by_id(data.dataset_id)
        if not dataset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

        run = EvalRun(
            agent_version_id=data.agent_version_id,
            dataset_id=data.dataset_id,
            dataset_version=dataset.version,
            judge_version_ids=[str(jid) for jid in data.judge_version_ids],
            status="queued",
            triggered_by_id=triggered_by_id,
        )
        run = await self.repo.create(run)

        # Enqueue to RQ (worker picks this up)
        try:
            from beacon.workers.eval_runner import enqueue_eval_run
            job = enqueue_eval_run(str(run.id))
            run.rq_job_id = job.id
            await self.repo.flush()
        except Exception:
            # Worker not available in dev — run stays queued
            pass

        return self._to_response(run)

    async def get(self, run_id: uuid.UUID) -> EvalRunResponse:
        run = await self.repo.get_by_id(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eval run not found")
        return self._to_response(run)

    async def list_results(
        self, run_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> PaginatedResponse[EvalResultResponse]:
        run = await self.repo.get_by_id(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eval run not found")
        rows, total = await self.repo.get_results(run_id, limit=limit, offset=offset)
        items = [
            EvalResultResponse(**{c.name: getattr(r, c.name) for c in r.__table__.columns})
            for r in rows
        ]
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    def _to_response(self, run: EvalRun) -> EvalRunResponse:
        return EvalRunResponse(
            **{c.name: getattr(run, c.name) for c in run.__table__.columns}
        )


class TraceService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TraceRepository(session)
        self.queue_repo = ReviewQueueRepository(session)

    async def ingest(self, data: TraceIngest) -> TraceResponse:
        """Ingest a production trace — redact PII, classify FERPA, route safety flags."""
        from beacon.safety.redaction import redact_pii
        from beacon.safety.ferpa import classify_ferpa
        from beacon.safety.crisis_detection import detect_crisis_combined

        # Hash session ID first (used as trace_salt for stable placeholders)
        session_hash = None
        trace_salt = None
        if data.session_id:
            session_hash = hashlib.sha256(data.session_id.encode()).hexdigest()
            trace_salt = session_hash

        # Redact PII (in memory — raw never persisted)
        redacted_prompt = redact_pii(data.raw_prompt, trace_salt=trace_salt)
        redacted_response = redact_pii(data.raw_response, trace_salt=trace_salt)

        # FERPA classification (on redacted text)
        ferpa_class = classify_ferpa(redacted_prompt)

        # Safety detection (on RAW text — before redaction removes signals)
        is_crisis, priority = detect_crisis_combined(data.raw_prompt, data.tool_calls)
        safety_flags: list[str] = []
        needs_review = False
        review_priority = "routine"

        if is_crisis:
            safety_flags.append(f"crisis_{priority}")
            needs_review = True
            review_priority = priority

        trace = ProductionTrace(
            agent_version_id=data.agent_version_id,
            session_hash=session_hash,
            ferpa_classification=ferpa_class,
            redacted_prompt=redacted_prompt,
            redacted_response=redacted_response,
            tool_calls=data.tool_calls,
            safety_flags=safety_flags,
            needs_review=needs_review,
            review_priority=review_priority if needs_review else None,
            input_tokens=data.input_tokens,
            output_tokens=data.output_tokens,
            latency_ms=data.latency_ms,
            model_id=data.model_id,
        )
        trace = await self.repo.create(trace)

        # If flagged, add to review queue
        if needs_review:
            await self._add_to_queue(trace, review_priority)

        return self._to_response(trace)

    async def _add_to_queue(self, trace: ProductionTrace, priority: str) -> None:
        settings = get_settings()
        sla_minutes = settings.crisis_review_sla_minutes if priority == "crisis" else 60
        item = ReviewQueueItem(
            trace_id=trace.id,
            priority=priority,
            status="queued",
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=sla_minutes),
        )
        self.queue_repo.session.add(item)
        await self.queue_repo.flush()

    async def get(self, trace_id: uuid.UUID) -> TraceResponse:
        trace = await self.repo.get_by_id(trace_id)
        if not trace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
        return self._to_response(trace)

    async def list(
        self,
        agent_version_id: uuid.UUID | None = None,
        needs_review: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResponse[TraceSummary]:
        rows, total = await self.repo.list_by_agent_version(
            agent_version_id or uuid.uuid4(),  # fallback handled in repo
            limit=limit, offset=offset, needs_review=needs_review,
        )
        items = [
            TraceSummary(
                id=t.id,
                agent_version_id=t.agent_version_id,
                ferpa_classification=t.ferpa_classification,
                safety_flags=t.safety_flags,
                needs_review=t.needs_review,
                review_priority=t.review_priority,
                created_at=t.created_at,
            )
            for t in rows
        ]
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    def _to_response(self, t: ProductionTrace) -> TraceResponse:
        return TraceResponse(
            **{c.name: getattr(t, c.name) for c in t.__table__.columns}
        )


class AnnotationService:
    def __init__(self, session: AsyncSession) -> None:
        self.annotation_repo = AnnotationRepository(session)
        self.trace_repo = TraceRepository(session)
        self.dataset_repo = DatasetRepository(session)
        self.example_repo = ExampleRepository(session)

    async def create(
        self, trace_id: uuid.UUID, data: AnnotationCreate, reviewer_id: uuid.UUID
    ) -> AnnotationResponse:
        trace = await self.trace_repo.get_by_id(trace_id)
        if not trace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

        existing = await self.annotation_repo.get_by_trace_and_reviewer(trace_id, reviewer_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already annotated this trace",
            )

        annotation = Annotation(
            trace_id=trace_id,
            reviewer_id=reviewer_id,
            **data.model_dump(),
        )
        annotation = await self.annotation_repo.create(annotation)
        return self._to_response(annotation)

    async def update(
        self, annotation_id: uuid.UUID, data: AnnotationUpdate, reviewer_id: uuid.UUID
    ) -> AnnotationResponse:
        annotation = await self.annotation_repo.get_by_id(annotation_id)
        if not annotation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")
        if annotation.reviewer_id != reviewer_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your annotation")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(annotation, field, value)
        await self.annotation_repo.flush()
        return self._to_response(annotation)

    async def promote_to_golden(
        self,
        trace_id: uuid.UUID,
        annotation_id: uuid.UUID,
        data: PromoteToGoldenRequest,
        created_by_id: uuid.UUID | None = None,
    ) -> None:
        trace = await self.trace_repo.get_by_id(trace_id)
        if not trace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

        dataset = await self.dataset_repo.get_by_id(data.dataset_id)
        if not dataset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

        example = Example(
            dataset_id=data.dataset_id,
            query=data.query,
            expected_behaviors=data.expected_behaviors,
            prohibited_behaviors=data.prohibited_behaviors,
            persona=data.persona,
            difficulty=data.difficulty,
            safety_tags=data.safety_tags,
            is_safety_tagged=bool(data.safety_tags),
            notes=data.notes,
            promoted_from_trace_id=trace_id,
            created_by_id=created_by_id,
        )
        self.example_repo.session.add(example)
        await self.example_repo.flush()

        # Link to annotation
        annotation = await self.annotation_repo.get_by_id(annotation_id)
        if annotation:
            annotation.promoted_example_id = example.id
            await self.annotation_repo.flush()

        # Bump dataset version
        await self.dataset_repo.bump_version(dataset)

    def _to_response(self, a: Annotation) -> AnnotationResponse:
        return AnnotationResponse(
            **{c.name: getattr(a, c.name) for c in a.__table__.columns}
        )


class SMEService:
    def __init__(self, session: AsyncSession) -> None:
        self.queue_repo = ReviewQueueRepository(session)

    async def list_queue(
        self,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResponse[ReviewQueueItemResponse]:
        rows, total = await self.queue_repo.list_queue(
            status=status, priority=priority, limit=limit, offset=offset
        )
        items = [self._to_response(item) for item in rows]
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get_queue_item(self, item_id: uuid.UUID) -> ReviewQueueItemResponse:
        item = await self.queue_repo.get_by_id(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
        return self._to_response(item)

    async def acknowledge(
        self, item_id: uuid.UUID, user_id: uuid.UUID, data: QueueAcknowledge
    ) -> ReviewQueueItemResponse:
        item = await self.queue_repo.get_by_id(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
        item.status = "acknowledged"
        item.assigned_to_id = user_id
        item.acknowledged_at = datetime.now(timezone.utc)
        if data.notes:
            item.resolution_notes = data.notes
        await self.queue_repo.flush()
        return self._to_response(item)

    async def resolve(
        self, item_id: uuid.UUID, data: QueueResolve
    ) -> ReviewQueueItemResponse:
        item = await self.queue_repo.get_by_id(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
        item.status = "resolved"
        item.resolved_at = datetime.now(timezone.utc)
        item.resolution_notes = data.resolution_notes
        await self.queue_repo.flush()
        return self._to_response(item)

    def _to_response(self, item: ReviewQueueItem) -> ReviewQueueItemResponse:
        data = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        trace_summary = None
        if hasattr(item, "trace") and item.trace:
            t = item.trace
            trace_summary = TraceSummary(
                id=t.id,
                agent_version_id=t.agent_version_id,
                ferpa_classification=t.ferpa_classification,
                safety_flags=t.safety_flags,
                needs_review=t.needs_review,
                review_priority=t.review_priority,
                created_at=t.created_at,
            )
        return ReviewQueueItemResponse(**data, trace=trace_summary)
