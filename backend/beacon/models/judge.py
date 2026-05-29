import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beacon.core.database import Base


class Judge(Base):
    __tablename__ = "judges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # quality or safety_critical
    judge_type: Mapped[str] = mapped_column(String(20), nullable=False, default="quality")
    # Safety-critical judges require 2-reviewer sign-off on version changes
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    versions: Mapped[list["JudgeVersion"]] = relationship(
        "JudgeVersion", back_populates="judge", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Judge id={self.id} slug={self.slug!r} type={self.judge_type!r}>"


class JudgeVersion(Base):
    __tablename__ = "judge_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    judge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("judges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    model_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="claude-sonnet-4-5"
    )
    rubric_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON schema for structured output validation
    output_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    few_shot_examples: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    pass_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Immutable once referenced by an EvalRun
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # For safety-critical judges: review sign-offs
    reviewer_1_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_2_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    judge: Mapped["Judge"] = relationship("Judge", back_populates="versions")
    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by_id]
    )
    reviewer_1: Mapped["User | None"] = relationship(
        "User", foreign_keys=[reviewer_1_id]
    )
    reviewer_2: Mapped["User | None"] = relationship(
        "User", foreign_keys=[reviewer_2_id]
    )

    def __repr__(self) -> str:
        return f"<JudgeVersion id={self.id} judge_id={self.judge_id} v={self.version_number}>"
