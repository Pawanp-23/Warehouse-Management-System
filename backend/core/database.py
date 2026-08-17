from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.server_api import ServerApi

from core.config import settings

client: AsyncMongoClient | None = None


async def connect_to_mongo() -> None:
    """Connect to MongoDB with automatic fallback strategies for Atlas cloud clusters."""
    global client
    uri = settings.mongodb_uri
    is_atlas = "mongodb.net" in uri or uri.startswith("mongodb+srv://")

    base_kwargs: dict = {
        "serverSelectionTimeoutMS": settings.mongo_server_selection_timeout_ms,
        "connectTimeoutMS": settings.mongo_connect_timeout_ms,
        "maxPoolSize": settings.mongo_max_pool_size,
        "retryWrites": True,
        "appName": "whitfield-wms-api",
    }

    # Build ordered list of connection strategies to try
    strategies: list[dict] = []

    if is_atlas:
        # Strategy 1: Atlas with Stable API + allow invalid TLS certs
        strategies.append({**base_kwargs, "server_api": ServerApi("1"), "tlsAllowInvalidCertificates": True})
        # Strategy 2: Atlas with Stable API + full TLS disabled
        strategies.append({**base_kwargs, "server_api": ServerApi("1"), "tls": False})
        # Strategy 3: Atlas without Stable API + allow invalid TLS certs
        strategies.append({**base_kwargs, "tlsAllowInvalidCertificates": True})
        # Strategy 4: Atlas plain — let pymongo decide
        strategies.append({**base_kwargs})
    else:
        # Local / non-Atlas: plain connection, no TLS
        strategies.append({**base_kwargs, "server_api": ServerApi("1")})
        strategies.append({**base_kwargs})

    last_error: Exception | None = None
    for i, kwargs in enumerate(strategies, 1):
        try:
            c = AsyncMongoClient(uri, **kwargs)
            await c.admin.command("ping")
            client = c
            return
        except Exception as exc:
            last_error = exc
            try:
                await c.close()
            except Exception:
                pass

    raise RuntimeError(f"Could not connect to MongoDB after {len(strategies)} strategies: {last_error}")


async def close_mongo_connection() -> None:
    if client is not None:
        await client.close()


def get_database():
    if client is None:
        raise RuntimeError("MongoDB connection has not been initialized")
    return client[settings.mongodb_database]


def get_client() -> AsyncMongoClient:
    if client is None:
        raise RuntimeError("MongoDB connection has not been initialized")
    return client


async def create_indexes() -> None:
    db = get_database()
    await db.organizations.create_index(
        [("name", ASCENDING)],
        unique=True,
        name="unique_organization_name",
    )
    await db.sellers.create_index(
        [("organization_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="unique_seller_code",
    )
    await db.products.create_index(
        [("organization_id", ASCENDING), ("seller_id", ASCENDING), ("sku", ASCENDING)],
        unique=True,
        name="unique_seller_sku",
    )
    await db.warehouses.create_index(
        [("organization_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="unique_warehouse_code",
    )
    await db.locations.create_index(
        [("warehouse_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="unique_location_code",
    )
    await db.inventory_balances.create_index(
        [
            ("organization_id", ASCENDING),
            ("seller_id", ASCENDING),
            ("product_id", ASCENDING),
            ("warehouse_id", ASCENDING),
            ("location_id", ASCENDING),
            ("stock_status", ASCENDING),
        ],
        unique=True,
        name="unique_inventory_position",
    )
    await db.inbound_receipts.create_index(
        [
            ("organization_id", ASCENDING),
            ("seller_id", ASCENDING),
            ("warehouse_id", ASCENDING),
            ("reference_type", ASCENDING),
            ("reference_value", ASCENDING),
        ],
        unique=True,
        name="unique_receipt_reference",
    )
    await db.orders.create_index(
        [("organization_id", ASCENDING), ("seller_id", ASCENDING), ("order_number", ASCENDING)],
        unique=True,
        name="unique_seller_order_number",
    )
    await db.idempotency_records.create_index(
        [("organization_id", ASCENDING), ("route", ASCENDING), ("key", ASCENDING)],
        unique=True,
        name="unique_idempotency_request",
    )
    await db.idempotency_records.create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="expire_idempotency_records",
    )
    await db.products.create_index(
        [("organization_id", ASCENDING), ("barcodes", ASCENDING)],
        unique=True,
        name="unique_organization_barcode",
    )
    await db.inventory_movements.create_index(
        [("organization_id", ASCENDING), ("created_at", DESCENDING)],
        name="inventory_movement_timeline",
    )
    await db.inventory_reservations.create_index(
        [("organization_id", ASCENDING), ("order_id", ASCENDING)],
        name="order_reservations",
    )
    await db.audit_logs.create_index(
        [("organization_id", ASCENDING), ("created_at", DESCENDING)],
        name="audit_log_timeline",
    )
    await db.knowledge_documents.create_index(
        [("organization_id", ASCENDING), ("sha256", ASCENDING)],
        unique=True,
        name="unique_tenant_knowledge_document",
    )
    await db.knowledge_documents.create_index(
        [("organization_id", ASCENDING), ("created_at", DESCENDING)],
        name="knowledge_document_timeline",
    )
    await db.knowledge_chunks.create_index(
        [("organization_id", ASCENDING), ("document_id", ASCENDING), ("chunk_index", ASCENDING)],
        unique=True,
        name="unique_knowledge_chunk",
    )
    await db.knowledge_chunks.create_index(
        [("organization_id", ASCENDING), ("terms", ASCENDING)],
        name="knowledge_term_lookup",
    )
    await db.users.create_index([("email", ASCENDING)], unique=True, name="unique_user_email")
    await db.users.create_index([("organization_id", ASCENDING), ("role", ASCENDING)], name="tenant_user_roles")
    await db.shipments.create_index([("organization_id", ASCENDING), ("tracking_number", ASCENDING)], unique=True, name="unique_tracking_number")
    await db.shipments.create_index([("organization_id", ASCENDING), ("created_at", DESCENDING)], name="shipment_timeline")
    await db.invoices.create_index([("organization_id", ASCENDING), ("invoice_number", ASCENDING)], unique=True, name="unique_invoice_number")
    await db.payments.create_index([("organization_id", ASCENDING), ("invoice_id", ASCENDING)], name="invoice_payments")
