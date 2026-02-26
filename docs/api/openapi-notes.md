# OpenAPI Notes (MVP Scaffold)

The scaffold exposes minimal contract-first endpoints used by tests.

## Public

- `GET /api/v1/health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/warehouse/timeline`

## Buyer Flow

- `POST /api/v1/orders`
- `GET /api/v1/comm-rooms/{room_id}`
- `POST /api/v1/payments/ecpay/{order_id}`
- `POST /api/v1/payments/ecpay/callback`

## Admin Flow

- `GET /api/v1/admin/products`
- `POST /api/v1/admin/products`
- `POST /api/v1/comm-rooms/{room_id}/shipping-quote`
- `GET /api/v1/admin/orders/export.csv`

## Notes

- Data persistence is in-memory for MVP scaffold tasks.
- API shape and route contracts are driven by the plan tests.
- ECPay integration is sandbox-style payload simulation for contract coverage.
