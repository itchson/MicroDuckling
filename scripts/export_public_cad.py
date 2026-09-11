"""Create a clean public CAD package from a reviewed engineering workspace.

Run with FreeCAD's Python: python scripts/export_public_cad.py --source <workspace>
Only explicitly approved project parts are exported. Source files are never edited.
"""
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

import FreeCAD as App
import Part

OMITTED = {"IMU", "Buck_0"}
RETIRED = {"ServoController", "Buck_1", *(f"ServoControllerMountScrew{i}" for i in range(4))}
PRINT_PARTS = {
    "BodyShellLeft", "BodyShellRight", "CameraBoardClamp", "CameraCradle",
    "CameraRing", "Chassis", "FacePanel", "FixedNeckSupport", "HeadFrame",
    "HeadHood", "Jaw", "LegFootLeft", "LegFootRight", "NeckCarrier", "UpperBill",
}
COUPONS = {"LegHornCoupon", "ClearanceCoupon"}
PRIVATE_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[/\\]|/Users/|/home/", re.IGNORECASE)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_copy(source, destination):
    if not source.is_file() or not source.stat().st_size:
        raise ValueError(f"Missing source export: {source.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if sha256(source) != sha256(destination):
        raise ValueError(f"Copy mismatch: {source.name}")


def assert_portable(text, label):
    if PRIVATE_PATH.search(text):
        raise ValueError(f"Local path found in {label}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "cad")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if source == output or source / "cad" == output:
        raise ValueError("Public output must be distinct from source CAD")
    raw = json.loads((source / "cad/assembly.json").read_text(encoding="utf-8"))
    records = raw["parts"]
    names = {record["name"] for record in records}
    if len(names) != len(records) or not OMITTED <= names or names & RETIRED:
        raise ValueError("Expected unique records, the two retained reference boards, and no retired electronics")
    if {r["name"] for r in records if r["kind"] == "print"} != PRINT_PARTS:
        raise ValueError("Printable-part allowlist changed; review it before publication")
    if {r["name"] for r in records if r["kind"] == "coupon"} != COUPONS:
        raise ValueError("Coupon allowlist changed; review it before publication")
    safe = [r for r in records if r["name"] not in OMITTED]
    active = [r for r in safe if r["kind"] != "coupon"]
    output.mkdir(parents=True, exist_ok=True)
    # Reject stale or unreviewed filenames instead of deleting existing files.
    for folder, allowed, suffix in (
        ("meshes", {r["name"] for r in safe}, ".json"),
        ("stl", PRINT_PARTS | COUPONS, ".stl"),
        ("3mf", PRINT_PARTS | COUPONS, ".3mf"),
    ):
        for file in (output / folder).glob("*"):
            if file.suffix != suffix or file.stem not in allowed:
                raise ValueError(f"Unreviewed existing public export: {folder}/{file.name}")
    for record in safe:
        name = record["name"]
        mesh_source = source / "cad/meshes" / f"{name}.json"
        mesh = json.loads(mesh_source.read_text(encoding="utf-8"))
        if set(mesh) - {"positions", "indices", "materials", "groups"}:
            raise ValueError(f"Unexpected mesh metadata: {name}")
        if len(mesh["positions"]) % 3 or len(mesh["indices"]) % 3:
            raise ValueError(f"Incomplete mesh coordinates or triangles: {name}")
        assert_portable(json.dumps(mesh), name)
        checked_copy(mesh_source, output / "meshes" / f"{name}.json")
        if name in PRINT_PARTS | COUPONS:
            folder = "coupons" if name in COUPONS else "stl"
            checked_copy(source / "cad" / folder / f"{name}.stl", output / "stl" / f"{name}.stl")
            mf_source = source / "exports/3mf_review" / f"{name}.3mf"
            with zipfile.ZipFile(mf_source) as archive:
                if set(archive.namelist()) != {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}:
                    raise ValueError(f"Unexpected 3MF archive contents: {name}")
                for member in archive.namelist():
                    assert_portable(archive.read(member).decode("utf-8"), name + "/" + member)
            checked_copy(mf_source, output / "3mf" / f"{name}.3mf")
    step = output / "MicroDuckling_R05_printed.step"
    assert_portable((source / "cad/MicroDuckling_R01.step").read_text(encoding="utf-8"), "printed STEP")
    checked_copy(source / "cad/MicroDuckling_R01.step", step)
    if len(Part.read(str(step)).Solids) != len(PRINT_PARTS):
        raise ValueError(f"Printed STEP must contain exactly {len(PRINT_PARTS)} solids")
    # Rebuild a new document rather than saving a modified source archive. This
    # prevents deleted objects, reference records, thumbnails or source metadata
    # from being retained in the public FCStd ZIP container.
    original = App.openDocument(str(source / "cad/MicroDuckling_R01.FCStd"))
    public = App.newDocument("MicroDuckling_R05_mechanical")
    public.Label = "MicroDuckling R06 mechanical preview"
    public.License = "Apache-2.0"
    public.LicenseURL = "https://www.apache.org/licenses/LICENSE-2.0"
    public.Comment = "Engineering prototype. Two reference PCB models omitted from mechanical CAD; separate public component visuals are provided. Fit and walking unverified."
    for record in active:
        native = original.getObject(record["object_name"])
        if native is None or native.Shape.isNull() or not native.Shape.isValid():
            raise ValueError(f"Invalid source native part: {record['name']}")
        obj = public.addObject("PartDesign::Feature", record["object_name"])
        obj.Label = record["name"]
        obj.Shape = native.Shape.copy()
        for key, value in (("ComponentType", record["kind"]), ("RigidLink", record["link"]), ("Notes", record["note"])):
            assert_portable(value, record["name"])
            obj.addProperty("App::PropertyString", key)
            setattr(obj, key, value)
        obj.addProperty("App::PropertyColor", "ReviewColor")
        obj.ReviewColor = tuple(int(record["color"][i:i + 2], 16) / 255 for i in (1, 3, 5))
        obj.addProperty("App::PropertyFloat", "EstimatedMass_g")
        obj.EstimatedMass_g = record["mass_g"]
    sheet = public.addObject("Spreadsheet::Sheet", "DesignParameters")
    for row, (key, value) in enumerate(raw["parameters"].items(), 1):
        sheet.set(f"A{row}", key)
        sheet.set(f"B{row}", str(value))
    sheet.setColumnWidth("A", 270)
    public.recompute()
    native_path = output / "MicroDuckling_R05_mechanical.FCStd"
    # Disable version backups for this generated public document.
    preferences = App.ParamGet("User parameter:BaseApp/Preferences/Document")
    backup_count = preferences.GetInt("CountBackupFiles", 1)
    try:
        preferences.SetInt("CountBackupFiles", 0)
        public.saveAs(str(native_path))
    finally:
        preferences.SetInt("CountBackupFiles", backup_count)
    App.closeDocument(public.Name)
    App.closeDocument(original.Name)
    reopened = App.openDocument(str(native_path))
    shape_objects = [obj for obj in reopened.Objects if hasattr(obj, "Shape")]
    if {obj.Label for obj in shape_objects} != {r["name"] for r in active}:
        raise ValueError("Public native document has unexpected objects")
    if not all(obj.Shape.isValid() and not obj.Shape.isNull() for obj in shape_objects):
        raise ValueError("Public native shape validity check failed")
    App.closeDocument(reopened.Name)
    with zipfile.ZipFile(native_path) as archive:
        for member in archive.namelist():
            if member.endswith(".xml"):
                text = archive.read(member).decode("utf-8")
                assert_portable(text, member)
                if any(f'name="{name}"' in text for name in OMITTED | COUPONS | RETIRED):
                    raise ValueError("Excluded native object found in saved document")
    raw["parts"] = safe
    raw["public_preview"] = {
        "omitted_components": sorted(OMITTED),
        "reason": "Retained reference boards are separated from the mechanical CAD; licensed public visual representations are provided in components/.",
        "native_scope": "Mechanical solids and original generic hardware envelopes; coupons excluded.",
        "mesh_scope": "Mechanical preview with two optional standalone fit coupons.",
        "mass_estimates_scope": "full_physical_assembly",
        "mass_estimates_note": "mass_g and com_mm retain the complete physical assembly estimates, including omitted boards; they are not totals of the public preview meshes.",
        "native_file": native_path.name,
        "printed_step_file": step.name,
        "native_sha256": sha256(native_path),
        "source_cad_sha256": sha256(source / "cad/MicroDuckling_R01.FCStd"),
        "source_assembly_sha256": sha256(source / "cad/assembly.json"),
        "assembled_part_count": len(active),
        "coupon_count": len(COUPONS),
    }
    encoded = json.dumps(raw, indent=2) + "\n"
    assert_portable(encoded, "assembly.json")
    (output / "assembly.json").write_text(encoded, encoding="utf-8", newline="\n")
    summary = {"native_shapes": len(active), "mesh_records": len(safe), "printed_parts": len(PRINT_PARTS), "coupons": len(COUPONS), "stl_files": len(PRINT_PARTS | COUPONS), "three_mf_files": len(PRINT_PARTS | COUPONS), "omitted_components": sorted(OMITTED), "native_sha256": sha256(native_path), "printed_step_sha256": sha256(step), "native_reopen_valid": True, "step_solids": len(PRINT_PARTS)}
    (output / "public_export_checks.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
