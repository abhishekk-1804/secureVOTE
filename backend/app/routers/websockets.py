"""
WebSocket router for SecureVOTE real-time event broadcasting.

Clients connect to receive live updates on votes, audit entries, device status,
and election state changes.

Authentication requires a single-use handshake ticket obtained via
POST /api/auth/ws-ticket. Connections without a valid ticket are rejected (1008).
"""

import logging
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.websocket_service import websocket_manager

logger = logging.getLogger("securevote.websockets")

router = APIRouter(tags=["websockets"])


@router.websocket("/api/ws")
async def websocket_global_endpoint(
    websocket: WebSocket,
    ticket: str | None = Query(default=None),
):
    """Global WebSocket endpoint for all election events."""
    await handle_websocket_connection(websocket, ticket=ticket, election_id=None)


@router.websocket("/api/ws/{election_id}")
async def websocket_election_endpoint(
    websocket: WebSocket,
    election_id: str,
    ticket: str | None = Query(default=None),
):
    """Scoped WebSocket endpoint for a specific election's events."""
    await handle_websocket_connection(websocket, ticket=ticket, election_id=election_id)


async def handle_websocket_connection(
    websocket: WebSocket,
    ticket: str | None,
    election_id: str | None,
):
    """Validate ticket and manage the active connection loop."""
    ticket_data = websocket_manager.validate_and_consume_ticket(
        ticket, expected_election_id=election_id
    )
    if not ticket_data:
        logger.warning(
            "Rejected WebSocket connection: missing, expired, or out-of-scope ticket for scope=%s.",
            election_id or "GLOBAL",
        )
        # Reject connection before or during handshake
        await websocket.close(
            code=1008, reason="Authentication required: invalid, expired, or out-of-scope ticket"
        )
        return


    await websocket_manager.connect(websocket, election_id=election_id)
    try:
        # Send initial confirmation message
        await websocket.send_json({
            "event": "CONNECTED",
            "election_id": election_id,
            "user": ticket_data["username"],
            "role": ticket_data["role"],
        })

        # Keep connection open until client disconnects or sends text
        while True:
            # Client can send ping / heartbeat
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
        await websocket_manager.disconnect(websocket)
