from datetime import datetime
from uuid import UUID

from pydantic import Field

from beacon.schemas.base import BeaconModel, UUIDMixin

AGENT_ROLES = ("advisor", "outreach", "retention", "finaid", "career", "tutor")


# ── Agent ─────────────────────────────────────────────────────────────────────

class AgentCreate(BeaconModel):
    program_id: UUID
    name: str = Field(min_length=2, max_length=255)
    role: str = Field(pattern=r"^(advisor|outreach|retention|finaid|career|tutor)$")
    owner_team: str | None = Field(default=None, max_length=255)
    owner_email: str | None = Field(default=None, max_length=255)
    description: str | None = None


class AgentUpdate(BeaconModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    role: str | None = Field(
        default=None,
        pattern=r"^(advisor|outreach|retention|finaid|career|tutor)$",
    )
    owner_team: str | None = None
    owner_email: str | None = None
    description: str | None = None
    is_active: bool | None = None


class AgentResponse(UUIDMixin):
    program_id: UUID
    name: str
    role: str
    owner_team: str | None
    owner_email: str | None
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    version_count: int = 0
    latest_version_id: UUID | None = None


class AgentSummary(UUIDMixin):
    name: str
    role: str
    program_id: UUID


# ── AgentVersion ──────────────────────────────────────────────────────────────

class AgentVersionCreate(BeaconModel):
    system_prompt: str = Field(min_length=10)
    model_id: str = Field(default="claude-sonnet-4-5", max_length=100)
    tool_definitions: dict | None = None
    knowledge_cutoff_date: datetime | None = None
    safety_config: dict | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    notes: str | None = None


class AgentVersionResponse(UUIDMixin):
    agent_id: UUID
    version_number: int
    system_prompt: str
    model_id: str
    tool_definitions: dict | None
    knowledge_cutoff_date: datetime | None
    safety_config: dict | None
    temperature: float
    max_tokens: int
    notes: str | None
    is_locked: bool
    created_at: datetime
    created_by_id: UUID | None


class AgentVersionSummary(UUIDMixin):
    agent_id: UUID
    version_number: int
    model_id: str
    is_locked: bool
    created_at: datetime
