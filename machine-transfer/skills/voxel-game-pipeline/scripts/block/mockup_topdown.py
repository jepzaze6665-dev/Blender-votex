"""Render a still mockup of the block character in a high-angle view. Graphics only.

  blender -b voxel_block.blend --python mockup_topdown.py
"""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
rng = random.Random(11)
scene = bpy.context.scene

for name in ("CameraRig", "Camera", "Fill"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name])
parts = list(bpy.data.objects)

hero = bpy.data.objects.new("Hero", None)
scene.collection.objects.link(hero)
for part in parts:
    part.parent = hero
hero.rotation_euler = (0, 0, math.radians(215))
hero.scale = (1.25, 1.25, 1.25)

bpy.ops.import_scene.gltf(filepath=str(HERE.parent / "voxel-weapon" / "export" / "voxel_weapon.glb"))
weapon = bpy.data.objects.new("WeaponPose", None)
scene.collection.objects.link(weapon)
for obj in bpy.context.selected_objects:
    if obj.parent is None:
        obj.parent = weapon
weapon.parent = hero
weapon.location = (0.52, 0.28, 0.68)
weapon.rotation_euler = (math.radians(8), math.radians(22), math.pi)
weapon.scale = (0.8, 0.8, 0.8)


def material(name, colour, emit=0.0):
    m = bpy.data.materials.new(name)
    s = m.node_tree.nodes.get("Principled BSDF") or m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    if not s.outputs[0].is_linked:
        out = next((n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeOutputMaterial"), None) \
            or m.node_tree.nodes.new("ShaderNodeOutputMaterial")
        m.node_tree.links.new(s.outputs[0], out.inputs["Surface"])
    s.inputs["Base Color"].default_value = (*colour, 1)
    s.inputs["Roughness"].default_value = 0.75
    if emit:
        s.inputs["Emission Color"].default_value = (*colour, 1)
        s.inputs["Emission Strength"].default_value = emit
    return m


cube = bpy.data.meshes.new("Cube")
h = 0.5
cube.from_pydata([(x, y, z) for x in (-h, h) for y in (-h, h) for z in (-h, h)], [],
                 [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
cube.update()
for poly in cube.polygons:
    poly.flip()
cube.update()


def block(loc, size, mat):
    data = cube.copy()
    data.materials.append(mat)
    o = bpy.data.objects.new("Block", data)
    o.location, o.scale = loc, size
    scene.collection.objects.link(o)
    return o


snow_a = material("SnowA", (0.34, 0.45, 0.66))
snow_b = material("SnowB", (0.29, 0.39, 0.6))
path = material("Path", (0.12, 0.16, 0.3))
trunk = material("Trunk", (0.05, 0.07, 0.16))
leaf = material("Leaf", (0.05, 0.16, 0.34))
leaf2 = material("Leaf2", (0.1, 0.27, 0.5))
wall = material("Wall", (0.16, 0.24, 0.47))
roof = material("Roof", (0.03, 0.07, 0.22))
crystal = material("Crystal", (0.12, 0.5, 1.0), 1.1)
enemy = material("Enemy", (0.24, 0.12, 0.42))
eye = material("Eye", (1, 1, 1), 2.0)
ring = material("Ring", (0.1, 0.55, 1.0), 1.2)

for x in range(-14, 15):
    for y in range(-14, 15):
        on_path = abs(y + x * 0.25) < 1.2
        block((x, y, -0.25 + rng.uniform(-0.02, 0.02)), (1, 1, 0.5), path if on_path else (snow_a if (x + y) % 2 else snow_b))


def tree(x, y):
    block((x, y, 0.6), (0.4, 0.4, 1.2), trunk)
    block((x, y, 1.5), (1.7, 1.7, 0.8), leaf)
    block((x, y, 2.2), (1.1, 1.1, 0.7), leaf2)


for x, y in ((-6, 4), (-8, 1), (-3, 7), (5, 6), (8, 3), (7, -6), (-7, -6), (2, -8), (-10, 6), (10, -1)):
    tree(x, y)
block((-3.5, 3.2, 1.1), (3.4, 2.8, 2.2), wall)
block((-3.5, 3.2, 2.5), (3.9, 3.3, 0.6), roof)
block((-3.5, 3.2, 3.0), (2.5, 2.0, 0.5), roof)
block((-3.5, 1.76, 0.6), (0.7, 0.05, 1.2), crystal)
block((3.5, 2.2, 0.8), (0.5, 0.5, 1.6), crystal)
block((-1.4, -4.2, 0.45), (0.5, 0.5, 0.9), crystal)


def foe(x, y, size, turn):
    b = block((x, y, size / 2), (size, size, size), enemy)
    b.rotation_euler.z = turn
    for side in (-1, 1):
        e = block((side * 0.22, -0.51, 0.16), (0.16, 0.03, 0.16), eye)
        e.parent = b


foe(2.1, -0.8, 0.62, 0.8)
foe(3.6, -2.5, 0.58, 0.5)
foe(4.7, 0.6, 0.75, 1.0)
foe(-4.0, -2.5, 0.58, -0.4)

for i in range(24):
    a = i / 24 * math.tau
    block((2.1 + math.cos(a) * 0.62, -0.8 + math.sin(a) * 0.62, 0.04), (0.12, 0.12, 0.05), ring)

world = bpy.data.worlds.new("World")
scene.world = world
bg = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.02, 0.03, 0.08, 1)
bg.inputs["Strength"].default_value = 1.2
wo = next((n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeOutputWorld"), None) \
    or world.node_tree.nodes.new("ShaderNodeOutputWorld")
world.node_tree.links.new(bg.outputs[0], wo.inputs["Surface"])

sun = bpy.data.lights.new("Sun", "SUN")
sun.energy, sun.color, sun.angle = 2.2, (0.82, 0.9, 1), math.radians(10)
sun_obj = bpy.data.objects.new("Sun", sun)
sun_obj.rotation_euler = (math.radians(52), 0, math.radians(-35))
scene.collection.objects.link(sun_obj)

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 34
camera = bpy.data.objects.new("Camera", cam_data)
camera.location = (7.5, -11.5, 11.0)
camera.rotation_euler = (Vector((0.5, -0.3, 0.6)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.collection.objects.link(camera)
scene.camera = camera
fill = bpy.data.lights.new("HeroFill", "POINT")
fill.energy, fill.color = 90, (0.7, 0.85, 1)
fill_obj = bpy.data.objects.new("HeroFill", fill)
fill_obj.location = (1.5, -2.5, 3)
scene.collection.objects.link(fill_obj)

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
scene.eevee.taa_render_samples = 48
scene.view_settings.view_transform = "Standard"
out = HERE / "export"
out.mkdir(exist_ok=True)
scene.render.filepath = str(out / "topdown_scene.png")
bpy.ops.render.render(write_still=True)
import json
from bpy_extras.object_utils import world_to_camera_view


def pixel(point):
    v = world_to_camera_view(scene, camera, Vector(point))
    return [round(v.x * 1600), round((1 - v.y) * 900)]


(out / "topdown_labels.json").write_text(json.dumps({"hero": pixel((0, 0, 2.25)), "foe": pixel((2.1, -0.8, 1.15))}))
print("RENDERED")
