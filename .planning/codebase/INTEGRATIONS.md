# External Integrations

**Analysis Date:** 2026-06-13

## APIs & External Services

### AI / LLM Providers
- **OpenAI** — GPT-4o, text-embedding-3-small embeddings, chat completions
  - SDK: `openai==1.58.1` (`services/backend/requirements.txt`)
  - Auth: `OPENAI_API_KEY` env var
  - Used in: `services/backend/app/services/` (brain, agent, summarization), `services/worker/` tasks
- **Anthropic** — Claude Sonnet 4 (default model `claude-sonnet-4-20250514`), chat completions
  - SDK: `anthropic==0.47.0` (`services/backend/requirements.txt`)
  - Auth: `ANTHROPIC_API_KEY` env var
  - Used in: `services/backend/app/services/` (brain, agent, dailynote)
- **Groq** — Fast LLM inference via Groq API
  - SDK: `groq==0.14.0` (`services/backend/requirements.txt`)
  - Auth: `GROQ_API_KEY` env var
  - Fallback/alternative provider
- **Ollama** — Local LLM inference (self-hosted, default `llama3`)
  - Auth: `OLLAMA_BASE_URL` env var (default `http://localhost:11434`)
  - No direct SDK — uses HTTP client

### Payment Processing
- **Stripe** — Primary payment provider, subscription billing
  - SDK: `stripe==11.4.1` (`services/backend/requirements.txt`)
  - Auth: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` env vars
  - Connector: `services/backend/app/connectors/stripe.py` (`StripeConnector` — API key auth, read-only balance/invoice/customer access)
  - Webhook: Stripe webhook signature verification via `verify_webhook_signature()` in `services/backend/app/connectors/base.py`
  - CSP: `https://js.stripe.com`, `https://api.stripe.com` whitelisted in `services/frontend/next.config.ts`
- **Paystack** — African payments fallback
  - SDK: `stripe` package not used; custom connector
  - Auth: `PAYSTACK_SECRET_KEY` env var
  - Connector: `services/backend/app/connectors/paystack.py` (`PaystackConnector`)
  - API: Standard REST (no dedicated SDK in requirements)

### Messaging / Communication
- **WhatsApp Business Cloud API** — Send/receive messages, manage templates
  - SDK: `twilio==9.4.5` for Twilio fallback; primary: direct REST via WhatsApp Cloud API
  - Auth: `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN` env vars
  - API Version: v22.0 (configured in `services/backend/app/core/config.py` WhatsAppSettings)
  - Connector: `services/backend/app/connectors/whatsapp.py` (`WhatsAppConnector` — API key auth, `api_base_url: https://graph.facebook.com/v22.0`)
  - Services: `services/backend/app/services/whatsapp.py`, `.../whatsapp_commands.py`, `.../whatsapp_conversation.py`, `.../whatsapp_notifications.py`
  - Tasks: `services/backend/app/tasks/whatsapp_tasks.py`
  - Webhook: Verify token configured as `anansi_webhook_verify_2026` (configurable)
- **Twilio** — WhatsApp SMS fallback channel
  - SDK: `twilio==9.4.5`
  - Auth: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` env vars
  - Also in Worker: `twilio==9.4.5` (`services/worker/requirements.txt`)

### Google Workspace
- **Gmail** — Read/process emails
  - Connector: `services/backend/app/connectors/gmail.py` (`GmailConnector`)
  - Auth: OAuth 2.0 (Google Cloud Project, shared client ID with other Google connectors)
  - Scopes: OAuth scopes for mail read
- **Google Calendar** — Read events
  - Connector: `services/backend/app/connectors/google_calendar.py` (`GoogleCalendarConnector`)
  - Auth: OAuth 2.0
  - Base class: `services/backend/app/connectors/google_base.py`
- **Google Drive** — File access
  - Connector: `services/backend/app/connectors/google_drive.py` (`GoogleDriveConnector`)
  - Auth: OAuth 2.0
- **Google Keep** — Notes access
  - Connector: `services/backend/app/connectors/google_keep.py` (`GoogleKeepConnector`)
  - Auth: OAuth 2.0
- **Worker**: Uses `google-api-python-client==2.157.0`, `google-auth-httplib2==0.2.0`, `google-auth-oauthlib==1.2.1` (`services/worker/requirements.txt`)

### Productivity / Project Management
- **Notion** — Knowledge base integration
  - Connector: `services/backend/app/connectors/notion.py` (`NotionConnector`)
  - Auth: API key based
- **Slack** — Messaging / notifications
  - Connector: `services/backend/app/connectors/slack.py` (`SlackConnector`)
  - Auth: OAuth 2.0
- **Linear** — Issue tracking
  - Connector: `services/backend/app/connectors/linear.py` (`LinearConnector`)
  - Auth: API key based
- **Outlook** — Email / calendar (Microsoft)
  - Connector: `services/backend/app/connectors/outlook.py` (`OutlookConnector`)
  - Auth: OAuth 2.0

### Social / Communication
- **Twitter/X** — Social media
  - Connector: `services/backend/app/connectors/twitter.py` (`TwitterConnector`)
  - Auth: API key based
- **Telegram** — Messaging
  - Connector: `services/backend/app/connectors/telegram.py` (`TelegramConnector`)
  - Auth: API key based (bot token)
- **Discord** — Community / notifications
  - Connector: `services/backend/app/connectors/discord.py` (`DiscordConnector`)
  - Auth: API key based (bot token)
- **GitHub** — Code repository / developer workflow
  - Connector: `services/backend/app/connectors/github.py` (`GitHubConnector`)
  - Auth: OAuth 2.0 (also used for GitHub OAuth login)
  - Also: `avatars.githubusercontent.com` whitelisted in CSP

### Email
- **Resend** — Transactional email (primary)
  - SDK: No dedicated SDK in requirements — HTTP-based via `aiosmtplib`/SMTP fallback
  - Auth: `RESEND_API_KEY` env var
  - Config: `EMAIL_FROM: "noreply@anansi.ai"`
  - Template: `jinja2==3.1.5` for email template rendering
- **SMTP** (fallback) — `aiosmtplib==4.0.0` in backend requirements

### Monitoring & Observability
- **Sentry** — Error tracking (backend + frontend)
  - Backend: `sentry-sdk[fastapi]==2.20.0`
  - Frontend: `NEXT_PUBLIC_SENTRY_DSN` env var (CSP: `https://*.sentry.io`, `https://o*.ingest.sentry.io`)
  - Auth: `SENTRY_DSN` env var
- **OpenTelemetry** — Distributed tracing
  - Packages: `opentelemetry-api==1.29.0`, `opentelemetry-sdk==1.29.0`, `opentelemetry-instrumentation-fastapi==0.50b0`, `opentelemetry-instrumentation-sqlalchemy==0.50b0`
  - Endpoint: `OTEL_EXPORTER_OTLP_ENDPOINT` (Honeycomb configured by default in `.env.example`)
  - Additional OTLP headers for Honeycomb: `x-honeycomb-team`
- **Flower** — Celery task monitoring
  - Docker service in `docker-compose.yml` (`mher/flower:2.0`) on port 5555
  - Broker: Redis

### Analytics
- **Umami** — Privacy-first, self-hosted analytics (frontend)
  - Config: `NEXT_PUBLIC_UMAMI_WEBSITE_ID`, `NEXT_PUBLIC_UMAMI_URL` env vars (optional)
  - Not yet wired in visible code — env vars defined only

### OAuth / Identity Providers
- **Google OAuth** — User login via Google
  - Auth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` env vars
  - Backend: `authlib==1.4.1` for OAuth flow
  - Frontend: `NEXT_PUBLIC_GOOGLE_CLIENT_ID` env var
  - CSP: `lh3.googleusercontent.com` for avatar images
  - Configuration: `services/backend/app/core/config.py` `OAuthSettings`
- **GitHub OAuth** — User login via GitHub
  - Auth: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI` env vars
  - Frontend: `NEXT_PUBLIC_GITHUB_CLIENT_ID` env var
  - CSP: `avatars.githubusercontent.com` for avatar images

## Data Storage

**Databases:**
- **PostgreSQL 16** (`pgvector/pgvector:pg16`) — Primary relational database
  - Connection: `DATABASE_URL` (async `postgresql+asyncpg://`) and `DATABASE_URL_SYNC` (sync `postgresql://`)
  - ORM: SQLAlchemy 2.0 asyncio, `asyncpg` driver
  - Extensions: `pgvector` (vector similarity search), `uuid-ossp`, `pgcrypto`
  - Migrations: Alembic (`services/backend/migrations/` — SQL files `001_initial_schema.sql`, `002_seed_data.sql`, `003_functions.sql`)
  - Pool: configurable pool size (default 20), max overflow 10, NullPool in serverless mode
  - Port: 5432
- **Neo4j 5** (`neo4j:5-community`) — Graph database for "Second Brain" knowledge web
  - Connection: `NEO4J_URI` (Bolt protocol `bolt://host:7687`)
  - Driver: `neo4j==5.27.1` async driver
  - Auth: `NEO4J_USER` / `NEO4J_PASSWORD`
  - Plugin: APOC (installed via `NEO4J_PLUGINS: '["apoc"]'`)
  - Schema: Constraints + indexes on MemoryNode (id, type, tags, created_at), link indexes, full-text search index
  - Memory settings: pagecache 512M, heap 512M-1G
  - Ports: 7474 (HTTP Browser), 7687 (Bolt)

**Caching:**
- **Redis 7** (`redis:7-alpine`) — Caching, session store, rate limiter, Celery message broker
  - Connection: `REDIS_URL` (`redis://host:6379/0`)
  - Client: `redis[hiredis]==5.2.1` with C extension
  - Persistence: AOF enabled (`--appendonly yes`)
  - Eviction: allkeys-lru, max memory 256MB
  - Port: 6379
  - Used by: Celery broker, rate limiter (token bucket), general caching

**File Storage:**
- **S3-compatible** (Cloudflare R2 / AWS S3 / MinIO) — Media and file storage
  - Connection: `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_REGION`
  - SDK: `boto3==1.36.0`, `s3fs==2024.12.0`
  - Dev default: MinIO (`minio/minio:latest`) on port 9000 (S3 API) and 9001 (console)
  - CSP: `*.r2.cloudflarestorage.com` whitelisted for images
  - Max file size: 50MB (configurable)
  - Bucket: `anansi-media`

**Search:**
- **Meilisearch v1.12** (`getmeili/meilisearch:v1.12`) — Full-text search
  - Connection: `MEILISEARCH_URL`, `MEILISEARCH_MASTER_KEY`
  - SDK: `meilisearch==0.34.0`
  - Port: 7700
  - Dev env: analytics disabled
  - Docker health check at `/health`

## Authentication & Identity

**Auth Provider:**
- **Custom JWT-based** (self-implemented) — Primary authentication system
  - Algorithm: RS256 with 2048-bit RSA key pair
  - Access token expiry: 15 minutes (default) — configurable via `JWT_ACCESS_EXPIRY`
  - Refresh token expiry: 7 days (default) — `JWT_REFRESH_EXPIRY`
  - Implementation: `services/backend/app/core/security.py` — key generation, JWT creation/verification, bcrypt hashing
  - Rate limiting: Redis-backed token bucket (`services/backend/app/core/security.py`)
  - 2FA: TOTP via `pyotp` library (QR code generation with `qrcode[pil]`)
  - OAuth flows: `authlib==1.4.1` for Google/GitHub OAuth integration

**Password Security:**
- Hashing: bcrypt with configurable cost (default 12 rounds)
- Library: `passlib[bcrypt]==1.7.4`

**Frontend Auth:**
- Client-side token management: `services/frontend/src/lib/api.ts` — Bearer token injection, automatic token refresh on 401
- Cookie-based refresh token (HTTP-only)

## Monitoring & Observability

**Error Tracking:**
- Sentry — Both backend (`sentry-sdk[fastapi]`) and frontend (`NEXT_PUBLIC_SENTRY_DSN`)

**Logs:**
- Structured logging with `structlog==24.4.0` (backend)
- JSON log format in production, console in dev
- Request ID middleware (`X-Request-ID`) for request tracking
- Response time header (`X-Response-Time-Ms`)

**Tracing:**
- OpenTelemetry with Honeycomb as default OTLP endpoint
- Auto-instrumentation for FastAPI and SQLAlchemy

**Metrics:**
- Flower (Celery task monitoring) on port 5555
- Health check endpoint (`GET /health`) checks PostgreSQL, Redis, Neo4j connectivity

## CI/CD & Deployment

**Hosting:**
- **Railway** — Production deployment (API, Web, Worker services)
  - Deployed via Railway CLI in CI pipeline
  - Command: `railway up --service <name>` with `RAILWAY_TOKEN`
  - Migrations: `railway run --service api alembic upgrade head`

**CI Pipeline:**
- **GitHub Actions** — `.github/workflows/deploy.yml` at `infra/ci/.github/workflows/deploy.yml`
  - Trigger: push to `main`/`develop`, PR to `main`, tags `v*`, manual dispatch
  - Jobs:
    1. `lint-and-test` — Runs on ubuntu-latest with PostgreSQL 16 + Redis 7 as service containers
       - TypeScript type check (`tsc --noEmit`)
       - ESLint frontend lint
       - Vitest frontend test
       - Python lint with Ruff
       - Pytest backend tests with coverage (Codecov upload)
    2. `build-and-push` — Builds 3 Docker images to GitHub Container Registry (ghcr.io)
       - `ghcr.io/<repo>/web`, `/api`, `/worker`
       - Tags: branch, PR, semver, short SHA, `latest`
       - Docker BuildKit caching via `type=gha`
    3. `deploy` — Deploys API, Web, Worker to Railway (main branch only)
    4. `notify` — Slack webhook notification on success/failure

**Docker Images:**
- `infra/docker/Dockerfile.api` — Python 3.13-slim, multi-stage, uvicorn with 4 workers
- `infra/docker/Dockerfile.web` — Node.js 22-alpine, multi-stage, Next.js standalone output
- `infra/docker/Dockerfile.worker` — Python 3.13-slim, multi-stage, Celery with 4 concurrency
- Dev variants: `Dockerfile.api.dev`, `Dockerfile.web.dev` (with hot reload)

**Container Registry:**
- GitHub Container Registry (`ghcr.io`)

## Environment Configuration

**Required env vars (critical):**
- `DATABASE_URL` / `DATABASE_URL_SYNC` — PostgreSQL connection strings
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` — Neo4j graph database
- `REDIS_URL` — Redis connection
- `SECRET_KEY` — Application secret
- `JWT_SECRET` — JWT signing key
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — AI providers

**Secrets location:**
- `.env` files at root, `services/backend/.env`, `services/frontend/.env` (gitignored)
- GitHub Actions secrets (`RAILWAY_TOKEN`, `SLACK_WEBHOOK`, etc.)
- GitHub Container Registry via `GITHUB_TOKEN`
- Template: `.env.example` files at root, backend, and frontend levels

## Webhooks & Callbacks

**Incoming:**
- **Stripe Webhook** — Payment events (subscription updates, invoices, etc.)
  - Verification: HMAC-SHA256 signature via `verify_webhook_signature()` in `services/backend/app/connectors/base.py`
  - Secret: `STRIPE_WEBHOOK_SECRET` env var
- **WhatsApp Webhook** — Incoming messages, message status updates
  - Endpoint: Part of WhatsApp API v22.0 Cloud API
  - Verify token: configurable (default `anansi_webhook_verify_2026`)
  - Verification: Custom token verification per WhatsApp Cloud API spec
- **Plugin Webhooks** — Generic webhook registration system for agents
  - Managed via `services/frontend/src/stores/integrations.ts` (register/unregister)
  - Backend: Webhook service in `services/backend/app/services/webhook.py`

**Outgoing:**
- **Slack** — CI/CD deployment notifications
  - Webhook: `secrets.SLACK_WEBHOOK` in GitHub Actions
  - Format: Slack incoming webhook JSON payload

---

*Integration audit: 2026-06-13*
