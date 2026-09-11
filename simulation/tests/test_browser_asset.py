"""Public sole geometry, units, provenance and complete browser asset derivation."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser.derive_asset import derive, RECOMMENDED_SETTINGS
from browser.sole_hulls import attach_sole_hulls

ROOT = Path(__file__).resolve().parents[2]


def fixture(directory):
    names = ["body", "left_leg", "right_leg", "head", "jaw"]
    tensor = dict(ixx=2e-5, ixy=0, ixz=0, iyy=3e-5, iyz=0, izz=4e-5)
    links = [dict(name=n, mass_kg=.02, com_mm=[1, 2, 3], frame_origin_global_mm=[0, 0, 38],
                  inertia_kg_m2=tensor.copy(), collisions=[dict(name="core", type="box", size_mm=[10, 8, 6],
                  origin_xyz_mm=[1, 2, 3], origin_rpy_rad=[0, 0, 0])]) for n in names]
    manifest = dict(source_cad_sha256="a" * 64, links=links, joints=[], rocker_contact=dict(radius_mm=100,
                    planform_bounds_xy_mm={n: [-30, 30, -15, 15] for n in names if n.endswith("_leg")},
                    centers_global_mm={n: [0, 0, 100] for n in names if n.endswith("_leg")}))
    path = directory / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    for name in ["TreadLeft", "TreadRight"]:
        (directory / f"{name}.json").write_text(json.dumps({"positions": [0, 0, 0, 10, 0, 0, 0, 10, 0, 0, 0, 3, 0, 0, 0]}), encoding="utf-8")
    return path


class BrowserAssetTests(unittest.TestCase):
    def test_complete_derivation_preserves_units_mass_and_physics_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = fixture(folder)
            asset = derive(source, folder)
            self.assertAlmostEqual(asset["totalMassKg"], .1)
            link = asset["links"][0]
            self.assertEqual(link["comM"], [.001, .002, .003])
            self.assertEqual(link["principalInertiaKgM2"], [2e-5, 3e-5, 4e-5])
            self.assertEqual(link["colliders"][0]["halfExtentsM"], [.005, .004, .003])
            self.assertEqual(asset["contactModel"]["recommendedSettings"], RECOMMENDED_SETTINGS)
            self.assertEqual(asset["provenance"]["manifestSha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            for leg in [x for x in asset["links"] if x["name"].endswith("_leg")]:
                points = list(zip(*[iter(leg["soleConvexHullM"])] * 3))
                self.assertEqual(len(points), 4, "duplicate source vertices are deduplicated")
                self.assertIn((0, 0, -.038), points, "global mm becomes link-local metres exactly once")
                self.assertIn((.01, 0, -.038), points)
                self.assertTrue(any(c["name"].startswith("rocker_") for c in leg["colliders"]), "legacy comparison remains possible")

    def test_cli_regeneration_is_deterministic_and_does_not_overwrite_source(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = fixture(folder)
            before = source.read_bytes()
            outputs = [folder / "first/asset.json", folder / "second/asset.json"]
            for output in outputs:
                subprocess.run([sys.executable, str(ROOT / "simulation/browser/derive_asset.py"), str(source),
                                str(output), "--mesh-dir", str(folder)], check=True, capture_output=True)
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
            self.assertEqual(source.read_bytes(), before)
            self.assertNotIn(str(folder), outputs[0].read_text(encoding="utf-8"))

    def test_current_public_hulls_roundtrip_from_original_cad_vertices(self):
        current = json.loads((ROOT / "simulation/browser/robot-physics.json").read_text(encoding="utf-8"))
        before = copy.deepcopy(current)
        rebuilt = attach_sole_hulls(current, ROOT / "cad/meshes")
        self.assertEqual(current, before, "attaching hulls must not mutate caller data")
        for original, updated in zip(current["links"], rebuilt["links"]):
            self.assertEqual(original, updated)
        self.assertEqual(rebuilt["provenance"]["soleConvexHull"], current["provenance"]["soleConvexHull"])
        self.assertEqual(rebuilt["totalMassKg"], current["totalMassKg"])

    def test_changed_source_bytes_update_provenance_without_changing_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = fixture(folder)
            asset = derive(source, folder)
            mesh = folder / "TreadLeft.json"
            mesh.write_text(mesh.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            changed = attach_sole_hulls(asset, folder)
            left = lambda a: a["provenance"]["soleConvexHull"]["sources"]["left_leg"]
            self.assertNotEqual(left(asset)["sha256"], left(changed)["sha256"])
            self.assertEqual(asset["links"], changed["links"])

    def test_invalid_and_planar_hulls_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = fixture(folder)
            for positions in [[0, 0, 0] * 4, [0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0], [float("nan"), 0, 0], [1, 2]]:
                (folder / "TreadLeft.json").write_text(json.dumps({"positions": positions}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    derive(source, folder)


if __name__ == "__main__":
    unittest.main()
