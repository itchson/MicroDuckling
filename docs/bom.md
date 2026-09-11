# Bill of materials and sourcing

The revised electrical layout uses **one shared 5 V regulator**, four MG90S servos and an ESP32-CAM issuing the servo signals directly. **PCA9685 and the second logic regulator are excluded from the purchase list.** The 2S battery and an IMU remain. The retained regulator geometry is Buck_0, based on Pololu D24V50F5; a cheaper regulator needs a measured mount and a loaded supply test.

Using the project's **A$20 estimate for four servos** and **A$30 estimate for the camera**, the proposed build is about **A$100–110 with the budget regulator candidate**. Keeping the dimensioned Pololu regulator makes the same budget about **A$120–142**. These totals include a battery, budget IMU, consumed hardware and print material, and exclude shipping, charger and tools. They do not price the exact branded IMU or guarantee that alternative parts fit the CAD.

## Revised budget

Australian prices checked **11 September 2026**; project estimates and material allowances are labelled separately.

| Qty | Part | Line cost | Basis / limitation |
|---:|---|---:|---|
| 4 | Positional MG90S-type servos, horns and screws | A$20 | Project estimate for all four. Measure the actual cases, horns and peak current. |
| 1 | ESP32-CAM with OV2640 camera | A$30 | Project estimate; [Phipps OV2640 board](https://www.phippselectronics.com/product/esp32-cam-wifi-bluethooth-development-board-with-ov2640-camera-module/) was A$29.95. |
| 1 | 2S 450 mAh LiPo candidate | A$16.95 | [Aus Electronics Direct PB4174](https://www.auselectronicsdirect.com.au/7.4v-450mah-lipo-2s-battery-pack-with-jst-connecto), **56 × 30 × 10 mm**. It does not match the existing 43 × 23 × 13 mm tray reference; connector/current suitability also needs checking. |
| 1 | Shared 5 V regulator candidate, DFRobot DFR0753 | A$16.80 | [Core Electronics](https://core-electronics.com.au/dc-dc-buck-converter-6-14v-to-5v-8a.html). Advertised 6–14 V input, up to 8 A output. A cost candidate, not a qualified replacement for the Pololu mount or a verified enclosed 8 A supply. |
| 1 | MPU-6050 IMU candidate | A$4.60 | [Core Electronics](https://core-electronics.com.au/mpu-6050-module-3-axis-gyroscope-acce-lerometer.html). Different mount and driver from the Adafruit reference. |
| — | Fasteners, wire, connectors, disconnect/fuse, capacitors, insulation and tread material | A$8–15 | Allowance for quantities consumed from workshop supplies. Buying complete assortments costs more. |
| — | Printed robot parts and fit coupons | A$3–5 | Material allowance with an existing printer; excludes failures and commercial printing. |

Electronics subtotal: **A$88.35**. With consumed hardware and printing: **A$99.35–108.35**, rounded to A$100–110. No PWM-driver board or second buck converter is counted.

For the retained **Pololu D24V50F5**, replace the A$16.80 candidate line with [Robot Gear's A$37.95](https://www.robotgear.com.au/Product.aspx/Details/1003-5V-5A-Pololu-Step-Down-Voltage-Regulator-D24V50F5) or [Core's A$49.95](https://core-electronics.com.au/pololu-5v-5a-step-down-voltage-regulator-d24v50f5.html). This adds A$21.15–33.15, giving **A$120.50–141.50** with the other assumptions unchanged. It is a geometry reference, not a requirement to buy the more expensive shop's board.

Lower advertised alternatives can reduce the planning total toward **A$80–110**: the earlier [four-servo offer](https://www.ebay.com.au/itm/166481674710) was A$14.99 and the [Zaitronics camera/programmer kit](https://zaitronics.com.au/products/esp32-cam-camera-mb-motherboard-usb-c-version-development-board) is A$16.25. The latter specifies **OV3660**, with a different camera and dispatch lead time. This lower range requires additional selection and fit work.

Charging equipment is separate. A [SkyRC B6neo at FPVFaster](https://www.fpvfaster.com.au/products/skyrc-b6-neo-smart-charger-200w-dc-pd-dual-input?variant=42251956486226) was around **A$52–62**, plus a compatible PD/DC supply and leads if needed. The [manufacturer](https://www.skyrc.com/b6neo-series) lists adjustable charging current and 2S support. Match the delivered pack's charge limit and connectors. Also allow for a 3.3 V logic USB-to-UART programmer when the camera purchase does not include one.

## Retained dimensional references

| Qty | Reference component | CAD / qualification |
|---:|---|---|
| 4 | MG90S with matching horns and centre screws | [TowerPro reference](https://towerpro.com.tw/product/mg90s-3/). Measure all four actual servos. |
| 1 | Ai-Thinker ESP32-CAM with ordinary OV2640 flex camera | [Manufacturer V1.0 datasheet, mirrored](https://wiki.diustou.com/cn/w/upload/b/be/Esp32-cam_product_specification_zh.pdf). Nominal board 27 × 40.5 mm; drawing says 40 mm long. Header rows are 22.86 mm apart at 2.54 mm pitch; no dedicated mounting holes. |
| 1 | Adafruit LSM6DS3TR-C IMU, product 4503 | [Product](https://www.adafruit.com/product/4503). 25.4 × 17.78 mm, two Ø2.5 mm mounts 20.32 mm apart. The A$4.60 MPU-6050 allowance does not buy this exact board. |
| 1 | Pololu D24V50F5, product 2851, Buck_0 | [Manufacturer](https://www.pololu.com/product/2851/specs). 17.78 × 20.32 mm, two diagonal Ø2.18 mm mounts; populated on both sides. Retained reference for the shared 5 V rail. |
| 1 | Gens ace GEA4502S60XT3, 2S 450 mAh | [Manufacturer](https://gensace.de/products/gea4502s60xt3). Existing packaging reference 43 × 23 × 13 mm and 28 g. Confirm delivered pack and connector dimensions. |
| — | Horns, small screws/nuts and nominal 0.20 mm thrust shim | Threads, engagement and shim stack require measurement; see [hardware worksheet](hardware-measurements.md). |
| 15 + 2 | Printed parts and fit coupons | cad/stl/, cad/coupons/ and geometry-only cad/3mf/. |

The Adafruit PCA9685 and Pololu D24V10F5 are superseded R05 references, not parts to purchase for the revised direct-PWM/shared-supply layout. The revised CAD omits both; historical reports may retain their names.

The electrical connection and pin allocation are documented separately in [electronics](electronics.md). See [parts and power research](parts-research.md) for current budgeting, thermal/dropout limits and proposed distribution capacitors. Record delivered dimensions and powered results in [hardware measurements](hardware-measurements.md).
