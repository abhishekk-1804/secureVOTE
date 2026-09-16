"""
Ed25519 Cryptographic Signing Service for SecureVOTE.

Provides asymmetric signing of authoritative election artifacts:
1. Result Manifest (signed once election is CLOSED/PUBLISHED and verified)
2. Audit-Root / verification artifacts

Rules:
- Ed25519 asymmetric signatures.
- Canonical JSON serialization (sort_keys=True, separators=(',', ':')).
- Ephemeral test key injection support for zero-state CI.
- Real private keys must never be committed.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEntry, Election, ResultManifest
from app.services.audit_service import AuditService


class SigningService:
    """Service handling asymmetric signing and verification of election artifacts."""

    _active_private_key: Optional[ed25519.Ed25519PrivateKey] = None
    _active_public_key: Optional[ed25519.Ed25519PublicKey] = None
    _active_key_id: Optional[str] = None

    @classmethod
    def set_keypair(
        cls,
        private_key: ed25519.Ed25519PrivateKey,
        public_key: Optional[ed25519.Ed25519PublicKey] = None,
        key_id: str = "test-key-1",
    ) -> None:
        """Inject an active keypair (primarily for ephemeral test fixtures)."""
        cls._active_private_key = private_key
        cls._active_public_key = public_key or private_key.public_key()
        cls._active_key_id = key_id

    @classmethod
    def clear_keypair(cls) -> None:
        """Reset injected active keypair."""
        cls._active_private_key = None
        cls._active_public_key = None
        cls._active_key_id = None

    @classmethod
    def generate_keypair(cls) -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Generate a fresh Ed25519 keypair."""
        priv = ed25519.Ed25519PrivateKey.generate()
        return priv, priv.public_key()

    @classmethod
    def get_public_key_bytes(cls, public_key: ed25519.Ed25519PublicKey) -> bytes:
        """Extract raw bytes from an Ed25519 public key."""
        return public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @classmethod
    def get_public_key_hex(cls, public_key: ed25519.Ed25519PublicKey) -> str:
        """Extract raw hex string from an Ed25519 public key."""
        return cls.get_public_key_bytes(public_key).hex()

    @classmethod
    def get_public_key_fingerprint(cls, public_key: ed25519.Ed25519PublicKey) -> str:
        """Compute SHA-256 fingerprint of the raw public key bytes."""
        raw_bytes = cls.get_public_key_bytes(public_key)
        return hashlib.sha256(raw_bytes).hexdigest()

    @classmethod
    def get_configured_private_key(cls) -> Optional[ed25519.Ed25519PrivateKey]:
        """
        Retrieve the current private key.
        Checks in-memory ephemeral key first, then environment variable SECUREVOTE_SIGNING_KEY_HEX.
        """
        if cls._active_private_key is not None:
            return cls._active_private_key

        env_hex = os.environ.get("SECUREVOTE_SIGNING_KEY_HEX")
        if env_hex:
            try:
                raw_priv = bytes.fromhex(env_hex.strip())
                return ed25519.Ed25519PrivateKey.from_private_bytes(raw_priv)
            except Exception:
                return None
        return None

    @classmethod
    def get_configured_public_key(cls) -> Optional[ed25519.Ed25519PublicKey]:
        """Retrieve public key corresponding to the configured private key."""
        if cls._active_public_key is not None:
            return cls._active_public_key

        priv = cls.get_configured_private_key()
        if priv is not None:
            return priv.public_key()
        return None

    @classmethod
    def get_public_key_metadata(cls) -> dict[str, Any]:
        """Return public metadata for the active signing key (never private key material)."""
        pub = cls.get_configured_public_key()
        if pub is None:
            return {
                "configured": False,
                "algorithm": "Ed25519",
                "key_id": None,
                "public_key": None,
                "fingerprint": None,
            }

        raw_hex = cls.get_public_key_hex(pub)
        fingerprint = cls.get_public_key_fingerprint(pub)
        key_id = cls._active_key_id or f"ed25519-{fingerprint[:8]}"
        return {
            "configured": True,
            "algorithm": "Ed25519",
            "key_id": key_id,
            "public_key": raw_hex,
            "fingerprint": fingerprint,
        }

    @staticmethod
    def canonical_serialize(data: dict[str, Any]) -> bytes:
        """
        Canonical JSON serialization for cryptographic signatures.
        Enforces sort_keys=True, compact separators (',', ':'), UTF-8.
        """
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def create_manifest_payload(
        cls,
        election_id: str,
        manifest_hash: str,
        configuration_hash: str,
        audit_root_hash: str,
        total_ballots: int,
        reconciliation_status: str,
        audit_chain_status: str,
    ) -> dict[str, Any]:
        """Construct the minimal canonical signed payload for a result manifest."""
        return {
            "artifact_type": "RESULT_MANIFEST",
            "artifact_version": "1.0.0",
            "election_id": election_id,
            "manifest_hash": manifest_hash,
            "configuration_hash": configuration_hash,
            "audit_root_hash": audit_root_hash,
            "total_ballots": total_ballots,
            "reconciliation_status": reconciliation_status,
            "audit_chain_status": audit_chain_status,
        }

    @classmethod
    def create_audit_root_payload(
        cls,
        election_id: str,
        audit_root_hash: str,
        entry_count: int,
    ) -> dict[str, Any]:
        """Construct the minimal canonical signed payload for an audit root verification."""
        return {
            "artifact_type": "AUDIT_ROOT_VERIFICATION",
            "artifact_version": "1.0.0",
            "election_id": election_id,
            "audit_root_hash": audit_root_hash,
            "entry_count": entry_count,
        }

    @classmethod
    def sign_payload(
        cls,
        payload: dict[str, Any],
        private_key: Optional[ed25519.Ed25519PrivateKey] = None,
    ) -> dict[str, Any]:
        """
        Sign a canonical payload with Ed25519.
        Returns a dict containing signature, public key, fingerprint, and canonical signed payload.
        """
        key = private_key or cls.get_configured_private_key()
        if key is None:
            raise HTTPException(
                status_code=503,
                detail="Signing key is not configured. Please provision a signing key.",
            )

        pub = key.public_key()
        canonical_bytes = cls.canonical_serialize(payload)
        signature = key.sign(canonical_bytes)

        pub_hex = cls.get_public_key_hex(pub)
        fingerprint = cls.get_public_key_fingerprint(pub)
        key_id = cls._active_key_id or f"ed25519-{fingerprint[:8]}"

        return {
            "algorithm": "Ed25519",
            "key_id": key_id,
            "public_key": pub_hex,
            "fingerprint": fingerprint,
            "signature": signature.hex(),
            "signed_payload": payload,
        }

    @classmethod
    def verify_signature(
        cls,
        payload: dict[str, Any] | bytes | str,
        signature_hex: str,
        public_key_hex: str,
    ) -> bool:
        """
        Verify an Ed25519 signature against canonical payload and raw public key hex.
        Returns True if valid, False otherwise. Never throws.
        """
        try:
            pub_bytes = bytes.fromhex(public_key_hex)
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)

            if isinstance(payload, dict):
                data_bytes = cls.canonical_serialize(payload)
            elif isinstance(payload, str):
                data_bytes = payload.encode("utf-8")
            else:
                data_bytes = payload

            sig_bytes = bytes.fromhex(signature_hex)
            pub_key.verify(sig_bytes, data_bytes)
            return True
        except (InvalidSignature, ValueError, TypeError, Exception):
            return False

    @classmethod
    async def sign_manifest(
        cls,
        db: AsyncSession,
        election_id: str,
        actor: str,
    ) -> ResultManifest:
        """
        Sign the result manifest of an election.

        Lifecycle constraints:
        - Election must be CLOSED or PUBLISHED.
        - Manifest must exist.
        - Reconciliation must be EXACT_MATCH.
        """
        election = await db.get(Election, election_id)
        if not election:
            raise HTTPException(status_code=404, detail="Election not found")

        # Lifecycle constraint: only CLOSED or PUBLISHED elections can be signed
        if election.state not in ("CLOSED", "PUBLISHED"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot sign manifest for election in '{election.state}' state. Must be CLOSED or PUBLISHED.",
            )

        manifest_result = await db.execute(
            select(ResultManifest).where(ResultManifest.election_id == election_id)
        )
        manifest = manifest_result.scalar_one_or_none()
        if not manifest:
            raise HTTPException(
                status_code=404,
                detail="Result manifest does not exist. Run verification first.",
            )

        if manifest.reconciliation_status not in ("PASSED", "EXACT_MATCH"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot sign manifest with reconciliation status '{manifest.reconciliation_status}'. Must be PASSED or EXACT_MATCH.",
            )

        # Get latest audit entry hash as audit_root_hash
        latest_audit = await db.execute(
            select(AuditEntry)
            .where(AuditEntry.election_id == election_id)
            .order_by(AuditEntry.sequence_number.desc())
            .limit(1)
        )
        audit_entry = latest_audit.scalar_one_or_none()
        audit_root_hash = audit_entry.entry_hash if audit_entry else "GENESIS"

        # Build canonical payload
        payload = cls.create_manifest_payload(
            election_id=election_id,
            manifest_hash=manifest.manifest_hash,
            configuration_hash=manifest.configuration_hash,
            audit_root_hash=audit_root_hash,
            total_ballots=manifest.total_ballots,
            reconciliation_status=manifest.reconciliation_status,
            audit_chain_status=manifest.audit_chain_status,
        )

        signed_artifact = cls.sign_payload(payload)

        # Store signature object as serialized JSON in manifest.digital_signature
        manifest.digital_signature = json.dumps(signed_artifact, sort_keys=True)
        manifest.verified_at = datetime.now(timezone.utc)
        manifest.verified_by = actor

        await db.flush()

        await AuditService.log_event(
            db=db,
            election_id=election_id,
            event_type="MANIFEST_SIGNED",
            event_data={
                "manifest_hash": manifest.manifest_hash,
                "key_id": signed_artifact["key_id"],
                "fingerprint": signed_artifact["fingerprint"],
                "algorithm": signed_artifact["algorithm"],
            },
            actor=actor,
        )

        return manifest
