from fastapi import APIRouter

from core.database import get_database

router = APIRouter()


@router.get("/health")
async def readiness_check():
    await get_database().command("ping")
    return {"status": "ok", "service": "whitfield-wms-api"}


@router.get("/live")
async def liveness_check():
    return {"status": "ok"}
