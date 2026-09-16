"""
Multi-Device Concurrent Aggregation & Isolation Test for SecureVOTE.

Tests:
1. Concurrent, interleaved voting across multiple physical/simulated EVM units
   (EVM-001, EVM-002, EVM-003, EVM-004).
2. Independent sequence number counters per device (no cross-device collision).
3. Selective device isolation/suspension (suspending EVM-003 does not impact
   EVM-001, EVM-002, or EVM-004).
4. Full multi-device aggregation and exact zero-drift reconciliation.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_multi_device_concurrent_voting_and_aggregation(client: AsyncClient, admin_token: str):
    """
    Test interleaved voting across 4 EVM devices, proving independent sequence
    counters, per-device totals aggregation, and zero-drift reconciliation.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    election_id = "EV-2026-801"

    # 1. Create election
    res = await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Multi-Device Aggregation Election"},
        headers=headers,
    )
    assert res.status_code == 201

    # 2. Add candidates
    res = await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Candidate One", "party": "Party Alpha", "symbol": "Sun", "position": 1},
                {"id": "C002", "name": "Candidate Two", "party": "Party Beta", "symbol": "Moon", "position": 2},
                {"id": "C003", "name": "Candidate Three", "party": "Party Gamma", "symbol": "Star", "position": 3},
            ]
        },
        headers=headers,
    )
    assert res.status_code == 201

    # 3. Register 4 EVM devices
    devices = ["EVM-001", "EVM-002", "EVM-003", "EVM-004"]
    for dev_id in devices:
        r = await client.post(
            f"/api/elections/{election_id}/devices",
            json={"id": dev_id, "name": f"Station {dev_id}"},
            headers=headers,
        )
        assert r.status_code == 201

    # 4. Lock configuration
    res = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "LOCKED", "reason": "Config frozen"},
        headers=headers,
    )
    assert res.status_code == 200

    # 5. Activate all 4 devices
    for dev_id in devices:
        r = await client.patch(
            f"/api/elections/{election_id}/devices/{dev_id}/status",
            json={"status": "ACTIVE"},
            headers=headers,
        )
        assert r.status_code == 200

    # 6. Open election
    res = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN", "reason": "Polls open"},
        headers=headers,
    )
    assert res.status_code == 200

    # 7. Interleaved voting across devices
    # Define vote plan: (device_id, candidate_id)
    # EVM-001: 4 votes (C001, C002, C001, C003)
    # EVM-002: 3 votes (C002, C002, C003)
    # EVM-003: 3 votes (C003, C001, C002)
    # EVM-004: 2 votes (C001, C003)
    # Total = 12 votes
    interleaved_schedule = [
        ("EVM-001", "C001"),
        ("EVM-002", "C002"),
        ("EVM-003", "C003"),
        ("EVM-004", "C001"),
        ("EVM-001", "C002"),
        ("EVM-003", "C001"),
        ("EVM-002", "C002"),
        ("EVM-001", "C001"),
        ("EVM-004", "C003"),
        ("EVM-003", "C002"),
        ("EVM-002", "C003"),
        ("EVM-001", "C003"),
    ]

    device_sequence_trackers = {d: 0 for d in devices}
    expected_device_counts = {d: 0 for d in devices}
    expected_cand_counts = {"C001": 0, "C002": 0, "C003": 0}

    for voter_idx, (dev_id, cand_id) in enumerate(interleaved_schedule, start=1):
        device_sequence_trackers[dev_id] += 1
        seq = device_sequence_trackers[dev_id]

        # Authorize session for this voter & device
        s_res = await client.post(
            f"/api/elections/{election_id}/sessions",
            json={"device_id": dev_id, "voter_credential": f"VOTER-MDEV-{voter_idx}"},
            headers=headers,
        )
        assert s_res.status_code == 201
        token = s_res.json()["session_token"]

        # Cast ballot
        v_res = await client.post(
            "/api/votes",
            json={"session_token": token, "device_id": dev_id, "candidate_id": cand_id, "sequence_number": seq},
            headers=headers,
        )
        assert v_res.status_code == 201

        expected_device_counts[dev_id] += 1
        expected_cand_counts[cand_id] += 1

    # 8. Verify independent sequence numbers & replay rejection
    # Attempting to replay sequence 1 on EVM-001 MUST be rejected
    s_replay = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"device_id": "EVM-001", "voter_credential": "VOTER-REPLAY-ATTEMPT"},
        headers=headers,
    )
    assert s_replay.status_code == 201
    replay_token = s_replay.json()["session_token"]

    bad_vote = await client.post(
        "/api/votes",
        json={"session_token": replay_token, "device_id": "EVM-001", "candidate_id": "C001", "sequence_number": 1},
        headers=headers,
    )
    assert bad_vote.status_code == 409
    assert "REPLAY REJECTED" in bad_vote.json()["detail"]

    # 9. Selective Device Isolation / Suspension
    # Suspend EVM-003
    susp_res = await client.patch(
        f"/api/elections/{election_id}/devices/EVM-003/status",
        json={"status": "SUSPENDED"},
        headers=headers,
    )
    assert susp_res.status_code == 200

    # New session on suspended EVM-003 must be rejected
    blocked_res = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"device_id": "EVM-003", "voter_credential": "VOTER-ON-SUSPENDED"},
        headers=headers,
    )
    assert blocked_res.status_code == 403
    assert "DEVICE REJECTED" in blocked_res.json()["detail"]

    # Active devices continue voting uninhibited
    s_active = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"device_id": "EVM-001", "voter_credential": "VOTER-AFTER-SUSP-1"},
        headers=headers,
    )
    assert s_active.status_code == 201
    token_active = s_active.json()["session_token"]

    device_sequence_trackers["EVM-001"] += 1
    v_active = await client.post(
        "/api/votes",
        json={
            "session_token": token_active,
            "device_id": "EVM-001",
            "candidate_id": "C001",
            "sequence_number": device_sequence_trackers["EVM-001"],
        },
        headers=headers,
    )
    assert v_active.status_code == 201
    expected_device_counts["EVM-001"] += 1
    expected_cand_counts["C001"] += 1

    # Reactivate EVM-003 and ensure it resumes with monotonic sequence
    react_res = await client.patch(
        f"/api/elections/{election_id}/devices/EVM-003/status",
        json={"status": "ACTIVE"},
        headers=headers,
    )
    assert react_res.status_code == 200

    s_resumed = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"device_id": "EVM-003", "voter_credential": "VOTER-RESUMED-1"},
        headers=headers,
    )
    assert s_resumed.status_code == 201
    token_resumed = s_resumed.json()["session_token"]

    device_sequence_trackers["EVM-003"] += 1
    v_resumed = await client.post(
        "/api/votes",
        json={
            "session_token": token_resumed,
            "device_id": "EVM-003",
            "candidate_id": "C002",
            "sequence_number": device_sequence_trackers["EVM-003"],
        },
        headers=headers,
    )
    assert v_resumed.status_code == 201
    expected_device_counts["EVM-003"] += 1
    expected_cand_counts["C002"] += 1

    # Total votes = 12 initial + 1 on EVM-001 + 1 on EVM-003 = 14
    total_expected = 14

    # 10. Close and run independent verification
    close_res = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED", "reason": "Polls officially closed"},
        headers=headers,
    )
    assert close_res.status_code == 200

    verify_res = await client.post(f"/api/elections/{election_id}/verify", headers=headers)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()

    assert verify_data["overall_status"] == "PASSED"
    assert verify_data["config_hash_valid"] is True
    assert verify_data["audit_chain_intact"] is True
    assert verify_data["reconciliation_passed"] is True
    assert verify_data["tally_independently_verified"] is True

    manifest = verify_data["manifest"]
    assert manifest["total_ballots"] == total_expected

    # Verify per-device breakdown
    dev_results = {d["device_id"]: d["ballot_count"] for d in manifest["device_results"]}
    for d, expected_cnt in expected_device_counts.items():
        assert dev_results[d] == expected_cnt, f"Device {d} count mismatch: expected {expected_cnt}, got {dev_results[d]}"

    # Verify per-candidate breakdown
    cand_results = {c["candidate_id"]: c["vote_count"] for c in manifest["candidate_results"]}
    for c, expected_cnt in expected_cand_counts.items():
        assert cand_results[c] == expected_cnt, f"Candidate {c} count mismatch: expected {expected_cnt}, got {cand_results[c]}"

    # Verify zero-drift reconciliation
    recon = manifest["reconciliation"]
    assert recon["is_exact_match"] is True
    assert recon["total_ballots"] == total_expected
    assert recon["sum_candidate_totals"] == total_expected
    assert recon["sum_device_totals"] == total_expected

