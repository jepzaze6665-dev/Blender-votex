"""Rig a character made of separate rigid parts, keyframe clips, and export a GLB.

  blender -b character.blend --python rig_rigid.py -- --config rig.json --out rigged.glb --save rigged.blend

Every mesh follows exactly one bone: no weights, no deformation. A part's object origin
must already sit on its joint. Bones all point along +Y with no roll, so pose rotations
read in model axes (X pitch, Y roll, Z yaw) for every bone. See the skill's rig-config
reference for the JSON format.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--save")
args = ap.parse_args(argv)
config = json.loads(Path(args.config).read_text(encoding="utf-8"))

bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
scene = bpy.context.scene
scene.render.fps = config.get("fps", 24)
BONE_LENGTH = config.get("bone_length", 0.12)

saved = {o.name: o.matrix_world.copy() for o in bpy.data.objects}

data = bpy.data.armatures.new("Rig")
rig = bpy.data.objects.new("Rig", data)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for spec in config["bones"]:
    source = spec.get("from")
    head = saved[source].translation.copy() if source else Vector(spec.get("head", (0, 0, 0)))
    bone = data.edit_bones.new(spec["name"])
    bone.head, bone.tail, bone.roll = head, head + Vector((0, BONE_LENGTH, 0)), 0
for spec in config["bones"]:
    if spec.get("parent"):
        data.edit_bones[spec["name"]].parent = data.edit_bones[spec["parent"]]
bpy.ops.object.mode_set(mode="OBJECT")

for spec in config["bones"]:
    mesh = spec.get("mesh")
    if not mesh:
        continue
    obj = bpy.data.objects[mesh]
    obj.parent, obj.parent_type, obj.parent_bone = rig, "BONE", spec["name"]
bpy.context.view_layer.update()
for spec in config["bones"]:
    if spec.get("mesh"):
        bpy.data.objects[spec["mesh"]].matrix_world = saved[spec["mesh"]]
bpy.context.view_layer.update()

for name in config.get("remove", []):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name])

for spec in config["bones"]:
    rig.pose.bones[spec["name"]].rotation_mode = spec.get("order", "XYZ")

rig.animation_data_create()
tracks = []
for clip in config["clips"]:
    action = bpy.data.actions.new(clip["name"])
    rig.animation_data.action = action
    for bone_name, keys in clip["tracks"].items():
        bone = rig.pose.bones[bone_name]
        for key in keys:
            frame = key["f"]
            bone.rotation_euler = [math.radians(key.get(a, 0)) for a in ("rx", "ry", "rz")]
            bone.location = [key.get(a, 0) for a in ("x", "y", "z")]
            bone.keyframe_insert("rotation_euler", frame=frame)
            bone.keyframe_insert("location", frame=frame)
    slot = rig.animation_data.action_slot
    rig.animation_data.action = None
    track = rig.animation_data.nla_tracks.new()
    track.name = clip["name"]
    strip = track.strips.new(clip["name"], 1, action)
    strip.action_slot = slot
    tracks.append(track)
for bone in rig.pose.bones:
    bone.rotation_euler = (0, 0, 0)
    bone.location = (0, 0, 0)

out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", use_selection=True,
                          export_animations=True, export_animation_mode="NLA_TRACKS",
                          export_skins=False)
print("RIGGED", len(config["bones"]), "bones", [c["name"] for c in config["clips"]], out)

if args.save:
    # Only one clip plays at a time in the saved file; un-mute a track to preview another.
    for i, track in enumerate(tracks):
        track.mute = i != 0
    scene.frame_start, scene.frame_end = 1, max(k["f"] for c in config["clips"][:1] for t in c["tracks"].values() for k in t)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.save).resolve()))
