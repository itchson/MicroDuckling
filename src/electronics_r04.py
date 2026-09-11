"""Rigidly mounted torso electronics. No purchased component is rescaled.

Installation starts with the servo regulator before battery, IMU and removable
neck support, giving access from the rear. The controller enters from the front.
"""
import FreeCAD as A


def build_electronics(api,chassis):
    V=A.Vector
    box,cyl,rounded,rounded_x,union=(api[k] for k in ['box','cyl','rounded','rounded_x','union'])
    add,install,HW,mounts=(api[k] for k in ['add','install_model','HW','hardware_mounts'])
    install('ServoController',HW.pca9685(),(27,-31.115,31.4),'body',8.5,basis=((0,1,0),(0,0,1),(1,0,0)))
    install('Buck_0',HW.pololu('Pololu-D24V50F5.step'),(12,10,44.8),'body',3.1,basis=((0,0,1),(0,1,0),(-1,0,0)))
    install('Buck_1',HW.pololu('Pololu-D24V10Fx.step'),(-4,-30,47),'body',1.0)

    # Front posts have 4.5mm bearing length behind the controller, avoiding hip ears.
    frame=rounded(21.6,-31.2,30,3.4,62.4,2.4,.6).fuse(box(20,-24,30,3,48,2.4))
    for y in [-28.575,28.575]:
        frame=frame.fuse(rounded(22.2,y-1.6,32.1,1.3,3.2,24.4,.5))
    for i,(point,diam) in enumerate(mounts['ServoController']):
        x,y,z=point
        post=cyl(22.5,y,z,1.6,4.5,V(1,0,0)).cut(cyl(22.3,y,z,.65,4.9,V(1,0,0)))
        frame=frame.fuse(post)
        shaft=x+1.635-6
        screw=cyl(shaft,y,z,.8,6,V(1,0,0)).fuse(cyl(shaft+6,y,z,1.6,1.3,V(1,0,0)))
        add('ServoControllerMountScrew'+str(i),screw,'body','hardware',api['steel'],.16,'M1.6x6 into4.5mm-long printed mounts; verify pilot strength and actual head/connector clearance.')
    chassis=chassis.fuse(frame)

    # Open-backed regulator support attaches to the existing front anchor rail.
    support=rounded_x(15,10.159,44.5,2.7,20,18,1)
    support=support.cut(box(14.8,13,48.6,3.1,14.3,10.1))
    for i,(point,diam) in enumerate(mounts['Buck_0']):
        x,y,z=point
        post=cyl(x,y,z,2,4.7,V(1,0,0)).cut(cyl(x-.2,y,z,.85,4.9,V(1,0,0)))
        support=support.fuse(post)
        face=x-1.5748
        screw=cyl(face,y,z,1,6,V(1,0,0)).fuse(cyl(face-1.3,y,z,2,1.3,V(1,0,0)))
        add('Buck_0MountScrew'+str(i),screw,'body','hardware',api['steel'],.16,'M2x6 inserted from the rear/inside into vertical regulator posts; fit before battery and removable neck support.')
    chassis=chassis.fuse(support)

    # Hole-free logic board uses an insulating cradle with ledges for an adhesive pad.
    tray=rounded(-5.1,-31.1,45.8,14.9,19.98,2.2,1)
    tray=tray.cut(box(-4.3,-30.3,46.8,13.3,18.38,1.5))
    tray=tray.cut(box(-4.3,-31.3,46.8,13.3,2.4,1.5))
    arms=[box(8.7,y,45.8,8.3,2.6,1) for y in [-30.8,-13.9]]
    arms.extend(rounded(15,y,45.8,3,2.6,6,.5) for y in [-30.8,-13.9])
    chassis=union([chassis,tray]+arms)
    # Preserve the shell screw bore and captive-nut entry through the new support.
    access=cyl(17,23.8,53,1.15,13,V(0,1,0)).fuse(api['hexy'](17,26,53,4.2,2)).fuse(box(14.9,26,44,4.2,2,9))
    chassis=chassis.cut(access).cut(api['mirror'](access))
    return chassis.removeSplitter()
