#include "tamper.h"
#include "config.h"

#ifdef ARDUINO
#include <Arduino.h>
#else
static bool mock_tamper_open = false;
#endif

static bool last_raw_state = false;
static bool debounced_state = false;
static uint32_t last_debounce_time = 0;

void tamper_init(void) {
#ifdef ARDUINO
    pinMode(PIN_TAMPER_SWITCH, INPUT);
    // In normal state, pulldown resistor connects pin to GND -> LOW (false)
    // When tamper breached (switch or test button triggered), connects to 5V -> HIGH (true)
    debounced_state = (digitalRead(PIN_TAMPER_SWITCH) == HIGH);
    last_raw_state = debounced_state;
#else
    mock_tamper_open = false;
    debounced_state = false;
    last_raw_state = false;
#endif
    last_debounce_time = 0;
}

bool tamper_is_physical_switch_open(void) {
#ifdef ARDUINO
    return (digitalRead(PIN_TAMPER_SWITCH) == HIGH);
#else
    return mock_tamper_open;
#endif
}

void tamper_set_mock_state(bool is_open) {
#ifndef ARDUINO
    mock_tamper_open = is_open;
#endif
}

bool tamper_poll(uint32_t current_time_ms) {
    bool raw = tamper_is_physical_switch_open();

    if (raw != last_raw_state) {
        last_debounce_time = current_time_ms;
        last_raw_state = raw;
    }

    if ((current_time_ms - last_debounce_time) > DEBOUNCE_DELAY_MS) {
        if (raw != debounced_state) {
            debounced_state = raw;
            if (debounced_state) {
                // Lid opened!
                return true;
            }
        }
    }

    return (debounced_state == true);
}
