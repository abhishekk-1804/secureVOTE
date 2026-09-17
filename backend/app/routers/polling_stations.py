from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import PollingStation, Election, User
from app.schemas import PollingStationCreate, PollingStationResponse
from app.routers.auth import get_current_user
from pydantic import BaseModel

class PollingStationStatusUpdate(BaseModel):
    status: str

router = APIRouter(prefix="/api/elections/{election_id}/polling-stations", tags=["Polling Stations"])

def check_admin(user: User):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough permissions")

@router.post("", response_model=PollingStationResponse, status_code=201)
async def create_polling_station(election_id: str, station_data: PollingStationCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin(current_user)
    election = await db.get(Election, election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    new_station = PollingStation(
        election_id=election_id,
        station_code=station_data.station_code,
        name=station_data.name,
        constituency=station_data.constituency,
        location=station_data.location,
        officer_name=station_data.officer_name,
        status="SETUP"
    )
    db.add(new_station)
    await db.commit()
    await db.refresh(new_station)
    return new_station

@router.get("", response_model=List[PollingStationResponse])
async def list_polling_stations(election_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PollingStation).where(PollingStation.election_id == election_id))
    return result.scalars().all()

@router.get("/{station_id}", response_model=PollingStationResponse)
async def get_polling_station(election_id: str, station_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PollingStation).where(PollingStation.election_id == election_id, PollingStation.id == station_id))
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(status_code=404, detail="Polling station not found")
    return station

@router.patch("/{station_id}/status", response_model=PollingStationResponse)
async def update_polling_station_status(election_id: str, station_id: str, status_data: PollingStationStatusUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin(current_user)
    result = await db.execute(select(PollingStation).where(PollingStation.election_id == election_id, PollingStation.id == station_id))
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(status_code=404, detail="Polling station not found")

    station.status = status_data.status
    await db.commit()
    await db.refresh(station)
    return station
