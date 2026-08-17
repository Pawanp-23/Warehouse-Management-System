from datetime import datetime, timezone
from uuid import uuid4

from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo.errors import DuplicateKeyError

from commons.exceptions import InsufficientStockError
from core.cruds.idempotency_crud import get_record, request_fingerprint, save_record
from core.cruds.inventory_crud import increment_balance, inventory_position_filter, reserve_available_balance
from core.database import get_client, get_database


async def create_and_reserve_order(organization_id: str, actor_id: str, payload, idempotency_key: str):
    db = get_database()
    client = get_client()
    route = "create-order"
    request_hash = request_fingerprint(payload)
    existing = await get_record(db, organization_id, route, idempotency_key, request_hash)
    if existing:
        return existing["response"]

    seller = await db.sellers.find_one({"_id": payload.seller_id, "organization_id": organization_id})
    warehouse = await db.warehouses.find_one({"_id": payload.warehouse_id, "organization_id": organization_id})
    if not seller or not warehouse:
        raise ValueError("Seller or warehouse does not belong to this organization")

    order_id = str(uuid4())

    async def transaction(session):
        existing = await get_record(db, organization_id, route, idempotency_key, request_hash, session)
        if existing:
            return existing["response"]

        now = datetime.now(timezone.utc)
        reservations = []
        for item in payload.items:
            product = await db.products.find_one({"_id": item.product_id, "organization_id": organization_id, "seller_id": payload.seller_id}, session=session)
            location = await db.locations.find_one({"_id": item.location_id, "organization_id": organization_id, "warehouse_id": payload.warehouse_id}, session=session)
            if not product or not location:
                raise ValueError("Order contains a product or location outside the selected seller/warehouse")

            available_position = inventory_position_filter(organization_id=organization_id, seller_id=payload.seller_id, product_id=item.product_id, warehouse_id=payload.warehouse_id, location_id=item.location_id, stock_status="AVAILABLE")
            available_balance = await reserve_available_balance(db, available_position, item.quantity, session)
            if not available_balance:
                current = await db.inventory_balances.find_one(available_position, session=session)
                raise InsufficientStockError(current["quantity"] if current else 0, item.quantity)

            reserved_position = {**available_position, "stock_status": "RESERVED"}
            await increment_balance(db, reserved_position, item.quantity, session)
            reservation_id = str(uuid4())
            movement_id = str(uuid4())
            reservations.append({"reservation_id": reservation_id, "product_id": item.product_id, "location_id": item.location_id, "quantity": item.quantity})
            await db.inventory_reservations.insert_one({"_id": reservation_id, "organization_id": organization_id, "order_id": order_id, **reserved_position, "quantity": item.quantity, "status": "RESERVED", "created_at": now}, session=session)
            await db.inventory_movements.insert_one({"_id": movement_id, **available_position, "movement_type": "RESERVE", "quantity": item.quantity, "to_stock_status": "RESERVED", "reference_type": "ORDER", "reference_id": order_id, "actor_id": actor_id, "idempotency_key": idempotency_key, "created_at": now}, session=session)

        await db.orders.insert_one({"_id": order_id, "organization_id": organization_id, "seller_id": payload.seller_id, "warehouse_id": payload.warehouse_id, "order_number": payload.order_number.strip().upper(), "source": payload.source, "status": "RESERVED", "items": [item.model_dump() for item in payload.items], "reservations": reservations, "created_at": now, "updated_at": now}, session=session)
        await db.audit_logs.insert_one({"_id": str(uuid4()), "organization_id": organization_id, "actor_id": actor_id, "action": "ORDER_RESERVED", "entity_type": "order", "entity_id": order_id, "metadata": {"order_number": payload.order_number, "reserved_quantity": sum(item.quantity for item in payload.items)}, "created_at": now}, session=session)
        response = {"id": order_id, "status": "RESERVED", "order_number": payload.order_number.strip().upper(), "reserved_quantity": sum(item.quantity for item in payload.items)}
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
