---
name: voxel-vfx
description: Design and build Stylized Voxel Magic VFX with a 2D + 3D hybrid method, using Blender-sculpted voxel effects exported as animated GLB, short 2D accents, skill options, concept prompts, timing tables, gameplay hooks, and in-game review. Use this whenever the user wants a skill effect, ultimate, slash, shockwave, storm, ice, fire, magic, aura, or any VFX for a voxel or block character, asks to improve an effect, sends a VFX concept image, or says "ทำ VFX", "ทำสกิล", "เอฟเฟกต์", "ไม้ตาย", "ปั้นสกิล", or "ยกคุณภาพ VFX", even if they do not name this skill.
---

# Voxel VFX

The standard is **Stylized Voxel Magic: 3D voxels tell the story, and 2D only accents the beat.** Effects are built from cubes in Blender so they share one world with voxel characters and weapons. Concept images are references for shape and mood. Do not paste them into the scene unless the user asks, and do not aim for an exact match.

Write to the user in their language. They choose from options, so offer labeled choices with one recommendation, then wait. Show finished work in the wide third-person test page with a fresh query string.

## Reference first

Follow the locked style in `voxel-style`, and end every image prompt with its shared prompt ending.

Before sculpting anything new, such as a character, monster, boss, weapon, wings, map piece, or effect, ask the user for reference images and give ready-to-paste prompts. The user generates them, which cuts down on guessing. Wait for the images unless the user says to go ahead without them. Crop and study them before building. They guide the design and need not be matched exactly.

## Workflow

1. Offer 3 options per skill. Give each a role: fast, area, or ultimate. A set with all three feels complete.
2. Say whether a concept image would help. Use the prompt in `references/recipes.md`. Generated sheets should show visible cubes, not flat pixel art.
3. Build the smallest skill first, because it sets the visual standard.
4. Capture key frames in the game, including anticipation, impact, and fade.
5. Report what was seen, what still falls short, and what needs the user to play it.
6. Save lessons here when a new technique works.

## Build method

Sculpt and keyframe in Blender, then export an animated GLB. Do not use a rendered sprite for the main shape: it blurred when enlarged and looked flat under a free camera, and the user rejected it. `assets/blender/` holds the three working build scripts.

- Merge cubes into pieces and animate the pieces. Rings and plates are far lighter than one object per cube.
- Blender's SCENE export gives one animation per object. Merge every track into one clip in the player, or most cubes stay at scale zero.
- Bake with `export_force_sampling=True` for rotation. Trigger hits from clip time.
- `assets/voxel_cloud.js` and `assets/reference-skills.js` show the older code-only method, for quick experiments only.

## Hybrid layers

Build and approve the 3D with all 2D off, then add 2D one piece at a time. Keep a key that toggles 2D for comparison. Read `references/hybrid-timing.md`.

- Each moment has one star. When 3D leads, 2D backs off.
- At most two 2D layers at once, shown briefly at a start or an impact.
- If a layer does not clearly improve the shot, remove it. Stacking every layer at once looked like a mess.
- Additive 2D fades on bright ground, so test on the brightest area.

## Cast poses

Each major skill needs its own character clip, keyed with `rigid-part-rigging`. The cast is part of the effect: delay the VFX to the frame the pose triggers it, so the player sees the character cause it.

## Rules that raised quality

- Vary thickness, height, and spacing. Perfect rings look like generated shapes.
- Keep white for the core. Too much white hides the cubes, the form, and the character.
- Use low emissive on dark cubes. Glow belongs on the accents.
- Stagger cubes as they appear and crumble, so effects never pop in as one piece.
- Let the player stay visible. Check that walls and funnels do not bury the character.
- Effects under the ground plane are hidden, so make depth by raising walls around a dark floor.
- Split large objects into groups that move together, such as moon plates, rather than scattering every cube.
- Avoid names that clash with game code. This has already broken a page: check helpers such as `cubes`, `vS`, and `vP`.

## Check before reporting

- Test in the real game camera, not only a close test camera, and with 2D both on and off.
- Capture while the effect is on screen. Tall objects can leave the frame.
- Confirm a patch applied before judging its result, then check hit area, cooldown, cleanup, and console errors.
- Keep cube counts sensible and say if heavy skills may need lower counts on phones.

## Original work

When the user shares a commercial game, take only general technique and timing. Create original names, shapes, and designs.
