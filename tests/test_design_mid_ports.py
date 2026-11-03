"""OSSE mid_ports opt-in: round-trip through families.to_mesher_config; absent = stable."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from hornlab_search.design.families import to_mesher_config, validate
from hornlab_search.types import Design, GeometryInvalidError, MeshSpec


def _osse_seed(**extra):
    p = {
        "r0_mm": 12.7,
        "a0_deg": 0.0,
        "L_mm": 140.0,
        "a_deg": 45.0,
        "n": 4.95,
        "s": 1.17,
        "q": 0.80,
        "k": 2.33,
        "exponent": 2.0,
        "aspect_ratio": 1.0,
    }
    p.update(extra)
    return Design("OSSE", p)


def _mspec():
    return MeshSpec(
        epw=6.0, f_max_hz=8000.0, quadrants="1",
        max_triangles=12000, allow_large_mesh=False,
    )


def _res():
    return {"throat": 6.0, "mouth": 18.0, "rear": 18.0}


def test_mid_ports_absent_config_has_no_block(tmp_path):
    cfg = to_mesher_config(_osse_seed(), _mspec(), _res(), tmp_path / "m.msh")
    assert "mid_ports" not in cfg
    assert "mid_ports" not in cfg.get("profile", {})
    assert "mid_ports" not in cfg.get("mesh", {})


def test_mid_ports_round_trip(tmp_path):
    ports = {
        "walls": "tblr",
        "z_frac": 0.35,
        "across_frac": 0.4,
        "port_along_mm": 25.0,
        "slide_mm": 30.0,
    }
    d = _osse_seed(mid_ports=ports)
    validate(d)
    cfg = to_mesher_config(d, _mspec(), _res(), tmp_path / "m.msh")
    assert cfg["mid_ports"] == ports
    # Must not leak into profile / morph sections.
    assert "mid_ports" not in cfg.get("profile", {})
    assert "walls" not in cfg.get("profile", {})


def test_mid_ports_absent_hash_stable_vs_explicit_omit(tmp_path):
    out = tmp_path / "same.msh"
    a = to_mesher_config(_osse_seed(), _mspec(), _res(), out)
    b = to_mesher_config(_osse_seed(), _mspec(), _res(), out)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert "mid_ports" not in a


def test_mid_ports_rejects_bad_walls():
    with pytest.raises(GeometryInvalidError, match="mid_ports.walls"):
        validate(_osse_seed(mid_ports={
            "walls": "xyz", "z_frac": 0.3, "across_frac": 0.4, "port_along_mm": 20.0,
        }))


def test_mid_ports_rejects_missing_required():
    with pytest.raises(GeometryInvalidError, match="mid_ports.z_frac"):
        validate(_osse_seed(mid_ports={
            "walls": "tb", "across_frac": 0.4, "port_along_mm": 20.0,
        }))
