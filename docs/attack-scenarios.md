# SecureVOTE Attack Scenarios & Automated Test Suite

## 1. Overview & Adversary Model

SecureVOTE maintains an automated, deterministic attack test suite (`backend/tests/test_attacks.py`) composed of **20 reproducible attack scenarios**.

These tests simulate realistic physical, network, database, and administrative adversary actions to verify that:
1. Preventative controls reject invalid state transitions and replays before persistence.
2. Detective controls log tamper flags and surface advisory anomaly warnings.
3. Cryptographic controls (hash chains, Ed25519 signatures, zero-drift reconciliation) fail unmistakably if past data is mutated or deleted.

> [!NOTE]
> **Controlled Test Environment**:
> These attacks are implemented as reproducible pytest integration tests against a test database instance. They demonstrate exact system defense behavior without simulating destructive physical actions on live infrastructure.

---

## 2. Exhaustive Attack Catalog (20 Scenarios)

| # | Attack Scenario | Threat Vector | Target Asset | Expected Result | Automated Test |
|---|---|---|---|---|---|
| **01** | **Audit Row Mutation** | Direct SQL `UPDATE` on historical `audit_entries` | Hash Chain Continuity | `AUDIT VERIFICATION FAILED` (`is_intact=False`) | `test_attack_1_tamper_audit_record` |
| **02** | **Candidate Roster Mutation** | Altering candidate name/order post-lock | Frozen Candidate Slate | `CONFIGURATION HASH MISMATCH` | `test_attack_2_tamper_config_post_lock` |
| **03** | **Double Voting Session Replay** | Submitting vote on already-used session | Single-Use Session Quota | `HTTP 409 Conflict` (`Session already used`) | `test_attack_3_duplicate_session` |
| **04** | **Ballot Ingestion on Closed Poll** | Submitting vote when election state is `CLOSED` | State Machine Enforcement | `HTTP 409 Conflict` (`Election is not OPEN`) | `test_attack_4_vote_after_close` |
| **05** | **Physical Enclosure Breach** | Microswitch interrupt trigger on terminal | Hardware Security State | `TAMPER_DETECTED` logged; terminal `SUSPENDED` | `test_attack_5_tamper_event_logging` |
| **06** | **Tally Manipulation** | Directly incrementing candidate vote count | Mathematical Reconciliation | `RECONCILIATION FAILURE` (Sum cand $\neq$ total) | `test_attack_6_tally_manipulation` |
| **07** | **Message Replay Attack** | Re-sending previously accepted terminal packet | Monotonic Sequence State | `HTTP 409 Conflict` (`Sequence <= last seen`) | `test_attack_7_replay_message` |
| **08** | **Revoked Device Injection** | Submitting vote from `REVOKED` or unregistered unit | Hardware Whitelist | `HTTP 403 Forbidden` (`Device is not active`) | `test_attack_8_unknown_and_revoked_device` |
| **09** | **Modified Result Manifest** | Altering candidate tally in signed manifest | Ed25519 Digital Signature | `SIGNATURE_INVALID` on cryptographic verify | `test_attack_9_modified_signed_result` |
| **10** | **Corrupted Export Ballot** | Mutating ballot hash or choice in export JSON | Offline Independent Verifier | Verifier Checkpoint 3 / 7 `FAILED` | `test_attack_10_modified_exported_ballot` |
| **11** | **Modified Anchor Root** | Modifying external Merkle root commitment | External Trust Registry | `ANCHOR_ROOT_MISMATCH` on receipt check | `test_attack_11_modified_anchor_root` |
| **12** | **High-Rate Anomaly Burst** | Submitting rapid votes exceeding threshold | Advisory Anomaly Engine | Advisory finding logged; polling **not blocked** | `test_attack_12_high_severity_anomaly_does_not_block_operations` |
| **13** | **Biometric Isolation Audit** | Querying tables for raw RFID UIDs / biometrics | Voter Privacy Hygiene | Zero raw credentials found; keyed HMAC only | `test_attack_13_voter_anonymity_schema_isolation` |
| **14** | **Sequence Number Rollback** | Submitting device message with retrograde sequence | Sequence Monotonicity | `HTTP 409 Conflict` (`Sequence retrograde`) | `test_attack_14_sequence_rollback` |
| **15** | **Mid-Poll Candidate Injection** | Attempting `POST /candidates` in `OPEN` state | Candidate Lock Freeze | `HTTP 409 Conflict` (`Cannot add candidates in OPEN`) | `test_attack_15_candidate_insertion_in_open_state` |
| **16** | **Orphaned Audit Link Injection** | Inserting audit entry with fabricated previous hash | Chain Cryptography | Audit verification flags broken parent link | `test_attack_16_orphaned_audit_entry_detached_chain` |
| **17** | **Cross-Constituency Spoof** | Submitting vote for foreign constituency candidate | Electoral Roll Scoping | `HTTP 400 Bad Request` / Validation rejection | `test_attack_17_cross_constituency_candidate_spoofing` |
| **18** | **Tampered Genesis Block** | Altering initial genesis hash `GENESIS_PREV_HASH` | Audit Root Provenance | Full audit chain invalidation from Block 0 | `test_attack_18_tampered_genesis_block` |
| **19** | **Cross-Election Token Replay** | Presenting valid session token from Election A to B | Multi-Tenant Isolation | `HTTP 404 / 409` (`Session belongs to different election`) | `test_attack_19_cross_election_session_replay` |
| **20** | **Single-Use Session Replay** | Sequential re-execution of cast vote transaction | Session Atomicity | Second transaction rejected with `HTTP 409` | `test_attack_20_concurrent_double_ballot` |

---

## 3. How to Execute Attack Tests Deterministically

```bash
cd d:\secureVOTE\backend

# Activate virtualenv
.\venv\Scripts\Activate.ps1

# Run the complete 20-scenario suite
python -m pytest tests/test_attacks.py -v

# Run an individual attack (e.g. Attack 1 - Audit Tampering)
python -m pytest tests/test_attacks.py -k "test_attack_1" -v
```

All 20 tests assert against explicit HTTP error status codes (`403 Forbidden`, `409 Conflict`), verification flags (`is_intact: False`, `is_valid: False`), and cryptographic signature failures.
