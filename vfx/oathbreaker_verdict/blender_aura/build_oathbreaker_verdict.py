"""ECLIPSE ONLINE - OATHBREAKER - "Oathbreaker Verdict" (ULTIMATE) aura VFX.

Builds a modular, fully procedural, animated 3D VFX asset in Blender (Eevee) and
optionally renders it as a transparent RGBA PNG sequence.

    blender -b --factory-startup --python build_oathbreaker_verdict.py -- [--save] [--frames 10,30] [--all]

Everything is deterministic (fixed seeds, keyed animation, no simulation caches).
Origin (0,0,0) = character feet. Core sits at chest height (H). No lights, no
floor, no world, no character: emission-only materials, so nothing casts shadows.
"""
import bpy, bmesh, math, random, sys, os, json
from mathutils import Vector, Euler, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
N = 72            # frames (3.0 s @ 24 fps)
FPS = 24
RES = 1024
H = 1.1           # core height above origin (chest of a ~2 m character)
CAM_TARGET = Vector((0.0, 0.0, 0.85))
ORTHO = 10.6
SEED = 6665
rng = random.Random(SEED)

PHASES = {"appear": (0.0, 0.15), "charge": (0.15, 0.35), "release": (0.35, 0.55),
          "impact": (0.55, 0.70), "follow_through": (0.70, 0.85), "fade_out": (0.85, 1.0)}


def F(p):
    """Normalized timeline position (0..1) -> frame."""
    return 1.0 + p * (N - 1)


# ----------------------------------------------------------------- palette ---
def srgb(h, a=1.0):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (a,)


VOID = srgb("0C0311")       # shadow: near-black purple
SHADOW = srgb("1E0730")
VIOLET = srgb("4A1270")     # secondary: dark violet
PURPLE = srgb("6A1AA8")     # secondary: corrupted purple
CRIMSON_D = srgb("6E0822")  # primary: deep crimson
CRIMSON = srgb("C40F33")
HOT = srgb("FF1E50")        # accent: bright crimson-purple emission
HOT_V = srgb("B42CE0")

R_CRIMSON = [(0.0, VOID), (0.3, CRIMSON_D), (0.68, CRIMSON), (1.0, HOT)]
R_VIOLET = [(0.0, VOID), (0.3, VIOLET), (0.7, PURPLE), (1.0, HOT_V)]
R_MIX = [(0.0, VOID), (0.28, VIOLET), (0.62, CRIMSON), (1.0, HOT)]
R_DARK = [(0.0, VOID), (0.55, SHADOW), (1.0, VIOLET)]
R_CHAIN = [(0.0, VOID), (0.4, SHADOW), (0.72, PURPLE), (1.0, HOT)]
R_WAVE_C = [(0.0, CRIMSON_D), (0.6, CRIMSON), (1.0, HOT)]
R_WAVE_V = [(0.0, VIOLET), (0.6, PURPLE), (1.0, HOT_V)]


# ---------------------------------------------------------------- keyframes ---
def _interp(kind):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = kind


def key(idb, path, p, value, interp="BEZIER"):
    _interp(interp)
    if path.startswith('["'):
        idb[path[2:-2]] = value
    else:
        setattr(idb, path, value)
    idb.keyframe_insert(data_path=path, frame=F(p))


def keys(idb, path, pairs, interp="BEZIER"):
    for p, v in pairs:
        key(idb, path, p, v, interp)


def props(obj, alpha=(), emit=(), dissolve=()):
    """Animate the per-object shader controls read by every VFX material."""
    for name, pairs in (("vfx_alpha", alpha), ("vfx_emit", emit), ("vfx_dissolve", dissolve)):
        for p, v in pairs:
            key(obj, f'["{name}"]', p, float(v))


def key_mod(obj, mod, ident, pairs, interp="BEZIER"):
    _interp(interp)
    for p, v in pairs:
        set_mod_input(obj.modifiers[mod], ident, v)
        tgt = getattr(obj.modifiers[mod], "properties", None)
        if tgt is not None:   # Blender 5.x: md.properties.inputs.Socket_N
            getattr(tgt.inputs, ident).keyframe_insert("value", frame=F(p))
        else:
            obj.keyframe_insert(data_path=f'modifiers["{mod}"]["{ident}"]', frame=F(p))


def set_mod_input(md, ident, v):
    if hasattr(md, "properties"):
        getattr(md.properties.inputs, ident).value = v
    else:
        md[ident] = v


# -------------------------------------------------------------- scene setup ---
def reset_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights,
                 bpy.data.curves, bpy.data.node_groups, bpy.data.textures):
        for b in list(coll):
            coll.remove(b)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def coll(name, parent):
    c = bpy.data.collections.new(name)
    parent.children.link(c)
    return c


def new_obj(name, data, c, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, data)
    c.objects.link(o)
    o.parent = parent
    o.location = loc
    if data is None:
        o.empty_display_type = "PLAIN_AXES"
        o.empty_display_size = 0.25
    else:
        for attr in ("visible_shadow",):
            if hasattr(o, attr):
                setattr(o, attr, False)
        o["vfx_alpha"] = 0.0
        o["vfx_emit"] = 1.0
        o["vfx_dissolve"] = 0.0
    return o


# --------------------------------------------------------------- materials ---
def _sock(sockets, name, typ=None):
    for s in sockets:
        if s.name == name and (typ is None or s.type == typ):
            return s
    raise KeyError(name)


class NB:
    """Tiny shader-node builder."""

    def __init__(self, nt):
        self.nt = nt
        self.x = 0

    def node(self, t, **kw):
        n = self.nt.nodes.new(t)
        for k, v in kw.items():
            setattr(n, k, v)
        n.location = (self.x, 0)
        self.x += 40
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.link(v, sock)
        else:
            sock.default_value = v

    def math(self, op, a, b=0.0, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.set(n.inputs[0], a)
        self.set(n.inputs[1], b)
        return n.outputs[0]


def mk_mat(name, ramp, emit=2.0, a_const=0.0, a_rim=0.0, a_uv=0.0, e_const=0.25, e_rim=0.6,
           e_uv=0.0, e_noise=0.3, rim_pow=2.0, rim_invert=False, uv_mode=None, uv_pow=1.0,
           breakup=0.3, noise_scale=3.0, noise_speed=1.0, obj_attrs=True):
    """Shared emissive/transparent VFX shader.

    energy  = const + rim*facing^p + uv term + animated 4D noise   -> palette ramp
    alpha   = (const + rim + uv) * noise breakup * dissolve mask * vfx_alpha
    Object custom props vfx_alpha / vfx_emit / vfx_dissolve drive each object.
    """
    m = bpy.data.materials.new(name)
    if not m.node_tree:
        m.use_nodes = True
    for attr, v in (("surface_render_method", "BLENDED"), ("use_backface_culling", False),
                    ("use_transparency_overlap", True), ("blend_method", "BLEND")):
        try:
            setattr(m, attr, v)
        except (AttributeError, TypeError):
            pass
    nt = m.node_tree
    nt.nodes.clear()
    b = NB(nt)
    out = b.node("ShaderNodeOutputMaterial")
    tc = b.node("ShaderNodeTexCoord")
    nz = b.node("ShaderNodeTexNoise", noise_dimensions="4D")
    b.link(tc.outputs["Object"], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = noise_scale
    nz.inputs["Detail"].default_value = 2.0
    nz.inputs["Roughness"].default_value = 0.6
    nz.inputs["Distortion"].default_value = 0.6
    w = nz.inputs["W"]
    _interp("LINEAR")
    w.default_value = 0.0
    w.keyframe_insert("default_value", frame=1)
    w.default_value = 3.0 * noise_speed
    w.keyframe_insert("default_value", frame=N)
    mr = b.node("ShaderNodeMapRange", clamp=True)
    b.link(nz.outputs["Fac"], _sock(mr.inputs, "Value", "VALUE"))
    _sock(mr.inputs, "From Min", "VALUE").default_value = 0.32
    _sock(mr.inputs, "From Max", "VALUE").default_value = 0.68
    nr = _sock(mr.outputs, "Result", "VALUE")

    lw = b.node("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    facing = lw.outputs["Facing"]
    if rim_invert:
        facing = b.math("SUBTRACT", 1.0, facing)
    rim = b.math("POWER", facing, rim_pow)

    uvt = 0.0
    if uv_mode:
        sep = b.node("ShaderNodeSeparateXYZ")
        b.link(tc.outputs["UV"], sep.inputs[0])
        v = sep.outputs["Y"]
        if uv_mode == "center":
            v = b.math("SUBTRACT", 1.0, b.math("ABSOLUTE", b.math("SUBTRACT", b.math("MULTIPLY", v, 2.0), 1.0)))
        uvt = b.math("POWER", v, uv_pow)

    def lin(c, kr, ku, kn):
        acc = c
        if kr:
            acc = b.math("ADD", acc, b.math("MULTIPLY", rim, kr))
        if ku and uv_mode:
            acc = b.math("ADD", acc, b.math("MULTIPLY", uvt, ku))
        if kn:
            acc = b.math("ADD", acc, b.math("MULTIPLY", nr, kn))
        if not isinstance(acc, bpy.types.NodeSocket):
            acc = b.math("ADD", acc, 0.0)
        return b.math("ADD", acc, 0.0, clamp=True)

    energy = lin(e_const, e_rim, e_uv, e_noise)
    cr = b.node("ShaderNodeValToRGB")
    els = cr.color_ramp.elements
    els[0].position, els[0].color = ramp[0]
    els[1].position, els[1].color = ramp[-1]
    for pos, col in ramp[1:-1]:
        e = els.new(pos)
        e.color = col
    b.link(energy, cr.inputs["Fac"])

    if obj_attrs:
        def attr(n):
            a = b.node("ShaderNodeAttribute", attribute_type="OBJECT", attribute_name=n)
            return a.outputs["Fac"]
        A, E, D = attr("vfx_alpha"), attr("vfx_emit"), attr("vfx_dissolve")
    else:
        A, E, D = 1.0, 1.0, 0.0

    strength = b.math("MULTIPLY", b.math("MULTIPLY", b.math("ADD", energy, 0.35), emit), E)
    em = b.node("ShaderNodeEmission")
    b.link(cr.outputs["Color"], em.inputs["Color"])
    b.link(strength, em.inputs["Strength"])

    alpha = lin(a_const, a_rim, a_uv, 0.0)
    alpha = b.math("MULTIPLY", alpha, b.math("ADD", 1.0 - breakup, b.math("MULTIPLY", nr, breakup)))
    dm = b.math("MULTIPLY", b.math("SUBTRACT", b.math("ADD", nr, 0.15), b.math("MULTIPLY", D, 1.3)), 8.0, clamp=True)
    alpha = b.math("MULTIPLY", b.math("MULTIPLY", alpha, dm), A, clamp=True)

    tr = b.node("ShaderNodeBsdfTransparent")
    mix = b.node("ShaderNodeMixShader")
    b.link(alpha, mix.inputs[0])
    b.link(tr.outputs[0], mix.inputs[1])
    b.link(em.outputs[0], mix.inputs[2])
    b.link(mix.outputs[0], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ meshes ---
def bm_to_mesh(name, bm, smooth=False, mat=None):
    for f in bm.faces:
        f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if mat:
        me.materials.append(mat)
    return me


def ico_mesh(name, subdiv, radius, mat, smooth=False):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    return bm_to_mesh(name, bm, smooth, mat)


def add_quad(bm, uv, pts, uvs):
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs)
    for loop, t in zip(f.loops, uvs):
        loop[uv].uv = t
    return f


def arc_band(bm, uv, r_in, r_out, a0, a1, seg, jag=0.0, r_rng=None):
    """Annular band in XY. UV: u along arc, v 0 inner -> 1 outer."""
    r_rng = r_rng or rng
    prev = None
    for i in range(seg + 1):
        t = i / seg
        a = a0 + (a1 - a0) * t
        ro = r_out + (r_rng.uniform(-jag, jag * 2.2) if jag and 0 < i < seg else 0.0)
        cur = ((r_in * math.cos(a), r_in * math.sin(a), 0), (ro * math.cos(a), ro * math.sin(a), 0), t)
        if prev:
            add_quad(bm, uv, [prev[0], cur[0], cur[1], prev[1]],
                     [(prev[2], 0), (cur[2], 0), (cur[2], 1), (prev[2], 1)])
        prev = cur


def stroke(bm, uv, p0, p1, w):
    p0, p1 = Vector((*p0, 0)), Vector((*p1, 0))
    d = (p1 - p0).normalized()
    n = Vector((-d.y, d.x, 0)) * (w / 2)
    add_quad(bm, uv, [p0 - n, p1 - n, p1 + n, p0 + n], [(0, 0), (1, 0), (1, 1), (0, 1)])


def diamond(bm, uv, c, rx, ry):
    cx, cy = c
    add_quad(bm, uv, [(cx - rx, cy, 0), (cx, cy - ry, 0), (cx + rx, cy, 0), (cx, cy + ry, 0)],
             [(0, 0), (0.5, 0.5), (1, 1), (0.5, 0.5)])


def piece_mesh(name, build, mat):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    build(bm, uv)
    cen = Vector()
    for v in bm.verts:
        cen += v.co
    cen /= max(1, len(bm.verts))
    return bm_to_mesh(name, bm, False, mat), cen


def rune_strokes(bm, uv, cx, cy, size, r):
    """Abstract angular glyph: 2-4 strokes on a 45-degree lattice. Never letters."""
    pts = [(cx + size * math.cos(a), cy + size * math.sin(a)) for a in
           [r.choice(range(8)) * math.pi / 4 + r.uniform(-0.15, 0.15) for _ in range(4)]]
    pts.insert(r.randrange(4), (cx + r.uniform(-.2, .2) * size, cy + r.uniform(-.2, .2) * size))
    for i in range(r.randint(2, 4)):
        stroke(bm, uv, pts[i], pts[i + 1], size * 0.22)
    diamond(bm, uv, (cx + r.uniform(-.5, .5) * size, cy + r.uniform(-.5, .5) * size), size * .22, size * .32)


def link_mesh(mat):
    """Low-poly elongated chain link (long axis = Y)."""
    bm = bmesh.new()
    U, V, R, r, sy = 10, 4, 0.11, 0.028, 1.65
    ring = []
    for i in range(U):
        a = 2 * math.pi * i / U
        row = []
        for j in range(V):
            bb = 2 * math.pi * j / V + math.pi / 4
            rr = R + r * math.cos(bb)
            row.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a) * sy, r * math.sin(bb))))
        ring.append(row)
    for i in range(U):
        for j in range(V):
            bm.faces.new([ring[i][j], ring[(i + 1) % U][j], ring[(i + 1) % U][(j + 1) % V], ring[i][(j + 1) % V]])
    return bm_to_mesh("VFX_ChainLink", bm, False, mat)


def spike_mesh(name, mat, r, segs=4, width=0.13):
    """Jagged crystal spike along +Z (origin at base). UV v = 0 base -> 1 tip."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rows = []
    for i in range(segs):
        t = i / segs
        w = width * (1 - t) ** 0.8
        off = Vector((r.uniform(-.09, .09), r.uniform(-.09, .09), 0)) if i else Vector()
        c = off + Vector((0, 0, t))
        rows.append(([bm.verts.new(c + Vector((math.cos(a) * w, math.sin(a) * w * 0.55, 0)))
                      for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2)], t))
    tip = bm.verts.new((r.uniform(-.05, .05), r.uniform(-.05, .05), 1.0))
    for (ra, ta), (rb, tb) in zip(rows, rows[1:]):
        for k in range(4):
            f = bm.faces.new([ra[k], ra[(k + 1) % 4], rb[(k + 1) % 4], rb[k]])
            for lp, t in zip(f.loops, [(0, ta), (1, ta), (1, tb), (0, tb)]):
                lp[uv].uv = t
    last, tl = rows[-1]
    for k in range(4):
        f = bm.faces.new([last[k], last[(k + 1) % 4], tip])
        for lp, t in zip(f.loops, [(0, tl), (1, tl), (0.5, 1)]):
            lp[uv].uv = t
    bm.faces.new(list(reversed(rows[0][0])))
    return bm_to_mesh(name, bm, False, mat)


# ------------------------------------------------------- geometry nodes -----
def shard_cloud_group():
    """Reusable GN particle cloud: N jagged shards scattered in a spherical shell.
    Inputs are modifier sockets, so Radius / Shard Size are keyframed per object."""
    ng = bpy.data.node_groups.new("VFX_ShardCloud", "GeometryNodeTree")
    it = ng.interface
    it.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    spec = [("Count", "NodeSocketInt", 64), ("Radius", "NodeSocketFloat", 1.0),
            ("Thickness", "NodeSocketFloat", 0.3), ("Flatten", "NodeSocketFloat", 1.0),
            ("Lift", "NodeSocketFloat", 0.0), ("Shard Size", "NodeSocketFloat", 0.05),
            ("Seed", "NodeSocketInt", 0)]
    for nm, t, d in spec:
        s = it.new_socket(nm, in_out="INPUT", socket_type=t)
        if d is not None:
            s.default_value = d
    N_ = ng.nodes
    L = ng.links.new
    gi, go = N_.new("NodeGroupInput"), N_.new("NodeGroupOutput")

    def rnd(dtype, lo, hi, seed_off):
        n = N_.new("FunctionNodeRandomValue")
        n.data_type = dtype
        typ = "VECTOR" if dtype == "FLOAT_VECTOR" else "VALUE"
        _sock(n.inputs, "Min", typ).default_value = lo
        _sock(n.inputs, "Max", typ).default_value = hi
        add = N_.new("ShaderNodeMath")
        add.operation = "ADD"
        L(gi.outputs["Seed"], add.inputs[0])
        add.inputs[1].default_value = seed_off
        L(add.outputs[0], _sock(n.inputs, "Seed"))
        return _sock(n.outputs, "Value", typ)

    def vmath(op, a, b=None, scale=None):
        n = N_.new("ShaderNodeVectorMath")
        n.operation = op
        L(a, n.inputs[0])
        if b is not None:
            L(b, n.inputs[1])
        if scale is not None:
            L(scale, _sock(n.inputs, "Scale"))
        return n.outputs["Vector"]

    def fmath(op, a, b):
        n = N_.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                L(v, n.inputs[i])
            else:
                n.inputs[i].default_value = v
        return n.outputs[0]

    dirv = vmath("NORMALIZE", rnd("FLOAT_VECTOR", (-1, -1, -1), (1, 1, 1), 0))
    rr = rnd("FLOAT", 0.0, 1.0, 1)
    radius = fmath("MULTIPLY", gi.outputs["Radius"],
                   fmath("SUBTRACT", 1.0, fmath("MULTIPLY", gi.outputs["Thickness"], rr)))
    pos = vmath("SCALE", dirv, scale=radius)
    flat = N_.new("ShaderNodeCombineXYZ")
    flat.inputs[0].default_value = 1.0
    flat.inputs[1].default_value = 1.0
    L(gi.outputs["Flatten"], flat.inputs[2])
    pos = vmath("MULTIPLY", pos, flat.outputs[0])
    lift = N_.new("ShaderNodeCombineXYZ")
    L(fmath("MULTIPLY", gi.outputs["Lift"], rnd("FLOAT", 0.2, 1.0, 4)), lift.inputs[2])
    pos = vmath("ADD", pos, lift.outputs[0])

    pts = N_.new("GeometryNodePoints")
    L(gi.outputs["Count"], pts.inputs["Count"])
    L(pos, pts.inputs["Position"])

    cone = N_.new("GeometryNodeMeshCone")
    cone.inputs["Vertices"].default_value = 3
    cone.inputs["Radius Top"].default_value = 0.0
    cone.inputs["Radius Bottom"].default_value = 0.35
    cone.inputs["Depth"].default_value = 1.8

    inst = N_.new("GeometryNodeInstanceOnPoints")
    L(pts.outputs["Points"], inst.inputs["Points"])
    L(cone.outputs["Mesh"], inst.inputs["Instance"])  # material comes from the object's slot
    rot = rnd("FLOAT_VECTOR", (0, 0, 0), (6.283, 6.283, 6.283), 2)
    try:
        e2r = N_.new("FunctionNodeEulerToRotation")
        L(rot, e2r.inputs[0])
        L(e2r.outputs[0], inst.inputs["Rotation"])
    except RuntimeError:
        L(rot, inst.inputs["Rotation"])
    L(fmath("MULTIPLY", gi.outputs["Shard Size"], rnd("FLOAT", 0.45, 1.5, 3)), inst.inputs["Scale"])
    L(inst.outputs["Instances"], go.inputs["Geometry"])
    return ng


def shard_cloud(name, ng, c, parent, loc, mat, count, seed, thickness=0.3, flatten=1.0, lift=0.0):
    base = bpy.data.meshes.new(name + "_base")
    base.materials.append(mat)
    o = new_obj(name, base, c, parent, loc)
    md = o.modifiers.new("ShardCloud", "NODES")
    md.node_group = ng
    ids = {i.name: i.identifier for i in ng.interface.items_tree
           if i.item_type == "SOCKET" and i.in_out == "INPUT"}
    for k, v in (("Count", count), ("Seed", seed), ("Thickness", thickness), ("Flatten", flatten),
                 ("Lift", lift), ("Shard Size", 0.0)):
        set_mod_input(md, ids[k], v)
    o["gn_inputs"] = json.dumps(ids)
    return o, ids


# ================================================================== BUILD ===
def build():
    reset_scene()
    scn = bpy.context.scene
    scn.name = "OathbreakerVerdict"
    root_c = coll("VFX_OathbreakerVerdict", scn.collection)
    C = {n: coll(f"VFX_{n}", root_c) for n in
         ("Core", "Ribbons", "Chains", "Symbols", "Shockwaves", "Spikes", "Particles")}
    cam_c = coll("VFX_Camera", scn.collection)
    help_c = coll("VFX_Helpers", scn.collection)
    help_c.hide_render = True

    ROOT = new_obj("VFX_OathbreakerVerdict_Root", None, root_c)   # move this to reposition
    ROOT.empty_display_type = "ARROWS"
    CORE_P = new_obj("Core_Pivot", None, C["Core"], ROOT, (0, 0, H))

    # ---------------- materials (modular, shared) ----------------
    M = dict(
        core_shell=mk_mat("M_Core_Shell", R_MIX, emit=2.2, a_const=0.06, a_rim=0.95, e_const=0.15,
                          e_rim=0.85, e_noise=0.35, rim_pow=1.6, breakup=0.35, noise_scale=2.5, noise_speed=2.0),
        core_inner=mk_mat("M_Core_Inner", R_DARK, emit=0.9, a_const=0.42, a_rim=0.5, e_const=0.1,
                          e_rim=0.8, e_noise=0.25, rim_pow=2.5, breakup=0.25, noise_scale=4.0, noise_speed=1.5),
        core_halo=mk_mat("M_Core_Halo", R_CRIMSON, emit=1.1, a_const=0.0, a_rim=0.26, e_const=0.35,
                         e_rim=0.35, e_noise=0.15, rim_pow=2.2, rim_invert=True, breakup=0.2, noise_scale=1.5),
        ribbon_c=mk_mat("M_Ribbon_Crimson", R_CRIMSON, emit=1.7, a_const=0.35, a_rim=0.65, e_const=0.35,
                        e_rim=0.6, e_noise=0.35, rim_pow=1.2, breakup=0.55, noise_scale=3.5, noise_speed=2.5),
        ribbon_v=mk_mat("M_Ribbon_Violet", R_VIOLET, emit=1.5, a_const=0.35, a_rim=0.65, e_const=0.35,
                        e_rim=0.6, e_noise=0.35, rim_pow=1.2, breakup=0.55, noise_scale=3.5, noise_speed=2.5),
        chain=mk_mat("M_Chain_SpectralIron", R_CHAIN, emit=1.6, a_const=0.8, a_rim=0.2, e_const=0.12,
                     e_rim=0.95, e_noise=0.2, rim_pow=1.8, breakup=0.1, noise_scale=6.0),
        ember=mk_mat("M_Chain_BreakGlow", R_CRIMSON, emit=3.0, a_const=0.75, a_rim=0.25, e_const=0.6,
                     e_rim=0.4, e_noise=0.2, breakup=0.2),
        sigil_c=mk_mat("M_Sigil_Crimson", R_CRIMSON, emit=1.5, a_const=0.35, a_uv=0.6, e_const=0.3,
                       e_rim=0.0, e_uv=0.5, e_noise=0.25, uv_mode="center", uv_pow=0.6, breakup=0.3),
        sigil_v=mk_mat("M_Sigil_Violet", R_VIOLET, emit=1.5, a_const=0.3, a_uv=0.6, e_const=0.3,
                       e_rim=0.0, e_uv=0.5, e_noise=0.25, uv_mode="center", uv_pow=0.6, breakup=0.3),
        wave_c=mk_mat("M_Shockwave_Crimson", R_WAVE_C, emit=2.0, a_const=0.0, a_uv=1.0, e_const=0.3,
                      e_rim=0.0, e_uv=0.7, e_noise=0.2, uv_mode="v", uv_pow=3.0, breakup=0.45, noise_scale=2.0),
        wave_v=mk_mat("M_Shockwave_Violet", R_WAVE_V, emit=1.9, a_const=0.0, a_uv=1.0, e_const=0.3,
                      e_rim=0.0, e_uv=0.7, e_noise=0.2, uv_mode="v", uv_pow=3.0, breakup=0.45, noise_scale=2.0),
        burst=mk_mat("M_Burst_Shell", R_MIX, emit=1.9, a_const=0.0, a_rim=0.85, e_const=0.25, e_rim=0.75,
                     e_noise=0.3, rim_pow=2.4, breakup=0.5, noise_scale=2.2, noise_speed=3.0),
        spike=mk_mat("M_Spike", R_MIX, emit=1.9, a_const=0.8, a_rim=0.45, a_uv=0.0, e_const=0.45,
                     e_rim=0.55, e_uv=0.0, e_noise=0.15, rim_pow=1.4, breakup=0.25, noise_scale=5.0),
        shard_c=mk_mat("M_Shard_Crimson", R_CRIMSON, emit=2.6, a_const=0.9, e_const=0.55, e_rim=0.45,
                       e_noise=0.1, breakup=0.0, obj_attrs=False),
        shard_v=mk_mat("M_Shard_Violet", R_VIOLET, emit=2.4, a_const=0.85, e_const=0.5, e_rim=0.45,
                       e_noise=0.1, breakup=0.0, obj_attrs=False),
    )
    ng = shard_cloud_group()

    # =============================== 1. CORE AURA ===========================
    jag_drv = new_obj("Core_JagTexture_Driver", None, help_c, CORE_P)
    keys(jag_drv, "rotation_euler", [(0, (0, 0, 0)), (1, (2.1, 1.3, 3.4))], "LINEAR")
    keys(jag_drv, "location", [(0, (0, 0, 0)), (1, (0.4, -0.3, 1.2))], "LINEAR")
    tex = bpy.data.textures.new("VFX_CoreJag", "VORONOI")
    tex.noise_scale = 0.32
    shell = new_obj("Core_Shell", ico_mesh("Core_Shell", 3, 0.62, M["core_shell"]), C["Core"], CORE_P)
    d = shell.modifiers.new("Jagged", "DISPLACE")
    d.texture, d.strength, d.mid_level = tex, 0.32, 0.55
    d.texture_coords, d.texture_coords_object = "OBJECT", jag_drv
    inner = new_obj("Core_Inner", ico_mesh("Core_Inner", 1, 0.34, M["core_inner"]), C["Core"], CORE_P)
    halo = new_obj("Core_Halo", ico_mesh("Core_Halo", 3, 1.15, M["core_halo"], smooth=True), C["Core"], CORE_P)
    keys(shell, "rotation_euler", [(0, (0, 0, 0)), (1, (0.6, -0.4, 4 * math.pi))], "LINEAR")
    keys(inner, "rotation_euler", [(0, (0, 0, 0)), (1, (-1.2, 0.8, -6 * math.pi))], "LINEAR")
    keys(CORE_P, "scale", [(p, (s, s, s)) for p, s in
                           [(0, 0), (0.025, 0.24), (0.05, 0.17), (0.085, 0.27), (0.12, 0.2), (0.15, 0.3),
                            (0.25, 0.5), (0.35, 0.72), (0.40, 0.52), (0.47, 1.25), (0.58, 1.5), (0.66, 1.32),
                            (0.75, 1.0), (0.85, 0.72), (0.95, 0.25), (1.0, 0.0)]])
    core_emit = [(0, 0), (0.03, 1.3), (0.06, 1.7), (0.09, 1.0), (0.12, 1.7), (0.15, 1.1), (0.35, 2.0),
                 (0.40, 2.5), (0.47, 3.2), (0.6, 3.8), (0.7, 2.2), (0.85, 1.3), (0.97, 0.4), (1.0, 0)]
    for o, a in ((shell, 1.0), (inner, 0.9), (halo, 1.0)):
        props(o, alpha=[(0, 0), (0.02, a), (0.93, a * 0.9), (1.0, 0)], emit=core_emit,
              dissolve=[(0.88, 0), (1.0, 0.7)])

    # gathering fragments (phase 1-2), orbiting fragments (whole effect)
    gather, gi = shard_cloud("Core_GatherFragments", ng, C["Particles"], ROOT, (0, 0, H), M["shard_c"],
                             70, 11, thickness=0.25, flatten=0.75)
    key_mod(gather, "ShardCloud", gi["Radius"], [(0, 2.7), (0.15, 1.7), (0.36, 0.4)])
    key_mod(gather, "ShardCloud", gi["Shard Size"], [(0, 0), (0.03, 0.03), (0.3, 0.05), (0.40, 0.0)])
    keys(gather, "rotation_euler", [(0, (0, 0, 0)), (0.42, (0, 0, -3 * math.pi))], "LINEAR")
    orbit, oi = shard_cloud("Core_OrbitFragments", ng, C["Particles"], ROOT, (0, 0, H), M["shard_v"],
                            40, 23, thickness=0.35, flatten=0.5)
    key_mod(orbit, "ShardCloud", oi["Radius"], [(0.08, 0.7), (0.35, 0.95), (0.40, 0.8), (0.5, 1.75),
                                                (0.65, 2.05), (0.85, 1.6), (1.0, 1.2)])
    key_mod(orbit, "ShardCloud", oi["Shard Size"], [(0.08, 0), (0.15, 0.06), (0.5, 0.08), (0.85, 0.06), (0.97, 0)])
    keys(orbit, "rotation_euler", [(0, (0, 0, 0)), (1, (0, 0, 5 * math.pi))], "LINEAR")

    # =============================== 2. ENERGY RIBBONS ======================
    prof = bpy.data.curves.new("VFX_RibbonProfile", "CURVE")
    sp = prof.splines.new("POLY")
    sp.points.add(3)
    for p_, co in zip(sp.points, [(-0.13, 0), (0, 0.02), (0.13, 0), (0, -0.02)]):
        p_.co = (*co, 0, 1)
    sp.use_cyclic_u = True
    prof_o = new_obj("RibbonProfile", prof, help_c)
    tap = bpy.data.curves.new("VFX_RibbonTaper", "CURVE")
    sp = tap.splines.new("POLY")
    sp.points.add(4)
    for p_, co in zip(sp.points, [(0, 0.05), (0.12, 1.0), (0.55, 0.85), (0.85, 0.6), (1.0, 0.0)]):
        p_.co = (*co, 0, 1)
    tap_o = new_obj("RibbonTaper", tap, help_c)

    for i in range(6):
        r = random.Random(SEED + 100 + i)
        sgn = 1 if i % 2 == 0 else -1
        a0 = i * math.pi / 3 + r.uniform(-0.2, 0.2)
        piv = new_obj(f"Ribbon_{i:02d}_Pivot", None, C["Ribbons"], ROOT)
        cu = bpy.data.curves.new(f"Ribbon_{i:02d}", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_mode, cu.bevel_object, cu.taper_object = "OBJECT", prof_o, tap_o
        cu.use_fill_caps = True
        cu.twist_mode = "MINIMUM"
        cu.resolution_u = 1
        s = cu.splines.new("POLY")
        n = 11
        s.points.add(n - 1)
        turns = r.uniform(0.55, 0.85)
        for k, pt in enumerate(s.points):
            t = k / (n - 1)
            ang = sgn * t * turns * 2 * math.pi + (r.uniform(-0.12, 0.12) if 0 < k < n - 1 else 0)
            rad = 0.72 + 0.6 * t + (r.uniform(-0.12, 0.12) if k % 2 else 0)
            z = 0.05 + 2.65 * t ** 0.9 + r.uniform(-0.06, 0.06)
            pt.co = (rad * math.cos(ang), rad * math.sin(ang), z, 1)
        cu.materials.append(M["ribbon_c"] if i % 2 == 0 else M["ribbon_v"])
        rb = new_obj(f"Ribbon_{i:02d}", cu, C["Ribbons"], piv)
        rb.scale = (1, 1, r.uniform(0.85, 1.1))
        rot = lambda tw: (0, 0, a0 + sgn * tw * math.pi)
        keys(piv, "rotation_euler", [(0.1, rot(0)), (0.35, rot(1.2)), (0.55, rot(3.3)), (0.7, rot(4.1)),
                                     (0.85, rot(4.7)), (1.0, rot(5.1))])
        keys(piv, "scale", [(0.15, (0.6, 0.6, 0.5)), (0.35, (1, 1, 1)), (0.40, (0.88, 0.88, 0.95)),
                            (0.5, (1.45, 1.45, 1.4)), (0.62, (1.6, 1.6, 1.5)), (0.78, (1.3, 1.3, 1.1)),
                            (0.92, (1.1, 1.1, 0.8))])
        st = 0.02 * i
        keys(cu, "bevel_factor_end", [(0.15 + st * 0.5, 0.0), (0.33 + st * 0.3, 1.0)])
        keys(cu, "bevel_factor_start", [(0.68, 0.0), (0.86, 0.85)])
        props(rb, alpha=[(0.15, 0), (0.2, 0.9), (0.45, 1.0), (0.55, 0.7), (0.72, 0.75), (0.86, 0.0)],
              emit=[(0.15, 1.0), (0.35, 1.6), (0.47, 2.3), (0.6, 2.4), (0.72, 1.5), (0.86, 0.8)],
              dissolve=[(0.66, 0.0), (0.84, 0.9)])

    # =============================== 3. BROKEN SPECTRAL CHAINS ===============
    lme = link_mesh(M["chain"])
    gme = spike_mesh("VFX_ChainBreakGlow", M["ember"], random.Random(5), segs=2, width=0.11)
    chains = [  # radius, height, tilt x/y (deg), segments (deg), spin dir, breaks?
        (1.35, 1.25, 18, -10, [(0, 95), (122, 192)], 1, True),
        (1.62, 0.80, -22, 15, [(196, 278), (300, 352)], -1, True),
        (1.18, 1.65, 58, 24, [(28, 118), (140, 172)], 1, True),
        (1.95, 1.10, 8, 12, [(8, 148), (170, 250)], -1, False),
    ]
    for ci, (R, h, tx, ty, segs, sd, breaks) in enumerate(chains):
        r = random.Random(SEED + 300 + ci)
        tilt = new_obj(f"Chain_{ci:02d}_Tilt", None, C["Chains"], ROOT, (0, 0, h))
        tilt.rotation_euler = (math.radians(tx), math.radians(ty), 0)
        spin = new_obj(f"Chain_{ci:02d}_Spin", None, C["Chains"], tilt)
        a0 = r.uniform(0, 2 * math.pi)
        pa = 0.03 + 0.025 * ci                        # materialize time
        pb = 0.40 + 0.016 * ci                        # break time
        spins = [(pa, 0), (0.35, 0.9), (0.45, 1.45), (0.8, 1.9)] if breaks else \
                [(pa, 0), (0.35, 0.9), (0.55, 1.9), (0.85, 2.6), (1.0, 3.0)]
        keys(spin, "rotation_euler", [(p, (0, 0, a0 + sd * v * math.pi)) for p, v in spins])
        keys(spin, "scale", [(pa, (0.35,) * 3), (pa + 0.09, (1,) * 3)])
        # vibration while charging (deterministic jitter)
        f0, f1 = int(F(0.2)), int(F(pb if breaks else 0.5))
        _interp("BEZIER")
        for f in range(f0, f1 + 1, 2):
            amp = 0.055 * (f - f0) / max(1, f1 - f0)
            spin.location = (r.uniform(-amp, amp), r.uniform(-amp, amp), r.uniform(-amp, amp))
            spin.keyframe_insert("location", frame=f)
        spin.location = (0, 0, 0)
        spin.keyframe_insert("location", frame=f1 + 2)

        objs = []
        step = 0.27 / R
        for sa, sb in segs:
            a, k = math.radians(sa), 0
            ends = []
            while a <= math.radians(sb):
                pos = Vector((R * math.cos(a), R * math.sin(a), 0))
                tan = Vector((-math.sin(a), math.cos(a), 0))
                up = Vector((0, 0, 1)) if k % 2 == 0 else pos.normalized()
                x = tan.cross(up)
                mat3 = Matrix((x, tan, up)).transposed()
                o = new_obj(f"Chain_{ci:02d}_Link_{len(objs):02d}", lme, C["Chains"], spin, pos)
                o.rotation_euler = mat3.to_euler()
                objs.append(o)
                ends.append((pos, tan))
                a += step
                k += 1
            for (pos, tan), sgn_ in ((ends[0], -1), (ends[-1], 1)):  # glowing broken ends
                g = new_obj(f"Chain_{ci:02d}_BreakGlow_{len(objs):02d}", gme, C["Chains"], spin,
                            pos + tan * sgn_ * 0.13)
                g.rotation_euler = (tan * sgn_).to_track_quat("Z", "Y").to_euler()
                g.scale = (1.4, 1.4, 0.32)
                g["is_glow"] = True
                objs.append(g)

        for o in objs:
            glow = o.get("is_glow", False)
            rest_l, rest_r = o.location.copy(), o.rotation_euler.copy()
            if breaks:
                out = Vector((rest_l.x, rest_l.y, 0)).normalized()
                out = (out + Vector((r.uniform(-.3, .3), r.uniform(-.3, .3), r.uniform(-.2, .6)))).normalized()
                dist = r.uniform(1.5, 2.9)
                tb = pb + r.uniform(-0.01, 0.015)
                keys(o, "location", [(tb, rest_l), (tb + 0.06, rest_l + out * dist * 0.5),
                                     (0.62, rest_l + out * dist * 0.82), (0.84, rest_l + out * dist)])
                tumble = Vector((r.uniform(-4, 4), r.uniform(-4, 4), r.uniform(-4, 4)))
                keys(o, "rotation_euler", [(tb, rest_r), (0.84, Vector(rest_r) + tumble)])
                props(o, alpha=[(pa, 0), (pa + 0.07, 1), (0.82, 0.8), (0.86, 0)],
                      emit=[(pa, 0.8 if not glow else 1.5), (0.35, 1.5 if not glow else 2.5),
                            (tb - 0.01, 2.0 if not glow else 3.0), (tb + 0.012, 4.2), (0.6, 1.8), (0.82, 0.3)],
                      dissolve=[(pa, 0.8), (pa + 0.08, 0), (0.7, 0), (0.85, 1.0)])
            else:
                props(o, alpha=[(pa, 0), (pa + 0.07, 1), (0.88, 0.9), (0.95, 0)],
                      emit=[(pa, 0.8), (0.35, 1.5), (0.5, 2.4), (0.6, 2.0), (0.8, 0.6), (0.94, 0.0)],
                      dissolve=[(pa, 0.8), (pa + 0.08, 0), (0.78, 0), (0.95, 1.0)])

    # =============================== 4. CORRUPTED OATH SYMBOLS ===============
    def sigil_pieces(prefix, parent, builders, mat, c, drift, pa, pd, flare, base_emit=1.0):
        for j, bld in enumerate(builders):
            me, cen = piece_mesh(f"{prefix}_Piece_{j:02d}", bld, mat)
            o = new_obj(f"{prefix}_Piece_{j:02d}", me, c, parent)
            r = random.Random(hash((prefix, j)) & 0xFFFF)
            dirv = Vector((cen.x, cen.y, 0))
            dirv = dirv.normalized() if dirv.length > 1e-4 else Vector((1, 0, 0))
            keys(o, "location", [(pd, (0, 0, 0)), (pd + 0.13, dirv * drift * r.uniform(0.7, 1.3))])
            keys(o, "rotation_euler", [(pd, (0, 0, 0)), (pd + 0.13, (0, 0, r.uniform(-0.5, 0.5)))])
            pulse = [(pa + 0.04 * q, base_emit * (1.5 if q % 2 else 1.0)) for q in range(int((0.40 - pa) / 0.04))]
            props(o, alpha=[(pa, 0), (pa + 0.03, 0.9), (pd + 0.13, 0.85), (pd + 0.15, 0)],
                  emit=[(pa, base_emit)] + pulse + [(flare - 0.03, base_emit * 1.2), (flare, 3.4 * base_emit),
                                                     (flare + 0.07, 1.6 * base_emit), (0.7, base_emit)],
                  dissolve=[(pa, 1.0), (pa + 0.09, 0.0), (pd, 0.0), (pd + 0.14, 1.0)])

    # ground sigil (fractured circle beneath the character)
    gs = new_obj("Sigil_Ground", None, C["Symbols"], ROOT, (0, 0, 0.03))
    keys(gs, "rotation_euler", [(0, (0, 0, 0)), (1, (0, 0, -0.7 * math.pi))], "LINEAR")
    keys(gs, "scale", [(0.18, (0.6,) * 3), (0.33, (1,) * 3), (0.40, (0.95,) * 3), (0.47, (1.12,) * 3),
                       (0.6, (1.16,) * 3), (0.86, (1.28,) * 3)])
    gr = random.Random(SEED + 500)
    bl = []
    cuts = sorted(gr.uniform(0, 2 * math.pi) for _ in range(6))
    for k in range(6):
        a0_, a1_ = cuts[k] + 0.09, (cuts[(k + 1) % 6] + (2 * math.pi if k == 5 else 0)) - 0.09
        bl.append(lambda bm, uv, a0_=a0_, a1_=a1_: arc_band(bm, uv, 2.12, 2.24, a0_, a1_, 24, jag=0.03,
                                                            r_rng=random.Random(int(a0_ * 1000))))
    for k in range(4):
        a0_ = k * math.pi / 2 + 0.25
        bl.append(lambda bm, uv, a0_=a0_: arc_band(bm, uv, 1.55, 1.61, a0_, a0_ + 1.15, 14))
    for k in range(7):
        ang = 2 * math.pi * k / 7 + 0.2
        rr_ = random.Random(SEED + 600 + k)
        bl.append(lambda bm, uv, ang=ang, rr_=rr_: rune_strokes(bm, uv, 1.88 * math.cos(ang), 1.88 * math.sin(ang), 0.14, rr_))
    tri = [(1.5 * math.cos(a), 1.5 * math.sin(a)) for a in (math.pi / 2, math.pi * 7 / 6, math.pi * 11 / 6)]
    for k in range(3):
        p0, p1 = Vector(tri[k]), Vector(tri[(k + 1) % 3])
        m1, m2 = p0.lerp(p1, 0.44), p0.lerp(p1, 0.56)
        bl.append(lambda bm, uv, p0=p0, m1=m1, m2=m2, p1=p1: (stroke(bm, uv, p0, m1, 0.05), stroke(bm, uv, m2, p1, 0.05)))
    sigil_pieces("Sigil_Ground", gs, bl, M["sigil_v"], C["Symbols"], 0.5, 0.18, 0.72, 0.44, 0.9)

    cam = None  # created below; floating sigils track it

    # =============================== 5. ENERGY EXPLOSION ====================
    def ring_mesh(name, mat, seed):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        arc_band(bm, uv, 0.87, 1.0, 0, 2 * math.pi, 80, jag=0.035, r_rng=random.Random(seed))
        return bm_to_mesh(name, bm, False, mat)

    sw1 = new_obj("Shockwave_Ground_A", ring_mesh("Shockwave_Ground_A", M["wave_c"], 1), C["Shockwaves"], ROOT, (0, 0, 0.06))
    keys(sw1, "scale", [(0.40, (0.15,) * 3), (0.52, (2.6,) * 3), (0.62, (3.95,) * 3), (0.72, (4.25,) * 3)])
    keys(sw1, "rotation_euler", [(0.4, (0, 0, 0)), (0.72, (0, 0, 0.8))], "LINEAR")
    props(sw1, alpha=[(0.40, 0), (0.41, 1), (0.6, 0.9), (0.72, 0)], emit=[(0.41, 3.8), (0.62, 2.4), (0.72, 1.2)],
          dissolve=[(0.55, 0), (0.72, 0.8)])
    sw2 = new_obj("Shockwave_Ground_B", ring_mesh("Shockwave_Ground_B", M["wave_v"], 2), C["Shockwaves"], ROOT, (0, 0, 0.08))
    keys(sw2, "scale", [(0.47, (0.15,) * 3), (0.6, (2.4,) * 3), (0.7, (3.3,) * 3), (0.8, (3.6,) * 3)])
    keys(sw2, "rotation_euler", [(0.47, (0, 0, 0)), (0.8, (0, 0, -0.9))], "LINEAR")
    props(sw2, alpha=[(0.47, 0), (0.48, 1), (0.68, 0.85), (0.8, 0)], emit=[(0.48, 3.4), (0.7, 2.0), (0.8, 1.0)],
          dissolve=[(0.62, 0), (0.8, 0.85)])
    sw3 = new_obj("Shockwave_Flash", ring_mesh("Shockwave_Flash", M["wave_c"], 3), C["Shockwaves"], ROOT, (0, 0, H))
    keys(sw3, "scale", [(0.46, (0.2,) * 3), (0.54, (1.6,) * 3), (0.62, (2.5,) * 3), (0.68, (2.8,) * 3)])
    props(sw3, alpha=[(0.46, 0), (0.47, 1), (0.6, 0.7), (0.68, 0)], emit=[(0.47, 4.0), (0.6, 2.5), (0.68, 1.5)],
          dissolve=[(0.56, 0), (0.68, 0.7)])

    burst = new_obj("Burst_Shell", ico_mesh("Burst_Shell", 2, 1.0, M["burst"]), C["Shockwaves"], ROOT, (0, 0, H))
    keys(burst, "scale", [(0.44, (0.3,) * 3), (0.52, (2.0,) * 3), (0.62, (2.8,) * 3), (0.68, (3.0,) * 3)])
    keys(burst, "rotation_euler", [(0.44, (0, 0, 0)), (0.68, (0.3, 0.2, 1.2))], "LINEAR")
    props(burst, alpha=[(0.44, 0), (0.46, 0.9), (0.58, 0.5), (0.68, 0)], emit=[(0.46, 3.6), (0.62, 2.0)],
          dissolve=[(0.52, 0), (0.68, 1.0)])

    sr = random.Random(SEED + 700)
    n_sp = 22
    for j in range(n_sp):
        az = 2 * math.pi * j / n_sp + sr.uniform(-0.12, 0.12)
        el = math.radians(sr.uniform(-12, 58))
        dv = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
        length = sr.uniform(2.0, 3.3) * (1.0 if j % 2 else 0.7)
        sk = new_obj(f"Spike_{j:02d}", spike_mesh(f"Spike_{j:02d}", M["spike"], sr, width=0.17), C["Spikes"], ROOT,
                     Vector((0, 0, H)) + dv * 0.35)
        sk.rotation_euler = dv.to_track_quat("Z", "Y").to_euler()
        ps = 0.46 + sr.uniform(0, 0.045)
        w = sr.uniform(0.8, 1.3)
        keys(sk, "scale", [(ps, (0, 0, 0)), (ps + 0.05, (w, w, length * 1.08)), (ps + 0.09, (w, w, length)),
                           (0.66, (w * 0.85, w * 0.85, length * 1.05)), (0.75, (0, 0, length * 1.25))])
        props(sk, alpha=[(ps, 0), (ps + 0.01, 1), (0.68, 1), (0.75, 0)],
              emit=[(ps + 0.02, 4.4), (0.62, 3.0), (0.72, 1.5)], dissolve=[(0.63, 0), (0.75, 0.7)])

    debris_c, dc = shard_cloud("Burst_Debris_Crimson", ng, C["Particles"], ROOT, (0, 0, H), M["shard_c"],
                               90, 41, thickness=0.55, flatten=0.55, lift=0.7)
    debris_v, dv_ = shard_cloud("Burst_Debris_Violet", ng, C["Particles"], ROOT, (0, 0, H), M["shard_v"],
                                70, 57, thickness=0.6, flatten=0.6, lift=0.9)
    for o, ids, rmax, d0 in ((debris_c, dc, 4.0, 0.0), (debris_v, dv_, 3.4, 0.02)):
        key_mod(o, "ShardCloud", ids["Radius"], [(0.45 + d0, 0.3), (0.6 + d0, 3.0 * rmax / 4), (0.8, rmax),
                                                 (0.95, rmax * 1.06)])
        key_mod(o, "ShardCloud", ids["Shard Size"], [(0.45 + d0, 0), (0.5 + d0, 0.085), (0.68, 0.065), (0.9, 0.0)])
        keys(o, "rotation_euler", [(0.45, (0, 0, 0)), (1, (0, 0, 1.4 if d0 else -1.4))], "LINEAR")

    # =============================== CAMERA ==================================
    cd = bpy.data.cameras.new("VFX_IsoCam")
    cd.type, cd.ortho_scale, cd.clip_start, cd.clip_end = "ORTHO", ORTHO, 0.1, 200
    cam = new_obj("VFX_IsoCam", cd, cam_c)
    rot = Euler((math.radians(60), 0, math.radians(45)))
    cam.rotation_euler = rot
    cam.location = CAM_TARGET - (rot.to_matrix() @ Vector((0, 0, -1))) * 40
    scn.camera = cam

    def track(o):
        c = o.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = cam, "TRACK_Z", "UP_Y"

    track(sw3)

    # floating sigils (camera facing, orbiting the aura)
    for k in range(5):
        r = random.Random(SEED + 800 + k)
        th = 2 * math.pi * k / 5 + 0.5
        R_ = 2.25 + r.uniform(-0.15, 0.2)
        z = 1.0 + (k % 3) * 0.6 + r.uniform(-0.1, 0.1)
        hold = new_obj(f"Sigil_Float_{k:02d}", None, C["Symbols"], ROOT)
        track(hold)
        pa = 0.19 + 0.025 * k
        pd = 0.71 + 0.012 * k
        pos = lambda rad, dz=0.0: (rad * math.cos(th), rad * math.sin(th), z + dz)
        keys(hold, "location", [(pa, pos(R_ * 0.9, -0.15)), (0.40, pos(R_)), (0.55, pos(R_ * 1.3, 0.25)),
                                (0.85, pos(R_ * 1.42, 0.4))])
        keys(hold, "scale", [(pa, (0.5,) * 3), (pa + 0.07, (1,) * 3), (0.40, (0.9,) * 3), (0.45, (1.25,) * 3),
                             (0.52, (1.05,) * 3)])
        spin = new_obj(f"Sigil_Float_{k:02d}_Spin", None, C["Symbols"], hold)
        sd = 1 if k % 2 else -1
        keys(spin, "rotation_euler", [(pa, (0, 0, 0)), (1, (0, 0, sd * 1.6 * math.pi))], "LINEAR")
        rs = random.Random(SEED + 900 + k)
        cuts = sorted(rs.uniform(0, 2 * math.pi) for _ in range(3))
        bl = []
        for q in range(3):
            a0_, a1_ = cuts[q] + 0.18, cuts[(q + 1) % 3] + (2 * math.pi if q == 2 else 0) - 0.18
            bl.append(lambda bm, uv, a0_=a0_, a1_=a1_: arc_band(bm, uv, 0.36, 0.42, a0_, a1_, 14))
        bl.append(lambda bm, uv, rs=rs: rune_strokes(bm, uv, 0, 0, 0.2, rs))
        bl.append(lambda bm, uv: diamond(bm, uv, (0, 0), 0.05, 0.09))
        ticks = [rs.uniform(0, 2 * math.pi) for _ in range(5)]
        bl.append(lambda bm, uv, ticks=ticks: [stroke(bm, uv, (0.46 * math.cos(a), 0.46 * math.sin(a)),
                                                      (0.56 * math.cos(a), 0.56 * math.sin(a)), 0.035) for a in ticks])
        sigil_pieces(f"Sigil_Float_{k:02d}", spin, bl, M["sigil_c"] if k % 2 == 0 else M["sigil_v"],
                     C["Symbols"], 0.25, pa, pd, 0.43 + 0.01 * k, 1.0)
        motes, mi = shard_cloud(f"Sigil_Float_{k:02d}_DissolveMotes", ng, C["Particles"], hold, (0, 0, 0),
                                M["shard_c"] if k % 2 == 0 else M["shard_v"], 26, 70 + k, thickness=0.5, lift=0.9)
        key_mod(motes, "ShardCloud", mi["Radius"], [(pd, 0.2), (pd + 0.17, 0.95)])
        key_mod(motes, "ShardCloud", mi["Shard Size"], [(pd, 0), (pd + 0.04, 0.035), (pd + 0.17, 0.0)])

    # =============================== RENDER SETTINGS =========================
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scn.render.engine = eng
            break
        except TypeError:
            continue
    ee = scn.eevee
    for attr, v in (("taa_render_samples", 32), ("use_raytracing", False), ("use_shadows", False),
                    ("use_motion_blur", False), ("use_gtao", False)):
        if hasattr(ee, attr):
            setattr(ee, attr, v)
    scn.render.use_motion_blur = False
    scn.render.film_transparent = True
    scn.render.resolution_x = scn.render.resolution_y = RES
    scn.render.resolution_percentage = 100
    scn.render.fps = FPS
    scn.frame_start, scn.frame_end = 1, N
    im = scn.render.image_settings
    im.file_format, im.color_mode, im.color_depth, im.compression = "PNG", "RGBA", "8", 15
    scn.view_settings.view_transform = "Standard"
    scn.view_settings.look = "None"
    world = bpy.data.worlds.new("VFX_NoWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0, 0, 0, 1)
        bg.inputs["Strength"].default_value = 0.0
    scn.world = world
    _interp("BEZIER")
    return scn, cam


def metadata(scn, cam):
    scn.frame_set(1)
    o = world_to_camera_view(scn, cam, Vector((0, 0, 0)))
    c = world_to_camera_view(scn, cam, Vector((0, 0, H)))
    ph = {k: [round(F(a)), round(F(b))] for k, (a, b) in PHASES.items()}
    return {"skill": "Oathbreaker Verdict", "class": "OATHBREAKER", "game": "ECLIPSE ONLINE",
            "fps": FPS, "frames": N, "duration_s": N / FPS, "resolution": [RES, RES],
            "camera": {"type": "orthographic", "ortho_scale": ORTHO, "rot_x_deg": 60, "rot_z_deg": 45,
                       "pixels_per_meter": RES / ORTHO},
            "anchor_feet_px": [round(o.x * RES, 2), round((1 - o.y) * RES, 2)],
            "anchor_core_px": [round(c.x * RES, 2), round((1 - c.y) * RES, 2)],
            "phases_frames": ph, "impact_frame": round(F(0.6)), "alpha": "straight (unpremultiplied) RGBA",
            "seed": SEED}


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    scn, cam = build()
    out = os.path.join(HERE, "render")
    os.makedirs(out, exist_ok=True)
    meta = metadata(scn, cam)
    with open(os.path.join(out, "oathbreaker_verdict_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print("META", json.dumps(meta))
    if "--save" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "oathbreaker_verdict_aura.blend"))
    if "--frames" in argv:
        tdir = os.path.join(out, "test")
        os.makedirs(tdir, exist_ok=True)
        for f in [int(x) for x in argv[argv.index("--frames") + 1].split(",")]:
            scn.frame_set(f)
            scn.render.filepath = os.path.join(tdir, f"test_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
    if "--all" in argv:
        fdir = os.path.join(out, "frames")
        os.makedirs(fdir, exist_ok=True)
        scn.render.filepath = os.path.join(fdir, "oathbreaker_verdict_")
        bpy.ops.render.render(animation=True)
    print("DONE")
