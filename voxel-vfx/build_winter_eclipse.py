"""Build the Winter Eclipse VFX in Blender 5.2. Deterministic.

  blender -b --factory-startup --python build_winter_eclipse.py

Timeline at 24 fps: crater opens, moon falls, impact on frame 34 (1.4 s), plates, spikes,
and a block wave burst out, then everything clears by frame 65. Cubes are merged into
keyframed pieces, so the .blend plays in Blender and the GLB stays light.
"""
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
FRAMES, IMPACT = 65, 34
rng = random.Random(77)
PALETTE = [(0.006, 0.012, 0.06), (0.03, 0.09, 0.36), (0.07, 0.25, 0.72), (0.2, 0.56, 0.93), (0.56, 0.86, 1), (1, 1, 1)]
EMIT = [0.01, 0.05, 0.13, 0.26, 0.42, 0.75]

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
    shader.inputs["Roughness"].default_value = 0.5
    tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    materials.append(m)

root = bpy.data.objects.new("WinterEclipse", None)
scene.collection.objects.link(root)
collection = bpy.data.collections.new("VFX_WinterEclipse")
scene.collection.children.link(collection)
total = 0


def piece(name, cubes, parent=root, location=(0, 0, 0)):
    """cubes: (x, y, z, sx, sy, sz, level). One merged object."""
    global total
    bm = bmesh.new()
    for x, y, z, sx, sy, sz, level in cubes:
        res = bmesh.ops.create_cube(bm, size=1)
        for v in res["verts"]:
            v.co = Vector((x + v.co.x * sx, y + v.co.y * sy, z + v.co.z * sz))
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = level
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    total += len(cubes)
    return obj


def keys(obj, path, frames):
    for frame, value in frames:
        setattr(obj, path, value)
        obj.keyframe_insert(path, frame=frame)


# Crater: a dark floor and a low stepped wall, opening outward from the centre.
floor, wall = [], []
x = -5.4
while x <= 5.4:
    y = -5.4
    while y <= 5.4:
        r = math.hypot(x, y)
        if r <= 5.4:
            floor.append((x, y, 0.08, 0.41, 0.41, 0.12, 0 if r < 3.6 else 1))
            steps = round(max(r - 4.1, 0) * 1.5 * (0.7 + rng.random() * 0.5))
            for n in range(steps):
                wall.append((x, y, 0.28 + n * 0.3, 0.4, 0.4, 0.3, 3 if n == steps - 1 else 2))
        y += 0.42
    x += 0.42
for name, cubes in (("CraterFloor", floor), ("CraterWall", wall)):
    o = piece(name, cubes)
    keys(o, "scale", [(1, (0.01, 0.01, 1)), (11, (1, 1, 1)), (FRAMES - 8, (1, 1, 1)), (FRAMES, (0.01, 0.01, 0.01))])

# Moon: a shell of cubes split into plates, with wide dark cracks between them.
moon = bpy.data.objects.new("Moon", None)
collection.objects.link(moon)
moon.parent = root
fall = [(f, (0, 0, 9.2 - (min(f, IMPACT) / IMPACT) ** 3.2 * 7)) for f in range(1, IMPACT + 1, 3)] + [(IMPACT, (0, 0, 2.2))]
keys(moon, "location", fall)
keys(moon, "rotation_euler", [(1, (0.2, 0, 0)), (IMPACT, (0.2, 0, 2.6))])
seeds = [Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized() for _ in range(13)]
plates = [[] for _ in seeds]
R, cell = 2.1, 0.28
x = -R
while x <= R:
    y = -R
    while y <= R:
        z = -R
        while z <= R:
            length = math.sqrt(x * x + y * y + z * z)
            if R - cell * 1.5 <= length <= R:
                u = Vector((x, y, z)).normalized()
                near = sorted((s.__sub__(u).length, i) for i, s in enumerate(seeds))
                crack = near[1][0] - near[0][0] < 0.14
                level = 0 if crack else (3, 4, 3, 2, 4)[near[0][1] % 5]
                plates[near[0][1]].append((x, y, z, cell * 0.96, cell * 0.96, cell * 0.96, level))
            z += cell
        y += cell
    x += cell
for i, cubes in enumerate(plates):
    if not cubes:
        continue
    o = piece(f"MoonPlate_{i:02d}", cubes, moon)
    throw = seeds[i] * rng.uniform(2.2, 4.2)
    steps = [(IMPACT, (0, 0, 0))]
    for f in range(IMPACT + 2, IMPACT + 21, 2):
        age = (f - IMPACT) / 24
        steps.append((f, tuple(throw * age * 2.2 + Vector((0, 0, -5 * age * age)))))
    keys(o, "location", steps)
    keys(o, "scale", [(1, (1, 1, 1)), (IMPACT + 6, (1, 1, 1)), (IMPACT + 20, (0.01, 0.01, 0.01))])

# Eclipse halo: a broken ring around the falling moon.
halo = []
for n in range(72):
    if n % 12 < 9:
        a = n / 72 * math.tau
        halo.append((math.cos(a) * 3, math.sin(a) * 3, math.sin(a * 2) * 0.2, 0.2, 0.2, 0.2, 5 if n % 3 else 4))
ring = piece("Halo", halo, moon)
keys(ring, "scale", [(1, (0.01, 0.01, 0.01)), (9, (1, 1, 1)), (IMPACT - 1, (1, 1, 1)), (IMPACT, (0.01, 0.01, 0.01))])
keys(ring, "rotation_euler", [(1, (0, 0, 0)), (IMPACT, (0, 0, 5))])

# Spikes: clusters of narrowing stacks that burst up at impact, with uneven height and lean.
for n in range(15):
    base = n / 15 * math.tau + rng.uniform(0, 0.22)
    cubes = []
    for m in range(3):
        a, r = base + (m - 1) * 0.09, rng.uniform(5, 5.9)
        tall, lean = (11 if m == 1 else 5) + rng.randint(0, 5), rng.uniform(0.06, 0.18)
        for h in range(tall):
            k = h / tall
            w = 0.68 * (1 - k) ** 1.15 + 0.06
            level = 5 if k > 0.84 else 4 if k > 0.55 else 3 if k > 0.25 else 2
            cubes.append((math.cos(a) * (r + h * lean), math.sin(a) * (r + h * lean), 0.15 + h * 0.3, w, w, 0.32, level))
    o = piece(f"Spikes_{n:02d}", cubes)
    start = IMPACT + n % 3
    keys(o, "scale", [(1, (1, 1, 0.01)), (start, (1, 1, 0.01)), (start + 3, (1, 1, 1.06)), (start + 5, (1, 1, 1)),
                      (FRAMES - 10, (1, 1, 1)), (FRAMES - 3, (1, 1, 0.01))])

# Block wave: arcs thrown outward at ground level.
for n in range(12):
    a0 = n / 12 * math.tau
    cubes = [(math.cos(a0 + i * 0.07) * 1.2, math.sin(a0 + i * 0.07) * 1.2, 0.3 + (i % 2) * 0.2, 0.38, 0.38, 0.38, 3 + i % 2) for i in range(7)]
    o = piece(f"Wave_{n:02d}", cubes)
    direction = Vector((math.cos(a0 + 0.2), math.sin(a0 + 0.2), 0))
    keys(o, "location", [(IMPACT, (0, 0, 0)), (IMPACT + 7, tuple(direction * 5 + Vector((0, 0, 0.7)))), (IMPACT + 14, tuple(direction * 9))])
    keys(o, "scale", [(1, (0.01, 0.01, 0.01)), (IMPACT, (0.01, 0.01, 0.01)), (IMPACT + 1, (1, 1, 1)), (IMPACT + 9, (1, 1, 1)), (IMPACT + 14, (0.01, 0.01, 0.01))])

# Chips: ten clumps on simple arcs.
for n in range(10):
    a = n / 10 * math.tau + 0.2
    cubes = [(rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8), rng.uniform(0, 0.8), s, s, s, 3 + i % 3)
             for i, s in enumerate(rng.uniform(0.12, 0.34) for _ in range(9))]
    o = piece(f"Chips_{n}", cubes)
    v = Vector((math.cos(a) * 10, math.sin(a) * 10, 7))
    steps = [(f, tuple(Vector((math.cos(a) * 4, math.sin(a) * 4, 0.3)) + v * ((f - IMPACT) / 24) + Vector((0, 0, -13 * ((f - IMPACT) / 24) ** 2))))
             for f in range(IMPACT, IMPACT + 19, 2)]
    keys(o, "location", steps)
    keys(o, "scale", [(1, (0.01, 0.01, 0.01)), (IMPACT, (0.01, 0.01, 0.01)), (IMPACT + 1, (1, 1, 1)), (IMPACT + 12, (1, 1, 1)), (IMPACT + 18, (0.01, 0.01, 0.01))])

print("CUBES", total)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "vfx_winter_eclipse.blend"))
out = HERE / "export"
out.mkdir(exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
root.select_set(True)
for obj in collection.objects:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out / "winter_eclipse.glb"), export_format="GLB", use_selection=True,
                          export_animations=True, export_animation_mode="SCENE", export_force_sampling=True)
print("EXPORTED", (out / "winter_eclipse.glb").stat().st_size // 1024, "KB")
