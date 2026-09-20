"""
Tests for Standalone Independent Verifier with SecureVOTE 3.1 ZK Ballot Validity Proofs.
"""

import copy
import os
import pytest

from app.crypto import PROTOCOL_VERSION
from app.crypto.canonical import ballot_domain, canonical_hash
from app.crypto.commitment import compute_ballot_commitment
from app.crypto.elgamal import (
    CURVE_ORDER,
    ElGamalCiphertext,
    G,
    generate_keypair,
    point_add,
    scalar_mult,
)
from app.crypto.keys import compute_key_fingerprint, serialize_public_key
from app.crypto.serialization import serialize_ciphertext
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally
from app.crypto.zk import prove_ballot_validity
from standalone_verifier.v3_verifier import StandaloneV3ElectionVerifier


@pytest.fixture
def zkp_package():
    """Build a complete, mathematically valid election package with ZK ballot validity proofs."""
    keypair = generate_keypair()
    pub_data = serialize_public_key(keypair.public_key)
    key_fp = compute_key_fingerprint(keypair.public_key)
    election_id = "V3-1-ZKP-VERIFY-001"
    candidates = ["CAND-A", "CAND-B", "NOTA"]
    candidate_count = len(candidates)

    votes = [0, 1, 0, 2]
    ballots = []

    for v_idx in votes:
        nonces = [
            int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1
            for _ in range(candidate_count)
        ]
        slots = []
        for j in range(candidate_count):
            val = 1 if j == v_idx else 0
            r = nonces[j]
            c1 = scalar_mult(r, G)
            c2 = point_add(scalar_mult(r, keypair.public_key.point), scalar_mult(val, G))
            slots.append(serialize_ciphertext(ElGamalCiphertext(c1=c1, c2=c2)))

        encrypted_vote = {
            "slots": slots,
            "candidate_ids": candidates,
            "candidate_count": candidate_count,
        }

        proof = prove_ballot_validity(
            public_key=keypair.public_key,
            candidate_index=v_idx,
            nonces=nonces,
            candidate_count=candidate_count,
            election_id=election_id,
            candidate_ids=candidates,
        )

        art_id = f"BALLOT-{os.urandom(4).hex()}"
        commitment = compute_ballot_commitment(
            election_id=election_id,
            artifact_id=art_id,
            encrypted_vote=encrypted_vote,
            candidate_count=candidate_count,
            key_fingerprint=key_fp,
        )
        artifact_data = {
            "protocol_version": PROTOCOL_VERSION,
            "election_id": election_id,
            "artifact_id": art_id,
            "encrypted_vote": encrypted_vote,
            "commitment": commitment,
            "key_fingerprint": key_fp,
            "proof": proof,
        }
        art_hash = canonical_hash(artifact_data, domain=ballot_domain(election_id))

        ballots.append({
            "protocol_version": PROTOCOL_VERSION,
            "artifact_type": "ENCRYPTED_BALLOT",
            "election_id": election_id,
            "artifact_id": art_id,
            "encrypted_vote": encrypted_vote,
            "commitment": commitment,
            "key_fingerprint": key_fp,
            "artifact_hash": art_hash,
            "proof": proof,
        })

    encrypted_tally = aggregate_encrypted_ballots(ballots, election_id, key_fp)
    decrypted_tally = decrypt_tally(keypair, encrypted_tally)

    package = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "public_key": pub_data,
        "candidates": candidates,
        "ballots": ballots,
        "encrypted_tally": encrypted_tally,
        "decrypted_tally": decrypted_tally,
    }
    return package, keypair


def test_zkp_package_happy_path(zkp_package):
    """Honest package with valid ZK validity proofs must pass all verifier checks."""
    package, keypair = zkp_package
    res = StandaloneV3ElectionVerifier.verify_package(package, keypair)

    assert res["verified"] is True
    assert res["ciphertext_structurally_valid"] is True
    assert res["commitment_valid"] is True
    assert res["proof_structurally_valid"] is True
    assert res["proof_cryptographically_valid"] is True
    assert res["ballot_validity_valid"] is True
    assert res["ballot_aggregation_valid"] is True
    assert res["tally_valid"] is True


def test_zkp_package_tampered_slot_proof(zkp_package):
    """Tampering with a slot proof in a ballot must fail ZK verification."""
    package, keypair = zkp_package
    bad_pkg = copy.deepcopy(package)
    # Tamper with challenge scalar c0 in slot 0 proof of ballot 0
    bad_pkg["ballots"][0]["proof"]["slot_proofs"][0]["c0"] = "ff" * 32

    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False
    assert res["proof_cryptographically_valid"] is False
    assert res["ballot_validity_valid"] is False

    failed = [c["checkpoint"] for c in res["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_7b_zk_ballot_validity" in failed


def test_zkp_package_tampered_sum_proof(zkp_package):
    """Tampering with the aggregate sum proof must fail ZK verification."""
    package, keypair = zkp_package
    bad_pkg = copy.deepcopy(package)
    # Tamper with sum proof scalar s
    bad_pkg["ballots"][0]["proof"]["sum_proof"]["s"] = "ee" * 32

    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False
    assert res["proof_cryptographically_valid"] is False

    failed = [c["checkpoint"] for c in res["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_7b_zk_ballot_validity" in failed


def test_zkp_package_tampered_ciphertext_breaks_zkp(zkp_package):
    """Altering a ciphertext point must fail both commitment and ZK proof verification."""
    package, keypair = zkp_package
    bad_pkg = copy.deepcopy(package)
    # Alter coordinate of slot 1 in ballot 1
    bad_pkg["ballots"][1]["encrypted_vote"]["slots"][1]["c1"]["x"] = "11" * 32

    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False
    # Both commitment and ZKP fail
    assert res["commitment_valid"] is False
    assert res["proof_cryptographically_valid"] is False


def test_no_zkp_in_securevote31_fails(zkp_package):
    """In SECUREVOTE31 mode, ballots without ZK validity proofs must fail checkpoint 7b."""
    package, keypair = zkp_package
    bad_pkg = copy.deepcopy(package)
    bad_pkg["protocol_version"] = "SECUREVOTE31"
    for b in bad_pkg["ballots"]:
        b.pop("proof", None)

    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False
    assert res["ballot_validity_valid"] is False
    assert res["ballot_validity_status"] == "NOT_PRESENT"
    failed = [c["checkpoint"] for c in res["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_7b_zk_ballot_validity" in failed


def test_mixed_zkp_and_non_zkp_ballots_rejected(zkp_package):
    """Packages with some proven ballots and some unproven ballots must be explicitly rejected."""
    package, keypair = zkp_package
    bad_pkg = copy.deepcopy(package)
    bad_pkg["protocol_version"] = "SECUREVOTE31"
    # Remove proof from only the first ballot
    bad_pkg["ballots"][0].pop("proof", None)

    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False
    assert res["ballot_validity_valid"] is False
    assert res["ballot_validity_status"] == "INVALID"
    failed = [c["checkpoint"] for c in res["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_7b_zk_ballot_validity" in failed


def test_malformed_proof_rejected(zkp_package):
    """Malformed or non-dict proof structures must be caught as structural proof invalidity."""
    package, keypair = zkp_package
    bad_pkg = copy.deepcopy(package)
    bad_pkg["ballots"][0]["proof"] = "MALFORMED_PROOF_STRING"

    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False
    assert res["ballot_validity_valid"] is False
    assert res["ballot_validity_status"] == "INVALID"
    failed = [c["checkpoint"] for c in res["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_7b_zk_ballot_validity" in failed


def test_proof_replay_across_elections_rejected(zkp_package):
    """Proofs generated for election A must fail verification when replayed in election B."""
    package, keypair = zkp_package
    bad_pkg = copy.deepcopy(package)
    bad_pkg["election_id"] = "FOREIGN-ELECTION-XYZ"
    # Replay ballot artifacts in foreign election
    for b in bad_pkg["ballots"]:
        b["election_id"] = "FOREIGN-ELECTION-XYZ"

    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False
    # Fails cryptographic ZKP verification because election_id is bound into transcript
    assert res["proof_cryptographically_valid"] is False


def test_wrong_public_key_rejected(zkp_package):
    """Proofs verified against an mismatched public key must fail verification."""
    from app.crypto.elgamal import generate_keypair
    package, keypair = zkp_package
    foreign_keypair = generate_keypair()
    bad_pkg = copy.deepcopy(package)
    bad_pkg["public_key"] = serialize_public_key(foreign_keypair.public_key)

    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False


def test_candidate_reorder_rejected(zkp_package):
    """Reordering candidates must fail ballot structure or commitment verification."""
    package, keypair = zkp_package
    bad_pkg = copy.deepcopy(package)
    # Reorder candidates in ballot 0
    cands = bad_pkg["ballots"][0]["encrypted_vote"]["candidate_ids"]
    bad_pkg["ballots"][0]["encrypted_vote"]["candidate_ids"] = list(reversed(cands))

    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False


def test_altered_domain_separator_rejected():
    """Altering domain separator in Fiat-Shamir transcript must fail proof verification."""
    from app.crypto.elgamal import generate_keypair, G, scalar_mult, point_add
    from app.crypto.zk.disjunctive import prove_disjunctive_01, verify_disjunctive_01
    from app.crypto.zk.exceptions import ChallengeMismatchError

    keypair = generate_keypair()
    r = 123456789
    c1 = scalar_mult(r, G)
    c2 = scalar_mult(r, keypair.public_key.point)  # vote = 0

    proof = prove_disjunctive_01(
        y_point=keypair.public_key.point,
        a_point=c1,
        b_point=c2,
        v_value=0,
        r_scalar=r,
        domain_prefix="HONEST_DOMAIN",
    )

    # Verifying with altered domain prefix must raise ChallengeMismatchError
    with pytest.raises(ChallengeMismatchError):
        verify_disjunctive_01(
            y_point=keypair.public_key.point,
            a_point=c1,
            b_point=c2,
            proof=proof,
            domain_prefix="ALTERED_TAMPERED_DOMAIN",
        )


def test_altered_transcript_point_rejected():
    """Altering any point bound in Fiat-Shamir transcript must alter derived challenge."""
    from app.crypto.elgamal import G, scalar_mult
    from app.crypto.zk.transcript import Transcript

    t1 = Transcript(domain="TEST")
    t1.append_point("P1", G)
    t1.append_point("P2", scalar_mult(2, G))
    c1 = t1.challenge_scalar("challenge")

    t2 = Transcript(domain="TEST")
    t2.append_point("P1", G)
    t2.append_point("P2", scalar_mult(3, G))  # Altered point
    c2 = t2.challenge_scalar("challenge")

    assert c1 != c2
