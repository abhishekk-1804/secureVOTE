"""
Geography and India Electoral Hierarchy router for SecureVOTE 2.0.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import PollingStation, Election, Voter
from app.geography import (
    INDIAN_STATES,
    PARLIAMENTARY_CONSTITUENCIES,
    get_all_states,
    get_state_by_code,
    get_pcs_for_state,
    get_pc_by_id,
)

router = APIRouter(prefix="/api/geography", tags=["Geography"])


@router.get("/states")
async def list_states():
    """List Indian States & UTs with PC/AC representation metadata."""
    return {"states": get_all_states(), "total": len(INDIAN_STATES)}


@router.get("/states/{state_code}")
async def get_state_details(state_code: str):
    """Get state details and associated parliamentary constituencies."""
    state = get_state_by_code(state_code)
    if not state:
        raise HTTPException(status_code=404, detail=f"State code {state_code} not found")
    pcs = get_pcs_for_state(state_code)
    return {
        **state,
        "parliamentary_constituencies": pcs,
    }


@router.get("/states/{state_code}/constituencies")
async def get_state_constituencies(state_code: str):
    """List parliamentary constituencies for a specific state."""
    state = get_state_by_code(state_code)
    if not state:
        raise HTTPException(status_code=404, detail=f"State code {state_code} not found")
    pcs = get_pcs_for_state(state_code)
    return {"state_code": state_code.upper(), "constituencies": pcs, "total": len(pcs)}


@router.get("/pc/{pc_id}")
async def get_parliamentary_constituency(pc_id: str, db: AsyncSession = Depends(get_db)):
    """Get parliamentary constituency details, assembly constituencies, and active polling stations."""
    pc = get_pc_by_id(pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"Parliamentary constituency {pc_id} not found")

    # Fetch associated live polling stations in database
    ps_res = await db.execute(
        select(PollingStation).where(PollingStation.constituency == pc["name"])
    )
    stations = ps_res.scalars().all()

    voter_count = await db.scalar(
        select(func.count(Voter.id)).where(Voter.constituency == pc["name"])
    )

    return {
        **pc,
        "live_polling_stations": [
            {
                "id": s.id,
                "station_code": s.station_code,
                "name": s.name,
                "location": s.location,
                "status": s.status,
                "assigned_devices": s.assigned_devices,
                "registered_voters": s.registered_voters,
            }
            for s in stations
        ],
        "registered_simulation_voters": voter_count or 0,
    }


@router.get("/map-data")
async def get_map_data(db: AsyncSession = Depends(get_db)):
    """Provides SVG path geometries and simulated election coverage for India map explorer."""
    # Count open elections
    res = await db.execute(select(Election).where(Election.state == "OPEN"))
    open_elections = res.scalars().all()

    active_state_codes = {"KA"} if open_elections else set()

    features = []
    for s in INDIAN_STATES:
        is_active = s["code"] in active_state_codes or s["active_simulation"]
        features.append({
            "code": s["code"],
            "name": s["name"],
            "capital": s["capital"],
            "region": s["region"],
            "total_pcs": s["total_pcs"],
            "total_acs": s["total_acs"],
            "registered_electors": s["registered_electors"],
            "svg_path": s["svg_path"],
            "center": s["center"],
            "has_active_simulation": is_active,
            "simulated_election_id": "EV-2026-001" if s["code"] == "KA" else None,
        })

    return {
        "viewbox": "0 0 600 650",
        "title": "India Electoral Geography - Reference Simulation",
        "features": features,
    }
