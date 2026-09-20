"""
Typed Exceptions for SecureVOTE 3.1 Zero-Knowledge Proof System.
"""

from app.crypto.exceptions import CryptoError


class ZKProofError(CryptoError):
    """Base exception for all zero-knowledge proof operations."""
    pass


class InvalidProofError(ZKProofError):
    """Raised when a proof artifact is malformed, truncated, or structurally invalid."""
    pass


class ProofVerificationError(ZKProofError):
    """Raised when mathematical verification of a zero-knowledge proof fails."""
    pass


class ChallengeMismatchError(ProofVerificationError):
    """Raised when the recomputed Fiat-Shamir challenge does not match the proof."""
    pass


class EquationVerificationError(ProofVerificationError):
    """Raised when elliptic curve verification equations do not balance."""
    pass


class WitnessError(ZKProofError):
    """Raised when the prover provides an invalid witness (e.g. non-binary value or incorrect scalar)."""
    pass
