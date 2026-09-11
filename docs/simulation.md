# Simulation experiments and Isaac scaffold

The viewer runs rigid-body physics, searches bounded gait parameters and tests image-guided approach. Its browser model is separate from the Isaac Lab scaffold. No Isaac runtime execution, Isaac-trained policy or physical walking result is supplied. R06 and R07 traces below are retained as historical evidence and do not certify changed R08 assets; consult the [R08 design record](r08-upper-mouth-design.md) for matching CAD and camera-approach checks. Training was not rerun for R08.

## Browser contact and weight

Five articulated rigid bodies and four revolute joints move under gravity. Continuous hulls derived from the actual tread meshes plus interior contact envelopes give nine robot colliders. The default is 600 Hz integration with 16 solver iterations. The old 109-box contact layout remains an explicit comparison option; its apparent gait speed was sensitive to timestep and is not the default. Mass, COM and inertia derive from the complete current CAD, including the independent face panel, shell-mounted upper-mouth base, direct servo sockets and simplified electronics. Collider geometry does not add mass again.

The interface shows COM, loaded contacts, slip speed, weight and estimated support. Ground friction and mass scaling restart the experiment so old scores do not describe a changed environment. Debug markers are excluded from the robot's camera image. See [contact physics and force definitions](browser-contact-physics.md): support uses momentum balance; per-foot loads use solver-impulse shares and are estimates. Tangential force is unavailable, rather than displayed as a false zero.

Self-collision is disabled because the interior envelopes are not exact outer shell shapes. The actuator model uses bounded PD effort, a 3 rad/s command slew limit, a 0.09 N·m effort ceiling and a 10.47 rad/s speed prior. Hip travel is ±12°, neck yaw ±45° and jaw opening 0–12°. These are unmeasured motor assumptions, with no thermal or electrical plant. Forward motion comes from integrated contact dynamics; no animation translates the body along a path.

## Gait search

**Step & balance** offers a custom swing, forward lean, pace, left/right phase, step timing and optional head sway. **Apply custom gait** selects those settings for playback, camera approach and the next search seed. Swing automatically shrinks as lean approaches the ±12° hip limit; commanded lean is not guaranteed body tilt. Camera tracking takes control of the neck during approach. **Restore reference** returns to the bundled gait, and **Play selected gait** runs whichever controller is selected.

Replaying the reference is not labeled new learning. **Start gait search** evaluates neutral and the selected seed, then runs up to 12 generations of 12 physical, 14-second candidate episodes. A phase-aware cross-entropy search varies frequency, bias, amplitude, duty, harmonics, phase and jaw motion. Each episode settles for one second before measurement. Search can change the custom seed settings; the sliders remain an editable draft until applied again.

The score rewards sustained late-episode COM velocity and net forward travel with lateral, heading and tilt costs. Falls are rejected. The interface reports actual episodes, speed, displacement and whether a newly searched candidate improved on the supplied seed. Parameter search in this small controller family is not a trained Isaac neural policy. Use held-out surfaces, loads and reset seeds before judging robustness.

Historical [R06 gait evidence](validation/r06-locomotion-summary.json) evaluates 12 thirty-second trials across three reset seeds, 600/1000 Hz and 16/24 solver iterations. There were no falls; mean forward travel was 234.6–239.8 mm, within −0.8% to +1.4% of the default setup. Open-loop lateral drift reached 58.2 mm, so straight walking still benefits from feedback. An eight-generation search evaluated 98 real episodes and improved 14-second travel from 112.6 to 146.1 mm on its training seed; the 31.2% late-speed gain is an in-sample result, not held-out or hardware validation. Exact candidates are in the [training record](validation/r06-locomotion-training-results.json).

Run new longer checks against the prepared current assets from the repository root. Reproducing a historical result requires the matching recorded CAD, controller and runtime hashes; a new run against R08 is a new experiment:

```sh
node --experimental-strip-types viewer/scripts/verification/open-loop.mjs
node --experimental-strip-types viewer/scripts/verification/training.mjs
```

## Image-guided approach

The synthetic camera uses 96 × 72 pixels, a 50° vertical field of view and the modeled head/lens transform. A color heuristic extracts the largest magenta region's bearing and width. The actor receives those image measurements, gait time and issued neck-command history; it receives no target coordinates, body pose or joint-angle telemetry.

Drag the magenta block or enable **Place target on ground** and click the floor. Sliders also position it precisely in a forward training area: 160–600 mm ahead and up to 400 mm either side. The 50 × 50 × 100 mm block stays on the ground. Moving it pauses and resets the episode, invalidating old camera frames. Left/ahead/right presets remain available.

**Search & trial settings** adjusts the head's lost-target sweep (0–45° each side), sweep period (2–12 seconds) and episode limit (15–120 simulated seconds). Search uses camera pixels; no target coordinates reach the actor. Wider or more distant placements can need longer trials and better steering. This bounded frontal workspace is not a demonstrated all-direction navigation system.

**Train to target** compares 12 bounded settings for head tracking, differential hip steering, amplitude and image-width stopping. The default time limit remains 60 seconds. Ground friction, foot friction and mass scale are editable; changing them resets old scores while retaining the selected gait. **Save experiment** includes the target, environment, search settings, selected policy, custom-gait draft and measured results.

The matching [R08 approach record](validation/r08-camera-approach.json) contains **12 successful episodes with no falls**, across six target placements and reset seeds 2026 and 42. It includes an initially out-of-view target; completion took **8.55–46.77 simulated seconds**. The evaluator checks canonical and cached camera meshes plus source hashes, so the record identifies the exact R08 geometry and controller tested. This uses the existing controller settings; it is an approach regression run, and training was not rerun for R08.

The historical [R07 approach record](validation/r07-camera-approach.json) contains **12 successful episodes** across six positions and two reset seeds. It includes 280 mm-forward / 80 mm-left, 240 mm-forward / 100 mm-right, and an initially out-of-view 180 mm-forward / 160 mm-left target. Completion took 8.65–29.55 simulated seconds, with no falls. These finite cases do not prove every placement or custom gait succeeds.

The historical [R07 camera search](validation/r07-camera-learning.json) evaluates 12 candidates: eight succeed and four time out, with no falls. The selected candidate improves score by 0.71 over the already-working initial controller and succeeds in all six held-out target/seed cases. The offline camera uses exact CAD triangle intersections accelerated by a BVH; regression checks compare hits with ordinary triangle raycasting. Interactive WebGL and pointer-drag QA remain separate from these automated tests.

The environment scores signed physical closing and retained progress, rather than apparent image area. Success requires at least 25 mm progress, a body-COM range of 110–130 mm, body heading within 20°, tilt within 15°, and 1.5 continuous seconds meeting those requirements. The controller's stop latch uses only filtered apparent width. Turning the head to look at the object while standing still cannot satisfy success.

The historical [R06 camera search record](validation/r06-camera-learning.json) evaluates all 12 candidate settings: eight succeed and four time out, with no falls. The selected candidate improves score from 16.75 to 17.38 and succeeds in all six held-out target/seed cases. The starting policy already succeeds; this demonstrates parameter refinement, not learning approach from scratch. The reusable search harness is `node --experimental-strip-types viewer/scripts/verification/camera-learning.mjs`, run from the repository root after preparing matching viewer assets. It records the current source and asset hashes; running it on R08 would create a new training experiment, not reproduce the historical record. No such R08 training result is supplied. Default parameters remain the reference settings.

Each image carries the episode ID and exact simulated frame time. A matching image advances six 60 Hz command updates, with 600 Hz physics underneath. Missing or stale images do not advance time or accrue dwell/reward. Training can render faster than real time; playback captures at roughly 10 Hz. Switching workspace tabs pauses the experiment. **Save experiment** exports the environment, controller and measured results, not a hardware or Isaac policy.

Regression tests use the actual CAD triangle meshes to form camera pixels with occlusion, then run the same controller and goal logic across ahead/left/right targets and two seeds. Worker tests separately verify stale-image rejection, physical scoring and real candidate evaluation. This is geometric camera testing; interactive WebGL QA, real camera lighting/latency and physical hardware remain unverified.

```sh
cd viewer
npm ci
npm test
npm run build
node --experimental-strip-types scripts/evaluate-approach.mjs
```

The historical [R06 six-episode record](validation/r06-camera-approach.json) reports six successes in 7.77–9.47 simulated seconds after the R06 mass update. The evaluator writes reproducible parameters, asset hash and episode traces under ignored `work/`. Re-run it whenever CAD, contact geometry, camera optics or controllers change.

## Isaac Lab scaffold

The existing API target is **Isaac Lab v2.3.2 with Isaac Sim 5.1**, as listed in its [compatibility table](https://github.com/isaac-sim/IsaacLab/tree/v2.3.2#isaac-sim-version-dependency). This is the scaffold's target, not a recommendation to install an obsolete runtime. Migration to a current release requires API review and a real import/environment smoke test before changing that claim.

### Articulation and units

| Joint order | Parent → child | Axis | Nominal limit |
|---|---|---|---|
| `left_hip` | body → left_leg | local Y | ±12° |
| `right_hip` | body → right_leg | local Y | ±12° |
| `neck_yaw` | body → head | local Z | ±45° |
| `jaw_pitch` | head → jaw | local Y | 0–12° |

The body is a floating rigid body. CAD axes are X forward, Y left, Z up. Lengths/meshes are millimetres; export converts translations and COM once to metres and uses mesh scale 0.001. Mass is kilograms and inertia is kg·m². Component inertia tensors are combined about link COMs using the parallel-axis theorem. Servo cases belong to the link holding the case. The four separately modeled output shafts belong to their driven links and rotate with the direct spline sockets, which are part of the rotating printed legs, neck carrier and jaw.

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
