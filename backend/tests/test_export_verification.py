"""
Integration test for SecureVOTE Machine-Verifiable Export and Independent Verifier.

Tests that an independent verifier can recompute:
1. Configuration hash
2. Audit hash chain
3. Raw ballot tallies and device counts
4. Zero-drift reconciliation
5. Result manifest and export integrity hash
SOLELY from the exported JSON file without database access.
"""

import hashlib
import json
import pytest
from httpx import AsyncClient


def verify_election_export(export_data: dict) -> dict:
    """
    Standalone independent verification engine.
    Requires NO database connection, NO ORM, and NO running server.
    Operates strictly on the exported JSON archive.
    """
    errors: list[str] = []
    checks_passed: list[str] = []

    # 1. Verify export archive envelope hash
    export_hash = export_data.get("export_hash")
    raw_payload = {k: v for k, v in export_data.items() if k != "export_hash"}
    canonical_export = json.dumps(raw_payload, sort_keys=True)
    computed_export_hash = hashlib.sha256(canonical_export.encode("utf-8")).hexdigest()

    if export_hash == computed_export_hash:
        checks_passed.append("Export envelope hash matches canonical JSON.")
    else:
        errors.append(
            f"EXPORT_HASH_MISMATCH: stored={export_hash}, computed={computed_export_hash}"
        )

    # 2. Verify configuration hash from raw candidates
    election = export_data.get("election", {})
    candidates = export_data.get("candidates", [])
    sorted_candidates = sorted(candidates, key=lambda c: c["position"])

    canonical_candidate_list = [
        {
            "id": c["id"],
            "name": c["name"],
            "party": c.get("party") or "",
            "symbol": c.get("symbol") or "",
            "position": c["position"],
        }
        for c in sorted_candidates
    ]

    canonical_config = {
        "election_id": election.get("id"),
        "candidates": canonical_candidate_list,
    }
    canonical_config_json = json.dumps(canonical_config, sort_keys=True, separators=(",", ":"))
    computed_config_hash = hashlib.sha256(canonical_config_json.encode("utf-8")).hexdigest()

    stored_config_hash = election.get("configuration_hash")
    if stored_config_hash == computed_config_hash:
        checks_passed.append(f"Configuration hash verified ({computed_config_hash[:12]}...).")
    else:
        errors.append(
            f"CONFIG_HASH_MISMATCH: stored={stored_config_hash}, computed={computed_config_hash}"
        )

    # 3. Verify audit log hash chain
    audit_log = export_data.get("audit_log", [])
    sorted_audit = sorted(audit_log, key=lambda a: a["sequence_number"])
    audit_chain_valid = True

    for i, entry in enumerate(sorted_audit):
        expected_seq = i + 1
        if entry["sequence_number"] != expected_seq:
            errors.append(
                f"AUDIT_SEQ_BREAK: expected {expected_seq}, got {entry['sequence_number']}"
            )
            audit_chain_valid = False

        expected_prev = sorted_audit[i - 1]["entry_hash"] if i > 0 else None
        if entry["previous_hash"] != expected_prev:
            errors.append(
                f"AUDIT_PREV_HASH_MISMATCH at seq {entry['sequence_number']}: "
                f"expected={expected_prev}, actual={entry['previous_hash']}"
            )
            audit_chain_valid = False

        # Format ISO timestamp canonically in UTC
        ts = entry["timestamp"]
        # Audit entry hash formula: sequence_number|event_type|event_data|timestamp_iso|previous_hash
        components = [
            str(entry["sequence_number"]),
            entry["event_type"],
            entry["event_data"] or "",
            ts,
            entry["previous_hash"] or "GENESIS",
        ]
        hash_input = "|".join(components)
        recomputed_entry_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        if entry["entry_hash"] != recomputed_entry_hash:
            errors.append(
                f"AUDIT_ENTRY_HASH_MISMATCH at seq {entry['sequence_number']}: "
                f"stored={entry['entry_hash']}, computed={recomputed_entry_hash}"
            )
            audit_chain_valid = False


    if audit_chain_valid and len(sorted_audit) > 0:
        checks_passed.append(f"Audit log hash chain verified ({len(sorted_audit)} entries intact).")

    # 4. Recompute raw ballot counts and verify per-device sequence numbers
    ballots = export_data.get("ballots", [])
    devices = export_data.get("devices", [])

    candidate_tallies: dict[str, int] = {c["id"]: 0 for c in candidates}
    device_tallies: dict[str, int] = {d["id"]: 0 for d in devices}
    device_last_seq: dict[str, int] = {d["id"]: 0 for d in devices}

    for b in ballots:
        cid = b["candidate_id"]
        did = b["device_id"]
        seq = b["sequence_number"]

        if cid in candidate_tallies:
            candidate_tallies[cid] += 1
        else:
            errors.append(f"UNKNOWN_CANDIDATE_IN_BALLOT: {cid}")

        if did in device_tallies:
            device_tallies[did] += 1
            if seq <= device_last_seq[did]:
                errors.append(
                    f"REPLAY_SEQUENCE_DETECTED for device {did}: seq {seq} <= last {device_last_seq[did]}"
                )
            device_last_seq[did] = seq
        else:
            errors.append(f"UNKNOWN_DEVICE_IN_BALLOT: {did}")

    total_ballots = len(ballots)
    sum_candidates = sum(candidate_tallies.values())
    sum_devices = sum(device_tallies.values())

    # 5. Exact zero-drift reconciliation
    drift = abs(sum_candidates - total_ballots) + abs(sum_devices - total_ballots)
    if drift == 0 and sum_candidates == total_ballots:
        checks_passed.append(
            f"Zero-drift reconciliation verified: "
            f"sum(candidates)={sum_candidates} == total_ballots={total_ballots} == sum(devices)={sum_devices}."
        )
    else:
        errors.append(
            f"RECONCILIATION_DRIFT: sum(candidates)={sum_candidates}, "
            f"total_ballots={total_ballots}, sum(devices)={sum_devices}, drift={drift}"
        )

    # 6. Verify result manifest if present
    manifest = export_data.get("manifest")
    if manifest:
        manifest_cand_totals = json.loads(manifest["candidate_totals"])
        if manifest_cand_totals == candidate_tallies:
            checks_passed.append("Manifest candidate tallies match independent recount.")
        else:
            errors.append("MANIFEST_TALLY_MISMATCH: manifest tallies do not match recount.")

        if manifest["total_ballots"] == total_ballots:
            checks_passed.append("Manifest total ballots match independent recount.")
        else:
            errors.append("MANIFEST_BALLOT_COUNT_MISMATCH")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "checks_passed": checks_passed,
        "recounted_tallies": candidate_tallies,
        "total_ballots": total_ballots,
        "drift": drift,
    }


async def _setup_test_election_and_export(client: AsyncClient, admin_token: str, election_id: str) -> dict:
    """Helper to set up a full election, cast votes on multiple devices, and export."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create election
    res = await client.post(
        "/api/elections",
        json={"id": election_id, "name": f"Export Integrity {election_id}"},
        headers=headers,
    )
    assert res.status_code == 201

    # 2. Add candidates
    res = await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Alice Green", "party": "Forward", "symbol": "Tree", "position": 1},
                {"id": "C002", "name": "Bob Blue", "party": "Unity", "symbol": "Anchor", "position": 2},
            ]
        },
        headers=headers,
    )
    assert res.status_code == 201

    # 3. Register devices with valid ID pattern ^EVM-\d{3}$
    res1 = await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-091", "name": "Export Station 1"},
        headers=headers,
    )
    assert res1.status_code == 201

    res2 = await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-092", "name": "Export Station 2"},
        headers=headers,
    )
    assert res2.status_code == 201

    # 4. Lock configuration
    res = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "LOCKED", "reason": "Config locked"},
        headers=headers,
    )
    assert res.status_code == 200

    # 5. Activate devices
    act1 = await client.patch(
        f"/api/elections/{election_id}/devices/EVM-091/status",
        json={"status": "ACTIVE"},
        headers=headers,
    )
    assert act1.status_code == 200

    act2 = await client.patch(
        f"/api/elections/{election_id}/devices/EVM-092/status",
        json={"status": "ACTIVE"},
        headers=headers,
    )
    assert act2.status_code == 200

    # 6. Open election
    res = await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN", "reason": "Polls open"},
        headers=headers,
    )
    assert res.status_code == 200

    # 7. Cast votes on EVM-091
    for i, cid in enumerate(["C001", "C002", "C001"], start=1):
        s_res = await client.post(
            f"/api/elections/{election_id}/sessions",
            json={"device_id": "EVM-091", "voter_credential": f"VOTER-EXP-1-{i}-{election_id}"},
            headers=headers,
        )
        assert s_res.status_code == 201
        token = s_res.json()["session_token"]
        v_res = await client.post(
            "/api/votes",
            json={"session_token": token, "device_id": "EVM-091", "candidate_id": cid, "sequence_number": i},
            headers=headers,
        )
        assert v_res.status_code == 201

    # 8. Cast votes on EVM-092
    for i, cid in enumerate(["C002", "C002"], start=1):
        s_res = await client.post(
            f"/api/elections/{election_id}/sessions",
            json={"device_id": "EVM-092", "voter_credential": f"VOTER-EXP-2-{i}-{election_id}"},
            headers=headers,
        )
        assert s_res.status_code == 201
        token = s_res.json()["session_token"]
        v_res = await client.post(
            "/api/votes",
            json={"session_token": token, "device_id": "EVM-092", "candidate_id": cid, "sequence_number": i},
            headers=headers,
        )
        assert v_res.status_code == 201


    # 9. Close and verify
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED", "reason": "Polls closed"},
        headers=headers,
    )
    await client.post(f"/api/elections/{election_id}/verify", headers=headers)

    # 10. Fetch export archive
    export_res = await client.get(f"/api/elections/{election_id}/export", headers=headers)
    assert export_res.status_code == 200
    return export_res.json()


@pytest.mark.asyncio
async def test_export_independent_verification_passes(client: AsyncClient, admin_token: str):
    """
    Integration test: Creates election, casts votes, closes, exports archive,
    and runs independent verification solely on the exported JSON.
    """
    export_data = await _setup_test_election_and_export(client, admin_token, "EV-2026-901")

    # Run independent verification on the export data
    report = verify_election_export(export_data)
    assert report["is_valid"] is True, f"Independent verification failed: {report['errors']}"
    assert report["total_ballots"] == 5
    assert report["recounted_tallies"]["C001"] == 2
    assert report["recounted_tallies"]["C002"] == 3
    assert report["drift"] == 0


@pytest.mark.asyncio
async def test_export_detects_tampered_ballot(client: AsyncClient, admin_token: str):
    """Tampering with a ballot in the exported JSON is caught by independent verifier."""
    export_data = await _setup_test_election_and_export(client, admin_token, "EV-2026-902")

    # Tamper with the first ballot's candidate
    export_data["ballots"][0]["candidate_id"] = "C002"

    report = verify_election_export(export_data)
    # Recomputed tallies no longer match the manifest's candidate totals
    assert report["is_valid"] is False
    assert any("EXPORT_HASH_MISMATCH" in e or "MANIFEST_TALLY_MISMATCH" in e for e in report["errors"])


@pytest.mark.asyncio
async def test_export_detects_tampered_audit_chain(client: AsyncClient, admin_token: str):
    """Tampering with an audit entry in the exported JSON is caught by independent verifier."""
    export_data = await _setup_test_election_and_export(client, admin_token, "EV-2026-903")

    # Tamper with an audit entry's event_type
    export_data["audit_log"][1]["event_type"] = "MALICIOUS_EVENT"

    report = verify_election_export(export_data)
    assert report["is_valid"] is False
    assert any("AUDIT_ENTRY_HASH_MISMATCH" in e for e in report["errors"])
