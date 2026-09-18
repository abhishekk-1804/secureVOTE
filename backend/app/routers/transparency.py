from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import json

from app.database import get_db
from app.models import Election, Candidate, PollingStation, Device, Voter, ResultManifest
from app.schemas import TransparencyOverview, CandidateResponse, DeviceResponse

router = APIRouter(prefix="/api/transparency", tags=["Transparency"])

@router.get("/elections", response_model=List[TransparencyOverview])
async def list_transparency_elections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Election))
    elections = result.scalars().all()

    overviews = []
    for el in elections:
        ps_count = await db.scalar(select(func.count(PollingStation.id)).where(PollingStation.election_id == el.id))
        voter_count = await db.scalar(select(func.count(Voter.id)).where(Voter.election_id == el.id))

        turnout = (el.total_ballots / voter_count * 100) if voter_count and voter_count > 0 else 0.0

        manifest = await db.execute(select(ResultManifest).where(ResultManifest.election_id == el.id))
        man = manifest.scalar_one_or_none()

        overviews.append(TransparencyOverview(
            election_id=el.id,
            election_name=el.name,
            state=el.state,
            total_ballots=el.total_ballots,
            device_count=len(el.devices) if el.devices else 0,
            polling_station_count=ps_count or 0,
            candidate_count=len(el.candidates) if el.candidates else 0,
            registered_voters=voter_count or 0,
            turnout_percentage=turnout,
            audit_chain_status=man.audit_chain_status if man else "PENDING",
            reconciliation_status=man.reconciliation_status if man else "PENDING",
            manifest_status="PUBLISHED" if man else "PENDING",
            notice="Aggregate data only - no individual voter information disclosed"
        ))
    return overviews

@router.get("/elections/{election_id}", response_model=TransparencyOverview)
async def get_transparency_overview(election_id: str, db: AsyncSession = Depends(get_db)):
    el = await db.get(Election, election_id)
    if not el:
        raise HTTPException(status_code=404, detail="Election not found")

    ps_count = await db.scalar(select(func.count(PollingStation.id)).where(PollingStation.election_id == el.id))
    voter_count = await db.scalar(select(func.count(Voter.id)).where(Voter.election_id == el.id))

    turnout = (el.total_ballots / voter_count * 100) if voter_count and voter_count > 0 else 0.0

    manifest = await db.execute(select(ResultManifest).where(ResultManifest.election_id == el.id))
    man = manifest.scalar_one_or_none()

    return TransparencyOverview(
        election_id=el.id,
        election_name=el.name,
        state=el.state,
        total_ballots=el.total_ballots,
        device_count=len(el.devices) if el.devices else 0,
        polling_station_count=ps_count or 0,
        candidate_count=len(el.candidates) if el.candidates else 0,
        registered_voters=voter_count or 0,
        turnout_percentage=turnout,
        audit_chain_status=man.audit_chain_status if man else "PENDING",
        reconciliation_status=man.reconciliation_status if man else "PENDING",
        manifest_status="PUBLISHED" if man else "PENDING",
        notice="Aggregate data only - no individual voter information disclosed"
    )

@router.get("/elections/{election_id}/candidates", response_model=List[CandidateResponse])
async def get_transparency_candidates(election_id: str, db: AsyncSession = Depends(get_db)):
    el = await db.get(Election, election_id)
    if not el:
        raise HTTPException(status_code=404, detail="Election not found")

    result = await db.execute(select(Candidate).where(Candidate.election_id == election_id))
    return result.scalars().all()

@router.get("/elections/{election_id}/results")
async def get_transparency_results(election_id: str, db: AsyncSession = Depends(get_db)):
    el = await db.get(Election, election_id)
    if not el:
        raise HTTPException(status_code=404, detail="Election not found")

    if el.state not in ["CLOSED", "PUBLISHED"]:
        raise HTTPException(status_code=400, detail="Results not available until election is CLOSED or PUBLISHED")

    manifest = await db.execute(select(ResultManifest).where(ResultManifest.election_id == el.id))
    man = manifest.scalar_one_or_none()

    if not man:
        raise HTTPException(status_code=404, detail="Results manifest not found")

    return {
        "election_id": el.id,
        "total_ballots": man.total_ballots,
        "candidate_totals": json.loads(man.candidate_totals),
        "device_totals": json.loads(man.device_totals),
        "reconciliation_status": man.reconciliation_status,
        "audit_chain_status": man.audit_chain_status,
        "manifest_hash": man.manifest_hash,
        "digital_signature": man.digital_signature
    }


@router.get("/elections/{election_id}/devices", response_model=List[DeviceResponse])
async def get_transparency_devices(election_id: str, db: AsyncSession = Depends(get_db)):
    el = await db.get(Election, election_id)
    if not el:
        raise HTTPException(status_code=404, detail="Election not found")

    result = await db.execute(select(Device).where(Device.election_id == election_id))
    return result.scalars().all()
