# SecureVOTE — Advisory Anomaly Detection Specification

## Overview
SecureVOTE incorporates a transparent, rule-based anomaly detection engine. It continuously analyzes ballot timing, device sequence numbers, physical tamper signals, and rejection patterns to surface potential integrity anomalies for election administrators and independent auditors.

> **Security & Positioning Rule**:
> SecureVOTE intentionally avoids black-box machine learning models for anomaly detection. In high-assurance election systems, opacity breeds distrust. Anomaly detection must be **transparent, deterministic, explainable**, and strictly **advisory**.

---

## 1. Deterministic Rule Catalog

| Rule ID | Category | Severity | Detection Logic | Explanation |
| :--- | :--- | :--- | :--- | :--- |
| `RULE-TAMPER-001` | `TAMPER` | `HIGH` | Physical tamper event (`TAMPER_DETECTED`, `DEVICE_TAMPER_SWITCH`) logged in audit trail. | Hardware enclosure breach or optical tamper switch trip detected on voting device. |
| `RULE-REJ-001` | `INTEGRITY` | `HIGH` | Clustered rejection events ($\ge 3$) from replay attempts, unknown devices, or invalid tokens. | High concentration of rejected voting requests indicates potential replay attack or hardware misconfiguration. |
| `RULE-RATE-001` | `VELOCITY` | `HIGH` | More than 4 ballots cast within $\le 5$ seconds on a single EVM unit. | Voting velocity significantly exceeds human voter physical interaction capability; suggests automated ballot injection. |
| `RULE-SEQ-001` | `SEQUENCE` | `MEDIUM` | Sequence counter jump ($gap > 1$) between consecutively recorded ballots on a device. | Missing sequence number suggests an aborted in-flight session or dropped ballot record. |
| `RULE-STATE-001` | `DEVICE` | `MEDIUM` | Registered device in `SUSPENDED` or `REVOKED` state. | Quarantined or offline voting terminal remains assigned to election. |
| `RULE-AUTH-001` | `AUTHENTICATION` | `MEDIUM` | Same voter credential authorized for more than one voting session. | Duplicate voter check-in detected at registration/pollbook station. |

---

## 2. Advisory Finding Schema
Every finding is returned with complete contextual evidence:
```json
{
  "finding_id": "8f31b819-33e2-45e0-b6ab-9618b76c813d",
  "election_id": "EV-2026-001",
  "device_id": "EVM-001",
  "rule_id": "RULE-TAMPER-001",
  "category": "TAMPER",
  "severity": "HIGH",
  "evidence": {
    "event_id": 4,
    "sequence_number": 4,
    "event_type": "DEVICE_TAMPER_SWITCH",
    "timestamp": "2026-09-16T12:04:12Z"
  },
  "timestamp": "2026-09-16T12:04:12Z",
  "advisory_explanation": "ADVISORY FINDING: Physical hardware tamper detected on device 'EVM-001' at audit sequence 4. Hardware lock may have been triggered. REQUIRES HUMAN REVIEW.",
  "requires_human_review": true
}
```

---

## 3. The Hard Lifecycle Boundary Invariant
Per the master security specification and mandatory Phase 5 Amendment:
> **Non-Negotiable Invariant**: Anomaly findings must **NEVER** automatically block, delay, or alter:
> - Election lifecycle transitions (LOCK, OPEN, CLOSE, PUBLISH)
> - Result manifest generation or tallies
> - Cryptographic signing of results
> - Independent verification outcomes

Automated heuristic components must never possess the power to disenfranchise voters, stall an election, or invalidate certified election results. Findings are surfaced for **human review only**.

### 3.1 Verification Proof
This invariant is enforced in executable test code (`tests/test_anomaly_detection.py::test_mandatory_hard_lifecycle_boundary`):
1. A `HIGH`-severity anomaly is triggered on an active election.
2. The anomaly engine confirms the presence of `RULE-TAMPER-001`.
3. The election is transitioned to `CLOSED` (succeeds without error).
4. Results are verified and manifest is generated (succeeds with `EXACT_MATCH`).
5. Manifest is digitally signed with Ed25519 (succeeds without error).
6. Exported JSON archive is validated by the standalone verifier (succeeds 100% valid).
