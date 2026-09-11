"""Export the CAD manifest to a portable, five-link, four-servo URDF.

Run from any directory: python simulation/export_urdf.py
CAD length fields and meshes are millimetres; mass/inertia fields already SI.
Inertia tensors must be about each link's own COM, in that link's axes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from paths import BUILD_ROOT as PROJECT
JOINT_ORDER = ("left_hip", "right_hip", "neck_yaw", "jaw_pitch")
LINK_NAMES = {"body", "left_leg", "right_leg", "head", "jaw"}
IKEYS = ("ixx", "ixy", "ixz", "iyy", "iyz", "izz")


def numbers(value, count, name):
    result = np.asarray(value, dtype=float)
    if result.shape != (count,) or not np.isfinite(result).all():
        raise ValueError(f"{name}: expected {count} finite numbers")
    return result


def fmt(value):
    return " ".join(f"{float(v):.12g}" for v in value)


def tensor(link):
    i = link["inertia_kg_m2"]
    return np.array([[i["ixx"], i["ixy"], i["ixz"]],
                     [i["ixy"], i["iyy"], i["iyz"]],
                     [i["ixz"], i["iyz"], i["izz"]]], dtype=float)


def validate_manifest(manifest, project=PROJECT):
    if manifest.get("units") != "mm":
        raise ValueError("Manifest must explicitly declare units='mm'")
    height = float(manifest["root_height_mm"])
    if not math.isfinite(height) or height <= 0:
        raise ValueError("root_height_mm must explicitly give the body origin above the floor")
    for key, filename in (("source_cad_sha256", "cad/MicroDuckling_R01.FCStd"),
                          ("source_assembly_sha256", "cad/assembly.json")):
        if key in manifest:
            actual = hashlib.sha256((project / filename).read_bytes()).hexdigest()
            if actual != manifest[key]:
                raise ValueError(f"{filename} changed; rerun derive_manifest.py before export")
    links = manifest["links"]
    names = [x["name"] for x in links]
    if len(names) != 5 or set(names) != LINK_NAMES:
        raise ValueError(f"Exactly these five links required: {sorted(LINK_NAMES)}")
    joints = manifest["joints"]
    if len(joints) != 4 or {j["name"] for j in joints} != set(JOINT_ORDER):
        raise ValueError("Exactly four independently controlled servo joints required")
    child_parent = {}
    for link in links:
        mass = float(link["mass_kg"])
        if not math.isfinite(mass) or mass <= 0:
            raise ValueError(f"{link['name']}: non-positive mass")
        numbers(link["com_mm"], 3, "com_mm")
        matrix = tensor(link)
        if not np.isfinite(matrix).all():
            raise ValueError("Inertia contains non-finite numbers")
        eig = np.linalg.eigvalsh(matrix)
        if eig[0] <= 0 or eig[2] > eig[0] + eig[1] + 1e-12:
            raise ValueError(f"{link['name']}: unphysical COM inertia eigenvalues {eig}")
        if not (project / link["mesh"]).is_file():
            raise FileNotFoundError(project / link["mesh"])
        if not link.get("collisions"):
            raise ValueError(f"{link['name']}: explicit colliders required")
        if link["name"].endswith("_leg") and len(link["collisions"]) < 5:
            raise ValueError("Curved feet require segmented colliders, not one hull")
    for joint in joints:
        if joint.get("type", "revolute") != "revolute":
            raise ValueError("Servo joints must be revolute")
        parent, child = joint["parent"], joint["child"]
        if parent not in LINK_NAMES or child not in LINK_NAMES or child in child_parent:
            raise ValueError("Invalid articulation parent/child mapping")
        child_parent[child] = parent
        numbers(joint["origin_xyz_mm"], 3, "origin_xyz_mm")
        axis = numbers(joint["axis"], 3, "axis")
        if not np.isclose(np.linalg.norm(axis), 1):
            raise ValueError("Joint axes must be unit vectors")
        limits = numbers(joint["limit_rad"], 2, "limit_rad")
        if not limits[0] < limits[1] or not limits[0] <= 0 <= limits[1]:
            raise ValueError("Limits must contain the CAD zero pose")
    if LINK_NAMES - set(child_parent) != {"body"}:
        raise ValueError("Body must be the single floating articulation root")
    for name in child_parent:
        visited = set()
        while name in child_parent:
            if name in visited:
                raise ValueError("Articulation cycle")
            visited.add(name)
            name = child_parent[name]
        if name != "body":
            raise ValueError("Disconnected articulation")


def origin(element, xyz_mm=(0, 0, 0), rpy=(0, 0, 0)):
    ET.SubElement(element, "origin", xyz=fmt(numbers(xyz_mm, 3, "xyz_mm") / 1000),
                  rpy=fmt(numbers(rpy, 3, "rpy_rad")))


def geometry(element, collision, project, output_dir):
    geo = ET.SubElement(element, "geometry")
    kind = collision["type"]
    if kind == "box":
        size = numbers(collision["size_mm"], 3, "size_mm")
        if np.any(size <= 0):
            raise ValueError("Box sizes must be positive")
        ET.SubElement(geo, "box", size=fmt(size / 1000))
    elif kind == "sphere":
        radius = float(collision["radius_mm"]) / 1000
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError("Sphere radius must be positive")
        ET.SubElement(geo, "sphere", radius=f"{radius:.12g}")
    elif kind == "cylinder":
        dimensions = numbers([collision["radius_mm"], collision["length_mm"]], 2, "cylinder")
        if np.any(dimensions <= 0):
            raise ValueError("Cylinder dimensions must be positive")
        ET.SubElement(geo, "cylinder", radius=f"{dimensions[0]/1000:.12g}",
                      length=f"{dimensions[1]/1000:.12g}")
    elif kind == "mesh":
        path = project / collision["mesh"]
        if not path.is_file():
            raise FileNotFoundError(path)
        relative = Path(os.path.relpath(path, output_dir)).as_posix()
        ET.SubElement(geo, "mesh", filename=relative, scale="0.001 0.001 0.001")
    else:
        raise ValueError(f"Unsupported collider type: {kind}")


def export(manifest_path, output_path, project=PROJECT):
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw.decode("utf-8-sig"))
    validate_manifest(manifest, project)
    robot = ET.Element("robot", name="microduckling")
    robot.append(ET.Comment("Engineering prototype. Dynamics and physical fit are not validated."))
    for link in manifest["links"]:
        element = ET.SubElement(robot, "link", name=link["name"])
        inertial = ET.SubElement(element, "inertial")
        origin(inertial, link["com_mm"])
        ET.SubElement(inertial, "mass", value=f"{link['mass_kg']:.12g}")
        ET.SubElement(inertial, "inertia", **{k: f"{link['inertia_kg_m2'][k]:.12g}" for k in IKEYS})
        visual = ET.SubElement(element, "visual", name=f"{link['name']}_visual")
        origin(visual, link.get("mesh_origin_xyz_mm", [0, 0, 0]))
        geometry(visual, {"type": "mesh", "mesh": link["mesh"]}, project, output_path.parent)
        mat = ET.SubElement(visual, "material", name=f"{link['name']}_color")
        default_color = [1.0, .43, .08, 1] if link["name"] in {"left_leg", "right_leg", "jaw"} else [.92, .92, .86, 1]
        ET.SubElement(mat, "color", rgba=fmt(link.get("color_rgba", default_color)))
        for idx, collider in enumerate(link["collisions"]):
            collision = ET.SubElement(element, "collision", name=collider.get("name", f"{link['name']}_collision_{idx}"))
            origin(collision, collider.get("origin_xyz_mm", [0, 0, 0]), collider.get("origin_rpy_rad", [0, 0, 0]))
            geometry(collision, collider, project, output_path.parent)
    joints_by_name = {j["name"]: j for j in manifest["joints"]}
    for name in JOINT_ORDER:
        j = joints_by_name[name]
        element = ET.SubElement(robot, "joint", name=name, type="revolute")
        ET.SubElement(element, "parent", link=j["parent"])
        ET.SubElement(element, "child", link=j["child"])
        origin(element, j["origin_xyz_mm"], j.get("origin_rpy_rad", [0, 0, 0]))
        ET.SubElement(element, "axis", xyz=fmt(j["axis"]))
        # 0.11 N m is an unverified modeling ceiling, not a continuous servo rating.
        ET.SubElement(element, "limit", lower=f"{j['limit_rad'][0]:.12g}", upper=f"{j['limit_rad'][1]:.12g}",
                      effort="0.11", velocity="10.471975512")
        ET.SubElement(element, "dynamics", damping="0", friction="0")
    ET.indent(robot, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(robot).write(output_path, encoding="utf-8", xml_declaration=True)
    info = {"status": "CAD-derived prototype; Isaac runtime validation pending", "source_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "mesh_sha256": {x["mesh"]: hashlib.sha256((project / x["mesh"]).read_bytes()).hexdigest()
                             for x in manifest["links"]},
            "urdf_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(), "joint_order": list(JOINT_ORDER),
            "joint_limits_rad": [joints_by_name[n]["limit_rad"] for n in JOINT_ORDER],
            "root_height_m": float(manifest["root_height_mm"]) / 1000,
            "mass_kg": sum(float(x["mass_kg"]) for x in manifest["links"]),
            "links": {x["name"]: {"mass_kg": x["mass_kg"], "com_m": (np.asarray(x["com_mm"]) / 1000).tolist(),
                                      "inertia_kg_m2": x["inertia_kg_m2"], "collider_count": len(x["collisions"])} for x in manifest["links"]}}
    output_path.with_name("robot_info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=PROJECT / "cad/manifest.json")
    parser.add_argument("--output", type=Path, default=PROJECT / "simulation/microduckling.urdf")
    args = parser.parse_args()
    print(json.dumps(export(args.manifest.resolve(), args.output.resolve()), indent=2))
