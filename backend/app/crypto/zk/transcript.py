"""
Fiat-Shamir Transcript Manager for SecureVOTE 3.1.

Computes non-interactive challenges via domain-separated SHA-256 hashing over
canonical representations of public parameters, ciphertexts, and proof commitments.
"""

import hashlib
from typing import Any, Optional

from app.crypto.canonical import canonical_json
from app.crypto.elgamal import CURVE_ORDER, ECPoint


class Transcript:
    """
    Fiat-Shamir transcript manager.

    Accumulates protocol elements and derives deterministic scalar challenges
    reduced modulo the secp256r1 group order q.
    """

    def __init__(self, domain: str):
        self.domain = domain
        self._entries: list[dict[str, Any]] = []

    def append_message(self, label: str, data: Any) -> None:
        """Append a labeled data field to the transcript."""
        self._entries.append({
            "label": label,
            "data": data,
        })

    def append_point(self, label: str, pt: ECPoint) -> None:
        """Append an elliptic curve point to the transcript."""
        if pt.is_infinity:
            pt_dict = {"x": "infinity", "y": "infinity"}
        else:
            pt_dict = {
                "x": f"{pt.x:064x}",
                "y": f"{pt.y:064x}",
            }
        self.append_message(label, pt_dict)

    def challenge_scalar(self, label: str = "challenge") -> int:
        """
        Derive a challenge scalar c in [1, q - 1] via domain-separated SHA-256.
        """
        payload = {
            "domain": self.domain,
            "label": label,
            "transcript": self._entries,
        }
        encoded = canonical_json(payload).encode("utf-8")
        digest = hashlib.sha256(encoded).digest()
        scalar = int.from_bytes(digest, "big") % (CURVE_ORDER - 1) + 1
        return scalar
