from uuid import UUID

from pydantic import Field, HttpUrl, field_validator

from beacon.schemas.base import BeaconModel, TimestampMixin, UUIDMixin


# ── Institution ───────────────────────────────────────────────────────────────

class InstitutionCreate(BeaconModel):
    name: str = Field(min_length=2, max_length=255)
    accreditor: str | None = Field(default=None, max_length=255)
    ipeds_id: str | None = Field(default=None, max_length=20)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    teams_webhook_url: str | None = None


class InstitutionUpdate(BeaconModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    accreditor: str | None = None
    ipeds_id: str | None = None
    teams_webhook_url: str | None = None


class InstitutionResponse(UUIDMixin, TimestampMixin):
    name: str
    accreditor: str | None
    ipeds_id: str | None
    slug: str
    teams_webhook_url: str | None
    program_count: int = 0


class InstitutionSummary(UUIDMixin):
    name: str
    slug: str


# ── Program ───────────────────────────────────────────────────────────────────

class ProgramCreate(BeaconModel):
    institution_id: UUID
    name: str = Field(min_length=2, max_length=255)
    degree_type: str = Field(max_length=50)
    format: str = Field(default="online", pattern=r"^(online|hybrid|in-person)$")
    modality: str = Field(default="async", pattern=r"^(async|sync|mixed)$")
    tuition_per_credit: float | None = Field(default=None, gt=0)
    total_credits: int | None = Field(default=None, gt=0)
    term_calendar: str = Field(
        default="semester", pattern=r"^(semester|quarter|eight-week)$"
    )
    description: str | None = None


class ProgramUpdate(BeaconModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    degree_type: str | None = None
    format: str | None = Field(default=None, pattern=r"^(online|hybrid|in-person)$")
    modality: str | None = Field(default=None, pattern=r"^(async|sync|mixed)$")
    tuition_per_credit: float | None = None
    total_credits: int | None = None
    term_calendar: str | None = None
    description: str | None = None


class ProgramResponse(UUIDMixin, TimestampMixin):
    institution_id: UUID
    name: str
    degree_type: str
    format: str
    modality: str
    tuition_per_credit: float | None
    total_credits: int | None
    term_calendar: str
    description: str | None
    institution: InstitutionSummary | None = None
    agent_count: int = 0
    dataset_count: int = 0


class ProgramSummary(UUIDMixin):
    name: str
    degree_type: str
    institution_id: UUID
