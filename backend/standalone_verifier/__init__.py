"""
Standalone Independent Verifier for SecureVOTE.

STRUCTURAL INDEPENDENCE PROPERTY:
This package has ZERO dependencies on:
- SQLAlchemy / ORM models
- backend database sessions or engines
- FastAPI application or routing
- Server-side mutable state

It operates purely on machine-verifiable JSON election export archives.
"""

from .verifier import StandaloneElectionVerifier, verify_election_archive

__all__ = ["StandaloneElectionVerifier", "verify_election_archive"]
