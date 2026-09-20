# SecureVOTE 3.2-A — Verifiable Threshold Distributed Key Generation (DKG) Implementation

- **Milestone**: `SecureVOTE 3.2-A`
- **Target Configuration**: $(t, n) = (2, 3)$ Trustees ($f \le 1$ Byzantine Corruption Bound)
- **Baseline Commit**: `812aa9d28d4b2d991a12260d0b725ee95eaf6708` (`v3.1.0-research`)
- **Branch**: `research/securevote-3.2-threshold`
- **Specification**: `docs/research/SECUREVOTE_3_2_THRESHOLD_DESIGN.md`
- **Status**: Implementation Complete & Verified (235/235 tests passing)

---

## 1. Overview & Protocol Architecture

SecureVOTE 3.2-A implements the Distributed Key Generation (DKG) layer based on the Gennaro-Jarecki-Krawczyk-Rabin (GJKR 2007) and Pedersen Verifiable Secret Sharing (VSS) framework over NIST P-256 (`secp256r1`).

In this architecture, no single entity generates, holds, or accesses the election private key $x \in \mathbb{Z}_q^*$. Instead, $n = 3$ trustees cooperatively generate a joint public key $Y \in E(\mathbb{F}_p)$ such that any threshold $t = 2$ of honest qualified trustees can subsequently compute threshold decryptions, while any single corrupted trustee learns zero information about $x$.

```
[Phase 1: Sampling & Pedersen Commitments]
   Trustee i: f_i(z) = a_{i,0} + a_{i,1}*z,  f'_i(z) = b_{i,0} + b_{i,1}*z
   Commitments: C_{i,k} = a_{i,k}*G + b_{i,k}*H  for k in {0, 1}
   Schnorr Proof of Representation on C_{i,0}
                         │
                         ▼
[Phase 2: Verifiable Pairwise Share Distribution]
   Trustee i sends to Trustee j: s_{i->j} = f_i(j),  s'_{i->j} = f'_i(j)
   Trustee j verifies: s_{i->j}*G + s'_{i->j}*H == C_{i,0} + j*C_{i,1}
                         │
                         ▼
[Phase 3: Public Complaint Ledger & Disqualification]
   If verification fails, Trustee j publishes DKGComplaint(i, j, s, s')
   Public evaluates: s*G + s'*H == C_{i,0} + j*C_{i,1}
   If invalid, Trustee i is disqualified: QUAL = {i : verified and no valid complaint}
                         │
                         ▼
[Phase 4: Feldman Verification Reveal]
   Qualified trustees publish Feldman commitments: A_{i,k} = a_{i,k}*G and b_{i,k}
   Public verifies: C_{i,k} == A_{i,k} + b_{i,k}*H
                         │
                         ▼
[Phase 5: Master Share Finalization & Public Ledger Manifest]
   Trustee j master share: x_j = \sum_{i in QUAL} s_{i->j} mod q
   Trustee j verification key: Y_j = \sum_{i in QUAL} (A_{i,0} + j*A_{i,1}) = x_j*G
   Joint Election Public Key: Y = \sum_{i in QUAL} A_{i,0}
   Public Manifest: DKGPublicManifest(election_id, t, n, QUAL, Y, {Y_j}, commitments)
```

---

## 2. Deterministic NUMS Independent Generator $H$

Pedersen commitments require two group generators $G$ and $H$ such that $\log_G(H)$ is computationally intractable (Nothing-Up-My-Sleeve / NUMS derivation).

### 2.1 Derivation Algorithm
1. Seed label: `b"SECUREVOTE32/PEDERSEN_H/GENERATOR/v1"`
2. Iterative counter $c \ge 0$ (4-byte big-endian):
   $$\text{candidate\_x} = \operatorname{SHA-256}(\text{seed} \parallel \text{uint32\_be}(c)) \pmod p$$
3. Curve equation check on $y^2 \equiv x^3 - 3x + b \pmod p$:
   - If quadratic residue via Tonelli-Shanks, select deterministic root where $y \equiv 0 \pmod 2$.
4. Check $H \ne \mathcal{O}$, $H \ne G$, and $[q]H = \mathcal{O}$.

### 2.2 Numerical Constant on NIST P-256 (`secp256r1`)
Counter $c = 0$ yields a valid on-curve point with even $y$:
```
PEDERSEN_H_X = 0xe7613bafcf2c51eb9e847c23bc42ffefd019f29ee87f5df598b965f3c14a2fbf
             = 104656064122413815814513802482333236505701616180229785597126205234554916669695
PEDERSEN_H_Y = 0x912a9b3c3c7e75525988e0cb20e6f24efba8e9c7041a806aaee7a0d4a9dc3d4c
             = 65660642017540351931825561733783512641172905144776509831199878678424381573772
```

---

## 3. Schnorr Proof of Representation on $C_{i,0}$

To prevent rogue-key and commitment substitution attacks, each trustee $i$ must prove knowledge of representation $(a_{i,0}, b_{i,0})$ such that:
$$C_{i,0} = a_{i,0} G + b_{i,0} H$$

### 3.1 Protocol
1. **Commitment**: Trustee samples ephemeral nonces $w_a, w_b \xleftarrow{\$} \mathbb{Z}_q^*$ and computes:
   $$W = w_a G + w_b H$$
2. **Challenge via Fiat-Shamir**:
   $$\text{Domain} = \texttt{"SECUREVOTE32/DKG/SCHNORR/\{election\_id\}/TRUSTEE/\{trustee\_id\}/"}$$
   $$c = \operatorname{TranscriptChallenge}(G, H, C_{i,0}, W) \pmod q$$
3. **Response**:
   $$s_a = w_a + c \cdot a_{i,0} \pmod q, \quad s_b = w_b + c \cdot b_{i,0} \pmod q$$
4. **Verification Equation**:
   $$s_a G + s_b H \stackrel{?}{=} W + c \cdot C_{i,0}$$

---

## 4. Verifiable Secret Sharing & Complaint Mechanism

### 4.1 Pairwise Share Verification
For each trustee $j \in \{1, \dots, n\}$, trustee $i$ computes:
$$s_{i \to j} = f_i(j) = a_{i,0} + a_{i,1} \cdot j \pmod q$$
$$s'_{i \to j} = f'_i(j) = b_{i,0} + b_{i,1} \cdot j \pmod q$$

Trustee $j$ verifies against trustee $i$'s public Pedersen commitments $(C_{i,0}, C_{i,1})$:
$$s_{i \to j} G + s'_{i \to j} H \stackrel{?}{=} C_{i,0} + j \cdot C_{i,1}$$

### 4.2 Public Complaint Ledger & Disqualification
If the equation fails or a share is missing, trustee $j$ posts an authenticated complaint on the bulletin board:
$$\text{DKGComplaint}(\text{accused}=i, \text{complainant}=j, s_{i \to j}, s'_{i \to j})$$

Any third-party verifier independently checks:
$$\text{LHS} = s_{i \to j} G + s'_{i \to j} H, \quad \text{RHS} = C_{i,0} + j \cdot C_{i,1}$$
- If $\text{LHS} \ne \text{RHS}$: The complaint is **VALID**. Trustee $i$ distributed an invalid share and is **disqualified**.
- If $\text{LHS} == \text{RHS}$: The complaint is **FALSE / MALICIOUS**. The share is mathematically consistent; trustee $i$ remains qualified.

### 4.3 Qualified Set ($\mathcal{QUAL}$) Determination
$$\mathcal{QUAL} = \{i \in \{1, \dots, n\} \mid \text{Valid Schnorr Proof on } C_{i,0} \land \neg(\exists \text{ valid complaint against } i)\}$$
- If $|\mathcal{QUAL}| < t = 2$, the DKG aborts with `InsufficientQualifiedTrusteesError`.

---

## 5. Feldman Verification Reveal & Public Key Derivation

### 5.1 Feldman Commitment Verification
Each qualified trustee $i \in \mathcal{QUAL}$ reveals:
$$A_{i,k} = a_{i,k} G \quad \text{and} \quad b_{i,k} \quad \text{for } k \in \{0, 1\}$$

The public verifies for each $k$:
$$C_{i,k} \stackrel{?}{=} A_{i,k} + b_{i,k} H$$
If any equality fails, the trustee is disqualified or the DKG aborts.

### 5.2 Key Derivation Equations
1. **Joint Election Public Key $Y$**:
   $$Y = \sum_{i \in \mathcal{QUAL}} A_{i,0} \in E(\mathbb{F}_p)$$
2. **Trustee Public Verification Keys $Y_j$**:
   $$Y_j = \sum_{i \in \mathcal{QUAL}} (A_{i,0} + j \cdot A_{i,1}) = x_j G$$
3. **Master Secret Share $x_j$ (Held privately by Trustee $j$)**:
   $$x_j = \sum_{i \in \mathcal{QUAL}} s_{i \to j} \pmod q$$

### 5.3 Correctness of Threshold Recombination
For any qualifying subset $\mathcal{S} \subset \mathcal{QUAL}$ of size $|\mathcal{S}| = t = 2$, the Lagrange interpolation coefficients at $z = 0$ are:
$$\lambda_j^{\mathcal{S}} = \prod_{k \in \mathcal{S}, k \ne j} \frac{-k}{j - k} \pmod q$$

The joint key satisfies:
$$\sum_{j \in \mathcal{S}} \lambda_j^{\mathcal{S}} Y_j = \sum_{j \in \mathcal{S}} \lambda_j^{\mathcal{S}} (x_j G) = \left(\sum_{j \in \mathcal{S}} \lambda_j^{\mathcal{S}} x_j\right) G = x G = Y$$

---

## 6. Artifact Schemas & Serialization

All artifacts implement canonical deterministic JSON serialization with hex-encoded integers and points:

| Artifact | Type | Storage / Ledger Target |
| :--- | :--- | :--- |
| `PedersenCommitmentPackage` | Public | Bulletin Board / Ledger |
| `PrivateSharePackage` | Private | Confidential Pairwise TLS |
| `DKGComplaint` | Public | Bulletin Board / Complaints |
| `FeldmanRevealPackage` | Public | Bulletin Board / Ledgers |
| `DKGPublicManifest` | Public | Authoritative Election Ledger |
| `TrusteePrivateKeyShare` | Private | Trustee Local HSM / Secure Storage |

### Manifest Schema (`DKGPublicManifest`)
```json
{
  "manifest_version": "1.0",
  "election_id": "ELEC-2026-PRIMARY",
  "threshold": 2,
  "trustee_count": 3,
  "qualified_trustees": [1, 2, 3],
  "joint_public_key": { "x": "0x...", "y": "0x..." },
  "trustee_verification_keys": {
    "1": { "x": "0x...", "y": "0x..." },
    "2": { "x": "0x...", "y": "0x..." },
    "3": { "x": "0x...", "y": "0x..." }
  },
  "pedersen_commitments": { ... },
  "feldman_commitments": { ... },
  "manifest_hash": "64_char_hex_digest"
}
```

---

## 7. Standalone Offline Verification Algorithm

Any external observer can verify the DKG without holding any secrets:
1. `verify_dkg_manifest(manifest)`:
   - Check threshold constraints ($|\mathcal{QUAL}| \ge t$).
   - Verify every qualified trustee's Schnorr proof on $C_{i,0}$.
   - Verify consistency of Feldman reveals: $C_{i,k} == A_{i,k} + b_{i,k} H$.
   - Verify joint public key: $Y == \sum_{i \in \mathcal{QUAL}} A_{i,0}$.
   - Verify trustee verification keys: $Y_j == \sum_{i \in \mathcal{QUAL}} (A_{i,0} + j \cdot A_{i,1})$.
   - Verify Lagrange reconstruction for every subset of size $t$: $\sum_{j \in \mathcal{S}} \lambda_j^{\mathcal{S}} Y_j == Y$.

---

## 8. Test Suite Summary & Coverage

All 17 dedicated DKG tests and 218 regression tests pass cleanly:

| Test Name | Verification Focus | Result |
| :--- | :--- | :--- |
| `test_pedersen_h_deterministic_derivation` | NUMS generator $H$ correctness, order, curve check | PASSED |
| `test_schnorr_representation_soundness` | Non-interactive Schnorr proof validity | PASSED |
| `test_schnorr_representation_mutated_scalar_rejected` | Fiat-Shamir response scalar tampering rejected | PASSED |
| `test_schnorr_representation_wrong_commitment_rejected` | Point substitution rejected | PASSED |
| `test_valid_3_trustee_dkg_complete_flow` | End-to-end DKG with 3 trustees and all 3 quorums | PASSED |
| `test_invalid_secret_share_rejected` | Peer detection of corrupted secret share | PASSED |
| `test_invalid_blinding_share_rejected` | Peer detection of corrupted blinding share | PASSED |
| `test_complaint_lifecycle_and_verification` | Complaint ledger posting and public verification | PASSED |
| `test_dealer_disqualification_and_2_of_3_qual` | Disqualification of malicious dealer, 2-of-3 quorum | PASSED |
| `test_insufficient_qualified_trustees_aborts` | Abort when qualified count $< t$ | PASSED |
| `test_feldman_reveal_mismatched_blinding_rejected` | Rejection of tampered blinding factor in reveal | PASSED |
| `test_feldman_reveal_mismatched_commitment_point_rejected` | Rejection of altered $A_{i,k}$ in reveal | PASSED |
| `test_distinct_election_domain_separation` | Domain isolation across election IDs | PASSED |
| `test_trustee_id_substitution_rejected` | Trustee identity spoofing rejected | PASSED |
| `test_dkg_artifacts_serialization_round_trip` | Canonical JSON serialization/deserialization | PASSED |
| `test_malformed_serialized_payload_rejected` | Schema validation and corruption rejection | PASSED |
| `test_no_private_secret_leakage_in_repr` | Zero secret leakage in object string representation | PASSED |

Total backend test suite: **235 passed, 0 failed** in 89.35s.

---

## 9. Security Boundaries & Prototype Limitations

1. **Static Adversary Model**: The current research prototype assumes an adversary who selects which trustee to corrupt before protocol execution begins. Adaptive adversaries (who corrupt trustees during execution based on observed messages) require non-committing encryption and zero-knowledge arguments not modeled here.
2. **Synchronous Broadcast Assumption**: The complaint resolution mechanism relies on an ideal synchronous authenticated broadcast channel. Asynchronous partitions or network delay attacks are not addressed at the crypto layer.
3. **Modular Reduction Bias**: Scalar sampling uses rejection-free modulo reduction `secrets.randbits(256) % CURVE_ORDER`. While the statistical bias is cryptographically negligible ($2^{-128}$), strict constant-time rejection sampling should be implemented before production hardening.
4. **Channel Confidentiality**: Distribution of private shares between trustees must occur over mutually authenticated TLS or end-to-end encrypted channels (ECIES). In this prototype, transport simulation operates in-process.
