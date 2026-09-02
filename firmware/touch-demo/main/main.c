#include <stdio.h>

#include "esp_check.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_lvgl_port.h"
#include "nvs_flash.h"

#include "bsp_display.h"
#include "bsp_i2c.h"
#include "bsp_touch.h"

#define LCD_H_RES 172
#define LCD_V_RES 320
#define LCD_DRAW_BUFFER_HEIGHT 50

static const char *TAG = "touch_demo";

static esp_lcd_panel_io_handle_t io_handle;
static esp_lcd_panel_handle_t panel_handle;
static esp_lcd_touch_handle_t touch_handle;
static lv_display_t *display;
static unsigned touch_count;

static void touch_button_event(lv_event_t *event)
{
    if (lv_event_get_code(event) != LV_EVENT_CLICKED) {
        return;
    }

    lv_obj_t *label = lv_event_get_user_data(event);
    touch_count++;
    lv_label_set_text_fmt(label, "Touches: %u", touch_count);
    ESP_LOGI(TAG, "touch count: %u", touch_count);
}

static void create_ui(void)
{
    lv_obj_t *screen = lv_scr_act();
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x102A43), 0);

    lv_obj_t *title = lv_label_create(screen);
    lv_label_set_text(title, "ESP32-S3\nTouch LCD");
    lv_obj_set_style_text_color(title, lv_color_hex(0xF0F4F8), 0);
    lv_obj_set_style_text_align(title, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 34);

    lv_obj_t *button = lv_btn_create(screen);
    lv_obj_set_size(button, 142, 76);
    lv_obj_align(button, LV_ALIGN_CENTER, 0, 14);
    lv_obj_set_style_bg_color(button, lv_color_hex(0x2CB67D), 0);

    lv_obj_t *label = lv_label_create(button);
    lv_label_set_text(label, "Touch me");
    lv_obj_center(label);
    lv_obj_add_event_cb(button, touch_button_event, LV_EVENT_CLICKED, label);

    lv_obj_t *status = lv_label_create(screen);
    lv_label_set_text(status, "JD9853 + AXS5106L\nESP-IDF v5.5.2");
    lv_obj_set_style_text_color(status, lv_color_hex(0xBCCCDC), 0);
    lv_obj_set_style_text_align(status, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(status, LV_ALIGN_BOTTOM_MID, 0, -28);
}

static esp_err_t init_lvgl(void)
{
    const lvgl_port_cfg_t lvgl_cfg = {
        .task_priority = 4,
        .task_stack = 10 * 1024,
        .task_affinity = -1,
        .task_max_sleep_ms = 500,
        .timer_period_ms = 5,
    };
    ESP_RETURN_ON_ERROR(lvgl_port_init(&lvgl_cfg), TAG, "LVGL init failed");

    const lvgl_port_display_cfg_t display_cfg = {
        .io_handle = io_handle,
        .panel_handle = panel_handle,
        .buffer_size = LCD_H_RES * LCD_DRAW_BUFFER_HEIGHT,
        .double_buffer = true,
        .hres = LCD_H_RES,
        .vres = LCD_V_RES,
        .monochrome = false,
        .rotation = {
            .swap_xy = false,
            .mirror_x = false,
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
    ESP_ERROR_CHECK(esp_lcd_panel_set_gap(panel_handle, 34, 0));
    display = lvgl_port_add_disp(&display_cfg);

    const lvgl_port_touch_cfg_t touch_cfg = {
        .disp = display,
        .handle = touch_handle,
    };
    lvgl_port_add_touch(&touch_cfg);
    return ESP_OK;
}

void app_main(void)
{
    esp_err_t result = nvs_flash_init();
    if (result == ESP_ERR_NVS_NO_FREE_PAGES ||
        result == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        result = nvs_flash_init();
    }
    ESP_ERROR_CHECK(result);

    i2c_master_bus_handle_t i2c_bus = bsp_i2c_init();
    bsp_display_init(&io_handle, &panel_handle,
                     LCD_H_RES * LCD_DRAW_BUFFER_HEIGHT);
    bsp_touch_init(&touch_handle, i2c_bus, LCD_H_RES, LCD_V_RES, 0);
    ESP_ERROR_CHECK(esp_lcd_touch_read_data(touch_handle));
    ESP_LOGI(TAG, "AXS5106L I2C read self-test passed");
    ESP_ERROR_CHECK(init_lvgl());

    bsp_display_brightness_init();
    bsp_display_set_brightness(100);

    if (lvgl_port_lock(0)) {
        create_ui();
        lvgl_port_unlock();
    }

    ESP_LOGI(TAG, "LCD and touch ready");
}
