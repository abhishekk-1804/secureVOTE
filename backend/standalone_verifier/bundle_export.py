"""
SecureVOTE 3.3 — Deterministic Evidence Bundle Exporter.

Transforms self-contained election packages into portable, canonical filesystem
evidence bundles conforming to SECUREVOTE-EVIDENCE-BUNDLE-1.

Properties:
- Pure deterministic output: identical packages produce byte-identical files.
- Canonical JSON serialization (no floats, sorted keys, compact separators).
- Lexicographically sorted artifact inventory.
- Independent manifest hashing (SHA-256).
- Optional Ed25519 asymmetric signature over canonical manifest hash.
- Zero secret leakage: private keys and trustee secret shares are NEVER exported.
"""

import argparse
import copy
import json
import os
import shutil
from typing import Any, Optional
import zipfile

from app.crypto.canonical import canonical_json
from app.crypto.exceptions import SerializationError
from standalone_verifier.bundle import (
    BUNDLE_PROTOCOL_VERSION,
    CANONICALIZATION_VERSION,
    HASH_ALGORITHM,
    ArtifactInventoryItem,
    BundleArtifactType,
    compute_file_sha256,
    compute_manifest_hash,
    normalize_bundle_path,
)


def export_bundle(
    package: dict[str, Any],
    output_dir: str,
    signing_private_key_hex: Optional[str] = None,
    create_zip: bool = False,
    deterministic_timestamp: str = "2026-09-21T00:00:00Z",
) -> dict[str, Any]:
    """
    Export a self-contained election package into a portable evidence bundle directory.

    Args:
        package: The source v3 election package dictionary.
        output_dir: Destination directory for the bundle.
        signing_private_key_hex: Optional 32-byte Ed25519 private key hex for signing manifest.
        create_zip: If True, also produces an archive bundle <output_dir>.zip.
        deterministic_timestamp: Timestamp string for reproducible metadata.

    Returns:
        The canonical manifest dictionary of the generated bundle.
    """
    election_id = package.get("election_id", "UNKNOWN_ELECTION")
    el_proto = package.get("protocol_version", "SECUREVOTE33")

    # Clean / prepare output directory
    os.makedirs(output_dir, exist_ok=True)
    for sub in ("context", "ballots", "proofs", "tally", "threshold", "signatures"):
        os.makedirs(os.path.join(output_dir, sub), exist_ok=True)

    inventory_items: list[ArtifactInventoryItem] = []

    def write_canonical_file(rel_path: str, artifact_type: str, data: Any) -> None:
        clean_rel = normalize_bundle_path(rel_path)
        full_path = os.path.join(output_dir, clean_rel)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if isinstance(data, (dict, list)):
            content_bytes = canonical_json(data).encode("utf-8")
        elif isinstance(data, str):
            content_bytes = data.encode("utf-8")
        elif isinstance(data, bytes):
            content_bytes = data
        else:
            raise TypeError(f"Unsupported file data type: {type(data).__name__}")

        with open(full_path, "wb") as f:
            f.write(content_bytes)

        sha = compute_file_sha256(content_bytes)
        size = len(content_bytes)
        art_id = clean_rel
        inventory_items.append(
            ArtifactInventoryItem(
                artifact_id=art_id,
                artifact_type=artifact_type,
                path=clean_rel,
                sha256=sha,
                size_bytes=size,
            )
        )

    # 1. Context: Election parameters
    candidates = package.get("candidates", [])
    election_context = {
        "election_id": election_id,
        "protocol_version": el_proto,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "created_at": deterministic_timestamp,
    }
    write_canonical_file(
        "context/election.json",
        BundleArtifactType.ELECTION_CONFIGURATION.value,
        election_context,
    )

    # 2. Context: Public key
    pub_key = package.get("public_key")
    if pub_key:
        write_canonical_file(
            "context/public_key.json",
            BundleArtifactType.PUBLIC_KEY.value,
            pub_key,
        )

    # 3. Ballots & Proofs
    ballots = package.get("ballots", [])
    ballot_commitment_hashes: list[dict[str, str]] = []

    for idx, b in enumerate(ballots):
        ballot_rel = f"ballots/ballot_{idx:06d}.json"
        write_canonical_file(
            ballot_rel,
            BundleArtifactType.ENCRYPTED_BALLOT.value,
            b,
        )
        ballot_commitment_hashes.append({
            "artifact_id": b.get("artifact_id", f"ballot-{idx}"),
            "commitment": b.get("commitment", ""),
            "artifact_hash": b.get("artifact_hash", ""),
        })

        if b.get("proof"):
            proof_rel = f"proofs/proof_{idx:06d}.json"
            proof_data = {
                "artifact_id": f"proof-{b.get('artifact_id', idx)}",
                "ballot_artifact_id": b.get("artifact_id", f"ballot-{idx}"),
                "proof": b["proof"],
            }
            write_canonical_file(
                proof_rel,
                BundleArtifactType.BALLOT_PROOF.value,
                proof_data,
            )

    # 4. Tally
    enc_tally = package.get("encrypted_tally")
    if enc_tally:
        write_canonical_file(
            "tally/encrypted_tally.json",
            BundleArtifactType.ENCRYPTED_TALLY.value,
            enc_tally,
        )

    dec_tally = package.get("decrypted_tally")
    if dec_tally:
        write_canonical_file(
            "tally/decrypted_tally.json",
            BundleArtifactType.DECRYPTED_TALLY.value,
            dec_tally,
        )

    # 5. Threshold Cryptosystem Artifacts (if present)
    threshold_tally_pkg = package.get("threshold_tally")
    threshold_params: Optional[dict[str, Any]] = None

    if threshold_tally_pkg:
        manifest_data = threshold_tally_pkg.get("manifest")
        if manifest_data:
            write_canonical_file(
                "threshold/dkg_manifest.json",
                BundleArtifactType.DKG_MANIFEST.value,
                manifest_data,
            )
            threshold_params = {
                "threshold": manifest_data.get("threshold", 2),
                "trustee_count": manifest_data.get("trustee_count", 3),
                "qualified_trustees": manifest_data.get("qualified_trustees", []),
                "selected_trustees": [],
            }

        trustee_pkgs = threshold_tally_pkg.get("trustee_packages", {})
        for tid, tpkg in sorted(trustee_pkgs.items(), key=lambda x: int(x[0])):
            write_canonical_file(
                f"threshold/trustee_{int(tid):02d}.json",
                BundleArtifactType.TRUSTEE_PACKAGE.value,
                tpkg,
            )

        t_result = threshold_tally_pkg.get("tally_result")
        if t_result:
            write_canonical_file(
                "threshold/threshold_tally.json",
                BundleArtifactType.THRESHOLD_TALLY_RESULT.value,
                t_result,
            )
            if threshold_params is not None:
                threshold_params["selected_trustees"] = t_result.get("selected_trustees", [])

    # 6. Verification Instructions (VERIFY.md)
    verify_md_content = f"""# SecureVOTE Independent Evidence Bundle Verification Guide

**Bundle Protocol:** `{BUNDLE_PROTOCOL_VERSION}`  
**Election ID:** `{election_id}`  
**Election Protocol:** `{el_proto}`  

---

## Standalone Verification Instructions

This evidence bundle contains self-contained cryptographic artifacts and can be verified
without access to the SecureVOTE server, database, or API.

### Prerequisites
- Python 3.10+
- `cryptography` package (`pip install cryptography`)

### Verification Command

Run the standalone bundle verifier from the repository root:

```bash
python -m standalone_verifier.verify_bundle "<path-to-bundle>"
```

Or pass `--json` to receive the machine-readable JSON verification report:

```bash
python -m standalone_verifier.verify_bundle "<path-to-bundle>" --json
```

---

## Research Notice
This bundle verifies mathematical consistency of supplied cryptographic evidence.
It does not establish voter authentication, physical polling integrity, or trustee non-collusion.
"""
    write_canonical_file(
        "VERIFY.md",
        BundleArtifactType.VERIFICATION_INSTRUCTIONS.value,
        verify_md_content,
    )

    # 7. Sort artifact inventory canonically by relative path
    sorted_inventory = sorted([item.to_dict() for item in inventory_items], key=lambda x: x["path"])

    # 8. Construct Manifest dictionary
    tally_commitment = enc_tally.get("commitment", "") if enc_tally else ""
    key_fingerprint = pub_key.get("fingerprint", "") if pub_key else ""

    manifest_dict: dict[str, Any] = {
        "bundle_protocol_version": BUNDLE_PROTOCOL_VERSION,
        "election_id": election_id,
        "election_protocol_version": el_proto,
        "canonicalization": CANONICALIZATION_VERSION,
        "hash_algorithm": HASH_ALGORITHM,
        "created_at": deterministic_timestamp,
        "election_parameters": {
            "candidates": candidates,
            "candidate_count": len(candidates),
            "ballot_count": len(ballots),
            "key_fingerprint": key_fingerprint,
        },
        "cryptographic_commitments": {
            "tally_commitment": tally_commitment,
            "ballot_commitment_hashes": ballot_commitment_hashes,
        },
        "threshold_parameters": threshold_params,
        "artifact_inventory": sorted_inventory,
        "manifest_hash": "",
        "signature": None,
    }

    # 9. Compute manifest hash
    manifest_hash = compute_manifest_hash(manifest_dict)
    manifest_dict["manifest_hash"] = manifest_hash

    # 10. Optional Ed25519 Signature
    if signing_private_key_hex:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        raw_priv = bytes.fromhex(signing_private_key_hex.strip())
        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_priv)
        pub_key_obj = priv_key.public_key()
        from cryptography.hazmat.primitives import serialization
        pub_bytes = pub_key_obj.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        sig_bytes = priv_key.sign(manifest_hash.encode("utf-8"))

        manifest_dict["signature"] = {
            "algorithm": "Ed25519",
            "key_id": f"ed25519-{compute_file_sha256(pub_bytes)[:8]}",
            "public_key": pub_bytes.hex(),
            "signature": sig_bytes.hex(),
        }

        # Write detached signature file to signatures/manifest.sig.json
        sig_file_path = os.path.join(output_dir, "signatures/manifest.sig.json")
        with open(sig_file_path, "wb") as f:
            f.write(canonical_json(manifest_dict["signature"]).encode("utf-8"))

    # 11. Write manifest.json to bundle root
    manifest_bytes = canonical_json(manifest_dict).encode("utf-8")
    with open(os.path.join(output_dir, "manifest.json"), "wb") as f:
        f.write(manifest_bytes)

    # 12. Optional ZIP archive generation
    if create_zip:
        zip_path = f"{output_dir.rstrip('/\\\\')}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    full_file = os.path.join(root, file)
                    rel_zip = os.path.relpath(full_file, output_dir).replace("\\", "/")
                    zf.write(full_file, arcname=rel_zip)

    return manifest_dict


def main():
    parser = argparse.ArgumentParser(description="SecureVOTE Portable Evidence Bundle Exporter")
    parser.add_argument("--package", required=True, help="Path to exported v3 election package JSON")
    parser.add_argument("--output-dir", required=True, help="Destination directory for bundle")
    parser.add_argument("--sign-key-hex", default=None, help="Optional 32-byte Ed25519 private key hex for manifest signing")
    parser.add_argument("--zip", action="store_true", help="Create .zip archive of the bundle")
    args = parser.parse_args()

    with open(args.package, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    manifest = export_bundle(
        package=pkg,
        output_dir=args.output_dir,
        signing_private_key_hex=args.sign_key_hex,
        create_zip=args.zip,
    )
    print(f"Evidence bundle successfully exported to: {args.output_dir}")
    print(f"Manifest Hash: {manifest['manifest_hash']}")
    if manifest.get("signature"):
        print(f"Signed: Ed25519 ({manifest['signature']['key_id']})")


if __name__ == "__main__":
    main()
