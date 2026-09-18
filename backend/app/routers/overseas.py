"""
Dual-Mode Overseas / NRI Elector Simulation Router for SecureVOTE 2.0.

Provides:
- Mode A: Current statutory in-person rule (Form 6A enrollment, in-person passport verification at home polling station)
- Mode B: Overseas Consular Research Lab (dual-control key custody, cryptographic diplomatic receipt, explicitly labeled research proposal)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, List
import hashlib
import uuid
from datetime import datetime, timezone

from app.database import get_db
from app.models import Election, Voter, PollingStation
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter(prefix="/api/overseas", tags=["Overseas / NRI Simulation"])


class Form6ASubmission(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    passport_number: str = Field(..., min_length=6, max_length=15)
    country_of_residence: str = Field(..., min_length=2, max_length=100)
    visa_type: str = Field(..., min_length=2, max_length=50)
    home_constituency: str = Field(..., min_length=2, max_length=100)
    date_of_birth: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class ConsularSimulationRequest(BaseModel):
    passport_number: str
    country: str
    consulate_city: str
    election_id: str


@router.get("/framework")
async def get_overseas_framework():
    """Returns statutory vs research framework comparison for NRI voting."""
    return {
        "mode_a": {
            "name": "Current Statutory Rule (In-Person)",
            "statutory_basis": "Representation of the People Act, 1950 (Section 20A)",
            "procedure": "Overseas citizens submit Form 6A to be enrolled in their home constituency. Voting requires physical presence at their registered polling booth with original passport.",
            "status": "CURRENT_LAW",
            "remote_voting_permitted": False,
        },
        "mode_b": {
            "name": "Consular Research Prototype (Research Proposal)",
            "statutory_basis": "Proposed Educational Research Framework (Not statutory law)",
            "procedure": "Dual-control cryptographic session authorization at designated Indian Consulates/Embassies with diplomatic pouch hash chain and hardware zero-knowledge token.",
            "status": "RESEARCH_PROPOSAL",
            "remote_voting_permitted": True,
            "disclaimer": "This is an academic research prototype and not recognized by the Election Commission of India.",
        },
    }


@router.post("/form6a")
async def submit_form_6a(data: Form6ASubmission, db: AsyncSession = Depends(get_db)):
    """Simulate Form 6A submission for overseas voter registration."""
    # Hash passport to avoid storing raw identity plaintext
    passport_hash = hashlib.sha256(data.passport_number.encode("utf-8")).hexdigest()[:16]
    ref_number = f"NRI-6A-{uuid.uuid4().hex[:6].upper()}"

    # Verify if home constituency matches an active simulation
    ps_res = await db.execute(select(PollingStation).where(PollingStation.constituency == data.home_constituency))
    station = ps_res.scalars().first()

    assigned_station_code = station.station_code if station else "PS-001 (Default Allocated)"

    return {
        "status": "APPROVED",
        "reference_number": ref_number,
        "applicant_name": data.full_name,
        "passport_pseudonym": f"PASS-{passport_hash}",
        "country": data.country_of_residence,
        "visa_status": data.visa_type,
        "registered_constituency": data.home_constituency,
        "assigned_polling_station": assigned_station_code,
        "enrollment_category": "OVERSEAS_ELECTOR_SEC_20A",
        "voting_requirement": "Must present original passport in person at the assigned polling station on poll day.",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/consular-simulate")
async def simulate_consular_session(req: ConsularSimulationRequest, db: AsyncSession = Depends(get_db)):
    """Mode B: Simulate dual-control consular voting research session."""
    el = await db.get(Election, req.election_id)
    if not el:
        raise HTTPException(status_code=404, detail="Election not found")

    token_seed = f"{req.passport_number}:{req.country}:{req.consulate_city}:{req.election_id}"
    session_hash = hashlib.sha256(token_seed.encode("utf-8")).hexdigest()

    return {
        "mode": "RESEARCH_CONSULAR_LAB",
        "consulate": f"Embassy/Consulate General of India, {req.consulate_city}, {req.country}",
        "session_token": f"CONSULAR-{session_hash[:16].upper()}",
        "diplomatic_custody_hash": hashlib.sha256(session_hash.encode("utf-8")).hexdigest(),
        "dual_custody_officers": ["Consular Officer A (Authorized)", "Consular Officer B (Witness)"],
        "tamper_evident_seal_id": f"SEAL-DIP-{uuid.uuid4().hex[:6].upper()}",
        "advisory_notice": "RESEARCH DEMONSTRATION ONLY -- Not recognized in actual elections.",
    }
