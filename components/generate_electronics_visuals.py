"""Build separately licensed board visuals for the MicroDuckling viewer.

Use FreeCAD's Python. Required inputs are a full assembly metadata JSON, the
Adafruit IMU mesh export beside it, and the upstream Adafruit notice directory.
This script never opens a Pololu STEP, an old Buck mesh, or a native CAD file.

python generate_electronics_visuals.py --cad <build/local/cad> --notices <references/components_r02/notices> --output <component-assets>

SPDX-License-Identifier: Apache-2.0
The Adafruit-derived IMU output mesh is separately CC-BY-SA-3.0.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil

import FreeCAD as App
import MeshPart
import Part

V = App.Vector
GREEN, BLACK, GOLD, SILVER, TAN = "#27634b", "#25272b", "#b7a16b", "#bdc3c8", "#b9a382"
PLACEMENTS = {
    "IMU": ((-12.62, -12.7, 54.2), ((0, 1, 0), (-1, 0, 0), (0, 0, 1))),
    "ServoController": ((27, -31.115, 31.4), ((0, 1, 0), (0, 0, 1), (1, 0, 0))),
    "Buck_0": ((12, 10, 44.8), ((0, 0, 1), (0, 1, 0), (-1, 0, 0))),
    "Buck_1": ((-4, -30, 47), ((1, 0, 0), (0, 1, 0), (0, 0, 1))),
}
ADAFRUIT = {
    "IMU": {"folder": "adafruit-lsm6ds3", "title": "Adafruit LSM6DS3TR-C 6-DoF Accel + Gyro IMU - STEMMA QT / Qwiic PCB", "source": "https://github.com/adafruit/Adafruit-LSM6DS3TR-C-PCB", "board_file": "Adafruit_LSM6DS3.brd", "board_sha256": "7a51838fd1cd4c5454fbd59fff928d67bd5fff31385b1db71daac461e2c5344d"},
    "ServoController": {"folder": "adafruit-pca9685", "title": "Adafruit 16-Channel PWM Servo Driver PCB Eagle Files", "source": "https://github.com/adafruit/Adafruit-16-Channel-PWM-Servo-Driver-PCB", "board_file": "Adafruit PCA9685 rev C.brd", "board_sha256": "803e6388dd025d2ef9312a7fbe731b7fd5edbd495ca3e93b6ade830a58212da0"},
}
NOTICE_HASHES = {
    "adafruit-lsm6ds3/README.md": "c158a0f76a54a00daaec00fbe92e63520e3914085b9e445d4d5faaa42bb6d526",
    "adafruit-lsm6ds3/license.txt": "075dad5e5fc96c27014fabc269f4f5732909cffd178a486f546d982b6cf86b74",
    "adafruit-lsm6ds3/LICENSE": "e893365dfcb99ee9b2be1aa26b65888a8f1017373617232cad3caa0f65562afb",
    "adafruit-pca9685/README.md": "3ec2a90b809dbec410275d1d2e6484f7c826aa68c3be50ce7c1ff8838736c908",
    "adafruit-pca9685/license.txt": "1f63e1f4676a433423b2c2ff1ccd9e80093f341f10b81f0ac0106342bc7bbe89",
}
POLOLU_SOURCES = {
    "Buck_0": ["https://www.pololu.com/product/2851", "https://www.pololu.com/file/0J1436/d24v50f5-step-down-voltage-regulator-dimensions.pdf", "https://www.pololu.com/product/2851/pictures"],
    "Buck_1": ["https://www.pololu.com/product/2831/specs", "https://www.pololu.com/product/2831/pictures"],
}


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, V(x, y, z))


def cylinder(x, y, z, radius, height):
    return Part.makeCylinder(radius, height, V(x, y, z))


def polygon_box(x, y, z, width, depth, height, corner):
    points = [(x + corner, y), (x + width - corner, y), (x + width, y + corner), (x + width, y + depth - corner), (x + width - corner, y + depth), (x + corner, y + depth), (x, y + depth - corner), (x, y + corner)]
    wire = Part.makePolygon([V(a, b, z) for a, b in points + points[:1]])
    return Part.Face(wire).extrude(V(0, 0, height))


def add(items, name, shape, color, metalness=0, roughness=.5):
    if shape.isNull() or not shape.isValid():
        raise ValueError("Invalid original visual primitive: " + name)
    items.append({"name": name, "shape": shape, "color": color, "roughness": roughness, "metalness": metalness})


def pads_and_board(items, width, depth, thickness, pads, holes=()):
    board = polygon_box(0, 0, 0, width, depth, thickness, .3)
    all_holes = list(holes) + [(x, y, 1.02) for x, y in pads]
    for x, y, diameter in all_holes:
        board = board.cut(cylinder(x, y, -.1, diameter / 2, thickness + .2))
    add(items, "original_PCB", board, GREEN)
    for index, (x, y, diameter) in enumerate(all_holes):
        outer = diameter / 2 + (.42 if diameter < 1.5 else .45)
        for side, z in (("top", thickness), ("bottom", -.04)):
            ring = cylinder(x, y, z, outer, .04).cut(cylinder(x, y, z - .01, diameter / 2, .07))
            add(items, f"plated_pad_{index}_{side}", ring, GOLD, .7, .3)


def passive(items, name, x, y, z, dx, dy, height, color=TAN):
    end = min(.3, dy / 4)
    add(items, name, box(x, y + end, z, dx, dy - end * 2, height), color)
    for side, yy in (("a", y), ("b", y + dy - end)):
        add(items, name + "_termination_" + side, box(x, yy, z, dx, end, height), SILVER, .65, .3)


def chip(items, name, x, y, z, dx, dy, height, count=6):
    add(items, name, polygon_box(x, y, z, dx, dy, height, .15), BLACK)
    for i in range(count):
        yy = y + .35 + i * (dy - .7) / (count - 1)
        for side, xx in (("left", x - .35), ("right", x + dx)):
            add(items, f"{name}_{side}_lead_{i}", box(xx, yy - .12, z, .35, .24, .2), SILVER, .7, .25)


def large_regulator():
    """Original primitives. Board/hole dimensions are PDF callouts in mm/mil.

    Component bodies/XY/lead locations are deliberately approximate photo-based
    visual details, with no circuit artwork, text, logos or copied CAD surfaces.
    """
    items = []
    width, depth, thickness = .7 * 25.4, .8 * 25.4, 1.57
    holes = [(85 * .0254, 85 * .0254, 2.18), (615 * .0254, 715 * .0254, 2.18)]
    pads = [(225 * .0254 + i * 2.54, 1.27) for i in range(5)]
    pads_and_board(items, width, depth, thickness, pads, holes)
    add(items, "shielded_inductor", polygon_box(1.25, 12.6, thickness, 6.9, 6.6, 4.5, .55), BLACK)
    for x in (1.15, 7.65):
        add(items, "inductor_contact_" + str(x), box(x, 14.1, thickness, .65, 3.4, .3), SILVER, .65)
    for name, x, y, radius, height in (("input_capacitor", 4.7, 8.3, 3.0, 4.5), ("output_capacitor", 13.15, 6.8, 3.1, 6.1)):
        add(items, name + "_base", cylinder(x, y, thickness, radius + .12, .35), BLACK)
        add(items, name + "_can", cylinder(x, y, thickness + .35, radius, height - .35), SILVER, .65, .35)
        add(items, name + "_top", cylinder(x, y, thickness + height, radius - .15, .025), "#d9dde0", .4, .35)
    for i, (x, y, dx, dy) in enumerate(((9, 15.1, 1.4, 2.8), (11.2, 15.1, 1.5, 2.8), (11.9, 12.4, 2.8, 1.5), (8.4, 6.4, 1.3, 2.6), (7.4, 3, 2.7, 1.3))):
        passive(items, f"ceramic_{i}", x, y, thickness, dx, dy, 1.1)
    chip(items, "underside_controller", 4.2, 7.6, -1.1, 3.3, 3.3, 1.1, 5)
    chip(items, "underside_switch", 10.8, 13.0, -.85, 3.7, 3.0, .85, 4)
    return items, [width, depth, thickness], holes


def small_regulator():
    """Original photo-informed visual model using the published 0.5 x 0.7in PCB.

    PCB thickness1.0mm, package XY and component heights are assumptions; the
    overall nominal height is informed by the public 0.14in product spec.
    """
    items = []
    width, depth, thickness = .5 * 25.4, .7 * 25.4, 1.0
    pads = [(1.27 + i * 2.54, 1.27) for i in range(5)] + [(11.43, 16.51)]
    pads_and_board(items, width, depth, thickness, pads)
    add(items, "shielded_inductor", polygon_box(6.15, 3.3, thickness, 5.8, 6.0, 2.55, .9), BLACK)
    for y in (3.25, 8.9):
        add(items, "inductor_contact_" + str(y), box(6.6, y, thickness, 4.8, .5, .3), SILVER, .65)
    chip(items, "regulator_IC", 1.15, 8.0, thickness, 3.7, 3.8, .85, 6)
    for i, (x, y, dx, dy) in enumerate(((8.5, 13.2, 2.2, 1.5), (8.5, 15.0, 2.2, 1.5), (5.7, 12.3, 2.0, 1.5), (5.7, 14.2, 2.0, 1.5), (1.65, 3.0, 2.0, 2.4), (4.6, 6.0, 1.1, 1.5))):
        passive(items, f"ceramic_{i}", x, y, thickness, dx, dy, .9)
    for i, (x, y) in enumerate(((1.0, 13.9), (3.0, 15.1), (1.2, 6.2))):
        passive(items, f"resistor_{i}", x, y, thickness, .85, 1.5, .5, BLACK)
    return items, [width, depth, thickness], []


def export_mesh(items, name):
    origin, axes = PLACEMENTS[name]
    transform = App.Matrix()
    for column, axis in enumerate(axes, 1):
        for row, value in enumerate(axis, 1):
            setattr(transform, f"A{row}{column}", value)
    transform.A14, transform.A24, transform.A34 = origin
    payload = {"positions": [], "indices": [], "materials": [], "groups": []}
    for item in items:
        shape = item["shape"].copy()
        shape.transformShape(transform, True)
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.045, AngularDeflection=.16, Relative=False)
        vertices, faces = mesh.Topology
        start, offset = len(payload["indices"]), len(payload["positions"]) // 3
        payload["positions"].extend(round(c, 5) for vertex in vertices for c in vertex)
        payload["indices"].extend(i + offset for face in faces for i in face)
        payload["groups"].append({"start": start, "count": len(faces) * 3, "materialIndex": len(payload["materials"])})
        payload["materials"].append({key: item[key] for key in ("name", "color", "roughness", "metalness")})
    return payload


def validate(mesh):
    assert len(mesh["positions"]) % 3 == len(mesh["indices"]) % 3 == 0
    assert all(math.isfinite(v) for v in mesh["positions"])
    assert all(isinstance(i, int) and 0 <= i < len(mesh["positions"]) // 3 for i in mesh["indices"])
    end = 0
    for group in mesh["groups"]:
        assert group["start"] == end and group["count"] > 0 and group["count"] % 3 == 0
        assert 0 <= group["materialIndex"] < len(mesh["materials"])
        end += group["count"]
    assert end == len(mesh["indices"])
    points = [mesh["positions"][i:i + 3] for i in range(0, len(mesh["positions"]), 3)]
    bbox = [min(v[axis] for v in points) for axis in range(3)] + [max(v[axis] for v in points) for axis in range(3)]
    return bbox


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cad", type=Path, required=True)
    parser.add_argument("--notices", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    out = args.output.resolve()
    (out / "meshes").mkdir(parents=True, exist_ok=True)
    assembly = json.loads((args.cad / "assembly.json").read_text(encoding="utf-8"))
    source_records = {record["name"]: record for record in assembly["parts"]}
    records, notices, checks = [], [], []
    for relative, expected in NOTICE_HASHES.items():
        path = args.notices / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Upstream notice changed: " + relative)
        destination = out / "licenses" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    for name in ("IMU", "Buck_0"):
        if source_records[name]["pcb_basis_global"] != [list(axis) for axis in PLACEMENTS[name][1]]:
            raise ValueError("Assembly datum orientation changed; review placement: " + name)
        record = copy.deepcopy(source_records[name])
        if name in ADAFRUIT:
            source = args.cad / "meshes" / (name + ".json")
            mesh = json.loads(source.read_text(encoding="utf-8"))
            spec = ADAFRUIT[name]
            license_id = "CC-BY-SA-3.0"
            changes = "Adapted Eagle board outlines, holes, pads and package positions into colored 3D meshes; generic component heights and fitted connectors were added; meshes placed rigidly in the MicroDuckling assembly. Not manufacturer mechanical CAD."
            notice = {"name": name, "license": license_id, "license_url": "https://creativecommons.org/licenses/by-sa/3.0/", "author": "Limor Fried/Ladyada for Adafruit Industries", "title": spec["title"], "source_url": spec["source"], "source_board_file": spec["board_file"], "source_board_sha256": spec["board_sha256"], "adaptation_author": "MicroDuckling contributors", "adaptation_changes": changes, "upstream_notice_directory": "licenses/" + spec["folder"], "mesh_path": "meshes/" + name + ".json"}
            record["geometry_provenance"] = "Adafruit Eagle-derived adaptation; exact existing viewer mesh"
            shutil.copyfile(source, out / "meshes" / (name + ".json"))
        else:
            items, pcb, holes = large_regulator() if name == "Buck_0" else small_regulator()
            mesh = export_mesh(items, name)
            license_id = "Apache-2.0"
            record["color"] = GREEN
            record["pcb_dimensions_mm"] = pcb
            record["volume_mm3"] = sum(item["shape"].Volume for item in items)
            record["note"] = "Original dimension-based visual approximation with photo-informed generic components. No manufacturer STEP or old regulator mesh was read, traced, simplified or converted. Board datum/orientation matches the current assembly; component shape/placement and thickness details are approximate. Bare solder pads are shown; optional headers are not fitted. Display geometry is not qualified for fit, collision, electrical, thermal or manufacturing checks. Mass and COM retain the full engineering assembly estimates."
            record["geometry_provenance"] = "Original procedural primitives based on published dimensions and photos"
            record["dimension_sources"] = POLOLU_SOURCES[name]
            record["mount_holes_local_mm"] = holes
            (out / "meshes" / (name + ".json")).write_text(json.dumps(mesh, separators=(",", ":")), encoding="utf-8", newline="\n")
            notice = {"name": name, "license": license_id, "license_url": "https://www.apache.org/licenses/LICENSE-2.0", "author": "MicroDuckling contributors", "title": "Original visual approximation of " + ("Pololu D24V50F5" if name == "Buck_0" else "Pololu D24V10F5"), "source_urls_for_facts_and_visual_reference": POLOLU_SOURCES[name], "creation_method": "Independent hand-authored boxes, cylinders, chamfered polygons, holes and generic component leads; no Pololu STEP/old mesh read or derivative geometry", "trademark_note": "Product names identify the represented hardware; no manufacturer endorsement or copied branding is implied.", "mesh_path": "meshes/" + name + ".json"}
        bbox = validate(mesh)
        record.update({"bbox": bbox, "dimensions_mm": [bbox[i + 3] - bbox[i] for i in range(3)], "material_groups": len(mesh["materials"]), "mesh_license": license_id, "mesh_path": "meshes/" + name + ".json", "pcb_origin_global_mm": list(PLACEMENTS[name][0]), "mass_estimates_scope": "full_physical_assembly", "visual_geometry_only": True})
        notice["mesh_sha256"] = hashlib.sha256((out / record["mesh_path"]).read_bytes()).hexdigest()
        notices.append(notice)
        records.append(record)
        checks.append({"name": name, "vertices": len(mesh["positions"]) // 3, "triangles": len(mesh["indices"]) // 3, "material_groups": len(mesh["groups"]), "bbox_mm": bbox, "complete_material_coverage": True, "mass_estimate_preserved": record["mass_g"] == source_records[name]["mass_g"], "com_estimate_preserved": record["com_mm"] == source_records[name]["com_mm"]})
    (out / "records.json").write_text(json.dumps({"schema_version": 1, "units": "mm", "coordinate_system": "MicroDuckling R06 CAD assembly coordinates", "mass_estimates_scope": "full_physical_assembly", "parts": records}, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "NOTICE.json").write_text(json.dumps({"schema_version": 1, "assets": notices, "collection_note": "Individual asset licenses apply. Adafruit mesh adaptations remain CC-BY-SA-3.0. Original Pololu approximations and this generator are Apache-2.0; no license is asserted over the represented commercial hardware."}, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "validation.json").write_text(json.dumps({"parts": checks, "part_count": len(checks), "pololu_step_or_prior_mesh_used": False}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
