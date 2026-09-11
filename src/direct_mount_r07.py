"""Apache-2.0. Configurable illustrative servo spline, NOT vendor-qualified.

The radial trapezoidal profile is a manufacturing hypothesis; it is not a measured
MG90S involute. Print the representative socket coupon before robot parts.
"""
import math
import FreeCAD as A
import Part

V = A.Vector
DEFAULTS = dict(teeth=20, outside_diameter_mm=4.8, root_diameter_mm=4.30,
                radial_clearance_mm=.06, socket_depth_mm=3.8,
                fit_status='UNVERIFIED illustrative radial tooth profile; measure actual servo batch')


def spline_y(x, y, z, length, clearance=0, parameters=None):
    p = {**DEFAULTS, **(parameters or {})}
    points = []
    for tooth in range(p['teeth']):
        for fraction, diameter in [(-.5, p['root_diameter_mm']),
                                   (-.22, p['outside_diameter_mm']),
                                   (.22, p['outside_diameter_mm']),
                                   (.5, p['root_diameter_mm'])]:
            angle = 2 * math.pi * (tooth + fraction) / p['teeth']
            radius = diameter / 2 + clearance
            point = V(x + radius * math.cos(angle), y, z + radius * math.sin(angle))
            if not points or (point - points[-1]).Length > 1e-7:
                points.append(point)
    if (points[-1] - points[0]).Length < 1e-7:
        points.pop()
    return Part.Face(Part.makePolygon(points + points[:1])).extrude(V(0, length, 0))


def socket_y(shape, x, y, z, outer_end, head_seat, parameters=None):
    p = {**DEFAULTS, **(parameters or {})}
    shape = shape.cut(spline_y(x, y - .02, z, p['socket_depth_mm'] + .02,
                              p['radial_clearance_mm'], p))
    shape = shape.cut(Part.makeCylinder(1.15, outer_end-y+.2, V(x,y,z),V(0,1,0)))
    shape = shape.cut(Part.makeCylinder(2.25, outer_end-head_seat+.2, V(x,head_seat,z),V(0,1,0)))
    # 0.35 mm chamfer guides the shaft into the socket without touching the turret.
    lead = Part.makeCone(p['outside_diameter_mm']/2+p['radial_clearance_mm']+.35,
                         p['outside_diameter_mm']/2+p['radial_clearance_mm'], .35,
                         V(x,y-.01,z), V(0,1,0))
    return shape.cut(lead).removeSplitter()


def integrated_upper_bill(face):
    """One connected face and flat upper mouth; assembly-global coordinates."""
    points = [(29.4,-23.6,86),(33,-25,86),(38,-25,86),(40,-23,86),
              (40,23,86),(38,25,86),(33,25,86),(29.4,23.6,86)]
    vertices = [V(*p) for p in points]
    plate = Part.Face(Part.makePolygon(vertices+vertices[:1])).extrude(V(0,0,2.2))
    # Actual overlap with the face skin creates a continuous load path across its width.
    result = face.fuse(plate).removeSplitter()
    if not result.isValid() or len(result.Solids) != 1:
        raise ValueError('Integrated face/bill must be a single valid connected solid')
    return result
