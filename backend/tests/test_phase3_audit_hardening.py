"""
Phase 3 Audit Hardening Test Suite for SecureVOTE Evidence Bundles.

Covers:
1. Checkpoint 15 strict tally reconciliation:
   - Negative tallies rejection
   - Unknown candidate rejection
   - Missing candidate rejection
   - Non-integer / float / bool tally rejection
   - Valid centralized tally passing
2. Verification status semantics:
   - Unsigned bundle CP4 status is NOT_APPLICABLE
   - Centralized threshold checks (CP12, CP13, CP14) status is NOT_APPLICABLE
   - NOT_APPLICABLE is not counted as PASSED
3. Archive security:
   - Duplicate ZIP member rejection (entry shadowing attack defense)
4. Generalized threshold verification:
   - 2-of-3 threshold verification still passes
   - 3-of-5 threshold verification passes
   - Insufficient threshold trustees fails
   - Duplicate selected trustees fails
   - Invalid / unqualified trustee fails
"""

import copy
import io
import json
import os
import shutil
import tempfile
import zipfile
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encrypt_ballot
from app.crypto.canonical import canonical_json
from app.crypto.elgamal import (
    INFINITY,
    ECPoint,
    ElGamalCiphertext,
    ElGamalPublicKey,
    generate_keypair,
    point_add,
    scalar_mult,
)
from app.crypto.keys import compute_key_fingerprint, serialize_public_key
from app.crypto.serialization import serialize_ciphertext
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally
from app.crypto.threshold import (
    ThresholdTallyResult,
    TrusteeDKGSession,
    build_dkg_manifest,
    compute_lagrange_coefficient,
    compute_tally_partial_decryptions,
    reconstruct_threshold_tally,
    resolve_qualified_set,
)
from app.crypto.threshold.serialization import (
    serialize_dkg_manifest,
    serialize_tally_partial_decryption_package,
    serialize_threshold_tally_result,
)
from standalone_verifier.bundle import (
    BundleVerificationStatus,
    compute_file_sha256,
    compute_manifest_hash,
)
from standalone_verifier.bundle_export import export_bundle
from standalone_verifier.bundle_verifier import BundleReader, StandaloneBundleVerifier


# -----------------------------------------------------------------------------
# Fixtures & Helpers
# -----------------------------------------------------------------------------

@pytest.fixture
def test_signing_key():
    """Generate Ed25519 keypair for test bundle signing."""
    priv = ed25519.Ed25519PrivateKey.generate()
    priv_hex = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()
    pub_hex = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    return priv_hex, pub_hex


@pytest.fixture
def centralized_package():
    """Build a standard 4-ballot centralized election package."""
    keypair = generate_keypair()
    pub_data = serialize_public_key(keypair.public_key)
    election_id = "P3-HARDEN-ELEC-CENTRAL"
    candidates = ["CAND-A", "CAND-B", "CAND-C"]
    candidate_count = len(candidates)

    votes = [0, 1, 0, 2]  # A=2, B=1, C=1
    ballots = []
    for v_idx in votes:
        b = encrypt_ballot(
            public_key=keypair.public_key,
            candidate_index=v_idx,
            candidate_count=candidate_count,
            election_id=election_id,
            candidate_ids=candidates,
            with_zkp=True,
        )
        ballots.append(b)

    key_fp = compute_key_fingerprint(keypair.public_key)
    encrypted_tally = aggregate_encrypted_ballots(ballots, election_id, key_fp)
    decrypted_tally = decrypt_tally(keypair, encrypted_tally)

    return {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "public_key": pub_data,
        "candidates": candidates,
        "ballots": ballots,
        "encrypted_tally": encrypted_tally,
        "decrypted_tally": decrypted_tally,
    }


def make_threshold_package(threshold: int, total_trustees: int, election_id: str, selected_ids: list[int] = None):
    """Helper to generate an arbitrary t-of-n threshold election package."""
    if selected_ids is None:
        selected_ids = list(range(1, threshold + 1))

    candidates = ["CAND-X", "CAND-Y"]
    candidate_count = len(candidates)

    sessions = [
        TrusteeDKGSession(i, election_id, threshold=threshold, total_trustees=total_trustees)
        for i in range(1, total_trustees + 1)
    ]
    pedersen_pkgs = {s.trustee_id: s.generate_pedersen_commitments() for s in sessions}
    all_shares = {s.trustee_id: s.generate_shares_for_peers() for s in sessions}

    for recipient in sessions:
        for sender in sessions:
            share = all_shares[sender.trustee_id][recipient.trustee_id]
            recipient.verify_received_share(share, pedersen_pkgs[sender.trustee_id])

    qual = resolve_qualified_set(list(range(1, total_trustees + 1)), pedersen_pkgs, [])
    feldman_pkgs = {s.trustee_id: s.reveal_feldman_commitments() for s in sessions}
    key_shares = {
        s.trustee_id: s.finalize_secret_share(qual, feldman_pkgs, pedersen_pkgs)
        for s in sessions
    }

    manifest = build_dkg_manifest(election_id, threshold, total_trustees, qual, pedersen_pkgs, feldman_pkgs)
    joint_pubkey = ElGamalPublicKey(point=manifest.joint_public_key)
    pub_data = serialize_public_key(joint_pubkey)

    # 3 ballots: votes = [X, Y, X] -> X=2, Y=1
    ballots = []
    for v_idx in [0, 1, 0]:
        b = encrypt_ballot(
            public_key=joint_pubkey,
            candidate_index=v_idx,
            candidate_count=candidate_count,
            election_id=election_id,
            candidate_ids=candidates,
            with_zkp=True,
        )
        ballots.append(b)

    key_fp = compute_key_fingerprint(joint_pubkey)
    encrypted_tally = aggregate_encrypted_ballots(ballots, election_id, key_fp)

    tally_slots = encrypted_tally["encrypted_tally"]["slots"]
    candidate_a_points = {
        cid: ECPoint(int(tally_slots[j]["c1"]["x"], 16), int(tally_slots[j]["c1"]["y"], 16))
        for j, cid in enumerate(candidates)
    }

    trustee_packages = {
        t_id: compute_tally_partial_decryptions(key_shares[t_id], candidate_a_points)
        for t_id in selected_ids
    }

    lambdas = {t_id: compute_lagrange_coefficient(t_id, selected_ids) for t_id in selected_ids}
    combined_d_points = {}
    candidate_results = {"CAND-X": 2, "CAND-Y": 1}
    for cid in candidates:
        d_j = INFINITY
        for t_id in selected_ids:
            w_i = trustee_packages[t_id].shares[cid].partial_decryption
            d_j = point_add(d_j, scalar_mult(lambdas[t_id], w_i))
        combined_d_points[cid] = d_j

    tally_result = ThresholdTallyResult(
        election_id=election_id,
        threshold=threshold,
        selected_trustees=sorted(selected_ids),
        candidate_results=candidate_results,
        total_votes=sum(candidate_results.values()),
        ballot_count=len(ballots),
        combined_decryption_points=combined_d_points,
        reconciled=True,
    )

    threshold_tally_dict = {
        "manifest": serialize_dkg_manifest(manifest),
        "trustee_packages": {str(k): serialize_tally_partial_decryption_package(v) for k, v in trustee_packages.items()},
        "tally_result": serialize_threshold_tally_result(tally_result),
    }

    return {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "public_key": pub_data,
        "candidates": candidates,
        "ballots": ballots,
        "encrypted_tally": encrypted_tally,
        "decrypted_tally": {
            "protocol_version": PROTOCOL_VERSION,
            "artifact_type": "DECRYPTED_TALLY",
            "election_id": election_id,
            "candidate_tallies": tally_result.candidate_results,
            "total_ballots": tally_result.total_votes,
            "ballot_count": len(ballots),
            "reconciliation_status": "BALANCED",
            "key_fingerprint": key_fp,
        },
        "threshold_tally": threshold_tally_dict,
    }


def patch_bundle_artifact(bundle_dir: str, rel_path: str, new_content: dict) -> None:
    """Helper to patch a bundle JSON artifact and update manifest.json cleanly."""
    new_bytes = canonical_json(new_content).encode("utf-8")
    full_path = os.path.join(bundle_dir, rel_path)
    with open(full_path, "wb") as f:
        f.write(new_bytes)

    with open(os.path.join(bundle_dir, "manifest.json"), "r") as f:
        m = json.load(f)

    for item in m["artifact_inventory"]:
        if item["path"] == rel_path:
            item["sha256"] = compute_file_sha256(new_bytes)
            item["size_bytes"] = len(new_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(bundle_dir, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))


# -----------------------------------------------------------------------------
# Test 1: Checkpoint 15 Rejects Negative Tallies
# -----------------------------------------------------------------------------

def test_checkpoint_15_rejects_negative_tallies(centralized_package, tmp_path):
    """Reject candidate tallies containing negative numbers, even if sum equals ballot count."""
    b_dir = str(tmp_path / "neg_tally_bundle")
    export_bundle(package=centralized_package, output_dir=b_dir)

    # Vulnerable input: sum equals 4, but CAND-B is negative (-1)
    bad_tally = {
        "candidate_tallies": {"CAND-A": 5, "CAND-B": -1, "CAND-C": 0},
        "total_ballots": 4,
    }
    patch_bundle_artifact(b_dir, "tally/decrypted_tally.json", bad_tally)

    report = StandaloneBundleVerifier.verify(b_dir)
    assert report["verified"] is False
    cp15 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_15_tally_reconciliation")
    assert cp15["status"] == "FAILED"
    assert "Invalid tally values" in cp15["message"]


# -----------------------------------------------------------------------------
# Test 2: Checkpoint 15 Rejects Unknown Candidates
# -----------------------------------------------------------------------------

def test_checkpoint_15_rejects_unknown_candidate(centralized_package, tmp_path):
    """Reject candidate tallies that include undeclared/unknown candidates."""
    b_dir = str(tmp_path / "unknown_cand_bundle")
    export_bundle(package=centralized_package, output_dir=b_dir)

    bad_tally = {
        "candidate_tallies": {"CAND-A": 2, "CAND-B": 1, "CAND-C": 1, "ROGUE": 0},
        "total_ballots": 4,
    }
    patch_bundle_artifact(b_dir, "tally/decrypted_tally.json", bad_tally)

    report = StandaloneBundleVerifier.verify(b_dir)
    assert report["verified"] is False
    cp15 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_15_tally_reconciliation")
    assert cp15["status"] == "FAILED"
    assert "Candidate mismatch" in cp15["message"]


# -----------------------------------------------------------------------------
# Test 3: Checkpoint 15 Rejects Missing Candidates
# -----------------------------------------------------------------------------

def test_checkpoint_15_rejects_missing_candidate(centralized_package, tmp_path):
    """Reject candidate tallies that omit one or more declared candidates."""
    b_dir = str(tmp_path / "missing_cand_bundle")
    export_bundle(package=centralized_package, output_dir=b_dir)

    bad_tally = {
        "candidate_tallies": {"CAND-A": 2, "CAND-B": 2},  # CAND-C missing
        "total_ballots": 4,
    }
    patch_bundle_artifact(b_dir, "tally/decrypted_tally.json", bad_tally)

    report = StandaloneBundleVerifier.verify(b_dir)
    assert report["verified"] is False
    cp15 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_15_tally_reconciliation")
    assert cp15["status"] == "FAILED"
    assert "Candidate mismatch" in cp15["message"]


# -----------------------------------------------------------------------------
# Test 4: Checkpoint 15 Rejects Non-Integer Tallies (Floats, Bools)
# -----------------------------------------------------------------------------

def test_checkpoint_15_rejects_non_integer_tally(centralized_package, tmp_path):
    """Reject boolean or non-integer values disguised as numbers."""
    b_dir = str(tmp_path / "bool_tally_bundle")
    export_bundle(package=centralized_package, output_dir=b_dir)

    bad_tally = {
        "candidate_tallies": {"CAND-A": True, "CAND-B": 2, "CAND-C": 1},
        "total_ballots": 4,
    }
    patch_bundle_artifact(b_dir, "tally/decrypted_tally.json", bad_tally)

    report = StandaloneBundleVerifier.verify(b_dir)
    assert report["verified"] is False
    cp15 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_15_tally_reconciliation")
    assert cp15["status"] == "FAILED"
    assert "Invalid tally values" in cp15["message"]


# -----------------------------------------------------------------------------
# Test 5: Valid Centralized Tally Passes
# -----------------------------------------------------------------------------

def test_valid_centralized_tally_passes(centralized_package, test_signing_key, tmp_path):
    """A mathematically sound centralized bundle passes Checkpoint 15 and overall."""
    priv_hex, pub_hex = test_signing_key
    b_dir = str(tmp_path / "valid_central_bundle")
    export_bundle(
        package=centralized_package,
        output_dir=b_dir,
        signing_private_key_hex=priv_hex,
    )

    report = StandaloneBundleVerifier.verify(
        bundle_path=b_dir,
        trusted_signing_public_key_hex=pub_hex,
    )
    assert report["verified"] is True
    cp15 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_15_tally_reconciliation")
    assert cp15["status"] == "PASSED"
    assert "Zero-drift reconciliation verified" in cp15["message"]


# -----------------------------------------------------------------------------
# Test 6: Unsigned Bundle CP4 Status Is NOT_APPLICABLE
# -----------------------------------------------------------------------------

def test_unsigned_bundle_status_is_not_applicable(centralized_package, tmp_path):
    """Unsigned bundles record CP4 as NOT_APPLICABLE, not PASSED or FAILED."""
    b_dir = str(tmp_path / "unsigned_bundle")
    export_bundle(package=centralized_package, output_dir=b_dir, signing_private_key_hex=None)

    report = StandaloneBundleVerifier.verify(bundle_path=b_dir)
    assert report["verified"] is True
    cp4 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_4_signature")
    assert cp4["status"] == "NOT_APPLICABLE"
    assert "NOT_APPLICABLE" in cp4["message"]
    assert report["signature_status"] == BundleVerificationStatus.NOT_PRESENT.value


# -----------------------------------------------------------------------------
# Test 7: Centralized Threshold Checks Are NOT_APPLICABLE
# -----------------------------------------------------------------------------

def test_centralized_threshold_checks_are_not_applicable(centralized_package, tmp_path):
    """In centralized mode, Checkpoints 12, 13, and 14 are NOT_APPLICABLE."""
    b_dir = str(tmp_path / "central_threshold_na_bundle")
    export_bundle(package=centralized_package, output_dir=b_dir)

    report = StandaloneBundleVerifier.verify(bundle_path=b_dir)
    assert report["verified"] is True

    cp12 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_12_threshold_manifest")
    cp13 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_13_partial_decryption_proofs")
    cp14 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_14_lagrange_combination_and_dlog")

    assert cp12["status"] == "NOT_APPLICABLE"
    assert cp13["status"] == "NOT_APPLICABLE"
    assert cp14["status"] == "NOT_APPLICABLE"


# -----------------------------------------------------------------------------
# Test 8: NOT_APPLICABLE Not Counted As Passed
# -----------------------------------------------------------------------------

def test_not_applicable_not_counted_as_passed(centralized_package, tmp_path):
    """Ensure checkpoints_passed strictly counts PASSED and tracks checkpoints_not_applicable."""
    b_dir = str(tmp_path / "counts_bundle")
    # Unsigned centralized bundle has CP4, CP12, CP13, CP14 NOT_APPLICABLE
    export_bundle(package=centralized_package, output_dir=b_dir, signing_private_key_hex=None)

    report = StandaloneBundleVerifier.verify(bundle_path=b_dir)
    assert report["verified"] is True
    assert report["checkpoints_failed"] == 0
    assert report["checkpoints_not_applicable"] == 4  # CP4, CP12, CP13, CP14
    assert report["checkpoints_passed"] == 11  # 15 - 4 = 11
    assert report["checkpoints_total"] == 15


# -----------------------------------------------------------------------------
# Test 9: Duplicate ZIP Member Rejected
# -----------------------------------------------------------------------------

def test_duplicate_zip_member_rejected(tmp_path):
    """ZIP bundles containing duplicate entries must be rejected immediately to avoid shadowing attacks."""
    import warnings
    zip_buf = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", b'{"election_id": "TEST"}')
            zf.writestr("manifest.json", b'{"election_id": "SHADOW"}')

    bad_zip_path = str(tmp_path / "shadowing.zip")
    with open(bad_zip_path, "wb") as f:
        f.write(zip_buf.getvalue())

    # BundleReader should raise ValueError
    with pytest.raises(ValueError, match="duplicate member names"):
        BundleReader(bad_zip_path)

    # StandaloneBundleVerifier should fail gracefully with MALFORMED
    report = StandaloneBundleVerifier.verify(bad_zip_path)
    assert report["verified"] is False
    assert report["overall_status"] == BundleVerificationStatus.MALFORMED.value
    assert "duplicate member names" in report["error"]


# -----------------------------------------------------------------------------
# Test 10: Threshold 2-of-3 Still Passes
# -----------------------------------------------------------------------------

def test_threshold_2_of_3_still_passes(test_signing_key, tmp_path):
    """2-of-3 threshold election bundle passes all 15 checkpoints."""
    priv_hex, pub_hex = test_signing_key
    pkg = make_threshold_package(threshold=2, total_trustees=3, election_id="P3-THRESH-2OF3")
    b_dir = str(tmp_path / "thresh_2of3_bundle")

    export_bundle(package=pkg, output_dir=b_dir, signing_private_key_hex=priv_hex)
    report = StandaloneBundleVerifier.verify(bundle_path=b_dir, trusted_signing_public_key_hex=pub_hex)

    assert report["verified"] is True
    assert report["checkpoints_passed"] == 15
    assert report["checkpoints_failed"] == 0
    assert report["checkpoints_not_applicable"] == 0


# -----------------------------------------------------------------------------
# Test 11: Threshold 3-of-5 Passes
# -----------------------------------------------------------------------------

def test_threshold_3_of_5_passes(test_signing_key, tmp_path):
    """Generalized 3-of-5 threshold election bundle passes CP12, CP13, and CP14."""
    priv_hex, pub_hex = test_signing_key
    pkg = make_threshold_package(
        threshold=3,
        total_trustees=5,
        election_id="P3-THRESH-3OF5",
        selected_ids=[1, 3, 5],
    )
    b_dir = str(tmp_path / "thresh_3of5_bundle")

    export_bundle(package=pkg, output_dir=b_dir, signing_private_key_hex=priv_hex)
    report = StandaloneBundleVerifier.verify(bundle_path=b_dir, trusted_signing_public_key_hex=pub_hex)

    assert report["verified"] is True
    assert report["checkpoints_passed"] == 15
    assert report["checkpoints_failed"] == 0

    cp12 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_12_threshold_manifest")
    cp13 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_13_partial_decryption_proofs")
    cp14 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_14_lagrange_combination_and_dlog")

    assert cp12["status"] == "PASSED"
    assert "t=3, n=5" in cp12["message"]
    assert cp13["status"] == "PASSED"
    assert cp14["status"] == "PASSED"


# -----------------------------------------------------------------------------
# Test 12: Threshold Insufficient Trustees Fails
# -----------------------------------------------------------------------------

def test_threshold_insufficient_trustees_fails(test_signing_key, tmp_path):
    """If selected trustees count is less than threshold t, Checkpoint 14 must fail."""
    priv_hex, pub_hex = test_signing_key
    pkg = make_threshold_package(threshold=2, total_trustees=3, election_id="P3-INSUFFICIENT-T")
    b_dir = str(tmp_path / "thresh_insufficient_bundle")
    export_bundle(package=pkg, output_dir=b_dir, signing_private_key_hex=priv_hex)

    # Tamper threshold_tally.json to only declare 1 trustee when t=2
    with open(os.path.join(b_dir, "threshold/threshold_tally.json"), "r") as f:
        t_data = json.load(f)

    t_data["selected_trustees"] = [1]
    patch_bundle_artifact(b_dir, "threshold/threshold_tally.json", t_data)

    report = StandaloneBundleVerifier.verify(bundle_path=b_dir)
    assert report["verified"] is False
    cp14 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_14_lagrange_combination_and_dlog")
    assert cp14["status"] == "FAILED"
    assert "Selected trustees count" in cp14["message"]


# -----------------------------------------------------------------------------
# Test 13: Threshold Duplicate Trustees Fails
# -----------------------------------------------------------------------------

def test_threshold_duplicate_trustees_fails(test_signing_key, tmp_path):
    """If selected trustees list has duplicates (e.g. [1, 1]), Checkpoint 14 must fail."""
    priv_hex, pub_hex = test_signing_key
    pkg = make_threshold_package(threshold=2, total_trustees=3, election_id="P3-DUP-TRUSTEES")
    b_dir = str(tmp_path / "thresh_dup_bundle")
    export_bundle(package=pkg, output_dir=b_dir, signing_private_key_hex=priv_hex)

    with open(os.path.join(b_dir, "threshold/threshold_tally.json"), "r") as f:
        t_data = json.load(f)

    t_data["selected_trustees"] = [1, 1]
    patch_bundle_artifact(b_dir, "threshold/threshold_tally.json", t_data)

    report = StandaloneBundleVerifier.verify(bundle_path=b_dir)
    assert report["verified"] is False
    cp14 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_14_lagrange_combination_and_dlog")
    assert cp14["status"] == "FAILED"
    assert "distinct" in cp14["message"]


# -----------------------------------------------------------------------------
# Test 14: Threshold Invalid Trustee Fails
# -----------------------------------------------------------------------------

def test_threshold_invalid_trustee_fails(test_signing_key, tmp_path):
    """If selected trustees contains an ID not in QUAL, Checkpoint 14 must fail."""
    priv_hex, pub_hex = test_signing_key
    pkg = make_threshold_package(threshold=2, total_trustees=3, election_id="P3-INVALID-TRUSTEE")
    b_dir = str(tmp_path / "thresh_invalid_bundle")
    export_bundle(package=pkg, output_dir=b_dir, signing_private_key_hex=priv_hex)

    with open(os.path.join(b_dir, "threshold/threshold_tally.json"), "r") as f:
        t_data = json.load(f)

    t_data["selected_trustees"] = [1, 99]
    patch_bundle_artifact(b_dir, "threshold/threshold_tally.json", t_data)

    report = StandaloneBundleVerifier.verify(bundle_path=b_dir)
    assert report["verified"] is False
    cp14 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_14_lagrange_combination_and_dlog")
    assert cp14["status"] == "FAILED"
    assert "must be in QUAL" in cp14["message"]
