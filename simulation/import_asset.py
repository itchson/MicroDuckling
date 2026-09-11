"""Convert the URDF using Isaac Lab 2.3.2 / Isaac Sim 5.1 and verify inertias.

Run using the Isaac Lab Python environment. This script is not a simulator test.
"""
import argparse
import json
from pathlib import Path
from asset_integrity import verify_export, imported_files

from paths import SIMULATION as here
info = verify_export(here)

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
launcher = AppLauncher(args)
app = launcher.app
report_path = here / "usd/import_report.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
# An interrupted or failed re-import must not leave old passing evidence behind.
report_path.write_text(json.dumps({"status": "RUNNING", "urdf_sha256": info["urdf_sha256"]}) + "\n",
                       encoding="utf-8")

try:
    import numpy as np
    from pxr import Usd, UsdPhysics
    from isaaclab.sim.converters import UrdfConverter, UrdfConverterCfg

    class InertiaPreservingConverter(UrdfConverter):
        def _get_urdf_import_config(self):
            config = super()._get_urdf_import_config()
            config.set_import_inertia_tensor(True)
            return config

    cfg = UrdfConverterCfg(
        asset_path=str(here / "microduckling.urdf"),
        usd_dir=str(here / "usd"), usd_file_name="microduckling.usd",
        force_usd_conversion=True, make_instanceable=False,
        fix_base=False, merge_fixed_joints=False, root_link_name="body",
        collision_from_visuals=False, collider_type="convex_hull", self_collision=True,
        replace_cylinders_with_capsules=False,
        joint_drive=UrdfConverterCfg.JointDriveCfg(
            drive_type="force", target_type="none",
            gains=UrdfConverterCfg.JointDriveCfg.PDGainsCfg(stiffness=0.0, damping=0.0)),
    )
    output = InertiaPreservingConverter(cfg).usd_path
    stage = Usd.Stage.Open(output)
    found = {}
    for prim in stage.Traverse():
        name = prim.GetName()
        if name not in info["links"] or not prim.HasAPI(UsdPhysics.RigidBodyAPI):
            continue
        mass_api = UsdPhysics.MassAPI(prim)
        expected = info["links"][name]
        mass = float(mass_api.GetMassAttr().Get())
        com = np.asarray(mass_api.GetCenterOfMassAttr().Get())
        moments = np.asarray(mass_api.GetDiagonalInertiaAttr().Get())
        q = mass_api.GetPrincipalAxesAttr().Get()
        w = q.GetReal()
        x, y, z = q.GetImaginary()
        rot = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
        imported_tensor = rot @ np.diag(moments) @ rot.T
        i = expected["inertia_kg_m2"]
        expected_tensor = np.array([[i["ixx"], i["ixy"], i["ixz"]],
                                    [i["ixy"], i["iyy"], i["iyz"]],
                                    [i["ixz"], i["iyz"], i["izz"]]])
        assert np.isclose(mass, expected["mass_kg"], rtol=1e-4), f"{name}: mass changed"
        assert np.allclose(com, expected["com_m"], atol=1e-6), f"{name}: COM changed"
        assert np.allclose(imported_tensor, expected_tensor, rtol=2e-3, atol=1e-10), f"{name}: inertia changed"
        found[name] = {"mass_kg": mass, "com_m": com.tolist()}
    assert set(found) == set(info["links"]), "Imported link set changed"
    roots = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.ArticulationRootAPI)]
    joints = [p for p in stage.Traverse() if p.IsA(UsdPhysics.RevoluteJoint)]
    assert len(roots) == 1 and len(joints) == 4, "Expected one four-joint articulation"
    fixed = [p for p in stage.Traverse() if p.IsA(UsdPhysics.FixedJoint)]
    assert not fixed, "Unexpected fixed joint: root must float"
    report = {"status": "IMPORTED_AND_INERTIAS_VERIFIED", "training_run": False,
              "urdf_sha256": info["urdf_sha256"], "usd_path": output, "links": found,
              "source_manifest_sha256": info["source_manifest_sha256"],
              "artifact_sha256": imported_files(here)}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
except Exception as exc:
    report_path.write_text(json.dumps({"status": "FAILED", "urdf_sha256": info["urdf_sha256"],
                                      "error": f"{type(exc).__name__}: {exc}"}, indent=2) + "\n",
                           encoding="utf-8")
    raise
finally:
    app.close()
