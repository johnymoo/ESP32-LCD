# ESP32-S3 Touch LCD 1.47

Development workspace for the Waveshare ESP32-S3-Touch-LCD-1.47 connected to
`gb10-2`. The repository is also a reusable baseline for adapting similar
ESP32-S3 touch displays after their board-specific BSP, pin map, panel geometry,
and touch transform have been verified.

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
LCD and AXS5106L touch controller through the vendor BSP, renders a 320 x 172
landscape GB10 cluster dashboard, joins Wi-Fi, and refreshes the cluster status
endpoint every five seconds. System load and model inference use separate,
large-text pages that rotate every five seconds; touching the display advances
immediately to the next page. The companion Web mirror is served from
`http://192.168.88.181:9108/`.

Read `AGENTS.md` before adapting the project to another display. See
`docs/SETUP.md` for installation and recovery, `docs/HARDWARE.md` for the pin
map, `docs/SOURCES.md` for official downloads and checksums, and
`docs/CLUSTER-DASHBOARD.md` for the data service contract.
