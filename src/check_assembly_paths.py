"""Probe nominal rigid component insertion paths with shell removed.

Most paths use 2mm steps; stepped withdrawal paths are <=1mm and record offsets.
Reverse each path for insertion, following the documented subassembly order.
"""
import FreeCAD as A,json,hashlib
from pathlib import Path
from build_paths import BUILD_ROOT as R
O=R/'cad';d=json.loads((O/'assembly.json').read_text());D=A.openDocument(str(O/'MicroDuckling_R01.FCStd'));V=A.Vector
ss={r['name']:D.getObject(r.get('object_name',r['name'])).Shape for r in d['parts'] if r['kind']!='coupon'}
cases=[('Battery','Chassis',V(-1,0,0),range(0,61,2)),
       ('ServoLeft','Chassis',V(0,1,0),range(0,51,2)),
       ('ServoRight','Chassis',V(0,-1,0),range(0,51,2)),
       ('ServoNeck','Chassis',V(0,0,1),range(0,51,2)),
       ('IMU','Chassis',V(0,0,1),range(0,41,2)),
       ('ESP32CAM','HeadFrame',V(0,0,1),range(0,61,2)),
       ('Buck_0','Chassis',None,[V(-i*.5,0,0) for i in range(5)]+[V(-2,0,i) for i in range(1,61)]),
       ('LegFootLeft','ServoLeft',V(0,1,0),range(0,15)),
       ('LegFootRight','ServoRight',V(0,-1,0),range(0,15)),
       ('NeckCarrier','ServoNeck',V(0,0,1),range(0,15)),
       ('ServoMouth','Jaw',None,[V(0,-i*.5,0) for i in range(9)]+[V(0,-4,-i) for i in range(1,41)]),
       ('MouthJawModule','HeadFrame',None,[V(0,i*.25,0) for i in range(3)]+[V(0,.5,-i) for i in range(1,41)]),
       ('ServoMouth','HeadFrame',None,[V(0,i*.25,0) for i in range(3)]+[V(0,.5,-i) for i in range(1,41)]),
       ('CameraBoardClamp','HeadFrame',V(0,0,1),range(0,41,2)),
       ('CameraCradle','FacePanel',V(-1,0,0),range(0,41,2))]
results=[]
for name,frame,axis,steps in cases:
    collisions=[]
    for step in steps:
        offset=axis*step if axis is not None else step
        q=(ss['ServoMouth'].fuse(ss['OutputSplineMouth']).fuse(ss['Jaw']) if name=='MouthJawModule' else ss[name]).copy()
        if name=='ServoMouth' and frame=='Jaw':q=q.fuse(ss['OutputSplineMouth'])
        q.translate(offset);v=q.common(ss[frame]).Volume
        if v>.01:collisions.append(dict(offset_mm=list(offset),volume_mm3=v))
    results.append(dict(part=name,mounting_frame=frame,direction_out=list(axis) if axis is not None else None,
                        step_mm=2 if axis is not None else 1,
                        sampled_offsets_mm=[list(axis*s if axis is not None else s) for s in steps],collisions=collisions))
    print(name,len(collisions),flush=True)
(O/'assembly_paths.json').write_text(json.dumps(dict(source_cad_sha256=hashlib.sha256((O/'MicroDuckling_R01.FCStd').read_bytes()).hexdigest(),source_assembly_sha256=hashlib.sha256((O/'assembly.json').read_bytes()).hexdigest(),scope='Rigid component vs named bare frame,2mm straight/<=1mm stepped samples; reverse for insertion. The assembled mouth case/output/jaw module vs bare head frame unseats0.5mm outward then drops before passive pin and carrier attachment. Mouth case plus geared output vs one-piece jaw first withdraws4mm leftward from its socket, then lowers through the jaw opening; passive pin and head frame must be absent. Servo regulator disengages2mm rearward then lifts before battery/IMU/neck support. Neighboring boards, hood, clamps and harness absent; full installed-neighbor order/tool access still unverified.',paths=results),indent=2))
