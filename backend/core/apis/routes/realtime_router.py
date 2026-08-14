from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from commons.dependencies import IDENTIFIER_PATTERN
from core.config import settings
from core.realtime import realtime_manager
from core.security import decode_access_token

router = APIRouter()


@router.websocket("/ws/{organization_id}")
async def warehouse_events(websocket: WebSocket, organization_id: str):
    if not IDENTIFIER_PATTERN.fullmatch(organization_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid organization")
        return

    selected_protocol = None
    if settings.auth_required:
        protocols = [item.strip() for item in websocket.headers.get("sec-websocket-protocol", "").split(",") if item.strip()]
        if len(protocols) != 2 or protocols[0] != "whitfield-auth":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
            return
        try:
            context = decode_access_token(protocols[1])
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            return
        if context.organization_id != organization_id or not context.roles.intersection({"viewer", "operator", "manager", "admin"}):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access denied")
            return
        selected_protocol = "whitfield-auth"

    await realtime_manager.connect(organization_id, websocket, selected_protocol)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_manager.disconnect(organization_id, websocket)
