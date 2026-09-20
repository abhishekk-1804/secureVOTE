# SecureVOTE 3.1 — Zero-Knowledge Ballot Validity Proof Specification

- **Date**: 2026-09-20
- **Authors**: SecureVOTE Applied Cryptography & Security Research Team
- **Status**: Specification & Reference Protocol
- **Protocol Version**: `SECUREVOTE31`

---

## 1. Research Motivation & Problem Statement

In additive Exponential ElGamal voting (SecureVOTE 3.0), candidate selections are encoded as one-hot vectors and encrypted component-wise over an elliptic curve group:

$$\mathbf{C} = \Big(\text{Enc}(v_0), \text{Enc}(v_1), \dots, \text{Enc}(v_{k-1})\Big)$$

While additive homomorphism permits accumulating election tallies directly in ciphertext space without intermediate decryption, **SecureVOTE 3.0 possessed an essential integrity vulnerability**:

> An adversarial voter or compromised voting terminal could submit an encrypted vector where components do not satisfy $v_j \in \{0, 1\}$ (e.g., submitting $v_0 = 100$ or negative values).

Such a malformed ballot homomorphically corrupts the aggregate tally while satisfying all curve-point and cryptographic commitment checks.

### The Research Question
> *Can zero-knowledge proofs demonstrate that an encrypted ballot encodes exactly one valid candidate choice, without revealing which candidate was selected?*

In SecureVOTE 3.1, we answer this question affirmatively by implementing, verifying, and benchmarking non-interactive zero-knowledge proofs of ballot validity.

---

## 2. Threat Model & Verifier Semantics

1. **Malicious Voter / Client**: Attempts to submit an encrypted ballot with $v_j \notin \{0, 1\}$ or $\sum v_j \neq 1$.
   * *Defense*: The standalone verifier checks the non-interactive proof of knowledge of the witness via the CDS94 and Chaum-Pedersen verification equations without receiving, knowing, or recomputing the secret witness. If the prover did not possess a valid binary, one-hot witness, the proof equations fail except with negligible probability.
2. **Dishonest Prover**: Attempts to forge proofs without knowing the randomness $r_j$ or for an invalid plaintext.
   * *Defense*: Soundness of the Sigma protocol under the Computational Diffie-Hellman (CDH) and Discrete Logarithm assumptions in the random oracle model.
3. **Passive Observer / Verifier**: Attempts to determine which candidate $v_j = 1$ was chosen by inspecting the proof transcript.
   * *Defense*: Special Honest-Verifier Zero-Knowledge (HVZK) property of CDS94 simulation; transcripts for $v=0$ and $v=1$ are computationally indistinguishable.
4. **Context Substitution / Replay**: Attempts to replay a valid proof in another election or under a different public key.
   * *Defense*: Cryptographic domain separation binding the election ID, public key, candidate ID, and ciphertext points into the Fiat-Shamir transcript.
5. **Verifier Knowledge Boundary**:
   * The verifier verifies a proof of knowledge of the secret witness $(i, \{r_j\})$.
   * The verifier **never** receives, computes, extracts, or stores the secret witness.

---

## 3. Mathematical Notation & Group Model

* **Elliptic Curve Group**: NIST P-256 (`secp256r1`)
  - Prime field: $\mathbb{F}_p$ where $p = 2^{256} - 2^{224} + 2^{192} + 2^{96} - 1$
  - Base point / Generator: $G$
  - Prime group order: $q = \text{0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551}$
  - Public key: $Y = x \cdot G \in E(\mathbb{F}_p)$
* **Candidate Slate**: $k \ge 2$ candidates with unique identifiers $\mathbf{K} = [\text{cid}_0, \dots, \text{cid}_{k-1}]$.
* **Ciphertext Slot $j$**:
  $$A_j = r_j \cdot G, \quad B_j = r_j \cdot Y + v_j \cdot G$$
  where $r_j \in_R \mathbb{Z}_q^*$ and $v_j \in \{0, 1\}$.

---

## 4. Formal Proof Statement & Witness

### 4.1 Public Statement
Given public parameters $(G, Y)$, election ID $E$, candidate slate $\mathbf{K}$, and ciphertext vector $\mathbf{C} = [(A_0, B_0), \dots, (A_{k-1}, B_{k-1})]$, prove:

$$\mathcal{R}_{\text{valid}} = \left\{ \begin{aligned}
& \forall j \in \{0, \dots, k-1\}: \; \text{Dec}(A_j, B_j) \in \{0, 1\} \\
& \wedge \; \sum_{j=0}^{k-1} \text{Dec}(A_j, B_j) = 1
\end{aligned} \right\}$$

### 4.2 Witness
The secret witness $\mathbf{W}$ known only to the prover consists of:
$$\mathbf{W} = \left( i, \; \{r_j\}_{j=0}^{k-1} \right)$$
where $i \in \{0, \dots, k-1\}$ is the selected candidate index ($v_i = 1$, $v_j = 0$ for $j \neq i$), and $r_j$ is the encryption randomness for slot $j$.

---

## 5. Sigma Protocol & CDS94 Disjunctive Construction

### 5.1 Slot-Level Disjunctive Proof (CDS94)
For each slot $j$, the prover proves $(v_j = 0) \vee (v_j = 1)$.

* If $v_j = 0$: $(A_j, B_j)$ is a DH-tuple with base $(G, Y)$.
* If $v_j = 1$: $(A_j, B_j - G)$ is a DH-tuple with base $(G, Y)$.

**Prover Protocol**:
1. Let $v \in \{0, 1\}$ be the true bit and $\bar{v} = 1 - v$ be the simulated bit.
2. **Simulation of False Branch $\bar{v}$**:
   - Sample simulated challenge $c_{\bar{v}} \leftarrow_R \mathbb{Z}_q^*$ and response $s_{\bar{v}} \leftarrow_R \mathbb{Z}_q^*$.
   - Set $B_0' = B_j$ and $B_1' = B_j - G$.
   - Compute simulated commitments:
     $$a_{\bar{v}} = s_{\bar{v}} \cdot G - c_{\bar{v}} \cdot A_j$$
     $$b_{\bar{v}} = s_{\bar{v}} \cdot Y - c_{\bar{v}} \cdot B_{\bar{v}}'$$
3. **Commitment of Real Branch $v$**:
   - Sample fresh blinding scalar $w \leftarrow_R \mathbb{Z}_q^*$.
   - Compute real commitments:
     $$a_v = w \cdot G, \quad b_v = w \cdot Y$$
4. **Fiat-Shamir Master Challenge**:
   Compute master challenge $c \in \mathbb{Z}_q^*$ over transcript:
   $$c = \text{Hash}\Big(\text{Domain}_{\text{slot}} \mathbin{\Vert} Y \mathbin{\Vert} A_j \mathbin{\Vert} B_j \mathbin{\Vert} a_0 \mathbin{\Vert} b_0 \mathbin{\Vert} a_1 \mathbin{\Vert} b_1\Big)$$
5. **Real Challenge & Response**:
   $$c_v = (c - c_{\bar{v}}) \bmod q$$
   $$s_v = (w + c_v \cdot r_j) \bmod q$$
6. **Slot Proof Artifact**:
   $$\pi_j = (a_0, b_0, a_1, b_1, c_0, c_1, s_0, s_1)$$

### 5.2 Ballot Sum Equality Proof
To prove $\sum_{j=0}^{k-1} v_j = 1$:
1. Homomorphically sum all slots:
   $$A_{\text{sum}} = \sum_{j=0}^{k-1} A_j = \left(\sum_{j=0}^{k-1} r_j\right) \cdot G$$
   $$B_{\text{sum}} = \sum_{j=0}^{k-1} B_j = \left(\sum_{j=0}^{k-1} r_j\right) \cdot Y + G$$
2. Let $B_{\text{sum}}' = B_{\text{sum}} - G$ and $R = \sum_{j=0}^{k-1} r_j \bmod q$.
3. Notice $(A_{\text{sum}}, B_{\text{sum}}')$ is a standard DH-tuple with base $(G, Y)$ and secret exponent $R$.
4. Prover generates a standard Chaum-Pedersen proof $\pi_{\text{sum}} = (a, b, c, s)$ with witness $R$.

---

## 6. Fiat-Shamir Transformation & Domain Separation

Every challenge is derived non-interactively using domain-separated SHA-256 hashing:

| Scope | Domain String Format |
|---|---|
| Slot Disjunctive Proof | `SECUREVOTE31/ZKP/SLOT/{election_id}/{candidate_id}/` |
| Aggregate Sum Proof | `SECUREVOTE31/ZKP/SUM/{election_id}/` |

Transcript serialization strictly canonicalizes all keys and formats coordinate points as fixed 64-hex strings (`f"{x:064x}"`).

---

## 7. Verification Algorithm & Operation Count

Given public key $Y$, ciphertext $\mathbf{C}$, and proof $\Pi = (\{\pi_j\}_{j=0}^{k-1}, \pi_{\text{sum}})$:

1. **Point Validation**: Verify all commitment and ciphertext points lie on $E(\mathbb{F}_p)$ and are not $\mathcal{O}$.
2. **Slot Proofs (for each $j \in \{0, \dots, k-1\}$)**:
   - Compute master challenge $c = \text{Transcript.challenge}()$.
   - Assert $(c_0 + c_1) \bmod q \equiv c$.
   - Assert $s_0 \cdot G = a_0 + c_0 \cdot A_j$ (requires 2 scalar mults).
   - Assert $s_0 \cdot Y = b_0 + c_0 \cdot B_j$ (requires 2 scalar mults).
   - Assert $s_1 \cdot G = a_1 + c_1 \cdot A_j$ (requires 2 scalar mults).
   - Assert $s_1 \cdot Y = b_1 + c_1 \cdot (B_j - G)$ (requires 2 scalar mults).
   - *Subtotal per slot*: **8 curve scalar multiplications**.
3. **Sum Proof**:
   - Compute $A_{\text{sum}} = \sum A_j$ and $B_{\text{sum}}' = \sum B_j - G$.
   - Compute sum challenge $c_{\text{sum}} = \text{Transcript.challenge}()$.
   - Assert $s_{\text{sum}} \cdot G = a + c_{\text{sum}} \cdot A_{\text{sum}}$ (requires 2 scalar mults).
   - Assert $s_{\text{sum}} \cdot Y = b + c_{\text{sum}} \cdot B_{\text{sum}}'$ (requires 2 scalar mults).
   - *Subtotal for sum proof*: **4 curve scalar multiplications**.

### Exact Scalar Multiplication Complexity Formula
$$\text{Scalar Mults per Ballot} = 8k + 4$$

For $k = 4$ candidates:
$$8(4) + 4 = 36 \text{ curve scalar multiplications per ballot}$$

Under the Decisional Diffie-Hellman (DDH) and discrete logarithm assumptions in the random oracle model, if all verification equations pass, the ballot encodes a valid one-hot vector with computational soundness (cheating probability bounded by $2/q$).

---

## 8. Verifier Status Semantics

The standalone verifier evaluates ballot validity under distinct status outcomes:

| Status Code | Meaning & Condition |
|---|---|
| `VALID` | All ballots contain well-formed proofs and satisfy all $8k + 4$ verification equations. |
| `INVALID` | One or more proofs fail algebraic equations, challenge sums, or points are off-curve. Also returned when a **mixed-proof package** (some ballots proven, some unproven) is detected. |
| `NOT_PRESENT` | Ballots contain no zero-knowledge proof. In `SECUREVOTE31` mode, this causes the checkpoint to fail (`PASSED = False`). In legacy `SECUREVOTE3` mode, this is recorded as unproven (`NOT_VERIFIED`). |

---

## 9. Explicit Non-Claims & Scope Limitations

SecureVOTE 3.1 does **NOT** claim:
1. **Full End-to-End Verifiability (E2E-V)**: Cast-as-intended verification is not implemented.
2. **Individual Cast Verification**: Lacks a Benaloh audit challenge mechanism.
3. **Timing or Metadata Anonymity**: Lacks mix-net shuffling; arrival sequence in logs can leak voter choices in small precincts.
4. **Threshold Security**: Uses a single central private key; distributed key generation (DKG) is deferred to Milestone 3.2.
5. **Coercion Resistance or Receipt-Freeness**: Does not prevent voters from disclosing randomness if they generate ballots independently.
6. **Machine-Checked Formal Verification**: Protocols follow published algorithms (CDS94, Chaum-Pedersen) but lack machine-checked proofs (e.g. EasyCrypt).
7. **Production Election Readiness**: Academic research prototype for applied cryptographic evaluation only.

---

## 10. Empirical Benchmarks (Authoritative 3-Trial Medians)

Empirical evaluation over NIST P-256 (`secp256r1`) with 4 candidate slots ($k=4$), conducted across 3 independent runs per scale (seeds 42, 143, 244) with `gc.collect()` isolation:

| Scale (Ballots) | v3.0 Size | v3.1 ZKP Size | Size Factor | v3.0 Gen (Median) | v3.1 Gen (Median) | Gen Overhead | v3.0 Verif (Median) | v3.1 Verif (Median) | Verif Overhead |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **10** | 1,973 B | 6,501 B | 3.29x | 1.91 s (±0.45s) | 9.07 s (±1.09s) | +376.1% | 0.049 s (±0.007s) | 8.55 s (±0.49s) | +17,412.3% |
| **50** | 1,973 B | 6,501 B | 3.29x | 7.17 s (±0.74s) | 43.14 s (±6.48s) | +501.4% | 0.28 s (±0.017s) | 38.58 s (±1.40s) | +13,893.4% |
| **100** | 1,974 B | 6,503 B | 3.29x | 13.83 s (±0.09s) | 82.27 s (±1.34s) | +494.7% | 0.53 s (±0.009s) | 76.90 s (±2.10s) | +14,479.1% |

*Raw trial data and variability metrics are documented in `evidence/v3_1_zkp_benchmark_results.json`.*
