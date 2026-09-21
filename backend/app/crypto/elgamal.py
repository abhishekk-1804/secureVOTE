"""
SecureVOTE 3.0 — Exponential ElGamal Encryption over NIST P-256.

Implements additive homomorphic encryption using the "Exponential ElGamal"
construction where messages are encoded as curve point exponents:

    Enc(m) = (r·G, r·Y + m·G)

where G is the generator, Y is the public key, and r is random.

Homomorphic property:
    Enc(m1) ⊕ Enc(m2) = (r1·G + r2·G, r1·Y + r2·Y + (m1+m2)·G) = Enc(m1 + m2)

Decryption recovers m·G, then brute-force discrete log recovers m.
This is efficient for small tallies (≤ 10,000 ballots).

Cryptographic Library: pyca/cryptography (NIST P-256 / secp256r1)

RESEARCH PROTOTYPE — NOT PRODUCTION ELECTION INFRASTRUCTURE.
"""

import os
from dataclasses import dataclass
from typing import Any, Optional

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

from app.crypto.exceptions import (
    AggregationError,
    DecryptionError,
    EncryptionError,
    InvalidCiphertextError,
    KeyGenerationError,
)

# ---------------------------------------------------------------------------
# Curve constants
# ---------------------------------------------------------------------------

CURVE = ec.SECP256R1()
CURVE_NAME = "secp256r1"

# The order of the secp256r1 generator point (number of points on the curve)
CURVE_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


# ---------------------------------------------------------------------------
# Low-level EC point arithmetic using pyca/cryptography
#
# pyca/cryptography does not expose raw point addition/scalar multiplication
# directly. We use the public numbers interface to perform arithmetic
# via Python integers over the secp256r1 field.
#
# For a research prototype this is appropriate. A production system would
# use a library with native point arithmetic (e.g., libsodium ristretto255).
# ---------------------------------------------------------------------------

# secp256r1 field prime
_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
# secp256r1 curve parameter a = -3
_A = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC
# secp256r1 curve parameter b
_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
# Generator point coordinates
_Gx = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
_Gy = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5


def _modinv(a: int, m: int) -> int:
    """Modular multiplicative inverse using Python's C-accelerated pow."""
    try:
        return pow(a, -1, m)
    except ValueError:
        raise ArithmeticError("Modular inverse does not exist")


@dataclass(frozen=True)
class ECPoint:
    """A point on the secp256r1 curve, or the point at infinity."""
    x: Optional[int]
    y: Optional[int]

    @property
    def is_infinity(self) -> bool:
        return self.x is None and self.y is None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ECPoint):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))


# Point at infinity (identity element)
INFINITY = ECPoint(None, None)

# Generator point
G = ECPoint(_Gx, _Gy)


def point_on_curve(p: Any) -> bool:
    """
    Verify that a point lies on the secp256r1 curve.

    Validates:
    - Object is an ECPoint instance
    - Point at infinity is considered on-curve (neutral element)
    - Affine coordinates x, y are non-boolean integers in [0, _P - 1]
    - Coordinates satisfy Weierstrass equation: y^2 = x^3 + a*x + b (mod P)
    """
    if not isinstance(p, ECPoint):
        return False
    if p.is_infinity:
        return True
    if p.x is None or p.y is None:
        return False
    if type(p.x) is not int or type(p.y) is not int:
        return False
    if not (0 <= p.x < _P and 0 <= p.y < _P):
        return False
    lhs = (p.y * p.y) % _P
    rhs = (p.x * p.x * p.x + _A * p.x + _B) % _P
    return lhs == rhs


def is_valid_public_point(p: Any) -> bool:
    """
    Validate that an EC point is a valid non-identity curve point.

    Appropriate for public keys, verification keys, commitments, and C1 components.
    """
    return isinstance(p, ECPoint) and not p.is_infinity and point_on_curve(p)


def is_valid_scalar(s: Any, allow_zero: bool = False) -> bool:
    """
    Validate that a scalar is an integer in the valid curve order range.

    If allow_zero is False (default for keys/nonces), scalar must be in [1, q - 1].
    If allow_zero is True, scalar must be in [0, q - 1].
    """
    if type(s) is not int:
        return False
    min_val = 0 if allow_zero else 1
    return min_val <= s < CURVE_ORDER


# ---------------------------------------------------------------------------
# Fast Jacobian coordinate arithmetic for secp256r1 (a = -3)
#
# RESEARCH PROTOTYPE TIMING LIMITATION NOTICE:
# This arithmetic implementation uses Python's arbitrary-precision integers
# and a standard double-and-add scalar multiplication loop.
# It is NOT constant-time.
#
# Sensitive operations involving private keys (x), secret shares (x_i), or
# ephemeral nonces (r, w) leak timing and branch patterns to local observers.
#
# In production election systems, all private-scalar elliptic curve operations
# MUST use constant-time primitives (e.g. Montgomery ladder, fixed-window
# comb, or audited C/Rust libraries such as libsodium / BoringSSL).
# This prototype is designed and intended strictly for educational research,
# algorithm simulation, and independent mathematical audit demonstration.
# ---------------------------------------------------------------------------

def _jacobian_double(X: int, Y: int, Z: int) -> tuple[int, int, int]:
    """Double a point in Jacobian coordinates."""
    if Y == 0 or Z == 0:
        return 0, 1, 0
    # a = -3 optimization: 3 * (X - Z^2) * (X + Z^2)
    Z2 = (Z * Z) % _P
    M = (3 * (X - Z2) * (X + Z2)) % _P
    Y2 = (Y * Y) % _P
    S = (4 * X * Y2) % _P
    X3 = (M * M - 2 * S) % _P
    Y3 = (M * (S - X3) - 8 * Y2 * Y2) % _P
    Z3 = (2 * Y * Z) % _P
    return X3, Y3, Z3


def _jacobian_add(X1: int, Y1: int, Z1: int, X2: int, Y2: int, Z2: int) -> tuple[int, int, int]:
    """Add two points in Jacobian coordinates."""
    if Z1 == 0:
        return X2, Y2, Z2
    if Z2 == 0:
        return X1, Y1, Z1
    Z1_2 = (Z1 * Z1) % _P
    Z2_2 = (Z2 * Z2) % _P
    U1 = (X1 * Z2_2) % _P
    U2 = (X2 * Z1_2) % _P
    S1 = (Y1 * Z2 * Z2_2) % _P
    S2 = (Y2 * Z1 * Z1_2) % _P
    if U1 == U2:
        if S1 != S2:
            return 0, 1, 0  # Infinity
        return _jacobian_double(X1, Y1, Z1)
    H = (U2 - U1) % _P
    R = (S2 - S1) % _P
    H2 = (H * H) % _P
    H3 = (H * H2) % _P
    U1H2 = (U1 * H2) % _P
    X3 = (R * R - H3 - 2 * U1H2) % _P
    Y3 = (R * (U1H2 - X3) - S1 * H3) % _P
    Z3 = (H * Z1 * Z2) % _P
    return X3, Y3, Z3


def _jacobian_to_affine(X: int, Y: int, Z: int) -> ECPoint:
    """Convert Jacobian coordinates (X, Y, Z) back to affine ECPoint."""
    if Z == 0:
        return INFINITY
    Z_inv = _modinv(Z, _P)
    Z_inv2 = (Z_inv * Z_inv) % _P
    Z_inv3 = (Z_inv * Z_inv2) % _P
    x = (X * Z_inv2) % _P
    y = (Y * Z_inv3) % _P
    return ECPoint(x, y)


def point_add(p1: ECPoint, p2: ECPoint) -> ECPoint:
    """Add two points on the secp256r1 curve."""
    if p1.is_infinity:
        return p2
    if p2.is_infinity:
        return p1
    assert p1.x is not None and p1.y is not None
    assert p2.x is not None and p2.y is not None

    X3, Y3, Z3 = _jacobian_add(p1.x, p1.y, 1, p2.x, p2.y, 1)
    return _jacobian_to_affine(X3, Y3, Z3)


def scalar_mult(k: int, p: ECPoint) -> ECPoint:
    """Scalar multiplication using fast Jacobian coordinates."""
    k = k % CURVE_ORDER
    if k == 0 or p.is_infinity:
        return INFINITY
    assert p.x is not None and p.y is not None

    # Double-and-add in Jacobian coordinates (zero modular inversions inside loop)
    # Result accumulator initialized to point at infinity (Z=0)
    RX, RY, RZ = 0, 1, 0
    AX, AY, AZ = p.x, p.y, 1

    while k > 0:
        if k & 1:
            RX, RY, RZ = _jacobian_add(RX, RY, RZ, AX, AY, AZ)
        AX, AY, AZ = _jacobian_double(AX, AY, AZ)
        k >>= 1

    return _jacobian_to_affine(RX, RY, RZ)


def point_negate(p: ECPoint) -> ECPoint:
    """Negate a point on the curve: -P = (x, -y mod p)."""
    if p.is_infinity:
        return INFINITY
    assert p.y is not None
    return ECPoint(p.x, (-p.y) % _P)


# ---------------------------------------------------------------------------
# ElGamal Key Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ElGamalPublicKey:
    """ElGamal public key: a point Y on secp256r1."""
    point: ECPoint

    def __post_init__(self):
        if not point_on_curve(self.point):
            raise KeyGenerationError("Public key point is not on the secp256r1 curve")
        if self.point.is_infinity:
            raise KeyGenerationError("Public key cannot be the point at infinity")


@dataclass(frozen=True)
class ElGamalPrivateKey:
    """ElGamal private key: a scalar x such that Y = x·G."""
    scalar: int
    public_key: ElGamalPublicKey

    def __post_init__(self):
        if not (1 <= self.scalar < CURVE_ORDER):
            raise KeyGenerationError("Private key scalar out of valid range")


# ---------------------------------------------------------------------------
# Ciphertext
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ElGamalCiphertext:
    """
    An ElGamal ciphertext: (C1, C2) where:
        C1 = r·G
        C2 = r·Y + m·G
    """
    c1: ECPoint
    c2: ECPoint

    def __post_init__(self):
        if not point_on_curve(self.c1):
            raise InvalidCiphertextError("C1 is not on the secp256r1 curve")
        if self.c1.is_infinity:
            raise InvalidCiphertextError("C1 cannot be the point at infinity")
        if not point_on_curve(self.c2):
            raise InvalidCiphertextError("C2 is not on the secp256r1 curve")


# ---------------------------------------------------------------------------
# Core Operations
# ---------------------------------------------------------------------------

def generate_keypair() -> ElGamalPrivateKey:
    """
    Generate a fresh ElGamal keypair using OS-provided cryptographic randomness.

    Returns an ElGamalPrivateKey (which contains the corresponding public key).
    """
    # Generate random scalar in [1, CURVE_ORDER-1]
    random_bytes = os.urandom(32)
    scalar = int.from_bytes(random_bytes, 'big') % (CURVE_ORDER - 1) + 1
    public_point = scalar_mult(scalar, G)
    pub = ElGamalPublicKey(point=public_point)
    return ElGamalPrivateKey(scalar=scalar, public_key=pub)


def encrypt_with_nonce(
    public_key: ElGamalPublicKey,
    message: int,
    r: Optional[int] = None,
) -> tuple[ElGamalCiphertext, int]:
    """
    Encrypt an integer message using Exponential ElGamal, returning (ciphertext, nonce).

    Args:
        public_key: The recipient's ElGamal public key.
        message: The integer to encrypt (typically 0 or 1 for one-hot encoding).
        r: Optional explicit random nonce in [1, CURVE_ORDER-1]. If None, sampled from os.urandom.

    Returns:
        A tuple of (ElGamalCiphertext, nonce integer).
    """
    if not isinstance(message, int):
        raise EncryptionError(f"Message must be an integer, got {type(message)}")

    if r is None:
        r_bytes = os.urandom(32)
        r = int.from_bytes(r_bytes, 'big') % (CURVE_ORDER - 1) + 1

    # C1 = r·G
    c1 = scalar_mult(r, G)

    # C2 = r·Y + m·G
    r_y = scalar_mult(r, public_key.point)
    m_g = scalar_mult(message, G)
    c2 = point_add(r_y, m_g)

    return ElGamalCiphertext(c1=c1, c2=c2), r


def encrypt(public_key: ElGamalPublicKey, message: int) -> ElGamalCiphertext:
    """
    Encrypt an integer message using Exponential ElGamal.

    The message is encoded as m·G (the message times the generator).
    Decryption recovers m·G, then brute-force discrete log recovers m.

    Args:
        public_key: The recipient's ElGamal public key.
        message: The integer to encrypt (typically 0 or 1 for one-hot encoding).

    Returns:
        An ElGamalCiphertext.
    """
    ct, _ = encrypt_with_nonce(public_key, message)
    return ct


def add_ciphertexts(ct1: ElGamalCiphertext, ct2: ElGamalCiphertext) -> ElGamalCiphertext:
    """
    Homomorphically add two ciphertexts.

    Enc(m1) ⊕ Enc(m2) = (C1_1 + C1_2, C2_1 + C2_2) = Enc(m1 + m2)
    """
    new_c1 = point_add(ct1.c1, ct2.c1)
    new_c2 = point_add(ct1.c2, ct2.c2)
    return ElGamalCiphertext(c1=new_c1, c2=new_c2)


def aggregate(ciphertexts: list[ElGamalCiphertext]) -> ElGamalCiphertext:
    """
    Homomorphically aggregate a list of ciphertexts.

    Returns Enc(sum of all plaintexts).

    Raises AggregationError if the list is empty.
    """
    if not ciphertexts:
        raise AggregationError("Cannot aggregate an empty list of ciphertexts")

    result = ciphertexts[0]
    for ct in ciphertexts[1:]:
        result = add_ciphertexts(result, ct)
    return result


def decrypt(private_key: ElGamalPrivateKey, ciphertext: ElGamalCiphertext,
            max_value: int = 10000) -> int:
    """
    Decrypt an Exponential ElGamal ciphertext.

    Recovers m·G = C2 - x·C1, then finds m by brute-force baby-step/giant-step.

    Args:
        private_key: The ElGamal private key.
        ciphertext: The ciphertext to decrypt.
        max_value: Maximum expected plaintext value (for discrete log search).

    Returns:
        The decrypted integer message.

    Raises:
        DecryptionError: If discrete log cannot be found within max_value range.
    """
    # Compute m·G = C2 - x·C1
    x_c1 = scalar_mult(private_key.scalar, ciphertext.c1)
    neg_x_c1 = point_negate(x_c1)
    m_g = point_add(ciphertext.c2, neg_x_c1)

    # Handle m = 0 (point at infinity)
    if m_g.is_infinity:
        return 0

    # Baby-step/giant-step to find m such that m·G = m_g
    return _baby_step_giant_step(m_g, max_value)


def _baby_step_giant_step(target: ECPoint, max_value: int) -> int:
    """
    Baby-step/giant-step algorithm to solve target = m·G for m in [0, max_value].

    Time: O(sqrt(max_value))
    Space: O(sqrt(max_value))
    """
    import math

    n = int(math.isqrt(max_value)) + 1

    # Baby steps: compute {j·G : j = 0, 1, ..., n-1}
    baby_steps: dict[tuple[Optional[int], Optional[int]], int] = {}
    current = INFINITY
    for j in range(n):
        baby_steps[(current.x, current.y)] = j
        current = point_add(current, G)

    # Giant step factor: -n·G
    neg_n_g = point_negate(scalar_mult(n, G))

    # Giant steps: check target - i·n·G for i = 0, 1, ...
    gamma = target
    for i in range(n):
        key = (gamma.x, gamma.y)
        if key in baby_steps:
            m = i * n + baby_steps[key]
            if m <= max_value:
                return m
        gamma = point_add(gamma, neg_n_g)

    # Also check negative values (for correctness with subtraction)
    # Try -m by checking if negate(target) matches
    neg_target = point_negate(target)
    if not neg_target.is_infinity:
        try:
            pos_m = _baby_step_giant_step_positive(neg_target, max_value)
            return -pos_m
        except DecryptionError:
            pass

    raise DecryptionError(
        f"Discrete log not found within range [0, {max_value}]. "
        f"The ciphertext may be corrupted or the tally exceeds max_value."
    )


def _baby_step_giant_step_positive(target: ECPoint, max_value: int) -> int:
    """Helper: find positive m such that target = m·G."""
    import math

    n = int(math.isqrt(max_value)) + 1
    baby_steps: dict[tuple[Optional[int], Optional[int]], int] = {}
    current = INFINITY
    for j in range(n):
        baby_steps[(current.x, current.y)] = j
        current = point_add(current, G)

    neg_n_g = point_negate(scalar_mult(n, G))
    gamma = target
    for i in range(n):
        key = (gamma.x, gamma.y)
        if key in baby_steps:
            m = i * n + baby_steps[key]
            if 1 <= m <= max_value:
                return m
        gamma = point_add(gamma, neg_n_g)

    raise DecryptionError("Positive discrete log not found")
