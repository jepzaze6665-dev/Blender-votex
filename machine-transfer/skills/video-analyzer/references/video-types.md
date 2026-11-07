# What to look for by video type

Use the matching section. A clip often spans several.

## Contents
- VFX and effects
- Animation (2D, anime, 3D)
- Game footage
- 3D model or product showcase
- Motion graphics and UI
- Live action, tutorials, trailers
- Screen recordings and social clips

## VFX and effects

- **Phases and timing**: anticipation, build, release, impact, follow-through, dissipation. Give frame counts. Run a burst across the impact.
- **Layers**: core, glow, trail, sparks, debris, smoke, shockwave, ground decal, distortion, screen flash, camera shake. List each separately, because each is built separately.
- **Technique tells**:
  - Stepped motion and repeating shapes: flipbook or sprite sheet.
  - Soft continuous motion with noise: shader or particles.
  - Volumes with real self-shadowing: simulation, often pre-rendered.
  - Smooth-edged ribbons: mesh trail with a scrolling texture.
  - Hard graphic shapes with held frames: hand-drawn or stylized 2D.
- **Delivery**: one-shot or loop (`loop`), on alpha or baked into a scene, bloom present or added by the engine.
- **Color**: `accent_palette`, and how color shifts over the effect's life.

## Animation (2D, anime, 3D)

- **Cadence**: `typical_hold_frames` per shot. Mixed cadence is common: camera on ones, characters on twos or threes.
- **Principles**: anticipation, smears, overshoot, arcs, squash and stretch, impact frames. Use bursts to catch them.
- **2D or 3D**: consistent volume under rotation and perfectly smooth camera moves suggest 3D, even with a toon look. Line boil, drawn shadows, and changing proportions suggest hand drawing.
- **Rig clues**: cut-out layers sliding over each other point to puppet animation.
- **Staging**: shot sizes, camera language, editing pace (`mean_shot_seconds`), and how action follows music.

## Game footage

- **Identify first**: camera (first person, third person, top-down, isometric, side view), genre, 2D or 3D, resolution of art.
- **Systems visible**: movement, combat, UI and HUD, inventory, progression, enemy behavior. What can be inferred from play, and what cannot.
- **Game feel**: hit-stop, screen shake, knockback, flash on hit, camera lag, input-to-response delay. Use bursts around hits.
- **Art pipeline**: pixel art (`pixel_block_size`), hand-painted, PBR, toon. Tile or modular reuse.
- **Scope honesty**: a minute of gameplay can hide years of content. Separate "core loop prototype" from "the full game" in the report.
- Use the `game-developer` skill for engine-level planning. Plan an original game with similar mechanics; do not rebuild the title itself.

## 3D model or product showcase

- **Form**: silhouette, topology hints (faceting, smoothness, panel lines), polygon budget, hard-surface or organic.
- **Materials**: metal, glass, subsurface, cloth. Roughness variation, whether textures are procedural or painted.
- **Presentation**: turntable or camera move, lighting setup, background, depth of field, render engine guess.
- **Views needed**: note whether the clip shows every side. Unseen sides are guesses, and matter for image-to-3D work.
- **Target use**: render only, game-ready, or web. It changes polygon and texture budgets.

## Motion graphics and UI

- **Elements**: type, shapes, masks, transitions, particles, 3D layers.
- **Timing**: easing feel, stagger, beat sync (`audio_hits_matching_visual_events_sec`).
- **Target format**: After Effects-style video, web animation in code, or Blender render. Code is usually cheapest for UI work.
- **Fonts**: name a likely font only with low confidence, and suggest an open alternative.

## Live action, tutorials, trailers

- **Tutorials**: run `--transcribe`, then turn it into steps, tools, and settings, and note which are shown on screen. Read on-screen settings from full frames.
- **Live action with effects**: separate plate from effects. Tracking, roto, and keying are the hard parts.
- **Trailers**: much of what appears may be pre-rendered cinematic, not gameplay. Say which is which when you can tell.

## Screen recordings and social clips

- Identify the true source first: app UI, username, caption, on-screen labels. Check `frames/full_frame`. A "Follow" button suggests the account is someone else's work.
- Ignore the recording's own ending, such as a swipe to the control panel.
- Quality is capped by re-encoding, so fine detail and frame cadence are unreliable. Say so, and only ask for a better file if it changes the plan.
- Comparison clips ("in Blender vs in game", "before vs after"): the difference between the halves is the lesson. Compare what survived the move and what was rebuilt.
- Speech-to-text can invent text over music, especially text repeating on-screen titles. Treat a transcript that only repeats a title as unconfirmed.
