# SecureVOTE Security Boundaries & Trust Architecture

## 1. System Components & Trust Boundaries

The SecureVOTE ecosystem consists of multiple distinct execution environments, each separated by strict trust boundaries.

```
+-----------------------------------------------------------------------------+
|                      ZONE 1: Physical Voting Terminal                       |
|  - ATmega328P Microcontroller (2 KB SRAM, 32 KB Flash, 1 KB EEPROM)         |
|  - 4 Candidate Buttons, Confirm Button, Admin Button, Tamper Microswitch    |
|  - Zero per-vote EEPROM storage                                             |
|  - Hardware Level: Untrusted physical environment; physical tamper monitored|
+-----------------------------------------------------------------------------+
                                       |
                   BOUNDARY A: Plaintext UART (9600 Baud)
                   (No TLS; Protected by monotonic sequence counter)
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                      ZONE 2: Collector / Serial Bridge                      |
|  - Python Bridge daemon running on local polling station workstation        |
|  - Ingests UART NDJSON stream, buffers fragments, handles malformed frames  |
|  - Authenticates via Admin JWT or session token                             |
+-----------------------------------------------------------------------------+
                                       |
                   BOUNDARY B: REST API / WebSocket (HTTP / TLS)
                   (Authenticated via JWT / Single-use scoped WS tickets)
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                      ZONE 3: Core Backend & Database                        |
|  - FastAPI asynchronous application server                                  |
|  - SQLite (dev) / PostgreSQL (production) relational database               |
|  - Cryptographic hash-chained audit log & advisory anomaly detection engine |
|  - Ed25519 asymmetric manifest signing authority                            |
+-----------------------------------------------------------------------------+
                                       |
                   BOUNDARY C: Machine-Verifiable JSON Export
                   (Completely offline; Zero DB or ORM coupling)
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                   ZONE 4: Independent Offline Verifier                      |
|  - Completely decoupled CLI tool (backend/standalone_verifier/verifier.py)   |
|  - Zero imports from FastAPI, SQLAlchemy, or application ORM models         |
|  - Recomputes all 12 cryptographic checkpoints from raw records             |
|  - Air-gapped execution capability on auditor machines                      |
+-----------------------------------------------------------------------------+
```

---

## 2. Detailed Boundary Guarantees

### Boundary A: Terminal <-> Serial Bridge (UART)
- **Assumptions**: Wire-level sniffing and injection are possible if physical cabling is accessed.
- **Enforcements**:
  1. Monotonic sequence counter per device stored in EEPROM and verified by backend.
  2. Any replayed or decremented sequence number is rejected (`HTTP 409`).
  3. Physical enclosure tamper switch immediately triggers persistent EEPROM latch (0x0E), halting terminal and transmitting `TAMPER` alert over serial.

### Boundary B: Serial Bridge <-> Backend REST API
- **Assumptions**: Local network may be shared; requests must be validated.
- **Enforcements**:
  1. Administrative operations (device status change, state transitions) require valid JWT with `ADMIN` role.
  2. Vote casting requires a valid, pre-authorized, single-use `session_token`.
  3. WebSockets require single-use, 60-second TTL handshake tickets bound to a specific scope (`/api/ws` global or `/api/ws/{election_id}`).

### Boundary C: Backend <-> Independent Offline Verifier
- **Assumptions**: The backend database or server could be under the control of a dishonest or coerced administrator.
- **Enforcements**:
  1. Verifier never queries the live database or trusts precomputed verification flags.
  2. Consumes only static, self-contained JSON election export archives conforming to `docs/export_schema.json`.
  3. Recomputes:
     - Configuration hash from raw candidate list
     - Ballot hash for every individual ballot
     - Monotonic sequence ordering per device
     - Candidate and device tallies from scratch
     - Exact zero-drift reconciliation
     - Audit log hash chain link-by-link
     - Ed25519 signature over result manifest
     - External ledger anchor receipts against recomputed audit root

---

## 3. Explicit Educational Disclaimers & Out-of-Scope Items

1. **Voter Anonymity / Ballot Secrecy**:
   - In this educational prototype, ballots are linked to voting sessions to demonstrate end-to-end auditability and traceability.
   - Real-world electronic voting systems must employ homomorphic tallying (e.g. Paillier, ElGamal) or cryptographic mixnets to ensure un-linkable ballot secrecy.
2. **Side-Channel & Power Analysis**:
   - Power analysis (DPA/SPA) and electromagnetic radiation emissions on the ATmega328P microcontroller are out of scope for this prototype.
3. **Physical Coercion / Vote Selling**:
   - Electronic credentials cannot physically prevent a voter from revealing their selection to a third party outside the polling booth. Controlled polling places and physical privacy screens remain essential.
