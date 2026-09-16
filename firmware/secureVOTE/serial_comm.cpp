#include "serial_comm.h"
#include <stdio.h>
#include <string.h>

#ifdef ARDUINO
#include <Arduino.h>
#endif

void serial_comm_init(long baud_rate) {
#ifdef ARDUINO
    Serial.begin(baud_rate);
#endif
}

void serial_comm_send_boot(const char* device_id, uint32_t seq, const char* config_hash) {
#ifdef ARDUINO
    Serial.print(F("{\"type\":\"BOOT\",\"device_id\":\""));
    Serial.print(device_id ? device_id : "UNKNOWN");
    Serial.print(F("\",\"sequence_number\":"));
    Serial.print(seq);
    Serial.print(F(",\"config_hash\":\""));
    Serial.print(config_hash ? config_hash : "");
    Serial.println(F("\"}"));
#endif
}

void serial_comm_send_state_change(const char* device_id, uint32_t seq, FSMState from, FSMState to) {
#ifdef ARDUINO
    Serial.print(F("{\"type\":\"STATE_CHANGE\",\"device_id\":\""));
    Serial.print(device_id ? device_id : "UNKNOWN");
    Serial.print(F("\",\"sequence_number\":"));
    Serial.print(seq);
    Serial.print(F(",\"from_state\":\""));
    Serial.print(fsm_state_name(from));
    Serial.print(F("\",\"to_state\":\""));
    Serial.print(fsm_state_name(to));
    Serial.println(F("\"}"));
#endif
}

void serial_comm_send_vote(const char* device_id, const char* candidate_id, uint32_t seq, const char* session_token) {
#ifdef ARDUINO
    Serial.print(F("{\"type\":\"VOTE\",\"device_id\":\""));
    Serial.print(device_id ? device_id : "UNKNOWN");
    Serial.print(F("\",\"candidate_id\":\""));
    Serial.print(candidate_id ? candidate_id : "NONE");
    Serial.print(F("\",\"sequence_number\":"));
    Serial.print(seq);
    Serial.print(F(",\"session_token\":\""));
    Serial.print(session_token ? session_token : "");
    Serial.println(F("\"}"));
#endif
}

void serial_comm_send_tamper(const char* device_id, uint32_t seq, const char* reason) {
#ifdef ARDUINO
    Serial.print(F("{\"type\":\"TAMPER\",\"device_id\":\""));
    Serial.print(device_id ? device_id : "UNKNOWN");
    Serial.print(F("\",\"sequence_number\":"));
    Serial.print(seq);
    Serial.print(F(",\"details\":\""));
    Serial.print(reason ? reason : "tamper_switch_triggered");
    Serial.println(F("\"}"));
#endif
}

void serial_comm_send_heartbeat(const char* device_id, uint32_t seq, FSMState state) {
#ifdef ARDUINO
    Serial.print(F("{\"type\":\"HEARTBEAT\",\"device_id\":\""));
    Serial.print(device_id ? device_id : "UNKNOWN");
    Serial.print(F("\",\"sequence_number\":"));
    Serial.print(seq);
    Serial.print(F(",\"state\":\""));
    Serial.print(fsm_state_name(state));
    Serial.println(F("\"}"));
#endif
}

void serial_comm_poll(void) {
#ifdef ARDUINO
    if (Serial.available() > 0) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.indexOf(F("\"cmd\":\"PING\"")) >= 0 || line.indexOf(F("PING")) >= 0) {
            Serial.println(F("{\"type\":\"PONG\"}"));
        }
    }
#endif
}
