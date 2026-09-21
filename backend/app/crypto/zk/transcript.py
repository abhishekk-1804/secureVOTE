"""
Fiat-Shamir Transcript Manager for SecureVOTE 3.1 & 3.3.

Computes non-interactive challenges via domain-separated hashing over
canonical representations of public parameters, ciphertexts, and proof commitments.

CRYPTOGRAPHIC ANALYSIS — HASH-TO-SCALAR BIAS:
- In `challenge_scalar`: A 256-bit SHA-256 digest is reduced modulo (q - 1), where
  q is the prime order of NIST P-256 (secp256r1), then offset by +1 to guarantee [1, q-1].
  Because 2^256 is not an exact multiple of (q - 1), this direct modular reduction introduces
  a statistical bias of Delta approx (2^256 mod (q - 1)) / 2^256 approx 2^-32.
  While practical for legacy compatibility and common in discrete-log proof implementations,
  this does not satisfy the Delta <= 2^-128 bound required by RFC 9380 / standard provable security.
- In `challenge_scalar_rfc9380`: Implements the RFC 9380 Section 5.3.1 `expand_message_xmd`
  construction with L = 48 bytes (384 bits). Reducing a 384-bit uniform byte string modulo (q - 1)
  guarantees a statistical distance of Delta <= 2^-128 from uniform distribution.
"""

import hashlib
from typing import Any, Optional

from app.crypto.canonical import canonical_json
from app.crypto.elgamal import CURVE_ORDER, ECPoint


def expand_message_xmd(
    msg: bytes,
    dst: bytes,
    len_in_bytes: int = 48,
    hash_fn=hashlib.sha256,
) -> bytes:
    """
    RFC 9380 Section 5.3.1 expand_message_xmd using SHA-256.

    Produces `len_in_bytes` pseudorandom bytes from `msg` and domain separation tag `dst`.
    For secp256r1 scalar derivation, len_in_bytes=48 (384 bits) achieves statistical
    distance Delta <= 2^-128 modulo the 256-bit curve order q.
    """
    b_in_bytes = 32  # SHA-256 output size
    s_in_bytes = 64  # SHA-256 block size

    ell = (len_in_bytes + b_in_bytes - 1) // b_in_bytes
    if ell > 255 or len_in_bytes > 65535 or len_in_bytes <= 0:
        raise ValueError(f"Invalid len_in_bytes: {len_in_bytes} (ell must be 1..255)")

    if len(dst) > 255:
        dst_prime = hash_fn(b"H2C-OVERSIZE-DST-" + dst).digest() + bytes([32])
    elif len(dst) == 0:
        raise ValueError("Domain separation tag (DST) must not be empty")
    else:
        dst_prime = dst + bytes([len(dst)])

    z_pad = bytes(s_in_bytes)
    lib_str = len_in_bytes.to_bytes(2, "big")
    b_0 = hash_fn(z_pad + msg + lib_str + b"\x00" + dst_prime).digest()
    b_1 = hash_fn(b_0 + b"\x01" + dst_prime).digest()

    blocks = [b_1]
    for i in range(2, ell + 1):
        strxor = bytes(x ^ y for x, y in zip(b_0, blocks[-1]))
        b_i = hash_fn(strxor + bytes([i]) + dst_prime).digest()
        blocks.append(b_i)

    return b"".join(blocks)[:len_in_bytes]


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
        if not isinstance(pt, ECPoint):
            raise TypeError(f"Expected ECPoint, got {type(pt).__name__}")
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

        NOTE ON STATISTICAL BIAS:
        Reduces 256-bit SHA-256 output modulo (q - 1). This has statistical bias
        approx 2^-32. Retained for exact protocol backward compatibility with
        v3.1, v3.2, and v3.3 release baselines.
        For bias < 2^-128, use `challenge_scalar_rfc9380`.
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

    def challenge_scalar_rfc9380(
        self,
        label: str = "challenge",
        dst: Optional[bytes] = None,
    ) -> int:
        """
        Derive a challenge scalar c in [1, q - 1] via RFC 9380 expand_message_xmd.

        Uses L = 48 bytes (384 bits) of expanded output to achieve statistical
        distance Delta <= 2^-128 modulo (q - 1).
        """
        payload = {
            "domain": self.domain,
            "label": label,
            "transcript": self._entries,
        }
        msg = canonical_json(payload).encode("utf-8")
        if dst is None:
            dst = f"{self.domain}/RFC9380/XMD:SHA-256".encode("utf-8")
        expanded = expand_message_xmd(msg=msg, dst=dst, len_in_bytes=48)
        scalar = int.from_bytes(expanded, "big") % (CURVE_ORDER - 1) + 1
        return scalar
