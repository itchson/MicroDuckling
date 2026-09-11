"""Apache-2.0. Shell-mounted upper-mouth base; global assembly millimetres.

Two flush M2 countersunk screws and top-loaded captive M2 nuts retain the base.
Registration and fastener dimensions are nominal; validate printed coupons.
"""
import math
import FreeCAD as A
import Part

V=A.Vector
PARAMETERS=dict(front_x=36.,rear_x=14.5,width=54.,bottom_z=82.9,plate_thickness=2.,
                corner_radius=5.,mount_x=18.,mount_y=22.,register_radius=2.6,
                register_height=1.2,register_radial_clearance=.15,
                register_end_clearance=.2,screw_clearance_diameter=2.3,
                nut_pocket_af=4.2,nut_af=4.,nut_bottom_z=87.5,
                screw_length=8.,head_rim_height=.2,head_cone_height=1.,closed_lip_gap=1.0)


def hex_z(x,y,z,af,length):
    radius=af/math.sqrt(3)
    points=[V(x+radius*math.cos(i*math.pi/3),y+radius*math.sin(i*math.pi/3),z) for i in range(6)]
    return Part.Face(Part.makePolygon(points+points[:1])).extrude(V(0,0,length))


def build_upper_mouth(hood,rounded):
    p=PARAMETERS; z=p['bottom_z']; top=z+p['plate_thickness']; x=p['mount_x']
    base=rounded(p['rear_x'],-p['width']/2,z,p['front_x']-p['rear_x'],p['width'],p['plate_thickness'],p['corner_radius'])
    # Rear central relief clears the ESP32-CAM and its vertical guide frame.
    base=base.cut(Part.makeBox(8.2,34,4,V(12.5,-17,z-.1)))
    # Seat the front lower shell rim on the base; clear its two rising registers.
    hood=hood.cut(Part.makeBox(24,58,2,V(13.5,-29,82.9)))
    hardware={}
    for side,y in [('Left',p['mount_y']),('Right',-p['mount_y'])]:
        boss=Part.makeCylinder(3.5,4.9,V(x,y,top))
        hood=hood.fuse(boss)
        register=Part.makeCylinder(p['register_radius'],p['register_height'],V(x,y,top))
        base=base.fuse(register)
        socket=Part.makeCylinder(p['register_radius']+p['register_radial_clearance'],
                                 p['register_height']+p['register_end_clearance']+.01,V(x,y,top-.01))
        bore=Part.makeCylinder(p['screw_clearance_diameter']/2,10,V(x,y,z-.1))
        countersink=Part.makeCone(2.01,1.01,1.0,V(x,y,z+.19))
        countersink=countersink.fuse(Part.makeCylinder(2.10,.21,V(x,y,z-.01)))
        base=base.cut(bore).cut(countersink)
        pocket=hex_z(x,y,p['nut_bottom_z'],p['nut_pocket_af'],3.2)
        hood=hood.cut(socket).cut(bore).cut(pocket)
        # M2x8 nominal countersunk length includes head; underside sits flush.
        screw=Part.makeCylinder(2.0,.2,V(x,y,z))
        screw=screw.fuse(Part.makeCone(2.0,1.0,1.0,V(x,y,z+.2)))
        screw=screw.fuse(Part.makeCylinder(1,6.8,V(x,y,z+1.2)))
        screw=screw.cut(hex_z(x,y,z-.01,1.3,.61))
        nut=hex_z(x,y,p['nut_bottom_z'],p['nut_af'],1.6)
        nut=nut.cut(Part.makeCylinder(.85,1.8,V(x,y,p['nut_bottom_z']-.1)))
        hardware['UpperMouthScrew'+side]=screw.removeSplitter()
        hardware['UpperMouthNut'+side]=nut.removeSplitter()
    for name,shape in [('HeadHood',hood),('UpperMouthBase',base)]:
        if not shape.isValid() or len(shape.Solids)!=1:
            raise RuntimeError(name+' must remain one valid connected solid')
    return hood.removeSplitter(),base.removeSplitter(),hardware
