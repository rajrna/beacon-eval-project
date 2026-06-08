import uuid
from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel


KNOWLEDGE_CATEGORIES = Literal[
    "admissions",
    "tuition",
    "requirements",
    "policies",
    "deadlines",
    "financial_aid",
    "clinical",
    "career",
    "general",
]


class KnowledgeEntryCreate(BaseModel):
    category: KNOWLEDGE_CATEGORIES
    key: str
    value: str
    display_label: str | None = None
    effective_date: date | None = None
    expires_date: date | None = None
    source_url: str | None = None
    last_verified: date | None = None
    notes: str | None = None


class KnowledgeEntryUpdate(BaseModel):
    value: str | None = None
    display_label: str | None = None
    effective_date: date | None = None
    expires_date: date | None = None
    source_url: str | None = None
    last_verified: date | None = None
    is_active: bool | None = None
    notes: str | None = None


class KnowledgeEntryResponse(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    category: str
    key: str
    value: str
    display_label: str | None
    effective_date: date | None
    expires_date: date | None
    source_url: str | None
    last_verified: date | None
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeBulkCreate(BaseModel):
    """Upload multiple knowledge entries at once."""
    entries: list[KnowledgeEntryCreate]
