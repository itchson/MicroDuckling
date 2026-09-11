"""Reject stale CAD/URDF/USD evidence before starting the expensive simulator.

Uses only the standard library so these checks also run without Isaac installed.
Hashes establish asset identity, not physical validity or successful locomotion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def verify_export(here: Path) -> dict:
    """Ensure exported information, URDF, manifest and original CAD agree."""
    info = read_json(here / "robot_info.json")
    manifest_path = here.parent / "cad/manifest.json"
    if info.get("source_manifest_sha256") != digest(manifest_path):
        raise ValueError("CAD manifest changed. Run export_urdf.py before importing or simulating.")
    if info.get("urdf_sha256") != digest(here / "microduckling.urdf"):
        raise ValueError("URDF changed. Run export_urdf.py before importing or simulating.")
    manifest = read_json(manifest_path)
    for key, filename in (("source_cad_sha256", "MicroDuckling_R01.FCStd"),
                          ("source_assembly_sha256", "assembly.json")):
        if manifest.get(key) != digest(manifest_path.parent / filename):
            raise ValueError("Saved CAD or assembly changed. Run derive_manifest.py and export_urdf.py.")
    meshes = info.get("mesh_sha256", {})
    if not meshes:
        raise ValueError("Export has no mesh identity evidence. Run export_urdf.py again.")
    for relative, expected in meshes.items():
        path = here.parent / relative
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"Exported mesh changed or is missing: {relative}. Rederive CAD and export again.")
    return info


def imported_files(here: Path) -> dict[str, str]:
    """Bind every local output layer/mesh, excluding the report itself."""
    return {p.relative_to(here).as_posix(): digest(p)
            for p in sorted((here / "usd").rglob("*"))
            if p.is_file() and p.name != "import_report.json"}


def verify_import(here: Path) -> tuple[dict, dict]:
    info = verify_export(here)
    report_path = here / "usd/import_report.json"
    if not report_path.is_file():
        raise ValueError("Run import_asset.py in Isaac Lab and pass its inertia checks first.")
    report = read_json(report_path)
    if (report.get("status") != "IMPORTED_AND_INERTIAS_VERIFIED"
            or report.get("urdf_sha256") != info["urdf_sha256"]
            or report.get("source_manifest_sha256") != info["source_manifest_sha256"]):
        raise ValueError("USD import evidence is stale or incomplete. Run import_asset.py again.")
    hashes = report.get("artifact_sha256", {})
    if "usd/microduckling.usd" not in hashes:
        raise ValueError("USD import evidence has no artifact hashes. Run import_asset.py again.")
    for relative, expected in hashes.items():
        path = (here / relative).resolve()
        if not path.is_relative_to((here / "usd").resolve()) or not path.is_file() or digest(path) != expected:
            raise ValueError(f"Imported artifact changed or is missing: {relative}. Run import_asset.py again.")
    return info, report


def verify_smoke(here: Path, environment_path: Path | None = None) -> dict:
    """Require a current bounded runtime pass before a train/play invocation."""
    verify_import(here)
    path = here / "isaac_smoke_report.json"
    if not path.is_file():
        raise ValueError("Run smoke_isaac.py for the current USD before training or playback.")
    report = read_json(path)
    environment_path = environment_path or here / "microduckling_lab/environment.py"
    if (report.get("status") != "FINITE_BOUNDED_SIMULATION"
            or report.get("import_report_sha256") != digest(here / "usd/import_report.json")
            or report.get("environment_sha256") != digest(environment_path)):
        raise ValueError("Runtime smoke evidence is stale or failed. Run smoke_isaac.py again.")
    return report
