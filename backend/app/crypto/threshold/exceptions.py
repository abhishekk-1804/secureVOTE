"""
SecureVOTE 3.2 — Threshold Cryptography Exceptions.

Defines domain-specific exceptions for Distributed Key Generation (DKG),
Verifiable Secret Sharing (VSS), and Threshold Cryptosystem operations.
"""

from app.crypto.exceptions import CryptoError


class ThresholdError(CryptoError):
    """Base exception for all threshold cryptographic errors."""
    pass


class DKGError(ThresholdError):
    """Base exception for Distributed Key Generation failures."""
    pass


class CommitmentVerificationError(DKGError):
    """Raised when a Pedersen or Feldman commitment check fails."""
    pass


class ShareVerificationError(DKGError):
    """Raised when a secret share does not satisfy the published commitment."""
    pass


class SchnorrProofError(DKGError):
    """Raised when a Proof of Knowledge fails verification."""
    pass


class ComplaintError(DKGError):
    """Raised during invalid complaint handling or fraudulent accusation."""
    pass


class DisqualificationError(DKGError):
    """Raised when a trustee is disqualified due to protocol violations."""
    pass


class InsufficientQualifiedTrusteesError(DKGError):
    """Raised when the qualified trustee set |QUAL| falls below threshold t."""
    pass


class ThresholdSerializationError(ThresholdError):
    """Raised when threshold artifact serialization or deserialization fails."""
    pass


class ThresholdDecryptionError(ThresholdError):
    """Base exception for threshold decryption and partial decryption errors."""
    pass


class PartialDecryptionProofError(ThresholdDecryptionError):
    """Raised when a Chaum-Pedersen partial decryption proof fails verification."""
    pass


class InvalidShareError(ThresholdDecryptionError):
    """Raised when a partial decryption point or format is invalid."""
    pass
