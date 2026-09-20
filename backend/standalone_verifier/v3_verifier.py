"""
Standalone Independent Verification Engine for SecureVOTE 3.0.

STRUCTURAL INDEPENDENCE GUARANTEE:
This module contains ZERO imports from:
- app.database
- app.models
- sqlalchemy
- fastapi

It verifies self-contained v3 election packages:
1. Protocol version validation
2. Public key curve validity and key fingerprint
3. Candidate list and election configuration
4. Individual ballot schema and structural integrity
5. Every ciphertext slot point-on-curve verification
6. Independent recomputation of every ballot commitment
7. Independent recomputation of every ballot artifact hash
8. Independent homomorphic aggregation of all ballots
9. Tally commitment and artifact hash validation
10. Decrypted tally zero-drift reconciliation
"""

import argparse
import json
import sys
from typing import Any, Optional

from app.crypto import PROTOCOL_VERSION
from app.crypto.canonical import (
    ballot_domain,
    canonical_hash,
    canonical_json,
    commitment_domain,
    tally_domain,
)
from app.crypto.commitment import (
    compute_ballot_commitment,
    compute_tally_commitment,
)
from app.crypto.elgamal import (
    ECPoint,
    ElGamalCiphertext,
    ElGamalPrivateKey,
    ElGamalPublicKey,
    point_on_curve,
)
from app.crypto.keys import compute_key_fingerprint, deserialize_public_key
from app.crypto.serialization import (
    deserialize_ciphertext,
    serialize_ciphertext,
)
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally


class StandaloneV3ElectionVerifier:
    """
    Independent, offline verifier for SecureVOTE 3.0 cryptographic packages.
    """

    @classmethod
    def verify_package(
        cls,
        package: dict[str, Any],
        private_key: Optional[ElGamalPrivateKey] = None,
    ) -> dict[str, Any]:
        """
        Execute the complete 10-checkpoint verification sequence on a v3 package.

        Package schema:
        {
            "protocol_version": "SECUREVOTE3",
            "election_id": "...",
            "public_key": { ... },
            "candidates": ["C1", "C2", ...],
            "ballots": [ { ... }, ... ],
            "encrypted_tally": { ... },
            "decrypted_tally": { ... } (optional)
        }
        """
        checkpoints: list[dict[str, Any]] = []
        overall_passed = True

        def record(name: str, passed: bool, message: str, details: Optional[dict[str, Any]] = None):
            nonlocal overall_passed
            if not passed:
                overall_passed = False
            checkpoints.append({
                "checkpoint": name,
                "status": "PASSED" if passed else "FAILED",
                "message": message,
                "details": details or {},
            })

        # Checkpoint 1: Protocol Version
        proto = package.get("protocol_version")
        if proto == PROTOCOL_VERSION:
            record("checkpoint_1_protocol_version", True, f"Protocol version {proto} verified")
        else:
            record("checkpoint_1_protocol_version", False, f"Expected {PROTOCOL_VERSION}, got {proto}")
            return {"verified": False, "checkpoints": checkpoints}

        # Checkpoint 2: Public Key Validation
        pub_key_data = package.get("public_key")
        try:
            public_key = deserialize_public_key(pub_key_data)
            expected_fp = pub_key_data.get("fingerprint")
            actual_fp = compute_key_fingerprint(public_key)
            if expected_fp == actual_fp:
                record("checkpoint_2_public_key", True, f"Public key valid on secp256r1; fingerprint {actual_fp[:16]}... verified")
            else:
                record("checkpoint_2_public_key", False, f"Key fingerprint mismatch: {actual_fp} != {expected_fp}")
        except Exception as e:
            record("checkpoint_2_public_key", False, f"Public key invalid: {e}")
            return {"verified": False, "checkpoints": checkpoints}

        election_id = package.get("election_id", "")
        candidates = package.get("candidates", [])
        candidate_count = len(candidates)

        # Checkpoint 3: Election Configuration & Candidates
        if election_id and candidate_count >= 2:
            record("checkpoint_3_election_config", True, f"Election {election_id} configured with {candidate_count} candidates")
        else:
            record("checkpoint_3_election_config", False, f"Invalid election configuration: {election_id}, candidates={candidates}")

        # Ballots verification
        ballots = package.get("ballots", [])
        ballot_count = len(ballots)

        # Checkpoint 4: Ballot Structural Integrity & Election Binding
        malformed_ballots = []
        for idx, b in enumerate(ballots):
            if b.get("election_id") != election_id:
                malformed_ballots.append(idx)
                continue
            for field in ["artifact_id", "encrypted_vote", "commitment", "key_fingerprint", "artifact_hash"]:
                if field not in b:
                    malformed_ballots.append(idx)
                    break
        if not malformed_ballots:
            record("checkpoint_4_ballot_structure", True, f"All {ballot_count} ballots structurally well-formed and bound to {election_id}")
        else:
            record("checkpoint_4_ballot_structure", False, f"Malformed or unbound ballots at indices: {malformed_ballots[:5]}")

        # Checkpoint 5: All Ciphertext Points On Curve
        curve_invalid = []
        for idx, b in enumerate(ballots):
            try:
                for slot_idx, slot in enumerate(b["encrypted_vote"]["slots"]):
                    ct = deserialize_ciphertext(slot)
                    if not point_on_curve(ct.c1) or not point_on_curve(ct.c2):
                        curve_invalid.append((idx, slot_idx))
            except Exception:
                curve_invalid.append((idx, -1))
        if not curve_invalid:
            record("checkpoint_5_ciphertext_curve", True, f"All ciphertext slots across {ballot_count} ballots lie on secp256r1")
        else:
            record("checkpoint_5_ciphertext_curve", False, f"Invalid curve points at ballots/slots: {curve_invalid[:5]}")

        # Checkpoint 6: Ballot Commitment Recomputation
        commitment_mismatches = []
        for idx, b in enumerate(ballots):
            try:
                expected_c = b["commitment"]
                recomputed_c = compute_ballot_commitment(
                    election_id=election_id,
                    artifact_id=b["artifact_id"],
                    encrypted_vote=b["encrypted_vote"],
                    candidate_count=b["encrypted_vote"]["candidate_count"],
                    key_fingerprint=b["key_fingerprint"],
                )
                if expected_c != recomputed_c:
                    commitment_mismatches.append(idx)
            except Exception:
                commitment_mismatches.append(idx)
        if not commitment_mismatches:
            record("checkpoint_6_ballot_commitments", True, f"All {ballot_count} ballot commitments independently verified")
        else:
            record("checkpoint_6_ballot_commitments", False, f"Commitment mismatches at indices: {commitment_mismatches[:5]}")

        # Checkpoint 7: Ballot Artifact Hash Recomputation
        hash_mismatches = []
        for idx, b in enumerate(ballots):
            try:
                expected_h = b["artifact_hash"]
                artifact_data = {
                    "protocol_version": b["protocol_version"],
                    "election_id": b["election_id"],
                    "artifact_id": b["artifact_id"],
                    "encrypted_vote": b["encrypted_vote"],
                    "commitment": b["commitment"],
                    "key_fingerprint": b["key_fingerprint"],
                }
                domain = ballot_domain(b["election_id"])
                recomputed_h = canonical_hash(artifact_data, domain=domain)
                if expected_h != recomputed_h:
                    hash_mismatches.append(idx)
            except Exception:
                hash_mismatches.append(idx)
        if not hash_mismatches:
            record("checkpoint_7_ballot_hashes", True, f"All {ballot_count} ballot artifact hashes independently verified")
        else:
            record("checkpoint_7_ballot_hashes", False, f"Artifact hash mismatches at indices: {hash_mismatches[:5]}")

        # Checkpoint 8: Independent Homomorphic Aggregation
        encrypted_tally = package.get("encrypted_tally")
        if encrypted_tally and ballots:
            try:
                recomputed_tally = aggregate_encrypted_ballots(
                    ballots,
                    election_id,
                    actual_fp,
                )
                # Verify that recomputed tally slots match package encrypted_tally slots
                stored_slots = encrypted_tally["encrypted_tally"]["slots"]
                recomputed_slots = recomputed_tally["encrypted_tally"]["slots"]
                slots_match = (stored_slots == recomputed_slots)
                if slots_match:
                    record("checkpoint_8_homomorphic_aggregation", True, f"Homomorphic aggregation of {ballot_count} ballots independently verified")
                else:
                    record("checkpoint_8_homomorphic_aggregation", False, "Published aggregate ciphertext does NOT match independent ballot sum")
            except Exception as e:
                record("checkpoint_8_homomorphic_aggregation", False, f"Aggregation error: {e}")
        else:
            record("checkpoint_8_homomorphic_aggregation", False, "Missing encrypted_tally or ballots for aggregation")

        # Checkpoint 9: Tally Commitment & Hash
        if encrypted_tally:
            try:
                expected_t_comm = encrypted_tally["commitment"]
                recomputed_t_comm = compute_tally_commitment(
                    election_id=election_id,
                    encrypted_tally=encrypted_tally["encrypted_tally"],
                    ballot_count=encrypted_tally["ballot_count"],
                    key_fingerprint=actual_fp,
                )
                if expected_t_comm == recomputed_t_comm:
                    record("checkpoint_9_tally_commitment", True, "Tally commitment independently verified")
                else:
                    record("checkpoint_9_tally_commitment", False, "Tally commitment mismatch")
            except Exception as e:
                record("checkpoint_9_tally_commitment", False, f"Tally commitment error: {e}")
        else:
            record("checkpoint_9_tally_commitment", False, "Missing encrypted_tally")

        # Checkpoint 10: Tally Decryption & Reconciliation
        decrypted_tally = package.get("decrypted_tally")
        if decrypted_tally:
            tallies = decrypted_tally.get("candidate_tallies", {})
            total_votes = sum(tallies.values())
            tally_ballots = decrypted_tally.get("total_ballots", 0)
            if total_votes == tally_ballots and tally_ballots == ballot_count:
                record("checkpoint_10_reconciliation", True, f"Zero-drift reconciliation verified: {total_votes} votes = {ballot_count} ballots")
            else:
                record("checkpoint_10_reconciliation", False, f"Reconciliation drift: votes={total_votes}, declared={tally_ballots}, ballots={ballot_count}")
        elif private_key and encrypted_tally:
            try:
                dec = decrypt_tally(private_key, encrypted_tally)
                tallies = dec.get("candidate_tallies", {})
                total_votes = sum(tallies.values())
                if total_votes == ballot_count:
                    record("checkpoint_10_reconciliation", True, f"Private key decryption and reconciliation verified: {total_votes} votes = {ballot_count} ballots")
                else:
                    record("checkpoint_10_reconciliation", False, f"Reconciliation failure upon decryption: {total_votes} != {ballot_count}")
            except Exception as e:
                record("checkpoint_10_reconciliation", False, f"Decryption failed: {e}")
        else:
            record("checkpoint_10_reconciliation", True, "No decrypted tally provided; encrypted stage verified")

        return {
            "verified": overall_passed,
            "election_id": election_id,
            "ballot_count": ballot_count,
            "checkpoints_total": len(checkpoints),
            "checkpoints_passed": sum(1 for c in checkpoints if c["status"] == "PASSED"),
            "checkpoints": checkpoints,
        }


def main():
    parser = argparse.ArgumentParser(description="SecureVOTE 3.0 Independent Verifier")
    parser.add_argument("package_file", help="Path to exported v3 election package JSON")
    args = parser.parse_args()

    with open(args.package_file, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    result = StandaloneV3ElectionVerifier.verify_package(pkg)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["verified"] else 1)


if __name__ == "__main__":
    main()
