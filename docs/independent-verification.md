# SecureVOTE — Independent Verifier Specification

## Overview
A core tenet of electronic voting integrity is that verification must **never** be performed by simply asking the server whether results are verified.
> **The Independent Verification Principle**: An auditor must be able to download a self-contained, machine-verifiable cryptographic archive or evidence bundle of the election, disconnect from all networks and databases, and independently reconstruct every hash, sequence, tally, chain link, zero-knowledge proof, and cryptographic signature from raw ground-truth records.

---

## 1. Structural Database Independence
The standalone verification engine (`backend/standalone_verifier/`) is structurally decoupled from the backend application:
- **Zero ORM Dependencies**: Contains no imports of SQLAlchemy, database models, session managers, or SQLite/Postgres drivers.
- **Zero API Dependencies**: Contains no imports of FastAPI, Starlette, or server routers.
- **AST Enforced**: CI includes automated AST analysis tests (`test_standalone_modules_have_zero_database_or_orm_imports`) that parse every standalone verifier module and fail if any database or ORM symbol is imported.
- **Disconnected Subprocess Proof**: CI runs an automated test (`test_cli_subprocess_database_disconnected`) that sets `DATABASE_URL` to an unreachable invalid socket, launches the verifier CLI in an isolated subprocess, and proves that full verification succeeds completely without database access.

---

## 2. Portable Evidence Bundles (`SECUREVOTE-EVIDENCE-BUNDLE-1`)

Evidence bundles provide self-contained, air-gapped cryptographic proofs for elections:
- **Directory Bundles**: Unpacked folder hierarchy containing canonical JSON files and human instructions.
- **ZIP Bundles**: Single-file zip archive verifiable without disk extraction.

### Security Defenses & Archive Hardening:
1. **Path Traversal & Device Name Protection**: All relative paths are normalized through `normalize_bundle_path`, rejecting:
   - Null bytes (`\0`) and ASCII control characters (< 32).
   - Absolute paths and volume separators (`:`, `/`, `\`).
   - Directory traversal sequences (`..`).
   - Redundant or empty segments (`//`, `./`, `/.`).
   - Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) and segments with trailing dots/spaces.
2. **ZIP Archive Alias & Shadowing Defenses**:
   - Duplicate raw member names or alias collisions (e.g. `./manifest.json` and `manifest.json` in the same archive) trigger immediate rejection.
   - Symbolic link entries (`S_IFLNK`) are prohibited and rejected.
   - Decompression limits: maximum 50 MB per file, 500 MB cumulative to prevent zip bombs.
3. **Directory Bundle Symlink Defenses**:
   - `os.path.realpath` enforcement ensures any symlink pointing outside the bundle root is rejected with `PermissionError`.
4. **Deterministic Canonicalization**:
   - `RFC-CANONICAL-JSON-1` serialization with recursive floating-point number rejection.
   - Inventory items sorted lexicographically by canonical relative path.

---

## 3. Cryptographic Verification Checkpoints

The bundle verifier executes up to **15 distinct independent mathematical checkpoints**:

| Checkpoint | Scope | Validation Rule |
| :--- | :--- | :--- |
| `checkpoint_1_bundle_schema` | Schema | Protocol versions, required fields, recursive float prohibition |
| `checkpoint_2_manifest_hash` | Hash | `SHA-256(canonical_json(manifest \ {manifest_hash, signature}))` |
| `checkpoint_3_inventory_integrity` | File Hashes | Recomputes SHA-256 and byte sizes of all declared files; detects rogue files |
| `checkpoint_4_signature` | Signatures | Ed25519 asymmetric signature verification over manifest hash (or `NOT_APPLICABLE` if unsigned) |
| `checkpoint_5_election_identity` | Context | Consistent binding between manifest `election_id` and context files |
| `checkpoint_6_candidate_config` | Candidates | Candidate list ordering, length $\ge 2$, and candidate_count equality |
| `checkpoint_7_public_key` | Public Key | Valid curve point on `secp256r1`, not infinity, fingerprint matches |
| `checkpoint_8_ballot_ciphertexts` | Ballots | $C_1, C_2$ on curve, $C_1 \ne \mathcal{O}$, slot count matches candidate count, commitments and artifact hashes recomputed |
| `checkpoint_9_zk_validity_proofs` | ZKP | Zero-knowledge 1-of-2 CDS94 disjunctive validity proofs and sum proofs ($\forall j: v_j \in \{0, 1\} \land \sum v_j = 1$) |
| `checkpoint_10_homomorphic_aggregation`| Homomorphic Tally | Independent EC addition of all ballot ciphertexts: published tally == $\sum_{i} \text{Ballot}_i$ |
| `checkpoint_11_tally_commitment` | Commitments | Recomputed tally commitment matches published commitment |
| `checkpoint_12_threshold_manifest` | Threshold DKG | $1 \le t \le n$, qualified trustees $|QUAL| \ge t$, joint public key on curve |
| `checkpoint_13_partial_decryption_proofs`| Trustee Proofs | Chaum-Pedersen equality proofs $\text{PoK}\{x_i: W_{ij} = x_i A_j \land Y_i = x_i G\}$ for all selected trustees |
| `checkpoint_14_lagrange_combination`| Threshold Decryption | Lagrange coefficients $\lambda_i$, combined points $D_j = \sum \lambda_i W_{ij}$, discrete log recovery $M_j = B_j - D_j = v_j G$ |
| `checkpoint_15_tally_reconciliation` | Reconciliation | Decrypted candidate tallies sum exactly to total ballots (zero tolerance drift); candidate sets match |

---

## 4. Machine-Readable Schema

The bundle verifier outputs structured JSON with explicit machine-readable status values:
- `VALID`: All mathematical checkpoints succeeded.
- `INVALID`: Cryptographic discrepancy, tampered hash, or drift detected.
- `MALFORMED`: Corrupted schema, float detected, or unsafe archive path.
- `UNSUPPORTED`: Unsupported protocol or canonicalization version.
- `NOT_APPLICABLE`: Legitimate optional feature not active in bundle (e.g. unsigned mode, centralized key mode).

```json
{
  "verified": true,
  "overall_status": "VALID",
  "bundle_id": "EV-2026-001",
  "protocol_version": "SECUREVOTE-EVIDENCE-BUNDLE-1",
  "election_protocol_version": "SECUREVOTE33",
  "manifest_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "signature_status": "VALID",
  "checkpoints_total": 15,
  "checkpoints_passed": 15,
  "checkpoints_failed": 0,
  "checkpoints_not_applicable": 0,
  "checkpoints": [ ... ],
  "explicit_limitations": [
    "Verifies supplied cryptographic evidence; does not independently establish voter physical identity or eligibility.",
    "Does not guarantee coercion resistance, receipt-freeness, or physical EVM paper/VVPAT printout equivalence.",
    "Assumes threshold non-collusion (threshold t trustees colluding can reconstruct secret key x).",
    "Does not constitute legal or regulatory election certification."
  ]
}
```

---

## 5. CLI Execution

Auditors can run the standalone bundle verifier from any terminal:
```bash
python -m standalone_verifier.verify_bundle <path_to_bundle_directory_or_zip> [--json] [--trusted-key <hex>]
```
Exits with code `0` if all assertions pass, or `1` if any checkpoint fails.
