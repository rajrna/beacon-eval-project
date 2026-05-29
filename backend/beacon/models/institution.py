import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beacon.core.database import Base


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    accreditor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ipeds_id: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    teams_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    programs: Mapped[list["Program"]] = relationship(
        "Program", back_populates="institution", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="institution"
    )

    def __repr__(self) -> str:
        return f"<Institution id={self.id} name={self.name!r}>"


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    degree_type: Mapped[str] = mapped_column(String(50), nullable=False)  # MBA, MSN, BSBA, etc.
    format: Mapped[str] = mapped_column(
        String(20), nullable=False, default="online"
    )  # online, hybrid, in-person
    modality: Mapped[str] = mapped_column(
        String(10), nullable=False, default="async"
    )  # async, sync, mixed
    tuition_per_credit: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    term_calendar: Mapped[str] = mapped_column(
        String(20), nullable=False, default="semester"
    )  # semester, quarter, eight-week
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    institution: Mapped["Institution"] = relationship(
        "Institution", back_populates="programs"
    )
    agents: Mapped[list["Agent"]] = relationship(
        "Agent", back_populates="program", cascade="all, delete-orphan"
    )
    datasets: Mapped[list["Dataset"]] = relationship(
        "Dataset", back_populates="program", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Program id={self.id} name={self.name!r}>"
