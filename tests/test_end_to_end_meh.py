"""M7: the MEH briefs and CAD seed configs, plus the real-solver end-to-end gate.

The offline tests load every MEH config/brief and compare the CAD tool's ``derived()`` layout
with ``calc/layout_out.md`` "Final seeds" (CPU, pure numpy; no gmsh, no solver). The real
CAD + BEM run is marked ``slow`` + ``gpu`` and is deselected everywhere except the owner's
GPU validation lane.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, requires_beat, requires_build123d, requires_mesher
from hornlab_search.config import load_brief, load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import step_build

TYPOLOGIES = EXAMPLES / "typologies" / "meh_2026-10-30"
BRIEFS = EXAMPLES / "briefs" / "meh_2026-10-30"

CONFIG_PATHS = sorted(TYPOLOGIES.glob("*.yaml"))
BRIEF_PATHS = sorted(BRIEFS.glob("*.yaml"))

#: layout_out.md "Final seeds" (after repair), mm / Hz. ``port_area`` is port_across x
#: port_along; the T2-B row's reference CD (HF108) differs from the T2 brief's HF1440, so its
#: port centroid is the only row assertion taken from that table (see meh_t2b.yaml).
SEEDS = {
    "meh_t2a": {"walls": "tb", "ports": 2, "z_m": 144.0, "z_port": 45.0,
                "mouth_w": 330.0, "mouth_h": 191.0, "v_front_cm3": 251.0},
    "meh_t2b": {"walls": "tb", "ports": 2, "z_m": 144.0, "z_port": 39.9},
    "meh_t1": {"walls": "tblr", "ports": 4, "z_m": 150.0, "z_port": 44.0,
               "mouth_w": 330.0, "mouth_h": 191.0, "v_front_cm3": 89.0},
}


def _tool():
    return step_build.load_cad_tool(tool=step_build.MEH_TOOL)


# ------------------------------------------------------------------ configs


def _seed_recipe(cfg):
    """The seed's CAD recipe: a CAD-authored seed carries it, a generator seed materialises it."""
    gen = getattr(cfg, "generator", None) or {}
    if str(gen.get("name", "")) == "meh":
        from hornlab_search.design.generated import materialize
        return materialize(gen, dict(cfg.seed_params), cfg.brief)["cad"]
    return cfg.seed_params["cad"]


@pytest.mark.parametrize("path", CONFIG_PATHS, ids=lambda p: p.stem)
def test_every_meh_config_loads_as_a_cad_seed(path):
    cfg = load_config(path)
    assert cfg.family == "FREEFORM"
    assert cfg.objective_version == 5
    assert cfg.objective_params["version"] == 5
    assert cfg.objective_params["cov_narrow_ratio"] == 2.0
    assert cfg.mesh.quadrants == "1"                 # C2: quarter meh STEP
    assert cfg.brief is not None and cfg.brief.get("meh")
    recipe = _seed_recipe(cfg)
    assert recipe["tool"] == step_build.MEH_TOOL
    # Every C9 recipe key is explicit (no hidden tool defaults in a YAML or generator seed).
    assert set(recipe) - {"tool"} == set(_tool().KEYS)
    if str((getattr(cfg, "generator", None) or {}).get("name", "")) == "meh":
        # A generator seed exposes exactly the six C9 search knobs.
        assert set(cfg.bounds_raw) == {"across_frac", "cov_h_deg", "cov_v_deg", "port_along_mm",
                                       "slide_mm", "z_frac"}
    else:
        assert cfg.bounds_raw == {}


@pytest.mark.parametrize("path", CONFIG_PATHS, ids=lambda p: p.stem)
def test_every_meh_config_derives_the_layout_out_seed(path):
    cfg = load_config(path)
    recipe = _seed_recipe(cfg)
    derived = _tool().derived(recipe)
    assert derived["ok"], derived["reasons"]
    # A generator search config shares the geometry of its CAD-authored sibling (`<name>_search`).
    want = SEEDS[cfg.name if cfg.name in SEEDS else cfg.name.removesuffix("_search")]
    assert derived["walls"] == want["walls"]
    assert len(derived["ports"]) == want["ports"]
    assert derived["z_m"] == pytest.approx(want["z_m"], abs=0.6)
    assert derived["z_port_mm"] == pytest.approx(want["z_port"], abs=0.6)
    for key, tol in (("mouth_w", 0.6), ("mouth_h", 0.6), ("v_front_cm3", 0.6)):
        if key in want:
            assert derived[key] == pytest.approx(want[key], abs=tol)
    # C9's port centroid/path/f_h are all present for the inner optimiser's layout context.
    assert derived["port_area_mm2"] > 0.0
    assert derived["path_to_diaphragm_mm"] > 0.0
    assert derived["f_quarter_wave_hz"] > 0.0


def test_meh_configs_select_the_real_brief_and_drivers():
    t2 = load_config(TYPOLOGIES / "meh_t2a.yaml")
    t1 = load_config(TYPOLOGIES / "meh_t1.yaml")
    assert t2.brief["name"] == "meh_home_90x60_t2"
    assert t1.brief["name"] == "meh_home_90x60_t1"
    assert t2.brief["meh"]["groups"]["cd"]["drivers"] == ["faitalpro_hf1440"]
    assert t1.brief["meh"]["groups"]["cd"]["drivers"] == ["faitalpro_hf108"]
    assert t2.brief["meh"]["groups"]["mid"]["count"] == 2
    assert t1.brief["meh"]["groups"]["mid"]["count"] == 4
    # C3: only the two tags this build knows.
    for cfg in (t2, t1):
        tags = {cfg.brief["meh"]["groups"]["cd"]["tag"], cfg.brief["meh"]["groups"]["mid"]["tag"]}
        assert tags == {2, 10}
    # The seed config's CAD recipe must match the brief's CD group reference (T2/T1).
    assert float(t2.seed_params["cad"]["exit_mm"]) == 35.8
    assert float(t1.seed_params["cad"]["exit_mm"]) == 25.4


# ------------------------------------------------------------------ briefs


@pytest.mark.parametrize("path", BRIEF_PATHS, ids=lambda p: p.stem)
def test_every_meh_brief_loads_and_validates(path):
    brief = load_brief(path)
    block = brief["meh"]
    assert block["groups"]["cd"]["tag"] == 2
    assert block["groups"]["mid"]["tag"] == 10
    assert block["groups"]["mid"]["count"] >= 1
    assert len(block["groups"]["cd"]["drivers"]) == 1      # M6 validator contract
    assert block["xo_hz"]["lo"] < block["xo_hz"]["hi"]
    assert set(block["xo_orders"]) <= {2, 4, 8}
    assert brief["objective"]["version"] == 5
    assert brief["target"]["band_lo_hz"] == 120.0
    assert brief["target"]["band_hi_hz"] == 12000.0


def test_t1_brief_has_the_compact_high_pass_and_target():
    brief = load_brief(BRIEFS / "meh_home_90x60_t1.yaml")
    block = brief["meh"]
    assert block["hp_hz"] == 160.0
    assert block["xo_hz"] == {"lo": 1000.0, "hi": 1500.0}
    assert block["groups"]["mid"]["count"] == 4
    assert block["spl_target"][0] == [160.0, 112.0]


def test_t2_brief_has_the_home_target():
    brief = load_brief(BRIEFS / "meh_home_90x60_t2.yaml")
    block = brief["meh"]
    assert block["hp_hz"] == 120.0
    assert block["xo_hz"] == {"lo": 650.0, "hi": 1100.0}
    assert block["groups"]["mid"]["count"] == 2
    assert block["spl_target"][1] == [250.0, 120.0]


# ------------------------------------------------------------------ real run (GPU lane)


@pytest.mark.slow
@pytest.mark.gpu
@requires_beat
@requires_mesher
@requires_build123d
def test_real_meh_end_to_end_gpu(tmp_path):
    """Owner-run only: real CAD mesh + multi-source BEM + inner optimiser + objective v5."""
    from hornlab_search.search import evaluate as evmod
    from hornlab_search.solve.beat import BeatBackend

    cfg = load_config(TYPOLOGIES / "meh_t2a.yaml")
    space = DesignSpace.from_config(cfg)
    backend = BeatBackend("cuda")
    ctx = evmod.make_context(cfg, cache_dir=tmp_path / "cache", lib_shas={})
    ctx.write_ndjson = False
    ev = evmod.evaluate(space.seed, space, cfg, "screen", tmp_path / "run", None, backend, ctx=ctx)
    assert ev.error == "", ev.error
    assert np.isfinite(ev.objective)
    assert ev.outcome is not None and ev.outcome.response is not None
    assert ev.outcome.response.channel_tags == (2, 10)


