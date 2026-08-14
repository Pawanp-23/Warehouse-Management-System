from datetime import datetime, timezone
from uuid import uuid4

from core.database import get_database


async def create_organization(name: str) -> dict:
    now = datetime.now(timezone.utc)
    organization = {"_id": str(uuid4()), "name": name.strip(), "created_at": now, "updated_at": now}
    await get_database().organizations.insert_one(organization)
    return organization


async def create_seller(organization_id: str, payload) -> dict:
    if not await get_database().organizations.find_one({"_id": organization_id}, {"_id": 1}):
        raise ValueError("Organization does not exist")
    now = datetime.now(timezone.utc)
    seller = {"_id": str(uuid4()), "organization_id": organization_id, "name": payload.name.strip(), "code": payload.code.upper(), "created_at": now, "updated_at": now}
    await get_database().sellers.insert_one(seller)
    return seller


async def create_warehouse(organization_id: str, payload) -> dict:
    if not await get_database().organizations.find_one({"_id": organization_id}, {"_id": 1}):
        raise ValueError("Organization does not exist")
    now = datetime.now(timezone.utc)
    warehouse = {"_id": str(uuid4()), "organization_id": organization_id, "name": payload.name.strip(), "code": payload.code.upper(), "city": payload.city.strip(), "state": payload.state.strip(), "created_at": now, "updated_at": now}
    await get_database().warehouses.insert_one(warehouse)
    return warehouse


async def create_location(organization_id: str, payload) -> dict:
    db = get_database()
    warehouse = await db.warehouses.find_one({"_id": payload.warehouse_id, "organization_id": organization_id})
    if not warehouse:
        raise ValueError("Warehouse does not belong to this organization")
    now = datetime.now(timezone.utc)
    location = {"_id": str(uuid4()), "organization_id": organization_id, "warehouse_id": payload.warehouse_id, "name": payload.name.strip(), "code": payload.code.upper(), "created_at": now, "updated_at": now}
    await db.locations.insert_one(location)
    return location


async def create_product(organization_id: str, payload) -> dict:
    db = get_database()
    seller = await db.sellers.find_one({"_id": payload.seller_id, "organization_id": organization_id})
    if not seller:
        raise ValueError("Seller does not belong to this organization")
    now = datetime.now(timezone.utc)
    product = {"_id": str(uuid4()), "organization_id": organization_id, "seller_id": payload.seller_id, "sku": payload.sku.upper(), "name": payload.name.strip(), "barcodes": [payload.barcode.strip()], "created_at": now, "updated_at": now}
    await db.products.insert_one(product)
    return product
