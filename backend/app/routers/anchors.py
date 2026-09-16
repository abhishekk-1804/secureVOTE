"""
Anchor router for SecureVOTE.

Provides endpoints for:
- Creating an anchor for an election's audit root (Local or External)
- Retrieving anchor receipt by reference
- Verifying an anchor reference against a root hash
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user, require_role
from app.schemas import (
    AnchorReceiptResponse,
    AnchorRequest,
    VerifyAnchorResponse,
)
from app.services.anchor_service import AnchorService

router = APIRouter(prefix="/api/anchors", tags=["anchoring"])
election_anchor_router = APIRouter(prefix="/api/elections/{election_id}/anchor", tags=["anchoring"])


@election_anchor_router.post("", response_model=AnchorReceiptResponse)
async def anchor_election_root(
    election_id: str,
    request: AnchorRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "AUDITOR")),
):
    """
    Anchor the current audit root hash of an election.
    Supports LOCAL and EXTERNAL providers.
    Requires ADMIN or AUDITOR role.
    """
    receipt = await AnchorService.anchor_election_root(
        db=db,
        election_id=election_id,
        provider_type=request.provider_type,
        actor=current_user.username,
    )
    return AnchorReceiptResponse(
        anchor_id=receipt.anchor_id,
        election_id=receipt.election_id,
        root_hash=receipt.root_hash,
        provider_type=receipt.provider_type,
        anchor_reference=receipt.anchor_reference,
        status=receipt.status,
        anchored_at=receipt.anchored_at,
        metadata=receipt.metadata,
    )


@election_anchor_router.get("/verify", response_model=VerifyAnchorResponse)
async def verify_election_anchor(
    election_id: str,
    reference: str,
    root_hash: str | None = None,
    provider_type: str = "LOCAL",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verify that an anchor reference commits to an authentic audit root hash of the election.
    If root_hash query param is provided, checks exact match.
    Otherwise checks that the anchored root exists as a valid entry in the election's audit chain.
    """
    from sqlalchemy import select
    from app.models import AuditEntry

    receipt = await AnchorService.get_anchor(reference, provider_type=provider_type)
    if not receipt:
        return VerifyAnchorResponse(
            verified=False,
            status="NOT ANCHORED",
            provider_type=provider_type,
            anchor_reference=reference,
            root_hash=root_hash or "",
            details=f"Anchor reference '{reference}' not found.",
        )

    if root_hash:
        is_valid = receipt.root_hash.lower() == root_hash.lower()
    else:
        # Check that the receipt's committed root_hash exists in this election's audit entries
        entry_match = await db.execute(
            select(AuditEntry).where(
                AuditEntry.election_id == election_id,
                AuditEntry.entry_hash == receipt.root_hash,
            )
        )
        is_valid = entry_match.scalar_one_or_none() is not None

    return VerifyAnchorResponse(
        verified=is_valid,
        status=receipt.status if is_valid else "ANCHOR VERIFICATION FAILED",
        provider_type=receipt.provider_type,
        anchor_reference=reference,
        root_hash=receipt.root_hash,
        details=(
            "Anchor root hash verified against election audit chain."
            if is_valid
            else "Anchor root hash mismatch or not found in audit chain."
        ),
    )


@router.get("/{reference}", response_model=AnchorReceiptResponse)
async def get_anchor_by_reference(
    reference: str,
    provider_type: str = "LOCAL",
    current_user: User = Depends(get_current_user),
):
    """Retrieve anchor commitment receipt by reference."""
    receipt = await AnchorService.get_anchor(reference, provider_type=provider_type)
    if not receipt:
        raise HTTPException(status_code=404, detail=f"Anchor reference '{reference}' not found")

    return AnchorReceiptResponse(
        anchor_id=receipt.anchor_id,
        election_id=receipt.election_id,
        root_hash=receipt.root_hash,
        provider_type=receipt.provider_type,
        anchor_reference=receipt.anchor_reference,
        status=receipt.status,
        anchored_at=receipt.anchored_at,
        metadata=receipt.metadata,
    )
