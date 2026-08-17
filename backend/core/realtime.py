from collections import defaultdict

from fastapi import WebSocket


class RealtimeManager:
    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, organization_id: str, websocket: WebSocket, subprotocol: str | None = None) -> None:
        await websocket.accept(subprotocol=subprotocol)
        self.connections[organization_id].add(websocket)

    def disconnect(self, organization_id: str, websocket: WebSocket) -> None:
        self.connections[organization_id].discard(websocket)
        if not self.connections[organization_id]:
            self.connections.pop(organization_id, None)

    async def broadcast(self, organization_id: str, event_type: str, entity_id: str) -> None:
        stale_connections: list[WebSocket] = []
        for websocket in self.connections.get(organization_id, set()).copy():
            try:
                await websocket.send_json({"type": event_type, "entity_id": entity_id})
            except Exception:
                stale_connections.append(websocket)
        for websocket in stale_connections:
            self.disconnect(organization_id, websocket)


realtime_manager = RealtimeManager()
