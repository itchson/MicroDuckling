"""Render the complete public mesh collection with Blender.

blender --background --factory-startup --python-exit-code 1 --python scripts/render_public_cad.py
Options follow Blender's -- separator. A private checkpoint can be saved with
--checkpoint <path>; no Blender scene is required by the public package.
The 100% exploded layout is evaluated by Node from viewer/lib/explode.ts.
Install viewer dependencies first; use --node to select a Node 22.18+ executable.
Rendered PNGs are CC-BY-SA-3.0; see assets/renders/README.md for credits.
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def material_layout(mesh, record):
    materials, groups = mesh.get("materials"), mesh.get("groups")
    count = len(mesh["indices"])
    if count % 3:
        raise ValueError("Incomplete triangle in " + record["name"])
    if not materials and not groups:
        return [{"name": record["name"], "color": record["color"], "roughness": .45 if record["kind"] == "hardware" else .65, "metalness": .6 if record["color"] == "#8d9398" else 0}], [{"start": 0, "count": count, "materialIndex": 0}]
    if not materials or not groups:
        raise ValueError("Both materials and groups are required")
    end = 0
    for group in sorted(groups, key=lambda item: item["start"]):
        start, size, index = group["start"], group["count"], group["materialIndex"]
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (start, size, index)) or start != end or size <= 0 or start % 3 or size % 3 or not 0 <= index < len(materials):
            raise ValueError("Invalid CAD material group")
        end = start + size
    if end != count:
        raise ValueError("Material groups must cover every triangle exactly once")
    return materials, groups


def make_material(name, color, roughness=.5, metalness=0):
    rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb)
    material = bpy.data.materials.new(name)
    material.diffuse_color = linear + (1,)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = material.diffuse_color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metalness
    return material


def cad_normals(mesh):
    """Smooth adjacent CAD facets within thirty degrees; preserve hard edges."""
    adjacent = [[] for _ in mesh.vertices]
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        for vertex in polygon.vertices:
            adjacent[vertex].append((polygon.normal.copy(), polygon.area))
    normals = []
    for polygon in mesh.polygons:
        for vertex in polygon.vertices:
            normal = Vector((0, 0, 0))
            for candidate, weight in adjacent[vertex]:
                if candidate.dot(polygon.normal) > math.cos(math.radians(30)):
                    normal += candidate * weight
            normals.append(normal.normalized())
    mesh.normals_split_custom_set(normals)


def viewer_explosion(root, records, node):
    """Run the viewer implementation directly at neutral joints and 100%."""
    sources = [root / "viewer/lib/explode.ts", root / "viewer/lib/robot.ts"]
    hashes = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    script = """
import {explodedLayout} from './lib/explode.ts';
let input='';for await(const chunk of process.stdin)input+=chunk;
const data=JSON.parse(input);
const offsets=Object.fromEntries([...explodedLayout(data,{},5)].map(([name,value])=>[name,value.toArray()]));
process.stdout.write(JSON.stringify(offsets));
"""
    # At zero joint angles every joint matrix is identity. Supplying null joints
    # avoids needing duplicate kinematics while retaining identical CAD bounds.
    data = {"parts": [dict(record, joint=None) for record in records], "joints": {}}
    result = subprocess.run([node, "--experimental-strip-types", "--input-type=module", "-e", script], input=json.dumps(data), text=True, capture_output=True, check=True, cwd=root / "viewer")
    offsets = json.loads(result.stdout)
    if set(offsets) != {record["name"] for record in records}:
        raise ValueError("Viewer explosion returned an unexpected part set")
    for value in offsets.values():
        if len(value) != 3 or not all(math.isfinite(v) for v in value):
            raise ValueError("Invalid viewer explosion offset")
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != hashes[path.relative_to(root).as_posix()] for path in sources):
        raise RuntimeError("Viewer layout changed while rendering; run again")
    return offsets, {"source": "viewer/lib/explode.ts", "source_sha256": hashes, "amount": 1, "gap_mm": 5, "joint_angles_deg": {}, "part_count": len(offsets)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--cad", type=Path, default=root / "cad")
    parser.add_argument("--components", type=Path, default=root / "components")
    parser.add_argument("--node", default="node")
    parser.add_argument("--output", type=Path, default=root / "assets/renders")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--device", choices=("auto", "optix", "cpu"), default="auto")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--width", type=int, default=1800)
    parser.add_argument("--height", type=int, default=1600)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    data = json.loads((args.cad / "assembly.json").read_text(encoding="utf-8"))
    mechanical_records = [record for record in data["parts"] if record["kind"] != "coupon"]
    board_names = {"IMU", "ServoController", "Buck_0", "Buck_1"}
    if board_names & {record["name"] for record in mechanical_records}:
        raise ValueError("Use the sanitized public CAD package, not the source assembly")
    if not data.get("public_preview"):
        raise ValueError("Missing public preview provenance")
    component_data = json.loads((args.components / "records.json").read_text(encoding="utf-8"))
    component_notices = json.loads((args.components / "NOTICE.json").read_text(encoding="utf-8"))
    component_records = component_data["parts"]
    if {record["name"] for record in component_records} != board_names:
        raise ValueError("Expected the four separately licensed component visuals")
    records = mechanical_records + component_records
    if len(records) != 91 or len({record["name"] for record in records}) != len(records):
        raise ValueError("Expected 91 unique assembled parts")
    source_manifest_sha256 = {
        "cad/assembly.json": hashlib.sha256((args.cad / "assembly.json").read_bytes()).hexdigest(),
        "components/records.json": hashlib.sha256((args.components / "records.json").read_bytes()).hexdigest(),
        "components/NOTICE.json": hashlib.sha256((args.components / "NOTICE.json").read_bytes()).hexdigest(),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = .001
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    preferences = bpy.context.preferences.addons["cycles"].preferences
    try:
        preferences.compute_device_type = "OPTIX"
        preferences.refresh_devices()
    except (TypeError, RuntimeError):
        if args.device == "optix":
            raise
    for device in preferences.devices:
        device.use = args.device != "cpu" and device.type == "OPTIX"
    use_optix = any(device.use for device in preferences.devices)
    if args.device == "optix" and not use_optix:
        raise RuntimeError("Requested OptiX device is unavailable")
    scene.cycles.device = "GPU" if use_optix else "CPU"
    engine_label = "Blender Cycles OptiX" if use_optix else "Blender Cycles CPU"
    print("Render device: " + engine_label, flush=True)
    objects, mesh_hashes, mesh_paths = {}, {}, {}
    for record in records:
        is_component = record["name"] in board_names
        path = (args.components if is_component else args.cad) / "meshes" / (record["name"] + ".json")
        mesh_paths[record["name"]] = ("components" if is_component else "cad") + "/meshes/" + record["name"] + ".json"
        mesh_hashes[record["name"]] = hashlib.sha256(path.read_bytes()).hexdigest()
        if is_component:
            notice = next((entry for entry in component_notices["assets"] if entry["name"] == record["name"]), None)
            if not notice or notice["mesh_sha256"] != mesh_hashes[record["name"]]:
                raise ValueError("Component attribution/hash mismatch: " + record["name"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        positions, indices = payload["positions"], payload["indices"]
        record["bbox"] = [min(positions[axis::3]) for axis in range(3)] + [max(positions[axis::3]) for axis in range(3)]
        mesh = bpy.data.meshes.new(record["name"])
        mesh.from_pydata([positions[i:i + 3] for i in range(0, len(positions), 3)], [], [indices[i:i + 3] for i in range(0, len(indices), 3)])
        mesh.update()
        obj = bpy.data.objects.new(record["name"], mesh)
        obj["cad_part_name"] = record["name"]
        obj["cad_mesh_sha256"] = mesh_hashes[record["name"]]
        scene.collection.objects.link(obj)
        objects[record["name"]] = obj
        materials, groups = material_layout(payload, record)
        for index, material in enumerate(materials):
            mesh.materials.append(make_material(f"{record['name']}_{index}", material["color"], material.get("roughness", .5), material.get("metalness", 0)))
        for group in groups:
            for index in range(group["start"] // 3, (group["start"] + group["count"]) // 3):
                mesh.polygons[index].material_index = group["materialIndex"]
        cad_normals(mesh)
    translations, exploded_layout = viewer_explosion(root, records, args.node)
    world = scene.world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.88, .92, 1.0, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .45
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, -.18))
    floor = bpy.context.object
    floor.name = "StudioFloor"
    floor.data.materials.append(make_material("StudioFloor", "#cad3dd", .8))
    lights = []
    for name, location, power, size in [
        ("Key", (180, -180, 380), 230000, 240),
        ("Fill", (80, 250, 240), 130000, 200),
        ("Rim", (-200, -20, 320), 190000, 170),
    ]:
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size = power, "DISK", size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector((0, 0, 90)) - obj.location).to_track_quat("-Z", "Y").to_euler()
        lights.append((obj, Vector(location), power, size))
    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    camera_data.clip_end = 5000
    scene.render.resolution_x, scene.render.resolution_y = args.width, args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 1.1
    scene.render.film_transparent = False

    def render(name, direction):
        bpy.context.view_layer.update()
        bounds = [obj.matrix_world @ Vector(corner) for obj in objects.values() for corner in obj.bound_box]
        low = Vector([min(corner[axis] for corner in bounds) for axis in range(3)])
        high = Vector([max(corner[axis] for corner in bounds) for axis in range(3)])
        target = (low + high) / 2
        floor.location.z = low.z - .18
        # Match studio illumination to the extent of each view; the expanded
        # layout can extend below the neutral ground plane and far past its lamps.
        lighting_scale = max(high - low) / 150
        for obj, location, power, size in lights:
            obj.location = target + (location - Vector((0, 0, 75))) * lighting_scale
            obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
            obj.data.energy = power * lighting_scale ** 2
            obj.data.size = size * lighting_scale
        direction = Vector(direction).normalized()
        camera.location = target + direction * 650
        camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        inverse = camera.rotation_euler.to_matrix().transposed()
        projected = [inverse @ (corner - target) for corner in bounds]
        width = max(v.x for v in projected) - min(v.x for v in projected)
        height = max(v.y for v in projected) - min(v.y for v in projected)
        center = Vector(((max(v.x for v in projected) + min(v.x for v in projected)) / 2, (max(v.y for v in projected) + min(v.y for v in projected)) / 2, 0))
        camera.location += camera.rotation_euler.to_matrix() @ center
        camera_data.ortho_scale = max(width, height * args.width / args.height) * 1.18
        scene.render.filepath = str(args.output / (name + ".png"))
        bpy.ops.render.render(write_still=True)

    render("assembled", (250, -310, 112))
    assembled_camera = (camera.location.copy(), camera.rotation_euler.copy(), camera_data.ortho_scale)
    assembled_lights = [(obj.location.copy(), obj.rotation_euler.copy(), obj.data.energy, obj.data.size) for obj, *_ in lights]
    assembled_floor_z = floor.location.z
    for record in records:
        offset = translations[record["name"]]
        objects[record["name"]].location = offset
    render("exploded", (250, -310, 160))
    for obj in objects.values():
        obj.location = (0, 0, 0)
    camera.location, camera.rotation_euler, camera_data.ortho_scale = assembled_camera
    floor.location.z = assembled_floor_z
    for (obj, *_), (location, rotation, energy, size) in zip(lights, assembled_lights):
        obj.location, obj.rotation_euler, obj.data.energy, obj.data.size = location, rotation, energy, size
    scene["public_preview"] = True
    scene["omitted_components"] = ""
    scene["render_license"] = "CC-BY-SA-3.0"
    if args.checkpoint:
        args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.checkpoint.resolve()))
    evidence = {"geometry_source": ["cad/meshes/*.json", "components/meshes/*.json"], "geometry_modified": False, "assembled_part_count": len(objects), "mechanical_part_count": len(mechanical_records), "component_part_count": len(component_records), "omitted_components": [], "coupons_rendered": False, "engine": engine_label, "samples": args.samples, "resolution": [args.width, args.height], "renders": ["assembled.png", "exploded.png"], "mesh_sha256": mesh_hashes, "mesh_paths": mesh_paths, "source_manifest_sha256": source_manifest_sha256, "exploded_translation_mm": translations, "exploded_layout": exploded_layout, "license": "CC-BY-SA-3.0", "license_url": "https://creativecommons.org/licenses/by-sa/3.0/", "attribution": {"notice": "components/NOTICE.json", "original_designers": "Limor Fried/Ladyada for Adafruit Industries", "adaptation_credit": "MicroDuckling contributors; colored 3D adaptations and scene rendering"}}
    (args.output / "render_provenance.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rendered_parts": len(objects), "renders": evidence["renders"], "geometry_modified": False}))


if __name__ == "__main__":
    main()
