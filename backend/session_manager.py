"""
Async Session Manager.
Handles session CRUD via SQLite (through SQLModel) and
broadcasts real-time events over WebSocket.
"""
import json
import httpx
from datetime import datetime, timezone
from typing import Optional

from backend.models import (
    SessionState, IncomingRequest, ExtractedIntelligence,
    ScamStatusPayload, StallMessagePayload,
)
from backend.connection_manager import manager as ws_manager


class SessionManager:
    """
    Manages session lifecycle and event broadcasting.

    Sessions are kept in-memory (dict) and are also serialised to SQLite
    via the /db helpers so they survive restarts.  The in-memory dict is
    the primary working copy for speed.
    """

    def __init__(self):
        self.memory_store: dict[str, SessionState] = {}

    # ── CRUD ───────────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self.memory_store.get(session_id)

    def create_session(self, request: IncomingRequest) -> SessionState:
        if request.metadata is None:
            meta = {}
        elif isinstance(request.metadata, dict):
            meta = request.metadata
        else:
            meta = request.metadata.model_dump()

        session = SessionState(
            session_id=request.sessionId,
            metadata=meta,
            conversation_history=[],
            start_time=datetime.now(timezone.utc),
        )
        self.memory_store[session.session_id] = session
        return session

    def save_session(self, session: SessionState):
        session.last_active = datetime.now(timezone.utc)
        self.memory_store[session.session_id] = session

    def update_session(self, session: SessionState, scammer_msg: str, agent_msg: str):
        session.message_count += 1
        now = str(datetime.now(timezone.utc))
        session.conversation_history.append(
            {"sender": "scammer", "text": scammer_msg, "timestamp": now}
        )
        session.conversation_history.append(
            {"sender": "agent", "text": agent_msg, "timestamp": now}
        )
        session.scammer_patience = self._calculate_patience_decay(session, agent_msg)
        self.save_session(session)

    # ── WebSocket Broadcasting ─────────────────────────────────────────────

    async def broadcast_scam_status(
        self,
        session_id: str,
        is_scam: bool,
        confidence: float,
        scam_type: str,
    ):
        """
        Response Type 1 — Scam Status Update.
        Pushed immediately after detection so the app can update its color dot.
        """
        if confidence >= 50:
            severity, color = "SCAM", "red"
        elif confidence >= 22:
            severity, color = "SUSPICIOUS", "yellow"
        else:
            severity, color = "SAFE", "green"

        payload = ScamStatusPayload(
            is_scam=is_scam,
            confidence=confidence,
            severity=severity,
            scam_type=scam_type if is_scam else None,
            ui_color=color,
        )
        await ws_manager.broadcast(
            session_id, "SCAM_STATUS_UPDATE", payload.model_dump()
        )

    async def broadcast_stall_message(
        self,
        session_id: str,
        message_body: str,
        delay: float,
        phase: str,
    ):
        """
        Response Type 2 — Stall Message.
        Pushed after response generation so the app can relay the reply.
        """
        payload = StallMessagePayload(
            message_body=message_body,
            suggested_delay=delay,
            phase=phase,
        )
        await ws_manager.broadcast(
            session_id, "STALL_MESSAGE", payload.model_dump()
        )

    # ── Patience Decay ─────────────────────────────────────────────────────

    def _calculate_patience_decay(self, session: SessionState, agent_msg: str) -> float:
        patience = session.scammer_patience
        base_decay = 3.0
        stall_keywords = ["wait", "hold on", "minute", "loading", "slow", "checking", "error"]
        extract_keywords = ["upi", "account", "number", "transfer", "send money"]

        agent_lower = agent_msg.lower()
        if any(kw in agent_lower for kw in stall_keywords):
            base_decay += 5.0
        if any(kw in agent_lower for kw in extract_keywords):
            base_decay -= 8.0
        if session.message_count <= 3:
            base_decay *= 0.5

        return round(max(0.0, patience - base_decay), 2)
