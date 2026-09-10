"""Reconcile unmodified JLCEDA BOM/CPL and drill exports with the native PCB."""
import csv
import io
import json
import re
import sys
from pathlib import Path
from audit_native import parse
from audit_release import audit, PARTS

root = Path(sys.argv[1])
pcb = root / 'native-pcb/PCB1.epru'
report = audit(pcb)
errors = report['errors']
board = next(d for d in parse(pcb) if d[0][1]['docType'] == 'PCB')
canvas = next(d for h, d in board if h['type'] == 'CANVAS')
origin = [canvas['originX']*.0254, canvas['originY']*.0254]
bom_rows = list(csv.DictReader(io.StringIO(
    (root/'GB10-Fan-RevB-BOM-20260909.csv').read_text(encoding='utf-8-sig'))))
bom = {}
for row in bom_rows:
    refs = row['Designator'].split(',')
    if len(refs) != int(row['Quantity']):
        errors.append('BOM quantity mismatch: '+row['Designator'])
    for ref in refs:
        if ref in bom:
            errors.append('Duplicate BOM ref: '+ref)
        bom[ref] = row['Supplier Part']
if bom != PARTS:
    errors.append('Exported BOM does not match reviewed 16-part contract')
cpl_rows = list(csv.DictReader(io.StringIO(
    (root/'GB10_Fan_RevB_CPL_20260909.csv').read_text(encoding='utf-16')), delimiter='\t'))
cpl = {r['Designator']: r for r in cpl_rows}
if len(cpl_rows) != 16 or set(cpl) != set(PARTS):
    errors.append('CPL has missing, duplicated or unexpected refs')
for part in report['bom']:
    ref = part['ref']
    if ref not in cpl:
        continue
    row = cpl[ref]
    if row['Layer'] != ('B' if part['side'] == 'bottom' else 'T'):
        errors.append('CPL side mismatch: '+ref)
    for axis, label in enumerate(['Mid X', 'Mid Y']):
        actual = float(row[label].removesuffix('mm'))
        expected = part['xy_mm'][axis] - origin[axis]
        if abs(actual-expected) > .002:
            errors.append(f'CPL coordinate mismatch {ref} {label}: {actual} vs {expected}')
    if float(row['Rotation']) != part['angle_deg']:
        errors.append('CPL rotation mismatch: '+ref)
    if row['SMD'] != ('No' if ref.startswith('J') else 'Yes'):
        errors.append('CPL mounting style mismatch: '+ref)

npth = (root/'gerber/Drill_NPTH_Through.DRL').read_text()
tools = dict(re.findall(r'^(T\d+)C([\d.]+)', npth, re.M))
holes, tool = [], None
for line in npth.splitlines():
    if line in tools:
        tool = line
    m = re.fullmatch(r'X(-?[\d.]+)Y(-?[\d.]+)', line)
    if m:
        holes.append([round(float(m[1])+origin[0], 3),
                      round(float(m[2])+origin[1], 3), round(float(tools[tool]), 3)])
mounts = sorted(h for h in holes if h[2] == 2.2)
if mounts != sorted([[x, y, 2.2] for x in [2.75, 41.75] for y in [8.835, 26.615]]):
    errors.append('NPTH mounting hole mismatch')
if sum(h[2] == 1.3 for h in holes) != 2:
    errors.append('Expected two 1.3 mm fan connector locating holes')
silks = [d for h,d in board if h['type'] == 'STRING']
expected_labels = {'GB10 FAN B','12V CENTER+','FAN1','FAN2','1:G 2:+ 3:T 4:P','USB <','1.47-M USB <'}
if {d['text'] for d in silks} != expected_labels or any(d['layerId'] != 3 for d in silks):
    errors.append('Silkscreen labels or layers differ from reviewed set')
result = {'errors': errors, 'bom_line_count':len(bom_rows), 'component_count':len(bom),
          'cpl_components':len(cpl_rows), 'smd_components':sum(r['SMD']=='Yes' for r in cpl_rows),
          'through_hole_components':sum(r['SMD']=='No' for r in cpl_rows),
          'cpl_format':'JLCEDA native UTF-16LE tab-separated CSV',
          'gerber_and_cpl_origin_mm': origin, 'npth_holes_xy_diameter_mm':holes,
          'silkscreen_labels':sorted(expected_labels),
          'limits':['File reconciliation is not DFM, assembly approval or a physical test.',
                    'Bottom rotations are native JLCEDA values; final factory placement preview must be reviewed.']}
encoded = json.dumps(result, ensure_ascii=False, indent=2)
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(encoded+'\n')
print(encoded)
raise SystemExit(bool(errors))
