---
name: voxel-game-pipeline
description: Turn generated concept images into voxel game assets and a playable web game. Covers weapon images to voxel models, front/side/back character sheets to modular voxel characters, Blender builds, GLB export and checks, rigid rigging, two-handed weapon IK, spring cloth, slash VFX, and a Three.js action prototype. Use this whenever the user wants to make a voxel weapon, voxel character, voxel enemy or prop from an image, asks for image prompts to use as a model reference, wants to put voxel assets into a web game, or says "ทำโมเดล voxel", "แปลงรูปเป็น voxel", "ปั้นตัวละคร voxel", "ขอ prompt ทำต้นแบบ", or "ทำเกมเว็บ", even if they do not name this skill.
---

# Voxel Game Pipeline

Build this way: the user generates a flat concept image, Claude converts it with scripts, builds in Blender, then proves it in a playable web game. Scripts stay the source of truth, so changes mean editing and rerunning, not patching a `.blend`.

Write to the user in their language. They are new to Blender and game engines, so explain terms briefly. When they ask for a plan, stop and give one before building. Keep generation prompts in English.

## Reference first

Follow the locked style in `voxel-style`, and end every image prompt with its shared prompt ending.

Before sculpting anything new, such as a character, monster, boss, weapon, wings, map piece, or effect, ask the user for reference images and give ready-to-paste prompts. The user generates them, which cuts down on guessing. Wait for the images unless the user says to go ahead without them. Crop and study them before building. They guide the design and need not be matched exactly.

## Choose the route

| Asset | Reference image | Script |
|---|---|---|
| Weapon or prop | One flat view, plain white background | `scripts/weapon/voxelize.py`, `build_weapon.py`, `validate_glb.py` |
| Character | Front, side, back on one sheet, A-pose, empty hands, plain white background | `scripts/character/voxelize_character.py`, `build_character.py`, `validate_character.py` |
| Motion | Pose sheet or clip, optional | The `rigid-part-rigging` skill and `scripts/character/rig.example.json` |
| Web game | None | `assets/web-game/index.html` |

Do not suggest an AI 3D generator for voxel work. Building from a grid gives crisper edges and easy edits.

Copy scripts into the project first, then adapt them there. The bundled scripts are a working reference built for one scythe and one hooded character, so their landmarks are not universal: weapon detection expects a diagonal shaft, and body landmarks are shares of height. Check each one against the preview, and tell the user which you changed.

## Weapon steps

1. Request a pixel-art weapon image: flat side view, whole weapon visible, solid white background, limited palette, no text.
2. Run `voxelize.py`, then read `voxel_preview.png`. Raise `--height` if gaps or gems fuse together.
3. Run `build_weapon.py -- --save --glb --stills 1,37,73,109`. Add `--anim` for the loop.
4. Run `validate_glb.py`, then compare the renders with the concept.

## Character steps

1. Request a turnaround sheet with same proportions in all views, about 4 heads tall, arms away from the body, and no weapon.
2. Run `voxelize_character.py`. Its preview shows the colour and part map side by side.
3. Check the landmark shares in `is_arm` and the part rules against the preview.
4. Run `build_character.py`, then `validate_character.py`.
5. Rig with `rigid-part-rigging`, starting from `rig.example.json`.

Shape comes from intersecting the front and side silhouettes, rounding each row, and smoothing depth. Default split is 19 modular parts: chest, hips, head, upper arms, forearms, floating hands, legs, floating feet, four skirt panels, and two shoulder pads.

## Modular characters

This is the preferred route for a new hero. `scripts/modular/build_modular.py` sculpts each part with its own shape function on a shared 5 cm grid, then builds exposed faces only. It gave cleaner forms and far fewer triangles than cutting a sheet: 12 parts and 8,524 triangles, against 22,872. Use a concept image as a reference, not as the source of the geometry.

- Split hood, face, eyes, body, cape, pads, hands, feet, and crystal, so eyes and crystals can glow or swap alone.
- Keep the established pivots and bone names, so existing clips carry over. New parts become child bones.
- Keep hands and feet floating unless the user chooses limbs.
- Check the back first: third-person cameras see it most. Next upgrades, if asked: a tapered hood back, a layered cape, a smaller head with broader shoulders, then larger trim details.

## Block characters

For a Trove-like chunky feel, use the block route: `scripts/block/voxelize_block.py`, `build_block.py`, and `rig.example.json`. Ask for a turnaround with no arms or legs, floating block hands and feet, and clear white gaps. It splits body, head, cape, two pads, two hands, and two feet, and keeps surfaces boxy. Hands sit on weapon grips directly, so no IK is needed. `mockup_topdown.py` and `mockup_ui.py` make a still mockup.

## Maps

`scripts/map/build_map.py` builds a floating island map in Blender and exports a GLB plus walk data. `assets/web-game/ice_map.js` loads both and adds the sky, shadows, snow, and motion that a GLB cannot carry. Check that every island is reachable, keep bridge entrances clear, and walk the route in the page.

## Review in top-down

This user reviews finished work in top-down, so end each change there and give the link. The template now opens in wide third person for map work; use `?view=top` for top-down and `?view=follow` for the old close camera. Click the ground to walk, click an enemy to attack, and press Space to slash or chain the three-hit combo. Judge readability from that camera: big silhouettes, a ring under the character, and a large blade. Reference pose sheets guide the feel only, so do not chase an exact match.

For a large weapon, scale the holder rather than the GLB, and raise hit reach to match. The current scythe uses 1.25x and reach 3.2.

## Web game

Copy `assets/web-game/index.html` beside an `assets/` folder holding `voxel_weapon.glb` and `voxel_character_rigged.glb`. Serve it over HTTP, because opening the file directly cannot load GLBs. Add a query such as `?v=2` after edits, since the browser may keep the old page.

The template includes movement easing, clips with crossfades, two-hand IK, springs, slash trail, hit-stop, waves, combo score, and game over. Its `__demo` object and `snap()` help with testing. `update()` can be stepped by hand to capture close-up frames. Do not clear `enemies` inside a test loop: the game spawns a new wave each time, and the page hangs.

## Check before reporting

- Inspect renders and in-game poses at close range as well as from the game camera.
- Measure actual part rotations when testing motion, not just internal spring values.
- Walk, stop, turn, and slash. Compare parts with rest after stopping.
- Say what was seen, what was only measured, and what the user still needs to play.

## Keep it original

When the user shares a commercial game as a reference, learn the technique and timing. Do not copy its characters, designs, or animation.

Keep large scope honest: this pipeline gives assets and a prototype, not a finished online game.
