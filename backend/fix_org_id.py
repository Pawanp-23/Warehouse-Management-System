"""Check and fix organization ID mismatch in Atlas."""
import asyncio
from pymongo import AsyncMongoClient

ATLAS_URI = (
    "mongodb+srv://pawanpatil2305_db_user:zruCMEeKfZXhbQn3"
    "@cluster0.0yaslwp.mongodb.net/whitfield_wms"
    "?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
)

COLLECTIONS_WITH_ORG = [
    "sellers", "products", "warehouses", "locations",
    "orders", "inventory_balances", "inventory_movements",
    "inventory_reservations", "inbound_receipts", "shipments",
    "invoices", "payments", "audit_logs",
]

async def main():
    client = AsyncMongoClient(ATLAS_URI, serverSelectionTimeoutMS=10000)
    db = client["whitfield_wms"]

    # Find all organizations
    orgs = await db.organizations.find({}).to_list(length=10)
    print("Organizations in Atlas:")
    for o in orgs:
        print(f"  {o['_id']} - {o['name']}")

    # Find the seeded admin user's org
    admin = await db.users.find_one({"email": "admin@whitfieldwms.com"})
    seeded_org_id = admin["organization_id"]
    print(f"\nSeeded admin belongs to org: {seeded_org_id}")

    # Find the imported organization (the one with actual data)
    imported_org = next((o for o in orgs if o["_id"] != seeded_org_id), None)
    if not imported_org:
        print("Only one org found — no mismatch!")
        await client.close()
        return

    imported_org_id = imported_org["_id"]
    print(f"Imported data org:           {imported_org_id}")
    print(f"\nFixing: updating all users to use imported org {imported_org_id}...")

    # Update all users to point to the imported org
    r = await db.users.update_many({}, {"$set": {"organization_id": imported_org_id}})
    print(f"  Updated {r.modified_count} users")

    # Delete the duplicate seeded org
    await db.organizations.delete_one({"_id": seeded_org_id})
    print(f"  Deleted duplicate seeded org {seeded_org_id}")

    # Verify counts
    print("\nData counts in imported org:")
    for coll in COLLECTIONS_WITH_ORG:
        count = await db[coll].count_documents({"organization_id": imported_org_id})
        if count:
            print(f"  {coll:30s} {count} docs")

    await client.close()
    print("\nDone! Refresh the app to see all data.")

if __name__ == "__main__":
    asyncio.run(main())
