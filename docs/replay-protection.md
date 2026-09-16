# SecureVOTE — Replay Protection & Sequence Counter Specification

## Overview
In electronic voting systems, a critical threat is the replay or retransmission of previously emitted voting records (e.g. over a tapped serial line or by maliciously power-cycling a polling device).

SecureVOTE employs a **defense-in-depth** strategy combining:
1. Non-volatile monotonic sequence counters in device EEPROM.
2. Cross-reboot sequence restoration.
3. Strict backend sequence rejection (`HTTP 409 Conflict`).
4. Cryptographic integrity verification across all recorded ballots.

---

## 1. EEPROM Persistence Mechanism

The Arduino Uno's ATmega328P microcontroller contains 1024 bytes of internal non-volatile EEPROM. SecureVOTE allocates the memory space as follows:

```
Address Range   Size (bytes)   Purpose
0x0000 - 0x0001       2        Magic Marker (0x5653 / 'SV')
0x0002 - 0x0009       8        Device ID string (null-terminated, e.g. "EVM-001")
0x000A - 0x000D       4        Monotonic Sequence Counter (uint32_t, little-endian)
0x000E                1        Tamper Latch Flag (0x01 = LATCHED, 0x00 = CLEAR)
0x000F - 0x004F      65        Configuration Hash (64 hex characters + null)
0x0050 - 0x0054       5        Admin PIN ("1234\0")
0x0056                1        Pause Flag (0x01 = PAUSED, 0x00 = READY)
```

### Critical Storage Rule: No Per-Vote Data in EEPROM
No individual ballot selections or candidate IDs are stored in microcontroller EEPROM; only device metadata, operational flags, and the monotonic sequence counter are maintained in non-volatile memory to prevent replay and wear.

However, avoiding per-vote EEPROM storage does **NOT** provide system-wide voter privacy or ballot secrecy. In this educational prototype, the backend database explicitly links recorded ballots (`ballots.session_id`) to voting sessions (`voting_sessions.id`) and voter credentials (`voting_sessions.voter_credential`) to demonstrate complete audit trails and reconciliation.

---

## 2. Boot & Reboot Sequence Preservation

A common vulnerability in naive embedded counters is resetting `sequence_number = 0` whenever the microcontroller power is cycled.

In SecureVOTE:
1. During `STATE_BOOT`, the firmware calls `storage_read_sequence()`.
2. The 32-bit integer is loaded into active SRAM memory.
3. If the device reboots after casting 42 votes (counter at 42), the next vote will be numbered 43.
4. The sequence counter **never resets to 0** on reboot or power cycling.

---

## 3. Commit-Before-Transmit Ordering

To prevent desynchronization between physical state and UART transmission:
1. When the voter confirms their ballot, `storage_increment_sequence()` is called first.
2. The new counter value is committed to non-volatile EEPROM.
3. Only *after* EEPROM write succeeds is the JSON `VOTE` payload emitted over UART.
4. If a brownout or power disconnect occurs during transmission, the counter in EEPROM is already advanced, preventing double-use of any sequence number.

---

## 4. Backend Replay Enforcement

The backend maintains `last_seen_sequence` for every registered hardware device in the database:

$$\text{Valid Condition: } \text{sequence\_number} > \text{device.last\_seen\_sequence}$$

If an attacker captures a serial transmission with $\text{seq} = k$ and attempts to replay it:
- The backend checks: if $k \le \text{device.last\_seen\_sequence}$, the request is rejected with `HTTP 409 Conflict`:
  ```json
  {"detail": "REPLAY REJECTED: sequence_number 1 <= last accepted 2."}
  ```
- The rejected replay attempt is permanently appended to the tamper-evident audit log as an anomaly event.
