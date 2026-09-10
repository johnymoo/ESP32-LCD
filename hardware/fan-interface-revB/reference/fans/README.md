# Actual fan evidence — 2026-09-09

The user supplied the two label photographs in this directory and confirmed:
“台达也是标准 4 线，支持测速”. Standard four-wire PWM/tach compatibility
is therefore a user-confirmed design input, not an independently measured result.

| Fan | Label rating | Power from label |
|---|---|---|
| Delta AFB0612LB, label suffix -Cb32, 60 mm | DC12V 0.10A | 1.20 W |
| Thermalright TL-C14C, 140 mm | DC12V 0.13AMP, 1500RPM PWM, 4PIN PWM | 1.56 W |
| One of each | 12 V, 0.23 A total | 2.76 W total |

The photos do not specify startup current or tach pulses per revolution. Those
remain prototype validation items. Do not assume 1500 RPM for the Delta fan.

## Connection

Preferred: TL-C14C to J2/FAN1, Delta to J3/FAN2. Both receive continuous 12 V
and the same open-drain PWM signal; each tach output reaches a separate ESP32
input. Four-pin order is 1 GND, 2 +12V, 3 TACH, 4 PWM.

The user's daisy-chain alternative is supported when the TL-C14C pass-through
duplicates GND, +12V and PWM, but returns only one fan's tach signal. This is
electrically parallel power, not series motors. Never join both tach outputs:
the resulting pulses cannot identify either fan's speed. With one PCB connector
used, the firmware must disable the unused tach alarm and cannot independently
detect a stalled fan whose tach signal is not returned. Verify which connector
has pin 3 populated before using the pass-through.

## Power and prototype checks

The populated F1 is C46641031, SMD1206-150-16 (1.5 A hold at its specified
reference ambient, 16 V rated). Its rating is well above the combined label
current. It is branch fault protection, not individual motor overload protection.
Check startup, hot-ambient derating and time-to-trip using the part datasheet and
the built prototype. D1 is SS34; measure the actual downstream fan voltage and
diode temperature under load.

Use the user's 12 V-capable USB-C charger through a cable/trigger that explicitly
requests 12 V, terminating in a center-positive DC5521 plug. A passive USB-C
cable does not by itself negotiate 12 V. Check the plug voltage before connecting.
The ESP32 display remains separately USB-C powered. VBUS/VBAT are not connected
through the carrier.

No fan temperature or startup test has been performed on physical hardware.
