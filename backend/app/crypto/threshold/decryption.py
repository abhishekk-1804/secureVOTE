"""
SecureVOTE 3.2 — Verifiable Partial Decryption Layer.

Implements partial decryption share computation and verification for threshold ElGamal.
Each trustee evaluates W_{i,j} = x_i * A_j for candidate slot j and generates a
Chaum-Pedersen proof demonstrating discrete-log equality with their public verification key Y_i.
"""

from dataclasses import dataclass
from typing import Optional

from app.crypto.elgamal import ECPoint, point_on_curve, scalar_mult
from app.crypto.threshold.dkg import TrusteePrivateKeyShare
from app.crypto.threshold.exceptions import (
    InvalidShareError,
    PartialDecryptionProofError,
)
from app.crypto.threshold.proof import (
    DEFAULT_PROTOCOL_VERSION,
    ChaumPedersenEqualityProof,
    check_partial_decryption_proof,
    prove_partial_decryption,
    verify_partial_decryption_proof,
)


@dataclass(frozen=True)
class PartialDecryptionShare:
    """
    Public partial decryption share for a single candidate slot.

    Attributes:
        election_id: Identifier of the election
        candidate_id: Candidate or contest identifier
        trustee_id: Integer trustee identifier (1-indexed)
        partial_decryption: Elliptic curve point W_{i,j} = x_i * A_j
        proof: Chaum-Pedersen discrete-log equality proof
        protocol_version: Protocol version string
    """
    election_id: str
    candidate_id: str
    trustee_id: int
    partial_decryption: ECPoint
    proof: ChaumPedersenEqualityProof
    protocol_version: str = DEFAULT_PROTOCOL_VERSION

    def __repr__(self) -> str:
        return (
            f"PartialDecryptionShare(election={self.election_id}, candidate={self.candidate_id}, "
            f"trustee={self.trustee_id}, W=({hex(self.partial_decryption.x)[:10]}..., "
            f"{hex(self.partial_decryption.y)[:10]}...))"
        )


@dataclass(frozen=True)
class TallyPartialDecryptionPackage:
    """
    Collection of partial decryptions published by a trustee for all candidates in an election.
    """
    election_id: str
    trustee_id: int
    shares: dict[str, PartialDecryptionShare]
    protocol_version: str = DEFAULT_PROTOCOL_VERSION


def compute_partial_decryption(
    trustee_share: TrusteePrivateKeyShare,
    candidate_id: str,
    a_point: ECPoint,
    protocol_version: str = DEFAULT_PROTOCOL_VERSION,
) -> PartialDecryptionShare:
    """
    Compute a verifiable partial decryption share W_{i,j} = x_i * A_j and accompanying ZK proof.

    Args:
        trustee_share: Private key share held by the trustee
        candidate_id: Identifier of the candidate slot
        a_point: Aggregated ciphertext component A_j = R_j * G
        protocol_version: Domain protocol version string

    Returns:
        PartialDecryptionShare containing W_{i,j} and Chaum-Pedersen proof.
    """
    if not point_on_curve(a_point) or a_point.is_infinity:
        raise InvalidShareError("Aggregated ciphertext point A_j is off-curve or at infinity")

    # W_{i,j} = x_i * A_j
    w_point = scalar_mult(trustee_share.secret_share, a_point)

    # Generate Chaum-Pedersen equality proof
    proof = prove_partial_decryption(
        x_i=trustee_share.secret_share,
        y_point=trustee_share.verification_key,
        a_point=a_point,
        w_point=w_point,
        election_id=trustee_share.election_id,
        candidate_id=candidate_id,
        trustee_id=trustee_share.trustee_id,
        protocol_version=protocol_version,
    )

    return PartialDecryptionShare(
        election_id=trustee_share.election_id,
        candidate_id=candidate_id,
        trustee_id=trustee_share.trustee_id,
        partial_decryption=w_point,
        proof=proof,
        protocol_version=protocol_version,
    )


def verify_partial_decryption_share(
    share: PartialDecryptionShare,
    verification_key: ECPoint,
    a_point: ECPoint,
    expected_election_id: Optional[str] = None,
    expected_candidate_id: Optional[str] = None,
    expected_trustee_id: Optional[int] = None,
) -> bool:
    """
    Verify a partial decryption share against a candidate's ciphertext point A_j
    and trustee's public verification key Y_i.

    Returns:
        True if all checks and proof equations succeed, False otherwise.
    """
    if expected_election_id is not None and share.election_id != expected_election_id:
        return False
    if expected_candidate_id is not None and share.candidate_id != expected_candidate_id:
        return False
    if expected_trustee_id is not None and share.trustee_id != expected_trustee_id:
        return False

    return verify_partial_decryption_proof(
        proof=share.proof,
        y_point=verification_key,
        a_point=a_point,
        w_point=share.partial_decryption,
        election_id=share.election_id,
        candidate_id=share.candidate_id,
        trustee_id=share.trustee_id,
        protocol_version=share.protocol_version,
    )


def compute_tally_partial_decryptions(
    trustee_share: TrusteePrivateKeyShare,
    candidate_a_points: dict[str, ECPoint],
    protocol_version: str = DEFAULT_PROTOCOL_VERSION,
) -> TallyPartialDecryptionPackage:
    """
    Compute partial decryptions for all candidates in an election tally.
    """
    shares = {}
    for cand_id, a_pt in candidate_a_points.items():
        shares[cand_id] = compute_partial_decryption(
            trustee_share=trustee_share,
            candidate_id=cand_id,
            a_point=a_pt,
            protocol_version=protocol_version,
        )

    return TallyPartialDecryptionPackage(
        election_id=trustee_share.election_id,
        trustee_id=trustee_share.trustee_id,
        shares=shares,
        protocol_version=protocol_version,
    )


def verify_tally_partial_decryption_package(
    package: TallyPartialDecryptionPackage,
    verification_key: ECPoint,
    candidate_a_points: dict[str, ECPoint],
    expected_election_id: Optional[str] = None,
    expected_trustee_id: Optional[int] = None,
) -> bool:
    """
    Verify all candidate shares in a trustee's partial decryption package.
    """
    if expected_election_id is not None and package.election_id != expected_election_id:
        return False
    if expected_trustee_id is not None and package.trustee_id != expected_trustee_id:
        return False

    if set(package.shares.keys()) != set(candidate_a_points.keys()):
        return False

    for cand_id, share in package.shares.items():
        a_pt = candidate_a_points[cand_id]
        if not verify_partial_decryption_share(
            share=share,
            verification_key=verification_key,
            a_point=a_pt,
            expected_election_id=package.election_id,
            expected_candidate_id=cand_id,
            expected_trustee_id=package.trustee_id,
        ):
            return False

    return True
