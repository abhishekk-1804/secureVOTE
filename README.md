# SecureVOTE

**Election Security Research Prototype — Embedded EVM + FastAPI + Next.js + Independent Verification**

SecureVOTE is an educational and academic security research prototype that explores how an electronic voting ecosystem can combine **embedded-device controls, authenticated device workflows, tamper-evident audit trails, cryptographic result signing, reconciliation, adversarial testing, and independent verification**.

> [!IMPORTANT]
> **Research / non-affiliation notice:** SecureVOTE is an independent educational and academic prototype. It is **not affiliated with, endorsed by, certified by, or operated by the Election Commission of India (ECI), BEL, ECIL, any State Election Commission, or any government authority.** It is not intended for legally binding elections.

## Product at a glance

SecureVOTE is deliberately larger than a dashboard:

- **Citizen / Voter Portal** — simulated eligibility, voter services, polling information, candidate information and grievance flows.
- **Digital EVM Twin** — browser-based simulation of an EVM-style voting workflow with candidate selection, confirmation, VVPAT preview, and optional **v3 Cryptographic Privacy Mode**.
- **SecureVOTE 3.0 Research Lab** — privacy-preserving electronic voting via Exponential ElGamal over NIST P-256 (`secp256r1`), additive homomorphic tallying, domain-separated SHA-256 commitments, and a 10-checkpoint independent verifier.
- **Physical EVM / Firmware** — Arduino Uno / ATmega328P firmware with an explicit 12-state finite-state machine, EEPROM state and physical tamper handling.
- **Election Operations Console** — election lifecycle, device operations, reconciliation, audit and security workflows.
- **Transparency Center** — aggregate election information and verification evidence without exposing raw credentials.
- **Independent Verifier** — database-independent verification of exported election records (v2 audit hash-chain & Ed25519 manifests, v3 homomorphic ciphertexts & commitments).
- **Security / Attack Lab** — deterministic adversarial scenarios for replay, tampering, configuration changes, tally manipulation, and ciphertext mutation.

## Architecture

```text
 Physical EVM / Digital EVM Twin
              │
              ▼
        Device / API Layer
              │
              ▼
       Election Backend
   FastAPI + PostgreSQL/SQLite
              │
       ┌──────┴───────┐
       ▼              ▼
   Audit Chain     Ballots / State
       │              │
       └──────┬───────┘
              ▼
       Reconciliation
              │
              ▼
       Result Manifest
              │
        Ed25519 Signature
              │
              ▼
     Independent Verifier
              │
       PASS / FAIL proofs
```

**Design principle:** Device ≠ Backend ≠ Verifier ≠ Dashboard.

The verifier is intentionally decoupled from FastAPI and SQLAlchemy so that exported election data can be checked independently.

## Security mechanisms explored

| Area | Prototype mechanism |
|---|---|
| Device state | Deterministic 12-state firmware FSM |
| Physical tamper | EEPROM-persistent tamper latch |
| Replay resistance | Monotonic device sequence numbers |
| Device authorization | Registered / revoked device checks |
| Auditability | SHA-256 hash-chained audit events |
| Result integrity | Canonical result manifest + Ed25519 signature |
| Reconciliation | Candidate totals = ballot total = device totals |
| Identity abstraction | HMAC-SHA256 keyed token handling |
| Independent verification | Offline JSON export verifier |
| Anomaly detection | Deterministic advisory rules |
| External anchoring | Local anchor abstraction; external ledger adapter is optional |

### Security boundary that matters

SecureVOTE intentionally does **not** claim that a hash chain, RFID, encryption, blockchain, or tamper logging alone makes an election secure.

In particular:

- RFID authentication is **not** voter eligibility.
- Tamper detection is **not** tamper prevention.
- A hash chain is **tamper-evident**, not magically immutable.
- A digital signature proves integrity/authorship of the signed manifest; it does not prove that the underlying election process was honest.
- The current research schema retains session-to-ballot linkage for tracing and testing, so **mathematical ballot anonymity is not claimed**.
- UART is plaintext in the current prototype.
- External public blockchain anchoring is **not configured** by default.

## Independent verification

One of the central demonstrations is:

```text
Export election archive
        │
        ▼
Independent verifier
        │
        ├── configuration
        ├── ballot hashes
        ├── ballot sequence
        ├── candidate totals
        ├── device totals
        ├── reconciliation
        ├── audit chain
        ├── audit root
        ├── manifest
        ├── Ed25519 signature
        └── anchor receipt
                │
          ┌─────┴─────┐
          ▼           ▼
        PASS         FAIL
```

A controlled mutation can intentionally change exported data and demonstrate that independent verification detects the resulting integrity failure.

## Validation snapshot

Latest project validation checkpoint:

| Component | Result |
|---|---:|
| Backend test suite | **88 / 88 passed** |
| Firmware native tests | **17 / 17 passed** |
| Dashboard tests | **28 / 28 passed** |
| Next.js production build | **43 / 43 routes compiled** |
| Standalone verifier tests | **12 / 12 passed** |
| Attack suite | **12 / 12 passed** |
| Deterministic 1,000-ballot demonstration | **Validated** |
| Docker / Wokwi automation | **Environment-blocked, documented** |

The repository contains reproducibility and security documentation for the detailed test methodology.

## Repository structure

```text
secureVOTE/
├── backend/                 # FastAPI, SQLAlchemy, election/security services
├── dashboard/               # Next.js / TypeScript civic + operations UI
├── firmware/                # Arduino / PlatformIO EVM firmware + serial bridge
├── docs/                    # Architecture, threat model, privacy, verification
├── docs/assets/              # Product showcase assets
└── README.md
```

## Run locally

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Dashboard

```powershell
cd dashboard
npm install
npm run dev
```

Open `http://localhost:3000`.

### Firmware

```powershell
cd firmware
pio run -e uno
pio test -e native
```

### Standalone verifier

```powershell
python backend/standalone_verifier/verifier.py election_export.json
```

## Research directions

SecureVOTE is intended as a platform for further study rather than a claim of production readiness.

Potential research directions include:

- cryptographic mixnets and stronger ballot-secrecy constructions;
- homomorphic tallying and end-to-end verifiability;
- hardware-backed key storage;
- formally verified embedded components;
- optical / air-gapped result transfer;
- stronger device attestation;
- measurable fault-injection and side-channel experiments;
- independent reproducibility studies.

## SecureVOTE 3.3 — India Election Security & Cryptographic Verification Research Platform

SecureVOTE 3.3 transforms the project into a comprehensive, multi-tiered Indian electoral security and cryptographic verification research platform.

### Key Highlights:
- **Electoral Geography Model**: Full 5-tier representation covering **12 reference Indian States & UTs** (Karnataka, Maharashtra, Tamil Nadu, Kerala, Telangana, Andhra Pradesh, Delhi, Uttar Pradesh, West Bengal, Gujarat, Rajasthan, Madhya Pradesh) spanning **64 Parliamentary Constituencies (PCs)** and **512 Assembly Constituencies (ACs)**.
- **Reference vs. Simulation Distinction**: Clearly differentiates official public Election Commission of India administrative reference names/counts from synthetic simulation datasets (electors, turnouts, ballots, devices, and candidate slates).
- **Interactive Command Center & Map**: SVG India Map centerpiece with hover tooltips, click-to-drilldown, turnout metrics, and accessible keyboard navigation.
- **Statutory Lifecycle Alignment**: Models the 12-stage Indian statutory lifecycle (Gazette Form 7A, two-stage EVM randomization, mock poll Rule 49E, Form 17C account of votes, counting Rule 56D, Form 20 final result sheet).
- **2-of-3 GJKR Threshold Decryption**: Distributed Key Generation with Pedersen VSS and Feldman polynomial commitments. Joint public key derived with zero trusted dealer.
- **Verifiable Partial Decryption**: Chaum-Pedersen Discrete Logarithm Equality (DLEQ) proofs generated by qualified trustees; secret shares $x_i$ strictly isolated on trustee security modules.
- **11-Point Verification Engine**: End-to-end verification checklist covering envelope integrity, configuration hashes, ballot chaining, device monotonicity, reconciliation, audit log, Ed25519 signatures, CDS94 1-hot ZKPs, and 2-of-3 threshold DLEQ proofs.

## Current limitations

1. The Arduino UART channel is plaintext.
2. The prototype database can retain a session-to-ballot relationship for research tracing.
3. Voter eligibility is simulated and is not connected to a statutory electoral roll.
4. The Digital EVM is a simulator / digital twin, not a certified election machine.
5. No certified VVPAT implementation is claimed.
6. External blockchain anchoring is not configured.
7. Docker and Wokwi automated execution depend on the local environment.

## Release & Milestone History

- **v2.0.0**: Locked baseline election-security research prototype (EVM digital twin + append-only audit log + Ed25519 manifest).
- **v3.0.0-research**: Exponential ElGamal over NIST P-256 (`secp256r1`), additive homomorphic tallying, and standalone independent verifier.
- **v3.1.0-research**: Cramer-Damgård-Schoenmakers (CDS94) disjunctive zero-knowledge ballot validity proofs ($c = c_0 + c_1 \pmod q$).
- **v3.2.0-research**: Gennaro-Jarecki-Krawczyk-Rabin (GJKR) 2-of-3 distributed key generation (DKG) and verifiable threshold partial decryption with Chaum-Pedersen DLEQ proofs.
- **v3.3.0-research (Current Branch)**: India Election Security & Cryptographic Verification Research Platform with interactive 12-state electoral hierarchy, Command Center, and 11-stage verification pipeline.
