#pragma once

#include <stdbool.h>
#include <stdint.h>

#define FAN_STAGE_COUNT 4
#define FAN_HYSTERESIS_C 3

#define FAN_BOUND_MIN_C 20
#define FAN_BOUND_MAX_C 95
#define FAN_REF_RPM_MIN 300
#define FAN_REF_RPM_MAX 5000

/* Persisted shared-curve configuration: the upper temperature bound of each
 * stage plus the per-fan full-speed reference used for relative RPM display.
 * Stage duty levels are fixed in firmware, matching the approved prototype. */
typedef struct {
    uint8_t bounds_c[FAN_STAGE_COUNT];
    uint16_t ref_rpm[2];
} fan_config_t;

void fan_config_defaults(fan_config_t *cfg);
bool fan_config_valid(const fan_config_t *cfg);
bool fan_config_load(fan_config_t *cfg);
bool fan_config_save(const fan_config_t *cfg);
