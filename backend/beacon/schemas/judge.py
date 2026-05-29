from datetime import datetime
from uuid import UUID

from pydantic import Field

from beacon.schemas.base import BeaconModel, UUIDMixin


# ── Judge ─────────────────────────────────────────────────────────────────────

class JudgeCreate(BeaconModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9-_]+$")
    description: str | None = None
    judge_type: str = Field(
        default="quality", pattern=r"^(quality|safety_critical)$"
    )
    is_safety_critical: bool = False


class JudgeUpdate(BeaconModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class JudgeResponse(UUIDMixin):
    name: str
    slug: str
    description: str | None
    judge_type: str
    is_safety_critical: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    version_count: int = 0
    latest_version_id: UUID | None = None


class JudgeSummary(UUIDMixin):
    name: str
    slug: str
    is_safety_critical: bool


# ── JudgeVersion ──────────────────────────────────────────────────────────────

class JudgeVersionCreate(BeaconModel):
    model_id: str = Field(default="claude-sonnet-4-5", max_length=100)
    rubric_prompt: str = Field(min_length=20)
    output_schema: dict
    few_shot_examples: list[dict] | None = None
    pass_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str | None = None


class JudgeVersionResponse(UUIDMixin):
    judge_id: UUID
    version_number: int
    model_id: str
    rubric_prompt: str
    output_schema: dict
    few_shot_examples: list[dict] | None
    pass_threshold: float
    temperature: float
    notes: str | None
    is_locked: bool
    is_approved: bool
    reviewer_1_id: UUID | None
    reviewer_2_id: UUID | None
    created_at: datetime
    created_by_id: UUID | None


class JudgeVersionApproval(BeaconModel):
    """Body for approving a safety-critical judge version."""
    reviewer_slot: int = Field(ge=1, le=2)  # 1 or 2
