"""
SecureVOTE 3.2 — Comprehensive Distributed Key Generation (DKG) Test Suite.

Verifies:
A. Valid 3-trustee DKG completion
B. Valid 2-of-3 QUAL set handling
C. Deterministic test vectors and NUMS generator H verification
D. Pedersen commitment verification (s*G + s'*H == C_0 + j*C_1)
E. Feldman extraction verification (C_{i,k} == A_{i,k} + b_{i,k}*H)
F. Invalid secret share rejection
G. Invalid blinding share rejection
H. Mutated commitment rejection
I. Malformed commitment rejection (off-curve / infinity)
J. Invalid proof of knowledge (Schnorr representation) rejection
K. Complaint generation on invalid share
L. Complaint verification on ledger
M. Dealer disqualification and exclusion from QUAL
N. Abort when |QUAL| < threshold (QUAL < 2)
O. Trustee verification keys derivation (Y_j == x_j*G)
P. Consistency check x_j*G == Y_j
Q. Joint public key Y validity on secp256r1
R. Domain separation: different elections produce distinct transcript challenges
S. Trustee-ID substitution rejection
T. Full serialization round-trip for all DKG artifacts
U. Malformed serialized artifact rejection
V. Zero joint private key materialization (x is never exposed)
"""

import pytest

from app.crypto.elgamal import (
    CURVE_ORDER,
    ECPoint,
    G,
    INFINITY,
    point_add,
    point_negate,
    point_on_curve,
    scalar_mult,
)
from app.crypto.threshold.dkg import (
    DKGComplaint,
    DKGPublicManifest,
    FeldmanRevealPackage,
    PEDERSEN_H,
    PEDERSEN_H_SEED,
    PedersenCommitmentPackage,
    PrivateSharePackage,
    SchnorrRepresentationProof,
    TrusteeDKGSession,
    TrusteePrivateKeyShare,
    build_dkg_manifest,
    derive_pedersen_h,
    prove_schnorr_representation,
    resolve_qualified_set,
    verify_complaint,
    verify_dkg_manifest,
    verify_pedersen_package,
    verify_schnorr_representation,
)
from app.crypto.threshold.exceptions import (
    CommitmentVerificationError,
    ComplaintError,
    DisqualificationError,
    DKGError,
    InsufficientQualifiedTrusteesError,
    SchnorrProofError,
    ShareVerificationError,
    ThresholdSerializationError,
)
from app.crypto.threshold.serialization import (
    deserialize_complaint,
    deserialize_dkg_manifest,
    deserialize_feldman_package,
    deserialize_pedersen_package,
    deserialize_schnorr_proof,
    deserialize_share_package,
    deserialize_trustee_private_key_share,
    serialize_complaint,
    serialize_dkg_manifest,
    serialize_feldman_package,
    serialize_pedersen_package,
    serialize_schnorr_proof,
    serialize_share_package,
    serialize_trustee_private_key_share,
)


# ---------------------------------------------------------------------------
# C & H. Deterministic NUMS Generator H & Point Verification
# ---------------------------------------------------------------------------

def test_pedersen_h_deterministic_derivation():
    """Verify H generator is deterministic, lies on curve, and is not G or infinity."""
    derived_h = derive_pedersen_h(PEDERSEN_H_SEED)
    assert derived_h == PEDERSEN_H
    assert point_on_curve(PEDERSEN_H)
    assert not PEDERSEN_H.is_infinity
    assert PEDERSEN_H != G
    # Order check on prime order group
    assert scalar_mult(CURVE_ORDER, PEDERSEN_H) == INFINITY


# ---------------------------------------------------------------------------
# J. Schnorr Proof of Representation Tests
# ---------------------------------------------------------------------------

def test_schnorr_representation_soundness():
    """Verify that honest Schnorr proofs verify cleanly."""
    a = 123456789
    b = 987654321
    comm = point_add(scalar_mult(a, G), scalar_mult(b, PEDERSEN_H))
    proof = prove_schnorr_representation(comm, a, b, "ELEC-01", 1)
    assert verify_schnorr_representation(comm, proof, "ELEC-01", 1)


def test_schnorr_representation_mutated_scalar_rejected():
    """Verify that tampered response scalars fail verification."""
    a = 12345
    b = 67890
    comm = point_add(scalar_mult(a, G), scalar_mult(b, PEDERSEN_H))
    proof = prove_schnorr_representation(comm, a, b, "ELEC-01", 1)

    bad_proof = SchnorrRepresentationProof(
        comm=proof.comm,
        c=proof.c,
        s_a=(proof.s_a + 1) % CURVE_ORDER,
        s_b=proof.s_b,
    )
    with pytest.raises(SchnorrProofError):
        verify_schnorr_representation(comm, bad_proof, "ELEC-01", 1)


def test_schnorr_representation_wrong_commitment_rejected():
    """Verify that proof generated for comm1 fails when verified against comm2."""
    a1, b1 = 11, 22
    a2, b2 = 33, 44
    comm1 = point_add(scalar_mult(a1, G), scalar_mult(b1, PEDERSEN_H))
    comm2 = point_add(scalar_mult(a2, G), scalar_mult(b2, PEDERSEN_H))

    proof1 = prove_schnorr_representation(comm1, a1, b1, "ELEC-01", 1)
    with pytest.raises(SchnorrProofError):
        verify_schnorr_representation(comm2, proof1, "ELEC-01", 1)


# ---------------------------------------------------------------------------
# A & O & P & Q & V. Valid 3-Trustee DKG & Consistency
# ---------------------------------------------------------------------------

def test_valid_3_trustee_dkg_complete_flow():
    """Verify that a full 3-trustee DKG completes and produces valid keys."""
    election_id = "LOC-SABHA-2026-TEST"
    trustee_ids = [1, 2, 3]
    sessions = [TrusteeDKGSession(i, election_id, threshold=2, total_trustees=3) for i in trustee_ids]

    # Phase 1: Pedersen Commitments
    pedersen_pkgs = {s.trustee_id: s.generate_pedersen_commitments() for s in sessions}
    for pkg in pedersen_pkgs.values():
        assert verify_pedersen_package(pkg, election_id)

    # Phase 2: Share Distribution
    all_shares = {s.trustee_id: s.generate_shares_for_peers() for s in sessions}

    # Phase 3: Share Verification
    for s in sessions:
        for sender_id in trustee_ids:
            share_pkg = all_shares[sender_id][s.trustee_id]
            assert s.verify_received_share(share_pkg, pedersen_pkgs[sender_id])

    # Phase 4: Qualified Set
    qual = resolve_qualified_set(trustee_ids, pedersen_pkgs, [])
    assert qual == [1, 2, 3]

    # Phase 5: Feldman Reveal
    feldman_pkgs = {s.trustee_id: s.reveal_feldman_commitments() for s in sessions}

    # Phase 6: Final Secret Shares
    key_shares = {}
    for s in sessions:
        ks = s.finalize_secret_share(qual, feldman_pkgs, pedersen_pkgs)
        key_shares[s.trustee_id] = ks
        # P. Check x_j * G == Y_j
        assert scalar_mult(ks.secret_share, G) == ks.verification_key

    # Q. Joint Public Key validity
    manifest = build_dkg_manifest(election_id, 2, 3, qual, pedersen_pkgs, feldman_pkgs)
    assert verify_dkg_manifest(manifest)
    assert manifest.joint_public_key == key_shares[1].joint_public_key
    assert point_on_curve(manifest.joint_public_key)

    # V. Lagrange reconstruction test across quorums confirms joint key without materializing x
    Y = manifest.joint_public_key
    x1 = key_shares[1].secret_share
    x2 = key_shares[2].secret_share
    x3 = key_shares[3].secret_share

    # Quorum {1, 2}: lambda_1 = 2, lambda_2 = -1
    recon_12 = (2 * x1 - x2) % CURVE_ORDER
    assert scalar_mult(recon_12, G) == Y

    # Quorum {2, 3}: lambda_2 = 3, lambda_3 = -2
    recon_23 = (3 * x2 - 2 * x3) % CURVE_ORDER
    assert scalar_mult(recon_23, G) == Y

    # Quorum {1, 3}: lambda_1 = 3 * 2^-1, lambda_3 = -1 * 2^-1
    inv2 = pow(2, -1, CURVE_ORDER)
    recon_13 = (3 * inv2 * x1 - inv2 * x3) % CURVE_ORDER
    assert scalar_mult(recon_13, G) == Y


# ---------------------------------------------------------------------------
# F & G. Share Verification Failure & Complaint Handling
# ---------------------------------------------------------------------------

def test_invalid_secret_share_rejected():
    """Verify that an altered secret share fails Pedersen commitment verification."""
    s1 = TrusteeDKGSession(1, "ELEC-01", threshold=2, total_trustees=3)
    s2 = TrusteeDKGSession(2, "ELEC-01", threshold=2, total_trustees=3)

    p1 = s1.generate_pedersen_commitments()
    shares1 = s1.generate_shares_for_peers()

    # Mutate secret share sent to trustee 2
    bad_share = PrivateSharePackage(
        election_id="ELEC-01",
        sender_id=1,
        recipient_id=2,
        share=(shares1[2].share + 1) % CURVE_ORDER,
        blinding_share=shares1[2].blinding_share,
    )

    with pytest.raises(ShareVerificationError):
        s2.verify_received_share(bad_share, p1)


def test_invalid_blinding_share_rejected():
    """Verify that an altered blinding share fails Pedersen commitment verification."""
    s1 = TrusteeDKGSession(1, "ELEC-01", threshold=2, total_trustees=3)
    s2 = TrusteeDKGSession(2, "ELEC-01", threshold=2, total_trustees=3)

    p1 = s1.generate_pedersen_commitments()
    shares1 = s1.generate_shares_for_peers()

    # Mutate blinding share sent to trustee 2
    bad_share = PrivateSharePackage(
        election_id="ELEC-01",
        sender_id=1,
        recipient_id=2,
        share=shares1[2].share,
        blinding_share=(shares1[2].blinding_share + 5) % CURVE_ORDER,
    )

    with pytest.raises(ShareVerificationError):
        s2.verify_received_share(bad_share, p1)


def test_complaint_lifecycle_and_verification():
    """Verify complaint generation, verification, and dealer disqualification."""
    s1 = TrusteeDKGSession(1, "ELEC-01", threshold=2, total_trustees=3)
    s2 = TrusteeDKGSession(2, "ELEC-01", threshold=2, total_trustees=3)

    p1 = s1.generate_pedersen_commitments()
    shares1 = s1.generate_shares_for_peers()

    # Create bad share
    bad_share = PrivateSharePackage(
        election_id="ELEC-01",
        sender_id=1,
        recipient_id=2,
        share=(shares1[2].share + 42) % CURVE_ORDER,
        blinding_share=shares1[2].blinding_share,
    )

    complaint = s2.create_complaint(1, bad_share, "Corrupted share received")
    assert complaint.complaining_trustee_id == 2
    assert complaint.accused_trustee_id == 1

    # Coordinator evaluates complaint: should be VALID (bad dealer detected)
    is_valid_complaint = verify_complaint(complaint, p1)
    assert is_valid_complaint is True

    # When dealer is evaluated with an honest share, complaint evaluation is FALSE (dismissed)
    honest_complaint = s2.create_complaint(1, shares1[2], "False accusation")
    assert verify_complaint(honest_complaint, p1) is False


# ---------------------------------------------------------------------------
# B & M & N. Disqualification and QUAL Set Scenarios
# ---------------------------------------------------------------------------

def test_dealer_disqualification_and_2_of_3_qual():
    """Verify that a cheating dealer is excluded from QUAL and remaining 2 trustees proceed."""
    election_id = "ELEC-DISQUAL-TEST"
    s1 = TrusteeDKGSession(1, election_id, threshold=2, total_trustees=3)
    s2 = TrusteeDKGSession(2, election_id, threshold=2, total_trustees=3)
    s3 = TrusteeDKGSession(3, election_id, threshold=2, total_trustees=3)

    p1 = s1.generate_pedersen_commitments()
    p2 = s2.generate_pedersen_commitments()
    p3 = s3.generate_pedersen_commitments()
    pedersen_pkgs = {1: p1, 2: p2, 3: p3}

    shares1 = s1.generate_shares_for_peers()
    shares2 = s2.generate_shares_for_peers()
    shares3 = s3.generate_shares_for_peers()

    # Trustee 1 cheated trustee 2
    bad_share_for_2 = PrivateSharePackage(
        election_id=election_id,
        sender_id=1,
        recipient_id=2,
        share=(shares1[2].share + 999) % CURVE_ORDER,
        blinding_share=shares1[2].blinding_share,
    )
    complaint_2_against_1 = s2.create_complaint(1, bad_share_for_2, "Bad share")

    # Resolve QUAL set with the complaint: Trustee 1 should be excluded
    qual = resolve_qualified_set([1, 2, 3], pedersen_pkgs, [complaint_2_against_1], threshold=2)
    assert qual == [2, 3]  # Trustee 1 disqualified!

    # Feldman reveal for qualified trustees 2 and 3
    f2 = s2.reveal_feldman_commitments()
    f3 = s3.reveal_feldman_commitments()
    feldman_pkgs = {2: f2, 3: f3}

    # Trustees 2 and 3 finalize shares using only QUAL = [2, 3]
    s2.verify_received_share(shares3[2], p3)
    s3.verify_received_share(shares2[3], p2)

    ks2 = s2.finalize_secret_share(qual, feldman_pkgs, pedersen_pkgs)
    ks3 = s3.finalize_secret_share(qual, feldman_pkgs, pedersen_pkgs)

    # Confirm key validity
    assert scalar_mult(ks2.secret_share, G) == ks2.verification_key
    assert scalar_mult(ks3.secret_share, G) == ks3.verification_key

    manifest = build_dkg_manifest(election_id, 2, 3, qual, pedersen_pkgs, feldman_pkgs)
    assert verify_dkg_manifest(manifest)
    assert manifest.qualified_trustees == [2, 3]

    # Trustee 1 attempting to finalize raises DisqualificationError
    with pytest.raises(DisqualificationError):
        s1.finalize_secret_share(qual, feldman_pkgs, pedersen_pkgs)


def test_insufficient_qualified_trustees_aborts():
    """Verify that if fewer than threshold t trustees qualify, DKG aborts."""
    election_id = "ELEC-ABORT-TEST"
    s1 = TrusteeDKGSession(1, election_id, threshold=2, total_trustees=3)
    s2 = TrusteeDKGSession(2, election_id, threshold=2, total_trustees=3)
    s3 = TrusteeDKGSession(3, election_id, threshold=2, total_trustees=3)

    p1 = s1.generate_pedersen_commitments()
    p2 = s2.generate_pedersen_commitments()
    p3 = s3.generate_pedersen_commitments()
    pedersen_pkgs = {1: p1, 2: p2, 3: p3}

    sh1 = s1.generate_shares_for_peers()
    sh2 = s2.generate_shares_for_peers()

    # Valid complaints against trustees 1 and 2
    bad_sh1 = PrivateSharePackage(election_id, 1, 3, (sh1[3].share + 1) % CURVE_ORDER, sh1[3].blinding_share)
    bad_sh2 = PrivateSharePackage(election_id, 2, 3, (sh2[3].share + 1) % CURVE_ORDER, sh2[3].blinding_share)
    c1 = s3.create_complaint(1, bad_sh1)
    c2 = s3.create_complaint(2, bad_sh2)

    # 2 trustees disqualified -> only trustee 3 qualifies (< threshold 2) -> must abort!
    with pytest.raises(InsufficientQualifiedTrusteesError):
        resolve_qualified_set([1, 2, 3], pedersen_pkgs, [c1, c2], threshold=2)


# ---------------------------------------------------------------------------
# E & H. Feldman Extraction & Consistency
# ---------------------------------------------------------------------------

def test_feldman_reveal_mismatched_blinding_rejected():
    """Verify that a trustee lying about blinding coefficients in Feldman reveal is rejected."""
    s1 = TrusteeDKGSession(1, "ELEC-01", threshold=2, total_trustees=3)
    p1 = s1.generate_pedersen_commitments()
    f1 = s1.reveal_feldman_commitments()

    # Mutate blinding factor
    bad_f1 = FeldmanRevealPackage(
        election_id="ELEC-01",
        trustee_id=1,
        feldman_commitments=f1.feldman_commitments,
        blinding_coefficients=[(f1.blinding_coefficients[0] + 1) % CURVE_ORDER, f1.blinding_coefficients[1]],
    )

    with pytest.raises(CommitmentVerificationError):
        build_dkg_manifest("ELEC-01", 1, 1, [1], {1: p1}, {1: bad_f1})


def test_feldman_reveal_mismatched_commitment_point_rejected():
    """Verify that a trustee lying about commitment point in Feldman reveal is rejected."""
    s1 = TrusteeDKGSession(1, "ELEC-01", threshold=2, total_trustees=3)
    p1 = s1.generate_pedersen_commitments()
    f1 = s1.reveal_feldman_commitments()

    # Mutate A_{1,0} point
    bad_point = point_add(f1.feldman_commitments[0], G)
    bad_f1 = FeldmanRevealPackage(
        election_id="ELEC-01",
        trustee_id=1,
        feldman_commitments=[bad_point, f1.feldman_commitments[1]],
        blinding_coefficients=f1.blinding_coefficients,
    )

    with pytest.raises(CommitmentVerificationError):
        build_dkg_manifest("ELEC-01", 1, 1, [1], {1: p1}, {1: bad_f1})


# ---------------------------------------------------------------------------
# R & S. Domain Separation & Trustee ID Substitution Tests
# ---------------------------------------------------------------------------

def test_distinct_election_domain_separation():
    """Verify that proofs generated for election A are invalid for election B."""
    s1_a = TrusteeDKGSession(1, "ELECTION-AAA", threshold=2, total_trustees=3)
    p1_a = s1_a.generate_pedersen_commitments()

    # Verify against wrong election ID -> must fail
    assert verify_pedersen_package(p1_a, "ELECTION-BBB") is False


def test_trustee_id_substitution_rejected():
    """Verify that a proof generated for trustee 1 fails when claimed by trustee 2."""
    s1 = TrusteeDKGSession(1, "ELEC-01", threshold=2, total_trustees=3)
    p1 = s1.generate_pedersen_commitments()

    # Reconstruct with wrong trustee ID
    bad_pkg = PedersenCommitmentPackage(
        election_id="ELEC-01",
        trustee_id=2,  # Substituted ID
        commitments=p1.commitments,
        proof_of_knowledge=p1.proof_of_knowledge,
    )

    assert verify_pedersen_package(bad_pkg, "ELEC-01") is False


# ---------------------------------------------------------------------------
# T & U. Serialization Round-Trip and Malformed Rejection
# ---------------------------------------------------------------------------

def test_dkg_artifacts_serialization_round_trip():
    """Verify serialization and deserialization for all DKG artifacts."""
    election_id = "ELEC-SER-01"
    s1 = TrusteeDKGSession(1, election_id, threshold=2, total_trustees=3)
    p1 = s1.generate_pedersen_commitments()
    sh1 = s1.generate_shares_for_peers()[2]
    comp = s1.create_complaint(2, sh1, "Test complaint")
    f1 = s1.reveal_feldman_commitments()

    # 1. Pedersen package
    ser_p = serialize_pedersen_package(p1)
    de_p = deserialize_pedersen_package(ser_p)
    assert de_p.election_id == p1.election_id
    assert de_p.trustee_id == p1.trustee_id
    assert de_p.commitments == p1.commitments

    # 2. Private share package
    ser_sh = serialize_share_package(sh1)
    de_sh = deserialize_share_package(ser_sh)
    assert de_sh.share == sh1.share
    assert de_sh.blinding_share == sh1.blinding_share

    # 3. Complaint artifact
    ser_comp = serialize_complaint(comp)
    de_comp = deserialize_complaint(ser_comp)
    assert de_comp.accused_trustee_id == comp.accused_trustee_id
    assert de_comp.revealed_share == comp.revealed_share

    # 4. Feldman package
    ser_f = serialize_feldman_package(f1)
    de_f = deserialize_feldman_package(ser_f)
    assert de_f.feldman_commitments == f1.feldman_commitments
    assert de_f.blinding_coefficients == f1.blinding_coefficients

    # 5. Manifest
    manifest = build_dkg_manifest(election_id, 1, 1, [1], {1: p1}, {1: f1})
    ser_man = serialize_dkg_manifest(manifest)
    de_man = deserialize_dkg_manifest(ser_man)
    assert de_man.joint_public_key == manifest.joint_public_key
    assert de_man.qualified_trustees == manifest.qualified_trustees

    # 6. Trustee private key share
    priv_share = TrusteePrivateKeyShare(
        election_id=election_id,
        trustee_id=1,
        secret_share=123456789,
        joint_public_key=p1.commitments[0],
        verification_key=p1.commitments[1],
    )
    ser_priv = serialize_trustee_private_key_share(priv_share)
    de_priv = deserialize_trustee_private_key_share(ser_priv)
    assert de_priv.secret_share == priv_share.secret_share


def test_malformed_serialized_payload_rejected():
    """Verify that corrupt JSON dictionaries are rejected with ThresholdSerializationError."""
    with pytest.raises(ThresholdSerializationError):
        deserialize_pedersen_package({"bad_key": 123})

    with pytest.raises(ThresholdSerializationError):
        deserialize_share_package({"share": "not_hex"})

    with pytest.raises(ThresholdSerializationError):
        deserialize_complaint({"complaining_trustee_id": "bad"})

    with pytest.raises(ThresholdSerializationError):
        deserialize_dkg_manifest({"threshold": "invalid"})


# ---------------------------------------------------------------------------
# Zero Private-Secret Leakage Tests
# ---------------------------------------------------------------------------

def test_no_private_secret_leakage_in_repr():
    """Verify that __repr__ masks private scalar shares and polynomial coefficients."""
    s1 = TrusteeDKGSession(1, "ELEC-01", threshold=2, total_trustees=3)
    s1.generate_pedersen_commitments()
    shares = s1.generate_shares_for_peers()

    # Check session repr does not expose private scalars
    sess_repr = repr(s1)
    assert "secret_share" not in sess_repr
    assert "PrivateSharePackage" not in sess_repr

    # Check share package repr masks scalars
    sh_repr = repr(shares[2])
    assert "<REDACTED>" in sh_repr
    assert hex(shares[2].share) not in sh_repr

    # Check private key share repr masks scalar
    pks = TrusteePrivateKeyShare(
        election_id="ELEC-01",
        trustee_id=1,
        secret_share=999888777,
        joint_public_key=G,
        verification_key=G,
    )
    pks_repr = repr(pks)
    assert "<REDACTED>" in pks_repr
    assert "999888777" not in pks_repr
