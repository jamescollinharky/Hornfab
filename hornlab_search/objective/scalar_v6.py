"""Objective v6 (2026-11-05): loading_smooth — Le Cléac'h / rollback class.

Why (docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md): CD-shaped v4 remapping
(``dislope: 0``, ``load: 0.5``) kept the wrong *math* — band-mean loading was diluted to ~2 % of J
and coverage still punished natural narrowing. v6 scores resistive load near the loading corner,
impedance smoothness (mouth-reflectance proxy), coverage only above ``pattern_beta · fc``, and a
natural DI rise (~+5 dB/decade), with the same tolerance normalisation as v4:

    J = sum_k  w_k * term_k / tol_k  + penalty

Stored ``terms`` are the normalised values. Never raises; never returns nan/inf.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

from ..metrics.di import di_slope_db_per_decade
from ..targets.spec import Target
from .scalar import penalty_result
from .scalar_v2 import (_plain_mean, _v2_flat_value, _v2_ripple_values, _weighted_mean,
                        freq_weight_vector)
from .scalar_v4 import _cov_term, _diag_term
from .terms import NAN_TERM_FILL, PENALTY_FAILED

log = logging.getLogger("hornlab_search.objective.scalar_v6")

__all__ = ["objective_v6", "V6Params", "V6_WEIGHTED_KEYS", "V6_ALL_KEYS", "V6_DEFAULT_WEIGHTS",
           "V6_DEFAULT_TOLERANCES", "worst_valid_v6_j", "resolve_fc_hz"]

V6_WEIGHTED_KEYS = ("load_near", "z_smooth", "flat", "rip", "cov_pat", "di_rise", "distd", "diag")
V6_BOOKKEEPING = ("penalty", "total", "n_nan", "n_in_band", "di_estimated")
V6_ALL_KEYS = V6_WEIGHTED_KEYS + V6_BOOKKEEPING

V6_DEFAULT_WEIGHTS = {
    "load_near": 1.0,
    "z_smooth": 0.8,
    "flat": 0.5,
    "rip": 0.8,
    "cov_pat": 0.3,
    "di_rise": 0.4,
    "distd": 0.3,
    "diag": 0.0,
}

#: Physical-ish starting tolerances (dossier §3.2); briefs must still list every key.
V6_DEFAULT_TOLERANCES = {
    "load_near": 0.25,
    "z_smooth": 0.15,
    "flat": 1.5,
    "rip": 2.0,
    "cov_pat": 15.0,
    "di_rise": 4.0,
    "distd": 2.0,
    "diag": 4.5,
}

_COV_BELOW_F0 = ("mask", "one_sided")
_DIAG_REFERENCES = ("round",)
_BLOCK_KEYS = {
    "version", "tolerances", "cov_narrow_ratio", "cov_below_f0", "diag_reference",
    "load_alpha", "pattern_beta", "fc_hz",
}


@dataclass(frozen=True)
class V6Params:
    """The ``objective:`` block of a v6 brief. Tolerances have NO silent defaults."""

    tolerances: dict
    cov_narrow_ratio: float = 1.0
    cov_below_f0: str = "one_sided"
    diag_reference: str = "round"
    load_alpha: float = 1.0
    pattern_beta: float = 1.6
    fc_hz: float | None = None

    @classmethod
    def from_block(cls, block: dict) -> "V6Params":
        if not isinstance(block, dict):
            raise ValueError("objective must be a mapping")
        unknown = set(block) - _BLOCK_KEYS
        if unknown:
            raise ValueError(f"objective unknown key(s) {sorted(unknown)} "
                             f"(allowed for v6: {sorted(_BLOCK_KEYS)})")
        tol = block.get("tolerances")
        if not isinstance(tol, dict):
            raise ValueError("objective v6 needs a 'tolerances' mapping with one entry per term: "
                             f"{list(V6_WEIGHTED_KEYS)}")
        missing = [k for k in V6_WEIGHTED_KEYS if k not in tol]
        extra = sorted(set(tol) - set(V6_WEIGHTED_KEYS))
        if missing or extra:
            raise ValueError(f"objective.tolerances: missing {missing}, unknown {extra} "
                             f"(required: {list(V6_WEIGHTED_KEYS)})")
        clean: dict = {}
        for k in V6_WEIGHTED_KEYS:
            v = tol[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or not math.isfinite(float(v)) or not float(v) > 0.0:
                raise ValueError(f"objective.tolerances.{k} must be a finite number > 0, got {v!r}")
            clean[k] = float(v)

        def _pos(name: str, default: float) -> float:
            v = block.get(name, default)
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or not math.isfinite(float(v)) or not float(v) > 0.0:
                raise ValueError(f"objective.{name} must be a finite number > 0, got {v!r}")
            return float(v)

        ratio = _pos("cov_narrow_ratio", 1.0)
        alpha = _pos("load_alpha", 1.0)
        beta = _pos("pattern_beta", 1.6)
        below = block.get("cov_below_f0", "one_sided")
        if below not in _COV_BELOW_F0:
            raise ValueError(f"objective.cov_below_f0 must be one of {list(_COV_BELOW_F0)}, got {below!r}")
        ref = block.get("diag_reference", "round")
        if ref not in _DIAG_REFERENCES:
            raise ValueError(f"objective.diag_reference must be one of {list(_DIAG_REFERENCES)}, got {ref!r}")
        fc = block.get("fc_hz", None)
        if fc is not None:
            if isinstance(fc, bool) or not isinstance(fc, (int, float)) \
                    or not math.isfinite(float(fc)) or not float(fc) > 0.0:
                raise ValueError(f"objective.fc_hz must be a finite number > 0 when set, got {fc!r}")
            fc = float(fc)
        return cls(tolerances=clean, cov_narrow_ratio=ratio, cov_below_f0=str(below),
                   diag_reference=str(ref), load_alpha=alpha, pattern_beta=beta, fc_hz=fc)

    def to_block(self) -> dict:
        out = {
            "version": 6,
            "tolerances": dict(self.tolerances),
            "cov_narrow_ratio": self.cov_narrow_ratio,
            "cov_below_f0": self.cov_below_f0,
            "diag_reference": self.diag_reference,
            "load_alpha": self.load_alpha,
            "pattern_beta": self.pattern_beta,
        }
        if self.fc_hz is not None:
            out["fc_hz"] = self.fc_hz
        return out


def resolve_v6_weights(weights: dict | None) -> dict:
    out = dict(V6_DEFAULT_WEIGHTS)
    for k, v in (weights or {}).items():
        if k in V6_DEFAULT_WEIGHTS:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                log.warning("weight %r=%r is not a number; using the default %r", k, v, out[k])
        else:
            log.warning("unknown objective weight %r ignored (known: %s)",
                        k, sorted(V6_DEFAULT_WEIGHTS))
    return out


def worst_valid_v6_j(params: V6Params, weights: dict | None) -> float:
    w = resolve_v6_weights(weights)
    return float(sum(w[k] * NAN_TERM_FILL / params.tolerances[k] for k in V6_WEIGHTED_KEYS))


def resolve_fc_hz(target: Target, params: V6Params, metrics=None) -> float:
    """Loading-corner frequency: params.fc_hz → metrics.scalars['fc_hz'] → target.f0 → band_lo."""
    if params.fc_hz is not None:
        return float(params.fc_hz)
    if metrics is not None:
        sc = getattr(metrics, "scalars", None) or {}
        for key in ("fc_hz", "g_fc_hz"):
            v = sc.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)) \
                    and float(v) > 0.0:
                return float(v)
    f0 = target.f0_effective_hz()
    if math.isfinite(f0) and f0 > 0.0:
        return float(f0)
    return float(target.band_lo_hz)


def _v6_penalty(value: float = PENALTY_FAILED, *, n_in_band: int = 0) -> tuple[float, dict]:
    j, t0 = penalty_result(value, n_in_band=n_in_band)
    t = {k: 0.0 for k in V6_WEIGHTED_KEYS}
    t["penalty"] = float(t0["penalty"])
    t["total"] = float(t0["total"])
    t["n_nan"] = int(t0.get("n_nan", 0))
    t["n_in_band"] = int(t0.get("n_in_band", n_in_band))
    t["di_estimated"] = float(t0.get("di_estimated", 0.0))
    return j, t


def objective_v6(metrics, resp, ok, target: Target, weights: dict | None, params: V6Params):
    try:
        return _objective_v6(metrics, resp, ok, target, weights, params)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective_v6() failed; returning the failure penalty")
        return _v6_penalty(PENALTY_FAILED)


def _load_near_term(f: np.ndarray, z_real, target: Target, params: V6Params,
                    fc_hz: float, scalars: dict) -> float:
    """Mean under-load hinge on [band_lo, f_load_hi] plus soft f_loaded hinge."""
    f0 = float(target.f0_effective_hz())
    f_load_hi = max(f0, float(params.load_alpha) * float(fc_hz))
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz) & (f <= f_load_hi)
    if z_real is None:
        hinge = NAN_TERM_FILL
    else:
        z = np.asarray(z_real, dtype=float)
        if not band.any():
            hinge = NAN_TERM_FILL
        else:
            deficit = np.maximum(0.0, float(target.z_min) - z)
            if target.freq_weights is not None:
                m, _ = _weighted_mean(deficit[band], freq_weight_vector(f, target)[band])
            else:
                m, _ = _plain_mean(deficit[band])
            hinge = float(m)
    # Soft corner: how far above f0 the throat first stays loaded.
    f_loaded = scalars.get("f_loaded_hz", scalars.get("f_load_hz", float("nan")))
    soft = 0.0
    if isinstance(f_loaded, (int, float)) and not isinstance(f_loaded, bool) \
            and math.isfinite(float(f_loaded)) and f0 > 0.0:
        soft = max(0.0, (float(f_loaded) - f0) / f0)
    return float(hinge + soft)


def _z_smooth_term(f: np.ndarray, z_real, target: Target) -> float:
    if z_real is None:
        return NAN_TERM_FILL
    z = np.asarray(z_real, dtype=float)
    f0 = float(target.f0_effective_hz())
    sel = (f >= target.band_lo_hz) & (f <= target.band_hi_hz) & (f >= f0) & np.isfinite(z)
    good = z[sel]
    if good.size < 2:
        return NAN_TERM_FILL if good.size == 0 else 0.0
    return float(np.std(good))


def _cov_pat_term(metrics, target: Target, f: np.ndarray, band: np.ndarray,
                  params: V6Params, f_pattern: float) -> float:
    """Coverage scored primarily above ``f_pattern``; below that, optional one-sided narrow-only."""
    # Build a synthetic Target-like scoring window by masking frequencies below f_pattern out of
    # the "above f0" path: reuse v4's _cov_term with a temporary f0 = f_pattern when mask mode,
    # or score the full band with one_sided relative to f_pattern.
    class _PatTarget:
        """Minimal stand-in so _cov_term uses f_pattern as the plane f0."""
        coverage_h_deg = target.coverage_h_deg
        coverage_v_deg = target.coverage_v_deg
        freq_weights = target.freq_weights
        f0_v_hz = None

        def f0_effective_hz(self):
            return float(f_pattern)

    # Bridge: wrap params so _cov_term sees cov_narrow_ratio / cov_below_f0.
    class _PatParams:
        cov_narrow_ratio = params.cov_narrow_ratio
        cov_below_f0 = params.cov_below_f0

    return float(_cov_term(metrics, _PatTarget(), f, band, _PatParams()))


def _di_rise_term(f: np.ndarray, di_db, target: Target) -> float:
    f0 = float(target.f0_effective_hz())
    score = (f >= target.band_lo_hz) & (f <= target.band_hi_hz) & (f >= f0)
    s = di_slope_db_per_decade(f[score], np.asarray(di_db, dtype=float)[score])
    if not np.isfinite(s):
        return 0.0
    return float((s - float(target.di_slope_target)) ** 2)


def _objective_v6(metrics, resp, ok, target: Target, weights, params: V6Params):
    if metrics is None or not ok:
        return _v6_penalty(PENALTY_FAILED)
    w = resolve_v6_weights(weights)
    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    n_band = int(band.sum())
    if n_band == 0:
        return _v6_penalty(PENALTY_FAILED, n_in_band=0)

    scalars = dict(getattr(metrics, "scalars", None) or {})
    fc_hz = resolve_fc_hz(target, params, metrics)
    f_pattern = float(params.pattern_beta) * fc_hz
    f0 = float(target.f0_effective_hz())
    score = band & (f >= f0)

    t_raw = {
        "load_near": _load_near_term(f, metrics.z_throat_real, target, params, fc_hz, scalars),
        "z_smooth": _z_smooth_term(f, metrics.z_throat_real, target),
        "cov_pat": _cov_pat_term(metrics, target, f, band, params, f_pattern),
        "di_rise": _di_rise_term(f, metrics.di_db, target),
    }

    # rip / flat — detrended when Response allows (v2 helpers).
    ripple_values, _ = _v2_ripple_values(metrics, resp, target, band)
    if target.freq_weights is not None:
        rip, _ = _weighted_mean(ripple_values[band], freq_weight_vector(f, target)[band])
    else:
        rip, _ = _plain_mean(ripple_values[band])
    t_raw["rip"] = float(rip)
    t_raw["flat"] = float(_v2_flat_value(metrics, resp, target, band))

    if w["distd"] != 0.0:
        di_s = np.asarray(metrics.di_db, dtype=float)[score]
        good = di_s[np.isfinite(di_s)]
        t_raw["distd"] = float(np.std(good)) if good.size >= 2 else 0.0
    else:
        t_raw["distd"] = 0.0

    if w["diag"] != 0.0:
        # Reuse v4 diag against the score band above f0 (not f_pattern): crease honesty.
        class _V4ish:
            cov_narrow_ratio = params.cov_narrow_ratio
            cov_below_f0 = params.cov_below_f0
            diag_reference = params.diag_reference
        t_raw["diag"] = float(_diag_term(metrics, resp, target, f, score, _V4ish()))
    else:
        t_raw["diag"] = 0.0

    t = {k: t_raw[k] / params.tolerances[k] for k in V6_WEIGHTED_KEYS}
    if not all(math.isfinite(v) for v in t.values()):
        return _v6_penalty(PENALTY_FAILED, n_in_band=n_band)
    total = sum(w[k] * t[k] for k in V6_WEIGHTED_KEYS)
    if not math.isfinite(total):
        return _v6_penalty(PENALTY_FAILED, n_in_band=n_band)

    bad = np.zeros(n_band, dtype=bool)
    for arr in (metrics.bw_h_deg, metrics.bw_v_deg, metrics.on_axis_db, metrics.di_db):
        bad |= ~np.isfinite(np.asarray(arr, dtype=float)[band])
    bad |= ~np.isfinite(ripple_values[band])
    if metrics.z_throat_real is not None:
        bad |= ~np.isfinite(np.asarray(metrics.z_throat_real, dtype=float)[band])

    t["penalty"] = 0.0
    t["total"] = float(total)
    t["n_nan"] = int(bad.sum())
    t["n_in_band"] = n_band
    t["di_estimated"] = 1.0 if metrics.di_source == "cuts_estimate" else 0.0
    assert set(t) == set(V6_ALL_KEYS)
    return float(total), t
