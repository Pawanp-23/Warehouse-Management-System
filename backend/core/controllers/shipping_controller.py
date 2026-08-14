from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from core.config import settings
from core.cruds.inventory_crud import increment_balance, inventory_position_filter
from core.database import get_client, get_database


async def create_shipment(organization_id: str, actor_id: str, payload) -> dict:
    db, client = get_database(), get_client()
    shipment_id = str(uuid4())
    async def transaction(session):
        order = await db.orders.find_one({"_id": payload.order_id, "organization_id": organization_id}, session=session)
        if not order: raise ValueError("Order not found")
        if order["status"] != "RESERVED": raise ValueError("Only reserved orders can be shipped")
        now = datetime.now(timezone.utc)
        for reservation in order["reservations"]:
            position = inventory_position_filter(organization_id=organization_id, seller_id=order["seller_id"],
                product_id=reservation["product_id"], warehouse_id=order["warehouse_id"],
                location_id=reservation["location_id"], stock_status="RESERVED")
            result = await db.inventory_balances.update_one({**position, "quantity": {"$gte": reservation["quantity"]}},
                {"$inc": {"quantity": -reservation["quantity"]}, "$set": {"updated_at": now}}, session=session)
            if not result.modified_count: raise ValueError("Reserved inventory is inconsistent")
            await db.inventory_reservations.update_one({"_id": reservation["reservation_id"]}, {"$set": {"status": "SHIPPED", "updated_at": now}}, session=session)
            await db.inventory_movements.insert_one({"_id": str(uuid4()), **position, "movement_type": "SHIP",
                "quantity": -reservation["quantity"], "to_stock_status": "OUTBOUND", "reference_type": "SHIPMENT",
                "reference_id": shipment_id, "actor_id": actor_id, "created_at": now}, session=session)
        event = {"status": "LABEL_CREATED", "location": None, "note": "Shipment created", "occurred_at": now}
        shipment = {"_id": shipment_id, "organization_id": organization_id, "order_id": order["_id"],
            "order_number": order["order_number"], "carrier_id": payload.carrier_id.upper(), "carrier_name": payload.carrier_name,
            "service_level": payload.service_level, "tracking_number": payload.tracking_number.upper(), "status": "LABEL_CREATED",
            "ship_to": payload.ship_to.model_dump(), "events": [event], "created_at": now, "updated_at": now}
        await db.shipments.insert_one(shipment, session=session)
        await db.orders.update_one({"_id": order["_id"]}, {"$set": {"status": "SHIPPED", "shipment_id": shipment_id, "updated_at": now}}, session=session)
        return shipment
    async with client.start_session() as session:
        return await session.with_transaction(transaction, read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority"))


async def update_tracking(organization_id: str, shipment_id: str, payload) -> dict | None:
    now = datetime.now(timezone.utc)
    event = {"status": payload.status, "location": payload.location, "note": payload.note, "occurred_at": now}
    shipment = await get_database().shipments.find_one_and_update({"_id": shipment_id, "organization_id": organization_id},
        {"$set": {"status": payload.status, "updated_at": now}, "$push": {"events": event}}, return_document=True)
    if shipment and payload.status == "DELIVERED":
        await get_database().orders.update_one({"_id": shipment["order_id"], "organization_id": organization_id}, {"$set": {"status": "DELIVERED", "updated_at": now}})
    return shipment


async def create_invoice(organization_id: str, payload) -> dict:
    db = get_database()
    order = await db.orders.find_one({"_id": payload.order_id, "organization_id": organization_id})
    if not order: raise ValueError("Order not found")
    if await db.invoices.find_one({"organization_id": organization_id, "order_id": order["_id"]}): raise ValueError("Order already has an invoice")
    now = datetime.now(timezone.utc)
    invoice = {"_id": str(uuid4()), "organization_id": organization_id, "invoice_number": f"INV-{now:%Y%m%d}-{str(uuid4())[:6].upper()}",
        "order_id": order["_id"], "order_number": order["order_number"], "subtotal_cents": payload.subtotal_cents,
        "tax_cents": payload.tax_cents, "total_cents": payload.subtotal_cents + payload.tax_cents, "currency": payload.currency,
        "status": "OPEN", "due_at": now + timedelta(days=payload.due_days), "created_at": now, "updated_at": now}
    await db.invoices.insert_one(invoice)
    return invoice


async def create_payment_intent(organization_id: str, invoice_id: str) -> dict:
    db = get_database()
    invoice = await db.invoices.find_one({"_id": invoice_id, "organization_id": organization_id})
    if not invoice: raise ValueError("Invoice not found")
    if invoice["status"] == "PAID": raise ValueError("Invoice is already paid")
    existing = await db.payments.find_one({"organization_id": organization_id, "invoice_id": invoice_id, "status": {"$nin": ["FAILED", "CANCELED"]}})
    if existing: return existing
    provider, provider_id, client_secret, payment_status = "unconfigured", None, None, "GATEWAY_NOT_CONFIGURED"
    if settings.stripe_secret_key:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post("https://api.stripe.com/v1/payment_intents", auth=(settings.stripe_secret_key, ""),
                headers={"Idempotency-Key": f"invoice-{invoice_id}"}, data={"amount": invoice["total_cents"], "currency": invoice["currency"],
                "metadata[invoice_id]": invoice_id, "metadata[organization_id]": organization_id, "automatic_payment_methods[enabled]": "true"})
            response.raise_for_status(); intent = response.json()
        provider, provider_id, client_secret, payment_status = "stripe", intent["id"], intent.get("client_secret"), intent["status"].upper()
    now = datetime.now(timezone.utc)
    payment = {"_id": str(uuid4()), "organization_id": organization_id, "invoice_id": invoice_id, "provider": provider,
        "provider_payment_id": provider_id, "amount_cents": invoice["total_cents"], "currency": invoice["currency"],
        "status": payment_status, "client_secret": client_secret, "created_at": now, "updated_at": now}
    await db.payments.insert_one(payment)
    return payment
