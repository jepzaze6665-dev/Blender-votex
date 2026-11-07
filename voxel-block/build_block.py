"""Build the block character from voxels.json. Blender 5.2, deterministic.

  blender -b --factory-startup --python build_block.py

Each part is a mesh whose origin is its pivot. The character faces +Y in Blender.
Writes voxel_block.blend and four review renders.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
VOXEL = 0.028   # 56 voxels is about 1.57 m

SIDES = [
    ((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
    ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
    ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]),
    ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
    ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
    ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)]),
]

data = json.loads((HERE / "voxels.json").read_text(encoding="utf-8"))
centre, side_mid = data["centre"] + 0.5, data["side_mid"] + 0.5
palette = data["palette"]
n = len(palette)


def world(c, y, s):
    return Vector((-(c - centre) * VOXEL, -(s - side_mid) * VOXEL, y * VOXEL))


for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
scene = bpy.context.scene

base = bpy.data.images.new("T_BlockPalette", n, 1, alpha=False)
emit = bpy.data.images.new("T_BlockEmission", n, 1, alpha=False)
base_px, emit_px = [], []
for r, g, b in palette:
    k = 1.0 if b > 235 and g > 185 else 0.0
    base_px += [r / 255, g / 255, b / 255, 1]
    emit_px += [r / 255 * k, g / 255 * k, b / 255 * k, 1]
base.pixels, emit.pixels = base_px, emit_px
base.pack()
emit.pack()

material = bpy.data.materials.new("M_Block")
tree = material.node_tree
tree.nodes.clear()
out = tree.nodes.new("ShaderNodeOutputMaterial")
shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
for image, socket in ((base, "Base Color"), (emit, "Emission Color")):
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image, tex.interpolation = image, "Closest"
    tree.links.new(tex.outputs["Color"], shader.inputs[socket])
shader.inputs["Roughness"].default_value = 0.6
shader.inputs["Emission Strength"].default_value = 1.8
tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])

groups = {}
for c, y, s, mat, part in data["voxels"]:
    groups.setdefault(part, {})[(c, y, s)] = mat

total = 0
for index, name in enumerate(data["parts"]):
    cells = groups[index]
    keys = list(cells)
    mean = [sum(k[i] for k in keys) / len(keys) + 0.5 for i in range(3)]
    if name == "Head":
        joint = (centre, data["neck"], side_mid)
    elif name == "Cape":
        joint = (mean[0], max(k[1] for k in keys), mean[2])
    else:
        joint = tuple(mean)
    pivot = world(*joint)
    vert_index, verts, faces, mats = {}, [], [], []
    for (x, y, z), mat in cells.items():
        for normal, corners in SIDES:
            if (x + normal[0], y + normal[1], z + normal[2]) in cells:
                continue
            quad = []
            for cx, cy, cz in corners:
                key = (x + cx, y + cy, z + cz)
                if key not in vert_index:
                    vert_index[key] = len(verts)
                    verts.append(world(*key) - pivot)
                quad.append(vert_index[key])
            faces.append(quad[::-1])   # the grid-to-world mapping mirrors space
            mats.append(mat)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="palette")
    for poly, mat in zip(mesh.polygons, mats):
        for loop in poly.loop_indices:
            uv.uv[loop].vector = ((mat + 0.5) / n, 0.5)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = pivot
    scene.collection.objects.link(obj)
    total += len(faces) * 2
print("BUILT triangles", total)

world_data = bpy.data.worlds.new("World")
scene.world = world_data
node = world_data.node_tree.nodes.get("Background") or world_data.node_tree.nodes.new("ShaderNodeBackground")
node.inputs["Color"].default_value = (0.012, 0.016, 0.03, 1)
wout = next((x for x in world_data.node_tree.nodes if x.bl_idname == "ShaderNodeOutputWorld"), None) \
    or world_data.node_tree.nodes.new("ShaderNodeOutputWorld")
world_data.node_tree.links.new(node.outputs[0], wout.inputs["Surface"])

rig = bpy.data.objects.new("CameraRig", None)
rig.location = (0, 0, 0.8)
scene.collection.objects.link(rig)
cam = bpy.data.cameras.new("Camera")
cam.lens = 70
camera = bpy.data.objects.new("Camera", cam)
camera.parent = rig
camera.location = (0, 4.4, 0)
camera.rotation_euler = (math.pi / 2, 0, math.pi)
scene.collection.objects.link(camera)
scene.camera = camera
fill = bpy.data.lights.new("Fill", "AREA")
fill.energy, fill.size, fill.color = 260, 4, (0.85, 0.9, 1)
fill_obj = bpy.data.objects.new("Fill", fill)
fill_obj.parent = rig
fill_obj.location = (1.2, 3.6, 1.5)
fill_obj.rotation_euler = (Vector((0, 0, 0)) - fill_obj.location).to_track_quat("-Z", "Y").to_euler()
scene.collection.objects.link(fill_obj)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 600, 800
scene.view_settings.view_transform = "Standard"
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "voxel_block.blend"))
renders = HERE / "renders"
renders.mkdir(exist_ok=True)
for name, angle in (("front", 0), ("side", 90), ("back", 180), ("three_quarter", 35)):
    rig.rotation_euler = (0, 0, math.radians(angle))
    scene.render.filepath = str(renders / f"{name}.png")
    bpy.ops.render.render(write_still=True)
