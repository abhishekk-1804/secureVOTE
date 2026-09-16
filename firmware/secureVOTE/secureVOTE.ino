#include <Arduino.h>
#include "config.h"
#include "state_machine.h"
#include "voting.h"
#include "auth.h"
#include "display.h"
#include "storage.h"
#include "tamper.h"
#include "serial_comm.h"

// Button tracking for edge detection & debouncing
struct ButtonDebounce {
    uint8_t pin;
    bool last_reading;
    bool state;
    uint32_t last_debounce_time;
};

static ButtonDebounce btn_cand1   = {PIN_BTN_CAND_1,  HIGH, HIGH, 0};
static ButtonDebounce btn_cand2   = {PIN_BTN_CAND_2,  HIGH, HIGH, 0};
static ButtonDebounce btn_cand3   = {PIN_BTN_CAND_3,  HIGH, HIGH, 0};
static ButtonDebounce btn_cand4   = {PIN_BTN_CAND_4,  HIGH, HIGH, 0};
static ButtonDebounce btn_confirm = {PIN_BTN_CONFIRM, HIGH, HIGH, 0};
static ButtonDebounce btn_admin   = {PIN_BTN_ADMIN,   HIGH, HIGH, 0};

// Admin button hold duration tracking
static uint32_t admin_press_start_ms = 0;
static bool admin_hold_triggered = false;

// Heartbeat timer
static uint32_t last_heartbeat_ms = 0;

// Helper: Read debounced button press (falling edge: pressed)
static bool is_button_pressed(ButtonDebounce* b, uint32_t now) {
    bool reading = digitalRead(b->pin);
    bool pressed = false;

    if (reading != b->last_reading) {
        b->last_debounce_time = now;
        b->last_reading = reading;
    }

    if ((now - b->last_debounce_time) > DEBOUNCE_DELAY_MS) {
        if (reading != b->state) {
            b->state = reading;
            if (b->state == LOW) {
                pressed = true; // Button pressed (active LOW)
            }
        }
    }
    return pressed;
}

void setup() {
    // 1. Hardware Pin Configurations
    pinMode(PIN_BTN_CAND_1, INPUT_PULLUP);
    pinMode(PIN_BTN_CAND_2, INPUT_PULLUP);
    pinMode(PIN_BTN_CAND_3, INPUT_PULLUP);
    pinMode(PIN_BTN_CAND_4, INPUT_PULLUP);
    pinMode(PIN_BTN_CONFIRM, INPUT_PULLUP);
    pinMode(PIN_BTN_ADMIN, INPUT_PULLUP);

    // 2. Initialize Subsystems
    serial_comm_init(9600);
    display_init();
    storage_init();
    tamper_init();
    voting_init();
    auth_init(DEFAULT_ADMIN_PIN);
    fsm_init();

    uint32_t now = millis();

    // 3. Announce Boot over UART
    serial_comm_send_boot(
        storage_get_device_id(),
        storage_get_sequence_counter(),
        storage_get_config_hash()
    );

    // 4. Enter SELF_TEST state
    fsm_transition_to(STATE_SELF_TEST, now);
    display_render_state(STATE_SELF_TEST, now);

    // Self-test checks
    // Check 1: Latch existing tamper state
    if (storage_get_tamper_flag() != 0 || tamper_is_physical_switch_open()) {
        storage_set_tamper_flag(1);
        FSMState state_before_tamper = fsm_get_current_state();
        fsm_trigger_tamper(now);
        display_beep_tamper();
        serial_comm_send_tamper(storage_get_device_id(), storage_get_sequence_counter(), "boot_tamper_check");
        serial_comm_send_state_change(
            storage_get_device_id(),
            storage_get_sequence_counter(),
            state_before_tamper,
            STATE_TAMPER_DETECTED
        );
        return;
    }

    // Check 2: Configuration hash validation
    if (!storage_validate_config_hash(EXPECTED_CONFIG_HASH)) {
        fsm_trigger_error(now);
        return;
    }

    // Check 3: Check persistent pause flag from EEPROM
    if (storage_get_pause_flag() != 0) {
        delay(1200);
        now = millis();
        fsm_transition_to(STATE_PAUSED, now);
        serial_comm_send_state_change(
            storage_get_device_id(),
            storage_get_sequence_counter(),
            STATE_SELF_TEST,
            STATE_PAUSED
        );
        return;
    }

    // Delay briefly to allow self-test screen to be visible
    delay(1200);
    now = millis();

    // 5. Enter READY state
    fsm_transition_to(STATE_READY, now);
    serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_SELF_TEST, STATE_READY);
}

void loop() {
    uint32_t now = millis();

    // -------------------------------------------------------------------------
    // 1. TAMPER SWITCH MONITORING (Highest Priority)
    // -------------------------------------------------------------------------
    if (tamper_poll(now)) {
        FSMState state_before_tamper = fsm_get_current_state();
        if (state_before_tamper != STATE_TAMPER_DETECTED) {
            storage_set_tamper_flag(1);
            fsm_trigger_tamper(now);
            display_beep_tamper();
            serial_comm_send_tamper(
                storage_get_device_id(),
                storage_get_sequence_counter(),
                "enclosure_breached"
            );
            serial_comm_send_state_change(
                storage_get_device_id(),
                storage_get_sequence_counter(),
                state_before_tamper,
                STATE_TAMPER_DETECTED
            );
        }
    }

    // -------------------------------------------------------------------------
    // 2. BUTTON EDGE DETECTION
    // -------------------------------------------------------------------------
    bool cand1_down   = is_button_pressed(&btn_cand1, now);
    bool cand2_down   = is_button_pressed(&btn_cand2, now);
    bool cand3_down   = is_button_pressed(&btn_cand3, now);
    bool cand4_down   = is_button_pressed(&btn_cand4, now);
    bool confirm_down = is_button_pressed(&btn_confirm, now);
    bool admin_down   = is_button_pressed(&btn_admin, now);

    // Admin button hold detection (held for ADMIN_HOLD_DELAY_MS)
    if (digitalRead(PIN_BTN_ADMIN) == LOW) {
        if (admin_press_start_ms == 0) {
            admin_press_start_ms = now;
            admin_hold_triggered = false;
        } else if (!admin_hold_triggered && (now - admin_press_start_ms) >= ADMIN_HOLD_DELAY_MS) {
            admin_hold_triggered = true;
            // Admin hold triggered!
            FSMState cur = fsm_get_current_state();
            if (cur == STATE_READY || cur == STATE_PAUSED || cur == STATE_TAMPER_DETECTED ||
                cur == STATE_ERROR || cur == STATE_VOTING || cur == STATE_CONFIRM) {
                // IN-FLIGHT-BALLOT RULE:
                // If pause is triggered while in VOTING or CONFIRM,
                // the in-progress ballot selection MUST be discarded.
                if (cur == STATE_VOTING || cur == STATE_CONFIRM) {
                    voting_discard_in_flight();
                }
                auth_reset_input();
                fsm_transition_to(STATE_ADMIN_AUTH, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), cur, STATE_ADMIN_AUTH);
            }
        }
    } else {
        admin_press_start_ms = 0;
        admin_hold_triggered = false;
    }

    // -------------------------------------------------------------------------
    // 3. FINITE STATE MACHINE EVENT PROCESSING
    // -------------------------------------------------------------------------
    FSMState cur_state = fsm_get_current_state();

    switch (cur_state) {
        case STATE_READY:
            if (cand1_down) {
                voting_select_candidate(0, now);
                fsm_transition_to(STATE_VOTING, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_READY, STATE_VOTING);
            } else if (cand2_down) {
                voting_select_candidate(1, now);
                fsm_transition_to(STATE_VOTING, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_READY, STATE_VOTING);
            } else if (cand3_down) {
                voting_select_candidate(2, now);
                fsm_transition_to(STATE_VOTING, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_READY, STATE_VOTING);
            } else if (cand4_down) {
                voting_select_candidate(3, now);
                fsm_transition_to(STATE_VOTING, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_READY, STATE_VOTING);
            }
            break;

        case STATE_VOTING:
            // Check idle timeout (30 seconds)
            if (voting_is_idle_timeout(now)) {
                voting_reset_session();
                fsm_transition_to(STATE_READY, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_VOTING, STATE_READY);
                break;
            }

            // Change selection
            if (cand1_down) voting_select_candidate(0, now);
            else if (cand2_down) voting_select_candidate(1, now);
            else if (cand3_down) voting_select_candidate(2, now);
            else if (cand4_down) voting_select_candidate(3, now);

            // Confirm selection
            if (confirm_down && voting_get_selected_candidate() >= 0) {
                voting_handle_confirm(now);
                fsm_transition_to(STATE_CONFIRM, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_VOTING, STATE_CONFIRM);
            }
            break;

        case STATE_CONFIRM:
            // Check idle timeout (30 seconds)
            if (voting_is_idle_timeout(now)) {
                voting_reset_session();
                fsm_transition_to(STATE_READY, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_CONFIRM, STATE_READY);
                break;
            }

            // Button 1: Go back to re-select
            if (cand1_down) {
                fsm_transition_to(STATE_VOTING, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_CONFIRM, STATE_VOTING);
            }
            // Confirm: Cast ballot
            else if (confirm_down) {
                fsm_transition_to(STATE_VOTE_SUBMISSION, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_CONFIRM, STATE_VOTE_SUBMISSION);
            }
            break;

        case STATE_VOTE_SUBMISSION: {
            int cand = voting_get_selected_candidate();
            const char* cand_id = (cand >= 0 && cand < NUM_CANDIDATES) ? CANDIDATES[cand].id : "C001";

            // Monotonically increment sequence counter in EEPROM (Replay protection)
            uint32_t new_seq = storage_increment_sequence_counter();

            // Broadcast vote record over UART
            serial_comm_send_vote(storage_get_device_id(), cand_id, new_seq, "simulated_session_token");

            display_beep_vote();
            fsm_transition_to(STATE_AUDIT_COMMIT, now);
            break;
        }

        case STATE_AUDIT_COMMIT:
            if (fsm_get_state_duration_ms(now) >= 400) {
                fsm_transition_to(STATE_VOTE_COMPLETE, now);
            }
            break;

        case STATE_VOTE_COMPLETE:
            if (fsm_get_state_duration_ms(now) >= 1500) {
                voting_reset_session();
                fsm_transition_to(STATE_READY, now);
                serial_comm_send_state_change(storage_get_device_id(), storage_get_sequence_counter(), STATE_VOTE_COMPLETE, STATE_READY);
            }
            break;

        case STATE_ADMIN_AUTH:
            // Cand 1 button: increment current digit (0..9)
            if (cand1_down) {
                auth_increment_digit();
            }
            // Confirm or Admin button click: advance digit or submit PIN
            else if (confirm_down || (admin_down && !admin_hold_triggered)) {
                if (auth_advance_digit()) {
                    // All 4 digits entered -> verify PIN
                    if (auth_verify_pin()) {
                        FSMState prev = fsm_get_previous_state();
                        if (prev == STATE_TAMPER_DETECTED || prev == STATE_ERROR) {
                            // Tamper / Error Recovery Path: requires closed switch + valid config hash
                            if (!tamper_is_physical_switch_open()) {
                                storage_clear_tamper_flag();
                                bool valid_config = storage_validate_config_hash(EXPECTED_CONFIG_HASH);
                                fsm_execute_recovery(valid_config, now);
                                serial_comm_send_state_change(
                                    storage_get_device_id(),
                                    storage_get_sequence_counter(),
                                    STATE_ADMIN_AUTH,
                                    fsm_get_current_state()
                                );
                            } else {
                                // Enclosure still open -> remain in TAMPER_DETECTED
                                fsm_trigger_tamper(now);
                                serial_comm_send_state_change(
                                    storage_get_device_id(),
                                    storage_get_sequence_counter(),
                                    STATE_ADMIN_AUTH,
                                    STATE_TAMPER_DETECTED
                                );
                            }
                        } else if (prev == STATE_PAUSED) {
                            // Unpause Path: PAUSED -> ADMIN_AUTH -> READY
                            storage_set_pause_flag(0);
                            fsm_transition_to(STATE_READY, now);
                            serial_comm_send_state_change(
                                storage_get_device_id(),
                                storage_get_sequence_counter(),
                                STATE_ADMIN_AUTH,
                                STATE_READY
                            );
                        } else {
                            // Pause Path: READY / VOTING / CONFIRM -> ADMIN_AUTH -> PAUSED
                            storage_set_pause_flag(1);
                            fsm_transition_to(STATE_PAUSED, now);
                            serial_comm_send_state_change(
                                storage_get_device_id(),
                                storage_get_sequence_counter(),
                                STATE_ADMIN_AUTH,
                                STATE_PAUSED
                            );
                        }
                    } else {
                        // Wrong PIN: beep alert and retry
                        display_beep_tamper();
                    }
                }
            }
            break;

        case STATE_PAUSED:
            // In PAUSED state, any vote-related buttons are rejected
            if (cand1_down || cand2_down || cand3_down || cand4_down || confirm_down) {
                display_beep_tamper();
            }
            break;

        case STATE_TAMPER_DETECTED:
        case STATE_ERROR:
            // In locked states, only the admin hold button sequence can initiate authentication
            break;

        default:
            break;
    }

    // -------------------------------------------------------------------------
    // 4. DISPLAY & INDICATORS REFRESH
    // -------------------------------------------------------------------------
    display_render_state(cur_state, now);
    display_update_indicators(cur_state, now);

    // -------------------------------------------------------------------------
    // 5. SERIAL COMMUNICATION & HEARTBEAT
    // -------------------------------------------------------------------------
    serial_comm_poll();

    if ((now - last_heartbeat_ms) >= HEARTBEAT_INTERVAL_MS) {
        last_heartbeat_ms = now;
        serial_comm_send_heartbeat(
            storage_get_device_id(),
            storage_get_sequence_counter(),
            cur_state
        );
    }
}
