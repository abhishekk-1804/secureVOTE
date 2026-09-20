# SecureVOTE 3.0 — Research Gaps & Future Roadmap

**Date**: 2026-09-20  
**Authors**: SecureVOTE Applied Cryptography & Security Research Team  
**Status**: Formal Architectural Assessment

---

## 1. Currently Demonstrated Capabilities

SecureVOTE 3.0 has empirically demonstrated:
1. **Confidential Ballot Ingestion**: Voter candidate choices are encoded into one-hot vectors and encrypted using Exponential ElGamal over NIST P-256 (`secp256r1`). Plaintext votes are never written to disk or database tables.
2. **Additive Homomorphic Aggregation**: Tallies are accumulated directly in ciphertext space via component-wise elliptic curve point addition, with exact zero-drift reconciliation across tested scales (10 to 5,000 ballots).
3. **Domain-Separated Cryptographic Commitments**: Every ballot and tally artifact is bound by domain-separated SHA-256 commitments that detect single-bit tampering.
4. **Independent 10-Checkpoint Verification**: A decoupled, offline verifier re-checks protocol versions, curve point validity, commitments, artifact hashes, homomorphic sums, and reconciliation with zero database or framework dependencies.
5. **Empirical Benchmarks**: Measured performance across scales up to 5,000 ballots, documenting real execution latency, throughput, and memory bounds.

---

## 2. Current Limitations

### 2.1 Absence of Zero-Knowledge Ballot Validity Proofs (`RESOLVED IN SECUREVOTE 3.1`)
* **Problem**: In SecureVOTE 3.0, the system did not prove that an encrypted ballot vector satisfies $v_j \in \{0, 1\}$ and $\sum_{j=0}^{k-1} v_j = 1$.
* **Resolution**: Successfully addressed in **SecureVOTE 3.1** via non-interactive Fiat-Shamir CDS94 disjunctive proofs for slots and Chaum-Pedersen sum equality proof. See `docs/research/SECUREVOTE_3_1_ZKP_SPECIFICATION.md` and `docs/research/SECUREVOTE_3_1_RESEARCH_GAPS.md`.

### 2.2 Single-Authority Decryption (`NOT IMPLEMENTED`)
* **Problem**: The election private key scalar is held in server RAM during the election lifecycle.
* **Vulnerability**: An adversary gaining process-level execution on the backend server can extract the private key and decrypt all individual ballots.
* **Impact on Claims**: SecureVOTE 3.0 is **NOT threshold-secure**.

### 2.3 Metadata & Temporal Correlation (`PARTIAL`)
* **Problem**: Even though ballots are stored without voter IDs in `v3_encrypted_ballots`, insertion timestamps and device sequence numbers in v2 audit logs could enable an observer to link voters to their encrypted ballots.
* **Impact on Claims**: SecureVOTE 3.0 provides **ballot confidentiality at rest**, but **NOT complete traffic or timing anonymity**.

### 2.4 Lack of Individual Cast-as-Intended Verifiability (`PARTIAL`)
* **Problem**: The voter cannot prove that the ciphertext output by the terminal corresponds to their intended selection without trusting the terminal's software.
* **Impact on Claims**: Lacks Benaloh challenge or voter-verifiable receipt mechanism.

---

## 3. Prioritized Research Milestones

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      SecureVOTE Research Roadmap                        │
├─────────────────────────┬───────────────────────────────────────────────┤
│ Milestone 1 (Priority)  │ Zero-Knowledge Ballot Validity Proofs (CDS94) │
│ Milestone 2 (Priority)  │ Distributed Key Generation & Threshold ElGamal│
│ Milestone 3             │ Verifiable Mix-Nets & Shuffling               │
│ Milestone 4             │ Benaloh Cast-as-Intended Voter Verification   │
│ Milestone 5             │ Receipt-Freeness & Coercion Resistance        │
└─────────────────────────┴───────────────────────────────────────────────┘
```

### Milestone 1: Zero-Knowledge Ballot Validity Proofs
* **Objective**: Ensure that every ciphertext vector contains a valid vote without revealing the selection.
* **Mathematical Construction**:
  1. For each slot $j \in \{0, \dots, k-1\}$, compute a non-interactive Cramer-Damgård-Schoenmakers (CDS94) disjunctive Chaum-Pedersen proof proving that $\text{Dec}(C_j) \in \{0, 1\}$:
     $$\text{PoK}\Big\{ (r_j, v_j) : (C_{1,j} = r_j G \wedge C_{2,j} = r_j Y) \vee (C_{1,j} = r_j G \wedge C_{2,j} = r_j Y + G) \Big\}$$
  2. For the aggregate vector, compute a Schnorr proof of equality proving that $\sum C_j$ encrypts $1$:
     $$\text{PoK}\Big\{ R : \sum C_{1,j} = R \cdot G \wedge \sum C_{2,j} - G = R \cdot Y \Big\}$$
* **Standard Reference**: Helios Voting, ElectionGuard v1.0.

### Milestone 2: Distributed Key Generation & $(t, n)$ Threshold Decryption
* **Objective**: Eliminate the single point of failure where a single server holds the decryption key.
* **Mathematical Construction**:
  1. Pederson DKG over `secp256r1` with $n$ trustees.
  2. Public key $Y = \sum Y_i$.
  3. Joint decryption: Each trustee $i$ provides a decryption share $S_i = x_i \cdot C_1^{\text{agg}}$ along with a Chaum-Pedersen proof of discrete log equality $\text{PoK}\{x_i : Y_i = x_i G \wedge S_i = x_i C_1^{\text{agg}}\}$.
  4. Lagrange interpolation recovers $M = \sum \lambda_i S_i$.

### Milestone 3: Verifiable Mix-Nets & Shuffling
* **Objective**: Sever timing and sequence correlations before ballots are published.
* **Mathematical Construction**:
  - Re-encryption mix-net using Wikström or Bayer-Groth argument of a shuffle.

### Milestone 4: Benaloh Challenge for Cast-as-Intended
* **Objective**: Allow the voter to audit the terminal without being able to sell their vote.
* **Workflow**: Terminal presents commitment. Voter can either "Audit" (terminal reveals randomness $r$, voter checks encryption on an independent device) or "Cast" (ballot is sealed into the tally).

---

## 4. Summary of Open Research Questions

1. **Microcontroller Hardware Feasibility**: Can an 8-bit ATmega328P or 32-bit ESP32 perform `secp256r1` point operations within 1 second, or should curve-based encryption be delegated to an authenticated hardware security module (HSM / Secure Element like ATECC608A)?
2. **Post-Quantum Migration**: What is the performance penalty of transitioning from ElGamal to lattice-based homomorphic schemes (e.g. BFV, BGV) on embedded election equipment?
3. **Air-Gapped Audit Bridge**: How to export multi-megabyte encrypted ballot archives from physically isolated polling stations to public bulletin boards with zero network connectivity?
