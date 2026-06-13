# Codebase Structure

**Analysis Date:** 2026-06-13

## Directory Layout

```
anansi-platform/
├── services/                      # Application services (monorepo)
│   ├── frontend/                  # Next.js 16 web application
│   │   ├── src/
│   │   │   ├── app/               # Next.js App Router pages + layouts
│   │   │   │   ├── (app)/         # Authenticated app shell (dashboard, agents, brain, etc.)
│   │   │   │   │   ├── agents/
│   │   │   │   │   ├── billing/
│   │   │   │   │   ├── brain/
│   │   │   │   │   ├── chat/
│   │   │   │   │   ├── dashboard/
│   │   │   │   │   ├── integrations/
│   │   │   │   │   ├── marketplace/
│   │   │   │   │   └── settings/
│   │   │   │   ├── (auth)/        # Login, signup, forgot-password
│   │   │   │   ├── (marketing)/   # Landing page
│   │   │   │   ├── globals.css
│   │   │   │   └── layout.tsx     # Root HTML layout
│   │   │   ├── components/        # React components by domain
│   │   │   │   ├── billing/       # PlanCard, PlanComparison
│   │   │   │   ├── brain/         # MemoryGraph, MemoryDetail, ReviewCard
│   │   │   │   ├── features/      # ActivityFeed, AIThread, MorningBriefing, QuickStats
│   │   │   │   ├── integrations/  # ConnectorCard, OAuthModal
│   │   │   │   ├── layout/        # Sidebar, SidebarItem, TopBar
│   │   │   │   ├── marketplace/   # ListingCard, InstallModal, ReviewSection
│   │   │   │   ├── ui/           # AnansiButton, Badge, GlassCard, Input, Modal, Toast, etc.
│   │   │   │   ├── whatsapp/     # WhatsAppDemo
│   │   │   │   └── workshop/     # AgentTestPanel, BlockConfigPanel, BlockPalette, CanvasNode, TemplateSelector
│   │   │   ├── hooks/            # Custom React hooks
│   │   │   │   └── useWebSocket.ts
│   │   │   ├── lib/              # API client and utilities
│   │   │   │   ├── api.ts        # HTTP client with auth + retry
│   │   │   │   └── utils.ts      # Shared utility functions
│   │   │   ├── stores/           # Zustand state stores
│   │   │   │   ├── billing.ts
│   │   │   │   ├── brain.ts
│   │   │   │   ├── chat.ts
│   │   │   │   ├── integrations.ts
│   │   │   │   ├── marketplace.ts
│   │   │   │   ├── ui.ts
│   │   │   │   └── workshop.ts
│   │   │   └── types/            # TypeScript type definitions
│   │   │       └── index.ts
│   │   ├── tests/                # Vitest unit/integration tests
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── vitest.config.ts
│   │   └── package.json
│   │
│   ├── backend/                  # FastAPI Python backend
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── __init__.py       # Versions aggregator
│   │   │   │   └── v1/               # API v1 endpoints
│   │   │   │       ├── __init__.py   # Router aggregator
│   │   │   │       ├── agents.py
│   │   │   │       ├── auth.py
│   │   │   │       ├── billing.py
│   │   │   │       ├── brain.py
│   │   │   │       ├── integrations.py
│   │   │   │       ├── marketplace.py
│   │   │   │       ├── notifications.py
│   │   │   │       ├── users.py
│   │   │   │       └── whatsapp.py
│   │   │   ├── connectors/           # External API integrations (17 connectors)
│   │   │   │   ├── base.py           # BaseConnector abstract class
│   │   │   │   ├── discord.py / github.py / gmail.py / google_*.py
│   │   │   │   ├── linear.py / notion.py / outlook.py / paystack.py
│   │   │   │   ├── slack.py / stripe.py / telegram.py / twitter.py
│   │   │   │   └── whatsapp.py
│   │   │   ├── core/                 # Cross-cutting infrastructure
│   │   │   │   ├── config.py         # Pydantic Settings (all sub-settings)
│   │   │   │   ├── dependencies.py   # FastAPI Depends: auth, rate-limit, plan
│   │   │   │   ├── events.py         # Lifespan: DB/Redis/Neo4j connect/disconnect
│   │   │   │   ├── exceptions.py     # Error hierarchy + handlers
│   │   │   │   └── security.py       # Password hashing, JWT, rate limiter
│   │   │   ├── db/                   # Database session management
│   │   │   │   ├── neo4j.py
│   │   │   │   └── session.py
│   │   │   ├── models/               # SQLAlchemy ORM models
│   │   │   │   ├── base.py           # Base, UUIDMixin, TimestampMixin
│   │   │   │   ├── agent.py / billing.py / brain.py
│   │   │   │   ├── conversation.py / integration.py / marketplace.py
│   │   │   │   ├── notification.py / team.py / user.py / whatsapp.py
│   │   │   │   └── __init__.py       # All models re-exported
│   │   │   ├── services/             # Business logic layer
│   │   │   │   ├── agent.py / auth.py / billing.py / brain.py
│   │   │   │   ├── blocks.py / creator.py / dailynote.py
│   │   │   │   ├── execution.py / graph.py / integration.py / linking.py
│   │   │   │   ├── marketplace.py / notification.py / review.py
│   │   │   │   ├── summarization.py / trigger.py / user.py / webhook.py
│   │   │   │   └── whatsapp*.py      # 4 WhatsApp service files
│   │   │   ├── tasks/                # Celery task definitions
│   │   │   │   ├── agent_tasks.py
│   │   │   │   └── whatsapp_tasks.py
│   │   │   ├── websocket/            # WebSocket infrastructure
│   │   │   │   ├── handler.py        # WS endpoint + message loop
│   │   │   │   └── manager.py        # Connection manager + event routing
│   │   │   └── main.py               # FastAPI app factory
│   │   ├── migrations/               # Database migration scripts
│   │   ├── tests/                    # Pytest test suite
│   │   └── requirements.txt
│   │
│   └── worker/                   # Celery worker (tasks defined in backend)
│       ├── tasks/                # Currently empty directory
│       └── requirements.txt
│
├── infra/                        # Infrastructure configuration
│   ├── ci/
│   │   └── .github/workflows/    # GitHub Actions CI/CD
│   │       └── deploy.yml
│   └── docker/
│       ├── docker-compose.yml    # Full dev stack: postgres, neo4j, redis, api, web, worker
│       ├── Dockerfile.api / Dockerfile.api.dev
│       ├── Dockerfile.web / Dockerfile.web.dev
│       └── Dockerfile.worker
│
├── tests/                        # E2E tests
│   └── e2e/
│       ├── playwright.config.ts
│       ├── agent.spec.ts
│       ├── auth.spec.ts
│       ├── brain.spec.ts
│       └── marketplace.spec.ts
│
├── docs/                         # Project documentation
│   ├── COMPLETION.md
│   └── TEAM.md
│
├── anansi-frontend-fix/          # Patch tar extraction (temporary)
├── api-fix/                      # Patch tar extraction (temporary)
├── .planning/                    # GSD planning artifacts
├── package.json                  # Root workspace package.json
├── tsconfig.base.json            # Shared TypeScript config
├── .eslintrc.json                # ESLint configuration
├── .prettierrc                   # Prettier configuration
├── docker-compose.yml            # Root docker-compose (likely reference)
├── dockerignore
├── .env.example
└── README.md
```

## Directory Purposes

**`services/frontend/src/app/`:**
- Purpose: Next.js App Router pages with route group layouts
- Contains: Route group directories `(app)`, `(auth)`, `(marketing)`, each with their own `layout.tsx`; individual page files
- Key files: `layout.tsx` (root HTML layout), `(app)/layout.tsx` (authenticated shell with Sidebar/TopBar), `(marketing)/page.tsx` (landing)

**`services/frontend/src/components/`:**
- Purpose: React components organized by domain
- Contains: 9 subdirectories (billing, brain, features, integrations, layout, marketplace, ui, whatsapp, workshop) with component files
- Naming: PascalCase component files (e.g., `MemoryGraph.tsx`, `ToastContainer` lives in `Toast.tsx`)

**`services/frontend/src/stores/`:**
- Purpose: Zustand state management stores
- Contains: 7 store files, one per domain (billing, brain, chat, integrations, marketplace, ui, workshop)
- Pattern: Single `create<State>()` call per file; state + actions defined together; async actions call `api.*` directly

**`services/frontend/src/lib/`:**
- Purpose: Shared utilities — HTTP client and helper functions
- Contains: `api.ts` (fetch wrapper with auth refresh/retry/error handling), `utils.ts` (shared helpers including `cn()` classname merger, `generateId()`)

**`services/backend/app/core/`:**
- Purpose: Cross-cutting infrastructure shared across all backend modules
- Contains: Config (pydantic-settings), dependencies (FastDI Depends), events (lifespan), exceptions (error hierarchy), security (auth/rate-limit)
- Key files: `config.py` (single `Settings` object aggregating all sub-settings), `events.py` (singleton DB/Redis/Neo4j connections)

**`services/backend/app/connectors/`:**
- Purpose: Pluggable external service integrations
- Contains: Abstract `BaseConnector` class + 17 concrete implementations
- Pattern: Each connector extends `BaseConnector`, defines `key`, `name`, `auth_type`, `test_connection()`

**`services/backend/app/services/`:**
- Purpose: Business logic — all domain operations
- Contains: 23 service modules covering agents, brain, auth, billing, integrations, etc.
- Pattern: Stateless service classes; methods create their own DB sessions via `get_session_factory()`

**`infra/docker/`:**
- Purpose: Container definitions for all services + supporting infrastructure
- Contains: Docker Compose file defining 8 services (postgres, neo4j, redis, meilisearch, minio, api, web, worker, flower); separate Dockerfiles for dev/prod

**`tests/e2e/`:**
- Purpose: End-to-end browser tests
- Contains: Playwright config + 4 spec files (agent, auth, brain, marketplace)

## Key File Locations

**Entry Points:**
- `services/backend/app/main.py`: FastAPI application factory and uvicorn entry point
- `services/frontend/src/app/layout.tsx`: Root Next.js layout
- `infra/docker/docker-compose.yml`: Service orchestration definition

**Configuration:**
- `services/backend/app/core/config.py`: All backend settings (pydantic-settings), environment-based
- `services/frontend/next.config.ts`: Next.js configuration (turbopack, images, security headers, redirects)
- `services/frontend/tailwind.config.ts`: Tailwind CSS v4 configuration
- `services/frontend/vitest.config.ts`: Frontend test configuration
- `tsconfig.base.json`: Shared TypeScript configuration with path aliases
- `.eslintrc.json`: ESLint configuration
- `.prettierrc`: Prettier formatting configuration

**Core Logic:**
- `services/backend/app/services/agent.py`: Agent CRUD, validation, versioning, publishing
- `services/backend/app/services/brain.py`: Memory node CRUD, embeddings, auto-linking, spaced repetition
- `services/backend/app/services/execution.py`: Agent execution engine with DAG traversal
- `services/backend/app/connectors/base.py`: Abstract integration connector framework
- `services/backend/app/websocket/manager.py`: Real-time event system
- `services/frontend/src/lib/api.ts`: Frontend HTTP client
- `services/frontend/src/types/index.ts`: All TypeScript domain types

**Testing:**
- `services/backend/tests/`: Pytest suite (10 test files mirroring API routes)
- `services/frontend/tests/`: Vitest suite (components/, lib/, stores/)
- `tests/e2e/`: Playwright E2E specs

## Naming Conventions

**Files:**
- **TypeScript/React:** PascalCase for components (`MemoryGraph.tsx`, `Sidebar.tsx`, `AnansiButton.tsx`), camelCase for utilities (`api.ts`, `utils.ts`, `useWebSocket.ts`)
- **Store files:** camelCase matching domain (`brain.ts`, `marketplace.ts`, `ui.ts`)
- **Python:** snake_case throughout (`agent.py`, `base.py`, `dependencies.py`, `websocket/`)
- **Backend API files:** snake_case matching the resource they expose (`agents.py`, `brain.py`, `integrations.py`)

**Directories:**
- **Frontend:** Lowercase domain names for route groups (`(app)/agents/`, `(auth)/login/`)
- **Components:** Lowercase domain subdirectories (`billing/`, `brain/`, `features/`, `ui/`)
- **Backend:** Lowercase single-word directories (`api/`, `core/`, `db/`, `models/`, `services/`)

**Functions:**
- **TypeScript:** camelCase for functions and methods (`loadGraph()`, `toggleSidebar()`, `setAccessToken()`)
- **Python:** snake_case for functions and methods (`create_agent()`, `validate_agent()`, `_serialize()`)

**Types:**
- **TypeScript:** PascalCase for interfaces and types (`MemoryNode`, `WSEvent`, `Toast`, `AgentDefinition`)
- **Python:** PascalCase for classes (`AgentService`, `MemoryService`, `BaseConnector`, `TokenBucketRateLimiter`)

## Where to Add New Code

**New Feature (Backend):**
- API endpoint: `services/backend/app/api/v1/` — create new file or add to existing resource file
- Business logic: `services/backend/app/services/` — create new service file
- ORM model: `services/backend/app/models/` — create new model file
- Register in: `models/__init__.py`, `api/v1/__init__.py`
- Tests: `services/backend/tests/`

**New Feature (Frontend):**
- Page route: `services/frontend/src/app/(app)/` — create route group directory with `page.tsx`
- Component: `services/frontend/src/components/<domain>/` — create `.tsx` file
- Store: `services/frontend/src/stores/` — create new store file
- Type: `services/frontend/src/types/index.ts` — add interface
- Tests: `services/frontend/tests/`

**New Connector / Integration:**
- Implementation: `services/backend/app/connectors/` — extend `BaseConnector`
- API endpoint: `services/backend/app/api/v1/integrations.py`
- Frontend component: `services/frontend/src/components/integrations/`
- Frontend store: `services/frontend/src/stores/integrations.ts`

**New Background Task:**
- Task definition: `services/backend/app/tasks/` — create new task file
- Worker config: `infra/docker/docker-compose.yml` — if new worker type needed

**New Infrastructure:**
- Dockerfile: `infra/docker/`
- CI workflow: `infra/ci/.github/workflows/`
- Docker Compose service: `infra/docker/docker-compose.yml`

## Special Directories

**`services/worker/tasks/`:**
- Purpose: Intended for Celery task files separate from backend
- Generated: No (manual creation expected)
- Committed: Yes (currently empty)

**`anansi-frontend-fix/` and `api-fix/`:**
- Purpose: Temporary patch tar extraction directories (from `.tar.gz` artifacts)
- Generated: Yes (from tar extraction)
- Committed: Yes, but temporary — should be cleaned up

**`migrations/`:**
- Purpose: Alembic database migration scripts
- Location: `services/backend/migrations/`
- Generated: Yes (by Alembic)
- Committed: Yes

---

*Structure analysis: 2026-06-13*
