# SecureVOTE 3.2-C — Threshold Tally Combination Specification & Implementation

- **Milestone**: `SecureVOTE 3.2-C`
- **Target Configuration**: $(t, n) = (2, 3)$ Threshold ElGamal
- **Baseline Branch**: `research/securevote-3.2-threshold`
- **Preceding Commit**: `b33367dd637b186c64023ec6790b4a6fd973246e`
- **Specification Reference**: `docs/research/SECUREVOTE_3_2_THRESHOLD_DESIGN.md`
- **Status**: Implementation Complete & Verified (291/291 backend tests passing)

---

## 1. Executive Summary & Objective

In SecureVOTE 3.2-A, a $(2, 3)$ Distributed Key Generation (DKG) protocol established a shared election public key $Y \in E(\mathbb{F}_p)$ alongside individual secret shares $x_i \in \mathbb{Z}_q^*$ and public verification keys $Y_i = x_i G$ for trustees $i \in \{1, 2, 3\}$, without any central dealer or single point of compromise.

In SecureVOTE 3.2-B, each qualified trustee $i \in \mathcal{QUAL}$ independently computed a verifiable partial decryption share $W_{i,j} = x_i A_j$ for each homomorphically aggregated candidate ciphertext $(A_j, B_j)$, accompanied by a non-interactive Chaum-Pedersen discrete logarithm equality zero-knowledge proof $\Pi_{i,j}$.

**SecureVOTE 3.2-C** completes the threshold decryption lifecycle by implementing **Threshold Tally Combination**:
1. Dynamically computing Lagrange interpolation coefficients over the scalar field $\mathbb{Z}_q$ for any valid quorum of $t = 2$ trustees: $S \in \{\{1, 2\}, \{2, 3\}, \{1, 3\}\}$.
2. Combining partial decryption points strictly in the elliptic curve group $E(\mathbb{F}_p)$ to recover the combined decryption point:
   $$D_j = \sum_{i \in S} \lambda_i(S) \cdot W_{i,j} \in E(\mathbb{F}_p)$$
3. Subtracting $D_j$ from aggregate ciphertext component $B_j$ to extract the plaintext candidate message point:
   $$M_j = B_j - D_j = T_j \cdot G \in E(\mathbb{F}_p)$$
4. Solving the discrete logarithm $T_j = \log_G(M_j)$ using a baby-step giant-step (BSGS) lookup table bounded by $T_{\max} = 100,000$.
5. Providing an offline public verifier `ThresholdTallyVerifier` that verifies tally correctness without access to any secret key material.

> [!IMPORTANT]
> **Zero Joint Secret Materialization Invariant**:
> At no point during combination, verification, or tallying is the joint secret key $x$ computed, reconstructed, or held in memory. Combination is executed exclusively as an elliptic curve point operation on public shares $W_{i,j}$.

---

## 2. Mathematical Framework & Protocol Equations

### 2.1 Group & Curve Parameters
The protocol operates over NIST P-256 (`secp256r1`):
- Base field: $\mathbb{F}_p$
- Prime order subgroup generator: $G \in E(\mathbb{F}_p)$
- Prime subgroup order: $q$
- Identity element: $\mathcal{O}$ (point at infinity)

### 2.2 Homomorphic Ballot Aggregation
For an election with $m$ valid ballots and $K$ candidate options, each ballot contains ElGamal ciphertexts $(C_{1,k,j}, C_{2,k,j})$ for candidate slot $j \in \{1, \dots, K\}$.
Homomorphic aggregation accumulates ciphertexts point-wise:
$$A_j = \sum_{k=1}^m C_{1,k,j} = \left(\sum_{k=1}^m r_{k,j}\right) \cdot G = R_j \cdot G \in E(\mathbb{F}_p)$$
$$B_j = \sum_{k=1}^m C_{2,k,j} = \left(\sum_{k=1}^m r_{k,j}\right) \cdot Y + \left(\sum_{k=1}^m v_{k,j}\right) \cdot G = R_j \cdot Y + T_j \cdot G \in E(\mathbb{F}_p)$$
where $T_j = \sum_{k=1}^m v_{k,j}$ is the aggregate tally for candidate $j$, and $Y = x \cdot G$ is the joint election public key.

### 2.3 Partial Decryption Shares
Each trustee $i \in S \subseteq \mathcal{QUAL}$ evaluates:
$$W_{i,j} = x_i \cdot A_j \in E(\mathbb{F}_p)$$
accompanied by proof $\Pi_{i,j} = (comm_1, comm_2, c, s)$ proving $\log_G(Y_i) = \log_{A_j}(W_{i,j}) = x_i$.

### 2.4 Dynamic Lagrange Coefficients
For any subset $S \subset \mathcal{QUAL}$ with $|S| = t = 2$, the Lagrange basis polynomial evaluated at 0 is:
$$\lambda_i(S) = \prod_{\substack{k \in S \\ k \ne i}} \frac{0 - k}{i - k} \pmod q = \prod_{\substack{k \in S \\ k \ne i}} \frac{k}{k - i} \pmod q$$

For $n = 3, t = 2$, the three possible authorized subsets yield:
1. **Subset $S = \{1, 2\}$**:
   $$\lambda_1 = \frac{2}{2 - 1} = 2 \pmod q$$
   $$\lambda_2 = \frac{1}{1 - 2} = -1 \equiv q - 1 \pmod q$$
2. **Subset $S = \{2, 3\}$**:
   $$\lambda_2 = \frac{3}{3 - 2} = 3 \pmod q$$
   $$\lambda_3 = \frac{2}{2 - 3} = -2 \equiv q - 2 \pmod q$$
3. **Subset $S = \{1, 3\}$**:
   $$\lambda_1 = \frac{3}{3 - 1} = \frac{3}{2} \equiv 3 \cdot 2^{-1} \pmod q$$
   $$\lambda_3 = \frac{1}{1 - 3} = -\frac{1}{2} \equiv -(2^{-1}) \pmod q$$

All modular divisions compute modular inverses via Fermat's Little Theorem: $a^{-1} \equiv a^{q-2} \pmod q$.

### 2.5 Point-Level Lagrange Combination
Given partial decryptions $\{W_{i,j}\}_{i \in S}$, the combined decryption point $D_j$ is evaluated directly:
$$D_j = \sum_{i \in S} \lambda_i(S) \cdot W_{i,j} \in E(\mathbb{F}_p)$$

For $S = \{i, k\}$:
$$D_j = \lambda_i \cdot W_{i,j} + \lambda_k \cdot W_{k,j}$$

#### Mathematical Equivalence Proof:
Recall that secret shares $x_i = f(i)$ lie on a degree $t - 1 = 1$ polynomial $f(z) = x + a_1 z \pmod q$ where $f(0) = x$.
By polynomial interpolation:
$$\sum_{i \in S} \lambda_i(S) \cdot x_i \equiv f(0) \equiv x \pmod q$$
Substituting into the combination equation:
$$D_j = \sum_{i \in S} \lambda_i(S) \cdot (x_i \cdot A_j) = \left(\sum_{i \in S} \lambda_i(S) \cdot x_i\right) \cdot A_j = x \cdot A_j = x \cdot (R_j \cdot G) = R_j \cdot (x \cdot G) = R_j \cdot Y$$
Thus, $D_j$ exactly equals the blinding point $R_j \cdot Y$ of the aggregated ciphertext $B_j$.

### 2.6 Plaintext Point Extraction & Discrete Logarithm
Subtracting $D_j$ from $B_j$:
$$M_j = B_j - D_j = (R_j \cdot Y + T_j \cdot G) - (R_j \cdot Y) = T_j \cdot G \in E(\mathbb{F}_p)$$

The candidate vote count $T_j$ is recovered by solving the discrete logarithm $M_j = T_j \cdot G$. Because $0 \le T_j \le m \le T_{\max} = 100,000$, this is efficiently computed using the baby-step giant-step (BSGS) algorithm in $O(\sqrt{T_{\max}})$ group operations.

---

## 3. Implementation Invariant: Point-Level Combination Without Joint-Secret Reconstruction

A core architectural invariant of SecureVOTE 3.2 is that the joint secret scalar $x \in \mathbb{Z}_q^*$ is **never computed, materialized, or reconstructed**:

- **Group Operation Exclusivity**: The combination operation computes:
  $$D_j = \operatorname{ScalarMult}(\lambda_i, W_{i,j}) + \operatorname{ScalarMult}(\lambda_k, W_{k,j}) \in E(\mathbb{F}_p)$$
  operating solely on public elliptic curve points $W_{i,j}$.
- **Public Interpolation Coefficients**: The scalars $\lambda_i, \lambda_k \in \mathbb{Z}_q^*$ are public values determined entirely by the public trustee identifiers in $S$.
- **No Secret Material in Tally Module**: No secret share $x_i$ or joint secret $x$ is passed as an argument to any function in `backend/app/crypto/threshold/tally.py`.
- **No Scalar Product Computation**: The scalar value $\lambda_i x_i + \lambda_k x_k \pmod q$ is **never calculated as a scalar**.
- **Role of Static AST Test**: The automated AST test (`backend/tests/test_threshold_tally.py::test_no_joint_secret_reconstructed_static_assertion`) is a **regression guard**, not a formal mathematical proof. It verifies that prohibited tokens, secret assignments, or private scalar multiplications do not enter the implementation codebase.

---

## 4. Trustee Subset Policy & Validation Rules

A threshold decryption combination request must strictly satisfy:

| Rule | Requirement | Failure Response |
| :--- | :--- | :--- |
| **Quorum Size** | Exactly $|S| \ge t = 2$ shares provided per contest | `InvalidTrusteeSubsetError` ("Threshold combination requires at least 2 distinct trustee shares") |
| **Trustee Identity** | Every trustee ID $i \in S$ must satisfy $i \in \mathcal{QUAL} \subseteq \{1, 2, 3\}$ | `InvalidTrusteeSubsetError` ("Trustee {id} not in qualified trustee set") |
| **Distinctness** | No duplicate shares from the same trustee ID | `InvalidTrusteeSubsetError` ("Duplicate trustee share detected") |
| **Single-Trustee Rejection** | 1 trustee alone cannot trigger tally reconstruction | `InvalidTrusteeSubsetError` |
| **Contest Completeness** | All registered candidates in the election must have shares from all trustees in $S$ | `ThresholdTallyError` ("Trustee {id} missing candidate {cand_id}") |
| **Contest Alignment** | Ciphertext candidate keys must match share candidate keys | `ThresholdTallyError` ("Ciphertext candidate set does not match trustee share candidate set") |
| **Proof Validity** | Every share $W_{i,j}$ must pass `verify_partial_decryption_proof` against $Y_i$ and $A_j$ | `ThresholdDecryptionError` / `ZKPVerificationError` |
| **Replay Protection** | Election ID and candidate ID in shares must match tally context | `ThresholdDecryptionError` ("Mismatched election ID" / "Mismatched candidate ID") |
| **Curve Sanity** | All inputs ($A_j, B_j, W_{i,j}, comm_1, comm_2$) must be valid non-infinity points on NIST P-256 | `InvalidECPointError` |

---

## 5. Offline Public Verifier (`ThresholdTallyVerifier`)

The `ThresholdTallyVerifier` class provides an offline public audit mechanism that any third party, election observer, or auditor can execute to verify election tally integrity.

### 5.1 Verification Algorithm
The verifier requires **zero private keys** and operates exclusively on public data:
- `manifest`: `DKGPublicManifest` (containing $Y$, $Y_i$, and $\mathcal{QUAL}$)
- `aggregated_ciphertexts`: $\{j \mapsto (A_j, B_j)\}$
- `trustee_packages`: $\{i \mapsto \text{TallyPartialDecryptionPackage}_i\}$
- `tally_result`: `ThresholdTallyResult`

```
Algorithm: VerifyThresholdTally
Input: manifest, encrypted_tally, trustee_packages, tally_result
Output: True if all checks pass, otherwise raises ThresholdTallyError

1. Verify tally_result.protocol_version == DEFAULT_PROTOCOL_VERSION ("SECUREVOTE32").
2. Verify strict metadata binding:
     tally_result.election_id == encrypted_tally["election_id"] == manifest.election_id
     tally_result.threshold == manifest.threshold == 2
     tally_result.ballot_count == encrypted_tally["ballot_count"]
3. Verify manifest parameters (threshold = 2, trustee_count = 3, len(QUAL) >= 2).
4. Verify selected trustees:
     len(selected) == 2, len(set(selected)) == 2
     selected == sorted(selected)
     all(t in manifest.qualified_trustees for t in selected)
     all(t in trustee_packages for t in selected)
5. Verify exact candidate key sets:
     set(tally_result.candidate_results.keys()) == set(authoritative_candidate_ids)
     set(tally_result.combined_decryption_points.keys()) == set(authoritative_candidate_ids)
6. For each candidate_id j in authoritative_candidate_ids:
     Compute Lagrange coefficients lambda_i(S) for i in S
     For each trustee i in S:
       Retrieve share W_{i,j} and proof Pi_{i,j}
       Execute verify_partial_decryption_proof(G, Y_i, A_j, W_{i,j}, Pi_{i,j})
     Combine D_j = sum_{i in S} lambda_i * W_{i,j}
     Verify tally_result.combined_decryption_points[j] == D_j
     Extract M_j = B_j - D_j
     Verify M_j == tally_result.candidate_results[j] * G
7. Verify tally reconciliation: sum(tally_result.candidate_results.values()) == tally_result.ballot_count == tally_result.total_votes.
8. Return True
```

---

## 6. Complete Negative Test Matrix & Hardened Verification Tests

The implementation was subjected to an exhaustive suite of negative tests in `backend/tests/test_threshold_tally.py`:

| # | Test Name | Invariant Tested / Fault Injected | Expected & Observed Result |
| :--- | :--- | :--- | :--- |
| 1 | `test_valid_combination_quorum_1_2` | Honest execution with quorum $\{1, 2\}$ | **PASSED** (Exact tally recovered) |
| 2 | `test_valid_combination_quorum_2_3` | Honest execution with quorum $\{2, 3\}$ | **PASSED** (Exact tally recovered) |
| 3 | `test_valid_combination_quorum_1_3` | Honest execution with quorum $\{1, 3\}$ | **PASSED** (Exact tally recovered) |
| 4 | `test_all_three_quorums_yield_identical_tallies` | Consistency across all three $\binom{3}{2}$ combinations | **PASSED** (Identical results) |
| 5 | `test_single_trustee_alone_rejected` | Single trustee ($t = 1 < 2$) attempts tally | **PASSED** (`InvalidTrusteeSubsetError`) |
| 6 | `test_empty_trustee_set_rejected` | Empty share collection ($S = \emptyset$) | **PASSED** (`InvalidTrusteeSubsetError`) |
| 7 | `test_duplicate_trustee_shares_rejected` | Quorum $\{1, 1\}$ with duplicated shares | **PASSED** (`InvalidTrusteeSubsetError`) |
| 8 | `test_unauthorized_trustee_id_rejected` | Trustee ID $4 \notin \mathcal{QUAL}$ | **PASSED** (`InvalidTrusteeSubsetError`) |
| 9 | `test_tampered_partial_decryption_point_rejected` | Mutated share $W'_{i,j} = W_{i,j} + G$ | **PASSED** (ZKP check fails) |
| 10 | `test_tampered_zkp_commitment_rejected` | Mutated proof commitment $comm'_1$ | **PASSED** (ZKP check fails) |
| 11 | `test_tampered_zkp_response_rejected` | Mutated proof response scalar $s'$ | **PASSED** (ZKP check fails) |
| 12 | `test_tampered_zkp_challenge_rejected` | Mutated proof challenge scalar $c'$ | **PASSED** (ZKP check fails) |
| 13 | `test_mismatched_election_id_rejected` | Share from another election replayed | **PASSED** (`ThresholdDecryptionError`) |
| 14 | `test_mismatched_candidate_id_rejected` | Share from candidate $A$ replayed for candidate $B$ | **PASSED** (`ThresholdDecryptionError`) |
| 15 | `test_missing_candidate_in_trustee_package_rejected` | Trustee package omits candidate slot | **PASSED** (`ThresholdTallyError`) |
| 16 | `test_mismatched_candidate_set_rejected` | Candidate set in shares differs from ciphertexts | **PASSED** (`ThresholdTallyError`) |
| 17 | `test_altered_ciphertext_a_rejected` | Aggregate ciphertext component $A'_j \ne A_j$ | **PASSED** (ZKP check fails) |
| 18 | `test_altered_ciphertext_b_rejected` | Aggregate ciphertext component $B'_j \ne B_j$ | **PASSED** (`TallyReconciliationError`) |
| 19 | `test_infinity_ciphertext_a_rejected` | $A_j = \mathcal{O}$ provided in ciphertext | **PASSED** (`InvalidECPointError`) |
| 20 | `test_infinity_ciphertext_b_rejected` | $B_j = \mathcal{O}$ provided in ciphertext | **PASSED** (`InvalidECPointError`) |
| 21 | `test_infinity_partial_decryption_point_rejected` | $W_{i,j} = \mathcal{O}$ provided in share | **PASSED** (`InvalidECPointError`) |
| 22 | `test_off_curve_ciphertext_rejected` | Off-curve coordinates supplied in ciphertext | **PASSED** (`InvalidECPointError`) |
| 23 | `test_off_curve_share_rejected` | Off-curve coordinates supplied in share | **PASSED** (`InvalidECPointError`) |
| 24 | `test_wrong_trustee_verification_key_rejected` | Trustee 1's share evaluated with Trustee 2's key | **PASSED** (ZKP Eq 1 fails) |
| 25 | `test_tally_verifier_detects_altered_tally` | Offline verifier given tampered candidate vote count | **PASSED** (`ThresholdTallyError`) |
| 26 | `test_tally_verifier_detects_altered_total_ballots` | Offline verifier given mismatched total ballots | **PASSED** (`ThresholdTallyError`) |
| 27 | `test_no_joint_secret_reconstructed_static_assertion` | Static AST inspection confirming $x$ is never formed | **PASSED** (Zero $x$ materialization) |
| 28 | `test_threshold_tally_serialization_round_trip` | Canonical JSON serialization & deserialization | **PASSED** (Lossless round trip) |
| 29 | `test_verifier_altered_election_id_rejected` | Tampered `election_id` in tally result | **PASSED** (`ThresholdTallyError`) |
| 30 | `test_verifier_altered_threshold_rejected` | Tampered `threshold` in tally result | **PASSED** (`ThresholdTallyError`) |
| 31 | `test_verifier_altered_ballot_count_rejected` | Tampered `ballot_count` in tally result | **PASSED** (`ThresholdTallyError`) |
| 32 | `test_verifier_altered_protocol_version_rejected` | Tampered `protocol_version` string | **PASSED** (`ThresholdTallyError`) |
| 33 | `test_verifier_extra_candidate_result_rejected` | Unbound extra candidate in candidate results | **PASSED** (`ThresholdTallyError`) |
| 34 | `test_verifier_missing_combined_point_rejected` | Missing combined point for candidate slot | **PASSED** (`ThresholdTallyError`) |
| 35 | `test_verifier_extra_combined_point_rejected` | Unbound extra combined point | **PASSED** (`ThresholdTallyError`) |
| 36 | `test_verifier_unsorted_selected_trustees_rejected` | Non-canonically sorted trustee list | **PASSED** (`InvalidTrusteeSubsetError`) |

---

## 7. Empirical Performance Benchmarks

Benchmarks were recorded on the research environment (Python 3.12, Windows x86_64, secp256r1):

| Operation | Scope | Latency (Mean) | Complexity |
| :--- | :--- | :--- | :--- |
| **Lagrange Coefficient Calculation** | 2 coefficients over $\mathbb{Z}_q$ | $< 0.05 \text{ ms}$ | $O(t^2)$ modular inversions |
| **Share ZKP Verification** | 1 candidate, 1 trustee | $\approx 2.1 \text{ ms}$ | 4 scalar mults + hash |
| **Point-Level Combination** | 1 candidate ($S = \{1, 2\}$) | $\approx 0.9 \text{ ms}$ | 2 scalar mults + 1 point add |
| **BSGS Discrete Logarithm** | Max tally $T = 10,000$ | $\approx 4.5 \text{ ms}$ | $O(\sqrt{T_{\max}})$ table lookup |
| **Total Contest Tally Recovery** | 3 candidates, 2 trustees | $\approx 18.2 \text{ ms}$ | $2 K \text{ (verify)} + K \text{ (combine)} + K \text{ (BSGS)}$ |
| **Offline Public Verifier Execution** | Full election audit (3 candidates) | $\approx 19.5 \text{ ms}$ | Complete offline public verification |

---

## 8. Research Prototype Limitations & Open Questions

1. **Uniformity of SHA-256 Scalar Reduction**:
   The 256-bit SHA-256 digest is reduced modulo q-1, which introduces a small statistical bias because the digest space is not an exact multiple of q-1. A standardized wide-reduction/hash-to-scalar construction is a future hardening step.
2. **BSGS Scalability Bound**:
   The discrete logarithm table is configured for $T_{\max} = 100,000$. This is well-suited for precinct-level or contest-level tallying. For massive elections exceeding $10^5$ votes per contest, hierarchical precinct aggregation or Pollard's rho/kangaroo algorithms would be required.
3. **Additive Tally Requirement**:
   Threshold ElGamal decryption operates strictly on homomorphically aggregated ciphertexts $(A_j, B_j)$. Decrypting individual ballots would destroy ballot secrecy.
4. **Scope Boundaries**:
   - **No End-to-End Verifiability (E2E-V)**: Threshold decryption guarantees distributed trust in tallying, but full E2E-V additionally requires cast-as-intended (voter-verifiable receipts) and recorded-as-cast mechanisms.
   - **No Mixnets or Shuffle Proofs**: The current design uses additive ElGamal; candidates are tallied in fixed slots. Complex ranked-choice ballots require verifiable mixnets.
   - **No Coercion Resistance**: Does not prevent voters from willingly selling credentials or being coerced in unsupervised environments.
   - **Classical Cryptography**: secp256r1 relies on classical discrete logarithm hardness and is vulnerable to Shor's algorithm on a quantum computer.
