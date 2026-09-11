# Parts and power research

The [BOM](bom.md) separates the exact R05 CAD parts from a proposed cheaper build. Australian shop prices checked on **11 September 2026** suggest roughly **A$90–120** for the generic alternative, excluding postage, charging equipment and tools. This is a planning estimate that needs mount revisions and electrical testing.

## Why the old estimate was high

At Core Electronics, the selected [Adafruit PCA9685](https://core-electronics.com.au/adafruit-16-channel-12-bit-pwm-servo-driver-i2c-interface-pca9685.html) was A$26.80, the [Pololu D24V50F5](https://core-electronics.com.au/pololu-5v-5a-step-down-voltage-regulator-d24v50f5.html) A$49.95 and the [Pololu D24V10F5](https://core-electronics.com.au/pololu-5v-1a-step-down-voltage-regulator-d24v10f5.html) A$21.40, including GST. Those **three boards alone total A$98.15**. Another Australian shop listed the [same 5 A Pololu board](https://www.robotgear.com.au/Product.aspx/Details/1003-5V-5A-Pololu-Step-Down-Voltage-Regulator-D24V50F5) at A$37.95, illustrating the effect of supplier choice.

These are the documented reference boards used to establish CAD geometry. Their prices are not the minimum cost of a four-servo robot. A generic PCA9685 and one suitable shared regulator could reduce this portion to about **A$25.79** using the BOM's quotes. That is an architecture proposal, not an already qualified replacement.

## What the regulator does

A standard 2S LiPo is about **7.4 V nominal and 8.4 V fully charged**. The proposed servo and camera supply is regulated **5 V**. A buck converter reduces the battery voltage; neither the PCA9685 nor the ESP32 GPIO outputs supply the servo motors' operating power. The [TowerPro MG90S reference](https://towerpro.com.tw/product/mg90s-3/) describes a low-voltage servo, and the [Ai-Thinker ESP32-CAM specification](https://datasheet.lcsc.com/lcsc/Ai-Thinker-ESP32-CAM-C277946.pdf) identifies the board's 5 V supply. Connect neither directly to a fully charged 2S pack.

R05 uses two regulators so the servo and logic positive rails are separate, with common ground. A cheaper proposal uses **one appropriately sized 5 V regulator**, with separate branches to the servo power bus and camera, common ground, short power returns and local decoupling. The [DFR0753 candidate](https://core-electronics.com.au/dc-dc-buck-converter-6-14v-to-5v-8a.html) specifies 6–14 V input and 5 V output. Its 8 A headline does not establish thermal performance, dropout margin, connector capacity or transient response in this enclosure. Measure simultaneous servo loading and camera Wi-Fi operation across the usable battery range. If that supply causes camera brownouts or unacceptable noise, revise distribution/filtering or retain a separate logic regulator.

Very cheap adjustable modules are available, but voltage headroom matters. For example, Core's [A$2.40 XL4015 module](https://core-electronics.com.au/dc-dc-adjustable-step-down-module-5a-75w.html) asks for 3 V of input-to-output headroom for reliable current limiting. It has not been selected as a verified 5 V supply throughout a 2S discharge. No regulator current label substitutes for testing this robot's real servo batch.

## Sixteen channels, two bus signals

The PCA9685 has **16 PWM output channels**, not a requirement for 16 ESP32 control pins. Four channels command the four servos; the ESP32 communicates with the controller over SDA and SCL. The IMU can share that I²C bus when addresses and electrical levels are compatible. [NXP's PCA9685 datasheet](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf) describes the independent PWM outputs and I²C interface.

Use 3.3 V for PCA9685 logic **VCC** and I²C pull-ups with the ESP32; servo **V+** is the separate 5 V power connection on the breakout. Check a generic board's actual pull-ups and connections. The current proposed GPIO13/14 bus allocation assumes microSD is disabled; camera, boot and programming pins still constrain the pin assignment. This repository does not yet supply working hardware firmware.

## When the IMU is needed

For manual servo poses on a supported robot, the controller can issue angles without an IMU. Balancing needs body-motion feedback. The current [simulation policy contract](simulation.md) explicitly consumes angular velocity and estimated gravity direction, so removing the IMU would remove required observations; it is not an equivalent build for that policy. A six-axis module combines three gyroscope axes and three accelerometer axes. The [A$4.60 MPU-6050 module](https://core-electronics.com.au/mpu-6050-module-3-axis-gyroscope-acce-lerometer.html) is a budget candidate, subject to a rigid mount, calibration, filtering and a suitable driver. It does not provide actual MG90S joint-angle feedback.

## What coordinated leg motion can do

Both leg joints rotate about the same model +Y axis; see the primary [joint export source](../simulation/derive_manifest.py) and [CAD generator](../src/build_cad.py). Coordinated pitch can change torso inclination relative to supported feet, producing a bow-like motion. In a free robot, floor contact, foot rolling, mass distribution and balance determine whether the body tilts, moves or falls. A pose preview alone does not demonstrate a stable bow.

The current mechanical joint envelope is **−12° to +12° per hip**, not the servo's advertised full rotation. Stay within that envelope until revised geometry, collision checks and physical measurements justify an extension. Independent neck yaw and jaw motion do not add a torso pitch joint.

Record actual batch dimensions and electrical results in [hardware measurements](hardware-measurements.md). The [reference input guide](../references/README.md) covers the hashed vendor CAD inputs used for the existing mounts. Nominal vendor data, shop current ratings and simulation parameters remain distinct from physical test results.
