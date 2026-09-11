# Build and validate

Run commands from the repository root. Python 3.10 or newer is required for the source; the publication checks were run with Python 3.12. The numerical tools need NumPy and trimesh. FreeCAD and NVIDIA's simulation tools are separate installations.

## Numerical checks without CAD or Isaac

```sh
python -m venv .venv
```

Activate the environment (`.venv\Scripts\Activate.ps1` in PowerShell, or `source .venv/bin/activate` on Linux/macOS), then:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s simulation/tests -v
python -m unittest discover -s scripts/tests -v
```

The simulation tests create their own small fixtures. They check millimetre-to-metre conversion, inertias, articulation topology, mass balance and stale evidence rejection. They require neither a generated robot nor Isaac and do not establish that the robot will walk.

## Local CAD rebuild

The source was developed against FreeCAD 1.1's Python modules (`FreeCAD`, `Part`, `MeshPart` and `PartDesign`). Use a Python interpreter supplied by or configured for that installation; installing a package named `FreeCAD` into an ordinary environment is not an equivalent setup. Set `$fcPython` in PowerShell to that interpreter's executable path and verify it before building:

```powershell
& $fcPython -c "import FreeCAD, Part, MeshPart, PartDesign; print(FreeCAD.Version())"
python scripts/fetch_reference_inputs.py
python scripts/fetch_reference_inputs.py --verify
& $fcPython src/build_cad.py
& $fcPython src/audit_cad.py
& $fcPython src/check_assembly_paths.py
& $fcPython src/check_detail_interfaces.py
& $fcPython src/check_display_geometry.py
& $fcPython src/check_harness_routes.py
```

On Linux, use the same script paths with your configured FreeCAD Python interpreter. FreeCAD distribution layouts differ; the import check above is the prerequisite, not an assumed installation path.

Edit parameters and construction logic in `src/build_cad.py`, `src/body_r04.py`, `src/head_r04.py` and `src/electronics_r04.py`. The module suffixes record their introduction; the active `design_revision` is R06. The parameter spreadsheet in the resulting document is a record, not a live parametric rebuild interface.

The builder writes `build/local/cad/MicroDuckling_R01.FCStd`, `build/local/cad/assembly.json`, part meshes and a print-only STEP. `R01` is a legacy filename; check `design_revision` for the actual revision. The full scene includes locally downloaded electronics. These full assemblies, input files and detailed hardware meshes are intentionally Git-ignored. Published geometry is curated separately; see [license scope](licensing.md). A successful local build does not authorize publishing every generated file.

All CAD checks and simulation tools use the same `build/local/` root. To use a different generated-output directory, set `MICRODUCKLING_BUILD_ROOT` before invoking them. Keep it separate from the repository's public files; in-repository output roots are limited to `build/` or `work/`. The manufacturer input cache remains in the repository's `references/components_r02/`.

To validate and package the 17 print/coupon meshes locally, then generate a separate public review export:

```powershell
python scripts/package_printables.py --source build/local
& $fcPython scripts/export_public_cad.py --source build/local --output build/public-check
```

The first command writes geometry-only 3MFs under `build/local/exports/3mf_review/`; the second filters approved geometry into `build/public-check/`. Inspect that export before deliberately replacing the published `cad/` files. Omit `--output` only when intentionally updating those public files.

## Derive local simulation assets

NumPy must also be importable in the FreeCAD Python environment for the derivation step:

```powershell
& $fcPython -c "import numpy; print(numpy.__version__)"
& $fcPython simulation/derive_manifest.py
python simulation/export_urdf.py
python simulation/validate_assets.py
python simulation/assess_balance.py
```

The derivation reopens the saved FreeCAD assembly, accounts for every non-coupon part, derives link-local meshes, and combines component masses and inertias. It writes local generated files under `build/local/cad/` and `build/local/simulation/`. These outputs are omitted from the public source repository because full link meshes contain vendor geometry. Regenerate them locally; do not bypass the hash checks or replace missing assets with unrelated meshes.

To derive a separate public browser review asset, combining local mass/inertia data with the original public tread hulls:

```sh
python simulation/browser/derive_asset.py build/local/cad/manifest.json build/browser-check/robot-physics.json --mesh-dir cad/meshes
```

Use the matching tread directory from a separate public export when reviewing changed CAD. The browser generator records both tread hashes, preserves mass independently of collider shape, and embeds the recommended convex/600 Hz/16-iteration settings. See [contact evidence and regeneration](browser-contact-physics.md) before intentionally replacing the checked-in browser asset.

The next step requires a compatible Isaac installation and an actual import/smoke run. See [simulation](simulation.md).
