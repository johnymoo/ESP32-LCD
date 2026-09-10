# ESP32-S3-Touch-LCD-1.47-M carrier pinout

Verified 2026-09-09 against the vendor schematic in
[johnymoo/ESP32-LCD](https://github.com/johnymoo/ESP32-LCD) and the
[annotated back-side photo](https://www.waveshare.com/w/upload/3/3f/ESP32-S3-Touch-LCD-1.47-details-inter.jpg).
Local originals are under `reference/waveshare/`.

P1 numbers the physical rows by odd/even pins, not consecutive blocks of
eleven. JDISP1 accepts odd P1 pins and JDISP2 accepts even P1 pins. Each
carrier socket is numbered 1 through 11 from the USB end.

Looking down into the carrier socket openings with the display USB-C end
to the left, JDISP1 is the upper row and JDISP2 is the lower row. The vendor
back-side photo must be mirrored to obtain this mating-side view.

| Socket position from USB end | P1 odd pin | JDISP1 | P1 even pin | JDISP2 |
|---:|---:|---|---:|---|
| 1 | 1 | VBUS (NC) | 2 | VBAT (NC) |
| 2 | 3 | GND | 4 | GND |
| 3 | 5 | TXD GPIO43 (NC) | 6 | GND |
| 4 | 7 | RXD GPIO44 (NC) | 8 | 3V3 |
| 5 | 9 | EN (NC) | 10 | SCL GPIO41 (NC) |
| 6 | 11 | GPIO1 / ESP_PWM | 12 | SDA GPIO42 (NC) |
| 7 | 13 | GPIO2 / ESP_TACH1 | 14 | GPIO11 (NC) |
| 8 | 15 | GPIO3 (NC; JTAG strapping) | 16 | GPIO10 (NC) |
| 9 | 17 | GPIO4 / ESP_TACH2 | 18 | GPIO9 (NC) |
| 10 | 19 | GPIO5 (NC) | 20 | GPIO8 (NC) |
| 11 | 21 | GPIO6 (NC) | 22 | GPIO7 (NC) |

NC means deliberately unconnected on the carrier. Connect P1.3/4/6 to
GND, P1.8 to the tach pull-up rail, and P1.11/13/17 to GPIO1/2/4. VBUS and
VBAT stay isolated from the fan power rail. The display retains USB-C power.

Mechanical constraints from `ESP32-S3-Touch-LCD-1.47_20250411.pdf`:

- Display envelope: 44.50 x 24.55 mm.
- Socket pitch: 2.54 mm; eleven contacts span 25.40 mm.
- Parallel row center distance: exactly 17.00 mm (669.2913 mil).
- First contact center is 12.60 mm from the USB-end envelope edge
  (2.75 mm mounting-hole inset + 9.85 mm offset).
- Contact rows are approximately 3.77 mm from the long envelope edges.
- Mounting-hole centers: 39.00 x 17.78 mm; M2.
- Selected female header C41417323 has an 8.5 mm insulation height.
  The drawing's 10.60 mm dimension is not the assembled carrier height.

Audit correction: earlier drafts assigned P1.6 to 3V3 (it is GND), omitted
the third ground, shifted several even pins, and split rows as 1-11/12-22.
Those drafts are not valid fabrication inputs.
