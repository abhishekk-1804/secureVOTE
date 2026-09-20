# SecureVOTE 3.2-B — Verifiable Partial Decryption Specification & Implementation

- **Milestone**: `SecureVOTE 3.2-B`
- **Target Configuration**: $(t, n) = (2, 3)$ Threshold ElGamal
- **Baseline Branch**: `research/securevote-3.2-threshold`
- **Preceding Commit**: `9fa0f3d44c24be51bf838aa359136d20f1787287`
- **Specification Reference**: `docs/research/SECUREVOTE_3_2_THRESHOLD_DESIGN.md`
- **Status**: Implementation Complete & Verified (258/258 backend tests passing)

---

## 1. Overview & Research Motivation

In SecureVOTE 3.2, the central election private key $x$ is never formed, reconstructed, or materialized. Instead, each trustee $i \in \mathcal{QUAL}$ possesses an individual master secret share $x_i \in \mathbb{Z}_q^*$ with a corresponding public verification key:
$$Y_i = x_i \cdot G \in E(\mathbb{F}_p)$$

To decrypt the homomorphically aggregated tally for candidate slot $j$ with aggregate ciphertext $(A_j, B_j)$, trustee $i$ computes a **partial decryption share**:
$$W_{i,j} = x_i \cdot A_j \in E(\mathbb{F}_p)$$

Because an untrusted or Byzantine trustee could attempt to sabotage or bias the election outcome by submitting a bogus point $W'_{i,j} \ne x_i \cdot A_j$, every partial decryption share must be accompanied by a non-interactive zero-knowledge proof of correctness.

SecureVOTE 3.2-B implements the **Chaum-Pedersen Equality of Discrete Logarithms** protocol under the Fiat-Shamir heuristic to prove:
$$\log_G(Y_i) = \log_{A_j}(W_{i,j}) = x_i$$
without disclosing $x_i$ or requiring interactive execution.

---

## 2. Threat Model & Security Properties

### 2.1 Threat Model
- **Trustee Corruption Bound**: Up to $f \le t - 1 = 1$ of $n = 3$ trustees may be malicious/Byzantine.
- **Malicious Trustee Capabilities**: A corrupted trustee may submit invalid points, refuse to participate, alter proof scalars, or replay proofs from other contests, candidates, or elections.
- **Network Assumptions**: Authenticated broadcast channel (public bulletin board) for partial decryptions and proofs.

### 2.2 Core Security Properties
1. **Zero Knowledge / Secrecy**: The proof reveals no information about private share $x_i$ beyond the equality of discrete logarithms.
2. **Special Soundness**: An adversary without knowledge of $x_i$ can convince an honest verifier with probability at most $1/q \approx 2^{-256}$.
3. **Completeness**: An honest trustee holding $x_i$ such that $Y_i = x_i G$ and $W_{i,j} = x_i A_j$ will always produce an accepting proof.
4. **Non-Malleability & Replay Defense**: Domain-separated Fiat-Shamir transcripts ensure proofs cannot be replayed across different elections, candidate slots, trustee identities, or curve points.

---

## 3. Cryptographic Construction

### 3.1 Prover Algorithm (`prove_partial_decryption`)
Given private share $x_i \in [1, q-1]$, verification key $Y_i = x_i G$, ciphertext component $A_j = R_j G$, and partial decryption share $W_{i,j} = x_i A_j$:

1. **Ephemeral Blinding**: Sample random nonce $w \xleftarrow{\$} [1, q - 1]$.
2. **Commitments**: Compute commitment points:
   $$comm_1 = w \cdot G$$
   $$comm_2 = w \cdot A_j$$
3. **Fiat-Shamir Challenge Derivation**:
   Construct canonical domain-separated transcript:
   $$\text{domain} = \texttt{"SECUREVOTE32/ZKP/PARTIAL\_DECRYPT/\{election\_id\}/\{candidate\_id\}/TRUSTEE/\{trustee\_id\}/"}$$
   Append protocol elements:
   - `protocol_version`: `"SECUREVOTE32"`
   - `election_id`: string
   - `candidate_id`: string
   - `trustee_id`: integer
   - `generator_G`: point $G$
   - `verification_key_Y`: point $Y_i$
   - `ciphertext_A`: point $A_j$
   - `partial_decryption_W`: point $W_{i,j}$
   - `comm_1`: point $comm_1$
   - `comm_2`: point $comm_2$

   Derive challenge scalar:
   $$c = \operatorname{TranscriptChallenge}(\text{"partial\_decrypt\_challenge"}) \in [1, q - 1]$$
4. **Response Scalar**:
   $$s = (w + c \cdot x_i) \pmod q$$
5. **Output**: Proof tuple $\Pi = (comm_1, comm_2, c, s)$.
6. **Ephemeral Nonce Erasure**: Blinding scalar $w$ is overwritten and eliminated from memory.

---

## 4. Verifier Algorithm (`verify_partial_decryption_proof`)

Given public parameters $(G, Y_i, A_j, W_{i,j})$ and proof $\Pi = (comm_1, comm_2, c, s)$:

1. **Curve & Infinity Checks**:
   - Check that $Y_i, A_j, W_{i,j}, comm_1, comm_2 \in E(\mathbb{F}_p)$ are on NIST P-256.
   - Reject if any of $Y_i, A_j, W_{i,j}, comm_1, comm_2$ is the point at infinity $\mathcal{O}$.
2. **Scalar Bounds Checks**:
   - Verify $1 \le c < q$.
   - Verify $0 \le s < q$.
3. **Fiat-Shamir Challenge Reconstruction**:
   Re-construct the identical canonical transcript and compute $c'$.
   Verify:
   $$c \stackrel{?}{=} c'$$
4. **Verification Equations**:
   - Equation 1 (verifies relation against $G$ and $Y_i$):
     $$s \cdot G \stackrel{?}{=} comm_1 + c \cdot Y_i$$
   - Equation 2 (verifies relation against $A_j$ and $W_{i,j}$):
     $$s \cdot A_j \stackrel{?}{=} comm_2 + c \cdot W_{i,j}$$
5. **Decision**: Accept if and only if both equations hold and $c == c'$.

---

## 5. Artifact Schemas & Serialization

All partial decryption artifacts adhere to canonical deterministic JSON serialization:

### 5.1 Partial Decryption Share Schema
```json
{
  "protocol_version": "SECUREVOTE32",
  "artifact_type": "PARTIAL_DECRYPTION_SHARE",
  "election_id": "ELEC-2026-PRIMARY",
  "candidate_id": "CAND-01",
  "trustee_id": 1,
  "partial_decryption": {
    "x": "0x5a1f8c4e...",
    "y": "0x912a9b3c..."
  },
  "proof": {
    "proof_type": "CHAUM_PEDERSEN_DLOG_EQUALITY",
    "comm_1": { "x": "0x...", "y": "0x..." },
    "comm_2": { "x": "0x...", "y": "0x..." },
    "c": "0x...",
    "s": "0x..."
  }
}
```

### 5.2 Tally Partial Decryption Package Schema
```json
{
  "protocol_version": "SECUREVOTE32",
  "artifact_type": "TALLY_PARTIAL_DECRYPTION_PACKAGE",
  "election_id": "ELEC-2026-PRIMARY",
  "trustee_id": 1,
  "shares": {
    "CAND-01": { ... },
    "CAND-02": { ... },
    "CAND-03": { ... }
  }
}
```

---

## 6. Negative Test Matrix & Validation Results

The implementation was validated against an exhaustive negative test suite in `backend/tests/test_threshold_partial_decryption.py`:

| # | Test Name | Mutation Tested | Expected & Observed Result |
| :--- | :--- | :--- | :--- |
| 1 | `test_valid_partial_decryption` | None (Honest execution) | **PASSED** (Valid proof accepted) |
| 2 | `test_altered_w_rejected` | Mutate partial decryption $W' = W + G$ | **PASSED** (Rejected, Eq 2 fails) |
| 3 | `test_altered_comm_1_rejected` | Mutate commitment $comm_1' = comm_1 + G$ | **PASSED** (Rejected, Challenge & Eq 1 fail) |
| 4 | `test_altered_comm_2_rejected` | Mutate commitment $comm_2' = comm_2 + G$ | **PASSED** (Rejected, Challenge & Eq 2 fail) |
| 5 | `test_altered_c_rejected` | Mutate challenge scalar $c' = (c + 1) \bmod q$ | **PASSED** (Rejected, Challenge check fails) |
| 6 | `test_altered_s_rejected` | Mutate response scalar $s' = (s + 1) \bmod q$ | **PASSED** (Rejected, Both equations fail) |
| 7 | `test_wrong_trustee_verification_key_rejected` | Substitute $Y_k \ne x_i G$ | **PASSED** (Rejected, Eq 1 fails) |
| 8 | `test_wrong_trustee_id_rejected` | Swap trustee ID in domain transcript | **PASSED** (Rejected, Challenge mismatch) |
| 9 | `test_wrong_election_id_rejected` | Swap election ID in domain transcript | **PASSED** (Rejected, Challenge mismatch) |
| 10 | `test_wrong_candidate_id_rejected` | Swap candidate ID in domain transcript | **PASSED** (Rejected, Challenge mismatch) |
| 11 | `test_wrong_aggregated_a_rejected` | Verify against alternate ciphertext $A'$ | **PASSED** (Rejected, Eq 2 fails) |
| 12 | `test_infinity_w_rejected` | Supply point at infinity $W = \mathcal{O}$ | **PASSED** (Rejected on point check) |
| 13 | `test_off_curve_w_rejected` | Supply off-curve coordinates $(x, y)$ | **PASSED** (Rejected on curve check) |
| 14 | `test_malformed_proof_rejected` | Out-of-range scalars ($c = 0$, $s \ge q$) | **PASSED** (Rejected on scalar bounds check) |
| 15 | `test_duplicate_share_artifact_behavior` | Repeated share generation for same contest | **PASSED** (Independent valid nonces) |
| 16 | `test_replay_from_another_election_rejected` | Replay share against different election ID | **PASSED** (Rejected, Challenge mismatch) |
| 17 | `test_replay_across_candidate_slots_rejected` | Replay share across candidate slots | **PASSED** (Rejected, Challenge mismatch) |
| 18 | `test_proof_generated_with_another_trustees_key_rejected` | Submit Trustee 2's proof claiming Trustee 1 | **PASSED** (Rejected, Verification key mismatch) |
| 19 | `test_protocol_version_mismatch_rejected` | Tamper protocol version domain string | **PASSED** (Rejected, Challenge mismatch) |
| 20 | `test_partial_decryption_serialization_round_trip` | Canonical JSON serialization | **PASSED** (Lossless round trip) |
| 21 | `test_tally_package_computation_and_verification` | Multi-candidate tally batch processing | **PASSED** (All 3 candidates verified) |
| 22 | `test_malformed_partial_decryption_json_rejected` | Corrupt JSON schema / types | **PASSED** (ThresholdSerializationError) |
| 23 | `test_no_private_secret_leakage_in_decryption` | Scan `repr()` and artifact payloads for $x_i$ | **PASSED** (Zero private key leakage) |

---

## 7. Security Boundaries & Prototype Limitations

1. **Non-Interactivity & Fiat-Shamir in ROM**: Security relies on the random oracle model for SHA-256 with domain-separated transcripts.
2. **Lagrange Combination Deferral**: This milestone covers only share generation and verification. Combining shares into the plaintext tally via Lagrange interpolation is deferred to milestone 3.2-C.
3. **Modulo Reduction Bias**: The challenge scalar $c \in [1, q - 1]$ is reduced modulo $(q - 1)$ from a 256-bit hash digest. This introduces a negligible ($2^{-32}$) theoretical bias, which is acceptable in this research prototype. Production implementations should use wide reduction (RFC 9380).
4. **Side-Channel Protection**: Scalar multiplications in this prototype use standard curve operations and are not hardened against micro-architectural side-channel or power analysis attacks.

---

## 8. Exact Deviations from Design

- **None**. The implementation adheres strictly to Section 10 ("Partial Decryption Protocol"), Section 11 ("Decryption-Share Proof of Correctness"), and Section 12 ("Share Verification Protocol") of `docs/research/SECUREVOTE_3_2_THRESHOLD_DESIGN.md`.
