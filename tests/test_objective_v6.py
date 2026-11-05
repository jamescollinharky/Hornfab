"""Objective v6 (loading_smooth): near-fc loading, z-smoothness, pattern-band cov, DI rise.

Offline, CPU only. Pins from docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md:

* every weighted term needs a positive finite tolerance; penalty-ordering at config load;
* constant Re z >= z_min -> load_near ~0; sinusoidal Re z -> z_smooth rises;
* DI rising at di_slope_target -> di_rise ~0;
* beamwidth wrong only below f_pattern -> cov_pat ~0 (one_sided / mask above pattern);
* version 6 is registered and config round-trips.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.config import ConfigError, _validate_objective_block
from hornlab_search.objective.scalar_v6 import (
    V6_ALL_KEYS,
    V6_DEFAULT_TOLERANCES,
    V6_DEFAULT_WEIGHTS,
    V6_WEIGHTED_KEYS,
    V6Params,
    objective_v6,
    resolve_fc_hz,
    worst_valid_v6_j,
)
from hornlab_search.objective.terms import NAN_TERM_FILL, PENALTY_FAILED, PENALTY_INVALID
from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

_T = {
    "coverage_h_deg": 90.0,
    "coverage_v_deg": 90.0,
    "band_lo_hz": 300.0,
    "band_hi_hz": 8000.0,
    "di_target_db": None,
    "di_slope_target": 5.0,
    "z_min": 0.7,
    "f0_hz": 1200.0,
}


def _params(tol=None, **kw) -> V6Params:
    block = {
        "version": 6,
        "tolerances": dict(V6_DEFAULT_TOLERANCES if tol is None else tol),
        **kw,
    }
    return V6Params.from_block(block)


def _target(**kw) -> Target:
    return Target.from_dict({**_T, **kw})


def _metrics(freqs, t: Target, *, bw_h=None, bw_v=None, di=None, z=None,
             scalars=None) -> MetricSet:
    f = np.asarray(freqs, dtype=float)
    return MetricSet(
        freqs_hz=f,
        bw_h_deg=np.full(f.size, t.coverage_h_deg) if bw_h is None else np.asarray(bw_h, float),
        bw_v_deg=np.full(f.size, t.coverage_v_deg) if bw_v is None else np.asarray(bw_v, float),
        di_db=np.full(f.size, 8.0) if di is None else np.asarray(di, float),
        di_source="balloon",
        ripple_h_db=np.zeros(f.size),
        ripple_v_db=np.zeros(f.size),
        on_axis_db=np.zeros(f.size),
        z_throat_real=None if z is None else np.asarray(z, float),
        scalars=dict(scalars or {}),
    )


def test_v6_is_a_supported_version():
    assert 6 in SUPPORTED_OBJECTIVE_VERSIONS


def test_params_require_every_tolerance():
    for k in V6_WEIGHTED_KEYS:
        tol = {j: 1.0 for j in V6_WEIGHTED_KEYS if j != k}
        with pytest.raises(ValueError, match="missing"):
            V6Params.from_block({"version": 6, "tolerances": tol})


def test_params_reject_bad_and_unknown():
    with pytest.raises(ValueError, match="unknown key"):
        V6Params.from_block({"version": 6, "tolerances": V6_DEFAULT_TOLERANCES, "bogus": 1})
    with pytest.raises(ValueError, match="pattern_beta"):
        _params(pattern_beta=0.0)
    with pytest.raises(ValueError, match="fc_hz"):
        _params(fc_hz=-10)


def test_config_block_round_trips():
    out = _validate_objective_block(
        {"version": 6, "tolerances": V6_DEFAULT_TOLERANCES, "pattern_beta": 1.7,
         "load_alpha": 1.1, "fc_hz": 800.0},
        "t.yaml",
    )
    assert out["version"] == 6 and out["pattern_beta"] == 1.7 and out["fc_hz"] == 800.0
    with pytest.raises(ConfigError, match="t.yaml"):
        _validate_objective_block({"version": 6}, "t.yaml")


def test_penalty_ordering_gate():
    # Defaults stay well under half the refusal penalty.
    assert worst_valid_v6_j(_params(), V6_DEFAULT_WEIGHTS) < 0.5 * PENALTY_INVALID


def test_resolve_fc_hz_precedence():
    t = _target(f0_hz=1200.0)
    p = _params(fc_hz=900.0)
    m = _metrics(np.array([500.0, 1000.0]), t, scalars={"fc_hz": 700.0})
    assert resolve_fc_hz(t, p, m) == 900.0          # params win
    assert resolve_fc_hz(t, _params(), m) == 700.0  # then scalars
    assert resolve_fc_hz(t, _params(), None) == 1200.0


def test_constant_loaded_z_gives_near_zero_load_near():
    t = _target()
    f = np.geomspace(300.0, 8000.0, 21)
    m = _metrics(f, t, z=np.ones(f.size))  # Re z = 1.0 >= z_min 0.7 everywhere
    j, terms = objective_v6(m, None, True, t, V6_DEFAULT_WEIGHTS, _params())
    assert math.isfinite(j)
    assert set(terms) == set(V6_ALL_KEYS)
    # Raw load_near = terms * tol; should be ~0 (no soft hinge without f_load).
    raw = terms["load_near"] * V6_DEFAULT_TOLERANCES["load_near"]
    assert raw < 1e-9


def test_underloaded_near_fc_raises_load_near():
    t = _target()
    f = np.geomspace(300.0, 8000.0, 21)
    z = np.ones(f.size)
    z[f <= 1200.0] = 0.1                     # dead below / at the loading corner
    m = _metrics(f, t, z=z)
    _, terms_bad = objective_v6(m, None, True, t, V6_DEFAULT_WEIGHTS, _params())
    m_ok = _metrics(f, t, z=np.ones(f.size))
    _, terms_ok = objective_v6(m_ok, None, True, t, V6_DEFAULT_WEIGHTS, _params())
    assert terms_bad["load_near"] > terms_ok["load_near"] + 0.5


def test_sinusoidal_z_raises_z_smooth():
    t = _target()
    f = np.geomspace(300.0, 8000.0, 41)
    m_flat = _metrics(f, t, z=np.ones(f.size))
    m_rip = _metrics(f, t, z=1.0 + 0.4 * np.sin(np.linspace(0, 8 * np.pi, f.size)))
    _, t_flat = objective_v6(m_flat, None, True, t, V6_DEFAULT_WEIGHTS, _params())
    _, t_rip = objective_v6(m_rip, None, True, t, V6_DEFAULT_WEIGHTS, _params())
    assert t_rip["z_smooth"] > t_flat["z_smooth"] + 0.5


def test_di_rise_zero_at_target_slope():
    t = _target(di_slope_target=5.0)
    f = np.geomspace(300.0, 8000.0, 25)
    # DI = 5 * log10(f/f_ref) -> slope +5 dB/decade.
    di = 5.0 * np.log10(f / 1000.0) + 6.0
    m = _metrics(f, t, di=di, z=np.ones(f.size))
    _, terms = objective_v6(m, None, True, t, V6_DEFAULT_WEIGHTS, _params())
    raw = terms["di_rise"] * V6_DEFAULT_TOLERANCES["di_rise"]
    assert raw < 1e-6


def test_cov_pat_ignores_errors_below_f_pattern():
    t = _target(f0_hz=1000.0)
    # fc = f0 = 1000; f_pattern = 1.6 * 1000 = 1600.
    f = np.array([500.0, 800.0, 1200.0, 2000.0, 4000.0, 6000.0])
    bw_h = np.array([180.0, 160.0, 140.0, 90.0, 90.0, 90.0])  # wrong below pattern, perfect above
    bw_v = bw_h.copy()
    m = _metrics(f, t, bw_h=bw_h, bw_v=bw_v, z=np.ones(f.size))
    # mask mode: only f >= f_pattern scored -> near zero.
    _, terms_mask = objective_v6(
        m, None, True, t, V6_DEFAULT_WEIGHTS, _params(cov_below_f0="mask", pattern_beta=1.6))
    raw_mask = terms_mask["cov_pat"] * V6_DEFAULT_TOLERANCES["cov_pat"]
    assert raw_mask < 1e-9
    # If we lower pattern_beta so 1200 is scored, the 140 deg miss must raise cov_pat.
    _, terms_low = objective_v6(
        m, None, True, t, V6_DEFAULT_WEIGHTS, _params(cov_below_f0="mask", pattern_beta=1.0))
    assert terms_low["cov_pat"] > terms_mask["cov_pat"] + 0.05


def test_failure_returns_penalty_and_key_set():
    j, terms = objective_v6(None, None, False, _target(), V6_DEFAULT_WEIGHTS, _params())
    assert j == PENALTY_FAILED
    assert set(terms) == set(V6_ALL_KEYS)
    assert terms["penalty"] == PENALTY_FAILED


def test_shipped_v6_briefs_load():
    root = Path(__file__).resolve().parents[1] / "examples" / "briefs"
    paths = [
        root / "campaign_2026-10-26_v6" / "native_lecleach_1200_1in_v6.yaml",
        root / "lecleach_rollback_1in_v6.yaml",
    ]
    for p in paths:
        raw = yaml.safe_load(p.read_text())
        block = _validate_objective_block(raw["objective"], str(p))
        assert block["version"] == 6
        params = V6Params.from_block(block)
        # Penalty ordering must hold with the brief's own weights.
        assert worst_valid_v6_j(params, raw["weights"]) < 0.5 * PENALTY_INVALID


def test_missing_z_uses_nan_fill_not_zero_reward():
    t = _target()
    f = np.geomspace(300.0, 8000.0, 11)
    m = _metrics(f, t, z=None)
    _, terms = objective_v6(m, None, True, t, V6_DEFAULT_WEIGHTS, _params())
    assert terms["load_near"] == pytest.approx(NAN_TERM_FILL / V6_DEFAULT_TOLERANCES["load_near"])
    assert terms["z_smooth"] == pytest.approx(NAN_TERM_FILL / V6_DEFAULT_TOLERANCES["z_smooth"])
