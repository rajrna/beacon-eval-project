import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beacon.core.database import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Snapshot of dataset version at time of run
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False)
    judge_version_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    # queued, running, succeeded, partial, failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    langfuse_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rq_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Aggregate results
    total_examples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed_examples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    aggregate_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    triggered_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    agent_version: Mapped["AgentVersion"] = relationship(
        "AgentVersion", back_populates="eval_runs"
    )
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="eval_runs")
    results: Mapped[list["EvalResult"]] = relationship(
        "EvalResult", back_populates="eval_run", cascade="all, delete-orphan"
    )
    triggered_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[triggered_by_id]
    )

    def __repr__(self) -> str:
        return f"<EvalRun id={self.id} status={self.status!r}>"


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    eval_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    example_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("examples.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    agent_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Per-judge scores: {judge_slug: {score: float, passed: bool, reasoning: str, flags: []}}
    judge_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    safety_flags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    langfuse_observation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    eval_run: Mapped["EvalRun"] = relationship("EvalRun", back_populates="results")
    example: Mapped["Example"] = relationship("Example", back_populates="eval_results")

    def __repr__(self) -> str:
        return f"<EvalResult id={self.id} passed={self.passed}>"
