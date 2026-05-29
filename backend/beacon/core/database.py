from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from beacon.core.settings import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def _create_engine() -> any:  # type: ignore[return]
    settings = get_settings()
    return create_async_engine(
        settings.database_url_str,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        echo=settings.debug,
    )


# Module-level engine and session factory — created once on first import
engine = _create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Annotated type for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
