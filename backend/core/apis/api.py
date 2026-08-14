from fastapi import APIRouter

from core.apis.routes import assistant_router, auth_router, health_router, inventory_router, knowledge_router, order_router, receipt_router, realtime_router, setup_router, shipping_router

api_router = APIRouter()
api_router.include_router(health_router.router, tags=["health"])
api_router.include_router(auth_router.router, prefix="/auth", tags=["authentication"])
api_router.include_router(setup_router.router, prefix="/setup", tags=["setup"])
api_router.include_router(receipt_router.router, prefix="/inbound-receipts", tags=["receiving"])
api_router.include_router(inventory_router.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(order_router.router, prefix="/orders", tags=["orders"])
api_router.include_router(realtime_router.router, tags=["realtime"])
api_router.include_router(shipping_router.router, tags=["shipping-and-billing"])
api_router.include_router(knowledge_router.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(assistant_router.router, prefix="/assistant", tags=["assistant"])
