"""Sculpt the ice prison around the dragon and keyframe its break. Deterministic.

  blender -b --factory-startup --python build_dragon_ice.py

Crystals stand on a dome that fits the crouched dragon, in the dragon's model space.
They tremble from 1.5 s and burst at 3 s, matching the dragon's Intro clip.
Writes export/voxel_dragon_ice.glb and export/dragon_ice_preview.png.
"""
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Vector

HERE = Path(__file__).resolve().parent
V, FPS, TREMBLE, BURST, END = 0.5, 24, 37, 73, 125
rng = random.Random(21)
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, END

materials = []
for name, colour, power, alpha in (("M_IceDeep", (0.02, 0.12, 0.5), 0.06, 0.4), ("M_IceBright", (0.08, 0.36, 0.9), 0.12, 0.5), ("M_IceEdge", (0.45, 0.78, 1), 0.25, 0.75), ("M_IceCrack", (0.02, 0.12, 0.5), 1, 0.6)):
    m = bpy.data.materials.new(name)
    tree = m.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (*colour, 1)
    shader.inputs["Emission Color"].default_value = (*colour, 1)
    shader.inputs["Emission Strength"].default_value = power
    shader.inputs["Alpha"].default_value = alpha
    shader.inputs["Roughness"].default_value = 0.25
    tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    m.surface_render_method = "BLENDED"
    materials.append(m)

# The page reveals these veins outward from the dragon's core.
materials[3].node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (0.6, 0.95, 1, 1)

collection = bpy.data.collections.new("Ice")
scene.collection.children.link(collection)
SIDES = [((1, 0, 0), (0, 1, 0)), ((-1, 0, 0), (0, 1, 0)), ((0, 1, 0), (0, 0, 1)), ((0, -1, 0), (0, 0, 1)), ((0, 0, 1), (1, 0, 0)), ((0, 0, -1), (1, 0, 0))]
triangles = 0


def crystal(length, radius):
    """A tall faceted crystal along +Z."""
    cells = {}
    steps = int(length / V)
    for k in range(steps):
        t = k / steps
        r = radius * min(1, 0.55 + t * 2.5) * (1 - max(t - 0.55, 0) / 0.45) ** 0.9
        c = int(r / V) + 1
        for i in range(-c, c + 1):
            for j in range(-c, c + 1):
                if abs(i * V) + abs(j * V) <= r * 1.3:
                    edge = (abs(i * V) + abs(j * V)) / max(r * 1.3, 0.01)
                    cells[(i, j, k)] = 3 if (i * 2 + j + k) % 7 == 0 and edge > 0.4 else 2 if t > 0.82 or (edge > 0.82 and (k + i) % 3 == 0) else 1 if edge > 0.45 else 0
    return cells


def mesh_object(name, cells):
    global triangles
    bm = bmesh.new()
    for (i, j, k), level in cells.items():
        centre = Vector((i, j, k)) * V
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
    triangles += len(mesh.polygons) * 2
    return obj


CENTRE = Vector((0, -1, 0))
RADII = Vector((8.2, 11, 10.5))
COUNT = 30
for n in range(COUNT):
    # Golden-angle points over the upper dome.
    z = 0.03 + 0.97 * (n + 0.5) / COUNT
    ring = math.sqrt(1 - z * z)
    a = n * 2.39996
    unit = Vector((math.cos(a) * ring, math.sin(a) * ring, z))
    base = CENTRE + Vector((unit.x * RADII.x, unit.y * RADII.y, unit.z * RADII.z)) * 0.62
    out = Vector((unit.x / RADII.x, unit.y / RADII.y, unit.z / RADII.z)).normalized()
    direction = (out + Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0.28))).normalized()
    length = rng.uniform(4.6, 7.4) * (1.15 - z * 0.35)
    radius = rng.uniform(1.2, 1.9)
    obj = mesh_object(f"Ice{n}", crystal(length, radius))
    rest = direction.to_track_quat("Z", "Y").to_euler()
    obj.rotation_mode = "XYZ"
    speed = rng.uniform(13, 24)
    velocity = (out * speed + Vector((0, 0, rng.uniform(6, 13))))
    spin = Vector((rng.uniform(-7, 7), rng.uniform(-7, 7), rng.uniform(-7, 7)))
    for f in list(range(1, TREMBLE, 12)) + list(range(TREMBLE, BURST, 2)) + list(range(BURST, END + 1, 3)):
        if f < BURST:
            amount = 0 if f < TREMBLE else 0.03 + 0.2 * (f - TREMBLE) / (BURST - TREMBLE)
            obj.location = base + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * amount
            obj.rotation_euler = rest
            obj.scale = (1, 1, 1)
        else:
            t = (f - BURST) / FPS
            obj.location = base + velocity * t + Vector((0, 0, -15 * t * t))
            obj.rotation_euler = Euler(tuple(r + s * t for r, s in zip(rest, spin)))
            fade = max(0.001, 1 - ((f - BURST) / (END - BURST)) ** 2.5)
            obj.scale = (fade, fade, fade)
        obj.keyframe_insert("location", frame=f)
        obj.keyframe_insert("rotation_euler", frame=f)
        obj.keyframe_insert("scale", frame=f)
print("BUILT triangles", triangles)

out_dir = HERE / "export"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(out_dir / "voxel_dragon_ice.glb"), export_format="GLB", use_selection=True,
                          export_animations=True, export_animation_mode="SCENE", export_force_sampling=True)
print("EXPORTED", (out_dir / "voxel_dragon_ice.glb").stat().st_size // 1024, "KB")

# Crystal pillars for the roar: an arc behind the dragon, leaving the south side open.
# Each origin sits at the pillar's base so the page can grow it from the ground.
for obj in list(collection.objects):
    bpy.data.objects.remove(obj)
pillars = 14
for n in range(pillars):
    a = math.radians(165 + n * (210 / (pillars - 1)))
    r = rng.uniform(14, 15.2)
    obj = mesh_object(f"Pillar{n}", crystal(rng.uniform(8, 13.5), rng.uniform(1.3, 2)))
    obj.location = (math.cos(a) * r, -math.sin(a) * r, -0.6)
    obj.rotation_euler = Vector((math.cos(a) * 0.22, -math.sin(a) * 0.22, 1)).normalized().to_track_quat("Z", "Y").to_euler()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(out_dir / "voxel_dragon_pillars.glb"), export_format="GLB", use_selection=True, export_animations=False)
print("PILLARS", (out_dir / "voxel_dragon_pillars.glb").stat().st_size // 1024, "KB")

world = bpy.data.worlds.new("World")
scene.world = world
bg = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.012, 0.02, 0.06, 1)
wo = next((n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeOutputWorld"), None) or world.node_tree.nodes.new("ShaderNodeOutputWorld")
world.node_tree.links.new(bg.outputs[0], wo.inputs["Surface"])
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 2.5
sun = bpy.data.objects.new("Sun", sun_data)
sun.rotation_euler = (math.radians(55), 0, math.radians(150))
scene.collection.objects.link(sun)
cam = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", cam)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = (-24, 30, 12)
camera.rotation_euler = (Vector((0, -1, 5)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.frame_set(1)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.view_settings.view_transform = "Standard"
scene.render.filepath = str(out_dir / "dragon_ice_preview.png")
bpy.ops.render.render(write_still=True)
print("DONE")
