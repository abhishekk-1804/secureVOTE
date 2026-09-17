"""
Comprehensive integration tests for SecureVOTE backend.

Covers: auth, election lifecycle, candidate config, config locking + hashing,
device registration/revocation, session authorization, vote recording,
duplicate prevention, replay protection, audit hashing + verification,
reconciliation, verification engine, result manifest, closed-election
rejection, invalid state transitions, and malformed input.

These tests exercise the full API through HTTPX Ã¢â‚¬â€ they are integration
tests, not unit tests, because they verify the complete requestÃ¢â€ â€™serviceÃ¢â€ â€™db
pipeline.
"""

import pytest
from httpx import AsyncClient


# ==========================================================================
# Auth Tests
# ==========================================================================

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    """Register a user, then log in and get a valid JWT."""
    resp = await client.post(
        "/api/auth/register",
        json={"username": "testuser", "password": "test1234", "role": "OBSERVER"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["role"] == "OBSERVER"

    resp = await client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "test1234"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Login with wrong password returns 401."""
    await client.post(
        "/api/auth/register",
        json={"username": "user2", "password": "correct1", "role": "OBSERVER"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "user2", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_registration(client: AsyncClient):
    """Duplicate username returns 409."""
    await client.post(
        "/api/auth/register",
        json={"username": "dup", "password": "pass1234", "role": "OBSERVER"},
    )
    resp = await client.post(
        "/api/auth/register",
        json={"username": "dup", "password": "pass5678", "role": "OBSERVER"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_protected_endpoint_without_auth(client: AsyncClient):
    """Accessing protected endpoint without token returns 401."""
    resp = await client.get("/api/elections")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_rbac_observer_cannot_create_election(
    client: AsyncClient, observer_token: str
):
    """OBSERVER role cannot create elections (requires ADMIN)."""
    resp = await client.post(
        "/api/elections",
        json={"id": "EV-2026-999", "name": "Test"},
        headers={"Authorization": f"Bearer {observer_token}"},
    )
    assert resp.status_code == 403


# ==========================================================================
# Election Lifecycle Tests
# ==========================================================================

@pytest.mark.asyncio
async def test_full_election_lifecycle(client: AsyncClient, admin_headers: dict):
    """
    End-to-end election lifecycle:
    CREATED Ã¢â€ â€™ add candidates Ã¢â€ â€™ CONFIGURED Ã¢â€ â€™ LOCKED Ã¢â€ â€™ register+activate device Ã¢â€ â€™
    OPEN Ã¢â€ â€™ authorize session Ã¢â€ â€™ cast vote Ã¢â€ â€™ CLOSED Ã¢â€ â€™ verify Ã¢â€ â€™ PUBLISHED
    """
    # 1. Create election
    resp = await client.post(
        "/api/elections",
        json={"id": "EV-2026-001", "name": "Test Election 2026"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["state"] == "CREATED"

    # 2. Add candidates (auto-transitions to CONFIGURED)
    resp = await client.post(
        "/api/elections/EV-2026-001/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Alice", "party": "Party A", "symbol": "A", "position": 1},
                {"id": "C002", "name": "Bob", "party": "Party B", "symbol": "B", "position": 2},
            ]
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201

    # Verify auto-transition to CONFIGURED
    resp = await client.get("/api/elections/EV-2026-001", headers=admin_headers)
    assert resp.json()["state"] == "CONFIGURED"

    # 3. Lock configuration
    resp = await client.patch(
        "/api/elections/EV-2026-001/state",
        json={"new_state": "LOCKED"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "LOCKED"
    assert data["configuration_hash"] is not None

    # 4. Register and activate a device
    resp = await client.post(
        "/api/elections/EV-2026-001/devices",
        json={"id": "EVM-001", "name": "Device 1"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    resp = await client.patch(
        "/api/elections/EV-2026-001/devices/EVM-001/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # 5. Open election
    resp = await client.patch(
        "/api/elections/EV-2026-001/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "OPEN"

    # 6. Authorize a voting session
    resp = await client.post(
        "/api/elections/EV-2026-001/sessions",
        json={"voter_credential": "VOTER-001", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    session_token = resp.json()["session_token"]

    # 7. Cast a vote
    resp = await client.post(
        "/api/votes",
        json={
            "session_token": session_token,
            "candidate_id": "C001",
            "device_id": "EVM-001",
            "sequence_number": 1,
        },
    )
    assert resp.status_code == 201
    vote_data = resp.json()
    assert vote_data["candidate_id"] == "C001"
    assert vote_data["ballot_hash"] is not None

    # 8. Close election
    resp = await client.patch(
        "/api/elections/EV-2026-001/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "CLOSED"

    # 9. Verify results
    resp = await client.get(
        "/api/elections/EV-2026-001/results",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    results = resp.json()
    assert results["overall_status"] == "PASSED"
    assert results["config_hash_valid"] is True
    assert results["audit_chain_intact"] is True
    assert results["reconciliation_passed"] is True
    assert results["tally_independently_verified"] is True

    # 10. Publish
    resp = await client.patch(
        "/api/elections/EV-2026-001/state",
        json={"new_state": "PUBLISHED"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_invalid_state_transition(client: AsyncClient, admin_headers: dict):
    """Reject invalid state transitions (e.g., CREATED Ã¢â€ â€™ OPEN)."""
    await client.post(
        "/api/elections",
        json={"id": "EV-2026-002", "name": "Bad Transition Test"},
        headers=admin_headers,
    )
    resp = await client.patch(
        "/api/elections/EV-2026-002/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "Invalid state transition" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_duplicate_election_id(client: AsyncClient, admin_headers: dict):
    """Duplicate election ID returns 409."""
    await client.post(
        "/api/elections",
        json={"id": "EV-2026-003", "name": "First"},
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/elections",
        json={"id": "EV-2026-003", "name": "Duplicate"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


# ==========================================================================
# Duplicate Vote / Session Prevention (Attack #3)
# ==========================================================================

@pytest.mark.asyncio
async def test_duplicate_session_rejected(client: AsyncClient, admin_headers: dict):
    """Same voter_credential cannot get two sessions (Attack #3)."""
    # Setup election to OPEN state
    await _setup_open_election(client, admin_headers, "EV-2026-004")

    # First session
    resp = await client.post(
        "/api/elections/EV-2026-004/sessions",
        json={"voter_credential": "VOTER-DUP", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    # Duplicate session
    resp = await client.post(
        "/api/elections/EV-2026-004/sessions",
        json={"voter_credential": "VOTER-DUP", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "DUPLICATE_SESSION" in resp.json()["detail"]


# ==========================================================================
# Vote After Close (Attack #4)
# ==========================================================================

@pytest.mark.asyncio
async def test_vote_after_close_rejected(client: AsyncClient, admin_headers: dict):
    """Voting after election close returns rejection (Attack #4)."""
    await _setup_open_election(client, admin_headers, "EV-2026-005")

    # Authorize session while open
    resp = await client.post(
        "/api/elections/EV-2026-005/sessions",
        json={"voter_credential": "VOTER-LATE", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    session_token = resp.json()["session_token"]

    # Close election
    await client.patch(
        "/api/elections/EV-2026-005/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )

    # Try to vote
    resp = await client.post(
        "/api/votes",
        json={
            "session_token": session_token,
            "candidate_id": "C001",
            "device_id": "EVM-001",
            "sequence_number": 1,
        },
    )
    assert resp.status_code == 409
    assert "REQUEST REJECTED" in resp.json()["detail"]


# ==========================================================================
# Replay Protection (Attack #7)
# ==========================================================================

@pytest.mark.asyncio
async def test_replay_rejected(client: AsyncClient, admin_headers: dict):
    """Replay of already-accepted sequence number is rejected (Attack #7)."""
    await _setup_open_election(client, admin_headers, "EV-2026-006")

    # Cast first vote
    resp = await client.post(
        "/api/elections/EV-2026-006/sessions",
        json={"voter_credential": "VOTER-R1", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    token1 = resp.json()["session_token"]
    resp = await client.post(
        "/api/votes",
        json={
            "session_token": token1,
            "candidate_id": "C001",
            "device_id": "EVM-001",
            "sequence_number": 1,
        },
    )
    assert resp.status_code == 201

    # Try second vote with same sequence number but different session
    resp = await client.post(
        "/api/elections/EV-2026-006/sessions",
        json={"voter_credential": "VOTER-R2", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    token2 = resp.json()["session_token"]
    resp = await client.post(
        "/api/votes",
        json={
            "session_token": token2,
            "candidate_id": "C001",
            "device_id": "EVM-001",
            "sequence_number": 1,  # REPLAY Ã¢â‚¬â€ same seq as before
        },
    )
    assert resp.status_code == 409
    assert "REPLAY REJECTED" in resp.json()["detail"]


# ==========================================================================
# Unknown/Revoked Device (Attack #8)
# ==========================================================================

@pytest.mark.asyncio
async def test_unknown_device_rejected(client: AsyncClient, admin_headers: dict):
    """Vote from unknown device is rejected (Attack #8)."""
    await _setup_open_election(client, admin_headers, "EV-2026-007")

    resp = await client.post(
        "/api/elections/EV-2026-007/sessions",
        json={"voter_credential": "VOTER-X", "device_id": "EVM-999"},
        headers=admin_headers,
    )
    assert resp.status_code == 403
    assert "DEVICE REJECTED" in resp.json()["detail"]


# ==========================================================================
# Audit Chain Verification (Attack #1)
# ==========================================================================

@pytest.mark.asyncio
async def test_audit_chain_intact(client: AsyncClient, admin_headers: dict):
    """Audit chain verifies as intact after normal operations."""
    await _setup_open_election(client, admin_headers, "EV-2026-008")

    resp = await client.get(
        "/api/elections/EV-2026-008/audit/verify",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_intact"] is True
    assert data["verified_entries"] > 0


# ==========================================================================
# Reconciliation (Attack #6)
# ==========================================================================

@pytest.mark.asyncio
async def test_reconciliation_passes(client: AsyncClient, admin_headers: dict):
    """Reconciliation passes when data is consistent."""
    await _setup_open_election(client, admin_headers, "EV-2026-009")

    # Cast 3 votes
    for i in range(1, 4):
        resp = await client.post(
            "/api/elections/EV-2026-009/sessions",
            json={"voter_credential": f"VOTER-{i:03d}", "device_id": "EVM-001"},
            headers=admin_headers,
        )
        token = resp.json()["session_token"]
        candidate = "C001" if i % 2 == 1 else "C002"
        await client.post(
            "/api/votes",
            json={
                "session_token": token,
                "candidate_id": candidate,
                "device_id": "EVM-001",
                "sequence_number": i,
            },
        )

    # Close and verify
    await client.patch(
        "/api/elections/EV-2026-009/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )

    resp = await client.get(
        "/api/elections/EV-2026-009/results",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    results = resp.json()
    assert results["reconciliation_passed"] is True
    assert results["overall_status"] == "PASSED"


# ==========================================================================
# Configuration Hash Verification (Attack #2)
# ==========================================================================

@pytest.mark.asyncio
async def test_config_hash_valid(client: AsyncClient, admin_headers: dict):
    """Configuration hash is valid after locking."""
    await _setup_open_election(client, admin_headers, "EV-2026-010")

    resp = await client.get(
        "/api/elections/EV-2026-010/results",
        headers=admin_headers,
    )
    assert resp.json()["config_hash_valid"] is True


# ==========================================================================
# Open Election Requires Active Device
# ==========================================================================

@pytest.mark.asyncio
async def test_open_without_device_fails(client: AsyncClient, admin_headers: dict):
    """Cannot open election without at least one ACTIVE device."""
    await client.post(
        "/api/elections",
        json={"id": "EV-2026-011", "name": "No Device Test"},
        headers=admin_headers,
    )
    await client.post(
        "/api/elections/EV-2026-011/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "A", "position": 1},
                {"id": "C002", "name": "B", "position": 2},
            ]
        },
        headers=admin_headers,
    )
    await client.patch(
        "/api/elections/EV-2026-011/state",
        json={"new_state": "LOCKED"},
        headers=admin_headers,
    )
    resp = await client.patch(
        "/api/elections/EV-2026-011/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "no ACTIVE devices" in resp.json()["detail"]


# ==========================================================================
# Malformed Input
# ==========================================================================

@pytest.mark.asyncio
async def test_malformed_election_id(client: AsyncClient, admin_headers: dict):
    """Invalid election ID format is rejected by Pydantic validation."""
    resp = await client.post(
        "/api/elections",
        json={"id": "BAD-ID", "name": "Bad ID"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_malformed_candidate_id(client: AsyncClient, admin_headers: dict):
    """Invalid candidate ID format is rejected."""
    await client.post(
        "/api/elections",
        json={"id": "EV-2026-012", "name": "Malformed Candidate"},
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/elections/EV-2026-012/candidates",
        json={"candidates": [{"id": "BADID", "name": "X", "position": 1}]},
        headers=admin_headers,
    )
    assert resp.status_code == 422


# ==========================================================================
# Health Check
# ==========================================================================

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health check returns 200."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ==========================================================================
# Helper: set up an election in OPEN state
# ==========================================================================

async def _setup_open_election(
    client: AsyncClient,
    admin_headers: dict,
    election_id: str,
) -> None:
    """Helper to create an election and advance it to OPEN state."""
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": f"Election {election_id}"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Alice", "party": "Party A", "symbol": "A", "position": 1},
                {"id": "C002", "name": "Bob", "party": "Party B", "symbol": "B", "position": 2},
            ]
        },
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "LOCKED"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-001", "name": "Device 1"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/devices/EVM-001/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )
