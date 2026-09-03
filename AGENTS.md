# ESP32 Touch Display Development Instructions

## Purpose

This repository is the reference implementation for Waveshare ESP32-S3 touch
displays connected to a Linux development host. Reuse its project structure,
scripts, documentation pattern, dashboard UI, and verification workflow for
similar boards. Do not assume that pin assignments or panel drivers are shared
between product variants.

## Repository layout

- `firmware/touch-demo`: primary ESP-IDF application and locked dependencies.
- `firmware/touch-demo/components`: vendor BSP, LCD, touch, and UI components.
- `scripts`: device discovery, build, backup, flash, monitor, and restore tools.
- `server`: read-only GB10 status endpoint and browser display mirror.
- `docs/HARDWARE.md`: verified board specifications and pin map.
- `docs/SETUP.md`: installed toolchain, commands, and recovery procedure.
- `docs/SOURCES.md`: official documentation, direct downloads, versions, and
  checksums.
- `docs/CLUSTER-DASHBOARD.md`: dashboard data contract and service operations.
- `vendor/waveshare`: extracted vendor reference packages and factory firmware.

## Current hardware baseline

- Board: Waveshare ESP32-S3-Touch-LCD-1.47, ESP32-S3R8.
- Flash / PSRAM: 16 MiB flash and 8 MiB octal PSRAM.
- LCD: JD9853, native 172 x 320.
- Touch: AXS5106L.
- Dashboard orientation: 320 x 172 landscape, rotation 90 degrees.
- Display transform: swap X/Y, mirror X, and apply panel gap `(0, 34)`.
- Stable USB path: `/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_*-if00`.

These values are specific to this board revision. Verify them from the vendor
BSP and a connected device before applying them to another display.

## Development environment

The canonical checkout is
`gb10-2:/home/admin/project/esp32-s3-touch-1.47`. ESP-IDF v5.5.2 and its tools
are installed under the ignored `.tools` directory. Project scripts load that
environment automatically. The optional LAN proxy is
`http://192.168.88.2:7890`; set `ESP32_USE_PROXY=0` to disable it.

Use the project wrappers:

```bash
./scripts/device-info.sh
./scripts/build.sh
./scripts/backup-flash.sh
./scripts/flash.sh
./scripts/monitor.sh
```

Exit the serial monitor with `Ctrl+]`.

## Adapting this project to a similar display

1. Record the exact product name, board revision, USB identity, MCU package,
   flash size, and PSRAM size. Capture a full flash backup before overwriting a
   new device.
2. Download the official demo, schematic, and mechanical files. Add their
   direct URLs, retrieval date, and SHA-256 values to `docs/SOURCES.md`.
3. Start from `firmware/touch-demo`, but replace the board-specific BSP and
   panel components with those from the new product's official package.
4. Verify every GPIO in `docs/HARDWARE.md`. Never infer pin compatibility from
   display size or enclosure similarity.
5. Set native resolution, LVGL resolution, color byte order, panel gap,
   rotation, mirroring, and touch coordinate transform from vendor evidence.
   Display and touch rotation must be tested together.
6. Update flash, PSRAM, and partition settings in `sdkconfig.defaults`, then
   regenerate the build configuration through `idf.py`; do not copy a generated
   `sdkconfig` across unlike boards.
7. Build, flash, and capture bounded serial evidence. Check the complete screen
   visually and test touch points near all four corners before declaring the
   adaptation complete.

Prefer copying known-good board components over rewriting controller protocols.
Keep local changes to vendor components small and document why they are needed.

## Dashboard and status service

The firmware reads `http://192.168.88.181:9108/status` every five seconds. The
browser mirror is served at `http://192.168.88.181:9108/` and refreshes every
two seconds. The service is deployed on `gb10` as the user unit
`cluster-display-status.service`.

The status service is read-only. Do not restart, stop, or reconfigure Qwen,
DeepSeek, trading, lexdata, or unrelated GB10 workloads while changing the
display. GPU memory fields are unavailable on GB10 and must not be invented.

## Secrets and generated files

- Keep real Wi-Fi credentials only in the ignored
  `firmware/touch-demo/main/wifi_credentials.h`.
- Update `wifi_credentials.example.h` with placeholders only.
- Never commit flash backups, passwords, keys, tokens, build output, `.tools`,
  or Python cache files.
- Before committing, run `git diff --check`, inspect staged files, and verify
  that `wifi_credentials.h` remains ignored.

## Acceptance checks

A firmware change is complete only when:

- `./scripts/build.sh` succeeds;
- `./scripts/flash.sh` writes and verifies the image;
- serial logs show the expected chip, PSRAM, LCD, touch, Wi-Fi, and application
  startup without aborts, Guru Meditation, or repeated bus errors;
- the full display is correctly oriented with no clipped text;
- touch coordinates match the display orientation when touch is used;
- live status updates succeed for at least two refresh cycles;
- `/health`, `/status`, and the browser mirror remain available when server
  code changes; and
- protected GB10 services remain healthy.
