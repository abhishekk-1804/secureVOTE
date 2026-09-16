"""Vote recording router for SecureVOTE."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user, require_role
from app.schemas import SessionAuthorize, SessionResponse, VoteCast, VoteResponse
from app.services.vote_service import VoteService

router = APIRouter(prefix="/api", tags=["votes"])


@router.post("/elections/{election_id}/sessions", response_model=SessionResponse, status_code=201)
async def authorize_session(
    election_id: str,
    data: SessionAuthorize,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    """Authorize a voting session. Requires ADMIN role."""
    session = await VoteService.authorize_session(
        db, election_id, data, actor=current_user.username
    )
    return session


@router.post("/votes", response_model=VoteResponse, status_code=201)
async def cast_vote(
    data: VoteCast,
    db: AsyncSession = Depends(get_db),
):
    """
    Cast a vote. Authenticated by session_token, not JWT.

    The session_token serves as the simulated credential/session
    authorization for this educational prototype.
    """
    vote = await VoteService.cast_vote(db, data, actor="voter")
    return vote


@router.get("/elections/{election_id}/sessions", response_model=list[SessionResponse])
async def list_sessions(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "AUDITOR")),
):
    """List all voting sessions for an election. Requires ADMIN or AUDITOR role."""
    return await VoteService.get_election_sessions(db, election_id)
