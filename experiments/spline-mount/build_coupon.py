"""SPDX-License-Identifier: Apache-2.0
Configurable illustrative spline coupons. No MG90S fit or load rating is implied.
Run with FreeCAD's Python: build_coupon.py [--config measured-spline.json].
"""
import argparse
import json
import math
from pathlib import Path
import FreeCAD as A
import Part
import MeshPart

EXAMPLE = dict(status='ILLUSTRATIVE UNVERIFIED - replace every spline measurement',
               tooth_count=20, major_diameter_mm=4.8, root_diameter_mm=4.30,
               tooth_tip_fraction=.30, root_flat_fraction=.30,
               engagement_mm=2.5, screw_clearance_mm=2.2,
               floor_mm=1.2, outer_hex_af_mm=9.0,
               radial_clearances_mm=[0, .03, .06, .09, .12])
V = A.Vector


def validate(p):
    n = p['tooth_count']
    if not isinstance(n, int) or not 6 <= n <= 60:
        raise ValueError('tooth_count must be an integer from6 to60')
    for key in ['major_diameter_mm', 'root_diameter_mm', 'engagement_mm', 'screw_clearance_mm', 'floor_mm', 'outer_hex_af_mm']:
        if not math.isfinite(p[key]) or p[key] <= 0:
            raise ValueError(f'Invalid {key}')
    tip, root = p['tooth_tip_fraction'], p['root_flat_fraction']
    if not 0 < tip < 1 or not 0 < root < 1 or tip + root >= 1:
        raise ValueError('Tip/root fractions must be positive and sum to less than1')
    if not p['screw_clearance_mm'] < p['root_diameter_mm'] < p['major_diameter_mm'] < p['outer_hex_af_mm'] - 2:
        raise ValueError('Inconsistent diameters or insufficient insert wall')
    if any(not math.isfinite(c) or c < 0 or c > .3 for c in p['radial_clearances_mm']):
        raise ValueError('Invalid radial clearance')


def polygon_prism(points, z, height):
    vertices = [V(x, y, z) for x, y in points]
    return Part.Face(Part.makePolygon(vertices + vertices[:1])).extrude(V(0, 0, height))


def socket(p, clearance, label_count=0):
    validate(p)
    if not 0 <= clearance <= .3: raise ValueError('Invalid clearance')
    pitch = 2 * math.pi / p['tooth_count']
    r_min, r_max = p['root_diameter_mm'] / 2 + clearance, p['major_diameter_mm'] / 2 + clearance
    profile = []
    # Original trapezoidal radial approximation, not an involute/vendor tooth standard.
    for tooth in range(p['tooth_count']):
        for fraction, radius in [(-.5 + p['root_flat_fraction'] / 2, r_min),
                                  (-p['tooth_tip_fraction'] / 2, r_max),
                                  (p['tooth_tip_fraction'] / 2, r_max),
                                  (.5 - p['root_flat_fraction'] / 2, r_min)]:
            angle = pitch * (tooth + fraction)
            profile.append((radius * math.cos(angle), radius * math.sin(angle)))
    height = p['engagement_mm'] + p['floor_mm']
    radius = p['outer_hex_af_mm'] / math.sqrt(3)
    outer = polygon_prism([(radius * math.cos(i * math.pi / 3), radius * math.sin(i * math.pi / 3)) for i in range(6)], 0, height)
    cutter = polygon_prism(profile, p['floor_mm'], p['engagement_mm'] + .1)
    body = outer.cut(cutter).cut(Part.makeCylinder(p['screw_clearance_mm'] / 2, height + .2, V(0, 0, -.1)))
    if label_count:
        body = body.fuse(Part.makeBox(7.5, 6, p['floor_mm'], V(3.5, -3, 0)))
        for n in range(label_count):
            body = body.cut(Part.makeCylinder(.45, p['floor_mm'] + .2, V(6 + n * .95, 0, -.1)))
    body = body.removeSplitter()
    if not body.isValid() or len(body.Solids) != 1 or body.Volume <= 0:
        raise ValueError('Invalid or disconnected coupon')
    return body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2] / 'build/spline-fit')
    args = parser.parse_args()
    p = json.loads(args.config.read_text()) if args.config else EXAMPLE.copy()
    validate(p)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'illustrative-20t.json').write_text(json.dumps(p, indent=2) + '\n')
    doc = A.newDocument('UNVERIFIED_Spline_Fit_Coupons')
    doc.License = 'Apache-2.0'
    doc.Comment = 'Original radial profile approximation. Physical spline dimensions and fit unverified.'
    checks = []
    for index, clearance in enumerate(p['radial_clearances_mm']):
        shape = socket(p, clearance, index + 1)
        name = f'UNVERIFIED_Socket_C{index + 1}'
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.01, AngularDeflection=.08, Relative=False)
        assert mesh.isSolid(), name
        mesh.write(str(out / f'{name}.stl'))
        points, faces = mesh.Topology
        (out / f'{name}.json').write_text(json.dumps({'positions': [v for point in points for v in point], 'indices': [v for face in faces for v in face]}))
        feature = doc.addObject('PartDesign::Feature', name)
        feature.Shape = shape
        feature.Placement.Base = V(index * 17, 0, 0)
        checks.append(dict(name=name, radialClearanceMm=clearance, identificationDots=index + 1,
                           oneValidSolid=True, watertightMesh=True, volumeMm3=shape.Volume))
    plain = socket(p, .06)
    insert = doc.addObject('PartDesign::Feature', 'UNVERIFIED_KeyedInsert')
    insert.Shape = plain
    mesh = MeshPart.meshFromShape(Shape=plain, LinearDeflection=.01, AngularDeflection=.08, Relative=False)
    assert mesh.isSolid()
    mesh.write(str(out / 'UNVERIFIED_KeyedInsert.stl'))
    points, faces = mesh.Topology
    (out / 'UNVERIFIED_KeyedInsert.json').write_text(json.dumps({'positions': [v for point in points for v in point], 'indices': [v for face in faces for v in face]}))
    insert.Placement.Base = V(0, 16, 0)
    variation = {**p, 'tooth_count': 21, 'major_diameter_mm': 4.86, 'root_diameter_mm': 4.35}
    assert socket(variation, .03).isValid()
    rejected = 0
    for bad in [{**p, 'tooth_count': 0}, {**p, 'root_diameter_mm': 5},
                {**p, 'tooth_tip_fraction': .8}, {**p, 'floor_mm': -1}]:
        try: validate(bad)
        except ValueError: rejected += 1
    assert rejected == 4
    doc.recompute()
    native = out / 'UNVERIFIED_SplineFit.FCStd'
    doc.saveAs(str(native))
    Part.export(list(doc.Objects), str(out / 'UNVERIFIED_SplineFit.step'))
    A.closeDocument(doc.Name)
    reopened = A.openDocument(str(native))
    assert len(reopened.Objects) == 6 and all(obj.Shape.isValid() for obj in reopened.Objects)
    A.closeDocument(reopened.Name)
    report = dict(parameters=p, checks=checks, printableMeshes=6, nativeReopenValid=True,
                  configurable21ToothGeometryValid=True, rejectedInvalidParameterTests=rejected,
                  fitVerified=False, torqueRatingVerified=False)
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
