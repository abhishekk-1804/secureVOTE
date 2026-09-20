"""
SecureVOTE 3.0 — Cryptographic Research Domain.

This package implements the privacy-preserving cryptographic layer
for SecureVOTE 3.0. It is designed to be independently testable
with ZERO coupling to FastAPI, SQLAlchemy, or frontend state.

Cryptosystem: Exponential ElGamal over NIST P-256 (secp256r1).

RESEARCH PROTOTYPE — NOT PRODUCTION ELECTION INFRASTRUCTURE.
"""

__version__ = "3.0.0-research"
PROTOCOL_VERSION = "SECUREVOTE3"
