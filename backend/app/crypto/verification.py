"""
SecureVOTE 3.0 — Independent Cryptographic Verification.

Verifies v3 encrypted ballot artifacts, commitments, tallies,
and reconciliation independently — without trusting the backend,
database, or any application state.

This module has ZERO imports from:
- FastAPI
- SQLAlchemy
- app.models
- app.database

It operates purely on exported JSON artifacts.
"""

import hashlib
import json
from typing import Any

from app.crypto import PROTOCOL_VERSION
from app.crypto.canonical import (
    ballot_domain,
    canonical_hash,
    canonical_json,
    commitment_domain,
    tally_domain,
)
from app.crypto.commitment import compute_ballot_commitment, compute_tally_commitment
from app.crypto.elgamal import (
    ECPoint,
    ElGamalCiphertext,
    ElGamalPrivateKey,
    ElGamalPublicKey,
    aggregate,
    decrypt,
    point_on_curve,
)
from app.crypto.exceptions import (
    CommitmentError,
    InvalidCiphertextError,
    SerializationError,
    VerificationError,
)
from app.crypto.keys import compute_key_fingerprint, deserialize_public_key
from app.crypto.serialization import deserialize_ciphertext


class V3Verifier:
    """
    Independent verifier for SecureVOTE 3.0 encrypted election artifacts.

    Each checkpoint returns a result dict with:
    - checkpoint: checkpoint name
    - status: "PASSED" or "FAILED"
    - details: human-readable explanation
    """

    @staticmethod
    def verify_protocol_version(artifact: dict[str, Any]) -> dict[str, str]:
        """Checkpoint 1: Verify protocol version."""
        version = artifact.get("protocol_version")
        if version != PROTOCOL_VERSION:
            return {
                "checkpoint": "protocol_version",
                "status": "FAILED",
                "details": f"Expected {PROTOCOL_VERSION}, got {version}",
            }
        return {
            "checkpoint": "protocol_version",
            "status": "PASSED",
            "details": f"Protocol version {PROTOCOL_VERSION} confirmed",
        }

    @staticmethod
    def verify_ballot_structure(artifact: dict[str, Any]) -> dict[str, str]:
        """Checkpoint 2: Verify encrypted ballot has required fields."""
        required = [
            "protocol_version", "artifact_type", "election_id", "artifact_id",
            "encrypted_vote", "commitment", "key_fingerprint", "artifact_hash",
        ]
        missing = [f for f in required if f not in artifact]
        if missing:
            return {
                "checkpoint": "ballot_structure",
                "status": "FAILED",
                "details": f"Missing required fields: {missing}",
            }
        if artifact.get("artifact_type") != "ENCRYPTED_BALLOT":
            return {
                "checkpoint": "ballot_structure",
                "status": "FAILED",
                "details": f"Expected artifact_type ENCRYPTED_BALLOT, got {artifact.get('artifact_type')}",
            }
        return {
            "checkpoint": "ballot_structure",
            "status": "PASSED",
            "details": "All required ballot fields present",
        }

    @staticmethod
    def verify_ciphertext_integrity(artifact: dict[str, Any]) -> dict[str, str]:
        """Checkpoint 3: Verify all ciphertext points lie on the curve."""
        try:
            encrypted_vote = artifact["encrypted_vote"]
            for i, slot in enumerate(encrypted_vote["slots"]):
                ct = deserialize_ciphertext(slot)
                if not point_on_curve(ct.c1):
                    return {
                        "checkpoint": "ciphertext_integrity",
                        "status": "FAILED",
                        "details": f"Slot {i}: C1 is not on secp256r1",
                    }
                if not point_on_curve(ct.c2):
                    return {
                        "checkpoint": "ciphertext_integrity",
                        "status": "FAILED",
                        "details": f"Slot {i}: C2 is not on secp256r1",
                    }
        except (KeyError, SerializationError, InvalidCiphertextError) as e:
            return {
                "checkpoint": "ciphertext_integrity",
                "status": "FAILED",
                "details": f"Ciphertext deserialization error: {e}",
            }
        return {
            "checkpoint": "ciphertext_integrity",
            "status": "PASSED",
            "details": f"All {len(encrypted_vote['slots'])} ciphertext slots verified on curve",
        }

    @staticmethod
    def verify_ballot_commitment(artifact: dict[str, Any]) -> dict[str, str]:
        """Checkpoint 4: Independently recompute and verify ballot commitment."""
        try:
            recomputed = compute_ballot_commitment(
                election_id=artifact["election_id"],
                artifact_id=artifact["artifact_id"],
                encrypted_vote=artifact["encrypted_vote"],
                candidate_count=artifact["encrypted_vote"]["candidate_count"],
                key_fingerprint=artifact["key_fingerprint"],
            )
            if recomputed != artifact["commitment"]:
                return {
                    "checkpoint": "ballot_commitment",
                    "status": "FAILED",
                    "details": f"Commitment mismatch: recomputed {recomputed[:16]}..., "
                               f"stored {artifact['commitment'][:16]}...",
                }
        except Exception as e:
            return {
                "checkpoint": "ballot_commitment",
                "status": "FAILED",
                "details": f"Commitment computation error: {e}",
            }
        return {
            "checkpoint": "ballot_commitment",
            "status": "PASSED",
            "details": "Ballot commitment independently verified",
        }

    @staticmethod
    def verify_ballot_artifact_hash(artifact: dict[str, Any]) -> dict[str, str]:
        """Checkpoint 5: Independently recompute artifact hash."""
        artifact_data = {
            "protocol_version": artifact["protocol_version"],
            "election_id": artifact["election_id"],
            "artifact_id": artifact["artifact_id"],
            "encrypted_vote": artifact["encrypted_vote"],
            "commitment": artifact["commitment"],
            "key_fingerprint": artifact["key_fingerprint"],
        }
        recomputed = canonical_hash(artifact_data, domain=ballot_domain(artifact["election_id"]))
        if recomputed != artifact["artifact_hash"]:
            return {
                "checkpoint": "ballot_artifact_hash",
                "status": "FAILED",
                "details": f"Artifact hash mismatch: recomputed {recomputed[:16]}..., "
                           f"stored {artifact['artifact_hash'][:16]}...",
            }
        return {
            "checkpoint": "ballot_artifact_hash",
            "status": "PASSED",
            "details": "Artifact hash independently verified",
        }

    @staticmethod
    def verify_key_metadata(
        artifact: dict[str, Any],
        public_key_data: dict[str, Any],
    ) -> dict[str, str]:
        """Checkpoint 6: Verify key fingerprint matches public key."""
        try:
            pub = deserialize_public_key(public_key_data)
            fp = compute_key_fingerprint(pub)
            if fp != artifact["key_fingerprint"]:
                return {
                    "checkpoint": "key_metadata",
                    "status": "FAILED",
                    "details": f"Key fingerprint mismatch: computed {fp[:16]}..., "
                               f"artifact has {artifact['key_fingerprint'][:16]}...",
                }
        except Exception as e:
            return {
                "checkpoint": "key_metadata",
                "status": "FAILED",
                "details": f"Key verification error: {e}",
            }
        return {
            "checkpoint": "key_metadata",
            "status": "PASSED",
            "details": "Key fingerprint matches provided public key",
        }

    @staticmethod
    def verify_tally_structure(tally: dict[str, Any]) -> dict[str, str]:
        """Checkpoint 7: Verify tally artifact structure."""
        required = [
            "protocol_version", "artifact_type", "election_id",
            "encrypted_tally", "ballot_count", "key_fingerprint",
            "commitment", "artifact_hash",
        ]
        missing = [f for f in required if f not in tally]
        if missing:
            return {
                "checkpoint": "tally_structure",
                "status": "FAILED",
                "details": f"Missing required fields: {missing}",
            }
        if tally.get("artifact_type") != "ENCRYPTED_TALLY":
            return {
                "checkpoint": "tally_structure",
                "status": "FAILED",
                "details": f"Expected artifact_type ENCRYPTED_TALLY, got {tally.get('artifact_type')}",
            }
        return {
            "checkpoint": "tally_structure",
            "status": "PASSED",
            "details": "All required tally fields present",
        }

    @staticmethod
    def verify_tally_commitment(tally: dict[str, Any]) -> dict[str, str]:
        """Checkpoint 8: Independently recompute tally commitment."""
        try:
            recomputed = compute_tally_commitment(
                election_id=tally["election_id"],
                encrypted_tally=tally["encrypted_tally"],
                ballot_count=tally["ballot_count"],
                key_fingerprint=tally["key_fingerprint"],
            )
            if recomputed != tally["commitment"]:
                return {
                    "checkpoint": "tally_commitment",
                    "status": "FAILED",
                    "details": f"Tally commitment mismatch",
                }
        except Exception as e:
            return {
                "checkpoint": "tally_commitment",
                "status": "FAILED",
                "details": f"Tally commitment error: {e}",
            }
        return {
            "checkpoint": "tally_commitment",
            "status": "PASSED",
            "details": "Tally commitment independently verified",
        }

    @staticmethod
    def verify_tally_reconciliation(decrypted_tally: dict[str, Any]) -> dict[str, str]:
        """Checkpoint 9: Verify tally reconciliation (sum = ballot_count)."""
        tallies = decrypted_tally.get("candidate_tallies", {})
        total = sum(tallies.values())
        expected = decrypted_tally.get("ballot_count", 0)
        if total != expected:
            return {
                "checkpoint": "tally_reconciliation",
                "status": "FAILED",
                "details": f"Tally sum ({total}) != ballot count ({expected}), drift = {total - expected}",
            }
        return {
            "checkpoint": "tally_reconciliation",
            "status": "PASSED",
            "details": f"Tally balanced: {total} votes across {len(tallies)} candidates",
        }

    @classmethod
    def verify_full_ballot(
        cls,
        artifact: dict[str, Any],
        public_key_data: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Run all ballot verification checkpoints."""
        return [
            cls.verify_protocol_version(artifact),
            cls.verify_ballot_structure(artifact),
            cls.verify_ciphertext_integrity(artifact),
            cls.verify_ballot_commitment(artifact),
            cls.verify_ballot_artifact_hash(artifact),
            cls.verify_key_metadata(artifact, public_key_data),
        ]

    @classmethod
    def verify_full_tally(
        cls,
        tally_artifact: dict[str, Any],
        decrypted_tally: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Run all tally verification checkpoints."""
        return [
            cls.verify_protocol_version(tally_artifact),
            cls.verify_tally_structure(tally_artifact),
            cls.verify_tally_commitment(tally_artifact),
            cls.verify_tally_reconciliation(decrypted_tally),
        ]
