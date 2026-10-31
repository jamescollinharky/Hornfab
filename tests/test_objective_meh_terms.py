"""Objective v5 (M6): the four C11 system terms, on analytic inputs.

Offline, CPU only.  The task's checkable properties:

* ``lw_resid`` = 0 for a flat LW, and the RMS of a broad tilt the boost limit cannot flatten
  (here exactly 2 dB: a +10/-10 dB step, 6 dB boost ceiling, equal halves);
* ``notch``: a 10 dB, 1/12-octave dip scores >= 2.5 dB; a smooth 3 dB shelf scores < 0.3 dB;
* ``xo_lob``: a log-linearly varying polar scores < 0.1 dB; an injected 6 dB off-axis lobe at fx
  scores > 1.5 dB;
* ``headroom``: 0 when SPL_max reaches the LR4-high-pass-adjusted target; the analytic 4 dB value
  for a uniform 4 dB shortfall;
* the stored terms are normalised (raw = term x tolerance), inner_score uses the same definitions
  and never raises.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from hornlab_search.objective.scalar_meh import (
    MEH_ALL_KEYS,
    MEH_DEFAULT_TOLERANCES,
    MEH_DEFAULT_WEIGHTS,
    MEH_EXTRA_KEYS,
    MEH_WEIGHTED_KEYS,
    MehParams,
    headroom_term,
    inner_score,
    lr4_highpass_db,
    lw_resid_term,
    notch_term,
    resolve_meh_weights,
    smooth_oct,
    worst_valid_j,
    xo_lob_term,
)
from hornlab_search.objective.terms import NAN_TERM_FILL
from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
from hornlab_search.targets.spec import Target

_T = {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 120.0,
      "band_hi_hz": 12000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}


def _target(**kw):
    return Target.from_dict({**_T, **kw})


def _params(**kw):
    return MehParams.from_block({"version": 5, **kw})


# ------------------------------------------------------------------ versions + params

def test_v5_is_a_supported_version():
    assert 5 in SUPPORTED_OBJECTIVE_VERSIONS


def test_default_tolerances_and_weights_are_the_c11_table():
    p = _params()
    assert p.tolerances == MEH_DEFAULT_TOLERANCES
    assert {k: MEH_DEFAULT_WEIGHTS[k] for k in MEH_WEIGHTED_KEYS} == {
        "cov": 1.0, "rip": 0.5, "di": 0.0, "dislope": 0.3, "flat": 0.0, "load": 0.0,
        "distd": 0.5, "diag": 0.0, "lw_resid": 0.5, "notch": 1.0, "xo_lob": 1.0,
        "headroom": 1.0,
    }
    assert p.tolerances["lw_resid"] == 1.0 and p.tolerances["notch"] == 3.0
    assert p.tolerances["xo_lob"] == 1.5 and p.tolerances["headroom"] == 2.0


def test_partial_tolerance_override_keeps_the_other_defaults():
    p = _params(tolerances={"notch": 6.0})
    assert p.tolerances["notch"] == 6.0
    assert p.tolerances["lw_resid"] == 1.0 and p.tolerances["cov"] == 2.0
    assert p.to_block()["version"] == 5


@pytest.mark.parametrize("bad", [0, -1.0, float("nan"), float("inf"), True, "2", None])
def test_bad_tolerance_refuses(bad):
    with pytest.raises(ValueError, match="tolerances.notch"):
        _params(tolerances={"notch": bad})


def test_unknown_keys_refuse():
    with pytest.raises(ValueError, match="unknown key"):
        _params(bogus=1)
    with pytest.raises(ValueError, match="unknown"):
        _params(tolerances={"bogus": 1.0})
    with pytest.raises(ValueError, match="cov_narrow_ratio"):
        _params(cov_narrow_ratio=0.0)
    with pytest.raises(ValueError, match="cov_below_f0"):
        _params(cov_below_f0="free")
    with pytest.raises(ValueError, match="diag_reference"):
        _params(diag_reference="separable")


def test_worst_valid_j_orders_below_the_penalty():
    j = worst_valid_j(_params(), None)
    expect = NAN_TERM_FILL * sum(
        MEH_DEFAULT_WEIGHTS[k] / MEH_DEFAULT_TOLERANCES[k] for k in MEH_WEIGHTED_KEYS)
    assert j == pytest.approx(expect, rel=1e-12)
    assert j < 0.5 * 1000.0
    assert worst_valid_j(_params(tolerances={"notch": 1e-3}), {"notch": 1.0}) > 0.5 * 1000.0


def test_unknown_weight_warns_and_keeps_the_default(caplog):
    w = resolve_meh_weights({"notch": 2.0, "bogus": 1.0, "headroom": "x"})
    assert w["notch"] == 2.0 and w["headroom"] == MEH_DEFAULT_WEIGHTS["headroom"]
    assert "unknown objective weight" in caplog.text


# ------------------------------------------------------------------ smoothing

def test_smooth_oct_of_a_constant_is_the_constant():
    f = np.geomspace(200.0, 8000.0, 20)
    assert np.allclose(smooth_oct(f, np.full(f.size, -12.0), 3.0), -12.0, atol=1e-12)


# ------------------------------------------------------------------ lw_resid

def test_lw_resid_is_zero_for_a_flat_listening_window():
    f = np.geomspace(200.0, 12000.0, 30)
    ctx = {"freqs": f, "LW": np.zeros(f.size), "hp_hz": 120.0, "max_boost_db": 6.0}
    assert lw_resid_term(_target(), ctx) == pytest.approx(0.0, abs=1e-12)


def test_lw_resid_is_the_analytic_rms_of_a_broad_tilt_over_the_boost_limit():
    # 24 points, equal halves, spacing 0.257 octave >> S6's 1/12-octave window, so smoothing is
    # the identity on this grid.  LW = +10 dB then -10 dB.  mean = 0; the +10 dB half is cut by
    # 10 dB (unlimited), the -10 dB half can only be boosted by 6 dB, so LW+E = 0 then -4 dB.
    # Residual about its own mean = +2 / -2 dB -> RMS = 2 dB.  Analytic, not fitted.
    f = np.geomspace(200.0, 12000.0, 24)
    lw = np.where(np.arange(f.size) < 12, 10.0, -10.0)
    ctx = {"freqs": f, "LW": lw, "hp_hz": 120.0, "max_boost_db": 6.0}
    assert lw_resid_term(_target(), ctx) == pytest.approx(2.0, rel=1e-9)

    # With enough boost the same tilt is flattened completely: E = mean - LW on both halves.
    ctx["max_boost_db"] = 20.0
    assert lw_resid_term(_target(), ctx) == pytest.approx(0.0, abs=1e-12)


def test_lw_resid_uses_the_bass_integration_band():
    # A huge defect below max(band_lo, 1.5 hp) is outside the scoring band and costs nothing.
    f = np.geomspace(60.0, 12000.0, 60)
    lw = np.zeros(f.size)
    lw[f < 150.0] = 40.0          # below 1.5 hp = 180 Hz, and below S3's window at 180 Hz
    ctx = {"freqs": f, "LW": lw, "hp_hz": 120.0, "max_boost_db": 6.0}
    t = _target(band_lo_hz=120.0)
    assert lw_resid_term(t, ctx) < 0.2


# ------------------------------------------------------------------ notch

def test_notch_scores_a_narrow_dip_and_ignores_a_smooth_shelf():
    f = 2.0 ** np.arange(np.log2(120.0), np.log2(12000.0), 1 / 48.0)
    dip = np.zeros(f.size)
    dip[np.abs(np.log2(f / 1000.0)) <= 1 / 24.0] = -10.0       # 1/12 octave wide, 10 dB deep
    assert notch_term(_target(), {"freqs": f, "LW": dip, "hp_hz": 120.0}) >= 2.5

    shelf = 1.5 * (1.0 + np.tanh(np.log2(f / 1000.0) / 2.0))   # smooth 3 dB shelf over 4 octaves
    assert notch_term(_target(), {"freqs": f, "LW": shelf, "hp_hz": 120.0}) < 0.3


def test_notch_is_zero_without_a_dip():
    f = np.geomspace(200.0, 12000.0, 40)
    assert notch_term(_target(), {"freqs": f, "LW": np.zeros(f.size)}) == pytest.approx(0.0)


# ------------------------------------------------------------------ xo_lob

_FX = 800.0
_H = np.array([-45.0, -30.0, 0.0, 30.0, 45.0])
_V = np.array([-30.0, 0.0, 30.0])


def _xo_ctx(spl_h, spl_v, fx=_FX):
    f = 2.0 ** np.arange(np.log2(fx / 4.0), np.log2(fx * 4.0), 1 / 24.0)
    return {"freqs": f, "xo_hz": [fx],
            "polars": {"h": (_H, np.asarray(spl_h, float)),
                       "v": (_V, np.asarray(spl_v, float))}}


def _linear_polars(fx=_FX):
    f = 2.0 ** np.arange(np.log2(fx / 4.0), np.log2(fx * 4.0), 1 / 24.0)
    bh = np.cos(np.radians(_H)) ** 2
    bv = np.cos(np.radians(_V)) ** 2
    sh = np.array([[b * np.log2(ff / fx) for b in bh] for ff in f])
    sv = np.array([[b * np.log2(ff / fx) for b in bv] for ff in f])
    return sh, sv


def test_xo_lob_is_zero_for_log_linear_polars():
    sh, sv = _linear_polars()
    assert xo_lob_term(_target(), _xo_ctx(sh, sv)) < 0.1


def test_xo_lob_scores_an_off_axis_lobe_at_the_crossover():
    sh, sv = _linear_polars()
    f = 2.0 ** np.arange(np.log2(_FX / 4.0), np.log2(_FX * 4.0), 1 / 24.0)
    bump = lambda angles: np.array(                       # noqa: E731 - a test fixture
        [[6.0 * math.exp(-0.5 * (np.log2(ff / _FX) / 0.2) ** 2) if a != 0.0 else 0.0
          for a in angles] for ff in f])
    assert xo_lob_term(_target(), _xo_ctx(sh + bump(_H), sv + bump(_V))) > 1.5


def test_xo_lob_is_the_unflattering_fill_without_polars():
    assert xo_lob_term(_target(), {"freqs": np.geomspace(200, 12000, 20), "xo_hz": [800.0]}) \
        == pytest.approx(NAN_TERM_FILL)


# ------------------------------------------------------------------ headroom

def test_lr4_highpass_is_minus_6db_at_the_corner():
    assert float(lr4_highpass_db(np.array([120.0]), 120.0)[0]) == pytest.approx(
        10.0 * math.log10(0.5), rel=1e-12)


def test_headroom_is_zero_when_the_ceiling_reaches_the_adjusted_target():
    f = np.geomspace(120.0, 12000.0, 40)
    target_db = np.full(f.size, 120.0)
    ctx = {"freqs": f, "spl_target_db": [[120.0, 120.0], [12000.0, 120.0]],
           "hp_hz": 120.0, "spl_max_db": target_db + lr4_highpass_db(f, 120.0) + 3.0}
    assert headroom_term(_target(), ctx) == pytest.approx(0.0)


def test_headroom_is_the_analytic_uniform_shortfall():
    f = np.geomspace(120.0, 12000.0, 40)
    target_db = np.full(f.size, 120.0)
    adjusted = target_db + lr4_highpass_db(f, 120.0)
    ctx = {"freqs": f, "spl_target_db": [[120.0, 120.0], [12000.0, 120.0]],
           "hp_hz": 120.0, "spl_max_db": adjusted - 4.0}
    assert headroom_term(_target(), ctx) == pytest.approx(4.0, rel=1e-12)


def test_headroom_accepts_the_brief_knots_and_interpolates_in_log_f():
    f = np.array([500.0])
    ctx = {"freqs": f, "spl_target_db": [[250.0, 100.0], [1000.0, 120.0]],
           "hp_hz": 60.0, "spl_max_db": np.array([0.0])}
    # 500 Hz is the geometric midpoint of 250..1000 Hz (one octave either side), so log
    # interpolation gives 110 dB; the 60 Hz LR4 corner is nearly transparent.
    expect = 110.0 + float(lr4_highpass_db(f, 60.0)[0])
    assert headroom_term(_target(), ctx) == pytest.approx(expect, rel=1e-9)


# ------------------------------------------------------------------ inner_score

def test_inner_score_is_weighted_and_normalised():
    # 0.257 octave spacing: S6's 1/12-octave window sees only the point itself, so the injected
    # LW step has the same exact 2 dB residual as the lw_resid test above.
    f = np.geomspace(200.0, 12000.0, 24)
    bh = np.cos(np.radians(_H)) ** 2
    bv = np.cos(np.radians(_V)) ** 2
    sh = np.array([[b * np.log2(ff / _FX) for b in bh] for ff in f])
    sv = np.array([[b * np.log2(ff / _FX) for b in bv] for ff in f])
    tgt = np.full(f.size, 120.0)
    ctx = {"freqs": f, "LW": np.zeros(f.size),
           "xo_hz": [_FX], "polars": {"h": (_H, sh), "v": (_V, sv)},
           "spl_target_db": [[100.0, 120.0], [16000.0, 120.0]], "hp_hz": 60.0,
           "spl_max_db": tgt + lr4_highpass_db(f, 60.0) + 1.0,
           "band_lo_hz": 120.0, "band_hi_hz": 12000.0}
    j, terms = inner_score(ctx, None)
    assert j == pytest.approx(0.0, abs=1e-9)
    assert set(terms) == set(MEH_EXTRA_KEYS) | {"penalty", "total"}
    assert terms["total"] == pytest.approx(j)

    # Inject the broad 2 dB lw residual: 0.5 weight / 1.0 dB tolerance -> 1.0.
    lw = np.where(np.arange(f.size) < f.size // 2, 10.0, -10.0)
    ctx["LW"] = lw
    j2, t2 = inner_score(ctx, {"lw_resid": 0.5})
    assert t2["lw_resid"] == pytest.approx(2.0, rel=1e-9)
    assert j2 == pytest.approx(1.0, rel=1e-9)


def test_inner_score_never_raises_on_an_unusable_context():
    j, terms = inner_score(None, None)
    assert math.isfinite(j) and j > 0.0
    assert set(terms) == set(MEH_EXTRA_KEYS) | {"penalty", "total"}
