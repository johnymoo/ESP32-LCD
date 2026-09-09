"""Move only F1 and its attached tracks after the actual JLC SMT model check.

The DFM4 board remains historical. Output must be applied in JLCEDA, repoured,
DRC checked and freshly exported before it can become a manufacturing source.
"""
import copy
import json
from pathlib import Path
from audit_native import parse

root = Path(__file__).parent / 'dfm-20260909'
board = parse(root / 'PCB1-silk-fixed.txt')[0]
before = copy.deepcopy(board)
for h, d in board:
    if h['type'] == 'COMPONENT' and h['id'] == 'b9b2efaa14830f06':
        assert abs(d['x']*.0254-15) < .001
        d['x'] = round(18/.0254, 4)
        d['y'] = round(13/.0254, 4)
    if h['type'] == 'ATTR' and d.get('key') == 'Designator' and d.get('value') == 'F1':
        d['x'] = round(18.5/.0254, 4)
    if h.get('id') == '27563ba2f54f3db3':
        d['endX'], d['endY'] = 535.432, 511.8100
    if h.get('id') == '8eac22b295369de5':
        d['startX'], d['startY'] = 535.432, 511.8100
        d['endX'] = 651.7703
        d['endY'] = 511.8100
    if h.get('id') == 'e58d57d37edbc183':
        d['endX'] = 765.5496
        d['endY'] = 511.8100

changes = [{'id':h['id'], 'type':h['type'], 'before':old, 'after':d}
           for (h,d),(_,old) in zip(board,before) if d != old]
assert len(changes) == 5
encoded = '|\n'.join(json.dumps(h,separators=(',',':'))+'||'+json.dumps(d,separators=(',',':')) for h,d in board)
(root/'PCB1-fuse-clearance.txt').write_text(encoded)
(root/'fuse-clearance-change-review.json').write_text(json.dumps(changes,indent=2)+'\n')
print('F1 moves +3.00 mm X, +0.50 mm Y; 3 incident tracks and its label updated.')
