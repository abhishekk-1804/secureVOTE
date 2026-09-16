"""
RFID router for SecureVOTE.

Provides endpoints for:
- Simulating RFID card taps with keyed pseudonymization
- Architectural boundary: RFID AUTHENTICATION != VOTER ELIGIBILITY
- Demo card profiles for UI and testing
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import RFIDTapRequest, RFIDTapResponse
from app.services.rfid_service import MockRFIDReader, RFIDService

router = APIRouter(prefix="/api/rfid", tags=["rfid"])


@router.post("/tap", response_model=RFIDTapResponse)
async def rfid_tap(
    request: RFIDTapRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process an RFID card tap.

    Computes a keyed pseudonym (HMAC-SHA256) for the raw UID.
    The raw UID is NEVER logged, persisted, or returned.

    Architectural Boundary:
    Successful RFID authentication does NOT grant a ballot or voting session
    unless the election is OPEN, device is ACTIVE, and voter has not already voted.
    """
    return await RFIDService.process_tap(
        db=db,
        raw_uid=request.raw_uid,
        device_id=request.device_id,
        election_id=request.election_id,
    )


@router.get("/demo-cards")
async def get_demo_cards():
    """
    List sample simulated card profiles for dashboard testing and demonstrations.
    Does not expose private keys or raw UIDs of real credentials.
    """
    return {
        "cards": [
            {
                "card_id": "CARD-VALID-01",
                "label": "Eligible Voter Card 1",
                "expected_status": "VALID",
                "description": "Standard voter credential. Authenticates and grants session if election is OPEN.",
            },
            {
                "card_id": "CARD-VALID-02",
                "label": "Eligible Voter Card 2",
                "expected_status": "VALID",
                "description": "Second voter credential for testing multi-voter flows.",
            },
            {
                "card_id": "CARD-REVOKED-01",
                "label": "Revoked / Lost Card",
                "expected_status": "REVOKED",
                "description": "Reported lost or compromised card. Rejected at authentication layer.",
            },
            {
                "card_id": "CARD-INVALID-99",
                "label": "Malformed / Invalid Card",
                "expected_status": "INVALID",
                "description": "Unrecognized or corrupted chip read. Rejected at format validation.",
            },
        ],
        "pseudonymization_algorithm": "HMAC-SHA256",
        "boundary_notice": "RFID AUTHENTICATION != VOTER ELIGIBILITY",
    }
