# SecureVOTE 3.3 — India Election Security & Cryptographic Verification Research Platform
## Architectural & Engineering Hardening Specification

- **Milestone Target**: `v3.3.0-research`
- **Baseline Protocol**: `v3.2.0-research` (Frozen at commit `58dc44f`)
- **Status**: Research Platform Hardening Specification & Correctness Verification Pass
- **Platform Scope**: Indian Electoral Simulation Hierarchy, Statutory Lifecycle Alignment, Client-Side Cryptographic Verifier, and System Hardening

---

## 1. Executive Summary & System Objectives

SecureVOTE 3.3 elevates SecureVOTE from a generic cryptographic prototype into a domain-grounded **Indian Election Security & Cryptographic Verification Research Platform**. 

Prior iterations established the underlying cryptographic primitives:
- **v2.0**: Device state machine, tamper-evident hash chaining, and Ed25519 manifest signing.
- **v3.0**: Additive Exponential ElGamal encryption over NIST P-256 (`secp256r1`) and offline tally verifier.
- **v3.1**: Cramer-Damgård-Schoenmakers (CDS94) disjunctive zero-knowledge ballot validity proofs ($1$-out-of-$k$ and binary vote proofs).
- **v3.2**: Gennaro-Jarecki-Krawczyk-Rabin (GJKR) $(t, n) = (2, 3)$ Distributed Key Generation and Chaum-Pedersen verifiable partial decryption.

Version 3.3 contextualizes these cryptographic primitives within the constitutional and statutory framework of Indian democratic elections, modeling the operational lifecycle established by the Representation of the People Act, 1951 and the Conduct of Elections Rules, 1961.

### Core Objectives of v3.3 Hardening Pass
1. **Strict Lifecycle State Machine Synchronization**: Eliminates client-server state drift, enforces terminal state semantics on `PUBLISHED`, and guarantees deterministic HTTP 409 Conflict handling.
2. **Byte-Level UTF-8 Encoding Integrity**: Repairs legacy mojibake and encoding corruption across 16 backend source files and frontend components.
3. **Independent Client-Side Mathematical Verifier**: Introduces `verifier-crypto.ts` executing authentic Web Crypto SHA-256 recomputations and canonical JSON serialization in the browser.
4. **Honest Metric & Claim Grounding**: Eliminates ungrounded marketing claims (e.g. "100% E2E verified", unhedged overseas voting endorsements), replacing them with precise descriptions of simulated benchmark workloads.

---

## 2. Statutory Lifecycle Alignment & State Synchronization

The Indian electoral process enforces strict legal cutoffs where once an election result is finalized and gazetted, it cannot be mutated or reopened. SecureVOTE 3.3 strictly enforces these semantics.

### 2.1 State Machine Specification

```text
[CREATED]
    │
    ▼
[CONFIGURED] ◄────────┐
    │                 │
    ▼                 │
 [LOCKED]             │ (Pre-poll adjustments)
    │                 │
    ▼                 │
  [OPEN]  ────────────┘
    │  ▲
    │  │ (Emergency pause / resumption)
    ▼  │
[SUSPENDED]
    │
    ▼
 [CLOSED]
    │
    ▼
[PUBLISHED] (TERMINAL — NO OUTGOING TRANSITIONS ALLOWED)
```

### 2.2 Terminal State Semantics (`PUBLISHED`)
In `backend/app/services/election_service.py`:
- `VALID_TRANSITIONS["PUBLISHED"] = []`
- Attempting to transition from `PUBLISHED` to any state raises `HTTPException(status_code=409, detail="Invalid state transition: PUBLISHED → <target>. Valid transitions from PUBLISHED: []")`.
- In the Command Center and Election Setup dashboards, when `election.state === "PUBLISHED"`:
  - A persistent notification banner states: `"PUBLISHED — FINAL / TERMINAL STATE: This election has completed its statutory lifecycle and results are locked. No further state transitions are permitted."`
  - All action and transition buttons are completely hidden or disabled.
  - Concurrent transition attempts by other administrative sessions prompt an automatic re-fetch of the authoritative backend state, accompanied by a non-blocking alert notifying the officer of the authoritative status.

---

## 3. Byte-Level UTF-8 Integrity & Encoding Hardening

To prevent encoding mismatches across operating systems and client environments, all source files were audited for UTF-8 byte corruption:
- Replaced double-encoded Latin-1 / UTF-8 artifact sequences (e.g. `Ã¢â€ â€™` $\to$ `→`, `Ã¢â‚¬â€` $\to$ `—`, `Ã‚§` $\to$ `§`) across 16 backend modules, test files, and dashboard components.
- Standardized file headers and string representations on strict UTF-8 with zero BOM.
- Verified with `git diff --check`, ensuring zero whitespace errors, no carriage return artifacts on edited lines, and clean diff generation across Linux and Windows environments.

---

## 4. Grounded Browser-Side Cryptographic Verifier (`verifier-crypto.ts`)

Previous iterations of the public `/verify` page relied partially on declarative status flags. SecureVOTE 3.3 introduces an authentic client-side verification engine in `dashboard/lib/verifier-crypto.ts` utilizing the browser's standard Web Crypto API (`crypto.subtle`).

### 4.1 Recomputation Pipeline
1. **Canonical JSON Serialization (`canonicalJson`)**:
   Implements recursive object key sorting, explicit string normalization, and compact formatting with zero extraneous whitespace (`{"a":1,"b":2}`) matching the backend's deterministic JSON serializer.
2. **SHA-256 Digest Recomputation (`sha256Hex`)**:
   Encodes canonical JSON strings into UTF-8 byte buffers and invokes `crypto.subtle.digest("SHA-256", buffer)` to generate exact 64-character lowercase hexadecimal digests.
3. **Candidate Configuration Hash (`recomputeConfigHash`)**:
   Re-sorts candidate roster by assigned ballot position and calculates the root configuration hash.
4. **Per-Ballot Hash & Chain Continuity (`recomputeBallotHash`)**:
   Calculates SHA-256 hashes of all ballot records and flags any individual ballot mutation.
5. **Audit Chain Recomputation (`recomputeAuditEntryHash`)**:
   Traverses the sequential audit event log, recomputing each entry's SHA-256 hash and verifying that `entry[i].previous_hash === entry[i-1].entry_hash`.
6. **11-Point Verification Checkpoints**:
   - `envelope_structure`: Archive JSON schema validation.
   - `election_metadata`: Identification and timing integrity.
   - `configuration_hash`: Candidate roster configuration hash match.
   - `ballot_hashes`: Full ballot digest recomputations.
   - `ballot_sequence`: Sequential sequence numbering without gaps.
   - `candidate_totals`: Summation verification across ballots.
   - `device_totals`: Verification of per-device counters against tally.
   - `reconciliation`: Zero-drift equation: $\sum C_i = \text{Total Cast} = \sum D_j$.
   - `audit_chain`: Continuous cryptographic hash chaining from genesis to root.
   - `manifest_hash`: Root manifest hash recomputation.
   - `ed25519_signature`: Asymmetric signature verification of result manifest.

### 4.2 Verification Honesty Principle
The verifier never returns an unwarranted green `PASSED` status:
- If required artifacts are missing or cannot be mathematically verified in the browser environment, the checkpoint status is explicitly set to `UNCHECKED` with a clear explanation.
- Mismatches in hashes, sequences, or signatures immediately flag a status of `FAILED` and surface the exact expected vs. computed values to the user.

---

## 5. Electoral Geography & Simulation Boundaries

SecureVOTE 3.3 establishes clear demarcation between statutory reference data and synthetic simulation records:

| Data Type | Scope & Modeling | Operational Boundary |
|---|---|---|
| **Electoral Reference Data** | 12 States/UTs, 64 PCs, 512 ACs, recognized national & state party symbols | Static administrative reference from public ECI records. No dynamic state mutation. |
| **Simulated Research Data** | 142,850 synthetic research ballots, simulated voter rolls, simulated EVM telemetry | Clearly labeled as synthetic benchmark data. Not drawn from actual voters. |
| **Statutory Forms** | Forms 7A, 17C, 20, and 49E templates | Educational and research reconstructions aligned with Conduct of Elections Rules, 1961. |

---

## 6. Comprehensive Verification & Regression Test Results

The platform underwent rigorous end-to-end verification across both the backend cryptographic engine and the frontend Next.js application:

### 6.1 Backend Test Suite (Pytest)
```text
Platform: Windows (Python 3.12.10, pytest 8.3.4)
Suite: backend/tests
Status: 315 / 315 PASSED (100%)
Runtime: 263.12 seconds
```
Key Test Modules:
- `test_anchoring.py`: 4 passed
- `test_anomaly_detection.py`: 3 passed
- `test_attacks.py`: 20 passed
- `test_crypto.py`: 60 passed
- `test_crypto_security_hardening.py`: 14 passed
- `test_india_platform.py`: 14 passed
- `test_integration.py`: 19 passed
- `test_lifecycle_transitions.py`: 2 passed (State machine validation & 409 terminal enforcement)
- `test_threshold_dkg.py`: 17 passed
- `test_threshold_partial_decryption.py`: 23 passed
- `test_threshold_tally.py`: 41 passed
- `test_v3_1_zkp_verifier.py`: 12 passed
- `test_zk_proofs.py`: 17 passed

### 6.2 Frontend Test Suite (Vitest)
```text
Platform: Node.js (Vitest 2.1.9)
Suite: dashboard/test
Status: 10 / 10 Test Files Passed, 45 / 45 Tests Passed (100%)
```
Key Test Files:
- `test/verifier-crypto.test.ts`: 7 passed (SHA-256 digests, canonical JSON, config hash, tamper detection)
- `test/lifecycle-sync.test.tsx`: 2 passed (Terminal PUBLISHED banner, 409 conflict auto-refetch)
- `test/india-platform.test.tsx`: 8 passed (IndiaMap SVG, CryptoPipeline, Command Center)
- `test/results-view.test.tsx`: 4 passed (Reconciliation, Ed25519 manifests)
- `test/voter-eligibility.test.tsx`: 3 passed (Simulated eligibility checks)
- `test/device-status.test.tsx`: 2 passed (Device sequence counters & status)
- `test/audit-explorer.test.tsx`: 3 passed (Cryptographic audit chain exploration)
- `test/phase5-integration.test.tsx`: 3 passed (12-point checks & anomaly detection)

### 6.3 Production Build Verification
```text
Framework: Next.js 14.2.3
Command: npm run build
Status: COMPILED SUCCESSFULLY
Routes: 45 / 45 static and dynamic routes prerendered with 0 TypeScript/ESLint warnings
```

---

## 7. Operational Integrity & Security Boundaries

1. **No Production Claims**: SecureVOTE 3.3 remains an educational and academic research prototype. It is explicitly not certified for statutory or binding governmental elections.
2. **Threshold Privacy**: Ballot secrecy is protected by $(t, n) = (2, 3)$ threshold ElGamal encryption. No single private key scalar is ever materialized or persisted in memory.
3. **Universal Auditability**: Every election result is accompanied by an Ed25519 signed manifest and can be verified by independent third parties using the standalone CLI or browser-based verifier.
