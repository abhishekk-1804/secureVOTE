"""
Canonical Serialization for SecureVOTE 3.1 Zero-Knowledge Proofs.
"""

from typing import Any

from app.crypto.elgamal import CURVE_ORDER, ECPoint
from app.crypto.serialization import deserialize_point, serialize_point
from app.crypto.zk.chaum_pedersen import ChaumPedersenProof
from app.crypto.zk.disjunctive import Disjunctive01Proof
from app.crypto.zk.exceptions import InvalidProofError


def serialize_chaum_pedersen(proof: ChaumPedersenProof) -> dict[str, Any]:
    """Serialize a ChaumPedersenProof into a canonical dictionary."""
    return {
        "proof_type": "CHAUM_PEDERSEN_EQUALITY",
        "a": serialize_point(proof.a),
        "b": serialize_point(proof.b),
        "c": f"{proof.c:064x}",
        "s": f"{proof.s:064x}",
    }


def deserialize_chaum_pedersen(data: dict[str, Any]) -> ChaumPedersenProof:
    """Deserialize a ChaumPedersenProof from a dictionary."""
    try:
        a = deserialize_point(data["a"])
        b = deserialize_point(data["b"])
        c = int(data["c"], 16)
        s = int(data["s"], 16)
        return ChaumPedersenProof(a=a, b=b, c=c, s=s)
    except (KeyError, ValueError, TypeError) as e:
        raise InvalidProofError(f"Malformed Chaum-Pedersen proof payload: {e}")


def serialize_disjunctive_01(proof: Disjunctive01Proof) -> dict[str, Any]:
    """Serialize a Disjunctive01Proof into a canonical dictionary."""
    return {
        "proof_type": "CDS94_DISJUNCTIVE_01",
        "a0": serialize_point(proof.a0),
        "b0": serialize_point(proof.b0),
        "a1": serialize_point(proof.a1),
        "b1": serialize_point(proof.b1),
        "c0": f"{proof.c0:064x}",
        "c1": f"{proof.c1:064x}",
        "s0": f"{proof.s0:064x}",
        "s1": f"{proof.s1:064x}",
    }


def deserialize_disjunctive_01(data: dict[str, Any]) -> Disjunctive01Proof:
    """Deserialize a Disjunctive01Proof from a dictionary."""
    try:
        a0 = deserialize_point(data["a0"])
        b0 = deserialize_point(data["b0"])
        a1 = deserialize_point(data["a1"])
        b1 = deserialize_point(data["b1"])
        c0 = int(data["c0"], 16)
        c1 = int(data["c1"], 16)
        s0 = int(data["s0"], 16)
        s1 = int(data["s1"], 16)
        return Disjunctive01Proof(
            a0=a0, b0=b0,
            a1=a1, b1=b1,
            c0=c0, c1=c1,
            s0=s0, s1=s1,
        )
    except (KeyError, ValueError, TypeError) as e:
        raise InvalidProofError(f"Malformed Disjunctive 0-1 proof payload: {e}")
