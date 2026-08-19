"""Import local JSON exports into MongoDB Atlas."""
import asyncio, json, os, sys
from pathlib import Path
from pymongo import AsyncMongoClient

ATLAS_URI = (
    "mongodb+srv://pawanpatil2305_db_user:zruCMEeKfZXhbQn3"
    "@cluster0.0yaslwp.mongodb.net/whitfield_wms"
    "?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
)
EXPORT_DIR = Path(r"C:\Users\pawpa\OneDrive\Desktop\whitfield-export")
DB_NAME = "whitfield_wms"

# Skip re-seeding users (already done by seed.py)
SKIP_COLLECTIONS = {"users"}

async def main():
    print("Connecting to Atlas...")
    client = AsyncMongoClient(ATLAS_URI, serverSelectionTimeoutMS=10_000)
    await client.admin.command("ping")
    print("Connected!\n")
    db = client[DB_NAME]

    json_files = sorted(EXPORT_DIR.glob("*.json"))
    for f in json_files:
        collection = f.stem
        if collection in SKIP_COLLECTIONS:
            print(f"  SKIP  {collection}")
            continue
        docs = json.loads(f.read_text(encoding="utf-8-sig"))
        if not docs:
            print(f"  EMPTY {collection}")
            continue
        # Drop existing and re-import
        await db[collection].drop()
        result = await db[collection].insert_many(docs)
        print(f"  OK    {collection:30s} -> {len(result.inserted_ids)} docs")


    await client.close()
    print("\n✅ Import complete! Refresh the app to see your data.")

if __name__ == "__main__":
    asyncio.run(main())
