"""Results and verification router for SecureVOTE."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user, require_role
from app.schemas import VerificationResponse
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/api/elections/{election_id}", tags=["results"])


@router.get("/results", response_model=VerificationResponse)
async def get_results(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get election results with full independent verification.

    This endpoint does NOT return cached results — it independently
    recomputes tallies, verifies the audit chain, and runs reconciliation
    every time it is called.
    """
    return await VerificationService.run_full_verification(
        db, election_id, actor=current_user.username
    )


@router.post("/verify", response_model=VerificationResponse)
async def run_verification(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "AUDITOR")),
):
    """
    Run full independent verification and generate/update result manifest.
    Requires ADMIN or AUDITOR role.
    """
    return await VerificationService.run_full_verification(
        db, election_id, actor=current_user.username
    )
