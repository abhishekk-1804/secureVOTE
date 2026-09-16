#include "voting.h"

static int selected_candidate = -1;
static uint32_t last_activity_ms = 0;
static bool selection_confirmed = false;

void voting_init(void) {
    selected_candidate = -1;
    last_activity_ms = 0;
    selection_confirmed = false;
}

bool voting_select_candidate(int candidate_idx, uint32_t current_time_ms) {
    if (candidate_idx < 0 || candidate_idx >= NUM_CANDIDATES) {
        return false;
    }
    selected_candidate = candidate_idx;
    last_activity_ms = current_time_ms;
    selection_confirmed = false;
    return true;
}

int voting_get_selected_candidate(void) {
    return selected_candidate;
}

bool voting_handle_confirm(uint32_t current_time_ms) {
    if (selected_candidate < 0 || selected_candidate >= NUM_CANDIDATES) {
        return false;
    }
    last_activity_ms = current_time_ms;
    selection_confirmed = true;
    return true;
}

void voting_cancel_selection(void) {
    selected_candidate = -1;
    selection_confirmed = false;
}

bool voting_is_idle_timeout(uint32_t current_time_ms) {
    if (last_activity_ms == 0) {
        return false;
    }
    return ((current_time_ms - last_activity_ms) >= IDLE_TIMEOUT_MS);
}

void voting_reset_session(void) {
    selected_candidate = -1;
    last_activity_ms = 0;
    selection_confirmed = false;
}

void voting_discard_in_flight(void) {
    // Explicitly zero-out and discard in-progress ballot
    selected_candidate = -1;
    last_activity_ms = 0;
    selection_confirmed = false;
}

uint32_t voting_get_last_activity_ms(void) {
    return last_activity_ms;
}
