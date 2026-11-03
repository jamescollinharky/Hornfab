"""MEH layout feasibility in a box envelope (research only; reference geometry for tools/cad/meh.py).

Frame (same as tools/cad/plughorn.py): CD coupling plane at z = 0, +z toward the mouth, x horizontal, y vertical,
mm. Flat-wall pyramid horn with its virtual apex at z = -z_c (z_c makes the pyramid section at z = 0 equal the CD
exit area). Cone drivers mount FACE-DOWN on the outside of a horn wall over their port: flange plane parallel to the
wall at (wall thickness + spacer) outside it, cone dish facing the port, motor pointing away from the horn. The CD
body is a cylinder behind z = 0. Checks: envelope, port fits on its wall, flange vs CD body, flange vs flange,
entry path vs the quarter-wave rule, front-chamber corner. Driver dimensions: datasheet cutout/depth (appendix A s8);
frame OD = cutout + 12 mm and motor diameter = 0.6 x cutout are [inferred] placeholders until M1 reads the drawings.
"""
from __future__ import annotations

import itertools
import math
import sys
from dataclasses import dataclass, replace

import numpy as np

C = 343.0


@dataclass(frozen=True)
class Cone:
    name: str
    cutout_mm: float
    depth_mm: float       # mounting depth (flange to motor back)
    sd_cm2: float
    dish_mm: float        # cone dish depth below the flange plane [inferred ~0.2 x cutout]

    @property
    def frame_r(self):
        return (self.cutout_mm + 12.0) / 2

    @property
    def motor_r(self):
        return 0.3 * self.cutout_mm


@dataclass(frozen=True)
class CD:
    name: str
    exit_mm: float
    body_d_mm: float
    body_len_mm: float
    duct_mm: float        # diaphragm to exit [inferred until drawings]


B_C_4NDF34 = Cone("B&C 4NDF34", 103, 66, 57, 20)
B_C_6NDL38 = Cone("B&C 6NDL38", 145, 85, 132, 30)
FAITAL_6PR160 = Cone("FaitalPRO 6PR160", 147, 73, 130, 30)
HF108 = CD("FaitalPRO HF108", 25.4, 87, 41, 25)
DH450 = CD("B&C DH450", 25.4, 69, 48, 25)
HF1440 = CD("FaitalPRO HF1440", 35.8, 124, 75, 40)


@dataclass(frozen=True)
class Layout:
    cone: Cone
    cd: CD
    walls: tuple          # ("tb",), ("lr",) or ("tb", "lr"): one driver per wall listed, both signs
    cov_h: float = 90.0
    cov_v: float = 60.0
    z_port: float = 70.0  # port centroid, axial mm from the coupling plane
    port_across: float = 60.0
    port_along: float = 25.0
    slide: float = 0.0    # driver centre offset along the wall slant from the port centroid (mm, + toward mouth)
    spacer: float = 4.0
    wall_t: float = 6.0
    roll: float = 20.0
    env_w: float = 406.4
    env_h: float = 406.4
    env_d: float = 380.0
    box_t: float = 18.0
    clearance: float = 3.0
    fill: float = 0.0      # fraction of the cone dish volume taken by a printed filler (front-chamber reducer)
    across_frac: float = 0.0  # > 0: port_across = across_frac x (this wall's width at the port's near end - 6 mm)


def _tan(deg):
    return math.tan(math.radians(deg / 2))


def geometry(L: Layout):
    th, tv = _tan(L.cov_h), _tan(L.cov_v)
    a_exit = math.pi * (L.cd.exit_mm / 2) ** 2
    z_c = math.sqrt(a_exit / (4 * th * tv))
    xin = L.env_w / 2 - L.box_t - L.roll
    yin = L.env_h / 2 - L.box_t - L.roll
    z_m = min(xin / th, yin / tv) - z_c          # longest horn whose mouth + roll fits the face
    return dict(th=th, tv=tv, z_c=z_c, z_m=z_m, mouth_w=2 * (z_m + z_c) * th, mouth_h=2 * (z_m + z_c) * tv)


def _wall_frame(wall, sign, g):
    """Port-centre point function, slant tangent t, outward normal n for a wall."""
    if wall == "tb":
        half = math.atan(g["tv"])
        t = np.array([0.0, sign * math.sin(half), math.cos(half)])
        n = np.array([0.0, sign * math.cos(half), -math.sin(half)])
        e = np.array([1.0, 0.0, 0.0])
        def p(z):
            return np.array([0.0, sign * (z + g["z_c"]) * g["tv"], z])
        def width(z):
            return 2 * (z + g["z_c"]) * g["th"]
    else:
        half = math.atan(g["th"])
        t = np.array([sign * math.sin(half), 0.0, math.cos(half)])
        n = np.array([sign * math.cos(half), 0.0, -math.sin(half)])
        e = np.array([0.0, 1.0, 0.0])
        def p(z):
            return np.array([sign * (z + g["z_c"]) * g["th"], 0.0, z])
        def width(z):
            return 2 * (z + g["z_c"]) * g["tv"]
    return p, t, n, e, width


def _driver_points(L: Layout, wall, sign, g, n_ring=48, n_rad=4):
    p, t, n, e, width = _wall_frame(wall, sign, g)
    base = p(L.z_port) + L.slide * t
    flange_c = base + (L.wall_t + L.spacer) * n
    pts = []
    for k in range(1, n_rad + 1):
        r = L.cone.frame_r * k / n_rad
        for phi in np.linspace(0, 2 * np.pi, n_ring, endpoint=False):
            pts.append(flange_c + r * (math.cos(phi) * e + math.sin(phi) * t))
    motor_end = flange_c + L.cone.depth_mm * n
    for phi in np.linspace(0, 2 * np.pi, n_ring, endpoint=False):
        for c in (flange_c + 0.3 * L.cone.depth_mm * n, motor_end):
            pts.append(c + L.cone.motor_r * (math.cos(phi) * e + math.sin(phi) * t))
    return np.array(pts), (p, t, n, e, width)


def _narrowest(L: Layout, g, z0):
    """Equal ports on every wall of a multi-wall layout: size them by the narrowest wall at z0."""
    return min(_wall_frame(w, 1, g)[4](z0) for w in L.walls)


def check(L: Layout):
    g = geometry(L)
    out = dict(g)
    reasons = []
    hx = L.env_w / 2 - L.box_t
    hy = L.env_h / 2 - L.box_t
    z_back = g["z_m"] - L.env_d + L.box_t
    if L.cd.body_len_mm > -z_back + 0 and -L.cd.body_len_mm < z_back:
        reasons.append("cd_body_behind_box")
    clouds = []
    for wall in L.walls:
        for sign in (1, -1):
            pts, (p, t, n, e, width) = _driver_points(L, wall, sign, g)
            clouds.append(pts)
            # port fits on the wall over its axial extent, beyond a 5 mm throat blend, before the mouth
            dz = 0.5 * L.port_along * t[2]
            z0, z1 = L.z_port - dz, L.z_port + dz
            across = L.across_frac * max(_narrowest(L, g, z0) - 6.0, 1.0) if L.across_frac > 0 else L.port_across
            if z0 < 5.0:
                reasons.append("port_in_throat_blend")
            if z1 > g["z_m"] - 10.0:
                reasons.append("port_at_mouth")
            if across > width(z0) - 6.0:
                reasons.append("port_wider_than_wall")
            if np.any(np.abs(pts[:, 0]) > hx) or np.any(np.abs(pts[:, 1]) > hy):
                reasons.append("driver_outside_face")
            if np.any(pts[:, 2] < z_back):
                reasons.append("driver_behind_box")
            if np.any(pts[:, 2] > g["z_m"]):
                reasons.append("driver_past_mouth")
            behind = pts[pts[:, 2] < 0.0]
            if behind.size:
                rr = np.hypot(behind[:, 0], behind[:, 1])
                inside_len = behind[:, 2] > -L.cd.body_len_mm
                if np.any((rr < L.cd.body_d_mm / 2 + L.clearance) & inside_len):
                    reasons.append("driver_hits_cd")
            # flange must stay outside the horn interior: any flange point inside the pyramid is a collision
            zz = pts[:, 2]
            inside = (np.abs(pts[:, 0]) < (zz + g["z_c"]) * g["th"]) & (np.abs(pts[:, 1]) < (zz + g["z_c"]) * g["tv"]) \
                & (zz > 0) & (zz < g["z_m"])
            if np.any(inside):
                reasons.append("driver_inside_horn")
    for a, b in itertools.combinations(range(len(clouds)), 2):
        d = np.min(np.linalg.norm(clouds[a][:, None, :] - clouds[b][None, :, :], axis=2))
        if d < L.clearance:
            reasons.append("drivers_collide")
            break
    # acoustics
    d_diaphragm = L.z_port + L.cd.duct_mm
    out["path_to_diaphragm_mm"] = d_diaphragm
    out["f_quarter_wave_hz"] = C / (4 * d_diaphragm / 1000)
    s_port = L.port_across * L.port_along * 1e-6
    r_eq = math.sqrt(s_port / math.pi)
    v_front = (L.cone.sd_cm2 * 1e-4) * (L.spacer + L.wall_t + (1 - L.fill) * L.cone.dish_mm / 3) * 1e-3
    l_eff = L.wall_t * 1e-3 + 2 * 0.85 * r_eq
    out["v_front_cm3"] = v_front * 1e6
    out["port_frac_sd"] = s_port * 1e4 / L.cone.sd_cm2
    out["f_h_hz"] = C / (2 * math.pi) * math.sqrt(s_port / (v_front * l_eff))
    gross = (L.env_w - 2 * L.box_t) * (L.env_h - 2 * L.box_t) * (L.env_d - 2 * L.box_t) * 1e-6
    horn_v = (4 * g["th"] * g["tv"] / 3) * ((g["z_m"] + g["z_c"]) ** 3 - g["z_c"] ** 3) * 1e-6
    out["box_interior_l"] = gross
    out["horn_air_l"] = horn_v
    out["reasons"] = sorted(set(reasons))
    out["ok"] = not reasons
    return out


def sweep(base: Layout, label: str, rng: np.random.Generator, n: int = 400):
    """Random sample of the knob box; report feasible fraction and the feasible ranges."""
    feas, why = [], {}
    for _ in range(n):
        L = replace(base,
                    cov_h=rng.uniform(70, 100), cov_v=rng.uniform(40, 90),
                    z_port=rng.uniform(20, 140), port_across=rng.uniform(20, 90),
                    port_along=rng.uniform(10, 40), slide=rng.uniform(-50, 50), spacer=rng.uniform(2, 12))
        r = check(L)
        if r["ok"]:
            feas.append((L, r))
        for k in r["reasons"]:
            why[k] = why.get(k, 0) + 1
    print(f"#### {label}\n")
    print(f"feasible {len(feas)}/{n}; failure reasons (count): "
          + ", ".join(f"{k} {v}" for k, v in sorted(why.items(), key=lambda kv: -kv[1])) + "\n")
    if feas:
        def rng_of(fn):
            vals = [fn(L, r) for L, r in feas]
            return f"{min(vals):.0f}-{max(vals):.0f}"
        print("| knob / output | feasible range |")
        print("|---|---|")
        for name, fn in [("cov_h", lambda L, r: L.cov_h), ("cov_v", lambda L, r: L.cov_v),
                         ("z_port (mm)", lambda L, r: L.z_port), ("port_across (mm)", lambda L, r: L.port_across),
                         ("slide (mm)", lambda L, r: L.slide), ("mouth W (mm)", lambda L, r: r["mouth_w"]),
                         ("mouth H (mm)", lambda L, r: r["mouth_h"]), ("horn length z_m (mm)", lambda L, r: r["z_m"]),
                         ("quarter-wave f at diaphragm (Hz)", lambda L, r: r["f_quarter_wave_hz"]),
                         ("f_h port corner (Hz)", lambda L, r: r["f_h_hz"])]:
            print(f"| {name} | {rng_of(fn)} |")
        print()
    return feas


def from_fractions(base: Layout, u: dict) -> Layout:
    """Reparameterised knobs (all in [0, 1] or physical ranges) -> a Layout, with a deterministic repair.

    port_across = frac x (wall width at the port's near end - 6 mm); z_port in [z_lo, z_hi] where z_lo clears the
    throat blend and z_hi keeps the port 10 mm inside the mouth; slide is increased (toward the mouth) in 2 mm steps
    until the flange clears the CD body, then decreased if it now passes the mouth. This is the bounds design the
    GA should get (tools/cad/meh.py implements the same repair and logs it)."""
    L = replace(base, cov_h=u["cov_h"], cov_v=u["cov_v"], port_along=u["port_along"], spacer=u["spacer"],
                slide=u["slide"], fill=u.get("fill", base.fill))
    g = geometry(L)
    z_lo = 5.0 + 0.5 * L.port_along
    z_hi = g["z_m"] - 10.0 - 0.5 * L.port_along
    z = z_lo + u["z_frac"] * max(z_hi - z_lo, 0.0)
    L = replace(L, z_port=z)
    wall = L.walls[0]
    _, t, _, _, width = _wall_frame(wall, 1, g)
    z0 = z - 0.5 * L.port_along * t[2]
    L = replace(L, port_across=u["across_frac"] * max(_narrowest(L, g, z0) - 6.0, 1.0), across_frac=u["across_frac"])
    for _ in range(60):
        r = check(L)
        if "driver_hits_cd" in r["reasons"]:
            L = replace(L, slide=L.slide + 2.0)
        elif "driver_past_mouth" in r["reasons"] and "driver_hits_cd" not in r["reasons"]:
            L = replace(L, slide=L.slide - 2.0)
            if "driver_hits_cd" in check(L)["reasons"]:
                break
        else:
            break
    return L


def sweep_reparam(base: Layout, label: str, rng: np.random.Generator, box: dict, n: int = 400):
    feas, why = [], {}
    for _ in range(n):
        u = {k: rng.uniform(*v) for k, v in box.items()}
        L = from_fractions(base, u)
        r = check(L)
        if r["ok"]:
            feas.append((L, r))
        for k in r["reasons"]:
            why[k] = why.get(k, 0) + 1
    vals = lambda fn: [fn(L, r) for L, r in feas]
    q = lambda xs: f"{np.percentile(xs, 5):.0f}-{np.percentile(xs, 95):.0f}" if xs else "-"
    print(f"| {label} | {len(feas)}/{n} | " + (", ".join(f"{k} {v}" for k, v in sorted(why.items(), key=lambda kv: -kv[1])) or "none")
          + f" | {q(vals(lambda L, r: L.z_port))} | {q(vals(lambda L, r: r['f_quarter_wave_hz']))} | "
          f"{q(vals(lambda L, r: r['f_h_hz']))} | {q(vals(lambda L, r: r['port_frac_sd'] * 100))} |")
    return feas


def seed_report(L: Layout, label: str):
    r = check(L)
    print(f"| {label} | {L.cov_h:.0f}x{L.cov_v:.0f} | {r['mouth_w']:.0f} x {r['mouth_h']:.0f} | {r['z_m']:.0f} | "
          f"{L.z_port:.0f} | {r['path_to_diaphragm_mm']:.0f} | {r['f_quarter_wave_hz']:.0f} | {r['v_front_cm3']:.0f} | "
          f"{r['port_frac_sd']:.2f} | {r['f_h_hz']:.0f} | {r['box_interior_l']:.0f} | "
          f"{'OK' if r['ok'] else ', '.join(r['reasons'])} |")


if __name__ == "__main__":
    rng = np.random.default_rng(20261030)
    print("Envelope: 406.4 x 406.4 mm face (16 in), 380 mm deep, 18 mm walls, 20 mm mouth roll.\n")
    print("### Seeds\n")
    print("| seed | coverage | mouth W x H | horn length (mm) | port z (mm) | path to diaphragm (mm) | "
          "quarter-wave f (Hz) | V_front (cm^3) | port / Sd | f_h (Hz) | box interior (L) | layout |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    t2 = Layout(B_C_6NDL38, HF108, ("tb",), 90, 60, z_port=60, port_across=70, port_along=26, slide=10, spacer=4)
    seed_report(t2, "T2 2 x 6NDL38 top/bottom, HF108")
    seed_report(replace(t2, walls=("lr",)), "T2 2 x 6NDL38 sides, HF108")
    seed_report(replace(t2, cone=FAITAL_6PR160), "T2 2 x 6PR160 top/bottom, HF108")
    seed_report(replace(t2, cd=HF1440, z_port=70), "T2 2 x 6NDL38 top/bottom, HF1440")
    t1 = Layout(B_C_4NDF34, HF108, ("tb", "lr"), 90, 60, z_port=45, port_across=40, port_along=20, slide=15,
                spacer=3)
    seed_report(t1, "T1 4 x 4NDF34 all walls, HF108")
    seed_report(replace(t1, cov_h=80, cov_v=80), "T1 4 x 4NDF34 all walls 80x80")
    seed_report(replace(t1, cd=DH450), "T1 4 x 4NDF34 all walls, DH450")
    print()
    print("### Random knob-box sweeps (n = 400 each)\n")
    sweep(t2, "T2: 2 x 6NDL38 on the top/bottom walls, HF108", rng)
    sweep(replace(t2, walls=("lr",)), "T2: 2 x 6NDL38 on the side walls, HF108", rng)
    sweep(t1, "T1: 4 x 4NDF34, one per wall, HF108", rng)

    print("### Reparameterised knob box with deterministic repair (n = 400 each)\n")
    print("Box: cov_h 75-95, cov_v 50-80, z_frac 0-1, across_frac 0.35-0.9, port_along 12-35 mm, spacer 2-8 mm, "
          "slide -10..40 mm (repaired), fill 0-0.7 (6.5-inch only).\n")
    print("| typology | feasible | remaining failures | z_port 5-95 % (mm) | quarter-wave f 5-95 % (Hz) | "
          "f_h 5-95 % (Hz) | port / Sd 5-95 % (%) |")
    print("|---|---|---|---|---|---|---|")
    box = dict(cov_h=(75, 95), cov_v=(50, 80), z_frac=(0, 1), across_frac=(0.35, 0.9), port_along=(12, 35),
               spacer=(2, 8), slide=(-10, 40))
    box65 = dict(box, fill=(0.0, 0.7))
    sweep_reparam(t2, "T2 2 x 6NDL38 top/bottom, HF108", rng, box65)
    sweep_reparam(replace(t2, cd=HF1440), "T2 2 x 6NDL38 top/bottom, HF1440", rng, box65)
    sweep_reparam(replace(t2, walls=("lr",)), "T2 2 x 6NDL38 sides, HF108", rng, box65)
    sweep_reparam(t1, "T1 4 x 4NDF34 one per wall, HF108", rng, box)
    sweep_reparam(replace(t1, walls=("tb",)), "T1b 2 x 4NDF34 top/bottom, HF108", rng, box)
    print()
    print("### Final seeds (after repair)\n")
    print("| seed | coverage | mouth W x H | horn length (mm) | port z (mm) | path to diaphragm (mm) | "
          "quarter-wave f (Hz) | V_front (cm^3) | port / Sd | f_h (Hz) | box interior (L) | layout |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    s2 = from_fractions(replace(t2, cd=HF1440), dict(cov_h=90, cov_v=60, z_frac=0.25, across_frac=0.8,
                                                     port_along=30, spacer=3, slide=10, fill=0.0))
    seed_report(s2, "T2-A seed: 2 x 6NDL38 t/b + HF1440, no fill")
    s2b = from_fractions(t2, dict(cov_h=90, cov_v=60, z_frac=0.2, across_frac=0.85, port_along=30, spacer=3,
                                  slide=10, fill=0.6))
    seed_report(s2b, "T2-B seed: 2 x 6NDL38 t/b + HF108, 60 % fill")
    s1 = from_fractions(t1, dict(cov_h=90, cov_v=60, z_frac=0.25, across_frac=0.7, port_along=20, spacer=3,
                                 slide=10))
    seed_report(s1, "T1 seed: 4 x 4NDF34 + HF108")
    sys.exit(0)
