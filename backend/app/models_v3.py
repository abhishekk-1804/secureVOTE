"""
SecureVOTE 3.0 — v3 Database Models.

These models extend the v2.0 schema with encrypted ballot artifacts,
crypto election metadata, and tally records. They coexist with v2
models — no v2 tables are modified or dropped.

All v3 tables use the prefix `v3_` to prevent namespace collision.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# V3 Crypto Election
# ---------------------------------------------------------------------------

class V3CryptoElection(Base):
    """
    v3 cryptographic metadata for an election.

    Links to an existing v2 Election by election_id.
    Stores the serialized public key, key fingerprint, and v3 status.

    The private key is NEVER stored in the database.
    """

    __tablename__ = "v3_crypto_elections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    election_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    protocol_version: Mapped[str] = mapped_column(String(20), nullable=False, default="SECUREVOTE3")
    public_key_json: Mapped[str] = mapped_column(Text, nullable=False)  # Serialized public key
    key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    key_id: Mapped[str] = mapped_column(String(50), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_ids_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    encrypted_ballots: Mapped[list["V3EncryptedBallot"]] = relationship(
        back_populates="crypto_election", cascade="all, delete-orphan"
    )
    tally: Mapped["V3EncryptedTally | None"] = relationship(
        back_populates="crypto_election", uselist=False, cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# V3 Encrypted Ballot
# ---------------------------------------------------------------------------

class V3EncryptedBallot(Base):
    """
    An encrypted ballot artifact stored in the database.

    Contains the full encrypted ballot artifact JSON plus
    the precomputed commitment and artifact hash for indexing.

    Note: This table is NOT linked to VotingSession by design.
    The v3 layer intentionally breaks the session→ballot link
    to improve privacy properties. The artifact_id is a random
    UUID with no relationship to voter identity.
    """

    __tablename__ = "v3_encrypted_ballots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    crypto_election_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("v3_crypto_elections.id"), nullable=False
    )
    artifact_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    artifact_json: Mapped[str] = mapped_column(Text, nullable=False)  # Full artifact
    commitment: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    crypto_election: Mapped["V3CryptoElection"] = relationship(
        back_populates="encrypted_ballots"
    )


# ---------------------------------------------------------------------------
# V3 Encrypted Tally
# ---------------------------------------------------------------------------

class V3EncryptedTally(Base):
    """
    The aggregated encrypted tally for a v3 election.

    One per crypto election. Contains the encrypted aggregate and
    optionally the decrypted results.
    """

    __tablename__ = "v3_encrypted_tallies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    crypto_election_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("v3_crypto_elections.id"), unique=True, nullable=False
    )
    encrypted_tally_json: Mapped[str] = mapped_column(Text, nullable=False)
    ballot_count: Mapped[int] = mapped_column(Integer, nullable=False)
    commitment: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decrypted_tally_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ENCRYPTED")
    # ENCRYPTED → DECRYPTED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    decrypted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    crypto_election: Mapped["V3CryptoElection"] = relationship(
        back_populates="tally"
    )
