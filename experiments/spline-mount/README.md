# Direct output-shaft mount preparation

Use a replaceable keyed spline insert so the leg, neck carrier and lower bill can attach directly at the servo output without a projecting horn arm. For load-bearing hips, the preferred eventual insert is a **confirmed matching metal female spline** captured in a printed carrier. A directly printed micro-spline is a useful fit experiment; this sample has no verified cyclic-torque rating and should not yet replace the hip interface in the canonical design. Keep the four-servo arrangement, neck thrust support and jaw's passive pivot.

## What is known about the servo

- TowerPro's current [MG90S page](https://towerpro.com.tw/product/mg90s-3/) lists a 22.8×12.2×28.5 mm body and 1.8 kgf·cm stall torque at 4.8 V. It does not specify the output spline dimensions and notes shaft/gear material changes. The model name alone is not a dimensional interface drawing.
- [Adafruit technical support](https://forums.adafruit.com/viewtopic.php?t=95879) identified its 2016 MG90S as 20 teeth with 4.8 mm outer diameter. Its [current product 1143](https://www.adafruit.com/product/1143) is an MG90D, also listed as 20 splines; it was revised in 2018. This does not verify another supplier's MG90S.
- A different seller's own [MG90S listing](https://createlabz.store/products/micro-servo-motor-mg905-metal-gear-180-degrees) specifies 21T/4.86 mm. This is evidence of conflicting supplier interfaces, not a verified match to the user's unit.
- The supplied Amazon URL lacks a product ASIN, so it has not established the actual variant. No purchase or nominal fit choice has been made from it.

The example's root diameter, tooth flank shape, engagement depth and screw clearance are explicitly illustrative. An exact socket requires tooth count, major diameter, minor/root diameter, usable tooth height, tooth-tip/root widths or a square-on macro image with scale, shaft shoulder/crown clearance, and the retaining screw's measured diameter/pitch/head/available engagement. Also measure the actual seated supplied horn's axial stack and inspect several servos from the pack for consistency.

## Current CAD interfaces

These are authored nominal CAD dimensions, not measurements of hardware:

| Interface | Current model | Direct-mount integration proposal |
| --- | --- | --- |
| Servo output | Smooth Ø4.8×4 mm cylinder in `servo_y`; no teeth; Ø8.5×2.4 mm illustrative horn hub | Replace the abstract fit assumption with a measured insert; retain the servo case and joint-axis datums |
| Hips | Ø10 mm central leg clearance, 3.6 mm upright, open radial arm slots; inner leg face at global Y±42.6 mm after widening | A local reinforced boss with keyed insert pocket; fill the old arm slots, preserve foot and pivot positions, extend the boss inward only by the measured shaft-to-leg stack |
| Neck | Ø12 mm central carrier passage, underside horn screw positions at 7 and 11 mm radius, separate thrust shoulder/shim | Keyed central insert carrier; retain thrust shoulder/shim so the spline does not become the head's axial bearing |
| Lower bill | 3 mm driven cheek with Ø4.6 mm center opening and arm screws at 7 and 11 mm radius; separate passive pivot | Locally reinforced keyed socket at the existing pivot; retain passive support and remove arm-only holes after fit validation |

Source: public `src/build_cad.py` (`servo_y`, `horn_y`, leg and neck blocks) and `src/head_r04.py` (jaw attachment). The current horn and shaft stack is explicitly assumed. A direct mount must not be sized by simply subtracting the old horn thickness.

Proposed replaceable insert: nominal 9 mm across-flats hex exterior, about 3.7 mm axial height, and a central through screw. A matching printed carrier pocket starts at 9.2 mm across flats for a coupon test, with at least 2 mm of surrounding material and a positive axial shoulder. The hex transfers torque; the central screw provides retention. A metal insert's **actual** outer profile, flange and screw access replace these illustrative dimensions. Do not substitute a common 25T standard-size servo insert for an unverified 20T/21T micro spline.

## Printable experiment

Run [build_coupon.py](build_coupon.py) with FreeCAD's Python. `--config measured-spline.json` accepts the same keys as `illustrative-20t.json`. It creates five socket cups with radial allowances 0/0.03/0.06/0.09/0.12 mm, identified by 1–5 through-dots on a side tab, plus one plain hex insert. All six STLs, a combined STEP and an editable native FCStd stay under the ignored `build/spline-fit/` directory and are clearly named `UNVERIFIED_*`. The radial tooth profile is an original trapezoidal approximation, not an involute or a claimed vendor spline standard.

Print the socket opening upward so its axis is vertical and the fine tooth shape lies in XY. The example 20T/4.8 mm diameter gives 0.754 mm circumferential pitch; its 30% tip fraction is about 0.226 mm. That feature is smaller than a typical 0.4 mm nozzle's 0.45 mm extrusion width. This is a geometric comparison and a reason to inspect the slicer preview and use finer XY capability; reducing layer height alone does not solve it. [Prusa's design guide](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135), [layer-height guidance](https://help.prusa3d.com/article/layers-and-perimeters_1748)

At a 2.3 mm effective radius,0.09 N·m torque corresponds to about 39 N tangential force, and the manufacturer's 1.8 kgf·cm stall figure converts to about 0.177 N·m or 77 N. These are simple force estimates, not a tooth stress calculation or a rated continuous operating load. Unequal tooth contact, wear, layer orientation and the small retention stack make a matched metal insert the more prudent starting point for repeated hip loading. Coupon fit alone does not prove strength.

First confirm tooth count and profile, then check gentle seating and backlash with the servo unpowered. Do not use the retaining screw to force a mismatched socket onto the shaft. Evaluate torque retention separately with a representative insert/carrier assembly and loads below the measured safe operating limit; a brief fit check cannot establish a fatigue rating.

Validation completed: all six exported meshes are closed; all native parts are single valid solids and reopen correctly. A 21-tooth/4.86 mm algorithm variation also builds, and four invalid parameter combinations are rejected. No physical fit or torque test has been performed. The assembly still uses its existing horn interfaces. This experiment prepares a measured replacement; it does not claim a socket that fits the unknown servo batch.
