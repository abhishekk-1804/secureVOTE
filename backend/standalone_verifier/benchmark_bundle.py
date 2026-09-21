"""
SecureVOTE 3.3 Phase 2 — Empirical Bundle Benchmark Harness.

Measures empirical performance across multiple bundle tiers (small, medium, large):
- Export time (ms)
- Manifest generation time (ms)
- Manifest verification time (ms)
- Artifact SHA-256 hashing time (ms)
- Ed25519 signature verification time (ms)
- Cryptographic verification time (ms, across ZK proofs, threshold DKG, Chaum-Pedersen proofs, Lagrange combinations, and tally recovery)
- Total standalone verification time (ms)
- Bundle directory size on disk (bytes)
- Manifest size (bytes)

All metrics are measured empirically across multiple trials (mean, min, max, stddev).
Results are output to stdout and written to docs/research/evidence/phase2_bundle_benchmarks.json.
"""

import copy
import json
import math
import os
import platform
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encrypt_ballot
from app.crypto.canonical import canonical_json
from app.crypto.commitment import compute_ballot_commitment
from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    ElGamalCiphertext,
    ElGamalPublicKey,
    add_ciphertexts,
    generate_keypair,
    point_add,
)
from app.crypto.keys import compute_key_fingerprint, serialize_public_key
from app.crypto.serialization import serialize_ciphertext
from app.crypto.tally import aggregate_encrypted_ballots
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
from standalone_verifier.bundle import (
    BUNDLE_PROTOCOL_VERSION,
    CANONICALIZATION_VERSION,
    compute_file_sha256,
    compute_manifest_hash,
    validate_manifest_schema,
)
from standalone_verifier.bundle_export import export_bundle
from standalone_verifier.bundle_verifier import BundleReader, StandaloneBundleVerifier


def get_git_commit() -> str:
    """Retrieve current git commit hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN"


def generate_benchmark_package(
    num_ballots: int,
    candidate_ids: List[str],
    threshold: int = 2,
    total_trustees: int = 3,
) -> Dict[str, Any]:
    """Generate a complete, verifiable threshold election package with real proofs."""
    election_id = f"BENCH-ELEC-N{num_ballots}-C{len(candidate_ids)}"
    candidate_count = len(candidate_ids)

    # 1. DKG across trustees
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
    key_shares = {s.trustee_id: s.finalize_secret_share(qual, feldman_pkgs, pedersen_pkgs) for s in sessions}

    manifest = build_dkg_manifest(election_id, threshold, total_trustees, qual, pedersen_pkgs, feldman_pkgs)
    joint_pubkey = ElGamalPublicKey(point=manifest.joint_public_key)
    pub_data = serialize_public_key(joint_pubkey)

    # 2. Encrypt ballots with ZK validity proofs
    ballots = []
    for i in range(num_ballots):
        c_idx = i % candidate_count
        b = encrypt_ballot(
            public_key=joint_pubkey,
            candidate_index=c_idx,
            candidate_count=candidate_count,
            election_id=election_id,
            candidate_ids=candidate_ids,
            with_zkp=True,
        )
        ballots.append(b)

    key_fp = compute_key_fingerprint(joint_pubkey)
    encrypted_tally = aggregate_encrypted_ballots(ballots, election_id, key_fp)

    # 3. Compute partial decryptions for threshold trustees (trustees 1..threshold)
    tally_slots = encrypted_tally["encrypted_tally"]["slots"]
    candidate_a_points = {}
    for j, cid in enumerate(candidate_ids):
        candidate_a_points[cid] = ECPoint(
            int(tally_slots[j]["c1"]["x"], 16),
            int(tally_slots[j]["c1"]["y"], 16),
        )

    trustee_packages = {}
    for t_id in range(1, threshold + 1):
        pkg = compute_tally_partial_decryptions(key_shares[t_id], candidate_a_points)
        trustee_packages[t_id] = pkg

    # 4. Reconstruct threshold tally
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


def compute_stats(values: List[float]) -> Dict[str, float]:
    """Calculate mean, min, max, and stddev."""
    if not values:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "stddev": 0.0}
    n = len(values)
    mean_val = sum(values) / n
    min_val = min(values)
    max_val = max(values)
    if n > 1:
        variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0
    return {
        "mean": round(mean_val, 3),
        "min": round(min_val, 3),
        "max": round(max_val, 3),
        "stddev": round(stddev, 3),
    }


def benchmark_tier(
    name: str,
    num_ballots: int,
    candidates: List[str],
    num_trials: int = 5,
) -> Dict[str, Any]:
    """Benchmark export and verification across a specific tier."""
    print(f"\n--- Benchmarking Tier: {name.upper()} ({num_ballots} ballots, {len(candidates)} candidates, {num_trials} trials) ---")
    print(f"Generating test election package with real cryptographic proofs...")
    t_gen_0 = time.perf_counter()
    pkg = generate_benchmark_package(num_ballots, candidates)
    t_gen = (time.perf_counter() - t_gen_0) * 1000.0
    print(f"Package generation completed in {t_gen:.2f} ms")

    # Generate Ed25519 signing keypair
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
    signing_priv_hex = priv_bytes.hex()
    signing_pub_hex = pub_bytes.hex()

    export_times = []
    manifest_gen_times = []
    manifest_verify_times = []
    sha256_times = []
    ed25519_verify_times = []
    crypto_verify_times = []
    total_verify_times = []
    bundle_sizes = []
    manifest_sizes = []

    for trial in range(1, num_trials + 1):
        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle_dir = os.path.join(tmp_dir, f"bundle_{name}_{trial}")

            # 1. Export bundle & measure export time
            t0 = time.perf_counter()
            manifest_info = export_bundle(
                package=pkg,
                output_dir=bundle_dir,
                signing_private_key_hex=signing_priv_hex,
                create_zip=False,
            )
            t_export = (time.perf_counter() - t0) * 1000.0
            export_times.append(t_export)

            # 2. Measure manifest generation time (manifest re-hash and canonicalization)
            manifest_path = os.path.join(bundle_dir, "manifest.json")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            t0 = time.perf_counter()
            computed_m_hash = compute_manifest_hash(manifest_data)
            t_mgen = (time.perf_counter() - t0) * 1000.0
            manifest_gen_times.append(t_mgen)

            # Measure manifest size and bundle directory size
            manifest_size = os.path.getsize(manifest_path)
            manifest_sizes.append(manifest_size)

            total_bundle_size = sum(
                os.path.getsize(os.path.join(root, file))
                for root, _, files in os.walk(bundle_dir)
                for file in files
            )
            bundle_sizes.append(total_bundle_size)

            # 3. Fine-grained verification measurements
            reader = BundleReader(bundle_dir)

            # (a) Manifest verification time (Checkpoint 1 + 2)
            t0 = time.perf_counter()
            validate_manifest_schema(manifest_data)
            computed_hash_v = compute_manifest_hash(manifest_data)
            assert computed_hash_v == manifest_data["manifest_hash"]
            t_mverify = (time.perf_counter() - t0) * 1000.0
            manifest_verify_times.append(t_mverify)

            # (b) Artifact SHA-256 hashing time (Checkpoint 3)
            inventory = manifest_data.get("artifact_inventory", [])
            t0 = time.perf_counter()
            for item in inventory:
                b = reader.read_bytes(item["path"])
                s = compute_file_sha256(b)
                assert s == item["sha256"]
            t_sha = (time.perf_counter() - t0) * 1000.0
            sha256_times.append(t_sha)

            # (c) Ed25519 signature verification time (Checkpoint 4)
            sig_data = json.loads(reader.read_bytes("signatures/manifest.sig.json").decode("utf-8"))
            t0 = time.perf_counter()
            ed_pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(sig_data["public_key"]))
            ed_pub.verify(
                bytes.fromhex(sig_data["signature"]),
                manifest_data["manifest_hash"].encode("utf-8"),
            )
            t_ed = (time.perf_counter() - t0) * 1000.0
            ed25519_verify_times.append(t_ed)

            # (d) Standalone full verification time (all 15 checkpoints)
            t0 = time.perf_counter()
            report = StandaloneBundleVerifier.verify(
                bundle_dir,
                trusted_signing_public_key_hex=signing_pub_hex,
            )
            t_total_verify = (time.perf_counter() - t0) * 1000.0
            total_verify_times.append(t_total_verify)
            assert report["overall_status"] == "VALID", f"Verification failed: {report}"

            # (e) Cryptographic verification time:
            # Checkpoints 7-15 time = total verification time - (manifest check + sha256 check + sig check)
            # Or measured directly. Since reader caching is minimal, t_total_verify - (t_mverify + t_sha + t_ed)
            # represents crypto operations (ZKP, aggregation, threshold, lagrange, discrete log, reconciliation).
            t_crypto = max(0.0, t_total_verify - (t_mverify + t_sha + t_ed))
            crypto_verify_times.append(t_crypto)

            print(f"  Trial {trial}/{num_trials}: Export={t_export:.2f}ms, Verify={t_total_verify:.2f}ms (Crypto={t_crypto:.2f}ms, SHA256={t_sha:.2f}ms)")

    result = {
        "tier": name,
        "ballot_count": num_ballots,
        "candidate_count": len(candidates),
        "trials": num_trials,
        "package_generation_time_ms": round(t_gen, 2),
        "bundle_directory_size_bytes": {
            "mean": int(sum(bundle_sizes) / len(bundle_sizes)),
            "min": min(bundle_sizes),
            "max": max(bundle_sizes),
        },
        "manifest_size_bytes": {
            "mean": int(sum(manifest_sizes) / len(manifest_sizes)),
            "min": min(manifest_sizes),
            "max": max(manifest_sizes),
        },
        "metrics_ms": {
            "export_time": compute_stats(export_times),
            "manifest_generation_time": compute_stats(manifest_gen_times),
            "manifest_verification_time": compute_stats(manifest_verify_times),
            "artifact_sha256_hashing_time": compute_stats(sha256_times),
            "ed25519_signature_verification_time": compute_stats(ed25519_verify_times),
            "cryptographic_verification_time": compute_stats(crypto_verify_times),
            "total_standalone_verification_time": compute_stats(total_verify_times),
        },
    }
    return result


def run_all_benchmarks() -> Dict[str, Any]:
    """Execute benchmarks across all three tiers and save machine-readable results."""
    print("================================================================================")
    print("SecureVOTE 3.3 Phase 2 — Empirical Evidence Bundle Benchmark Harness")
    print("================================================================================")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Python:    {platform.python_version()} ({platform.python_implementation()})")
    print(f"Platform:  {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Git Commit: {get_git_commit()}")
    print("================================================================================")

    tiers = [
        ("small", 10, ["CAND-A", "CAND-B", "CAND-C"], 5),
        ("medium", 50, ["CAND-A", "CAND-B", "CAND-C", "NOTA"], 5),
        ("large", 100, ["CAND-A", "CAND-B", "CAND-C", "NOTA"], 5),
    ]

    tier_results = []
    for name, num_ballots, candidates, trials in tiers:
        res = benchmark_tier(name, num_ballots, candidates, num_trials=trials)
        tier_results.append(res)

    output_payload = {
        "benchmark_metadata": {
            "protocol_version": BUNDLE_PROTOCOL_VERSION,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": get_git_commit(),
            "environment": {
                "os": platform.system(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
            },
        },
        "tiers": tier_results,
    }

    # Print summary table
    print("\n=======================================================================================")
    print("PHASE 2 EMPIRICAL BENCHMARK SUMMARY TABLE")
    print("=======================================================================================")
    header = (
        f"{'Tier':<8} | {'Ballots':<7} | {'Export (ms)':<12} | {'Manifest (ms)':<13} | "
        f"{'SHA-256 (ms)':<12} | {'Crypto (ms)':<12} | {'Total Verify (ms)':<17} | {'Size (KB)':<9}"
    )
    print(header)
    print("-" * len(header))
    for t in tier_results:
        m = t["metrics_ms"]
        size_kb = t["bundle_directory_size_bytes"]["mean"] / 1024.0
        row = (
            f"{t['tier']:<8} | {t['ballot_count']:<7} | "
            f"{m['export_time']['mean']:>8.2f} ms | "
            f"{m['manifest_verification_time']['mean']:>9.2f} ms | "
            f"{m['artifact_sha256_hashing_time']['mean']:>8.2f} ms | "
            f"{m['cryptographic_verification_time']['mean']:>8.2f} ms | "
            f"{m['total_standalone_verification_time']['mean']:>13.2f} ms | "
            f"{size_kb:>7.1f} KB"
        )
        print(row)
    print("=======================================================================================")

    # Save to docs/research/evidence/phase2_bundle_benchmarks.json
    output_dir = Path("..") / "docs" / "research" / "evidence"
    if not output_dir.exists():
        # Try from current directory
        if Path("docs/research").exists():
            output_dir = Path("docs/research/evidence")
        elif Path("../docs/research").exists():
            output_dir = Path("../docs/research/evidence")
        else:
            output_dir = Path("docs/research/evidence")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "phase2_bundle_benchmarks.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print(f"\nSaved empirical benchmark results to: {out_file.resolve()}\n")
    return output_payload


if __name__ == "__main__":
    run_all_benchmarks()
