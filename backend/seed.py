"""
Whitfield WMS - One-shot seed script
Creates the organization and all four user accounts.
Run ONCE after MongoDB replica set is up and backend deps are installed:
    python seed.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from uuid import uuid4

from pymongo import AsyncMongoClient
from pymongo.server_api import ServerApi

from core.config import settings
from core.security import hash_password

MONGO_URI = settings.mongodb_uri
DB_NAME   = settings.mongodb_database

ORG_NAME  = "Whitfield Fulfillment"
ORG_ID    = str(uuid4())

USERS = [
    {"name": "Admin",   "email": "admin@whitfieldwms.com",   "password": "Whitfield!Admin2026",   "role": "admin"},
    {"name": "Manager", "email": "manager@whitfieldwms.com", "password": "Whitfield!Manager2026", "role": "manager"},
    {"name": "Staff",   "email": "staff@whitfieldwms.com",   "password": "Whitfield!Staff2026",   "role": "staff"},
    {"name": "User",    "email": "user@whitfieldwms.com",    "password": "Whitfield!User2026",    "role": "user"},
]


async def seed() -> None:
    print("\n" + "="*55)
    print("  Whitfield WMS - Seed Script")
    print("="*55)

    client = AsyncMongoClient(
        MONGO_URI,
        server_api=ServerApi("1"),
        serverSelectionTimeoutMS=5_000,
        appName="whitfield-seed",
    )

    try:
        await client.admin.command("ping")
        print("Connected to MongoDB")
    except Exception as exc:
        print(f"\nERROR: Cannot reach MongoDB: {exc}")
        print("Make sure the MongoDB service is running with --replSet rs0.")
        sys.exit(1)

    db = client[DB_NAME]

    existing_org = await db.organizations.find_one({"name": ORG_NAME})
    if existing_org:
        org_id = existing_org["_id"]
        print(f"Organization already exists (id={org_id})")
    else:
        now = datetime.now(timezone.utc)
        org_doc = {"_id": ORG_ID, "name": ORG_NAME, "created_at": now, "updated_at": now}
        await db.organizations.insert_one(org_doc)
        org_id = ORG_ID
        print(f"Organization created (id={org_id})")

    print()
    for u in USERS:
        existing = await db.users.find_one({"email": u["email"].lower()})
        if existing:
            print(f"[{u['role'].upper():<8}] {u['email']} - already exists, skipped")
            continue
        now = datetime.now(timezone.utc)
        user_doc = {
            "_id": str(uuid4()), "organization_id": org_id,
            "name": u["name"], "email": u["email"].lower(),
            "password_hash": hash_password(u["password"]),
            "role": u["role"], "active": True,
            "created_at": now, "updated_at": now,
        }
        await db.users.insert_one(user_doc)
        print(f"[{u['role'].upper():<8}] {u['email']} - created")

    await client.close()

    print("\n" + "="*55)
    print("  Seed complete! Login credentials:")
    print("="*55)
    for u in USERS:
        print(f"  {u['role'].upper():<10} {u['email']:<32} {u['password']}")
    print("="*55)
    print("\n  API docs  -> http://localhost:8000/docs")
    print("  Frontend  -> http://localhost:3001\n")


if __name__ == "__main__":
    asyncio.run(seed())
