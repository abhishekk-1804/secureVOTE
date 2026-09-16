#ifndef SECUREVOTE_STATE_MACHINE_H
#define SECUREVOTE_STATE_MACHINE_H

#include <stdint.h>
#include <stdbool.h>

// =============================================================================
// SecureVOTE Finite State Machine
// 12 States covering boot, operation, authentication, tamper, and recovery
// =============================================================================

typedef enum {
    STATE_BOOT = 0,
    STATE_SELF_TEST,
    STATE_READY,
    STATE_ADMIN_AUTH,
    STATE_VOTING,
    STATE_CONFIRM,
    STATE_VOTE_SUBMISSION,
    STATE_AUDIT_COMMIT,
    STATE_VOTE_COMPLETE,
    STATE_PAUSED,
    STATE_TAMPER_DETECTED,
    STATE_ERROR
} FSMState;

// State names for logging and debugging
const char* fsm_state_name(FSMState state);

// State machine lifecycle
void fsm_init(void);

// Get current state
FSMState fsm_get_current_state(void);

// Get previous state before current transition
FSMState fsm_get_previous_state(void);

// Get state duration in milliseconds
uint32_t fsm_get_state_duration_ms(uint32_t current_time_ms);

// Check if a state transition is valid according to the formal transition matrix
bool fsm_is_transition_valid(FSMState from, FSMState to);

// Request a state transition. Returns true if allowed, false if rejected.
bool fsm_transition_to(FSMState new_state, uint32_t current_time_ms);

// Emergency tamper trigger (callable from any state)
void fsm_trigger_tamper(uint32_t current_time_ms);

// Unrecoverable error trigger
void fsm_trigger_error(uint32_t current_time_ms);

// Execute the recovery flow: called after successful ADMIN_AUTH
// Validates configuration hash: if valid -> READY, else -> ERROR
bool fsm_execute_recovery(bool config_hash_valid, uint32_t current_time_ms);

// Check if the current state permits voting actions
bool fsm_can_vote(void);

// Check if device is in a locked/security state
bool fsm_is_locked(void);

#endif // SECUREVOTE_STATE_MACHINE_H
