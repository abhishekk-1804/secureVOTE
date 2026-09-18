"""
Deterministic Demo Election Seeder for SecureVOTE.

Creates:
- Users: admin, officer, auditor, observer
- Election: EV-2026-001 (SecureVOTE General Election Simulation 2026)
- 4 Candidates: C001-C004 with political parties and symbols
- 2 Polling Stations: PS-001, PS-002 in Bengaluru Central
- 4 Devices: EVM-001 to EVM-004, fully activated
- 20 Synthetic Voters: VTR-2026-00001 to VTR-2026-00020 with ELIGIBLE status
- Locks configuration and opens election for live EVM Digital Twin polling

Usage:
    python backend/scripts/seed_demo_election.py [--reset]
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory, engine, Base
from app.models import (
    User,
    Election,
    Candidate,
    Device,
    PollingStation,
    Voter,
    AuditEntry,
    VotingSession,
    Ballot,
    ResultManifest,
)
from app.utils.security import hash_password
from app.utils.hashing import compute_configuration_hash
from app.services.audit_service import AuditService


def _utcnow():
    return datetime.now(timezone.utc)


async def _seed_with_session(session: AsyncSession, reset: bool = False):
    """Internal seeder logic operating on a provided SQLAlchemy AsyncSession."""
    print("==================================================")
    print("  SECUREVOTE 2.0 -- DEMO ELECTION SEEDER")
    print("==================================================")

    # 1. Seed standard users
    print("[1/6] Seeding system users...")
    users_to_seed = [
        ("admin", "AdminSecurePassword123!", "ADMIN"),
        ("officer", "OfficerSecurePassword123!", "ADMIN"),
        ("auditor", "AuditorSecurePassword123!", "AUDITOR"),
        ("observer", "ObserverSecurePassword123!", "OBSERVER"),
    ]
    for username, password, role in users_to_seed:
        res = await session.execute(select(User).where(User.username == username))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                username=username,
                hashed_password=hash_password(password),
                role=role,
                is_active=True,
            )
            session.add(user)
            print(f"  + Created user: {username} ({role})")
        else:
            user.role = role
            user.is_active = True
            print(f"  * Verified user: {username} ({role})")

    await session.commit()

    # 2. Check existing election
    election_id = "EV-2026-001"
    res = await session.execute(select(Election).where(Election.id == election_id))
    election = res.scalar_one_or_none()

    if election and reset:
        print(f"  - Reset requested. Purging existing {election_id}...")
        await session.execute(delete(Ballot).where(Ballot.election_id == election_id))
        await session.execute(delete(VotingSession).where(VotingSession.election_id == election_id))
        await session.execute(delete(ResultManifest).where(ResultManifest.election_id == election_id))
        await session.execute(delete(AuditEntry).where(AuditEntry.election_id == election_id))
        await session.execute(delete(Voter).where(Voter.election_id == election_id))
        await session.execute(delete(PollingStation).where(PollingStation.election_id == election_id))
        await session.execute(delete(Device).where(Device.election_id == election_id))
        await session.execute(delete(Candidate).where(Candidate.election_id == election_id))
        await session.execute(delete(Election).where(Election.id == election_id))
        await session.commit()
        election = None

    if not election:
        print(f"[2/6] Creating Election {election_id}...")
        now = _utcnow()
        election = Election(
            id=election_id,
            name="SecureVOTE General Election Simulation 2026",
            description="Simulated election prototype for Parliamentary Constituency Bengaluru Central.",
            state="CREATED",
            total_ballots=0,
            created_at=now,
        )
        session.add(election)
        await session.commit()

        await AuditService.log_event(
            db=session,
            election_id=election_id,
            event_type="ELECTION_CREATED",
            event_data={"name": election.name, "description": election.description},
            actor="admin",
        )
        await session.commit()

    print(f"[3/6] Ensuring candidates for {election_id}...")
    candidates_data = [
        ("C001", "Alice Vance", "Forward Alliance", "A", 1),
        ("C002", "Bob Jenkins", "Civic Liberty", "B", 2),
        ("C003", "Carol Danvers", "Reform Union", "C", 3),
        ("C004", "David Miller", "Independent Coalition", "D", 4),
    ]
    candidates_dicts = []
    for cid, name, party, symbol, pos in candidates_data:
        c_res = await session.execute(
            select(Candidate).where(Candidate.election_id == election_id, Candidate.id == cid)
        )
        cand = c_res.scalar_one_or_none()
        if not cand:
            cand = Candidate(
                id=cid,
                election_id=election_id,
                name=name,
                party=party,
                symbol=symbol,
                position=pos,
            )
            session.add(cand)
            print(f"  + Added Candidate: {cid} - {name} ({party})")
        candidates_dicts.append({
            "id": cid,
            "name": name,
            "party": party,
            "symbol": symbol,
            "position": pos,
        })
    await session.commit()

    # 4. Ensure Polling Stations & Devices
    print(f"[4/6] Ensuring Polling Stations and EVM Devices...")
    stations_data = [
        ("PS-001", "Govt Higher Primary School, MG Road", "Bengaluru Central", "Shivajinagar, Bengaluru", "Rajesh Sharma"),
        ("PS-002", "Community Center, Indiranagar 100ft Rd", "Bengaluru Central", "Indiranagar, Bengaluru", "Priya Sundaram"),
    ]
    for scode, sname, const, loc, officer in stations_data:
        ps_res = await session.execute(
            select(PollingStation).where(PollingStation.election_id == election_id, PollingStation.station_code == scode)
        )
        ps = ps_res.scalar_one_or_none()
        if not ps:
            ps = PollingStation(
                election_id=election_id,
                station_code=scode,
                name=sname,
                constituency=const,
                location=loc,
                assigned_devices=2,
                registered_voters=500,
                status="READY",
                officer_name=officer,
            )
            session.add(ps)
            print(f"  + Added Polling Station: {scode} - {sname}")
    await session.commit()

    devices_data = [
        ("EVM-001", "Ballot Unit BU-01 (PS-001)"),
        ("EVM-002", "Ballot Unit BU-02 (PS-001)"),
        ("EVM-003", "Ballot Unit BU-03 (PS-002)"),
        ("EVM-004", "Ballot Unit BU-04 (PS-002)"),
    ]
    for did, dname in devices_data:
        dev_res = await session.execute(
            select(Device).where(Device.election_id == election_id, Device.id == did)
        )
        dev = dev_res.scalar_one_or_none()
        if not dev:
            dev = Device(
                id=did,
                election_id=election_id,
                name=dname,
                status="ACTIVE",
                last_sequence_number=0,
                activated_at=_utcnow(),
            )
            session.add(dev)
            print(f"  + Added & Activated Device: {did} ({dname})")
        else:
            dev.status = "ACTIVE"
            if not dev.activated_at:
                dev.activated_at = _utcnow()
            print(f"  * Activated Device: {did} ({dev.status})")
    await session.commit()

    # 5. Lock and Open State
    print(f"[5/6] Updating Election state to OPEN...")
    cfg_hash = compute_configuration_hash(election_id, candidates_dicts)
    election_res = await session.execute(select(Election).where(Election.id == election_id))
    cur_election = election_res.scalar_one()

    cur_election.configuration_hash = cfg_hash
    cur_election.configured_at = cur_election.configured_at or _utcnow()
    cur_election.locked_at = cur_election.locked_at or _utcnow()
    cur_election.state = "OPEN"
    cur_election.opened_at = cur_election.opened_at or _utcnow()
    await session.commit()

    await AuditService.log_event(
        db=session,
        election_id=election_id,
        event_type="CONFIGURATION_LOCKED",
        event_data={"configuration_hash": cfg_hash, "candidate_count": len(candidates_dicts)},
        actor="admin",
    )
    await AuditService.log_event(
        db=session,
        election_id=election_id,
        event_type="ELECTION_OPENED",
        event_data={"active_devices": len(devices_data)},
        actor="admin",
    )
    await session.commit()
    print(f"  * Election {election_id} state is OPEN (Config Hash: {cfg_hash[:16]}...)")

    # 6. Seed synthetic voters
    print(f"[6/6] Seeding synthetic eligible voters...")
    voter_samples = [
        ("VTR-2026-00001", "Aarav Patel", "1994-05-12", "Bengaluru Central"),
        ("VTR-2026-00002", "Deepa Krishnan", "1988-11-23", "Bengaluru Central"),
        ("VTR-2026-00003", "Rohan Kulkarni", "2001-02-17", "Bengaluru Central"),
        ("VTR-2026-00004", "Sunita Nair", "1976-08-30", "Bengaluru Central"),
        ("VTR-2026-00005", "Karthik Iyer", "1995-12-05", "Bengaluru Central"),
        ("VTR-2026-00006", "Ananya Hegde", "1999-04-19", "Bengaluru Central"),
        ("VTR-2026-00007", "Manish Verma", "1982-07-14", "Bengaluru Central"),
        ("VTR-2026-00008", "Fatima Sheikh", "1991-09-28", "Bengaluru Central"),
        ("VTR-2026-00009", "Vikram Gowda", "2003-01-09", "Bengaluru Central"),
        ("VTR-2026-00010", "Meenakshi Sundaram", "1970-03-22", "Bengaluru Central"),
    ]
    for vid, vname, vdob, vconst in voter_samples:
        v_res = await session.execute(
            select(Voter).where(Voter.election_id == election_id, Voter.voter_id_number == vid)
        )
        v = v_res.scalar_one_or_none()
        if not v:
            v = Voter(
                election_id=election_id,
                voter_id_number=vid,
                name=vname,
                date_of_birth=vdob,
                constituency=vconst,
                eligibility_status="ELIGIBLE",
                registration_status="VERIFIED",
                has_voted=False,
            )
            session.add(v)
    await session.commit()
    print(f"  + Seeded {len(voter_samples)} synthetic voters.")

    print("==================================================")
    print(f"SUCCESS: Demo election {election_id} seeded and OPEN!")
    print("==================================================")


async def seed_demo_election(reset: bool = False, session: AsyncSession | None = None):
    """Idempotently provisions the deterministic demo election in OPEN state."""
    if session is not None:
        await _seed_with_session(session, reset=reset)
    else:
        async with async_session_factory() as s:
            await _seed_with_session(s, reset=reset)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed SecureVOTE Demo Election")
    parser.add_argument("--reset", action="store_true", help="Purge existing demo election data before seeding")
    args = parser.parse_args()

    asyncio.run(seed_demo_election(reset=args.reset))
