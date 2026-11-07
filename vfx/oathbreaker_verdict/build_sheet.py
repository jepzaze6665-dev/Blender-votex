"""Oathbreaker Verdict (ULTIMATE) - procedural pixel-art aura VFX sheet.
576x384, 4 rows (S, N, W, E) x 6 frames, 96x96/frame, transparent, no AA."""
import math, random
from pathlib import Path
from PIL import Image

F = 96
OUT = Path(__file__).parent
# Palette: crimson (primary) / purple (secondary) / pale rose-white (accent)
VOID = (34, 8, 46, 255)
PUR_D = (74, 18, 110, 255)
PUR = (128, 46, 180, 255)
PUR_L = (186, 102, 236, 255)
CRI_D = (110, 10, 34, 255)
CRI = (196, 22, 52, 255)
CRI_L = (255, 70, 86, 255)
ACC = (255, 214, 228, 255)
DIRS = {"S": (0, 1), "N": (0, -1), "W": (-1, 0), "E": (1, 0)}
CX, CY = 48, 66  # feet anchor (isometric ground center)


class Frame:
    def __init__(s):
        s.im = Image.new("RGBA", (F, F), (0, 0, 0, 0)); s.px = s.im.load()

    def p(s, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < F and 0 <= y < F: s.px[x, y] = c

    def blk(s, x, y, c, n=2):
        for i in range(n):
            for j in range(n): s.p(x + i, y + j, c)

    def ellipse(s, rx, ry, c, cy=CY, gap=None, dither=False):
        steps = int(2 * math.pi * max(rx, ry) * 1.5) + 8
        for k in range(steps):
            a = 2 * math.pi * k / steps
            if gap and gap(a): continue
            if dither and k % 2: continue
            s.p(CX + math.cos(a) * rx, cy + math.sin(a) * ry, c)

    def line(s, x0, y0, x1, y1, c):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / n; s.p(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, c)


def rune(fr, x, y, kind, c, hi):
    """5x5 dark oath glyphs."""
    G = ["00100|01110|00100|01010|10001",  # broken oath
         "10001|01010|00100|01010|10001",  # severance X
         "11111|00100|01110|00100|00100",  # verdict sword-cross
         "01110|10001|00100|10001|01110"]  # sundered ring
    for j, row in enumerate(G[kind % 4].split("|")):
        for i, ch in enumerate(row):
            if ch == "1": fr.p(x + i - 2, y + j - 2, hi if j == 0 else c)


def chain_link(fr, x, y, horiz, c, hi, broken=False):
    if horiz:
        pts = [(0, 0), (1, -1), (2, -1), (3, 0), (2, 1), (1, 1)]
    else:
        pts = [(0, 0), (-1, 1), (-1, 2), (0, 3), (1, 2), (1, 1)]
    for k, (i, j) in enumerate(pts):
        if broken and k == 3: continue
        fr.p(x + i, y + j, hi if k == 1 else c)


def flame_col(fr, x, base, h, cols, rng):
    for k in range(h):
        y = base - k
        w = max(0, int((1 - k / h) * 2.2))
        c = cols[min(len(cols) - 1, int(k / h * len(cols)))]
        for dx in range(-w, w + 1):
            if rng.random() < 0.85: fr.p(x + dx + (1 if k % 6 > 3 else 0), y, c)


def frame(fi, d, seed):
    rng = random.Random(seed)
    fr = Frame(); dx, dy = DIRS[d]
    # ---- ground sigil ----
    ring = [(14, 5), (22, 8), (30, 11), (38, 14), (40, 15), (42, 16)][fi]
    rc = [PUR_D, PUR, CRI, CRI_L, CRI, PUR_D][fi]
    rx, ry = ring
    gap = lambda a: (int(a * 6 / math.pi) % 3 == 2) if fi >= 4 else False
    fr.ellipse(rx, ry, rc, gap=gap, dither=fi == 5)
    if fi in (1, 2, 3, 4):
        fr.ellipse(rx - 5, ry - 2, PUR if fi != 3 else CRI, dither=fi == 4)
    if fi in (2, 3):
        fr.ellipse(rx + 3, ry + 1, PUR_D, dither=True)
    # glyphs around ring
    if 1 <= fi <= 4:
        n = 6
        for k in range(n):
            a = 2 * math.pi * k / n + fi * 0.25
            c = [PUR, CRI, CRI_L, PUR][fi - 1]
            rune(fr, CX + math.cos(a) * (rx - 9), CY + math.sin(a) * (ry - 3) - (fi - 1),
                 k, c, ACC if fi == 3 else CRI_L)
    # ---- rising aura flames ----
    hgt = [6, 16, 30, 44, 26, 10][fi]
    count = [6, 12, 18, 22, 14, 6][fi]
    for k in range(count):
        a = 2 * math.pi * k / count + rng.random() * 0.3
        x = CX + math.cos(a) * rx * 0.75
        base = CY + math.sin(a) * ry * 0.75
        h = int(hgt * (0.55 + rng.random() * 0.45))
        cols = [CRI_D, CRI, PUR, PUR_D] if fi < 3 else [CRI, CRI_L, PUR_L, PUR] if fi == 3 else [PUR_D, PUR, CRI_D]
        flame_col(fr, x, base, h, cols, rng)
    # ---- chains rising and breaking ----
    if 1 <= fi <= 3:
        for side in (-1, 1):
            x = CX + side * (rx - 4)
            top = CY - [0, 14, 28, 40][fi]
            y = CY
            while y > top:
                chain_link(fr, x, y - 3, False, PUR, PUR_L, broken=(fi == 3 and y < top + 8))
                y -= 4
    if fi in (3, 4, 5):  # broken chain shards fly outward, biased to facing
        spread = [0, 0, 0, 16, 30, 40][fi]
        for k in range(14 if fi < 5 else 7):
            a = rng.random() * 2 * math.pi
            r = spread * (0.6 + rng.random() * 0.5)
            x = CX + math.cos(a) * r + dx * spread * 0.45
            y = CY - 22 + math.sin(a) * r * 0.7 + dy * spread * 0.3
            chain_link(fr, x, y, rng.random() < 0.5, PUR if fi < 5 else PUR_D,
                       PUR_L if fi < 5 else PUR, broken=True)
    # ---- verdict explosion (impact) ----
    ec = (CX + dx * 4, CY - 22 + dy * 3)
    if fi == 2:
        for r, c in ((5, CRI), (3, CRI_L), (1, ACC)):
            for yy in range(-r, r + 1):
                for xx in range(-r, r + 1):
                    if xx * xx + yy * yy <= r * r: fr.p(ec[0] + xx, ec[1] + yy, c)
    if fi == 3:
        for r, c in ((20, PUR_D), (16, PUR), (12, CRI), (8, CRI_L), (4, ACC)):
            for yy in range(-r, r + 1):
                for xx in range(-r, r + 1):
                    d2 = xx * xx + yy * yy
                    if d2 <= r * r and (r < 20 or (xx + yy) % 2 == 0):
                        fr.p(ec[0] + xx, ec[1] + yy, c)
        for k in range(12):  # jagged rays
            a = 2 * math.pi * k / 12 + 0.13
            L = 30 if k % 2 else 22
            L += 8 if (round(math.cos(a)) == dx and round(math.sin(a)) == dy) else 0
            fr.line(ec[0] + math.cos(a) * 18, ec[1] + math.sin(a) * 18,
                    ec[0] + math.cos(a) * L, ec[1] + math.sin(a) * L, CRI_L if k % 2 else PUR_L)
        # oath glyph burned into core
        rune(fr, ec[0], ec[1], 2, VOID, VOID)
    if fi == 4:  # hollow shock ring
        for r, c in ((26, CRI), (24, PUR)):
            n = 120
            for k in range(n):
                if k % 7 == 0: continue
                a = 2 * math.pi * k / n
                fr.p(ec[0] + math.cos(a) * r, ec[1] + math.sin(a) * r * 0.8, c)
        rune(fr, ec[0], ec[1] - 26, 1, CRI, CRI_L)
    # ---- oath symbol crown ----
    if fi in (2, 3, 4):
        oy = CY - [0, 0, 48, 56, 60][fi]
        c = [0, 0, PUR, CRI_L, PUR_D][fi]
        rune(fr, CX, oy, 0, c, ACC if fi == 3 else c)
    # ---- particles / embers ----
    pn = [6, 10, 18, 30, 34, 16][fi]
    for k in range(pn):
        x = CX + rng.randint(-rx - 4, rx + 4) + dx * fi * 2
        y = CY - rng.randint(0, hgt + 14) + dy * fi
        c = rng.choice([CRI_L, PUR_L, ACC, CRI] if fi < 5 else [PUR, CRI_D, PUR_D])
        if fi in (3, 4) and k % 4 == 0: fr.blk(x, y, c)
        else: fr.p(x, y, c)
    # ---- 1px dark outline for readability over any character ----
    src = fr.im.copy().load()
    for y in range(F):
        for x in range(F):
            if src[x, y][3] == 0 and fi < 5:
                for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + ox, y + oy
                    if 0 <= xx < F and 0 <= yy < F and src[xx, yy][3] and src[xx, yy] not in (VOID, PUR_D):
                        if (x + y) % 3 == 0: fr.px[x, y] = VOID
                        break
    return fr.im


sheet = Image.new("RGBA", (F * 6, F * 4), (0, 0, 0, 0))
for r, d in enumerate("SNWE"):
    for fi in range(6):
        sheet.paste(frame(fi, d, 1000 * r + fi), (fi * F, r * F))
sheet.save(OUT / "oathbreaker_verdict_aura_576x384.png")
sheet.resize((F * 6 * 2, F * 4 * 2), Image.NEAREST).save(OUT / "preview_x2.png")
print("ok", sheet.size)
