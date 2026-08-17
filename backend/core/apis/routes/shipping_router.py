from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from commons.dependencies import get_actor_id, get_organization_id, require_roles
from core.apis.schemas.shipping import CreateInvoiceRequest, CreateShipmentRequest, InvoiceResource, PaymentIntentResource, ShipmentResource, TrackingUpdateRequest
from core.controllers import shipping_controller
from core.database import get_database
from core.realtime import realtime_manager

router = APIRouter()

def shipment_resource(item): return ShipmentResource(id=item["_id"], **{key: item[key] for key in ("order_id","order_number","carrier_id","carrier_name","service_level","tracking_number","status","ship_to","events","created_at")})
def invoice_resource(item): return InvoiceResource(id=item["_id"], **{key: item[key] for key in ("invoice_number","order_id","order_number","subtotal_cents","tax_cents","total_cents","currency","status","due_at","created_at")})
def payment_resource(item): return PaymentIntentResource(id=item["_id"], **{key: item.get(key) for key in ("invoice_id","provider","provider_payment_id","amount_cents","currency","status","client_secret","created_at")})

@router.get("/shipments", response_model=list[ShipmentResource], dependencies=[Depends(require_roles("viewer","operator","manager","admin"))])
async def shipments(organization_id: str = Depends(get_organization_id)):
    return [shipment_resource(item) for item in await get_database().shipments.find({"organization_id": organization_id}).sort("created_at",-1).to_list(length=500)]

@router.post("/shipments", response_model=ShipmentResource, status_code=201, dependencies=[Depends(require_roles("operator","manager","admin"))])
async def create_shipment(payload: CreateShipmentRequest, organization_id: str = Depends(get_organization_id), actor_id: str = Depends(get_actor_id)):
    try: item = await shipping_controller.create_shipment(organization_id, actor_id, payload)
    except (ValueError, DuplicateKeyError) as error: raise HTTPException(409, str(error)) from error
    await realtime_manager.broadcast(organization_id, "shipment.created", item["_id"]); return shipment_resource(item)

@router.post("/shipments/{shipment_id}/events", response_model=ShipmentResource, dependencies=[Depends(require_roles("operator","manager","admin"))])
async def tracking(shipment_id: str, payload: TrackingUpdateRequest, organization_id: str = Depends(get_organization_id)):
    item = await shipping_controller.update_tracking(organization_id, shipment_id, payload)
    if not item: raise HTTPException(404, "Shipment not found")
    await realtime_manager.broadcast(organization_id, "shipment.updated", shipment_id); return shipment_resource(item)

@router.get("/invoices", response_model=list[InvoiceResource], dependencies=[Depends(require_roles("manager","admin"))])
async def invoices(organization_id: str = Depends(get_organization_id)):
    return [invoice_resource(item) for item in await get_database().invoices.find({"organization_id": organization_id}).sort("created_at",-1).to_list(length=500)]

@router.post("/invoices", response_model=InvoiceResource, status_code=201, dependencies=[Depends(require_roles("manager","admin"))])
async def create_invoice(payload: CreateInvoiceRequest, organization_id: str = Depends(get_organization_id)):
    try:
        item = await shipping_controller.create_invoice(organization_id, payload)
        await realtime_manager.broadcast(organization_id, "invoice.created", item["_id"])
        return invoice_resource(item)
    except ValueError as error: raise HTTPException(409, str(error)) from error

@router.get("/payments", response_model=list[PaymentIntentResource], dependencies=[Depends(require_roles("manager","admin"))])
async def payments(organization_id: str = Depends(get_organization_id)):
    return [payment_resource(item) for item in await get_database().payments.find({"organization_id": organization_id}).sort("created_at",-1).to_list(length=500)]

@router.post("/invoices/{invoice_id}/payment-intent", response_model=PaymentIntentResource, dependencies=[Depends(require_roles("manager","admin"))])
async def payment_intent(invoice_id: str, organization_id: str = Depends(get_organization_id)):
    try:
        item = await shipping_controller.create_payment_intent(organization_id, invoice_id)
        await realtime_manager.broadcast(organization_id, "payment.updated", item["_id"])
        return payment_resource(item)
    except ValueError as error: raise HTTPException(409, str(error)) from error
