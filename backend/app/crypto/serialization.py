"""
SecureVOTE 3.0 — Ciphertext Serialization.

Handles conversion of ElGamal ciphertexts, public keys, and other
cryptographic objects to/from JSON-safe dictionaries.
"""

from typing import Any, Optional

from app.crypto import PROTOCOL_VERSION
from app.crypto.elgamal import (
    ECPoint,
    ElGamalCiphertext,
    ElGamalPublicKey,
    INFINITY,
    point_on_curve,
)
from app.crypto.exceptions import InvalidCiphertextError, SerializationError


def serialize_point(p: ECPoint) -> dict[str, str]:
    """Serialize an EC point to a JSON-safe dictionary."""
    if p.is_infinity:
        return {"x": "infinity", "y": "infinity"}
    assert p.x is not None and p.y is not None
    return {
        "x": f"{p.x:064x}",
        "y": f"{p.y:064x}",
    }


def deserialize_point(data: dict[str, str]) -> ECPoint:
    """Deserialize an EC point from a JSON dictionary."""
    if data.get("x") == "infinity":
        return INFINITY
    try:
        x = int(data["x"], 16)
        y = int(data["y"], 16)
    except (KeyError, ValueError) as e:
        raise SerializationError(f"Invalid point coordinates: {e}")

    point = ECPoint(x, y)
    if not point_on_curve(point):
        raise InvalidCiphertextError("Deserialized point is not on the secp256r1 curve")
    return point


def serialize_ciphertext(ct: ElGamalCiphertext) -> dict[str, Any]:
    """Serialize an ElGamal ciphertext to a JSON-safe dictionary."""
    return {
        "c1": serialize_point(ct.c1),
        "c2": serialize_point(ct.c2),
        "curve": "secp256r1",
        "protocol_version": PROTOCOL_VERSION,
    }


def deserialize_ciphertext(data: dict[str, Any]) -> ElGamalCiphertext:
    """
    Deserialize an ElGamal ciphertext from a JSON dictionary.

    Validates protocol version, curve, and point-on-curve.
    """
    if data.get("protocol_version") != PROTOCOL_VERSION:
        raise SerializationError(
            f"Protocol version mismatch: expected {PROTOCOL_VERSION}, "
            f"got {data.get('protocol_version')}"
        )
    if data.get("curve") != "secp256r1":
        raise SerializationError(f"Unsupported curve: {data.get('curve')}")

    c1 = deserialize_point(data["c1"])
    c2 = deserialize_point(data["c2"])
    return ElGamalCiphertext(c1=c1, c2=c2)
