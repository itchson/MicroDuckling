# Separately licensed component visuals

Two assets complete the active R08 viewer: the body IMU and shared 5 V regulator. The PCA9685 and separate logic regulator were removed from the robot. Coordinates are assembly millimetres. Keep each mesh with its record, attribution and license.

| Asset | Representation | License |
|---|---|---|
| `meshes/IMU.json` | Adafruit LSM6DS3TR-C board adapted from Eagle geometry; generic component heights and fitted connectors | CC-BY-SA-3.0 |
| `meshes/Buck_0.json` | Original dimension-based approximation of the Pololu D24V50F5 shared regulator | Apache-2.0 |

The IMU design is by **Limor Fried/Ladyada for Adafruit Industries**. MicroDuckling contributors adapted its board outlines, holes, pads and package placements to colored 3D meshes, added generic heights and connectors, and positioned it in the assembly. See [machine-readable attribution](NOTICE.json), the [upstream README](licenses/adafruit-lsm6ds3/README.md), [hardware license](licenses/adafruit-lsm6ds3/license.txt) and [additional upstream MIT notice](licenses/adafruit-lsm6ds3/LICENSE). The historical PCA9685 upstream notices are retained for earlier revisions; its mesh was removed in R06.

The regulator visual uses independently authored primitives, without reading or converting manufacturer STEP geometry. Its PCB outline and nominal envelope use the [manufacturer dimensions](https://www.pololu.com/file/0J1436/d24v50f5-step-down-voltage-regulator-dimensions.pdf); [product photographs](https://www.pololu.com/product/2851/pictures) informed a generic component arrangement. Detail and placement are approximate. Its mass and COM retain the engineering assembly estimates, so adding the visual does not add another regulator's weight. Product names identify the represented hardware and imply no endorsement.

These display meshes are not substitutes for supplier mechanical drawings, electrical validation or physical measurements. The complete native mechanical model and printed-part STEP remain separate from these assets.

Regenerate with FreeCAD's Python after building the source assembly:

```sh
python components/generate_electronics_visuals.py --cad build/local/cad --notices references/components_r02/notices --output components
```

The script reads the assembly records, the IMU mesh and the explicitly named upstream notice files; it generates the regulator from original source primitives. Ship `licenses/Apache-2.0.txt`, the applicable Adafruit notices and this README with the outputs. `records.json`, `NOTICE.json` and `validation.json` preserve physical estimates, material groups, bounds and provenance.
