import re
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request, status

from core.config import settings
from core.security import AuthContext, decode_access_token

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _validate_identifier(value: str | None, field: str) -> str:
    if value is None or not IDENTIFIER_PATTERN.fullmatch(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}")
    return value


async def get_auth_context(
    request: Request,
    authorization: str | None = Header(default=None),
    x_organization_id: str | None = Header(default=None),
    x_actor_id: str | None = Header(default=None),
) -> AuthContext:
    cached = getattr(request.state, "auth_context", None)
    if cached is not None:
        return cached

    if authorization and authorization.startswith("Bearer "):
        context = decode_access_token(authorization[7:].strip())
        if x_organization_id and context.organization_id != x_organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token organization mismatch")
    elif settings.auth_required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        context = AuthContext(
            actor_id=_validate_identifier(x_actor_id or "development-user", "actor ID"),
            organization_id=_validate_identifier(x_organization_id, "organization ID") if x_organization_id else None,
            roles=frozenset({"platform_admin", "admin", "manager", "operator", "viewer"}),
        )

    request.state.auth_context = context
    return context


async def get_organization_id(context: AuthContext = Depends(get_auth_context)) -> str:
    if context.organization_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization context required")
    return _validate_identifier(context.organization_id, "organization ID")


async def get_actor_id(context: AuthContext = Depends(get_auth_context)) -> str:
    return _validate_identifier(context.actor_id, "actor ID")


async def get_idempotency_key(idempotency_key: str = Header(...)) -> str:
    if not 8 <= len(idempotency_key) <= 128 or not IDENTIFIER_PATTERN.fullmatch(idempotency_key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Idempotency-Key")
    return idempotency_key


def require_roles(*allowed_roles: str) -> Callable:
    async def dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not context.roles.intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return context

    return dependency


def require_match(value: str | None, expected: str, field: str) -> None:
    if value != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{field} does not belong to the current organization",
        )
