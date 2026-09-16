"""
Vote service for SecureVOTE.

Handles voting session authorization and ballot recording with strict
integrity checks: duplicate-session prevention, replay protection,
and deterministic ballot hashing.

Note: voter anonymity is NOT preserved in this prototype â€” session
linkage exists for educational demonstration of audit trails.
"""

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ballot, Candidate, Device, Election, VotingSession
from app.schemas import SessionAuthorize, VoteCast, VoteResponse
from app.services.audit_service import AuditService
from app.utils.hashing import compute_ballot_hash
from app.utils.identifiers import generate_session_token, generate_uuid


class VoteService:
    """Voting session authorization and ballot recording."""

    @staticmethod
    async def authorize_session(
        db: AsyncSession,
        election_id: str,
        data: SessionAuthorize,
        actor: str,
    ) -> VotingSession:
        """
        Authorize a new voting session.

        Rejects duplicate sessions for the same voter_credential+election
        (spec Â§12 attack #3).
        """
        # Verify election exists and is OPEN
        election = await db.get(Election, election_id)
        if not election:
            raise HTTPException(status_code=404, detail=f"Election {election_id} not found.")
        if election.state != "OPEN":
            raise HTTPException(
                status_code=409,
                detail=f"Election not open (state={election.state}): REQUEST REJECTED",
            )

        # Verify device
        device = await db.get(Device, data.device_id)
        if not device:
            raise HTTPException(
                status_code=403,
                detail=f"DEVICE REJECTED: Unknown device {data.device_id}.",
            )
        if device.election_id != election_id:
            raise HTTPException(
                status_code=403,
                detail=f"DEVICE REJECTED: Device {data.device_id} not registered for this election.",
            )
        if device.status != "ACTIVE":
            raise HTTPException(
                status_code=403,
                detail=f"DEVICE REJECTED: Device {data.device_id} status is {device.status}.",
            )

        # Check for duplicate session (one credential per election)
        result = await db.execute(
            select(VotingSession).where(
                VotingSession.election_id == election_id,
                VotingSession.voter_credential == data.voter_credential,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="DUPLICATE_SESSION: REQUEST REJECTED",
            )

        session = VotingSession(
            election_id=election_id,
            device_id=data.device_id,
            session_token=generate_session_token(),
            voter_credential=data.voter_credential,
            status="AUTHORIZED",
        )
        db.add(session)
        await db.flush()

        await AuditService.log_event(
            db=db,
            election_id=election_id,
            event_type="SESSION_AUTHORIZED",
            event_data={
                "session_id": session.id,
                "device_id": data.device_id,
                # voter_credential logged for audit trail (educational prototype)
                "voter_credential": data.voter_credential,
            },
            actor=actor,
            device_id=data.device_id,
        )

        return session

    @staticmethod
    async def cast_vote(
        db: AsyncSession,
        data: VoteCast,
        actor: str,
    ) -> VoteResponse:
        """
        Record a ballot. This is the core voting transaction.

        Enforces: session validity, election state, device match,
        candidate existence, and replay protection via monotonic
        sequence numbers.
        """
        # Look up session by token
        result = await db.execute(
            select(VotingSession).where(
                VotingSession.session_token == data.session_token
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")

        # Session must be AUTHORIZED (not already VOTED/EXPIRED/REVOKED)
        if session.status != "AUTHORIZED":
            raise HTTPException(
                status_code=409,
                detail=f"Session status is {session.status}: REQUEST REJECTED",
            )

        # Election must be OPEN
        election = await db.get(Election, session.election_id)
        if not election or election.state != "OPEN":
            raise HTTPException(
                status_code=409,
                detail="Election not open: REQUEST REJECTED",
            )

        # Device must match the session's device
        if data.device_id != session.device_id:
            raise HTTPException(
                status_code=409,
                detail=f"Device mismatch: session bound to {session.device_id}, got {data.device_id}.",
            )

        # Validate device is still active
        device = await db.get(Device, data.device_id)
        if not device or device.status != "ACTIVE":
            raise HTTPException(
                status_code=403,
                detail=f"DEVICE REJECTED: Device {data.device_id} is not active.",
            )

        # Validate candidate exists and belongs to this election
        candidate = await db.get(Candidate, data.candidate_id)
        if not candidate or candidate.election_id != session.election_id:
            raise HTTPException(
                status_code=404,
                detail=f"Candidate {data.candidate_id} not found in this election.",
            )

        # Replay protection: sequence must be strictly increasing per device
        if data.sequence_number <= device.last_sequence_number:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"REPLAY REJECTED: sequence_number {data.sequence_number} "
                    f"<= last accepted {device.last_sequence_number}."
                ),
            )

        now = datetime.now(timezone.utc)
        ballot_id = generate_uuid()

        # Compute ballot hash
        ballot_hash = compute_ballot_hash(
            election_id=session.election_id,
            session_id=session.id,
            candidate_id=data.candidate_id,
            device_id=data.device_id,
            sequence_number=data.sequence_number,
            timestamp=now,
        )

        # Create ballot record
        ballot = Ballot(
            id=ballot_id,
            election_id=session.election_id,
            session_id=session.id,
            device_id=data.device_id,
            candidate_id=data.candidate_id,
            sequence_number=data.sequence_number,
            ballot_hash=ballot_hash,
            recorded_at=now,
        )
        db.add(ballot)

        # Update session
        session.status = "VOTED"
        session.voted_at = now

        # Update device counters
        device.last_sequence_number = data.sequence_number
        device.total_votes_cast += 1
        device.last_seen_at = now

        # Update election total
        election.total_ballots += 1

        await db.flush()

        # Audit: log vote WITHOUT candidate_id for educational separation
        await AuditService.log_event(
            db=db,
            election_id=session.election_id,
            event_type="VOTE_CAST",
            event_data={
                "ballot_id": ballot_id,
                "device_id": data.device_id,
                "sequence_number": data.sequence_number,
                "ballot_hash": ballot_hash,
            },
            actor=actor,
            device_id=data.device_id,
        )

        return VoteResponse(
            ballot_id=ballot_id,
            election_id=session.election_id,
            candidate_id=data.candidate_id,
            device_id=data.device_id,
            sequence_number=data.sequence_number,
            ballot_hash=ballot_hash,
            recorded_at=now,
        )

    @staticmethod
    async def get_session(db: AsyncSession, session_token: str) -> VotingSession:
        """Get a voting session by token."""
        result = await db.execute(
            select(VotingSession).where(
                VotingSession.session_token == session_token
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        return session

    @staticmethod
    async def get_election_ballots(
        db: AsyncSession, election_id: str
    ) -> list[Ballot]:
        """Return all ballots for an election ordered by recorded_at."""
        result = await db.execute(
            select(Ballot)
            .where(Ballot.election_id == election_id)
            .order_by(Ballot.recorded_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_election_sessions(
        db: AsyncSession, election_id: str
    ) -> list[VotingSession]:
        """Return all voting sessions for an election."""
        result = await db.execute(
            select(VotingSession)
            .where(VotingSession.election_id == election_id)
            .order_by(VotingSession.authorized_at)
        )
        return list(result.scalars().all())
