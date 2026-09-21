"""
FastAPI Router for SecureVOTE 3.0 Cryptographic Research API.
"""

import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.crypto import PROTOCOL_VERSION
from app.crypto.elgamal import ElGamalPrivateKey, ElGamalPublicKey, G, scalar_mult
from app.schemas_v3 import (
    V3AggregateTallyRequest,
    V3CastBallotRequest,
    V3CastBallotResponse,
    V3DecryptTallyRequest,
    V3EncryptBallotRequest,
    V3InitElectionRequest,
    V3InitElectionResponse,
    V3TallyResponse,
    V3VerifyRequest,
    V3VerifyResponse,
)
from app.services.crypto_v3_service import CryptoV3Service
from standalone_verifier.v3_verifier import StandaloneV3ElectionVerifier

router = APIRouter(prefix="/api/v3/crypto", tags=["SecureVOTE 3.0 Crypto"])


@router.post("/elections/init", response_model=V3InitElectionResponse)
async def init_crypto_election(
    req: V3InitElectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initialize a new v3 cryptographic research election."""
    crypto_el = await CryptoV3Service.init_election(db, req.election_id, req.candidates)
    return V3InitElectionResponse(
        election_id=crypto_el.election_id,
        protocol_version=crypto_el.protocol_version,
        key_fingerprint=crypto_el.key_fingerprint,
        public_key=json.loads(crypto_el.public_key_json),
        candidate_count=crypto_el.candidate_count,
        candidates=json.loads(crypto_el.candidate_ids_json),
        status=crypto_el.status,
    )


@router.get("/elections/{election_id}", response_model=V3InitElectionResponse)
async def get_crypto_election(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve v3 election public parameters and key metadata."""
    crypto_el = await CryptoV3Service.get_election(db, election_id)
    return V3InitElectionResponse(
        election_id=crypto_el.election_id,
        protocol_version=crypto_el.protocol_version,
        key_fingerprint=crypto_el.key_fingerprint,
        public_key=json.loads(crypto_el.public_key_json),
        candidate_count=crypto_el.candidate_count,
        candidates=json.loads(crypto_el.candidate_ids_json),
        status=crypto_el.status,
    )


@router.post("/ballots/encrypt")
async def encrypt_ballot_endpoint(
    req: V3EncryptBallotRequest,
    db: AsyncSession = Depends(get_db),
):
    """Client helper endpoint: encrypt a vote choice using the election public key."""
    artifact = await CryptoV3Service.encrypt_ballot_for_voter(
        db, req.election_id, req.candidate_index, with_zkp=req.with_zkp
    )
    return artifact


@router.post("/ballots/cast", response_model=V3CastBallotResponse)
async def cast_ballot_endpoint(
    req: V3CastBallotRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit an encrypted ballot artifact."""
    record = await CryptoV3Service.cast_ballot(db, req.election_id, req.ballot_artifact)
    ballots = await CryptoV3Service.get_ballots(db, req.election_id)
    return V3CastBallotResponse(
        status="RECORDED",
        artifact_id=record.artifact_id,
        commitment=record.commitment,
        artifact_hash=record.artifact_hash,
        ballot_count=len(ballots),
    )


@router.get("/ballots/{election_id}")
async def list_ballots_endpoint(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all cast encrypted ballot artifacts for an election."""
    ballots = await CryptoV3Service.get_ballots(db, election_id)
    return {
        "election_id": election_id,
        "total_ballots": len(ballots),
        "ballots": ballots,
    }


@router.post("/tally/aggregate", response_model=V3TallyResponse)
async def aggregate_tally_endpoint(
    req: V3AggregateTallyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Compute homomorphic aggregate tally from all cast encrypted ballots."""
    t_record = await CryptoV3Service.aggregate_tally(db, req.election_id)
    return V3TallyResponse(
        election_id=req.election_id,
        protocol_version=PROTOCOL_VERSION,
        ballot_count=t_record.ballot_count,
        status=t_record.status,
        commitment=t_record.commitment,
        artifact_hash=t_record.artifact_hash,
        encrypted_tally=json.loads(t_record.encrypted_tally_json),
        decrypted_tally=json.loads(t_record.decrypted_tally_json) if t_record.decrypted_tally_json else None,
    )


@router.post("/tally/decrypt")
async def decrypt_tally_endpoint(
    req: V3DecryptTallyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Decrypt the aggregate tally."""
    override_priv = None
    if req.private_key_scalar_hex:
        scalar = int(req.private_key_scalar_hex, 16)
        pub_pt = scalar_mult(scalar, G)
        pub = ElGamalPublicKey(point=pub_pt)
        override_priv = ElGamalPrivateKey(scalar=scalar, public_key=pub)

    decrypted = await CryptoV3Service.decrypt_tally(db, req.election_id, override_priv)
    return decrypted


@router.get("/tally/{election_id}", response_model=V3TallyResponse)
async def get_tally_endpoint(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get published encrypted / decrypted tally."""
    crypto_el = await CryptoV3Service.get_election(db, election_id)
    from sqlalchemy import select
    from app.models_v3 import V3EncryptedTally
    stmt = select(V3EncryptedTally).where(V3EncryptedTally.crypto_election_id == crypto_el.id)
    t_record = (await db.execute(stmt)).scalar_one_or_none()
    if not t_record:
        raise HTTPException(status_code=404, detail="Tally not found for this election")

    return V3TallyResponse(
        election_id=election_id,
        protocol_version=PROTOCOL_VERSION,
        ballot_count=t_record.ballot_count,
        status=t_record.status,
        commitment=t_record.commitment,
        artifact_hash=t_record.artifact_hash,
        encrypted_tally=json.loads(t_record.encrypted_tally_json),
        decrypted_tally=json.loads(t_record.decrypted_tally_json) if t_record.decrypted_tally_json else None,
    )


@router.get("/export/{election_id}")
async def export_package_endpoint(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Export self-contained v3 election package for standalone verification."""
    package = await CryptoV3Service.export_package(db, election_id)
    return package


@router.get("/bundle/{election_id}")
async def export_bundle_endpoint(
    election_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Export self-contained SECUREVOTE-EVIDENCE-BUNDLE-1 manifest and artifacts."""
    import tempfile
    package = await CryptoV3Service.export_package(db, election_id)

    from app.services.signing_service import SigningService
    signing_key = SigningService.get_configured_private_key()
    priv_hex = None
    if signing_key:
        from cryptography.hazmat.primitives import serialization
        priv_bytes = signing_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        priv_hex = priv_bytes.hex()

    temp_dir = tempfile.mkdtemp(prefix=f"bundle_{election_id}_")
    from standalone_verifier.bundle_export import export_bundle
    bundle_dir = os.path.join(temp_dir, f"evidence_bundle_{election_id}")
    manifest = export_bundle(
        package=package,
        output_dir=bundle_dir,
        signing_private_key_hex=priv_hex,
        create_zip=False,
    )
    return {"manifest": manifest, "bundle_dir": bundle_dir}


@router.post("/verify", response_model=V3VerifyResponse)
async def verify_package_endpoint(req: V3VerifyRequest):
    """Run independent verifier on an uploaded v3 package."""
    result = StandaloneV3ElectionVerifier.verify_package(req.package)
    return V3VerifyResponse(
        verified=result["verified"],
        election_id=result.get("election_id", ""),
        ballot_count=result.get("ballot_count", 0),
        checkpoints_passed=result["checkpoints_passed"],
        checkpoints_total=result["checkpoints_total"],
        checkpoints=result["checkpoints"],
    )
