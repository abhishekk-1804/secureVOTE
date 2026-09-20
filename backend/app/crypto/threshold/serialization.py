"""
SecureVOTE 3.2 — Canonical Serialization for Threshold Cryptography Artifacts.

Provides deterministic, canonical serialization and deserialization for:
- DKG Pedersen Commitments
- Schnorr Proofs of Knowledge
- Private Trustee Shares (internal storage)
- Complaint Artifacts
- Feldman Reveal Packages
- DKG Public Manifests
"""

from typing import Any

from app.crypto.elgamal import CURVE_ORDER, ECPoint
from app.crypto.serialization import deserialize_point, serialize_point
from app.crypto.threshold.exceptions import ThresholdSerializationError


def serialize_schnorr_proof(proof: Any) -> dict[str, Any]:
    """Serialize a Schnorr representation proof into a canonical dictionary."""
    return {
        "proof_type": "SCHNORR_REPRESENTATION_POK",
        "comm": serialize_point(proof.comm),
        "c": f"{proof.c:064x}",
        "s_a": f"{proof.s_a:064x}",
        "s_b": f"{proof.s_b:064x}",
    }


def deserialize_schnorr_proof(data: dict[str, Any]) -> Any:
    """Deserialize a Schnorr representation proof from a dictionary."""
    try:
        from app.crypto.threshold.dkg import SchnorrRepresentationProof
        comm = deserialize_point(data["comm"])
        c = int(data["c"], 16)
        s_a = int(data["s_a"], 16)
        s_b = int(data["s_b"], 16)
        return SchnorrRepresentationProof(comm=comm, c=c, s_a=s_a, s_b=s_b)
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed Schnorr proof payload: {e}")


def serialize_pedersen_package(pkg: Any) -> dict[str, Any]:
    """Serialize a Trustee Pedersen commitment package for ledger broadcast."""
    return {
        "protocol_version": "SECUREVOTE32",
        "artifact_type": "DKG_PEDERSEN_COMMITMENT_PACKAGE",
        "election_id": pkg.election_id,
        "trustee_id": pkg.trustee_id,
        "commitments": [serialize_point(pt) for pt in pkg.commitments],
        "proof_of_knowledge": serialize_schnorr_proof(pkg.proof_of_knowledge),
    }


def deserialize_pedersen_package(data: dict[str, Any]) -> Any:
    """Deserialize a Trustee Pedersen commitment package from dictionary."""
    try:
        from app.crypto.threshold.dkg import PedersenCommitmentPackage
        election_id = data["election_id"]
        trustee_id = int(data["trustee_id"])
        commitments = [deserialize_point(pt) for pt in data["commitments"]]
        pok = deserialize_schnorr_proof(data["proof_of_knowledge"])
        return PedersenCommitmentPackage(
            election_id=election_id,
            trustee_id=trustee_id,
            commitments=commitments,
            proof_of_knowledge=pok,
        )
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed Pedersen commitment package: {e}")


def serialize_share_package(pkg: Any) -> dict[str, Any]:
    """Serialize a private share package for point-to-point trustee communication."""
    return {
        "protocol_version": "SECUREVOTE32",
        "artifact_type": "DKG_PRIVATE_SHARE_PACKAGE",
        "election_id": pkg.election_id,
        "sender_id": pkg.sender_id,
        "recipient_id": pkg.recipient_id,
        "share": f"{pkg.share:064x}",
        "blinding_share": f"{pkg.blinding_share:064x}",
    }


def deserialize_share_package(data: dict[str, Any]) -> Any:
    """Deserialize a private share package."""
    try:
        from app.crypto.threshold.dkg import PrivateSharePackage
        return PrivateSharePackage(
            election_id=data["election_id"],
            sender_id=int(data["sender_id"]),
            recipient_id=int(data["recipient_id"]),
            share=int(data["share"], 16),
            blinding_share=int(data["blinding_share"], 16),
        )
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed private share package: {e}")


def serialize_complaint(complaint: Any) -> dict[str, Any]:
    """Serialize a DKG complaint artifact for ledger broadcast."""
    return {
        "protocol_version": "SECUREVOTE32",
        "artifact_type": "DKG_COMPLAINT_ARTIFACT",
        "election_id": complaint.election_id,
        "complaining_trustee_id": complaint.complaining_trustee_id,
        "accused_trustee_id": complaint.accused_trustee_id,
        "revealed_share": f"{complaint.revealed_share:064x}",
        "revealed_blinding_share": f"{complaint.revealed_blinding_share:064x}",
        "reason": complaint.reason,
    }


def deserialize_complaint(data: dict[str, Any]) -> Any:
    """Deserialize a DKG complaint artifact."""
    try:
        from app.crypto.threshold.dkg import DKGComplaint
        return DKGComplaint(
            election_id=data["election_id"],
            complaining_trustee_id=int(data["complaining_trustee_id"]),
            accused_trustee_id=int(data["accused_trustee_id"]),
            revealed_share=int(data["revealed_share"], 16),
            revealed_blinding_share=int(data["revealed_blinding_share"], 16),
            reason=str(data.get("reason", "")),
        )
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed complaint artifact: {e}")


def serialize_feldman_package(pkg: Any) -> dict[str, Any]:
    """Serialize a Phase 5 Feldman reveal package."""
    return {
        "protocol_version": "SECUREVOTE32",
        "artifact_type": "DKG_FELDMAN_REVEAL_PACKAGE",
        "election_id": pkg.election_id,
        "trustee_id": pkg.trustee_id,
        "feldman_commitments": [serialize_point(pt) for pt in pkg.feldman_commitments],
        "blinding_coefficients": [f"{sc:064x}" for sc in pkg.blinding_coefficients],
    }


def deserialize_feldman_package(data: dict[str, Any]) -> Any:
    """Deserialize a Phase 5 Feldman reveal package."""
    try:
        from app.crypto.threshold.dkg import FeldmanRevealPackage
        return FeldmanRevealPackage(
            election_id=data["election_id"],
            trustee_id=int(data["trustee_id"]),
            feldman_commitments=[deserialize_point(pt) for pt in data["feldman_commitments"]],
            blinding_coefficients=[int(sc, 16) for sc in data["blinding_coefficients"]],
        )
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed Feldman reveal package: {e}")


def serialize_dkg_manifest(manifest: Any) -> dict[str, Any]:
    """Serialize a final DKG public manifest."""
    return {
        "protocol_version": "SECUREVOTE32",
        "artifact_type": "DKG_PUBLIC_MANIFEST",
        "election_id": manifest.election_id,
        "threshold": manifest.threshold,
        "trustee_count": manifest.trustee_count,
        "qualified_trustees": manifest.qualified_trustees,
        "joint_public_key": serialize_point(manifest.joint_public_key),
        "trustee_verification_keys": [
            {"trustee_id": item["trustee_id"], "point": serialize_point(item["point"])}
            for item in manifest.trustee_verification_keys
        ],
        "pedersen_commitments": [
            {"trustee_id": item["trustee_id"], "commitments": [serialize_point(pt) for pt in item["commitments"]]}
            for item in manifest.pedersen_commitments
        ],
        "feldman_commitments": [
            {"trustee_id": item["trustee_id"], "commitments": [serialize_point(pt) for pt in item["commitments"]]}
            for item in manifest.feldman_commitments
        ],
    }


def deserialize_dkg_manifest(data: dict[str, Any]) -> Any:
    """Deserialize a final DKG public manifest."""
    try:
        from app.crypto.threshold.dkg import DKGPublicManifest
        return DKGPublicManifest(
            election_id=data["election_id"],
            threshold=int(data["threshold"]),
            trustee_count=int(data["trustee_count"]),
            qualified_trustees=[int(x) for x in data["qualified_trustees"]],
            joint_public_key=deserialize_point(data["joint_public_key"]),
            trustee_verification_keys=[
                {"trustee_id": int(item["trustee_id"]), "point": deserialize_point(item["point"])}
                for item in data["trustee_verification_keys"]
            ],
            pedersen_commitments=[
                {"trustee_id": int(item["trustee_id"]), "commitments": [deserialize_point(pt) for pt in item["commitments"]]}
                for item in data["pedersen_commitments"]
            ],
            feldman_commitments=[
                {"trustee_id": int(item["trustee_id"]), "commitments": [deserialize_point(pt) for pt in item["commitments"]]}
                for item in data["feldman_commitments"]
            ],
        )
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed DKG public manifest: {e}")


def serialize_trustee_private_key_share(share: Any) -> dict[str, Any]:
    """Serialize a private trustee key share for secure local storage."""
    return {
        "protocol_version": "SECUREVOTE32",
        "artifact_type": "TRUSTEE_PRIVATE_KEY_SHARE",
        "election_id": share.election_id,
        "trustee_id": share.trustee_id,
        "secret_share": f"{share.secret_share:064x}",
        "joint_public_key": serialize_point(share.joint_public_key),
        "verification_key": serialize_point(share.verification_key),
    }


def deserialize_trustee_private_key_share(data: dict[str, Any]) -> Any:
    """Deserialize a private trustee key share."""
    try:
        from app.crypto.threshold.dkg import TrusteePrivateKeyShare
        return TrusteePrivateKeyShare(
            election_id=data["election_id"],
            trustee_id=int(data["trustee_id"]),
            secret_share=int(data["secret_share"], 16),
            joint_public_key=deserialize_point(data["joint_public_key"]),
            verification_key=deserialize_point(data["verification_key"]),
        )
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed private key share payload: {e}")


def serialize_partial_decryption_proof(proof: Any) -> dict[str, Any]:
    """Serialize a Chaum-Pedersen partial decryption proof."""
    return {
        "proof_type": "CHAUM_PEDERSEN_DLOG_EQUALITY",
        "comm_1": serialize_point(proof.comm_1),
        "comm_2": serialize_point(proof.comm_2),
        "c": f"{proof.c:064x}",
        "s": f"{proof.s:064x}",
    }


def deserialize_partial_decryption_proof(data: dict[str, Any]) -> Any:
    """Deserialize a Chaum-Pedersen partial decryption proof."""
    try:
        from app.crypto.threshold.proof import ChaumPedersenEqualityProof
        comm_1 = deserialize_point(data["comm_1"])
        comm_2 = deserialize_point(data["comm_2"])
        c = int(data["c"], 16)
        s = int(data["s"], 16)
        return ChaumPedersenEqualityProof(comm_1=comm_1, comm_2=comm_2, c=c, s=s)
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed partial decryption proof payload: {e}")


def serialize_partial_decryption_share(share: Any) -> dict[str, Any]:
    """Serialize a PartialDecryptionShare for public ledger broadcast."""
    return {
        "protocol_version": share.protocol_version,
        "artifact_type": "PARTIAL_DECRYPTION_SHARE",
        "election_id": share.election_id,
        "candidate_id": share.candidate_id,
        "trustee_id": share.trustee_id,
        "partial_decryption": serialize_point(share.partial_decryption),
        "proof": serialize_partial_decryption_proof(share.proof),
    }


def deserialize_partial_decryption_share(data: dict[str, Any]) -> Any:
    """Deserialize a PartialDecryptionShare."""
    try:
        from app.crypto.threshold.decryption import PartialDecryptionShare
        return PartialDecryptionShare(
            election_id=data["election_id"],
            candidate_id=data["candidate_id"],
            trustee_id=int(data["trustee_id"]),
            partial_decryption=deserialize_point(data["partial_decryption"]),
            proof=deserialize_partial_decryption_proof(data["proof"]),
            protocol_version=data.get("protocol_version", "SECUREVOTE32"),
        )
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed partial decryption share payload: {e}")


def serialize_tally_partial_decryption_package(pkg: Any) -> dict[str, Any]:
    """Serialize a complete tally partial decryption package."""
    return {
        "protocol_version": pkg.protocol_version,
        "artifact_type": "TALLY_PARTIAL_DECRYPTION_PACKAGE",
        "election_id": pkg.election_id,
        "trustee_id": pkg.trustee_id,
        "shares": {
            cand_id: serialize_partial_decryption_share(share)
            for cand_id, share in pkg.shares.items()
        },
    }


def deserialize_tally_partial_decryption_package(data: dict[str, Any]) -> Any:
    """Deserialize a complete tally partial decryption package."""
    try:
        from app.crypto.threshold.decryption import TallyPartialDecryptionPackage
        shares = {
            cand_id: deserialize_partial_decryption_share(share_data)
            for cand_id, share_data in data["shares"].items()
        }
        return TallyPartialDecryptionPackage(
            election_id=data["election_id"],
            trustee_id=int(data["trustee_id"]),
            shares=shares,
            protocol_version=data.get("protocol_version", "SECUREVOTE32"),
        )
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed tally partial decryption package payload: {e}")


def serialize_threshold_tally_result(res: Any) -> dict[str, Any]:
    """Serialize a ThresholdTallyResult for public audit publication."""
    return {
        "protocol_version": res.protocol_version,
        "artifact_type": "THRESHOLD_TALLY_RESULT",
        "election_id": res.election_id,
        "threshold": res.threshold,
        "selected_trustees": res.selected_trustees,
        "candidate_results": res.candidate_results,
        "total_votes": res.total_votes,
        "ballot_count": res.ballot_count,
        "combined_decryption_points": {
            cid: serialize_point(pt)
            for cid, pt in res.combined_decryption_points.items()
        },
        "reconciled": res.reconciled,
    }


def deserialize_threshold_tally_result(data: dict[str, Any]) -> Any:
    """Deserialize a ThresholdTallyResult from dictionary."""
    try:
        from app.crypto.threshold.tally import ThresholdTallyResult
        combined_points = {
            cid: deserialize_point(pt_data)
            for cid, pt_data in data["combined_decryption_points"].items()
        }
        return ThresholdTallyResult(
            election_id=data["election_id"],
            threshold=int(data["threshold"]),
            selected_trustees=[int(x) for x in data["selected_trustees"]],
            candidate_results={cid: int(v) for cid, v in data["candidate_results"].items()},
            total_votes=int(data["total_votes"]),
            ballot_count=int(data["ballot_count"]),
            combined_decryption_points=combined_points,
            reconciled=bool(data["reconciled"]),
            protocol_version=data.get("protocol_version", "SECUREVOTE32"),
        )
    except Exception as e:
        raise ThresholdSerializationError(f"Malformed threshold tally result payload: {e}")
