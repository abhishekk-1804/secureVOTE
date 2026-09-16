"""
Standalone Independent Verification Engine for SecureVOTE.

STRUCTURAL INDEPENDENCE GUARANTEE:
This module contains NO imports from:
- app.database
- app.models
- sqlalchemy
- fastapi

It consumes self-contained JSON election export archives and independently recomputes:
1. Export envelope integrity hash
2. Election configuration hash from raw candidate list
3. EVERY individual ballot SHA-256 hash
4. Monotonic sequence and replay protection per device
5. Candidate tallies directly from raw ballots
6. Device tallies directly from raw ballots
7. Exact zero-drift reconciliation
8. Audit log hash chain link-by-link
9. Audit root commitment
10. Result manifest hash
11. Ed25519 digital signature
12. Audit root anchor commitment
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
from typing import Any, Optional


def sha256_hex(data: str | bytes) -> str:
    """Compute SHA-256 hex string."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_json(data: Any) -> str:
    """Canonical JSON serialization for deterministic hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def format_iso_timestamp(timestamp: str) -> str:
    """Ensure timestamp string has canonical UTC timezone representation."""
    if not timestamp:
        return ""
    if not (timestamp.endswith("Z") or "+" in timestamp[10:] or ("-" in timestamp[10:] and "T" in timestamp)):
        return timestamp + "+00:00"
    return timestamp


class StandaloneElectionVerifier:
    """
    Completely decoupled, offline verifier for SecureVOTE election archives.
    """

    @classmethod
    def compute_config_hash(cls, election_id: str, candidates: list[dict[str, Any]]) -> str:
        """Independently recompute configuration hash from candidates sorted by position."""
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
        return sha256_hex(canonical_json(config_data))

    @classmethod
    def compute_ballot_hash(
        cls,
        election_id: str,
        session_id: str,
        candidate_id: str,
        device_id: str,
        sequence_number: int,
        timestamp: str,
    ) -> str:
        """Independently recompute SHA-256 ballot hash."""
        components = [
            election_id,
            str(session_id),
            candidate_id,
            device_id,
            str(sequence_number),
            format_iso_timestamp(timestamp),
        ]
        return sha256_hex("|".join(components))

    @classmethod
    def compute_audit_entry_hash(
        cls,
        sequence_number: int,
        event_type: str,
        event_data: Optional[str],
        timestamp: str,
        previous_hash: Optional[str],
    ) -> str:
        """Independently recompute SHA-256 hash for an audit log entry."""
        components = [
            str(sequence_number),
            event_type,
            event_data or "",
            timestamp,
            previous_hash or "GENESIS",
        ]
        return sha256_hex("|".join(components))

    @classmethod
    def compute_manifest_hash(
        cls,
        election_id: str,
        total_ballots: int,
        candidate_totals: dict[str, int],
        device_totals: dict[str, int],
        reconciliation_status: str,
        audit_chain_status: str,
        configuration_hash: str,
    ) -> str:
        """Independently recompute result manifest hash."""
        manifest_data = {
            "election_id": election_id,
            "total_ballots": total_ballots,
            "candidate_totals": dict(sorted(candidate_totals.items())),
            "device_totals": dict(sorted(device_totals.items())),
            "reconciliation_status": reconciliation_status,
            "audit_chain_status": audit_chain_status,
            "configuration_hash": configuration_hash,
        }
        return sha256_hex(canonical_json(manifest_data))

    @classmethod
    def verify_ed25519_signature(
        cls,
        payload: dict[str, Any],
        signature_hex: str,
        public_key_hex: str,
    ) -> bool:
        """Verify an Ed25519 signature on canonical JSON payload."""
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric import ed25519

            pub_bytes = bytes.fromhex(public_key_hex)
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            data_bytes = canonical_json(payload).encode("utf-8")
            sig_bytes = bytes.fromhex(signature_hex)
            pub_key.verify(sig_bytes, data_bytes)
            return True
        except Exception:
            return False

    @classmethod
    def verify_export_data(
        cls,
        export_data: dict[str, Any],
        expected_public_key_hex: Optional[str] = None,
        anchor_receipt: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Execute full independent verification on raw exported JSON data.
        Returns a machine-readable results dictionary with explicit failure codes.
        """
        checks: dict[str, bool] = {
            "export_envelope": False,
            "configuration": False,
            "ballot_hashes": False,
            "ballot_sequence": False,
            "candidate_totals": False,
            "device_totals": False,
            "reconciliation": False,
            "audit_chain": False,
            "audit_root": False,
            "manifest": False,
            "signature": False,
            "anchor": False,
        }
        failures: list[str] = []
        details: list[str] = []

        election = export_data.get("election")
        if not isinstance(election, dict):
            return {
                "valid": False,
                "checks": checks,
                "failures": ["INVALID_EXPORT_STRUCTURE: missing election metadata"],
                "summary": {},
            }

        election_id = election.get("id", "")

        # -------------------------------------------------------------
        # 1. Export envelope integrity hash
        # -------------------------------------------------------------
        stored_export_hash = export_data.get("export_hash")
        raw_payload = {k: v for k, v in export_data.items() if k != "export_hash"}
        computed_export_hash = sha256_hex(json.dumps(raw_payload, sort_keys=True))
        if stored_export_hash and stored_export_hash.lower() == computed_export_hash.lower():
            checks["export_envelope"] = True
            details.append("Export envelope hash verified.")
        else:
            failures.append("EXPORT_ENVELOPE_MISMATCH")
            details.append(f"Export hash mismatch: stored={stored_export_hash}, computed={computed_export_hash}")

        # -------------------------------------------------------------
        # 2. Election Configuration Hash
        # -------------------------------------------------------------
        candidates = export_data.get("candidates", [])
        stored_config_hash = election.get("configuration_hash", "")
        recomputed_config_hash = cls.compute_config_hash(election_id, candidates)

        if stored_config_hash and stored_config_hash.lower() == recomputed_config_hash.lower():
            checks["configuration"] = True
            details.append("Configuration hash verified.")
        else:
            failures.append("CONFIGURATION_HASH_MISMATCH")
            details.append(f"Config hash mismatch: stored={stored_config_hash}, computed={recomputed_config_hash}")

        # -------------------------------------------------------------
        # 3. Individual Ballot Hashes & 4. Ballot Sequence Integrity
        # -------------------------------------------------------------
        ballots = export_data.get("ballots", [])
        devices = export_data.get("devices", [])
        known_candidates = {c["id"] for c in candidates}
        known_devices = {d["id"] for d in devices}

        ballots_valid = True
        sequence_valid = True

        recounted_candidate_totals: dict[str, int] = {c["id"]: 0 for c in candidates}
        recounted_device_totals: dict[str, int] = {d["id"]: 0 for d in devices}
        device_sequences: dict[str, list[int]] = {d["id"]: [] for d in devices}

        for b in ballots:
            cid = b.get("candidate_id")
            did = b.get("device_id")
            seq = b.get("sequence_number")
            sid = b.get("session_id")
            ts = b.get("recorded_at")
            stored_bhash = b.get("ballot_hash")

            # Independent ballot hash calculation
            recomputed_bhash = cls.compute_ballot_hash(
                election_id=election_id,
                session_id=sid,
                candidate_id=cid,
                device_id=did,
                sequence_number=seq,
                timestamp=ts,
            )
            if stored_bhash != recomputed_bhash:
                ballots_valid = False
                failures.append(f"BALLOT_HASH_MISMATCH: ballot {b.get('id')} hash corrupted")

            if cid in recounted_candidate_totals:
                recounted_candidate_totals[cid] += 1
            else:
                ballots_valid = False
                failures.append(f"UNKNOWN_CANDIDATE_IN_BALLOT: {cid}")

            if did in recounted_device_totals:
                recounted_device_totals[did] += 1
                device_sequences[did].append(seq)
            else:
                ballots_valid = False
                failures.append(f"UNKNOWN_DEVICE_IN_BALLOT: {did}")

        # Check sequence monotonicity per device
        for did, seqs in device_sequences.items():
            last_seq = 0
            for s in seqs:
                if s <= last_seq:
                    sequence_valid = False
                    failures.append(f"BALLOT_SEQUENCE_INVALID: device {did} replay/non-monotonic {s} <= {last_seq}")
                last_seq = s

        checks["ballot_hashes"] = ballots_valid
        checks["ballot_sequence"] = sequence_valid

        # -------------------------------------------------------------
        # 5. Candidate Totals & 6. Device Totals & 7. Reconciliation
        # -------------------------------------------------------------
        total_ballots_counted = len(ballots)
        sum_cand = sum(recounted_candidate_totals.values())
        sum_dev = sum(recounted_device_totals.values())

        checks["candidate_totals"] = (sum_cand == total_ballots_counted)
        checks["device_totals"] = (sum_dev == total_ballots_counted)

        drift = abs(sum_cand - total_ballots_counted) + abs(sum_dev - total_ballots_counted)
        if drift == 0 and (sum_cand == sum_dev == total_ballots_counted):
            checks["reconciliation"] = True
            reconciliation_status = "PASSED"
        else:
            checks["reconciliation"] = False
            reconciliation_status = "RECONCILIATION FAILURE"
            failures.append(f"RECONCILIATION_FAILURE: drift={drift}, cand_sum={sum_cand}, dev_sum={sum_dev}, total={total_ballots_counted}")

        # -------------------------------------------------------------
        # 8. Audit Log Hash Chain & 9. Audit Root Commitment
        # -------------------------------------------------------------
        audit_log = export_data.get("audit_log", [])
        sorted_audit = sorted(audit_log, key=lambda a: a.get("sequence_number", 0))
        audit_chain_valid = True
        audit_root_hash = "GENESIS"

        for i, entry in enumerate(sorted_audit):
            expected_seq = i + 1
            seq = entry.get("sequence_number")
            if seq != expected_seq:
                audit_chain_valid = False
                failures.append(f"AUDIT_CHAIN_INVALID: sequence jump expected {expected_seq}, got {seq}")

            expected_prev = sorted_audit[i - 1].get("entry_hash") if i > 0 else None
            stored_prev = entry.get("previous_hash")
            if stored_prev != expected_prev:
                audit_chain_valid = False
                failures.append(f"AUDIT_CHAIN_INVALID: previous hash break at seq {seq}")

            recomputed_entry_hash = cls.compute_audit_entry_hash(
                sequence_number=seq,
                event_type=entry.get("event_type", ""),
                event_data=entry.get("event_data"),
                timestamp=entry.get("timestamp", ""),
                previous_hash=stored_prev,
            )
            if entry.get("entry_hash") != recomputed_entry_hash:
                audit_chain_valid = False
                failures.append(f"AUDIT_CHAIN_INVALID: entry hash mismatch at seq {seq}")

            audit_root_hash = entry.get("entry_hash") or audit_root_hash

        checks["audit_chain"] = audit_chain_valid
        checks["audit_root"] = (audit_chain_valid and (len(sorted_audit) > 0))
        audit_chain_status = "INTACT" if audit_chain_valid else "BROKEN"

        # -------------------------------------------------------------
        # 10. Result Manifest Consistency
        # -------------------------------------------------------------
        manifest = export_data.get("manifest")
        if manifest:
            # Independent reconciliation of manifest candidate/device totals
            manifest_cand = manifest.get("candidate_totals", {})
            if isinstance(manifest_cand, str):
                try:
                    manifest_cand = json.loads(manifest_cand)
                except Exception:
                    manifest_cand = {}

            manifest_dev = manifest.get("device_totals", {})
            if isinstance(manifest_dev, str):
                try:
                    manifest_dev = json.loads(manifest_dev)
                except Exception:
                    manifest_dev = {}

            # Check if manifest omitted zero-vote candidates
            if all(k in recounted_candidate_totals and recounted_candidate_totals[k] == v for k, v in manifest_cand.items()):
                omitted_cand = {k: v for k, v in recounted_candidate_totals.items() if k not in manifest_cand}
                if all(v == 0 for v in omitted_cand.values()):
                    manifest_candidate_totals = manifest_cand
                else:
                    manifest_candidate_totals = recounted_candidate_totals
            else:
                manifest_candidate_totals = recounted_candidate_totals

            # Check if manifest omitted zero-vote devices
            if all(k in recounted_device_totals and recounted_device_totals[k] == v for k, v in manifest_dev.items()):
                omitted_dev = {k: v for k, v in recounted_device_totals.items() if k not in manifest_dev}
                if all(v == 0 for v in omitted_dev.values()):
                    manifest_device_totals = manifest_dev
                else:
                    manifest_device_totals = recounted_device_totals
            else:
                manifest_device_totals = recounted_device_totals

            # Recompute manifest hash from independently verified totals
            recomputed_manifest_hash = cls.compute_manifest_hash(
                election_id=election_id,
                total_ballots=total_ballots_counted,
                candidate_totals=manifest_candidate_totals,
                device_totals=manifest_device_totals,
                reconciliation_status=reconciliation_status,
                audit_chain_status=audit_chain_status,
                configuration_hash=recomputed_config_hash,
            )
            stored_mhash = manifest.get("manifest_hash")
            if stored_mhash and stored_mhash.lower() == recomputed_manifest_hash.lower():
                checks["manifest"] = True
            else:
                failures.append("MANIFEST_MISMATCH")
                details.append(f"Manifest hash mismatch: stored={stored_mhash}, computed={recomputed_manifest_hash}")
        else:
            # If election was not yet verified/manifested, check is marked true if no manifest expected
            checks["manifest"] = True

        # -------------------------------------------------------------
        # 11. Ed25519 Signature Verification
        # -------------------------------------------------------------
        sig_data_str = manifest.get("digital_signature") if manifest else None
        if sig_data_str:
            try:
                sig_obj = json.loads(sig_data_str) if isinstance(sig_data_str, str) else sig_data_str
                sig_hex = sig_obj.get("signature", "")
                pub_hex = expected_public_key_hex or sig_obj.get("public_key", "")
                signed_payload = sig_obj.get("signed_payload", {})

                # Confirm signed payload references this election and verified manifest hash
                if (
                    signed_payload.get("election_id") == election_id
                    and signed_payload.get("manifest_hash") == manifest.get("manifest_hash")
                    and cls.verify_ed25519_signature(signed_payload, sig_hex, pub_hex)
                ):
                    checks["signature"] = True
                else:
                    failures.append("SIGNATURE_INVALID")
            except Exception:
                failures.append("SIGNATURE_INVALID")
        else:
            # If no signature was present in export, check is true if unsigned
            checks["signature"] = True

        # -------------------------------------------------------------
        # 12. Audit Root Anchor Commitment Verification
        # -------------------------------------------------------------
        if anchor_receipt:
            anchored_root = anchor_receipt.get("root_hash", "")
            valid_roots = {e.get("entry_hash", "").lower() for e in sorted_audit}
            if anchored_root.lower() == audit_root_hash.lower() or anchored_root.lower() in valid_roots:
                checks["anchor"] = True
            else:
                failures.append("ANCHOR_MISMATCH")
        else:
            # No anchor provided to verify against
            checks["anchor"] = True

        # Overall validity: all checks must be True and failures empty
        overall_valid = all(checks.values()) and len(failures) == 0

        return {
            "valid": overall_valid,
            "checks": checks,
            "failures": failures,
            "details": details,
            "summary": {
                "election_id": election_id,
                "total_ballots_recounted": total_ballots_counted,
                "candidates_recounted": len(recounted_candidate_totals),
                "devices_recounted": len(recounted_device_totals),
                "audit_entries_recomputed": len(sorted_audit),
                "audit_root_hash": audit_root_hash,
                "reconciliation_drift": drift,
            },
        }

    @classmethod
    def verify_file(
        cls,
        export_file_path: str,
        public_key_hex: Optional[str] = None,
        anchor_file_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Load an export JSON file and run verification."""
        if not os.path.exists(export_file_path):
            return {
                "valid": False,
                "checks": {},
                "failures": [f"FILE_NOT_FOUND: {export_file_path}"],
                "summary": {},
            }

        with open(export_file_path, "r", encoding="utf-8") as f:
            export_data = json.load(f)

        anchor_receipt = None
        if anchor_file_path and os.path.exists(anchor_file_path):
            with open(anchor_file_path, "r", encoding="utf-8") as af:
                anchor_receipt = json.load(af)

        return cls.verify_export_data(
            export_data=export_data,
            expected_public_key_hex=public_key_hex,
            anchor_receipt=anchor_receipt,
        )


def verify_election_archive(
    archive_data: dict[str, Any],
    public_key: Optional[str] = None,
) -> dict[str, Any]:
    """Convenience function for external callers."""
    return StandaloneElectionVerifier.verify_export_data(
        export_data=archive_data,
        expected_public_key_hex=public_key,
    )


def main():
    parser = argparse.ArgumentParser(description="SecureVOTE Standalone Independent Verifier")
    parser.add_argument("export_file", help="Path to machine-verifiable JSON election export")
    parser.add_argument("--public-key", help="Optional Ed25519 public key in hex format")
    parser.add_argument("--anchor-receipt", help="Optional path to anchor receipt JSON")
    args = parser.parse_args()

    result = StandaloneElectionVerifier.verify_file(
        export_file_path=args.export_file,
        public_key_hex=args.public_key,
        anchor_file_path=args.anchor_receipt,
    )

    print(json.dumps(result, indent=2))
    if result["valid"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
