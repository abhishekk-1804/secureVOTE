# SecureVOTE 3.0 — Empirical Cryptographic Benchmarks

**Date**: 2026-09-20  
**Host Environment**: Windows 11, Python 3.12.10 (AMD64)  
**Cryptographic Primitive**: Exponential ElGamal over NIST P-256 (`secp256r1`)  
**Point Arithmetic**: Optimized Jacobian coordinates with C-accelerated modular inversion (`pow(a, -1, p)`)  
**Candidate Slate**: 4 candidates (4 ciphertext pairs per ballot)  
**Source Data**: `evidence/v3_benchmark_results.json`

---

## 1. Executive Summary

| Ballots | Encryption Time | Throughput | Aggregation Time | Decryption Time | Verifier Time | Peak Memory | Verification Status |
|---|---|---|---|---|---|---|---|
| **10** | 1.930 s | 5.2 ballots/s | 48.80 ms | 151.73 ms | 0.057 s | 0.09 MB | **PASSED (10/10)** |
| **100** | 36.816 s | 2.7 ballots/s | 1,031.46 ms | 350.98 ms | 1.183 s | 0.66 MB | **PASSED (10/10)** |
| **1,000** | 371.849 s | 2.7 ballots/s | 10,074.10 ms | 418.15 ms | 11.748 s | 6.55 MB | **PASSED (10/10)** |
| **5,000** | 1,893.836 s | 2.6 ballots/s | 44,610.01 ms | 333.85 ms | 35.497 s | 32.74 MB | **PASSED (10/10)** |

---

## 2. Key Observations

### 2.1 Encryption Throughput
- Average throughput is consistently **2.6 – 2.7 ballots/sec** in pure Python on a single CPU core.
- Each ballot requires 4 independent candidate slot encryptions (8 scalar multiplications on `secp256r1` per ballot).
- Each scalar multiplication performs 256 doublings and additions in Jacobian coordinates.

### 2.2 Homomorphic Aggregation
- Scales strictly linearly $\mathcal{O}(N)$ with ballot count.
- Aggregating **1,000 ballots (4,000 ciphertexts)** requires only **10.07 seconds**.
- Aggregating **5,000 ballots (20,000 ciphertexts)** requires **44.61 seconds**.

### 2.3 Decryption Latency (Baby-Step Giant-Step)
- Decryption time remains virtually constant between **150 ms and 420 ms** across all election sizes.
- Because tallies are decrypted only *after* aggregation, decryption operates on single aggregated points rather than individual ballots.
- BSGS complexity $\mathcal{O}(\sqrt{N})$ requires at most $\lceil\sqrt{5000}\rceil = 71$ point additions per candidate slot.

### 2.4 Independent Standalone Verification
- The 10-checkpoint verifier verified all 5,000 ballots (evaluating all commitments, curve checks, and re-aggregating every ballot) in **35.49 seconds**.
- Peak memory usage for 5,000 ballots in Python memory was only **32.74 MB**.

### 2.5 Zero-Drift Reconciliation Integrity
- At every scale from 10 to 5,000 ballots, the sum of decrypted candidate tallies matched the ground truth ballot count with **exact zero drift**:
  - Scale 10: $5 + 3 + 2 + 0 = 10$
  - Scale 100: $47 + 27 + 17 + 9 = 100$
  - Scale 1,000: $374 + 318 + 200 + 108 = 1,000$
  - Scale 5,000: $1996 + 1529 + 991 + 484 = 5,000$
