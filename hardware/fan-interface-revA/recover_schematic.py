"""Build a reviewable SCH_PAGE repair from the actual JLCEDA source export.

Preserves placed device identities and library links. Output is applied using
JLCEDA's File Source UI; the generator does not access a browser or cloud API.
The output still requires online SCH DRC and subsequent PCB synchronization.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import zipfile


def parse(text):
    docs = []
    for line in text.splitlines():
        if not line.strip():
            continue
        a, b = line.removesuffix('|').split('||', 1)
        if not b:
            continue  # Export tombstone for an object already deleted online.
        h, d = json.loads(a), json.loads(b)
        if h['type'] == 'DOCHEAD':
            docs.append([])
        docs[-1].append((h, d))
    return docs


def encode(rows):
    return '\n'.join(json.dumps(h, separators=(',', ':'), ensure_ascii=False) + '||' +
                     json.dumps(d, separators=(',', ':'), ensure_ascii=False) + '|'
                     for h, d in rows) + '\n'


NETS = {
    'VIN12_RAW': ['J1.1', 'F1.1'],
    'VIN12_PROT': ['F1.2', 'D1.2'],
    'FAN12': ['D1.1', 'J2.2', 'J3.2', 'C1.1', 'C2.1'],
    'GND': ['J1.2', 'J2.1', 'J3.1', 'J4.2', 'Q1.2', 'C1.2', 'C2.2', 'R2.2'],
    'ESP_PWM': ['J4.3', 'R1.1'],
    'PWM_GATE': ['R1.2', 'Q1.1', 'R2.1'],
    'PWM_BUS': ['Q1.3', 'J2.4', 'J3.4'],
    'TACH1_FAN': ['J2.3', 'R3.1'],
    'ESP_TACH1': ['R3.2', 'J4.4', 'R4.1'],
    'TACH2_FAN': ['J3.3', 'R5.1'],
    'ESP_TACH2': ['R5.2', 'J4.5', 'R6.1'],
    '3V3': ['J4.1', 'R4.2', 'R6.2'],
}

PLACEMENT = {
    'J1': (150, -680, 0), 'F1': (330, -685, 0),
    'D1': (530, -685, 180), 'C1': (730, -685, 0), 'C2': (930, -685, 0),
    'J4': (170, -470, 0), 'R1': (360, -480, 0),
    'Q1': (570, -480, 0), 'R2': (360, -380, 0),
    'J2': (980, -500, 0), 'J3': (980, -390, 0),
    'R3': (250, -250, 0), 'R4': (460, -250, 0),
    'R5': (730, -250, 0), 'R6': (940, -250, 0),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('backup', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    with zipfile.ZipFile(args.backup) as z:
        name = next(n for n in z.namelist() if n.endswith('.epru'))
        docs = parse(z.read(name).decode())
    libraries = {r[0][1]['uuid']: r for r in docs}
    original = next(r for r in docs if r[0][1]['docType'] == 'SCH_PAGE')
    page = copy.deepcopy(original)
    attrs = {}
    for h, d in page:
        if h['type'] == 'ATTR':
            attrs.setdefault(d['parentId'], {})[d['key']] = d
    components = {attrs[h['id']]['Designator']['value']: (h, d)
                  for h, d in page if h['type'] == 'COMPONENT'
                  and 'Designator' in attrs.get(h['id'], {})}
    assert set(components) == set(PLACEMENT)
    component_ids = {h['id'] for h, d in page if h['type'] == 'COMPONENT'}
    # Drop the known malformed wire, orphan labels and editor placeholders.
    page = [(h, d) for h, d in page
            if h['type'] not in ('WIRE', 'LINE', 'ELE_PLACEHOLDER')
            and not (h['type'] == 'ATTR' and d.get('parentId') not in component_ids)]
    pins = {}
    for ref, (h, c) in components.items():
        a = attrs[h['id']]
        x, y, rotation = PLACEMENT[ref]
        dx, dy = x - c['x'], y - c['y']
        for d in a.values():
            if d.get('x') is not None: d['x'] += dx
            if d.get('y') is not None: d['y'] += dy
        c.update(x=x, y=y, rotation=rotation, isMirror=False)
        # Use explicit footprint references inherited from the actual device.
        device = libraries[a['Device']['value']]
        metadata = next(d for t, d in device if t['type'] == 'META')['attributes']
        if not a['Footprint'].get('value'):
            a['Footprint']['value'] = metadata['Footprint']
        for key in ('Designator', 'Name'):
            a[key].update(x=x - 10, y=y + (-16 if key == 'Designator' else 23),
                          rotation=0, fontSize=10)
        if ref.startswith('J'):
            a['Name'].update(x=x - 5, y=y + (48 if ref == 'J4' else 38), fontSize=8)
        if ref == 'Q1':
            a['Designator'].update(x=x+30, y=y-12)
            a['Name'].update(x=x+30, y=y+2)
        symbol = libraries[a['Symbol']['value']]
        for ph, p in symbol:
            if ph['type'] != 'PIN': continue
            pa = {v['key']: v['value'] for t, v in symbol
                  if t['type'] == 'ATTR' and v.get('parentId') == ph['id']}
            # Only 0/180 degree placements are used; no mirror ambiguity.
            sign = -1 if rotation == 180 else 1
            pos = [x + sign*p['x'], y + sign*p['y']]
            angle = math.radians(p['rotation'] + rotation)
            outward = [-round(math.cos(angle)), round(math.sin(angle))]
            pins[ref + '.' + pa['Pin Number']] = (pos, outward, pa['Pin Name'])
    pin_net = {p: n for n, ps in NETS.items() for p in ps}
    assert len(pin_net) == sum(map(len, NETS.values()))
    assert set(pins) - set(pin_net) == {'J4.6'}
    assert pins['D1.2'][2] == 'A' and pins['D1.1'][2] == 'K'
    assert pins['Q1.1'][2] == 'G' and pins['Q1.2'][2] == 'S' and pins['Q1.3'][2] == 'D'
    base_attr = {'x': None, 'y': None, 'rotation': 0, 'color': None,
                 'fontFamily': None, 'fontSize': 7, 'fontWeight': None,
                 'italic': None, 'underline': None, 'align': 'LEFT_BOTTOM',
                 'fillColor': None, 'keyVisible': False, 'valueVisible': True}
    def add(kind, label, data):
        uid = hashlib.sha256(('gb10-reva-repair:' + label).encode()).hexdigest()[:16]
        page.append(({'type': kind, 'id': uid}, data))
        return uid
    segments = []
    for pin, net in pin_net.items():
        pos, direction, _ = pins[pin]
        length = 65 if pin.startswith('J') else 40
        end = [pos[i] + length*direction[i] for i in (0, 1)]
        wid = add('WIRE', pin, {'zIndex': 60})
        add('LINE', pin+':line', {'fillColor': None, 'fillStyle': None,
             'strokeColor': None, 'strokeStyle': None, 'strokeWidth': None,
             'startX': pos[0], 'startY': pos[1], 'endX': end[0], 'endY': end[1],
             'lineGroup': wid})
        label_pos = end if direction[0] < 0 else pos
        add('ATTR', pin+':net', dict(base_attr, x=label_pos[0], y=label_pos[1],
             value=net, key='NET', parentId=wid, zIndex=61))
        segments.append({'pin': pin, 'net': net, 'start': pos, 'end': end})
    # Verify geometrical wires don't accidentally touch unlike nets.
    def on(p, seg):
        a, b = seg['start'], seg['end']
        return ((b[0]-a[0])*(p[1]-a[1]) == (b[1]-a[1])*(p[0]-a[0])
                and min(a[0],b[0]) <= p[0] <= max(a[0],b[0])
                and min(a[1],b[1]) <= p[1] <= max(a[1],b[1]))
    for a in segments:
        for b in segments:
            if a['net'] != b['net']:
                assert not on(a['start'], b) and not on(a['end'], b), (a,b)
    # Normalize snapshot tickets, preserving object IDs for PCB identity.
    for i, (h, d) in enumerate(page):
        h.pop('firstTicket', None)
        if i: h['ticket'] = i
        else: h.pop('ticket', None)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'P1-before-repair.txt').write_text(encode(original))
    (args.output/'P1-repaired.txt').write_text(encode(page))
    (args.output/'connectivity-review.json').write_text(json.dumps({
        'nets': NETS, 'segments': segments, 'nc_pending': {'J4.6': pins['J4.6'][0]},
        'checks': [f'{len(pin_net)} pin mappings checked', 'D1 A/K and Q1 G/S/D checked',
                   'wire endpoint intersections checked'],
        'online_drc': 'pending'}, indent=2))
    print(f'{len(components)} components; {len(pin_net)} connected pins; J4.6 NC flag pending')
    print(args.output/'P1-repaired.txt')


if __name__ == '__main__':
    main()
