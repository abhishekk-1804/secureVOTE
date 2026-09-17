# SecureVOTE - UI & Information Architecture Specification

## Overview

SecureVOTE 2.0 features a tri-modal user experience designed to serve distinct election stakeholders with appropriate context, ergonomics, and trust boundaries:

1. **Public / Citizen Portal (`/(public)/*`)**: Light civic design palette, high information accessibility, mobile-first responsive layouts. No officer sidebar.
2. **EVM Digital Twin (`/(evm)/*`)**: Fullscreen, tactile embedded device simulator replicating the physical Arduino hardware faceplate, LCD, LEDs, and physical button workflows.
3. **Election Officer Operations (`/(officer)/*`)**: Dense, professional operational console with dark institutional theme, structured 5-section sidebar navigation, and real-time telemetry.

```
                  +-----------------------------------+
                  |        Root Layout (app/)         |
                  |     - AuthProvider & Themes       |
                  +-----------------+-----------------+
                                    |
         +--------------------------+--------------------------+
         |                          |                          |
+--------v-------+          +-------v--------+         +-------v--------+
|   (public)/    |          |     (evm)/     |         |   (officer)/   |
| Public Portal  |          | Digital Twin   |         | Officer Console|
| - Landing      |          | - Fullscreen   |         | - 5-Sec Nav    |
| - Voter (8 pp) |          | - Hardware UI  |         | - Dark Theme   |
| - Transparency |          | - Single-use   |         | - Audit/Ops    |
| - Verifier     |          |   Session Auth |         | - Live Counter |
+----------------+          +----------------+         +----------------+
```

---

## Route Directory Map

### 1. Citizen & Public Routes (`/(public)/`)

| Route | Purpose | Access |
|---|---|---|
| `/` | System overview, architecture map, entrypoint gateways | Public |
| `/voter` | Citizen service portal landing & quick links | Public |
| `/voter/register` | Simulated voter registration form | Public (Demo) |
| `/voter/eligibility` | Deterministic voter eligibility evaluation | Public |
| `/voter/status` | Voting status lookup by voter ID | Public |
| `/voter/profile` | Digital voter card & post-vote verification status | Public |
| `/voter/roll` | Constituency electoral roll lookup | Public |
| `/voter/polling-station` | Polling station finder | Public |
| `/voter/candidates` | Published candidate roster and party symbols | Public |
| `/voter/complaints` | Grievance filing and tracking by reference ID | Public |
| `/voter/vote` | Gateway to the Digital EVM terminal | Public |
| `/voter/help` | Step-by-step voting guidance & FAQs | Public |
| `/transparency` | Public election transparency overview | Public |
| `/transparency/elections/[id]` | Election-specific aggregate telemetry & audits | Public |
| `/verify` | Independent third-party machine verifier | Public |

### 2. Digital EVM Twin (`/(evm)/`)

| Route | Purpose | Access |
|---|---|---|
| `/evm` | EVM device launcher & status monitor | Officer / Demo |
| `/evm/[deviceId]` | Interactive EVM terminal with LCD, buttons, LEDs, and VVPAT slip | Authorized Session |

### 3. Officer & Operational Routes (`/(officer)/`)

| Route | Purpose | Role Required |
|---|---|---|
| `/command` | Central command dashboard (legacy compatibility) | OBSERVER / ADMIN |
| `/election/setup` | Election creation, configuration lock, and state transitions | ADMIN |
| `/election/candidates` | Candidate nomination and roster management | ADMIN |
| `/election/parties` | Political party registry & compliance checklist | OBSERVER / ADMIN |
| `/election/polling-stations`| Polling booth setup and officer assignments | ADMIN |
| `/election/devices` | EVM unit registration, health tracking, status toggles | ADMIN |
| `/election/polling` | Live polling operations & session authorizations | ADMIN |
| `/election/counting` | Real-time candidate vs device totals & balance checking | AUDITOR / ADMIN |
| `/election/results` | Election Results Record & manifest signing | AUDITOR / ADMIN |
| `/election/verification` | Live cryptographic verification suite & anchor status | AUDITOR / ADMIN |
| `/election/audit` | Tamper-evident chronological audit log explorer | AUDITOR / ADMIN |
| `/election/security` | Advisory anomaly detection & RFID pseudonymization demo | AUDITOR / ADMIN |
| `/election/attacks` | Interactive 12-vector attack demonstration sandbox | OBSERVER / ADMIN |
| `/election/observers` | Non-mutating observation dashboard for designated observers | OBSERVER |
| `/election/reports` | Reconciliation certificates & archive export downloads | AUDITOR / ADMIN |
| `/election/complaints` | Officer grievance triage, assignment, and resolution | ADMIN |
| `/election/simulation` | Deterministic synthetic load generator (1k-100k ballots) | ADMIN |
| `/election/transparency` | Officer preview of citizen transparency data | OBSERVER / ADMIN |

---

## Design Tokens & Civic Palette

- **Civic Navy (`#1e3a5f`, `#2563eb`)**: Primary institutional branding, headers, actions.
- **Saffron (`#f59e0b`)**: Accent badges, warnings, active configuration indicators.
- **Emerald (`#10b981`)**: Verified audit chain, exact reconciliation, successful votes.
- **Rose (`#ef4444`)**: Rejected attempts, cryptographic mismatches, revoked units.
- **Slate (`#0f172a`, `#1e293b`)**: Dark institutional console for operations and EVM bezel.

---

## Accessibility & Trust Standards

1. **Zero-Trust Frontend**: All cryptographic claims, sequence enforcements, and state transitions originate from the backend API.
2. **Ballot Secrecy Guarantee**: Post-vote citizen screens display confirmation of vote recording without ever disclosing candidate selection.
3. **No Em-Dash Typography**: All UI text adheres strictly to standard hyphens for system compatibility.
