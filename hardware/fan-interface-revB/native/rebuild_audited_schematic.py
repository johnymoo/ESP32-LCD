"""Generate a reviewable JLCEDA page from the downloaded project libraries.

Import P1-audited.txt into File Source (no trailing | on the final row).
The source document and component identities are retained for PCB ECO.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
from audit_native import parse

ROOT = Path(__file__).parent
docs = parse(ROOT / 'audit-2026-09-09/schematic/P1.epru')
page = copy.deepcopy(next(d for d in docs if d[0][1]['docType'] == 'SCH_PAGE'))
libs = {d[0][1].get('uuid'): d for d in docs}
attrs = {}
for h, d in page:
    if h['type'] == 'ATTR':
        attrs.setdefault(d['parentId'], {})[d['key']] = d
components = {attrs[h['id']]['Designator']['value']: (h, d)
              for h, d in page if h['type'] == 'COMPONENT'
              and 'Designator' in attrs.get(h['id'], {})}
NETS = {
    'J1.1': 'VIN12_RAW', 'J1.2': 'GND',
    'F1.1': 'VIN12_RAW', 'F1.2': 'VIN12_PROT',
    'D1.1': 'FAN12', 'D1.2': 'VIN12_PROT',
    'C1.1': 'FAN12', 'C1.2': 'GND', 'C2.1': 'FAN12', 'C2.2': 'GND',
    'J2.1': 'GND', 'J2.2': 'FAN12', 'J2.3': 'TACH1_FAN', 'J2.4': 'PWM_BUS',
    'J3.1': 'GND', 'J3.2': 'FAN12', 'J3.3': 'TACH2_FAN', 'J3.4': 'PWM_BUS',
    'R1.1': 'ESP_PWM', 'R1.2': 'PWM_GATE', 'R2.1': 'PWM_GATE', 'R2.2': 'GND',
    'Q1.1': 'PWM_GATE', 'Q1.2': 'GND', 'Q1.3': 'PWM_BUS',
    'R3.1': 'TACH1_FAN', 'R3.2': 'ESP_TACH1',
    'R4.1': 'ESP_TACH1', 'R4.2': '3V3',
    'R5.1': 'TACH2_FAN', 'R5.2': 'ESP_TACH2',
    'R6.1': 'ESP_TACH2', 'R6.2': '3V3',
    'JDISP1.2': 'GND', 'JDISP1.6': 'ESP_PWM',
    'JDISP1.7': 'ESP_TACH1', 'JDISP1.8': 'ESP_TACH2',
    'JDISP2.2': 'GND', 'JDISP2.3': 'GND', 'JDISP2.4': '3V3',
}
positions = {'JDISP1': (260, -450), 'JDISP2': (500, -450),
             'R1': (680, -460), 'Q1': (800, -460), 'R2': (800, -350)}
for ref, (x, y) in positions.items():
    h, d = components[ref]
    dx, dy = x - d['x'], y - d['y']
    d.update(x=x, y=y)
    for a in attrs[h['id']].values():
        if isinstance(a.get('x'), (int, float)):
            a['x'] += dx
        if isinstance(a.get('y'), (int, float)):
            a['y'] += dy

# Only the original six wires existed. Replace their graphics and labels.
old_wires = {h['id'] for h, d in page if h['type'] == 'WIRE'}
out = [(h, d) for h, d in page
       if h['type'] != 'WIRE'
       and not (h['type'] == 'LINE' and d.get('lineGroup') in old_wires)
       and not (h['type'] == 'ATTR' and d.get('parentId') in old_wires)]
review = {}
for key, net in NETS.items():
    ref, num = key.split('.')
    h, d = components[ref]
    symbol = libs[attrs[h['id']]['Symbol']['value']]
    pin_ids = {v['parentId']: v['value'] for hh, v in symbol
               if hh['type'] == 'ATTR' and v.get('key') == 'Pin Number'}
    p = next(v for hh, v in symbol
             if hh['type'] == 'PIN' and pin_ids.get(hh['id']) == num)
    assert not d.get('isMirror'), 'Mirrored symbols need explicit transform support'
    angle = math.radians(d.get('rotation', 0))
    x = round(d['x'] + p['x']*math.cos(angle) + p['y']*math.sin(angle), 6)
    y = round(d['y'] - p['x']*math.sin(angle) + p['y']*math.cos(angle), 6)
    direction = math.radians(p['rotation'] + d.get('rotation', 0))
    ex, ey = round(x - 25*math.cos(direction), 6), round(y + 25*math.sin(direction), 6)
    uid = hashlib.sha256(('RevB-audit-wire:' + key).encode()).hexdigest()[:16]
    out.extend([
        ({'type': 'WIRE', 'id': uid}, {'zIndex': 80}),
        ({'type': 'LINE', 'id': uid+'l'}, {
            'fillColor': None, 'fillStyle': None, 'strokeColor': None,
            'strokeStyle': None, 'strokeWidth': None, 'startX': x, 'startY': y,
            'endX': ex, 'endY': ey, 'lineGroup': uid}),
        ({'type': 'ATTR', 'id': uid+'a'}, {
            'x': ex, 'y': ey, 'rotation': 0, 'color': None,
            'fontFamily': None, 'fontSize': 7, 'fontWeight': None,
            'italic': None, 'underline': None, 'align': 'LEFT_BOTTOM',
            'value': net, 'keyVisible': False, 'valueVisible': True,
            'key': 'NET', 'fillColor': None, 'parentId': uid, 'zIndex': 81})
    ])
    review[key] = {'net': net, 'pin_xy': [x, y], 'stub_end': [ex, ey]}
for i, (h, d) in enumerate(out):
    h.pop('firstTicket', None)
    if i:
        h['ticket'] = i
    else:
        h.pop('ticket', None)

def encode(rows):
    return '|\n'.join(json.dumps(h, separators=(',', ':'), ensure_ascii=False)
                     + '||' + json.dumps(d, separators=(',', ':'), ensure_ascii=False)
                     for h, d in rows)

(ROOT / 'P1-audited.txt').write_text(encode(out))
(ROOT / 'schematic-net-review.json').write_text(json.dumps(review, indent=2))
print(f'Generated {len(components)} components and {len(review)} labeled pins')
