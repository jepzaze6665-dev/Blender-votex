---
name: voxel-asset-library
description: Organize voxel game assets into a reusable library with standard names, shared rig profiles, shared animation sets, attachment sockets, JSON manifests, validation, usage reports, and a browser preview. Use this whenever the user adds or organizes characters, weapons, skins, VFX, rigs, or animations for a voxel game, wants one rig or clip reused across models, wants to swap a skin or effect, asks for "asset library", "จัดระบบ asset", "ริกกลาง", "ใช้ท่าร่วมกัน", "เปลี่ยนสกิน", or wants to check which assets are used.
---

# Voxel Asset Library

Models change often, rigs rarely. So a character is a model plus a shared rig profile, and a weapon is a model plus named sockets. That lets one clip set serve many characters and lets VFX attach without knowing which skin is loaded.

Write to the user in their language and explain terms briefly. Build models with `voxel-game-pipeline` and rigs with `rigid-part-rigging`; this skill organizes the results.

## Library layout

```text
asset-library/
├── manifests/      one JSON file per asset
├── preview/        copied from this skill's assets/preview
└── report/         usage report output
```

Manifests point at project files by relative path, so existing work can stay where it is.

## Add an asset

1. Pick an ID using `references/standards.md`.
2. Write its manifest. Copy the closest example in that reference.
3. For a new body shape, add a profile to `references/rig-profiles.json` only if no existing one fits. Reuse is the goal: a new profile also needs its own clips.
4. Validate, then update the report:

```bash
python "$HOME/.claude/skills/voxel-asset-library/scripts/library.py" validate asset-library
python "$HOME/.claude/skills/voxel-asset-library/scripts/library.py" report asset-library
```

5. Open the preview over HTTP to check it by eye. Validation proves the structure, not the look or motion.

## Sockets

A socket is a named attachment point. Effects and weapons attach to sockets, never to raw positions. Character sockets are bones in the GLB; weapon sockets live in the manifest as local positions.

## Original content

Learning how another game organizes assets is fine. Do not put its models, rigs, clips, effects, or extracted files in the library. Record every asset's `source` truthfully in the manifest.
