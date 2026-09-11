# Assembly and fit development

R08 is a four-servo prototype with two rigid leg/rocker-foot prints, a faceted torso, neck yaw, an independent face and a shell-mounted upper-mouth base and a moving lower jaw. Physical assembly, printed strength and powered operation remain unverified. Start with the [measurement worksheet](hardware-measurements.md) and [BOM](bom.md).

## Datums and motion

Coordinates are X forward, Y left, Z up, in millimetres. Hip axes are at global Z = 38 mm; the neck pivot is at Z = 80 mm. Nominal joint travel is hips ±12°, neck ±45°, jaw 0–12°. These are modeled ranges, not calibrated servo endpoints. Check the direct socket seating and sweep the printed parts with the complete cable/connector envelopes.

The torso is 76 × 78 × 37 mm. The head is 52 mm wide across the face, 64 mm deep and 52 mm high. The shared 5 V regulator, IMU and battery sit in the torso; ESP32-CAM, the separate flex camera and mouth servo occupy the head. The nominal assembly envelope is 76 × 112 × 136 mm.

## Assembly fasteners

Use nominal M2 screws for the printed-part connections. Where nut pockets are modeled, fit the corresponding captive M2 nuts; the passive jaw pivot uses its M2 locknut. The remaining printed pilots need qualification with the selected 2 mm thread-forming fastener. Common CAD holes are 2.30 mm passing clearance and 1.70 mm pilot diameter (0.85 mm radius). Check the actual print, screw type, engagement depth and repeated-assembly strength before accepting these dimensions. Do not assume every connection has a nut pocket.

The four center screws retaining the direct servo sockets must match the actual servo output threads. Their nominal 2 mm visual diameter is not an M2 thread specification. See [fastener measurements](hardware-measurements.md) for the different locations and grip stacks.

## Provisional assembly order

1. Measure all servo output splines and retaining screws. Print the clearance and spline coupons; the default 20T/4.8 mm major/4.30 mm root profile is provisional. Qualify the selected fasteners in representative-depth pilots.
2. Fit the bare chassis and torso servo cases. Install the vertical D24V50F5 before the battery, IMU and removable neck support obstruct its inside-facing screws. Its modeled insertion lowers from above, then seats 2 mm forward.
3. Wire the single regulator to separate servo and camera power branches with common ground; follow the [electronics allocation](electronics.md). The PCA9685 and second regulator are absent in R08.
4. Thread the restraint tape through the chassis slots before adding the insulating pad and battery. Qualify its overlap and release path without fastening directly to the pouch. Fit the body IMU and check screw-tip clearance.
5. Seat the leg and neck carrier sockets directly on the matching servo splines. Retain them with the matching central screws, checking actual grip, seating and blind-hole depth. Check the neck support, actual thrust shim and carrier stack for weight support without preload. There are no horn arms or horn-to-print screws.
6. Prepare the loose hood before fitting the face or electronics. Load its two upper-mouth M2 nuts through the open front, seat the separate upper-mouth base on its hood registers and install its two flush M2×8 countersunk screws from below while the jaw is absent. The base has no attachment to the face. Fit the face independently: its four M2 screws enter from the rear, so their straight access paths require the hood to remain off the populated head frame. See [R08 mount geometry and nut loading](r08-upper-mouth-design.md).
7. Preassemble the mouth servo with the jaw while the head frame and passive pivot are absent. Raise the servo through the central jaw opening, then move it 4 mm along its shaft axis into the jaw socket. Seat the center retaining screw with the required engagement. The checked reverse path withdraws the servo 4 mm toward negative Y before lowering it through the jaw. Raise the complete jaw/servo module into the bare head frame, then seat it 0.5 mm inward along the shaft axis. This reverses the checked module withdrawal path of 0.5 mm outward followed by 40 mm down. Keep the passive pivot and neck carrier off until the module is seated. Fit the vertical ESP32-CAM, removable clamp and camera cradle once access permits.
8. After installing the preassembled jaw/servo module, fit the passive pivot, retaining free motion and nominal endplay. Do not assume the rigid one-piece jaw can be slid sideways onto an already installed mouth servo and passive pivot. Connect the head to the neck, route the actual loom and align the camera without stressing its flex. Check full combined travel before fitting the prepared hood/face/upper-mouth module and body shells.

This sequence reflects sampled nominal insertion paths. Those checks compare components to named bare frames; they do not prove every installed-neighbor, nut or screwdriver path. Use the actual hardware to confirm the sequence.

## Printing and materials

Public STLs and 3MFs use millimetres. The 3MFs contain geometry only. Choose printer-specific orientation and supports; qualify thin walls, leg layer strength, small pilots and the curved sole finish. The source uses 1.3 mm torso walls, approximately 1.2 mm hood walls, 3.6 mm leg uprights and 2.2 mm foot material. CAD plastic mass assumes solid material at 1.24 g/cm³, so sliced and weighed masses will differ.

Tread, restraint tape and the insulating pad are separate material envelopes. Their material, adhesion, compression, friction and retention need tests. Do not scale purchased geometry to make a print fit; update the relevant dimensions and regenerate.

See [R08 changes](r08-upper-mouth-design.md), the historical [R05 refinement](r05-assembly-refinement.md), [engineering review](engineering-review.md) and [simulation](simulation.md) for evidence and remaining work.
