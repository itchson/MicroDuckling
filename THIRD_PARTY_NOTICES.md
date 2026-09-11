# Third-party notices

MicroDuckling is an independent hobby project inspired by [Microduck](https://pollen-robotics.com/microduck/) from Pollen Robotics, the robotics team at Hugging Face. It is not affiliated with or endorsed by either organization. The four-servo mechanism and printed parts are specific to MicroDuckling.

The [Microduck runtime](https://github.com/pollen-robotics/microduck) and [training repository](https://github.com/pollen-robotics/microduck_rl) were studied as references. Their software is distributed under Apache-2.0. This repository does not distribute their runtime, policies or official mechanical meshes. Pollen's [press kit](https://pollen-robotics.com/microduck/press-kit/) explains the scope of its open-source release.

## Included UI components

`viewer/components/ui/button.tsx`, `viewer/components/ui/checkbox.tsx`, `viewer/components/ui/slider.tsx` and `viewer/lib/utils.ts` are adapted from [shadcn/ui](https://github.com/shadcn-ui/ui), Copyright (c) 2023 shadcn. They retain the MIT license in [licenses/shadcn-ui-MIT.txt](licenses/shadcn-ui-MIT.txt). The repository's Apache license does not replace that notice. Changes integrate the components into the MicroDuckling viewer and its styling.

React, Three.js, Base UI, Lucide, Tailwind CSS and other installed dependencies retain their respective licenses. The package manifests and lockfile identify the dependency versions; their packages supply the applicable notices.

The browser physics module uses `@dimforge/rapier3d-compat` 0.20.0, the official JavaScript/WebAssembly bindings for [Rapier](https://github.com/dimforge/rapier). The installed package and [upstream license](https://github.com/dimforge/rapier/blob/master/LICENSE) identify Apache-2.0. It is installed through npm, not copied into this repository as vendored source. Preserve applicable dependency notices when distributing built viewer bundles.

## Included electronics visuals and renders

`components/meshes/IMU.json` adapts **Adafruit LSM6DS3TR-C 6-DoF Accel + Gyro IMU - STEMMA QT / Qwiic PCB**; the historical PCA9685 adaptation was removed from the active R06 build. The original IMU design is by **Limor Fried/Ladyada for Adafruit Industries** and the IMU mesh adaptation retains **CC-BY-SA-3.0**. MicroDuckling contributors converted Eagle outlines, holes, pads and package positions to colored 3D meshes, added approximate heights and fitted connectors, and placed the boards in the assembly. These are not manufacturer mechanical CAD.

Source titles, URLs, board hashes, mesh hashes and changes are recorded in [components/NOTICE.json](components/NOTICE.json). The complete upstream notices are included without replacing their hardware-specific terms:

- [LSM6DS3TR-C README](components/licenses/adafruit-lsm6ds3/README.md), [CC hardware license](components/licenses/adafruit-lsm6ds3/license.txt), and [additional upstream MIT notice](components/licenses/adafruit-lsm6ds3/LICENSE).
- [PCA9685 README](components/licenses/adafruit-pca9685/README.md) and [CC hardware license](components/licenses/adafruit-pca9685/license.txt).

`components/meshes/Buck_0.json` is an **Apache-2.0 original visual approximation by MicroDuckling contributors** of the Pololu D24V50F5. The D24V10F5 visual was removed in R06. Published dimensions and photographs informed generic geometry. No manufacturer STEP, prior regulator mesh, photograph, drawing image, logo or silkscreen is included. Product names identify represented hardware and do not imply endorsement or a license over that hardware.

Electronics-inclusive assembled/exploded renders and their derivative thumbnails are released as composite artwork under [CC-BY-SA-3.0](https://creativecommons.org/licenses/by-sa/3.0/). Attribution: **MicroDuckling contributors — robot design, mesh adaptations and rendering; Limor Fried/Ladyada for Adafruit Industries — original IMU PCB design (historical R05 images also incorporated the PCA9685 design)**, with source details in the component notice above. Keep this attribution and license with redistributed images. See [render provenance](assets/renders/render_provenance.json) for asset inputs. The separately identified [AI-generated mascot](assets/brand/PROVENANCE.md) and independent mechanical source remain under the project's Apache-2.0 terms.

## Downloaded component references

The CAD source can load the following manufacturer files for local engineering review. The original downloaded inputs remain outside the public repository; the separately licensed Adafruit adaptations are included as described above. Pololu STEP-derived meshes remain excluded. The project's Apache license does not replace upstream terms.

| Component | Source | Terms and attribution |
|---|---|---|
| Adafruit PCA9685 product 815, rev C PCB | [Official Eagle repository](https://github.com/adafruit/Adafruit-16-Channel-PWM-Servo-Driver-PCB) | Hardware README selects CC-BY-SA 3.0; designed by Limor Fried/Ladyada for Adafruit Industries. |
| Adafruit LSM6DS3TR-C product 4503 PCB | [Official Eagle repository](https://github.com/adafruit/Adafruit-LSM6DS3TR-C-PCB) | Hardware README selects CC-BY-SA 3.0; the repository also contains an MIT license file. Both notices are fetched. |
| Pololu D24V50F5 | [Manufacturer resources](https://www.pololu.com/product/2851/resources) | Manufacturer STEP model. No redistribution permission is claimed here. |
| Pololu D24V10F5 | [Manufacturer resources](https://www.pololu.com/product/2831/resources) | Manufacturer family STEP model. No redistribution permission is claimed here. |
| Ai-Thinker ESP32-CAM | [Manufacturer datasheet mirrored by LCSC](https://datasheet.lcsc.com/lcsc/Ai-Thinker-ESP32-CAM-C277946.pdf) | Nominal dimensions inform a project-created approximate representation; the PDF and its illustrations are not distributed here. |
| ESP32-CAM pin mapping | [Espressif camera example](https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h) | Reference link; the complete example header is not included. |

The [input manifest](references/inputs.json) records download URLs, SHA-256 hashes and upstream notice files. The fetch script also saves notices alongside each local input. Preserve complete upstream READMEs, licenses, creator attribution and change descriptions when redistributing the Adafruit adaptations. Their inclusion in the viewer does not change the license of the separate printed-part exports.

FreeCAD, NumPy, trimesh, Isaac Lab, Isaac Sim and their dependencies are installed separately. Isaac Lab v2.3.2 uses [BSD-3-Clause](https://github.com/isaac-sim/IsaacLab/blob/v2.3.2/LICENSE). The simulation scaffold uses its APIs and invokes its installed training scripts; it does not bundle those packages.

The offline geometric-camera tests use [three-mesh-bvh](https://github.com/gkjohnson/three-mesh-bvh), copyright 2018 Garrett Johnson, under its MIT license. It is installed as a development dependency with its upstream license; no library source is copied into this repository.
