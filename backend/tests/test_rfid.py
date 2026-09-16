"""
Phase 5: RFID / Identity Abstraction and Keyed Pseudonymization Tests.

Verifies:
1. Valid RFID card tap generates a voting session in an OPEN election.
2. Repeated card use is detected and rejected (anti-double-voting).
3. Revoked card is rejected.
4. Invalid card format is rejected.
5. MANDATORY AMENDMENT 3: Keyed pseudonymization (HMAC-SHA256), NOT bare SHA-256.
6. Changing server secret changes pseudonyms.
7. Strict privacy: Raw UID is never persisted or logged in the database.
8. Architectural boundary: RFID AUTHENTICATION != VOTER ELIGIBILITY (closed/locked election).
"""

import hashlib
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import AuditEntry, Ballot, VotingSession
from app.services.rfid_service import MockRFIDReader


@pytest.mark.asyncio
async def test_rfid_valid_tap_creates_session_in_open_election(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    """Valid card on an OPEN election and ACTIVE device authorizes a session."""
    election_id = "EV-2026-801"
    device_id = "EVM-001"

    # Setup election
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": "RFID Test Election"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Alice", "position": 1},
                {"id": "C002", "name": "Bob", "position": 2},
            ]
        },
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": device_id, "name": "Unit 1"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/devices/{device_id}/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "LOCKED"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )

    # Tap valid card
    raw_uid = "CARD-VALID-01"
    resp = await client.post(
        "/api/rfid/tap",
        json={
            "raw_uid": raw_uid,
            "device_id": device_id,
            "election_id": election_id,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is True
    assert data["card_status"] == "VALID"
    assert data["device_id"] == device_id
    assert data["session_id"] is not None
    assert len(data["pseudonym"]) == 64  # SHA-256 hex length
    assert "RFID AUTHENTICATION != VOTER ELIGIBILITY" in data["notice"]

    # Cast a ballot using the authorized session token
    token = data["session_id"]
    vote_resp = await client.post(
        "/api/votes",
        json={
            "session_token": token,
            "candidate_id": "C001",
            "device_id": device_id,
            "sequence_number": 1,
        },
    )
    assert vote_resp.status_code == 201


@pytest.mark.asyncio
async def test_rfid_repeated_use_rejected(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    """Tapping the same card twice in the same election is rejected (REPEATED_USE)."""
    election_id = "EV-2026-802"
    device_id = "EVM-001"

    await client.post("/api/elections", json={"id": election_id, "name": "Repeat Tap Election"}, headers=admin_headers)
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Alice", "position": 1},
                {"id": "C002", "name": "Bob", "position": 2},
            ]
        },
        headers=admin_headers,
    )
    await client.post(f"/api/elections/{election_id}/devices", json={"id": device_id, "name": "Unit 1"}, headers=admin_headers)
    await client.patch(f"/api/elections/{election_id}/devices/{device_id}/status", json={"status": "ACTIVE"}, headers=admin_headers)
    await client.patch(f"/api/elections/{election_id}/state", json={"new_state": "LOCKED"}, headers=admin_headers)
    await client.patch(f"/api/elections/{election_id}/state", json={"new_state": "OPEN"}, headers=admin_headers)

    raw_uid = "CARD-VALID-MULTI-01"

    # First tap succeeds
    resp1 = await client.post(
        "/api/rfid/tap",
        json={"raw_uid": raw_uid, "device_id": device_id, "election_id": election_id},
    )
    assert resp1.status_code == 200
    assert resp1.json()["card_status"] == "VALID"
    assert resp1.json()["session_id"] is not None

    # Second tap fails with REPEATED_USE
    resp2 = await client.post(
        "/api/rfid/tap",
        json={"raw_uid": raw_uid, "device_id": device_id, "election_id": election_id},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["card_status"] == "REPEATED_USE"
    assert data2["session_id"] is None
    assert "Credential already used" in data2["notice"]


@pytest.mark.asyncio
async def test_rfid_revoked_card_rejected(client: AsyncClient):
    """Revoked card is rejected at the authentication layer."""
    resp = await client.post(
        "/api/rfid/tap",
        json={
            "raw_uid": "CARD-REVOKED-01",
            "device_id": "EVM-001",
            "election_id": "EV-2026-803",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is False
    assert data["card_status"] == "REVOKED"
    assert data["session_id"] is None


@pytest.mark.asyncio
async def test_rfid_invalid_format_rejected(client: AsyncClient):
    """Invalid or malformed card UID is rejected."""
    resp = await client.post(
        "/api/rfid/tap",
        json={
            "raw_uid": "MALFORMED_CHIP_ERROR",
            "device_id": "EVM-001",
            "election_id": "EV-2026-804",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is False
    assert data["card_status"] == "INVALID"
    assert data["session_id"] is None


def test_mandatory_amendment_keyed_pseudonymization_not_bare_sha256():
    """
    MANDATORY AMENDMENT 3:
    1. Keyed pseudonymization HMAC-SHA256(server_secret, uid).
    2. Proves pseudonym is NOT bare SHA-256(uid).
    3. Proves changing the server secret changes the pseudonym.
    """
    raw_uid = "04A1B2C3D4E5"
    bare_sha256 = hashlib.sha256(raw_uid.encode("utf-8")).hexdigest()

    # Compute default keyed pseudonym using the test fixture secret
    pseudonym = MockRFIDReader.compute_pseudonym(raw_uid)

    # 1. Must NOT be bare SHA-256
    assert pseudonym != bare_sha256, "CRITICAL: Keyed pseudonym must not match bare SHA-256"

    # 2. Changing secret produces completely different pseudonyms
    pseudo_secret_a = MockRFIDReader.compute_pseudonym(raw_uid, secret="secret-key-salt-alpha")
    pseudo_secret_b = MockRFIDReader.compute_pseudonym(raw_uid, secret="secret-key-salt-beta")

    assert pseudo_secret_a != pseudo_secret_b, "Changing secret must produce different pseudonyms"
    assert pseudo_secret_a != bare_sha256
    assert pseudo_secret_b != bare_sha256


@pytest.mark.asyncio
async def test_rfid_missing_secret_fails_safely(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    When SECUREVOTE_RFID_SECRET is not configured in the environment:
    1. Direct call to MockRFIDReader.get_server_secret() raises RuntimeError.
    2. Direct call to MockRFIDReader.compute_pseudonym(uid) raises RuntimeError.
    3. POST /api/rfid/tap fails safely with HTTP 500 configuration error without crashing or falling back.
    """
    monkeypatch.delenv("SECUREVOTE_RFID_SECRET", raising=False)

    # 1. Direct call to get_server_secret() raises RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        MockRFIDReader.get_server_secret()
    assert "CRITICAL CONFIGURATION ERROR" in str(exc_info.value)

    # 2. Direct call to compute_pseudonym() raises RuntimeError
    with pytest.raises(RuntimeError) as exc_info2:
        MockRFIDReader.compute_pseudonym("CARD-VALID-01")
    assert "CRITICAL CONFIGURATION ERROR" in str(exc_info2.value)

    # 3. HTTP endpoint returns 500 with configuration error details
    resp = await client.post(
        "/api/rfid/tap",
        json={
            "raw_uid": "CARD-VALID-01",
            "device_id": "EVM-001",
            "election_id": "EV-2026-MISSING-SECRET",
        },
    )
    assert resp.status_code == 500
    detail = resp.json().get("detail", "")
    assert "SECUREVOTE_RFID_SECRET is not configured" in detail


def test_rfid_explicit_secret_and_hmac_properties():
    """
    Verifies HMAC-SHA256 pseudonym properties:
    1. Explicit test secret works.
    2. Same UID + same secret produces identical pseudonym.
    3. Same UID + different secret produces different pseudonym.
    4. Pseudonym is strictly not bare SHA-256(raw_uid).
    """
    raw_uid = "04A1B2C3D4E5"
    secret_a = "ephemeral-test-secret-alpha"
    secret_b = "ephemeral-test-secret-beta"

    # Explicit test secret works
    p1 = MockRFIDReader.compute_pseudonym(raw_uid, secret=secret_a)
    p2 = MockRFIDReader.compute_pseudonym(raw_uid, secret=secret_a)
    assert p1 == p2
    assert len(p1) == 64

    # Different secret produces different pseudonym
    p3 = MockRFIDReader.compute_pseudonym(raw_uid, secret=secret_b)
    assert p1 != p3

    # Neither matches bare SHA-256(raw_uid)
    bare_sha256 = hashlib.sha256(raw_uid.encode("utf-8")).hexdigest()
    assert p1 != bare_sha256
    assert p3 != bare_sha256



@pytest.mark.asyncio
async def test_strict_privacy_raw_uid_never_stored_in_database(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_engine,
):
    """
    Strict privacy verification:
    The raw UID string must NEVER be stored in any database column or logged event.
    """
    election_id = "EV-2026-805"
    device_id = "EVM-001"
    unique_raw_uid = "RAW-SECRET-PHYSICAL-CHIP-998877"

    await client.post("/api/elections", json={"id": election_id, "name": "Privacy Election"}, headers=admin_headers)
    await client.post(f"/api/elections/{election_id}/candidates", json={"candidates": [{"id": "C001", "name": "Alice", "position": 1}]}, headers=admin_headers)
    await client.post(f"/api/elections/{election_id}/devices", json={"id": device_id, "name": "Unit 1"}, headers=admin_headers)
    await client.patch(f"/api/elections/{election_id}/devices/{device_id}/status", json={"status": "ACTIVE"}, headers=admin_headers)
    await client.patch(f"/api/elections/{election_id}/state", json={"new_state": "LOCKED"}, headers=admin_headers)
    await client.patch(f"/api/elections/{election_id}/state", json={"new_state": "OPEN"}, headers=admin_headers)

    tap_resp = await client.post(
        "/api/rfid/tap",
        json={"raw_uid": unique_raw_uid, "device_id": device_id, "election_id": election_id},
    )
    assert tap_resp.status_code == 200

    # Inspect all rows in database to verify raw UID never entered storage
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Check VotingSession records
        sessions = (await session.execute(select(VotingSession))).scalars().all()
        for s in sessions:
            assert unique_raw_uid not in s.voter_credential
            assert unique_raw_uid not in s.session_token

        # Check AuditEntry records
        audit_events = (await session.execute(select(AuditEntry))).scalars().all()
        for a in audit_events:
            if a.event_data:
                assert unique_raw_uid not in a.event_data


@pytest.mark.asyncio
async def test_rfid_architectural_boundary_closed_election(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    """
    Architectural boundary test:
    RFID AUTHENTICATION != VOTER ELIGIBILITY
    A valid card tapped when election is CLOSED or LOCKED authenticates the card,
    but grants NO voting session, because voter eligibility requires an OPEN election.
    """
    election_id = "EV-2026-806"
    device_id = "EVM-001"

    await client.post("/api/elections", json={"id": election_id, "name": "Boundary Election"}, headers=admin_headers)
    await client.post(f"/api/elections/{election_id}/candidates", json={"candidates": [{"id": "C001", "name": "Alice", "position": 1}]}, headers=admin_headers)
    await client.post(f"/api/elections/{election_id}/devices", json={"id": device_id, "name": "Unit 1"}, headers=admin_headers)
    await client.patch(f"/api/elections/{election_id}/devices/{device_id}/status", json={"status": "ACTIVE"}, headers=admin_headers)
    # Election is in SETUP state, NOT OPEN!

    resp = await client.post(
        "/api/rfid/tap",
        json={
            "raw_uid": "CARD-VALID-BOUNDARY",
            "device_id": device_id,
            "election_id": election_id,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is True
    assert data["card_status"] == "VALID"
    assert data["session_id"] is None  # NO session created!
    assert "election is not open" in data["notice"].lower()
