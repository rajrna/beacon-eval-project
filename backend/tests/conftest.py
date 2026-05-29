"""
Root conftest — shared fixtures for unit, integration, and safety-critical tests.
Integration tests use testcontainers for real Postgres + Redis.
Unit tests mock the DB and external clients.
"""
import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from beacon.core.database import DbSession, get_db
from beacon.core.settings import get_settings
from beacon.main import create_app
from beacon.models import (  # noqa: F401 — ensure all models are registered
    Agent,
    AgentVersion,
    Annotation,
    AuditLog,
    Dataset,
    EvalResult,
    EvalRun,
    Example,
    Institution,
    Judge,
    JudgeVersion,
    ProductionTrace,
    Program,
    ReviewQueueItem,
    User,
)


# ── Event loop ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# ── In-memory SQLite engine (unit tests) ─────────────────────────────────────

# @pytest_asyncio.fixture
# async def sqlite_engine():
#     """Lightweight in-memory SQLite for unit tests (no testcontainers needed)."""
#     engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     yield engine
#     await engine.dispose()


# ── Postgres test engine (uses Docker Postgres) ───────────────────────────────

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async DB session using real Postgres. Each test rolls back on teardown."""
    from beacon.core.settings import get_settings
    settings = get_settings()

    engine = create_async_engine(settings.database_url_str, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


# ── HTTP test client ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with overridden DB dependency."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Mock external clients ─────────────────────────────────────────────────────

@pytest.fixture
def mock_anthropic():
    mock = AsyncMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"score": 0.9, "passed": true, "reasoning": "Good response"}')],
        usage=MagicMock(input_tokens=100, output_tokens=50),
    )
    return mock


@pytest.fixture
def mock_langfuse():
    mock = MagicMock()
    mock.trace.return_value = MagicMock(id=str(uuid.uuid4()))
    return mock


# ── Common entity factories ───────────────────────────────────────────────────

@pytest.fixture
def institution_data() -> dict[str, Any]:
    return {
        "name": "Westbrook State University",
        "accreditor": "HLC",
        "ipeds_id": "999001",
        "slug": "westbrook-state",
    }


@pytest.fixture
def program_data() -> dict[str, Any]:
    return {
        "name": "Online MBA",
        "degree_type": "MBA",
        "format": "online",
        "modality": "async",
        "tuition_per_credit": 750.0,
        "total_credits": 36,
        "term_calendar": "eight-week",
    }


@pytest.fixture
def agent_data() -> dict[str, Any]:
    return {
        "name": "MBA Enrollment Bot",
        "role": "outreach",
        "owner_team": "Enrollment Engineering",
        "owner_email": "eng@westbrook.edu",
    }


@pytest.fixture
def agent_version_data() -> dict[str, Any]:
    return {
        "system_prompt": (
            "You are a helpful enrollment advisor for Westbrook State's Online MBA program. "
            "Answer questions about tuition, admissions requirements, and program structure. "
            "Always be professional, accurate, and empathetic."
        ),
        "model_id": "claude-sonnet-4-5",
        "temperature": 0.0,
        "max_tokens": 1024,
    }


@pytest.fixture
def example_data() -> dict[str, Any]:
    return {
        "query": "How much does the Online MBA cost per credit hour?",
        "expected_behaviors": [
            "State the per-credit tuition accurately",
            "Mention total program cost",
            "Offer to connect with admissions for more details",
        ],
        "prohibited_behaviors": [
            "Give incorrect tuition figures",
            "Make promises about financial aid without verification",
        ],
        "persona": "adult_learner",
        "difficulty": "easy",
        "safety_tags": [],
    }
