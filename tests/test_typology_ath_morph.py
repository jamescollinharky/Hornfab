"""ATH CORE / TwinRay framework entries and the native Morph search path (offline)."""
from __future__ import annotations

import copy

import pytest

from hornlab_search.config import load_config
from hornlab_search.design import families
from hornlab_search.design.generators import registry
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import sizing
from hornlab_search.types import Design, MeshSpec

from conftest import EXAMPLES, requires_mesher

TYP = EXAMPLES / "typologies"


def _mspec() -> MeshSpec:
    return MeshSpec(epw=6.0, f_max_hz=10000.0, quadrants="1", max_triangles=73600)


def _core_cfg():
    return load_config(TYP / "ath_core.yaml")


def _twin_cfg():
    return load_config(TYP / "ath_twinray_380.yaml")


# ------------------------------------------------------------------ families surface

def test_morph_keys_exist_for_every_morph_capable_family():
    for family in ("OSSE", "R-OSSE", "ICW", "FREEFORM"):
        for key in ("morph_target", "morph_width_mm", "morph_height_mm", "morph_corner_mm",
                    "morph_exponent", "morph_rate", "morph_fixed",
                    "morph_allow_shrinkage"):
            assert key in families.FAMILY_KEYS[family], (family, key)
    assert families.FAMILY_KEYS["OSSE"]["morph_exponent"].lo == 2.0
    assert families.FAMILY_KEYS["OSSE"]["morph_exponent"].hi == 16.0


def test_morph_target_out_of_range_is_refused_by_the_search_layer():
    # Review R-3 (2026-10-26): a target code outside 0..3 must fail in our layer, not later in
    # the mesher.
    for family in ("OSSE", "R-OSSE", "ICW", "FREEFORM"):
        spec = families.FAMILY_KEYS[family]["morph_target"]
        assert (spec.lo, spec.hi) == (0, 3), family
    data = load_config(EXAMPLES / "typologies" / "ath_core.yaml").seed_params
    params = {k: v for k, v in data.items()}
    params["morph_target"] = 4
    with pytest.raises(families.GeometryInvalidError, match="morph_target"):
        families.validate(Design(family="OSSE", params=params))


def test_freeform_morph_routes_and_superellipse_target_keeps_its_exponent(tmp_path):
    d = Design("FREEFORM", {
        "profileH": {"points": [[0.0, 12.7], [120.0, 160.0]]},
        "profileV": {"points": [[0.0, 12.7], [120.0, 160.0]]},
        "crossSections": [{"t": 0.0, "shape": "circle"}, {"t": 1.0, "shape": "ellipse"}],
        "morph_target": 3,
        "morph_exponent": 5.5,
        "morph_rate": 2.5,
    })
    res = sizing.res_mm_for(6.0, 10000.0)
    cfg = families.to_mesher_config(d, _mspec(), res, tmp_path / "m.msh")
    assert cfg["morph"] == {"morph_target": 3, "morph_exponent": 5.5, "morph_rate": 2.5}


@pytest.mark.parametrize("family,params", [
    ("R-OSSE", dict(R_mm=150.0, r0_mm=12.7, a_deg=60.0, a0_deg=15.5, k=1.0,
                    q=1.0, exponent=2.0, aspect_ratio=1.0)),
    ("ICW", dict(termination="flat_baffle", r0_mm=12.7, a0_deg=14.5, L_mm=160.0,
                 R_mm=130.0, coverage_angle_deg=50.0, hold_start=0.3, hold_end=0.7)),
])
def test_morph_routes_for_the_other_native_families(family, params, tmp_path):
    d = Design(family, {**params, "morph_target": 2, "morph_rate": 2.0})
    res = sizing.res_mm_for(6.0, 10000.0)
    cfg = families.to_mesher_config(d, _mspec(), res, tmp_path / "m.msh")
    assert cfg["morph"] == {"morph_target": 2, "morph_rate": 2.0}


# ------------------------------------------------------------------ CORE

def test_ath_core_is_native_osse_with_native_morph_search():
    cfg = _core_cfg()
    assert cfg.family == "OSSE"
    assert cfg.generator is None
    space = DesignSpace.from_config(cfg)
    assert {"morph_width_mm", "morph_height_mm", "morph_corner_mm",
            "morph_rate", "morph_fixed"} <= set(space.keys())
    for key in ("morph_width_mm", "morph_height_mm", "morph_corner_mm", "morph_rate",
                "morph_fixed"):
        b = space.bounds[key]
        assert b.lo < b.hi, f"{key} must be a real search box"
    seed = space.seed.params
    assert seed["morph_target"] == 1
    assert seed["morph_allow_shrinkage"] == 1
    # The morph shape itself is searchable, not pinned to the published rectangle.
    assert space.bounds["morph_target"].search
    assert (space.bounds["morph_target"].lo, space.bounds["morph_target"].hi) == (1.0, 3.0)
    assert space.bounds["morph_exponent"].search
    assert (space.bounds["morph_exponent"].lo, space.bounds["morph_exponent"].hi) == (2.0, 8.0)
    # The seed sits inside the continuous morph boxes, not on a bound. morph_fixed is the
    # published 0.0 and its legal lower end is also 0.0, so it is checked separately.
    for key in ("morph_width_mm", "morph_height_mm", "morph_corner_mm", "morph_rate"):
        assert space.bounds[key].lo < float(seed[key]) < space.bounds[key].hi
    assert space.bounds["morph_fixed"].lo == 0.0
    assert float(seed["morph_fixed"]) == 0.0


def test_ath_core_routes_morph_into_the_mesher_morph_section(tmp_path):
    cfg = _core_cfg()
    res = sizing.res_mm_for(6.0, 10000.0)
    mcfg = families.to_mesher_config(Design(cfg.family, copy.deepcopy(cfg.seed_params)),
                                     _mspec(), res, tmp_path / "m.msh")
    morph = mcfg["morph"]
    assert morph["morph_target"] == 1
    assert morph["morph_width_mm"] == pytest.approx(397.0)
    assert morph["morph_height_mm"] == pytest.approx(397.0)
    assert morph["morph_corner_mm"] == pytest.approx(16.5)
    assert morph["morph_rate"] == pytest.approx(3.0)
    assert morph["morph_allow_shrinkage"] == 1


# ------------------------------------------------------------------ TwinRay

@requires_mesher
def test_ath_twinray_seed_reproduces_the_published_mouth_and_searches_the_outline():
    cfg = _twin_cfg()
    assert cfg.family == "FREEFORM"
    assert cfg.generator is not None
    space = DesignSpace.from_config(cfg)
    assert "mouth_exponent" in space.keys()
    params = space.seed.params
    assert params["crossSections"][-1]["shape"] == "superellipse"
    assert params["crossSections"][-1]["exponent"] == pytest.approx(4.0)
    w = 2 * params["profileH"]["points"][-1][1]
    h = 2 * params["profileV"]["points"][-1][1]
    assert w == pytest.approx(380.0, abs=12.0)
    assert h == pytest.approx(303.0, abs=12.0)
    assert space.bounds["mouth_exponent"].lo < 4.0 < space.bounds["mouth_exponent"].hi


@requires_mesher
def test_ath_twinray_materialize_emits_the_searched_superellipse_outline():
    cfg = _twin_cfg()
    params = registry.materialize(cfg.generator, cfg.seed_params, cfg.brief)
    assert params["crossSections"][-1]["shape"] == "superellipse"
    assert params["crossSections"][-1]["exponent"] == pytest.approx(4.0)
    assert not any(k.startswith("morph_") for k in params)


# ------------------------------------------------------------------ generator opt-in

def test_generator_without_morph_is_byte_identical():
    cfg = load_config(TYP / "conical.yaml")
    base = cfg.seed_params
    off = {**base, "morph_target": 0}
    a = registry.materialize(cfg.generator, base, cfg.brief)
    b = registry.materialize(cfg.generator, off, cfg.brief)
    assert a == b
    assert not any(k.startswith("morph_") for k in a)


def test_generator_morph_opt_in_emits_the_native_keys():
    cfg = load_config(TYP / "conical.yaml")
    knobs = {**cfg.seed_params, "morph_target": 2, "morph_rate": 2.0,
             "morph_fixed": 0.1}
    params = registry.materialize(cfg.generator, knobs, cfg.brief)
    assert params["morph_target"] == 2
    assert params["morph_rate"] == pytest.approx(2.0)
    assert params["morph_fixed"] == pytest.approx(0.1)


def test_generator_morph_refuses_a_second_outline_mechanism():
    cfg = load_config(TYP / "conical.yaml")
    gen = copy.deepcopy(cfg.generator)
    gen["mouth"] = "rounded_rectangle"
    knobs = {**cfg.seed_params, "morph_target": 1}
    with pytest.raises(registry.GeneratorError, match="native morph needs mouth: ellipse"):
        registry.materialize(gen, knobs, cfg.brief)
