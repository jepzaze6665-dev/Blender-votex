# rig.json format

```json
{
  "fps": 24,
  "remove": ["Hand_R", "Character"],
  "bones": [
    {"name": "Root", "head": [0, 0, 0]},
    {"name": "Torso", "parent": "Root", "from": "Torso", "mesh": "Torso"},
    {"name": "Head", "parent": "Torso", "from": "Head", "mesh": "Head"},
    {"name": "ArmR", "parent": "Torso", "from": "ArmR", "mesh": "ArmR"},
    {"name": "ArmL", "parent": "Torso", "from": "ArmL", "mesh": "ArmL"},
    {"name": "LegR", "parent": "Root", "from": "LegR", "mesh": "LegR"},
    {"name": "LegL", "parent": "Root", "from": "LegL", "mesh": "LegL"},
    {"name": "Hand_R", "parent": "ArmR", "from": "Hand_R", "order": "ZYX"}
  ],
  "clips": [
    {"name": "Idle", "tracks": {"Torso": [{"f": 1}, {"f": 25, "z": -0.02}, {"f": 49}]}}
  ]
}
```

- `from`: an existing object whose position becomes the joint. `head`: explicit XYZ instead.
- `mesh`: the object that follows this bone. Omit it for sockets and root bones.
- `order`: Euler order. Default `XYZ` pitches first, then yaws: right for limbs. Use `ZYX` when spinning around an axis before tilting, as for a weapon socket.
- `remove`: helper objects to delete after their positions are read.

## Keys

Each key has `f` (frame) and any of:

- `rx`, `ry`, `rz`: rotation in degrees.
- `x`, `y`, `z`: offset from rest in metres.

Missing values mean 0, so a key sets the full pose of that bone. Give every animated bone a key on the first and last frame.

All bones point along +Y with no roll, so axes match the model, with the character facing +Y:

| Value | Effect on a hanging limb or the body |
|---|---|
| `rx` positive | A hanging limb swings forward, but an upright body or root leans BACK. Use negative `rx` to lean forward |
| `rz` positive | Turns toward the character's left |
| `ry` positive | Tilts toward the character's right |
