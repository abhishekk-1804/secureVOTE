"""
SecureVOTE 3.0 — Encrypted Ballot Artifact.

Creates privacy-preserving ballot artifacts using one-hot encoding
and Exponential ElGamal encryption.

Vote Encoding (One-Hot):
    Candidate A selected: [1, 0, 0, 0]
    Candidate B selected: [0, 1, 0, 0]
    Candidate C selected: [0, 0, 1, 0]
    NOTA selected:        [0, 0, 0, 1]

Each slot is independently encrypted:
    Enc([1,0,0,0]) = [Enc(1), Enc(0), Enc(0), Enc(0)]

Homomorphic aggregation sums corresponding slots:
    Enc([1,0,0,0]) ⊕ Enc([0,1,0,0]) ⊕ Enc([0,0,1,0])
    = Enc([1,1,1,0])

The artifact is detached from voter identity — it contains only:
- election_id
- artifact_id (random UUID)
- encrypted_vote (ciphertext vector)
- commitment
- protocol metadata
"""

import uuid
from typing import Any

from app.crypto import PROTOCOL_VERSION
from app.crypto.canonical import ballot_domain, canonical_hash
from app.crypto.commitment import compute_ballot_commitment
from app.crypto.elgamal import (
    ElGamalCiphertext,
    ElGamalPublicKey,
    encrypt,
    encrypt_with_nonce,
)
from app.crypto.exceptions import EncryptionError
from app.crypto.keys import compute_key_fingerprint
from app.crypto.serialization import serialize_ciphertext


def encode_vote_onehot(candidate_index: int, candidate_count: int) -> list[int]:
    """
    Encode a candidate choice as a one-hot vector.

    Args:
        candidate_index: 0-based index of the chosen candidate.
        candidate_count: Total number of candidates.

    Returns:
        A list of ints of length candidate_count, with exactly one 1 and all other 0s.

    Raises:
        EncryptionError: If candidate_index is out of range.
    """
    if not (0 <= candidate_index < candidate_count):
        raise EncryptionError(
            f"Candidate index {candidate_index} out of range [0, {candidate_count})"
        )
    return [1 if i == candidate_index else 0 for i in range(candidate_count)]


def encrypt_ballot(
    public_key: ElGamalPublicKey,
    candidate_index: int,
    candidate_count: int,
    election_id: str,
    candidate_ids: list[str],
    with_zkp: bool = False,
) -> dict[str, Any]:
    """
    Create a complete encrypted ballot artifact.

    Args:
        public_key: The election's ElGamal public key.
        candidate_index: 0-based index of the selected candidate.
        candidate_count: Total number of candidates.
        election_id: The election identifier.
        candidate_ids: Ordered list of candidate IDs.
        with_zkp: If True, attaches a zero-knowledge ballot validity proof (CDS94 + Chaum-Pedersen).

    Returns:
        A complete encrypted ballot artifact dictionary.
    """
    if len(candidate_ids) != candidate_count:
        raise EncryptionError(
            f"candidate_ids length ({len(candidate_ids)}) does not match "
            f"candidate_count ({candidate_count})"
        )

    # Encode as one-hot vector
    onehot = encode_vote_onehot(candidate_index, candidate_count)

    # Encrypt each slot independently
    encrypted_slots: list[ElGamalCiphertext] = []
    serialized_slots: list[dict[str, Any]] = []
    nonces: list[int] = []

    for value in onehot:
        ct, r = encrypt_with_nonce(public_key, value)
        nonces.append(r)
        encrypted_slots.append(ct)
        serialized_slots.append(serialize_ciphertext(ct))

    # Build encrypted vote structure
    encrypted_vote = {
        "slots": serialized_slots,
        "candidate_ids": candidate_ids,
        "candidate_count": candidate_count,
    }

    # Compute key fingerprint
    key_fp = compute_key_fingerprint(public_key)

    # Generate artifact ID
    artifact_id = str(uuid.uuid4())

    # Compute commitment
    commitment = compute_ballot_commitment(
        election_id=election_id,
        artifact_id=artifact_id,
        encrypted_vote=encrypted_vote,
        candidate_count=candidate_count,
        key_fingerprint=key_fp,
    )

    # Optional ZK ballot validity proof
    proof = None
    if with_zkp:
        from app.crypto.zk import prove_ballot_validity
        proof = prove_ballot_validity(
            public_key=public_key,
            candidate_index=candidate_index,
            nonces=nonces,
            candidate_count=candidate_count,
            election_id=election_id,
            candidate_ids=candidate_ids,
        )

    # Compute artifact hash
    artifact_data: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "artifact_id": artifact_id,
        "encrypted_vote": encrypted_vote,
        "commitment": commitment,
        "key_fingerprint": key_fp,
    }
    if proof is not None:
        artifact_data["proof"] = proof

    artifact_hash = canonical_hash(artifact_data, domain=ballot_domain(election_id))

    # Build final artifact
    artifact: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "artifact_type": "ENCRYPTED_BALLOT",
        "election_id": election_id,
        "artifact_id": artifact_id,
        "encrypted_vote": encrypted_vote,
        "commitment": commitment,
        "key_fingerprint": key_fp,
        "artifact_hash": artifact_hash,
    }
    if proof is not None:
        artifact["proof"] = proof

    return artifact


def encrypt_ballot_with_zkp(
    public_key: ElGamalPublicKey,
    candidate_index: int,
    candidate_count: int,
    election_id: str,
    candidate_ids: list[str],
) -> dict[str, Any]:
    """Convenience helper to create an encrypted ballot with a zero-knowledge validity proof."""
    return encrypt_ballot(
        public_key=public_key,
        candidate_index=candidate_index,
        candidate_count=candidate_count,
        election_id=election_id,
        candidate_ids=candidate_ids,
        with_zkp=True,
    )
