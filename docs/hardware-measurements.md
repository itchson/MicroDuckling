# Hardware measurement worksheet

**No physical measurements are recorded yet.** Leave result cells blank until measured. CAD values below are hypotheses. Label servos **L**, **R**, **N**, **M** for left/right hip, neck and mouth; keep each servo's supplied center screw identified with its servo. Stock horns can serve as measurement references but are not installed in R07.

| Identification | Record |
|---|---|
| Date, operator, source revision | |
| Supplier, SKU, PCB revision, batch and photographs | |
| Caliper resolution and zero check; scale resolution | |
| Printer, material, orientation, layer height | |
| Power supply/pack, instruments and test conditions | |

Use millimetres and grams. For servos define **A** as the flat base opposite the shaft, **B** as the short case end nearest the shaft, and **C** as a marked long side. Heights run from A toward the shaft. Distinguish the rectangular case, mounting ears, fixed crown, spline and fully seated direct socket. Measure unpowered external geometry; do not force an unknown screw or open the gearcase to identify it.

## Servo geometry

| Measurement | CAD assumption, not measured | L | R | N | M |
|---|---:|---|---|---|---|
| Case length × width | 22.8 × 12.4 | | | | |
| A to rectangular case top / highest fixed crown | 25.8 / 28.5 | | | | |
| A to spline tip | 32.5 | | | | |
| Shaft center from B / C | 6.2 / 6.2 | | | | |
| Ear outer span / selected hole pitch | 32.1 / 27.7 | | | | |
| A to ear underside / ear thickness | 18.5 / 2.8 | | | | |
| Hole/slot diameter and actual center coordinates | Ø2.2 modeled | | | | |
| Both crown lobes: outline, offsets and heights | approximate | | | | |
| Lead exit, cable size and plugged connector envelope | unknown | | | | |
| Installed mass, including stated lead length | 13.4 g | | | | |

Hole pitch is not the ear's total span. Locate shaft centers from measured tangents and shaft radii consistently. Photograph the crown and output spline beside a scale in the same plane; include a square-on macro view for tooth counting.

## Direct spline, screw and thrust stack

The actual printed leg, neck carrier and jaw sockets now use a configurable 20T profile with 4.8 mm major and 4.30 mm root diameters. **These are unverified assumptions, not a measured MG90S standard.** Use the spline coupon before printing or loading a complete interface. Record several servos from the same pack; the model name does not establish interchangeable output shafts.

| Measurement | L | R | N | M |
|---|---|---|---|---|
| Tooth count, major diameter and root diameter | | | | |
| Tooth tip/root widths and flank shape; macro photograph reference | | | | |
| Usable spline height and shoulder/crown outline | | | | |
| Socket's actual printed allowance and seated depth | | | | |
| A to seated socket outer face and screw-head top | | | | |
| Center screw diameter/pitch, under-head length and usable engagement | | | | |
| Backlash, axial play, radial rocking and full sweep clearance | | | | |
| Repeat assembly and representative load/wear result | | | | |

Do not use the retaining screw to force an incorrect tooth profile onto the shaft. Confirm the socket seats on its intended shoulder and does not bottom on the shaft tip; check screw engagement and blind depth separately. For the neck, record support top → actual thrust shim → carrier shoulder and verify support without axial preload. The nominal shim is 0.20 mm; a gap alone does not carry weight. See [R07 interface parameters](r07-direct-mount-design.md) and the [spline experiment](../experiments/spline-mount/README.md).

| Fastener location | Nominal intent | Actual thread / head / length | Grip stack / engagement / tip clearance | Result |
|---|---|---|---|---|
| Hip ears | 4 × M2×6, printed pilots | | | |
| Mouth ears | 2 × M2×8 with nuts | | | |
| Passive jaw pivot | M2×12 with locknut; 0.2 mm nominal endplay | | | |
| Servo regulator / IMU mounts | M2×6 | | | |
| Camera clamp / cradle | M2×6 | | | |
| Hood, face, shells and neck attachments | M2; check source length and pilot or captive-nut location | | | |
| Four direct-socket center retaining screws | Vendor-specific thread; 2 mm CAD envelope is not an M2 specification | | | |

Printed-part assembly fasteners are nominal M2. Common CAD passing holes are Ø2.30 mm, and common printed pilots are Ø1.70 mm (0.85 mm radius). Qualify the pilots with the selected 2 mm thread-forming fastener, printer and material; record cracking, stripping and repeated assembly in a representative-depth sample. The clearance coupon supplies Ø2.1/2.2/2.3/2.4 mm passing holes and Ø1.6/1.7/1.8 mm pilot trials. Captive M2 nuts apply only at modeled pockets; retain the passive jaw pivot's M2 locknut. No nut is assumed behind a plain printed pilot.

Nominal cylindrical CAD screws do not model threads. The four servo-output center screws are vendor-specific despite their 2 mm visual envelope; measure their thread rather than substituting an M2 screw by appearance. For a straight stack, engagement is under-head length minus unthreaded grip length; include washers, recesses and gaps. Verify blind depth and tip clearance. The thin clearance coupon checks diameters, not thread retention: use a representative-depth pilot sample for stripping, cracking and repeated assembly tests.

## Electronics, camera and battery

| Component | Actual outline / thickness | Top and bottom fitted envelope, including plugs | Retention / clearance | Installed mass |
|---|---|---|---|---|
| Adafruit LSM6DS3TR-C 4503 | | | | |
| Pololu D24V50F5 | | | | |
| ESP32-CAM and fitted headers | | | | |
| OV2640 carrier, lens and flex | | | | |
| 2S pack, discharge and balance plugs | | | | |

Use the [BOM](bom.md) only as a reference column. Measure camera carrier size, lens projection/optical center, flex width/length/orientation, latch access and usable cradle adjustment. The provisional camera carrier and barrel are 10 mm and 8 mm envelopes. Do not load the ribbon to achieve lens alignment.

## Assembly and electrical qualification

| Check | Observation / measurement | Status |
|---|---|---|
| Servo saddles seat on ears without distorting cases; direct sockets fully seat | | |
| Full direct-socket and printed-part sweeps: hips ±12°, neck ±45°, jaw 0–12° | | |
| All screw, nut, driver and component insertion paths in assembly order | | |
| Loose hood/face module closes; face screws accessible with module removed | | |
| Board insulation, solder projections and release space for every plug | | |
| Battery pad and restraint fit; pack removable without pulling leads | | |
| Rear access, wire gauge, connectors, strain relief and neck service loop | | |
| Camera flex stays clear throughout actual head/jaw motion | | |
| Each servo neutral, sign and safe pulse/angle endpoints | | |
| Loaded lag, backlash, current, rail voltage and temperature over time | | |
| Simultaneous servo movement with camera/Wi-Fi and shell closed | | |
| Battery monitoring, undervoltage response, watchdog and power shutdown | | |
| Weighed link masses/COM estimates, printed strength and tread friction | | |

Keep timestamped raw measurements and conditions. Stall torque is not a continuous loaded rating. Start powered tests with reduced motion and support for the mechanism; this worksheet does not qualify a finished robot. See [assembly](design-and-assembly.md) and [simulation calibration](simulation.md).
