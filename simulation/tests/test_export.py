"""Numerical regression tests for dangerous URDF unit/inertia/topology mistakes."""
import copy
import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_urdf import export, validate_manifest


def fixture(project):
    (project / "shape.stl").write_text("solid dummy\nendsolid dummy\n")
    i = dict(ixx=2e-6, ixy=1e-7, ixz=2e-8, iyy=2.5e-6, iyz=-1e-7, izz=3e-6)
    names = ["body", "left_leg", "right_leg", "head", "jaw"]
    links = [dict(name=n, mesh="shape.stl", mass_kg=.02, com_mm=[2, -3, 4], inertia_kg_m2=i.copy(),
                  collisions=[dict(type="box", size_mm=[5, 10, 2], origin_xyz_mm=[0, 0, -20])] * (6 if n.endswith("_leg") else 1)) for n in names]
    joints = [dict(name=n, parent=p, child=c, type="revolute", origin_xyz_mm=xyz,
                   axis=axis, limit_rad=[-.5, .5]) for n, p, c, xyz, axis in [
        ("left_hip", "body", "left_leg", [0, 40, 0], [0, 1, 0]),
        ("right_hip", "body", "right_leg", [0, -40, 0], [0, 1, 0]),
        ("neck_yaw", "body", "head", [0, 0, 47], [0, 0, 1]),
        ("jaw_pitch", "head", "jaw", [20, 0, 10], [0, 1, 0])]]
    return dict(units="mm", root_height_mm=36, links=links, joints=joints)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.manifest = fixture(self.project)

    def tearDown(self):
        self.temp.cleanup()

    def test_mm_converted_once_and_com_tensor_kept_in_si(self):
        source = self.project / "manifest.json"
        source.write_text(json.dumps(self.manifest))
        output = self.project / "simulation/robot.urdf"
        info = export(source, output, self.project)
        root = ET.parse(output).getroot()
        self.assertEqual(root.find("joint/origin").attrib["xyz"], "0 0.04 0")
        body = root.find("link")
        self.assertEqual(body.find("inertial/origin").attrib["xyz"], "0.002 -0.003 0.004")
        self.assertAlmostEqual(float(body.find("inertial/inertia").attrib["ixy"]), 1e-7)
        self.assertEqual(body.find("visual/geometry/mesh").attrib["filename"], "../shape.stl")
        self.assertAlmostEqual(info["mass_kg"], .1)
        self.assertAlmostEqual(info["root_height_m"], .036)

    def test_negative_or_impossible_inertia_rejected(self):
        for i in (-1e-6, 20e-6):
            m = copy.deepcopy(self.manifest)
            m["links"][0]["inertia_kg_m2"]["izz"] = i
            with self.assertRaisesRegex(ValueError, "unphysical"):
                validate_manifest(m, self.project)

    def test_duplicate_child_or_cycle_rejected(self):
        for parent, child in (("head", "body"), ("body", "head")):
            m = copy.deepcopy(self.manifest)
            m["joints"][3].update(parent=parent, child=child)
            with self.assertRaises(ValueError):
                validate_manifest(m, self.project)

    def test_single_hull_foot_rejected(self):
        self.manifest["links"][1]["collisions"] = self.manifest["links"][1]["collisions"][:1]
        with self.assertRaisesRegex(ValueError, "segmented"):
            validate_manifest(self.manifest, self.project)

    def test_nonunit_joint_axis_rejected(self):
        self.manifest["joints"][0]["axis"] = [0, 1000, 0]
        with self.assertRaisesRegex(ValueError, "unit vectors"):
            validate_manifest(self.manifest, self.project)

    def test_actor_has_no_unavailable_servo_or_ground_truth_telemetry(self):
        source = Path(__file__).resolve().parents[1] / "microduckling_lab/environment.py"
        tree = ast.parse(source.read_text())
        observation = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_get_observations")
        data_fields = {n.attr for n in ast.walk(observation) if isinstance(n, ast.Attribute)
                       and isinstance(n.value, ast.Attribute) and n.value.attr == "data"}
        self.assertEqual(data_fields, {"root_ang_vel_b", "projected_gravity_b"})

    def test_manifest_cannot_silently_describe_changed_cad(self):
        (self.project / "cad").mkdir()
        (self.project / "cad/MicroDuckling_R01.FCStd").write_bytes(b"changed CAD")
        self.manifest["source_cad_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "rerun derive_manifest"):
            validate_manifest(self.manifest, self.project)


if __name__ == "__main__":
    unittest.main()
