"""DSP, SPL limits and system synthesis for the MEH effort (contracts C11/C12).

No solver and no GPU: every response here is synthetic. The reference Linkwitz-Riley is imported
**by file path** from the research ``calc/`` folder, never from package code.
"""
from __future__ import annotations

import importlib.util
import math
import sys
import time
import types
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.constants import REF_P
from hornlab_search.meh import dsp, limits, synthesis
from hornlab_search.meh.drivers import CDSource, ConeDriver
from hornlab_search.meh.network import cd_volume_velocity, couple, entry_norton, from_bem
from hornlab_search.metrics.compute import compute_metrics
from hornlab_search.targets.spec import Target

# ------------------------------------------------------------------ reference import by path

REPO = Path(__file__).resolve().parents[1]
CALC = REPO / "docs" / "research" / "typologies" / "mini_meh_2026-10-29" / "calc"


def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sketch = _load_by_path("meh_1d_sketch_ref", CALC / "meh_1d_sketch.py")


# ------------------------------------------------------------------ fixtures

def _cd() -> CDSource:
    return CDSource(
        name="test CD", exit_mm=35.8, p_aes_w=80.0, min_xo_hz=700.0, sens_db_1w=110.0,
        body_d_mm=124.0, body_len_mm=75.0, fs_cd_hz=500.0, q_cd=1.0, di_ref_db=10.0,
    )


def _mid() -> ConeDriver:
    return ConeDriver(
        name="test 6.5-inch mid", re_ohm=5.5, le_h=0.2e-3, bl_tm=9.0, sd_m2=135e-4,
        xmax_m=4.0e-3, p_aes_w=100.0, fs_hz=80.0, rms_kg_s=1.0, mms_kg=12.0e-3,
        cms_m_per_n=0.3e-3,
    )


def _solution(**kw) -> synthesis.NetworkSolution:
    base = dict(
        cd_stem="", mid_stem="", xo_hz=800.0, xo_order=4, mid_delay_ms=0.2,
        mid_polarity=-1, gains_db=(1.5, -2.0), v_front_m3=30e-6, v_rear_m3=1.0e-3,
        hp_hz=120.0, mid_count=4, s_port_m2=12e-4, l_neck_m=0.012,
        cd=_cd(), mid=_mid(),
    )
    base.update(kw)
    return synthesis.NetworkSolution(**base)


def _fake_bem(freqs, angles, tags=(2, 10), areas=None, cp=None, im=None, sphere=None):
    freqs = np.asarray(freqs, dtype=float)
    angles = np.asarray(angles, dtype=float)
    n_f, n_c = freqs.size, len(tags)
    if areas is None:
        areas = {2: 1.2e-3, 10: 2.4e-4}
    if cp is None:
        rng = np.random.default_rng(7)
        cp = (rng.standard_normal((n_f, n_c, 2, angles.size))
              + 1j * rng.standard_normal((n_f, n_c, 2, angles.size)))
    if im is None:
        rng = np.random.default_rng(8)
        im = (rng.standard_normal((n_f, n_c, n_c))
              + 1j * rng.standard_normal((n_f, n_c, n_c)))
    return types.SimpleNamespace(
        freqs_hz=freqs,
        h_angles_deg=angles,
        v_angles_deg=angles,
        channel_tags=tuple(tags),
        tag_areas_m2=dict(areas),
        channel_pressure=np.asarray(cp, dtype=np.complex128),
        channel_sphere_pressure=None if sphere is None else np.asarray(sphere, dtype=np.complex128),
        impedance_matrix=np.asarray(im, dtype=np.complex128),
        balloon_dirs=None,
        n_dof=None,
        meta={},
    )


# ------------------------------------------------------------------ LR4 / delay / EQ

def test_lr4_low_plus_high_is_unit_magnitude_allpass():
    f = np.geomspace(20.0, 20_000.0, 600)
    lp = dsp.lr(f, 1000.0, 4, "lp")
    hp = dsp.lr(f, 1000.0, 4, "hp")
    assert lp.dtype == np.complex128 and hp.dtype == np.complex128
    # LR4 = (2nd-order Butterworth)^2; lp + hp is the all-pass (1+s^2)^2/(s^2+sqrt2 s+1)^2.
    np.testing.assert_allclose(np.abs(lp + hp), 1.0, rtol=0.0, atol=1e-9)


def test_lr4_matches_reference_sketch():
    f = np.geomspace(100.0, 10_000.0, 60)
    np.testing.assert_allclose(dsp.lr(f, 900.0, 4, "lp"), sketch.lr4(f, 900.0, "lp"),
                               rtol=1e-12, atol=0.0)
    np.testing.assert_allclose(dsp.lr(f, 900.0, 4, "hp"), sketch.lr4(f, 900.0, "hp"),
                               rtol=1e-12, atol=0.0)


def test_delay_has_the_right_phase_slope():
    f = np.linspace(50.0, 2000.0, 40)
    ms = 0.25
    tau = ms * 1e-3
    h = dsp.delay(f, ms)
    np.testing.assert_allclose(h, np.exp(-1j * 2.0 * np.pi * f * tau), rtol=0.0, atol=1e-15)
    phase = np.unwrap(np.angle(h))
    slope = np.gradient(phase, f)
    np.testing.assert_allclose(slope, np.full_like(f, -2.0 * np.pi * tau), rtol=0.0, atol=1e-12)


def test_peaking_gain_and_polarity():
    np.testing.assert_allclose(dsp.peaking(1000.0, 1000.0, 6.0, 1.0), 10.0 ** (6.0 / 20.0),
                               rtol=1e-12)
    np.testing.assert_allclose(np.abs(dsp.peaking(np.array([1.0, 1.0e6]), 1000.0, 6.0, 1.0)),
                               1.0, rtol=1e-4)
    np.testing.assert_array_equal(dsp.polarity(-1), np.array(-1.0))
    with pytest.raises(ValueError, match="polarity"):
        dsp.polarity(0.5)


def test_smooth_oct_is_a_power_average_in_the_window():
    f = np.geomspace(100.0, 10_000.0, 200)
    db = -3.0 + 9.0 * np.sin(np.log2(f / 1000.0))
    smoothed = dsp.smooth_oct(f, db, 1.0 / 3.0)
    i = 97
    half = 2.0 ** (1.0 / 6.0)
    sel = (f >= f[i] / half) & (f <= f[i] * half)
    expected = 10.0 * np.log10(np.mean(10.0 ** (db[sel] / 10.0)))
    assert smoothed[i] == pytest.approx(expected, rel=1e-15)
    np.testing.assert_allclose(dsp.smooth_oct(f, np.full_like(f, -7.0), 1.0 / 3.0),
                               np.full_like(f, -7.0), rtol=0.0, atol=1e-12)


def test_system_eq_never_boosts_more_than_the_limit():
    f = np.geomspace(120.0, 12_000.0, 240)
    log2 = np.log2(f / 1000.0)
    lw = -3.0 + 3.0 * np.sin(log2) - 30.0 * np.exp(-0.5 * (log2 / 0.35) ** 2)
    eq = dsp.system_eq(lw, f, 6.0)
    assert eq.dtype == np.float64
    assert np.all(eq <= 6.0 + 1e-12)
    assert np.max(eq) == pytest.approx(6.0, abs=1e-9)     # the deep dip hits the boost ceiling
    # A perfect boost beyond the limit is clipped, but a cut is unlimited: a +30 dB peak is cut hard.
    peak = -3.0 + 30.0 * np.exp(-0.5 * (log2 / 0.35) ** 2)
    eq_peak = dsp.system_eq(peak, f, 6.0)
    assert np.min(eq_peak) < -10.0
    assert np.all(eq_peak <= 6.0 + 1e-12)


# ------------------------------------------------------------------ spl_max: all five limits

def _nominal_state(cd_spl=100.0, exc=2.0, power=50.0, port_v=5.0, drive_v=2.83) -> dict:
    return {
        "freqs_hz": np.array([1000.0]),
        "spl_ref_db": np.array([100.0]),
        "spl_channel_db": np.array([[cd_spl, 100.0]]),
        "excursion_peak_mm": np.array([[np.inf, exc]]),
        "electrical_power_w": np.array([[np.inf, power]]),
        "port_velocity_mps": np.array([[np.inf, port_v]]),
        "drive_v_rms": np.array([[np.inf, drive_v]]),
    }


CD_LIMIT_DB = 110.0 + 10.0 * math.log10(80.0)          # sens_db_1w + 10 log10(p_aes_w), DI=di_ref


@pytest.mark.parametrize(
    "label, kw, expected_scale",
    [
        ("excursion", dict(exc=2.0, power=1.0, port_v=1.0, drive_v=2.83, cd_spl=100.0), 2.0),
        ("power", dict(exc=0.01, power=50.0, port_v=1.0, drive_v=2.83, cd_spl=100.0),
         math.sqrt(100.0 / 50.0)),
        ("port", dict(exc=0.01, power=1.0, port_v=10.0, drive_v=2.83, cd_spl=100.0), 17.0 / 10.0),
        ("amp", dict(exc=0.01, power=1.0, port_v=1.0, drive_v=40.0, cd_spl=100.0), 1.0),
        ("cd_power", dict(exc=0.01, power=1.0, port_v=1.0, drive_v=2.83, cd_spl=125.0),
         10.0 ** ((CD_LIMIT_DB - 125.0) / 20.0)),
    ],
)
def test_spl_max_hits_each_limit_and_reports_it(label, kw, expected_scale):
    solution = _solution(nominal_state=_nominal_state(**kw))
    brief = {"amp_v_rms": 40.0, "port_air_mps_max": 17.0}
    db, bound = limits.spl_max(np.array([1000.0]), solution, brief, return_limits=True)
    assert db.shape == (1,)
    assert bound[0] == label
    assert db[0] == pytest.approx(100.0 + 20.0 * math.log10(expected_scale), abs=1e-9)
    assert limits.binding_limits(np.array([1000.0]), solution, brief)[0] == label


def test_spl_max_from_a_solved_response_is_finite():
    freqs = np.geomspace(200.0, 5000.0, 12)
    angles = np.array([-30.0, 0.0, 30.0])
    resp = _fake_bem(freqs, angles)
    solution = _solution(response=resp)
    db = limits.spl_max(freqs, solution, {"amp_v_rms": 40.0, "port_air_mps_max": 17.0})
    assert db.shape == freqs.shape
    assert np.all(np.isfinite(db))
    assert np.all(db < 200.0)


# ------------------------------------------------------------------ synthesis sum

def test_system_response_two_channels_equals_the_hand_sum():
    freqs = np.array([400.0, 800.0, 1600.0])
    angles = np.array([-30.0, 0.0, 30.0])
    rng = np.random.default_rng(11)
    cp = (rng.standard_normal((freqs.size, 2, 2, angles.size))
          + 1j * rng.standard_normal((freqs.size, 2, 2, angles.size)))
    im = (rng.standard_normal((freqs.size, 2, 2))
          + 1j * rng.standard_normal((freqs.size, 2, 2)))
    sphere = (rng.standard_normal((freqs.size, 2, 5))
              + 1j * rng.standard_normal((freqs.size, 2, 5)))
    resp = _fake_bem(freqs, angles, cp=cp, im=im, sphere=sphere)
    resp.balloon_dirs = rng.standard_normal((5, 3))
    resp.balloon_dirs /= np.linalg.norm(resp.balloon_dirs, axis=1, keepdims=True)
    solution = _solution()

    out = synthesis.system_response(resp, solution)

    # Independent hand computation of every channel's complex drive and the sum.
    h_net, z_net, f_out = from_bem(resp)
    hp = dsp.lr(freqs, 120.0, 4, "hp")
    u_cd = cd_volume_velocity(
        freqs, solution.cd,
        10.0 ** (solution.gains_db[0] / 20.0) * dsp.lr(freqs, 800.0, 4, "hp") * hp)
    e = (synthesis.NOMINAL_VOLTS * 10.0 ** (solution.gains_db[1] / 20.0)
         * dsp.lr(freqs, 800.0, 4, "lp") * dsp.polarity(-1) * dsp.delay(freqs, 0.2) * hp)
    u_sc, y = entry_norton(freqs, solution.mid, 4, 30e-6, 12e-4, 0.012, 1e-3, e)
    u = couple(z_net, u_sc[:, None], y[:, None], u_cd)

    drive = synthesis.channel_drives(resp, solution)
    np.testing.assert_allclose(drive["U"], u, rtol=1e-14, atol=0.0)
    np.testing.assert_allclose(drive["U"][:, 0], u_cd, rtol=1e-14, atol=0.0)

    p_net = h_net[:, 0] * u[:, 0, None, None] + h_net[:, 1] * u[:, 1, None, None]
    p_bem = np.conj(p_net)
    np.testing.assert_allclose(out.p_h, p_bem[:, 0, :], rtol=1e-13, atol=0.0)
    np.testing.assert_allclose(out.p_v, p_bem[:, 1, :], rtol=1e-13, atol=0.0)
    np.testing.assert_allclose(
        out.spl_h_db, 20.0 * np.log10(np.abs(p_bem[:, 0, :]) / REF_P), rtol=1e-13, atol=0.0)

    # Sphere: the same sum, same conversion.
    areas = np.array([1.2e-3, 2.4e-4])
    h_s = np.conj(sphere * (-1j * 2.0 * np.pi * freqs)[:, None, None] / areas[None, :, None])
    p_s = np.conj(np.einsum("fcn,fc->fn", h_s, u))
    np.testing.assert_allclose(out.p_balloon, p_s, rtol=1e-13, atol=0.0)
    assert out.balloon_dirs is not None

    # The synthesised system has no single throat impedance: the contract asks for an all-nan array.
    assert out.z_throat is not None and np.all(np.isnan(out.z_throat))
    np.testing.assert_array_equal(out.freqs_hz, f_out)


# ------------------------------------------------------------------ synthesis + metrics

def _metrics_fixture():
    freqs = np.geomspace(150.0, 10_000.0, 30)
    angles = np.array([-90.0, -60.0, -45.0, -30.0, -15.0, 0.0,
                       15.0, 30.0, 45.0, 60.0, 90.0])
    n_f = freqs.size
    cp = np.empty((n_f, 2, 2, angles.size), dtype=np.complex128)
    for c in range(2):
        for p in range(2):
            cp[:, c, p, :] = (1.0 + 0.2 * c + 0.1 * p) * np.exp(
                1j * (0.1 * np.arange(n_f)[:, None] + 0.05 * angles[None, :]))
    rng = np.random.default_rng(21)
    im = (rng.standard_normal((n_f, 2, 2)) + 1j * rng.standard_normal((n_f, 2, 2)))
    return _fake_bem(freqs, angles, cp=cp, im=im)


def test_synthesis_runs_through_compute_metrics_finite_and_nan_impedance():
    resp = _metrics_fixture()
    solution = _solution(response=resp)
    out = synthesis.system_response(resp, solution)

    assert np.all(np.isfinite(out.spl_h_db))
    assert np.all(np.isfinite(out.spl_v_db))
    assert np.all(np.isfinite(out.p_h))
    assert out.z_throat is not None and np.all(np.isnan(out.z_throat))

    target = Target(coverage_h_deg=90.0, coverage_v_deg=60.0,
                    band_lo_hz=120.0, band_hi_hz=12_000.0, di_target_db=None)
    m = compute_metrics(out, target)

    assert m.scalars["n_freqs"] == resp.freqs_hz.size
    assert m.scalars["di_source"] == "cuts_estimate"
    assert np.all(np.isfinite(m.bw_h_deg))
    assert np.all(np.isfinite(m.bw_v_deg))
    assert np.all(np.isfinite(m.di_db))
    assert np.all(np.isfinite(m.on_axis_db))
    assert np.all(np.isnan(m.z_throat_real))          # carried through as nan, never -inf


# ------------------------------------------------------------------ CPU budget

def test_budget_60f_2planes_37angles_2channels_under_two_seconds():
    freqs = np.geomspace(120.0, 12_000.0, 60)
    angles = np.linspace(-90.0, 90.0, 37)
    resp = _metrics_fixture_60(freqs, angles)
    solution = _solution(response=resp)
    target = Target(coverage_h_deg=90.0, coverage_v_deg=60.0,
                    band_lo_hz=120.0, band_hi_hz=12_000.0, di_target_db=None)
    brief = {"amp_v_rms": 40.0, "port_air_mps_max": 17.0}

    t0 = time.perf_counter()
    out = synthesis.system_response(resp, solution)
    compute_metrics(out, target)
    limits.spl_max(freqs, solution, brief)
    elapsed = time.perf_counter() - t0

    assert elapsed < 2.0, f"MEH synthesis+metrics+spl_max took {elapsed:.2f} s"


def _metrics_fixture_60(freqs, angles):
    n_f = freqs.size
    rng = np.random.default_rng(31)
    cp = (rng.standard_normal((n_f, 2, 2, angles.size))
          + 1j * rng.standard_normal((n_f, 2, 2, angles.size)))
    im = (rng.standard_normal((n_f, 2, 2)) + 1j * rng.standard_normal((n_f, 2, 2)))
    return _fake_bem(freqs, angles, cp=cp, im=im)
