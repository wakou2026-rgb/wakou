from __future__ import annotations

import importlib
from typing import Any, cast

from fastapi import FastAPI

auth_router_module = importlib.import_module("app.modules.auth.router")
product_router_module = importlib.import_module("app.modules.products.router")
magazine_router_module = importlib.import_module("app.modules.magazines.router")
costs_router_module = importlib.import_module("app.modules.costs.router")
crm_router_module = importlib.import_module("app.modules.crm.router")
orders_router_module = importlib.import_module("app.modules.orders.router")
comm_router_module = importlib.import_module("app.modules.orders.comm_router")
coupons_router_module = importlib.import_module("app.modules.coupons.router")
payments_router_module = importlib.import_module("app.modules.payments.router")
categories_router_module = importlib.import_module("app.modules.categories.router")
reviews_buyer_router_module = importlib.import_module("app.modules.reviews.buyer_router")
reviews_admin_router_module = importlib.import_module("app.modules.reviews.router")
events_router_module = importlib.import_module("app.modules.events.router")
gacha_router_module = importlib.import_module("app.modules.gacha.router")
users_router_module = importlib.import_module("app.modules.users.router")
warehouse_router_module = importlib.import_module("app.modules.warehouse.router")
shipments_router_module = importlib.import_module("app.modules.shipments.router")
wishlist_router_module = importlib.import_module("app.modules.wishlist.router")

slowapi_module = importlib.import_module("slowapi")
slowapi_errors_module = importlib.import_module("slowapi.errors")

_rate_limit_exceeded_handler = slowapi_module._rate_limit_exceeded_handler
RateLimitExceeded = slowapi_errors_module.RateLimitExceeded

from app.core.bootstrap import (  # noqa: E402
    _run_migrations as _run_migrations_impl,
    _start_inquiry_reminder_worker as _start_inquiry_reminder_worker_impl,
    bootstrap_state,
)
from app.core.mailer import build_html_email, send_email  # noqa: E402
from app.core.state import ADMIN_BASE_URL, FRONTEND_BASE_URL, INQUIRY_NOTIFY_TO_EMAIL  # noqa: E402

app = FastAPI(title="wakou-api")
app.state.limiter = auth_router_module.limiter
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))

app.include_router(product_router_module.router)
app.include_router(product_router_module.admin_router)

app.include_router(auth_router_module.auth_router)
app.include_router(auth_router_module.admin_router)

app.include_router(magazine_router_module.router)
app.include_router(magazine_router_module.public_router)

app.include_router(costs_router_module.router)
app.include_router(crm_router_module.router)

app.include_router(orders_router_module.router)
app.include_router(orders_router_module.buyer_router)
app.include_router(comm_router_module.router)
app.include_router(comm_router_module.buyer_router)

app.include_router(coupons_router_module.router)
app.include_router(payments_router_module.router)

app.include_router(categories_router_module.public_router)
app.include_router(categories_router_module.admin_router)

app.include_router(reviews_buyer_router_module.router)
app.include_router(reviews_admin_router_module.router)
app.include_router(reviews_admin_router_module.buyer_router)

app.include_router(events_router_module.router)

app.include_router(gacha_router_module.router)
app.include_router(gacha_router_module.admin_router)

app.include_router(users_router_module.buyer_router)
app.include_router(warehouse_router_module.router)
app.include_router(shipments_router_module.router)

app.include_router(wishlist_router_module.wishlist_router)


@app.on_event("startup")
def _run_migrations() -> None:
    _run_migrations_impl()



@app.on_event("startup")
def _start_inquiry_reminder_worker() -> None:
    _start_inquiry_reminder_worker_impl()


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"service": "wakou-api"}


bootstrap_state()
