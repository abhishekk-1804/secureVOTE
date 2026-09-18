"""
Unit and Integration Tests for SecureVOTE 2.0 Ecosystem Extensions.

Covers:
1. Synthetic voter registration and unique constraint.
2. Deterministic eligibility simulation engine.
3. Voter lookup endpoint.
4. Polling station management lifecycle.
5. Citizen grievance / complaint submission, tracking, and status transitions.
6. Public transparency endpoints (unauthenticated access, safe aggregates).
7. Deterministic simulation preset execution.
8. Role-based access control (RBAC) enforcement on administrative endpoints.
"""

import json
import pytest
from httpx import AsyncClient


async def _create_test_election(client: AsyncClient, admin_headers: dict, election_id: str = "EV-2026-901"):
    """Helper to create an election."""
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": f"Ecosystem Test Election {election_id}"},
        headers=admin_headers,
    )
    return election_id


# ===========================================================================
# 1. Voter Registration & Lookup
# ===========================================================================

@pytest.mark.asyncio
async def test_voter_registration_and_lookup(client: AsyncClient, admin_headers: dict):
    """Test registering synthetic voters and looking them up."""
    election_id = await _create_test_election(client, admin_headers, "EV-2026-902")

    # Register voter
    reg_resp = await client.post(
        f"/api/elections/{election_id}/voters",
        json={
            "name": "Devi Rao",
            "date_of_birth": "1995-08-14",
            "constituency": "North District",
        },
        headers=admin_headers,
    )
    assert reg_resp.status_code == 201
    voter_data = reg_resp.json()
    assert voter_data["name"] == "Devi Rao"
    assert voter_data["voter_id_number"].startswith("VTR-")
    assert voter_data["eligibility_status"] == "PENDING"
    assert voter_data["has_voted"] is False

    # Lookup by voter ID (public endpoint)
    voter_id = voter_data["voter_id_number"]
    lookup_resp = await client.get(
        f"/api/elections/{election_id}/voter-lookup?voter_id_number={voter_id}"
    )
    assert lookup_resp.status_code == 200
    assert lookup_resp.json()["name"] == "Devi Rao"

    # Lookup non-existent voter returns 404
    bad_lookup = await client.get(
        f"/api/elections/{election_id}/voter-lookup?voter_id_number=VTR-99999"
    )
    assert bad_lookup.status_code == 404


# ===========================================================================
# 2. Eligibility Simulation Engine
# ===========================================================================

@pytest.mark.asyncio
async def test_eligibility_engine_rules(client: AsyncClient, admin_headers: dict):
    """Test deterministic synthetic eligibility evaluation."""
    election_id = await _create_test_election(client, admin_headers, "EV-2026-903")

    # Adult voter (>= 18) -> ELIGIBLE
    adult_resp = await client.post(
        f"/api/elections/{election_id}/eligibility",
        json={
            "name": "Suresh Raina",
            "date_of_birth": "2000-01-01",
            "constituency": "Central District",
        },
    )
    assert adult_resp.status_code == 200
    assert adult_resp.json()["status"] == "ELIGIBLE"
    assert "All checks passed" in adult_resp.json()["reasons"][0]

    # Minor voter (< 16) -> NOT_ELIGIBLE
    minor_resp = await client.post(
        f"/api/elections/{election_id}/eligibility",
        json={
            "name": "Young Voter",
            "date_of_birth": "2015-06-01",
            "constituency": "Central District",
        },
    )
    assert minor_resp.status_code == 200
    assert minor_resp.json()["status"] == "NOT_ELIGIBLE"

    # Boundary notice present
    assert "NOT A REAL GOVERNMENT SERVICE" in adult_resp.json()["notice"]


# ===========================================================================
# 3. Polling Stations Lifecycle
# ===========================================================================

@pytest.mark.asyncio
async def test_polling_station_crud(client: AsyncClient, admin_headers: dict):
    """Test creating, listing, and updating polling stations."""
    election_id = await _create_test_election(client, admin_headers, "EV-2026-904")

    # Create station
    create_resp = await client.post(
        f"/api/elections/{election_id}/polling-stations",
        json={
            "station_code": "PS-001",
            "name": "Civic Centre Booth A",
            "constituency": "North District",
            "location": "Municipal Hall Room 101",
            "officer_name": "Presiding Officer Das",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    station = create_resp.json()
    assert station["station_code"] == "PS-001"
    assert station["status"] == "SETUP"

    # List stations (public)
    list_resp = await client.get(f"/api/elections/{election_id}/polling-stations")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Update status
    patch_resp = await client.patch(
        f"/api/elections/{election_id}/polling-stations/{station['id']}/status",
        json={"status": "READY"},
        headers=admin_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "READY"


# ===========================================================================
# 4. Citizen Complaint / Grievance Management
# ===========================================================================

@pytest.mark.asyncio
async def test_complaint_workflow(client: AsyncClient, admin_headers: dict):
    """Test submitting complaint publicly, tracking it, and updating status."""
    election_id = await _create_test_election(client, admin_headers, "EV-2026-905")

    # Citizen submits complaint without auth
    sub_resp = await client.post(
        "/api/complaints",
        json={
            "election_id": election_id,
            "category": "ACCESSIBILITY",
            "description": "Wheelchair ramp at Booth A requires repair before polling day.",
            "complainant_name": "Citizen Rakesh",
            "complainant_contact": "rakesh@example.test",
        },
    )
    assert sub_resp.status_code == 201
    complaint = sub_resp.json()
    ref_num = complaint["reference_number"]
    assert ref_num.startswith("GRV-")
    assert complaint["status"] == "SUBMITTED"

    # Track complaint publicly by reference number
    track_resp = await client.get(f"/api/complaints/track/{ref_num}")
    assert track_resp.status_code == 200
    assert track_resp.json()["complainant_name"] == "Citizen Rakesh"

    # Officer updates complaint status
    cid = complaint["id"]
    update_resp = await client.patch(
        f"/api/complaints/{cid}/status",
        json={
            "status": "ASSIGNED",
            "assigned_officer": "Zonal Officer Singh",
            "resolution_notes": "Assigned to PWD team for prompt repair.",
        },
        headers=admin_headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "ASSIGNED"
    assert updated["assigned_officer"] == "Zonal Officer Singh"


# ===========================================================================
# 5. Public Transparency Endpoints
# ===========================================================================

@pytest.mark.asyncio
async def test_transparency_endpoints(client: AsyncClient, admin_headers: dict):
    """Transparency endpoints must be publicly accessible and return safe aggregates."""
    election_id = await _create_test_election(client, admin_headers, "EV-2026-906")

    # Add 2 candidates
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Candidate A", "position": 1, "party": "Party 1"},
                {"id": "C002", "name": "Candidate B", "position": 2, "party": "Party 2"},
            ]
        },
        headers=admin_headers,
    )

    # Public transparency elections list
    trans_list = await client.get("/api/transparency/elections")
    assert trans_list.status_code == 200
    elections_data = trans_list.json()
    assert any(e["election_id"] == election_id for e in elections_data)

    # Public transparency overview for election
    overview_resp = await client.get(f"/api/transparency/elections/{election_id}")
    assert overview_resp.status_code == 200
    overview = overview_resp.json()
    assert overview["election_id"] == election_id
    assert overview["candidate_count"] == 2
    assert "no individual voter information disclosed" in overview["notice"]

    # Public candidates list
    cand_resp = await client.get(f"/api/transparency/elections/{election_id}/candidates")
    assert cand_resp.status_code == 200
    assert len(cand_resp.json()) == 2

    # Register a device and test public transparency devices list
    await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-042", "name": "Transparency Test Unit"},
        headers=admin_headers,
    )
    dev_resp = await client.get(f"/api/transparency/elections/{election_id}/devices")
    assert dev_resp.status_code == 200
    devs = dev_resp.json()
    assert len(devs) == 1
    assert devs[0]["id"] == "EVM-042"


@pytest.mark.asyncio
async def test_seed_demo_endpoint(client: AsyncClient):
    """Test seed-demo endpoint provisions deterministic demo election EV-2026-001 in OPEN state."""
    seed_resp = await client.post("/api/simulation/seed-demo")
    assert seed_resp.status_code == 200
    data = seed_resp.json()
    assert data["status"] == "SUCCESS"
    assert data["election_id"] == "EV-2026-001"
    assert data["state"] == "OPEN"

    # Verify transparency view sees the seeded election as OPEN
    trans_resp = await client.get("/api/transparency/elections/EV-2026-001")
    assert trans_resp.status_code == 200
    assert trans_resp.json()["state"] == "OPEN"
    assert trans_resp.json()["candidate_count"] == 4

    # Verify devices are accessible
    devs_resp = await client.get("/api/transparency/elections/EV-2026-001/devices")
    assert devs_resp.status_code == 200
    assert len(devs_resp.json()) == 4



# ===========================================================================
# 6. Deterministic Simulation Endpoint
# ===========================================================================

@pytest.mark.asyncio
async def test_simulation_presets_and_execution(client: AsyncClient, admin_headers: dict):
    """Test listing simulation presets and executing a deterministic demo run."""
    # Presets listing
    presets_resp = await client.get("/api/simulation/presets")
    assert presets_resp.status_code == 200
    presets = presets_resp.json()
    assert "DEMO_1000" in presets

    # Execute DEMO_1000 in test database
    sim_resp = await client.post(
        "/api/simulation/run",
        json={"preset": "DEMO_1000", "election_name": "Test Simulation Run"},
        headers=admin_headers,
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["status"] == "COMPLETED"
    assert sim_data["ballots_generated"] > 0
    assert sim_data["audit_entries"] > 0
    assert sim_data["duration_seconds"] >= 0.0


@pytest.mark.asyncio
async def test_simulation_audit_chain_and_standalone_export_verification(
    client: AsyncClient, admin_headers: dict
):
    """
    Critical Hardening Verification:
    1. Run simulated election (DEMO_1000).
    2. Verify audit chain verification endpoint reports intact chain.
    3. Export the election archive.
    4. Verify the archive with StandaloneElectionVerifier (offline, independent).
    5. Ensure all checks pass: export envelope, config hash, ballots, tally, reconciliation, audit chain, manifest.
    6. Verify that tampering with audit entries or ballots is strictly detected.
    """
    from standalone_verifier.verifier import StandaloneElectionVerifier

    # 1. Run simulation
    sim_resp = await client.post(
        "/api/simulation/run",
        json={"preset": "DEMO_1000", "election_name": "Verification Test Run"},
        headers=admin_headers,
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    election_id = sim_data["election_id"]

    # 2. In-system audit chain verification
    chain_resp = await client.get(f"/api/elections/{election_id}/audit/verify", headers=admin_headers)
    assert chain_resp.status_code == 200
    chain_data = chain_resp.json()
    assert chain_data["is_intact"] is True
    assert chain_data["total_entries"] == sim_data["audit_entries"]

    # 3. Export election archive
    export_resp = await client.get(f"/api/elections/{election_id}/export", headers=admin_headers)
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["election"]["id"] == election_id

    # 4. Standalone independent verification
    v_result = StandaloneElectionVerifier.verify_export_data(export_data)
    assert v_result["checks"]["export_envelope"] is True
    assert v_result["checks"]["configuration"] is True
    assert v_result["checks"]["ballot_hashes"] is True
    assert v_result["checks"]["ballot_sequence"] is True
    assert v_result["checks"]["candidate_totals"] is True
    assert v_result["checks"]["device_totals"] is True
    assert v_result["checks"]["reconciliation"] is True
    assert v_result["checks"]["audit_chain"] is True
    assert v_result["checks"]["audit_root"] is True
    assert v_result["checks"]["manifest"] is True
    assert len(v_result["failures"]) == 0

    # 5. Tamper detection: Corrupt an audit entry
    tampered_audit = json.loads(json.dumps(export_data))
    tampered_audit["audit_log"][1]["entry_hash"] = "f" * 64
    audit_tamper_result = StandaloneElectionVerifier.verify_export_data(tampered_audit)
    assert audit_tamper_result["checks"]["audit_chain"] is False
    assert any("AUDIT_CHAIN_INVALID" in f for f in audit_tamper_result["failures"])

    # 6. Tamper detection: Corrupt a ballot
    tampered_ballot = json.loads(json.dumps(export_data))
    tampered_ballot["ballots"][0]["ballot_hash"] = "e" * 64
    ballot_tamper_result = StandaloneElectionVerifier.verify_export_data(tampered_ballot)
    assert ballot_tamper_result["checks"]["ballot_hashes"] is False
    assert any("BALLOT_HASH_MISMATCH" in f for f in ballot_tamper_result["failures"])


# ===========================================================================
# 7. Role-Based Access Control (RBAC) Protection
# ===========================================================================

@pytest.mark.asyncio
async def test_ecosystem_rbac_protection(client: AsyncClient, admin_headers: dict, observer_token: str):
    """Verify unauthorized roles cannot execute administrative operations."""
    election_id = await _create_test_election(client, admin_headers, "EV-2026-907")
    observer_headers = {"Authorization": f"Bearer {observer_token}"}

    # Observer cannot register voters
    unauth_voter = await client.post(
        f"/api/elections/{election_id}/voters",
        json={"name": "Attacker", "date_of_birth": "1990-01-01", "constituency": "North"},
        headers=observer_headers,
    )
    assert unauth_voter.status_code == 403

    # Observer cannot run simulation
    unauth_sim = await client.post(
        "/api/simulation/run",
        json={"preset": "DEMO_1000"},
        headers=observer_headers,
    )
    assert unauth_sim.status_code == 403

    # Observer cannot create polling stations
    unauth_ps = await client.post(
        f"/api/elections/{election_id}/polling-stations",
        json={
            "station_code": "PS-999",
            "name": "Rogue Station",
            "constituency": "West",
            "location": "Nowhere",
        },
        headers=observer_headers,
    )
    assert unauth_ps.status_code == 403
