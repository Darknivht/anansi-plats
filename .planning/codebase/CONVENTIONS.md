# Coding Conventions

**Analysis Date:** 2026-06-13

## Naming Patterns

**Files:**
- React components: PascalCase (`AnansiButton.tsx`, `GlassCard.tsx`, `MorningBriefing.tsx`)
- Utility modules: camelCase (`api.ts`, `utils.ts`)
- Stores: camelCase (`ui.ts`, `brain.ts`, `chat.ts`, `workshop.ts`)
- Hooks: camelCase with `use` prefix (`useWebSocket.ts`)
- Backend Python: snake_case (`test_auth.py`, `conftest.py`, `test_brain.py`)
- E2E tests: kebab-case (`auth.spec.ts`, `agent.spec.ts`)
- Test files: `*.test.ts`/`*.test.tsx` (frontend) or `test_*.py` (backend)

**Functions:**
- Functions: camelCase (`formatRelativeTime`, `generateId`, `loadGraph`, `toggleSidebar`)
- React components: PascalCase exported functions (`export function AnansiButton(...)`)
- Backend Python: snake_case (`test_register_success`, `create_access_token`)
- Private helpers: underscore-prefixed in Python (`_override_get_db`), `_`-prefixed unused params in TypeScript

**Variables:**
- camelCase for all TypeScript/JavaScript variables, including constants
- `UPPER_SNAKE_CASE` for configuration maps like `BLOCK_LABELS`, `BLOCK_DEFAULTS`, `BLOCK_COLORS` (see `src/stores/workshop.ts`)
- Boolean naming: `isOpen`, `isLoading`, `isDirty`, `hasError`, `showCloseButton`

**Types:**
- Interfaces: PascalCase (`User`, `MemoryNode`, `GraphData`, `ChatState`)
- Type aliases: PascalCase (`Theme`, `ToastType`, `ButtonVariant`)
- Backend Python: PascalCase for test classes (`TestRegister`, `TestLogin`)
- Props interfaces: component name + `Props` suffix (`AnansiButtonProps`, `ModalProps`, `BadgeProps`)

## Code Style

**Formatting:**
- **Prettier** configured at root `.prettierrc`
- Semicolons: required (`semi: true`)
- Quotes: single quotes (`singleQuote: true`)
- Trailing commas: everywhere (`trailingComma: "all"`)
- Tab width: 2 spaces
- Print width: 100 characters
- Arrow parens: always
- End of line: LF
- Tailwind CSS classes: sorted via `prettier-plugin-tailwindcss`
- Special tailwind functions: `clsx`, `cn`, `cva` recognized
- Markdown: prose wrap always, 80 char width

**Linting:**
- **ESLint** configured at root `.eslintrc.json`
- Extends: `next/core-web-vitals`, `next/typescript`
- Plugins: `react`
- Key rules:
  - `no-console` – warn, only allow `console.warn` and `console.error`
  - `@typescript-eslint/no-unused-vars` – warn, ignore `_`-prefixed
  - `@typescript-eslint/no-explicit-any` – warn
  - `@typescript-eslint/consistent-type-imports` – warn, prefer `type-imports`
  - `prefer-const` – error
  - `prefer-template` – warn
  - `no-var` – error
  - `eqeqeq` – error, smart mode
  - `no-throw-literal` – error
  - `prefer-promise-reject-errors` – error
  - `curly` – warn, multi-line
  - `react/self-closing-comp` – warn
  - `react/jsx-curly-brace-presence` – warn, never for props/children

**TypeScript:**
- Strict mode enabled (`strict: true`)
- `noUncheckedIndexedAccess: true` – forces undefined checks on indexed access
- `noImplicitOverride: true` – requires `override` keyword
- Target: ES2022
- Path aliases: `@/*` → `./services/frontend/src/*`
- Module: ESNext with bundler resolution

## Import Organization

**Order (TypeScript):**
1. React imports (`import { useState } from "react"`)
2. Next.js imports (`import type { Metadata } from "next"`)
3. Third-party library imports (`import { create } from "zustand"`, `import { cn } from "../../lib/utils"`)
4. Internal relative imports (components, utils, stores)
5. Type-only imports (`import type { ... }`)

**Path Aliases:**
- `@/` → `./services/frontend/src/`
- `@anansi/ui/*` → `./services/frontend/src/components/ui/*`
- `@anansi/lib/*` → `./services/frontend/src/lib/*`
- `@anansi/hooks/*` → `./services/frontend/src/hooks/*`
- `@anansi/stores/*` → `./services/frontend/src/stores/*`
- `@anansi/types/*` → `./services/frontend/src/types/*`
- Project uses both relative imports and `@/` alias — relative more common in components

**Barrel Files:**
- `src/types/index.ts` – single barrel file for all type definitions
- `src/components/ui/` – components exported individually, no barrel file

## Error Handling

**Patterns:**
- Frontend: custom `ApiClientError` class extending `Error` with `status`, `code`, `details`, `requestId` fields (`src/lib/api.ts`)
- Backend: Python exception-based with FastAPI error handlers
- API layer: `try/catch` with `console.error` logging, then state reset (e.g., `set({ isLoadingGraph: false })`)
- Store actions: errors caught and logged via `console.error`, not re-thrown (see `src/stores/brain.ts` line 187)
- Retry logic: `requestWithRetry()` with exponential backoff for 5xx errors, max 3 retries (`src/lib/api.ts` lines 155–173)
- Token refresh: automatic 401 retry with token refresh, redirect to `/login` on failure (`src/lib/api.ts` lines 108–128)

```typescript
// Standard error handling pattern in stores (src/stores/brain.ts)
loadGraph: async () => {
  set({ isLoadingGraph: true });
  try {
    const response = await api.get<GraphData>("/api/v1/brain/graph");
    set({ graphData: response, isLoadingGraph: false });
  } catch (err) {
    console.error("Failed to load graph:", err);
    set({ isLoadingGraph: false });
  }
},
```

- Input validation: `aria-invalid` attribute with error message display (`src/components/ui/Input.tsx`)
- Backend: Pydantic validation with 422 responses

## Logging

**Framework:** `console` (frontend), Python `logging` (backend — configured via `pytest.ini` with `log_cli = true`)

**Patterns:**
- `console.error` for error cases only
- `console.warn` for warnings
- ESLint rule: `no-console` with `allow: ["warn", "error"]` — `console.log` is not permitted
- Backend tests: `log_cli_level = INFO` in `pytest.ini`

## Comments

**When to Comment:**
- Component docstrings: JSDoc `/** ... */` for public components and utility functions (see `src/lib/utils.ts`, `src/components/ui/Skeleton.tsx`)
- Section dividers: `// ── Section Name ──` style for organizing large files (see `src/stores/brain.ts`, `src/stores/workshop.ts`)
- Complex logic: inline comments for non-obvious patterns (e.g., token refresh retry)
- TODO/FIXME: used sparingly — none found in clean code

**JSDoc/TSDoc:**
- Used for public component interfaces and utility functions
- Example from `src/components/ui/Wikilink.tsx`:
```typescript
/**
 * [[wikilink]] component that renders as a clickable pill badge.
 * Inspired by Obsidian's [[wikilink]] notation.
 * Clicking opens the memory detail view.
 */
```
- Example from `src/lib/utils.ts`:
```typescript
/**
 * Merge class names with Tailwind class conflict resolution.
 * Uses clsx for conditional classes and tailwind-merge for conflict resolution.
 */
```

## Function Design

**Size:**
- Components: typically under 120 lines (e.g., `AnansiButton.tsx` 117 lines, `Badge.tsx` 60 lines, `Wikilink.tsx` 56 lines)
- Utility functions: small, single-purpose (5–20 lines each in `src/lib/utils.ts`)
- Store actions: async functions with try/catch pattern, typically 10–30 lines
- Large stores: `src/stores/brain.ts` (358 lines), `src/stores/workshop.ts` (533 lines) — these are large because they contain state + many actions

**Parameters:**
- Components: destructured props object with defaults
- Props interfaces: clearly defined with optional/default values
- Utility functions: simple positional params or options object for 3+ params (see `formatRelativeTime(date: Date | string)`)
- Backend test methods: `self, async_client, ...fixtures` pattern

**Return Values:**
- Components: return JSX or `null` (see `Modal.tsx`: `if (!isOpen) return null;`)
- Utility functions: typed return values
- Store actions: `Promise<void>` for async side-effect actions, typed promises for data-fetching
- Backend test assertions: use `assert` statements

## Module Design

**Exports:**
- Named exports preferred over default exports (every component and utility uses named exports: `export function AnansiButton`, `export const api`)
- Exception: `Input` component in `src/components/ui/Input.tsx` uses `export const Input = forwardRef<...>(...)`
- Backend: Python module docstrings at top of test files (see `tests/e2e/auth.spec.ts` equivalent docstring pattern in `test_auth.py`)

**Barrel Files:**
- `src/types/index.ts` re-exports all type definitions
- No barrel files for components — imported directly by path

## React Conventions

**Component Structure:**
- Function components with explicit props interface
- `"use client"` directive for interactive components that use hooks or browser APIs
- All components are client components when they use state, effects, or event handlers
- Server components where possible (e.g., `src/app/layout.tsx` — no `"use client"`)

**State Management:**
- **Zustand** for global state stores (`src/stores/`)
- Store pattern: define state interface → define actions → `create<State>()` with initial state → action implementations
- Store access via `useStore()` hook in components
- Direct state access in tests via `useStore.getState()` and `useStore.setState()`
- No Redux or Context API used

**Styling:**
- Tailwind CSS v4 with custom CSS variables
- `cn()` utility from `clsx` for conditional class merging (no `tailwind-merge` yet — noted in `src/lib/utils.ts` line 9)
- CSS variables for theming: `var(--color-text-primary)`, `var(--color-bg-deepest)`, `var(--glass-interactive-bg)`, etc.
- Glass morphism design system: `glass-card`, `glass-elevated`, `glass-interactive` classes
- Variant-based styling via `Record<Variant, string>` maps (see `variantClasses` in `AnansiButton.tsx`)

**Hooks:**
- Custom hooks in `src/hooks/` directory
- `useWebSocket` returns `{ isConnected, reconnectAttempts, send, subscribe }`
- Hook pattern: options interface → return interface → implementation with `useRef`, `useCallback`, `useEffect`, `useState`

**Backend Python Conventions:**
- Test classes: PascalCase grouping endpoints (`TestRegister`, `TestLogin`, `TestTokenRefresh`, `TestOAuth`)
- Test methods: `test_<descriptive_name>` with docstrings
- Fixtures: `pytest_asyncio.fixture` for async, `pytest.fixture` for sync
- Markers: `@pytest.mark.asyncio` on each test method, domain markers (`@pytest.mark.brain`, `@pytest.mark.auth`)
- Module docstrings at top of each test file
- `from __future__ import annotations` in test modules
- Raw SQL inserts via `text()` for test data setup (not ORM in many tests)

---

*Convention analysis: 2026-06-13*
