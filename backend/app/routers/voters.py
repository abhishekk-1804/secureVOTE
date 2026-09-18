from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import List
from datetime import datetime, timezone

from app.database import get_db
from app.models import Voter, Election, PollingStation, User
from app.schemas import VoterCreate, VoterResponse, EligibilityCheckRequest, EligibilityCheckResponse
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/elections/{election_id}", tags=["Voters"])

def check_admin(user: User):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough permissions")

def check_admin_or_auditor(user: User):
    if user.role not in ["ADMIN", "AUDITOR"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

def calculate_age(dob: str) -> int:
    try:
        birth_date = datetime.strptime(dob, "%Y-%m-%d")
        today = datetime.now(timezone.utc)
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except ValueError:
        return 0

@router.post("/voters", response_model=VoterResponse, status_code=201)
async def register_voter(election_id: str, voter_data: VoterCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin(current_user)

    # Check election
    election = await db.get(Election, election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    voter_id_number = f"VTR-{uuid.uuid4().hex[:8].upper()}"

    new_voter = Voter(
        election_id=election_id,
        voter_id_number=voter_id_number,
        name=voter_data.name,
        date_of_birth=voter_data.date_of_birth,
        constituency=voter_data.constituency,
        eligibility_status="PENDING",
        registration_status="REGISTERED"
    )
    db.add(new_voter)
    await db.commit()
    await db.refresh(new_voter)
    return new_voter

@router.get("/voters", response_model=List[VoterResponse])
async def list_voters(election_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_or_auditor(current_user)
    result = await db.execute(select(Voter).where(Voter.election_id == election_id))
    return result.scalars().all()

@router.get("/voters/{voter_id}", response_model=VoterResponse)
async def get_voter(election_id: str, voter_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_or_auditor(current_user)
    result = await db.execute(select(Voter).where(Voter.election_id == election_id, Voter.id == voter_id))
    voter = result.scalar_one_or_none()
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found")
    return voter

@router.post("/eligibility", response_model=EligibilityCheckResponse)
async def check_eligibility(election_id: str, req: EligibilityCheckRequest, db: AsyncSession = Depends(get_db)):
    if election_id != "mock-election":
        election = await db.get(Election, election_id)
        if not election:
            raise HTTPException(status_code=404, detail="Election not found")

    age = calculate_age(req.date_of_birth)
    reasons = []

    # Check constituency
    if election_id != "mock-election":
        ps_result = await db.execute(select(PollingStation).where(PollingStation.election_id == election_id))
        polling_stations = ps_result.scalars().all()
        valid_constituencies = {ps.constituency for ps in polling_stations}
    else:
        valid_constituencies = set()

    constituency_valid = req.constituency in valid_constituencies or not valid_constituencies
    if not constituency_valid and valid_constituencies:
        reasons.append("Constituency not found in this election")

    name_valid = len(req.name) >= 2
    if not name_valid:
        reasons.append("Name too short")

    if age < 16:
        reasons.append("Underage")

    if not (name_valid and constituency_valid):
        status = "NOT_ELIGIBLE"
    elif age < 16:
        status = "NOT_ELIGIBLE"
    elif age < 18:
        status = "NEEDS_REVIEW"
        if not reasons:
            reasons.append("Age verification required")
    else:
        status = "ELIGIBLE"

    if not reasons and status == "ELIGIBLE":
        reasons = ["All checks passed"]

    return EligibilityCheckResponse(
        status=status,
        reasons=reasons,
        voter_id=None,
        notice="SIMULATED ELIGIBILITY CHECK - NOT A REAL GOVERNMENT SERVICE"
    )

@router.get("/voter-lookup", response_model=VoterResponse)
async def lookup_voter(election_id: str, voter_id_number: str, db: AsyncSession = Depends(get_db)):
    query = select(Voter).where(Voter.voter_id_number == voter_id_number)
    if election_id != "mock-election":
        query = query.where(Voter.election_id == election_id)
    result = await db.execute(query)
    voter = result.scalar_one_or_none()
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found")
    return voter
