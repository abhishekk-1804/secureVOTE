# SecureVOTE — Independent Verifier Specification

## Overview
A core tenet of electronic voting integrity is that verification must **never** be performed by simply asking the server whether results are verified.
> **The Independent Verification Principle**: An auditor must be able to download a self-contained, machine-verifiable JSON archive of the election, disconnect from all networks and databases, and independently reconstruct every hash, sequence, tally, chain link, and cryptographic signature from raw ground-truth records.

---

## 1. Structural Database Independence
The standalone verifier (`backend/standalone_verifier/`) is structurally decoupled from the backend application:
- **Zero ORM Dependencies**: Contains no imports of SQLAlchemy, database models, session managers, or SQLite/Postgres drivers.
- **Zero API Dependencies**: Contains no imports of FastAPI, Starlette, or server routers.
- **AST Enforced**: CI includes an automated AST analysis test (`test_verifier_has_zero_database_or_orm_imports`) that parses the verifier code and fails if any database or ORM symbol is imported.
- **Disconnected Subprocess Proof**: CI runs an automated test (`test_database_disconnected_proof`) that sets `DATABASE_URL` to an unreachable invalid socket, launches the verifier CLI in an isolated subprocess, and proves that full verification succeeds completely without database access.

---

## 2. Independent Recomputation (The 12 Checks)
The verifier reconstructs 12 independent checks:
1. **Export Envelope Hash**: Recomputes SHA-256 of canonical JSON without `export_hash`.
2. **Configuration Hash**: Recomputes SHA-256 of candidate IDs and positions sorted by position.
3. **Ballot Hashes**: Recalculates `SHA-256(election_id | session_id | candidate_id | device_id | sequence_number | timestamp)` for **every single ballot** in the archive.
4. **Ballot Sequence Integrity**: Enforces that per-device sequence numbers are strictly monotonic and never repeat (replay protection).
5. **Candidate Tallies**: Recounts candidate votes directly from the verified raw ballots.
6. **Device Totals**: Recounts device vote totals directly from the verified raw ballots.
7. **Zero-Drift Reconciliation**: Enforces that `sum(candidate_totals) == total_ballots == sum(device_totals)` with exact zero tolerance.
8. **Audit Log Hash Chain**: Recomputes the SHA-256 hash for every chronological audit log entry:
   `entry_hash = SHA-256(seq | event_type | event_data | timestamp | previous_hash)`.
9. **Audit Root Commitment**: Verifies that the final entry hash in the verified chain matches the audit root.
10. **Result Manifest Hash**: Recomputes the manifest hash from the independently recounted totals and compares against the manifest record.
11. **Digital Signature**: Cryptographically verifies the Ed25519 digital signature on the canonical manifest payload using the public key.
12. **Audit Root Anchor**: Verifies that the external/local anchor receipt commits to the identical audit root hash.

---

## 3. Machine-Readable Schema
The verifier outputs structured JSON with explicit machine-readable failure codes:
```json
{
  "valid": true,
  "checks": {
    "export_envelope": true,
    "configuration": true,
    "ballot_hashes": true,
    "ballot_sequence": true,
    "candidate_totals": true,
    "device_totals": true,
    "reconciliation": true,
    "audit_chain": true,
    "audit_root": true,
    "manifest": true,
    "signature": true,
    "anchor": true
  },
  "failures": [],
  "summary": {
    "election_id": "EV-2026-001",
    "total_ballots_recounted": 1420,
    "candidates_recounted": 4,
    "devices_recounted": 3,
    "audit_entries_recomputed": 64,
    "audit_root_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "reconciliation_drift": 0
  }
}
```

Failure codes include:
- `EXPORT_ENVELOPE_MISMATCH`
- `CONFIGURATION_HASH_MISMATCH`
- `BALLOT_HASH_MISMATCH`
- `BALLOT_SEQUENCE_INVALID`
- `RECONCILIATION_FAILURE`
- `AUDIT_CHAIN_INVALID`
- `MANIFEST_MISMATCH`
- `SIGNATURE_INVALID`
- `ANCHOR_MISMATCH`

---

## 4. CLI Execution
Auditors can run the verifier from any terminal:
```bash
python -m standalone_verifier <path_to_election_export.json> --anchor-receipt <path_to_anchor.json>
```
Exits with status code `0` on complete success, or `1` if any check fails.

---

## 5. Trust Boundaries & Limitations
1. **Omission vs Alteration**: The verifier detects any modification or insertion of ballot records, sequence tampering, or audit chain alteration. However, if a malicious server silently drops a ballot before generating the export, the internal hash chain may still look valid if the sequence numbers were falsified. Monotonic sequence gap analysis and physical voter-verified paper audit trails (VVPAT) provide defense-in-depth against ballot dropping.
2. **Export Integrity**: Verification assumes the exported JSON file was transferred without truncation. The `export_envelope` hash ensures transmission integrity.
