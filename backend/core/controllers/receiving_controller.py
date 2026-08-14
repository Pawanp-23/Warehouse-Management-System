from datetime import datetime, timezone
from uuid import uuid4

from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo.errors import DuplicateKeyError

from commons.dependencies import require_match
from core.cruds.idempotency_crud import get_record, request_fingerprint, save_record
from core.cruds.inventory_crud import decrement_balance, increment_balance, inventory_position_filter
from core.database import get_client, get_database


async def create_receipt(organization_id: str, payload):
    db = get_database()
    seller = await db.sellers.find_one({"_id": payload.seller_id, "organization_id": organization_id})
    warehouse = await db.warehouses.find_one({"_id": payload.warehouse_id, "organization_id": organization_id})
    if not seller or not warehouse:
        raise ValueError("Seller or warehouse does not belong to this organization")

    now = datetime.now(timezone.utc)
    receipt = {
        "_id": str(uuid4()),
        "organization_id": organization_id,
        "seller_id": payload.seller_id,
        "warehouse_id": payload.warehouse_id,
        "reference_type": payload.reference_type,
        "reference_value": payload.reference_value.strip().upper(),
        "status": "DRAFT",
        "lines": [],
        "created_at": now,
        "updated_at": now,
    }
    await db.inbound_receipts.insert_one(receipt)
    return receipt


async def receive_scan(organization_id: str, actor_id: str, receipt_id: str, payload, idempotency_key: str):
    db = get_database()
    client = get_client()
    route = f"receipt-scan:{receipt_id}"
    request_hash = request_fingerprint(payload)
    existing = await get_record(db, organization_id, route, idempotency_key, request_hash)
    if existing:
        return existing["response"]

    receipt = await db.inbound_receipts.find_one({"_id": receipt_id, "organization_id": organization_id})
    if not receipt:
        raise LookupError("Receipt not found")
    if receipt["status"] == "COMPLETED":
        raise ValueError("Completed receipts cannot receive additional stock")

    product = await db.products.find_one(
        {"_id": payload.product_id, "organization_id": organization_id, "seller_id": receipt["seller_id"]}
    )
    location = await db.locations.find_one({"_id": payload.location_id, "organization_id": organization_id, "warehouse_id": receipt["warehouse_id"]})
    if not product or not location:
        raise ValueError("Product or location is invalid for this receipt")

    movement_id = str(uuid4())
    status = "RECEIVING" if payload.condition == "GOOD" else "DAMAGED"

    async def transaction(session):
        existing = await get_record(db, organization_id, route, idempotency_key, request_hash, session)
        if existing:
            return existing["response"]

        position = inventory_position_filter(
            organization_id=organization_id,
            seller_id=receipt["seller_id"],
            product_id=payload.product_id,
            warehouse_id=receipt["warehouse_id"],
            location_id=payload.location_id,
            stock_status=status,
        )
        balance = await increment_balance(db, position, payload.quantity, session)
        now = datetime.now(timezone.utc)
        await db.inventory_movements.insert_one(
            {
                "_id": movement_id,
                **position,
                "movement_type": "RECEIVE_GOOD" if status == "RECEIVING" else "RECEIVE_DAMAGED",
                "quantity": payload.quantity,
                "reference_type": "INBOUND_RECEIPT",
                "reference_id": receipt_id,
                "actor_id": actor_id,
                "idempotency_key": idempotency_key,
                "created_at": now,
            },
            session=session,
        )
        await db.inbound_receipts.update_one(
            {"_id": receipt_id},
            {
                "$push": {"lines": {"product_id": payload.product_id, "location_id": payload.location_id, "quantity": payload.quantity, "condition": payload.condition, "movement_id": movement_id, "received_at": now}},
                "$set": {"updated_at": now},
            },
            session=session,
        )
        await db.audit_logs.insert_one(
            {"_id": str(uuid4()), "organization_id": organization_id, "actor_id": actor_id, "action": "INVENTORY_RECEIVED", "entity_type": "inventory_movement", "entity_id": movement_id, "metadata": {"receipt_id": receipt_id, "quantity": payload.quantity, "stock_status": status}, "created_at": now},
            session=session,
        )
        response = {"id": movement_id, "status": "RECORDED", "received_quantity": payload.quantity, "stock_status": status, "balance_quantity": balance["quantity"]}
        await save_record(db, organization_id, route, idempotency_key, request_hash, response, session)
        return response

    try:
        async with client.start_session() as session:
            return await session.with_transaction(transaction, read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority"))
    except DuplicateKeyError:
        existing = await get_record(db, organization_id, route, idempotency_key, request_hash)
        if existing:
            return existing["response"]
        raise


async def complete_receipt(organization_id: str, actor_id: str, receipt_id: str, idempotency_key: str):
    db = get_database()
    client = get_client()
    route = f"complete-receipt:{receipt_id}"
    request_hash = request_fingerprint({"receipt_id": receipt_id})

    async def transaction(session):
        existing = await get_record(db, organization_id, route, idempotency_key, request_hash, session)
        if existing:
            return existing["response"]
        now = datetime.now(timezone.utc)
        receipt = await db.inbound_receipts.find_one_and_update(
            {"_id": receipt_id, "organization_id": organization_id, "status": "DRAFT"},
            {"$set": {"status": "COMPLETED", "completed_by": actor_id, "updated_at": now}},
            session=session,
        )
        if not receipt:
            raise LookupError("Receipt not found or already completed")

        for line in receipt["lines"]:
            if line["condition"] != "GOOD":
                continue
            receiving_position = inventory_position_filter(
                organization_id=organization_id,
                seller_id=receipt["seller_id"],
                product_id=line["product_id"],
                warehouse_id=receipt["warehouse_id"],
                location_id=line["location_id"],
                stock_status="RECEIVING",
            )
            moved = await decrement_balance(db, receiving_position, line["quantity"], session)
            if not moved:
                raise RuntimeError("Receipt inventory is inconsistent")
            available_position = {**receiving_position, "stock_status": "AVAILABLE"}
            await increment_balance(db, available_position, line["quantity"], session)
            await db.inventory_movements.insert_one(
                {
                    "_id": str(uuid4()),
                    **receiving_position,
                    "movement_type": "PUTAWAY",
                    "quantity": line["quantity"],
                    "to_stock_status": "AVAILABLE",
                    "reference_type": "INBOUND_RECEIPT",
                    "reference_id": receipt_id,
                    "actor_id": actor_id,
                    "created_at": now,
                },
                session=session,
            )

        await db.audit_logs.insert_one(
            {"_id": str(uuid4()), "organization_id": organization_id, "actor_id": actor_id, "action": "RECEIPT_COMPLETED", "entity_type": "inbound_receipt", "entity_id": receipt_id, "metadata": {"line_count": len(receipt["lines"])}, "created_at": now},
            session=session,
        )
        response = {"id": receipt_id, "status": "COMPLETED"}
        await save_record(db, organization_id, route, idempotency_key, request_hash, response, session)
        return response

    try:
        async with client.start_session() as session:
            return await session.with_transaction(transaction, read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority"))
    except DuplicateKeyError:
        existing = await get_record(db, organization_id, route, idempotency_key, request_hash)
        if existing:
            return existing["response"]
        raise
