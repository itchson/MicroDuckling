# MicroDuckling electronics visuals

Four independently addressable viewer assets restore the complete electronics view while keeping the mechanical CAD export separate. Coordinates are the existing MicroDuckling R05 assembly coordinates in millimetres. Keep each mesh with its record, attribution and applicable license.

| Mesh | Representation | License |
| --- | --- | --- |
| `meshes/IMU.json` | Adafruit LSM6DS3TR-C board adapted from Eagle geometry; generic component heights and connectors | CC-BY-SA-3.0 |
| `meshes/ServoController.json` | Adafruit PCA9685 rev C board adapted from Eagle geometry; fitted header banks and generic component envelopes | CC-BY-SA-3.0 |
| `meshes/Buck_0.json` | Original dimension-based visual approximation of the Pololu D24V50F5 | Apache-2.0 |
| `meshes/Buck_1.json` | Original dimension-based visual approximation of the Pololu D24V10F5 | Apache-2.0 |

The Adafruit board designs are by **Limor Fried/Ladyada for Adafruit Industries**. The original work titles, source URLs, board hashes, changes and mesh hashes are in `NOTICE.json`. These colored 3D mesh adaptations were prepared by MicroDuckling contributors. Eagle outlines, holes, pads and package positions were converted into 3D geometry; generic Z dimensions, connector bodies and fitted headers were added; each board was placed rigidly in the robot assembly. They are not manufacturer mechanical CAD.

The complete upstream notices are preserved without modification:

- [Adafruit LSM6DS3TR-C original README](licenses/adafruit-lsm6ds3/README.md), [hardware license](licenses/adafruit-lsm6ds3/license.txt), and [additional upstream MIT notice](licenses/adafruit-lsm6ds3/LICENSE).
- [Adafruit PCA9685 original README](licenses/adafruit-pca9685/README.md) and [hardware license](licenses/adafruit-pca9685/license.txt).

The hardware READMEs and `license.txt` select [Creative Commons Attribution-ShareAlike 3.0 Unported](https://creativecommons.org/licenses/by-sa/3.0/); the Adafruit mesh adaptations are distributed on that basis. Preserve their attribution, change descriptions and license when redistributing them. This package does not treat the additional LSM6 MIT file as a replacement for its hardware-specific CC notice. The remaining independent files use the supplied [Apache 2.0 license](licenses/Apache-2.0.txt). Product names identify represented hardware; they do not imply endorsement.

The two Pololu representations were authored from boxes, cylinders, chamfered polygons and holes. Their generator never opens manufacturer STEP files or prior regulator meshes. It uses published board dimensions and recognizable component classes/arrangement from manufacturer photos. No manufacturer drawing image, photograph, circuit trace artwork, logo or silkscreen is included in these meshes.

- D24V50F5 board dimensions and mechanical holes use the millimetre/mil callouts in the [manufacturer dimensional drawing](https://www.pololu.com/file/0J1436/d24v50f5-step-down-voltage-regulator-dimensions.pdf). The [product photos](https://www.pololu.com/product/2851/pictures) informed the approximate inductor, capacitor and underside IC arrangement. Component XY positions and package details are approximate.
- D24V10F5 uses the published 0.5 × 0.7 inch board dimensions and nominal 0.14 inch overall height from the [manufacturer specifications](https://www.pololu.com/product/2831/specs). Its 1.0 mm PCB thickness and package dimensions are modeling assumptions. The [product photos](https://www.pololu.com/product/2831/pictures) informed the generic component arrangement.

Optional regulator headers are not fitted; bare plated solder connections and IC leads are represented. The component visuals are for identification and assembly explanation. They are not qualified for manufacturing, fit, collision, electrical or thermal checks. `mass_g` and `com_mm` preserve the engineering assembly's physical estimates; these values are not recomputed from the approximate display geometry. `volume_mm3` for the Pololu models describes the new visual primitives. No mechanical part, mounting position or robot mass total is changed by this package.

## Reproduce

Run with FreeCAD's Python, using an existing full local build and the fetched upstream Adafruit notices:

```powershell
& $fcPython components/generate_electronics_visuals.py --cad build/local/cad --notices references/components_r02/notices --output build/local/component-visuals
```

The script reads only `assembly.json`, `meshes/IMU.json`, `meshes/ServoController.json`, and the five explicitly named Adafruit notice files. It generates both regulator meshes from its own source primitives. Ship the supplied `licenses/Apache-2.0.txt` and this README with generated outputs. `records.json` preserves the normal part schema and adds the mesh license, relative mesh path, PCB datum and provenance. `NOTICE.json` supplies machine-readable attribution. `validation.json` records complete material groups, counts, bounds and retained mass/COM estimates.

For integration, append these four records to the viewer's part collection and resolve their `mesh_path` from the component asset directory. Do not add them to the Apache-only mechanical native or printed STEP exports. Keep the visible viewer attribution accessible; images that incorporate the Adafruit adaptations should carry their credit and an appropriate CC-BY-SA notice alongside them.
