"""
RFID / Identity Abstraction Service for SecureVOTE.

Provides:
- MockRFIDReader: deterministic simulation of RFID card reads (VALID, INVALID, REVOKED, REPEATED_USE).
- Keyed pseudonymization: HMAC-SHA256(server_secret, uid) - raw UIDs are NEVER logged or persisted.
- Architectural boundary enforcement: RFID AUTHENTICATION != VOTER ELIGIBILITY.
"""

import hashlib
import hmac
import logging
import os
import re
from typing import ClassVar

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device, Election, VotingSession
from app.schemas import RFIDTapResponse, SessionAuthorize
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class MockRFIDReader:
    """
    Mock RFID reader simulating physical contact/contactless smartcard reads.
    Provides deterministic simulation and keyed pseudonymization.
    """

    REVOKED_CARDS: ClassVar[set[str]] = {
        "CARD-REVOKED-01",
        "UID-REVOKED-99",
        "REVOKED_CARD_001",
    }

    @staticmethod
    def get_server_secret() -> str:
        """
        Fetch server-side secret for keyed pseudonymization.
        Fails safely and explicitly if SECUREVOTE_RFID_SECRET is not provisioned.
        """
        secret = os.environ.get("SECUREVOTE_RFID_SECRET")
        if not secret:
            raise RuntimeError(
                "CRITICAL CONFIGURATION ERROR: SECUREVOTE_RFID_SECRET is not configured in the environment. "
                "RFID pseudonymization requires a provisioned server-side secret key."
            )
        return secret

    @classmethod
    def compute_pseudonym(cls, raw_uid: str, secret: str | None = None) -> str:
        """
        Compute keyed pseudonym for a raw UID using HMAC-SHA256.
        MANDATORY AMENDMENT 3: Bare SHA-256(raw_uid) is strictly prohibited.
        """
        effective_secret = secret if secret is not None else cls.get_server_secret()
        return hmac.new(
            effective_secret.encode("utf-8"),
            raw_uid.strip().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def is_valid_format(cls, raw_uid: str) -> bool:
        """
        Validate UID format.
        Accepts hex strings (8 to 32 chars) or standard test card identifiers (e.g. CARD-...).
        Rejects empty strings, strings with invalid control characters, or explicit INVALID prefixes.
        """
        if not raw_uid or not isinstance(raw_uid, str):
            return False
        cleaned = raw_uid.strip()
        if not cleaned or len(cleaned) < 4:
            return False
        if "INVALID" in cleaned.upper() or "MALFORMED" in cleaned.upper():
            return False
        return bool(re.match(r"^[A-Za-z0-9_\-]+$", cleaned))

    @classmethod
    def is_revoked(cls, raw_uid: str) -> bool:
        """Check if card UID is in the revocation list."""
        cleaned = raw_uid.strip().upper()
        if cleaned in cls.REVOKED_CARDS:
            return True
        for revoked in cls.REVOKED_CARDS:
            if revoked.upper() in cleaned:
                return True
        return False

    @classmethod
    def add_revoked_card(cls, card_id: str) -> None:
        """Register a card as revoked."""
        cls.REVOKED_CARDS.add(card_id.strip().upper())


class RFIDService:
    """Service handling RFID card taps and identity abstraction."""

    @staticmethod
    async def process_tap(
        db: AsyncSession,
        raw_uid: str,
        device_id: str,
        election_id: str,
        secret: str | None = None,
    ) -> RFIDTapResponse:
        """
        Process an RFID card tap.

        Strict Privacy:
        The raw_uid is processed only in memory to compute its pseudonym.
        The raw_uid is NEVER logged, persisted in the DB, or included in any audit event.
        """
        # 1. Format validation
        if not MockRFIDReader.is_valid_format(raw_uid):
            logger.warning("RFID tap failed: invalid card format on device %s", device_id)
            return RFIDTapResponse(
                authenticated=False,
                pseudonym="",
                card_status="INVALID",
                device_id=device_id,
                session_id=None,
                notice="RFID AUTHENTICATION != VOTER ELIGIBILITY: Card format invalid or unreadable.",
            )

        # 2. Keyed Pseudonymization (Amendment 3)
        try:
            pseudonym = MockRFIDReader.compute_pseudonym(raw_uid, secret=secret)
        except RuntimeError as e:
            logger.error("RFID tap processing failed due to missing secret: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail="RFID service misconfigured: SECUREVOTE_RFID_SECRET is not configured on the server.",
            ) from e

        # 3. Revocation Check
        if MockRFIDReader.is_revoked(raw_uid):
            logger.warning("RFID tap rejected: revoked card (pseudonym %s...) on device %s", pseudonym[:8], device_id)
            await AuditService.log_event(
                db=db,
                election_id=election_id,
                event_type="RFID_CARD_REJECTED",
                event_data=f'{{"reason": "CARD_REVOKED", "pseudonym": "{pseudonym[:12]}..."}}',
                actor="rfid_reader",
                device_id=device_id,
            )
            return RFIDTapResponse(
                authenticated=False,
                pseudonym=pseudonym,
                card_status="REVOKED",
                device_id=device_id,
                session_id=None,
                notice="RFID AUTHENTICATION != VOTER ELIGIBILITY: Card has been revoked/reported lost.",
            )

        # 4. Check for repeated use (anti-double-voting) in this election
        existing_session = await db.execute(
            select(VotingSession).where(
                VotingSession.election_id == election_id,
                VotingSession.voter_credential == pseudonym,
            )
        )
        if existing_session.scalar_one_or_none():
            logger.warning("RFID tap rejected: repeated card use (pseudonym %s...) in election %s", pseudonym[:8], election_id)
            await AuditService.log_event(
                db=db,
                election_id=election_id,
                event_type="RFID_CARD_REJECTED",
                event_data=f'{{"reason": "REPEATED_USE", "pseudonym": "{pseudonym[:12]}..."}}',
                actor="rfid_reader",
                device_id=device_id,
            )
            return RFIDTapResponse(
                authenticated=True,
                pseudonym=pseudonym,
                card_status="REPEATED_USE",
                device_id=device_id,
                session_id=None,
                notice="RFID AUTHENTICATION != VOTER ELIGIBILITY: Credential already used for voting in this election.",
            )

        # 5. Check election and device state for voter eligibility
        election = await db.get(Election, election_id)
        device = await db.get(Device, device_id)

        if not election or election.state != "OPEN":
            logger.info("RFID tap authenticated for pseudonym %s..., but election %s is not OPEN", pseudonym[:8], election_id)
            return RFIDTapResponse(
                authenticated=True,
                pseudonym=pseudonym,
                card_status="VALID",
                device_id=device_id,
                session_id=None,
                notice="RFID AUTHENTICATION != VOTER ELIGIBILITY: Card authenticated, but election is not OPEN.",
            )

        if not device or device.status != "ACTIVE":
            logger.info("RFID tap authenticated for pseudonym %s..., but device %s is not ACTIVE", pseudonym[:8], device_id)
            return RFIDTapResponse(
                authenticated=True,
                pseudonym=pseudonym,
                card_status="VALID",
                device_id=device_id,
                session_id=None,
                notice=f"RFID AUTHENTICATION != VOTER ELIGIBILITY: Card authenticated, but device {device_id} is not ACTIVE.",
            )

        # 6. Eligible: Create voting session using the pseudonym as voter_credential
        from app.services.vote_service import VoteService
        auth_data = SessionAuthorize(
            voter_credential=pseudonym,
            device_id=device_id,
        )
        session = await VoteService.authorize_session(
            db=db,
            election_id=election_id,
            data=auth_data,
            actor="rfid_reader",
        )

        logger.info("RFID session authorized for pseudonym %s... on device %s", pseudonym[:8], device_id)
        return RFIDTapResponse(
            authenticated=True,
            pseudonym=pseudonym,
            card_status="VALID",
            device_id=device_id,
            session_id=session.session_token,
            notice="RFID AUTHENTICATION != VOTER ELIGIBILITY: Authenticated and session granted for OPEN election.",
        )
