"""Derive link-local meshes and mass tensors from the saved FreeCAD assembly.

Run with FreeCAD's Python interpreter. Owns generated cad/manifest.json and
cad/simulation_meshes; never modifies the source FCStd or CAD builder.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

import FreeCAD as App
import Part
import MeshPart
import numpy as np

from paths import BUILD_ROOT as PROJECT
CAD = PROJECT / "cad"
V = App.Vector


def inertia_matrix(shape):
    m = shape.MatrixOfInertia
    return np.array([[m.A11, m.A12, m.A13], [m.A21, m.A22, m.A23], [m.A31, m.A32, m.A33]])


def parallel_axis(mass, offset_m):
    return mass * (float(offset_m @ offset_m) * np.eye(3) - np.outer(offset_m, offset_m))


def object_for_record(doc, record, used):
    name = record.get("object_name", record["name"])
    obj = doc.getObject(name)
    if obj is not None and obj.Name not in used:
        return obj
    clean = re.sub(r"[^a-zA-Z0-9]", "", record["name"]).lower()
    candidates = [o for o in doc.Objects if o.Name not in used and hasattr(o, "Shape")
                  and any(re.sub(r"[^a-zA-Z0-9]", "", x).lower() == clean for x in (o.Name, o.Label))]
    if len(candidates) == 1:
        return candidates[0]
    # Handles FreeCAD's sanitized duplicate names by checking saved physical metadata.
    candidates = [o for o in doc.Objects if o.Name not in used and hasattr(o, "EstimatedMass_g")
                  and o.RigidLink == record["link"] and o.ComponentType == record["kind"]
                  and abs(o.EstimatedMass_g - record["mass_g"]) < 1e-7
                  and np.linalg.norm(np.array(o.Shape.CenterOfMass) - record["com_mm"]) < 1e-5]
    if len(candidates) != 1:
        raise ValueError(f"Cannot unambiguously resolve saved object {record['name']}: {[o.Name for o in candidates]}")
    return candidates[0]


def box(center, size, link_origin, name, rpy=(0, 0, 0)):
    return dict(type="box", name=name, origin_xyz_mm=(np.array(center)-link_origin).tolist(),
                origin_rpy_rad=list(rpy), size_mm=list(size))


def rpy_from_z(normal):
    n = normal / np.linalg.norm(normal)
    x = np.array([n[2], 0, -n[0]])
    x /= np.linalg.norm(x)
    y = np.cross(n, x)
    rot = np.column_stack([x, y, n])
    return [math.atan2(rot[2, 1], rot[2, 2]), math.asin(-rot[2, 0]), math.atan2(rot[1, 0], rot[0, 0])]


def foot_colliders(sign, origin, params, tread):
    radius = params["foot_radius"]
    thickness = params["foot_thickness"] + params["tread_thickness"]
    # CAD foot is a rounded 70 x 52 mm planform, corner radius 9 mm.
    xmin, xmax, ymin, ymax = tread["bounds_xy_mm"]
    sphere_center = np.array(tread["center_global_mm"])
    x_edges = np.linspace(xmin, xmax, 15)
    y_edges = np.linspace(ymin, ymax, 12)
    def in_planform(x, y):
        dx = max(abs(x - (xmin+xmax)/2) - ((xmax-xmin)/2-9), 0)
        dy = max(abs(y - (ymin+ymax)/2) - ((ymax-ymin)/2-9), 0)
        return dx*dx + dy*dy <= 81 + 1e-8
    colliders = []
    for ix, (x0, x1) in enumerate(zip(x_edges[:-1], x_edges[1:])):
        for iy, (y0, y1) in enumerate(zip(y_edges[:-1], y_edges[1:])):
            if not all(in_planform(x, y) for x in (x0, x1) for y in (y0, y1)):
                continue
            x, y = (x0+x1)/2, (y0+y1)/2
            dx, dy = x-sphere_center[0], y-sphere_center[1]
            dz = math.sqrt(radius**2 - dx*dx - dy*dy)
            surface = np.array([x, y, sphere_center[2]-dz])
            normal = np.array([-dx, -dy, dz]) / radius
            center = surface + normal * thickness/2
            # Slight tangent overlap removes artificial cracks between neighboring cells.
            sx = (x1-x0) / math.sqrt(1-normal[0]**2) + .12
            sy = (y1-y0) / math.sqrt(1-normal[1]**2) + .12
            colliders.append(box(center, (sx, sy, thickness), origin, f"sole_{ix}_{iy}", rpy_from_z(normal)))
    colliders.append(box((0, sign*(params["leg_y"]+params["leg_thickness"]/2), params["hip_z"]-14),
                         (12, params["leg_thickness"], 25), origin, "leg_spine"))
    return colliders


def derive():
    # Confirm FreeCAD's matrix uses volume-weighted COM inertia, independent of translation.
    check = Part.makeBox(2, 3, 4, V(11, 20, 30))
    assert np.allclose(inertia_matrix(check), np.diag([50, 40, 26])), "Unexpected FreeCAD inertia convention"
    assembly_path = CAD / "assembly.json"
    assembly_bytes = assembly_path.read_bytes()
    assembly = json.loads(assembly_bytes.decode("utf-8-sig"))
    params = assembly["parameters"]
    source_path = CAD / "MicroDuckling_R01.FCStd"
    doc = App.openDocument(str(source_path))
    origins = {
        "body": np.array([0., 0., params["hip_z"]]),
        "left_leg": np.array([0., params["leg_y"], params["hip_z"]]),
        "right_leg": np.array([0., -params["leg_y"], params["hip_z"]]),
        "head": np.array([0., 0., params["neck_pivot_z"]]),
        "jaw": np.array([params["jaw_pivot_x"], 0., params["jaw_pivot_z"]]),
    }
    components = {name: [] for name in origins}
    geometry = {name: [] for name in origins}
    used = set()
    mapping = {}
    tread_geometry = {}
    try:
        for record in assembly["parts"]:
            if record["kind"] == "coupon":
                continue
            obj = object_for_record(doc, record, used)
            used.add(obj.Name)
            mapping[record["name"]] = obj.Name
            if not obj.Shape.isValid():
                raise ValueError(f"Invalid shape: {record['name']}")
            total_volume = sum(s.Volume for s in obj.Shape.Solids)
            assert np.isclose(total_volume, record["volume_mm3"], rtol=1e-6), f"Stale assembly record: {record['name']}"
            shape_com = sum((solid.Volume*np.array(solid.CenterOfMass) for solid in obj.Shape.Solids),
                            np.zeros(3))/total_volume
            assert np.allclose(shape_com, record["com_mm"], atol=1e-5), f"Stale COM: {record['name']}"
            density_kg_mm3 = float(record["mass_g"]) / 1000 / total_volume
            for solid in obj.Shape.Solids:
                components[record["link"]].append({
                    "record": record["name"], "mass": solid.Volume*density_kg_mm3,
                    "com": np.array(solid.CenterOfMass),
                    "tensor": inertia_matrix(solid)*density_kg_mm3*1e-6})
            geometry[record["link"]].append(obj.Shape.copy())
            if record["name"] in ("TreadLeft", "TreadRight"):
                spherical_faces = [f.Surface for f in obj.Shape.Faces if isinstance(f.Surface, Part.Sphere)]
                outer = max(spherical_faces, key=lambda surface: surface.Radius)
                assert abs(outer.Radius-params["foot_radius"]) < 1e-5, "CAD tread sphere changed"
                # Reopened BRep sphere bounds can be loose. Use the trimmed tread's
                # tessellated vertices so the rectangle does not grow past its CAD mask.
                tread_mesh = MeshPart.meshFromShape(Shape=obj.Shape, LinearDeflection=.075,
                                                    AngularDeflection=.18, Relative=False)
                vertices = tread_mesh.Topology[0]
                tread_geometry[record["link"]] = dict(center_global_mm=list(outer.Center),
                    bounds_xy_mm=[min(v.x for v in vertices),max(v.x for v in vertices),
                                  min(v.y for v in vertices),max(v.y for v in vertices)])
        links = []
        output_dir = CAD / "simulation_meshes"
        output_dir.mkdir(exist_ok=True)
        for name, origin in origins.items():
            entries = components[name]
            mass = sum(c["mass"] for c in entries)
            com = sum((c["mass"]*c["com"] for c in entries), np.zeros(3)) / mass
            inertia = sum((c["tensor"]+parallel_axis(c["mass"], (c["com"]-com)/1000) for c in entries), np.zeros((3, 3)))
            shape = Part.makeCompound(geometry[name])
            shape.translate(V(*(-origin)))
            mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.12, AngularDeflection=.22, Relative=False)
            mesh_path = output_dir / f"{name}.stl"
            mesh.write(str(mesh_path))
            if name.endswith("_leg"):
                collisions = foot_colliders(1 if name == "left_leg" else -1, origin, params, tread_geometry[name])
            elif name == "body":
                # Inner approximation stays within the compact faceted torso;
                # CAD sweeps, not these training primitives, check exterior fit.
                collisions = [box((params.get("body_x",0), 0, params["body_z"]),
                                  (params["body_dimensions_mm"][0]-12, 52, params["body_dimensions_mm"][2]-6),
                                  origin, "body_core")]
            elif name == "head":
                collisions = [box(((params['head_rear_x']+params['head_front_x'])/2, 0, params["head_base_z"]+26),
                                  (params['head_dimensions_mm'][0]-12, params['head_dimensions_mm'][1]-14, 26),
                                  origin, "head_core")]
            else:
                # U-shaped jaw: keep the neck opening free in the coarse physics asset.
                # R04 shortened the rear lip with the pivot; do not retain the
                # old fixed 60 mm rail that extended outside the new printed jaw.
                jaw_rear = params.get("jaw_rear_x", params["jaw_pivot_x"] - 10)
                jaw_front = params.get("jaw_front_x", 36)
                rail_center = (jaw_rear + jaw_front) / 2
                rail_length = jaw_front - jaw_rear - 8
                if rail_length <= 0:
                    raise ValueError("Jaw is too short for inset rail colliders")
                collisions = [box((rail_center, y, params["jaw_pivot_z"]-8.9), (rail_length, 5, 1.8), origin, 'jaw_rail_'+str(i))
                              for i,y in enumerate([-params['jaw_width_mm']/2+4,params['jaw_width_mm']/2-4])]
                collisions.append(box((28.5,0,params['jaw_pivot_z']-8.9),(9,params['jaw_width_mm']-8,1.8),origin,'jaw_front'))
            links.append(dict(name=name, mesh=mesh_path.relative_to(PROJECT).as_posix(), mass_kg=mass,
                              com_mm=(com-origin).tolist(), inertia_kg_m2=dict(ixx=inertia[0,0], ixy=inertia[0,1], ixz=inertia[0,2],
                              iyy=inertia[1,1], iyz=inertia[1,2], izz=inertia[2,2]), collisions=collisions,
                              frame_origin_global_mm=origin.tolist(), components=sorted(set(c["record"] for c in entries))))
        joints = []
        for name, parent, child, axis, limits in [
            ("left_hip", "body", "left_leg", [0, 1, 0], [-params["hip_limit_deg"], params["hip_limit_deg"]]),
            ("right_hip", "body", "right_leg", [0, 1, 0], [-params["hip_limit_deg"], params["hip_limit_deg"]]),
            ("neck_yaw", "body", "head", [0, 0, 1], [-params["neck_limit_deg"], params["neck_limit_deg"]]),
            ("jaw_pitch", "head", "jaw", [0, 1, 0], [0, params["jaw_limit_deg"]]),
        ]:
            joints.append(dict(name=name, parent=parent, child=child, type="revolute", axis=axis,
                               origin_xyz_mm=(origins[child]-origins[parent]).tolist(), origin_rpy_rad=[0,0,0],
                               limit_rad=[math.radians(x) for x in limits]))
        manifest = dict(schema_version=1, units="mm", root_height_mm=params["hip_z"],
                        status="CAD-derived prototype; contact model, physical fit and walking unvalidated",
                        source_cad_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                        source_assembly_sha256=hashlib.sha256(assembly_bytes).hexdigest(),
                        mass_assumption="Each component record mass uniformly distributed over its FreeCAD solids; combine full COM tensors via parallel-axis theorem",
                        collision_assumption="Rocker lower envelope approximated by tangent oriented box grid; rounded corner cells inset; body/head/jaw conservative inner primitives",
                        rocker_contact=dict(radius_mm=params["foot_radius"],
                            centers_global_mm={name: value["center_global_mm"] for name,value in tread_geometry.items()},
                            planform_bounds_xy_mm={name: value["bounds_xy_mm"] for name,value in tread_geometry.items()}),
                        links=links, joints=joints)
        total = sum(l["mass_kg"] for l in links)
        assert abs(total*1000 - assembly["mass_g"]) < 1e-7, "Mass accounting changed"
        (CAD / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        report = dict(status="DERIVED_FROM_SAVED_CAD", source_cad_sha256=manifest["source_cad_sha256"],
                      total_mass_kg=total, object_mapping=mapping,
                      links={l["name"]: dict(mass_kg=l["mass_kg"], com_mm=l["com_mm"], colliders=len(l["collisions"])) for l in links})
        (PROJECT / "simulation").mkdir(parents=True, exist_ok=True)
        (PROJECT / "simulation/cad_derivation.json").write_text(json.dumps(report, indent=2)+"\n")
        print(json.dumps(report, indent=2))
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    derive()
