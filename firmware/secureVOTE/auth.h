#ifndef SECUREVOTE_AUTH_H
#define SECUREVOTE_AUTH_H

#include <stdint.h>
#include <stdbool.h>

#define PIN_LENGTH 4

// Initialize auth module
void auth_init(const char* correct_pin);

// Reset PIN input buffer
void auth_reset_input(void);

// Increment current digit (0..9)
void auth_increment_digit(void);

// Get current editing digit index (0..3)
int auth_get_current_digit_idx(void);

// Get value of a specific entered digit (0..9)
int auth_get_digit_value(int idx);

// Advance to next digit. Returns true if all 4 digits have been entered
bool auth_advance_digit(void);

// Verify the entered PIN against the expected PIN
bool auth_verify_pin(void);

// Check if currently entering PIN
bool auth_is_in_progress(void);

// Set expected PIN
void auth_set_pin(const char* pin);

// Get failed attempt count
int auth_get_failed_attempts(void);

#endif // SECUREVOTE_AUTH_H
