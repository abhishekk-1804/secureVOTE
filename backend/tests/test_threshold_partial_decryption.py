"""
SecureVOTE 3.2 — Verifiable Partial Decryption & Chaum-Pedersen Proof Tests.

Validates:
1. Correctness of Chaum-Pedersen discrete-log equality proofs for partial decryption shares.
2. Complete Negative Test Matrix (altered points, scalars, wrong keys, replay attacks).
3. Cross-election, cross-candidate, and cross-trustee domain separation.
4. Robustness against malformed, infinity, and off-curve points.
5. Canonical serialization round-trip for partial decryption artifacts.
6. Zero private key / nonce leakage.
"""

import pytest

from app.crypto.elgamal import (
    CURVE_ORDER,
    G,
    INFINITY,
    ECPoint,
    point_add,
    point_on_curve,
    scalar_mult,
)
from app.crypto.threshold import (
    ChaumPedersenEqualityProof,
    InvalidShareError,
    PartialDecryptionProofError,
    PartialDecryptionShare,
    ThresholdSerializationError,
    TrusteePrivateKeyShare,
    check_partial_decryption_proof,
    compute_partial_decryption,
    compute_tally_partial_decryptions,
    deserialize_partial_decryption_proof,
    deserialize_partial_decryption_share,
    deserialize_tally_partial_decryption_package,
    prove_partial_decryption,
    serialize_partial_decryption_proof,
    serialize_partial_decryption_share,
    serialize_tally_partial_decryption_package,
    verify_partial_decryption_proof,
    verify_partial_decryption_share,
    verify_tally_partial_decryption_package,
)


@pytest.fixture
def setup_trustee_and_ciphertext():
    """Setup honest trustee key-share and candidate ciphertext components."""
    election_id = "ELEC-TEST-2026"
    candidate_id = "CAND-01"
    trustee_id = 1

    # Trustee 1 private key share x_1 and public verification key Y_1
    x_1 = 0x5a1f8c4e2b9d7a3f106482e9d5c7b3a1f0e4d2c8b6a482619374628192a47291 % CURVE_ORDER
    y_1 = scalar_mult(x_1, G)

    # Joint public key (for context)
    joint_public_key = scalar_mult(0x123456789, G)

    trustee_share = TrusteePrivateKeyShare(
        election_id=election_id,
        trustee_id=trustee_id,
        secret_share=x_1,
        joint_public_key=joint_public_key,
        verification_key=y_1,
    )

    # Aggregated ciphertext A_j = R_j * G
    r_j = 0x9876543210fedcba9876543210fedcba9876543210fedcba9876543210fedcba % CURVE_ORDER
    a_j = scalar_mult(r_j, G)

    return {
        "election_id": election_id,
        "candidate_id": candidate_id,
        "trustee_id": trustee_id,
        "x_1": x_1,
        "y_1": y_1,
        "trustee_share": trustee_share,
        "r_j": r_j,
        "a_j": a_j,
    }


# ===========================================================================
# 1. Positive Tests: Valid Partial Decryption
# ===========================================================================

def test_valid_partial_decryption(setup_trustee_and_ciphertext):
    """Verify that an honest trustee computes a valid partial decryption share and proof."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(
        trustee_share=ctx["trustee_share"],
        candidate_id=ctx["candidate_id"],
        a_point=ctx["a_j"],
    )

    assert isinstance(share, PartialDecryptionShare)
    assert share.election_id == ctx["election_id"]
    assert share.candidate_id == ctx["candidate_id"]
    assert share.trustee_id == ctx["trustee_id"]
    assert point_on_curve(share.partial_decryption)
    assert not share.partial_decryption.is_infinity

    # Mathematical consistency: W = x_1 * A_j
    expected_w = scalar_mult(ctx["x_1"], ctx["a_j"])
    assert share.partial_decryption == expected_w

    # Proof verification
    is_valid = verify_partial_decryption_share(
        share=share,
        verification_key=ctx["y_1"],
        a_point=ctx["a_j"],
    )
    assert is_valid is True

    # Strict check passes without raising
    check_partial_decryption_proof(
        proof=share.proof,
        y_point=ctx["y_1"],
        a_point=ctx["a_j"],
        w_point=share.partial_decryption,
        election_id=ctx["election_id"],
        candidate_id=ctx["candidate_id"],
        trustee_id=ctx["trustee_id"],
    )


# ===========================================================================
# Negative Test Matrix (Items 2 through 18)
# ===========================================================================

def test_altered_w_rejected(setup_trustee_and_ciphertext):
    """Item 2: Altered partial decryption point W must fail verification."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    # Mutate W point
    bad_w = point_add(share.partial_decryption, G)
    bad_share = PartialDecryptionShare(
        election_id=share.election_id,
        candidate_id=share.candidate_id,
        trustee_id=share.trustee_id,
        partial_decryption=bad_w,
        proof=share.proof,
    )

    assert verify_partial_decryption_share(bad_share, ctx["y_1"], ctx["a_j"]) is False
    with pytest.raises(PartialDecryptionProofError):
        check_partial_decryption_proof(
            share.proof, ctx["y_1"], ctx["a_j"], bad_w,
            ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"]
        )


def test_altered_comm_1_rejected(setup_trustee_and_ciphertext):
    """Item 3: Altered commitment point comm_1 must fail verification."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    bad_proof = ChaumPedersenEqualityProof(
        comm_1=point_add(share.proof.comm_1, G),
        comm_2=share.proof.comm_2,
        c=share.proof.c,
        s=share.proof.s,
    )
    assert verify_partial_decryption_proof(
        bad_proof, ctx["y_1"], ctx["a_j"], share.partial_decryption,
        ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"]
    ) is False


def test_altered_comm_2_rejected(setup_trustee_and_ciphertext):
    """Item 4: Altered commitment point comm_2 must fail verification."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    bad_proof = ChaumPedersenEqualityProof(
        comm_1=share.proof.comm_1,
        comm_2=point_add(share.proof.comm_2, G),
        c=share.proof.c,
        s=share.proof.s,
    )
    assert verify_partial_decryption_proof(
        bad_proof, ctx["y_1"], ctx["a_j"], share.partial_decryption,
        ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"]
    ) is False


def test_altered_c_rejected(setup_trustee_and_ciphertext):
    """Item 5: Altered Fiat-Shamir challenge c must fail verification."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    bad_proof = ChaumPedersenEqualityProof(
        comm_1=share.proof.comm_1,
        comm_2=share.proof.comm_2,
        c=(share.proof.c + 1) % CURVE_ORDER,
        s=share.proof.s,
    )
    assert verify_partial_decryption_proof(
        bad_proof, ctx["y_1"], ctx["a_j"], share.partial_decryption,
        ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"]
    ) is False


def test_altered_s_rejected(setup_trustee_and_ciphertext):
    """Item 6: Altered response scalar s must fail verification."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    bad_proof = ChaumPedersenEqualityProof(
        comm_1=share.proof.comm_1,
        comm_2=share.proof.comm_2,
        c=share.proof.c,
        s=(share.proof.s + 1) % CURVE_ORDER,
    )
    assert verify_partial_decryption_proof(
        bad_proof, ctx["y_1"], ctx["a_j"], share.partial_decryption,
        ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"]
    ) is False


def test_wrong_trustee_verification_key_rejected(setup_trustee_and_ciphertext):
    """Item 7: Verification against wrong trustee verification key Y_k must fail."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    wrong_y = scalar_mult(999999, G)
    assert verify_partial_decryption_share(share, wrong_y, ctx["a_j"]) is False


def test_wrong_trustee_id_rejected(setup_trustee_and_ciphertext):
    """Item 8: Proof claimed for a different trustee ID must fail."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    # Verifying with trustee_id = 2 instead of 1
    assert verify_partial_decryption_proof(
        share.proof, ctx["y_1"], ctx["a_j"], share.partial_decryption,
        ctx["election_id"], ctx["candidate_id"], trustee_id=2
    ) is False


def test_wrong_election_id_rejected(setup_trustee_and_ciphertext):
    """Item 9: Verification under wrong election ID must fail."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    assert verify_partial_decryption_proof(
        share.proof, ctx["y_1"], ctx["a_j"], share.partial_decryption,
        "WRONG-ELECTION-2026", ctx["candidate_id"], ctx["trustee_id"]
    ) is False


def test_wrong_candidate_id_rejected(setup_trustee_and_ciphertext):
    """Item 10: Verification under wrong candidate ID must fail."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    assert verify_partial_decryption_proof(
        share.proof, ctx["y_1"], ctx["a_j"], share.partial_decryption,
        ctx["election_id"], "CAND-99", ctx["trustee_id"]
    ) is False


def test_wrong_aggregated_a_rejected(setup_trustee_and_ciphertext):
    """Item 11: Verification against a different aggregated ciphertext point A must fail."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    different_a = scalar_mult(0x5555555, G)
    assert verify_partial_decryption_share(share, ctx["y_1"], different_a) is False


def test_infinity_w_rejected(setup_trustee_and_ciphertext):
    """Item 12: Partial decryption point at infinity must be rejected."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    assert verify_partial_decryption_proof(
        share.proof, ctx["y_1"], ctx["a_j"], INFINITY,
        ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"]
    ) is False


def test_off_curve_w_rejected(setup_trustee_and_ciphertext):
    """Item 13: Off-curve partial decryption point must be rejected."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    # Construct invalid off-curve point
    off_curve_w = ECPoint(x=12345, y=67890)
    assert not point_on_curve(off_curve_w)

    assert verify_partial_decryption_proof(
        share.proof, ctx["y_1"], ctx["a_j"], off_curve_w,
        ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"]
    ) is False


def test_malformed_proof_rejected(setup_trustee_and_ciphertext):
    """Item 14: Malformed proof objects or out-of-range scalars must be rejected."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    # Scalar c = 0 (out of range [1, q-1])
    bad_proof_zero_c = ChaumPedersenEqualityProof(
        comm_1=share.proof.comm_1,
        comm_2=share.proof.comm_2,
        c=0,
        s=share.proof.s,
    )
    assert verify_partial_decryption_proof(
        bad_proof_zero_c, ctx["y_1"], ctx["a_j"], share.partial_decryption,
        ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"]
    ) is False

    # Scalar s >= CURVE_ORDER
    bad_proof_huge_s = ChaumPedersenEqualityProof(
        comm_1=share.proof.comm_1,
        comm_2=share.proof.comm_2,
        c=share.proof.c,
        s=CURVE_ORDER + 5,
    )
    assert verify_partial_decryption_proof(
        bad_proof_huge_s, ctx["y_1"], ctx["a_j"], share.partial_decryption,
        ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"]
    ) is False


def test_duplicate_share_artifact_behavior(setup_trustee_and_ciphertext):
    """Item 15: Verify package handles duplicate/repeated shares consistently."""
    ctx = setup_trustee_and_ciphertext
    share_1 = compute_partial_decryption(ctx["trustee_share"], "CAND-01", ctx["a_j"])
    share_2 = compute_partial_decryption(ctx["trustee_share"], "CAND-01", ctx["a_j"])

    # Both are valid independent nonces/proofs for the same candidate
    assert share_1.partial_decryption == share_2.partial_decryption
    assert verify_partial_decryption_share(share_1, ctx["y_1"], ctx["a_j"]) is True
    assert verify_partial_decryption_share(share_2, ctx["y_1"], ctx["a_j"]) is True


def test_replay_from_another_election_rejected(setup_trustee_and_ciphertext):
    """Item 16: Cross-election replay attack must fail challenge verification."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    # Replay share against target election "ELEC-2027-PARLIAMENT"
    replayed_share = PartialDecryptionShare(
        election_id="ELEC-2027-PARLIAMENT",
        candidate_id=share.candidate_id,
        trustee_id=share.trustee_id,
        partial_decryption=share.partial_decryption,
        proof=share.proof,
    )
    assert verify_partial_decryption_share(
        replayed_share,
        ctx["y_1"],
        ctx["a_j"],
        expected_election_id="ELEC-2027-PARLIAMENT",
    ) is False


def test_replay_across_candidate_slots_rejected(setup_trustee_and_ciphertext):
    """Item 17: Cross-candidate replay attack must fail verification."""
    ctx = setup_trustee_and_ciphertext
    share_cand1 = compute_partial_decryption(ctx["trustee_share"], "CAND-01", ctx["a_j"])

    # Attempt to use proof from CAND-01 to satisfy CAND-02
    replayed_for_cand2 = PartialDecryptionShare(
        election_id=share_cand1.election_id,
        candidate_id="CAND-02",
        trustee_id=share_cand1.trustee_id,
        partial_decryption=share_cand1.partial_decryption,
        proof=share_cand1.proof,
    )
    assert verify_partial_decryption_share(
        replayed_for_cand2,
        ctx["y_1"],
        ctx["a_j"],
        expected_candidate_id="CAND-02",
    ) is False


def test_proof_generated_with_another_trustees_key_rejected(setup_trustee_and_ciphertext):
    """Item 18: Proof generated with trustee 2's key claiming trustee 1 identity must fail."""
    ctx = setup_trustee_and_ciphertext

    # Trustee 2 key
    x_2 = 0x112233445566778899aabbccddeeff00112233445566778899aabbccddeeff00 % CURVE_ORDER
    y_2 = scalar_mult(x_2, G)
    w_2 = scalar_mult(x_2, ctx["a_j"])

    # Trustee 2 creates proof with their own secret x_2
    proof_t2 = prove_partial_decryption(
        x_i=x_2,
        y_point=y_2,
        a_point=ctx["a_j"],
        w_point=w_2,
        election_id=ctx["election_id"],
        candidate_id=ctx["candidate_id"],
        trustee_id=2,
    )

    # An adversary attempts to submit proof_t2 for Trustee 1 with Trustee 1's public key
    assert verify_partial_decryption_proof(
        proof_t2,
        y_point=ctx["y_1"],  # Claimed trustee 1 key
        a_point=ctx["a_j"],
        w_point=w_2,
        election_id=ctx["election_id"],
        candidate_id=ctx["candidate_id"],
        trustee_id=1,  # Claimed trustee 1 ID
    ) is False


# ===========================================================================
# Protocol Version & Binding Tests
# ===========================================================================

def test_protocol_version_mismatch_rejected(setup_trustee_and_ciphertext):
    """Verify that proofs generated under a different protocol version are rejected."""
    ctx = setup_trustee_and_ciphertext
    w_point = scalar_mult(ctx["x_1"], ctx["a_j"])
    proof = prove_partial_decryption(
        x_i=ctx["x_1"],
        y_point=ctx["y_1"],
        a_point=ctx["a_j"],
        w_point=w_point,
        election_id=ctx["election_id"],
        candidate_id=ctx["candidate_id"],
        trustee_id=ctx["trustee_id"],
        protocol_version="SECUREVOTE32-DRAFT",
    )

    # Verifying under canonical version "SECUREVOTE32" must fail challenge check
    assert verify_partial_decryption_proof(
        proof, ctx["y_1"], ctx["a_j"], w_point,
        ctx["election_id"], ctx["candidate_id"], ctx["trustee_id"],
        protocol_version="SECUREVOTE32",
    ) is False


# ===========================================================================
# Serialization & Tally Package Tests
# ===========================================================================

def test_partial_decryption_serialization_round_trip(setup_trustee_and_ciphertext):
    """Verify canonical serialization and deserialization for partial decryption artifacts."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    # Proof serialization
    ser_proof = serialize_partial_decryption_proof(share.proof)
    de_proof = deserialize_partial_decryption_proof(ser_proof)
    assert de_proof.comm_1 == share.proof.comm_1
    assert de_proof.comm_2 == share.proof.comm_2
    assert de_proof.c == share.proof.c
    assert de_proof.s == share.proof.s

    # Share serialization
    ser_share = serialize_partial_decryption_share(share)
    de_share = deserialize_partial_decryption_share(ser_share)
    assert de_share.election_id == share.election_id
    assert de_share.candidate_id == share.candidate_id
    assert de_share.trustee_id == share.trustee_id
    assert de_share.partial_decryption == share.partial_decryption
    assert de_share.proof.c == share.proof.c


def test_tally_package_computation_and_verification(setup_trustee_and_ciphertext):
    """Verify multi-candidate tally partial decryption computation and batch verification."""
    ctx = setup_trustee_and_ciphertext

    candidate_a_points = {
        "CAND-01": ctx["a_j"],
        "CAND-02": scalar_mult(0x33333333, G),
        "CAND-03": scalar_mult(0x77777777, G),
    }

    tally_package = compute_tally_partial_decryptions(
        trustee_share=ctx["trustee_share"],
        candidate_a_points=candidate_a_points,
    )

    assert len(tally_package.shares) == 3
    assert set(tally_package.shares.keys()) == {"CAND-01", "CAND-02", "CAND-03"}

    # Verify entire package
    is_valid = verify_tally_partial_decryption_package(
        package=tally_package,
        verification_key=ctx["y_1"],
        candidate_a_points=candidate_a_points,
        expected_election_id=ctx["election_id"],
        expected_trustee_id=ctx["trustee_id"],
    )
    assert is_valid is True

    # Package serialization round trip
    ser_pkg = serialize_tally_partial_decryption_package(tally_package)
    de_pkg = deserialize_tally_partial_decryption_package(ser_pkg)
    assert de_pkg.election_id == tally_package.election_id
    assert len(de_pkg.shares) == 3


def test_malformed_partial_decryption_json_rejected():
    """Verify malformed JSON payloads fail with ThresholdSerializationError."""
    with pytest.raises(ThresholdSerializationError):
        deserialize_partial_decryption_proof({"bad_field": 123})

    with pytest.raises(ThresholdSerializationError):
        deserialize_partial_decryption_share({"election_id": "TEST"})

    with pytest.raises(ThresholdSerializationError):
        deserialize_tally_partial_decryption_package({"trustee_id": "not_an_int"})


# ===========================================================================
# Zero Secret Leakage Tests
# ===========================================================================

def test_no_private_secret_leakage_in_decryption(setup_trustee_and_ciphertext):
    """Verify that partial decryption objects never expose private shares or nonces in repr."""
    ctx = setup_trustee_and_ciphertext
    share = compute_partial_decryption(ctx["trustee_share"], ctx["candidate_id"], ctx["a_j"])

    repr_share = repr(share)
    repr_proof = repr(share.proof)

    secret_hex = hex(ctx["x_1"])[2:]
    assert secret_hex not in repr_share
    assert secret_hex not in repr_proof
    assert str(ctx["x_1"]) not in repr_share
    assert str(ctx["x_1"]) not in repr_proof
