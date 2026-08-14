# API contract

Base URL: `/api/v1`

Tenant-scoped endpoints use `Authorization: Bearer <access-token>`. The verified token supplies the actor, organization, and roles; clients must not be trusted to choose a tenant with a custom header.

Stock-changing commands require an `Idempotency-Key` header. Reusing a key with different payload data returns an idempotency conflict.

## Authentication

| Method | Path | Access |
|---|---|---|
| POST | `/auth/register` | Public registration policy |
| POST | `/auth/login` | Public |
| GET | `/auth/me` | Authenticated |
| GET | `/auth/users` | Admin |
| PATCH | `/auth/users/{user_id}` | Admin |
| DELETE | `/auth/users/{user_id}` | Admin |

## Master data

| Method | Path | Access |
|---|---|---|
| GET/POST | `/setup/sellers` | Read / manager write |
| GET/POST | `/setup/warehouses` | Read / manager write |
| GET/POST | `/setup/locations` | Read / manager write |
| GET/POST | `/setup/products` | Read / manager write |
| POST | `/setup/organizations` | Platform administrator |

Every resource receives a stable UUID. The UI displays human-readable names and codes while API commands send the UUID.

## Receiving and inventory

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/inbound-receipts` | List or register deliveries |
| POST | `/inbound-receipts/{id}/scan` | Record good or damaged stock |
| POST | `/inbound-receipts/{id}/complete` | Release good stock as available |
| GET | `/inventory` | List current projected balances |

## Orders and shipping

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/orders` | List orders or reserve stock atomically |
| GET/POST | `/shipments` | List or create carrier shipments |
| POST | `/shipments/{id}/events` | Append tracking lifecycle events |

Insufficient inventory returns HTTP `409` with code `INSUFFICIENT_STOCK`.

## Billing

| Method | Path | Access |
|---|---|---|
| GET/POST | `/invoices` | Manager or admin |
| GET | `/payments` | Manager or admin |
| POST | `/invoices/{id}/payment-intent` | Manager or admin |

If Stripe is not configured, payment creation records `GATEWAY_NOT_CONFIGURED` instead of reporting a fake payment.

## Knowledge and assistant

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/knowledge/documents` | List or upload tenant documents |
| DELETE | `/knowledge/documents/{id}` | Remove a tenant document |
| POST | `/knowledge/search` | Retrieve grounded passages |
| POST | `/assistant/chat` | Generate a grounded assistant response |

## Realtime and health

- `GET /health` checks API and database readiness.
- `GET /live` checks process liveness.
- `/ws/{organization_id}` broadcasts authenticated tenant events. Browser clients send the JWT through the `whitfield-auth` WebSocket subprotocol rather than a query string.

When enabled, `/docs` is the authoritative interactive OpenAPI reference.
