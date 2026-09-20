# SecureVOTE 3.0 — Cryptographic Specification

**Protocol Identifier**: `SECUREVOTE3`  
**Version**: `3.0.0-research`  
**Cryptographic Primitive**: Exponential ElGamal over NIST P-256 (`secp256r1`)  
**Commitment Scheme**: Domain-Separated SHA-256

---

## 1. Mathematical Foundation

### 1.1 Underlying Group

SecureVOTE 3.0 operates over the prime-order elliptic curve group **NIST P-256 (secp256r1 / prime256v1)** defined by:

$$y^2 \equiv x^3 - 3x + b \pmod p$$

where:
- Base field prime: $p = 2^{256} - 2^{224} + 2^{192} + 2^{96} - 1$
- Generator point: $G = (G_x, G_y)$
- Group order: $q = \text{0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551}$
- Cofactor: $h = 1$

All point arithmetic utilizes Jacobian coordinates $(X, Y, Z)$ where $(x, y) = (X/Z^2 \pmod p, Y/Z^3 \pmod p)$, eliminating modular inversions during scalar multiplication.

---

## 2. Key Management

### 2.1 Keypair Generation

1. An election authority generates a private key scalar:
   $$x \leftarrow_R [1, q - 1]$$
   using cryptographically secure random bytes (`os.urandom(32)`).
2. The public key point is computed via scalar multiplication:
   $$Y = x \cdot G$$
3. The public key is validated:
   $$Y \neq \mathcal{O} \quad \text{and} \quad Y \in E(\mathbb{F}_p)$$

### 2.2 Key Fingerprint

The key fingerprint is a domain-separated SHA-256 digest:
$$\text{FP}(Y) = \text{SHA-256}(\text{"SECUREVOTE3/KEY/"} \mathbin{\Vert} \text{hex}(Y_x) \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{hex}(Y_y))$$

---

## 3. Ballot Encoding & Encryption

### 3.1 One-Hot Vector Representation

For an election with $k$ candidates, a vote for candidate index $i \in \{0, \dots, k-1\}$ is represented as a $k$-dimensional one-hot integer vector:
$$\mathbf{v} = [v_0, v_1, \dots, v_{k-1}], \quad v_j = \begin{cases} 1 & \text{if } j = i \\ 0 & \text{if } j \neq i \end{cases}$$

### 3.2 Exponential ElGamal Encryption

Each vector slot $v_j$ is encrypted independently under public key $Y$:
1. Sample random nonce $r_j \leftarrow_R [1, q - 1]$.
2. Compute ciphertext pair:
   $$C_{1,j} = r_j \cdot G$$
   $$C_{2,j} = r_j \cdot Y + v_j \cdot G$$
3. Output ciphertext $\text{Enc}(v_j) = (C_{1,j}, C_{2,j})$.

For $v_j = 0$, $v_j \cdot G = \mathcal{O}$ (the point at infinity).  
For $v_j = 1$, $v_j \cdot G = G$.

---

## 4. Ballot Commitments & Artifact Hashing

### 4.1 Domain Separation Prefixes

| Context | Prefix Pattern |
|---------|----------------|
| Key Material | `SECUREVOTE3/KEY/` |
| Ballot Artifact | `SECUREVOTE3/BALLOT/{election_id}/` |
| Ballot Commitment | `SECUREVOTE3/COMMITMENT/{election_id}/` |
| Tally Artifact | `SECUREVOTE3/TALLY/{election_id}/` |

### 4.2 Ballot Commitment

A cryptographic commitment binds the encrypted ballot artifact:
$$\text{Commitment} = \text{SHA-256}\Big(\text{"SECUREVOTE3/COMMITMENT/"} \mathbin{\Vert} \text{canonical\_json}(\text{payload})\Big)$$
where $\text{payload}$ includes:
- `protocol_version`
- `election_id`
- `artifact_id` (random UUIDv4)
- `encrypted_vote` (all serialized ciphertext slots)
- `candidate_count`
- `key_fingerprint`

---

## 5. Homomorphic Tallying

### 5.1 Component-Wise Additive Aggregation

Given $N$ encrypted ballots where ballot $i$ has slots $\mathbf{C}^{(i)} = [(C_{1,0}^{(i)}, C_{2,0}^{(i)}), \dots, (C_{1,k-1}^{(i)}, C_{2,k-1}^{(i)})]$, the aggregate tally for candidate slot $j$ is:
$$C_{1,j}^{\text{agg}} = \sum_{i=1}^N C_{1,j}^{(i)} = \left(\sum_{i=1}^N r_j^{(i)}\right) \cdot G$$
$$C_{2,j}^{\text{agg}} = \sum_{i=1}^N C_{2,j}^{(i)} = \left(\sum_{i=1}^N r_j^{(i)}\right) \cdot Y + \left(\sum_{i=1}^N v_j^{(i)}\right) \cdot G$$

### 5.2 Decryption via Discrete-Log Recovery

To recover the plaintext tally $T_j = \sum_{i=1}^N v_j^{(i)}$:
1. Compute the discrete-log target point:
   $$M_j = C_{2,j}^{\text{agg}} - x \cdot C_{1,j}^{\text{agg}} = T_j \cdot G$$
2. If $M_j = \mathcal{O}$, then $T_j = 0$.
3. Otherwise, solve $M_j = T_j \cdot G$ using the Baby-Step Giant-Step (BSGS) algorithm bounded by maximum ballot count $N$.
   Time complexity: $\mathcal{O}(\sqrt{N})$ group operations.
   Space complexity: $\mathcal{O}(\sqrt{N})$ points.

### 5.3 Exact Zero-Drift Reconciliation Invariant

The decrypted candidate tallies must strictly satisfy:
$$\sum_{j=0}^{k-1} T_j \equiv N_{\text{ballots}}$$
Any non-zero drift flags a reconciliation invariant failure.

---

## 6. Independent Verifier (10 Checkpoints)

The standalone verifier (`standalone_verifier/v3_verifier.py`) operates offline with **zero database, ORM, or web dependencies**:

1. **Checkpoint 1 — Protocol Version**: Validates protocol identifier equals `SECUREVOTE3`.
2. **Checkpoint 2 — Public Key Integrity**: Confirms public key lies on `secp256r1` and matches declared fingerprint.
3. **Checkpoint 3 — Configuration Integrity**: Asserts election identifier and candidate slate $\ge 2$.
4. **Checkpoint 4 — Ballot Structural Well-Formedness**: Verifies schema across all cast ballots.
5. **Checkpoint 5 — Ciphertext Curve Verification**: Asserts every $C_1, C_2$ coordinate pair satisfies $y^2 \equiv x^3 - 3x + b \pmod p$.
6. **Checkpoint 6 — Ballot Commitment Recomputation**: Recomputes SHA-256 commitment from raw ciphertexts.
7. **Checkpoint 7 — Artifact Hash Verification**: Recomputes canonical artifact hash.
8. **Checkpoint 8 — Independent Homomorphic Aggregation**: Recomputes point additions across all ballots and compares against published aggregate.
9. **Checkpoint 9 — Tally Commitment Recomputation**: Validates published tally commitment.
10. **Checkpoint 10 — Zero-Drift Reconciliation**: Confirms $\sum \text{Tallies} = N_{\text{ballots}}$.

---

## 7. Security Boundaries, Status & Limitations

### 7.1 Formal Cryptographic Assurance Matrix

| Property | Status | Evidence / Implementation Scope |
|---|---|---|
| **Artifact Integrity** | **IMPLEMENTED** | Checkpoints 1, 4, 7 recompute canonical hashes across all artifacts. |
| **Ciphertext Point Validity** | **IMPLEMENTED** | Checkpoint 5 asserts all $(C_1, C_2)$ coordinates lie on `secp256r1`. |
| **Commitment Integrity** | **IMPLEMENTED** | Checkpoint 6 independently recomputes domain-separated SHA-256 commitments. |
| **Homomorphic Aggregation Correctness** | **IMPLEMENTED** | Checkpoint 8 re-aggregates every ballot independently and compares against published aggregate point. |
| **Zero-Drift Tally Reconciliation** | **IMPLEMENTED** | Checkpoint 10 asserts $\sum T_j \equiv N_{\text{ballots}}$ with exact zero drift. |
| **Ballot Plaintext Confidentiality (at Rest)** | **IMPLEMENTED** | Candidate choices are stored as randomized ciphertexts, not plaintexts. |
| **Individual Verifiability (Recorded-as-Cast)** | **PARTIAL** | Voter can look up their SHA-256 commitment on the public bulletin board, but cannot verify cast-as-intended without a Benaloh challenge/receipt. |
| **Universal Verifiability (Tallied-as-Recorded)** | **PARTIAL** | The public can verify that the published tally equals the homomorphic sum of published ciphertexts, but cannot verify that ciphertexts contain valid 0/1 votes. |
| **Zero-Knowledge Ballot Validity Proofs** | **NOT IMPLEMENTED** | Proof that $v_j \in \{0, 1\}$ and $\sum v_j = 1$ is not implemented; system currently relies on trusted client/firmware. |
| **End-to-End Verifiability (E2E-V)** | **NOT IMPLEMENTED** | Requires both ballot validity ZKPs and individual cast-as-intended mechanisms. |
| **Threshold Decryption (DKG)** | **NOT IMPLEMENTED** | Single private scalar held in server RAM during election. |
| **Voter Anonymity / Mix-Net** | **NOT IMPLEMENTED** | Timestamps and device sequence numbers permit temporal metadata correlation. |

### 7.2 Explicit Limitations
- **No Claims of E2E-V**: SecureVOTE 3.0 provides homomorphic tallying and independent aggregate verification, but is NOT fully End-to-End Verifiable due to the lack of ballot validity proofs and Benaloh voter challenges.
- **Single-Authority Decryption**: In prototype mode, threshold decryption (DKG) is not active; the private key is held in server memory.
- **Timing & Metadata Side-Channels**: Device sequence numbers and timestamps allow correlation without an anonymous mix-net or shuffle protocol.
- **Academic Research Prototype**: SecureVOTE is an educational security prototype, not certified election equipment.

