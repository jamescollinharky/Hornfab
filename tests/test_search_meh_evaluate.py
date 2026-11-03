"""M7: the MEH branch of ``search/evaluate.py`` against a fake mesh + fake solver.

No BEM solve, no Julia, no GPU. The mesh is a synthetic ``MeshResult`` plus the
``mesh_meta.json`` the M5 CAD route writes (recipe + ``derived()``); the backend returns a
contract-shaped two-channel ``Response`` (CD tag 2, mid tag 10, symmetric impedance matrix).
That exercises the REAL branch: source tags on the solve spec, M4's inner network optimiser,
synthesis, metrics on the synthesised response, objective v5 and the dataset record.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import load_config, solve_spec
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import step_build
from hornlab_search.search import evaluate as evmod
from hornlab_search.types import MeshResult, Response, SolveOutcome

T2_BRIEF = EXAMPLES / "briefs" / "meh_2026-10-30" / "meh_home_90x60_t2.yaml"
T2_CONFIG = EXAMPLES / "typologies" / "meh_2026-10-30" / "meh_t2a.yaml"

#: A complete provenance map: build_record/validate_record requires all five keys.
LIB_SHAS = {k: "0" * 40 for k in
            ("hornlab_mesher", "hornlab_beat_bem", "hornlab_bempp_bem", "hornlab_plots",
             "hornlab_search")}


# ------------------------------------------------------------------ fake mesh / solver


def _write_fake_mesh(design, out_dir: Path) -> MeshResult:
    out = Path(out_dir)
    (out / "cad").mkdir(parents=True, exist_ok=True)
    recipe = design.params["cad"]
    tool = step_build.load_cad_tool(tool=step_build.MEH_TOOL)
    derived = tool.derived(recipe)
    meta = {
        "summary": {"area_m2": 0.2, "tags": {"1": 100, "2": 10, "10": 10},
                    "n_triangles": 2400},
        "cad": {
            "tool": "tools/cad/meh.py", "tool_sha256": "x", "step_sha256": "y",
            "recipe": recipe, "derived": derived,
            "face_inventory": {"driver": 1, "entry_mid": 1, "wall": 25},
        },
    }
    (out / "mesh_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return MeshResult(path=str(out / "mesh.msh"), n_triangles=2400, n_dof=1234,
                      quadrants="1", symmetry_plane="yz+xz",
                      res_mm={"throat": 3.0, "mouth": 6.0, "rear": 6.0},
                      bbox_m=(0.0, 0.0, 0.0, 0.2032, 0.2032, 0.38), seconds=0.01)


def _fake_response(freqs) -> Response:
    """Two channels with different levels + a symmetric 2x2 impedance matrix (C4/C5)."""
    freqs = np.asarray(freqs, dtype=float)
    nf = freqs.size
    angles = np.linspace(-90.0, 90.0, 73)
    cut = 90.0 - 0.002 * angles ** 2
    spl = np.tile(cut, (nf, 1))
    cp = np.zeros((nf, 2, 2, angles.size), dtype=complex)
    for c, _level in enumerate((1.0, 0.7)):
        mag = 20e-6 * 10 ** ((spl + 20.0 * c) / 20.0)
        cp[:, c, :, :] = mag[:, None, :] * np.exp(1j * 0.1 * c)
    z = np.zeros((nf, 2, 2), dtype=complex)
    z[:, 0, 0] = 1.0 + 0.1j
    z[:, 1, 1] = 1.2 + 0.2j
    z[:, 0, 1] = z[:, 1, 0] = 0.05 + 0.01j
    return Response(
        freqs_hz=freqs, h_angles_deg=angles, v_angles_deg=angles.copy(),
        spl_h_db=spl, spl_v_db=spl.copy(), balloon_dirs=None, spl_balloon_db=None,
        z_throat=np.full(nf, np.nan), backend="fake", n_dof=1234, meta={},
        channel_tags=(2, 10), channel_pressure=cp, channel_sphere_pressure=None,
        impedance_matrix=z, tag_areas_m2={2: 1e-3, 10: 2e-3})


class FakeBackend:
    """Returns the synthetic two-channel response; counts real solve requests."""

    name = "fake"

    def __init__(self):
        self.calls = 0
        self.specs = []

    def solve(self, mesh, spec):
        self.calls += 1
        self.specs.append(spec)
        assert list((spec.extra or {}).get("source_tags") or []) == [2, 10]
        return SolveOutcome(True, _fake_response(spec.freqs_hz), 0.02, None)


# ------------------------------------------------------------------ temp config helper


def _temp_config(tmp_path: Path, *, brief_changes=None, name="cfg") -> Path:
    brief = yaml.safe_load(T2_BRIEF.read_text(encoding="utf-8"))
    if brief_changes is not None:
        brief_changes(brief)
    bp = tmp_path / f"{name}_brief.yaml"
    bp.write_text(yaml.safe_dump(brief, sort_keys=False), encoding="utf-8")
    raw = yaml.safe_load(T2_CONFIG.read_text(encoding="utf-8"))
    raw["brief_file"] = str(bp)
    cp = tmp_path / f"{name}.yaml"
    cp.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return cp


def _one_candidate(brief):
    """One CD, one mid, one crossover order: the end-to-end unit test stays cheap."""
    brief["meh"]["groups"]["mid"]["drivers"] = ["bc_6ndl38"]
    brief["meh"]["xo_orders"] = [2]


def _meh_setup(tmp_path, monkeypatch):
    monkeypatch.setattr(evmod, "build_mesh", lambda design, mspec, cfg, out_dir, **kw:
                        _write_fake_mesh(design, out_dir))
    cfg = load_config(_temp_config(tmp_path, brief_changes=_one_candidate))
    space = DesignSpace.from_config(cfg)
    return cfg, space, space.seed


# ------------------------------------------------------------------ tests


def test_meh_evaluate_returns_finite_j_and_a_record(tmp_path, monkeypatch):
    cfg, space, design = _meh_setup(tmp_path, monkeypatch)
    store = DatasetStore(tmp_path / "dataset")
    ctx = evmod.make_context(cfg, store=store, cache_dir=tmp_path / "cache", lib_shas=LIB_SHAS)
    ctx.write_ndjson = False
    backend = FakeBackend()

    ev = evmod.evaluate(design, space, cfg, "screen", tmp_path / "run", store, backend, ctx=ctx)

    assert ev.error == "", ev.error
    assert np.isfinite(ev.objective)
    assert backend.calls == 1
    # C11: every v5 key is present, the four system terms included.
    assert {"lw_resid", "notch", "xo_lob", "headroom", "total"} <= set(ev.terms)
    assert np.isfinite(ev.terms["total"])
    assert all(np.isfinite(ev.terms[k]) for k in ("lw_resid", "notch", "xo_lob", "headroom"))

    # The Evaluation carries the BEM response (per-channel arrays), not the synthesised one.
    assert ev.outcome is not None
    resp = ev.outcome.response
    assert resp is not None
    assert resp.channel_tags == (2, 10)
    assert resp.channel_pressure is not None
    assert resp.channel_pressure.shape[1] == 2
    assert resp.impedance_matrix is not None
    assert resp.impedance_matrix.shape[1:] == (2, 2)

    meta, arrays = store.read(0, 0)
    assert meta["ok"] is True
    assert meta["objective_version"] == 5
    assert meta["channel_tags"] == [2, 10]
    assert set(arrays) >= {"channel_pressure", "impedance_matrix", "freqs_hz"}
    assert "channel_pressure" in arrays and arrays["channel_pressure"].shape[1] == 2
    # C12: the chosen network + the CAD layout the inner optimiser consumed.
    assert meta["network_solution"]["cd_stem"] == "faitalpro_hf1440"
    assert meta["network_solution"]["mid_stem"] == "bc_6ndl38"
    assert meta["network_solution"]["xo_order"] == 2
    assert meta["provenance"]["meh"]["layout"]["derived"]["port_area_mm2"] > 0


def test_rescore_with_another_driver_and_hp_needs_no_new_solve(tmp_path, monkeypatch):
    cfg, space, design = _meh_setup(tmp_path, monkeypatch)
    cache = tmp_path / "cache"
    backend = FakeBackend()

    ctx1 = evmod.make_context(cfg, cache_dir=cache, lib_shas=LIB_SHAS)
    ctx1.write_ndjson = False
    ev1 = evmod.evaluate(design, space, cfg, "screen", tmp_path / "run1", None, backend, ctx=ctx1)
    assert ev1.error == "", ev1.error
    assert backend.calls == 1

    def other_brief(brief):
        _one_candidate(brief)
        brief["meh"]["groups"]["mid"]["drivers"] = ["faitalpro_6pr160"]
        brief["meh"]["hp_hz"] = 160

    cfg2 = load_config(_temp_config(tmp_path, brief_changes=other_brief, name="cfg2"))
    space2 = DesignSpace.from_config(cfg2)
    assert space2.seed.hash() == design.hash()          # same geometry, same solve key
    ctx2 = evmod.make_context(cfg2, cache_dir=cache, lib_shas=LIB_SHAS)
    ctx2.write_ndjson = False
    ev2 = evmod.evaluate(design, space2, cfg2, "screen", tmp_path / "run2", None, backend, ctx=ctx2)

    assert ev2.error == "", ev2.error
    assert backend.calls == 1, "the stored BEM response must be re-scored without a new solve"
    assert np.isfinite(ev2.objective)
    assert ev2.objective != ev1.objective
    assert ev2.cached is True


def test_meh_solve_spec_carries_the_brief_tags(tmp_path):
    cfg = load_config(_temp_config(tmp_path, brief_changes=_one_candidate))
    spec = solve_spec("screen", cfg)
    assert "source_tags" not in spec.extra                  # config.solve_spec stays untouched
    meh = evmod.meh_block_of(cfg)
    assert meh is not None
    assert evmod.meh_source_tags(meh) == (2, 10)
    assert evmod._with_meh_source_tags(spec, meh).extra["source_tags"] == [2, 10]


def test_non_meh_brief_keeps_the_single_source_spec():
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    assert evmod.meh_block_of(cfg) is None
    assert "source_tags" not in solve_spec("screen", cfg).extra

