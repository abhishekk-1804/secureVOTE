"""
Chaum-Pedersen Zero-Knowledge Proof of Discrete-Log Equality.

Given points (G, Y, A, B'), proves knowledge of scalar r such that:
    A = r · G   AND   B' = r · Y
without revealing r.
"""

import os
from dataclasses import dataclass

from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    G,
    point_add,
    point_negate,
    point_on_curve,
    scalar_mult,
)
from app.crypto.zk.exceptions import (
    ChallengeMismatchError,
    EquationVerificationError,
    InvalidProofError,
)
from app.crypto.zk.transcript import Transcript


@dataclass(frozen=True)
class ChaumPedersenProof:
    """
    Chaum-Pedersen proof tuple:
        a: blinding commitment a = w · G
        b: blinding commitment b = w · Y
        c: Fiat-Shamir challenge scalar
        s: response scalar s = (w + c · r) mod q
    """
    a: ECPoint
    b: ECPoint
    c: int
    s: int

    def __post_init__(self):
        if not point_on_curve(self.a) or not point_on_curve(self.b):
            raise InvalidProofError("Proof commitment points not on secp256r1")
        if not (1 <= self.c < CURVE_ORDER):
            raise InvalidProofError("Proof challenge scalar out of valid range")
        if not (0 <= self.s < CURVE_ORDER):
            raise InvalidProofError("Proof response scalar out of valid range")


def prove_equality(
    y_point: ECPoint,
    a_point: ECPoint,
    b_prime_point: ECPoint,
    r_scalar: int,
    domain_prefix: str,
) -> ChaumPedersenProof:
    """
    Generate non-interactive Chaum-Pedersen proof that A = r·G and B' = r·Y.

    Args:
        y_point: Public key point Y
        a_point: Point A = r·G
        b_prime_point: Point B' = r·Y
        r_scalar: The secret nonce scalar r
        domain_prefix: Unique domain string for transcript separation
    """
    # 1. Sample fresh random blinding scalar w in [1, q - 1]
    w = int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1

    # 2. Compute commitment points
    comm_a = scalar_mult(w, G)
    comm_b = scalar_mult(w, y_point)

    # 3. Derive challenge c via Fiat-Shamir transcript
    transcript = Transcript(domain=domain_prefix)
    transcript.append_point("public_key_Y", y_point)
    transcript.append_point("ciphertext_A", a_point)
    transcript.append_point("ciphertext_B_prime", b_prime_point)
    transcript.append_point("commitment_a", comm_a)
    transcript.append_point("commitment_b", comm_b)
    c = transcript.challenge_scalar("chaum_pedersen_challenge")

    # 4. Compute response scalar s = (w + c * r) mod q
    s = (w + c * r_scalar) % CURVE_ORDER

    return ChaumPedersenProof(a=comm_a, b=comm_b, c=c, s=s)


def verify_equality(
    y_point: ECPoint,
    a_point: ECPoint,
    b_prime_point: ECPoint,
    proof: ChaumPedersenProof,
    domain_prefix: str,
) -> bool:
    """
    Verify non-interactive Chaum-Pedersen proof.

    Checks:
        1. c == Hash(domain || Y || A || B' || a || b)
        2. s · G == a + c · A
        3. s · Y == b + c · B'
    """
    # 1. Recompute challenge
    transcript = Transcript(domain=domain_prefix)
    transcript.append_point("public_key_Y", y_point)
    transcript.append_point("ciphertext_A", a_point)
    transcript.append_point("ciphertext_B_prime", b_prime_point)
    transcript.append_point("commitment_a", proof.a)
    transcript.append_point("commitment_b", proof.b)
    expected_c = transcript.challenge_scalar("chaum_pedersen_challenge")

    if proof.c != expected_c:
        raise ChallengeMismatchError(f"Fiat-Shamir challenge mismatch: {proof.c} != {expected_c}")

    # 2. Verify equation 1: s · G == a + c · A
    lhs1 = scalar_mult(proof.s, G)
    rhs1 = point_add(proof.a, scalar_mult(proof.c, a_point))
    if lhs1 != rhs1:
        raise EquationVerificationError("Chaum-Pedersen equation 1 (s·G == a + c·A) failed")

    # 3. Verify equation 2: s · Y == b + c · B'
    lhs2 = scalar_mult(proof.s, y_point)
    rhs2 = point_add(proof.b, scalar_mult(proof.c, b_prime_point))
    if lhs2 != rhs2:
        raise EquationVerificationError("Chaum-Pedersen equation 2 (s·Y == b + c·B') failed")

    return True
