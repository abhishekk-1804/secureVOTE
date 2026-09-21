"""
SecureVOTE 3.2 — Chaum-Pedersen Discrete-Log Equality Proofs for Partial Decryption.

Implements non-interactive zero-knowledge proofs demonstrating that a partial decryption
point W_{i,j} was correctly derived from an aggregated ciphertext component A_j
using the trustee's private share x_i, without revealing x_i.

Relation:
    log_G(Y_i) == log_{A_j}(W_{i,j}) == x_i
"""

import secrets
from dataclasses import dataclass
from typing import Optional

from app.crypto.elgamal import (
    CURVE_ORDER,
    G,
    INFINITY,
    ECPoint,
    point_add,
    point_on_curve,
    scalar_mult,
)
from app.crypto.threshold.exceptions import (
    InvalidShareError,
    PartialDecryptionProofError,
)
from app.crypto.zk.transcript import Transcript

DEFAULT_PROTOCOL_VERSION = "SECUREVOTE32"


@dataclass(frozen=True)
class ChaumPedersenEqualityProof:
    """
    Non-interactive zero-knowledge proof of equality of discrete logarithms.

    Proves:
        log_G(Y_i) == log_{A_j}(W_{i,j})

    Attributes:
        comm_1: w * G
        comm_2: w * A_j
        c: Fiat-Shamir challenge scalar in [1, q-1]
        s: Response scalar (w + c * x_i) mod q
    """
    comm_1: ECPoint
    comm_2: ECPoint
    c: int
    s: int

    def __repr__(self) -> str:
        return (
            f"ChaumPedersenEqualityProof(comm_1={self.comm_1}, comm_2={self.comm_2}, "
            f"c={hex(self.c)[:10]}..., s={hex(self.s)[:10]}...)"
        )


# Type alias for clarity in threshold decryption context
PartialDecryptionProof = ChaumPedersenEqualityProof


def build_partial_decrypt_transcript(
    y_point: ECPoint,
    a_point: ECPoint,
    w_point: ECPoint,
    comm_1: ECPoint,
    comm_2: ECPoint,
    election_id: str,
    candidate_id: str,
    trustee_id: int,
    protocol_version: str = DEFAULT_PROTOCOL_VERSION,
) -> Transcript:
    """
    Construct the canonical domain-separated Fiat-Shamir transcript for partial decryption.
    """
    domain = f"SECUREVOTE32/ZKP/PARTIAL_DECRYPT/{election_id}/{candidate_id}/TRUSTEE/{trustee_id}/"
    transcript = Transcript(domain=domain)
    transcript.append_message("protocol_version", protocol_version)
    transcript.append_message("election_id", election_id)
    transcript.append_message("candidate_id", candidate_id)
    transcript.append_message("trustee_id", trustee_id)
    transcript.append_point("generator_G", G)
    transcript.append_point("verification_key_Y", y_point)
    transcript.append_point("ciphertext_A", a_point)
    transcript.append_point("partial_decryption_W", w_point)
    transcript.append_point("comm_1", comm_1)
    transcript.append_point("comm_2", comm_2)
    return transcript


def prove_partial_decryption(
    x_i: int,
    y_point: ECPoint,
    a_point: ECPoint,
    w_point: ECPoint,
    election_id: str,
    candidate_id: str,
    trustee_id: int,
    protocol_version: str = DEFAULT_PROTOCOL_VERSION,
) -> ChaumPedersenEqualityProof:
    """
    Generate a non-interactive Chaum-Pedersen proof of discrete log equality.

    Proves:
        Y_i = x_i * G  and  W_{i,j} = x_i * A_j

    Args:
        x_i: Trustee private key share scalar in [1, q-1]
        y_point: Trustee public verification key Y_i
        a_point: Aggregated ciphertext component A_j
        w_point: Partial decryption share W_{i,j} = x_i * A_j
        election_id: Unique election identifier
        candidate_id: Candidate identifier for the slot
        trustee_id: Integer trustee identifier
        protocol_version: Protocol domain version string

    Returns:
        ChaumPedersenEqualityProof instance containing (comm_1, comm_2, c, s)

    Raises:
        InvalidShareError: If inputs are malformed, off-curve, or inconsistent.
    """
    if not isinstance(x_i, int) or not (1 <= x_i < CURVE_ORDER):
        raise InvalidShareError("Secret share scalar x_i must be in [1, q-1]")

    if not point_on_curve(y_point) or y_point.is_infinity:
        raise InvalidShareError("Verification key Y_i is off-curve or at infinity")

    if not point_on_curve(a_point) or a_point.is_infinity:
        raise InvalidShareError("Ciphertext point A_j is off-curve or at infinity")

    if not point_on_curve(w_point) or w_point.is_infinity:
        raise InvalidShareError("Partial decryption point W is off-curve or at infinity")

    # Verify input consistency before proving
    if scalar_mult(x_i, G) != y_point:
        raise InvalidShareError("Provided verification key Y_i does not match x_i * G")

    if scalar_mult(x_i, a_point) != w_point:
        raise InvalidShareError("Provided partial decryption W does not match x_i * A_j")

    # 1. Sample ephemeral nonce w in [1, q-1]
    w = secrets.randbits(256) % (CURVE_ORDER - 1) + 1

    try:
        # 2. Compute commitments
        comm_1 = scalar_mult(w, G)
        comm_2 = scalar_mult(w, a_point)

        # 3. Derive Fiat-Shamir challenge
        transcript = build_partial_decrypt_transcript(
            y_point=y_point,
            a_point=a_point,
            w_point=w_point,
            comm_1=comm_1,
            comm_2=comm_2,
            election_id=election_id,
            candidate_id=candidate_id,
            trustee_id=trustee_id,
            protocol_version=protocol_version,
        )
        c = transcript.challenge_scalar("partial_decrypt_challenge")

        # 4. Compute response scalar s = (w + c * x_i) mod q
        s = (w + c * x_i) % CURVE_ORDER

        return ChaumPedersenEqualityProof(
            comm_1=comm_1,
            comm_2=comm_2,
            c=c,
            s=s,
        )
    finally:
        # Ephemeral nonce hygiene: clear local variable reference.
        # Python-level memory zeroization is not claimed.
        # The nonce w is not serialized, persisted, logged, or returned.
        w = 0


def verify_partial_decryption_proof(
    proof: ChaumPedersenEqualityProof,
    y_point: ECPoint,
    a_point: ECPoint,
    w_point: ECPoint,
    election_id: str,
    candidate_id: str,
    trustee_id: int,
    protocol_version: str = DEFAULT_PROTOCOL_VERSION,
) -> bool:
    """
    Verify a non-interactive Chaum-Pedersen proof of discrete log equality.

    Verifies:
        1. All points are on NIST P-256 and not at infinity.
        2. Challenge c matches canonical Fiat-Shamir transcript.
        3. s * G == comm_1 + c * Y_i
        4. s * A_j == comm_2 + c * W_{i,j}

    Returns:
        True if all equations hold, False otherwise.
    """
    try:
        check_partial_decryption_proof(
            proof=proof,
            y_point=y_point,
            a_point=a_point,
            w_point=w_point,
            election_id=election_id,
            candidate_id=candidate_id,
            trustee_id=trustee_id,
            protocol_version=protocol_version,
        )
        return True
    except (PartialDecryptionProofError, InvalidShareError, Exception):
        return False


def check_partial_decryption_proof(
    proof: ChaumPedersenEqualityProof,
    y_point: ECPoint,
    a_point: ECPoint,
    w_point: ECPoint,
    election_id: str,
    candidate_id: str,
    trustee_id: int,
    protocol_version: str = DEFAULT_PROTOCOL_VERSION,
) -> None:
    """
    Strict verifier for Chaum-Pedersen partial decryption proofs.
    Raises PartialDecryptionProofError on any failure.
    """
    if not isinstance(proof, ChaumPedersenEqualityProof):
        raise PartialDecryptionProofError("Invalid proof object type")

    # 1. Point validity and infinity checks
    if not point_on_curve(y_point) or y_point.is_infinity:
        raise PartialDecryptionProofError("Verification key Y_i is off-curve or at infinity")

    if not point_on_curve(a_point) or a_point.is_infinity:
        raise PartialDecryptionProofError("Ciphertext point A_j is off-curve or at infinity")

    if not point_on_curve(w_point) or w_point.is_infinity:
        raise PartialDecryptionProofError("Partial decryption point W is off-curve or at infinity")

    if not point_on_curve(proof.comm_1) or proof.comm_1.is_infinity:
        raise PartialDecryptionProofError("Commitment comm_1 is off-curve or at infinity")

    if not point_on_curve(proof.comm_2) or proof.comm_2.is_infinity:
        raise PartialDecryptionProofError("Commitment comm_2 is off-curve or at infinity")

    # 2. Scalar range checks
    if not isinstance(proof.c, int) or type(proof.c) is not int or not (1 <= proof.c < CURVE_ORDER):
        raise PartialDecryptionProofError(f"Challenge c is out of valid range [1, q-1]: {proof.c}")

    if not isinstance(proof.s, int) or type(proof.s) is not int or not (0 <= proof.s < CURVE_ORDER):
        raise PartialDecryptionProofError(f"Response scalar s is out of valid range [0, q-1]: {proof.s}")

    # 3. Fiat-Shamir challenge reconstruction
    transcript = build_partial_decrypt_transcript(
        y_point=y_point,
        a_point=a_point,
        w_point=w_point,
        comm_1=proof.comm_1,
        comm_2=proof.comm_2,
        election_id=election_id,
        candidate_id=candidate_id,
        trustee_id=trustee_id,
        protocol_version=protocol_version,
    )
    expected_c = transcript.challenge_scalar("partial_decrypt_challenge")

    if proof.c != expected_c:
        raise PartialDecryptionProofError(
            f"Fiat-Shamir challenge mismatch: provided {proof.c} != computed {expected_c}"
        )

    # 4. Equation 1: s * G == comm_1 + c * Y_i
    lhs_1 = scalar_mult(proof.s, G)
    rhs_1 = point_add(proof.comm_1, scalar_mult(proof.c, y_point))
    if lhs_1 != rhs_1:
        raise PartialDecryptionProofError("Verification equation 1 (s*G == comm_1 + c*Y_i) failed")

    # 5. Equation 2: s * A_j == comm_2 + c * W_{i,j}
    lhs_2 = scalar_mult(proof.s, a_point)
    rhs_2 = point_add(proof.comm_2, scalar_mult(proof.c, w_point))
    if lhs_2 != rhs_2:
        raise PartialDecryptionProofError("Verification equation 2 (s*A_j == comm_2 + c*W_{i,j}) failed")
