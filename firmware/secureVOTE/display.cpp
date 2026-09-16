#include "display.h"
#include "config.h"
#include "voting.h"
#include "auth.h"
#include "storage.h"

#ifdef ARDUINO
#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

static LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);
#endif

static FSMState last_rendered_state = (FSMState)-1;
static int last_rendered_param = -999;
static uint32_t last_blink_time = 0;
static bool blink_state = false;
static uint32_t buzzer_off_time = 0;

void display_init(void) {
#ifdef ARDUINO
    pinMode(PIN_LED_GREEN, OUTPUT);
    pinMode(PIN_LED_RED, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);

    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_RED, LOW);
    digitalWrite(PIN_BUZZER, LOW);

    Wire.begin();
    lcd.init();
    lcd.backlight();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(F("   SecureVOTE EVM   "));
    lcd.setCursor(0, 1);
    lcd.print(F(" Prototype HW v2.0  "));
    lcd.setCursor(0, 2);
    lcd.print(F("Initializing HW...  "));
    lcd.setCursor(0, 3);
    lcd.print(F("ATmega328P @ 16 MHz "));
#endif
    last_rendered_state = (FSMState)-1;
}

void display_render_state(FSMState state, uint32_t current_time_ms) {
    int current_param = 0;
    if (state == STATE_VOTING || state == STATE_CONFIRM) {
        current_param = voting_get_selected_candidate();
    } else if (state == STATE_ADMIN_AUTH) {
        current_param = auth_get_current_digit_idx() * 100 + auth_get_digit_value(auth_get_current_digit_idx());
    } else if (state == STATE_READY) {
        current_param = (int)storage_get_sequence_counter();
    }

    if (state == last_rendered_state && current_param == last_rendered_param) {
        return; // Avoid LCD redraw flickering
    }

    last_rendered_state = state;
    last_rendered_param = current_param;

#ifdef ARDUINO
    lcd.clear();

    switch (state) {
        case STATE_BOOT:
        case STATE_SELF_TEST:
            lcd.setCursor(0, 0);
            lcd.print(F("=== SELF-TEST ==="));
            lcd.setCursor(0, 1);
            lcd.print(F("EEPROM Storage: OK"));
            lcd.setCursor(0, 2);
            lcd.print(F("Config Hash: Valid"));
            lcd.setCursor(0, 3);
            lcd.print(F("Seq Restored: #"));
            lcd.print(storage_get_sequence_counter());
            break;

        case STATE_READY:
            lcd.setCursor(0, 0);
            lcd.print(F("* SecureVOTE EVM *"));
            lcd.setCursor(0, 1);
            lcd.print(F("Unit: "));
            lcd.print(storage_get_device_id());
            lcd.print(F(" Seq:#"));
            lcd.print(storage_get_sequence_counter());
            lcd.setCursor(0, 2);
            lcd.print(F("Press [1-4] to Vote "));
            lcd.setCursor(0, 3);
            lcd.print(F("Hold ADMIN for PIN  "));
            break;

        case STATE_VOTING: {
            int cand = voting_get_selected_candidate();
            lcd.setCursor(0, 0);
            lcd.print(F("BALLOT SELECTION    "));
            if (cand >= 0 && cand < NUM_CANDIDATES) {
                lcd.setCursor(0, 1);
                lcd.print(F("["));
                lcd.print(cand + 1);
                lcd.print(F("] "));
                lcd.print(CANDIDATES[cand].name);
                lcd.setCursor(0, 2);
                lcd.print(F("Party: "));
                lcd.print(CANDIDATES[cand].party);
                lcd.setCursor(0, 3);
                lcd.print(F("Press CONFIRM to Lock"));
            } else {
                lcd.setCursor(0, 1);
                lcd.print(F("1:Alice  2:Bob      "));
                lcd.setCursor(0, 2);
                lcd.print(F("3:Carol  4:David    "));
                lcd.setCursor(0, 3);
                lcd.print(F("Select Candidate... "));
            }
            break;
        }

        case STATE_CONFIRM: {
            int cand = voting_get_selected_candidate();
            lcd.setCursor(0, 0);
            lcd.print(F("CONFIRM YOUR BALLOT:"));
            lcd.setCursor(0, 1);
            if (cand >= 0 && cand < NUM_CANDIDATES) {
                lcd.print(F("> "));
                lcd.print(CANDIDATES[cand].name);
                lcd.setCursor(0, 2);
                lcd.print(F("Sym: ["));
                lcd.print(CANDIDATES[cand].symbol);
                lcd.print(F("] "));
                lcd.print(CANDIDATES[cand].party);
            }
            lcd.setCursor(0, 3);
            lcd.print(F("CONFIRM:Cast 1:Back "));
            break;
        }

        case STATE_VOTE_SUBMISSION:
            lcd.setCursor(0, 0);
            lcd.print(F("RECORDING BALLOT... "));
            lcd.setCursor(0, 1);
            lcd.print(F("Hashing Record...   "));
            lcd.setCursor(0, 2);
            lcd.print(F("Sequence: #"));
            lcd.print(storage_get_sequence_counter());
            lcd.setCursor(0, 3);
            lcd.print(F("Transmitting UART..."));
            break;

        case STATE_AUDIT_COMMIT:
            lcd.setCursor(0, 0);
            lcd.print(F("AUDIT COMMIT...     "));
            lcd.setCursor(0, 1);
            lcd.print(F("Tamper-Evident Chain"));
            lcd.setCursor(0, 2);
            lcd.print(F("Sequence: #"));
            lcd.print(storage_get_sequence_counter());
            lcd.setCursor(0, 3);
            lcd.print(F("EEPROM Monotonic OK "));
            break;

        case STATE_VOTE_COMPLETE:
            lcd.setCursor(0, 0);
            lcd.print(F("********************"));
            lcd.setCursor(0, 1);
            lcd.print(F("*  VOTE RECORDED!  *"));
            lcd.setCursor(0, 2);
            lcd.print(F("* THANK YOU VOTER! *"));
            lcd.setCursor(0, 3);
            lcd.print(F("********************"));
            break;

        case STATE_ADMIN_AUTH: {
            lcd.setCursor(0, 0);
            lcd.print(F("== ADMIN SECURITY =="));
            lcd.setCursor(0, 1);
            lcd.print(F("Enter 4-Digit PIN:  "));
            lcd.setCursor(0, 2);
            lcd.print(F("PIN: [ "));
            for (int i = 0; i < PIN_LENGTH; i++) {
                if (i == auth_get_current_digit_idx()) {
                    lcd.print(auth_get_digit_value(i));
                } else if (i < auth_get_current_digit_idx()) {
                    lcd.print(F("*"));
                } else {
                    lcd.print(F("_"));
                }
                lcd.print(F(" "));
            }
            lcd.print(F("]"));
            lcd.setCursor(0, 3);
            lcd.print(F("1:NextDigit ADMIN:OK"));
            break;
        }

        case STATE_TAMPER_DETECTED:
            lcd.setCursor(0, 0);
            lcd.print(F("!! TAMPER DETECTED!!"));
            lcd.setCursor(0, 1);
            lcd.print(F("VOTING IS LOCKED!   "));
            lcd.setCursor(0, 2);
            lcd.print(F("ENCLOSURE BREACHED  "));
            lcd.setCursor(0, 3);
            lcd.print(F("Admin Auth Required "));
            break;

        case STATE_ERROR:
            lcd.setCursor(0, 0);
            lcd.print(F("!! SYSTEM ERROR !!  "));
            lcd.setCursor(0, 1);
            lcd.print(F("Fault Detected!     "));
            lcd.setCursor(0, 2);
            lcd.print(F("Config Hash Check   "));
            lcd.setCursor(0, 3);
            lcd.print(F("Admin Auth to Reset "));
            break;

        case STATE_PAUSED:
            lcd.setCursor(0, 0);
            lcd.print(F("-- ELECTION PAUSED--"));
            lcd.setCursor(0, 1);
            lcd.print(F("Voting Suspended    "));
            lcd.setCursor(0, 2);
            lcd.print(F("Session Maintained  "));
            lcd.setCursor(0, 3);
            lcd.print(F("Admin Auth to Resume"));
            break;
    }
#endif
}

void display_update_indicators(FSMState state, uint32_t current_time_ms) {
    if ((current_time_ms - last_blink_time) >= BLINK_INTERVAL_MS) {
        last_blink_time = current_time_ms;
        blink_state = !blink_state;
    }

    // Check buzzer turn-off
    if (buzzer_off_time > 0 && current_time_ms >= buzzer_off_time) {
        display_buzzer_off();
    }

#ifdef ARDUINO
    switch (state) {
        case STATE_READY:
            digitalWrite(PIN_LED_GREEN, HIGH);
            digitalWrite(PIN_LED_RED, LOW);
            break;

        case STATE_VOTING:
        case STATE_CONFIRM:
        case STATE_VOTE_SUBMISSION:
        case STATE_AUDIT_COMMIT:
            digitalWrite(PIN_LED_GREEN, blink_state ? HIGH : LOW);
            digitalWrite(PIN_LED_RED, LOW);
            break;

        case STATE_ADMIN_AUTH:
            digitalWrite(PIN_LED_GREEN, LOW);
            digitalWrite(PIN_LED_RED, blink_state ? HIGH : LOW);
            break;

        case STATE_TAMPER_DETECTED:
        case STATE_ERROR:
            digitalWrite(PIN_LED_GREEN, LOW);
            digitalWrite(PIN_LED_RED, HIGH); // Solid Red
            break;

        case STATE_PAUSED:
            digitalWrite(PIN_LED_GREEN, blink_state ? HIGH : LOW);
            digitalWrite(PIN_LED_RED, blink_state ? HIGH : LOW);
            break;

        default:
            digitalWrite(PIN_LED_GREEN, LOW);
            digitalWrite(PIN_LED_RED, LOW);
            break;
    }
#endif
}

void display_beep_vote(void) {
#ifdef ARDUINO
    digitalWrite(PIN_BUZZER, HIGH);
    buzzer_off_time = millis() + BEEP_VOTE_MS;
#endif
}

void display_beep_tamper(void) {
#ifdef ARDUINO
    digitalWrite(PIN_BUZZER, HIGH);
    buzzer_off_time = millis() + BEEP_TAMPER_MS;
#endif
}

void display_buzzer_off(void) {
#ifdef ARDUINO
    digitalWrite(PIN_BUZZER, LOW);
#endif
    buzzer_off_time = 0;
}
