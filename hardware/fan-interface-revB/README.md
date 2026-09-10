# GB10 fan interface Rev B

Current status (2026-09-09): PCB project ownership has moved to `johnymoo/ESP32-LCD`.
PCB order Y1 is order-complete and awaiting engineering preparation, with NO SMT.
The original 11 BOM items have been purchased at minimum order quantities;
the paid retail order is being picked. Combined cost is CNY 87.03 including shipping.
See [current retail order](retail-order-20260909.md); release-contained
order-status notes retain earlier snapshots and are not current checkout status.
Rev C is deferred in [issue #1](https://github.com/johnymoo/ESP32-LCD/issues/1).

This is the direct-plug carrier for the Waveshare ESP32-S3-Touch-LCD-1.47-M. The display board remains powered and connected to GB10 through its own USB-C cable. The carrier supplies only fan power and signal interfacing.

The design has been finalized in JLCEDA Pro with real LCSC devices and local manufacturing backups. Rev A is the electrical baseline; Rev B changes the ESP32 connection to two direct-insertion 1x11 female headers.

The 2026-09-09 audit corrected the display connector mapping: odd/even vendor
pins form the two rows; vendor pin 8 is 3V3, while pin 6 is GND. See
[display-pinout.md](display-pinout.md). Earlier generated source snapshots
are historical, unvalidated drafts and must not be submitted for fabrication.

The online PCB has a 45 x 30 mm outline with 17.00 mm socket spacing. The
schematic and PCB use real Molex fan headers, a DC5521 jack, and an AO3400A
PWM sink. TACH2 now uses GPIO4 instead of the GPIO3 strapping pin.
Routing, two GND pours, capacitor clearance adjustments and seven top-silkscreen
labels are complete. DFM5 also moves F1 to clear J1 and corrects exposed traces
and silkscreen. JLCEDA schematic DRC at 07:29:29 and PCB DRC at 10:27:50
on 2026-09-09 reported no issues (124 PCB checks). Current manufacturing and
native exports are in [release-20260909-dfm5](release-20260909-dfm5/README.md).
The user supplied fan label photos (0.23 A total at 12 V) and confirmed the Delta
is a standard four-wire fan with tach output. See [fan evidence](reference/fans/README.md).
Online PCB/SMT DFM and assembly preview are complete, with remaining process
alerts explicitly documented for factory review. A separate JLC CPL corrects
C1/D1/Q1/J1 rotation by 180 degrees; reimport verified it without manual rotation.
The user submitted DFM5 PCB order Y1 at 12:15:47 on 2026-09-09 and later completed
checkout. The user chose self-soldering to avoid assembly
charges. Order Y1 was updated to NO SMT; the order list now offers “改为需SMT”
and shows CNY 43 for five bare boards with 48-hour free expedited production.
The saved SMT quote is historical only; do not resume or submit it. See
[hand assembly and purchasing](release-20260909-dfm5/hand-assembly.md).
PCB production-artwork confirmation, delivery, hand assembly and prototype tests remain open.

`bom-review.csv` and the older `native/*rebuild*` outputs are historical starting
points. Use the latest downloaded online project and the current design inputs;
do not regenerate a production board from an old snapshot.

See [design-inputs.md](design-inputs.md) for the electrical topology, starting BOM and acceptance gates.
