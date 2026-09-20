# SecureVOTE 3.0 Architecture Audit

**Date**: 2026-09-20
**Auditor**: SecureVOTE Engineering Lead
**Baseline**: v2.0.0 (commit a86b266)

## 1. Repository Structure

```
secureVOTE/
├── backend/           # FastAPI + SQLAlchemy async + SQLite/PostgreSQL
│   ├── app/
│   │   ├── config.py         # Pydantic settings (DB, JWT, signing key)
│   │   ├── database.py       # Async SQLAlchemy engine + session factory
│   │   ├── main.py           # FastAPI app entry, CORS, router registration
│   │   ├── models.py         # 9 ORM models (User, Election, Candidate, Device, VotingSession, Ballot, AuditEntry, ResultManifest, Voter, PollingStation, Complaint)
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── geography.py      # Synthetic Indian constituency data
│   │   ├── routers/          # 19 API router modules
│   │   ├── services/         # 11 service modules
│   │   └── utils/            # Security utilities (password hashing, JWT)
│   ├── standalone_verifier/  # DB-independent election archive verifier
│   ├── tests/                # 15 test files, 100 tests
│   └── scripts/              # Seed/demo scripts
├── dashboard/         # Next.js 14 + TypeScript + Tailwind CSS
│   ├── app/                  # 43 routes (App Router)
│   ├── components/           # Reusable UI components
│   ├── lib/                  # API client, types
│   └── test/                 # 7 Vitest test files, 28 tests
├── firmware/          # Arduino ATmega328P + PlatformIO
│   ├── secureVOTE/           # 12-state FSM firmware
│   ├── bridge/               # Python serial bridge
│   └── test/                 # 17 native unit tests
├── docs/              # 25 documentation files
├── simulation/        # Election simulation scripts
└── exports/           # Exported election archives
```

## 2. Election Lifecycle State Machine

```
CREATED → CONFIGURED → LOCKED → OPEN → SUSPENDED ↔ OPEN → CLOSED → PUBLISHED
```

State transitions enforced in `election_service.py` with audit logging at each transition.

## 3. Cryptographic Trust Boundaries

### Current v2.0 Cryptographic Primitives

| Primitive | Usage | Library |
|-----------|-------|---------|
| SHA-256 | Ballot hashes, audit chain, config hash, manifest hash | hashlib |
| Ed25519 | Result manifest signing | cryptography (pyca) |
| HMAC-SHA256 | RFID identity pseudonymization | hmac + hashlib |
| HS256 JWT | Authentication tokens | python-jose |
| bcrypt | Password hashing | passlib |

### Trust Model Analysis

**Trust Assumption 1**: Database integrity is NOT trusted.
- Audit chain provides tamper evidence via SHA-256 hash chaining.
- Standalone verifier independently recomputes all hashes.
- ✅ Sound architectural decision.

**Trust Assumption 2**: Backend computes and holds all plaintext vote data.
- Ballots are stored as `(election_id, session_id, device_id, candidate_id, sequence_number)`.
- Anyone with DB access sees every voter's choice.
- ⚠️ **This is the primary privacy gap v3.0 must address.**

**Trust Assumption 3**: Signing key is held server-side.
- Ed25519 private key loaded from env or file.
- Single-authority signing (no threshold).
- ✅ Appropriate for prototype, documented limitation.

**Trust Assumption 4**: RFID pseudonymization provides identity abstraction.
- Raw UIDs are HMAC'd before storage.
- ✅ Sound, but RFID AUTH ≠ VOTER ELIGIBILITY is correctly documented.

## 4. Privacy Leakage Analysis

### Critical Finding: Ballot-Session Linkability

The `Ballot` model has a direct FK to `VotingSession`:
```python
session_id: Mapped[str] = mapped_column(..., ForeignKey("voting_sessions.id"), unique=True)
```

The `VotingSession` contains:
```python
voter_credential: Mapped[str]  # Links to voter identity
```

**Impact**: DB operator or compromised backend can reconstruct: voter → session → ballot → candidate_id.

**v3.0 Mitigation**: Encrypted ballots where the candidate selection is ciphertext, not plaintext.

### Secondary Finding: Device-Sequence Ballot Ordering

Even without session linkage, `(device_id, sequence_number)` combined with polling station observation could enable temporal correlation attacks.

**v3.0 Mitigation**: Document this metadata leakage explicitly. Full mix-net shuffle is out of scope but should be noted as future research.

## 5. Serialization Analysis

v2.0 uses `json.dumps(data, sort_keys=True, separators=(',', ':'))` for canonical serialization in:
- `signing_service.py` (manifest signing)
- `audit_service.py` (audit hash computation)
- `standalone_verifier/verifier.py` (independent verification)

**Finding**: Consistent across all three sites. No float ambiguity (all values are strings/ints). Timestamps are ISO-8601 strings.

**v3.0 Decision**: Extend this pattern with explicit domain separation prefixes for v3 artifacts.

## 6. Standalone Verifier Independence

The verifier (`standalone_verifier/verifier.py`) correctly has:
- Zero imports from `app.*`, `sqlalchemy`, `fastapi`
- 12 independent verification checkpoints
- CLI entry point
- Machine-readable JSON output

**v3.0 Extension**: Add v3 verification checkpoints for encrypted ballot artifacts, commitments, and homomorphic tally verification.

## 7. Attack Test Coverage

20 automated attack tests in `test_attacks.py` covering:
- Audit chain tampering (Attack 1)
- Configuration mutation (Attack 2)
- Session replay (Attack 3)
- Closed-election voting (Attack 4)
- Physical tamper events (Attack 5)
- Tally manipulation (Attack 6)
- UART message replay (Attack 7)
- Unauthorized device (Attack 8)
- Manifest signature mutation (Attack 9)
- Export archive mutation (Attack 10)
- Merkle root corruption (Attack 11)
- Advisory anomaly non-blocking (Attack 12)
- Schema isolation audit (Attack 13)
- Sequence rollback (Attack 14)
- Candidate insertion in OPEN state (Attack 15)
- Orphaned audit entry (Attack 16)
- Cross-constituency spoofing (Attack 17)
- Genesis block tampering (Attack 18)
- Cross-election session replay (Attack 19)
- Concurrent double ballot (Attack 20)

**v3.0 Extension**: Add attacks against encrypted ballots, commitments, ciphertext aggregation, key material, and protocol version.

## 8. v3.0 Research Direction

### Core Research Question
Can we add meaningful ballot privacy (encrypted candidate choices) to the existing integrity infrastructure without sacrificing the audit verification properties?

### Chosen Cryptosystem: Exponential ElGamal over NIST P-256

**Rationale**:
1. **Additive homomorphism**: `Enc(m1) * Enc(m2) = Enc(m1 + m2)` via encoding votes as group exponents.
2. **Mature library**: Python `cryptography` library (already a dependency) provides NIST P-256 elliptic curve operations.
3. **No new dependencies**: Avoids introducing heavyweight libraries like `phe` (Paillier) which have less mature maintenance.
4. **Performance**: EC operations are fast; 1000-ballot aggregation is sub-second.
5. **Limitation**: Decryption requires brute-force discrete log for small tallies (≤ ballot count). Acceptable for research prototype with ≤ 10,000 ballots.

**Alternative Considered**: Paillier via `phe` library.
- Pro: Native additive homomorphism without discrete log.
- Con: Much larger ciphertexts (2048-bit modulus), slower operations, additional dependency.
- Decision: ElGamal over EC is more educational, more compact, and uses existing `cryptography` dependency.

### Implementation Architecture

```
backend/app/crypto/
├── __init__.py           # Package init + version
├── elgamal.py            # Core ElGamal encryption/decryption/aggregation
├── keys.py               # Key generation, serialization, fingerprinting
├── ballot.py             # One-hot encoding, encrypted ballot artifact
├── commitment.py         # Domain-separated SHA-256 ballot commitments
├── canonical.py          # Deterministic canonical serialization (v3)
├── tally.py              # Homomorphic aggregation + decryption
├── verification.py       # Independent v3 artifact verification
├── serialization.py      # Ciphertext/key serialization formats
└── exceptions.py         # Typed crypto exceptions
```

### Privacy Model

| Information | Who can see it? | v2.0 | v3.0 |
|-------------|----------------|------|------|
| Candidate choice (plaintext) | DB operator | ✅ Visible | ❌ Encrypted |
| Encrypted ballot ciphertext | DB operator | N/A | ✅ Visible but opaque |
| Voter→session link | DB operator | ✅ Visible | ✅ Still visible (v2 compat) |
| Session→ballot link | DB operator | ✅ Visible | ⚠️ Separate v3 artifacts |
| Device sequence ordering | Observer at station | ✅ Visible | ✅ Still visible (metadata) |
| Aggregate tally | Public (after close) | ✅ Visible | ✅ Visible (decrypted) |

**Key Honesty**: v3.0 encrypts the vote content but does NOT eliminate session linkability or metadata leakage. This is explicitly documented.

## 9. Implementation Plan

### Phase 1: Crypto Core (backend/app/crypto/)
- ElGamal over P-256: keygen, encrypt, decrypt, aggregate
- Canonical serialization with domain separation
- Ballot commitments
- Unit tests for all crypto operations

### Phase 2: v3 API Layer (backend/app/routers/)
- `/api/v3/crypto/keys` - key generation
- `/api/v3/crypto/encrypt` - ballot encryption
- `/api/v3/crypto/tally` - aggregation + decryption
- `/api/v3/verification/verify` - v3 artifact verification

### Phase 3: Database Models
- `CryptoElection` - v3 election with key metadata
- `EncryptedBallot` - encrypted ballot artifacts
- `CryptoTally` - aggregated encrypted tally

### Phase 4: Standalone Verifier v3
- v3 verification checkpoints
- Independent ciphertext verification

### Phase 5: Research Engine
- Reproducible experiment runner
- Benchmark measurements

### Phase 6: Dashboard Research Lab
- `/research/*` routes
- Visual encryption/tally demonstration

### Phase 7: Attack Tests + Documentation
- v3 cryptographic attack tests
- Research documentation suite

## 10. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Breaking v2 tests | Run v2 tests after each phase |
| Crypto implementation bugs | Extensive test vectors, property tests |
| Performance bottleneck in ElGamal discrete log | Baby-step/giant-step for small tallies, document limitation |
| Dependency conflicts | Using existing `cryptography` library only |
| Frontend integration complexity | Incremental addition, no v2 UI changes |
