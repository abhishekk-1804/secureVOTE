# SecureVOTE Security Model

## 1. Security Philosophy: Defense-in-Depth

SecureVOTE does not rely on a single defensive perimeter. Instead, it implements a layered, **defense-in-depth** architecture where failures at one layer are caught and audited by subsequent layers.

Security controls are partitioned into four explicit operational categories:

1. **PREVENTION**: Rejects unauthorized state transitions, message replays, and duplicate voting before data persistence.
2. **DETECTION**: Flags physical enclosure tampering, communication drops, and heuristic statistical anomalies.
3. **AUDITABILITY**: Maintains an immutable, append-only SHA-256 hash-chained event trail anchored to external proofs.
4. **VERIFICATION**: Proves mathematical reconciliation, configuration integrity, and cryptographic authenticity via independent verifiers.

---

## 2. Cryptographic Primitives & Specifications

| Primitive | Algorithm / Standard | Implementation Purpose | Key Length / Digest |
|---|---|---|---|
| **Hash Chaining** | SHA-256 (FIPS 180-4) | Linking chronological audit log entries: $\text{hash}_i = \text{SHA-256}(\text{hash}_{i-1} \parallel \text{data})$ | 256-bit (64 hex characters) |
| **Ballot Digests** | SHA-256 (FIPS 180-4) | Immutable fingerprint for each individual ballot | 256-bit |
| **Configuration Freeze** | SHA-256 (FIPS 180-4) | Canonical fingerprint over frozen candidate list sorted by position | 256-bit |
| **Manifest Signing** | Ed25519 (RFC 8032) | Asymmetric elliptic-curve digital signature over certified result manifest | 256-bit private key / 512-bit signature |
| **Identity Pseudonymization**| HMAC-SHA256 (RFC 2104) | Keyed identity abstraction for raw RFID UIDs and national IDs | 256-bit secret key |
| **External Anchoring** | Merkle Root (SHA-256) | Periodic cryptographic commitment of audit log state to external ledgers | 256-bit root hash |

---

## 3. Layered Controls Breakdown

### Layer 1: Hardware Terminal Security
- **Enclosure Tamper Switch**: Connected to interrupt pin D8. Any opening of the enclosure immediately trips a non-volatile flag in EEPROM (`0x0E`), halting voting operations (`STATE_TAMPER_DETECTED`).
- **Monotonic Sequence Counter**: Incremented in EEPROM on every ballot cast, preventing packet replays.
- **Zero Raw Ballot Persistence in MCU**: Microcontroller memory retains only total counts, never voter-to-candidate maps.

### Layer 2: API & Gateway Controls
- **Role-Based Access Control (RBAC)**: Enforced on all sensitive endpoints via JWT claims (`ADMIN`, `AUDITOR`, `OBSERVER`).
- **Finite State Machine (FSM)**: Enforces strict statutory progression (`CREATED -> CONFIGURED -> LOCKED -> OPEN -> CLOSED -> PUBLISHED`). Voting is strictly blocked (`HTTP 409`) unless in `OPEN` state.
- **Single-Use Session Tokens**: Unique database constraint on `(election_id, voter_credential)`. Subsequent presentations rejected with `HTTP 409 Conflict`.

### Layer 3: Advisory Anomaly Detection Engine
- **Role**: Advisory and non-blocking. Guides human review by the Returning Officer (RO); does not automatically halt voting.
- **6 Deterministic Heuristics**:
  1. `VOTING_RATE_BURST`: Detects abnormal voting velocity (> 10 votes/min per booth).
  2. `SEQUENCE_GAP_DETECTED`: Flags skipped packet sequence numbers indicating dropped or intercepted messages.
  3. `FREQUENT_REJECTIONS`: Detects credential stuffing or invalid card tap bursts.
  4. `OFF_HOURS_ACTIVITY`: Detects voting events recorded outside declared polling hours.
  5. `UNREGISTERED_DEVICE_ATTEMPT`: Flags unauthorized terminal access attempts.
  6. `TAMPER_LATCH_ACTIVE`: Alerts command center to physical enclosure switch trips.

### Layer 4: Mathematical Verification & Zero-Drift
- **Reconciliation Equation**:
  $$\sum_{k=1}^C \text{candidate\_votes}_k \equiv \text{total\_ballots} \equiv \sum_{j=1}^D \text{device\_votes}_j$$
- Any discrepancy ($\text{drift} \neq 0$) causes independent verification to immediately report `RECONCILIATION FAILURE`.
