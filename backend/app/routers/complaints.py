from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timezone

from app.database import get_db
from app.models import Complaint, User
from app.schemas import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

def check_admin(user: User):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough permissions")

def check_admin_or_auditor(user: User):
    if user.role not in ["ADMIN", "AUDITOR"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

@router.post("", response_model=ComplaintResponse, status_code=201)
async def submit_complaint(complaint_data: ComplaintCreate, db: AsyncSession = Depends(get_db)):
    year = datetime.now(timezone.utc).year
    # Get max sequence for current year
    result = await db.execute(select(Complaint.reference_number).where(Complaint.reference_number.like(f"GRV-{year}-%")))
    refs = result.scalars().all()
    seq = 1
    if refs:
        seqs = [int(r.split("-")[-1]) for r in refs if r.split("-")[-1].isdigit()]
        if seqs:
            seq = max(seqs) + 1

    reference_number = f"GRV-{year}-{seq:05d}"

    new_complaint = Complaint(
        election_id=complaint_data.election_id,
        reference_number=reference_number,
        category=complaint_data.category,
        description=complaint_data.description,
        complainant_name=complaint_data.complainant_name,
        complainant_contact=complaint_data.complainant_contact,
        status="SUBMITTED"
    )
    db.add(new_complaint)
    await db.commit()
    await db.refresh(new_complaint)
    return new_complaint

@router.get("", response_model=List[ComplaintResponse])
async def list_complaints(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin_or_auditor(current_user)
    result = await db.execute(select(Complaint))
    return result.scalars().all()

@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(complaint_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if complaint_id == "track":
        raise HTTPException(status_code=400, detail="Invalid complaint id")
    check_admin_or_auditor(current_user)
    complaint = await db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@router.get("/track/{reference_number}", response_model=ComplaintResponse)
async def track_complaint(reference_number: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Complaint).where(Complaint.reference_number == reference_number))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
async def update_complaint_status(complaint_id: str, status_data: ComplaintStatusUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin(current_user)
    complaint = await db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint.status = status_data.status
    if status_data.assigned_officer is not None:
        complaint.assigned_officer = status_data.assigned_officer
    if status_data.resolution_notes is not None:
        complaint.resolution_notes = status_data.resolution_notes

    await db.commit()
    await db.refresh(complaint)
    return complaint
