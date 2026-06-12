# ANANSI — Development Team Charter

## Command Structure

```
🧠 Shikamaru (Team Lead / Architect)
├── 🏗️ Agent-01: Scaffold & Infrastructure
│   - Project scaffolding, Docker, CI/CD, configs
│   - Reports to: Shikamaru
├── 🗄️ Agent-02: Database & Data Layer
│   - PostgreSQL schema, Neo4j schema, migrations, indexes
│   - Reports to: Shikamaru
├── ⚙️ Agent-03: Backend Core
│   - FastAPI app, auth, user management, middleware
│   - Reports to: Shikamaru
├── 🎨 Agent-04: Frontend Core
│   - Next.js setup, design system, layout, glassmorphism
│   - Reports to: Shikamaru
├── 🧠 Agent-05: Second Brain Engine
│   - Memory system, wikilinks, graph, summarization, daily notes, spaced repetition
│   - Reports to: Shikamaru
├── 🔧 Agent-06: Agent Workshop
│   - Agent builder canvas, block system, execution engine
│   - Reports to: Shikamaru
├── 🔌 Agent-07: Integrations & API
│   - OAuth connectors, webhooks, Anansi Connect protocol
│   - Reports to: Shikamaru
├── 📱 Agent-08: WhatsApp Channel
│   - WhatsApp bot, linking flow, quick commands, voice notes
│   - Reports to: Shikamaru
├── 🏪 Agent-09: Marketplace & Billing
│   - Marketplace browse/install, creator dashboard, payments, subscriptions
│   - Reports to: Shikamaru
└── 🧪 Agent-10: QA & Testing
    - Test suite, types, linting, E2E tests, review
    - Reports to: Shikamaru
```

## Communication Protocol

1. Each agent is autonomous but **reports all major decisions and outputs to Shikamaru**
2. No agent has authority to change another agent's code without Shikamaru approval
3. API contracts are defined by Shikamaru and must be followed
4. All agents use the same `/data/workspace/anansi-platform/` workspace
5. Output format: files + summary of what was built
6. On completion of a task, agent reports back to Telegram via the spawn channel

## Build Order

```
Wave 1 (Foundation):
  Agent-01 (Scaffold) + Agent-02 (Database) + Agent-03 (Backend) + Agent-04 (Frontend)
      ↓
Wave 2 (Core AI):
  Agent-05 (Brain Engine) + Agent-06 (Workshop)
      ↓
Wave 3 (Ecosystem):
  Agent-07 (Integrations) + Agent-08 (WhatsApp) + Agent-09 (Marketplace)
      ↓
Wave 4 (Quality):
  Agent-10 (QA) — wraps everything with tests
```

## Spec Reference

Full platform spec: `/data/workspace/ANANSI-v2.md`
Team charter: `/data/workspace/anansi-platform/docs/TEAM.md`
