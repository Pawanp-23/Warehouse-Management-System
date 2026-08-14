from datetime import datetime, timezone
from uuid import uuid4

from core.config import settings
from core.database import get_database
from core.security import create_access_token, hash_password, verify_password


def resource(user: dict) -> dict:
    return {"id": user["_id"], "name": user["name"], "email": user["email"], "organization_id": user["organization_id"], "role": user["role"], "active": user["active"]}


async def register(payload) -> dict:
    db = get_database()
    organization = await db.organizations.find_one({"_id": payload.organization_id}, {"_id": 1})
    if not organization:
        raise ValueError("Organization does not exist")
    role_count = await db.users.count_documents({"organization_id": payload.organization_id})
    if payload.role == "admin" and role_count > 0 and payload.invite_code != settings.admin_invite_code:
        raise PermissionError("Valid admin invite code required")
    if payload.role == "manager" and payload.invite_code != settings.manager_invite_code:
        raise PermissionError("Valid manager invite code required")
    now = datetime.now(timezone.utc)
    user = {"_id": str(uuid4()), "organization_id": payload.organization_id, "name": payload.name.strip(),
            "email": str(payload.email).lower(), "password_hash": hash_password(payload.password), "role": payload.role,
            "active": True, "created_at": now, "updated_at": now}
    await db.users.insert_one(user)
    return {"access_token": create_access_token(user["_id"], user["organization_id"], user["role"]), "user": resource(user)}


async def login(email: str, password: str) -> dict:
    user = await get_database().users.find_one({"email": email.lower()})
    if not user or not user.get("active") or not verify_password(password, user.get("password_hash", "")):
        raise PermissionError("Invalid email or password")
    return {"access_token": create_access_token(user["_id"], user["organization_id"], user["role"]), "user": resource(user)}
