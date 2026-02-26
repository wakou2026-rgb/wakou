# Wakou Fullstack MVP

This repository contains a frontend/backend-separated MVP baseline for Wakou Vintage Select.

## Tech Stack

- Frontend: Vue 3 + Vite + Pinia + vue-i18n + Vue Router
- Backend: FastAPI + pytest
- Infra: Docker Compose + Nginx + MySQL 8

## Quick Start (Docker)

```bash
docker compose up --build
```

If your environment reports `project name must not be empty`, set a project name explicitly:

```bash
COMPOSE_PROJECT_NAME=wakou docker compose up --build
```

## Service URLs

- Frontend: `http://localhost/`
- Backend health: `http://localhost/api/v1/health`

## Local Verification Commands

```bash
pytest backend/tests -v
npm --prefix frontend run test
npm --prefix frontend run build
COMPOSE_PROJECT_NAME=wakou docker compose config
```

## Environment Variables

See `.env.example` for baseline values.

- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- `JWT_SECRET`, `JWT_ALGORITHM`

## Demo Accounts (MVP scaffold)

Register via API with role:

- Buyer: `buyer@example.com` / `Pass123!`
- Admin: `admin@example.com` / `Pass123!`

These accounts are in-memory for scaffold testing and reset per test run.
