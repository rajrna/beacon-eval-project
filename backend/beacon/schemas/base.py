from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BeaconModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimestampMixin(BeaconModel):
    created_at: datetime
    updated_at: datetime


class UUIDMixin(BeaconModel):
    id: UUID


class PaginatedResponse(BeaconModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool


class ProblemDetail(BeaconModel):
    """RFC 7807 problem details."""
    type: str = "https://beacon.dev/errors/generic"
    title: str
    status: int
    detail: str
    instance: str | None = None
