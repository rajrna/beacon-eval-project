"""
Auth dependencies for FastAPI.

For local development without Entra ID configured, JWT validation is bypassed
and a dev user is injected. Set ENTRA_CLIENT_ID in .env.local to enable real auth.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from beacon.core.settings import get_settings
from beacon.models.user import User

logger = structlog.get_logger(__name__)

security = HTTPBearer(auto_error=False)


# ── Dev user (used when Entra ID is not configured) ───────────────────────────

def _make_dev_user() -> User:
    user = User()
    user.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.entra_oid = "dev-oid"
    user.email = "dev@beacon.local"
    user.display_name = "Dev User"
    user.role = "admin"
    user.is_active = True
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


DEV_USER = _make_dev_user()


# ── Token validation ──────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    settings = get_settings()

    # Local dev bypass — no Entra ID configured
    if not settings.entra_client_id:
        logger.debug("auth_bypassed_dev_mode")
        return DEV_USER

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # In production this would validate the JWT against Entra ID JWKS
        # and look up the user in the DB. For now we return the dev user
        # when a token is present, so the auth plumbing is in place.
        # Full MSAL validation is wired in Part 5 (auth integration).
        logger.debug("auth_token_present", token_prefix=credentials.credentials[:10])
        return DEV_USER
    except Exception as exc:
        logger.warning("auth_validation_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── Typed dependency aliases ──────────────────────────────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]


# ── RBAC helpers ─────────────────────────────────────────────────────────────

def require_roles(*roles: str):
    """Dependency factory — raises 403 if user doesn't have one of the given roles."""
    async def _check(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted for this action. "
                       f"Required: {roles}",
            )
        return current_user
    return Depends(_check)


def require_admin():
    return require_roles("admin")


def require_engineer_or_above():
    return require_roles("admin", "engineer")


def require_sme_or_above():
    return require_roles("admin", "engineer", "sme")


def require_any_role():
    return require_roles("admin", "engineer", "sme", "viewer")


# ── Institution scoping ───────────────────────────────────────────────────────

def assert_institution_access(user: User, institution_id: uuid.UUID) -> None:
    """Raise 403 if the user doesn't belong to the institution (unless admin)."""
    if user.role == "admin":
        return
    if user.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this institution is not permitted.",
        )
