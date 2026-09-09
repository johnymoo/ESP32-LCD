"""Measure printed silk against actual solder openings and holes in a ZIP.

Independent geometry check, supplemental to the online factory DFM.
Gerbonara 1.6.3 and Shapely 2.x; arcs approximated within 1 micron.
"""
import json
import sys
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
from gerbonara import LayerStack
from gerbonara.utils import MM

stack=LayerStack.open(sys.argv[1])
def shapes(objects):
    result=[]
    for obj in objects:
        for prim in obj.to_primitives(unit=MM):
            p=Polygon(prim.to_arc_poly().approximate_arcs(max_error=.001).outline)
            if not p.is_valid:p=p.buffer(0)
            result.append((p,prim.polarity_dark))
    return result
def composite(items):
    out=Polygon()
    for p,dark in items:out=out.union(p) if dark else out.difference(p)
    return out
holes=composite(shapes(o for layer in stack.drill_layers for o in layer.objects))
report={}
for side in ['top','bottom']:
    mask=composite(shapes(stack[side,'mask'].objects))
    silk=shapes(stack[side,'silk'].objects)
    assert all(d for _,d in silk)
    mask_gaps=[p.distance(mask) for p,_ in silk]
    hole_gaps=[p.distance(holes) for p,_ in silk]
    report[side]={'minimum_solder_opening_clearance_mm':min(mask_gaps),
                  'minimum_drill_clearance_mm':min(hole_gaps),
                  'silk_primitives_with_mask_clearance_below_0_18':sum(v<.18 for v in mask_gaps),
                  'silk_primitives_with_hole_clearance_below_0_18':sum(v<.18 for v in hole_gaps)}
encoded=json.dumps(report,indent=2)+'\n'
if len(sys.argv)>2:Path(sys.argv[2]).write_text(encoded)
print(encoded)
