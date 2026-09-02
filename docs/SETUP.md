# Setup and operation

## Installed environment

- Host: `gb10-2` (`aarch64`, Ubuntu 24.04)
- ESP-IDF: `v5.5.2` in `.tools/esp-idf`
- ESP-IDF tools: `.tools/espressif`
- Optional LAN proxy: `http://192.168.88.2:7890`
- Linux serial driver: in-kernel `cdc_acm`
- Required user group: `dialout`

The host packages are the standard Espressif Linux prerequisites. The
toolchain itself stays inside this project and is ignored by Git.

## Commands

```bash
./scripts/device-info.sh
./scripts/build.sh
./scripts/backup-flash.sh
./scripts/flash.sh
./scripts/monitor.sh
```

Set `ESP32_USE_PROXY=0` to disable the project proxy for a command.

## Recovery

Full Flash backups are stored under `firmware/backups` with SHA-256 sidecars.
They are intentionally ignored by Git because they may contain device-specific
data. Restore only a backup captured from this board:

```bash
./scripts/restore-flash.sh firmware/backups/<timestamp>-flash-16MiB.bin
```

The vendor factory image is also available at
`vendor/waveshare/extracted/ESP32-S3-Touch-LCD-1.47-Demo/Firmware/01_factory.bin`
and is flashed at address `0x0`, but a full device backup is preferred.

