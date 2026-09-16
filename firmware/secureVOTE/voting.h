#ifndef SECUREVOTE_VOTING_H
#define SECUREVOTE_VOTING_H

#include <stdint.h>
#include <stdbool.h>
#include "config.h"

// Initialize voting subsystem
void voting_init(void);

// Record voter button press for candidate index (0..3)
// Returns true if selection was updated
bool voting_select_candidate(int candidate_idx, uint32_t current_time_ms);

// Get currently selected candidate (0..3, or -1 if none)
int voting_get_selected_candidate(void);

// Confirm selection (transitions to CONFIRM, then returns true when ready for submission)
bool voting_handle_confirm(uint32_t current_time_ms);

// Cancel selection / go back
void voting_cancel_selection(void);

// Check if current voting session has timed out (30 seconds of inactivity)
bool voting_is_idle_timeout(uint32_t current_time_ms);

// Reset voting session data
void voting_reset_session(void);

// Explicitly discard in-progress ballot selection if session interrupted (e.g. paused)
// Ensures ballot is never partially recorded or carried across state boundaries
void voting_discard_in_flight(void);

// Get last interaction time
uint32_t voting_get_last_activity_ms(void);

#endif // SECUREVOTE_VOTING_H
