from datetime import datetime
from uuid import UUID

from pydantic import Field

from beacon.schemas.base import BeaconModel, UUIDMixin

DATASET_CATEGORIES = ("tuition", "admissions", "retention", "safety", "career", "finaid")
PERSONAS = ("adult_learner", "first_gen", "military", "international", "struggling", "traditional")
DIFFICULTIES = ("easy", "medium", "hard", "adversarial")


# ── Dataset ───────────────────────────────────────────────────────────────────

class DatasetCreate(BeaconModel):
    program_id: UUID
    name: str = Field(min_length=2, max_length=255)
    category: str = Field(
        pattern=r"^(tuition|admissions|retention|safety|career|finaid)$"
    )
    description: str | None = None
    sme_owner_id: UUID | None = None


class DatasetUpdate(BeaconModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    sme_owner_id: UUID | None = None


class DatasetResponse(UUIDMixin):
    program_id: UUID
    name: str
    category: str
    description: str | None
    sme_owner_id: UUID | None
    version: int
    langfuse_dataset_id: str | None
    created_at: datetime
    updated_at: datetime
    example_count: int = 0


class DatasetSummary(UUIDMixin):
    name: str
    category: str
    version: int
    program_id: UUID


# ── Example ───────────────────────────────────────────────────────────────────

class ExampleCreate(BeaconModel):
    query: str = Field(min_length=5)
    expected_behaviors: list[str] = Field(default_factory=list)
    prohibited_behaviors: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    persona: str | None = Field(
        default=None,
        pattern=r"^(adult_learner|first_gen|military|international|struggling|traditional)$",
    )
    difficulty: str = Field(
        default="medium", pattern=r"^(easy|medium|hard|adversarial)$"
    )
    safety_tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    external_id: str | None = None


class ExampleUpdate(BeaconModel):
    query: str | None = Field(default=None, min_length=5)
    expected_behaviors: list[str] | None = None
    prohibited_behaviors: list[str] | None = None
    reference_answer: str | None = None
    persona: str | None = None
    difficulty: str | None = None
    safety_tags: list[str] | None = None
    notes: str | None = None


class ExampleResponse(UUIDMixin):
    dataset_id: UUID
    query: str
    expected_behaviors: list[str]
    prohibited_behaviors: list[str]
    reference_answer: str | None
    persona: str | None
    difficulty: str
    safety_tags: list[str]
    is_safety_tagged: bool
    notes: str | None
    external_id: str | None
    promoted_from_trace_id: UUID | None
    created_at: datetime
    created_by_id: UUID | None


# ── Bulk import ───────────────────────────────────────────────────────────────

class DatasetImportRequest(BeaconModel):
    """Upload multiple examples at once (e.g. from a JSONL file)."""
    examples: list[ExampleCreate] = Field(min_length=1, max_length=1000)
    replace_existing: bool = False


class DatasetImportResponse(BeaconModel):
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
