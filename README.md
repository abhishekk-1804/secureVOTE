# SecureVOTE - Electronic Voting System Security Prototype

An educational and research-oriented electronic voting security prototype demonstrating defense-in-depth, hardware tamper detection, tamper-evident audit trails, asymmetric cryptographic signing, local/external audit-root anchoring abstraction, independent offline verification, advisory anomaly detection, and keyed identity abstraction.

> [!NOTE]
> **Research-Oriented Prototype Notice**: SecureVOTE is an educational and academic research prototype. It is **not** an election-ready, nationally deployable, or legally certified voting system. It illustrates how cryptographic verification, hardware state machines, and defense-in-depth principles can be realized on resource-constrained microcontrollers and audited independently.

---

## Architecture Overview

```
+---------------------------------------------------------------------------------------+
|                                  SecureVOTE Ecosystem                                 |
+---------------------------------------------------------------------------------------+
|  Firmware (Arduino Uno ATmega328P @ 16 MHz)                                           |
|  - Strictly enforced deterministic 12-state FSM                                       |
|  - Physical tamper switch with persistent non-volatile EEPROM latch (0x0E)            |
|  - Monotonic sequence counter per device stored in EEPROM (0x0A)                      |
|  - Zero per-vote EEPROM storage (no hardware-level ballot persistence)                |
|  - 20x4 Character LCD (I2C 0x27), Status LEDs, Buzzer, 4 Candidate + Control Buttons  |
+-------------------------------------------|-------------------------------------------+
                                            | Newline-Delimited JSON over UART (9600 Bd)
+-------------------------------------------v-------------------------------------------+
|  Serial Bridge Transport (Python 3.12 / HTTPX)                                        |
|  - Ingests UART stream from physical Arduino or Wokwi simulator                       |
|  - Relays VOTE, TAMPER, STATE_CHANGE, and HEARTBEAT events to Backend REST API        |
+-------------------------------------------|-------------------------------------------+
                                            | REST API / JSON
+-------------------------------------------v-------------------------------------------+
|  Backend (FastAPI, SQLAlchemy Async, SQLite / PostgreSQL)                             |
|  - Cryptographic SHA-256 hash-chained tamper-evident audit log                        |
|  - Configuration freezing (pre-election candidate slate SHA-256 hash)                 |
|  - Zero-drift reconciliation constraint: sum(candidates) == total == sum(devices)     |
|  - Ed25519 asymmetric manifest signing (canonical JSON serialization)                 |
|  - External audit-root anchoring abstraction (Local & External Ledgers)               |
|  - Advisory anomaly detection engine (6 deterministic rules, strictly non-blocking)   |
|  - Keyed identity abstraction (HMAC-SHA256, RFID AUTHENTICATION != VOTER ELIGIBILITY)  |
+-------------------------------------------|-------------------------------------------+
                      | Machine-Verifiable Export   | REST API & Scoped WebSockets
                      v                             v
+-------------------------------------------+ +-----------------------------------------+
|  Independent Standalone Verifier          | |  Audit & Operations Dashboard           |
|  - Zero Database & Zero ORM Dependency    | |  - Next.js 14, Tailwind CSS, TypeScript |
|  - Recomputes 12 verification checkpoints | |  - Real-time scoped WebSocket telemetry |
|  - Verifies Ed25519 digital signature     | |  - Audit log explorer & tamper monitor  |
|  - Validates Merkle audit root receipts   | |  - 12-checkpoint verification card      |
|  - Operates completely offline from JSON  | |  - Advisory anomaly drawer & RFID tool  |
+-------------------------------------------+ +-----------------------------------------+
```

---

## Core Technical Specifications

### 1. Hardware & Firmware Layer (Arduino Uno ATmega328P)

#### Physical Pinout Table (Source: `firmware/secureVOTE/config.h`)

| Pin | Signal Name | Type | Active Level | Purpose / Function |
|---|---|---|---|---|
| **D0** | `PIN_SERIAL_RX` | Input | TTL | Hardware UART Receive (Collector Link) |
| **D1** | `PIN_SERIAL_TX` | Output | TTL | Hardware UART Transmit (Collector Link, 9600 Baud) |
| **D2** | `PIN_BTN_CAND_1` | Input | `INPUT_PULLUP` (LOW) | Candidate 1 Selection (Alice Vance) |
| **D3** | `PIN_BTN_CAND_2` | Input | `INPUT_PULLUP` (LOW) | Candidate 2 Selection (Bob Jenkins) |
| **D4** | `PIN_BTN_CAND_3` | Input | `INPUT_PULLUP` (LOW) | Candidate 3 Selection (Carol Danvers) |
| **D5** | `PIN_BTN_CAND_4` | Input | `INPUT_PULLUP` (LOW) | Candidate 4 Selection (David Miller) |
| **D6** | `PIN_BTN_CONFIRM`| Input | `INPUT_PULLUP` (LOW) | Cast / Confirm Selection / Advance Entry |
| **D7** | `PIN_BTN_ADMIN`  | Input | `INPUT_PULLUP` (LOW) | Admin Mode Hold ($\ge 2$s) / Next Digit |
| **D8** | `PIN_TAMPER_SWITCH`| Input | Pulldown (HIGH = breach) | Enclosure Lid Physical Tamper Microswitch |
| **D9** | `PIN_LED_GREEN`  | Output | Active HIGH | Status: Solid = READY, Blinking = VOTING/CONFIRM |
| **D10**| `PIN_LED_RED`    | Output | Active HIGH | Alert: Solid = TAMPER/ERROR, Blinking = ADMIN_AUTH |
| **D11**| `PIN_BUZZER`     | Output | Active HIGH | Piezo Buzzer: 120ms Beep = Vote, 1200ms Tone = Tamper |
| **A4** | `PIN_I2C_SDA`    | I/O | Open Drain | I2C Data for 20x4 Character LCD (PCF8574 Backpack) |
| **A5** | `PIN_I2C_SCL`    | I/O | Open Drain | I2C Clock for 20x4 Character LCD (PCF8574 Backpack) |

#### Deterministic 12-State Finite State Machine (Source: `firmware/secureVOTE/state_machine.h`)

The firmware implements an explicit 12-state FSM with a formal transition validation matrix:
1. `STATE_BOOT` (0): Power-on boot and hardware peripheral initialization.
2. `STATE_SELF_TEST` (1): Verifies EEPROM magic bytes, validates configuration hash, inspects tamper and pause flags.
3. `STATE_READY` (2): Idle state awaiting voter interaction or administrative command.
4. `STATE_ADMIN_AUTH` (3): 4-digit PIN entry interface for administrative pause, unpause, or recovery.
5. `STATE_VOTING` (4): Candidate chosen; active 30-second inactivity timeout.
6. `STATE_CONFIRM` (5): Awaiting confirmation button press; active 30-second inactivity timeout.
7. `STATE_VOTE_SUBMISSION` (6): Monotonic sequence counter incremented in EEPROM *before* UART transmission.
8. `STATE_AUDIT_COMMIT` (7): Audit commitment window with visual display update.
9. `STATE_VOTE_COMPLETE` (8): Confirmation screen and completion beep before returning to `READY`.
10. `STATE_PAUSED` (9): Operational pause state; all voting buttons rejected; persists across power cycles.
11. `STATE_TAMPER_DETECTED` (10): Triggered by lid opening; non-volatile EEPROM latch; only cleared via physical closure + authorized PIN + valid configuration hash.
12. `STATE_ERROR` (11): Critical error state (e.g. self-test failure or configuration mismatch).

*In-Flight Ballot Discard Rule*: If an administrative pause or tamper event interrupts the device while in `STATE_VOTING` or `STATE_CONFIRM`, the in-progress ballot is immediately cleared and discarded.

#### Persistent EEPROM Memory Map (Total: 1024 Bytes ATmega328P EEPROM)

```
0x00 - 0x01: Magic Header [0x53, 0x56] ("SV", Little-Endian uint16 0x5653)
0x02 - 0x09: Device ID String (8 bytes, e.g. "EVM-001\0")
0x0A - 0x0D: Monotonic Sequence Counter (uint32_t, 4 bytes, big-endian)
0x0E       : Physical Tamper Latch Flag (uint8_t, 1 = tampered, 0 = normal)
0x0F - 0x4F: Configuration Hash String (65 bytes: 64 hex characters + null)
0x50 - 0x54: Admin Recovery PIN String (5 bytes, "1234\0")
0x56       : Operational Pause Flag (uint8_t, 1 = paused, 0 = active)
```
*Discipline*: **Zero per-vote data stored**. EEPROM holds only device state, sequence numbers, and configuration hashes. No voter votes or credentials exist in firmware memory.

#### Serial Communication Protocol (Source: `firmware/secureVOTE/serial_comm.cpp`)
- **Transport**: Hardware UART (9600 baud, 8-N-1, newline-delimited JSON).
- **Emitted Messages**:
  - `BOOT`: `{"type":"BOOT","device_id":"EVM-001","sequence_number":0,"config_hash":"..."}`
  - `STATE_CHANGE`: `{"type":"STATE_CHANGE","device_id":"EVM-001","sequence_number":N,"from_state":"...","to_state":"..."}`
  - `VOTE`: `{"type":"VOTE","device_id":"EVM-001","candidate_id":"C001","sequence_number":N,"session_token":"..."}`
  - `TAMPER`: `{"type":"TAMPER","device_id":"EVM-001","sequence_number":N,"details":"..."}`
  - `HEARTBEAT`: `{"type":"HEARTBEAT","device_id":"EVM-001","sequence_number":N,"state":"READY"}`
  - Inbound command: `PING` -> Responds with `{"type":"PONG"}`

---

### 2. Backend & Cryptographic Layer

- **Election Lifecycle State Machine**:
  `SETUP` -> `CONFIG_FROZEN` -> `LOCKED` -> `OPEN` -> `CLOSED` -> `PUBLISHED`
- **Role-Based Access Control (RBAC)**:
  - `ADMIN`: Election configuration, candidate registration, device authorization, state transitions.
  - `AUDITOR`: Full audit trail inspection, cryptographic verifier execution, anomaly review.
  - `OBSERVER`: Read-only access to published election tallies and manifests.
- **Tamper-Evident SHA-256 Audit Chain**:
  Every system event generates a tamper-evident log entry linked to its predecessor:
  $$\text{entry\_hash}_i = \text{SHA-256}(\text{previous\_hash} \parallel \text{election\_id} \parallel \text{event\_type} \parallel \text{event\_data} \parallel \text{timestamp})$$
- **Zero-Drift Reconciliation Rule**:
  Strict invariant enforced across all tallies:
  $$\sum \text{candidate\_votes} \equiv \text{total\_ballots} \equiv \sum \text{device\_votes}$$
- **Asymmetric Manifest Signing (Ed25519)**:
  Authoritative Result Manifests generated at `CLOSED`/`PUBLISHED` state are signed using Ed25519 over canonical JSON (`json.dumps(..., sort_keys=True, separators=(',', ':'))`).
- **Audit-Root Anchoring Abstraction**:
  Canonical Merkle root of all audit events is anchored to external or local targets:
  - `LOCAL ANCHOR`: In-memory reference commitment for deterministic testing.
  - `EXTERNAL ANCHOR`: Pluggable blockchain adapter (truthfully reports `NOT CONFIGURED` when external RPC endpoints are absent).
- **Advisory Anomaly Detection Engine**:
  Evaluates 6 deterministic rules without disrupting active voting operations:
  1. `R01_TAMPER_BURST`: Multiple tamper events detected across devices.
  2. `R02_REJECTION_SPIKE`: Excessive consecutive authorization or credential rejections.
  3. `R03_SEQUENCE_ANOMALY`: Non-sequential or duplicate sequence counter attempts.
  4. `R04_OFF_HOURS_ACTIVITY`: Operations occurring outside designated poll hours.
  5. `R05_VOTE_RATE_ANOMALY`: Unrealistic voting frequency on a single terminal.
  6. `R06_DEVICE_DISCONNECT`: Prolonged missed heartbeats from active voting terminals.
- **Keyed RFID / Identity Abstraction**:
  $$\text{RFID AUTHENTICATION} \neq \text{VOTER ELIGIBILITY}$$
  Raw card serial numbers are never saved in any database or audit event. UIDs are pseudonymized using HMAC-SHA256 with a mandatory server-side secret loaded from `SECUREVOTE_RFID_SECRET`. Fails safely with `RuntimeError` / `HTTP 500` if unconfigured.

---

### 3. Independent Standalone Verifier

Located in `backend/standalone_verifier/verifier.py`:
- **Complete Decoupling**: Contains **zero** imports from FastAPI, SQLAlchemy, or application ORM models. Operates entirely against an exported JSON election archive.
- **12 Independent Verification Checkpoints**:
  1. `export_envelope`: Cryptographic verification of archive structure.
  2. `configuration`: Slate hash recalculated from candidate list sorted by position.
  3. `ballot_hashes`: Every single ballot hash recomputed from raw components.
  4. `ballot_sequence`: Monotonic ordering and duplicate prevention verified per terminal.
  5. `candidate_totals`: Recounted directly from individual ballot records.
  6. `device_totals`: Recounted directly from individual ballot records.
  7. `reconciliation`: Strict exact match ($\text{candidates} == \text{total} == \text{devices}$).
  8. `audit_chain`: Full link-by-link cryptographic SHA-256 verification from genesis.
  9. `audit_root`: Recomputation of canonical SHA-256 Merkle root.
  10. `manifest`: Hash verification of result manifest against recounted totals.
  11. `signature`: Ed25519 digital signature verification using published SecureVOTE public key.
  12. `anchor`: Commitment receipt matching against recomputed audit root.

---

### 4. Automated Attack Demonstrations (`backend/tests/test_attacks.py`)

Twelve automated adversarial tests prove that the defense-in-depth architecture prevents, detects, and isolates election tampering:

| Test ID | Adversarial Attack Scenario | Security Defense & System Response |
|---|---|---|
| **Attack 1** | Direct SQL modification of audit log event data | Hash chain break detected immediately at corrupted entry. |
| **Attack 2** | Modification of candidate slate after election freeze | Configuration hash check fails; transition to `OPEN` blocked. |
| **Attack 3** | Re-submission of previously used voting session token | Rejected with `HTTP 409 Conflict` (Session already consumed). |
| **Attack 4** | Casting ballot after election state is set to `CLOSED` | Rejected with `HTTP 400 Bad Request` (Election not open). |
| **Attack 5** | Physical lid opening during voting operation | Hardware switch latched in EEPROM; device halted in `TAMPER_DETECTED`. |
| **Attack 6** | Direct database ballot insertion / tally tampering | Zero-drift reconciliation failure detected ($\text{drift} \neq 0$). |
| **Attack 7** | Replay of intercepted UART serial message | Rejected due to duplicate / non-monotonic sequence counter. |
| **Attack 8** | Ballot cast from unauthorized / revoked terminal | Rejected with `HTTP 403 Forbidden` (Device not ACTIVE). |
| **Attack 9** | Modification of candidate tally in signed result manifest | Ed25519 digital signature verification fails (`InvalidSignature`). |
| **Attack 10** | Modification of candidate ID in exported election archive | Standalone verifier detects ballot hash mismatch & tally divergence. |
| **Attack 11** | Corruption of anchored Merkle audit root | Standalone verifier detects mismatch between receipt and audit chain. |
| **Attack 12** | High-severity advisory anomaly trigger | Anomaly logged for human review, but voting operations remain unblocked. |

---

## Running SecureVOTE Locally

### Prerequisites
- Python 3.12+ with virtual environment
- Node.js 18+ and npm
- PlatformIO Core (CLI)
- MSYS2 / UCRT64 GCC toolchain (for native firmware unit tests on Windows)

### 1. Backend REST API (FastAPI)
```powershell
cd D:\secureVOTE\backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Run backend development server
uvicorn app.main:app --reload --port 8000
```
Interactive OpenAPI documentation is available at `http://localhost:8000/docs` (45 REST endpoints).

### 2. Next.js 14 Civic Ecosystem & Operations Dashboard
```powershell
cd D:\secureVOTE\dashboard
npm install
npm run dev
```
Accessible at `http://localhost:3000`:
- **Landing Gateway**: `http://localhost:3000/`
- **Citizen / Voter Portal**: `http://localhost:3000/voter` (Eligibility, Registration, Roll, Polling Station Finder, Complaints, Digital Voter Card, Voting Guide)
- **Digital EVM Simulator**: `http://localhost:3000/evm` (Interactive Terminal, Hardware LCD, Tactile Candidate Faceplate, VVPAT Preview)
- **Public Transparency Center**: `http://localhost:3000/transparency` (Safe aggregate telemetry, published candidate rosters, manifest proofs)
- **Independent Machine Verifier**: `http://localhost:3000/verify` (Browser-based zero-trust archive verification with drag-and-drop)
- **Officer Command Console**: `http://localhost:3000/command` and `http://localhost:3000/election/*` (Setup, Polling Operations, Counting Center, Reconciliation, Manifest Signing, Audit Explorer, Security Center, Attack Demonstration Sandbox)

### 3. Serial Bridge (Physical Hardware Link)
```powershell
cd D:\secureVOTE\firmware\bridge
python serial_bridge.py --port COM3 --baud 9600 --backend http://localhost:8000 --election EV-2026-001
```

### 4. Independent Standalone Verifier CLI
```powershell
# Export election archive from backend: GET /api/elections/{id}/export
python backend/standalone_verifier/verifier.py election_export.json
```

---

## Comprehensive Test Suite Execution

All test suites execute deterministically without external network or service dependencies:

### 1. Full Backend Test Suite (88 Tests)
```powershell
cd D:\secureVOTE\backend
.\venv\Scripts\pytest.exe tests/ -v
```
*Result*: **88 passed** across 15 test files.

### 2. Firmware Native Test Suite (17 Tests)
```powershell
cd D:\secureVOTE\firmware
$env:PATH = "D:\DevTools\ucrt64\bin;" + $env:PATH
pio test -e native
```
*Result*: **17 passed** across all state-machine, voting lifecycle, recovery, and persistence suites.

### 3. Firmware Arduino Uno Production Build
```powershell
cd D:\secureVOTE\firmware
pio run -e uno
```
*Result*: **SUCCESS** (RAM: 53.6%, Flash: 45.8% on ATmega328P).

### 4. Dashboard Vitest Unit Suite (28 Tests)
```powershell
cd D:\secureVOTE\dashboard
npm test -- --run
```
*Result*: **28 passed** across 7 test files (including error formatting and voter eligibility).

### 5. Dashboard Next.js Production Build
```powershell
cd D:\secureVOTE\dashboard
npm run build
```
*Result*: **SUCCESS** (41 static/dynamic pages compiled cleanly without errors).

### 6. Standalone Verifier Test Suite (12 Tests)
```powershell
cd D:\secureVOTE\backend
.\venv\Scripts\pytest.exe tests/test_standalone_verifier.py -v
```
*Result*: **12 passed** (validates 100% database/ORM disconnection and all tamper-detection assertions).

### 7. Attack Demonstration Suite (12 Tests)
```powershell
cd D:\secureVOTE\backend
.\venv\Scripts\pytest.exe tests/test_attacks.py -v
```
*Result*: **12 passed** across all 12 documented attack vectors.

---

## Architectural Boundaries & Limitations

1. **Plaintext UART Link**: Microcontrollers like the ATmega328P lack hardware cryptographic acceleration. Serial communications over UART (9600 baud) are plaintext JSON strings. Integrity and replay are governed by sequence counters and hash-chain verification, not wire-level TLS.
2. **Demo-Mode Credentials**: For bench demonstrations, `--demo-mode` creates synthetic test voter tokens tagged as `[DEMO-MODE]`. Production deployments would interface with dedicated hardware identity providers.
3. **Environment-Blocked External Integrations**:
   - **Docker Host Daemon**: `ENVIRONMENT-BLOCKED` (Host daemon inactive).
   - **Wokwi CLI Automated Runner**: `ENVIRONMENT-BLOCKED` (Requires `WOKWI_CLI_TOKEN`).
   - **Public Blockchain Ledger**: `NOT CONFIGURED` (`LocalAnchorProvider` active as default).
4. **Ballot Secrecy vs. Relational Traceability**: In this prototype, ballot secrecy is **not mathematically anonymous**. Each `Ballot` record maintains an explicit relational foreign-key linkage to its `VotingSession` (`session_id`) and associated credential. This was intentionally designed to enable educational demonstration of end-to-end audit tracing, duplicate vote prevention, and exact reconciliation. Real-world production systems require cryptographic mix-nets or homomorphic tallying to decouple voter identity from cast ballots.
5. **Research Prototype Notice**: SecureVOTE demonstrates verification architectures; it does not replace voter-verified paper audit trails (VVPAT) or national legal certification.

---

## Future Research Directions

- Hardware Security Module (ATECC608A / TPM 2.0) integration for hardware-accelerated Ed25519 signing.
- Cryptographic mixnets or homomorphic encryption (e.g. ElectionGuard) for end-to-end mathematical ballot secrecy.
- Air-gapped QR-code optical data transport between voting terminals and tally stations.
- Formally verified microkernels (e.g. seL4) for voting terminal operating systems.
