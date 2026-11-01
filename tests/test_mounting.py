"""WP12 (M6): brief ``mounting`` -> mesher enclosure, cache identity, provenance.

The SEARCH-side key is ``brief.mounting`` (plan verbatim: type/depth_mm/margins_mm/edge_mm/
plan). Nothing here invents a mesher key: the emitted section uses the mesher's own
``enclosure.*`` names (``config_builder._enclosure_from_config``) and only the rounded-rectangle
plan (``plan_type=1``), the only one hornlab_mesher builds on closed/reduced domains.

Most tests are pure/offline. The single real build is ``requires_mesher``-gated and small
(quarter R-OSSE at 3 kHz): it proves the plumbing end to end (enclosure tag group, bigger mesh
than the freestanding equivalent, the mesh_meta echo).
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
import yaml

from conftest import EXAMPLES, REPO, requires_mesher
from hornlab_search.config import ConfigError, load_brief, load_config
from hornlab_search.design import families
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build, grid_build, step_build
from hornlab_search.search.evaluate import evaluate, make_context, read_ndjson
from hornlab_search.types import Design, GeometryInvalidError, MeshSpec

#: A normalized block, exactly the shape ``Config.mounting`` stores (full l/t/r/b margins).
MOUNT = {
    "type": "enclosure",
    "depth_mm": 250.0,
    "margins_mm": {"l": 25.0, "t": 30.0, "r": 35.0, "b": 40.0},
    "edge_mm": 12.0,
    "plan": "rounded_rectangle",
}

BRIEF = EXAMPLES / "briefs" / "enclosure_1in.yaml"
CONFIG_1IN = EXAMPLES / "rosse_baseline.yaml"     # 12.7 mm throat: matches the 1-inch briefs


# ------------------------------------------------------------------ helpers


def _brief_body(mounting, **over) -> dict:
    """A complete, driver-fair brief body (mirrors examples/briefs/organic_rollback_1in.yaml)."""
    body = {
        "name": "wp12_mounting",
        "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
        "envelope": {"max_mouth_w_mm": 520.0, "max_mouth_h_mm": 420.0, "max_depth_mm": 260.0},
        "symmetry": "hv",
        "source": {"cap": "auto"},
        "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 700.0,
                   "band_hi_hz": 5500.0, "di_target_db": None, "di_slope_target": 0.0,
                   "z_min": 0.7},
        "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5,
                    "load": 0.5},
    }
    body.update(over)
    if mounting is not None:
        body["mounting"] = mounting
    return body


def _load_brief(tmp_path: Path, mounting, **over) -> dict:
    """Write the YAML exactly like the GUI's ``save_user_brief`` does and load it."""
    p = tmp_path / "wp12_mounting.yaml"
    p.write_text(yaml.safe_dump(_brief_body(mounting, **over), sort_keys=False), encoding="utf-8")
    return load_brief(p)


def _big(cfg):
    """Caps lifted: these tests study meshing/plumbing, not the VRAM budget."""
    return dataclasses.replace(cfg, mesh=dataclasses.replace(
        cfg.mesh, dof_cap_screen=10**6, dof_cap_verify=10**6, dof_cap_final=10**6))


# ------------------------------------------------------------------ (a) brief validation


def test_brief_accepts_the_plan_verbatim_mounting_block(tmp_path):
    raw = _load_brief(tmp_path, {"type": "enclosure", "depth_mm": 250,
                                 "margins_mm": 25, "edge_mm": 18,
                                 "plan": "rounded_rectangle"})
    assert raw["mounting"] == {"type": "enclosure", "depth_mm": 250, "margins_mm": 25,
                               "edge_mm": 18, "plan": "rounded_rectangle"}


def test_brief_mounting_is_normalized_by_load_config(tmp_path):
    body = _brief_body({"type": "enclosure", "depth_mm": 300, "margins_mm": {"l": 30},
                        "edge_mm": 0, "plan": "rounded_rectangle"})
    p = tmp_path / "wp12.yaml"
    p.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    cfg = load_config(CONFIG_1IN, brief=p)
    assert cfg.mounting == {"type": "enclosure", "depth_mm": 300.0,
                            "margins_mm": {"l": 30.0, "t": 25.0, "r": 25.0, "b": 25.0},
                            "edge_mm": 0.0, "plan": "rounded_rectangle"}
    # the normalized block is echoed into raw (config_sha) ...
    assert cfg.raw["mounting"] == cfg.mounting
    # ... and a run directory's own merged config.yaml round-trips to the SAME block
    merged = tmp_path / "merged.yaml"
    merged.write_text(yaml.safe_dump(cfg.raw, sort_keys=False), encoding="utf-8")
    cfg2 = load_config(merged)
    assert cfg2.mounting == cfg.mounting


def test_brief_scalar_margins_broadcast_to_the_four_sides(tmp_path):
    body = _brief_body({"type": "enclosure", "depth_mm": 250, "margins_mm": 40,
                        "edge_mm": 18, "plan": "rounded_rectangle"})
    p = tmp_path / "b.yaml"
    p.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    cfg = load_config(CONFIG_1IN, brief=p)
    assert cfg.mounting["margins_mm"] == {"l": 40.0, "t": 40.0, "r": 40.0, "b": 40.0}


def test_brief_without_mounting_stays_freestanding(tmp_path):
    cfg = load_config(CONFIG_1IN, brief=EXAMPLES / "briefs" / "hifi_90x60_1in.yaml")
    assert cfg.mounting is None and "mounting" not in cfg.raw


@pytest.mark.parametrize("block, match", [
    ({"type": "enclosure", "depth_mm": 250, "bogus": 1}, "unknown key"),
    ({"depth_mm": 250}, "mounting.type"),
    ({"type": "freestanding", "depth_mm": 250}, "mounting.type"),
    ({"type": "enclosure"}, "depth_mm"),                                     # required
    ({"type": "enclosure", "depth_mm": 0}, "mounting.depth_mm"),
    ({"type": "enclosure", "depth_mm": -5}, "mounting.depth_mm"),
    ({"type": "enclosure", "depth_mm": 250, "margins_mm": 0}, "mounting.margins_mm"),
    ({"type": "enclosure", "depth_mm": 250, "margins_mm": {"l": -1}}, "margins_mm.l"),
    ({"type": "enclosure", "depth_mm": 250, "margins_mm": {"x": 10}}, "unknown side"),
    ({"type": "enclosure", "depth_mm": 250, "edge_mm": -1}, "mounting.edge_mm"),
    ({"type": "enclosure", "depth_mm": 250, "plan": "ellipse"}, "mounting.plan"),
    ({"type": "enclosure", "depth_mm": 250, "plan": "superellipse"}, "mounting.plan"),
])
def test_brief_refuses_bad_mounting_blocks(tmp_path, block, match):
    with pytest.raises(ConfigError, match=match):
        _load_brief(tmp_path, block)


# ------------------------------------------------------------------ (b) mcfg translation

ROSSE_SEED = dict(R_mm=150.0, r0_mm=12.7, a_deg=60.0, a0_deg=15.5, k=1.0, q=1.0,
                  exponent=2.0, aspect_ratio=1.0)
MESH = MeshSpec(epw=6.0, f_max_hz=3000.0, quadrants="1", max_triangles=100000)
RES = {"throat": 10.0, "mouth": 20.0, "rear": 20.0}
OUT = Path("out.msh")


def _mcfg(mounting):
    return families.to_mesher_config(Design("R-OSSE", dict(ROSSE_SEED)), MESH, RES, OUT,
                                     mounting=mounting)


def test_mounting_absent_is_the_exact_today_dict():
    expected = {
        "formula": "R-OSSE", "mode": "freestanding",
        "profile": {"R_mm": 150.0, "r0_mm": 12.7, "a_deg": 60.0, "a0_deg": 15.5, "k": 1.0,
                    "q": 1.0},
        "cross_section": {"exponent": 2.0, "aspect_ratio": 1.0},
        "mesh": {"quadrants": "1", "throat_res_mm": 10.0, "mouth_res_mm": 20.0,
                 "rear_res_mm": 20.0, "max_triangles": 100000, "allow_large_mesh": False,
                 "scale_to_metres": True},
        "output": {"path": "out.msh"},
    }
    assert _mcfg(None) == expected
    assert _mcfg(None) == families.to_mesher_config(  # explicit default arg identical
        Design("R-OSSE", dict(ROSSE_SEED)), MESH, RES, OUT)


def test_mounting_flips_mode_and_emits_only_the_meshers_own_enclosure_keys():
    cfg = _mcfg(MOUNT)
    assert cfg["mode"] == "enclosure"
    assert cfg["enclosure"] == {
        "depth_mm": 250.0,
        "space_l_mm": 25.0,          # margins_mm l/t/r/b -> the mesher's space_*_mm names
        "space_t_mm": 30.0,
        "space_r_mm": 35.0,
        "space_b_mm": 40.0,
        "edge_mm": 12.0,
        "plan_type": 1,              # rounded_rectangle is the ONLY token
    }
    # the plan's key list is the contract: no plan_n / depth_margin_mm / front/back sizes
    assert set(cfg["enclosure"]) == {"depth_mm", "space_l_mm", "space_t_mm", "space_r_mm",
                                     "space_b_mm", "edge_mm", "plan_type"}
    # everything except the top-level mode flip + enclosure section is untouched
    base = _mcfg(None)
    assert {k: v for k, v in cfg.items() if k not in ("mode", "enclosure")} == \
        {k: v for k, v in base.items() if k != "mode"}
    # the enclosure section is a TOP-LEVEL sibling of "mesh" (never nested under it)
    assert "enclosure" not in cfg["mesh"]


# ------------------------------------------------------------------ (c) cache identity

def test_mesh_cache_key_separates_mounting_and_is_stable():
    cfg = load_config(CONFIG_1IN)
    design = DesignSpace.from_config(cfg).seed
    free = build.mesh_cache_key(design, MESH, cfg)
    enc = build.mesh_cache_key(design, MESH, dataclasses.replace(cfg, mounting=MOUNT))
    again = build.mesh_cache_key(design, MESH, dataclasses.replace(cfg, mounting=dict(MOUNT)))
    assert enc != free
    assert enc == again
    assert free == f"{design.hash()}-{MESH.hash()}"            # absent = today's exact string
    assert enc == f"{free}-{families.mounting_key(MOUNT)}"
    # a different block is a different key (depth is part of the identity)
    other = dict(MOUNT, depth_mm=300.0)
    assert build.mesh_cache_key(design, MESH, dataclasses.replace(cfg, mounting=other)) != enc


# ------------------------------------------------------------------ (d) GRID route

@requires_mesher
def test_grid_enclosure_drops_outer_points_and_keeps_symmetry(tmp_path, monkeypatch):
    from hornlab_search.constants import C_AIR
    from hornlab_search.design.generators import grid as G

    brief = {"driver": {"exit_radius_mm": 5.0, "exit_angle_deg": 8.0},
             "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0,
                          "max_depth_mm": 220.0}}
    spec = {"name": "grid", "profile_h": {"type": "conical"}, "profile_v": "same",
            "n_phi": 13, "n_s": 32, "max_wall_deg": 80.0, "wall_thickness_mm": 3.0}
    knobs = {"L_mm": 60.0, "h_rm_mm": 25.0}
    inner, meta = G.grid_points(spec, knobs, brief)

    # pure resolution checks (no mesher): enclosure -> no outer shell, explicit outer refused
    _, outer, _, _, _ = grid_build._resolve_grid({"inner_points": inner, "meta": meta},
                                                 enclosure=MOUNT)
    assert outer is None
    with pytest.raises(ValueError, match="enclosure cannot be combined with outer_points"):
        grid_build._resolve_grid({"inner_points": inner, "meta": meta,
                                  "outer_points": inner.copy()}, enclosure=MOUNT)

    ms = MeshSpec(epw=6.0, f_max_hz=1000.0 * C_AIR / (6.0 * 12.0), quadrants="1",
                  max_triangles=10**6)
    cfg = _big(load_config(CONFIG_1IN))
    captured = {}

    import hornlab_mesher.mesher as mesher
    real = mesher.build_mesh_with_info

    def spy(geometry, density, **kwargs):
        captured["geometry"] = geometry
        return real(geometry, density, **kwargs)

    monkeypatch.setattr(mesher, "build_mesh_with_info", spy)
    r = grid_build.build_grid_mesh({"inner_points": inner, "meta": meta,
                                    "wall_thickness_mm": 3.0},
                                   ms, tmp_path / "mesh.msh", cfg, mounting=MOUNT)
    geom = captured["geometry"]
    from hornlab_mesher.geometry import PointGridBuildMode
    assert geom.build_mode is PointGridBuildMode.ENCLOSURE
    assert geom.outer_points is None                      # structural guard: NO freestanding shell
    assert geom.closed is False and geom.symmetry_planes == ("x", "y")
    assert geom.enclosure is not None
    assert geom.enclosure.depth_mm == 250.0
    assert (geom.enclosure.space_l_mm, geom.enclosure.space_t_mm,
            geom.enclosure.space_r_mm, geom.enclosure.space_b_mm) == (25.0, 30.0, 35.0, 40.0)
    assert geom.enclosure.plan_type == 1 and geom.enclosure.edge_type == 1
    summary = build.read_msh_summary(r.path)
    assert summary["tags"].get(3, 0) > 0                  # SD2G0 enclosure wall
    assert summary["tag_names"][3] == "SD2G0"


@requires_mesher
def test_grid_route_and_mesher_agree_that_enclosure_excludes_other_topologies():
    """Parity with the mesher's own geometry guard (geometry.py:307-320)."""
    import numpy as np
    from hornlab_mesher.geometry import HornEnclosure, PointGridHornGeometry

    enc = families.enclosure_object(MOUNT)
    assert isinstance(enc, HornEnclosure)
    grid = np.zeros((3, 2, 3), dtype=float)
    grid[:, :, 0] = np.linspace(1.0, 5.0, 2)              # non-degenerate x radius
    with pytest.raises(ValueError, match="infinite_baffle and enclosure"):
        PointGridHornGeometry(inner_points=grid, closed=False, enclosure=enc,
                              infinite_baffle=True)
    with pytest.raises(ValueError, match="enclosure cannot be combined with outer_points"):
        PointGridHornGeometry(inner_points=grid, closed=False, enclosure=enc,
                              outer_points=grid.copy())


# ------------------------------------------------------------------ (e) STEP refusal

def test_cad_design_with_mounting_is_refused_cleanly(tmp_path):
    recipe = {"tool": "multicell", "n_h": 2, "n_v": 2, "alpha_total_deg": 60.0,
              "beta_total_deg": 60.0, "length_mm": 120.0, "z_s_mm": 30.0,
              "r_throat_mm": 12.7, "septum_mm": 2.0, "throat_wall_mm": 3.0, "flare_hz": 500.0}
    cfg = dataclasses.replace(load_config(CONFIG_1IN), mounting=MOUNT)
    ms = MeshSpec(epw=10.0, f_max_hz=2000.0, quadrants="1234", max_triangles=10**6)
    with pytest.raises(GeometryInvalidError, match="CAD \\+ enclosure is not implemented"):
        step_build.build_mesh_from_cad(recipe, ms, cfg, tmp_path / "cad", mode="screen")
    # the refusal fires BEFORE any mesher/CAD import or file write
    assert not (tmp_path / "cad").exists()


# ------------------------------------------------------------------ (f) provenance / evaluate keys

@pytest.fixture
def fake_cfg(smoke_cfg):
    from test_search_support import fast_cfg
    return fast_cfg(smoke_cfg)


def _evaluate(cfg, tmp_path, monkeypatch, ctx):
    from test_search_support import SyntheticBackend, install_fakes
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    space = DesignSpace.from_config(cfg)
    ndjson = tmp_path / "run" / "search.ndjson"
    from hornlab_search.dataset.store import DatasetStore
    store = DatasetStore(tmp_path / "ds")
    ev = evaluate(space.seed, space, cfg, "screen", tmp_path / "run", store, be, ctx=ctx)
    return ev, store, read_ndjson(ndjson)


class _MustNotBeCalled:
    """A backend that proves a cache/memo hit never reaches it."""
    name = "must-not-be-called"

    def solve(self, *a, **k):                       # pragma: no cover - a hit never calls this
        raise AssertionError("backend was called for a memo/cache hit")

    solve_traced = solve


def test_mounting_rides_in_the_evaluate_key_row_and_dataset_provenance(
        fake_cfg, tmp_path, monkeypatch):
    from test_search_support import LIBS
    cfg = dataclasses.replace(fake_cfg, mounting=MOUNT)
    ctx = make_context(cfg, None, lib_shas=LIBS,
                       ndjson=tmp_path / "run" / "search.ndjson")
    ev, store, rows = _evaluate(cfg, tmp_path, monkeypatch, ctx)
    (row,) = rows
    assert row["mounting"] == MOUNT
    assert row["key"] == f"{ev.design_hash}-{ev.mesh_hash}-{ev.solve_hash}-" \
                         f"{families.mounting_key(MOUNT)}"
    (meta, _arrays) = next(store.iter_records(with_arrays=True))
    assert meta["provenance"]["mounting"] == MOUNT

    # the in-run memo uses the SAME key: a second evaluation of the seed is a known hit
    space = DesignSpace.from_config(cfg)
    ev2 = evaluate(space.seed, space, cfg, "screen", tmp_path / "run", store,
                   _MustNotBeCalled(), ctx=ctx)
    assert ev2.cached and ctx.counters["cache_hits_run"] == 1
    assert len(read_ndjson(tmp_path / "run" / "search.ndjson")) == 1


def test_absent_mounting_leaves_the_row_and_key_byte_identical(fake_cfg, tmp_path, monkeypatch):
    from test_search_support import LIBS
    ctx = make_context(fake_cfg, None, lib_shas=LIBS,
                       ndjson=tmp_path / "run" / "search.ndjson")
    ev, store, rows = _evaluate(fake_cfg, tmp_path, monkeypatch, ctx)
    (row,) = rows
    assert "mounting" not in row
    assert row["key"] == f"{ev.design_hash}-{ev.mesh_hash}-{ev.solve_hash}"
    assert "-mnt-" not in row["key"]
    (meta, _arrays) = next(store.iter_records(with_arrays=True))
    assert "mounting" not in (meta.get("provenance") or {})


# ------------------------------------------------------------------ (g) GUI save path / example brief


def test_save_user_brief_body_loads_clean(tmp_path):
    """``gui.data.save_user_brief`` validates through ``load_brief``; a mounting body now loads."""
    body = _brief_body({"type": "enclosure", "depth_mm": 250, "margins_mm": 25,
                        "edge_mm": 18, "plan": "rounded_rectangle"})
    body["name"] = "wp12_gui_brief"
    p = tmp_path / "wp12_gui_brief.yaml"
    p.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    raw = load_brief(p)
    assert raw["mounting"]["type"] == "enclosure"


def test_example_enclosure_brief_loads_and_normalizes():
    raw = load_brief(BRIEF)
    assert raw["mounting"] == {"type": "enclosure", "depth_mm": 250.0, "margins_mm": 25.0,
                               "edge_mm": 18.0, "plan": "rounded_rectangle"}
    cfg = load_config(CONFIG_1IN, brief=BRIEF)
    assert cfg.mounting == {"type": "enclosure", "depth_mm": 250.0,
                            "margins_mm": {"l": 25.0, "t": 25.0, "r": 25.0, "b": 25.0},
                            "edge_mm": 18.0, "plan": "rounded_rectangle"}


# ------------------------------------------------------------------ (h) ONE real enclosure build


@requires_mesher
def test_enclosure_mesh_build_carries_the_enclosure_group_and_meta_echo(tmp_path):
    """One small quarter enclosure build (offline CPU mesher) + its freestanding twin."""
    cfg = _big(load_config(CONFIG_1IN, brief=BRIEF))
    design = DesignSpace.from_config(cfg).seed
    ms = MeshSpec(epw=6.0, f_max_hz=3000.0, quadrants="1", max_triangles=10**6)
    r_enc = build.build_mesh(design, ms, cfg, tmp_path / "enc", mode="screen")
    r_free = build.build_mesh(design, ms, dataclasses.replace(cfg, mounting=None),
                              tmp_path / "free", mode="screen")

    summary, _xyz, _tri = build.read_msh_summary(r_enc.path, return_arrays=True)
    assert summary["tags"].get(3, 0) > 0 and summary["tag_names"][3] == "SD2G0"
    assert summary["tags"].get(2, 0) > 0 and summary["tag_names"][2] == "SD1D1001"
    assert summary["tags"].get(1, 0) > 0
    assert r_enc.n_triangles > r_free.n_triangles       # measured at 3 kHz on the pin
    assert r_enc.quadrants == "1"

    meta = json.loads((tmp_path / "enc" / "mesh_meta.json").read_text(encoding="utf-8"))
    assert meta["mesher_config"]["mode"] == "enclosure"
    assert meta["mounting"]["normalized"] == cfg.mounting
    assert meta["mounting"]["mesher"] == families.enclosure_section(cfg.mounting)
    assert meta["mounting"]["n_triangles"] == r_enc.n_triangles
    # the freestanding twin's meta has no mounting echo (old metas stay byte-identical)
    free_meta = json.loads((tmp_path / "free" / "mesh_meta.json").read_text(encoding="utf-8"))
    assert "mounting" not in free_meta
    print(f"\nWP12 enclosure build: n_triangles={r_enc.n_triangles} "
          f"(freestanding {r_free.n_triangles}), tags={summary['tags']}, "
          f"bbox={r_enc.bbox_m}")
