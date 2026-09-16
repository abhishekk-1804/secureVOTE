"""
Demonstration tests for the 8 security attack vectors from Section 12.

| # | Attack | Expected result |
|---|---|---|
| 1 | Modify an audit record | AUDIT VERIFICATION FAILED |
| 2 | Modify election configuration post-lock | CONFIGURATION HASH MISMATCH |
| 3 | Duplicate voting session | REQUEST REJECTED |
| 4 | Vote after election close | REQUEST REJECTED |
| 5 | Trigger physical tamper event | TAMPER_DETECTED logged in audit |
| 6 | Manipulate a derived tally value directly | RECONCILIATION FAILURE |
| 7 | Replay an already-accepted device message | REPLAY REJECTED |
| 8 | Submit from an unknown/revoked device | DEVICE REJECTED |
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import AuditEntry, Ballot, Candidate, Election
from app.services.audit_service import AuditService


async def _setup_open_election(client: AsyncClient, admin_headers: dict, election_id: str):
    """Helper to create and open an election with 2 candidates and 1 active device."""
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": f"Attack Test Election {election_id}"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Candidate One", "position": 1},
                {"id": "C002", "name": "Candidate Two", "position": 2},
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
        json={"id": "EVM-001", "name": "Polling Unit 1"},
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


# ===========================================================================
# Attack 1: Modify an audit record in DB -> AUDIT VERIFICATION FAILED
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_1_tamper_audit_record(client: AsyncClient, admin_headers: dict, db_engine):
    """
    Attack 1: An attacker directly modifies an audit log row in the database.
    Expected: Independent hash recomputation detects the break and reports AUDIT VERIFICATION FAILED.
    """
    election_id = "EV-2026-101"
    await _setup_open_election(client, admin_headers, election_id)

    # Verify audit chain is initially intact
    verify_resp = await client.get(f"/api/elections/{election_id}/audit/verify", headers=admin_headers)
    assert verify_resp.json()["is_intact"] is True

    # Malicious database manipulation: tamper with event_data of the first audit record
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEntry)
            .where(AuditEntry.election_id == election_id, AuditEntry.sequence_number == 1)
        )
        entry = result.scalar_one()
        entry.event_data = '{"tampered": true}'
        await session.commit()

    # Re-run independent audit verification
    verify_resp = await client.get(f"/api/elections/{election_id}/audit/verify", headers=admin_headers)
    data = verify_resp.json()

    assert data["is_intact"] is False
    assert "AUDIT VERIFICATION FAILED" in data["details"]
    assert data["first_broken_sequence"] == 1


# ===========================================================================
# Attack 2: Modify election configuration post-lock -> CONFIGURATION HASH MISMATCH
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_2_tamper_config_post_lock(client: AsyncClient, admin_headers: dict, db_engine):
    """
    Attack 2: An attacker modifies candidate configuration in the DB after it was locked.
    Expected: Independent verification detects CONFIGURATION HASH MISMATCH.
    """
    election_id = "EV-2026-102"
    await _setup_open_election(client, admin_headers, election_id)

    # Tamper with candidate name directly in DB
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            update(Candidate)
            .where(Candidate.election_id == election_id, Candidate.id == "C001")
            .values(name="Malicious Injected Candidate")
        )
        await session.commit()

    # Run verification
    results_resp = await client.get(f"/api/elections/{election_id}/results", headers=admin_headers)
    data = results_resp.json()

    assert data["config_hash_valid"] is False
    assert any("CONFIGURATION HASH MISMATCH" in d for d in data["details"])
    assert data["overall_status"] == "FAILED"


# ===========================================================================
# Attack 3: Duplicate voting session -> REQUEST REJECTED
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_3_duplicate_session(client: AsyncClient, admin_headers: dict):
    """
    Attack 3: Attempt to authorize two sessions for the same voter credential in the same election.
    Expected: REQUEST REJECTED (409 Conflict).
    """
    election_id = "EV-2026-103"
    await _setup_open_election(client, admin_headers, election_id)

    # First authorization succeeds
    resp1 = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-ATTACK3", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    assert resp1.status_code == 201

    # Second authorization with same voter credential must be rejected
    resp2 = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-ATTACK3", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    assert resp2.status_code == 409
    assert "REQUEST REJECTED" in resp2.json()["detail"]


# ===========================================================================
# Attack 4: Vote after election close -> REQUEST REJECTED
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_4_vote_after_close(client: AsyncClient, admin_headers: dict):
    """
    Attack 4: An authorized token attempts to cast a vote after the election has been CLOSED.
    Expected: REQUEST REJECTED (409 Conflict).
    """
    election_id = "EV-2026-104"
    await _setup_open_election(client, admin_headers, election_id)

    # Get valid session while open
    session_resp = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-ATTACK4", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    session_token = session_resp.json()["session_token"]

    # Close the election
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )

    # Attempt to cast vote after close
    vote_resp = await client.post(
        "/api/votes",
        json={
            "session_token": session_token,
            "candidate_id": "C001",
            "device_id": "EVM-001",
            "sequence_number": 1,
        },
    )
    assert vote_resp.status_code == 409
    assert "REQUEST REJECTED" in vote_resp.json()["detail"]


# ===========================================================================
# Attack 5: Tamper switch event logging
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_5_tamper_event_logging(client: AsyncClient, admin_headers: dict, db_engine):
    """
    Attack 5: Physical tamper switch detection is recorded as a TAMPER_DETECTED audit event.
    Expected: Logged into the hash-chained audit log and verified as part of the immutable chain.
    """
    election_id = "EV-2026-105"
    await _setup_open_election(client, admin_headers, election_id)

    # Simulate firmware reporting a tamper event
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await AuditService.log_event(
            db=session,
            election_id=election_id,
            event_type="TAMPER_DETECTED",
            event_data={"trigger": "lid_switch_opened", "status": "VOTING_LOCKED"},
            actor="hardware",
            device_id="EVM-001",
        )
        await session.commit()

    # Verify audit chain remains intact with the tamper event recorded
    verify_resp = await client.get(f"/api/elections/{election_id}/audit/verify", headers=admin_headers)
    assert verify_resp.json()["is_intact"] is True

    # Audit log lists the tamper event
    log_resp = await client.get(f"/api/elections/{election_id}/audit", headers=admin_headers)
    entries = log_resp.json()["entries"]
    assert any(e["event_type"] == "TAMPER_DETECTED" for e in entries)


# ===========================================================================
# Attack 6: Manipulate a derived tally directly -> RECONCILIATION FAILURE
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_6_tally_manipulation(client: AsyncClient, admin_headers: dict, db_engine):
    """
    Attack 6: An attacker alters election.total_ballots or injects an extra ballot.
    Expected: Exact reconciliation flags RECONCILIATION FAILURE with zero tolerance.
    """
    election_id = "EV-2026-106"
    await _setup_open_election(client, admin_headers, election_id)

    # Cast 1 legitimate vote
    session_resp = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-ATK6", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    token = session_resp.json()["session_token"]
    await client.post(
        "/api/votes",
        json={
            "session_token": token,
            "candidate_id": "C001",
            "device_id": "EVM-001",
            "sequence_number": 1,
        },
    )

    # Tamper with the election total_ballots counter directly in DB
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            update(Election)
            .where(Election.id == election_id)
            .values(total_ballots=999)  # Tampered total
        )
        await session.commit()

    # Reconcile via verification
    verify_resp = await client.get(f"/api/elections/{election_id}/results", headers=admin_headers)
    data = verify_resp.json()

    assert data["reconciliation_passed"] is False
    assert any("RECONCILIATION FAILURE" in d for d in data["details"])
    assert data["overall_status"] == "FAILED"


# ===========================================================================
# Attack 7: Replay an already-accepted device message -> REPLAY REJECTED
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_7_replay_message(client: AsyncClient, admin_headers: dict):
    """
    Attack 7: A device sequence number is replayed.
    Expected: REPLAY REJECTED (409 Conflict).
    """
    election_id = "EV-2026-107"
    await _setup_open_election(client, admin_headers, election_id)

    # Vote 1: sequence_number 1
    s1 = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-REPLAY-1", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    t1 = s1.json()["session_token"]
    await client.post(
        "/api/votes",
        json={"session_token": t1, "candidate_id": "C001", "device_id": "EVM-001", "sequence_number": 1},
    )

    # Vote 2: replayed sequence_number 1 on new session
    s2 = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-REPLAY-2", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    t2 = s2.json()["session_token"]
    replay_resp = await client.post(
        "/api/votes",
        json={"session_token": t2, "candidate_id": "C002", "device_id": "EVM-001", "sequence_number": 1},
    )
    assert replay_resp.status_code == 409
    assert "REPLAY REJECTED" in replay_resp.json()["detail"]


# ===========================================================================
# Attack 8: Submit from an unknown/revoked device -> DEVICE REJECTED
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_8_unknown_and_revoked_device(client: AsyncClient, admin_headers: dict):
    """
    Attack 8: Attempt session authorization or vote from an unknown or revoked device.
    Expected: DEVICE REJECTED (403 Forbidden).
    """
    election_id = "EV-2026-108"
    await _setup_open_election(client, admin_headers, election_id)

    # Sub-test 8a: Unknown device
    resp_unknown = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-ATK8-1", "device_id": "EVM-999"},
        headers=admin_headers,
    )
    assert resp_unknown.status_code == 403
    assert "DEVICE REJECTED" in resp_unknown.json()["detail"]

    # Sub-test 8b: Revoke EVM-001
    await client.patch(
        f"/api/elections/{election_id}/devices/EVM-001/status",
        json={"status": "REVOKED"},
        headers=admin_headers,
    )

    # Attempt session authorization on revoked device
    resp_revoked = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-ATK8-2", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    assert resp_revoked.status_code == 403
    assert "DEVICE REJECTED" in resp_revoked.json()["detail"]


# ===========================================================================
# Phase 5 Attack 9: Modified signed result -> SIGNATURE_INVALID
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_9_modified_signed_result(
    client: AsyncClient,
    admin_headers: dict,
    ephemeral_signing_key,
):
    """
    Attack 9: Attacker modifies any byte in the signed result payload or signature.
    Expected: Independent Verifier reports SIGNATURE_INVALID.
    """
    election_id = "EV-2026-109"
    await _setup_open_election(client, admin_headers, election_id)

    # Cast 1 vote
    s_resp = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-ATK9-1", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    token = s_resp.json()["session_token"]
    await client.post(
        "/api/votes",
        json={"session_token": token, "candidate_id": "C001", "device_id": "EVM-001", "sequence_number": 1},
    )

    # Close and verify and sign
    await client.patch(f"/api/elections/{election_id}/state", json={"new_state": "CLOSED"}, headers=admin_headers)
    await client.post(f"/api/elections/{election_id}/verify", headers=admin_headers)
    await client.post(f"/api/elections/{election_id}/sign-manifest", headers=admin_headers)

    # Export
    export_resp = await client.get(f"/api/elections/{election_id}/export", headers=admin_headers)
    export_data = export_resp.json()

    # Tamper with the digital signature
    from standalone_verifier.verifier import StandaloneElectionVerifier
    import json
    sig_obj = json.loads(export_data["manifest"]["digital_signature"])
    sig_obj["signature"] = "0" * len(sig_obj["signature"])
    export_data["manifest"]["digital_signature"] = json.dumps(sig_obj)

    result = StandaloneElectionVerifier.verify_export_data(export_data)
    assert result["valid"] is False
    assert "SIGNATURE_INVALID" in result["failures"]
    assert result["checks"]["signature"] is False


# ===========================================================================
# Phase 5 Attack 10: Modified exported ballot -> BALLOT_HASH_MISMATCH
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_10_modified_exported_ballot(
    client: AsyncClient,
    admin_headers: dict,
    ephemeral_signing_key,
):
    """
    Attack 10: Attacker alters candidate selection inside an exported ballot record.
    Expected: Independent Verifier recalculates SHA-256 hash and detects BALLOT_HASH_MISMATCH.
    """
    election_id = "EV-2026-110"
    await _setup_open_election(client, admin_headers, election_id)

    # Cast 1 vote
    s_resp = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-ATK10-1", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    token = s_resp.json()["session_token"]
    await client.post(
        "/api/votes",
        json={"session_token": token, "candidate_id": "C001", "device_id": "EVM-001", "sequence_number": 1},
    )

    await client.patch(f"/api/elections/{election_id}/state", json={"new_state": "CLOSED"}, headers=admin_headers)
    export_resp = await client.get(f"/api/elections/{election_id}/export", headers=admin_headers)
    export_data = export_resp.json()

    # Tamper with candidate in ballot record
    from standalone_verifier.verifier import StandaloneElectionVerifier
    export_data["ballots"][0]["candidate_id"] = "C002"

    result = StandaloneElectionVerifier.verify_export_data(export_data)
    assert result["valid"] is False
    assert any("BALLOT_HASH_MISMATCH" in f for f in result["failures"])
    assert result["checks"]["ballot_hashes"] is False


# ===========================================================================
# Phase 5 Attack 11: Modified anchor root -> ANCHOR_MISMATCH
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_11_modified_anchor_root(
    client: AsyncClient,
    admin_headers: dict,
    ephemeral_signing_key,
):
    """
    Attack 11: Attacker attempts to forge or mutate the external anchored audit root.
    Expected: Independent Verifier reports ANCHOR_MISMATCH.
    """
    election_id = "EV-2026-111"
    await _setup_open_election(client, admin_headers, election_id)

    await client.patch(f"/api/elections/{election_id}/state", json={"new_state": "CLOSED"}, headers=admin_headers)
    anchor_resp = await client.post(
        f"/api/elections/{election_id}/anchors",
        json={"provider": "LOCAL ANCHOR"},
        headers=admin_headers,
    )
    receipt = anchor_resp.json()

    export_resp = await client.get(f"/api/elections/{election_id}/export", headers=admin_headers)
    export_data = export_resp.json()

    # Modify anchored root to forged hash
    receipt["root_hash"] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    from standalone_verifier.verifier import StandaloneElectionVerifier
    result = StandaloneElectionVerifier.verify_export_data(export_data, anchor_receipt=receipt)
    assert result["valid"] is False
    assert "ANCHOR_MISMATCH" in result["failures"]
    assert result["checks"]["anchor"] is False


# ===========================================================================
# Phase 5 Attack 12: High-severity anomaly -> ADVISORY FINDING (Not blocking)
# ===========================================================================

@pytest.mark.asyncio
async def test_attack_12_high_severity_anomaly_does_not_block_operations(
    client: AsyncClient,
    admin_headers: dict,
    ephemeral_signing_key,
    db_engine,
):
    """
    Attack 12: An adversary triggers physical chassis breach or extreme voting rate bursts
    producing HIGH-severity advisory anomaly findings.
    Expected: Anomaly is logged with ADVISORY FINDING notice, but election operations,
    manifest verification, and digital signing proceed unaffected without denial of service.
    """
    election_id = "EV-2026-112"
    await _setup_open_election(client, admin_headers, election_id)

    # Cast vote
    s_resp = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-ATK12-1", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    token = s_resp.json()["session_token"]
    await client.post(
        "/api/votes",
        json={"session_token": token, "candidate_id": "C001", "device_id": "EVM-001", "sequence_number": 1},
    )

    # Inject HIGH-severity hardware tamper switch event
    from app.services.audit_service import AuditService
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await AuditService.log_event(
            db=session,
            election_id=election_id,
            event_type="DEVICE_TAMPER_SWITCH",
            event_data='{"switch": "chassis", "state": "BREACH"}',
            actor="adversary",
            device_id="EVM-001",
        )
        await session.commit()

    # Confirm advisory finding is present
    ano_resp = await client.get(f"/api/elections/{election_id}/anomalies", headers=admin_headers)
    assert ano_resp.status_code == 200
    ano_data = ano_resp.json()
    high_findings = [f for f in ano_data["findings"] if f["severity"] == "HIGH"]
    assert len(high_findings) >= 1
    assert ano_data["status"] == "ADVISORY_ONLY_DOES_NOT_BLOCK_LIFECYCLE"

    # HARD BOUNDARY: Closing election and digital signing MUST NOT be blocked
    close_resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )
    assert close_resp.status_code == 200

    verify_resp = await client.post(f"/api/elections/{election_id}/verify", headers=admin_headers)
    assert verify_resp.status_code == 200

    sign_resp = await client.post(f"/api/elections/{election_id}/sign-manifest", headers=admin_headers)
    assert sign_resp.status_code == 200
    assert sign_resp.json()["digital_signature"]["algorithm"] == "Ed25519"
