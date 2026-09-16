#include "state_machine.h"
#include <stddef.h>

// Current state and timestamp when state was entered
static FSMState current_state = STATE_BOOT;
static FSMState previous_state = STATE_BOOT;
static uint32_t state_entered_ms = 0;

// State names lookup
static const char* STATE_NAMES[] = {
    "BOOT",
    "SELF_TEST",
    "READY",
    "ADMIN_AUTH",
    "VOTING",
    "CONFIRM",
    "VOTE_SUBMISSION",
    "AUDIT_COMMIT",
    "VOTE_COMPLETE",
    "PAUSED",
    "TAMPER_DETECTED",
    "ERROR"
};

const char* fsm_state_name(FSMState state) {
    if ((int)state >= 0 && (int)state <= (int)STATE_ERROR) {
        return STATE_NAMES[state];
    }
    return "UNKNOWN";
}

void fsm_init(void) {
    current_state = STATE_BOOT;
    previous_state = STATE_BOOT;
    state_entered_ms = 0;
}

FSMState fsm_get_current_state(void) {
    return current_state;
}

FSMState fsm_get_previous_state(void) {
    return previous_state;
}

uint32_t fsm_get_state_duration_ms(uint32_t current_time_ms) {
    return current_time_ms - state_entered_ms;
}

bool fsm_is_transition_valid(FSMState from, FSMState to) {
    // Tamper detected can be entered from ANY active state
    if (to == STATE_TAMPER_DETECTED) {
        return true;
    }

    // Error state can be entered from any state
    if (to == STATE_ERROR) {
        return true;
    }

    // State-by-state explicit transition matrix
    switch (from) {
        case STATE_BOOT:
            return (to == STATE_SELF_TEST);

        case STATE_SELF_TEST:
            return (to == STATE_READY || to == STATE_PAUSED);

        case STATE_READY:
            return (to == STATE_ADMIN_AUTH || to == STATE_VOTING || to == STATE_PAUSED);

        case STATE_ADMIN_AUTH:
            // Admin auth can return to ready, pause the device, or enter recovery/error
            return (to == STATE_READY || to == STATE_PAUSED || to == STATE_ERROR || to == STATE_TAMPER_DETECTED);

        case STATE_VOTING:
            // Candidate selected -> CONFIRM; timeout/cancel -> READY; admin pause intent -> ADMIN_AUTH
            return (to == STATE_CONFIRM || to == STATE_READY || to == STATE_ADMIN_AUTH);

        case STATE_CONFIRM:
            // Confirmed -> VOTE_SUBMISSION; Back -> VOTING; Timeout -> READY; admin pause intent -> ADMIN_AUTH
            return (to == STATE_VOTE_SUBMISSION || to == STATE_VOTING || to == STATE_READY || to == STATE_ADMIN_AUTH);

        case STATE_VOTE_SUBMISSION:
            // Transmit -> AUDIT_COMMIT
            return (to == STATE_AUDIT_COMMIT);

        case STATE_AUDIT_COMMIT:
            // Committed -> VOTE_COMPLETE
            return (to == STATE_VOTE_COMPLETE);

        case STATE_VOTE_COMPLETE:
            // Brief visual complete -> READY
            return (to == STATE_READY);

        case STATE_PAUSED:
            // Paused can only be accessed/unpaused via ADMIN_AUTH (all vote events rejected)
            return (to == STATE_ADMIN_AUTH);

        case STATE_TAMPER_DETECTED:
            // TAMPER_DETECTED is exited ONLY via ADMIN_AUTH
            return (to == STATE_ADMIN_AUTH);

        case STATE_ERROR:
            // ERROR is exited ONLY via ADMIN_AUTH
            return (to == STATE_ADMIN_AUTH);

        default:
            return false;
    }
}

bool fsm_transition_to(FSMState new_state, uint32_t current_time_ms) {
    if (!fsm_is_transition_valid(current_state, new_state)) {
        return false; // Explicitly rejected
    }

    previous_state = current_state;
    current_state = new_state;
    state_entered_ms = current_time_ms;
    return true;
}

void fsm_trigger_tamper(uint32_t current_time_ms) {
    previous_state = current_state;
    current_state = STATE_TAMPER_DETECTED;
    state_entered_ms = current_time_ms;
}

void fsm_trigger_error(uint32_t current_time_ms) {
    previous_state = current_state;
    current_state = STATE_ERROR;
    state_entered_ms = current_time_ms;
}

bool fsm_execute_recovery(bool config_hash_valid, uint32_t current_time_ms) {
    // Recovery can only occur from ADMIN_AUTH
    if (current_state != STATE_ADMIN_AUTH) {
        return false;
    }

    // Re-check configuration hash
    if (config_hash_valid) {
        previous_state = current_state;
        current_state = STATE_READY;
        state_entered_ms = current_time_ms;
        return true;
    } else {
        // Hash check failed -> re-enter ERROR state
        previous_state = current_state;
        current_state = STATE_ERROR;
        state_entered_ms = current_time_ms;
        return false;
    }
}

bool fsm_can_vote(void) {
    return (current_state == STATE_VOTING || current_state == STATE_CONFIRM);
}

bool fsm_is_locked(void) {
    return (current_state == STATE_TAMPER_DETECTED ||
            current_state == STATE_ERROR ||
            current_state == STATE_PAUSED);
}
