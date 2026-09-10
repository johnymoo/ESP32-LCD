"""Minimal source changes following the 2026-09-09 independent JLC DFM.

Input is the unmodified UI download; output PCB text goes into File Source.
Component positions, footprints, parts, pad nets and board size are unchanged.
"""
import copy
import json
from pathlib import Path
from audit_native import parse

ROOT = Path(__file__).parent / 'dfm-20260909'
docs = parse(ROOT / 'before/PCB1.epru')
pcb = next(d for d in docs if d[0][1]['docType'] == 'PCB')
original = copy.deepcopy(pcb)

# Absolute source coordinates in mm, retaining the existing bottom text orientation.
labels = {
    'C1': (17.5, 23.5), 'C2': (23.5, 22.0), 'D1': (21.8, 16.5),
    'F1': (10.5, 11.0), 'J1': (4.0, 18.0), 'J2': (20.0, 1.0),
    'J3': (33.0, 1.0), 'Q1': (28.0, 17.3), 'R1': (27.6, 23.3),
    'R2': (31.3, 21.5), 'R3': (23.0, 15.5), 'R4': (26.0, 15.5),
    'R5': (32.0, 15.5), 'R6': (35.0, 15.5),
}

# Move the whole connected corner, including every incident segment, not just
# one Gerber line.  All coordinates are mil, as stored by JLCEDA.
points = {
    (936.0651, 503.3848): (931.0651, 498.3848),
    (1025.2145, 503.3848): (1020.2145, 498.3848),
    (1002.1004, 817.0929): (1007.1004, 822.0929),
    (1082.1002, 817.0929): (1087.1002, 822.0929),
    (1141.7339, 757.4591): (1141.7339, 767.4591),
    (994.1752, 561.4949): (1002.1752, 569.4949),
    (1377.6547, 561.4949): (1377.6547, 569.4949),
}
changes = []
for (h, d), (_, before) in zip(pcb, original):
    if h['type'] == 'ATTR' and d.get('key') == 'Designator' and d.get('value') in labels:
        x, y = labels[d['value']]
        d.update(x=round(x/.0254, 4), y=round(y/.0254, 4),
                 fontSize=40, strokeWidth=7, mirror=True)
    if h['type'] in ('LINE', 'VIA'):
        for xkey, ykey in [('startX','startY'), ('endX','endY'), ('centerX','centerY')]:
            old = (d.get(xkey), d.get(ykey))
            if old in points:
                d[xkey], d[ykey] = points[old]
    if d != before:
        changes.append({'id': h['id'], 'type': h['type'],
                        'before': before, 'after': d})

def encode(doc):
    return '|\n'.join(json.dumps(h, separators=(',',':'), ensure_ascii=False)
                      + '||' + json.dumps(d, separators=(',',':'), ensure_ascii=False)
                      for h, d in doc)

online = parse(ROOT/'online-source-before.txt')[0]
replacements = {c['id']: c['after'] for c in changes}
matched = 0
for i, (h, d) in enumerate(online):
    if h.get('id') in replacements:
        online[i] = (h, replacements[h['id']])
        matched += 1
assert matched == len(changes), (matched, len(changes))
(ROOT/'PCB1-dfm-fixed.txt').write_text(encode(online))
(ROOT/'PCB1-dfm-fixed.epru').write_text('|\n'.join(encode(d) for d in docs))
(ROOT/'source-change-review.json').write_text(json.dumps(changes, indent=2)+'\n')
print(f'{len(changes)} records changed; {len(labels)} labels; no component movement')
