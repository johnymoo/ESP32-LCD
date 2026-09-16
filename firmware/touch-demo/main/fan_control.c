#include "fan_control.h"

#include <string.h>

#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#define FAN_PWM_GPIO GPIO_NUM_1
#define FAN_TACH1_GPIO GPIO_NUM_2
#define FAN_TACH2_GPIO GPIO_NUM_4
#define FAN_PWM_FREQ_HZ 25000
#define FAN_PWM_RESOLUTION LEDC_TIMER_10_BIT
#define FAN_PWM_MAX_DUTY ((1U << 10) - 1U)
#define FAN_PULSES_PER_REV 2U

static const uint8_t k_stage_level[FAN_STAGE_COUNT] = {0, 35, 65, 100};

#define FAN_KICK_MS 1000
#define FAN_TICK_MS 250
#define FAN_TACH_WINDOWS_PER_TICK 4
#define FAN_TACH_FAIL_STREAK 3
#define FAN_STAGE_VOTES 2
#define FAN_SAMPLE_STALE_S 10

static const char *TAG = "fan_control";

static SemaphoreHandle_t s_lock;
static fan_config_t s_config;
static fan_mode_t s_mode = FAN_MODE_AUTO;
static uint8_t s_stage;
static fan_fault_t s_fault;
static bool s_wifi_up = true;
static int s_head_c;
static int s_worker_c;
static bool s_temps_valid;
static bool s_had_valid_sample;
static int64_t s_last_valid_us;
static uint8_t s_candidate;
static uint8_t s_candidate_votes;
static int64_t s_kick_until_us;
static volatile uint32_t s_tach_pulses[2];
static uint32_t s_tach_prev[2];
static int64_t s_tach_window_us;
static uint8_t s_tach_zero_streak[2];
static bool s_tach_ok[2] = {true, true};
static uint32_t s_rpm[2];
static portMUX_TYPE s_tach_mux = portMUX_INITIALIZER_UNLOCKED;

static void IRAM_ATTR fan_tach_isr(void *argument)
{
    const gpio_num_t gpio = (gpio_num_t)(intptr_t)argument;
    portENTER_CRITICAL_ISR(&s_tach_mux);
    s_tach_pulses[gpio == FAN_TACH1_GPIO ? 0 : 1]++;
    portEXIT_CRITICAL_ISR(&s_tach_mux);
}

/* The carrier inverts the PWM sense: GPIO1 high turns Q1 on and pulls the fan
 * PWM line low, so the effective fan duty is 100 minus the GPIO1 duty. */
static void fan_apply_level(uint8_t level)
{
    const uint32_t gpio_duty = (uint32_t)(FAN_PWM_MAX_DUTY * (100u - level)) / 100U;
    ESP_ERROR_CHECK(ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, gpio_duty));
    ESP_ERROR_CHECK(ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0));
}

static uint8_t stage_for_temp(int temp_c)
{
    for (unsigned i = 0; i < FAN_STAGE_COUNT; i++) {
        if (temp_c <= (int)s_config.bounds_c[i]) {
            return (uint8_t)i;
        }
    }
    return FAN_STAGE_COUNT - 1;
}

static uint8_t effective_stage(void)
{
    return s_fault != FAN_FAULT_NONE ? FAN_STAGE_COUNT - 1 : s_stage;
}

static void enter_stage(uint8_t stage)
{
    if (stage > 0 && k_stage_level[s_stage] == 0) {
        s_kick_until_us = esp_timer_get_time() + FAN_KICK_MS * 1000LL;
        ESP_LOGI(TAG, "kick-start before stage %u", stage);
    }
    s_stage = stage;
}

static void recompute_fault(void)
{
    const int64_t now_us = esp_timer_get_time();
    const fan_fault_t previous = s_fault;
    if (!s_wifi_up) {
        s_fault = FAN_FAULT_WIFI_DOWN;
    } else if (s_had_valid_sample &&
               now_us - s_last_valid_us > FAN_SAMPLE_STALE_S * 1000000LL) {
        s_fault = FAN_FAULT_ENDPOINT_TIMEOUT;
    } else if (s_temps_valid) {
        s_fault = FAN_FAULT_NONE;
    } else {
        s_fault = FAN_FAULT_TEMP_INVALID;
    }
    if (s_fault != previous) {
        static const char *names[] = {"none", "temp-invalid", "endpoint-timeout",
                                      "wifi-down"};
        if (s_fault == FAN_FAULT_NONE) {
            ESP_LOGI(TAG, "fault cleared, resume %s", s_mode == FAN_MODE_AUTO ? "auto" : "manual");
        } else {
            ESP_LOGW(TAG, "fault %s, fans forced to full speed", names[s_fault]);
        }
    }
}

void fan_control_on_sample(int head_temp_c, int worker_temp_c, bool temps_valid)
{
    if (xSemaphoreTake(s_lock, pdMS_TO_TICKS(1000)) != pdTRUE) {
        return;
    }
    s_head_c = head_temp_c;
    s_worker_c = worker_temp_c;
    s_temps_valid = temps_valid;
    if (temps_valid) {
        s_last_valid_us = esp_timer_get_time();
        if (s_mode == FAN_MODE_AUTO) {
            const int ctrl = head_temp_c > worker_temp_c ? head_temp_c : worker_temp_c;
            uint8_t candidate = stage_for_temp(ctrl);
            if (candidate < s_stage &&
                ctrl >= (int)s_config.bounds_c[candidate] - FAN_HYSTERESIS_C) {
                candidate = s_stage;
            }
            if (!s_had_valid_sample) {
                s_candidate = candidate;
                s_candidate_votes = 0;
                s_stage = candidate;
                ESP_LOGI(TAG, "initial stage %u (ctrl %dC)", candidate, ctrl);
            } else if (candidate != s_candidate) {
                s_candidate = candidate;
                s_candidate_votes = 1;
            } else if (candidate != s_stage) {
                s_candidate_votes++;
                if (s_candidate_votes >= FAN_STAGE_VOTES) {
                    ESP_LOGI(TAG, "stage %u -> %u (ctrl %dC)", s_stage, candidate, ctrl);
                    enter_stage(candidate);
                }
            } else {
                s_candidate_votes = 0;
            }
        }
        s_had_valid_sample = true;
    }
    recompute_fault();
    xSemaphoreGive(s_lock);
}

void fan_control_sample_lost(void)
{
    if (xSemaphoreTake(s_lock, pdMS_TO_TICKS(1000)) != pdTRUE) {
        return;
    }
    s_temps_valid = false;
    s_candidate_votes = 0;
    recompute_fault();
    xSemaphoreGive(s_lock);
}

void fan_control_set_wifi(bool up)
{
    if (xSemaphoreTake(s_lock, pdMS_TO_TICKS(1000)) != pdTRUE) {
        return;
    }
    s_wifi_up = up;
    recompute_fault();
    xSemaphoreGive(s_lock);
}

void fan_control_set_mode(fan_mode_t mode)
{
    if (xSemaphoreTake(s_lock, pdMS_TO_TICKS(1000)) != pdTRUE) {
        return;
    }
    if (s_mode == mode) {
        xSemaphoreGive(s_lock);
        return;
    }
    s_mode = mode;
    if (mode == FAN_MODE_AUTO && s_temps_valid) {
        const int ctrl = s_head_c > s_worker_c ? s_head_c : s_worker_c;
        enter_stage(stage_for_temp(ctrl));
    }
    ESP_LOGI(TAG, "mode %s", mode == FAN_MODE_AUTO ? "auto" : "manual");
    xSemaphoreGive(s_lock);
}

bool fan_control_set_manual_stage(uint8_t stage)
{
    if (stage >= FAN_STAGE_COUNT) {
        return false;
    }
    if (xSemaphoreTake(s_lock, pdMS_TO_TICKS(1000)) != pdTRUE) {
        return false;
    }
    s_mode = FAN_MODE_MANUAL;
    if (stage != s_stage) {
        enter_stage(stage);
    }
    ESP_LOGI(TAG, "manual stage %u", stage);
    xSemaphoreGive(s_lock);
    return true;
}

bool fan_control_apply_config(const fan_config_t *cfg)
{
    if (!fan_config_valid(cfg) || !fan_config_save(cfg)) {
        return false;
    }
    if (xSemaphoreTake(s_lock, pdMS_TO_TICKS(1000)) != pdTRUE) {
        return false;
    }
    s_config = *cfg;
    if (s_mode == FAN_MODE_AUTO && s_temps_valid) {
        const int ctrl = s_head_c > s_worker_c ? s_head_c : s_worker_c;
        enter_stage(stage_for_temp(ctrl));
    }
    xSemaphoreGive(s_lock);
    ESP_LOGI(TAG, "config applied and stored");
    return true;
}

void fan_control_get_status(fan_status_t *status)
{
    if (xSemaphoreTake(s_lock, pdMS_TO_TICKS(1000)) != pdTRUE) {
        return;
    }
    const int64_t now_us = esp_timer_get_time();
    const bool kick = now_us < s_kick_until_us;
    status->mode = s_mode;
    status->stage = effective_stage();
    status->level = kick ? 100 : k_stage_level[status->stage];
    status->ctrl_temp_c = s_head_c > s_worker_c ? s_head_c : s_worker_c;
    status->temps_valid = s_temps_valid;
    status->rpm[0] = s_rpm[0];
    status->rpm[1] = s_rpm[1];
    status->tach_ok[0] = s_tach_ok[0];
    status->tach_ok[1] = s_tach_ok[1];
    status->kick_active = kick;
    status->fault = s_fault;
    xSemaphoreGive(s_lock);
}

void fan_control_get_config(fan_config_t *cfg)
{
    if (xSemaphoreTake(s_lock, pdMS_TO_TICKS(1000)) != pdTRUE) {
        return;
    }
    *cfg = s_config;
    xSemaphoreGive(s_lock);
}

static void fan_tach_window(void)
{
    uint32_t pulses[2];
    portENTER_CRITICAL(&s_tach_mux);
    pulses[0] = s_tach_pulses[0];
    pulses[1] = s_tach_pulses[1];
    const int64_t now_us = esp_timer_get_time();
    const int64_t elapsed_us = now_us - s_tach_window_us;
    s_tach_window_us = now_us;
    portEXIT_CRITICAL(&s_tach_mux);

    if (xSemaphoreTake(s_lock, 0) != pdTRUE) {
        return;
    }
    const bool motors_expected = k_stage_level[effective_stage()] > 0 ||
                                 esp_timer_get_time() < s_kick_until_us;
    for (unsigned i = 0; i < 2; i++) {
        const uint32_t delta = pulses[i] - s_tach_prev[i];
        s_tach_prev[i] = pulses[i];
        s_rpm[i] = (uint32_t)(((uint64_t)delta * 60000000ULL) /
                              ((uint64_t)elapsed_us * FAN_PULSES_PER_REV));
        if (motors_expected) {
            if (delta == 0) {
                if (s_tach_zero_streak[i] < UINT8_MAX) {
                    s_tach_zero_streak[i]++;
                }
                if (s_tach_zero_streak[i] >= FAN_TACH_FAIL_STREAK) {
                    s_tach_ok[i] = false;
                }
            } else {
                s_tach_zero_streak[i] = 0;
                s_tach_ok[i] = true;
            }
        } else {
            s_tach_zero_streak[i] = 0;
            s_tach_ok[i] = true;
        }
    }
    xSemaphoreGive(s_lock);
}

static void fan_control_task(void *argument)
{
    unsigned tick = 0;
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(FAN_TICK_MS));
        if (++tick >= FAN_TACH_WINDOWS_PER_TICK) {
            tick = 0;
            fan_tach_window();
        }
        if (xSemaphoreTake(s_lock, pdMS_TO_TICKS(1000)) != pdTRUE) {
            continue;
        }
        const bool kick = esp_timer_get_time() < s_kick_until_us;
        fan_apply_level(kick ? 100 : k_stage_level[effective_stage()]);
        xSemaphoreGive(s_lock);
    }
}

void fan_control_init(void)
{
    fan_config_load(&s_config);

    const ledc_timer_config_t timer_config = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_num = LEDC_TIMER_0,
        .duty_resolution = FAN_PWM_RESOLUTION,
        .freq_hz = FAN_PWM_FREQ_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer_config));

    const ledc_channel_config_t channel_config = {
        .gpio_num = FAN_PWM_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0,
        .intr_type = LEDC_INTR_DISABLE,
        .timer_sel = LEDC_TIMER_0,
        .duty = 0,
        .hpoint = 0,
        .flags = {.output_invert = 0},
    };
    ESP_ERROR_CHECK(ledc_channel_config(&channel_config));

    const gpio_config_t tach_config = {
        .pin_bit_mask = (1ULL << FAN_TACH1_GPIO) | (1ULL << FAN_TACH2_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    ESP_ERROR_CHECK(gpio_config(&tach_config));
    ESP_ERROR_CHECK(gpio_install_isr_service(ESP_INTR_FLAG_IRAM));
    ESP_ERROR_CHECK(gpio_isr_handler_add(FAN_TACH1_GPIO, fan_tach_isr,
                                         (void *)(intptr_t)FAN_TACH1_GPIO));
    ESP_ERROR_CHECK(gpio_isr_handler_add(FAN_TACH2_GPIO, fan_tach_isr,
                                         (void *)(intptr_t)FAN_TACH2_GPIO));

    s_lock = xSemaphoreCreateMutex();
    s_tach_window_us = esp_timer_get_time();
    /* Fail safe: request full speed until the first control decision. */
    fan_apply_level(100);
    xTaskCreate(fan_control_task, "fan_control", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "ready: PWM=GPIO1 25kHz shared, TACH1=GPIO2, TACH2=GPIO4, "
                  "bounds %u/%u/%u/%u C, refs %u/%u RPM",
             s_config.bounds_c[0], s_config.bounds_c[1], s_config.bounds_c[2],
             s_config.bounds_c[3], s_config.ref_rpm[0], s_config.ref_rpm[1]);
}
