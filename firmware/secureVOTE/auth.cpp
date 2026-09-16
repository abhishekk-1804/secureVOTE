#include "auth.h"
#include <string.h>

static char expected_pin[PIN_LENGTH + 1] = "1234";
static int entered_digits[PIN_LENGTH] = {0, 0, 0, 0};
static int current_digit_idx = 0;
static int failed_attempts = 0;
static bool in_progress = false;

void auth_init(const char* correct_pin) {
    if (correct_pin && strlen(correct_pin) >= PIN_LENGTH) {
        strncpy(expected_pin, correct_pin, PIN_LENGTH);
        expected_pin[PIN_LENGTH] = '\0';
    }
    auth_reset_input();
    failed_attempts = 0;
}

void auth_reset_input(void) {
    for (int i = 0; i < PIN_LENGTH; i++) {
        entered_digits[i] = 0;
    }
    current_digit_idx = 0;
    in_progress = true;
}

void auth_increment_digit(void) {
    if (current_digit_idx >= 0 && current_digit_idx < PIN_LENGTH) {
        entered_digits[current_digit_idx] = (entered_digits[current_digit_idx] + 1) % 10;
    }
}

int auth_get_current_digit_idx(void) {
    return current_digit_idx;
}

int auth_get_digit_value(int idx) {
    if (idx >= 0 && idx < PIN_LENGTH) {
        return entered_digits[idx];
    }
    return 0;
}

bool auth_advance_digit(void) {
    current_digit_idx++;
    if (current_digit_idx >= PIN_LENGTH) {
        in_progress = false;
        return true; // All digits entered
    }
    return false;
}

bool auth_verify_pin(void) {
    char entered_pin_str[PIN_LENGTH + 1];
    for (int i = 0; i < PIN_LENGTH; i++) {
        entered_pin_str[i] = '0' + entered_digits[i];
    }
    entered_pin_str[PIN_LENGTH] = '\0';

    if (strncmp(entered_pin_str, expected_pin, PIN_LENGTH) == 0) {
        failed_attempts = 0;
        in_progress = false;
        return true;
    } else {
        failed_attempts++;
        auth_reset_input();
        return false;
    }
}

bool auth_is_in_progress(void) {
    return in_progress;
}

void auth_set_pin(const char* pin) {
    if (pin && strlen(pin) >= PIN_LENGTH) {
        strncpy(expected_pin, pin, PIN_LENGTH);
        expected_pin[PIN_LENGTH] = '\0';
    }
}

int auth_get_failed_attempts(void) {
    return failed_attempts;
}
