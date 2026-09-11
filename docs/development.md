# Development

See [build and validation](build.md) for Python setup, verified component downloads, the FreeCAD rebuild and static simulation checks. [CONTRIBUTING](../CONTRIBUTING.md) describes review and contribution practices.

The active mechanical source is `src/build_cad.py` with `body_r04.py`, `head_r04.py`, `electronics_r04.py`, `hardware_r02.py` and `direct_mount_r07.py`. R04 module suffixes record their introduction; the current assembly is R07. Source dimensions are millimetres. Detailed vendor geometry is an optional local input; it is not part of the public CAD payload.

All local CAD/audit/simulation outputs default to `build/local/`. For a separate output location, set `MICRODUCKLING_BUILD_ROOT` before invoking any build or simulation command. Do not set it to the repository root or a published source/assets directory. The reference cache stays at `references/components_r02/`.

When dimensions or mass assumptions change, regenerate CAD, repeat the nominal geometry checks, derive new simulation assets and rerun the numerical checks. Keep numerical geometry results distinct from physical measurements or successful dynamics. See [engineering review](engineering-review.md), [hardware measurements](hardware-measurements.md), [simulation](simulation.md) and [licensing](licensing.md).
