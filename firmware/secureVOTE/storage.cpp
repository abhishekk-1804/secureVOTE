#include "storage.h"
#include "config.h"
#include <string.h>

#ifdef ARDUINO
#include <EEPROM.h>

static uint8_t raw_read(int addr) {
    return EEPROM.read(addr);
}

static void raw_write(int addr, uint8_t val) {
    EEPROM.update(addr, val); // update avoids write wear if value unchanged
}
#else
// Mock EEPROM buffer for native host tests
static uint8_t mock_eeprom[1024] = {0};

static uint8_t raw_read(int addr) {
    if (addr >= 0 && addr < 1024) return mock_eeprom[addr];
    return 0;
}

static void raw_write(int addr, uint8_t val) {
    if (addr >= 0 && addr < 1024) mock_eeprom[addr] = val;
}
#endif

// Cached in-memory values
static uint32_t cached_seq = 0;
static uint8_t cached_tamper = 0;
static uint8_t cached_pause = 0;
static char cached_device_id[16] = {0};
static char cached_config_hash[68] = {0};

static uint16_t read_uint16(int addr) {
    uint8_t low = raw_read(addr);
    uint8_t high = raw_read(addr + 1);
    return (uint16_t)(low | ((uint16_t)high << 8));
}

static void write_uint16(int addr, uint16_t val) {
    raw_write(addr, (uint8_t)(val & 0xFF));
    raw_write(addr + 1, (uint8_t)((val >> 8) & 0xFF));
}

static uint32_t read_uint32(int addr) {
    uint32_t val = 0;
    for (int i = 0; i < 4; i++) {
        val |= ((uint32_t)raw_read(addr + i)) << (i * 8);
    }
    return val;
}

static void write_uint32(int addr, uint32_t val) {
    for (int i = 0; i < 4; i++) {
        raw_write(addr + i, (uint8_t)((val >> (i * 8)) & 0xFF));
    }
}

void storage_format(void) {
    write_uint16(EEPROM_MAGIC_ADDR, EEPROM_MAGIC_VAL);

    // Default device ID
    const char* def_id = DEVICE_ID_STR;
    for (size_t i = 0; i < 8; i++) {
        raw_write(EEPROM_DEVICE_ID_ADDR + i, (i < strlen(def_id)) ? def_id[i] : 0);
    }

    // Sequence counter starts at 0 on clean flash
    write_uint32(EEPROM_SEQ_ADDR, 0);

    // Tamper flag untampered
    raw_write(EEPROM_TAMPER_ADDR, 0);

    // Pause flag unpaused (0 = ready/active)
    raw_write(EEPROM_PAUSE_ADDR, 0);

    // Default expected config hash
    const char* def_hash = EXPECTED_CONFIG_HASH;
    for (size_t i = 0; i < 65; i++) {
        raw_write(EEPROM_CONFIG_HASH_ADDR + i, (i < strlen(def_hash)) ? def_hash[i] : 0);
    }

    // Refresh cache
    cached_seq = 0;
    cached_tamper = 0;
    cached_pause = 0;
    strncpy(cached_device_id, def_id, sizeof(cached_device_id) - 1);
    strncpy(cached_config_hash, def_hash, sizeof(cached_config_hash) - 1);
}

void storage_init(void) {
    uint16_t magic = read_uint16(EEPROM_MAGIC_ADDR);
    if (magic != EEPROM_MAGIC_VAL) {
        // First boot or unformatted EEPROM -> format
        storage_format();
        return;
    }

    // Restore sequence counter from EEPROM (persisted across restarts)
    cached_seq = read_uint32(EEPROM_SEQ_ADDR);

    // Restore tamper latch
    cached_tamper = raw_read(EEPROM_TAMPER_ADDR);

    // Restore pause flag (persisted across restarts)
    cached_pause = raw_read(EEPROM_PAUSE_ADDR);

    // Restore device ID
    for (int i = 0; i < 8; i++) {
        cached_device_id[i] = (char)raw_read(EEPROM_DEVICE_ID_ADDR + i);
    }
    cached_device_id[7] = '\0';

    // Restore configuration hash
    for (int i = 0; i < 64; i++) {
        cached_config_hash[i] = (char)raw_read(EEPROM_CONFIG_HASH_ADDR + i);
    }
    cached_config_hash[64] = '\0';
}

uint32_t storage_get_sequence_counter(void) {
    return cached_seq;
}

uint32_t storage_increment_sequence_counter(void) {
    cached_seq++;
    write_uint32(EEPROM_SEQ_ADDR, cached_seq);
    return cached_seq;
}

uint8_t storage_get_tamper_flag(void) {
    return cached_tamper;
}

void storage_set_tamper_flag(uint8_t flag) {
    cached_tamper = flag;
    raw_write(EEPROM_TAMPER_ADDR, flag);
}

void storage_clear_tamper_flag(void) {
    cached_tamper = 0;
    raw_write(EEPROM_TAMPER_ADDR, 0);
}

uint8_t storage_get_pause_flag(void) {
    return cached_pause;
}

void storage_set_pause_flag(uint8_t flag) {
    cached_pause = flag;
    raw_write(EEPROM_PAUSE_ADDR, flag);
}

const char* storage_get_device_id(void) {
    return cached_device_id;
}

void storage_set_device_id(const char* device_id) {
    if (device_id) {
        strncpy(cached_device_id, device_id, 7);
        cached_device_id[7] = '\0';
        for (int i = 0; i < 8; i++) {
            raw_write(EEPROM_DEVICE_ID_ADDR + i, (uint8_t)cached_device_id[i]);
        }
    }
}

const char* storage_get_config_hash(void) {
    return cached_config_hash;
}

void storage_set_config_hash(const char* hash) {
    if (hash) {
        strncpy(cached_config_hash, hash, 64);
        cached_config_hash[64] = '\0';
        for (int i = 0; i < 64; i++) {
            raw_write(EEPROM_CONFIG_HASH_ADDR + i, (uint8_t)cached_config_hash[i]);
        }
        raw_write(EEPROM_CONFIG_HASH_ADDR + 64, 0);
    }
}

bool storage_validate_config_hash(const char* expected_hash) {
    if (!expected_hash) return false;
    return (strncmp(cached_config_hash, expected_hash, 64) == 0);
}
