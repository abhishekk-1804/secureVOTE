"""
Indian Electoral Geography — REFERENCE / SIMULATION DATA for SecureVOTE 3.0.

IMPORTANT DISCLAIMER:
All data in this module — including state/UT names, PC/AC counts, registered elector
estimates, polling-station distributions, and SVG map geometry — is REFERENCE /
SIMULATION DATA compiled for academic, research, and demonstration purposes only.

This data is NOT:
- An official electoral roll.
- An official Election Commission of India (ECI) database.
- Statutory or certified election data.
- A live or real-time data source.

Elector count values are approximate reference figures based on publicly available
historical election-commission publications and are subject to change. Do not rely
on these values for any legal or operational election purpose.

Provides structured reference geography representing:
- States and Union Territories (Codes, Names, PC/AC counts, Capitals)
- Parliamentary Constituencies (PCs)
- Assembly Constituencies (ACs)
- Polling Stations distribution (approximate/reference)
- Normalized SVG path geometry for interactive map visualization
"""

from typing import Any

INDIAN_STATES: list[dict[str, Any]] = [
    {
        "code": "KA",
        "name": "Karnataka",
        "capital": "Bengaluru",
        "region": "South",
        "total_pcs": 28,
        "total_acs": 224,
        "registered_electors": 54289000,
        "active_simulation": True,
        "svg_path": "M 220 380 L 260 370 L 280 410 L 260 480 L 230 470 L 210 420 Z",
        "center": [15.3173, 75.7139],
    },
    {
        "code": "MH",
        "name": "Maharashtra",
        "capital": "Mumbai",
        "region": "West",
        "total_pcs": 48,
        "total_acs": 288,
        "registered_electors": 92430000,
        "active_simulation": False,
        "svg_path": "M 180 300 L 280 290 L 320 340 L 260 370 L 200 360 L 170 330 Z",
        "center": [19.7515, 75.7139],
    },
    {
        "code": "DL",
        "name": "NCT of Delhi",
        "capital": "New Delhi",
        "region": "North",
        "total_pcs": 7,
        "total_acs": 70,
        "registered_electors": 15200000,
        "active_simulation": False,
        "svg_path": "M 230 180 L 245 180 L 245 195 L 230 195 Z",
        "center": [28.6139, 77.2090],
    },
    {
        "code": "TN",
        "name": "Tamil Nadu",
        "capital": "Chennai",
        "region": "South",
        "total_pcs": 39,
        "total_acs": 234,
        "registered_electors": 62300000,
        "active_simulation": False,
        "svg_path": "M 240 480 L 290 470 L 280 540 L 250 550 L 230 500 Z",
        "center": [11.1271, 78.6569],
    },
    {
        "code": "UP",
        "name": "Uttar Pradesh",
        "capital": "Lucknow",
        "region": "North",
        "total_pcs": 80,
        "total_acs": 403,
        "registered_electors": 153000000,
        "active_simulation": False,
        "svg_path": "M 260 170 L 380 180 L 360 250 L 280 250 L 250 200 Z",
        "center": [26.8467, 80.9462],
    },
    {
        "code": "WB",
        "name": "West Bengal",
        "capital": "Kolkata",
        "region": "East",
        "total_pcs": 42,
        "total_acs": 294,
        "registered_electors": 75800000,
        "active_simulation": False,
        "svg_path": "M 420 220 L 450 220 L 440 310 L 410 300 Z",
        "center": [22.9868, 87.8550],
    },
    {
        "code": "TG",
        "name": "Telangana",
        "capital": "Hyderabad",
        "region": "South",
        "total_pcs": 17,
        "total_acs": 119,
        "registered_electors": 31700000,
        "active_simulation": False,
        "svg_path": "M 270 340 L 330 340 L 320 400 L 270 390 Z",
        "center": [18.1124, 79.0193],
    },
    {
        "code": "GJ",
        "name": "Gujarat",
        "capital": "Gandhinagar",
        "region": "West",
        "total_pcs": 26,
        "total_acs": 182,
        "registered_electors": 49400000,
        "active_simulation": False,
        "svg_path": "M 130 240 L 190 240 L 180 310 L 120 280 Z",
        "center": [22.2587, 71.1924],
    },
]

PARLIAMENTARY_CONSTITUENCIES: list[dict[str, Any]] = [
    # Karnataka PCs
    {
        "id": "KA-PC-24",
        "pc_number": 24,
        "name": "Bengaluru Central",
        "state_code": "KA",
        "reservation": "GEN",
        "total_electors": 1950000,
        "assembly_constituencies": [
            {"ac_number": 160, "name": "Sarvagnanagar", "reservation": "GEN", "registered_voters": 248000},
            {"ac_number": 161, "name": "C.V. Raman Nagar", "reservation": "SC", "registered_voters": 235000},
            {"ac_number": 162, "name": "Shivajinagar", "reservation": "GEN", "registered_voters": 210000},
            {"ac_number": 163, "name": "Shanti Nagar", "reservation": "GEN", "registered_voters": 222000},
            {"ac_number": 164, "name": "Gandhi Nagar", "reservation": "GEN", "registered_voters": 215000},
            {"ac_number": 165, "name": "Rajaji Nagar", "reservation": "GEN", "registered_voters": 228000},
            {"ac_number": 166, "name": "Govindraj Nagar", "reservation": "GEN", "registered_voters": 272000},
            {"ac_number": 167, "name": "Vijay Nagar", "reservation": "GEN", "registered_voters": 320000},
        ],
    },
    {
        "id": "KA-PC-25",
        "pc_number": 25,
        "name": "Bengaluru South",
        "state_code": "KA",
        "reservation": "GEN",
        "total_electors": 2200000,
        "assembly_constituencies": [
            {"ac_number": 170, "name": "Basavanagudi", "reservation": "GEN", "registered_voters": 230000},
            {"ac_number": 171, "name": "Padmanaba Nagar", "reservation": "GEN", "registered_voters": 265000},
            {"ac_number": 172, "name": "BTM Layout", "reservation": "GEN", "registered_voters": 270000},
            {"ac_number": 173, "name": "Jayanagar", "reservation": "GEN", "registered_voters": 205000},
            {"ac_number": 175, "name": "Bommanahalli", "reservation": "GEN", "registered_voters": 410000},
        ],
    },
    {
        "id": "KA-PC-26",
        "pc_number": 26,
        "name": "Bengaluru North",
        "state_code": "KA",
        "reservation": "GEN",
        "total_electors": 2800000,
        "assembly_constituencies": [
            {"ac_number": 151, "name": "K.R. Puram", "reservation": "GEN", "registered_voters": 480000},
            {"ac_number": 152, "name": "Byatarayanapura", "reservation": "GEN", "registered_voters": 450000},
            {"ac_number": 153, "name": "Yeshwanthpur", "reservation": "GEN", "registered_voters": 470000},
            {"ac_number": 157, "name": "Malleshwaram", "reservation": "GEN", "registered_voters": 215000},
            {"ac_number": 158, "name": "Hebbal", "reservation": "GEN", "registered_voters": 280000},
        ],
    },
    # Maharashtra PCs
    {
        "id": "MH-PC-31",
        "pc_number": 31,
        "name": "Mumbai South",
        "state_code": "MH",
        "reservation": "GEN",
        "total_electors": 1520000,
        "assembly_constituencies": [
            {"ac_number": 182, "name": "Worli", "reservation": "GEN", "registered_voters": 255000},
            {"ac_number": 183, "name": "Shivadi", "reservation": "GEN", "registered_voters": 248000},
            {"ac_number": 184, "name": "Byculla", "reservation": "GEN", "registered_voters": 232000},
            {"ac_number": 185, "name": "Malabar Hill", "reservation": "GEN", "registered_voters": 268000},
            {"ac_number": 186, "name": "Mumbadevi", "reservation": "GEN", "registered_voters": 225000},
            {"ac_number": 187, "name": "Colaba", "reservation": "GEN", "registered_voters": 292000},
        ],
    },
    # Delhi PCs
    {
        "id": "DL-PC-04",
        "pc_number": 4,
        "name": "New Delhi",
        "state_code": "DL",
        "reservation": "GEN",
        "total_electors": 1610000,
        "assembly_constituencies": [
            {"ac_number": 38, "name": "Delhi Cantt", "reservation": "GEN", "registered_voters": 135000},
            {"ac_number": 39, "name": "Rajinder Nagar", "reservation": "GEN", "registered_voters": 180000},
            {"ac_number": 40, "name": "New Delhi", "reservation": "GEN", "registered_voters": 145000},
            {"ac_number": 42, "name": "Kasturba Nagar", "reservation": "GEN", "registered_voters": 155000},
            {"ac_number": 43, "name": "Malviya Nagar", "reservation": "GEN", "registered_voters": 150000},
            {"ac_number": 44, "name": "R K Puram", "reservation": "GEN", "registered_voters": 158000},
            {"ac_number": 50, "name": "Greater Kailash", "reservation": "GEN", "registered_voters": 178000},
        ],
    },
]


def get_all_states() -> list[dict[str, Any]]:
    return INDIAN_STATES


def get_state_by_code(code: str) -> dict[str, Any] | None:
    code_upper = code.upper()
    for s in INDIAN_STATES:
        if s["code"] == code_upper:
            return s
    return None


def get_pcs_for_state(state_code: str) -> list[dict[str, Any]]:
    code_upper = state_code.upper()
    return [pc for pc in PARLIAMENTARY_CONSTITUENCIES if pc["state_code"] == code_upper]


def get_pc_by_id(pc_id: str) -> dict[str, Any] | None:
    for pc in PARLIAMENTARY_CONSTITUENCIES:
        if pc["id"] == pc_id or str(pc["pc_number"]) == pc_id:
            return pc
    return None
