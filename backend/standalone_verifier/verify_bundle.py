"""
SecureVOTE 3.3 — Standalone Evidence Bundle Verification CLI.

Usage:
    python -m standalone_verifier.verify_bundle <path_to_bundle_directory_or_zip> [--json] [--trusted-key <hex>]
"""

import argparse
import json
import os
import sys

from standalone_verifier.bundle_verifier import StandaloneBundleVerifier


def print_human_report(res: dict) -> None:
    print("=" * 78)
    print("  SECUREVOTE 3.3 — INDEPENDENT EVIDENCE BUNDLE VERIFICATION REPORT")
    print("=" * 78)
    print(f"Bundle ID:             {res.get('bundle_id', 'UNKNOWN')}")
    print(f"Bundle Protocol:       {res.get('protocol_version', 'UNKNOWN')}")
    print(f"Election Protocol:     {res.get('election_protocol_version', 'UNKNOWN')}")
    print(f"Manifest Hash:         {res.get('manifest_hash', 'UNKNOWN')}")
    print(f"Signature Status:      {res.get('signature_status', 'NOT_PRESENT')}")
    print(f"Overall Status:        {res.get('overall_status', 'INVALID')}")
    print(f"Checkpoints Passed:    {res.get('checkpoints_passed', 0)} / {res.get('checkpoints_total', 0)}")
    print("-" * 78)
    print(f"{'CHECKPOINT':<48} | {'STATUS':<10} | {'MESSAGE'}")
    print("-" * 78)
    for cp in res.get("checkpoints", []):
        name = cp["checkpoint"]
        status = cp["status"]
        msg = cp["message"]
        print(f"{name:<48} | {status:<10} | {msg[:80]}")
    print("=" * 78)

    if res.get("explicit_limitations"):
        print("RESEARCH LIMITATIONS & BOUNDARIES:")
        for lim in res["explicit_limitations"]:
            print(f"  - {lim}")
        print("=" * 78)

    if res.get("verified"):
        print(">>> VERIFICATION RESULT: PASSED (All mathematical assertions verified)")
    else:
        print(">>> VERIFICATION RESULT: FAILED (One or more checkpoints failed)")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(description="SecureVOTE Standalone Evidence Bundle Verifier")
    parser.add_argument("bundle_path", help="Path to evidence bundle directory or .zip archive")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON report")
    parser.add_argument("--trusted-key", default=None, help="Expected Ed25519 public signing key hex")
    args = parser.parse_args()

    result = StandaloneBundleVerifier.verify(
        bundle_path=args.bundle_path,
        trusted_signing_public_key_hex=args.trusted_key,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_human_report(result)

    sys.exit(0 if result.get("verified") else 1)


if __name__ == "__main__":
    main()
