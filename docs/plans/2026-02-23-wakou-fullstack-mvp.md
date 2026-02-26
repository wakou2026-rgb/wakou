# Wakou Fullstack MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-style, frontend/backend-separated MVP website for Wakou Vintage Select with full user/admin flows, ECPay sandbox, and Dockerized deployment.

**Architecture:** Use a monorepo with Vue 3 frontend and FastAPI backend connected by REST API. Use MySQL 8 as system of record, with role-based JWT auth and modular domains (products, warehouse timeline, cart/orders, communication room, admin). Reverse proxy and static serving via Nginx with Docker Compose orchestration.

**Tech Stack:** Vue 3 + Vite + Tailwind CSS + Vue Router + Pinia + vue-i18n, FastAPI + SQLAlchemy + Alembic + Pydantic + pytest, MySQL 8, Docker + Docker Compose + Nginx, ECPay sandbox.

---

### Task 1: Monorepo and Container Baseline

**Files:**
- Create: `frontend/`
- Create: `backend/`
- Create: `infra/nginx/default.conf`
- Create: `docker-compose.yml`
- Create: `.env.example`

**Step 1: Write the failing integration test target**

Create `backend/tests/smoke/test_health_contract.py`:

```python
def test_health_contract_shape(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["service"] == "wakou-api"
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/smoke/test_health_contract.py -v`
Expected: FAIL (app/service not scaffolded yet)

**Step 3: Implement minimal structure**

- Add FastAPI app entrypoint and `/api/v1/health`
- Add Dockerfiles for frontend/backend
- Add Compose services: `frontend`, `backend`, `db`, `nginx`

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/smoke/test_health_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend frontend infra docker-compose.yml .env.example
git commit -m "chore: scaffold fullstack monorepo and container baseline"
```

### Task 2: Auth and RBAC Foundation

**Files:**
- Create: `backend/app/modules/auth/*`
- Create: `backend/tests/auth/test_register_login_refresh.py`
- Create: `backend/tests/auth/test_rbac_guard.py`

**Step 1: Write failing tests**

```python
def test_register_and_login_returns_tokens(client):
    r = client.post("/api/v1/auth/register", json={"email":"a@b.com","password":"Pass123!","role":"buyer"})
    assert r.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email":"a@b.com","password":"Pass123!"})
    assert login.status_code == 200
    assert "access_token" in login.json()

def test_buyer_cannot_access_admin_endpoint(client, buyer_token):
    r = client.get("/api/v1/admin/products", headers={"Authorization":f"Bearer {buyer_token}"})
    assert r.status_code == 403
```

**Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/auth -v`
Expected: FAIL with missing auth routes/guards

**Step 3: Write minimal implementation**

- JWT access/refresh tokens
- Password hashing
- Role guard (`buyer`, `admin`)
- Auth endpoints (`register`, `login`, `refresh`, `me`)

**Step 4: Run tests to verify pass**

Run: `pytest backend/tests/auth -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/modules/auth backend/tests/auth
git commit -m "feat: add jwt auth and role-based access control"
```

### Task 3: Core Catalog and Warehouse Timeline APIs

**Files:**
- Create: `backend/app/modules/products/*`
- Create: `backend/app/modules/warehouse/*`
- Create: `backend/tests/products/test_products_query.py`
- Create: `backend/tests/warehouse/test_timeline.py`

**Step 1: Write failing tests**

```python
def test_product_list_supports_filters(client):
    r = client.get("/api/v1/products?category=watch&lang=zh-Hant")
    assert r.status_code == 200
    assert isinstance(r.json()["items"], list)

def test_warehouse_timeline_sorted_desc(client):
    r = client.get("/api/v1/warehouse/timeline")
    assert r.status_code == 200
    items = r.json()["items"]
    assert items == sorted(items, key=lambda x: x["arrived_at"], reverse=True)
```

**Step 2: Run tests to verify fail**

Run: `pytest backend/tests/products backend/tests/warehouse -v`
Expected: FAIL

**Step 3: Implement minimal code**

- Product model with multilingual fields
- Product listing/detail APIs
- Warehouse log model and timeline API

**Step 4: Run tests to verify pass**

Run: `pytest backend/tests/products backend/tests/warehouse -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/modules/products backend/app/modules/warehouse backend/tests/products backend/tests/warehouse
git commit -m "feat: implement product catalog and warehouse timeline apis"
```

### Task 4: Cart, Order, Communication Room Workflow

**Files:**
- Create: `backend/app/modules/cart/*`
- Create: `backend/app/modules/orders/*`
- Create: `backend/app/modules/comm_room/*`
- Create: `backend/tests/orders/test_comm_room_flow.py`

**Step 1: Write failing tests**

```python
def test_buyer_order_enters_comm_room(client, buyer_token):
    r = client.post("/api/v1/orders", json={"product_id":1,"mode":"inquiry"}, headers={"Authorization":f"Bearer {buyer_token}"})
    assert r.status_code == 201
    room = client.get(f"/api/v1/comm-rooms/{r.json()['comm_room_id']}", headers={"Authorization":f"Bearer {buyer_token}"})
    assert room.status_code == 200

def test_admin_sets_shipping_quote(client, admin_token, seeded_room_id):
    r = client.post(f"/api/v1/comm-rooms/{seeded_room_id}/shipping-quote", json={"currency":"TWD","amount":320}, headers={"Authorization":f"Bearer {admin_token}"})
    assert r.status_code == 200
```

**Step 2: Run tests to verify fail**

Run: `pytest backend/tests/orders/test_comm_room_flow.py -v`
Expected: FAIL

**Step 3: Implement minimal workflow**

- Cart APIs and checkout draft
- Order creation modes: `buy_now` and `inquiry`
- Comm-room messages and shipping quote update
- Status transitions: `created -> waiting_quote -> buyer_confirmed -> paid`

**Step 4: Run tests to verify pass**

Run: `pytest backend/tests/orders/test_comm_room_flow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/modules/cart backend/app/modules/orders backend/app/modules/comm_room backend/tests/orders
git commit -m "feat: add cart order and communication room workflows"
```

### Task 5: ECPay Sandbox Integration

**Files:**
- Create: `backend/app/integrations/ecpay/*`
- Create: `backend/tests/payments/test_ecpay_sandbox.py`

**Step 1: Write failing test**

```python
def test_create_ecpay_checkout_form_for_order(client, buyer_token, payable_order_id):
    r = client.post(f"/api/v1/payments/ecpay/{payable_order_id}", headers={"Authorization":f"Bearer {buyer_token}"})
    assert r.status_code == 200
    assert "CheckMacValue" in r.json()["payload"]
```

**Step 2: Run test to verify fail**

Run: `pytest backend/tests/payments/test_ecpay_sandbox.py -v`
Expected: FAIL

**Step 3: Implement minimal integration**

- Build ECPay sandbox payload signer
- Create payment initiation endpoint
- Create callback endpoint to update order status to `paid`

**Step 4: Run test to verify pass**

Run: `pytest backend/tests/payments/test_ecpay_sandbox.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/integrations/ecpay backend/tests/payments
git commit -m "feat: integrate ecpay sandbox payment flow"
```

### Task 6: Admin APIs (Product/Order/Warehouse Management)

**Files:**
- Create: `backend/app/modules/admin/*`
- Create: `backend/tests/admin/test_admin_crud.py`

**Step 1: Write failing tests**

```python
def test_admin_can_create_product(client, admin_token):
    r = client.post("/api/v1/admin/products", json={"sku":"WK-001","grade":"A","price_twd":12800}, headers={"Authorization":f"Bearer {admin_token}"})
    assert r.status_code == 201

def test_admin_can_export_orders_csv(client, admin_token):
    r = client.get("/api/v1/admin/orders/export.csv", headers={"Authorization":f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
```

**Step 2: Run tests to verify fail**

Run: `pytest backend/tests/admin/test_admin_crud.py -v`
Expected: FAIL

**Step 3: Implement minimal admin endpoints**

- Product CRUD
- Warehouse log CRUD
- Order status/review update
- CSV export

**Step 4: Run tests to verify pass**

Run: `pytest backend/tests/admin/test_admin_crud.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/modules/admin backend/tests/admin
git commit -m "feat: add admin management apis and csv export"
```

### Task 7: Frontend App Shell, i18n, and Auth

**Files:**
- Create: `frontend/src/app/*`
- Create: `frontend/src/i18n/*`
- Create: `frontend/src/modules/auth/*`
- Create: `frontend/tests/auth/login.spec.ts`

**Step 1: Write failing test**

```typescript
import { test, expect } from 'vitest'

test('login stores jwt token and redirects to home', async () => {
  expect(true).toBe(false)
})
```

**Step 2: Run test to verify fail**

Run: `npm --prefix frontend run test -- login.spec.ts`
Expected: FAIL

**Step 3: Implement minimal app shell**

- Router layout
- i18n (`zh-Hant`, `ja`, `en`)
- Auth store and login view

**Step 4: Run test to verify pass**

Run: `npm --prefix frontend run test -- login.spec.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src frontend/tests
git commit -m "feat: add frontend shell i18n and auth flow"
```

### Task 8: Frontend Buyer Flows

**Files:**
- Create: `frontend/src/modules/catalog/*`
- Create: `frontend/src/modules/cart/*`
- Create: `frontend/src/modules/checkout/*`
- Create: `frontend/src/modules/comm-room/*`
- Create: `frontend/tests/buyer/buyer-flow.spec.ts`

**Step 1: Write failing e2e-like test**

```typescript
test('buyer can browse add to cart checkout and open comm room', async () => {
  expect(true).toBe(false)
})
```

**Step 2: Run test to verify fail**

Run: `npm --prefix frontend run test -- buyer-flow.spec.ts`
Expected: FAIL

**Step 3: Implement minimal buyer views**

- Catalog list/detail
- Japan warehouse timeline page
- Cart and checkout page
- Comm room page (messages + shipping quote)

**Step 4: Run test to verify pass**

Run: `npm --prefix frontend run test -- buyer-flow.spec.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/modules frontend/tests/buyer
git commit -m "feat: implement buyer-facing catalog checkout and comm-room flows"
```

### Task 9: Frontend Admin Console

**Files:**
- Create: `frontend/src/modules/admin/*`
- Create: `frontend/tests/admin/admin-console.spec.ts`

**Step 1: Write failing test**

```typescript
test('admin can create product and update order status', async () => {
  expect(true).toBe(false)
})
```

**Step 2: Run test to verify fail**

Run: `npm --prefix frontend run test -- admin-console.spec.ts`
Expected: FAIL

**Step 3: Implement minimal admin pages**

- Product management
- Warehouse timeline management
- Order review + shipping quote input

**Step 4: Run test to verify pass**

Run: `npm --prefix frontend run test -- admin-console.spec.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/modules/admin frontend/tests/admin
git commit -m "feat: add admin console for products warehouse and orders"
```

### Task 10: End-to-End Verification and Docs

**Files:**
- Create: `README.md`
- Create: `docs/api/openapi-notes.md`

**Step 1: Write failing smoke test expectation**

Document command contract in `README.md` for these checks:
- `docker compose up --build`
- Frontend available at `/`
- Backend health at `/api/v1/health`

**Step 2: Run full verification**

Run:
- `pytest backend/tests -v`
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`
- `docker compose config`

Expected: PASS / exit code 0

**Step 3: Finalize docs**

- Env variables (DB, JWT, ECPay sandbox keys)
- Local and docker run instructions
- Admin and buyer demo accounts

**Step 4: Re-run verification**

Run all commands again and confirm green.

**Step 5: Commit**

```bash
git add README.md docs
git commit -m "docs: add runbook and verification guide for fullstack mvp"
```
