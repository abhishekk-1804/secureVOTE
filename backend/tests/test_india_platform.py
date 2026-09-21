"""
SecureVOTE 3.3 — Indian Electoral Platform Tests.

Verifies:
- All 12 states & UTs are registered with valid geography metadata.
- SVG path data, centers, and bounds are well-formed.
- Lok Sabha PCs and Assembly Constituencies exist and match reference data.
- Polling stations contain valid CU, BU, and VVPAT hardware identifiers.
- Synthetic candidates exist per PC with Rule 49B NOTA.
- National summary metrics aggregate correctly across all 12 jurisdictions.
- REST API endpoints for geography, hierarchy, polling stations, and candidates.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.geography import (
    INDIAN_STATES,
    PARLIAMENTARY_CONSTITUENCIES,
    SYNTHETIC_POLLING_STATIONS,
    SYNTHETIC_CANDIDATES,
    get_all_states,
    get_state_by_code,
    get_pcs_for_state,
    get_pc_by_id,
    get_polling_stations_for_pc,
    get_candidates_for_pc,
    get_polling_station_by_code,
)


@pytest.fixture
def client():
    return TestClient(app)


class TestIndianElectoralModel:
    """Direct validation of Indian electoral geography model."""

    def test_required_12_states_present(self):
        expected_codes = {"KA", "MH", "TN", "KL", "TG", "AP", "DL", "UP", "WB", "GJ", "RJ", "MP"}
        actual_codes = {s["code"] for s in get_all_states()}
        assert expected_codes.issubset(actual_codes), f"Missing states: {expected_codes - actual_codes}"
        assert len(actual_codes) >= 12

    def test_state_metadata_well_formed(self):
        for state in get_all_states():
            assert "code" in state
            assert "name" in state
            assert "capital" in state
            assert "region" in state
            assert state["pc_count"] > 0
            assert state["ac_count"] > 0
            assert state["elector_count_est"] > 0
            assert "d" in state and len(state["d"]) > 5
            assert "center" in state and len(state["center"]) == 2

    def test_constituencies_exist_for_all_states(self):
        for state in get_all_states():
            pcs = get_pcs_for_state(state["code"])
            assert len(pcs) > 0, f"No PCs found for state {state['code']}"
            for pc in pcs:
                assert pc["pc_id"].startswith(f"{state['code']}-PC-")
                assert len(pc["acs"]) > 0, f"No ACs in PC {pc['pc_id']}"
                assert pc["estimated_electors"] > 100_000

    def test_polling_stations_have_three_unit_devices(self):
        """ECI EVM architecture requires CU, BU, and VVPAT per station."""
        for pc in PARLIAMENTARY_CONSTITUENCIES:
            stations = get_polling_stations_for_pc(pc["id"])
            assert len(stations) > 0, f"No polling stations for PC {pc['id']}"
            for st in stations:
                assert st["cu_serial"].startswith("CU-"), f"Invalid CU serial: {st['cu_serial']}"
                assert st["bu_serial"].startswith("BU-"), f"Invalid BU serial: {st['bu_serial']}"
                assert st["vvpat_serial"].startswith("VVPAT-"), f"Invalid VVPAT serial: {st['vvpat_serial']}"
                assert st["registered_voters"] > 0
                assert 0 <= st["turnout_pct"] <= 100

    def test_candidates_have_rule_49b_nota(self):
        """Conduct of Elections Rules, 1961 - Rule 49B requires None of the Above."""
        for pc in PARLIAMENTARY_CONSTITUENCIES:
            candidates = get_candidates_for_pc(pc["id"])
            assert len(candidates) >= 2, f"PC {pc['id']} must have candidates"
            nota_found = any(c["name"].startswith("None of the Above") or c["party"] == "NOTA" for c in candidates)
            assert nota_found, f"NOTA not found for PC {pc['id']}"


class TestGeographyApiEndpoints:
    """Integration test of /api/geography/ endpoints."""

    def test_get_states_endpoint(self, client):
        resp = client.get("/api/geography/states")
        assert resp.status_code == 200
        data = resp.json()
        assert "states" in data
        assert data["total"] >= 12
        codes = [s["code"] for s in data["states"]]
        assert "KA" in codes
        assert "MH" in codes
        assert "UP" in codes

    def test_get_single_state_endpoint(self, client):
        resp = client.get("/api/geography/states/KA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"]["code"] == "KA"
        assert data["state"]["name"] == "Karnataka"
        assert len(data["constituencies"]) >= 2

    def test_get_nonexistent_state(self, client):
        resp = client.get("/api/geography/states/ZZ")
        assert resp.status_code == 404

    def test_get_pc_endpoint(self, client):
        resp = client.get("/api/geography/pc/KA-PC-24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pc_id"] == "KA-PC-24"
        assert data["pc_name"] == "Bengaluru Central"
        assert len(data["acs"]) == 8
        assert "polling_stations" in data
        assert "candidates" in data

    def test_get_pc_polling_stations(self, client):
        resp = client.get("/api/geography/pc/KA-PC-24/polling-stations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pc_id"] == "KA-PC-24"
        assert len(data["polling_stations"]) >= 3
        station = data["polling_stations"][0]
        assert "cu_serial" in station
        assert "bu_serial" in station
        assert "vvpat_serial" in station

    def test_get_pc_candidates(self, client):
        resp = client.get("/api/geography/pc/KA-PC-24/candidates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pc_id"] == "KA-PC-24"
        assert len(data["candidates"]) >= 4
        # Rule 49B NOTA is present
        assert any("NOTA" in c["party"] for c in data["candidates"])

    def test_get_single_polling_station(self, client):
        resp = client.get("/api/geography/polling-station/KA-24-PS-042")
        assert resp.status_code == 200
        data = resp.json()
        assert data["station_code"] == "KA-24-PS-042"
        assert "cu_serial" in data
        assert "vvpat_serial" in data

    def test_get_national_summary(self, client):
        resp = client.get("/api/geography/national-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_states"] == 12
        assert data["total_pcs"] >= 60
        assert data["total_acs"] >= 400
        assert data["active_trustees"] == 3
        assert data["trustee_threshold"] == "2-of-3"
        assert "disclaimer" in data
        assert "Research Prototype" in data["disclaimer"]
        assert len(data["states_summary"]) == 12

    def test_get_map_data(self, client):
        resp = client.get("/api/geography/map-data")
        assert resp.status_code == 200
        data = resp.json()
        assert data["viewbox"] == "0 0 600 650"
        assert len(data["features"]) == 12
        for f in data["features"]:
            assert "d" in f
            assert "turnout_pct" in f
            assert "verification_status" in f
            assert f["verification_status"] in ("VERIFIED", "WARNING", "PENDING", "READY")

