import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beacon.core.database import Base


class ProductionTrace(Base):
    __tablename__ = "production_traces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    langfuse_trace_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    # Stable hash of session_id — never the raw identifier
    session_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # FERPA classification: public, directory, confidential
    ferpa_classification: Mapped[str] = mapped_column(
        String(20), nullable=False, default="public"
    )
    # PII-redacted content only — raw never persisted
    redacted_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    redacted_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    safety_flags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    # Safety routing
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    review_priority: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # crisis, concerning, routine
    # Token / cost metadata (from agent response)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    agent_version: Mapped["AgentVersion"] = relationship(
        "AgentVersion", back_populates="production_traces"
    )
    annotations: Mapped[list["Annotation"]] = relationship(
        "Annotation", back_populates="trace", cascade="all, delete-orphan"
    )
    review_queue_item: Mapped["ReviewQueueItem | None"] = relationship(
        "ReviewQueueItem", back_populates="trace", uselist=False
    )
    promoted_examples: Mapped[list["Example"]] = relationship(
        "Example",
        primaryjoin="ProductionTrace.id == foreign(Example.promoted_from_trace_id)",
        back_populates=None,
    )

    def __repr__(self) -> str:
        return (
            f"<ProductionTrace id={self.id} ferpa={self.ferpa_classification!r} "
            f"needs_review={self.needs_review}>"
        )


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_traces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    overall_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1–5
    dimension_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # none, concerning, crisis
    safety_assessment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Link to Example created when promoted to golden set
    promoted_example_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("examples.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    trace: Mapped["ProductionTrace"] = relationship(
        "ProductionTrace", back_populates="annotations"
    )
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id])
    promoted_example: Mapped["Example | None"] = relationship(
        "Example", foreign_keys=[promoted_example_id]
    )

    def __repr__(self) -> str:
        return f"<Annotation id={self.id} quality={self.overall_quality}>"


class ReviewQueueItem(Base):
    __tablename__ = "review_queue_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_traces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="routine"
    )  # crisis, concerning, routine
    # queued, in_review, acknowledged, resolved
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For SLA tracking
    sla_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sla_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    trace: Mapped["ProductionTrace"] = relationship(
        "ProductionTrace", back_populates="review_queue_item"
    )
    assigned_to: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_to_id]
    )

    def __repr__(self) -> str:
        return (
            f"<ReviewQueueItem id={self.id} priority={self.priority!r} "
            f"status={self.status!r}>"
        )
