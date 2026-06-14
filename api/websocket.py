from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


class WebsocketHub:
    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections = [item for item in self.connections if item is not websocket]

    async def broadcast(self, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for websocket in self.connections:
            try:
                await websocket.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)

