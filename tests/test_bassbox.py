"""Offline tests for ``tools/bassbox.py`` and the seven M10 woofer files (work package M10).

The model and the design search are CPU-only (numpy + scipy): no GPU, no Julia, no solver, no mesher.
The tool is loaded by path because ``tools/`` is a scripts directory, not a package (same pattern as
``tests/test_tools_night_runner.py``).

The physical checks are the ones the task names: a textbook B4 alignment, energy balance, and the
port-velocity formula against a hand calculation. The driver checks are the C8 contract from
``docs/meh/00_MEH_CONTRACTS.md``: required keys, the ``derived`` list, and the recorded formulas.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

from conftest import REPO
from hornlab_search.constants import RHO_AIR
from hornlab_search.meh.drivers import ConeDriver, load_cone, mmd_from_mms

TOOL = REPO / "tools" / "bassbox.py"
DRIVERS = REPO / "examples" / "drivers"


def _load_tool():
    spec = importlib.util.spec_from_file_location("bassbox_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bb = _load_tool()

#: The seven files this task owns (C13).
NEW_STEMS = (
    "bc_15tbx100",
    "bc_18tbw100",
    "bc_18sw115",
    "faitalpro_15xl1400",
    "faitalpro_18xl1800",
    "eighteensound_18nlw9601",
    "beyma_15lx60v2",
)

# C8 "cone": required keys plus the "or" groups (same list as tests/test_meh_driver_files.py).
CONE_REQUIRED = (
    "name", "kind", "re_ohm", "le_mh", "bl_tm", "sd_cm2", "xmax_mm", "p_aes_w",
    "fs_hz", "cutout_mm", "depth_mm", "source",
)
CONE_ALTERNATIVES = (
    ("qms", "rms_kg_s"),
    ("mmd_g", "mms_g"),
    ("cms_mm_per_n", "vas_l"),
)
CONE_OPTIONAL = ("frame_od_mm", "motor_od_mm", "dish_mm", "sens_db_2v83", "notes")
STRING_KEYS = ("name", "kind", "source", "notes")

# M1's exact formula strings; a derived key must state its formula in `notes`.
DERIVED_FORMULAS = {
    "mmd_g": "Mmd = Mms - 2*(8/3)*rho*a^3",
    "cms_mm_per_n": "Cms = Vas/(rho*c^2*Sd^2)",
}


def _driver_dict(stem: str) -> dict:
    path = DRIVERS / f"{stem}.yaml"
    assert path.is_file(), f"missing driver file {path}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


# --------------------------------------------------------------------------- synthetic driver

def _synthetic_driver(qts=0.383, fs=35.0, qms=10.0, mms_g=100.0, sd_cm2=500.0, re_ohm=6.0):
    """A driver built from the textbook alignment inputs: Qts, fs, Qms, Mms, Sd, Re.

    ``Qes = 2 pi fs Mms Re / Bl^2`` is inverted for Bl, and ``Cms = 1/((2 pi fs)^2 Mms)``.
    """
    mms = mms_g * 1e-3
    sd = sd_cm2 * 1e-4
    qes = qts * qms / (qms - qts)
    bl = math.sqrt(2.0 * math.pi * fs * mms * re_ohm / qes)
    cms = 1.0 / ((2.0 * math.pi * fs) ** 2 * mms)
    vas_l = 1.2041 * 343.0 ** 2 * sd ** 2 * cms * 1e3
    return ConeDriver.from_dict({
        "name": "B4 reference",
        "kind": "cone",
        "re_ohm": re_ohm,
        "le_mh": 0.0,
        "bl_tm": bl,
        "sd_cm2": sd_cm2,
        "xmax_mm": 20.0,
        "p_aes_w": 500.0,
        "fs_hz": fs,
        "qms": qms,
        "mms_g": mms_g,
        "cms_mm_per_n": cms * 1e3,
        "vas_l": vas_l,
        "cutout_mm": 250.0,
        "depth_mm": 120.0,
        "source": "synthetic (test only)",
    })


def _passband_relative(spl, f, lo=5.0, hi=8.0, fs=35.0):
    ref = float(np.mean(spl[(f >= lo * fs) & (f <= hi * fs)]))
    return spl - ref


# --------------------------------------------------------------------------- B4 alignment

def test_textbook_b4_is_minus_3db_at_fs() -> None:
    """Lossless B4: fs = fb, Qts = 0.383, and the B4 box constant alpha = Vas/Vb = sqrt(2).

    The lossless vented-box pressure response is ``p ~ s^4 / (s^4 + a3 s^3 + a2 s^2 + a1 s + a0)``
    with ``a1 = a3 = 1/(Qts h)`` and ``a2 = 1 + (1+alpha)/h^2``. ``|H|^2 = q^8/(q^8+1)`` (the
    4th-order Butterworth magnitude) needs ``a2 = 2 + sqrt(2)`` at ``h = 1``, i.e. ``alpha =
    sqrt(2)`` for Qts = 1/(2 sqrt 2) = 0.354 (0.383 is the same value rounded). The literal
    ``alpha = 1`` in the task text is checked separately below: it is not a B4.
    """
    d = _synthetic_driver()
    qes = 2.0 * math.pi * d.fs_hz * d.mms_kg * d.re_ohm / d.bl_tm ** 2
    qts = 1.0 / (1.0 / d.qms + 1.0 / qes)
    assert qts == pytest.approx(0.383, abs=1e-3)

    vb_l = d.vas_l / math.sqrt(2.0)      # B4 box constant alpha = Vas/Vb = sqrt(2)
    s_port_cm2 = 200.0
    s_port_m2 = s_port_cm2 * 1e-4
    l_eff = bb.port_effective_length(vb_l * 1e-3, d.fs_hz, s_port_m2)
    box = bb.Box("vented", vb_l, d.fs_hz, s_port_cm2, l_eff * 1e3,
                 q_leak=1e9, q_port=1e9, n_end=0.0)   # lossless textbook box, exact tuning
    assert box.tuning_hz == pytest.approx(d.fs_hz, rel=1e-12)

    f = np.geomspace(5.0, 400.0, 800)
    spl = _passband_relative(bb.evaluate(f, d, box).spl_db, f)
    at_fs = float(np.interp(math.log(d.fs_hz), np.log(f), spl))
    at_2fs = float(np.interp(math.log(2 * d.fs_hz), np.log(f), spl))
    assert at_fs == pytest.approx(-3.0, abs=0.2), f"B4 is {at_fs:.3f} dB at fs, expected -3.0"
    assert at_2fs == pytest.approx(0.0, abs=0.2), f"B4 passband is {at_2fs:.3f} dB at 2 fs"


def test_b4_volume_ratio_is_sqrt2_not_one() -> None:
    """The task text's literal (fs = fb, Qts 0.383, alpha = 1) is NOT a B4 in a lossless box.

    With alpha = 1 the ``s^2`` coefficient is 3 instead of 2 + sqrt(2) = 3.414, and the response is
    0.0 dB at fs (f3 lands at 0.89 fs). The test above therefore uses the textbook B4 constant
    alpha = sqrt(2); this test records the arithmetic so the deviation from the task text is
    visible instead of hidden. If the task text is amended, delete this test.
    """
    d = _synthetic_driver()
    s_port_cm2 = 200.0
    s_port_m2 = s_port_cm2 * 1e-4
    l_eff = bb.port_effective_length(d.vas_l * 1e-3, d.fs_hz, s_port_m2)
    box = bb.Box("vented", d.vas_l, d.fs_hz, s_port_cm2, l_eff * 1e3,
                 q_leak=1e9, q_port=1e9, n_end=0.0)   # alpha = Vas/Vb = 1
    f = np.geomspace(5.0, 400.0, 800)
    spl = _passband_relative(bb.evaluate(f, d, box).spl_db, f)
    at_fs = float(np.interp(math.log(d.fs_hz), np.log(f), spl))
    assert at_fs == pytest.approx(0.0, abs=0.2)


# --------------------------------------------------------------------------- energy / port

@pytest.mark.parametrize("kind", ["sealed", "vented"])
def test_energy_balance(kind: str) -> None:
    """P_electrical = P_joule + P_mechanical + P_port + P_leak exactly (passive lumped circuit)."""
    d = _synthetic_driver()
    if kind == "vented":
        box = bb.Box("vented", 60.0, 32.0, 200.0, 250.0)
    else:
        box = bb.Box("sealed", 60.0)
    f = np.geomspace(20.0, 200.0, 60)
    state = bb.evaluate(f, d, box)
    assert bb.energy_balance(state) < 1e-9

    # the far-field monopole power and the radiated-power bookkeeping agree
    p = state.powers_w
    w = 2.0 * np.pi * f
    u_net = state.u_d_m3s + state.u_p_m3s
    rad_from_u = RHO_AIR * w ** 2 * np.abs(u_net) ** 2 / (4.0 * math.pi * 343.0)
    np.testing.assert_allclose(p["radiated"], rad_from_u, rtol=1e-12, atol=0.0)
    assert float(np.max(p["radiated"])) > 0.0
    assert float(np.max(p["radiated"])) < float(np.max(p["electrical"]))


def test_port_velocity_formula_against_hand_calculation() -> None:
    """peak particle velocity = sqrt(2) |U_rms| / S_port (C7 / C11)."""
    u_rms = 0.012          # m^3/s rms, a hand value
    s_port = 0.018         # m^2
    hand = math.sqrt(2.0) * u_rms / s_port
    assert bb.port_velocity_peak(u_rms, s_port) == pytest.approx(hand, rel=1e-12)
    assert bb.port_velocity_peak(u_rms, s_port) == pytest.approx(0.942809, rel=1e-6)

    # the same velocity through the box model: at 40 Hz the port flow reproduces the hand value
    d = _synthetic_driver()
    box = bb.Box("vented", 60.0, 32.0, 180.0, 250.0)   # 180 cm^2 = the 0.018 m^2 above
    state = bb.evaluate([40.0], d, box, volts=1.0)
    assert state.port_v_peak_mps[0] == pytest.approx(
        math.sqrt(2.0) * abs(state.u_p_m3s[0]) / s_port)


def test_port_tuning_is_the_helmholtz_formula() -> None:
    vb = 0.100          # m^3
    s_port = 0.020      # m^2
    l_eff = 0.250       # m
    hand = 343.0 / (2.0 * math.pi) * math.sqrt(s_port / (vb * l_eff))
    assert bb.port_tuning_hz(vb, s_port, l_eff) == pytest.approx(hand, rel=1e-12)
    assert bb.port_effective_length(vb, hand, s_port) == pytest.approx(l_eff, rel=1e-12)


def test_port_end_correction_is_two_mouths_for_a_free_standing_box() -> None:
    box = bb.Box("vented", 100.0, 30.0, 200.0, 100.0, n_end=2.0)
    r_eq = math.sqrt(200.0e-4 / math.pi)
    assert box.l_eff_m == pytest.approx(0.100 + 2.0 * 0.85 * r_eq, rel=1e-12)
    # a sealed box has no port branch
    assert bb.Box("sealed", 50.0).l_eff_m == 0.0


def test_port_tuning_reproduces_the_requested_fb() -> None:
    d = _synthetic_driver()
    for fb in (26.0, 30.0, 35.0):
        l_eff = bb.port_effective_length(60e-3, fb, 200e-4)
        box = bb.Box("vented", 60.0, fb, 200.0, l_eff * 1e3, n_end=0.0)
        assert box.tuning_hz == pytest.approx(fb, rel=1e-12)


# --------------------------------------------------------------------------- limits

def test_max_spl_sits_exactly_on_a_limit() -> None:
    """At e_lim the binding quantity equals its limit and none of the three is exceeded."""
    from hornlab_search.meh.drivers import load_cone
    d = load_cone("faitalpro_18xl1800")
    box = bb.Box("vented", 80.0, 32.0, 150.0, 260.0)
    f = np.geomspace(25.0, 150.0, 30)
    lim = bb.max_spl(f, d, box)
    for i, fi in enumerate(f):
        st = bb.evaluate([fi], d, box, volts=float(lim["e_lim_v"][i]))
        ratios = np.array([
            st.x_peak_mm[0] / d.xmax_mm,
            (float(lim["e_lim_v"][i]) ** 2 / d.re_ohm) / d.p_aes_w,
            st.port_v_peak_mps[0] / bb.PORT_AIR_MPS_MAX,
        ])
        assert np.all(ratios <= 1.0 + 1e-9)
        assert float(np.max(ratios)) == pytest.approx(1.0, abs=1e-9)
        assert lim["limiting"][i] in ("xmax", "p_aes", "port")
    assert float(np.max(lim["e_lim_v"])) > 0.0


def test_electrical_impedance_shows_the_vented_double_hump() -> None:
    d = _synthetic_driver()
    f = np.geomspace(15.0, 200.0, 2000)
    vbox = bb.Box("vented", 60.0, 32.0, 200.0, 250.0)
    vented = bb.evaluate(f, d, vbox).z_in_ohm
    sealed = bb.evaluate(f, d, bb.Box("sealed", 60.0)).z_in_ohm
    mag = np.abs(vented)
    # two local maxima around the tuning, separated by a minimum near fb
    imax = [i for i in range(1, len(mag) - 1) if mag[i] > mag[i - 1] and mag[i] > mag[i + 1]]
    assert len(imax) >= 2
    i_lo, i_hi = imax[0], imax[-1]
    i_min = i_lo + int(np.argmin(mag[i_lo:i_hi + 1]))
    assert f[i_lo] < f[i_min] < f[i_hi]
    assert math.log(f[i_min] / vbox.tuning_hz) == pytest.approx(0.0, abs=0.10)
    # the sealed box has one resonance peak, not two
    smag = np.abs(sealed)
    simax = [i for i in range(1, len(smag) - 1) if smag[i] > smag[i - 1] and smag[i] > smag[i + 1]]
    assert len(simax) == 1


def test_spl_at_2v83_matches_the_datasheet_sensitivity() -> None:
    """Midband SPL at 2.83 V vs the maker's published sensitivity (within 3 dB)."""
    f = np.array([250.0, 300.0])
    for stem in NEW_STEMS:
        d = load_cone(stem)
        spl = bb.evaluate(f, d, bb.Box("sealed", 1e4)).spl_at_2v83_db
        assert d.sens_db_2v83 is not None
        assert float(np.mean(spl)) == pytest.approx(d.sens_db_2v83, abs=3.0), stem


# --------------------------------------------------------------------------- driver files

@pytest.mark.parametrize("stem", NEW_STEMS)
def test_new_driver_file_satisfies_c8(stem: str) -> None:
    data = _driver_dict(stem)
    assert data.get("kind") == "cone"
    missing = [key for key in CONE_REQUIRED if data.get(key) is None]
    assert not missing, f"{stem}: missing C8 required key(s) {missing}"
    for group in CONE_ALTERNATIVES:
        assert any(data.get(key) is not None for key in group), f"{stem}: needs one of {group}"
    for key in STRING_KEYS:
        assert isinstance(data.get(key), str) and data[key].strip(), f"{stem}: {key} must be text"
    assert data["source"].startswith("http")

    allowed = set(CONE_REQUIRED) | set(CONE_OPTIONAL) | {"kind", "derived"}
    for group in CONE_ALTERNATIVES:
        allowed.update(group)
    assert not (set(data) - allowed), f"{stem}: keys outside C8: {sorted(set(data) - allowed)}"

    for key, value in data.items():
        if key in STRING_KEYS or key == "derived":
            continue
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        assert math.isfinite(float(value)) and float(value) > 0.0


@pytest.mark.parametrize("stem", NEW_STEMS)
def test_derived_values_carry_their_formulas(stem: str) -> None:
    data = _driver_dict(stem)
    derived = data.get("derived", [])
    assert isinstance(derived, list)
    for key in derived:
        assert key in data, f"{stem}: derived key {key} has no value"
        assert key in DERIVED_FORMULAS
        assert DERIVED_FORMULAS[key] in data["notes"], (
            f"{stem}: notes must state {DERIVED_FORMULAS[key]!r} for {key}")


@pytest.mark.parametrize("stem", NEW_STEMS)
def test_derived_mmd_matches_the_repo_helper(stem: str) -> None:
    data = _driver_dict(stem)
    mms = float(data["mms_g"])
    sd = float(data["sd_cm2"])
    implied = mmd_from_mms(mms, sd)
    if "mmd_g" in data.get("derived", []):
        assert float(data["mmd_g"]) == pytest.approx(implied, abs=0.02)
    else:
        # FaitalPRO publish Mmd directly; the sheet's own rounding is <= 1.1 g off the air-load
        # relation (the model uses the published value, as instructed).
        assert float(data["mmd_g"]) == pytest.approx(implied, abs=1.2)


@pytest.mark.parametrize("stem", NEW_STEMS)
def test_derived_cms_matches_the_vas_formula(stem: str) -> None:
    data = _driver_dict(stem)
    if "cms_mm_per_n" not in data.get("derived", []):
        return
    sd = float(data["sd_cm2"]) * 1e-4
    hand = float(data["vas_l"]) * 1e-3 / (1.2041 * 343.0 ** 2 * sd ** 2) * 1e3
    assert float(data["cms_mm_per_n"]) == pytest.approx(hand, rel=1e-5)


@pytest.mark.parametrize("stem", NEW_STEMS)
def test_model_fs_is_within_the_datasheet_spread(stem: str) -> None:
    """The published Vas/Mms pair reproduces Fs; the two B&C/18 Sound files are 4-8 % off and say so."""
    d = load_cone(stem)
    fs_model = 1.0 / (2.0 * math.pi * math.sqrt(d.mms_kg * d.cms_m_per_n))
    assert fs_model == pytest.approx(d.fs_hz, rel=0.08), stem


@pytest.mark.parametrize("stem", NEW_STEMS)
def test_xmax_basis_is_recorded(stem: str) -> None:
    notes = _driver_dict(stem)["notes"].lower()
    assert ("one-way" in notes) or ("peak" in notes), f"{stem}: Xmax basis is not recorded"


def test_beyma_xmax_conflict_is_recorded() -> None:
    notes = _driver_dict("beyma_15lx60v2")["notes"]
    assert "8 mm" in notes and "9 mm" in notes
    assert "conflict" in notes.lower()
    assert float(_driver_dict("beyma_15lx60v2")["xmax_mm"]) == 8.0


def test_faitalpro_mmd_is_the_published_value() -> None:
    assert float(_driver_dict("faitalpro_15xl1400")["mmd_g"]) == 162.4
    assert float(_driver_dict("faitalpro_18xl1800")["mmd_g"]) == 228.8


# --------------------------------------------------------------------------- designs

@pytest.fixture(scope="module")
def rows():
    """Run the real design search once for all seven drivers."""
    return bb.recommend()


def test_recommendation_meets_the_owner_targets(rows) -> None:
    assert rows
    best = rows[0]
    assert best["meets"], "the recommended design does not meet the targets"
    d = best["design"]
    assert d.margin_40_db >= 0.0
    assert d.margin_63_120_db >= 0.0
    assert d.ripple_max_db <= bb.FLAT_TOL_DB
    assert d.ripple_rms_db <= bb.FLAT_RMS_DB
    assert d.peq_boost_db <= bb.MAX_PEQ_BOOST_DB
    assert d.f3_hz is not None and d.f3_hz <= bb.FLAT_BAND_HZ[0] + 1.0
    if d.kind == "vented":
        assert d.port_length_mm is not None and d.port_length_mm > 0.0
        assert d.fb_hz is not None


@pytest.mark.parametrize("stem", NEW_STEMS)
def test_every_shortlisted_driver_has_a_meeting_design(rows, stem: str) -> None:
    mine = [r for r in rows if r["stem"] == stem]
    assert mine, f"{stem}: no design produced"
    assert any(r["meets"] for r in mine), f"{stem}: no design meets the targets"
    for r in mine:
        d = r["design"]
        assert d.vb_l > 0.0
        assert len(d.cabinet_mm) == 3
        assert d.gross_l >= d.vb_l
        if r["meets"]:
            assert d.margin_40_db >= 0.0 and d.margin_63_120_db >= 0.0


def test_designs_are_json_serialisable(rows) -> None:
    import json
    text = json.dumps([r["design"].as_dict() for r in rows])
    assert '"kind"' in text and '"cabinet_mm"' in text


def test_design_is_deterministic() -> None:
    """The grids and the PEQ fit are deterministic: two runs on one driver agree exactly."""
    d = load_cone("faitalpro_15xl1400")
    a = bb.design_sealed(d, "faitalpro_15xl1400")
    b = bb.design_sealed(d, "faitalpro_15xl1400")
    assert a is not None and b is not None
    assert a.vb_l == b.vb_l
    assert a.peq == b.peq
