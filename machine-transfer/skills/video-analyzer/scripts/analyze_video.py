#!/usr/bin/env python3
"""Turn a video into things Claude can actually look at and reason about.

Claude cannot watch a video, so this script produces:
  analysis.json   metadata, shots, flashes, motion peaks, frame holds, loop score,
                  palette, pixel-art hints, audio events, local environment
  sheets/         labelled contact sheets (read these first)
  frames/         the individual selected frames, for zooming in
  burst_*/        frame-by-frame sheets of a short range (--burst)
  transcript.json speech with timestamps (--transcribe)

Usage:
  python analyze_video.py VIDEO [--out DIR] [--max-frames 48]
  python analyze_video.py VIDEO --out DIR --burst 1.2-2.0 [--burst-fps 24]
  python analyze_video.py VIDEO --out DIR --transcribe [--allow-model-download]

All numbers are hints for judgement, not ground truth. Frames are decoded through
ffmpeg pipes rather than cv2 file APIs because those fail on non-ASCII Windows paths.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import cv2
except ImportError:
    cv2 = None

LOW_W = 160            # analysis width
SIG_W, SIG_H = 32, 18  # per-frame signature kept in memory
LONG_VIDEO_SEC = 600   # beyond this, analyse at a reduced frame rate
LONG_VIDEO_FPS = 10
HOLD_EPS = 0.0015      # mean abs gray diff below this counts as a repeated frame
FLOW_PER_SEC = 4       # optical-flow samples per second


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def fmt_time(t):
    m, s = divmod(max(t, 0.0), 60)
    return f"{int(m):02d}:{s:05.2f}"


def ratio(text):
    try:
        a, b = str(text).split("/")
        return float(a) / float(b) if float(b) else 0.0
    except (ValueError, ZeroDivisionError):
        try:
            return float(text)
        except (TypeError, ValueError):
            return 0.0


# ---------------------------------------------------------------- probing

def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    if r.returncode:
        sys.exit(f"ffprobe could not read the file: {r.stderr.decode('utf-8', 'replace').strip()}")
    data = json.loads(r.stdout.decode("utf-8", "replace"))
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if video is None:
        sys.exit("No video stream found in this file.")
    fmt = data.get("format", {})
    avg, raw = ratio(video.get("avg_frame_rate")), ratio(video.get("r_frame_rate"))
    fps = avg or raw or 24.0
    duration = float(fmt.get("duration") or video.get("duration") or 0)
    rotation = 0
    for side in video.get("side_data_list", []) or []:
        rotation = int(side.get("rotation", 0) or 0) or rotation
    w, h = int(video["width"]), int(video["height"])
    if abs(rotation) in (90, 270):
        w, h = h, w
    pix = video.get("pix_fmt", "")
    return {
        "file": Path(path).name,
        "size_mb": round(int(fmt.get("size", 0) or 0) / 1e6, 2),
        "container": fmt.get("format_name"),
        "duration_sec": round(duration, 3),
        "width": w,
        "height": h,
        "fps": round(fps, 3),
        "variable_frame_rate": bool(avg and raw and abs(avg - raw) > 0.5),
        "video_codec": video.get("codec_name"),
        "pix_fmt": pix,
        "may_have_alpha": bool(re.search(r"(rgba|bgra|argb|abgr|yuva|gbrap|ya\d|pal8)", pix))
        or video.get("codec_name") == "gif",
        "has_audio": audio is not None,
        "audio_codec": audio.get("codec_name") if audio else None,
    }


def frame_times(path, count, fps, reduced):
    """Real presentation times, so variable-frame-rate captures stay in sync."""
    if not reduced:
        r = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(path)])
        vals = []
        for line in r.stdout.decode("ascii", "ignore").split():
            try:
                vals.append(float(line.strip(",")))
            except ValueError:
                pass
        if len(vals) == count:
            vals.sort()
            return np.array(vals) - vals[0]
    return np.arange(count) / fps


# ---------------------------------------------------------------- active region

def longest_band(flags):
    best, start = (0, 0), None
    for i, flag in enumerate(list(flags) + [False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if i - start > best[1] - best[0]:
                best = (start, i)
            start = None
    return best


def active_region(path, meta):
    """Find the part of the frame that really changes.

    Screen recordings and letterboxed clips carry static bars or app UI that can cover
    half the frame. Left in, they dilute every measurement: cuts go unseen and the
    palette fills with black. Returns (x, y, w, h) in source pixels, or None.
    """
    if meta["may_have_alpha"]:
        return None  # effects on empty backgrounds: the "static" area is where they spread into
    w, h = 96, max(2, int(round(96 * meta["height"] / meta["width"] / 2)) * 2)
    duration = meta["duration_sec"] or 1
    rate = 0.2 if duration > LONG_VIDEO_SEC else min(8, max(2, 60 / duration))
    r = run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0",
             "-vf", f"fps={rate},scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", "-"])
    count = len(r.stdout) // (w * h)
    if count < 4:
        return None
    frames = np.frombuffer(r.stdout[:count * w * h], np.uint8).reshape(count, h, w).astype(np.int16)
    # Changing often, not just once: a title swapping mid-clip must not count as content.
    # Loose thresholds on purpose: cutting off real content (the edge of a shockwave that
    # only reaches there briefly) is worse than keeping a little UI.
    active = (np.abs(np.diff(frames, axis=0)) > 6).mean(axis=0) > 0.08
    y0, y1 = longest_band(active.mean(axis=1) > 0.02)
    x0, x1 = longest_band(active.mean(axis=0) > 0.02)
    if y1 <= y0 or x1 <= x0 or (y1 - y0) * (x1 - x0) > 0.85 * w * h or (y1 - y0) * (x1 - x0) < 0.1 * w * h:
        return None
    sx, sy = meta["width"] / w, meta["height"] / h
    x, y = int(x0 * sx) // 2 * 2, int(y0 * sy) // 2 * 2
    return x, y, int((x1 - x0) * sx) // 2 * 2, int((y1 - y0) * sy) // 2 * 2


def crop_filter(crop):
    return f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}," if crop else ""


# ---------------------------------------------------------------- single decode pass

def scan(path, meta, crop=None):
    duration = meta["duration_sec"]
    reduced = duration > LONG_VIDEO_SEC
    fps = LONG_VIDEO_FPS if reduced else meta["fps"]
    src_w, src_h = (crop[2], crop[3]) if crop else (meta["width"], meta["height"])
    low_h = max(2, int(round(LOW_W * src_h / src_w / 2)) * 2)
    chain = crop_filter(crop) + (f"fps={LONG_VIDEO_FPS}," if reduced else "") + \
        f"scale={LOW_W}:{low_h}:flags=area,format=rgb24"
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-fps_mode",
           "cfr" if reduced else "passthrough", "-vf", chain, "-f", "rawvideo", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = LOW_W * low_h * 3
    flow_every = max(1, int(round(fps / FLOW_PER_SEC)))
    next_flow = 1

    diffs, hists, sigs, flows = [0.0], [0.0], [], []
    prev_gray = prev_hist = None
    i = 0
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        rgb = np.frombuffer(buf, np.uint8).reshape(low_h, LOW_W, 3)
        gray = (rgb @ np.array([0.299, 0.587, 0.114], np.float32)).astype(np.float32)
        q = (rgb >> 5).astype(np.int32)
        hist = np.bincount((q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]).ravel(), minlength=512)
        hist = hist / hist.sum()
        sigs.append(np.asarray(Image.fromarray(rgb).resize((SIG_W, SIG_H), Image.BILINEAR)))
        if prev_gray is not None:
            diffs.append(float(np.abs(gray - prev_gray).mean()) / 255)
            hists.append(float(np.abs(hist - prev_hist).sum()) / 2)
            # Wait for a frame that changed, or held drawings would read as a still camera.
            if cv2 is not None and i >= next_flow and diffs[-1] >= HOLD_EPS:
                sample = flow_sample(prev_gray, gray)
                if sample:
                    flows.append((i, *sample))
                next_flow = i + flow_every
        prev_gray, prev_hist = gray, hist
        i += 1
    proc.stdout.close()
    proc.wait()
    if not sigs:
        sys.exit("ffmpeg decoded no frames from this file.")
    return {
        "count": len(sigs), "fps": fps, "reduced": reduced,
        "times": frame_times(path, len(sigs), fps, reduced),
        "diff": np.array(diffs), "hist": np.array(hists),
        "sig": np.stack(sigs).astype(np.int16), "flow": flows,
    }


def flow_sample(a, b):
    """Global camera motion between two frames, from tracked features and a RANSAC fit.

    Returns x and y shift in pixels, the leftover motion of things that do not follow
    the camera, and the scale change. None when there is too little texture to track.
    """
    a8, b8 = a.astype(np.uint8), b.astype(np.uint8)
    pts = cv2.goodFeaturesToTrack(a8, 200, 0.01, 5)
    if pts is None or len(pts) < 8:
        return None
    nxt, status, _ = cv2.calcOpticalFlowPyrLK(a8, b8, pts, None, winSize=(15, 15), maxLevel=3)
    ok = status.ravel() == 1
    if ok.sum() < 8:
        return None
    p0, p1 = pts[ok].reshape(-1, 2), nxt[ok].reshape(-1, 2)
    fit, _ = cv2.estimateAffinePartial2D(p0, p1, method=cv2.RANSAC, ransacReprojThreshold=1.0)
    if fit is None:
        return None
    h, w = a.shape
    centre = np.array([w / 2, h / 2, 1.0])
    shift = fit @ centre - centre[:2]
    predicted = p0 @ fit[:, :2].T + fit[:, 2]
    residual = float(np.linalg.norm(p1 - predicted, axis=1).mean())
    return float(shift[0]), float(shift[1]), residual, float(np.hypot(fit[0, 0], fit[1, 0]) - 1)


def find_events(s):
    """Separate hard cuts from flashes: a flash returns to what was there before it."""
    hist, sig, times, n = s["hist"], s["sig"], s["times"], s["count"]
    med = float(np.median(hist))
    mad = float(np.median(np.abs(hist - med))) or 0.001
    threshold = max(0.35, med + 8 * mad)
    after = max(2, int(round(s["fps"] * 0.2)))
    min_gap = 0.12
    cuts, flashes, last_cut, skip_until = [], [], -1e9, 0
    for i in np.where(hist > threshold)[0]:
        i = int(i)
        if i == 0 or i <= skip_until:
            continue
        before = sig[i - 1]
        jump = float(np.abs(sig[i] - before).mean())
        settle = float(np.abs(sig[min(n - 1, i + after)] - before).mean())
        t = float(times[i])
        if i + after < n and settle < jump * 0.45:
            flashes.append(t)
            skip_until = i + after  # the jump back out of a flash is not a cut
        elif t - last_cut >= min_gap:
            cuts.append(i)
            last_cut = t
    return cuts, flashes, threshold


def motion_peaks(s, cuts, limit=12):
    diff = s["diff"].copy()
    for c in cuts:
        diff[max(0, c - 1):c + 2] = 0
    k = max(1, int(round(s["fps"] * 0.08)))
    smooth = np.convolve(diff, np.ones(k) / k, mode="same")
    floor = float(np.percentile(smooth, 75)) if len(smooth) > 4 else 0
    gap = max(1, int(round(s["fps"] * 0.25)))
    peaks = []
    for i in np.argsort(smooth)[::-1]:
        i = int(i)
        if smooth[i] <= max(floor, 0.004) or len(peaks) >= limit:
            break
        if all(abs(i - p) >= gap for p in peaks):
            peaks.append(i)
    return sorted(peaks)


def hold_stats(s, a=0, b=None):
    """Repeated-frame run lengths reveal animating on twos/threes or a capped game capture.

    Measured per shot as well as overall: a pan on ones next to acting on twos would
    otherwise hide the cadence.
    """
    diff = s["diff"][a + 1:b]
    if s["reduced"] or len(diff) < 7:
        return {"note": "not measured (reduced-rate scan or too few frames)"}
    same = diff < HOLD_EPS
    runs, length = [], 1
    for flag in same:
        if flag:
            length += 1
        else:
            runs.append(length)
            length = 1
    runs.append(length)
    moving = [r for r in runs if r <= 8]  # longer runs are stills, not cadence
    if len(moving) < 4:
        return {"repeated_frame_share": round(float(same.mean()), 3),
                "note": "mostly static or no measurable cadence"}
    values, counts = np.unique(moving, return_counts=True)
    mode = int(values[counts.argmax()])
    return {
        "repeated_frame_share": round(float(same.mean()), 3),
        "typical_hold_frames": mode,
        "hold_distribution": {str(int(v)): int(c) for v, c in zip(values, counts)},
        "effective_fps_estimate": round(s["fps"] / mode, 2),
    }


def describe_shots(s, cuts):
    times, n = s["times"], s["count"]
    end_time = float(times[-1]) + 1.0 / max(s["fps"], 1)
    bounds = [0] + cuts + [n]
    width = float(LOW_W)
    shots = []
    for idx, (a, b) in enumerate(zip(bounds, bounds[1:]), 1):
        start = float(times[a])
        end = float(times[b]) if b < n else end_time
        samples = [f for f in s["flow"] if a < f[0] < b]
        shot = {"id": idx, "start": round(start, 3), "end": round(end, 3),
                "duration": round(end - start, 3),
                "mean_change": round(float(s["diff"][a + 1:b].mean()) if b > a + 1 else 0.0, 4)}
        shot.update(camera_hint(samples, s["fps"], width))
        holds = hold_stats(s, a, b)
        if "typical_hold_frames" in holds:
            shot["typical_hold_frames"] = holds["typical_hold_frames"]
            shot["effective_fps"] = holds["effective_fps_estimate"]
        shot["_range"] = (a, b)
        shots.append(shot)
    return shots


def camera_hint(samples, fps, width):
    if not samples:
        return {"camera_hint": "unknown"}
    arr = np.array([f[1:] for f in samples])
    vx, vy = arr[:, 0] * fps / width, arr[:, 1] * fps / width  # screen widths per second
    speed = float(np.hypot(vx, vy).mean())
    drift = float(np.hypot(vx.mean(), vy.mean()))
    zoom = float(arr[:, 3].mean() * fps)                       # scale change per second
    subject = float(arr[:, 2].mean() * fps / width)
    if abs(zoom) > 0.04 and abs(zoom) > drift:
        hint = "push-in" if zoom > 0 else "pull-out"
    elif speed < 0.015:
        hint = "locked or nearly static"
    elif len(samples) >= 3 and drift < speed * 0.35:
        hint = "shake or handheld"
    else:
        hint = "pan/track " + ("horizontal" if abs(vx.mean()) >= abs(vy.mean()) else "vertical")
    return {"camera_hint": hint, "camera_speed": round(speed, 3), "zoom_per_sec": round(zoom, 3),
            "subject_motion": round(subject, 3)}


def loop_score(s):
    sig, n = s["sig"], s["count"]
    if n < 4:
        return {"note": "too short"}
    first_to_last = float(np.abs(sig[0] - sig[-1]).mean()) / 255
    typical = float(np.median(s["diff"][1:])) or 0.0001
    # Blank at both ends means a one-shot effect, however well the two ends match.
    empty_ends = bool(sig[0].std(axis=(0, 1)).max() < 2 and sig[-1].std(axis=(0, 1)).max() < 2)
    return {"first_last_difference": round(first_to_last, 4),
            "typical_frame_difference": round(typical, 4),
            "starts_and_ends_empty": empty_ends,
            "looks_seamless": bool(first_to_last < max(typical * 2.5, 0.01)) and not empty_ends}


# ---------------------------------------------------------------- audio

def analyze_audio(path, meta):
    if not meta["has_audio"]:
        return {"present": False}
    rate = 8000
    r = run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
             "-f", "s16le", "-"])
    pcm = np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768
    if pcm.size < rate // 10:
        return {"present": True, "note": "audio stream is empty"}
    win = rate // 20
    usable = pcm[: pcm.size // win * win].reshape(-1, win)
    db = np.maximum(20 * np.log10(np.sqrt((usable ** 2).mean(axis=1)) + 1e-6), -60)
    peak = float(20 * np.log10(np.abs(pcm).max() + 1e-6))
    if peak < -50:
        return {"present": True, "silent": True, "peak_db": round(peak, 1)}
    rise = np.diff(db, prepend=db[0])
    onsets = []
    for i in np.argsort(rise)[::-1]:
        i = int(i)
        if rise[i] < 8 or len(onsets) >= 20:
            break
        if all(abs(i - o) >= 3 for o in onsets):
            onsets.append(i)
    return {"present": True, "silent": False, "peak_db": round(peak, 1),
            "mean_db": round(float(db.mean()), 1),
            "share_of_quiet_time": round(float((db < -45).mean()), 3),
            "onsets_sec": [round(i * 0.05, 2) for i in sorted(onsets)]}


def transcribe(path, out, model_name, allow_download):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return {"error": "faster-whisper is not installed"}
    # Decode with ffmpeg: faster-whisper's own PyAV path breaks on newer PyAV releases.
    r = run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", "16000",
             "-f", "f32le", "-"])
    samples = np.frombuffer(r.stdout, np.float32)
    if samples.size == 0:
        return {"error": "no audio to transcribe"}
    model, last = None, None
    for device, compute in (("cuda", "float16"), ("cpu", "int8")):
        try:
            model = WhisperModel(model_name, device=device, compute_type=compute,
                                 local_files_only=not allow_download)
            segments, info = model.transcribe(samples, vad_filter=True)
            rows = [{"start": round(x.start, 2), "end": round(x.end, 2), "text": x.text.strip()}
                    for x in segments]
            result = {"language": info.language, "device": device, "segments": rows}
            (out / "transcript.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            return {"language": info.language, "device": device, "segments": len(rows),
                    "file": "transcript.json"}
        except Exception as exc:  # GPU runtime libraries are often missing: retry on CPU
            last = str(exc)
    if "local" in (last or "").lower() or "snapshot" in (last or "").lower():
        return {"error": f"model '{model_name}' is not downloaded yet; rerun with "
                         "--allow-model-download after the user agrees"}
    return {"error": last}


# ---------------------------------------------------------------- frames and sheets

def pick_frames(s, shots, flashes, peaks, budget):
    times = s["times"]
    picks = {}

    def add(t, label):
        if len(picks) >= budget:
            return
        if all(abs(t - other) >= 0.04 for other in picks):
            picks[t] = label

    def shot_of(t):
        for shot in shots:
            if shot["start"] <= t < shot["end"]:
                return shot["id"]
        return shots[-1]["id"]

    ordered = sorted(shots, key=lambda x: -x["duration"])
    if len(shots) > budget * 0.6:          # many cuts: keep room for action frames
        ordered = ordered[: int(budget * 0.6)]
    for shot in ordered:
        add((shot["start"] + shot["end"]) / 2, f"S{shot['id']} mid")
    for t in flashes[:8]:
        add(t, f"S{shot_of(t)} flash")
    for i in peaks:
        t = float(times[i])
        add(t, f"S{shot_of(t)} peak")
    for shot in ordered:
        if shot["duration"] >= 1.0:
            add(shot["start"] + 0.04, f"S{shot['id']} first")
            add(shot["end"] - 0.08, f"S{shot['id']} last")
    span = float(times[-1])
    target = min(budget, max(16, int(span * 8)))
    if len(shots) == 1 or len(picks) < 24:  # one take or a short clip: fill evenly
        for k in range(target):
            t = span * k / target
            if len(picks) < target:
                add(t, f"S{shot_of(t)} even")
    return sorted(picks.items())


def grab(path, t, dest, meta, crop=None):
    w = crop[2] if crop else meta["width"]
    tiny = w <= 640
    scale = crop_filter(crop) + f"scale={min(w, 1280)}:-2:flags={'neighbor' if tiny else 'lanczos'}"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{max(t, 0):.3f}", "-i", str(path), "-map", "0:v:0",
           "-frames:v", "1", "-vf", scale]
    if dest.suffix == ".jpg":
        cmd += ["-q:v", "3"]
    return run(cmd + [str(dest)]).returncode == 0 and dest.exists()


def font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def flatten(path):
    """Show transparency as mid gray so effects on alpha stay visible on a sheet."""
    img = Image.open(path).convert("RGBA")
    base = Image.new("RGBA", img.size, (96, 96, 96, 255))
    base.alpha_composite(img)
    return base.convert("RGB")


def contact_sheets(items, dest_dir, prefix, meta, per_sheet=12):
    """items: (image path, label). Tiles stay near 1560px wide, which reads well as an image."""
    portrait = meta["height"] > meta["width"]
    cols = 6 if portrait else 4
    tile_w = 1560 // cols
    tile_h = max(40, int(tile_w * meta["height"] / meta["width"]))
    bar = 26
    label_font = font(16)
    upscale = meta["width"] < tile_w
    paths = []
    for page, start in enumerate(range(0, len(items), per_sheet), 1):
        chunk = items[start:start + per_sheet]
        rows = -(-len(chunk) // cols)
        sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + bar)), (18, 18, 20))
        draw = ImageDraw.Draw(sheet)
        for k, (path, label) in enumerate(chunk):
            x, y = (k % cols) * tile_w, (k // cols) * (tile_h + bar)
            thumb = flatten(path).resize((tile_w - 4, tile_h),
                                         Image.NEAREST if upscale else Image.LANCZOS)
            sheet.paste(thumb, (x + 2, y))
            draw.text((x + 6, y + tile_h + 4), label, fill=(235, 235, 235), font=label_font)
        out = dest_dir / f"{prefix}_{page:02d}.jpg"
        sheet.save(out, quality=88)
        paths.append(out)
    return paths


def pixel_block(gray):
    """Size of nearest-neighbour blocks if the frame is upscaled pixel art, else 1."""
    if gray.shape[1] < 32:
        return 1
    col = np.abs(np.diff(gray, axis=1)).mean(axis=0)
    total = float(col.sum())
    if total < 1e-6:
        return 1
    for size in (8, 6, 5, 4, 3, 2):
        best = max(float(col[r::size].sum()) for r in range(size))
        if best / total >= 0.8:
            return size
    return 1


def dominant_colours(img, n=8):
    quant = img.quantize(colors=n, method=Image.MEDIANCUT)
    palette = quant.getpalette()
    counts = sorted(quant.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    return [{"hex": "#%02x%02x%02x" % tuple(palette[i * 3:i * 3 + 3]), "share": round(c / total, 3)}
            for c, i in counts]


def style_stats(paths, meta):
    blocks, colours, sat, val, pool, vivid = [], [], [], [], [], []
    for path in paths[:: max(1, len(paths) // 10)]:
        img = flatten(path)
        arr = np.asarray(img)
        blocks.append(pixel_block(arr.astype(np.float32).mean(axis=2)))
        colours.append(len(np.unique(arr.reshape(-1, 3), axis=0)))
        hsv = np.asarray(img.convert("HSV"), np.float32) / 255
        sat.append(float(hsv[..., 1].mean()))
        val.append(float(hsv[..., 2].mean()))
        pool.append(img.resize((64, max(1, 64 * img.height // img.width))))
        vivid.append(np.asarray(img)[(hsv[..., 1] > 0.3) & (hsv[..., 2] > 0.2)])
    canvas = Image.new("RGB", (64, sum(p.height for p in pool)))
    y = 0
    for p in pool:
        canvas.paste(p, (0, y))
        y += p.height
    swatches = dominant_colours(canvas)
    # Backgrounds swamp the overall palette, so report the vivid pixels on their own too.
    pixels = np.concatenate(vivid) if vivid else np.zeros((0, 3), np.uint8)
    accents = []
    if len(pixels) >= 16:
        pixels = pixels[:: max(1, len(pixels) // 40000)]
        accents = dominant_colours(Image.fromarray(pixels[None, :, :]), 6)
    block = int(np.median(blocks))
    native = (meta["width"] // block, meta["height"] // block) if block > 1 else None
    return {"palette": swatches, "accent_palette": accents, "mean_saturation": round(float(np.mean(sat)), 3),
            "mean_brightness": round(float(np.mean(val)), 3),
            "median_unique_colours_per_frame": int(np.median(colours)),
            "pixel_block_size": block, "native_pixel_size_estimate": native,
            "low_resolution_source": meta["width"] <= 480}


def environment():
    blender = shutil.which("blender")
    if not blender:
        root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Blender Foundation"
        found = sorted(root.glob("*/blender.exe")) if root.exists() else []
        blender = str(found[-1]) if found else None
    gpu = None
    if shutil.which("nvidia-smi"):
        r = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
        gpu = r.stdout.decode("utf-8", "replace").strip() or None
    try:
        import faster_whisper  # noqa: F401
        whisper = True
    except ImportError:
        whisper = False
    return {"blender_executable": blender, "gpu": gpu, "speech_to_text": whisper,
            "optical_flow": cv2 is not None, "yt_dlp": shutil.which("yt-dlp") is not None}


# ---------------------------------------------------------------- commands

def do_burst(path, meta, out, spec, fps, crop=None):
    match = re.fullmatch(r"\s*([\d.]+)\s*-\s*([\d.]+)\s*", spec)
    if not match or float(match[2]) <= float(match[1]):
        sys.exit("--burst expects START-END in seconds, for example 1.2-2.0")
    start, end = float(match[1]), float(match[2])
    rate = fps or meta["fps"]
    if (end - start) * rate > 48:           # stay readable: thin rather than truncate
        rate = 48 / (end - start)
    folder = out / f"burst_{start:g}-{end:g}"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*"):
        old.unlink()
    width = crop[2] if crop else meta["width"]
    scale = crop_filter(crop) + "scale=" + str(min(width, 960)) + ":-2:flags=" + \
        ("neighbor" if width <= 640 else "lanczos")
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(path),
         "-map", "0:v:0", "-vf", f"fps={rate:.4f},{scale}", str(folder / "f_%04d.png")])
    frames = sorted(folder.glob("f_*.png"))
    if not frames:
        sys.exit("No frames in that range. Check it against the video length.")
    items = [(p, f"#{i + 1}  {fmt_time(start + i / rate)}") for i, p in enumerate(frames)]
    shape = {**meta, "width": crop[2], "height": crop[3]} if crop else meta
    sheets = contact_sheets(items, folder, "sheet", shape)
    print(f"{len(frames)} frames at {rate:.2f} fps in {folder}")
    for sheet in sheets:
        print(f"sheet: {sheet}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", help="output folder (default: ./video-analysis/<name>)")
    ap.add_argument("--max-frames", type=int, default=48)
    ap.add_argument("--burst", help="START-END seconds: frame-by-frame sheets of this range only")
    ap.add_argument("--burst-fps", type=float, default=0)
    ap.add_argument("--full-frame", action="store_true",
                    help="keep static bars and app UI instead of cropping to the active area")
    ap.add_argument("--transcribe", action="store_true")
    ap.add_argument("--whisper-model", default="small")
    ap.add_argument("--allow-model-download", action="store_true")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} was not found on PATH.")
    path = Path(args.video)
    if not path.is_file():
        sys.exit(f"File not found: {path}")
    out = Path(args.out) if args.out else Path.cwd() / "video-analysis" / path.stem
    out.mkdir(parents=True, exist_ok=True)
    meta = probe(path)

    crop = None if args.full_frame else active_region(path, meta)
    if args.burst:
        do_burst(path, meta, out, args.burst, args.burst_fps, crop)
        return
    if args.transcribe and (out / "analysis.json").exists():
        result = transcribe(path, out, args.whisper_model, args.allow_model_download)
        data = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
        data["transcript"] = result
        (out / "analysis.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return

    s = scan(path, meta, crop)
    if s["count"] < 2:
        sys.exit("This is a single still image. Open it directly instead of analysing it as video.")
    cuts, flashes, threshold = find_events(s)
    peaks = motion_peaks(s, cuts)
    shots = describe_shots(s, cuts)
    if not meta["duration_sec"]:
        meta["duration_sec"] = round(float(s["times"][-1]), 3)

    frames_dir, sheets_dir = out / "frames", out / "sheets"
    for folder in (frames_dir, sheets_dir):
        folder.mkdir(exist_ok=True)
        for old in folder.glob("*"):
            old.unlink()
    small = meta["width"] * meta["height"] <= 1_000_000 or meta["may_have_alpha"]
    shape = {**meta, "width": crop[2], "height": crop[3]} if crop else meta
    if crop:  # the cropped-away UI can name the source, so keep one untouched frame
        grab(path, float(s["times"][s["count"] // 2]), frames_dir / f"full_frame.{'png' if small else 'jpg'}", meta)
    items, index = [], []
    for n, (t, label) in enumerate(pick_frames(s, shots, flashes, peaks, args.max_frames), 1):
        dest = frames_dir / f"f{n:03d}_{t:08.3f}s.{'png' if small else 'jpg'}"
        if grab(path, t, dest, meta, crop):
            items.append((dest, f"{label}  {fmt_time(t)}"))
            index.append({"file": f"frames/{dest.name}", "time": round(t, 3), "label": label})
    if not items:
        sys.exit("Could not extract any frames.")
    sheets = contact_sheets(items, sheets_dir, "sheet", shape)

    audio = analyze_audio(path, meta)
    onsets = audio.get("onsets_sec", [])
    events = flashes + [float(s["times"][i]) for i in list(peaks) + cuts]
    synced = sorted({o for o in onsets if any(abs(o - e) <= 0.1 for e in events)})
    for shot in shots:
        shot.pop("_range")
    listed, shots_note = shots, None
    if len(shots) > 60:
        (out / "shots.json").write_text(json.dumps(shots, indent=1), encoding="utf-8")
        listed = sorted(sorted(shots, key=lambda x: -x["duration"])[:40], key=lambda x: x["id"])
        shots_note = f"the 40 longest of {len(shots)} shots; all of them are in shots.json"
    data = {
        "video": meta,
        "active_region": {"x": crop[0], "y": crop[1], "w": crop[2], "h": crop[3],
                          "note": "measurements and frames use this area; see frames/full_frame"}
        if crop else None,
        "scan": {"frames_decoded": s["count"], "analysis_fps": round(s["fps"], 3),
                 "reduced_rate": s["reduced"], "cut_threshold": round(threshold, 3)},
        "shots": listed,
        "shots_note": shots_note,
        "shot_count": len(shots),
        "mean_shot_seconds": round(float(np.mean([x["duration"] for x in shots])), 2),
        "flashes_sec": [round(t, 3) for t in flashes],
        "motion_peaks_sec": [round(float(s["times"][i]), 3) for i in peaks],
        "frame_holds": hold_stats(s),
        "loop": loop_score(s),
        "style": style_stats([p for p, _ in items], shape),
        "audio": audio,
        "audio_hits_matching_visual_events_sec": synced,
        "sheets": [f"sheets/{p.name}" for p in sheets],
        "frames": index,
        "environment": environment(),
    }
    if args.transcribe:
        data["transcript"] = transcribe(path, out, args.whisper_model, args.allow_model_download)
    (out / "analysis.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{meta['file']}: {meta['width']}x{meta['height']} {meta['fps']}fps {meta['duration_sec']}s, "
          f"{len(shots)} shots, {len(flashes)} flashes, {len(items)} frames")
    print(f"analysis: {out / 'analysis.json'}")
    for sheet in sheets:
        print(f"sheet: {sheet}")


if __name__ == "__main__":
    main()
