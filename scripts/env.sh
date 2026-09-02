#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PROJECT_ROOT
export IDF_TOOLS_PATH="$PROJECT_ROOT/.tools/espressif"
export IDF_SKIP_CHECK_SUBMODULES=1

if [[ "${ESP32_USE_PROXY:-1}" == "1" ]]; then
    export HTTP_PROXY="${HTTP_PROXY:-http://192.168.88.2:7890}"
    export HTTPS_PROXY="${HTTPS_PROXY:-http://192.168.88.2:7890}"
    export http_proxy="${http_proxy:-$HTTP_PROXY}"
    export https_proxy="${https_proxy:-$HTTPS_PROXY}"
fi

IDF_EXPORT="$PROJECT_ROOT/.tools/esp-idf/export.sh"
if [[ ! -r "$IDF_EXPORT" ]]; then
    echo "ESP-IDF is missing: $IDF_EXPORT" >&2
    exit 1
fi

# shellcheck disable=SC1090
source "$IDF_EXPORT" >/dev/null

