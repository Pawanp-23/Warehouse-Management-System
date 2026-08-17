from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class Address(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    line1: str = Field(min_length=3, max_length=150)
    city: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=80)
    postal_code: str = Field(min_length=3, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=2)


class CreateShipmentRequest(BaseModel):
    order_id: str
    carrier_id: str = Field(min_length=2, max_length=50)
    carrier_name: str = Field(min_length=2, max_length=80)
    service_level: str = Field(min_length=2, max_length=80)
    tracking_number: str = Field(min_length=5, max_length=100)
    ship_to: Address


class TrackingUpdateRequest(BaseModel):
    status: str = Field(pattern="^(LABEL_CREATED|PICKED_UP|IN_TRANSIT|OUT_FOR_DELIVERY|DELIVERED|EXCEPTION)$")
    location: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)


class ShipmentResource(BaseModel):
    id: str
    order_id: str
    order_number: str
    carrier_id: str
    carrier_name: str
    service_level: str
    tracking_number: str
    status: str
    ship_to: Address
    events: list[dict]
    created_at: datetime


class CreateInvoiceRequest(BaseModel):
    order_id: str
    subtotal_cents: int = Field(gt=0, le=100_000_000)
    tax_cents: int = Field(default=0, ge=0, le=20_000_000)
    currency: str = Field(default="usd", pattern="^[a-z]{3}$")
    due_days: int = Field(default=30, ge=0, le=365)


class InvoiceResource(BaseModel):
    id: str
    invoice_number: str
    order_id: str
    order_number: str
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    currency: str
    status: str
    due_at: datetime
    created_at: datetime


class PaymentIntentResource(BaseModel):
    id: str
    invoice_id: str
    provider: str
    provider_payment_id: str | None
    amount_cents: int
    currency: str
    status: str
    client_secret: str | None = None
    created_at: datetime
