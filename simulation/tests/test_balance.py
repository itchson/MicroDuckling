"""Hand-calculated mass/lever-arm cases for the CAD balance assessment."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assess_balance import ideal_contacts, pose_metrics


def fixture():
    inertia = dict(ixx=.01, ixy=0, ixz=0, iyy=.01, iyz=0, izz=.01)
    links = [dict(name=n, mass_kg=1., com_mm=[10, 0, 0] if n == "jaw" else [0, 0, 0],
                  inertia_kg_m2=inertia.copy(), frame_origin_global_mm=[0, 0, 0])
             for n in ("body", "left_leg", "right_leg", "head", "jaw")]
    joints = [dict(name=n, parent=p, child=c, origin_xyz_mm=t, axis=a)
              for n,p,c,t,a in [("left_hip","body","left_leg",[0,40,0],[0,1,0]),
                                ("right_hip","body","right_leg",[0,-40,0],[0,1,0]),
                                ("neck_yaw","body","head",[0,0,50],[0,0,1]),
                                ("jaw_pitch","head","jaw",[20,0,0],[0,1,0])]]
    return dict(links=links, joints=joints, rocker_contact=dict(radius_mm=110,
        centers_global_mm={"left_leg":[0,30,110],"right_leg":[0,-30,110]},
        planform_bounds_xy_mm={"left_leg":[-34,36,4,56],"right_leg":[-34,36,-56,-4]}))


class BalanceTests(unittest.TestCase):
    def test_neutral_com_gravity_moment_and_parallel_axis(self):
        result = pose_metrics(fixture())
        np.testing.assert_allclose(result["global_com_mm"], [6, 0, 20], atol=1e-12)
        self.assertAlmostEqual(result["head_and_jaw_mass_fraction"], .4)
        self.assertAlmostEqual(result["combined_static_hip_pitch_moment_Nm"], 9.80665 * .03)
        self.assertAlmostEqual(result["head_and_jaw_yaw_inertia_about_neck_kg_m2"], .02 + .03**2)

    def test_yaw_moves_head_mass_sideways_without_fake_vertical_offset(self):
        result = pose_metrics(fixture(), neck=np.pi/2)
        np.testing.assert_allclose(result["global_com_mm"], [0, 6, 20], atol=1e-12)
        self.assertAlmostEqual(result["combined_static_hip_pitch_moment_Nm"], 0)
        self.assertAlmostEqual(result["head_and_jaw_yaw_inertia_about_neck_kg_m2"], .0209)

    def test_jaw_rotation_changes_com_and_yaw_inertia(self):
        result = pose_metrics(fixture(), jaw=np.pi/2)
        np.testing.assert_allclose(result["global_com_mm"], [4, 0, 18], atol=1e-12)
        self.assertAlmostEqual(result["head_and_jaw_yaw_inertia_about_neck_kg_m2"], .0204)

    def test_rounded_feet_do_not_imply_flat_support_area(self):
        result = ideal_contacts(fixture(), [6, 0, 20])
        self.assertAlmostEqual(result["projection_distance_to_contact_segment_mm"], 6)
        self.assertTrue(result["lateral_projection_between_contacts"])
        self.assertAlmostEqual(result["ground_height_mm"], 0)


if __name__ == "__main__":
    unittest.main()
