"""Unit tests for core app health and settings."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_defaults() -> None:
    from beacon.core.settings import get_settings
    settings = get_settings()
    assert settings.environment in ("local", "dev", "prod")
    assert settings.database_pool_size > 0
    assert settings.eval_batch_size == 10
    assert settings.crisis_review_sla_minutes == 15


def test_settings_is_local() -> None:
    from beacon.core.settings import get_settings
    settings = get_settings()
    # In test environment, defaults to local
    assert settings.is_local is True
