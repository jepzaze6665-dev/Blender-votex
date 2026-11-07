"""Write rig.json for the dragon: bones for all 32 parts, plus the base clips.

Axes: +rx lifts anything pointing +Y and swings a leg forward, +rz yaws to the dragon's
left, and -ry raises the right wing (+ry raises the left).
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
bones = [{"name": "Root", "head": [0, -2.75, 0]}]


def add(name, parent):
    bones.append({"name": name, "parent": parent, "from": name, "mesh": name})


add("Body", "Root")
add("Core", "Body")
add("Neck1", "Body")
add("Neck2", "Neck1")
add("Neck3", "Neck2")
add("Head", "Neck3")
add("Jaw", "Head")
add("Crown", "Head")
for n in range(1, 7):
    add(f"Tail{n}", "Body" if n == 1 else f"Tail{n - 1}")
for s in "RL":
    for leg in ("Front", "Hind"):
        add(f"{leg}Upper{s}", "Body")
        add(f"{leg}Lower{s}", f"{leg}Upper{s}")
        add(f"{leg}Foot{s}", f"{leg}Lower{s}")
    add(f"WingArm{s}", "Body")
    add(f"WingFore{s}", f"WingArm{s}")
    add(f"WingPanel{s}", f"WingFore{s}")

TAU = math.tau


def wave(length, step, **channels):
    """A looping track. Each channel is (amplitude, phase in turns, optional offset)."""
    keys = []
    for f in range(1, length + 2, step):
        t = (f - 1) / length
        key = {"f": f}
        for name, spec in channels.items():
            amp, phase, *rest = spec
            key[name] = round(amp * math.sin(TAU * (t + phase)) + (rest[0] if rest else 0), 3)
        keys.append(key)
    return keys


def wing(side):
    """Mirror a wing key's roll and yaw for the left side."""
    return 1 if side == "R" else -1


def idle():
    L, st = 72, 6
    tr = {"Body": wave(L, st, z=(0.07, 0), rx=(0.8, 0.1)),
          "Neck1": wave(L, st, rx=(1.6, 0.05), rz=(2, 0.3)),
          "Neck2": wave(L, st, rx=(1.6, 0.12), rz=(2.2, 0.36)),
          "Neck3": wave(L, st, rx=(1.6, 0.2), rz=(2.2, 0.42)),
          "Head": wave(L, st, rx=(2, 0.3), rz=(2.5, 0.5)),
          "Jaw": wave(L, st, rx=(0.8, 0.3, -1))}
    for n in range(1, 7):
        tr[f"Tail{n}"] = wave(L, st, rz=(3 + n * 0.8, -n * 0.08), rx=(1.2, -n * 0.08))
    for s in "RL":
        m = wing(s)
        tr[f"WingArm{s}"] = wave(L, st, ry=(2.4 * m, 0.1), rz=(8 * m, 0.1, -3 * m))
        tr[f"WingFore{s}"] = wave(L, st, ry=(3 * m, 0.02), rz=(7 * m, 0.02))
        tr[f"WingPanel{s}"] = wave(L, st, ry=(3.5 * m, -0.06), rz=(6 * m, -0.06))
    return {"name": "Idle", "tracks": tr}


def walk():
    L, st = 48, 4
    tr = {"Root": wave(L, st, z=(0.14, 0.12), ry=(1.8, 0)),
          "Neck1": wave(L, st, rz=(3, 0.1), rx=(1.5, 0.2)),
          "Neck2": wave(L, st, rz=(2.5, 0.16)),
          "Neck3": wave(L, st, rz=(-2, 0.22)),
          "Head": wave(L, st, rz=(-3, 0.28), rx=(1.5, 0.4))}
    for n in range(1, 7):
        tr[f"Tail{n}"] = wave(L, st, rz=(4 + n, -n * 0.09))
    # Diagonal pairs step together: front right with hind left.
    for leg, s, phase in (("Front", "R", 0), ("Hind", "L", 0), ("Front", "L", 0.5), ("Hind", "R", 0.5)):
        up, lo, ft = [], [], []
        for f in range(1, L + 2, st):
            p = ((f - 1) / L + phase) % 1
            swing = math.sin(TAU * p)
            lift = max(0, math.cos(TAU * p)) ** 1.5          # raised only on the forward swing
            a = 19 * swing
            b = -30 * lift if leg == "Front" else 30 * lift
            up.append({"f": f, "rx": round(a + 8 * lift, 2)})
            lo.append({"f": f, "rx": round(b - 8 * lift, 2)})
            ft.append({"f": f, "rx": round(-(a + b) * 0.8, 2)})
        tr[f"{leg}Upper{s}"], tr[f"{leg}Lower{s}"], tr[f"{leg}Foot{s}"] = up, lo, ft
    for s in "RL":
        m = wing(s)
        # Sweeps forward and back in step with the stride, each joint trailing the last.
        tr[f"WingArm{s}"] = wave(L, st, ry=(3 * m, 0.1), rz=(15 * m, 0.25, -8 * m))
        tr[f"WingFore{s}"] = wave(L, st, ry=(4 * m, 0), rz=(11 * m, 0.17))
        tr[f"WingPanel{s}"] = wave(L, st, rz=(9 * m, 0.09))
    return {"name": "Walk", "tracks": tr}


def poses(frames):
    """frames: [(frame, {bone: key})] -> tracks. Bones carry a rest key at unlisted ends."""
    names = {b for _, pose in frames for b in pose}
    tracks = {}
    for b in names:
        tracks[b] = [{"f": f, **pose.get(b, {})} for f, pose in frames if b in pose or f in (frames[0][0], frames[-1][0])]
    return tracks


def wings(arm, fore, panel, swept=0):
    out = {}
    for s in "RL":
        m = wing(s)
        out[f"WingArm{s}"] = {"ry": -arm * m, "rz": swept * m}
        out[f"WingFore{s}"] = {"ry": -fore * m, "rz": swept * 0.7 * m}
        out[f"WingPanel{s}"] = {"ry": -panel * m, "rz": swept * 0.5 * m}
    return out


def tail(rx, rz=0):
    return {f"Tail{n}": {"rx": rx, "rz": rz} for n in range(1, 7)}


def hind(up):
    out = {}
    for s in "RL":
        out[f"HindUpper{s}"] = {"rx": -up}
        out[f"HindFoot{s}"] = {"rx": 0}
    return out


def front(up, lo):
    out = {}
    for s in "RL":
        out[f"FrontUpper{s}"] = {"rx": up}
        out[f"FrontLower{s}"] = {"rx": lo}
        out[f"FrontFoot{s}"] = {"rx": -lo * 0.6}
    return out


def roar():
    rest = {"Root": {}, "Neck1": {}, "Neck2": {}, "Neck3": {}, "Head": {}, "Jaw": {}, **wings(0, 0, 0), **tail(0), **hind(0), **front(0, 0)}
    crouch = {"Root": {"rx": -3, "z": -0.3}, "Neck1": {"rx": -16}, "Neck2": {"rx": -12}, "Neck3": {"rx": -6}, "Head": {"rx": -10}, "Jaw": {"rx": -2},
              **wings(-12, -10, -6, 16), **tail(3), **hind(-4), **front(10, -22)}
    rear = {"Root": {"rx": 15, "z": 0.3}, "Neck1": {"rx": 13}, "Neck2": {"rx": 15}, "Neck3": {"rx": 14}, "Head": {"rx": 12}, "Jaw": {"rx": -26},
            **wings(16, 12, 8, -18), **tail(-6), **hind(15), **front(-16, 34)}
    shake = {**rear, "Head": {"rx": 15, "rz": 6}, "Neck3": {"rx": 15, "rz": 4}, "Jaw": {"rx": -30}, **wings(20, 15, 11, -24)}
    shake2 = {**rear, "Head": {"rx": 15, "rz": -6}, "Neck3": {"rx": 15, "rz": -4}, "Jaw": {"rx": -30}, **wings(14, 11, 7, -12)}
    return {"name": "Roar", "tracks": poses([(1, rest), (16, crouch), (28, rear), (40, shake), (50, shake2), (60, shake), (70, rear), (92, rest)])}


def hit():
    rest = {"Root": {}, "Neck1": {}, "Neck2": {}, "Head": {}, "Jaw": {}, **wings(0, 0, 0)}
    flinch = {"Root": {"y": -0.35, "rz": 3}, "Neck1": {"rx": 6, "rz": 8}, "Neck2": {"rx": 8, "rz": 8}, "Head": {"rx": 12, "rz": 10}, "Jaw": {"rx": -14}, **wings(10, 8, 6)}
    return {"name": "Hit", "tracks": poses([(1, rest), (5, flinch), (20, rest)])}


def death():
    rest = {"Root": {}, "Neck1": {}, "Neck2": {}, "Neck3": {}, "Head": {}, "Jaw": {}, **wings(0, 0, 0), **tail(0), **hind(0), **front(0, 0)}
    stagger = {"Root": {"ry": 5, "z": -0.2}, "Neck1": {"rx": 12}, "Neck2": {"rx": 8}, "Head": {"rx": 14}, "Jaw": {"rx": -30}, **wings(12, 8, 6), **tail(-3), **hind(-3), **front(6, -8)}
    fall = {"Root": {"ry": 15, "z": -2.7}, "Neck1": {"rx": -22, "rz": 8}, "Neck2": {"rx": -16, "rz": 12}, "Neck3": {"rx": -12, "rz": 10}, "Head": {"rx": -12, "rz": 6}, "Jaw": {"rx": -16},
            **wings(-30, -32, -24, 12), **tail(4, 5), **hind(-38), **front(46, -72)}
    return {"name": "Death", "tracks": poses([(1, rest), (18, stagger), (52, fall), (72, fall)])}


def neck(a, b, c, head=0, jaw=0, yaw=0):
    return {"Neck1": {"rx": a, "rz": yaw}, "Neck2": {"rx": b, "rz": yaw}, "Neck3": {"rx": c, "rz": yaw},
            "Head": {"rx": head, "rz": yaw}, "Jaw": {"rx": jaw}}


def bite():
    wind = {"Root": {"rx": 4, "y": -0.5}, **neck(16, 14, 12, 8, -30), **tail(-3), **wings(8, 6, 4)}
    strike = {"Root": {"rx": -4, "y": 1.2, "z": -0.2}, **neck(-24, -16, -8, -6, -34), **tail(4), **wings(-6, -4, -3)}
    snap = {"Root": {"rx": -5, "y": 1.3, "z": -0.25}, **neck(-26, -17, -9, -8, 0), **tail(5), **wings(-8, -5, -4)}
    return {"name": "Bite", "tracks": poses([(1, {}), (14, wind), (19, strike), (22, snap), (30, snap), (46, {})])}


def claw():
    wind = {"Root": {"rx": 8, "rz": -7, "z": 0.2}, "Body": {"ry": -5}, **neck(6, 6, 2, 6, -10, -8), **tail(-2, 4),
            "FrontUpperR": {"rx": 62, "ry": -12}, "FrontLowerR": {"rx": -48}, "FrontFootR": {"rx": 22}, **wings(10, 8, 4)}
    strike = {"Root": {"rx": -5, "rz": 9, "y": 0.8, "z": -0.15}, "Body": {"ry": 6}, **neck(-12, -8, -4, -4, -18, 6), **tail(3, -5),
              "FrontUpperR": {"rx": 8, "ry": 12}, "FrontLowerR": {"rx": 18}, "FrontFootR": {"rx": -24}, **wings(-6, -4, -2)}
    return {"name": "Claw", "tracks": poses([(1, {}), (15, wind), (21, strike), (29, strike), (48, {})])}


def tail_swipe():
    def bend(a):
        return {f"Tail{n}": {"rz": a * (0.7 + n * 0.1), "rx": -3} for n in range(1, 7)}
    wind = {"Root": {"rz": -20, "z": -0.15}, **neck(-4, -2, 0, 0, -6, 7), **bend(13), **wings(6, 4, 2)}
    swing = {"Root": {"rz": 32, "z": 0.1}, **neck(2, 2, 0, 2, -12, -9), **bend(-15), **wings(-8, -5, -3)}
    follow = {"Root": {"rz": 26}, **neck(2, 2, 0, 2, -8, -6), **bend(9), **wings(2, 2, 1)}
    return {"name": "TailSwipe", "tracks": poses([(1, {}), (16, wind), (25, swing), (32, follow), (56, {})])}


def frost_breath():
    charge = {"Root": {"rx": 6, "z": 0.15, "y": -0.3}, **neck(18, 16, 12, 12, -4), **wings(14, 10, 6, -6), **tail(-3)}
    open_l = {"Root": {"rx": -2, "y": 0.3}, **neck(-12, -8, -4, -4, -30, 7), **wings(4, 3, 2), **tail(2, -3)}
    open_r = {**open_l, **neck(-12, -8, -4, -4, -32, -7), **tail(2, 3)}
    return {"name": "FrostBreath", "tracks": poses([(1, {}), (20, charge), (28, open_l), (48, open_r), (68, open_l), (76, open_l), (96, {})])}


def wing_gust():
    up = {"Root": {"rx": 7, "z": 0.45}, **neck(6, 6, 4, 4, -8), **wings(30, 22, 16, -26), **tail(-3)}
    down = {"Root": {"rx": 3, "z": 0.95}, **neck(-6, -4, -2, -2, -18), **wings(-26, -20, -18, 24), **tail(3)}
    return {"name": "WingGust", "tracks": poses([(1, {}), (16, up), (23, down), (32, up), (39, down), (48, up), (55, down), (76, {})])}


def intro():
    """Seven seconds, matching the ice: frozen, tremble from 1.5 s, burst at 3 s, roar from 4 s."""
    curl = {f"Tail{n}": {"rz": 24, "rx": 3} for n in range(1, 7)}
    frozen = {"Root": {"z": -2.1}, **neck(-30, -26, -18, -10, 0, 6), **wings(-36, -30, -20, -40), **curl, **hind(-34), **front(42, -68)}
    stir = {**frozen, "Root": {"z": -1.9, "rx": 3}, **neck(-24, -20, -14, -4, -4, 3)}
    burst = {"Root": {"rx": 9, "z": 0.1}, **neck(4, 8, 10, 12, -16), **wings(26, 20, 14, -10), **tail(-3), **hind(8), **front(-8, 16)}
    rear = {"Root": {"rx": 16, "z": 0.4}, **neck(14, 16, 14, 12, -30), **wings(18, 14, 10, -20), **tail(-6), **hind(16), **front(-18, 36)}
    shake_l = {**rear, **neck(15, 16, 15, 16, -32, 5), **wings(22, 16, 11, -24)}
    shake_r = {**rear, **neck(15, 16, 15, 16, -32, -5), **wings(15, 12, 8, -14)}
    land = {"Root": {"rx": -3, "z": -0.3}, **neck(-6, -4, -2, -2, -8), **wings(6, 4, 2, 8), **tail(2), **hind(-3), **front(8, -14)}
    return {"name": "Intro", "tracks": poses([(1, frozen), (37, frozen), (66, stir), (73, stir), (82, burst), (96, rear), (108, shake_l), (120, shake_r),
                                              (132, shake_l), (140, rear), (152, land), (169, {})])}


config = {"fps": 24, "bone_length": 0.5, "bones": bones, "clips": [idle(), walk(), roar(), hit(), death(), bite(), claw(), tail_swipe(), frost_breath(), wing_gust(), intro()]}
(HERE / "rig.json").write_text(json.dumps(config, indent=1), encoding="utf8")
print("bones", len(bones), "clips", [c["name"] for c in config["clips"]])
