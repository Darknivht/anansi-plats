"""
Anansi Test Fixtures — shared across all test modules.

Provides test database (SQLite in-memory), mock Redis (fakeredis),
mock Neo4j, async test client, auth helpers, and sample data factories.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, AsyncIterator, Generator

import fakeredis.aioredis
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.dependencies import get_current_user, CurrentUser
from app.core.events import get_db_session, get_redis, get_neo4j
from app.core.security import (
    create_access_token,
    create_refresh_token,
)
from app.main import create_app

# ─── Force test settings ─────────────────────────────────────────────────────────

# Override to use in-memory SQLite for tests
settings.database.url = "sqlite+aiosqlite:///:memory:"
settings.database.echo = False
settings.redis.url = "redis://localhost:6379/1"
settings.ai.openai_api_key = "test-key"
settings.oauth.google_client_id = "test-google-id"
settings.oauth.google_client_secret = "test-google-secret"
settings.oauth.github_client_id = "test-github-id"
settings.oauth.github_client_secret = "test-github-secret"
settings.payment.stripe_secret_key = "test-stripe-key"
settings.payment.stripe_webhook_secret = "test-webhook-secret"
settings.payment.paystack_secret_key = "test-paystack-key"
settings.storage.endpoint_url = "http://localhost:9000"
settings.storage.access_key_id = "test"
settings.storage.secret_access_key = "test"
settings.storage.bucket = "test-bucket"


# ─── Test Database ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create an in-memory SQLite engine with all tables created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=NullPool,
    )

    # Import all models to ensure they're registered
    from app.models.base import Base
    from app.models.user import User, OAuthAccount, Session
    from app.models.brain import MemoryNode, MemoryLink, DailyNote, MemoryReview
    from app.models.agent import Agent, AgentVersion, BlockDefinition, TriggerDefinition
    from app.models.billing import Subscription, Invoice, Plan
    from app.models.notification import Notification
    from app.models.integration import ConnectorConnection, WebhookEndpoint
    from app.models.marketplace import (
        MarketplaceListing, MarketplaceReview, MarketplaceInstall,
        CreatorAnalytics,
    )
    from app.models.whatsapp import WhatsAppSession, WhatsAppMessage, OTPCode
    from app.models.conversation import Conversation, Message
    from app.models.team import Team, TeamMember

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine) -> AsyncIterator[AsyncSession]:
    """Provide a clean SQLAlchemy session for each test."""
    connection = await test_engine.connect()
    transaction = await connection.begin()

    factory = async_sessionmaker(
        connection, class_=AsyncSession, expire_on_commit=False
    )
    session = factory()

    # Override the get_db_session dependency
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    yield session

    await transaction.rollback()
    await session.close()
    await connection.close()


# ─── Fake Redis ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def test_redis():
    """Provide a fake Redis instance for testing."""
    server = fakeredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield redis
    await redis.aclose()


# ─── Fake Neo4j ──────────────────────────────────────────────────────────────────


class FakeNeo4jResult:
    """A simple fake Neo4j result for testing."""

    def __init__(self, records: list[dict[str, Any]] | None = None):
        self._records = records or [{"ok": 1}]

    async def single(self):
        return self._records[0] if self._records else None

    async def data(self):
        return self._records


class FakeNeo4jSession:
    """A fake Neo4j session for testing."""

    def __init__(self, records: list[dict[str, Any]] | None = None):
        self._records = records

    async def run(self, query: str, **kwargs):
        return FakeNeo4jResult(self._records)

    async def close(self):
        pass


class FakeNeo4jDriver:
    """A fake Neo4j driver for testing."""

    def __init__(self, records: list[dict[str, Any]] | None = None):
        self._records = records

    def session(self, **kwargs):
        return FakeNeo4jSession(self._records)

    async def close(self):
        pass


@pytest_asyncio.fixture
async def test_neo4j():
    """Provide a mock Neo4j driver."""
    driver = FakeNeo4jDriver([{"ok": 1}])
    yield driver


# ─── Async Test Client ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def app(
    test_db: AsyncSession,
    test_redis,
    test_neo4j,
) -> FastAPI:
    """Create a FastAPI app with overridden dependencies."""
    application = create_app()

    # Override all infrastructure dependencies
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield test_db

    def _override_get_redis():
        return test_redis

    def _override_get_neo4j():
        return test_neo4j

    application.dependency_overrides[get_db_session] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    application.dependency_overrides[get_neo4j] = _override_get_neo4j

    return application


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ─── Auth Helpers ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def auth_headers(test_db: AsyncSession) -> dict[str, str]:
    """Generate auth headers for a test user.

    Creates a user in the test DB and returns valid auth headers.
    """
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    await test_db.execute(
        text("""
            INSERT INTO users (id, email, password_hash, display_name, timezone, is_active, created_at, updated_at)
            VALUES (:id, :email, :hash, :name, 'Africa/Lagos', 1, :now, :now)
        """),
        {
            "id": user_id,
            "email": f"test_{user_id[:8]}@example.com",
            "hash": "$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Jq5Jq5Jq5Jq5Jq5Jq5Jq5O",
            "name": "Test User",
            "now": now,
        },
    )
    await test_db.commit()

    access_token = create_access_token(
        user_id,
        extra_claims={
            "email": f"test_{user_id[:8]}@example.com",
            "display_name": "Test User",
            "plan": "free",
            "is_active": True,
            "is_verified": False,
        },
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def auth_headers_pro(test_db: AsyncSession) -> dict[str, str]:
    """Generate auth headers for a pro-plan test user."""
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    await test_db.execute(
        text("""
            INSERT INTO users (id, email, password_hash, display_name, timezone, is_active, plan, created_at, updated_at)
            VALUES (:id, :email, :hash, :name, 'Africa/Lagos', 1, 'pro', :now, :now)
        """),
        {
            "id": user_id,
            "email": f"pro_{user_id[:8]}@example.com",
            "hash": "$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Jq5Jq5Jq5Jq5Jq5Jq5Jq5O",
            "name": "Pro User",
            "now": now,
        },
    )
    await test_db.commit()

    access_token = create_access_token(
        user_id,
        extra_claims={
            "email": f"pro_{user_id[:8]}@example.com",
            "display_name": "Pro User",
            "plan": "pro",
            "is_active": True,
            "is_verified": True,
        },
    )
    return {"Authorization": f"Bearer {access_token}"}


# ─── Sample Data Fixtures ────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def sample_user(test_db: AsyncSession) -> dict[str, Any]:
    """Create a sample user for testing."""
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    await test_db.execute(
        text("""
            INSERT INTO users (id, email, password_hash, display_name, timezone, is_active, plan, is_verified, created_at, updated_at)
            VALUES (:id, :email, :hash, :name, 'Africa/Lagos', 1, 'free', 0, :now, :now)
        """),
        {
            "id": user_id,
            "email": f"sample_{user_id[:8]}@example.com",
            "hash": "$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Jq5Jq5Jq5Jq5Jq5Jq5Jq5O",
            "name": "Sample User",
            "now": now,
        },
    )
    await test_db.commit()

    return {
        "id": user_id,
        "email": f"sample_{user_id[:8]}@example.com",
        "display_name": "Sample User",
        "plan": "free",
        "is_active": True,
    }


@pytest_asyncio.fixture
async def sample_memory_node(
    test_db: AsyncSession,
    sample_user: dict[str, Any],
) -> dict[str, Any]:
    """Create a sample memory node for testing."""
    from app.models.brain import MemoryNode
    node_id = uuid.uuid4()

    node = MemoryNode(
        id=node_id,
        user_id=uuid.UUID(sample_user["id"]),
        type="fact",
        title="Test Memory Node",
        content="This is a test memory node for testing purposes.",
        tags=["#test", "#memory"],
        source="explicit",
        confidence=0.9,
        layers={
            "l1_summary": None,
            "l2_highlights": [],
            "l3_full": "This is a test memory node for testing purposes.",
            "l4_compressed": None,
        },
        review_interval=86400,
        next_review_at=datetime.now(timezone.utc),
        is_orphan=True,
        links_count=0,
    )
    test_db.add(node)
    await test_db.commit()
    await test_db.refresh(node)

    return {
        "id": str(node.id),
        "user_id": str(node.user_id),
        "type": node.type,
        "title": node.title,
        "content": node.content,
        "tags": node.tags,
    }


@pytest_asyncio.fixture
async def sample_agent(
    test_db: AsyncSession,
    sample_user: dict[str, Any],
) -> dict[str, Any]:
    """Create a sample agent definition for testing."""
    from app.models.agent import Agent, BlockDefinition
    agent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    agent = Agent(
        id=agent_id,
        user_id=uuid.UUID(sample_user["id"]),
        name="Test Agent",
        description="A test agent for testing",
        version=1,
        is_active=True,
        metadata_={"framework": "test"},
    )
    test_db.add(agent)
    await test_db.flush()

    # Add a block
    block = BlockDefinition(
        id=uuid.uuid4(),
        agent_id=agent.id,
        block_type="input",
        label="Test Input",
        config={"prompt": "Hello"},
        position_x=100,
        position_y=100,
    )
    test_db.add(block)
    await test_db.commit()

    return {
        "id": str(agent.id),
        "user_id": str(agent.user_id),
        "name": agent.name,
        "version": agent.version,
    }


# ─── Mock Services ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_ai_service(mocker):
    """Mock AI service responses (OpenAI, Anthropic, etc.)."""
    mock = mocker.patch("app.services.brain.MemoryService._generate_embedding")
    mock.return_value = [0.1] * 384
    return mock


@pytest.fixture
def mock_whatsapp_api(mocker):
    """Mock WhatsApp Cloud API calls."""
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"messages": [{"id": "wamid.test"}]}
    return mock_post


@pytest.fixture
def mock_stripe(mocker):
    """Mock Stripe API calls."""
    mock = mocker.patch("stripe.checkout.Session.create")
    mock.return_value = {"id": "cs_test", "url": "https://checkout.stripe.com/test"}
    return mock


@pytest.fixture
def mock_paystack(mocker):
    """Mock Paystack API calls."""
    mock = mocker.patch("httpx.AsyncClient.post")
    mock.return_value.status_code = 200
    mock.return_value.json.return_value = {
        "status": True,
        "data": {"authorization_url": "https://paystack.com/test"},
    }
    return mock
