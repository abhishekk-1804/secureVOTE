# SecureVOTE 3.3 — Cryptographic Hardening Specification & Audit Reference

**Document Status:** Research & Audit Reference  
**Classification:** Cryptographic Hardening Specification  
**Branch:** `research/securevote-3.3-hardening`  
**Target Release:** SecureVOTE v3.3 Hardening Pass  
**Baseline Pinned Tags:** `v3.2.0-research` (`58dc44f`), `v3.3.0-research` (`1b3eb6f`)  

---

## 1. Executive Summary & Hardening Objectives

The SecureVOTE v3.3 Cryptographic Hardening Pass reinforces the security properties, deterministic behavior, and input validation of the cryptographic subsystem without altering released historical tags (`v3.2.0-research` and `v3.3.0-research`) and without altering protocol invariants.

### Scope of Hardening
1. **Hash-to-Scalar & Fiat-Shamir Analysis:** Formalized the statistical bias analysis of the existing SHA-256 modular reduction and implemented the RFC 9380 Section 5.3.1 `expand_message_xmd` construction with $L = 48$ bytes ($384$ bits).
2. **Transcript Domain Separation Audit:** Verified domain separation across all Zero-Knowledge Proof (ZKP) and Distributed Key Generation (DKG) transcripts to prevent cross-domain proof replay.
3. **Canonical Serialization Hardening:** Enforced recursive floating-point rejection, deterministic key sorting, compact separator formatting, and UTF-8 determinism.
4. **Point & Scalar Validation:** Hardened elliptic curve point-on-curve verification, infinity point rejection, negative coordinate rejection, and non-boolean scalar type/range validation.
5. **Side-Channel & Timing Limitation Disclosures:** Documented variable-time Jacobian arithmetic in Python and its side-channel implications.
6. **Information Leakage Prevention:** Verified that zero private keys, secret shares, or nonces are exposed in exceptions, traces, or log strings.
7. **Independent Standalone Verifier Extension:** Added Checkpoint 11 for verifiable threshold tally audit, validating Chaum-Pedersen discrete-log equality proofs and Lagrange interpolation over elliptic curve points.

---

## 2. Hash-to-Scalar & Fiat-Shamir Transformation

### 2.1 Current Implementation: SHA-256 with Direct Modular Reduction
In SecureVOTE v3.1, v3.2, and v3.3, Fiat-Shamir challenges are computed using domain-separated SHA-256 over canonical JSON transcripts:

$$\text{digest} = \text{SHA-256}(\text{canonical\_json}(\text{payload}))$$
$$c = (\text{int.from\_bytes}(\text{digest}, \text{"big"}) \bmod (q - 1)) + 1$$

where $q$ is the prime group order of NIST P-256 ($\text{secp256r1}$):
$$q = 115792089210356248762697446949407573529996955224135760342422259061068514753269$$

### 2.2 Statistical Bias Analysis
Because $2^{256}$ is not an integer multiple of $(q - 1)$, direct reduction introduces a modulo bias:

$$\Delta = \frac{2^{256} \bmod (q - 1)}{2^{256}} \approx 2^{-32}$$

While common in engineering implementations of discrete-log proofs (and sufficient to prevent practical forgery in standard threat models), this statistical distance does not satisfy the theoretical bound of $\Delta \le 2^{-128}$ required by modern standards such as RFC 9380.

### 2.3 RFC 9380 `expand_message_xmd` Implementation
To provide a path toward standardized provable security while preserving backward compatibility for existing ballots:
- **`expand_message_xmd`**: Implemented per RFC 9380 Section 5.3.1 using SHA-256 with block size $s = 64$ bytes and digest size $b = 32$ bytes.
- **Wide Reduction with $L = 48$ bytes (384 bits):**
  $$L = \left\lceil \frac{256 + 128}{8} \right\rceil = 48 \text{ bytes}$$
  Deriving 48 bytes via `expand_message_xmd` guarantees a statistical distance from uniform modulo $(q - 1)$ bounded by:
  $$\Delta \le 2^{-128}$$
- **Compatibility Policy:** Existing proof systems continue using `challenge_scalar` for exact protocol compatibility with existing databases and ballots; `challenge_scalar_rfc9380` is available for future protocol revisions.

---

## 3. Transcript Domain Separation Reference

To ensure cryptographic independence and prevent cross-context replay attacks, each protocol component utilizes a distinct, structured domain separation tag:

| Protocol Stage | Context / Role | Domain Separation Tag Format |
|---|---|---|
| **v3.1 ZKP** | Slot Disjunctive Proof | `SECUREVOTE31/ZKP/SLOT_PROOF/{election_id}/CAND/{candidate_id}/` |
| **v3.1 ZKP** | Sum Equality Proof | `SECUREVOTE31/ZKP/SUM_PROOF/{election_id}/` |
| **v3.2 Threshold** | Partial Decryption Proof | `SECUREVOTE32/ZKP/PARTIAL_DECRYPT/{election_id}/{candidate_id}/TRUSTEE/{trustee_id}/` |
| **v3.2 DKG** | Schnorr Proof of Knowledge | `SECUREVOTE32/DKG/SCHNORR_POK/{election_id}/TRUSTEE/{trustee_id}/` |
| **v3.2 DKG** | NUMS Generator $H$ | `SECUREVOTE32/PEDERSEN_H/GENERATOR/v1` |

### Security Invariants
1. A proof generated for a candidate slot cannot be accepted for a sum proof or another candidate slot.
2. A partial decryption proof from Trustee $A$ cannot be accepted as coming from Trustee $B$.
3. An election ID mismatch immediately alters the transcript hash, producing a challenge mismatch error.

---

## 4. Canonical Serialization & Float Rejection

SecureVOTE relies on canonical JSON serialization for commitment generation, artifact hashing, and Fiat-Shamir transcripts.

### 4.1 Strict Float Rejection
IEEE 754 floating-point representations are non-canonical across architectures, operating systems, and runtimes due to negative zero (`-0.0`), NaN payloads, subnormals, and non-deterministic string formatting.
- **Rule:** Floating-point numbers (`float`) are strictly forbidden in all serialized cryptographic structures.
- **Enforcement:** `canonical_json` recursively inspects all objects prior to serialization. Any occurrence of `float` as a value, list element, or dictionary key raises `app.crypto.exceptions.SerializationError`.

### 4.2 Deterministic Formatting
Canonical JSON strings are produced with:
- Alphabetically sorted keys (`sort_keys=True`).
- Compact separators (`separators=(',', ':')` with zero whitespace).
- Unescaped UTF-8 characters (`ensure_ascii=False`).

---

## 5. Point & Scalar Validation Rules

All operations on NIST P-256 ($\text{secp256r1}$) adhere to the following validation constraints:

### 5.1 Coordinate and Curve Verification
For any point $P = (x, y)$:
1. **Type Constraint:** $x$ and $y$ must be non-boolean integers (`type(coord) is int`).
2. **Range Constraint:** $0 \le x < p$ and $0 \le y < p$, where $p = 2^{256} - 2^{224} + 2^{192} + 2^{96} - 1$.
3. **Curve Equation:** Coordinates must strictly satisfy:
   $$y^2 \equiv x^3 - 3x + b \pmod p$$
4. **Hex Encoding:** Deserialization requires valid hexadecimal strings; negative hex prefixes (`-`) are explicitly rejected.

### 5.2 Point at Infinity Policy
- **Public Keys ($Y, Y_i$):** MUST NOT be the point at infinity.
- **Ciphertext $C_1 = r \cdot G$:** MUST NOT be the point at infinity.
- **Ciphertext $C_2 = r \cdot Y + m \cdot G$:** Permitted to be infinity only when $m = 0$ and $r \cdot Y = \mathcal{O}$ (neutral point).
- **Proof Commitments ($comm_1, comm_2, a, b$):** MUST NOT be the point at infinity.

### 5.3 Scalar Validation
For any scalar $s$:
1. $s$ must be a non-boolean integer (`type(s) is int`).
2. $0 \le s < q$ (or $1 \le s < q$ for private keys, nonces, and challenges where zero is prohibited).

---

## 6. NIST P-256 Implementation & Side-Channel Notice

### Variable-Time Jacobian Coordinates Limitation
The internal elliptic curve operations in `app.crypto.elgamal` use pure Python Jacobian coordinates arithmetic:
- Point addition and doubling involve branch conditions dependent on point coordinates and equality.
- Python integer multiplication and modular arithmetic are variable-time and not constant-time.
- **Security Implication:** This implementation is vulnerable to microarchitectural cache-timing and execution-time side-channel attacks if executed in an untrusted, co-located hardware environment.
- **Mitigation/Architecture Context:** SecureVOTE is a distributed research platform where private operations (trustee share operations) occur inside isolated trustee process environments. However, **no claim of constant-time or side-channel immunity is made.**

---

## 7. Security Error Handling & Secret Shielding

### 7.1 Ephemeral Nonce Hygiene
In `prove_partial_decryption`, ephemeral nonce $w$ is sampled using `secrets.randbits(256)`. In a `finally:` block:
```python
finally:
    w = 0
```
- **Explicit Claim:** Python integer rebinding does **not** guarantee hardware or CPython heap memory zeroization.
- The nonce $w$ is not serialized, persisted, logged, or returned.

### 7.2 Fail-Closed Error Messages
Exceptions raised during cryptographic verification (`PartialDecryptionProofError`, `SchnorrProofError`, `InvalidProofError`, `InvalidShareError`):
- Never format or interpolate private keys, secret shares, or nonces into error messages.
- Fail closed by raising specific exceptions or returning `False` in high-level verifiers.

---

## 8. Independent Standalone Verifier (11-Checkpoint Pipeline)

The standalone verifier (`backend/standalone_verifier/v3_verifier.py`) operates with zero dependencies on database, ORM, or web framework components.

### Verification Sequence:
1. **Checkpoint 1:** Protocol Version (`SECUREVOTE3`, `SECUREVOTE31`, `SECUREVOTE32`, `SECUREVOTE33`).
2. **Checkpoint 2:** Public Key secp256r1 validity and SHA-256 fingerprint matching.
3. **Checkpoint 3:** Election Configuration and Candidate List validation.
4. **Checkpoint 4:** Ballot Structural Integrity and Election ID binding.
5. **Checkpoint 5:** Every Ciphertext Slot point-on-curve verification.
6. **Checkpoint 6:** Independent Recomputation of Ballot Commitments.
7. **Checkpoint 7:** Independent Recomputation of Ballot Artifact Hashes.
8. **Checkpoint 7B:** Zero-Knowledge Ballot Validity Proofs (∀j: $v_j \in \{0, 1\} \land \sum v_j = 1$).
9. **Checkpoint 8:** Independent Homomorphic Aggregation of All Ballots.
10. **Checkpoint 9:** Tally Commitment and Artifact Hash Validation.
11. **Checkpoint 10:** Zero-Drift Decrypted Tally Reconciliation.
12. **Checkpoint 11:** Verifiable Threshold Tally Audit (Chaum-Pedersen equality proofs and Lagrange EC point combination).

---

## 9. Research Boundaries & Honest Disclosures

SecureVOTE 3.3 is an academic and research verification platform. The following explicit disclaimers apply:
1. **No End-to-End Verifiability (E2Ev):** While individual cryptographic checkpoints are verifiable, the system as a whole does not provide receipt-free, coercion-resistant E2E verifiability under standard academic definitions (e.g., Juels-Catalano-Jakobsson or Benaloh).
2. **No Mathematical Anonymity:** Homomorphic aggregation hides individual votes within the tally, but physical network traffic, device IDs, and voter authentication logs may link voter activity.
3. **Not Production Ready:** This implementation is not certified for legally binding public elections.
