# Direct servo wiring

The current electrical plan removes the PCA9685. The ESP32-CAM generates four servo control signals, and one regulated **5 V supply** powers the camera board and all four MG90S servos. Keep the body-mounted six-axis IMU. This is a concrete wiring and firmware bring-up plan; simultaneous camera, servo, reset and power behavior still need bench qualification.

This allocation is for the **classic Ai-Thinker ESP32-CAM with OV2640 and PSRAM**, using the exposed headers, with microSD empty and disabled. Other boards sold as “ESP32 camera” need their own schematic check.

## Signal connections

| Function | ESP32-CAM header | Connection |
| --- | --- | --- |
| Left hip servo signal | IO2 | High-speed LEDC channel 0 |
| Right hip servo signal | IO13 | High-speed LEDC channel 1 |
| Neck yaw servo signal | IO14 | High-speed LEDC channel 2 |
| Jaw servo signal | IO15 | High-speed LEDC channel 3 |
| IMU SDA | U0R / GPIO3 | Through removable signal link J1 |
| IMU SCL | U0T / GPIO1 | Through removable signal link J2 |
| IMU VIN | 3V3 | For the selected Adafruit LSM6DS3TR-C breakout |
| IMU and servo grounds | GND | Common with regulator and camera board |
| All four servo positive leads | Shared 5 V bus | Do not route motor current through a GPIO or the ESP32-CAM PCB |
| ESP32-CAM supply | 5V | Separate branch from the same regulator |

The [Ai-Thinker schematic](https://docs.ai-thinker.com/_media/esp32/docs/esp32_cam_sch.pdf) shows these GPIOs on the headers and microSD wiring. GPIO4 also controls the onboard white flash LED, so this allocation leaves it unused. GPIO16 is connected to **PSRAM chip select**, and GPIO17 to its clock; neither is a spare servo or IMU pin. GPIO12 stays unused because its reset level selects the flash supply voltage. The [ESP32 GPIO documentation](https://docs.espressif.com/projects/esp-idf/en/v5.5.2/esp32/api-reference/peripherals/gpio.html) identifies these peripheral and reset restrictions.

Add a **10 kΩ pull-down to ground on GPIO2 and GPIO15**, near the ESP32-CAM. These are proposed external bias values to verify on the actual board, including its microSD pull-ups. Check both reset levels with the chosen servo batch connected. Servo signal inputs must tolerate 3.3 V commands and must not drive the ESP32 pin above its supply. TowerPro's published MG90S page does not establish a universal input threshold for all units sold under that name; verify the purchased batch. A signal buffer may be necessary if it fails that check, without adding a separate PWM controller.

## Reset and programming

GPIO2 must be low or floating for UART download when GPIO0 is held low; normal flash boot ignores GPIO2. GPIO15 low suppresses ROM boot messages on GPIO1, which becomes IMU SCL. GPIO12 high at reset can select a 1.8 V flash supply and prevent a 3.3 V board from booting; this plan never connects a peripheral to it. These behaviors are documented in [Espressif's boot-mode guide](https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/boot-mode-selection.html) and the [ESP32 datasheet, boot configuration tables](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf).

Use two removable links, one for each IMU signal. For programming:

1. Turn off robot power and isolate the servo 5 V branch. Open J1 and J2 so the programmer cannot contend with the IMU.
2. Connect a **3.3 V logic** USB-UART adapter: adapter TX → U0R/GPIO3, adapter RX → U0T/GPIO1, and common ground. Keep one intended 5 V source; do not parallel the adapter's power output with the regulator.
3. Hold GPIO0 to ground while resetting or powering the ESP32-CAM into download mode. GPIO2 must remain low. Flash the application.
4. Power off, remove the GPIO0-to-ground link and programmer signal leads, then close J1/J2. Restart with servo power still isolated and check camera/IMU initialization before enabling the servo branch.

Runtime UART logging and console input are unavailable with the IMU connected. Set `CONFIG_ESP_CONSOLE_NONE=y` and `CONFIG_BOOTLOADER_LOG_LEVEL_NONE=y`; do not add later `Serial`, UART, console or panic-output configuration that drives GPIO1/3. GPIO15's pull-down addresses the earlier ROM output that firmware settings cannot suppress. [ESP-IDF console configuration](https://docs.espressif.com/projects/esp-idf/en/v5.5.2/esp32/api-reference/kconfig.html#config-esp-console-uart) describes this distinction. A USB programmer base must also be electrically disconnected from the reused pins during normal operation.

## Camera, PWM and I²C allocation

The existing camera signals stay unchanged: XCLK0; SCCB SDA26/SCL27; D0–D7 on 5/18/19/21/36/39/34/35; VSYNC25, HREF23, PCLK22, PWDN32, no reset GPIO. This matches [Espressif's Ai-Thinker camera pin map](https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h).

Use **ESP-IDF 5.4/5.5**, with `esp32-camera` **2.1.6** pinned for this bring-up component:

| Peripheral | Explicit resource |
| --- | --- |
| Camera XCLK | Low-speed LEDC timer 0, channel 0; 20 MHz |
| Four servos | High-speed LEDC timer 0, channels 0–3; 50 Hz, 16-bit duty |
| Camera SCCB | I²C controller 0 on GPIO26/27 |
| Body IMU | I²C controller 1 on GPIO3/1; start at 100 kHz |

The two LEDC banks are independent on classic ESP32. Espressif's pinned [camera clock implementation](https://github.com/espressif/esp32-camera/blob/v2.1.6/target/xclk.c) explicitly selects `LEDC_LOW_SPEED_MODE`; the servo component explicitly selects `LEDC_HIGH_SPEED_MODE`. Do not let an automatic Arduino PWM allocator reassign the camera timer. [LEDC documentation](https://docs.espressif.com/projects/esp-idf/en/v5.5.2/esp32/api-reference/peripherals/ledc.html) describes the separate modes and timer/channel configuration.

**Camera SCCB defaults to I²C1 in this camera release.** Override it with `CONFIG_SCCB_HARDWARE_I2C_PORT0=y`; merely changing IMU pins would leave a bus conflict. Select `CONFIG_SCCB_HARDWARE_I2C_DRIVER_NEW=y` and use the new I²C API for the IMU too. The camera's [Kconfig](https://github.com/espressif/esp32-camera/blob/v2.1.6/Kconfig) and [build selection](https://github.com/espressif/esp32-camera/blob/v2.1.6/CMakeLists.txt) establish these defaults and the IDF 5.4 driver transition.

For the selected Adafruit board, use 3.3 V at VIN and retain its I²C pull-ups to that logic supply. Do not pull the ESP32 signals to 5 V. The [Adafruit pinout](https://learn.adafruit.com/adafruit-lsm6ds3tr-c-6-dof-accel-gyro-imu/pinouts) gives the default address, power and pull-up details. Poll the sensor initially; no extra interrupt GPIO is allocated. A different IMU breakout needs its own power, address and driver check. Manual supported poses can omit the IMU, but the planned balance policy requires angular velocity and gravity-direction observations.

## One shared 5 V supply

```text
2S battery → switch/protection → one 5 V buck regulator
                               ├─ servo power bus → four servo + leads
                               └─ separate camera branch → ESP32-CAM 5V
ESP32-CAM 3V3 → IMU VIN
All returns → common ground, with short separate servo/camera power paths
```

The existing regulator candidate, current assumptions and decoupling proposal are in the [BOM](bom.md) and [power research](parts-research.md). A second external logic regulator is not required by this plan. The ESP32-CAM still uses its onboard 3.3 V regulator. Keep servo return current out of the camera's ground wiring, and measure voltage at both branch endpoints during simultaneous servo loading and Wi-Fi capture. A larger capacitor does not establish current capacity or guarantee brownout-free operation.

## Bring-up status

The [firmware I/O component](../firmware/README.md) supplies explicit pin/timer setup, zero-duty startup, calibrated angle-to-pulse conversion and limits. It requires measured servo direction, neutral and pulse limits; there is no generic calibration or automatic walking application.

Before installed motion, verify reset/download behavior, all four 50 Hz signals alongside camera XCLK, PSRAM frame capture, IMU reads, and servo input voltage. Then test a supported robot with constrained motion, measure loaded 5 V transients and regulator temperature, and exercise command timeout, reset and physical servo-power isolation. These checks remain outstanding on hardware. Removing the PCA9685 does not by itself make a stalled program safe: the ESP32 LEDC hardware can keep producing its last commanded pulses.
