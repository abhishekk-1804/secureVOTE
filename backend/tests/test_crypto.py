"""
Tests for SecureVOTE 3.0 Cryptographic Core.

Tests cover:
1. ElGamal keygen, encrypt, decrypt
2. Homomorphic property (additive aggregation)
3. One-hot ballot encoding
4. Encrypted ballot artifact creation and verification
5. Tally aggregation and decryption
6. Commitment integrity
7. Canonical serialization determinism
8. Key serialization round-trip
9. Ciphertext serialization round-trip
10. Domain separation
11. V3 verifier checkpoints
12. Attack scenarios against v3 artifacts
"""

import copy
import hashlib
import json
import os
import sys
import uuid

import pytest

# Ensure the backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encode_vote_onehot, encrypt_ballot
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
    verify_ballot_commitment,
)
from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    ElGamalCiphertext,
    ElGamalPrivateKey,
    ElGamalPublicKey,
    G,
    INFINITY,
    add_ciphertexts,
    aggregate,
    decrypt,
    encrypt,
    generate_keypair,
    point_add,
    point_negate,
    point_on_curve,
    scalar_mult,
)
from app.crypto.exceptions import (
    AggregationError,
    CommitmentError,
    DecryptionError,
    EncryptionError,
    InvalidCiphertextError,
    KeyGenerationError,
    SerializationError,
    VerificationError,
)
from app.crypto.keys import (
    compute_key_fingerprint,
    create_key_metadata,
    deserialize_public_key,
    serialize_public_key,
)
from app.crypto.serialization import (
    deserialize_ciphertext,
    deserialize_point,
    serialize_ciphertext,
    serialize_point,
)
from app.crypto.tally import aggregate_encrypted_ballots, decrypt_tally
from app.crypto.verification import V3Verifier


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def keypair():
    """Generate a fresh ElGamal keypair for each test."""
    return generate_keypair()


@pytest.fixture
def election_config():
    """Standard test election configuration."""
    return {
        "election_id": "TEST-ELECTION-001",
        "candidate_ids": ["C1", "C2", "C3", "NOTA"],
        "candidate_count": 4,
    }


# ===================================================================
# 1. Point Arithmetic
# ===================================================================

class TestPointArithmetic:
    def test_generator_on_curve(self):
        """Generator point G must be on secp256r1."""
        assert point_on_curve(G)

    def test_infinity_on_curve(self):
        """Point at infinity is on curve by convention."""
        assert point_on_curve(INFINITY)

    def test_add_infinity_identity(self):
        """P + O = P (infinity is the identity element)."""
        assert point_add(G, INFINITY) == G
        assert point_add(INFINITY, G) == G

    def test_add_inverse_gives_infinity(self):
        """P + (-P) = O."""
        neg_g = point_negate(G)
        result = point_add(G, neg_g)
        assert result.is_infinity

    def test_scalar_mult_zero(self):
        """0·G = O."""
        assert scalar_mult(0, G).is_infinity

    def test_scalar_mult_one(self):
        """1·G = G."""
        assert scalar_mult(1, G) == G

    def test_scalar_mult_associative(self):
        """(a·b)·G = a·(b·G)."""
        a, b = 17, 23
        left = scalar_mult(a * b, G)
        right = scalar_mult(a, scalar_mult(b, G))
        assert left == right

    def test_point_add_commutative(self):
        """P + Q = Q + P."""
        p = scalar_mult(7, G)
        q = scalar_mult(13, G)
        assert point_add(p, q) == point_add(q, p)


# ===================================================================
# 2. ElGamal Core
# ===================================================================

class TestElGamalCore:
    def test_keygen_produces_valid_key(self, keypair):
        """Keygen must produce a valid private key with correct public key."""
        assert 1 <= keypair.scalar < CURVE_ORDER
        assert point_on_curve(keypair.public_key.point)
        assert not keypair.public_key.point.is_infinity

    def test_keygen_deterministic_public_key(self, keypair):
        """Public key must equal scalar * G."""
        expected_point = scalar_mult(keypair.scalar, G)
        assert keypair.public_key.point == expected_point

    def test_encrypt_decrypt_zero(self, keypair):
        """Encrypt(0) and decrypt should recover 0."""
        ct = encrypt(keypair.public_key, 0)
        result = decrypt(keypair, ct)
        assert result == 0

    def test_encrypt_decrypt_one(self, keypair):
        """Encrypt(1) and decrypt should recover 1."""
        ct = encrypt(keypair.public_key, 1)
        result = decrypt(keypair, ct)
        assert result == 1

    def test_encrypt_decrypt_small_values(self, keypair):
        """Encrypt and decrypt small integers [0..10]."""
        for m in range(11):
            ct = encrypt(keypair.public_key, m)
            result = decrypt(keypair, ct)
            assert result == m, f"Failed for m={m}"

    def test_encrypt_produces_different_ciphertexts(self, keypair):
        """Two encryptions of the same message should differ (random nonce)."""
        ct1 = encrypt(keypair.public_key, 1)
        ct2 = encrypt(keypair.public_key, 1)
        # C1 should differ (different random r)
        assert ct1.c1 != ct2.c1 or ct1.c2 != ct2.c2

    def test_wrong_key_decryption_fails(self):
        """Decryption with wrong key should fail or produce wrong result."""
        key1 = generate_keypair()
        key2 = generate_keypair()
        ct = encrypt(key1.public_key, 5)
        # Decrypting with wrong key should not give 5
        try:
            result = decrypt(key2, ct, max_value=100)
            assert result != 5  # Should not recover correct plaintext
        except DecryptionError:
            pass  # Also acceptable — BSGS doesn't find it

    def test_ciphertext_on_curve(self, keypair):
        """Both components of ciphertext must be on curve."""
        ct = encrypt(keypair.public_key, 42)
        assert point_on_curve(ct.c1)
        assert point_on_curve(ct.c2)


# ===================================================================
# 3. Homomorphic Property
# ===================================================================

class TestHomomorphicProperty:
    def test_additive_homomorphism_basic(self, keypair):
        """Enc(3) + Enc(5) should decrypt to 8."""
        ct1 = encrypt(keypair.public_key, 3)
        ct2 = encrypt(keypair.public_key, 5)
        ct_sum = add_ciphertexts(ct1, ct2)
        result = decrypt(keypair, ct_sum)
        assert result == 8

    def test_aggregate_multiple(self, keypair):
        """Aggregate [Enc(1), Enc(1), Enc(1)] should decrypt to 3."""
        cts = [encrypt(keypair.public_key, 1) for _ in range(3)]
        agg = aggregate(cts)
        result = decrypt(keypair, agg)
        assert result == 3

    def test_aggregate_mixed_values(self, keypair):
        """Aggregate [Enc(0), Enc(1), Enc(0), Enc(1), Enc(1)] should decrypt to 3."""
        values = [0, 1, 0, 1, 1]
        cts = [encrypt(keypair.public_key, v) for v in values]
        agg = aggregate(cts)
        result = decrypt(keypair, agg)
        assert result == sum(values)

    def test_aggregate_100_ballots(self, keypair):
        """Aggregate 100 Enc(1) ballots should decrypt to 100."""
        cts = [encrypt(keypair.public_key, 1) for _ in range(100)]
        agg = aggregate(cts)
        result = decrypt(keypair, agg)
        assert result == 100

    def test_aggregate_empty_raises(self):
        """Aggregating empty list must raise AggregationError."""
        with pytest.raises(AggregationError):
            aggregate([])

    def test_homomorphic_onehot_tally(self, keypair):
        """
        Simulate 10 voters voting for 4 candidates.
        Voters 0-3 → Candidate 0
        Voters 4-6 → Candidate 1
        Voters 7-8 → Candidate 2
        Voter 9   → Candidate 3 (NOTA)
        Expected tally: [4, 3, 2, 1]
        """
        candidate_count = 4
        votes = [0, 0, 0, 0, 1, 1, 1, 2, 2, 3]

        # Encrypt all slots per ballot
        all_slot_ciphertexts: list[list[ElGamalCiphertext]] = []
        for vote in votes:
            onehot = encode_vote_onehot(vote, candidate_count)
            encrypted_slots = [encrypt(keypair.public_key, v) for v in onehot]
            all_slot_ciphertexts.append(encrypted_slots)

        # Aggregate per slot
        tallied = []
        for slot_idx in range(candidate_count):
            slot_cts = [ballot[slot_idx] for ballot in all_slot_ciphertexts]
            agg = aggregate(slot_cts)
            count = decrypt(keypair, agg)
            tallied.append(count)

        assert tallied == [4, 3, 2, 1]
        assert sum(tallied) == len(votes)


# ===================================================================
# 4. One-Hot Encoding
# ===================================================================

class TestOneHotEncoding:
    def test_encode_first_candidate(self):
        assert encode_vote_onehot(0, 4) == [1, 0, 0, 0]

    def test_encode_last_candidate(self):
        assert encode_vote_onehot(3, 4) == [0, 0, 0, 1]

    def test_encode_middle_candidate(self):
        assert encode_vote_onehot(1, 3) == [0, 1, 0]

    def test_encode_out_of_range_raises(self):
        with pytest.raises(EncryptionError):
            encode_vote_onehot(4, 4)

    def test_encode_negative_raises(self):
        with pytest.raises(EncryptionError):
            encode_vote_onehot(-1, 4)


# ===================================================================
# 5. Encrypted Ballot Artifact
# ===================================================================

class TestEncryptedBallot:
    def test_encrypt_ballot_structure(self, keypair, election_config):
        """Encrypted ballot artifact must have all required fields."""
        artifact = encrypt_ballot(
            public_key=keypair.public_key,
            candidate_index=0,
            candidate_count=election_config["candidate_count"],
            election_id=election_config["election_id"],
            candidate_ids=election_config["candidate_ids"],
        )
        assert artifact["protocol_version"] == PROTOCOL_VERSION
        assert artifact["artifact_type"] == "ENCRYPTED_BALLOT"
        assert artifact["election_id"] == election_config["election_id"]
        assert "artifact_id" in artifact
        assert "encrypted_vote" in artifact
        assert "commitment" in artifact
        assert "key_fingerprint" in artifact
        assert "artifact_hash" in artifact

    def test_encrypt_ballot_different_artifacts(self, keypair, election_config):
        """Two ballots for the same candidate should produce different artifacts."""
        a1 = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        a2 = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        # Different artifact IDs
        assert a1["artifact_id"] != a2["artifact_id"]
        # Different commitments (because artifact_id differs)
        assert a1["commitment"] != a2["commitment"]

    def test_encrypt_ballot_mismatched_ids_raises(self, keypair, election_config):
        """Mismatched candidate_ids length must raise."""
        with pytest.raises(EncryptionError):
            encrypt_ballot(
                keypair.public_key, 0,
                candidate_count=4,
                election_id="E1",
                candidate_ids=["C1", "C2"],  # Only 2, but count is 4
            )


# ===================================================================
# 6. Canonical Serialization
# ===================================================================

class TestCanonicalSerialization:
    def test_canonical_json_deterministic(self):
        """Same data must always produce the same JSON string."""
        data = {"b": 2, "a": 1, "c": 3}
        s1 = canonical_json(data)
        s2 = canonical_json(data)
        assert s1 == s2
        assert s1 == '{"a":1,"b":2,"c":3}'

    def test_canonical_json_no_whitespace(self):
        """Canonical JSON must have no whitespace."""
        data = {"key": "value", "number": 42}
        result = canonical_json(data)
        assert " " not in result
        assert "\n" not in result
        assert "\t" not in result

    def test_domain_separation_different(self):
        """Different domains must produce different hashes."""
        data = {"test": "value"}
        h1 = canonical_hash(data, domain="SECUREVOTE3/BALLOT/E1/")
        h2 = canonical_hash(data, domain="SECUREVOTE3/TALLY/E1/")
        assert h1 != h2

    def test_domain_prefix_format(self):
        assert ballot_domain("E1") == "SECUREVOTE3/BALLOT/E1/"
        assert commitment_domain("E1") == "SECUREVOTE3/COMMITMENT/E1/"
        assert tally_domain("E1") == "SECUREVOTE3/TALLY/E1/"


# ===================================================================
# 7. Key Serialization
# ===================================================================

class TestKeySerialization:
    def test_public_key_round_trip(self, keypair):
        """Serialize → deserialize must recover same public key."""
        serialized = serialize_public_key(keypair.public_key)
        deserialized = deserialize_public_key(serialized)
        assert deserialized.point == keypair.public_key.point

    def test_key_fingerprint_deterministic(self, keypair):
        """Same key must always produce same fingerprint."""
        fp1 = compute_key_fingerprint(keypair.public_key)
        fp2 = compute_key_fingerprint(keypair.public_key)
        assert fp1 == fp2

    def test_different_keys_different_fingerprints(self):
        """Different keys must produce different fingerprints."""
        k1 = generate_keypair()
        k2 = generate_keypair()
        assert compute_key_fingerprint(k1.public_key) != compute_key_fingerprint(k2.public_key)

    def test_wrong_protocol_version_raises(self, keypair):
        """Deserializing with wrong protocol version must raise."""
        serialized = serialize_public_key(keypair.public_key)
        serialized["protocol_version"] = "WRONG"
        with pytest.raises(SerializationError):
            deserialize_public_key(serialized)

    def test_key_metadata_excludes_private_key(self, keypair):
        """Key metadata must not contain the private scalar."""
        meta = create_key_metadata(keypair, "E1", "KEY-1")
        meta_json = json.dumps(meta)
        assert str(keypair.scalar) not in meta_json
        assert hex(keypair.scalar) not in meta_json


# ===================================================================
# 8. Ciphertext Serialization
# ===================================================================

class TestCiphertextSerialization:
    def test_ciphertext_round_trip(self, keypair):
        """Serialize → deserialize must preserve ciphertext."""
        ct = encrypt(keypair.public_key, 42)
        serialized = serialize_ciphertext(ct)
        deserialized = deserialize_ciphertext(serialized)
        assert deserialized.c1 == ct.c1
        assert deserialized.c2 == ct.c2

    def test_serialize_includes_protocol_version(self, keypair):
        ct = encrypt(keypair.public_key, 1)
        serialized = serialize_ciphertext(ct)
        assert serialized["protocol_version"] == PROTOCOL_VERSION
        assert serialized["curve"] == "secp256r1"

    def test_wrong_curve_raises(self, keypair):
        ct = encrypt(keypair.public_key, 1)
        serialized = serialize_ciphertext(ct)
        serialized["curve"] = "secp384r1"
        with pytest.raises(SerializationError):
            deserialize_ciphertext(serialized)


# ===================================================================
# 9. Commitment Integrity
# ===================================================================

class TestCommitmentIntegrity:
    def test_commitment_changes_on_mutation(self, keypair, election_config):
        """Mutating any field must change the commitment."""
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        original_commitment = artifact["commitment"]

        # Mutate the artifact_id
        mutated = copy.deepcopy(artifact)
        mutated["artifact_id"] = str(uuid.uuid4())
        recomputed = compute_ballot_commitment(
            election_id=mutated["election_id"],
            artifact_id=mutated["artifact_id"],
            encrypted_vote=mutated["encrypted_vote"],
            candidate_count=mutated["encrypted_vote"]["candidate_count"],
            key_fingerprint=mutated["key_fingerprint"],
        )
        assert recomputed != original_commitment

    def test_verify_ballot_commitment_passes(self, keypair, election_config):
        """Valid commitment should pass verification."""
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        result = verify_ballot_commitment(
            expected_commitment=artifact["commitment"],
            election_id=artifact["election_id"],
            artifact_id=artifact["artifact_id"],
            encrypted_vote=artifact["encrypted_vote"],
            candidate_count=artifact["encrypted_vote"]["candidate_count"],
            key_fingerprint=artifact["key_fingerprint"],
        )
        assert result is True

    def test_verify_ballot_commitment_rejects_tampered(self, keypair, election_config):
        """Tampered artifact should fail commitment verification."""
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        with pytest.raises(CommitmentError):
            verify_ballot_commitment(
                expected_commitment=artifact["commitment"],
                election_id="TAMPERED-ELECTION",  # Changed!
                artifact_id=artifact["artifact_id"],
                encrypted_vote=artifact["encrypted_vote"],
                candidate_count=artifact["encrypted_vote"]["candidate_count"],
                key_fingerprint=artifact["key_fingerprint"],
            )


# ===================================================================
# 10. Tally (End-to-End)
# ===================================================================

class TestTallyEndToEnd:
    def test_full_tally_10_voters_4_candidates(self, keypair, election_config):
        """
        End-to-end: 10 voters, 4 candidates.
        Expected: C1=4, C2=3, C3=2, NOTA=1
        """
        votes = [0, 0, 0, 0, 1, 1, 1, 2, 2, 3]
        artifacts = []
        for v in votes:
            a = encrypt_ballot(
                keypair.public_key, v,
                election_config["candidate_count"],
                election_config["election_id"],
                election_config["candidate_ids"],
            )
            artifacts.append(a)

        key_fp = compute_key_fingerprint(keypair.public_key)

        # Aggregate
        tally_artifact = aggregate_encrypted_ballots(
            artifacts,
            election_config["election_id"],
            key_fp,
        )
        assert tally_artifact["artifact_type"] == "ENCRYPTED_TALLY"
        assert tally_artifact["ballot_count"] == 10

        # Decrypt
        result = decrypt_tally(keypair, tally_artifact, max_ballots=100)
        assert result["candidate_tallies"] == {
            "C1": 4, "C2": 3, "C3": 2, "NOTA": 1,
        }
        assert result["total_ballots"] == 10
        assert result["reconciliation_status"] == "BALANCED"

    def test_tally_wrong_key_rejects(self, election_config):
        """Decrypting tally with wrong key must raise."""
        key1 = generate_keypair()
        key2 = generate_keypair()

        artifacts = [
            encrypt_ballot(
                key1.public_key, 0,
                election_config["candidate_count"],
                election_config["election_id"],
                election_config["candidate_ids"],
            )
        ]
        key_fp = compute_key_fingerprint(key1.public_key)
        tally_artifact = aggregate_encrypted_ballots(
            artifacts, election_config["election_id"], key_fp,
        )

        with pytest.raises(DecryptionError, match="Key fingerprint mismatch"):
            decrypt_tally(key2, tally_artifact)

    def test_aggregate_mismatched_election_rejects(self, keypair, election_config):
        """Aggregating ballots from different elections must raise."""
        a1 = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            "ELECTION-A",
            election_config["candidate_ids"],
        )
        a2 = encrypt_ballot(
            keypair.public_key, 1,
            election_config["candidate_count"],
            "ELECTION-B",
            election_config["candidate_ids"],
        )
        key_fp = compute_key_fingerprint(keypair.public_key)
        with pytest.raises(AggregationError, match="election_id"):
            aggregate_encrypted_ballots([a1, a2], "ELECTION-A", key_fp)


# ===================================================================
# 11. V3 Verifier
# ===================================================================

class TestV3Verifier:
    def test_verify_full_ballot_all_pass(self, keypair, election_config):
        """All verifier checkpoints should pass for a valid ballot."""
        artifact = encrypt_ballot(
            keypair.public_key, 2,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        pub_data = serialize_public_key(keypair.public_key)
        results = V3Verifier.verify_full_ballot(artifact, pub_data)
        for r in results:
            assert r["status"] == "PASSED", f"Checkpoint {r['checkpoint']} failed: {r['details']}"

    def test_verify_detects_tampered_commitment(self, keypair, election_config):
        """Verifier should detect a tampered commitment."""
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        artifact["commitment"] = "0" * 64  # Tamper
        pub_data = serialize_public_key(keypair.public_key)
        results = V3Verifier.verify_full_ballot(artifact, pub_data)
        commitment_result = [r for r in results if r["checkpoint"] == "ballot_commitment"][0]
        assert commitment_result["status"] == "FAILED"

    def test_verify_detects_tampered_hash(self, keypair, election_config):
        """Verifier should detect a tampered artifact hash."""
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        artifact["artifact_hash"] = "f" * 64  # Tamper
        pub_data = serialize_public_key(keypair.public_key)
        results = V3Verifier.verify_full_ballot(artifact, pub_data)
        hash_result = [r for r in results if r["checkpoint"] == "ballot_artifact_hash"][0]
        assert hash_result["status"] == "FAILED"

    def test_verify_detects_wrong_protocol_version(self, keypair, election_config):
        """Verifier should detect wrong protocol version."""
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        artifact["protocol_version"] = "SECUREVOTE2"  # Wrong version
        pub_data = serialize_public_key(keypair.public_key)
        results = V3Verifier.verify_full_ballot(artifact, pub_data)
        version_result = [r for r in results if r["checkpoint"] == "protocol_version"][0]
        assert version_result["status"] == "FAILED"

    def test_verify_detects_key_mismatch(self, keypair, election_config):
        """Verifier should detect key fingerprint mismatch."""
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        # Use a different key for verification
        other_key = generate_keypair()
        other_pub_data = serialize_public_key(other_key.public_key)
        results = V3Verifier.verify_full_ballot(artifact, other_pub_data)
        key_result = [r for r in results if r["checkpoint"] == "key_metadata"][0]
        assert key_result["status"] == "FAILED"

    def test_verify_full_tally_all_pass(self, keypair, election_config):
        """All tally verifier checkpoints should pass for valid tally."""
        artifacts = [
            encrypt_ballot(
                keypair.public_key, i % election_config["candidate_count"],
                election_config["candidate_count"],
                election_config["election_id"],
                election_config["candidate_ids"],
            )
            for i in range(8)
        ]
        key_fp = compute_key_fingerprint(keypair.public_key)
        tally = aggregate_encrypted_ballots(
            artifacts, election_config["election_id"], key_fp,
        )
        decrypted = decrypt_tally(keypair, tally, max_ballots=100)
        results = V3Verifier.verify_full_tally(tally, decrypted)
        for r in results:
            assert r["status"] == "PASSED", f"Checkpoint {r['checkpoint']} failed: {r['details']}"


# ===================================================================
# 12. Attack Scenarios
# ===================================================================

class TestV3AttackScenarios:
    def test_attack_ciphertext_mutation(self, keypair, election_config):
        """
        Attack: Mutate a ciphertext slot in an encrypted ballot.
        Expected: Commitment and artifact hash verification should fail.
        """
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        # Mutate C1 of first slot
        tampered = copy.deepcopy(artifact)
        tampered["encrypted_vote"]["slots"][0]["c1"]["x"] = "00" * 32

        pub_data = serialize_public_key(keypair.public_key)
        results = V3Verifier.verify_full_ballot(tampered, pub_data)

        # At least commitment or hash should fail
        failed = [r for r in results if r["status"] == "FAILED"]
        assert len(failed) > 0, "Ciphertext mutation was not detected"

    def test_attack_swap_candidate_ids(self, keypair, election_config):
        """
        Attack: Swap candidate_ids order to reassign tallies.
        Expected: Commitment verification should fail.
        """
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        tampered = copy.deepcopy(artifact)
        ids = tampered["encrypted_vote"]["candidate_ids"]
        ids[0], ids[1] = ids[1], ids[0]  # Swap first two

        pub_data = serialize_public_key(keypair.public_key)
        results = V3Verifier.verify_full_ballot(tampered, pub_data)
        failed = [r for r in results if r["status"] == "FAILED"]
        assert len(failed) > 0, "Candidate ID swap was not detected"

    def test_attack_cross_election_aggregation(self, keypair):
        """
        Attack: Aggregate ballots from different elections.
        Expected: Aggregation should raise AggregationError.
        """
        a1 = encrypt_ballot(
            keypair.public_key, 0, 2, "ELECTION-X", ["C1", "C2"],
        )
        a2 = encrypt_ballot(
            keypair.public_key, 1, 2, "ELECTION-Y", ["C1", "C2"],
        )
        key_fp = compute_key_fingerprint(keypair.public_key)
        with pytest.raises(AggregationError):
            aggregate_encrypted_ballots([a1, a2], "ELECTION-X", key_fp)

    def test_attack_wrong_key_decryption(self, election_config):
        """
        Attack: Decrypt tally with unauthorized key.
        Expected: Key fingerprint check should reject.
        """
        legit_key = generate_keypair()
        attacker_key = generate_keypair()

        artifacts = [
            encrypt_ballot(
                legit_key.public_key, 0,
                election_config["candidate_count"],
                election_config["election_id"],
                election_config["candidate_ids"],
            )
        ]
        key_fp = compute_key_fingerprint(legit_key.public_key)
        tally = aggregate_encrypted_ballots(
            artifacts, election_config["election_id"], key_fp,
        )
        with pytest.raises(DecryptionError, match="Key fingerprint mismatch"):
            decrypt_tally(attacker_key, tally)

    def test_attack_inject_extra_ballot(self, keypair, election_config):
        """
        Attack: Inject an extra ballot to inflate tallies.
        Expected: ballot_count in tally won't match external records.
        (This test verifies the reconciliation check at decryption time.)
        """
        legit_ballots = [
            encrypt_ballot(
                keypair.public_key, 0,
                election_config["candidate_count"],
                election_config["election_id"],
                election_config["candidate_ids"],
            )
            for _ in range(5)
        ]
        # Inject one extra
        injected = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        all_ballots = legit_ballots + [injected]

        key_fp = compute_key_fingerprint(keypair.public_key)
        tally = aggregate_encrypted_ballots(
            all_ballots, election_config["election_id"], key_fp,
        )

        # Tally will report ballot_count=6 (including injected)
        # but decryption should succeed — the injection is only
        # detectable by comparing against authoritative ballot count
        result = decrypt_tally(keypair, tally, max_ballots=100)
        assert result["total_ballots"] == 6  # Reflects the injection
        assert result["reconciliation_status"] == "BALANCED"  # Math is correct

    def test_attack_protocol_version_downgrade(self, keypair, election_config):
        """
        Attack: Change protocol version to bypass v3 verification.
        Expected: Protocol version check should fail.
        """
        artifact = encrypt_ballot(
            keypair.public_key, 0,
            election_config["candidate_count"],
            election_config["election_id"],
            election_config["candidate_ids"],
        )
        artifact["protocol_version"] = "SECUREVOTE2"
        result = V3Verifier.verify_protocol_version(artifact)
        assert result["status"] == "FAILED"
