from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from commons.dependencies import get_actor_id, get_idempotency_key, get_organization_id, require_roles
from commons.exceptions import DuplicateCommandError, InsufficientStockError
from core.apis.schemas.orders import CreateOrderRequest, OrderCommandResponse, OrderListResponse
from core.controllers import fulfillment_controller
from core.database import get_database
from core.realtime import realtime_manager

router = APIRouter()


@router.get("", response_model=list[OrderListResponse], dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def list_orders(organization_id: str = Depends(get_organization_id)):
    orders = await get_database().orders.find({"organization_id": organization_id}).sort("created_at", -1).to_list(length=100)
    return [
        OrderListResponse(
            id=item["_id"], seller_id=item["seller_id"], warehouse_id=item["warehouse_id"],
            order_number=item["order_number"], source=item["source"], status=item["status"],
            item_count=len(item["items"]), created_at=item["created_at"].isoformat(),
        )
        for item in orders
    ]


@router.post("", response_model=OrderCommandResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("operator", "manager", "admin"))])
async def create_order(
    payload: CreateOrderRequest,
    organization_id: str = Depends(get_organization_id),
    actor_id: str = Depends(get_actor_id),
    idempotency_key: str = Depends(get_idempotency_key),
):
    try:
        result = await fulfillment_controller.create_and_reserve_order(organization_id, actor_id, payload, idempotency_key)
        await realtime_manager.broadcast(organization_id, "order.reserved", result["id"])
        return result
    except InsufficientStockError as error:
        raise HTTPException(status_code=409, detail={"code": "INSUFFICIENT_STOCK", "available_quantity": error.available_quantity, "requested_quantity": error.requested_quantity}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="Order number already exists or duplicate command") from error
    except DuplicateCommandError as error:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": str(error)}) from error
