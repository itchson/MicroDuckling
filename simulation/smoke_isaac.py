"""Bounded runtime smoke test for the exported floating-base four-servo robot.

No training occurs. A passing finite-state test does not establish walking.
Run in Isaac Lab after import_asset.py. Output records falls rather than hiding them.
"""
import argparse
import json
from pathlib import Path
from asset_integrity import digest, verify_import

from paths import SIMULATION as here, SOURCE_SIMULATION
info, import_report = verify_import(here)

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--seconds", type=float, default=5.0)
parser.add_argument("--physics-dt", type=float, choices=(.001, .002), default=.002,
                    help="Use 1 ms to compare contact/solver convergence against the 2 ms baseline.")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if not 1 <= args.seconds <= 30:
    parser.error("seconds must be between 1 and 30")
launcher = AppLauncher(args)
app = launcher.app
report_path = here / "isaac_smoke_report.json"
report = {"status": "RUNNING", "training_run": False, "walking_validated": False,
          "import_report_sha256": digest(here / "usd/import_report.json"),
          "environment_sha256": digest(SOURCE_SIMULATION / "microduckling_lab/environment.py"),
          "urdf_sha256": info["urdf_sha256"], "physics_dt_s": args.physics_dt,
          "control_dt_s": .02, "servo_parameters": "nominal midpoint priors; zero command delay"}
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
env = None
try:
    import torch
    from microduckling_lab.environment import MicroDucklingEnv, MicroDucklingEnvCfg

    cfg = MicroDucklingEnvCfg()
    cfg.scene.num_envs = 1
    cfg.events = None  # Verify nominal CAD mass, without startup mass randomization.
    cfg.randomize_servos = False
    cfg.seed = 42
    cfg.sim.dt = args.physics_dt
    cfg.decimation = round(.02 / args.physics_dt)
    cfg.sim.render_interval = cfg.decimation
    cfg.sim.device = args.device
    env = MicroDucklingEnv(cfg)
    obs, _ = env.reset()
    assert obs["policy"].shape == (1, 56)
    fall_count = 0
    max_effort = 0.0
    min_root_z = float("inf")
    q_min = torch.full((4,), float("inf"), device=env.device)
    q_max = -q_min
    for step in range(int(args.seconds / env.step_dt)):
        # Bounded diagnostic motion; no prescribed base trajectory and no guaranteed gait.
        phase = torch.tensor(step * env.step_dt * 4.0, device=env.device)
        target = torch.zeros((1, 4), device=env.device)
        target[:, 0] = .1 * torch.sin(phase)
        target[:, 1] = -.1 * torch.sin(phase)
        target[:, 2] = .1 * torch.sin(phase / 2)
        target[:, 3] = env.upper[3] * .25 * (1 + torch.sin(phase))
        action = ((target - env.center) / env.half).clamp(-1, 1)
        obs, reward, terminated, truncated, extra = env.step(action)
        assert torch.isfinite(obs["policy"]).all() and torch.isfinite(reward).all()
        pre_reset = env.last_pre_reset
        assert pre_reset["finite"].all(), "Nonfinite state occurred before automatic reset"
        max_effort = max(max_effort, pre_reset["efforts"].abs().max().item())
        assert max_effort <= 0.110001
        min_root_z = min(min_root_z, pre_reset["root_z"][0].item())
        q = pre_reset["joint_pos"][0]
        q_min = torch.minimum(q_min, q)
        q_max = torch.maximum(q_max, q)
        fall_count += int(terminated.sum())
    report.update(status="FINITE_BOUNDED_SIMULATION", simulated_seconds=args.seconds,
                  joint_order=env.robot.find_joints(env.cfg.robot_cfg.actuators["servo_plant"].joint_names_expr,
                                                   preserve_order=True)[1],
                  fall_resets=fall_count, maximum_commanded_effort_Nm=max_effort,
                  minimum_pre_reset_root_z_m=min_root_z,
                  maximum_joint_limit_violation_rad=float(torch.maximum(
                      env.lower - q_min, q_max - env.upper).clamp_min(0).max()),
                  observed_joint_min_rad=q_min.tolist(), observed_joint_max_rad=q_max.tolist())
except Exception as exc:
    report.update(status="FAILED", error=f"{type(exc).__name__}: {exc}")
    raise
finally:
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if env is not None:
        env.close()
    app.close()
