"""
Anansi Events — Application lifecycle (startup / shutdown) event handlers.

Connects and disconnects from PostgreSQL, Redis, Neo4j, and other infrastructure.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import AsyncIterator

from neo4j import AsyncGraphDatabase
from pydantic import AnyHttpUrl
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


# ─── Module-level globals (set during startup) ───────────────────────────────────

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis_client: Redis | None = None
_neo4j_driver: AsyncGraphDatabase.driver | None = None


# ─── Database ────────────────────────────────────────────────────────────────────


async def connect_database() -> AsyncEngine:
    """Create and test the async SQLAlchemy engine (PostgreSQL + pgvector).

    Returns:
        Configured AsyncEngine instance.
    """
    global _engine, _session_factory

    logger.info("Connecting to database", url=settings.database.url)
    _engine = create_async_engine(
        settings.database.url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_pre_ping=settings.database.pool_pre_ping,
        echo=settings.database.echo,
        connect_args={
            "timeout": settings.database.connect_timeout,
            "ssl": settings.database.ssl_mode if settings.database.ssl_mode != "prefer" else None,
        },
    )

    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    # Verify connectivity
    try:
        async with _engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection failed", error=str(exc))
        raise

    return _engine


async def disconnect_database() -> None:
    """Dispose of the database engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connection closed")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the async session factory (must be initialised during startup).

    Returns:
        Session factory for creating AsyncSession instances.
    """
    if _session_factory is None:
        raise RuntimeError("Database session factory not initialised. Call connect_database() first.")
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession for dependency injection (FastAPI Depends)."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ─── Redis ───────────────────────────────────────────────────────────────────────


async def connect_redis() -> Redis:
    """Create and verify a Redis connection.

    Returns:
        Redis client instance.
    """
    global _redis_client

    logger.info("Connecting to Redis", url=settings.redis.url)
    _redis_client = Redis.from_url(
        settings.redis.url,
        socket_timeout=settings.redis.socket_timeout,
        socket_connect_timeout=settings.redis.socket_connect_timeout,
        retry_on_timeout=settings.redis.retry_on_timeout,
        max_connections=settings.redis.max_connections,
        health_check_interval=settings.redis.health_check_interval,
        decode_responses=settings.redis.decode_responses,
    )

    try:
        await _redis_client.ping()
        logger.info("Redis connection verified")
    except Exception as exc:
        logger.error("Redis connection failed", error=str(exc))
        raise

    return _redis_client


async def disconnect_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> Redis:
    """Get the Redis client singleton.

    Returns:
        Redis client instance.
    """
    if _redis_client is None:
        raise RuntimeError("Redis not initialised. Call connect_redis() first.")
    return _redis_client


# ─── Neo4j ───────────────────────────────────────────────────────────────────────


async def connect_neo4j() -> AsyncGraphDatabase.driver:
    """Create and verify a Neo4j driver (graph database for the Second Brain).

    Returns:
        Async Neo4j driver instance.
    """
    global _neo4j_driver

    logger.info("Connecting to Neo4j", url=settings.neo4j.url)
    _neo4j_driver = AsyncGraphDatabase.driver(
        settings.neo4j.url,
        auth=(settings.neo4j.user, settings.neo4j.password),
        max_connection_pool_size=settings.neo4j.max_connection_pool_size,
        connection_acquisition_timeout=settings.neo4j.connection_acquisition_timeout,
        max_transaction_retry_time=settings.neo4j.max_transaction_retry_time,
    )

    try:
        async with _neo4j_driver.session(database=settings.neo4j.database) as session:
            result = await session.run("RETURN 1 AS ok")
            record = await result.single()
            if record and record.get("ok") == 1:
                logger.info("Neo4j connection verified")
    except Exception as exc:
        logger.error("Neo4j connection failed", error=str(exc))
        raise

    return _neo4j_driver


async def disconnect_neo4j() -> None:
    """Close the Neo4j driver."""
    global _neo4j_driver
    if _neo4j_driver:
        await _neo4j_driver.close()
        _neo4j_driver = None
        logger.info("Neo4j connection closed")


def get_neo4j() -> AsyncGraphDatabase.driver:
    """Get the Neo4j driver singleton.

    Returns:
        Neo4j async driver instance.
    """
    if _neo4j_driver is None:
        raise RuntimeError("Neo4j not initialised. Call connect_neo4j() first.")
    return _neo4j_driver


# ─── Application lifespan (used in main.py) ──────────────────────────────────────


@asynccontextmanager
async def lifespan(app: "FastAPI") -> AsyncIterator[None]:  # type: ignore[name-defined]  # noqa: F821
    """FastAPI lifespan context manager — startup and shutdown.

    Usage in ``main.py``:
        app = FastAPI(lifespan=lifespan, ...)
    """
    from app.core.security import init_rate_limiter

    logger.info("Anansi starting up...", environment=settings.app.environment)

    # ── Startup ──
    try:
        await connect_database()
    except Exception:
        logger.exception("Database startup failed — continuing without DB for now")

    try:
        await connect_redis()
    except Exception:
        logger.exception("Redis startup failed — continuing without Redis for now")
        # In development we can limp along without Redis

    try:
        await connect_neo4j()
    except Exception:
        logger.exception("Neo4j startup failed — continuing without Neo4j for now")

    # Initialise rate limiter (depends on Redis)
    if _redis_client is not None:
        init_rate_limiter(_redis_client)
        logger.info("Rate limiter ready")
    else:
        logger.warning("Rate limiter not available (no Redis)")

    logger.info(
        "Anansi started successfully",
        version=settings.app.version,
        environment=settings.app.environment,
    )

    yield  # ── App is running ──

    # ── Shutdown ──
    logger.info("Anansi shutting down...")
    await disconnect_neo4j()
    await disconnect_redis()
    await disconnect_database()
    logger.info("Anansi shut down complete")


__all__ = [
    "lifespan",
    "get_db_session",
    "get_session_factory",
    "get_redis",
    "get_neo4j",
    "connect_database",
    "connect_redis",
    "connect_neo4j",
    "disconnect_database",
    "disconnect_redis",
    "disconnect_neo4j",
]
