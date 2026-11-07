"""Build and render the Frost Crescent VFX in Blender 5.2. Deterministic.

  blender -b --factory-startup --python build_frost_crescent.py

Every cube is a real keyframed object, so the .blend can be opened and played. Exports
export/frost_crescent.glb with its animation. The wave stays in place here: travel
across the map is applied by the game, which only plays this animation.
"""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
FRAMES = 24
rng = random.Random(23)
PALETTE = [(0.014, 0.04, 0.19), (0.03, 0.11, 0.48), (0.07, 0.27, 0.78), (0.2, 0.58, 0.95), (0.56, 0.86, 1), (1, 1, 1)]
EMIT = [0.02, 0.06, 0.14, 0.26, 0.4, 0.7]

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
scene = bpy.context.scene
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

meshes = []
h = 0.5
for m in materials:
    mesh = bpy.data.meshes.new("Cube")
    mesh.from_pydata([(x, y, z) for x in (-h, h) for y in (-h, h) for z in (-h, h)], [],
                     [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)])
    mesh.update()
    mesh.materials.append(m)
    meshes.append(mesh)

root = bpy.data.objects.new("FrostCrescent", None)
scene.collection.objects.link(root)
collection = bpy.data.collections.new("VFX_FrostCrescent")
scene.collection.children.link(collection)


def cube(pos, size, level, born, gone, drift=None, turn=0):
    obj = bpy.data.objects.new("Ice", meshes[level])
    collection.objects.link(obj)
    obj.parent = root
    obj.rotation_euler.z = turn
    p = Vector(pos)
    for frame, scale in ((1, 0), (born, 0), (born + 2, size), (gone, size), (gone + 3, 0)):
        obj.scale = (scale,) * 3
        obj.keyframe_insert("scale", frame=max(frame, 1))
    if drift:
        obj.location = p
        obj.keyframe_insert("location", frame=1)
        obj.location = p + Vector(drift)
        obj.keyframe_insert("location", frame=FRAMES)
    else:
        obj.location = p


# Forward is +Y. One clean blade: cubes follow the arc and turn with it, and the band
# narrows to sharp tips. Colour runs in order from the bright inner edge to the deep rim.
RADIUS, CENTRE_Y, SPAN, WIDTH = 4.7, -1.8, 1.28, 1.45
STEP = 0.29
count = 0
a = -SPAN
while a <= SPAN:
    k = abs(a) / SPAN
    width = WIDTH * (1 - k ** 2.2)
    rows = max(1, round(width / STEP))
    size = 0.28 if k < 0.72 else 0.21
    for row in range(rows):
        d = (row + 0.5) / rows
        r = RADIUS + (d - 0.5) * width
        level = 5 if d < 0.16 else 4 if d < 0.38 else 3 if d < 0.62 else 2 if d < 0.84 else 1
        layers = 2 if 0.15 < d < 0.75 and k < 0.8 else 1
        for n in range(layers):
            cube((math.sin(a) * r, math.cos(a) * r + CENTRE_Y, 0.3 + n * size), size, level,
                 1 + round(k * 3), 11 + round((1 - k) * 7 + rng.random() * 2), turn=-a)
            count += 1
    a += STEP / RADIUS
for n in range(44):                    # chips stream straight back off the blade
    a = rng.uniform(-SPAN * 0.92, SPAN * 0.92)
    r = RADIUS - 0.9 - rng.uniform(0, 1.7)
    cube((math.sin(a) * r, math.cos(a) * r + CENTRE_Y, rng.uniform(0.25, 0.8)), rng.choice((0.11, 0.16)), 3 + n % 2,
         2 + n % 5, rng.randint(13, 20), (0, -rng.uniform(1.8, 3), 0), -a)
    count += 1
for frame, s in ((1, 0.84), (FRAMES, 1.12)):
    root.scale = (s, s, 1)
    root.keyframe_insert("scale", frame=frame)
print("CUBES", count)

world = bpy.data.worlds.new("World")
scene.world = world
bg = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.05, 0.08, 0.2, 1)
wo = next((n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeOutputWorld"), None) \
    or world.node_tree.nodes.new("ShaderNodeOutputWorld")
world.node_tree.links.new(bg.outputs[0], wo.inputs["Surface"])
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy, sun_data.color = 1.3, (0.8, 0.9, 1)
sun = bpy.data.objects.new("Sun", sun_data)
sun.rotation_euler = (math.radians(50), 0, math.radians(-25))
scene.collection.objects.link(sun)

# Matches the wide third-person view: behind and above the wave.
cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 30
camera = bpy.data.objects.new("Camera", cam_data)
camera.location = (0, -11.5, 7.2)
camera.rotation_euler = (Vector((0, 0.4, 0.3)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.collection.objects.link(camera)
scene.camera = camera

scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = 24
scene.render.engine = "BLENDER_EEVEE"
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = 640
scene.eevee.taa_render_samples = 24
scene.eevee.use_raytracing = True
scene.eevee.use_shadows = True if hasattr(scene.eevee, 'use_shadows') else None
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "vfx_frost_crescent.blend"))
# The game plays this GLB, so the effect stays sharp and real 3D from any camera.
out = HERE / "export"
out.mkdir(exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
root.select_set(True)
for obj in collection.objects:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out / "frost_crescent.glb"), export_format="GLB", use_selection=True,
                          export_animations=True, export_animation_mode="SCENE", export_force_sampling=False)
print("EXPORTED", (out / "frost_crescent.glb").stat().st_size // 1024, "KB")
