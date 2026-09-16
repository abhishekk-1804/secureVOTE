"""Audit log router for SecureVOTE."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import AuditEntryResponse, AuditLogResponse, AuditVerificationResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/elections/{election_id}/audit", tags=["audit"])


@router.get("", response_model=AuditLogResponse)
async def get_audit_log(
    election_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated audit log for an election."""
    entries, total = await AuditService.get_audit_log(db, election_id, limit, offset)

    # Determine chain status (quick check â€” full verify is a separate endpoint)
    chain_status = "UNCHECKED"
    if total > 0:
        verification = await AuditService.verify_chain(db, election_id)
        chain_status = "INTACT" if verification["is_intact"] else "BROKEN"

    return AuditLogResponse(
        entries=[AuditEntryResponse.model_validate(e) for e in entries],
        total=total,
        chain_status=chain_status,
    )


@router.get("/verify", response_model=AuditVerificationResponse)
async def verify_audit_chain(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Independently verify the audit hash chain.

    Recomputes every hash from raw record data â€” does NOT read any
    precomputed verification flag.
    """
    result = await AuditService.verify_chain(db, election_id)
    return AuditVerificationResponse(**result)
