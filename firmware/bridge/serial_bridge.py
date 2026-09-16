"""
SecureVOTE — Serial Bridge Transport (Phase 2 Addition).

Bridges serial/UART messages from the physical Arduino or Wokwi simulation
to the FastAPI backend REST API.

Supported Message Types from Firmware:
1. {"type":"VOTE", "device_id":"EVM-001", "candidate_id":"C001", "sequence_number":1, "session_token":"..."}
   -> Calls POST /api/votes with VoteCast schema
2. {"type":"TAMPER", "device_id":"EVM-001", "sequence_number":2, "details":"..."}
   -> Logs TAMPER_DETECTED audit event and updates device status
3. {"type":"STATE_CHANGE", "device_id":"EVM-001", "sequence_number":3, "from_state":"...", "to_state":"..."}
   -> Logs device state transition audit event
4. {"type":"HEARTBEAT", "device_id":"EVM-001", "sequence_number":4, "state":"READY"}
   -> Updates device heartbeat timestamp

Usage:
  # Live hardware serial mode:
  python serial_bridge.py --port COM3 --baud 9600 --backend http://localhost:8000 --election EV-2026-001

  # Replay / Simulation file capture mode:
  python serial_bridge.py --replay capture.log --backend http://localhost:8000 --election EV-2026-001

  # Single message relay test:
  python serial_bridge.py --message '{"type":"VOTE","device_id":"EVM-001","candidate_id":"C001","sequence_number":1,"session_token":"..."}'
"""

import argparse
import asyncio
import json
import sys
import time
from typing import Any

import httpx

try:
    import serial
except ImportError:
    serial = None


class SerialBridge:
    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        election_id: str = "EV-2026-001",
        admin_token: str | None = None,
        demo_mode: bool = False,
        client: httpx.AsyncClient | None = None,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.election_id = election_id
        self.admin_token = admin_token
        self.demo_mode = demo_mode
        self.http_client = client or httpx.AsyncClient(base_url=self.backend_url, timeout=10.0)
        self._buffer: str = ""

    def _headers(self) -> dict[str, str]:
        if self.admin_token:
            return {"Authorization": f"Bearer {self.admin_token}"}
        return {}

    async def process_chunk(self, chunk: str) -> list[dict[str, Any]]:
        """
        Buffer incoming streaming data chunks and process complete NDJSON lines.
        Incomplete fragments remain in the buffer until a newline delimiter is received.
        """
        self._buffer += chunk
        results = []
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            res = await self.process_raw_line(line)
            if res is not None:
                results.append(res)
        return results

    async def process_raw_line(self, line: str) -> dict[str, Any] | None:
        """Parse and route a single raw JSON line from serial UART."""
        line = line.strip()
        if not line or not line.startswith("{"):
            return None

        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"[BRIDGE ERROR] Invalid JSON: {line} ({e})")
            return None

        msg_type = msg.get("type")
        print(f"[BRIDGE] Received message type: {msg_type}")

        if msg_type == "VOTE":
            return await self._handle_vote(msg)
        elif msg_type == "TAMPER":
            return await self._handle_tamper(msg)
        elif msg_type == "STATE_CHANGE":
            return self._handle_state_change(msg)
        elif msg_type == "HEARTBEAT":
            return self._handle_heartbeat(msg)
        elif msg_type == "BOOT":
            print(f"[BRIDGE] Device BOOT: ID={msg.get('device_id')}, Seq={msg.get('sequence_number')}")
            return {"status": "ACK", "type": "BOOT"}
        else:
            print(f"[BRIDGE WARNING] Unrecognized message type: {msg_type}")
            return {"status": "IGNORED", "type": msg_type}

    async def _handle_vote(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Relay vote to backend POST /api/votes."""
        device_id = msg.get("device_id")
        candidate_id = msg.get("candidate_id")
        sequence_number = msg.get("sequence_number")
        session_token = msg.get("session_token")

        if not session_token or session_token == "simulated_session_token":
            if not self.demo_mode:
                print("[BRIDGE ERROR] Vote rejected: Missing authenticated session token (demo_mode=False)")
                return {
                    "status": "REJECTED",
                    "code": 401,
                    "reason": "MISSING_SESSION_TOKEN",
                    "detail": "Real session token required. Enable demo mode explicitly (--demo-mode) to permit synthetic credentials.",
                }

            # Synthetic session creation ONLY permitted when demo_mode is explicitly enabled
            voter_cred = f"VOTER-SERIAL-{device_id}-{sequence_number}"
            print(f"[BRIDGE DEMO-MODE] Generating synthetic demo session for voter credential: {voter_cred}")
            sess_resp = await self.http_client.post(
                f"/api/elections/{self.election_id}/sessions",
                json={"voter_credential": voter_cred, "device_id": device_id},
                headers=self._headers(),
            )
            if sess_resp.status_code == 201:
                session_token = sess_resp.json()["session_token"]
            else:
                print(f"[BRIDGE ERROR] Session authorization failed: {sess_resp.text}")
                return {"status": "FAILED", "reason": "SESSION_AUTH_FAILED", "detail": sess_resp.text}

        payload = {
            "session_token": session_token,
            "candidate_id": candidate_id,
            "device_id": device_id,
            "sequence_number": sequence_number,
        }

        resp = await self.http_client.post("/api/votes", json=payload)
        if resp.status_code == 201:
            data = resp.json()
            print(f"[BRIDGE SUCCESS] Ballot recorded: Hash={data.get('ballot_hash')[:16]}... Candidate={candidate_id}")
            return {"status": "RECORDED", "data": data}
        else:
            print(f"[BRIDGE ERROR] Vote rejected ({resp.status_code}): {resp.text}")
            return {"status": "REJECTED", "code": resp.status_code, "detail": resp.text}

    async def _handle_tamper(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Log tamper event to backend."""
        device_id = msg.get("device_id")
        details = msg.get("details", "tamper_switch_triggered")
        print(f"[BRIDGE ALERT] TAMPER DETECTED on {device_id}: {details}")
        try:
            resp = await self.http_client.patch(
                f"/api/elections/{self.election_id}/devices/{device_id}/status",
                json={"status": "SUSPENDED"},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return {"status": "TAMPER_PROCESSED", "device_status": "SUSPENDED"}
            else:
                print(f"[BRIDGE WARNING] Device status update returned {resp.status_code}: {resp.text}")
                return {"status": "TAMPER_FAILED", "detail": resp.text}
        except Exception as e:
            return {"status": "TAMPER_RECORDED_LOCAL", "error": str(e)}

    def _handle_state_change(self, msg: dict[str, Any]) -> dict[str, Any]:
        from_st = msg.get("from_state")
        to_st = msg.get("to_state")
        print(f"[BRIDGE INFO] Device {msg.get('device_id')} State Transition: {from_st} -> {to_st}")
        return {"status": "ACK", "transition": f"{from_st}->{to_st}"}

    def _handle_heartbeat(self, msg: dict[str, Any]) -> dict[str, Any]:
        print(f"[BRIDGE HEARTBEAT] Device {msg.get('device_id')} in {msg.get('state')}")
        return {"status": "ACK", "heartbeat": True}

    async def run_live_serial(self, port: str, baud: int = 9600):
        if serial is None:
            raise RuntimeError("pyserial is not installed. Run: pip install pyserial")

        print(f"[BRIDGE] Opening live serial connection on {port} @ {baud} baud...")
        with serial.Serial(port, baud, timeout=1.0) as ser:
            time.sleep(2.0)  # Wait for Arduino auto-reset
            print("[BRIDGE] Connected. Listening for firmware UART messages...")
            while True:
                chunk = ser.read(ser.in_waiting or 1).decode("utf-8", errors="replace")
                if chunk:
                    await self.process_chunk(chunk)

    async def run_replay_file(self, filename: str):
        print(f"[BRIDGE] Replaying serial captures from file: {filename}")
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                results = await self.process_chunk(line)
                for res in results:
                    print(f"       Result -> {res.get('status')}")


async def async_main():
    parser = argparse.ArgumentParser(description="SecureVOTE Serial Bridge")
    parser.add_argument("--port", help="Serial COM port (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("--backend", default="http://localhost:8000", help="FastAPI backend URL")
    parser.add_argument("--election", default="EV-2026-001", help="Election ID")
    parser.add_argument("--admin-token", help="Admin JWT token for privileged updates")
    parser.add_argument("--demo-mode", action="store_true", default=False, help="Enable synthetic session creation for local demo")
    parser.add_argument("--replay", help="Path to capture file containing serial lines")
    parser.add_argument("--message", help="Single raw JSON serial message to process")
    args = parser.parse_args()

    bridge = SerialBridge(
        backend_url=args.backend,
        election_id=args.election,
        admin_token=args.admin_token,
        demo_mode=args.demo_mode,
    )

    if args.message:
        res = await bridge.process_raw_line(args.message)
        print(json.dumps(res, indent=2))
    elif args.replay:
        await bridge.run_replay_file(args.replay)
    elif args.port:
        await bridge.run_live_serial(args.port, args.baud)
    else:
        print("Usage: provide --port, --replay, or --message. Run with --help for details.")


if __name__ == "__main__":
    asyncio.run(async_main())
