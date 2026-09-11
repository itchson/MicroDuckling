# Bill of materials and sourcing

This is the R05 component selection, not a tested purchase bundle. Match exact PCB revisions and connector configurations before relying on a mount. Prices and stock vary and are deliberately omitted.

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
