idf_component_register(
    SRCS "main.c" "fan_control.c" "fan_config.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES
        driver
        esp_bsp
        esp_event
        esp_http_client
        esp_netif
        esp_timer
        esp_wifi
        json
        nvs_flash
)
