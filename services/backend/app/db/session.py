"""Async PostgreSQL session management with SQLAlchemy 2.0.

Provides:
- Async engine configured via environment variable
- AsyncSession factory with proper configuration
- FastAPI dependency for getting database sessions
- Lifecycle functions (init_db, close_db)

Usage:
    from app.db import get_db

    @router.get("/items")
    async def get_items(db: AsyncSession = Depends(get_db)):
        ...
"""

import os
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.models import Base

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://anansi:anansi@localhost:5432/anansi",
)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    poolclass=NullPool,  # Stateless for serverless compatibility
    pool_pre_ping=True,
    connect_args={
        "command_timeout": 60,
        "server_settings": {
            "application_name": "anansi-api",
        },
    },
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Allow using objects after session commit
    autoflush=False,
)

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession.

    Session is automatically closed when the request finishes.
    Rollback is called if an exception occurs.

    Yields:
        AsyncSession: A database session for the request.
    """
    session: AsyncSession = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

_initialized: bool = False


async def init_db() -> None:
    """Initialize the database.

    Creates all tables defined in the Base metadata.
    For production, use Alembic migrations instead.
    """
    global _initialized

    if _initialized:
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _initialized = True


async def close_db() -> None:
    """Dispose of the database engine connection pool."""
    await engine.dispose()
