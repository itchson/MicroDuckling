"""Find same-facing planar overlaps that remain on a hardware exterior."""
from pathlib import Path
import sys, json, itertools, math, hashlib
from build_paths import BUILD_ROOT as ROOT, REPOSITORY
import FreeCAD as App
import Part
import hardware_r02 as HW

OUT = ROOT/'cad'
V = App.Vector

def scan(name, model):
    components = model['components']
    solids = list(model['shape'].Solids)
    groups = {}
    for index, item in enumerate(components):
        for face in item['shape'].Faces:
            if not isinstance(face.Surface, Part.Plane):
                continue
            u0,u1,v0,v1 = face.ParameterRange
            normal = face.normalAt((u0+u1)/2, (v0+v1)/2)
            key = tuple(round(value, 6) for value in list(normal) + [normal.dot(face.CenterOfMass)])
            groups.setdefault(key, []).append((index, face, normal))
    findings = []
    checked = 0
    for group in groups.values():
        for (i,a,normal),(j,b,_) in itertools.combinations(group,2):
            if i == j or components[i]['color'] == components[j]['color']:
                continue
            if not a.BoundBox.intersect(b.BoundBox):
                continue
            overlap = a.common(b)
            if overlap.Area < 1e-6:
                continue
            checked += 1
            visible_area = 0
            visible_points = []
            for face in overlap.Faces:
                vertices, triangles = face.tessellate(.02)
                for triangle in triangles:
                    points = [vertices[k] for k in triangle]
                    center = sum(points, V()) / 3
                    outside = center + normal * .0002
                    if not any(s.isInside(outside, 1e-7, False) for s in solids):
                        area = (points[1]-points[0]).cross(points[2]-points[0]).Length/2
                        visible_area += area
                        visible_points.append(list(center))
            if visible_area > 1e-5:
                findings.append(dict(material_a=components[i]['name'], material_b=components[j]['name'],
                                     normal=list(normal), area_mm2=visible_area,
                                     overlap_bounds_mm=[overlap.BoundBox.XMin,overlap.BoundBox.YMin,overlap.BoundBox.ZMin,
                                                        overlap.BoundBox.XMax,overlap.BoundBox.YMax,overlap.BoundBox.ZMax],
                                     exterior_sample=visible_points[0]))
    return dict(name=name, checked_coplanar_pairs=checked, findings=findings)

if __name__ == '__main__':
    reports = []
    document=App.openDocument(str(OUT/'MicroDuckling_R01.FCStd'))
    payload=json.loads((OUT/'meshes/Battery.json').read_text())
    positions=[V(*payload['positions'][i:i+3]) for i in range(0,len(payload['positions']),3)]
    components=[]
    for group in payload['groups']:
        indices=payload['indices'][group['start']:group['start']+group['count']]
        faces=[]
        for i in range(0,len(indices),3):
            pts=[positions[k] for k in indices[i:i+3]]
            faces.append(Part.Face(Part.makePolygon(pts+pts[:1])))
        material=payload['materials'][group['materialIndex']]
        components.append(dict(name=material['name'],color=material['color'],shape=Part.makeCompound(faces)))
    reports.append(scan('Battery',dict(shape=document.Battery.Shape,components=components)))
    for name, factory in [('ESP32CAM',HW.esp32cam), ('ServoController',HW.pca9685), ('IMU',HW.imu),
                          ('Buck_0',lambda:HW.pololu('Pololu-D24V50F5.step')),
                          ('Buck_1',lambda:HW.pololu('Pololu-D24V10Fx.step'))]:
        if any(report['name'] == name for report in reports):
            continue
        report = scan(name, factory())
        reports.append(report)
        print(json.dumps(report, indent=2), flush=True)
    result=dict(source_cad_sha256=hashlib.sha256((OUT/'MicroDuckling_R01.FCStd').read_bytes()).hexdigest(),
                source_hardware_sha256=hashlib.sha256((REPOSITORY/'src/hardware_r02.py').read_bytes()).hexdigest(),
                scope='Same-facing exposed planar overlap between different material groups. Battery uses exported display triangles; PCBs use the component solids that generate their display meshes. Outward surface samples exclude enclosed mating surfaces. This does not test the browser renderer.',
                components=reports)
    (OUT/'display_surface_checks.json').write_text(json.dumps(result,indent=2))
    assert not any(r['findings'] for r in reports),'Duplicate exterior display surfaces remain'
