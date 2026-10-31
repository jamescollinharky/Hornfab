"""Inner optimiser tests (M4 build step 6; contract C12).

Every response here is synthetic: no solver, no GPU, no mesher.  The recovery fixture models two
ideal band-limited sources whose acoustic responses are the LR4 high/low halves of the crossover,
one of them carrying a known 0.3 ms delay and a -1 polarity.  With the two sources flat inside the
overlap, only the right delay/polarity/crossover produces the flat LR4 all-pass sum, so the test
asks the optimiser to find it through the same default proxy the caller-less path uses.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pytest

from hornlab_search.meh import inner
from hornlab_search.meh.drivers import CDSource, ConeDriver
from hornlab_search.meh.network import cd_volume_velocity, entry_norton
from hornlab_search.meh.dsp import lr
from hornlab_search.meh.synthesis import NOMINAL_VOLTS, NetworkSolution
from hornlab_search.types import Response

FX = 900.0          # true CD/mid crossover
TAU_MS = 0.3        # true mid delay
FILL = 0.3          # true front-chamber filler
REAR_L = 2.0        # true rear chamber [L]
S_PORT_M2 = 2500e-6
L_NECK_M = 0.006


def _cd() -> CDSource:
    return CDSource(name="test CD", exit_mm=35.8, p_aes_w=400.0, min_xo_hz=700.0,
                    sens_db_1w=110.0, body_d_mm=124.0, body_len_mm=75.0, fs_cd_hz=500.0,
                    q_cd=1.0, di_ref_db=10.0)


def _mid(name: str = "test 6.5-inch mid") -> ConeDriver:
    return ConeDriver(name=name, re_ohm=5.5, le_h=0.2e-3, bl_tm=9.0, sd_m2=132e-4,
                      xmax_m=8.0e-3, p_aes_w=500.0, fs_hz=72.0, rms_kg_s=1.0, mms_kg=17e-3,
                      cms_m_per_n=0.28e-3, dish_mm=30.0, cutout_mm=145.0)


def _angles():
    h = np.array([-45.0, -30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0, 45.0])
    v = np.array([-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0])
    return h, v


def _synthetic(freqs, h_angles, v_angles, *, fx=FX, tau_ms=TAU_MS, fill=FILL, rear_l=REAR_L):
    """Two ideal band-limited sources: LR4 high/low halves at ``fx``, mid delayed and inverted."""
    cd, mid = _cd(), _mid()
    w = 2.0 * np.pi * freqs
    v_front = float(mid.sd_m2) * (3e-3 + 6e-3 + (1.0 - fill) * 30e-3 / 3.0)
    a_unit = cd_volume_velocity(freqs, cd, 1.0)
    b_unit = entry_norton(freqs, mid, 2, v_front, S_PORT_M2, L_NECK_M, rear_l * 1e-3, 1.0)[0]

    p_cd = lr(freqs, fx, 4, "hp")
    p_mid = lr(freqs, fx, 4, "lp") * (-1.0) * np.exp(1j * w * tau_ms * 1e-3)
    h0 = p_cd / a_unit
    h1 = p_mid / (b_unit * NOMINAL_VOLTS)

    n_f = freqs.size
    area_cd, area_mid = 1.2e-3, 2.4e-4
    cp = np.zeros((n_f, 2, 2, h_angles.size), dtype=np.complex128)
    for p, angles in enumerate((h_angles, v_angles)):
        # from_bem: H_net = conj(channel_pressure * (-j w) / area)  ->  cp = 1j conj(H) area / w
        cp[:, 0, p, :] = (1j * np.conj(h0) * area_cd / w)[:, None]
        cp[:, 1, p, :] = (1j * np.conj(h1) * area_mid / w)[:, None]

    resp = Response(
        freqs_hz=freqs, h_angles_deg=h_angles, v_angles_deg=v_angles,
        spl_h_db=np.zeros((n_f, h_angles.size)), spl_v_db=np.zeros((n_f, v_angles.size)),
        balloon_dirs=None, spl_balloon_db=None, z_throat=None,
        channel_tags=(2, 10), tag_areas_m2={2: area_cd, 10: area_mid},
        channel_pressure=cp, impedance_matrix=np.zeros((n_f, 2, 2), dtype=np.complex128),
    )
    return resp, cd, mid


def _brief(*, fx=FX, delay=(0.2, 0.6), gain=(-20.0, 20.0), mids=("mid",)):
    return {
        "groups": {
            "cd": {"tag": 2, "drivers": ["cd"]},
            "mid": {"tag": 10, "count": 2, "drivers": list(mids)},
        },
        "hp_hz": 120.0,
        "xo_hz": {"lo": fx * 0.8, "hi": fx * 1.25},
        "xo_orders": [4],
        "delay_ms": {"lo": delay[0], "hi": delay[1]},
        "v_front_fill": {"lo": FILL, "hi": FILL},
        "v_rear_l": {"lo": REAR_L, "hi": REAR_L},
        "amp_v_rms": 200.0,
        "port_air_mps_max": 40.0,
        "max_boost_db": 0.0,
        "spl_target": [[100.0, 60.0], [12000.0, 60.0]],
        "listening_window": {"h_deg": [0, 10, 20, 30], "v_deg": [10]},
        "mid_gain_db": {"lo": gain[0], "hi": gain[1]},
        "target": {"band_lo_hz": 500.0, "band_hi_hz": 1600.0},
        "weights": {},
    }


def _layout():
    return {
        "port_area_mm2": S_PORT_M2 * 1e6,
        "v_front_cm3": 132.0 * (3.0 + 6.0 + 30.0 / 3.0) * 0.1,
        "wall_t_mm": 6.0, "spacer_mm": 3.0, "dish_mm": 30.0,
        "ok": True, "reasons": [],
    }


def _recovery_fixture():
    freqs = np.geomspace(500.0, 1600.0, 40)
    h, v = _angles()
    resp, cd, mid = _synthetic(freqs, h, v)
    return resp, cd, mid


@pytest.fixture(scope="module")
def recovered():
    resp, cd, mid = _recovery_fixture()
    return inner.optimise_network(resp, _layout(), _brief(), {"cd": [cd], "mid": [mid]})


# ---------------------------------------------------------------------- recovery


def test_recovers_delay_polarity_and_crossover(recovered):
    assert recovered.mid_polarity == -1
    assert abs(recovered.mid_delay_ms - TAU_MS) <= 0.02, \
        f"recovered {recovered.mid_delay_ms:.4f} ms vs true {TAU_MS} ms"
    assert abs(recovered.xo_hz / FX - 1.0) <= 0.05, \
        f"recovered xo {recovered.xo_hz:.1f} Hz vs true {FX} Hz (5% tolerance)"
    assert recovered.xo_order == 4
    assert recovered.seed == 1234
    assert len(recovered.gains_db) == 2
    assert np.all(np.isfinite(recovered.gains_db))
    assert recovered.v_front_m3 > 0.0 and recovered.v_rear_m3 > 0.0


def test_record_curves_and_budget_accounting(recovered, ):
    freqs = np.geomspace(500.0, 1600.0, 40)
    assert len(recovered.eq_db) == freqs.size
    assert len(recovered.spl_max_db) == freqs.size
    assert np.all(np.isfinite(recovered.eq_db))
    assert np.all(np.isfinite(recovered.spl_max_db))
    # one combo, one order, two polarities, at most 160 evaluations each
    assert 0 < recovered.n_evals <= 2 * 160
    assert np.isfinite(recovered.inner_J)


# ---------------------------------------------------------------------- determinism / JSON


def test_deterministic_for_a_fixed_seed():
    resp, cd, mid = _recovery_fixture()
    first = inner.optimise_network(resp, _layout(), _brief(), {"cd": [cd], "mid": [mid]})
    second = inner.optimise_network(resp, _layout(), _brief(), {"cd": [cd], "mid": [mid]})
    assert first.to_dict() == second.to_dict()
    assert first.seed == second.seed == 1234


def test_network_solution_json_round_trip(recovered):
    record = recovered.to_dict()
    blob = json.dumps(record)                       # must not meet a numpy scalar
    back = json.loads(blob)
    assert set(back) == set(record)
    assert back["cd_stem"] == record["cd_stem"]
    assert back["mid_stem"] == record["mid_stem"]
    assert back["xo_order"] == record["xo_order"]
    assert back["mid_polarity"] == record["mid_polarity"]
    assert back["seed"] == record["seed"]
    assert back["n_evals"] == record["n_evals"]
    for key in ("xo_hz", "mid_delay_ms", "v_front_m3", "v_rear_m3", "inner_J"):
        assert back[key] == pytest.approx(record[key], rel=0.0, abs=0.0)
    assert [float(x) for x in back["gains_db"]] == list(record["gains_db"])
    assert [float(x) for x in back["eq_db"]] == list(record["eq_db"])
    assert [float(x) for x in back["spl_max_db"]] == list(record["spl_max_db"])


# ---------------------------------------------------------------------- caller score


def test_caller_score_is_used_and_receives_the_meh_context():
    resp, cd, mid = _recovery_fixture()
    brief = _brief()
    brief["weights"] = {"lw_resid": 0.5, "notch": 1.0, "xo_lob": 1.0, "headroom": 1.0}
    seen: dict = {}

    def score(ctx, weights):
        seen["ctx"] = ctx
        seen["weights"] = weights
        return 0.25, {"total": 0.25}

    sol = inner.optimise_network(resp, _layout(), brief, {"cd": [cd], "mid": [mid]}, score=score)

    assert sol.inner_J == pytest.approx(0.25, rel=0.0, abs=0.0)
    assert seen["weights"] == brief["weights"]
    for key in ("freqs", "LW", "polars", "xo_hz", "spl_max_db", "spl_target_db",
                "hp_hz", "max_boost_db", "band_lo_hz", "band_hi_hz"):
        assert key in seen["ctx"]
    assert seen["ctx"]["polars"]["h"][0].shape == np.asarray(seen["ctx"]["polars"]["h"][1]).shape[1:]


# ---------------------------------------------------------------------- enumeration


def test_enumerates_mid_candidates_and_keeps_their_stem():
    freqs = np.geomspace(600.0, 1400.0, 12)
    h, v = _angles()
    resp, cd, _mid_unused = _synthetic(freqs, h, v)
    mid_a, mid_b = _mid("mid A"), _mid("mid B")
    brief = _brief(mids=("mid_a", "mid_b"))
    sol = inner.optimise_network(resp, _layout(), brief,
                                 {"cd": [cd], "mid": [mid_a, mid_b]})
    assert sol.mid_stem in ("mid_a", "mid_b")
    assert sol.cd_stem == "cd"
    # two combos x one order x two polarities x <= 160 evaluations
    assert 0 < sol.n_evals <= 2 * 2 * 160


# ---------------------------------------------------------------------- hostile input


def test_hostile_inputs_raise_clear_errors():
    freqs = np.geomspace(600.0, 1400.0, 8)
    h, v = _angles()
    resp, cd, mid = _synthetic(freqs, h, v)

    with pytest.raises(ValueError, match="empty"):
        inner.optimise_network(resp, _layout(), _brief(), {"cd": [cd], "mid": []})
    with pytest.raises(ValueError, match="empty"):
        inner.optimise_network(resp, _layout(), _brief(), [])

    bad_xo = _brief()
    bad_xo["xo_hz"] = {"lo": 1200.0, "hi": 800.0}
    with pytest.raises(ValueError, match="lo < hi"):
        inner.optimise_network(resp, _layout(), bad_xo, {"cd": [cd], "mid": [mid]})

    bad_delay = _brief()
    bad_delay["delay_ms"] = {"lo": 2.0, "hi": -1.0}
    with pytest.raises(ValueError, match="lo <= hi"):
        inner.optimise_network(resp, _layout(), bad_delay, {"cd": [cd], "mid": [mid]})

    no_area = _layout()
    no_area.pop("port_area_mm2")
    with pytest.raises(ValueError, match="port"):
        inner.optimise_network(resp, no_area, _brief(), {"cd": [cd], "mid": [mid]})

    missing = _brief()
    missing.pop("groups")
    with pytest.raises(ValueError, match="missing required key"):
        inner.optimise_network(resp, _layout(), missing, {"cd": [cd], "mid": [mid]})


# ---------------------------------------------------------------------- CPU budget


def _budget_fixture(n_f=60, n_angles=37):
    freqs = np.geomspace(120.0, 12000.0, n_f)
    angles = np.linspace(-90.0, 90.0, n_angles)
    rng = np.random.default_rng(20261031)
    n_c = 2
    cp = (rng.standard_normal((n_f, n_c, 2, n_angles))
          + 1j * rng.standard_normal((n_f, n_c, 2, n_angles)))
    im = (rng.standard_normal((n_f, n_c, n_c))
          + 1j * rng.standard_normal((n_f, n_c, n_c)))
    resp = Response(
        freqs_hz=freqs, h_angles_deg=angles, v_angles_deg=angles,
        spl_h_db=np.zeros((n_f, n_angles)), spl_v_db=np.zeros((n_f, n_angles)),
        balloon_dirs=None, spl_balloon_db=None, z_throat=None,
        channel_tags=(2, 10), tag_areas_m2={2: 1.2e-3, 10: 2.4e-4},
        channel_pressure=cp, impedance_matrix=im,
    )
    return resp, freqs


def test_budget_60f_2planes_37angles_2channels_under_two_seconds():
    resp, freqs = _budget_fixture()
    brief = _brief()
    geom = inner._layout(_layout(), _mid(), 2)
    solution = inner._make_solution(
        resp, cd_stem="cd", mid_stem="mid", cd=_cd(), mid=_mid(), geom=geom, block=brief,
        xo_hz=FX, xo_order=4, delay_ms=TAU_MS, polarity=-1, gain_db=0.0,
        fill=FILL, rear_l=REAR_L)

    t0 = time.perf_counter()
    j, ctx = inner._evaluate(resp, solution, brief, brief, None, None, freqs)
    elapsed = time.perf_counter() - t0

    assert np.isfinite(j)
    assert ctx["LW"].shape == freqs.shape
    assert elapsed < 2.0, f"one inner candidate took {elapsed:.2f} s (budget 2 s)"
