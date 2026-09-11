# Third-party notices

MicroDuckling is an independent hobby project inspired by [Microduck](https://pollen-robotics.com/microduck/) from Pollen Robotics, the robotics team at Hugging Face. It is not affiliated with or endorsed by either organization. The four-servo mechanism and printed parts are specific to MicroDuckling.

The [Microduck runtime](https://github.com/pollen-robotics/microduck) and [training repository](https://github.com/pollen-robotics/microduck_rl) were studied as references. Their software is distributed under Apache-2.0. This repository does not distribute their runtime, policies or official mechanical meshes. Pollen's [press kit](https://pollen-robotics.com/microduck/press-kit/) explains the scope of its open-source release.

## Included UI components

`viewer/components/ui/button.tsx`, `viewer/components/ui/checkbox.tsx`, `viewer/components/ui/slider.tsx` and `viewer/lib/utils.ts` are adapted from [shadcn/ui](https://github.com/shadcn-ui/ui), Copyright (c) 2023 shadcn. They retain the MIT license in [licenses/shadcn-ui-MIT.txt](licenses/shadcn-ui-MIT.txt). The repository's Apache license does not replace that notice. Changes integrate the components into the MicroDuckling viewer and its styling.

React, Three.js, Base UI, Lucide, Tailwind CSS and other installed dependencies retain their respective licenses. The package manifests and lockfile identify the dependency versions; their packages supply the applicable notices.

## Downloaded component references

The CAD source can load the following manufacturer files for local engineering review. Those inputs and their detailed derived geometry are not included in the public repository. Their licenses are not replaced by MicroDuckling's Apache license.

| Component | Source | Terms and attribution |
|---|---|---|
| Adafruit PCA9685 product 815, rev C PCB | [Official Eagle repository](https://github.com/adafruit/Adafruit-16-Channel-PWM-Servo-Driver-PCB) | Hardware README selects CC-BY-SA 3.0; designed by Limor Fried/Ladyada for Adafruit Industries. |
| Adafruit LSM6DS3TR-C product 4503 PCB | [Official Eagle repository](https://github.com/adafruit/Adafruit-LSM6DS3TR-C-PCB) | Hardware README selects CC-BY-SA 3.0; the repository also contains an MIT license file. Both notices are fetched. |
| Pololu D24V50F5 | [Manufacturer resources](https://www.pololu.com/product/2851/resources) | Manufacturer STEP model. No redistribution permission is claimed here. |
| Pololu D24V10F5 | [Manufacturer resources](https://www.pololu.com/product/2831/resources) | Manufacturer family STEP model. No redistribution permission is claimed here. |
| Ai-Thinker ESP32-CAM | [Manufacturer datasheet mirrored by LCSC](https://datasheet.lcsc.com/lcsc/Ai-Thinker-ESP32-CAM-C277946.pdf) | Nominal dimensions inform a project-created approximate representation; the PDF and its illustrations are not distributed here. |
| ESP32-CAM pin mapping | [Espressif camera example](https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h) | Reference link; the complete example header is not included. |

The [input manifest](references/inputs.json) records download URLs, SHA-256 hashes and upstream notice files. The fetch script saves notices alongside each downloaded input. Adafruit's board-derived representations preserve the hardware license: extracting XY features, adding approximate heights and applying rigid placement do not make them solely Apache-licensed. Preserve complete upstream READMEs, licenses, creator attribution and change descriptions when redistributing those assets.

FreeCAD, NumPy, trimesh, Isaac Lab, Isaac Sim and their dependencies are installed separately. Isaac Lab v2.3.2 uses [BSD-3-Clause](https://github.com/isaac-sim/IsaacLab/blob/v2.3.2/LICENSE). The simulation scaffold uses its APIs and invokes its installed training scripts; it does not bundle those packages.
