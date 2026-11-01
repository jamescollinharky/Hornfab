"""WP11b/D: CMA-ME quality-diversity search (``search.algorithm: cma_me``, ``search.qd``).

Offline, no GPU, no mesher, no solver. The runtime tests use a 2-knob copy of the smoke family and
a caching stand-in for ``evaluate`` that returns a real ``MetricSet`` (smooth in-band beamwidths,
one per knob): the search machinery (budget, resume, artifacts) is the production code; only the
acoustics is replaced.

Pinned artifact contract (the GUI lane reads ``archive_heatmap.json`` only):
  archive.json         {algorithm, descriptors{h,v}, bins, ranges{h,v}, cells[...], stats{...}}
  archive_heatmap.json {bins, ranges{h,v}, descriptors{h,v},
                        cells[{h_center, v_center, objective, design_hash}]}
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import ConfigError, load_config, solve_spec
from hornlab_search.design.space import DesignSpace
from hornlab_search.search import cma as cma_mod
from hornlab_search.search import cma_me as qd_mod
from hornlab_search.search.evaluate import (append_ndjson, evaluation_to_row, read_ndjson,
                                            row_to_evaluation)
from hornlab_search.types import Evaluation, MetricSet, SolveOutcome
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes

QD_NAMES = ("mean_bw_h_deg", "mean_bw_v_deg")


def qd_block(**kw) -> dict:
    block = {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg",
             "bins_h": 6, "bins_v": 6}
    block.update(kw)
    return block


def _config(tmp_path, *, algorithm: str = "cma_me", qd: object = "missing",
            name: str = "cfg.yaml", restarts: dict | None = None):
    """A copy of search_smoke.yaml with the algorithm / qd block under test."""
    raw = yaml.safe_load((EXAMPLES / "search_smoke.yaml").read_text(encoding="utf-8"))
    raw["search"]["algorithm"] = algorithm
    if qd != "missing":
        if qd is None:
            raw["search"].pop("qd", None)
        else:
            raw["search"]["qd"] = qd
    if restarts is not None:
        raw["search"]["restarts"] = restarts
    path = tmp_path / name
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def two_knob_cfg(smoke, qd=None):
    """The smoke family reduced to two searchable knobs (``a_deg``, ``aspect_ratio``), with a
    ``search.qd`` block, so the 11x11 acceptance scan is cheap and spans the descriptor space."""
    bounds = {k: dict(v) for k, v in smoke.bounds_raw.items()}
    for k in bounds:
        bounds[k]["search"] = k in ("a_deg", "aspect_ratio")
    raw = json.loads(json.dumps(smoke.raw))
    raw["search"] = {**raw["search"], "algorithm": "cma_me", "qd": qd or qd_block()}
    s = dataclasses.replace(smoke.search, algorithm="cma_me", qd=qd or qd_block(), tolfun=1e-12,
                            restarts=None)
    return dataclasses.replace(smoke, bounds_raw=bounds, search=s, raw=raw)


def knob_eval(cfg, log=None):
    """A caching stand-in for ``evaluate`` over the two knobs.

    Descriptors are full-scale angles (180*u for the normalised knob u), so an 11x11 scan of the
    knob cube reaches (close to) the whole bin grid; J is a smooth bowl whose optimum is inside the
    cube. Cache hits are honoured exactly like ``evaluate`` (in-run memo / resumed ndjson row), so
    the budget and resume semantics under test are the production ones. Every new evaluation also
    writes its real ndjson row, which is what the artifact digest reads."""
    freqs = np.linspace(float(cfg.target_raw["band_lo_hz"]), float(cfg.target_raw["band_hi_hz"]), 9)

    def fake(design, space, cfg_, mode, run_dir, store, backend, *, ctx=None, **kw):
        key = f"{design.hash()}-fake-mesh-fake-solve"
        if ctx is not None and key in ctx.known:
            return dataclasses.replace(ctx.known[key], design=design)
        p = design.params
        u1 = (float(p["a_deg"]) - 5.0) / 50.0
        u2 = (float(p["aspect_ratio"]) - 1.0) / 1.0
        n = freqs.size
        metrics = MetricSet(
            freqs_hz=freqs.copy(), bw_h_deg=np.full(n, 180.0 * u1),
            bw_v_deg=np.full(n, 180.0 * u2), di_db=np.zeros(n), di_source="cuts_estimate",
            ripple_h_db=np.zeros(n), ripple_v_db=np.zeros(n), on_axis_db=np.zeros(n),
            z_throat_real=None, scalars={})
        j = float((u1 - 0.62) ** 2 + (u2 - 0.37) ** 2)
        ev = Evaluation(design_hash=design.hash(), design=design, mesh_hash="fake-mesh",
                        solve_hash="fake-solve", objective=j, terms={"total": j}, metrics=metrics,
                        mesh=None, outcome=SolveOutcome(True, None, 0.0, None, ""), cached=False,
                        error="")
        if log is not None:
            log.append(design.hash())
        if ctx is not None and run_dir is not None:
            row = evaluation_to_row(ev, mode, ctx.n_rows, {"mesh": 0.0, "solve": 0.0, "total": 0.0})
            append_ndjson(Path(run_dir) / "search.ndjson", row)
            ctx.n_rows += 1
            ctx.known[key] = row_to_evaluation(row)
        return ev

    return fake


def run_qd(cfg, run_dir, budget, **kw):
    return cma_mod.search(cfg, run_dir, "screen", backend=SyntheticBackend(), budget=budget,
                          lib_shas=LIBS, **kw)


def run_json(run_dir):
    return json.loads((run_dir / "run.json").read_text(encoding="utf-8"))


def archive_json(run_dir):
    return json.loads((run_dir / "archive.json").read_text(encoding="utf-8"))


def flat_cells(payload, bins) -> set[int]:
    return {int(c["bin"][0]) * int(bins[1]) + int(c["bin"][1]) for c in payload["cells"]}


# ------------------------------------------------------------------ a. algorithm validation


def test_algorithm_accepts_exactly_cma_and_cma_me(tmp_path):
    with pytest.raises(ConfigError, match=r"search\.algorithm"):
        load_config(_config(tmp_path, algorithm="nsga2", qd=None, name="bad.yaml"))

    cfg = load_config(_config(tmp_path, qd=qd_block(), name="qd.yaml"))
    assert cfg.search.algorithm == "cma_me"
    assert cfg.search.qd == qd_block()

    plain = load_config(_config(tmp_path, algorithm="cma", qd=None, name="plain.yaml"))
    assert plain.search.algorithm == "cma" and plain.search.qd is None

    # cma_me without a qd block has no bins/descriptors: refused rather than silently defaulted.
    with pytest.raises(ConfigError, match=r"search\.qd"):
        load_config(_config(tmp_path, algorithm="cma_me", qd=None, name="noqd.yaml"))


# ------------------------------------------------------------------ b. qd validation


@pytest.mark.parametrize("block", [
    {"descriptor_h": "mean_di_db", "descriptor_v": "mean_bw_v_deg", "bins_h": 4, "bins_v": 4},
    {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_h_deg_typo", "bins_h": 4,
     "bins_v": 4},
    {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg", "bins_h": 4, "bins_v": 4,
     "extra": 1},
    {"descriptor_h": "mean_bw_h_deg", "bins_h": 4, "bins_v": 4},        # missing descriptor_v
    {"descriptor_v": "mean_bw_v_deg", "bins_h": 4, "bins_v": 4},        # missing descriptor_h
    {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg", "bins_v": 4},   # no bins_h
    {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg", "bins_h": 4},   # no bins_v
    {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg", "bins_h": 1, "bins_v": 4},
    {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg", "bins_h": 65, "bins_v": 4},
    {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg", "bins_h": 4.5, "bins_v": 4},
    {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg", "bins_h": True, "bins_v": 4},
    "mean_bw_h_deg",                                                     # not a mapping
])
def test_bad_qd_blocks_raise_config_error_with_the_search_qd_prefix(tmp_path, block):
    with pytest.raises(ConfigError, match=r"search\.qd"):
        load_config(_config(tmp_path, qd=block, name="badqd.yaml"))


# ------------------------------------------------------------------ c. absent key = today


def test_plain_cma_writes_no_archive_and_no_qd_run_json_key(smoke_cfg, tmp_path, monkeypatch):
    cfg = fast_cfg(smoke_cfg)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    cma_mod.search(cfg, tmp_path / "r", "screen", backend=be, budget=12, lib_shas=LIBS)
    assert not (tmp_path / "r" / "archive.json").exists()
    assert not (tmp_path / "r" / "archive_heatmap.json").exists()
    rj = run_json(tmp_path / "r")
    assert "qd" not in rj
    assert rj["stats"]["non_cached"] == 12 and rj["stop_reason"] == "budget"


# ------------------------------------------------------------------ d. budget + resume


def test_budget_exactness_and_deterministic_resume_match_an_uninterrupted_run(
        smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=6, bins_v=6))
    budget = 40

    seen_u: list[str] = []
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(cfg, seen_u))
    run_qd(cfg, tmp_path / "u", budget)

    seen_1: list[str] = []
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(cfg, seen_1))
    run_qd(cfg, tmp_path / "r", budget // 2)
    assert len(seen_1) == budget // 2

    seen_2: list[str] = []
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(cfg, seen_2))
    run_qd(cfg, None, budget // 2, resume=tmp_path / "r")
    assert not (set(seen_1) & set(seen_2)), "a finished evaluation was evaluated again"

    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(rows) == budget and not any(r["cached"] for r in rows)
    assert run_json(tmp_path / "r")["stats"]["non_cached"] == budget   # combined, exactly once
    assert run_json(tmp_path / "r")["stop_reason"] == "budget"

    # deterministic replay: byte-for-byte the same cell set, centers, objectives and stats
    au, ar = archive_json(tmp_path / "u"), archive_json(tmp_path / "r")
    assert au["cells"] == ar["cells"]
    assert au["ranges"] == ar["ranges"] and au["bins"] == ar["bins"]
    assert au["stats"] == ar["stats"]
    hu = json.loads((tmp_path / "u" / "archive_heatmap.json").read_text(encoding="utf-8"))
    hr = json.loads((tmp_path / "r" / "archive_heatmap.json").read_text(encoding="utf-8"))
    assert hu["cells"] == hr["cells"]
    assert json.loads((tmp_path / "u" / "best.json").read_text())["objective"] == \
        json.loads((tmp_path / "r" / "best.json").read_text())["objective"]


def test_archive_json_matches_the_pinned_contract(smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=5, bins_v=4))
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(cfg))
    run_qd(cfg, tmp_path / "r", 30)

    a = archive_json(tmp_path / "r")
    assert a["algorithm"] == "cma_me"
    assert a["descriptors"] == {"h": "mean_bw_h_deg", "v": "mean_bw_v_deg"}
    assert a["bins"] == [5, 4]
    assert set(a["ranges"]) == {"h", "v"}
    assert a["stats"]["total_bins"] == 20
    assert a["stats"]["occupied_bins"] == len(a["cells"]) <= 20
    assert a["stats"]["coverage"] == pytest.approx(len(a["cells"]) / 20)
    assert a["stats"]["non_cached"] == 30 and a["stats"]["total_evals"] == 30
    assert [tuple(c["bin"]) for c in a["cells"]] == sorted(tuple(c["bin"]) for c in a["cells"])
    for c in a["cells"]:
        assert set(c) == {"bin", "center", "objective", "design_hash", "eval_no"}
        lo_h, hi_h = a["ranges"]["h"]
        lo_v, hi_v = a["ranges"]["v"]
        assert lo_h <= c["center"][0] <= hi_h and lo_v <= c["center"][1] <= hi_v
        assert isinstance(c["eval_no"], int)

    heat = json.loads((tmp_path / "r" / "archive_heatmap.json").read_text(encoding="utf-8"))
    assert set(heat) == {"bins", "ranges", "cells", "descriptors"}     # exactly the pinned schema
    assert heat["descriptors"] == {"h": "mean_bw_h_deg", "v": "mean_bw_v_deg"}
    assert heat["descriptors"] == a["descriptors"]                    # same names as the full record
    assert heat["bins"] == [5, 4] and set(heat["ranges"]) == {"h", "v"}
    assert len(heat["cells"]) == len(a["cells"])
    for hc, c in zip(heat["cells"], a["cells"]):
        assert set(hc) == {"h_center", "v_center", "objective", "design_hash"}
        assert hc["h_center"] == pytest.approx(c["center"][0])
        assert hc["v_center"] == pytest.approx(c["center"][1])
        assert hc["objective"] == pytest.approx(c["objective"])
        assert hc["design_hash"] == c["design_hash"]

    rj = run_json(tmp_path / "r")
    assert rj["qd"]["total_bins"] == 20 and rj["qd"]["non_cached"] == 30


# ------------------------------------------------------------------ e. solve-spec equality


def test_qd_does_not_touch_the_solve_spec(tmp_path):
    """Search-only: the solve-spec hash (cache + provenance) is identical with and without qd."""
    plain = load_config(_config(tmp_path, algorithm="cma", qd=None, name="plain.yaml"))
    qd = load_config(_config(tmp_path, qd=qd_block(), name="qd.yaml"))
    assert solve_spec("screen", plain) == solve_spec("screen", qd)


# ------------------------------------------------------------------ f. ACCEPTANCE: coverage


def test_acceptance_cma_me_covers_most_of_the_grid_scan_reachable_cells(
        smoke_cfg, tmp_path, monkeypatch, capsys):
    """2-knob cheap family: enumerate an 11x11 knob grid through the SAME evaluator, compute the
    cell set that scan reaches at the chosen bins, then run cma_me with a small budget. CMA-ME must
    reach > 50% of the scan-reachable cells."""
    pytest.importorskip("ribs", reason="ribs not installed")
    from ribs.archives import GridArchive

    qd = qd_block(bins_h=8, bins_v=8)
    cfg = two_knob_cfg(smoke_cfg, qd=qd)
    fake = knob_eval(cfg)
    space = DesignSpace.from_config(cfg)
    k = len(space.keys())
    scan = GridArchive(solution_dim=k, dims=[8, 8],
                       ranges=[qd_mod.DESCRIPTOR_RANGE_DEG, qd_mod.DESCRIPTOR_RANGE_DEG],
                       seed=cfg.search.seed)
    for i in range(11):
        for j in range(11):
            x = np.array([i / 10.0, j / 10.0])
            ev = fake(space.denormalize(x), space, cfg, "screen", None, None, None)
            vals = qd_mod.descriptor_values(ev, cfg, QD_NAMES)
            assert vals is not None
            scan.add(solution=x[None], objective=np.array([-ev.objective]),
                     measures=np.asarray(vals, dtype=float)[None])
    reached = {int(v) for v in scan.data()["index"]}

    monkeypatch.setattr(qd_mod, "evaluate", fake)
    run_qd(cfg, tmp_path / "r", 160)
    a = archive_json(tmp_path / "r")
    got = flat_cells(a, a["bins"]) & reached
    coverage = len(got) / float(len(reached))
    with capsys.disabled():
        print(f"\nACCEPTANCE coverage: {len(got)}/{len(reached)} scan-reachable cells = "
              f"{100.0 * coverage:.1f}% (archive {a['stats']['occupied_bins']}/"
              f"{a['stats']['total_bins']} bins, {a['stats']['non_cached']} non-cached evals)")
    assert coverage > 0.5, f"CMA-ME reached only {len(got)}/{len(reached)} cells"
