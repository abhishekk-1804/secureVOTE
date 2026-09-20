"""
SecureVOTE 3.0 — Key Management.

Handles ElGamal key generation, serialization, deserialization,
and key fingerprinting. Private keys are NEVER serialized to
public-facing formats.

Key Fingerprints use domain-separated SHA-256:
    SHA-256("SECUREVOTE3/KEY/" || public_key_hex)
"""

import hashlib
from typing import Any, Optional

from app.crypto import PROTOCOL_VERSION
from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    ElGamalPrivateKey,
    ElGamalPublicKey,
    G,
    generate_keypair,
    point_on_curve,
    scalar_mult,
)
from app.crypto.exceptions import KeyGenerationError, SerializationError


# ---------------------------------------------------------------------------
# Key Fingerprinting
# ---------------------------------------------------------------------------

def compute_key_fingerprint(public_key: ElGamalPublicKey) -> str:
    """
    Compute a domain-separated SHA-256 fingerprint of the public key.

    Format: SHA-256("SECUREVOTE3/KEY/" + hex(x) + ":" + hex(y))
    """
    assert public_key.point.x is not None and public_key.point.y is not None
    key_material = f"{public_key.point.x:064x}:{public_key.point.y:064x}"
    domain = f"{PROTOCOL_VERSION}/KEY/{key_material}"
    return hashlib.sha256(domain.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Key Serialization (Public Keys Only)
# ---------------------------------------------------------------------------

def serialize_public_key(public_key: ElGamalPublicKey) -> dict[str, Any]:
    """
    Serialize a public key to a JSON-safe dictionary.

    Private keys are NEVER included in serialized output.
    """
    assert public_key.point.x is not None and public_key.point.y is not None
    return {
        "protocol_version": PROTOCOL_VERSION,
        "curve": "secp256r1",
        "x": f"{public_key.point.x:064x}",
        "y": f"{public_key.point.y:064x}",
        "fingerprint": compute_key_fingerprint(public_key),
    }


def deserialize_public_key(data: dict[str, Any]) -> ElGamalPublicKey:
    """
    Deserialize a public key from a JSON dictionary.

    Validates:
    1. Protocol version
    2. Curve name
    3. Point is on curve
    4. Point is not infinity
    5. Fingerprint matches
    """
    if data.get("protocol_version") != PROTOCOL_VERSION:
        raise SerializationError(
            f"Protocol version mismatch: expected {PROTOCOL_VERSION}, "
            f"got {data.get('protocol_version')}"
        )

    if data.get("curve") != "secp256r1":
        raise SerializationError(
            f"Unsupported curve: {data.get('curve')}"
        )

    try:
        x = int(data["x"], 16)
        y = int(data["y"], 16)
    except (KeyError, ValueError) as e:
        raise SerializationError(f"Invalid public key coordinates: {e}")

    point = ECPoint(x, y)
    if not point_on_curve(point):
        raise SerializationError("Deserialized point is not on the secp256r1 curve")

    pub = ElGamalPublicKey(point=point)

    # Verify fingerprint
    expected_fp = compute_key_fingerprint(pub)
    if data.get("fingerprint") and data["fingerprint"] != expected_fp:
        raise SerializationError(
            f"Key fingerprint mismatch: expected {expected_fp}, "
            f"got {data['fingerprint']}"
        )

    return pub


# ---------------------------------------------------------------------------
# Key Metadata
# ---------------------------------------------------------------------------

def create_key_metadata(
    private_key: ElGamalPrivateKey,
    election_id: str,
    key_id: str,
) -> dict[str, Any]:
    """
    Create key metadata for a v3 election.

    The private key scalar is NOT included — only the public key and
    fingerprint are stored.
    """
    return {
        "key_id": key_id,
        "election_id": election_id,
        "protocol_version": PROTOCOL_VERSION,
        "public_key": serialize_public_key(private_key.public_key),
        "fingerprint": compute_key_fingerprint(private_key.public_key),
        "key_type": "ELGAMAL_SECP256R1",
        "status": "ACTIVE",
    }
