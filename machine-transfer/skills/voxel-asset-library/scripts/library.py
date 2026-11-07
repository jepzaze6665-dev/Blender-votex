#!/usr/bin/env python3
"""Validate a voxel asset library and report how its assets are used.

  python library.py validate LIBRARY_DIR
  python library.py report LIBRARY_DIR

validate exits 1 when it finds an error. report writes report/usage.md and manifests.json.
"""
import json
import re
import struct
import sys
from pathlib import Path

PROFILES = json.loads((Path(__file__).parent.parent / "references" / "rig-profiles.json").read_text(encoding="utf-8"))
ID = re.compile(r"^(character|weapon|vfx|prop)(_[a-z0-9]+)+_\d{2}$")


def read_glb(path):
    with open(path, "rb") as f:
        magic, _, _ = struct.unpack("<III", f.read(12))
        if magic != 0x46546C67:
            raise ValueError("not a GLB file")
        size, _ = struct.unpack("<II", f.read(8))
        doc = json.loads(f.read(size))
    triangles = 0
    for mesh in doc.get("meshes", []):
        for prim in mesh["primitives"]:
            key = prim.get("indices", prim["attributes"]["POSITION"])
            triangles += doc["accessors"][key]["count"] // 3
    return {"nodes": {n.get("name") for n in doc.get("nodes", [])},
            "clips": {a.get("name") for a in doc.get("animations", [])}, "triangles": triangles}


def load(library):
    assets = {}
    for path in sorted((library / "manifests").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_path"] = path
        assets[data.get("id", path.stem)] = data
    return assets


def validate(library):
    assets, errors, notes = load(library), [], []
    for key, a in assets.items():
        def err(text):
            errors.append(f"{key}: {text}")

        if not ID.match(key):
            err("ID does not follow the naming standard")
        if a["_path"].stem != key:
            err(f"file name {a['_path'].name} does not match the ID")
        if a.get("type") != key.split("_")[0]:
            err("type does not match the ID prefix")
        if not a.get("source"):
            err("source is missing")
        glb = None
        if a.get("model"):
            model = (a["_path"].parent / a["model"]).resolve()
            if not model.is_file():
                err(f"model not found: {a['model']}")
            else:
                glb = read_glb(model)
                notes.append(f"{key}: {glb['triangles']} triangles")
        elif a.get("type") != "vfx":
            err("model is missing")
        if a.get("type") == "character":
            profile = PROFILES.get(a.get("rig"))
            if not profile:
                err(f"unknown rig profile: {a.get('rig')}")
            elif glb:
                for bone in sorted(set(profile["bones"]) - glb["nodes"]):
                    err(f"missing bone {bone}")
                for clip in sorted(set(profile["clips"]) - glb["clips"]):
                    err(f"missing clip {clip}")
                if glb["triangles"] > profile["max_triangles"]:
                    err(f"{glb['triangles']} triangles is over the budget of {profile['max_triangles']}")
        for field in ("equips", "vfx"):
            for ref in a.get(field, []):
                if ref not in assets:
                    err(f"{field} points at unknown asset {ref}")
        for ref in a.get("vfx", []):
            target = assets.get(ref, {}).get("attach")
            if target and a.get("type") == "weapon" and target not in a.get("sockets", {}):
                err(f"{ref} attaches to {target}, which this weapon does not define")
    print(f"{len(assets)} assets, {len(errors)} errors")
    for line in notes + errors:
        print(" ", line)
    return 1 if errors else 0


def report(library):
    assets = load(library)
    uses = {k: [] for k in assets}
    rigs = {}
    for key, a in assets.items():
        for field in ("equips", "vfx"):
            for ref in a.get(field, []):
                uses.setdefault(ref, []).append(key)
        if a.get("rig"):
            rigs.setdefault(a["rig"], []).append(key)
    lines = ["# Asset usage", "", "| Asset | Type | Used by |", "|---|---|---|"]
    for key, a in sorted(assets.items()):
        lines.append(f"| {key} | {a.get('type')} | {', '.join(uses[key]) or '-'} |")
    lines += ["", "| Rig | Characters |", "|---|---|"]
    lines += [f"| {r} | {len(v)} |" for r, v in sorted(rigs.items())]
    unused = [k for k, a in assets.items() if a.get("type") != "character" and not uses[k]]
    lines += ["", "Unused: " + (", ".join(sorted(unused)) or "none"), ""]
    folder = library / "report"
    folder.mkdir(exist_ok=True)
    (folder / "usage.md").write_text("\n".join(lines), encoding="utf-8")
    clean = [{k: v for k, v in a.items() if k != "_path"} for a in assets.values()]
    (library / "manifests.json").write_text(json.dumps(clean, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {folder / 'usage.md'} and manifests.json")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("validate", "report"):
        sys.exit(__doc__)
    sys.exit((validate if sys.argv[1] == "validate" else report)(Path(sys.argv[2])))
