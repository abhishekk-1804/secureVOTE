#ifndef SECUREVOTE_SERIAL_COMM_H
#define SECUREVOTE_SERIAL_COMM_H

#include <stdint.h>
#include <stdbool.h>
#include "state_machine.h"

// Initialize hardware UART serial port (9600 baud)
void serial_comm_init(long baud_rate);

// Broadcast boot announcement JSON message
void serial_comm_send_boot(const char* device_id, uint32_t seq, const char* config_hash);

// Broadcast state change JSON message
void serial_comm_send_state_change(const char* device_id, uint32_t seq, FSMState from, FSMState to);

// Broadcast cast ballot JSON message
void serial_comm_send_vote(const char* device_id, const char* candidate_id, uint32_t seq, const char* session_token);

// Broadcast tamper alert JSON message
void serial_comm_send_tamper(const char* device_id, uint32_t seq, const char* reason);

// Broadcast periodic heartbeat JSON message
void serial_comm_send_heartbeat(const char* device_id, uint32_t seq, FSMState state);

// Poll for inbound serial commands (non-blocking)
void serial_comm_poll(void);

#endif // SECUREVOTE_SERIAL_COMM_H
