import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from core.apis.schemas.orders import CreateOrderRequest, OrderItemRequest
from core.config import settings
from core.cruds.idempotency_crud import request_fingerprint
from core.security import create_access_token, decode_access_token, hash_password, verify_password


def _encode(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _token(payload: dict, secret: str | None = None) -> str:
    header = _encode({"alg": "HS256", "typ": "JWT"})
    body = _encode(payload)
    signature = hmac.new((secret or settings.jwt_secret).encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii')}"


def _claims(**overrides):
    claims = {
        "sub": "operator-1",
        "org_id": "organization-1",
        "roles": ["operator"],
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": int(time.time()) + 300,
    }
    claims.update(overrides)
    return claims


def test_valid_token_binds_actor_tenant_and_roles():
    context = decode_access_token(_token(_claims()))
    assert context.actor_id == "operator-1"
    assert context.organization_id == "organization-1"
    assert context.roles == {"operator"}


@pytest.mark.parametrize("token", [_token(_claims(exp=1)), _token(_claims(), secret="wrong-secret")])
def test_expired_or_tampered_tokens_are_rejected(token):
    with pytest.raises(HTTPException) as error:
        decode_access_token(token)
    assert error.value.status_code == 401


def test_idempotency_fingerprint_is_stable_and_payload_sensitive():
    first = OrderItemRequest(product_id="product-1", location_id="location-1", quantity=2)
    request = CreateOrderRequest(seller_id="seller-1", warehouse_id="warehouse-1", order_number="ORDER-1", items=[first])
    same = CreateOrderRequest(seller_id="seller-1", warehouse_id="warehouse-1", order_number="ORDER-1", items=[first])
    changed = CreateOrderRequest(seller_id="seller-1", warehouse_id="warehouse-1", order_number="ORDER-1", items=[OrderItemRequest(product_id="product-1", location_id="location-1", quantity=3)])
    assert request_fingerprint(request) == request_fingerprint(same)
    assert request_fingerprint(request) != request_fingerprint(changed)


def test_duplicate_order_positions_are_rejected():
    line = {"product_id": "product-1", "location_id": "location-1", "quantity": 1}
    with pytest.raises(ValidationError):
        CreateOrderRequest(seller_id="seller-1", warehouse_id="warehouse-1", order_number="ORDER-1", items=[line, line])


def test_password_hashes_are_salted_and_verifiable():
    first = hash_password("StrongPassword!2026")
    second = hash_password("StrongPassword!2026")
    assert first != second
    assert verify_password("StrongPassword!2026", first)
    assert not verify_password("wrong-password", first)


def test_created_access_token_contains_tenant_role_mapping():
    context = decode_access_token(create_access_token("user-1", "organization-1", "staff"))
    assert context.actor_id == "user-1"
    assert context.organization_id == "organization-1"
    assert {"staff", "viewer"}.issubset(context.roles)
    assert "operator" not in context.roles
