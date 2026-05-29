import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beacon.core.database import Base


class Agent(Base):
    __tablename__ = "agents"

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
    role: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # advisor, outreach, retention, finaid, career, tutor
    owner_team: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    program: Mapped["Program"] = relationship("Program", back_populates="agents")
    versions: Mapped[list["AgentVersion"]] = relationship(
        "AgentVersion", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name!r} role={self.role!r}>"


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(nullable=False, default=1)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="claude-sonnet-4-5"
    )
    tool_definitions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    knowledge_cutoff_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    safety_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    temperature: Mapped[float] = mapped_column(nullable=False, default=0.0)
    max_tokens: Mapped[int] = mapped_column(nullable=False, default=1024)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Once referenced by an EvalRun, this version is locked
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="versions")
    eval_runs: Mapped[list["EvalRun"]] = relationship(
        "EvalRun", back_populates="agent_version"
    )
    production_traces: Mapped[list["ProductionTrace"]] = relationship(
        "ProductionTrace", back_populates="agent_version"
    )
    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by_id]
    )

    def __repr__(self) -> str:
        return f"<AgentVersion id={self.id} agent_id={self.agent_id} v={self.version_number}>"
