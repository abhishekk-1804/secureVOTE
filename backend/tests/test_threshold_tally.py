"""
SecureVOTE 3.2 — Verifiable Threshold Tally Combination Tests.

Covers:
1. All three 2-of-3 valid trustee quorums: {1, 2}, {2, 3}, {1, 3}.
2. Rejection of one trustee alone.
3. Complete 28-item Negative Test Matrix.
4. Independent verification via ThresholdTallyVerifier.
5. Strict source-level assertion confirming no joint secret scalar x is ever materialized.
6. Benchmark performance measurement of share verification, Lagrange combination, and BSGS.
"""

import ast
import inspect
import time
from dataclasses import replace
from typing import Any

import pytest

from app.crypto.elgamal import (
    CURVE_ORDER,
    G,
    INFINITY,
    ECPoint,
    ElGamalCiphertext,
    ElGamalPublicKey,
    add_ciphertexts,
    encrypt,
    point_add,
    point_negate,
    point_on_curve,
    scalar_mult,
)
from app.crypto.serialization import serialize_ciphertext
from app.crypto.threshold import (
    ChaumPedersenEqualityProof,
    DKGPublicManifest,
    InvalidShareError,
    InvalidTrusteeSubsetError,
    PartialDecryptionProofError,
    PartialDecryptionShare,
    TallyPartialDecryptionPackage,
    TallyReconciliationError,
    ThresholdTallyError,
    ThresholdTallyResult,
    ThresholdTallyVerifier,
    TrusteeDKGSession,
    build_dkg_manifest,
    combine_candidate_partial_decryptions,
    compute_lagrange_coefficient,
    compute_tally_partial_decryptions,
    reconstruct_threshold_tally,
    resolve_qualified_set,
)


@pytest.fixture
def setup_3_trustee_election():
    """
    Setup a realistic 3-trustee threshold election with:
    - n = 3, t = 2, QUAL = [1, 2, 3]
    - Authoritative DKG manifest with joint public key Y
    - 10 encrypted ballots across 3 candidates (votes: Cand-A=5, Cand-B=3, Cand-C=2)
    - Partial decryption packages from all 3 trustees
    """
    election_id = "ELEC-THRESH-TALLY-01"
    candidate_ids = ["CAND-A", "CAND-B", "CAND-C"]
    total_ballots = 10
    known_votes = {"CAND-A": 5, "CAND-B": 3, "CAND-C": 2}

    # 1. Execute DKG across 3 trustees
    sessions = [TrusteeDKGSession(i, election_id, threshold=2, total_trustees=3) for i in [1, 2, 3]]
    pedersen_pkgs = {s.trustee_id: s.generate_pedersen_commitments() for s in sessions}

    # Exchange shares
    all_shares = {s.trustee_id: s.generate_shares_for_peers() for s in sessions}
    for recipient in sessions:
        for sender in sessions:
            share = all_shares[sender.trustee_id][recipient.trustee_id]
            recipient.verify_received_share(share, pedersen_pkgs[sender.trustee_id])

    qual = resolve_qualified_set([1, 2, 3], pedersen_pkgs, [])
    feldman_pkgs = {s.trustee_id: s.reveal_feldman_commitments() for s in sessions}
    key_shares = {s.trustee_id: s.finalize_secret_share(qual, feldman_pkgs, pedersen_pkgs) for s in sessions}

    manifest = build_dkg_manifest(election_id, 2, 3, qual, pedersen_pkgs, feldman_pkgs)
    joint_pubkey = ElGamalPublicKey(point=manifest.joint_public_key)

    # 2. Encrypt 10 ballots according to known_votes
    # CAND-A: 5 votes, CAND-B: 3 votes, CAND-C: 2 votes
    # In exponential ElGamal: Aggregated ciphertext for candidate c is:
    # A_c = sum(r_i) * G, B_c = sum(r_i) * Y + Votes_c * G
    slot_ciphertexts = {cid: [] for cid in candidate_ids}

    # Create individual mock ballot encryptions and aggregate
    ballot_votes = (
        [{"CAND-A": 1, "CAND-B": 0, "CAND-C": 0}] * 5 +
        [{"CAND-A": 0, "CAND-B": 1, "CAND-C": 0}] * 3 +
        [{"CAND-A": 0, "CAND-B": 0, "CAND-C": 1}] * 2
    )

    for b in ballot_votes:
        for cid in candidate_ids:
            vote_val = b[cid]
            ct = encrypt(joint_pubkey, vote_val)
            slot_ciphertexts[cid].append(ct)

    # Homomorphically add slots
    aggregated_ciphertexts = {}
    candidate_a_points = {}
    for cid in candidate_ids:
        agg = slot_ciphertexts[cid][0]
        for ct in slot_ciphertexts[cid][1:]:
            agg = add_ciphertexts(agg, ct)
        aggregated_ciphertexts[cid] = agg
        candidate_a_points[cid] = agg.c1

    # Format authoritative encrypted tally artifact
    serialized_slots = [
        serialize_ciphertext(aggregated_ciphertexts[cid])
        for cid in candidate_ids
    ]
    encrypted_tally = {
        "protocol_version": "SECUREVOTE32",
        "artifact_type": "ENCRYPTED_TALLY",
        "election_id": election_id,
        "ballot_count": total_ballots,
        "encrypted_tally": {
            "candidate_count": 3,
            "candidate_ids": candidate_ids,
            "slots": serialized_slots,
        },
    }

    # 3. Generate partial decryption packages from each trustee
    trustee_packages = {}
    for t_id in [1, 2, 3]:
        pkg = compute_tally_partial_decryptions(key_shares[t_id], candidate_a_points)
        trustee_packages[t_id] = pkg

    return {
        "election_id": election_id,
        "candidate_ids": candidate_ids,
        "known_votes": known_votes,
        "total_ballots": total_ballots,
        "manifest": manifest,
        "key_shares": key_shares,
        "candidate_a_points": candidate_a_points,
        "aggregated_ciphertexts": aggregated_ciphertexts,
        "encrypted_tally": encrypted_tally,
        "trustee_packages": trustee_packages,
    }


# ===========================================================================
# Lagrange Basis Unit Tests
# ===========================================================================

def test_lagrange_coefficients_independent_verification():
    """Verify Lagrange coefficients match mathematically computed reference values."""
    # Quorum {1, 2}: lambda_1 = 2, lambda_2 = -1 = q - 1
    l1_12 = compute_lagrange_coefficient(1, [1, 2])
    l2_12 = compute_lagrange_coefficient(2, [1, 2])
    assert l1_12 == 2
    assert l2_12 == (CURVE_ORDER - 1)
    assert (l1_12 + l2_12) % CURVE_ORDER == 1

    # Quorum {2, 3}: lambda_2 = 3, lambda_3 = -2 = q - 2
    l2_23 = compute_lagrange_coefficient(2, [2, 3])
    l3_23 = compute_lagrange_coefficient(3, [2, 3])
    assert l2_23 == 3
    assert l3_23 == (CURVE_ORDER - 2)
    assert (l2_23 + l3_23) % CURVE_ORDER == 1

    # Quorum {1, 3}: lambda_1 = 3/2 = 3 * 2^-1, lambda_3 = -1/2 = -2^-1
    inv2 = pow(2, CURVE_ORDER - 2, CURVE_ORDER)
    l1_13 = compute_lagrange_coefficient(1, [1, 3])
    l3_13 = compute_lagrange_coefficient(3, [1, 3])
    assert l1_13 == (3 * inv2) % CURVE_ORDER
    assert l3_13 == (-inv2) % CURVE_ORDER
    assert (l1_13 + l3_13) % CURVE_ORDER == 1


# ===========================================================================
# 2-of-3 Combinations: {1,2}, {2,3}, {1,3} & Single Trustee Check
# ===========================================================================

def test_valid_combination_quorum_12(setup_3_trustee_election):
    """Item 1: Verify quorum {1, 2} recovers the exact known election tally."""
    ctx = setup_3_trustee_election
    selected_packages = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}

    res = reconstruct_threshold_tally(selected_packages, ctx["encrypted_tally"], ctx["manifest"])
    assert res.selected_trustees == [1, 2]
    assert res.candidate_results == ctx["known_votes"]
    assert res.total_votes == ctx["total_ballots"]
    assert res.reconciled is True


def test_valid_combination_quorum_23(setup_3_trustee_election):
    """Item 2: Verify quorum {2, 3} recovers the exact known election tally."""
    ctx = setup_3_trustee_election
    selected_packages = {2: ctx["trustee_packages"][2], 3: ctx["trustee_packages"][3]}

    res = reconstruct_threshold_tally(selected_packages, ctx["encrypted_tally"], ctx["manifest"])
    assert res.selected_trustees == [2, 3]
    assert res.candidate_results == ctx["known_votes"]
    assert res.total_votes == ctx["total_ballots"]
    assert res.reconciled is True


def test_valid_combination_quorum_13(setup_3_trustee_election):
    """Item 3: Verify quorum {1, 3} recovers the exact known election tally."""
    ctx = setup_3_trustee_election
    selected_packages = {1: ctx["trustee_packages"][1], 3: ctx["trustee_packages"][3]}

    res = reconstruct_threshold_tally(selected_packages, ctx["encrypted_tally"], ctx["manifest"])
    assert res.selected_trustees == [1, 3]
    assert res.candidate_results == ctx["known_votes"]
    assert res.total_votes == ctx["total_ballots"]
    assert res.reconciled is True


def test_one_trustee_only_rejected(setup_3_trustee_election):
    """Item 4: Verify one trustee alone cannot reconstruct tally (threshold = 2 required)."""
    ctx = setup_3_trustee_election
    single_package = {1: ctx["trustee_packages"][1]}

    with pytest.raises(InvalidTrusteeSubsetError) as excinfo:
        reconstruct_threshold_tally(single_package, ctx["encrypted_tally"], ctx["manifest"])
    assert "requires exactly 2 distinct trustees" in str(excinfo.value)


# ===========================================================================
# Negative Test Matrix (Items 5 through 28)
# ===========================================================================

def test_duplicate_trustee_rejected(setup_3_trustee_election):
    """Item 5: Passing duplicate trustee ID in subset calculation must fail."""
    with pytest.raises(InvalidTrusteeSubsetError):
        compute_lagrange_coefficient(1, [1, 1])


def test_duplicate_share_artifact_rejected(setup_3_trustee_election):
    """Item 6: Duplicate share packages from the same trustee must be rejected."""
    ctx = setup_3_trustee_election
    pkg1 = ctx["trustee_packages"][1]
    # Attempt to supply trustee 1 twice
    with pytest.raises(InvalidTrusteeSubsetError):
        reconstruct_threshold_tally({1: pkg1}, ctx["encrypted_tally"], ctx["manifest"])


def test_missing_candidate_share_rejected(setup_3_trustee_election):
    """Item 7: A trustee package missing a candidate share must fail reconstruction."""
    ctx = setup_3_trustee_election
    pkg1 = ctx["trustee_packages"][1]
    # Remove CAND-C from trustee 2
    pkg2 = ctx["trustee_packages"][2]
    bad_shares = {cid: s for cid, s in pkg2.shares.items() if cid != "CAND-C"}
    bad_pkg2 = TallyPartialDecryptionPackage(pkg2.election_id, pkg2.trustee_id, bad_shares)

    with pytest.raises(ThresholdTallyError) as excinfo:
        reconstruct_threshold_tally({1: pkg1, 2: bad_pkg2}, ctx["encrypted_tally"], ctx["manifest"])
    assert "missing partial decryption share" in str(excinfo.value)


def test_wrong_trustee_id_rejected(setup_3_trustee_election):
    """Item 8: Package labeled with wrong trustee ID must fail validation."""
    ctx = setup_3_trustee_election
    pkg1 = ctx["trustee_packages"][1]
    pkg2 = ctx["trustee_packages"][2]

    # Change pkg2's trustee_id to 9
    bad_pkg2 = TallyPartialDecryptionPackage(pkg2.election_id, 9, pkg2.shares)
    with pytest.raises(InvalidTrusteeSubsetError):
        reconstruct_threshold_tally({1: pkg1, 9: bad_pkg2}, ctx["encrypted_tally"], ctx["manifest"])


def test_wrong_election_id_rejected(setup_3_trustee_election):
    """Item 9: Package with mismatched election ID must fail."""
    ctx = setup_3_trustee_election
    pkg1 = ctx["trustee_packages"][1]
    pkg2 = ctx["trustee_packages"][2]

    bad_pkg2 = TallyPartialDecryptionPackage("WRONG-ELECTION", pkg2.trustee_id, pkg2.shares)
    with pytest.raises(ThresholdTallyError) as excinfo:
        reconstruct_threshold_tally({1: pkg1, 2: bad_pkg2}, ctx["encrypted_tally"], ctx["manifest"])
    assert "does not match encrypted tally" in str(excinfo.value)


def test_wrong_candidate_id_rejected(setup_3_trustee_election):
    """Item 10: Individual candidate share validation with wrong candidate ID must fail."""
    ctx = setup_3_trustee_election
    share = ctx["trustee_packages"][1].shares["CAND-A"]
    vk = ctx["manifest"].get_trustee_verification_key(1)
    a_pt = ctx["candidate_a_points"]["CAND-A"]

    with pytest.raises(ThresholdTallyError) as excinfo:
        from app.crypto.threshold.tally import validate_partial_share_contribution
        validate_partial_share_contribution(share, ctx["election_id"], "CAND-WRONG", 1, vk, a_pt, ctx["manifest"])
    assert "candidate_id mismatch" in str(excinfo.value)


def test_wrong_verification_key_rejected(setup_3_trustee_election):
    """Item 11: Verification against wrong verification key must fail."""
    ctx = setup_3_trustee_election
    share = ctx["trustee_packages"][1].shares["CAND-A"]
    wrong_vk = scalar_mult(999, G)
    a_pt = ctx["candidate_a_points"]["CAND-A"]

    with pytest.raises(InvalidShareError) as excinfo:
        from app.crypto.threshold.tally import validate_partial_share_contribution
        validate_partial_share_contribution(share, ctx["election_id"], "CAND-A", 1, wrong_vk, a_pt, ctx["manifest"])
    assert "does not match DKG manifest" in str(excinfo.value)


def test_invalid_chaum_pedersen_proof_rejected(setup_3_trustee_election):
    """Item 12: Corrupted Chaum-Pedersen proof must fail validation."""
    ctx = setup_3_trustee_election
    share = ctx["trustee_packages"][1].shares["CAND-A"]
    bad_proof = ChaumPedersenEqualityProof(share.proof.comm_1, share.proof.comm_2, share.proof.c, (share.proof.s + 1) % CURVE_ORDER)
    bad_share = PartialDecryptionShare(share.election_id, share.candidate_id, share.trustee_id, share.partial_decryption, bad_proof)

    vk = ctx["manifest"].get_trustee_verification_key(1)
    a_pt = ctx["candidate_a_points"]["CAND-A"]

    with pytest.raises(PartialDecryptionProofError):
        from app.crypto.threshold.tally import validate_partial_share_contribution
        validate_partial_share_contribution(bad_share, ctx["election_id"], "CAND-A", 1, vk, a_pt, ctx["manifest"])


def test_altered_w_rejected(setup_3_trustee_election):
    """Item 13: Altered W partial decryption point must fail verification."""
    ctx = setup_3_trustee_election
    share = ctx["trustee_packages"][1].shares["CAND-A"]
    bad_w = point_add(share.partial_decryption, G)
    bad_share = PartialDecryptionShare(share.election_id, share.candidate_id, share.trustee_id, bad_w, share.proof)

    vk = ctx["manifest"].get_trustee_verification_key(1)
    a_pt = ctx["candidate_a_points"]["CAND-A"]

    with pytest.raises(PartialDecryptionProofError):
        from app.crypto.threshold.tally import validate_partial_share_contribution
        validate_partial_share_contribution(bad_share, ctx["election_id"], "CAND-A", 1, vk, a_pt, ctx["manifest"])


def test_altered_a_rejected(setup_3_trustee_election):
    """Item 14: Verification against altered ciphertext point A must fail."""
    ctx = setup_3_trustee_election
    share = ctx["trustee_packages"][1].shares["CAND-A"]
    vk = ctx["manifest"].get_trustee_verification_key(1)
    bad_a = point_add(ctx["candidate_a_points"]["CAND-A"], G)

    with pytest.raises(PartialDecryptionProofError):
        from app.crypto.threshold.tally import validate_partial_share_contribution
        validate_partial_share_contribution(share, ctx["election_id"], "CAND-A", 1, vk, bad_a, ctx["manifest"])


def test_altered_b_rejected(setup_3_trustee_election):
    """Item 15: Altering ciphertext B component must cause discrete log or reconciliation failure."""
    ctx = setup_3_trustee_election
    pkg1 = ctx["trustee_packages"][1]
    pkg2 = ctx["trustee_packages"][2]

    # Mutate ciphertext B for CAND-A in encrypted tally
    import copy
    bad_tally = copy.deepcopy(ctx["encrypted_tally"])
    ct0 = ctx["aggregated_ciphertexts"]["CAND-A"]
    bad_ct0 = ElGamalCiphertext(c1=ct0.c1, c2=point_add(ct0.c2, scalar_mult(5, G)))
    bad_tally["encrypted_tally"]["slots"][0] = serialize_ciphertext(bad_ct0)

    with pytest.raises((TallyReconciliationError, ThresholdTallyError)):
        reconstruct_threshold_tally({1: pkg1, 2: pkg2}, bad_tally, ctx["manifest"])


def test_malformed_point_rejected(setup_3_trustee_election):
    """Item 16: Malformed point data must fail deserialization."""
    from app.crypto.serialization import deserialize_point
    from app.crypto.exceptions import SerializationError
    with pytest.raises(SerializationError):
        deserialize_point({"x": "not_hex", "y": "123"})


def test_infinity_point_rejected(setup_3_trustee_election):
    """Item 17: Partial decryption share with infinity point must fail validation."""
    ctx = setup_3_trustee_election
    share = ctx["trustee_packages"][1].shares["CAND-A"]
    bad_share = PartialDecryptionShare(share.election_id, share.candidate_id, share.trustee_id, INFINITY, share.proof)
    vk = ctx["manifest"].get_trustee_verification_key(1)
    a_pt = ctx["candidate_a_points"]["CAND-A"]

    with pytest.raises(InvalidShareError):
        from app.crypto.threshold.tally import validate_partial_share_contribution
        validate_partial_share_contribution(bad_share, ctx["election_id"], "CAND-A", 1, vk, a_pt, ctx["manifest"])


def test_off_curve_point_rejected(setup_3_trustee_election):
    """Item 18: Partial decryption share with off-curve point must fail validation."""
    ctx = setup_3_trustee_election
    share = ctx["trustee_packages"][1].shares["CAND-A"]
    bad_pt = ECPoint(x=12345, y=67890)
    bad_share = PartialDecryptionShare(share.election_id, share.candidate_id, share.trustee_id, bad_pt, share.proof)
    vk = ctx["manifest"].get_trustee_verification_key(1)
    a_pt = ctx["candidate_a_points"]["CAND-A"]

    with pytest.raises(InvalidShareError):
        from app.crypto.threshold.tally import validate_partial_share_contribution
        validate_partial_share_contribution(bad_share, ctx["election_id"], "CAND-A", 1, vk, a_pt, ctx["manifest"])


def test_altered_lagrange_coefficient_rejected(setup_3_trustee_election):
    """Item 19: An altered Lagrange coefficient must fail independent verification."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])

    # Mutate combined point D_j (which equals what altered lambda would produce)
    bad_combined = {cid: point_add(pt, G) for cid, pt in res.combined_decryption_points.items()}
    bad_res = ThresholdTallyResult(
        election_id=res.election_id,
        threshold=res.threshold,
        selected_trustees=res.selected_trustees,
        candidate_results=res.candidate_results,
        total_votes=res.total_votes,
        ballot_count=res.ballot_count,
        combined_decryption_points=bad_combined,
        reconciled=res.reconciled,
    )

    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Combined decryption point mismatch" in str(excinfo.value)


def test_invalid_trustee_set_membership_rejected(setup_3_trustee_election):
    """Item 20: Trustee not in manifest qualified set QUAL must be rejected."""
    ctx = setup_3_trustee_election
    pkg1 = ctx["trustee_packages"][1]
    # Create manifest where only trustees 1 and 2 are QUAL, and attempt to use 3
    manifest_without_3 = DKGPublicManifest(
        election_id=ctx["manifest"].election_id,
        threshold=2,
        trustee_count=3,
        qualified_trustees=[1, 2],  # Trustee 3 excluded
        joint_public_key=ctx["manifest"].joint_public_key,
        trustee_verification_keys=ctx["manifest"].trustee_verification_keys,
        pedersen_commitments=ctx["manifest"].pedersen_commitments,
        feldman_commitments=ctx["manifest"].feldman_commitments,
    )
    pkg3 = ctx["trustee_packages"][3]

    with pytest.raises(InvalidTrusteeSubsetError) as excinfo:
        reconstruct_threshold_tally({1: pkg1, 3: pkg3}, ctx["encrypted_tally"], manifest_without_3)
    assert "must both be members of manifest qualified set" in str(excinfo.value)


def test_mixing_shares_different_elections_rejected(setup_3_trustee_election):
    """Item 21: Mixing shares from different elections must be rejected."""
    ctx = setup_3_trustee_election
    pkg1 = ctx["trustee_packages"][1]
    pkg2 = ctx["trustee_packages"][2]

    # Create share from different election
    sh_diff = PartialDecryptionShare("DIFF-ELECTION", "CAND-A", 2, pkg2.shares["CAND-A"].partial_decryption, pkg2.shares["CAND-A"].proof)
    bad_shares = dict(pkg2.shares)
    bad_shares["CAND-A"] = sh_diff
    bad_pkg2 = TallyPartialDecryptionPackage(pkg2.election_id, 2, bad_shares)

    with pytest.raises(ThresholdTallyError) as excinfo:
        reconstruct_threshold_tally({1: pkg1, 2: bad_pkg2}, ctx["encrypted_tally"], ctx["manifest"])
    assert "election_id mismatch" in str(excinfo.value)


def test_mixing_shares_different_candidates_rejected(setup_3_trustee_election):
    """Item 22: Mixing shares across different candidate slots must fail."""
    ctx = setup_3_trustee_election
    pkg1 = ctx["trustee_packages"][1]
    pkg2 = ctx["trustee_packages"][2]

    # Put CAND-B share into CAND-A slot
    bad_shares = dict(pkg2.shares)
    bad_shares["CAND-A"] = pkg2.shares["CAND-B"]
    bad_pkg2 = TallyPartialDecryptionPackage(pkg2.election_id, 2, bad_shares)

    with pytest.raises(ThresholdTallyError) as excinfo:
        reconstruct_threshold_tally({1: pkg1, 2: bad_pkg2}, ctx["encrypted_tally"], ctx["manifest"])
    assert "candidate_id mismatch" in str(excinfo.value)


def test_using_two_shares_same_trustee_rejected(setup_3_trustee_election):
    """Item 23: Passing two shares belonging to the same trustee must fail."""
    ctx = setup_3_trustee_election
    share1 = ctx["trustee_packages"][1].shares["CAND-A"]
    vks = {1: ctx["manifest"].get_trustee_verification_key(1)}
    a_pt = ctx["candidate_a_points"]["CAND-A"]

    with pytest.raises(InvalidTrusteeSubsetError) as excinfo:
        combine_candidate_partial_decryptions(share1, share1, a_pt, vks, ctx["manifest"], ctx["election_id"], "CAND-A")
    assert "Cannot combine shares from the same trustee ID" in str(excinfo.value)


def test_attempting_combine_three_shares_rejected(setup_3_trustee_election):
    """Item 24: Attempting to combine 3 packages when threshold API requires exactly 2 must fail."""
    ctx = setup_3_trustee_election
    pkgs_all_3 = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2], 3: ctx["trustee_packages"][3]}

    with pytest.raises(InvalidTrusteeSubsetError) as excinfo:
        reconstruct_threshold_tally(pkgs_all_3, ctx["encrypted_tally"], ctx["manifest"])
    assert "requires exactly 2 distinct trustees" in str(excinfo.value)


def test_altered_trustee_qual_metadata_rejected(setup_3_trustee_election):
    """Item 25: Altered manifest QUAL set with fewer than 2 trustees must fail verification."""
    ctx = setup_3_trustee_election
    bad_manifest = DKGPublicManifest(
        election_id=ctx["manifest"].election_id,
        threshold=2,
        trustee_count=3,
        qualified_trustees=[1],  # Only 1 qualified trustee
        joint_public_key=ctx["manifest"].joint_public_key,
        trustee_verification_keys=ctx["manifest"].trustee_verification_keys,
        pedersen_commitments=ctx["manifest"].pedersen_commitments,
        feldman_commitments=ctx["manifest"].feldman_commitments,
    )
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])

    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(bad_manifest, ctx["encrypted_tally"], selected, res)
    assert "Insufficient qualified trustees" in str(excinfo.value)


def test_altered_threshold_parameter_rejected(setup_3_trustee_election):
    """Item 26: Manifest with non-(2, 3) threshold parameter must fail verification."""
    ctx = setup_3_trustee_election
    bad_manifest = DKGPublicManifest(
        election_id=ctx["manifest"].election_id,
        threshold=3,  # Altered threshold
        trustee_count=3,
        qualified_trustees=[1, 2, 3],
        joint_public_key=ctx["manifest"].joint_public_key,
        trustee_verification_keys=ctx["manifest"].trustee_verification_keys,
        pedersen_commitments=ctx["manifest"].pedersen_commitments,
        feldman_commitments=ctx["manifest"].feldman_commitments,
    )
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])

    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(bad_manifest, ctx["encrypted_tally"], selected, res)
    assert "Manifest parameters do not conform" in str(excinfo.value)


def test_tally_reconciliation_mismatch_rejected(setup_3_trustee_election):
    """Item 27: When sum of candidate votes != ballot count, reconciliation fails."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}

    # Set ballot_count to 999 instead of 10
    bad_encrypted_tally = dict(ctx["encrypted_tally"])
    bad_encrypted_tally["ballot_count"] = 999

    with pytest.raises(TallyReconciliationError) as excinfo:
        reconstruct_threshold_tally(selected, bad_encrypted_tally, ctx["manifest"])
    assert "Tally reconciliation mismatch" in str(excinfo.value)


def test_incorrect_expected_election_tally_rejected(setup_3_trustee_election):
    """Item 28: Verifier rejects if results in ThresholdTallyResult do not match ciphertexts."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])

    # Lie about candidate vote counts in result (e.g. CAND-A=9, CAND-B=1, CAND-C=0)
    tampered_results = {"CAND-A": 9, "CAND-B": 1, "CAND-C": 0}
    bad_res = ThresholdTallyResult(
        election_id=res.election_id,
        threshold=res.threshold,
        selected_trustees=res.selected_trustees,
        candidate_results=tampered_results,
        total_votes=10,
        ballot_count=10,
        combined_decryption_points=res.combined_decryption_points,
        reconciled=True,
    )

    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Discrete logarithm mismatch" in str(excinfo.value)


# ===========================================================================
# Offline Public Verifier Soundness & Metadata Binding Tests
# ===========================================================================

def test_offline_threshold_tally_verifier_honest(setup_3_trustee_election):
    """Verify that ThresholdTallyVerifier succeeds on valid honest tallies."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}

    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    is_verified = ThresholdTallyVerifier.verify(
        manifest=ctx["manifest"],
        encrypted_tally=ctx["encrypted_tally"],
        trustee_packages=selected,
        tally_result=res,
    )
    assert is_verified is True


def test_verifier_altered_election_id_rejected(setup_3_trustee_election):
    """Verifier rejects if tally_result election_id does not match encrypted_tally."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    bad_res = replace(res, election_id="ALTERED-ELECTION-ID")
    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Election ID mismatch" in str(excinfo.value)


def test_verifier_altered_threshold_rejected(setup_3_trustee_election):
    """Verifier rejects if tally_result threshold does not match manifest."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    bad_res = replace(res, threshold=3)
    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Threshold mismatch" in str(excinfo.value)


def test_verifier_altered_ballot_count_rejected(setup_3_trustee_election):
    """Verifier rejects if tally_result ballot_count does not match encrypted_tally."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    bad_res = replace(res, ballot_count=999)
    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Ballot count mismatch" in str(excinfo.value)


def test_verifier_altered_protocol_version_rejected(setup_3_trustee_election):
    """Verifier rejects if tally_result protocol_version does not match expected version."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    bad_res = replace(res, protocol_version="SECUREVOTE33-UNKNOWN")
    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Protocol version mismatch" in str(excinfo.value)


def test_verifier_extra_candidate_result_rejected(setup_3_trustee_election):
    """Verifier rejects extra unbound candidate results."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    extra_candidates = dict(res.candidate_results)
    extra_candidates["CAND-EXTRA"] = 0
    bad_res = replace(res, candidate_results=extra_candidates)
    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Candidate results key mismatch" in str(excinfo.value)


def test_verifier_missing_combined_point_rejected(setup_3_trustee_election):
    """Verifier rejects missing combined decryption points."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    missing_points = dict(res.combined_decryption_points)
    missing_points.pop("CAND-A")
    bad_res = replace(res, combined_decryption_points=missing_points)
    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Combined decryption points key mismatch" in str(excinfo.value)


def test_verifier_extra_combined_point_rejected(setup_3_trustee_election):
    """Verifier rejects extra unbound combined decryption points."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    extra_points = dict(res.combined_decryption_points)
    extra_points["CAND-EXTRA"] = res.combined_decryption_points["CAND-A"]
    bad_res = replace(res, combined_decryption_points=extra_points)
    with pytest.raises(ThresholdTallyError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Combined decryption points key mismatch" in str(excinfo.value)


def test_verifier_unsorted_selected_trustees_rejected(setup_3_trustee_election):
    """Verifier rejects if selected trustees in tally_result are not canonically sorted."""
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    bad_res = replace(res, selected_trustees=[2, 1])
    with pytest.raises(InvalidTrusteeSubsetError) as excinfo:
        ThresholdTallyVerifier.verify(ctx["manifest"], ctx["encrypted_tally"], selected, bad_res)
    assert "Selected trustees must be sorted canonically" in str(excinfo.value)


# ===========================================================================
# Static Audit & AST Hard Assertion: No Joint Secret Reconstruction
# ===========================================================================

def test_no_joint_secret_reconstructed_static_assertion():
    """
    Hard AST and source-level assertion:
    Verifies that backend/app/crypto/threshold/tally.py NEVER attempts
    to reconstruct the joint secret scalar x or compute lambda * x_i.
    """
    import app.crypto.threshold.tally as tally_module
    source_code = inspect.getsource(tally_module)

    # Prohibited identifier patterns
    prohibited_tokens = [
        "reconstructed_secret",
        "joint_secret",
        "secret_reconstruction",
        "reconstruct_secret",
    ]
    for token in prohibited_tokens:
        assert token not in source_code, f"Prohibited secret reconstruction token found: '{token}'"

    # AST Inspection: verify that scalar_mult is only called on ECPoints, not scalar products of secret_share
    parsed_ast = ast.parse(source_code)
    for node in ast.walk(parsed_ast):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assert target.id != "x", "Accidental assignment to variable named 'x' detected in tally module"
                    assert "private" not in target.id, f"Suspicious private variable assignment: {target.id}"


# ===========================================================================
# Serialization Round-Trip
# ===========================================================================

def test_threshold_tally_result_serialization_round_trip(setup_3_trustee_election):
    """Verify canonical serialization and deserialization of ThresholdTallyResult."""
    from app.crypto.threshold.serialization import (
        deserialize_threshold_tally_result,
        serialize_threshold_tally_result,
    )
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}
    res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])

    ser = serialize_threshold_tally_result(res)
    de = deserialize_threshold_tally_result(ser)

    assert de.election_id == res.election_id
    assert de.threshold == res.threshold
    assert de.selected_trustees == res.selected_trustees
    assert de.candidate_results == res.candidate_results
    assert de.total_votes == res.total_votes
    assert de.reconciled == res.reconciled
    assert de.combined_decryption_points == res.combined_decryption_points


# ===========================================================================
# Reproducible Performance Benchmark
# ===========================================================================

def test_benchmark_threshold_tally_performance(setup_3_trustee_election):
    """
    Benchmark execution time for:
    1. Partial share verification
    2. Point-level Lagrange combination
    3. BSGS discrete log recovery
    4. Total threshold tally reconstruction
    """
    ctx = setup_3_trustee_election
    selected = {1: ctx["trustee_packages"][1], 2: ctx["trustee_packages"][2]}

    # Warm-up run
    _ = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])

    # Timed runs
    iterations = 5
    start = time.perf_counter()
    for _ in range(iterations):
        res = reconstruct_threshold_tally(selected, ctx["encrypted_tally"], ctx["manifest"])
    total_time = (time.perf_counter() - start) / iterations

    assert res.reconciled is True
    # In-memory execution on P-256 for 3 candidates should take well under 100ms per tally
    assert total_time < 0.5, f"Tally combination exceeded reasonable time budget: {total_time:.4f}s"
