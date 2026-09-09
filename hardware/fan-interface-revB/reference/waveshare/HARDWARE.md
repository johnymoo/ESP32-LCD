# Hardware

- Board: Waveshare ESP32-S3-Touch-LCD-1.47
- MCU package: ESP32-S3R8, dual-core LX7, 8 MiB octal PSRAM
- Flash: 16 MiB
- Display: JD9853, 172 x 320, 16-bit color
- Touch: AXS5106L capacitive controller
- USB: ESP32-S3 native USB Serial/JTAG, USB ID `303a:1001`
- Stable Linux path: `/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_*-if00`

## Board pin map

| Function | GPIO |
| --- | ---: |
| LCD MOSI | 39 |
| LCD SCLK | 38 |
| LCD CS | 21 |
| LCD DC | 45 |
| LCD reset | 40 |
| LCD backlight PWM | 46 |
| Touch/I2C SDA | 42 |
| Touch/I2C SCL | 41 |
| Touch interrupt | 47 |
| Touch reset | 48 |
| SD CLK | 16 |
| SD CMD | 15 |
| SD D0/D1/D2/D3 | 17/18/13/14 |
| BOOT button | 0 |

The values above are taken from the vendor ESP-IDF BSP included in the demo
archive. The public product page contains one apparent typo (`72 x 320`); the
feature list, examples, BSP, and display configuration consistently use
`172 x 320`.

