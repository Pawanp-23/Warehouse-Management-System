from datetime import datetime, timezone

from pymongo import ReturnDocument


def inventory_position_filter(
    *,
    organization_id: str,
    seller_id: str,
    product_id: str,
    warehouse_id: str,
    location_id: str,
    stock_status: str,
) -> dict:
    return {
        "organization_id": organization_id,
        "seller_id": seller_id,
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "location_id": location_id,
        "stock_status": stock_status,
    }


async def increment_balance(db, position: dict, quantity: int, session):
    now = datetime.now(timezone.utc)
    return await db.inventory_balances.find_one_and_update(
        position,
        {"$inc": {"quantity": quantity}, "$set": {"updated_at": now}, "$setOnInsert": {"created_at": now}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        session=session,
    )


async def reserve_available_balance(db, position: dict, quantity: int, session):
    now = datetime.now(timezone.utc)
    return await db.inventory_balances.find_one_and_update(
        {**position, "quantity": {"$gte": quantity}},
        {"$inc": {"quantity": -quantity}, "$set": {"updated_at": now}},
        return_document=ReturnDocument.AFTER,
        session=session,
    )


async def decrement_balance(db, position: dict, quantity: int, session):
    now = datetime.now(timezone.utc)
    return await db.inventory_balances.find_one_and_update(
        {**position, "quantity": {"$gte": quantity}},
        {"$inc": {"quantity": -quantity}, "$set": {"updated_at": now}},
        return_document=ReturnDocument.AFTER,
        session=session,
    )
