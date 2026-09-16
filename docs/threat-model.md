# SecureVOTE Threat Model

## 1. Overview & Positioning

SecureVOTE is an academic and research-oriented electronic voting security prototype designed to demonstrate **defense-in-depth**, **tamper detection**, **hash-chained auditing**, **asymmetric digital signatures**, and **independent offline verification**.

This document formally details the system's threat model, attacker profiles, trust assumptions, STRIDE threat taxonomy, and mitigations.

> [!NOTE]
> **Research Prototype Scope**: SecureVOTE is an educational framework. It does not replace certified national voting equipment (such as precinct-count optical scan systems or systems with voter-verified paper audit trails).

---

## 2. Attacker Profiles & Capabilities

| Attacker Profile | Motivations | Capabilities | Limitations |
|---|---|---|---|
| **Rogue Voter / Coerced Voter** | Cast multiple votes; sell vote; disrupt local booth | Physical access to voting booth buttons during session | No access to hardware enclosure, backend DB, or firmware keys |
| **Dishonest Polling Worker** | Manipulate terminal state; ballot stuffing; impersonate voters | Physical proximity to terminals; admin PIN access | Cannot forge central configuration hash or alter hash-chained audit logs |
| **Physical Tamperer / Burglar** | Steal or reprogram terminals; probe EEPROM | Physical tools to open enclosure during storage or transit | Enclosure microswitch trips persistent non-volatile latch, halting terminal |
| **Network Eavesdropper / Man-in-the-Middle** | Intercept or replay UART/HTTP messages | Sniff serial link or LAN traffic; replay recorded packets | Sequence numbers enforce strictly increasing order; duplicate payloads rejected |
| **Compromised Backend Administrator / DBA** | Modify tallies, alter stored votes, inject audit records | Direct SQL write access to database tables | Cannot alter historical audit hash chain without detection; cannot forge Ed25519 signatures |
| **External Verifier / Auditor** | Verify election integrity without trust in central server | Read-only access to published export archive | Zero database access; must recompute all proofs mathematically from raw data |

---

## 3. STRIDE Threat Analysis

### Spoofing (Identity)
- **Threat**: Attacker creates fake voting sessions or impersonates registered devices.
- **Mitigations**:
  - Devices must be pre-registered and activated by an Administrator prior to election lock.
  - Voting sessions require unique, single-use credentials (`voter_credential`). Once voted, session is marked `VOTED` and cannot be reused (`HTTP 409`).
  - Keyed identity abstraction: RFID cards are pseudonymized via HMAC-SHA256 with a server-side secret (`SECUREVOTE_RFID_SECRET`). Raw card UIDs are never stored.

### Tampering (Integrity)
- **Threat**: Attacker modifies candidate lists, alters ballot contents, or rewrites audit log rows.
- **Mitigations**:
  - Pre-election configuration hash freezes candidate list at `LOCKED` state. Any post-lock alteration triggers `CONFIGURATION HASH MISMATCH`.
  - Ballots are hashed deterministically upon insertion (`SHA-256(election_id | session_id | candidate_id | device_id | seq | timestamp)`).
  - Audit log entries form a cryptographic hash chain: modifying any historical row invalidates all subsequent `previous_hash` links.
  - Result Manifests are signed using Ed25519 over canonical JSON.
  - Physical enclosure tampering trips microswitch on D8, setting persistent non-volatile latch in EEPROM (0x0E). Terminal enters `STATE_TAMPER_DETECTED` and halts.

### Repudiation
- **Threat**: Operator denies changing configuration; device denies casting a vote; auditor disputes tally.
- **Mitigations**:
  - Every administrative action is logged to the hash-chained audit log with actor attribution.
  - Final tallies and manifests are signed with an Ed25519 private key.
  - Audit root is anchored to external immutable ledgers or cryptographic commitment receipts.

### Information Disclosure
- **Threat**: Attacker observes serial UART or database to learn how a voter voted.
- **Mitigations & Known Prototype Boundary**:
  - *Firmware*: Zero per-vote data stored in EEPROM.
  - *Audit Log*: Does not log `candidate_id` in `VOTE_CAST` audit entries.
  - *Known Limitation*: In this research prototype, the database maintains a session-to-ballot linkage for educational auditability. True secret-ballot anonymity requires cryptographic mixnets or homomorphic encryption (e.g. ElectionGuard), which is noted as future work.

### Denial of Service (DoS)
- **Threat**: Tamper switch jamming, rapid button presses, or flood of serial packets.
- **Mitigations**:
  - FSM enforces minimum transition delays and 30-second inactivity timeouts.
  - Advisory anomaly detection flags high-rate voting bursts and repeated authorization failures without blocking legitimate polling operations.
  - Serial bridge buffers incoming bytes cleanly, dropping malformed frames without crashing.

### Elevation of Privilege
- **Threat**: Observer attempts to register candidates or change election state; unauthenticated client attempts admin operations.
- **Mitigations**:
  - Role-Based Access Control (RBAC) enforced via FastAPI dependency injection: `ADMIN`, `AUDITOR`, `OBSERVER`.
  - State machine transitions strictly validated (`SETUP -> CONFIG_FROZEN -> LOCKED -> OPEN -> CLOSED -> PUBLISHED`). Invalid transitions rejected with `HTTP 409`.

---

## 4. Residual Risks & Future Mitigations

1. **Microcontroller Cryptographic Limitations**: The ATmega328P cannot perform asymmetric cryptography or TLS due to 2 KB RAM constraints. Mitigated by serial bridge encapsulation and future integration of hardware security modules (e.g., ATECC608A).
2. **Database Administrator Compromise**: A malicious DBA can delete rows, but cannot forge valid audit chains or result manifests without detection during independent verification.
3. **Ballot Secrecy in Prototype**: Educational linkage preserved for traceability; production systems must implement cryptographic tallying techniques.
