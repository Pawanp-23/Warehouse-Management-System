from typing import Literal

from pydantic import Field, model_validator

from core.apis.schemas.common import APIModel, CommandResponse


class OrderItemRequest(APIModel):
    product_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    location_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    quantity: int = Field(gt=0, le=100000)


class CreateOrderRequest(APIModel):
    seller_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    warehouse_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    order_number: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
    source: Literal["MANUAL", "CSV", "API", "SHOPIFY"] = "MANUAL"
    items: list[OrderItemRequest] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def reject_duplicate_positions(self):
        positions = [(item.product_id, item.location_id) for item in self.items]
        if len(positions) != len(set(positions)):
            raise ValueError("Duplicate product/location lines must be combined")
        return self


class OrderCommandResponse(CommandResponse):
    order_number: str
    reserved_quantity: int


class OrderListResponse(APIModel):
    id: str
    seller_id: str
    warehouse_id: str
    order_number: str
    source: str
    status: str
    item_count: int
    created_at: str
