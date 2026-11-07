"""Validate the rendered Oathbreaker Verdict sequence and package it for engines.

    python package_and_validate.py

Outputs (render/):
  validation.json                - pass/fail checks (empty ends, no edge clipping, palette hues, no popping)
  oathbreaker_verdict_sheet_256.png/.json - 9x8 sprite atlas for HTML5 Canvas 2D
  preview.gif, contact_sheet.png - review media composited over a dark ground
"""
import glob, json, os, colorsys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "render")
meta = json.load(open(os.path.join(R, "oathbreaker_verdict_meta.json")))
files = sorted(glob.glob(os.path.join(R, "frames", "oathbreaker_verdict_*.png")))
frames = [np.array(Image.open(f).convert("RGBA")) for f in files]
assert len(frames) == meta["frames"], (len(frames), meta["frames"])

# ---- checks ---------------------------------------------------------------
border = max(int(max(a[:3, :, 3].max(), a[-3:, :, 3].max(), a[:, :3, 3].max(), a[:, -3:, 3].max())) for a in frames)
cover = [float((a[..., 3] > 4).mean()) for a in frames]
energy = [float(a[..., 3].astype(np.float64).sum() / 255) for a in frames]
jumps = [abs(energy[i + 1] - energy[i]) / max(energy) for i in range(len(energy) - 1)]

# palette audit: hue of visible, saturated pixels (alpha-weighted)

tot = bad = 0.0
for a in frames[::2]:
    m = (a[..., 3] > 40)
    px = a[m][:, :3].astype(np.float64) / 255
    if not len(px):
        continue
    w = a[m][:, 3].astype(np.float64)
    mx, mn = px.max(1), px.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    keep = (sat > 0.25) & (mx > 0.12)
    r, g, b = px[keep].T
    d = (mx - mn)[keep]
    h = np.where(mx[keep] == r, ((g - b) / d) % 6, np.where(mx[keep] == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    ok = (h >= 255) | (h <= 15)
    tot += w[keep].sum()
    bad += w[keep][~ok].sum()
off_palette = bad / max(tot, 1)

checks = {
    "frame_count": len(frames), "resolution": list(frames[0].shape[1::-1]),
    "first_frame_empty": bool(frames[0][..., 3].max() == 0),
    "last_frame_empty": bool(frames[-1][..., 3].max() == 0),
    "edge_max_alpha (3px border, all frames)": border, "no_edge_clipping": border == 0,
    "peak_coverage_frame": int(np.argmax(cover)) + 1, "peak_coverage_pct": round(100 * max(cover), 2),
    "max_frame_to_frame_alpha_jump_pct": round(100 * max(jumps), 2),
    "off_palette_hue_pct (outside 255..360/0..15 deg)": round(100 * off_palette, 3),
    "palette_ok": bool(off_palette < 0.01),
}
checks["PASS"] = bool(all(checks[k] for k in ("first_frame_empty", "last_frame_empty", "no_edge_clipping", "palette_ok")))
json.dump(checks, open(os.path.join(R, "validation.json"), "w"), indent=2)
print(json.dumps(checks, indent=2))

# ---- sprite atlas (Canvas 2D) -------------------------------------------------
S, COLS = 256, 9
rows = (len(frames) + COLS - 1) // COLS
sheet = Image.new("RGBA", (S * COLS, S * rows), (0, 0, 0, 0))
k = S / meta["resolution"][0]
for i, f in enumerate(files):
    sheet.paste(Image.open(f).resize((S, S), Image.LANCZOS), ((i % COLS) * S, (i // COLS) * S))
sheet.save(os.path.join(R, "oathbreaker_verdict_sheet_256.png"), optimize=True)
json.dump({"image": "oathbreaker_verdict_sheet_256.png", "frame_w": S, "frame_h": S, "cols": COLS,
           "rows": rows, "frames": len(frames), "fps": meta["fps"],
           "anchor_feet": [round(v * k, 2) for v in meta["anchor_feet_px"]],
           "anchor_core": [round(v * k, 2) for v in meta["anchor_core_px"]],
           "phases_frames": meta["phases_frames"], "impact_frame": meta["impact_frame"]},
          open(os.path.join(R, "oathbreaker_verdict_sheet_256.json"), "w"), indent=2)

# ---- review media ---------------------------------------------------------------
def on_ground(f, size):
    im = Image.open(f).convert("RGBA")
    bg = Image.new("RGBA", im.size, (24, 22, 28, 255))
    bg.alpha_composite(im)
    return bg.resize((size, size), Image.LANCZOS).convert("RGB")

gif = [on_ground(f, 512) for f in files]
gif[0].save(os.path.join(R, "preview.gif"), save_all=True, append_images=gif[1:],
            duration=round(1000 / meta["fps"]), loop=0)
pick = list(range(0, len(files), 6)) + [len(files) - 1]
T = 300
cs = Image.new("RGB", (T * 5, T * ((len(pick) + 4) // 5)), (24, 22, 28))
for j, i in enumerate(pick):
    t = on_ground(files[i], T)
    ImageDraw.Draw(t).text((6, 6), f"f{i + 1:02d}", fill=(200, 200, 200))
    cs.paste(t, ((j % 5) * T, (j // 5) * T))
cs.save(os.path.join(R, "contact_sheet.png"))
print("packaged")
