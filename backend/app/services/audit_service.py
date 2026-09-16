"""
Audit service for SecureVOTE.

Manages the append-only, hash-chained audit log. Each entry's hash includes
the previous entry's hash, forming a tamper-evident chain. Verification
independently recomputes all hashes from raw records â€” it never reads a
precomputed status flag.
"""

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEntry
from app.services.websocket_service import websocket_manager
from app.utils.hashing import compute_audit_entry_hash



class AuditService:
    """Append-only hash-chained audit log operations."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        election_id: str,
        event_type: str,
        event_data: dict | None = None,
        actor: str | None = None,
        device_id: str | None = None,
    ) -> AuditEntry:
        """
        Append a new audit entry to the hash chain.

        The sequence number is monotonically increasing per election.
        The entry hash is computed from: sequence_number, event_type,
        event_data (JSON), timestamp (ISO), and previous entry's hash.
        """
        now = datetime.now(timezone.utc)

        # Get the last audit entry for this election to chain hashes
        result = await db.execute(
            select(AuditEntry)
            .where(AuditEntry.election_id == election_id)
            .order_by(AuditEntry.sequence_number.desc())
            .limit(1)
        )
        last_entry = result.scalar_one_or_none()

        if last_entry is not None:
            sequence_number = last_entry.sequence_number + 1
            previous_hash = last_entry.entry_hash
        else:
            sequence_number = 1
            previous_hash = None

        # Serialize event data
        event_data_json = json.dumps(event_data, sort_keys=True) if event_data else None

        # Compute hash for this entry
        entry_hash = compute_audit_entry_hash(
            sequence_number=sequence_number,
            event_type=event_type,
            event_data=event_data_json,
            timestamp=now,
            previous_hash=previous_hash,
        )

        entry = AuditEntry(
            election_id=election_id,
            event_type=event_type,
            event_data=event_data_json,
            actor=actor,
            device_id=device_id,
            sequence_number=sequence_number,
            timestamp=now,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        db.add(entry)
        await db.flush()

        await websocket_manager.broadcast(
            election_id=election_id,
            event_type="AUDIT_EVENT",
            data={
                "id": entry.id,
                "sequence_number": entry.sequence_number,
                "event_type": entry.event_type,
                "entry_hash": entry.entry_hash,
                "actor": entry.actor,
                "device_id": entry.device_id,
                "timestamp": entry.timestamp.isoformat(),
            },
        )

        return entry


    @staticmethod
    async def get_audit_log(
        db: AsyncSession,
        election_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditEntry], int]:
        """
        Get audit log entries for an election, ordered by sequence number.

        Returns (entries, total_count).
        """
        # Total count
        count_result = await db.execute(
            select(func.count(AuditEntry.id))
            .where(AuditEntry.election_id == election_id)
        )
        total = count_result.scalar_one()

        # Paginated entries
        result = await db.execute(
            select(AuditEntry)
            .where(AuditEntry.election_id == election_id)
            .order_by(AuditEntry.sequence_number.asc())
            .offset(offset)
            .limit(limit)
        )
        entries = list(result.scalars().all())

        return entries, total

    @staticmethod
    async def verify_chain(
        db: AsyncSession,
        election_id: str,
    ) -> dict:
        """
        Independently verify the entire audit hash chain for an election.

        This method recomputes every hash from raw record data â€” it does NOT
        read any precomputed verification flag. Any modification to any
        historical entry will cause the chain to break at that point.

        Returns a dict with:
        - is_intact: bool
        - total_entries: int
        - verified_entries: int
        - first_broken_index: int | None (0-based)
        - first_broken_sequence: int | None
        - details: str
        """
        result = await db.execute(
            select(AuditEntry)
            .where(AuditEntry.election_id == election_id)
            .order_by(AuditEntry.sequence_number.asc())
        )
        entries = list(result.scalars().all())

        if not entries:
            return {
                "is_intact": True,
                "total_entries": 0,
                "verified_entries": 0,
                "first_broken_index": None,
                "first_broken_sequence": None,
                "details": "No audit entries to verify.",
            }

        verified = 0
        expected_previous_hash = None

        for i, entry in enumerate(entries):
            # Verify the chain link: entry.previous_hash must match
            # the previous entry's entry_hash
            if entry.previous_hash != expected_previous_hash:
                return {
                    "is_intact": False,
                    "total_entries": len(entries),
                    "verified_entries": verified,
                    "first_broken_index": i,
                    "first_broken_sequence": entry.sequence_number,
                    "details": (
                        f"AUDIT VERIFICATION FAILED: Chain broken at entry "
                        f"sequence {entry.sequence_number} (index {i}). "
                        f"Expected previous_hash={expected_previous_hash!r}, "
                        f"found={entry.previous_hash!r}."
                    ),
                }

            # Recompute the entry hash from raw data
            recomputed_hash = compute_audit_entry_hash(
                sequence_number=entry.sequence_number,
                event_type=entry.event_type,
                event_data=entry.event_data,
                timestamp=entry.timestamp,
                previous_hash=entry.previous_hash,
            )

            if recomputed_hash != entry.entry_hash:
                return {
                    "is_intact": False,
                    "total_entries": len(entries),
                    "verified_entries": verified,
                    "first_broken_index": i,
                    "first_broken_sequence": entry.sequence_number,
                    "details": (
                        f"AUDIT VERIFICATION FAILED: Hash mismatch at entry "
                        f"sequence {entry.sequence_number} (index {i}). "
                        f"Stored hash={entry.entry_hash}, "
                        f"recomputed={recomputed_hash}. "
                        f"The entry data may have been modified."
                    ),
                }

            expected_previous_hash = entry.entry_hash
            verified += 1

        return {
            "is_intact": True,
            "total_entries": len(entries),
            "verified_entries": verified,
            "first_broken_index": None,
            "first_broken_sequence": None,
            "details": (
                f"Audit chain intact. All {verified} entries verified "
                f"by independent hash recomputation."
            ),
        }
