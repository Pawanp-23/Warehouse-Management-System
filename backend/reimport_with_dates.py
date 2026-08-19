"""Re-import JSON exports to Atlas with proper datetime conversion."""
import asyncio, json, re
from pathlib import Path
from datetime import datetime, timezone
from pymongo import AsyncMongoClient

ATLAS_URI = (
    "mongodb+srv://pawanpatil2305_db_user:zruCMEeKfZXhbQn3"
    "@cluster0.0yaslwp.mongodb.net/whitfield_wms"
    "?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
)
EXPORT_DIR = Path(r"C:\Users\pawpa\OneDrive\Desktop\whitfield-export")
DB_NAME = "whitfield_wms"
SKIP_COLLECTIONS = {"users"}  # already seeded + fixed

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

def parse_dates(obj):
    """Recursively convert ISO datetime strings to Python datetime objects."""
    if isinstance(obj, dict):
        return {k: parse_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [parse_dates(v) for v in obj]
    if isinstance(obj, str) and ISO_RE.match(obj):
        try:
            # Handle Z suffix and +00:00
            s = obj.replace("Z", "+00:00")
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        except ValueError:
            return obj
    return obj

async def main():
    client = AsyncMongoClient(ATLAS_URI, serverSelectionTimeoutMS=10000)
    await client.admin.command("ping")
    print("Connected to Atlas!\n")
    db = client[DB_NAME]

    for f in sorted(EXPORT_DIR.glob("*.json")):
        collection = f.stem
        if collection in SKIP_COLLECTIONS:
            print(f"  SKIP  {collection}")
            continue
        raw_docs = json.loads(f.read_text(encoding="utf-8-sig"))
        if not raw_docs:
            print(f"  EMPTY {collection}")
            continue
        docs = [parse_dates(d) for d in raw_docs]
        await db[collection].drop()
        result = await db[collection].insert_many(docs)
        print(f"  OK    {collection:30s} -> {len(result.inserted_ids)} docs with proper datetimes")

    await client.close()
    print("\nDone! Backend 500 errors should be gone now.")

if __name__ == "__main__":
    asyncio.run(main())
