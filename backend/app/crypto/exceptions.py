"""
SecureVOTE 3.0 — Typed Cryptographic Exceptions.

Every cryptographic failure produces a specific, typed exception
rather than a generic error. This enables precise attack detection
and verifier diagnostics.
"""


class CryptoError(Exception):
    """Base exception for all SecureVOTE cryptographic operations."""
    pass


class KeyGenerationError(CryptoError):
    """Failed to generate cryptographic key material."""
    pass


class EncryptionError(CryptoError):
    """Failed to encrypt ballot or artifact."""
    pass


class DecryptionError(CryptoError):
    """Failed to decrypt ciphertext — wrong key, corrupted ciphertext, or invalid tally range."""
    pass


class AggregationError(CryptoError):
    """Failed to aggregate encrypted ballots — mismatched parameters or corrupted ciphertexts."""
    pass


class CommitmentError(CryptoError):
    """Commitment verification failed — artifact has been modified."""
    pass


class SerializationError(CryptoError):
    """Failed to serialize or deserialize cryptographic artifact."""
    pass


class VerificationError(CryptoError):
    """Independent verification checkpoint failed."""
    pass


class InvalidCiphertextError(CryptoError):
    """Ciphertext is malformed or does not lie on the expected curve."""
    pass


class KeyMismatchError(CryptoError):
    """Operation attempted with wrong key — election key does not match artifact."""
    pass


class ProtocolVersionError(CryptoError):
    """Protocol version mismatch — artifact was created with a different protocol version."""
    pass


class DomainSeparationError(CryptoError):
    """Domain separator mismatch — artifact belongs to a different context."""
    pass
