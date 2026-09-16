import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def sha256_hex(data: str) -> str:
    """Compute SHA-256 hash and return as lowercase hex string."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def format_iso_timestamp(timestamp: datetime | str) -> str:
    """Format a datetime or ISO string canonically in UTC."""
    if isinstance(timestamp, str):
        return timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)
    return timestamp.isoformat()


def compute_audit_entry_hash(
    sequence_number: int,
    event_type: str,
    event_data: str | None,
    timestamp: datetime | str,
    previous_hash: str | None,
) -> str:
    """
    Compute the SHA-256 hash for an audit log entry.

    The hash chain works by including the previous entry's hash in each
    new entry's hash computation, creating a tamper-evident linked chain.
    Any modification to a historical entry will cause all subsequent hashes
    to mismatch.

    Hash input: sequence_number|event_type|event_data|timestamp_iso|previous_hash
    """
    components = [
        str(sequence_number),
        event_type,
        event_data or "",
        format_iso_timestamp(timestamp),
        previous_hash or "GENESIS",
    ]
    hash_input = "|".join(components)
    return sha256_hex(hash_input)


def compute_ballot_hash(
    election_id: str,
    session_id: str,
    candidate_id: str,
    device_id: str,
    sequence_number: int,
    timestamp: datetime | str,
) -> str:
    """
    Compute SHA-256 hash for a ballot record.

    This provides integrity verification for individual ballot records.
    It does NOT provide voter anonymity â€” the session linkage is preserved
    for educational demonstration of audit trails.
    """
    components = [
        election_id,
        str(session_id),
        candidate_id,
        device_id,
        str(sequence_number),
        format_iso_timestamp(timestamp),
    ]
    hash_input = "|".join(components)
    return sha256_hex(hash_input)


def compute_configuration_hash(election_id: str, candidates: list[dict[str, Any]]) -> str:
    """
    Compute SHA-256 hash of the election configuration.

    This hash is computed when configuration is locked and verified
    throughout the election lifecycle. Any change to candidates after
    locking will cause a configuration hash mismatch.

    Candidates are sorted by position to ensure deterministic hashing.
    """
    sorted_candidates = sorted(candidates, key=lambda c: c.get("position", 0))
    config_data = {
        "election_id": election_id,
        "candidates": [
            {
                "id": c["id"],
                "name": c["name"],
                "party": c.get("party", ""),
                "symbol": c.get("symbol", ""),
                "position": c["position"],
            }
            for c in sorted_candidates
        ],
    }
    # Use sort_keys and separators for deterministic JSON serialization
    canonical_json = json.dumps(config_data, sort_keys=True, separators=(",", ":"))
    return sha256_hex(canonical_json)


def compute_manifest_hash(
    election_id: str,
    total_ballots: int,
    candidate_totals: dict[str, int],
    device_totals: dict[str, int],
    reconciliation_status: str,
    audit_chain_status: str,
    configuration_hash: str,
) -> str:
    """
    Compute SHA-256 hash of the result manifest.

    This hash covers all result data and is what gets digitally signed.
    Independent verifiers can recompute this hash from raw records.
    """
    manifest_data = {
        "election_id": election_id,
        "total_ballots": total_ballots,
        "candidate_totals": dict(sorted(candidate_totals.items())),
        "device_totals": dict(sorted(device_totals.items())),
        "reconciliation_status": reconciliation_status,
        "audit_chain_status": audit_chain_status,
        "configuration_hash": configuration_hash,
    }
    canonical_json = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"))
    return sha256_hex(canonical_json)
