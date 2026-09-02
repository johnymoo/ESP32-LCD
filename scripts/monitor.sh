#!/usr/bin/env bash

set -euo pipefail
source "$(dirname "$0")/env.sh"
source "$(dirname "$0")/device.sh"

cd "$PROJECT_ROOT/firmware/touch-demo"
idf.py -p "$ESP32_PORT" monitor

