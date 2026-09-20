"""
SecureVOTE 3.1 — Zero-Knowledge Ballot Validity Proof Package.
"""

from app.crypto.zk.ballot_proof import (
    BallotValidityProof,
    prove_ballot_validity,
    verify_ballot_validity,
)
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
    ChallengeMismatchError,
    EquationVerificationError,
    InvalidProofError,
    ProofVerificationError,
    WitnessError,
    ZKProofError,
)
from app.crypto.zk.transcript import Transcript

ZK_PROTOCOL_VERSION = "SECUREVOTE31"

__all__ = [
    "ZK_PROTOCOL_VERSION",
    "BallotValidityProof",
    "prove_ballot_validity",
    "verify_ballot_validity",
    "ChaumPedersenProof",
    "prove_equality",
    "verify_equality",
    "Disjunctive01Proof",
    "prove_disjunctive_01",
    "verify_disjunctive_01",
    "Transcript",
    "ZKProofError",
    "InvalidProofError",
    "ProofVerificationError",
    "ChallengeMismatchError",
    "EquationVerificationError",
    "WitnessError",
]
