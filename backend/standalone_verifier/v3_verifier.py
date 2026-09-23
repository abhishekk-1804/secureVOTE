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
        allowed_protos = {PROTOCOL_VERSION, "SECUREVOTE31", "SECUREVOTE32", "SECUREVOTE33"}
        if proto in allowed_protos:
            record("checkpoint_1_protocol_version", True, f"Protocol version {proto} verified")
        else:
            record("checkpoint_1_protocol_version", False, f"Expected one of {sorted(allowed_protos)}, got {proto}")
            return {"verified": False, "checkpoints": checkpoints}

        # Checkpoint 2: Public Key Validation
        pub_key_data = package.get("public_key")
        try:
            public_key = deserialize_public_key(pub_key_data)
            if public_key.point.is_infinity or not point_on_curve(public_key.point):
                record("checkpoint_2_public_key", False, "Public key point is off-curve or at infinity")
                return {"verified": False, "checkpoints": checkpoints}
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
                    if not point_on_curve(ct.c1) or ct.c1.is_infinity or not point_on_curve(ct.c2):
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
                if "proof" in b:
                    artifact_data["proof"] = b["proof"]
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

        # Checkpoint 7B: Zero-Knowledge Ballot Validity Proofs (SecureVOTE 3.1)
        # Verifies that every ballot proves v_j in {0, 1} and sum(v_j) == 1 without revealing selections
        is_sv31 = (proto == "SECUREVOTE31")
        proofs_present = [("proof" in b and b["proof"] is not None) for b in ballots]
        proof_count = sum(1 for p in proofs_present if p)

        zkp_structural_failures = []
        zkp_cryptographic_failures = []
        zk_status = "NOT_PRESENT"

        if proof_count == ballot_count and ballot_count > 0:
            from app.crypto.zk import verify_ballot_validity
            for idx, b in enumerate(ballots):
                proof = b.get("proof")
                if not proof or not isinstance(proof, dict):
                    zkp_structural_failures.append(idx)
                    continue
                try:
                    verify_ballot_validity(
                        public_key=public_key,
                        encrypted_vote=b["encrypted_vote"],
                        proof=proof,
                        election_id=election_id,
                    )
                except Exception as e:
                    zkp_cryptographic_failures.append((idx, str(e)))

            if not zkp_structural_failures and not zkp_cryptographic_failures:
                zk_status = "VALID"
                record(
                    "checkpoint_7b_zk_ballot_validity",
                    True,
                    f"Zero-knowledge ballot validity proofs verified for all {ballot_count} ballots (∀j: v_j ∈ {{0,1}} ∧ Σv_j = 1)",
                    details={"zk_status": "VALID", "verified_ballots": ballot_count},
                )
            else:
                zk_status = "INVALID"
                fail_msg = f"ZKP verification failed: structural={zkp_structural_failures[:3]}, crypto={zkp_cryptographic_failures[:3]}"
                record(
                    "checkpoint_7b_zk_ballot_validity",
                    False,
                    fail_msg,
                    details={"zk_status": "INVALID", "structural_failures": zkp_structural_failures, "crypto_failures": zkp_cryptographic_failures},
                )
        elif 0 < proof_count < ballot_count:
            # Mixed-proof package: some ballots have proofs and some do not
            zk_status = "INVALID"
            record(
                "checkpoint_7b_zk_ballot_validity",
                False,
                f"Mixed-proof package rejected in {proto} mode: {proof_count}/{ballot_count} ballots contain proofs",
                details={"zk_status": "INVALID", "proof_count": proof_count, "ballot_count": ballot_count},
            )
        else:
            # proof_count == 0
            if is_sv31:
                # In SECUREVOTE31 mode, lack of ZK validity proofs MUST fail checkpoint 7b
                zk_status = "NOT_PRESENT"
                record(
                    "checkpoint_7b_zk_ballot_validity",
                    False,
                    "Missing required Zero-Knowledge ballot validity proofs in SECUREVOTE31 package (NOT_PRESENT)",
                    details={"zk_status": "NOT_PRESENT", "ballot_count": ballot_count},
                )
            else:
                # v3.0 compatibility mode: proofs not required for v3.0, marked NOT_VERIFIED
                zk_status = "NOT_PRESENT"
                record(
                    "checkpoint_7b_zk_ballot_validity",
                    True,
                    "No ZK validity proofs present (v3.0 plaintext ballot mode - NOT_VERIFIED)",
                    details={"zk_status": "NOT_PRESENT", "ballot_count": ballot_count},
                )

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
            tallies = decrypted_tally.get("candidate_tallies")
            tally_ballots = decrypted_tally.get("total_ballots")
            if not isinstance(tallies, dict):
                record("checkpoint_10_reconciliation", False, "candidate_tallies must be a dictionary")
            elif type(tally_ballots) is not int or isinstance(tally_ballots, bool) or tally_ballots < 0:
                record("checkpoint_10_reconciliation", False, f"Invalid total_ballots in decrypted_tally: {tally_ballots!r}")
            elif any(type(v) is not int or isinstance(v, bool) or v < 0 for v in tallies.values()):
                record("checkpoint_10_reconciliation", False, "candidate_tallies contains negative, boolean, or non-integer counts")
            elif set(tallies.keys()) != set(candidates):
                missing = set(candidates) - set(tallies.keys())
                unknown = set(tallies.keys()) - set(candidates)
                record("checkpoint_10_reconciliation", False, f"Candidate mismatch in decrypted tally: missing={sorted(list(missing))}, unknown={sorted(list(unknown))}")
            else:
                total_votes = sum(tallies.values())
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
            record("checkpoint_10_reconciliation", True, "No decrypted tally provided; encrypted stage verified (reconciliation - NOT_APPLICABLE)", details={"status": "NOT_APPLICABLE"})

        # Checkpoint 11: Threshold Tally Verification (if present)
        threshold_tally_pkg = package.get("threshold_tally")
        threshold_status = "NOT_PRESENT"
        if threshold_tally_pkg:
            try:
                from app.crypto.threshold.serialization import (
                    deserialize_dkg_manifest,
                    deserialize_tally_partial_decryption_package,
                    deserialize_threshold_tally_result,
                )
                from app.crypto.threshold.tally import ThresholdTallyVerifier

                manifest = deserialize_dkg_manifest(threshold_tally_pkg["manifest"])
                trustee_packages = {
                    int(tid): deserialize_tally_partial_decryption_package(tpkg)
                    for tid, tpkg in threshold_tally_pkg["trustee_packages"].items()
                }
                tally_result = deserialize_threshold_tally_result(threshold_tally_pkg["tally_result"])

                ThresholdTallyVerifier.verify(
                    manifest=manifest,
                    encrypted_tally=encrypted_tally,
                    trustee_packages=trustee_packages,
                    tally_result=tally_result,
                    expected_protocol_version=tally_result.protocol_version,
                )
                threshold_status = "VALID"
                record(
                    "checkpoint_11_threshold_tally",
                    True,
                    "Threshold tally combination, Chaum-Pedersen equality proofs, and Lagrange interpolation independently verified",
                    details={
                        "threshold_status": "VALID",
                        "threshold": tally_result.threshold,
                        "selected_trustees": tally_result.selected_trustees,
                        "total_votes": tally_result.total_votes,
                    },
                )
            except Exception as e:
                threshold_status = "INVALID"
                record(
                    "checkpoint_11_threshold_tally",
                    False,
                    f"Threshold tally verification failed: {e}",
                    details={"threshold_status": "INVALID", "error": str(e)},
                )
        else:
            record(
                "checkpoint_11_threshold_tally",
                True,
                "No threshold tally package present (centralized or unfinalized tally mode - SKIPPED)",
                details={"threshold_status": "NOT_PRESENT"},
            )

        # Granular diagnostic category states
        c_map = {c["checkpoint"]: (c["status"] == "PASSED") for c in checkpoints}
        ciphertext_structurally_valid = c_map.get("checkpoint_4_ballot_structure", False) and c_map.get("checkpoint_5_ciphertext_curve", False)
        commitment_valid = c_map.get("checkpoint_6_ballot_commitments", False) and c_map.get("checkpoint_7_ballot_hashes", False)
        proof_structurally_valid = (zk_status != "INVALID")
        proof_cryptographically_valid = (zk_status == "VALID")
        ballot_validity_valid = (zk_status == "VALID")
        ballot_aggregation_valid = c_map.get("checkpoint_8_homomorphic_aggregation", False)
        tally_valid = c_map.get("checkpoint_9_tally_commitment", False) and c_map.get("checkpoint_10_reconciliation", False)
        threshold_valid = (threshold_status != "INVALID")

        return {
            "verified": overall_passed,
            "election_id": election_id,
            "protocol_version": proto,
            "ballot_count": ballot_count,
            "checkpoints_total": len(checkpoints),
            "checkpoints_passed": sum(1 for c in checkpoints if c["status"] == "PASSED"),
            "ciphertext_structurally_valid": ciphertext_structurally_valid,
            "commitment_valid": commitment_valid,
            "proof_structurally_valid": proof_structurally_valid,
            "proof_cryptographically_valid": proof_cryptographically_valid,
            "ballot_validity_valid": ballot_validity_valid,
            "ballot_validity_status": zk_status,
            "ballot_aggregation_valid": ballot_aggregation_valid,
            "tally_valid": tally_valid,
            "threshold_valid": threshold_valid,
            "threshold_status": threshold_status,
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
