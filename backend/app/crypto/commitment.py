"""
SecureVOTE 3.0 — Ballot Commitments.

Implements domain-separated, versioned ballot commitments using SHA-256.

A commitment binds an encrypted ballot artifact to its contents without
revealing the plaintext vote. It enables a verifier to detect any
post-commitment modification.

Commitment = SHA-256(domain_prefix || canonical_json(artifact_data))

Domain separation ensures commitments from different elections, different
artifact types, and different protocol versions cannot collide.
"""

import hashlib
from typing import Any

from app.crypto import PROTOCOL_VERSION
from app.crypto.canonical import canonical_hash, canonical_json, commitment_domain
from app.crypto.exceptions import CommitmentError


def compute_ballot_commitment(
    election_id: str,
    artifact_id: str,
    encrypted_vote: dict[str, Any],
    candidate_count: int,
    key_fingerprint: str,
) -> str:
    """
    Compute a commitment over an encrypted ballot artifact.

    Inputs bound by the commitment:
    - election_id
    - artifact_id
    - encrypted_vote (serialized ciphertexts)
    - candidate_count (number of slots)
    - key_fingerprint (public key used for encryption)

    Returns hex-encoded SHA-256 commitment.
    """
    commitment_data = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "artifact_id": artifact_id,
        "encrypted_vote": encrypted_vote,
        "candidate_count": candidate_count,
        "key_fingerprint": key_fingerprint,
    }
    domain = commitment_domain(election_id)
    return canonical_hash(commitment_data, domain=domain)


def verify_ballot_commitment(
    expected_commitment: str,
    election_id: str,
    artifact_id: str,
    encrypted_vote: dict[str, Any],
    candidate_count: int,
    key_fingerprint: str,
) -> bool:
    """
    Verify that a ballot commitment matches the provided artifact data.

    Returns True if the commitment matches, raises CommitmentError otherwise.
    """
    recomputed = compute_ballot_commitment(
        election_id=election_id,
        artifact_id=artifact_id,
        encrypted_vote=encrypted_vote,
        candidate_count=candidate_count,
        key_fingerprint=key_fingerprint,
    )
    if recomputed != expected_commitment:
        raise CommitmentError(
            f"Commitment mismatch: expected {expected_commitment}, "
            f"recomputed {recomputed}"
        )
    return True


def compute_tally_commitment(
    election_id: str,
    encrypted_tally: dict[str, Any],
    ballot_count: int,
    key_fingerprint: str,
) -> str:
    """
    Compute a commitment over an encrypted tally result.
    """
    from app.crypto.canonical import tally_domain

    commitment_data = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "encrypted_tally": encrypted_tally,
        "ballot_count": ballot_count,
        "key_fingerprint": key_fingerprint,
    }
    domain = tally_domain(election_id)
    return canonical_hash(commitment_data, domain=domain)
