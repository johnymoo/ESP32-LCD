#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#include "cJSON.h"
#include "esp_check.h"
#include "esp_err.h"
#include "esp_event.h"
#include "esp_http_client.h"
#include "esp_log.h"
#include "esp_lvgl_port.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "nvs_flash.h"

#include "bsp_display.h"
#include "bsp_i2c.h"
#include "bsp_touch.h"
#include "cluster_config.h"
#include "fan_config.h"
#include "fan_control.h"
#include "wifi_credentials.h"

#define DISPLAY_ROTATION 90
#define LCD_H_RES 320
#define LCD_V_RES 172
#define LCD_DRAW_BUFFER_HEIGHT 40
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT BIT1
#define WIFI_MAX_RETRY 10
#define DEFAULT_PAGE_ROTATION_MS 10000
#define MIN_PAGE_ROTATION_MS 1000
#define MAX_PAGE_ROTATION_MS 300000
#define UI_REFRESH_MS 500

/* Shared palette with the approved high-fidelity mockups. */
#define COLOR_BG 0x091A24
#define COLOR_PANEL 0x172B3A
#define COLOR_BORDER 0x315568
#define COLOR_CYAN 0x7DE2D1
#define COLOR_MUTED 0x8BA8B7
#define COLOR_BRIGHT 0xE6F1F5
#define COLOR_AMBER 0xFFC66D
#define COLOR_RED 0xFF6B6B
#define COLOR_GREEN 0x8EE3A2
#define COLOR_BTN_BG 0x112E3B
#define COLOR_BTN_BORDER 0x315A6A
#define COLOR_ROW_BG 0x102A36
#define COLOR_ROW_BORDER 0x294F5E
#define COLOR_BAR_TRACK 0x254552
#define COLOR_DARK 0x061018
#define COLOR_BANNER_BG 0x3A1720

#define DEGREE_C "\xC2\xB0" "C"
#define DEGREE_SYMBOL "\xC2\xB0"
#define BULLET "\xE2\x80\xA2"
/* U+00B7 is not in the built-in Montserrat charset (it renders as a box);
 * reuse the bullet glyph, which LVGL ships and the UI has used before. */
#define MIDDOT "\xE2\x80\xA2"

typedef enum {
    PAGE_SYSTEM = 0,
    PAGE_MODEL,
    PAGE_FAN,
    PAGE_SETTINGS,
    PAGE_EDIT,
    PAGE_COUNT,
} ui_page_t;

typedef enum {
    EDIT_CURVE = 0,
    EDIT_REF,
} edit_mode_t;

static const char *TAG = "cluster_display";

static const char *k_stage_name[FAN_STAGE_COUNT] = {"STOP", "LOW", "MED", "HIGH"};
static const uint8_t k_stage_level[FAN_STAGE_COUNT] = {0, 35, 65, 100};

static esp_lcd_panel_io_handle_t io_handle;
static esp_lcd_panel_handle_t panel_handle;
static esp_lcd_touch_handle_t touch_handle;
static lv_display_t *display;
static EventGroupHandle_t wifi_events;
static int wifi_retries;
static char wifi_ip[16] = "--";

static lv_obj_t *pages[PAGE_COUNT];
static lv_obj_t *clock_labels[PAGE_COUNT];
static lv_obj_t *host_hero[2];
static lv_obj_t *host_temp_label[2];
static lv_obj_t *host_thr[2];
static lv_obj_t *host_bar[2][6];
static lv_obj_t *host_bar_value[2][6];
static lv_obj_t *host_foot[2];
static lv_obj_t *model_dot;
static lv_obj_t *model_state_label;
static lv_obj_t *model_name_label;
static lv_obj_t *model_hero_label;
static lv_obj_t *model_prompt_label;
static lv_obj_t *model_chip_label[3];
static lv_obj_t *model_ttft_label;
static lv_obj_t *model_p95_label;
static lv_obj_t *model_itl_label;
static lv_obj_t *model_prefix_value;
static lv_obj_t *model_spec_value;
static lv_obj_t *model_kv_label;
static lv_obj_t *model_kv_bar;
static lv_timer_t *page_timer;
static uint32_t page_rotation_ms = DEFAULT_PAGE_ROTATION_MS;
static ui_page_t current_page = PAGE_SYSTEM;

static lv_obj_t *fan_mode_label;
static lv_obj_t *fan_stage_label;
static lv_obj_t *fan_fault_banner;
static lv_obj_t *fan_fault_text;
static lv_obj_t *fan_rpm_value[2];
static lv_obj_t *fan_rpm_bar[2];
static lv_obj_t *fan_pwm_value;
static lv_obj_t *fan_pwm_bar;
static lv_obj_t *fan_tach_label;

static lv_obj_t *settings_tab[FAN_STAGE_COUNT == 4 ? 3 : 3];
static lv_obj_t *settings_curve_values[FAN_STAGE_COUNT];
static lv_obj_t *settings_ref_values[2];
static lv_obj_t *settings_mode_bodies[3];
static lv_obj_t *settings_mode_buttons[FAN_STAGE_COUNT + 1];
static lv_obj_t *mode_live_bar[2];
static lv_obj_t *mode_live_value[2];
static lv_obj_t *settings_toast;
static lv_timer_t *toast_timer;

static edit_mode_t edit_mode;
static uint8_t edit_index;
static int32_t edit_value;
static int32_t edit_min;
static int32_t edit_max;
static lv_obj_t *edit_title_label;
static lv_obj_t *edit_value_label;
static lv_obj_t *edit_left_label;
static lv_obj_t *edit_info_label;
static lv_obj_t *edit_minus_button;
static lv_obj_t *edit_plus_button;

typedef struct {
    char data[4096];
    size_t length;
} http_response_t;

static void refresh_settings_labels(void);

static lv_obj_t *create_panel(lv_obj_t *parent, int x, int y, int width, int height,
                              uint32_t bg, uint32_t border)
{
    lv_obj_t *panel = lv_obj_create(parent);
    lv_obj_set_pos(panel, x, y);
    lv_obj_set_size(panel, width, height);
    lv_obj_set_style_radius(panel, 4, 0);
    lv_obj_set_style_bg_color(panel, lv_color_hex(bg), 0);
    lv_obj_set_style_border_color(panel, lv_color_hex(border), 0);
    lv_obj_set_style_border_width(panel, 1, 0);
    lv_obj_set_style_pad_all(panel, 0, 0);
    lv_obj_clear_flag(panel, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(panel, LV_OBJ_FLAG_CLICKABLE);
    return panel;
}

static lv_obj_t *create_label(lv_obj_t *parent, int x, int y, int width,
                              const lv_font_t *font, uint32_t color,
                              const char *text, lv_text_align_t align)
{
    lv_obj_t *label = lv_label_create(parent);
    lv_obj_set_pos(label, x, y);
    if (width > 0) {
        lv_obj_set_width(label, width);
    }
    lv_obj_set_style_text_font(label, font, 0);
    lv_obj_set_style_text_color(label, lv_color_hex(color), 0);
    lv_label_set_text(label, text);
    if (width > 0) {
        lv_label_set_long_mode(label, LV_LABEL_LONG_CLIP);
        lv_obj_set_style_text_align(label, align, 0);
    }
    return label;
}

static lv_obj_t *create_page(lv_obj_t *screen)
{
    lv_obj_t *page = lv_obj_create(screen);
    lv_obj_set_pos(page, 0, 0);
    lv_obj_set_size(page, LCD_H_RES, LCD_V_RES);
    lv_obj_set_style_radius(page, 0, 0);
    lv_obj_set_style_border_width(page, 0, 0);
    lv_obj_set_style_pad_all(page, 0, 0);
    lv_obj_set_style_bg_color(page, lv_color_hex(COLOR_BG), 0);
    lv_obj_clear_flag(page, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(page, LV_OBJ_FLAG_CLICKABLE);
    return page;
}

static void create_title_band(lv_obj_t *page)
{
    /* Merged title/status band across the top; widgets created after it render
     * on top, and its non-clickable surface lets taps fall through to the page. */
    lv_obj_t *band = create_panel(page, 0, 0, LCD_H_RES, 22, COLOR_PANEL, COLOR_PANEL);
    lv_obj_set_style_border_width(band, 0, 0);
    lv_obj_set_style_radius(band, 0, 0);
}

static void create_title(lv_obj_t *page, const char *text)
{
    create_title_band(page);
    create_label(page, 8, 3, 0, &lv_font_montserrat_16, COLOR_CYAN, text, LV_TEXT_ALIGN_AUTO);
}

static lv_obj_t *create_button(lv_obj_t *parent, int x, int y, int width, int height,
                               const char *text, const lv_font_t *font)
{
    lv_obj_t *button = lv_btn_create(parent);
    lv_obj_set_pos(button, x, y);
    lv_obj_set_size(button, width, height);
    lv_obj_set_style_bg_color(button, lv_color_hex(COLOR_BTN_BG), LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_set_style_border_color(button, lv_color_hex(COLOR_BTN_BORDER), LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_set_style_border_width(button, 1, LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_set_style_radius(button, 3, LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_set_style_shadow_width(button, 0, LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_t *label = lv_label_create(button);
    lv_obj_set_style_text_font(label, font, 0);
    lv_obj_set_style_text_color(label, lv_color_hex(COLOR_MUTED), 0);
    lv_label_set_text(label, text);
    lv_obj_center(label);
    return button;
}

static void set_button_selected(lv_obj_t *button, bool selected)
{
    lv_obj_set_style_bg_color(button, lv_color_hex(selected ? COLOR_CYAN : COLOR_BTN_BG),
                              LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_set_style_border_color(button, lv_color_hex(selected ? COLOR_CYAN : COLOR_BTN_BORDER),
                                  LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_t *label = lv_obj_get_child(button, 0);
    lv_obj_set_style_text_color(label, lv_color_hex(selected ? COLOR_DARK : COLOR_MUTED), 0);
}

static void show_page(ui_page_t page);

static ui_page_t next_status_page(void)
{
    return current_page == PAGE_FAN ? PAGE_SYSTEM : (ui_page_t)(current_page + 1);
}

static void nav_click_event(lv_event_t *event)
{
    if (lv_event_get_code(event) != LV_EVENT_CLICKED) {
        return;
    }
    const intptr_t target = (intptr_t)lv_event_get_user_data(event);
    show_page((ui_page_t)target);
}

static void page_touch_event(lv_event_t *event)
{
    if (lv_event_get_code(event) != LV_EVENT_CLICKED) {
        return;
    }
    show_page(next_status_page());
    if (page_timer != NULL) {
        lv_timer_reset(page_timer);
    }
}

static void show_page(ui_page_t page)
{
    for (unsigned i = 0; i < PAGE_COUNT; i++) {
        lv_obj_add_flag(pages[i], LV_OBJ_FLAG_HIDDEN);
    }
    lv_obj_clear_flag(pages[page], LV_OBJ_FLAG_HIDDEN);
    current_page = page;
    if (page_timer != NULL) {
        if (page <= PAGE_FAN) {
            lv_timer_resume(page_timer);
            lv_timer_reset(page_timer);
        } else {
            lv_timer_pause(page_timer);
        }
    }
}

static void page_timer_event(lv_timer_t *timer)
{
    (void)timer;
    show_page(next_status_page());
}

static void fan_status_refresh(const fan_status_t *status)
{
    char text[96];

    const bool fault = status->fault != FAN_FAULT_NONE;
    if (fault) {
        static const char *reasons[] = {
            "",
            "TEMP INVALID - FANS AT FULL SPEED",
            "STATUS TIMEOUT - FANS AT FULL SPEED",
            "WIFI DOWN - FANS AT FULL SPEED",
        };
        lv_label_set_text(fan_fault_text, reasons[status->fault]);
        lv_obj_clear_flag(fan_fault_banner, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(fan_fault_banner, LV_OBJ_FLAG_HIDDEN);
    }

    snprintf(text, sizeof(text), "MODE %s",
             status->mode == FAN_MODE_MANUAL ? "MANUAL" : "AUTO");
    lv_label_set_text(fan_mode_label, text);
    snprintf(text, sizeof(text), "STAGE %s", k_stage_name[status->stage]);
    lv_label_set_text(fan_stage_label, text);

    fan_config_t config;
    fan_control_get_config(&config);
    for (unsigned i = 0; i < 2; i++) {
        snprintf(text, sizeof(text), "%" PRIu32 " / %u RPM", status->rpm[i],
                 config.ref_rpm[i]);
        lv_label_set_text(fan_rpm_value[i], text);
        uint32_t ratio = status->rpm[i] * 100u / config.ref_rpm[i];
        if (ratio > 100) {
            ratio = 100;
        }
        lv_bar_set_value(fan_rpm_bar[i], (int32_t)ratio, LV_ANIM_OFF);
        lv_bar_set_value(mode_live_bar[i], (int32_t)ratio, LV_ANIM_OFF);
        char live[32];
        snprintf(live, sizeof(live), "%" PRIu32 " / %u RPM", status->rpm[i],
                 config.ref_rpm[i]);
        lv_label_set_text(mode_live_value[i], live);
    }

    lv_bar_set_value(fan_pwm_bar, (int32_t)status->level, LV_ANIM_OFF);
    snprintf(text, sizeof(text), "%u%%", status->level);
    lv_label_set_text(fan_pwm_value, text);

    const bool ok0 = status->tach_ok[0];
    const bool ok1 = status->tach_ok[1];
    if (ok0 == ok1) {
        snprintf(text, sizeof(text), "tach %s", ok0 ? "OK" : "FAIL");
    } else {
        snprintf(text, sizeof(text), "tach %s " MIDDOT " %s",
                 ok0 ? "OK" : "FAIL", ok1 ? "OK" : "FAIL");
    }
    lv_label_set_text(fan_tach_label, text);
    lv_obj_set_style_text_color(fan_tach_label,
                                lv_color_hex(ok0 && ok1 ? COLOR_GREEN : COLOR_RED), 0);

    const bool manual = status->mode == FAN_MODE_MANUAL;
    set_button_selected(settings_mode_buttons[0], !manual);
    for (unsigned i = 0; i < FAN_STAGE_COUNT; i++) {
        set_button_selected(settings_mode_buttons[i + 1], manual && status->stage == i);
    }
}

static void ui_refresh_timer(lv_timer_t *timer)
{
    (void)timer;
    fan_status_t status;
    fan_control_get_status(&status);
    fan_status_refresh(&status);
}

static void toast_timer_event(lv_timer_t *timer)
{
    lv_obj_add_flag((lv_obj_t *)timer->user_data, LV_OBJ_FLAG_HIDDEN);
    lv_timer_del(timer);
    toast_timer = NULL;
}

static void show_toast(const char *text)
{
    lv_label_set_text(settings_toast, text);
    lv_obj_clear_flag(settings_toast, LV_OBJ_FLAG_HIDDEN);
    if (toast_timer != NULL) {
        lv_timer_del(toast_timer);
    }
    toast_timer = lv_timer_create(toast_timer_event, 1500, settings_toast);
}

static void apply_edit_value_label(void)
{
    char text[32];
    if (edit_mode == EDIT_CURVE) {
        snprintf(text, sizeof(text), "%" PRId32 DEGREE_C, edit_value);
    } else {
        snprintf(text, sizeof(text), "%" PRId32, edit_value);
    }
    lv_label_set_text(edit_value_label, text);
}

static void open_edit(edit_mode_t mode, uint8_t index)
{
    fan_config_t config;
    fan_control_get_config(&config);
    char title[40];
    char info[64];
    edit_mode = mode;
    edit_index = index;
    if (mode == EDIT_CURVE) {
        snprintf(title, sizeof(title), "EDIT CURVE %s %s", BULLET, k_stage_name[index]);
        edit_value = config.bounds_c[index];
        edit_min = index == 0 ? FAN_BOUND_MIN_C : config.bounds_c[index - 1] + 1;
        edit_max = index == FAN_STAGE_COUNT - 1 ? FAN_BOUND_MAX_C : config.bounds_c[index + 1] - 1;
        lv_label_set_text(edit_left_label, "UPPER LIMIT");
        snprintf(info, sizeof(info), "Limits must increase " MIDDOT " duty %u%%",
                 k_stage_level[index]);
        lv_label_set_text(edit_info_label, info);
        lv_label_set_text(lv_obj_get_child(edit_minus_button, 0), "-  DOWN (1" DEGREE_C ")");
        lv_label_set_text(lv_obj_get_child(edit_plus_button, 0), "+  UP (1" DEGREE_C ")");
    } else {
        snprintf(title, sizeof(title), "EDIT REF %s FAN%u", BULLET, index + 1u);
        edit_value = config.ref_rpm[index];
        edit_min = FAN_REF_RPM_MIN;
        edit_max = FAN_REF_RPM_MAX;
        lv_label_set_text(edit_left_label, "FULL-SPEED");
        snprintf(info, sizeof(info), "Measured at 100%% PWM " MIDDOT " step 10 RPM");
        lv_label_set_text(edit_info_label, info);
        lv_label_set_text(lv_obj_get_child(edit_minus_button, 0), "-  DOWN (10 RPM)");
        lv_label_set_text(lv_obj_get_child(edit_plus_button, 0), "+  UP (10 RPM)");
    }
    lv_label_set_text(edit_title_label, title);
    apply_edit_value_label();
    show_page(PAGE_EDIT);
}

static void edit_button_event(lv_event_t *event)
{
    const lv_event_code_t code = lv_event_get_code(event);
    if (code != LV_EVENT_CLICKED && code != LV_EVENT_LONG_PRESSED_REPEAT) {
        return;
    }
    const intptr_t delta = (intptr_t)lv_event_get_user_data(event);
    if (delta != 0) {
        const int32_t step = edit_mode == EDIT_CURVE ? 1 : 10;
        edit_value += (int32_t)delta * step;
        if (edit_value < edit_min) {
            edit_value = edit_min;
        }
        if (edit_value > edit_max) {
            edit_value = edit_max;
        }
        apply_edit_value_label();
    }
}

static void edit_cancel_event(lv_event_t *event)
{
    if (lv_event_get_code(event) == LV_EVENT_CLICKED) {
        show_page(PAGE_SETTINGS);
    }
}

static void edit_save_event(lv_event_t *event)
{
    if (lv_event_get_code(event) != LV_EVENT_CLICKED) {
        return;
    }
    fan_config_t config;
    fan_control_get_config(&config);
    if (edit_mode == EDIT_CURVE) {
        config.bounds_c[edit_index] = (uint8_t)edit_value;
    } else {
        config.ref_rpm[edit_index] = (uint16_t)edit_value;
    }
    show_toast(fan_control_apply_config(&config) ? "SAVED" : "SAVE FAILED");
    refresh_settings_labels();
    show_page(PAGE_SETTINGS);
}

static void settings_tab_event(lv_event_t *event)
{
    if (lv_event_get_code(event) != LV_EVENT_CLICKED) {
        return;
    }
    const intptr_t tab = (intptr_t)lv_event_get_user_data(event);
    for (unsigned i = 0; i < 3; i++) {
        set_button_selected(settings_tab[i], i == tab);
        if (i == tab) {
            lv_obj_clear_flag(settings_mode_bodies[i], LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(settings_mode_bodies[i], LV_OBJ_FLAG_HIDDEN);
        }
    }
}

static void curve_row_event(lv_event_t *event)
{
    if (lv_event_get_code(event) == LV_EVENT_CLICKED) {
        open_edit(EDIT_CURVE, (uint8_t)(intptr_t)lv_event_get_user_data(event));
    }
}

static void ref_row_event(lv_event_t *event)
{
    if (lv_event_get_code(event) == LV_EVENT_CLICKED) {
        open_edit(EDIT_REF, (uint8_t)(intptr_t)lv_event_get_user_data(event));
    }
}

static void mode_button_event(lv_event_t *event)
{
    if (lv_event_get_code(event) != LV_EVENT_CLICKED) {
        return;
    }
    const intptr_t index = (intptr_t)lv_event_get_user_data(event);
    if (index == 0) {
        fan_control_set_mode(FAN_MODE_AUTO);
    } else {
        fan_control_set_manual_stage((uint8_t)(index - 1));
    }
}

static void refresh_settings_labels(void)
{
    fan_config_t config;
    fan_control_get_config(&config);
    char text[48];
    for (unsigned i = 0; i < FAN_STAGE_COUNT; i++) {
        snprintf(text, sizeof(text), "<= %u" DEGREE_C " " MIDDOT " %u%%",
                 config.bounds_c[i], k_stage_level[i]);
        lv_label_set_text(settings_curve_values[i], text);
    }
    for (unsigned i = 0; i < 2; i++) {
        snprintf(text, sizeof(text), "REF %u RPM", config.ref_rpm[i]);
        lv_label_set_text(settings_ref_values[i], text);
    }
}

static void create_clock(lv_obj_t *page, ui_page_t index)
{
    clock_labels[index] = create_label(page, 232, 5, 80, &lv_font_montserrat_12,
                                       COLOR_MUTED, "--:--:--", LV_TEXT_ALIGN_RIGHT);
}

static lv_obj_t *create_host_bar(lv_obj_t *parent, int x, int y, int width)
{
    lv_obj_t *bar = lv_bar_create(parent);
    lv_obj_set_pos(bar, x, y);
    lv_obj_set_size(bar, width, 8);
    lv_bar_set_range(bar, 0, 100);
    lv_obj_set_style_bg_opa(bar, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_bg_color(bar, lv_color_hex(COLOR_BAR_TRACK), LV_PART_MAIN);
    lv_obj_set_style_bg_color(bar, lv_color_hex(COLOR_CYAN), LV_PART_INDICATOR);
    lv_obj_set_style_radius(bar, 4, LV_PART_MAIN);
    lv_obj_set_style_radius(bar, 4, LV_PART_INDICATOR);
    lv_bar_set_value(bar, 0, LV_ANIM_OFF);
    return bar;
}

static void create_system_page(lv_obj_t *screen)
{
    static const char *names[2] = {"HEAD", "WORKER"};
    static const char *k_bar_name[6] = {"GPU", "RAM", "DSK", "SOC", "NVM", "CPU"};

    lv_obj_t *page = create_page(screen);
    pages[PAGE_SYSTEM] = page;
    create_title(page, "SYSTEM LOAD");
    create_clock(page, PAGE_SYSTEM);
    lv_obj_add_event_cb(page, page_touch_event, LV_EVENT_CLICKED, NULL);

    for (unsigned i = 0; i < 2; i++) {
        const int x = i == 0 ? 8 : 164;
        lv_obj_t *panel = create_panel(page, x, 28, 148, 142, COLOR_PANEL, COLOR_BORDER);
        create_label(panel, 8, 3, 0, &lv_font_montserrat_12, COLOR_CYAN, names[i],
                     LV_TEXT_ALIGN_AUTO);
        host_thr[i] = create_label(panel, 64, 4, 27, &lv_font_montserrat_12, COLOR_DARK,
                                   "THR", LV_TEXT_ALIGN_CENTER);
        lv_obj_set_style_bg_opa(host_thr[i], LV_OPA_COVER, 0);
        lv_obj_set_style_bg_color(host_thr[i], lv_color_hex(COLOR_AMBER), 0);
        lv_obj_set_style_radius(host_thr[i], 3, 0);
        lv_obj_add_flag(host_thr[i], LV_OBJ_FLAG_HIDDEN);

        host_hero[i] = create_label(panel, 8, 18, 64, &lv_font_montserrat_20, COLOR_BRIGHT,
                                    "--", LV_TEXT_ALIGN_AUTO);
        host_temp_label[i] = create_label(panel, 72, 26, 68, &lv_font_montserrat_12,
                                          COLOR_BRIGHT, "GPU --", LV_TEXT_ALIGN_AUTO);
        for (unsigned j = 0; j < 6; j++) {
            const int y = 44 + (int)j * 13;
            create_label(panel, 8, y, 0, &lv_font_montserrat_12, COLOR_MUTED, k_bar_name[j],
                         LV_TEXT_ALIGN_AUTO);
            host_bar[i][j] = create_host_bar(panel, 40, y + 1, 72);
            host_bar_value[i][j] = create_label(panel, 114, y, 26, &lv_font_montserrat_12,
                                                COLOR_CYAN, "--", LV_TEXT_ALIGN_RIGHT);
        }
        host_foot[i] = create_label(panel, 8, 126, 136, &lv_font_montserrat_12, COLOR_MUTED,
                                    "--", LV_TEXT_ALIGN_AUTO);
    }
}

static lv_obj_t *create_model_chip(lv_obj_t *parent, int x, int y, int width)
{
    lv_obj_t *chip = lv_btn_create(parent);
    lv_obj_set_pos(chip, x, y);
    lv_obj_set_size(chip, width, 18);
    lv_obj_set_style_bg_color(chip, lv_color_hex(COLOR_BAR_TRACK),
                              LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_set_style_border_width(chip, 0, LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_set_style_radius(chip, 3, LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_set_style_shadow_width(chip, 0, LV_PART_MAIN | LV_STATE_DEFAULT);
    lv_obj_t *label = lv_label_create(chip);
    lv_obj_set_style_text_font(label, &lv_font_montserrat_12, 0);
    lv_obj_set_style_text_color(label, lv_color_hex(COLOR_MUTED), 0);
    lv_label_set_text(label, "--");
    lv_obj_center(label);
    return label;
}

static void create_model_page(lv_obj_t *screen)
{
    lv_obj_t *page = create_page(screen);
    pages[PAGE_MODEL] = page;
    create_title(page, "MODEL INFERENCE");
    create_clock(page, PAGE_MODEL);
    lv_obj_add_event_cb(page, page_touch_event, LV_EVENT_CLICKED, NULL);

    lv_obj_t *panel = create_panel(page, 8, 28, 304, 140, COLOR_PANEL, COLOR_BORDER);

    model_dot = create_panel(panel, 8, 8, 8, 8, COLOR_RED, COLOR_RED);
    lv_obj_set_style_radius(model_dot, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_border_width(model_dot, 0, 0);
    model_state_label = create_label(panel, 22, 6, 100, &lv_font_montserrat_12,
                                     COLOR_RED, "MODEL DOWN", LV_TEXT_ALIGN_AUTO);
    model_name_label = create_label(panel, 150, 6, 146, &lv_font_montserrat_12,
                                    COLOR_MUTED, "", LV_TEXT_ALIGN_RIGHT);

    create_label(panel, 8, 26, 0, &lv_font_montserrat_12, COLOR_MUTED, "THROUGHPUT",
                 LV_TEXT_ALIGN_AUTO);
    model_hero_label = create_label(panel, 8, 38, 64, &lv_font_montserrat_24, COLOR_CYAN,
                                    "--", LV_TEXT_ALIGN_AUTO);
    create_label(panel, 74, 46, 0, &lv_font_montserrat_16, COLOR_CYAN, "tok/s",
                 LV_TEXT_ALIGN_AUTO);
    model_prompt_label = create_label(panel, 120, 46, 90, &lv_font_montserrat_12,
                                      COLOR_BRIGHT, "", LV_TEXT_ALIGN_AUTO);
    lv_label_set_recolor(model_prompt_label, true);

    model_chip_label[0] = create_model_chip(panel, 212, 26, 42);
    lv_label_set_text(model_chip_label[0], "run --");
    model_chip_label[1] = create_model_chip(panel, 258, 26, 38);
    lv_label_set_text(model_chip_label[1], "wait --");
    model_chip_label[2] = create_model_chip(panel, 212, 48, 42);
    lv_label_set_text(model_chip_label[2], "pre --");

    create_label(panel, 8, 72, 0, &lv_font_montserrat_12, COLOR_MUTED, "LATENCY",
                 LV_TEXT_ALIGN_AUTO);
    create_label(panel, 8, 86, 0, &lv_font_montserrat_12, COLOR_MUTED, "TTFT",
                 LV_TEXT_ALIGN_AUTO);
    model_ttft_label = create_label(panel, 48, 84, 60, &lv_font_montserrat_16,
                                    COLOR_BRIGHT, "--", LV_TEXT_ALIGN_AUTO);
    create_label(panel, 122, 86, 0, &lv_font_montserrat_12, COLOR_MUTED, "p95",
                 LV_TEXT_ALIGN_AUTO);
    model_p95_label = create_label(panel, 154, 84, 60, &lv_font_montserrat_16,
                                   COLOR_BRIGHT, "--", LV_TEXT_ALIGN_AUTO);
    create_label(panel, 206, 86, 0, &lv_font_montserrat_12, COLOR_MUTED, "ITL",
                 LV_TEXT_ALIGN_AUTO);
    model_itl_label = create_label(panel, 230, 84, 66, &lv_font_montserrat_16,
                                   COLOR_BRIGHT, "--", LV_TEXT_ALIGN_RIGHT);

    create_label(panel, 8, 106, 0, &lv_font_montserrat_12, COLOR_MUTED, "EFFICIENCY",
                 LV_TEXT_ALIGN_AUTO);
    lv_obj_t *prefix_chip = create_panel(panel, 8, 120, 88, 16, COLOR_BAR_TRACK,
                                         COLOR_BAR_TRACK);
    lv_obj_set_style_radius(prefix_chip, 3, 0);
    create_label(prefix_chip, 6, 2, 0, &lv_font_montserrat_12, COLOR_MUTED, "prefix",
                 LV_TEXT_ALIGN_AUTO);
    model_prefix_value = create_label(prefix_chip, 50, 2, 34, &lv_font_montserrat_12,
                                      COLOR_GREEN, "--", LV_TEXT_ALIGN_RIGHT);
    lv_obj_t *spec_chip = create_panel(panel, 96, 120, 88, 16, COLOR_BAR_TRACK,
                                       COLOR_BAR_TRACK);
    lv_obj_set_style_radius(spec_chip, 3, 0);
    create_label(spec_chip, 6, 2, 0, &lv_font_montserrat_12, COLOR_MUTED, "spec",
                 LV_TEXT_ALIGN_AUTO);
    model_spec_value = create_label(spec_chip, 50, 2, 34, &lv_font_montserrat_12,
                                    COLOR_CYAN, "--", LV_TEXT_ALIGN_RIGHT);
    model_kv_label = create_label(panel, 188, 109, 100, &lv_font_montserrat_12, COLOR_AMBER,
                                  "KV --", LV_TEXT_ALIGN_AUTO);
    model_kv_bar = create_host_bar(panel, 188, 124, 100);
    lv_obj_set_style_bg_color(model_kv_bar, lv_color_hex(COLOR_AMBER), LV_PART_INDICATOR);
}

static void create_fan_page(lv_obj_t *screen)
{
    lv_obj_t *page = create_page(screen);
    pages[PAGE_FAN] = page;
    create_title(page, "FAN STATUS");
    create_clock(page, PAGE_FAN);

    /* The gear sits centered in the top row; the rest of the row and the page
     * body stay tap zones that advance the carousel. */
    lv_obj_t *gear = create_button(page, 148, 1, 24, 20, LV_SYMBOL_SETTINGS,
                                   &lv_font_montserrat_16);
    lv_obj_add_event_cb(gear, nav_click_event, LV_EVENT_CLICKED,
                        (void *)(intptr_t)PAGE_SETTINGS);
    lv_obj_add_event_cb(page, page_touch_event, LV_EVENT_CLICKED, NULL);

    lv_obj_t *panel = create_panel(page, 8, 28, 304, 140, COLOR_PANEL, COLOR_BORDER);
    fan_mode_label = create_label(panel, 10, 12, 110, &lv_font_montserrat_12, COLOR_BRIGHT,
                                  "MODE --", LV_TEXT_ALIGN_AUTO);
    lv_label_set_recolor(fan_mode_label, true);
    fan_stage_label = create_label(panel, 130, 12, 110, &lv_font_montserrat_12, COLOR_BRIGHT,
                                   "STAGE --", LV_TEXT_ALIGN_AUTO);
    lv_label_set_recolor(fan_stage_label, true);
    fan_tach_label = create_label(panel, 10, 12, 284, &lv_font_montserrat_12, COLOR_GREEN,
                                  "tach --", LV_TEXT_ALIGN_RIGHT);

    fan_fault_banner = create_panel(page, 8, 28, 304, 20, COLOR_BANNER_BG, COLOR_RED);
    lv_obj_set_style_radius(fan_fault_banner, 3, 0);
    fan_fault_text = create_label(fan_fault_banner, 0, 3, 304, &lv_font_montserrat_12,
                                  COLOR_RED, "", LV_TEXT_ALIGN_CENTER);
    lv_obj_add_flag(fan_fault_banner, LV_OBJ_FLAG_HIDDEN);

    create_label(panel, 10, 40, 0, &lv_font_montserrat_12, COLOR_MUTED, "PWM",
                 LV_TEXT_ALIGN_AUTO);
    fan_pwm_bar = create_host_bar(panel, 50, 42, 208);
    fan_pwm_value = create_label(panel, 262, 40, 32, &lv_font_montserrat_12, COLOR_BRIGHT,
                                 "0%", LV_TEXT_ALIGN_RIGHT);

    for (unsigned i = 0; i < 2; i++) {
        const int y = 68 + (int)i * 30;
        char name[8];
        snprintf(name, sizeof(name), "FAN%u", i + 1u);
        create_label(panel, 10, y, 0, &lv_font_montserrat_12, COLOR_CYAN, name,
                     LV_TEXT_ALIGN_AUTO);
        fan_rpm_bar[i] = create_host_bar(panel, 50, y + 2, 150);
        fan_rpm_value[i] = create_label(panel, 204, y, 90, &lv_font_montserrat_12,
                                        COLOR_BRIGHT, "-- RPM", LV_TEXT_ALIGN_RIGHT);
    }
}

static lv_obj_t *create_settings_body(lv_obj_t *page, bool hidden)
{
    lv_obj_t *body = lv_obj_create(page);
    lv_obj_set_pos(body, 0, 0);
    lv_obj_set_size(body, LCD_H_RES, LCD_V_RES);
    lv_obj_set_style_bg_opa(body, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(body, 0, 0);
    lv_obj_set_style_pad_all(body, 0, 0);
    lv_obj_clear_flag(body, LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE);
    if (hidden) {
        lv_obj_add_flag(body, LV_OBJ_FLAG_HIDDEN);
    }
    return body;
}

static void create_settings_page(lv_obj_t *screen)
{
    lv_obj_t *page = create_page(screen);
    pages[PAGE_SETTINGS] = page;
    create_title(page, "FAN SETTINGS");
    create_clock(page, PAGE_SETTINGS);

    /* Tab bodies are created first so the tab buttons, back button, and toast
     * stack above them in z-order. */
    lv_obj_t *curve_body = create_settings_body(page, false);
    lv_obj_t *calib_body = create_settings_body(page, true);
    lv_obj_t *mode_body = create_settings_body(page, true);
    settings_mode_bodies[0] = curve_body;
    settings_mode_bodies[1] = calib_body;
    settings_mode_bodies[2] = mode_body;

    for (unsigned i = 0; i < FAN_STAGE_COUNT; i++) {
        lv_obj_t *row = create_panel(curve_body, 8, 56 + (int)i * 22, 304, 20, COLOR_ROW_BG,
                                     COLOR_ROW_BORDER);
        lv_obj_set_style_radius(row, 3, 0);
        lv_obj_add_flag(row, LV_OBJ_FLAG_CLICKABLE);
        lv_obj_add_event_cb(row, curve_row_event, LV_EVENT_CLICKED, (void *)(intptr_t)i);
        create_label(row, 8, 4, 0, &lv_font_montserrat_12, COLOR_BRIGHT, k_stage_name[i],
                     LV_TEXT_ALIGN_AUTO);
        settings_curve_values[i] = create_label(row, 100, 4, 196, &lv_font_montserrat_12,
                                                COLOR_CYAN, "", LV_TEXT_ALIGN_RIGHT);
    }
    create_label(curve_body, 8, 150, 304, &lv_font_montserrat_12, COLOR_MUTED,
                 "Tap a stage to edit " MIDDOT " hysteresis 3" DEGREE_C,
                 LV_TEXT_ALIGN_AUTO);

    for (unsigned i = 0; i < 2; i++) {
        lv_obj_t *row = create_panel(calib_body, 8, 60 + (int)i * 30, 304, 24, COLOR_ROW_BG,
                                     COLOR_ROW_BORDER);
        lv_obj_set_style_radius(row, 3, 0);
        lv_obj_add_flag(row, LV_OBJ_FLAG_CLICKABLE);
        lv_obj_add_event_cb(row, ref_row_event, LV_EVENT_CLICKED, (void *)(intptr_t)i);
        char name[24];
        snprintf(name, sizeof(name), "FAN%u FULL-SPEED REF", i + 1u);
        create_label(row, 8, 6, 0, &lv_font_montserrat_12, COLOR_BRIGHT, name,
                     LV_TEXT_ALIGN_AUTO);
        settings_ref_values[i] = create_label(row, 140, 6, 156, &lv_font_montserrat_12,
                                              COLOR_CYAN, "", LV_TEXT_ALIGN_RIGHT);
    }
    create_label(calib_body, 8, 150, 304, &lv_font_montserrat_12, COLOR_MUTED,
                 "Measured at 100% PWM " MIDDOT " tach health only", LV_TEXT_ALIGN_AUTO);

    /* One row of mode buttons: AUTO plus the four manual stages. */
    settings_mode_buttons[0] = create_button(mode_body, 8, 56, 57, 24, "AUTO",
                                             &lv_font_montserrat_12);
    lv_obj_add_event_cb(settings_mode_buttons[0], mode_button_event, LV_EVENT_CLICKED,
                        (void *)0);
    for (unsigned i = 0; i < FAN_STAGE_COUNT; i++) {
        settings_mode_buttons[i + 1] = create_button(mode_body, 8 + (int)(i + 1) * 61, 56,
                                                     57, 24, k_stage_name[i],
                                                     &lv_font_montserrat_12);
        lv_obj_add_event_cb(settings_mode_buttons[i + 1], mode_button_event,
                            LV_EVENT_CLICKED, (void *)(intptr_t)(i + 1));
    }
    for (unsigned i = 0; i < 2; i++) {
        lv_obj_t *row = create_panel(mode_body, 8, 92 + (int)i * 26, 304, 22, COLOR_ROW_BG,
                                     COLOR_ROW_BORDER);
        char name[8];
        snprintf(name, sizeof(name), "FAN%u", i + 1u);
        create_label(row, 12, 5, 0, &lv_font_montserrat_12, COLOR_CYAN, name,
                     LV_TEXT_ALIGN_AUTO);
        mode_live_bar[i] = create_host_bar(row, 52, 7, 110);
        mode_live_value[i] = create_label(row, 194, 5, 102, &lv_font_montserrat_12,
                                          COLOR_BRIGHT, "-- RPM", LV_TEXT_ALIGN_RIGHT);
    }
    create_label(mode_body, 8, 150, 304, &lv_font_montserrat_12, COLOR_MUTED,
                 "Stage tap = MANUAL " MIDDOT " reverts to AUTO on restart",
                 LV_TEXT_ALIGN_AUTO);

    static const char *tabs[3] = {"CURVE", "CALIB", "MODE"};
    for (unsigned i = 0; i < 3; i++) {
        settings_tab[i] = create_button(page, 8 + (int)i * 104, 28, 96, 20, tabs[i],
                                        &lv_font_montserrat_12);
        set_button_selected(settings_tab[i], i == 0);
        lv_obj_add_event_cb(settings_tab[i], settings_tab_event, LV_EVENT_CLICKED,
                            (void *)(intptr_t)i);
    }

    lv_obj_t *back = create_button(page, 164, 1, 60, 20, "BACK", &lv_font_montserrat_12);
    lv_obj_add_event_cb(back, nav_click_event, LV_EVENT_CLICKED, (void *)(intptr_t)PAGE_FAN);

    settings_toast = create_label(page, 0, 78, 320, &lv_font_montserrat_12, COLOR_AMBER,
                                  "", LV_TEXT_ALIGN_CENTER);
    lv_obj_add_flag(settings_toast, LV_OBJ_FLAG_HIDDEN);
}

static void create_edit_page(lv_obj_t *screen)
{
    lv_obj_t *page = create_page(screen);
    pages[PAGE_EDIT] = page;
    create_title_band(page);
    create_clock(page, PAGE_EDIT);
    edit_title_label = create_label(page, 8, 3, 150, &lv_font_montserrat_16, COLOR_CYAN, "",
                                    LV_TEXT_ALIGN_AUTO);
    /* Same placement as the settings BACK: leaving an edit screen never
     * requires reaching the small CANCEL at the panel bottom. */
    lv_obj_t *back = create_button(page, 164, 1, 60, 20, "BACK", &lv_font_montserrat_12);
    lv_obj_add_event_cb(back, edit_cancel_event, LV_EVENT_CLICKED, NULL);

    lv_obj_t *panel = create_panel(page, 8, 28, 304, 140, COLOR_PANEL, COLOR_BORDER);
    edit_left_label = create_label(panel, 0, 10, 304, &lv_font_montserrat_12, COLOR_MUTED,
                                   "", LV_TEXT_ALIGN_CENTER);
    edit_value_label = create_label(panel, 0, 24, 304, &lv_font_montserrat_24, COLOR_BRIGHT,
                                    "", LV_TEXT_ALIGN_CENTER);
    edit_info_label = create_label(panel, 8, 52, 288, &lv_font_montserrat_12, COLOR_MUTED,
                                   "", LV_TEXT_ALIGN_CENTER);
    edit_minus_button = create_button(panel, 8, 68, 142, 30, "-", &lv_font_montserrat_12);
    lv_obj_add_event_cb(edit_minus_button, edit_button_event, LV_EVENT_CLICKED,
                        (void *)(intptr_t)-1);
    lv_obj_add_event_cb(edit_minus_button, edit_button_event, LV_EVENT_LONG_PRESSED_REPEAT,
                        (void *)(intptr_t)-1);
    edit_plus_button = create_button(panel, 154, 68, 142, 30, "+", &lv_font_montserrat_12);
    lv_obj_add_event_cb(edit_plus_button, edit_button_event, LV_EVENT_CLICKED,
                        (void *)(intptr_t)1);
    lv_obj_add_event_cb(edit_plus_button, edit_button_event, LV_EVENT_LONG_PRESSED_REPEAT,
                        (void *)(intptr_t)1);
    lv_obj_t *cancel = create_button(panel, 154, 104, 142, 26, "CANCEL",
                                     &lv_font_montserrat_12);
    lv_obj_add_event_cb(cancel, edit_cancel_event, LV_EVENT_CLICKED, NULL);
    lv_obj_t *save = create_button(panel, 8, 104, 142, 26, "SAVE", &lv_font_montserrat_12);
    set_button_selected(save, true);
    lv_obj_add_event_cb(save, edit_save_event, LV_EVENT_CLICKED, NULL);
}

static void create_ui(void)
{
    lv_obj_t *screen = lv_scr_act();
    lv_obj_set_style_bg_color(screen, lv_color_hex(COLOR_BG), 0);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);

    create_system_page(screen);
    create_model_page(screen);
    create_fan_page(screen);
    create_settings_page(screen);
    create_edit_page(screen);
    refresh_settings_labels();
    for (unsigned i = 1; i < PAGE_COUNT; i++) {
        lv_obj_add_flag(pages[i], LV_OBJ_FLAG_HIDDEN);
    }
    page_timer = lv_timer_create(page_timer_event, page_rotation_ms, NULL);
    lv_timer_create(ui_refresh_timer, UI_REFRESH_MS, NULL);
}

static void set_clock(const char *text)
{
    if (lvgl_port_lock(1000)) {
        for (unsigned i = 0; i < PAGE_COUNT; i++) {
            lv_label_set_text(clock_labels[i], text);
        }
        lvgl_port_unlock();
    }
}

static double json_number(cJSON *object, const char *name, double fallback)
{
    cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    return cJSON_IsNumber(item) ? item->valuedouble : fallback;
}

static bool json_has(cJSON *object, const char *name)
{
    cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    return cJSON_IsNumber(item);
}

static bool json_bool(cJSON *object, const char *name)
{
    cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    return cJSON_IsBool(item) && cJSON_IsTrue(item);
}

static void format_uptime(double seconds, char *out, size_t out_size)
{
    if (seconds < 0) {
        strlcpy(out, "--", out_size);
        return;
    }
    const int total = (int)seconds;
    const int days = total / 86400;
    const int hours = (total % 86400) / 3600;
    const int minutes = (total % 3600) / 60;
    if (days >= 2) {
        snprintf(out, out_size, "%dd", days);
    } else if (hours >= 1) {
        snprintf(out, out_size, "%dh", hours + days * 24);
    } else {
        snprintf(out, out_size, "%dm", minutes);
    }
}

static void set_bar_value(lv_obj_t *bar, lv_obj_t *label, double pct, uint32_t color,
                          const char *text)
{
    if (pct >= 0) {
        lv_bar_set_value(bar, (int32_t)(pct + 0.5), LV_ANIM_OFF);
        lv_label_set_text(label, text);
    } else {
        lv_bar_set_value(bar, 0, LV_ANIM_OFF);
        lv_label_set_text(label, "--");
    }
    lv_obj_set_style_bg_color(bar, lv_color_hex(color), LV_PART_INDICATOR);
    lv_obj_set_style_text_color(label, lv_color_hex(color), 0);
}

static uint32_t pct_color(double pct)
{
    return pct >= 97 ? COLOR_RED : pct >= 90 ? COLOR_AMBER : COLOR_CYAN;
}

/* Temperature bars map 0-100 degrees C straight onto the bar. */
static uint32_t temp_color(double temp)
{
    return temp >= 95 ? COLOR_RED : temp >= 80 ? COLOR_AMBER : COLOR_CYAN;
}

static void format_pct(char *out, size_t size, double pct, int digits)
{
    if (pct < 0) {
        strlcpy(out, "--", size);
    } else if (digits) {
        snprintf(out, size, "%.*f%%", digits, pct);
    } else {
        snprintf(out, size, "%.0f%%", pct);
    }
}

static void update_host_panel(unsigned index, cJSON *host)
{
    char text[64];
    char value[24];
    char uptime[12];
    const bool valid = host != NULL && json_has(host, "temp_c");

    if (!valid) {
        lv_label_set_text(host_hero[index], "--");
        lv_label_set_text(host_temp_label[index], "GPU --");
        for (unsigned j = 0; j < 6; j++) {
            lv_bar_set_value(host_bar[index][j], 0, LV_ANIM_OFF);
            lv_label_set_text(host_bar_value[index][j], "--");
        }
        lv_label_set_text(host_foot[index], "--");
        lv_obj_add_flag(host_thr[index], LV_OBJ_FLAG_HIDDEN);
        return;
    }

    const double temp = json_number(host, "temp_c", -1);
    const double util = json_number(host, "gpu_util_pct", -1);
    const double ram = json_number(host, "mem_used_pct", -1);
    const double disk = json_number(host, "root_used_pct", -1);
    const double power = json_number(host, "power_w", -1);
    const double power_est = json_number(host, "power_sys_est_w", -1);
    const double soc = json_number(host, "cpu_temp_c", -1);
    const double nvme = json_number(host, "nvme_temp_c", -1);
    const double cpu = json_number(host, "cpu_usage_pct", -1);
    format_uptime(json_number(host, "uptime_s", -1), uptime, sizeof(uptime));

    if (util >= 0) {
        snprintf(text, sizeof(text), "%.0f%%", util);
        lv_label_set_text(host_hero[index], text);
    } else {
        lv_label_set_text(host_hero[index], "--");
    }
    if (temp >= 0) {
        snprintf(text, sizeof(text), "GPU %.0f" DEGREE_SYMBOL, temp);
        lv_label_set_text(host_temp_label[index], text);
    } else {
        lv_label_set_text(host_temp_label[index], "GPU --");
    }

    /* GPU utilisation and CPU load are activity, not capacity warnings:
     * always cyan. Temperatures bar 0-100 degrees C with heat thresholds. */
    format_pct(value, sizeof(value), util, 0);
    set_bar_value(host_bar[index][0], host_bar_value[index][0], util, COLOR_CYAN, value);
    format_pct(value, sizeof(value), ram, 0);
    set_bar_value(host_bar[index][1], host_bar_value[index][1], ram, pct_color(ram), value);
    format_pct(value, sizeof(value), disk, 0);
    set_bar_value(host_bar[index][2], host_bar_value[index][2], disk, pct_color(disk), value);
    if (soc >= 0) {
        snprintf(value, sizeof(value), "%.0f" DEGREE_C, soc);
        set_bar_value(host_bar[index][3], host_bar_value[index][3], soc, temp_color(soc),
                      value);
    } else {
        set_bar_value(host_bar[index][3], host_bar_value[index][3], -1, COLOR_CYAN, "--");
    }
    if (nvme >= 0) {
        snprintf(value, sizeof(value), "%.0f" DEGREE_C, nvme);
        set_bar_value(host_bar[index][4], host_bar_value[index][4], nvme,
                      temp_color(nvme), value);
    } else {
        set_bar_value(host_bar[index][4], host_bar_value[index][4], -1, COLOR_CYAN, "--");
    }
    format_pct(value, sizeof(value), cpu, 0);
    set_bar_value(host_bar[index][5], host_bar_value[index][5], cpu, COLOR_CYAN, value);

    if (power >= 0) {
        char est[24];
        if (power_est >= 0) {
            snprintf(est, sizeof(est), "est %.0fW", power_est);
        } else {
            strlcpy(est, "est --", sizeof(est));
        }
        snprintf(text, sizeof(text), "%.0fW " MIDDOT " %s " MIDDOT " %s", power, est,
                 uptime);
    } else {
        snprintf(text, sizeof(text), "-- " MIDDOT " up %s", uptime);
    }
    lv_label_set_text(host_foot[index], text);

    const bool throttle = json_bool(host, "throttle_thermal") ||
                          json_bool(host, "throttle_power_cap");
    if (throttle) {
        lv_obj_clear_flag(host_thr[index], LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(host_thr[index], LV_OBJ_FLAG_HIDDEN);
    }
}

static void update_model_panel(cJSON *model)
{
    char text[64];
    cJSON *healthy = cJSON_GetObjectItemCaseSensitive(model, "healthy");
    const bool ok = cJSON_IsTrue(healthy);
    lv_obj_set_style_bg_color(model_dot, lv_color_hex(ok ? COLOR_GREEN : COLOR_RED), 0);
    lv_label_set_text(model_state_label, ok ? "ONLINE" : "OFFLINE");
    lv_obj_set_style_text_color(model_state_label,
                                lv_color_hex(ok ? COLOR_GREEN : COLOR_RED), 0);
    cJSON *name = cJSON_GetObjectItemCaseSensitive(model, "name");
    lv_label_set_text(model_name_label, cJSON_IsString(name) ? name->valuestring : "");

    if (!ok) {
        lv_label_set_text(model_hero_label, "--");
        lv_label_set_text(model_prompt_label, "");
        for (unsigned i = 0; i < 3; i++) {
            lv_label_set_text(model_chip_label[i], "--");
            lv_obj_set_style_text_color(model_chip_label[i], lv_color_hex(COLOR_MUTED), 0);
        }
        lv_label_set_text(model_ttft_label, "--");
        lv_label_set_text(model_p95_label, "--");
        lv_label_set_text(model_itl_label, "--");
        lv_label_set_text(model_prefix_value, "--");
        lv_label_set_text(model_spec_value, "--");
        lv_label_set_text(model_kv_label, "KV --");
        lv_bar_set_value(model_kv_bar, 0, LV_ANIM_OFF);
        return;
    }

    snprintf(text, sizeof(text), "%.1f", json_number(model, "generation_tps", 0));
    lv_label_set_text(model_hero_label, text);
    const double prompt_tps = json_number(model, "prompt_tps", 0);
    if (prompt_tps >= 100.0) {
        snprintf(text, sizeof(text), "#8ba8b7 in# #e6f1f5 %.0f# #8ba8b7 tok/s#",
                 prompt_tps);
    } else {
        snprintf(text, sizeof(text), "#8ba8b7 in# #e6f1f5 %.1f# #8ba8b7 tok/s#",
                 prompt_tps);
    }
    lv_label_set_text(model_prompt_label, text);

    const double running = json_number(model, "running", 0);
    const double waiting = json_number(model, "waiting", 0);
    const double preemptions = json_number(model, "preemptions_total", 0);
    snprintf(text, sizeof(text), "run %.0f", running);
    lv_label_set_text(model_chip_label[0], text);
    lv_obj_set_style_text_color(model_chip_label[0], lv_color_hex(COLOR_GREEN), 0);
    snprintf(text, sizeof(text), "wait %.0f", waiting);
    lv_label_set_text(model_chip_label[1], text);
    lv_obj_set_style_text_color(model_chip_label[1],
                                lv_color_hex(waiting > 0 ? COLOR_AMBER : COLOR_MUTED), 0);
    snprintf(text, sizeof(text), "pre %.0f", preemptions);
    lv_label_set_text(model_chip_label[2], text);
    lv_obj_set_style_text_color(model_chip_label[2],
                                lv_color_hex(preemptions > 0 ? COLOR_RED : COLOR_GREEN), 0);

    const double ttft = json_number(model, "ttft_ms", -1);
    if (ttft >= 0) {
        snprintf(text, sizeof(text), "%.2fs", ttft / 1000.0);
        lv_label_set_text(model_ttft_label, text);
    } else {
        lv_label_set_text(model_ttft_label, "--");
    }
    const double ttft_p95 = json_number(model, "ttft_p95_ms", -1);
    if (ttft_p95 >= 0) {
        snprintf(text, sizeof(text), "%.2fs", ttft_p95 / 1000.0);
        lv_label_set_text(model_p95_label, text);
    } else {
        lv_label_set_text(model_p95_label, "--");
    }
    const double itl_p95 = json_number(model, "itl_p95_ms", -1);
    if (itl_p95 >= 0) {
        snprintf(text, sizeof(text), "%.0fms", itl_p95);
        lv_label_set_text(model_itl_label, text);
    } else {
        lv_label_set_text(model_itl_label, "--");
    }

    const double prefix = json_number(model, "prefix_cache_hit_pct", -1);
    format_pct(text, sizeof(text), prefix, 0);
    lv_label_set_text(model_prefix_value, text);
    const double spec = json_number(model, "spec_accept_pct", -1);
    format_pct(text, sizeof(text), spec, 0);
    lv_label_set_text(model_spec_value, text);

    const double kv = json_number(model, "kv_pct", -1);
    if (kv >= 0) {
        snprintf(text, sizeof(text), "KV %.1f%%", kv);
        lv_label_set_text(model_kv_label, text);
        lv_bar_set_value(model_kv_bar, (int32_t)(kv + 0.5), LV_ANIM_OFF);
    } else {
        lv_label_set_text(model_kv_label, "KV --");
        lv_bar_set_value(model_kv_bar, 0, LV_ANIM_OFF);
    }
}

static void update_dashboard(const char *json)
{
    cJSON *root = cJSON_Parse(json);
    if (root == NULL) {
        set_clock("--:--:--");
        fan_control_sample_lost();
        return;
    }

    cJSON *head = cJSON_GetObjectItemCaseSensitive(root, "head");
    cJSON *worker = cJSON_GetObjectItemCaseSensitive(root, "worker");
    cJSON *model = cJSON_GetObjectItemCaseSensitive(root, "model");
    cJSON *updated = cJSON_GetObjectItemCaseSensitive(root, "updated");
    double configured_rotation = json_number(root, "page_rotation_ms", DEFAULT_PAGE_ROTATION_MS);
    uint32_t new_rotation_ms = configured_rotation >= MIN_PAGE_ROTATION_MS &&
                                           configured_rotation <= MAX_PAGE_ROTATION_MS
                                   ? (uint32_t)configured_rotation
                                   : DEFAULT_PAGE_ROTATION_MS;

    if (!cJSON_IsObject(head) || !cJSON_IsObject(worker) || !cJSON_IsObject(model)) {
        cJSON_Delete(root);
        set_clock("--:--:--");
        fan_control_sample_lost();
        return;
    }

    const bool head_valid = json_has(head, "temp_c");
    const bool worker_valid = json_has(worker, "temp_c");
    const double head_temp = json_number(head, "temp_c", 0);
    const double worker_temp = json_number(worker, "temp_c", 0);

    if (lvgl_port_lock(1000)) {
        if (new_rotation_ms != page_rotation_ms) {
            page_rotation_ms = new_rotation_ms;
            lv_timer_set_period(page_timer, page_rotation_ms);
            lv_timer_reset(page_timer);
            ESP_LOGI(TAG, "page rotation updated: %" PRIu32 " ms", page_rotation_ms);
        }
        update_host_panel(0, head);
        update_host_panel(1, worker);
        update_model_panel(model);
        for (unsigned i = 0; i < PAGE_COUNT; i++) {
            lv_label_set_text(clock_labels[i],
                              cJSON_IsString(updated) ? updated->valuestring : "--:--:--");
        }
        lvgl_port_unlock();
    }
    cJSON_Delete(root);
    fan_control_on_sample((int)head_temp, (int)worker_temp, head_valid && worker_valid);
}

static esp_err_t http_event(esp_http_client_event_t *event)
{
    http_response_t *response = event->user_data;
    if (event->event_id == HTTP_EVENT_ON_DATA && event->data_len > 0) {
        size_t available = sizeof(response->data) - response->length - 1;
        size_t copy_length = event->data_len < available ? event->data_len : available;
        memcpy(response->data + response->length, event->data, copy_length);
        response->length += copy_length;
        response->data[response->length] = '\0';
    }
    return ESP_OK;
}

static esp_err_t fetch_status(char *output, size_t output_size)
{
    http_response_t response = {0};
    esp_http_client_config_t config = {
        .url = CLUSTER_STATUS_URL,
        .event_handler = http_event,
        .user_data = &response,
        .timeout_ms = 3500,
    };
    esp_http_client_handle_t client = esp_http_client_init(&config);
    ESP_RETURN_ON_FALSE(client != NULL, ESP_ERR_NO_MEM, TAG, "HTTP client init failed");
    esp_err_t result = esp_http_client_perform(client);
    int status = esp_http_client_get_status_code(client);
    esp_http_client_cleanup(client);
    if (result != ESP_OK || status != 200 || response.length == 0) {
        return result == ESP_OK ? ESP_FAIL : result;
    }
    strlcpy(output, response.data, output_size);
    return ESP_OK;
}

static void dashboard_task(void *argument)
{
    /* Static so the enlarged payload buffer stays off the 8 KB task stack
     * (fetch_status keeps its own 4 KB response buffer on the same stack). */
    static char json[4096];
    while (true) {
        EventBits_t bits = xEventGroupGetBits(wifi_events);
        if (bits & WIFI_CONNECTED_BIT) {
            esp_err_t result = fetch_status(json, sizeof(json));
            if (result == ESP_OK) {
                update_dashboard(json);
                ESP_LOGI(TAG, "cluster status updated");
            } else {
                ESP_LOGW(TAG, "status fetch failed: %s", esp_err_to_name(result));
                set_clock("--:--:--");
                fan_control_sample_lost();
            }
        } else {
            set_clock("--:--:--");
            fan_control_sample_lost();
            if (bits & WIFI_FAIL_BIT) {
                wifi_retries = 0;
                xEventGroupClearBits(wifi_events, WIFI_FAIL_BIT);
                ESP_LOGI(TAG, "retrying WiFi after failed connection cycle");
                esp_wifi_connect();
            }
        }
        vTaskDelay(pdMS_TO_TICKS(CLUSTER_REFRESH_MS));
    }
}

static void wifi_event(void *argument, esp_event_base_t event_base,
                       int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        const wifi_event_sta_disconnected_t *event = event_data;
        fan_control_set_wifi(false);
        xEventGroupClearBits(wifi_events, WIFI_CONNECTED_BIT);
        ESP_LOGW(TAG, "WiFi disconnected: reason=%u retry=%d/%d",
                 event->reason, wifi_retries + 1, WIFI_MAX_RETRY);
        if (wifi_retries < WIFI_MAX_RETRY) {
            wifi_retries++;
            esp_wifi_connect();
        } else {
            xEventGroupSetBits(wifi_events, WIFI_FAIL_BIT);
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = event_data;
        snprintf(wifi_ip, sizeof(wifi_ip), IPSTR, IP2STR(&event->ip_info.ip));
        wifi_retries = 0;
        fan_control_set_wifi(true);
        xEventGroupClearBits(wifi_events, WIFI_FAIL_BIT);
        xEventGroupSetBits(wifi_events, WIFI_CONNECTED_BIT);
        ESP_LOGI(TAG, "WiFi connected: %s", wifi_ip);
    }
}

static esp_err_t init_wifi(void)
{
    wifi_events = xEventGroupCreate();
    ESP_RETURN_ON_FALSE(wifi_events != NULL, ESP_ERR_NO_MEM, TAG, "event group failed");
    ESP_RETURN_ON_ERROR(esp_netif_init(), TAG, "netif init failed");
    ESP_RETURN_ON_ERROR(esp_event_loop_create_default(), TAG, "event loop failed");
    ESP_RETURN_ON_FALSE(esp_netif_create_default_wifi_sta() != NULL,
                        ESP_FAIL, TAG, "station netif failed");

    wifi_init_config_t init_config = WIFI_INIT_CONFIG_DEFAULT();
    ESP_RETURN_ON_ERROR(esp_wifi_init(&init_config), TAG, "WiFi init failed");
    ESP_RETURN_ON_ERROR(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                                   wifi_event, NULL), TAG, "WiFi handler failed");
    ESP_RETURN_ON_ERROR(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                                   wifi_event, NULL), TAG, "IP handler failed");

    wifi_config_t config = {0};
    strlcpy((char *)config.sta.ssid, WIFI_SSID, sizeof(config.sta.ssid));
    strlcpy((char *)config.sta.password, WIFI_PASSWORD, sizeof(config.sta.password));
    config.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
    config.sta.pmf_cfg.capable = true;
    config.sta.pmf_cfg.required = false;
    ESP_RETURN_ON_ERROR(esp_wifi_set_mode(WIFI_MODE_STA), TAG, "station mode failed");
    ESP_RETURN_ON_ERROR(esp_wifi_set_config(WIFI_IF_STA, &config), TAG, "WiFi config failed");
    ESP_RETURN_ON_ERROR(esp_wifi_start(), TAG, "WiFi start failed");

    EventBits_t bits = xEventGroupWaitBits(
        wifi_events, WIFI_CONNECTED_BIT | WIFI_FAIL_BIT, pdFALSE, pdFALSE,
        pdMS_TO_TICKS(20000));
    return (bits & WIFI_CONNECTED_BIT) ? ESP_OK : ESP_FAIL;
}

static esp_err_t init_lvgl(void)
{
    const lvgl_port_cfg_t lvgl_config = {
        .task_priority = 4,
        .task_stack = 10 * 1024,
        .task_affinity = -1,
        .task_max_sleep_ms = 500,
        .timer_period_ms = 5,
    };
    ESP_RETURN_ON_ERROR(lvgl_port_init(&lvgl_config), TAG, "LVGL init failed");

    lvgl_port_display_cfg_t display_config = {
        .io_handle = io_handle,
        .panel_handle = panel_handle,
        .buffer_size = LCD_H_RES * LCD_DRAW_BUFFER_HEIGHT,
        .double_buffer = true,
        .hres = LCD_H_RES,
        .vres = LCD_V_RES,
        .monochrome = false,
        .rotation = {
            .swap_xy = true,
            .mirror_x = true,
            .mirror_y = false,
        },
        .flags = {
            .buff_spiram = false,
            .buff_dma = true,
#if LVGL_VERSION_MAJOR >= 9
            .swap_bytes = true,
#endif
        },
    };
    ESP_ERROR_CHECK(esp_lcd_panel_set_gap(panel_handle, 0, 34));
    display = lvgl_port_add_disp(&display_config);

    const lvgl_port_touch_cfg_t touch_config = {
        .disp = display,
        .handle = touch_handle,
    };
    lvgl_port_add_touch(&touch_config);
    return ESP_OK;
}

void app_main(void)
{
    esp_err_t result = nvs_flash_init();
    if (result == ESP_ERR_NVS_NO_FREE_PAGES || result == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        result = nvs_flash_init();
    }
    ESP_ERROR_CHECK(result);

    /* Bring the shared PWM up in its fail-safe full-speed state before any
     * display or network work, so an early abort still leaves cooling on. */
    fan_control_init();

    i2c_master_bus_handle_t i2c_bus = bsp_i2c_init();
    bsp_display_init(&io_handle, &panel_handle, LCD_H_RES * LCD_DRAW_BUFFER_HEIGHT);
    bsp_touch_init(&touch_handle, i2c_bus, LCD_H_RES, LCD_V_RES, DISPLAY_ROTATION);
    ESP_ERROR_CHECK(esp_lcd_touch_read_data(touch_handle));
    ESP_ERROR_CHECK(init_lvgl());
    bsp_display_brightness_init();
    bsp_display_set_brightness(85);

    if (lvgl_port_lock(0)) {
        create_ui();
        lvgl_port_unlock();
    }

    result = init_wifi();
    if (result != ESP_OK) {
        ESP_LOGE(TAG, "WiFi connection failed");
    }
    xTaskCreate(dashboard_task, "dashboard", 8192, NULL, 4, NULL);
    ESP_LOGI(TAG, "landscape cluster dashboard ready with fan control");
}
