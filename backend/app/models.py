"""
SQLAlchemy ORM models for SecureVOTE.

This is a research-oriented prototype. The database is not assumed immutable —
integrity comes from append-only audit events + hash chaining + independent
verification, not from row-level protection alone.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# User (JWT / RBAC)
# ---------------------------------------------------------------------------

class User(Base):
    """
    Application user for simulated credential/session authorization.

    Roles: ADMIN, AUDITOR, OBSERVER.
    This is NOT a voter record — voters are represented by VotingSession.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="OBSERVER")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------------------------------------------------------------------------
# Election
# ---------------------------------------------------------------------------

class Election(Base):
    """
    An election lifecycle record.

    States: CREATED → CONFIGURED → LOCKED → OPEN → SUSPENDED → CLOSED → PUBLISHED
    """

    __tablename__ = "elections"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="CREATED")
    configuration_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_ballots: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    configured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="election", cascade="all, delete-orphan", lazy="selectin")
    devices: Mapped[list["Device"]] = relationship(back_populates="election", cascade="all, delete-orphan", lazy="selectin")
    ballots: Mapped[list["Ballot"]] = relationship(back_populates="election", cascade="all, delete-orphan")
    sessions: Mapped[list["VotingSession"]] = relationship(back_populates="election", cascade="all, delete-orphan")
    audit_entries: Mapped[list["AuditEntry"]] = relationship(back_populates="election", cascade="all, delete-orphan")
    result_manifest: Mapped["ResultManifest | None"] = relationship(back_populates="election", uselist=False, cascade="all, delete-orphan")

    @property
    def device_count(self) -> int:
        return len(self.devices) if "devices" in self.__dict__ and self.devices is not None else 0

    @property
    def ballot_count(self) -> int:
        return self.total_ballots


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------

class Candidate(Base):
    """A candidate in an election."""

    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("election_id", "position", name="uq_candidate_position"),
    )

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    election_id: Mapped[str] = mapped_column(String(50), ForeignKey("elections.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    party: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(10), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    election: Mapped["Election"] = relationship(back_populates="candidates")


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------

class Device(Base):
    """
    A registered voting device (EVM unit).

    Status: REGISTERED → ACTIVE → SUSPENDED / REVOKED
    Tracks last_sequence_number for replay protection.
    """

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    election_id: Mapped[str] = mapped_column(String(50), ForeignKey("elections.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="REGISTERED")
    device_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_sequence_number: Mapped[int] = mapped_column(Integer, default=0)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_votes_cast: Mapped[int] = mapped_column(Integer, default=0)

    election: Mapped["Election"] = relationship(back_populates="devices")
    ballots: Mapped[list["Ballot"]] = relationship(back_populates="device")
    sessions: Mapped[list["VotingSession"]] = relationship(back_populates="device")


# ---------------------------------------------------------------------------
# VotingSession
# ---------------------------------------------------------------------------

class VotingSession(Base):
    """
    A simulated voting session / credential authorization.

    Each voter_credential gets exactly one session per election.
    This is a simulated credential — not a real voter identity mechanism.
    Status: AUTHORIZED → VOTED / EXPIRED / REVOKED
    """

    __tablename__ = "voting_sessions"
    __table_args__ = (
        UniqueConstraint("election_id", "voter_credential", name="uq_voter_credential"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    election_id: Mapped[str] = mapped_column(String(50), ForeignKey("elections.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(20), ForeignKey("devices.id"), nullable=False)
    session_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    voter_credential: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="AUTHORIZED")
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    voted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    election: Mapped["Election"] = relationship(back_populates="sessions")
    device: Mapped["Device"] = relationship(back_populates="sessions")
    ballot: Mapped["Ballot | None"] = relationship(back_populates="session", uselist=False)


# ---------------------------------------------------------------------------
# Ballot
# ---------------------------------------------------------------------------

class Ballot(Base):
    """
    A recorded ballot (vote record).

    Linked to a session (one ballot per session) and a device.
    sequence_number is monotonically increasing per device for replay protection.

    Note: voter anonymity is NOT preserved in this prototype — the session
    linkage exists for educational demonstration of audit trails.
    """

    __tablename__ = "ballots"
    __table_args__ = (
        UniqueConstraint("device_id", "sequence_number", name="uq_device_sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    election_id: Mapped[str] = mapped_column(String(50), ForeignKey("elections.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("voting_sessions.id"), unique=True, nullable=False)
    device_id: Mapped[str] = mapped_column(String(20), ForeignKey("devices.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(10), ForeignKey("candidates.id"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ballot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    election: Mapped["Election"] = relationship(back_populates="ballots")
    session: Mapped["VotingSession"] = relationship(back_populates="ballot")
    device: Mapped["Device"] = relationship(back_populates="ballots")
    candidate: Mapped["Candidate"] = relationship()


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------

class AuditEntry(Base):
    """
    Append-only, hash-chained audit log entry.

    Each entry's hash includes the previous entry's hash, forming a
    tamper-evident chain. Any modification to a historical entry causes
    all subsequent hashes to mismatch.

    The chain is verified by independently recomputing hashes from raw
    records — never by reading a precomputed flag.
    """

    __tablename__ = "audit_entries"
    __table_args__ = (
        Index("ix_audit_election_seq", "election_id", "sequence_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    election_id: Mapped[str] = mapped_column(String(50), ForeignKey("elections.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    election: Mapped["Election"] = relationship(back_populates="audit_entries")


# ---------------------------------------------------------------------------
# ResultManifest
# ---------------------------------------------------------------------------

class ResultManifest(Base):
    """
    Signed result manifest for a completed election.

    Contains independently verifiable tallies, reconciliation status, and
    audit chain status. The manifest_hash is digitally signed backend-side
    (per spec §9 — Arduino Uno does not perform asymmetric signing).
    """

    __tablename__ = "result_manifests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    election_id: Mapped[str] = mapped_column(String(50), ForeignKey("elections.id"), unique=True, nullable=False)
    total_ballots: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_totals: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    device_totals: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    reconciliation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    audit_chain_status: Mapped[str] = mapped_column(String(20), nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    digital_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    election: Mapped["Election"] = relationship(back_populates="result_manifest")


# ---------------------------------------------------------------------------
# Voter (synthetic/demo)
# ---------------------------------------------------------------------------

class Voter(Base):
    __tablename__ = "voters"
    __table_args__ = (
        UniqueConstraint("election_id", "voter_id_number", name="uq_voter_election_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    election_id: Mapped[str] = mapped_column(String(50), ForeignKey("elections.id"), nullable=False)
    voter_id_number: Mapped[str] = mapped_column(String(20), nullable=False)  # Synthetic ID like "VTR-00001"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    constituency: Mapped[str] = mapped_column(String(100), nullable=False)
    polling_station_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    eligibility_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")  # ELIGIBLE, NOT_ELIGIBLE, PENDING, NEEDS_REVIEW
    registration_status: Mapped[str] = mapped_column(String(20), nullable=False, default="REGISTERED")  # REGISTERED, VERIFIED, REJECTED
    has_voted: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

# ---------------------------------------------------------------------------
# PollingStation
# ---------------------------------------------------------------------------

class PollingStation(Base):
    __tablename__ = "polling_stations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    election_id: Mapped[str] = mapped_column(String(50), ForeignKey("elections.id"), nullable=False)
    station_code: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "PS-001"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    constituency: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_devices: Mapped[int] = mapped_column(Integer, default=0)
    registered_voters: Mapped[int] = mapped_column(Integer, default=0)
    votes_cast: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SETUP")  # SETUP, READY, POLLING, CLOSED
    officer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

# ---------------------------------------------------------------------------
# Complaint
# ---------------------------------------------------------------------------

class Complaint(Base):
    __tablename__ = "complaints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    election_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("elections.id"), nullable=True)
    reference_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # e.g. "GRV-2026-00001"
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # VOTER_REGISTRATION, POLLING_STATION, EVM, VOTING_ISSUE, ACCESSIBILITY, ELECTION_PROCESS, CANDIDATE_PARTY, TECHNICAL, OTHER
    description: Mapped[str] = mapped_column(Text, nullable=False)
    complainant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    complainant_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUBMITTED")  # SUBMITTED, RECEIVED, ASSIGNED, UNDER_REVIEW, RESOLVED, CLOSED
    assigned_officer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ---------------------------------------------------------------------------
# SecureVOTE 3.0 Research Models Import
# ---------------------------------------------------------------------------
from app.models_v3 import V3CryptoElection, V3EncryptedBallot, V3EncryptedTally  # noqa: E402, F401
