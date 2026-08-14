from pydantic import Field

from core.apis.schemas.common import APIModel, CreatedResource


class CreateOrganizationRequest(APIModel):
    name: str = Field(min_length=2, max_length=120, pattern=r"^[^\x00-\x1f\x7f]+$")


class CreateSellerRequest(APIModel):
    name: str = Field(min_length=2, max_length=120, pattern=r"^[^\x00-\x1f\x7f]+$")
    code: str = Field(pattern=r"^[A-Z0-9_-]{2,20}$")


class CreateWarehouseRequest(APIModel):
    name: str = Field(min_length=2, max_length=120, pattern=r"^[^\x00-\x1f\x7f]+$")
    code: str = Field(pattern=r"^[A-Z0-9_-]{2,20}$")
    city: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z .'-]+$")
    state: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z .'-]+$")


class CreateLocationRequest(APIModel):
    warehouse_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    code: str = Field(pattern=r"^[A-Z0-9_-]{2,40}$")
    name: str = Field(min_length=2, max_length=120, pattern=r"^[^\x00-\x1f\x7f]+$")


class CreateProductRequest(APIModel):
    seller_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    sku: str = Field(pattern=r"^[A-Z0-9_-]{2,60}$")
    name: str = Field(min_length=2, max_length=200, pattern=r"^[^\x00-\x1f\x7f]+$")
    barcode: str = Field(min_length=4, max_length=128, pattern=r"^[A-Za-z0-9._:/+-]+$")


class SetupResource(CreatedResource):
    name: str


class SellerResource(SetupResource):
    code: str


class WarehouseResource(SetupResource):
    code: str
    city: str
    state: str


class LocationResource(SetupResource):
    warehouse_id: str
    code: str


class ProductResource(SetupResource):
    seller_id: str
    sku: str
    barcode: str
