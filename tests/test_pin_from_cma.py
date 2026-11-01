"""Offline tests for CMA-driven knob pin recommendations."""
from __future__ import annotations

import copy

import pytest

from hornlab_search.search.pin_from_cma import (
    apply_pins_to_config,
    format_pin_plan_md,
    recommend_pins,
)


def _cov(shares_stds: dict[str, tuple[float, float]]) -> dict:
    """Build a minimal cma_covariance from {key: (share, std_unit)}."""
    coords = []
    for k, (share, std) in shares_stds.items():
        coords.append({"key": k, "share": share, "std_unit": std, "C_ii": std ** 2})
    return {"coordinates": coords, "n_dim": len(coords), "sigma": 0.2}


def test_recommend_pins_small_share_and_std():
    # N=4 → share_thresh = max(0.04, 0.5/4)=0.125
    # median std of [0.01,0.02,0.10,0.12] = 0.06; std_thresh=0.35*0.06=0.021
    cov = _cov({
        "a": (0.02, 0.01),   # pin — share and std both under thresh
        "b": (0.03, 0.05),   # keep — std above thresh
        "c": (0.40, 0.10),   # keep — large share
        "d": (0.55, 0.12),   # keep
    })
    best = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}
    plan = recommend_pins(cov, best_params=best)
    assert plan["pin"] == ["a"]
    assert set(plan["keep"]) == {"b", "c", "d"}
    pin_a = next(d for d in plan["decisions"] if d["key"] == "a")
    assert pin_a["action"] == "pin" and pin_a["value"] == 1.0


def test_spearman_veto_keeps_influential_knob():
    cov = _cov({
        "a": (0.02, 0.01),
        "b": (0.40, 0.10),
        "c": (0.58, 0.12),
    })
    best = {"a": 1.0, "b": 2.0, "c": 3.0}
    sens = [{"key": "a", "rho": 0.8}]  # |rho| >= 0.35 → veto
    plan = recommend_pins(cov, best_params=best, sens=sens)
    assert "a" in plan["keep"]
    reasons = next(d["reasons"] for d in plan["decisions"] if d["key"] == "a")
    assert any("Spearman veto" in r for r in reasons)


def test_min_keep_and_max_pin_fraction():
    # All four pass share+std gates; max_pin_fraction=0.5 and min_keep=2 → at most 2 pins.
    cov = _cov({
        "a": (0.01, 0.01),
        "b": (0.02, 0.01),
        "c": (0.03, 0.01),
        "d": (0.04, 0.01),
    })
    best = {k: float(i) for i, k in enumerate("abcd", 1)}
    plan = recommend_pins(cov, best_params=best, min_keep=2, max_pin_fraction=0.5,
                          std_ratio=2.0)  # std gate always true here
    assert len(plan["pin"]) == 2
    assert len(plan["keep"]) == 2
    # Smallest shares pinned first
    assert plan["pin"] == ["a", "b"]


def test_no_best_value_skips_pin():
    cov = _cov({"a": (0.02, 0.01), "b": (0.98, 0.2)})
    plan = recommend_pins(cov, best_params={"b": 1.0})  # a missing
    assert "a" in plan["keep"]
    assert any("no_best_value" in r for r in
               next(d["reasons"] for d in plan["decisions"] if d["key"] == "a"))


def test_permanently_pinned_ignored():
    cov = _cov({"a": (0.02, 0.01), "b": (0.98, 0.2)})
    bounds = {"a": {"lo": 1, "hi": 1, "search": False}, "b": {"lo": 0, "hi": 1}}
    plan = recommend_pins(cov, best_params={"a": 1.0, "b": 2.0}, bounds=bounds)
    assert "a" not in plan["pin"] and "a" not in plan["keep"]
    assert "a" in plan["permanently_pinned"]


def test_apply_pins_to_config_round_trip():
    doc = {
        "seed_params": {"a": 0.0, "b": 0.0, "c": 0.0},
        "bounds": {
            "a": {"lo": 0.0, "hi": 10.0},
            "b": {"lo": 0.0, "hi": 10.0},
            "c": {"lo": 0.0, "hi": 10.0},
        },
    }
    plan = {
        "decisions": [
            {"key": "a", "action": "pin", "value": 3.5, "reasons": []},
            {"key": "b", "action": "keep", "reasons": []},
        ],
    }
    out = apply_pins_to_config(doc, plan)
    assert out["bounds"]["a"] == {"lo": 3.5, "hi": 3.5, "search": False}
    assert out["seed_params"]["a"] == 3.5
    assert out["bounds"]["b"] == {"lo": 0.0, "hi": 10.0}
    assert doc["bounds"]["a"]["hi"] == 10.0  # original untouched


def test_format_pin_plan_md_mentions_actions():
    # N≥3 so min_keep=2 still allows a pin
    plan = recommend_pins(
        _cov({"a": (0.02, 0.01), "b": (0.40, 0.10), "c": (0.58, 0.12)}),
        best_params={"a": 1.0, "b": 2.0, "c": 3.0},
    )
    md = format_pin_plan_md(plan, run_id="demo")
    assert "## Decisions" in md
    assert "**pin**" in md
    assert "`a`" in md


def test_cli_pin_plan_writes_artifacts(tmp_path):
    import json

    import yaml

    from hornlab_search.cli import main

    runs = tmp_path / "runs"
    rid = "20261031T000000Z-screen-pinplan"
    run = runs / rid
    run.mkdir(parents=True)
    cov = _cov({
        "L_mm": (0.02, 0.01),
        "a_deg": (0.40, 0.10),
        "n": (0.58, 0.12),
    })
    (run / "run.json").write_text(json.dumps({"cma_covariance": cov}), encoding="utf-8")
    (run / "best.json").write_text(json.dumps({
        "params": {"L_mm": 200.0, "a_deg": 45.0, "n": 5.0}, "objective": 1.0, "ok": True,
    }), encoding="utf-8")
    (run / "config.yaml").write_text(yaml.safe_dump({
        "seed_params": {"L_mm": 180.0, "a_deg": 40.0, "n": 4.0},
        "bounds": {
            "L_mm": {"lo": 100.0, "hi": 300.0},
            "a_deg": {"lo": 20.0, "hi": 60.0},
            "n": {"lo": 1.0, "hi": 10.0},
        },
    }), encoding="utf-8")
    (run / "search.ndjson").write_text(
        json.dumps({"ok": True, "objective": 2.0,
                    "params": {"L_mm": 180, "a_deg": 40, "n": 4}}) + "\n"
        + json.dumps({"ok": True, "objective": 1.0,
                      "params": {"L_mm": 200, "a_deg": 45, "n": 5}}) + "\n",
        encoding="utf-8",
    )
    out_cfg = tmp_path / "pinned.yaml"
    rc = main(["pin-plan", "--runs-dir", str(runs), "--run", rid,
               "--write-config", str(out_cfg)])
    assert rc == 0
    assert (run / "pin_plan.json").is_file()
    assert (run / "PIN_PLAN.md").is_file()
    plan = json.loads((run / "pin_plan.json").read_text(encoding="utf-8"))
    assert "L_mm" in plan["pin"]
    patched = yaml.safe_load(out_cfg.read_text(encoding="utf-8"))
    assert patched["bounds"]["L_mm"]["search"] is False
    assert patched["bounds"]["L_mm"]["lo"] == 200.0
