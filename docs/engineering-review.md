# Engineering review

**R05 is a CAD prototype.** No physical assembly, electrical load/thermal test, Isaac runtime execution, learned walking policy or hardware gait is reported. The following summarizes the original R05 engineering checks and distinguishes them from checks of the public export.

## Original detailed CAD review

The original 2026-09-11 R05 assembly used detailed purchased-component references. Its nominal mass is 257.28 g and neutral COM is approximately (0.19, 0.57, 57.23) mm in the global CAD frame. Source CAD SHA-256: `4819acd1b9158d1ec77f48f93f5091425a44d6252d6c162664b00be08dc9bd09`. Source assembly JSON SHA-256: `68bd9fd40488ea97935b10021dbdd4c666b5d1f31ce9d6946a4177c1063c7f72`. Public [assembly metadata](../cad/assembly.json) records these original source identities and the publication omissions.

| Original check | Reported result and scope |
|---|---|
| Saved solids | Reopened solids valid. |
| Print/coupon exports | 16 watertight, consistently wound, positive-volume, single-component STL meshes; geometry-only 3MF round trips matched. |
| Static intersections | 47 identified screw/shaft, screw/nut or printed-pilot engagements; no unexplained pairs. |
| Independent motion | No overlaps above 0.05 mm³: hips every 2°, neck every 5°, jaw every 1°. |
| Combined jaw/neck samples | No jaw-print/body-print overlap above 0.05 mm³ at jaw every 2° and yaw every 15°. |
| Rigid insertion | 12 components clear of named bare frames; straight steps 2 mm and stepped mouth/regulator paths at most 1 mm. |
| Neutral wire routes | Three illustrative harness groups checked against rigid geometry and each other, with no unexplained overlap above 0.01 mm³. |
| Access and seam | 0.300 mm nominal body seam; an 8 × 4 mm rear cable probe; four Ø4.2 mm face-screw access envelopes on the loose hood. |

Independent motion excludes illustrative flexible harnesses and four identified servo/shaft-screw engagement pairs. A hip sweep omits the opposite leg. Combined samples cover the printed jaw against body prints only. These are discrete nominal intersection tests, not continuous sweeps, minimum-clearance guarantees, tolerance stacks or physical fit tests. The insertion checks omit neighboring installed components. The loose hood access result does not imply a screwdriver can reach those screws with the head assembled.

## Public export

The public STEP contains project-created printed parts. The native mechanical CAD and viewer also retain project-created hardware approximations, while omitting the detailed Adafruit IMU/PCA9685 and Pololu regulator geometry. The full intended assembly mass remains in metadata, including omitted boards. [Public export checks](../cad/public_export_checks.json) identify the published files and their geometry checks; these do not re-prove the original full-assembly collision review.

Regenerating local full CAD uses [separately downloaded references](../references/README.md) and writes to `build/local/`. Reports created by the [build workflow](build.md) bind their results to the actual local CAD hash. Original reported results must not be relabeled as results for an edited model.

## Before a build or gait claim

Measure the four actual servos and horns, test representative printed pilots, verify every installed component/tool path, finish the harness and battery restraint, and measure current, voltage and temperature under simultaneous motion. Weigh completed links and qualify traction and structural strength. Then verify the Isaac import, contacts and actuator model, train and evaluate policies, and test bounded physical motion. The [hardware worksheet](hardware-measurements.md) and [simulation guide](simulation.md) define those next steps.
