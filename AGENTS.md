# AGENTS.md

Guide for autonomous coding agents operating in this repository.

## Project Overview

- Monorepo with separated frontend/backend services.
- Frontend: Vue 3 + Vite + Pinia + vue-i18n + Vue Router.
- Backend: FastAPI + SQLAlchemy + pytest.
- Infra: Docker Compose + Nginx + MySQL 8.
- Primary docs entrypoint: `README.md`.

## Agent Operating Principles

- Make minimal, targeted edits.
- Match existing patterns in nearby files before introducing new ones.
- Favor test-backed changes over speculative rewrites.
- Do not add tooling (lint/formatter/deps) unless explicitly requested.
- Preserve existing API contract behavior (status codes, payload shapes, errors).

## Build, Test, and Verification Commands

> **⚠️ 部署方式：本專案使用 Docker Compose 運行完整 stack。**
> 前後端皆透過 Docker 啟動，`npm run dev` 和直接跑 uvicorn 不是本專案預設的開發方式。
> - 完整啟動：`docker compose up --build`（或 `COMPOSE_PROJECT_NAME=wakou docker compose up --build`）
> - `npm`、`pytest` 等指令僅用於驗證，不用於啟動服務。

### Root-level verification

- Backend tests: `pytest backend/tests -v`
- Frontend tests: `npm --prefix frontend run test`
- Frontend build: `npm --prefix frontend run build`
- Compose validation: `COMPOSE_PROJECT_NAME=wakou docker compose config`

### Docker / infra

- Full stack up: `docker compose up --build`
- Explicit project-name variant:
  - `COMPOSE_PROJECT_NAME=wakou docker compose up --build`

### Frontend scripts (`frontend/package.json`)

> 以下指令**僅用於測試/建置驗證**，不用於啟動應用程式（應使用 Docker）。

- Dev: `npm --prefix frontend run dev`
- Test: `npm --prefix frontend run test` (runs `vitest run`)
- Build: `npm --prefix frontend run build` (runs `vite build`)
- Preview: `npm --prefix frontend run preview`

## Single-Test Execution (Important)

### Backend (pytest)

- Single file:
  - `pytest backend/tests/auth/test_register_login_refresh.py -v`
- Single function:
  - `pytest backend/tests/auth/test_register_login_refresh.py::test_register_and_login_returns_tokens -v`
- Generic node-id pattern:
  - `pytest path/to/test_file.py::TestClass::test_method -v`

### Frontend (Vitest)

- Single spec file:
  - `npm --prefix frontend run test -- tests/auth/login.spec.ts`
- By test name:
  - `npm --prefix frontend run test -- -t "login stores jwt token and redirects to home"`
- Direct command from `frontend/`:
  - `vitest run tests/auth/login.spec.ts`

## Lint / Format / Typecheck Reality

- No root/frontend lint script currently configured.
- No root/frontend formatter script currently configured.
- Do not claim lint pass status as part of completion unless tooling is added later.
- Pyright is configured in:
  - `pyrightconfig.json`
  - `backend/pyrightconfig.json`
- Current backend pyright profile is permissive (many unknown/any reports disabled).

## Backend Style Guidelines (FastAPI / Python)

### Imports and module boundaries

- Use grouped imports: stdlib -> third-party -> local.
- Keep routers/services/schemas/models separated under `backend/app/modules/*`.
- Keep route handlers thin; put business logic in services.

### Naming and types

- `snake_case`: functions, variables.
- `PascalCase`: classes, Pydantic models.
- Use explicit payload schemas via Pydantic `BaseModel`.
- Add type hints on public/new functions where practical.
- Follow existing Python 3.10+ syntax (`|`, `list[...]`, `dict[...]`).

### Error handling and HTTP behavior

- Use `HTTPException` with explicit status and detail.
- Stay consistent with existing semantics:
  - auth failures -> `401`
  - insufficient role -> `403`
  - missing entity -> `404`
  - duplicate/conflict -> `409`
- Prefer narrow exception catches and rethrow with context (`from exc`) when needed.
- Avoid silent catches.

### Backend tests

- Use pytest function style: `def test_*`.
- Reuse fixtures from `backend/tests/conftest.py` (`client`, `admin_token`, `buyer_token`, etc.).
- Assert status code and key contract fields.

## Frontend Style Guidelines (Vue 3 / Vite)

### Structure and responsibilities

- Route/views: `frontend/src/app`.
- Domain logic/services: `frontend/src/modules/*`.
- Keep fetch/data code in service/api modules, not spread across components.

### Naming and imports

- Use ES module imports with double quotes.
- `PascalCase`: components/views.
- `camelCase`: functions, refs, computed values.
- Reuse existing key conventions (`wakou_*` localStorage keys, established route names).

### State, routing, and storage

- Use Pinia as canonical client state for auth and shared app state.
- Router access control lives in `frontend/src/app/router.js`.
- Guard storage access with browser checks (`typeof window === "undefined"`).

### Network and error patterns

- Service functions use `fetch` + `response.ok` checks.
- Throw `Error` on failure with stable message patterns:
  - `"<action> failed"`
  - `"<action> failed (<status>)"`
- In views, handle async failures with `try/catch` and set UI state fields.

### Styling conventions

- Existing UI uses CSS variables (`--ink-*`, `--paper-*`, `--accent-*`).
- Preserve existing visual language unless redesign is explicitly requested.
- Maintain responsiveness patterns already present in views.

### Frontend tests

- Test framework: Vitest (`frontend/vitest.config.js`, `environment: "jsdom"`).
- Current style: `describe/it/expect` with mocked `globalThis.fetch` where needed.
- Test location/pattern: `frontend/tests/**`, `*.spec.ts`.

## Cursor/Copilot Rules Status

- `.cursorrules`: not found.
- `.cursor/rules/`: not found.
- `.github/copilot-instructions.md`: not found.
- If added later, treat them as top-priority repository instructions.

## Recommended Agent Workflow

1. Read nearby files and copy local patterns first.
2. Implement smallest viable change.
3. Run narrow tests first (single test/file), then broader scope.
4. For frontend touches, run `npm --prefix frontend run build` before closing.
5. For backend touches, run relevant `pytest` scopes before closing.
6. Report pre-existing failures separately from regressions introduced by your change.

## Quick Command Reference

- Backend tests all: `pytest backend/tests -v`
- Backend single test: `pytest path/to/test.py::test_name -v`
- Frontend tests all: `npm --prefix frontend run test`
- Frontend single spec: `npm --prefix frontend run test -- tests/path/file.spec.ts`
- Frontend build: `npm --prefix frontend run build`
- Docker full stack: `docker compose up --build`
