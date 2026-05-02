import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("geotrade.ws")

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected. Active connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket disconnected. Active connections: %d", len(self.active_connections))

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
            
        data = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.error("Error broadcasting to WebSocket: %s", e)
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/live-risk")
async def live_risk_feed(websocket: WebSocket):
    """
    WebSocket endpoint for real-time risk updates (e.g., for the Globe UI).
    Clients connect here, and the backend pushes `{type: "RISK_UPDATE", data: ...}`
    events when background syncs finish.
    """
    await manager.connect(websocket)
    try:
        # Keep connection alive
        while True:
            # We don't expect client messages, just heartbeat pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
