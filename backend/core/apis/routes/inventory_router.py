from fastapi import APIRouter, Depends

from commons.dependencies import get_organization_id, require_roles
from core.apis.schemas.inventory import InventoryBalanceResponse
from core.database import get_database

router = APIRouter()


@router.get("", response_model=list[InventoryBalanceResponse], dependencies=[Depends(require_roles("viewer", "operator", "manager", "admin"))])
async def list_inventory(organization_id: str = Depends(get_organization_id), warehouse_id: str | None = None):
    query = {"organization_id": organization_id}
    if warehouse_id:
        query["warehouse_id"] = warehouse_id
    projection = {"_id": 0, "organization_id": 0, "created_at": 0}
    cursor = get_database().inventory_balances.find(query, projection).sort("updated_at", -1)
    balances = await cursor.to_list(length=100)
    return [InventoryBalanceResponse(**balance) for balance in balances]
