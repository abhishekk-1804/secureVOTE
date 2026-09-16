"""Election management router for SecureVOTE."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user, require_role
from app.schemas import (
    CandidateBatchCreate,
    CandidateResponse,
    ElectionCreate,
    ElectionListResponse,
    ElectionResponse,
    ElectionStateChange,
    SuccessResponse,
)
from app.services.election_service import ElectionService

router = APIRouter(prefix="/api/elections", tags=["elections"])


@router.post("", response_model=ElectionResponse, status_code=201)
async def create_election(
    data: ElectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    """Create a new election. Requires ADMIN role."""
    election = await ElectionService.create_election(db, data, actor=current_user.username)
    return election


@router.get("", response_model=ElectionListResponse)
async def list_elections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all elections."""
    elections = await ElectionService.list_elections(db)
    return ElectionListResponse(elections=elections, total=len(elections))


@router.get("/{election_id}", response_model=ElectionResponse)
async def get_election(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get election details with candidates and device count."""
    election = await ElectionService.get_election(db, election_id)
    return election


@router.post("/{election_id}/candidates", response_model=list[CandidateResponse], status_code=201)
async def add_candidates(
    election_id: str,
    data: CandidateBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    """Add candidates to an election. Requires ADMIN role."""
    candidates = await ElectionService.add_candidates(db, election_id, data, actor=current_user.username)
    return candidates


@router.get("/{election_id}/candidates", response_model=list[CandidateResponse])
async def get_candidates(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get candidates for an election."""
    return await ElectionService.get_candidates(db, election_id)


@router.patch("/{election_id}/state", response_model=ElectionResponse)
async def change_state(
    election_id: str,
    data: ElectionStateChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    """Change election state. Enforces strict state machine transitions. Requires ADMIN role."""
    election = await ElectionService.change_state(db, election_id, data, actor=current_user.username)
    return election
