"""
SecureVOTE 3.0 — Cryptographic Benchmark Suite.

Benchmarks the cryptographic pipeline across election scales:
- 10 ballots
- 100 ballots
- 1,000 ballots
- 5,000 ballots

Captures exact empirical measurements:
- Key generation time
- Ballot encryption time & throughput (ballots/sec)
- Ciphertext slot sizes
- Homomorphic aggregation time
- Decryption time (discrete log recovery)
- Independent verifier duration
- Peak memory usage
"""

import argparse
import json
import os
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from typing import Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from research.v3_experiment import run_experiment


def benchmark_scale(ballots: int, seed: int = 42) -> dict[str, Any]:
    """Execute a full benchmark run at a given scale with memory tracing."""
    tracemalloc.start()
    report = run_experiment(ballots_count=ballots, seed=seed)
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    timings = report["performance_timings"]
    sizes = report["size_metrics"]

    return {
        "ballots": ballots,
        "keygen_ms": round(timings["key_generation_seconds"] * 1000, 2),
        "encryption_seconds": timings["encryption_seconds"],
        "throughput_ballots_per_sec": timings["encryption_throughput_per_sec"],
        "aggregation_ms": round(timings["aggregation_seconds"] * 1000, 2),
        "decryption_ms": round(timings["decryption_seconds"] * 1000, 2),
        "verification_seconds": timings["verification_seconds"],
        "total_seconds": timings["total_experiment_seconds"],
        "single_ballot_bytes": sizes["single_ballot_json_bytes"],
        "all_ballots_mb": round(sizes["all_ballots_json_bytes"] / (1024 * 1024), 2),
        "peak_memory_mb": round(peak_mem / (1024 * 1024), 2),
        "verified": report["verification"]["verified"],
    }


def run_all_benchmarks(scales: list[int] | None = None, output_file: str | None = None) -> list[dict[str, Any]]:
    """Run benchmarks across all target election scales."""
    if scales is None:
        scales = [10, 100, 1000, 5000]

    results = []
    print("\n========================================================")
    print(f"STARTING SECUREVOTE 3.0 BENCHMARK MATRIX: {scales}")
    print("========================================================")

    for n in scales:
        res = benchmark_scale(n)
        results.append(res)

    print("\n=========================================================================================================")
    print("SECUREVOTE 3.0 EMPIRICAL BENCHMARK RESULTS")
    print("=========================================================================================================")
    header = f"{'Ballots':<8} | {'Enc Time (s)':<12} | {'Throughput':<15} | {'Agg Time (ms)':<14} | {'Dec Time (ms)':<14} | {'Verif (s)':<10} | {'Peak Mem (MB)':<13} | {'Verified'}"
    print(header)
    print("-" * len(header))
    for r in results:
        tput_str = f"{r['throughput_ballots_per_sec']:.1f} b/s"
        status_str = "PASSED" if r["verified"] else "FAILED"
        print(f"{r['ballots']:<8} | {r['encryption_seconds']:<12.3f} | {tput_str:<15} | {r['aggregation_ms']:<14.2f} | {r['decryption_ms']:<14.2f} | {r['verification_seconds']:<10.3f} | {r['peak_memory_mb']:<13.2f} | {status_str}")
    print("=========================================================================================================\n")

    if output_file:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        summary = {
            "protocol": "Exponential ElGamal over secp256r1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Benchmark summary written to: {output_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description="SecureVOTE 3.0 Benchmark Suite")
    parser.add_argument("--scales", nargs="+", type=int, default=[10, 100, 1000, 5000], help="List of ballot counts")
    parser.add_argument("--out", type=str, default="evidence/v3_benchmark_results.json", help="Path to write JSON summary")
    args = parser.parse_args()

    run_all_benchmarks(scales=args.scales, output_file=args.out)


if __name__ == "__main__":
    main()
