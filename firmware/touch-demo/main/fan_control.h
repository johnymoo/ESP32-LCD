#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "fan_config.h"

typedef enum {
    FAN_FAULT_NONE = 0,
    FAN_FAULT_TEMP_INVALID,
    FAN_FAULT_ENDPOINT_TIMEOUT,
    FAN_FAULT_WIFI_DOWN,
} fan_fault_t;

typedef enum {
    FAN_MODE_AUTO = 0,
    FAN_MODE_MANUAL,
} fan_mode_t;

typedef struct {
    fan_mode_t mode;
    uint8_t stage;
    uint8_t level;
    int ctrl_temp_c;
    bool temps_valid;
    uint32_t rpm[2];
    bool tach_ok[2];
    bool kick_active;
    fan_fault_t fault;
} fan_status_t;

/* Rev B carrier: GPIO1 is the shared inverted open-drain PWM for both fans,
 * GPIO2/GPIO4 are the FAN1/FAN2 tach inputs. */
void fan_control_init(void);
void fan_control_on_sample(int head_temp_c, int worker_temp_c, bool temps_valid);
void fan_control_sample_lost(void);
void fan_control_set_wifi(bool up);
void fan_control_set_mode(fan_mode_t mode);
bool fan_control_set_manual_stage(uint8_t stage);
bool fan_control_apply_config(const fan_config_t *cfg);
void fan_control_get_status(fan_status_t *status);
void fan_control_get_config(fan_config_t *cfg);
