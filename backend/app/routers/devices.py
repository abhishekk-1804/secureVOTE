"""Device management router for SecureVOTE."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user, require_role
from app.schemas import DeviceRegister, DeviceResponse, DeviceStatusUpdate
from app.services.device_service import DeviceService

router = APIRouter(prefix="/api/elections/{election_id}/devices", tags=["devices"])


@router.post("", response_model=DeviceResponse, status_code=201)
async def register_device(
    election_id: str,
    data: DeviceRegister,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    """Register a device for an election. Requires ADMIN role."""
    device = await DeviceService.register_device(
        db, election_id, data, actor=current_user.username
    )
    return device


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    election_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all devices for an election."""
    return await DeviceService.list_devices(db, election_id)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    election_id: str,
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get device details."""
    return await DeviceService.get_device(db, election_id, device_id)


@router.patch("/{device_id}/status", response_model=DeviceResponse)
async def update_device_status(
    election_id: str,
    device_id: str,
    data: DeviceStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    """Update device status. Requires ADMIN role."""
    device = await DeviceService.update_device_status(
        db, election_id, device_id, data, actor=current_user.username
    )
    return device
