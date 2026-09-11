# R07: direct servo sockets and a one-piece face

R07 removes all four servo horn arms from the assembled robot. Female spline sockets are built into `LegFootLeft`, `LegFootRight`, `NeckCarrier` and `Jaw`, so each printed part engages its servo output directly. Four central retaining screws remain. The fixed upper bill is fused into `FacePanel` as one connected printable solid; the separate upper-bill part, locating keys, screws and nuts are removed.

## Direct output interfaces

The geometry is defined by the `DEFAULTS` parameter mapping and construction functions in [direct_mount_r07.py](../src/direct_mount_r07.py); edit measured values there and regenerate the complete model and fit coupon together. Its default profile is an **unverified manufacturing hypothesis**, not a measured interface for every servo sold as MG90S:

| Parameter | Provisional value |
| --- | --- |
| Teeth | 20 |
| Shaft major / root diameter | 4.80 / 4.30 mm |
| Radial socket allowance | 0.06 mm |
| Socket depth | 3.80 mm |
| Nominal shaft/socket axial overlap / tip room | 3.50 / 0.30 mm |
| Nominal hub-to-crown axial gap | 0.50 mm |
| Entry lead-in | 0.35 mm |
| Full-profile overlap after the lead-in | About 3.15 mm |
| Center screw passage | 2.30 mm diameter |
| Screw-head recess | 4.50 mm diameter |

The actual assembly now uses these sockets, rather than deferring the change to an optional coupon. The four servo output shafts are separate hardware records with the corresponding toothed profile. Each belongs to its driven link and rotates with the fitted leg, neck carrier or jaw; the servo case stays on its mounting link. This nominal geometric match does not establish fit to the actual purchased shafts. The incomplete Amazon link did not identify an exact supplier variant. Tooth count, diameters, flank shape, usable shaft height, retaining-screw thread and seating stack need measurement before choosing the final values.

The socket shape is a radial trapezoidal approximation. At 20 teeth and 4.8 mm diameter, circumferential pitch is about 0.754 mm; the modeled 44% tooth-tip fraction is about 0.332 mm before allowances. That is finer than a typical 0.4 mm nozzle's extrusion width. Inspect the slicer's actual tooth paths and qualify the printed result; reducing layer height alone does not improve XY resolution. The [spline experiment](../experiments/spline-mount/README.md) retains a separate optional insert study with a different 30% tip fraction. Those experimental inserts are not extra required robot parts.

Use `SplineFitCoupon` before printing or loading a complete interface. A freely seating coupon can establish a candidate fit but cannot establish cyclic torque capacity. Check backlash, repeat assembly, tooth wear and representative loaded retention. Do not force the socket onto the output using its center screw. If printed teeth prove inadequate, a measured matching metal insert is a possible future revision.

The neck retains its support annulus and nominal 0.20 mm thrust shim. The socket transmits rotation; the seated support stack must carry head weight without preloading the servo output. The jaw retains its separate passive pivot. Mate the mouth servo and jaw before attaching the passive pivot and head frame: the checked withdrawal path moves the servo 4 mm toward negative Y to disengage the socket, then lowers it through the jaw opening; assembly reverses that path. The assembled jaw/servo module also clears the bare head frame on a sampled withdrawal path of 0.5 mm outward and then 40 mm down. Reverse that path to install the module before the passive pin and neck carrier, as described in [assembly](design-and-assembly.md). Measure central-screw engagement and blind-hole depth for each location; old horn screw lengths are not automatically correct for the new grip stacks. The schematic screw shaft lengths are 6.7 mm at each hip, 9 mm at the neck and 7 mm at the jaw. These are modeled envelopes, not qualified purchase lengths or verified screw threads.

## M2 assembly fasteners

Printed-part connections use nominal **M2 screws**, with captive M2 nuts where the existing design supplies nut pockets. The common passing clearance is 2.30 mm diameter; printed pilot holes are commonly 1.70 mm diameter (0.85 mm radius). These pilot holes are intended to be qualified with the chosen 2 mm thread-forming screw and printed material. They are not modeled internal threads, and their fit and repeated-assembly strength require representative-depth samples. The clearance coupon includes alternate passing-hole and pilot sizes for that test.

The body-shell connections retain their captive nuts. Mouth-servo mounting uses the modeled M2 nuts, and the passive jaw pivot retains its M2 locknut. Other connections use the existing printed pilots; no unmodeled nuts or inserts are assumed. Select lengths for the actual grip, head recess and available engagement, following the [hardware worksheet](hardware-measurements.md).

The **four servo-output center screws are the exception**: their actual thread must match the servo manufacturer's output shaft. Their 2 mm CAD envelope does not specify an M2 thread. This distinction does not change the M2 choice for the robot's printed-part assembly connections.

## Integral upper bill

The flat upper mouth is part of `FacePanel`, connected across the face by a fused root. It is not a separately screwed plate. The plate is nominally 50 mm wide and 2.2 mm thick, with clipped front corners that follow the faceted design. The face remains removable from the head using its existing face attachment screws; no new bill attachment hardware is needed.

A single-material face print gives the face and upper bill the same color. Painting the bill or using a suitable multicolor print is optional and does not create another mechanical part. The moving lower jaw remains a separate orange print. Nominal closed upper-to-lower bill clearance is 4.10 mm.

## Checks and simulation

The [R07 CAD record](validation/r07-cad.json) contains the native/export hashes, printable mesh round trips and detailed checks. The updated [simulation record](validation/r07-camera-approach.json) reports 12 successful image-guided approach episodes across six target placements and two seeds. The viewer provides ground target placement, custom swing/lean/pace/phase/timing, friction and camera-search settings; see [simulation controls](simulation.md).

The revised assembly has **14 robot print parts and two coupons**, with **77 assembled records** (75 mechanical and two separate electronics visuals). Complete nominal mass is **248.66 g** and global neutral COM is **(−0.78, 0.72, 58.01) mm**. These estimates include modeled hardware and full-density plastic; they are not measurements of a printed build.

Native interface checks report zero neutral overlap between each direct socket and its matching modeled servo, with all 20 tooth crest/valley samples passing at every output. The nominal 0.06 mm radial profile allowance gives a measured CAD minimum gap of about 0.036 mm normal to the tooth flanks; radial allowance is not the same as surface-normal clearance. These compare the authored mating profiles; they do not establish hardware fit. All 15 sampled nominal assembly paths report zero collisions, including the complete jaw/servo module against the bare head frame. These isolated paths do not establish every installed-neighbor or tool-access sequence. Simulation checks must use the matching regenerated CAD, mass properties and asset hashes. Historical [R06 evidence](r06-simplified-design.md) remains available but does not establish results for R07. Nominal solid, clearance and mesh checks do not qualify the physical spline fit, tooth strength, screw retention or powered operation.

Stable `MicroDuckling_R05_*` CAD download filenames remain for existing links; the source revision and manifest identify the actual R07 geometry. See [assembly](design-and-assembly.md), [measurement worksheet](hardware-measurements.md), [simulation](simulation.md) and the unchanged [direct PWM/shared supply wiring](electronics.md).
