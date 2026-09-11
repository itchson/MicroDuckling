# Browser contact physics and numerical checks

The browser uses Rapier rigid-body integration with gravity, bounded joint motors and Coulomb contact friction. Movement is produced by those forces. Display geometry, collision geometry and CAD-estimated mass/inertia are separate inputs. Robot self-collision remains disabled because the interior body/head/leg envelopes are approximate.

The recommended browser settings are continuous convex sole hulls, a **1/600 s physics step**, **16 solver iterations**, gravity 9.81 m/s², foot friction 0.9, ground friction 0.7, other-part friction 0.35, mass scale 1, allowed penetration error 0.05 mm and prediction distance 0.2 mm. Commands update at 60 Hz. Friction uses the explicit `Min` combination rule, giving effective foot-ground friction `min(0.9, ground friction)`. These material and actuator values are unmeasured priors. Rapier uses Coulomb friction without separate static/dynamic coefficients. [Rapier collider documentation](https://rapier.rs/docs/user_guides/javascript/colliders/)

Each sole hull uses the original public tread mesh vertices converted from assembly millimetres to link-local metres, rounded to 1e-8 m and deduplicated. Rapier constructs one convex hull per tread. This leaves nine robot colliders plus ground; the 109 legacy robot boxes remain available for explicit numerical comparison. Changing collision mode does not add or remove the specified link mass. A faceted convex hull is still an approximation to a continuous curved rubber sole.

## Contact readouts

| Readout | Meaning |
|---|---|
| Mass and weight | Sum of simulated link masses; weight is mass × configured gravity. Uniform mass scaling also scales inertia and leaves local COM positions unchanged. |
| World COM | Mass-weighted live rigid-body centres of mass. |
| Support from momentum balance | Change in total robot linear momentum minus gravity and approximate linear drag, divided by elapsed simulated time. |
| Foot load estimate | Total support allocated according to each sole's share of raw normal contact impulses. This is an estimated split, not an independently measured foot force. |
| Slip | Actual tangential velocity of the body at its contact points relative to stationary ground; foot values are impulse-weighted averages. |
| Contact markers | Last fixed-substep contact locations. These are points, not pressure patches. |

The support calculation compensates the model's 0.01/s linear damping using a trapezoidal approximation. It reports ground support as unavailable when the robot also loads the target obstacle, because total momentum cannot isolate the two supports. Force/slip averages cover the actual fixed substeps executed by the public update call. Contact telemetry is for inspection and evaluation; it is excluded from policy observations.

Rapier 0.20.0 raw per-contact impulses and contact-force events were unsuitable as direct force readouts in these checks. A resting 1 kg box returned `mg × (1 + 1 / solverIterations)` for impulse divided by timestep and for force events: 11.03625 N at eight iterations despite negligible vertical acceleration and 9.81 N weight. Per-point tangential getters returned zero while friction changed motion. The engine preserves raw values for diagnostics, displays tangential force as unavailable, and does not rescale raw impulses to the expected weight. Contact ordering was checked against the installed API and [Rapier's manifold documentation](https://rapier.rs/docs/user_guides/javascript/advanced_collision_detection/); upstream [impulse accumulation source](https://github.com/dimforge/rapier/blob/3e12c2679cb1940a876bde93af9cec0cf2f57944/src/dynamics/solver/contact_constraint/contact_with_coulomb_friction.rs) is linked for investigation. The numerical behavior is a local observation, not an upstream acknowledgement of a defect.

## Recorded numerical evidence

The 11 September 2026 contact audit used a 0.257281 kg CAD model. After two seconds settling and two seconds sampling, support from momentum balance was 2.52387 N against 2.52393 N weight. At half mass it was 1.26153 N against 1.26196 N; at 1.5 times mass it was about 3.7875 N against 3.7859 N. Removing the ground caused free fall. Zero gravity with internal motor commands preserved total COM position within 2 μm.

An independent sliding-box check with rotation locked measured deceleration 3.92404, 6.86703 and 8.82897 m/s² at friction coefficients 0.4, 0.7 and 0.9. These match `coefficient × gravity` within 0.001 m/s². Zero friction preserved horizontal velocity. This verifies that friction changes the dynamics even though the tangential API readout was unavailable.

A fixed diagnostic rocking gait was run for 30 seconds at seed 2026, with 0.002-radian reset perturbations and 60 Hz commands:

| Sole / solver iterations | Travel at 300 Hz | At 600 Hz | At 1,000 Hz |
|---|---:|---:|---:|
| Legacy boxes / 8 | 62.77 mm | 27.64 mm | 21.41 mm |
| Convex / 8 | 22.82 mm | 8.74 mm | 10.33 mm |
| Convex / 16 | 7.45 mm | 8.05 mm | 8.12 mm |

All nine runs stayed upright. The convex/16 setting showed materially better timestep convergence; its late forward speeds were 0.697, 0.662 and 0.609 mm/s respectively. This table checks numerical sensitivity using one fixed diagnostic controller. It is not a hardware validation or a claim about the best controller found by later search.

The recorded hull fixture's SHA-256 is `676452fc96ee216c69a5a8725e577ac93b4c04438c0cc9da98a71ff167152f09`; source CAD hash is `2bfee66a13c8f88110521157c7b271f15e3d4d98a9cedfb0e5e9f0a088842ed5`. These identify the geometry used for this numerical comparison. Subsequent CAD or dynamics changes require new evidence; a matching joint command file alone does not reproduce a changed plant.

## Regeneration

After rebuilding CAD and running `simulation/derive_manifest.py`, derive a separate browser review asset from the matching public tread meshes:

```sh
python simulation/browser/derive_asset.py build/local/cad/manifest.json build/browser-check/robot-physics.json --mesh-dir cad/meshes
python -m unittest discover -s simulation/tests -v
```

When reviewing a separate public CAD export, use `--mesh-dir build/public-check/cad/meshes`. Inspect the output before intentionally replacing `simulation/browser/robot-physics.json`. The generator records source-manifest and tread hashes, retains the complete physical mass/inertia estimate, and embeds `contactModel.recommendedSettings`. Only original Apache-licensed tread vertices are included. Full local link meshes containing vendor geometry remain excluded from the public asset.

Changing friction, mass, timestep, solver settings or contact geometry invalidates previously selected training results. Compare held-out seeds, sustained progress, falls, slip and finer numerical settings before interpreting a simulated controller as robust. Physical motors, printed parts, actual tread material, camera latency and power supply behavior still require measurement.
