# Asset requests and intake checks

Copy the relevant template into the report and fill every bracket from the analysis. Prompts stay in English. Use original descriptions: no franchise, character, or artist names. Tool names below are examples; if the user already has a favorite, use it.

Default save location: `assets/from-user/<name>` in the working project.

## Request card

Each request needs all of these, so the user can act without asking anything back:

```markdown
### ขอ #N — <ชื่อ> (จำเป็น/เสริม)
- **เหตุผล:** <ทำไมผมทำเองไม่ได้ หรือทำไมของคุณจะดีกว่า>
- **เครื่องมือ:** <ประเภทเครื่องมือ พร้อมตัวอย่าง>
- **Prompt:** <บล็อกโค้ดพร้อมคัดลอก>
- **สเปก:** <ความละเอียด, ฟอร์แมต, จำนวน, พื้นหลัง>
- **บันทึกที่:** <พาธ>
- **ถ้าไม่มี:** <ทางเลือกสำรอง และคุณภาพที่จะลดลง>
- **ได้แล้วผมทำต่อ:** <ขั้นตอนถัดไปของผม>
```

## Concept or style image

Tool type: image generator (Midjourney, Flux, GPT Image, Gemini, or similar).
Spec: 2048 px or larger on the long side, PNG, generate 4 and send the best 1 or 2.

```text
[subject], [art style in plain words], [camera angle and lens feel], [lighting],
color palette of [hex values from accent_palette], [mood], clean silhouette,
no text, no logo, no watermark
```

## Image for image-to-3D

This one image decides the mesh, so it is worth the extra care. Ask for it before generating a model.

Spec: one subject, whole object in frame, plain light gray or white background, even soft light, no cast shadows, 3/4 view or front view, 1024 px or larger, PNG.

```text
[subject] as a single standalone 3D asset, full object visible, centered,
[front or three-quarter] view, plain light gray background, soft even studio lighting,
no shadows, no props, no text, clean readable shapes, [style] style, [palette]
```

For characters, use a neutral A-pose or T-pose, arms away from the body, fingers separated, mouth closed, and ask for front, side, and back views in the same style if the tool accepts multiple views:

```text
character turnaround sheet of [character], front view, side view, back view, same proportions
in all views, neutral A-pose, full body, plain light gray background, flat even lighting,
orthographic look, no text, [style] style
```

## AI 3D model

Tool type: image-to-3D (Meshy, Tripo, Hunyuan3D, Rodin, or similar).
Spec: `.glb` with textures embedded, or `.fbx` with a texture folder. Choose PBR textures when offered. Target by use:

| Use | Triangles | Texture |
|---|---|---|
| Web | up to 50k | 1K to 2K |
| Game prop | 5k to 30k | 1K to 2K |
| Game character | 20k to 60k | 2K |
| Render only | highest offered | highest offered |

Tell the user Claude will do cleanup afterward, so a slightly rough mesh is fine; a wrong shape is not. Say to check the back of the model before sending.

## Rigging and motion

- **Humanoid auto-rig and motion library**: Mixamo or similar. Spec: FBX with skin, 30 fps. State the exact motions needed, such as "idle, run, heavy attack".
- **Performance from video**: AI mocap tools (Rokoko Vision, DeepMotion, or similar), or a phone clip of the user acting it out: full body in frame, fixed camera, plain clothes, good light. Spec: FBX or BVH.
- A reference clip alone is also useful: Claude can match its timing frame by frame.

## Textures, HDRIs, and references

- **Seamless texture**: image generator or a free library such as Poly Haven or ambientCG. Spec: 2K or larger, tileable, and PBR maps when possible. Check the license.
- **HDRI**: Poly Haven, 2K to 4K `.hdr` or `.exr`, for realistic reflections.
- **Better video**: if footage is the limit, ask for a higher resolution source, or a slowed-down capture of the key moment. Spec: original file, not a screen recording of a player.

## Sound

Tool type: sound library or an audio generator. Spec: WAV, 48 kHz, one file per cue, named by timestamp. Give the cue list from `audio_hits_matching_visual_events_sec` and what happens at each cue.

## Intake checks

Inspect each asset before building on it, and report the results.

**Images**: right size and format, the subject is complete and not cropped, background is clean, no stray text or watermark, style and palette match. Warped details, such as extra fingers, get flagged here rather than found later in 3D.

**3D models**, in Blender:
1. Import, then record triangle count, dimensions, object and material count, and whether textures loaded.
2. Fix scale and orientation; put the origin at the base or feet, and apply transforms.
3. Check for inverted normals, loose parts, non-manifold edges, and holes.
4. Render front, side, back, and three-quarter views, and look at them. AI meshes are usually weakest at the back and in thin parts.
5. Simplify if over budget. Retopology of AI meshes for clean deformation is limited, so say so before promising rigging.
6. Check texture resolution and baked-in lighting, which will fight the scene's own lights.

**Motion**: frame rate, bone naming, root motion, foot sliding, scale, and whether it retargets onto the intended rig.

**Audio**: format, sample rate, clipping, length, and license.

Fix what can be fixed. Only ask for a regeneration when the problem is in the source, and say exactly what to change in the prompt.
