"""Legal keys per family, validation, and the Design -> hornlab_mesher config dict.

The mesher's parameter names ARE the contract (01_CONTRACTS section 5); nothing here renames
them. A Design carries the family and a dict in the mesher's own keys and units (mm / deg).

Tables below were populated from 01_CONTRACTS section 5 and checked against the on-disk
``hornlab_mesher`` ``docs/config-schema.md``. The file on disk wins. A key that is not in a
family's table is REJECTED, not passed through: the mesher itself silently ignores unknown
profile keys (measured: ``bogus_key`` builds fine), which is exactly why we must not.

Adding a key is a one-line table edit. ``lo`` / ``hi`` are HARD schema limits only (for example
``s1`` in 0..10, a superellipse exponent in 2..16), never rule-of-thumb plausibility limits:
nothing in the optimizer may refuse a design on a rule of thumb (contracts section 3).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from ..types import Design, GeometryInvalidError, MeshSpec

# ------------------------------------------------------------------ key tables


@dataclass(frozen=True)
class KeySpec:
    kind: type                 # float | int | str | list | dict | bool
    lo: float | None = None    # hard schema limit, inclusive; None = unbounded
    hi: float | None = None
    note: str = ""
    section: str = "profile"   # where the mesher config wants it: top | profile | cross_section |
    #                            mesh | morph | gcurve | enclosure | source
    choices: tuple | None = None   # legal values for str keys


def _f(lo=None, hi=None, note="", section="profile") -> KeySpec:
    return KeySpec(float, lo, hi, note, section)


def _i(lo=None, hi=None, note="", section="profile") -> KeySpec:
    return KeySpec(int, lo, hi, note, section)


MODES = ("freestanding", "free-standing", "free", "bare", "inner", "open",
         "infinite-baffle", "ib", "baffle", "enclosure", "enclosed")

# -- keys shared by every OSSE-like family (OSSE, R-OSSE): throat + cross section
_THROAT = {
    "r0_mm": _f(note="throat radius, mm"),
    "a_deg": _f(note="coverage half-angle, deg (mesher convention)"),
    "a0_deg": _f(note="throat half-angle, deg"),
    "k": _f(note="OS/R-OSSE k"),
    "q": _f(note="termination q (> 0 while s != 0 for OSSE)"),
    "s1": _f(0.0, 10.0, "throat stretch, mm/deg; plain finite number only"),
    "s2": _f(0.0, 10.0, "throat stretch, 1/mm; plain finite number only"),
    "throat_ext_length_mm": _f(note="throat extension length, mm"),
    "throat_ext_angle_deg": _f(note="throat extension angle, deg"),
    "slot_length_mm": _f(note="slot length, mm"),
}
_CROSS = {
    "exponent": _f(note="superellipse exponent of the cross section", section="cross_section"),
    "aspect_ratio": _f(note="width-to-height scaling", section="cross_section"),
}
_COMMON = {
    "mode": KeySpec(str, note="mesher build mode", section="top", choices=MODES),
    "wall_thickness_mm": _f(0.0, None, "freestanding shell thickness, mm", section="mesh"),
}
_MORPH = {
    "morph_target": _i(0, 3, "0 none, 1 rectangle, 2 circle, 3 superellipse", section="morph"),
    "morph_width_mm": _f(note="full target width, mm; 0 = implicit mouth extent", section="morph"),
    "morph_height_mm": _f(note="full target height, mm; 0 = implicit mouth extent", section="morph"),
    "morph_corner_mm": _f(note="target corner radius, mm", section="morph"),
    "morph_exponent": _f(2.0, 16.0, "superellipse exponent for morph target 3", section="morph"),
    "morph_rate": _f(0.0, None, "morph rate, >= 0 (Ath documents >= 1)", section="morph"),
    "morph_fixed": _f(note="fixed part, 0..1", section="morph"),
    "morph_allow_shrinkage": _i(note="0/1", section="morph"),
}
_GCURVE = {
    "gcurve_type": _i(note="0 off, 1 superellipse, 2 superformula", section="gcurve"),
    "gcurve_width_mm": _f(section="gcurve"),
    "gcurve_aspect_ratio": _f(section="gcurve"),
    "gcurve_dist": _f(section="gcurve"),
    "gcurve_rot_deg": _f(section="gcurve"),
    "gcurve_sf": KeySpec(str, section="gcurve", note="superformula expression string"),
    "gcurve_se_n": _f(section="gcurve"),
    "gcurve_sf_a": _f(section="gcurve"),
    "gcurve_sf_b": _f(section="gcurve"),
    "gcurve_sf_m1": _f(section="gcurve"),
    "gcurve_sf_m2": _f(section="gcurve"),
    "gcurve_sf_n1": _f(section="gcurve"),
    "gcurve_sf_n2": _f(section="gcurve"),
    "gcurve_sf_n3": _f(section="gcurve"),
}

# Per-azimuth ("per-direction") OSSE laws, the Ath CORE construction (at-horns.eu/core.html):
#   a(p) = a_deg + az_a_sf_amp * SF(p) + az_a_cos_amp * |cos p|^az_a_cos_pow
#   n(p) = n + az_n_cos2_amp * cos^2 p          s(p) = s + az_s_cos2_amp * cos^2 p
# with the Gielis superformula SF(p) = (|cos(m p/4)/a|^n2 + |sin(m p/4)/b|^n3)^(-1/n1).
# CORE itself is a_deg 5, sf amp 35 (m 4, n1 12, n2 15, n3 16, a 1, b 0.618), cos amp -15 pow 10,
# n 6 + 1.5 cos^2, s 0.6 + 0.23 cos^2 -> a = 25.0 / 33.8 / 23.4 deg at p = 0 / 45 / 90 deg: the
# wider diagonals fold the walls into the creases. These keys never reach the mesher as keys:
# to_mesher_config turns them into the mesher's own p-expressions for a, n and s. All absent or
# zero = the plain numeric a/n/s (byte-identical). m is a multiple of 4 so every law keeps the
# quarter-model mirror symmetry.
_AZLAW = {
    "az_a_sf_amp": _f(-60.0, 60.0, "superformula term amplitude on the wall angle a, deg", section="azlaw"),
    "az_sf_m": _f(4.0, 12.0, "superformula lobes m (a multiple of 4)", section="azlaw"),
    "az_sf_n1": _f(0.1, 40.0, "superformula n1 (overall sharpness)", section="azlaw"),
    "az_sf_n2": _f(0.1, 40.0, "superformula n2 (cosine-term exponent)", section="azlaw"),
    "az_sf_n3": _f(0.1, 40.0, "superformula n3 (sine-term exponent)", section="azlaw"),
    "az_sf_a": _f(0.05, 5.0, "superformula a (cosine-term scale)", section="azlaw"),
    "az_sf_b": _f(0.05, 5.0, "superformula b (sine-term scale)", section="azlaw"),
    "az_a_cos_amp": _f(-60.0, 60.0, "|cos p|^pow term amplitude on a, deg", section="azlaw"),
    "az_a_cos_pow": _f(0.5, 40.0, "|cos p| exponent of that term", section="azlaw"),
    "az_n_cos2_amp": _f(-10.0, 10.0, "cos^2 p term on the termination n", section="azlaw"),
    "az_s_cos2_amp": _f(-1.0, 1.0, "cos^2 p term on the termination s", section="azlaw"),
}
AZLAW_DEFAULTS = {"az_sf_m": 4.0, "az_sf_n1": 2.0, "az_sf_n2": 2.0, "az_sf_n3": 2.0,
                  "az_sf_a": 1.0, "az_sf_b": 1.0, "az_a_cos_pow": 2.0}


def _num(v: float) -> str:
    return repr(float(v))


def azlaw_expressions(params: dict) -> dict:
    """The mesher p-expressions for a / n / s from the az_* knobs (radians, Python syntax the
    mesher's expression evaluator accepts). Returns {} when every az amplitude is 0/absent."""
    g = {**AZLAW_DEFAULTS, **{k: v for k, v in params.items() if k in _AZLAW}}
    amp_sf = float(g.get("az_a_sf_amp", 0.0))
    amp_cos = float(g.get("az_a_cos_amp", 0.0))
    amp_n = float(g.get("az_n_cos2_amp", 0.0))
    amp_s = float(g.get("az_s_cos2_amp", 0.0))
    out: dict = {}
    if amp_sf or amp_cos:
        terms = [_num(params.get("a_deg", 60.0))]
        if amp_sf:
            m4 = _num(float(g["az_sf_m"]) / 4.0)
            sf = (f"(abs(cos({m4}*p)/{_num(g['az_sf_a'])})**{_num(g['az_sf_n2'])} + "
                  f"abs(sin({m4}*p)/{_num(g['az_sf_b'])})**{_num(g['az_sf_n3'])})"
                  f"**({_num(-1.0 / float(g['az_sf_n1']))})")
            terms.append(f"{_num(amp_sf)}*{sf}")
        if amp_cos:
            terms.append(f"{_num(amp_cos)}*abs(cos(p))**{_num(g['az_a_cos_pow'])}")
        out["a_deg"] = " + ".join(terms)
    if amp_n:
        out["n"] = f"{_num(params.get('n', 4.0))} + {_num(amp_n)}*cos(p)**2"
    if amp_s:
        out["s"] = f"{_num(params.get('s', 0.0))} + {_num(amp_s)}*cos(p)**2"
    return out


def azlaw_values(params: dict, p_rad: float) -> dict:
    """a / n / s at one azimuth (for validation and docs), plain floats."""
    from math import cos, sin
    g = {**AZLAW_DEFAULTS, **{k: v for k, v in params.items() if k in _AZLAW}}
    a = float(params.get("a_deg", 60.0))
    if float(g.get("az_a_sf_amp", 0.0)):
        m4 = float(g["az_sf_m"]) / 4.0
        base = (abs(cos(m4 * p_rad) / g["az_sf_a"]) ** g["az_sf_n2"]
                + abs(sin(m4 * p_rad) / g["az_sf_b"]) ** g["az_sf_n3"])
        a += float(g["az_a_sf_amp"]) * base ** (-1.0 / float(g["az_sf_n1"]))
    if float(g.get("az_a_cos_amp", 0.0)):
        a += float(g["az_a_cos_amp"]) * abs(cos(p_rad)) ** float(g["az_a_cos_pow"])
    n = float(params.get("n", 4.0)) + float(g.get("az_n_cos2_amp", 0.0)) * cos(p_rad) ** 2
    s = float(params.get("s", 0.0)) + float(g.get("az_s_cos2_amp", 0.0)) * cos(p_rad) ** 2
    return {"a_deg": a, "n": n, "s": s}


_OSSE = {
    **_THROAT, **_CROSS, **_COMMON, **_MORPH, **_GCURVE, **_AZLAW,
    "L_mm": _f(note="axial length, mm (OSSE only)"),
    "n": _f(note="termination n (> 0 while s != 0)"),
    "s": _f(note="termination s"),
    "rot_deg": _f(note="rotation, deg (OSSE only)"),
    "h": _f(note="half-sine bulge, mm"),
    # Opt-in L1 MEH mid-port patches on native OSSE walls (mesher fork mid_ports).
    # Absent = byte-identical mesher config / mesh. Emitted as top-level mid_ports.
    "mid_ports": KeySpec(
        dict,
        note="walls/z_frac/across_frac/port_along_mm/slide_mm -> tag 10 flush exits",
        section="top",
    ),
}

_ROSSE = {
    **_THROAT, **_CROSS, **_COMMON, **_MORPH,
    "R_mm": _f(note="mouth radius, mm (R-OSSE only)"),
    "tmax": _f(note="truncation parameter, > 0"),
    "m": _f(note="R-OSSE m"),
    "r": _f(note="R-OSSE r"),
    "b": _f(note="R-OSSE b"),
}

_ICW = {
    **_COMMON, **_MORPH,
    "termination": KeySpec(str, note="categorical; cannot take a lo/hi bound", section="profile",
                           choices=("flat_baffle", "rollback")),
    "r0_mm": _f(note="throat radius, mm"),
    "a0_deg": _f(note="throat half-angle, deg"),
    "L_mm": _f(note="axial length, mm"),
    "R_mm": _f(note="mouth radius, mm"),
    "coverage_angle_deg": _f(0.0, None, "ICW wall half-angle (mesher enforces theta0_deg < coverage_angle_deg < 90.0); target coverage_*_deg is the TOTAL included angle"),
    "hold_start": _f(0.0, 1.0),
    "hold_end": _f(0.0, 1.0),
    "kappa0": _f(note="initial curvature, 1/mm"),
    "theta1_deg": _f(note="theta1, deg"),
    "n_coeff": _i(note="ICW basis size"),
    "kappa_abs_max": _f(),
    "dkappa_ds_abs_max": _f(),
    "theta_max_deg": _f(),
    "pin_mouth_radius": KeySpec(bool),
    "icw_seed": KeySpec(dict, note="seed formula the ICW curve is fitted to"),
    "icw_coeffs": KeySpec(list),
    "icw_S": _f(),
}

_FREEFORM = {
    **_COMMON, **_MORPH,
    "profileH": KeySpec(dict, note="{points, throatAngleDeg, mouthAngleDeg}, horizontal meridian"),
    "profileV": KeySpec(dict, note="{points, throatAngleDeg, mouthAngleDeg}, vertical meridian"),
    "crossSections": KeySpec(list, note="2..32 stations {t, shape, [exponent|cornerRadiusMm]}"),
    "inflectionPolicy": KeySpec(str, choices=("warn", "reject")),
}

FAMILY_KEYS: dict[str, dict[str, KeySpec]] = {
    "OSSE": _OSSE,
    "R-OSSE": _ROSSE,
    "ICW": _ICW,
    "FREEFORM": _FREEFORM,
}

# Keys the mesher refuses for a family, with the reason the schema gives. Checked BEFORE the
# generic "unknown key" rejection so the user gets the real explanation.
_REFUSED_HINTS: dict[str, dict[str, str]] = {
    "R-OSSE": {
        "rot_deg": "R-OSSE does not support rot_deg (OSSE only)",
        "L_mm": "R-OSSE does not support an explicit L_mm (use R_mm; OSSE only)",
        "n": "n is an OSSE-only key",
        "s": "s is an OSSE-only key",
        "h": "h is an OSSE-only key",
    },
    "OSSE": {
        "R_mm": "R_mm is an R-OSSE-only key",
        "tmax": "tmax is an R-OSSE-only key",
        "m": "m is an R-OSSE-only key",
        "r": "r is an R-OSSE-only key",
        "b": "b is an R-OSSE-only key",
    },
}
_ICW_OSSE_SHAPE = ("a_deg", "n", "s", "q", "k", "h", "rot_deg", "s1", "s2", "tmax", "m", "r", "b",
                   "exponent", "aspect_ratio", "throat_ext_length_mm", "throat_ext_angle_deg",
                   "slot_length_mm")
for _k in _ICW_OSSE_SHAPE:
    _REFUSED_HINTS.setdefault("ICW", {})[_k] = (
        f"ICW rejects the OSSE/R-OSSE shape key '{_k}' at the top level "
        "(put an OSSE/R-OSSE seed inside icw_seed instead)")
for _k in ("sampling_mode", "z_map_points", "zmap"):
    _REFUSED_HINTS["ICW"][_k] = f"ICW rejects zmap sampling ('{_k}'); it samples uniformly in arc length"
_REFUSED_HINTS["FREEFORM"] = {
    k: f"FREEFORM refuses '{k}': crossSections / the two meridians own the outline"
    for k in ("exponent", "aspect_ratio", "rot_deg", "h", "s1", "s2", "throat_ext_length_mm",
              "throat_ext_angle_deg", "slot_length_mm", "gcurve_type")
}

# FREEFORM bare-key aliases. The shipped examples/freeform_hv.yaml bounds a bare ``exponent``;
# the value lives in the superellipse station of ``crossSections`` (task 04 owns this mapping).
FREEFORM_ALIASES = {"exponent"}

_FF_PROFILE_KEYS = {"points", "throatAngleDeg", "mouthAngleDeg"}
_FF_SHAPES = ("circle", "ellipse", "superellipse", "rounded_rectangle")

# ------------------------------------------------------------------ small helpers


def _isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def _bad(family: str, key: str, why: str) -> GeometryInvalidError:
    return GeometryInvalidError(f"{family}: key '{key}': {why}")


def legal_roots(family: str) -> set[str]:
    return set(FAMILY_KEYS[family])


# ------------------------------------------------------------------ param paths


def resolve_path(family: str, params: dict, key: str) -> tuple:
    """Turn a search key into a path of dict keys / list indices into ``params``.

    - a key present at the top level is itself;
    - ``a.b.0.c`` walks dicts by name and lists by integer index;
    - for FREEFORM, a bare ``exponent`` is the first superellipse station in ``crossSections``.
    Raises KeyError if the path does not exist (the caller decides what that means).
    """
    if key in params:
        return (key,)
    if family == "FREEFORM" and key in FREEFORM_ALIASES:
        for i, st in enumerate(params.get("crossSections", [])):
            if isinstance(st, dict) and st.get("shape") == "superellipse":
                return ("crossSections", i, key)
        raise KeyError(f"no superellipse station in crossSections for '{key}'")
    if "." in key:
        parts = []
        node = params
        for tok in key.split("."):
            if isinstance(node, dict):
                if tok not in node:
                    raise KeyError(key)
                parts.append(tok)
                node = node[tok]
            elif isinstance(node, (list, tuple)):
                try:
                    i = int(tok)
                    node = node[i]
                except (ValueError, IndexError):
                    raise KeyError(key) from None
                parts.append(i)
            else:
                raise KeyError(key)
        return tuple(parts)
    raise KeyError(key)


def param_get(family: str, params: dict, key: str):
    node = params
    for step in resolve_path(family, params, key):
        node = node[step]
    return node


def param_set(family: str, params: dict, key: str, value) -> None:
    """In-place set along the same path ``param_get`` reads."""
    path = resolve_path(family, params, key)
    node = params
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value


def root_key(key: str) -> str:
    return key.split(".", 1)[0]


# ------------------------------------------------------------------ validation


def _check_value(family: str, key: str, spec: KeySpec, v) -> None:
    if spec.kind is float:
        if not _isnum(v):
            raise _bad(family, key, f"must be a finite number, got {v!r}")
    elif spec.kind is int:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or float(v) != int(v):
            raise _bad(family, key, f"must be an integer, got {v!r}")
    elif spec.kind is str:
        if not isinstance(v, str):
            raise _bad(family, key, f"must be a string, got {v!r}")
        if spec.choices is not None and v.strip().lower() not in spec.choices:
            raise _bad(family, key, f"must be one of {list(spec.choices)}, got {v!r}")
    elif spec.kind is bool:
        if not isinstance(v, bool):
            raise _bad(family, key, f"must be a bool, got {v!r}")
    elif spec.kind is list:
        if not isinstance(v, (list, tuple)):
            raise _bad(family, key, f"must be a list, got {type(v).__name__}")
    elif spec.kind is dict:
        if not isinstance(v, dict):
            raise _bad(family, key, f"must be a mapping, got {type(v).__name__}")
    if spec.kind in (float, int):
        if spec.lo is not None and float(v) < spec.lo:
            raise _bad(family, key, f"{v!r} is below the schema minimum {spec.lo}")
        if spec.hi is not None and float(v) > spec.hi:
            raise _bad(family, key, f"{v!r} is above the schema maximum {spec.hi}")


def _validate_osse_like(design: Design) -> None:
    p = design.params
    fam = design.family
    if any(k in p for k in _AZLAW):
        m = float(p.get("az_sf_m", AZLAW_DEFAULTS["az_sf_m"]))
        if abs(m / 4.0 - round(m / 4.0)) > 1e-9:
            raise _bad(fam, "az_sf_m", f"must be a multiple of 4 (quarter-model symmetry), got {m!r}")
        import math as _m
        for deg in range(0, 91, 3):                     # the whole law, sampled per 3 degrees
            v = azlaw_values(p, _m.radians(deg))
            if not (0.5 <= v["a_deg"] <= 89.5) or not _m.isfinite(v["a_deg"]):
                raise _bad(fam, "az_a_sf_amp", f"the per-direction wall angle a({deg} deg) = "
                                               f"{v['a_deg']:.2f} leaves (0.5, 89.5) deg")
            if v["s"] != 0 and v["n"] <= 0:
                raise _bad(fam, "az_n_cos2_amp", f"n({deg} deg) = {v['n']:.3f} must stay > 0")
    if fam == "OSSE":
        s = p.get("s", 0.0)
        if s != 0:
            n = p.get("n", 4.0)
            q = p.get("q", 0.995)
            if n <= 0:
                raise _bad(fam, "n", f"must be > 0 while s != 0, got {n!r}")
            if q <= 0:
                raise _bad(fam, "q", f"must be > 0 while s != 0, got {q!r}")
        if "L_mm" in p and p["L_mm"] <= 0:
            raise _bad(fam, "L_mm", f"must be > 0, got {p['L_mm']!r}")
    if fam == "R-OSSE":
        if "tmax" in p and p["tmax"] <= 0:
            raise _bad(fam, "tmax", f"must be > 0, got {p['tmax']!r}")
        if "R_mm" in p and p["R_mm"] <= 0:
            raise _bad(fam, "R_mm", f"must be > 0, got {p['R_mm']!r}")
    if "r0_mm" in p and p["r0_mm"] <= 0:
        raise _bad(fam, "r0_mm", f"must be > 0, got {p['r0_mm']!r}")
    if fam == "OSSE" and "mid_ports" in p:
        _validate_mid_ports(p["mid_ports"], fam)


def _validate_mid_ports(raw, fam: str) -> None:
    """Light schema check; the mesher fork refuses bad values at build time."""
    if not isinstance(raw, dict):
        raise _bad(fam, "mid_ports", "must be a mapping")
    legal = {"walls", "z_frac", "across_frac", "port_along_mm", "slide_mm"}
    unknown = set(raw) - legal
    if unknown:
        raise _bad(fam, "mid_ports", f"unknown key(s) {sorted(unknown)} (legal: {sorted(legal)})")
    for req in ("walls", "z_frac", "across_frac", "port_along_mm"):
        if req not in raw:
            raise _bad(fam, f"mid_ports.{req}", "required when mid_ports is present")
    walls = str(raw["walls"]).strip().lower()
    if walls not in ("tb", "lr", "tblr"):
        raise _bad(fam, "mid_ports.walls", f"must be tb|lr|tblr, got {raw['walls']!r}")
    zf = float(raw["z_frac"])
    if not 0.0 < zf < 1.0:
        raise _bad(fam, "mid_ports.z_frac", f"must be in (0, 1), got {zf!r}")
    af = float(raw["across_frac"])
    if not 0.0 < af <= 1.0:
        raise _bad(fam, "mid_ports.across_frac", f"must be in (0, 1], got {af!r}")
    if not float(raw["port_along_mm"]) > 0.0:
        raise _bad(fam, "mid_ports.port_along_mm",
                   f"must be > 0, got {raw['port_along_mm']!r}")


def _validate_icw(design: Design) -> None:
    p = design.params
    hs, he = p.get("hold_start"), p.get("hold_end")
    if hs is not None and he is not None and not hs < he:
        raise _bad("ICW", "hold_start", f"must be < hold_end ({hs!r} vs {he!r})")


def _validate_profile(name: str, prof) -> list:
    fam = "FREEFORM"
    if not isinstance(prof, dict):
        raise _bad(fam, name, "must be a mapping with 'points'")
    unknown = set(prof) - _FF_PROFILE_KEYS
    if unknown:
        raise _bad(fam, name, f"unknown profile key(s) {sorted(unknown)} "
                              f"(legal: {sorted(_FF_PROFILE_KEYS)})")
    pts = prof.get("points")
    if not isinstance(pts, (list, tuple)) or not 2 <= len(pts) <= 64:
        raise _bad(fam, f"{name}.points", "must be a list of 2 to 64 rows")
    last_z = -math.inf
    for i, row in enumerate(pts):
        if not isinstance(row, (list, tuple)) or len(row) not in (2, 3) \
                or not all(_isnum(x) for x in row):
            raise _bad(fam, f"{name}.points[{i}]", f"row must be [z, r] or [z, r, angleDeg], got {row!r}")
        z, r = float(row[0]), float(row[1])
        if r <= 0:
            raise _bad(fam, f"{name}.points[{i}]", f"radius must be positive, got {r!r}")
        if not z > last_z:
            raise _bad(fam, f"{name}.points[{i}]",
                       f"z must be strictly increasing (z={z!r} follows {last_z!r})")
        last_z = z
    for ak in ("throatAngleDeg", "mouthAngleDeg"):
        if ak in prof:
            if not _isnum(prof[ak]) or not -90.0 <= float(prof[ak]) <= 90.0:
                raise _bad(fam, f"{name}.{ak}", f"must be in [-90, 90], got {prof[ak]!r}")
    return pts


def _validate_freeform(design: Design) -> None:
    fam = "FREEFORM"
    p = design.params
    for name in ("profileH", "profileV"):
        if name not in p:
            raise _bad(fam, name, "required")
    ptsH = _validate_profile("profileH", p["profileH"])
    ptsV = _validate_profile("profileV", p["profileV"])
    if abs(float(ptsH[0][0]) - float(ptsV[0][0])) > 1e-9 or abs(float(ptsH[-1][0]) - float(ptsV[-1][0])) > 1e-9:
        raise _bad(fam, "profileV", "first and last z must match profileH")
    if abs(float(ptsH[0][1]) - float(ptsV[0][1])) > 1e-6:
        raise _bad(fam, "profileV", "first radius must match profileH (shared throat)")
    cs = p.get("crossSections")
    if cs is None:
        return
    if not 2 <= len(cs) <= 32:
        raise _bad(fam, "crossSections", f"needs 2 to 32 stations, got {len(cs)}")
    last_t = -math.inf
    for i, st in enumerate(cs):
        where = f"crossSections[{i}]"
        if not isinstance(st, dict) or "t" not in st or "shape" not in st:
            raise _bad(fam, where, "station must be a mapping with 't' and 'shape'")
        t = st["t"]
        if not _isnum(t) or not 0.0 <= float(t) <= 1.0:
            raise _bad(fam, f"{where}.t", f"must be in [0, 1], got {t!r}")
        if not float(t) > last_t:
            raise _bad(fam, f"{where}.t", f"must be strictly increasing (t={t!r} follows {last_t!r})")
        last_t = float(t)
        shape = st["shape"]
        if shape not in _FF_SHAPES:
            raise _bad(fam, f"{where}.shape", f"must be one of {list(_FF_SHAPES)}, got {shape!r}")
        if shape == "superellipse" and "exponent" in st:
            e = st["exponent"]
            if not _isnum(e) or not 2.0 <= float(e) <= 16.0:
                raise _bad(fam, f"{where}.exponent", f"superellipse exponent must be in [2, 16], got {e!r}")
        if shape == "rounded_rectangle":
            c = st.get("cornerRadiusMm")
            if not _isnum(c) or float(c) <= 0:
                raise _bad(fam, f"{where}.cornerRadiusMm", f"required and positive, got {c!r}")
    if float(cs[0]["t"]) != 0.0 or float(cs[-1]["t"]) != 1.0:
        raise _bad(fam, "crossSections", "first station must be t=0 and last t=1")
    if cs[0]["shape"] not in ("circle", "ellipse"):
        raise _bad(fam, "crossSections[0].shape", "first shape must be circle or ellipse")


def validate(design: Design) -> None:
    """Raise GeometryInvalidError naming the offending key. No guessing: a key not in the
    family's table is rejected, not passed through.

    WP10: a ``FREEFORM`` design whose params carry ``"grid"`` is the point-grid adapter. The
    family literal stays FREEFORM (frozen contract), but the params are a grid spec, not anchors,
    so the grid schema validates them (``generators.grid.validate_grid_params``) instead of
    ``_validate_freeform``.

    WP14: the same for a ``FREEFORM`` design whose params carry ``"cad"`` -- a labelled-STEP
    recipe for ``mesh/step_build.py`` (``tool: multicell``), validated by
    ``step_build.validate_cad_params``. The family literal stays FREEFORM, and a cad Design
    carries ONLY ``cad`` (exactly like a grid Design carries only ``grid``).
    """
    fam = design.family
    if fam not in FAMILY_KEYS:
        raise GeometryInvalidError(f"unknown family {fam!r}; legal: {list(FAMILY_KEYS)}")
    table = FAMILY_KEYS[fam]
    if not isinstance(design.params, dict):
        raise GeometryInvalidError(f"{fam}: params must be a dict")
    if "grid" in design.params:
        if fam != "FREEFORM":
            raise GeometryInvalidError(
                f"{fam}: a grid design must use family FREEFORM (got {fam!r})")
        from .generators import grid as grid_gen            # lazy: generators import this pkg
        extra = sorted(k for k in design.params if k != "grid")
        if extra:
            raise _bad(fam, extra[0], "not a grid design key (a grid Design carries only 'grid')")
        try:
            grid_gen.validate_grid_params(design.params["grid"])
        except grid_gen.registry.GeneratorError as exc:
            raise GeometryInvalidError(f"{fam}.grid: {exc}") from exc
        return
    if "cad" in design.params:
        if fam != "FREEFORM":
            raise GeometryInvalidError(
                f"{fam}: a cad design must use family FREEFORM (got {fam!r})")
        from ..mesh import step_build as cad_mod             # lazy: mesh imports this package
        extra = sorted(k for k in design.params if k != "cad")
        if extra:
            raise _bad(fam, extra[0], "not a cad design key (a cad Design carries only 'cad')")
        try:
            cad_mod.validate_cad_params(design.params["cad"])
        except cad_mod.CadParamsError as exc:
            raise GeometryInvalidError(f"{fam}.cad: {exc}") from exc
        return
    hints = _REFUSED_HINTS.get(fam, {})
    for key in design.params:
        if key in table:
            continue
        if key in hints:
            raise _bad(fam, key, hints[key])
        raise _bad(fam, key, f"not a legal {fam} key (legal: {sorted(table)})")
    for key, v in design.params.items():
        _check_value(fam, key, table[key], v)
    if fam in ("OSSE", "R-OSSE"):
        _validate_osse_like(design)
    elif fam == "ICW":
        _validate_icw(design)
    elif fam == "FREEFORM":
        _validate_freeform(design)


# ------------------------------------------------------------------ enclosure (WP12)

#: SEARCH-side mounting plan token -> the mesher's own ``plan_type``. Only the rounded rectangle
#: has a watertight closed/reduced-domain enclosure builder (hornlab_mesher
#: builders/enclosure.py); config.py refuses every other token at load time.
MOUNTING_PLANS = {"rounded_rectangle": 1}


def enclosure_section(mounting: dict) -> dict:
    """Normalized ``brief.mounting`` -> the mesher's own top-level ``enclosure`` section.

    ONE translator for both routes (formula route below, GRID route in mesh/grid_build.py).
    Emits ONLY the mesher's own key names (``config_builder._enclosure_from_config``): depth_mm,
    the four margins broadcast to ``space_l/t/r/b_mm``, edge_mm and plan_type. Deliberately NOT
    emitted (the mesher's own defaults apply): edge_type (1, rounded fillet), plan_n (unused by
    plan_type 1), depth_margin_mm (1 mm) and front_mesh_size_mm / back_mesh_size_mm.
    """
    margins = mounting["margins_mm"]
    return {
        "depth_mm": float(mounting["depth_mm"]),
        "space_l_mm": float(margins["l"]),
        "space_t_mm": float(margins["t"]),
        "space_r_mm": float(margins["r"]),
        "space_b_mm": float(margins["b"]),
        "edge_mm": float(mounting["edge_mm"]),
        "plan_type": int(MOUNTING_PLANS[mounting["plan"]]),
    }


def enclosure_object(mounting: dict):
    """The mesher's ``HornEnclosure`` for a direct point-grid build (the GRID route).

    Lazy import: this module is imported by offline code where the mesher may not be installed.
    """
    from hornlab_mesher.geometry import HornEnclosure
    return HornEnclosure(**enclosure_section(mounting))


def mounting_key(mounting: dict | None) -> str:
    """Stable cache-key component for a normalized mounting block.

    ``""`` when absent, so every existing (freestanding) mesh/solve/evaluate key is byte-identical.
    """
    if mounting is None:
        return ""
    blob = json.dumps(mounting, sort_keys=True, separators=(",", ":"), default=float)
    return "mnt-" + hashlib.sha256(blob.encode()).hexdigest()[:12]


# ------------------------------------------------------------------ mesher config


def to_mesher_config(design: Design, mesh: MeshSpec, res_mm: dict, out_path: Path, *,
                     mounting: dict | None = None) -> dict:
    """Build the dict ``hornlab_mesher.build_from_config`` consumes.

    DEVIATION FROM THE TASK FILE'S SKETCH (see NOTES_FOR_SENIOR 2026-10-12 task-04): the
    sketch is a flat dict. Measured against hornlab-waveguide-mesher 0.2.4, a TOP-LEVEL
    ``max_triangles`` is silently ignored (the default 18000 applies and a quarter mesh is
    then refused at 4500). Keys must live in their natural section, so this returns the
    sectioned form the mesher's own examples use. Each key's section comes from its KeySpec.

    WP12: ``mounting`` (the normalized ``brief.mounting`` block) flips the top-level mode to
    ``enclosure`` and adds the mesher's own top-level ``enclosure`` section (a SIBLING of
    ``mesh``, not a member of it). ``None`` keeps today's dict byte-for-byte.
    """
    validate(design)
    table = FAMILY_KEYS[design.family]
    cfg: dict = {"formula": design.family, "mode": "freestanding"}
    if mounting is not None:
        cfg["mode"] = "enclosure"
        cfg["enclosure"] = enclosure_section(mounting)
    sections: dict[str, dict] = {"profile": {}, "cross_section": {}, "mesh": {}, "morph": {},
                                 "gcurve": {}}
    exprs = azlaw_expressions(design.params) if design.family == "OSSE" else {}
    for key, value in design.params.items():
        sec = table[key].section
        if sec == "azlaw":                  # folded into the a / n / s expressions below
            continue
        value = copy.deepcopy(exprs.get(key, value))
        if sec == "top":
            cfg[key] = value
        else:
            sections.setdefault(sec, {})[key] = value
    for key, expr in exprs.items():
        if key not in design.params:        # the mesher's own default is then the base value
            sections["profile"][key] = expr
    sections["mesh"].update({
        "quadrants": mesh.quadrants,
        "throat_res_mm": res_mm["throat"],
        "mouth_res_mm": res_mm["mouth"],
        "rear_res_mm": res_mm["rear"],
        "max_triangles": int(mesh.max_triangles),
        "allow_large_mesh": bool(mesh.allow_large_mesh),   # False
        "scale_to_metres": True,                           # EXPLICIT, never implicit
    })
    for name, body in sections.items():
        if body:
            cfg[name] = body
    cfg["output"] = {"path": str(out_path)}
    return cfg


def wrap_mesher_error(exc: BaseException) -> GeometryInvalidError:
    """Map a mesher ConfigError / ValueError / MesherError onto GeometryInvalidError, message
    preserved verbatim. Per-azimuth throat stretch gets a pointer at design/custom.py."""
    msg = str(exc)
    if "per-azimuth" in msg or "not supported yet" in msg:
        return GeometryInvalidError(
            f"{msg}  [hornlab_mesher refuses per-azimuth geometry; that gap is the reserved "
            "extension point hornlab_search/design/custom.py]")
    return GeometryInvalidError(msg)
