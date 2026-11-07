"""Sculpt the crystal wings in Blender 5.2. Deterministic.

  blender -b --factory-startup --python build_wings.py

Built in the character's model space, facing +Y with the wings behind it. Object names
carry the tier layers: Frame, Primary (tier 1), Secondary, Core, Gem (2), Covert, Shard (3).
FoldR and FoldL carry no keys, so the game can fold the wings over the flap animation.
Writes voxel_wings.blend, export/voxel_wings.glb, and export/wings_preview.png.
"""
import math
import os
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
V, LOOP = 0.06, 48
SLIM = os.environ.get("WING_SLIM") == "1"   # tapered variant, written to *_slim files
SUFFIX = "_slim" if SLIM else ""
rng = random.Random(9)
PALETTE = [(0.008, 0.02, 0.1), (0.016, 0.05, 0.24), (0.03, 0.14, 0.6), (0.07, 0.34, 0.95), (0.18, 0.6, 1), (0.48, 0.84, 1), (0.9, 0.98, 1)]
EMIT = [0, 0, 0.05, 0.14, 0.26, 0.36, 0.5]

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
scene = bpy.context.scene
scene.render.fps = 24
scene.frame_start, scene.frame_end = 1, LOOP + 1
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"

materials = []
for colour, power in zip(PALETTE, EMIT):
    m = bpy.data.materials.new("M_Wing")
    tree = m.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (*colour, 1)
    shader.inputs["Emission Color"].default_value = (*colour, 1)
    shader.inputs["Emission Strength"].default_value = power
    shader.inputs["Roughness"].default_value = 0.42
    tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    materials.append(m)

collection = bpy.data.collections.new("Wings")
scene.collection.children.link(collection)
root = bpy.data.objects.new("WingsRoot", None)
collection.objects.link(root)
SIDES = [((1, 0, 0), (0, 1, 0)), ((-1, 0, 0), (0, 1, 0)), ((0, 1, 0), (0, 0, 1)), ((0, -1, 0), (0, 0, 1)), ((0, 0, 1), (1, 0, 0)), ((0, 0, -1), (1, 0, 0))]
triangles = 0


def mesh_object(name, cells, parent, location=(0, 0, 0), size=V):
    """cells: {(i, j, k): level}. Builds exposed faces only."""
    global triangles
    bm = bmesh.new()
    for (i, j, k), level in cells.items():
        centre = Vector((i, j, k)) * size
        for normal, axis in SIDES:
            if (i + normal[0], j + normal[1], k + normal[2]) in cells:
                continue
            n, a = Vector(normal), Vector(axis)
            b = n.cross(a)
            c = centre + n * size / 2
            face = bm.faces.new([bm.verts.new(c + (a * p + b * q) * size / 2) for p, q in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            face.material_index = level
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    triangles += len(mesh.polygons) * 2
    return obj


def feather(length, width, base_level, tip_level):
    """A faceted blade along +X, in the XZ plane, widest a third of the way out."""
    cells = {}
    steps = int(length / V)
    for u in range(steps):
        t = u / steps
        half = width * (math.sin(min(t / 0.38, 1) * math.pi / 2) ** 0.7) * (1 - max(t - 0.38, 0) / 0.62) ** 0.8
        rows = max(1, round(half / V))
        for w in range(-rows, rows + 1):
            edge = abs(w) / max(rows, 1)
            level = round(base_level + (min(tip_level, 5) - base_level) * t ** 1.25)
            if tip_level == 6 and (t > 0.86 or (t > 0.62 and edge > 0.78)):
                level = 6                                 # white only along the tip and edge
            depth = 1 if edge < 0.65 else 0
            for d in range(-depth, depth + 1):
                cells[(u, d, w)] = level
    return cells


def diamond(radius, tall):
    cells = {}
    for i in range(-radius, radius + 1):
        for k in range(-tall, tall + 1):
            for j in (-1, 0, 1):
                if abs(i) / (radius + 0.5) + abs(k) / (tall + 0.5) + abs(j) * 0.3 <= 1:
                    edge = abs(i) / (radius + 0.5) + abs(k) / (tall + 0.5)
                    cells[(i, j, k)] = 6 if edge < 0.42 else 5 if edge < 0.72 else 4
    return cells


# Body-side centre crystal.
core = mesh_object("Core", diamond(3, 8), root, (0, -0.44, 0.82))
pieces = []
for side, label in ((1, "R"), (-1, "L")):
    fold = bpy.data.objects.new(f"Fold{label}", None)
    collection.objects.link(fold)
    fold.parent = root
    fold.location = (side * 0.16, -0.42, 0.98)
    wing = bpy.data.objects.new(f"Wing{label}", None)
    collection.objects.link(wing)
    wing.parent = fold
    # Arm of the wing: a thick dark frame from the back up to the shoulder peak.
    frame = {}
    arm = [(0, 0), (4, 2), (8, 5), (12, 9), (14, 11)]
    for (x0, z0), (x1, z1) in zip(arm, arm[1:]):
        for s in range(9):
            x, z = round(x0 + (x1 - x0) * s / 8), round(z0 + (z1 - z0) * s / 8)
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    if abs(dx) + abs(dz) <= 3:
                        frame[(side * (x + dx), -4, z + dz)] = 1 if abs(dz) < 2 else 2
                        frame[(side * (x + dx), -3, z + dz)] = 1
    mesh_object(f"Frame{label}", frame, wing)
    mesh_object(f"Gem{label}", diamond(1, 3), wing, (side * 0.56, -0.3, 0.44))
    def layer(name, count, top, sweep, lengths, width, base, tip_level, depth, arm_x, arm_z, tips=False):
        for i in range(count):
            k = i / (count - 1)
            angle = top - sweep * k
            length = lengths[0] + (lengths[1] - lengths[0]) * math.sin(k * math.pi) ** 0.7 - lengths[2] * k
            if SLIM:   # long upper feathers, a narrow fan, and a short lower edge
                angle = top + 16 - sweep * 0.72 * k
                length = lengths[1] * 1.15 * (1 - 0.64 * k ** 1.2)
            x, z = arm_x - k * (arm_x - 0.24), arm_z - k * arm_z
            rad = math.radians(angle if side > 0 else 180 - angle)
            obj = mesh_object(f"{name}{label}{i}", feather(length, width * (0.8 if SLIM else 1), base, tip_level), wing,
                              (side * x, depth + (i % 2) * 0.05, z))
            obj.rotation_euler = (0, -rad, 0)
            if tips:
                tip = bpy.data.objects.new(f"Tip{label}{i}", None)
                collection.objects.link(tip)
                tip.parent = obj
                tip.location = (length * 0.98, 0, 0)
            pieces.append((obj, -rad, k * 0.7))

    # Three overlapping panels: long primaries, mid feathers, and short coverts by the frame.
    layer("Primary", 12, 56, 142, (1.65, 2.05, 0.35), 0.3, 2, 6, 0.0, 0.8, 0.64, tips=True)
    layer("Secondary", 10, 44, 138, (0.98, 1.22, 0.3), 0.23, 2, 5, -0.1, 0.72, 0.5)
    layer("Covert", 9, 34, 130, (0.56, 0.68, 0.18), 0.17, 1, 4, -0.18, 0.66, 0.4)
    for frame_no in range(1, LOOP + 2, 4):
        phase = (frame_no - 1) / LOOP * math.tau
        wing.rotation_euler = (0, side * math.sin(phase) * 0.06, side * (math.sin(phase) * 0.08 - 0.05))
        wing.keyframe_insert("rotation_euler", frame=frame_no)
    for n in range(8):
        a = math.radians(rng.uniform(-20, 72) if SLIM else rng.uniform(-82, 62))
        r = rng.uniform(2.15, 2.75)
        x, z = side * math.cos(a) * r, math.sin(a) * r + 0.5
        shard = mesh_object(f"Shard{label}{n}", diamond(1, 3 + n % 2), wing, (x, -0.1, z))
        base = Vector((x, -0.1, z))
        for frame_no in range(1, LOOP + 2, 6):
            phase = (frame_no - 1) / LOOP * math.tau + n
            shard.location = base + Vector((0, 0, math.sin(phase) * 0.1))
            shard.rotation_euler = (0, phase, 0)
            shard.keyframe_insert("location", frame=frame_no)
            shard.keyframe_insert("rotation_euler", frame=frame_no)

# A ripple runs out through the feathers.
for obj, rest, offset in pieces:
    for frame_no in range(1, LOOP + 2, 6):
        phase = (frame_no - 1) / LOOP * math.tau - offset * 3
        obj.rotation_euler = (0, rest + math.sin(phase) * 0.035, 0)
        obj.keyframe_insert("rotation_euler", frame=frame_no)
print("BUILT triangles", triangles)

bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"voxel_wings{SUFFIX}.blend"))
out = HERE / "export"
out.mkdir(exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(out / f"voxel_wings{SUFFIX}.glb"), export_format="GLB", use_selection=True,
                          export_animations=True, export_animation_mode="SCENE", export_force_sampling=True)
print("EXPORTED", (out / f"voxel_wings{SUFFIX}.glb").stat().st_size // 1024, "KB")

world = bpy.data.worlds.new("World")
scene.world = world
bg = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.006, 0.01, 0.03, 1)
wo = next((n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeOutputWorld"), None) \
    or world.node_tree.nodes.new("ShaderNodeOutputWorld")
world.node_tree.links.new(bg.outputs[0], wo.inputs["Surface"])
cam = bpy.data.cameras.new("Camera")
cam.lens = 45
camera = bpy.data.objects.new("Camera", cam)
camera.location = (0, -9.4, 1.1)
camera.rotation_euler = (math.pi / 2, 0, 0)
scene.collection.objects.link(camera)
scene.camera = camera
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 1.3
sun = bpy.data.objects.new("Sun", sun_data)
sun.rotation_euler = (math.radians(70), 0, math.radians(20))
scene.collection.objects.link(sun)
scene.frame_set(1)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.view_settings.view_transform = "Standard"
scene.render.filepath = str(out / f"wings{SUFFIX}_preview.png")
bpy.ops.render.render(write_still=True)
print("DONE")
