# Assembly and fit development

R06 is a four-servo prototype with two rigid leg/rocker-foot prints, a faceted torso, neck yaw, a fixed upper bill and a moving lower jaw. Physical assembly, printed strength and powered operation remain unverified. Start with the [measurement worksheet](hardware-measurements.md) and [BOM](bom.md).

## Datums and motion

Coordinates are X forward, Y left, Z up, in millimetres. Hip axes are at global Z = 38 mm; the neck pivot is at Z = 80 mm. Nominal joint travel is hips ±12°, neck ±45°, jaw 0–12°. These are modeled ranges, not calibrated servo endpoints. Always sweep the actual stock horns and complete cable/connector envelopes.

The torso is 76 × 78 × 37 mm. The head is 52 mm wide across the face, 64 mm deep and 52 mm high. The shared 5 V regulator, IMU and battery sit in the torso; ESP32-CAM, the separate flex camera and mouth servo occupy the head. The nominal assembly envelope is 76 × 112 × 136 mm.

## Provisional assembly order

1. Measure all servos and horns, print the clearance and horn coupons, and qualify the selected fasteners in representative-depth pilots.
2. Fit the bare chassis and torso servo cases. Install the vertical D24V50F5 before the battery, IMU and removable neck support obstruct its inside-facing screws. Its modeled insertion lowers from above, then seats 2 mm forward.
3. Wire the single regulator to separate servo and camera power branches with common ground; follow the [electronics allocation](electronics.md). The PCA9685 and second regulator are absent in R06.
4. Thread the restraint tape through the chassis slots before adding the insulating pad and battery. Qualify its overlap and release path without fastening directly to the pouch. Fit the body IMU and check screw-tip clearance.
5. Seat the stock hip and neck horns. Check the neck support, actual thrust shim and carrier stack for weight support without preload. Attach the legs without consuming the stock center screw's required grip.
6. Install the mouth servo into the bare head frame from below before attaching the neck carrier. The modeled path raises it, then seats it 0.5 mm inward. Fit the vertical ESP32-CAM, removable clamp and camera cradle.
7. Assemble the loose hood and face as a removable module. Fit the upper bill locating keys, captive M2 nuts and two M2×8 screws while the face is accessible. Four face screws enter from the rear; their straight access paths require the hood to be off the populated head frame. Align and retain the camera without stressing its flex.
8. Fit the jaw drive and passive pivot, retaining free motion and nominal endplay. Connect the head to the neck, route the actual loom and check the full combined travel before fitting the shells.

This sequence reflects sampled nominal insertion paths. Those checks compare components to named bare frames; they do not prove every installed-neighbor, nut or screwdriver path. Use the actual hardware to confirm the sequence.

## Printing and materials

Public STLs and 3MFs use millimetres. The 3MFs contain geometry only. Choose printer-specific orientation and supports; qualify thin walls, leg layer strength, small pilots and the curved sole finish. The source uses 1.3 mm torso walls, approximately 1.2 mm hood walls, 3.6 mm leg uprights and 2.2 mm foot material. CAD plastic mass assumes solid material at 1.24 g/cm³, so sliced and weighed masses will differ.

Tread, restraint tape and the insulating pad are separate material envelopes. Their material, adhesion, compression, friction and retention need tests. Do not scale purchased geometry to make a print fit; update the relevant dimensions and regenerate.

See [R06 changes](r06-simplified-design.md), the historical [R05 refinement](r05-assembly-refinement.md), [engineering review](engineering-review.md) and [simulation](simulation.md) for evidence and remaining work.
