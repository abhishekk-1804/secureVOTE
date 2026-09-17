# SecureVOTE  -  WebSocket Protocol & Real-Time Event Architecture

## 1. Overview & Trust Boundary

The SecureVOTE dashboard requires real-time observability of election events without compromising the security boundaries established in the core architecture:
```
[ Hardware EVMs ] â”€â”€Serialâ”€â”€> [ Bridge ] â”€â”€RESTâ”€â”€> [ Backend API ]
                                                          â”‚
                                         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                                         â”‚ (Broadcaster)                   â”‚
                                         â–¼                                 â–¼
                             [ WebSocket Stream ]               [ REST Poll Fallback ]
                                         â”‚                                 â”‚
                                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                                          â–¼
                                              [ Next.js Dashboard ]
```

The WebSocket server provides an **ephemeral notification and event-streaming channel**.
- It does **not** replace the authoritative database or cryptographic audit log.
- It is a **loss-tolerant push optimization**. If a client disconnects, experiences network partitions, or drops frames, it falls back to querying the authoritative REST endpoints (`/api/elections/{id}/results`, `/api/elections/{id}/audit`, etc.).

---

## 2. Authentication Decision: Single-Use Handshake Ticket vs Query String JWT

### The Vulnerability of Query String Tokens
The W3C WebSocket standard in browsers (`new WebSocket(url)`) does not allow passing custom HTTP headers (such as `Authorization: Bearer <token>`) during the initial HTTP upgrade handshake.

A naive approach is to append the JWT to the query string:
```
ws://backend:8000/api/ws?token=eyJhbGciOi...
```
**Why this is prohibited in SecureVOTE**:
1. **Access Log Exposure**: Query strings are written in plaintext to reverse proxy logs (Nginx, Traefik), cloud load balancer logs, and API gateway access logs.
2. **Browser History & Cache**: Query strings remain stored in client history and referer headers.
3. **Replay Window**: A long-lived access token leaked through logs allows unauthorized observers to maintain persistent session taps.

### The Single-Use Ticket Solution & Strict Scope Binding
SecureVOTE implements a secure handshake ticket mechanism with strict scope binding:

1. **Ticket Request with Explicit Scope**:
   - The authenticated client requests a handshake ticket using its bearer token, declaring the intended scope:
     ```http
     POST /api/auth/ws-ticket HTTP/1.1
     Host: localhost:8000
     Authorization: Bearer <jwt_access_token>
     Content-Type: application/json

     {
       "election_id": "EV-2026-001"
     }
     ```
     *(To request a global monitor ticket, `election_id` is omitted or passed as `null`.)*

2. **Ephemeral Ticket Generation**:
   - The backend generates a cryptographically random, unguessable token (`secrets.token_urlsafe(32)`) with a short Time-To-Live (TTL = 60 seconds), binds it to `(username, role, election_id)`, stores it in an ephemeral in-memory cache, and returns:
     ```json
     {
       "ticket": "vK7_8L2mNp9...",
       "expires_in": 60,
       "election_id": "EV-2026-001"
     }
     ```

3. **Handshake & Strict Scope Validation**:
   - The client establishes the WebSocket connection using the short-lived ticket:
     ```
     ws://localhost:8000/api/ws/EV-2026-001?ticket=vK7_8L2mNp9...
     ```
   - **Immediate Invalidation (Single-Use)**: During the handshake, the backend atomically pops the ticket from memory. It cannot be used a second time under any circumstance.
   - **Scope Verification**:
     - Connecting to `/api/ws/{election_id}` requires a ticket bound to that exact `election_id`. A ticket issued for another election or a global ticket is **rejected with close code 1008**.
     - Connecting to `/api/ws` requires a ticket issued with global scope (`election_id=None`). An election-scoped ticket is **rejected with close code 1008**.
   - If a connection attempt arrives without a ticket, with an expired ticket, or with an out-of-scope ticket, the server immediately closes the socket with policy code `1008` (Policy Violation).

---

## 3. Endpoints & Scopes

- **Global Event Stream**:
  ```
  /api/ws?ticket=<global_ticket>
  ```
  Broadcasts events across all elections (used by system-wide administration monitors). Only accepts global tickets (`election_id=None`).

- **Election-Scoped Event Stream**:
  ```
  /api/ws/{election_id}?ticket=<scoped_ticket>
  ```
  Broadcasts events strictly scoped to `{election_id}` (used by command centers and election results views). Only accepts tickets explicitly bound to `{election_id}`.


---

## 4. Message Schema & Event Types

All messages emitted by the server follow a standardized JSON schema:

```json
{
  "event": "<EVENT_TYPE>",
  "election_id": "EV-2026-001",
  "timestamp": "2026-09-16T12:00:00.000000Z",
  "data": { ... }
}
```

### Supported Events

#### 1. `CONNECTED`
Sent by the server immediately after successful ticket handshake:
```json
{
  "event": "CONNECTED",
  "election_id": "EV-2026-001",
  "user": "admin",
  "role": "ADMIN"
}
```

#### 2. `VOTE_CAST`
Broadcast when a valid ballot is accepted and written to the database:
```json
{
  "event": "VOTE_CAST",
  "election_id": "EV-2026-001",
  "timestamp": "2026-09-16T12:05:00.123456Z",
  "data": {
    "ballot_id": "b8f2c01a-...",
    "device_id": "EVM-001",
    "sequence_number": 42,
    "ballot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "total_ballots": 42
  }
}
```
*Note: Per ballot secrecy design, candidate IDs are not broadcast in the raw vote event.*

#### 3. `AUDIT_EVENT`
Broadcast when any append-only audit record is committed to the hash chain:
```json
{
  "event": "AUDIT_EVENT",
  "election_id": "EV-2026-001",
  "timestamp": "2026-09-16T12:05:00.125000Z",
  "data": {
    "id": "a91b2c3d-...",
    "sequence_number": 105,
    "event_type": "VOTE_CAST",
    "entry_hash": "4a5b6c7d...",
    "actor": "voter_session",
    "device_id": "EVM-001",
    "timestamp": "2026-09-16T12:05:00.123456Z"
  }
}
```

#### 4. `DEVICE_STATUS_CHANGED`
Broadcast when a voting machine's operational state changes (e.g. registration, physical tamper trigger, or administrative suspension):
```json
{
  "event": "DEVICE_STATUS_CHANGED",
  "election_id": "EV-2026-001",
  "timestamp": "2026-09-16T12:10:00.000000Z",
  "data": {
    "device_id": "EVM-002",
    "old_status": "ACTIVE",
    "new_status": "SUSPENDED"
  }
}
```

#### 5. `ELECTION_STATE_CHANGED`
Broadcast when the election advances through its finite state machine (e.g., `LOCKED`, `OPEN`, `CLOSED`, `PUBLISHED`):
```json
{
  "event": "ELECTION_STATE_CHANGED",
  "election_id": "EV-2026-001",
  "timestamp": "2026-09-16T12:15:00.000000Z",
  "data": {
    "election_id": "EV-2026-001",
    "old_state": "OPEN",
    "new_state": "CLOSED",
    "reason": "Polls closed at scheduled time"
  }
}
```

---

## 5. Client Fallback & Reconnection Strategy

If a WebSocket connection cannot be established or drops unexpectedly:
1. The client sets its connection state to `fallback_polling`.
2. A periodic background poller runs against REST endpoints (default interval: 5 seconds):
   - `GET /api/elections/{id}`
   - `GET /api/elections/{id}/results`
   - `GET /api/elections/{id}/devices`
3. The client applies exponential backoff for WebSocket reconnection attempts (1s, 2s, 4s, 8s, up to 30s max), acquiring a fresh single-use ticket for each attempt.
4. Once reconnected, polling frequency slows or stops, and real-time push resumes seamlessly.
