"""Nominal R08 direct sockets and shell-mounted upper mouth. Does not certify physical fit."""
import hashlib
import json
import math
import FreeCAD as A
import Part
from build_paths import BUILD_ROOT
from upper_mouth_r08 import hex_z

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
bill=shapes['UpperMouthBase']; hood=shapes['HeadHood']; jaw=shapes['Jaw']
assert len(bill.Solids)==1 and bill.isValid()
assert abs(bill.BoundBox.XMax-jaw.BoundBox.XMax)<1e-5
assert abs(bill.BoundBox.YLength-jaw.BoundBox.YLength)<1e-5
assert bill.common(hood).Volume<1e-5
assert bill.distToShape(face)[0]>.25
assert face.BoundBox.XMax<31
mounts=[]
for side in ['Left','Right']:
    screw=shapes['UpperMouthScrew'+side]; nut=shapes['UpperMouthNut'+side]
    seated_area=sum(a.common(b).Area for a in screw.Faces for b in bill.Faces
                    if isinstance(a.Surface,Part.Cone) and isinstance(b.Surface,Part.Cone))
    assert screw.common(bill).Volume<1e-5
    assert seated_area>1, 'Countersunk head must bear on its conical seat'
    assert abs(screw.BoundBox.ZMin-bill.BoundBox.ZMin)<1e-5
    assert screw.common(hood).Volume<1e-5
    assert nut.common(hood).Volume<1e-5
    y=22 if side=='Left' else -22
    driver=hex_z(18,y,67,1.3,16.49)
    tool_intersections={name:driver.common(shapes[name]).Volume for name in ['UpperMouthBase','HeadHood','UpperMouthScrew'+side]}
    assert max(tool_intersections.values())<1e-5
    mounts.append(dict(driver_hex_af_mm=1.3,driver_probe_intersections_mm3=tool_intersections,
                       driver_scope='Straight underside driver on loose hood/base subassembly; jaw, FacePanel, electronics and body absent. Actual tool and handling access unverified.',side=side,fastener='M2x8 countersunk with M2 captive nut',
                       head_flush=True,head_seat_contact_area_mm2=seated_area,
                       printed_clearance_hole_mm=2.3,countersink_included_angle_deg=90,head_rim_height_mm=.2,head_total_height_mm=1.2,
                       register_radial_allowance_mm=.15,register_axial_allowance_mm=.2))
gaps=[]
for angle in range(13):
    moved=jaw.copy();moved.rotate(V(-16,0,90),V(0,1,0),angle)
    gaps.append(dict(jaw_angle_deg=angle,bill_gap_mm=bill.distToShape(moved)[0],
                     base_intersection_mm3=bill.common(moved).Volume))
assert min(row['bill_gap_mm'] for row in gaps)>=.99
assert max(row['base_intersection_mm3'] for row in gaps)<1e-5
result=dict(source_cad_sha256=hashlib.sha256((C/'MicroDuckling_R01.FCStd').read_bytes()).hexdigest(),
            source_assembly_sha256=hashlib.sha256((C/'assembly.json').read_bytes()).hexdigest(),
            fit_status='UNVERIFIED: illustrative radial tooth hypothesis, not a measured manufacturer spline. These tests prove only nominal CAD consistency; printer resolution, actual fits and loaded tooth life need physical tests.',
            retired_parts_absent=True,interfaces=interfaces,
            shell_upper_mouth=dict(separate_connected_print=True,upper_plate_thickness_mm=2.0,
                front_x_mm=bill.BoundBox.XMax,width_mm=bill.BoundBox.YLength,
                same_front_and_width_as_jaw=True,face_clearance_mm=bill.distToShape(face)[0],
                hood_intersection_mm3=bill.common(hood).Volume,mounts=mounts,jaw_samples=gaps))
(C/'direct_interface_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8',newline='\n')
print(json.dumps(result,indent=2))
