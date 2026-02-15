"""
WebSocket Connection Manager.
Tracks active WebSocket connections per session and broadcasts events.
"""
import json
from typing import Dict, List
from fastapi import WebSocket
from datetime import datetime, timezone


class ConnectionManager:
    """Manages WebSocket connections grouped by session_id."""

    def __init__(self):
        # session_id -> list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept a new WebSocket and register it under the session."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        """Remove a WebSocket when the client disconnects."""
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, event_type: str, payload: dict):
        """
        Broadcast a WebSocket event to all connections for a given session.

        event_type: "SCAM_STATUS_UPDATE" | "STALL_MESSAGE" | "ERROR" | "ACK"
        payload:    The model-dumped dict for the specific event payload.
        """
        message = json.dumps({
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        })

        connections = self.active_connections.get(session_id, [])
        dead: List[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        for ws in dead:
            self.disconnect(session_id, ws)


# Singleton instance used across the app
manager = ConnectionManager()
