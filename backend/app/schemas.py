"""
Pydantic v2 request/response schemas for SecureVOTE API.

All response schemas use from_attributes=True to allow direct construction
from SQLAlchemy model instances.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# Auth
# ===========================================================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="OBSERVER", pattern="^(ADMIN|AUDITOR|OBSERVER)$")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ===========================================================================
# Election
# ===========================================================================

class ElectionCreate(BaseModel):
    id: str = Field(..., pattern=r"^EV-\d{4}-\d{3}$", examples=["EV-2026-001"])
    name: str = Field(..., min_length=3, max_length=255)
    description: str | None = None


class ElectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None
    state: str
    configuration_hash: str | None
    total_ballots: int
    created_at: datetime
    configured_at: datetime | None
    locked_at: datetime | None
    opened_at: datetime | None
    closed_at: datetime | None
    published_at: datetime | None
    candidates: list["CandidateResponse"] = []
    device_count: int = 0
    ballot_count: int = 0


class ElectionStateChange(BaseModel):
    new_state: str = Field(..., pattern="^(CONFIGURED|LOCKED|OPEN|SUSPENDED|CLOSED|PUBLISHED)$")
    reason: str | None = None


class ElectionListResponse(BaseModel):
    elections: list[ElectionResponse]
    total: int


# ===========================================================================
# Candidate
# ===========================================================================

class CandidateCreate(BaseModel):
    id: str = Field(..., pattern=r"^C\d{3}$", examples=["C001"])
    name: str = Field(..., min_length=1, max_length=255)
    party: str | None = None
    symbol: str | None = None
    position: int = Field(..., ge=1)


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    election_id: str
    name: str
    party: str | None
    symbol: str | None
    position: int
    created_at: datetime


class CandidateBatchCreate(BaseModel):
    candidates: list[CandidateCreate] = Field(..., min_length=1)


# ===========================================================================
# Device
# ===========================================================================

class DeviceRegister(BaseModel):
    id: str = Field(..., pattern=r"^EVM-\d{3}$", examples=["EVM-001"])
    name: str = Field(..., min_length=1, max_length=255)
    device_hash: str | None = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    election_id: str
    name: str
    status: str
    device_hash: str | None
    last_sequence_number: int
    registered_at: datetime
    activated_at: datetime | None
    last_seen_at: datetime | None
    total_votes_cast: int


class DeviceStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(ACTIVE|SUSPENDED|REVOKED)$")


# ===========================================================================
# Voting Session
# ===========================================================================

class SessionAuthorize(BaseModel):
    voter_credential: str = Field(..., min_length=1, max_length=100)
    device_id: str = Field(..., pattern=r"^EVM-\d{3}$")


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    election_id: str
    device_id: str
    session_token: str
    voter_credential: str
    status: str
    authorized_at: datetime
    voted_at: datetime | None


# ===========================================================================
# Vote / Ballot
# ===========================================================================

class VoteCast(BaseModel):
    session_token: str = Field(..., min_length=1)
    candidate_id: str = Field(..., pattern=r"^C\d{3}$")
    device_id: str = Field(..., pattern=r"^EVM-\d{3}$")
    sequence_number: int = Field(..., ge=1)


class VoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ballot_id: str
    election_id: str
    candidate_id: str
    device_id: str
    sequence_number: int
    ballot_hash: str
    recorded_at: datetime


# ===========================================================================
# Audit
# ===========================================================================

class AuditEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    election_id: str
    event_type: str
    event_data: str | None
    actor: str | None
    device_id: str | None
    sequence_number: int
    timestamp: datetime
    previous_hash: str | None
    entry_hash: str


class AuditLogResponse(BaseModel):
    entries: list[AuditEntryResponse]
    total: int
    chain_status: str


class AuditVerificationResponse(BaseModel):
    is_intact: bool
    total_entries: int
    verified_entries: int
    first_broken_index: int | None = None
    first_broken_sequence: int | None = None
    details: str


# ===========================================================================
# Results
# ===========================================================================

class CandidateResult(BaseModel):
    candidate_id: str
    candidate_name: str
    party: str | None
    symbol: str | None
    vote_count: int
    percentage: float


class DeviceResult(BaseModel):
    device_id: str
    device_name: str
    ballot_count: int


class ReconciliationResult(BaseModel):
    total_ballots: int
    sum_candidate_totals: int
    sum_device_totals: int
    is_exact_match: bool
    status: str


class ResultManifestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    election_id: str
    total_ballots: int
    candidate_totals: str  # JSON string
    device_totals: str  # JSON string
    reconciliation_status: str
    audit_chain_status: str
    configuration_hash: str
    manifest_hash: str
    digital_signature: str | None
    generated_at: datetime
    verified_at: datetime | None
    verified_by: str | None
    candidate_results: list[CandidateResult] = []
    device_results: list[DeviceResult] = []
    reconciliation: ReconciliationResult | None = None


# ===========================================================================
# Verification
# ===========================================================================

class VerificationRequest(BaseModel):
    election_id: str


class VerificationResponse(BaseModel):
    election_id: str
    config_hash_valid: bool
    audit_chain_intact: bool
    reconciliation_passed: bool
    tally_independently_verified: bool
    overall_status: str  # PASSED or FAILED
    manifest: ResultManifestResponse | None = None
    details: list[str] = []


# ===========================================================================
# General
# ===========================================================================

class ErrorResponse(BaseModel):
    detail: str


class SuccessResponse(BaseModel):
    message: str


# ===========================================================================
# WebSocket Ticket
# ===========================================================================

class WsTicketRequest(BaseModel):
    election_id: str | None = None


class WsTicketResponse(BaseModel):
    ticket: str
    expires_in: int = 60
    election_id: str | None = None



# ===========================================================================
# Machine-Verifiable Export
# ===========================================================================

class BallotExportItem(BaseModel):
    id: str
    session_id: str
    device_id: str
    candidate_id: str
    sequence_number: int
    ballot_hash: str
    recorded_at: str


class AuditExportItem(BaseModel):
    id: int | str
    sequence_number: int
    event_type: str
    event_data: str | None
    actor: str | None
    device_id: str | None
    timestamp: str
    previous_hash: str | None
    entry_hash: str



class DeviceExportItem(BaseModel):
    id: str
    name: str
    status: str
    last_sequence_number: int
    total_votes_cast: int
    registered_at: str
    activated_at: str | None
    last_seen_at: str | None


class CandidateExportItem(BaseModel):
    id: str
    name: str
    party: str | None
    symbol: str | None
    position: int


class ElectionExportMeta(BaseModel):
    id: str
    name: str
    description: str | None
    state: str
    configuration_hash: str | None
    total_ballots: int
    created_at: str
    locked_at: str | None
    opened_at: str | None
    closed_at: str | None
    published_at: str | None


class ElectionExportResponse(BaseModel):
    export_version: str = "1.0.0"
    exported_at: str
    election: ElectionExportMeta
    candidates: list[CandidateExportItem]
    devices: list[DeviceExportItem]
    ballots: list[BallotExportItem]
    audit_log: list[AuditExportItem]
    manifest: dict | None = None
    export_hash: str


# ===========================================================================
# Phase 5: Cryptographic Signing
# ===========================================================================

class PublicKeyInfoResponse(BaseModel):
    configured: bool
    algorithm: str = "Ed25519"
    key_id: str | None = None
    public_key: str | None = None
    fingerprint: str | None = None


class VerifySignatureRequest(BaseModel):
    payload: dict[str, Any]
    signature: str
    public_key: str | None = None


class VerifySignatureResponse(BaseModel):
    valid: bool
    algorithm: str = "Ed25519"
    details: str
    key_id: str | None = None
    fingerprint: str | None = None


class SignedManifestResponse(BaseModel):
    manifest_id: str
    election_id: str
    manifest_hash: str
    digital_signature: dict[str, Any]
    signed_at: datetime
    signed_by: str


# ===========================================================================
# Phase 5: External Audit-Root Anchoring
# ===========================================================================

class AnchorRequest(BaseModel):
    provider_type: str = "LOCAL"  # LOCAL or EXTERNAL


class AnchorReceiptResponse(BaseModel):
    anchor_id: str
    election_id: str
    root_hash: str
    provider_type: str  # LOCAL ANCHOR, EXTERNAL ANCHOR, NOT CONFIGURED, ENVIRONMENT-BLOCKED
    anchor_reference: str
    status: str  # LOCAL ANCHOR, EXTERNAL ANCHOR, NOT ANCHORED, ANCHOR VERIFICATION FAILED
    anchored_at: datetime
    metadata: dict[str, Any] = {}


class VerifyAnchorResponse(BaseModel):
    verified: bool
    status: str
    provider_type: str
    anchor_reference: str
    root_hash: str
    details: str


# ===========================================================================
# Phase 5: Advisory Anomaly Detection
# ===========================================================================

class AdvisoryFinding(BaseModel):
    finding_id: str
    election_id: str
    device_id: str | None = None
    rule_id: str
    category: str
    severity: str  # LOW, MEDIUM, HIGH
    evidence: dict[str, Any]
    timestamp: datetime
    advisory_explanation: str
    requires_human_review: bool = True


class AdvisoryFindingsResponse(BaseModel):
    election_id: str
    findings_count: int
    findings: list[AdvisoryFinding]
    status: str = "ADVISORY_ONLY_DOES_NOT_BLOCK_LIFECYCLE"


# ===========================================================================
# Phase 5: RFID / Identity Abstraction
# ===========================================================================

class RFIDTapRequest(BaseModel):
    raw_uid: str
    device_id: str
    election_id: str


class RFIDTapResponse(BaseModel):
    authenticated: bool
    pseudonym: str
    card_status: str  # VALID, INVALID, REVOKED, REPEATED_USE
    device_id: str
    session_id: str | None = None
    notice: str = "RFID AUTHENTICATION != VOTER ELIGIBILITY"


# ===========================================================================
# Voter schemas
# ===========================================================================

class VoterCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    date_of_birth: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    constituency: str = Field(..., min_length=2, max_length=100)

class VoterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    election_id: str
    voter_id_number: str
    name: str
    date_of_birth: str
    constituency: str
    polling_station_id: str | None
    eligibility_status: str
    registration_status: str
    has_voted: bool
    registered_at: datetime

class EligibilityCheckRequest(BaseModel):
    name: str = Field(..., min_length=2)
    date_of_birth: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    constituency: str = Field(..., min_length=2)

class EligibilityCheckResponse(BaseModel):
    status: str  # ELIGIBLE, NOT_ELIGIBLE, NEEDS_REVIEW
    reasons: list[str]
    voter_id: str | None = None
    notice: str = "SIMULATED ELIGIBILITY CHECK - NOT A REAL GOVERNMENT SERVICE"

# ===========================================================================
# PollingStation schemas
# ===========================================================================

class PollingStationCreate(BaseModel):
    station_code: str = Field(..., pattern=r"^PS-\d{3}$")
    name: str = Field(..., min_length=3, max_length=255)
    constituency: str = Field(..., min_length=2, max_length=100)
    location: str = Field(..., min_length=3, max_length=255)
    officer_name: str | None = None

class PollingStationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    election_id: str
    station_code: str
    name: str
    constituency: str
    location: str
    assigned_devices: int
    registered_voters: int
    votes_cast: int
    status: str
    officer_name: str | None
    created_at: datetime

# ===========================================================================
# Complaint schemas
# ===========================================================================

class ComplaintCreate(BaseModel):
    election_id: str | None = None
    category: str = Field(..., pattern="^(VOTER_REGISTRATION|POLLING_STATION|EVM|VOTING_ISSUE|ACCESSIBILITY|ELECTION_PROCESS|CANDIDATE_PARTY|TECHNICAL|OTHER)$")
    description: str = Field(..., min_length=10, max_length=2000)
    complainant_name: str = Field(..., min_length=2, max_length=255)
    complainant_contact: str | None = None

class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    election_id: str | None
    reference_number: str
    category: str
    description: str
    complainant_name: str
    complainant_contact: str | None
    status: str
    assigned_officer: str | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime

class ComplaintStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(RECEIVED|ASSIGNED|UNDER_REVIEW|RESOLVED|CLOSED)$")
    assigned_officer: str | None = None
    resolution_notes: str | None = None

# ===========================================================================
# Simulation schemas
# ===========================================================================

class SimulationRequest(BaseModel):
    preset: str = Field(default="DEMO_1000", pattern="^(DEMO_1000|DEMO_10000|DEMO_100000)$")
    election_name: str = Field(default="SecureVOTE Demo Election 2026")

class SimulationResponse(BaseModel):
    election_id: str
    preset: str
    ballots_generated: int
    devices_created: int
    polling_stations_created: int
    voters_registered: int
    candidates_created: int
    audit_entries: int
    duration_seconds: float
    status: str

# ===========================================================================
# Transparency schemas
# ===========================================================================

class TransparencyOverview(BaseModel):
    election_id: str
    election_name: str
    state: str
    total_ballots: int
    device_count: int
    polling_station_count: int
    candidate_count: int
    registered_voters: int
    turnout_percentage: float
    audit_chain_status: str
    reconciliation_status: str
    manifest_status: str
    notice: str = "Aggregate data only - no individual voter information disclosed"
