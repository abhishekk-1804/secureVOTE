# SecureVOTE Threat Model

## 1. Overview & Positioning

SecureVOTE is an academic and research-oriented electronic voting security prototype designed to study defense-in-depth, physical and electronic tamper detection, append-only hash-chained auditing, asymmetric digital signatures, and independent offline verification.

This document formally details the system boundaries, assets, threat taxonomy, and an exhaustive threat matrix spanning embedded hardware, serial transport, API infrastructure, database persistence, and public verification.

> [!IMPORTANT]
> **Three-Tier Demarcation**:
> - **Current Indian Election Practice**: Standalone, air-gapped M3 EVMs (BU, CU, VVPAT) by BEL/ECIL with one-time programmable (OTP) microcontrollers, physical seals, Rule 49E mock poll, Form 17C reconciliation, and 5-station random paper audits.
> - **SecureVOTE Simulation**: Software digital twin simulating CU/BU ergonomics, 7s VVPAT window, 1000Hz buzzer, Rule 49B NOTA, and a 12-stage lifecycle.
> - **Proposed Research Concept**: Append-only SHA-256 hash chains, Ed25519 digital signatures, keyed HMAC identity abstraction, and machine-verifiable independent verifiers.

---

## 2. Protected Assets & Trust Boundaries

### Protected Assets
1. **Candidate Slate & Configuration**: Freeze fingerprint representing valid candidates, parties, and ballot ordering.
2. **Voter Eligibility & Session Tokens**: Single-use authorizations granting ballot access.
3. **Cast Ballots**: Individual voter selections and their cryptographic SHA-256 digests.
4. **Audit Trail**: Chronological, append-only log of operational, security, and administrative events.
5. **Certified Result Manifest**: Final election tallies, device contributions, and official Ed25519 signature.
6. **Device Registration & Identity**: Whitelisted terminal identifiers, status flags, and sequence states.

### Trust Boundaries
- **TB-1 (Physical Enclosure)**: Enclosure switches protect internal EEPROM and MCU pins from physical probes.
- **TB-2 (Serial Transport)**: UART bridge separates bare-metal ATmega328P from the host operating system.
- **TB-3 (API Gateway)**: RBAC token validation separates public web clients from privileged officer operations.
- **TB-4 (Data Persistence)**: Relational constraints and hash chaining separate the active database engine from historical records.
- **TB-5 (Independent Audit Boundary)**: Standalone Python verifier operates strictly on exported JSON envelopes without network or database access.

---

## 3. Exhaustive Threat Analysis Matrix

| Threat | Protected Asset | Attack Surface | Existing Control | Detection Mechanism | Verification Check | Residual Limitation |
|---|---|---|---|---|---|---|
| **1. Malicious Device** | Election Ingestion Pipeline | Serial port / Device API | Pre-registration check; election state must be `OPEN`; terminal must be `ACTIVE` | `HTTP 403 Forbidden` on unregistered device identifier; `TAMPER_DETECTED` status | Device whitelist inspection; status table review | Rogue hardware with stolen valid device credentials could submit ballots if unrevoked before poll. |
| **2. Duplicated Device Identity** | Sequence State & Tallies | Parallel serial connections / API calls | Strictly monotonic sequence numbers per device stored in DB & EEPROM | `HTTP 409 Conflict` on duplicate or retrograde sequence numbers (`sequence <= last_seen`) | Independent verifier Checkpoint 4 (Monotonicity audit across device event logs) | If an attacker clones a device identity and transmits before the legitimate unit, the legitimate unit is subsequently rejected. |
| **3. Replayed Vote / Session** | Ballot Integrity & Voter Quota | `/api/votes` endpoint | Single-use constraint on `session_id`; state transitions from `ACTIVE` to `VOTED` | `HTTP 409 Conflict` on re-presentation of spent session credential | Independent verifier Checkpoint 7 (Zero-drift reconciliation: total ballots == sum of single sessions) | Wire replay of a completed session request cannot inject a second ballot. |
| **4. Modified Ballot Record** | Cast Ballot Content | Direct SQL `UPDATE` on `ballots` table | Deterministic ballot hash recomputation: `SHA-256(election:session:device:candidate:seq:timestamp)` | Database row hash mismatch flags discrepancy during recount | Independent verifier Checkpoint 3 (Recomputes SHA-256 for every raw ballot) | Database-level modification is detected post-hoc during verification, not prevented in real-time against a malicious root DBA. |
| **5. Modified Audit Record** | Historical Event Trail | Direct SQL `UPDATE` on `audit_entries` | Cryptographic SHA-256 chaining: $\text{entry\_hash}_i = \text{SHA-256}(\text{prev\_hash} \parallel \text{data})$ | Break in `previous_hash` continuity on altered row and all subsequent links | Independent verifier Checkpoint 8 (Cryptographic chain continuity verification from genesis) | Modification is detected immediately upon audit verification, but database engine itself cannot prevent raw table writes. |
| **6. Deleted Audit Record** | Complete Event Audit | Direct SQL `DELETE` on `audit_entries` | Sequential entry sequence IDs and continuous hash link to next record | Gap in sequence numbers and hash mismatch between surrounding entries | Independent verifier Checkpoint 8 (Audit chain continuity flags broken link) | Deleting the tail of the log is detected if audit root has been published or anchored externally. |
| **7. Forged Result Manifest** | Official Certified Results | Result publication endpoint | Manifest signed using Ed25519 elliptic curve private key over canonical JSON manifest | Cryptographic signature verification failure (`SIGNATURE_INVALID`) | Independent verifier Checkpoint 9 (Verifies Ed25519 signature against published authority public key) | Attacker possessing the offline signing private key could forge a valid manifest; key security relies on operational air-gapping. |
| **8. Unauthorized Officer Action** | State Machine & Roster | Admin API endpoints | Role-Based Access Control (RBAC) via JWT claims (`ADMIN`, `AUDITOR`, `OBSERVER`) | `HTTP 403 Forbidden` on insufficient role privilege; actor username recorded in audit log | Audit log inspection of administrative event milestones (Rule 49V analogue) | Stolen administrator JWT token allows authorized actions until token expiration or key revocation. |
| **9. Compromised Backend** | Election Orchestration | Application server process | Immutable configuration freezing; independent verifier runs outside the backend | Advisory anomaly heuristics engine flags abnormal rates or sequence anomalies | Independent verifier operates on exported envelope completely disconnected from backend code | A compromised application server could drop votes before committing them to the database. |
| **10. Compromised Database** | Persistent State Tables | Database storage engine (SQLite/PostgreSQL) | Cryptographic hash chaining on audit logs; external root commitments (anchoring) | Anchor mismatch between internal tree root and externally published commitment receipt | Independent verifier proves divergence between database export and published anchor receipts | A malicious DBA can alter data, but cannot forge matching hash chains and external anchor receipts without detection. |
| **11. RFID Credential Replay** | Voter Identification Token | RFID card tap interface | Keyed pseudonymization: `HMAC-SHA256(raw_uid, SECRET)`; `RFID AUTH != VOTER ELIGIBILITY` | Presentation of card outside `OPEN` election or for already-voted elector returns rejection | Session registration audit trail review | Cloned physical RFID card can authenticate as that card, but cannot double-vote if that voter's session is already closed. |
| **12. Serial / UART Manipulation** | Terminal Communications | Physical serial link (TX/RX lines) | Line-delimited JSON framing with packet sequence numbers; firmware state machine | Bridge drops malformed JSON frames; FSM rejects out-of-order commands | Physical inspection of terminal connections; firmware sequence audit | Physical access to UART lines allows eavesdropping on vote payloads in prototype. Mitigated in production by hardware secure elements. |
| **13. Malformed Device Messages** | Bridge Stability & Parsing | Serial bridge listener / WebSockets | Strict schema validation with Pydantic; try/catch JSON framing in firmware & bridge | Bridge logs error and discards malformed frame without state change or crash | Audit log monitors `COMMUNICATION_ERROR` frequency | High-volume garbage transmission causes local bridge DoS on that specific serial port, requiring physical reset. |

---

## 4. Attacker Profiles & Threat Assumptions

| Profile | Motivation | Assumed Capabilities | Non-Capabilities |
|---|---|---|---|
| **External Eavesdropper** | Compromise secrecy or replay votes | Can sniff network and serial link; replay recorded packets | Cannot forge HMAC-SHA256 pseudonyms or increment monotonic sequences |
| **Rogue Voter** | Double voting or booth disruption | Physical access to Ballot Unit buttons during voting turn | No access to Control Unit, officer credentials, or firmware code |
| **Corrupt Polling Officer** | Stuff ballots or manipulate devices | Physical access to Control Unit; local administrative access | Cannot alter frozen candidate slate or bypass central sequence checks |
| **Hostile DBA / Server Intruder** | Alter tallies or erase logs | Direct SQL read/write access to central database | Cannot forge Ed25519 manifest signature or defeat hash chain verification |
| **Independent Auditor** | Detect fraud or verify integrity | Access to published export envelope and verifier script | Zero trust in server infrastructure; verifies mathematical proofs only |

---

## 5. Defense-in-Depth Summary

1. **Prevention**: Database unique constraints (`(election_id, voter_credential)`), FSM closed-state rejection, monotonic sequence checks, device whitelisting.
2. **Detection**: Enclosure microswitch tamper latch (`0x0E`), 6 advisory anomaly heuristics (bursts, gaps, rejection spikes), terminal heartbeat monitoring.
3. **Auditability**: Continuous SHA-256 hash chaining, Presiding Officer chronological event diary, external cryptographic root commitments.
4. **Independent Verification**: Offline standalone Python verifier validating 12 mathematical invariants on exported archives.
