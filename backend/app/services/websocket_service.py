"""
WebSocket manager and ticket authentication service for SecureVOTE.

Provides real-time broadcasting for election events (VOTE_CAST, AUDIT_EVENT,
DEVICE_STATUS_CHANGED, ELECTION_STATE_CHANGED).

Enforces single-use, short-lived handshake tickets to prevent JWT exposure
in WebSocket connection URLs (spec Phase 4 requirement).
"""

import asyncio
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("securevote.websocket")


class WebSocketManager:
    """Manages WebSocket connections and single-use ticket lifecycle."""

    def __init__(self):
        # Maps websocket -> election_id (None for global subscription)
        self._active_connections: dict[WebSocket, str | None] = {}
        # Maps ticket -> dict(username, role, expires_at)
        self._tickets: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def create_ticket(
        self,
        username: str,
        role: str,
        election_id: str | None = None,
        ttl_seconds: int = 60,
    ) -> str:
        """
        Generate a cryptographically random, single-use ticket.
        Optionally bound to a specific election_id (or None for global scope).
        TTL defaults to 60 seconds.
        """
        self._purge_expired_tickets()
        ticket = secrets.token_urlsafe(32)
        expires_at = time.time() + ttl_seconds
        self._tickets[ticket] = {
            "username": username,
            "role": role,
            "election_id": election_id,
            "expires_at": expires_at,
        }
        return ticket

    def validate_and_consume_ticket(
        self,
        ticket: str | None,
        expected_election_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Validate and consume a ticket upon WebSocket handshake.
        Single-use: immediately deletes the ticket upon validation.
        Enforces strict scope binding:
        - Global endpoint (/api/ws) requires expected_election_id=None and ticket with election_id=None.
        - Scoped endpoint (/api/ws/{election_id}) requires ticket with matching election_id.
        """
        if not ticket:
            return None

        self._purge_expired_tickets()

        # Atomically pop the ticket (single-use)
        ticket_data = self._tickets.pop(ticket, None)
        if not ticket_data:
            return None

        if time.time() > ticket_data["expires_at"]:
            return None

        # Verify scope binding
        ticket_election_id = ticket_data.get("election_id")
        if ticket_election_id != expected_election_id:
            logger.warning(
                "WebSocket ticket scope mismatch: ticket is for '%s', endpoint requires '%s'",
                ticket_election_id or "GLOBAL",
                expected_election_id or "GLOBAL",
            )
            return None

        return ticket_data


    def _purge_expired_tickets(self) -> None:
        """Remove any expired tickets from in-memory cache."""
        now = time.time()
        expired = [t for t, data in self._tickets.items() if now > data["expires_at"]]
        for t in expired:
            self._tickets.pop(t, None)

    async def connect(self, websocket: WebSocket, election_id: str | None = None) -> None:
        """Accept a websocket connection and register it."""
        await websocket.accept()
        async with self._lock:
            self._active_connections[websocket] = election_id
        logger.info(
            "WebSocket connected (election_id=%s). Active count: %d",
            election_id or "ALL",
            len(self._active_connections),
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a websocket connection."""
        async with self._lock:
            self._active_connections.pop(websocket, None)
        logger.info(
            "WebSocket disconnected. Active count: %d", len(self._active_connections)
        )

    async def broadcast(
        self,
        election_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        Broadcast an event to all subscribers interested in election_id
        or globally subscribed.
        """
        message = {
            "event": event_type,
            "election_id": election_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }

        async with self._lock:
            targets = list(self._active_connections.items())

        dead_connections: list[WebSocket] = []
        for ws, sub_election_id in targets:
            if sub_election_id is None or sub_election_id == election_id:
                try:
                    await ws.send_json(message)
                except Exception as exc:
                    logger.warning("Failed to send WebSocket message: %s", exc)
                    dead_connections.append(ws)

        if dead_connections:
            async with self._lock:
                for dead in dead_connections:
                    self._active_connections.pop(dead, None)


# Global singleton instance
websocket_manager = WebSocketManager()
