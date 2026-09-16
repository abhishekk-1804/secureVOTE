"""
Signing router for SecureVOTE.

Provides endpoints for:
- Retrieving public key verification metadata
- Signing a result manifest for a CLOSED/PUBLISHED election (Admin/Auditor only)
- Verifying an Ed25519 signature on an arbitrary canonical payload
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user, require_role
from app.schemas import (
    PublicKeyInfoResponse,
    SignedManifestResponse,
    VerifySignatureRequest,
    VerifySignatureResponse,
)
from app.services.signing_service import SigningService

router = APIRouter(prefix="/api/signing", tags=["signing"])
election_signing_router = APIRouter(prefix="/api/elections/{election_id}", tags=["signing"])


@router.get("/public-key", response_model=PublicKeyInfoResponse)
async def get_public_key_info():
    """
    Retrieve active public key metadata for signature verification.
    Never exposes private key material.
    """
    info = SigningService.get_public_key_metadata()
    return PublicKeyInfoResponse(**info)


@router.post("/verify", response_model=VerifySignatureResponse)
async def verify_signature(request: VerifySignatureRequest):
    """
    Verify an Ed25519 digital signature against a JSON payload.
    Uses provided public key, or the system active public key if omitted.
    """
    pub_hex = request.public_key
    if not pub_hex:
        pub = SigningService.get_configured_public_key()
        if not pub:
            raise HTTPException(
                status_code=400,
                detail="No public key provided and no system public key configured.",
            )
        pub_hex = SigningService.get_public_key_hex(pub)

    is_valid = SigningService.verify_signature(
        payload=request.payload,
        signature_hex=request.signature,
        public_key_hex=pub_hex,
    )

    fingerprint = None
    try:
        raw_bytes = bytes.fromhex(pub_hex)
        import hashlib
        fingerprint = hashlib.sha256(raw_bytes).hexdigest()
    except Exception:
        pass

    return VerifySignatureResponse(
        valid=is_valid,
        algorithm="Ed25519",
        details="Signature verified successfully." if is_valid else "Signature verification failed.",
        key_id=f"ed25519-{fingerprint[:8]}" if fingerprint else None,
        fingerprint=fingerprint,
    )


@election_signing_router.post("/sign-manifest", response_model=SignedManifestResponse)
async def sign_election_manifest(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "AUDITOR")),
):
    """
    Digitally sign the Result Manifest of an election.
    Enforces that election must be CLOSED or PUBLISHED with an EXACT_MATCH reconciliation.
    Requires ADMIN or AUDITOR role.
    """
    manifest = await SigningService.sign_manifest(
        db=db,
        election_id=election_id,
        actor=current_user.username,
    )

    sig_data = json.loads(manifest.digital_signature) if manifest.digital_signature else {}

    return SignedManifestResponse(
        manifest_id=manifest.id,
        election_id=election_id,
        manifest_hash=manifest.manifest_hash,
        digital_signature=sig_data,
        signed_at=manifest.verified_at,
        signed_by=manifest.verified_by or current_user.username,
    )
