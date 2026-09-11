"""Validate the approved STL exports and create portable geometry-only 3MF files.

Run after the FreeCAD generator:
    python scripts/package_printables.py --source build/local

Outputs stay in <source>/exports. Each 3MF contains one millimetre mesh and no
slicer profile, printer settings, supports, vendor geometry or assembly aggregate.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import trimesh

PRINT_PARTS = {
    "BodyShellLeft", "BodyShellRight", "CameraBoardClamp", "CameraCradle",
    "CameraRing", "Chassis", "FacePanel", "FixedNeckSupport", "HeadFrame",
    "HeadHood", "Jaw", "LegFootLeft", "LegFootRight", "NeckCarrier",
}
COUPONS = {"SplineFitCoupon", "ClearanceCoupon"}
NAMESPACE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
CONTENT_TYPES = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
RELATIONSHIPS = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'


def write_3mf(name, mesh, path):
    ET.register_namespace("", NAMESPACE)
    tag = lambda name: "{" + NAMESPACE + "}" + name
    root = ET.Element(tag("model"), unit="millimeter")
    ET.SubElement(root, tag("metadata"), name="Title").text = name + " - FIT PROTOTYPE, not print release"
    resources = ET.SubElement(root, tag("resources"))
    obj = ET.SubElement(resources, tag("object"), id="1", type="model", name=name)
    model_mesh = ET.SubElement(obj, tag("mesh"))
    vertices = ET.SubElement(model_mesh, tag("vertices"))
    triangles = ET.SubElement(model_mesh, tag("triangles"))
    for vertex in mesh.vertices:
        ET.SubElement(vertices, tag("vertex"), x=str(vertex[0]), y=str(vertex[1]), z=str(vertex[2]))
    for face in mesh.faces:
        ET.SubElement(triangles, tag("triangle"), v1=str(face[0]), v2=str(face[1]), v3=str(face[2]))
    build = ET.SubElement(root, tag("build"))
    ET.SubElement(build, tag("item"), objectid="1")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", RELATIONSHIPS)
        archive.writestr("3D/3dmodel.model", ET.tostring(root, encoding="utf-8", xml_declaration=True))


def verify_roundtrip(path, original):
    with zipfile.ZipFile(path) as archive:
        if set(archive.namelist()) != {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}:
            raise ValueError("Unexpected 3MF package contents: " + path.name)
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    vertices = np.array([[float(vertex.get(axis)) for axis in ("x", "y", "z")] for vertex in root.findall(".//{*}vertex")])
    faces = np.array([[int(face.get(index)) for index in ("v1", "v2", "v3")] for face in root.findall(".//{*}triangle")])
    if root.get("unit") != "millimeter" or not np.array_equal(vertices, original.vertices) or not np.array_equal(faces, original.faces):
        raise ValueError("3MF changed mesh coordinates, indices or units: " + path.name)
    restored = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if not np.array_equal(restored.bounds, original.bounds) or not np.isclose(restored.volume, original.volume, rtol=1e-12, atol=1e-9):
        raise ValueError("3MF changed mesh bounds or volume: " + path.name)
    return {"3mf_roundtrip_counts_match": True, "3mf_roundtrip_vertices_and_faces_exact": True, "3mf_roundtrip_volume_matches": True, "3mf_unit": "millimeter"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "build/local")
    args = parser.parse_args()
    source = args.source.resolve()
    records = json.loads((source / "cad/assembly.json").read_text(encoding="utf-8"))["parts"]
    parts = [record for record in records if record["kind"] in {"print", "coupon"}]
    if {record["name"] for record in parts if record["kind"] == "print"} != PRINT_PARTS:
        raise ValueError("Printable-part allowlist changed; review it before packaging")
    if {record["name"] for record in parts if record["kind"] == "coupon"} != COUPONS or len(parts) != len(PRINT_PARTS | COUPONS):
        raise ValueError(f"Expected exactly {len(PRINT_PARTS)} printed parts and {len(COUPONS)} coupons")
    output = source / "exports/3mf_review"
    for path in output.glob("*"):
        if path.suffix != ".3mf" or path.stem not in PRINT_PARTS | COUPONS:
            raise ValueError("Unreviewed existing 3MF export: " + path.name)
    validated = []
    # Validate all source meshes before writing any 3MFs. Processing welds the
    # duplicate STL vertices; the resulting coordinates and triangles are then
    # carried into the 3MF without scaling, repair or geometry simplification.
    for record in sorted(parts, key=lambda part: part["name"]):
        relative = Path("cad") / ("coupons" if record["kind"] == "coupon" else "stl") / (record["name"] + ".stl")
        path = source / relative
        mesh = trimesh.load_mesh(path, process=True)
        if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
            raise ValueError("Invalid source mesh: " + record["name"])
        connected = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(mesh.faces)), min_len=1)
        cad_volume = float(record["volume_mm3"])
        volume_error = abs(float(mesh.volume) - cad_volume) / cad_volume if cad_volume > 0 else float("inf")
        result = {
            "name": record["name"], "kind": record["kind"], "source_stl": relative.as_posix(),
            "source_stl_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "watertight": bool(mesh.is_watertight), "winding_consistent": bool(mesh.is_winding_consistent),
            "positive_volume": bool(mesh.volume > 0), "connected_components": len(connected),
            "vertices": len(mesh.vertices), "faces": len(mesh.faces), "dimensions_mm": mesh.extents.tolist(),
            "mesh_volume_mm3": float(mesh.volume), "cad_volume_mm3": cad_volume,
            "cad_volume_relative_error": volume_error,
        }
        if not (result["watertight"] and result["winding_consistent"] and result["positive_volume"] and len(connected) == 1 and volume_error <= .01):
            raise ValueError("STL topology or CAD volume validation failed: " + json.dumps(result))
        validated.append((record["name"], mesh, result))
    output.mkdir(parents=True, exist_ok=True)
    report = []
    for name, mesh, result in validated:
        path = output / (name + ".3mf")
        write_3mf(name, mesh, path)
        result.update(verify_roundtrip(path, mesh))
        result["3mf_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        report.append(result)
    (source / "exports/mesh_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"printed_parts": len(PRINT_PARTS), "coupons": len(COUPONS), "3mf_files": len(report), "topology_passed": True, "roundtrip_geometry_exact": True, "maximum_cad_volume_relative_error": max(item["cad_volume_relative_error"] for item in report)}, indent=2))


if __name__ == "__main__":
    main()
