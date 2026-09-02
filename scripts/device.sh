#!/usr/bin/env bash

set -e

DEVICE_GLOB=/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_*-if00
shopt -s nullglob
devices=($DEVICE_GLOB)
shopt -u nullglob

if [[ ${#devices[@]} -ne 1 ]]; then
    echo "Expected one Espressif USB JTAG/serial device, found ${#devices[@]}" >&2
    exit 1
fi

ESP32_PORT="${devices[0]}"
export ESP32_PORT

