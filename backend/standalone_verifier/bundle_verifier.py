"""
SecureVOTE 3.3 — Standalone Evidence Bundle Verification Engine.

Provides complete, mathematically rigorous verification of portable evidence bundles
conforming to SECUREVOTE-EVIDENCE-BUNDLE-1.

STRUCTURAL INDEPENDENCE GUARANTEE:
This module contains ZERO imports from:
- fastapi
- sqlalchemy
- app.database
- app.models
- app.services

All evidence is validated from first cryptographic principles directly from the bundle.
Server-asserted status booleans ('verified', 'reconciled', 'passed') are NEVER trusted.
"""

import json
import os
from typing import Any, Optional
import zipfile

from app.crypto.canonical import (
    ballot_domain,
    canonical_hash,
    canonical_json,
    tally_domain,
)
from app.crypto.commitment import (
    compute_ballot_commitment,
    compute_tally_commitment,
)
from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    G,
    INFINITY,
    _baby_step_giant_step,
    is_valid_public_point,
    point_add,
    point_negate,
    point_on_curve,
    scalar_mult,
)
from app.crypto.exceptions import SerializationError
from app.crypto.keys import compute_key_fingerprint, deserialize_public_key
from app.crypto.serialization import deserialize_ciphertext
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally
from standalone_verifier.bundle import (
    BUNDLE_PROTOCOL_VERSION,
    BundleVerificationStatus,
    compute_file_sha256,
    compute_manifest_hash,
    normalize_bundle_path,
    validate_manifest_schema,
)


class BundleReader:
    """Safely reads files from either a directory bundle or a ZIP bundle."""

    def __init__(self, bundle_path: str):
        self.bundle_path = os.path.abspath(bundle_path)
        self.is_zip = zipfile.is_zipfile(self.bundle_path) if os.path.isfile(self.bundle_path) else False
        if not self.is_zip and not os.path.isdir(self.bundle_path):
            raise ValueError(f"Bundle path does not exist or is not a valid directory/zip: {bundle_path}")

        if self.is_zip:
            self.zf = zipfile.ZipFile(self.bundle_path, "r")
        else:
            self.zf = None

    def read_bytes(self, rel_path: str) -> bytes:
        clean = normalize_bundle_path(rel_path)
        if self.is_zip:
            try:
                return self.zf.read(clean)
            except KeyError:
                raise FileNotFoundError(f"Artifact not found in zip bundle: {clean}")
        else:
            full_path = os.path.join(self.bundle_path, clean)
            common = os.path.commonpath([self.bundle_path, full_path])
            if common != self.bundle_path:
                raise PermissionError(f"Path traversal detected: {rel_path}")
            if not os.path.isfile(full_path):
                raise FileNotFoundError(f"Artifact not found in directory bundle: {clean}")
            with open(full_path, "rb") as f:
                return f.read()

    def read_json(self, rel_path: str) -> Any:
        raw = self.read_bytes(rel_path)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse JSON in {rel_path}: {e}")

    def exists(self, rel_path: str) -> bool:
        try:
            clean = normalize_bundle_path(rel_path)
            if self.is_zip:
                return clean in self.zf.namelist()
            else:
                full_path = os.path.join(self.bundle_path, clean)
                return os.path.isfile(full_path)
        except Exception:
            return False

    def list_all_files(self) -> list[str]:
        """List all relative file paths present in the bundle."""
        if self.is_zip:
            return [
                name for name in self.zf.namelist()
                if not name.endswith("/")
            ]
        else:
            result = []
            for root, _, files in os.walk(self.bundle_path):
                for f in files:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, self.bundle_path).replace("\\", "/")
                    result.append(rel)
            return result

    def close(self) -> None:
        if self.zf:
            self.zf.close()


class StandaloneBundleVerifier:
    """
    15-Checkpoint Independent Verifier for SECUREVOTE-EVIDENCE-BUNDLE-1.
    """

    @classmethod
    def verify(
        cls,
        bundle_path: str,
        trusted_signing_public_key_hex: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Execute full standalone verification on a bundle.

        Returns:
            Structured verification report dictionary.
        """
        reader = None
        checkpoints: list[dict[str, Any]] = []
        overall_passed = True
        overall_status = BundleVerificationStatus.VALID.value

        def record(name: str, passed: bool, message: str, details: Optional[dict[str, Any]] = None):
            nonlocal overall_passed, overall_status
            if not passed:
                overall_passed = False
                overall_status = BundleVerificationStatus.INVALID.value
            checkpoints.append({
                "checkpoint": name,
                "status": "PASSED" if passed else "FAILED",
                "message": message,
                "details": details or {},
            })

        try:
            reader = BundleReader(bundle_path)
        except Exception as e:
            return {
                "verified": False,
                "overall_status": BundleVerificationStatus.MALFORMED.value,
                "error": f"Cannot read bundle: {e}",
                "checkpoints": [{
                    "checkpoint": "checkpoint_1_bundle_schema",
                    "status": "FAILED",
                    "message": str(e),
                }],
            }

        try:
            # -------------------------------------------------------------
            # Checkpoint 1: Bundle Schema & Float Rejection
            # -------------------------------------------------------------
            try:
                manifest_raw = reader.read_bytes("manifest.json")
                manifest = json.loads(manifest_raw.decode("utf-8"))
                validate_manifest_schema(manifest)
                record(
                    "checkpoint_1_bundle_schema",
                    True,
                    f"Bundle schema verified: {manifest.get('bundle_protocol_version')}",
                )
            except Exception as e:
                record(
                    "checkpoint_1_bundle_schema",
                    False,
                    f"Manifest schema validation failed: {e}",
                )
                return {
                    "verified": False,
                    "overall_status": BundleVerificationStatus.MALFORMED.value,
                    "error": str(e),
                    "checkpoints": checkpoints,
                }

            election_id = manifest["election_id"]
            el_proto = manifest["election_protocol_version"]

            # -------------------------------------------------------------
            # Checkpoint 2: Manifest Hash Recomputation
            # -------------------------------------------------------------
            expected_m_hash = manifest.get("manifest_hash", "")
            computed_m_hash = compute_manifest_hash(manifest)
            if expected_m_hash == computed_m_hash:
                record(
                    "checkpoint_2_manifest_hash",
                    True,
                    f"Manifest hash verified independently ({computed_m_hash[:16]}...)",
                )
            else:
                record(
                    "checkpoint_2_manifest_hash",
                    False,
                    f"Manifest hash mismatch: declared={expected_m_hash}, computed={computed_m_hash}",
                )

            # -------------------------------------------------------------
            # Checkpoint 3: Artifact Inventory Integrity
            # -------------------------------------------------------------
            inventory = manifest.get("artifact_inventory", [])
            inventory_failures = []
            declared_paths = set()

            for item in inventory:
                rel_path = item["path"]
                declared_paths.add(rel_path)
                try:
                    file_bytes = reader.read_bytes(rel_path)
                    computed_sha = compute_file_sha256(file_bytes)
                    if computed_sha != item["sha256"]:
                        inventory_failures.append(f"Hash mismatch for {rel_path}: {computed_sha} != {item['sha256']}")
                    if len(file_bytes) != item["size_bytes"]:
                        inventory_failures.append(f"Size mismatch for {rel_path}: {len(file_bytes)} != {item['size_bytes']}")
                except Exception as e:
                    inventory_failures.append(f"Failed to read {rel_path}: {e}")

            # Check for undeclared rogue files in bundle
            all_files_on_disk = set(reader.list_all_files())
            allowed_system_files = {"manifest.json", "signatures/manifest.sig.json"}
            undeclared = [f for f in all_files_on_disk if f not in allowed_system_files and f not in declared_paths]
            if undeclared:
                inventory_failures.append(f"Undeclared files present in bundle: {undeclared[:5]}")

            if not inventory_failures:
                record(
                    "checkpoint_3_inventory_integrity",
                    True,
                    f"All {len(inventory)} artifacts in inventory verified by SHA-256 digest and size",
                )
            else:
                record(
                    "checkpoint_3_inventory_integrity",
                    False,
                    f"Inventory integrity failed: {inventory_failures[:3]}",
                    details={"failures": inventory_failures},
                )

            # -------------------------------------------------------------
            # Checkpoint 4: Ed25519 Detached/Manifest Signature
            # -------------------------------------------------------------
            sig_info = manifest.get("signature")
            signature_status = BundleVerificationStatus.NOT_PRESENT.value

            if sig_info:
                try:
                    from cryptography.hazmat.primitives.asymmetric import ed25519
                    sig_hex = sig_info["signature"]
                    pub_hex = sig_info["public_key"]

                    # If trusted key was provided, verify pub key match
                    if trusted_signing_public_key_hex and pub_hex != trusted_signing_public_key_hex:
                        signature_status = BundleVerificationStatus.INVALID.value
                        record(
                            "checkpoint_4_signature",
                            False,
                            f"Public signing key {pub_hex} does not match trusted key {trusted_signing_public_key_hex}",
                        )
                    else:
                        pub_bytes = bytes.fromhex(pub_hex)
                        pub_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
                        sig_bytes = bytes.fromhex(sig_hex)
                        # Verify over manifest_hash
                        pub_key_obj.verify(sig_bytes, computed_m_hash.encode("utf-8"))
                        signature_status = BundleVerificationStatus.VALID.value
                        record(
                            "checkpoint_4_signature",
                            True,
                            f"Ed25519 signature valid ({sig_info.get('key_id')})",
                            details={"key_id": sig_info.get("key_id"), "public_key": pub_hex},
                        )
                except Exception as e:
                    signature_status = BundleVerificationStatus.INVALID.value
                    record(
                        "checkpoint_4_signature",
                        False,
                        f"Ed25519 signature verification failed: {e}",
                    )
            else:
                record(
                    "checkpoint_4_signature",
                    True,
                    "No manifest signature present (unsigned bundle mode - NOT_PRESENT)",
                    details={"signature_status": BundleVerificationStatus.NOT_PRESENT.value},
                )

            # -------------------------------------------------------------
            # Checkpoint 5: Election Context & Identity Consistency
            # -------------------------------------------------------------
            el_context = None
            try:
                el_context = reader.read_json("context/election.json")
                if el_context.get("election_id") == election_id:
                    record(
                        "checkpoint_5_election_identity",
                        True,
                        f"Election identity consistently bound to {election_id}",
                    )
                else:
                    record(
                        "checkpoint_5_election_identity",
                        False,
                        f"Election ID mismatch: manifest has {election_id}, context has {el_context.get('election_id')}",
                    )
            except Exception as e:
                record(
                    "checkpoint_5_election_identity",
                    False,
                    f"Failed to read context/election.json: {e}",
                )

            # -------------------------------------------------------------
            # Checkpoint 6: Candidate Configuration & Ordering
            # -------------------------------------------------------------
            candidates_manifest = manifest["election_parameters"]["candidates"]
            candidate_count_manifest = manifest["election_parameters"].get("candidate_count")
            candidates_context = el_context.get("candidates", []) if el_context else []
            if (
                el_context is not None
                and candidates_manifest == candidates_context
                and len(candidates_manifest) >= 2
                and candidate_count_manifest == len(candidates_manifest)
                and el_context.get("candidate_count") == len(candidates_manifest)
            ):
                record(
                    "checkpoint_6_candidate_config",
                    True,
                    f"Candidate list verified: {len(candidates_manifest)} candidates in canonical order",
                )
            else:
                record(
                    "checkpoint_6_candidate_config",
                    False,
                    f"Candidate list or count mismatch: manifest={candidates_manifest} (count={candidate_count_manifest}), context={candidates_context}",
                )

            # -------------------------------------------------------------
            # Checkpoint 7: Public Key Validation
            # -------------------------------------------------------------
            public_key = None
            actual_fp = None
            try:
                pub_data = reader.read_json("context/public_key.json")
                public_key = deserialize_public_key(pub_data)
                actual_fp = compute_key_fingerprint(public_key)
                expected_fp = manifest["election_parameters"].get("key_fingerprint")

                if actual_fp == expected_fp:
                    record(
                        "checkpoint_7_public_key",
                        True,
                        f"Master public key valid on secp256r1; fingerprint verified ({actual_fp[:16]}...)",
                    )
                else:
                    record(
                        "checkpoint_7_public_key",
                        False,
                        f"Public key fingerprint mismatch: {actual_fp} != {expected_fp}",
                    )
            except Exception as e:
                record(
                    "checkpoint_7_public_key",
                    False,
                    f"Failed to validate public key in context/public_key.json: {e}",
                )

            # -------------------------------------------------------------
            # Checkpoint 8: Ballot Ciphertexts and Commitments
            # -------------------------------------------------------------
            ballot_count = manifest["election_parameters"]["ballot_count"]
            ballots = []
            ballot_failures = []

            for idx in range(ballot_count):
                b_path = f"ballots/ballot_{idx:06d}.json"
                try:
                    b = reader.read_json(b_path)
                    ballots.append(b)

                    # Point-on-curve verification for all slots
                    for slot in b["encrypted_vote"]["slots"]:
                        ct = deserialize_ciphertext(slot)
                        if not point_on_curve(ct.c1) or ct.c1.is_infinity or not point_on_curve(ct.c2):
                            ballot_failures.append(f"Ballot {idx} has invalid curve point")

                    # Recompute commitment
                    recomputed_c = compute_ballot_commitment(
                        election_id=election_id,
                        artifact_id=b["artifact_id"],
                        encrypted_vote=b["encrypted_vote"],
                        candidate_count=b["encrypted_vote"]["candidate_count"],
                        key_fingerprint=b["key_fingerprint"],
                    )
                    if recomputed_c != b["commitment"]:
                        ballot_failures.append(f"Ballot {idx} commitment mismatch")

                    # Recompute artifact hash
                    art_dict = {
                        "protocol_version": b["protocol_version"],
                        "election_id": b["election_id"],
                        "artifact_id": b["artifact_id"],
                        "encrypted_vote": b["encrypted_vote"],
                        "commitment": b["commitment"],
                        "key_fingerprint": b["key_fingerprint"],
                    }
                    if "proof" in b:
                        art_dict["proof"] = b["proof"]
                    recomputed_h = canonical_hash(art_dict, domain=ballot_domain(election_id))
                    if recomputed_h != b["artifact_hash"]:
                        ballot_failures.append(f"Ballot {idx} artifact hash mismatch")
                except Exception as e:
                    ballot_failures.append(f"Ballot {idx} error: {e}")

            if not ballot_failures:
                record(
                    "checkpoint_8_ballot_ciphertexts_and_commitments",
                    True,
                    f"All {ballot_count} ballots verified: on-curve ciphertexts, commitments, and artifact hashes",
                )
            else:
                record(
                    "checkpoint_8_ballot_ciphertexts_and_commitments",
                    False,
                    f"Ballot integrity failed: {ballot_failures[:3]}",
                )

            # -------------------------------------------------------------
            # Checkpoint 9: Zero-Knowledge Ballot Validity Proofs
            # -------------------------------------------------------------
            is_sv31_plus = el_proto in {"SECUREVOTE31", "SECUREVOTE32", "SECUREVOTE33"}
            proof_count = sum(1 for b in ballots if b.get("proof"))
            ext_proof_count = 0
            for idx in range(ballot_count):
                if reader.exists(f"proofs/proof_{idx:06d}.json"):
                    ext_proof_count += 1

            effective_proof_count = max(proof_count, ext_proof_count)
            zk_status = BundleVerificationStatus.NOT_PRESENT.value

            if effective_proof_count == ballot_count and ballot_count > 0:
                from app.crypto.zk import verify_ballot_validity
                zk_failures = []
                for idx, b in enumerate(ballots):
                    try:
                        proof_to_verify = b.get("proof")
                        proof_rel = f"proofs/proof_{idx:06d}.json"
                        try:
                            ext_p = reader.read_json(proof_rel)
                            if "proof" in ext_p:
                                proof_to_verify = ext_p["proof"]
                                if b.get("proof") and b["proof"] != proof_to_verify:
                                    zk_failures.append(f"Ballot {idx} proof does not match proofs/{proof_rel}")
                        except Exception:
                            pass

                        if not proof_to_verify:
                            zk_failures.append(f"Ballot {idx} missing proof")
                            continue

                        verify_ballot_validity(
                            public_key=public_key,
                            encrypted_vote=b["encrypted_vote"],
                            proof=proof_to_verify,
                            election_id=election_id,
                        )
                    except Exception as e:
                        zk_failures.append(f"Ballot {idx}: {e}")

                if not zk_failures:
                    zk_status = BundleVerificationStatus.VALID.value
                    record(
                        "checkpoint_9_zk_validity_proofs",
                        True,
                        f"Zero-knowledge validity proofs verified for all {ballot_count} ballots (∀j: v_j ∈ {{0,1}} ∧ Σv_j = 1)",
                    )
                else:
                    zk_status = BundleVerificationStatus.INVALID.value
                    record(
                        "checkpoint_9_zk_validity_proofs",
                        False,
                        f"ZKP verification failed: {zk_failures[:3]}",
                    )
            elif 0 < effective_proof_count < ballot_count:
                zk_status = BundleVerificationStatus.INVALID.value
                record(
                    "checkpoint_9_zk_validity_proofs",
                    False,
                    f"Mixed-proof bundle rejected: {effective_proof_count}/{ballot_count} ballots contain proofs",
                )
            else:
                if is_sv31_plus:
                    zk_status = BundleVerificationStatus.NOT_PRESENT.value
                    record(
                        "checkpoint_9_zk_validity_proofs",
                        False,
                        f"Missing required ZK validity proofs in {el_proto} bundle",
                    )
                else:
                    zk_status = BundleVerificationStatus.NOT_PRESENT.value
                    record(
                        "checkpoint_9_zk_validity_proofs",
                        True,
                        "No ZK validity proofs present (v3.0 plaintext ballot mode - NOT_PRESENT)",
                    )

            # -------------------------------------------------------------
            # Checkpoint 10: Homomorphic Aggregation
            # -------------------------------------------------------------
            tally_fp = actual_fp or manifest["election_parameters"].get("key_fingerprint", "")
            enc_tally = None
            try:
                enc_tally = reader.read_json("tally/encrypted_tally.json")
            except Exception:
                pass

            if enc_tally and ballots:
                try:
                    recomputed_tally = aggregate_encrypted_ballots(
                        ballots,
                        election_id,
                        tally_fp,
                    )
                    stored_slots = enc_tally["encrypted_tally"]["slots"]
                    recomputed_slots = recomputed_tally["encrypted_tally"]["slots"]
                    if stored_slots == recomputed_slots:
                        record(
                            "checkpoint_10_homomorphic_aggregation",
                            True,
                            f"Homomorphic aggregation of {ballot_count} ballots independently verified",
                        )
                    else:
                        record(
                            "checkpoint_10_homomorphic_aggregation",
                            False,
                            "Published encrypted tally slots do NOT match independent homomorphic summation",
                        )
                except Exception as e:
                    record(
                        "checkpoint_10_homomorphic_aggregation",
                        False,
                        f"Homomorphic aggregation error: {e}",
                    )
            else:
                record(
                    "checkpoint_10_homomorphic_aggregation",
                    False,
                    "Missing encrypted tally artifact or ballots for aggregation",
                )

            # -------------------------------------------------------------
            # Checkpoint 11: Tally Commitment
            # -------------------------------------------------------------
            try:
                if enc_tally:
                    expected_t_comm = enc_tally.get("commitment", "")
                    recomputed_t_comm = compute_tally_commitment(
                        election_id=election_id,
                        encrypted_tally=enc_tally["encrypted_tally"],
                        ballot_count=enc_tally["ballot_count"],
                        key_fingerprint=tally_fp,
                    )
                    if expected_t_comm == recomputed_t_comm:
                        record(
                            "checkpoint_11_tally_commitment",
                            True,
                            "Tally commitment independently verified from aggregated ciphertexts",
                        )
                    else:
                        record(
                            "checkpoint_11_tally_commitment",
                            False,
                            f"Tally commitment mismatch: {expected_t_comm} != {recomputed_t_comm}",
                        )
                else:
                    record(
                        "checkpoint_11_tally_commitment",
                        False,
                        "Missing encrypted tally for commitment verification",
                    )
            except Exception as e:
                record(
                    "checkpoint_11_tally_commitment",
                    False,
                    f"Tally commitment calculation error: {e}",
                )

            # -------------------------------------------------------------
            # Checkpoints 12-14: Threshold Cryptosystem Verification
            threshold_params = manifest.get("threshold_parameters")
            has_threshold = threshold_params is not None

            if has_threshold:
                from app.crypto.threshold.serialization import (
                    deserialize_dkg_manifest,
                    deserialize_tally_partial_decryption_package,
                    deserialize_threshold_tally_result,
                )
                from app.crypto.threshold.proof import verify_partial_decryption_proof
                from app.crypto.threshold.tally import compute_lagrange_coefficient

                dkg_manifest = None
                # Checkpoint 12: Threshold Manifest Integrity
                try:
                    manifest_data = reader.read_json("threshold/dkg_manifest.json")
                    dkg_manifest = deserialize_dkg_manifest(manifest_data)
                    pub_data_ctx = None
                    try:
                        pub_data_ctx = reader.read_json("context/public_key.json")
                    except Exception:
                        pass

                    if dkg_manifest.threshold != 2 or dkg_manifest.trustee_count != 3 or len(dkg_manifest.qualified_trustees) < 2:
                        record("checkpoint_12_threshold_manifest", False, f"Invalid threshold manifest parameters: t={dkg_manifest.threshold}, n={dkg_manifest.trustee_count}")
                    elif dkg_manifest.election_id != election_id:
                        record("checkpoint_12_threshold_manifest", False, f"Manifest election ID mismatch: {dkg_manifest.election_id} != {election_id}")
                    elif not point_on_curve(dkg_manifest.joint_public_key) or dkg_manifest.joint_public_key.is_infinity:
                        record("checkpoint_12_threshold_manifest", False, "Joint public key is off-curve or at infinity")
                    elif pub_data_ctx and (f"{dkg_manifest.joint_public_key.x:064x}" != pub_data_ctx.get("x") or f"{dkg_manifest.joint_public_key.y:064x}" != pub_data_ctx.get("y")):
                        record("checkpoint_12_threshold_manifest", False, "DKG joint public key does not match election public key")
                    else:
                        record(
                            "checkpoint_12_threshold_manifest",
                            True,
                            f"DKG manifest verified: t={dkg_manifest.threshold}, n={dkg_manifest.trustee_count}, QUAL={dkg_manifest.qualified_trustees}",
                        )
                except Exception as e:
                    record("checkpoint_12_threshold_manifest", False, f"DKG manifest validation failed: {e}")

                # Checkpoint 13: Partial Decryption Proofs
                trustee_pkgs = {}
                t_result = None
                try:
                    for item in inventory:
                        if item["artifact_type"] == "TRUSTEE_PACKAGE":
                            tpkg_data = reader.read_json(item["path"])
                            tid = tpkg_data["trustee_id"]
                            trustee_pkgs[tid] = deserialize_tally_partial_decryption_package(tpkg_data)

                    t_result_data = reader.read_json("threshold/threshold_tally.json")
                    t_result = deserialize_threshold_tally_result(t_result_data)

                    if not dkg_manifest:
                        record("checkpoint_13_partial_decryption_proofs", False, "Cannot verify partial decryption proofs without valid DKG manifest")
                    else:
                        selected = t_result.selected_trustees
                        # Get ciphertext slots from encrypted_tally
                        enc_t_obj = enc_tally.get("encrypted_tally", enc_tally) if enc_tally else {}
                        slot_list = enc_t_obj.get("slots", [])
                        candidate_ids = enc_t_obj.get("candidate_ids", [])
                        slot_a_points = {}
                        for s_idx, cid in enumerate(candidate_ids):
                            ct = deserialize_ciphertext(slot_list[s_idx])
                            slot_a_points[cid] = ct.c1

                        proof_failures = []
                        for tid in selected:
                            if tid not in trustee_pkgs:
                                proof_failures.append(f"Missing trustee package for selected trustee {tid}")
                                continue
                            tpkg = trustee_pkgs[tid]
                            vk = dkg_manifest.get_trustee_verification_key(tid)
                            for cid, share in tpkg.shares.items():
                                if cid not in slot_a_points:
                                    proof_failures.append(f"Trustee {tid} share for unknown candidate {cid}")
                                    continue
                                is_valid = verify_partial_decryption_proof(
                                    proof=share.proof,
                                    y_point=vk,
                                    a_point=slot_a_points[cid],
                                    w_point=share.partial_decryption,
                                    election_id=election_id,
                                    candidate_id=cid,
                                    trustee_id=tid,
                                    protocol_version=share.protocol_version,
                                )
                                if not is_valid:
                                    proof_failures.append(f"Chaum-Pedersen proof failed for trustee {tid}, candidate {cid}")

                        if proof_failures:
                            record("checkpoint_13_partial_decryption_proofs", False, f"Proof failures: {proof_failures[:3]}")
                        else:
                            record("checkpoint_13_partial_decryption_proofs", True, f"Chaum-Pedersen proofs verified for trustees {selected}")
                except Exception as e:
                    record("checkpoint_13_partial_decryption_proofs", False, f"Partial decryption proof verification failed: {e}")

                # Checkpoint 14: Lagrange Combination & Discrete Log
                try:
                    if not dkg_manifest or not t_result:
                        record("checkpoint_14_lagrange_combination_and_dlog", False, "Prerequisites missing for Lagrange combination")
                    else:
                        selected = t_result.selected_trustees
                        if len(selected) != 2 or len(set(selected)) != 2:
                            record("checkpoint_14_lagrange_combination_and_dlog", False, f"Selected trustees must contain exactly 2 distinct trustees, got {selected}")
                        elif any(tid not in dkg_manifest.qualified_trustees for tid in selected):
                            record("checkpoint_14_lagrange_combination_and_dlog", False, f"Selected trustees {selected} must be in QUAL {dkg_manifest.qualified_trustees}")
                        elif any(tid not in trustee_pkgs for tid in selected):
                            record("checkpoint_14_lagrange_combination_and_dlog", False, f"Missing partial decryptions for selected trustees {selected}")
                        else:
                            # Verify point-level Lagrange combination for each candidate
                            enc_t_obj = enc_tally.get("encrypted_tally", enc_tally) if enc_tally else {}
                            slot_list = enc_t_obj.get("slots", [])
                            candidate_ids = enc_t_obj.get("candidate_ids", [])

                            t_i, t_k = selected[0], selected[1]
                            l_i = compute_lagrange_coefficient(t_i, selected)
                            l_k = compute_lagrange_coefficient(t_k, selected)

                            lagrange_failures = []
                            for s_idx, cid in enumerate(candidate_ids):
                                ct = deserialize_ciphertext(slot_list[s_idx])
                                b_pt = ct.c2
                                w_i = trustee_pkgs[t_i].shares[cid].partial_decryption
                                w_k = trustee_pkgs[t_k].shares[cid].partial_decryption
                                d_j = point_add(scalar_mult(l_i, w_i), scalar_mult(l_k, w_k))
                                declared_d = t_result.combined_decryption_points.get(cid)
                                if declared_d != d_j:
                                    lagrange_failures.append(f"Combined D_j mismatch for candidate {cid}")

                                # Verify discrete log plaintext recovery: M_j = B_j - D_j == v_j * G
                                from app.crypto.elgamal import point_negate
                                votes = t_result.candidate_results.get(cid, 0)
                                expected_m = scalar_mult(votes, G)
                                actual_m = point_add(b_pt, point_negate(d_j))
                                if actual_m != expected_m:
                                    lagrange_failures.append(f"Discrete log mismatch for candidate {cid}: votes={votes}")

                            if lagrange_failures:
                                record("checkpoint_14_lagrange_combination_and_dlog", False, f"Lagrange failures: {lagrange_failures[:3]}")
                            else:
                                record("checkpoint_14_lagrange_combination_and_dlog", True, f"Lagrange combination and discrete log recovery verified for trustees {selected}")
                except Exception as e:
                    record("checkpoint_14_lagrange_combination_and_dlog", False, f"Lagrange combination check failed: {e}")
            else:
                record(
                    "checkpoint_12_threshold_manifest",
                    True,
                    "No threshold cryptosystem artifacts present (centralized key mode - NOT_PRESENT)",
                )
                record(
                    "checkpoint_13_partial_decryption_proofs",
                    True,
                    "No threshold partial decryptions (centralized key mode - NOT_PRESENT)",
                )
                record(
                    "checkpoint_14_lagrange_combination_and_dlog",
                    True,
                    "No threshold Lagrange combination (centralized key mode - NOT_PRESENT)",
                )

            # -------------------------------------------------------------
            # Checkpoint 15: Tally Reconciliation
            # -------------------------------------------------------------
            dec_tally = None
            try:
                dec_tally = reader.read_json("tally/decrypted_tally.json")
            except Exception:
                pass

            if dec_tally:
                tallies = dec_tally.get("candidate_tallies", {})
                total_votes = sum(tallies.values())
                declared_ballots = dec_tally.get("total_ballots", 0)
                if total_votes == declared_ballots and total_votes == ballot_count:
                    record(
                        "checkpoint_15_tally_reconciliation",
                        True,
                        f"Zero-drift reconciliation verified: {total_votes} votes == {ballot_count} ballots",
                    )
                else:
                    record(
                        "checkpoint_15_tally_reconciliation",
                        False,
                        f"Reconciliation drift: votes={total_votes}, declared={declared_ballots}, ballots={ballot_count}",
                    )
            elif has_threshold:
                # If threshold tally result exists
                try:
                    t_res = reader.read_json("threshold/threshold_tally.json")
                    total_votes = sum(t_res.get("candidate_results", {}).values())
                    if total_votes == ballot_count and t_res.get("reconciled", False):
                        record(
                            "checkpoint_15_tally_reconciliation",
                            True,
                            f"Threshold tally zero-drift reconciliation verified: {total_votes} votes == {ballot_count} ballots",
                        )
                    else:
                        record(
                            "checkpoint_15_tally_reconciliation",
                            False,
                            f"Threshold reconciliation drift: votes={total_votes}, ballots={ballot_count}",
                        )
                except Exception as e:
                    record(
                        "checkpoint_15_tally_reconciliation",
                        False,
                        f"Threshold reconciliation read error: {e}",
                    )
            else:
                record(
                    "checkpoint_15_tally_reconciliation",
                    True,
                    "No decrypted tally provided; encrypted homomorphic aggregation stage verified",
                )

        finally:
            if reader:
                reader.close()

        c_map = {c["checkpoint"]: (c["status"] == "PASSED") for c in checkpoints}

        return {
            "verified": overall_passed,
            "overall_status": overall_status if overall_passed else BundleVerificationStatus.INVALID.value,
            "bundle_id": election_id,
            "protocol_version": BUNDLE_PROTOCOL_VERSION,
            "election_protocol_version": el_proto,
            "manifest_hash": computed_m_hash if "computed_m_hash" in locals() else "",
            "signature_status": signature_status if "signature_status" in locals() else BundleVerificationStatus.NOT_PRESENT.value,
            "checkpoints_total": len(checkpoints),
            "checkpoints_passed": sum(1 for c in checkpoints if c["status"] == "PASSED"),
            "checkpoints_failed": sum(1 for c in checkpoints if c["status"] == "FAILED"),
            "artifact_checks": {
                "schema_valid": c_map.get("checkpoint_1_bundle_schema", False),
                "manifest_hash_valid": c_map.get("checkpoint_2_manifest_hash", False),
                "inventory_valid": c_map.get("checkpoint_3_inventory_integrity", False),
            },
            "crypto_checks": {
                "public_key_valid": c_map.get("checkpoint_7_public_key", False),
                "ballots_valid": c_map.get("checkpoint_8_ballot_ciphertexts_and_commitments", False),
                "zk_proofs_valid": c_map.get("checkpoint_9_zk_validity_proofs", False),
                "aggregation_valid": c_map.get("checkpoint_10_homomorphic_aggregation", False),
                "tally_commitment_valid": c_map.get("checkpoint_11_tally_commitment", False),
            },
            "threshold_checks": {
                "manifest_valid": c_map.get("checkpoint_12_threshold_manifest", False),
                "partial_proofs_valid": c_map.get("checkpoint_13_partial_decryption_proofs", False),
                "lagrange_valid": c_map.get("checkpoint_14_lagrange_combination_and_dlog", False),
            },
            "tally_checks": {
                "reconciliation_valid": c_map.get("checkpoint_15_tally_reconciliation", False),
            },
            "checkpoints": checkpoints,
            "explicit_limitations": [
                "Verifies supplied cryptographic evidence; does not independently establish voter physical identity or eligibility.",
                "Does not guarantee coercion resistance, receipt-freeness, or physical EVM paper/VVPAT printout equivalence.",
                "Assumes threshold non-collusion (threshold t trustees colluding can reconstruct secret key x).",
                "Does not constitute legal or regulatory election certification.",
            ],
        }
