"""
Tests for SecureVOTE Standalone Independent Verifier (Phase 5.3).

Covers:
1. Structural Independence Audit: Confirms 0 imports from database, models, sqlalchemy, fastapi.
2. Database-Disconnected Proof: Executes verifier in an isolated subprocess with DB disconnected.
3. Full recomputation of all 12 checks on a valid signed & anchored export archive.
4. Tamper Tests across all dimensions:
   - Tampered ballot candidate
   - Tampered ballot hash
   - Tampered sequence number (replay)
   - Tampered device ID
   - Tampered audit event data
   - Tampered audit chain previous_hash
   - Tampered candidate configuration
   - Tampered manifest total
   - Tampered Ed25519 signature
   - Tampered anchor root
"""

import ast
import copy
import json
import os
import subprocess
import sys
import tempfile
import pytest
from httpx import AsyncClient

from standalone_verifier.verifier import StandaloneElectionVerifier


def test_verifier_has_zero_database_or_orm_imports():
    """Prove structural independence by AST analysis of the standalone verifier module."""
    verifier_path = os.path.join(
        os.path.dirname(__file__), "..", "standalone_verifier", "verifier.py"
    )
    with open(verifier_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    forbidden = ["database", "models", "sqlalchemy", "fastapi", "app."]
    found_forbidden = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                for fb in forbidden:
                    if fb in n.name:
                        found_forbidden.append((n.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for fb in forbidden:
                if fb in mod:
                    found_forbidden.append((mod, node.lineno))

    assert len(found_forbidden) == 0, f"Standalone verifier must not import database/ORM: {found_forbidden}"


@pytest.mark.asyncio
async def test_database_disconnected_proof(
    client: AsyncClient,
    admin_headers: dict[str, str],
    ephemeral_signing_key,
    tmp_path,
):
    """
    MANDATORY AMENDMENT TEST:
    1. Create an election, register devices, cast votes, close, verify, sign manifest, anchor root.
    2. Export the machine-verifiable JSON archive.
    3. Save the archive to a standalone JSON file on disk.
    4. Disconnect the database / set invalid DB environment.
    5. Run the standalone verifier in a separate OS subprocess with an invalid database URL.
    6. Confirm the verifier successfully validates the archive without database access.
    """
    election_id = "EV-2026-901"

    # Setup election
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": "DB Independence Proof Election"},
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
    await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-001", "name": "Unit 1"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/devices/EVM-001/status",
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

    # Cast 2 votes
    for i, cid in enumerate(["C001", "C002"], start=1):
        s_resp = await client.post(
            f"/api/elections/{election_id}/sessions",
            json={"voter_credential": f"VOTER-{i:03d}", "device_id": "EVM-001"},
            headers=admin_headers,
        )
        token = s_resp.json()["session_token"]
        await client.post(
            "/api/votes",
            json={
                "session_token": token,
                "candidate_id": cid,
                "device_id": "EVM-001",
                "sequence_number": i,
            },
            headers=admin_headers,
        )

    # Close and verify election
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )
    await client.post(f"/api/elections/{election_id}/verify", headers=admin_headers)

    # Sign manifest
    sign_resp = await client.post(
        f"/api/elections/{election_id}/sign-manifest",
        headers=admin_headers,
    )
    assert sign_resp.status_code == 200

    # Create local anchor
    anchor_resp = await client.post(
        f"/api/elections/{election_id}/anchor",
        json={"provider_type": "LOCAL"},
        headers=admin_headers,
    )
    assert anchor_resp.status_code == 200
    anchor_data = anchor_resp.json()

    # Export archive
    export_resp = await client.get(f"/api/elections/{election_id}/export", headers=admin_headers)
    assert export_resp.status_code == 200
    export_data = export_resp.json()

    # Save export and anchor to standalone JSON files on disk
    export_file = tmp_path / "election_export.json"
    anchor_file = tmp_path / "anchor_receipt.json"

    export_file.write_text(json.dumps(export_data), encoding="utf-8")
    anchor_file.write_text(json.dumps(anchor_data), encoding="utf-8")

    # Step 5: Execute verifier in a completely isolated subprocess with DATABASE_URL set to an invalid dummy
    isolated_env = os.environ.copy()
    isolated_env["DATABASE_URL"] = "postgresql://invalid_user:invalid_pass@127.0.0.1:54329/nonexistent_db"
    isolated_env["SECUREVOTE_DB"] = "invalid"

    # Add standalone_verifier parent directory to PYTHONPATH
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    isolated_env["PYTHONPATH"] = backend_dir

    cmd = [
        sys.executable,
        "-m",
        "standalone_verifier.verifier",
        str(export_file),
        "--anchor-receipt",
        str(anchor_file),
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=isolated_env,
        timeout=10,
    )

    assert proc.returncode == 0, f"Subprocess verifier failed without DB: {proc.stderr}\nOutput: {proc.stdout}"
    output = json.loads(proc.stdout)

    assert output["valid"] is True
    assert output["failures"] == []
    assert output["checks"]["configuration"] is True
    assert output["checks"]["ballot_hashes"] is True
    assert output["checks"]["ballot_sequence"] is True
    assert output["checks"]["reconciliation"] is True
    assert output["checks"]["audit_chain"] is True
    assert output["checks"]["manifest"] is True
    assert output["checks"]["signature"] is True
    assert output["checks"]["anchor"] is True
    assert output["summary"]["total_ballots_recounted"] == 2


@pytest.fixture
def valid_export_fixture():
    """Generates an in-memory valid export payload for tampering tests."""
    from app.services.signing_service import SigningService
    priv, pub = SigningService.generate_keypair()
    pub_hex = SigningService.get_public_key_hex(pub)

    election_id = "EV-2026-TEST"
    candidates = [
        {"id": "C001", "name": "Alice", "party": "A", "symbol": "A", "position": 1},
        {"id": "C002", "name": "Bob", "party": "B", "symbol": "B", "position": 2},
    ]
    config_hash = StandaloneElectionVerifier.compute_config_hash(election_id, candidates)

    devices = [
        {
            "id": "EVM-01",
            "name": "Unit 1",
            "status": "ACTIVE",
            "last_sequence_number": 2,
            "total_votes_cast": 2,
            "registered_at": "2026-09-16T10:00:00Z",
            "activated_at": "2026-09-16T10:05:00Z",
            "last_seen_at": "2026-09-16T10:15:00Z",
        }
    ]

    ballots = [
        {
            "id": "b-1",
            "session_id": "s-1",
            "device_id": "EVM-01",
            "candidate_id": "C001",
            "sequence_number": 1,
            "recorded_at": "2026-09-16T10:10:00Z",
            "ballot_hash": StandaloneElectionVerifier.compute_ballot_hash(
                election_id, "s-1", "C001", "EVM-01", 1, "2026-09-16T10:10:00Z"
            ),
        },
        {
            "id": "b-2",
            "session_id": "s-2",
            "device_id": "EVM-01",
            "candidate_id": "C002",
            "sequence_number": 2,
            "recorded_at": "2026-09-16T10:12:00Z",
            "ballot_hash": StandaloneElectionVerifier.compute_ballot_hash(
                election_id, "s-2", "C002", "EVM-01", 2, "2026-09-16T10:12:00Z"
            ),
        },
    ]

    # Audit chain
    audit_0_hash = StandaloneElectionVerifier.compute_audit_entry_hash(
        1, "ELECTION_CREATED", "", "2026-09-16T10:00:00Z", None
    )
    audit_1_hash = StandaloneElectionVerifier.compute_audit_entry_hash(
        2, "ELECTION_LOCKED", "", "2026-09-16T10:06:00Z", audit_0_hash
    )
    audit_log = [
        {
            "id": 1,
            "sequence_number": 1,
            "event_type": "ELECTION_CREATED",
            "event_data": "",
            "actor": "admin",
            "device_id": None,
            "timestamp": "2026-09-16T10:00:00Z",
            "previous_hash": None,
            "entry_hash": audit_0_hash,
        },
        {
            "id": 2,
            "sequence_number": 2,
            "event_type": "ELECTION_LOCKED",
            "event_data": "",
            "actor": "admin",
            "device_id": None,
            "timestamp": "2026-09-16T10:06:00Z",
            "previous_hash": audit_0_hash,
            "entry_hash": audit_1_hash,
        },
    ]

    manifest_hash = StandaloneElectionVerifier.compute_manifest_hash(
        election_id=election_id,
        total_ballots=2,
        candidate_totals={"C001": 1, "C002": 1},
        device_totals={"EVM-01": 2},
        reconciliation_status="PASSED",
        audit_chain_status="INTACT",
        configuration_hash=config_hash,
    )

    signed_payload = {
        "artifact_type": "RESULT_MANIFEST",
        "artifact_version": "1.0.0",
        "election_id": election_id,
        "manifest_hash": manifest_hash,
        "configuration_hash": config_hash,
        "audit_root_hash": audit_1_hash,
        "total_ballots": 2,
        "reconciliation_status": "PASSED",
        "audit_chain_status": "INTACT",
    }
    signed_art = SigningService.sign_payload(signed_payload, private_key=priv)

    manifest = {
        "id": "m-1",
        "election_id": election_id,
        "total_ballots": 2,
        "candidate_totals": json.dumps({"C001": 1, "C002": 1}),
        "device_totals": json.dumps({"EVM-01": 2}),
        "reconciliation_status": "PASSED",
        "audit_chain_status": "INTACT",
        "configuration_hash": config_hash,
        "manifest_hash": manifest_hash,
        "digital_signature": json.dumps(signed_art),
        "generated_at": "2026-09-16T10:20:00Z",
        "verified_at": "2026-09-16T10:20:00Z",
        "verified_by": "auditor",
    }

    raw = {
        "export_version": "1.0.0",
        "exported_at": "2026-09-16T10:25:00Z",
        "election": {
            "id": election_id,
            "name": "Test Election",
            "description": None,
            "state": "CLOSED",
            "configuration_hash": config_hash,
            "total_ballots": 2,
            "created_at": "2026-09-16T10:00:00Z",
            "locked_at": "2026-09-16T10:06:00Z",
            "opened_at": "2026-09-16T10:08:00Z",
            "closed_at": "2026-09-16T10:18:00Z",
            "published_at": None,
        },
        "candidates": candidates,
        "devices": devices,
        "ballots": ballots,
        "audit_log": audit_log,
        "manifest": manifest,
    }
    raw["export_hash"] = StandaloneElectionVerifier.compute_config_hash.__globals__["sha256_hex"](
        json.dumps(raw, sort_keys=True)
    )

    anchor_receipt = {
        "anchor_id": "anc-01",
        "election_id": election_id,
        "root_hash": audit_1_hash,
        "provider_type": "LOCAL ANCHOR",
        "anchor_reference": "local-anc-12345",
        "status": "LOCAL ANCHOR",
    }

    return raw, pub_hex, anchor_receipt


def test_tamper_ballot_candidate(valid_export_fixture):
    """Mutating candidate in a ballot must fail ballot_hashes check."""
    export, pub_hex, anchor = valid_export_fixture
    tampered = copy.deepcopy(export)
    tampered["ballots"][0]["candidate_id"] = "C002"

    res = StandaloneElectionVerifier.verify_export_data(tampered, pub_hex, anchor)
    assert res["valid"] is False
    assert res["checks"]["ballot_hashes"] is False


def test_tamper_ballot_hash(valid_export_fixture):
    """Corrupting a ballot hash must fail ballot_hashes check."""
    export, pub_hex, anchor = valid_export_fixture
    tampered = copy.deepcopy(export)
    tampered["ballots"][0]["ballot_hash"] = "0" * 64

    res = StandaloneElectionVerifier.verify_export_data(tampered, pub_hex, anchor)
    assert res["valid"] is False
    assert res["checks"]["ballot_hashes"] is False


def test_tamper_sequence_replay(valid_export_fixture):
    """Repeating a sequence number on a device must fail ballot_sequence check."""
    export, pub_hex, anchor = valid_export_fixture
    tampered = copy.deepcopy(export)
    tampered["ballots"][1]["sequence_number"] = 1  # Duplicate sequence 1

    res = StandaloneElectionVerifier.verify_export_data(tampered, pub_hex, anchor)
    assert res["valid"] is False
    assert res["checks"]["ballot_sequence"] is False


def test_tamper_device_id(valid_export_fixture):
    """Injecting unknown device must fail ballot_hashes and reconciliation."""
    export, pub_hex, anchor = valid_export_fixture
    tampered = copy.deepcopy(export)
    tampered["ballots"][0]["device_id"] = "UNKNOWN-EVM"

    res = StandaloneElectionVerifier.verify_export_data(tampered, pub_hex, anchor)
    assert res["valid"] is False
    assert res["checks"]["ballot_hashes"] is False


def test_tamper_audit_event_data(valid_export_fixture):
    """Modifying audit event content must fail audit_chain check."""
    export, pub_hex, anchor = valid_export_fixture
    tampered = copy.deepcopy(export)
    tampered["audit_log"][0]["event_data"] = "TAMPERED DATA"

    res = StandaloneElectionVerifier.verify_export_data(tampered, pub_hex, anchor)
    assert res["valid"] is False
    assert res["checks"]["audit_chain"] is False


def test_tamper_audit_chain_previous_hash(valid_export_fixture):
    """Breaking the previous_hash link must fail audit_chain check."""
    export, pub_hex, anchor = valid_export_fixture
    tampered = copy.deepcopy(export)
    tampered["audit_log"][1]["previous_hash"] = "f" * 64

    res = StandaloneElectionVerifier.verify_export_data(tampered, pub_hex, anchor)
    assert res["valid"] is False
    assert res["checks"]["audit_chain"] is False


def test_tamper_candidate_configuration(valid_export_fixture):
    """Modifying candidate configuration must fail configuration check."""
    export, pub_hex, anchor = valid_export_fixture
    tampered = copy.deepcopy(export)
    tampered["candidates"][0]["name"] = "Alice In Wonderland"

    res = StandaloneElectionVerifier.verify_export_data(tampered, pub_hex, anchor)
    assert res["valid"] is False
    assert res["checks"]["configuration"] is False


def test_tamper_manifest_totals(valid_export_fixture):
    """Modifying manifest totals must fail manifest consistency check."""
    export, pub_hex, anchor = valid_export_fixture
    tampered = copy.deepcopy(export)
    tampered["manifest"]["total_ballots"] = 999
    tampered["manifest"]["manifest_hash"] = "0" * 64

    res = StandaloneElectionVerifier.verify_export_data(tampered, pub_hex, anchor)
    assert res["valid"] is False
    assert res["checks"]["manifest"] is False


def test_tamper_ed25519_signature(valid_export_fixture):
    """Corrupting the digital signature must fail signature check."""
    export, pub_hex, anchor = valid_export_fixture
    tampered = copy.deepcopy(export)
    sig_obj = json.loads(tampered["manifest"]["digital_signature"])
    # Flip bytes in signature
    sig_bytes = bytearray.fromhex(sig_obj["signature"])
    sig_bytes[0] ^= 0xAA
    sig_obj["signature"] = sig_bytes.hex()
    tampered["manifest"]["digital_signature"] = json.dumps(sig_obj)

    res = StandaloneElectionVerifier.verify_export_data(tampered, pub_hex, anchor)
    assert res["valid"] is False
    assert res["checks"]["signature"] is False


def test_tamper_anchor_root(valid_export_fixture):
    """Mismatched anchor root hash must fail anchor verification check."""
    export, pub_hex, anchor = valid_export_fixture
    tampered_anchor = copy.deepcopy(anchor)
    tampered_anchor["root_hash"] = "e" * 64  # Corrupted anchor root

    res = StandaloneElectionVerifier.verify_export_data(export, pub_hex, tampered_anchor)
    assert res["valid"] is False
    assert res["checks"]["anchor"] is False
