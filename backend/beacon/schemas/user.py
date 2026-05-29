from datetime import datetime
from uuid import UUID

from pydantic import Field

from beacon.schemas.base import BeaconModel, UUIDMixin

USER_ROLES = ("engineer", "sme", "viewer", "admin")


class UserResponse(UUIDMixin):
    entra_oid: str
    email: str
    display_name: str
    role: str
    institution_id: UUID | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserRoleUpdate(BeaconModel):
    role: str = Field(pattern=r"^(engineer|sme|viewer|admin)$")
    institution_id: UUID | None = None
