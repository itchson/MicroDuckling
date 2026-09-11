"""Nominal R07 direct sockets and integral face. Does not certify physical fit."""
import hashlib
import json
import math
import FreeCAD as A
import Part
from build_paths import BUILD_ROOT

V=A.Vector
C=BUILD_ROOT/'cad'
D=A.openDocument(str(C/'MicroDuckling_R01.FCStd'))
data=json.loads((C/'assembly.json').read_text(encoding='utf-8'))
shapes={r['name']:D.getObject(r.get('object_name',r['name'])).Shape for r in data['parts']}
retired=['HornLeft','HornRight','NeckHorn','MouthHorn','UpperBill','LegHornCoupon',
         'UpperBillScrewLeft','UpperBillScrewRight','UpperBillNutLeft','UpperBillNutRight']
assert not set(retired)&shapes.keys()
assert not any('HornScrew' in name for name in shapes)
interfaces=[]
definitions=[('LegFootLeft','ServoLeft',(0,36,38),(0,1,0),5.5),
             ('LegFootRight','ServoRight',(0,-36,38),(0,-1,0),5.5),
             ('NeckCarrier','ServoNeck',(0,0,70),(0,0,1),5.5),
             ('Jaw','ServoMouth',(-16,16,90),(0,1,0),4.5)]
for name,servo,entry,axis,outer_radius in definitions:
    shape=shapes[name]; motor=shapes[servo]; origin=V(*entry); direction=V(*axis)
    zone=Part.makeCylinder(2.5,4.01,origin-direction*.5,direction)
    shaft_name='OutputSpline'+servo.removeprefix('Servo')
    shaft=shapes[shaft_name]; case=motor
    assert shaft.common(zone).Volume>shaft.Volume-1e-5
    driven_link=next(r['link'] for r in data['parts'] if r['name']==name)
    assert next(r['link'] for r in data['parts'] if r['name']==shaft_name)==driven_link
    profile_checks=[]
    for tooth in range(20):
        pair=[]
        for offset in [0,.5]:
            angle=2*math.pi*(tooth+offset)/20
            radial=V(2.35*math.cos(angle),0,2.35*math.sin(angle))
            if axis==(0,0,1):radial=V(radial.x,-radial.z,0)
            if axis==(0,-1,0):radial=V(radial.x,0,radial.z)
            pair.append(shape.isInside(origin+direction*1.0+radial,1e-6,False))
        profile_checks.append(pair==[False,True])
    report=dict(part=name,servo=servo,output_shaft_part=shaft_name,output_shaft_link=driven_link,one_connected_solid=len(shape.Solids)==1,
                socket_entry_mm=list(entry),socket_axis=list(axis),
                shaft_socket_overlap_mm=3.5,nominal_socket_depth_mm=3.8,
                nominal_tip_room_mm=.3,nominal_radial_allowance_mm=.06,
                minimum_hub_radial_wall_mm=outer_radius-2.46,
                shaft_intersection_mm3=shaft.common(shape).Volume,
                case_crown_gap_mm=case.distToShape(shape)[0],
                tooth_valley_and_crest_probes_passed=sum(profile_checks),
                sampled_shaft_distance_mm=shaft.distToShape(shape)[0])
    assert report['one_connected_solid']
    assert report['shaft_intersection_mm3']<1e-5
    assert report['case_crown_gap_mm']>=.49
    assert all(profile_checks),'Socket must contain real alternating internal tooth surfaces'
    interfaces.append(report)
face=shapes['FacePanel']; assert len(face.Solids)==1 and face.isValid()
bill=face.common(Part.makeBox(11,51,2.2,V(29.4,-25.5,86)))
assert bill.Volume>900
gaps=[]
for angle in range(13):
    jaw=shapes['Jaw'].copy();jaw.rotate(V(-16,0,90),V(0,1,0),angle)
    gaps.append(dict(jaw_angle_deg=angle,bill_gap_mm=bill.distToShape(jaw)[0],
                     face_intersection_mm3=face.common(jaw).Volume))
assert min(row['bill_gap_mm'] for row in gaps)>=4.09
assert max(row['face_intersection_mm3'] for row in gaps)<1e-5
result=dict(source_cad_sha256=hashlib.sha256((C/'MicroDuckling_R01.FCStd').read_bytes()).hexdigest(),
            source_assembly_sha256=hashlib.sha256((C/'assembly.json').read_bytes()).hexdigest(),
            fit_status='UNVERIFIED: illustrative radial tooth hypothesis, not a measured manufacturer spline. These tests prove only nominal CAD consistency; printer resolution, actual fits and loaded tooth life need physical tests.',
            retired_parts_absent=True,interfaces=interfaces,
            integrated_face=dict(single_connected_solid=True,upper_bill_plate_thickness_mm=2.2,
                                 plate_material_volume_mm3=bill.Volume, jaw_samples=gaps))
(C/'direct_interface_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8',newline='\n')
print(json.dumps(result,indent=2))
