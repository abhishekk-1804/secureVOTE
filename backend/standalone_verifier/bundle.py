"""
SecureVOTE 3.3 — Portable Cryptographic Verification Bundle Core.

Defines the canonical schema, artifact inventory, and hashing rules for
SECUREVOTE-EVIDENCE-BUNDLE-1:
- Self-contained, portable directory or archive containing all public election evidence.
- Canonical JSON serialization with recursive floating-point rejection.
- Deterministic artifact inventory sorted lexicographically by relative path.
- Independent manifest hashing: SHA-256 over canonical manifest body.
- Path traversal defenses (preventing relative directory escapes or absolute paths).
"""

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import os
from typing import Any, Optional

from app.crypto.canonical import canonical_json
from app.crypto.exceptions import SerializationError

BUNDLE_PROTOCOL_VERSION = "SECUREVOTE-EVIDENCE-BUNDLE-1"
CANONICALIZATION_VERSION = "RFC-CANONICAL-JSON-1"
HASH_ALGORITHM = "SHA-256"
SUPPORTED_ELECTION_PROTOCOLS = {"SECUREVOTE3", "SECUREVOTE31", "SECUREVOTE32", "SECUREVOTE33"}


class BundleArtifactType(str, Enum):
    """Authoritative artifact types within an evidence bundle."""
    ELECTION_CONFIGURATION = "ELECTION_CONFIGURATION"
    PUBLIC_KEY = "PUBLIC_KEY"
    ENCRYPTED_BALLOT = "ENCRYPTED_BALLOT"
    BALLOT_PROOF = "BALLOT_PROOF"
    ENCRYPTED_TALLY = "ENCRYPTED_TALLY"
    DECRYPTED_TALLY = "DECRYPTED_TALLY"
    DKG_MANIFEST = "DKG_MANIFEST"
    TRUSTEE_PACKAGE = "TRUSTEE_PACKAGE"
    THRESHOLD_TALLY_RESULT = "THRESHOLD_TALLY_RESULT"
    VERIFICATION_INSTRUCTIONS = "VERIFICATION_INSTRUCTIONS"
    SIGNATURE = "SIGNATURE"


class BundleVerificationStatus(str, Enum):
    """Machine-readable verification checkpoint statuses."""
    VALID = "VALID"
    INVALID = "INVALID"
    NOT_PRESENT = "NOT_PRESENT"
    UNSUPPORTED = "UNSUPPORTED"
    MALFORMED = "MALFORMED"


@dataclass(frozen=True)
class ArtifactInventoryItem:
    """Deterministic entry in a bundle's artifact inventory."""
    artifact_id: str
    artifact_type: str
    path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


def normalize_bundle_path(rel_path: str) -> str:
    """
    Validate and normalize a relative path within a bundle.

    Rejects:
    - Absolute paths
    - Path traversal sequences ('..')
    - Paths starting with '/' or '\\'
    - Windows drive prefixes (e.g. 'C:')

    Returns:
    - Forward-slash normalized relative path.
    """
    if not isinstance(rel_path, str) or not rel_path.strip():
        raise ValueError(f"Artifact path must be a non-empty string, got {rel_path!r}")

    # Standardize on forward slashes
    clean = rel_path.replace("\\", "/").strip()

    if clean.startswith("/") or clean.startswith("\\"):
        raise ValueError(f"Artifact path must be relative, cannot start with separator: {rel_path!r}")

    if ":" in clean:
        raise ValueError(f"Artifact path cannot contain volume separators: {rel_path!r}")

    if "//" in clean or "/./" in clean or clean.startswith("./") or clean.endswith("/.") or clean == ".":
        raise ValueError(f"Artifact path contains redundant or dot segments: {rel_path!r}")

    parts = clean.split("/")
    if any(p == "." or not p for p in parts):
        raise ValueError(f"Artifact path contains empty or dot segments: {rel_path!r}")

    if ".." in parts:
        raise ValueError(f"Directory traversal sequences ('..') are strictly prohibited: {rel_path!r}")

    return "/".join(parts)


def compute_manifest_hash(manifest_dict: dict[str, Any]) -> str:
    """
    Compute the deterministic SHA-256 manifest hash over canonical JSON.

    The hash is calculated over the canonical manifest body EXCLUDING:
    - 'manifest_hash'
    - 'signature'

    This ensures that manifest_hash binds all metadata and the entire artifact
    inventory without self-referential paradoxes.
    """
    # Create body copy excluding hash and signature
    body = {
        k: v for k, v in manifest_dict.items()
        if k not in ("manifest_hash", "signature")
    }
    canonical_bytes = canonical_json(body).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def compute_file_sha256(data_bytes: bytes) -> str:
    """Compute standard SHA-256 hexadecimal digest of raw file bytes."""
    return hashlib.sha256(data_bytes).hexdigest()


def validate_manifest_schema(manifest: dict[str, Any]) -> None:
    """
    Validate that a bundle manifest conforms to SECUREVOTE-EVIDENCE-BUNDLE-1 schema.
    Raises ValueError or SerializationError on violation.
    """
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a JSON dictionary")

    # 0. Reject floating-point numbers recursively
    def check_no_floats(obj: Any, path: str = "") -> None:
        if isinstance(obj, float):
            raise ValueError(f"Floating-point numbers are strictly forbidden in evidence bundles: {path}={obj}")
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_no_floats(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                check_no_floats(v, f"{path}[{i}]")

    check_no_floats(manifest)

    # 1. Protocol Version
    proto = manifest.get("bundle_protocol_version")
    if proto != BUNDLE_PROTOCOL_VERSION:
        raise ValueError(f"Unsupported bundle protocol version: expected {BUNDLE_PROTOCOL_VERSION}, got {proto!r}")

    # 2. Election Protocol
    el_proto = manifest.get("election_protocol_version")
    if el_proto not in SUPPORTED_ELECTION_PROTOCOLS:
        raise ValueError(f"Unsupported election protocol version: {el_proto!r}")

    # 3. Required top-level fields
    required_fields = [
        "election_id",
        "election_protocol_version",
        "canonicalization",
        "hash_algorithm",
        "created_at",
        "election_parameters",
        "cryptographic_commitments",
        "artifact_inventory",
        "manifest_hash",
    ]
    for field in required_fields:
        if field not in manifest:
            raise ValueError(f"Missing required manifest field: {field!r}")

    # 4. Inventory validation
    inventory = manifest.get("artifact_inventory")
    if not isinstance(inventory, list):
        raise ValueError("artifact_inventory must be a list")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    prev_path = ""

    for item in inventory:
        if not isinstance(item, dict):
            raise ValueError(f"Inventory entry must be a dictionary, got {type(item).__name__}")
        for k in ("artifact_id", "artifact_type", "path", "sha256", "size_bytes"):
            if k not in item:
                raise ValueError(f"Inventory item missing field '{k}': {item}")

        art_id = item["artifact_id"]
        if art_id in seen_ids:
            raise ValueError(f"Duplicate artifact_id in inventory: {art_id!r}")
        seen_ids.add(art_id)

        clean_path = normalize_bundle_path(item["path"])
        if clean_path in seen_paths:
            raise ValueError(f"Duplicate path in inventory: {clean_path!r}")
        seen_paths.add(clean_path)

        # Enforce canonical path sorting in inventory
        if clean_path < prev_path:
            raise ValueError(f"Artifact inventory is not sorted canonically: {clean_path} appeared after {prev_path}")
        prev_path = clean_path

        # Validate hex hash
        sha = item["sha256"]
        if not isinstance(sha, str) or len(sha) != 64:
            raise ValueError(f"Invalid SHA-256 hash in inventory item '{art_id}': {sha!r}")
        try:
            bytes.fromhex(sha)
        except ValueError:
            raise ValueError(f"Non-hex SHA-256 hash in inventory item '{art_id}': {sha!r}")

        # Validate size
        if type(item["size_bytes"]) is not int or item["size_bytes"] < 0:
            raise ValueError(f"Invalid size_bytes in inventory item '{art_id}': {item['size_bytes']}")

    # 5. Verify no floats anywhere in the manifest
    # canonical_json will automatically raise SerializationError if any float exists
    canonical_json(manifest)
