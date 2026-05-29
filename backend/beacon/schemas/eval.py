from datetime import datetime
from uuid import UUID

from pydantic import Field

from beacon.schemas.base import BeaconModel, UUIDMixin


# ── EvalRun ───────────────────────────────────────────────────────────────────

class EvalRunTrigger(BeaconModel):
    """POST /v1/runs — triggers a new eval run."""
    agent_version_id: UUID
    dataset_id: UUID
    judge_version_ids: list[UUID] = Field(min_length=1)


class EvalRunResponse(UUIDMixin):
    agent_version_id: UUID
    dataset_id: UUID
    dataset_version: int
    judge_version_ids: list[str]
    status: str
    langfuse_run_id: str | None
    rq_job_id: str | None
    total_examples: int | None
    passed_examples: int | None
    pass_rate: float | None
    aggregate_scores: dict | None
    total_cost_usd: float | None
    total_latency_ms: int | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    triggered_by_id: UUID | None


class EvalRunSummary(UUIDMixin):
    agent_version_id: UUID
    dataset_id: UUID
    status: str
    pass_rate: float | None
    created_at: datetime


# ── EvalResult ────────────────────────────────────────────────────────────────

class EvalResultResponse(UUIDMixin):
    eval_run_id: UUID
    example_id: UUID
    agent_response: str | None
    judge_scores: dict | None
    safety_flags: list[str]
    passed: bool | None
    latency_ms: int | None
    cost_usd: float | None
    input_tokens: int | None
    output_tokens: int | None
    langfuse_observation_id: str | None
    error_message: str | None
    created_at: datetime


# ── ProductionTrace ───────────────────────────────────────────────────────────

class TraceIngest(BeaconModel):
    """Payload sent by a student agent to ingest a production trace."""
    agent_version_id: UUID
    raw_prompt: str = Field(min_length=1)
    raw_response: str = Field(min_length=1)
    tool_calls: list[dict] | None = None
    session_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    model_id: str | None = None


class TraceResponse(UUIDMixin):
    agent_version_id: UUID
    langfuse_trace_id: str | None
    session_hash: str | None
    ferpa_classification: str
    redacted_prompt: str | None
    redacted_response: str | None
    tool_calls: list[dict] | None
    safety_flags: list[str]
    needs_review: bool
    review_priority: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    model_id: str | None
    created_at: datetime


class TraceSummary(UUIDMixin):
    agent_version_id: UUID
    ferpa_classification: str
    safety_flags: list[str]
    needs_review: bool
    review_priority: str | None
    created_at: datetime


# ── Annotation ────────────────────────────────────────────────────────────────

class AnnotationCreate(BeaconModel):
    overall_quality: int | None = Field(default=None, ge=1, le=5)
    dimension_scores: dict | None = None
    safety_assessment: str | None = Field(
        default=None, pattern=r"^(none|concerning|crisis)$"
    )
    notes: str | None = None


class AnnotationUpdate(BeaconModel):
    overall_quality: int | None = Field(default=None, ge=1, le=5)
    dimension_scores: dict | None = None
    safety_assessment: str | None = Field(
        default=None, pattern=r"^(none|concerning|crisis)$"
    )
    notes: str | None = None


class AnnotationResponse(UUIDMixin):
    trace_id: UUID
    reviewer_id: UUID
    overall_quality: int | None
    dimension_scores: dict | None
    safety_assessment: str | None
    notes: str | None
    promoted_example_id: UUID | None
    created_at: datetime
    updated_at: datetime


# ── SME Queue ─────────────────────────────────────────────────────────────────

class ReviewQueueItemResponse(UUIDMixin):
    trace_id: UUID
    priority: str
    status: str
    assigned_to_id: UUID | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    resolution_notes: str | None
    sla_deadline: datetime | None
    sla_breached: bool
    created_at: datetime
    trace: TraceSummary | None = None


class QueueAcknowledge(BeaconModel):
    notes: str | None = None


class QueueResolve(BeaconModel):
    resolution_notes: str = Field(min_length=5)


# ── Promote trace to golden example ──────────────────────────────────────────

class PromoteToGoldenRequest(BeaconModel):
    dataset_id: UUID
    query: str = Field(min_length=5)
    expected_behaviors: list[str] = Field(min_length=1)
    prohibited_behaviors: list[str] = Field(default_factory=list)
    persona: str | None = Field(
        default=None,
        pattern=r"^(adult_learner|first_gen|military|international|struggling|traditional)$",
    )
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard|adversarial)$")
    safety_tags: list[str] = Field(default_factory=list)
    notes: str | None = None
