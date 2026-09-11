"""Check added nominal assembly interfaces in the saved detailed CAD.

FreeCAD Python; mm. This checks the loose hood/face subassembly, not an
installed-head screwdriver path or the user's actual driver and fasteners.
"""
from pathlib import Path
import json, hashlib
import FreeCAD as A, Part

from build_paths import BUILD_ROOT as R
C=R/'cad'
D=A.openDocument(str(C/'MicroDuckling_R01.FCStd'))
V=A.Vector
ports=[]
assembly=json.loads((C/'assembly.json').read_text());p=assembly['parameters']
for y in [-p['face_mount_y'],p['face_mount_y']]:
    for z in [h+p['head_shift_z'] for h in p['face_mount_z']]:
        path=Part.makeCylinder(2.1,19-p['head_rear_x'],V(p['head_rear_x']-.5,y,z),V(1,0,0))
        volume=path.common(D.HeadHood.Shape).Volume
        ports.append(dict(y_mm=y,z_mm=z,path_diameter_mm=4.2,
                          overlap_mm3=volume,clear=volume<.001))
gap=D.BodyShellLeft.Shape.distToShape(D.BodyShellRight.Shape)[0]
solids={r['name']:D.getObject(r.get('object_name',r['name'])).Shape for r in assembly['parts']}
clearance_pairs=[('ESP32CAM','HeadHood'),('UpperBill','Jaw'),('UpperBill','CameraRing'),
                 ('CameraBoardClamp','HeadHood'),('Buck_0','BodyShellLeft'),
                 ('Buck_0','ServoLeft'),
                 ('IMU','BodyShellLeft'),('IMU','BodyShellRight'),
                 ('ServoNeck','BodyShellLeft'),('ServoNeck','BodyShellRight'),
                 ('BatteryStrap','Chassis'),('BatteryStrap','Battery')]
clearances=[dict(a=a,b=b,distance_mm=solids[a].distToShape(solids[b])[0]) for a,b in clearance_pairs]
rear_probe=Part.makeBox(4.5,8,4,V(-36,-4,41))
rear_access=dict(probe_bounds_mm=[-36,-4,41,-31.5,4,45],
                 nominal_aperture_mm=[14,10],
                 shell_overlap_mm3={name:rear_probe.common(solids[name]).Volume
                                    for name in ['BodyShellLeft','BodyShellRight']},
                 scope='Straight cable corridor through both rear shell halves and locating lip. Actual battery leads, connector insertion and strain relief are not qualified.')
result=dict(source_cad_sha256=hashlib.sha256((C/'MicroDuckling_R01.FCStd').read_bytes()).hexdigest(),
            loose_hood_rear_access=ports,body_shell_minimum_distance_mm=gap,
            rear_cable_access=rear_access,
            selected_electronics_clearances=clearances,
            scope='Nominal rigid geometry. Rear access is checked with the hood off the frame; the lower paths are blocked by the installed mouth servo. Actual tools, fastener heads, print compensation and tolerance stacks remain unverified.')
(C/'detail_interface_checks.json').write_text(json.dumps(result,indent=2))
assert all(p['clear'] for p in ports), 'Rear screw/driver access blocked in loose hood'
assert gap>=.20, 'Body registration allowance fell below0.20mm nominal geometry'
assert all(p['distance_mm']>=(.09 if p['a']=='BatteryStrap' and p['b']=='Battery' else .20) for p in clearances), 'Selected nominal interface gap failed'
assert max(rear_access['shell_overlap_mm3'].values())<.001, 'Rear cable access is blocked by a shell or its locating lip'
print(json.dumps(result,indent=2))
