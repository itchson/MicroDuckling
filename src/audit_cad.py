"""Read saved CAD, test intersections and sampled moving-pair clearances."""
import FreeCAD as A,Part,json,math,itertools,hashlib,sys
from pathlib import Path
from build_paths import BUILD_ROOT as R
O=R/'cad';d=json.loads((O/'assembly.json').read_text());D=A.openDocument(str(O/'MicroDuckling_R01.FCStd'))
rs=[r for r in d['parts'] if r['kind']!='coupon'];ss={r['name']:D.getObject(r.get('object_name',r['name'])).Shape for r in rs};V=A.Vector
out={'static_overlaps':[],'motion_overlaps':[],'combined_jaw_neck_overlaps':[],'reopened_solids_valid':all(s.isValid() for s in ss.values()),'notes':'Nominal CAD solids including sourced PCB outlines and modeled fasteners. Samples only, not continuous motion or positive-clearance proof. Illustrative flexible harness routes excluded from static and motion tests; actual wiring, plugs, tolerance and full assembly access unverified.'}
out['source_cad_sha256']=hashlib.sha256((O/'MicroDuckling_R01.FCStd').read_bytes()).hexdigest()
out['source_assembly_sha256']=hashlib.sha256((O/'assembly.json').read_bytes()).hexdigest()
out['servo_output_motion_scope']='Output spline shafts are separate parts on the driven links. Complete servo cases and crowns remain fixed and are checked at every joint sample. Actual output bearings and spline tolerances remain unverified.'
for a,b in itertools.combinations(rs,2):
    if a['kind']=='harness' or b['kind']=='harness':continue
    if not ss[a['name']].BoundBox.intersect(ss[b['name']].BoundBox):continue
    vol=ss[a['name']].common(ss[b['name']]).Volume
    if vol>.01:out['static_overlaps'].append({'a':a['name'],'b':b['name'],'volume_mm3':round(vol,4),'same_link':a['link']==b['link']})
print('STATIC',len(out['static_overlaps']),flush=True)
(R/'work').mkdir(exist_ok=True)
(R/'work'/'latest_static_audit.json').write_text(json.dumps({k:out[k] for k in ['static_overlaps','reopened_solids_valid','source_cad_sha256','source_assembly_sha256']},indent=2))
if '--static-only' in sys.argv:sys.exit(0)
p=d['parameters']
motions=[('left_leg',V(0,p['leg_y'],p['hip_z']),V(0,1,0),range(-12,13,2)),('right_leg',V(0,-p['leg_y'],p['hip_z']),V(0,1,0),range(-12,13,2)),('jaw',V(p['jaw_pivot_x'],0,p['jaw_pivot_z']),V(0,1,0),range(0,13,1)),('head',V(0,0,p['neck_pivot_z']),V(0,0,1),range(-45,46,5))]
for link,piv,axis,angles in motions:
    moving=[r for r in rs if not r['name'].startswith('Harness') and (r['link']==link or link=='head' and r['link']=='jaw')]
    fixed=[r for r in rs if not r['name'].startswith('Harness') and r not in moving and not (link in ['left_leg','right_leg'] and r['link'] in ['left_leg','right_leg'])]
    for angle in angles:
        for a in moving:
            s=ss[a['name']].copy();s.rotate(piv,axis,angle)
            for b in fixed:
                q=ss[b['name']]
                if s.BoundBox.intersect(q.BoundBox):
                    vol=s.common(q).Volume
                    if vol>.05:out['motion_overlaps'].append({'joint':link,'angle':angle,'a':a['name'],'b':b['name'],'volume_mm3':round(vol,3)})
    print('MOTION',link,flush=True)
for yaw in range(-45,46,15):
    for opening in range(0,13,2):
        jaw=ss['Jaw'].copy();jaw.rotate(V(p['jaw_pivot_x'],0,p['jaw_pivot_z']),V(0,1,0),opening);jaw.rotate(V(0,0,p['neck_pivot_z']),V(0,0,1),yaw)
        for b in [r for r in rs if r['link']=='body' and r['kind']=='print']:
            q=ss[b['name']]
            if not jaw.BoundBox.intersect(q.BoundBox):continue
            v=jaw.common(q).Volume
            if v>.05:out['combined_jaw_neck_overlaps'].append(dict(yaw=yaw,opening=opening,part=b['name'],volume_mm3=v))
print('COMBINED',len(out['combined_jaw_neck_overlaps']),flush=True)
(O/'audit.json').write_text(json.dumps(out,indent=2));print('DONE',len(out['motion_overlaps']),flush=True)
