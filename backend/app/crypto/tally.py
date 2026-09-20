"""
SecureVOTE 3.0 — Homomorphic Tally.

Aggregates encrypted ballot artifacts using the additive homomorphic
property of Exponential ElGamal, then decrypts the aggregate to
recover plaintext tallies.

Workflow:
    1. Collect all encrypted ballot artifacts for an election.
    2. Aggregate corresponding ciphertext slots across all ballots.
    3. Decrypt each aggregated slot to recover the tally per candidate.
    4. Verify that the sum of tallies equals the number of ballots.
"""

from typing import Any

from app.crypto import PROTOCOL_VERSION
from app.crypto.canonical import canonical_hash, tally_domain
from app.crypto.commitment import compute_tally_commitment
from app.crypto.elgamal import (
    ElGamalCiphertext,
    ElGamalPrivateKey,
    add_ciphertexts,
    aggregate,
    decrypt,
)
from app.crypto.exceptions import (
    AggregationError,
    DecryptionError,
    VerificationError,
)
from app.crypto.keys import compute_key_fingerprint
from app.crypto.serialization import (
    deserialize_ciphertext,
    serialize_ciphertext,
)


def aggregate_encrypted_ballots(
    ballot_artifacts: list[dict[str, Any]],
    election_id: str,
    expected_key_fingerprint: str,
) -> dict[str, Any]:
    """
    Homomorphically aggregate all encrypted ballot artifacts.

    Each ballot has `candidate_count` ciphertext slots. Corresponding
    slots are added together across all ballots.

    Args:
        ballot_artifacts: List of encrypted ballot artifact dictionaries.
        election_id: The election identifier.
        expected_key_fingerprint: Expected public key fingerprint.

    Returns:
        Encrypted tally artifact dictionary.
    """
    if not ballot_artifacts:
        raise AggregationError("Cannot aggregate zero ballot artifacts")

    # Validate all ballots are for the same election and key
    candidate_count = ballot_artifacts[0]["encrypted_vote"]["candidate_count"]
    candidate_ids = ballot_artifacts[0]["encrypted_vote"]["candidate_ids"]

    for i, artifact in enumerate(ballot_artifacts):
        if artifact["election_id"] != election_id:
            raise AggregationError(
                f"Ballot {i} has election_id={artifact['election_id']}, "
                f"expected {election_id}"
            )
        if artifact["key_fingerprint"] != expected_key_fingerprint:
            raise AggregationError(
                f"Ballot {i} has key_fingerprint={artifact['key_fingerprint']}, "
                f"expected {expected_key_fingerprint}"
            )
        if artifact["encrypted_vote"]["candidate_count"] != candidate_count:
            raise AggregationError(
                f"Ballot {i} has candidate_count={artifact['encrypted_vote']['candidate_count']}, "
                f"expected {candidate_count}"
            )
        if artifact["encrypted_vote"]["candidate_ids"] != candidate_ids:
            raise AggregationError(
                f"Ballot {i} has mismatched candidate_ids"
            )

    # Deserialize all ciphertext slots
    all_slots: list[list[ElGamalCiphertext]] = []
    for artifact in ballot_artifacts:
        slots = []
        for slot_data in artifact["encrypted_vote"]["slots"]:
            slots.append(deserialize_ciphertext(slot_data))
        all_slots.append(slots)

    # Aggregate corresponding slots
    aggregated_slots: list[ElGamalCiphertext] = []
    for slot_idx in range(candidate_count):
        slot_ciphertexts = [ballot_slots[slot_idx] for ballot_slots in all_slots]
        agg = aggregate(slot_ciphertexts)
        aggregated_slots.append(agg)

    # Serialize aggregated tally
    serialized_slots = [serialize_ciphertext(ct) for ct in aggregated_slots]

    encrypted_tally = {
        "slots": serialized_slots,
        "candidate_ids": candidate_ids,
        "candidate_count": candidate_count,
    }

    # Compute tally commitment
    commitment = compute_tally_commitment(
        election_id=election_id,
        encrypted_tally=encrypted_tally,
        ballot_count=len(ballot_artifacts),
        key_fingerprint=expected_key_fingerprint,
    )

    # Compute tally artifact hash
    tally_data = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "encrypted_tally": encrypted_tally,
        "ballot_count": len(ballot_artifacts),
        "key_fingerprint": expected_key_fingerprint,
        "commitment": commitment,
    }
    artifact_hash = canonical_hash(tally_data, domain=tally_domain(election_id))

    return {
        "protocol_version": PROTOCOL_VERSION,
        "artifact_type": "ENCRYPTED_TALLY",
        "election_id": election_id,
        "encrypted_tally": encrypted_tally,
        "ballot_count": len(ballot_artifacts),
        "key_fingerprint": expected_key_fingerprint,
        "commitment": commitment,
        "artifact_hash": artifact_hash,
    }


def decrypt_tally(
    private_key: ElGamalPrivateKey,
    tally_artifact: dict[str, Any],
    max_ballots: int = 10000,
) -> dict[str, Any]:
    """
    Decrypt the aggregated encrypted tally to recover plaintext vote counts.

    Args:
        private_key: The election's ElGamal private key.
        tally_artifact: The encrypted tally artifact dictionary.
        max_ballots: Maximum expected ballot count (for discrete log bound).

    Returns:
        Decrypted tally result dictionary.
    """
    encrypted_tally = tally_artifact["encrypted_tally"]
    candidate_ids = encrypted_tally["candidate_ids"]
    candidate_count = encrypted_tally["candidate_count"]
    ballot_count = tally_artifact["ballot_count"]

    # Verify key fingerprint matches
    expected_fp = tally_artifact["key_fingerprint"]
    actual_fp = compute_key_fingerprint(private_key.public_key)
    if actual_fp != expected_fp:
        raise DecryptionError(
            f"Key fingerprint mismatch: tally expects {expected_fp}, "
            f"provided key has {actual_fp}"
        )

    # Decrypt each slot
    tallies: dict[str, int] = {}
    total = 0

    for slot_idx in range(candidate_count):
        ct = deserialize_ciphertext(encrypted_tally["slots"][slot_idx])
        count = decrypt(private_key, ct, max_value=max_ballots)
        candidate_id = candidate_ids[slot_idx]
        tallies[candidate_id] = count
        total += count

    # Reconciliation check: sum of tallies must equal ballot count
    if total != ballot_count:
        raise VerificationError(
            f"Tally reconciliation failure: sum of tallies ({total}) "
            f"does not equal ballot count ({ballot_count}). "
            f"Drift = {total - ballot_count}"
        )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "artifact_type": "DECRYPTED_TALLY",
        "election_id": tally_artifact["election_id"],
        "candidate_tallies": tallies,
        "total_ballots": total,
        "ballot_count": ballot_count,
        "reconciliation_status": "BALANCED",
        "key_fingerprint": expected_fp,
    }
