"""
Deterministic Demo Scenario Runner for SecureVOTE (Section 11).

Election: EV-2026-001 "SecureVOTE Demo Election 2026"
Candidates: C001â€“C004 (fictional parties, symbols Aâ€“D)
Devices: EVM-001â€¦004
Ballots: 1000 deterministic ballots across 4 devices (no random seeds)

Full Sequence:
1. Register admin user & authenticate
2. Configure election & 4 candidates
3. Hash & lock configuration
4. Register & activate 4 devices
5. Open election
6. Authorize sessions & cast 1000 deterministic votes
7. Close election
8. Verify configuration hash
9. Verify audit hash chain
10. Reconcile raw ballots (exact zero drift)
11. Recompute independent tally
12. Generate & independently verify result manifest
13. Publish election
"""

import asyncio
import sys
import time
from pathlib import Path
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, async_session_factory, engine
from app.main import app


async def run_deterministic_demo(total_votes: int = 1000, verbose: bool = True):
    """Run the complete deterministic demo scenario."""
    start_time = time.time()

    # Re-initialize DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # Step 1: Admin setup
        if verbose:
            print("[1/8] Setting up Admin Authentication...")
        await client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "AdminSecurePassword123!", "role": "ADMIN"},
        )
        login_resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "AdminSecurePassword123!"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create Election & Candidates
        election_id = "EV-2026-001"
        if verbose:
            print(f"[2/8] Creating Election {election_id} and 4 Candidates...")
        await client.post(
            "/api/elections",
            json={
                "id": election_id,
                "name": "SecureVOTE Demo Election 2026",
                "description": "Educational prototype demonstration election with 1000 deterministic ballots.",
            },
            headers=headers,
        )

        candidates = [
            {"id": "C001", "name": "Alice Vance", "party": "Forward Alliance", "symbol": "A", "position": 1},
            {"id": "C002", "name": "Bob Jenkins", "party": "Civic Liberty", "symbol": "B", "position": 2},
            {"id": "C003", "name": "Carol Danvers", "party": "Reform Union", "symbol": "C", "position": 3},
            {"id": "C004", "name": "David Miller", "party": "Independent Coalition", "symbol": "D", "position": 4},
        ]
        await client.post(
            f"/api/elections/{election_id}/candidates",
            json={"candidates": candidates},
            headers=headers,
        )

        # Step 3: Lock Configuration (freezes candidate list & computes config hash)
        if verbose:
            print("[3/8] Freezing and Locking Election Configuration...")
        lock_resp = await client.patch(
            f"/api/elections/{election_id}/state",
            json={"new_state": "LOCKED", "reason": "Candidate registration concluded"},
            headers=headers,
        )
        config_hash = lock_resp.json()["configuration_hash"]
        if verbose:
            print(f"      Configuration Hash: {config_hash}")

        # Step 4: Register & Activate 4 EVM Devices
        if verbose:
            print("[4/8] Registering & Activating 4 EVM Units (EVM-001..EVM-004)...")
        device_ids = ["EVM-001", "EVM-002", "EVM-003", "EVM-004"]
        for dev_id in device_ids:
            await client.post(
                f"/api/elections/{election_id}/devices",
                json={"id": dev_id, "name": f"Polling Booth Unit {dev_id[-3:]}"},
                headers=headers,
            )
            await client.patch(
                f"/api/elections/{election_id}/devices/{dev_id}/status",
                json={"status": "ACTIVE"},
                headers=headers,
            )

        # Step 5: Open Election
        if verbose:
            print("[5/8] Opening Election for Voting...")
        await client.patch(
            f"/api/elections/{election_id}/state",
            json={"new_state": "OPEN", "reason": "Polls opened at 08:00"},
            headers=headers,
        )

        # Step 6: Cast Deterministic Ballots
        if verbose:
            print(f"[6/8] Casting {total_votes} Deterministic Ballots across 4 Devices...")

        device_seq = {d: 0 for d in device_ids}
        vote_progress_step = max(1, total_votes // 10)

        for i in range(1, total_votes + 1):
            # Deterministic round-robin allocation
            dev_idx = (i - 1) % 4
            device_id = device_ids[dev_idx]
            device_seq[device_id] += 1
            seq = device_seq[device_id]

            # Deterministic candidate selection (no random seeds)
            cand_idx = ((i * 7) % 4) + 1
            cand_id = f"C{cand_idx:03d}"
            voter_cred = f"VOTER-DEMO-{i:04d}"

            # Authorize session
            sess_resp = await client.post(
                f"/api/elections/{election_id}/sessions",
                json={"voter_credential": voter_cred, "device_id": device_id},
                headers=headers,
            )
            session_token = sess_resp.json()["session_token"]

            # Cast ballot
            await client.post(
                "/api/votes",
                json={
                    "session_token": session_token,
                    "candidate_id": cand_id,
                    "device_id": device_id,
                    "sequence_number": seq,
                },
            )

            if verbose and (i % vote_progress_step == 0 or i == total_votes):
                print(f"      Cast {i}/{total_votes} ballots...")

        # Step 7: Close Election
        if verbose:
            print("[7/8] Closing Polls (State -> CLOSED)...")
        await client.patch(
            f"/api/elections/{election_id}/state",
            json={"new_state": "CLOSED", "reason": "Polls closed at 18:00"},
            headers=headers,
        )

        # Step 8: Full Independent Verification & Results
        if verbose:
            print("[8/8] Executing Independent Verification & Reconciliation...")
        results_resp = await client.get(
            f"/api/elections/{election_id}/results",
            headers=headers,
        )
        results = results_resp.json()

        # Publish
        await client.patch(
            f"/api/elections/{election_id}/state",
            json={"new_state": "PUBLISHED", "reason": "Results certified"},
            headers=headers,
        )

        elapsed = time.time() - start_time
        if verbose:
            print("\n" + "=" * 60)
            print("DEMO SCENARIO EXECUTION SUMMARY")
            print("=" * 60)
            print(f"Election ID:               {results['election_id']}")
            print(f"Overall Status:            {results['overall_status']}")
            print(f"Config Hash Valid:         {results['config_hash_valid']}")
            print(f"Audit Chain Intact:        {results['audit_chain_intact']}")
            print(f"Reconciliation Passed:     {results['reconciliation_passed']}")
            print(f"Tally Verified:            {results['tally_independently_verified']}")
            print(f"Total Ballots Cast:        {results['manifest']['total_ballots']}")
            print(f"Manifest Hash:             {results['manifest']['manifest_hash']}")
            print("-" * 60)
            print("Candidate Results:")
            for cr in results["manifest"]["candidate_results"]:
                print(f"  {cr['candidate_id']}: {cr['candidate_name']:<22} ({cr['party']:<22}) -> {cr['vote_count']:>4} votes ({cr['percentage']:>5.2f}%)")
            print("-" * 60)
            print("Device Allocations:")
            for dr in results["manifest"]["device_results"]:
                print(f"  {dr['device_id']}: {dr['device_name']:<25} -> {dr['ballot_count']:>4} ballots")
            print("-" * 60)
            print(f"Execution Time:            {elapsed:.2f}s")
            print("=" * 60 + "\n")

        return results


if __name__ == "__main__":
    count = 1000
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
    asyncio.run(run_deterministic_demo(total_votes=count, verbose=True))
