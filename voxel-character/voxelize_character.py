#!/usr/bin/env python3
"""Turn a front/side/back turnaround sheet into a voxel character split into parts.

  python voxelize_character.py ../assets/from-user/character-turnaround.png --height 96

Shape: the front and side silhouettes are intersected, then each row is rounded so limbs
are not slabs. Colour: projected from whichever view faces that voxel.
Writes voxels.json and voxel_preview.png next to this script.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
PARTS = ["Torso", "Head", "ArmR", "ArmL", "LegR", "LegL", "ForeR", "ForeL", "HandR", "HandL",
         "FootR", "FootL", "Hips", "SkirtF", "SkirtB", "SkirtR", "SkirtL", "PadR", "PadL"]


def split_views(img):
    arr = np.asarray(img.convert("RGB"), np.float32)
    mask = np.abs(arr - 255).sum(axis=2) > 70
    used = mask.sum(axis=0) > 0
    spans, start = [], None
    for x, flag in enumerate(list(used) + [False]):
        if flag and start is None:
            start = x
        elif not flag and start is not None:
            if x - start > 80:
                spans.append((start, x))
            start = None
    if len(spans) != 3:
        raise SystemExit(f"expected 3 views, found {spans}")
    ys = np.where(mask.any(axis=1))[0]
    return arr, mask, spans, ys.min(), ys.max() + 1


def sample(arr, mask, x0, x1, y0, y1, cell, width):
    """Downsample one view to the voxel grid. Returns solid mask and colours."""
    rows = int(round((y1 - y0) / cell))
    solid = np.zeros((rows, width), bool)
    colour = np.zeros((rows, width, 3), np.float32)
    centre = (x0 + x1) / 2
    for r in range(rows):
        for c in range(width):
            xa = int(centre + (c - width / 2) * cell)
            ya = int(y0 + r * cell)
            xb, yb = int(xa + cell) + 1, int(ya + cell) + 1
            if xa < x0 or xb > x1:   # stay inside this view, or a neighbour leaks in
                continue
            m = mask[ya:yb, xa:xb]
            if m.size and m.mean() >= 0.5:
                solid[r, c] = True
                colour[r, c] = np.median(arr[ya:yb, xa:xb][m], axis=0)
    return solid, colour


def spans_of(row):
    out, start = [], None
    for i, flag in enumerate(list(row) + [False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            out.append((start, i - 1))
            start = None
    return out


def smooth_depth(grid, rows, width):
    """Blur each column's front and back depth, so rows do not form terraces.

    Row-by-row silhouettes differ by a voxel or two, and light picks that out as stripes.
    """
    near = np.full((rows, width), np.nan)
    far = np.full((rows, width), np.nan)
    for c, y, s in grid:
        r = rows - 1 - y
        near[r, c] = s if np.isnan(near[r, c]) else min(near[r, c], s)
        far[r, c] = s if np.isnan(far[r, c]) else max(far[r, c], s)
    out = {}
    for r in range(rows):
        y = rows - 1 - r
        for c in range(width):
            if np.isnan(near[r, c]):
                continue
            a, b = max(r - 3, 0), r + 4
            d, e = max(c - 1, 0), c + 2
            lo = int(round(np.nanmean(near[a:b, d:e])))
            hi = int(round(np.nanmean(far[a:b, d:e])))
            for s in range(lo, hi + 1):
                out[(c, y, s)] = None
    return out


def keep_largest(voxels, parts):
    """Drop crumbs: a loose voxel inside a moving part flies off when it moves."""
    groups = {}
    for v in voxels:
        groups.setdefault(v[4], {})[(v[0], v[1], v[2])] = v
    drop = set()
    for part, cells in groups.items():
        left, islands = set(cells), []
        while left:
            stack = [left.pop()]
            found = list(stack)
            while stack:
                x, y, z = stack.pop()
                for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
                    if n in left:
                        left.remove(n)
                        stack.append(n)
                        found.append(n)
            islands.append(found)
        islands.sort(key=len)
        for island in islands[:-1]:
            if len(island) < 60:
                drop.update((k[0], k[1], k[2]) for k in island)
    voxels[:] = [v for v in voxels if (v[0], v[1], v[2]) not in drop]


def build_palette(colours, n):
    img = Image.fromarray(colours.astype(np.uint8)[None, :, :]).quantize(colors=n, method=Image.MEDIANCUT)
    pal = np.array(img.getpalette()[: n * 3], np.float32).reshape(-1, 3)
    return pal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--height", type=int, default=96)
    args = ap.parse_args()

    arr, mask, spans, y0, y1 = split_views(Image.open(args.image))
    cell = (y1 - y0) / args.height
    width = int(np.ceil(max(b - a for a, b in spans) / cell)) + 4
    (fa, fb), (sa, sb), (ba, bb) = spans
    front, front_c = sample(arr, mask, fa, fb, y0, y1, cell, width)
    side, side_c = sample(arr, mask, sa, sb, y0, y1, cell, width)
    back, back_c = sample(arr, mask, ba, bb, y0, y1, cell, width)
    back, back_c = back[:, ::-1], back_c[:, ::-1]   # same screen side as the front view
    rows = front.shape[0]
    centre = width / 2 - 0.5

    # The side view faces left: low columns are the character's front.
    grid = {}
    for r in range(rows):
        # Each side span is its own solid, so a cape tail cannot pull the leg off-centre.
        for sa_, sb_ in spans_of(side[r]):
            z_mid, z_half = (sa_ + sb_) / 2, (sb_ - sa_) / 2 + 0.5
            for a, b in spans_of(front[r] | back[r]):
                mid, half = (a + b) / 2, (b - a) / 2 + 0.5
                depth = min(z_half, max(half * 1.15, 2.5))
                for c in range(a, b + 1):
                    u = (c - mid) / half
                    reach = depth * np.sqrt(max(1 - u * u * 0.82, 0.05))
                    for s in range(sa_, sb_ + 1):
                        if abs(s - z_mid) <= reach:
                            grid[(c, rows - 1 - r, s)] = None

    grid = smooth_depth(grid, rows, width)

    # Pick the view each voxel shows.
    colour_of = {}
    filled = set(grid)
    for key in grid:
        c, y, s = key
        r = rows - 1 - y
        s = min(max(s, 0), width - 1)
        exposed_front = (c, y, s - 1) not in filled
        exposed_back = (c, y, s + 1) not in filled
        exposed_side = (c - 1, y, s) not in filled or (c + 1, y, s) not in filled
        if exposed_front and front[r, c]:
            colour = front_c[r, c]
        elif exposed_back and back[r, c]:
            colour = back_c[r, c]
        elif exposed_side and side[r, s]:
            colour = side_c[r, s]
        elif front[r, c]:
            colour = front_c[r, c]
        else:
            colour = back_c[r, c]
        colour_of[key] = colour

    values = np.array(list(colour_of.values()))
    palette = build_palette(values, 12)
    palette = palette[np.argsort(palette.sum(axis=1))]
    keys = list(colour_of)
    index = np.linalg.norm(values[:, None, :] - palette[None], axis=2).argmin(axis=1)

    # Landmarks as shares of height, read from the sheet: neck, belt.
    neck = int(rows * 0.715)
    belt = int(rows * 0.475)
    # Arms: the outer spans of the front view between shoulder and hand.
    torso_half = 0
    for r in range(int(rows * 0.40), int(rows * 0.52)):
        for a, b in spans_of(front[r]):
            if a <= centre <= b:
                torso_half = max(torso_half, 0)
    mid_rows = [spans_of(front[r]) for r in range(int(rows * 0.46), int(rows * 0.56))]
    gaps = [sp[1][0] - 1 for sp in mid_rows if len(sp) == 3]
    arm_edge = centre - (np.median(gaps) if gaps else centre * 0.55)
    shoulder = int(rows * 0.70)
    # Legs: a column round each leg axis below the belt.
    feet = [spans_of(front[r]) for r in range(rows - 6, rows - 1)]
    two = [sp for sp in feet if len(sp) >= 2]
    leg_axis = abs(centre - (two[0][0][0] + two[0][0][1]) / 2) if two else width * 0.2
    leg_radius = leg_axis * 0.72
    side_mid = np.median([k[2] for k in keys if k[1] < rows * 0.2])

    def is_arm(c, y):
        if not rows * 0.27 < y < shoulder:
            return False
        if y >= rows * 0.47:
            return abs(c - centre) >= arm_edge
        row = spans_of(front[rows - 1 - y])  # below the belt: only clear outer spans, not the robe
        return len(row) >= 3 and (c <= row[0][1] or c >= row[-1][0])

    voxels = []
    for key, mat in zip(keys, index):
        c, y, s = key
        dx = c - centre
        ds = s - side_mid
        right = dx < 0                     # screen left is the character's right side
        if y >= neck and abs(dx) < 12:
            part = "Head"
        elif y >= rows * 0.58 and abs(dx) >= 10:
            part = "PadR" if right else "PadL"
        elif is_arm(c, y):
            if y >= rows * 0.5:
                part = "ArmR" if right else "ArmL"
            elif y >= rows * 0.43:
                part = "ForeR" if right else "ForeL"
            elif y >= rows * 0.41:
                continue                   # wrist gap: the hand floats
            else:
                part = "HandR" if right else "HandL"
        elif y < belt * 0.9 and np.hypot(abs(dx) - leg_axis, ds * 0.8) < leg_radius:
            if y >= rows * 0.125:
                part = "LegR" if right else "LegL"
            elif y >= rows * 0.105:
                continue                   # ankle gap: the foot floats
            else:
                part = "FootR" if right else "FootL"
        elif y >= rows * 0.54:
            part = "Torso"
        elif y >= rows * 0.41:
            part = "Hips"
        elif abs(ds) > abs(dx):
            part = "SkirtF" if ds < 0 else "SkirtB"
        else:
            part = "SkirtR" if right else "SkirtL"
        voxels.append([int(c), int(y), int(s), int(mat), PARTS.index(part)])

    keep_largest(voxels, PARTS)
    counts = [sum(1 for v in voxels if v[4] == i) for i in range(len(PARTS))]

    (HERE / "voxels.json").write_text(json.dumps({
        "grid": [width, rows], "centre": centre, "side_mid": float(side_mid), "palette": palette.round().tolist(),
        "parts": PARTS, "neck": neck, "belt": belt, "shoulder": shoulder,
        "arm_edge": float(arm_edge), "leg_axis": float(leg_axis), "voxels": voxels}), encoding="utf-8")

    # Preview: front projection coloured, and part map.
    view = np.full((rows, width, 3), 235, np.uint8)
    parts = view.copy()
    tint = np.array([[(i * 97) % 200 + 40, (i * 53) % 200 + 40, (i * 151) % 200 + 40] for i in range(len(PARTS))], np.uint8)
    nearest = {}
    for v in voxels:
        k = (v[0], v[1])
        if k not in nearest or v[2] < nearest[k][2]:
            nearest[k] = v
    for (c, y), v in nearest.items():
        view[rows - 1 - y, c] = palette[v[3]]
        parts[rows - 1 - y, c] = tint[v[4]]
    both = np.concatenate([view, parts], axis=1)
    Image.fromarray(both).resize((both.shape[1] * 6, rows * 6), Image.NEAREST).save(HERE / "voxel_preview.png")
    print(f"views {spans}, grid {width}x{rows}, depth from side, voxels {len(voxels)}, parts {dict(zip(PARTS, counts))}, "
          f"arm_edge {arm_edge:.1f}, leg_axis {leg_axis:.1f}")


if __name__ == "__main__":
    main()
