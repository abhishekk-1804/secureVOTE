r"""
SecureVOTE 3.2 — Distributed Key Generation (DKG) Protocol Engine.

Implements the Gennaro-Jarecki-Krawczyk-Rabin (GJKR) DKG framework over NIST P-256 (secp256r1)
for a (t=2, n=3) threshold cryptosystem:
1. Derives transparent independent Pedersen generator H.
2. Degree-1 polynomial sampling and Pedersen commitments C_{i,k} = a_{i,k}*G + b_{i,k}*H.
3. Schnorr Proof of Representation on C_{i,0}.
4. Pairwise verifiable secret sharing s_{i->j}, s'_{i->j}.
5. Public complaint resolution and dealer disqualification forming QUAL.
6. Phase 5 Feldman commitments A_{i,k} = a_{i,k}*G and public key derivation Y = \sum A_{i,0}.
7. Master trustee secret share x_j = \sum s_{i->j} mod q with check x_j*G == Y_j.

CRITICAL SECURITY ASSURANCES:
- The joint secret key x is never materialized, computed, or serialized at any point.
- Private shares and polynomial scalars are strictly shielded from logs and public artifacts.
"""

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Optional

from app.crypto.elgamal import (
    _A,
    _B,
    _P,
    CURVE_ORDER,
    ECPoint,
    G,
    INFINITY,
    point_add,
    point_negate,
    point_on_curve,
    scalar_mult,
)
from app.crypto.threshold.exceptions import (
    CommitmentVerificationError,
    ComplaintError,
    DisqualificationError,
    DKGError,
    InsufficientQualifiedTrusteesError,
    SchnorrProofError,
    ShareVerificationError,
)
from app.crypto.zk.transcript import Transcript

# ---------------------------------------------------------------------------
# Independent Generator H for Pedersen Commitments
# ---------------------------------------------------------------------------

PEDERSEN_H_SEED = b"SECUREVOTE32/PEDERSEN_H/GENERATOR/v1"

# Pre-computed transparent NUMS generator on secp256r1 derived via hash-to-curve
# with seed b"SECUREVOTE32/PEDERSEN_H/GENERATOR/v1" and counter = 0
PEDERSEN_H = ECPoint(
    x=0xe7613baf7ef63f90a9fc2b6dc4616c9f744d28056b300b5a523943d54cc988ff,
    y=0x912a9b3c4ba302f082331e03f46ada80fca0de6c14620793420e78ca422c4a8c,
)


def derive_pedersen_h(seed: bytes = PEDERSEN_H_SEED) -> ECPoint:
    """
    Deterministically derive an independent generator point H on secp256r1.
    Uses a verifiable 'nothing-up-my-sleeve' hash-to-curve construction;
    security relies on the assumption that the discrete-log relation between
    G and H is computationally unknown.
    """
    counter = 0
    while True:
        digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        x = int.from_bytes(digest, "big") % _P
        rhs = (x * x * x + _A * x + _B) % _P
        # Check Euler criterion for quadratic residue modulo prime P
        if pow(rhs, (_P - 1) // 2, _P) == 1:
            y = pow(rhs, (_P + 1) // 4, _P)
            # Canonicalize to even y
            if y % 2 != 0:
                y = _P - y
            pt = ECPoint(x, y)
            if point_on_curve(pt) and pt != G and not pt.is_infinity:
                return pt
        counter += 1


# ---------------------------------------------------------------------------
# Proof of Representation on Pedersen Commitment C_{i,0}
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SchnorrRepresentationProof:
    """
    Schnorr proof of representation:
    Proves knowledge of (a, b) such that C = a*G + b*H.
    """
    comm: ECPoint
    c: int
    s_a: int
    s_b: int

    def __post_init__(self):
        if not point_on_curve(self.comm) or self.comm.is_infinity:
            raise SchnorrProofError("Commitment point in Schnorr proof is invalid or at infinity")
        if not (1 <= self.c < CURVE_ORDER):
            raise SchnorrProofError("Challenge scalar out of valid range")
        if not (0 <= self.s_a < CURVE_ORDER) or not (0 <= self.s_b < CURVE_ORDER):
            raise SchnorrProofError("Response scalar out of valid range")


def prove_schnorr_representation(
    c_point: ECPoint,
    a_scalar: int,
    b_scalar: int,
    election_id: str,
    trustee_id: int,
    h_point: ECPoint = PEDERSEN_H,
) -> SchnorrRepresentationProof:
    """
    Generate a non-interactive proof of representation: C = a*G + b*H.
    """
    w_a = int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1
    w_b = int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1

    comm = point_add(scalar_mult(w_a, G), scalar_mult(w_b, h_point))

    domain = f"SECUREVOTE32/DKG/SCHNORR/{election_id}/TRUSTEE/{trustee_id}/"
    transcript = Transcript(domain=domain)
    transcript.append_point("generator_G", G)
    transcript.append_point("generator_H", h_point)
    transcript.append_point("commitment_C", c_point)
    transcript.append_point("blinding_comm", comm)
    c = transcript.challenge_scalar("schnorr_representation_challenge")

    s_a = (w_a + c * a_scalar) % CURVE_ORDER
    s_b = (w_b + c * b_scalar) % CURVE_ORDER

    return SchnorrRepresentationProof(comm=comm, c=c, s_a=s_a, s_b=s_b)


def verify_schnorr_representation(
    c_point: ECPoint,
    proof: SchnorrRepresentationProof,
    election_id: str,
    trustee_id: int,
    h_point: ECPoint = PEDERSEN_H,
) -> bool:
    """
    Verify a non-interactive proof of representation: C = a*G + b*H.
    """
    if not point_on_curve(c_point) or c_point.is_infinity:
        raise SchnorrProofError("Target commitment is off-curve or at infinity")

    domain = f"SECUREVOTE32/DKG/SCHNORR/{election_id}/TRUSTEE/{trustee_id}/"
    transcript = Transcript(domain=domain)
    transcript.append_point("generator_G", G)
    transcript.append_point("generator_H", h_point)
    transcript.append_point("commitment_C", c_point)
    transcript.append_point("blinding_comm", proof.comm)
    expected_c = transcript.challenge_scalar("schnorr_representation_challenge")

    if proof.c != expected_c:
        raise SchnorrProofError(f"Fiat-Shamir challenge mismatch in Schnorr proof: {proof.c} != {expected_c}")

    lhs = point_add(scalar_mult(proof.s_a, G), scalar_mult(proof.s_b, h_point))
    rhs = point_add(proof.comm, scalar_mult(proof.c, c_point))

    if lhs != rhs:
        raise SchnorrProofError("Schnorr representation equation (s_a*G + s_b*H == comm + c*C) failed")

    return True


# ---------------------------------------------------------------------------
# DKG Artifact Data Structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PedersenCommitmentPackage:
    """Public Phase 1 package published by a trustee."""
    election_id: str
    trustee_id: int
    commitments: list[ECPoint]  # [C_{i,0}, C_{i,1}]
    proof_of_knowledge: SchnorrRepresentationProof

    def __post_init__(self):
        if len(self.commitments) < 2:
            raise CommitmentVerificationError("Commitment package must have at least 2 coefficient commitments")
        for idx, pt in enumerate(self.commitments):
            if not point_on_curve(pt) or pt.is_infinity:
                raise CommitmentVerificationError(f"Commitment {idx} is invalid or at infinity")


@dataclass(frozen=True)
class PrivateSharePackage:
    """Private Phase 2 package sent from trustee i to trustee j."""
    election_id: str
    sender_id: int
    recipient_id: int
    share: int           # s_{i->j}
    blinding_share: int  # s'_{i->j}

    def __repr__(self) -> str:
        return f"PrivateSharePackage(election_id='{self.election_id}', sender_id={self.sender_id}, recipient_id={self.recipient_id}, share=<REDACTED>, blinding_share=<REDACTED>)"


@dataclass(frozen=True)
class DKGComplaint:
    """Public complaint artifact posted to ledger when share verification fails."""
    election_id: str
    complaining_trustee_id: int
    accused_trustee_id: int
    revealed_share: int
    revealed_blinding_share: int
    reason: str = ""


@dataclass(frozen=True)
class FeldmanRevealPackage:
    """Public Phase 5 package published by a qualified trustee."""
    election_id: str
    trustee_id: int
    feldman_commitments: list[ECPoint]   # [A_{i,0}, A_{i,1}]
    blinding_coefficients: list[int]     # [b_{i,0}, b_{i,1}]

    def __post_init__(self):
        if len(self.feldman_commitments) != len(self.blinding_coefficients):
            raise CommitmentVerificationError("Feldman commitments and blinding coefficients length mismatch")
        for pt in self.feldman_commitments:
            if not point_on_curve(pt) or pt.is_infinity:
                raise CommitmentVerificationError("Feldman commitment point is invalid or at infinity")
        for b in self.blinding_coefficients:
            if not (0 <= b < CURVE_ORDER):
                raise CommitmentVerificationError("Blinding coefficient out of valid group order range")


@dataclass(frozen=True)
class TrusteePrivateKeyShare:
    """Private secret share retained locally by a trustee."""
    election_id: str
    trustee_id: int
    secret_share: int
    joint_public_key: ECPoint
    verification_key: ECPoint

    def __repr__(self) -> str:
        return (
            f"TrusteePrivateKeyShare(election_id='{self.election_id}', "
            f"trustee_id={self.trustee_id}, secret_share=<REDACTED>, "
            f"joint_public_key=ECPoint(...), verification_key=ECPoint(...))"
        )


@dataclass(frozen=True)
class DKGPublicManifest:
    """Universal DKG manifest recorded on the public ledger."""
    election_id: str
    threshold: int
    trustee_count: int
    qualified_trustees: list[int]
    joint_public_key: ECPoint
    trustee_verification_keys: list[dict[str, Any]]
    pedersen_commitments: list[dict[str, Any]]
    feldman_commitments: list[dict[str, Any]]

    def get_trustee_verification_key(self, trustee_id: int) -> ECPoint:
        """Lookup verification key point for a given trustee ID."""
        for item in self.trustee_verification_keys:
            if item["trustee_id"] == trustee_id:
                return item["point"]
        raise KeyError(f"Trustee {trustee_id} not found in manifest verification keys")



# ---------------------------------------------------------------------------
# Trustee DKG Session State Machine
# ---------------------------------------------------------------------------

class TrusteeDKGSession:
    """
    Manages the state and cryptographic protocol rounds for an individual trustee.
    """

    def __init__(
        self,
        trustee_id: int,
        election_id: str,
        threshold: int = 2,
        total_trustees: int = 3,
        h_point: ECPoint = PEDERSEN_H,
    ):
        if trustee_id <= 0:
            raise DKGError("Trustee ID must be a positive integer")
        if threshold < 2:
            raise DKGError("Threshold t must be at least 2")
        if total_trustees < threshold:
            raise DKGError("Total trustees n cannot be less than threshold t")

        self.trustee_id = trustee_id
        self.election_id = election_id
        self.threshold = threshold
        self.total_trustees = total_trustees
        self.h_point = h_point

        # Private polynomial coefficients (degree t - 1 = 1)
        self._a_coeffs: list[int] = []
        self._b_coeffs: list[int] = []

        # Generated artifacts
        self.pedersen_package: Optional[PedersenCommitmentPackage] = None
        self.shares_generated: dict[int, PrivateSharePackage] = {}
        self.received_shares: dict[int, PrivateSharePackage] = {}

    def __repr__(self) -> str:
        return f"TrusteeDKGSession(trustee_id={self.trustee_id}, election_id='{self.election_id}', threshold={self.threshold})"

    def generate_pedersen_commitments(self) -> PedersenCommitmentPackage:
        """
        Phase 1: Sample random polynomials f_i(z) and f'_i(z) of degree t-1,
        and generate Pedersen commitments C_{i,k} = a_{i,k}*G + b_{i,k}*H.
        """
        # Degree t - 1 polynomial coefficients
        degree = self.threshold - 1
        self._a_coeffs = [
            int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1
            for _ in range(degree + 1)
        ]
        self._b_coeffs = [
            int.from_bytes(os.urandom(32), "big") % (CURVE_ORDER - 1) + 1
            for _ in range(degree + 1)
        ]

        commitments = []
        for k in range(degree + 1):
            ak_g = scalar_mult(self._a_coeffs[k], G)
            bk_h = scalar_mult(self._b_coeffs[k], self.h_point)
            c_k = point_add(ak_g, bk_h)
            commitments.append(c_k)

        # Schnorr proof on constant term C_{i,0}
        pok = prove_schnorr_representation(
            c_point=commitments[0],
            a_scalar=self._a_coeffs[0],
            b_scalar=self._b_coeffs[0],
            election_id=self.election_id,
            trustee_id=self.trustee_id,
            h_point=self.h_point,
        )

        self.pedersen_package = PedersenCommitmentPackage(
            election_id=self.election_id,
            trustee_id=self.trustee_id,
            commitments=commitments,
            proof_of_knowledge=pok,
        )
        return self.pedersen_package

    def generate_shares_for_peers(self) -> dict[int, PrivateSharePackage]:
        """
        Phase 2: Compute secret evaluations s_{i->j} = f_i(j) and s'_{i->j} = f'_i(j)
        for all peers j in {1, ..., n}.
        """
        if not self._a_coeffs or not self._b_coeffs:
            raise DKGError("Commitments must be generated before shares can be distributed")

        shares = {}
        for j in range(1, self.total_trustees + 1):
            # Evaluate f_i(j) = a_0 + a_1 * j
            s = (self._a_coeffs[0] + self._a_coeffs[1] * j) % CURVE_ORDER
            # Evaluate f'_i(j) = b_0 + b_1 * j
            s_prime = (self._b_coeffs[0] + self._b_coeffs[1] * j) % CURVE_ORDER

            pkg = PrivateSharePackage(
                election_id=self.election_id,
                sender_id=self.trustee_id,
                recipient_id=j,
                share=s,
                blinding_share=s_prime,
            )
            shares[j] = pkg

        self.shares_generated = shares
        return shares

    def verify_received_share(
        self,
        share_pkg: PrivateSharePackage,
        dealer_pedersen_pkg: PedersenCommitmentPackage,
    ) -> bool:
        """
        Phase 3: Verify received share against dealer's public Pedersen commitments:
        s*G + s'*H == C_{i,0} + j*C_{i,1}.
        """
        if share_pkg.recipient_id != self.trustee_id:
            raise ShareVerificationError(f"Share recipient {share_pkg.recipient_id} != trustee {self.trustee_id}")
        if share_pkg.sender_id != dealer_pedersen_pkg.trustee_id:
            raise ShareVerificationError("Share sender does not match commitment package trustee ID")
        if share_pkg.election_id != self.election_id:
            raise ShareVerificationError("Share election ID mismatch")

        j = self.trustee_id
        # LHS: s*G + s'*H
        lhs = point_add(
            scalar_mult(share_pkg.share, G),
            scalar_mult(share_pkg.blinding_share, self.h_point),
        )

        # RHS: C_0 + j * C_1
        c_0 = dealer_pedersen_pkg.commitments[0]
        c_1 = dealer_pedersen_pkg.commitments[1]
        rhs = point_add(c_0, scalar_mult(j, c_1))

        if lhs != rhs:
            raise ShareVerificationError(
                f"Share from trustee {share_pkg.sender_id} failed Pedersen commitment verification"
            )

        self.received_shares[share_pkg.sender_id] = share_pkg
        return True

    def create_complaint(
        self,
        accused_trustee_id: int,
        bad_share_pkg: PrivateSharePackage,
        reason: str = "Invalid share verification against Pedersen commitment",
    ) -> DKGComplaint:
        """
        Create a public complaint artifact broadcasting the invalid share.
        """
        return DKGComplaint(
            election_id=self.election_id,
            complaining_trustee_id=self.trustee_id,
            accused_trustee_id=accused_trustee_id,
            revealed_share=bad_share_pkg.share,
            revealed_blinding_share=bad_share_pkg.blinding_share,
            reason=reason,
        )

    def reveal_feldman_commitments(self) -> FeldmanRevealPackage:
        """
        Phase 5: Reveal public Feldman commitments A_{i,k} = a_{i,k}*G and blinding scalars b_{i,k}.
        """
        if not self._a_coeffs:
            raise DKGError("Cannot reveal Feldman commitments before polynomial generation")

        feldman_commitments = [scalar_mult(ak, G) for ak in self._a_coeffs]
        return FeldmanRevealPackage(
            election_id=self.election_id,
            trustee_id=self.trustee_id,
            feldman_commitments=feldman_commitments,
            blinding_coefficients=list(self._b_coeffs),
        )

    def finalize_secret_share(
        self,
        qualified_trustees: list[int],
        feldman_packages: dict[int, FeldmanRevealPackage],
        pedersen_packages: dict[int, PedersenCommitmentPackage],
    ) -> TrusteePrivateKeyShare:
        r"""
        Phase 6: Finalize master secret share x_j = \sum_{i \in QUAL} s_{i->j} mod q,
        derive verification key Y_j and joint public key Y.
        """
        if len(qualified_trustees) < self.threshold:
            raise InsufficientQualifiedTrusteesError(
                f"Qualified trustees {qualified_trustees} below threshold {self.threshold}"
            )
        if self.trustee_id not in qualified_trustees:
            raise DisqualificationError(f"Trustee {self.trustee_id} is disqualified and cannot finalize share")

        j = self.trustee_id

        # Verify all Feldman reveal packages against original Pedersen commitments
        for i in qualified_trustees:
            if i not in feldman_packages or i not in pedersen_packages:
                raise CommitmentVerificationError(f"Missing commitment packages for qualified trustee {i}")

            f_pkg = feldman_packages[i]
            p_pkg = pedersen_packages[i]

            # Check C_{i,k} == A_{i,k} + b_{i,k}*H
            for k in range(len(f_pkg.feldman_commitments)):
                a_k = f_pkg.feldman_commitments[k]
                b_k = f_pkg.blinding_coefficients[k]
                expected_c = point_add(a_k, scalar_mult(b_k, self.h_point))
                if expected_c != p_pkg.commitments[k]:
                    raise CommitmentVerificationError(
                        f"Feldman reveal for trustee {i} does not match Phase 1 Pedersen commitment at index {k}"
                    )

            # Check s_{i->j} * G == A_{i,0} + j * A_{i,1}
            share = self.received_shares.get(i)
            if share is None and i == self.trustee_id:
                # Own share evaluation
                s_self = (self._a_coeffs[0] + self._a_coeffs[1] * j) % CURVE_ORDER
            elif share is not None:
                s_self = share.share
            else:
                raise DKGError(f"Missing received share from qualified trustee {i}")

            lhs_check = scalar_mult(s_self, G)
            rhs_check = point_add(f_pkg.feldman_commitments[0], scalar_mult(j, f_pkg.feldman_commitments[1]))
            if lhs_check != rhs_check:
                raise CommitmentVerificationError(
                    f"Feldman share consistency check failed for trustee {i} at evaluation point {j}"
                )

        # Compute master secret share x_j
        x_j = 0
        for i in qualified_trustees:
            if i == self.trustee_id:
                s_val = (self._a_coeffs[0] + self._a_coeffs[1] * j) % CURVE_ORDER
            else:
                s_val = self.received_shares[i].share
            x_j = (x_j + s_val) % CURVE_ORDER

        # Derive joint public key Y = \sum_{i \in QUAL} A_{i,0}
        joint_y = feldman_packages[qualified_trustees[0]].feldman_commitments[0]
        for i in qualified_trustees[1:]:
            joint_y = point_add(joint_y, feldman_packages[i].feldman_commitments[0])

        # Derive trustee verification key Y_j = \sum_{i \in QUAL} (A_{i,0} + j*A_{i,1})
        y_j = point_add(
            feldman_packages[qualified_trustees[0]].feldman_commitments[0],
            scalar_mult(j, feldman_packages[qualified_trustees[0]].feldman_commitments[1]),
        )
        for i in qualified_trustees[1:]:
            eval_pt = point_add(
                feldman_packages[i].feldman_commitments[0],
                scalar_mult(j, feldman_packages[i].feldman_commitments[1]),
            )
            y_j = point_add(y_j, eval_pt)

        # Mathematical sanity check: x_j * G == Y_j
        if scalar_mult(x_j, G) != y_j:
            raise DKGError(f"Consistency check x_j * G == Y_j failed for trustee {j}")

        return TrusteePrivateKeyShare(
            election_id=self.election_id,
            trustee_id=j,
            secret_share=x_j,
            joint_public_key=joint_y,
            verification_key=y_j,
        )


# ---------------------------------------------------------------------------
# Coordinator / Universal DKG Verification Functions
# ---------------------------------------------------------------------------

def verify_pedersen_package(
    pkg: PedersenCommitmentPackage,
    election_id: str,
    h_point: ECPoint = PEDERSEN_H,
) -> bool:
    """
    Universal check: verify that a trustee's Phase 1 commitments are valid
    and accompanied by a valid Schnorr proof of representation on C_{i,0}.
    """
    if pkg.election_id != election_id:
        return False
    try:
        return verify_schnorr_representation(
            c_point=pkg.commitments[0],
            proof=pkg.proof_of_knowledge,
            election_id=election_id,
            trustee_id=pkg.trustee_id,
            h_point=h_point,
        )
    except SchnorrProofError:
        return False



def verify_complaint(
    complaint: DKGComplaint,
    dealer_pedersen_pkg: PedersenCommitmentPackage,
    h_point: ECPoint = PEDERSEN_H,
) -> bool:
    """
    Publicly evaluate a complaint posted against a dealer:
    Checks if s*G + s'*H == C_0 + j*C_1.
    - If the check FAILS: the complaint is VALID (the dealer distributed a bad share).
    - If the check PASSES: the complaint is FALSE (the share was valid; complainant lied).
    """
    if complaint.accused_trustee_id != dealer_pedersen_pkg.trustee_id:
        raise ComplaintError("Complaint accused trustee ID does not match package")

    j = complaint.complaining_trustee_id
    lhs = point_add(
        scalar_mult(complaint.revealed_share, G),
        scalar_mult(complaint.revealed_blinding_share, h_point),
    )
    c_0 = dealer_pedersen_pkg.commitments[0]
    c_1 = dealer_pedersen_pkg.commitments[1]
    rhs = point_add(c_0, scalar_mult(j, c_1))

    # Complaint is valid if and only if LHS != RHS (i.e. share is indeed invalid)
    is_valid_complaint = (lhs != rhs)
    return is_valid_complaint


def resolve_qualified_set(
    all_trustee_ids: list[int],
    pedersen_packages: dict[int, PedersenCommitmentPackage],
    complaints: list[DKGComplaint],
    threshold: int = 2,
    h_point: ECPoint = PEDERSEN_H,
) -> list[int]:
    """
    Determine the set of qualified participants QUAL:
    Trustees who failed Schnorr proof or against whom a valid complaint was verified are disqualified.
    """
    disqualified = set()

    # 1. Check Schnorr proofs for all trustees
    for t_id in all_trustee_ids:
        pkg = pedersen_packages.get(t_id)
        if not pkg:
            disqualified.add(t_id)
            continue
        try:
            if not verify_pedersen_package(pkg, pkg.election_id, h_point=h_point):
                disqualified.add(t_id)
        except Exception:
            disqualified.add(t_id)

    # 2. Check complaints
    for comp in complaints:
        accused = comp.accused_trustee_id
        pkg = pedersen_packages.get(accused)
        if pkg:
            try:
                if verify_complaint(comp, pkg, h_point=h_point):
                    disqualified.add(accused)
            except Exception:
                disqualified.add(accused)

    qual = [t_id for t_id in sorted(all_trustee_ids) if t_id not in disqualified]
    if len(qual) < threshold:
        raise InsufficientQualifiedTrusteesError(
            f"Qualified trustees count ({len(qual)}) is below threshold ({threshold}). Disqualified: {disqualified}"
        )
    return qual


def build_dkg_manifest(
    election_id: str,
    threshold: int,
    trustee_count: int,
    qualified_trustees: list[int],
    pedersen_packages: dict[int, PedersenCommitmentPackage],
    feldman_packages: dict[int, FeldmanRevealPackage],
    h_point: ECPoint = PEDERSEN_H,
) -> DKGPublicManifest:
    """
    Construct the authoritative DKGPublicManifest for the election ledger.
    """
    if len(qualified_trustees) < threshold:
        raise InsufficientQualifiedTrusteesError(f"Qualified trustees ({len(qualified_trustees)}) < threshold ({threshold})")

    # Verify Feldman packages
    for i in qualified_trustees:
        f_pkg = feldman_packages[i]
        p_pkg = pedersen_packages[i]
        for k in range(len(f_pkg.feldman_commitments)):
            expected_c = point_add(
                f_pkg.feldman_commitments[k],
                scalar_mult(f_pkg.blinding_coefficients[k], h_point),
            )
            if expected_c != p_pkg.commitments[k]:
                raise CommitmentVerificationError(f"Feldman commitment mismatch for qualified trustee {i} at index {k}")

    # Derive joint public key Y = \sum_{i \in QUAL} A_{i,0}
    joint_y = feldman_packages[qualified_trustees[0]].feldman_commitments[0]
    for i in qualified_trustees[1:]:
        joint_y = point_add(joint_y, feldman_packages[i].feldman_commitments[0])

    # Derive verification keys Y_j for all j in {1, ..., trustee_count}
    trustee_vks = []
    for j in range(1, trustee_count + 1):
        y_j = point_add(
            feldman_packages[qualified_trustees[0]].feldman_commitments[0],
            scalar_mult(j, feldman_packages[qualified_trustees[0]].feldman_commitments[1]),
        )
        for i in qualified_trustees[1:]:
            eval_pt = point_add(
                feldman_packages[i].feldman_commitments[0],
                scalar_mult(j, feldman_packages[i].feldman_commitments[1]),
            )
            y_j = point_add(y_j, eval_pt)
        trustee_vks.append({"trustee_id": j, "point": y_j})

    pedersen_summary = [
        {"trustee_id": t_id, "commitments": pedersen_packages[t_id].commitments}
        for t_id in sorted(pedersen_packages.keys())
    ]
    feldman_summary = [
        {"trustee_id": t_id, "commitments": feldman_packages[t_id].feldman_commitments}
        for t_id in sorted(feldman_packages.keys())
    ]

    return DKGPublicManifest(
        election_id=election_id,
        threshold=threshold,
        trustee_count=trustee_count,
        qualified_trustees=qualified_trustees,
        joint_public_key=joint_y,
        trustee_verification_keys=trustee_vks,
        pedersen_commitments=pedersen_summary,
        feldman_commitments=feldman_summary,
    )


def verify_dkg_manifest(
    manifest: DKGPublicManifest,
    h_point: ECPoint = PEDERSEN_H,
) -> bool:
    """
    Offline Standalone Verification:
    Verifies that a published DKG manifest is structurally sound, curve points lie on secp256r1,
    the joint public key matches the sum of qualified Feldman commitments, and verification keys match.
    """
    if manifest.threshold < 2:
        return False
    if len(manifest.qualified_trustees) < manifest.threshold:
        return False
    if not point_on_curve(manifest.joint_public_key) or manifest.joint_public_key.is_infinity:
        return False

    # Extract Feldman commitments map
    f_map = {}
    for entry in manifest.feldman_commitments:
        t_id = entry["trustee_id"]
        comm_pts = entry["commitments"]
        if not all(point_on_curve(pt) and not pt.is_infinity for pt in comm_pts):
            return False
        f_map[t_id] = comm_pts

    # Recompute Y = \sum_{i \in QUAL} A_{i,0}
    qual = manifest.qualified_trustees
    if not all(t_id in f_map for t_id in qual):
        return False

    expected_y = f_map[qual[0]][0]
    for t_id in qual[1:]:
        expected_y = point_add(expected_y, f_map[t_id][0])

    if manifest.joint_public_key != expected_y:
        return False

    # Check each verification key Y_j
    vk_map = {item["trustee_id"]: item["point"] for item in manifest.trustee_verification_keys}
    for j in range(1, manifest.trustee_count + 1):
        if j not in vk_map:
            return False
        if not point_on_curve(vk_map[j]) or vk_map[j].is_infinity:
            return False

        expected_yj = point_add(f_map[qual[0]][0], scalar_mult(j, f_map[qual[0]][1]))
        for t_id in qual[1:]:
            expected_yj = point_add(
                expected_yj,
                point_add(f_map[t_id][0], scalar_mult(j, f_map[t_id][1])),
            )
        if vk_map[j] != expected_yj:
            return False

    return True
