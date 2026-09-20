"""
Ballot-Level Zero-Knowledge Validity Proof for SecureVOTE 3.1.

Combines:
1. Slot-level CDS94 disjunctive proofs: ∀j ∈ {0, ..., k-1}, v_j ∈ {0, 1}
2. Aggregate Chaum-Pedersen equality proof: Σ v_j = 1
"""

from dataclasses import dataclass
from typing import Any

from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    ElGamalPublicKey,
    point_add,
)
from app.crypto.serialization import deserialize_ciphertext
from app.crypto.zk.chaum_pedersen import (
    ChaumPedersenProof,
    prove_equality,
    verify_equality,
)
from app.crypto.zk.disjunctive import (
    Disjunctive01Proof,
    prove_disjunctive_01,
    verify_disjunctive_01,
)
from app.crypto.zk.exceptions import (
    InvalidProofError,
    ProofVerificationError,
    WitnessError,
)
from app.crypto.zk.serialization import (
    deserialize_chaum_pedersen,
    deserialize_disjunctive_01,
    serialize_chaum_pedersen,
    serialize_disjunctive_01,
)


@dataclass(frozen=True)
class BallotValidityProof:
    """
    Complete Zero-Knowledge Ballot Validity Proof.

    Guarantees:
    1. Every slot ciphertext encrypts 0 or 1.
    2. The sum of all encrypted slots encrypts 1.
    Together, these establish that the ballot encodes exactly one valid candidate selection.
    """
    election_id: str
    slot_proofs: list[Disjunctive01Proof]
    sum_proof: ChaumPedersenProof


def prove_ballot_validity(
    public_key: ElGamalPublicKey,
    candidate_index: int,
    nonces: list[int],
    candidate_count: int,
    election_id: str,
    candidate_ids: list[str],
) -> dict[str, Any]:
    """
    Generate complete zero-knowledge ballot validity proof for a one-hot vote.

    Args:
        public_key: Election ElGamal public key
        candidate_index: Index of chosen candidate (0 <= index < candidate_count)
        nonces: List of random scalars r_j used in encrypting each slot
        candidate_count: Total candidates
        election_id: Election identifier for domain binding
        candidate_ids: Ordered list of candidate IDs
    """
    if not (0 <= candidate_index < candidate_count):
        raise WitnessError(f"Candidate index {candidate_index} out of range [0, {candidate_count - 1}]")
    if len(nonces) != candidate_count:
        raise WitnessError(f"Nonces length ({len(nonces)}) does not match candidate count ({candidate_count})")
    if len(candidate_ids) != candidate_count:
        raise WitnessError(f"Candidate IDs length ({len(candidate_ids)}) does not match candidate count ({candidate_count})")

    # One-hot plaintext vector
    onehot = [1 if j == candidate_index else 0 for j in range(candidate_count)]

    # Compute ciphertexts points: A_j = r_j · G, B_j = r_j · Y + v_j · G
    from app.crypto.elgamal import G, scalar_mult
    slot_proofs = []
    a_points = []
    b_points = []

    for j in range(candidate_count):
        v_j = onehot[j]
        r_j = nonces[j]
        a_j = scalar_mult(r_j, G)
        r_y = scalar_mult(r_j, public_key.point)
        m_g = scalar_mult(v_j, G)
        b_j = point_add(r_y, m_g)

        a_points.append(a_j)
        b_points.append(b_j)

        # Slot domain separation: SECUREVOTE31/ZKP/SLOT/{election_id}/{candidate_id}/
        cid = candidate_ids[j]
        slot_domain = f"SECUREVOTE31/ZKP/SLOT/{election_id}/{cid}/"
        sp = prove_disjunctive_01(
            y_point=public_key.point,
            a_point=a_j,
            b_point=b_j,
            v_value=v_j,
            r_scalar=r_j,
            domain_prefix=slot_domain,
        )
        slot_proofs.append(serialize_disjunctive_01(sp))

    # Sum proof: A_sum = Σ A_j, B_sum = Σ B_j
    # We prove that (A_sum, B_sum - G) is a DH-tuple with witness R = (Σ r_j) mod q
    a_sum = a_points[0]
    b_sum = b_points[0]
    for j in range(1, candidate_count):
        a_sum = point_add(a_sum, a_points[j])
        b_sum = point_add(b_sum, b_points[j])

    from app.crypto.elgamal import point_negate
    b_sum_prime = point_add(b_sum, point_negate(G))
    r_sum = sum(nonces) % CURVE_ORDER

    sum_domain = f"SECUREVOTE31/ZKP/SUM/{election_id}/"
    sum_p = prove_equality(
        y_point=public_key.point,
        a_point=a_sum,
        b_prime_point=b_sum_prime,
        r_scalar=r_sum,
        domain_prefix=sum_domain,
    )
    serialized_sum_proof = serialize_chaum_pedersen(sum_p)

    return {
        "protocol_version": "SECUREVOTE31",
        "proof_type": "BALLOT_VALIDITY_PROOF",
        "election_id": election_id,
        "candidate_count": candidate_count,
        "candidate_ids": candidate_ids,
        "slot_proofs": slot_proofs,
        "sum_proof": serialized_sum_proof,
    }


def verify_ballot_validity(
    public_key: ElGamalPublicKey,
    encrypted_vote: dict[str, Any],
    proof: dict[str, Any],
    election_id: str,
) -> bool:
    """
    Verify complete zero-knowledge ballot validity proof.

    Verifies:
        1. Context matches: election_id, candidate_count, candidate_ids.
        2. Each slot proof confirms v_j in {0, 1}.
        3. The sum proof confirms sum(v_j) == 1.
    """
    if proof.get("protocol_version") != "SECUREVOTE31":
        raise InvalidProofError(f"Invalid proof protocol version: {proof.get('protocol_version')}")
    if proof.get("election_id") != election_id:
        raise InvalidProofError(f"Proof election_id mismatch: {proof.get('election_id')} != {election_id}")

    candidate_count = encrypted_vote.get("candidate_count", 0)
    candidate_ids = encrypted_vote.get("candidate_ids", [])
    slots = encrypted_vote.get("slots", [])

    if len(slots) != candidate_count or len(candidate_ids) != candidate_count:
        raise InvalidProofError("Encrypted vote structural mismatch in slot/candidate lengths")

    slot_proofs_raw = proof.get("slot_proofs", [])
    if len(slot_proofs_raw) != candidate_count:
        raise InvalidProofError(f"Slot proofs count ({len(slot_proofs_raw)}) != candidate count ({candidate_count})")

    # Deserialize ciphertexts and verify each slot
    a_points = []
    b_points = []

    for j in range(candidate_count):
        try:
            ct = deserialize_ciphertext(slots[j])
        except Exception as e:
            raise ProofVerificationError(f"Slot {j} ciphertext invalid: {e}")

        a_points.append(ct.c1)
        b_points.append(ct.c2)

        cid = candidate_ids[j]
        slot_domain = f"SECUREVOTE31/ZKP/SLOT/{election_id}/{cid}/"
        try:
            sp = deserialize_disjunctive_01(slot_proofs_raw[j])
        except Exception as e:
            raise ProofVerificationError(f"Slot {j} proof invalid: {e}")

        # Verify CDS94 proof for slot j
        try:
            verify_disjunctive_01(
                y_point=public_key.point,
                a_point=ct.c1,
                b_point=ct.c2,
                proof=sp,
                domain_prefix=slot_domain,
            )
        except Exception as e:
            raise ProofVerificationError(f"Slot {j} ({cid}) disjunctive 0-or-1 proof failed: {e}")

    # Verify sum proof
    from app.crypto.elgamal import G, point_negate
    a_sum = a_points[0]
    b_sum = b_points[0]
    for j in range(1, candidate_count):
        a_sum = point_add(a_sum, a_points[j])
        b_sum = point_add(b_sum, b_points[j])

    b_sum_prime = point_add(b_sum, point_negate(G))
    sum_domain = f"SECUREVOTE31/ZKP/SUM/{election_id}/"
    try:
        sum_p = deserialize_chaum_pedersen(proof.get("sum_proof", {}))
    except Exception as e:
        raise ProofVerificationError(f"Ballot sum proof invalid: {e}")

    try:
        verify_equality(
            y_point=public_key.point,
            a_point=a_sum,
            b_prime_point=b_sum_prime,
            proof=sum_p,
            domain_prefix=sum_domain,
        )
    except Exception as e:
        raise ProofVerificationError(f"Ballot sum equality proof (sum v_j == 1) failed: {e}")

    return True
