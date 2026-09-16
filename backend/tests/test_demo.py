"""
Test for the Deterministic Demo Scenario (Section 11).
"""

import pytest
from httpx import AsyncClient

from scripts.run_demo import run_deterministic_demo


@pytest.mark.asyncio
async def test_deterministic_demo_scenario():
    """
    Executes the deterministic demo scenario with 100 ballots
    and verifies all independent checks pass.
    """
    results = await run_deterministic_demo(total_votes=100, verbose=False)

    assert results["overall_status"] == "PASSED"
    assert results["config_hash_valid"] is True
    assert results["audit_chain_intact"] is True
    assert results["reconciliation_passed"] is True
    assert results["tally_independently_verified"] is True
    assert results["manifest"]["total_ballots"] == 100

    # Verify candidate vote distribution sum equals exactly 100
    candidate_sum = sum(c["vote_count"] for c in results["manifest"]["candidate_results"])
    assert candidate_sum == 100

    # Verify device vote distribution sum equals exactly 100 (25 ballots each)
    device_sum = sum(d["ballot_count"] for d in results["manifest"]["device_results"])
    assert device_sum == 100
    for d in results["manifest"]["device_results"]:
        assert d["ballot_count"] == 25
