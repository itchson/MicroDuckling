"""SPDX-License-Identifier: Apache-2.0
R06 fixed upper-bill candidate. FreeCAD solids in assembly-global millimetres.
One new print, two front-access M2x8 screws, two captive M2 nuts.
"""
import math
import FreeCAD as A
import Part

V = A.Vector
DEFAULTS = dict(face_front_x=30.2, plate_front_x=40.0, plate_bottom_z=86.0,
                plate_thickness=2.2, half_width=25.0, rear_half_width=23.6,
                mount_y=13.5, mount_z=92.0, ear_width=6.4, ear_top_z=95.2,
                ear_thickness=2.4, key_width=3.0, key_height=1.4,
                key_depth=1.8, key_bottom_z=87.0, key_clearance=.15,
                screw_clearance=2.3, screw_length=8.0, nut_af=4.0,
                nut_thickness=1.6, nut_pocket_af=4.2)


def prism(points, vector):
    vertices = [V(*point) for point in points]
    return Part.Face(Part.makePolygon(vertices + vertices[:1])).extrude(V(*vector))


def hex_x(x, y, z, af, length):
    radius = af / math.sqrt(3)
    return prism([(x, y + radius * math.cos(math.pi / 6 + i * math.pi / 3),
                   z + radius * math.sin(math.pi / 6 + i * math.pi / 3)) for i in range(6)],
                 (length, 0, 0))


def fixed_upper_bill(face_shape, options=None):
    """Return modified FacePanel and new UpperBill/hardware; input face is unchanged.

    All dimensions here are already in final assembly coordinates. In build_head,
    apply this function to a temporary copy shifted by head_shift_z, then translate
    outputs back by -head_shift_z before passing them to the existing add().
    """
    p = {**DEFAULTS, **(options or {})}
    x, z, w = p['face_front_x'], p['plate_bottom_z'], p['half_width']
    front = p['plate_front_x']
    if front <= x + 5 or p['plate_thickness'] < 1.5 or p['mount_y'] <= 0:
        raise ValueError('Invalid upper bill envelope')
    outline = [(x, -p['rear_half_width'], z), (x + 2.8, -w, z),
               (front - 2, -w, z), (front, -w + 2, z),
               (front, w - 2, z), (front - 2, w, z),
               (x + 2.8, w, z), (x, p['rear_half_width'], z)]
    bill = prism(outline, (0, 0, p['plate_thickness']))
    face = face_shape.copy()
    hardware = []
    for side, y in [('Left', p['mount_y']), ('Right', -p['mount_y'])]:
        ear = Part.makeBox(p['ear_thickness'], p['ear_width'], p['ear_top_z'] - z,
                           V(x, y - p['ear_width'] / 2, z))
        key = Part.makeBox(p['key_depth'] + .1, p['key_width'], p['key_height'],
                           V(x - p['key_depth'], y - p['key_width'] / 2, p['key_bottom_z']))
        bill = bill.fuse(ear).fuse(key)
        # New rear boss ends at the existing face skin; pockets load from inside.
        boss = Part.makeCylinder(3.4, 5.1, V(24.2, y, p['mount_z']), V(1, 0, 0))
        face = face.fuse(boss)
        clearance = p['key_clearance']
        slot = Part.makeBox(p['key_depth'] + .4, p['key_width'] + 2 * clearance,
                            p['key_height'] + 2 * clearance,
                            V(x - p['key_depth'] - .2, y - p['key_width'] / 2 - clearance,
                              p['key_bottom_z'] - clearance))
        bore = Part.makeCylinder(p['screw_clearance'] / 2, 12,
                                 V(23.5, y, p['mount_z']), V(1, 0, 0))
        pocket = hex_x(24.0, y, p['mount_z'], p['nut_pocket_af'], 2.4)
        face = face.cut(slot).cut(bore).cut(pocket)
        bill = bill.cut(bore)
        # Axial placement gives nominal1.4mm overlap in the captive nut.
        head_x = x + p['ear_thickness']
        screw = Part.makeCylinder(1, p['screw_length'],
                                  V(head_x - p['screw_length'], y, p['mount_z']), V(1, 0, 0))
        screw = screw.fuse(Part.makeCylinder(2, 1.4, V(head_x, y, p['mount_z']), V(1, 0, 0)))
        screw = screw.cut(Part.makeCylinder(.65, .8, V(head_x + .7, y, p['mount_z']), V(1, 0, 0)))
        nut = hex_x(24.4, y, p['mount_z'], p['nut_af'], p['nut_thickness'])
        nut = nut.cut(Part.makeCylinder(1.05, 2.0, V(24.2, y, p['mount_z']), V(1, 0, 0)))
        hardware.extend([(f'UpperBillScrew{side}', screw), (f'UpperBillNut{side}', nut)])
    return {'FacePanel': face.removeSplitter(), 'UpperBill': bill.removeSplitter(),
            **{name: shape.removeSplitter() for name, shape in hardware}}
