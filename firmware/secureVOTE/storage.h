#ifndef SECUREVOTE_STORAGE_H
#define SECUREVOTE_STORAGE_H

#include <stdint.h>
#include <stdbool.h>

// Initialize persistent storage subsystem (checks magic bytes, formats on first boot)
void storage_init(void);

// Read restored monotonic sequence counter
uint32_t storage_get_sequence_counter(void);

// Increment and atomically persist the monotonic sequence counter to EEPROM
// Returns the newly incremented sequence counter
uint32_t storage_increment_sequence_counter(void);

// Read tamper latch flag (1 = tampered, 0 = untampered)
uint8_t storage_get_tamper_flag(void);

// Set and persist tamper latch flag
void storage_set_tamper_flag(uint8_t flag);

// Clear tamper latch flag (only callable during admin recovery)
void storage_clear_tamper_flag(void);

// Read persistent pause flag from EEPROM (1 = paused, 0 = ready/active)
uint8_t storage_get_pause_flag(void);

// Set and persist pause flag in EEPROM across reboots
void storage_set_pause_flag(uint8_t flag);

// Get stored device ID string (e.g. "EVM-001")
const char* storage_get_device_id(void);

// Set and persist device ID string
void storage_set_device_id(const char* device_id);

// Get stored configuration hash
const char* storage_get_config_hash(void);

// Set and persist configuration hash
void storage_set_config_hash(const char* hash);

// Validate current configuration hash against expected hash
bool storage_validate_config_hash(const char* expected_hash);

// Reset storage to factory default test state
void storage_format(void);

#endif // SECUREVOTE_STORAGE_H
