# Simulation and training scaffold

The source provides CAD-to-URDF export, numerical validation, an Isaac Lab environment and a training-script wrapper. **No Isaac import, runtime test, trained policy or physical gait is supplied.** Generated URDF/USD and full link meshes are built locally because they contain vendor geometry.

The existing API target is **Isaac Lab v2.3.2 with Isaac Sim 5.1**, as listed in its [compatibility table](https://github.com/isaac-sim/IsaacLab/tree/v2.3.2#isaac-sim-version-dependency). This is the scaffold's target, not a recommendation to install an obsolete runtime. Migration to a current release requires API review and a real import/environment smoke test before changing that claim.

## Articulation and units

| Joint order | Parent → child | Axis | Nominal limit |
|---|---|---|---|
| `left_hip` | body → left_leg | local Y | ±12° |
| `right_hip` | body → right_leg | local Y | ±12° |
| `neck_yaw` | body → head | local Z | ±45° |
| `jaw_pitch` | head → jaw | local Y | 0–12° |

The body is a floating rigid body. CAD axes are X forward, Y left, Z up. Lengths/meshes are millimetres; export converts translations and COM once to metres and uses mesh scale 0.001. Mass is kilograms and inertia is kg·m². Component inertia tensors are combined about link COMs using the parallel-axis theorem. Servo cases belong to the link holding the case; horns belong to rotating links.

Each curved sole uses a two-dimensional grid of tangent boxes, with rounded corner cells inset and slight overlap to reduce gaps. Other links use simple interior collision primitives. These approximate contact geometry and omit some exterior surfaces; inspect cooking, seams and fall contacts in the simulator. The initial physics step is 2 ms, command interval 20 ms, contact offset 0.2 mm, rest offset zero. Compare 1 ms and finer sole segmentation before accepting behavior.

## Servo and observation assumptions

The policy produces four normalized position commands. The simulated internal servo plant adds command delay, lag, backlash, bounded gains and a speed-dependent effort limit. Initial priors include 0–40 ms transport delay, 20–80 ms lag, 0.008–0.035 rad backlash, 0.06–0.11 N·m zero-speed effort ceiling and a 3 rad/s command slew limit. These are unmeasured modeling choices; stall torque is not a continuous rating. The model has no thermal, supply brownout or measured electrical plant.

The actor receives four frames of 14 values: body gyro XYZ, projected gravity XYZ, four requested motion/pose commands and four issued servo commands. It receives no measured joint angle/velocity, root linear velocity, foot contact or simulation phase. A stock three-wire MG90S provides no joint-angle telemetry. Firmware would need matching ordering, normalization, history reset, joint signs, zero offsets, safe limits and slew handling. No such firmware is included.

Friction, restitution, mass scale and actuator properties are randomized around uncalibrated priors. Calibrate servo neutral/endpoints and loaded lag with an external pointer or camera; log commands, voltage, current and temperature. Identify IMU axes/filter delay, link mass and surface/tread behavior, then validate on separate sequences. Two hip axes support a low-speed rocking/shuffling experiment, not general humanoid foot placement or recovery.

## Reproduce and run

First complete the [local CAD and asset derivation](build.md). All generated outputs default to `build/local/`; an explicit `MICRODUCKLING_BUILD_ROOT` changes that root consistently for CAD, audits and simulation. The source and downloaded reference cache remain in the repository.

Static steps use ordinary Python after the FreeCAD derivation:

```sh
python simulation/export_urdf.py
python simulation/validate_assets.py
python simulation/assess_balance.py
python -m unittest discover -s simulation/tests -v
```

For a compatible, separately installed Isaac Lab checkout, set `$lab` to its directory and run from the repository root:

```powershell
& "$lab/isaaclab.bat" -p simulation/import_asset.py --headless
& "$lab/isaaclab.bat" -p simulation/smoke_isaac.py --seconds 5 --headless
& "$lab/isaaclab.bat" -p simulation/run_rl.py --isaaclab-root $lab --mode train --task MicroDuckling-Flat-v0 --num_envs 64 --max_iterations 10 --headless
```

Linux uses `isaaclab.sh` with the corresponding arguments. The wrapper delegates to the installed RSL-RL workflow; it does not bundle or modify it. Import checks compare link masses, COMs and full inertia tensors. Training requires matching import evidence and a current bounded smoke report; changed CAD, meshes, nested USD assets or environment source invalidate stale evidence. Ten training iterations would test the pipeline, not prove a useful gait.

Inspect the scene visibly and record falls, travel, slip, tracking error, torque and sustained load over multiple seeds and held-out parameters. Complete power shutdown and mechanical qualification before attempting constrained physical deployment.
