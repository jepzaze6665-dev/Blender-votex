#!/usr/bin/env python3
"""Turn a flat weapon concept image into a voxel grid for build_weapon.py.

  python voxelize.py ../assets/from-user/weapon-concept.png --height 96

Writes voxels.json and voxel_preview.png next to this script. Thickness comes from a
distance transform: thin at edges, thick at the core, mirrored front to back.
"""
import argparse
import json
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).parent

# Material roles, chosen by colour. Index order is the palette order in voxels.json.
PALETTE = [
    ("frame_dark", (20, 28, 78)),
    ("frame_mid", (34, 56, 130)),
    ("blade_blue", (62, 104, 200)),
    ("edge_glow", (96, 176, 240)),
    ("crystal", (170, 228, 252)),
]
GLOW_FROM = 3  # palette indices from here on emit light


def upright(img, background=254):
    """Rotate so the shaft is vertical, found from the long straight part of the mask."""
    arr = np.asarray(img.convert("RGB"), np.float32)
    mask = np.abs(arr - 255).sum(axis=2) > 60
    ys, xs = np.where(mask)
    # The shaft is the lower-right run of the mask in this kind of diagonal concept.
    keep = (xs > xs.min() + 0.55 * np.ptp(xs)) & (ys > ys.min() + 0.45 * np.ptp(ys))
    keep &= xs < xs.min() + 0.88 * np.ptp(xs)
    pts = np.stack([xs[keep], ys[keep]], 1).astype(np.float64)
    direction = np.linalg.svd(pts - pts.mean(0), full_matrices=False)[2][0]
    if direction[1] < 0:
        direction = -direction
    angle = float(np.degrees(np.arctan2(direction[0], direction[1])))
    turned = img.convert("RGB").rotate(-angle, Image.BICUBIC, expand=True,
                                       fillcolor=(background,) * 3)
    return turned, angle


def to_grid(img, height):
    arr = np.asarray(img, np.float32)
    mask = np.abs(arr - 255).sum(axis=2) > 60
    ys, xs = np.where(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cell = (y1 - y0) / height
    width = int(np.ceil((x1 - x0) / cell))
    solid = np.zeros((height, width), bool)
    colour = np.zeros((height, width, 3), np.float32)
    for r in range(height):
        for c in range(width):
            ya, yb = int(y0 + r * cell), int(y0 + (r + 1) * cell)
            xa, xb = int(x0 + c * cell), int(x0 + (c + 1) * cell)
            m = mask[ya:yb, xa:xb]
            if m.size and m.mean() >= 0.45:
                solid[r, c] = True
                colour[r, c] = np.median(arr[ya:yb, xa:xb][m], axis=0)
    return solid, colour, cell


def assign(colour, solid):
    table = np.array([p[1] for p in PALETTE], np.float32)
    dist = np.linalg.norm(colour[..., None, :] - table, axis=-1)
    return smooth(np.where(solid, dist.argmin(axis=-1), -1))


def smooth(material):
    """Replace lone speckles with the majority of their neighbours; glowing cells stay."""
    out = material.copy()
    h, w = material.shape
    for r in range(h):
        for c in range(w):
            if material[r, c] < 0 or material[r, c] >= GLOW_FROM:
                continue
            around = material[max(r - 1, 0):r + 2, max(c - 1, 0):c + 2].ravel()
            around = around[(around >= 0) & (around < GLOW_FROM)]
            if len(around) >= 3:
                values, counts = np.unique(around, return_counts=True)
                if counts.max() > len(around) / 2:
                    out[r, c] = values[counts.argmax()]
    return out


def pulse_path(solid, tip):
    """Walking distance from the blade tip, 0 to 1: the route the energy pulse travels."""
    h, w = solid.shape
    dist = np.full((h, w), -1.0)
    dist[tip] = 0
    queue = deque([tip])
    while queue:
        r, c = queue.popleft()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                n = (r + dr, c + dc)
                if 0 <= n[0] < h and 0 <= n[1] < w and solid[n] and dist[n] < 0:
                    dist[n] = dist[r, c] + 1
                    queue.append(n)
    return dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--height", type=int, default=128)
    ap.add_argument("--max-half", type=int, default=3)
    args = ap.parse_args()

    img, angle = upright(Image.open(args.image))
    solid, colour, cell = to_grid(img, args.height)
    material = assign(colour, solid)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(solid.astype(np.uint8), connectivity=8)
    main_label = 1 + int(stats[1:, cv2.CC_STAT_AREA].argmax())
    core = labels == main_label

    depth = cv2.distanceTransform(solid.astype(np.uint8), cv2.DIST_L2, 3)
    half = np.clip(np.round(depth * 0.75 - 0.5), 0, args.max_half).astype(int)

    # Blade tip: the lowest solid cell in the left half of the grid.
    h, w = solid.shape
    rows, cols = np.where(core & (np.arange(w)[None, :] < w * 0.45))
    tip = (int(rows.max()), int(cols[rows.argmax()]))
    walk = pulse_path(core, tip)
    # The pulse ends at the head crystal, so everything further along the shaft stays dark
    # unless it glows on its own.
    crystal_rows, crystal_cols = np.where(core & (material == 4) & (np.arange(h)[:, None] < h * 0.35))
    limit = float(walk[crystal_rows, crystal_cols].max()) if len(crystal_rows) else float(walk.max())

    voxels = []
    for r, c in zip(*np.where(solid)):
        island = 0 if core[r, c] else int(labels[r, c])
        p = float(walk[r, c]) / limit if core[r, c] else 1.0
        for z in range(-int(half[r, c]), int(half[r, c]) + 1):
            voxels.append([int(c), int(h - 1 - r), z, int(material[r, c]), round(p, 3), island])

    (HERE / "voxels.json").write_text(json.dumps({
        "source": Path(args.image).name, "rotation_deg": round(angle, 2), "pixels_per_voxel": round(cell, 2),
        "grid": [int(w), int(h)], "palette": [{"name": n, "rgb": c} for n, c in PALETTE],
        "glow_from": GLOW_FROM, "voxels": voxels}), encoding="utf-8")

    table = np.array([(235, 235, 240)] + [p[1] for p in PALETTE], np.uint8)
    preview = Image.fromarray(table[material + 1]).resize((w * 8, h * 8), Image.NEAREST)
    preview.save(HERE / "voxel_preview.png")
    print(f"rotated {angle:.1f} deg, grid {w}x{h}, {cell:.1f} px per voxel, {len(voxels)} voxels, "
          f"{count - 2} islands, tip {tip}, materials {np.bincount(material[solid], minlength=5).tolist()}")


if __name__ == "__main__":
    main()
