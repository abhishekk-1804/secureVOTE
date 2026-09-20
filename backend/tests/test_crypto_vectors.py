"""
Tests for Canonical Cryptographic Test Vectors.
"""

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encode_vote_onehot
from app.crypto.canonical import ballot_domain, canonical_hash
from app.crypto.commitment import compute_ballot_commitment
from app.crypto.keys import compute_key_fingerprint, serialize_public_key
from app.crypto.serialization import serialize_ciphertext
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally
from app.crypto.vectors import (
    BALLOT_1_NONCES,
    BALLOT_2_NONCES,
    BALLOT_3_NONCES,
    CANDIDATE_COUNT,
    CANDIDATE_IDS,
    ELECTION_CANONICAL_ID,
    VECTOR_KEY_1_PUB_X,
    VECTOR_KEY_1_PUB_Y,
    VECTOR_PRIVATE_KEY_1,
    VECTOR_PRIVATE_KEY_2,
    VECTOR_PUBLIC_KEY_1,
    deterministic_encrypt,
)
from app.crypto.verification import V3Verifier


def build_deterministic_ballot(artifact_id: str, candidate_index: int, nonces: list[int]):
    onehot = encode_vote_onehot(candidate_index, CANDIDATE_COUNT)
    slots = []
    for val, nonce in zip(onehot, nonces):
        ct = deterministic_encrypt(VECTOR_PUBLIC_KEY_1, val, nonce)
        slots.append(serialize_ciphertext(ct))

    encrypted_vote = {
        "slots": slots,
        "candidate_ids": CANDIDATE_IDS,
        "candidate_count": CANDIDATE_COUNT,
    }

    key_fp = compute_key_fingerprint(VECTOR_PUBLIC_KEY_1)
    commitment = compute_ballot_commitment(
        election_id=ELECTION_CANONICAL_ID,
        artifact_id=artifact_id,
        encrypted_vote=encrypted_vote,
        candidate_count=CANDIDATE_COUNT,
        key_fingerprint=key_fp,
    )

    artifact_data = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": ELECTION_CANONICAL_ID,
        "artifact_id": artifact_id,
        "encrypted_vote": encrypted_vote,
        "commitment": commitment,
        "key_fingerprint": key_fp,
    }
    artifact_hash = canonical_hash(artifact_data, domain=ballot_domain(ELECTION_CANONICAL_ID))

    return {
        "protocol_version": PROTOCOL_VERSION,
        "artifact_type": "ENCRYPTED_BALLOT",
        "election_id": ELECTION_CANONICAL_ID,
        "artifact_id": artifact_id,
        "encrypted_vote": encrypted_vote,
        "commitment": commitment,
        "key_fingerprint": key_fp,
        "artifact_hash": artifact_hash,
    }


def test_canonical_public_key_coordinates():
    """Verify fixed public key coordinates match secp256r1 derivation."""
    assert len(VECTOR_KEY_1_PUB_X) == 64
    assert len(VECTOR_KEY_1_PUB_Y) == 64
    fp = compute_key_fingerprint(VECTOR_PUBLIC_KEY_1)
    assert len(fp) == 64


def test_deterministic_ballot_vector():
    """Build and verify deterministic ballot vectors."""
    b1 = build_deterministic_ballot("BALLOT-UUID-001", 0, BALLOT_1_NONCES)  # CAND-ALPHA
    b2 = build_deterministic_ballot("BALLOT-UUID-002", 1, BALLOT_2_NONCES)  # CAND-BETA
    b3 = build_deterministic_ballot("BALLOT-UUID-003", 3, BALLOT_3_NONCES)  # NOTA

    pub_data = serialize_public_key(VECTOR_PUBLIC_KEY_1)

    # Verify all 3 ballots independently
    for b in [b1, b2, b3]:
        results = V3Verifier.verify_full_ballot(b, pub_data)
        for r in results:
            assert r["status"] == "PASSED", f"{r['checkpoint']} failed: {r['details']}"

    # Homomorphic aggregation
    key_fp = compute_key_fingerprint(VECTOR_PUBLIC_KEY_1)
    tally = aggregate_encrypted_ballots([b1, b2, b3], ELECTION_CANONICAL_ID, key_fp)
    assert tally["ballot_count"] == 3

    # Decrypt
    decrypted = decrypt_tally(VECTOR_PRIVATE_KEY_1, tally)
    assert decrypted["candidate_tallies"] == {
        "CAND-ALPHA": 1,
        "CAND-BETA": 1,
        "CAND-GAMMA": 0,
        "NOTA": 1,
    }
    assert decrypted["total_ballots"] == 3
    assert decrypted["reconciliation_status"] == "BALANCED"

    # Full tally verification
    tally_results = V3Verifier.verify_full_tally(tally, decrypted)
    for r in tally_results:
        assert r["status"] == "PASSED", f"{r['checkpoint']} failed: {r['details']}"
