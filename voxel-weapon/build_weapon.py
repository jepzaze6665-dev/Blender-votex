"""Build the voxel weapon scene from voxels.json. Blender 5.2, deterministic.

  blender -b --factory-startup --python build_weapon.py -- --save --glb
  blender -b --factory-startup --python build_weapon.py -- --stills 1,37,73,109
  blender -b --factory-startup --python build_weapon.py -- --anim

The GLB is exported before the animated shader nodes are added, because glTF keeps
plain textures and emissive strength but not a procedural pulse. The pulse route is
still shipped as a second UV set (TEXCOORD_1, U = distance along the weapon), so an
engine shader can recreate it.
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
VOXEL = 0.015          # metres: 128 voxels is about 1.9 m
CYCLE = 72             # frames per pulse
FRAMES = CYCLE * 2     # one camera orbit, seamless when looped
FPS = 24
GLOW_STRENGTH = 2.6
EMIT_SHARE = [0.0, 0.0, 0.14, 0.55, 1.0]   # how much each palette colour emits
PULSE_START, PULSE_END, PULSE_WIDTH = -0.4, 2.6, 0.13  # dark at both ends, so the wrap is invisible
HEAD_FRAME = 1 + CYCLE * (1.0 - PULSE_START) / (PULSE_END - PULSE_START)  # pulse reaches p = 1

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def flag(name):
    return name in args


def option(name):
    return args[args.index(name) + 1] if name in args else None


def pulse_at(frame):
    """Brightness of the pulse where it meets the head crystal, 0 to 1."""
    f = (frame - 1) % CYCLE
    t = PULSE_START + (PULSE_END - PULSE_START) * f / CYCLE
    return math.exp(-(((1.0 - t) / PULSE_WIDTH) ** 2))


# ---------------------------------------------------------------- mesh

FACES = [
    ((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
    ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
    ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]),
    ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
    ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
    ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)]),
]


def voxel_mesh(name, cells, origin, palette_size):
    """Only faces that touch air are built, which removes most of the geometry."""
    index, verts, faces, face_data = {}, [], [], []
    for (x, y, z), (mat, pulse) in cells.items():
        for normal, corners in FACES:
            if (x + normal[0], y + normal[1], z + normal[2]) in cells:
                continue
            quad = []
            for cx, cy, cz in corners:
                key = (x + cx, y + cy, z + cz)
                if key not in index:
                    index[key] = len(verts)
                    # Grid x is across, grid y is up, grid z is depth.
                    verts.append(((key[0] - origin[0]) * VOXEL, (key[2] - origin[2]) * VOXEL,
                                  (key[1] - origin[1]) * VOXEL))
                quad.append(index[key])
            faces.append(quad[::-1])  # swapping y and z mirrors the winding
            face_data.append((mat, pulse))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    palette_uv = mesh.uv_layers.new(name="palette")
    pulse_uv = mesh.uv_layers.new(name="pulse")
    for poly, (mat, pulse) in zip(mesh.polygons, face_data):
        for loop in poly.loop_indices:
            palette_uv.uv[loop].vector = ((mat + 0.5) / palette_size, 0.5)
            pulse_uv.uv[loop].vector = (pulse, 0.5)
    mesh.uv_layers.active = palette_uv
    return mesh


def palette_image(name, colours):
    image = bpy.data.images.new(name, len(colours), 1, alpha=False)
    image.pixels = [v for c in colours for v in (c[0], c[1], c[2], 1.0)]
    image.pack()
    return image


def voxel_material(base_image, emit_image):
    material = bpy.data.materials.new("M_Voxel")
    tree = material.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "palette"
    for image, socket in ((base_image, "Base Color"), (emit_image, "Emission Color")):
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Closest"
        tree.links.new(uv.outputs["UV"], tex.inputs["Vector"])
        tree.links.new(tex.outputs["Color"], shader.inputs[socket])
    shader.inputs["Metallic"].default_value = 0.1
    shader.inputs["Roughness"].default_value = 0.5
    shader.inputs["Emission Strength"].default_value = GLOW_STRENGTH
    tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    return material


def add_pulse(material):
    """Emission Strength = base * (1 + boost * gaussian(position - pulse head))."""
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    shader = next(n for n in nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "pulse"
    split = nodes.new("ShaderNodeSeparateXYZ")
    links.new(uv.outputs["UV"], split.inputs[0])
    head = nodes.new("ShaderNodeValue")
    head.name = "PulseHead"

    def math_node(op, a, b=None):
        node = nodes.new("ShaderNodeMath")
        node.operation = op
        for i, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, (int, float)):
                node.inputs[i].default_value = value
            else:
                links.new(value, node.inputs[i])
        return node.outputs[0]

    scaled = math_node("DIVIDE", math_node("SUBTRACT", split.outputs["X"], head.outputs[0]), PULSE_WIDTH)
    bump = math_node("EXPONENT", math_node("MULTIPLY", math_node("MULTIPLY", scaled, scaled), -1.0))
    strength = math_node("MULTIPLY", math_node("ADD", math_node("MULTIPLY", bump, 7.0), 1.0), GLOW_STRENGTH)
    links.new(strength, shader.inputs["Emission Strength"])
    for frame, value in ((1, PULSE_START), (CYCLE, PULSE_END), (CYCLE + 1, PULSE_START),
                         (FRAMES, PULSE_END)):
        head.outputs[0].default_value = value
        head.outputs[0].keyframe_insert("default_value", frame=frame)


def emission_material(name, colour, strength):
    material = bpy.data.materials.new(name)
    tree = material.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*colour, 1)
    emit.inputs["Strength"].default_value = strength
    tree.links.new(emit.outputs[0], out.inputs["Surface"])
    return material


# ---------------------------------------------------------------- scene pieces

def add_sparks(root, glow_points, centre):
    """Small cubes rising off the glowing parts. Periodic in CYCLE, so the clip loops."""
    rng = random.Random(7)
    cube = bpy.data.meshes.new("Spark")
    h = 0.5
    verts = [(x, y, z) for x in (-h, h) for y in (-h, h) for z in (-h, h)]
    cube.from_pydata(verts, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    cube.materials.append(emission_material("M_Spark", (0.3, 0.75, 1.0), 5.0))
    collection = bpy.data.collections.new("VFX_Sparks")
    bpy.context.scene.collection.children.link(collection)
    for i in range(48):
        obj = bpy.data.objects.new(f"Spark_{i:02d}", cube)
        collection.objects.link(obj)
        obj.parent = root
        start = Vector(rng.choice(glow_points))
        drift = Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), rng.uniform(0.1, 0.34)))
        phase, size = rng.random(), VOXEL * rng.uniform(0.6, 1.5)
        for frame in range(1, FRAMES + 1, 4):
            life = ((frame - 1) / CYCLE + phase) % 1.0
            obj.location = start + drift * life
            obj.scale = (size * math.sin(math.pi * life),) * 3
            obj.keyframe_insert("location", frame=frame)
            obj.keyframe_insert("scale", frame=frame)
    # Four diamonds pop outward as the pulse arrives at the head crystal.
    burst = bpy.data.objects
    for i in range(4):
        obj = burst.new(f"Burst_{i}", cube)
        collection.objects.link(obj)
        obj.parent = root
        angle = math.pi / 4 + i * math.pi / 2
        direction = Vector((math.cos(angle), 0, math.sin(angle)))
        obj.rotation_euler = (0, math.pi / 4, 0)
        for frame in range(1, FRAMES + 1, 2):
            f = (frame - HEAD_FRAME) % CYCLE
            f = f - CYCLE if f > CYCLE / 2 else f
            pop = math.exp(-((f - 5) / 6) ** 2) if f > -6 else 0.0
            obj.location = centre + direction * (0.11 + 0.012 * max(f, 0))
            obj.scale = (VOXEL * 2.2 * pop,) * 3
            obj.keyframe_insert("location", frame=frame)
            obj.keyframe_insert("scale", frame=frame)


def add_stage(centre):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("World")
    scene.world = world
    background = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
    background.inputs["Color"].default_value = (0.006, 0.008, 0.016, 1)
    background.inputs["Strength"].default_value = 1.0
    output = next((n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeOutputWorld"), None) \
        or world.node_tree.nodes.new("ShaderNodeOutputWorld")
    world.node_tree.links.new(background.outputs[0], output.inputs["Surface"])

    def area(name, location, energy, colour, size):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.color, data.size = energy, colour, size
        light = bpy.data.objects.new(name, data)
        light.location = location
        direction = Vector(centre) - Vector(location)
        light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(light)

    area("Rim_L", (2.6, 2.2, 1.4), 90, (0.35, 0.6, 1.0), 2.0)
    area("Rim_R", (-2.6, 2.4, 0.6), 60, (0.3, 0.5, 1.0), 2.0)

    # A light at the crystal, so the flare also touches the frame around it.
    data = bpy.data.lights.new("CrystalLight", "POINT")
    data.color, data.shadow_soft_size = (0.35, 0.72, 1.0), 0.05
    crystal = bpy.data.objects.new("CrystalLight", data)
    crystal.location = centre
    scene.collection.objects.link(crystal)
    for frame in range(1, FRAMES + 1, 2):
        data.energy = 6 + 60 * pulse_at(frame)
        data.keyframe_insert("energy", frame=frame)


def add_camera(height_centre, distance):
    scene = bpy.context.scene
    rig = bpy.data.objects.new("CameraRig", None)
    rig.location = (0, 0, height_centre)
    scene.collection.objects.link(rig)
    data = bpy.data.cameras.new("Camera")
    data.lens = 70
    camera = bpy.data.objects.new("Camera", data)
    camera.parent = rig
    camera.location = (0, -distance, 0.1)
    camera.rotation_euler = (math.pi / 2 - math.atan2(0.1, distance), 0, 0)
    scene.collection.objects.link(camera)
    scene.camera = camera
    fill = bpy.data.lights.new("CameraFill", "AREA")
    fill.energy, fill.color, fill.size = 260, (0.78, 0.86, 1.0), 3.0
    fill_obj = bpy.data.objects.new("CameraFill", fill)
    fill_obj.parent = rig
    fill_obj.location = (-1.2, -distance * 0.8, 1.6)
    fill_obj.rotation_euler = (Vector((0, 0, 0)) - fill_obj.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill_obj)
    for frame, angle in ((1, 0.0), (FRAMES + 1, math.tau)):
        rig.rotation_euler = (0, 0, angle)
        rig.keyframe_insert("rotation_euler", frame=frame)


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1440
    scene.eevee.taa_render_samples = 32
    scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    tree = bpy.data.node_groups.new("Bloom", "CompositorNodeTree")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    layers = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = 1.0
    glare.inputs["Strength"].default_value = 0.3
    glare.inputs["Size"].default_value = 0.55
    out = tree.nodes.new("NodeGroupOutput")
    tree.links.new(layers.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], out.inputs[0])
    scene.compositing_node_group = tree
    scene.render.use_compositing = True


# ---------------------------------------------------------------- build

def main():
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    scene = bpy.context.scene

    data = json.loads((HERE / "voxels.json").read_text(encoding="utf-8"))
    palette = [[pow(v / 255, 1.0) for v in p["rgb"]] for p in data["palette"]]
    groups = {}
    for x, y, z, mat, pulse, island in data["voxels"]:
        groups.setdefault(island, {})[(x, y, z)] = (mat, pulse)
    core = groups[0]

    # Hold the weapon at the middle of the shaft: the origin is what a hand attaches to.
    width, height = data["grid"]
    low = [k[0] for k in core if k[1] < height * 0.3]
    origin = (sorted(low)[len(low) // 2] + 0.5, height * 0.5, 0.5)

    base = palette_image("T_Palette", palette)
    emit = palette_image("T_Emission", [[v * k for v in c] for c, k in zip(palette, EMIT_SHARE)])
    material = voxel_material(base, emit)

    collection = bpy.data.collections.new("Weapon")
    scene.collection.children.link(collection)
    root = bpy.data.objects.new("Weapon_Root", None)
    collection.objects.link(root)
    parts = []
    for island, cells in sorted(groups.items()):
        name = "Weapon" if island == 0 else f"FloatingShard_{island}"
        mesh = voxel_mesh(name, cells, origin, len(palette))
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.parent = root
        parts.append(obj)
    triangles = sum(len(p.data.polygons) * 2 for p in parts)
    print(f"BUILT parts={len(parts)} triangles={triangles} "
          f"height={(height * VOXEL):.2f}m width={(width * VOXEL):.2f}m")

    if flag("--glb"):
        bpy.ops.object.select_all(action="DESELECT")
        root.select_set(True)
        for part in parts:
            part.select_set(True)
        path = HERE / "export" / "voxel_weapon.glb"
        path.parent.mkdir(exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                                  export_animations=False, export_texcoords=True, export_normals=True)
        print(f"GLB {path} {path.stat().st_size / 1024:.0f} KB")

    add_pulse(material)
    for i, part in enumerate(parts[1:]):
        for frame in range(1, FRAMES + 1, 6):
            part.location.z = 0.012 * math.sin(math.tau * ((frame - 1) / CYCLE + i * 0.37))
            part.keyframe_insert("location", frame=frame)

    def world_point(key):
        return ((key[0] + 0.5 - origin[0]) * VOXEL, (key[2] + 0.5 - origin[2]) * VOXEL,
                (key[1] + 0.5 - origin[1]) * VOXEL)

    glow = [world_point(k) for k, (mat, pulse) in core.items() if mat >= 3 and k[1] > height * 0.55]
    head = [Vector(world_point(k)) for k, (mat, pulse) in core.items()
            if mat == 4 and k[1] > height * 0.7 and k[0] > width * 0.45]
    centre = sum(head, Vector()) / len(head)
    add_sparks(root, glow, centre)

    add_stage(centre)
    add_camera(0.0, 5.0)
    setup_render()

    if flag("--save"):
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "voxel_weapon.blend"))
    renders = HERE / "renders"
    renders.mkdir(exist_ok=True)
    if option("--stills"):
        for frame in option("--stills").split(","):
            scene.frame_set(int(frame))
            scene.render.filepath = str(renders / f"still_{int(frame):03d}.png")
            bpy.ops.render.render(write_still=True)
    if flag("--anim"):
        scene.render.filepath = str(renders / "frames" / "f_")
        bpy.ops.render.render(animation=True)


main()
