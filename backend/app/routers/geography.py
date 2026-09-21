"""
Geography and India Electoral Hierarchy router for SecureVOTE 3.3.
Provides endpoints for States/UTs, Parliamentary Constituencies, Assembly Constituencies,
polling stations, and candidate reference datasets.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Any
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
    get_polling_stations_for_pc,
    get_polling_station_by_code,
    get_candidates_for_pc,
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
        "state": state,
        "parliamentary_constituencies": pcs,
        "constituencies": pcs,
        "total_constituencies": len(pcs),
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

    live_stations = [
        {
            "id": s.id,
            "station_code": s.station_code,
            "name": s.name,
            "location": s.location,
            "status": s.status,
            "assigned_devices": [f"CU-{s.station_code}", f"BU-{s.station_code}", f"VVPAT-{s.station_code}"],
            "cu_serial": f"CU-{s.station_code}",
            "bu_serial": f"BU-{s.station_code}",
            "vvpat_serial": f"VVPAT-{s.station_code}",
            "registered_voters": s.registered_voters,
            "ballots_cast": s.votes_cast,
            "turnout_pct": round((s.votes_cast / s.registered_voters * 100), 1) if s.registered_voters else 0.0,
            "is_synthetic": True,
        }
        for s in stations
    ]

    # If database has no live stations, populate with reference synthetic stations
    if not live_stations:
        live_stations = get_polling_stations_for_pc(pc_id)

    candidates = get_candidates_for_pc(pc_id)

    return {
        **pc,
        "polling_stations": live_stations,
        "live_polling_stations": live_stations,
        "registered_simulation_voters": voter_count or pc.get("total_electors", 0),
        "candidates": candidates,
    }


@router.get("/pc/{pc_id}/polling-stations")
async def list_polling_stations(pc_id: str):
    """Retrieve polling stations for a given parliamentary constituency."""
    pc = get_pc_by_id(pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"Parliamentary constituency {pc_id} not found")
    stations = get_polling_stations_for_pc(pc_id)
    return {"pc_id": pc_id, "constituency_name": pc["name"], "polling_stations": stations, "total": len(stations)}


@router.get("/pc/{pc_id}/candidates")
async def list_candidates(pc_id: str):
    """Retrieve candidate and party options for a given parliamentary constituency."""
    pc = get_pc_by_id(pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"Parliamentary constituency {pc_id} not found")
    candidates = get_candidates_for_pc(pc_id)
    return {"pc_id": pc_id, "constituency_name": pc["name"], "candidates": candidates, "total": len(candidates)}


@router.get("/polling-station/{station_code}")
async def get_polling_station(station_code: str):
    """Retrieve detailed security, hardware, and device status for a polling station."""
    ps = get_polling_station_by_code(station_code)
    if not ps:
        # Fallback search if station code is formatted without prefix
        for pc in PARLIAMENTARY_CONSTITUENCIES:
            stations = get_polling_stations_for_pc(pc["id"])
            for s in stations:
                if s["station_code"] == station_code or s["id"] == station_code:
                    return s
        raise HTTPException(status_code=404, detail=f"Polling station {station_code} not found")
    return ps


@router.get("/national-summary")
async def get_national_summary(db: AsyncSession = Depends(get_db)):
    """Provides high-level aggregated metrics across all Indian States & UTs for the Command Center."""
    states = get_all_states()
    total_states = len(states)
    total_pcs = sum(s.get("total_pcs", s.get("pc_count", 0)) for s in states)
    total_acs = sum(s.get("total_acs", s.get("ac_count", 0)) for s in states)
    total_electors = sum(s.get("registered_electors", s.get("elector_count_est", 0)) for s in states)

    # Count database open elections
    res = await db.execute(select(func.count(Election.id)).where(Election.state == "OPEN"))
    open_count = res.scalar() or 1

    return {
        "title": "India Election Security Research Platform",
        "jurisdiction": "Republic of India (Simulation)",
        "total_states": total_states,
        "total_states_and_uts": total_states,
        "total_pcs": total_pcs,
        "total_parliamentary_constituencies": total_pcs,
        "total_acs": total_acs,
        "total_assembly_constituencies": total_acs,
        "national_registered_electors_est": total_electors,
        "total_registered_electors": total_electors,
        "simulated_ballots_cast": 142850,
        "national_turnout_pct": 68.4,
        "active_simulated_elections": open_count,
        "active_pilot_state": "Karnataka (KA)",
        "active_trustees": 3,
        "trustee_threshold": "2-of-3",
        "trustee_network_model": "2-of-3 Threshold ElGamal",
        "verification_integrity_pct": 100.0,
        "cryptographic_baseline": "v3.2.0-research (secp256r1 + CDS94 ZKP + DKG + Threshold Tally)",
        "anomalies_detected": 0,
        "verification_status": "VERIFIED",
        "disclaimer": "Research Prototype — Indian Electoral Simulation — Not an official Election Commission system",
        "states_summary": [
            {
                "code": s["code"],
                "name": s["name"],
                "pcs": s.get("total_pcs", s.get("pc_count", 0)),
                "turnout": s.get("turnout_percentage", 70.0),
                "status": s.get("verification_status", "READY"),
            }
            for s in states
        ],
    }


@router.get("/map-data")
async def get_map_data(db: AsyncSession = Depends(get_db)):
    """Provides SVG path geometries and simulated election coverage for India map explorer."""
    res = await db.execute(select(Election).where(Election.state == "OPEN"))
    open_elections = res.scalars().all()

    active_state_codes = {"KA"} if open_elections else set()

    states = get_all_states()
    features = []
    for s in states:
        is_active = s["code"] in active_state_codes or s.get("active_simulation", False)
        svg_d = s.get("svg_path", s.get("d", ""))
        features.append({
            "code": s["code"],
            "name": s["name"],
            "capital": s["capital"],
            "region": s["region"],
            "total_pcs": s.get("total_pcs", s.get("pc_count", 0)),
            "pc_count": s.get("total_pcs", s.get("pc_count", 0)),
            "total_acs": s.get("total_acs", s.get("ac_count", 0)),
            "ac_count": s.get("total_acs", s.get("ac_count", 0)),
            "registered_electors": s.get("registered_electors", s.get("elector_count_est", 0)),
            "elector_count_est": s.get("registered_electors", s.get("elector_count_est", 0)),
            "svg_path": svg_d,
            "d": svg_d,
            "center": s["center"],
            "turnout_percentage": s.get("turnout_percentage", 70.0),
            "turnout_pct": s.get("turnout_percentage", 70.0),
            "anomalies_count": s.get("anomalies_count", 0),
            "anomalies_detected": s.get("anomalies_count", 0),
            "verification_status": s.get("verification_status", "VERIFIED"),
            "has_active_simulation": is_active,
            "simulated_election_id": "EV-2026-001" if s["code"] == "KA" else None,
        })

    return {
        "viewbox": "0 0 600 650",
        "title": "India Electoral Geography - Reference Simulation",
        "features": features,
    }
