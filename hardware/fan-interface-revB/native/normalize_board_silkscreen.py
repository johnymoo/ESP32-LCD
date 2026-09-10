"""Create editable board-level silk, clearing solder openings by >=0.20 mm.

Original footprint outlines are retained on assembly layers. Copper, paste,
mask, library land patterns, component locations and pin mappings are untouched.
Uses the actually exported DFM2 masks, not assumed pad bounding boxes.
"""
import copy
import json
from pathlib import Path
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from gerbonara import LayerStack
from gerbonara.utils import MM
from audit_native import parse

ROOT = Path(__file__).parent/'dfm-20260909'
docs = parse(ROOT/'before/PCB1.epru')
libs = {d[0][1].get('uuid'): d for d in docs}
board = parse(ROOT/'PCB1-dfm-fixed.txt')[0]
attrs = {}
for h,d in board:
    if h['type']=='ATTR': attrs.setdefault(d['parentId'], {})[d['key']] = d['value']
stack = LayerStack.open('/Users/chris/Downloads/GB10-Fan-RevB-DFM2-20260909.zip')
origin = next(d for h,d in board if h['type']=='CANVAS')
ox,oy=origin['originX']*.0254,origin['originY']*.0254
from shapely.affinity import translate
mask_parts=[]
for obj in stack['bottom','mask'].objects:
    for prim in obj.to_primitives(unit=MM):
        poly=Polygon(prim.to_arc_poly().approximate_arcs(max_error=.001).outline)
        assert prim.polarity_dark, 'Unexpected mask clearing primitive'
        mask_parts.append(translate(poly,xoff=ox,yoff=oy))
for x in (2.75,41.75):
    for y in (8.835,26.615): mask_parts.append(Point(x,y).buffer(1.1))
for x in (19.73,32.73): mask_parts.append(Point(x,6.16).buffer(.65))
blocked=unary_union(mask_parts)
new=[]
def add_line(points, width=.20):
    safe=LineString(points).intersection(box(.25,.25,44.75,29.75)).difference(blocked.buffer(.21+width/2))
    geoms=[safe] if safe.geom_type=='LineString' else getattr(safe,'geoms',[])
    for segment in geoms:
        if segment.geom_type!='LineString' or segment.length<.35: continue
        coords=list(segment.coords)
        path=[coords[0][0]/.0254,coords[0][1]/.0254,'L']
        for x,y in coords[1:]:path.extend([x/.0254,y/.0254])
        n=len(new)
        new.append(({'type':'POLY','ticket':10000+n,'id':f'revb_dfm_silk_{n}'},
                    {'partitionId':'','groupId':0,'netName':'','layerId':4,'width':width/.0254,
                     'path':path,'locked':False,'zIndex':-1,'polyType':'NORMAL'}))

for h,d in board:
    if h['type']=='ATTR' and d.get('key')=='Designator' and d.get('layerId')==4:
        d['mirror']=False
        corrected={'R1':(28.9,23.3),'C2':(25.3,21.9),'D1':(23.6,16.7),'F1':(15.6,10.5)}
        if d['value'] in corrected:
            d['x'],d['y']=[round(v/.0254,4) for v in corrected[d['value']]]
    if h['type']!='COMPONENT' or d['layerId']!=2:continue
    a=attrs[h['id']]; ref=a['Designator']
    d['layerIdReplacements']={'3':9}
    assert d['angle']==0
    # Small two-pad parts are adequately identified by their designator;
    # keep their detailed package outlines on the assembly drawing.
    if ref.startswith('R') or ref=='C2':continue
    for fh,fd in libs[a['Footprint']]:
        if fh['type']!='POLY' or fd.get('layerId')!=3:continue
        p=fd['path']
        if len(p)!=5 or p[2]!='L':continue
        add_line([((d['x']+p[0])*.0254,(d['y']-p[1])*.0254),
                  ((d['x']+p[3])*.0254,(d['y']-p[4])*.0254)],max(.20,fd['width']*.0254))

# Unambiguous capacitor polarity, retained outside its solder lands.
add_line([(14.9,23.0),(15.7,23.0)])
add_line([(15.3,22.6),(15.3,23.4)])
add_line([(20.3,23.0),(21.1,23.0)])
# Cathode stripe inside the SS34 body, on the pin-1/FAN12 side.
add_line([(17.6,14.6),(17.6,17.4)],.25)
board.extend(new)
encoded='|\n'.join(json.dumps(h,separators=(',',':'))+'||'+json.dumps(d,separators=(',',':')) for h,d in board)
(ROOT/'PCB1-silk-fixed.txt').write_text(encoded)
(ROOT/'silkscreen-normalization.json').write_text(json.dumps({'board_silk_segments':len(new),'minimum_stroke_mm':.20,'clearance_target_mm':.20,'original_outlines':'assembly layers','limits':'Verify layer remapping and text orientation in fresh export; re-run DRC/DFM.'},indent=2)+'\n')
print(f'Generated {len(new)} editable board silk strokes; original libraries unchanged')
