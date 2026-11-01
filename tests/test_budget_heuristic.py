"""Offline tests for Hansen-grounded search budget suggestions."""
from __future__ import annotations

import math

import pytest

from hornlab_search.search.budget_heuristic import (
    GUI_BUDGET_CAP,
    compare_budget,
    default_popsize,
    screen_budget,
    suggest_budget,
)


def test_default_popsize_matches_hansen():
    assert default_popsize(1) == 4
    assert default_popsize(5) == 4 + int(3 * math.log(5))
    assert default_popsize(17) == 4 + int(3 * math.log(17))


def test_screen_and_compare_match_campaign():
    assert screen_budget(1) == 40
    assert screen_budget(5) == 50
    assert compare_budget(1) == 150
    assert compare_budget(8) == 200


def test_single_cma_uses_hansen_100n_floored_at_150():
    s1 = suggest_budget(1, restarts_mode="off")
    assert s1["recommended"] == 150
    assert s1["hansen_100n"] == 100
    assert s1["popsize_default"] == 4

    s5 = suggest_budget(5, restarts_mode="config")
    assert s5["recommended"] == 500
    assert s5["screen"] == 50
    assert s5["compare"] == 150

    s17 = suggest_budget(17)
    assert s17["recommended"] == 1700
    assert s17["restarts_mode"] == "config_default"


def test_ipop_inflates_for_restarts():
    # N=5 single=500; screen=50; R=9 → (1+9)*50=500 → still 500
    low = suggest_budget(5, restarts_mode="ipop", restarts_max=2)
    assert low["recommended"] == 500

    # R=15 → 16*50=800 > 500
    high = suggest_budget(5, restarts_mode="ipop", restarts_max=15)
    assert high["recommended"] == 800
    assert high["restarts_max"] == 15


def test_bipop_adds_small_run_uplift():
    # N=5 single=500; BIPOP base = ceil(1.25*500)=625
    b = suggest_budget(5, restarts_mode="bipop", restarts_max=2)
    assert b["recommended"] == 625


def test_gui_cap():
    huge = suggest_budget(100, restarts_mode="off")
    assert huge["uncapped"] == 10000
    assert huge["recommended"] == GUI_BUDGET_CAP
    assert huge["capped"] is True


def test_bad_mode_raises():
    with pytest.raises(ValueError, match="restarts_mode"):
        suggest_budget(5, restarts_mode="ipopx")
