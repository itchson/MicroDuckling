"""Compact panelled MicroDuckling torso, in global CAD millimetres.

Run with FreeCAD's Python. This module creates shapes only: no document, file,
mounting hole, neck aperture or shell split is changed by importing/calling it.

    s = body_solids()
    body = s["outer"].cut(s["inner"])

For a Y=0 clamshell split with a 0.30 mm butt gap, put the register root in
Y=0.15..1.60 and its tongue in Y=-1.25..0.55. Cut both rings from the common
register_inner; use register_root_outer for the root and register_outer for
the tongue. Apply the same neck/service apertures to the register as the body,
and interrupt the lip wherever internal hardware needs it. At the flat panels,
register_outer sits 0.30 mm inside the cavity, and its ring is 1.00 mm thick.

The dimensions are a new MG90S enclosure, inspired by the planar panels and
edge treatment in the official Microduck left_shell/right_shell STL exports;
it is not a scaled vendor shell or a verified hardware fit.
"""
import FreeCAD as App
import Part

V = App.Vector

# z, rear X, front X, half-width Y, diagonal corner chamfer in XY.
# Corresponding octagons make planar side/chamfer/shoulder faces.
PROFILE = (
    (28.0, -32.0, 38.0, 36.0, 3.5),
    (33.0, -35.0, 41.0, 39.0, 4.0),
    (55.0, -35.0, 41.0, 39.0, 4.0),
    (65.0, -29.0, 35.0, 32.0, 4.0),
)


def _vertices(level):
    z, xmin, xmax, halfwidth, corner = level
    points = [
        (xmin + corner, -halfwidth), (xmax - corner, -halfwidth),
        (xmax, -halfwidth + corner), (xmax, halfwidth - corner),
        (xmax - corner, halfwidth), (xmin + corner, halfwidth),
        (xmin, halfwidth - corner), (xmin, -halfwidth + corner),
    ]
    return [V(x, y, z) for x, y in points]


def _face(vertices):
    return Part.Face(Part.makePolygon(vertices + vertices[:1]))


def _panel_loft():
    # Explicit planar faces preserve the flat ruled loft sections as planes.
    # OCC's generic makeLoft converts the sloping faces to BSplines, whose
    # inward offsets are unreliable at the shoulder/chamfer intersections.
    rings = [_vertices(p) for p in PROFILE]
    bottom = _face(rings[0])
    bottom.reverse()
    faces = [bottom, _face(rings[-1])]
    for lower, upper in zip(rings[:-1], rings[1:]):
        for i in range(8):
            j = (i + 1) % 8
            faces.append(_face([lower[i], lower[j], upper[j], upper[i]]))
    return Part.makeSolid(Part.makeShell(faces))


def _solid(shape, label):
    shape = shape.removeSplitter()
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
        raise RuntimeError("Body R02 is not one valid solid: " + label)
    return shape.Solids[0]


def _finish(shape, radius, label):
    shape = _solid(shape, label + " before edge finish")
    if radius:
        shape = shape.makeFillet(radius, shape.Edges)
    return _solid(shape, label)


def _inset_panels(raw, distance):
    # Intersect inward-shifted planar half spaces. This keeps exact normal
    # panel thickness without relying on OCC's failing multi-shoulder offset.
    result = raw.copy()
    for face in raw.Faces:
        normal = face.normalAt(0, 0)
        center = face.CenterOfMass - normal * distance
        tangent = face.Edges[0].Vertexes[-1].Point - face.Edges[0].Vertexes[0].Point
        tangent.normalize()
        side = normal.cross(tangent)
        side.normalize()
        span = 250
        plane = _face([center + tangent * span + side * span,
                       center - tangent * span + side * span,
                       center - tangent * span - side * span,
                       center + tangent * span - side * span])
        interior = plane.extrude(normal * -500)
        result = result.common(interior)
    return _solid(result, "inset planar half spaces")


def body_solids(wall=1.3, register_clearance=0.3, register_thickness=1.0,
                edge_radius=0.8):
    """Return closed outer/cavity and register solids in the assembly frame.

    Envelope: X[-35,41], Y[-39,39], Z[28,65] mm. ``wall`` is the normal
    distance between the flat panels. Small edge fillets locally thicken
    corner material. The middle stays full width for the battery and motors.
    Solid validity, cavity containment and minimum wall/register distances
    are checked before returning. Tessellated bounds give the stated envelope;
    OCC's bounding box for fillet patches can be about 0.012 mm looser.
    """
    if not 1.2 <= wall <= 1.4:
        raise ValueError("The reviewed body wall range is 1.2..1.4 mm")
    if not 0.2 <= register_clearance <= 0.4 or not 0.8 <= register_thickness <= 1.2:
        raise ValueError("Register clearance/thickness outside reviewed range")
    if not 0 <= edge_radius <= 1.0:
        raise ValueError("Use a modest outer edge fillet in 0..1 mm")
    raw = _solid(_panel_loft(), "ruled panel loft")

    def inset(distance, label):
        shape = _inset_panels(raw, distance)
        return _finish(shape, min(edge_radius, 0.45), label)

    result = {
        "outer": _finish(raw, edge_radius, "outer"),
        "inner": inset(wall, "inner"),
        "register_outer": inset(wall + register_clearance, "register tongue"),
        "register_inner": inset(wall + register_clearance + register_thickness, "register bore"),
        "register_root_outer": inset(wall - 0.55, "register root"),
    }
    _solid(result["outer"].cut(result["inner"]), "complete unsplit wall")
    if result["inner"].cut(result["outer"]).Volume > 1e-5:
        raise RuntimeError("Body R02 cavity protrudes through exterior")
    skin_distance = result["outer"].Shells[0].distToShape(result["inner"].Shells[0])[0]
    register_distance = result["inner"].Shells[0].distToShape(result["register_outer"].Shells[0])[0]
    if skin_distance < wall - 1e-5 or register_distance < register_clearance - 1e-5:
        raise RuntimeError("Body R02 wall or register clearance fell below its nominal minimum")
    return result
