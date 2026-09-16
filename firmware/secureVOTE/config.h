#ifndef SECUREVOTE_CONFIG_H
#define SECUREVOTE_CONFIG_H

#include <stdint.h>

// =============================================================================
// SecureVOTE Embedded Prototype — Hardware Configuration & Pinout Definition
// Target: Arduino Uno (ATmega328P) @ 16 MHz
// LCD: 20x4 Character LCD with PCF8574 I2C Backpack (Address: 0x27)
// =============================================================================

// --- PINOUT ALLOCATION (Verified Zero-Conflict) ---
// Serial UART
#define PIN_SERIAL_RX       0   // Hardware UART RX (Reserved)
#define PIN_SERIAL_TX       1   // Hardware UART TX (Reserved)

// Candidate Selection Buttons (Active LOW with INPUT_PULLUP)
#define PIN_BTN_CAND_1      2   // Candidate 1 (Alice Vance)
#define PIN_BTN_CAND_2      3   // Candidate 2 (Bob Jenkins)
#define PIN_BTN_CAND_3      4   // Candidate 3 (Carol Danvers)
#define PIN_BTN_CAND_4      5   // Candidate 4 (David Miller)

// Control Buttons (Active LOW with INPUT_PULLUP)
#define PIN_BTN_CONFIRM     6   // Cast / Confirm / Enter
#define PIN_BTN_ADMIN       7   // Admin / Mode / Next Digit

// Security / Tamper Switch (Active LOW when closed; HIGH when lid opens)
#define PIN_TAMPER_SWITCH   8   // Enclosure Lid Tamper Microswitch

// Visual Indicators
#define PIN_LED_GREEN       9   // Status LED: Solid = READY, Blink = VOTING/CONFIRM
#define PIN_LED_RED         10  // Alert LED: Solid = TAMPER/ERROR, Blink = ADMIN_AUTH

// Auditory Indicator
#define PIN_BUZZER          11  // Piezo Buzzer: Short beep = Vote, Long tone = Alarm

// I2C Bus for LCD Display
#define PIN_I2C_SDA         A4  // I2C Data
#define PIN_I2C_SCL         A5  // I2C Clock
#define LCD_I2C_ADDR        0x27
#define LCD_COLS            20
#define LCD_ROWS            4

// --- TIMING CONSTANTS (Milliseconds) ---
#define DEBOUNCE_DELAY_MS       50      // Button debounce settling time
#define IDLE_TIMEOUT_MS         30000   // 30s timeout: reset VOTING/CONFIRM to READY
#define ADMIN_HOLD_DELAY_MS     2000    // Hold admin button for 2s to enter ADMIN_AUTH
#define BEEP_VOTE_MS            120     // Short confirmation beep duration
#define BEEP_TAMPER_MS          1200    // Long tamper alarm tone duration
#define HEARTBEAT_INTERVAL_MS   10000   // Serial heartbeat broadcast interval
#define BLINK_INTERVAL_MS       350     // LED blinking half-period

// --- ELECTION & DEVICE METADATA ---
#define DEVICE_ID_STR           "EVM-001"
#define ELECTION_ID_STR         "EV-2026-001"
#define DEFAULT_ADMIN_PIN       "1234"  // 4-digit PIN for educational prototype
#define NUM_CANDIDATES          4

// Expected Frozen Configuration Hash (SHA-256 of candidate list)
// Matches Phase 1 compute_configuration_hash("EV-2026-001", candidates)
#define EXPECTED_CONFIG_HASH    "34d70b0c609559c403328e1215b3e6c0c5980e07cb185b3db5c088c445a49f87"

// Candidate Data Structure
struct CandidateInfo {
    const char* id;
    const char* name;
    const char* party;
    char symbol;
};

// Candidate Table (Position 1..4)
static const CandidateInfo CANDIDATES[NUM_CANDIDATES] = {
    {"C001", "Alice Vance",    "Forward Alliance",      'A'},
    {"C002", "Bob Jenkins",    "Civic Liberty",         'B'},
    {"C003", "Carol Danvers",  "Reform Union",          'C'},
    {"C004", "David Miller",   "Independent Coalition", 'D'}
};

// --- EEPROM MEMORY MAP (Strict Discipline: No per-vote data stored) ---
// Total ATmega328P EEPROM: 1024 Bytes
#define EEPROM_MAGIC_ADDR       0x00    // 2 bytes: Magic marker (0x53, 0x56 = "SV")
#define EEPROM_MAGIC_VAL        0x5653  // Little-endian 'SV'
#define EEPROM_DEVICE_ID_ADDR   0x02    // 8 bytes: Device ID string (e.g. "EVM-001\0")
#define EEPROM_SEQ_ADDR         0x0A    // 4 bytes: uint32_t Monotonic Sequence Counter
#define EEPROM_TAMPER_ADDR      0x0E    // 1 byte:  uint8_t Tamper Latch (1 = tampered)
#define EEPROM_CONFIG_HASH_ADDR 0x0F    // 65 bytes: Config hash string (64 hex + null)
#define EEPROM_PIN_ADDR         0x50    // 5 bytes: Admin PIN ("1234\0")
#define EEPROM_PAUSE_ADDR       0x56    // 1 byte:  uint8_t Pause Flag (1 = paused, 0 = active/ready)

#endif // SECUREVOTE_CONFIG_H
