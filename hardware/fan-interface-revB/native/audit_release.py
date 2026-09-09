"""Audit exported native PCB against the separately reviewed RevB contract.

This does not replace JLCEDA DRC or a physical fan acceptance test. It checks
the pin mapping, device identity, routing presence, sockets and mounting holes.
Usage: python3 audit_release.py path/to/PCB1.epru
"""
import json
import argparse
import math
import sys
from collections import Counter
from pathlib import Path

from audit_native import parse

EXPECTED = {
    'J1.1': 'VIN12_RAW', 'J1.2': 'GND',
    'F1.1': 'VIN12_RAW', 'F1.2': 'VIN12_PROT',
    'D1.1': 'FAN12', 'D1.2': 'VIN12_PROT',
    'C1.1': 'FAN12', 'C1.2': 'GND', 'C2.1': 'FAN12', 'C2.2': 'GND',
    'J2.1': 'GND', 'J2.2': 'FAN12', 'J2.3': 'TACH1_FAN', 'J2.4': 'PWM_BUS',
    'J3.1': 'GND', 'J3.2': 'FAN12', 'J3.3': 'TACH2_FAN', 'J3.4': 'PWM_BUS',
    'Q1.1': 'PWM_GATE', 'Q1.2': 'GND', 'Q1.3': 'PWM_BUS',
    'R1.1': 'ESP_PWM', 'R1.2': 'PWM_GATE', 'R2.1': 'PWM_GATE', 'R2.2': 'GND',
    'R3.1': 'TACH1_FAN', 'R3.2': 'ESP_TACH1', 'R4.1': 'ESP_TACH1', 'R4.2': '3V3',
    'R5.1': 'TACH2_FAN', 'R5.2': 'ESP_TACH2', 'R6.1': 'ESP_TACH2', 'R6.2': '3V3',
    'JDISP1.2': 'GND', 'JDISP1.6': 'ESP_PWM', 'JDISP1.7': 'ESP_TACH1',
    'JDISP1.9': 'ESP_TACH2', 'JDISP2.2': 'GND', 'JDISP2.3': 'GND', 'JDISP2.4': '3V3',
}
PARTS = {
    'J1': 'C381116', 'J2': 'C240840', 'J3': 'C240840',
    'JDISP1': 'C41417323', 'JDISP2': 'C41417323', 'Q1': 'C20917',
    'R1': 'C22962', 'R2': 'C25803', 'R3': 'C22962', 'R4': 'C23162',
    'R5': 'C22962', 'R6': 'C23162', 'C1': 'C970685', 'C2': 'C14663',
    'D1': 'C8678', 'F1': 'C46641031',
}


def audit(path):
    docs = parse(path)
    board = next(d for d in docs if d[0][1]['docType'] == 'PCB')
    libs = {d[0][1].get('uuid'): d for d in docs}
    attrs = {}
    for h, d in board:
        if h['type'] == 'ATTR':
            attrs.setdefault(d['parentId'], {})[d['key']] = d.get('value')
    components = {attrs[h['id']]['Designator']: (h, d)
                  for h, d in board if h['type'] == 'COMPONENT'}
    ids = {h['id']: ref for ref, (h, d) in components.items()}
    actual = {}
    errors = []
    for h, d in board:
        if h['type'] == 'PAD_NET':
            _, comp, pin, *_ = json.loads(h['id'])
            if d.get('padNet'):
                actual[f'{ids[comp]}.{pin}'] = d['padNet']
    for key in sorted(set(actual) | set(EXPECTED)):
        if actual.get(key) != EXPECTED.get(key):
            errors.append(f'{key}: actual={actual.get(key)}, expected={EXPECTED.get(key)}')
    bom = []
    for ref, (h, d) in sorted(components.items()):
        a = attrs[h['id']]
        meta = next(v for hh, v in libs[a['Device']] if hh['type'] == 'META')
        merged = meta['attributes'] | {k: v for k, v in a.items() if v is not None}
        if merged.get('Supplier Part') != PARTS.get(ref):
            errors.append(f'{ref}: unexpected part {merged.get("Supplier Part")}')
        bom.append({'ref': ref, 'lcsc': merged.get('Supplier Part'),
                    'part': merged.get('Manufacturer Part'),
                    'side': 'bottom' if d['layerId'] == 2 else 'top',
                    'xy_mm': [round(d['x']*.0254, 4), round(d['y']*.0254, 4)],
                    'angle_deg': d['angle']})
    if set(components) != set(PARTS):
        errors.append('Unexpected or missing component designators')
    sockets = [components[r][1] for r in ['JDISP1', 'JDISP2']]
    row_spacing = abs(sockets[0]['y'] - sockets[1]['y']) * .0254
    if abs(row_spacing - 17) > .001 or abs(sockets[0]['x']-sockets[1]['x']) > .001:
        errors.append('Display socket positions do not match 17 mm parallel rows')
    for ref in ['JDISP1', 'JDISP2']:
        h, d = components[ref]
        pads = [v for hh, v in libs[attrs[h['id']]['Footprint']] if hh['type'] == 'PAD']
        pads.sort(key=lambda p: int(p['num']))
        if len(pads) != 11 or d['layerId'] != 1 or d['angle'] != 0:
            errors.append(ref + ': wrong socket count/side/angle')
        for p, q in zip(pads, pads[1:]):
            pitch = math.hypot(p['centerX']-q['centerX'], p['centerY']-q['centerY'])*.0254
            if abs(pitch-2.54) > .001:
                errors.append(ref + ': wrong socket pitch')
    holes = []
    for h, d in board:
        if h['type'] == 'FILL' and d.get('layerId') == 12:
            for p in d.get('path', []):
                if p[0] == 'CIRCLE':
                    holes.append([round(x*.0254, 4) for x in p[1:]])
    expected_holes = [[x, y, 1.1] for x in [2.75, 41.75] for y in [8.835, 26.615]]
    if sorted(holes) != sorted(expected_holes):
        errors.append('Mounting hole locations/diameters do not match module')
    counts = Counter(h['type'] for h, d in board)
    pours = [d for h, d in board if h['type'] == 'POUR']
    if {(d['layerId'], d['netName']) for d in pours} != {(1, 'GND'), (2, 'GND')}:
        errors.append('Expected top and bottom GND pours')
    if not counts['LINE']:
        errors.append('No PCB tracks exported')
    return {'source': str(Path(path).resolve()), 'errors': errors,
            'electrical_pin_count': len(actual), 'socket_spacing_mm': row_spacing,
            'holes_xy_radius_mm': holes, 'record_counts': dict(counts), 'bom': bom,
            'limits': ['Does not replace DRC, DFM or electrical fan compatibility checks',
                       'Fan standard four-wire compatibility is user-confirmed; physical startup/tach tests remain']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pcb')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit(args.pcb)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
        print(json.dumps({'errors': result['errors'], 'report': str(args.output)}))
    else:
        print(encoded)
    raise SystemExit(bool(result['errors']))
