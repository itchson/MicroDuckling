# Start here

MicroDuckling is an engineering prototype. The public files support inspection, modification and fit experiments; they are not a tested assembly kit. Browser walking and camera approach are model experiments; a working hardware application and Isaac-trained policy are not supplied.

1. Read the [engineering review](engineering-review.md) and [R08 changes](r08-upper-mouth-design.md).
2. Inspect the printed parts in `cad/stl/`, the coupons in `cad/coupons/`, and the geometry-only files in `cad/3mf/`. The 3MF files have no printer profiles.
3. Select the exact parts in the [BOM](bom.md) and fill out the [measurement worksheet](hardware-measurements.md). Start with the coupons before printing the whole robot.
4. Follow [build and validation](build.md) to regenerate local CAD or run the numerical tests.
5. Use [simulation](simulation.md) for the planned Isaac workflow and its current limits.

All CAD dimensions are millimetres. Four MG90S servos drive left hip pitch, right hip pitch, neck yaw and the jaw. The planned controller is an ESP32-CAM using four direct GPIO servo signals, one shared 5 V regulator and a body-mounted IMU. See the [pin and power allocation](electronics.md). Battery monitoring, fault shutdown and firmware still need implementation and tests.
