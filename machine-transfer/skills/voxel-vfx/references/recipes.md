# Voxel VFX recipes

Working examples are in `assets/reference-skills.js`, taken from the frost scythe test page.

## Concept prompt

```text
original voxel art VFX concept sheet for [theme] character, top-down three-quarter game view,
three large separate skill effects in one row, every effect built from visible chunky glowing cubes,
1. [fast skill shape], 2. [area skill shape], 3. [ultimate shape],
bold anime action silhouettes, clear stepped edges, visible cube faces, high contrast,
palette of [hex values], plain solid black background,
no character, no text, no labels, no logo, no watermark
```

## Frost Crescent: fast projectile

Clean blade: 268 cubes follow the arc and turn with it, in two main sizes. The band tapers to sharp tips. Colour runs in order from the bright inner edge to a deep rim, and chips stream straight back. Launch it at the swing, not on the key press. Random grids and mixed block sizes looked rough.

## Blizzard Vortex: area

Approved. Twelve rings form a funnel, with two winding bands, a thin core, three broken wind rings, two turning spirals, and ground chunks. Each ring is one object, with 20 animation tracks in total. Lifetime 2.8 s. Pull enemies inward on a repeating tick.

## Winter Eclipse: ultimate

Timeline: darken, moon falls, impact at frame 34, then plates, spikes, block wave, and chips. It clears by frame 65. Moon plates are merged pieces with dark cracks. 2D is limited to star, shock, and crack at impact.

## Open issues

- Moon can leave the frame early with a low or close camera.
- Crater wall reads as a ring on bright ground, and may hide the player.
- Cast poses work, but need checking from a clear camera: plant and slam contact, movement during casts, and damage taken while casting.
