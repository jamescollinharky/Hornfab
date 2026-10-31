"""Objective v5 ("meh", 2026-10-30): v4's pattern terms plus the MEH system terms.

Why (docs/meh/00_MEH_CONTRACTS.md C11): an MEH is one system - a CD channel and one or more
mid entry groups summed through a passive/lumped network - so the pattern terms must be scored on
the SYNTHESISED system response, not on a bare horn.  What the owner's DSP cannot fix is scored on
top of that:

    J = sum_k  w_k * term_k / tol_k  + penalty

    k in cov rip di dislope flat load distd diag        (v4 keys, v4 functions, unchanged meaning)
       + lw_resid notch xo_lob headroom                 (the four new system terms)

The stored ``terms`` hold the NORMALISED values (``term_k / tol_k``), exactly like v4, so
``sum(w_k * terms[k]) == terms['total']`` and every display that multiplies by the weights stays
right.  Raw values are ``terms[k] * tol_k``.

The four new terms (C11):

* ``lw_resid`` - RMS of ``S6(LW + E) - mean`` over the bass-integration band, where the
  FIR-equivalent EQ is ``E = min(mean(LW) - S3(LW), max_boost_db)`` (unlimited cut, the boost
  ceiling from the brief) and ``Sk`` is 1/k-octave smoothing.  A broad tilt the EQ can flatten is
  free; a broad tilt that needs more than the boost limit is not.
* ``notch`` - mean of the three largest ``max(0, S3(LW) - LW)`` values in the band: narrow dips a
  smoothing EQ cannot fill.
* ``xo_lob`` - RMS of ``N(theta, f) - R(theta, f)`` around each CD/mid crossover ``fx``, with
  ``N = SPL - SPL(0 deg)`` and ``R`` the log-frequency linear interpolation of ``N`` between
  ``fx/2`` and ``2 fx``.  ``R`` is what a smooth crossover-shaped system looks like; the residual
  is the off-axis lobing the crossover itself creates.
* ``headroom`` - mean of ``max(0, spl_target(f) + 20 log10|LR4_HP(f; hp_hz)| - SPL_max(f))`` over
  the band.  The MEH's own high-pass is intended (C11 bass-box crossover rule); the target it must
  reach is the SYSTEM target raised by the LR4 high-pass response.

``meh_ctx`` (built by M7; this module imports no network code):

    {
      "freqs":        (nf,) Hz, ascending,
      "LW":           (nf,) dB, the listening-window power average,
      "polars":       {"h": (angles_deg, spl_db[nf, na]), "v": (angles_deg, spl_db[nf, na])},
      "xo_hz":        [fx, ...] the chosen CD/mid crossover(s),
      "spl_max_db":   (nf,) dB, the level ceiling from M4's limits,
      "spl_target_db": either (nf,) dB or the brief's [[Hz, dB], ...] knots,
      # optional, with the C10 defaults when absent:
      "hp_hz": 120.0, "max_boost_db": 6.0,
    }

``objective_meh`` and ``inner_score`` NEVER raise and never return nan or inf.  They use numpy only,
so they are safe callables for M4's inner optimiser through M7.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..targets.spec import Target
from .scalar_v4 import V4_ALL_KEYS, V4_WEIGHTED_KEYS, V4Params, objective_v4
from .terms import NAN_TERM_FILL, PENALTY_FAILED

log = logging.getLogger("hornlab_search.objective.scalar_meh")

__all__ = [
    "objective_meh", "inner_score", "MehParams", "MEH_EXTRA_KEYS", "MEH_WEIGHTED_KEYS",
    "MEH_ALL_KEYS", "MEH_DEFAULT_WEIGHTS", "MEH_DEFAULT_TOLERANCES", "resolve_meh_weights",
    "worst_valid_meh_j", "smooth_oct", "lr4_highpass_db", "lw_resid_term", "notch_term",
    "xo_lob_term", "headroom_term",
]

#: The four terms v5 adds to v4, in C11 order.
MEH_EXTRA_KEYS = ("lw_resid", "notch", "xo_lob", "headroom")
#: Every weighted term of v5, in C11 order (v4's eight first).
MEH_WEIGHTED_KEYS = V4_WEIGHTED_KEYS + MEH_EXTRA_KEYS
#: Every key an ``Evaluation.terms`` dict carries for v5.
MEH_ALL_KEYS = V4_ALL_KEYS + MEH_EXTRA_KEYS

#: C11 default weights (T2/T1 brief).  Pattern terms carry the C11 table's values; ``flat`` is 0
#: because FIR makes on-axis flatness free, ``di``/``diag`` are 0 on the screen (no balloon).
MEH_DEFAULT_WEIGHTS = {
    "cov": 1.0, "rip": 0.5, "di": 0.0, "dislope": 0.3, "flat": 0.0, "load": 0.0,
    "distd": 0.5, "diag": 0.0, "lw_resid": 0.5, "notch": 1.0, "xo_lob": 1.0, "headroom": 1.0,
}

#: C11 tolerances for the four new terms; the v4 keys keep the frozen Option A tolerance set
#: (docs/evidence/OBJECTIVE_V4_TOLERANCES.md) so v5 does not silently re-normalise v4's terms.
MEH_DEFAULT_TOLERANCES = {
    "cov": 2.0, "rip": 1.0, "di": 0.4, "dislope": 9.0, "flat": 1.5, "load": 0.3,
    "distd": 2.0, "diag": 2.0, "lw_resid": 1.0, "notch": 3.0, "xo_lob": 1.5, "headroom": 2.0,
}

_COV_BELOW_F0 = ("mask", "one_sided")
_DIAG_REFERENCES = ("round",)
_BLOCK_KEYS = {"version", "tolerances", "cov_narrow_ratio", "cov_below_f0", "diag_reference"}

#: The C10 defaults used only when M7's context omits the key (the brief always carries them).
_DEFAULT_HP_HZ = 120.0
_DEFAULT_MAX_BOOST_DB = 6.0


@dataclass(frozen=True)
class MehParams:
    """The ``objective:`` block of a v5 brief, validated.

    Unlike v4, every tolerance has a documented default: the C11 table for the four new terms and
    the frozen v4 Option A set for the eight pattern terms.  A brief may override any subset; a
    value that is not a finite number > 0 is refused, and an unknown key is refused so a YAML typo
    is never silent.
    """

    tolerances: dict
    cov_narrow_ratio: float = 1.0
    cov_below_f0: str = "mask"
    diag_reference: str = "round"

    @classmethod
    def from_block(cls, block: dict) -> "MehParams":
        if not isinstance(block, dict):
            raise ValueError("objective must be a mapping")
        unknown = set(block) - _BLOCK_KEYS
        if unknown:
            raise ValueError(f"objective unknown key(s) {sorted(unknown)} "
                             f"(allowed for v5: {sorted(_BLOCK_KEYS)})")
        raw_tol = block.get("tolerances", {})
        if raw_tol is None:
            raw_tol = {}
        if not isinstance(raw_tol, dict):
            raise ValueError("objective.tolerances must be a mapping (omit it for the C11 defaults)")
        unknown = sorted(set(raw_tol) - set(MEH_WEIGHTED_KEYS))
        if unknown:
            raise ValueError(f"objective.tolerances: unknown {unknown} "
                             f"(allowed: {list(MEH_WEIGHTED_KEYS)})")
        clean = dict(MEH_DEFAULT_TOLERANCES)
        for k, v in raw_tol.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or not math.isfinite(float(v)) or not float(v) > 0.0:
                raise ValueError(f"objective.tolerances.{k} must be a finite number > 0, got {v!r}")
            clean[k] = float(v)
        ratio = block.get("cov_narrow_ratio", 1.0)
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) \
                or not math.isfinite(float(ratio)) or not float(ratio) > 0.0:
            raise ValueError(f"objective.cov_narrow_ratio must be a finite number > 0, got {ratio!r}")
        below = block.get("cov_below_f0", "mask")
        if below not in _COV_BELOW_F0:
            raise ValueError(f"objective.cov_below_f0 must be one of {list(_COV_BELOW_F0)}, got {below!r}")
        ref = block.get("diag_reference", "round")
        if ref not in _DIAG_REFERENCES:
            raise ValueError(f"objective.diag_reference must be one of {list(_DIAG_REFERENCES)}, got {ref!r}")
        return cls(tolerances=clean, cov_narrow_ratio=float(ratio), cov_below_f0=str(below),
                   diag_reference=str(ref))

    def to_block(self) -> dict:
        """The normalised mapping stored in the config (so ``config_sha`` covers every choice)."""
        return {"version": 5, "tolerances": dict(self.tolerances),
                "cov_narrow_ratio": self.cov_narrow_ratio, "cov_below_f0": self.cov_below_f0,
                "diag_reference": self.diag_reference}


def resolve_meh_weights(weights: dict | None) -> dict:
    """C11 defaults overlaid with ``weights``; unknown keys warn (never raise), as in v1-v4."""
    out = dict(MEH_DEFAULT_WEIGHTS)
    for k, v in (weights or {}).items():
        if k in MEH_DEFAULT_WEIGHTS:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                log.warning("weight %r=%r is not a number; using the default %r", k, v, out[k])
        else:
            log.warning("unknown objective weight %r ignored (known: %s)", k,
                        sorted(MEH_DEFAULT_WEIGHTS))
    return out


def worst_valid_j(params: MehParams, weights: dict | None) -> float:
    """J of a VALID design whose every weighted term is unmeasurable (``NAN_TERM_FILL``).

    Same penalty-ordering invariant as v4: this must stay far below the refusal penalty, or a
    refused design could outrank a working one.  Config checks it at load, per brief.
    """
    w = resolve_meh_weights(weights)
    return float(sum(w[k] * NAN_TERM_FILL / params.tolerances[k] for k in MEH_WEIGHTED_KEYS))


#: Alias with the v4 helper's name, so config/test code reads the same way for v5.
worst_valid_meh_j = worst_valid_j


# ------------------------------------------------------------------ smoothing / filters

def smooth_oct(f, db, frac: float) -> np.ndarray:
    """Fractional-octave smoothing: power average in a +/- ``frac``/2 octave window.

    ``frac`` is the denominator: 3 -> 1/3-octave, 6 -> 1/6-octave.  ``nan`` inputs are skipped; a
    point whose window holds no finite sample stays ``nan``.  The window is symmetric in log2 f and
    truncated at the array edges, which is the standard fractional-octave average and is what M4's
    ``dsp.smooth_oct`` uses for the same reason (power, not dB, averaging).
    """
    f = np.asarray(f, dtype=float)
    db = np.asarray(db, dtype=float)
    if f.ndim != 1 or db.ndim != 1 or f.size != db.size:
        return np.full(f.shape, np.nan, dtype=float)
    if f.size == 0:
        return np.full(0, np.nan, dtype=float)
    try:
        frac = float(frac)
    except (TypeError, ValueError):
        return np.full(f.size, np.nan, dtype=float)
    if not math.isfinite(frac) or frac <= 0.0:
        return np.full(f.size, np.nan, dtype=float)
    finite = np.isfinite(f) & (f > 0.0) & np.isfinite(db)
    out = np.full(f.size, np.nan, dtype=float)
    if not finite.any():
        return out
    logf = np.where(f > 0.0, np.log2(np.where(f > 0.0, f, 1.0)), np.nan)
    half = 0.5 / frac
    for i in range(f.size):
        if not finite[i]:
            continue
        window = finite & (np.abs(logf - logf[i]) <= half + 1e-12)
        if not window.any():
            continue
        power = np.power(10.0, db[window] / 10.0)
        out[i] = 10.0 * math.log10(float(np.mean(power)))
    return out


def lr4_highpass_db(f, fc: float) -> np.ndarray:
    """20 log10 |LR4 high-pass| at ``fc``: ``10 log10(x^4 / (1 + x^4))``, x = f/fc.

    LR4 is two cascaded 2nd-order Butterworth sections, so |H_LR4|^2 = x^4/(1+x^4).  At f = fc this
    is -6.0206 dB, the Linkwitz-Riley crossover point.
    """
    f = np.asarray(f, dtype=float)
    fc = float(fc)
    if not math.isfinite(fc) or fc <= 0.0:
        return np.full(f.shape, np.nan, dtype=float)
    x = np.maximum(f, 0.0) / fc
    x4 = x ** 4
    with np.errstate(divide="ignore"):
        return 10.0 * np.log10(x4 / (1.0 + x4))


# ------------------------------------------------------------------ context access

def _ctx_array(meh_ctx, key, *, ndim=1):
    if not isinstance(meh_ctx, dict) or meh_ctx.get(key) is None:
        return None
    try:
        a = np.asarray(meh_ctx[key], dtype=float)
    except (TypeError, ValueError):
        return None
    return a if a.ndim == ndim else None


def _ctx_float(meh_ctx, key, default: float) -> float:
    if not isinstance(meh_ctx, dict):
        return float(default)
    try:
        v = float(meh_ctx.get(key, default))
    except (TypeError, ValueError):
        return float(default)
    return v if math.isfinite(v) else float(default)


def _band(f, lo: float, hi: float) -> np.ndarray:
    return (f >= float(lo) - 1e-9) & (f <= float(hi) + 1e-9)


def _nanmean(x) -> float:
    x = np.asarray(x, dtype=float)
    good = x[np.isfinite(x)]
    if good.size == 0:
        return NAN_TERM_FILL
    return float(np.mean(good))


def _integration_band(target: Any, meh_ctx) -> tuple[float, float]:
    """C11 bass-box rule: [max(band_lo, 1.5 hp_hz), band_hi] for lw_resid and notch."""
    lo = float(target.band_lo_hz)
    hi = float(target.band_hi_hz)
    hp = _ctx_float(meh_ctx, "hp_hz", _DEFAULT_HP_HZ)
    return max(lo, 1.5 * hp), hi


# ------------------------------------------------------------------ the four terms (raw)

def lw_resid_term(target: Target, meh_ctx) -> float:
    """C11 ``lw_resid`` in dB (raw; the caller divides by the tolerance)."""
    f = _ctx_array(meh_ctx, "freqs")
    lw = _ctx_array(meh_ctx, "LW")
    if f is None or lw is None or f.size != lw.size or f.size == 0:
        return float(NAN_TERM_FILL)
    lo, hi = _integration_band(target, meh_ctx)
    band = _band(f, lo, hi) & np.isfinite(lw)
    if not band.any():
        return float(NAN_TERM_FILL)
    mean_lw = float(np.mean(lw[band]))
    s3 = smooth_oct(f, lw, 3.0)
    boost = _ctx_float(meh_ctx, "max_boost_db", _DEFAULT_MAX_BOOST_DB)
    eq = np.minimum(mean_lw - s3, boost)          # unlimited cut, boost ceiling only
    eq_lw = lw + eq
    s6 = smooth_oct(f, eq_lw, 6.0)
    good = band & np.isfinite(s6)
    if not good.any():
        return float(NAN_TERM_FILL)
    resid = s6[good] - float(np.mean(s6[good]))
    return float(np.sqrt(np.mean(resid ** 2)))


def notch_term(target: Target, meh_ctx) -> float:
    """C11 ``notch`` in dB (raw): mean of the three largest narrow dips left by 1/3-oct smoothing."""
    f = _ctx_array(meh_ctx, "freqs")
    lw = _ctx_array(meh_ctx, "LW")
    if f is None or lw is None or f.size != lw.size or f.size == 0:
        return float(NAN_TERM_FILL)
    lo, hi = _integration_band(target, meh_ctx)
    band = _band(f, lo, hi) & np.isfinite(lw)
    if not band.any():
        return float(NAN_TERM_FILL)
    s3 = smooth_oct(f, lw, 3.0)
    depth = np.maximum(0.0, s3 - lw)[band & np.isfinite(s3)]
    if depth.size == 0:
        return float(NAN_TERM_FILL)
    top = np.sort(depth)[-3:]
    return float(np.mean(top))


def _polar_plane(meh_ctx, plane: str):
    """(angles_deg, spl_db[nf, na]) for one plane, or None.

    Accepts the documented ``{"h": (angles, spl), "v": (angles, spl)}`` form and the equivalent
    dict form ``{"angles_deg": ..., "spl_db": ...}``.
    """
    if not isinstance(meh_ctx, dict):
        return None
    polars = meh_ctx.get("polars")
    if not isinstance(polars, dict):
        return None
    p = polars.get(plane)
    angles = None
    spl = None
    if isinstance(p, dict):
        angles = p.get("angles_deg")
        spl = p.get("spl_db")
    elif isinstance(p, (tuple, list)) and len(p) == 2:
        angles, spl = p
    if angles is None or spl is None:
        angles = meh_ctx.get(f"{plane}_angles_deg")
    try:
        a = np.asarray(angles, dtype=float)
        s = np.asarray(spl, dtype=float)
    except (TypeError, ValueError):
        return None
    if a.ndim != 1 or s.ndim != 2 or s.shape[1] != a.size or a.size == 0:
        return None
    return a, s


def _interp_logf(f, vals, f0: float) -> float:
    """Linearly interpolate ``vals(f)`` at ``f0`` in log2 f; endpoint-extrapolated."""
    f = np.asarray(f, dtype=float)
    vals = np.asarray(vals, dtype=float)
    good = np.isfinite(f) & (f > 0.0) & np.isfinite(vals)
    if not good.any() or not math.isfinite(f0) or f0 <= 0.0:
        return float("nan")
    x = np.log2(f[good])
    y = vals[good]
    return float(np.interp(math.log2(float(f0)), x, y))


def _on_axis_index(angles: np.ndarray) -> int | None:
    i = int(np.argmin(np.abs(angles)))
    return i if abs(float(angles[i])) <= 1e-9 else None


def xo_lob_term(target: Target, meh_ctx) -> float:
    """C11 ``xo_lob`` in dB (raw), over every crossover in ``meh_ctx['xo_hz']`` and both planes."""
    f = _ctx_array(meh_ctx, "freqs")
    if f is None or f.size == 0:
        return float(NAN_TERM_FILL)
    raw_xo = meh_ctx.get("xo_hz") if isinstance(meh_ctx, dict) else None
    if raw_xo is None or isinstance(raw_xo, bool):
        return float(NAN_TERM_FILL)
    if isinstance(raw_xo, dict):
        if "fx" in raw_xo:
            xo_seq = [raw_xo["fx"]]
        elif "lo" in raw_xo and "hi" in raw_xo:
            xo_seq = [raw_xo["lo"], raw_xo["hi"]]
        else:
            return float(NAN_TERM_FILL)
    elif isinstance(raw_xo, (int, float)) and not isinstance(raw_xo, bool):
        xo_seq = [raw_xo]
    elif isinstance(raw_xo, (list, tuple)):
        xo_seq = list(raw_xo)
    else:
        return float(NAN_TERM_FILL)
    try:
        xos = [float(x) for x in xo_seq]
    except (TypeError, ValueError):
        return float(NAN_TERM_FILL)
    xos = [x for x in xos if math.isfinite(x) and x > 0.0]
    if not xos:
        return float(NAN_TERM_FILL)

    planes = []
    for name, limit in (("h", 45.0), ("v", 30.0)):
        pp = _polar_plane(meh_ctx, name)
        if pp is None:
            continue
        angles, spl = pp
        if spl.shape[0] != f.size:
            continue
        ax = _on_axis_index(angles)
        if ax is None:
            continue
        use = np.abs(angles) <= limit + 1e-9
        if not use.any():
            continue
        # N(theta, f) = SPL - SPL(on axis), per frequency.
        normal = spl - spl[:, [ax]]
        planes.append((angles, normal, use))
    if not planes:
        return float(NAN_TERM_FILL)

    residuals = []
    for fx in xos:
        window = _band(f, fx / math.sqrt(2.0), fx * math.sqrt(2.0))
        if not window.any():
            continue
        for angles, normal, use in planes:
            n_lo = np.array([_interp_logf(f, normal[:, j], fx / 2.0)
                             for j in np.flatnonzero(use)], dtype=float)
            n_hi = np.array([_interp_logf(f, normal[:, j], 2.0 * fx)
                             for j in np.flatnonzero(use)], dtype=float)
            if not np.all(np.isfinite(n_lo)) or not np.all(np.isfinite(n_hi)):
                continue
            logpos = np.log2(f[window] / (fx / 2.0)) / 2.0       # 0 at fx/2, 1 at 2fx
            ref = n_lo[None, :] + (n_hi - n_lo)[None, :] * logpos[:, None]
            measured = normal[np.ix_(window, np.flatnonzero(use))]
            ok = np.isfinite(measured) & np.isfinite(ref)
            if ok.any():
                residuals.append((measured - ref)[ok].ravel())
    if not residuals:
        return float(NAN_TERM_FILL)
    r = np.concatenate(residuals)
    return float(np.sqrt(np.mean(r ** 2)))


def _target_curve(f: np.ndarray, raw) -> np.ndarray | None:
    """The brief's ``spl_target`` as a curve on ``f`` (knots in [Hz, dB], log-f linear)."""
    if raw is None:
        return None
    try:
        arr = np.asarray(raw, dtype=float)
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


def headroom_term(target: Target, meh_ctx) -> float:
    """C11 ``headroom`` in dB (raw): mean band shortfall against target + LR4 high-pass."""
    f = _ctx_array(meh_ctx, "freqs")
    if f is None or f.size == 0:
        return float(NAN_TERM_FILL)
    smax = _ctx_array(meh_ctx, "spl_max_db")
    if smax is None or smax.size != f.size:
        return float(NAN_TERM_FILL)
    tgt = _target_curve(f, meh_ctx.get("spl_target_db") if isinstance(meh_ctx, dict) else None)
    if tgt is None:
        return float(NAN_TERM_FILL)
    hp = _ctx_float(meh_ctx, "hp_hz", _DEFAULT_HP_HZ)
    adj = tgt + lr4_highpass_db(f, hp)
    band = _band(f, target.band_lo_hz, target.band_hi_hz) & np.isfinite(smax) & np.isfinite(adj)
    if not band.any():
        return float(NAN_TERM_FILL)
    short = np.maximum(0.0, adj[band] - smax[band])
    return float(np.mean(short))


_TERM_FUNCS = {
    "lw_resid": lw_resid_term,
    "notch": notch_term,
    "xo_lob": xo_lob_term,
    "headroom": headroom_term,
}


# ------------------------------------------------------------------ penalties / assembly

def _penalty(value: float = PENALTY_FAILED, *, n_in_band: int = 0) -> tuple[float, dict]:
    t = {k: 0.0 for k in MEH_ALL_KEYS}
    t["penalty"] = float(value)
    t["total"] = float(value)
    t["n_in_band"] = int(n_in_band)
    return float(value), t


def _v4_params(params: MehParams) -> V4Params:
    return V4Params(
        tolerances={k: float(params.tolerances[k]) for k in V4_WEIGHTED_KEYS},
        cov_narrow_ratio=params.cov_narrow_ratio,
        cov_below_f0=params.cov_below_f0,
        diag_reference=params.diag_reference,
    )


def _raw_terms(target: Any, meh_ctx) -> dict:
    return {k: float(fn(target, meh_ctx)) for k, fn in _TERM_FUNCS.items()}


def _assemble(terms: dict, weights: dict, tolerances: dict, *, n_nan: int, n_in_band: int,
              di_estimated: float) -> tuple[float, dict]:
    normalised = {k: float(terms[k]) / float(tolerances[k]) for k in MEH_WEIGHTED_KEYS}
    if not all(math.isfinite(v) for v in normalised.values()):
        return _penalty(PENALTY_FAILED, n_in_band=n_in_band)
    total = float(sum(weights[k] * normalised[k] for k in MEH_WEIGHTED_KEYS))
    if not math.isfinite(total):
        return _penalty(PENALTY_FAILED, n_in_band=n_in_band)
    out = dict(normalised)
    out["penalty"] = 0.0
    out["total"] = total
    out["n_nan"] = int(n_nan)
    out["n_in_band"] = int(n_in_band)
    out["di_estimated"] = float(di_estimated)
    assert set(out) == set(MEH_ALL_KEYS)
    return total, out


def objective_meh(metrics, resp, ok, target: Target, weights: dict | None,
                  params: MehParams | None, meh_ctx) -> tuple[float, dict]:
    """Score one evaluation under objective v5.  ``(J, terms)``; ``terms`` has ``MEH_ALL_KEYS``."""
    try:
        return _objective_meh(metrics, resp, ok, target, weights, params, meh_ctx)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective_meh() failed; returning the failure penalty")
        return _penalty(PENALTY_FAILED)


def _objective_meh(metrics, resp, ok, target, weights, params, meh_ctx):
    if metrics is None or not ok or target is None:
        return _penalty(PENALTY_FAILED)
    if params is None:
        params = MehParams.from_block({"version": 5})
    if not isinstance(params, MehParams):
        raise TypeError(f"params must be a MehParams, got {type(params).__name__}")
    w = resolve_meh_weights(weights)

    # v4 does the eight pattern terms on the SYNTHESISED response.  Its weights dict gets only the
    # v4 keys; handing it the v5 keys would make it warn about keys it does not own.
    j4, t4 = objective_v4(metrics, resp, ok, target,
                          {k: w[k] for k in V4_WEIGHTED_KEYS}, _v4_params(params))
    if float(t4.get("penalty", 0.0)) > 0.0:
        return _penalty(float(t4["penalty"]), n_in_band=int(t4.get("n_in_band", 0)))

    raw = {k: float(t4[k]) * float(params.tolerances[k]) for k in V4_WEIGHTED_KEYS}
    raw.update(_raw_terms(target, meh_ctx))
    return _assemble(raw, w, params.tolerances,
                     n_nan=int(t4.get("n_nan", 0)),
                     n_in_band=int(t4.get("n_in_band", 0)),
                     di_estimated=float(t4.get("di_estimated", 0.0)))


def inner_score(meh_ctx, weights: dict | None, params: MehParams | None = None) -> tuple[float, dict]:
    """Cheap inner score for M4's optimiser: the four system terms only, no balloon terms.

    Same definitions, tolerances and weights as :func:`objective_meh`, but no v4 pattern terms
    (there is no balloon in the inner loop).  NEVER raises; an unusable context scores the four
    terms at ``NAN_TERM_FILL`` instead.
    """
    try:
        if params is None:
            params = MehParams.from_block({"version": 5})
        w = resolve_meh_weights(weights)
        target = _InnerTarget(meh_ctx)
        raw = _raw_terms(target, meh_ctx)
        normalised = {k: float(raw[k]) / float(params.tolerances[k]) for k in MEH_EXTRA_KEYS}
        if not all(math.isfinite(v) for v in normalised.values()):
            t = {k: 0.0 for k in MEH_EXTRA_KEYS}
            t["penalty"] = float(PENALTY_FAILED)
            t["total"] = float(PENALTY_FAILED)
            return float(PENALTY_FAILED), t
        total = float(sum(w[k] * normalised[k] for k in MEH_EXTRA_KEYS))
        if not math.isfinite(total):
            t = {k: 0.0 for k in MEH_EXTRA_KEYS}
            t["penalty"] = float(PENALTY_FAILED)
            t["total"] = float(PENALTY_FAILED)
            return float(PENALTY_FAILED), t
        out = dict(normalised)
        out["penalty"] = 0.0
        out["total"] = total
        return total, out
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("inner_score() failed; returning the failure penalty")
        t = {k: 0.0 for k in MEH_EXTRA_KEYS}
        t["penalty"] = float(PENALTY_FAILED)
        t["total"] = float(PENALTY_FAILED)
        return float(PENALTY_FAILED), t


class _InnerTarget:
    """The only target fields the four system terms read; the inner loop has no brief Target.

    M7 passes the same ``meh_ctx`` the outer scorer sees; when it carries the brief band
    (``band_lo_hz``/``band_hi_hz``) the inner score uses it, otherwise it scores the whole grid.
    """

    def __init__(self, meh_ctx=None):
        ctx = meh_ctx if isinstance(meh_ctx, dict) else {}
        try:
            self.band_lo_hz = float(ctx.get("band_lo_hz", 0.0))
        except (TypeError, ValueError):
            self.band_lo_hz = 0.0
        try:
            self.band_hi_hz = float(ctx.get("band_hi_hz", float("inf")))
        except (TypeError, ValueError):
            self.band_hi_hz = float("inf")
