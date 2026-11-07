"""Build the voxel character from voxels.json. Blender 5.2, deterministic.

  blender -b --factory-startup --python build_character.py

Each body part is a separate mesh whose origin is its joint, so an engine can pose it by
rotating the part: no skinning needed. Hand_R marks where a weapon attaches. The character
faces +Y in Blender, which is -Z in glTF. Writes the .blend, export/voxel_character.glb,
and four review renders.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
VOXEL = 0.02   # 96 voxels is 1.92 m

SIDES = [
    ((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
    ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
    ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]),
    ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
    ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
    ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)]),
]


def main():
    data = json.loads((HERE / "voxels.json").read_text(encoding="utf-8"))
    centre, side_mid = data["centre"] + 0.5, data["side_mid"] + 0.5
    palette = data["palette"]
    n = len(palette)

    def world(c, y, s):
        # Grid column runs screen-left to right, which is the character's right to left.
        return (-(c - centre) * VOXEL, -(s - side_mid) * VOXEL, y * VOXEL)

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    scene = bpy.context.scene

    base = bpy.data.images.new("T_CharPalette", n, 1, alpha=False)
    emit = bpy.data.images.new("T_CharEmission", n, 1, alpha=False)
    base_px, emit_px = [], []
    for r, g, b in palette:
        base_px += [r / 255, g / 255, b / 255, 1]
        k = 1.0 if b > 240 and g > 205 else 0.0     # only the brightest ice glows; trims stay armour
        emit_px += [r / 255 * k, g / 255 * k, b / 255 * k, 1]
    base.pixels, emit.pixels = base_px, emit_px
    base.pack(); emit.pack()

    material = bpy.data.materials.new("M_Character")
    tree = material.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    for image, socket in ((base, "Base Color"), (emit, "Emission Color")):
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image, tex.interpolation = image, "Closest"
        tree.links.new(tex.outputs["Color"], shader.inputs[socket])
    shader.inputs["Roughness"].default_value = 0.6
    shader.inputs["Metallic"].default_value = 0.05
    shader.inputs["Emission Strength"].default_value = 1.2
    tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])

    groups = {}
    for c, y, s, mat, part in data["voxels"]:
        groups.setdefault(part, {})[(c, y, s)] = mat

    edge, axis = data["arm_edge"], data["leg_axis"]

    def top_of(name, drop):
        """Joint at the middle of a part's top slice, lowered by drop voxels."""
        cells = list(groups[data["parts"].index(name)])
        top = max(k[1] for k in cells)
        band = [k for k in cells if k[1] >= top - 4]
        return (sum(k[0] for k in band) / len(band) + 0.5, top - drop, sum(k[2] for k in band) / len(band) + 0.5)
    rows = data["grid"][1]

    def centre_of(name):
        cells = list(groups[data["parts"].index(name)])
        n_ = len(cells)
        return tuple(sum(k[i] for k in cells) / n_ + 0.5 for i in range(3))

    joints = {
        "Torso": (centre, rows * 0.54, side_mid), "Hips": (centre, rows * 0.47, side_mid),
        "Head": (centre, data["neck"], side_mid),
        "LegR": (centre - axis, data["belt"] * 0.9, side_mid), "LegL": (centre + axis, data["belt"] * 0.9, side_mid),
        "HandR": centre_of("HandR"), "HandL": centre_of("HandL"),
    }
    for name, drop in (("ArmR", 0), ("ArmL", 0), ("ForeR", 0), ("ForeL", 0), ("FootR", 0), ("FootL", 0),
                       ("SkirtF", 0), ("SkirtB", 0), ("SkirtR", 0), ("SkirtL", 0), ("PadR", 7), ("PadL", 7)):
        joints[name] = top_of(name, drop)

    root = bpy.data.objects.new("Character", None)
    scene.collection.objects.link(root)
    objects, triangles = {}, 0
    for index, name in enumerate(data["parts"]):
        cells = groups.get(index, {})
        pivot = Vector(world(*joints[name]))
        vert_index, verts, faces, mats = {}, [], [], []
        for (x, y, z), mat in cells.items():
            for normal, corners in SIDES:
                if (x + normal[0], y + normal[1], z + normal[2]) in cells:
                    continue
                quad = []
                for cx, cy, cz in corners:
                    key = (x + cx, y + cy, z + cz)
                    if key not in vert_index:
                        vert_index[key] = len(verts)
                        verts.append(Vector(world(*key)) - pivot)
                    quad.append(vert_index[key])
                # The grid-to-world mapping mirrors space, so the winding must flip too.
                faces.append(quad[::-1])
                mats.append(mat)
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        uv = mesh.uv_layers.new(name="palette")
        for poly, mat in zip(mesh.polygons, mats):
            for loop in poly.loop_indices:
                uv.uv[loop].vector = ((mat + 0.5) / n, 0.5)
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name, mesh)
        obj.location = pivot
        scene.collection.objects.link(obj)
        obj.parent = root
        objects[name] = obj
        triangles += len(faces) * 2

    print("BUILT", {k: len(v.data.polygons) * 2 for k, v in objects.items()}, "triangles", triangles)

    (HERE / "export").mkdir(exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(HERE / "export" / "voxel_character.glb"), export_format="GLB",
                              use_selection=True, export_animations=False)

    world_data = bpy.data.worlds.new("World")
    scene.world = world_data
    node = world_data.node_tree.nodes.get("Background") or world_data.node_tree.nodes.new("ShaderNodeBackground")
    node.inputs["Color"].default_value = (0.012, 0.016, 0.03, 1)
    wout = next((x for x in world_data.node_tree.nodes if x.bl_idname == "ShaderNodeOutputWorld"), None) \
        or world_data.node_tree.nodes.new("ShaderNodeOutputWorld")
    world_data.node_tree.links.new(node.outputs[0], wout.inputs["Surface"])

    rig = bpy.data.objects.new("CameraRig", None)
    rig.location = (0, 0, 0.96)
    scene.collection.objects.link(rig)
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 70
    camera = bpy.data.objects.new("Camera", cam_data)
    camera.parent = rig
    camera.location = (0, 5.2, 0)
    camera.rotation_euler = (math.pi / 2, 0, math.pi)
    scene.collection.objects.link(camera)
    scene.camera = camera
    fill = bpy.data.lights.new("Fill", "AREA")
    fill.energy, fill.size, fill.color = 300, 4, (0.85, 0.9, 1)
    fill_obj = bpy.data.objects.new("Fill", fill)
    fill_obj.parent = rig
    fill_obj.location = (1.2, 4, 1.6)
    fill_obj.rotation_euler = (Vector((0, 0, 0)) - fill_obj.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill_obj)

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 600, 800
    scene.view_settings.view_transform = "Standard"
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "voxel_character.blend"))
    renders = HERE / "renders"
    renders.mkdir(exist_ok=True)
    for name, angle in (("front", 0), ("side", 90), ("back", 180), ("three_quarter", 35)):
        rig.rotation_euler = (0, 0, math.radians(angle))
        scene.render.filepath = str(renders / f"{name}.png")
        bpy.ops.render.render(write_still=True)


main()
