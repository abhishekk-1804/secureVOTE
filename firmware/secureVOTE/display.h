#ifndef SECUREVOTE_DISPLAY_H
#define SECUREVOTE_DISPLAY_H

#include <stdint.h>
#include <stdbool.h>
#include "state_machine.h"

// Initialize display and visual/auditory indicators
void display_init(void);

// Update LCD screen according to current FSM state and parameters
void display_render_state(FSMState state, uint32_t current_time_ms);

// Update LED blinking/solid patterns based on current FSM state
void display_update_indicators(FSMState state, uint32_t current_time_ms);

// Sound a short confirmation beep (120ms)
void display_beep_vote(void);

// Sound a long alarm tone (1200ms)
void display_beep_tamper(void);

// Turn off buzzer immediately
void display_buzzer_off(void);

#endif // SECUREVOTE_DISPLAY_H
