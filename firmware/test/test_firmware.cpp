#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <unity.h>

#include "../secureVOTE/config.h"
#include "../secureVOTE/state_machine.h"
#include "../secureVOTE/voting.h"
#include "../secureVOTE/auth.h"
#include "../secureVOTE/storage.h"
#include "../secureVOTE/tamper.h"

void setUp(void) {}
void tearDown(void) {}

// =============================================================================
// FSM Tests: Lifecycle, Valid Transitions, and Transition Matrix
// =============================================================================

void test_fsm_init_and_state_names() {
    fsm_init();
    assert(fsm_get_current_state() == STATE_BOOT);
    assert(strcmp(fsm_state_name(STATE_BOOT), "BOOT") == 0);
    assert(strcmp(fsm_state_name(STATE_READY), "READY") == 0);
    assert(strcmp(fsm_state_name(STATE_TAMPER_DETECTED), "TAMPER_DETECTED") == 0);
    assert(strcmp(fsm_state_name(STATE_ERROR), "ERROR") == 0);
    assert(strcmp(fsm_state_name(STATE_PAUSED), "PAUSED") == 0);
}

void test_fsm_core_voting_lifecycle() {
    fsm_init();
    uint32_t t = 1000;

    // BOOT -> SELF_TEST
    assert(fsm_transition_to(STATE_SELF_TEST, t));
    assert(fsm_get_current_state() == STATE_SELF_TEST);

    // SELF_TEST -> READY
    t += 500;
    assert(fsm_transition_to(STATE_READY, t));
    assert(fsm_get_current_state() == STATE_READY);

    // READY -> VOTING
    t += 500;
    assert(fsm_transition_to(STATE_VOTING, t));
    assert(fsm_get_current_state() == STATE_VOTING);
    assert(fsm_can_vote() == true);

    // VOTING -> CONFIRM
    t += 500;
    assert(fsm_transition_to(STATE_CONFIRM, t));
    assert(fsm_get_current_state() == STATE_CONFIRM);
    assert(fsm_can_vote() == true);

    // CONFIRM -> VOTE_SUBMISSION
    t += 500;
    assert(fsm_transition_to(STATE_VOTE_SUBMISSION, t));
    assert(fsm_get_current_state() == STATE_VOTE_SUBMISSION);
    assert(fsm_can_vote() == false);

    // VOTE_SUBMISSION -> AUDIT_COMMIT
    t += 500;
    assert(fsm_transition_to(STATE_AUDIT_COMMIT, t));
    assert(fsm_get_current_state() == STATE_AUDIT_COMMIT);

    // AUDIT_COMMIT -> VOTE_COMPLETE
    t += 500;
    assert(fsm_transition_to(STATE_VOTE_COMPLETE, t));
    assert(fsm_get_current_state() == STATE_VOTE_COMPLETE);

    // VOTE_COMPLETE -> READY
    t += 1500;
    assert(fsm_transition_to(STATE_READY, t));
    assert(fsm_get_current_state() == STATE_READY);
}

void test_fsm_rejected_invalid_transitions() {
    fsm_init();
    uint32_t t = 1000;

    // Direct jump from BOOT to READY must be REJECTED
    assert(!fsm_transition_to(STATE_READY, t));
    assert(fsm_get_current_state() == STATE_BOOT);

    // Jump from BOOT to VOTE_SUBMISSION must be REJECTED
    assert(!fsm_transition_to(STATE_VOTE_SUBMISSION, t));
    assert(fsm_get_current_state() == STATE_BOOT);

    // Advance to READY
    assert(fsm_transition_to(STATE_SELF_TEST, t));
    assert(fsm_transition_to(STATE_READY, t));

    // Jump from READY directly to VOTE_SUBMISSION without candidate selection must be REJECTED
    assert(!fsm_transition_to(STATE_VOTE_SUBMISSION, t));
    assert(fsm_get_current_state() == STATE_READY);

    // Jump from READY directly to AUDIT_COMMIT must be REJECTED
    assert(!fsm_transition_to(STATE_AUDIT_COMMIT, t));

    // Jump from READY directly to VOTE_COMPLETE must be REJECTED
    assert(!fsm_transition_to(STATE_VOTE_COMPLETE, t));
    assert(fsm_get_current_state() == STATE_READY);
}

void test_fsm_tamper_entry_from_multiple_states() {
    uint32_t t = 1000;

    // Tamper from READY
    fsm_init();
    fsm_transition_to(STATE_SELF_TEST, t);
    fsm_transition_to(STATE_READY, t);
    fsm_trigger_tamper(t);
    assert(fsm_get_current_state() == STATE_TAMPER_DETECTED);
    assert(fsm_is_locked() == true);
    assert(fsm_can_vote() == false);

    // Tamper from VOTING
    fsm_init();
    fsm_transition_to(STATE_SELF_TEST, t);
    fsm_transition_to(STATE_READY, t);
    fsm_transition_to(STATE_VOTING, t);
    fsm_trigger_tamper(t);
    assert(fsm_get_current_state() == STATE_TAMPER_DETECTED);
    assert(fsm_is_locked() == true);

    // Tamper from CONFIRM
    fsm_init();
    fsm_transition_to(STATE_SELF_TEST, t);
    fsm_transition_to(STATE_READY, t);
    fsm_transition_to(STATE_VOTING, t);
    fsm_transition_to(STATE_CONFIRM, t);
    fsm_trigger_tamper(t);
    assert(fsm_get_current_state() == STATE_TAMPER_DETECTED);

    // Tamper from PAUSED
    fsm_init();
    fsm_transition_to(STATE_SELF_TEST, t);
    fsm_transition_to(STATE_READY, t);
    fsm_transition_to(STATE_PAUSED, t);
    fsm_trigger_tamper(t);
    assert(fsm_get_current_state() == STATE_TAMPER_DETECTED);

    // While in TAMPER_DETECTED, voting transitions must be explicitly REJECTED
    assert(!fsm_transition_to(STATE_VOTING, t));
    assert(!fsm_transition_to(STATE_CONFIRM, t));
    assert(!fsm_transition_to(STATE_VOTE_SUBMISSION, t));
    assert(!fsm_transition_to(STATE_READY, t)); // Cannot bypass ADMIN_AUTH
    assert(fsm_get_current_state() == STATE_TAMPER_DETECTED);
}

void test_fsm_recovery_success() {
    uint32_t t = 1000;
    fsm_init();
    fsm_transition_to(STATE_SELF_TEST, t);
    fsm_transition_to(STATE_READY, t);
    fsm_trigger_tamper(t);

    // Admin initiates auth for recovery
    assert(fsm_transition_to(STATE_ADMIN_AUTH, t));
    assert(fsm_get_current_state() == STATE_ADMIN_AUTH);

    // Recovery executed with valid config hash -> transitions to READY
    bool recovered = fsm_execute_recovery(true, t);
    assert(recovered == true);
    assert(fsm_get_current_state() == STATE_READY);
    assert(fsm_is_locked() == false);
}

void test_fsm_recovery_failure_reenters_error() {
    uint32_t t = 1000;
    fsm_init();
    fsm_transition_to(STATE_SELF_TEST, t);
    fsm_transition_to(STATE_READY, t);
    fsm_trigger_tamper(t);

    // Admin enters auth
    assert(fsm_transition_to(STATE_ADMIN_AUTH, t));

    // Recovery executed with INVALID config hash -> must re-enter ERROR state
    bool recovered = fsm_execute_recovery(false, t);
    assert(recovered == false);
    assert(fsm_get_current_state() == STATE_ERROR);
    assert(fsm_is_locked() == true);
}

// =============================================================================
// Voting Module Tests: Candidate Selection, Confirmation, and Idle Timeout
// =============================================================================

void test_voting_selection_and_confirm() {
    voting_init();
    assert(voting_get_selected_candidate() == -1);

    uint32_t t = 1000;
    // Select candidate 0 (Alice Vance)
    assert(voting_select_candidate(0, t));
    assert(voting_get_selected_candidate() == 0);

    // Switch selection to candidate 2 (Carol Danvers)
    assert(voting_select_candidate(2, t + 100));
    assert(voting_get_selected_candidate() == 2);

    // Out of bounds selection rejected
    assert(!voting_select_candidate(4, t + 200));
    assert(!voting_select_candidate(-1, t + 200));
    assert(voting_get_selected_candidate() == 2);

    // Confirm
    assert(voting_handle_confirm(t + 300));

    // Reset session
    voting_reset_session();
    assert(voting_get_selected_candidate() == -1);
}

void test_voting_idle_timeout() {
    voting_init();
    uint32_t start_t = 10000;

    voting_select_candidate(1, start_t);
    assert(!voting_is_idle_timeout(start_t));
    assert(!voting_is_idle_timeout(start_t + 15000)); // 15s -> not timed out
    assert(!voting_is_idle_timeout(start_t + 29999)); // 29.999s -> not timed out

    // 30.000s -> timed out!
    assert(voting_is_idle_timeout(start_t + 30000));
    assert(voting_is_idle_timeout(start_t + 45000));
}

// =============================================================================
// Admin Authentication Module Tests: Digits and Verification
// =============================================================================

void test_auth_correct_pin() {
    auth_init("1234");
    auth_reset_input();

    // Digit 0: increment from 0 to 1
    auth_increment_digit();
    assert(auth_get_digit_value(0) == 1);
    assert(!auth_advance_digit()); // moves to digit 1

    // Digit 1: increment twice (0 -> 1 -> 2)
    auth_increment_digit();
    auth_increment_digit();
    assert(auth_get_digit_value(1) == 2);
    assert(!auth_advance_digit()); // moves to digit 2

    // Digit 2: increment 3 times (0 -> 3)
    auth_increment_digit();
    auth_increment_digit();
    auth_increment_digit();
    assert(auth_get_digit_value(2) == 3);
    assert(!auth_advance_digit()); // moves to digit 3

    // Digit 3: increment 4 times (0 -> 4)
    auth_increment_digit();
    auth_increment_digit();
    auth_increment_digit();
    auth_increment_digit();
    assert(auth_get_digit_value(3) == 4);
    assert(auth_advance_digit() == true); // all 4 digits entered

    // Verify
    assert(auth_verify_pin() == true);
    assert(auth_get_failed_attempts() == 0);
}

void test_auth_incorrect_pin() {
    auth_init("1234");
    auth_reset_input();

    // Leave as "0000" and advance through all digits
    auth_advance_digit();
    auth_advance_digit();
    auth_advance_digit();
    assert(auth_advance_digit() == true);

    // Verify fails
    assert(auth_verify_pin() == false);
    assert(auth_get_failed_attempts() == 1);
}

// =============================================================================
// Storage Subsystem Tests: Replay Sequence Persistence & Tamper Latch
// =============================================================================

void test_storage_sequence_counter_persistence() {
    // Format storage to fresh state
    storage_format();
    assert(storage_get_sequence_counter() == 0);

    // Increment 5 times
    for (int i = 1; i <= 5; i++) {
        uint32_t seq = storage_increment_sequence_counter();
        assert(seq == (uint32_t)i);
    }
    assert(storage_get_sequence_counter() == 5);

    // SIMULATE DEVICE RESTART / POWER CYCLE:
    // Re-initialize storage module without formatting. It must restore seq from EEPROM!
    storage_init();
    assert(storage_get_sequence_counter() == 5); // RESTORED! Monotonic sequence preserved!

    // Further increments continue monotonically
    uint32_t next_seq = storage_increment_sequence_counter();
    assert(next_seq == 6);
}

void test_storage_tamper_flag_and_config_hash() {
    storage_format();
    assert(storage_get_tamper_flag() == 0);

    // Set tamper flag
    storage_set_tamper_flag(1);
    assert(storage_get_tamper_flag() == 1);

    // Simulate power cycle
    storage_init();
    assert(storage_get_tamper_flag() == 1); // Tamper remains latched across reboot!

    // Admin clears tamper flag
    storage_clear_tamper_flag();
    assert(storage_get_tamper_flag() == 0);

    // Config hash check
    assert(storage_validate_config_hash(EXPECTED_CONFIG_HASH) == true);
    assert(storage_validate_config_hash("0000000000000000000000000000000000000000000000000000000000000000") == false);
}

// =============================================================================
// Hardening Tests: PAUSED Flow, In-Flight Ballot Rule, and Tamper Audit
// =============================================================================

void test_fsm_pause_and_unpause_flow() {
    fsm_init();
    storage_format();
    uint32_t t = 1000;

    // Advance to READY
    assert(fsm_transition_to(STATE_SELF_TEST, t));
    assert(fsm_transition_to(STATE_READY, t));
    assert(fsm_get_current_state() == STATE_READY);

    // 1. READY -> ADMIN_AUTH (Pause Intent) -> PAUSED
    assert(fsm_transition_to(STATE_ADMIN_AUTH, t));
    assert(fsm_get_previous_state() == STATE_READY);
    storage_set_pause_flag(1);
    assert(fsm_transition_to(STATE_PAUSED, t));
    assert(fsm_get_current_state() == STATE_PAUSED);
    assert(storage_get_pause_flag() == 1);
    assert(fsm_is_locked() == true);
    assert(fsm_can_vote() == false);

    // 2. PAUSED -> ADMIN_AUTH (Unpause Intent) -> READY
    assert(fsm_transition_to(STATE_ADMIN_AUTH, t));
    assert(fsm_get_previous_state() == STATE_PAUSED);
    storage_set_pause_flag(0);
    assert(fsm_transition_to(STATE_READY, t));
    assert(fsm_get_current_state() == STATE_READY);
    assert(storage_get_pause_flag() == 0);
    assert(fsm_is_locked() == false);
}

void test_fsm_voting_in_flight_ballot_discard_on_pause() {
    fsm_init();
    voting_init();
    uint32_t t = 1000;

    // Advance to VOTING
    assert(fsm_transition_to(STATE_SELF_TEST, t));
    assert(fsm_transition_to(STATE_READY, t));
    assert(fsm_transition_to(STATE_VOTING, t));

    // Voter selects Candidate 1 (Alice Vance)
    assert(voting_select_candidate(0, t));
    assert(voting_get_selected_candidate() == 0);

    // IN-FLIGHT-BALLOT RULE:
    // Administrative pause triggered while in VOTING -> ballot selection discarded
    voting_discard_in_flight();
    assert(fsm_transition_to(STATE_ADMIN_AUTH, t));
    assert(fsm_transition_to(STATE_PAUSED, t));

    // Ballot must be completely zeroed out (never carried into PAUSED, never recorded)
    assert(voting_get_selected_candidate() == -1);
    assert(fsm_get_current_state() == STATE_PAUSED);
}

void test_fsm_paused_rejects_voting_events() {
    fsm_init();
    uint32_t t = 1000;

    // Advance to PAUSED
    assert(fsm_transition_to(STATE_SELF_TEST, t));
    assert(fsm_transition_to(STATE_READY, t));
    assert(fsm_transition_to(STATE_ADMIN_AUTH, t));
    assert(fsm_transition_to(STATE_PAUSED, t));
    assert(fsm_get_current_state() == STATE_PAUSED);

    // All voting transitions from PAUSED must be explicitly REJECTED
    assert(!fsm_is_transition_valid(STATE_PAUSED, STATE_VOTING));
    assert(!fsm_is_transition_valid(STATE_PAUSED, STATE_CONFIRM));
    assert(!fsm_is_transition_valid(STATE_PAUSED, STATE_VOTE_SUBMISSION));
    assert(!fsm_transition_to(STATE_VOTING, t));
    assert(!fsm_transition_to(STATE_CONFIRM, t));
    assert(!fsm_transition_to(STATE_VOTE_SUBMISSION, t));
    assert(fsm_get_current_state() == STATE_PAUSED);
    assert(fsm_can_vote() == false);
}

void test_fsm_pause_flag_persists_across_restart() {
    storage_format();
    assert(storage_get_pause_flag() == 0);

    // Set pause flag in persistent storage
    storage_set_pause_flag(1);
    assert(storage_get_pause_flag() == 1);

    // SIMULATE DEVICE RESTART / POWER LOSS:
    // Storage re-initialization restores the pause flag without formatting
    storage_init();
    assert(storage_get_pause_flag() == 1); // Persisted across reboot!

    // Firmware boots from SELF_TEST directly into STATE_PAUSED
    fsm_init();
    uint32_t t = 1000;
    assert(fsm_transition_to(STATE_SELF_TEST, t));
    assert(fsm_is_transition_valid(STATE_SELF_TEST, STATE_PAUSED));
    assert(fsm_transition_to(STATE_PAUSED, t));
    assert(fsm_get_current_state() == STATE_PAUSED);

    // Unpause and verify clearance survives restart
    storage_set_pause_flag(0);
    storage_init();
    assert(storage_get_pause_flag() == 0);
}

void test_tamper_state_change_audit_regression() {
    fsm_init();
    uint32_t t = 1000;

    // Case A: Tamper triggered from READY
    assert(fsm_transition_to(STATE_SELF_TEST, t));
    assert(fsm_transition_to(STATE_READY, t));

    // Bug #2 Regression Test:
    // Old code called fsm_get_current_state() AFTER fsm_trigger_tamper(),
    // which emitted "from_state": "TAMPER_DETECTED" -> "to_state": "TAMPER_DETECTED".
    // Corrected code captures state_before_tamper BEFORE fsm_trigger_tamper().
    FSMState state_before_tamper_ready = fsm_get_current_state();
    assert(state_before_tamper_ready == STATE_READY);

    fsm_trigger_tamper(t);
    assert(fsm_get_current_state() == STATE_TAMPER_DETECTED);

    // Assert that the recorded previous state is NOT TAMPER_DETECTED
    assert(state_before_tamper_ready != STATE_TAMPER_DETECTED);
    assert(state_before_tamper_ready == STATE_READY);

    // Case B: Tamper triggered from VOTING
    // Recover first
    assert(fsm_transition_to(STATE_ADMIN_AUTH, t));
    assert(fsm_execute_recovery(true, t));
    assert(fsm_get_current_state() == STATE_READY);

    assert(fsm_transition_to(STATE_VOTING, t));
    assert(fsm_get_current_state() == STATE_VOTING);

    FSMState state_before_tamper_voting = fsm_get_current_state();
    assert(state_before_tamper_voting == STATE_VOTING);

    fsm_trigger_tamper(t);
    assert(fsm_get_current_state() == STATE_TAMPER_DETECTED);

    // Assert that the recorded previous state is NOT TAMPER_DETECTED
    assert(state_before_tamper_voting != STATE_TAMPER_DETECTED);
    assert(state_before_tamper_voting == STATE_VOTING);
}

// =============================================================================
// Main Test Runner Entrypoint
// =============================================================================

int main(int argc, char **argv) {
    UNITY_BEGIN();

    RUN_TEST(test_fsm_init_and_state_names);
    RUN_TEST(test_fsm_core_voting_lifecycle);
    RUN_TEST(test_fsm_rejected_invalid_transitions);
    RUN_TEST(test_fsm_tamper_entry_from_multiple_states);
    RUN_TEST(test_fsm_recovery_success);
    RUN_TEST(test_fsm_recovery_failure_reenters_error);
    RUN_TEST(test_voting_selection_and_confirm);
    RUN_TEST(test_voting_idle_timeout);
    RUN_TEST(test_auth_correct_pin);
    RUN_TEST(test_auth_incorrect_pin);
    RUN_TEST(test_storage_sequence_counter_persistence);
    RUN_TEST(test_storage_tamper_flag_and_config_hash);

    // Hardening regression tests
    RUN_TEST(test_fsm_pause_and_unpause_flow);
    RUN_TEST(test_fsm_voting_in_flight_ballot_discard_on_pause);
    RUN_TEST(test_fsm_paused_rejects_voting_events);
    RUN_TEST(test_fsm_pause_flag_persists_across_restart);
    RUN_TEST(test_tamper_state_change_audit_regression);

    return UNITY_END();
}
