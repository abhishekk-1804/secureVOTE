"""
Pydantic Schemas for SecureVOTE 3.0 Cryptographic API.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class V3InitElectionRequest(BaseModel):
    election_id: str = Field(..., min_length=3, max_length=50)
    candidates: list[str] = Field(..., min_length=2, max_length=50)


class V3InitElectionResponse(BaseModel):
    election_id: str
    protocol_version: str
    key_fingerprint: str
    public_key: dict[str, Any]
    candidate_count: int
    candidates: list[str]
    status: str


class V3EncryptBallotRequest(BaseModel):
    election_id: str
    candidate_index: int = Field(..., ge=0)


class V3CastBallotRequest(BaseModel):
    election_id: str
    ballot_artifact: dict[str, Any]


class V3CastBallotResponse(BaseModel):
    status: str
    artifact_id: str
    commitment: str
    artifact_hash: str
    ballot_count: int


class V3AggregateTallyRequest(BaseModel):
    election_id: str


class V3DecryptTallyRequest(BaseModel):
    election_id: str
    private_key_scalar_hex: Optional[str] = None  # Optional: use server in-memory research key if omitted


class V3TallyResponse(BaseModel):
    election_id: str
    protocol_version: str
    ballot_count: int
    status: str
    commitment: str
    artifact_hash: str
    encrypted_tally: dict[str, Any]
    decrypted_tally: Optional[dict[str, Any]] = None


class V3VerifyRequest(BaseModel):
    package: dict[str, Any]


class V3VerifyResponse(BaseModel):
    verified: bool
    election_id: str
    ballot_count: int
    checkpoints_passed: int
    checkpoints_total: int
    checkpoints: list[dict[str, Any]]
