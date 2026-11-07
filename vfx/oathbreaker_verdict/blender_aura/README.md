# Oathbreaker Verdict — Ultimate Aura VFX (ECLIPSE ONLINE / OATHBREAKER)

A procedural, modular Blender 5.2 / Eevee VFX asset. It contains only VFX: no character, floor, lights or world.

## Rebuild / render
```
blender -b --factory-startup --python build_oathbreaker_verdict.py -- --save --all   # .blend + 72 PNGs
blender -b --factory-startup --python build_oathbreaker_verdict.py -- --frames 20,44 # spot-check frames
python package_and_validate.py                                                        # checks + atlas + previews
```
The build is deterministic (fixed seeds, keyed animation, no caches), so every rebuild gives the same frames.

## Spec
- 72 frames @ 24 fps (3.0 s), 1024², straight-alpha RGBA PNG. Frames 1 and 72 are fully transparent.
- Orthographic iso camera (X 60°, Z 45°, ortho scale 10.6, 96.6 px/m).
- Origin = character feet → pixel (512, 583.1). Core = chest height 1.1 m → pixel (512, 491.1).
- Phases (frames): appear 1–12 · charge 12–26 · release 26–40 · impact 40–51 (peak about 43–44) · follow-through 51–61 · fade 61–72.

## Scene layout (`VFX_OathbreakerVerdict`)
Everything is parented to `VFX_OathbreakerVerdict_Root`. Move that one object to reposition the effect.

| Collection | Contents |
|---|---|
| VFX_Core | Faceted displaced shell (Voronoi displace, animated), dark inner core, soft halo |
| VFX_Ribbons | 6 curve ribbons (diamond bevel profile + taper), grow/contract via `bevel_factor_*` |
| VFX_Chains | 4 tilted orbiting chains of individual links and glowing break ends. Chains 0–2 shatter at release; chain 3 orbits until it fades |
| VFX_Symbols | Fractured ground sigil plus 5 camera-facing floating sigils, built from separate pieces that drift apart and dissolve |
| VFX_Shockwaves | 2 ground shockwave rings, 1 camera-facing flash ring, 1 burst shell |
| VFX_Spikes | 22 jagged crystal spikes |
| VFX_Particles | `VFX_ShardCloud` Geometry Nodes clouds: gathering fragments, orbiting fragments, 2 debris bursts, per-sigil dissolve motes |

## Controls
- **Shader controls (per object):** every VFX material reads the object custom properties `vfx_alpha`, `vfx_emit` and `vfx_dissolve` (noise dissolve). Keyframe these to retime any element.
- **Shared materials:** the `M_*` materials share one node layout. It uses animated 4D noise, a palette color ramp and a Transparent/Emission mix, with Blended render mode.
- **GN clouds:** each cloud is set through its modifier inputs (Count, Radius, Thickness, Flatten, Lift, Shard Size, Seed). Radius and Shard Size are keyframed.
- **Palette:** limited to near-black purple, dark violet, corrupted purple, deep crimson and crimson, plus crimson/violet accents. The validation step checks that no saturated hue falls outside the 255°–15° range.

## Notes
- The game engine is expected to add bloom. The renders contain no compositor glare, because glare does not survive in straight alpha.
- The effect has no lights and no shadow-casting geometry, and every object has `visible_shadow` turned off.
