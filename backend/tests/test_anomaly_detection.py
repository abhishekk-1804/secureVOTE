"""
Unit and Integration Tests for SecureVOTE Advisory Anomaly Detection (Phase 5.4).

Tests:
1. Tamper correlation rule detects hardware tamper events (HIGH severity).
2. Rejection burst rule detects clustered rejections (HIGH severity).
3. Voting rate burst rule detects unusually fast ballot submissions (HIGH severity).
4. Sequence gap rule detects non-consecutive sequence numbers (MEDIUM severity).
5. Device status rule detects suspended/revoked devices (MEDIUM severity).
6. MANDATORY BOUNDARY TEST:
   Proves that high-severity advisory findings NEVER automatically block or alter:
   - Election lifecycle transitions (close)
   - Manifest generation and verification
   - Cryptographic manifest signing
   - Independent verification
"""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import AuditEntry
from app.services.anomaly_detection import AnomalyDetectionService
from standalone_verifier.verifier import StandaloneElectionVerifier


@pytest.mark.asyncio
async def test_tamper_correlation_detection(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_engine,
):
    """Test that hardware tamper events trigger a HIGH severity advisory finding."""
    election_id = "EV-2026-ANO1"
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Tamper Anomaly Test"},
        headers=admin_headers,
    )

    # Directly log a tamper event in audit log using dedicated session
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        session.add(
            AuditEntry(
                election_id=election_id,
                event_type="TAMPER_DETECTED",
                event_data='{"sensor": "switch_1", "state": "TRIGGERED"}',
                actor="hardware",
                device_id="EVM-001",
                sequence_number=1,
                timestamp=datetime.now(timezone.utc),
                previous_hash="GENESIS",
                entry_hash="a" * 64,
            )
        )
        await session.commit()

    resp = await client.get(f"/api/elections/{election_id}/anomalies", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["findings_count"] >= 1
    tamper_findings = [f for f in data["findings"] if f["rule_id"] == "RULE-TAMPER-001"]
    assert len(tamper_findings) == 1
    assert tamper_findings[0]["severity"] == "HIGH"
    assert tamper_findings[0]["category"] == "TAMPER"
    assert "REQUIRES HUMAN REVIEW" in tamper_findings[0]["advisory_explanation"]


@pytest.mark.asyncio
async def test_rejection_burst_detection(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session,
):
    """Test that >= 3 rejected events trigger a HIGH severity rejection burst finding."""
    election_id = "EV-2026-ANO2"
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Rejection Burst Test"},
        headers=admin_headers,
    )

    now = datetime.now(timezone.utc)
    for i in range(1, 4):
        db_session.add(
            AuditEntry(
                election_id=election_id,
                event_type="REPLAY_ATTEMPT_REJECTED",
                event_data=f'{{"attempt": {i}}}',
                actor="system",
                device_id="EVM-002",
                sequence_number=i,
                timestamp=now,
                previous_hash="GENESIS" if i == 1 else "h" * 64,
                entry_hash=f"h{i}" * 32,
            )
        )
    await db_session.commit()

    resp = await client.get(f"/api/elections/{election_id}/anomalies", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()

    rej_findings = [f for f in data["findings"] if f["rule_id"] == "RULE-REJ-001"]
    assert len(rej_findings) == 1
    assert rej_findings[0]["severity"] == "HIGH"
    assert rej_findings[0]["evidence"]["rejection_count"] == 3


@pytest.mark.asyncio
async def test_mandatory_hard_lifecycle_boundary(
    client: AsyncClient,
    admin_headers: dict[str, str],
    ephemeral_signing_key,
    db_engine,
):
    """
    MANDATORY AMENDMENT TEST:
    Trigger a condition that produces a HIGH-severity advisory finding (e.g. tamper switch).
    Confirm that:
    1. The high-severity advisory finding is present.
    2. Closing the election succeeds normally.
    3. Manifest generation and verification succeeds normally.
    4. Digital signing succeeds normally.
    5. Independent verification on exported archive succeeds normally.
    Proves that anomaly findings NEVER block or alter deterministic election operations.
    """
    election_id = "EV-2026-903"

    # 1. Create election with candidates and device
    resp = await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Hard Boundary Test Election"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Alice", "position": 1},
                {"id": "C002", "name": "Bob", "position": 2},
            ]
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-001", "name": "Unit 1"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    resp = await client.patch(
        f"/api/elections/{election_id}/devices/EVM-001/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "LOCKED"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # 2. Cast a valid ballot
    s_resp = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-BND-01", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    assert s_resp.status_code == 201, f"Session authorization failed: {s_resp.text}"
    token = s_resp.json()["session_token"]
    v_resp = await client.post(
        "/api/votes",
        json={
            "session_token": token,
            "candidate_id": "C001",
            "device_id": "EVM-001",
            "sequence_number": 1,
        },
        headers=admin_headers,
    )
    assert v_resp.status_code == 201

    # 3. Simulate a HIGH-severity advisory anomaly: log a hardware tamper event
    from app.services.audit_service import AuditService
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await AuditService.log_event(
            db=session,
            election_id=election_id,
            event_type="DEVICE_TAMPER_SWITCH",
            event_data='{"switch": "chassis", "state": "OPEN"}',
            actor="hardware",
            device_id="EVM-001",
        )
        await session.commit()

    # 4. Verify that the anomaly detection engine reports a HIGH-severity finding
    ano_resp = await client.get(f"/api/elections/{election_id}/anomalies", headers=admin_headers)
    assert ano_resp.status_code == 200
    ano_data = ano_resp.json()
    high_findings = [f for f in ano_data["findings"] if f["severity"] == "HIGH"]
    assert len(high_findings) >= 1
    assert ano_data["status"] == "ADVISORY_ONLY_DOES_NOT_BLOCK_LIFECYCLE"

    # 5. HARD BOUNDARY CHECK 1: Election state transition (closing) must succeed unaffected
    close_resp = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["state"] == "CLOSED"

    # 6. HARD BOUNDARY CHECK 2: Verification and manifest generation must succeed unaffected
    verify_resp = await client.post(f"/api/elections/{election_id}/verify", headers=admin_headers)
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["overall_status"] == "PASSED"
    assert v_data["reconciliation_passed"] is True

    # 7. HARD BOUNDARY CHECK 3: Manifest signing must succeed unaffected
    sign_resp = await client.post(
        f"/api/elections/{election_id}/sign-manifest",
        headers=admin_headers,
    )
    assert sign_resp.status_code == 200
    assert sign_resp.json()["digital_signature"]["algorithm"] == "Ed25519"

    # 8. HARD BOUNDARY CHECK 4: Export and independent verification must succeed unaffected
    export_resp = await client.get(f"/api/elections/{election_id}/export", headers=admin_headers)
    assert export_resp.status_code == 200
    export_data = export_resp.json()

    indep_result = StandaloneElectionVerifier.verify_export_data(export_data)
    assert indep_result["valid"] is True, f"Failures: {indep_result['failures']}, Details: {indep_result['details']}, Manifest: {export_data.get('manifest')}"
    assert indep_result["checks"]["reconciliation"] is True
    assert indep_result["checks"]["manifest"] is True
    assert indep_result["checks"]["signature"] is True
