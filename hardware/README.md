# Fan interface PCB project

Canonical repository: `johnymoo/ESP32-LCD`. This project was migrated from
`johnymoo/Nvidia-DGX/dual-gb10-enclosure/electronics` on 2026-09-09 at the user's
request. The DGX repository owns enclosure mechanics and integration references;
this repository owns PCB schematics, layout, BOM, manufacturing exports and revisions.

The complete hardware import is included in
[PR #2](https://github.com/johnymoo/ESP32-LCD/pull/2) on branch
`pcb/fan-interface-migration`, alongside the fabrication skill and retrospective.
Original manufacturing files retain their bytes. The reviewed numeric false
positives and user-authorized, one-commit privacy-hook exception are recorded in
[import review](import-review-20260910.md); global hook settings are unchanged.

- [Rev B](fan-interface-revB/README.md): active direct-plug design for the
  ESP32-S3-Touch-LCD-1.47-M; current manufacturing baseline is
  [release-20260909-dfm5](fan-interface-revB/release-20260909-dfm5/README.md).
  Current purchasing status is [Rev B retail order](fan-interface-revB/retail-order-20260909.md),
  which supersedes order-status snapshots inside the frozen manufacturing release.
- [Rev A](fan-interface-revA/README.md): historical electrical/layout inputs;
  do not fabricate these drafts in place of Rev B DFM5.
- [Rev C issue #1](https://github.com/johnymoo/ESP32-LCD/issues/1): backlog only,
  larger packages and fewer passives if Rev B proves unsuitable for hand assembly.

Rev B uses the original 11 line items/16 components per board. No Rev C package,
substitution or omitted part is approved for this run. Order bare PCB plus loose
components, with no SMT service. Assemble and validate one board before the rest.
PCB Y1 is now order-complete and awaiting engineering preparation, at CNY 43
for five boards. The original loose parts are paid and being picked, at CNY 44.03
including shipping and discounts; combined total is CNY 87.03.
Production-artwork approval and physical testing are distinct
from this order review and must still be checked at their respective stages.

Imported release files and their original SHA256SUMS retain their manufacturing
provenance. Absolute paths inside historical audit JSON identify original sources;
they are not the current checkout path. Older releases and native reconstruction
scripts are historical evidence, not alternate fabrication masters.

Hardware files do not implement fan-control firmware. Existing display/dashboard
firmware remains in `firmware/`; do not flash or modify it merely to migrate PCB files.
