"""
Indian Electoral Geography — REFERENCE / SIMULATION DATA for SecureVOTE 3.3.

=============================================================================
IMPORTANT DISCLAIMERS & METADATA BOUNDARIES:
=============================================================================
1. REAL PUBLIC REFERENCE DATA:
   - State and Union Territory names, ISO-3166-2:IN codes, capitals, and regions.
   - Official counts of Parliamentary Constituencies (Lok Sabha) and Assembly Constituencies.
   - Names of Parliamentary Constituencies (PCs) and Assembly Constituencies (ACs).
   - Approximate registered elector estimates compiled from public historical publications.

2. SYNTHETIC SIMULATION DATA:
   - Polling station names, station codes (e.g. KA-24-PS-001), and room allocations.
   - Assigned voting devices (CU/BU/VVPAT) and status indicators.
   - Simulated voter turnouts, ballots cast, and candidate vote counts.
   - Candidate names, parties, and affiliations.
   - All cryptographic tallies, zero-knowledge proofs, and threshold shares.

This module is compiled STRICTLY for academic research and educational demonstration.
It is NOT an official electoral roll or an official database of the Election Commission of India (ECI).
Do NOT rely on these values for official, legal, or production electoral operations.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Reference Indian States & Union Territories (12 Representative Jurisdictions)
# ---------------------------------------------------------------------------

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
        "svg_path": "M 220 370 L 260 365 L 275 410 L 260 480 L 230 475 L 210 420 Z",
        "center": [15.3173, 75.7139],
        "turnout_percentage": 73.8,
        "anomalies_count": 0,
        "verification_status": "VERIFIED",
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
        "svg_path": "M 180 300 L 275 295 L 315 340 L 260 365 L 205 360 L 175 325 Z",
        "center": [19.7515, 75.7139],
        "turnout_percentage": 68.4,
        "anomalies_count": 0,
        "verification_status": "READY",
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
        "svg_path": "M 235 480 L 285 470 L 280 545 L 250 555 L 230 500 Z",
        "center": [11.1271, 78.6569],
        "turnout_percentage": 72.1,
        "anomalies_count": 0,
        "verification_status": "READY",
    },
    {
        "code": "KL",
        "name": "Kerala",
        "capital": "Thiruvananthapuram",
        "region": "South",
        "total_pcs": 20,
        "total_acs": 140,
        "registered_electors": 27700000,
        "active_simulation": False,
        "svg_path": "M 215 485 L 235 490 L 245 550 L 230 560 L 215 515 Z",
        "center": [10.8505, 76.2711],
        "turnout_percentage": 76.5,
        "anomalies_count": 0,
        "verification_status": "READY",
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
        "svg_path": "M 265 340 L 325 335 L 315 395 L 265 385 Z",
        "center": [18.1124, 79.0193],
        "turnout_percentage": 71.9,
        "anomalies_count": 0,
        "verification_status": "READY",
    },
    {
        "code": "AP",
        "name": "Andhra Pradesh",
        "capital": "Amaravati",
        "region": "South",
        "total_pcs": 25,
        "total_acs": 175,
        "registered_electors": 40800000,
        "active_simulation": False,
        "svg_path": "M 275 395 L 365 355 L 325 450 L 260 440 Z",
        "center": [15.9129, 79.7400],
        "turnout_percentage": 79.2,
        "anomalies_count": 0,
        "verification_status": "READY",
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
        "turnout_percentage": 63.8,
        "anomalies_count": 0,
        "verification_status": "READY",
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
        "svg_path": "M 255 170 L 375 175 L 355 245 L 275 245 L 245 195 Z",
        "center": [26.8467, 80.9462],
        "turnout_percentage": 66.2,
        "anomalies_count": 0,
        "verification_status": "READY",
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
        "svg_path": "M 410 215 L 445 215 L 435 305 L 405 295 Z",
        "center": [22.9868, 87.8550],
        "turnout_percentage": 78.9,
        "anomalies_count": 0,
        "verification_status": "READY",
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
        "svg_path": "M 130 240 L 190 235 L 180 305 L 120 280 Z",
        "center": [22.2587, 71.1924],
        "turnout_percentage": 65.4,
        "anomalies_count": 0,
        "verification_status": "READY",
    },
    {
        "code": "RJ",
        "name": "Rajasthan",
        "capital": "Jaipur",
        "region": "North-West",
        "total_pcs": 25,
        "total_acs": 200,
        "registered_electors": 53200000,
        "active_simulation": False,
        "svg_path": "M 155 165 L 235 160 L 245 235 L 155 240 Z",
        "center": [27.0238, 74.2179],
        "turnout_percentage": 67.8,
        "anomalies_count": 0,
        "verification_status": "READY",
    },
    {
        "code": "MP",
        "name": "Madhya Pradesh",
        "capital": "Bhopal",
        "region": "Central",
        "total_pcs": 29,
        "total_acs": 230,
        "registered_electors": 56100000,
        "active_simulation": False,
        "svg_path": "M 220 245 L 325 240 L 315 305 L 195 295 Z",
        "center": [22.9734, 78.6569],
        "turnout_percentage": 74.2,
        "anomalies_count": 0,
        "verification_status": "READY",
    },
]

# ---------------------------------------------------------------------------
# Parliamentary Constituencies (Lok Sabha)
# ---------------------------------------------------------------------------

PARLIAMENTARY_CONSTITUENCIES: list[dict[str, Any]] = [
    # 1. Karnataka
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
    # 2. Maharashtra
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
    {
        "id": "MH-PC-34",
        "pc_number": 34,
        "name": "Pune",
        "state_code": "MH",
        "reservation": "GEN",
        "total_electors": 2080000,
        "assembly_constituencies": [
            {"ac_number": 208, "name": "Vadgaon Sheri", "reservation": "GEN", "registered_voters": 435000},
            {"ac_number": 209, "name": "Shivajinagar", "reservation": "GEN", "registered_voters": 305000},
            {"ac_number": 210, "name": "Kothrud", "reservation": "GEN", "registered_voters": 405000},
            {"ac_number": 212, "name": "Parvati", "reservation": "GEN", "registered_voters": 345000},
            {"ac_number": 214, "name": "Pune Cantonment", "reservation": "SC", "registered_voters": 285000},
            {"ac_number": 215, "name": "Kasba Peth", "reservation": "GEN", "registered_voters": 275000},
        ],
    },
    # 3. Tamil Nadu
    {
        "id": "TN-PC-04",
        "pc_number": 4,
        "name": "Chennai Central",
        "state_code": "TN",
        "reservation": "GEN",
        "total_electors": 1350000,
        "assembly_constituencies": [
            {"ac_number": 14, "name": "Villivakkam", "reservation": "GEN", "registered_voters": 255000},
            {"ac_number": 16, "name": "Egmore", "reservation": "SC", "registered_voters": 195000},
            {"ac_number": 18, "name": "Harbour", "reservation": "GEN", "registered_voters": 180000},
            {"ac_number": 19, "name": "Chepauk-Thiruvallikeni", "reservation": "GEN", "registered_voters": 235000},
            {"ac_number": 20, "name": "Thousand Lights", "reservation": "GEN", "registered_voters": 240000},
            {"ac_number": 21, "name": "Anna Nagar", "reservation": "GEN", "registered_voters": 245000},
        ],
    },
    # 4. Kerala
    {
        "id": "KL-PC-20",
        "pc_number": 20,
        "name": "Thiruvananthapuram",
        "state_code": "KL",
        "reservation": "GEN",
        "total_electors": 1430000,
        "assembly_constituencies": [
            {"ac_number": 132, "name": "Kazhakoottam", "reservation": "GEN", "registered_voters": 190000},
            {"ac_number": 133, "name": "Vattiyoorkavu", "reservation": "GEN", "registered_voters": 198000},
            {"ac_number": 134, "name": "Thiruvananthapuram", "reservation": "GEN", "registered_voters": 192000},
            {"ac_number": 135, "name": "Nemom", "reservation": "GEN", "registered_voters": 204000},
            {"ac_number": 137, "name": "Parassala", "reservation": "GEN", "registered_voters": 218000},
            {"ac_number": 138, "name": "Kattakkada", "reservation": "GEN", "registered_voters": 195000},
            {"ac_number": 139, "name": "Kovalam", "reservation": "GEN", "registered_voters": 233000},
        ],
    },
    # 5. Telangana
    {
        "id": "TG-PC-09",
        "pc_number": 9,
        "name": "Hyderabad",
        "state_code": "TG",
        "reservation": "GEN",
        "total_electors": 1980000,
        "assembly_constituencies": [
            {"ac_number": 58, "name": "Malakpet", "reservation": "GEN", "registered_voters": 285000},
            {"ac_number": 64, "name": "Karwan", "reservation": "GEN", "registered_voters": 310000},
            {"ac_number": 65, "name": "Goshamahal", "reservation": "GEN", "registered_voters": 265000},
            {"ac_number": 66, "name": "Charminar", "reservation": "GEN", "registered_voters": 230000},
            {"ac_number": 67, "name": "Chandrayangutta", "reservation": "GEN", "registered_voters": 295000},
            {"ac_number": 68, "name": "Yakutpura", "reservation": "GEN", "registered_voters": 330000},
            {"ac_number": 69, "name": "Bahadurpura", "reservation": "GEN", "registered_voters": 265000},
        ],
    },
    # 6. Andhra Pradesh
    {
        "id": "AP-PC-04",
        "pc_number": 4,
        "name": "Visakhapatnam",
        "state_code": "AP",
        "reservation": "GEN",
        "total_electors": 1820000,
        "assembly_constituencies": [
            {"ac_number": 20, "name": "Bhimli", "reservation": "GEN", "registered_voters": 315000},
            {"ac_number": 21, "name": "Visakhapatnam East", "reservation": "GEN", "registered_voters": 275000},
            {"ac_number": 22, "name": "Visakhapatnam South", "reservation": "GEN", "registered_voters": 210000},
            {"ac_number": 23, "name": "Visakhapatnam North", "reservation": "GEN", "registered_voters": 285000},
            {"ac_number": 24, "name": "Visakhapatnam West", "reservation": "GEN", "registered_voters": 240000},
            {"ac_number": 25, "name": "Gajuwaka", "reservation": "GEN", "registered_voters": 320000},
        ],
    },
    # 7. NCT of Delhi
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
    # 8. Uttar Pradesh
    {
        "id": "UP-PC-35",
        "pc_number": 35,
        "name": "Lucknow",
        "state_code": "UP",
        "reservation": "GEN",
        "total_electors": 2050000,
        "assembly_constituencies": [
            {"ac_number": 171, "name": "Lucknow West", "reservation": "GEN", "registered_voters": 420000},
            {"ac_number": 172, "name": "Lucknow North", "reservation": "GEN", "registered_voters": 440000},
            {"ac_number": 173, "name": "Lucknow East", "reservation": "GEN", "registered_voters": 435000},
            {"ac_number": 174, "name": "Lucknow Central", "reservation": "GEN", "registered_voters": 375000},
            {"ac_number": 175, "name": "Lucknow Cantt", "reservation": "GEN", "registered_voters": 380000},
        ],
    },
    {
        "id": "UP-PC-77",
        "pc_number": 77,
        "name": "Varanasi",
        "state_code": "UP",
        "reservation": "GEN",
        "total_electors": 1850000,
        "assembly_constituencies": [
            {"ac_number": 387, "name": "Rohaniya", "reservation": "GEN", "registered_voters": 395000},
            {"ac_number": 388, "name": "Varanasi North", "reservation": "GEN", "registered_voters": 410000},
            {"ac_number": 389, "name": "Varanasi South", "reservation": "GEN", "registered_voters": 315000},
            {"ac_number": 390, "name": "Varanasi Cantt", "reservation": "GEN", "registered_voters": 440000},
            {"ac_number": 391, "name": "Sevapuri", "reservation": "GEN", "registered_voters": 335000},
        ],
    },
    # 9. West Bengal
    {
        "id": "WB-PC-23",
        "pc_number": 23,
        "name": "Kolkata Dakshin",
        "state_code": "WB",
        "reservation": "GEN",
        "total_electors": 1750000,
        "assembly_constituencies": [
            {"ac_number": 149, "name": "Kasba", "reservation": "GEN", "registered_voters": 290000},
            {"ac_number": 153, "name": "Behala Purba", "reservation": "GEN", "registered_voters": 305000},
            {"ac_number": 154, "name": "Behala Paschim", "reservation": "GEN", "registered_voters": 310000},
            {"ac_number": 158, "name": "Kolkata Port", "reservation": "GEN", "registered_voters": 235000},
            {"ac_number": 159, "name": "Bhabanipur", "reservation": "GEN", "registered_voters": 205000},
            {"ac_number": 160, "name": "Rashbehari", "reservation": "GEN", "registered_voters": 205000},
            {"ac_number": 161, "name": "Ballygunge", "reservation": "GEN", "registered_voters": 245000},
        ],
    },
    # 10. Gujarat
    {
        "id": "GJ-PC-07",
        "pc_number": 7,
        "name": "Ahmedabad East",
        "state_code": "GJ",
        "reservation": "GEN",
        "total_electors": 1900000,
        "assembly_constituencies": [
            {"ac_number": 35, "name": "Gandhinagar Dakshin", "reservation": "GEN", "registered_voters": 310000},
            {"ac_number": 43, "name": "Vatva", "reservation": "GEN", "registered_voters": 360000},
            {"ac_number": 44, "name": "Nikol", "reservation": "GEN", "registered_voters": 295000},
            {"ac_number": 45, "name": "Naroda", "reservation": "GEN", "registered_voters": 280000},
            {"ac_number": 46, "name": "Thakkarbapa Nagar", "reservation": "GEN", "registered_voters": 235000},
            {"ac_number": 47, "name": "Bapunagar", "reservation": "GEN", "registered_voters": 205000},
        ],
    },
    # 11. Rajasthan
    {
        "id": "RJ-PC-07",
        "pc_number": 7,
        "name": "Jaipur",
        "state_code": "RJ",
        "reservation": "GEN",
        "total_electors": 2280000,
        "assembly_constituencies": [
            {"ac_number": 49, "name": "Hawa Mahal", "reservation": "GEN", "registered_voters": 255000},
            {"ac_number": 50, "name": "Vidhyadhar Nagar", "reservation": "GEN", "registered_voters": 335000},
            {"ac_number": 51, "name": "Civil Lines", "reservation": "GEN", "registered_voters": 245000},
            {"ac_number": 52, "name": "Kishanpole", "reservation": "GEN", "registered_voters": 195000},
            {"ac_number": 53, "name": "Adarsh Nagar", "reservation": "GEN", "registered_voters": 250000},
            {"ac_number": 54, "name": "Malviya Nagar", "reservation": "GEN", "registered_voters": 220000},
            {"ac_number": 55, "name": "Sanganer", "reservation": "GEN", "registered_voters": 340000},
            {"ac_number": 56, "name": "Bagru", "reservation": "SC", "registered_voters": 340000},
        ],
    },
    # 12. Madhya Pradesh
    {
        "id": "MP-PC-19",
        "pc_number": 19,
        "name": "Bhopal",
        "state_code": "MP",
        "reservation": "GEN",
        "total_electors": 2150000,
        "assembly_constituencies": [
            {"ac_number": 149, "name": "Berasia", "reservation": "SC", "registered_voters": 230000},
            {"ac_number": 150, "name": "Bhopal Uttar", "reservation": "GEN", "registered_voters": 240000},
            {"ac_number": 151, "name": "Narela", "reservation": "GEN", "registered_voters": 325000},
            {"ac_number": 152, "name": "Bhopal Dakshin-Paschim", "reservation": "GEN", "registered_voters": 220000},
            {"ac_number": 153, "name": "Bhopal Madhya", "reservation": "GEN", "registered_voters": 245000},
            {"ac_number": 154, "name": "Govindpura", "reservation": "GEN", "registered_voters": 365000},
            {"ac_number": 155, "name": "Huzur", "reservation": "GEN", "registered_voters": 325000},
        ],
    },
]

# ---------------------------------------------------------------------------
# Representative Synthetic Polling Stations (Clearly Designated Simulation Data)
# ---------------------------------------------------------------------------

SYNTHETIC_POLLING_STATIONS: dict[str, list[dict[str, Any]]] = {
    "KA-PC-24": [
        {
            "id": "KA-24-PS-041",
            "station_code": "KA-24-PS-041",
            "name": "Govt Higher Primary School, Shivaji Road",
            "location": "Shivajinagar, Bengaluru",
            "pc_id": "KA-PC-24",
            "ac_name": "Shivajinagar",
            "assigned_devices": ["CU-KA-101", "BU-KA-201", "VVPAT-KA-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1240,
            "ballots_cast": 918,
            "turnout_percentage": 74.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
        {
            "id": "KA-24-PS-042",
            "station_code": "KA-24-PS-042",
            "name": "BBMP Community Hall, Queens Road",
            "location": "Shivajinagar, Bengaluru",
            "pc_id": "KA-PC-24",
            "ac_name": "Shivajinagar",
            "assigned_devices": ["CU-KA-102", "BU-KA-202", "VVPAT-KA-302"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1180,
            "ballots_cast": 892,
            "turnout_percentage": 75.6,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
        {
            "id": "KA-24-PS-078",
            "station_code": "KA-24-PS-078",
            "name": "St. Joseph's Model School, Museum Road",
            "location": "Shanti Nagar, Bengaluru",
            "pc_id": "KA-PC-24",
            "ac_name": "Shanti Nagar",
            "assigned_devices": ["CU-KA-103", "BU-KA-203", "VVPAT-KA-303"],
            "device_status": "ONLINE",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1350,
            "ballots_cast": 972,
            "turnout_percentage": 72.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
        {
            "id": "KA-24-PS-115",
            "station_code": "KA-24-PS-115",
            "name": "Govt High School, Ulsoor",
            "location": "Sarvagnanagar, Bengaluru",
            "pc_id": "KA-PC-24",
            "ac_name": "Sarvagnanagar",
            "assigned_devices": ["CU-KA-104", "BU-KA-204", "VVPAT-KA-304"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1420,
            "ballots_cast": 1051,
            "turnout_percentage": 74.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "MH-PC-31": [
        {
            "id": "MH-31-PS-012",
            "station_code": "MH-31-PS-012",
            "name": "Municipal Primary School, Worli Naka",
            "location": "Worli, Mumbai",
            "pc_id": "MH-PC-31",
            "ac_name": "Worli",
            "assigned_devices": ["CU-MH-101", "BU-MH-201", "VVPAT-MH-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1150,
            "ballots_cast": 782,
            "turnout_percentage": 68.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
        {
            "id": "MH-31-PS-055",
            "station_code": "MH-31-PS-055",
            "name": "St. Mary's High School, Byculla East",
            "location": "Byculla, Mumbai",
            "pc_id": "MH-PC-31",
            "ac_name": "Byculla",
            "assigned_devices": ["CU-MH-102", "BU-MH-202", "VVPAT-MH-302"],
            "device_status": "ONLINE",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1290,
            "ballots_cast": 877,
            "turnout_percentage": 68.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "DL-PC-04": [
        {
            "id": "DL-04-PS-022",
            "station_code": "DL-04-PS-022",
            "name": "NDMC Primary School, Lodhi Estate",
            "location": "New Delhi",
            "pc_id": "DL-PC-04",
            "ac_name": "New Delhi",
            "assigned_devices": ["CU-DL-101", "BU-DL-201", "VVPAT-DL-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1050,
            "ballots_cast": 682,
            "turnout_percentage": 65.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "TN-PC-04": [
        {
            "id": "TN-04-PS-018",
            "station_code": "TN-04-PS-018",
            "name": "Chennai Corporation Higher Secondary School",
            "location": "Egmore, Chennai",
            "pc_id": "TN-PC-04",
            "ac_name": "Egmore",
            "assigned_devices": ["CU-TN-101", "BU-TN-201", "VVPAT-TN-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1220,
            "ballots_cast": 878,
            "turnout_percentage": 72.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "KL-PC-20": [
        {
            "id": "KL-20-PS-034",
            "station_code": "KL-20-PS-034",
            "name": "Govt Model Boys Vocational Higher Secondary School",
            "location": "Thycaud, Thiruvananthapuram",
            "pc_id": "KL-PC-20",
            "ac_name": "Thiruvananthapuram",
            "assigned_devices": ["CU-KL-101", "BU-KL-201", "VVPAT-KL-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1110,
            "ballots_cast": 849,
            "turnout_percentage": 76.5,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "TG-PC-09": [
        {
            "id": "TG-09-PS-019",
            "station_code": "TG-09-PS-019",
            "name": "Govt High School, Moghalpura",
            "location": "Charminar, Hyderabad",
            "pc_id": "TG-PC-09",
            "ac_name": "Charminar",
            "assigned_devices": ["CU-TG-101", "BU-TG-201", "VVPAT-TG-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1340,
            "ballots_cast": 965,
            "turnout_percentage": 72.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "AP-PC-04": [
        {
            "id": "AP-04-PS-026",
            "station_code": "AP-04-PS-026",
            "name": "Municipal Corporation High School, Siripuram",
            "location": "Visakhapatnam East",
            "pc_id": "AP-PC-04",
            "ac_name": "Visakhapatnam East",
            "assigned_devices": ["CU-AP-101", "BU-AP-201", "VVPAT-AP-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1280,
            "ballots_cast": 1011,
            "turnout_percentage": 79.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "UP-PC-35": [
        {
            "id": "UP-35-PS-042",
            "station_code": "UP-35-PS-042",
            "name": "Colvin Taluqdars College, University Road",
            "location": "Lucknow Central",
            "pc_id": "UP-PC-35",
            "ac_name": "Lucknow Central",
            "assigned_devices": ["CU-UP-101", "BU-UP-201", "VVPAT-UP-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1310,
            "ballots_cast": 865,
            "turnout_percentage": 66.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "WB-PC-23": [
        {
            "id": "WB-23-PS-030",
            "station_code": "WB-23-PS-030",
            "name": "South Suburban School, Bhabanipur",
            "location": "Bhabanipur, Kolkata",
            "pc_id": "WB-PC-23",
            "ac_name": "Bhabanipur",
            "assigned_devices": ["CU-WB-101", "BU-WB-201", "VVPAT-WB-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1190,
            "ballots_cast": 940,
            "turnout_percentage": 79.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "GJ-PC-07": [
        {
            "id": "GJ-07-PS-015",
            "station_code": "GJ-07-PS-015",
            "name": "Ahmedabad Municipal Corporation School, Nikol",
            "location": "Nikol, Ahmedabad",
            "pc_id": "GJ-PC-07",
            "ac_name": "Nikol",
            "assigned_devices": ["CU-GJ-101", "BU-GJ-201", "VVPAT-GJ-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1250,
            "ballots_cast": 812,
            "turnout_percentage": 65.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "RJ-PC-07": [
        {
            "id": "RJ-07-PS-028",
            "station_code": "RJ-07-PS-028",
            "name": "Maharaja Sawai Man Singh Vidyalaya, Civil Lines",
            "location": "Civil Lines, Jaipur",
            "pc_id": "RJ-PC-07",
            "ac_name": "Civil Lines",
            "assigned_devices": ["CU-RJ-101", "BU-RJ-201", "VVPAT-RJ-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1380,
            "ballots_cast": 938,
            "turnout_percentage": 68.0,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
    "MP-PC-19": [
        {
            "id": "MP-19-PS-033",
            "station_code": "MP-19-PS-033",
            "name": "Model Higher Secondary School, TT Nagar",
            "location": "Bhopal Dakshin-Paschim",
            "pc_id": "MP-PC-19",
            "ac_name": "Bhopal Dakshin-Paschim",
            "assigned_devices": ["CU-MP-101", "BU-MP-201", "VVPAT-MP-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1270,
            "ballots_cast": 942,
            "turnout_percentage": 74.2,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ],
}

# ---------------------------------------------------------------------------
# Representative Synthetic Candidate Sets (Clearly Flagged as Simulation Data)
# ---------------------------------------------------------------------------

SYNTHETIC_CANDIDATES: dict[str, list[dict[str, Any]]] = {
    "KA-PC-24": [
        {
            "id": "CAND-KA-24-01",
            "name": "A. Ramesh Kumar",
            "party": "National Democratic Front (Synthetic)",
            "party_code": "NDF",
            "symbol": "Lotus & Sun",
            "position": 1,
            "is_synthetic": True,
            "is_nota": False,
        },
        {
            "id": "CAND-KA-24-02",
            "name": "S. Mansoor Ali",
            "party": "United Progressive Alliance (Synthetic)",
            "party_code": "UPA",
            "symbol": "Open Hand & Torch",
            "position": 2,
            "is_synthetic": True,
            "is_nota": False,
        },
        {
            "id": "CAND-KA-24-03",
            "name": "Dr. Kavitha Gowda",
            "party": "Janata Vikas Dal (Synthetic)",
            "party_code": "JVD",
            "symbol": "Farmer Plough",
            "position": 3,
            "is_synthetic": True,
            "is_nota": False,
        },
        {
            "id": "CAND-KA-24-NOTA",
            "name": "None of the Above (Rule 49B)",
            "party": "NOTA",
            "party_code": "NOTA",
            "symbol": "Cross Ballot",
            "position": 4,
            "is_synthetic": False,
            "is_nota": True,
        },
    ],
    "MH-PC-31": [
        {
            "id": "CAND-MH-31-01",
            "name": "V. S. Deshmukh",
            "party": "Maharashtra Vikas Morcha (Synthetic)",
            "party_code": "MVM",
            "symbol": "Bow & Arrow",
            "position": 1,
            "is_synthetic": True,
            "is_nota": False,
        },
        {
            "id": "CAND-MH-31-02",
            "name": "P. N. Mehta",
            "party": "National Democratic Front (Synthetic)",
            "party_code": "NDF",
            "symbol": "Lotus & Sun",
            "position": 2,
            "is_synthetic": True,
            "is_nota": False,
        },
        {
            "id": "CAND-MH-31-NOTA",
            "name": "None of the Above (Rule 49B)",
            "party": "NOTA",
            "party_code": "NOTA",
            "symbol": "Cross Ballot",
            "position": 3,
            "is_synthetic": False,
            "is_nota": True,
        },
    ],
    "DL-PC-04": [
        {
            "id": "CAND-DL-04-01",
            "name": "Sunil V. Sharma",
            "party": "Citizens Welfare Forum (Synthetic)",
            "party_code": "CWF",
            "symbol": "Broom",
            "position": 1,
            "is_synthetic": True,
            "is_nota": False,
        },
        {
            "id": "CAND-DL-04-02",
            "name": "Ananya Malhotra",
            "party": "National Democratic Front (Synthetic)",
            "party_code": "NDF",
            "symbol": "Lotus & Sun",
            "position": 2,
            "is_synthetic": True,
            "is_nota": False,
        },
        {
            "id": "CAND-DL-04-NOTA",
            "name": "None of the Above (Rule 49B)",
            "party": "NOTA",
            "party_code": "NOTA",
            "symbol": "Cross Ballot",
            "position": 3,
            "is_synthetic": False,
            "is_nota": True,
        },
    ],
}

# Generic fallback candidate set for any constituency without explicit custom candidates
DEFAULT_CANDIDATE_SET = [
    {
        "id": "CAND-DEFAULT-01",
        "name": "Candidate 1 (Synthetic)",
        "party": "Democratic Front (Synthetic)",
        "party_code": "DF",
        "symbol": "Sun",
        "position": 1,
        "is_synthetic": True,
        "is_nota": False,
    },
    {
        "id": "CAND-DEFAULT-02",
        "name": "Candidate 2 (Synthetic)",
        "party": "Progressive Alliance (Synthetic)",
        "party_code": "PA",
        "symbol": "Torch",
        "position": 2,
        "is_synthetic": True,
        "is_nota": False,
    },
    {
        "id": "CAND-DEFAULT-03",
        "name": "Candidate 3 (Synthetic)",
        "party": "Janata Council (Synthetic)",
        "party_code": "JC",
        "symbol": "Wheel",
        "position": 3,
        "is_synthetic": True,
        "is_nota": False,
    },
    {
        "id": "CAND-DEFAULT-NOTA",
        "name": "None of the Above (Rule 49B)",
        "party": "NOTA",
        "party_code": "NOTA",
        "symbol": "Cross Ballot",
        "position": 4,
        "is_synthetic": False,
        "is_nota": True,
    },
]


# ---------------------------------------------------------------------------
# Query & Retrieval Functions
# ---------------------------------------------------------------------------

def _enrich_station(st: dict[str, Any]) -> dict[str, Any]:
    """Enrich polling station dictionary with serial shortcuts and turnout aliases."""
    s = dict(st)
    devs = s.get("assigned_devices", [])
    s.setdefault("cu_serial", devs[0] if len(devs) > 0 else f"CU-{s.get('station_code', '01')}")
    s.setdefault("bu_serial", devs[1] if len(devs) > 1 else f"BU-{s.get('station_code', '01')}")
    s.setdefault("vvpat_serial", devs[2] if len(devs) > 2 else f"VVPAT-{s.get('station_code', '01')}")
    s.setdefault("turnout_pct", s.get("turnout_percentage", 70.0))
    s.setdefault("status", s.get("device_status", "VERIFIED"))
    return s


def get_all_states() -> list[dict[str, Any]]:
    """Retrieve list of all 12 reference Indian States and UTs with aliases."""
    result = []
    for s in INDIAN_STATES:
        item = dict(s)
        item["pc_count"] = item["total_pcs"]
        item["ac_count"] = item["total_acs"]
        item["elector_count_est"] = item["registered_electors"]
        item["d"] = item["svg_path"]
        item["turnout_pct"] = item.get("turnout_percentage", 70.0)
        result.append(item)
    return result


def get_state_by_code(code: str) -> dict[str, Any] | None:
    """Lookup state metadata by uppercase 2-letter state code."""
    code_upper = code.upper()
    for s in get_all_states():
        if s["code"] == code_upper:
            return s
    return None


def get_pcs_for_state(state_code: str) -> list[dict[str, Any]]:
    """Retrieve parliamentary constituencies for a specific state code."""
    code_upper = state_code.upper()
    results = []
    for pc in PARLIAMENTARY_CONSTITUENCIES:
        if pc["state_code"] == code_upper:
            item = dict(pc)
            item["pc_id"] = item["id"]
            item["pc_name"] = item["name"]
            item["acs"] = item.get("assembly_constituencies", [])
            item["estimated_electors"] = item.get("total_electors", 1800000)
            results.append(item)
    return results


def get_pc_by_id(pc_id: str) -> dict[str, Any] | None:
    """Lookup parliamentary constituency by unique ID (e.g. 'KA-PC-24')."""
    for pc in PARLIAMENTARY_CONSTITUENCIES:
        if pc["id"] == pc_id or str(pc["pc_number"]) == pc_id or pc.get("pc_id") == pc_id:
            item = dict(pc)
            item["pc_id"] = item["id"]
            item["pc_name"] = item["name"]
            item["acs"] = item.get("assembly_constituencies", [])
            item["estimated_electors"] = item.get("total_electors", 1800000)
            return item
    return None


def get_polling_stations_for_pc(pc_id: str) -> list[dict[str, Any]]:
    """Retrieve synthetic polling stations for a given parliamentary constituency."""
    stations = SYNTHETIC_POLLING_STATIONS.get(pc_id)
    if stations:
        return [_enrich_station(st) for st in stations]

    # Generate generic synthetic polling stations if none configured explicitly
    pc = get_pc_by_id(pc_id)
    if not pc:
        return []

    pc_num = pc["pc_number"]
    st_code = pc["state_code"]
    acs = pc.get("assembly_constituencies", [])
    ac_name = acs[0]["name"] if acs else "Ward 1"

    generated = [
        {
            "id": f"{st_code}-{pc_num}-PS-001",
            "station_code": f"{st_code}-{pc_num}-PS-001",
            "name": f"Govt Model School, Sector 1, {pc['name']}",
            "location": f"{ac_name}, {pc['name']}",
            "pc_id": pc_id,
            "ac_name": ac_name,
            "assigned_devices": [f"CU-{st_code}-101", f"BU-{st_code}-201", f"VVPAT-{st_code}-301"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1250,
            "ballots_cast": 920,
            "turnout_percentage": 73.6,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
        {
            "id": f"{st_code}-{pc_num}-PS-002",
            "station_code": f"{st_code}-{pc_num}-PS-002",
            "name": f"Community Centre, Sector 2, {pc['name']}",
            "location": f"{ac_name}, {pc['name']}",
            "pc_id": pc_id,
            "ac_name": ac_name,
            "assigned_devices": [f"CU-{st_code}-102", f"BU-{st_code}-202", f"VVPAT-{st_code}-302"],
            "device_status": "VERIFIED",
            "evm_status": "ONLINE",
            "vvpat_status": "READY",
            "registered_voters": 1180,
            "ballots_cast": 875,
            "turnout_percentage": 74.1,
            "anomalies_detected": 0,
            "verification_state": "VALID",
            "is_synthetic": True,
        },
    ]
    return [_enrich_station(st) for st in generated]


def get_candidates_for_pc(pc_id: str) -> list[dict[str, Any]]:
    """Retrieve synthetic candidates for a given parliamentary constituency."""
    if isinstance(pc_id, str) and pc_id in SYNTHETIC_CANDIDATES:
        return SYNTHETIC_CANDIDATES[pc_id]
    return DEFAULT_CANDIDATE_SET


def get_polling_station_by_code(station_code: str) -> dict[str, Any] | None:
    """Lookup a single polling station by its unique code (e.g. 'KA-24-PS-042')."""
    for stations in SYNTHETIC_POLLING_STATIONS.values():
        for s in stations:
            if s["station_code"] == station_code or s["id"] == station_code:
                return _enrich_station(s)
    # Search in generated stations across all PCs
    for pc in PARLIAMENTARY_CONSTITUENCIES:
        for s in get_polling_stations_for_pc(pc["id"]):
            if s["station_code"] == station_code or s["id"] == station_code:
                return _enrich_station(s)
    return None

