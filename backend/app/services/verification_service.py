"""
Independent verification engine for SecureVOTE.

The verifier independently recomputes tallies, hashes, and reconciliation
from raw ballot/audit records — it never reads a precomputed "VERIFIED"
flag and passes it through (spec Â§4 trust boundary rule).

Generates and optionally signs result manifests.
"""

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ballot, Candidate, Device, Election, ResultManifest
from app.schemas import (
    AuditVerificationResponse,
    CandidateResult,
    DeviceResult,
    ReconciliationResult,
    ResultManifestResponse,
    VerificationResponse,
)
from app.services.audit_service import AuditService
from app.services.election_service import ElectionService
from app.services.reconciliation_service import ReconciliationService
from app.utils.hashing import compute_manifest_hash
from app.utils.identifiers import generate_uuid


class VerificationService:
    """
    Independent verification engine.

    Recomputes everything from raw records. Does not trust precomputed
    values from any other component.
    """

    @staticmethod
    async def run_full_verification(
        db: AsyncSession,
        election_id: str,
        actor: str = "verifier",
    ) -> VerificationResponse:
        """
        Run complete independent verification of an election.

        Steps:
        1. Verify configuration hash
        2. Verify audit hash chain
        3. Run reconciliation (exact, zero tolerance)
        4. Independently recompute tally from raw ballots
        5. Generate result manifest
        """
        details: list[str] = []

        # 1. Verify configuration hash
        config_valid, stored_hash, computed_hash = (
            await ElectionService.verify_configuration(db, election_id)
        )
        if config_valid:
            details.append("Configuration hash verification: PASSED")
        else:
            details.append(
                f"CONFIGURATION HASH MISMATCH: stored={stored_hash}, "
                f"computed={computed_hash}"
            )

        # 2. Verify audit hash chain
        audit_result = await AuditService.verify_chain(db, election_id)
        audit_intact = audit_result["is_intact"]
        details.append(f"Audit chain verification: {audit_result['details']}")

        # 3. Run reconciliation
        recon_result = await ReconciliationService.reconcile(db, election_id)
        recon_passed = recon_result["is_exact_match"]
        details.extend(recon_result["details"])

        # 4. Independently recompute tally
        tally_verified = await VerificationService._verify_tally_independently(
            db, election_id, recon_result["candidate_totals"], details
        )

        # 5. Generate result manifest
        manifest = await VerificationService._generate_manifest(
            db=db,
            election_id=election_id,
            recon_result=recon_result,
            audit_intact=audit_intact,
            config_valid=config_valid,
            actor=actor,
        )

        # Build candidate and device result lists for response
        election = await ElectionService.get_election(db, election_id)
        candidates = await ElectionService.get_candidates(db, election_id)

        candidate_results = []
        total_votes = recon_result["total_ballots"] or 1  # avoid div by zero
        for c in candidates:
            count = recon_result["candidate_totals"].get(c.id, 0)
            pct = (count / total_votes * 100) if total_votes > 0 else 0.0
            candidate_results.append(
                CandidateResult(
                    candidate_id=c.id,
                    candidate_name=c.name,
                    party=c.party,
                    symbol=c.symbol,
                    vote_count=count,
                    percentage=round(pct, 2),
                )
            )

        devices_result = await db.execute(
            select(Device).where(Device.election_id == election_id)
        )
        device_results = []
        for d in devices_result.scalars().all():
            count = recon_result["device_totals"].get(d.id, 0)
            device_results.append(
                DeviceResult(
                    device_id=d.id,
                    device_name=d.name,
                    ballot_count=count,
                )
            )

        overall = "PASSED" if all([
            config_valid, audit_intact, recon_passed, tally_verified
        ]) else "FAILED"

        manifest_response = None
        if manifest:
            manifest_response = ResultManifestResponse(
                id=manifest.id,
                election_id=manifest.election_id,
                total_ballots=manifest.total_ballots,
                candidate_totals=manifest.candidate_totals,
                device_totals=manifest.device_totals,
                reconciliation_status=manifest.reconciliation_status,
                audit_chain_status=manifest.audit_chain_status,
                configuration_hash=manifest.configuration_hash,
                manifest_hash=manifest.manifest_hash,
                digital_signature=manifest.digital_signature,
                generated_at=manifest.generated_at,
                verified_at=manifest.verified_at,
                verified_by=manifest.verified_by,
                candidate_results=candidate_results,
                device_results=device_results,
                reconciliation=ReconciliationResult(
                    total_ballots=recon_result["total_ballots"],
                    sum_candidate_totals=recon_result["sum_candidate_totals"],
                    sum_device_totals=recon_result["sum_device_totals"],
                    is_exact_match=recon_result["is_exact_match"],
                    status=recon_result["status"],
                ),
            )

        return VerificationResponse(
            election_id=election_id,
            config_hash_valid=config_valid,
            audit_chain_intact=audit_intact,
            reconciliation_passed=recon_passed,
            tally_independently_verified=tally_verified,
            overall_status=overall,
            manifest=manifest_response,
            details=details,
        )

    @staticmethod
    async def _verify_tally_independently(
        db: AsyncSession,
        election_id: str,
        reported_candidate_totals: dict[str, int],
        details: list[str],
    ) -> bool:
        """
        Independently recount all ballots from raw records and compare
        with the reported totals. This is separate from reconciliation —
        it verifies that the reconciliation service itself computed correctly.
        """
        from sqlalchemy import func

        result = await db.execute(
            select(Ballot.candidate_id, func.count(Ballot.id))
            .where(Ballot.election_id == election_id)
            .group_by(Ballot.candidate_id)
        )
        independent_totals: dict[str, int] = dict(result.all())

        # Compare each candidate
        all_candidate_ids = set(reported_candidate_totals.keys()) | set(
            independent_totals.keys()
        )

        mismatches = []
        for cid in all_candidate_ids:
            reported = reported_candidate_totals.get(cid, 0)
            independent = independent_totals.get(cid, 0)
            if reported != independent:
                mismatches.append(
                    f"Candidate {cid}: reported={reported}, "
                    f"independent_count={independent}"
                )

        if mismatches:
            details.append(
                "TALLY VERIFICATION FAILED: Independent recount does not match. "
                + "; ".join(mismatches)
            )
            return False

        details.append(
            f"Independent tally verification: PASSED "
            f"({len(independent_totals)} candidates recounted)"
        )
        return True

    @staticmethod
    async def _generate_manifest(
        db: AsyncSession,
        election_id: str,
        recon_result: dict,
        audit_intact: bool,
        config_valid: bool,
        actor: str,
    ) -> ResultManifest | None:
        """Generate or update the result manifest for an election."""
        election = await db.get(Election, election_id)
        if not election:
            return None

        recon_status = recon_result["status"]
        audit_status = "INTACT" if audit_intact else "BROKEN"
        config_hash = election.configuration_hash or ""

        candidate_totals_json = json.dumps(
            dict(sorted(recon_result["candidate_totals"].items())),
            sort_keys=True,
        )
        device_totals_json = json.dumps(
            dict(sorted(recon_result["device_totals"].items())),
            sort_keys=True,
        )

        manifest_hash = compute_manifest_hash(
            election_id=election_id,
            total_ballots=recon_result["total_ballots"],
            candidate_totals=recon_result["candidate_totals"],
            device_totals=recon_result["device_totals"],
            reconciliation_status=recon_status,
            audit_chain_status=audit_status,
            configuration_hash=config_hash,
        )

        now = datetime.now(timezone.utc)

        # Check for existing manifest
        existing = await db.execute(
            select(ResultManifest).where(
                ResultManifest.election_id == election_id
            )
        )
        manifest = existing.scalar_one_or_none()

        if manifest:
            # Update existing manifest
            manifest.total_ballots = recon_result["total_ballots"]
            manifest.candidate_totals = candidate_totals_json
            manifest.device_totals = device_totals_json
            manifest.reconciliation_status = recon_status
            manifest.audit_chain_status = audit_status
            manifest.configuration_hash = config_hash
            manifest.manifest_hash = manifest_hash
            manifest.verified_at = now
            manifest.verified_by = actor
        else:
            # Create new manifest
            manifest = ResultManifest(
                id=generate_uuid(),
                election_id=election_id,
                total_ballots=recon_result["total_ballots"],
                candidate_totals=candidate_totals_json,
                device_totals=device_totals_json,
                reconciliation_status=recon_status,
                audit_chain_status=audit_status,
                configuration_hash=config_hash,
                manifest_hash=manifest_hash,
                generated_at=now,
                verified_at=now,
                verified_by=actor,
            )
            db.add(manifest)

        await db.flush()

        await AuditService.log_event(
            db=db,
            election_id=election_id,
            event_type="MANIFEST_GENERATED",
            event_data={
                "manifest_hash": manifest_hash,
                "reconciliation_status": recon_status,
                "audit_chain_status": audit_status,
                "total_ballots": recon_result["total_ballots"],
            },
            actor=actor,
        )

        return manifest
