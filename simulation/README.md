# SecureVOTE — Wokwi Simulation Guide

This directory contains the hardware simulation schematics and configuration for running SecureVOTE on an Arduino Uno inside the [Wokwi](https://wokwi.com) simulator.

---

## Files in this Directory

- `diagram.json`: Complete circuit wiring diagram connecting:
  - Arduino Uno microcontroller board.
  - 20x4 I2C LCD Display (SDA -> A4, SCL -> A5).
  - 4 Candidate Selection pushbuttons (Pins 2, 3, 4, 5).
  - Confirm pushbutton (Pin 6).
  - Admin pushbutton (Pin 7).
  - Tamper Lid Slide Switch (`sw_tamper`, Pin 8, for interactive browser testing).
  - Tamper Breach Pushbutton (`btn_tamper`, Pin 8, for automated scenario execution).
  - Tamper Pull-down Resistor (`r_tamper`, 1k ohm between Pin 8 and GND).
  - Green Status LED (Pin 9).
  - Red Tamper/Error LED (Pin 10).
  - Piezo Buzzer (Pin 11).
- `scenario-tamper.yaml`: Automated Wokwi scenario that boots the device, waits for `READY`, programmatically triggers the tamper switch, and asserts the resulting `TAMPER` alert and `STATE_CHANGE` transition (`from_state: READY -> to_state: TAMPER_DETECTED`).
- `wokwi.toml`: PlatformIO / Wokwi integration configuration mapping the ELF and HEX firmware binaries (`.pio/build/uno/firmware.hex`).

---

## How to Build the Firmware

From the `firmware/` directory:

```bash
# Build Arduino Uno firmware binary
pio run

# Run native host unit tests (17/17 passing)
g++ -static -I../secureVOTE test/test_firmware.cpp ../secureVOTE/state_machine.cpp ../secureVOTE/voting.cpp ../secureVOTE/auth.cpp ../secureVOTE/storage.cpp ../secureVOTE/tamper.cpp -o test/test_firmware.exe
./test/test_firmware.exe
```

The compiled binary will be located at:
`firmware/.pio/build/uno/firmware.hex`

---

## Running the Simulation

### Option A: Wokwi Web Simulator (Recommended for visual testing)
1. Open [wokwi.com](https://wokwi.com).
2. Start a new **Arduino Uno** project.
3. Switch to the `diagram.json` tab and paste the contents of `simulation/diagram.json`.
4. Upload the compiled `firmware.hex` or copy the source files from `firmware/secureVOTE/`.
5. Click **Start Simulation**.
6. Observe LCD welcome screen, LED status, and button interactions.
7. Click the **TAMPER TEST** button or slide the tamper switch to trigger the physical breach.
8. Observe immediate transition: Red LED solid, buzzer alarm, and serial alert emission.

### Option B: Wokwi CLI (Automated Scenario)
When a Wokwi CLI authentication token is available:

```bash
# Set your token
export WOKWI_CLI_TOKEN="your_token_here"

# Run automated tamper scenario
wokwi-cli --scenario simulation/scenario-tamper.yaml simulation/
```

The scenario will:
1. Wait for `{"type":"STATE_CHANGE", ... "from_state":"SELF_TEST","to_state":"READY"}`
2. Trigger the tamper switch via `set-control: part-id: btn_tamper, control: pressed, value: 1`
3. Capture the `TAMPER` alert
4. Assert the corrected `STATE_CHANGE` serial event: `from_state: READY` $\rightarrow$ `to_state: TAMPER_DETECTED` (proving it does **not** report `TAMPER_DETECTED -> TAMPER_DETECTED`).

---

## Connecting the Serial Bridge

To stream events from Wokwi or a real Arduino Uno directly into the SecureVOTE FastAPI backend:

```bash
# Ensure backend is running
cd backend
source venv/Scripts/activate
uvicorn app.main:app --port 8000

# In another terminal, run the serial bridge
cd firmware/bridge
# For production/fail-closed mode (real session tokens required):
python serial_bridge.py --port COM3 --baud 9600 --election EV-2026-001

# For automated demo mode (permitting synthetic session credentials):
python serial_bridge.py --port COM3 --baud 9600 --election EV-2026-001 --demo-mode
```
