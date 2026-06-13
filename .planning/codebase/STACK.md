# Technology Stack

**Analysis Date:** 2026-06-13

## Languages

**Primary:**
- Python 3.13+ — Backend API (`services/backend/`), background worker (`services/worker/`)
- TypeScript 5.7+ — Frontend (`services/frontend/`), E2E tests (`tests/e2e/`)
- SQL — PostgreSQL migration scripts (`services/backend/migrations/`)
- Cypher — Neo4j graph queries (`services/backend/app/db/neo4j.py`)

**Secondary:**
- JavaScript (ES2022) — root-level `package.json` scripts
- YAML — Docker Compose (`docker-compose.yml`, `infra/docker/docker-compose.yml`), CI/CD (`infra/ci/.github/workflows/deploy.yml`)
- CSS — Tailwind CSS v4 with PostCSS (`services/frontend/src/app/globals.css`)
- Markdown — Project docs (`README.md`)

## Runtime

**Environment:**
- Node.js >=22.0.0 (npm >=10.0.0) — Frontend runtime, build toolchain
- Python 3.13-slim — Backend API and Worker (Docker images based on `python:3.13-slim`)
- Docker & Docker Compose — Local development and production deployment

**Package Manager:**
- npm (workspaces) — Frontend monorepo at root level, workspace `services/frontend` (`package-lock.json` present)
- pip — Backend Python dependencies (`services/backend/requirements.txt`, `services/worker/requirements.txt`)

## Frameworks

**Core:**
- Next.js 16.2+ (`next: ^16.2.0`) — React framework with App Router, Turbopack, standalone output (`services/frontend/`)
- React 19.1+ (`react: ^19.1.0`, `react-dom: ^19.1.0`) — UI component library
- FastAPI 0.115.6 — Python async web framework (`services/backend/`)
- SQLAlchemy 2.0.36 (asyncio) — Async ORM for PostgreSQL (`services/backend/`)
- Celery 5.4.0 — Distributed task queue with Redis broker (`services/backend/`, `services/worker/`)
- Alembic 1.14.0 — Database migration management (`services/backend/`)

**Testing:**
- Vitest 4.1.8 — Frontend unit/integration test runner (`services/frontend/vitest.config.ts`)
- Testing Library 16.x (`@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`) — React component testing
- Playwright — E2E browser tests (`tests/e2e/playwright.config.ts`) with Chromium + Firefox
- Pytest 8.3.4 + pytest-asyncio — Backend test runner (`services/backend/pytest.ini`)
- pytest-cov — Backend coverage reporting
- factory-boy — Test data factories for backend

**Build/Dev:**
- Turbopack — Next.js dev bundler (configured in `next.config.ts`)
- TypeScript `tsc` — Type checking (separate from build)
- Tailwind CSS v4 — CSS framework with PostCSS (`@tailwindcss/postcss`)
- Vite (via `@vitejs/plugin-react`) — Vitest's underlying bundler for frontend tests
- Uvicorn 0.34.0 — ASGI server for FastAPI (hot reload in dev)
- Ruff — Python linter (CI only, in `infra/ci/.github/workflows/deploy.yml`)
- Prettier 3.5+ — Code formatter with `prettier-plugin-tailwindcss`

## Key Dependencies

### Frontend (`services/frontend/package.json`)

**Critical:**
- `next: ^16.2.0` — Core framework (App Router, server components, static generation)
- `react: ^19.1.0` / `react-dom: ^19.1.0` — UI rendering
- `zustand: ^5.0.0` — Lightweight state management (stores in `src/stores/`)
- `reactflow: ^11.11.0` — Visual agent builder with node/edge graphs

**UI/Style:**
- `lucide-react: ^0.400.0` — Icon library
- `tailwindcss: ^4.0.0` — Utility-first CSS
- `clsx: ^2.1.0` — Conditional class name utility

**Infrastructure:**
- `typescript: ^5.7.2` — Type safety
- `vitest: ^4.1.8` — Test runner
- `jsdom: ^29.1.1` — DOM environment for tests
- `@vitejs/plugin-react: ^6.0.2` — React transform for Vitest

### Backend (`services/backend/requirements.txt`)

**Critical:**
- `fastapi==0.115.6` / `uvicorn[standard]==0.34.0` — Web framework + ASGI server
- `sqlalchemy[asyncio]==2.0.36` / `asyncpg==0.30.0` — PostgreSQL ORM + async driver
- `neo4j==5.27.1` — Native async driver for Neo4j graph database
- `redis[hiredis]==5.2.1` — Redis client with C extension for performance
- `celery[redis]==5.4.0` — Task queue with Redis broker
- `pydantic==2.10.4` / `pydantic-settings==2.7.1` — Data validation + env config

**AI/LLM:**
- `openai==1.58.1` — OpenAI API client
- `anthropic==0.47.0` — Anthropic API client
- `groq==0.14.0` — Groq API client
- `tiktoken==0.8.0` — Token counting for LLM prompts

**Auth & Security:**
- `python-jose[cryptography]==3.3.0` — JWT (RS256) creation/verification
- `passlib[bcrypt]==1.7.4` / `bcrypt==4.2.1` — Password hashing
- `authlib==1.4.1` — OAuth 2.0 client flows
- `pyotp==2.9.0` / `qrcode[pil]==7.4.2` — TOTP 2FA support

**Storage:**
- `boto3==1.36.0` — AWS SDK for S3-compatible storage (MinIO / R2)
- `s3fs==2024.12.0` — Filesystem interface over S3

**Integrations:**
- `stripe==11.4.1` — Payment processing
- `twilio==9.4.5` — WhatsApp messaging via Twilio
- `meilisearch==0.34.0` — Full-text search client

**Monitoring:**
- `sentry-sdk[fastapi]==2.20.0` — Error tracking
- `opentelemetry-api==1.29.0` / `opentelemetry-sdk==1.29.0` — Distributed tracing
- `opentelemetry-instrumentation-fastapi==0.50b0` / `-sqlalchemy==0.50b0` — Auto-instrumentation
- `structlog==24.4.0` — Structured logging

### Worker (`services/worker/requirements.txt`)

**Critical:**
- `celery[redis]==5.4.0` — Task execution
- `sqlalchemy[asyncio]==2.0.36` / `asyncpg==0.30.0` — Database access
- `neo4j==5.27.1` — Graph database access
- `openai==1.58.1` / `anthropic==0.47.0` — LLM API clients
- `google-api-python-client==2.157.0` — Google Workspace APIs
- `boto3==1.36.0` — S3 storage
- `beautifulsoup4==4.12.3` / `markdown==3.7.0` — Content processing

### Root Dev Dependencies
- `prettier: ^3.5.0` — Formatter
- `prettier-plugin-tailwindcss: ^0.6.0` — Tailwind class sorting

## Configuration

**Environment:**
- Root `.env.example` — Template with all required environment variables (69 vars)
- `services/backend/.env.example` — Backend-specific env template (81 vars)
- `services/frontend/.env.example` — Frontend env template (35 vars, `NEXT_PUBLIC_*` prefix)
- Backend uses `pydantic-settings` with `SettingsConfigDict` — env prefix per module (`DATABASE_`, `REDIS_`, `NEO4J_`, `JWT_`, `OAUTH_`, `AI_`, `WHATSAPP_`, `PAYMENT_`, `STORAGE_`, `MONITORING_`, `RATE_LIMIT_`, `CORS_`, `APP_`)
- Frontend uses `process.env.NEXT_PUBLIC_*` for client-side vars

**Build:**
- `tsconfig.base.json` — Shared TypeScript config (target ES2022, strict mode, path aliases `@/*`, `@anansi/*`)
- `tsconfig.json` — Frontend-specific tsconfig (extends base)
- `vitest.config.ts` — Vitest config (jsdom env, path alias, coverage thresholds)
- `tailwind.config.ts` — Tailwind theme (dark theme default, custom colors, typography scale)
- `postcss.config.mjs` — PostCSS with `@tailwindcss/postcss`
- `.eslintrc.json` — ESLint (Next.js core-web-vitals + TypeScript rules)
- `.prettierrc` — Prettier config (single quotes, trailing commas, 100 print width)
- `pytest.ini` — Pytest markers, async mode, coverage config
- `.coveragerc` — Coverage exclusions and reporting

## Platform Requirements

**Development:**
- Node.js >=22
- Python >=3.13
- Docker + Docker Compose (for PostgreSQL, Neo4j, Redis, Meilisearch, MinIO)
- npm >=10
- Git

**Production:**
- Docker runtime (images built via CI, deployed to Railway)
- PostgreSQL 16 with pgvector extension
- Neo4j 5 (community edition)
- Redis 7 (alpine)
- Meilisearch (full-text search)
- S3-compatible storage (Cloudflare R2 in production, MinIO in dev)

---

*Stack analysis: 2026-06-13*
