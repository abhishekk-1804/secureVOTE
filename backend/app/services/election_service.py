"""
Election lifecycle service for SecureVOTE.

Manages the election state machine with strict transition validation:
CREATED → CONFIGURED → LOCKED → OPEN → SUSPENDED/CLOSED → PUBLISHED

Configuration is frozen and hashed at the LOCKED transition. Any attempt
to modify candidates after locking will produce a CONFIGURATION HASH MISMATCH.
"""

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Candidate, Device, Election
from app.schemas import (
    CandidateBatchCreate,
    ElectionCreate,
    ElectionStateChange,
)
from app.services.audit_service import AuditService
from app.services.websocket_service import websocket_manager
from app.utils.hashing import compute_configuration_hash



# Valid state transitions for the election lifecycle
VALID_TRANSITIONS: dict[str, list[str]] = {
    "CREATED": ["CONFIGURED"],
    "CONFIGURED": ["LOCKED"],
    "LOCKED": ["OPEN"],
    "OPEN": ["SUSPENDED", "CLOSED"],
    "SUSPENDED": ["OPEN", "CLOSED"],
    "CLOSED": ["PUBLISHED"],
    "PUBLISHED": [],
}


class ElectionService:
    """Service for managing the election lifecycle with strict state machine transitions."""

    @staticmethod
    async def create_election(
        db: AsyncSession, data: ElectionCreate, actor: str
    ) -> Election:
        """Create a new election in CREATED state."""
        result = await db.execute(select(Election).where(Election.id == data.id))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Election with this ID already exists.")

        election = Election(
            id=data.id,
            name=data.name,
            description=data.description,
            state="CREATED",
        )
        db.add(election)
        await db.flush()

        await AuditService.log_event(
            db=db,
            election_id=election.id,
            event_type="ELECTION_CREATED",
            event_data={"election_id": election.id, "name": election.name},
            actor=actor,
        )
        return await ElectionService.get_election(db, election.id)

    @staticmethod
    async def get_election(db: AsyncSession, election_id: str) -> Election:
        """Fetch election with eager loading of candidates and devices."""
        result = await db.execute(
            select(Election)
            .options(selectinload(Election.candidates), selectinload(Election.devices))
            .where(Election.id == election_id)
        )
        election = result.scalar_one_or_none()
        if not election:
            raise HTTPException(status_code=404, detail=f"Election {election_id} not found.")
        return election

    @staticmethod
    async def list_elections(db: AsyncSession) -> list[Election]:
        """Return all elections ordered by created_at desc."""
        result = await db.execute(
            select(Election)
            .options(selectinload(Election.candidates), selectinload(Election.devices))
            .order_by(Election.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_candidates(
        db: AsyncSession,
        election_id: str,
        data: CandidateBatchCreate,
        actor: str,
    ) -> list[Candidate]:
        """
        Add candidates to an election.

        Election must be in CREATED state. Auto-transitions to CONFIGURED
        when 2+ candidates exist.
        """
        election = await ElectionService.get_election(db, election_id)
        if election.state != "CREATED":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot add candidates in {election.state} state. Must be CREATED.",
            )

        # Check existing candidates
        existing_result = await db.execute(
            select(Candidate).where(Candidate.election_id == election_id)
        )
        existing_candidates = list(existing_result.scalars().all())
        existing_ids = {c.id for c in existing_candidates}
        existing_positions = {c.position for c in existing_candidates}

        new_candidates = []
        for c_data in data.candidates:
            if c_data.id in existing_ids:
                raise HTTPException(status_code=409, detail=f"Duplicate candidate ID: {c_data.id}")
            if c_data.position in existing_positions:
                raise HTTPException(
                    status_code=409, detail=f"Duplicate candidate position: {c_data.position}"
                )
            existing_ids.add(c_data.id)
            existing_positions.add(c_data.position)

            candidate = Candidate(**c_data.model_dump(), election_id=election_id)
            db.add(candidate)
            new_candidates.append(candidate)

        await db.flush()

        # Auto-transition to CONFIGURED if we have enough candidates
        total_candidates = len(existing_candidates) + len(new_candidates)
        if total_candidates >= 2:
            election.state = "CONFIGURED"
            election.configured_at = datetime.now(timezone.utc)
            await db.flush()

        await AuditService.log_event(
            db=db,
            election_id=election_id,
            event_type="CANDIDATES_ADDED",
            event_data={
                "count": len(new_candidates),
                "candidate_ids": [c.id for c in new_candidates],
                "auto_configured": total_candidates >= 2,
            },
            actor=actor,
        )

        return new_candidates

    @staticmethod
    async def change_state(
        db: AsyncSession,
        election_id: str,
        data: ElectionStateChange,
        actor: str,
    ) -> Election:
        """
        Change election state with strict transition validation.

        Invalid transitions are rejected. Special logic:
        - CONFIGURED→LOCKED: computes and stores configuration hash
        - LOCKED→OPEN: requires at least 1 ACTIVE device
        """
        election = await ElectionService.get_election(db, election_id)
        old_state = election.state
        new_state = data.new_state

        allowed = VALID_TRANSITIONS.get(old_state, [])
        if new_state not in allowed:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Invalid state transition: {old_state} → {new_state}. "
                    f"Valid transitions from {old_state}: {allowed}"
                ),
            )

        now = datetime.now(timezone.utc)

        # Transition-specific logic
        if old_state == "CONFIGURED" and new_state == "LOCKED":
            candidates = await ElectionService.get_candidates(db, election_id)
            candidate_dicts = [
                {
                    "id": c.id,
                    "name": c.name,
                    "party": c.party,
                    "symbol": c.symbol,
                    "position": c.position,
                }
                for c in candidates
            ]
            election.configuration_hash = compute_configuration_hash(
                election_id, candidate_dicts
            )
            election.locked_at = now

        elif old_state == "LOCKED" and new_state == "OPEN":
            result = await db.execute(
                select(func.count()).where(
                    Device.election_id == election_id,
                    Device.status == "ACTIVE",
                )
            )
            active_devices = result.scalar_one()
            if active_devices < 1:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot open election: no ACTIVE devices registered.",
                )
            election.opened_at = now

        elif new_state == "CLOSED":
            election.closed_at = now

        elif new_state == "PUBLISHED":
            election.published_at = now

        election.state = new_state
        await db.flush()

        await AuditService.log_event(
            db=db,
            election_id=election_id,
            event_type="STATE_CHANGE",
            event_data={
                "old_state": old_state,
                "new_state": new_state,
                "reason": data.reason,
            },
            actor=actor,
        )

        await websocket_manager.broadcast(
            election_id=election_id,
            event_type="ELECTION_STATE_CHANGED",
            data={
                "election_id": election_id,
                "old_state": old_state,
                "new_state": new_state,
                "reason": data.reason,
            },
        )

        return await ElectionService.get_election(db, election_id)


    @staticmethod
    async def get_candidates(
        db: AsyncSession, election_id: str
    ) -> list[Candidate]:
        """Return candidates for the election ordered by position."""
        result = await db.execute(
            select(Candidate)
            .where(Candidate.election_id == election_id)
            .order_by(Candidate.position)
        )
        return list(result.scalars().all())

    @staticmethod
    async def verify_configuration(
        db: AsyncSession, election_id: str
    ) -> tuple[bool, str, str]:
        """
        Recompute configuration hash from current candidates and compare
        with the stored hash. Returns (is_valid, stored_hash, computed_hash).

        Any mismatch indicates configuration was modified after locking —
        a CONFIGURATION HASH MISMATCH (spec §12 attack #2).
        """
        election = await ElectionService.get_election(db, election_id)
        candidates = await ElectionService.get_candidates(db, election_id)

        candidate_dicts = [
            {
                "id": c.id,
                "name": c.name,
                "party": c.party,
                "symbol": c.symbol,
                "position": c.position,
            }
            for c in candidates
        ]
        computed_hash = compute_configuration_hash(election_id, candidate_dicts)
        stored_hash = election.configuration_hash or ""
        is_valid = computed_hash == stored_hash

        return (is_valid, stored_hash, computed_hash)
