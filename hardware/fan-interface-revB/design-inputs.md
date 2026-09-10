# Fan interface Rev B design inputs

Status: 2026-09-09 audit corrected the earlier row split and 3V3 assignment.
Online schematic, device standardization, initial routing and ground pours are
complete. Latest PCB DRC at 2026-09-09 10:27:50 reported no issues across 124
checks; schematic DRC at 07:29:29 reported zero errors/warnings. Manufacturing
exports and native backups are in `release-20260909-dfm5/`. Online PCB/SMT DFM
and model/polarity preview have been performed; process alerts and factory
assembly acceptance remain explicit in that release's `order-readiness.md`.
Physical prototype validation remains open.

## Verified display reference

Source repository: <https://github.com/johnymoo/ESP32-LCD>

Local reference files:

- `reference/waveshare/ESP32-S3-Touch-LCD-1.47-Schematic.pdf`
- `reference/waveshare/ESP32-S3-Touch-LCD-1.47_20250411.pdf`
- `reference/waveshare/HARDWARE.md`

The mechanical drawing gives a board envelope of 44.50 x 24.55 mm, two parallel
headers with 17.00 mm row center distance, 2.54 mm pitch, and 25.40 mm contact
span (10 intervals). The display module height is approximately 10.60 mm with
the supplied headers. The 22-pin header pinout is:

| Header pin | Board signal | ESP32-S3 GPIO / rail |
|---:|---|---|
| 1 | VBUS | USB 5 V |
| 2 | VBAT | battery rail; leave unused |
| 3 | GND | ground |
| 4 | GND | ground |
| 5 | ESP_TXD | GPIO43; leave unused |
| 6 | GND | ground |
| 7 | ESP_RXD | GPIO44; leave unused |
| 8 | VCC3V3 | 3.3 V |
| 9 | ESP_EN | reset/enable; leave unused |
| 10 | SCL | GPIO41; touch/I2C |
| 11 | IO1 | GPIO1; PWM candidate |
| 12 | SDA | GPIO42; touch/I2C |
| 13 | IO2 | GPIO2; TACH1 candidate |
| 14 | IO11 | GPIO11; spare |
| 15 | IO3 | GPIO3; unused JTAG strapping pin |
| 16 | IO10 | GPIO10; spare |
| 17 | IO4 | GPIO4; TACH2 |
| 18 | IO9 | GPIO9; spare |
| 19 | IO5 | GPIO5; spare |
| 20 | IO8 | GPIO8; spare |
| 21 | IO6 | GPIO6; spare |
| 22 | IO7 | GPIO7; spare |

P1 odd pins map to JDISP1 and P1 even pins map to JDISP2. The carrier uses
JDISP1.2 = GND, .6 = GPIO1, .7 = GPIO2, .9 = GPIO4; JDISP2.2/.3 = GND,
.4 = 3V3. See `display-pinout.md` for the mating-side orientation.

The vendor schematic's pin-out block exposes GPIO1 through GPIO11. The working
carrier assignment is GPIO1 = PWM, GPIO2 = TACH1, GPIO4 = TACH2. GPIO3 and
GPIO5-GPIO11 remain unconnected on the first revision. Do not route VBAT.
GPIO3 was moved out of the tach circuit because the ESP32-S3 datasheet v2.2,
section 3, identifies it as the JTAG source strapping input.

## Manufacturing target

- Two-layer FR-4, 1.6 mm, standard JLCPCB process.
- Final manufacturing master: JLCEDA Pro project.
- Local audit copy: native EPRO2/EPRU, Gerber/drill and BOM/CPL snapshots.
  No validated KiCad conversion has been produced.
- Board outline: 45 x 30 mm.
- Assembly: through-hole connectors and socket headers; small passive and MOSFET parts may be assembled by JLCPCB.

## Electrical architecture

```text
12 V DC input -> fuse -> reverse-polarity protection -> FAN_12V
                                                   ├─ FAN1 pin 2
                                                   └─ FAN2 pin 2

ESP32 3V3/GND -------------------------------> tach pull-ups / signal reference
ESP32 PWM -> gate resistor -> AO3400A open-drain -> FAN1/FAN2 PWM pins
FAN1 TACH -> series resistor -> ESP32 TACH1
FAN2 TACH -> series resistor -> ESP32 TACH2
```

- The display's USB-C supplies the ESP32/display.
- The PCB does not feed 12 V or 5 V into the display.
- Fan grounds and ESP32 signal ground must be common.
- PWM is one shared 25 kHz open-drain bus.
- TACH1 and TACH2 remain separate.
- PWM GPIO duty is inverted by Q1: fan high-time duty = 1 - GPIO high-time duty.
  At reset, R2 keeps Q1 off so the fan PWM inputs float high (full speed for
  compatible four-wire fans). Firmware needs telemetry timeout/full-speed fallback.
- The fan connectors follow the standard target order: GND / +12V / TACH / PWM.

Actual fans: Delta AFB0612LB (-Cb32 label), 60 mm, 12 V 0.10 A; Thermalright
TL-C14C, 140 mm, 12 V 0.13 A, 1500 RPM PWM. The user confirmed the Delta's
standard four-wire/tach interface. Combined label current is 0.23 A (2.76 W).
The two fan motors receive parallel 12 V power. Optional daisy chaining must
return only one tach output. Separate J2/J3 connections provide both speeds.
See `reference/fans/README.md` for evidence and the prototype test boundary.

## Display connector requirement

The board must expose two parallel 1x11, 2.54 mm female headers so the ESP32-S3-Touch-LCD-1.47-M can plug directly into the carrier. Before assigning any GPIO, verify from the exact -M documentation:

1. Header pitch and row-to-row center distance.
2. Pin numbering direction and board-edge offsets.
3. Complete 22-pin GPIO/power map.
4. GPIO already used by LCD, touch controller, USB, boot straps and TF/flash.
5. USB-C, buttons, display glass and cable keep-outs.

No GPIO number is considered verified until it is supported by the exact -M schematic or pin table.

## Component starting set

Reuse the electrically reviewed Rev A values unless the exact fan or connector measurement requires a change:

| Ref | Function | Starting value / part |
|---|---|---|
| Q1 | PWM sink | AO3400A, SOT-23, LCSC C20917; RDS(on) specified at VGS=2.5 V |
| R1 | gate series | 220 Ohm, C22962 |
| R2 | gate pulldown | 100 kOhm |
| R3/R5 | tach series | 220 Ohm |
| R4/R6 | tach pull-up | 4.7 kOhm to ESP32 3V3 |
| C1 | fan rail bulk | 100 uF, >=25 V |
| C2 | local bypass | 100 nF |
| F1 | 12 V protection | resettable fuse sized after startup-current test |
| J2/J3 | fan output | Molex 470531000, C240840, bottom-mounted |
| J1 | 12 V input | DC-005-5A-2.0, C381116, center-positive; pin 3 switch NC; bottom-mounted |
| JDISP | display interface | two 1x11, 2.54 mm female headers |

## Pre-order acceptance gates

- Exact display pin map and mechanical drawing attached to the project.
- Fan 4-pin order and tach electrical levels measured or confirmed from datasheets.
- Schematic ERC/DRC clean.
- PCB DRC clean.
- 3D/footprint check confirms the display can be inserted without USB-C or button collision.
- BOM contains real LCSC/JLC part numbers and assembly-compatible footprints.
- Gerber, drill, BOM and CPL exports open and match the JLCEDA project.
- Bench test plan covers 12 V polarity, fan startup, PWM open/high impedance fallback, and both tach channels.
