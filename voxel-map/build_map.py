"""Build the floating ice temple map in Blender 5.2. Deterministic.

  blender -b --factory-startup --python build_map.py

Writes ice_temple_map.blend, export/ice_temple_map.glb, export/ice_temple_collision.json,
and export/map_preview.png. The user's concept image is a reference only. Each collection
holds one merged mesh, so it can be opened and edited in Blender. Map axes: x, height, z.
"""
import json
import math
from collections import deque
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent


def hsh(x, z):
    s = math.sin(x * 127.1 + z * 311.7) * 43758.5453
    return s - math.floor(s)


def key(x, z):
    return f"{round(x)},{round(z)}"


STONE = [(30, 45, 98), (38, 58, 120), (48, 72, 140), (22, 33, 74)]
CLIFF_TOP = [(66, 92, 156), (58, 84, 148)]
CLIFF_ROOT = [(18, 27, 66), (22, 33, 76)]
PAVE = [(92, 124, 182), (98, 130, 188), (86, 118, 176)]
SNOW = [(198, 216, 244), (184, 204, 238)]
TRIM = (152, 190, 234)
RUNE = (86, 190, 244)
CORE = (88, 170, 232)
MOON = [(150, 172, 220), (126, 150, 208), (104, 130, 194)]
ICE = [(84, 190, 250), (168, 236, 255)]
CLOUD = [(188, 208, 250), (143, 168, 234)]


def soft(x, z):
    """Slow noise: large patches, not a tile-by-tile checker."""
    return (math.sin(x * 0.23 + z * 0.11) + math.sin(x * 0.09 - z * 0.21 + 2) + 2) / 4 * 0.8 + hsh(x // 3, z // 3) * 0.2


parts = {n: [] for n in ("Terrain", "Bridges", "Temple", "Shrine", "Crystals", "Props", "Floating", "Clouds")}
cells, blockers = {}, []


def box(group, x, y, z, sx, sy, sz, colour):
    parts[group].append((x, y, z, sx, sy, sz, colour))


islands = {
    "start": dict(x=-6, z=40, r=8.5, top=0.0),
    "arena": dict(x=0, z=2, r=16, top=2.5),
    "west": dict(x=-33, z=-3, r=8, top=4.0),
    "temple": dict(x=-7, z=-37, r=12.5, top=7.0),
    "shrine": dict(x=34, z=-19, r=7, top=9.0),
}

for name, i in islands.items():
    R = math.ceil(i["r"] + 1)
    for x in range(-R, R + 1):
        for z in range(-R, R + 1):
            wx, wz, d = i["x"] + x, i["z"] + z, math.hypot(x, z)
            if d > i["r"] + (hsh(wx, wz) - 0.5) * 1.5:
                continue
            k = d / i["r"]
            cells[key(wx, wz)] = i["top"]
            depth = 2 + (1 - k ** 1.5) * i["r"] * 1.25 + hsh(wz, wx) * 3
            # Three rock strata per column, so cliffs read as layers, not one dark wall.
            cap = min(1.6 + hsh(wx, wz) * 1.2, depth * 0.3)
            mid = depth * (0.4 + hsh(wz, wx * 2) * 0.15)
            y0 = i["top"] - 0.3
            box("Terrain", wx, y0 - cap / 2, wz, 1, cap, 1, CLIFF_TOP[int(hsh(wx, wz * 2) * 2)])
            box("Terrain", wx, y0 - cap - mid / 2, wz, 1, mid, 1, STONE[int(hsh(wx * 2, wz) * 3)])
            rest = depth - cap - mid
            box("Terrain", wx, y0 - cap - mid - rest / 2, wz, 0.92, rest, 0.92, CLIFF_ROOT[int(hsh(wz * 2, wx) * 2)])
            n = soft(wx, wz)
            top = PAVE[int(n * 2.99)]
            snow = k > 0.84 or (name != "arena" and n > 0.6)
            if snow:
                top = SNOW[int(hsh(wx, wz * 3) * 2)]
            if name == "arena" and k <= 0.82:
                band, angle = int(d), math.atan2(z, x)
                if band in (5, 10):
                    top = TRIM
                if band in (7, 8) and math.sin(angle * 8) > 0.72:
                    top = TRIM
                if band <= 2:
                    top = CORE
                if band == 3:
                    box("Crystals", wx, i["top"] + 0.01, wz, 0.9, 0.05, 0.9, RUNE)
            box("Terrain", wx, i["top"] - 0.15, wz, 1, 0.3, 1, top)
            if k > 0.86:   # snow hangs over the rim in uneven drips
                drip = 0.5 + hsh(wx * 3, wz) * 1.8
                box("Terrain", wx, i["top"] - 0.3 - drip / 2, wz, 1.04, drip, 1.04, SNOW[0])
            if name != "arena" and k > 0.5 and hsh(wx * 7, wz * 5) > 0.91:
                size = 0.3 + hsh(wx, wz * 9) * 0.35
                box("Props", wx + hsh(wz, wx) - 0.5, i["top"] + size / 2, wz + hsh(wx, wz) - 0.5, size, size, size, STONE[2])
            if k > 0.72 and hsh(wx * 5, wz * 3) > 0.84:
                length = 2 + hsh(wx, wz * 7) * 6
                box("Crystals", wx, i["top"] - depth * 0.45 - length / 2, wz, 0.75, length, 0.75, ICE[0])
                box("Crystals", wx, i["top"] - depth * 0.45 - length - 0.9, wz, 0.35, 1.8, 0.35, ICE[1])


def bridge(a, b):
    ax, az, at, bx, bz, bt = *a, *b
    length = math.hypot(bx - ax, bz - az)
    nx, nz = (bz - az) / length, -(bx - ax) / length
    t = 0.0
    while t <= length:
        w = -1.5
        while w <= 1.5:
            x = ax + (bx - ax) * t / length + nx * w
            z = az + (bz - az) * t / length + nz * w
            if key(x, z) not in cells:
                h = round((at + (bt - at) * t / length) * 2) / 2
                cells[key(x, z)] = h
                box("Bridges", round(x), h - 0.5, round(z), 1, 1, 1, SNOW[0] if soft(x, z) > 0.6 else PAVE[int(hsh(x, z) * 3)])
                box("Bridges", round(x), h - 1.3, round(z), 0.8, 0.6, 0.8, STONE[0])
            w += 0.45
        if int(t / 0.45) % 7 == 0:                 # posts along both sides
            for side in (-2.1, 2.1):
                x = ax + (bx - ax) * t / length + nx * side
                z = az + (bz - az) * t / length + nz * side
                h = round((at + (bt - at) * t / length) * 2) / 2
                box("Bridges", x, h + 0.25, z, 0.42, 1.1, 0.42, STONE[2])
                box("Bridges", x, h + 0.9, z, 0.58, 0.22, 0.58, SNOW[1])
        t += 0.45


start, arena, west, temple, shrine = (islands[n] for n in ("start", "arena", "west", "temple", "shrine"))
bridge((-6, 32.5, 0), (-6, 16.5, 2.5))
bridge((-15, 0, 2.5), (-26, -3, 4))
bridge((-3, -13, 2.5), (-5, -26, 7))
bridge((15, -5, 2.5), (28, -16, 9))


def pillar(group, x, z, top, h=2.8):
    box(group, x, top + h / 2, z, 1.3, h, 1.3, STONE[1])
    box(group, x, top + h + 0.2, z, 1.8, 0.4, 1.8, STONE[0])
    box("Crystals", x, top + h * 0.55, z - 0.67, 0.35, 0.9, 0.08, ICE[0])
    blockers.append({"x": x, "z": z, "r": 1.15})


def crystal(x, z, top, size):
    for i in range(6):
        w = size * (1 - abs(i - 2) / 4.6)
        box("Crystals", x, top + size * 0.6 * (i + 0.5), z, w, size * 0.62, w, ICE[1] if i > 3 else ICE[0])


for island, count, radius in ((arena, 8, 14.2), (start, 3, 7.2), (west, 3, 6.4)):
    for i in range(count):
        a = i / count * math.tau + 0.4
        if island is start and math.sin(a) < -0.7:
            continue
        x, z = round(island["x"] + math.cos(a) * radius), round(island["z"] + math.sin(a) * radius)
        if abs(a - math.pi / 2) > 0.55:
            pillar("Props", x, z, island["top"])
        crystal(x + 2, z + 1, island["top"], 0.7)

tx, tz, tt = temple["x"], temple["z"], temple["top"]
# Plinth: stepped base with a broad central stair.
for i in range(4):
    box("Temple", tx, tt + 0.3 + i * 0.6, tz - 7.5, 22 - i * 2, 0.6, 12 - i * 1.2, STONE[2] if i % 2 else STONE[1])
    box("Temple", tx, tt + 0.62 + i * 0.6, tz - 7.5, 22.3 - i * 2, 0.06, 12.3 - i * 1.2, TRIM)
for i in range(6):
    box("Temple", tx, tt + 0.2 + i * 0.4, tz - 1.5 - i * 0.8, 7, 0.4, 0.8, PAVE[1])
blockers.append({"x": tx - 5, "z": tz - 8, "r": 6.2})
blockers.append({"x": tx + 5, "z": tz - 8, "r": 6.2})
base = tt + 2.4
# Colonnade, back wall, and a stepped roof.
for dx in (-8, -5, -2, 2, 5, 8):
    box("Temple", tx + dx, base + 2.6, tz - 4.5, 1.2, 5.2, 1.2, STONE[2])
    box("Temple", tx + dx, base + 0.3, tz - 4.5, 1.7, 0.6, 1.7, STONE[0])
    box("Temple", tx + dx, base + 5.3, tz - 4.5, 1.8, 0.5, 1.8, TRIM)
    box("Crystals", tx + dx, base + 3, tz - 3.86, 0.3, 1.2, 0.08, ICE[0])
box("Temple", tx, base + 2.7, tz - 10.5, 18, 5.4, 1.4, STONE[1])
for dx in (-6, 6):
    box("Temple", tx + dx, base + 2.7, tz - 9.7, 3, 3.6, 0.2, STONE[3])
box("Crystals", tx, base + 2, tz - 9.7, 3.2, 4, 0.1, ICE[0])
for i, (w, d) in enumerate(((20, 8.4), (16, 6.6), (11, 4.8), (6, 3))):
    box("Temple", tx, base + 5.9 + i * 0.6, tz - 7.2, w, 0.6, d, STONE[0] if i % 2 else STONE[1])
    box("Temple", tx, base + 6.22 + i * 0.6, tz - 7.2, w + 0.3, 0.05, d + 0.3, SNOW[1])
# Great crystal rising through the roof.
for i in range(13):
    k = 1 - abs(i - 4) / 9
    w = 3.4 * k
    box("Crystals", tx, base + 7 + i * 0.95, tz - 7.2, w, 1, w, ICE[1] if i > 8 or i % 3 == 0 else ICE[0])
# Broken crescent, standing on the temple and curving around the crystal.
cy = base + 12
for x in range(-13, 14):
    for y in range(-13, 14):
        outer, inner = math.hypot(x, y), math.hypot(x - 4.2, y)
        if outer > 12.5 or inner < 10 or cy + y < base + 2:
            continue
        if x > 3 and -5 < y < 1:     # the break in the ring
            continue
        box("Temple", tx + x, cy + y, tz - 12, 1, 1, 2, MOON[int(hsh(x, y) * 3)])
for n in range(16):
    a = hsh(n, 41) * math.tau
    box("Floating", tx + 7 + math.cos(a) * 3, cy - 2 + math.sin(a) * 4, tz - 12 + hsh(n, 7) * 3 - 1.5, 0.9, 0.9, 0.9, MOON[n % 3])

sx, sz, st = shrine["x"], shrine["z"], shrine["top"]
for i in range(3):
    box("Shrine", sx, st + 0.2 + i * 0.4, sz, 9 - i * 1.5, 0.4, 9 - i * 1.5, STONE[2 - i % 2])
blockers.append({"x": sx, "z": sz, "r": 3.8})
top = st + 1.2
for dx, dz in ((-2.8, -2.8), (2.8, -2.8), (-2.8, 2.8), (2.8, 2.8)):
    box("Shrine", sx + dx, top + 2.4, sz + dz, 0.9, 4.8, 0.9, STONE[2])
    box("Shrine", sx + dx, top + 4.9, sz + dz, 1.4, 0.3, 1.4, TRIM)
for i, w in enumerate((9, 7, 5, 3)):
    box("Shrine", sx, top + 5.3 + i * 0.6, sz, w, 0.6, w, STONE[1] if i % 2 else STONE[0])
    box("Shrine", sx, top + 5.62 + i * 0.6, sz, w + 0.25, 0.05, w + 0.25, SNOW[1])
for i in range(7):
    w = 1.7 * (1 - abs(i - 2) / 5.6)
    box("Crystals", sx, top + 0.45 + i * 0.68, sz, w, 0.7, w, ICE[1] if i > 3 else ICE[0])

# Rocks that hover near the islands; the web page bobs this group.
for n in range(22):
    a, r = hsh(n, 53) * math.tau, 18 + hsh(n, 57) * 30
    x, z, y, size = math.cos(a) * r, math.sin(a) * r - 6, -2 + hsh(n, 61) * 16, 0.7 + hsh(n, 63) * 1.5
    if key(x, z) in cells:
        continue
    box("Floating", x, y, z, size, size * 0.8, size, CLIFF_TOP[n % 2])
    box("Floating", x, y - size * 0.7, z, size * 0.62, size * 0.8, size * 0.62, STONE[n % 3])
    box("Floating", x, y + size * 0.42, z, size * 0.9, 0.12, size * 0.9, SNOW[0])

for i in range(16):
    a, r = hsh(i, 3) * math.tau, 52 + hsh(i, 8) * 45
    x, z, y, s = math.cos(a) * r, math.sin(a) * r, -8 + hsh(i, 5) * 20, 2 + hsh(i, 9) * 4
    for n in range(4):
        box("Props", x, y - n * s * 0.7, z, s * (1 - n * 0.22), s * 0.7, s * (1 - n * 0.22), STONE[n])
for i in range(300):
    a, r, s = hsh(i, 13) * math.tau, math.sqrt(hsh(i, 21)) * 150, 7 + hsh(i, 4) * 16
    box("Clouds", math.cos(a) * r, -30 - hsh(i, 2) * 8, math.sin(a) * r, s, 3 + hsh(i, 6) * 4, s, CLOUD[int(hsh(i, 7) * 2)])

# ---- walkability check: every destination must be reachable from the start
def can_stand(x, z, y):
    h = cells.get(key(x, z))
    return h is not None and h - y < 1.3 and not any(math.hypot(x - b["x"], z - b["z"]) < b["r"] for b in blockers)


spawn = (start["x"], start["top"], start["z"] + 2)
seen, todo = {key(spawn[0], spawn[2])}, deque([(spawn[0], spawn[2], spawn[1])])
while todo:
    x, z, y = todo.popleft()
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, nz = x + dx, z + dz
        if key(nx, nz) not in seen and can_stand(nx, nz, y):
            seen.add(key(nx, nz))
            todo.append((nx, nz, cells[key(nx, nz)]))
reach = {n: key(i["x"], i["z"] + (6 if n == "temple" else 0)) in seen for n, i in islands.items() if n != "shrine"}
reach["shrine"] = key(shrine["x"] - 5.2, shrine["z"] + 2) in seen
print("REACHABLE", reach, f"{len(seen)}/{len(cells)} cells")

# ---- Blender scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
scene = bpy.context.scene
colours = sorted({b[6] for group in parts.values() for b in group})
index = {c: i for i, c in enumerate(colours)}
image = bpy.data.images.new("T_MapPalette", len(colours), 1, alpha=False)
image.pixels = [v for c in colours for v in (c[0] / 255, c[1] / 255, c[2] / 255, 1)]
image.pack()


def material(name, emission):
    m = bpy.data.materials.new(name)
    tree = m.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image, tex.interpolation = image, "Closest"
    tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Roughness"].default_value = 0.8
    if emission:
        tree.links.new(tex.outputs["Color"], shader.inputs["Emission Color"])
        shader.inputs["Emission Strength"].default_value = emission
    tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    return m


solid, glow = material("M_MapSolid", 0), material("M_MapGlow", 1.1)
triangles = 0
for group, boxes in parts.items():
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("palette")
    for x, y, z, w, h, d, colour in boxes:
        c = Vector((x, -z, y))
        res = bmesh.ops.create_cube(bm, size=1)
        for v in res["verts"]:
            v.co = c + Vector((v.co.x * w, v.co.y * d, v.co.z * h))
        faces = {f for v in res["verts"] for f in v.link_faces}
        u = (index[colour] + 0.5) / len(colours)
        for f in faces:
            for loop in f.loops:
                loop[uv].uv = (u, 0.5)
    mesh = bpy.data.meshes.new(group)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(glow if group == "Crystals" else solid)
    obj = bpy.data.objects.new(group, mesh)
    collection = bpy.data.collections.new(group)
    scene.collection.children.link(collection)
    collection.objects.link(obj)
    triangles += len(mesh.polygons) * 2
print("BUILT boxes", sum(len(v) for v in parts.values()), "triangles", triangles)

out = HERE / "export"
out.mkdir(exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(out / "ice_temple_map.glb"), export_format="GLB", use_selection=True, export_animations=False)
(out / "ice_temple_collision.json").write_text(json.dumps({
    "cells": cells, "blockers": blockers, "spawn": spawn,
    "arena": {"x": arena["x"], "z": arena["z"], "top": arena["top"]}}), encoding="utf-8")

world = bpy.data.worlds.new("World")
scene.world = world
bg = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.012, 0.022, 0.13, 1)
wo = next((n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeOutputWorld"), None) \
    or world.node_tree.nodes.new("ShaderNodeOutputWorld")
world.node_tree.links.new(bg.outputs[0], wo.inputs["Surface"])
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy, sun_data.color = 2.5, (0.78, 0.86, 1)
for name_, loc, power in (("TempleGlow", (tx, tz * -1 + 7, tt + 14), 3500), ("ArenaGlow", (0, -2, 6), 1200), ("ShrineGlow", (sx, -sz, st + 4), 900)):
    d_ = bpy.data.lights.new(name_, "POINT")
    d_.energy, d_.color = power, (0.35, 0.72, 1)
    o_ = bpy.data.objects.new(name_, d_)
    o_.location = loc
    scene.collection.objects.link(o_)
sun = bpy.data.objects.new("Sun", sun_data)
sun.rotation_euler = (math.radians(55), 0, math.radians(35))
scene.collection.objects.link(sun)
cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 26
camera = bpy.data.objects.new("Camera", cam_data)
camera.location = (-10, -72, 34)
camera.rotation_euler = (Vector((-3, 10, 4)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.collection.objects.link(camera)
scene.camera = camera
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
scene.view_settings.view_transform = "Standard"
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "ice_temple_map.blend"))
scene.render.filepath = str(out / "map_preview.png")
bpy.ops.render.render(write_still=True)
print("DONE")
