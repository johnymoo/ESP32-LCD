"""Reposition existing native PCB components, keeping all pad-net mappings."""
import copy
import json
import math
from pathlib import Path
import sys
import zipfile
from recover_schematic import parse, encode, NETS

MM = 1000 / 25.4
placements = {
    'J1': (6, 21, 0), 'F1': (12, 21, 0), 'D1': (19, 21, 180),
    'C1': (27, 20, 0), 'C2': (27, 15, 0),
    'J2': (36, 22, 0), 'J3': (36, 11, 0), 'J4': (20, 4, 270),
    'Q1': (21, 11.5, 0), 'R1': (16, 11.5, 0), 'R2': (18, 8, 0),
    'R3': (29.5, 12, 0), 'R5': (29.5, 5.5, 0),
    'R4': (24.5, 9.5, 0), 'R6': (24.5, 6, 0),
}

with zipfile.ZipFile(sys.argv[1]) as z:
    docs = parse(z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode())
libraries = {r[0][1]['uuid']: r for r in docs}
original = next(r for r in docs if r[0][1]['docType'] == 'PCB')
pcb = copy.deepcopy(original)
attrs = {}
for h, d in pcb:
    if h['type'] == 'ATTR': attrs.setdefault(d['parentId'], {})[d['key']] = d
components = {attrs[h['id']]['Designator']['value']: (h,d)
              for h,d in pcb if h['type']=='COMPONENT'}
assert set(components) == set(placements)
actual = {}
pads = []
for ref, (h,c) in components.items():
    a = attrs[h['id']]
    x, y, ang = placements[ref]
    dx, dy = x*MM-c['x'], y*MM-c['y']
    c.update(x=round(x*MM,4), y=round(y*MM,4), angle=ang)
    for d in a.values():
        if d.get('x') is not None: d['x'] += dx
        if d.get('y') is not None: d['y'] += dy
    a['Designator'].update(x=round((x-1)*MM,4), y=round((y+2)*MM,4),
                          angle=0, fontSize=32, strokeWidth=5, origin='LEFT_BOTTOM')
    if ref in ('C1','J2','J3'):
        a['Designator'].update(x=(x-1)*MM, y=(y+(4 if ref=='C1' else 1.7))*MM)
    if ref=='J4': a['Designator'].update(x=4*MM,y=4*MM)
    fp = a.get('Footprint',{}).get('value')
    if not fp:
        dev = libraries[a['Device']['value']]
        fp = next(d for t,d in dev if t['type']=='META')['attributes']['Footprint']
    footprint = libraries[fp]
    nets = {}
    for t,d in pcb:
        if t['type']=='PAD_NET':
            key = json.loads(t['id'])
            if key[1]==h['id']: nets[key[2]]=d['padNet']
    for ph,p in footprint:
        if ph['type'] != 'PAD':continue
        net = nets[p['num']]
        if net: actual.setdefault(net,[]).append(ref+'.'+p['num'])
        co,si=math.cos(math.radians(ang)),math.sin(math.radians(ang))
        px = x+(p['centerX']*co-p['centerY']*si)/MM
        py = y+(p['centerX']*si+p['centerY']*co)/MM
        w,hh=p['defaultPad']['width']/MM,p['defaultPad']['height']/MM
        if ang in (90,270):w,hh=hh,w
        assert .4 < px-w/2 and px+w/2 < 39.6, (ref,p['num'],px,w)
        assert .4 < py-hh/2 and py+hh/2 < 24.6, (ref,p['num'],py,hh)
        pads.append({'pin':ref+'.'+p['num'],'net':net,'x':px,'y':py,'w':w,'h':hh})
assert {k:sorted(v) for k,v in actual.items()} == {k:sorted(v) for k,v in NETS.items()}
for h,d in pcb:
    if h['type']=='POLY' and d.get('polyType')=='BOARD_OUTLINE':
        d['path']=['R',0,round(25*MM,4),round(40*MM,4),round(25*MM,4),0,0]
    if h['type']=='CANVAS': d.update(unit='mm',gridXSize=10,gridYSize=10,snapXSize=10,snapYSize=10)
    if h['type']=='PRIMITIVE' and h['id']=='["PRIMITIVE","RATLINE"]':d['display']=True
    if h['type']=='RULE' and h['id']=='["RULE","TRACK","copperThickness1oz"]':
        d['ruleContext']['track']['content'][0].update(stroMin=10,stroDef=20,stroMax=100)
# Board legend; placement is checked in the rendered PCB before fabrication.
for i,(text,x,y,size) in enumerate([
    ('GB10 FAN RevA',2,16,40),('12V ONLY',2,18.5,32),
    ('ESP32 3V3',7,7,30),('PWM: OPEN DRAIN',2,14,27),
    ('1 GND / 2 12V',30,24,26),('3 TACH / 4 PWM',30,1,26),
]):
    pcb.append(({'type':'STRING','id':f'gb10legend{i}'}, {
        'partitionId':'','groupId':0,'layerId':3,'x':x*MM,'y':y*MM,'text':text,
        'fontFamily':'default','fontSize':size,'strokeWidth':5,'bold':False,
        'italic':False,'origin':'LEFT_BOTTOM','angle':0,'reverse':False,
        'expansion':0,'mirror':False,'locked':False,'zIndex':99}))
for i,(h,d) in enumerate(pcb):
    h.pop('firstTicket',None)
    if i:h['ticket']=i
    else:h.pop('ticket',None)
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
(out/'PCB1-before-layout.txt').write_text(encode(original))
(out/'PCB1-layout.txt').write_text(encode(pcb))
(out/'pcb-pad-review.json').write_text(json.dumps({'pads':pads,'nets':actual,
    'board_mm':[40,25],'default_track_mm':.508,'online_drc':'pending'},indent=2))
print('15 components positioned; 38 connected pads match schematic; pad edge bounds pass')
print(out/'PCB1-layout.txt')
