#ifndef SECUREVOTE_TAMPER_H
#define SECUREVOTE_TAMPER_H

#include <stdint.h>
#include <stdbool.h>

// Initialize tamper detection hardware
void tamper_init(void);

// Poll tamper switch with software debounce.
// Returns true if an active tamper trigger was detected.
bool tamper_poll(uint32_t current_time_ms);

// Check current physical switch state (true = enclosure open / circuit broken)
bool tamper_is_physical_switch_open(void);

// For testing: simulate physical tamper switch state
void tamper_set_mock_state(bool is_open);

#endif // SECUREVOTE_TAMPER_H
