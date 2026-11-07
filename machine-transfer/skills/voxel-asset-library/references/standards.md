# Library standards

## IDs

Lowercase words joined by underscores, ending in a two-digit variant:

`<type>_<group>_<name>_<nn>`

| Type | Example |
|---|---|
| character | `character_hero_frost_reaper_01` |
| weapon | `weapon_scythe_frost_01` |
| vfx | `vfx_weapon_slash_frost_01` |
| prop | `prop_camp_lantern_01` |

## Character manifest

```json
{
  "id": "character_hero_frost_reaper_01",
  "type": "character",
  "rig": "biped_hero",
  "model": "../../web-prototype/assets/voxel_character_rigged.glb",
  "source": "original, from the user's generated turnaround",
  "equips": ["weapon_scythe_frost_01"],
  "vfx": []
}
```

## Weapon manifest

```json
{
  "id": "weapon_scythe_frost_01",
  "type": "weapon",
  "class": "polearm",
  "model": "../../web-prototype/assets/voxel_weapon.glb",
  "source": "original, from the user's generated concept",
  "sockets": {"Grip_R": [0, 0, 0], "Grip_L": [0, -0.45, 0], "Tip": [-0.72, 0.33, 0]},
  "vfx": ["vfx_weapon_slash_frost_01"]
}
```

## VFX manifest

```json
{
  "id": "vfx_weapon_slash_frost_01",
  "type": "vfx",
  "kind": "trail",
  "attach": "Tip",
  "params": {"colour": "#67b9e9", "life": 0.16},
  "source": "original procedural effect"
}
```

`model` is optional for VFX, since many are procedural. `attach` must be a socket defined by a weapon or rig that uses the effect.

`equips` and `vfx` are references to other IDs. The report counts these references to show usage.
