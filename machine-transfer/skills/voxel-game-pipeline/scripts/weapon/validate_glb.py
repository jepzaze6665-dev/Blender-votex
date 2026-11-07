"""Import the exported GLB into an empty scene and check what actually arrived.

  blender -b --factory-startup --python validate_glb.py

Writes export/validation.json. Signed volume above zero means normals face outward.
"""
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
path = HERE / "export" / "voxel_weapon.glb"

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
bpy.ops.import_scene.gltf(filepath=str(path))
bpy.context.view_layer.update()

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
low = [min(p[i] for p in points) for i in range(3)]
high = [max(p[i] for p in points) for i in range(3)]

parts = []
for obj in meshes:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    parts.append({
        "name": obj.name,
        "triangles": len(bm.faces),
        "signed_volume": round(bm.calc_volume(signed=True), 6),
        "uv_sets": [u.name for u in obj.data.uv_layers],
        "materials": [m.name for m in obj.data.materials],
    })
    bm.free()

material = bpy.data.materials.get("M_Voxel")
shader = next(n for n in material.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
images = [{"name": i.name, "size": list(i.size)} for i in bpy.data.images if i.size[0] > 0]
report = {
    "file_kb": round(path.stat().st_size / 1024),
    "objects": len(meshes),
    "triangles": sum(p["triangles"] for p in parts),
    "size_m": [round(h - l, 3) for l, h in zip(low, high)],
    "origin_inside_bounds": all(l <= 0 <= h for l, h in zip(low, high)),
    "normals_outward": all(p["signed_volume"] > 0 for p in parts),
    "base_colour_textured": shader.inputs["Base Color"].is_linked,
    "emission_textured": shader.inputs["Emission Color"].is_linked,
    "emission_strength": round(shader.inputs["Emission Strength"].default_value, 3),
    "images": images,
    "parts": parts,
}
(HERE / "export" / "validation.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("VALIDATION", json.dumps({k: v for k, v in report.items() if k != "parts"}))
print("PARTS", json.dumps(parts))
