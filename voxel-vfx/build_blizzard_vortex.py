"""Build the Blizzard Vortex VFX in Blender 5.2. Deterministic.

  blender -b --factory-startup --python build_blizzard_vortex.py

Cubes are merged into rings, and each ring is a keyframed object that spins at its own
speed, so the .blend plays in Blender and the GLB stays light. Writes
vfx_blizzard_vortex.blend and export/blizzard_vortex.glb.
"""
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
FRAMES = 67     # 2.8 s at 24 fps
rng = random.Random(41)
PALETTE = [(0.014, 0.04, 0.19), (0.03, 0.11, 0.48), (0.07, 0.27, 0.78), (0.2, 0.58, 0.95), (0.56, 0.86, 1), (1, 1, 1)]
EMIT = [0.02, 0.06, 0.14, 0.26, 0.4, 0.7]

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
scene = bpy.context.scene
scene.render.fps = 24
scene.frame_start, scene.frame_end = 1, FRAMES
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"

materials = []
for colour, power in zip(PALETTE, EMIT):
    m = bpy.data.materials.new("M_Ice")
    tree = m.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (*colour, 1)
    shader.inputs["Emission Color"].default_value = (*colour, 1)
    shader.inputs["Emission Strength"].default_value = power
    shader.inputs["Roughness"].default_value = 0.45
    tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    materials.append(m)

root = bpy.data.objects.new("BlizzardVortex", None)
scene.collection.objects.link(root)
collection = bpy.data.collections.new("VFX_BlizzardVortex")
scene.collection.children.link(collection)
for frame, size in ((1, 0.01), (8, 1), (FRAMES - 9, 1), (FRAMES, 0.01)):
    root.scale = (size, size, size)
    root.keyframe_insert("scale", frame=frame)


def ring(name, cubes, turns_per_second, tilt=(0, 0)):
    """cubes: (x, y, z, size, level). One merged object that spins around Z."""
    bm = bmesh.new()
    for x, y, z, size, level in cubes:
        res = bmesh.ops.create_cube(bm, size=size)
        for v in res["verts"]:
            v.co += Vector((x, y, z))
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = level
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = root
    total = -turns_per_second * math.tau * FRAMES / 24
    for frame, angle in ((1, 0), (FRAMES, total)):
        obj.rotation_euler = (tilt[0], tilt[1], angle)
        obj.keyframe_insert("rotation_euler", frame=frame)
    return len(cubes)


count = 0
levels = 12
for l in range(levels):
    k = l / (levels - 1)
    radius, z, size = 0.34 + k ** 1.55 * 3.7, 0.2 + l * 0.27, 0.24 + k * 0.09
    n = max(7, round(radius * math.tau / (size * 1.02)))
    cubes = []
    for i in range(n):
        a = i / n * math.tau
        band = (math.sin(a * 2 + l * 0.8) + 1) / 2     # two bands wind up the funnel
        if band < 0.2 and k > 0.15:
            continue
        level = 5 if band > 0.96 else 4 if band > 0.78 else 3 if band > 0.5 else 2 if band > 0.3 else 1
        r = radius + rng.uniform(-0.05, 0.05)
        cubes.append((math.cos(a) * r, math.sin(a) * r, z + rng.uniform(-0.03, 0.03), size, level))
        if band > 0.6:                                  # thick wall where a band passes
            r2 = r + size * 0.62
            cubes.append((math.cos(a) * r2, math.sin(a) * r2, z + size * 0.7, size * 0.82, max(level - 1, 1)))
    count += ring(f"Funnel_{l:02d}", cubes, 0.85 - k * 0.5)

core = []
for l in range(14):
    for n in range(3):
        a = n * 2.1 + l * 0.45
        core.append((math.cos(a) * 0.15, math.sin(a) * 0.15, 0.1 + l * 0.24, 0.17, 5 if l % 3 else 4))
count += ring("Core", core, 1.6)

for w in range(3):
    radius, z = 4.4 + w * 0.6, 0.8 + w * 0.8
    cubes = []
    for n in range(84):
        if (n + w * 9) % 28 > 17:                       # broken arcs, not full circles
            continue
        a = n / 84 * math.tau
        cubes.append((math.cos(a) * radius, math.sin(a) * radius, z + math.sin(a * 2) * 0.25, 0.18, 4 if w == 1 else 3))
    count += ring(f"Wind_{w}", cubes, 0.42 - w * 0.08, (0.1 * (w - 1), 0.07 * w))

for s in range(2):                                      # a turning spiral reads as an inward pull
    cubes = []
    for arm in range(3):
        for n in range(26):
            u = n / 26
            a = arm * math.tau / 3 + u * 5.2 + s
            r = 5.3 * (1 - u) + 0.4
            cubes.append((math.cos(a) * r, math.sin(a) * r, 0.5 + u * 2.6 + s * 0.3, 0.25 - u * 0.1, 4 + n % 2))
    count += ring(f"Stream_{s}", cubes, 0.6 + s * 0.15)

ground = []
for n in range(120):
    a, r = rng.uniform(0, math.tau), rng.uniform(1, 5)
    ground.append((math.cos(a) * r, math.sin(a) * r, rng.uniform(0.05, 0.35), rng.uniform(0.13, 0.38), rng.randint(1, 4)))
count += ring("GroundChunks", ground, 0.18)
print("CUBES", count)

bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "vfx_blizzard_vortex.blend"))
out = HERE / "export"
out.mkdir(exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
root.select_set(True)
for obj in collection.objects:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out / "blizzard_vortex.glb"), export_format="GLB", use_selection=True,
                          export_animations=True, export_animation_mode="SCENE", export_force_sampling=True)
print("EXPORTED", (out / "blizzard_vortex.glb").stat().st_size // 1024, "KB")
