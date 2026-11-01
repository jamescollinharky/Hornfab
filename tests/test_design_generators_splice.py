"""WP9 G2 meridian splice (Report 4 WP9 step 1; dossier section 2.1). Offline.

Ship bar
--------
P1 C1 continuity at the joint: the wall-angle gap across the joint is < 0.5 deg, for the
   osse|tractrix matched-angle case and for the Hermite-bridge fallback.
P2 both parents are built from the same r0 (a mismatch is refused, never rescaled).
P3 zs_frac -> z_s is monotone; the [0.2, 0.8] bounds are not widened.
P4 an unmatched joint (> the direct-splice bar) takes the 10 %-of-L Hermite bridge and
   still passes P1. (2026-10-25 R9-audit correction: the direct-splice bar moved from the
   Report-4 wording value 2 deg down to the P1 bar itself, 0.5 deg - the 2 deg direct band
   was shipping C0 kinks up to 1.876 deg on the shipped seed while everything labeled C1.)
Plus the existing generator test style: Hermite reconstruction through 16 anchors is
within 0.2 mm of the analytic pieces away from the joint, and the registry/provenance
wiring carries the nested first/second spec.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config
from hornlab_search.design import families
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import profiles as P
from hornlab_search.design.generators import registry
from hornlab_search.design.space import DesignSpace

R0 = 12.7            # mm, 1-inch driver
A0 = 5.0             # deg, driver exit angle (axi_90x90_1in brief)
L_OSSE = 110.0       # mm, parent-1 depth
MAX_WALL = 80.0

TYP = EXAMPLES / "typologies"
_JOINT_TOL_DEG = 0.5
_FIDELITY_TOL_MM = 0.2
_AWAY_MM = 5.0


def _osse(L: float = L_OSSE, a_deg: float = 25.0, s: float = 0.4) -> P.Meridian:
    return registry.build_meridian(
        {"type": "osse"}, {"L_mm": L, "h_first_a_deg": a_deg, "h_first_s": s},
        "h_first", r0=R0, a0=A0, L=L, max_wall=MAX_WALL, phi=0.0)


def _tractrix(fc_hz: float = 750.0) -> P.Meridian:
    return registry.build_meridian(
        {"type": "tractrix"}, {"h_second_fc_hz": fc_hz},
        "h_second", r0=R0, a0=A0, L=L_OSSE, max_wall=MAX_WALL, phi=0.0)


def _spliced(zs_frac: float) -> P.Meridian:
    return P.splice(_osse(), _tractrix(), zs_frac)


def _joint_gap_deg(m: P.Meridian) -> float:
    """Largest wall-angle step between the two output points straddling z_s."""
    z_s = m.info["z_s_mm"]
    i = int(np.searchsorted(m.z_mm, z_s, side="left"))
    if i >= len(m.z_mm) - 1:
        return 0.0
    return float(abs(m.theta_deg[i + 1] - m.theta_deg[i]))


def _tangent_deg(m: P.Meridian, z0: float, at: str) -> float:
    """Local quadratic tangent estimate at z0 (``at`` = 'start' or 'end').

    The bridge is a cubic Hermite: its start/end slopes are the parent angles.  A
    quadratic through the joint and its neighbours recovers that tangent to well under
    the 0.5 deg bar without duplicating the spline.
    """
    z, r = m.z_mm, m.r_mm
    if at == "start":
        i = int(np.searchsorted(z, z0, side="right"))
        idx = np.arange(i - 1, i + 3)
    else:
        j = int(np.argmin(np.abs(z - z0)))
        idx = np.arange(j - 2, j + 2)
    coef = np.polyfit(z[idx], r[idx], 2)
    return float(np.degrees(np.arctan(np.polyval(np.polyder(coef), z0))))


# ---------------------------------------------------------------------------
# P2: same r0
# ---------------------------------------------------------------------------

@requires_mesher
def test_parents_share_the_driver_exit_radius():
    m = _spliced(0.5)
    assert m.r_mm[0] == pytest.approx(R0)
    assert m.z_mm[0] == pytest.approx(0.0, abs=1e-12)
    assert np.all(np.abs(m.theta_deg) < 90.0)


def test_different_parent_r0_is_refused():
    first = registry.build_meridian(
        {"type": "conical"}, {"L_mm": 100.0, "h_rm_mm": 60.0},
        "h", r0=12.7, a0=A0, L=100.0, max_wall=MAX_WALL, phi=0.0)
    second = registry.build_meridian(
        {"type": "conical"}, {"L_mm": 100.0, "h_rm_mm": 60.0},
        "h", r0=12.8, a0=A0, L=100.0, max_wall=MAX_WALL, phi=0.0)
    with pytest.raises(ValueError, match="same r0"):
        P.splice(first, second, 0.5)


# ---------------------------------------------------------------------------
# P3: bounds and monotone zs_frac mapping
# ---------------------------------------------------------------------------

@requires_mesher
@pytest.mark.parametrize("bad", [0.19, 0.81, -0.5, 1.5])
def test_zs_frac_bounds_are_not_widened(bad):
    with pytest.raises(ValueError, match=r"zs_frac must be in \[0\.2, 0\.8\]"):
        P.splice(_osse(), _tractrix(), bad)


@requires_mesher
def test_zs_frac_maps_monotonically_to_zs():
    zs = [_spliced(f).info["z_s_mm"] for f in (0.2, 0.35, 0.5, 0.65, 0.8)]
    assert all(b > a for a, b in zip(zs, zs[1:]))
    assert zs[0] == pytest.approx(0.2 * L_OSSE)
    assert zs[-1] == pytest.approx(0.8 * L_OSSE)


# ---------------------------------------------------------------------------
# P1: matched-angle case
# ---------------------------------------------------------------------------

@requires_mesher
def test_matched_or_bridged_case_is_c1():
    """2026-10-25: with the corrected 0.5 deg bar the old zs=0.5 'matched' fixture (whose
    measured parent angle gap was 0.602 deg) now bridges - so this test asserts the SHIP
    BAR (P1) branch-agnostically, and the genuinely-matched direct path gets its own test."""
    m = _spliced(0.5)
    assert m.info["joint"] in ("matched", "hermite_bridge")
    assert _joint_gap_deg(m) < _JOINT_TOL_DEG
    assert np.all(np.diff(m.z_mm) > 0)
    assert np.all(np.diff(m.r_mm) > 0)


@requires_mesher
def test_angle_matched_cone_cone_splice_takes_the_direct_path():
    """2026-10-25: a genuinely angle-matched joint (two cones with the same wall angle,
    delta == 0) still takes the direct splice under the corrected bar."""
    a = registry.build_meridian(
        {"type": "conical"}, {"h_rm_mm": 62.0},
        "h", r0=R0, a0=A0, L=100.0, max_wall=MAX_WALL, phi=0.0)
    b = registry.build_meridian(
        {"type": "conical"}, {"h_second_rm_mm": 62.0},
        "h_second", r0=R0, a0=A0, L=100.0, max_wall=MAX_WALL, phi=0.0)
    m = P.splice(a, b, 0.5)
    assert m.info["joint"] == "matched"
    assert m.info["delta_theta_deg"] == pytest.approx(0.0, abs=1e-9)
    assert _joint_gap_deg(m) < 1e-6


# ---------------------------------------------------------------------------
# P4: Hermite-bridge fallback
# ---------------------------------------------------------------------------

@requires_mesher
def test_unmatched_joint_takes_the_bridge():
    m = _spliced(0.2)
    assert m.info["joint"] == "hermite_bridge"
    assert abs(m.info["delta_theta_deg"]) > P._SPLICE_MATCH_TOL_DEG   # the fallback condition (0.5)
    z_s, z_b = m.info["z_s_mm"], m.info["z_bridge_mm"]
    assert 0.0 < z_b - z_s <= 0.10 * m.info["L2_mm"] + 1e-9
    assert np.all(np.diff(m.z_mm) > 0)
    assert np.all(np.diff(m.r_mm) > 0)


@requires_mesher
@pytest.mark.parametrize("zs_frac", [0.2, 0.35, 0.65, 0.8])
def test_bridge_fallback_passes_p1(zs_frac):
    m = _spliced(zs_frac)
    assert m.info["joint"] == "hermite_bridge"           # these zs values do not match
    z_s, z_b = m.info["z_s_mm"], m.info["z_bridge_mm"]
    assert abs(m.info["delta_theta_deg"]) > P._SPLICE_MATCH_TOL_DEG
    # P1 at both bridge ends: the fitted tangent matches the parent angle there.
    i_s = int(np.searchsorted(m.z_mm, z_s, side="left")) - 1
    j_b = int(np.argmin(np.abs(m.z_mm - z_b)))
    assert abs(_tangent_deg(m, z_s, "start") - m.theta_deg[i_s]) < _JOINT_TOL_DEG
    assert abs(_tangent_deg(m, z_b, "end") - m.theta_deg[j_b]) < _JOINT_TOL_DEG


# ---------------------------------------------------------------------------
# Hermite fidelity away from the joint (existing generator test style, V2)
# ---------------------------------------------------------------------------

@requires_mesher
@pytest.mark.parametrize("zs_frac", [0.425, 0.475, 0.525, 0.575])
def test_shipped_splice_range_carries_c1_after_the_tol_correction(zs_frac):
    """2026-10-25 R9-audit regression: on the shipped config's own seed these zs_frac
    values measured parent wall-angle gaps of 1.752 / 0.602 / 0.617 / 1.876 deg - under
    the old 2-deg rule they shipped DIRECT (C0 kinks) while the catalog labeled C1.
    Under the corrected bar every zs on the shipped range passes the P1 bar."""
    m = _spliced(zs_frac)
    assert m.info["joint"] in ("matched", "hermite_bridge")
    assert _joint_gap_deg(m) < _JOINT_TOL_DEG
    assert np.all(np.diff(m.z_mm) > 0) and np.all(np.diff(m.r_mm) > 0)

@requires_mesher
@pytest.mark.parametrize("zs_frac", [0.2, 0.5, 0.8])
def test_hermite_fidelity_away_from_the_joint(zs_frac):
    m = _spliced(zs_frac)
    anc = P.select_anchors(m, 16)
    r_ref = P.hermite_reference(anc, m.z_mm)
    err = np.abs(r_ref - m.r_mm)
    away = np.abs(m.z_mm - m.info["z_s_mm"]) > _AWAY_MM
    assert err[away].max() <= _FIDELITY_TOL_MM
    # The joint itself is a kink by construction; the anchors still bound it.
    assert err.max() <= _FIDELITY_TOL_MM


# ---------------------------------------------------------------------------
# Registry dispatch, config, provenance
# ---------------------------------------------------------------------------

@requires_mesher
def test_registry_reads_nested_parent_knob_prefixes_only_when_present():
    """Parent-1/2 knobs use {p}_first_{name}/{p}_second_{name}; absent -> DEFAULT_KNOBS."""
    spec = {"type": "splice", "first": {"type": "tractrix"}, "second": {"type": "tractrix"}}
    # Only the flat knobs that exist are read; the rest fall back to DEFAULT_KNOBS.
    m = registry.build_meridian(spec, {"L_mm": 100.0, "h_second_fc_hz": 700.0}, "h",
                                r0=R0, a0=A0, L=100.0, max_wall=MAX_WALL, phi=0.0)
    assert m.r_mm[0] == pytest.approx(R0)
    # The second parent used fc=700: its mouth radius equals the tractrix a*sin(80 deg).
    from hornlab_search.constants import C_AIR
    a_mm = C_AIR / (2.0 * np.pi * 700.0) * 1000.0
    assert m.r_mm[-1] == pytest.approx(a_mm * np.sin(np.radians(MAX_WALL)), rel=1e-6)


def test_splice_requires_nested_parent_specs():
    with pytest.raises(registry.GeneratorError, match="first.*second"):
        registry.build_meridian({"type": "splice"}, {}, "h", r0=R0, a0=A0, L=L_OSSE,
                                max_wall=MAX_WALL, phi=0.0)


@requires_mesher
def test_example_config_seed_and_provenance():
    cfg = load_config(TYP / "splice_osse_tractrix.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace) and space.family == "FREEFORM"
    assert space.keys() == ["h_zs_frac"]                 # only the splice position is searched
    assert cfg.bounds_raw["h_zs_frac"]["lo"] == 0.2 and cfg.bounds_raw["h_zs_frac"]["hi"] == 0.8
    families.validate(space.seed)
    pH = space.seed.params["profileH"]["points"]
    assert pH[0][0] == 0.0 and pH[0][1] == pytest.approx(R0)
    assert space.seed.params["profileV"] == space.seed.params["profileH"]   # axisymmetric
    prov = space.provenance(space.seed)
    assert prov is not None
    assert prov["spec"]["profile_h"] == {
        "type": "splice", "first": {"type": "osse"}, "second": {"type": "tractrix"}}
    assert prov["derived"]["h"]["joint"] == "matched"
    json.dumps(prov)                                     # provenance is JSON-serializable
    json.dumps(space.seed.params)                        # params stay JSON-serializable
