from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from commons.dependencies import get_organization_id, require_roles
from core.apis.schemas.setup import (
    CreateLocationRequest,
    CreateOrganizationRequest,
    CreateProductRequest,
    CreateSellerRequest,
    CreateWarehouseRequest,
    LocationResource,
    ProductResource,
    SellerResource,
    SetupResource,
    WarehouseResource,
)
from core.controllers import setup_controller
from core.database import get_database
from core.realtime import realtime_manager

router = APIRouter()


def response_from(document: dict) -> SetupResource:
    return SetupResource(id=document["_id"], name=document["name"], created_at=document["created_at"])


@router.get("/sellers", response_model=list[SellerResource], dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def list_sellers(organization_id: str = Depends(get_organization_id)):
    sellers = await get_database().sellers.find({"organization_id": organization_id}).sort("name", 1).to_list(length=200)
    return [SellerResource(id=item["_id"], name=item["name"], code=item["code"], created_at=item["created_at"]) for item in sellers]


@router.get("/warehouses", response_model=list[WarehouseResource], dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def list_warehouses(organization_id: str = Depends(get_organization_id)):
    warehouses = await get_database().warehouses.find({"organization_id": organization_id}).sort("name", 1).to_list(length=200)
    return [WarehouseResource(id=item["_id"], name=item["name"], code=item["code"], city=item["city"], state=item["state"], created_at=item["created_at"]) for item in warehouses]


@router.get("/locations", response_model=list[LocationResource], dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def list_locations(organization_id: str = Depends(get_organization_id), warehouse_id: str | None = None):
    query = {"organization_id": organization_id}
    if warehouse_id:
        query["warehouse_id"] = warehouse_id
    locations = await get_database().locations.find(query).sort("code", 1).to_list(length=1000)
    return [LocationResource(id=item["_id"], name=item["name"], warehouse_id=item["warehouse_id"], code=item["code"], created_at=item["created_at"]) for item in locations]


@router.get("/products", response_model=list[ProductResource], dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def list_products(organization_id: str = Depends(get_organization_id), seller_id: str | None = None):
    query = {"organization_id": organization_id}
    if seller_id:
        query["seller_id"] = seller_id
    products = await get_database().products.find(query).sort("name", 1).to_list(length=1000)
    return [ProductResource(id=item["_id"], name=item["name"], seller_id=item["seller_id"], sku=item["sku"], barcode=next(iter(item.get("barcodes") or []), None), created_at=item["created_at"]) for item in products]


@router.post("/organizations", response_model=SetupResource, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("platform_admin"))])
async def create_organization(payload: CreateOrganizationRequest):
    try:
        return response_from(await setup_controller.create_organization(payload.name))
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="Organization name already exists") from error


@router.post("/sellers", response_model=SetupResource, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin", "manager"))])
async def create_seller(payload: CreateSellerRequest, organization_id: str = Depends(get_organization_id)):
    try:
        seller = await setup_controller.create_seller(organization_id, payload)
        await realtime_manager.broadcast(organization_id, "seller.created", seller["_id"])
        return response_from(seller)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="Seller code already exists") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/warehouses", response_model=SetupResource, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin", "manager"))])
async def create_warehouse(payload: CreateWarehouseRequest, organization_id: str = Depends(get_organization_id)):
    try:
        warehouse = await setup_controller.create_warehouse(organization_id, payload)
        await realtime_manager.broadcast(organization_id, "warehouse.created", warehouse["_id"])
        return response_from(warehouse)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="Warehouse code already exists") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/locations", response_model=SetupResource, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin", "manager"))])
async def create_location(payload: CreateLocationRequest, organization_id: str = Depends(get_organization_id)):
    try:
        location = await setup_controller.create_location(organization_id, payload)
        await realtime_manager.broadcast(organization_id, "location.created", location["_id"])
        return response_from(location)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="Location code already exists in this warehouse") from error


@router.post("/products", response_model=SetupResource, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin", "manager"))])
async def create_product(payload: CreateProductRequest, organization_id: str = Depends(get_organization_id)):
    try:
        product = await setup_controller.create_product(organization_id, payload)
        await realtime_manager.broadcast(organization_id, "product.created", product["_id"])
        return response_from(product)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="SKU already exists for this seller") from error
