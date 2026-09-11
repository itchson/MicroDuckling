# Simulation experiments and Isaac scaffold

The viewer runs rigid-body physics, searches bounded gait parameters and tests image-guided approach. Its browser model is separate from the Isaac Lab scaffold. No Isaac runtime execution, Isaac-trained policy or physical walking result is supplied.

## Browser contact and weight

Five articulated rigid bodies and four revolute joints move under gravity. Continuous hulls derived from the actual tread meshes plus interior contact envelopes give nine robot colliders. The default is 600 Hz integration with 16 solver iterations. The old 109-box contact layout remains an explicit comparison option; its apparent gait speed was sensitive to timestep and is not the default. Mass, COM and inertia derive from the complete current CAD, including the upper bill and simplified electronics. Collider geometry does not add mass again.

The interface shows COM, loaded contacts, slip speed, weight and estimated support. Ground friction and mass scaling restart the experiment so old scores do not describe a changed environment. Debug markers are excluded from the robot's camera image. See [contact physics and force definitions](browser-contact-physics.md): support uses momentum balance; per-foot loads use solver-impulse shares and are estimates. Tangential force is unavailable, rather than displayed as a false zero.

Self-collision is disabled because the interior envelopes are not exact outer shell shapes. The actuator model uses bounded PD effort, a 3 rad/s command slew limit, a 0.09 N·m effort ceiling and a 10.47 rad/s speed prior. Hip travel is ±12°, neck yaw ±45° and jaw opening 0–12°. These are unmeasured motor assumptions, with no thermal or electrical plant. Forward motion comes from integrated contact dynamics; no animation translates the body along a path.

## Gait search

**Try reference gait** plays a bundled, physically evaluated rocking gait with out-of-phase hips and a free camera-controlled neck. Replaying this reference is not labeled new learning. **Start gait search** evaluates neutral and the supplied seed, then runs up to 12 generations of 12 physical, 14-second candidate episodes. A phase-aware cross-entropy search varies frequency, bias, amplitude, duty, harmonics, phase and jaw motion. Each episode settles for one second before measurement.

The score rewards sustained late-episode COM velocity and net forward travel with lateral, heading and tilt costs. Falls are rejected. The interface reports actual episodes, speed, displacement and whether a newly searched candidate improved on the supplied seed. Parameter search in this small controller family is not a trained Isaac neural policy. Use held-out surfaces, loads and reset seeds before judging robustness.

The [R06 gait evidence](validation/r06-locomotion-summary.json) evaluates 12 thirty-second trials across three reset seeds, 600/1000 Hz and 16/24 solver iterations. There were no falls; mean forward travel was 234.6–239.8 mm, within −0.8% to +1.4% of the default setup. Open-loop lateral drift reached 58.2 mm, so straight walking still benefits from feedback. An eight-generation search evaluated 98 real episodes and improved 14-second travel from 112.6 to 146.1 mm on its training seed; the 31.2% late-speed gain is an in-sample result, not held-out or hardware validation. Exact candidates are in the [training record](validation/r06-locomotion-training-results.json).

Reproduce these longer checks from the repository root:

```sh
node --experimental-strip-types viewer/scripts/verification/open-loop.mjs
node --experimental-strip-types viewer/scripts/verification/training.mjs
```

## Image-guided approach

The synthetic camera uses 96 × 72 pixels, a 50° vertical field of view and the modeled head/lens transform. A color heuristic extracts the largest magenta region's bearing and width. The actor receives those image measurements, gait time and issued neck-command history; it receives no target coordinates, body pose or joint-angle telemetry.

**Train to target** compares 12 bounded settings for head tracking, differential hip steering, amplitude and image-width stopping. Trials last up to 60 simulated seconds. The target is a 50 × 50 × 100 mm block, initially 180 mm forward and optionally 40 mm left or right. Its height keeps it in view as the robot approaches with a horizontal camera.

The environment scores signed physical closing and retained progress, rather than apparent image area. Success requires at least 25 mm progress, a body-COM range of 110–130 mm, body heading within 20°, tilt within 15°, and 1.5 continuous seconds meeting those requirements. The controller's stop latch uses only filtered apparent width. Turning the head to look at the object while standing still cannot satisfy success.

The [R06 camera search record](validation/r06-camera-learning.json) evaluates all 12 candidate settings: eight succeed and four time out, with no falls. The selected candidate improves score from 16.75 to 17.38 and succeeds in all six held-out target/seed cases. The starting policy already succeeds; this demonstrates parameter refinement, not learning approach from scratch. Reproduce after preparing the viewer assets with `node --experimental-strip-types viewer/scripts/verification/camera-learning.mjs` from the repository root. Default parameters remain the separately tested reference settings.

Each image carries the episode ID and exact simulated frame time. A matching image advances six 60 Hz command updates, with 600 Hz physics underneath. Missing or stale images do not advance time or accrue dwell/reward. Training can render faster than real time; playback captures at roughly 10 Hz. Switching workspace tabs pauses the experiment. **Save experiment** exports the environment, controller and measured results, not a hardware or Isaac policy.

Regression tests use the actual CAD triangle meshes to form camera pixels with occlusion, then run the same controller and goal logic across ahead/left/right targets and two seeds. Worker tests separately verify stale-image rejection, physical scoring and real candidate evaluation. This is geometric camera testing; interactive WebGL QA, real camera lighting/latency and physical hardware remain unverified.

```sh
cd viewer
npm ci
npm test
npm run build
node --experimental-strip-types scripts/evaluate-approach.mjs
```

The [current six-episode record](validation/r06-camera-approach.json) reports six successes in 7.77–9.47 simulated seconds after the R06 mass update. The evaluator writes reproducible parameters, asset hash and episode traces under ignored `work/`. Re-run it whenever CAD, contact geometry, camera optics or controllers change.

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
