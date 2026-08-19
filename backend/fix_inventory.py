"""Increase available inventory for demo testing."""
import asyncio
from pymongo import AsyncMongoClient

ATLAS_URI = (
    "mongodb+srv://pawanpatil2305_db_user:zruCMEeKfZXhbQn3"
    "@cluster0.0yaslwp.mongodb.net/whitfield_wms"
    "?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
)

async def main():
    client = AsyncMongoClient(ATLAS_URI, serverSelectionTimeoutMS=10000)
    db = client["whitfield_wms"]
    r = await db.inventory_balances.update_many(
        {"stock_status": "AVAILABLE"},
        {"$set": {"quantity": 100}}
    )
    print(f"Updated {r.modified_count} AVAILABLE balance records to qty=100")
    await client.close()

asyncio.run(main())
