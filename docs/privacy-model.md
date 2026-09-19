# SecureVOTE Privacy & Anonymity Model

## 1. Executive Summary & Research Honesty

SecureVOTE is an educational simulation and security research prototype. While it enforces strict identity pseudonymization and access control at its boundaries, **this research prototype is NOT mathematically anonymous**.

Each cast `Ballot` record maintains an explicit relational foreign-key linkage to its `VotingSession` (`session_id`) and associated credential. This design was chosen intentionally to enable clear educational demonstration of end-to-end audit tracing, duplicate voting rejection, and exact multi-point reconciliation.

In this document, we transparently disclose what data exists, what is synthetic, what is pseudonymized, what is publicly exposed, and what cryptographic mechanisms are required for production-grade secret-ballot elections.

---

## 2. Inventory of Voter Information & Data Lifecycle

| Data Element | Storage Location | Sensitivity | Pseudonymized? | Publicly Exposed? |
|---|---|---|---|---|
| **Elector Full Name** | `voters` table (SQLite/PostgreSQL) | Synthetic Demo Data | No (Plaintext in demo roll) | Searchable in public simulated roll |
| **Voter ID / EPIC Number** | `voters` table | Synthetic Demo Data | No (e.g. `VTR-00101`) | Searchable in public simulated roll |
| **Date of Birth** | `voters` table | Synthetic Demo Data | No (e.g. `1994-05-12`) | Searchable in public simulated roll |
| **Constituency & Polling Station** | `voters` table | Synthetic Reference Data | No (e.g. `Bengaluru Central`) | Displayed on voter card / slip |
| **Raw RFID Chip UID** | **NEVER STORED** | High (Physical Token) | **Yes — Irreversibly** | **NEVER EXPOSED** |
| **Keyed RFID Pseudonym** | Audit log metadata | Cryptographic Identifier | Yes: `HMAC-SHA256(raw_uid, SECRET)` | Truncated hex snippet in officer view |
| **Voting Session Credential** | `voting_sessions` table | Ephemeral Session Token | Random UUID / single-use token | Required for ballot submission API |
| **Cast Ballot Choice** | `ballots` table | High (Elector Choice) | Associated with `session_id` | Aggregated only in public results |
| **Audit Trail Entries** | `audit_entries` table | Operational Metadata | Actor attribution (`admin`, `EVM-001`) | Hash chain publicly exportable |

---

## 3. Boundary Principle: Decoupled Authentication

To demonstrate modern identity abstraction without compromising data hygiene, SecureVOTE implements the **Decoupled Verification Principle**:

$$\text{RFID AUTHENTICATION} \neq \text{VOTER ELIGIBILITY}$$

1. **Zero Raw Biometric / UID Storage**:
   - The embedded RFID reader or web simulator captures the hardware UID (e.g. `CARD-VALID-01`).
   - The backend immediately computes a keyed pseudonym:
     $$\text{pseudonym} = \text{HMAC-SHA256}(\text{raw\_uid}, \text{SECUREVOTE\_RFID\_SECRET})$$
   - The raw UID is discarded immediately from memory and is **never** written to database tables, logs, or response payloads.
2. **Eligibility Independence**:
   - Tapping an authenticated RFID card proves possession of a registered token.
   - However, a voting session is only granted if the independent electoral roll confirms the elector is eligible in that constituency, the election state is `OPEN`, and the elector has not already voted.

---

## 4. Why This Prototype Is Not Mathematically Anonymous

In real-world democratic elections, voter privacy requires **ballot secrecy** (the inability of anyone, including election authorities, to associate a cast ballot with the identity of the voter who cast it) and **receipt-freeness** (the inability of a voter to prove how they voted to a third party, preventing vote-buying and coercion).

### The Relational Linkage in SecureVOTE:
- In `backend/app/models.py`:
  ```python
  class Ballot(Base):
      __tablename__ = "ballots"
      id = Column(String, primary_key=True)
      election_id = Column(String, ForeignKey("elections.id"))
      session_id = Column(String, ForeignKey("voting_sessions.id"), unique=True)  # <--- LINKAGE
      device_id = Column(String, ForeignKey("devices.id"))
      candidate_id = Column(String, ForeignKey("candidates.id"))
      sequence_number = Column(Integer)
      ballot_hash = Column(String(64))
  ```
- **Consequence**: Anyone with read access to the database or raw database backup can join `ballots` with `voting_sessions` and `voters` to determine exactly which candidate a specific elector selected.
- **Why it was retained**: This relational link allows the prototype to demonstrate:
  1. Exact duplicate voting prevention with unique constraints.
  2. End-to-end tracing during security attack simulations (e.g. verifying that a replay attempt was rejected).
  3. Simple, reproducible independent tally reconciliation.

---

## 5. Production-Grade Privacy Mechanisms Required

To transition from an educational research prototype to a production-grade secret-ballot system, the following cryptographic mechanisms would be required:

### 1. Cryptographic Mix-Nets (Verifiable Shuffles)
- Ballots are encrypted with the election public key before submission: $\mathcal{E}_{\text{pk}}(c)$.
- After polls close, a sequence of independent mixing nodes shuffles and re-randomizes the encrypted ballots:
  $$\{\mathcal{E}_{\text{pk}}(c_1), \dots, \mathcal{E}_{\text{pk}}(c_n)\} \xrightarrow{\text{shuffle}} \{\mathcal{E}'_{\text{pk}}(c_{\pi(1)}), \dots, \mathcal{E}'_{\text{pk}}(c_{\pi(n)})\}$$
- Each node produces a zero-knowledge proof of shuffle correctness (e.g. Wikström or Bayer-Groth proofs).
- The final shuffled set is decrypted threshold-wise, completely breaking the association between submission order, device identity, voter session, and cast choice.

### 2. Homomorphic Tallying (e.g., ElectionGuard / Paillier / ElGamal)
- Ballots are encrypted as additively homomorphic ciphertexts:
  $$\mathcal{E}(v_1) \cdot \mathcal{E}(v_2) = \mathcal{E}(v_1 + v_2)$$
- The election authority tallies the encrypted ballots directly without ever decrypting individual ballots:
  $$\mathcal{E}(\text{Total}) = \prod_{i=1}^n \mathcal{E}(v_i)$$
- Only the aggregate sum $\text{Total}$ is decrypted using threshold secret sharing among electoral trustees. Individual ballots remain encrypted forever.

### 3. Physical Air-Gap Isolation (Current Indian EVM Model)
- In the actual Indian Election Commission architecture:
  - The Ballot Unit (BU) and Control Unit (CU) maintain strictly **zero network connectivity**.
  - The physical EVM records total button presses in internal memory counters without recording any timestamp, voter ID, or serial ordering that could correlate with the Presiding Officer's Form 17A register of voters.
  - Physical VVPAT slips drop into a sealed, opaque compartment, physically separating the voter from their cast slip.

---

## 6. Summary of Disclosures

| Aspect | SecureVOTE Prototype | Production Election Requirement |
|---|---|---|
| **Ballot Anonymity** | Relational session linkage (Traceable) | Verifiable mix-net shuffle or homomorphic tallying |
| **Voter Pseudonymization** | Keyed HMAC-SHA256 for RFID | Zero biometric persistence; anonymous credential systems |
| **Receipt-Freeness** | VVPAT visual slip + ballot hash | Physical drop box; zero individual cryptographic receipts |
| **Public Transparency** | Aggregate tallies + hash chain proofs | Shuffled ciphertexts + threshold decryption proofs |
