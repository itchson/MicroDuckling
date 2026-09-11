"""Compact MicroDuckling camera and mouth head. Dimensions are in mm.

Purchased geometry undergoes rigid placement only. Source Z coordinates retain
the builder's documented -10mm head offset. The torso and rocker datums stay fixed.
"""
import math
import FreeCAD as A, Part
from direct_mount_r07 import integrated_upper_bill, socket_y, spline_y


def build_head(api):
    V=A.Vector
    box,cyl,union,rounded,rounded_x,rounded_y=(api[n] for n in ['box','cyl','union','rounded','rounded_x','rounded_y'])
    add,finish,at_plane,mirror,lead,hexy=(api[n] for n in ['add','finish','at_plane','mirror','lead','hexy'])
    servo_y,screw_y,screw_z=(api[n] for n in ['servo_y','screw_y','screw_z'])
    install,HW,mounts,P=(api[n] for n in ['install_model','HW','hardware_mounts','P'])
    black,steel,orange=(api[n] for n in ['black','steel','orange'])
    rear,front,half=P['head_rear_x'],P['head_front_x'],P['head_halfwidth']
    face_y=P['face_mount_y']; side_x=P['hood_mount_x']
    pivot=P['jaw_pivot_x']
    def trace(label,s):
        print('HEAD FRAME',label,s.isValid(),len(s.Solids),flush=True)

    def faceted(x,length,base,width,straight,height):
        # Shared six-sided profile: flat roof and sloping shoulders, like the torso.
        # Keep the legacy call dimensions so all nested registers remain coherent.
        top=base+straight+height;inset=P['head_shoulder_inset_mm'];drop=P['head_shoulder_height_mm']
        points=[V(x,-width,base),V(x,width,base),V(x,width,top-drop),
                V(x,width-inset,top),V(x,-width+inset,top),V(x,-width,top-drop)]
        return Part.Face(Part.makePolygon(points+[points[0]])).extrude(V(length,0,0))

    outer=finish('Faceted hood outer edge rolls',faceted(rear,front-rear,94,half,17,35),.8,lambda e:True)
    inner=finish('Faceted hood inner edge rolls',faceted(rear+1.2,front-rear,94,half-1.2,17,33.8),.4,lambda e:True)
    hood=outer.cut(inner)
    for x in [rear+3,7]:
        rib=faceted(x,1.2,94,half-1.05,17,33.95).cut(faceted(x-.1,1.4,93.8,half-2.25,17.2,32.75))
        hood=hood.fuse(rib)
    # Faceted service relief still clears the swept cheek; the pivot bore is round.
    for sg in [1,-1]:
        y=half-4 if sg==1 else -half-6
        r=13.2;corner=r*(2-math.sqrt(2))
        points=[(pivot-r+corner,y,100-r),(pivot+r-corner,y,100-r),
                (pivot+r,y,100-r+corner),(pivot+r,y,100+r-corner),
                (pivot+r-corner,y,100+r),(pivot-r+corner,y,100+r),
                (pivot-r,y,100+r-corner),(pivot-r,y,100-r+corner)]
        hood=hood.cut(api['polyextr'](points,(0,10,0)))
    face=finish('Narrow face outer edge',faceted(29,1.2,96,half-2.2,15,32.8),.25,at_plane('X',30.2))
    register=faceted(27.8,1.4,95.7,half-1.5,15.3,33.5).cut(faceted(27.6,1.8,96.7,half-2.7,14.3,32.3))
    face=face.fuse(register)
    for y in [-face_y,face_y]:
        for z in P['face_mount_z']:
            tab=rounded_x(20.5,y-3 if y>0 else -half-1,z-3,3.5,half+4-abs(y),6,1)
            tab=tab.common(outer).cut(cyl(20.3,y,z,1.15,4,V(1,0,0)))
            hood=hood.fuse(tab).cut(cyl(rear-.3,y,z,2.3,3,V(1,0,0)))
            boss=cyl(24,y,z,3,5.2,V(1,0,0)).cut(cyl(23.8,y,z,.85,5,V(1,0,0)))
            face=face.fuse(boss.cut(lead(24,y,z,.85,.2,V(1,0,0))))
    for y in [-12,12]:face=face.fuse(cyl(24,y,121,2.8,5.2,V(1,0,0)).cut(cyl(23.8,y,121,.85,5,V(1,0,0))))
    face=face.cut(cyl(28.8,0,121,9.8,3,V(1,0,0)))
    # The fixed upper bill uses global head coordinates; add() applies the legacy
    # head shift, so bring each candidate back into this builder's source frame.
    face_global=face.copy();face_global.translate(V(0,0,P['head_shift_z']))
    face=integrated_upper_bill(face_global)
    face.translate(V(0,0,-P['head_shift_z']))
    add('FacePanel',face,'head',color=black,note='One connected printed face and flat upper mouth. Full-width fused 2.2 mm plate replaces the separate keyed bill, front screws and captive nuts. Four original rear face screws remain. Orange display region denotes optional paint on the same print. Nominal closed-jaw gap 4.10 mm; actual print fit unverified.')
    # A chamfered-square surround matches the shells; keep the optical bore circular.
    def bezel_wire(x,halfsize,corner):
        yz=[(-halfsize+corner,-halfsize),(halfsize-corner,-halfsize),
            (halfsize,-halfsize+corner),(halfsize,halfsize-corner),
            (halfsize-corner,halfsize),(-halfsize+corner,halfsize),
            (-halfsize,halfsize-corner),(-halfsize,-halfsize+corner)]
        pts=[V(x,y,121+z) for y,z in yz]
        return Part.makePolygon(pts+pts[:1])
    ring=Part.makeLoft([bezel_wire(30.2,13.5,5),bezel_wire(34.6,12.8,4.7)],True,True).fuse(cyl(29,0,121,9.5,1.4,V(1,0,0)))
    ring=finish('Optical bezel front rolls',ring.cut(cyl(28.8,0,121,8.5,6,V(1,0,0))),.35,at_plane('X',34.6))
    add('CameraRing',ring,'head',color=orange,note='Faceted tapered camera surround with a circular17mm optical bore and0.30mm radial locating fit. The optical path stays round; adhesive retention remains untested.')

    install('ESP32CAM',HW.esp32cam(),(17,-13.5,92),'head',9.2,basis=((0,1,0),(0,0,1),(1,0,0)))
    camera=[dict(name='OV2640 flex sensor PCB',shape=box(24,-5,116,1,10,10),color='#b77922'),
            dict(name='Lens carrier',shape=box(25,-4.5,116.5,2,9,9).fuse(cyl(27,0,121,4,4.8,V(1,0,0))),color='#181b20'),
            dict(name='Optical glass',shape=cyl(31.8,0,121,2.8,.2,V(1,0,0)),color='#1b3349')]
    add('OV2640Camera',Part.makeCompound([c['shape'] for c in camera]),'head','hardware',black,.8,'Adjustable OV2640 carrier.10mm sensor PCB and8mm lens envelope remain assumptions; measure actual flex length and lens registration.',camera)
    # Straight edge guides with rolled entry ends keep a full section at the tray.
    guides=[finish('Camera guide entry '+str(y),box(14.8,y,91.8,5.4,2.4,41.1),.3,at_plane('Z',132.9)) for y in [-16.2,13.8]]
    bracket=union([rounded(14.8,-16.2,90.5,5.4,32.4,1.5,.7)]+guides)
    for y in [-14.1,13.2]:bracket=bracket.cut(box(16.7,y,91.8,1.6,.9,41.4))
    for y in [-15,15]:bracket=bracket.cut(cyl(16,y,128.1,.85,5.2))
    trace('camera bracket alone',bracket)
    clamp=rounded(14.8,-16.2,132.9,5.4,32.4,1.2,.7)
    for y in [-15,15]:clamp=clamp.cut(cyl(16,y,132.7,1.15,1.6))
    add('CameraBoardClamp',clamp,'head',note='Top retainer for a rigidly rotated ESP32-CAM:27mm across,40.5mm tall. Two M2x6 screws. Board edge grooves retain0.3mm nominal lateral clearance.')
    cradle=rounded_x(22.2,-6.8,114.2,3.1,13.6,13.6,1.2)
    cradle=cradle.cut(box(22,-5.3,115.7,3,10.6,10.6)).cut(box(24.9,-4.7,116.3,.7,9.4,9.4))
    for y in [-12,12]:
        cradle=cradle.fuse(rounded_x(22.2,y-3,118,1.8,6,6,1)).fuse(box(22.2,-12 if y<0 else 6,118.5,1.8,6,5))
        slot=union([cyl(22,y,120,1.15,2.3,V(1,0,0)),cyl(22,y,122,1.15,2.3,V(1,0,0)),box(22,y-1.15,120,2.3,2.3,2)])
        cradle=cradle.cut(slot)
    add('CameraCradle',cradle,'head',note='Slotted flex-camera cradle with±1mm vertical adjustment. Confirm actual lens stack and flexible cable; retain sensor using a thin compliant adhesive.')

    tray=rounded(rear+3,-half+2.8,107,front-rear-6,2*half-5.6,2,4)
    rim=rounded(rear+3,-half+2.8,108.8,front-rear-6,2*half-5.6,3,4).cut(rounded(rear+4.2,-half+4,108.6,front-rear-8.4,2*half-8,3.5,2.8))
    frame=union([tray,rim,bracket])
    frame=frame.cut(box(8.1,-13.7,106.8,12.6,27.4,5))
    # Open the neck/mouth bay, while leaving longitudinal side beams.
    frame=frame.cut(rounded(-17,-9,106.8,9,18,2.5,2))
    trace('floor',frame)
    frame=frame.removeSplitter()
    trace('bracket',frame)
    for y in [-13,13]:frame=frame.fuse(cyl(5,y,92,3.2,17)).cut(cyl(5,y,91.8,1.15,17.5))
    trace('neck posts',frame)
    mouth=servo_y(pivot,-13,100);add('ServoMouth',mouth,'head','hardware',black,13.32)
    add('OutputSplineMouth',spline_y(pivot,15.5,100,4),'jaw','hardware',steel,.08,'Illustrative unverified output teeth; rotates with jaw. Included in complete servo mass.')
    for x in [pivot+v for v in api['earxs']]:
        width=4.6 if x<-20 else 6.6
        frame=frame.fuse(rounded_y(x-width/2,2.5,95,width,3,13,1.2).cut(cyl(x,2.3,100,1.15,3.5,V(0,1,0))))
    frame=frame.cut(mouth)
    trace('mouth posts',frame)
    passive=rounded_y(pivot-5,-23,96,10,5,14,2).cut(cyl(pivot,-23.2,100,1.15,5.4,V(0,1,0)))
    frame=frame.fuse(passive)
    trace('passive',frame)
    for sg in [1,-1]:
        tab=rounded_y(side_x-3,18,107,6,6.4,10,1).cut(cyl(side_x,17.8,113,.85,9,V(0,1,0)))
        frame=frame.fuse(tab if sg==1 else mirror(tab))
        bore=cyl(side_x,24,113,1.15,7,V(0,1,0));hood=hood.cut(bore if sg==1 else mirror(bore))
    trace('hood tabs',frame)
    add('HeadFrame',frame,'head',note='Short camera/mouth frame with integrated neck posts and vertical ESP32-CAM guides. One shared 5 V regulator resides in the torso; the ESP32-CAM provides four servo control signals. Purchased parts are unscaled; plugs and service-loop routing require physical validation.')

    jawrear=pivot-10;jawlength=36-jawrear
    jaw=rounded(jawrear,-27,90,jawlength,54,1.2,5)
    cutout=rounded(jawrear-2,-18.5,89.8,24-jawrear,37,3,4);jaw=jaw.cut(cutout)
    cheek=Part.BezierCurve();cheek.setPoles([V(pivot+8,24,100),V(pivot+8,24,94),V(pivot+14,24,91),V(28,24,91)])
    wire=Part.Wire([Part.makeLine(V(jawrear,24,91),V(pivot-8,24,100)),Part.Arc(V(pivot-8,24,100),V(pivot,24,108),V(pivot+8,24,100)).toShape(),cheek.toShape(),Part.makeLine(V(28,24,91),V(jawrear,24,91))])
    ear=finish('Narrow jaw cheek outer roll',Part.Face(wire).extrude(V(0,3,0)),.45,at_plane('Y',27))
    rim=rounded(jawrear,-27,91,jawlength,54,.9,5).cut(rounded(jawrear+1.2,-25.8,90.8,jawlength-2.4,51.6,1.3,3.8))
    rim=rim.common(union([box(pivot+2,-28,90.8,35-pivot,56,2),box(jawrear-1,23.5,90.8,jawlength+2,4.5,2),box(jawrear-1,-28,90.8,jawlength+2,4.5,2)]))
    jaw=union([jaw,rim,ear,mirror(ear)]).cut(cutout)
    jaw=jaw.cut(cyl(pivot,-27.2,100,1.15,3.5,V(0,1,0)))
    jaw=jaw.fuse(cyl(pivot,16,100,4.5,11,V(0,1,0)))
    jaw=socket_y(jaw,pivot,16,100,27,24.5)
    add('Jaw',jaw,'jaw',color=orange,note='54 mm hinged beak with integrated direct spline hub and opposite passive pivot. Illustrative unverified 20-tooth 4.8/4.30 mm profile, 0.06 mm radial allowance, 3.5 mm nominal shaft overlap. Axial screw retains hub; no horn arm or arm screws. Physical fit, tooth strength and opening require bench testing.')
    add('HeadHood',hood,'head',note='52mm frontal width,64mm depth,52mm height. Faceted roof, matching pivot reliefs,0.8mm outside/0.4mm inside edge rolls, ribs and registered camera face. Rear face-screw ports and removable side screws.')
    screw_y('JawPassivePin',pivot,15.2,100,12,'head',-1,2)
    nut=hexy(pivot,15.3,100,4,2.5).cut(cyl(pivot,15.1,100,.85,2.9,V(0,1,0)))
    add('JawPassiveLocknut',mirror(nut),'head','hardware',steel,.12,'M2 nominal locknut and short passive pivot; set axial endplay without clamping jaw. Verify selected hardware dimensions.')
    screw_y('MouthShaftScrew',pivot,17.5,100,7,'jaw',1,2)
    for sg in [1,-1]:screw_y('HoodScrew'+str(sg),side_x,20,113,6,'head',sg,2)
    for y in [-15,15]:screw_z('CameraClampScrew'+str(y),16,y,128.1,6,'head')
    for y in [-12,12]:
        screw=cyl(22.2,y,121,1,6,V(1,0,0)).fuse(cyl(20.9,y,121,2,1.3,V(1,0,0)))
        add('CameraCradleScrew'+str(y),screw,'head','hardware',steel,.13,'M2x6 adjustable camera cradle clamp.')
    for k,x in enumerate([pivot+v for v in api['earxs']]):
        screw_y('MouthMountScrew'+str(k),x,.3,100,8,'head',1,2)
        nut=hexy(x,.9,100,4,1.6).cut(cyl(x,.7,100,.85,2,V(0,1,0)))
        add('MouthMountNut'+str(k),nut,'head','hardware',steel,.1)
    for y in [-face_y,face_y]:
        for z in P['face_mount_z']:
            screw=cyl(20.5,y,z,1,6,V(1,0,0)).fuse(cyl(19.2,y,z,2,1.3,V(1,0,0)))
            add('FaceScrew'+str(y)+'_'+str(z),screw,'head','hardware',steel,.13,'Rear-driven M2x6 through hood ear into face pilot; install on bench before hood/frame assembly.')
