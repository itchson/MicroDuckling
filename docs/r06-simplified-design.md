# R06: upper bill and simpler electronics

Historical revision. R07 replaces the separate upper bill with an integral face feature and replaces horn attachments with direct spline sockets. See [R07 changes](r07-direct-mount-design.md) for the current build. The dimensions, part counts and simulation evidence below describe R06 only.

R06 adds a fixed upper bill and adopts direct ESP32-CAM servo signals with one shared 5 V regulator. The robot still has four MG90S joints. The PCA9685, its four screws, its front frame/posts and the separate logic regulator cradle have been removed. The battery and IMU stay low in the body; the ESP32-CAM, flex camera and mouth servo stay in the head.

## Upper bill

The orange plate is a separate printable part, 50 mm wide, projecting from X = 30.2 to 40 mm, with a 2.2 mm flat section. Two locating keys register it against the face, with 0.15 mm nominal clearance. Two front-access M2×8 screws engage captive rear M2 nuts. The modified face has the matching slots and reinforced nut pockets.

Install the nuts and upper bill while the face/hood module is accessible, before closing the head. The lower jaw retains its driven cheek and passive pivot. Native solid checks sampled jaw opening from 0° to 12° in 1° increments: the minimum upper-to-lower bill clearance is 4.10 mm closed and increases as the jaw opens. Neck yaw from −45° to +45° was checked in 15° increments for the new parts. These are nominal geometry checks, not a physical fit certificate.

## Power and control

See [electronics and GPIO allocation](electronics.md), [BOM](bom.md) and [power research](parts-research.md). One regulated supply branches to the servo power bus and the ESP32-CAM's 5 V input, with a common ground. The existing D24V50F5 remains the dimensioned regulator reference. A cheaper substitute needs its actual dimensions, mounting arrangement and load/thermal behavior checked.

The CAD harness is still an illustrative route with a mass allowance. It does not model every signal branch, connector, capacitor, fuse or strain-relief detail. Direct PWM source is an integration component; the complete hardware application and powered tests remain unfinished.

## Direct spline experiment

The [configurable spline experiment](../experiments/spline-mount/README.md) prepares a replaceable keyed insert and small fit coupons. The supplied servo link has not established a specific spline variant. The illustrative tooth profile is not a verified MG90S interface, so the assembled model retains its existing horn attachments until that fit is established.

## Simulation and exports

The browser uses continuous tread hulls, 600 Hz integration and 16 solver iterations. Foot-load estimates, slip, loaded contact markers and the centre of mass are visible. Camera training evaluates actual travel and a stable stopping zone; looking at the target alone earns no approach reward. See [the simulation guide](simulation.md) for evidence and limitations.

There are 15 robot print parts plus two assembly fit coupons, 88 assembled mechanical records and two separately licensed component visuals. Stable `MicroDuckling_R05_*` download filenames are retained for existing links; the R06 manifest and source parameters identify that historical revision.

The complete nominal mass is **247.96 g**, with global COM **(−0.67, 0.76, 58.19) mm**. The [frozen CAD review](validation/r06-cad.json) records source/export hashes and check counts. The [six camera-approach traces](validation/r06-camera-approach.json) use the R06 mass/inertia and R06 CAD camera meshes: all six reach the stopping zone in 7.77–9.47 simulated seconds, with no falls. These are model results, not hardware measurements.
