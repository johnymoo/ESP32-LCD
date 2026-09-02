#!/usr/bin/env bash

set -euo pipefail
source "$(dirname "$0")/env.sh"
source "$(dirname "$0")/device.sh"

if [[ $# -ne 1 || ! -f "$1" ]]; then
    echo "Usage: $0 <16MiB-flash-backup.bin>" >&2
    exit 2
fi

size="$(stat -c %s "$1")"
if [[ "$size" -ne 16777216 ]]; then
    echo "Refusing restore: expected 16777216 bytes, got $size" >&2
    exit 2
fi

esptool.py --chip esp32s3 --port "$ESP32_PORT" --baud 460800 \
    write_flash 0 "$1"

