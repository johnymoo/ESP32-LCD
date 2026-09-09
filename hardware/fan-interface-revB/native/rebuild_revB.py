import copy, hashlib, json, math
from pathlib import Path

SRC = Path(__file__).with_name('P1-current.epru')
OUT = Path(__file__).with_name('P1-rebuilt.txt')

def parse(path):
    docs, cur = [], None
    for line in path.read_text().splitlines():
        if '||' not in line:
            continue
        try:
            hs, ds = line.split('||', 1)
            h, d = json.loads(hs), json.loads(ds.rstrip('|'))
        except Exception:
            continue
        if h.get('type') == 'DOCHEAD':
            cur = []
            docs.append(cur)
        if cur is not None:
            cur.append((h, d))
    return docs

def enc(rows):
    return '\n'.join(json.dumps(h, separators=(',', ':'), ensure_ascii=False) + '||' +
                     json.dumps(d, separators=(',', ':'), ensure_ascii=False) + '|'
                     for h, d in rows) + '\n'

docs = parse(SRC)
page = next(d for d in docs if d and d[0][1].get('docType') == 'SCH_PAGE')
libraries = {d[0][1].get('uuid'): d for d in docs if d and d[0][1].get('uuid')}

attrs = {}
for h, d in page:
    if h.get('type') == 'ATTR':
        attrs.setdefault(d.get('parentId'), {})[d.get('key')] = d

comps = {}
for h, d in page:
    if h.get('type') == 'COMPONENT' and 'Designator' in attrs.get(h['id'], {}):
        comps[attrs[h['id']]['Designator']['value']] = (h, d)

assert 'JDISP2' in comps and 'JDISP1' not in comps

# The carrier accepts the display's two header rows.  The second row already
# exists as JDISP2; clone its device identity for the first row.
old_h, old_d = comps['JDISP2']
new_id = hashlib.sha256(b'GB10-RevB-JDISP1').hexdigest()[:16]
new_h, new_d = copy.deepcopy(old_h), copy.deepcopy(old_d)
new_h['id'] = new_id
new_d['x'], new_d['y'] = 520, -570
attrs[new_id] = copy.deepcopy(attrs[old_h['id']])
new_d['rotation'] = 0
new_attrs = []
for h, d in page:
    if h.get('type') == 'ATTR' and d.get('parentId') == old_h['id']:
        ah = copy.deepcopy(h)
        a = copy.deepcopy(d)
        ah['id'] = hashlib.sha256(('GB10-RevB-JDISP1:' + h['id']).encode()).hexdigest()[:16]
        a['parentId'] = new_id
        if a.get('key') == 'Designator':
            a['value'] = 'JDISP1'; a['x'] = 510; a['y'] = -630
        elif a.get('key') == 'Name':
            a['x'] = 510; a['y'] = -522
        new_attrs.append((ah, a))

# Keep the original page objects/components, clone the second header, and
# remove all old wiring/labels.  Connectivity is recreated with short stubs
# and named labels, which also removes the stale J4/U1-era geometry.
kept = []
for h, d in page:
    if h.get('type') in ('WIRE', 'LINE', 'ELE_PLACEHOLDER'):
        continue
    if h.get('type') == 'ATTR' and d.get('key') in ('NET', '_NETLABEL_'):
        continue
    kept.append((h, d))
kept.append((new_h, new_d))
for ah, a in new_attrs:
    kept.append((ah, a))

# Find a symbol's pin geometry by its component Symbol UUID.
def symbol_pins(comp_id):
    au = attrs[comp_id]['Symbol']['value']
    doc = libraries[au]
    out = {}
    for h, d in doc:
        if h.get('type') != 'PIN':
            continue
        pa = {x.get('key'): x.get('value') for hh, x in doc
              if hh.get('type') == 'ATTR' and x.get('parentId') == h['id']}
        out[pa['Pin Number']] = (d['x'], d['y'], d['rotation'])
    return out

def pin_pos(comp_h, comp_d, num):
    x, y, r = comp_d['x'], comp_d['y'], comp_d.get('rotation', 0)
    px, py, _ = symbol_pins(comp_h['id'])[str(num)]
    if r == 180:
        px, py = -px, -py
    return x + px, y + py

# Directly labeled nets.  Pins omitted here are intentionally NC.
NETS = {
    'J1.1': 'VIN12_RAW', 'J1.2': 'GND',
    'F1.1': 'VIN12_RAW', 'F1.2': 'VIN12_PROT',
    'D1.1': 'FAN12', 'D1.2': 'VIN12_PROT',
    'C1.1': 'FAN12', 'C1.2': 'GND', 'C2.1': 'FAN12', 'C2.2': 'GND',
    'J2.1': 'GND', 'J2.2': 'FAN12', 'J2.3': 'TACH1_FAN', 'J2.4': 'PWM_BUS',
    'J3.1': 'GND', 'J3.2': 'FAN12', 'J3.3': 'TACH2_FAN', 'J3.4': 'PWM_BUS',
    'R1.1': 'ESP_PWM', 'R1.2': 'PWM_GATE', 'R2.1': 'PWM_GATE', 'R2.2': 'GND',
    'Q1.1': 'PWM_GATE', 'Q1.2': 'GND', 'Q1.3': 'PWM_BUS',
    'R3.1': 'TACH1_FAN', 'R3.2': 'ESP_TACH1', 'R4.1': 'ESP_TACH1', 'R4.2': '3V3',
    'R5.1': 'TACH2_FAN', 'R5.2': 'ESP_TACH2', 'R6.1': 'ESP_TACH2', 'R6.2': '3V3',
    # P1 odd pins occupy JDISP1; even pins occupy JDISP2.
    'JDISP1.2': 'GND', 'JDISP1.6': 'ESP_PWM',
    'JDISP1.7': 'ESP_TACH1', 'JDISP1.9': 'ESP_TACH2',
    'JDISP2.2': 'GND', 'JDISP2.3': 'GND', 'JDISP2.4': '3V3',
}

base = {'fillColor': None, 'fillStyle': None, 'strokeColor': None,
        'strokeStyle': None, 'strokeWidth': None, 'startX': 0, 'startY': 0,
        'endX': 0, 'endY': 0}
for key, net in NETS.items():
    ref, num = key.rsplit('.', 1)
    h, d = new_h, new_d if ref == 'JDISP1' else comps[ref]
    if ref != 'JDISP1':
        h, d = comps[ref]
    x, y = pin_pos(h, d, num)
    # All symbols in this page expose pins to the left.  A short leftward
    # stub makes the net label unambiguous and easy to inspect online.
    wg = hashlib.sha256(('GB10-RevB-wire:' + key).encode()).hexdigest()[:16]
    kept.append(({'type': 'WIRE', 'id': wg}, {'zIndex': 60}))
    kept.append(({'type': 'LINE', 'id': wg + 'l'}, dict(base, startX=x, startY=y,
                 endX=x-30, endY=y, lineGroup=wg)))
    kept.append(({'type': 'ATTR', 'id': wg + 'a'}, {
        'x': x-30, 'y': y, 'rotation': 0, 'color': None, 'fontFamily': None,
        'fontSize': 7, 'fontWeight': None, 'italic': None, 'underline': None,
        'align': 'LEFT_BOTTOM', 'value': net, 'keyVisible': False,
        'valueVisible': True, 'key': 'NET', 'fillColor': None,
        'parentId': wg, 'zIndex': 61}))

# Give the cloned header its own designator attrs with the correct parent.
# The copied values above intentionally preserve the device/library linkage.
for i, (h, d) in enumerate(kept):
    h.pop('firstTicket', None)
    if i:
        h['ticket'] = i
    else:
        h.pop('ticket', None)

OUT.write_text(enc(kept))
print('components:', sorted(comps), '+ JDISP1')
print('labeled pins:', len(NETS))
print('output:', OUT)
