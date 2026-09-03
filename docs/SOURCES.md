# Sources

Links and downloads were verified on 2026-09-03 against Waveshare's official
documentation.

## Board documentation

- [Waveshare product documentation](https://docs.waveshare.net/ESP32-S3-Touch-LCD-1.47/)
- [Waveshare legacy wiki page](https://www.waveshare.net/wiki/ESP32-S3-Touch-LCD-1.47)
- [Resources and documents](https://docs.waveshare.net/ESP32-S3-Touch-LCD-1.47/Resources-And-Documents/)
- [ESP-IDF development guide](https://docs.waveshare.net/ESP32-S3-Touch-LCD-1.47/ESP-IDF/)
- [Firmware flashing guide](https://docs.waveshare.net/ESP32-S3-Touch-LCD-1.47/Firmware-Flashing/)

## Direct downloads

- [Demo code and board drivers](https://files.waveshare.net/wiki/ESP32-S3-Touch-LCD-1.47/ESP32-S3-Touch-LCD-1.47-Demo.zip)
  contains the Arduino examples, ESP-IDF examples, factory binaries, board BSP,
  JD9853 LCD driver, and AXS5106L touch driver used by this project.
- [Schematic PDF](https://www.waveshare.net/w/upload/0/0d/ESP32-S3-Touch-LCD-1.47-Schematic.pdf)
- [2D/3D mechanical files](https://files.waveshare.net/wiki/ESP32-S3-Touch-LCD-1.47/ESP32-S3-Touch-LCD-1.47-2D3D.zip)

Waveshare distributes the board-specific drivers inside the demo ZIP rather
than as separate downloads. Their project locations are:

| Driver | Local path | Upstream location in the demo ZIP |
| --- | --- | --- |
| Board BSP and pin mapping | `firmware/touch-demo/components/esp_bsp` | `ESP-IDF/01_factory/components/esp_bsp` |
| JD9853 LCD panel | `firmware/touch-demo/components/esp_lcd_jd9853` | `ESP-IDF/01_factory/components/esp_lcd_jd9853` |
| AXS5106L touch controller | `firmware/touch-demo/components/esp_lcd_touch_axs5106` | `ESP-IDF/01_factory/components/esp_lcd_touch_axs5106` |

## Toolchain and managed components

- [ESP-IDF v5.5.2 source](https://github.com/espressif/esp-idf/tree/v5.5.2)
- [ESP-IDF programming guide](https://docs.espressif.com/projects/esp-idf/en/v5.5.2/esp32s3/get-started/index.html)
- [`espressif/esp_lcd_touch` 1.1.2](https://components.espressif.com/components/espressif/esp_lcd_touch/versions/1.1.2)
- [`espressif/esp_lvgl_port` 2.5.0](https://components.espressif.com/components/espressif/esp_lvgl_port/versions/2.5.0)
- [`lvgl/lvgl` 8.4.0](https://components.espressif.com/components/lvgl/lvgl/versions/8.4.0)

The exact resolved versions and component hashes are recorded in
`firmware/touch-demo/dependencies.lock`.

## Download checksums

```text
121e69ce59f145ec1ac7a353ce7cc13d917a9705b8908eb473075ed52777df4b  ESP32-S3-Touch-LCD-1.47-2D3D.zip
82510e02ac1fd8e4d14f42dacf552130f96b7536a45f49f90800b3f93b6c379c  ESP32-S3-Touch-LCD-1.47-Demo.zip
db1f05c28bbd078e76b430ff2a1332fe7e566731104756a73c84f08c38333ae5  ESP32-S3-Touch-LCD-1.47-Schematic.pdf
```
