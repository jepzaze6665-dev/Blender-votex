"""Sculpt the modular block character part by part in Blender 5.2. Deterministic.

  blender -b --factory-startup --python build_modular.py

An original character: every part is designed on a shared voxel grid instead of being cut
from an image. Pivots match the earlier block rig, so existing clips still work. Writes
voxel_modular.blend, rig.json, and four review renders. The character faces +Y.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
V = 0.05
DARK, NAVY, MID, TRIM, GLOW, CORE = range(6)
PALETTE = [(0.006, 0.01, 0.045), (0.018, 0.04, 0.17), (0.045, 0.11, 0.36), (0.17, 0.36, 0.72), (0.2, 0.62, 1), (0.72, 0.93, 1)]
EMIT = [0, 0, 0, 0.02, 1.3, 2]


def rounded(x, y, z, hx, hy, hz, power=4):
    return (abs(x / hx) ** power + abs(y / hy) ** power + abs(z / hz) ** power) <= 1


def hood(x, y, z):
    cx, cy, cz = x, y + 0.03, z - 1.17
    if not rounded(cx, cy, cz, 0.37, 0.37, 0.33):
        tip = cy < -0.28 and abs(cx) < 0.12 and -0.05 < cz < 0.2 and cy > -0.42 - cz * 0.3
        return NAVY if tip else None
    opening = abs(x) < 0.26 * (1 - max(z - 1.08, 0) / 0.32) and 0.94 < z < 1.4
    if opening and y > 0.1:
        return None
    rim = abs(x) < 0.32 * (1 - max(z - 1.08, 0) / 0.42) and 0.9 < z < 1.44 and y > 0.2
    if rim:
        return TRIM
    return MID if z > 1.34 or abs(x) > 0.3 else NAVY


def face(x, y, z):
    return DARK if abs(x) < 0.27 and 0.94 < z < 1.34 and -0.1 < y < 0.14 else None


def eyes(x, y, z):
    if 1.06 < z < 1.22 and 0.06 < abs(x) < 0.17 and 0.12 < y < 0.2:
        return CORE if 1.1 < z < 1.18 and 0.09 < abs(x) < 0.14 else GLOW
    return None


def body(x, y, z):
    k = (0.86 - z) / 0.5
    half = 0.27 + k * 0.07
    if not (0.36 < z < 0.87 and rounded(x, y, 0, half, 0.24, 1, 5)):
        return None
    if 0.48 < z < 0.53:
        return TRIM if abs(x) < 0.3 else MID
    if y > 0.17 and abs(abs(x) - (0.86 - z) * 0.32) < 0.04 and z > 0.53:
        return TRIM
    return MID if z < 0.42 else NAVY


def cape(x, y, z):
    tooth = 0.31 + 0.05 * abs(math.sin(x * 11))
    if -0.34 < y < -0.24 and abs(x) < 0.28 and tooth < z < 0.84:
        return MID if abs(x) < 0.08 else NAVY
    return None


def pad(side):
    def shape(x, y, z):
        lx, lz = x - side * 0.39, z - 0.8
        if not rounded(lx, y, lz, 0.17, 0.2, 0.13):
            return None
        return TRIM if lz > 0.06 or abs(lx) > 0.13 else MID
    return shape


def hand(side):
    def shape(x, y, z):
        lx, lz = x - side * 0.55, z - 0.5
        if not rounded(lx, y, lz, 0.16, 0.16, 0.17):
            return None
        return GLOW if y > 0.1 and abs(lx) + abs(lz) < 0.06 else TRIM if -0.05 < lz < 0 else NAVY
    return shape


def foot(side):
    def shape(x, y, z):
        lx, ly = x - side * 0.21, y - 0.05
        if not (rounded(lx, ly, z - 0.1, 0.14, 0.23, 0.13) and z >= 0):
            return None
        return GLOW if ly > 0.14 and abs(lx) + abs(z - 0.11) < 0.05 else TRIM if z < 0.06 else NAVY
    return shape


def crystal(x, y, z):
    if abs(x) / 0.12 + abs(z - 0.66) / 0.17 <= 1 and 0.22 < y < 0.34:
        return CORE if abs(x) / 0.06 + abs(z - 0.66) / 0.09 <= 1 else GLOW
    return None


PARTS = {
    "Hood": (hood, (0, 0, 0.9)), "Face": (face, (0, 0, 0.9)), "Eyes": (eyes, (0, 0, 0.9)),
    "Body": (body, (0, 0, 0.62)), "Cape": (cape, (0, -0.29, 0.84)), "Crystal": (crystal, (0, 0, 0.62)),
    "PadR": (pad(1), (0.39, 0, 0.8)), "PadL": (pad(-1), (-0.39, 0, 0.8)),
    "HandR": (hand(1), (0.55, 0, 0.5)), "HandL": (hand(-1), (-0.55, 0, 0.5)),
    "FootR": (foot(1), (0.21, 0.05, 0.1)), "FootL": (foot(-1), (-0.21, 0.05, 0.1)),
}

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
scene = bpy.context.scene
materials = []
for colour, power in zip(PALETTE, EMIT):
    m = bpy.data.materials.new("M_Modular")
    tree = m.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (*colour, 1)
    shader.inputs["Emission Color"].default_value = (*colour, 1)
    shader.inputs["Emission Strength"].default_value = power
    shader.inputs["Roughness"].default_value = 0.62
    tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    materials.append(m)

SIDES = [((1, 0, 0), 0), ((-1, 0, 0), 0), ((0, 1, 0), 1), ((0, -1, 0), 1), ((0, 0, 1), 2), ((0, 0, -1), 2)]
total = 0
for name, (shape, joint) in PARTS.items():
    cells = {}
    for i in range(-16, 17):
        for j in range(-12, 13):
            for k in range(0, 34):
                level = shape((i + 0.5) * V, (j + 0.5) * V, (k + 0.5) * V)
                if level is not None:
                    cells[(i, j, k)] = level
    bm = bmesh.new()
    pivot = Vector(joint)
    for (i, j, k), level in cells.items():
        centre = Vector(((i + 0.5) * V, (j + 0.5) * V, (k + 0.5) * V)) - pivot
        for normal, axis in SIDES:
            if (i + normal[0], j + normal[1], k + normal[2]) in cells:
                continue
            n = Vector(normal)
            a = Vector((0, 1, 0)) if axis == 0 else Vector((0, 0, 1)) if axis == 1 else Vector((1, 0, 0))
            b = n.cross(a)
            c = centre + n * V / 2
            f = bm.faces.new([bm.verts.new(c + (a * p + b * q) * V / 2) for p, q in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            f.material_index = level
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = pivot
    scene.collection.objects.link(obj)
    total += len(mesh.polygons) * 2
print("BUILT", len(PARTS), "parts, triangles", total)

# Rig: the same bones and clips as the block character, plus face, eyes, and crystal.
source = json.loads((HERE.parent / "voxel-block" / "rig.json").read_text(encoding="utf-8"))
bones = [b for b in source["bones"]]
for b in bones:
    if b["name"] == "Head":
        b.update({"from": "Hood", "mesh": "Hood"})
bones += [{"name": "Face", "parent": "Head", "from": "Face", "mesh": "Face"},
          {"name": "Eyes", "parent": "Head", "from": "Eyes", "mesh": "Eyes"},
          {"name": "Crystal", "parent": "Body", "from": "Crystal", "mesh": "Crystal"}]
source["bones"] = bones
(HERE / "rig.json").write_text(json.dumps(source, indent=1), encoding="utf-8")

world = bpy.data.worlds.new("World")
scene.world = world
bg = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.02, 0.03, 0.07, 1)
wo = next((n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeOutputWorld"), None) \
    or world.node_tree.nodes.new("ShaderNodeOutputWorld")
world.node_tree.links.new(bg.outputs[0], wo.inputs["Surface"])
rig = bpy.data.objects.new("CameraRig", None)
rig.location = (0, 0, 0.78)
scene.collection.objects.link(rig)
cam = bpy.data.cameras.new("Camera")
cam.lens = 70
camera = bpy.data.objects.new("Camera", cam)
camera.parent = rig
camera.location = (0, 4.3, 0)
camera.rotation_euler = (math.pi / 2, 0, math.pi)
scene.collection.objects.link(camera)
scene.camera = camera
fill = bpy.data.lights.new("Fill", "AREA")
fill.energy, fill.size, fill.color = 240, 4, (0.85, 0.9, 1)
fo = bpy.data.objects.new("Fill", fill)
fo.parent = rig
fo.location = (1.2, 3.6, 1.6)
fo.rotation_euler = (Vector((0, 0, 0)) - fo.location).to_track_quat("-Z", "Y").to_euler()
scene.collection.objects.link(fo)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 600, 800
scene.view_settings.view_transform = "Standard"
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "voxel_modular.blend"))
renders = HERE / "renders"
renders.mkdir(exist_ok=True)
for name, angle in (("front", 0), ("side", 90), ("back", 180), ("three_quarter", 35)):
    rig.rotation_euler = (0, 0, math.radians(angle))
    scene.render.filepath = str(renders / f"{name}.png")
    bpy.ops.render.render(write_still=True)
