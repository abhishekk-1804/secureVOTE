"""
Service layer for SecureVOTE 3.0 Cryptographic Operations.
"""

import json
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encrypt_ballot
from app.crypto.elgamal import (
    ElGamalPrivateKey,
    ElGamalPublicKey,
    generate_keypair,
)
from app.crypto.keys import (
    compute_key_fingerprint,
    deserialize_public_key,
    serialize_public_key,
)
from app.models_v3 import (
    V3CryptoElection,
    V3EncryptedBallot,
    V3EncryptedTally,
)
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally
from standalone_verifier.v3_verifier import StandaloneV3ElectionVerifier


class CryptoV3Service:
    """
    Manages v3 elections, keys, encrypted ballots, and homomorphic tallies.
    """

    # In-memory store for research private keys (NEVER persisted to DB)
    _ephemeral_private_keys: dict[str, ElGamalPrivateKey] = {}

    @classmethod
    def register_private_key(cls, election_id: str, private_key: ElGamalPrivateKey):
        cls._ephemeral_private_keys[election_id] = private_key

    @classmethod
    def get_private_key(cls, election_id: str) -> Optional[ElGamalPrivateKey]:
        return cls._ephemeral_private_keys.get(election_id)

    @classmethod
    async def init_election(
        cls,
        db: AsyncSession,
        election_id: str,
        candidates: list[str],
    ) -> V3CryptoElection:
        """Initialize a new v3 cryptographic election."""
        # Check if already exists
        stmt = select(V3CryptoElection).where(V3CryptoElection.election_id == election_id)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"V3 Election {election_id} already initialized")

        keypair = generate_keypair()
        cls.register_private_key(election_id, keypair)

        pub_data = serialize_public_key(keypair.public_key)
        key_fp = compute_key_fingerprint(keypair.public_key)

        crypto_el = V3CryptoElection(
            election_id=election_id,
            protocol_version=PROTOCOL_VERSION,
            public_key_json=json.dumps(pub_data),
            key_fingerprint=key_fp,
            key_id=f"KEY-{election_id}",
            candidate_count=len(candidates),
            candidate_ids_json=json.dumps(candidates),
            status="ACTIVE",
        )
        db.add(crypto_el)
        await db.commit()
        await db.refresh(crypto_el)
        return crypto_el

    @classmethod
    async def get_election(cls, db: AsyncSession, election_id: str) -> V3CryptoElection:
        stmt = select(V3CryptoElection).where(V3CryptoElection.election_id == election_id)
        res = await db.execute(stmt)
        crypto_el = res.scalar_one_or_none()
        if not crypto_el:
            raise HTTPException(status_code=404, detail=f"V3 Election {election_id} not found")
        return crypto_el

    @classmethod
    async def encrypt_ballot_for_voter(
        cls,
        db: AsyncSession,
        election_id: str,
        candidate_index: int,
    ) -> dict[str, Any]:
        """Encrypt a voter choice using the election's public key."""
        crypto_el = await cls.get_election(db, election_id)
        pub_data = json.loads(crypto_el.public_key_json)
        public_key = deserialize_public_key(pub_data)
        candidates = json.loads(crypto_el.candidate_ids_json)

        if not (0 <= candidate_index < len(candidates)):
            raise HTTPException(status_code=400, detail=f"Invalid candidate index {candidate_index}")

        artifact = encrypt_ballot(
            public_key=public_key,
            candidate_index=candidate_index,
            candidate_count=len(candidates),
            election_id=election_id,
            candidate_ids=candidates,
        )
        return artifact

    @classmethod
    async def cast_ballot(
        cls,
        db: AsyncSession,
        election_id: str,
        artifact: dict[str, Any],
    ) -> V3EncryptedBallot:
        """Validate and record an encrypted ballot artifact."""
        crypto_el = await cls.get_election(db, election_id)
        if crypto_el.status != "ACTIVE":
            raise HTTPException(status_code=400, detail=f"Election {election_id} is not ACTIVE (status: {crypto_el.status})")

        # Verify commitment and public key fingerprint
        pub_data = json.loads(crypto_el.public_key_json)
        if artifact.get("key_fingerprint") != crypto_el.key_fingerprint:
            raise HTTPException(status_code=400, detail="Ballot key fingerprint does not match election key")

        from standalone_verifier.v3_verifier import StandaloneV3ElectionVerifier
        single_pkg = {
            "protocol_version": PROTOCOL_VERSION,
            "election_id": election_id,
            "public_key": pub_data,
            "candidates": json.loads(crypto_el.candidate_ids_json),
            "ballots": [artifact],
            "encrypted_tally": None,
        }
        # Run verifier checkpoints 1-7
        chk_res = StandaloneV3ElectionVerifier.verify_package(single_pkg)
        failed = [c for c in chk_res["checkpoints"][:7] if c["status"] == "FAILED"]
        if failed:
            raise HTTPException(status_code=400, detail=f"Cryptographic ballot verification failed: {failed[0]['message']}")

        # Ensure artifact_id uniqueness
        stmt = select(V3EncryptedBallot).where(V3EncryptedBallot.artifact_id == artifact["artifact_id"])
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Ballot {artifact['artifact_id']} already recorded")

        b_record = V3EncryptedBallot(
            crypto_election_id=crypto_el.id,
            artifact_id=artifact["artifact_id"],
            artifact_json=json.dumps(artifact),
            commitment=artifact["commitment"],
            artifact_hash=artifact["artifact_hash"],
        )
        db.add(b_record)
        await db.commit()
        await db.refresh(b_record)
        return b_record

    @classmethod
    async def get_ballots(cls, db: AsyncSession, election_id: str) -> list[dict[str, Any]]:
        crypto_el = await cls.get_election(db, election_id)
        stmt = select(V3EncryptedBallot).where(V3EncryptedBallot.crypto_election_id == crypto_el.id)
        res = await db.execute(stmt)
        records = res.scalars().all()
        return [json.loads(r.artifact_json) for r in records]

    @classmethod
    async def aggregate_tally(cls, db: AsyncSession, election_id: str) -> V3EncryptedTally:
        """Homomorphically aggregate all cast encrypted ballots."""
        crypto_el = await cls.get_election(db, election_id)
        ballots = await cls.get_ballots(db, election_id)
        if not ballots:
            raise HTTPException(status_code=400, detail="Cannot aggregate tally: no ballots cast")

        tally_artifact = aggregate_encrypted_ballots(
            ballot_artifacts=ballots,
            election_id=election_id,
            expected_key_fingerprint=crypto_el.key_fingerprint,
        )

        # Check if tally record already exists
        stmt = select(V3EncryptedTally).where(V3EncryptedTally.crypto_election_id == crypto_el.id)
        t_record = (await db.execute(stmt)).scalar_one_or_none()
        if not t_record:
            t_record = V3EncryptedTally(
                crypto_election_id=crypto_el.id,
                encrypted_tally_json=json.dumps(tally_artifact),
                ballot_count=len(ballots),
                commitment=tally_artifact["commitment"],
                artifact_hash=tally_artifact["artifact_hash"],
                status="ENCRYPTED",
            )
            db.add(t_record)
        else:
            t_record.encrypted_tally_json = json.dumps(tally_artifact)
            t_record.ballot_count = len(ballots)
            t_record.commitment = tally_artifact["commitment"]
            t_record.artifact_hash = tally_artifact["artifact_hash"]
            t_record.status = "ENCRYPTED"
            t_record.decrypted_tally_json = None

        await db.commit()
        await db.refresh(t_record)
        return t_record

    @classmethod
    async def decrypt_tally(
        cls,
        db: AsyncSession,
        election_id: str,
        override_private_key: Optional[ElGamalPrivateKey] = None,
    ) -> dict[str, Any]:
        """Decrypt the homomorphic aggregate tally."""
        crypto_el = await cls.get_election(db, election_id)
        stmt = select(V3EncryptedTally).where(V3EncryptedTally.crypto_election_id == crypto_el.id)
        t_record = (await db.execute(stmt)).scalar_one_or_none()
        if not t_record:
            raise HTTPException(status_code=400, detail="No aggregate tally found. Run aggregation first.")

        priv = override_private_key or cls.get_private_key(election_id)
        if not priv:
            raise HTTPException(status_code=400, detail="Election private key not available for decryption")

        tally_artifact = json.loads(t_record.encrypted_tally_json)
        decrypted = decrypt_tally(priv, tally_artifact, max_ballots=t_record.ballot_count + 1000)

        t_record.decrypted_tally_json = json.dumps(decrypted)
        t_record.status = "DECRYPTED"
        from datetime import datetime, timezone
        t_record.decrypted_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(t_record)

        return decrypted

    @classmethod
    async def export_package(cls, db: AsyncSession, election_id: str) -> dict[str, Any]:
        """Export a complete v3 package for standalone verification."""
        crypto_el = await cls.get_election(db, election_id)
        ballots = await cls.get_ballots(db, election_id)

        stmt = select(V3EncryptedTally).where(V3EncryptedTally.crypto_election_id == crypto_el.id)
        t_record = (await db.execute(stmt)).scalar_one_or_none()

        pkg = {
            "protocol_version": PROTOCOL_VERSION,
            "election_id": election_id,
            "public_key": json.loads(crypto_el.public_key_json),
            "candidates": json.loads(crypto_el.candidate_ids_json),
            "ballots": ballots,
            "encrypted_tally": json.loads(t_record.encrypted_tally_json) if t_record else None,
            "decrypted_tally": json.loads(t_record.decrypted_tally_json) if (t_record and t_record.decrypted_tally_json) else None,
        }
        return pkg
