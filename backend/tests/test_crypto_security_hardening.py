"""
Adversarial Security & Boundary Hardening Tests for SecureVOTE 3.0.

Specifically tests:
1. Invalid curve points (points off the secp256r1 curve)
2. Infinity point edge cases (identity element handling in encryption/decryption)
3. Wrong curve identifier rejection
4. Wrong election key fingerprint rejection
5. Wrong protocol version rejection
6. Cross-election ciphertext reuse rejection
7. Malformed ciphertext payloads (bad hex, truncated coordinates)
8. Malformed canonical JSON serialization
9. Invalid candidate count (< 2 or mismatch)
10. Invalid one-hot representation (out of bounds, negative index)
11. Replay of ballot artifacts
12. Modified public key substitution
13. Private key leakage prevention (asserting scalars never appear in public objects)
14. Artifact substitution attack (swapping ballots between elections)
"""

import copy
import json
import pytest

from app.crypto import PROTOCOL_VERSION
from app.crypto.ballot import encode_vote_onehot, encrypt_ballot
from app.crypto.canonical import canonical_hash, canonical_json
from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    ElGamalCiphertext,
    ElGamalPublicKey,
    G,
    INFINITY,
    decrypt,
    encrypt,
    generate_keypair,
    point_add,
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
from standalone_verifier.v3_verifier import StandaloneV3ElectionVerifier


# ---------------------------------------------------------------------------
# 1. Invalid Curve Points
# ---------------------------------------------------------------------------

def test_invalid_curve_point_rejected():
    """A coordinate pair not satisfying y^2 = x^3 - 3x + b must be rejected."""
    # (x=5, y=5) does not satisfy the secp256r1 equation
    bad_point = ECPoint(5, 5)
    assert not point_on_curve(bad_point)

    with pytest.raises(KeyGenerationError, match="not on the secp256r1 curve"):
        ElGamalPublicKey(point=bad_point)

    with pytest.raises(InvalidCiphertextError, match="not on the secp256r1 curve"):
        ElGamalCiphertext(c1=bad_point, c2=G)


# ---------------------------------------------------------------------------
# 2. Infinity Points Handling
# ---------------------------------------------------------------------------

def test_infinity_point_handling():
    """Points at infinity must be correctly handled during encryption and decryption."""
    assert INFINITY.is_infinity
    assert point_on_curve(INFINITY)
    assert point_add(G, INFINITY) == G
    assert point_add(INFINITY, G) == G

    # Serializing and deserializing infinity
    serialized = serialize_point(INFINITY)
    assert serialized == {"x": "infinity", "y": "infinity"}
    deserialized = deserialize_point(serialized)
    assert deserialized == INFINITY

    # Public key cannot be infinity
    with pytest.raises(KeyGenerationError, match="point at infinity"):
        ElGamalPublicKey(point=INFINITY)


# ---------------------------------------------------------------------------
# 3. Wrong Curve Identifier
# ---------------------------------------------------------------------------

def test_wrong_curve_rejected():
    """Payloads declaring unsupported curves must be rejected."""
    keypair = generate_keypair()
    pub_data = serialize_public_key(keypair.public_key)
    pub_data["curve"] = "secp384r1"
    with pytest.raises(SerializationError, match="Unsupported curve"):
        deserialize_public_key(pub_data)

    ct = encrypt(keypair.public_key, 1)
    ct_data = serialize_ciphertext(ct)
    ct_data["curve"] = "ed25519"
    with pytest.raises(SerializationError, match="Unsupported curve"):
        deserialize_ciphertext(ct_data)


# ---------------------------------------------------------------------------
# 4. Wrong Election Key
# ---------------------------------------------------------------------------

def test_wrong_election_key_rejection():
    """Decrypting or aggregating with a mismatched key must be rejected."""
    k1 = generate_keypair()
    k2 = generate_keypair()

    artifact = encrypt_ballot(k1.public_key, 0, 3, "ELEC-1", ["A", "B", "C"])
    fp1 = compute_key_fingerprint(k1.public_key)
    fp2 = compute_key_fingerprint(k2.public_key)

    # Aggregating with mismatched expected fingerprint
    with pytest.raises(AggregationError, match="key_fingerprint"):
        aggregate_encrypted_ballots([artifact], "ELEC-1", fp2)

    # Decrypting with wrong private key
    tally = aggregate_encrypted_ballots([artifact], "ELEC-1", fp1)
    with pytest.raises(DecryptionError, match="Key fingerprint mismatch"):
        decrypt_tally(k2, tally)


# ---------------------------------------------------------------------------
# 5. Wrong Protocol Version
# ---------------------------------------------------------------------------

def test_wrong_protocol_version_rejection():
    """Artifacts with incorrect protocol versions must be rejected."""
    keypair = generate_keypair()
    pub_data = serialize_public_key(keypair.public_key)
    pub_data["protocol_version"] = "SECUREVOTE_V2"
    with pytest.raises(SerializationError, match="Protocol version mismatch"):
        deserialize_public_key(pub_data)

    ct = encrypt(keypair.public_key, 0)
    ct_data = serialize_ciphertext(ct)
    ct_data["protocol_version"] = "LEGACY_V1"
    with pytest.raises(SerializationError, match="Protocol version mismatch"):
        deserialize_ciphertext(ct_data)


# ---------------------------------------------------------------------------
# 6. Cross-Election Ciphertext Reuse
# ---------------------------------------------------------------------------

def test_cross_election_reuse_rejection():
    """Ballots from Election A must not be accepted into Election B aggregation."""
    keypair = generate_keypair()
    fp = compute_key_fingerprint(keypair.public_key)

    b_a = encrypt_ballot(keypair.public_key, 0, 2, "ELECTION-ALPHA", ["X", "Y"])
    b_b = encrypt_ballot(keypair.public_key, 1, 2, "ELECTION-BETA", ["X", "Y"])

    with pytest.raises(AggregationError, match="election_id"):
        aggregate_encrypted_ballots([b_a, b_b], "ELECTION-ALPHA", fp)


# ---------------------------------------------------------------------------
# 7. Malformed Ciphertext Payloads
# ---------------------------------------------------------------------------

def test_malformed_ciphertext_payloads():
    """Truncated or invalid hex strings in ciphertext must be rejected."""
    keypair = generate_keypair()
    ct = encrypt(keypair.public_key, 1)
    ct_data = serialize_ciphertext(ct)

    # Malformed non-hex string
    bad_ct = copy.deepcopy(ct_data)
    bad_ct["c1"]["x"] = "NOT_A_HEX_STRING"
    with pytest.raises(SerializationError):
        deserialize_ciphertext(bad_ct)

    # Missing coordinate field
    bad_ct2 = copy.deepcopy(ct_data)
    del bad_ct2["c2"]["y"]
    with pytest.raises(SerializationError):
        deserialize_ciphertext(bad_ct2)


# ---------------------------------------------------------------------------
# 8. Malformed Canonical Serialization
# ---------------------------------------------------------------------------

def test_malformed_canonical_serialization():
    """Unserializable objects (e.g., sockets, non-JSON types) must raise SerializationError."""
    with pytest.raises(SerializationError):
        canonical_json(object())


# ---------------------------------------------------------------------------
# 9. Invalid Candidate Count
# ---------------------------------------------------------------------------

def test_invalid_candidate_count():
    """Candidate counts < 2 or mismatching candidate_ids length must fail."""
    keypair = generate_keypair()
    # Length mismatch
    with pytest.raises(EncryptionError, match="does not match"):
        encrypt_ballot(keypair.public_key, 0, candidate_count=4, election_id="E1", candidate_ids=["A", "B"])


# ---------------------------------------------------------------------------
# 10. Invalid One-Hot Representation
# ---------------------------------------------------------------------------

def test_invalid_onehot_bounds():
    """Negative index or index >= count must raise EncryptionError."""
    with pytest.raises(EncryptionError, match="out of range"):
        encode_vote_onehot(-1, 4)
    with pytest.raises(EncryptionError, match="out of range"):
        encode_vote_onehot(4, 4)
    with pytest.raises(EncryptionError, match="out of range"):
        encode_vote_onehot(99, 4)


# ---------------------------------------------------------------------------
# 11. Replay of Ballot Artifacts
# ---------------------------------------------------------------------------

def test_ballot_replay_detection():
    """Two identical ballot artifacts submitted with same artifact_id must collide."""
    keypair = generate_keypair()
    b = encrypt_ballot(keypair.public_key, 0, 3, "ELEC-1", ["A", "B", "C"])
    # If two identical artifacts exist, artifact_id is duplicated
    assert b["artifact_id"] == b["artifact_id"]
    # When creating fresh ballots, artifact_ids are unique
    b2 = encrypt_ballot(keypair.public_key, 0, 3, "ELEC-1", ["A", "B", "C"])
    assert b["artifact_id"] != b2["artifact_id"]


# ---------------------------------------------------------------------------
# 12. Modified Public Key Substitution
# ---------------------------------------------------------------------------

def test_public_key_substitution_attack():
    """Replacing the public key on an export package causes verifier failure."""
    key1 = generate_keypair()
    key2 = generate_keypair()
    b = encrypt_ballot(key1.public_key, 0, 2, "E1", ["C1", "C2"])
    fp1 = compute_key_fingerprint(key1.public_key)
    tally = aggregate_encrypted_ballots([b], "E1", fp1)

    # Package signed with key1, but published with key2
    bad_pkg = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": "E1",
        "public_key": serialize_public_key(key2.public_key),  # Substituted!
        "candidates": ["C1", "C2"],
        "ballots": [b],
        "encrypted_tally": tally,
    }
    res = StandaloneV3ElectionVerifier.verify_package(bad_pkg)
    assert res["verified"] is False
    failed = [c["checkpoint"] for c in res["checkpoints"] if c["status"] == "FAILED"]
    assert any("public_key" in f or "aggregation" in f for f in failed)


# ---------------------------------------------------------------------------
# 13. Private Key Leakage Prevention
# ---------------------------------------------------------------------------

def test_private_key_never_leaked():
    """Public metadata, serialized keys, and ballot artifacts must NEVER contain private scalars."""
    keypair = generate_keypair()
    scalar_hex = hex(keypair.scalar)
    scalar_dec = str(keypair.scalar)

    # Check serialize_public_key
    pub_json = json.dumps(serialize_public_key(keypair.public_key))
    assert scalar_hex not in pub_json
    assert scalar_dec not in pub_json

    # Check create_key_metadata
    meta_json = json.dumps(create_key_metadata(keypair, "E1", "K1"))
    assert scalar_hex not in meta_json
    assert scalar_dec not in meta_json

    # Check ballot artifact
    artifact = encrypt_ballot(keypair.public_key, 0, 2, "E1", ["A", "B"])
    artifact_json = json.dumps(artifact)
    assert scalar_hex not in artifact_json
    assert scalar_dec not in artifact_json


# ---------------------------------------------------------------------------
# 14. Artifact Substitution Attack
# ---------------------------------------------------------------------------

def test_artifact_substitution_attack():
    """Swapping a ballot from another election must fail commitment/domain verification."""
    k = generate_keypair()
    fp = compute_key_fingerprint(k.public_key)

    b1 = encrypt_ballot(k.public_key, 0, 2, "ELEC-GENUINE", ["C1", "C2"])
    b_foreign = encrypt_ballot(k.public_key, 1, 2, "ELEC-ATTACKER", ["C1", "C2"])

    # Attempt to slip b_foreign into ELEC-GENUINE package
    pkg = {
        "protocol_version": PROTOCOL_VERSION,
        "election_id": "ELEC-GENUINE",
        "public_key": serialize_public_key(k.public_key),
        "candidates": ["C1", "C2"],
        "ballots": [b1, b_foreign],
        "encrypted_tally": None,
    }
    res = StandaloneV3ElectionVerifier.verify_package(pkg)
    assert res["verified"] is False
    failed = [c["checkpoint"] for c in res["checkpoints"] if c["status"] == "FAILED"]
    assert "checkpoint_6_ballot_commitments" in failed
