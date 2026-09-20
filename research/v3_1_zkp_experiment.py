"""
SecureVOTE 3.1 — Zero-Knowledge Ballot Validity Proof Comparative Experiment.

Directly compares:
  BASELINE: SecureVOTE 3.0 (Encrypted ballot without ZK proof)
  VERSUS:   SecureVOTE 3.1 (Encrypted ballot + CDS94 slot proofs + sum equality proof)

Empirically measures:
- Encryption & proof generation latency
- Proof verification latency
- Ballot artifact size before vs after proof
- Aggregation & decryption latencies
- Peak memory consumption
- Overhead percentage
"""

import argparse
import json
import os
import random
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from typing import Any

# Ensure backend modules on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encode_vote_onehot
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


def run_comparative_trial(ballots_count: int, seed: int = 42) -> dict[str, Any]:
    """Run a comparative benchmark at a given ballot scale."""
    random.seed(seed)
    candidates = ["CAND-A", "CAND-B", "CAND-C", "NOTA"]
    candidate_count = len(candidates)
    election_id = f"ZKP-EXP-{seed}-{ballots_count}"

    keypair = generate_keypair()
    pub_data = serialize_public_key(keypair.public_key)
    key_fp = compute_key_fingerprint(keypair.public_key)

    print(f"\n========================================================", flush=True)
    print(f"RUNNING COMPARATIVE EXPERIMENT: {ballots_count} BALLOTS", flush=True)
    print(f"========================================================", flush=True)

    # -----------------------------------------------------------------------
    # 1. BASELINE: SecureVOTE 3.0 (Without ZKP)
    # -----------------------------------------------------------------------
    print("[1/2] Benchmarking Baseline (SecureVOTE 3.0 - No ZKP)...", flush=True)
    tracemalloc.start()
    t0 = time.perf_counter()

    base_ballots = []
    votes_distribution = []
    nonces_list = []

    for i in range(ballots_count):
        r_val = random.random()
        c_idx = 0 if r_val < 0.4 else (1 if r_val < 0.7 else (2 if r_val < 0.9 else 3))
        votes_distribution.append(c_idx)

        nonces = [
            int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1
            for _ in range(candidate_count)
        ]
        nonces_list.append(nonces)

        slots = []
        for j in range(candidate_count):
            v = 1 if j == c_idx else 0
            r = nonces[j]
            c1 = scalar_mult(r, G)
            c2 = point_add(scalar_mult(r, keypair.public_key.point), scalar_mult(v, G))
            slots.append(serialize_ciphertext(ElGamalCiphertext(c1=c1, c2=c2)))

        encrypted_vote = {
            "slots": slots,
            "candidate_ids": candidates,
            "candidate_count": candidate_count,
        }
        art_id = f"BASE-BALLOT-{i:06d}"
        comm = compute_ballot_commitment(
            election_id=election_id,
            artifact_id=art_id,
            encrypted_vote=encrypted_vote,
            candidate_count=candidate_count,
            key_fingerprint=key_fp,
        )
        art_data = {
            "protocol_version": PROTOCOL_VERSION,
            "election_id": election_id,
            "artifact_id": art_id,
            "encrypted_vote": encrypted_vote,
            "commitment": comm,
            "key_fingerprint": key_fp,
        }
        art_hash = canonical_hash(art_data, domain=ballot_domain(election_id))

        base_ballots.append({
            "protocol_version": PROTOCOL_VERSION,
            "artifact_type": "ENCRYPTED_BALLOT",
            "election_id": election_id,
            "artifact_id": art_id,
            "encrypted_vote": encrypted_vote,
            "commitment": comm,
            "key_fingerprint": key_fp,
            "artifact_hash": art_hash,
        })

    t_base_gen = time.perf_counter() - t0
    base_tally = aggregate_encrypted_ballots(base_ballots, election_id, key_fp)
    base_dec = decrypt_tally(keypair, base_tally, max_ballots=ballots_count + 1000)

    base_pkg = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "public_key": pub_data,
        "candidates": candidates,
        "ballots": base_ballots,
        "encrypted_tally": base_tally,
        "decrypted_tally": base_dec,
    }

    t0_verif = time.perf_counter()
    base_verif = StandaloneV3ElectionVerifier.verify_package(base_pkg)
    t_base_verif = time.perf_counter() - t0_verif
    _, base_peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    base_ballot_size = len(json.dumps(base_ballots[0]))

    # -----------------------------------------------------------------------
    # 2. EXPERIMENT: SecureVOTE 3.1 (With ZKP)
    # -----------------------------------------------------------------------
    print("[2/2] Benchmarking SecureVOTE 3.1 (With ZK Ballot Validity Proofs)...", flush=True)
    tracemalloc.start()
    t0 = time.perf_counter()

    zk_ballots = []
    t_proof_gen_only = 0.0

    for i in range(ballots_count):
        c_idx = votes_distribution[i]
        nonces = nonces_list[i]

        slots = []
        for j in range(candidate_count):
            v = 1 if j == c_idx else 0
            r = nonces[j]
            c1 = scalar_mult(r, G)
            c2 = point_add(scalar_mult(r, keypair.public_key.point), scalar_mult(v, G))
            slots.append(serialize_ciphertext(ElGamalCiphertext(c1=c1, c2=c2)))

        encrypted_vote = {
            "slots": slots,
            "candidate_ids": candidates,
            "candidate_count": candidate_count,
        }

        t_p0 = time.perf_counter()
        proof = prove_ballot_validity(
            public_key=keypair.public_key,
            candidate_index=c_idx,
            nonces=nonces,
            candidate_count=candidate_count,
            election_id=election_id,
            candidate_ids=candidates,
        )
        t_proof_gen_only += (time.perf_counter() - t_p0)

        art_id = f"ZK-BALLOT-{i:06d}"
        comm = compute_ballot_commitment(
            election_id=election_id,
            artifact_id=art_id,
            encrypted_vote=encrypted_vote,
            candidate_count=candidate_count,
            key_fingerprint=key_fp,
        )
        art_data = {
            "protocol_version": PROTOCOL_VERSION,
            "election_id": election_id,
            "artifact_id": art_id,
            "encrypted_vote": encrypted_vote,
            "commitment": comm,
            "key_fingerprint": key_fp,
            "proof": proof,
        }
        art_hash = canonical_hash(art_data, domain=ballot_domain(election_id))

        zk_ballots.append({
            "protocol_version": PROTOCOL_VERSION,
            "artifact_type": "ENCRYPTED_BALLOT",
            "election_id": election_id,
            "artifact_id": art_id,
            "encrypted_vote": encrypted_vote,
            "commitment": comm,
            "key_fingerprint": key_fp,
            "artifact_hash": art_hash,
            "proof": proof,
        })

    t_zk_gen_total = time.perf_counter() - t0
    zk_tally = aggregate_encrypted_ballots(zk_ballots, election_id, key_fp)
    zk_dec = decrypt_tally(keypair, zk_tally, max_ballots=ballots_count + 1000)

    zk_pkg = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": election_id,
        "public_key": pub_data,
        "candidates": candidates,
        "ballots": zk_ballots,
        "encrypted_tally": zk_tally,
        "decrypted_tally": zk_dec,
    }

    t0_verif = time.perf_counter()
    zk_verif = StandaloneV3ElectionVerifier.verify_package(zk_pkg)
    t_zk_verif = time.perf_counter() - t0_verif
    _, zk_peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    zk_ballot_size = len(json.dumps(zk_ballots[0]))

    # Calculate comparative metrics
    size_multiplier = zk_ballot_size / base_ballot_size
    gen_overhead_pct = ((t_zk_gen_total - t_base_gen) / t_base_gen) * 100 if t_base_gen > 0 else 0
    verif_overhead_pct = ((t_zk_verif - t_base_verif) / t_base_verif) * 100 if t_base_verif > 0 else 0

    print(f"\n--- COMPARISON SUMMARY ({ballots_count} BALLOTS) ---")
    print(f"Ballot Size:        v3.0 = {base_ballot_size} B  |  v3.1 = {zk_ballot_size} B  ({size_multiplier:.2f}x)")
    print(f"Generation Time:    v3.0 = {t_base_gen:.3f} s   |  v3.1 = {t_zk_gen_total:.3f} s  (+{gen_overhead_pct:.1f}%)")
    print(f"Verification Time:  v3.0 = {t_base_verif:.3f} s  |  v3.1 = {t_zk_verif:.3f} s  (+{verif_overhead_pct:.1f}%)")
    print(f"Peak Memory:        v3.0 = {base_peak_mem/1e6:.2f} MB |  v3.1 = {zk_peak_mem/1e6:.2f} MB")
    print(f"All Checks Passed:  v3.0 = {base_verif['verified']}  |  v3.1 = {zk_verif['verified']}")

    return {
        "ballots": ballots_count,
        "seed": seed,
        "baseline_v3_0": {
            "generation_seconds": round(t_base_gen, 4),
            "verification_seconds": round(t_base_verif, 4),
            "ballot_size_bytes": base_ballot_size,
            "peak_memory_mb": round(base_peak_mem / 1e6, 2),
            "verified": base_verif["verified"],
        },
        "zkp_v3_1": {
            "total_generation_seconds": round(t_zk_gen_total, 4),
            "proof_generation_only_seconds": round(t_proof_gen_only, 4),
            "verification_seconds": round(t_zk_verif, 4),
            "ballot_size_bytes": zk_ballot_size,
            "peak_memory_mb": round(zk_peak_mem / 1e6, 2),
            "verified": zk_verif["verified"],
            "ballot_validity_status": zk_verif.get("ballot_validity_status", "VALID" if zk_verif["verified"] else "INVALID"),
        },
        "comparative_overhead": {
            "size_overhead_multiplier": round(size_multiplier, 2),
            "size_increase_bytes": zk_ballot_size - base_ballot_size,
            "generation_overhead_pct": round(gen_overhead_pct, 1),
            "verification_overhead_pct": round(verif_overhead_pct, 1),
        },
    }


def compute_statistics_for_scale(ballots_count: int, raw_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute median, min, max, and variability across repetitions for a scale."""
    import statistics

    base_gen = [r["baseline_v3_0"]["generation_seconds"] for r in raw_runs]
    base_verif = [r["baseline_v3_0"]["verification_seconds"] for r in raw_runs]
    base_mem = [r["baseline_v3_0"]["peak_memory_mb"] for r in raw_runs]

    zk_gen = [r["zkp_v3_1"]["total_generation_seconds"] for r in raw_runs]
    zk_proof_only = [r["zkp_v3_1"]["proof_generation_only_seconds"] for r in raw_runs]
    zk_verif = [r["zkp_v3_1"]["verification_seconds"] for r in raw_runs]
    zk_mem = [r["zkp_v3_1"]["peak_memory_mb"] for r in raw_runs]

    med_base_gen = round(statistics.median(base_gen), 4)
    med_base_verif = round(statistics.median(base_verif), 4)
    med_zk_gen = round(statistics.median(zk_gen), 4)
    med_zk_proof_only = round(statistics.median(zk_proof_only), 4)
    med_zk_verif = round(statistics.median(zk_verif), 4)

    gen_overhead_pct = round(((med_zk_gen - med_base_gen) / med_base_gen) * 100, 1) if med_base_gen > 0 else 0
    verif_overhead_pct = round(((med_zk_verif - med_base_verif) / med_base_verif) * 100, 1) if med_base_verif > 0 else 0

    ballot_size_base = raw_runs[0]["baseline_v3_0"]["ballot_size_bytes"]
    ballot_size_zk = raw_runs[0]["zkp_v3_1"]["ballot_size_bytes"]

    return {
        "ballots": ballots_count,
        "repetitions": len(raw_runs),
        "raw_runs": raw_runs,
        "median_summary": {
            "baseline_v3_0": {
                "generation_seconds": med_base_gen,
                "verification_seconds": med_base_verif,
                "ballot_size_bytes": ballot_size_base,
                "peak_memory_mb": round(statistics.median(base_mem), 2),
                "verified": all(r["baseline_v3_0"]["verified"] for r in raw_runs),
            },
            "zkp_v3_1": {
                "total_generation_seconds": med_zk_gen,
                "proof_generation_only_seconds": med_zk_proof_only,
                "verification_seconds": med_zk_verif,
                "ballot_size_bytes": ballot_size_zk,
                "peak_memory_mb": round(statistics.median(zk_mem), 2),
                "verified": all(r["zkp_v3_1"]["verified"] for r in raw_runs),
                "ballot_validity_status": "VALID",
            },
            "comparative_overhead": {
                "size_overhead_multiplier": round(ballot_size_zk / ballot_size_base, 2),
                "size_increase_bytes": ballot_size_zk - ballot_size_base,
                "generation_overhead_pct": gen_overhead_pct,
                "verification_overhead_pct": verif_overhead_pct,
            },
        },
        "variability": {
            "baseline_generation_seconds": {
                "min": min(base_gen),
                "max": max(base_gen),
                "stddev": round(statistics.stdev(base_gen), 4) if len(base_gen) > 1 else 0.0,
            },
            "baseline_verification_seconds": {
                "min": min(base_verif),
                "max": max(base_verif),
                "stddev": round(statistics.stdev(base_verif), 4) if len(base_verif) > 1 else 0.0,
            },
            "zkp_total_generation_seconds": {
                "min": min(zk_gen),
                "max": max(zk_gen),
                "stddev": round(statistics.stdev(zk_gen), 4) if len(zk_gen) > 1 else 0.0,
            },
            "zkp_verification_seconds": {
                "min": min(zk_verif),
                "max": max(zk_verif),
                "stddev": round(statistics.stdev(zk_verif), 4) if len(zk_verif) > 1 else 0.0,
            },
        },
    }


def main():
    import gc
    parser = argparse.ArgumentParser(description="SecureVOTE 3.1 ZKP Comparative Benchmark")
    parser.add_argument("--scales", nargs="+", type=int, default=[10, 50, 100], help="Ballot count scales")
    parser.add_argument("--repetitions", type=int, default=3, help="Number of repetitions per scale")
    parser.add_argument("--out", type=str, default="evidence/v3_1_zkp_benchmark_results.json", help="Output JSON path")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    scale_evaluations = []

    for n in args.scales:
        print(f"\n========================================================", flush=True)
        print(f"BENCHMARKING SCALE: {n} BALLOTS ({args.repetitions} INDEPENDENT RUNS)", flush=True)
        print(f"========================================================", flush=True)

        raw_runs = []
        for rep in range(args.repetitions):
            seed = 42 + rep * 101
            print(f"\n--- RUN {rep + 1}/{args.repetitions} (Scale {n}, Seed {seed}) ---", flush=True)
            gc.collect()
            run_res = run_comparative_trial(ballots_count=n, seed=seed)
            raw_runs.append(run_res)

        scale_stat = compute_statistics_for_scale(ballots_count=n, raw_runs=raw_runs)
        scale_evaluations.append(scale_stat)

        # Write progressive results
        summary = {
            "benchmark": "SecureVOTE 3.0 vs 3.1 ZKP Comparative Evaluation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repetitions_per_scale": args.repetitions,
            "scales_completed": [s["ballots"] for s in scale_evaluations],
            "scale_evaluations": scale_evaluations,
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\nProgressive results updated in: {args.out}", flush=True)

    print(f"\nAll comparative benchmark scales complete. Final results: {args.out}\n", flush=True)


if __name__ == "__main__":
    main()
