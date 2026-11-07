---
name: rigid-part-rigging
description: Rig and animate characters built from separate solid parts, such as voxel, blocky, low-poly, or toy-like characters whose head, torso, arms, and legs move without bending. Covers splitting parts, placing joints, building a Blender armature, keyframing snappy game clips (idle, walk, attack), attaching weapons through sockets, exporting a GLB, and playing clips in a web or game engine. Use this whenever the user wants to rig, animate, or make a voxel or block character move, asks for "Rigid Part Rigging", "ใส่กระดูก", "ทำริก", "แยกชิ้นส่วนตัวละคร", "ให้ตัวละครขยับ", "ท่าเดิน", "ท่าฟัน", or wants movement like a blocky voxel game. Not for smooth skinned characters that need weight painting.
---

# Rigid Part Rigging

Each body part is a solid piece that follows one bone. Nothing bends, so there is no weight painting, the same clip works on any character with the same bone names, and clips stay light. The style comes from timing rather than from mesh quality: few keys, strong poses, fast transitions.

Write to the user in their language. They may be new to Blender, so explain rig terms the first time you use them.

## 1. Check the parts

The rig is only as good as the split. Before rigging, confirm:

- One mesh object per moving part, named clearly (Head, Torso, ArmR, ArmL, LegR, LegL).
- Each object's origin sits on its joint: shoulder, hip, neck. A wrong origin makes the part swing around the wrong point, and it is the most common fault.
- The model stands at the world origin with feet at Z = 0 and faces +Y, so a GLB faces -Z.
- Each part keeps closed faces where it meets its neighbour, or holes appear when it rotates.
- Long clothing is a decision. Keep a robe on the torso and let legs swing inside it, or split it into its own part. Tell the user which you chose.

Add parts only for motion the user will notice. Six parts plus a weapon socket is a good default. Elbows and knees cost animation time on every clip.

For more freedom, go modular: separate hands and feet with a small gap so they float, add hips so upper and lower body counter-rotate, and split skirts and shoulder pads for spring motion. Drive those with damped springs in the engine instead of keys, and offset keys so hips lead, then chest, arms, weapon.

## 2. Write the rig config

Create `rig.json` beside the character, using `references/rig-config.md`. Use the humanoid hierarchy in that reference unless the character has a different body.

## 3. Build and export

```bash
"BLENDER" -b character.blend --python "$HOME/.claude/skills/rigid-part-rigging/scripts/rig_rigid.py" -- --config rig.json --out export/rigged.glb --save rigged.blend
```

`BLENDER` is the full path to the Blender executable. Rebuilding always starts from the unrigged `.blend`, so edit `rig.json` and rerun instead of patching the rigged file.

## 4. Animate

Read `references/motion.md` before writing keys. Snappy rigid motion needs different timing from realistic animation.

## 5. Use in the engine

- Play clips with the engine's animation mixer, crossfading about 0.1 s between loops. Play attacks once.
- Attach a weapon as a child of the socket bone. Socket orientation can differ after export, so cancel the bone's rest rotation with an in-between node rather than guessing an offset.
- Drive gameplay from clip timing: record the frame the hit lands, and run hit checks and VFX at that time.
- Remove any older pose code, or it will fight the mixer.
- For two-handed weapons, keyframe the weapon, not the arms. Put a Swing bone at the chest and a Weapon bone under it, split arms at the elbow, and solve two-bone IK to grip points on the weapon each frame after the mixer runs. Hands then stay on the shaft through any swing. Keep poses within arm reach.
- Lean the whole body into movement and turns. A rigid character reads as fluid through big whole-body tilts, not through limb detail.
- Smoothness is mostly outside the clips: ease velocity toward its target, damp turning along the shortest angle, let the camera trail the player, crossfade loops, and scale walk playback by actual speed.
- Procedural offsets on bones without keys must start from the stored rest rotation every frame. The mixer only resets keyed bones, so anything else accumulates and slowly spins. Test by walking, stopping, and comparing with rest.
- A flat weapon seen edge-on can vanish behind the body when the character faces sideways. Check all four facing directions.

- For combos, make one clip per hit, with a hit window and a total frame count. Queue input during a swing and start the next clip once the cut ends. A free hand can stay animated at rest and blend onto the grip while attacking.
- Browsers cache GLBs. Add a changing query to the model URL, or tests will measure the old rig.

## 6. Verify

Look at the result. A clean export proves nothing about the motion.

- Import the GLB and confirm bones, clip names, and clip lengths.
- Capture key poses in the real game or a render: contact, passing, windup, impact, recovery.
- Inspect poses up close as well as from the game camera: terraced surfaces and stray voxels hide at distance.
- Check that looping clips match on the first and last frame, that no part flies off (wrong origin), and that limbs swing the intended way. Left and right mix-ups are common.
- Say what was checked by eye and what still needs the user to play it.

## Limits to state

Rigid parts will not fold cloth, flex fingers, or change facial expression. A single-piece arm cannot bend at the elbow. Offer an extra part when the user wants that.

When the user names a game as a reference, take the general style only. Do not copy its models, clips, or designs.
