"""Add inventory balances for all products that don't have AVAILABLE stock."""
import asyncio
from datetime import datetime, timezone
from pymongo import AsyncMongoClient

ATLAS_URI = (
    "mongodb+srv://pawanpatil2305_db_user:zruCMEeKfZXhbQn3"
    "@cluster0.0yaslwp.mongodb.net/whitfield_wms"
    "?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
)

async def main():
    client = AsyncMongoClient(ATLAS_URI, serverSelectionTimeoutMS=10000)
    db = client["whitfield_wms"]
    now = datetime.now(timezone.utc)

    # Get all products, sellers, warehouses, locations
    products = await db.products.find({}).to_list(length=100)
    warehouses = await db.warehouses.find({}).to_list(length=100)
    locations = await db.locations.find({}).to_list(length=100)
    org_id = products[0]["organization_id"] if products else None

    print(f"Found {len(products)} products, {len(warehouses)} warehouses, {len(locations)} locations")

    added = 0
    for product in products:
        pid = product["_id"]
        seller_id = product.get("seller_id")
        for warehouse in warehouses:
            wid = warehouse["_id"]
            # Find a location in this warehouse
            loc = next((l for l in locations if l.get("warehouse_id") == wid), None)
            if not loc:
                continue
            # Check if AVAILABLE balance already exists
            existing = await db.inventory_balances.find_one({
                "product_id": pid, "warehouse_id": wid, "stock_status": "AVAILABLE"
            })
            if existing:
                # Just ensure quantity is high enough
                await db.inventory_balances.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"quantity": 100, "updated_at": now}}
                )
                print(f"  Updated existing AVAILABLE for {product.get('name', pid)[:30]} in {warehouse.get('name', wid)[:20]}")
            else:
                import uuid
                doc = {
                    "_id": str(uuid.uuid4()),
                    "organization_id": org_id,
                    "seller_id": seller_id,
                    "product_id": pid,
                    "warehouse_id": wid,
                    "location_id": loc["_id"],
                    "stock_status": "AVAILABLE",
                    "quantity": 100,
                    "created_at": now,
                    "updated_at": now,
                }
                await db.inventory_balances.insert_one(doc)
                print(f"  Added 100 units AVAILABLE for {product.get('name', pid)[:30]} in {warehouse.get('name', wid)[:20]}")
                added += 1

    await client.close()
    print(f"\nDone! Added {added} new inventory balance records. All products now have 100 units available.")

asyncio.run(main())
