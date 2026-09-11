"""Reproducible MicroDuckling R01 engineering prototype; FreeCAD Python, mm.
Source parameters drive geometry. Unknown vendor interfaces remain fit hypotheses.
"""
import FreeCAD as A, Part, MeshPart
from pathlib import Path
import math, json, sys
from body_r04 import body_solids
import hardware_r02 as HW
from direct_mount_r07 import DEFAULTS as SPLINE, spline_y, socket_y
from build_paths import BUILD_ROOT as R
O=R/'cad'
for p in [O,O/'meshes',O/'stl',O/'coupons',O/'simulation_meshes']:p.mkdir(parents=True,exist_ok=True)
V=A.Vector
P=dict(body_rx=38.,body_ry=39.,body_rz=18.5,body_x=3.,body_z=46.5,wall=1.3,
       body_dimensions_mm=[76,78,37],design_revision='R07 integrated face bill and direct servo sockets', direct_spline=SPLINE,case_running_clearance=.30,shell_register_clearance=.30,
       servo_signal_source='ESP32-CAM GPIO; pin assignment requires firmware review',power_topology='Single shared 5 V regulator for servos and ESP32-CAM',
       hip_z=38.,servo_y=7.,servo_case_l=22.8,servo_case_w=12.4,servo_case_h=28.5,
       shaft_offset_ASSUMED=6.2,shaft_tip_ASSUMED=32.5,
       ear_pitch_ASSUMED=27.7,ear_depth_ASSUMED=18.5,ear_thickness_ASSUMED=2.8,
       leg_y=42.6,leg_thickness=3.6,foot_radius=110.,foot_thickness=2.2,tread_thickness=.6,
       hip_limit_deg=12.,neck_limit_deg=45.,jaw_limit_deg=12.,
       head_shift_z=-10.,head_base_z=84.,head_front_x=31.,head_rear_x=-33.,head_halfwidth=26.,head_shoulder_inset_mm=8.,head_shoulder_height_mm=10.,
       neck_pivot_z=80.,jaw_pivot_x=-16.,jaw_pivot_z=90.,
       face_mount_y=20,face_mount_z=[102,119],hood_mount_x=-25,clamp_mount_y=15,head_dimensions_mm=[64,52,52],jaw_width_mm=54,
       density_g_mm3=.00124,interface_clearance=.4,release_status='ENGINEERING PROTOTYPE - hardware fit and walking unverified')
(O/'parameters.json').write_text(json.dumps(P,indent=2),encoding='utf-8',newline='\n')
D=A.newDocument('MicroDuckling_R01'); shapes={}; records=[]; meshes={}; features=[]
white='#eee9df';orange='#f87712';black='#25282b';steel='#8d9398'
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def cyl(x,y,z,r,h,axis=V(0,0,1)):return Part.makeCylinder(r,h,V(x,y,z),axis)
def union(ss):
    q=ss[0]
    for s in ss[1:]:q=q.fuse(s)
    refined=q.removeSplitter()
    return refined if not refined.isNull() and refined.isValid() else q
def ellipsoid(cx,cy,cz,rx,ry,rz):
    m=A.Matrix();m.A11=rx;m.A22=ry;m.A33=rz
    s=Part.makeSphere(1).transformGeometry(m);s.translate(V(cx,cy,cz));return s
def mirror(s):q=s.copy();return q.mirror(V(),V(0,1,0))
def polyextr(points,vector):return Part.Face(Part.makePolygon([V(*p) for p in points]+[V(*points[0])])).extrude(V(*vector))
def faceted_port(center,radius,depth,axis='Z'):
    # Circumscribed octagon retains the circle's full radial clearance.
    a=radius*(math.sqrt(2)-1)
    pairs=[(-a,-radius),(a,-radius),(radius,-a),(radius,a),(a,radius),(-a,radius),(-radius,a),(-radius,-a)]
    x,y,z=center
    if axis=='Z':return polyextr([(x+u,y+v,z) for u,v in pairs],(0,0,depth))
    if axis=='Y':return polyextr([(x+u,y,z+v) for u,v in pairs],(0,depth,0))
    return polyextr([(x,y+u,z+v) for u,v in pairs],(depth,0,0))
def rounded(x,y,z,l,w,h,r=2):return union([box(x+r,y,z,l-2*r,w,h),box(x,y+r,z,l,w-2*r,h)]+[cyl(xx,yy,z,r,h) for xx in [x+r,x+l-r] for yy in [y+r,y+w-r]])
def rounded_y(x,y,z,l,w,h,r=1):
    q=rounded(x,z,0,l,h,w,r);q.rotate(V(),V(1,0,0),90);q.translate(V(0,y+w,0));return q
def rounded_x(x,y,z,l,w,h,r=1):
    q=rounded(y,z,0,w,h,l,r);q.rotate(V(),V(1,1,1),120);q.translate(V(x,0,0));return q
def finish(label,s,r,predicate):
    edges=[e for e in s.Edges if predicate(e)]
    if not edges:raise RuntimeError('Missing finishing edges: '+label)
    result=s.makeFillet(r,edges)
    if not result.isValid() or len(result.Solids)!=1:raise RuntimeError('Invalid fillet: '+label)
    features.append(dict(feature=label,radius_mm=r,edge_count=len(edges),valid=True));return result
def at_plane(axis,value):
    return lambda e:abs(getattr(e.BoundBox,axis+'Min')-value)<.001 and getattr(e.BoundBox,axis+'Length')<.001
def lead(x,y,z,rad,depth=.2,axis=V(0,0,1)):
    return Part.makeCone(rad+depth,rad,depth,V(x,y,z),axis)
def sloty(x,y,z,rad,depth,lo,hi):return union([cyl(x,y,z+lo,rad,depth,V(0,1,0)),cyl(x,y,z+hi,rad,depth,V(0,1,0)),box(x-rad,y,z+lo,2*rad,depth,hi-lo)])
def hexy(x,y,z,af,h):
    rr=af/math.sqrt(3);return polyextr([(x+rr*math.cos(i*math.pi/3),y,z+rr*math.sin(i*math.pi/3)) for i in range(6)],(0,h,0))
def placed(s,name,link):
    q=s.copy()
    if link in ['head','jaw']:q.translate(V(0,0,P['head_shift_z']))
    if link=='left_leg' or name=='ServoLeft':q.translate(V(0,2,0))
    if link=='right_leg' or name=='ServoRight':q.translate(V(0,-2,0))
    return q

def add(name,s,link='body',kind='print',color=white,mass=None,note='',components=None):
    refined=s.removeSplitter()
    if not refined.isNull() and refined.isValid():s=refined
    s=placed(s,name,link)
    if len(s.Solids)==1:s=s.Solids[0]
    if s.isNull() or not s.isValid():raise RuntimeError('INVALID '+name)
    if kind in ['print','coupon'] and len(s.Solids)!=1:raise RuntimeError('DISCONNECTED '+name+' '+str([(round(q.Volume,2),list(q.CenterOfMass)) for q in s.Solids]))
    ob=D.addObject('PartDesign::Feature',name);ob.Label=name;ob.Shape=s
    for key,val in [('ComponentType',kind),('RigidLink',link),('Notes',note)]:ob.addProperty('App::PropertyString',key);setattr(ob,key,val)
    ob.addProperty('App::PropertyColor','ReviewColor');ob.ReviewColor=tuple(int(color[i:i+2],16)/255 for i in [1,3,5])
    m=mass if mass is not None else s.Volume*P['density_g_mm3']
    ob.addProperty('App::PropertyFloat','EstimatedMass_g');ob.EstimatedMass_g=m
    # Fine sampling is needed where the hood relief crosses the small rear returns.
    linear,angular=(.025,.09) if name=='HeadHood' else (.075,.18)
    mesh=MeshPart.meshFromShape(Shape=s.cleaned(),LinearDeflection=linear,AngularDeflection=angular,Relative=False)
    if kind in ['print','coupon'] and not mesh.isSolid():raise RuntimeError('OPEN PRINT MESH '+name)
    vs,fs=mesh.Topology
    payload=dict(positions=[round(c,5) for v in vs for c in v],indices=[n for f in fs for n in f])
    if name=='FacePanel':
        # Optional painted bill region on the SAME mesh and single printed solid.
        # Partition original surface triangles once; no overlaid surface geometry.
        face_triangles=[];bill_triangles=[]
        for triangle in fs:
            centroid=sum((vs[index] for index in triangle),V())/3
            target=bill_triangles if centroid.x>30.2001 and centroid.z<88.21 else face_triangles
            target.extend(triangle)
        payload['indices']=face_triangles+bill_triangles
        payload['materials']=[dict(name='Face print',color=black,roughness=.6,metalness=0),
                              dict(name='Optional orange bill paint',color=orange,roughness=.6,metalness=0)]
        payload['groups']=[dict(start=0,count=len(face_triangles),materialIndex=0),
                           dict(start=len(face_triangles),count=len(bill_triangles),materialIndex=1)]
    if components:
        payload=dict(positions=[],indices=[],materials=[],groups=[])
        for component in components:
            part_mesh=MeshPart.meshFromShape(Shape=placed(component['shape'],name,link).cleaned(),LinearDeflection=.07,AngularDeflection=.18,Relative=False)
            vertices,triangles=part_mesh.Topology
            start=len(payload['indices']);offset=len(payload['positions'])//3
            payload['positions'].extend(round(c,5) for vertex in vertices for c in vertex)
            payload['indices'].extend(n+offset for triangle in triangles for n in triangle)
            material=len(payload['materials'])
            payload['materials'].append(dict(name=component['name'],color=component['color'],roughness=.45,metalness=.65 if component['color'] in ['#b8bec5','#c9a34d','#d2b86f'] else 0))
            payload['groups'].append(dict(start=start,count=len(triangles)*3,materialIndex=material))
    (O/'meshes'/f'{name}.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8',newline='\n')
    b=s.BoundBox; c=sum((v.CenterOfMass*v.Volume for v in s.Solids),V())/s.Volume
    rec=dict(name=name,object_name=ob.Name,link=link,kind=kind,color=color,mass_g=m,com_mm=list(c),volume_mm3=s.Volume,dimensions_mm=[b.XLength,b.YLength,b.ZLength],note=note)
    records.append(rec);shapes[name]=s;meshes[name]=mesh
    if kind in ['print','coupon']:
        me=mesh.copy();vs=me.Topology[0];me.translate(-min(v.x for v in vs),-min(v.y for v in vs),-min(v.z for v in vs));me.write(str(O/('coupons' if kind=='coupon' else 'stl')/f'{name}.stl'))
    print(name,round(m,2),'g',flush=True);return s
def screw_y(name,x,y,z,length,link='body',sign=1,diam=2):
    s=union([cyl(x,y,z,diam/2,length,V(0,1,0)),cyl(x,y+length,z,diam,1.4,V(0,1,0))]);s=s.cut(cyl(x,y+length+.4,z,.7,1.3,V(0,1,0)))
    note=('Vendor-specific servo output retaining screw; displayed 2 mm diameter is an UNVERIFIED envelope, not an M2 thread specification. Match actual spline thread and available engagement.' if 'ShaftScrew' in name else 'M2 nominal fastener; thread not modeled. Clearance/pilot or captive-nut interface requires physical fit testing.')
    return add(name,s if sign==1 else mirror(s),link,'hardware',steel,.13,note)
def servo_y(x,y,z):
    # x,z are output axis; y is flat base. Noncircular twin-lobe crown, conservative envelope.
    case=box(x-6.2,y,z-6.2,22.8,25.8,12.4)
    ears=box(x-10.85,y+18.5,z-6.2,32.1,2.8,12.4)
    crown=union([cyl(x,y+25.8,z,6.2,2.7,V(0,1,0)),cyl(x+8,y+25.8,z,3.2,2.7,V(0,1,0))])
    s=union([case,ears,crown])
    for xx in [x+5.2-13.85,x+5.2+13.85]:s=s.cut(cyl(xx,y+18.3,z,1.1,3.3,V(0,1,0)))
    return s
hardware_mounts={}
def install_model(name,model,origin,link,mass,basis=((1,0,0),(0,1,0),(0,0,1))):
    matrix=A.Matrix()
    for column,axis in enumerate(basis,1):
        for row,value in enumerate(axis,1):setattr(matrix,'A'+str(row)+str(column),value)
    matrix.A14,matrix.A24,matrix.A34=origin
    def transform(shape):
        q=shape.copy();q.transformShape(matrix,True);return q
    components=[dict(c,shape=transform(c['shape'])) for c in model['components']]
    result=add(name,transform(model['shape']),link,'hardware',components[0]['color'],mass,model['notes'],components)
    records[-1]['pcb_dimensions_mm']=model.get('pcb_dimensions_mm')
    records[-1]['pcb_basis_global']=[list(axis) for axis in basis]
    records[-1]['material_groups']=len(components)
    hardware_mounts[name]=[(matrix.multVec(V(h[0],h[1],0)),h[2]) for h in model.get('mount_holes',[])]
    return result
# Motors and common chassis: open gear end, integral printed direct drive sockets, open crown clearance.
hip=P['hip_z']; earxs=[5.2-13.85,5.2+13.85]
leftservo=servo_y(0,5,hip)
add('ServoLeft',leftservo,kind='hardware',color=black,mass=13.32,note='Case/crown portion of 13.4 g nominal complete servo; 0.08 g output shaft is on the driven link. Conservative nominal MG90S envelope; lug pitch, turret, shaft require actual sample measurements.')
add('ServoRight',mirror(leftservo),kind='hardware',color=black,mass=13.32)
add('OutputSplineLeft',spline_y(0,33.5,hip,4),'left_leg','hardware',steel,.08,'Illustrative unverified output teeth; rotates with left leg. Included in complete servo mass.')
add('OutputSplineRight',mirror(spline_y(0,33.5,hip,4)),'right_leg','hardware',steel,.08,'Illustrative unverified output teeth; rotates with right leg. Included in complete servo mass.')
# Compact layout derived from the user's physical three-servo arrangement.
# The14mm central case gap accepts12.4mm neck width with0.8mm air each side.
body_geometry=body_solids()
chassis=rounded(-30,-30,30,51,60,2.4,3)
neck=servo_y(0,0,0);neck.rotate(V(),V(1,0,0),90);neck.translate(V(0,0,41))
add('ServoNeck',neck,kind='hardware',color=black,mass=13.32)
neckshaft=spline_y(0,28.5,0,4);neckshaft.rotate(V(),V(1,0,0),90);neckshaft.translate(V(0,0,51))
add('OutputSplineNeck',neckshaft,'head','hardware',steel,.08,'Illustrative unverified output teeth; rotates with head. Included in complete servo mass.')
battery=box(-31,-21.5,36.5,23,43,13);battery=battery.makeFillet(.65,battery.Edges)
# Physical pack shape and foil label occupy the selected43x23x13mm envelope.
foil=box(-30,-16,49.48,21,32,.02)
battery_parts=[dict(name='Black pack sleeve',shape=battery.cut(foil).removeSplitter(),color='#21252b'),dict(name='Foil identification strip',shape=foil,color='#c4bdac')]
add('Battery',battery,kind='hardware',color='#21252b',mass=28,note='Gens ace GEA4502S60XT3 nominal43x23x13mm pack; rounded sleeve and identification foil. Keep low for balance. Published envelope does not establish pouch swelling or connector/lead tolerances.',components=battery_parts)
install_model('IMU',HW.imu(),(-12.62,-12.7,54.2),'body',1.7,basis=((0,1,0),(-1,0,0),(0,0,1)))
# Low battery cradle, removable soft strap inserted before servo placement.
tray=rounded(-33,-23,34,26,46,1.8,1)
for yy in [-24.2,22.2]:tray=tray.fuse(box(-33,yy,35.8,26,2,2.7))
# strap slots added after solid union
chassis=union([chassis,tray,box(-28,-3,30,4,6,6)])
# Central floor supports the upright neck; two short bridges keep it below body cap.
chassis=union([chassis,box(-12,-6.6,38.6,36,13.2,2),box(-12,-3,30,4,6,10),box(20,-3,30,4,6,10)])
for xx in earxs:
    post=rounded(xx-3.3,-7.5,49.9,6.6,15,9.6,1.1).cut(cyl(xx,0,55.8,.85,4.2))
    chassis=chassis.fuse(post)
chassis=union([chassis,box(19,-3,39,4,6,12),box(-12,-15,50,5,30,2),box(-14,-3,49.8,6,6,3)])
# Hip-ear pillars retain stock cases, with open crown and integral print sockets.
for sg in [1,-1]:
    for xx in earxs:
        post=rounded_y(xx-3.3,22.5,30,6.6,3,15,1.1)
        cut=cyl(xx,22.1,38,.85,3.7,V(0,1,0))
        post=post.cut(cut);chassis=chassis.fuse(post if sg==1 else mirror(post),0.001)
# The torso retains only the low battery and its rigidly attached IMU.
chassis=union([chassis,rounded(-31.6,-14,51.7,19.3,28,2.1,1),box(-15,-3,49.5,4,6,4.5)])
# Shell anchors are horizontal and accessible with hips fitted.
chassis=chassis.removeSplitter()
assert chassis.isValid(), "Invalid core before anchors"
anchors=[(-26,53),(17,53)]
for xx,zz in anchors:
    for sg in [1,-1]:
        post=union([rounded_y(xx-3,0,zz-3,6,28,6,1.2),rounded(xx-3,0,30,6,5,26,1),rounded_y(xx-3.5,26,zz-3.5,7,8,7,1.2)])
        chassis=chassis.fuse(post if sg==1 else mirror(post),0.001)
# Support head weight on a fixed annulus, independently of the rotating spline.
support=cyl(0,0,71,16,2.7).cut(cyl(0,0,70.8,12.25,3.1))
for yy in [-15,12]:support=support.fuse(rounded(-10,yy,53,4,3,20.2,.55))
for yy in [-12,12]:
    pad=rounded(-10,yy-4.5,52.3,12,9,2,1.2).cut(cyl(-2,yy,52.1,1.15,2.5))
    support=support.fuse(pad)
    boss=box(-5,yy-3.5,49.8,6,7,2.5).fuse(box(-11,-15 if yy<0 else 6.5,50,12,8.5,2.3))
    chassis=chassis.fuse(boss).cut(cyl(-2,yy,50,.85,2.5))
add('FixedNeckSupport',support,note='Removable annular head support. Install after lowering neck servo into open central gap; two M2x4 screws into1.7mm pilot holes that require physical coupon testing.')
add('ThrustShim',cyl(0,0,73.7,16,.2).cut(cyl(0,0,73.6,12.25,.4)),kind='hardware',color='#dad9d2',mass=.14,note='Nominal0.2mm PTFE thrust washer closes support-to-shoulder gap; select thickness against actual fully seated socket stack so shoulder bears without axial preload.')
print('CORE BEFORE CUT',chassis.Volume,len(chassis.Solids),flush=True)
for n in ['ServoLeft','ServoRight','ServoNeck','Battery','IMU']:
    chassis=chassis.cut(shapes[n]);print('CORE CUT',n,chassis.Volume,len(chassis.Solids),flush=True)
# Nominal case running clearance is separate from the ear contact faces.
hipkeep=box(-6.5,6.7,hip-6.5,23.4,26.4,13)
neckkeep=box(-6.5,-6.5,40.7,23.4,13,26.4)
chassis=chassis.cut(hipkeep).cut(mirror(hipkeep)).cut(neckkeep)
print('CORE CLIP BEFORE',chassis.Volume,flush=True)
chassis=chassis.common(body_geometry['inner'])
chassis=chassis.fuse(box(17,-3,31,1,6,23))
chassis=chassis.fuse(box(18.95,-1.05,32.35,1.1,2.1,6.3))
rearbrace=polyextr([(-18,22.2,30),(-14,22.2,30),(-20,22.2,38),(-20,22.2,54),(-24,22.2,54),(-24,22.2,38)],(0,2,0))
chassis=chassis.fuse(rearbrace).fuse(mirror(rearbrace))
print('CORE CLIP AFTER',chassis.Volume,len(chassis.Solids),flush=True)
for xx,zz in anchors:
    for sg in [1,-1]:
        cut=cyl(xx,23.8,zz,1.15,13,V(0,1,0)).fuse(hexy(xx,26,zz,4.2,2)).fuse(box(xx-2.1,26,zz-9,4.2,2,9))
        chassis=chassis.cut(cut if sg==1 else mirror(cut))
chassis=Part.makeCompound([q for q in chassis.Solids if q.Volume>5]).removeSplitter()
for xx in earxs:
    pilot=cyl(xx,22.1,38,.85,3.7,V(0,1,0))
    chassis=chassis.cut(pilot).cut(mirror(pilot))
    mouth=lead(xx,25.5,38,.85,.2,V(0,-1,0));chassis=chassis.cut(mouth).cut(mirror(mouth))
strap_cut=box(-19.3,21.7,33.15,3.6,3,6)
chassis=chassis.cut(strap_cut).cut(mirror(strap_cut))
# The IMU's actual two mounting holes, kept above the battery pouch.
for point,diam in hardware_mounts['IMU']:
    x,y,z=point
    boss=cyl(x,y,50.5,2.6,z-.035-50.5).cut(cyl(x,y,50.3,.85,4.0))
    chassis=chassis.fuse(boss)
for point,diam in hardware_mounts['IMU']:
    chassis=chassis.cut(cyl(point.x,point.y,49.6,.85,4.8))
# The stock hip ears slide outward above the floor, with0.30mm vertical room.
ear_slide=rounded_y(-11.15,25.7,31.5,32.7,9,1.2,.25)
chassis=chassis.cut(ear_slide).cut(mirror(ear_slide))
from electronics_r04 import build_electronics
chassis=build_electronics(globals(),chassis)
# Flatten the pack bed for a cut-sheet pad; do not force foam over tall pedestals.
chassis=chassis.cut(box(-30.8,-21.3,35.8,22.6,42.6,.8)).removeSplitter()
add('Chassis',chassis,note='Three-servo torso with low battery, IMU mounts and one vertical shared 5 V regulator. Separate PWM controller frame/posts and logic-regulator tray/arms removed. ESP32-CAM drives four servo signals directly; routing and pin selection require firmware review. Actual hardware fit, insulation and wiring require physical validation.')
# Continuous soft tape route, clear of the rear pedestal and beneath the IMU.
# It is cut/sewn material, not a rigid printed clamp around a pouch battery.
strap=rounded_x(-19,-22.7,33.4,3,45.4,16.55,1).cut(
    rounded_x(-19.1,-22.35,33.75,3.2,44.7,15.85,.65))
strap=strap.fuse(box(-19,22.65,40,3,.4,7)).removeSplitter()
add('BatteryStrap',strap,kind='hardware',color='#575c64',mass=.25,
    note='Custom3mm-wide soft tape restraint, nominal0.35mm thick, with7mm side lap. Thread through3.6mm chassis slots before assembly. Material, sewn/bonded lap strength and snug fit without pouch compression need physical qualification;0.25g allowance.')
add('BatteryPad',rounded(-30.5,-21,35.8,22,42,.7,1),kind='hardware',color='#454a51',mass=.05,
    note='Cut22x42x0.7mm electrically insulating compliant pad below pack;0.05g allowance. Actual foam thickness, compression and adhesive need qualification. Keep adhesive and stitching away from the pouch itself.')

# Two complete rigid leg-feet. True spherical rocker underside with smooth rounded ends.
footmask=rounded(-34,2,-1,70,52,21,9)
center=V(0,28,110)
outer=Part.makeSphere(109.4,center);inner=Part.makeSphere(107.2,center)
sole=outer.cut(inner).common(footmask)
sole=finish('Foot upper perimeter',sole,.45,lambda e:abs((e.valueAt((e.FirstParameter+e.LastParameter)/2)-center).Length-107.2)<.01)
tread=Part.makeSphere(110,center).cut(outer).common(footmask)
right=Part.BezierCurve();right.setPoles([V(9,40.6,38),V(7,40.6,27),V(9,40.6,11),V(15,40.6,2.8)])
left=Part.BezierCurve();left.setPoles([V(-15,40.6,2.8),V(-9,40.6,11),V(-7,40.6,27),V(-9,40.6,38)])
outline=Part.Wire([Part.Arc(V(-9,40.6,38),V(0,40.6,47),V(9,40.6,38)).toShape(),right.toShape(),Part.makeLine(V(15,40.6,2.8),V(-15,40.6,2.8)),left.toShape()])
leg=Part.Face(outline).extrude(V(0,3.6,0))
leg=finish('Leg upright edge rolls',leg,.55,lambda e:at_plane('Y',40.6)(e) or at_plane('Y',44.2)(e))
leg=leg.fuse(sole).fuse(polyextr([(-8,37,3),(8,37,3),(4,37,25),(-4,37,25)],(0,3.8,0)))
leg=leg.common(outer)
# Integral hub reaches inboard to the actual modeled output teeth; 0.5 mm
# nominal axial clearance remains between hub entry and the servo crown.
leg=leg.fuse(cyl(0,34,38,5.5,10.2,V(0,1,0)))
leg=socket_y(leg,0,34,38,44.2,42.2)
for side,sg in [('Left',1),('Right',-1)]:
    link=side.lower()+'_leg';q=leg if sg==1 else mirror(leg)
    add('LegFoot'+side,q,link,color=orange,note='Single rigid leg, rocker foot and integral direct spline hub. Illustrative unverified 20-tooth 4.8/4.30 mm profile, 0.06 mm radial allowance; 3.5 mm nominal shaft overlap and axial center screw. Physical fit and torque capacity require coupon and loaded bench testing.')
    add('Tread'+side,tread if sg==1 else mirror(tread),link,'tread',black,.9,'0.6mm equivalent conforming traction layer. Start localized thin silicone strips; coefficient and compression must be measured.')
    screw_y('ShaftScrew'+side,0,35.5,38,6.7,link,sg,2)
# Removable rounded body clamshells; wingless and without a tail.
outerbody=body_geometry['outer'];innerbody=body_geometry['inner']
body=outerbody.cut(innerbody)
neck_opening=faceted_port((0,0,59),18.5,25).fuse(rounded(-11.4,-6.7,59,34,13.4,25,2))
body=body.cut(neck_opening)
for sg in [1,-1]:body=body.cut(faceted_port((0,30 if sg==1 else -60,38),12.5,30,'Y'))
for sg in [1,-1]:
    cut=rounded_y(-11.5,5,31.3,33.6,55,13.4,2)
    body=body.cut(cut if sg==1 else mirror(cut))
for xx,zz in anchors:
    for sg in [1,-1]:
        # cylindrical mounting boss extends into shell; cut remains accessible from outside.
        b=cyl(xx,34.2,zz,3.6,12,V(0,1,0)).common(outerbody).cut(cyl(xx,34,zz,1.15,15,V(0,1,0)))
        body=body.fuse(b if sg==1 else mirror(b))
        cut=cyl(xx,36,zz,2.3,30,V(0,1,0));body=body.cut(cut if sg==1 else mirror(cut))
        screw_y('BodyScrew'+str(xx)+str(sg),xx,24,zz,12,'body',sg,2)
        nut=hexy(xx,26,zz,4,1.6).cut(cyl(xx,25.8,zz,.85,2,V(0,1,0)))
        add('BodyNut'+str(xx)+str(sg),nut if sg==1 else mirror(nut),kind='hardware',color=steel,mass=.1)
for xx,zz in anchors:
    for sg in [1,-1]:
        bore=cyl(xx,30,zz,1.15,24,V(0,1,0));body=body.cut(bore if sg==1 else mirror(bore))
# Through-wall rear cable access. R04's old cutter stopped at the new rear face.
# Extend beyond the inner wall and locating lip, stopping before the battery.
service=polyextr([(-40,y,z) for y,z in [(-7,40),(-5,38),(5,38),(7,40),
                                    (7,46),(5,48),(-5,48),(-7,46)]],(8.5,0,0))
body=finish('Rear cable port outer edge',body.cut(service),.35,
            lambda e:at_plane('X',-35)(e) and e.BoundBox.YMin>=-7.01
            and e.BoundBox.YMax<=7.01 and e.BoundBox.ZMin>=37.99
            and e.BoundBox.ZMax<=48.01)
vents=[]
for xx in [-20,-15,-10]:
    vent=box(xx,-7,59,2,14,20).fuse(cyl(xx+1,-7,59,1,20)).fuse(cyl(xx+1,7,59,1,20))
    vents.append(vent);body=body.cut(vent)
bodyL=body.common(box(-100,.15,0,200,100,200));bodyR=body.common(box(-100,-100,0,200,99.85,200))
# Overlapping register lip slides inside the opposite shell with0.30mm radial allowance.
register_inner=body_geometry['register_inner']
root=body_geometry['register_root_outer'].cut(register_inner).common(box(-70,.15,10,140,1.45,80))
tongue=body_geometry['register_outer'].cut(register_inner).common(box(-70,-1.25,10,140,1.8,80))
register=root.fuse(tongue).cut(service).cut(neck_opening)
for vent in vents:register=register.cut(vent)
# Local interruptions clear the chassis floor and central structural posts by0.30mm.
register=register.cut(box(-32,-2,29.7,56,4,3.0))
register=register.cut(box(17.9,-2,29.7,8,4,30.2))
register=register.cut(box(-34,-2,33.7,4,4,2.4)).cut(box(-32.5,-2,51.4,3.0,4,5.0))
# R06 restores the locating lip where the removed PWM board needed two reliefs.
bodyL=bodyL.fuse(register)
add('BodyShellLeft',bodyL,note='Compact faceted torso with flat panels, chamfered shoulders, 0.8 mm edge fillets and 1.3 mm walls. Registered clamshell seam has 0.30 mm nominal clearance; no tail or wings.')
add('BodyShellRight',bodyR)
# Neck journal and hollow rotating head carrier. Slip bearing carries head weight on frame.
carrier=union([cyl(0,0,81.3,11.8,2.7),cyl(0,0,83.9,16,6.1),rounded(-18,-18,90,36,36,2,4)])
carrier=carrier.fuse(cyl(0,0,80,5.5,12))
# Form a Y-axis socket then rigidly rotate it onto the vertical neck output.
carrier.rotate(V(),V(1,0,0),-90)
carrier=socket_y(carrier,0,80,0,92,90.5)
carrier.rotate(V(),V(1,0,0),90)
# Radial open cable passage avoids the central socket/shaft; strap wiring clear of yaw sweep.
carrier=carrier.cut(box(-9,5,80,19.8,5,15))
for yy in [-13,13]:carrier=carrier.cut(cyl(5,yy,87.8,.85,4.5))
carrier=carrier.cut(box(14.5,-19,89.9,6,38,4))
add('NeckCarrier',carrier,'head',color=black,note='Slip thrust shoulder0.20mm above fixed support with nominal0.20mm PTFE shim; journal diametral clearance0.9mm. Integral direct spline socket reaches the output shaft; shim thickness must match actual seated socket to carry weight without preload. Spline fit and strength unverified. Cable notch separate from output shaft.')
# Narrow head is a separately authored assembly; purchased geometry is never scaled.
def screw_z(name,x,y,z,length,link,diam=2):
    screw=union([cyl(x,y,z,diam/2,length),cyl(x,y,z+length,diam,1.3)])
    note=('Vendor-specific servo output retaining screw; displayed 2 mm diameter is an UNVERIFIED envelope, not an M2 thread specification. Match actual spline thread and available engagement.' if 'ShaftScrew' in name else 'M2 nominal screw; selected head, pilot and engagement strength require physical fit testing.')
    return add(name,screw,link,'hardware',steel,.16,note)
from head_r04 import build_head
build_head(globals())
for i,(point,diam) in enumerate(hardware_mounts['IMU']):
    screw_z('IMUMountScrew'+str(i),point.x,point.y,49.8,6,'body')
for yy in [-13,13]:screw_z('HeadFrameScrew'+str(yy),5,yy,89,20,'head')
for xx in earxs:screw_z('NeckMountScrew'+str(xx),xx,0,56.3,6,'body')
for yy in [-12,12]:screw_z('NeckSupportScrew'+str(yy),-2,yy,50.3,4,'body')
screw_z('NeckShaftScrew',0,0,81.5,9,'head')
for sg in [1,-1]:
    for k,xx in enumerate(earxs):screw_y('HipMountScrew'+str(sg)+'_'+str(k),xx,22.3,38,6,'body',sg,2)
# Flexible harnesses are schematic cable routes, never rectangular volume proxies.
def cable(points,radius):
    nodes=[V(*p) for p in points];segments=[]
    for a,b in zip(nodes[:-1],nodes[1:]):segments.append(Part.makeCylinder(radius,(b-a).Length,a,(b-a).normalize()))
    segments.extend(Part.makeSphere(radius,p) for p in nodes[1:-1])
    return union(segments)
body_wires=[];head_wires=[]
for i,color in enumerate(['#b94435','#23252a','#ce9e34']):
    offset=(i-1)*1.0
    body_wires.append(dict(name='Torso cable corridor '+str(i),color=color,shape=cable([(-6+offset,20+offset,48),(-3+offset,18+offset,60),(-3+offset,8+offset,68),(-3+offset,8+offset,80)],.42)))
    y=7+i;end_y=11.43 if i<2 else -11.43;end_z=104.36 if i!=1 else 101.82
    approach_x=6.7 if i==1 else 7.7
    head_points=[(-3+offset,y,80),(-3+offset,y,81),(10,y,81),(10,y,107+i),
                 (approach_x,y,107+i),(approach_x,end_y,107+i),(approach_x,end_y,end_z)]
    if i==1:head_points.append((7.7,end_y,end_z))
    head_wires.append(dict(name='Head cable corridor '+str(i),color=color,
                           shape=cable([(x,y,z-P['head_shift_z']) for x,y,z in head_points],.42)))
add('HarnessBody',Part.makeCompound([p['shape'] for p in body_wires]),kind='harness',color=black,mass=6,note='Illustrative trunk route and 6 g wiring/connector allowance for direct ESP32-CAM servo signals and shared 5 V power. Individual signal/ground branches and power distribution are not yet routed. Detailed routing, lengths, strain relief and powered movement require the physical build.',components=body_wires)
add('HarnessHead',Part.makeCompound([p['shape'] for p in head_wires]),'head','harness',black,2.5,
    'Three indicative0.84mm-diameter cable corridors join the torso paths at neutral and reach the current ESP32 header region. Carrier notch widened1.8mm to bypass mouth servo. Not a pin assignment or complete loom: mating plugs, all branches, smooth bends and a flexible yaw service loop require physical qualification.2.5g wiring allowance.',head_wires)
# Indicative 10mm-wide camera flex from the current FFC region to sensor rear.
# Actual-global X/Z profile clears the tray, SD cage and lower cradle bridge.
flex_profile=[(19.35,94.8),(20.25,94.8),(20.25,104.45),(21.9,105.3),
              (23.7,108.0),(23.7,110.6),(23.95,110.6),(23.95,110.8),
              (23.5,110.8),(23.5,108.06),(21.75,105.45),(20.05,104.55),
              (20.05,95.0),(19.35,95.0)]
ribbon=polyextr([(x,-5,z-P['head_shift_z']) for x,z in flex_profile],(0,10,0))
add('HarnessCameraRibbon',ribbon,'head','harness','#b57928',.1,
    'Indicative10mm-wide camera flex corridor from current FFC region to sensor rear, clear of rigid parts in neutral CAD. Small terminal gaps are intentional: actual flex width, length, contact insertion and smooth minimum-radius bends require measurement; not a manufactured ribbon design.')
# Actual interface extractions for first cheap fit checks.
add('SplineFitCoupon',socket_y(cyl(0,0,0,5.5,10.2,V(0,1,0)),0,0,0,10.2,8.2),kind='coupon',color=orange,mass=0,note='Representative integral hip hub: identical radial profile, 3.8 mm socket, entry chamfer, center bore and screw counterbore. All tooth dimensions unverified; measure and fit actual servo before printing full parts. Coupon is not a load qualification.')
coupon=rounded(0,0,0,59,28,2,2)
for i,gap in enumerate([.3,.45]):
    xx=2+i*28;coupon=coupon.fuse(box(xx,2,2,26.8,16.4,4)).cut(box(xx+2-gap,4-gap,-.1,22.8+gap*2,12.4+gap*2,6.2))
for i,d in enumerate([2.1,2.2,2.3,2.4]):coupon=coupon.cut(cyl(6+i*8,23,-.1,d/2,2.2))
for i,d in enumerate([1.6,1.7,1.8]):coupon=coupon.cut(cyl(40+i*6,23,-.1,d/2,2.2))
add('ClearanceCoupon',coupon,kind='coupon',color=orange,mass=0,note='MG90S body windows0.30/0.45mm per side; clearance holes2.1/2.2/2.3/2.4mm; pilot sizing holes1.6/1.7/1.8mm. Thin coupon checks diameter only, engagement strength requires representative-depth sample.')
# Persist geometry and mass data, reusable by audit/render/export scripts.
sheet=D.addObject('Spreadsheet::Sheet','DesignParameters')
for i,(k,v) in enumerate(P.items(),1):sheet.set('A'+str(i),k);sheet.set('B'+str(i),str(v))
sheet.setColumnWidth('A',270);D.recompute();D.saveAs(str(O/'MicroDuckling_R01.FCStd'))
Part.export([D.getObject(r['name']) for r in records if r['kind']=='print'],str(O/'MicroDuckling_R01.step'))
active=[r for r in records if r['kind']!='coupon'];mass=sum(r['mass_g'] for r in active)
com=[sum(r['mass_g']*r['com_mm'][i] for r in active)/mass for i in range(3)]
(O/'assembly.json').write_text(json.dumps(dict(parameters=P,parts=records,mass_g=mass,com_mm=com,status=P['release_status']),indent=2),encoding='utf-8',newline='\n')
(O/'detail_features.json').write_text(json.dumps(dict(design_revision=P['design_revision'],features=features,notes='Native solid edge treatments. Ranges and fits are design choices, not measured Microduck production dimensions.'),indent=2),encoding='utf-8',newline='\n')
print('TOTAL',mass,'COM',com,flush=True)
