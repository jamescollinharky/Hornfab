"""Offline tests for tools/run_staged_search.py (staged vs joint A/B harness).

Hermetic: no GPU, no Julia, no ``hornlab-search`` subprocess. Pure helpers + a dry-run of
``main`` that only writes derived YAMLs.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

from conftest import REPO

TOOL = REPO / "tools" / "run_staged_search.py"
JOINT = REPO / "examples" / "typologies" / "staged_ab_2026-10-31" / "joint__crease_core_law.yaml"
STAGE_A = REPO / "examples" / "typologies" / "staged_ab_2026-10-31" / "stageA_macro__crease_core_law.yaml"
STAGE_B = REPO / "examples" / "typologies" / "staged_ab_2026-10-31" / "stageB_shape__crease_core_law.yaml"


def _load():
    spec = importlib.util.spec_from_file_location("run_staged_search_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


T = _load()


def _joint():
    return yaml.safe_load(JOINT.read_text(encoding="utf-8"))


def test_committed_configs_exist_and_budgets_sum():
    assert JOINT.is_file() and STAGE_A.is_file() and STAGE_B.is_file()
    j = _joint()
    a = yaml.safe_load(STAGE_A.read_text(encoding="utf-8"))
    b = yaml.safe_load(STAGE_B.read_text(encoding="utf-8"))
    assert j["search"]["budget"] == 60
    assert a["search"]["budget"] == 20
    assert b["search"]["budget"] == 20
    assert T.resolve_budgets(60) == (20, 20, 20)


def test_macro_and_shape_partition_covers_joint_searchable():
    j = _joint()
    searchable = T.searchable_keys(j)
    macro = T.macro_active(j)
    shape = T.shape_active(j)
    assert macro == {"L_mm", "a_deg", "n", "s", "k"}
    assert "az_a_sf_amp" in shape and "morph_corner_mm" in shape
    assert macro.isdisjoint(shape)
    assert macro | shape == searchable


def test_stage_a_pins_all_shape_keys():
    a = yaml.safe_load(STAGE_A.read_text(encoding="utf-8"))
    for key in T.shape_active(_joint()):
        b = a["bounds"][key]
        assert b.get("search") is False
        assert b["lo"] == b["hi"]


def test_seed_from_best_overwrites_overlapping_keys():
    doc = _joint()
    best = {"L_mm": 400.0, "a_deg": 12.0, "az_a_sf_amp": 40.0, "unknown_extra": 1}
    out = T.seed_from_best(doc, best)
    assert out["seed_params"]["L_mm"] == 400.0
    assert out["seed_params"]["a_deg"] == 12.0
    assert out["seed_params"]["az_a_sf_amp"] == 40.0
    assert "unknown_extra" not in out["seed_params"]


def test_build_stage_b_pins_macro_at_best_and_opens_shape():
    j = _joint()
    b_tmpl = yaml.safe_load(STAGE_B.read_text(encoding="utf-8"))
    best = dict(j["seed_params"])
    best.update({"L_mm": 310.0, "a_deg": 18.0, "n": 4.5, "s": 0.8, "k": 1.2})
    out = T.build_stage_b(b_tmpl, j, best, budget=20)
    assert out["seed_params"]["L_mm"] == 310.0
    assert out["bounds"]["L_mm"]["search"] is False
    assert out["bounds"]["L_mm"]["lo"] == 310.0
    assert out["bounds"]["a_deg"]["hi"] == 18.0
    # Shape boxes restored to the joint full range.
    assert out["bounds"]["az_a_sf_amp"].get("search") is not False
    assert out["bounds"]["az_a_sf_amp"]["lo"] == j["bounds"]["az_a_sf_amp"]["lo"]
    assert out["bounds"]["az_a_sf_amp"]["hi"] == j["bounds"]["az_a_sf_amp"]["hi"]
    assert out["search"]["budget"] == 20


def test_build_stage_c_narrows_around_best():
    j = _joint()
    best = dict(j["seed_params"])
    best["a_deg"] = 20.0
    best["L_mm"] = 300.0
    out = T.build_stage_c(j, best, budget=20, frac=0.12, sigma0=0.06)
    full_a = j["bounds"]["a_deg"]
    width = full_a["hi"] - full_a["lo"]
    half = 0.12 * width
    assert out["bounds"]["a_deg"]["lo"] == max(full_a["lo"], 20.0 - half)
    assert out["bounds"]["a_deg"]["hi"] == min(full_a["hi"], 20.0 + half)
    assert out["seed_params"]["a_deg"] == 20.0
    assert out["search"]["sigma0"] == 0.06
    assert out["search"]["budget"] == 20
    assert out["name"] == "stageC_polish__crease_core_law"


def test_crease_angles_match_published_core_seed():
    """CORE seed: a ≈ 25.0 / 33.8 / 23.4 at p = 0/45/90 (LEARNINGS / config header)."""
    j = _joint()
    angles = T.crease_angles(j["seed_params"])
    assert angles is not None
    assert abs(angles["a0_deg"] - 25.0) < 0.6
    assert abs(angles["a45_deg"] - 33.8) < 0.6
    assert abs(angles["a90_deg"] - 23.4) < 0.6
    assert angles["crease_strength_deg"] > 8.0


def test_resolve_backend_auto_is_metal_on_darwin(monkeypatch):
    monkeypatch.setattr(T.sys, "platform", "darwin")
    assert T.resolve_backend("auto") == "beat_metal"
    monkeypatch.setattr(T.sys, "platform", "win32")
    assert T.resolve_backend("auto") == "beat_cuda"
    assert T.resolve_backend("beat_cpu") == "beat_cpu"


def test_apply_solve_backend_clears_cuda_fused_off_cuda():
    j = _joint()
    assert j["solve"]["backend"] == "beat_cuda"
    assert j["solve"].get("cuda_fused") is True
    metal = T.apply_solve_backend(j, "beat_metal")
    assert metal["solve"]["backend"] == "beat_metal"
    assert metal["solve"]["cuda_fused"] is False
    # Original untouched.
    assert j["solve"]["backend"] == "beat_cuda"


def test_dry_run_on_mac_emits_metal_configs(tmp_path, monkeypatch):
    monkeypatch.setattr(T.sys, "platform", "darwin")
    out = tmp_path / "mac"
    rc = T.main([
        "--base", str(JOINT), "--stage-a", str(STAGE_A),
        "--stage-b-template", str(STAGE_B),
        "--out", str(out), "--dry-run", "--backend", "auto",
    ])
    assert rc == 0
    plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    assert plan["backend"] == "beat_metal"
    joint = yaml.safe_load((out / "configs" / "joint__crease_core_law.yaml").read_text())
    assert joint["solve"]["backend"] == "beat_metal"
    assert joint["solve"]["cuda_fused"] is False


def test_synthetic_coupled_ab_returns_verdict():
    result = T.run_synthetic_ab(budget_total=60, seed=1234, coupling=0.7)
    assert result["verdict"] in {"staged+polish wins", "joint wins", "tie"}
    assert result["staged"]["n_evals"] >= 60
    assert result["joint"]["n_evals"] >= 60
    assert result["staged"]["J_C"] <= result["seed_J"]
    assert result["joint"]["J"] <= result["seed_J"]


def test_synthetic_cli_writes_json(tmp_path):
    out = tmp_path / "syn"
    rc = T.main(["--synthetic", "--out", str(out), "--budget-total", "60"])
    assert rc == 0
    data = json.loads((out / "SYNTHETIC.json").read_text(encoding="utf-8"))
    assert "verdict" in data
    assert (out / "COMPARE_SYNTHETIC.md").is_file()


def test_stage_knob_schedule_lists_fixed():
    j = yaml.safe_load(JOINT.read_text(encoding="utf-8"))
    sched = T.stage_knob_schedule(j)
    assert set(sched["stage_A_macro"]["active"]).issubset(T.MACRO_KEYS)
    assert set(sched["stage_B_shape"]["active"]).issubset(T.SHAPE_KEYS)
    joint = set(sched["joint_searchable"])
    assert set(sched["stage_A_macro"]["fixed"]) == joint - set(sched["stage_A_macro"]["active"])
    assert set(sched["stage_B_shape"]["fixed"]) == joint - set(sched["stage_B_shape"]["active"])
    assert sched["stage_C_polish"]["fixed"] == []
    assert "r0_mm" in sched["permanently_pinned"] or "morph_target" in sched["permanently_pinned"]


def test_dry_run_writes_derived_configs_and_compare(tmp_path):
    out = tmp_path / "staged_ab"
    rc = T.main([
        "--base", str(JOINT),
        "--stage-a", str(STAGE_A),
        "--stage-b-template", str(STAGE_B),
        "--out", str(out),
        "--dry-run",
        "--both",
    ])
    assert rc == 0
    assert (out / "plan.json").is_file()
    assert (out / "COMPARE.md").is_file()
    assert (out / "configs" / "stageA_macro__crease_core_law.yaml").is_file()
    assert (out / "configs" / "stageB_shape__crease_core_law.yaml").is_file()
    assert (out / "configs" / "stageC_polish__crease_core_law.yaml").is_file()
    assert (out / "configs" / "joint__crease_core_law.yaml").is_file()
    plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    assert plan["budgets"] == {"A": 20, "B": 20, "C": 20, "joint": 60}
    sched = plan["knob_schedule"]
    assert "L_mm" in sched["stage_A_macro"]["active"]
    assert "az_a_sf_amp" in sched["stage_A_macro"]["fixed"]
    assert "L_mm" in sched["stage_B_shape"]["fixed"]
    assert "az_a_sf_amp" in sched["stage_B_shape"]["active"]
    compare = (out / "COMPARE.md").read_text(encoding="utf-8")
    assert "## Knob schedule" in compare
    assert "Fixed / pinned this stage" in compare
    assert "`L_mm`" in compare
    # Stage C must be narrowed vs the joint full box on a searched macro key.
    c = yaml.safe_load((out / "configs" / "stageC_polish__crease_core_law.yaml").read_text())
    j = yaml.safe_load((out / "configs" / "joint__crease_core_law.yaml").read_text())
    assert c["bounds"]["L_mm"]["hi"] - c["bounds"]["L_mm"]["lo"] < (
        j["bounds"]["L_mm"]["hi"] - j["bounds"]["L_mm"]["lo"])
    assert c["search"]["sigma0"] == T.POLISH_SIGMA0
