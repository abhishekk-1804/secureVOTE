"""
Test suite for Phase 2 Serial Bridge Integration.

Validates that serial UART messages formatted by the Arduino firmware
are properly parsed, translated, and recorded into the backend database.
"""

import pytest
from httpx import AsyncClient
import sys
from pathlib import Path

# Add firmware/bridge to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "firmware" / "bridge"))
from serial_bridge import SerialBridge


@pytest.mark.asyncio
async def test_serial_bridge_relay_end_to_end(client: AsyncClient, admin_headers: dict):
    """
    Simulates the Wokwi serial UART line stream and verifies
    the bridge relays the messages into actual database ballots.
    """
    election_id = "EV-2026-001"

    # Setup election, candidates, and device EVM-001 in OPEN state
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Bridge Test Election"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Alice Vance", "party": "Party A", "symbol": "A", "position": 1},
                {"id": "C002", "name": "Bob Jenkins", "party": "Party B", "symbol": "B", "position": 2},
            ]
        },
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "LOCKED"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-001", "name": "Polling Unit 1"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/devices/EVM-001/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )

    # Initialize bridge pointing directly to test ASGI client
    token_str = admin_headers["Authorization"].split()[1]
    bridge = SerialBridge(backend_url="http://test", election_id=election_id, admin_token=token_str, client=client)

    # 1. Simulate Firmware BOOT message
    boot_line = '{"type":"BOOT","device_id":"EVM-001","sequence_number":0,"config_hash":"34d70b"}\n'
    res_boot = await bridge.process_raw_line(boot_line)
    assert res_boot["status"] == "ACK"

    # 2. Simulate Firmware STATE_CHANGE message
    state_line = '{"type":"STATE_CHANGE","device_id":"EVM-001","sequence_number":0,"from_state":"BOOT","to_state":"READY"}\n'
    res_state = await bridge.process_raw_line(state_line)
    assert res_state["status"] == "ACK"

    # 3. Simulate Firmware VOTE message (Candidate 1, Seq 1)
    # First authorize session
    sess_resp = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-SERIAL-001", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    token1 = sess_resp.json()["session_token"]

    vote_line_1 = f'{{"type":"VOTE","device_id":"EVM-001","candidate_id":"C001","sequence_number":1,"session_token":"{token1}"}}\n'
    res_vote1 = await bridge.process_raw_line(vote_line_1)
    assert res_vote1["status"] == "RECORDED"
    assert res_vote1["data"]["candidate_id"] == "C001"
    assert res_vote1["data"]["sequence_number"] == 1

    # 4. Simulate Firmware VOTE message (Candidate 2, Seq 2)
    sess_resp2 = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-SERIAL-002", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    token2 = sess_resp2.json()["session_token"]

    vote_line_2 = f'{{"type":"VOTE","device_id":"EVM-001","candidate_id":"C002","sequence_number":2,"session_token":"{token2}"}}\n'
    res_vote2 = await bridge.process_raw_line(vote_line_2)
    assert res_vote2["status"] == "RECORDED"
    assert res_vote2["data"]["candidate_id"] == "C002"
    assert res_vote2["data"]["sequence_number"] == 2

    # 5. Simulate Replay Attack over serial (Seq 1 again) -> Must be REJECTED
    sess_resp3 = await client.post(
        f"/api/elections/{election_id}/sessions",
        json={"voter_credential": "VOTER-SERIAL-003", "device_id": "EVM-001"},
        headers=admin_headers,
    )
    token3 = sess_resp3.json()["session_token"]
    replay_line = f'{{"type":"VOTE","device_id":"EVM-001","candidate_id":"C001","sequence_number":1,"session_token":"{token3}"}}\n'
    res_replay = await bridge.process_raw_line(replay_line)
    assert res_replay["status"] == "REJECTED"
    assert res_replay["code"] == 409

    # 6. Simulate Tamper Switch Alert
    tamper_line = '{"type":"TAMPER","device_id":"EVM-001","sequence_number":3,"details":"enclosure_breached"}\n'
    res_tamper = await bridge.process_raw_line(tamper_line)
    assert res_tamper["status"] == "TAMPER_PROCESSED"

    # 7. Verify device was suspended by tamper report
    dev_resp = await client.get(f"/api/elections/{election_id}/devices/EVM-001", headers=admin_headers)
    assert dev_resp.json()["status"] == "SUSPENDED"

    # 8. Run independent reconciliation & verification
    # Close election and verify
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "CLOSED"},
        headers=admin_headers,
    )
    recon_resp = await client.get(f"/api/elections/{election_id}/results", headers=admin_headers)
    recon_data = recon_resp.json()
    assert recon_data["reconciliation_passed"] is True
    assert recon_data["manifest"]["total_ballots"] == 2


@pytest.mark.asyncio
async def test_serial_bridge_demo_mode_fail_closed(client: AsyncClient, admin_headers: dict):
    """
    Test Fix 3: Serial bridge fail-closed session token requirement.
    Without demo_mode=True, missing session_token is rejected with 401.
    With demo_mode=True, synthetic demo session is created.
    """
    election_id = "EV-2026-002"
    token_str = admin_headers["Authorization"].split()[1]

    # Setup election
    await client.post(
        "/api/elections",
        json={"id": election_id, "name": "Demo Mode Test Election"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/candidates",
        json={
            "candidates": [
                {"id": "C001", "name": "Alice Vance", "party": "Party A", "symbol": "A", "position": 1},
                {"id": "C002", "name": "Bob Jenkins", "party": "Party B", "symbol": "B", "position": 2},
            ]
        },
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "LOCKED"},
        headers=admin_headers,
    )
    await client.post(
        f"/api/elections/{election_id}/devices",
        json={"id": "EVM-001", "name": "Polling Unit 1"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/devices/EVM-001/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    await client.patch(
        f"/api/elections/{election_id}/state",
        json={"new_state": "OPEN"},
        headers=admin_headers,
    )

    # 1. Default bridge (demo_mode=False) MUST FAIL-CLOSED on simulated/missing token
    strict_bridge = SerialBridge(
        backend_url="http://test",
        election_id=election_id,
        admin_token=token_str,
        demo_mode=False,
        client=client,
    )
    unauth_vote = '{"type":"VOTE","device_id":"EVM-001","candidate_id":"C001","sequence_number":1,"session_token":"simulated_session_token"}\n'
    res_rejected = await strict_bridge.process_raw_line(unauth_vote)
    assert res_rejected["status"] == "REJECTED"
    assert res_rejected["code"] == 401
    assert res_rejected["reason"] == "MISSING_SESSION_TOKEN"

    # 2. Bridge with demo_mode=True allows synthetic demo session authorization
    demo_bridge = SerialBridge(
        backend_url="http://test",
        election_id=election_id,
        admin_token=token_str,
        demo_mode=True,
        client=client,
    )
    res_demo = await demo_bridge.process_raw_line(unauth_vote)
    assert res_demo["status"] == "RECORDED"
    assert res_demo["data"]["candidate_id"] == "C001"
    assert res_demo["data"]["sequence_number"] == 1


@pytest.mark.asyncio
async def test_serial_bridge_fragmented_ndjson_chunks(client: AsyncClient, admin_headers: dict):
    """
    Test Phase 6X: Serial bridge robust line-buffering against fragmented UART reads,
    multiple NDJSON lines in a single chunk, and malformed input resilience.
    """
    election_id = "EV-2026-FRAG"
    token_str = admin_headers["Authorization"].split()[1]

    bridge = SerialBridge(
        backend_url="http://test",
        election_id=election_id,
        admin_token=token_str,
        client=client,
    )

    # 1. Fragmented message across two chunks
    chunk1 = '{"type":"BOOT","device_id":"EVM-001",'
    chunk2 = '"sequence_number":0,"config_hash":"34d70b"}\n'

    res1 = await bridge.process_chunk(chunk1)
    assert res1 == [], "Incomplete fragment should be buffered without emitting a message"
    assert bridge._buffer == chunk1

    res2 = await bridge.process_chunk(chunk2)
    assert len(res2) == 1
    assert res2[0]["status"] == "ACK"
    assert res2[0]["type"] == "BOOT"
    assert bridge._buffer == ""

    # 2. Multi-line chunk with trailing incomplete fragment
    chunk3 = (
        '{"type":"STATE_CHANGE","device_id":"EVM-001","sequence_number":0,"from_state":"BOOT","to_state":"READY"}\n'
        '{"type":"HEARTBE'
    )
    res3 = await bridge.process_chunk(chunk3)
    assert len(res3) == 1
    assert res3[0]["status"] == "ACK"
    assert res3[0]["transition"] == "BOOT->READY"
    assert bridge._buffer == '{"type":"HEARTBE'

    chunk4 = 'AT","device_id":"EVM-001","sequence_number":0,"state":"READY"}\n'
    res4 = await bridge.process_chunk(chunk4)
    assert len(res4) == 1
    assert res4[0]["status"] == "ACK"
    assert res4[0]["heartbeat"] is True
    assert bridge._buffer == ""

    # 3. Malformed non-JSON chunk followed by newline handled gracefully without crash
    chunk_garbage = 'THIS_IS_CORRUPTED_SERIAL_NOISE_12345\n'
    res_garbage = await bridge.process_chunk(chunk_garbage)
    assert res_garbage == [], "Malformed lines should be safely skipped without crashing"
    assert bridge._buffer == ""
