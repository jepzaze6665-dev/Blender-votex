---
name: voxel-style
description: The locked art style for the user's voxel game, covering look, voxel size, colour, glow, shapes, proportions, motion, area colour themes, and the shared prompt ending for reference images. Use this before sculpting or writing an image prompt for any character, monster, boss, weapon, wings, map, or effect, and whenever the user asks about art direction, a new area theme, or whether something fits, or says "ล็อคสไตล์", "สไตล์เกม", "คุมสไตล์", or "ธีมพื้นที่", even if they do not name this skill.
---

# Voxel Style

The game has many areas, such as a starter town and a desert. Ice is only the first one built. The core is locked so every area feels like one game, while colour, materials, and mood change by area. See `assets/style-sheet.png` for approved work, and treat its blue as that area's colour, not the game's. If a request breaks a locked rule, say so and ask, because the user may want an exception.

## Locked core

- **Look:** Stylized Voxel Magic. Cubes stay visible, 3D tells the story, and 2D only accents a beat.
- **Voxel size:** larger bodies use larger cubes. Hero 5 cm, wings 6 cm, boss body 20 cm with a 10 cm head. The face or focal point may use a finer grid than its body.
- **Colour structure:** every theme uses a dark base, a saturated mid, a bright accent, and a near-white used only on tips and edges.
- **Glow:** only focal points glow, such as eyes, cores, magic, and lamps. Everything else stays unlit.
- **Shape:** chunky forms that read from far away, with a few finer accents. Check the silhouette in the game camera.
- **Scale:** the hero is the unit. Small monsters are 1 to 2 times its height and bosses about 5 times.
- **Motion:** rigid parts never bend. Attacks have a wind-up, a fast strike, and a recovery. Long parts move in a trailing wave.
- **Originality:** no copied assets, names, or designs.
- **Review:** judge in the game camera, not only from preview renders.

## Area themes

Each area sets its four colours, accent material, and mood. Proposed rows are starting points: confirm them with the user, then mark them approved.

| Area | Status | Dark base | Saturated mid | Bright accent | Near-white | Accent material | Mood |
|---|---|---|---|---|---|---|---|
| Ice | Approved | Navy | Royal blue | Ice blue | Frost white | Crystal | Cold, magical |
| Starter town | Proposed | Dark brown | Warm wood | Grass green, roof red | Cream | Wood, stone, lanterns | Warm, safe |
| Desert | Proposed | Deep umber | Sand orange | Turquoise | Pale sand | Sandstone, gold, turquoise | Hot, ancient |

## Prompt ending

Add this to the end of every reference image prompt. Fill the brackets from the area's row. Attach an approved image when one exists for that subject.

```text
Built entirely from visible cube voxels, like a high quality blocky 3D game model. Chunky readable silhouette with a few finer accents. Palette: [dark base], [saturated mid], [bright accent], with [near-white] only on highlights and edges. Accent material: [material]. Mood: [mood]. Glow only on focal points. Stylized game art, clean separated parts, no text, no logo.
```

For sheets, add the view instructions before this ending.
