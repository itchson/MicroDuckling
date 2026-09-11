# Bill of materials and sourcing

An exploratory build using generic boards is roughly **A$90–120 in parts**, before shipping, charger and tools, at the prices checked on **11 September 2026**. This is a proposed cheaper electrical layout, not a purchase bundle that fits the current CAD. The R05 reference below uses more expensive Adafruit and Pololu boards. Match exact PCB revisions and connector configurations before relying on any mount.

## Budget alternative to investigate

All amounts are Australian dollars. These are advertised single-order prices or explicitly labelled allowances, not measured hardware performance. Stock and checkout totals can change.

| Qty | Proposed component | Line cost | Price evidence and limitation |
|---:|---|---:|---|
| 4 | Positional MG90S-type servos, horns and screws | A$15–20 | [Australian seller's four-pack](https://www.ebay.com.au/itm/166481674710), A$14.99 when checked. Generic batch; do not assume genuine TowerPro specifications or use continuous-rotation variants. |
| 1 | ESP32-CAM and camera | A$16–30 | [Zaitronics kit](https://zaitronics.com.au/products/esp32-cam-camera-mb-motherboard-usb-c-version-development-board), A$16.25 including programmer, specifies **OV3660** and 5–10 day dispatch lead time; availability display is mixed. [Phipps OV2640 board](https://www.phippselectronics.com/product/esp32-cam-wifi-bluethooth-development-board-with-ov2640-camera-module/), A$29.95. Camera flex, lens and mount differ. |
| 1 | Generic PCA9685 board | A$8.99 | [Tempero Systems](https://temperosystems.com.au/products/pca9685-16-channel-12-bit-pwm-servo-driver-i2c-interface/). Same controller family does not imply Adafruit hole spacing or terminal placement. |
| 1 | 2S 450 mAh LiPo pack | A$16.95 | [Aus Electronics Direct PB4174](https://www.auselectronicsdirect.com.au/7.4v-450mah-lipo-2s-battery-pack-with-jst-connecto). Listed **56 × 30 × 10 mm**; this does **not** match the current 43 × 23 × 13 mm tray reference. |
| 1 | Shared 5 V switching regulator candidate | A$16.80 | [DFRobot DFR0753 at Core](https://core-electronics.com.au/dc-dc-buck-converter-6-14v-to-5v-8a.html), specified input 6–14 V. The advertised 8 A is not a verified sustained rating inside this robot. |
| 1 | Six-axis IMU for balance control | A$4.60 | [Core MPU-6050 module](https://core-electronics.com.au/mpu-6050-module-3-axis-gyroscope-acce-lerometer.html). Different mount and sensor driver from the selected Adafruit board; sampling and calibration need validation. |
| — | Fasteners, wire, connectors, disconnect, capacitor, insulation, pad/tread material | A$8–15 | Planning allowance for quantities used, assuming workshop supplies; buying complete assortments costs more. |
| — | Printed parts and fit coupons | A$3–5 | Material allowance with an existing printer; excludes failed prints and commercial printing. |

Rounded total: **A$90–120**, including the IMU. This requires checking replacement dimensions, revising mounts and testing power delivery. Keeping A$20 servos, an A$30 camera and an A$5 PCA9685 deal gives **A$93.35 before consumables and printing** after adding the quoted battery, regulator and IMU. A complete A$80 build has not been verified.

Charging equipment is separate. A [SkyRC B6neo at FPVFaster](https://www.fpvfaster.com.au/products/skyrc-b6-neo-smart-charger-200w-dc-pd-dual-input?variant=42251956486226) was listed around **A$52–62**, depending on variant, plus a compatible PD/DC supply and battery leads if not already owned. The [manufacturer](https://www.skyrc.com/b6neo-series) specifies adjustable current and 2S support. Set current to the pack manufacturer's limit. An inexpensive fixed-current charger is not automatically suitable for a 450 mAh pack. Allow separately for a 3.3 V logic USB-to-UART programmer when the camera purchase does not include one.

See [parts and power research](parts-research.md) for the electrical trade-offs and the cost of the existing branded selection.

## Current R05 CAD reference parts

| Qty | Component | Source / qualification |
|---:|---|---|
| 4 | MG90S micro servos with matching stock horns and center screws | [TowerPro reference](https://towerpro.com.tw/product/mg90s-3/); cases, crowns, horns and performance vary between sellers/batches. Measure all four. |
| 1 | Ai-Thinker ESP32-CAM with ordinary OV2640 flex camera | [Ai-Thinker datasheet](https://datasheet.lcsc.com/lcsc/Ai-Thinker-ESP32-CAM-C277946.pdf); actual camera carrier, lens and flex require measurement. |
| 1 | Adafruit PCA9685, product 815, rev C | [Product](https://www.adafruit.com/product/815); generic PCA9685 boards are not dimensionally interchangeable. |
| 1 | Adafruit LSM6DS3TR-C IMU, product 4503 | [Product](https://www.adafruit.com/product/4503); mounted rigidly to the torso. |
| 1 | Pololu D24V50F5 regulator, product 2851 | [Product](https://www.pololu.com/product/2851); selected 5 V servo rail, subject to current/thermal testing. |
| 1 | Pololu D24V10F5 regulator, product 2831 | [Product](https://www.pololu.com/product/2831); selected 5 V logic rail. |
| 1 | Gens ace GEA4502S60XT3, 2S 450 mAh pack | [Manufacturer](https://gensace.de/products/gea4502s60xt3); nominal packaging reference 43 × 23 × 13 mm and 28 g. Verify delivered pack and connectors. |
| — | Stock horns, small screws/nuts, nominal 0.20 mm thrust shim | Exact threads, lengths, engagement and shim stack need qualification; see the worksheet. |
| — | Wires, connectors, disconnect, insulation, restraint tape, pad and tread material | Routes are only envelopes. Complete the loom, retention and fault shutdown design before powered assembly. |
| 14 + 2 | Printed robot parts and fit coupons | `cad/stl/` and `cad/coupons/`; geometry-only 3MFs in `cad/3mf/`. |
| — | Compatible balance charger, USB-to-UART programmer and test equipment | Charger must match the delivered pack's permitted current and connectors; UART signals must be 3.3 V. |

## Dimensional reference

| Board | Nominal outline, mm | Mounting reference |
|---|---|---|
| PCA9685 rev C | 62.23 × 25.4 | Four Ø2.5 mm holes, 55.88 × 19.05 mm pattern from Eagle. |
| Adafruit 4503 | 25.4 × 17.78 | Two Ø2.5 mm mounting holes, 20.32 mm apart; lower corner pads are electrical. |
| D24V50F5 | 17.78 × 20.32 | Two diagonal Ø2.18 mm mounts; components exist on both sides. |
| D24V10F5 | 12.7 × 17.78 | No mounting holes; insulating edge cradle and retention remain to qualify. |
| ESP32-CAM | 27 × 40.5 in datasheet text; drawing says 40 long | Header rows 22.86 mm apart at 2.54 mm pitch; no dedicated mounting holes. |

Adafruit Eagle files establish XY geometry, not populated component heights. The Pololu STEP files omit soldered leads and optional headers. The ESP32-CAM component envelopes and lens alignment are approximate. See [reference inputs](../references/README.md) and record actual results in [hardware measurements](hardware-measurements.md).

## Electrical architecture under development

The 2S pack feeds both regulators. Their positive outputs stay separate; grounds are common. The servo regulator supplies PCA9685 **V+** and all servos. The logic regulator supplies ESP32-CAM **5V**; PCA9685 **VCC** uses 3.3 V logic. The proposed external I²C bus is GPIO13/14 with microSD disabled; camera wiring remains on its dedicated pins.

This is a proposed allocation, not supplied firmware. GPIO12 is a boot strapping pin, and ESP32 ADC2 use conflicts with Wi-Fi. Battery monitoring, undervoltage behavior, a watchdog and a hardware fail-disable path remain unfinished. PCA9685 can retain its previous PWM output when the MCU stalls. Do not treat a software timeout or regulator current headline as tested fault protection. Test supply transients and temperatures with the selected servos, leads and enclosure before powered motion.
