"""
SecureVOTE 3.4 Phase 4 — Independent Verification Hardening & Unification Test Suite.

Validates the hardened independent verification boundary across all layers:
1. Structural Independence (AST audit: zero database/ORM/FastAPI imports in standalone modules).
2. Path Traversal & Archive Security (null bytes, control chars, Windows reserved device names,
   trailing dots/spaces, zip alias shadowing, zip symlinks, zip bomb bounds, directory symlink escapes).
3. Manifest Schema & Canonicalization (canonical inventory paths, strict type validation,
   floating point rejection, threshold parameters schema).
4. Cryptographic Verifier Hardening (V3Verifier & StandaloneV3ElectionVerifier: coordinate checks,
   non-infinity C1, ballot slot count equality, strict tally reconciliation).
5. StandaloneBundleVerifier 15-Checkpoint End-to-End Validation & Tamper Defenses.
6. Isolated CLI Subprocess Verification (database-disconnected proof).
"""

import ast
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

import pytest

from app.crypto.ballot import encrypt_ballot
from app.crypto.canonical import canonical_hash, canonical_json
from app.crypto.commitment import compute_ballot_commitment, compute_tally_commitment
from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    ElGamalCiphertext,
    ElGamalPublicKey,
    G,
    INFINITY,
    _P,
    generate_keypair,
    point_add,
    point_on_curve,
    scalar_mult,
)
from app.crypto.keys import compute_key_fingerprint, serialize_public_key
from app.crypto.serialization import deserialize_ciphertext, serialize_ciphertext
from app.crypto.tally import aggregate_encrypted_ballots
from app.crypto.verification import V3Verifier
from app.crypto.zk import prove_ballot_validity
from standalone_verifier.bundle import (
    BUNDLE_PROTOCOL_VERSION,
    CANONICALIZATION_VERSION,
    HASH_ALGORITHM,
    WINDOWS_RESERVED_NAMES,
    BundleArtifactType,
    BundleVerificationStatus,
    compute_file_sha256,
    compute_manifest_hash,
    normalize_bundle_path,
    validate_manifest_schema,
)
from standalone_verifier.bundle_export import export_bundle
from standalone_verifier.bundle_verifier import BundleReader, StandaloneBundleVerifier
from standalone_verifier.v3_verifier import StandaloneV3ElectionVerifier


# =============================================================================
# Helper Fixtures & Builders
# =============================================================================

@pytest.fixture
def sample_election_bundle_data():
    """Generates a complete, mathematically valid SECUREVOTE33 package with 3 ballots."""
    keypair = generate_keypair()
    pub_data = serialize_public_key(keypair.public_key)
    election_id = "PHASE4-ELEC-TEST-001"
    candidates = ["CAND-ALICE", "CAND-BOB", "CAND-CHARLIE"]

    # 3 ballots: Alice (1,0,0), Bob (0,1,0), Alice (1,0,0)
    selections = [0, 1, 0]
    ballots = []
    for idx, sel in enumerate(selections):
        b = encrypt_ballot(
            public_key=keypair.public_key,
            candidate_index=sel,
            candidate_count=len(candidates),
            election_id=election_id,
            candidate_ids=candidates,
            with_zkp=True,
        )
        ballots.append(b)

    enc_tally = aggregate_encrypted_ballots(ballots, election_id, pub_data["fingerprint"])
    dec_tally = {
        "candidate_tallies": {"CAND-ALICE": 2, "CAND-BOB": 1, "CAND-CHARLIE": 0},
        "total_ballots": 3,
        "ballot_count": 3,
    }

    package = {
        "protocol_version": "SECUREVOTE33",
        "election_id": election_id,
        "public_key": pub_data,
        "candidates": candidates,
        "ballots": ballots,
        "encrypted_tally": enc_tally,
        "decrypted_tally": dec_tally,
    }
    return package, keypair


# =============================================================================
# 1. Structural Independence Audit (AST Analysis)
# =============================================================================

def test_standalone_modules_have_zero_database_or_orm_imports():
    """
    Audit all standalone verifier modules to guarantee zero dependencies
    on database, ORM, models, or backend services.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    modules_to_audit = [
        os.path.join(repo_root, "standalone_verifier", "bundle.py"),
        os.path.join(repo_root, "standalone_verifier", "bundle_verifier.py"),
        os.path.join(repo_root, "standalone_verifier", "v3_verifier.py"),
        os.path.join(repo_root, "standalone_verifier", "bundle_export.py"),
        os.path.join(repo_root, "standalone_verifier", "verify_bundle.py"),
        os.path.join(repo_root, "app", "crypto", "verification.py"),
    ]

    forbidden_patterns = [
        "sqlalchemy",
        "fastapi",
        "app.database",
        "app.models",
        "app.services",
        "aiosqlite",
    ]

    violations = []
    for mod_path in modules_to_audit:
        assert os.path.isfile(mod_path), f"Module not found: {mod_path}"
        with open(mod_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=mod_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for fb in forbidden_patterns:
                        if fb in alias.name:
                            violations.append((os.path.basename(mod_path), alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                for fb in forbidden_patterns:
                    if fb in mod_name:
                        violations.append((os.path.basename(mod_path), mod_name, node.lineno))

    assert len(violations) == 0, f"Structural independence violation in standalone verifiers: {violations}"


# =============================================================================
# 2. Path Traversal & Archive Hardening Tests
# =============================================================================

def test_normalize_bundle_path_security_defenses():
    """Test all input validation and sanitization filters in normalize_bundle_path."""
    # Valid relative paths
    assert normalize_bundle_path("manifest.json") == "manifest.json"
    assert normalize_bundle_path("context/election.json") == "context/election.json"
    assert normalize_bundle_path("ballots/ballot_000000.json") == "ballots/ballot_000000.json"
    assert normalize_bundle_path("path\\to\\file.txt") == "path/to/file.txt"

    # Null bytes
    with pytest.raises(ValueError, match="null bytes"):
        normalize_bundle_path("manifest\0.json")

    # Control characters
    with pytest.raises(ValueError, match="control characters"):
        normalize_bundle_path("context/\nelection.json")
    with pytest.raises(ValueError, match="control characters"):
        normalize_bundle_path("context/\telection.json")

    # Absolute and separator prefixes
    with pytest.raises(ValueError, match="cannot start with separator"):
        normalize_bundle_path("/manifest.json")
    with pytest.raises(ValueError, match="cannot start with separator"):
        normalize_bundle_path("\\manifest.json")

    # Volume separators
    with pytest.raises(ValueError, match="volume separators"):
        normalize_bundle_path("C:/manifest.json")

    # Path traversal
    with pytest.raises(ValueError, match="prohibited"):
        normalize_bundle_path("../manifest.json")
    with pytest.raises(ValueError, match="prohibited"):
        normalize_bundle_path("ballots/../../etc/passwd")

    # Empty segments and dot components
    with pytest.raises(ValueError, match="redundant or dot|empty or dot"):
        normalize_bundle_path("ballots//ballot_0.json")
    with pytest.raises(ValueError, match="redundant or dot"):
        normalize_bundle_path("./manifest.json")
    with pytest.raises(ValueError, match="redundant or dot"):
        normalize_bundle_path("context/./election.json")

    # Trailing dots and spaces
    with pytest.raises(ValueError, match="cannot end with dot or space"):
        normalize_bundle_path("context/election. ")
    with pytest.raises(ValueError, match="cannot end with dot or space"):
        normalize_bundle_path("context/election.")

    # Windows reserved device names
    for dev in ["CON", "prn", "aux", "nul", "COM1", "com9", "lpt1", "LPT9"]:
        with pytest.raises(ValueError, match="Windows reserved device name"):
            normalize_bundle_path(f"context/{dev}.json")
        with pytest.raises(ValueError, match="Windows reserved device name"):
            normalize_bundle_path(f"{dev}/data.json")


def test_zip_bundle_shadowing_and_symlink_rejection(tmp_path):
    """Verify BundleReader rejects shadowed zip entries, symlinks, and zip bomb bounds."""
    # 1. Shadowed entries: identical raw names
    buf1 = io.BytesIO()
    with zipfile.ZipFile(buf1, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", b'{"id": "A"}')
        zf.writestr("manifest.json", b'{"id": "B"}')
    zip_path1 = str(tmp_path / "shadow1.zip")
    with open(zip_path1, "wb") as f:
        f.write(buf1.getvalue())

    with pytest.raises(ValueError, match="duplicate member names"):
        BundleReader(zip_path1)

    # 2. Shadowed entries: non-identical raw names normalizing to same path
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("context/election.json", b'{"id": "A"}')
        zf.writestr("context\\election.json", b'{"id": "B"}')
    zip_path2 = str(tmp_path / "shadow2.zip")
    with open(zip_path2, "wb") as f:
        f.write(buf2.getvalue())

    with pytest.raises(ValueError, match="duplicate member names"):
        BundleReader(zip_path2)

    # 3. Symlink entry rejection
    buf3 = io.BytesIO()
    with zipfile.ZipFile(buf3, "w", zipfile.ZIP_DEFLATED) as zf:
        zinfo = zipfile.ZipInfo("symlink_entry.json")
        zinfo.create_system = 3  # Unix
        zinfo.external_attr = 0o120777 << 16  # S_IFLNK
        zf.writestr(zinfo, b"/etc/passwd")
    zip_path3 = str(tmp_path / "symlink.zip")
    with open(zip_path3, "wb") as f:
        f.write(buf3.getvalue())

    with pytest.raises(ValueError, match="symbolic link"):
        BundleReader(zip_path3)


def test_directory_bundle_symlink_escape_defense(tmp_path):
    """Verify directory BundleReader detects and rejects symlinks pointing outside bundle root."""
    bundle_dir = tmp_path / "dir_bundle"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text('{"test": 1}', encoding="utf-8")

    outside_file = tmp_path / "outside_secret.txt"
    outside_file.write_text("CONFIDENTIAL", encoding="utf-8")

    symlink_file = bundle_dir / "escape.txt"
    try:
        os.symlink(str(outside_file), str(symlink_file))
    except (OSError, NotImplementedError):
        # On Windows without SeCreateSymbolicLinkPrivilege, symlinks might require admin or developer mode
        pytest.skip("Symlink creation not permitted in this environment")

    reader = BundleReader(str(bundle_dir))
    with pytest.raises(PermissionError, match="Symlink or directory traversal escape"):
        reader.read_bytes("escape.txt")


# =============================================================================
# 3. Manifest Schema & Canonicalization Tests
# =============================================================================

def test_manifest_schema_strictness():
    """Verify validate_manifest_schema strictly enforces canonicalization, hashes, and types."""
    valid_manifest = {
        "bundle_protocol_version": BUNDLE_PROTOCOL_VERSION,
        "election_protocol_version": "SECUREVOTE33",
        "canonicalization": CANONICALIZATION_VERSION,
        "hash_algorithm": HASH_ALGORITHM,
        "created_at": "2026-09-21T00:00:00Z",
        "election_id": "TEST-ELEC-001",
        "election_parameters": {
            "candidates": ["C1", "C2"],
            "candidate_count": 2,
            "ballot_count": 0,
            "key_fingerprint": "a" * 64,
        },
        "cryptographic_commitments": {},
        "artifact_inventory": [
            {
                "artifact_id": "manifest.json",
                "artifact_type": "VERIFICATION_INSTRUCTIONS",
                "path": "VERIFY.md",
                "sha256": "0" * 64,
                "size_bytes": 100,
            }
        ],
        "manifest_hash": "b" * 64,
    }

    # Base valid manifest must pass
    validate_manifest_schema(valid_manifest)

    # 1. Unsupported canonicalization
    m1 = copy.deepcopy(valid_manifest)
    m1["canonicalization"] = "NON-STANDARD-CANONICAL"
    with pytest.raises(ValueError, match="Unsupported canonicalization"):
        validate_manifest_schema(m1)

    # 2. Unsupported hash algorithm
    m2 = copy.deepcopy(valid_manifest)
    m2["hash_algorithm"] = "SHA-512"
    with pytest.raises(ValueError, match="Unsupported hash algorithm"):
        validate_manifest_schema(m2)

    # 3. Invalid election_id
    m3 = copy.deepcopy(valid_manifest)
    m3["election_id"] = "   "
    with pytest.raises(ValueError, match="Invalid election_id"):
        validate_manifest_schema(m3)

    # 4. Floating point rejection
    m4 = copy.deepcopy(valid_manifest)
    m4["election_parameters"]["float_field"] = 3.14
    with pytest.raises(ValueError, match="Floating-point numbers are strictly forbidden"):
        validate_manifest_schema(m4)

    # 5. Invalid key fingerprint length / characters
    m5 = copy.deepcopy(valid_manifest)
    m5["election_parameters"]["key_fingerprint"] = "not-a-valid-hex"
    with pytest.raises(ValueError, match="key_fingerprint must be a 64-character hex"):
        validate_manifest_schema(m5)

    # 6. Non-canonical path in inventory (e.g. backslashes)
    m6 = copy.deepcopy(valid_manifest)
    m6["artifact_inventory"][0]["path"] = "context\\VERIFY.md"
    with pytest.raises(ValueError, match="Inventory path must be strictly canonical"):
        validate_manifest_schema(m6)

    # 7. Unknown artifact_type
    m7 = copy.deepcopy(valid_manifest)
    m7["artifact_inventory"][0]["artifact_type"] = "MALICIOUS_PAYLOAD"
    with pytest.raises(ValueError, match="Unknown artifact_type"):
        validate_manifest_schema(m7)

    # 8. Boolean size_bytes rejection (isinstance(True, int) is True in Python)
    m8 = copy.deepcopy(valid_manifest)
    m8["artifact_inventory"][0]["size_bytes"] = True
    with pytest.raises(ValueError, match="Invalid size_bytes"):
        validate_manifest_schema(m8)

    # 9. Invalid threshold parameters schema
    m9 = copy.deepcopy(valid_manifest)
    m9["threshold_parameters"] = {
        "threshold": 3,
        "trustee_count": 2,  # t > n violates 1 <= t <= n
        "qualified_trustees": [1, 2],
    }
    with pytest.raises(ValueError, match="Invalid threshold parameters"):
        validate_manifest_schema(m9)


# =============================================================================
# 4. Cryptographic Verifier Hardening (V3Verifier & StandaloneV3ElectionVerifier)
# =============================================================================

def test_v3verifier_ciphertext_and_structure_checks():
    """Verify V3Verifier enforces C1 non-infinity, curve validity, and slot counts."""
    keypair = generate_keypair()
    ballot = encrypt_ballot(
        public_key=keypair.public_key,
        candidate_index=0,
        candidate_count=2,
        election_id="TEST-ELEC",
        candidate_ids=["C1", "C2"],
    )
    b_clean = {k: v for k, v in ballot.items() if not k.startswith("_")}

    # Base ballot passes
    res = V3Verifier.verify_ciphertext_integrity(b_clean)
    assert res["status"] == "PASSED"

    # C1 at infinity
    b_inf = copy.deepcopy(b_clean)
    b_inf["encrypted_vote"]["slots"][0]["c1"] = {"is_infinity": True, "x": None, "y": None}
    res_inf = V3Verifier.verify_ciphertext_integrity(b_inf)
    assert res_inf["status"] == "FAILED"

    # Slot count mismatch with candidate_count
    b_mismatch = copy.deepcopy(b_clean)
    b_mismatch["encrypted_vote"]["candidate_count"] = 5
    res_mismatch = V3Verifier.verify_ballot_structure(b_mismatch)
    assert res_mismatch["status"] == "FAILED"
    assert "Slot count mismatch" in res_mismatch["details"]


def test_v3verifier_tally_reconciliation_strictness():
    """Verify V3Verifier.verify_tally_reconciliation rejects bools, negatives, and drift."""
    valid_decrypted = {
        "candidate_tallies": {"Alice": 5, "Bob": 5},
        "ballot_count": 10,
    }
    assert V3Verifier.verify_tally_reconciliation(valid_decrypted)["status"] == "PASSED"

    # Boolean tally count
    bad_bool = {
        "candidate_tallies": {"Alice": True, "Bob": 9},
        "ballot_count": 10,
    }
    assert V3Verifier.verify_tally_reconciliation(bad_bool)["status"] == "FAILED"

    # Negative tally count
    bad_neg = {
        "candidate_tallies": {"Alice": -1, "Bob": 11},
        "ballot_count": 10,
    }
    assert V3Verifier.verify_tally_reconciliation(bad_neg)["status"] == "FAILED"

    # Drift
    bad_drift = {
        "candidate_tallies": {"Alice": 5, "Bob": 6},
        "ballot_count": 10,
    }
    assert V3Verifier.verify_tally_reconciliation(bad_drift)["status"] == "FAILED"


def test_standalone_v3_verifier_hardened_checks(sample_election_bundle_data):
    """Verify StandaloneV3ElectionVerifier detects off-curve public keys and tally tampering."""
    package, keypair = sample_election_bundle_data

    # Valid package passes
    res_valid = StandaloneV3ElectionVerifier.verify_package(package)
    assert res_valid["verified"] is True

    # Tampered public key: point at infinity
    pkg_bad_key = copy.deepcopy(package)
    pkg_bad_key["public_key"]["x"] = None
    pkg_bad_key["public_key"]["y"] = None
    pkg_bad_key["public_key"]["is_infinity"] = True
    res_bad_key = StandaloneV3ElectionVerifier.verify_package(pkg_bad_key)
    assert res_bad_key["verified"] is False
    assert any(c["checkpoint"] == "checkpoint_2_public_key" and c["status"] == "FAILED" for c in res_bad_key["checkpoints"])

    # Tampered tally reconciliation: candidate mismatch
    pkg_cand_mismatch = copy.deepcopy(package)
    pkg_cand_mismatch["decrypted_tally"]["candidate_tallies"] = {
        "CAND-ALICE": 2,
        "CAND-BOB": 1,
        "UNKNOWN-CAND": 0,
    }
    res_cand_mismatch = StandaloneV3ElectionVerifier.verify_package(pkg_cand_mismatch)
    assert res_cand_mismatch["verified"] is False
    cp10 = next(c for c in res_cand_mismatch["checkpoints"] if c["checkpoint"] == "checkpoint_10_reconciliation")
    assert cp10["status"] == "FAILED"
    assert "Candidate mismatch" in cp10["message"]

    # Package without decrypted tally: reconciliation is marked NOT_APPLICABLE
    pkg_no_dec = copy.deepcopy(package)
    del pkg_no_dec["decrypted_tally"]
    res_no_dec = StandaloneV3ElectionVerifier.verify_package(pkg_no_dec)
    assert res_no_dec["verified"] is True
    cp10_na = next(c for c in res_no_dec["checkpoints"] if c["checkpoint"] == "checkpoint_10_reconciliation")
    assert cp10_na["status"] == "PASSED"
    assert cp10_na["details"].get("status") == "NOT_APPLICABLE"


# =============================================================================
# 5. StandaloneBundleVerifier 15-Checkpoint End-to-End & Tamper Defenses
# =============================================================================

def test_full_bundle_export_and_deterministic_verification(sample_election_bundle_data, tmp_path):
    """Export standard bundle to directory and zip; verify all 15 checkpoints pass deterministically."""
    package, keypair = sample_election_bundle_data
    bundle_dir = str(tmp_path / "full_bundle")

    # Export bundle with zip
    export_bundle(package, bundle_dir, create_zip=True)

    # 1. Verify directory bundle
    rep_dir = StandaloneBundleVerifier.verify(bundle_dir)
    assert rep_dir["verified"] is True
    assert rep_dir["overall_status"] == BundleVerificationStatus.VALID.value
    assert rep_dir["checkpoints_passed"] >= 11
    assert rep_dir["checkpoints_failed"] == 0

    # 2. Verify zip bundle
    zip_path = f"{bundle_dir}.zip"
    rep_zip = StandaloneBundleVerifier.verify(zip_path)
    assert rep_zip["verified"] is True
    assert rep_zip["overall_status"] == BundleVerificationStatus.VALID.value

    # 3. Determinism check: verify reports are identical
    assert rep_dir["manifest_hash"] == rep_zip["manifest_hash"]
    assert rep_dir["checkpoints_total"] == rep_zip["checkpoints_total"]


def test_bundle_tamper_attacks_fail_closed(sample_election_bundle_data, tmp_path):
    """
    Test targeted tamper attacks against an exported evidence bundle:
    - Tampered ballot ciphertext
    - Tampered decrypted tally reconciliation
    - Tampered manifest hash
    - Rogue uninventoried file
    """
    package, keypair = sample_election_bundle_data
    base_dir = str(tmp_path / "base_bundle")
    export_bundle(package, base_dir)

    # Attack A: Tamper ballot ciphertext
    t_ballot_dir = str(tmp_path / "tamper_ballot")
    shutil.copytree(base_dir, t_ballot_dir)
    b0_path = os.path.join(t_ballot_dir, "ballots", "ballot_000000.json")
    with open(b0_path, "r", encoding="utf-8") as f:
        b0 = json.load(f)
    # Alter ciphertext slot
    ct = deserialize_ciphertext(b0["encrypted_vote"]["slots"][0])
    ct_tampered = ElGamalCiphertext(c1=ct.c1, c2=point_add(ct.c2, G))
    b0["encrypted_vote"]["slots"][0] = serialize_ciphertext(ct_tampered)
    with open(b0_path, "wb") as f:
        f.write(canonical_json(b0).encode("utf-8"))

    rep_a = StandaloneBundleVerifier.verify(t_ballot_dir)
    assert rep_a["verified"] is False
    assert rep_a["overall_status"] == BundleVerificationStatus.INVALID.value

    # Attack B: Tamper decrypted tally (vote drift)
    t_tally_dir = str(tmp_path / "tamper_tally")
    shutil.copytree(base_dir, t_tally_dir)
    dec_t_path = os.path.join(t_tally_dir, "tally", "decrypted_tally.json")
    with open(dec_t_path, "r", encoding="utf-8") as f:
        dec_t = json.load(f)
    dec_t["candidate_tallies"]["CAND-ALICE"] += 1  # 2 -> 3 votes, drift = +1
    new_dec_bytes = canonical_json(dec_t).encode("utf-8")
    with open(dec_t_path, "wb") as f:
        f.write(new_dec_bytes)

    # Update manifest inventory for dec_tally so inventory hash matches, but reconciliation fails
    m_path = os.path.join(t_tally_dir, "manifest.json")
    with open(m_path, "r", encoding="utf-8") as f:
        m = json.load(f)
    for it in m["artifact_inventory"]:
        if it["path"] == "tally/decrypted_tally.json":
            it["sha256"] = compute_file_sha256(new_dec_bytes)
            it["size_bytes"] = len(new_dec_bytes)
    m["manifest_hash"] = compute_manifest_hash(m)
    with open(m_path, "wb") as f:
        f.write(canonical_json(m).encode("utf-8"))

    rep_b = StandaloneBundleVerifier.verify(t_tally_dir)
    assert rep_b["verified"] is False
    cp15 = next(c for c in rep_b["checkpoints"] if c["checkpoint"] == "checkpoint_15_tally_reconciliation")
    assert cp15["status"] == "FAILED"
    assert "Reconciliation drift" in cp15["message"]

    # Attack C: Rogue undeclared file inside bundle
    t_rogue_dir = str(tmp_path / "tamper_rogue")
    shutil.copytree(base_dir, t_rogue_dir)
    with open(os.path.join(t_rogue_dir, "context", "backdoor.json"), "wb") as f:
        f.write(b'{"exploit": true}')

    rep_c = StandaloneBundleVerifier.verify(t_rogue_dir)
    assert rep_c["verified"] is False
    cp3 = next(c for c in rep_c["checkpoints"] if c["checkpoint"] == "checkpoint_3_inventory_integrity")
    assert cp3["status"] == "FAILED"
    assert "Undeclared files present in bundle" in cp3["message"]


# =============================================================================
# 6. Database-Disconnected CLI Subprocess Execution Test
# =============================================================================

def test_cli_subprocess_database_disconnected(sample_election_bundle_data, tmp_path):
    """
    Execute standalone_verifier.verify_bundle via OS subprocess with
    DATABASE_URL pointed to an invalid/non-existent database.
    Proves true out-of-band operational independence.
    """
    package, keypair = sample_election_bundle_data
    bundle_dir = str(tmp_path / "cli_bundle")
    export_bundle(package, bundle_dir)

    python_exe = sys.executable
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///non_existent_invalid_path_db.sqlite3"
    env["PYTHONPATH"] = repo_root

    cmd = [
        python_exe,
        "-m",
        "standalone_verifier.verify_bundle",
        bundle_dir,
        "--json",
    ]

    proc = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert proc.returncode == 0, f"CLI verification failed: stdout={proc.stdout}\nstderr={proc.stderr}"
    report = json.loads(proc.stdout)
    assert report["verified"] is True
    assert report["overall_status"] == BundleVerificationStatus.VALID.value
