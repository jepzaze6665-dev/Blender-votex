---
name: voxel-boss
description: Build a large voxel boss from concept images, with a part-by-part Blender sculpt, a many-jointed rigid rig, attack clips, a boss intro cutscene, and Blender-made attack effects, tested in a Three.js page. Use this whenever the user wants a boss, a giant monster, a dragon, a boss intro or awakening scene, boss attacks, or boss attack effects for a voxel game, or says "ทำบอส", "มังกร", "ฉากเปิดตัวบอส", "อนิเมชันบอส", "ท่าโจมตีบอส", or "เอฟเฟกต์บอส", even if they do not name this skill. Not for small enemies with one simple rig.
---

# Voxel Boss

Work in stages and let the user approve each one: concept images, model, rig and clips, attacks, intro, attack effects. Write to the user in their language, offer labelled options with one recommendation, and report what still falls short.

The folder this was built in is for graphics. Combat, AI, collision, and damage belong to the user's game project, so the test page only mocks them.

Working example: an ice dragon. Copy from `scripts/` and `assets/`, then change the shapes.

| File | Purpose |
|---|---|
| `scripts/build_dragon.py` | Sculpt 32 parts, with origins on joints |
| `scripts/gen_rig.py` | Write `rig.json`: bones and clips, generated in code |
| `scripts/build_dragon_ice.py` | Intro prop that breaks, plus arena pillars |
| `scripts/build_dragon_vfx.py` | Attack effects as animated GLBs |
| `assets/boss_intro.js` | Cutscene: camera, timing, dimming, effects |
| `assets/dragon.html` | Clip and effect test page, one button per clip |

```bash
blender -b --factory-startup --python build_dragon.py
python gen_rig.py
blender -b voxel_dragon.blend --python <rigid-part-rigging>/scripts/rig_rigid.py -- --config rig.json --out export/voxel_dragon_rigged.glb --save voxel_dragon_rigged.blend
blender -b --factory-startup --python build_dragon_ice.py
blender -b --factory-startup --python build_dragon_vfx.py
```

Rebuild the model before re-rigging, because rigging saves into a separate file from a clean sculpt.

## Reference first

Follow the locked style in `voxel-style`, and end every image prompt with its shared prompt ending.

Before sculpting anything new, such as a character, monster, boss, weapon, wings, map piece, or effect, ask the user for reference images and give ready-to-paste prompts. The user generates them, which cuts down on guessing. Wait for the images unless the user says to go ahead without them. Crop and study them before building. They guide the design and need not be matched exactly.

## Concept images

Ask for a hero image, a turnaround with front, side, back, and top, and an image of the key moment. Tell the user to attach the first image when making the others, so all show one creature. Effect sheets are worth requesting too: they changed the dragon's effects far more than tuning did.

## Read the reference first

Crop the face and key details from each image and enlarge them before sculpting. The dragon's first faces failed because the sculpt followed a guess: the mouth was open with long fangs, while every reference showed a closed mouth with a short jagged white band. Compare in a sheet with the reference above the model, from the same angle.

## Sculpt

- Build tubes from spheres along a path, and spikes as tapered cones. Loft the head through side-profile stations of width, top, and bottom.
- Use a coarse grid for the body and a finer one for the head. The face is what people look at.
- Keep skin to one main tone with a few darker blocks. Two-tone noise reads as a checkerboard.
- Keep crystals slim. Thick ones look like blobs.
- Hide Blender sun shadows in previews. Cube shadows draw noisy triangles that are not in the model.
- A size target is a choice, not a rule. Ask which platform the game targets. For PC, the dragon at about 90,000 triangles was accepted. Merging coplanar faces is the first way to reduce it.

## Rig and clips

Generate clips from small helpers (`wave`, `poses`, `neck`, `wings`, `tail`) rather than hand-writing JSON. Bones use model axes: +rx lifts things pointing +Y and swings legs forward, +rz yaws left, -ry raises the right wing, and rz sweeps wings forward and back.

- Put the Root at the hind feet, so rearing up pivots there, and counter-rotate the hind legs.
- Offset each neck, tail, and wing joint in phase, so motion travels along the body.
- Wings need both raise and sweep. Only flapping up and down looked stiff to the user.
- Give each attack a wind-up, a fast strike, a hold, and a recovery.
- The boss model faces -Z in Three.js. Aim test cameras at its front.

## Intro cutscene

The approved shape is about 7 seconds: quiet approach, rising tension, burst, roar, name, then hand the camera back.

- Trigger once when the player comes close, freeze the player, hide small enemies, and restore them at the end. Keep a replay key.
- Dim toward the burst, then return brighter. Scene lights alone barely change an emissive map, so a multiply overlay does the work. Too dark hides glowing details.
- Keep the eyes dark, then light them at the darkest moment with a cut to the face. This was the strongest beat.
- Slow time for about 0.4 seconds at the burst.
- Reveal cracks outward from the core with a shader distance test.
- Bloom turns bright translucent crystal white, so keep emission low on large props.
- Do not stand arena pillars between the camera and the boss. Put them behind it as a backdrop.

## Attack effects

Follow `voxel-vfx`. Each effect's first frame is the attack's impact, and the page starts it on that clip time. Effects follow one of four anchors: mouth, foot, root, or the mouth every frame for breath. Tall effects grow by scale from a base origin, so they do not poke through floating islands.

The effects cost a lot of triangles, because each crystal is its own object. Reduce the wave and frozen ground first if a scene stutters.

## Check

- Step the cutscene by calling `boss.update` and capture key moments, because a hidden browser pane runs at about one frame per second. Say so, and ask the user to judge timing in real play.
- Test the trigger, the end state, enemies restored, and console errors.
- Capture each attack from a side that shows it. Tail effects need a view from behind.
