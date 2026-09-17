# SecureVOTE Standalone Verifier Specification

## 1. Overview & Structural Independence Guarantee

The SecureVOTE Standalone Verifier (`backend/standalone_verifier/verifier.py`) is an offline, air-gapped, zero-trust verification tool.

### Absolute Independence Guarantees
1. **Zero ORM / Database Dependency**: The verifier contains **0 imports** from `sqlalchemy`, `fastapi`, `app.database`, or `app.models`. It runs purely using the Python standard library (`hashlib`, `json`, `os`, `sys`, `argparse`). Optional Ed25519 verification utilizes `cryptography` when public keys are supplied.
2. **Pure Data Consumer**: It operates solely upon self-contained, machine-verifiable JSON election export archives conforming to `docs/export_schema.json`.
3. **No Database Access**: Can execute in completely network-isolated and database-disconnected environments (e.g., air-gapped auditor laptops).

---

## 2. Cryptographic Verification Pipeline

The verifier executes **12 distinct, independent verification checks** in strict order:

```
+-------------------------------------------------------------------------+
|                    1. Export Envelope Integrity                         |
|   SHA-256(canonical_json(archive \ {export_hash})) == archive.export_hash|
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  2. Election Configuration Hash                         |
|  Recompute from raw candidate list sorted by position; compare to header|
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  3. Individual Ballot Hash Chain                        |
|  Recompute SHA-256 hash for EVERY recorded ballot from raw components   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  4. Monotonic Sequence Verification                     |
|  Verify sequence numbers strictly increase per device (anti-replay)     |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  5. Raw Candidate Tally Aggregation                     |
|  Independently aggregate candidate vote counts directly from ballots    |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                    6. Raw Device Tally Aggregation                      |
|  Independently aggregate device vote counts directly from ballots       |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  7. Exact Zero-Drift Reconciliation                     |
|  sum(candidate_totals) == total_ballots AND                             |
|  sum(device_totals) == total_ballots (Zero Tolerance)                   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  8. Audit Log Hash Chain Verification                   |
|  Link-by-link recalculation of entry_hash from raw event data & prev    |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                    9. Audit Root Commitment                             |
|  Final entry_hash committed as the immutable root of the election       |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  10. Result Manifest Hash Verification                  |
|  Recompute manifest_hash over tallies, status, config, and audit root   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  11. Ed25519 Digital Signature                          |
|  Verify asymmetric cryptographic signature over manifest_hash           |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  12. Anchor Receipt Cross-Verification                  |
|  Verify external immutable public ledger anchor against audit root      |
+-------------------------------------------------------------------------+
```

---

## 3. CLI Invocation and Arguments

```bash
python backend/standalone_verifier/verifier.py <path_to_export_archive.json> [options]
```

### Options:
- `--anchor <path_to_anchor_receipt.json>`: Optional path to external ledger or local anchor receipt.
- `--pubkey <hex_string>`: Optional Ed25519 public key hex string for digital signature validation.
- `--json`: Output machine-readable JSON verification report.
- `--verbose`: Print detailed step-by-step cryptographic audit logs.

### Exit Codes:
- `0`: **SUCCESS**  -  All verification checks passed with zero discrepancies.
- `1`: **VERIFICATION FAILURE**  -  Cryptographic mismatch, reconciliation failure, replay, or tampering detected.
- `2`: **INVALID INPUT / ERROR**  -  File not found, invalid JSON format, or unparseable payload.

---

## 4. Standalone Air-Gapped Auditor Workflow

1. Obtain export archive from the SecureVOTE server:
   ```bash
   curl -H "Authorization: Bearer <TOKEN>" https://server/api/elections/EV-2026-001/export -o archive.json
   ```
2. Copy `archive.json` and `backend/standalone_verifier/verifier.py` to an offline, air-gapped machine with standard Python 3.10+.
3. Run verification:
   ```bash
   python verifier.py archive.json --json
   ```
4. Confirm exit code is `0` and `"overall_status": "VERIFIED"`.
