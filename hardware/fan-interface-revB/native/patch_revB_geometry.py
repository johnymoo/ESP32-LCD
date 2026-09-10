import json
from pathlib import Path

src = Path(__file__).with_name('PCB1-complete.epru')
out = Path(__file__).with_name('PCB1-geometry-fixed.epru')
rows = []
for line in src.read_text().splitlines():
    if '||' not in line:
        rows.append(line); continue
    hs, ds = line.split('||', 1)
    try:
        h, d = json.loads(hs), json.loads(ds.rstrip('|'))
    except Exception:
        rows.append(line); continue
    rows.append((h, d))

ids = {
    'JDISP2': '1b6162c12924ea3c',
    'J2': '8722eee746183e6b',
    'J3': '08129aba0720b784',
}
positions = {
    ids['JDISP2']: (450, 919),
    ids['J2']: (1450, 1000),
    ids['J3']: (1450, 500),
}
for item in rows:
    if isinstance(item, str): continue
    h, d = item
    if h.get('type') == 'COMPONENT' and h.get('id') in positions:
        d['x'], d['y'] = positions[h['id']]
    if h.get('type') == 'ATTR' and d.get('parentId') in positions and d.get('key') == 'Designator':
        x, y = positions[d['parentId']]
        d['x'], d['y'] = x + 120, y - 80
    if h.get('type') == 'POLY' and d.get('polyType') == 'BOARD_OUTLINE':
        d['path'] = ['R', 699.4689, 463.9764, 2200, 1400, 0, 0]

def enc(item):
    if isinstance(item, str): return item
    h, d = item
    return json.dumps(h, separators=(',', ':'), ensure_ascii=False) + '||' + json.dumps(d, separators=(',', ':'), ensure_ascii=False) + '|'

out.write_text('\n'.join(enc(x) for x in rows) + '\n')
print(out)
