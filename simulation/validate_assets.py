"""Check CAD/URDF units, link inertia, four-axis mapping and mesh availability.

Requires numpy and trimesh, not Isaac. Passing does not validate contact dynamics.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
from export_urdf import PROJECT, JOINT_ORDER, validate_manifest, tensor


def validate(manifest_path, urdf_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    validate_manifest(manifest)
    root = ET.parse(urdf_path).getroot()
    links = {x.attrib["name"]: x for x in root.findall("link")}
    joints = {x.attrib["name"]: x for x in root.findall("joint")}
    assert len(links) == 5 and len(joints) == 4
    assert set(joints) == set(JOINT_ORDER)
    meshes = {}
    maximum_tread_surface_error_mm = 0.0
    for link in manifest["links"]:
        elem = links[link["name"]]
        assert np.isclose(float(elem.find("inertial/mass").attrib["value"]), link["mass_kg"], rtol=1e-10)
        assert np.allclose(np.fromstring(elem.find("inertial/origin").attrib["xyz"], sep=" "), np.array(link["com_mm"])/1000)
        imported_i = {k: float(v) for k, v in elem.find("inertial/inertia").attrib.items()}
        assert np.allclose(tensor({"inertia_kg_m2": imported_i}), tensor(link), rtol=1e-10, atol=1e-16)
        path = PROJECT / link["mesh"]
        mesh = trimesh.load_mesh(path, force="mesh")
        assert len(mesh.faces) > 0 and np.isfinite(mesh.vertices).all()
        # Broad millimetre sanity bound catches accidental 1000x scale errors.
        assert 1 < mesh.extents.max() < 300
        mesh_tag = elem.find("visual/geometry/mesh")
        assert np.allclose(np.fromstring(mesh_tag.attrib["scale"], sep=" "), [.001]*3)
        assert (urdf_path.parent / mesh_tag.attrib["filename"]).resolve() == path.resolve()
        assert len(elem.findall("collision")) == len(link["collisions"])
        if link["name"].endswith("_leg") and "rocker_contact" in manifest:
            rocker = manifest["rocker_contact"]
            center = np.array(rocker["centers_global_mm"][link["name"]])
            frame = np.array(link["frame_origin_global_mm"])
            for collider in link["collisions"]:
                if not collider.get("name", "").startswith("sole_"):
                    continue
                roll, pitch, yaw = collider["origin_rpy_rad"]
                cr, sr, cp, sp, cy, sy = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
                rot = np.array([[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
                                [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr], [-sp, cp*sr, cp*cr]])
                xyz = np.array(collider["origin_xyz_mm"]) + frame
                sx, sy_, sz = collider["size_mm"]
                for x in (-sx/2, sx/2):
                    for y in (-sy_/2, sy_/2):
                        vertex = xyz + rot @ np.array([x, y, -sz/2])
                        error = abs(np.linalg.norm(vertex-center)-rocker["radius_mm"])
                        maximum_tread_surface_error_mm = max(maximum_tread_surface_error_mm, error)
            assert maximum_tread_surface_error_mm < .1, "Rocker tangent grid deviates more than0.1mm radially"
        meshes[link["name"]] = {"extents_mm": mesh.extents.tolist(), "triangles": len(mesh.faces),
                                "colliders": len(link["collisions"]), "mass_kg": link["mass_kg"]}
    axis_map = {"left_hip": [0, 1, 0], "right_hip": [0, 1, 0], "neck_yaw": [0, 0, 1], "jaw_pitch": [0, 1, 0]}
    for joint in manifest["joints"]:
        elem = joints[joint["name"]]
        assert elem.attrib["type"] == "revolute"
        axis = np.fromstring(elem.find("axis").attrib["xyz"], sep=" ")
        assert np.isclose(abs(np.dot(axis, axis_map[joint["name"]])), 1)
        xyz = np.fromstring(elem.find("origin").attrib["xyz"], sep=" ")
        assert np.allclose(xyz, np.array(joint["origin_xyz_mm"])/1000)
    report = {"status": "PASS_STATIC_EXPORT_CHECKS", "isaac_runtime_tested": False,
              "walking_validated": False, "hardware_validated": False,
              "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "urdf_sha256": hashlib.sha256(urdf_path.read_bytes()).hexdigest(),
              "maximum_tread_box_corner_radial_error_mm": maximum_tread_surface_error_mm,
              "total_mass_kg": sum(x["mass_kg"] for x in manifest["links"]), "links": meshes}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=PROJECT / "cad/manifest.json")
    parser.add_argument("--urdf", type=Path, default=PROJECT / "simulation/microduckling.urdf")
    args = parser.parse_args()
    report = validate(args.manifest, args.urdf)
    args.urdf.with_name("static_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
