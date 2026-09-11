"""Audit saved nominal harness solids against rigid parts in the neutral pose.

Run with FreeCAD's Python. This checks intersections only: it does not qualify
flexible routing, strain relief, minimum bend radius, or neck/jaw movement.
"""
from pathlib import Path
import hashlib
import json
import math
from itertools import combinations

import FreeCAD as App
import Part
import PartDesign  # Registers document object types when opening the saved CAD.


from build_paths import BUILD_ROOT as ROOT
CAD = ROOT / "cad"
EXPECTED_HARNESSES = {"HarnessBody", "HarnessHead", "HarnessCameraRibbon"}
INTERSECTION_LIMIT_MM3 = 0.01


def audit():
    cad_path = CAD / "MicroDuckling_R01.FCStd"
    assembly_path = CAD / "assembly.json"
    cad_hash = hashlib.sha256(cad_path.read_bytes()).hexdigest()
    assembly_bytes = assembly_path.read_bytes()
    assembly = json.loads(assembly_bytes)
    report = {
        "source_cad_sha256": cad_hash,
        "source_assembly_sha256": hashlib.sha256(assembly_bytes).hexdigest(),
        "pose": "saved neutral pose",
        "unexplained_intersection_limit_mm3": INTERSECTION_LIMIT_MM3,
        "scope": (
            "Neutral-pose intersections of saved nominal harness solids against all "
            "non-harness assembled parts, plus intersections between distinct cable solids. Coupons are "
            "excluded. This is not flexible-cable simulation or a clearance, connector "
            "retention, strain-relief, bend-radius, electrical, or motion qualification."
        ),
        "pairs": [],
        "cable_pairs": [],
        "failures": [],
        "passed": False,
    }
    document = None
    try:
        records = [p for p in assembly["parts"] if p["kind"] != "coupon"]
        harnesses = [p for p in records if p["kind"] == "harness"]
        actual = {p["name"] for p in harnesses}
        if actual != EXPECTED_HARNESSES:
            raise ValueError(f"Unexpected harness inventory: {sorted(actual)}")
        rigid = [p for p in records if p["kind"] != "harness"]
        if not any(p["name"] == 'ESP32CAM' for p in rigid):
            raise ValueError("Expected ESP32CAM rigid part is missing")
        if len({p["name"] for p in records}) != len(records):
            raise ValueError("Duplicate assembled part names")
        document = App.openDocument(str(cad_path))
        shapes = {}
        for record in records:
            obj = document.getObject(record.get("object_name", record["name"]))
            if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
                raise ValueError(f"Missing saved shape: {record['name']}")
            if not obj.Shape.isValid():
                raise ValueError(f"Invalid saved shape: {record['name']}")
            shapes[record["name"]] = obj.Shape
        for harness in harnesses:
            a = harness["name"]
            for record in rigid:
                b = record["name"]
                left, right = shapes[a], shapes[b]
                volume = (left.common(right).Volume
                          if left.BoundBox.intersect(right.BoundBox) else 0.0)
                if not math.isfinite(volume) or volume < 0:
                    raise ValueError(f"Invalid overlap volume for {a} / {b}: {volume}")
                limit = INTERSECTION_LIMIT_MM3
                pair = {
                    "harness": a,
                    "rigid_part": b,
                    "overlap_mm3": volume,
                    "maximum_overlap_mm3": limit,
                    "passed": volume <= limit,
                }
                report["pairs"].append(pair)
                if not pair["passed"]:
                    report["failures"].append(pair)
        report["harness_count"] = len(harnesses)
        strands=[(record['name'],i,solid) for record in harnesses
                 for i,solid in enumerate(shapes[record['name']].Solids)]
        for (a,ai,left),(b,bi,right) in combinations(strands,2):
            volume=left.common(right).Volume if left.BoundBox.intersect(right.BoundBox) else 0.0
            pair=dict(a=a,a_solid=ai,b=b,b_solid=bi,overlap_mm3=volume,
                      passed=math.isfinite(volume) and volume<=INTERSECTION_LIMIT_MM3)
            report['cable_pairs'].append(pair)
            if not pair['passed']:report['failures'].append(pair)
        report["rigid_part_count"] = len(rigid)
        report["checked_pair_count"] = len(report["pairs"])
        # Catch an asset rebuild that overlapped this audit rather than stamping
        # the results with hashes from a different CAD/manifest generation.
        if hashlib.sha256(cad_path.read_bytes()).hexdigest() != cad_hash:
            raise ValueError("CAD changed during harness audit")
        if assembly_path.read_bytes() != assembly_bytes:
            raise ValueError("Assembly manifest changed during harness audit")
        report["passed"] = not report["failures"]
    except Exception as error:
        report["failures"].append({"error": str(error)})
    finally:
        if document is not None:
            App.closeDocument(document.Name)
        (CAD / "harness_route_checks.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps({
        "passed": report["passed"],
        "checked_pair_count": report.get("checked_pair_count", 0),
        "failures": report["failures"],
        "report": str(CAD / "harness_route_checks.json"),
    }, indent=2))
    if not report["passed"]:
        raise SystemExit("Neutral harness intersection audit failed")
    return report


if __name__ == "__main__":
    audit()
