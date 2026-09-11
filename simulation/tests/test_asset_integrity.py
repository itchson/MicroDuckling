"""Stale artifact evidence must not authorize running a different robot."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_integrity import digest, imported_files, verify_export, verify_import, verify_smoke


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.here = self.project / "simulation"
        (self.here / "usd/layers").mkdir(parents=True)
        (self.here / "microduckling_lab").mkdir()
        cad = self.project / "cad"
        cad.mkdir()
        (cad / "MicroDuckling_R01.FCStd").write_bytes(b"cad revision")
        (cad / "assembly.json").write_text("{}")
        self.write(cad / "manifest.json", {
            "source_cad_sha256": digest(cad / "MicroDuckling_R01.FCStd"),
            "source_assembly_sha256": digest(cad / "assembly.json")})
        (self.here / "microduckling.urdf").write_bytes(b"robot revision")
        (cad / "mesh.stl").write_bytes(b"mesh revision")
        self.info = {"source_manifest_sha256": digest(cad / "manifest.json"),
                     "mesh_sha256": {"cad/mesh.stl": digest(cad / "mesh.stl")},
                     "urdf_sha256": digest(self.here / "microduckling.urdf")}
        self.write(self.here / "robot_info.json", self.info)
        (self.here / "usd/microduckling.usd").write_bytes(b"root layer")
        (self.here / "usd/layers/mesh.usd").write_bytes(b"collision mesh")
        (self.here / "microduckling_lab/environment.py").write_text("# environment")
        self.report = dict(self.info, status="IMPORTED_AND_INERTIAS_VERIFIED",
                           artifact_sha256=imported_files(self.here))
        self.write(self.here / "usd/import_report.json", self.report)
        self.smoke = {"status": "FINITE_BOUNDED_SIMULATION",
                      "import_report_sha256": digest(self.here / "usd/import_report.json"),
                      "environment_sha256": digest(self.here / "microduckling_lab/environment.py")}
        self.write(self.here / "isaac_smoke_report.json", self.smoke)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_matching_export_import_smoke_chain_accepted(self):
        self.assertEqual(verify_export(self.here), self.info)
        self.assertEqual(verify_import(self.here)[1], self.report)
        self.assertEqual(verify_smoke(self.here), self.smoke)

    def test_cad_edit_without_reexport_is_rejected(self):
        (self.project / "cad/MicroDuckling_R01.FCStd").write_bytes(b"moved battery")
        with self.assertRaisesRegex(ValueError, "derive_manifest"):
            verify_import(self.here)

    def test_nested_usd_edit_or_missing_file_is_rejected(self):
        path = self.here / "usd/layers/mesh.usd"
        path.write_bytes(b"wrong collision geometry")
        with self.assertRaisesRegex(ValueError, "Imported artifact"):
            verify_import(self.here)
        path.unlink()
        with self.assertRaisesRegex(ValueError, "Imported artifact"):
            verify_import(self.here)

    def test_visual_mesh_change_requires_reexport(self):
        (self.project / "cad/mesh.stl").write_bytes(b"wrong length units")
        with self.assertRaisesRegex(ValueError, "Exported mesh changed"):
            verify_export(self.here)

    def test_failed_or_stale_smoke_rejected(self):
        self.smoke["status"] = "FAILED"
        self.write(self.here / "isaac_smoke_report.json", self.smoke)
        with self.assertRaisesRegex(ValueError, "stale or failed"):
            verify_smoke(self.here)

    def test_environment_source_can_stay_outside_generated_build(self):
        source = self.project / "environment-source.py"
        source.write_text("# environment")
        self.assertEqual(verify_smoke(self.here, source), self.smoke)
        source.write_text("# changed actuator model")
        with self.assertRaisesRegex(ValueError, "stale or failed"):
            verify_smoke(self.here, source)
        self.smoke["status"] = "FINITE_BOUNDED_SIMULATION"
        self.write(self.here / "isaac_smoke_report.json", self.smoke)
        (self.here / "microduckling_lab/environment.py").write_text("# changed servo torque")
        with self.assertRaisesRegex(ValueError, "stale or failed"):
            verify_smoke(self.here)


if __name__ == "__main__":
    unittest.main()
