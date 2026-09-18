"""
Regression tests for simulation candidate and device primary key collision remediation.

Covers TESTS A through K:
- TEST A: Seed demo election + Run simulation -> PASS
- TEST B: Seed demo election + Run simulation twice -> PASS both times
- TEST C: Run two independent simulations -> Both coexist without ID collisions
- TEST D: Verify candidate IDs are globally unique
- TEST E: Verify device IDs are globally unique
- TEST F: Verify all foreign keys remain valid
- TEST G: Verify votes reference the correct candidate/device
- TEST H: Verify results remain correct
- TEST I: Verify audit records remain correct
- TEST J: Export both elections -> Both exports independently verify
- TEST K: Run standalone verifier against both exports -> PASS for both
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Election, Candidate, Device, Ballot, AuditEntry
from standalone_verifier.verifier import StandaloneElectionVerifier
from app.services.signing_service import SigningService


@pytest.mark.asyncio
async def test_a_seed_and_run_simulation(client: AsyncClient, admin_headers: dict):
    """TEST A: Seed demo election, then run simulation. Expected: PASS."""
    seed_resp = await client.post("/api/simulation/seed-demo", headers=admin_headers)
    assert seed_resp.status_code == 200, f"Seed failed: {seed_resp.text}"

    sim_resp = await client.post(
        "/api/simulation/run",
        json={"preset": "DEMO_1000", "election_name": "Test Sim A"},
        headers=admin_headers,
    )
    assert sim_resp.status_code == 200, f"Simulation failed: {sim_resp.text}"
    data = sim_resp.json()
    assert data["status"] == "COMPLETED"
    assert data["election_id"].startswith("EV-2026-SIM-")
    assert data["ballots_generated"] == 700


@pytest.mark.asyncio
async def test_b_seed_and_run_simulation_twice(client: AsyncClient, admin_headers: dict):
    """TEST B: Seed demo election, then run simulation twice. Expected: PASS both times."""
    seed_resp = await client.post("/api/simulation/seed-demo", headers=admin_headers)
    assert seed_resp.status_code == 200, f"Seed failed: {seed_resp.text}"

    sim1 = await client.post(
        "/api/simulation/run",
        json={"preset": "DEMO_1000", "election_name": "Sim 1"},
        headers=admin_headers,
    )
    assert sim1.status_code == 200, f"Sim 1 failed: {sim1.text}"
    sim1_data = sim1.json()

    sim2 = await client.post(
        "/api/simulation/run",
        json={"preset": "DEMO_1000", "election_name": "Sim 2"},
        headers=admin_headers,
    )
    assert sim2.status_code == 200, f"Sim 2 failed: {sim2.text}"
    sim2_data = sim2.json()

    assert sim1_data["election_id"] != sim2_data["election_id"]


@pytest.mark.asyncio
async def test_c_through_k_full_multi_election_coexistence(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    """
    TESTS C through K:
    - TEST C: Run two independent simulations -> Both coexist
    - TEST D: Verify candidate IDs are globally unique
    - TEST E: Verify device IDs are globally unique
    - TEST F: Verify all foreign keys remain valid
    - TEST G: Verify votes reference correct candidate/device
    - TEST H: Verify results remain correct (reconciliation)
    - TEST I: Verify audit records remain correct
    - TEST J: Export both elections -> Both exports independently verify
    - TEST K: Run standalone verifier against both exports -> PASS for both
    """
    priv, pub = SigningService.generate_keypair()
    SigningService.set_keypair(priv, pub, key_id="multi-test-key")

    try:
        seed_resp = await client.post("/api/simulation/seed-demo", headers=admin_headers)
        assert seed_resp.status_code == 200

        sim1 = await client.post(
            "/api/simulation/run",
            json={"preset": "DEMO_1000", "election_name": "Coexist Sim 1"},
            headers=admin_headers,
        )
        assert sim1.status_code == 200
        elec1_id = sim1.json()["election_id"]

        sim2 = await client.post(
            "/api/simulation/run",
            json={"preset": "DEMO_1000", "election_name": "Coexist Sim 2"},
            headers=admin_headers,
        )
        assert sim2.status_code == 200
        elec2_id = sim2.json()["election_id"]

        # TEST C: Both coexist in database
        elections = (await db_session.execute(select(Election.id))).scalars().all()
        assert "EV-2026-001" in elections
        assert elec1_id in elections
        assert elec2_id in elections

        # TEST D: Verify candidate IDs are globally unique across all elections
        candidates = (await db_session.execute(select(Candidate))).scalars().all()
        cand_ids = [c.id for c in candidates]
        assert len(cand_ids) == len(set(cand_ids)), f"Duplicate candidate IDs: {cand_ids}"
        for cid in cand_ids:
            assert len(cid) <= 10, f"Candidate ID exceeds 10 chars: {cid}"

        # TEST E: Verify device IDs are globally unique across all elections
        devices = (await db_session.execute(select(Device))).scalars().all()
        dev_ids = [d.id for d in devices]
        assert len(dev_ids) == len(set(dev_ids)), f"Duplicate device IDs: {dev_ids}"
        for did in dev_ids:
            assert len(did) <= 20, f"Device ID exceeds 20 chars: {did}"

        # TEST F: Verify all foreign keys remain valid
        ballots = (await db_session.execute(select(Ballot))).scalars().all()
        cand_id_set = set(cand_ids)
        dev_id_set = set(dev_ids)
        elec_id_set = set(elections)

        for b in ballots:
            assert b.election_id in elec_id_set
            assert b.candidate_id in cand_id_set
            assert b.device_id in dev_id_set

        # TEST G: Verify votes reference the correct candidate/device belonging to their election
        cand_elec_map = {c.id: c.election_id for c in candidates}
        dev_elec_map = {d.id: d.election_id for d in devices}

        for b in ballots:
            assert cand_elec_map[b.candidate_id] == b.election_id
            assert dev_elec_map[b.device_id] == b.election_id

        # TEST H: Verify results remain correct (reconciliation for each simulated election)
        for eid in [elec1_id, elec2_id]:
            rec_resp = await client.post(f"/api/elections/{eid}/verify", headers=admin_headers)
            assert rec_resp.status_code == 200, f"Verification failed for {eid}: {rec_resp.text}"
            rec_data = rec_resp.json()
            assert rec_data["reconciliation_passed"] is True
            assert rec_data["audit_chain_intact"] is True
            assert rec_data["overall_status"] == "PASSED"

        # TEST I: Verify audit records remain correct
        for eid in [elec1_id, elec2_id]:
            audit_entries = (
                await db_session.execute(
                    select(AuditEntry).where(AuditEntry.election_id == eid).order_by(AuditEntry.sequence_number)
                )
            ).scalars().all()
            assert len(audit_entries) > 0
            for idx, ae in enumerate(audit_entries):
                assert ae.sequence_number == idx + 1
            for idx in range(1, len(audit_entries)):
                assert audit_entries[idx].previous_hash == audit_entries[idx - 1].entry_hash

        # TEST J & K: Export and verify both elections independently with StandaloneElectionVerifier
        for eid in [elec1_id, elec2_id]:
            sign_resp = await client.post(f"/api/elections/{eid}/sign-manifest", headers=admin_headers)
            assert sign_resp.status_code == 200, f"Sign failed for {eid}: {sign_resp.text}"

            exp_resp = await client.get(f"/api/elections/{eid}/export", headers=admin_headers)
            assert exp_resp.status_code == 200, f"Export failed for {eid}: {exp_resp.text}"
            exp_data = exp_resp.json()

            ver_result = StandaloneElectionVerifier.verify_export_data(exp_data)
            assert ver_result["valid"] is True, f"Standalone verify failed for {eid}: {ver_result['failures']}"
            assert len(ver_result["failures"]) == 0

    finally:
        SigningService.clear_keypair()
