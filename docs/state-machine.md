# SecureVOTE — Firmware Finite State Machine (FSM)

## Overview
This document specifies the 12-state Finite State Machine implemented in the SecureVOTE C/C++ embedded firmware running on the Arduino Uno (ATmega328P). SecureVOTE is a **research-oriented prototype** demonstrating embedded voting integrity, **defense-in-depth**, and **tamper-evident** monitoring.

The firmware enforces strict separation of concerns, transition matrix validation, non-volatile EEPROM security latching, an explicit in-flight ballot discard rule, and idle timeout safety to prevent voting session abandonment or invalid operations.

---

## The 12 States

| State Enum | Identifier | Description | Recoverability |
|---|---|---|---|
| 0 | `STATE_BOOT` | Initial boot and hardware initialization. | Transient |
| 1 | `STATE_SELF_TEST` | Self-test: reads EEPROM sequence, verifies config hash, checks tamper & pause flags. | Transient |
| 2 | `STATE_READY` | Idle/ready state awaiting session authorization or administrative input. | Active |
| 3 | `STATE_ADMIN_AUTH` | Admin 4-digit PIN authentication mode (digit increment, advance, verify). | Active |
| 4 | `STATE_VOTING` | Voting session active; candidate options presented to the voter. | Active (30s timeout) |
| 5 | `STATE_CONFIRM` | Awaiting voter press of CONFIRM button to finalize vote choice. | Active (30s timeout) |
| 6 | `STATE_VOTE_SUBMISSION` | Vote commit: sequence incremented in EEPROM *before* UART transmission. | Transient |
| 7 | `STATE_AUDIT_COMMIT` | Audit record commitment phase with visual progress feedback. | Transient |
| 8 | `STATE_VOTE_COMPLETE` | Brief "Vote Recorded / Thank You" visual and auditory confirmation screen. | Transient |
| 9 | `STATE_PAUSED` | Administrative pause state. Voting suspended; persistent across power loss. | Recoverable via PIN |
| 10 | `STATE_TAMPER_DETECTED` | Enclosure switch breached. Non-volatile latch in EEPROM until authorized PIN recovery. | Recoverable via PIN |
| 11 | `STATE_ERROR` | System error state (e.g. self-test failure, config mismatch). | Recoverable via PIN |

---

## State Transition Matrix

The table below documents all valid transitions and rejection behavior:

| Source State | Event / Trigger | Target State | Condition / Notes |
|---|---|---|---|
| `BOOT` | `EVENT_BOOT_SUCCESS` | `SELF_TEST` | Boot initialization complete. |
| `SELF_TEST` | `EVENT_SELF_TEST_OK` | `READY` | Self-test passes and EEPROM pause flag is clear (`0x00`). |
| `SELF_TEST` | `EVENT_PAUSE_DETECTED` | `PAUSED` | Self-test passes but persistent EEPROM pause flag is set (`0x01`). |
| `SELF_TEST` | `EVENT_TAMPER_DETECTED` | `TAMPER_DETECTED`| Enclosure switch open or EEPROM tamper flag set. |
| `SELF_TEST` | `EVENT_ERROR_DETECTED` | `ERROR` | Configuration hash mismatch or memory failure. |
| `READY` | `EVENT_VOTE_START` | `VOTING` | Voter presses candidate button [1-4]. |
| `READY` | `EVENT_ADMIN_HOLD` | `ADMIN_AUTH` | Admin button held for $\ge 2$s (Pause Intent). |
| `READY` | `EVENT_TAMPER_DETECTED` | `TAMPER_DETECTED`| Enclosure breach detected. |
| `VOTING` | `EVENT_CANDIDATE_CHOSEN` | `CONFIRM` | Voter confirms candidate selection. |
| `VOTING` | `EVENT_IDLE_TIMEOUT` | `READY` | 30-second inactivity timeout expires; session reset. |
| `VOTING` | `EVENT_ADMIN_HOLD` | `ADMIN_AUTH` | Admin hold: **in-flight ballot discarded**; pause intent. |
| `VOTING` | `EVENT_TAMPER_DETECTED` | `TAMPER_DETECTED`| Enclosure breach detected. |
| `CONFIRM` | `EVENT_CONFIRM_PRESSED` | `VOTE_SUBMISSION`| Voter confirms selection; sequence incremented. |
| `CONFIRM` | `EVENT_CANCEL_PRESSED` | `VOTING` | Voter cancels and re-selects candidate. |
| `CONFIRM` | `EVENT_IDLE_TIMEOUT` | `READY` | 30-second inactivity timeout expires; session reset. |
| `CONFIRM` | `EVENT_ADMIN_HOLD` | `ADMIN_AUTH` | Admin hold: **in-flight ballot discarded**; pause intent. |
| `CONFIRM` | `EVENT_TAMPER_DETECTED` | `TAMPER_DETECTED`| Enclosure breach detected. |
| `VOTE_SUBMISSION` | `EVENT_TRANSMIT_OK` | `AUDIT_COMMIT` | Monotonic sequence committed to EEPROM and UART JSON sent. |
| `AUDIT_COMMIT` | `EVENT_COMMIT_COMPLETE` | `VOTE_COMPLETE` | Audit duration elapsed. |
| `VOTE_COMPLETE` | `EVENT_DISPLAY_TIMEOUT` | `READY` | Confirmation screen timeout elapsed (1.5s). |
| `ADMIN_AUTH` | `EVENT_PIN_OK_PAUSE` | `PAUSED` | Correct PIN entered when origin was `READY`/`VOTING`/`CONFIRM`. |
| `ADMIN_AUTH` | `EVENT_PIN_OK_UNPAUSE` | `READY` | Correct PIN entered when origin was `PAUSED`. |
| `ADMIN_AUTH` | `EVENT_PIN_OK_RECOVER` | `READY` | Correct PIN entered from `TAMPER`/`ERROR`, switch closed, hash matches. |
| `ADMIN_AUTH` | `EVENT_RECOVERY_FAILED` | `TAMPER_DETECTED` / `ERROR` | Switch still open or config mismatch during recovery. |
| `PAUSED` | `EVENT_ADMIN_HOLD` | `ADMIN_AUTH` | Admin hold initiated to enter unpause PIN. |
| `PAUSED` | `EVENT_ANY_VOTE` | *REJECTED* | **All voting transitions explicitly rejected.** |
| `TAMPER_DETECTED` | `EVENT_ADMIN_HOLD` | `ADMIN_AUTH` | Admin hold initiates recovery authentication. |
| `ERROR` | `EVENT_ADMIN_HOLD` | `ADMIN_AUTH` | Admin hold initiates diagnostic recovery. |

---

## The In-Flight-Ballot Rule
If an administrative pause is triggered (by holding the Admin button for $\ge 2000$ ms) while a voter session is active in `STATE_VOTING` or `STATE_CONFIRM`:
1. The firmware invokes `voting_discard_in_flight()` as an explicit, mandatory check prior to state transition.
2. All candidate selections, confirm flags, and session timestamps are immediately cleared and zeroed out.
3. The ballot is **never partially recorded** and **never carried into `STATE_PAUSED`**.
4. When the machine is subsequently unpaused by an administrator, the device returns to a clean `STATE_READY`. The voter must initiate a new, freshly authorized session.

---

## Non-Volatile Persistence Policy for `STATE_PAUSED`
- **Architectural Decision**: Administrative pause state **persists across device power loss / restarts**.
- **Implementation**: Stored at EEPROM byte `0x0056` (`EEPROM_PAUSE_ADDR`).
  - Transitioning to `STATE_PAUSED` writes `0x01` to EEPROM.
  - Unpausing writes `0x00` to EEPROM.
- **Fail-Safe Security Rationale**: If an election official pauses a voting machine for maintenance or polling suspension, an adversary cannot bypass the pause by disconnecting and reconnecting power. During `STATE_BOOT` and `STATE_SELF_TEST`, the firmware inspects the pause flag and boots directly into `STATE_PAUSED`. Only an authenticated administrator with the valid 4-digit PIN can return the machine to `STATE_READY`.

---

## Tamper Event Latency & Non-Volatile Persistence
The enclosure tamper switch is evaluated continuously in the main execution loop with debouncing. When triggered:
1. The previous operational state is captured **before** state modification.
2. The FSM transitions immediately to `STATE_TAMPER_DETECTED`.
3. The EEPROM tamper flag (`0x000E`) is latched to `0x01`.
4. A `TAMPER` JSON alert is emitted over UART.
5. A `STATE_CHANGE` event is emitted showing the exact origin state (e.g. `READY -> TAMPER_DETECTED` or `VOTING -> TAMPER_DETECTED`). The firmware **never** reports `TAMPER_DETECTED -> TAMPER_DETECTED`.
6. Red LED illuminates solid, auditory alarm sounds, and all voting operations are locked.
7. Power cycling does not clear the tamper latch. Recovery requires physical switch closure, administrator PIN authentication, and configuration hash re-verification.
