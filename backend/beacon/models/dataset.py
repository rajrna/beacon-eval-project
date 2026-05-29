import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beacon.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # tuition, admissions, retention, safety, career, finaid
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sme_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Bumped on any change; immutable once referenced by EvalRun
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    langfuse_dataset_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    program: Mapped["Program"] = relationship("Program", back_populates="datasets")
    sme_owner: Mapped["User | None"] = relationship(
        "User", foreign_keys=[sme_owner_id]
    )
    examples: Mapped[list["Example"]] = relationship(
        "Example", back_populates="dataset", cascade="all, delete-orphan"
    )
    eval_runs: Mapped[list["EvalRun"]] = relationship(
        "EvalRun", back_populates="dataset"
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} name={self.name!r} category={self.category!r}>"


class Example(Base):
    __tablename__ = "examples"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Core content
    query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behaviors: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    prohibited_behaviors: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Student persona dimension
    persona: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # adult_learner, first_gen, military, international, struggling, traditional

    # Metadata
    difficulty: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )  # easy, medium, hard, adversarial
    safety_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    is_safety_tagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    langfuse_item_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Promotion tracking (when promoted from a production trace)
    promoted_from_trace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_traces.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="examples")
    eval_results: Mapped[list["EvalResult"]] = relationship(
        "EvalResult", back_populates="example"
    )
    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by_id]
    )

    def __repr__(self) -> str:
        return f"<Example id={self.id} persona={self.persona!r} difficulty={self.difficulty!r}>"
