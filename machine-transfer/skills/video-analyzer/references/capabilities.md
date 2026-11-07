# Capability tiers

Assign every element one tier. Judge against **the quality in the clip**, not whether something vaguely similar is possible. Before relying on a tool, confirm it is available in this session.

- 🟢 **Claude builds it**: result is close to the clip without help.
- 🟡 **Claude builds it, with limits**: useful result, but simpler or stylized. State the gap, and whether a user asset closes it.
- 🔴 **Needs the user or another tool**: Claude cannot reach usable quality alone, but can finish the job once the asset arrives.

## What Claude has to work with

- **Blender** through the MCP tools or headless `blender -b --python`: scripted scenes, Geometry Nodes, shader nodes, keyframes, EEVEE and Cycles rendering, GLB export.
- **Code**: Python image and sprite generation, GLSL, Three.js/WebGL, canvas, game engine code (use the `game-developer` skill for Unity or Unreal work), ffmpeg compositing.
- **Vision**: reads frames, renders, and sheets, so it can compare its output to the reference and iterate.
- **No generative media**: no built-in generation of images, video, audio, or 3D, and no way to judge how audio sounds. It cannot operate paid generation services for the user unless they set that up and ask.

## By domain

| Domain | 🟢 | 🟡 | 🔴 |
|---|---|---|---|
| **VFX** | Procedural auras, shockwaves, slashes, trails, particles, sigils, sprite sheets, flipbooks, alpha renders, engine-ready atlases | Fire, smoke, liquid (simulations are slow and limited by GPU memory and time); hand-drawn anime effects (close in shape, drawing feel differs) | Film-quality fluid or destruction simulation; compositing onto real footage that needs roto or tracking by hand |
| **3D models** | Hard-surface, props, architecture, abstract sculpture, stylized low-poly, modular kits, procedural materials | Stylized creatures from primitives; cleanup, decimation, UV, and material work on imported meshes | Realistic or appealing characters and faces, detailed organic sculpts, photoscans: use an image-to-3D tool or an artist |
| **Character animation** | Rigid mechanical motion, procedural loops (idle bob, hover, spin), camera moves | Simple rigs on humanoids, basic walk cycles; retargeting supplied motion | Acting, facial performance, fine combat choreography: needs mocap, a motion library, or an animator |
| **2D animation** | Motion graphics, shape and text animation, parallax, UI motion, procedural pixel-art effects | Puppet-style cut-out animation from supplied art | Frame-by-frame hand drawing; character art in a specific illustrated style |
| **Games** | Gameplay systems, shaders, UI, camera feel, hit-stop, screen shake, prototypes with placeholder art | Whole levels from procedural kits; simple enemy AI at scale | Final character art, large content sets, music, voice |
| **Web 3D** | Three.js scenes, scroll and pointer interaction, GLB pipeline, performance work | Heavy scenes on phones (needs real device testing by the user) | Nothing specific; depends on art assets |
| **Look and render** | Lighting, color grading, stylized shading, toon outlines, post effects | Photoreal scenes (limited by assets, not lighting) | Real-world textures and HDRIs at photo quality, when procedural falls short |
| **Sound** | Timing plans; syncing supplied audio with ffmpeg | Simple synthesized blips | Music, sound design, voice |

## Machine limits

Read `environment` in `analysis.json`. With about 8 GB of GPU memory, expect long or failing high-resolution Cycles simulations and heavy volumetrics, and prefer EEVEE, baked sprites, or lower resolution. Say roughly how heavy a job is before committing to it.

## Honesty checks

- Calling an element 🟢 means you could describe the build steps right now. If you cannot, it is 🟡.
- Style is the common gap: a Python-built effect can match the shape and timing of a hand-drawn one and still look procedural. Say so.
- Estimate how much of the clip is achievable by share of visible work, as a rough judgement, and label it as such.
