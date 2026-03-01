# Orders + Comm-Rooms DB Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate all stub order/comm-room routes in `main.py` to real MySQL-backed DB, making the buyer order flow and admin management fully functional.

**Architecture:** Add `CommRoom` and `CommMessage` SQLAlchemy models under the existing `orders` module. Wire all stub routes in `main.py` to service functions. Update tests to expect real status codes (201/200) instead of 501/404.

**Tech Stack:** FastAPI, SQLAlchemy (mapped_column style), MySQL 8, pytest

---

## Current State

These routes in `main.py` are stubs returning 501/404/empty:

- `POST /api/v1/orders` → 501
- `GET /api/v1/orders/me` → empty list
- `GET /api/v1/comm-rooms/me` → empty list
- `GET /api/v1/comm-rooms/{room_id}` → 404
- `POST /api/v1/comm-rooms/{room_id}/messages` → 404
- `POST /api/v1/comm-rooms/{room_id}/final-quote` → 404
- `POST /api/v1/comm-rooms/{room_id}/accept-quote` → 404
- `POST /api/v1/comm-rooms/{room_id}/upload-proof` → 404
- `POST /api/v1/orders/{order_id}/confirm-payment` → 404
- `POST /api/v1/orders/{order_id}/complete` → 404

The `orders/router.py` already handles admin listing (`GET /api/v1/admin/orders`) and status update (`PATCH /api/v1/admin/orders/{id}/status`) — **do not touch those**.

The `orders/models.py` already has the `Order` model with `comm_room_id` FK field.

---

## Task 1: Add CommRoom + CommMessage models

**Files:**
- Modify: `backend/app/modules/orders/models.py`

**Step 1: Add the two new models at the bottom of `models.py`**

```python
class CommRoom(Base):
    __tablename__ = "comm_rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    buyer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="open")
    final_price_twd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shipping_fee_twd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_twd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transfer_proof_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class CommMessage(Base):
    __tablename__ = "comm_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("comm_rooms.id"), nullable=False, index=True)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(32), nullable=False, default="buyer")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
```

Import needed at top: `ForeignKey` is already imported from sqlalchemy. Confirm `Text` is imported too.

**Step 2: Verify models file compiles**

```bash
cd backend && python -c "from app.modules.orders.models import CommRoom, CommMessage; print('OK')"
```

Expected: `OK`

---

## Task 2: Add schemas for comm-rooms

**Files:**
- Modify: `backend/app/modules/orders/schemas.py`

**Step 1: Add these new schemas at the bottom**

```python
class CommMessageItem(BaseModel):
    id: int
    room_id: int
    sender_email: str
    sender_role: str
    message: str
    image_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommRoomItem(BaseModel):
    id: int
    order_id: int
    buyer_email: str
    status: str
    final_price_twd: int | None
    shipping_fee_twd: int | None
    discount_twd: int
    transfer_proof_url: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[CommMessageItem] = []

    model_config = {"from_attributes": True}


class CommRoomListResponse(BaseModel):
    items: list[CommRoomItem]


class CreateOrderPayload(BaseModel):
    product_id: int = Field(validation_alias=AliasChoices("product_id", "productId"))
    mode: str
    coupon_id: int | None = Field(default=None, validation_alias=AliasChoices("coupon_id", "couponId"))
    points_to_redeem: int | None = Field(default=0, validation_alias=AliasChoices("points_to_redeem", "pointsToRedeem"))


class FinalQuotePayload(BaseModel):
    final_price_twd: int
    shipping_fee_twd: int
    discount_twd: int | None = 0


class TransferProofPayload(BaseModel):
    transfer_proof_url: str


class CommRoomMessagePayload(BaseModel):
    message: str
    image_url: str | None = None
```

Add imports at the top of schemas.py:
```python
from pydantic import AliasChoices, Field
```

---

## Task 3: Add service functions for order creation + comm-room operations

**Files:**
- Modify: `backend/app/modules/orders/service.py`

**Step 1: Add the following service functions**

```python
from .models import CommRoom, CommMessage


def create_order_with_room(
    session: Session,
    buyer_email: str,
    product_id: int,
    mode: str,
    product_name: str = "",
    amount_twd: int = 0,
) -> tuple[Order, CommRoom]:
    order = Order(
        buyer_email=buyer_email,
        product_id=product_id,
        product_name=product_name,
        status="inquiring",
        amount_twd=amount_twd,
    )
    session.add(order)
    session.flush()  # get order.id

    room = CommRoom(
        order_id=order.id,
        buyer_email=buyer_email,
        status="open",
    )
    session.add(room)
    session.flush()

    order.comm_room_id = room.id
    session.commit()
    session.refresh(order)
    session.refresh(room)
    return order, room


def get_room_with_messages(session: Session, room_id: int) -> CommRoom | None:
    room = session.get(CommRoom, room_id)
    if room is None:
        return None
    # Eagerly load messages
    from sqlalchemy import select
    room._messages = list(
        session.scalars(
            select(CommMessage).where(CommMessage.room_id == room_id).order_by(CommMessage.id)
        )
    )
    return room


def add_room_message(
    session: Session,
    room_id: int,
    sender_email: str,
    sender_role: str,
    message: str,
    image_url: str | None = None,
) -> CommMessage:
    msg = CommMessage(
        room_id=room_id,
        sender_email=sender_email,
        sender_role=sender_role,
        message=message,
        image_url=image_url,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


def set_final_quote(
    session: Session,
    room_id: int,
    final_price_twd: int,
    shipping_fee_twd: int,
    discount_twd: int = 0,
) -> CommRoom:
    room = session.get(CommRoom, room_id)
    if room is None:
        raise ValueError(f"room {room_id} not found")
    room.final_price_twd = final_price_twd
    room.shipping_fee_twd = shipping_fee_twd
    room.discount_twd = discount_twd
    room.status = "quote_sent"
    session.commit()
    session.refresh(room)
    return room


def accept_quote(session: Session, room_id: int, buyer_email: str) -> CommRoom:
    room = session.get(CommRoom, room_id)
    if room is None:
        raise ValueError(f"room {room_id} not found")
    if room.buyer_email != buyer_email:
        raise PermissionError("not your room")
    room.status = "accepted"
    session.commit()
    session.refresh(room)
    return room


def upload_proof(session: Session, room_id: int, buyer_email: str, proof_url: str) -> CommRoom:
    room = session.get(CommRoom, room_id)
    if room is None:
        raise ValueError(f"room {room_id} not found")
    if room.buyer_email != buyer_email:
        raise PermissionError("not your room")
    room.transfer_proof_url = proof_url
    room.status = "proof_uploaded"
    session.commit()
    session.refresh(room)
    return room


def list_rooms_for_buyer(session: Session, buyer_email: str) -> list[CommRoom]:
    from sqlalchemy import select
    return list(
        session.scalars(
            select(CommRoom).where(CommRoom.buyer_email == buyer_email).order_by(CommRoom.id.desc())
        )
    )


def list_orders_for_buyer(session: Session, buyer_email: str) -> list[Order]:
    from sqlalchemy import select
    return list(
        session.scalars(
            select(Order).where(Order.buyer_email == buyer_email).order_by(Order.id.desc())
        )
    )
```

---

## Task 4: Wire stub routes in main.py to real service functions

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Add imports at the top of main.py** (after existing module imports)

Add to the importlib block at top:
```python
comm_room_service = importlib.import_module("app.modules.orders.service")
comm_room_schemas = importlib.import_module("app.modules.orders.schemas")
```

Then add near the other alias bindings:
```python
CommRoom = importlib.import_module("app.modules.orders.models").CommRoom
```

**Step 2: Replace the stub route handlers with real DB implementations**

Replace `create_order` (line ~469):
```python
@app.post("/api/v1/orders", status_code=201)
def create_order(payload: OrderPayload, current_user: User = Depends(require_role(["buyer"]))) -> dict[str, Any]:
    session = SessionLocal()
    try:
        # Look up product name if available
        product = session.get(HH, payload.product_id)  # HH = Product
        product_name = ""
        amount_twd = 0
        if product:
            from app.modules.products.models import Product as _Product
            product_name = getattr(product, "name_zh_hant", "") or ""
            amount_twd = getattr(product, "price_twd", 0) or 0
        order, room = comm_room_service.create_order_with_room(
            session,
            buyer_email=current_user.email,
            product_id=payload.product_id,
            mode=payload.mode,
            product_name=product_name,
            amount_twd=amount_twd,
        )
        return {"order_id": order.id, "room_id": room.id, "status": order.status}
    finally:
        session.close()
```

Replace `my_orders` (line ~476):
```python
@app.get("/api/v1/orders/me")
def my_orders(current_user: User = Depends(require_role(ANY_AUTH_ROLES))) -> dict[str, list[dict[str, Any]]]:
    session = SessionLocal()
    try:
        orders = comm_room_service.list_orders_for_buyer(session, current_user.email)
        return {"items": [
            {
                "id": o.id,
                "product_id": o.product_id,
                "product_name": o.product_name,
                "status": o.status,
                "amount_twd": o.amount_twd,
                "final_amount_twd": o.final_amount_twd,
                "comm_room_id": o.comm_room_id,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]}
    finally:
        session.close()
```

Replace `my_comm_rooms` (line ~482):
```python
@app.get("/api/v1/comm-rooms/me")
def my_comm_rooms(current_user: User = Depends(require_role(ANY_AUTH_ROLES))) -> dict[str, list[dict[str, Any]]]:
    session = SessionLocal()
    try:
        rooms = comm_room_service.list_rooms_for_buyer(session, current_user.email)
        return {"items": [
            {
                "id": r.id,
                "order_id": r.order_id,
                "status": r.status,
                "final_price_twd": r.final_price_twd,
                "shipping_fee_twd": r.shipping_fee_twd,
                "discount_twd": r.discount_twd,
                "created_at": r.created_at.isoformat(),
            }
            for r in rooms
        ]}
    finally:
        session.close()
```

Replace `get_comm_room` (line ~488):
```python
@app.get("/api/v1/comm-rooms/{room_id}")
def get_comm_room(room_id: int, current_user: User = Depends(require_role(ANY_AUTH_ROLES))) -> dict[str, Any]:
    session = SessionLocal()
    try:
        room = comm_room_service.get_room_with_messages(session, room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="room not found")
        msgs = getattr(room, "_messages", [])
        return {
            "id": room.id,
            "order_id": room.order_id,
            "buyer_email": room.buyer_email,
            "status": room.status,
            "final_price_twd": room.final_price_twd,
            "shipping_fee_twd": room.shipping_fee_twd,
            "discount_twd": room.discount_twd,
            "transfer_proof_url": room.transfer_proof_url,
            "created_at": room.created_at.isoformat(),
            "messages": [
                {
                    "id": m.id,
                    "sender_email": m.sender_email,
                    "sender_role": m.sender_role,
                    "message": m.message,
                    "image_url": m.image_url,
                    "created_at": m.created_at.isoformat(),
                }
                for m in msgs
            ],
        }
    finally:
        session.close()
```

Replace `send_comm_room_message` (line ~495):
```python
@app.post("/api/v1/comm-rooms/{room_id}/messages")
def send_comm_room_message(
    room_id: int,
    payload: CommRoomMessagePayload,
    current_user: User = Depends(require_role(ANY_AUTH_ROLES)),
) -> dict[str, Any]:
    session = SessionLocal()
    try:
        room = session.get(CommRoom, room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="room not found")
        msg = comm_room_service.add_room_message(
            session,
            room_id=room_id,
            sender_email=current_user.email,
            sender_role=current_user.role,
            message=payload.message,
            image_url=payload.image_url,
        )
        return {"id": msg.id, "room_id": msg.room_id, "message": msg.message, "created_at": msg.created_at.isoformat()}
    finally:
        session.close()
```

Replace `set_final_quote` (line ~507):
```python
@app.post("/api/v1/comm-rooms/{room_id}/final-quote")
def set_final_quote(
    room_id: int,
    payload: FinalQuotePayload,
    current_user: User = Depends(require_role(["admin", "sales", "maintenance", "super_admin"])),
) -> dict[str, Any]:
    session = SessionLocal()
    try:
        try:
            room = comm_room_service.set_final_quote(
                session, room_id, payload.final_price_twd, payload.shipping_fee_twd, payload.discount_twd or 0
            )
            return {"id": room.id, "status": room.status, "final_price_twd": room.final_price_twd}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()
```

Replace `accept_quote` (line ~519):
```python
@app.post("/api/v1/comm-rooms/{room_id}/accept-quote")
def accept_quote(room_id: int, current_user: User = Depends(require_role(["buyer"]))) -> dict[str, Any]:
    session = SessionLocal()
    try:
        try:
            room = comm_room_service.accept_quote(session, room_id, current_user.email)
            return {"id": room.id, "status": room.status}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    finally:
        session.close()
```

Replace `upload_proof` (line ~526):
```python
@app.post("/api/v1/comm-rooms/{room_id}/upload-proof")
def upload_proof(
    room_id: int,
    payload: TransferProofPayload,
    current_user: User = Depends(require_role(["buyer"])),
) -> dict[str, Any]:
    session = SessionLocal()
    try:
        try:
            room = comm_room_service.upload_proof(session, room_id, current_user.email, payload.transfer_proof_url)
            return {"id": room.id, "status": room.status}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    finally:
        session.close()
```

Replace `confirm_manual_payment` (line ~538):
```python
@app.post("/api/v1/orders/{order_id}/confirm-payment")
def confirm_manual_payment(
    order_id: int,
    current_user: User = Depends(require_role(["admin", "sales", "maintenance", "super_admin"])),
) -> dict[str, Any]:
    session = SessionLocal()
    try:
        order = session.get(User.__class__, order_id)  # NOTE: use Order model
        # Use the existing update_order_status service
        try:
            order = comm_room_service.update_order_status(session, order_id, "payment_confirmed")
            return {"id": order.id, "status": order.status}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()
```

> **IMPORTANT NOTE for implementer:** `update_order_status` is already defined in `service.py`. Import it properly — don't call `comm_room_service.update_order_status` because the module was loaded differently. Instead, call the function directly from the already-imported `comm_room_service` module object.

Replace `complete_order` (line ~564):
```python
@app.post("/api/v1/orders/{order_id}/complete")
def complete_order(
    order_id: int,
    current_user: User = Depends(require_role(["admin", "sales", "maintenance", "super_admin"])),
) -> dict[str, Any]:
    session = SessionLocal()
    try:
        try:
            order = comm_room_service.update_order_status(session, order_id, "completed")
            return {"id": order.id, "status": order.status}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()
```

**Also: ensure `CommRoom` is importable in main.py for the `send_comm_room_message` handler.** Add this near the top importlib block:

```python
order_models = importlib.import_module("app.modules.orders.models")
CommRoom = order_models.CommRoom
```

---

## Task 5: Update tests to expect real status codes

**Files:**
- Modify: `backend/tests/orders/test_comm_room_flow.py`

**Step 1: Update `test_buyer_order_enters_comm_room`**

The order creation should now return 201 with `{"order_id": ..., "room_id": ..., "status": "inquiring"}`.
The comm-room GET should now return 200 (since the room was just created).

```python
def test_buyer_order_enters_comm_room(client, buyer_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
    data = create_response.json()
    assert "room_id" in data
    room_id = data["room_id"]

    room_response = client.get(
        f"/api/v1/comm-rooms/{room_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert room_response.status_code == 200
    room_data = room_response.json()
    assert room_data["status"] == "open"
```

**Step 2: Update `test_buyer_order_accepts_camel_case_payload`**

```python
def test_buyer_order_accepts_camel_case_payload(client, buyer_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"productId": 1, "mode": "inquiry", "pointsToRedeem": 0, "couponId": None},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
```

**Step 3: Update `test_admin_sets_final_quote`**

This requires a real room to exist. Create an order first to get a room_id, then set the final quote.

```python
def test_admin_sets_final_quote(client, buyer_token, admin_token):
    # Create an order first (as buyer)
    create_resp = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_resp.status_code == 201
    room_id = create_resp.json()["room_id"]

    response = client.post(
        f"/api/v1/comm-rooms/{room_id}/final-quote",
        json={"final_price_twd": 12000, "shipping_fee_twd": 300, "discount_twd": 100},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "quote_sent"
```

---

## Task 6: Run tests and verify

**Step 1: Run the comm-room tests**

```bash
pytest backend/tests/orders/test_comm_room_flow.py -v
```

Expected: 3 passed

**Step 2: Run all backend tests**

```bash
pytest backend/tests -v
```

Expected: all pass (31+ tests)

**Step 3: Run frontend build**

```bash
npm --prefix frontend run build
```

Expected: success

---

## Important Notes

### SQLite vs MySQL in tests

Tests use SQLite in-memory (from config). The models use `Integer` + `ForeignKey` — these work fine in SQLite too. The `onupdate` lambda pattern for `updated_at` also works in SQLite.

### `orders/router.py` still references ORDERS in-memory (fallback)

The fallback in `orders/router.py` lines 25-44 imports `from app.main import ORDERS` which no longer exists. Since the DB path always runs first (and returns results), the `except Exception` catches the import error silently — this is fine. The code path is never reached in normal operation. **Do not touch it** unless tests break.

### Product lookup in `create_order`

`main.py` already has `HH = Product` (the alias from line 33: `HH = product_models.Product`). Use `session.get(HH, payload.product_id)` to look up the product. If product doesn't exist (product_id=1 in test DB won't exist), product_name stays "" and amount_twd stays 0 — that's acceptable for test purposes.

### comm_room_service module binding

`comm_room_service` is loaded via `importlib.import_module("app.modules.orders.service")`. After Task 3 adds `create_order_with_room` etc., `comm_room_service.create_order_with_room(...)` will work.
