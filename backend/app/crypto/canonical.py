"""
SecureVOTE 3.0 — Canonical Serialization.

Deterministic, versioned serialization for all v3 cryptographic artifacts.

Rules:
1. JSON keys are sorted alphabetically.
2. Separators are (',', ':') — no whitespace.
3. UTF-8 encoding.
4. No floats — only strings and integers.
5. Timestamps are ISO-8601 strings with explicit UTC timezone.
6. Domain-separated hashing with explicit version prefix.
7. No whitespace dependence.

Domain Separation Prefixes:
    SECUREVOTE3/BALLOT/...
    SECUREVOTE3/COMMITMENT/...
    SECUREVOTE3/TALLY/...
    SECUREVOTE3/KEY/...
    SECUREVOTE3/ARTIFACT/...
"""

import hashlib
import json
from typing import Any

from app.crypto import PROTOCOL_VERSION
from app.crypto.exceptions import SerializationError


def _validate_no_floats(obj: Any) -> None:
    """Ensure no floating-point values exist in data destined for canonical serialization."""
    if isinstance(obj, float):
        raise SerializationError("Floating-point values are prohibited in canonical serialization")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, float):
                raise SerializationError("Floating-point keys are prohibited in canonical serialization")
            _validate_no_floats(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _validate_no_floats(item)


def canonical_json(data: Any) -> str:
    """
    Produce a deterministic canonical JSON string.

    - Sorted keys
    - Compact separators (no whitespace)
    - UTF-8 encoding guaranteed (ensure_ascii=False)
    - No floating-point values permitted
    - No trailing newline
    """
    _validate_no_floats(data)
    try:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise SerializationError(f"Cannot serialize to canonical JSON: {e}")


def canonical_hash(data: Any, domain: str = "") -> str:
    """
    Compute domain-separated SHA-256 hash of canonical JSON data.

    Hash = SHA-256(domain || canonical_json(data))

    Args:
        data: The data to hash (must be JSON-serializable).
        domain: Domain separation prefix (e.g., "SECUREVOTE3/BALLOT/").

    Returns:
        Hex-encoded SHA-256 digest.
    """
    payload = domain + canonical_json(data)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ballot_domain(election_id: str) -> str:
    """Construct the domain separator for ballot artifacts."""
    return f"{PROTOCOL_VERSION}/BALLOT/{election_id}/"


def commitment_domain(election_id: str) -> str:
    """Construct the domain separator for ballot commitments."""
    return f"{PROTOCOL_VERSION}/COMMITMENT/{election_id}/"


def tally_domain(election_id: str) -> str:
    """Construct the domain separator for tally artifacts."""
    return f"{PROTOCOL_VERSION}/TALLY/{election_id}/"


def artifact_domain(election_id: str, artifact_type: str) -> str:
    """Construct a generic domain separator for any artifact type."""
    return f"{PROTOCOL_VERSION}/{artifact_type}/{election_id}/"
