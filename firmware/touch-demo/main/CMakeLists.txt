idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES
        esp_bsp
        esp_event
        esp_http_client
        esp_netif
        esp_wifi
        json
        nvs_flash
)
