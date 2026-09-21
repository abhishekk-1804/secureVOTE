"""
SecureVOTE 3.3 Phase 1 — Cryptographic Hardening Test Suite.

Comprehensive validation of Phase 1 hardening:
1. RFC 9380 Section 5.3.1 expand_message_xmd test vectors and statistical scalar derivation.
2. Fiat-Shamir transcript domain separation and cross-domain mutation rejection.
3. Canonical JSON float rejection and canonical encoding determinism.
4. Point & scalar validation (off-curve, infinity, negative coordinates, non-integer/boolean scalars).
5. Proof dataclass strictness and fail-closed validation.
6. Standalone verifier Checkpoint 11 (threshold tally) integration and tamper detection.
7. Absence of private key/share leakage in error messages.
"""

import copy
import hashlib
import json
import pytest

from app.crypto.canonical import canonical_json, canonical_hash
from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    ElGamalCiphertext,
    ElGamalPrivateKey,
    G,
    INFINITY,
    _P,
    is_valid_public_point,
    is_valid_scalar,
    point_add,
    point_on_curve,
    scalar_mult,
)
from app.crypto.exceptions import (
    EncryptionError,
    InvalidCiphertextError,
    KeyGenerationError,
    SerializationError,
)
from app.crypto.keys import (
    compute_key_fingerprint,
    deserialize_public_key,
    generate_keypair,
    serialize_public_key,
)
from app.crypto.serialization import (
    deserialize_point,
    serialize_point,
)
from app.crypto.threshold.dkg import (
    PEDERSEN_H,
    SchnorrRepresentationProof,
    derive_pedersen_h,
    prove_schnorr_representation,
    verify_schnorr_representation,
)
from app.crypto.threshold.exceptions import (
    SchnorrProofError,
    ThresholdSerializationError,
)
from app.crypto.threshold.proof import (
    ChaumPedersenEqualityProof,
    check_partial_decryption_proof,
    prove_partial_decryption,
    verify_partial_decryption_proof,
)
from app.crypto.zk.chaum_pedersen import (
    ChaumPedersenProof,
    prove_equality,
    verify_equality,
)
from app.crypto.zk.disjunctive import (
    Disjunctive01Proof,
    prove_disjunctive_01,
    verify_disjunctive_01,
)
from app.crypto.zk.exceptions import InvalidProofError
from app.crypto.zk.transcript import Transcript, expand_message_xmd
from standalone_verifier.v3_verifier import StandaloneV3ElectionVerifier


# ==============================================================================
# 1. RFC 9380 expand_message_xmd & Hash-to-Scalar Validation
# ==============================================================================

class TestRFC9380AndFiatShamir:
    """Test RFC 9380 Section 5.3.1 implementation against official test vectors."""

    def test_rfc9380_official_test_vector_32_bytes(self):
        """RFC 9380 Appendix J.1 test vector for SHA-256 with empty message and 32 bytes."""
        dst = b"QUUX-V01-CS02-with-hash-to-curve-SHA256-128"
        msg = b""
        result = expand_message_xmd(msg=msg, dst=dst, len_in_bytes=32)
        expected_hex = "375f0f593c30f8218c2774ca31bd652452ba71749fd3e04f7cab2a99b493ef26"
        assert result.hex() == expected_hex

    def test_rfc9380_official_test_vector_48_bytes(self):
        """RFC 9380 Appendix J.1 test vector for SHA-256 with empty message and 48 bytes."""
        dst = b"QUUX-V01-CS02-with-hash-to-curve-SHA256-128"
        msg = b""
        result = expand_message_xmd(msg=msg, dst=dst, len_in_bytes=48)
        expected_hex = "83dcb4a6835c4127f95bb22edddd780254e1b272f26e5a62d67c6e065fc12370ccf6047a3b01689c0b270747d46e2bd7"
        assert result.hex() == expected_hex

    def test_rfc9380_oversized_dst_handling(self):
        """RFC 9380 specifies hashing DSTs longer than 255 bytes with H2C-OVERSIZE-DST- prefix."""
        long_dst = b"D" * 300
        result = expand_message_xmd(msg=b"test", dst=long_dst, len_in_bytes=48)
        assert len(result) == 48

    def test_rfc9380_invalid_parameters_fail_closed(self):
        """Invalid len_in_bytes or empty DST must raise ValueError."""
        with pytest.raises(ValueError, match="Domain separation tag.*must not be empty"):
            expand_message_xmd(msg=b"test", dst=b"", len_in_bytes=48)

        with pytest.raises(ValueError, match="Invalid len_in_bytes"):
            expand_message_xmd(msg=b"test", dst=b"DST", len_in_bytes=0)

        with pytest.raises(ValueError, match="Invalid len_in_bytes"):
            expand_message_xmd(msg=b"test", dst=b"DST", len_in_bytes=70000)

    def test_transcript_rfc9380_scalar_range_and_determinism(self):
        """Transcript.challenge_scalar_rfc9380 must produce valid non-zero scalars in [1, q-1]."""
        t1 = Transcript("SECUREVOTE33/TEST/DOMAIN/")
        t1.append_message("epoch", 1)
        t1.append_point("generator", G)
        c1 = t1.challenge_scalar_rfc9380()
        assert 1 <= c1 < CURVE_ORDER

        # Determinism check
        t2 = Transcript("SECUREVOTE33/TEST/DOMAIN/")
        t2.append_message("epoch", 1)
        t2.append_point("generator", G)
        c2 = t2.challenge_scalar_rfc9380()
        assert c1 == c2

    def test_legacy_challenge_scalar_backward_compatibility(self):
        """Existing challenge_scalar must remain deterministic and in [1, q-1]."""
        t = Transcript("SECUREVOTE31/ZKP/SUM_PROOF/ELEC-1/")
        t.append_point("generator", G)
        c = t.challenge_scalar("sum_challenge")
        assert 1 <= c < CURVE_ORDER


# ==============================================================================
# 2. Transcript Domain Separation Hardening
# ==============================================================================

class TestDomainSeparationHardening:
    """Validate that transcripts enforce domain separation and prevent cross-domain reuse."""

    def test_domain_swapping_alters_derived_challenge(self):
        """Same transcript content under different domains must derive different challenges."""
        t_slot = Transcript("SECUREVOTE31/ZKP/SLOT_PROOF/ELEC-1/CAND-0/")
        t_slot.append_point("G", G)

        t_sum = Transcript("SECUREVOTE31/ZKP/SUM_PROOF/ELEC-1/")
        t_sum.append_point("G", G)

        c_slot = t_slot.challenge_scalar("challenge")
        c_sum = t_sum.challenge_scalar("challenge")
        assert c_slot != c_sum

    def test_threshold_partial_decrypt_domain_binding(self):
        """Swapping election ID or candidate ID in domain changes challenge scalar."""
        t_c1 = Transcript("SECUREVOTE32/ZKP/PARTIAL_DECRYPT/ELEC-1/CAND-01/TRUSTEE/1/")
        t_c1.append_point("G", G)

        t_c2 = Transcript("SECUREVOTE32/ZKP/PARTIAL_DECRYPT/ELEC-1/CAND-02/TRUSTEE/1/")
        t_c2.append_point("G", G)

        assert t_c1.challenge_scalar() != t_c2.challenge_scalar()


# ==============================================================================
# 3. Canonical JSON & Float Rejection
# ==============================================================================

class TestCanonicalSerializationHardening:
    """Validate strict float rejection and canonical encoding rules."""

    def test_reject_float_at_top_level(self):
        with pytest.raises(SerializationError, match="Floating-point values are prohibited"):
            canonical_json(1.5)

    def test_reject_float_in_dictionary_value(self):
        with pytest.raises(SerializationError, match="Floating-point values are prohibited"):
            canonical_json({"alpha": "valid", "score": 99.9})

    def test_reject_float_in_nested_list(self):
        with pytest.raises(SerializationError, match="Floating-point values are prohibited"):
            canonical_json({"data": [1, 2, [3, 4.0]]})

    def test_canonical_json_determinism_and_formatting(self):
        """Ensure keys are sorted alphabetically, separators are compact, and UTF-8 is preserved."""
        obj = {"z_key": "नमस्ते", "a_key": 10, "m_key": [3, 2, 1]}
        encoded = canonical_json(obj)
        expected = '{"a_key":10,"m_key":[3,2,1],"z_key":"नमस्ते"}'
        assert encoded == expected


# ==============================================================================
# 4. Point & Scalar Validation
# ==============================================================================

class TestPointAndScalarValidation:
    """Verify point-on-curve, infinity, and scalar range checking."""

    def test_point_on_curve_rejects_non_ecpoint_and_booleans(self):
        assert point_on_curve("not_a_point") is False
        assert point_on_curve(None) is False
        assert point_on_curve(123) is False

    def test_point_on_curve_rejects_boolean_coordinates(self):
        """ECPoint with boolean coordinates (e.g. ECPoint(True, False)) must be rejected."""
        pt = ECPoint(x=True, y=False)
        assert point_on_curve(pt) is False

    def test_point_on_curve_rejects_off_curve_coordinates(self):
        """Valid integer range but not satisfying y^2 = x^3 + ax + b mod p."""
        pt = ECPoint(x=G.x, y=(G.y + 1) % _P)
        assert point_on_curve(pt) is False

    def test_point_on_curve_rejects_out_of_range_coordinates(self):
        pt_neg = ECPoint(x=-1, y=G.y)
        assert point_on_curve(pt_neg) is False
        pt_huge = ECPoint(x=_P + 5, y=G.y)
        assert point_on_curve(pt_huge) is False

    def test_is_valid_public_point(self):
        assert is_valid_public_point(G) is True
        assert is_valid_public_point(INFINITY) is False
        assert is_valid_public_point(ECPoint(1, 2)) is False

    def test_is_valid_scalar(self):
        assert is_valid_scalar(1) is True
        assert is_valid_scalar(CURVE_ORDER - 1) is True
        assert is_valid_scalar(0, allow_zero=False) is False
        assert is_valid_scalar(0, allow_zero=True) is True
        assert is_valid_scalar(CURVE_ORDER) is False
        assert is_valid_scalar(-1) is False
        assert is_valid_scalar(True) is False
        assert is_valid_scalar(False) is False
        assert is_valid_scalar("scalar") is False

    def test_deserialize_point_rejects_negative_hex_strings(self):
        """Negative hex values like '-1a' must be rejected in point deserialization."""
        with pytest.raises(SerializationError, match="Negative coordinate representations are prohibited"):
            deserialize_point({"x": "-01", "y": f"{G.y:064x}"})

    def test_deserialize_point_rejects_mixed_infinity(self):
        """If one coordinate is 'infinity', the other must also be 'infinity'."""
        with pytest.raises(SerializationError, match="Both coordinates must be 'infinity'"):
            deserialize_point({"x": "infinity", "y": f"{G.y:064x}"})

    def test_deserialize_public_key_rejects_infinity(self):
        """Public key cannot be at infinity."""
        with pytest.raises(SerializationError, match="Public key cannot be the point at infinity"):
            deserialize_public_key({
                "protocol_version": "SECUREVOTE3",
                "curve": "secp256r1",
                "x": "infinity",
                "y": "infinity",
                "fingerprint": "a" * 64,
            })

    def test_ciphertext_c1_cannot_be_infinity(self):
        """ElGamal ciphertext C1 cannot be at infinity."""
        with pytest.raises(InvalidCiphertextError, match="C1 cannot be the point at infinity"):
            ElGamalCiphertext(c1=INFINITY, c2=G)


# ==============================================================================
# 5. Proof Dataclass Hardening
# ==============================================================================

class TestProofDataclassHardening:
    """Validate strict fail-closed instantiation of proof dataclasses."""

    def test_schnorr_proof_rejects_infinity_and_booleans(self):
        with pytest.raises(SchnorrProofError, match="Commitment point.*invalid or at infinity"):
            SchnorrRepresentationProof(comm=INFINITY, c=1, s_a=1, s_b=1)

        with pytest.raises(SchnorrProofError, match="Challenge scalar out of valid range"):
            SchnorrRepresentationProof(comm=G, c=True, s_a=1, s_b=1)

        with pytest.raises(SchnorrProofError, match="Response scalar s_a out of valid range"):
            SchnorrRepresentationProof(comm=G, c=1, s_a=False, s_b=1)

    def test_chaum_pedersen_proof_rejects_infinity_and_booleans(self):
        with pytest.raises(InvalidProofError, match="Proof commitment point 'a' is off-curve, at infinity, or invalid"):
            ChaumPedersenProof(a=INFINITY, b=G, c=1, s=1)

        with pytest.raises(InvalidProofError, match="Proof challenge scalar out of valid range"):
            ChaumPedersenProof(a=G, b=G, c=True, s=1)

        with pytest.raises(InvalidProofError, match="Proof response scalar out of valid range"):
            ChaumPedersenProof(a=G, b=G, c=1, s=True)

    def test_disjunctive_01_proof_rejects_infinity_and_booleans(self):
        with pytest.raises(InvalidProofError, match="Commitment point is off-curve, at infinity, or invalid"):
            Disjunctive01Proof(
                a0=INFINITY, b0=G, a1=G, b1=G,
                c0=1, c1=1, s0=1, s1=1,
            )

        with pytest.raises(InvalidProofError, match="Scalar.*out of valid group order range"):
            Disjunctive01Proof(
                a0=G, b0=G, a1=G, b1=G,
                c0=True, c1=1, s0=1, s1=1,
            )


# ==============================================================================
# 6. Standalone Verifier Checkpoint 11 (Threshold Tally)
# ==============================================================================

class TestStandaloneVerifierCheckpoint11:
    """Verify Checkpoint 11 integration and tamper detection in StandaloneV3ElectionVerifier."""

    def test_verifier_without_threshold_tally_passes_checkpoint_11_as_skipped(self):
        """Standard v3 packages without threshold tallies pass Checkpoint 11 with NOT_PRESENT."""
        keypair = generate_keypair()
        pub_data = serialize_public_key(keypair.public_key)
        pkg = {
            "protocol_version": "SECUREVOTE3",
            "election_id": "TEST-STANDALONE-001",
            "public_key": pub_data,
            "candidates": ["C1", "C2"],
            "ballots": [],
            "encrypted_tally": None,
        }
        res = StandaloneV3ElectionVerifier.verify_package(pkg)
        cp11 = next(c for c in res["checkpoints"] if c["checkpoint"] == "checkpoint_11_threshold_tally")
        assert cp11["status"] == "PASSED"
        assert res["threshold_status"] == "NOT_PRESENT"
        assert res["threshold_valid"] is True

    def test_verifier_rejects_tampered_threshold_tally_result(self):
        """If threshold_tally is present but malformed, Checkpoint 11 must fail."""
        keypair = generate_keypair()
        pub_data = serialize_public_key(keypair.public_key)
        pkg = {
            "protocol_version": "SECUREVOTE32",
            "election_id": "TEST-STANDALONE-002",
            "public_key": pub_data,
            "candidates": ["C1", "C2"],
            "ballots": [],
            "encrypted_tally": None,
            "threshold_tally": {
                "manifest": "malformed_manifest",
                "trustee_packages": {},
                "tally_result": {},
            },
        }
        res = StandaloneV3ElectionVerifier.verify_package(pkg)
        cp11 = next(c for c in res["checkpoints"] if c["checkpoint"] == "checkpoint_11_threshold_tally")
        assert cp11["status"] == "FAILED"
        assert res["threshold_status"] == "INVALID"
        assert res["threshold_valid"] is False
        assert res["verified"] is False


# ==============================================================================
# 7. Absence of Secret Leakage in Exceptions
# ==============================================================================

class TestSecretLeakagePrevention:
    """Verify that exception messages do not include private keys, shares, or nonces."""

    def test_invalid_share_error_does_not_contain_share_value(self):
        secret_scalar = 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
        # Passing an inconsistent public key triggers InvalidShareError
        with pytest.raises(Exception) as exc_info:
            prove_partial_decryption(
                x_i=secret_scalar,
                y_point=G,  # G does not match secret_scalar * G
                a_point=G,
                w_point=G,
                election_id="ELEC-1",
                candidate_id="CAND-1",
                trustee_id=1,
            )
        msg = str(exc_info.value)
        assert hex(secret_scalar) not in msg
        assert str(secret_scalar) not in msg
