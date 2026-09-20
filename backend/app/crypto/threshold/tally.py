"""
SecureVOTE 3.2 — Verifiable Threshold Tally Combination.

Implements 2-of-3 threshold tally reconstruction using Lagrange interpolation over EC points.
Plaintext tallies are recovered by combining verified partial decryptions:
    D_j = lambda_i * W_{i,j} + lambda_k * W_{k,j}
    M_j = B_j - D_j = T_j * G

CRITICAL SECURITY CONSTRAINT:
The joint private key x is NEVER computed, materialized, or reconstructed.
Interpolation is executed strictly on elliptic curve points, never on secret scalars.
"""

from dataclasses import dataclass
from typing import Any, Optional

from app.crypto.elgamal import (
    CURVE_ORDER,
    G,
    INFINITY,
    ECPoint,
    _baby_step_giant_step,
    point_add,
    point_negate,
    point_on_curve,
    scalar_mult,
)
from app.crypto.serialization import deserialize_ciphertext
from app.crypto.threshold.decryption import (
    PartialDecryptionShare,
    TallyPartialDecryptionPackage,
)
from app.crypto.threshold.dkg import DKGPublicManifest
from app.crypto.threshold.exceptions import (
    InvalidShareError,
    InvalidTrusteeSubsetError,
    PartialDecryptionProofError,
    TallyReconciliationError,
    ThresholdTallyError,
)
from app.crypto.threshold.proof import (
    DEFAULT_PROTOCOL_VERSION,
    check_partial_decryption_proof,
)


@dataclass(frozen=True)
class ThresholdTallyResult:
    """
    Authoritative recovered threshold election tally result.

    Attributes:
        election_id: Unique election identifier
        threshold: Threshold t required for combination (always 2 in this prototype)
        selected_trustees: Sorted list of 2 trustee IDs used for reconstruction
        candidate_results: Mapping of candidate_id -> integer vote count
        total_votes: Sum of recovered candidate vote counts
        ballot_count: Expected ballot count from encrypted tally artifact
        combined_decryption_points: Mapping of candidate_id -> combined point D_j
        reconciled: True if total_votes == ballot_count
        protocol_version: Protocol domain version string
    """
    election_id: str
    threshold: int
    selected_trustees: list[int]
    candidate_results: dict[str, int]
    total_votes: int
    ballot_count: int
    combined_decryption_points: dict[str, ECPoint]
    reconciled: bool
    protocol_version: str = DEFAULT_PROTOCOL_VERSION


def compute_lagrange_coefficient(trustee_id: int, subset: list[int] | set[int]) -> int:
    """
    Compute the Lagrange interpolation basis coefficient lambda_i at z = 0
    over the secp256r1 scalar field Z_q for a designated trustee in subset S.

    Formula:
        lambda_i = \\prod_{k \\in S, k \\neq i} \\frac{k}{k - i} \\pmod q

    Args:
        trustee_id: The trustee identity i (1-indexed)
        subset: The set or list of trustee identities in the reconstruction quorum

    Returns:
        Integer scalar lambda_i in [1, q-1]

    Raises:
        InvalidTrusteeSubsetError: If trustee_id is not in subset or subset is invalid.
    """
    s_list = sorted(list(set(subset)))
    if trustee_id not in s_list:
        raise InvalidTrusteeSubsetError(f"Trustee {trustee_id} is not in selected subset {s_list}")

    if len(s_list) < 2:
        raise InvalidTrusteeSubsetError(f"Lagrange interpolation requires at least 2 points, got {len(s_list)}")

    numerator = 1
    denominator = 1

    for k in s_list:
        if k == trustee_id:
            continue
        # Evaluate at z = 0: (0 - k) / (trustee_id - k) = k / (k - trustee_id)
        numerator = (numerator * k) % CURVE_ORDER
        diff = (k - trustee_id) % CURVE_ORDER
        if diff == 0:
            raise InvalidTrusteeSubsetError(f"Duplicate trustee ID detected in subset: {k}")
        denominator = (denominator * diff) % CURVE_ORDER

    inv_denominator = pow(denominator, CURVE_ORDER - 2, CURVE_ORDER)
    lambda_i = (numerator * inv_denominator) % CURVE_ORDER
    return lambda_i


def validate_partial_share_contribution(
    share: PartialDecryptionShare,
    expected_election_id: str,
    expected_candidate_id: str,
    expected_trustee_id: int,
    verification_key: ECPoint,
    a_point: ECPoint,
    manifest: Optional[DKGPublicManifest] = None,
) -> None:
    """
    Execute rigorous validation of a single trustee partial decryption contribution
    prior to any point combination.

    Checks:
        1. Election ID match
        2. Candidate ID match
        3. Trustee ID match
        4. Verification key on-curve and not infinity
        5. Partial decryption point on-curve and not infinity
        6. Manifest consistency (if manifest provided)
        7. Chaum-Pedersen discrete-log equality proof verification
    """
    if share.election_id != expected_election_id:
        raise ThresholdTallyError(
            f"Share election_id mismatch: share has '{share.election_id}', expected '{expected_election_id}'"
        )

    if share.candidate_id != expected_candidate_id:
        raise ThresholdTallyError(
            f"Share candidate_id mismatch: share has '{share.candidate_id}', expected '{expected_candidate_id}'"
        )

    if share.trustee_id != expected_trustee_id:
        raise ThresholdTallyError(
            f"Share trustee_id mismatch: share has {share.trustee_id}, expected {expected_trustee_id}"
        )

    if not point_on_curve(verification_key) or verification_key.is_infinity:
        raise InvalidShareError(f"Verification key for trustee {expected_trustee_id} is invalid or at infinity")

    if not point_on_curve(share.partial_decryption) or share.partial_decryption.is_infinity:
        raise InvalidShareError(f"Partial decryption point for trustee {expected_trustee_id} is invalid or at infinity")

    if manifest is not None:
        if expected_trustee_id not in manifest.qualified_trustees:
            raise InvalidTrusteeSubsetError(
                f"Trustee {expected_trustee_id} is not in manifest qualified set {manifest.qualified_trustees}"
            )
        manifest_vk = manifest.get_trustee_verification_key(expected_trustee_id)
        if manifest_vk != verification_key:
            raise InvalidShareError(f"Verification key for trustee {expected_trustee_id} does not match DKG manifest")

    # Strict Chaum-Pedersen verification
    check_partial_decryption_proof(
        proof=share.proof,
        y_point=verification_key,
        a_point=a_point,
        w_point=share.partial_decryption,
        election_id=expected_election_id,
        candidate_id=expected_candidate_id,
        trustee_id=expected_trustee_id,
        protocol_version=share.protocol_version,
    )


def combine_candidate_partial_decryptions(
    share_i: PartialDecryptionShare,
    share_k: PartialDecryptionShare,
    a_point: ECPoint,
    verification_keys: dict[int, ECPoint],
    manifest: DKGPublicManifest,
    expected_election_id: str,
    expected_candidate_id: str,
) -> ECPoint:
    """
    Perform verifiable point-level Lagrange combination of two partial decryption shares.

    Computes:
        D_j = lambda_i * W_{i,j} + lambda_k * W_{k,j}

    CRITICAL: Never combines secret scalars. Points are combined exclusively on E(F_p).
    """
    if share_i.trustee_id == share_k.trustee_id:
        raise InvalidTrusteeSubsetError(
            f"Cannot combine shares from the same trustee ID ({share_i.trustee_id})"
        )

    trustee_subset = [share_i.trustee_id, share_k.trustee_id]
    if len(trustee_subset) != 2:
        raise InvalidTrusteeSubsetError("Threshold tally combination requires exactly 2 distinct trustees")

    # 1. Validate both individual contributions
    vk_i = verification_keys[share_i.trustee_id]
    validate_partial_share_contribution(
        share=share_i,
        expected_election_id=expected_election_id,
        expected_candidate_id=expected_candidate_id,
        expected_trustee_id=share_i.trustee_id,
        verification_key=vk_i,
        a_point=a_point,
        manifest=manifest,
    )

    vk_k = verification_keys[share_k.trustee_id]
    validate_partial_share_contribution(
        share=share_k,
        expected_election_id=expected_election_id,
        expected_candidate_id=expected_candidate_id,
        expected_trustee_id=share_k.trustee_id,
        verification_key=vk_k,
        a_point=a_point,
        manifest=manifest,
    )

    # 2. Compute explicit Lagrange coefficients
    lambda_i = compute_lagrange_coefficient(share_i.trustee_id, trustee_subset)
    lambda_k = compute_lagrange_coefficient(share_k.trustee_id, trustee_subset)

    # 3. Combine partial decryptions as elliptic curve points:
    #    D_j = lambda_i * W_{i,j} + lambda_k * W_{k,j}
    term_i = scalar_mult(lambda_i, share_i.partial_decryption)
    term_k = scalar_mult(lambda_k, share_k.partial_decryption)
    combined_d = point_add(term_i, term_k)

    if not point_on_curve(combined_d) or combined_d.is_infinity:
        raise ThresholdTallyError("Combined decryption point D_j is invalid or at infinity")

    return combined_d


def reconstruct_threshold_tally(
    shares_by_trustee: dict[int, TallyPartialDecryptionPackage],
    encrypted_tally: dict[str, Any],
    manifest: DKGPublicManifest,
    max_ballots: int = 10000,
) -> ThresholdTallyResult:
    """
    Recover the election tally by combining verifiable partial decryptions from exactly 2 trustees.

    Args:
        shares_by_trustee: Mapping of trustee_id -> TallyPartialDecryptionPackage for exactly 2 trustees
        encrypted_tally: Authoritative encrypted tally artifact containing candidate ciphertext slots
        manifest: Authoritative DKGPublicManifest containing joint public key and trustee verification keys
        max_ballots: Maximum expected ballot count for discrete log bounded search

    Returns:
        ThresholdTallyResult containing recovered candidate counts and reconciliation status.

    Raises:
        InvalidTrusteeSubsetError: If trustee count != 2 or trustees not in QUAL.
        ThresholdTallyError: If inputs are invalid or ciphertext points are malformed.
        TallyReconciliationError: If recovered vote count sum does not match ballot_count.
    """
    # 1. Structural and quorum validation
    selected_trustee_ids = sorted(list(shares_by_trustee.keys()))
    if len(selected_trustee_ids) != 2:
        raise InvalidTrusteeSubsetError(
            f"Threshold combination requires exactly 2 distinct trustees, got {len(selected_trustee_ids)}: {selected_trustee_ids}"
        )

    t_i, t_k = selected_trustee_ids[0], selected_trustee_ids[1]
    if t_i not in manifest.qualified_trustees or t_k not in manifest.qualified_trustees:
        raise InvalidTrusteeSubsetError(
            f"Selected trustees {selected_trustee_ids} must both be members of manifest qualified set {manifest.qualified_trustees}"
        )

    election_id = encrypted_tally["election_id"]
    if manifest.election_id != election_id:
        raise ThresholdTallyError(
            f"Election ID mismatch: manifest has '{manifest.election_id}', tally has '{election_id}'"
        )

    pkg_i = shares_by_trustee[t_i]
    pkg_k = shares_by_trustee[t_k]

    if pkg_i.election_id != election_id or pkg_k.election_id != election_id:
        raise ThresholdTallyError("Trustee package election_id does not match encrypted tally")

    # 2. Extract encrypted candidate slots
    tally_data = encrypted_tally.get("encrypted_tally", encrypted_tally)
    candidate_ids = tally_data["candidate_ids"]
    candidate_count = tally_data["candidate_count"]
    slot_data_list = tally_data["slots"]
    ballot_count = encrypted_tally["ballot_count"]

    if len(slot_data_list) != candidate_count or len(candidate_ids) != candidate_count:
        raise ThresholdTallyError("Ciphertext slot count does not match candidate count")

    # Verify both trustees provided shares for all candidate IDs
    for cid in candidate_ids:
        if cid not in pkg_i.shares:
            raise ThresholdTallyError(f"Trustee {t_i} is missing partial decryption share for candidate '{cid}'")
        if cid not in pkg_k.shares:
            raise ThresholdTallyError(f"Trustee {t_k} is missing partial decryption share for candidate '{cid}'")

    verification_keys = {
        t_i: manifest.get_trustee_verification_key(t_i),
        t_k: manifest.get_trustee_verification_key(t_k),
    }

    # 3. Combine per-candidate shares and recover discrete logarithms
    candidate_results: dict[str, int] = {}
    combined_d_points: dict[str, ECPoint] = {}

    for idx, cid in enumerate(candidate_ids):
        ct = deserialize_ciphertext(slot_data_list[idx])
        a_point = ct.c1
        b_point = ct.c2

        if not point_on_curve(a_point) or a_point.is_infinity:
            raise ThresholdTallyError(f"Ciphertext A component for candidate '{cid}' is off-curve or at infinity")

        if not point_on_curve(b_point) or b_point.is_infinity:
            raise ThresholdTallyError(f"Ciphertext B component for candidate '{cid}' is off-curve or at infinity")

        share_i = pkg_i.shares[cid]
        share_k = pkg_k.shares[cid]

        # Combine D_j = lambda_i * W_{i,j} + lambda_k * W_{k,j}
        combined_d = combine_candidate_partial_decryptions(
            share_i=share_i,
            share_k=share_k,
            a_point=a_point,
            verification_keys=verification_keys,
            manifest=manifest,
            expected_election_id=election_id,
            expected_candidate_id=cid,
        )
        combined_d_points[cid] = combined_d

        # M_j = B_j - D_j = B_j + (-D_j)
        neg_combined_d = point_negate(combined_d)
        m_point = point_add(b_point, neg_combined_d)

        # Discrete log search: M_j = T_j * G
        if m_point.is_infinity:
            votes = 0
        else:
            votes = _baby_step_giant_step(m_point, max_value=max_ballots)

        candidate_results[cid] = votes

    # 4. Tally Reconciliation Check
    total_votes = sum(candidate_results.values())
    if total_votes != ballot_count:
        raise TallyReconciliationError(
            f"Tally reconciliation mismatch: sum of candidate votes ({total_votes}) != ballot count ({ballot_count})"
        )

    return ThresholdTallyResult(
        election_id=election_id,
        threshold=manifest.threshold,
        selected_trustees=selected_trustee_ids,
        candidate_results=candidate_results,
        total_votes=total_votes,
        ballot_count=ballot_count,
        combined_decryption_points=combined_d_points,
        reconciled=True,
        protocol_version=DEFAULT_PROTOCOL_VERSION,
    )


# ===========================================================================
# Independent Offline Verifier
# ===========================================================================

class ThresholdTallyVerifier:
    """
    Independent, public offline auditor for threshold election tallies.

    Validates:
        1. Authoritative DKG manifest parameters (threshold = 2, trustee count = 3, QUAL size >= 2).
        2. Selected trustees belong to QUAL and constitute an authorized quorum of size 2.
        3. All candidate ciphertext slots (A_j, B_j) are valid on-curve points.
        4. Chaum-Pedersen proofs for both trustees verify against manifest verification keys.
        5. Exact Lagrange basis coefficients over Z_q.
        6. Combined decryption points D_j == lambda_i * W_i + lambda_k * W_k.
        7. Decrypted plaintexts satisfy M_j = T_j * G == B_j - D_j.
        8. Tally reconciliation: sum(T_j) == ballot_count.

    Crucial: Requires NO private keys, NO secret shares, and NEVER materializes secret x.
    """

    @classmethod
    def verify(
        cls,
        manifest: DKGPublicManifest,
        encrypted_tally: dict[str, Any],
        trustee_packages: dict[int, TallyPartialDecryptionPackage],
        tally_result: ThresholdTallyResult,
        max_ballots: int = 10000,
    ) -> bool:
        """
        Verify the complete threshold tally pipeline independently.
        Returns True on complete verification, or raises ThresholdTallyError on invalid artifact.
        """
        # 1. Manifest verification
        if manifest.threshold != 2 or manifest.trustee_count != 3:
            raise ThresholdTallyError("Manifest parameters do not conform to (2, 3) threshold model")

        if len(manifest.qualified_trustees) < 2:
            raise ThresholdTallyError("Insufficient qualified trustees in manifest")

        # 2. Quorum verification
        selected = tally_result.selected_trustees
        if len(selected) != 2:
            raise InvalidTrusteeSubsetError(f"Tally result selected trustees must have size 2, got {len(selected)}")

        for t_id in selected:
            if t_id not in manifest.qualified_trustees:
                raise InvalidTrusteeSubsetError(f"Trustee {t_id} is not in qualified set {manifest.qualified_trustees}")
            if t_id not in trustee_packages:
                raise ThresholdTallyError(f"Missing partial decryption package for trustee {t_id}")

        t_i, t_k = selected[0], selected[1]
        pkg_i = trustee_packages[t_i]
        pkg_k = trustee_packages[t_k]

        vk_i = manifest.get_trustee_verification_key(t_i)
        vk_k = manifest.get_trustee_verification_key(t_k)

        # 3. Lagrange coefficients
        lambda_i = compute_lagrange_coefficient(t_i, selected)
        lambda_k = compute_lagrange_coefficient(t_k, selected)

        # 4. Candidate-by-candidate verification
        tally_data = encrypted_tally.get("encrypted_tally", encrypted_tally)
        candidate_ids = tally_data["candidate_ids"]
        slot_data_list = tally_data["slots"]

        for idx, cid in enumerate(candidate_ids):
            ct = deserialize_ciphertext(slot_data_list[idx])
            a_pt = ct.c1
            b_pt = ct.c2

            sh_i = pkg_i.shares[cid]
            sh_k = pkg_k.shares[cid]

            # Verify individual proofs
            check_partial_decryption_proof(
                proof=sh_i.proof,
                y_point=vk_i,
                a_point=a_pt,
                w_point=sh_i.partial_decryption,
                election_id=manifest.election_id,
                candidate_id=cid,
                trustee_id=t_i,
            )
            check_partial_decryption_proof(
                proof=sh_k.proof,
                y_point=vk_k,
                a_point=a_pt,
                w_point=sh_k.partial_decryption,
                election_id=manifest.election_id,
                candidate_id=cid,
                trustee_id=t_k,
            )

            # Check point combination: D_j == lambda_i * W_i + lambda_k * W_k
            expected_d = point_add(
                scalar_mult(lambda_i, sh_i.partial_decryption),
                scalar_mult(lambda_k, sh_k.partial_decryption),
            )
            actual_d = tally_result.combined_decryption_points[cid]
            if expected_d != actual_d:
                raise ThresholdTallyError(f"Combined decryption point mismatch for candidate '{cid}'")

            # Check discrete log: M_j == T_j * G
            t_j = tally_result.candidate_results[cid]
            m_pt = point_add(b_pt, point_negate(actual_d))
            expected_m = scalar_mult(t_j, G) if t_j != 0 else INFINITY
            if m_pt != expected_m:
                raise ThresholdTallyError(f"Discrete logarithm mismatch for candidate '{cid}': expected {t_j}*G")

        # 5. Reconciliation
        if sum(tally_result.candidate_results.values()) != encrypted_tally["ballot_count"]:
            raise TallyReconciliationError("Tally reconciliation check failed")

        return True
