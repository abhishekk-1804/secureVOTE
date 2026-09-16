"""
Pydantic v2 request/response schemas for SecureVOTE API.

All response schemas use from_attributes=True to allow direct construction
from SQLAlchemy model instances.
"""

from datetime import datetime
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
