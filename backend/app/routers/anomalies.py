"""
Advisory Anomaly Detection Router for SecureVOTE.

Provides endpoint for retrieving deterministic advisory findings.
Findings are informational only and never block election lifecycle operations.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import AdvisoryFindingsResponse
from app.services.anomaly_detection import AnomalyDetectionService

router = APIRouter(prefix="/api/elections/{election_id}/anomalies", tags=["anomalies"])


@router.get("", response_model=AdvisoryFindingsResponse)
async def get_election_anomalies(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evaluate deterministic anomaly rules against election audit and ballot data.
    Returns advisory findings tagged 'REQUIRES HUMAN REVIEW'.
    Findings are strictly advisory and do NOT block or delay any election operations.
    """
    return await AnomalyDetectionService.analyze_election(db, election_id)
