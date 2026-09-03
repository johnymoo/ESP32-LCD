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
#include "wifi_credentials.h"

#define DISPLAY_ROTATION 90
#define LCD_H_RES 320
#define LCD_V_RES 172
#define LCD_DRAW_BUFFER_HEIGHT 40
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT BIT1
#define WIFI_MAX_RETRY 10
#define PAGE_ROTATION_MS 10000

static const char *TAG = "cluster_display";

static esp_lcd_panel_io_handle_t io_handle;
static esp_lcd_panel_handle_t panel_handle;
static esp_lcd_touch_handle_t touch_handle;
static lv_display_t *display;
static EventGroupHandle_t wifi_events;
static int wifi_retries;
static char wifi_ip[16] = "--";

static lv_obj_t *system_page;
static lv_obj_t *model_page;
static lv_obj_t *head_label;
static lv_obj_t *worker_label;
static lv_obj_t *model_state_label;
static lv_obj_t *model_metrics_label;
static lv_obj_t *system_footer_label;
static lv_obj_t *model_footer_label;
static lv_timer_t *page_timer;
static unsigned current_page;

typedef struct {
    char data[2048];
    size_t length;
} http_response_t;

static lv_obj_t *create_panel(lv_obj_t *parent, int x, int y, int width, int height)
{
    lv_obj_t *panel = lv_obj_create(parent);
    lv_obj_set_pos(panel, x, y);
    lv_obj_set_size(panel, width, height);
    lv_obj_set_style_radius(panel, 4, 0);
    lv_obj_set_style_bg_color(panel, lv_color_hex(0x172B3A), 0);
    lv_obj_set_style_border_color(panel, lv_color_hex(0x315568), 0);
    lv_obj_set_style_border_width(panel, 1, 0);
    lv_obj_set_style_pad_all(panel, 7, 0);
    lv_obj_clear_flag(panel, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(panel, LV_OBJ_FLAG_CLICKABLE);
    return panel;
}

static lv_obj_t *create_page(lv_obj_t *screen)
{
    lv_obj_t *page = lv_obj_create(screen);
    lv_obj_set_pos(page, 0, 0);
    lv_obj_set_size(page, LCD_H_RES, LCD_V_RES);
    lv_obj_set_style_radius(page, 0, 0);
    lv_obj_set_style_border_width(page, 0, 0);
    lv_obj_set_style_pad_all(page, 0, 0);
    lv_obj_set_style_bg_color(page, lv_color_hex(0x091A24), 0);
    lv_obj_clear_flag(page, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(page, LV_OBJ_FLAG_CLICKABLE);
    return page;
}

static void create_title(lv_obj_t *page, const char *text, const char *index)
{
    lv_obj_t *title = lv_label_create(page);
    lv_label_set_text(title, text);
    lv_obj_set_style_text_color(title, lv_color_hex(0x7DE2D1), 0);
    lv_obj_set_style_text_font(title, &lv_font_montserrat_20, 0);
    lv_obj_align(title, LV_ALIGN_TOP_LEFT, 8, 3);

    lv_obj_t *page_index = lv_label_create(page);
    lv_label_set_text(page_index, index);
    lv_obj_set_style_text_color(page_index, lv_color_hex(0x8BA8B7), 0);
    lv_obj_set_style_text_font(page_index, &lv_font_montserrat_20, 0);
    lv_obj_align(page_index, LV_ALIGN_TOP_RIGHT, -8, 3);
}

static lv_obj_t *create_footer(lv_obj_t *page)
{
    lv_obj_t *footer = lv_label_create(page);
    lv_label_set_text(footer, "WiFi: connecting");
    lv_obj_set_width(footer, 304);
    lv_obj_set_style_text_color(footer, lv_color_hex(0x8BA8B7), 0);
    lv_obj_set_style_text_align(footer, LV_TEXT_ALIGN_RIGHT, 0);
    lv_obj_align(footer, LV_ALIGN_BOTTOM_MID, 0, -4);
    return footer;
}

static void show_next_page(void)
{
    current_page = (current_page + 1) % 2;
    if (current_page == 0) {
        lv_obj_clear_flag(system_page, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(model_page, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(system_page, LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(model_page, LV_OBJ_FLAG_HIDDEN);
    }
    ESP_LOGI(TAG, "display page: %s", current_page == 0 ? "system" : "model");
}

static void page_timer_event(lv_timer_t *timer)
{
    show_next_page();
}

static void page_touch_event(lv_event_t *event)
{
    if (lv_event_get_code(event) != LV_EVENT_CLICKED) {
        return;
    }
    show_next_page();
    if (page_timer != NULL) {
        lv_timer_reset(page_timer);
    }
}

static void create_ui(void)
{
    lv_obj_t *screen = lv_scr_act();
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x091A24), 0);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);

    system_page = create_page(screen);
    create_title(system_page, "SYSTEM LOAD", "1/2");

    lv_obj_t *head_panel = create_panel(system_page, 5, 31, 153, 116);
    head_label = lv_label_create(head_panel);
    lv_obj_set_width(head_label, lv_pct(100));
    lv_obj_set_style_text_color(head_label, lv_color_hex(0xE6F1F5), 0);
    lv_obj_set_style_text_font(head_label, &lv_font_montserrat_20, 0);
    lv_label_set_text(head_label, "HEAD\nWaiting...");

    lv_obj_t *worker_panel = create_panel(system_page, 162, 31, 153, 116);
    worker_label = lv_label_create(worker_panel);
    lv_obj_set_width(worker_label, lv_pct(100));
    lv_obj_set_style_text_color(worker_label, lv_color_hex(0xE6F1F5), 0);
    lv_obj_set_style_text_font(worker_label, &lv_font_montserrat_20, 0);
    lv_label_set_text(worker_label, "WORKER\nWaiting...");

    system_footer_label = create_footer(system_page);

    model_page = create_page(screen);
    create_title(model_page, "MODEL INFERENCE", "2/2");

    lv_obj_t *model_panel = create_panel(model_page, 5, 31, 310, 116);
    model_state_label = lv_label_create(model_panel);
    lv_obj_set_width(model_state_label, lv_pct(100));
    lv_obj_set_style_text_color(model_state_label, lv_color_hex(0xFF6B6B), 0);
    lv_obj_set_style_text_font(model_state_label, &lv_font_montserrat_24, 0);
    lv_label_set_text(model_state_label, "MODEL DOWN");

    model_metrics_label = lv_label_create(model_panel);
    lv_obj_set_pos(model_metrics_label, 0, 31);
    lv_obj_set_width(model_metrics_label, lv_pct(100));
    lv_obj_set_style_text_color(model_metrics_label, lv_color_hex(0xE6F1F5), 0);
    lv_obj_set_style_text_font(model_metrics_label, &lv_font_montserrat_20, 0);
    lv_label_set_text(model_metrics_label, "RUN 0  WAIT 0\nKV 0%\nIN 0  OUT 0 tok/s");

    model_footer_label = create_footer(model_page);

    lv_obj_add_event_cb(system_page, page_touch_event, LV_EVENT_CLICKED, NULL);
    lv_obj_add_event_cb(model_page, page_touch_event, LV_EVENT_CLICKED, NULL);
    lv_obj_add_flag(model_page, LV_OBJ_FLAG_HIDDEN);
    page_timer = lv_timer_create(page_timer_event, PAGE_ROTATION_MS, NULL);
}

static void set_footer(const char *text, lv_color_t color)
{
    if (lvgl_port_lock(1000)) {
        lv_label_set_text(system_footer_label, text);
        lv_label_set_text(model_footer_label, text);
        lv_obj_set_style_text_color(system_footer_label, color, 0);
        lv_obj_set_style_text_color(model_footer_label, color, 0);
        lvgl_port_unlock();
    }
}

static double json_number(cJSON *object, const char *name, double fallback)
{
    cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    return cJSON_IsNumber(item) ? item->valuedouble : fallback;
}

static void update_dashboard(const char *json)
{
    cJSON *root = cJSON_Parse(json);
    if (root == NULL) {
        set_footer("Status: invalid JSON", lv_color_hex(0xFF6B6B));
        return;
    }

    cJSON *head = cJSON_GetObjectItemCaseSensitive(root, "head");
    cJSON *worker = cJSON_GetObjectItemCaseSensitive(root, "worker");
    cJSON *model = cJSON_GetObjectItemCaseSensitive(root, "model");
    cJSON *updated = cJSON_GetObjectItemCaseSensitive(root, "updated");

    if (!cJSON_IsObject(head) || !cJSON_IsObject(worker) || !cJSON_IsObject(model)) {
        cJSON_Delete(root);
        set_footer("Status: host unavailable", lv_color_hex(0xFFB86B));
        return;
    }

    char head_text[96];
    char worker_text[96];
    char model_metrics_text[128];
    char footer_text[80];
    snprintf(head_text, sizeof(head_text), "HEAD  %.0fC\nGPU %.0f%%\nLOAD %.1f\nRAM %.0f%% %.0fW",
             json_number(head, "temp_c", -1), json_number(head, "gpu_util_pct", -1),
             json_number(head, "load1", -1), json_number(head, "mem_used_pct", -1),
             json_number(head, "power_w", -1));
    snprintf(worker_text, sizeof(worker_text), "WORKER %.0fC\nGPU %.0f%%\nLOAD %.1f\nRAM %.0f%% %.0fW",
             json_number(worker, "temp_c", -1), json_number(worker, "gpu_util_pct", -1),
             json_number(worker, "load1", -1), json_number(worker, "mem_used_pct", -1),
             json_number(worker, "power_w", -1));

    cJSON *healthy = cJSON_GetObjectItemCaseSensitive(model, "healthy");
    const bool model_ok = cJSON_IsTrue(healthy);
    snprintf(model_metrics_text, sizeof(model_metrics_text), "RUN %.0f  WAIT %.0f\nKV %.0f%%\nIN %.0f  OUT %.0f tok/s",
             json_number(model, "running", 0), json_number(model, "waiting", 0),
             json_number(model, "kv_pct", 0), json_number(model, "prompt_tps", 0),
             json_number(model, "generation_tps", 0));
    snprintf(footer_text, sizeof(footer_text), "WiFi %s  Updated %s", wifi_ip,
             cJSON_IsString(updated) ? updated->valuestring : "--:--:--");

    if (lvgl_port_lock(1000)) {
        lv_label_set_text(head_label, head_text);
        lv_label_set_text(worker_label, worker_text);
        lv_label_set_text(model_state_label, model_ok ? "MODEL ONLINE" : "MODEL DOWN");
        lv_label_set_text(model_metrics_label, model_metrics_text);
        lv_obj_set_style_text_color(model_state_label,
                                    model_ok ? lv_color_hex(0x7DE2D1) : lv_color_hex(0xFF6B6B), 0);
        lv_label_set_text(system_footer_label, footer_text);
        lv_label_set_text(model_footer_label, footer_text);
        lv_obj_set_style_text_color(system_footer_label, lv_color_hex(0x8BA8B7), 0);
        lv_obj_set_style_text_color(model_footer_label, lv_color_hex(0x8BA8B7), 0);
        lvgl_port_unlock();
    }
    cJSON_Delete(root);
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
    char json[2048];
    while (true) {
        EventBits_t bits = xEventGroupGetBits(wifi_events);
        if (bits & WIFI_CONNECTED_BIT) {
            esp_err_t result = fetch_status(json, sizeof(json));
            if (result == ESP_OK) {
                update_dashboard(json);
                ESP_LOGI(TAG, "cluster status updated");
            } else {
                ESP_LOGW(TAG, "status fetch failed: %s", esp_err_to_name(result));
                set_footer("Status endpoint unreachable", lv_color_hex(0xFFB86B));
            }
        } else {
            set_footer("WiFi disconnected", lv_color_hex(0xFF6B6B));
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
        set_footer("WiFi connection failed", lv_color_hex(0xFF6B6B));
        ESP_LOGE(TAG, "WiFi connection failed");
    }
    xTaskCreate(dashboard_task, "dashboard", 8192, NULL, 4, NULL);
    ESP_LOGI(TAG, "landscape cluster dashboard ready");
}
