"""MEH layout (``tools/cad/meh.py``) against the reference ``calc/meh_layout.py`` (task M5).

Pure numpy: no build123d, no gmsh. The reference script is imported as the ORACLE here (never by
package code), with its own frozen cone/CD records, so a number that drifts in the port fails.
"""
from __future__ import annotations

import importlib.util
import sys

import pytest

from conftest import REPO
from hornlab_search.mesh import step_build

REFERENCE = REPO / "docs" / "research" / "typologies" / "mini_meh_2026-10-29" / "calc" / "meh_layout.py"

#: T1 recipe: B&C 4NDF34 + FaitalPRO HF108, all four walls (C9 T1).
T1_RECIPE = dict(
    walls="tblr", exit_mm=25.4, cd_duct_mm=25.0, cd_body_d_mm=87.0, cd_body_len_mm=41.0,
    cone_cutout_mm=103.0, cone_depth_mm=66.0, across_frac=0.7, port_along_mm=20.0, spacer_mm=3.0,
)


@pytest.fixture(scope="module")
def tool():
    return step_build.load_cad_tool(tool=step_build.MEH_TOOL)


@pytest.fixture(scope="module")
def reference():
    name = "meh_layout_reference"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REFERENCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _reference_seed(reference, base, fractions):
    layout = reference.from_fractions(base, fractions)
    report = reference.check(layout)
    assert report["ok"], report["reasons"]
    return layout, report


def _t2_reference(reference):
    t2 = reference.Layout(reference.B_C_6NDL38, reference.HF108, ("tb",), 90, 60,
                          z_port=60, port_across=70, port_along=26, slide=10, spacer=4)
    base = reference.replace(t2, cd=reference.HF1440)
    return _reference_seed(reference, base, dict(
        cov_h=90, cov_v=60, z_frac=0.25, across_frac=0.8, port_along=30, spacer=3, slide=10, fill=0.0))


def _t1_reference(reference):
    t1 = reference.Layout(reference.B_C_4NDF34, reference.HF108, ("tb", "lr"), 90, 60,
                          z_port=45, port_across=40, port_along=20, slide=15, spacer=3)
    return _reference_seed(reference, t1, dict(
        cov_h=90, cov_v=60, z_frac=0.25, across_frac=0.7, port_along=20, spacer=3, slide=10))


def test_keys_and_defaults_are_the_c9_table(tool):
    assert set(tool.KEYS) == {
        "cov_h_deg", "cov_v_deg", "z_frac", "across_frac", "port_along_mm", "slide_mm", "walls",
        "env_w_mm", "env_h_mm", "env_d_mm", "box_t_mm", "roll_mm", "wall_t_mm", "spacer_mm",
        "exit_mm", "cd_duct_mm", "cd_body_d_mm", "cd_body_len_mm", "cone_cutout_mm",
        "cone_depth_mm", "clearance_mm",
    }
    assert tool.defaults() == {
        "cov_h_deg": 90.0, "cov_v_deg": 60.0, "z_frac": 0.25, "across_frac": 0.8,
        "port_along_mm": 30.0, "slide_mm": 10.0, "walls": "tb",
        "env_w_mm": 406.4, "env_h_mm": 406.4, "env_d_mm": 380.0, "box_t_mm": 18.0,
        "roll_mm": 20.0, "wall_t_mm": 6.0, "spacer_mm": 3.0,
        "exit_mm": 35.8, "cd_duct_mm": 40.0, "cd_body_d_mm": 124.0, "cd_body_len_mm": 75.0,
        "cone_cutout_mm": 145.0, "cone_depth_mm": 85.0, "clearance_mm": 3.0,
    }
    assert set(tool.INFERRED_KEYS) == {"exit_mm", "cd_duct_mm", "cone_cutout_mm", "cone_depth_mm"}


def test_t2a_seed_matches_the_reference(tool, reference):
    layout, ref = _t2_reference(reference)
    d = tool.derived(tool.defaults())
    assert d["ok"], d["reasons"]
    assert d["z_c"] == pytest.approx(ref["z_c"], abs=0.2)
    assert d["z_m"] == pytest.approx(ref["z_m"], abs=0.2)
    assert d["mouth_w"] == pytest.approx(ref["mouth_w"], abs=0.2)
    assert d["mouth_h"] == pytest.approx(ref["mouth_h"], abs=0.2)
    assert d["z_port_mm"] == pytest.approx(layout.z_port, abs=0.2)
    assert d["path_to_diaphragm_mm"] == pytest.approx(ref["path_to_diaphragm_mm"], abs=0.2)
    assert d["f_quarter_wave_hz"] == pytest.approx(ref["f_quarter_wave_hz"], abs=1.0)
    assert d["f_h_hz"] == pytest.approx(ref["f_h_hz"], abs=1.0)
    assert d["v_front_cm3"] == pytest.approx(ref["v_front_cm3"], abs=0.2)
    assert d["port_across_mm"] == pytest.approx(layout.port_across, abs=0.2)
    assert d["slide_mm"] == pytest.approx(layout.slide, abs=0.2)
    assert set(d["inferred_keys"]) == set(tool.INFERRED_KEYS)


def test_t1_seed_matches_the_reference(tool, reference):
    layout, ref = _t1_reference(reference)
    d = tool.derived(dict(tool.defaults(), **T1_RECIPE))
    assert d["ok"], d["reasons"]
    assert d["z_c"] == pytest.approx(ref["z_c"], abs=0.2)
    assert d["z_m"] == pytest.approx(ref["z_m"], abs=0.2)
    assert d["mouth_w"] == pytest.approx(ref["mouth_w"], abs=0.2)
    assert d["mouth_h"] == pytest.approx(ref["mouth_h"], abs=0.2)
    assert d["z_port_mm"] == pytest.approx(layout.z_port, abs=0.2)
    assert d["path_to_diaphragm_mm"] == pytest.approx(ref["path_to_diaphragm_mm"], abs=0.2)
    assert d["f_quarter_wave_hz"] == pytest.approx(ref["f_quarter_wave_hz"], abs=1.0)
    assert d["f_h_hz"] == pytest.approx(ref["f_h_hz"], abs=1.0)
    assert d["slide_mm"] == pytest.approx(layout.slide, abs=0.2)


def test_slide_repair_is_deterministic_and_logged(tool):
    d = tool.derived(dict(tool.defaults(), slide_mm=-10.0))
    assert d["ok"], d["reasons"]
    assert d["slide_mm"] == pytest.approx(32.0, abs=1e-9)     # the reference repair
    assert d["repairs"], "the repair must be logged"
    assert d["repairs"][0]["from_mm"] == pytest.approx(-10.0)
    assert d["repairs"][0]["reason"] == "driver_hits_cd"
    assert d["repairs"][0]["step_mm"] == pytest.approx(2.0)
    assert d["repairs"][-1]["to_mm"] == pytest.approx(32.0)


def test_envelope_violation_reports_reasons(tool):
    d = tool.derived(dict(tool.defaults(), env_w_mm=300.0, env_h_mm=300.0))
    assert d["ok"] is False
    assert {"driver_hits_cd", "driver_outside_face", "driver_past_mouth"} <= set(d["reasons"])


def test_port_centroids_are_mirror_paired(tool):
    d = tool.derived(tool.defaults())
    assert len(d["ports"]) == 2                                   # top + bottom, tb
    top, bottom = d["ports"]
    assert top["centroid_mm"][1] == pytest.approx(-bottom["centroid_mm"][1], abs=1e-9)
    assert top["centroid_mm"][0] == pytest.approx(bottom["centroid_mm"][0], abs=1e-9)
    assert top["centroid_mm"][2] == pytest.approx(bottom["centroid_mm"][2], abs=1e-9)
    assert top["area_mm2"] == pytest.approx(d["port_area_mm2"], abs=1e-9)
    assert top["path_to_diaphragm_mm"] == pytest.approx(d["path_to_diaphragm_mm"], abs=1e-9)
