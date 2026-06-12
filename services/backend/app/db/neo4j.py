"""Neo4j 5 graph database — async driver setup and session management.

Neo4j handles:
- Bidirectional link traversals (O(1) graph walks)
- Knowledge web queries for the Graph View visualization
- Network analysis (clusters, paths, centrality)
- Spaced repetition scheduling across the graph
- Complex multi-hop relationship queries

Usage:
    from app.db.neo4j import get_neo4j_session, init_neo4j, close_neo4j

    async with get_neo4j_session() as session:
        result = await session.run("MATCH (n) RETURN n LIMIT 10")
        records = await result.data()
"""

import os
import logging
from collections.abc import AsyncGenerator
from typing import Optional

from neo4j import (
    AsyncDriver,
    AsyncGraphDatabase,
    AsyncSession as Neo4jAsyncSession,
    Auth,
    TrustAll,
    TrustSystemCAs,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "anansi-neo4j")
NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")

# Maximum connection pool size
NEO4J_MAX_CONNECTION_POOL_SIZE: int = int(
    os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "50")
)
# Connection acquisition timeout in seconds
NEO4J_CONNECTION_ACQUISITION_TIMEOUT: int = int(
    os.getenv("NEO4J_CONNECTION_ACQUISITION_TIMEOUT", "30")
)
# Maximum lifetime of a connection in seconds
NEO4J_MAX_CONNECTION_LIFETIME: int = int(
    os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", "3600")
)

# ---------------------------------------------------------------------------
# Async Driver
# ---------------------------------------------------------------------------

_driver: Optional[AsyncDriver] = None


async def init_neo4j() -> None:
    """Initialize the Neo4j async driver with connection pooling.

    Called once on application startup.
    """
    global _driver

    if _driver is not None:
        return

    try:
        _driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=Auth.basic(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_pool_size=NEO4J_MAX_CONNECTION_POOL_SIZE,
            connection_acquisition_timeout=NEO4J_CONNECTION_ACQUISITION_TIMEOUT,
            max_connection_lifetime=NEO4J_MAX_CONNECTION_LIFETIME,
            # Enable APOC if available for advanced graph algorithms
            # See: https://neo4j.com/labs/apoc/
        )

        # Verify connectivity
        async with _driver.session(database=NEO4J_DATABASE) as session:
            await session.run("RETURN 1 AS result")

        logger.info(
            "Neo4j connected: %s (db=%s, pool=%d)",
            NEO4J_URI,
            NEO4J_DATABASE,
            NEO4J_MAX_CONNECTION_POOL_SIZE,
        )
    except Exception as exc:
        logger.error("Failed to connect to Neo4j at %s: %s", NEO4J_URI, exc)
        raise


async def close_neo4j() -> None:
    """Close the Neo4j driver and all connections.

    Called once on application shutdown.
    """
    global _driver

    if _driver is None:
        return

    try:
        await _driver.close()
        logger.info("Neo4j driver closed")
    except Exception as exc:
        logger.error("Error closing Neo4j driver: %s", exc)
    finally:
        _driver = None


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


async def get_neo4j_session() -> AsyncGenerator[Neo4jAsyncSession, None]:
    """FastAPI dependency that yields a Neo4j async session.

    The session is automatically closed after use.

    Yields:
        Neo4jAsyncSession: A Neo4j session with managed transaction lifecycle.
    """
    if _driver is None:
        raise RuntimeError(
            "Neo4j driver is not initialized. "
            "Call init_neo4j() before accessing sessions."
        )

    session: Neo4jAsyncSession = _driver.session(
        database=NEO4J_DATABASE,
        # Default access mode is WRITE; use READ for read-only queries
        default_access_mode="WRITE",
    )

    try:
        yield session
    finally:
        await session.close()


def get_neo4j_driver() -> AsyncDriver:
    """Get the global Neo4j async driver instance.

    Raises:
        RuntimeError: If the driver has not been initialized.

    Returns:
        AsyncDriver: The global Neo4j driver.
    """
    if _driver is None:
        raise RuntimeError(
            "Neo4j driver is not initialized. "
            "Call init_neo4j() before accessing the driver."
        )
    return _driver


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


async def run_cypher(
    query: str,
    parameters: Optional[dict] = None,
    database: Optional[str] = None,
) -> list[dict]:
    """Execute a Cypher query and return all records.

    Convenience function for simple queries. Creates and closes
    its own session.

    Args:
        query: The Cypher query string.
        parameters: Optional query parameters.
        database: Override the default database.

    Returns:
        List of record dictionaries.
    """
    driver = get_neo4j_driver()
    async with driver.session(database=database or NEO4J_DATABASE) as session:
        result = await session.run(query, parameters or {})
        records = await result.data()
        return records


async def verify_connection() -> bool:
    """Verify the Neo4j connection is healthy.

    Returns:
        True if the database responds correctly.
    """
    try:
        result = await run_cypher("RETURN 1 AS health")
        return result[0]["health"] == 1
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Second Brain — Neo4j Schema & index initialization
# ---------------------------------------------------------------------------


async def ensure_schema() -> None:
    """Ensure the Neo4j graph schema exists with proper indexes.

    Creates constraints and indexes for the Second Brain knowledge web.
    Should be called once on application startup.
    """
    queries = [
        # Node key constraint for memory nodes
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:MemoryNode) REQUIRE n.id IS UNIQUE",
        # Index on memory node type for filtering
        "CREATE INDEX IF NOT EXISTS FOR (n:MemoryNode) ON (n.type)",
        # Index on memory node tags
        "CREATE INDEX IF NOT EXISTS FOR (n:MemoryNode) ON (n.tags)",
        # Index on memory node creation time
        "CREATE INDEX IF NOT EXISTS FOR (n:MemoryNode) ON (n.created_at)",
        # Index on link type for relationship filtering
        "CREATE INDEX IF NOT EXISTS FOR ()-[r:LINKS_TO]-() ON (r.type)",
        # Index on link strength
        "CREATE INDEX IF NOT EXISTS FOR ()-[r:LINKS_TO]-() ON (r.strength)",
        # Index on link confidence
        "CREATE INDEX IF NOT EXISTS FOR ()-[r:LINKS_TO]-() ON (r.confidence)",
        # Full-text search index on title and content
        "CREATE FULLTEXT INDEX IF NOT EXISTS memory_fulltext FOR (n:MemoryNode) "
        "ON EACH [n.title, n.content]",
        # Index for user nodes
        "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
        # Index for agent nodes
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE",
    ]

    for query in queries:
        try:
            await run_cypher(query)
            logger.debug("Neo4j schema: %s", query[:80])
        except Exception as exc:
            logger.warning("Neo4j schema query failed: %s\n%s", exc, query[:100])

    logger.info("Neo4j schema initialized")
