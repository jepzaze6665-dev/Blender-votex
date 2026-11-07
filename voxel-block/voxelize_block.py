#!/usr/bin/env python3
"""Turn a blocky turnaround sheet with floating hands and feet into voxel parts.

  python voxelize_block.py ../assets/from-user/block-character-turnaround.png

Blocks stay boxy: silhouettes are intersected without rounding. Writes voxels.json and
voxel_preview.png next to this script.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).parent
PARTS = ["Body", "Head", "Cape", "PadR", "PadL", "HandR", "HandL", "FootR", "FootL"]


def split_views(arr, mask):
    used = mask.any(axis=0)
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
    return spans, int(ys.min()), int(ys.max()) + 1


def sample(arr, mask, x0, x1, y0, cell, rows, width):
    solid = np.zeros((rows, width), bool)
    colour = np.zeros((rows, width, 3), np.float32)
    mid = (x0 + x1) / 2
    for r in range(rows):
        for c in range(width):
            xa, ya = int(mid + (c - width / 2) * cell), int(y0 + r * cell)
            xb, yb = int(xa + cell) + 1, int(ya + cell) + 1
            if xa < x0 or xb > x1:
                continue
            m = mask[ya:yb, xa:xb]
            if m.size and m.mean() >= 0.5:
                solid[r, c] = True
                colour[r, c] = np.median(arr[ya:yb, xa:xb][m], axis=0)
    return solid, colour


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--height", type=int, default=56)
    ap.add_argument("--neck", type=float, default=0.43, help="share of height from the top")
    ap.add_argument("--hand-offset", type=float, default=0.18, help="hand centre behind the side view centre")
    args = ap.parse_args()

    arr = np.asarray(Image.open(args.image).convert("RGB"), np.float32)
    mask = np.abs(arr - 255).sum(axis=2) > 70
    spans, y0, y1 = split_views(arr, mask)
    rows = args.height
    cell = (y1 - y0) / rows
    width = int(np.ceil(max(b - a for a, b in spans) / cell)) + 2
    (fa, fb), (sa, sb), (ba, bb) = spans
    front, front_c = sample(arr, mask, fa, fb, y0, cell, rows, width)
    side, side_c = sample(arr, mask, sa, sb, y0, cell, rows, width)
    back, back_c = sample(arr, mask, ba, bb, y0, cell, rows, width)
    back, back_c = back[:, ::-1], back_c[:, ::-1]
    union = front | back
    centre = width / 2 - 0.5

    count, labels, stats, _ = cv2.connectedComponentsWithStats(union.astype(np.uint8), connectivity=4)
    order = sorted(range(1, count), key=lambda i: -stats[i, cv2.CC_STAT_AREA])
    body_label, extras = order[0], [i for i in order[1:] if stats[i, cv2.CC_STAT_AREA] >= 12]
    role = {}
    for i in extras:
        cols = np.where(labels == i)[1]
        rws = np.where(labels == i)[0]
        kind = "Foot" if rws.max() >= rows - 3 else "Hand"
        role[i] = kind + ("R" if cols.mean() < centre else "L")
    if sorted(role.values()) != ["FootL", "FootR", "HandL", "HandR"]:
        raise SystemExit(f"could not find hands and feet separately: {role}")

    side_cols = np.where(side.any(axis=0))[0]
    side_min, side_max = int(side_cols.min()), int(side_cols.max())
    side_mid = (side_min + side_max) / 2
    span = side_max - side_min
    neck = int(rows * args.neck)
    chest = [np.where(front[r] & (labels[r] == body_label))[0] for r in range(int(rows * 0.60), int(rows * 0.68))]
    torso_half = float(np.median([max(abs(c.min() - centre), abs(c.max() - centre)) for c in chest if len(c)]))
    cape_from = side_min + span * 0.84

    grid = {}
    hand_mid = side_mid + span * args.hand_offset
    for r in range(rows):
        y = rows - 1 - r
        sc = np.where(side[r])[0]
        for c in np.where(union[r])[0]:
            label = labels[r, c]
            if label == body_label:
                dx = abs(c - centre)
                if r < neck:
                    part, zs = "Head", sc
                elif dx > torso_half:
                    part = "PadR" if c < centre else "PadL"
                    zs = np.arange(int(hand_mid - 6), int(hand_mid + 7))
                else:
                    part, zs = "Body", sc
            elif label in role:
                part = role[label]
                if part.startswith("Hand"):
                    cells = np.where((labels == label).any(axis=0))[0]
                    half = (cells.max() - cells.min() + 1) / 2 * 0.9
                    zs = np.arange(int(hand_mid - half), int(hand_mid + half) + 1)
                else:
                    zs = sc
            else:
                continue
            for s in zs:
                name = "Cape" if part == "Body" and s >= cape_from else part
                grid[(int(c), y, int(s))] = name

    filled = set(grid)
    colours = []
    for c, y, s in grid:
        r = rows - 1 - y
        if (c, y, s - 1) not in filled and front[r, c]:
            colour = front_c[r, c]
        elif (c, y, s + 1) not in filled and back[r, c]:
            colour = back_c[r, c]
        elif side[r, s] and ((c - 1, y, s) not in filled or (c + 1, y, s) not in filled or (c, y + 1, s) not in filled):
            colour = side_c[r, s]
            # The side view draws an eye, but the front view already supplies both eyes.
            if r < neck and colour[1] > 165 and colour[2] > 225:
                colour = np.array([8, 12, 34], np.float32)
        elif front[r, c]:
            colour = front_c[r, c]
        else:
            colour = back_c[r, c]
        colours.append(colour)
    values = np.array(colours)
    quant = Image.fromarray(values.astype(np.uint8)[None]).quantize(colors=10, method=Image.MEDIANCUT)
    palette = np.array(quant.getpalette()[:30], np.float32).reshape(-1, 3)
    palette = palette[np.argsort(palette.sum(axis=1))]
    index = np.linalg.norm(values[:, None] - palette[None], axis=2).argmin(axis=1)

    voxels = [[c, y, s, int(m), PARTS.index(p)] for ((c, y, s), p), m in zip(grid.items(), index)]
    (HERE / "voxels.json").write_text(json.dumps({
        "grid": [width, rows], "centre": centre, "side_mid": side_mid, "neck": rows - neck,
        "palette": palette.round().tolist(), "parts": PARTS, "voxels": voxels}), encoding="utf-8")

    view = np.full((rows, width, 3), 235, np.uint8)
    tint = np.full((rows, width, 3), 235, np.uint8)
    hues = np.array([[(i * 97) % 200 + 40, (i * 53) % 200 + 40, (i * 151) % 200 + 40] for i in range(len(PARTS))], np.uint8)
    near = {}
    for v in voxels:
        if (v[0], v[1]) not in near or v[2] < near[(v[0], v[1])][2]:
            near[(v[0], v[1])] = v
    for (c, y), v in near.items():
        view[rows - 1 - y, c] = palette[v[3]]
        tint[rows - 1 - y, c] = hues[v[4]]
    both = np.concatenate([view, tint], axis=1)
    Image.fromarray(both).resize((both.shape[1] * 8, rows * 8), Image.NEAREST).save(HERE / "voxel_preview.png")
    print(f"grid {width}x{rows}, {cell:.1f} px per voxel, voxels {len(voxels)}, parts",
          {p: sum(1 for v in voxels if v[4] == i) for i, p in enumerate(PARTS)})


if __name__ == "__main__":
    main()
