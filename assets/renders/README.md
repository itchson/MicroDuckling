# MicroDuckling assembly renders

`assembled.png` and `exploded.png` show the complete 91-part R05 assembly at neutral joints. The two separate fit coupons are excluded. The exploded image uses the viewer's 100% layout, evaluated directly from `viewer/lib/explode.ts`; this is an explanatory layout, not a physical disassembly sequence. The renderer preserves every input mesh vertex and triangle and moves parts rigidly for the exploded view.

Both PNG images are licensed under **Creative Commons Attribution-ShareAlike 3.0 Unported (CC-BY-SA-3.0)**. See the [full license](LICENSE-CC-BY-SA-3.0.txt) and [license summary](https://creativecommons.org/licenses/by-sa/3.0/).

Rendered by **MicroDuckling contributors**. These images incorporate colored 3D adaptations of the following board designs by **Limor Fried/Ladyada for Adafruit Industries**:

- [Adafruit 16-Channel PWM Servo Driver PCB Eagle Files](https://github.com/adafruit/Adafruit-16-Channel-PWM-Servo-Driver-PCB), represented by the `ServoController` mesh.
- [Adafruit LSM6DS3TR-C 6-DoF Accel + Gyro IMU - STEMMA QT / Qwiic PCB](https://github.com/adafruit/Adafruit-LSM6DS3TR-C-PCB), represented by the `IMU` mesh.

Changes from the original Adafruit designs: PCB outlines, holes, pads and package placements were adapted from Eagle into colored 3D geometry; generic component heights and fitted connectors were added; the resulting meshes were placed and rendered in the MicroDuckling assembly. Attribution, original upstream READMEs and licenses are retained in the [component notices](../../components/README.md) and [machine-readable notice manifest](../../components/NOTICE.json).

The two Pololu regulator visuals are original dimension-based approximations with generic component details. They are identified in the component manifest and use no manufacturer STEP geometry. The assembly and hardware remain engineering prototypes; rendered visual detail does not establish physical fit or operating performance. Product names identify represented hardware and do not imply endorsement.

`render_provenance.json` records all 91 input mesh hashes and their individual source paths, source manifest hashes, the viewer layout source hashes, the exact exploded translations, image settings and licensing. The separate mechanical CAD files retain their own license.

To reproduce after installing the viewer dependencies:

```powershell
& $blenderExe --background --factory-startup --python-exit-code 1 --python scripts/render_public_cad.py -- --width 2400 --height 2000
```

Pass `--node` followed by a Node 22.18+ executable if Node is not on `PATH`; `--device cpu` requests CPU rendering. The default selects OptiX when available and records the actual device type.
