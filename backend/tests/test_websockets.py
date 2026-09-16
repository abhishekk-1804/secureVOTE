"""
Test WebSocket event streaming, single-use handshake ticket authentication,
and strict scope binding.

Verifies:
1. POST /api/auth/ws-ticket generates a short-lived ticket (global or election-scoped).
2. WebSocket handshake without ticket or with invalid ticket is rejected (code 1008).
3. Ticket is strictly single-use: subsequent handshake with the same ticket is rejected.
4. Scope Binding:
   - Ticket for election A cannot authenticate to election B.
   - Valid ticket for election A connects to election A.
   - Global ticket cannot be used as an election-scoped ticket.
   - Election-scoped ticket cannot be used on the global /api/ws endpoint.
5. Real-time broadcast receives events on connected sockets.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.services.websocket_service import websocket_manager


@pytest.mark.asyncio
async def test_ws_ticket_generation(client: AsyncClient, admin_token: str):
    """Test generating single-use WebSocket handshake tickets (global and scoped)."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Unauthenticated request rejected
    unauth_res = await client.post("/api/auth/ws-ticket")
    assert unauth_res.status_code == 401

    # 2. Global ticket generation (no body)
    auth_res = await client.post("/api/auth/ws-ticket", headers=headers)
    assert auth_res.status_code == 200
    data = auth_res.json()
    assert "ticket" in data
    assert data["expires_in"] == 60
    assert data["election_id"] is None
    assert len(data["ticket"]) > 20

    # 3. Election-scoped ticket generation
    scoped_res = await client.post(
        "/api/auth/ws-ticket",
        json={"election_id": "EV-2026-701"},
        headers=headers,
    )
    assert scoped_res.status_code == 200
    scoped_data = scoped_res.json()
    assert "ticket" in scoped_data
    assert scoped_data["election_id"] == "EV-2026-701"


def test_ws_connection_and_single_use_ticket():
    """
    Test WebSocket handshake with TestClient:
    - Missing ticket -> 1008
    - Invalid ticket -> 1008
    - Valid ticket -> connects
    - Reuse ticket -> 1008 (single-use enforced!)
    """
    with TestClient(app) as test_client:
        # 1. Connect without ticket
        with pytest.raises(Exception):
            with test_client.websocket_connect("/api/ws") as ws:
                pass

        # 2. Connect with bogus ticket
        with pytest.raises(Exception):
            with test_client.websocket_connect("/api/ws?ticket=invalid-ticket-12345") as ws:
                pass

        # 3. Generate valid global ticket
        ticket = websocket_manager.create_ticket(
            username="test_admin", role="ADMIN", election_id=None, ttl_seconds=60
        )

        # 4. Connect with valid global ticket
        with test_client.websocket_connect(f"/api/ws?ticket={ticket}") as ws:
            msg = ws.receive_json()
            assert msg["event"] == "CONNECTED"
            assert msg["user"] == "test_admin"
            assert msg["role"] == "ADMIN"

            # Ping/pong test
            ws.send_text("ping")
            reply = ws.receive_text()
            assert reply == "pong"

        # 5. Reuse same ticket -> MUST fail because ticket was consumed (single-use)
        with pytest.raises(Exception):
            with test_client.websocket_connect(f"/api/ws?ticket={ticket}") as ws:
                pass


def test_ws_ticket_scope_binding_and_isolation():
    """
    Test strict scope binding:
    - Ticket for Election A cannot authenticate to Election B.
    - Valid ticket for Election A connects to Election A.
    - Single-use behavior holds (consumed ticket cannot reconnect to Election A).
    - Global ticket cannot be used as an election-scoped ticket.
    - Election-scoped ticket cannot be used on the global endpoint.
    """
    election_a = "EV-2026-702"
    election_b = "EV-2026-703"

    with TestClient(app) as test_client:
        # 1. Issue ticket scoped strictly to Election A
        ticket_a = websocket_manager.create_ticket(
            username="auditor_user", role="AUDITOR", election_id=election_a, ttl_seconds=60
        )

        # 2. Attempt to use Election A ticket on Election B -> MUST be rejected (1008)
        with pytest.raises(Exception):
            with test_client.websocket_connect(f"/api/ws/{election_b}?ticket={ticket_a}") as ws:
                pass

        # 3. Single-use: ticket_a was consumed upon the failed handshake above!
        # Attempting to use ticket_a on Election A now must fail
        with pytest.raises(Exception):
            with test_client.websocket_connect(f"/api/ws/{election_a}?ticket={ticket_a}") as ws:
                pass

        # 4. Issue a fresh ticket for Election A and connect to Election A -> MUST succeed
        fresh_ticket_a = websocket_manager.create_ticket(
            username="auditor_user", role="AUDITOR", election_id=election_a, ttl_seconds=60
        )
        with test_client.websocket_connect(f"/api/ws/{election_a}?ticket={fresh_ticket_a}") as ws:
            msg = ws.receive_json()
            assert msg["event"] == "CONNECTED"
            assert msg["election_id"] == election_a

        # 5. Single-use check: fresh_ticket_a cannot be reused on Election A
        with pytest.raises(Exception):
            with test_client.websocket_connect(f"/api/ws/{election_a}?ticket={fresh_ticket_a}") as ws:
                pass

        # 6. Global ticket CANNOT authenticate to an election-scoped stream
        global_ticket = websocket_manager.create_ticket(
            username="admin_user", role="ADMIN", election_id=None, ttl_seconds=60
        )
        with pytest.raises(Exception):
            with test_client.websocket_connect(f"/api/ws/{election_a}?ticket={global_ticket}") as ws:
                pass

        # 7. Election-scoped ticket CANNOT authenticate to the global stream
        scoped_ticket = websocket_manager.create_ticket(
            username="admin_user", role="ADMIN", election_id=election_a, ttl_seconds=60
        )
        with pytest.raises(Exception):
            with test_client.websocket_connect(f"/api/ws?ticket={scoped_ticket}") as ws:
                pass


@pytest.mark.asyncio
async def test_ws_event_broadcasting(client: AsyncClient, admin_token: str):
    """Test broadcasting events to connected WebSocket clients."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    election_id = "EV-2026-701"

    # Create election
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": "WS Test Election"},
        headers=headers,
    )
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Cand A", "position": 1},
                {"id": "C002", "name": "Cand B", "position": 2},
            ]
        },
        headers=headers,
    )

    # Issue scoped ticket for election_id
    ticket = websocket_manager.create_ticket(
        username="admin", role="ADMIN", election_id=election_id, ttl_seconds=60
    )

    with TestClient(app) as test_client:
        with test_client.websocket_connect(f"/api/ws/{election_id}?ticket={ticket}") as ws:
            init_msg = ws.receive_json()
            assert init_msg["event"] == "CONNECTED"
            assert init_msg["election_id"] == election_id

            # Directly broadcast an event to verify delivery over the connection
            await websocket_manager.broadcast(
                election_id=election_id,
                event_type="TEST_BROADCAST",
                data={"status": "live"},
            )

            event = ws.receive_json()
            assert event["event"] == "TEST_BROADCAST"
            assert event["election_id"] == election_id
            assert event["data"]["status"] == "live"
