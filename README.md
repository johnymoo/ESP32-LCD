# ESP32-S3 Touch LCD 1.47

Development workspace for the Waveshare ESP32-S3-Touch-LCD-1.47 connected to
`gb10-2`.

## Quick start

```bash
cd ~/project/esp32-s3-touch-1.47
./scripts/device-info.sh
./scripts/build.sh
./scripts/flash.sh
./scripts/monitor.sh
```

Exit the serial monitor with `Ctrl+]`.

The primary application is `firmware/touch-demo`. It initializes the JD9853
LCD and AXS5106L touch controller through the vendor BSP. Pressing the on-screen
button increments a counter and writes a `touch count` entry to the serial log.

See `docs/SETUP.md` for installation and recovery, `docs/HARDWARE.md` for the
pin map, and `docs/SOURCES.md` for upstream material and checksums.

