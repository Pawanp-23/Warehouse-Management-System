from datetime import datetime, timedelta, timezone
import hashlib
import json

from commons.exceptions import DuplicateCommandError
from core.config import settings


def request_fingerprint(payload) -> str:
    value = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def get_record(db, organization_id: str, route: str, key: str, request_hash: str, session=None):
    record = await db.idempotency_records.find_one(
        {"organization_id": organization_id, "route": route, "key": key},
        session=session,
    )
    if record and record.get("request_hash") != request_hash:
        raise DuplicateCommandError("Idempotency key was already used with a different request")
    return record


async def save_record(db, organization_id: str, route: str, key: str, request_hash: str, response: dict, session):
    now = datetime.now(timezone.utc)
    await db.idempotency_records.insert_one(
        {
            "organization_id": organization_id,
            "route": route,
            "key": key,
            "request_hash": request_hash,
            "response": response,
            "created_at": now,
            "expires_at": now + timedelta(hours=settings.idempotency_ttl_hours),
        },
        session=session,
    )
