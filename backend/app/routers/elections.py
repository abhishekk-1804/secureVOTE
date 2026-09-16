"""Election management router for SecureVOTE."""

import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditEntry, Ballot, Candidate, Device, Election, ResultManifest, User
from app.routers.auth import get_current_user, require_role
from app.schemas import (
    CandidateBatchCreate,
    CandidateResponse,
    ElectionCreate,
    ElectionExportResponse,
    ElectionListResponse,
    ElectionResponse,
    ElectionStateChange,
    SuccessResponse,
)
from app.services.election_service import ElectionService
from app.utils.hashing import format_iso_timestamp


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


@router.get("/{election_id}/export", response_model=ElectionExportResponse)
async def export_election(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export complete election archive for offline independent machine verification.
    Contains raw candidates, devices, ballots, audit entries, and cryptographic manifest.
    """
    election = await db.get(Election, election_id)
    if not election:
        raise HTTPException(status_code=404, detail=f"Election {election_id} not found.")

    candidates_res = await db.execute(
        select(Candidate)
        .where(Candidate.election_id == election_id)
        .order_by(Candidate.position)
    )
    candidates = candidates_res.scalars().all()

    devices_res = await db.execute(
        select(Device)
        .where(Device.election_id == election_id)
        .order_by(Device.id)
    )
    devices = devices_res.scalars().all()

    ballots_res = await db.execute(
        select(Ballot)
        .where(Ballot.election_id == election_id)
        .order_by(Ballot.device_id, Ballot.sequence_number)
    )
    ballots = ballots_res.scalars().all()

    audit_res = await db.execute(
        select(AuditEntry)
        .where(AuditEntry.election_id == election_id)
        .order_by(AuditEntry.sequence_number)
    )
    audit_log = audit_res.scalars().all()

    manifest_res = await db.execute(
        select(ResultManifest)
        .where(ResultManifest.election_id == election_id)
        .order_by(ResultManifest.generated_at.desc())
        .limit(1)
    )
    manifest = manifest_res.scalar_one_or_none()

    now = datetime.now(timezone.utc).isoformat()

    candidates_data = [
        {
            "id": c.id,
            "name": c.name,
            "party": c.party,
            "symbol": c.symbol,
            "position": c.position,
        }
        for c in candidates
    ]

    devices_data = [
        {
            "id": d.id,
            "name": d.name,
            "status": d.status,
            "last_sequence_number": d.last_sequence_number,
            "total_votes_cast": d.total_votes_cast,
            "registered_at": d.registered_at.isoformat(),
            "activated_at": d.activated_at.isoformat() if d.activated_at else None,
            "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
        }
        for d in devices
    ]

    ballots_data = [
        {
            "id": b.id,
            "session_id": b.session_id,
            "device_id": b.device_id,
            "candidate_id": b.candidate_id,
            "sequence_number": b.sequence_number,
            "ballot_hash": b.ballot_hash,
            "recorded_at": b.recorded_at.isoformat(),
        }
        for b in ballots
    ]

    audit_data = [
        {
            "id": a.id,
            "sequence_number": a.sequence_number,
            "event_type": a.event_type,
            "event_data": a.event_data,
            "actor": a.actor,
            "device_id": a.device_id,
            "timestamp": format_iso_timestamp(a.timestamp),
            "previous_hash": a.previous_hash,

            "entry_hash": a.entry_hash,
        }
        for a in audit_log
    ]

    manifest_data = None
    if manifest:
        manifest_data = {
            "id": manifest.id,
            "election_id": manifest.election_id,
            "total_ballots": manifest.total_ballots,
            "candidate_totals": manifest.candidate_totals,
            "device_totals": manifest.device_totals,
            "reconciliation_status": manifest.reconciliation_status,
            "audit_chain_status": manifest.audit_chain_status,
            "configuration_hash": manifest.configuration_hash,
            "manifest_hash": manifest.manifest_hash,
            "digital_signature": manifest.digital_signature,
            "generated_at": manifest.generated_at.isoformat(),
            "verified_at": manifest.verified_at.isoformat() if manifest.verified_at else None,
            "verified_by": manifest.verified_by,
        }

    election_meta = {
        "id": election.id,
        "name": election.name,
        "description": election.description,
        "state": election.state,
        "configuration_hash": election.configuration_hash,
        "total_ballots": election.total_ballots,
        "created_at": election.created_at.isoformat(),
        "locked_at": election.locked_at.isoformat() if election.locked_at else None,
        "opened_at": election.opened_at.isoformat() if election.opened_at else None,
        "closed_at": election.closed_at.isoformat() if election.closed_at else None,
        "published_at": election.published_at.isoformat() if election.published_at else None,
    }

    raw_payload = {
        "export_version": "1.0.0",
        "exported_at": now,
        "election": election_meta,
        "candidates": candidates_data,
        "devices": devices_data,
        "ballots": ballots_data,
        "audit_log": audit_data,
        "manifest": manifest_data,
    }

    canonical_json = json.dumps(raw_payload, sort_keys=True)
    export_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    raw_payload["export_hash"] = export_hash
    return raw_payload
