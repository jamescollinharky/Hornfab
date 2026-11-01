"""Offline tests for CMA covariance snapshots (search/cma.py::covariance_summary)."""
from __future__ import annotations

import json

import cma as cma_lib
import numpy as np
import pytest

from hornlab_search.search import cma as cma_mod
from hornlab_search.types import Design, Evaluation, SolveOutcome
from test_search_support import LIBS, SyntheticBackend, fast_cfg


def test_covariance_summary_shapes_and_order():
    keys = ["a", "b", "c"]
    es = cma_lib.CMAEvolutionStrategy([0.5, 0.5, 0.5], 0.2,
                                      {"bounds": [0, 1], "verbose": -1, "seed": 7})
    for _ in range(8):
        X = es.ask()
        # Anisotropic bowl: stretch axis 1 so C_11 should grow relative to others.
        F = [float((x[0] - 0.4) ** 2 + 4.0 * (x[1] - 0.4) ** 2 + (x[2] - 0.4) ** 2) for x in X]
        es.tell(X, F)
    snap = cma_mod.covariance_summary(es, keys, include_C=True)
    assert snap["keys"] == keys
    assert snap["n_dim"] == 3
    assert len(snap["coordinates"]) == 3
    assert snap["coordinates"][0]["C_ii"] >= snap["coordinates"][-1]["C_ii"]
    assert set(c["key"] for c in snap["coordinates"]) == set(keys)
    assert abs(sum(c["share"] for c in snap["coordinates"]) - 1.0) < 1e-9
    assert snap["eigenpairs"] and snap["eigenpairs"][0]["rank"] == 1
    assert "top_loadings" in snap["eigenpairs"][0]
    assert snap["C"] is not None and len(snap["C"]) == 3
    with pytest.raises(ValueError):
        cma_mod.covariance_summary(es, ["a", "b"])


def analytic_eval():
    def fake(design, space, cfg, mode, run_dir, store, backend, **kw):
        p = design.params
        j = (((p["a_deg"] - 32.0) / 10.0) ** 2 + ((p["n"] - 5.0) / 3.0) ** 2
             + ((p["L_mm"] - 300.0) / 100.0) ** 2 + (p["aspect_ratio"] - 1.5) ** 2)
        return Evaluation(design_hash=design.hash(), design=design, mesh_hash="m", solve_hash="s",
                          objective=float(j), terms={"total": float(j)}, metrics=None, mesh=None,
                          outcome=SolveOutcome(True, None, 0.0, None, ""), cached=False, error="")
    return fake


def test_search_writes_cma_covariance(smoke_cfg, tmp_path, monkeypatch):
    cfg = fast_cfg(smoke_cfg)
    monkeypatch.setattr(cma_mod, "evaluate", analytic_eval())
    from hornlab_search.solve import worker
    worker.mark_cold()
    run_dir = tmp_path / "r"
    cma_mod.search(cfg, run_dir, "screen", backend=SyntheticBackend(), budget=25,
                   store=None, lib_shas=LIBS)
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    cov = run["cma_covariance"]
    assert cov["n_dim"] == len(cov["keys"])
    assert cov["coordinates"]
    assert (run_dir / "cma" / "covariance.json").is_file()
    side = json.loads((run_dir / "cma" / "covariance.json").read_text(encoding="utf-8"))
    assert side["keys"] == cov["keys"]
