# Database design

Whitfield uses tenant-scoped MongoDB collections and a permanent inventory ledger. A single editable product `quantity` is not the source of truth.

## Core collections

- `organizations`: 3PL tenants.
- `users`: tenant users, password hashes, roles, and activation state.
- `sellers`: brands whose inventory is managed by a tenant.
- `warehouses`: physical fulfillment sites.
- `locations`: scan-ready bins belonging to a warehouse.
- `products`: seller-owned SKUs and barcodes.
- `inbound_receipts`: inbound deliveries and scan lines.
- `inventory_balances`: current stock projections by tenant, seller, product, warehouse, bin, and status.
- `inventory_movements`: append-only stock ledger entries.
- `orders`: fulfillment orders and reserved line items.
- `inventory_reservations`: stock allocations for orders.
- `shipments`: carrier, recipient, tracking number, and lifecycle events.
- `invoices`: server-calculated financial documents.
- `payments`: payment-provider intent state.
- `knowledge_documents`: tenant-scoped document chunks and metadata.
- `audit_logs`: accountable material actions.
- `idempotency_records`: payload-bound command deduplication.

All operational documents contain `organization_id`. Related resources use stable UUID strings and compound unique indexes scoped to the tenant.

## Inventory states

- `RECEIVING`: scanned good stock that has not completed receiving.
- `AVAILABLE`: sellable stock.
- `RESERVED`: allocated to an order.
- `DAMAGED`: non-sellable stock.

## State transitions

```text
good scan -> RECEIVING
receipt completion -> AVAILABLE
order reservation -> RESERVED
shipment creation -> stock leaves RESERVED and shipment becomes authoritative
damaged scan -> DAMAGED
```

Stock-changing commands execute in MongoDB transactions and use idempotency keys. The API updates balance projections and appends immutable movement records in the same transaction, preventing partial reservations and negative inventory.

## Indexing principles

- Tenant ID is the leading field for operational queries.
- Seller codes, warehouse codes, location codes, SKUs, order numbers, tracking numbers, and invoice numbers are uniquely constrained within their correct ownership scope.
- Idempotency records expire with a TTL index.
- List endpoints use bounded result sizes and deterministic sort orders.
