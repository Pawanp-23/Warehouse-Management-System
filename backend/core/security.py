import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from core.config import settings


@dataclass(frozen=True)
class AuthContext:
    actor_id: str
    organization_id: str | None
    roles: frozenset[str]


def _decode_segment(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from error


def decode_access_token(token: str) -> AuthContext:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    encoded_header, encoded_payload, encoded_signature = parts
    try:
        header: dict[str, Any] = json.loads(_decode_segment(encoded_header))
        payload: dict[str, Any] = json.loads(_decode_segment(encoded_payload))
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from error

    if header.get("alg") != "HS256" or header.get("typ") not in (None, "JWT"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported access token")

    message = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected = hmac.new(settings.jwt_secret.encode("utf-8"), message, hashlib.sha256).digest()
    supplied = _decode_segment(encoded_signature)
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    now = int(time.time())
    if not isinstance(payload.get("exp"), (int, float)) or int(payload["exp"]) <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token has expired")
    if payload.get("nbf") is not None and int(payload["nbf"]) > now + 30:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is not active")
    if payload.get("iss") != settings.jwt_issuer or payload.get("aud") != settings.jwt_audience:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token claims")

    actor_id = payload.get("sub")
    organization_id = payload.get("org_id")
    raw_roles = payload.get("roles", [])
    if not isinstance(actor_id, str) or not actor_id or not isinstance(raw_roles, list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token claims")
    if organization_id is not None and (not isinstance(organization_id, str) or not organization_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token claims")

    roles = frozenset(role for role in raw_roles if isinstance(role, str) and role)
    return AuthContext(actor_id=actor_id, organization_id=organization_id, roles=roles)


def create_access_token(actor_id: str, organization_id: str, role: str) -> str:
    now = int(time.time())
    role_map = {
        "user": ["user", "viewer"],
        "staff": ["staff", "viewer"],
        "manager": ["manager", "operator", "viewer"],
        "admin": ["admin", "manager", "operator", "viewer"],
    }
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": actor_id, "org_id": organization_id, "roles": role_map[role], "iss": settings.jwt_issuer,
               "aud": settings.jwt_audience, "iat": now, "exp": now + settings.access_token_minutes * 60}
    encode = lambda value: base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).rstrip(b"=").decode()
    encoded_header, encoded_payload = encode(header), encode(payload)
    signature = hmac.new(settings.jwt_secret.encode(), f"{encoded_header}.{encoded_payload}".encode(), hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def hash_password(password: str) -> str:
    salt = hashlib.sha256(f"{time.time_ns()}:{password}".encode()).digest()[:16]
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(derived).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_value, hash_value = encoded.split("$", 2)
        if algorithm != "scrypt": return False
        salt = base64.urlsafe_b64decode(salt_value)
        expected = base64.urlsafe_b64decode(hash_value)
        supplied = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(expected, supplied)
    except (ValueError, TypeError):
        return False
