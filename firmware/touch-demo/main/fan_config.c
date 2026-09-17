#include "fan_config.h"

#include <string.h>

#include "esp_log.h"
#include "nvs.h"

static const char *TAG = "fan_config";

#define FAN_NVS_NAMESPACE "fanctl"

void fan_config_defaults(fan_config_t *cfg)
{
    cfg->bounds_c[0] = 45;
    cfg->bounds_c[1] = 55;
    cfg->bounds_c[2] = 65;
    cfg->bounds_c[3] = 85;
    cfg->ref_rpm[0] = 1500;
    cfg->ref_rpm[1] = 1500;
}

bool fan_config_valid(const fan_config_t *cfg)
{
    for (unsigned i = 0; i < FAN_STAGE_COUNT; i++) {
        if (cfg->bounds_c[i] < FAN_BOUND_MIN_C || cfg->bounds_c[i] > FAN_BOUND_MAX_C) {
            return false;
        }
        if (i > 0 && cfg->bounds_c[i] <= cfg->bounds_c[i - 1]) {
            return false;
        }
    }
    for (unsigned i = 0; i < 2; i++) {
        if (cfg->ref_rpm[i] < FAN_REF_RPM_MIN || cfg->ref_rpm[i] > FAN_REF_RPM_MAX) {
            return false;
        }
    }
    return true;
}

bool fan_config_load(fan_config_t *cfg)
{
    fan_config_defaults(cfg);
    nvs_handle_t handle;
    esp_err_t err = nvs_open(FAN_NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        return false;
    }
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "nvs open failed: %s", esp_err_to_name(err));
        return false;
    }
    bool stored = false;
    char key[3] = "b0";
    for (unsigned i = 0; i < FAN_STAGE_COUNT; i++) {
        uint8_t value = cfg->bounds_c[i];
        key[1] = (char)('0' + i);
        if (nvs_get_u8(handle, key, &value) == ESP_OK) {
            cfg->bounds_c[i] = value;
            stored = true;
        }
    }
    for (unsigned i = 0; i < 2; i++) {
        uint16_t value = cfg->ref_rpm[i];
        key[1] = (char)('0' + i);
        if (nvs_get_u16(handle, key, &value) == ESP_OK) {
            cfg->ref_rpm[i] = value;
            stored = true;
        }
    }
    nvs_close(handle);
    if (!fan_config_valid(cfg)) {
        ESP_LOGW(TAG, "stored config invalid, using defaults");
        fan_config_defaults(cfg);
        return false;
    }
    return stored;
}

bool fan_config_save(const fan_config_t *cfg)
{
    if (!fan_config_valid(cfg)) {
        return false;
    }
    nvs_handle_t handle;
    esp_err_t err = nvs_open(FAN_NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "nvs open for write failed: %s", esp_err_to_name(err));
        return false;
    }
    char key[3] = "b0";
    for (unsigned i = 0; i < FAN_STAGE_COUNT; i++) {
        key[1] = (char)('0' + i);
        err = nvs_set_u8(handle, key, cfg->bounds_c[i]);
        if (err != ESP_OK) {
            break;
        }
    }
    for (unsigned i = 0; i < 2 && err == ESP_OK; i++) {
        key[1] = (char)('0' + i);
        err = nvs_set_u16(handle, key, cfg->ref_rpm[i]);
    }
    if (err == ESP_OK) {
        err = nvs_commit(handle);
    }
    nvs_close(handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "nvs save failed: %s", esp_err_to_name(err));
        return false;
    }
    return true;
}
