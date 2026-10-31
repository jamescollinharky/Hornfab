"""Inner optimiser for the MEH network (contract C12; M4 build step 6).

The outer search solves one geometry and hands over a multi-source BEM ``Response`` (one channel
per source tag: CD = 0, mid entry group = 1).  The geometry does not depend on the drives, so the
inner loop is **free of BEM work**: for every driver combination named by the brief it searches the
lumped-network knobs with CMA-ES on the cheap, CPU-only synthesis in :mod:`hornlab_search.meh`:

    variables  log(xo_hz), mid_delay_ms, mid_gain_db, fill, v_rear_l

``xo_order`` (from ``brief.xo_orders``) and ``mid_polarity`` (+1 / -1) are enumerated, not optimised
(C12: "xo order in xo_orders, mid polarity +-1").  Each CMA run uses ``popsize=8``, at most 160
evaluations and a fixed seed, so the same inputs and seed always produce the same
:class:`~hornlab_search.meh.synthesis.NetworkSolution` (the determinism test pins this).

Scoring
-------
The caller (M7) passes ``score``, normally ``objective.scalar_meh.inner_score``.  It receives the
same ``meh_ctx`` mapping :func:`objective_meh` sees (``freqs``, ``LW``, ``polars``, ``xo_hz``,
``spl_max_db``, band and EQ context) and returns ``J`` (a ``(J, terms)`` tuple is accepted too).
This module **never imports objective code**.  With ``score=None`` it uses a local proxy of the
four C11 system terms (``lw_resid + notch + xo_lob + headroom``, normalised by the C11 tolerances
and weighted by the brief weights) so tests and standalone use need no objective module.

Inputs
------
``resp``           a BEM ``Response`` carrying the C5 MEH channel fields (``from_bem`` validates).
``layout_derived`` the ``derived()`` mapping of the ``meh`` CAD tool (C9): port area, front-chamber
                    volume, neck/wall thickness and optional spacer/dish overrides.  A full CAD
                    result with the mapping under ``"derived"`` is accepted too.
``brief``           the full brief (its ``meh:`` block is used) or the ``meh:`` block itself.
``drivers``         ``{"cd": [...], "mid": [...]}`` of loaded driver objects or stems (a flat
                    sequence of driver objects is accepted too); ``None`` loads the brief stems.

Errors are explicit ``ValueError``s: an empty driver list, a reversed range or a layout without a
positive port area is a caller bug, not something to paper over with a returned "solution".
"""
from __future__ import annotations

import inspect
import math
import numbers
from collections.abc import Mapping, Sequence

import numpy as np

from .dsp import lr, smooth_oct, system_eq
from .limits import spl_max
from .network import from_bem
from .synthesis import NOMINAL_VOLTS, NetworkSolution, nominal_state, system_response

__all__ = ["optimise_network"]

#: C12 search budget per CMA run (popsize is fixed too; the test pins both).
POPSIZE = 8
MAX_EVALS = 160
#: C11 defaults used by the local proxy when the caller supplies no weights.
_PROXY_WEIGHTS = {"lw_resid": 0.5, "notch": 1.0, "xo_lob": 1.0, "headroom": 1.0}
#: C11 tolerances for the four system terms.
_PROXY_TOL = {"lw_resid": 1.0, "notch": 3.0, "xo_lob": 1.5, "headroom": 2.0}
#: Mid-channel gain search range when the brief does not carry one (C10 has no gain key: the DSP
#: gain is a free level-match knob, and the C11 brief always matches the two channel levels).
_DEFAULT_GAIN_DB = (-20.0, 20.0)
_MISSING = object()


# ---------------------------------------------------------------------- input validation


def _is_num(value) -> bool:
    return (not isinstance(value, bool) and isinstance(value, numbers.Real)
            and math.isfinite(float(value)))


def _number(value, where: str) -> float:
    if not _is_num(value):
        raise ValueError(f"{where} must be a finite number, got {value!r}")
    return float(value)


def _meh_block(brief) -> tuple[dict, dict]:
    """Return ``(meh_block, full_brief)`` from either the full brief or the block itself."""
    if not isinstance(brief, Mapping):
        raise ValueError("brief must be a mapping (the full brief or its meh: block)")
    if "meh" in brief:
        block = brief["meh"]
        full = brief
    else:
        block = brief
        full = {}
    if not isinstance(block, Mapping):
        raise ValueError("brief['meh'] must be a mapping")
    required = ("groups", "hp_hz", "xo_hz", "xo_orders", "delay_ms", "v_front_fill", "v_rear_l",
                "amp_v_rms", "port_air_mps_max", "max_boost_db", "spl_target",
                "listening_window")
    missing = [k for k in required if k not in block or block[k] is None]
    if missing:
        raise ValueError(f"meh brief is missing required key(s) {missing}")
    return dict(block), dict(full)


def _range(block, key: str, *, strict: bool = False, positive: bool = False) -> tuple[float, float]:
    """Read and validate one ``{lo, hi}`` range from the ``meh:`` block."""
    sub = block.get(key)
    if not isinstance(sub, Mapping):
        raise ValueError(f"meh.{key} must be a mapping with keys lo and hi")
    if "lo" not in sub or "hi" not in sub:
        raise ValueError(f"meh.{key} must carry both 'lo' and 'hi'")
    lo = _number(sub["lo"], f"meh.{key}.lo")
    hi = _number(sub["hi"], f"meh.{key}.hi")
    if positive and (lo <= 0.0 or hi <= 0.0):
        raise ValueError(f"meh.{key} must be > 0, got lo={lo:g}, hi={hi:g}")
    if (lo >= hi) if strict else (lo > hi):
        cmp = "lo < hi" if strict else "lo <= hi"
        raise ValueError(f"meh.{key} needs {cmp}, got lo={lo:g}, hi={hi:g}")
    return lo, hi


def _gain_range(block) -> tuple[float, float]:
    """Mid gain range: ``meh.mid_gain_db`` / ``meh.gain_db`` if present, else a sane default."""
    for key in ("mid_gain_db", "gain_db"):
        if key in block and block[key] is not None:
            return _range(block, key)
    return _DEFAULT_GAIN_DB


def _orders(block) -> tuple[int, ...]:
    raw = block.get("xo_orders")
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("meh.xo_orders must be a non-empty list of Linkwitz-Riley orders")
    out: list[int] = []
    for order in raw:
        if isinstance(order, bool) or not isinstance(order, numbers.Integral) \
                or order < 2 or order % 2:
            raise ValueError(f"meh.xo_orders must contain even integers >= 2, got {order!r}")
        if int(order) not in out:
            out.append(int(order))
    return tuple(out)


def _seed(block, full=None) -> int:
    """Fixed CMA seed: an explicit ``seed`` (block, brief or ``search.seed``), else 1234."""
    candidates = [block]
    if isinstance(full, Mapping):
        candidates.extend([full, full.get("search")])
    for src in candidates:
        if not isinstance(src, Mapping):
            continue
        seed = src.get("seed")
        if seed is None:
            continue
        if isinstance(seed, bool) or not isinstance(seed, numbers.Integral):
            raise ValueError(f"seed must be an integer, got {seed!r}")
        return int(seed)
    return 1234


def _band(full: Mapping, block: Mapping) -> tuple[float, float]:
    target = full.get("target") if isinstance(full, Mapping) else None
    if isinstance(target, Mapping):
        lo, hi = target.get("band_lo_hz"), target.get("band_hi_hz")
        if _is_num(lo) and _is_num(hi) and float(lo) < float(hi):
            return float(lo), float(hi)
    lo = block.get("band_lo_hz", 120.0)
    hi = block.get("band_hi_hz", 12000.0)
    if _is_num(lo) and _is_num(hi) and float(lo) < float(hi):
        return float(lo), float(hi)
    return 120.0, 12000.0


def _weights(full: Mapping):
    raw = full.get("weights") if isinstance(full, Mapping) else None
    if not isinstance(raw, Mapping):
        return None
    out = {}
    for key in _PROXY_WEIGHTS:
        if key in raw and _is_num(raw[key]):
            out[key] = float(raw[key])
    return out or None


# ---------------------------------------------------------------------- drivers / layout


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def _resolve_drivers(drivers, block):
    """Return ``[(stem, CDSource), ...]`` and ``[(stem, ConeDriver), ...]``."""
    from .drivers import CDSource, ConeDriver, load_cd, load_cone

    groups = block.get("groups")
    if not isinstance(groups, Mapping):
        raise ValueError("meh.groups must be a mapping with cd and mid")
    try:
        cd_stems = list(groups["cd"]["drivers"])
        mid_stems = list(groups["mid"]["drivers"])
    except (KeyError, TypeError):
        raise ValueError("meh.groups must carry groups.cd.drivers and groups.mid.drivers") from None
    if not cd_stems:
        raise ValueError("meh.groups.cd.drivers is empty")
    if not mid_stems:
        raise ValueError("meh.groups.mid.drivers is empty")

    cd_items: list = []
    mid_items: list = []
    if drivers is None:
        pass
    elif isinstance(drivers, Mapping):
        if "cd" in drivers or "mid" in drivers:
            if "cd" in drivers:
                cd_items = _as_list(drivers.get("cd"))
                if not cd_items:
                    raise ValueError("drivers.cd is empty")
            if "mid" in drivers:
                mid_items = _as_list(drivers.get("mid"))
                if not mid_items:
                    raise ValueError("drivers.mid is empty")
        else:
            # stem-keyed mapping: {'<stem>': driver_or_stem, ...}
            for stem, value in drivers.items():
                if isinstance(value, CDSource):
                    cd_items.append((str(stem), value))
                elif isinstance(value, ConeDriver):
                    mid_items.append((str(stem), value))
                elif isinstance(value, str):
                    if stem in cd_stems:
                        cd_items.append(str(stem))
                    elif stem in mid_stems:
                        mid_items.append(str(stem))
                    else:
                        raise ValueError(f"driver stem {stem!r} is not in the brief groups")
                else:
                    raise ValueError(f"drivers[{stem!r}] is not a driver or a stem")
            if not cd_items and not mid_items:
                raise ValueError("drivers mapping contains no drivers")
    elif isinstance(drivers, (list, tuple)):
        objs = list(drivers)
        if not objs:
            raise ValueError("drivers is an empty list")
        for item in objs:
            if isinstance(item, CDSource):
                cd_items.append(item)
            elif isinstance(item, ConeDriver):
                mid_items.append(item)
            elif isinstance(item, str):
                if item in cd_stems:
                    cd_items.append(item)
                elif item in mid_stems:
                    mid_items.append(item)
                else:
                    raise ValueError(f"driver stem {item!r} is not in the brief groups")
            else:
                raise ValueError(f"drivers entry {item!r} is not a driver or a stem")
        if not cd_items and not mid_items:
            raise ValueError("drivers sequence contains no drivers")
    else:
        raise ValueError("drivers must be a mapping, a sequence of drivers, or None")

    def _side(items, stems, loader, kind, side):
        out = []
        for i, item in enumerate(items):
            if isinstance(item, tuple) and len(item) == 2:
                stem, obj = str(item[0]), item[1]
                if isinstance(obj, str):
                    obj = loader(obj)
            elif isinstance(item, str):
                stem, obj = item, loader(item)
            else:
                stem = stems[i] if i < len(stems) else str(getattr(item, "name", ""))
                obj = item
            if not isinstance(obj, kind):
                raise ValueError(f"drivers.{side}[{i}] is not a {kind.__name__}")
            out.append((stem, obj))
        # Load any brief stem that the caller did not supply explicitly.
        for i in range(len(items), len(stems)):
            out.append((stems[i], loader(stems[i])))
        return out

    cds = _side(cd_items, cd_stems, load_cd, CDSource, "cd")
    mids = _side(mid_items, mid_stems, load_cone, ConeDriver, "mid")
    if not cds:
        raise ValueError("no CD driver candidates (meh.groups.cd.drivers is empty)")
    if not mids:
        raise ValueError("no mid driver candidates (meh.groups.mid.drivers is empty)")
    return cds, mids


def _layout_value(layout: Mapping, params, key: str, default=_MISSING):
    for src in (layout, params):
        if isinstance(src, Mapping) and src.get(key) is not None:
            return src[key]
        if not isinstance(src, Mapping) and src is not None and getattr(src, key, None) is not None:
            return getattr(src, key)
    if default is _MISSING:
        raise ValueError(f"layout_derived is missing '{key}'")
    return default


def _layout(layout_derived, mid, mid_count) -> dict:
    """Validate the CAD ``derived`` mapping and derive the network's fixed geometry (SI)."""
    if not isinstance(layout_derived, Mapping):
        raise ValueError("layout_derived must be the meh CAD tool's derived() mapping")
    layout = layout_derived.get("derived", layout_derived)
    if not isinstance(layout, Mapping):
        raise ValueError("layout_derived['derived'] must be a mapping")
    params = layout_derived.get("params") or layout_derived.get("recipe") or {}

    area_mm2 = layout.get("port_area_mm2")
    if area_mm2 is None and layout.get("s_port_m2") is None:
        ports = layout.get("ports")
        if isinstance(ports, (list, tuple)) and ports and isinstance(ports[0], Mapping):
            area_mm2 = ports[0].get("area_mm2")
    if layout.get("s_port_m2") is not None:
        s_port_m2 = _number(layout["s_port_m2"], "layout_derived.s_port_m2")
    else:
        s_port_m2 = _number(area_mm2, "layout_derived.port_area_mm2") * 1e-6
    if not s_port_m2 > 0.0:
        raise ValueError("layout_derived must give a positive port area (port_area_mm2)")

    l_neck_m = None
    for key in ("l_neck_m", "l_neck_mm"):
        value = layout.get(key)
        if value is not None:
            l_neck_m = _number(value, f"layout_derived.{key}") * (1.0 if key.endswith("_m") else 1e-3)
            break
    if l_neck_m is None:
        wall_t_mm = _layout_value(layout, params, "wall_t_mm", 6.0)
        l_neck_m = _number(wall_t_mm, "layout_derived.wall_t_mm") * 1e-3
    if l_neck_m < 0.0:
        raise ValueError(f"layout_derived neck length must be >= 0, got {l_neck_m:g} m")

    dish_mm = layout.get("dish_mm")
    if dish_mm is None:
        dish_mm = getattr(mid, "dish_mm", None)
    if dish_mm is None:
        cutout = getattr(mid, "cutout_mm", None) or 145.0
        dish_mm = 0.2 * float(cutout)          # the reference's inferred placeholder (C9)
    dish_m = _number(dish_mm, "layout_derived.dish_mm") * 1e-3
    if dish_m < 0.0:
        raise ValueError(f"layout_derived.dish_mm must be >= 0, got {dish_mm!r}")

    if layout.get("v_front_m3") is not None:
        v_front0 = _number(layout["v_front_m3"], "layout_derived.v_front_m3")
    elif layout.get("v_front_cm3") is not None:
        v_front0 = _number(layout["v_front_cm3"], "layout_derived.v_front_cm3") * 1e-6
    else:
        spacer_mm = _layout_value(layout, params, "spacer_mm", 3.0)
        wall_t_mm = _layout_value(layout, params, "wall_t_mm", 6.0)
        base = float(mid.sd_m2) * (_number(spacer_mm, "layout_derived.spacer_mm")
                                   + _number(wall_t_mm, "layout_derived.wall_t_mm")) * 1e-3
        v_front0 = base + float(mid.sd_m2) * dish_m / 3.0
    if not v_front0 > 0.0:
        raise ValueError(f"layout_derived front-chamber volume must be > 0, got {v_front0:g} m^3")

    return {
        "s_port_m2": float(s_port_m2),
        "l_neck_m": float(l_neck_m),
        "n_end": 1,                    # C7: the horn-side radiation mass is already in Z_net
        "q_port": 10.0,
        "v_front0_m3": float(v_front0),
        "dish_m3": float(mid.sd_m2) * dish_m / 3.0,
        "mid_count": int(mid_count),
    }


def _front_volume(geom: dict, fill: float) -> float:
    """C7 front-chamber volume with the printed filler: ``base + (1-fill) * dish/3``."""
    v = geom["v_front0_m3"] - float(fill) * geom["dish_m3"]
    floor = 0.02 * geom["v_front0_m3"]
    return float(max(v, floor))


# ---------------------------------------------------------------------- scoring context


def _power_db(values) -> float:
    a = np.asarray(values, dtype=np.float64)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return float("nan")
    return float(10.0 * math.log10(float(np.mean(np.power(10.0, a / 10.0)))))


def _lw_curve(spl_h, h_angles, spl_v, v_angles, window) -> np.ndarray:
    def _sel(angles, wanted):
        angles = np.asarray(angles, dtype=np.float64)
        idx = []
        for a in wanted:
            hit = np.flatnonzero(np.abs(angles - float(a)) <= 1e-9)
            if hit.size:
                idx.append(int(hit[0]))
        return idx

    try:
        sel_h = _sel(h_angles, window.get("h_deg", []))
        sel_v = _sel(v_angles, window.get("v_deg", []))
    except (TypeError, AttributeError):
        sel_h, sel_v = [], []
    cols = []
    if sel_h:
        cols.append(np.asarray(spl_h, dtype=np.float64)[:, sel_h])
    if sel_v:
        cols.append(np.asarray(spl_v, dtype=np.float64)[:, sel_v])
    if not cols:
        ax = int(np.argmin(np.abs(np.asarray(h_angles, dtype=np.float64))))
        return np.asarray(spl_h, dtype=np.float64)[:, ax].copy()
    stacked = np.concatenate(cols, axis=1)
    power = np.mean(np.power(10.0, stacked / 10.0), axis=1)
    with np.errstate(divide="ignore"):
        return 10.0 * np.log10(power)


def _interp_logf(f, values, f0: float) -> float:
    f = np.asarray(f, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    good = np.isfinite(f) & (f > 0.0) & np.isfinite(values)
    if not good.any() or not (math.isfinite(f0) and f0 > 0.0):
        return float("nan")
    return float(np.interp(math.log2(float(f0)), np.log2(f[good]), values[good]))


def _target_curve(f, raw):
    if raw is None:
        return None
    try:
        arr = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if arr.ndim == 1:
        return arr if arr.size == f.size else None
    if arr.ndim != 2 or arr.shape[1] != 2 or arr.shape[0] < 2:
        return None
    good = np.isfinite(arr[:, 0]) & (arr[:, 0] > 0.0) & np.isfinite(arr[:, 1])
    if good.sum() < 2:
        return None
    knots = arr[good]
    if np.any(np.diff(knots[:, 0]) <= 0.0):
        return None
    return np.interp(np.log2(np.maximum(f, 1e-12)), np.log2(knots[:, 0]), knots[:, 1])


def _proxy_terms(ctx: dict) -> dict:
    """The four C11 system terms, evaluated locally (no objective import)."""
    f = np.asarray(ctx["freqs"], dtype=np.float64)
    lw = np.asarray(ctx["LW"], dtype=np.float64)
    lo, hi = float(ctx.get("band_lo_hz", 120.0)), float(ctx.get("band_hi_hz", 12000.0))
    band = (f >= lo - 1e-9) & (f <= hi + 1e-9) & np.isfinite(lw)

    out = {"lw_resid": 0.0, "notch": 0.0, "xo_lob": 0.0, "headroom": 0.0}
    max_boost = float(ctx.get("max_boost_db", 6.0))

    if band.any():
        s3 = smooth_oct(f, lw, 1.0 / 3.0)
        eq = system_eq(lw, f, max_boost)
        eq_lw = lw + eq
        s6 = smooth_oct(f, eq_lw, 1.0 / 6.0)
        good = band & np.isfinite(s6)
        if good.any():
            resid = s6[good] - float(np.mean(s6[good]))
            out["lw_resid"] = float(np.sqrt(np.mean(resid ** 2)))
        depth = np.maximum(0.0, s3 - lw)
        depth = depth[band & np.isfinite(depth)]
        if depth.size:
            out["notch"] = float(np.mean(np.sort(depth)[-3:]))

    # xo_lob: N(theta) - R(theta) around the chosen crossover, both planes.
    residuals = []
    xos = [float(x) for x in (ctx.get("xo_hz") or []) if _is_num(x) and float(x) > 0.0]
    polars = ctx.get("polars")
    if xos and isinstance(polars, Mapping):
        for name, limit in (("h", 45.0), ("v", 30.0)):
            plane = polars.get(name)
            if not isinstance(plane, (tuple, list)) or len(plane) != 2:
                continue
            angles = np.asarray(plane[0], dtype=np.float64)
            spl = np.asarray(plane[1], dtype=np.float64)
            if angles.ndim != 1 or spl.ndim != 2 or spl.shape[0] != f.size \
                    or spl.shape[1] != angles.size or angles.size == 0:
                continue
            ax = int(np.argmin(np.abs(angles)))
            normal = spl - spl[:, [ax]]
            use = np.flatnonzero(np.abs(angles) <= limit + 1e-9)
            if use.size == 0:
                continue
            for fx in xos:
                window = (f >= fx / math.sqrt(2.0) - 1e-9) & (f <= fx * math.sqrt(2.0) + 1e-9)
                if not window.any():
                    continue
                n_lo = np.array([_interp_logf(f, normal[:, j], fx / 2.0) for j in use])
                n_hi = np.array([_interp_logf(f, normal[:, j], 2.0 * fx) for j in use])
                if not (np.all(np.isfinite(n_lo)) and np.all(np.isfinite(n_hi))):
                    continue
                logpos = np.log2(f[window] / (fx / 2.0)) / 2.0
                ref = n_lo[None, :] + (n_hi - n_lo)[None, :] * logpos[:, None]
                measured = normal[np.ix_(window, use)]
                ok = np.isfinite(measured) & np.isfinite(ref)
                if ok.any():
                    residuals.append((measured - ref)[ok].ravel())
    if residuals:
        r = np.concatenate(residuals)
        out["xo_lob"] = float(np.sqrt(np.mean(r ** 2)))

    # headroom: band shortfall against the target raised by the MEH's own LR4 high-pass.
    smax = np.asarray(ctx.get("spl_max_db", []), dtype=np.float64)
    tgt = _target_curve(f, ctx.get("spl_target_db"))
    if smax.shape == f.shape and tgt is not None:
        hp = float(ctx.get("hp_hz", 120.0))
        adj = tgt + 20.0 * np.log10(np.abs(lr(f, hp, 4, "hp")) + 1e-300)
        good = band & np.isfinite(smax) & np.isfinite(adj)
        if good.any():
            out["headroom"] = float(np.mean(np.maximum(0.0, adj[good] - smax[good])))
    return out


def _default_score(ctx: dict, weights=None) -> float:
    terms = _proxy_terms(ctx)
    w = dict(_PROXY_WEIGHTS)
    for key, value in (weights or {}).items():
        if key in w and _is_num(value):
            w[key] = float(value)
    total = sum(w[key] * float(terms[key]) / _PROXY_TOL[key] for key in _PROXY_TOL)
    return float(total) if math.isfinite(total) else 1e9


def _call_score(score, ctx: dict, weights) -> float:
    """Call the caller's score, tolerating ``(ctx)``, ``(ctx, weights)`` and ``(J, terms)``."""
    if score is None:
        return _default_score(ctx, weights)
    try:
        n_pos = len([p for p in inspect.signature(score).parameters.values()
                     if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
    except (TypeError, ValueError):
        n_pos = 1
    try:
        value = score(ctx, weights) if n_pos >= 2 else score(ctx)
    except Exception:  # noqa: BLE001 - a broken score must not abort the sweep
        return 1e9
    if isinstance(value, (tuple, list)):
        value = value[0] if value else 1e9
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 1e9
    return value if math.isfinite(value) else 1e9


# ---------------------------------------------------------------------- evaluation


def _make_solution(resp, *, cd_stem, mid_stem, cd, mid, geom, block, xo_hz, xo_order,
                   delay_ms, polarity, gain_db, fill, rear_l) -> NetworkSolution:
    return NetworkSolution(
        cd_stem=str(cd_stem),
        mid_stem=str(mid_stem),
        xo_hz=float(xo_hz),
        xo_order=int(xo_order),
        mid_delay_ms=float(delay_ms),
        mid_polarity=int(polarity),
        gains_db=(0.0, float(gain_db)),
        v_front_m3=float(_front_volume(geom, fill)),
        v_rear_m3=float(rear_l) * 1e-3,
        hp_hz=float(block["hp_hz"]),
        mid_count=int(geom["mid_count"]),
        s_port_m2=float(geom["s_port_m2"]),
        l_neck_m=float(geom["l_neck_m"]),
        n_end=int(geom["n_end"]),
        q_port=float(geom["q_port"]),
        cd=cd,
        mid=mid,
        response=resp,
    )


def _context(system, state, solution, block, full, freqs) -> dict:
    lo, hi = _band(full, block)
    return {
        "freqs": np.asarray(freqs, dtype=np.float64),
        "LW": _lw_curve(system.spl_h_db, system.h_angles_deg,
                        system.spl_v_db, system.v_angles_deg, block["listening_window"]),
        "polars": {
            "h": (np.asarray(system.h_angles_deg, dtype=np.float64),
                  np.asarray(system.spl_h_db, dtype=np.float64)),
            "v": (np.asarray(system.v_angles_deg, dtype=np.float64),
                  np.asarray(system.spl_v_db, dtype=np.float64)),
        },
        "xo_hz": [float(solution.xo_hz)],
        "spl_max_db": np.asarray(spl_max(freqs, solution, block), dtype=np.float64),
        "spl_target_db": block.get("spl_target"),
        "hp_hz": float(block["hp_hz"]),
        "max_boost_db": float(block["max_boost_db"]),
        "band_lo_hz": lo,
        "band_hi_hz": hi,
    }


def _evaluate(resp, solution, block, full, score, weights, freqs):
    """Synthesise, apply the limits, and return ``(J, ctx)`` for one candidate."""
    state = nominal_state(resp, solution)
    solution.nominal_state = state
    system = system_response(resp, solution)
    ctx = _context(system, state, solution, block, full, freqs)
    return _call_score(score, ctx, weights), ctx


# ---------------------------------------------------------------------- CMA search


def _decode(z, ranges) -> tuple[float, float, float, float, float]:
    """Map a normalised ``[0, 1]^5`` point to the physical knobs."""
    z = np.clip(np.asarray(z, dtype=np.float64).ravel(), 0.0, 1.0)
    (xo_lo, xo_hi), delay, gain, fill, rear = ranges
    lx = math.log(xo_lo) + z[0] * (math.log(xo_hi) - math.log(xo_lo))
    xo = math.exp(lx)
    delay_ms = delay[0] + z[1] * (delay[1] - delay[0])
    gain_db = gain[0] + z[2] * (gain[1] - gain[0])
    fill_frac = fill[0] + z[3] * (fill[1] - fill[0])
    rear_l = rear[0] + z[4] * (rear[1] - rear[0])
    return float(xo), float(delay_ms), float(gain_db), float(fill_frac), float(rear_l)


def _cma_run(evaluate, ranges, seed, *, max_evals=MAX_EVALS, popsize=POPSIZE):
    """One CMA run in normalised space; returns ``(best_params, best_J, n_evals)``.

    ``max_evals`` is a hard cap: only whole generations (``popsize`` points each) are evaluated and
    one slot is reserved for the centre point, so ``n_evals`` never exceeds ``max_evals``.
    """
    try:
        import cma
    except ImportError as exc:  # pragma: no cover - cma is an installed dependency
        raise RuntimeError("the MEH inner optimiser needs the 'cma' package") from exc

    n_evals = 0
    cache: dict[tuple, float] = {}

    def objective(z):
        nonlocal n_evals
        key = tuple(round(float(v), 12) for v in np.asarray(z).ravel())
        if key in cache:
            return cache[key]
        n_evals += 1
        params = _decode(z, ranges)
        value = float(evaluate(params))
        cache[key] = value
        return value

    x0 = np.full(5, 0.5, dtype=np.float64)
    best_z = x0.copy()
    best_j = objective(x0)                     # always evaluate the centre (budget slot 1)
    es = cma.CMAEvolutionStrategy(
        x0, 0.25,
        {"popsize": int(popsize), "maxfevals": int(max_evals), "seed": int(seed),
         "verbose": -9, "bounds": [0.0, 1.0], "tolfun": 1e-9, "tolx": 1e-9},
    )
    max_generations = max(0, (int(max_evals) - 1) // int(popsize))
    for _ in range(max_generations):
        if es.stop():
            break
        xs = es.ask()
        values = [objective(z) for z in xs]
        es.tell(xs, values)
        for z, value in zip(xs, values):
            if value < best_j:
                best_j, best_z = float(value), np.asarray(z, dtype=np.float64).copy()
    return _decode(best_z, ranges), float(best_j), int(n_evals)


# ---------------------------------------------------------------------- public entry point


def optimise_network(resp, layout_derived, brief, drivers, score=None) -> NetworkSolution:
    """Search the CD/mid drives for one solved MEH geometry (C12).

    Enumerates ``min(CD x mid candidates, 9)`` driver combinations from ``brief.meh.groups``, every
    ``xo_order`` in ``brief.meh.xo_orders`` and both mid polarities.  Each CMA run searches
    ``[log xo_hz, mid_delay_ms, mid_gain_db, fill, v_rear_l]`` inside the brief ranges with
    ``popsize=8`` and at most 160 evaluations.  Returns the best :class:`NetworkSolution` with the
    C12 record filled in; ``n_evals`` is the total number of score evaluations spent across every
    combination (so ``n_evals <= 2 * 160 * len(orders) * n_combos``).

    Raises ``ValueError`` for a hostile input (empty driver list, reversed/absent range, a layout
    without a positive port area, a response without MEH channels).
    """
    block, full = _meh_block(brief)

    # ---- validate every search range before doing any work (clear errors, not garbage).
    xo_range = _range(block, "xo_hz", strict=True, positive=True)
    delay_range = _range(block, "delay_ms")
    gain_range = _gain_range(block)
    fill_range = _range(block, "v_front_fill")
    rear_range = _range(block, "v_rear_l", positive=True)
    orders = _orders(block)
    seed = _seed(block, full)
    hp_hz = _number(block["hp_hz"], "meh.hp_hz")
    if not hp_hz > 0.0:
        raise ValueError(f"meh.hp_hz must be > 0, got {hp_hz:g}")
    max_boost = _number(block["max_boost_db"], "meh.max_boost_db")
    if max_boost < 0.0:
        raise ValueError(f"meh.max_boost_db must be >= 0, got {max_boost:g}")

    groups = block.get("groups")
    if not isinstance(groups, Mapping) or "mid" not in groups:
        raise ValueError("meh.groups must carry a mid group")
    try:
        mid_count = int(groups["mid"]["count"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("meh.groups.mid.count must be a positive integer") from None
    if mid_count < 1:
        raise ValueError(f"meh.groups.mid.count must be >= 1, got {mid_count}")

    cd_cands, mid_cands = _resolve_drivers(drivers, block)
    combos = [(cd_stem, cd, mid_stem, mid)
              for cd_stem, cd in cd_cands for mid_stem, mid in mid_cands][:9]
    if not combos:
        raise ValueError("no driver combinations to search")

    # ---- validate the response once; the geometry is shared by every candidate.
    h_net, _z_net, freqs = from_bem(resp)
    if freqs.size == 0:
        raise ValueError("resp.freqs_hz is empty")
    if np.any(freqs <= 0.0):
        raise ValueError("resp.freqs_hz must be > 0 for the log-frequency search")
    if h_net.shape[1] < 2:
        raise ValueError(
            f"the MEH inner optimiser needs at least a CD and one mid channel, got "
            f"{h_net.shape[1]}")
    for name in ("h_angles_deg", "v_angles_deg"):
        if not hasattr(resp, name):
            raise ValueError(f"resp has no {name}; a synthesised system needs both planes")

    weights = _weights(full) if full else None
    if weights is None:
        weights = _weights(block)
    best = None  # (J, solution, meh_ctx, n_evals)
    total_evals = 0
    ranges = (xo_range, delay_range, gain_range, fill_range, rear_range)

    for cd_stem, cd, mid_stem, mid in combos:
        geom = _layout(layout_derived, mid, mid_count)
        for order in orders:
            for polarity in (1, -1):
                def evaluate(params):
                    xo_hz, delay_ms, gain_db, fill, rear_l = params
                    solution = _make_solution(
                        resp, cd_stem=cd_stem, mid_stem=mid_stem, cd=cd, mid=mid, geom=geom,
                        block=block, xo_hz=xo_hz, xo_order=order, delay_ms=delay_ms,
                        polarity=polarity, gain_db=gain_db, fill=fill, rear_l=rear_l)
                    j, ctx = _evaluate(resp, solution, block, full, score, weights, freqs)
                    return j

                params, j, n = _cma_run(evaluate, ranges, seed)
                total_evals += n
                if best is None or j < best[0]:
                    # Re-evaluate the winning point so the stored context belongs to exactly the
                    # returned knobs (the CMA cache is per run and not shared).
                    xo_hz, delay_ms, gain_db, fill, rear_l = params
                    solution = _make_solution(
                        resp, cd_stem=cd_stem, mid_stem=mid_stem, cd=cd, mid=mid, geom=geom,
                        block=block, xo_hz=xo_hz, xo_order=order, delay_ms=delay_ms,
                        polarity=polarity, gain_db=gain_db, fill=fill, rear_l=rear_l)
                    j, ctx = _evaluate(resp, solution, block, full, score, weights, freqs)
                    best = (j, solution, ctx, n)

    assert best is not None
    j_best, solution, ctx, _n = best

    # ---- the C12 record: the EQ and SPL_max curves on the solved grid.
    solution.inner_J = float(j_best)
    solution.n_evals = int(total_evals)
    solution.seed = int(seed)
    solution.eq_db = tuple(float(v) for v in
                           np.asarray(system_eq(np.asarray(ctx["LW"], dtype=np.float64),
                                                np.asarray(freqs, dtype=np.float64),
                                                max_boost), dtype=np.float64))
    solution.spl_max_db = tuple(float(v) for v in
                                np.asarray(ctx["spl_max_db"], dtype=np.float64))
    return solution
