# SecureVOTE 3.3 Phase 2 — Portable Cryptographic Evidence Bundles Specification & Audit Reference

**Document Status:** Research Specification & Empirical Verification Reference  
**Classification:** Cryptographic Evidence Architecture  
**Protocol Version:** `SECUREVOTE-EVIDENCE-BUNDLE-1`  
**Canonicalization Version:** `RFC-CANONICAL-JSON-1`  
**Branch:** `research/securevote-3.3-phase2`  
**Baseline Pinned Tags:** `v3.2.0-research` (`58dc44f`), `v3.3.0-research` (`1b3eb6f`)  

---

## 1. Executive Summary & Mission

SecureVOTE 3.3 Phase 2 introduces **Portable Cryptographic Evidence Bundles** (`SECUREVOTE-EVIDENCE-BUNDLE-1`), a self-contained, deterministic election evidence distribution format. 

### Core Objective
Enable independent third-party auditors, election observers, civil society organizations, and participants to mathematically verify the complete integrity, validity, and tally of an election **without**:
- FastAPI or backend web server processes
- SQLAlchemy or active database connections
- SQLite or persistent disk state
- Network access or external API calls
- Trust in server-side application logs or administrative claims

The bundle encapsulates every mathematical artifact generated during the election lifecycle—context definitions, public keys, encrypted ballots, ballot commitments, zero-knowledge validity proofs, homomorphic aggregate tallies, Distributed Key Generation (DKG) manifests, trustee partial decryption shares, Chaum-Pedersen equality proofs, and detached digital signatures—into a standalone directory or `.zip` archive.

---

## 2. Bundle Architecture & Directory Hierarchy

A SecureVOTE portable evidence bundle is organized into a strictly normalized directory structure:

```
<bundle_root>/
├── context/
│   ├── election.json                  # Canonical election parameters, ID, candidate list, ballot count
│   └── public_key.json                # Master/joint NIST P-256 public key and fingerprint
├── ballots/
│   ├── ballot_000001.json             # Encrypted ballot slots and commitments
│   └── ...
├── proofs/
│   ├── proof_000001.json              # Disjunctive & sum Zero-Knowledge proofs for ballot validity
│   └── ...
├── tally/
│   ├── encrypted_tally.json           # Homomorphic slot sums and tally commitment
│   └── decrypted_tally.json           # Decrypted vote counts, totals, and reconciliation status
├── threshold/                         # [Present in threshold elections]
│   ├── dkg_manifest.json              # Pedersen/Feldman commitments, joint pubkey, QUAL set
│   ├── trustee_shares.json            # Public partial decryption shares W_i,j
│   └── chaum_pedersen_proofs.json     # Discrete-log equality proofs for all partial decryptions
├── signatures/                        # [Present in signed bundles]
│   └── manifest.sig.json              # Detached Ed25519 signature over canonical manifest_hash
├── manifest.json                      # Cryptographic root envelope: inventory, hashes, sizes
└── VERIFY.md                          # Human-readable instructions for standalone verification
```

### Path Traversal Hardening & Safe Ingestion
To protect verifier machines from arbitrary file extraction and path traversal vulnerabilities, all artifact paths are processed through `normalize_bundle_path`:
1. Rejection of directory traversal tokens (`..`, `.`).
2. Rejection of leading root slashes (`/` or `\`).
3. Rejection of Windows volume identifiers or drive letters (`C:`, `D:`).
4. Rejection of redundant delimiters (`//`, `\\\\`).
5. Enforced POSIX forward-slash (`/`) canonical separators.

---

## 3. Canonical Serialization & Manifest Hashing Construction

### 3.1 Deterministic Canonical Serialization (`RFC-CANONICAL-JSON-1`)
All JSON artifacts in the bundle conform to strict canonical serialization invariants:
- **Key Sorting:** Dictionary keys are sorted lexicographically by Unicode code point (`sort_keys=True`).
- **Compact Separators:** Zero arbitrary whitespace; separators are exactly `(',', ':')`.
- **Character Encoding:** Unescaped UTF-8 (`ensure_ascii=False`).
- **Recursive Float Rejection:** Floating-point numbers (`float`) are strictly forbidden. IEEE 754 representations (NaN, subnormals, negative zero, variable formatting across runtimes) cause nondeterminism. If any float is encountered anywhere in a data structure, serialization immediately raises `app.crypto.exceptions.SerializationError`.

### 3.2 Manifest Structure
The root `manifest.json` serves as the cryptographic envelope:
```json
{
  "bundle_protocol_version": "SECUREVOTE-EVIDENCE-BUNDLE-1",
  "election_protocol_version": "SECUREVOTE33",
  "canonicalization_version": "RFC-CANONICAL-JSON-1",
  "hash_algorithm": "SHA-256",
  "election_id": "ELECTION-ID",
  "created_at": "2026-09-21T00:00:00Z",
  "artifact_inventory": [
    {
      "path": "ballots/ballot_000001.json",
      "artifact_type": "BALLOT",
      "sha256": "8f3b2...",
      "size_bytes": 1420
    }
  ],
  "manifest_hash": "c3a1b...",
  "signature": { ... }
}
```

### 3.3 Manifest Hash Derivation & Non-Circularity
To prevent circular hash dependencies, the manifest hash is computed as:
$$\text{manifest\_hash} = \text{SHA-256}\left(\text{canonical\_json}\left(\text{manifest} \setminus \{\text{"manifest\_hash"}, \text{"signature"}\}\right)\right)$$

The `signatures/manifest.sig.json` and `manifest.json` files are envelope metadata files and are excluded from `artifact_inventory`, ensuring complete mathematical separation between the payload inventory and the signature envelope.

---

## 4. Detached Signature Model & Key Pinning

### 4.1 Detached Ed25519 Signature
The election authority or notary signs the bundle using an Ed25519 digital signature:
$$\sigma = \text{Ed25519\_Sign}\left(sk_{\text{signer}}, \text{manifest\_hash}_{\text{UTF-8}}\right)$$

### 4.2 Signature Verification States
The standalone verifier evaluates the manifest signature into three distinct states:
- **`VALID`**: Signature is present, mathematically valid over the recomputed manifest hash, and (if key pinning is active) matches the pinned trusted public key.
- **`INVALID`**: Signature is corrupted, public key is invalid, or the public key does not match the pinned trusted key.
- **`NOT_PRESENT`**: Unsigned bundle mode. The verifier continues and evaluates all cryptographic evidence without failing Checkpoint 4, reporting `NOT_PRESENT` status transparently.

---

## 5. The 15-Checkpoint Standalone Verification Pipeline

The `StandaloneBundleVerifier` executes an automated 15-checkpoint verification pipeline. Every checkpoint operates directly on the raw files via `BundleReader` (supporting uncompressed directory bundles or compressed `.zip` archives directly in memory):

| # | Checkpoint Identifier | Description & Mathematical Verification Invariant |
|---|---|---|
| **1** | `checkpoint_1_bundle_schema` | Validates manifest schema compliance, field types, and recursive floating-point absence. |
| **2** | `checkpoint_2_manifest_hash` | Recomputes $\text{SHA-256}(\text{manifest} \setminus \{\text{hash}, \text{sig}\})$ and checks equality with declared `manifest_hash`. |
| **3** | `checkpoint_3_inventory_integrity` | Verifies SHA-256 digests and byte sizes of all declared artifacts; detects and rejects undeclared rogue files. |
| **4** | `checkpoint_4_signature` | Verifies detached Ed25519 signature over `manifest_hash` and checks trusted key pinning. |
| **5** | `checkpoint_5_election_identity` | Asserts `election_id` consistency across `context/election.json`, `manifest.json`, and all artifact headers. |
| **6** | `checkpoint_6_candidate_config` | Validates candidate list, ordering, count, and consistency across context and tally files. |
| **7** | `checkpoint_7_public_key` | Validates NIST P-256 public key coordinates on-curve ($y^2 \equiv x^3 - 3x + b \pmod p$), not point at infinity, and verifies SHA-256 key fingerprint. |
| **8** | `checkpoint_8_ballot_ciphertexts_and_commitments` | Validates all ballot slot coordinates on-curve, checks ballot hash bindings, and recomputes ballot commitments. |
| **9** | `checkpoint_9_zk_validity_proofs` | Recomputes Fiat-Shamir challenges and verifies disjunctive 1-of-2 slot validity proofs ($v_j \in \{0, 1\}$) and sum proof ($\sum v_j = 1$). |
| **10** | `checkpoint_10_homomorphic_aggregation` | Recomputes homomorphic product across all ballots: $C_{\text{agg}, j} = \sum_{i} C_{i, j} = \left(\sum c_{1, i}, \sum c_{2, i}\right)$ and compares against `encrypted_tally.json`. |
| **11** | `checkpoint_11_tally_commitment` | Recomputes SHA-256 tally commitment binding the aggregated ciphertext to `election_id` and `key_fingerprint`. |
| **12** | `checkpoint_12_threshold_manifest` | [Threshold mode] Validates threshold parameters ($t, n$), QUAL set consistency, and Feldman polynomial commitments. |
| **13** | `checkpoint_13_partial_decryption_proofs` | [Threshold mode] Verifies Chaum-Pedersen discrete-log equality proofs for all trustee partial decryption shares ($W_{i, j} = s_i \cdot A_j$). |
| **14** | `checkpoint_14_lagrange_combination_and_dlog` | [Threshold mode] Verifies Lagrange interpolation $D_j = \sum_{i \in \mathcal{S}} \lambda_i W_{i, j}$ and discrete-log resolution: $B_j - D_j = v_j \cdot G$ using point subtraction $B_j + (-D_j)$. |
| **15** | `checkpoint_15_tally_reconciliation` | Asserts exact conservation of votes: $\sum_{j=1}^m v_j = \text{ballot\_count}$ with zero vote drift. |

---

## 6. Empirical Performance Benchmarks

Empirical measurements were conducted on Windows 11 AMD64 (Python 3.12.10 CPython) across 5 trials per tier, utilizing complete threshold election packages ($t=2, n=3$) with full Chaum-Pedersen proofs and ZK validity proofs.

Machine-readable benchmark results are preserved in `docs/research/evidence/phase2_bundle_benchmarks.json`.

### Benchmark Results Table

| Bundle Tier | Ballots | Candidates | Export (ms) | Manifest Hash (ms) | SHA-256 Digest (ms) | Crypto Verification (ms) | Total Verification (ms) | Bundle Size (KB) |
|---|---|---|---|---|---|---|---|---|
| **Small** | 10 | 3 | 36.52 ms | 0.37 ms | 94.28 ms | 654.71 ms | 749.59 ms | 104.9 KB |
| **Medium** | 50 | 4 | 139.53 ms | 1.73 ms | 434.23 ms | 4,124.23 ms | 4,560.93 ms | 575.3 KB |
| **Large** | 100 | 4 | 261.99 ms | 3.39 ms | 1,196.92 ms | 8,083.87 ms | 9,284.46 ms | 1,133.7 KB |

### Analysis of Computational Cost
1. **Export Overhead:** Exporting a 100-ballot bundle with 400 slot ciphertexts, 400 ZK proofs, and threshold manifests requires approximately **262 ms**, demonstrating negligible overhead for operational archiving.
2. **Cryptographic Bottleneck:** Verification time scales linearly with $N \times M$ (ballots $\times$ candidate slots) due to pure-Python elliptic curve point multiplications during Disjunctive Chaum-Pedersen verification (Checkpoint 9).
3. **Storage Efficiency:** Even with full disjunctive proofs, commitments, and threshold packages, a 100-ballot evidence bundle occupies only **1.13 MB** uncompressed, making it highly portable.

---

## 7. Adversarial Mutation Matrix & Validation

The bundle verification subsystem is subjected to an exhaustive adversarial test suite (`tests/test_evidence_bundle_phase2.py`) consisting of 38 automated test cases covering happy paths and malicious mutation vectors:

| Attack Category | Test Coverage | Expected & Verified Outcome |
|---|---|---|
| **Float Injection** | Floating-point value placed in candidate count or tally | Rejection at Checkpoint 1 (`SerializationError`) |
| **Path Traversal** | Path entries containing `../`, `C:\`, `/etc/passwd` | Rejection during schema/inventory validation |
| **Inventory Tampering** | Deleted file, altered file content, tampered SHA-256 digest | Rejection at Checkpoint 3 (`Inventory integrity failed`) |
| **Rogue Files** | Uninventoried `.py` or `.json` injected into bundle | Rejection at Checkpoint 3 (`Undeclared files present`) |
| **Signature Forgery** | Bit flipped in signature, altered manifest hash, untrusted key | Rejection at Checkpoint 4 (`InvalidSignature` / `Key mismatch`) |
| **Context Tampering** | Mutated `election_id` in election context | Rejection at Checkpoint 5 (`Election ID mismatch`) |
| **Candidate Tampering**| Modified candidate order, swapped candidate names | Rejection at Checkpoint 6 (`Candidate ordering mismatch`) |
| **Off-Curve Point** | Ciphertext coordinate modified to invalid curve point | Rejection at Checkpoint 8 (`Point not on curve`) |
| **Ballot Tampering** | Ciphertext modified after proof generation | Rejection at Checkpoint 9 (`Ballot validity proof invalid`) |
| **Aggregation Tampering**| Encrypted aggregate ciphertext modified | Rejection at Checkpoint 10 (`Homomorphic sum mismatch`) |
| **Commitment Spoofing**| Tally commitment mismatched against encrypted tally | Rejection at Checkpoint 11 (`Tally commitment mismatch`) |
| **Threshold Quorum** | Fewer than $t$ trustee packages provided | Rejection at Checkpoint 12 (`Insufficient trustees`) |
| **CP Proof Forgery** | Tampered partial decryption Chaum-Pedersen proof | Rejection at Checkpoint 13 (`Chaum-Pedersen proof failed`) |
| **Discrete Log Drift** | Forged decrypted tally count | Rejection at Checkpoint 14 (`Discrete log mismatch`) |
| **Vote Reconciliation**| Decrypted sum deviates from ballot count | Rejection at Checkpoint 15 (`Vote conservation drift`) |

---

## 8. Threat Boundaries & Explicit Non-Claims

To maintain scientific integrity and prevent security theater, the trust boundaries of portable evidence bundles are explicitly defined:

### What the Bundle Proves:
1. **Mathematical Consistency:** The published tally is the exact homomorphic sum of the published encrypted ballots.
2. **Ballot Well-Formedness:** Every included ballot was proven in zero-knowledge to encode a valid 1-of-$k$ selection without revealing the voter's choice.
3. **Threshold Decryption Correctness:** The decrypted tally was produced by authorized trustees holding valid key shares without reconstructing the master secret key.
4. **Bundle Immutability:** Any post-export tampering with any file in the bundle is mathematically detectable via the manifest hash and artifact digests.

### What the Bundle Does NOT Prove (Explicit Non-Claims):
1. **No Physical Voter Authentication:** The bundle proves that encrypted ballots are mathematically valid. It does not verify whether the submitter was a legally eligible citizen, nor does it detect physical impersonation.
2. **No Coercion Resistance:** Standard ElGamal ballots with client-side encryption do not protect voters against real-time screen recording, shoulder-surfing, or forced credential sharing.
3. **No Physical EVM Equivalence:** Electronic Evidence Bundles are software-based artifacts and do not offer the air-gapped hardware guarantees or paper audit trails of physical Indian Electronic Voting Machines (EVMs) with VVPAT printers.
4. **Threshold Non-Collusion Assumption:** Security depends on the cryptographic assumption that at least $n - t + 1$ trustees are honest and do not collude to recover the joint private key.
5. **Research Platform Limitation:** SecureVOTE is an academic research platform and is not certified for legally binding public elections.

---

## 9. Independent Verifier Usage

### 9.1 Command-Line Verification
Auditors can verify an exported directory bundle or `.zip` archive using the standalone CLI:

```bash
# Basic verification
python -m standalone_verifier.verify_bundle path/to/bundle

# Verifying a zip archive directly
python -m standalone_verifier.verify_bundle path/to/bundle.zip

# Verification with pinned trusted public signing key
python -m standalone_verifier.verify_bundle path/to/bundle --trusted-key <ed25519_hex_public_key>

# Machine-readable JSON output for automated auditor pipelines
python -m standalone_verifier.verify_bundle path/to/bundle --json
```

### 9.2 Python Standalone Integration
```python
from standalone_verifier.bundle_verifier import StandaloneBundleVerifier

# Execute verification without database or web framework
report = StandaloneBundleVerifier.verify(
    bundle_path="path/to/bundle.zip",
    trusted_signing_public_key_hex="a1b2c3...",
)

if report["overall_status"] == "VALID":
    print(f"Election {report['bundle_id']} successfully verified (15/15 checkpoints).")
else:
    print(f"Verification failed: {report['error']}")
```
