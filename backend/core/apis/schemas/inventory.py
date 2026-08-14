from datetime import datetime

from core.apis.schemas.common import APIModel


class InventoryBalanceResponse(APIModel):
    product_id: str
    seller_id: str
    warehouse_id: str
    location_id: str
    stock_status: str
    quantity: int
    updated_at: datetime
