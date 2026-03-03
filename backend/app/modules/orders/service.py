from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Order, CommRoom, CommMessage


def list_orders(session: Session) -> list[Order]:
    return list(session.scalars(select(Order).order_by(Order.id.desc())))


def get_order(session: Session, order_id: int) -> Order | None:
    return session.get(Order, order_id)


def update_order_status(
    session: Session,
    order_id: int,
    status: str,
    note: str | None = None,
    final_amount_twd: int | None = None,
) -> Order:
    order = session.get(Order, order_id)
    if not order:
        raise ValueError(f"order {order_id} not found")
    order.status = status
    if note is not None:
        order.note = note
    if final_amount_twd is not None:
        order.final_amount_twd = final_amount_twd
    session.commit()
    session.refresh(order)
    return order


def create_order_with_room(
    session: Session,
    buyer_email: str,
    product_id: int,
    mode: str,
    product_name: str = "",
    amount_twd: int = 0,
) -> tuple[Order, CommRoom]:
    initial_status = "buyer_confirmed" if mode == "buy_now" else "inquiring"
    order = Order(
        buyer_email=buyer_email,
        product_id=product_id,
        product_name=product_name,
        status=initial_status,
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
    return list(
        session.scalars(
            select(CommRoom).where(CommRoom.buyer_email == buyer_email).order_by(CommRoom.id.desc())
        )
    )


def list_orders_for_buyer(session: Session, buyer_email: str) -> list[Order]:
    return list(
        session.scalars(
            select(Order).where(Order.buyer_email == buyer_email).order_by(Order.id.desc())
        )
    )
