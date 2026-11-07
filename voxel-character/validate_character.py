"""Import the exported GLB into an empty scene and check it. Writes export/validation.json."""
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
path = HERE / "export" / "voxel_character.glb"
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
bpy.ops.import_scene.gltf(filepath=str(path))
bpy.context.view_layer.update()

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
parts = {}
for obj in meshes:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    parts[obj.name] = {"triangles": len(bm.faces), "signed_volume": round(bm.calc_volume(signed=True), 5)}
    bm.free()
report = {
    "file_kb": round(path.stat().st_size / 1024),
    "triangles": sum(p["triangles"] for p in parts.values()),
    "size_m": [round(max(p[i] for p in points) - min(p[i] for p in points), 3) for i in range(3)],
    "feet_z": round(min(p[2] for p in points), 3),
    "normals_outward": all(p["signed_volume"] > 0 for p in parts.values()),
    "part_count": len(meshes),
    "parts": parts,
}
(HERE / "export" / "validation.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("VALIDATION", json.dumps(report))
