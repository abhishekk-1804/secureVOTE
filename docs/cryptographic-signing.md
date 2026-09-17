# SecureVOTE  -  Cryptographic Artifact Signing Specification

## Overview
SecureVOTE employs asymmetric digital signatures using **Ed25519** (Edwards-curve Digital Signature Algorithm over Curve25519) to provide non-repudiation, tamper-evidence, and verifiable provenance for authoritative election artifacts.

As established in the core security specification:
> **Trust Boundary**: Digital signing is performed exclusively on the backend server. The resource-constrained embedded firmware (Arduino Uno ATmega328P with 2 KB RAM) does not perform asymmetric cryptography. Firmware integrity is governed by physical tamper detection, monotonic hardware sequence counters, and pre-computed configuration hashes.

---

## 1. Signed Artifacts

SecureVOTE supports asymmetric signing for two critical artifacts:

### 1.1 Result Manifest (`RESULT_MANIFEST`)
Generated upon completion of independent verification following election closure.
```json
{
  "artifact_type": "RESULT_MANIFEST",
  "artifact_version": "1.0.0",
  "election_id": "elec-general-2026",
  "manifest_hash": "c3f848074d47...64hex",
  "configuration_hash": "e6a18d9...64hex",
  "audit_root_hash": "9f83...64hex",
  "total_ballots": 1420,
  "reconciliation_status": "EXACT_MATCH",
  "audit_chain_status": "INTACT"
}
```

### 1.2 Audit-Root Verification Artifact (`AUDIT_ROOT_VERIFICATION`)
Authoritative commitment to the tip of the append-only SHA-256 audit log.
```json
{
  "artifact_type": "AUDIT_ROOT_VERIFICATION",
  "artifact_version": "1.0.0",
  "election_id": "elec-general-2026",
  "audit_root_hash": "9f83...64hex",
  "entry_count": 52
}
```

---

## 2. Canonical Serialization Rules
To prevent serialization malleability across different JSON parsers, platforms, and programming languages:
1. **Sort Keys**: JSON object keys are strictly lexicographically sorted (`sort_keys=True`).
2. **Compact Separators**: No whitespace after delimiters (`separators=(',', ':')`).
3. **Encoding**: UTF-8 bytes without BOM.
4. **Data Minimization**: Signed payloads contain only cryptographic commitments and metadata - never voter credentials, raw RFID UIDs, or unneeded plaintext.

---

## 3. Key Management & Provisioning

### 3.1 Ephemeral Keys for Automated Testing (CI)
Per the Phase 5 Amendments, automated tests in pytest **MUST NOT** assume persistent or committed keys. Tests generate ephemeral Ed25519 keypairs via the `ephemeral_signing_key` fixture at setup time and inject them in-memory into `SigningService`.

### 3.2 Persistent Key Provisioning for Demonstrations / Deployments
In an extended deployment or demonstration, a persistent private key must never be checked into git. It is provisioned using one of the following methods:

1. **Environment Variable**:
   ```bash
   export SECUREVOTE_SIGNING_KEY_HEX="<64-hex-character-ed25519-seed>"
   ```
2. **Mounted Secret File**:
   Mount a protected file (mode `0400`) at runtime and point the service to read the key.
3. **Hardware Security Module (HSM) / KMS**:
   In production implementations, signing keys reside inside HSMs (e.g. PKCS#11 or cloud KMS) where the private key cannot be extracted.

Public keys and fingerprints are exposed via the public endpoint `GET /api/signing/public-key`.

---

## 4. Lifecycle Rules & Enforcement
1. **State Gate**: Result manifest signing is strictly forbidden while an election is `CREATED` or `OPEN`. An election must be transitioned to `CLOSED` or `PUBLISHED` before signing is permitted.
2. **Integrity Gate**: Signing requires zero-drift reconciliation (`reconciliation_status == "EXACT_MATCH"`).
3. **Advisory Boundary**: Anomaly detection findings are advisory only and do not prevent an election administrator or auditor from signing a verified manifest.

---

## 5. Security Limitations & Trust Boundary
1. **Server Trust Boundary**: An Ed25519 signature confirms that the election authority server signed this specific result manifest. It does not prevent a compromised server from signing false tallies if the database itself was altered prior to manifest calculation. To detect server compromise, external auditors must independently recompute tallies using the standalone verifier on exported archives.
2. **Client Hardware Boundary**: The signature does not authenticate the physical EVM unit; device integrity relies on the authenticated device sequence counter and physical tamper latch.
