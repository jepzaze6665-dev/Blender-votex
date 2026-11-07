---
name: voxel-wings
description: Sculpt and upgrade voxel wings in Blender for a block or voxel character, then fit them to the character and run them in a Three.js test page. Covers layered feathers, colour ramps, round and tapered shapes, fold and spread poses, upgrade tiers, flowing sparkles, and a core-to-tip light pulse. Use this whenever the user wants wings, a back accessory, angel or crystal wings, wing tiers, wing VFX, or says "ทำปีก", "ปีกคริสตัล", "ปีกนางฟ้า", "ยกระดับปีก", "เอฟเฟกต์ปีก", "กางปีก", or "พับปีก", even if they do not name this skill.
---

# Voxel Wings

Build wings as real 3D voxels in Blender. Effects in the page only accent them. A concept image is a reference, not an exact target.

## Reference first

Follow the locked style in `voxel-style`, and end every image prompt with its shared prompt ending.

Before sculpting anything new, such as a character, monster, boss, weapon, wings, map piece, or effect, ask the user for reference images and give ready-to-paste prompts. The user generates them, which cuts down on guessing. Wait for the images unless the user says to go ahead without them. Crop and study them before building. They guide the design and need not be matched exactly.

## Start

1. If the user asks for a plan, give labelled options and wait for a choice.
2. Copy `scripts/build_wings.py` into a `voxel-wings/` project folder. Change the palette, feather layers, and attachment point for the new design.
3. Build, then read the preview image before opening the game.

```bash
blender -b --factory-startup --python build_wings.py
WING_SLIM=1 blender -b --factory-startup --python build_wings.py
```

The first command makes the round wings. The second makes the tapered wings as separate `*_slim` files. Keep both when the user likes both.

## Sculpt

- Use three overlapping layers: long `Primary`, mid `Secondary`, and short `Covert` feathers. Thin, separated feathers read as spikes.
- Set each layer's feather count, angle sweep, length, and width in the `layer(...)` calls.
- Round shape: a wide fan with long feathers in the middle. Tapered shape: long upper feathers, a narrower fan, and a short lower edge, which also shows more of the body.
- Colour runs dark blue at the root, bright blue through the feather, and white only at the tip and edge. Too much white flattens the wing under bloom.
- Keep object names stable. The page uses them for tiers, and `Tip[RL]n` empties for sparkles.
- `FoldR` and `FoldL` have no keys, so the page can fold the wings over the flap animation.

## Fit and run

Follow `assets/wings-web.js`, the working code from the test page.

- Build in the character's model space, facing +Y, with wings behind it. Attach to the body bone using the inverse rest matrix, measured before clips start.
- Merge the SCENE-mode GLB's tracks into one clip, or only the first object animates.
- Start with `WING_SCALE = 0.62` for the modular hero, about a 3.3 m span, and refit by eye for other bodies.
- `WING_IDLE_FOLD` sets the standing pose: 1 is folded, 0 is open. The approved value is 0.6, a visible V from behind. Moving, jumping, and attacking open the wings.
- A `?wing=slim` query switches the model, so two shapes can be compared on the same page.

## Tiers

| Tier | Visible | Effect |
|---|---|---|
| 1 | Frame, Primary | None |
| 2 | Secondary, Core, Gem | Light pulse, 0.45 |
| 3 | Covert, Shard | Sparkles, pulse 0.8 |
| 4 | All layers | Dense sparkles, pulse 1.25 |

Sparkles run only when the wings are more than half open, so they stop at the 0.6 idle pose. Offer an idle sparkle if the user wants one.

## Check

- Review in the wide third-person view from behind, since that is the angle players see. Front and side shots do not replace it.
- Check idle, moving, every tier, and attack frames for clipping through the body or weapon.
- Measure the fold and pulse values through the page's debug object, and read the console for errors.
- Report triangles and file size. The round wings are 53,724 triangles and the tapered wings 47,100, which is heavy for many characters at once.
- Record each shape in the asset library with `voxel-asset-library`, then validate.
