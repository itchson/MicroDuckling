"""SPDX-License-Identifier: Apache-2.0

Add optional link-local sole hull points using only the two public tread meshes.
The derivation uses the Python standard library; Rapier constructs the hull at load.
Existing box colliders are preserved for a selectable legacy contact model.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

SOLE_MESHES = {"left_leg": "TreadLeft", "right_leg": "TreadRight"}


def has_volume(points):
    """Reject coincident, collinear and coplanar point sets before hull construction."""
    def sub(a, b):
        return tuple(x - y for x, y in zip(a, b))

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    def cross(a, b):
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

    offsets = [sub(p, points[0]) for p in points]
    first = max(offsets, key=lambda p: dot(p, p))
    normals = [cross(first, p) for p in offsets]
    normal = max(normals, key=lambda p: dot(p, p))
    size = math.sqrt(dot(first, first))
    return size > 0 and max(abs(dot(normal, p)) for p in offsets) > size ** 3 * 1e-10


def attach_sole_hulls(asset: dict, mesh_dir: Path) -> dict:
    """Return a copy with soleConvexHullM flat XYZ points on the two foot links.

    CAD mesh positions are assembly-global millimetres; cadZeroOriginsM contains
    assembly-global link origins in metres. Local points are round(mm / 1000 -
    originM, 8). No rotation is needed: zero-pose link axes match the CAD axes.
    """
    result = copy.deepcopy(asset)
    links = {link["name"]: link for link in result["links"]}
    sources = {}
    for link_name, mesh_name in SOLE_MESHES.items():
        raw = (mesh_dir / f"{mesh_name}.json").read_bytes()
        positions = json.loads(raw)["positions"]
        origin = result["cadZeroOriginsM"][link_name]
        if len(origin) != 3 or not all(math.isfinite(v) for v in origin):
            raise ValueError(f"Invalid origin for {link_name}")
        if not positions or len(positions) % 3 or not all(math.isfinite(v) for v in positions):
            raise ValueError(f"Invalid public mesh positions: {mesh_name}")
        points = sorted({tuple(round(positions[i + axis] / 1000 - origin[axis], 8)
                               for axis in range(3)) for i in range(0, len(positions), 3)})
        if len(points) < 4 or not has_volume(points):
            raise ValueError(f"Insufficient or degenerate hull points: {mesh_name}")
        links[link_name]["soleConvexHullM"] = [value for point in points for value in point]
        sources[link_name] = {
            "source": f"cad/meshes/{mesh_name}.json",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "sourceVertexCount": len(positions) // 3,
            "uniquePointCount": len(points),
            "cadZeroOriginM": list(origin),
        }
    result.setdefault("provenance", {})["soleConvexHull"] = {
        "license": "Apache-2.0",
        "sourceUnits": "mm",
        "outputUnits": "m",
        "coordinateFrame": "link local; zero-pose axes match assembly CAD axes",
        "roundingM": 1e-8,
        "method": "Unique rounded public tread vertices; Rapier constructs their convex hull.",
        "sources": sources,
        "legacyCollidersPreserved": True,
        "activation": "When selecting hull contacts, replace only rocker_* colliders with one sole hull per leg; keep other colliders.",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", required=True, type=Path)
    parser.add_argument("--mesh-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("robot-physics-hulls.json"))
    args = parser.parse_args()
    if args.output.resolve() == args.asset.resolve():
        raise ValueError("Use a distinct output for optional hull A/B testing")
    raw = args.asset.read_bytes()
    result = attach_sole_hulls(json.loads(raw), args.mesh_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(result, indent=2) + "\n").encode("utf-8")
    args.output.write_bytes(encoded)
    report = {"sourcePhysicsAssetSha256": hashlib.sha256(raw).hexdigest(),
              "outputPhysicsAssetSha256": hashlib.sha256(encoded).hexdigest(),
              **result["provenance"]["soleConvexHull"]}
    args.output.with_name("hull-provenance.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output.name,
                      "pointsPerLink": {name: s["uniquePointCount"] for name, s in report["sources"].items()}}))


if __name__ == "__main__":
    main()
