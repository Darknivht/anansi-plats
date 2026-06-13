# Codebase Concerns

**Analysis Date:** 2026-06-13

## Tech Debt

### Stub AI/Agent Engine — WebSocket handlers return placeholder responses

**Issue:** All WebSocket event handlers for AI and agent execution are stubs that echo input back instead of routing to actual services.

**Files:**
- `services/backend/app/websocket/handler.py` — Lines 200-209 (`ai.send_message`), 235-244 (`agent.run`), 257-267 (`brain.create_node`)

**Impact:** The primary real-time features of the platform (AI chat, agent execution, brain operations) do not work over WebSocket. The frontend's `useWebSocket` hook connects but receives mock data.

**Fix approach:** Implement actual routing from WebSocket handlers to `app.services.ai` (AI service), `app.services.execution` (execution_engine), and `app.services.brain`/`app.services.graph` (brain service). Stream responses via `manager.send_to_user`.

---

### Notification Service — Delivery is a no-op

**Issue:** `NotificationService._send_external_notification` only logs the delivery intent — no actual email, WhatsApp, or push notification is sent.

**Files:**
- `services/backend/app/services/notification.py` — Lines 324-330

**Impact:** Users receive in-app notifications but never get pushed notifications via email/SMS/WhatsApp. The notification infrastructure exists but is disconnected.

**Fix approach:** Implement delivery via `WhatsAppService.send_message()`, `aiosmtplib` for email, and optionally push notifications. Wire the delivery channel based on user preferences.

---

### Webhook HMAC Verification — Always returns True

**Issue:** The `_verify_webhook_signature` static method in TriggerService always returns `True` regardless of the signature. The HMAC secret retrieval and verification is not implemented.

**Files:**
- `services/backend/app/services/trigger.py` — Lines 380-386, 413-426

**Impact:** Any incoming webhook payload (even unauthenticated) can trigger agent execution. This is a security vulnerability — external actors can invoke agents by calling the webhook URL.

**Fix approach:** Store per-agent webhook secrets in the database or Redis. Implement actual `hmac.compare_digest()` verification against the stored secret using the payload body and `x-webhook-signature` header.

---

### Execution Engine — AI and Integration routing are stubs

**Issue:** The Agent Execution Engine (`execution.py`) has TODO comments for AI service integration and external connector routing. Block execution stubs return mock results.

**Files:**
- `services/backend/app/services/execution.py` — Lines 254, 333, 523

**Impact:** Agent workflows cannot actually invoke LLM calls or external API integrations. The block execution pipeline exists but the terminal blocks (AI call, HTTP request, etc.) are not wired.

**Fix approach:** Implement `app/services/ai.py` (if not existing) or wire existing AI provider SDK calls (OpenAI, Anthropic). Implement connector routing via the connector registry.

---

### WhatsApp OTP — Logged but never sent

**Issue:** When linking a WhatsApp number, the OTP verification code is generated and stored but only logged — it is never actually sent via WhatsApp template message or SMS gateway.

**Files:**
- `services/backend/app/services/whatsapp.py` — Lines 219-226

**Impact:** Users cannot complete WhatsApp linking because they never receive the OTP. The feature is broken in production.

**Fix approach:** Implement actual WhatsApp Cloud API template message sending for OTP delivery, or integrate an SMS gateway (Twilio) as fallback.

---

### User Account Deletion — No background cleanup

**Issue:** When a user deletes their account, the user record is soft-deleted but no background task is enqueued to clean up conversations, memory nodes, files, team memberships, etc.

**Files:**
- `services/backend/app/services/user.py` — Line 306

**Impact:** Deleted users leave behind orphaned data in PostgreSQL, Neo4j, and S3 storage. This creates data bloat and privacy concerns.

**Fix approach:** Enqueue a Celery task on account deletion that iterates through all associated data and either anonymizes or removes it.

---

### Worker Service — Empty tasks directory

**Issue:** The `services/worker/tasks/` directory is completely empty. The Celery worker Docker service is configured and running but has no tasks to execute.

**Files:**
- `services/worker/tasks/` (empty directory)
- `docker-compose.yml` — Lines 196-213 (worker service definition)
- `infra/docker/Dockerfile.worker` (Dockerfile references worker, but no tasks exist)

**Impact:** The entire background task processing infrastructure (Celery, Flower monitoring, Redis broker) is deployed but unused. Any background task that needs to be enqueued (email sending, cleanup, AI processing) cannot be executed.

**Fix approach:** Populate `services/worker/tasks/` with actual Celery task modules. Migrate or duplicate the task definitions from `services/backend/app/tasks/` where needed, or restructure to share task code.

---

### Connector Stubs — Telegram and Twitter are empty

**Issue:** The Telegram and Twitter/connector implementations contain only empty method stubs with `pass` bodies.

**Files:**
- `services/backend/app/connectors/telegram.py` — Line 40
- `services/backend/app/connectors/twitter.py` — Line 182

**Impact:** These connectors are listed in the UI and API but cannot be used. Users get errors if they attempt to connect.

**Fix approach:** Implement actual API integrations for Telegram Bot API and Twitter API v2, or remove them from the registry if not planned.

---

### WhatsApp Command — Graph image generation is a stub

**Issue:** The `/graph` quick command returns a text description instead of generating an actual graph visualization image.

**Files:**
- `services/backend/app/services/whatsapp_commands.py` — Line 508

**Impact:** Users on WhatsApp cannot get the visual graph view of their Second Brain.

**Fix approach:** Implement or integrate with a graph rendering service (e.g., generate PNG via matplotlib, Graphviz, or a headless browser render of the graph view).

---

### WhatsApp Morning Briefing — Weather integration is a placeholder

**Issue:** The daily morning briefing sends brain stats but has a TODO placeholder for weather data.

**Files:**
- `services/backend/app/services/whatsapp_notifications.py` — Line 162

**Impact:** Missing a feature users expect from a morning briefing.

**Fix approach:** Integrate with a weather API (OpenWeatherMap, WeatherAPI) based on user's timezone or stored city preference.

---

## Security Considerations

### Hardcoded Default Credentials in Source Code

**Risk:** Multiple services have hardcoded default passwords/credentials that are used when environment variables are not set. If these defaults reach production (e.g., via misconfigured deployment), they are trivially guessable.

**Files:**
- `services/backend/app/core/config.py` — Lines 66 (`Neo4jSettings.password = "anansi"`), 186 (`StorageSettings.secret_access_key = "minioadmin"`)
- `services/backend/app/db/neo4j.py` — Line 40 (`NEO4J_PASSWORD = "anansi-neo4j"`)
- `docker-compose.yml` — Lines 9, 12, 14, 17, 42-44 (develop defaults in compose)
- `infra/docker/docker-compose.yml` — Lines 8, 12, 14, 42-44 (same defaults)

**Current mitigation:** Defaults only activate when env vars are unset. Docker compose files use shell variable substitution with defaults. However, having "anansi" and "minioadmin" as compile-time defaults is risky.

**Recommendations:**
- Remove hardcoded password defaults from `config.py` — make them required env vars.
- Add a startup check that warns/fails if default credentials are detected in production mode.
- Generate random secrets during first deploy setup.

---

### Webhook Signature Verification — Always passes

**Risk:** The `_verify_webhook_signature` method at `trigger.py:414-426` always returns `True` regardless of the signature value. This means ANY POST to a webhook URL can trigger agent execution.

**Files:**
- `services/backend/app/services/trigger.py` — Lines 413-426

**Current mitigation:** None. The HMAC verification code is intentionally stubbed.

**Recommendations:** Implement HMAC verification using agent-specific secrets before production deployment. Remove the stub and either implement or throw a `NotImplementedError`.

---

### Rate Limiter Fails Open on Redis Failure

**Risk:** When Redis is unavailable, `TokenBucketRateLimiter.check()` returns `(True, max_requests, 0)` — allowing unlimited requests. This defeats rate limiting during Redis outages.

**Files:**
- `services/backend/app/core/security.py` — Lines 304-307

**Current mitigation:** Logs the error. In development this is acceptable, but in production it could allow abuse.

**Recommendations:** Add a fallback in-memory rate limiter or fail closed (return False) in production mode.

---

### OTP and Sensitive Data Logged in Plaintext

**Risk:** WhatsApp OTP codes are logged at INFO level via structlog in `services/backend/app/services/whatsapp.py:221-226`. Logs may be ingested by centralized logging systems, creating exposure.

**Files:**
- `services/backend/app/services/whatsapp.py` — Lines 221-226

**Current mitigation:** Only logged during development.

**Recommendations:** Remove OTP from log output. Use a log filter to redact sensitive fields.

---

### JWT Ephemeral Development Keys

**Risk:** When no JWT keys are configured in settings, the system generates ephemeral RSA keys at module import time (`security.py:66`). These change on every restart, invalidating all existing tokens. In development mode, this is acceptable, but a misconfigured production deployment would silently use ephemeral keys.

**Files:**
- `services/backend/app/core/security.py` — Lines 62-63, 66

**Current mitigation:** A warning is logged. Documentation instructs setting `JWT_PRIVATE_KEY` in production.

**Recommendations:** Fail startup in production mode if JWT keys are not configured.

---

### CORS Allows All Headers

**Risk:** CORS configuration at `config.py:246` uses `allow_headers: list[str] = Field(default=["*"])` which allows all custom headers in cross-origin requests.

**Files:**
- `services/backend/app/core/config.py` — Line 246

**Current mitigation:** Origins are restricted to known domains.

**Recommendations:** Restrict allowed headers to the specific set the API uses (`Content-Type`, `Authorization`, `X-Request-ID`, etc.).

---

## Performance Bottlenecks

### Large Service Files

**Problem:** Several backend service files exceed 800 lines, indicating they handle too many responsibilities or have not been decomposed.

**Files and sizes:**
- `services/backend/app/services/blocks.py` — 1150 lines
- `services/backend/app/services/execution.py` — 1134 lines
- `services/backend/app/services/billing.py` — 1038 lines
- `services/backend/app/services/whatsapp.py` — 914 lines
- `services/backend/app/services/graph.py` — 872 lines
- `services/backend/app/services/whatsapp_commands.py` — 865 lines
- `services/frontend/src/components/workshop/BlockConfigPanel.tsx` — 795 lines

**Impact:** These files are difficult to maintain, test, and reason about. They likely violate the Single Responsibility Principle. Import cycles become harder to manage.

**Improvement path:** Split into smaller modules. For example, `billing.py` could separate subscription management, invoice generation, and webhook handling. `whatsapp.py` could separate connection management, message sending, media handling, and webhook verification.

### Two Database Connection Configurations

**Problem:** Neo4j connection details are configured in two places with different mechanisms:
1. `app/core/config.py` via Pydantic Settings (env-prefixed)
2. `app/db/neo4j.py` via raw `os.getenv()` calls

**Files:**
- `services/backend/app/core/config.py` — Lines 59-70
- `services/backend/app/db/neo4j.py` — Lines 38-54

**Impact:** Configuration drift — one could be updated without the other. The `db/neo4j.py` module doesn't use the centralized settings.

**Improvement path:** Make `app/db/neo4j.py` import and use `settings.neo4j.*` instead of `os.getenv()`. Remove the duplicated configuration.

### Sync DB URL Property — String manipulation

**Problem:** `DatabaseSettings.sync_url` uses simple string replacement (`self.url.replace("+asyncpg", "")`) to derive the sync URL. If the async URL format changes, this silently breaks.

**Files:**
- `services/backend/app/core/config.py` — Lines 33-36

**Improvement path:** Use `SQLAlchemy`'s URL manipulation utilities or maintain a separate env variable for the sync URL.

---

## Fragile Areas

### Module-level Singletons

**What makes it fragile:** Multiple services use module-level singletons (`_engine`, `_driver`, `_rate_limiter_instance`, `settings`) initialized at import time or during startup. These make unit testing difficult (state leaks between tests) and create implicit dependencies.

**Files:**
- `services/backend/app/core/security.py` — `_RSA_PRIVATE_KEY`, `_RSA_PUBLIC_KEY` (line 66), `_rate_limiter_instance` (line 328)
- `services/backend/app/core/events.py` — `_engine`, `_session_factory`, `_redis_client`, `_neo4j_driver` (lines 25-28)
- `services/backend/app/db/neo4j.py` — `_driver` (line 60)
- `services/backend/app/core/config.py` — `settings` (line 295)
- `services/backend/app/websocket/manager.py` — `manager` (line 386)

**Safe modification:** When modifying any singleton, ensure the global is properly reset in tests (e.g., pytest fixtures with monkeypatch). For production changes, ensure the startup lifecycle (`lifespan` in `events.py`) properly reinitializes.

**Test coverage:** The `conftest.py` overrides settings with test values, but singleton state from previous tests can leak if fixtures don't properly clean up.

### WhatsApp Service — Manual DB session management

**What makes it fragile:** Multiple WhatsApp service methods bypass FastAPI's dependency injection and manually create DB sessions using `db = await anext(get_db_session())`. This pattern is used in 12 locations across the WhatsApp services. These sessions must be manually closed, and errors in session management can cause connection leaks.

**Files:**
- `services/backend/app/services/whatsapp_commands.py` — Line 40
- `services/backend/app/services/whatsapp_conversation.py` — Lines 71, 148, 288
- `services/backend/app/services/whatsapp_notifications.py` — Lines 91, 122, 215, 261, 291, 322, 415, 455

**Safe modification:** Ensure every `anext(get_db_session())` call has a corresponding `await db.close()` in a `finally` block. Prefer refactoring to accept `AsyncSession` as a parameter (dependency injection).

### Duplicate Fix Directories — Codebase drift

**What makes it fragile:** Two extracted fix archives (`anansi-frontend-fix/` and `api-fix/`) contain modified copies of source files. These patches were applied after the main build and may diverge from the originals.

**Files:**
- `anansi-frontend-fix/` — Full frontend source tree with modifications
- `api-fix/` — Contains `services/backend/app/api/v1/agents.py`, `auth.py`, `users.py` patches
- `anansi-frontend-fix.tar.gz` and `api-fix.tar.gz` — Original archives

**Safe modification:** Before modifying any file under `services/`, check if a corresponding fix exists in `api-fix/` or `anansi-frontend-fix/`. The fix versions may contain critical patches not present in the main source. Ideally, merge the fixes into the main source and remove the fix directories.

---

## Scaling Limits

### Database Connection Pools

**Current capacity:** PostgreSQL pool of 20 (max_overflow 10), Redis max 50 connections, Neo4j pool of 50.

**Limit:** With a single API instance and 4 workers, each worker could exhaust the pool under load. No connection pooling for Neo4j across workers.

**Scaling path:** Increase pool sizes proportionally with worker count. Add PgBouncer for PostgreSQL connection pooling in production. Use Redis connection pool sharing.

### No Horizontal Scaling Configuration

**Current capacity:** Single API instance, single worker instance.

**Limit:** No Kubernetes/ECS configuration, no load balancer setup, no auto-scaling policies. The platform cannot scale beyond a single VM without manual configuration.

**Scaling path:** Containerize with horizontal scaling in mind. Add a load balancer (e.g., nginx, ALB). Configure session affinity for WebSocket connections. Use Redis pub/sub for cross-instance WebSocket messaging.

---

## Dependencies at Risk

### python-jose (JWT library)

**Risk:** `python-jose` (used at `services/backend/requirements.txt:31`) has had periods of low maintenance. The library is used with RS256 and `cryptography` backend, which is well-tested.

**Impact:** If `python-jose` becomes unmaintained, security patches for JWT vulnerabilities may be delayed.

**Migration plan:** Migrate to `python-jwt` (already listed at line 33) or use `PyJWT` directly with `cryptography` for RSA signing. The `python-jwt` library listed in requirements appears to be `python_jwt` (a different package) — verify intent.

---

## Missing Critical Features

### No AI Service Layer

**Problem:** The codebase imports and configures OpenAI, Anthropic, and Groq SDKs, but there is no unified AI service layer (`app/services/ai.py`) that routes requests to providers, manages context windows, or handles streaming responses.

**Files:**
- No `services/backend/app/services/ai.py` exists (confirmed via directory listing)
- `services/backend/app/core/config.py` — Lines 120-138 (AI settings defined)
- `services/backend/requirements.txt` — Lines 39-41 (SDKs installed)

**Blocks:** All agent execution blocks that involve LLM calls, AI chat in WebSocket, WhatsApp AI conversations, and morning briefing generation.

### No Celery Task Definitions

**Problem:** The entire Celery infrastructure (Redis broker, worker service, Flower monitoring) is deployed but there are zero task definitions. The `services/worker/tasks/` directory is empty.

**Files:**
- `services/worker/tasks/` — Empty directory
- `services/backend/app/tasks/agent_tasks.py` and `whatsapp_tasks.py` — Exist but likely unused

**Blocks:** Background job processing for email delivery, data cleanup, AI inference, scheduled agent triggers.

---

## Test Coverage Gaps

### Untested Core Services

**What's not tested:** The largest and most complex backend services have no dedicated test modules:
- `services/backend/app/services/blocks.py` (1150 lines) — No tests
- `services/backend/app/services/execution.py` (1134 lines) — No tests
- `services/backend/app/services/billing.py` (1038 lines) — No tests
- `services/backend/app/services/graph.py` (872 lines) — No tests

**Files:**
- `services/backend/tests/` — 11 test files exist but none cover the services above
- `services/backend/tests/test_billing.py` and `test_brain.py` exist but with limited coverage

**Risk:** These are the most complex and business-critical modules. Defects in execution, billing, or graph logic could go undetected.

**Priority:** High

### Frontend Store Tests Missing

**What's not tested:** Several Zustand stores lack test coverage:
- `services/frontend/src/stores/integrations.ts` — No test file
- `services/frontend/src/stores/marketplace.ts` — No test file

**Files:**
- `services/frontend/tests/stores/` — Contains `brain.test.ts`, `chat.test.ts`, `ui.test.ts`, `workshop.test.ts` but not the above

**Priority:** Medium

### E2E Tests — Page rendering only

**What's not tested:** All E2E tests (`tests/e2e/`) only check that pages render with expected text/headings. There are no interaction flows (login, agent creation, brain operations, billing) tested end-to-end.

**Files:**
- `tests/e2e/auth.spec.ts` — Checks login/signup pages render
- `tests/e2e/agent.spec.ts` — Checks agent pages render
- `tests/e2e/brain.spec.ts` — Checks brain pages render
- `tests/e2e/marketplace.spec.ts` — Checks marketplace pages render

**Risk:** Critical user flows can break without detection.

**Priority:** Medium

### No CI Workflow Found

**What's not tested:** The CI workflow at `infra/ci/.github/workflows/deploy.yml` exists but no CI integration is configured. Tests are not run automatically on pull requests or pushes.

**Risk:** Code changes can be merged without running tests.

**Priority:** Medium

---

*Concerns audit: 2026-06-13*
