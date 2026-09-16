"""
Unit and Integration Tests for SecureVOTE External Audit-Root Anchoring (Phase 5.2).

Tests:
1. Local anchor creation commits audit root hash.
2. Retrieval by reference succeeds.
3. Matching root hash verifies successfully.
4. Mismatching root hash fails verification.
5. Unknown anchor reference fails safely.
6. External ledger provider returns NOT CONFIGURED / ENVIRONMENT-BLOCKED when unconfigured.
7. Anchor metadata rejects voter credentials or ballot plaintext.
8. End-to-end API anchoring creates audit entry and returns valid receipt.
"""

import pytest
from httpx import AsyncClient

from app.services.anchor_service import AnchorService, LocalAnchorProvider, ExternalLedgerAdapter


@pytest.mark.asyncio
async def test_local_anchor_provider_lifecycle():
    """Test creating, retrieving, and verifying local anchor receipts."""
    provider = LocalAnchorProvider()
    election_id = "EV-2026-001"
    root_hash = "a" * 64
    metadata = {"anchor_version": "1.0.0", "election_id": election_id}

    receipt = await provider.anchor(election_id, root_hash, metadata)
    assert receipt.status == "LOCAL ANCHOR"
    assert receipt.provider_type == "LOCAL ANCHOR"
    assert receipt.root_hash == root_hash
    assert receipt.anchor_reference.startswith("local-anc-")

    # Retrieval
    retrieved = await provider.get_anchor(receipt.anchor_reference)
    assert retrieved is not None
    assert retrieved.anchor_id == receipt.anchor_id

    # Verification: matching root
    assert await provider.verify_anchor(receipt.anchor_reference, root_hash) is True

    # Verification: tampered root
    assert await provider.verify_anchor(receipt.anchor_reference, "b" * 64) is False

    # Verification: invalid reference
    assert await provider.verify_anchor("invalid-ref", root_hash) is False


@pytest.mark.asyncio
async def test_anchor_rejects_sensitive_plaintext_metadata():
    """Local provider must raise ValueError if caller attempts to anchor voter PII."""
    provider = LocalAnchorProvider()
    election_id = "EV-2026-001"
    root_hash = "a" * 64

    # Attempting to include voter_credential must be rejected
    with pytest.raises(ValueError) as exc:
        await provider.anchor(
            election_id,
            root_hash,
            {"voter_credential": "SECRET-VOTER-123"},
        )
    assert "Forbidden sensitive key" in str(exc.value)

    # Attempting to include raw_uid must be rejected
    with pytest.raises(ValueError) as exc:
        await provider.anchor(
            election_id,
            root_hash,
            {"raw_uid": "04A1B2C3"},
        )
    assert "Forbidden sensitive key" in str(exc.value)


@pytest.mark.asyncio
async def test_external_ledger_unconfigured_safety():
    """External provider must truthfully return NOT CONFIGURED / ENVIRONMENT-BLOCKED when unconfigured."""
    adapter = ExternalLedgerAdapter()
    assert adapter.is_configured() is False

    receipt = await adapter.anchor("EV-2026-001", "a" * 64, {"version": "1.0"})
    assert receipt.status == "NOT CONFIGURED"
    assert receipt.provider_type == "EXTERNAL ANCHOR"
    assert "ENVIRONMENT-BLOCKED" in receipt.metadata.get("notice", "")

    # Verification against unconfigured adapter fails safely
    is_valid = await adapter.verify_anchor("any-ref", "a" * 64)
    assert is_valid is False


@pytest.mark.asyncio
async def test_anchoring_api_endpoints(
    client: AsyncClient,
    admin_headers: dict[str, str],
):
    """Integration test for POST and GET anchor endpoints via FastAPI."""
    election_id = "EV-2026-888"

    # Create and setup election
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Anchoring Test Election"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Candidate 1", "position": 1},
            ]
        },
        headers=admin_headers,
    )

    # 1. Create LOCAL anchor
    anchor_resp = await client.post(
        f"/api/elections/{election_id}/anchor",
        json={"provider_type": "LOCAL"},
        headers=admin_headers,
    )
    assert anchor_resp.status_code == 200
    receipt = anchor_resp.json()
    assert receipt["provider_type"] == "LOCAL ANCHOR"
    assert receipt["status"] == "LOCAL ANCHOR"
    assert receipt["election_id"] == election_id
    ref = receipt["anchor_reference"]

    # 2. Verify anchor via API
    verify_resp = await client.get(
        f"/api/elections/{election_id}/anchor/verify?reference={ref}",
        headers=admin_headers,
    )
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["verified"] is True
    assert verify_data["status"] == "LOCAL ANCHOR"

    # 3. Retrieve receipt by reference
    get_resp = await client.get(f"/api/anchors/{ref}", headers=admin_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["anchor_id"] == receipt["anchor_id"]

    # 4. External anchor request returns NOT CONFIGURED safely
    ext_resp = await client.post(
        f"/api/elections/{election_id}/anchor",
        json={"provider_type": "EXTERNAL"},
        headers=admin_headers,
    )
    assert ext_resp.status_code == 200
    assert ext_resp.json()["status"] == "NOT CONFIGURED"
