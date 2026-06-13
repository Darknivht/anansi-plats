# Testing Patterns

**Analysis Date:** 2026-06-13

## Test Framework

**Runner (Frontend):**
- **Vitest** v4.1.8
- Config: `services/frontend/vitest.config.ts`
- Plugin: `@vitejs/plugin-react` v6.0.2
- Environment: `jsdom` with CSS enabled
- Globals: `true` (vitest globals available without imports — `vi`, `describe`, `it`, `expect`)
- Mock reset: `mockReset: true` (auto-resets mocks between tests)
- Setup file: `tests/setup.tsx`

**Runner (Backend):**
- **pytest** with `pytest-asyncio` for async support
- Config: `services/backend/pytest.ini`
- Mode: `asyncio_mode = auto`
- Options: `-v --strict-markers`
- Logging: `log_cli = true`, `log_cli_level = INFO`

**Runner (E2E):**
- **Playwright** (`@playwright/test`)
- Config: `tests/e2e/playwright.config.ts`
- Browsers: Chromium, Firefox (fully parallel)
- CI: retries 2, workers 1; local: no retries, all workers

**Assertion Libraries:**
- Frontend: Vitest built-in assertions + `@testing-library/jest-dom/vitest` for DOM matchers
- Backend: pytest `assert` statements
- E2E: Playwright's `expect` with locator matchers

**Run Commands:**
```bash
npm test                              # Run all frontend tests
npm run test -- --run                 # Single run (not watch mode)
cd services/backend && pytest         # Run all backend tests
cd services/backend && pytest tests/test_auth.py -k "test_login"  # Filter tests
cd services/backend && pytest -m slow # Run only slow-marked tests
npx playwright test --config tests/e2e/playwright.config.ts  # Run E2E tests
```

## Test File Organization

**Frontend Tests:**
- Separate directory: `services/frontend/tests/` — mirrors `src/` structure
- Pattern: `src/lib/utils.ts` → `tests/lib/utils.test.ts`
- Pattern: `src/components/ui/AnansiButton.tsx` → `tests/components/AnansiButton.test.tsx`
- Pattern: `src/stores/ui.ts` → `tests/stores/ui.test.ts`
- Setup file: `tests/setup.tsx` (global mocks)

```
services/frontend/
├── src/
│   ├── components/ui/AnansiButton.tsx
│   ├── lib/utils.ts
│   └── stores/ui.ts
└── tests/
    ├── setup.tsx
    ├── components/AnansiButton.test.tsx
    ├── lib/utils.test.ts
    └── stores/ui.test.ts
```

**Backend Tests:**
- Separate directory: `services/backend/tests/`
- Naming: `test_<module>.py`
- Pattern: `app/api/v1/auth.py` → `tests/test_auth.py`
- Shared fixtures: `tests/conftest.py`

**E2E Tests:**
- Location: `tests/e2e/`
- Naming: `<feature>.spec.ts`
- Config: `tests/e2e/playwright.config.ts`

## Test Structure

**Suite Organization — Frontend:**

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AnansiButton } from '../components/ui/AnansiButton';

describe('AnansiButton', () => {
  it('renders children correctly', () => {
    render(<AnansiButton>Click Me</AnansiButton>);
    expect(screen.getByText('Click Me')).toBeInTheDocument();
  });

  it('handles click events', () => {
    const handleClick = vi.fn();
    render(<AnansiButton onClick={handleClick}>Clickable</AnansiButton>);
    fireEvent.click(screen.getByText('Clickable'));
    expect(handleClick).toHaveBeenCalledOnce();
  });
});
```

**Suite Organization — Backend:**

```python
class TestRegister:
    """Test user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient):
        """Test successful registration returns tokens."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "StrongPass1", "display_name": "New User"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
```

**Suite Organization — E2E:**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
  });
});
```

**Patterns:**
- Frontend: `describe`/`it` blocks, one assertion group per `describe`
- Backend: Class-per-endpoint pattern (`TestRegister`, `TestLogin`, `TestTokenRefresh`), one method per scenario
- Backend test methods always decorated with `@pytest.mark.asyncio`
- Backend docstrings on each test method explaining what's being tested
- Frontend tests: one `it` per logical behavior (rendering, variants, events, edge cases)

## Mocking

**Frontend Framework:** Vitest's `vi` (built-in)

**Frontend Setup Mocks (`tests/setup.tsx`):**
- `next/navigation`: mocks `useRouter`, `usePathname`, `useSearchParams`, `useParams`
- `next/image`: renders `<img>` instead of Next.js optimized Image
- `next/link`: renders `<a>` instead of Next.js Link
- `lucide-react`: preserves actual icon implementation via `vi.requireActual`
- `WebSocket`: mock class implementing `send`, `close`, `onopen`, `onclose`, `onmessage`, `onerror`
- `fetch`: always returns 200 with empty JSON
- `IntersectionObserver`: no-op mock class
- `Element.prototype.scrollIntoView`: vi.fn()

```typescript
// From tests/setup.tsx — Mock pattern for Next.js navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    pathname: '/',
    query: {},
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
```

**Backend Mocking Framework:** `pytest-mock` (via `mocker` fixture)

**Backend Fixture Patterns (`tests/conftest.py`):**
- In-memory SQLite database for transactional test isolation
- `fakeredis` for Redis mocking
- Custom `FakeNeo4jDriver`/`FakeNeo4jSession`/`FakeNeo4jResult` classes for Neo4j
- FastAPI dependency overrides via `app.dependency_overrides`
- Auth headers fixture creates user in DB and returns `Bearer` token

```python
# From conftest.py — Mock service pattern
@pytest.fixture
def mock_ai_service(mocker):
    """Mock AI service responses (OpenAI, Anthropic, etc.)."""
    mock = mocker.patch("app.services.brain.MemoryService._generate_embedding")
    mock.return_value = [0.1] * 384
    return mock
```

**What to Mock:**
- External HTTP calls (OpenAI, Stripe, WhatsApp Cloud API, Paystack)
- Infrastructure (Redis, Neo4j)
- AI embedding services
- File/email sending

**What NOT to Mock:**
- Database (uses real SQLite in-memory)
- Internal application logic
- Request validation (tested through API)

## Fixtures and Factories

**Frontend Test Data:**
- Inline data factory in test files (see `tests/stores/chat.test.ts`):
```typescript
const conv: Conversation = {
  id: 'conv-1',
  title: 'Test Chat',
  messages: [],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};
```

**Backend Fixtures (`tests/conftest.py`):**
- `event_loop` — session-scoped event loop
- `test_engine` — session-scoped in-memory SQLite with all tables created
- `test_db` — function-scoped transactional DB session with rollback
- `test_redis` — fake Redis instance via `fakeredis`
- `test_neo4j` — fake Neo4j driver with custom classes
- `app` — FastAPI app with overridden dependencies
- `async_client` — `httpx.AsyncClient` for HTTP testing
- `auth_headers` — creates user + generates JWT
- `auth_headers_pro` — creates pro-plan user + generates JWT
- `sample_user` — creates sample user record
- `sample_memory_node` — creates sample memory node via SQLAlchemy ORM
- `sample_agent` — creates sample agent with block definition
- `mock_ai_service` — patches embedding generation
- `mock_whatsapp_api` — patches HTTPX POST for WhatsApp
- `mock_stripe` — patches Stripe checkout session
- `mock_paystack` — patches HTTPX POST for Paystack

**Fixture Location:** `services/backend/tests/conftest.py` — all shared fixtures centralized in one file.

## Coverage

**Frontend Coverage:**
- Provider: `v8`
- Reporters: `text`, `json`, `html`
- Thresholds: statements 70%, branches 60%, functions 65%, lines 70%
- Include: `src/**/*.{ts,tsx}`
- Exclude: `*.d.ts`, `*.test.*`, `__mocks__/`
- Reports directory: `./coverage`

```bash
cd services/frontend && npx vitest --coverage    # View coverage
```

**Backend Coverage (`.coveragerc`):**
- Source: `app`
- Omit: migrations, tests, `__init__.py`
- Exclude lines: `pragma: no cover`, `raise NotImplementedError`, `if __name__`, `pass`, `logger.`
- Show missing: yes

```bash
cd services/backend && pytest --cov=app --cov-report=html
```

**Coverage Requirements:** Frontend has hard thresholds (70/60/65/70). Backend has no hard thresholds but coverage config is present.

## Test Types

**Unit Tests (Frontend):**
- Pure utility functions (`tests/lib/utils.test.ts`) — no mocking needed
- Component rendering with variants (`tests/components/*.test.tsx`) — component-level
- Store state management (`tests/stores/*.test.ts`) — direct `getState()`/`setState()` access

**Integration Tests (Backend):**
- API endpoint tests using `async_client` — full request/response cycle
- Test database with transactional isolation (in-memory SQLite)
- Dependency injection overrides for external services
- Auth headers fixture for authenticated endpoints
- Marked with domain-specific markers (`@pytest.mark.brain`, `@pytest.mark.auth`, etc.)

**E2E Tests:**
- Playwright with Chromium and Firefox
- Page-level interaction testing
- Navigation flows and content visibility assertions
- Local dev servers: frontend (port 3000), backend (port 8000)
- Artifacts: screenshots on failure, video retention on failure, trace on first retry

## Common Patterns

**Store Testing Pattern:**
```typescript
// From tests/stores/ui.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '../stores/ui';

describe('UI Store', () => {
  beforeEach(() => {
    // Reset store to defaults
    useUIStore.setState({
      sidebarOpen: true,
      sidebarExpanded: true,
      activeModal: null,
      modalData: null,
      theme: 'dark',
      toasts: [],
      commandPaletteOpen: false,
    });
  });

  it('toggles sidebar open state', () => {
    expect(useUIStore.getState().sidebarOpen).toBe(true);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(false);
  });
});
```

**Component Testing Pattern:**
```typescript
// From tests/components/Wikilink.test.tsx
it('calls onClick with target when clicked', () => {
  const handleClick = vi.fn();
  render(<Wikilink target="Project Alpha" onClick={handleClick} />);
  fireEvent.click(screen.getByText('Project Alpha'));
  expect(handleClick).toHaveBeenCalledWith('Project Alpha');
  expect(handleClick).toHaveBeenCalledOnce();
});
```

**API Testing Pattern:**
```typescript
// From tests/lib/api.test.ts
it('performs a GET request successfully', async () => {
  const mockData = { id: 1, name: 'Test' };
  (global.fetch as any).mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: () => Promise.resolve(mockData),
  });

  const result = await api.get('/api/v1/test');
  expect(result).toEqual(mockData);
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining('/api/v1/test'),
    expect.objectContaining({ method: 'GET' }),
  );
});
```

**Backend API Testing Pattern:**
```python
# From tests/test_auth.py
@pytest.mark.asyncio
async def test_register_success(self, async_client: AsyncClient):
    """Test successful registration returns tokens."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "StrongPass1",
            "display_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
```

**Backend Fixture Usage:**
```python
# From tests/test_brain.py — using sample_memory_node fixture
@pytest.mark.asyncio
async def test_get_node(
    self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
):
    """Test retrieving a specific node."""
    node_id = sample_memory_node["id"]
    response = await async_client.get(
        f"/api/v1/brain/nodes/{node_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "node" in data
```

**Error Testing Pattern:**
```typescript
// From tests/lib/api.test.ts
it('throws ApiClientError on non-ok response', async () => {
  (global.fetch as any).mockResolvedValueOnce({
    ok: false,
    status: 404,
    json: () => Promise.resolve({ error: { code: 'not_found', message: 'Not found' } }),
  });

  await expect(api.get('/api/v1/nonexistent')).rejects.toThrow(ApiClientError);
  await expect(api.get('/api/v1/nonexistent')).rejects.toThrow('Not found');
});
```

**Async Testing with Fake Timers:**
```typescript
// From tests/stores/ui.test.ts
it('auto-removes toast after duration', async () => {
  vi.useFakeTimers();
  useUIStore.getState().addToast('info', 'Auto-remove', undefined, 100);
  expect(useUIStore.getState().toasts).toHaveLength(1);
  vi.advanceTimersByTime(100);
  expect(useUIStore.getState().toasts).toHaveLength(0);
  vi.useRealTimers();
});
```

---

*Testing analysis: 2026-06-13*
