# SecureVOTE — External Audit-Root Anchoring Specification

## Overview
In electronic voting architectures, an append-only cryptographic hash chain protects the audit log against retroactive tampering. However, if the entire server database is compromised, an attacker could potentially regenerate an alternate hash chain starting from an early point in time.

To counter retroactive history rewriting, SecureVOTE implements **External Audit-Root Anchoring**: periodically committing the latest audit log entry hash (the "audit root") to an external medium outside the primary election server's administrative control.

---

## 1. Architectural Design & Abstraction
SecureVOTE decouples core election logic from any specific ledger technology via the `AnchorProvider` protocol:

```python
class AnchorProvider(Protocol):
    async def anchor(self, election_id: str, root_hash: str, metadata: dict) -> AnchorReceipt: ...
    async def get_anchor(self, reference: str) -> Optional[AnchorReceipt]: ...
    async def verify_anchor(self, reference: str, root_hash: str) -> bool: ...
```

### 1.1 `LocalAnchorProvider`
- **Label**: `LOCAL ANCHOR`
- In-memory/local storage provider designed for unit testing, demonstrations, and offline audits.
- **Truthful Claim**: Explicitly identified as a local commitment mechanism. It is **never** presented as decentralized or blockchain-backed evidence.

### 1.2 `ExternalLedgerAdapter`
- **Label**: `EXTERNAL ANCHOR`
- Interfaces with an external distributed ledger or public blockchain network when configured via environment variables:
  - `SECUREVOTE_LEDGER_RPC_URL`
  - `SECUREVOTE_LEDGER_CONTRACT`
- **Fail-Closed / Truthful Reporting**: When external credentials or RPC endpoints are not configured, the adapter immediately returns:
  - Status: `NOT CONFIGURED`
  - Notice: `ENVIRONMENT-BLOCKED: External ledger integration disabled.`
  - It does **not** crash and does **not** fake successful blockchain transactions.

---

## 2. Privacy & Data Minimization Invariant
Anchoring commitments are visible to external entities (and potentially the public in public blockchains). Therefore, SecureVOTE enforces a strict data minimization rule:

> **Data Minimization Rule**:
> Anchor payloads MUST NEVER contain voter credentials, raw RFID UIDs, PINs, candidate choices, or ballot plaintext.
>
> Attempting to pass sensitive voter identifiers into `AnchorProvider.anchor()` raises an immediate `ValueError`.

Permitted anchor commitment metadata:
```json
{
  "anchor_version": "1.0.0",
  "election_id": "EV-2026-001",
  "audit_root_hash": "3f82a1...64hex",
  "manifest_hash": "c92d0...64hex",
  "audit_entries_count": 42,
  "timestamp": "2026-09-16T12:00:00Z"
}
```

---

## 3. Anchor States
The system and dashboard distinguish between four explicit states:

1. `LOCAL ANCHOR`: Successfully committed to the local audit store.
2. `EXTERNAL ANCHOR`: Successfully committed to an external distributed ledger.
3. `NOT ANCHORED`: Reference does not exist or commitment was not found.
4. `ANCHOR VERIFICATION FAILED`: Stored anchor exists, but the committed root hash does not match the recomputed audit root.
5. `NOT CONFIGURED`: External ledger provider credentials or network access are unavailable.

---

## 4. Trust Boundaries & Security Limitations
1. **Commitment vs Correctness**: Anchoring an audit root commits the server to a specific state at a specific point in time. It proves that history has not been rewritten since the anchor was posted. However, anchoring does *not* prove that the votes recorded in that history are legally valid or that EVMs were uncompromised.
2. **Availability Boundary**: If an external blockchain network experiences network partitions or high gas fees, anchoring may fail. SecureVOTE ensures that failure to anchor does not block voter check-in or voting on physical EVMs.
