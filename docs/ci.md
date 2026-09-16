# SecureVOTE — CI/CD Pipeline & Automated Verification Strategy

## 1. Overview

SecureVOTE utilizes GitHub Actions (`.github/workflows/ci.yml`) to enforce automated verification across all layers of the project on every commit and pull request to `main`.

The pipeline executes three parallel validation jobs:
1. **`firmware`**: Compiles the embedded Arduino Uno C++ firmware and runs the 17-test native PlatformIO test suite.
2. **`backend`**: Executes the comprehensive 37-test pytest suite covering attack trees, replay protection, multi-device aggregation, export verification, and WebSocket streaming.
3. **`dashboard`**: Executes the Vitest component test suite and compiles the Next.js production build with full TypeScript type checks.

---

## 2. Hardware & Simulation Exclusion Rationale

A critical architectural decision for the SecureVOTE CI pipeline is the **explicit exclusion of physical serial hardware and headless Wokwi execution**:

### Why Physical Serial Hardware is Excluded
1. **Cloud Runner Constraints**: GitHub Actions runners are headless Linux virtual machines hosted in Microsoft Azure data centers. They do not possess physical USB ports connected to Arduino Uno microcontrollers.
2. **No Hardware Loopback Emulation**: Simulating hardware UART via software bridges in CI creates fragile, timing-dependent tests that often produce false positives/negatives without providing real hardware confidence.
3. **Native Firmware Testing**: Instead of requiring physical hardware, SecureVOTE implements PlatformIO's `native` environment. The exact same C++ FSM, EEPROM storage emulator, voting logic, and tamper state machines compile and run natively on x86_64 GCC, exercising 17 rigorous test cases in ~2 seconds.

### Why Wokwi Headless Simulation is Excluded
1. **Secret Dependency**: Headless execution via the Wokwi CLI requires a paid or authenticated `WOKWI_CLI_TOKEN`. Public open-source CI runs and forks cannot assume the presence of third-party commercial tokens.
2. **Interactive UI Focus**: Wokwi is primarily an interactive visual simulator for educational demonstration and circuit wiring exploration (`diagram.json`). Automated unit tests provide stronger, deterministic regression protection than headless browser simulations.

---

## 3. Job Specifications

### Job 1: `firmware`
- **Compiler**: `avr-gcc` via PlatformIO toolchain + host GCC.
- **Commands**:
  - `pio run -d firmware -e uno`: Verifies that ATmega328P code compiles within flash (32KB) and SRAM (2KB) memory limits.
  - `pio test -d firmware -e native`: Runs 17 unit tests verifying FSM state transitions, pause recovery, in-flight ballot discard, and EEPROM sequence monotonicity.

### Job 2: `backend`
- **Environment**: Python 3.12 on `ubuntu-latest`.
- **Commands**:
  - `pytest backend/tests/ -v`: Runs all 37 integration, attack simulation, serial bridge, export verification, and multi-device tests.

### Job 3: `dashboard`
- **Environment**: Node.js 20 on `ubuntu-latest`.
- **Commands**:
  - `npm test -- --run`: Runs Vitest component and behavioral tests.
  - `npm run build`: Validates Next.js static asset compilation and TypeScript type integrity.
