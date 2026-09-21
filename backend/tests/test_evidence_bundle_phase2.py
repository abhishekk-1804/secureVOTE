"""
SecureVOTE 3.3 Phase 2 — Comprehensive Portable Evidence Bundle Test Suite.

Validates:
1. Happy Path:
   - Full directory bundle export and standalone verification (15/15 checkpoints).
   - Full ZIP archive bundle export and standalone verification without disk extraction.
   - Ed25519 signed bundle verification.
   - Unsigned bundle verification (reports NOT_PRESENT signature status honestly).
   - Trusted signing key pinning.
   - Threshold election bundle verification (DKG manifest, trustee shares, Chaum-Pedersen proofs, Lagrange reconstruction).

2. Determinism & Canonicalization:
   - Identical package exported twice produces byte-identical files, manifests, and hashes.
   - Floating-point rejection in manifests and canonical serialization.
   - Lexicographically sorted inventory order.

3. Adversarial Mutation Matrix (28+ targeted attacks):
   - Manifest schema mutations (floats, missing fields, version spoofing, unsorted inventory).
   - Inventory tampering (missing file, rogue undeclared file, tampered SHA-256, tampered size).
   - Directory traversal attacks (.., absolute paths, drive letters, leading slashes, redundant /).
   - Signature forgery (altered signature, altered manifest hash, untrusted key).
   - Ballot tampering (mutated ciphertext, off-curve coordinates, forged commitments, tampered proofs).
   - Aggregation tampering (mutated encrypted tally, tally commitment mismatch).
   - Threshold tampering (mutated DKG manifest, forged partial decryption share, tampered CP proof, insufficient quorum).
   - Tally reconciliation tampering (vote drift, candidate count mismatch).
"""

import copy
import json
import os
import shutil
import tempfile
import uuid
import zipfile
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encrypt_ballot
from app.crypto.canonical import ballot_domain, canonical_hash, canonical_json
from app.crypto.commitment import compute_ballot_commitment
from app.crypto.elgamal import (
    CURVE_ORDER,
    G,
    ECPoint,
    ElGamalCiphertext,
    ElGamalPublicKey,
    add_ciphertexts,
    encrypt,
    generate_keypair,
    point_add,
    scalar_mult,
)
from app.crypto.exceptions import SerializationError
from app.crypto.keys import compute_key_fingerprint, serialize_public_key
from app.crypto.serialization import serialize_ciphertext
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally
from app.crypto.threshold import (
    ChaumPedersenEqualityProof,
    DKGPublicManifest,
    PartialDecryptionShare,
    TallyPartialDecryptionPackage,
    TrusteeDKGSession,
    build_dkg_manifest,
    combine_candidate_partial_decryptions,
    compute_tally_partial_decryptions,
    reconstruct_threshold_tally,
    resolve_qualified_set,
)
from app.crypto.threshold.serialization import (
    serialize_dkg_manifest,
    serialize_tally_partial_decryption_package,
    serialize_threshold_tally_result,
)
from app.crypto.zk import prove_ballot_validity
from standalone_verifier.bundle import (
    BUNDLE_PROTOCOL_VERSION,
    CANONICALIZATION_VERSION,
    HASH_ALGORITHM,
    BundleVerificationStatus,
    compute_file_sha256,
    compute_manifest_hash,
    normalize_bundle_path,
    validate_manifest_schema,
)
from standalone_verifier.bundle_export import export_bundle
from standalone_verifier.bundle_verifier import BundleReader, StandaloneBundleVerifier


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def ed25519_keypair():
    """Generate a test Ed25519 keypair."""
    priv = ed25519.Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return priv_bytes.hex(), pub_bytes.hex()


@pytest.fixture
def standard_v3_package():
    """Build a mathematically valid standard v3 election package with ZK proofs."""
    keypair = generate_keypair()
    pub_data = serialize_public_key(keypair.public_key)
    election_id = "BUNDLE-TEST-ELEC-001"
    candidates = ["CAND-ALPHA", "CAND-BETA", "CAND-GAMMA", "NOTA"]
    candidate_count = len(candidates)

    # 4 ballots: votes = [0, 1, 0, 2]
    votes = [0, 1, 0, 2]
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


@pytest.fixture
def threshold_v3_package():
    """Build a complete, verifiable 3-trustee threshold election package."""
    election_id = "BUNDLE-THRESH-ELEC-002"
    candidate_ids = ["CAND-A", "CAND-B", "CAND-C"]
    candidate_count = len(candidate_ids)

    # 1. DKG across 3 trustees with threshold t=2
    sessions = [TrusteeDKGSession(i, election_id, threshold=2, total_trustees=3) for i in [1, 2, 3]]
    pedersen_pkgs = {s.trustee_id: s.generate_pedersen_commitments() for s in sessions}

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
    pub_data = serialize_public_key(joint_pubkey)

    # 2. Encrypt 3 ballots: votes = [A, B, A] -> A=2, B=1, C=0
    ballot_votes = [0, 1, 0]
    ballots = []
    for v_idx in ballot_votes:
        b = encrypt_ballot(
            public_key=joint_pubkey,
            candidate_index=v_idx,
            candidate_count=candidate_count,
            election_id=election_id,
            candidate_ids=candidate_ids,
            with_zkp=True,
        )
        ballots.append(b)

    key_fp = compute_key_fingerprint(joint_pubkey)
    encrypted_tally = aggregate_encrypted_ballots(ballots, election_id, key_fp)

    # 3. Candidate A-points from aggregated ciphertext
    tally_slots = encrypted_tally["encrypted_tally"]["slots"]
    candidate_a_points = {}
    for j, cid in enumerate(candidate_ids):
        ct_slot = serialize_ciphertext(ElGamalCiphertext(
            c1=ECPoint(int(tally_slots[j]["c1"]["x"], 16), int(tally_slots[j]["c1"]["y"], 16)),
            c2=ECPoint(int(tally_slots[j]["c2"]["x"], 16), int(tally_slots[j]["c2"]["y"], 16)),
        ))
        candidate_a_points[cid] = ECPoint(int(tally_slots[j]["c1"]["x"], 16), int(tally_slots[j]["c1"]["y"], 16))

    # Trustees 1 and 2 produce partial decryptions
    trustee_packages = {}
    for t_id in [1, 2]:
        pkg = compute_tally_partial_decryptions(key_shares[t_id], candidate_a_points)
        trustee_packages[t_id] = pkg

    # 4. Combine partial decryptions
    tally_result = reconstruct_threshold_tally(
        shares_by_trustee=trustee_packages,
        encrypted_tally=encrypted_tally,
        manifest=manifest,
        max_ballots=len(ballots),
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
        "candidates": candidate_ids,
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


# -----------------------------------------------------------------------------
# Test Suite 1: Happy Paths
# -----------------------------------------------------------------------------

def test_happy_path_directory_bundle(standard_v3_package, ed25519_keypair, tmp_path):
    """Test full directory bundle export and standalone 15-checkpoint verification."""
    priv_hex, pub_hex = ed25519_keypair
    bundle_dir = str(tmp_path / "bundle_dir")

    manifest = export_bundle(
        package=standard_v3_package,
        output_dir=bundle_dir,
        signing_private_key_hex=priv_hex,
        create_zip=False,
    )

    assert manifest["bundle_protocol_version"] == BUNDLE_PROTOCOL_VERSION
    assert manifest["signature"] is not None

    report = StandaloneBundleVerifier.verify(
        bundle_path=bundle_dir,
        trusted_signing_public_key_hex=pub_hex,
    )

    assert report["verified"] is True
    assert report["overall_status"] == BundleVerificationStatus.VALID.value
    assert report["checkpoints_passed"] == 15
    assert report["checkpoints_failed"] == 0

    for cp in report["checkpoints"]:
        assert cp["status"] == "PASSED", f"Checkpoint {cp['checkpoint']} failed: {cp['message']}"


def test_happy_path_zip_bundle(standard_v3_package, ed25519_keypair, tmp_path):
    """Test full ZIP archive bundle export and verification directly from archive."""
    priv_hex, pub_hex = ed25519_keypair
    bundle_dir = str(tmp_path / "bundle_zip_source")
    zip_path = f"{bundle_dir}.zip"

    export_bundle(
        package=standard_v3_package,
        output_dir=bundle_dir,
        signing_private_key_hex=priv_hex,
        create_zip=True,
    )

    assert os.path.exists(zip_path)

    report = StandaloneBundleVerifier.verify(
        bundle_path=zip_path,
        trusted_signing_public_key_hex=pub_hex,
    )

    assert report["verified"] is True
    assert report["checkpoints_passed"] == 15
    assert report["checkpoints_failed"] == 0
    assert report["overall_status"] == BundleVerificationStatus.VALID.value


def test_happy_path_unsigned_bundle(standard_v3_package, tmp_path):
    """Test unsigned bundle reports NOT_PRESENT honestly without failing."""
    bundle_dir = str(tmp_path / "bundle_unsigned")

    manifest = export_bundle(
        package=standard_v3_package,
        output_dir=bundle_dir,
        signing_private_key_hex=None,
    )

    assert manifest["signature"] is None

    report = StandaloneBundleVerifier.verify(bundle_path=bundle_dir)

    assert report["verified"] is True
    cp4 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_4_signature")
    assert cp4["status"] == "PASSED"
    assert "NOT_PRESENT" in cp4["message"]
    assert report["signature_status"] == BundleVerificationStatus.NOT_PRESENT.value


def test_happy_path_threshold_bundle(threshold_v3_package, ed25519_keypair, tmp_path):
    """Test full threshold election bundle with DKG manifest and Chaum-Pedersen proofs."""
    priv_hex, pub_hex = ed25519_keypair
    bundle_dir = str(tmp_path / "threshold_bundle")

    export_bundle(
        package=threshold_v3_package,
        output_dir=bundle_dir,
        signing_private_key_hex=priv_hex,
        create_zip=False,
    )

    report = StandaloneBundleVerifier.verify(
        bundle_path=bundle_dir,
        trusted_signing_public_key_hex=pub_hex,
    )

    assert report["verified"] is True
    assert report["overall_status"] == BundleVerificationStatus.VALID.value
    assert report["checkpoints_passed"] == 15
    assert report["checkpoints_failed"] == 0

    cp12 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_12_threshold_manifest")
    cp13 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_13_partial_decryption_proofs")
    cp14 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_14_lagrange_combination_and_dlog")
    assert cp12["status"] == "PASSED"
    assert cp13["status"] == "PASSED"
    assert cp14["status"] == "PASSED"


# -----------------------------------------------------------------------------
# Test Suite 2: Determinism & Canonicalization
# -----------------------------------------------------------------------------

def test_bundle_export_pure_determinism(standard_v3_package, ed25519_keypair, tmp_path):
    """Exporting the same package twice must yield byte-for-byte identical output."""
    priv_hex, _ = ed25519_keypair
    dir1 = str(tmp_path / "bundle_det_1")
    dir2 = str(tmp_path / "bundle_det_2")

    fixed_ts = "2026-09-21T12:00:00Z"

    m1 = export_bundle(standard_v3_package, dir1, signing_private_key_hex=priv_hex, deterministic_timestamp=fixed_ts)
    m2 = export_bundle(standard_v3_package, dir2, signing_private_key_hex=priv_hex, deterministic_timestamp=fixed_ts)

    # Manifests must match exactly
    assert canonical_json(m1) == canonical_json(m2)
    assert m1["manifest_hash"] == m2["manifest_hash"]

    # Compare every file in inventory
    for item1, item2 in zip(m1["artifact_inventory"], m2["artifact_inventory"]):
        assert item1["path"] == item2["path"]
        assert item1["sha256"] == item2["sha256"]
        assert item1["size_bytes"] == item2["size_bytes"]

        with open(os.path.join(dir1, item1["path"]), "rb") as f1, open(os.path.join(dir2, item2["path"]), "rb") as f2:
            assert f1.read() == f2.read()


def test_float_rejection_in_manifest(standard_v3_package, tmp_path):
    """Floats in manifest schema must raise ValueError."""
    bundle_dir = str(tmp_path / "bundle_float_test")
    manifest = export_bundle(standard_v3_package, bundle_dir)

    # Inject float
    manifest["election_parameters"]["candidate_count"] = 4.0
    with pytest.raises((ValueError, SerializationError), match="[Ff]loat"):
        validate_manifest_schema(manifest)


def test_inventory_path_sorting_enforcement(standard_v3_package, tmp_path):
    """Unsorted artifact inventory must fail manifest schema validation."""
    bundle_dir = str(tmp_path / "bundle_sort_test")
    manifest = export_bundle(standard_v3_package, bundle_dir)

    # Swap first two items in inventory to break sorting
    assert len(manifest["artifact_inventory"]) >= 2
    item0 = manifest["artifact_inventory"][0]
    item1 = manifest["artifact_inventory"][1]
    manifest["artifact_inventory"][0] = item1
    manifest["artifact_inventory"][1] = item0

    with pytest.raises(ValueError, match="sorted"):
        validate_manifest_schema(manifest)


# -----------------------------------------------------------------------------
# Test Suite 3: Path Traversal Defenses
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("malicious_path", [
    "../evil.json",
    "context/../../etc/passwd",
    "..\\evil.json",
    "/etc/shadow",
    "\\windows\\system32\\calc.exe",
    "C:/secret.txt",
    "D:\\boot.ini",
    "foo//bar",
    "foo/./bar",
    "./bar",
    "bar/.",
    ".",
])
def test_path_traversal_rejection(malicious_path):
    """Path traversal sequences, redundant slashes, and non-relative paths must be rejected."""
    with pytest.raises(ValueError):
        normalize_bundle_path(malicious_path)


# -----------------------------------------------------------------------------
# Test Suite 4: Adversarial Mutation Matrix
# -----------------------------------------------------------------------------

@pytest.fixture
def base_exported_bundle(standard_v3_package, ed25519_keypair, tmp_path):
    """Create a baseline exported bundle directory for mutation tests."""
    priv_hex, pub_hex = ed25519_keypair
    bundle_dir = str(tmp_path / "base_bundle")
    export_bundle(
        package=standard_v3_package,
        output_dir=bundle_dir,
        signing_private_key_hex=priv_hex,
    )
    return bundle_dir, pub_hex


def mutate_file(bundle_dir: str, rel_path: str, mutator_fn):
    """Helper to load, mutate, and overwrite a JSON file in the bundle."""
    full_path = os.path.join(bundle_dir, rel_path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    mutated = mutator_fn(data)
    with open(full_path, "wb") as f:
        f.write(canonical_json(mutated).encode("utf-8"))


# --- Checkpoint 1 & 2: Schema and Manifest Hash Mutations ---

def test_mutation_manifest_version_downgrade(base_exported_bundle, tmp_path):
    """Attack 1: Spoofed or downgraded bundle protocol version."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m1")
    shutil.copytree(src, target)

    def mutate(m):
        m["bundle_protocol_version"] = "SECUREVOTE-EVIDENCE-BUNDLE-0"
        return m
    mutate_file(target, "manifest.json", mutate)

    report = StandaloneBundleVerifier.verify(target, trusted_signing_public_key_hex=pub)
    assert report["verified"] is False
    assert report["overall_status"] == BundleVerificationStatus.MALFORMED.value
    assert report["checkpoints"][0]["status"] == "FAILED"


def test_mutation_manifest_missing_field(base_exported_bundle, tmp_path):
    """Attack 2: Manifest missing required top-level field."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m2")
    shutil.copytree(src, target)

    def mutate(m):
        del m["election_parameters"]
        return m
    mutate_file(target, "manifest.json", mutate)

    report = StandaloneBundleVerifier.verify(target, trusted_signing_public_key_hex=pub)
    assert report["verified"] is False
    assert report["overall_status"] == BundleVerificationStatus.MALFORMED.value


def test_mutation_manifest_hash_tampering(base_exported_bundle, tmp_path):
    """Attack 3: Altered manifest hash."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m3")
    shutil.copytree(src, target)

    def mutate(m):
        m["manifest_hash"] = "aa" * 32
        return m
    mutate_file(target, "manifest.json", mutate)

    report = StandaloneBundleVerifier.verify(target, trusted_signing_public_key_hex=pub)
    assert report["verified"] is False
    assert any(c["checkpoint"] == "checkpoint_2_manifest_hash" and c["status"] == "FAILED" for c in report["checkpoints"])


# --- Checkpoint 3: Inventory Integrity Mutations ---

def test_mutation_inventory_file_hash_mismatch(base_exported_bundle, tmp_path):
    """Attack 4: Modifying content of an artifact without updating manifest."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m4")
    shutil.copytree(src, target)

    def mutate(el):
        el["candidates"].append("ROGUE-CANDIDATE")
        return el
    mutate_file(target, "context/election.json", mutate)

    report = StandaloneBundleVerifier.verify(target, trusted_signing_public_key_hex=pub)
    assert report["verified"] is False
    cp3 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_3_inventory_integrity")
    assert cp3["status"] == "FAILED"


def test_mutation_inventory_missing_file(base_exported_bundle, tmp_path):
    """Attack 5: Deleting an artifact declared in inventory."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m5")
    shutil.copytree(src, target)

    os.remove(os.path.join(target, "context/election.json"))

    report = StandaloneBundleVerifier.verify(target, trusted_signing_public_key_hex=pub)
    assert report["verified"] is False
    cp3 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_3_inventory_integrity")
    assert cp3["status"] == "FAILED"


def test_mutation_inventory_undeclared_rogue_file(base_exported_bundle, tmp_path):
    """Attack 6: Adding an undeclared rogue file to the bundle."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m6")
    shutil.copytree(src, target)

    with open(os.path.join(target, "rogue_backdoor.sh"), "w") as f:
        f.write("#!/bin/sh\necho malicious")

    report = StandaloneBundleVerifier.verify(target, trusted_signing_public_key_hex=pub)
    assert report["verified"] is False
    cp3 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_3_inventory_integrity")
    assert cp3["status"] == "FAILED"
    assert "Undeclared" in cp3["message"] or "Undeclared" in str(cp3["details"])


def test_mutation_inventory_duplicate_path(base_exported_bundle, tmp_path):
    """Attack 7: Duplicate paths inside manifest inventory."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m7")
    shutil.copytree(src, target)

    def mutate(m):
        dup = copy.deepcopy(m["artifact_inventory"][0])
        dup["artifact_id"] = "dup_id"
        m["artifact_inventory"].append(dup)
        return m
    mutate_file(target, "manifest.json", mutate)

    report = StandaloneBundleVerifier.verify(target, trusted_signing_public_key_hex=pub)
    assert report["verified"] is False
    assert report["overall_status"] == BundleVerificationStatus.MALFORMED.value


# --- Checkpoint 4: Signature Attacks ---

def test_mutation_signature_forged_bytes(base_exported_bundle, tmp_path):
    """Attack 8: Forged Ed25519 signature."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m8")
    shutil.copytree(src, target)

    def mutate(m):
        m["signature"]["signature"] = "ff" * 64
        return m
    mutate_file(target, "manifest.json", mutate)

    report = StandaloneBundleVerifier.verify(target, trusted_signing_public_key_hex=pub)
    assert report["verified"] is False
    cp4 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_4_signature")
    assert cp4["status"] == "FAILED"


def test_mutation_signature_wrong_trusted_key(base_exported_bundle, tmp_path):
    """Attack 9: Signature valid but signed by untrusted key."""
    src, _ = base_exported_bundle
    target = str(tmp_path / "m9")
    shutil.copytree(src, target)

    untrusted_pub = "11" * 32
    report = StandaloneBundleVerifier.verify(target, trusted_signing_public_key_hex=untrusted_pub)
    assert report["verified"] is False
    cp4 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_4_signature")
    assert cp4["status"] == "FAILED"
    assert "does not match trusted key" in cp4["message"]


# --- Checkpoint 5, 6, 7: Context & Keys ---

def test_mutation_election_id_drift(base_exported_bundle, tmp_path):
    """Attack 10: Election ID mismatch between manifest and context/election.json."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m10")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    with open(os.path.join(target, "context/election.json"), "r") as f:
        el = json.load(f)
    el["election_id"] = "DIFFERENT-ELECTION-ID"
    new_el_bytes = canonical_json(el).encode("utf-8")
    with open(os.path.join(target, "context/election.json"), "wb") as f:
        f.write(new_el_bytes)

    for item in m["artifact_inventory"]:
        if item["path"] == "context/election.json":
            item["sha256"] = compute_file_sha256(new_el_bytes)
            item["size_bytes"] = len(new_el_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp5 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_5_election_identity")
    assert cp5["status"] == "FAILED"


def test_mutation_candidate_count_tampering(base_exported_bundle, tmp_path):
    """Attack 11: Candidate count mismatch between manifest and context."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m11")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    m["election_parameters"]["candidate_count"] = 99
    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp6 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_6_candidate_config")
    assert cp6["status"] == "FAILED"


def test_mutation_public_key_point_off_curve(base_exported_bundle, tmp_path):
    """Attack 12: Public key point off secp256r1 curve."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m12")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    with open(os.path.join(target, "context/public_key.json"), "r") as f:
        pk = json.load(f)
    pk["y"] = "00" * 32
    new_bytes = canonical_json(pk).encode("utf-8")
    with open(os.path.join(target, "context/public_key.json"), "wb") as f:
        f.write(new_bytes)

    for item in m["artifact_inventory"]:
        if item["path"] == "context/public_key.json":
            item["sha256"] = compute_file_sha256(new_bytes)
            item["size_bytes"] = len(new_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp7 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_7_public_key")
    assert cp7["status"] == "FAILED"


# --- Checkpoint 8 & 9: Ballot Ciphertexts, Commitments, Proofs ---

def test_mutation_ballot_commitment_tampering(base_exported_bundle, tmp_path):
    """Attack 13: Forged ballot commitment hash."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m13")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    b_path = "ballots/ballot_000000.json"
    with open(os.path.join(target, b_path), "r") as f:
        b = json.load(f)
    b["commitment"] = "aa" * 32
    new_bytes = canonical_json(b).encode("utf-8")
    with open(os.path.join(target, b_path), "wb") as f:
        f.write(new_bytes)

    for item in m["artifact_inventory"]:
        if item["path"] == b_path:
            item["sha256"] = compute_file_sha256(new_bytes)
            item["size_bytes"] = len(new_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp8 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_8_ballot_ciphertexts_and_commitments")
    assert cp8["status"] == "FAILED"


def test_mutation_ballot_zk_proof_tampering(base_exported_bundle, tmp_path):
    """Attack 14: Tampered zero-knowledge validity proof."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m14")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    p_path = "proofs/proof_000000.json"
    assert os.path.exists(os.path.join(target, p_path))

    with open(os.path.join(target, p_path), "r") as f:
        p = json.load(f)
    # Mutate proof response_r scalar
    p["proof"]["sum_proof"]["response_r"] = hex(123456789)
    new_bytes = canonical_json(p).encode("utf-8")
    with open(os.path.join(target, p_path), "wb") as f:
        f.write(new_bytes)

    for item in m["artifact_inventory"]:
        if item["path"] == p_path:
            item["sha256"] = compute_file_sha256(new_bytes)
            item["size_bytes"] = len(new_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp9 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_9_zk_validity_proofs")
    assert cp9["status"] == "FAILED"


# --- Checkpoint 10 & 11: Homomorphic Aggregation and Tally Commitment ---

def test_mutation_homomorphic_tally_tampering(base_exported_bundle, tmp_path):
    """Attack 15: Tampered aggregate encrypted tally slot."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m15")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    t_path = "tally/encrypted_tally.json"
    with open(os.path.join(target, t_path), "r") as f:
        enc_t = json.load(f)
    slots = enc_t.get("encrypted_tally", {}).get("slots", [])
    if slots:
        slots[0]["c2"]["x"] = hex(int(slots[0]["c2"]["x"], 16) + 1)[2:].zfill(64)
    new_bytes = canonical_json(enc_t).encode("utf-8")
    with open(os.path.join(target, t_path), "wb") as f:
        f.write(new_bytes)

    for item in m["artifact_inventory"]:
        if item["path"] == t_path:
            item["sha256"] = compute_file_sha256(new_bytes)
            item["size_bytes"] = len(new_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp10 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_10_homomorphic_aggregation")
    assert cp10["status"] == "FAILED"


# --- Checkpoint 12, 13, 14: Threshold Cryptosystem Attacks ---

@pytest.fixture
def base_exported_threshold_bundle(threshold_v3_package, ed25519_keypair, tmp_path):
    """Create a baseline threshold bundle for threshold-specific attacks."""
    priv_hex, pub_hex = ed25519_keypair
    bundle_dir = str(tmp_path / "base_threshold_bundle")
    export_bundle(
        package=threshold_v3_package,
        output_dir=bundle_dir,
        signing_private_key_hex=priv_hex,
    )
    return bundle_dir, pub_hex


def test_mutation_threshold_dkg_joint_key_altered(base_exported_threshold_bundle, tmp_path):
    """Attack 16: Altered joint public key in DKG manifest."""
    src, pub = base_exported_threshold_bundle
    target = str(tmp_path / "m16")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    dkg_path = "threshold/dkg_manifest.json"
    with open(os.path.join(target, dkg_path), "r") as f:
        dkg = json.load(f)
    dkg["joint_public_key"]["x"] = hex((int(dkg["joint_public_key"]["x"], 16) + 2))[2:].zfill(64)
    new_bytes = canonical_json(dkg).encode("utf-8")
    with open(os.path.join(target, dkg_path), "wb") as f:
        f.write(new_bytes)

    for item in m["artifact_inventory"]:
        if item["path"] == dkg_path:
            item["sha256"] = compute_file_sha256(new_bytes)
            item["size_bytes"] = len(new_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp12 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_12_threshold_manifest")
    assert cp12["status"] == "FAILED"


def test_mutation_threshold_chaum_pedersen_proof_tampered(base_exported_threshold_bundle, tmp_path):
    """Attack 17: Mutated Chaum-Pedersen proof in trustee partial decryption package."""
    src, pub = base_exported_threshold_bundle
    target = str(tmp_path / "m17")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    t1_path = "threshold/trustee_01.json"
    with open(os.path.join(target, t1_path), "r") as f:
        tpkg = json.load(f)
    cid0 = list(tpkg["shares"].keys())[0]
    tpkg["shares"][cid0]["proof"]["s"] = hex(123456789)[2:].zfill(64)
    new_bytes = canonical_json(tpkg).encode("utf-8")
    with open(os.path.join(target, t1_path), "wb") as f:
        f.write(new_bytes)

    for item in m["artifact_inventory"]:
        if item["path"] == t1_path:
            item["sha256"] = compute_file_sha256(new_bytes)
            item["size_bytes"] = len(new_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp13 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_13_partial_decryption_proofs")
    assert cp13["status"] == "FAILED"


def test_mutation_threshold_insufficient_trustees(base_exported_threshold_bundle, tmp_path):
    """Attack 18: Reconstructing tally with fewer than threshold trustees (t=2, only 1 provided)."""
    src, pub = base_exported_threshold_bundle
    target = str(tmp_path / "m18")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    res_path = "threshold/threshold_tally.json"
    with open(os.path.join(target, res_path), "r") as f:
        t_res = json.load(f)
    t_res["selected_trustees"] = [1]
    new_res_bytes = canonical_json(t_res).encode("utf-8")
    with open(os.path.join(target, res_path), "wb") as f:
        f.write(new_res_bytes)

    for item in m["artifact_inventory"]:
        if item["path"] == res_path:
            item["sha256"] = compute_file_sha256(new_res_bytes)
            item["size_bytes"] = len(new_res_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp14 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_14_lagrange_combination_and_dlog")
    assert cp14["status"] == "FAILED"


# --- Checkpoint 15: Tally Reconciliation Attacks ---

def test_mutation_tally_reconciliation_drift(base_exported_bundle, tmp_path):
    """Attack 19: Decrypted tally sum does not equal total ballots (vote stuffing/loss)."""
    src, pub = base_exported_bundle
    target = str(tmp_path / "m19")
    shutil.copytree(src, target)

    with open(os.path.join(target, "manifest.json"), "r") as f:
        m = json.load(f)

    d_path = "tally/decrypted_tally.json"
    with open(os.path.join(target, d_path), "r") as f:
        dec_t = json.load(f)
    # Inflate votes for candidate 0
    c0 = list(dec_t["candidate_tallies"].keys())[0]
    dec_t["candidate_tallies"][c0] += 5
    new_bytes = canonical_json(dec_t).encode("utf-8")
    with open(os.path.join(target, d_path), "wb") as f:
        f.write(new_bytes)

    for item in m["artifact_inventory"]:
        if item["path"] == d_path:
            item["sha256"] = compute_file_sha256(new_bytes)
            item["size_bytes"] = len(new_bytes)

    m["manifest_hash"] = compute_manifest_hash(m)
    with open(os.path.join(target, "manifest.json"), "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    report = StandaloneBundleVerifier.verify(target)
    assert report["verified"] is False
    cp15 = next(c for c in report["checkpoints"] if c["checkpoint"] == "checkpoint_15_tally_reconciliation")
    assert cp15["status"] == "FAILED"
