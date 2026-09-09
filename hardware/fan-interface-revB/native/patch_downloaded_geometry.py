import json
from pathlib import Path

src = Path('/tmp/PCB1-pure.epru')
out = Path('/tmp/PCB1-revB-geometry.epru')
rows = []
for line in src.read_text().splitlines():
    if '||' not in line:
        rows.append(line)
        continue
    hs, ds = line.split('||', 1)
    try:
        rows.append((json.loads(hs), json.loads(ds.rstrip('|'))))
    except Exception:
        rows.append(line)

refs = {}
for item in rows:
    if not isinstance(item, str):
        h, d = item
        if h.get('type') == 'ATTR' and d.get('key') == 'Designator':
            refs[d.get('parentId')] = d.get('value')
positions_by_ref = {
    'JDISP1': (450, 250),
    'JDISP2': (450, 919),
    'J2': (1450, 1000),
    'J3': (1450, 500),
}
for item in rows:
    if isinstance(item, str):
        continue
    h, d = item
    ref = refs.get(h.get('id'))
    if h.get('type') == 'COMPONENT' and ref in positions_by_ref:
        d['x'], d['y'] = positions_by_ref[ref]
    if h.get('type') == 'ATTR' and d.get('key') == 'Designator' and d.get('value') in positions_by_ref:
        x, y = positions_by_ref[d['value']]
        d['x'], d['y'] = x + 120, y - 80
    if h.get('type') == 'POLY' and d.get('polyType') == 'BOARD_OUTLINE':
        d['path'] = ['R', 699.4689, 463.9764, 2200, 1400, 0, 0]

def encode(item):
    if isinstance(item, str):
        return item
    h, d = item
    return json.dumps(h, separators=(',', ':'), ensure_ascii=False) + '||' + json.dumps(d, separators=(',', ':'), ensure_ascii=False) + '|'

out.write_text('\n'.join(encode(x) for x in rows) + '\n')
print(out)
