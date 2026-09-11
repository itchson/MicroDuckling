# Component reference inputs

The public repository contains source URLs and hashes, not vendor CAD or product documentation. [inputs.json](inputs.json) records the four files required by `src/hardware_r02.py` and their original upstream notices.

From the repository root:

```sh
python scripts/fetch_reference_inputs.py --list
python scripts/fetch_reference_inputs.py
python scripts/fetch_reference_inputs.py --verify
```

Downloads go to `references/components_r02/`, which is ignored by Git. Existing files must match their recorded SHA-256 and byte count; mismatches stop the command without replacing the file. A changed upstream file needs an explicit source review and manifest update. `--verify` uses no network.

Adafruit board sources use the hardware README's CC-BY-SA 3.0 terms. The LSM6DS3 repository also supplies an MIT license file, which is fetched alongside its hardware notices. Pololu's STEP resources are manufacturer references; this project does not claim a license to redistribute them or their exact geometry. See [licensing](../docs/licensing.md).

The ESP32-CAM model uses published nominal dimensions and explicitly approximate component envelopes; it does not load a datasheet or a vendor mesh. References for dimensional facts and component selection are in the [BOM](../docs/bom.md).
