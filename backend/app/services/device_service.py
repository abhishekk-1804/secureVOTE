"""
Device management service for SecureVOTE.

Handles device registration, activation, suspension, and revocation.
Devices are simulated EVM units — in a production system they would be
physically authenticated hardware modules.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device, Election
from app.schemas import DeviceRegister, DeviceStatusUpdate
from app.services.audit_service import AuditService
from app.services.websocket_service import websocket_manager



class DeviceService:
    """Device lifecycle management."""

    VALID_STATUS_TRANSITIONS = {
        "REGISTERED": ["ACTIVE"],
        "ACTIVE": ["SUSPENDED", "REVOKED"],
        "SUSPENDED": ["ACTIVE", "REVOKED"],
        # REVOKED is terminal — no transitions out
    }

    @staticmethod
    async def register_device(
        db: AsyncSession,
        election_id: str,
        data: DeviceRegister,
        actor: str,
    ) -> Device:
        """
        Register a new device for an election.

        Election must be in CONFIGURED or LOCKED state (devices can be
        registered before the election opens).
        """
        # Verify election exists and is in a valid state for registration
        result = await db.execute(
            select(Election).where(Election.id == election_id)
        )
        election = result.scalar_one_or_none()
        if not election:
            raise HTTPException(status_code=404, detail=f"Election {election_id} not found.")
        if election.state not in ("CONFIGURED", "LOCKED", "OPEN"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot register devices in {election.state} state.",
            )

        # Check for duplicate device ID
        existing = await db.execute(
            select(Device).where(Device.id == data.id)
        )
        existing_dev = existing.scalar_one_or_none()
        if existing_dev:
            if existing_dev.election_id == election_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Device {data.id} already registered for election {election_id}.",
                )
            else:
                raise HTTPException(
                    status_code=409,
                    detail=f"Device {data.id} already registered in the system.",
                )

        device = Device(
            id=data.id,
            election_id=election_id,
            name=data.name,
            status="REGISTERED",
            device_hash=data.device_hash,
        )
        db.add(device)
        await db.flush()

        await AuditService.log_event(
            db=db,
            election_id=election_id,
            event_type="DEVICE_REGISTERED",
            event_data={"device_id": data.id, "device_name": data.name},
            actor=actor,
            device_id=data.id,
        )

        return device

    @staticmethod
    async def update_device_status(
        db: AsyncSession,
        election_id: str,
        device_id: str,
        data: DeviceStatusUpdate,
        actor: str,
    ) -> Device:
        """
        Update a device's status with strict transition validation.

        Revoked devices cannot be re-activated — this is a one-way
        security action.
        """
        result = await db.execute(
            select(Device).where(
                Device.id == device_id,
                Device.election_id == election_id,
            )
        )
        device = result.scalar_one_or_none()
        if not device:
            raise HTTPException(
                status_code=404,
                detail=f"Device {device_id} not found in election {election_id}.",
            )

        # Idempotent status update check
        if device.status == data.status:
            return device

        # Validate transition
        valid_targets = DeviceService.VALID_STATUS_TRANSITIONS.get(device.status, [])
        if data.status not in valid_targets:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Invalid device status transition: {device.status} → {data.status}. "
                    f"Valid transitions: {valid_targets}"
                ),
            )

        old_status = device.status
        device.status = data.status
        now = datetime.now(timezone.utc)

        if data.status == "ACTIVE":
            device.activated_at = now
        device.last_seen_at = now

        await db.flush()

        await AuditService.log_event(
            db=db,
            election_id=election_id,
            event_type="DEVICE_STATUS_CHANGED",
            event_data={
                "device_id": device_id,
                "old_status": old_status,
                "new_status": data.status,
            },
            actor=actor,
            device_id=device_id,
        )

        await websocket_manager.broadcast(
            election_id=election_id,
            event_type="DEVICE_STATUS_CHANGED",
            data={
                "device_id": device_id,
                "old_status": old_status,
                "new_status": data.status,
            },
        )

        return device


    @staticmethod
    async def get_device(
        db: AsyncSession,
        election_id: str,
        device_id: str,
    ) -> Device:
        """Get a device by ID, scoped to an election."""
        result = await db.execute(
            select(Device).where(
                Device.id == device_id,
                Device.election_id == election_id,
            )
        )
        device = result.scalar_one_or_none()
        if not device:
            raise HTTPException(
                status_code=404,
                detail=f"Device {device_id} not found in election {election_id}.",
            )
        return device

    @staticmethod
    async def list_devices(
        db: AsyncSession,
        election_id: str,
    ) -> list[Device]:
        """List all devices for an election."""
        result = await db.execute(
            select(Device)
            .where(Device.election_id == election_id)
            .order_by(Device.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def validate_device_for_voting(
        db: AsyncSession,
        election_id: str,
        device_id: str,
    ) -> Device:
        """
        Validate that a device can accept votes.

        The device must exist, belong to the election, and be ACTIVE.
        Unknown or revoked devices are rejected per spec Â§12 attack #8.
        """
        result = await db.execute(
            select(Device).where(
                Device.id == device_id,
                Device.election_id == election_id,
            )
        )
        device = result.scalar_one_or_none()
        if not device:
            raise HTTPException(
                status_code=403,
                detail=f"DEVICE REJECTED: Unknown device {device_id}.",
            )
        if device.status != "ACTIVE":
            raise HTTPException(
                status_code=403,
                detail=f"DEVICE REJECTED: Device {device_id} status is {device.status}.",
            )
        return device
