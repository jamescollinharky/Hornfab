"""Multiple-entry horn (MEH) L1 CAD: horn + box + flush mid-port patches -> labelled STEP.

LABELLED-HYPOTHESIS-SHAPE EXPERIMENT under a neutral name (task M5, 2026-10-30). The layout is the
reference implementation ``docs/research/typologies/mini_meh_2026-10-29/calc/meh_layout.py``
(``geometry``, ``_wall_frame``, ``check``, ``from_fractions``, ``_narrowest``) ported into this tool,
with the same numbers; ``layout_out.md``'s "Final seeds" are the T2-A / T1 seeds. This module is a
*tool*, not library code: every number is a documented default and a CLI argument, and the mesh
adapter (``hornlab_search/mesh/step_build.py``) loads it by file path.

Frame (identical to ``plughorn.py`` / the reference): millimetres, the CD coupling plane at ``z = 0``,
``+z`` toward the mouth, ``x`` horizontal and ``y`` vertical. The horn is a flat-wall pyramid with its
virtual apex at ``z = -z_c`` and ``z_c = sqrt(A_exit / (4 tan(h/2) tan(v/2)))`` so the section at
``z = 0`` has the CD exit area. The mouth is at ``z_m``; a quarter-round of ``roll_mm`` carries it to
the front face at ``z_m + roll_mm``.

L1 solid (contract C9)
----------------------
ONE material solid = the outer box (``env_w_mm x env_h_mm``, starting at the mouth plane and running
back ``env_d_mm``) minus the horn air (pyramid frustum from ``z = 0`` to the mouth, plus the mouth
roundover) minus the CD bore (a cylinder of ``exit_mm`` from ``z = -cd_duct_mm`` to ``0``). The mid
ports are **imprinted** flush patches on the horn's inner walls: a rectangle ``port_along_mm`` along
the wall slant by ``port_across_mm`` across it, centred at the port centroid. No hole and no chamber
(C3). The solid is cut to the quarter ``x >= 0, y >= 0``; the two cut planes are NOT BEM faces, so the
exported shape is an OPEN shell (the mesher solves it with ``quadrants="1"`` and
``native_symmetry_plane="yz+xz"``).

Face-label contract (C3)
------------------------
Every face carries exactly one label:

``driver``     the CD diaphragm disc at ``z = -cd_duct_mm`` (tag 2, SD1D1001)
``entry_mid``  each imprinted mid-port patch (tag 10, mid_port_exit_left)
``entry_aux``  reserved; no face in v1 (tag 11, mid_port_exit_right)
``wall``       every other face (tag 1, SD1G0)

``[inferred]`` driver values
----------------------------
M1 (the driver datasheets) has not landed. This tool therefore uses the C9 contract defaults and marks
them inferred, exactly as C9 does: ``exit_mm = 35.8`` (HF1440), ``cd_duct_mm = 40`` (* in C9),
``cd_body_d_mm = 124`` and ``cd_body_len_mm = 75``. The C9 cone defaults are ``cone_cutout_mm = 145``
and ``cone_depth_mm = 85`` (B&C 6NDL38); the T1 seed passes the B&C 4NDF34 pair instead. ``derived()``
echoes ``inferred_keys``. The reference cone records (Sd + dish) live in ``_REFERENCE_CONES`` until M1
supplies the driver files; the tool refuses an unknown cone pair rather than guess Sd.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

import numpy as np

C = 343.0  # m/s, the reference's constant
_LABEL_COLOURS = {
    "driver": (0.37, 0.53, 0.71),
    "wall": (0.61, 0.47, 0.29),
    "entry_mid": (0.20, 0.70, 0.35),
    "entry_aux": (0.80, 0.20, 0.60),
}
LABELS = ("driver", "wall", "entry_mid", "entry_aux")

#: Reference cone records (name, Sd, dish). ``dish_mm`` is the reference's inferred placeholder
#: (``~0.2 x cutout``) and ``sd_cm2`` the datasheet Sd used by the research layout. M1 replaces both
#: with the driver files; until then these three pairs are the only cones the tool can lay out.
_REFERENCE_CONES: dict[tuple[float, float], dict[str, Any]] = {
    (103.0, 66.0): {"name": "B&C 4NDF34", "sd_cm2": 57.0, "dish_mm": 20.0},
    (145.0, 85.0): {"name": "B&C 6NDL38", "sd_cm2": 132.0, "dish_mm": 30.0},
    (147.0, 73.0): {"name": "FaitalPRO 6PR160", "sd_cm2": 130.0, "dish_mm": 30.0},
}

#: C9 recipe keys, every one required (like plughorn) and no others are accepted.
KEYS = (
    "cov_h_deg", "cov_v_deg", "z_frac", "across_frac", "port_along_mm", "slide_mm", "walls",
    "env_w_mm", "env_h_mm", "env_d_mm", "box_t_mm", "roll_mm", "wall_t_mm", "spacer_mm",
    "exit_mm", "cd_duct_mm", "cd_body_d_mm", "cd_body_len_mm", "cone_cutout_mm", "cone_depth_mm",
    "clearance_mm",
)
#: Values taken from the C9 table while M1's driver files have not landed. C9 stars cd_duct_mm with
#: "*" = [inferred]; the other three are the C9 "from the CD/cone file" defaults, equally placeholders.
INFERRED_KEYS = ("exit_mm", "cd_duct_mm", "cone_cutout_mm", "cone_depth_mm")


def _multicell():
    """The sibling multicell tool: its OCC bridge and STEP round-trip parser are reused, not copied."""
    name = "hornlab_search_cad_multicell"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "multicell.py")
    if spec is None or spec.loader is None:
        raise ImportError("could not load tools/cad/multicell.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@dataclass(frozen=True)
class MehParams:
    """The tool's own parameters: every C9 recipe key, plus the derived port placement and repair log."""

    cov_h_deg: float = 90.0
    cov_v_deg: float = 60.0
    z_frac: float = 0.25
    across_frac: float = 0.8
    port_along_mm: float = 30.0
    slide_mm: float = 10.0
    walls: str = "tb"
    env_w_mm: float = 406.4
    env_h_mm: float = 406.4
    env_d_mm: float = 380.0
    box_t_mm: float = 18.0
    roll_mm: float = 20.0
    wall_t_mm: float = 6.0
    spacer_mm: float = 3.0
    exit_mm: float = 35.8           # [inferred] C9 / HF1440
    cd_duct_mm: float = 40.0        # [inferred] C9 *
    cd_body_d_mm: float = 124.0     # [inferred] C9 / HF1440
    cd_body_len_mm: float = 75.0    # [inferred] C9 / HF1440
    cone_cutout_mm: float = 145.0   # [inferred] C9 / B&C 6NDL38
    cone_depth_mm: float = 85.0     # [inferred] C9 / B&C 6NDL38
    clearance_mm: float = 3.0
    # ---- computed by from_fractions(); not recipe keys
    z_port_mm: float = 0.0
    port_across_mm: float = 0.0
    repairs: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def walls_list(self) -> tuple[str, ...]:
        if self.walls == "tb":
            return ("tb",)
        if self.walls == "lr":
            return ("lr",)
        return ("tb", "lr")  # tblr

    def validate(self) -> None:
        if self.walls not in ("tb", "lr", "tblr"):
            raise ValueError(f"walls must be 'tb', 'lr', or 'tblr', got {self.walls!r}")
        for name in ("cov_h_deg", "cov_v_deg"):
            if not 0.0 < float(getattr(self, name)) < 180.0:
                raise ValueError(f"{name} must be in (0, 180), got {getattr(self, name)!r}")
        for name in ("port_along_mm", "env_w_mm", "env_h_mm", "env_d_mm", "box_t_mm",
                     "wall_t_mm", "exit_mm", "cd_body_d_mm", "cd_body_len_mm",
                     "cone_cutout_mm", "cone_depth_mm", "clearance_mm"):
            if not float(getattr(self, name)) > 0.0:
                raise ValueError(f"{name} must be > 0, got {getattr(self, name)!r}")
        for name in ("roll_mm", "spacer_mm", "cd_duct_mm"):
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} must be >= 0, got {getattr(self, name)!r}")
        if not math.isfinite(float(self.slide_mm)):
            raise ValueError(f"slide_mm must be finite, got {self.slide_mm!r}")
        if not 0.0 <= float(self.z_frac) <= 1.0:
            raise ValueError(f"z_frac must be in [0, 1], got {self.z_frac!r}")
        if not 0.0 < float(self.across_frac) <= 1.0:
            raise ValueError(f"across_frac must be in (0, 1], got {self.across_frac!r}")
        if self.env_d_mm <= 2.0 * self.box_t_mm:
            raise ValueError("env_d_mm must be deeper than two box walls")
        _cone_data(self)


def _cone_data(p: MehParams) -> dict[str, Any]:
    key = (round(float(p.cone_cutout_mm), 3), round(float(p.cone_depth_mm), 3))
    data = _REFERENCE_CONES.get(key)
    if data is None:
        raise ValueError(
            "unknown cone cutout/depth "
            f"{p.cone_cutout_mm:g}/{p.cone_depth_mm:g} mm: M1's cone datasheets have not landed, so the "
            "MEH tool only knows the C9 reference cones "
            f"{sorted(_REFERENCE_CONES)} (Sd and dish would otherwise be guesses)")
    return data


DEFAULTS = MehParams()


def defaults() -> dict[str, Any]:
    """The C9 T2-A recipe defaults (every key required, no hidden defaults in a recipe)."""
    return {k: getattr(DEFAULTS, k) for k in KEYS}


def _tan(deg: float) -> float:
    return math.tan(math.radians(deg / 2.0))


def geometry(p: MehParams) -> dict[str, float]:
    """The reference ``geometry``: pyramid apex distance, horn length and mouth size."""
    th, tv = _tan(p.cov_h_deg), _tan(p.cov_v_deg)
    a_exit = math.pi * (p.exit_mm / 2.0) ** 2
    z_c = math.sqrt(a_exit / (4.0 * th * tv))
    xin = p.env_w_mm / 2.0 - p.box_t_mm - p.roll_mm
    yin = p.env_h_mm / 2.0 - p.box_t_mm - p.roll_mm
    z_m = min(xin / th, yin / tv) - z_c          # longest horn whose mouth + roll fits the face
    return {"th": th, "tv": tv, "z_c": z_c, "z_m": z_m,
            "mouth_w": 2.0 * (z_m + z_c) * th, "mouth_h": 2.0 * (z_m + z_c) * tv}


def _wall_frame(wall: str, sign: int, g: dict[str, float]):
    """Port-centre point function, slant tangent ``t``, outward normal ``n``, across ``e``, width."""
    if wall == "tb":
        half = math.atan(g["tv"])
        t = np.array([0.0, sign * math.sin(half), math.cos(half)])
        n = np.array([0.0, sign * math.cos(half), -math.sin(half)])
        e = np.array([1.0, 0.0, 0.0])

        def p(z):
            return np.array([0.0, sign * (z + g["z_c"]) * g["tv"], z])

        def width(z):
            return 2.0 * (z + g["z_c"]) * g["th"]
    else:
        half = math.atan(g["th"])
        t = np.array([sign * math.sin(half), 0.0, math.cos(half)])
        n = np.array([sign * math.cos(half), 0.0, -math.sin(half)])
        e = np.array([0.0, 1.0, 0.0])

        def p(z):
            return np.array([sign * (z + g["z_c"]) * g["th"], 0.0, z])

        def width(z):
            return 2.0 * (z + g["z_c"]) * g["tv"]
    return p, t, n, e, width


def _narrowest(p: MehParams, g: dict[str, float], z0: float) -> float:
    """Equal ports on every wall: size them by the narrowest used wall at the port's near end."""
    return min(_wall_frame(w, 1, g)[4](z0) for w in p.walls_list)


def _driver_points(p: MehParams, wall: str, sign: int, g: dict[str, float],
                   n_ring: int = 48, n_rad: int = 4):
    """The reference driver-envelope point cloud (frame ring + motor ring)."""
    point, t, n, e, width = _wall_frame(wall, sign, g)
    base = point(p.z_port_mm) + p.slide_mm * t
    flange_c = base + (p.wall_t_mm + p.spacer_mm) * n
    frame_r = (p.cone_cutout_mm + 12.0) / 2.0
    motor_r = 0.3 * p.cone_cutout_mm
    pts = []
    for k in range(1, n_rad + 1):
        r = frame_r * k / n_rad
        for phi in np.linspace(0.0, 2.0 * np.pi, n_ring, endpoint=False):
            pts.append(flange_c + r * (math.cos(phi) * e + math.sin(phi) * t))
    motor_end = flange_c + p.cone_depth_mm * n
    for phi in np.linspace(0.0, 2.0 * np.pi, n_ring, endpoint=False):
        for c in (flange_c + 0.3 * p.cone_depth_mm * n, motor_end):
            pts.append(c + motor_r * (math.cos(phi) * e + math.sin(phi) * t))
    return np.array(pts), (point, t, n, e, width)


def check(p: MehParams) -> dict[str, Any]:
    """The reference ``check``: geometry, every layout reason, and the acoustic diagnostics."""
    g = geometry(p)
    out: dict[str, Any] = dict(g)
    reasons: list[str] = []
    hx = p.env_w_mm / 2.0 - p.box_t_mm
    hy = p.env_h_mm / 2.0 - p.box_t_mm
    z_back = g["z_m"] - p.env_d_mm + p.box_t_mm
    if p.cd_body_len_mm > -z_back and -p.cd_body_len_mm < z_back:
        reasons.append("cd_body_behind_box")
    clouds = []
    for wall in p.walls_list:
        for sign in (1, -1):
            pts, (point, t, n, e, width) = _driver_points(p, wall, sign, g)
            clouds.append(pts)
            # port fits on the wall over its axial extent, beyond a 5 mm throat blend, before the mouth
            dz = 0.5 * p.port_along_mm * t[2]
            z0, z1 = p.z_port_mm - dz, p.z_port_mm + dz
            across = (p.across_frac * max(_narrowest(p, g, z0) - 6.0, 1.0)
                      if p.across_frac > 0.0 else p.port_across_mm)
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
                inside_len = behind[:, 2] > -p.cd_body_len_mm
                if np.any((rr < p.cd_body_d_mm / 2.0 + p.clearance_mm) & inside_len):
                    reasons.append("driver_hits_cd")
            # flange must stay outside the horn interior: any flange point inside the pyramid collides
            zz = pts[:, 2]
            inside = ((np.abs(pts[:, 0]) < (zz + g["z_c"]) * g["th"])
                      & (np.abs(pts[:, 1]) < (zz + g["z_c"]) * g["tv"])
                      & (zz > 0.0) & (zz < g["z_m"]))
            if np.any(inside):
                reasons.append("driver_inside_horn")
    for a in range(len(clouds)):
        for b in range(a + 1, len(clouds)):
            d = np.min(np.linalg.norm(clouds[a][:, None, :] - clouds[b][None, :, :], axis=2))
            if d < p.clearance_mm:
                reasons.append("drivers_collide")
                break

    # acoustics
    d_diaphragm = p.z_port_mm + p.cd_duct_mm
    out["path_to_diaphragm_mm"] = d_diaphragm
    out["f_quarter_wave_hz"] = C / (4.0 * d_diaphragm / 1000.0)
    cone = _cone_data(p)
    s_port = p.port_across_mm * p.port_along_mm * 1e-6
    r_eq = math.sqrt(s_port / math.pi)
    v_front = (cone["sd_cm2"] * 1e-4) * (p.spacer_mm + p.wall_t_mm + cone["dish_mm"] / 3.0) * 1e-3
    l_eff = p.wall_t_mm * 1e-3 + 2.0 * 0.85 * r_eq
    out["v_front_cm3"] = v_front * 1e6
    out["port_frac_sd"] = s_port * 1e4 / cone["sd_cm2"]
    out["f_h_hz"] = C / (2.0 * math.pi) * math.sqrt(s_port / (v_front * l_eff))
    gross = ((p.env_w_mm - 2.0 * p.box_t_mm) * (p.env_h_mm - 2.0 * p.box_t_mm)
             * (p.env_d_mm - 2.0 * p.box_t_mm) * 1e-6)
    horn_v = (4.0 * g["th"] * g["tv"] / 3.0) * (
        (g["z_m"] + g["z_c"]) ** 3 - g["z_c"] ** 3) * 1e-6
    out["box_interior_l"] = gross
    out["horn_air_l"] = horn_v
    out["z_port_mm"] = p.z_port_mm
    out["port_across_mm"] = p.port_across_mm
    out["port_area_mm2"] = p.port_across_mm * p.port_along_mm
    out["slide_mm"] = p.slide_mm
    out["walls"] = p.walls
    out["repairs"] = [dict(r) for r in p.repairs]
    out["inferred_keys"] = list(INFERRED_KEYS)
    out["ports"] = [
        {"wall": wall, "sign": sign,
         "centroid_mm": [float(v) for v in _wall_frame(wall, sign, g)[0](p.z_port_mm)],
         "area_mm2": p.port_across_mm * p.port_along_mm,
         "z_port_mm": p.z_port_mm,
         "path_to_diaphragm_mm": d_diaphragm,
         "f_quarter_wave_hz": out["f_quarter_wave_hz"]}
        for wall in p.walls_list for sign in (1, -1)
    ]
    out["reasons"] = sorted(set(reasons))
    out["ok"] = not reasons
    return out


def _from_fractions(p: MehParams) -> MehParams:
    """The reference ``from_fractions`` + the deterministic slide repair, logged in ``repairs``.

    ``port_across = across_frac x (narrowest used wall width at the port's near end - 6 mm)`` and
    ``z_port`` is ``z_frac`` between the throat-blend clear and the 10 mm-inside-the-mouth bound;
    ``slide`` is increased (toward the mouth) in 2 mm steps while the flange hits the CD body, then
    decreased if it now passes the mouth (the generalised repair point).
    """
    g = geometry(p)
    z_lo = 5.0 + 0.5 * p.port_along_mm
    z_hi = g["z_m"] - 10.0 - 0.5 * p.port_along_mm
    z = z_lo + p.z_frac * max(z_hi - z_lo, 0.0)
    p = replace(p, z_port_mm=z, repairs=())
    wall = p.walls_list[0]
    _, t, _, _, _width = _wall_frame(wall, 1, g)
    z0 = z - 0.5 * p.port_along_mm * t[2]
    p = replace(p, port_across_mm=p.across_frac * max(_narrowest(p, g, z0) - 6.0, 1.0))
    repairs: list[dict[str, Any]] = []

    def _step(reason: str, delta: float) -> MehParams:
        new = round(p.slide_mm + delta, 10)
        repairs.append({"knob": "slide_mm", "from_mm": p.slide_mm, "to_mm": new,
                        "step_mm": delta, "reason": reason})
        return replace(p, slide_mm=new)

    for _ in range(60):
        reasons = check(p)["reasons"]
        if "driver_hits_cd" in reasons:
            p = _step("driver_hits_cd", 2.0)
        elif "driver_past_mouth" in reasons and "driver_hits_cd" not in reasons:
            p = _step("driver_past_mouth", -2.0)
            if "driver_hits_cd" in check(p)["reasons"]:
                break
        else:
            break
    return replace(p, repairs=tuple(repairs))


def params_from_recipe(recipe: dict[str, Any] | MehParams) -> MehParams:
    """``cad`` recipe -> the tool's repaired params (mm / deg), refusing unknown or missing keys."""
    if isinstance(recipe, MehParams):
        return recipe
    values = {k: v for k, v in recipe.items() if k != "tool"}
    unknown = sorted(set(values) - set(KEYS))
    if unknown:
        raise ValueError(f"unknown meh key(s) {unknown}")
    missing = [k for k in KEYS if k not in values]
    if missing:
        raise ValueError(f"missing required meh key(s) {missing}; the recipe carries every key")
    p = replace(DEFAULTS, **values)
    p.validate()
    return _from_fractions(p)


def derived(recipe: dict[str, Any] | MehParams) -> dict[str, Any]:
    """Pure-numpy layout from the reference, including the repair log and the reasons (empty = OK)."""
    return check(params_from_recipe(recipe))


# ---------------------------------------------------------------------- CAD


def _cad():
    """Import build123d/OCP on use (the optional ``cad`` extra), like plughorn."""
    base = _multicell()._cad()
    try:
        from OCP.BRep import BRep_Tool
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepFeat import BRepFeat_SplitShape
        from OCP.TopAbs import TopAbs_SHELL
        from OCP.TopExp import TopExp_Explorer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "this tool needs build123d; install the optional extra: "
            "`.venv\\Scripts\\python.exe -m pip install -e .[cad]`") from exc
    return {**base, "BRep_Tool": BRep_Tool, "BRepCheck_Analyzer": BRepCheck_Analyzer,
            "BRepFeat_SplitShape": BRepFeat_SplitShape, "TopAbs_SHELL": TopAbs_SHELL,
            "TopExp_Explorer": TopExp_Explorer}


def _geom_name(face) -> str:
    gt = face.geom_type
    return gt.name if hasattr(gt, "name") else str(gt)


def _normal(face) -> np.ndarray:
    c = face.center()
    n = face.normal_at(c)
    return np.array([float(n.X), float(n.Y), float(n.Z)])


def _center(face) -> np.ndarray:
    c = face.center()
    return np.array([float(c.X), float(c.Y), float(c.Z)])


def _rect_face(bd, corners):
    return bd.Face(bd.Wire.make_polygon([bd.Vector(*map(float, q)) for q in corners], close=True))


def _rect_at(z: float, xh: float, yh: float):
    return [(-xh, -yh, z), (xh, -yh, z), (xh, yh, z), (-xh, yh, z)]


def _rect_prism_solid(bd, stations: list[tuple[float, float, float]]):
    """ONE closed polyhedron of axis-aligned rectangular cross-sections (every face a PLANE).

    The reference horn is a *flat-wall* pyramid; a build123d ``loft`` would give BSPLINE side faces,
    which the port imprint cannot split (and which the "flat wall" contract does not name). Building
    the ruled frustum + mouth roundover as planar quads keeps the walls genuinely planar and the port
    rectangle exactly on them.
    """
    faces = []
    for (z0, x0, y0), (z1, x1, y1) in zip(stations, stations[1:]):
        faces.append(_rect_face(bd, [(-x0, y0, z0), (x0, y0, z0), (x1, y1, z1), (-x1, y1, z1)]))
        faces.append(_rect_face(bd, [(x0, -y0, z0), (-x0, -y0, z0), (-x1, -y1, z1), (x1, -y1, z1)]))
        faces.append(_rect_face(bd, [(x0, y0, z0), (x0, -y0, z0), (x1, -y1, z1), (x1, y1, z1)]))
        faces.append(_rect_face(bd, [(-x0, -y0, z0), (-x0, y0, z0), (-x1, y1, z1), (-x1, -y1, z1)]))
    faces.append(_rect_face(bd, _rect_at(*stations[0])[::-1]))
    faces.append(_rect_face(bd, _rect_at(*stations[-1])))
    return bd.Solid(bd.Shell(faces))


def _air_solid(bd, p: MehParams, g: dict[str, float], over_mm: float = 2.0):
    """Horn air: rectangular pyramid frustum z=0 -> mouth, quarter-round to the front, + a prism."""
    roll = p.roll_mm
    xm, ym = g["mouth_w"] / 2.0, g["mouth_h"] / 2.0
    stations = [(0.0, g["z_c"] * g["th"], g["z_c"] * g["tv"]),
                (g["z_m"], xm, ym)]
    steps = max(1, int(math.ceil(roll / 2.5)))
    for k in range(1, steps + 1):
        th = 0.5 * math.pi * k / steps
        stations.append((g["z_m"] + roll * math.sin(th),
                         xm + roll * (1.0 - math.cos(th)),
                         ym + roll * (1.0 - math.cos(th))))
    # a short straight prism past the front plane so the boolean cuts a clean opening
    stations.append((g["z_m"] + roll + over_mm, xm + roll, ym + roll))
    return _rect_prism_solid(bd, stations)


def _find_inner_wall(part, p: MehParams, g: dict[str, float], wall: str, sign: int):
    """The solid's planar inner-wall face for ``wall``/``sign`` (geometry match, no label needed)."""
    point, _t, n, _e, _width = _wall_frame(wall, sign, g)
    c0 = point(p.z_port_mm)
    hits = []
    for face in part.faces():
        if _geom_name(face) != "PLANE":
            continue
        fn = _normal(face)
        if abs(abs(float(np.dot(fn, n))) - 1.0) > 1e-6:
            continue
        c = _center(face)
        if abs(float(np.dot(c0 - c, n))) > 1e-4:
            continue
        bb = face.bounding_box()
        if not (bb.min.Z - 1e-6 <= p.z_port_mm <= bb.max.Z + 1e-6):
            continue
        hits.append(face)
    if len(hits) != 1:
        raise RuntimeError(f"could not find the {wall}{sign:+d} inner wall face ({len(hits)} candidates)")
    return hits[0]


def _imprint_ports(bd, part, p: MehParams, g: dict[str, float]):
    """Split each surviving inner wall with its half port rectangle wire (a flush, coplanar patch).

    The quarter is cut FIRST: an OCC boolean intersection after the split merges coplanar faces and
    would silently erase the imprint. The half patch runs from the symmetry plane (``e = 0``) to
    ``port_across / 2``; its ``e = 0`` edge lies on the cut boundary, which ``BRepFeat_SplitShape``
    accepts as a notch in the wall face.
    """
    split = _cad()["BRepFeat_SplitShape"]()
    split.Init(part.wrapped)
    for wall in p.walls_list:
        face = _find_inner_wall(part, p, g, wall, 1)
        point, t, _n, e, _width = _wall_frame(wall, 1, g)
        c = point(p.z_port_mm)
        d_along = 0.5 * p.port_along_mm * np.asarray(t, dtype=float)
        d_across = 0.5 * p.port_across_mm * np.asarray(e, dtype=float)
        corners = [c - d_along, c + d_along, c + d_along + d_across, c - d_along + d_across]
        wire = bd.Wire.make_polygon([bd.Vector(*map(float, q)) for q in corners], close=True)
        split.Add(wire.wrapped, face.wrapped)
    split.Build()
    if not split.IsDone():
        raise RuntimeError("refusing: OCC could not imprint the mid-port outlines")
    return bd.Part(split.Shape())


def _quarter_cut(bd, part, p: MehParams, g: dict[str, float]):
    """Intersect the full solid with x >= 0, y >= 0 (the cut planes are removed later)."""
    front = g["z_m"] + p.roll_mm
    pad = 50.0
    big = 2.0 * max(p.env_w_mm, p.env_h_mm) + 2.0 * p.env_d_mm + 1000.0
    cutter = bd.Pos(big / 2.0, big / 2.0, front - p.env_d_mm / 2.0) * bd.Box(
        big, big, p.env_d_mm + 2.0 * pad)
    return part & cutter


def _on_cut_plane(face) -> bool:
    if _geom_name(face) != "PLANE":
        return False
    c, n = _center(face), _normal(face)
    if abs(c[0]) < 1e-4 and abs(n[0]) > 1.0 - 1e-6:
        return True
    if abs(c[1]) < 1e-4 and abs(n[1]) > 1.0 - 1e-6:
        return True
    return False


def _closed_quarter(part, p: MehParams) -> dict[str, Any]:
    """Validate the closed quarter solid before the symmetry cut faces are removed."""
    o = _cad()
    faces = list(part.faces())
    solids = list(part.solids())
    shells = []
    ex = o["TopExp_Explorer"](part.wrapped, o["TopAbs_SHELL"])
    while ex.More():
        shells.append(o["BRep_Tool"].IsClosed_s(ex.Current()))
        ex.Next()
    degenerate = [f for f in faces if f.area <= 0.0]
    report = {
        "faces": len(faces), "solids": len(solids), "volume_mm3": float(part.volume),
        "valid": bool(o["BRepCheck_Analyzer"](part.wrapped).IsValid()),
        "shells": len(shells), "all_shells_closed": bool(shells) and all(shells),
        "degenerate_faces": len(degenerate),
        "min_face_area_mm2": min((f.area for f in faces), default=0.0),
    }
    if report["solids"] != 1:
        raise RuntimeError(f"refusing: expected 1 solid, got {report['solids']}")
    if not report["valid"]:
        raise RuntimeError("refusing: the built solid is not a valid BRep")
    if not report["all_shells_closed"]:
        raise RuntimeError(f"refusing: {report['shells']} shell(s), not all closed")
    if report["degenerate_faces"]:
        raise RuntimeError(f"refusing: {report['degenerate_faces']} zero-area face(s)")
    return report


def _driver_index(faces, p: MehParams) -> int:
    r = p.exit_mm / 2.0
    area = math.pi * r * r / 4.0            # the quarter cut leaves a quarter disc
    hits = []
    for i, face in enumerate(faces):
        if _geom_name(face) != "PLANE":
            continue
        c, n = _center(face), _normal(face)
        if abs(c[2] + p.cd_duct_mm) > 0.5:
            continue
        if abs(float(n[2])) < 1.0 - 1e-6:
            continue
        if math.isclose(face.area, area, rel_tol=1e-3):
            hits.append(i)
    if len(hits) != 1:
        raise RuntimeError(f"refusing: {len(hits)} driver disc faces (need exactly 1)")
    return hits[0]


def _patch_index(faces, p: MehParams, g: dict[str, float], wall: str, sign: int) -> int:
    point, _t, n, e, _width = _wall_frame(wall, sign, g)
    expected_c = point(p.z_port_mm) + (p.port_across_mm / 4.0) * np.asarray(e, dtype=float)
    area = 0.5 * p.port_along_mm * p.port_across_mm
    hits = []
    for i, face in enumerate(faces):
        if _geom_name(face) != "PLANE":
            continue
        if not math.isclose(face.area, area, rel_tol=1e-3):
            continue
        fn = _normal(face)
        if abs(abs(float(np.dot(fn, n))) - 1.0) > 1e-6:
            continue
        if float(np.linalg.norm(_center(face) - expected_c)) > 0.5:
            continue
        hits.append(i)
    if len(hits) != 1:
        raise RuntimeError(
            f"refusing: {len(hits)} {wall}{sign:+d} mid-port patch faces (need exactly 1)")
    return hits[0]


def _labels(faces, p: MehParams, g: dict[str, float]) -> list[str]:
    driver = _driver_index(faces, p)
    entries = {_patch_index(faces, p, g, wall, 1) for wall in p.walls_list}
    labels = []
    for i, _face in enumerate(faces):
        if i == driver:
            labels.append("driver")
        elif i in entries:
            labels.append("entry_mid")
        else:
            labels.append("wall")
    return labels


def build_shell(p: MehParams):
    """Build the quarter open-shell solid; returns ``(shell, closed_quarter_report)``."""
    p.validate()
    if p.cd_duct_mm <= 0.0:
        raise ValueError("the L1 solid needs cd_duct_mm > 0: a z=0 driver disc is not modelled")
    d = check(p)
    if d["reasons"]:
        raise ValueError("layout reasons: " + ", ".join(d["reasons"]))
    o = _cad()
    bd = o["bd"]
    g = geometry(p)
    front = g["z_m"] + p.roll_mm
    box = bd.Pos(0.0, 0.0, front - p.env_d_mm / 2.0) * bd.Box(p.env_w_mm, p.env_h_mm, p.env_d_mm)
    horn = _air_solid(bd, p, g)
    bore = bd.Pos(0.0, 0.0, -p.cd_duct_mm) * bd.Cylinder(
        p.exit_mm / 2.0, p.cd_duct_mm + 2.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    part = box - horn - bore
    part = _quarter_cut(bd, part, p, g)
    part = _imprint_ports(bd, part, p, g)
    report = _closed_quarter(part, p)
    faces = list(part.faces())
    keep = [f for f in faces if not _on_cut_plane(f)]
    if not keep:
        raise RuntimeError("refusing: the quarter cut removed every face")
    return bd.Shell(keep), report


def _write_labelled_step(part, labels, path: Path) -> Path:
    """Write STEP with one named presentation style per face (the multicell contract, 4 labels)."""
    o = _cad()
    labels = list(labels)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = o["STEPControl_Writer"]()
    with _multicell()._quiet_occ():
        status = writer.Transfer(part.wrapped, o["STEPControl_StepModelType"].STEPControl_AsIs)
    if "RetDone" not in str(status):
        raise RuntimeError(f"refusing: STEP transfer failed ({status})")
    styles = o["STEPConstruct_Styles"]()
    styles.Init(writer.WS())
    model = writer.Model()
    colours = {
        label: o["Quantity_Color"](*rgb, o["Quantity_TypeOfColor"].Quantity_TOC_RGB)
        for label, rgb in _LABEL_COLOURS.items()
    }
    encoded = {label: o["STEPConstruct_Styles"].EncodeColor_s(colour)
               for label, colour in colours.items()}
    for face, label in zip(part.faces(), labels):
        probe = styles.AddStyle(face.wrapped, o["StepVisual_PresentationStyleAssignment"](), None)
        if probe is None:
            raise RuntimeError("refusing: OCC could not map a face onto its STEP entity")
        item = probe.Item()
        colour = colours[label]
        psa_full = styles.MakeColorPSA(
            item, encoded[label], encoded[label],
            o["STEPConstruct_RenderingProperties"](colour), False)
        psa = o["StepVisual_PresentationStyleAssignment"]()
        styles_array = o["HArray1_StepVisual_PresentationStyleSelect"](1, 1)
        styles_array.SetValue(1, psa_full.Styles().Value(1))
        psa.SetStyles(styles_array)
        styled = styles.AddStyle(item, psa, None)
        styled.SetName(o["TCollection_HAsciiString"](label))
        model.AddWithRefs(styled)
    with _multicell()._quiet_occ():
        status = writer.Write(str(path))
    if "RetDone" not in str(status):
        path.unlink(missing_ok=True)
        raise RuntimeError(f"refusing: STEP write failed ({status})")
    return path


def read_face_inventory(path: Path) -> dict[str, int]:
    """Label -> face count of a written MEH STEP, as ``hornlab_mesher.step_text`` sees it."""
    parser = _multicell().step_text_module()
    path = Path(path)
    text = parser.read_step_text(path)
    bodies = parser.step_body_inventory(text)
    if len(bodies) != 1:
        raise RuntimeError(f"refusing: STEP has {len(bodies)} bodies, expected exactly 1")
    body = bodies[0]
    if body.kind not in ("solid", "surface"):
        raise RuntimeError(f"refusing: STEP body is {body.kind!r}, not a solid/surface model")
    unit = parser.step_length_unit_mm_from_text(text)
    if unit is None or abs(unit - 1.0) > 1e-9:
        raise RuntimeError(f"refusing: STEP length unit is {unit} mm, expected 1.0")
    styled = parser.parse_styled_face_groups(path)
    per_face: dict[int, list[str]] = {}
    for label, face_ids in styled.items():
        if label not in LABELS:
            raise RuntimeError(f"refusing: STEP carries an unlabelled-group name {label!r}")
        for face_id in face_ids:
            per_face.setdefault(int(face_id), []).append(label)
    solid_faces = (set(int(i) for i in body.face_ids) if body.kind == "surface"
                   else set(int(i) for i in parser.parse_solid_brep_faces(path)))
    stray = set(per_face) - solid_faces
    unlabelled = solid_faces - set(per_face)
    if stray:
        raise RuntimeError(f"refusing: {len(stray)} labelled face(s) outside the body")
    if unlabelled:
        raise RuntimeError(f"refusing: {len(unlabelled)} of {len(solid_faces)} faces carry no label")
    doubled = {f: tags for f, tags in per_face.items() if len(tags) != 1}
    if doubled:
        raise RuntimeError(f"refusing: {len(doubled)} face(s) carry more than one label")
    inventory: dict[str, int] = {}
    for tags in per_face.values():
        inventory[tags[0]] = inventory.get(tags[0], 0) + 1
    if inventory.get("driver", 0) != 1:
        raise RuntimeError(f"refusing: STEP must carry exactly one 'driver' face, found "
                           f"{inventory.get('driver', 0)}")
    return dict(sorted(inventory.items()))


def export(path: Path, params: dict[str, Any] | MehParams = DEFAULTS) -> dict[str, Any]:
    """Build, check, write and round-trip one MEH STEP."""
    p = params_from_recipe(params) if not isinstance(params, MehParams) else params
    d = check(p)
    if d["reasons"]:
        raise ValueError("layout reasons: " + ", ".join(d["reasons"]))
    shell, solid = build_shell(p)
    labels = _labels(list(shell.faces()), p, geometry(p))
    _write_labelled_step(shell, labels, path)
    try:
        inventory = read_face_inventory(path)
    except RuntimeError:
        Path(path).unlink(missing_ok=True)
        raise
    expected_entry = len(p.walls_list)          # one surviving (+1) port per used wall
    if inventory.get("driver", 0) != 1:
        Path(path).unlink(missing_ok=True)
        raise RuntimeError(f"refusing: inventory {inventory} is not one driver face")
    if inventory.get("entry_mid", 0) != expected_entry:
        Path(path).unlink(missing_ok=True)
        raise RuntimeError(
            f"refusing: inventory {inventory} has {inventory.get('entry_mid', 0)} entry_mid "
            f"face(s), expected {expected_entry} (one half port per used wall)")
    if set(inventory) - set(LABELS):
        Path(path).unlink(missing_ok=True)
        raise RuntimeError(f"refusing: inventory {inventory} carries an unknown label")
    if sum(inventory.values()) != len(list(shell.faces())):
        Path(path).unlink(missing_ok=True)
        raise RuntimeError(
            f"refusing: STEP labels {sum(inventory.values())} faces but the shell has "
            f"{len(list(shell.faces()))}")
    return {"params": p, "derived": d, "solid": solid, "part": shell,
            "inventory": inventory, "path": Path(path)}


def build(recipe: dict[str, Any], step_path: Path) -> dict[str, Any]:
    """Public entry: recipe -> labelled quarter STEP (mm) + the tool's own report."""
    return export(Path(step_path), params_from_recipe(recipe))


# ---------------------------------------------------------------------- CLI


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="meh.py", description=(__doc__ or "MEH L1 CAD tool").splitlines()[0],
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--out", required=True, help="STEP path")
    for f in fields(MehParams):
        if f.name in ("z_port_mm", "port_across_mm", "repairs"):
            continue
        if f.name == "walls":
            ap.add_argument("--walls", default=f.default, choices=("tb", "lr", "tblr"))
        else:
            ap.add_argument("--" + f.name.replace("_", "-"), type=float, default=f.default)
    return ap


def main(argv=None) -> int:
    a = _parser().parse_args(argv)
    recipe = {"tool": "meh"}
    for f in fields(MehParams):
        if f.name in ("z_port_mm", "port_across_mm", "repairs"):
            continue
        recipe[f.name] = getattr(a, f.name)
    try:
        result = build(recipe, Path(a.out))
    except (ValueError, RuntimeError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result["derived"], indent=1, sort_keys=True, default=float))
    print("solid:", result["solid"])
    print("face inventory (round-tripped STEP):", result["inventory"])
    print(f"wrote {result['path']} ({result['path'].stat().st_size} bytes)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
