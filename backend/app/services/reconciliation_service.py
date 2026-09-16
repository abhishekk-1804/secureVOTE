"""
Reconciliation service for SecureVOTE.

Performs exact reconciliation of election results per spec Â§10:
sum(candidate_totals) == total_valid_ballots AND
sum(device_totals) == total_ballots must hold with ZERO drift.
Any mismatch is a RECONCILIATION FAILURE â€” there is no tolerance band.
"""

import json
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ballot, Candidate, Device, Election


class ReconciliationService:
    """Exact reconciliation â€” zero tolerance for any numerical drift."""

    @staticmethod
    async def reconcile(
        db: AsyncSession,
        election_id: str,
    ) -> dict:
        """
        Independently recompute tallies from raw ballot records and
        reconcile against device and election totals.

        This method reads raw records directly â€” it never uses
        precomputed totals or cached flags. All counts are computed
        from scratch.

        Returns a dict with:
        - total_ballots: int
        - candidate_totals: dict[str, int]
        - device_totals: dict[str, int]
        - sum_candidate_totals: int
        - sum_device_totals: int
        - is_exact_match: bool
        - status: str ("PASSED" or "RECONCILIATION FAILURE")
        - details: list[str]
        """
        details: list[str] = []

        # Count ballots per candidate directly from ballot records
        candidate_count_result = await db.execute(
            select(Ballot.candidate_id, func.count(Ballot.id))
            .where(Ballot.election_id == election_id)
            .group_by(Ballot.candidate_id)
        )
        candidate_totals: dict[str, int] = dict(candidate_count_result.all())

        # Count ballots per device directly from ballot records
        device_count_result = await db.execute(
            select(Ballot.device_id, func.count(Ballot.id))
            .where(Ballot.election_id == election_id)
            .group_by(Ballot.device_id)
        )
        device_totals: dict[str, int] = dict(device_count_result.all())

        # Total ballots from raw count
        total_result = await db.execute(
            select(func.count(Ballot.id))
            .where(Ballot.election_id == election_id)
        )
        total_ballots = total_result.scalar_one()

        sum_candidate = sum(candidate_totals.values())
        sum_device = sum(device_totals.values())

        # Exact match checks (Â§10: zero drift)
        candidate_match = sum_candidate == total_ballots
        device_match = sum_device == total_ballots
        cross_match = sum_candidate == sum_device
        is_exact_match = candidate_match and device_match and cross_match

        if not candidate_match:
            details.append(
                f"RECONCILIATION FAILURE: sum(candidate_totals)={sum_candidate} "
                f"!= total_ballots={total_ballots}"
            )
        if not device_match:
            details.append(
                f"RECONCILIATION FAILURE: sum(device_totals)={sum_device} "
                f"!= total_ballots={total_ballots}"
            )
        if not cross_match:
            details.append(
                f"RECONCILIATION FAILURE: sum(candidate_totals)={sum_candidate} "
                f"!= sum(device_totals)={sum_device}"
            )

        # Cross-check with election's stored total_ballots
        election = await db.get(Election, election_id)
        if election and election.total_ballots != total_ballots:
            is_exact_match = False
            details.append(
                f"RECONCILIATION FAILURE: election.total_ballots="
                f"{election.total_ballots} != counted_ballots={total_ballots}"
            )

        # Cross-check with device stored totals
        devices_result = await db.execute(
            select(Device).where(Device.election_id == election_id)
        )
        for device in devices_result.scalars().all():
            counted = device_totals.get(device.id, 0)
            if device.total_votes_cast != counted:
                is_exact_match = False
                details.append(
                    f"RECONCILIATION FAILURE: device {device.id} "
                    f"reports {device.total_votes_cast} votes but "
                    f"{counted} ballots found in records"
                )

        if is_exact_match:
            details.append(
                f"Reconciliation passed. {total_ballots} ballots across "
                f"{len(candidate_totals)} candidates and {len(device_totals)} devices."
            )

        status = "PASSED" if is_exact_match else "RECONCILIATION FAILURE"

        return {
            "total_ballots": total_ballots,
            "candidate_totals": candidate_totals,
            "device_totals": device_totals,
            "sum_candidate_totals": sum_candidate,
            "sum_device_totals": sum_device,
            "is_exact_match": is_exact_match,
            "status": status,
            "details": details,
        }
