"""Database initialization and session management.

Provides:
- Async engine creation and disposal
- AsyncSession factory
- get_db dependency for FastAPI
- Neo4j driver setup
"""

from .session import (
    engine,
    async_session_factory,
    get_db,
    init_db,
    close_db,
)
from .neo4j import (
    get_neo4j_driver,
    get_neo4j_session,
    init_neo4j,
    close_neo4j,
)

__all__ = [
    "engine",
    "async_session_factory",
    "get_db",
    "init_db",
    "close_db",
    "get_neo4j_driver",
    "get_neo4j_session",
    "init_neo4j",
    "close_neo4j",
]
