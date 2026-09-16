# SecureVOTE — Device Communication Protocol

## Overview
The SecureVOTE embedded firmware communicates with upstream collectors and the backend API using single-line JSON messages transmitted over UART serial at **9600 baud, 8-N-1** (8 data bits, no parity, 1 stop bit).

In this **research-oriented prototype**, the hardware device emits structured events that can be ingested by the Python serial bridge (`firmware/bridge/serial_bridge.py`) and relayed to the FastAPI REST backend.

---

## Message Types & Schemas

### 1. `BOOT`
Emitted immediately upon device power-on, boot initialization, and self-test completion.

```json
{
  "type": "BOOT",
  "device_id": "EVM-001",
  "sequence_number": 0,
  "config_hash": "34d70b0c609559c403328e1215b3e6c0c5980e07cb185b3db5c088c445a49f87"
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | Constant `"BOOT"`. |
| `device_id` | string | Unique hardware identifier stored in EEPROM (e.g. `"EVM-001"`). |
| `sequence_number` | integer | Current non-volatile sequence counter value read from EEPROM. |
| `config_hash` | string | Full 64-character SHA-256 configuration hash of the loaded candidate configuration. |

---

### 2. `STATE_CHANGE`
Emitted whenever the firmware Finite State Machine (FSM) transitions from one state to another.

```json
{
  "type": "STATE_CHANGE",
  "device_id": "EVM-001",
  "sequence_number": 0,
  "from_state": "BOOT",
  "to_state": "READY"
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | Constant `"STATE_CHANGE"`. |
| `device_id` | string | Unique hardware identifier. |
| `sequence_number` | integer | Monotonic sequence counter. |
| `from_state` | string | Origin state name (e.g. `"BOOT"`, `"SELF_TEST"`, `"READY"`, `"VOTING"`, `"CONFIRM"`). |
| `to_state` | string | Destination state name (e.g. `"READY"`, `"VOTING"`, `"CONFIRM"`, `"VOTE_SUBMISSION"`, `"AUDIT_COMMIT"`, `"VOTE_COMPLETE"`, `"PAUSED"`, `"TAMPER_DETECTED"`, `"ERROR"`). |

---

### 3. `VOTE`
Emitted when a voter completes candidate selection, confirms their choice, and the vote is finalized.

```json
{
  "type": "VOTE",
  "device_id": "EVM-001",
  "candidate_id": "C001",
  "sequence_number": 1,
  "session_token": "SES-demo-session-token"
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | Constant `"VOTE"`. |
| `device_id` | string | Unique hardware identifier. |
| `candidate_id` | string | Chosen candidate identifier (e.g. `"C001"`). |
| `sequence_number` | integer | Strictly monotonic sequence number (incremented in EEPROM *before* emission). |
| `session_token` | string | Simulated credential/session authorization token validating one-person-one-vote. |

---

### 4. `TAMPER`
Emitted instantaneously when the physical enclosure lid/breach switch is triggered.

```json
{
  "type": "TAMPER",
  "device_id": "EVM-001",
  "sequence_number": 2,
  "details": "enclosure_breached"
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | Constant `"TAMPER"`. |
| `device_id` | string | Unique hardware identifier. |
| `sequence_number` | integer | Monotonic sequence counter. |
| `details` | string | Diagnostic breach information (e.g. `"enclosure_breached"`). |

---

### 5. `HEARTBEAT`
Emitted periodically (every 10 seconds) during idle operation to confirm device liveness.

```json
{
  "type": "HEARTBEAT",
  "device_id": "EVM-001",
  "sequence_number": 2,
  "state": "READY"
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | Constant `"HEARTBEAT"`. |
| `device_id` | string | Unique hardware identifier. |
| `sequence_number` | integer | Monotonic sequence counter. |
| `state` | string | Current FSM state name. |

---

## Bridge Relay Mapping

The Python serial bridge (`firmware/bridge/serial_bridge.py`) translates incoming UART JSON records into backend REST API requests:

1. **`VOTE`** $\rightarrow$ `POST /api/votes` with `{ session_token, candidate_id, device_id, sequence_number }`.
2. **`TAMPER`** $\rightarrow$ `PATCH /api/elections/{election_id}/devices/{device_id}/status` with `{"status": "SUSPENDED"}` and appends to backend tamper audit log.
3. **`BOOT` / `STATE_CHANGE` / `HEARTBEAT`** $\rightarrow$ Parsed and logged for operational telemetry and audit trail.
