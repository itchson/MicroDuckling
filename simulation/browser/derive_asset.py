"""Derive a small public scalar physics asset from the local CAD manifest.

Usage: python derive_asset.py <cad/manifest.json> <robot-physics.json>
Requires NumPy. No vendor geometry, mesh data or workstation paths are emitted.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np


def quaternion(matrix):
    # Stable matrix-to-quaternion conversion using the dominant diagonal branch.
    m = np.asarray(matrix)
    trace = np.trace(m)
    if trace > 0:
        s = math.sqrt(trace + 1) * 2
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s,
             (m[1, 0] - m[0, 1]) / s, s / 4]
    else:
        i = int(np.argmax(np.diag(m)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = math.sqrt(1 + m[i, i] - m[j, j] - m[k, k]) * 2
        q = [0, 0, 0, (m[k, j] - m[j, k]) / s]
        q[i], q[j], q[k] = s / 4, (m[j, i] + m[i, j]) / s, (m[k, i] + m[i, k]) / s
    q = np.asarray(q)
    return (q / np.linalg.norm(q)).tolist()


def rpy_quaternion(rpy):
    r, p, y = [float(x) / 2 for x in rpy]
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return [sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy]


def derive(source):
    raw = source.read_bytes()
    d = json.loads(raw)
    result = {"schemaVersion": 1, "name": "MicroDuckling R05 browser physics experiment",
              "units": "m-kg-s-rad", "upAxis": "z", "forwardAxis": "x",
              "provenance": {"manifestSha256": hashlib.sha256(raw).hexdigest(),
                             "sourceCadSha256": d["source_cad_sha256"],
                             "massScope": "Full intended assembly including omitted supplier boards",
                             "status": "CAD estimates; approximate contacts and unmeasured servo model. Browser Rapier experiment, not Isaac Sim or a hardware-qualified controller."},
              "cadZeroOriginsM": {}, "links": [], "joints": [],
              "contactModel": {"footRadiusM": d["rocker_contact"]["radius_mm"] / 1000,
                               "segmentsX": 11, "segmentsY": 5, "friction": 0.7,
                               "description": "11 by 5 tangent boxes per spherical rocker foot; inner core boxes for torso/head/jaw. Self-collision excluded because core envelopes are approximate."}}
    for link in d["links"]:
        name, i = link["name"], link["inertia_kg_m2"]
        tensor = np.array([[i["ixx"], i["ixy"], i["ixz"]], [i["ixy"], i["iyy"], i["iyz"]], [i["ixz"], i["iyz"], i["izz"]]])
        values, axes = np.linalg.eigh(tensor)
        if np.linalg.det(axes) < 0:
            axes[:, 0] *= -1
        if min(values) <= 0:
            raise ValueError("Non-positive inertia")
        origin = np.array(link["frame_origin_global_mm"]) / 1000
        result["cadZeroOriginsM"][name] = origin.tolist()
        entry = {"name": name, "massKg": link["mass_kg"], "comM": (np.array(link["com_mm"]) / 1000).tolist(),
                 "inertiaKgM2": tensor.tolist(), "principalInertiaKgM2": values.tolist(),
                 "inertiaFrame": quaternion(axes), "colliders": []}
        for c in link["collisions"]:
            if c["name"].startswith("sole_"):
                continue
            if c["type"] != "box":
                raise ValueError("Expected authored box primitives")
            entry["colliders"].append({"name": c["name"], "halfExtentsM": (np.array(c["size_mm"]) / 2000).tolist(),
                                       "positionM": (np.array(c["origin_xyz_mm"]) / 1000).tolist(),
                                       "quaternion": rpy_quaternion(c["origin_rpy_rad"])})
        if name.endswith("_leg"):
            bounds = np.array(d["rocker_contact"]["planform_bounds_xy_mm"][name]) / 1000
            center = np.array(d["rocker_contact"]["centers_global_mm"][name]) / 1000
            radius = result["contactModel"]["footRadiusM"]
            nx, ny = 11, 5
            dx, dy, thickness = (bounds[1] - bounds[0]) / nx, (bounds[3] - bounds[2]) / ny, 0.0028
            for ix in range(nx):
                for iy in range(ny):
                    x = bounds[0] + (ix + .5) * dx
                    y = bounds[2] + (iy + .5) * dy
                    rx, ry = x - center[0], y - center[1]
                    # Omit the outer corners of the rounded planform.
                    if ((x - (bounds[0] + bounds[1]) / 2) / ((bounds[1] - bounds[0]) / 2)) ** 2 + (ry / ((bounds[3] - bounds[2]) / 2)) ** 2 > 1.35:
                        continue
                    z = center[2] - math.sqrt(radius * radius - rx * rx - ry * ry)
                    normal = np.array([-rx, -ry, center[2] - z]) / radius
                    # local +Z normal points into the foot; no vendor geometry.
                    q = np.array([-normal[1], normal[0], 0., 1 + normal[2]])
                    q /= np.linalg.norm(q)
                    point = np.array([x, y, z]) + normal * thickness / 2 - origin
                    entry["colliders"].append({"name": f"rocker_{ix}_{iy}", "halfExtentsM": [dx * .515, dy * .515, thickness / 2],
                                               "positionM": point.tolist(), "quaternion": q.tolist()})
        result["links"].append(entry)
    for j in d["joints"]:
        result["joints"].append({"name": j["name"], "parent": j["parent"], "child": j["child"],
                                 "parentAnchorM": (np.array(j["origin_xyz_mm"]) / 1000).tolist(),
                                 "childAnchorM": [0, 0, 0], "axis": j["axis"], "limitsRad": j["limit_rad"],
                                 "motor": {"stiffnessNmPerRad": .7, "dampingNmsPerRad": .008,
                                           "maxTorqueNm": .09, "noLoadSpeedRadS": 10.47, "commandRateRadS": 3}})
    result["totalMassKg"] = sum(l["massKg"] for l in result["links"])
    return result


if __name__ == "__main__":
    output = Path(sys.argv[2])
    asset = derive(Path(sys.argv[1]))
    output.write_text(json.dumps(asset, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"massKg": asset["totalMassKg"], "links": len(asset["links"]), "colliders": sum(len(l["colliders"]) for l in asset["links"])}))
