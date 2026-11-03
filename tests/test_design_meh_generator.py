"""The ``meh`` generator dispatch in ``design/generated.py`` (added with M7's pipeline).

No CAD, no gmsh, no solver: this only proves the knob box materialises into a legal labelled STEP
recipe, which is the precondition for a CMA search over the MEH layout knobs.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import EXAMPLES, requires_build123d, requires_mesher
from hornlab_search.config import load_config
from hornlab_search.design.generated import GeneratedSpace, materialize

pytestmark = [requires_build123d, requires_mesher]

CONFIG = EXAMPLES / "typologies" / "meh_2026-10-30" / "meh_t2a_search.yaml"


@pytest.fixture(scope="module")
def cfg():
    return load_config(CONFIG)


def test_the_meh_knob_box_is_the_c9_search_set(cfg):
    space = GeneratedSpace.from_config(cfg)
    assert space.keys() == ["across_frac", "cov_h_deg", "cov_v_deg", "port_along_mm",
                            "slide_mm", "z_frac"]


def test_seed_is_the_repaired_t2a_recipe(cfg):
    space = GeneratedSpace.from_config(cfg)
    cad = space.seed.params["cad"]
    assert cad["tool"] == "meh"
    assert cad["slide_mm"] == pytest.approx(32.0)     # the C9 default 10 repairs to 32 (M8 link 1)
    assert cad["cov_h_deg"] == pytest.approx(90.0)
    assert cad["walls"] == "tb"


def test_every_knob_vector_materialises_a_legal_recipe_or_refuses(cfg):
    space = GeneratedSpace.from_config(cfg)
    for x in (np.zeros(len(space.keys())), np.ones(len(space.keys())), np.full(len(space.keys()), 0.5)):
        knobs = space.knobs_from_unit(x)
        recipe = materialize(cfg.generator, knobs, cfg.brief)["cad"]
        assert set(cfg.generator["fixed"]) <= set(recipe)
        for key in space.keys():
            assert recipe[key] == pytest.approx(knobs[key])


def test_an_unknown_knob_is_refused(cfg):
    with pytest.raises(ValueError, match="unknown key"):
        materialize(dict(cfg.generator), {"not_a_meh_key": 1.0}, cfg.brief)


def test_an_illegal_envelope_refuses(cfg):
    gen = dict(cfg.generator)
    gen["fixed"] = dict(gen["fixed"], env_w_mm=200.0)
    with pytest.raises(ValueError, match="meh:"):
        materialize(gen, {}, cfg.brief)
