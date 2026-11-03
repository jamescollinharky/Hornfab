"""Mesher-gated: OSSE mid_ports inventory (tags {1,2,10}) and ports-absent stability."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from hornlab_search.design.families import to_mesher_config
from hornlab_search.types import Design, MeshSpec
from tests.conftest import requires_mesher


def _osse(**extra):
    # Solana-like OSSE+SF+morph (matches the mesher fork mid_ports golden).
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
        "wall_thickness_mm": 5.0,
        "gcurve_type": 2,
        "gcurve_width_mm": 65.0,
        "gcurve_aspect_ratio": 1.0,
        "gcurve_dist": 0.28,
        "gcurve_rot_deg": 0.0,
        "gcurve_sf_a": 1.38,
        "gcurve_sf_b": 1.44,
        "gcurve_sf_m1": 8.0,
        "gcurve_sf_m2": 8.0,
        "gcurve_sf_n1": 2.15,
        "gcurve_sf_n2": 5.25,
        "gcurve_sf_n3": 3.02,
        "morph_target": 1,
        "morph_width_mm": 353.0,
        "morph_height_mm": 353.0,
        "morph_corner_mm": 14.0,
        "morph_exponent": 4.0,
        "morph_rate": 3.7,
        "morph_fixed": 0.35,
        "morph_allow_shrinkage": 1,
    }
    p.update(extra)
    return Design("OSSE", p)


def _mspec():
    return MeshSpec(
        epw=4.0, f_max_hz=4000.0, quadrants="1",
        max_triangles=80000, allow_large_mesh=True,
    )


def _res():
    return {"throat": 4.0, "mouth": 12.0, "rear": 12.0}


@requires_mesher
def test_mid_ports_absent_mesh_byte_identical(tmp_path):
    import hornlab_mesher as hm

    ms, res = _mspec(), _res()
    a_path = tmp_path / "a.msh"
    b_path = tmp_path / "b.msh"
    cfg_a = to_mesher_config(_osse(), ms, res, a_path)
    cfg_b = to_mesher_config(_osse(), ms, res, b_path)
    assert "mid_ports" not in cfg_a
    hm.build_from_config(cfg_a, a_path)
    hm.build_from_config(cfg_b, b_path)
    assert hashlib.sha256(a_path.read_bytes()).hexdigest() == hashlib.sha256(
        b_path.read_bytes()
    ).hexdigest()


@requires_mesher
def test_mid_ports_on_inventory(tmp_path):
    import hornlab_mesher as hm

    ports = {
        "walls": "tblr",
        "z_frac": 0.35,
        "across_frac": 0.4,
        "port_along_mm": 25.0,
        "slide_mm": 0.0,
    }
    out = tmp_path / "ports.msh"
    cfg = to_mesher_config(_osse(mid_ports=ports), _mspec(), _res(), out)
    assert cfg["mid_ports"] == ports
    result = hm.build_from_config(cfg, out)
    tags = set(result.physical_groups)
    assert tags == {1, 2, 10}
    report = (result.metadata or {}).get("midPorts")
    assert report is not None
    assert int(report["n_port_triangles"]) > 0
    assert len(report["patches"]) == 2
    expected = float(report["expected_area_mm2"])
    got = float(report["port_area_mm2"])
    assert expected > 0.0
    # Fork golden hits ~1%; search-side screen res can land ~1–2% on the same recipe.
    assert abs(got - expected) / expected <= 0.02
