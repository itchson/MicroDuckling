# Simulation experiments and Isaac scaffold

The viewer includes a **Rapier browser physics experiment and seeded cross-entropy method (CEM) search over bounded gait parameters**. The separate Python source provides CAD-to-URDF export, numerical validation, an Isaac Lab environment and a training-script wrapper. **No Isaac runtime execution, Isaac-trained policy or physical gait is supplied.** Generated URDF/USD and full link meshes are built locally because they contain vendor geometry.

## Browser physics and gait search

Run the [local viewer](../README.md#run-the-cad-viewer-locally) and use its physics controls. This model contains five floating/articulated rigid bodies, four revolute joints, gravity, a ground plane and 109 original box contact primitives. Mass, COM and principal inertia properties come from CAD-derived scalar data; the full intended mass is 0.257281 kg, including the electronics. Display meshes do not supply collision geometry or add their mass a second time. Self-collision is disabled because the interior contact boxes do not represent exact shell surfaces.

The force-based motor model follows position commands with a 3 rad/s command slew limit and a modeled 0.09 N·m effort ceiling, derated toward zero at 10.47 rad/s. Hip limits stay ±12°, neck yaw ±45° and jaw 0–12°. These are unmeasured actuator priors; displayed torque is a bounded PD estimate, not measured motor current or solver impulse telemetry. Body movement comes from physics integration, not an animation that assigns forward travel.

CEM evaluates sinusoidal gait candidates, retains the highest-scoring candidates and updates the sampling distribution for the next generation. It searches frequency, amplitudes, phase, hip biases and head-yaw oscillation. **Start gait search** runs up to 30 generations of eight candidates with four-second episodes; **Play best gait** replays the selected parameters. Reward uses simulated forward displacement, lateral/heading/tilt costs, survival and falls. This is parameter search over a small controller family; it does not train an Isaac neural policy or establish a controller ready for hardware. The base gait search uses a repeatable initial condition, so improvement does not establish robustness across surfaces, loads or seeds.

The standalone seed-42 engine check evaluated 25 episodes across three generations. Its best candidate moved **3.842 mm in four seconds**, against **0.024 mm neutral drift**, without falling. That small change can include stance adjustment and contact effects; it is not convincing evidence of walking. Re-evaluate after engine, contact or controller changes rather than carrying that result forward as a new model's score.

The normal viewer checks include the headless engine tests:

```sh
cd viewer
npm ci
npm test
npm run build
```

## Synthetic camera and controller search

The browser renders a **96 × 72 pixel** camera view from the front lens location. A color heuristic finds the largest connected magenta region and produces visibility, horizontal bearing and image-area fraction. The controller uses those image measurements, gait phase and issued neck-command history; target world coordinates are used to place the environment object, not as controller observations. This is a synthetic color-target experiment, not a learned object recognizer or physical ESP32-CAM feed.

**Learn camera control** tests 12 bounded controller settings in trials lasting up to six simulated seconds, ending early on a fall. It varies head tracking gain, differential hip bias gain and gait amplitude scaling, retaining the best observed score. **Try approach** runs those settings. **Pause**, **Reset** and **Save experiment** control the experiment and export its parameters/results; the saved JSON is not a hardware or Isaac policy.

The camera score rewards visibility, centering and growth in apparent target area, with a fall penalty. Apparent area is a proxy: head rotation and changing projection can improve the score without moving closer. No successful approach or walking demonstration is claimed. Tests cover the pixel detector and a six-second worker trial using deterministic observation fixtures, including rejection of observations from stale runs. Interactive WebGL camera QA remains outstanding, and no real camera, lighting, latency or hardware controller has been validated. The camera path is separate from the standalone gait result reported above.

Camera messages carry the simulated frame time and episode ID. Observations expire after 0.3 simulated seconds; missing images cause a stationary head scan. A candidate is eligible only after at least ten fresh observations cover at least half the trial, with no fall. Visibility is weighted by covered trial time, rather than counting a single retained image as continuous observation. Switching workspace tabs pauses the experiment and retains its results until a page reload.

## Isaac Lab scaffold

The existing API target is **Isaac Lab v2.3.2 with Isaac Sim 5.1**, as listed in its [compatibility table](https://github.com/isaac-sim/IsaacLab/tree/v2.3.2#isaac-sim-version-dependency). This is the scaffold's target, not a recommendation to install an obsolete runtime. Migration to a current release requires API review and a real import/environment smoke test before changing that claim.

### Articulation and units

| Joint order | Parent → child | Axis | Nominal limit |
|---|---|---|---|
| `left_hip` | body → left_leg | local Y | ±12° |
| `right_hip` | body → right_leg | local Y | ±12° |
| `neck_yaw` | body → head | local Z | ±45° |
| `jaw_pitch` | head → jaw | local Y | 0–12° |

The body is a floating rigid body. CAD axes are X forward, Y left, Z up. Lengths/meshes are millimetres; export converts translations and COM once to metres and uses mesh scale 0.001. Mass is kilograms and inertia is kg·m². Component inertia tensors are combined about link COMs using the parallel-axis theorem. Servo cases belong to the link holding the case; horns belong to rotating links.

Each curved sole uses a two-dimensional grid of tangent boxes, with rounded corner cells inset and slight overlap to reduce gaps. Other links use simple interior collision primitives. These approximate contact geometry and omit some exterior surfaces; inspect cooking, seams and fall contacts in the simulator. The initial physics step is 2 ms, command interval 20 ms, contact offset 0.2 mm, rest offset zero. Compare 1 ms and finer sole segmentation before accepting behavior.

### Servo and observation assumptions

The policy produces four normalized position commands. The simulated internal servo plant adds command delay, lag, backlash, bounded gains and a speed-dependent effort limit. Initial priors include 0–40 ms transport delay, 20–80 ms lag, 0.008–0.035 rad backlash, 0.06–0.11 N·m zero-speed effort ceiling and a 3 rad/s command slew limit. These are unmeasured modeling choices; stall torque is not a continuous rating. The model has no thermal, supply brownout or measured electrical plant.

The actor receives four frames of 14 values: body gyro XYZ, projected gravity XYZ, four requested motion/pose commands and four issued servo commands. It receives no measured joint angle/velocity, root linear velocity, foot contact or simulation phase. A stock three-wire MG90S provides no joint-angle telemetry. Firmware would need matching ordering, normalization, history reset, joint signs, zero offsets, safe limits and slew handling. No such firmware is included.

Friction, restitution, mass scale and actuator properties are randomized around uncalibrated priors. Calibrate servo neutral/endpoints and loaded lag with an external pointer or camera; log commands, voltage, current and temperature. Identify IMU axes/filter delay, link mass and surface/tread behavior, then validate on separate sequences. Two hip axes support a low-speed rocking/shuffling experiment, not general humanoid foot placement or recovery.

### Reproduce and run

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
