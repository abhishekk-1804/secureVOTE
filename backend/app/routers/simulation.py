from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import time
import random
import uuid
import hashlib
import json
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_db
from app.models import Election, Candidate, PollingStation, Device, Voter, User, VotingSession, Ballot, AuditEntry, ResultManifest
from app.schemas import SimulationRequest, SimulationResponse
from app.routers.auth import get_current_user
from app.utils.hashing import (
    compute_audit_entry_hash,
    compute_ballot_hash,
    compute_configuration_hash,
    compute_manifest_hash,
)

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])

PRESETS = {
    "DEMO_1000": {"voters": 1000, "stations": 2, "devices": 4, "candidates": 4},
    "DEMO_10000": {"voters": 10000, "stations": 10, "devices": 20, "candidates": 6},
    "DEMO_100000": {"voters": 100000, "stations": 50, "devices": 100, "candidates": 8}
}

CANDIDATE_NAMES = ["Priya Sharma", "Rajesh Kumar", "Anita Desai", "Vikram Singh", "Sunil Chettri", "Meera Reddy", "Sanjay Gupta", "Kavita Rao"]
PARTIES = ["Democratic Reform Party", "People's Progress Alliance", "National Development Front", "Citizens United Movement", "Independent", "Green Earth Party", "Forward Block", "Tech Innovators Party"]
CONSTITUENCIES = ["North District", "South District", "East District", "West District", "Central District"]

def check_admin(user: User):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough permissions")

def _utcnow():
    return datetime.now(timezone.utc)

@router.get("/presets")
async def get_presets():
    return PRESETS

@router.post("/run", response_model=SimulationResponse)
async def run_simulation(req: SimulationRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin(current_user)

    start_time = time.time()
    preset_data = PRESETS.get(req.preset)
    if not preset_data:
        raise HTTPException(status_code=400, detail="Invalid preset")

    existing_elections = set((await db.execute(select(Election.id))).scalars().all())
    existing_candidates = set((await db.execute(select(Candidate.id))).scalars().all())
    existing_devices = set((await db.execute(select(Device.id))).scalars().all())

    num_cand = preset_data["candidates"]
    num_dev = preset_data["devices"]

    if getattr(req, "election_id", None):
        election_id = req.election_id
        if election_id in existing_elections:
            raise HTTPException(status_code=409, detail=f"Election {election_id} already exists")
        h = hashlib.sha256(election_id.encode()).hexdigest()[:4].upper()
        cand_prefix = f"S{h}"
    else:
        sim_idx = 1
        while (
            f"EV-2026-SIM-{sim_idx:03d}" in existing_elections
            or any(f"S{sim_idx:02d}-C{i+1:02d}" in existing_candidates for i in range(num_cand))
            or any(f"EVM-S{sim_idx:02d}-{j+1:03d}" in existing_devices for j in range(num_dev))
        ):
            sim_idx += 1
        election_id = f"EV-2026-SIM-{sim_idx:03d}"
        cand_prefix = f"S{sim_idx:02d}" if sim_idx < 100 else f"S{sim_idx}"

    random.seed(election_id)

    # 1. Create Election
    election = Election(
        id=election_id,
        name=req.election_name,
        description=f"Simulated Election ({req.preset})",
        state="CREATED"
    )
    db.add(election)
    await db.commit()

    # 2. Create Candidates
    candidates = []
    for i in range(num_cand):
        c = Candidate(
            id=f"{cand_prefix}-C{i+1:02d}",
            election_id=election_id,
            name=CANDIDATE_NAMES[i],
            party=PARTIES[i],
            symbol="",
            position=i+1
        )
        candidates.append(c)
        db.add(c)

    # 3. Create Polling Stations & Devices
    stations = []
    devices = []
    for i in range(preset_data["stations"]):
        ps = PollingStation(
            election_id=election_id,
            station_code=f"PS-{cand_prefix}-{i+1:03d}",
            name=f"Simulated Station {i+1}",
            constituency=random.choice(CONSTITUENCIES),
            location="Simulation Area",
            status="READY",
            assigned_devices=preset_data["devices"] // preset_data["stations"]
        )
        stations.append(ps)
        db.add(ps)

        for j in range(ps.assigned_devices):
            dev = Device(
                id=f"EVM-{cand_prefix}-{len(devices)+1:03d}",
                election_id=election_id,
                name=f"Device {len(devices)+1}",
                status="ACTIVE",
                last_sequence_number=0,
                total_votes_cast=0,
                device_hash=hashlib.sha256(f"dev-{cand_prefix}-{len(devices)+1}".encode()).hexdigest(),
                registered_at=_utcnow(),
                last_seen_at=_utcnow(),
            )
            devices.append(dev)
            db.add(dev)

    # 4. Create Voters
    voters = []
    for i in range(preset_data["voters"]):
        v = Voter(
            election_id=election_id,
            voter_id_number=f"VTR-{i:06d}",
            name=f"Voter {i}",
            date_of_birth="1990-01-01",
            constituency=random.choice(CONSTITUENCIES),
            eligibility_status="ELIGIBLE",
            registration_status="VERIFIED"
        )
        voters.append(v)
        db.add(v)

    await db.commit()

    # 5. Transition Election & Compute Canonical Configuration Hash
    candidate_dicts = [
        {
            "id": c.id,
            "name": c.name,
            "party": c.party,
            "symbol": c.symbol or "",
            "position": c.position,
        }
        for c in sorted(candidates, key=lambda x: x.position)
    ]
    config_hash = compute_configuration_hash(election_id, candidate_dicts)

    election.state = "CONFIGURED"
    election.configured_at = _utcnow()
    election.configuration_hash = config_hash

    election.state = "LOCKED"
    election.locked_at = _utcnow()

    election.state = "OPEN"
    election.opened_at = _utcnow()
    await db.commit()

    # 6. Generate Ballots & Canonical Hash-Chained Audit Log
    turnout = int(preset_data["voters"] * 0.7)

    last_hash = None
    seq_num = 1

    def add_audit(event_type: str, data: str | None = None):
        nonlocal last_hash, seq_num
        now = _utcnow()
        entry_hash = compute_audit_entry_hash(
            sequence_number=seq_num,
            event_type=event_type,
            event_data=data,
            timestamp=now,
            previous_hash=last_hash,
        )
        ae = AuditEntry(
            election_id=election_id,
            event_type=event_type,
            event_data=data,
            sequence_number=seq_num,
            timestamp=now,
            previous_hash=last_hash,
            entry_hash=entry_hash
        )
        db.add(ae)
        last_hash = entry_hash
        seq_num += 1
        return ae

    add_audit("ELECTION_CREATED", json.dumps({"name": req.election_name}))
    add_audit("CANDIDATES_ADDED", json.dumps({"count": len(candidates)}))
    add_audit("ELECTION_CONFIGURED", json.dumps({"configuration_hash": config_hash}))
    add_audit("ELECTION_LOCKED", json.dumps({"locked_at": election.locked_at.isoformat()}))
    add_audit("ELECTION_OPENED", json.dumps({"opened_at": election.opened_at.isoformat()}))

    # Generate ballots
    candidate_tallies = {c.id: 0 for c in candidates}
    device_tallies = {d.id: 0 for d in devices}

    batch_size = 500
    for i in range(turnout):
        device = devices[i % len(devices)]
        candidate = candidates[i % len(candidates)]
        device.last_sequence_number += 1
        device.total_votes_cast += 1
        candidate_tallies[candidate.id] += 1
        device_tallies[device.id] += 1

        now_vote = _utcnow()
        session_id = str(uuid.uuid4())
        v_session = VotingSession(
            id=session_id,
            election_id=election_id,
            device_id=device.id,
            session_token=uuid.uuid4().hex,
            voter_credential=f"SIM-CRED-{election_id}-{i+1:06d}",
            status="VOTED",
            authorized_at=now_vote,
            voted_at=now_vote,
        )
        db.add(v_session)

        b_hash = compute_ballot_hash(
            election_id=election_id,
            session_id=session_id,
            candidate_id=candidate.id,
            device_id=device.id,
            sequence_number=device.last_sequence_number,
            timestamp=now_vote,
        )
        b = Ballot(
            election_id=election_id,
            session_id=session_id,
            device_id=device.id,
            candidate_id=candidate.id,
            sequence_number=device.last_sequence_number,
            recorded_at=now_vote,
            ballot_hash=b_hash
        )
        db.add(b)

        if (i + 1) % batch_size == 0:
            add_audit("VOTES_CAST_BATCH", json.dumps({"batch_count": batch_size, "total_so_far": i + 1}))
            await db.commit()

    election.total_ballots = turnout
    add_audit("ELECTION_CLOSED", json.dumps({"total_votes": turnout}))

    election.state = "CLOSED"
    election.closed_at = _utcnow()
    await db.commit()

    # 7. Generate Manifest with Canonical Manifest Hash
    manifest_hash = compute_manifest_hash(
        election_id=election_id,
        total_ballots=turnout,
        candidate_totals=candidate_tallies,
        device_totals=device_tallies,
        reconciliation_status="PASSED",
        audit_chain_status="INTACT",
        configuration_hash=election.configuration_hash,
    )
    now_m = _utcnow()
    manifest = ResultManifest(
        election_id=election_id,
        total_ballots=turnout,
        candidate_totals=json.dumps(dict(sorted(candidate_tallies.items()))),
        device_totals=json.dumps(dict(sorted(device_tallies.items()))),
        reconciliation_status="PASSED",
        audit_chain_status="INTACT",
        configuration_hash=election.configuration_hash,
        manifest_hash=manifest_hash,
        generated_at=now_m,
        verified_at=now_m,
        verified_by="SIMULATOR_ENGINE",
    )
    db.add(manifest)

    add_audit("MANIFEST_GENERATED", json.dumps({"manifest_hash": manifest_hash}))

    election.state = "PUBLISHED"
    election.published_at = _utcnow()
    await db.commit()

    duration = time.time() - start_time

    return SimulationResponse(
        election_id=election_id,
        preset=req.preset,
        ballots_generated=turnout,
        devices_created=preset_data["devices"],
        polling_stations_created=preset_data["stations"],
        voters_registered=preset_data["voters"],
        candidates_created=preset_data["candidates"],
        audit_entries=seq_num - 1,
        duration_seconds=duration,
        status="COMPLETED"
    )


@router.post("/seed-demo")
async def seed_demo_endpoint(reset: bool = False, db: AsyncSession = Depends(get_db)):
    """Idempotently seed the deterministic demo election in OPEN state."""
    from scripts.seed_demo_election import seed_demo_election
    await seed_demo_election(reset=reset, session=db)
    return {
        "status": "SUCCESS",
        "election_id": "EV-2026-001",
        "state": "OPEN",
        "message": "Deterministic demo election seeded and OPEN for EVM Digital Twin."
    }
