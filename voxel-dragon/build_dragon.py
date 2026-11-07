"""Sculpt the ice dragon boss in Blender 5.2, part by part. Deterministic.

  blender -b --factory-startup --python build_dragon.py

Faces +Y, ground at Z 0, about five times the hero's height. Every part is its own
object with its origin on its joint, ready for rigid rigging.
Writes voxel_dragon.blend, export/voxel_dragon.glb, export/parts.json, and preview renders.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
V = 0.2
DARK, NAVY, BLUE, PALE, WHITE, ICE, BRIGHT, GLOW, EYE, MOUTH = range(10)
PALETTE = [(0.014, 0.03, 0.15), (0.03, 0.08, 0.34), (0.06, 0.2, 0.68), (0.34, 0.58, 0.9),
           (0.82, 0.86, 0.95), (0.06, 0.32, 0.95), (0.16, 0.58, 1), (0.6, 0.95, 1), (0.08, 0.75, 1), (0.02, 0.2, 0.75)]
EMIT = [0, 0, 0, 0, 0, 0.3, 0.55, 2.2, 3, 1.1]

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
scene = bpy.context.scene
materials = []
for n, (colour, power) in enumerate(zip(PALETTE, EMIT)):
    m = bpy.data.materials.new(f"M_Dragon{n}")
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

collection = bpy.data.collections.new("Dragon")
scene.collection.children.link(collection)
SIDES = [((1, 0, 0), (0, 1, 0)), ((-1, 0, 0), (0, 1, 0)), ((0, 1, 0), (0, 0, 1)),
         ((0, -1, 0), (0, 0, 1)), ((0, 0, 1), (1, 0, 0)), ((0, 0, -1), (1, 0, 0))]
triangles = 0
joints = {}


def grid(p):
    return tuple(round(c / V) for c in p)


def speckle(i, j, k):
    """Blocky two-tone scales, stable from build to build."""
    return DARK if ((i // 3) * 73 + (j // 3) * 151 + (k // 3) * 283) % 6 == 0 else NAVY


def part(name, cells, pivot):
    global triangles
    bm = bmesh.new()
    origin = Vector(pivot)
    for (i, j, k), level in cells.items():
        centre = Vector((i, j, k)) * V - origin
        for normal, axis in SIDES:
            if (i + normal[0], j + normal[1], k + normal[2]) in cells:
                continue
            n, a = Vector(normal), Vector(axis)
            b = n.cross(a)
            c = centre + n * V / 2
            face = bm.faces.new([bm.verts.new(c + (a * p + b * q) * V / 2) for p, q in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            face.material_index = level
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.location = origin
    triangles += len(mesh.polygons) * 2
    joints[name] = [round(c, 3) for c in pivot]
    return obj


def tube(cells, points, colour=None, squash=(1, 1, 1)):
    """Fill spheres along points of (x, y, z, radius). colour(i, j, k, offset) picks the level."""
    for a, b in zip(points, points[1:]):
        steps = max(2, int(math.dist(a[:3], b[:3]) / (V * 0.7)))
        for s in range(steps + 1):
            t = s / steps
            x, y, z, r = (a[n] + (b[n] - a[n]) * t for n in range(4))
            cr = int(r / V) + 1
            ci, cj, ck = grid((x, y, z))
            for i in range(-cr, cr + 1):
                for j in range(-cr, cr + 1):
                    for k in range(-cr, cr + 1):
                        off = (i * V / squash[0], j * V / squash[1], k * V / squash[2])
                        if off[0] ** 2 + off[1] ** 2 + off[2] ** 2 <= r * r:
                            at = (ci + i, cj + j, ck + k)
                            cells[at] = colour(*at, off, r) if colour else speckle(*at)


def spike(cells, base, direction, length, radius, levels=(ICE, BRIGHT)):
    """A faceted crystal cone."""
    d = Vector(direction).normalized()
    steps = max(2, int(length / (V * 0.8)))
    for s in range(steps):
        t = s / steps
        c = Vector(base) + d * length * t
        r = radius * (1 - t) ** 0.8 + 0.02
        cr = int(r / V) + 1
        ci, cj, ck = grid(c)
        for i in range(-cr, cr + 1):
            for j in range(-cr, cr + 1):
                for k in range(-cr, cr + 1):
                    if abs(i * V) + abs(j * V) + abs(k * V) <= r * 1.25:
                        cells[(ci + i, cj + j, ck + k)] = levels[1] if (t > 0.55 or (i + k) % 3 == 0) else levels[0]


def belly(i, j, k, off, r):
    """Pale underside, in stacked plates."""
    if off[2] < -r * 0.5 and abs(off[0]) < r * 0.62:
        return PALE if k % 2 else BLUE
    return speckle(i, j, k)


def throat(i, j, k, off, r):
    if off[1] > r * 0.35 and abs(off[0]) < r * 0.6:
        return PALE if k % 2 else BLUE
    return speckle(i, j, k)


def spine(cells, points, every, size):
    for a, b in zip(points, points[1:]):
        count = max(1, int(math.dist(a[:3], b[:3]) / every))
        for s in range(count):
            t = (s + 0.5) / count
            x, y, z, r = (a[n] + (b[n] - a[n]) * t for n in range(4))
            spike(cells, (x, y, z + r * 0.8), (0, -0.55, 1), size * (0.8 + 0.55 * r), size * 0.13 + 0.08)


# Body, with shoulder armour and the chest plate.
body_path = [(0, -3.1, 4.5, 1.75), (0, -0.6, 4.7, 2.05), (0, 1.8, 5.1, 2.15), (0, 3, 5.5, 1.75)]
body = {}
tube(body, body_path, belly, (1.05, 1, 1))
spine(body, body_path, 1.05, 1.4)
for side in (1, -1):
    for y, z in ((-1.8, 6.1), (0.6, 6.6)):
        spike(body, (side * 1.5, y, z), (side, -0.4, 0.75), 1.1, 0.34)
    for n in range(5):
        at = grid((side * (0.82 + n * 0.1), 4.45 - n * 0.2, 6 - n * 0.42))
        for di in range(-1, 2):
            for dk in range(-1, 2):
                body[(at[0] + di, at[1], at[2] + dk)] = WHITE
part("Body", body, (0, 0, 4.8))

# Chest core: a heart of crystal set in a dark plate.
core = {}
for i in range(-6, 7):
    for k in range(-8, 7):
        width = 6 - max(0, -k) * 0.78 if k < 2 else 6 - (k - 2) * 1.2 + (2 if abs(i) > 2 else -1)
        if abs(i) <= width:
            edge = width - abs(i)
            level = NAVY if edge < 1.5 else ICE if edge < 3 else BRIGHT if edge < 4.2 else GLOW
            for j in (0, 1):
                core[(i, round(4.5 / V) + j + (1 if edge > 3 else 0), round(5 / V) + k)] = level
part("Core", core, (0, 4.7, 5))

# Neck in three joints, rising in a soft S.
neck_path = [(0, 3, 6, 1.35), (0, 4, 6.9, 1.12), (0, 4.65, 7.9, 0.98), (0, 5, 8.9, 0.9)]
for n in range(3):
    seg = {}
    tube(seg, neck_path[n:n + 2], throat)
    spine(seg, neck_path[n:n + 2], 0.7, 1.05 - n * 0.1)
    part(f"Neck{n + 1}", seg, neck_path[n][:3])

# The head uses a finer grid: a wedge lofted through side-profile stations.
BODY_V = V
V = 0.1
#          y    half width  top    bottom
SKULL = [(4.5, 0.9, 10.3, 8.95), (5.3, 1.32, 10.78, 8.85), (6.1, 1.16, 10.42, 8.85), (7, 0.82, 9.98, 8.82),
         (7.8, 0.64, 9.72, 8.82), (8.4, 0.54, 9.56, 8.88), (8.62, 0.4, 9.36, 9.02)]


def station(table, y):
    y = min(max(y, table[0][0]), table[-1][0])
    for a, b in zip(table, table[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            return [a[n] + (b[n] - a[n]) * t for n in range(1, len(a))]
    return None


def loft(cells, table, colour):
    for j in range(round(table[0][0] / V), round(table[-1][0] / V) + 1):
        y = j * V
        w, top, bottom = station(table, y)
        mid, half = (top + bottom) / 2, (top - bottom) / 2
        for k in range(round(bottom / V), round(top / V) + 1):
            v = (k * V - mid) / half
            # Flat underside and a chamfered, narrower top.
            limit = w * (1 - max(v, 0) ** 2.4 * 0.62) * (1 - max(-v, 0) ** 4 * 0.2)
            for n in range(-round(limit / V), round(limit / V) + 1):
                cells[(n, j, k)] = colour(n, j, k, v, n * V / max(w, 0.01))


def skin(i, j, k, v, across):
    if v < -0.86:
        return MOUTH                                      # glowing roof, seen when the jaw opens
    if v > 0.3 and ((i // 3) * 31 + (j // 3) * 17 + (k // 3) * 7) % 10 == 0:
        return BLUE                                       # lit scales along the top
    return speckle(i, j, k)


head = {}
loft(head, SKULL, skin)
# Raised scales: whole blocks of the surface step out by one cell.
for (i, j, k), level in list(head.items()):
    if ((i // 3) * 41 + (j // 3) * 23 + (k // 3) * 59) % 4 == 0:
        for step in ((1 if i > 0 else -1, 0, 0), (0, 0, 1)):
            at = (i + step[0], j, k + step[2])
            if at not in head and k * V > 9.1:
                head[at] = level
for (i, j, k), level in list(head.items()):
    y, z, x = j * V, k * V, abs(i) * V
    w = station(SKULL, y)[0]
    # One soft glowing eye on each side, sunk under the brow.
    if x > w * 0.5:
        d = math.hypot((y - 6.35) / 0.34, (z - 10) / 0.2)
        if d <= 1:
            head[(i, j, k)] = EYE
        elif d <= 1.45:
            head[(i, j, k)] = ICE
for side in (1, -1):
    # A dark brow ridge, same colour as the face, overhanging the eye.
    tube(head, [(side * 1.26, 5.6, 10.56, 0.2), (side * 1.1, 6.3, 10.38, 0.17), (side * 0.8, 7, 10.08, 0.12)])
    # Nostril pits near the blunt tip.
    for dy in (0, 1):
        for dk in (0, 1):
            head[grid((side * 0.34, 8.05 + dy * V, 9.58 + dk * V))] = DARK
    # The mouth is closed: a jagged white band of short teeth, rising to the cheek.
    sizes = (3, 2, 4, 2, 3, 2, 3, 4, 2, 3, 2, 3)
    drops = (0.2, 0.1, 0.3, 0.1, 0.2, 0.3, 0.1, 0.2, 0.1, 0.4, 0.2, 0.1)
    tops = (0.1, 0, 0.1, 0.1, 0, 0.1, 0.2, 0, 0.1, 0, 0, 0.1)
    y = 5.4
    n = 0
    while y < 8.5:
        for dy in range(sizes[n % 12]):
            at_y = y + dy * V
            w, _, low = station(SKULL, at_y)
            rise = (8.45 - at_y) * 0.13
            out = 1 + n % 2                                # some lumps stand proud of the lip
            for x_step in range(0, out):
                z = low + rise + tops[n % 12]
                while z > low + rise - drops[n % 12] - (0.16 if 7.8 < y < 8.1 else 0):
                    tone = PALE if (n % 3 == 1 and z < low + rise - 0.05) else WHITE
                    head[grid((side * (w + x_step * V), at_y, z))] = tone
                    z -= V
        y += sizes[n % 12] * V
        n += 1
    # White horn root rising from the brow; the crystal Crown continues it.
    spike(head, (side * 0.82, 5.85, 10.62), (side * 0.32, -0.82, 0.78), 2, 0.3, (WHITE, WHITE))
    # White spurs on the cheek.
    spike(head, (side * 1.28, 5.45, 9.75), (side * 0.42, -1, 0.3), 1.15, 0.24, (WHITE, WHITE))
    spike(head, (side * 1.22, 5.5, 9.25), (side * 0.42, -1, 0.05), 0.85, 0.2, (WHITE, WHITE))
# Small white gem on the forehead, and a low bump on the nose.
spike(head, (0, 6.75, 10.28), (0, -0.4, 1), 0.34, 0.14, (WHITE, WHITE))
spike(head, (0, 8.28, 9.6), (0, 0.5, 1), 0.24, 0.1, (WHITE, WHITE))
part("Head", head, (0, 5, 8.95))

JAW = [(4.9, 0.9, 8.95, 8.25), (6, 0.8, 8.72, 8.2), (7, 0.62, 8.62, 8.24), (8, 0.5, 8.62, 8.3), (8.38, 0.36, 8.62, 8.36)]


def jaw_skin(i, j, k, v, across):
    if v > 0.45:
        return WHITE if (j // 2) % 2 else PALE            # short lower teeth under the band
    return PALE if (j // 3) % 3 else BLUE


jaw = {}
loft(jaw, JAW, jaw_skin)
spike(jaw, (0, 8.1, 8.3), (0, 0.15, -1), 0.8, 0.22)        # crystal on the chin
part("Jaw", jaw, (0, 5, 8.45))
V = BODY_V

# Slim crystal crown on the fine grid. Rig it as a child of Head.
V = 0.1
crown = {}
for side in (1, -1):
    # Main horn, continuing the white root.
    spike(crown, (side * 1.2, 4.9, 11.5), (side * 0.32, -0.82, 0.78), 4.4, 0.3)
    # Crest of smaller crystals behind it.
    for x, y, z, dx, dy, dz, length, r in ((0.55, 4.7, 10.6, 0.12, -0.75, 1, 3.2, 0.26), (1.15, 4.6, 10.2, 0.6, -1, 0.5, 2.9, 0.23),
                                           (1.3, 4.7, 9.5, 0.75, -1, 0.15, 2.4, 0.2), (1, 4.5, 9, 0.7, -1, -0.1, 1.8, 0.17)):
        spike(crown, (side * x, y, z), (side * dx, dy, dz), length, r)
spike(crown, (0, 5.3, 10.5), (0, -0.55, 1), 3.9, 0.3)
part("Crown", crown, (0, 5, 8.95))
V = BODY_V

# Legs: upper, lower, and a foot with crystal claws, on both sides.
for side, label in ((1, "R"), (-1, "L")):
    for name, y, top in (("Front", 2.1, 5.1), ("Hind", -2.4, 4.8)):
        lean = 0.55 if name == "Front" else -0.65
        hip = (side * 2.05, y, top)
        knee = (side * 2.5, y + lean, 2.8)
        ankle = (side * 2.45, y + (0.1 if name == "Front" else -0.35), 1.05)
        upper = {}
        tube(upper, [(*hip, 1.28 if name == "Hind" else 1.12), (*knee, 0.84)])
        spike(upper, (side * 2.85, y, top + 0.2), (side * 0.8, -0.7, 0.75), 1.7, 0.42)
        part(f"{name}Upper{label}", upper, hip)
        lower = {}
        tube(lower, [(*knee, 0.8), (*ankle, 0.58)])
        for n in range(3):                               # frost bands
            at = grid((side * 3.1, y + lean * 0.4, 2.45 - n * 0.48))
            for dj in range(-3, 4):
                lower[(at[0], at[1] + dj, at[2])] = WHITE
        spike(lower, (side * 2.95, y, 2.5), (side * 0.75, -0.7, 0.45), 1.5, 0.38)
        part(f"{name}Lower{label}", lower, knee)
        foot = {}
        ax, ay = ankle[0], ankle[1]
        tube(foot, [(ax, ay, 1, 0.6), (ax, ay + 0.75, 0.48, 0.48)], None, (1.35, 1, 1))
        for toe in (-1, 0, 1):
            tx = ax + toe * 0.56
            spike(foot, (tx, ay + 0.95, 0.5), (toe * 0.3, 1, -0.32), 1.5, 0.24)
            at = grid((tx, ay + 0.98, 0.55))
            for di in (-1, 0, 1):
                foot[(at[0] + di, at[1], at[2])] = WHITE
        part(f"{name}Foot{label}", foot, ankle)

# Tail in six joints, ending in a crystal blade.
tail_path = [(0, -3.8, 4.5, 1.3), (0, -5.2, 3.9, 1.02), (0, -6.6, 3.1, 0.82), (0, -8, 2.3, 0.64),
             (0, -9.4, 1.8, 0.48), (0, -10.8, 1.65, 0.36), (0, -12, 1.9, 0.26)]
for n in range(6):
    seg = {}
    tube(seg, tail_path[n:n + 2], belly)
    spine(seg, tail_path[n:n + 2], 0.72, 1 - n * 0.09)
    if n == 5:
        for a, l in ((0, 3.1), (0.28, 2.3), (-0.28, 2.3), (0.55, 1.5), (-0.55, 1.5)):
            spike(seg, (0, -11.8, 1.9), (0, -1, 0.1 + a), l, 0.5)
            spike(seg, (0, -11.8, 1.9), (a, -1, 0.14), l * 0.8, 0.34)
    part(f"Tail{n + 1}", seg, tail_path[n][:3])


def inside(x, z, polygon):
    hit = False
    for (x0, z0), (x1, z1) in zip(polygon, polygon[1:] + polygon[:1]):
        if (z0 > z) != (z1 > z) and x < (x1 - x0) * (z - z0) / (z1 - z0) + x0:
            hit = not hit
    return hit


# Wings: an arm, a forearm, then a panel of fingers and an ice membrane.
for side, label in ((1, "R"), (-1, "L")):
    shoulder, elbow, wrist = (1.7, 0.9, 6.6), (4.3, 0.2, 10.1), (6.5, -0.3, 11.2)
    S = lambda p: (side * p[0], p[1], p[2])
    arm = {}
    tube(arm, [(*S(shoulder), 0.72), (*S(elbow), 0.5)])
    part(f"WingArm{label}", arm, S(shoulder))
    fore = {}
    tube(fore, [(*S(elbow), 0.5), (*S(wrist), 0.42)])
    for n in range(4):
        spike(fore, S((4.5 + n * 0.55, 0.1, 10.55 + n * 0.25)), (side * 0.25, 0, 1), 0.45, 0.2, (WHITE, WHITE))
    part(f"WingFore{label}", fore, S(elbow))

    panel = {}
    tips = [(10.9, 5.1), (8.3, 3.4), (5.5, 3), (2.9, 4.1)]
    valleys = [(9.4, 5.8), (6.9, 4.9), (4.2, 4.9), (2.2, 5.6)]
    outline = [(1.8, 6.8), (4.3, 10.1), (6.5, 11.2), (9, 8.8)]
    for t, v in zip(tips, valleys):
        outline += [t, v]
    y0 = -0.45
    for i in range(int(1.5 / V), int(11.2 / V)):
        for k in range(int(2.8 / V), int(11.4 / V)):
            x, z = i * V, k * V
            if inside(x, z, outline):
                shard = (((i // 3) * 2654435761) ^ (((k + (i // 3) % 2 * 2) // 4) * 40503)) // 64 % 7   # offset ice plates
                tone = BLUE if shard == 0 else ICE if shard < 3 else BRIGHT
                panel[(side * i, round(y0 / V), k)] = tone
    tube(panel, [(*S(wrist), 0.32), (*S((9, -0.5, 8.8)), 0.25), (*S((tips[0][0], -0.55, tips[0][1])), 0.14)])
    for t in tips[1:]:
        tube(panel, [(*S(wrist), 0.26), (*S(((wrist[0] + t[0]) / 2, -0.5, (wrist[2] + t[1]) / 2 + 0.25)), 0.2), (*S((t[0], -0.55, t[1])), 0.12)])
    for t in tips:
        spike(panel, S((t[0], -0.55, t[1] + 0.3)), (side * 0.05, 0, -1), 0.7, 0.2, (WHITE, WHITE))
    spike(panel, S((6.5, -0.3, 11.3)), (side * 0.65, 0, 0.6), 1.25, 0.28, (WHITE, WHITE))
    part(f"WingPanel{label}", panel, S(wrist))

print("BUILT triangles", triangles, "parts", len(joints))
out = HERE / "export"
out.mkdir(exist_ok=True)
(out / "parts.json").write_text(json.dumps(joints, indent=1), encoding="utf8")
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "voxel_dragon.blend"))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(out / "voxel_dragon.glb"), export_format="GLB", use_selection=True, export_animations=False)
print("EXPORTED", (out / "voxel_dragon.glb").stat().st_size // 1024, "KB")

# Preview only: a block the height of the hero shows the scale.
hero = bpy.data.meshes.new("HeroScale")
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1)
bm.to_mesh(hero)
bm.free()
hero_obj = bpy.data.objects.new("HeroScale", hero)
hero_obj.scale = (0.8, 0.8, 1.9)
hero_obj.location = (-5.5, 7, 0.95)
scene.collection.objects.link(hero_obj)

world = bpy.data.worlds.new("World")
scene.world = world
bg = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.012, 0.02, 0.06, 1)
wo = next((n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeOutputWorld"), None) \
    or world.node_tree.nodes.new("ShaderNodeOutputWorld")
world.node_tree.links.new(bg.outputs[0], wo.inputs["Surface"])
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 3.2
sun_data.use_shadow = False   # cube shadows read as noise in previews
sun = bpy.data.objects.new("Sun", sun_data)
sun.rotation_euler = (math.radians(55), 0, math.radians(150))
scene.collection.objects.link(sun)
fill_data = bpy.data.lights.new("Fill", "SUN")
fill_data.energy = 2.2
fill_data.use_shadow = False
fill = bpy.data.objects.new("Fill", fill_data)
fill.rotation_euler = (math.radians(60), 0, math.radians(-40))
scene.collection.objects.link(fill)
cam = bpy.data.cameras.new("Camera")
cam.lens = 50
camera = bpy.data.objects.new("Camera", cam)
scene.collection.objects.link(camera)
scene.camera = camera
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.view_settings.view_transform = "Standard"
target = Vector((0, -1.5, 5.6))
views = (("hero", (-20, 27, 10)), ("side", (-42, -1.5, 6)), ("front", (0, 40, 6)), ("back", (0, -44, 11)), ("face", (-9, 19, 10.5)), ("profile", (-15, 6.5, 9.9)), ("headon", (0, 26, 10)))
for name, at in views:
    target = Vector((0, 6.2, 10.2)) if name in ("face", "profile", "headon") else Vector((0, -1.5, 5.6))
    camera.location = at
    camera.rotation_euler = (target - Vector(at)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out / f"dragon_{name}.png")
    bpy.ops.render.render(write_still=True)
print("DONE")
