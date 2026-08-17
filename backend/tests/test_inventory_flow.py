import os
from uuid import uuid4

import pytest
import pytest_asyncio

if not os.getenv("MONGO_TEST_URI"):
    pytest.skip("Set MONGO_TEST_URI to a MongoDB replica-set URI to run integration tests", allow_module_level=True)

os.environ["MONGODB_URI"] = os.environ["MONGO_TEST_URI"]
os.environ["MONGODB_DATABASE"] = f"whitfield_wms_test_{uuid4().hex}"

from commons.exceptions import InsufficientStockError
from core.apis.schemas.orders import CreateOrderRequest, OrderItemRequest
from core.apis.schemas.receiving import CreateReceiptRequest, ReceiveScanRequest
from core.apis.schemas.setup import CreateLocationRequest, CreateProductRequest, CreateSellerRequest, CreateWarehouseRequest
from core.controllers import fulfillment_controller, receiving_controller, setup_controller
from core.database import close_mongo_connection, connect_to_mongo, create_indexes, get_database


@pytest_asyncio.fixture(autouse=True)
async def mongo_database():
    await connect_to_mongo()
    await create_indexes()
    yield
    await get_database().client.drop_database(get_database().name)
    await close_mongo_connection()


@pytest.mark.asyncio
async def test_duplicate_receipt_is_idempotent_and_oversell_is_rejected():
    organization = await setup_controller.create_organization("Whitfield Fulfillment")
    organization_id = organization["_id"]
    seller = await setup_controller.create_seller(organization_id, CreateSellerRequest(name="Seller A", code="SELLER_A"))
    warehouse = await setup_controller.create_warehouse(organization_id, CreateWarehouseRequest(name="Reno", code="RENO", city="Reno", state="Nevada"))
    location = await setup_controller.create_location(organization_id, CreateLocationRequest(warehouse_id=warehouse["_id"], name="A-01", code="A-01"))
    product = await setup_controller.create_product(organization_id, CreateProductRequest(seller_id=seller["_id"], sku="RED-001", name="Red Product", barcode="012345678905"))

    receipt = await receiving_controller.create_receipt(organization_id, CreateReceiptRequest(seller_id=seller["_id"], warehouse_id=warehouse["_id"], reference_type="MANUAL_TICKET", reference_value="TICKET-1"))
    scan = ReceiveScanRequest(product_id=product["_id"], location_id=location["_id"], quantity=20, condition="GOOD")
    first = await receiving_controller.receive_scan(organization_id, "receiver-1", receipt["_id"], scan, "receipt-scan-1")
    duplicate = await receiving_controller.receive_scan(organization_id, "receiver-1", receipt["_id"], scan, "receipt-scan-1")
    assert first == duplicate
    assert (await get_database().inventory_balances.find_one({"stock_status": "RECEIVING"}))["quantity"] == 20
    await receiving_controller.complete_receipt(organization_id, "receiver-1", receipt["_id"], "complete-receipt-1")
    assert (await get_database().inventory_balances.find_one({"stock_status": "AVAILABLE"}))["quantity"] == 20

    nine_units = CreateOrderRequest(seller_id=seller["_id"], warehouse_id=warehouse["_id"], order_number="ORDER-1", items=[OrderItemRequest(product_id=product["_id"], location_id=location["_id"], quantity=9)])
    await fulfillment_controller.create_and_reserve_order(organization_id, "manager-1", nine_units, "order-1")
    twelve_units = CreateOrderRequest(seller_id=seller["_id"], warehouse_id=warehouse["_id"], order_number="ORDER-2", items=[OrderItemRequest(product_id=product["_id"], location_id=location["_id"], quantity=12)])
    with pytest.raises(InsufficientStockError):
        await fulfillment_controller.create_and_reserve_order(organization_id, "manager-1", twelve_units, "order-2")
