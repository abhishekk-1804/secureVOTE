"""
Integration Tests for SecureVOTE 3.0 Cryptographic FastAPI Endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_v3_crypto_election_lifecycle(client: AsyncClient):
    """
    Test complete lifecycle via REST API:
    init -> get -> encrypt -> cast -> list -> aggregate -> decrypt -> export -> verify
    """
    election_id = "V3-API-TEST-001"
    candidates = ["CAND-A", "CAND-B", "NOTA"]

    # 1. Init election
    init_resp = await client.post(
        "/api/v3/crypto/elections/init",
        json={"election_id": election_id, "candidates": candidates},
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()
    assert init_data["election_id"] == election_id
    assert init_data["candidate_count"] == 3
    assert len(init_data["key_fingerprint"]) == 64

    # 2. Get election
    get_resp = await client.get(f"/api/v3/crypto/elections/{election_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["key_fingerprint"] == init_data["key_fingerprint"]

    # 3. Encrypt ballots
    # Voter 1 votes CAND-A (index 0)
    enc1 = await client.post(
        "/api/v3/crypto/ballots/encrypt",
        json={"election_id": election_id, "candidate_index": 0},
    )
    assert enc1.status_code == 200
    b1_artifact = enc1.json()
    assert b1_artifact["artifact_type"] == "ENCRYPTED_BALLOT"

    # Voter 2 votes CAND-B (index 1)
    enc2 = await client.post(
        "/api/v3/crypto/ballots/encrypt",
        json={"election_id": election_id, "candidate_index": 1},
    )
    b2_artifact = enc2.json()

    # Voter 3 votes CAND-A (index 0)
    enc3 = await client.post(
        "/api/v3/crypto/ballots/encrypt",
        json={"election_id": election_id, "candidate_index": 0},
    )
    b3_artifact = enc3.json()

    # 4. Cast ballots
    c1 = await client.post(
        "/api/v3/crypto/ballots/cast",
        json={"election_id": election_id, "ballot_artifact": b1_artifact},
    )
    assert c1.status_code == 200
    assert c1.json()["ballot_count"] == 1

    c2 = await client.post(
        "/api/v3/crypto/ballots/cast",
        json={"election_id": election_id, "ballot_artifact": b2_artifact},
    )
    assert c2.status_code == 200
    assert c2.json()["ballot_count"] == 2

    c3 = await client.post(
        "/api/v3/crypto/ballots/cast",
        json={"election_id": election_id, "ballot_artifact": b3_artifact},
    )
    assert c3.status_code == 200
    assert c3.json()["ballot_count"] == 3

    # 5. List ballots
    list_resp = await client.get(f"/api/v3/crypto/ballots/{election_id}")
    assert list_resp.status_code == 200
    assert list_resp.json()["total_ballots"] == 3

    # 6. Aggregate tally
    agg_resp = await client.post(
        "/api/v3/crypto/tally/aggregate",
        json={"election_id": election_id},
    )
    assert agg_resp.status_code == 200
    agg_data = agg_resp.json()
    assert agg_data["ballot_count"] == 3
    assert agg_data["status"] == "ENCRYPTED"

    # 7. Decrypt tally
    dec_resp = await client.post(
        "/api/v3/crypto/tally/decrypt",
        json={"election_id": election_id},
    )
    assert dec_resp.status_code == 200
    dec_data = dec_resp.json()
    assert dec_data["candidate_tallies"] == {
        "CAND-A": 2,
        "CAND-B": 1,
        "NOTA": 0,
    }
    assert dec_data["total_ballots"] == 3
    assert dec_data["reconciliation_status"] == "BALANCED"

    # 8. Get tally record
    get_tally = await client.get(f"/api/v3/crypto/tally/{election_id}")
    assert get_tally.status_code == 200
    assert get_tally.json()["status"] == "DECRYPTED"

    # 9. Export package
    export_resp = await client.get(f"/api/v3/crypto/export/{election_id}")
    assert export_resp.status_code == 200
    package = export_resp.json()
    assert len(package["ballots"]) == 3

    # 10. Verify package via API
    verify_resp = await client.post(
        "/api/v3/crypto/verify",
        json={"package": package},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified"] is True
    assert verify_resp.json()["checkpoints_passed"] == verify_resp.json()["checkpoints_total"]


@pytest.mark.asyncio
async def test_v3_cast_rejects_tampered_ballot(client: AsyncClient):
    """Submitting a mutated ballot artifact to the API must be rejected with HTTP 400."""
    election_id = "V3-API-TAMPER-001"
    candidates = ["C1", "C2"]

    await client.post(
        "/api/v3/crypto/elections/init",
        json={"election_id": election_id, "candidates": candidates},
    )

    enc = await client.post(
        "/api/v3/crypto/ballots/encrypt",
        json={"election_id": election_id, "candidate_index": 0},
    )
    artifact = enc.json()

    # Tamper with slot C1 coordinate
    artifact["encrypted_vote"]["slots"][0]["c1"]["x"] = "00" * 32

    resp = await client.post(
        "/api/v3/crypto/ballots/cast",
        json={"election_id": election_id, "ballot_artifact": artifact},
    )
    assert resp.status_code == 400
