"""
Tests for SecureVOTE election lifecycle state machine.

Validates:
- All permitted transitions:
  CREATED → CONFIGURED → LOCKED → OPEN → SUSPENDED/CLOSED → PUBLISHED
- Terminal state semantics of PUBLISHED:
  PUBLISHED has NO valid outgoing transitions (returns HTTP 409 Conflict)
- Invalid transitions rejection and clean UTF-8 error messages
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_lifecycle_and_terminal_published_state(client: AsyncClient, admin_headers: dict):
    election_id = "EV-2026-091"

    # 1. Create election (CREATED)
    resp = await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Lifecycle Test Election"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["state"] == "CREATED"

    # 2. Add candidates (Auto-transitions to CONFIGURED)
    resp = await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Candidate 1", "party": "Party 1", "symbol": "P1", "position": 1},
                {"id": "C002", "name": "Candidate 2", "party": "Party 2", "symbol": "P2", "position": 2},
            ]
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201

    resp = await client.get(f"/api/elections/{election_id}", headers=admin_headers)
    assert resp.json()["state"] == "CONFIGURED"

    # 3. CONFIGURED → LOCKED
    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "LOCKED", "reason": "Candidates finalized"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "LOCKED"
    assert resp.json()["configuration_hash"] is not None

    # Register and activate device to allow opening
    await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-001", "name": "Control Unit 1"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/devices/EVM-001/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )

    # 4. LOCKED → OPEN
    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN", "reason": "Polls open"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "OPEN"

    # 5. OPEN → SUSPENDED
    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "SUSPENDED", "reason": "Temporary suspension"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "SUSPENDED"

    # 6. SUSPENDED → OPEN
    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN", "reason": "Polls resumed"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "OPEN"

    # 7. OPEN → CLOSED
    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED", "reason": "Poll hours concluded"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "CLOSED"

    # 8. CLOSED → PUBLISHED
    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "PUBLISHED", "reason": "Results certified and published"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "PUBLISHED"

    # ------------------------------------------------------------------------
    # STRICT TERMINAL STATE ENFORCEMENT: PUBLISHED has NO outgoing transitions
    # ------------------------------------------------------------------------
    forbidden_targets = ["CLOSED", "OPEN", "SUSPENDED", "LOCKED", "CONFIGURED"]
    for target in forbidden_targets:
        resp = await client.patch(
            f"/api/elections/{election_id}/state",
            json={"new_state": target, "reason": "Attempting transition from terminal state"},
            headers=admin_headers,
        )
        assert resp.status_code == 409, f"Expected 409 for PUBLISHED -> {target}, got {resp.status_code}"
        detail = resp.json()["detail"]
        assert f"Invalid state transition: PUBLISHED → {target}" in detail
        assert "Valid transitions from PUBLISHED: []" in detail


@pytest.mark.asyncio
async def test_invalid_state_transitions_rejected(client: AsyncClient, admin_headers: dict):
    election_id = "EV-2026-092"

    await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Invalid Transition Test"},
        headers=admin_headers,
    )

    # CREATED cannot jump to OPEN
    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "Invalid state transition: CREATED → OPEN" in resp.json()["detail"]

    # CREATED cannot jump to CLOSED
    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "Invalid state transition: CREATED → CLOSED" in resp.json()["detail"]
