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
from app.crypto.elgamal import ElGamalCiphertext, ElGamalPublicKey, encrypt
from app.crypto.exceptions import EncryptionError
from app.crypto.keys import compute_key_fingerprint
from app.crypto.serialization import serialize_ciphertext


def encode_vote_onehot(candidate_index: int, candidate_count: int) -> list[int]:
    """
    Encode a vote as a one-hot vector.

    Args:
        candidate_index: 0-based index of the selected candidate.
        candidate_count: Total number of candidates.

    Returns:
        A list of integers: [0, ..., 1, ..., 0] with 1 at the selected index.

    Raises:
        EncryptionError: If candidate_index is out of range.
    """
    if not (0 <= candidate_index < candidate_count):
        raise EncryptionError(
            f"Candidate index {candidate_index} out of range [0, {candidate_count})"
        )
    onehot = [0] * candidate_count
    onehot[candidate_index] = 1
    return onehot


def encrypt_ballot(
    public_key: ElGamalPublicKey,
    candidate_index: int,
    candidate_count: int,
    election_id: str,
    candidate_ids: list[str],
) -> dict[str, Any]:
    """
    Create a complete encrypted ballot artifact.

    Args:
        public_key: The election's ElGamal public key.
        candidate_index: 0-based index of the selected candidate.
        candidate_count: Total number of candidates.
        election_id: The election identifier.
        candidate_ids: Ordered list of candidate IDs.

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

    for value in onehot:
        ct = encrypt(public_key, value)
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

    # Compute artifact hash
    artifact_data = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "artifact_id": artifact_id,
        "encrypted_vote": encrypted_vote,
        "commitment": commitment,
        "key_fingerprint": key_fp,
    }
    artifact_hash = canonical_hash(artifact_data, domain=ballot_domain(election_id))

    # Build final artifact
    artifact = {
        "protocol_version": PROTOCOL_VERSION,
        "artifact_type": "ENCRYPTED_BALLOT",
        "election_id": election_id,
        "artifact_id": artifact_id,
        "encrypted_vote": encrypted_vote,
        "commitment": commitment,
        "key_fingerprint": key_fp,
        "artifact_hash": artifact_hash,
    }

    return artifact
