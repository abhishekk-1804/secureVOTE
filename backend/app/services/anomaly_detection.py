"""
Advisory Anomaly Detection Engine for SecureVOTE.

Provides transparent, deterministic, rule-based advisory anomaly detection.
Rules:
1. VOTING_RATE_BURST: Unusually high ballot casting rate on a device in a narrow window.
2. SEQUENCE_ANOMALY: Gaps or out-of-order sequence indicators.
3. REJECTION_BURST: Clustered replay or rejected vote requests.
4. DEVICE_STATE_ANOMALY: Device suspended/revoked during voting or state flapping.
5. TAMPER_CORRELATION: Hardware tamper events detected on voting units.
6. AUTH_ANOMALY: Clustered credential reuse or authentication failures.

HARD LIFECYCLE BOUNDARY:
Findings produced by this service are ADVISORY ONLY and tagged "REQUIRES HUMAN REVIEW".
They MUST NEVER automatically block, delay, or alter:
- Election lifecycle transitions (LOCK, OPEN, CLOSE, PUBLISH)
- Result manifest calculation or signing
- Independent verification results
- Vote recording or ballot counts
"""

from datetime import datetime, timezone
import json
from typing import Any, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEntry, Ballot, Device, Election, VotingSession
from app.schemas import AdvisoryFinding, AdvisoryFindingsResponse


class AnomalyDetectionService:
    """Deterministic rule-based anomaly detection engine."""

    @classmethod
    async def analyze_election(
        cls,
        db: AsyncSession,
        election_id: str,
    ) -> AdvisoryFindingsResponse:
        """
        Evaluate all deterministic anomaly detection rules against election audit and ballot data.
        Returns a structured advisory report.
        """
        findings: list[AdvisoryFinding] = []

        # 1. Evaluate Tamper Correlation
        tamper_findings = await cls._check_tamper_correlation(db, election_id)
        findings.extend(tamper_findings)

        # 2. Evaluate Rejection Bursts
        rejection_findings = await cls._check_rejection_bursts(db, election_id)
        findings.extend(rejection_findings)

        # 3. Evaluate Voting Rate Bursts
        rate_findings = await cls._check_voting_rate_bursts(db, election_id)
        findings.extend(rate_findings)

        # 4. Evaluate Sequence Anomalies (Gaps)
        seq_findings = await cls._check_sequence_gaps(db, election_id)
        findings.extend(seq_findings)

        # 5. Evaluate Device State Anomalies
        device_findings = await cls._check_device_state_anomalies(db, election_id)
        findings.extend(device_findings)

        # 6. Evaluate Authentication Anomalies
        auth_findings = await cls._check_auth_anomalies(db, election_id)
        findings.extend(auth_findings)

        return AdvisoryFindingsResponse(
            election_id=election_id,
            findings_count=len(findings),
            findings=findings,
            status="ADVISORY_ONLY_DOES_NOT_BLOCK_LIFECYCLE",
        )

    @classmethod
    async def _check_tamper_correlation(
        cls,
        db: AsyncSession,
        election_id: str,
    ) -> list[AdvisoryFinding]:
        """Detect physical tamper events correlated with voting units."""
        findings = []
        result = await db.execute(
            select(AuditEntry).where(
                AuditEntry.election_id == election_id,
                AuditEntry.event_type.in_(["TAMPER_DETECTED", "DEVICE_TAMPER_SWITCH", "TAMPER_LATCH_SET"]),
            )
        )
        tamper_events = result.scalars().all()
        for evt in tamper_events:
            findings.append(
                AdvisoryFinding(
                    finding_id=str(uuid.uuid4()),
                    election_id=election_id,
                    device_id=evt.device_id,
                    rule_id="RULE-TAMPER-001",
                    category="TAMPER",
                    severity="HIGH",
                    evidence={
                        "event_id": evt.id,
                        "sequence_number": evt.sequence_number,
                        "event_type": evt.event_type,
                        "timestamp": evt.timestamp.isoformat(),
                    },
                    timestamp=evt.timestamp,
                    advisory_explanation=(
                        f"ADVISORY FINDING: Physical hardware tamper detected on device '{evt.device_id or 'UNKNOWN'}' "
                        f"at audit sequence {evt.sequence_number}. Hardware lock may have been triggered. "
                        f"REQUIRES HUMAN REVIEW."
                    ),
                    requires_human_review=True,
                )
            )
        return findings

    @classmethod
    async def _check_rejection_bursts(
        cls,
        db: AsyncSession,
        election_id: str,
    ) -> list[AdvisoryFinding]:
        """Detect clusters of rejected votes or replay attempts (>= 3 rejections)."""
        findings = []
        result = await db.execute(
            select(AuditEntry).where(
                AuditEntry.election_id == election_id,
                AuditEntry.event_type.in_([
                    "REPLAY_ATTEMPT_REJECTED",
                    "VOTE_REJECTED",
                    "SESSION_REJECTED",
                    "UNAUTHORIZED_DEVICE_ATTEMPT",
                ]),
            )
        )
        rejection_events = result.scalars().all()
        if len(rejection_events) >= 3:
            findings.append(
                AdvisoryFinding(
                    finding_id=str(uuid.uuid4()),
                    election_id=election_id,
                    device_id=rejection_events[0].device_id,
                    rule_id="RULE-REJ-001",
                    category="INTEGRITY",
                    severity="HIGH",
                    evidence={
                        "rejection_count": len(rejection_events),
                        "rejection_types": list({e.event_type for e in rejection_events}),
                        "first_rejection_time": rejection_events[0].timestamp.isoformat(),
                        "last_rejection_time": rejection_events[-1].timestamp.isoformat(),
                    },
                    timestamp=rejection_events[-1].timestamp,
                    advisory_explanation=(
                        f"ADVISORY FINDING: Clustered rejected requests detected ({len(rejection_events)} rejections). "
                        f"Possible communication glitch, operator error, or replay attempt. "
                        f"REQUIRES HUMAN REVIEW."
                    ),
                    requires_human_review=True,
                )
            )
        return findings

    @classmethod
    async def _check_voting_rate_bursts(
        cls,
        db: AsyncSession,
        election_id: str,
    ) -> list[AdvisoryFinding]:
        """Detect unexpectedly rapid ballot casting (> 4 ballots in <= 5 seconds on a single device)."""
        findings = []
        result = await db.execute(
            select(Ballot)
            .where(Ballot.election_id == election_id)
            .order_by(Ballot.device_id, Ballot.sequence_number)
        )
        ballots = result.scalars().all()

        device_ballots: dict[str, list[Ballot]] = {}
        for b in ballots:
            device_ballots.setdefault(b.device_id, []).append(b)

        for did, b_list in device_ballots.items():
            if len(b_list) >= 4:
                for i in range(len(b_list) - 3):
                    window = b_list[i : i + 4]
                    t0 = window[0].recorded_at.timestamp()
                    t1 = window[-1].recorded_at.timestamp()
                    delta = t1 - t0
                    if delta <= 5.0:
                        findings.append(
                            AdvisoryFinding(
                                finding_id=str(uuid.uuid4()),
                                election_id=election_id,
                                device_id=did,
                                rule_id="RULE-RATE-001",
                                category="VELOCITY",
                                severity="HIGH",
                                evidence={
                                    "device_id": did,
                                    "ballot_count": len(window),
                                    "window_duration_seconds": round(delta, 2),
                                    "start_sequence": window[0].sequence_number,
                                    "end_sequence": window[-1].sequence_number,
                                },
                                timestamp=window[-1].recorded_at,
                                advisory_explanation=(
                                    f"ADVISORY FINDING: Rapid voting burst detected on device '{did}'. "
                                    f"{len(window)} ballots cast in {round(delta, 2)} seconds. "
                                    f"Exceeds human voter physical interaction model. "
                                    f"REQUIRES HUMAN REVIEW."
                                ),
                                requires_human_review=True,
                            )
                        )
                        break  # Emit once per burst window
        return findings

    @classmethod
    async def _check_sequence_gaps(
        cls,
        db: AsyncSession,
        election_id: str,
    ) -> list[AdvisoryFinding]:
        """Detect sequence counter gaps (> 1) on any device."""
        findings = []
        result = await db.execute(
            select(Ballot)
            .where(Ballot.election_id == election_id)
            .order_by(Ballot.device_id, Ballot.sequence_number)
        )
        ballots = result.scalars().all()

        device_ballots: dict[str, list[Ballot]] = {}
        for b in ballots:
            device_ballots.setdefault(b.device_id, []).append(b)

        for did, b_list in device_ballots.items():
            for i in range(1, len(b_list)):
                curr_seq = b_list[i].sequence_number
                prev_seq = b_list[i - 1].sequence_number
                gap = curr_seq - prev_seq
                if gap > 1:
                    findings.append(
                        AdvisoryFinding(
                            finding_id=str(uuid.uuid4()),
                            election_id=election_id,
                            device_id=did,
                            rule_id="RULE-SEQ-001",
                            category="SEQUENCE",
                            severity="MEDIUM",
                            evidence={
                                "device_id": did,
                                "previous_sequence": prev_seq,
                                "current_sequence": curr_seq,
                                "gap_size": gap,
                            },
                            timestamp=b_list[i].recorded_at,
                            advisory_explanation=(
                                f"ADVISORY FINDING: Sequence gap of {gap} detected on device '{did}' "
                                f"between sequence {prev_seq} and {curr_seq}. "
                                f"Possible unrecorded discarded session or dropped ballot. "
                                f"REQUIRES HUMAN REVIEW."
                            ),
                            requires_human_review=True,
                        )
                    )
        return findings

    @classmethod
    async def _check_device_state_anomalies(
        cls,
        db: AsyncSession,
        election_id: str,
    ) -> list[AdvisoryFinding]:
        """Detect devices in suspended or revoked state that remain configured."""
        findings = []
        result = await db.execute(
            select(Device).where(
                Device.election_id == election_id,
                Device.status.in_(["SUSPENDED", "REVOKED"]),
            )
        )
        inactive_devices = result.scalars().all()
        for d in inactive_devices:
            findings.append(
                AdvisoryFinding(
                    finding_id=str(uuid.uuid4()),
                    election_id=election_id,
                    device_id=d.id,
                    rule_id="RULE-STATE-001",
                    category="DEVICE",
                    severity="MEDIUM",
                    evidence={
                        "device_id": d.id,
                        "device_status": d.status,
                        "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                        "total_votes_cast": d.total_votes_cast,
                    },
                    timestamp=datetime.now(timezone.utc),
                    advisory_explanation=(
                        f"ADVISORY FINDING: Device '{d.id}' is currently in '{d.status}' status. "
                        f"Unit is offline or quarantined from election pool. "
                        f"REQUIRES HUMAN REVIEW."
                    ),
                    requires_human_review=True,
                )
            )
        return findings

    @classmethod
    async def _check_auth_anomalies(
        cls,
        db: AsyncSession,
        election_id: str,
    ) -> list[AdvisoryFinding]:
        """Detect repeated session authorization attempts with duplicate credentials."""
        findings = []
        result = await db.execute(
            select(VotingSession).where(VotingSession.election_id == election_id)
        )
        sessions = result.scalars().all()

        cred_counts: dict[str, int] = {}
        for s in sessions:
            if s.voter_credential:
                cred_counts[s.voter_credential] = cred_counts.get(s.voter_credential, 0) + 1

        for cred, count in cred_counts.items():
            if count > 1:
                findings.append(
                    AdvisoryFinding(
                        finding_id=str(uuid.uuid4()),
                        election_id=election_id,
                        device_id=None,
                        rule_id="RULE-AUTH-001",
                        category="AUTHENTICATION",
                        severity="MEDIUM",
                        evidence={
                            "voter_credential": f"{cred[:4]}****",
                            "session_count": count,
                        },
                        timestamp=datetime.now(timezone.utc),
                        advisory_explanation=(
                            f"ADVISORY FINDING: Credential '{cred[:4]}****' authorized {count} voting sessions. "
                            f"Duplicate check-in detected. "
                            f"REQUIRES HUMAN REVIEW."
                        ),
                        requires_human_review=True,
                    )
                )
        return findings
