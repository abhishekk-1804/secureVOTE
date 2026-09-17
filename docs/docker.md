# SecureVOTE  -  Docker Architecture & Hardware Boundary Specification

## 1. Overview & Service Composition

The SecureVOTE application stack is containerized for reproducible local execution and server deployment using Docker and Docker Compose.

```
                    HOST SYSTEM (Windows / Linux / macOS)
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚                                                                          â”‚
  â”‚   [ Physical Arduino Uno / Wokwi Simulation ]                            â”‚
  â”‚                          â”‚                                               â”‚
  â”‚                     (COM3 / Serial)                                      â”‚
  â”‚                          â–¼                                               â”‚
  â”‚   [ serial_bridge.py ] (Runs natively on HOST)                          â”‚
  â”‚                          â”‚                                               â”‚
  â”‚                    (HTTP / REST)                                         â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                             â–¼ (Port 8000)
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ DOCKER ENVIRONMENT                                                       â”‚
  â”‚                                                                          â”‚
  â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
  â”‚   â”‚ backend                       â”‚     â”‚ dashboard                  â”‚  â”‚
  â”‚   â”‚ FastAPI + Python 3.12-slim    â”‚â—„â”€â”€â”€â”€â”¤ Next.js 14 + Node 20-alp   â”‚  â”‚
  â”‚   â”‚ Port 8000 (REST + WebSocket)  â”‚     â”‚ Port 3000 (UI)             â”‚  â”‚
  â”‚   â”‚ Volume: backend-data          â”‚     â”‚                            â”‚  â”‚
  â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 2. The Hardware Boundary: Why `serial_bridge.py` Runs on Host

A foundational requirement in SecureVOTE is clear delineation of trust boundaries and hardware boundaries.

### The Technical Limitation of Docker on Windows
1. **Windows COM Port Isolation**: Under Docker Desktop for Windows, containers execute inside a Linux kernel hosted in a WSL2 (Windows Subsystem for Linux 2) lightweight utility VM.
2. **Serial Device Virtualization**: Host COM ports (e.g. `COM1`, `COM3`, `\\.\COM*`) and USB-to-UART bridge controllers (FTDI, CH340, ATmega16U2) are bound to the Windows device tree. Docker on Windows cannot natively bind or pass Windows character devices into Linux containers.
3. **USBIP Overhead & Instability**: While third-party USB-over-IP (`usbipd-win`) utilities exist, they require kernel-level bridging, administrative elevation, and break easily across USB disconnect/reconnect cycles.
4. **Wokwi Headless Integration**: Headless Wokwi simulations on Windows frequently communicate via local named pipes or loopback pseudo-terminals that cannot cross container namespaces without non-standard networking bridges.

### The Architectural Decision
- **`backend` and `dashboard` run in Docker**: These services represent the central election authority, database, verification engine, and presentation tiers.
- **`serial_bridge.py` runs natively on the host**: The bridge is a lightweight edge daemon whose sole role is translating raw UART serial lines (`SERIAL_EVENT: ...`) into structured HTTP/REST requests. Running the bridge directly on the host machine ensures low-latency, reliable access to physical serial ports and Wokwi simulation environments.

---

## 3. Container Images & Build Configurations

### Backend Container (`backend/Dockerfile`)
- **Base Image**: `python:3.12-slim`
- **Dependencies**: Compiled C-extensions for cryptographic primitives (`cryptography`, `bcrypt`).
- **Data Persistence**: Mounts `/app/data` to a named volume (`backend-data`) for persistent SQLite database and verification artifacts.
- **Exposed Port**: `8000` (FastAPI REST endpoints and WebSocket stream).

### Dashboard Container (`dashboard/Dockerfile`)
- **Base Image**: Multi-stage build based on `node:20-alpine`.
  - Stage 1 (`deps`): Installs production packages cleanly via `npm ci`.
  - Stage 2 (`builder`): Compiles TypeScript and Next.js static and server assets via `npm run build`.
  - Stage 3 (`runner`): Stripped runtime container running as an unprivileged user (`nextjs:nodejs`).
- **Exposed Port**: `3000` (Next.js server).

---

## 4. Running the Stack

To build and start the containerized backend and dashboard:
```bash
docker compose up --build
```

To run the serial bridge on the host connecting an EVM unit on `COM3`:
```bash
python serial_bridge.py --port COM3 --election-id EV-2026-001 --api-url http://localhost:8000
```
