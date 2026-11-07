"""Sculpt and key the dragon's attack effects in Blender 5.2. Deterministic.

  blender -b --factory-startup --python build_dragon_vfx.py

Each effect is built facing +Y, like the dragon, and its first frame is the attack's
impact. Writes export/vfx_dragon_{bite,claw,tail,gust,breath,floor}.glb.
"""
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent / "export"
V = 0.2
DEEP, ICE, BRIGHT, WHITE = range(4)
PALETTE = [(0.02, 0.1, 0.42, 0.05), (0.06, 0.32, 0.95, 0.3), (0.18, 0.62, 1, 0.55), (0.75, 0.93, 1, 0.8)]
rng = random.Random(33)
scene = bpy.context.scene
scene.render.fps = 24
SIDES = [((1, 0, 0), (0, 1, 0)), ((-1, 0, 0), (0, 1, 0)), ((0, 1, 0), (0, 0, 1)), ((0, -1, 0), (0, 0, 1)), ((0, 0, 1), (1, 0, 0)), ((0, 0, -1), (1, 0, 0))]
materials = []
for n, (r, g, b, power) in enumerate(PALETTE):
    m = bpy.data.materials.new(f"M_DragonFx{n}")
    tree = m.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (r, g, b, 1)
    shader.inputs["Emission Color"].default_value = (r, g, b, 1)
    shader.inputs["Emission Strength"].default_value = power
    tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    materials.append(m)


def piece(name, cells):
    bm = bmesh.new()
    for (i, j, k), level in cells.items():
        centre = Vector((i, j, k)) * V
        for normal, axis in SIDES:
            if (i + normal[0], j + normal[1], k + normal[2]) in cells:
                continue
            nn, a = Vector(normal), Vector(axis)
            b = nn.cross(a)
            c = centre + nn * V / 2
            face = bm.faces.new([bm.verts.new(c + (a * p + b * q) * V / 2) for p, q in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            face.material_index = level
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def shard(height, radius):
    """A crystal along +Z, with its origin at the base."""
    cells = {}
    steps = max(2, int(height / V))
    for k in range(steps):
        t = k / steps
        r = radius * (1 - t) ** 0.8
        c = int(r / V)
        for i in range(-c, c + 1):
            for j in range(-c, c + 1):
                if abs(i) + abs(j) <= c:
                    cells[(i, j, k)] = WHITE if t > 0.75 else BRIGHT if (i + j + k) % 3 else ICE
    return cells


def lump(size):
    """A rough handful of cubes."""
    cells = {(0, 0, 0): BRIGHT}
    for _ in range(size):
        x, y, z = rng.choice(list(cells))
        d = rng.choice(SIDES)[0]
        cells[(x + d[0], y + d[1], z + d[2])] = rng.choice((ICE, BRIGHT, BRIGHT, WHITE))
    return cells


def key(obj, f, at, turn=(0, 0, 0), size=1.0):
    obj.location = at
    obj.rotation_euler = turn
    obj.scale = size if isinstance(size, tuple) else (size, size, size)
    for path in ("location", "rotation_euler", "scale"):
        obj.keyframe_insert(path, frame=f)


def export(name, last):
    scene.frame_start, scene.frame_end = 1, last
    bpy.ops.object.select_all(action="SELECT")
    path = OUT / f"vfx_dragon_{name}.glb"
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                              export_animations=True, export_animation_mode="SCENE", export_force_sampling=True)
    print("FX", name, sum(len(o.data.polygons) * 2 for o in bpy.data.objects if o.type == "MESH"), "tris", path.stat().st_size // 1024, "KB")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)


def fling(obj, start, velocity, f0, life, gravity=16, size=1.0, spin=6):
    """Hidden until f0, then a ballistic arc that shrinks away."""
    turn = [rng.uniform(-spin, spin) for _ in range(3)]
    if f0 > 1:
        key(obj, 1, start, size=0.001)
        key(obj, f0 - 1, start, size=0.001)
    for f in range(f0, f0 + life + 1, 2):
        t = (f - f0) / 24
        at = Vector(start) + Vector(velocity) * t + Vector((0, 0, -gravity * t * t))
        k = (f - f0) / life
        key(obj, f, at, tuple(a * t for a in turn), max(0.001, size * (1 - k ** 3)))


def rise(obj, at, f0, up, hold, down, turn=(0, 0, 0)):
    """Grow out of the ground, overshoot, hold, then sink."""
    if f0 > 1:
        key(obj, 1, at, turn, (1, 1, 0.001))
        key(obj, f0 - 1, at, turn, (1, 1, 0.001))
    key(obj, f0, at, turn, (1, 1, 0.05))
    key(obj, f0 + up, at, turn, (1, 1, 1.18))
    key(obj, f0 + up + 2, at, turn, (1, 1, 1))
    key(obj, f0 + up + 2 + hold, at, turn, (1, 1, 1))
    key(obj, f0 + up + 2 + hold + down, at, turn, (0.4, 0.4, 0.001))


def aim(direction):
    return Vector(direction).normalized().to_track_quat("Z", "Y").to_euler()


def mound(radius):
    """A heap of snow cubes, with its origin at the ground."""
    cells = {}
    c = int(radius / V)
    for i in range(-c, c + 1):
        for j in range(-c, c + 1):
            top = int((1 - (i * i + j * j) / (c * c + 1)) * c * 0.75 + rng.uniform(-0.6, 0.8))
            for k in range(0, top + 1):
                cells[(i, j, k)] = WHITE if k >= top - 1 else BRIGHT
    return cells


def cloud(radius, count, levels):
    """Loose cubes filling a ball, for a body of breath."""
    cells = {}
    c = radius / V
    for _ in range(count):
        p = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if p.length <= 1:
            cells[tuple(round(v * c) for v in p)] = rng.choice(levels)
    return cells


# Bite: long crystals burst out of the jaws, inside a wide thin ring.
for n in range(24):
    a = rng.uniform(0, math.tau)
    d = Vector((math.cos(a), rng.uniform(0.25, 0.8), math.sin(a))).normalized()
    obj = piece(f"Shard{n}", shard(rng.uniform(0.9, 2.3), rng.uniform(0.28, 0.5)))
    rest = aim(d)
    speed = rng.uniform(9, 18)
    for f in range(1, 23, 2):
        t = (f - 1) / 24
        key(obj, f, d * speed * t, rest, max(0.001, 1 - ((f - 1) / 22) ** 3))
for n in range(14):
    a = rng.uniform(0, math.tau)
    d = Vector((math.cos(a), rng.uniform(0.3, 1), math.sin(a)))
    fling(piece(f"Chip{n}", lump(rng.randint(1, 3))), (0, 0, 0), d * rng.uniform(10, 16), 1, 18, 4)
ring = {}
for n in range(90):
    a = n / 90 * math.tau
    for r in (14, 15):
        ring[(round(math.cos(a) * r), 0, round(math.sin(a) * r))] = BRIGHT if n % 5 else WHITE
obj = piece("Ring", ring)
for f, sz in ((1, 0.2), (4, 1), (8, 1.45), (13, 1.7), (15, 0.001)):
    key(obj, f, (0, 0.6, 0), size=sz)
export("bite", 24)

# Claw: three dark trenches, with crystals growing taller toward the far end.
for line, x0 in enumerate((-1.5, 0, 1.5)):
    for n in range(9):
        y = 0.8 + n * 1.2
        k = n / 8
        at = (x0 * (1 + k * 0.5), y, 0)
        trench = {(i, j, kk): DEEP if rng.random() < 0.75 else ICE for i in (-1, 0, 1) for j in range(-4, 3) for kk in (0,)}
        rise(piece(f"Scar{line}_{n}", trench), at, 1 + n, 1, 30, 6)
        tall = 1 + k ** 1.4 * 3.6 * rng.uniform(0.8, 1.15)
        rise(piece(f"Spike{line}_{n}", shard(tall, 0.42 + k * 0.28)), at, 2 + n, 3, 15 - n // 2, 7, (rng.uniform(-0.28, -0.08), rng.uniform(-0.15, 0.15), 0))
        fling(piece(f"Rub{line}_{n}", lump(3)), (at[0], at[1], 0.3), (rng.uniform(-3, 3), rng.uniform(-1, 3), rng.uniform(6, 10)), 2 + n, 14, 18, 0.9)
export("claw", 52)

# Tail swipe: a crescent of crystals, thin at the start and tallest at its leading end.
ARC = 34
for n in range(ARC):
    k = n / (ARC - 1)
    a = math.radians(-155 + k * 130)
    width = 0.7 + k * 2.9
    f0 = 1 + round(k * 10)
    for row in range(1 + round(k * 3)):
        off = rng.uniform(-width, width)
        r = 10.5 + off
        tall = (0.5 + k ** 1.6 * 3.9) * rng.uniform(0.65, 1.2)
        at = (math.cos(a) * r, math.sin(a) * r, 0)
        rise(piece(f"Wave{n}_{row}", shard(tall, 0.42 + k * 0.42)), at, f0 + row, 3, 7, 6, (rng.uniform(-0.22, 0.22), rng.uniform(-0.22, 0.22), 0))
    base = {(i, j, 0): DEEP if (i + j * 2) % 5 == 0 else ICE if (i * j) % 3 else BRIGHT
            for i in range(-round(width / V), round(width / V) + 1) for j in (-3, -2, -1, 0, 1, 2)}
    rise(piece(f"Bed{n}", base), (math.cos(a) * 10.5, math.sin(a) * 10.5, 0.02), f0, 2, 9, 6, (0, 0, a))
    fling(piece(f"Spray{n}", lump(2)), (math.cos(a) * 10.5, math.sin(a) * 10.5, 0.4),
          (math.cos(a) * 4, math.sin(a) * 4, rng.uniform(6, 12)), f0 + 1, 14, 16, 0.9)
export("tail", 44)

# Wing gust: curving streams of small cubes run along the ground and heap into snow.
STREAMS = 11
for beat, f0 in enumerate((1, 17, 33)):
    for st in range(STREAMS):
        x0 = -10 + st / (STREAMS - 1) * 20
        bend = x0 * 0.55
        for n in range(16):
            obj = piece(f"Gust{beat}_{st}_{n}", lump(rng.randint(0, 2)))
            start = f0 + n // 2
            key(obj, 1, (x0, 0, 6), size=0.001)
            if start > 1:
                key(obj, start - 1, (x0, 0, 6), size=0.001)
            for f in range(start, start + 19, 2):
                t = (f - start) / 18
                key(obj, f, (x0 + bend * t * t, 1 + t * 20 + n * 0.1, 0.45 + (1 - t) ** 2 * (5.5 + (st % 3))), (t * 3, t * 2, 0), max(0.001, 1.15 * (1 - t ** 5)))
    if beat == 0:
        for st in range(STREAMS):
            x0 = -10 + st / (STREAMS - 1) * 20
            at = (x0 + x0 * 0.55, 21 + rng.uniform(-2, 2), 0)
            rise(piece(f"Heap{st}", mound(rng.uniform(1, 1.8))), at, 15 + rng.randint(0, 6), 5, 34, 10)
export("gust", 80)

# Frost breath: a thick cone of cubes, white at the mouth and breaking up at the far end.
LENGTH, CYCLE, START, STOP = 19, 16, 1, 50
direction = Vector((0, 1, -0.4)).normalized()
side, up = Vector((1, 0, 0)), Vector((0, 0.37, 0.93))
for n in range(120):
    a, wide = rng.uniform(0, math.tau), rng.random() ** 0.5
    offset = rng.randint(0, CYCLE - 1)
    near = n % 3 == 0
    cells = cloud(0.5, 12, (WHITE, WHITE, BRIGHT)) if near else lump(rng.randint(2, 6))
    obj = piece(f"Breath{n}", cells)
    key(obj, 1, (0, 0, 0), size=0.001)
    for f in range(START, STOP + CYCLE + 1, 2):
        age = (f + offset - START) % CYCLE / CYCLE
        live = START <= f - age * CYCLE <= STOP
        reach = age * (0.55 if near else 1)
        at = direction * LENGTH * reach + (side * math.cos(a) + up * math.sin(a)) * wide * (0.3 + reach * 5.4)
        key(obj, f, at, (age * 3 + a, age * 2, a), (0.7 + reach * 2.3) * (1 - age ** 6) if live else 0.001)
for n in range(7):                                    # the solid throat of the beam
    obj = piece(f"Throat{n}", cloud(0.7 + n * 0.28, 70 + n * 12, (WHITE, WHITE, BRIGHT)))
    at = direction * (0.6 + n * 1.25)
    for f, sz in ((1, 0.001), (4, 1), (STOP, 1), (STOP + 7, 0.001)):
        key(obj, f, at, (0, f * 0.2, 0), sz)
    for f in range(6, STOP, 8):
        key(obj, f, at, (0, f * 0.2, 0), 0.9 + (f + n * 3) % 3 * 0.1)
export("breath", STOP + CYCLE)

# Frozen ground: big crystals in a wedge, tallest at the far end, with cubes rising off them.
for n in range(34):
    k = rng.random() ** 0.7
    y = 9 + k * 13
    x = rng.uniform(-1, 1) * (2 + k * 7.5)
    f0 = 3 + round(k * 26) + rng.randint(0, 8)
    tall = (1.4 + k * 5) * rng.uniform(0.6, 1.2)
    turn = (rng.uniform(-0.45, 0.25), rng.uniform(-0.45, 0.45), 0)
    rise(piece(f"Spire{n}", shard(tall, 0.75 + k * 0.85)), (x, y, 0), f0, 4, 66 - f0 // 2, 12, turn)
for n in range(16):
    k = n / 15
    plate = {(i, j, 0): rng.choice((ICE, BRIGHT, BRIGHT, DEEP)) for i in range(-7, 8) for j in range(-5, 6)}
    rise(piece(f"Plate{n}", plate), (rng.uniform(-1, 1) * (1.5 + k * 6), 6 + k * 15, 0.02), 1 + round(k * 26), 2, 72, 12, (0, 0, rng.uniform(-0.3, 0.3)))
for n in range(26):
    at = (rng.uniform(-8, 8), rng.uniform(11, 22), rng.uniform(1, 3))
    fling(piece(f"Float{n}", {(0, 0, 0): BRIGHT, (1, 0, 0): ICE, (0, 1, 0): WHITE, (0, 0, 1): BRIGHT, (1, 1, 1): ICE}), at, (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(2, 4.5)), 16 + rng.randint(0, 40), 42, 0, rng.uniform(0.9, 1.6), 2)
export("floor", 120)
print("DONE")
