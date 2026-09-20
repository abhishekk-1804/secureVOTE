"""
Tests for Standalone V3 Election Verifier and Adversarial Mutation Detection.

Validates the 10-checkpoint verifier against:
1. Happy path: valid v3 election package with full verification
2. Attack 1: Mutated ciphertext in a ballot slot
3. Attack 2: Mutated ballot commitment
4. Attack 3: Mutated public key
5. Attack 4: Swapped/mutated candidate mapping
6. Attack 5: Mutated aggregate encrypted tally
7. Attack 6: Mutated artifact hash
8. Attack 7: Mutated election configuration
9. Attack 8: Protocol version downgrade / spoofing
10. Attack 9: Decrypted tally reconciliation drift
11. Attack 10: Missing/malformed ballot artifact metadata
"""

import copy
import pytest

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encrypt_ballot
from app.crypto.keys import compute_key_fingerprint, generate_keypair, serialize_public_key
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally
from standalone_verifier.v3_verifier import StandaloneV3ElectionVerifier


@pytest.fixture
def valid_package():
    """Build a complete, mathematically valid v3 election package."""
    keypair = generate_keypair()
    pub_data = serialize_public_key(keypair.public_key)
    election_id = "V3-VERIFY-TEST-001"
    candidates = ["CAND-1", "CAND-2", "CAND-3", "NOTA"]

    # Generate 6 ballots: votes = [0, 1, 0, 2, 3, 0]
    votes = [0, 1, 0, 2, 3, 0]
    ballots = []
    for v in votes:
        b = encrypt_ballot(
            public_key=keypair.public_key,
            candidate_index=v,
            candidate_count=len(candidates),
            election_id=election_id,
            candidate_ids=candidates,
        )
        ballots.append(b)

    key_fp = compute_key_fingerprint(keypair.public_key)
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


def test_standalone_verifier_happy_path(valid_package):
    """Happy path: All 10 checkpoints must pass."""
    pkg, keypair = valid_package
    result = StandaloneV3ElectionVerifier.verify_package(pkg, keypair)
    assert result["verified"] is True
    assert result["checkpoints_passed"] == result["checkpoints_total"]
    for cp in result["checkpoints"]:
        assert cp["status"] == "PASSED", f"Checkpoint {cp['checkpoint']} failed: {cp['message']}"


def test_attack_mutated_ciphertext(valid_package):
    """Attack 1: Tampering with a single ciphertext slot must fail verification."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    # Mutate C1 coordinate of slot 0 in ballot 0
    pkg_tampered["ballots"][0]["encrypted_vote"]["slots"][0]["c1"]["x"] = "11" * 32
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False
    failed = [c["checkpoint"] for c in result["checkpoints"] if c["status"] == "FAILED"]
    assert any("commitment" in f or "aggregation" in f or "curve" in f for f in failed)


def test_attack_mutated_commitment(valid_package):
    """Attack 2: Forged ballot commitment must be detected."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    pkg_tampered["ballots"][1]["commitment"] = "00" * 32
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False
    failed = [c["checkpoint"] for c in result["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_6_ballot_commitments" in failed


def test_attack_mutated_public_key(valid_package):
    """Attack 3: Mutating public key must fail key validation and aggregation."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    other_key = generate_keypair()
    pkg_tampered["public_key"] = serialize_public_key(other_key.public_key)
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False


def test_attack_mutated_candidate_mapping(valid_package):
    """Attack 4: Swapping candidate IDs in a ballot must fail commitment check."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    cids = pkg_tampered["ballots"][0]["encrypted_vote"]["candidate_ids"]
    cids[0], cids[1] = cids[1], cids[0]
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False
    failed = [c["checkpoint"] for c in result["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_6_ballot_commitments" in failed


def test_attack_mutated_encrypted_tally(valid_package):
    """Attack 5: Altered aggregate tally ciphertext must not match independent aggregation."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    # Mutate aggregate slot 0 C2 coordinate
    pkg_tampered["encrypted_tally"]["encrypted_tally"]["slots"][0]["c2"]["x"] = "aa" * 32
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False
    failed = [c["checkpoint"] for c in result["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_8_homomorphic_aggregation" in failed


def test_attack_mutated_artifact_hash(valid_package):
    """Attack 6: Altered ballot artifact hash must fail hash recomputation."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    pkg_tampered["ballots"][2]["artifact_hash"] = "deadbeef" * 8
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False
    failed = [c["checkpoint"] for c in result["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_7_ballot_hashes" in failed


def test_attack_mutated_election_config(valid_package):
    """Attack 7: Invalid candidate count (< 2) must fail config checkpoint."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    pkg_tampered["candidates"] = ["SOLO_CANDIDATE"]
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False
    failed = [c["checkpoint"] for c in result["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_3_election_config" in failed


def test_attack_protocol_downgrade(valid_package):
    """Attack 8: Protocol version downgrade must fail immediately."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    pkg_tampered["protocol_version"] = "SECUREVOTE2"
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False
    assert result["checkpoints"][0]["status"] == "FAILED"


def test_attack_reconciliation_drift(valid_package):
    """Attack 9: Fabricated candidate totals that drift from ballot count must fail."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    pkg_tampered["decrypted_tally"]["candidate_tallies"]["CAND-1"] += 1  # Add fake vote
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False
    failed = [c["checkpoint"] for c in result["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_10_reconciliation" in failed


def test_attack_missing_metadata(valid_package):
    """Attack 10: Stripping commitment field from ballot must fail structural checkpoint."""
    pkg, keypair = valid_package
    pkg_tampered = copy.deepcopy(pkg)
    del pkg_tampered["ballots"][0]["commitment"]
    result = StandaloneV3ElectionVerifier.verify_package(pkg_tampered)
    assert result["verified"] is False
    failed = [c["checkpoint"] for c in result["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_4_ballot_structure" in failed
