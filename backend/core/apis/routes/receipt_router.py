from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from commons.dependencies import get_actor_id, get_idempotency_key, get_organization_id, require_roles
from commons.exceptions import DuplicateCommandError
from core.apis.schemas.common import CommandResponse
from core.apis.schemas.receiving import CreateReceiptRequest, ReceiptCommandResponse, ReceiptListResponse, ReceiptResponse, ReceiveScanRequest
from core.controllers import receiving_controller
from core.database import get_database
from core.realtime import realtime_manager

router = APIRouter()


@router.get("", response_model=list[ReceiptListResponse], dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def list_receipts(organization_id: str = Depends(get_organization_id)):
    receipts = await get_database().inbound_receipts.find({"organization_id": organization_id}).sort("created_at", -1).to_list(length=100)
    return [
        ReceiptListResponse(
            id=item["_id"], seller_id=item["seller_id"], warehouse_id=item["warehouse_id"],
            reference_type=item["reference_type"], reference_value=item["reference_value"],
            status=item["status"], line_count=len(item["lines"]), created_at=item["created_at"].isoformat(),
        )
        for item in receipts
    ]


@router.post("", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("operator", "manager", "admin"))])
async def create_receipt(payload: CreateReceiptRequest, organization_id: str = Depends(get_organization_id)):
    try:
        receipt = await receiving_controller.create_receipt(organization_id, payload)
        await realtime_manager.broadcast(organization_id, "receipt.created", receipt["_id"])
        return ReceiptResponse(id=receipt["_id"], status=receipt["status"], reference_value=receipt["reference_value"], created_at=receipt["created_at"])
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DuplicateCommandError as error:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": str(error)}) from error
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="This inbound receipt already exists") from error


@router.post("/{receipt_id}/scan", response_model=ReceiptCommandResponse, dependencies=[Depends(require_roles("operator", "manager", "admin"))])
async def scan_receipt(
    receipt_id: str,
    payload: ReceiveScanRequest,
    organization_id: str = Depends(get_organization_id),
    actor_id: str = Depends(get_actor_id),
    idempotency_key: str = Depends(get_idempotency_key),
):
    try:
        result = await receiving_controller.receive_scan(organization_id, actor_id, receipt_id, payload, idempotency_key)
        await realtime_manager.broadcast(organization_id, "inventory.received", receipt_id)
        return result
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/{receipt_id}/complete", response_model=CommandResponse, dependencies=[Depends(require_roles("operator", "manager", "admin"))])
async def complete_receipt(
    receipt_id: str,
    organization_id: str = Depends(get_organization_id),
    actor_id: str = Depends(get_actor_id),
    idempotency_key: str = Depends(get_idempotency_key),
):
    try:
        result = await receiving_controller.complete_receipt(organization_id, actor_id, receipt_id, idempotency_key)
        await realtime_manager.broadcast(organization_id, "receipt.completed", receipt_id)
        return result
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateCommandError as error:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": str(error)}) from error
