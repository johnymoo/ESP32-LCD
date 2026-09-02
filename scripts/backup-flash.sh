#!/usr/bin/env bash

set -euo pipefail
source "$(dirname "$0")/env.sh"
source "$(dirname "$0")/device.sh"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="$PROJECT_ROOT/firmware/backups/${timestamp}-flash-16MiB.bin"
mkdir -p "$(dirname "$backup")"
esptool.py --chip esp32s3 --port "$ESP32_PORT" --baud 460800 \
    read_flash 0 0x1000000 "$backup"
sha256sum "$backup" | tee "$backup.sha256"

