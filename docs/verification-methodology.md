# SecureVOTE Verification Methodology

## 1. Zero-Trust Verification Architecture

A foundational principle of SecureVOTE is that neither election officials, database administrators, nor application servers are trusted unconditionally.

The system enforces **Universal Verifiability**:
- Any observer, candidate, political party agent, or independent auditor can verify the correctness of the election results from exported raw archives without relying on the backend code, ORM, or database engine.

---

## 2. The 12 Mathematical Invariant Checks

The standalone independent verifier (`backend/standalone_verifier/verifier.py`) and the browser verifier (`dashboard/app/(public)/verify/page.tsx`) execute 12 deterministic invariant checks over exported election envelopes:

| # | Check Code | Invariant Verified | Mathematical Formula / Proof | Failure Code |
|---|---|---|---|---|
| **01** | `ENVELOPE_SCHEMA` | Structural validity & format version | $E \models \text{Schema}(\text{export\_version} = \text{"1.0.0"})$ | `ERR_INVALID_ENVELOPE` |
| **02** | `CONFIG_HASH` | Candidate roster & position freeze | $H(\text{sort}(\text{candidates})) \equiv \text{election.configuration\_hash}$ | `ERR_CONFIG_HASH_MISMATCH` |
| **03** | `BALLOT_HASHES` | Individual ballot digest integrity | $H(e \parallel s \parallel d \parallel c \parallel \text{seq} \parallel t) \equiv b.\text{ballot\_hash}$ | `ERR_BALLOT_HASH_CORRUPT` |
| **04** | `SEQ_MONOTONICITY` | Strict anti-replay sequence monotonicity | $\forall dev, \text{seq}_{i+1} > \text{seq}_i$ | `ERR_SEQUENCE_RETROGRADE` |
| **05** | `CANDIDATE_TALLY` | Independent candidate count aggregation | $\text{Tally}(c_k) = \sum_{b \in B} \mathbf{1}[b.\text{candidate\_id} = c_k]$ | `ERR_TALLY_AGGREGATION` |
| **06** | `DEVICE_TALLY` | Independent hardware terminal contribution | $\text{Tally}(d_j) = \sum_{b \in B} \mathbf{1}[b.\text{device\_id} = d_j]$ | `ERR_DEVICE_TALLY` |
| **07** | `ZERO_DRIFT` | Exact multi-point reconciliation equation | $\sum_{k} \text{Tally}(c_k) \equiv |B| \equiv \sum_{j} \text{Tally}(d_j)$ | `ERR_RECONCILIATION_DRIFT` |
| **08** | `AUDIT_CONTINUITY` | Continuous SHA-256 hash chaining | $\text{hash}_i \equiv H(\text{hash}_{i-1} \parallel \text{event\_data}_i)$ | `ERR_AUDIT_CHAIN_BREAK` |
| **09** | `AUDIT_GENESIS` | Initial block linked to root zero string | $\text{hash}_0.\text{previous\_hash} \equiv \text{"0"*64}$ | `ERR_GENESIS_CORRUPT` |
| **10** | `MANIFEST_MATCH` | Published tallies match raw ballot sum | $\text{manifest.tallies} \equiv \text{Tally}(C)$ | `ERR_MANIFEST_TALLY_MISMATCH` |
| **11** | `ED25519_SIGNATURE` | Asymmetric signature over canonical manifest | $\text{Verify}_{\text{pk}}(\text{canonical}(M), \sigma) \equiv \text{True}$ | `ERR_SIGNATURE_INVALID` |
| **12** | `ANCHOR_COMMITMENT` | External ledger root commitment verification | $\text{Receipt.root\_hash} \equiv \text{MerkleRoot}(\text{AuditLog})$ | `ERR_ANCHOR_MISMATCH` |

---

## 3. Two Verification Interfaces

### 1. Pure Python Offline Verifier
- **Location**: `backend/standalone_verifier/verifier.py`
- **Dependencies**: Python standard library (`hashlib`, `json`, `sys`) + `cryptography` (for Ed25519)
- **Zero ORM Dependency**: Contains **zero imports** from FastAPI or SQLAlchemy.
- **Execution**:
  ```bash
  python backend/standalone_verifier/verifier.py election_export.json
  ```

### 2. Client-Side Browser Verifier
- **Location**: `dashboard/app/(public)/verify/page.tsx`
- **Zero Server-Side Trust**: Executes entirely in the user's browser runtime using JavaScript Web Cryptography APIs.
- **Demonstration Capabilities**:
  - Live export fetch from backend.
  - Custom JSON file upload (`election_export.json`).
  - Interactive "Simulate Mutation" button to demonstrate how deliberate tampering causes Checkpoint 8 (`Tamper-Evident Audit Hash Chain`) or Checkpoint 3 to fail.
