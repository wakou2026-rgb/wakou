from __future__ import annotations

import os
from typing import Any


PRODUCTS: list[dict[str, Any]] = []
CATEGORIES: list[dict[str, Any]] = []

MAGAZINES: list[dict[str, Any]] = []
USERS_LIST: list[dict[str, Any]] = []
REVENUE_RECORDS: list[dict[str, Any]] = []
WAREHOUSE_LOGS: list[dict[str, Any]] = []
SHIPMENT_EVENTS: dict[int, list[dict[str, Any]]] = {}
POINTS_LOGS: list[dict[str, Any]] = []
REVIEWS: list[dict[str, Any]] = []
COST_RECORDS: list[dict[str, Any]] = []
POINTS_POLICY: dict[str, Any] = {
    "point_value_twd": 1,
    "base_rate": 0.01,
    "diamond_rate": 0.02,
    "expiry_months": 12,
}
LEVELS_CONFIG: list[dict[str, Any]] = [
    {"name": "初見", "threshold": 0, "rate": 0.01},
    {"name": "生日禮遇", "threshold": 20000, "rate": 0.012},
    {"name": "免運會員", "threshold": 50000, "rate": 0.015},
    {"name": "尊榮會員", "threshold": 150000, "rate": 0.02},
]
next_review_id = 1
next_cost_id = 1
next_revenue_id = 1
next_event_id = 1
ORDERS: dict[int, dict[str, Any]] = {}
COMM_ROOMS: dict[int, dict[str, Any]] = {}
WISHLISTS: dict[str, list[str]] = {}
USER_DISPLAY_NAMES: dict[str, str] = {}
EVENT_LOGS: list[dict[str, Any]] = []
USER_NOTIFICATION_CURSOR: dict[str, int] = {}
COUPONS: list[dict[str, Any]] = []
USER_COUPONS: list[dict[str, Any]] = []
GACHA_POOLS: list[dict[str, Any]] = []
GACHA_DRAW_QUOTA: dict[str, int] = {}
CRM_NOTES: dict[str, list[dict[str, Any]]] = {}
next_coupon_id = 1
next_user_coupon_id = 1
next_gacha_pool_id = 1
next_order_id = 1
next_room_id = 1
next_product_id = 1
next_mag_article_id = 1

FULL_ADMIN_ROLES = {"admin", "super_admin"}
PRODUCT_ADMIN_ROLES = {"admin", "super_admin", "maintenance"}
ORDER_ADMIN_ROLES = {"admin", "super_admin", "sales", "maintenance"}

INQUIRY_NOTIFY_TO_EMAIL = os.getenv("NOTIFY_TO_EMAIL", "").strip()
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost").rstrip("/")
ADMIN_BASE_URL = os.getenv("ADMIN_BASE_URL", "http://localhost/admin").rstrip("/")
INQUIRY_REMINDER_HOURS = max(int(os.getenv("INQUIRY_REMINDER_HOURS", "6")), 1)
INQUIRY_REMINDER_SCAN_SECONDS = max(int(os.getenv("INQUIRY_REMINDER_SCAN_SECONDS", "600")), 60)
_inquiry_reminder_thread_started = False


def reset_state() -> None:
    global next_order_id, next_room_id, next_product_id, next_mag_article_id, next_review_id, next_cost_id, next_revenue_id, next_event_id, next_coupon_id, next_user_coupon_id, next_gacha_pool_id, _inquiry_reminder_thread_started

    ORDERS.clear()
    COMM_ROOMS.clear()
    WISHLISTS.clear()
    USER_DISPLAY_NAMES.clear()
    PRODUCTS.clear()
    CATEGORIES.clear()
    MAGAZINES.clear()
    USERS_LIST.clear()
    REVENUE_RECORDS.clear()
    WAREHOUSE_LOGS.clear()
    SHIPMENT_EVENTS.clear()
    POINTS_LOGS.clear()
    REVIEWS.clear()
    COST_RECORDS.clear()
    EVENT_LOGS.clear()
    USER_NOTIFICATION_CURSOR.clear()
    COUPONS.clear()
    USER_COUPONS.clear()
    GACHA_POOLS.clear()
    GACHA_DRAW_QUOTA.clear()
    CRM_NOTES.clear()
    next_order_id = 1
    next_room_id = 1
    next_product_id = 1
    next_mag_article_id = 1
    next_review_id = 1
    next_cost_id = 1
    next_revenue_id = 1
    next_event_id = 1
    next_coupon_id = 1
    next_user_coupon_id = 1
    next_gacha_pool_id = 1
    _inquiry_reminder_thread_started = False
