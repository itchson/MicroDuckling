"""Compare CAD mass balance without pretending that static geometry proves a gait.

Run after derive_manifest.py/export_urdf.py. The body and hips stay at CAD zero;
only head yaw and jaw pitch are sampled. SI inertia comes from the CAD manifest.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import zipfile

import numpy as np

from asset_integrity import digest, read_json, verify_export
from export_urdf import tensor

from paths import BUILD_ROOT as PROJECT
GRAVITY = 9.80665


def rotation(axis, angle):
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * skew + (1 - math.cos(angle)) * (skew @ skew)


def rpy_matrix(values):
    roll, pitch, yaw = values
    return rotation([0, 0, 1], yaw) @ rotation([0, 1, 0], pitch) @ rotation([1, 0, 0], roll)


def pose_links(manifest, angles):
    links = {link["name"]: link for link in manifest["links"]}
    frames = {"body": (np.eye(3), np.asarray(links["body"]["frame_origin_global_mm"]))}
    pending = list(manifest["joints"])
    while pending:
        before = len(pending)
        for joint in pending[:]:
            if joint["parent"] not in frames:
                continue
            parent_r, parent_t = frames[joint["parent"]]
            local_r = rpy_matrix(joint.get("origin_rpy_rad", [0, 0, 0]))
            frames[joint["child"]] = (
                parent_r @ local_r @ rotation(joint["axis"], angles.get(joint["name"], 0)),
                parent_t + parent_r @ np.asarray(joint["origin_xyz_mm"]))
            pending.remove(joint)
        if before == len(pending):
            raise ValueError("Invalid articulation tree")
    return {name: dict(mass=link["mass_kg"],
                       com=frames[name][1] + frames[name][0] @ np.asarray(link["com_mm"]),
                       inertia=frames[name][0] @ tensor(link) @ frames[name][0].T,
                       frame_origin=frames[name][1]) for name, link in links.items()}


def combined(parts):
    mass = sum(p["mass"] for p in parts)
    com = sum((p["mass"] * p["com"] for p in parts), np.zeros(3)) / mass
    return mass, com


def pose_metrics(manifest, neck=0.0, jaw=0.0):
    posed = pose_links(manifest, {"neck_yaw": neck, "jaw_pitch": jaw})
    total, com = combined(list(posed.values()))
    head = [posed["head"], posed["jaw"]]
    head_mass, head_com = combined(head)
    pivot = posed["head"]["frame_origin"]
    yaw_i = sum(p["inertia"][2, 2] + p["mass"] * float(np.sum(((p["com"] - pivot)[:2] / 1000)**2))
                for p in head)
    supported_mass, supported_com = combined([posed[n] for n in ("body", "head", "jaw")])
    hip_center = posed["body"]["frame_origin"]
    hip_pitch = supported_mass * GRAVITY * (supported_com[0] - hip_center[0]) / 1000
    return dict(neck_yaw_deg=math.degrees(neck), jaw_pitch_deg=math.degrees(jaw),
                total_mass_g=total * 1000, global_com_mm=com.tolist(),
                head_and_jaw_mass_g=head_mass * 1000, head_and_jaw_mass_fraction=head_mass / total,
                head_and_jaw_com_mm=head_com.tolist(),
                head_com_horizontal_offset_from_neck_mm=float(np.linalg.norm((head_com - pivot)[:2])),
                head_and_jaw_yaw_inertia_about_neck_kg_m2=float(yaw_i),
                supported_body_head_jaw_mass_g=supported_mass * 1000,
                combined_static_hip_pitch_moment_Nm=float(hip_pitch))


def ideal_contacts(manifest, com):
    """Two ideal point contacts at the bottoms of unrotated spherical treads."""
    rocker = manifest["rocker_contact"]
    radius = rocker["radius_mm"]
    points = []
    for name in ("left_leg", "right_leg"):
        point = np.asarray(rocker["centers_global_mm"][name], dtype=float) - [0, 0, radius]
        xmin, xmax, ymin, ymax = rocker["planform_bounds_xy_mm"][name]
        if not (xmin <= point[0] <= xmax and ymin <= point[1] <= ymax):
            raise ValueError("Spherical bottom is outside the trimmed tread; contact model must be revised")
        points.append(point)
    if not np.isclose(points[0][2], points[1][2], atol=1e-5):
        raise ValueError("Neutral foot contact heights differ")
    a, b = points[0][:2], points[1][:2]
    c = np.asarray(com)[:2]
    ab = b - a
    along = float((c - a) @ ab / (ab @ ab))
    closest = a + np.clip(along, 0, 1) * ab
    return dict(ideal_ground_contacts_mm=[p.tolist() for p in points],
                ground_height_mm=float(points[0][2]),
                support_geometry="Line segment between two ideal point contacts; zero fore-aft area",
                com_projection_xy_mm=c.tolist(),
                projection_distance_to_contact_segment_mm=float(np.linalg.norm(c - closest)),
                lateral_projection_between_contacts=bool(0 <= along <= 1),
                com_height_above_contact_plane_mm=float(com[2] - points[0][2]),
                note="Rigid sphere/plane geometry only. Finite TPU contact patches, rolling equilibrium, friction and dynamics are not solved.")


def assess(manifest):
    joints = {j["name"]: j for j in manifest["joints"]}
    samples = [pose_metrics(manifest, n, j)
               for n in np.linspace(*joints["neck_yaw"]["limit_rad"], 5)
               for j in np.linspace(*joints["jaw_pitch"]["limit_rad"], 3)]
    neutral = pose_metrics(manifest)
    neutral["support_projection"] = ideal_contacts(manifest, neutral["global_com_mm"])
    coms = np.asarray([s["global_com_mm"] for s in samples])
    return dict(neutral=neutral, samples=samples,
                sampled_com_min_mm=coms.min(axis=0).tolist(), sampled_com_max_mm=coms.max(axis=0).tolist(),
                maximum_sampled_absolute_combined_hip_pitch_moment_Nm=max(
                    abs(s["combined_static_hip_pitch_moment_Nm"]) for s in samples))


def assembly_metrics(assembly):
    parts = [p for p in assembly["parts"] if p["kind"] != "coupon"]
    total = sum(p["mass_g"] for p in parts)
    com = sum((p["mass_g"] * np.asarray(p["com_mm"]) for p in parts), np.zeros(3)) / total
    head_mass = sum(p["mass_g"] for p in parts if p["link"] in ("head", "jaw"))
    if not np.isclose(total, assembly["mass_g"], atol=1e-6):
        raise ValueError("Assembly mass accounting is inconsistent")
    return dict(total_mass_g=total, global_com_mm=com.tolist(), head_and_jaw_mass_g=head_mass,
                head_and_jaw_mass_fraction=head_mass / total)


def baseline_data(assembly_path):
    assembly = read_json(assembly_path)
    output = dict(source_assembly_sha256=digest(assembly_path),
                  design_revision=assembly["parameters"].get("design_revision"),
                  neutral=assembly_metrics(assembly))
    # A review checkpoint can supply baseline tensors without reopening old CAD.
    archive = assembly_path.parent / "MicroDuckling_R03_review.zip"
    if archive.is_file():
        with zipfile.ZipFile(archive) as z:
            paths = [p for p in z.namelist() if p.endswith("cad/manifest.json")]
            if len(paths) == 1:
                manifest = json.loads(z.read(paths[0]).decode("utf-8-sig"))
                if manifest.get("source_assembly_sha256") != output["source_assembly_sha256"]:
                    raise ValueError("Baseline ZIP manifest does not match baseline assembly")
                output.update(assess(manifest))
                output["source_archive_sha256"] = digest(archive)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-assembly", type=Path, help="Optional earlier assembly JSON to compare")
    parser.add_argument("--output", type=Path, default=PROJECT / "simulation/balance_assessment.json")
    args = parser.parse_args()
    verify_export(PROJECT / "simulation")
    manifest = read_json(PROJECT / "cad/manifest.json")
    assembly = read_json(PROJECT / "cad/assembly.json")
    result = dict(status="CAD_MASS_BALANCE_ESTIMATE", walking_validated=False,
                  source_manifest_sha256=digest(PROJECT / "cad/manifest.json"),
                  design_revision=assembly["parameters"].get("design_revision"),
                  assumptions=[
                      "Estimated CAD component masses and COM tensors; not measured hardware mass/inertia.",
                      "Body and both hip joints fixed at CAD zero; sample only neck yaw and jaw pitch.",
                      "Combined hip pitch moment balances gravity on body+head+jaw; no equal-load split or single-servo continuous rating is inferred.",
                      "Ignores acceleration, impacts, friction, cable forces, electrical sag, servo heating and gear backlash.",
                      "Ideal neutral sphere/plane point contacts are not a finite flat-foot support polygon."],
                  current=assess(manifest))
    assembly_check = assembly_metrics(assembly)
    if not np.allclose(assembly_check["global_com_mm"], result["current"]["neutral"]["global_com_mm"], atol=1e-5):
        raise ValueError("Manifest neutral kinematics disagrees with assembled COM")
    if args.baseline_assembly and args.baseline_assembly.is_file():
        result["baseline"] = baseline_data(args.baseline_assembly)
        now, old = result["current"]["neutral"], result["baseline"]["neutral"]
        result["change_from_baseline"] = {key: (np.asarray(now[key]) - np.asarray(old[key])).tolist()
                                           for key in old if key in now and isinstance(old[key], (float, int, list))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "neutral": result["current"]["neutral"],
                      "change_from_baseline": result.get("change_from_baseline")}, indent=2))


if __name__ == "__main__":
    main()
