"""
SecureVOTE 3.0 — Reproducible Cryptographic Election Experiment.

Usage:
    python -m research.v3_experiment --ballots 1000 --seed 42

Performs a full, real execution:
1. Generates and configures a research election
2. Generates cryptographic key material
3. Simulates voter selections using a seeded PRNG
4. One-hot encodes all ballots
5. Exponential ElGamal encrypts all candidate slots
6. Computes domain-separated SHA-256 commitments for all ballots
7. Homomorphically aggregates all ciphertexts
8. Decrypts aggregate tally using private key
9. Validates decrypted results against ground truth
10. Runs the standalone independent verifier across all artifacts
11. Records exact microsecond timings and size measurements
12. Generates an evidence report
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from typing import Any

# Ensure backend modules are on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encrypt_ballot
from app.crypto.keys import (
    compute_key_fingerprint,
    generate_keypair,
    serialize_public_key,
)
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally
from standalone_verifier.v3_verifier import StandaloneV3ElectionVerifier


def run_experiment(ballots_count: int, seed: int, output_file: str | None = None) -> dict[str, Any]:
    """Run an end-to-end reproducible election experiment."""
    random.seed(seed)
    experiment_start = time.perf_counter()

    election_id = f"EXP-{seed}-{ballots_count}"
    candidates = ["CAND-A", "CAND-B", "CAND-C", "NOTA"]
    candidate_count = len(candidates)

    print(f"\n========================================================")
    print(f"SecureVOTE 3.0 Cryptographic Experiment")
    print(f"Election: {election_id} | Ballots: {ballots_count} | Seed: {seed}")
    print(f"========================================================")

    # Step 1 & 2: Key Generation
    t0 = time.perf_counter()
    keypair = generate_keypair()
    t_keygen = time.perf_counter() - t0
    pub_data = serialize_public_key(keypair.public_key)
    key_fp = compute_key_fingerprint(keypair.public_key)
    print(f"[1/6] Key generation completed in {t_keygen*1000:.2f} ms")
    print(f"      Public key fingerprint: {key_fp}")

    # Step 3, 4, 5, 6: Generate, Encode, Encrypt & Commit Ballots
    print(f"[2/6] Generating and encrypting {ballots_count} ballots...")
    ground_truth = {c: 0 for c in candidates}
    ballots = []

    t0 = time.perf_counter()
    for i in range(ballots_count):
        # Choose candidate according to non-uniform distribution
        # e.g., 40% A, 30% B, 20% C, 10% NOTA
        r = random.random()
        if r < 0.40:
            c_idx = 0
        elif r < 0.70:
            c_idx = 1
        elif r < 0.90:
            c_idx = 2
        else:
            c_idx = 3

        ground_truth[candidates[c_idx]] += 1

        b = encrypt_ballot(
            public_key=keypair.public_key,
            candidate_index=c_idx,
            candidate_count=candidate_count,
            election_id=election_id,
            candidate_ids=candidates,
        )
        ballots.append(b)
    t_encryption = time.perf_counter() - t0
    throughput = ballots_count / t_encryption if t_encryption > 0 else 0
    print(f"      Encryption completed in {t_encryption:.3f} s ({throughput:.1f} ballots/sec)")

    # Step 7: Homomorphic Aggregation
    print(f"[3/6] Homomorphically aggregating {ballots_count} encrypted ballots...")
    t0 = time.perf_counter()
    encrypted_tally = aggregate_encrypted_ballots(ballots, election_id, key_fp)
    t_aggregation = time.perf_counter() - t0
    print(f"      Aggregation completed in {t_aggregation*1000:.2f} ms")

    # Step 8: Decrypt Tally
    print(f"[4/6] Decrypting aggregate tally using election private key...")
    t0 = time.perf_counter()
    decrypted_tally = decrypt_tally(keypair, encrypted_tally, max_ballots=ballots_count + 1000)
    t_decryption = time.perf_counter() - t0
    print(f"      Decryption completed in {t_decryption*1000:.2f} ms")

    # Step 9: Ground Truth Comparison
    candidate_tallies = decrypted_tally["candidate_tallies"]
    ground_truth_match = (candidate_tallies == ground_truth)
    total_votes = sum(candidate_tallies.values())
    balanced = (total_votes == ballots_count)

    print(f"\n[5/6] Ground Truth Comparison:")
    print(f"      Candidate    | Ground Truth | Decrypted Tally | Match")
    print(f"      -------------+--------------+-----------------+------")
    for c in candidates:
        match_str = "YES" if candidate_tallies[c] == ground_truth[c] else "MISMATCH!"
        print(f"      {c:<12} | {ground_truth[c]:<12} | {candidate_tallies[c]:<15} | {match_str}")
    print(f"      Total Ballots: {total_votes} / {ballots_count} (Balanced: {balanced})")

    if not ground_truth_match:
        raise RuntimeError("CRITICAL: Ground truth does NOT match decrypted tally!")

    # Step 10: Standalone Independent Verification
    print(f"\n[6/6] Executing independent standalone verification...")
    package = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "public_key": pub_data,
        "candidates": candidates,
        "ballots": ballots,
        "encrypted_tally": encrypted_tally,
        "decrypted_tally": decrypted_tally,
    }

    t0 = time.perf_counter()
    verification_result = StandaloneV3ElectionVerifier.verify_package(package, keypair)
    t_verification = time.perf_counter() - t0
    print(f"      Verification: {verification_result['checkpoints_passed']}/{verification_result['checkpoints_total']} checkpoints PASSED ({t_verification:.3f} s)")

    total_experiment_time = time.perf_counter() - experiment_start

    # Size measurements
    single_ballot_bytes = len(json.dumps(ballots[0]))
    all_ballots_bytes = sum(len(json.dumps(b)) for b in ballots)
    tally_bytes = len(json.dumps(encrypted_tally))

    report = {
        "experiment_id": election_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "protocol_version": PROTOCOL_VERSION,
        "parameters": {
            "ballots": ballots_count,
            "seed": seed,
            "candidates": candidates,
            "curve": "secp256r1",
        },
        "ground_truth": ground_truth,
        "decrypted_tally": candidate_tallies,
        "reconciliation": {
            "total_ballots": total_votes,
            "ground_truth_match": ground_truth_match,
            "balanced": balanced,
        },
        "performance_timings": {
            "key_generation_seconds": round(t_keygen, 6),
            "encryption_seconds": round(t_encryption, 6),
            "encryption_throughput_per_sec": round(throughput, 2),
            "aggregation_seconds": round(t_aggregation, 6),
            "decryption_seconds": round(t_decryption, 6),
            "verification_seconds": round(t_verification, 6),
            "total_experiment_seconds": round(total_experiment_time, 4),
        },
        "size_metrics": {
            "single_ballot_json_bytes": single_ballot_bytes,
            "all_ballots_json_bytes": all_ballots_bytes,
            "aggregate_tally_json_bytes": tally_bytes,
        },
        "verification": {
            "verified": verification_result["verified"],
            "checkpoints_passed": verification_result["checkpoints_passed"],
            "checkpoints_total": verification_result["checkpoints_total"],
            "checkpoints": verification_result["checkpoints"],
        },
    }

    if output_file:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to: {output_file}")

    print(f"\n========================================================")
    print(f"EXPERIMENT RESULT: {'SUCCESS (100% VERIFIED)' if verification_result['verified'] else 'FAILED'}")
    print(f"Total Elapsed Time: {total_experiment_time:.2f} s")
    print(f"========================================================\n")

    return report


def main():
    parser = argparse.ArgumentParser(description="SecureVOTE 3.0 Cryptographic Experiment Runner")
    parser.add_argument("--ballots", type=int, default=1000, help="Number of simulated ballots (default: 1000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--out", type=str, default=None, help="Path to write JSON experiment report")
    args = parser.parse_args()

    run_experiment(ballots_count=args.ballots, seed=args.seed, output_file=args.out)


if __name__ == "__main__":
    main()
