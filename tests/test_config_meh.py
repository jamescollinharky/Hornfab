"""The C10 ``meh:`` brief block (M6).

Offline, CPU only.  The contracts pinned here:

* the exact C10 example validates and is normalised (numbers to float, tags/count to int, every
  nested key checked so a YAML typo is never silent);
* every range from the M6 task refuses outside its limit: hp 60-250 Hz, xo lo < hi in 300-3000,
  orders a subset of {2, 4, 8}, delay -3..3 ms, fill 0..0.9, rear 0.2..20 L, amp 5..200 V RMS,
  port air 5..40 m/s, boost 0..12 dB, spl_target sorted with dB 80..140;
* driver stems are checked against ``examples/drivers/`` with the C8 kind; a MISSING file is a
  warning (M1 runs in parallel) and a wrong kind is refused;
* a brief carrying the block loads through ``load_brief`` unchanged when it has no block, and an
  embedded run-directory brief is re-validated.
"""
from __future__ import annotations

import copy

import pytest
import yaml

from hornlab_search.config import ConfigError, _validate_meh_block, load_brief, load_config


def _c10():
    return {
        "groups": {
            "cd": {"tag": 2, "drivers": ["faitalpro_hf1440"]},
            "mid": {"tag": 10, "count": 2, "drivers": ["bc_6ndl38", "faitalpro_6pr160"]},
        },
        "hp_hz": 120,
        "xo_hz": {"lo": 650, "hi": 1100},
        "xo_orders": [2, 4],
        "delay_ms": {"lo": -1.0, "hi": 2.0},
        "v_front_fill": {"lo": 0.0, "hi": 0.7},
        "v_rear_l": {"lo": 0.8, "hi": 6.0},
        "amp_v_rms": 40.0,
        "port_air_mps_max": 17.0,
        "max_boost_db": 6.0,
        "spl_target": [[120, 114], [250, 120], [12000, 120]],
        "listening_window": {"h_deg": [0, 10, 20, 30], "v_deg": [10]},
    }


def _drivers(tmp_path, block):
    """Create a driver YAML for every stem in the block with its C8 kind."""
    root = tmp_path / "drivers"
    root.mkdir(exist_ok=True)
    kinds = {"cd": "compression_meh", "mid": "cone"}
    for group, kind in kinds.items():
        for stem in block["groups"][group]["drivers"]:
            (root / f"{stem}.yaml").write_text(
                yaml.safe_dump({"name": stem, "kind": kind}), encoding="utf-8")
    return root


def _valid(tmp_path):
    block = _c10()
    return block, _drivers(tmp_path, block)


def _fails(block, match, drivers_dir=None):
    with pytest.raises(ConfigError, match=match):
        _validate_meh_block(block, "brief.yaml:meh", drivers_dir=drivers_dir)


# ------------------------------------------------------------------ the contract example

def test_c10_example_validates_and_normalises(tmp_path):
    block, drivers = _valid(tmp_path)
    out = _validate_meh_block(block, "brief.yaml:meh", drivers_dir=drivers)
    assert out["groups"]["cd"] == {"tag": 2, "drivers": ["faitalpro_hf1440"]}
    assert out["groups"]["mid"] == {"tag": 10, "count": 2,
                                    "drivers": ["bc_6ndl38", "faitalpro_6pr160"]}
    assert out["hp_hz"] == 120.0 and isinstance(out["hp_hz"], float)
    assert out["xo_hz"] == {"lo": 650.0, "hi": 1100.0}
    assert out["xo_orders"] == [2, 4]
    assert out["delay_ms"] == {"lo": -1.0, "hi": 2.0}
    assert out["v_front_fill"] == {"lo": 0.0, "hi": 0.7}
    assert out["v_rear_l"] == {"lo": 0.8, "hi": 6.0}
    assert out["amp_v_rms"] == 40.0 and out["port_air_mps_max"] == 17.0
    assert out["max_boost_db"] == 6.0
    assert out["spl_target"] == [[120.0, 114.0], [250.0, 120.0], [12000.0, 120.0]]
    assert out["listening_window"] == {"h_deg": [0.0, 10.0, 20.0, 30.0], "v_deg": [10.0]}


def test_missing_driver_files_warn_and_do_not_fail(tmp_path, caplog):
    block = _c10()
    out = _validate_meh_block(block, "brief.yaml:meh", drivers_dir=tmp_path / "absent")
    assert out["groups"]["cd"]["drivers"] == ["faitalpro_hf1440"]
    assert "M1 has not landed" in caplog.text


def test_driver_kind_must_match_the_group(tmp_path):
    block, drivers = _valid(tmp_path)
    (drivers / "bc_6ndl38.yaml").write_text(
        yaml.safe_dump({"name": "bc_6ndl38", "kind": "compression_meh"}), encoding="utf-8")
    _fails(block, r"expected 'cone'", drivers)


def test_unreadable_driver_file_refuses(tmp_path):
    block, drivers = _valid(tmp_path)
    (drivers / "bc_6ndl38.yaml").write_text("kind: [unclosed", encoding="utf-8")
    _fails(block, "cannot read driver file", drivers)


# ------------------------------------------------------------------ exact keys

def test_unknown_and_missing_top_level_keys_refuse(tmp_path):
    block, drivers = _valid(tmp_path)
    block["not_a_key"] = 1
    _fails(block, r"unknown key\(s\)", drivers)
    block, drivers = _valid(tmp_path)
    del block["hp_hz"]
    _fails(block, r"missing required key", drivers)


def test_groups_exact_keys_tags_and_counts(tmp_path):
    block, drivers = _valid(tmp_path)
    block["groups"]["cd"]["tag"] = 3
    _fails(block, "tag must be 2", drivers)
    block, drivers = _valid(tmp_path)
    block["groups"]["mid"]["tag"] = 11
    _fails(block, "tag must be 10", drivers)
    block, drivers = _valid(tmp_path)
    block["groups"]["cd"]["drivers"] = []
    _fails(block, "non-empty list", drivers)
    block, drivers = _valid(tmp_path)
    block["groups"]["cd"]["drivers"] = ["a", "b"]
    _fails(block, "exactly one CD file", drivers)
    block, drivers = _valid(tmp_path)
    block["groups"]["mid"]["count"] = 0
    _fails(block, "count must be an integer >= 1", drivers)
    block, drivers = _valid(tmp_path)
    block["groups"]["mid"]["bogus"] = 1
    _fails(block, r"unknown key\(s\)", drivers)


# ------------------------------------------------------------------ ranges

@pytest.mark.parametrize("value,match", [
    (59.0, "hp_hz"), (251.0, "hp_hz"), (True, "hp_hz"), ("120", "hp_hz"),
])
def test_hp_range(tmp_path, value, match):
    block, drivers = _valid(tmp_path)
    block["hp_hz"] = value
    _fails(block, match, drivers)


@pytest.mark.parametrize("xo,match", [
    ({"lo": 299.0, "hi": 1000.0}, "xo_hz.lo"),
    ({"lo": 1000.0, "hi": 3001.0}, "xo_hz.hi"),
    ({"lo": 1100.0, "hi": 1100.0}, "lo < hi"),
    ({"lo": 1200.0, "hi": 1000.0}, "lo < hi"),
    ({"lo": 650.0}, r"missing required key 'hi'"),
    ({"lo": 650.0, "hi": 1100.0, "mid": 900.0}, "unknown key"),
])
def test_xo_range(tmp_path, xo, match):
    block, drivers = _valid(tmp_path)
    block["xo_hz"] = xo
    _fails(block, match, drivers)


@pytest.mark.parametrize("orders,match", [
    ([], "non-empty list"), ([3], r"subset of \[2, 4, 8\]"), ([2, 2], "duplicate"),
    ([2, 4, 8, 16], "subset"), ([2.0], "subset"), ([True], "subset"),
])
def test_xo_orders(tmp_path, orders, match):
    block, drivers = _valid(tmp_path)
    block["xo_orders"] = orders
    _fails(block, match, drivers)


@pytest.mark.parametrize("key,sub,value,match", [
    ("delay_ms", "lo", -3.01, "delay_ms.lo"), ("delay_ms", "hi", 3.01, "delay_ms.hi"),
    ("v_front_fill", "lo", -0.01, "v_front_fill.lo"), ("v_front_fill", "hi", 0.91, "v_front_fill.hi"),
    ("v_rear_l", "lo", 0.19, "v_rear_l.lo"), ("v_rear_l", "hi", 20.1, "v_rear_l.hi"),
])
def test_range_blocks(tmp_path, key, sub, value, match):
    block, drivers = _valid(tmp_path)
    block[key][sub] = value
    _fails(block, match, drivers)


@pytest.mark.parametrize("key,value,match", [
    ("amp_v_rms", 4.9, "amp_v_rms"), ("amp_v_rms", 200.1, "amp_v_rms"),
    ("port_air_mps_max", 4.9, "port_air_mps_max"),
    ("port_air_mps_max", 40.1, "port_air_mps_max"),
    ("max_boost_db", -0.1, "max_boost_db"), ("max_boost_db", 12.1, "max_boost_db"),
])
def test_scalar_ranges(tmp_path, key, value, match):
    block, drivers = _valid(tmp_path)
    block[key] = value
    _fails(block, match, drivers)


@pytest.mark.parametrize("spl,match", [
    ([[120, 114]], "at least two"),
    ([[120, 79], [1000, 120]], r"spl_target\[0\]\[1\]"),
    ([[1200, 120], [1000, 120]], "strictly increasing"),
    ([[1000, 120], [1200, 1200]], r"spl_target\[1\]\[1\]"),
    ([[120, 120, 1], [1000, 120]], "Hz, dB"),
])
def test_spl_target(tmp_path, spl, match):
    block, drivers = _valid(tmp_path)
    block["spl_target"] = spl
    _fails(block, match, drivers)


def test_listening_window(tmp_path):
    block, drivers = _valid(tmp_path)
    block["listening_window"] = {"h_deg": []}
    _fails(block, "h_deg", drivers)
    block, drivers = _valid(tmp_path)
    block["listening_window"] = {"h_deg": [0], "v_deg": [10], "diag_deg": [45]}
    _fails(block, r"unknown key\(s\)", drivers)
    block, drivers = _valid(tmp_path)
    block["listening_window"] = {"h_deg": [0, "x"], "v_deg": [10]}
    _fails(block, "finite number", drivers)


# ------------------------------------------------------------------ brief plumbing

def _brief(block=None):
    return {
        "name": "meh_test", "description": "meh",
        "driver": {"exit_radius_mm": 17.9, "exit_angle_deg": 0.0},
        "envelope": {"max_mouth_w_mm": 370.0, "max_mouth_h_mm": 370.0, "max_depth_mm": 380.0},
        "symmetry": "hv", "source": {"cap": "auto"},
        "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 120.0,
                   "band_hi_hz": 12000.0, "di_target_db": None, "di_slope_target": 0.0,
                   "z_min": 0.0, "f0_hz": 850.0},
        "weights": {"cov": 1.0}, **({} if block is None else {"meh": block}),
    }


def test_load_brief_accepts_and_normalises_the_block(tmp_path):
    block, _drivers_dir = _valid(tmp_path)
    path = tmp_path / "brief.yaml"
    path.write_text(yaml.safe_dump(_brief(block)), encoding="utf-8")
    brief = load_brief(path)
    assert brief["meh"]["xo_orders"] == [2, 4]
    assert brief["meh"]["hp_hz"] == 120.0


def test_load_brief_without_the_block_is_unchanged(tmp_path):
    path = tmp_path / "brief.yaml"
    path.write_text(yaml.safe_dump(_brief(None)), encoding="utf-8")
    brief = load_brief(path)
    assert "meh" not in brief


def test_embedded_brief_is_revalidated(tmp_path):
    """A run directory's merged brief goes through the same validator, so a bad block refuses."""
    block, _drivers_dir = _valid(tmp_path)
    brief = _brief(block)
    cfg = {
        "name": "run", "family": "FREEFORM", "brief": brief,
        "seed_params": {}, "bounds": {},
        "target": dict(brief["target"]), "weights": dict(brief["weights"]),
        "mesh": {"epw": 8.0, "quadrants": "1", "dof_cap_screen": 5000, "dof_cap_verify": 7000,
                 "dof_cap_final": 8900, "dof_per_triangle": 0.51},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73, "balloon": True,
                  "balloon_points_screen": 512, "balloon_points_verify": 1024,
                  "gmres_tol": 1.0e-05, "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 10,
                   "popsize": None, "tolfun": 0.001},
    }
    path = tmp_path / "run.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    loaded = load_config(path)
    assert loaded.brief is not None
    assert loaded.brief["meh"] == _validate_meh_block(block, "x")

    bad = copy.deepcopy(cfg)
    bad["brief"]["meh"]["hp_hz"] = 10.0
    path.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(ConfigError, match="hp_hz"):
        load_config(path)
