from typing import Literal

from pydantic import Field

from core.apis.schemas.common import APIModel, CommandResponse, CreatedResource


class CreateReceiptRequest(APIModel):
    seller_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    warehouse_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    reference_type: Literal["CARRIER_TRACKING", "MANUAL_TICKET"]
    reference_value: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9 ._:/-]*$")


class ReceiveScanRequest(APIModel):
    product_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    location_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    quantity: int = Field(gt=0, le=100000)
    condition: Literal["GOOD", "DAMAGED"]


class ReceiptResponse(CreatedResource):
    status: str
    reference_value: str


class ReceiptCommandResponse(CommandResponse):
    received_quantity: int
    stock_status: str
    balance_quantity: int


class ReceiptListResponse(APIModel):
    id: str
    seller_id: str
    warehouse_id: str
    reference_type: str
    reference_value: str
    status: str
    line_count: int
    created_at: str
