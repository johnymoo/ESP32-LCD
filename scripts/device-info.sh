#!/usr/bin/env bash

set -euo pipefail
source "$(dirname "$0")/env.sh"
source "$(dirname "$0")/device.sh"

ls -l "$ESP32_PORT"
esptool.py --chip esp32s3 --port "$ESP32_PORT" chip_id
esptool.py --chip esp32s3 --port "$ESP32_PORT" flash_id

