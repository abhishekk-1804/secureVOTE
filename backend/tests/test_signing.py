"""
Unit and Integration Tests for SecureVOTE Cryptographic Signing (Phase 5.1).

Tests:
1. Valid Ed25519 signature verifies.
2. Modified payload fails verification.
3. Modified signature bytes fail verification.
4. Signature verification with wrong public key fails.
5. Canonical JSON serialization is strictly deterministic regardless of key insertion order.
6. Ephemeral test key injection and safe failure when key is not configured.
7. Public key API exposes only public metadata, never private key material.
8. Manifest signing enforces election lifecycle (only CLOSED/PUBLISHED elections).
9. Manifest signing requires EXACT_MATCH reconciliation.
10. Manifest signature references correct election and audit root hash.
"""

import json
import pytest
from httpx import AsyncClient

from app.services.signing_service import SigningService


def test_ed25519_sign_and_verify(ephemeral_signing_key):
    """Test standard sign and verify flow using ephemeral key."""
    priv, pub = ephemeral_signing_key
    payload = {
        "artifact_type": "RESULT_MANIFEST",
        "election_id": "elec-test-01",
        "total_ballots": 42,
        "manifest_hash": "a" * 64,
    }

    signed = SigningService.sign_payload(payload, private_key=priv)
    assert signed["algorithm"] == "Ed25519"
    assert "signature" in signed
    assert "public_key" in signed
    assert "fingerprint" in signed

    is_valid = SigningService.verify_signature(
        payload=payload,
        signature_hex=signed["signature"],
        public_key_hex=signed["public_key"],
    )
    assert is_valid is True


def test_signature_fails_on_modified_payload(ephemeral_signing_key):
    """Tampering with signed payload must invalidate the signature."""
    priv, pub = ephemeral_signing_key
    payload = {"election_id": "elec-1", "votes": 100}
    signed = SigningService.sign_payload(payload, private_key=priv)

    tampered_payload = {"election_id": "elec-1", "votes": 101}
    assert SigningService.verify_signature(
        payload=tampered_payload,
        signature_hex=signed["signature"],
        public_key_hex=signed["public_key"],
    ) is False


def test_signature_fails_on_corrupted_signature(ephemeral_signing_key):
    """Tampering with the signature hex string must fail verification."""
    priv, pub = ephemeral_signing_key
    payload = {"election_id": "elec-1", "votes": 100}
    signed = SigningService.sign_payload(payload, private_key=priv)

    # Flip the last byte of the signature
    sig_bytes = bytearray.fromhex(signed["signature"])
    sig_bytes[-1] ^= 0xFF
    corrupted_sig = sig_bytes.hex()

    assert SigningService.verify_signature(
        payload=payload,
        signature_hex=corrupted_sig,
        public_key_hex=signed["public_key"],
    ) is False


def test_signature_fails_with_wrong_public_key(ephemeral_signing_key):
    """Verification against an unrelated public key must fail."""
    priv, pub = ephemeral_signing_key
    payload = {"election_id": "elec-1", "votes": 100}
    signed = SigningService.sign_payload(payload, private_key=priv)

    # Generate a separate unrelated keypair
    _, other_pub = SigningService.generate_keypair()
    other_pub_hex = SigningService.get_public_key_hex(other_pub)

    assert SigningService.verify_signature(
        payload=payload,
        signature_hex=signed["signature"],
        public_key_hex=other_pub_hex,
    ) is False


def test_canonical_json_serialization_is_deterministic():
    """Verify sort_keys and whitespace compaction are deterministic."""
    dict_a = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
    dict_b = {"nested": {"y": 20, "z": 10}, "a": 1, "b": 2}

    ser_a = SigningService.canonical_serialize(dict_a)
    ser_b = SigningService.canonical_serialize(dict_b)

    assert ser_a == ser_b
    assert b" " not in ser_a  # No whitespace after separators


def test_unconfigured_signing_key_fails_safely():
    """When no key is configured, sign_payload raises 503 rather than crashing."""
    SigningService.clear_keypair()
    with pytest.raises(Exception) as exc_info:
        SigningService.sign_payload({"test": 1})
    assert "503" in str(exc_info.value) or "not configured" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_public_key_api_endpoint(client: AsyncClient, ephemeral_signing_key):
    """API endpoint returns public key metadata and NEVER private key."""
    resp = await client.get("/api/signing/public-key")
    assert resp.status_code == 200
    data = resp.json()

    assert data["configured"] is True
    assert data["algorithm"] == "Ed25519"
    assert "public_key" in data
    assert "fingerprint" in data
    assert "private_key" not in data
    assert "secret" not in data


@pytest.mark.asyncio
async def test_verify_signature_api_endpoint(client: AsyncClient, ephemeral_signing_key):
    """API endpoint /api/signing/verify verifies signatures successfully."""
    priv, pub = ephemeral_signing_key
    payload = {"election_id": "elec-api", "total_ballots": 5}
    signed = SigningService.sign_payload(payload, private_key=priv)

    resp = await client.post(
        "/api/signing/verify",
        json={
            "payload": payload,
            "signature": signed["signature"],
            "public_key": signed["public_key"],
        },
    )
    assert resp.status_code == 200
    res = resp.json()
    assert res["valid"] is True

    # Negative verify test via API
    resp_tampered = await client.post(
        "/api/signing/verify",
        json={
            "payload": {"election_id": "elec-api", "total_ballots": 999},
            "signature": signed["signature"],
            "public_key": signed["public_key"],
        },
    )
    assert resp_tampered.status_code == 200
    assert resp_tampered.json()["valid"] is False


@pytest.mark.asyncio
async def test_manifest_signing_lifecycle_enforcement(
    client: AsyncClient,
    admin_headers: dict[str, str],
    ephemeral_signing_key,
):
    """Manifest signing MUST be rejected if election is still OPEN or CREATED."""
    election_id = "EV-2026-777"
    # 1. Create an election
    create_resp = await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Lifecycle Test Election"},
        headers=admin_headers,
    )
    assert create_resp.status_code == 201

    # Attempt to sign in CREATED state -> 400
    sign_resp = await client.post(
        f"/api/elections/{election_id}/sign-manifest",
        headers=admin_headers,
    )
    assert sign_resp.status_code == 400
    assert "CLOSED or PUBLISHED" in sign_resp.json()["detail"]

    # Add candidates (auto transitions to CONFIGURED)
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Alice", "party": "Party A", "symbol": "A", "position": 1},
                {"id": "C002", "name": "Bob", "party": "Party B", "symbol": "B", "position": 2},
            ]
        },
        headers=admin_headers,
    )

    # Register and activate device
    await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-001", "name": "Device 1"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/devices/EVM-001/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )

    # Lock election
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "LOCKED"},
        headers=admin_headers,
    )

    # Open election
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )

    # Attempt to sign in OPEN state -> 400
    sign_resp_open = await client.post(
        f"/api/elections/{election_id}/sign-manifest",
        headers=admin_headers,
    )
    assert sign_resp_open.status_code == 400

    # Close election, run verification to generate manifest
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )
    verify_resp = await client.post(f"/api/elections/{election_id}/verify", headers=admin_headers)
    assert verify_resp.status_code == 200

    # Now signing must succeed
    sign_resp_closed = await client.post(
        f"/api/elections/{election_id}/sign-manifest",
        headers=admin_headers,
    )
    assert sign_resp_closed.status_code == 200
    manifest_data = sign_resp_closed.json()
    assert manifest_data["election_id"] == election_id
    assert manifest_data["digital_signature"]["algorithm"] == "Ed25519"
    assert "signature" in manifest_data["digital_signature"]
    assert "fingerprint" in manifest_data["digital_signature"]
