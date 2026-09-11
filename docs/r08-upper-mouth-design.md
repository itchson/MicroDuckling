# R08: an upper mouth mounted beneath the head hood

R08 introduces `UpperMouthBase`, a separate printable upper mouth that mounts beneath the front of `HeadHood` with M2 fasteners. Its lip follows the lower jaw. The upper mouth is no longer fused to `FacePanel` and does not fasten to it; the face remains an independent removable part.

The four direct servo sockets, rotating output-shaft records, neck thrust support and passive jaw pivot remain. Their default 20T/4.80 mm major/4.30 mm root spline profile is still unverified against the actual servo batch. Use the spline fit coupon and [hardware worksheet](hardware-measurements.md) before accepting physical fit or load capacity. The [R07 record](r07-direct-mount-design.md) documents the introduction and parameters of these retained interfaces.

The part and shell mounts are authored in [upper_mouth_r08.py](../src/upper_mouth_r08.py). Regenerate the hood and upper-mouth base together after changing their interface parameters.

## Geometry and shell mounting

| Feature | Nominal CAD value |
| --- | --- |
| Upper lip front / width | X = 36 mm / 54 mm, aligned with the lower jaw |
| Plate thickness and vertical extent | 2 mm, Z = 82.9–84.9 mm |
| Closed upper-to-lower lip gap | 1.0 mm |
| Upper-mouth base to face clearance | 0.8 mm |
| Two locating-register centers | X = 18 mm, Y = ±22 mm |
| Register radius / height | 2.6 / 1.2 mm |
| Socket radial / end allowance | 0.15 / 0.20 mm |
| Nut-bearing web above register socket | 1.2 mm |

The rear central relief clears the camera and head frame. The locating registers seat into the hood bosses and carry alignment loads. Two M2×8 countersunk screws enter from below and engage captive M2 nuts in the hood. Their modeled Ø4 mm heads use a 90° cone over 1 mm plus a 0.2 mm rim, with 1.3 mm hex drives and matching recessed seats. The heads sit flush with the upper-mouth underside. Both countersunk seats have nominal cone contact, and straight 1.3 mm across-flats hex-driver access was checked from below against the loose hood, base and screws. That access check excludes the jaw, face, electronics and body, so complete the fastening before those parts obstruct the tool. These are modeled screw envelopes; delivered head and nut dimensions need checking.

## Assembly

Load the two M2 nuts through the open front of the loose hood **before fitting the face panel or electronics**. The sampled withdrawal route lifts each nut 3 mm, moves it 8 mm toward the center and then 30 mm forward; reverse that route to load the pockets. Seat the upper-mouth base on its registers and tighten the two screws while the jaw is absent and the underside is accessible. Fit the independent face panel afterwards. The upper-mouth base stays attached to the hood when the face is removed. With its screws removed, the base has a sampled 0–40 mm straight downward withdrawal path from the loose hood and independently from the face; these checks exclude the jaw and populated internal assembly.

Printed-part connections retain nominal M2 fasteners; vendor-specific servo center screws must match the actual output threads. See [assembly](design-and-assembly.md) for the retained jaw/servo sequence and [fastener measurements](hardware-measurements.md) for pilot and grip qualification.

## Fastener reference

The countersunk mounting geometry uses a 90° head reference. [Bossard's countersunk screw description](https://www.bossard.com/au-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-flat-countersunk-head-screws-fully-threaded/p/2105/) identifies that included angle. Its [supplier dimensional sheet](https://xonstorage.z8.web.core.windows.net/pdf/bossard_1021729_sup11manufacturerlinknew.pdf) lists an M2 variant with maximum 4 mm head diameter, 1.2 mm head height and a 1.3 mm hex drive. The sheet also says M2 is not included in DIN 7991, so these are supplier-reference dimensions, not a universal M2 head specification. Check the delivered screw head, drive access, nut fit and printed countersink before assembly.

## Validation scope

The assembly contains **15 robot print parts and two fit coupons**, with **82 assembled records** (80 mechanical and two separately supplied electronics visuals). Complete nominal mass is **250.34 g**, with global neutral COM **(−0.66, 0.72, 58.18) mm**. These are CAD estimates, not measured build values.

Jaw clearance was sampled every 1° through 0–12° opening: the minimum upper-to-lower mouth gap is **1.0 mm** at closure and increases to approximately **7.74 mm** at the open limit. The [R08 CAD record](validation/r08-cad.json) identifies the frozen native model and exported geometry. All native solids are valid, 19 sampled insertion paths report no collisions, and the sampled joint-motion and combined jaw/neck checks report no interference. Static review contains 37 nominal material engagements; the two new pairs are upper-mouth screw/nut thread contacts. Direct-socket, mouth, driver-access, harness and display checks pass. These checks are scoped to the modeled parts and sampled paths.

The [R08 camera-approach record](validation/r08-camera-approach.json) reports **12 successful episodes with no falls**, covering six target placements and reset seeds 2026 and 42, including an initially out-of-view target. Completion took **8.55–46.77 simulated seconds**. The evaluator verifies source and canonical/cached mesh hashes before testing the CAD-occluded synthetic camera. The 62 viewer/simulation tests, TypeScript/Vite build and 27 Python tests also pass. These finite cases do not establish success for every placement, custom gait, surface or load.

R07 geometry and learning traces remain historical, and training was not rerun for R08. Geometric clearances do not establish printed fit, fastener retention, spline wear, power stability or physical walking. NVIDIA Isaac Sim / Isaac Lab runtime and hardware transfer remain development work.

The [shared 5 V supply and direct ESP32-CAM signals](electronics.md), [parts budget](bom.md) and component-license boundaries are unchanged. Stable `MicroDuckling_R05_*` download filenames remain for existing links; inspect the manifest revision for the actual design.
