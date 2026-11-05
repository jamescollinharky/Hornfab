"""Objective v5 composition (M6).

Offline, CPU only.  Pins:

* ``J = sum_k w_k * term_k / tol_k + penalty`` over the twelve v5 terms, and the stored terms are
  normalised (raw = term x tolerance), exactly like v4;
* with the four new weights at zero, v5's pattern half IS v4 (same v4 functions, same tolerances);
* a failed evaluation returns the v4-style finite penalty with the full v5 key set;
* ``objective: {version: 5}`` loads (the C11 tolerances are the defaults), the config refuses
  tolerances that let an all-unmeasurable valid design outrank a refusal, and v1-v4 blocks are
  byte-identical;
* the search dispatch bridge registers v5 so ``search/evaluate.py``'s version gate stays in
  lock-step (M7 replaces the MEH branch with the real ``meh_ctx`` path).
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.config import ConfigError, _validate_objective_block, load_config
from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective.scalar_meh import (
    MEH_ALL_KEYS,
    MEH_DEFAULT_TOLERANCES,
    MEH_DEFAULT_WEIGHTS,
    MEH_EXTRA_KEYS,
    MEH_WEIGHTED_KEYS,
    MehParams,
    objective_meh,
)
from hornlab_search.objective.scalar_v4 import V4_WEIGHTED_KEYS, V4Params, objective_v4
from hornlab_search.objective.terms import NAN_TERM_FILL, PENALTY_FAILED
from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

_T = {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 120.0,
      "band_hi_hz": 12000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}


def _target(**kw):
    return Target.from_dict({**_T, **kw})


def _metrics(f, t: Target) -> MetricSet:
    f = np.asarray(f, dtype=float)
    ref = target_di_gaussian_db(t.coverage_h_deg, t.coverage_v_deg)
    return MetricSet(
        freqs_hz=f,
        bw_h_deg=np.full(f.size, t.coverage_h_deg),
        bw_v_deg=np.full(f.size, t.coverage_v_deg),
        di_db=np.full(f.size, ref),
        di_source="balloon", ripple_h_db=np.zeros(f.size), ripple_v_db=np.zeros(f.size),
        on_axis_db=np.zeros(f.size), z_throat_real=None, scalars={})


def _flat_ctx(f):
    """All four system terms zero: flat LW, log-linear polars, target reached everywhere."""
    fx = 800.0
    angles_h = np.array([-45.0, -30.0, 0.0, 30.0, 45.0])
    angles_v = np.array([-30.0, 0.0, 30.0])
    bh = np.cos(np.radians(angles_h)) ** 2
    bv = np.cos(np.radians(angles_v)) ** 2
    sh = np.array([[b * np.log2(ff / fx) for b in bh] for ff in f])
    sv = np.array([[b * np.log2(ff / fx) for b in bv] for ff in f])
    from hornlab_search.objective.scalar_meh import lr4_highpass_db
    target_db = np.full(f.size, 120.0)
    return {"freqs": f, "LW": np.zeros(f.size), "xo_hz": [fx],
            "polars": {"h": (angles_h, sh), "v": (angles_v, sv)},
            "spl_target_db": [[120.0, 120.0], [12000.0, 120.0]], "hp_hz": 120.0,
            "max_boost_db": 6.0,
            "spl_max_db": target_db + lr4_highpass_db(f, 120.0) + 3.0,
            "band_lo_hz": 120.0, "band_hi_hz": 12000.0}


# ------------------------------------------------------------------ composition

def test_j_is_the_weighted_normalised_term_sum():
    f = np.geomspace(200.0, 12000.0, 24)
    t = _target()
    ctx = _flat_ctx(f)
    ctx["LW"] = np.where(np.arange(f.size) < 12, 10.0, -10.0)     # lw_resid = 2.0 dB exactly
    j, terms = objective_meh(_metrics(f, t), None, True, t, None, None, ctx)

    assert terms["lw_resid"] == pytest.approx(2.0, rel=1e-9)
    assert terms["notch"] == pytest.approx(0.0, abs=1e-12)
    assert terms["xo_lob"] == pytest.approx(0.0, abs=1e-9)
    assert terms["headroom"] == pytest.approx(0.0, abs=1e-12)
    assert j == pytest.approx(0.5 * 2.0 / 1.0, rel=1e-9)
    assert terms["total"] == pytest.approx(j, rel=1e-12)
    assert j == pytest.approx(
        sum(MEH_DEFAULT_WEIGHTS[k] * terms[k] for k in MEH_WEIGHTED_KEYS), rel=1e-12)
    assert set(terms) == set(MEH_ALL_KEYS)


def test_tolerance_and_weight_change_the_contribution_as_defined():
    f = np.geomspace(200.0, 12000.0, 24)
    t = _target()
    ctx = _flat_ctx(f)
    ctx["LW"] = np.where(np.arange(f.size) < 12, 10.0, -10.0)
    m = _metrics(f, t)

    _, base = objective_meh(m, None, True, t, None, None, ctx)
    p2 = MehParams.from_block({"version": 5, "tolerances": {"lw_resid": 2.0}})
    j2, t2 = objective_meh(m, None, True, t, None, p2, ctx)
    assert t2["lw_resid"] == pytest.approx(base["lw_resid"] / 2.0, rel=1e-12)
    assert j2 == pytest.approx(0.5, rel=1e-9)

    j3, t3 = objective_meh(m, None, True, t, {"lw_resid": 1.0}, None, ctx)
    assert t3["lw_resid"] == pytest.approx(base["lw_resid"], rel=1e-12)
    assert j3 == pytest.approx(2.0, rel=1e-9)


def test_with_the_new_weights_off_v5_pattern_terms_are_v4():
    f = np.geomspace(200.0, 12000.0, 24)
    t = _target()
    m = _metrics(f, t)
    ctx = _flat_ctx(f)
    w = {**{k: MEH_DEFAULT_WEIGHTS[k] for k in V4_WEIGHTED_KEYS},
         **{k: 0.0 for k in MEH_EXTRA_KEYS}}
    v4p = V4Params(tolerances={k: MEH_DEFAULT_TOLERANCES[k] for k in V4_WEIGHTED_KEYS})
    j4, t4 = objective_v4(m, None, True, t, w, v4p)
    j5, t5 = objective_meh(m, None, True, t, w, None, ctx)
    assert j5 == pytest.approx(j4, rel=1e-12)
    for k in V4_WEIGHTED_KEYS:
        assert t5[k] == pytest.approx(t4[k], rel=1e-12)
    for k in MEH_EXTRA_KEYS:
        assert t5[k] == pytest.approx(0.0)


# ------------------------------------------------------------------ failure / finiteness

def test_failed_evaluation_returns_the_penalty_with_the_v5_key_set():
    j, terms = objective_meh(None, None, False, _target(), None, None, None)
    assert j == PENALTY_FAILED and math.isfinite(j)
    assert set(terms) == set(MEH_ALL_KEYS)
    assert terms["penalty"] == PENALTY_FAILED and terms["total"] == PENALTY_FAILED


def test_missing_context_scores_the_four_terms_at_the_fill_but_never_nan():
    f = np.geomspace(200.0, 12000.0, 24)
    t = _target()
    j, terms = objective_meh(_metrics(f, t), None, True, t, None, None, None)
    assert math.isfinite(j) and j > 0.0
    for k in MEH_EXTRA_KEYS:
        assert terms[k] == pytest.approx(NAN_TERM_FILL / MEH_DEFAULT_TOLERANCES[k], rel=1e-12)
    assert set(terms) == set(MEH_ALL_KEYS)


def test_bad_params_fail_closed_not_open():
    f = np.geomspace(200.0, 12000.0, 24)
    t = _target()
    j, terms = objective_meh(_metrics(f, t), None, True, t, None,
                             "not-params", _flat_ctx(f))  # type: ignore[arg-type]
    assert j == PENALTY_FAILED and set(terms) == set(MEH_ALL_KEYS)


# ------------------------------------------------------------------ config + dispatch

def _write_cfg(tmp_path, objective, weights):
    import yaml
    from pathlib import Path
    typ = Path(tmp_path) / "typ.yaml"
    typ.write_text(yaml.safe_dump({
        "name": "typ", "family": "FREEFORM", "brief_file": "brief.yaml",
        "generator": {"name": "typology", "profile_h": {"type": "hypex"},
                      "profile_v": {"type": "hypex"}, "n_anchors": 16, "max_wall_deg": 80.0,
                      "mouth": "ellipse"},
        "seed_params": {"L_mm": 190.0, "h_rm_mm": 120.0, "v_rm_mm": 120.0, "h_T": 0.7, "v_T": 0.7},
        "bounds": {"L_mm": {"lo": 140.0, "hi": 220.0}, "h_rm_mm": {"lo": 60.0, "hi": 150.0},
                   "v_rm_mm": {"lo": 60.0, "hi": 150.0}, "h_T": {"lo": 0.3, "hi": 1.0},
                   "v_T": {"lo": 0.3, "hi": 1.0}},
        "target": dict(_T), "weights": dict(weights),
        "mesh": {"epw": 8.0, "quadrants": "1", "dof_cap_screen": 5000, "dof_cap_verify": 7000,
                 "dof_cap_final": 8900, "dof_per_triangle": 0.51},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73, "balloon": True,
                  "balloon_points_screen": 512, "balloon_points_verify": 1024, "gmres_tol": 1.0e-05,
                  "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 100,
                   "popsize": None, "tolfun": 0.001},
    }, sort_keys=False), encoding="utf-8")
    brief = Path(tmp_path) / "brief.yaml"
    brief.write_text(yaml.safe_dump({
        "name": "v5", "description": "v5 test brief",
        "driver": {"exit_radius_mm": 17.9, "exit_angle_deg": 0.0},
        "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0, "max_depth_mm": 220.0},
        "symmetry": "hv", "target": {**_T, "f0_hz": 850.0}, "weights": weights,
        "objective": objective}, sort_keys=False), encoding="utf-8")
    return typ, brief


def test_config_loads_v5_with_the_c11_default_tolerances(tmp_path):
    typ, brief = _write_cfg(
        tmp_path,
        {"version": 5, "cov_narrow_ratio": 2.0, "cov_below_f0": "one_sided"},
        {"cov": 1.0, "lw_resid": 0.5, "notch": 1.0})
    cfg = load_config(typ, brief=brief)
    assert cfg.objective_version == 5
    assert cfg.objective_params is not None
    assert cfg.objective_params["version"] == 5
    assert cfg.objective_params["tolerances"]["notch"] == 3.0
    assert cfg.objective_params["cov_narrow_ratio"] == 2.0
    assert cfg.objective_params["cov_below_f0"] == "one_sided"


def test_config_refuses_v5_tolerances_that_break_penalty_ordering(tmp_path):
    typ, brief = _write_cfg(
        tmp_path,
        {"version": 5, "tolerances": {"notch": 1e-3}},
        {"notch": 1.0})
    with pytest.raises(ConfigError, match="refusal penalty"):
        load_config(typ, brief=brief)


def test_v1_to_v4_blocks_are_byte_identical():
    assert _validate_objective_block({"version": 1}, "t.yaml") == {"version": 1}
    assert _validate_objective_block({"version": 3}, "t.yaml") == {"version": 3}
    ones = {k: 1.0 for k in V4_WEIGHTED_KEYS}
    out = _validate_objective_block({"version": 4, "tolerances": ones}, "t.yaml")
    assert out["version"] == 4 and out["tolerances"] == ones
    with pytest.raises(ConfigError, match="unknown"):
        _validate_objective_block({"version": 3, "tolerances": ones}, "t.yaml")


def test_search_dispatch_registers_v5_and_scores_finitely(tmp_path):
    from hornlab_search.search.evaluate import _score, make_context

    typ, brief = _write_cfg(tmp_path, {"version": 5}, {"cov": 1.0})
    cfg = load_config(typ, brief=brief)
    ctx = make_context(cfg, lib_shas={})
    assert isinstance(ctx.objective_params, MehParams)
    f = np.geomspace(120.0, 12000.0, 12)
    m = _metrics(f, ctx.target)
    j, terms = _score(m, None, ctx)
    assert math.isfinite(j)
    assert set(terms) == set(MEH_ALL_KEYS)
    # M6 bridge: no meh_ctx on the context yet, so the system terms are the unflattering fill.
    assert terms["lw_resid"] == pytest.approx(NAN_TERM_FILL, rel=1e-12)


def test_versions_tuple_is_additive():
    assert SUPPORTED_OBJECTIVE_VERSIONS == (1, 2, 3, 4, 5, 6)
