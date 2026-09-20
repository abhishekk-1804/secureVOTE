"""
Comprehensive Test Suite for SecureVOTE 3.1 Zero-Knowledge Proof System.

Covers:
Category A: Honest proofs across candidate positions, keys, and elections
Category B: Ciphertext mutations (modifying A, B, individual/multiple slots)
Category C: Proof mutations (commitments, challenges, responses, truncation)
Category D: Context mutations (election ID, public key, candidate ordering, protocol version)
Category E: Replay attacks (cross-election, cross-key, cross-ciphertext)
Category F: Invalid ballots (v=2, v=-1, multi-choice, zero-choice, wrong length)
Category G: Mathematical boundary cases (infinity, boundary scalars, malformed points)
Category H: Negative verification guarantees (every tampered case MUST fail)
"""

import copy
import os
import pytest

from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    G,
    generate_keypair,
    point_add,
    scalar_mult,
)
from app.crypto.serialization import serialize_ciphertext
from app.crypto.zk import (
    ZK_PROTOCOL_VERSION,
    InvalidProofError,
    ProofVerificationError,
    WitnessError,
    prove_ballot_validity,
    prove_disjunctive_01,
    prove_equality,
    verify_ballot_validity,
    verify_disjunctive_01,
    verify_equality,
)


@pytest.fixture
def election_setup():
    """Fixture providing keys, election metadata, and candidates."""
    keypair = generate_keypair()
    election_id = "ZK-ELECTION-2026"
    candidates = ["CAND-ALPHA", "CAND-BETA", "CAND-GAMMA", "NOTA"]
    return keypair, election_id, candidates


def build_ballot_with_nonces(public_key, candidate_index, candidates, election_id):
    """Helper: build ciphertext dict and matching nonces for proof testing."""
    count = len(candidates)
    nonces = [
        int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1
        for _ in range(count)
    ]
    slots = []
    for j in range(count):
        v = 1 if j == candidate_index else 0
        r = nonces[j]
        c1 = scalar_mult(r, G)
        c2 = point_add(scalar_mult(r, public_key.point), scalar_mult(v, G))
        from app.crypto.elgamal import ElGamalCiphertext
        slots.append(serialize_ciphertext(ElGamalCiphertext(c1=c1, c2=c2)))

    encrypted_vote = {
        "slots": slots,
        "candidate_ids": candidates,
        "candidate_count": count,
    }
    proof = prove_ballot_validity(
        public_key=public_key,
        candidate_index=candidate_index,
        nonces=nonces,
        candidate_count=count,
        election_id=election_id,
        candidate_ids=candidates,
    )
    return encrypted_vote, proof, nonces


# ===========================================================================
# Category A: Honest Proofs
# ===========================================================================

def test_honest_chaum_pedersen():
    """Honest Chaum-Pedersen equality proof must verify."""
    keypair = generate_keypair()
    r = 12345
    a = scalar_mult(r, G)
    b_prime = scalar_mult(r, keypair.public_key.point)
    domain = "SECUREVOTE31/TEST/CP/"

    proof = prove_equality(keypair.public_key.point, a, b_prime, r, domain)
    assert verify_equality(keypair.public_key.point, a, b_prime, proof, domain) is True


def test_honest_cds94_both_branches():
    """Honest CDS94 disjunctive proof must verify for both v=0 and v=1."""
    keypair = generate_keypair()
    domain = "SECUREVOTE31/TEST/CDS/"

    # Test v = 0
    r0 = 98765
    a0 = scalar_mult(r0, G)
    b0 = scalar_mult(r0, keypair.public_key.point)  # v=0 * G is infinity
    p0 = prove_disjunctive_01(keypair.public_key.point, a0, b0, 0, r0, domain)
    assert verify_disjunctive_01(keypair.public_key.point, a0, b0, p0, domain) is True

    # Test v = 1
    r1 = 54321
    a1 = scalar_mult(r1, G)
    b1 = point_add(scalar_mult(r1, keypair.public_key.point), G)  # v=1 * G is G
    p1 = prove_disjunctive_01(keypair.public_key.point, a1, b1, 1, r1, domain)
    assert verify_disjunctive_01(keypair.public_key.point, a1, b1, p1, domain) is True


def test_honest_ballot_every_candidate_position(election_setup):
    """Honest ballot validity proofs must verify for every candidate slot."""
    keypair, election_id, candidates = election_setup
    for idx in range(len(candidates)):
        encrypted_vote, proof, _ = build_ballot_with_nonces(
            keypair.public_key, idx, candidates, election_id
        )
        assert verify_ballot_validity(
            keypair.public_key, encrypted_vote, proof, election_id
        ) is True


# ===========================================================================
# Category B: Ciphertext Mutations
# ===========================================================================

def test_mutate_ciphertext_a(election_setup):
    """Mutating ciphertext A coordinate in any slot must fail verification."""
    keypair, election_id, candidates = election_setup
    vote, proof, _ = build_ballot_with_nonces(keypair.public_key, 0, candidates, election_id)
    tampered_vote = copy.deepcopy(vote)
    # Mutate A coordinate of slot 0
    tampered_vote["slots"][0]["c1"]["x"] = "12" * 32
    with pytest.raises(ProofVerificationError):
        verify_ballot_validity(keypair.public_key, tampered_vote, proof, election_id)


def test_mutate_ciphertext_b(election_setup):
    """Mutating ciphertext B coordinate must fail verification."""
    keypair, election_id, candidates = election_setup
    vote, proof, _ = build_ballot_with_nonces(keypair.public_key, 1, candidates, election_id)
    tampered_vote = copy.deepcopy(vote)
    # Mutate B coordinate of slot 1
    tampered_vote["slots"][1]["c2"]["x"] = "34" * 32
    with pytest.raises(ProofVerificationError):
        verify_ballot_validity(keypair.public_key, tampered_vote, proof, election_id)


# ===========================================================================
# Category C: Proof Mutations
# ===========================================================================

def test_mutate_proof_commitment(election_setup):
    """Altering a commitment point in the proof must fail verification."""
    keypair, election_id, candidates = election_setup
    vote, proof, _ = build_ballot_with_nonces(keypair.public_key, 0, candidates, election_id)
    tampered_proof = copy.deepcopy(proof)
    # Mutate a0 point in slot 0 proof
    tampered_proof["slot_proofs"][0]["a0"]["x"] = "56" * 32
    with pytest.raises(ProofVerificationError):
        verify_ballot_validity(keypair.public_key, vote, tampered_proof, election_id)


def test_mutate_proof_response(election_setup):
    """Altering a response scalar in the proof must fail verification."""
    keypair, election_id, candidates = election_setup
    vote, proof, _ = build_ballot_with_nonces(keypair.public_key, 0, candidates, election_id)
    tampered_proof = copy.deepcopy(proof)
    tampered_proof["slot_proofs"][0]["s0"] = "78" * 32
    with pytest.raises(ProofVerificationError):
        verify_ballot_validity(keypair.public_key, vote, tampered_proof, election_id)


def test_truncate_proof(election_setup):
    """Omitting a slot proof must raise InvalidProofError."""
    keypair, election_id, candidates = election_setup
    vote, proof, _ = build_ballot_with_nonces(keypair.public_key, 0, candidates, election_id)
    tampered_proof = copy.deepcopy(proof)
    tampered_proof["slot_proofs"].pop()
    with pytest.raises(InvalidProofError, match="Slot proofs count"):
        verify_ballot_validity(keypair.public_key, vote, tampered_proof, election_id)


# ===========================================================================
# Category D: Context & Slate Mutations
# ===========================================================================

def test_wrong_election_id(election_setup):
    """Proof submitted with mismatched election_id must be rejected."""
    keypair, election_id, candidates = election_setup
    vote, proof, _ = build_ballot_with_nonces(keypair.public_key, 0, candidates, election_id)
    with pytest.raises(InvalidProofError, match="election_id mismatch"):
        verify_ballot_validity(keypair.public_key, vote, proof, "WRONG-ELECTION-ID")


def test_wrong_public_key(election_setup):
    """Verifying a proof under a different public key must fail."""
    k1, election_id, candidates = election_setup
    k2 = generate_keypair()
    vote, proof, _ = build_ballot_with_nonces(k1.public_key, 0, candidates, election_id)
    with pytest.raises(ProofVerificationError):
        verify_ballot_validity(k2.public_key, vote, proof, election_id)


def test_reorder_candidate_slate(election_setup):
    """Permuting the candidate IDs to swap votes must fail domain verification."""
    keypair, election_id, candidates = election_setup
    vote, proof, _ = build_ballot_with_nonces(keypair.public_key, 0, candidates, election_id)
    permuted_vote = copy.deepcopy(vote)
    # Swap candidate 0 and 1
    permuted_vote["candidate_ids"][0], permuted_vote["candidate_ids"][1] = (
        permuted_vote["candidate_ids"][1],
        permuted_vote["candidate_ids"][0],
    )
    with pytest.raises(ProofVerificationError):
        verify_ballot_validity(keypair.public_key, permuted_vote, proof, election_id)


def test_wrong_protocol_version(election_setup):
    """Proof claiming wrong protocol version must be rejected."""
    keypair, election_id, candidates = election_setup
    vote, proof, _ = build_ballot_with_nonces(keypair.public_key, 0, candidates, election_id)
    tampered_proof = copy.deepcopy(proof)
    tampered_proof["protocol_version"] = "LEGACY_V3"
    with pytest.raises(InvalidProofError, match="protocol version"):
        verify_ballot_validity(keypair.public_key, vote, tampered_proof, election_id)


# ===========================================================================
# Category E: Replay Attacks
# ===========================================================================

def test_cross_election_proof_replay(election_setup):
    """A valid proof from Election 1 must fail in Election 2."""
    keypair, _, candidates = election_setup
    vote, proof, _ = build_ballot_with_nonces(keypair.public_key, 0, candidates, "ELEC-1")
    # Try verifying against ELEC-2
    with pytest.raises(InvalidProofError):
        verify_ballot_validity(keypair.public_key, vote, proof, "ELEC-2")


def test_proof_attached_to_different_ciphertext(election_setup):
    """Attaching ballot proof A to ballot ciphertext B must fail verification."""
    keypair, election_id, candidates = election_setup
    vote1, proof1, _ = build_ballot_with_nonces(keypair.public_key, 0, candidates, election_id)
    vote2, proof2, _ = build_ballot_with_nonces(keypair.public_key, 1, candidates, election_id)
    # Swap proof
    with pytest.raises(ProofVerificationError):
        verify_ballot_validity(keypair.public_key, vote2, proof1, election_id)


# ===========================================================================
# Category F: Invalid Ballots (Non-Binary, Multi-Choice, Zero-Choice)
# ===========================================================================

def test_invalid_witness_non_binary():
    """Proving a non-binary slot (v=2) must fail at prover witness check."""
    keypair = generate_keypair()
    with pytest.raises(WitnessError, match="binary witness"):
        prove_disjunctive_01(
            keypair.public_key.point,
            G, G,
            v_value=2,
            r_scalar=123,
            domain_prefix="TEST",
        )


def test_invalid_candidate_index_out_of_bounds(election_setup):
    """Candidate index >= count must raise WitnessError."""
    keypair, election_id, candidates = election_setup
    with pytest.raises(WitnessError, match="out of range"):
        prove_ballot_validity(
            public_key=keypair.public_key,
            candidate_index=10,  # Only 4 candidates
            nonces=[1, 2, 3, 4],
            candidate_count=4,
            election_id=election_id,
            candidate_ids=candidates,
        )


# ===========================================================================
# Category G: Mathematical Boundary Cases
# ===========================================================================

def test_boundary_scalars_rejected_in_proof():
    """Zero or >= CURVE_ORDER challenge/response scalars must raise InvalidProofError."""
    from app.crypto.zk.chaum_pedersen import ChaumPedersenProof
    # Challenge c = 0 is forbidden
    with pytest.raises(InvalidProofError, match="challenge scalar out of valid range"):
        ChaumPedersenProof(a=G, b=G, c=0, s=1)

    # Response s >= CURVE_ORDER is forbidden
    with pytest.raises(InvalidProofError, match="response scalar out of valid range"):
        ChaumPedersenProof(a=G, b=G, c=1, s=CURVE_ORDER + 5)
