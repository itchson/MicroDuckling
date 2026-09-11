"""Rigidly mounted torso electronics. No purchased component is rescaled.

Installation starts with the shared 5 V regulator before battery, IMU and
removable neck support, giving access from the rear. Servo signals originate
at the ESP32-CAM; no separate PWM controller or logic regulator is installed.
"""
import FreeCAD as A


def build_electronics(api,chassis):
    V=A.Vector
    box,cyl,rounded_x=(api[k] for k in ['box','cyl','rounded_x'])
    add,install,HW,mounts=(api[k] for k in ['add','install_model','HW','hardware_mounts'])
    install('Buck_0',HW.pololu('Pololu-D24V50F5.step'),(12,10,44.8),'body',3.1,basis=((0,0,1),(0,1,0),(-1,0,0)))

    # Open-backed regulator support attaches to the existing front anchor rail.
    support=rounded_x(15,10.159,44.5,2.7,20,18,1)
    support=support.cut(box(14.8,13,48.6,3.1,14.3,10.1))
    for i,(point,diam) in enumerate(mounts['Buck_0']):
        x,y,z=point
        post=cyl(x,y,z,2,4.7,V(1,0,0)).cut(cyl(x-.2,y,z,.85,4.9,V(1,0,0)))
        support=support.fuse(post)
        face=x-1.5748
        screw=cyl(face,y,z,1,6,V(1,0,0)).fuse(cyl(face-1.3,y,z,2,1.3,V(1,0,0)))
        add('Buck_0MountScrew'+str(i),screw,'body','hardware',api['steel'],.16,'M2x6 inserted from the rear/inside into shared 5 V regulator posts; fit before battery and removable neck support.')
    chassis=chassis.fuse(support)
    # Preserve the shell screw bore and captive-nut entry through the new support.
    access=cyl(17,23.8,53,1.15,13,V(0,1,0)).fuse(api['hexy'](17,26,53,4.2,2)).fuse(box(14.9,26,44,4.2,2,9))
    chassis=chassis.cut(access).cut(api['mirror'](access))
    return chassis.removeSplitter()
