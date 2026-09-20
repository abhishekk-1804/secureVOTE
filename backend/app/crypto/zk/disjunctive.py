"""
Cramer-Damgård-Schoenmakers (CDS94) Disjunctive Zero-Knowledge Proof.

Proves that an Exponential ElGamal ciphertext Enc(v) = (A, B) encrypts either
v = 0 OR v = 1, without revealing which branch holds.
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
    WitnessError,
)
from app.crypto.zk.transcript import Transcript


@dataclass(frozen=True)
class Disjunctive01Proof:
    """
    CDS94 Disjunctive 0-or-1 Proof.

    Contains commitment pairs, challenge scalars, and response scalars
    for both branch 0 (v=0) and branch 1 (v=1).
    """
    a0: ECPoint
    b0: ECPoint
    a1: ECPoint
    b1: ECPoint
    c0: int
    c1: int
    s0: int
    s1: int

    def __post_init__(self):
        for pt in [self.a0, self.b0, self.a1, self.b1]:
            if not point_on_curve(pt):
                raise InvalidProofError("Commitment point not on secp256r1")
        for sc in [self.c0, self.c1, self.s0, self.s1]:
            if not (0 <= sc < CURVE_ORDER):
                raise InvalidProofError(f"Scalar {sc} out of valid group order range")


def prove_disjunctive_01(
    y_point: ECPoint,
    a_point: ECPoint,
    b_point: ECPoint,
    v_value: int,
    r_scalar: int,
    domain_prefix: str,
) -> Disjunctive01Proof:
    """
    Generate non-interactive CDS94 proof that (A, B) encrypts 0 or 1.

    Args:
        y_point: Public key point Y
        a_point: Ciphertext component A = r · G
        b_point: Ciphertext component B = r · Y + v · G
        v_value: The plaintext bit (must be 0 or 1)
        r_scalar: The secret randomness scalar r
        domain_prefix: Domain separation identifier
    """
    if v_value not in (0, 1):
        raise WitnessError(f"Disjunctive proof requires binary witness v in {{0, 1}}, got {v_value}")

    real = v_value
    sim = 1 - real

    # 1. Simulate the false branch (sim)
    # Pick random challenge c_sim and response s_sim in [1, q - 1]
    c_sim = int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1
    s_sim = int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1

    # Base points for simulated verification equations:
    # If sim == 0, B_sim' = B
    # If sim == 1, B_sim' = B - G
    b_sim_prime = b_point if sim == 0 else point_add(b_point, point_negate(G))

    # Compute simulated commitments:
    # a_sim = s_sim · G - c_sim · A
    # b_sim = s_sim · Y - c_sim · B_sim'
    a_sim = point_add(scalar_mult(s_sim, G), point_negate(scalar_mult(c_sim, a_point)))
    b_sim = point_add(scalar_mult(s_sim, y_point), point_negate(scalar_mult(c_sim, b_sim_prime)))

    # 2. Commit for the real branch (real)
    # Pick fresh blinding scalar w in [1, q - 1]
    w = int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1
    a_real = scalar_mult(w, G)
    b_real = scalar_mult(w, y_point)

    # Assign branch commitments
    if real == 0:
        a0, b0 = a_real, b_real
        a1, b1 = a_sim, b_sim
    else:
        a0, b0 = a_sim, b_sim
        a1, b1 = a_real, b_real

    # 3. Derive master Fiat-Shamir challenge c
    transcript = Transcript(domain=domain_prefix)
    transcript.append_point("public_key_Y", y_point)
    transcript.append_point("ciphertext_A", a_point)
    transcript.append_point("ciphertext_B", b_point)
    transcript.append_point("a0", a0)
    transcript.append_point("b0", b0)
    transcript.append_point("a1", a1)
    transcript.append_point("b1", b1)
    c_master = transcript.challenge_scalar("cds94_master_challenge")

    # 4. Compute real challenge: c_real = (c_master - c_sim) mod q
    c_real = (c_master - c_sim) % CURVE_ORDER

    # 5. Compute real response: s_real = (w + c_real * r) mod q
    s_real = (w + c_real * r_scalar) % CURVE_ORDER

    if real == 0:
        c0, s0 = c_real, s_real
        c1, s1 = c_sim, s_sim
    else:
        c0, s0 = c_sim, s_sim
        c1, s1 = c_real, s_real

    return Disjunctive01Proof(
        a0=a0, b0=b0,
        a1=a1, b1=b1,
        c0=c0, c1=c1,
        s0=s0, s1=s1,
    )


def verify_disjunctive_01(
    y_point: ECPoint,
    a_point: ECPoint,
    b_point: ECPoint,
    proof: Disjunctive01Proof,
    domain_prefix: str,
) -> bool:
    """
    Verify non-interactive CDS94 0-or-1 proof.

    Checks:
        1. c_master == (c0 + c1) mod q
        2. s0 · G == a0 + c0 · A
        3. s0 · Y == b0 + c0 · B
        4. s1 · G == a1 + c1 · A
        5. s1 · Y == b1 + c1 · (B - G)
    """
    # 1. Recompute master challenge
    transcript = Transcript(domain=domain_prefix)
    transcript.append_point("public_key_Y", y_point)
    transcript.append_point("ciphertext_A", a_point)
    transcript.append_point("ciphertext_B", b_point)
    transcript.append_point("a0", proof.a0)
    transcript.append_point("b0", proof.b0)
    transcript.append_point("a1", proof.a1)
    transcript.append_point("b1", proof.b1)
    c_master = transcript.challenge_scalar("cds94_master_challenge")

    # Check sum of challenges
    c_sum = (proof.c0 + proof.c1) % CURVE_ORDER
    if c_sum != c_master:
        raise ChallengeMismatchError(f"Challenge sum mismatch: (c0 + c1) mod q = {c_sum} != {c_master}")

    # 2. Branch 0 verification:
    # s0 · G == a0 + c0 · A
    lhs_g0 = scalar_mult(proof.s0, G)
    rhs_g0 = point_add(proof.a0, scalar_mult(proof.c0, a_point))
    if lhs_g0 != rhs_g0:
        raise EquationVerificationError("Disjunctive equation 0A (s0·G == a0 + c0·A) failed")

    # s0 · Y == b0 + c0 · B
    lhs_y0 = scalar_mult(proof.s0, y_point)
    rhs_y0 = point_add(proof.b0, scalar_mult(proof.c0, b_point))
    if lhs_y0 != rhs_y0:
        raise EquationVerificationError("Disjunctive equation 0B (s0·Y == b0 + c0·B) failed")

    # 3. Branch 1 verification:
    # s1 · G == a1 + c1 · A
    lhs_g1 = scalar_mult(proof.s1, G)
    rhs_g1 = point_add(proof.a1, scalar_mult(proof.c1, a_point))
    if lhs_g1 != rhs_g1:
        raise EquationVerificationError("Disjunctive equation 1A (s1·G == a1 + c1·A) failed")

    # s1 · Y == b1 + c1 · (B - G)
    b_minus_g = point_add(b_point, point_negate(G))
    lhs_y1 = scalar_mult(proof.s1, y_point)
    rhs_y1 = point_add(proof.b1, scalar_mult(proof.c1, b_minus_g))
    if lhs_y1 != rhs_y1:
        raise EquationVerificationError("Disjunctive equation 1B (s1·Y == b1 + c1·(B - G)) failed")

    return True
