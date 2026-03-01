# 和光精選 Full-Stack Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three known frontend bugs (categories 404, magazine garbled, admin/frontend desync) and wire up a complete admin backend covering dynamic categories, enhanced products, CRM + comm-room management, and finance reporting—all backed by the MySQL DB.

**Architecture:** The backend already has well-structured modules (`products`, `magazines`, `orders`, `crm`, `costs`, `events`). Most of the module ORM, service, and router scaffolding is in place but either not registered in `main.py`, not seeded to the DB, or not connected to the admin frontend. The plan adds/fixes only what is missing and removes in-memory shims once DB equivalents exist.

**Tech Stack:** FastAPI + SQLAlchemy (MySQL / SQLite), Vue 3 + Element Plus (admin), Vue 3 + Pinia (frontend), pytest, Vitest, Docker Compose + Nginx.

---

## GROUND TRUTH — what already exists

| Layer | What's there | Gap |
|---|---|---|
| `backend/app/modules/products` | Full CRUD router+service+schema | Missing `description_zh/ja/en`, `preview_images`, `detail_images`, `stock_qty`, `cost_twd` columns |
| `backend/app/modules/magazines` | Full DB CRUD router + service + schema | `reset_state()` seeds in-memory `MAGAZINES` list, never writes to DB → public endpoint returns empty |
| `backend/app/modules/orders` | DB model + router (with in-memory fallback) | Orders in main.py still in-memory; router has explicit fallback |
| `backend/app/modules/crm` | `BuyerNote`, `PointsLedger`, `PointsPolicy` | CommRoom CRUD API not exposed in admin |
| `backend/app/modules/costs` | `Cost` model + admin router (`/costs`, `/report/*`) | Not registered in `main.py` |
| `backend/app/modules/events` | `AuditEvent` model | router not registered |
| `backend/app/main.py` | In-memory `CATEGORIES`, `/api/v1/categories` route | Route exists (line 1997) but reads in-memory `CATEGORIES` list — dies if `MAGAZINES` are not seeded |
| `admin/src/views/finance` | Chart + cost list | Already wired to correct DB-backed API |
| `admin/src/views/products` | Product CRUD | Categories are hardcoded, not fetched from API |
| `admin/src/views/magazine` | Magazine CRUD | Already wired to DB router |
| `admin/src/views/crm` | Buyer notes + points | No comm-room view |
| `admin/src/views/orders` | Order list | Wired to DB router |

---

## Task 1: Register missing backend routers

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Confirm which routers are missing**

Open `backend/app/main.py` lines 45-50 — currently only these are registered:
```
app.include_router(product_router.router)
app.include_router(product_router.admin_router)
app.include_router(auth_router_module.admin_router)
app.include_router(magazine_router_module.router)
app.include_router(magazine_router_module.public_router)
```

Missing registrations: `costs.router`, `crm.router`, `orders.router`, `events.router`.

**Step 2: Add imports and registrations**

At the top of `main.py` after line 26, add:
```python
costs_router_module = importlib.import_module("app.modules.costs.router")
crm_router_module = importlib.import_module("app.modules.crm.router")
orders_router_module = importlib.import_module("app.modules.orders.router")
```

After line 50 (`app.include_router(magazine_router_module.public_router)`), add:
```python
app.include_router(costs_router_module.router)
app.include_router(crm_router_module.router)
app.include_router(orders_router_module.router)
```

**Step 3: Run backend tests**

```bash
pytest backend/tests -v
```
Expected: all existing tests pass, no import errors.

**Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(backend): register costs, crm, orders routers in main.py"
```

---

## Task 2: Fix magazine DB seed — write articles to DB in reset_state()

**Context:** `reset_state()` (main.py ~line 621) populates in-memory `MAGAZINES` list with rich article data but never writes to the `magazine_articles` DB table. The public endpoint `GET /api/v1/magazines` calls `list_articles(session, published_only=True)` which reads from DB → returns empty list → frontend shows garbled/empty state.

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Add magazine_article DB module import at top of main.py**

After line 25 (`product_models = importlib.import_module("app.modules.products.models")`), add:
```python
magazine_models = importlib.import_module("app.modules.magazines.models")
```

And after line 34 (`Product = product_models.Product`), add:
```python
MagazineArticle = magazine_models.MagazineArticle
```

**Step 2: In reset_state(), after the MAGAZINES.extend(...) block (around line 1067), add DB write**

Find where `article_id_cursor` finishes (around line 1067-1068). After `next_mag_article_id = article_id_cursor`, add a new DB session block:

```python
# Write magazine articles to DB
session = SessionLocal()
try:
    session.execute(delete(MagazineArticle))
    import json as _json
    for brand_block in MAGAZINES:
        brand = brand_block.get("brand", "")
        for content in brand_block.get("contents", []):
            article = MagazineArticle(
                id=int(content.get("article_id", 0)),
                brand=brand,
                slug=str(content.get("slug", "")),
                title_zh=str(content.get("title", {}).get("zh-Hant", "")),
                title_ja=str(content.get("title", {}).get("ja", "")),
                title_en=str(content.get("title", {}).get("en", "")),
                desc_zh=str(content.get("description", {}).get("zh-Hant", "")),
                desc_ja=str(content.get("description", {}).get("ja", "")),
                desc_en=str(content.get("description", {}).get("en", "")),
                body_zh=str(content.get("body", {}).get("zh-Hant", "")),
                body_ja=str(content.get("body", {}).get("ja", "")),
                body_en=str(content.get("body", {}).get("en", "")),
                image_url=str(content.get("image_url", "")),
                gallery_urls_json=_json.dumps(content.get("gallery_urls", [])),
                published=content.get("status", "published") == "published",
            )
            session.add(article)
    session.commit()
finally:
    session.close()
```

**Step 3: Verify — run backend tests**

```bash
pytest backend/tests -v
```
Expected: tests pass. No magazine-related failures.

**Step 4: Verify magazine endpoint manually (optional)**

```bash
COMPOSE_PROJECT_NAME=wakou docker compose up --build -d
curl http://localhost/api/v1/magazines
```
Expected: JSON with `articles` array containing 2+ items with non-empty `title["zh-Hant"]`.

**Step 5: Commit**

```bash
git add backend/app/main.py
git commit -m "fix(backend): seed magazine articles to DB in reset_state so public endpoint returns data"
```

---

## Task 3: Add a proper `/api/v1/categories` DB-backed endpoint

**Context:** The existing `GET /api/v1/categories` route (main.py line 1997) reads from the in-memory `CATEGORIES` list, which is populated by `reset_state()` / `bootstrap_state()`. This is fragile — there's no `categories` table yet. The simplest correct fix is to create a `Category` DB model, seed it in `reset_state()`, and return from DB.

**Files:**
- Create: `backend/app/modules/categories/` (new module)
  - `__init__.py`
  - `models.py`
  - `router.py`
- Modify: `backend/app/main.py`

### Step 1: Create the categories module

Create `backend/app/modules/categories/__init__.py` (empty):
```python
```

Create `backend/app/modules/categories/models.py`:
```python
from __future__ import annotations
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from ...core.db import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # slug: "watch", "bag", etc.
    title_zh: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title_ja: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title_en: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

Create `backend/app/modules/categories/router.py`:
```python
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .models import Category

public_router = APIRouter(prefix="/api/v1/categories", tags=["categories"])
admin_router = APIRouter(prefix="/api/v1/admin/categories", tags=["admin-categories"])


def _row_to_dict(cat: Category) -> dict[str, Any]:
    return {
        "id": cat.id,
        "title": {"zh-Hant": cat.title_zh, "ja": cat.title_ja, "en": cat.title_en},
        "image": cat.image_url,
        "sort_order": cat.sort_order,
        "is_active": cat.is_active,
    }


@public_router.get("")
def list_categories(session: Session = Depends(get_db_session)) -> dict:
    cats = list(session.scalars(
        select(Category).where(Category.is_active == True).order_by(Category.sort_order)  # noqa: E712
    ))
    return {"items": [_row_to_dict(c) for c in cats]}


@admin_router.get("")
def admin_list_categories(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales", "maintenance"])),
) -> dict:
    cats = list(session.scalars(select(Category).order_by(Category.sort_order)))
    return {"items": [_row_to_dict(c) for c in cats]}


@admin_router.post("", status_code=201)
def admin_create_category(
    payload: dict,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    cat_id = str(payload.get("id", "")).strip()
    if not cat_id:
        raise HTTPException(status_code=400, detail="id is required")
    existing = session.get(Category, cat_id)
    if existing:
        raise HTTPException(status_code=409, detail="category already exists")
    title = payload.get("title", {})
    cat = Category(
        id=cat_id,
        title_zh=title.get("zh-Hant", ""),
        title_ja=title.get("ja", ""),
        title_en=title.get("en", ""),
        image_url=str(payload.get("image", "")),
        sort_order=int(payload.get("sort_order", 0)),
        is_active=bool(payload.get("is_active", True)),
    )
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return _row_to_dict(cat)


@admin_router.patch("/{cat_id}")
def admin_update_category(
    cat_id: str,
    payload: dict,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    cat = session.get(Category, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="category not found")
    if "title" in payload:
        title = payload["title"]
        if "zh-Hant" in title:
            cat.title_zh = title["zh-Hant"]
        if "ja" in title:
            cat.title_ja = title["ja"]
        if "en" in title:
            cat.title_en = title["en"]
    if "image" in payload:
        cat.image_url = payload["image"]
    if "sort_order" in payload:
        cat.sort_order = int(payload["sort_order"])
    if "is_active" in payload:
        cat.is_active = bool(payload["is_active"])
    session.commit()
    session.refresh(cat)
    return _row_to_dict(cat)


@admin_router.delete("/{cat_id}", status_code=200)
def admin_delete_category(
    cat_id: str,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    cat = session.get(Category, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="category not found")
    session.delete(cat)
    session.commit()
    return {"ok": True}
```

**Step 2: Register categories module in main.py**

After line 26 (other importlib lines), add:
```python
categories_router_module = importlib.import_module("app.modules.categories.router")
```

After the existing `include_router` lines (after line 50), add:
```python
app.include_router(categories_router_module.public_router)
app.include_router(categories_router_module.admin_router)
```

Also remove (or keep as alias) the old in-memory `/api/v1/categories` route at line 1997 — **delete** it to avoid route conflict.

**Step 3: Import Category in reset_state() and seed it**

In main.py, add Category import after other model imports:
```python
Category = categories_router_module.Category  # re-use from router module
```

Wait — better to import the model directly. After line 34 (`Product = product_models.Product`), add:
```python
categories_model_module = importlib.import_module("app.modules.categories.models")
Category = categories_model_module.Category
```

In `reset_state()`, find `CATEGORIES.extend([...])` around line 1022-1029 and add a DB seed block **after** it:
```python
# Seed categories to DB
session_cat = SessionLocal()
try:
    from sqlalchemy import delete as _delete
    session_cat.execute(_delete(Category))
    seed_categories = [
        Category(id="watch", title_zh="經典腕錶", title_ja="クラシックウォッチ", title_en="Classic Watches", image_url="/Watches.png", sort_order=0),
        Category(id="bag", title_zh="復古包款", title_ja="ヴィンテージバッグ", title_en="Vintage Bags", image_url="/Handbags.png", sort_order=1),
        Category(id="jewelry", title_zh="珠寶飾品", title_ja="ジュエリー", title_en="Jewelry", image_url="/Jewelry.png", sort_order=2),
        Category(id="apparel", title_zh="珍藏服飾", title_ja="コレクションアパレル", title_en="Apparel", image_url="/Apparel.png", sort_order=3),
        Category(id="lifestyle", title_zh="藝術擺件", title_ja="ライフスタイル", title_en="Lifestyle", image_url="/Lifestyle.png", sort_order=4),
        Category(id="accessory", title_zh="特選配件", title_ja="セレクトアクセサリー", title_en="Accessories", image_url="/Wallets.png", sort_order=5),
    ]
    session_cat.add_all(seed_categories)
    session_cat.commit()
finally:
    session_cat.close()
```

**Step 4: Add `categories` table to Base.metadata.create_all**

`Base.metadata.create_all(bind=engine)` already runs in `reset_state()` (line 623) — since `Category` now extends `Base`, it will auto-create the table. ✓

**Step 5: Run backend tests**

```bash
pytest backend/tests -v
```
Expected: all pass.

**Step 6: Test the public endpoint**

```bash
COMPOSE_PROJECT_NAME=wakou docker compose up --build -d
curl http://localhost/api/v1/categories
```
Expected: `{"items": [{"id": "watch", "title": {"zh-Hant": "經典腕錶", ...}, "image": "/Watches.png", ...}, ...]}`

**Step 7: Commit**

```bash
git add backend/app/modules/categories/ backend/app/main.py
git commit -m "feat(backend): add Category model, DB-backed /api/v1/categories, admin CRUD"
```

---

## Task 4: Add extended product fields (description, images, stock, cost)

**Context:** The `Product` ORM model is missing: `description_zh/ja/en`, `preview_images_json`, `detail_images_json`, `stock_qty`, `cost_twd`. The admin frontend stores these in-memory via the `PRODUCTS` list. We need to add them to DB so the admin can persist real product data.

**Files:**
- Modify: `backend/app/modules/products/models.py`
- Modify: `backend/app/modules/products/schemas.py`
- Modify: `backend/app/modules/products/service.py`
- Modify: `backend/app/modules/products/router.py`
- Modify: `backend/app/main.py` (seed with descriptions)

**Step 1: Add columns to Product model**

In `backend/app/modules/products/models.py`, after line 25 (`size` column), add:
```python
    description_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_ja: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    preview_images_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    detail_images_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    stock_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost_twd: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

**Step 2: Update AdminProductPayload schema**

In `backend/app/modules/products/schemas.py`, add to `AdminProductPayload`:
```python
    description: dict[str, str] | None = None
    preview_images: list[str] | None = None
    detail_images: list[str] | None = None
    stock_qty: int = 1
    cost_twd: int | None = None
```

And to `AdminProductUpdatePayload`:
```python
    description: dict[str, str] | None = None
    preview_images: list[str] | None = None
    detail_images: list[str] | None = None
    stock_qty: int | None = None
    cost_twd: int | None = None
```

And to `ProductItem` / `ProductDetailResponse`:
```python
    description: str = ""  # already exists — change to dict[str, str]
    preview_images: list[str] = []
    detail_images: list[str] = []
    stock_qty: int = 1
    cost_twd: int | None = None
```

**Step 3: Update service.py**

In `backend/app/modules/products/service.py`, update `resolve_product_extra` (or create it if missing) to read from DB columns instead of in-memory PRODUCTS cache:
```python
def resolve_product_extra(product: Product, lang: str) -> tuple[str, list[str]]:
    import json
    desc_map = {
        "zh-Hant": product.description_zh or "",
        "ja": product.description_ja or "",
        "en": product.description_en or "",
    }
    description = desc_map.get(lang) or desc_map.get("en", "")
    try:
        preview = json.loads(product.preview_images_json or "[]")
    except (ValueError, TypeError):
        preview = []
    return description, preview
```

**Step 4: Update router.py `_build_product_item`**

Pass the full `product` object (not just `product.id`) to `resolve_product_extra`. Update the call signature throughout `router.py`.

**Step 5: Update admin_create_product and admin_update_product in router.py**

In `admin_create_product`:
```python
    import json as _json
    desc = payload.description or {}
    product = Product(
        ...existing fields...,
        description_zh=desc.get("zh-Hant", ""),
        description_ja=desc.get("ja", ""),
        description_en=desc.get("en", ""),
        preview_images_json=_json.dumps(payload.preview_images or []),
        detail_images_json=_json.dumps(payload.detail_images or []),
        stock_qty=payload.stock_qty,
        cost_twd=payload.cost_twd,
    )
```

In `admin_update_product`, add corresponding field updates.

**Step 6: Update reset_state() seed in main.py**

For each product in the seed `Product(...)` calls, pass:
```python
    description_zh="...",
    description_ja="...",
    description_en="...",
    preview_images_json='["/Watches.png"]',
```
(Use the existing descriptions from the in-memory `PRODUCTS.extend` block.)

**Step 7: Run backend tests**

```bash
pytest backend/tests -v
```
Expected: all pass.

**Step 8: Commit**

```bash
git add backend/app/modules/products/ backend/app/main.py
git commit -m "feat(backend): add description, images, stock_qty, cost_twd columns to Product model"
```

---

## Task 5: Add CommRoom/CommMessage admin API endpoints

**Context:** CommRooms exist in DB (`comm_rooms`, `comm_messages` tables in `orders/models.py`) but there are no DB-backed admin endpoints to list rooms, get messages, or post replies. The current admin `COMM_ROOMS` data is in-memory only.

**Files:**
- Create: `backend/app/modules/orders/comm_router.py`
- Modify: `backend/app/main.py`

**Step 1: Create comm_router.py**

```python
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .models import CommRoom, CommMessage, Order

router = APIRouter(prefix="/api/v1/admin/comm-rooms", tags=["admin-comm-rooms"])


def _room_to_dict(room: CommRoom, messages: list[CommMessage], order: Order | None) -> dict[str, Any]:
    return {
        "id": room.id,
        "order_id": room.order_id,
        "buyer_email": room.buyer_email,
        "product_id": order.product_id if order else None,
        "product_name": order.product_name if order else "",
        "status": room.status,
        "final_price_twd": room.final_price_twd,
        "shipping_fee_twd": room.shipping_fee_twd,
        "discount_twd": room.discount_twd,
        "transfer_proof_url": room.transfer_proof_url,
        "created_at": room.created_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "from": m.sender_role,
                "sender_email": m.sender_email,
                "message": m.message,
                "image_url": m.image_url,
                "timestamp": m.created_at.isoformat(),
            }
            for m in sorted(messages, key=lambda x: x.id)
        ],
    }


@router.get("")
def admin_list_comm_rooms(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    rooms = list(session.scalars(select(CommRoom).order_by(CommRoom.id.desc())))
    result = []
    for room in rooms:
        msgs = list(session.scalars(select(CommMessage).where(CommMessage.room_id == room.id)))
        order = session.get(Order, room.order_id)
        result.append(_room_to_dict(room, msgs, order))
    return {"items": result, "total": len(result)}


@router.get("/{room_id}")
def admin_get_comm_room(
    room_id: int,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    room = session.get(CommRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="comm room not found")
    msgs = list(session.scalars(select(CommMessage).where(CommMessage.room_id == room_id)))
    order = session.get(Order, room.order_id)
    return _room_to_dict(room, msgs, order)


@router.post("/{room_id}/messages", status_code=201)
def admin_post_message(
    room_id: int,
    payload: dict,
    session: Session = Depends(get_db_session),
    current_user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    room = session.get(CommRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="comm room not found")
    if room.status == "closed":
        raise HTTPException(status_code=400, detail="comm room is closed")
    msg = CommMessage(
        room_id=room_id,
        sender_email=current_user.email,
        sender_role=current_user.role,
        message=str(payload.get("message", "")),
        image_url=payload.get("image_url"),
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return {
        "id": msg.id,
        "from": msg.sender_role,
        "sender_email": msg.sender_email,
        "message": msg.message,
        "image_url": msg.image_url,
        "timestamp": msg.created_at.isoformat(),
    }


@router.patch("/{room_id}/status")
def admin_set_room_status(
    room_id: int,
    payload: dict,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    room = session.get(CommRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="comm room not found")
    new_status = str(payload.get("status", "")).strip()
    if new_status not in {"open", "closed", "waiting_quote", "quoted", "paid", "completed"}:
        raise HTTPException(status_code=400, detail="invalid status")
    room.status = new_status
    session.commit()
    return {"ok": True, "status": new_status}
```

**Step 2: Register comm_router in main.py**

After line 26, add:
```python
comm_router_module = importlib.import_module("app.modules.orders.comm_router")
```

After `app.include_router(orders_router_module.router)` (from Task 1), add:
```python
app.include_router(comm_router_module.router)
```

**Step 3: Run backend tests**

```bash
pytest backend/tests -v
```
Expected: all pass.

**Step 4: Commit**

```bash
git add backend/app/modules/orders/comm_router.py backend/app/main.py
git commit -m "feat(backend): add DB-backed comm-room admin CRUD with reply and status toggle"
```

---

## Task 6: Add notification config endpoint (LINE/Discord/Email)

**Context:** User wants notifications when a new message arrives in a comm room. We need a simple config store and a webhook trigger function.

**Files:**
- Create: `backend/app/modules/orders/notification.py`
- Modify: `backend/app/modules/orders/comm_router.py`
- Modify: `backend/app/main.py`

**Step 1: Create notification.py**

```python
from __future__ import annotations
import json
import os
import httpx

# Simple file-based config (Docker volume persistent)
_CONFIG_PATH = os.getenv("NOTIFICATION_CONFIG_PATH", "/tmp/wakou_notifications.json")


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(config: dict) -> None:
    with open(_CONFIG_PATH, "w") as f:
        json.dump(config, f)


def get_config() -> dict:
    return _load_config()


def update_config(payload: dict) -> dict:
    config = _load_config()
    config.update({k: v for k, v in payload.items() if k in {"line_webhook", "discord_webhook", "email_to"}})
    _save_config(config)
    return config


async def send_notification(subject: str, body: str) -> None:
    config = _load_config()
    discord_url = config.get("discord_webhook", "")
    line_url = config.get("line_webhook", "")
    if discord_url:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(discord_url, json={"content": f"**{subject}**\n{body}"})
        except Exception:
            pass
    if line_url:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(line_url, json={"message": f"{subject}\n{body}"})
        except Exception:
            pass
```

**Step 2: Update comm_router.py — trigger notification after new message**

In `admin_post_message`, after `session.commit()`, add:
```python
    # Trigger notification (non-blocking)
    import asyncio
    from .notification import send_notification
    try:
        asyncio.create_task(send_notification(
            subject=f"新訊息 — 諮詢室 #{room_id}",
            body=f"來自 {current_user.email}: {msg.message[:100]}"
        ))
    except RuntimeError:
        pass  # No event loop in sync context — skip notification
```

**Step 3: Add notification config endpoints**

In `comm_router.py`, add:
```python
from .notification import get_config, update_config

@router.get("/notification-config")
def admin_get_notification_config(
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    return get_config()


@router.post("/notification-config")
def admin_update_notification_config(
    payload: dict,
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    return update_config(payload)
```

**Step 4: Run tests and commit**

```bash
pytest backend/tests -v
git add backend/app/modules/orders/notification.py backend/app/modules/orders/comm_router.py
git commit -m "feat(backend): add notification config endpoint + discord/line webhook trigger on new message"
```

---

## Task 7: Finance — wire per-product cost to Cost model

**Context:** The `Cost` model exists with `title`, `amount_twd`, `recorded_at`. The admin finance page already calls `GET /api/v1/admin/costs` and `POST /api/v1/admin/costs`. The only missing piece: no way to link a cost to a specific product. We add an optional `product_id` FK to `Cost`.

**Files:**
- Modify: `backend/app/modules/costs/models.py`
- Modify: `backend/app/modules/costs/schemas.py`
- Modify: `backend/app/modules/costs/service.py`

**Step 1: Add optional product_id to Cost model**

In `backend/app/modules/costs/models.py`, after `recorded_at`, add:
```python
    product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_type: Mapped[str] = mapped_column(String(64), nullable=False, default="misc")
    # cost_type: "product_purchase" | "shipping" | "misc" | "tax" | "other"
```

**Step 2: Update CostCreatePayload schema**

In `backend/app/modules/costs/schemas.py`, add to `CostCreatePayload`:
```python
    product_id: int | None = None
    cost_type: str = "misc"
```

And to `CostItem`:
```python
    product_id: int | None = None
    cost_type: str = "misc"
```

**Step 3: Update service.py create_cost function**

```python
def create_cost(session, title, amount_twd, recorded_at, product_id=None, cost_type="misc"):
    cost = Cost(
        title=title,
        amount_twd=amount_twd,
        recorded_at=recorded_at,
        product_id=product_id,
        cost_type=cost_type,
    )
    session.add(cost)
    session.commit()
    session.refresh(cost)
    return cost
```

**Step 4: Update router to pass new fields**

In `backend/app/modules/costs/router.py`, update `admin_create_cost`:
```python
    cost = create_cost(session, payload.title, payload.amount_twd, payload.recorded_at,
                       product_id=payload.product_id, cost_type=payload.cost_type)
```

**Step 5: Run tests and commit**

```bash
pytest backend/tests -v
git add backend/app/modules/costs/
git commit -m "feat(backend): add product_id and cost_type to Cost model for per-product cost tracking"
```

---

## Task 8: Frontend fix — CollectionView categories

**Context:** `CollectionView.vue` calls `GET /api/v1/categories` — this endpoint now exists (fixed in Task 3) and returns `{"items": [...]}` with each item having `id`, `title` (dict), `image`. The Vue component currently reads `col.image` and `col.title` — the `title` is now a locale dict. Fix the Vue component to handle the new shape.

**Files:**
- Modify: `frontend/src/app/views/CollectionView.vue`

**Step 1: Update loadCategories to use locale**

The component currently reads `col.image` and `col.title`. With the new API, `title` is `{"zh-Hant": "經典腕錶", "ja": "...", "en": "..."}`. Update:

In `CollectionView.vue`, change:
```javascript
collections.value = data.items || [];
```
to:
```javascript
collections.value = (data.items || []).map(item => ({
  id: item.id,
  image: item.image,
  title: (item.title && (item.title["zh-Hant"] || item.title.en)) || item.id,
}));
```

**Step 2: Frontend build check**

```bash
npm --prefix frontend run build
```
Expected: exit 0, no errors.

**Step 3: Commit**

```bash
git add frontend/src/app/views/CollectionView.vue
git commit -m "fix(frontend): map category title locale dict in CollectionView"
```

---

## Task 9: Frontend fix — MagazineView article_id field

**Context:** `MagazineView.vue` calls `fetchPublicMagazines()` from the service, which calls `GET /api/v1/magazines`. The DB-backed endpoint now returns articles from DB via `ArticleItem.from_orm_row()`. Check the response shape matches what the view expects.

The view expects: `item.article_id`, `item.slug`, `item.brand`, `item.title` (dict), `item.description` (dict), `item.image_url`, `item.status`.

The `ArticleItem` schema returns: `article_id`, `slug`, `brand`, `title` (dict), `description` (dict), `image_url`, `published` (bool — NOT `status` string).

**Files:**
- Modify: `frontend/src/app/views/MagazineView.vue`
- Modify: `frontend/src/app/views/MagazineDetailView.vue`

**Step 1: Fix status field mapping in MagazineView.vue**

In `loadMagazines()`, change:
```javascript
status: item.status || "published"
```
to:
```javascript
status: item.published === false ? "archived" : "published"
```

**Step 2: Read MagazineDetailView.vue to check field mapping**

Read `frontend/src/app/views/MagazineDetailView.vue` — verify it reads `title["zh-Hant"]` and `body["zh-Hant"]` correctly from the response. If it reads `title.zh_hant` (underscore), update to `title["zh-Hant"]`.

**Step 3: Frontend build check**

```bash
npm --prefix frontend run build
```
Expected: exit 0, no errors.

**Step 4: Frontend tests**

```bash
npm --prefix frontend run test
```
Expected: all pass.

**Step 5: Commit**

```bash
git add frontend/src/app/views/MagazineView.vue frontend/src/app/views/MagazineDetailView.vue
git commit -m "fix(frontend): map magazine published bool to status string, fix field keys"
```

---

## Task 10: Admin — add Categories management page

**Context:** Admin panel has no category management page. We need a simple CRUD page that calls `GET/POST/PATCH/DELETE /api/v1/admin/categories`.

**Files:**
- Create: `admin/src/api/categories.ts`
- Create: `admin/src/views/categories/index.vue`
- Modify: `admin/src/router/modules/` (add route)
- Modify: `admin/src/layout/sidebar` or menu config (add menu entry)

**Step 1: Create categories API module**

Create `admin/src/api/categories.ts`:
```typescript
import { http } from "@/utils/http";

export interface CategoryItem {
  id: string;
  title: { "zh-Hant": string; ja: string; en: string };
  image: string;
  sort_order: number;
  is_active: boolean;
}

export const getCategories = () =>
  http.request<{ items: CategoryItem[] }>("get", "/api/v1/admin/categories");

export const createCategory = (data: Partial<CategoryItem>) =>
  http.request("post", "/api/v1/admin/categories", { data });

export const updateCategory = (id: string, data: Partial<CategoryItem>) =>
  http.request("patch", `/api/v1/admin/categories/${id}`, { data });

export const deleteCategory = (id: string) =>
  http.request("delete", `/api/v1/admin/categories/${id}`);
```

**Step 2: Read how existing admin views (e.g., products/index.vue) use El-table + dialog**

Before writing the view, read `admin/src/views/products/index.vue` lines 1-100 as a reference for the El-table + ElDialog pattern.

**Step 3: Create categories view**

Create `admin/src/views/categories/index.vue` following the same pattern as `products/index.vue`:
- ElTable with columns: ID, 中文名稱, 日文名稱, 英文名稱, 圖片預覽, 排序, 啟用狀態, 操作
- ElDialog for create/edit with fields: id (create only), title.zh-Hant, title.ja, title.en, image URL, sort_order, is_active
- Delete with ElMessageBox confirm
- Image preview inline (small thumbnail)

**Step 4: Read existing router module pattern**

Read `admin/src/router/modules/` directory and one existing module file to match the route config pattern.

**Step 5: Add route module**

Create `admin/src/router/modules/categories.ts` following the same pattern as an existing module.

**Step 6: Add menu entry**

Find where admin sidebar menu items are defined (check `admin/src/layout/` or `admin/src/router/`) and add a "分類管理" item.

**Step 7: Frontend build check**

```bash
npm --prefix admin run build
```
Expected: exit 0.

**Step 8: Commit**

```bash
git add admin/src/api/categories.ts admin/src/views/categories/ admin/src/router/modules/categories.ts
git commit -m "feat(admin): add categories management page with CRUD"
```

---

## Task 11: Admin — update Products page to use dynamic categories + new fields

**Context:** `admin/src/views/products/index.vue` has hardcoded `categoryOptions` (line 50-57). We need to fetch them from `/api/v1/admin/categories` dynamically. Also add fields for description (zh/ja/en), preview_images, stock_qty, cost_twd.

**Files:**
- Modify: `admin/src/views/products/index.vue`

**Step 1: Import getCategories and load on mount**

At top of script setup, add:
```typescript
import { getCategories, type CategoryItem } from "@/api/categories";
const categoryOptions = ref<{ value: string; label: string }[]>([]);

async function loadCategories() {
  const res = await getCategories();
  const items = (res as any)?.items || (res as any)?.data?.items || [];
  categoryOptions.value = items.map((c: CategoryItem) => ({
    value: c.id,
    label: c.title["zh-Hant"] || c.id,
  }));
}
```

In `onMounted`, add `loadCategories()` call (alongside `loadProducts()`).

Remove the hardcoded `const categoryOptions = [...]` array.

**Step 2: Add new fields to the form dialog**

In `formData.ref`, add:
```typescript
  description_zh: "",
  description_ja: "",
  description_en: "",
  preview_images: [] as string[],
  stock_qty: 1,
  cost_twd: undefined as number | undefined,
```

In the dialog template, add form items after existing fields:
- ElInput for `description_zh`, `description_ja`, `description_en` (textarea)
- ElInputNumber for `stock_qty`
- ElInputNumber for `cost_twd` (optional)
- Image URL inputs for preview_images (text + add/remove buttons)

**Step 3: Update API call to pass new fields**

When calling `createProduct` or `updateProduct`, include the new fields.

**Step 4: Build check**

```bash
npm --prefix admin run build
```
Expected: exit 0.

**Step 5: Commit**

```bash
git add admin/src/views/products/index.vue
git commit -m "feat(admin): dynamic category fetch + description/stock/cost fields in product form"
```

---

## Task 12: Admin — add CommRoom management page

**Context:** Admin needs a page to see all comm rooms, read message threads, reply, and close rooms.

**Files:**
- Create: `admin/src/api/commRooms.ts`
- Create: `admin/src/views/commrooms/index.vue`
- Modify: `admin/src/router/modules/` (add route)

**Step 1: Create commRooms API module**

Create `admin/src/api/commRooms.ts`:
```typescript
import { http } from "@/utils/http";

export const getCommRooms = () =>
  http.request("get", "/api/v1/admin/comm-rooms");

export const getCommRoom = (id: number) =>
  http.request("get", `/api/v1/admin/comm-rooms/${id}`);

export const postMessage = (roomId: number, message: string) =>
  http.request("post", `/api/v1/admin/comm-rooms/${roomId}/messages`, {
    data: { message }
  });

export const setRoomStatus = (roomId: number, status: string) =>
  http.request("patch", `/api/v1/admin/comm-rooms/${roomId}/status`, {
    data: { status }
  });

export const getNotificationConfig = () =>
  http.request("get", "/api/v1/admin/comm-rooms/notification-config");

export const updateNotificationConfig = (config: {
  discord_webhook?: string;
  line_webhook?: string;
  email_to?: string;
}) => http.request("post", "/api/v1/admin/comm-rooms/notification-config", { data: config });
```

**Step 2: Create commrooms view**

Create `admin/src/views/commrooms/index.vue`:
- Left panel: list of comm rooms (buyer, product, status badge, last message timestamp)
- Right panel: message thread for selected room (chat-style layout)
- Footer: reply input + send button
- Header action: "關閉諮詢室" button (if status != closed)
- Tab or modal: notification settings (Discord webhook URL, LINE webhook URL)

Follow Element Plus style — use `ElCard`, `ElBadge`, `ElTag`, `ElInput` textarea, `ElButton`.

**Step 3: Add route and menu entry**

Following pattern from Task 10, add route and menu item for "諮詢管理".

**Step 4: Build check**

```bash
npm --prefix admin run build
```
Expected: exit 0.

**Step 5: Commit**

```bash
git add admin/src/api/commRooms.ts admin/src/views/commrooms/ admin/src/router/modules/commrooms.ts
git commit -m "feat(admin): add comm-room management page with reply, close, and notification settings"
```

---

## Task 13: Admin — update Finance page for per-product costs

**Context:** Finance page already works for summary + chart + cost list. Update the "新增成本" dialog to optionally select a product and a cost type (misc/shipping/product_purchase/tax).

**Files:**
- Modify: `admin/src/views/finance/index.vue`
- Modify: `admin/src/api/finance.ts`

**Step 1: Read current finance API schema**

Read `admin/src/api/finance.ts` to understand `CostEntry` type and `addCost` function signature.

**Step 2: Update CostEntry type and addCost**

Add to `CostEntry`:
```typescript
  product_id?: number;
  cost_type?: string;
```

Update `addCost` to pass these fields.

**Step 3: Update dialog in finance view**

In the "新增成本" dialog, add:
- ElSelect for `cost_type` (options: 雜費/shipping/商品採購/稅費)
- ElSelect for `product_id` (optional, load product list from `/api/v1/admin/products`)
- When `cost_type === "product_purchase"`, make product_id required

**Step 4: Build check**

```bash
npm --prefix admin run build
```
Expected: exit 0.

**Step 5: Commit**

```bash
git add admin/src/views/finance/index.vue admin/src/api/finance.ts
git commit -m "feat(admin): add product_id and cost_type to finance cost entry dialog"
```

---

## Task 14: Admin — add CRM buyers list with comm-room drill-down

**Context:** Current CRM page shows buyer notes and points. Add a buyer list that shows each buyer's orders, comm rooms, and lets the admin jump to a specific room.

**Files:**
- Modify: `admin/src/views/crm/index.vue`

**Step 1: Read current CRM view**

Read `admin/src/views/crm/index.vue` to understand current layout.

**Step 2: Add buyers list tab**

Add a tab (or section) with:
- Table: email, display_name, role, total orders, total spent
- Row expand: show their comm rooms (room ID, product, status, last message)
- Link/button: "前往諮詢室" that navigates to the comm rooms page filtered by this buyer

**Step 3: Build check**

```bash
npm --prefix admin run build
```
Expected: exit 0.

**Step 4: Commit**

```bash
git add admin/src/views/crm/
git commit -m "feat(admin): add buyer list with comm-room drill-down in CRM page"
```

---

## Task 15: Final integration test + Docker build

**Step 1: Run all backend tests**

```bash
pytest backend/tests -v
```
Expected: all pass (or note pre-existing failures separately).

**Step 2: Run all frontend tests**

```bash
npm --prefix frontend run test
npm --prefix admin run build
```
Expected: all pass / exit 0.

**Step 3: Docker compose config validation**

```bash
COMPOSE_PROJECT_NAME=wakou docker compose config
```
Expected: valid config, no errors.

**Step 4: (Optional) Full stack smoke test**

```bash
COMPOSE_PROJECT_NAME=wakou docker compose up --build
```
Manually verify:
- `http://localhost/` — frontend loads, collections page shows 6 category images ✓
- `http://localhost/magazine` — 2+ articles visible with correct Chinese text ✓
- `http://localhost/api/v1/categories` — returns JSON with 6 items ✓
- Admin panel — categories, products, comm rooms, finance pages all load ✓

**Step 5: Commit (if any last fixes)**

```bash
git add .
git commit -m "chore: final integration fixes after full-stack smoke test"
```

---

## Summary of Changes

| File | Change |
|---|---|
| `backend/app/main.py` | +router registrations, +magazine DB seed, +category DB seed, remove in-memory `/api/v1/categories` route |
| `backend/app/modules/categories/` | NEW module — Category model, public + admin CRUD router |
| `backend/app/modules/products/models.py` | +description_zh/ja/en, preview_images_json, detail_images_json, stock_qty, cost_twd |
| `backend/app/modules/products/schemas.py` | +new fields to payload + response |
| `backend/app/modules/products/service.py` | update resolve_product_extra to read from DB |
| `backend/app/modules/products/router.py` | pass full product to extra resolver |
| `backend/app/modules/orders/comm_router.py` | NEW — CommRoom admin CRUD + reply + status toggle |
| `backend/app/modules/orders/notification.py` | NEW — file-based notification config + Discord/LINE webhook trigger |
| `backend/app/modules/costs/models.py` | +product_id, cost_type columns |
| `backend/app/modules/costs/schemas.py` | +product_id, cost_type |
| `backend/app/modules/costs/service.py` | update create_cost signature |
| `frontend/src/app/views/CollectionView.vue` | fix title locale dict mapping |
| `frontend/src/app/views/MagazineView.vue` | fix published→status mapping |
| `frontend/src/app/views/MagazineDetailView.vue` | verify field key alignment |
| `admin/src/api/categories.ts` | NEW |
| `admin/src/views/categories/index.vue` | NEW — full CRUD |
| `admin/src/views/products/index.vue` | dynamic categories + new fields |
| `admin/src/api/commRooms.ts` | NEW |
| `admin/src/views/commrooms/index.vue` | NEW — chat-style rooms manager |
| `admin/src/views/crm/index.vue` | +buyers list + room drill-down |
| `admin/src/views/finance/index.vue` | +product_id + cost_type in cost form |
| `admin/src/api/finance.ts` | +product_id + cost_type fields |
| `admin/src/router/modules/categories.ts` | NEW route |
| `admin/src/router/modules/commrooms.ts` | NEW route |
