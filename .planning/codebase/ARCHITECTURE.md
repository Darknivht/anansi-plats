<!-- refreshed: 2026-06-13 -->
# Architecture

**Analysis Date:** 2026-06-13

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                      │
│  Next.js 16 App (services/frontend/)                                     │
│  ├── app/          (Route groups: (app), (auth), (marketing))            │
│  ├── components/   (UI, layout, domain-specific components)             │
│  ├── hooks/        (Custom React hooks)                                  │
│  ├── stores/       (Zustand state stores)                                │
│  ├── lib/          (API client, utilities)                               │
│  └── types/        (TypeScript type definitions)                         │
├──────────────────────┤                      ├────────────────────────────┤
│         HTTP REST (api.ts)                  WebSocket (useWebSocket.ts)  │
│         /api/v1/*                           /ws/v1                       │
└──────────────────────┬──────────────────────┬────────────────────────────┘
                       │                      │
                       ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                                 │
│  services/backend/app/                                                   │
│  ├── main.py         (App factory, middleware, health check)             │
│  ├── api/v1/         (REST endpoints: agents, auth, billing, brain,     │
│  │                     integrations, marketplace, notifications,        │
│  │                     users, whatsapp)                                  │
│  ├── websocket/      (WebSocket handler + connection manager)            │
│  ├── core/           (Config, dependencies, exceptions, security,        │
│  │                     events/lifespan)                                  │
│  ├── services/       (Business logic layer: agent, brain, auth, etc.)   │
│  ├── models/         (SQLAlchemy ORM models)                             │
│  ├── connectors/     (External API integrations: Discord, Gmail,        │
│  │                     GitHub, Notion, Slack, Stripe, etc.)             │
│  ├── db/             (PostgreSQL session management)                     │
│  └── tasks/          (Celery async task definitions)                     │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE LAYER                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │PostgreSQL│  │  Redis   │  │  Neo4j   │  │MinIO/S3  │  │Meilisearch│ │
│  │+pgvector │  │ Cache/Q  │  │Graph DB  │  │ Storage  │  │ Full-text │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └───────────┘ │
│                                                                          │
│  ┌──────────┐  ┌──────────┐                                             │
│  │ Celery   │  │  Flower  │                                             │
│  │ Worker   │  │ Monitor  │                                             │
│  └──────────┘  └──────────┘                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| App Factory | Creates and configures FastAPI app with middleware, routers, lifespan | `services/backend/app/main.py` |
| API v1 Router | Aggregates all v1 REST endpoint routers under /api/v1 | `services/backend/app/api/v1/__init__.py` |
| Core Config | Pydantic Settings loading from env/.env — all config sections | `services/backend/app/core/config.py` |
| Dependencies | FastAPI dependency injection (auth, rate-limit, plan-gate) | `services/backend/app/core/dependencies.py` |
| Exceptions | Standardized error hierarchy + FastAPI handler registration | `services/backend/app/core/exceptions.py` |
| Security | Password hashing (bcrypt), JWT (RS256), token-bucket rate limiter | `services/backend/app/core/security.py` |
| Events | App lifespan: connect/disconnect PostgreSQL, Redis, Neo4j | `services/backend/app/core/events.py` |
| ORM Models | Base, UUIDMixin, TimestampMixin; all domain models | `services/backend/app/models/` |
| Business Services | CRUD + domain logic for agents, brain, auth, billing, etc. | `services/backend/app/services/` |
| Connectors | Abstract BaseConnector + 17 external service implementations | `services/backend/app/connectors/` |
| WebSocket Handler | JWT-authenticated WS endpoint, message routing, handler registry | `services/backend/app/websocket/handler.py` |
| WebSocket Manager | Connection tracking, broadcast, heartbeat, event builders | `services/backend/app/websocket/manager.py` |
| Frontend Layout | Root layout, app shell (Sidebar/TopBar), auth pages, marketing | `services/frontend/src/app/` |
| Frontend Stores | Zustand stores: ui, brain, chat, billing, integrations, etc. | `services/frontend/src/stores/` |
| API Client | Fetch-based client with auto-refresh, retry, error handling | `services/frontend/src/lib/api.ts` |
| E2E Tests | Playwright specs: auth, brain, agent, marketplace | `tests/e2e/` |

## Pattern Overview

**Overall:** Modular monolith with three microservices (frontend, API, worker) deployed as separate containers.

**Key Characteristics:**
- **Frontend:** Next.js 16 App Router with route groups (`(app)`, `(auth)`, `(marketing)`) for layout scoping
- **Backend:** FastAPI with factory pattern (`create_app()`), versioned API (`/api/v1/*`), dependency injection for auth/rate-limit/plan-gating
- **Data access:** Repository-style services layer — `services/` own all ORM queries, API endpoints delegate to services
- **State management:** Zustand stores on frontend, async with `api` client calls inside store actions
- **Database:** SQLAlchemy 2.0 async with pgvector, plus Neo4j for knowledge graph
- **Background work:** Celery with Redis broker for async agent execution
- **Real-time:** WebSocket via FastAPI native WebSocket support, JWT auth via query param
- **Integrations:** Pluggable connector pattern with abstract `BaseConnector` class

## Layers

**Client Layer (Frontend):**
- Purpose: Browser UI rendered by Next.js 16 (React 19)
- Location: `services/frontend/src/`
- Contains: App routes, React components, Zustand stores, API client, hooks, type definitions
- Depends on: Backend API via HTTP REST (`lib/api.ts`) and WebSocket (`hooks/useWebSocket.ts`)
- Used by: End users via browser

**API Layer (Backend):**
- Purpose: HTTP REST + WebSocket server, business logic, data access
- Location: `services/backend/app/`
- Contains: FastAPI app factory, routers, services, models, connectors, WebSocket handler
- Depends on: PostgreSQL, Redis, Neo4j, S3 storage, Meilisearch
- Used by: Frontend, third-party API consumers, webhooks

**Worker Layer (Background Tasks):**
- Purpose: Async task processing via Celery
- Location: `services/worker/tasks/` (currently empty — tasks defined in `services/backend/app/tasks/`)
- Depends on: Redis (broker), backend code
- Used by: Agent execution engine, scheduled tasks

**Infrastructure Layer:**
- Purpose: Data stores, message broker, object storage, search
- Defined in: `infra/docker/docker-compose.yml`
- Contains: PostgreSQL 16 + pgvector, Neo4j 5, Redis 7, MinIO/S3, Meilisearch, Celery Flower

## Data Flow

### Primary Request Path (REST API)

1. **Request arrives** at FastAPI (`services/backend/app/main.py:90`)
2. **Middleware chain** processes: Request ID injection → CORS → Response time tracking → Rate-limit headers (`main.py:39-84`)
3. **Router dispatches** to v1 endpoint — e.g., `GET /api/v1/agents` → `api/v1/agents.py:54`
4. **Dependency injection** resolves auth (`get_current_user` in `core/dependencies.py:79`), rate limiting, plan gating
5. **Service call** — e.g., `agent_service.list_agents()` in `services/agent.py:98`
6. **Service queries DB** via session factory from `core/events.py`, returns serialized dict
7. **Response returned** as JSON dict/object through FastAPI serialization

### WebSocket Flow

1. Client opens connection to `wss://api.anansi.ai/ws/v1?token=<jwt>` (`websocket/handler.py:59`)
2. JWT verified; connection accepted and registered with `WebSocketManager` (`websocket/manager.py:61`)
3. Welcome event sent, message loop starts (`handler.py:135`)
4. Client sends `{"type": "ai.send_message", "payload": {...}}`
5. Handler dispatches to registered handler via `manager.handle_client_event()` (`manager.py:240`)
6. Server streams responses back via `manager.send_to_user()` (`manager.py:169`)

### Agent Execution Flow

1. REST endpoint `POST /agents/{id}/run` triggers execution (`api/v1/agents.py:129`)
2. `execution_engine.run_agent()` creates `AgentRun` record, prepares `ExecutionContext` (`services/execution.py`)
3. Blocks are executed in topological order via DAG traversal
4. Real-time status streamed via WebSocket (`manager.event_agent_running/completed/error`)
5. Results and memory impact recorded; async variant queues via Celery (`services/tasks/agent_tasks.py`)

**State Management:**
- Frontend: Zustand stores (`stores/`) hold all client state. Actions call `api.*` methods directly inside store actions. No Redux or React Query.
- Backend: Stateless request handling. Session-per-request via `get_db_session()` dependency. Module-level singletons for Redis client, Neo4j driver, rate limiter (`core/events.py`, `core/security.py`).

## Key Abstractions

**BaseConnector** (`services/backend/app/connectors/base.py`):
- Purpose: Abstract base for all external service integrations (OAuth2, API key, Basic auth)
- Examples: `connectors/gmail.py`, `connectors/slack.py`, `connectors/stripe.py`, `connectors/notion.py` (17 total implementations)
- Pattern: Template method with abstract `test_connection()`, shared OAuth helpers (`exchange_code`, `refresh_token`, `revoke_token`)

**AgentService** (`services/backend/app/services/agent.py`):
- Purpose: CRUD, validation, versioning, publishing, duplication of agents
- Pattern: Stateless service class, each method opens its own session via `get_session_factory()`

**MemoryService** (`services/backend/app/services/brain.py`):
- Purpose: Second Brain memory management — CRUD for memory nodes, vector embeddings, auto-linking, spaced repetition review, semantic search
- Pattern: Service class with lazy OpenAI client, pgvector for embeddings, WebSocket broadcasting on mutations

**ExecutionEngine** (`services/backend/app/services/execution.py`):
- Purpose: Agent execution orchestrator — DAG traversal, block execution, error handling, result broadcasting
- Pattern: `ExecutionContext` object passed through block chain, topological sort for execution order

**WebSocketManager** (`services/backend/app/websocket/manager.py`):
- Purpose: Singleton managing all active WS connections, event routing, broadcasting
- Pattern: Pub-sub with decorator-based handler registration (`@manager.on("event_type")`)

**Zustand Stores** (`services/frontend/src/stores/`):
- Purpose: Client-side state management for UI, brain, chat, billing, integrations, marketplace, workshop
- Pattern: `create<State>()` with state + actions in a single object. Actions are async and call `api.*` directly.

**API Client** (`services/frontend/src/lib/api.ts`):
- Purpose: Fetch-based HTTP client with JWT auto-refresh, exponential-backoff retry on 5xx, structured error handling
- Pattern: Singleton `api` object with `.get()/.post()/.put()/.patch()/.delete()` methods

## Entry Points

**FastAPI Application:**
- Location: `services/backend/app/main.py`
- Triggers: `uvicorn app.main:app` (production via Dockerfile.api)
- Responsibilities: App factory, middleware stack, router registration, health check, lifespan management

**Next.js Application:**
- Location: `services/frontend/src/app/layout.tsx`
- Triggers: `next dev` / `next start` (development / production via Dockerfile.web)
- Responsibilities: Root HTML layout, font loading, metadata/SEO, global CSS

**Celery Worker:**
- Location: `services/backend/app/tasks/agent_tasks.py`
- Triggers: `celery -A app.tasks worker` (via docker-compose worker service)
- Responsibilities: Async agent execution, WhatsApp notification processing

**Playwright E2E Tests:**
- Location: `tests/e2e/playwright.config.ts`
- Triggers: `npx playwright test`
- Responsibilities: Auth flows, agent builder, brain graph, marketplace browsing

## Architectural Constraints

- **Threading:** Single-threaded async event loop (asyncio) for FastAPI backend. Celery workers use multiprocessing (concurrency=2 in compose). Worker tasks use SQLAlchemy async sessions.
- **Global state:** Module-level singletons exist in `core/events.py` (`_engine`, `_session_factory`, `_redis_client`, `_neo4j_driver`) and `core/security.py` (`_rate_limiter_instance`, `_RSA_PRIVATE_KEY`, `_RSA_PUBLIC_KEY`). `websocket/manager.py` has a singleton `manager`.
- **Circular imports:** Mitigated by deferred imports inside endpoint handlers (e.g., `from app.services.blocks import block_registry` inside route functions) and by importing models in `models/__init__.py` after definition.
- **API versioning:** All endpoints under `/api/v1/*` with versioned router aggregation in `api/__init__.py` (currently only v1). WebSocket at `/ws/v1`.

## Anti-Patterns

### Module-Level Singletons in events.py

**What happens:** `core/events.py` uses global module variables (`_engine`, `_session_factory`, `_redis_client`, `_neo4j_driver`) set during lifespan startup and accessed via getter functions. Same pattern in `core/security.py` for rate limiter.
**Why it's wrong:** These cannot be easily swapped for testing; tests that need different DB/Redis instances must monkey-patch module globals.
**Do this instead:** Consider FastAPI's `app.state` or a dependency provider pattern. See `core/config.py` which cleanly uses pydantic-settings without globals.

### Services Create Their Own Sessions

**What happens:** Service methods (e.g., `AgentService.list_agents()` at `services/agent.py:98`) always call `get_session_factory()` and create their own session, never accepting one as a parameter.
**Why it's wrong:** Prevents transactional composition across multiple service calls. If two services must run in the same DB transaction, there is no way to pass a shared session.
**Do this instead:** Accept an optional `session: AsyncSession` parameter for callers who need transactional control, falling back to creating a new session when none is provided.

### Inline Validation Functions in API Handlers

**What happens:** `api/v1/agents.py` defines `_validate_uuid()` as a module-level helper instead of using Pydantic path parameter validation.
**Why it's wrong:** Duplicated validation logic; every endpoint re-validates UUIDs manually.
**Do this instead:** Use `Path(..., pattern="...")` validation or a Pydantic model for path/query parameters.

## Error Handling

**Strategy:** Custom exception hierarchy rooted in `AnansiError` (`core/exceptions.py`), with standardized JSON error format. FastAPI exception handlers registered for AnansiError, HTTPException, and generic Exception.

**Patterns:**
- All custom exceptions have `code`, `status_code`, `message`, `details`, `links`, `request_id` fields
- `anansi_exception_handler()` returns structured `{"error": {...}}` JSON responses
- `http_exception_handler()` converts FastAPI HTTPException to same format
- `unhandled_exception_handler()` catch-all returns 500 with request_id
- Services raise `NotFoundError`, `ValidationError`, `ConflictError` as appropriate
- Rate limiting raises `RateLimitError` with `retry_after_seconds`

## Cross-Cutting Concerns

**Logging:** Structured logging via `structlog` throughout backend. Request ID middleware adds correlation IDs. JSON format in production, console in dev.

**Validation:** Inline validation in API handlers (e.g., `_validate_uuid`), service-level validation (e.g., `AgentService.validate_agent()` does DAG cycle detection), and Pydantic schema validation for some request bodies.

**Authentication:** JWT (RS256, 2048-bit RSA) with access tokens (15 min) and refresh tokens (7 days). OAuth via Google and GitHub. Password auth via bcrypt (cost 12). WebSocket auth via JWT query parameter.

**Rate Limiting:** Redis-backed token-bucket algorithm. Tiered by plan (free/pro/business). Fail-open on Redis outage.

**CORS:** Whitelist-based CORS middleware for `anansi.ai` domains and `localhost:3000`.

---

*Architecture analysis: 2026-06-13*
