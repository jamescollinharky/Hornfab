"""Tests for dataset/record.py: build_record and validate_record. Offline and fast."""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pytest

from conftest import make_fake_response
from hornlab_search.dataset.record import (ARRAY_KEYS, DEFAULT_TRACE_FRACTION, REQUIRED_LIB_SHAS,
                                           SCHEMA_VERSION, build_record, dumps_strict,
                                           record_objective_version, should_capture_traces,
                                           to_jsonable, validate_record)
from hornlab_search.metrics.compute import compute_metrics
from hornlab_search.objective.versions import (SUPPORTED_OBJECTIVE_VERSIONS,
                                               is_supported_objective_version)
from hornlab_search.types import Evaluation, MeshResult, SolveOutcome, SolveSpec, Design
from test_dataset_factory import GRID, LIB_SHAS, TARGET, make_eval, solve_spec


def _built(**kw):
    return build_record(make_eval(3), TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                        area_m2=0.125, created_utc="2026-10-13T00:00:00Z", **kw)


def _leaves(x, path="$"):
    if isinstance(x, dict):
        for k, v in x.items():
            assert isinstance(k, str), f"non-str key at {path}"
            yield from _leaves(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _leaves(v, f"{path}[{i}]")
    else:
        yield path, x


# 1
def test_complete_record_survives_json_dumps_with_no_default_handler():
    meta, arrays = _built()
    text = json.dumps(meta)                               # no default=, no allow_nan games
    assert json.loads(text) == meta
    validate_record(meta)
    assert meta["schema_version"] == SCHEMA_VERSION
    assert meta["ok"] is True and meta["error"] == ""
    assert set(arrays) <= set(ARRAY_KEYS) and "spl_h_db" in arrays and "bw_h_deg" in arrays


# 2
def test_no_numpy_types_anywhere_in_metadata():
    meta, _ = _built()
    n = 0
    for path, leaf in _leaves(meta):
        n += 1
        assert type(leaf) in (str, int, float, bool, type(None)), (path, type(leaf))
    assert n > 50
    # the factory deliberately put np.float64 / np.int64 into scalars and terms
    assert type(meta["metrics_scalars"]["ripple_mean_db"]) is float
    assert type(meta["metrics_scalars"]["n_multilobe_h"]) is int
    assert type(meta["terms"]["nan_count"]) is int


# 3
def test_failed_evaluation_records_ok_false_error_and_no_arrays():
    meta, arrays = build_record(make_eval(5, ok=False, error="MeshTooLargeError: 9000 > 8000"),
                                TARGET, LIB_SHAS, grid=GRID, created_utc="2026-10-13T00:00:00Z")
    validate_record(meta)
    assert meta["ok"] is False
    assert meta["error"] == "MeshTooLargeError: 9000 > 8000"
    assert arrays == {}
    assert meta["mesh"]["n_triangles"] is None and meta["mesh"]["grid"] == GRID
    assert meta["metrics_scalars"] == {}
    assert meta["objective"] == 1e3


def test_failure_without_a_message_still_says_why():
    ev = make_eval(6, ok=False, error="")
    ev.outcome = SolveOutcome(ok=False, response=None, seconds=2.0, peak_vram_mb=None, message="CUDA OOM")
    meta, arrays = build_record(ev, TARGET, LIB_SHAS)
    assert meta["ok"] is False and meta["error"] == "CUDA OOM" and arrays == {}
    ev2 = make_eval(7, ok=False, error="")
    meta2, _ = build_record(ev2, TARGET, LIB_SHAS)
    assert meta2["error"]                                   # never empty on a failure
    validate_record(meta2)


# 4
@pytest.mark.parametrize("key", ["schema_version", "design_hash", "target", "mesh", "solve",
                                 "excitation", "traces", "lib_shas", "objective", "terms",
                                 "created_utc", "params", "metrics_scalars"])
def test_validate_rejects_a_missing_required_key_by_name(key):
    meta, _ = _built()
    del meta[key]
    with pytest.raises(ValueError, match=f"'{key}'"):
        validate_record(meta)


# 5
@pytest.mark.parametrize("pkg", REQUIRED_LIB_SHAS)
def test_validate_rejects_lib_shas_missing_one_package(pkg):
    meta, _ = _built()
    del meta["lib_shas"][pkg]
    with pytest.raises(ValueError, match=pkg):
        validate_record(meta)


def test_validate_rejects_an_empty_sha():
    meta, _ = _built()
    meta["lib_shas"]["hornlab_plots"] = ""
    with pytest.raises(ValueError, match="hornlab_plots"):
        validate_record(meta)


# 6
@pytest.mark.parametrize("bad", [np.float64(1.0), np.float32(1.0), np.int64(3), np.bool_(True),
                                 np.array([1.0, 2.0])])
def test_validate_rejects_numpy_values_smuggled_in(bad):
    meta, _ = _built()
    meta["terms"]["smuggled"] = bad
    with pytest.raises(ValueError, match="numpy"):
        validate_record(meta)


def test_validate_rejects_nan_inf_tuples_and_wrong_schema_version():
    for bad in (float("nan"), float("inf"), (1, 2)):
        meta, _ = _built()
        meta["terms"]["x"] = bad
        with pytest.raises(ValueError):
            validate_record(meta)
    meta, _ = _built()
    meta["schema_version"] = 2
    with pytest.raises(ValueError, match="schema_version"):
        validate_record(meta)
    meta, _ = _built()
    meta["ok"] = False                                      # failure with empty error
    with pytest.raises(ValueError, match="error"):
        validate_record(meta)


# 19
def test_validate_rejects_missing_excitation_block_and_missing_mesh_grid():
    meta, _ = _built()
    del meta["excitation"]
    with pytest.raises(ValueError, match="excitation"):
        validate_record(meta)
    meta, _ = _built()
    del meta["mesh"]["grid"]
    with pytest.raises(ValueError, match="grid"):
        validate_record(meta)
    meta, _ = _built()
    del meta["excitation"]["amplitude"]
    with pytest.raises(ValueError, match="amplitude"):
        validate_record(meta)


def test_excitation_and_grid_are_on_every_row_including_failures():
    for ev in (make_eval(1), make_eval(2, ok=False)):
        meta, _ = build_record(ev, TARGET, LIB_SHAS)        # no grid, no solve_spec supplied
        validate_record(meta)
        assert meta["excitation"]["port_tag"] == 2
        assert meta["excitation"]["port_name"] == "SD1D1001"
        assert meta["excitation"]["kind"] == "uniform_normal_velocity"
        assert meta["excitation"]["frequency_dependent"] is False
        assert meta["mesh"]["grid"] == {"angular_segments": None, "length_segments": None,
                                        "available": False}


# strict JSON: NaN and Inf are written as null
def test_nan_and_inf_become_null_and_every_line_is_strict_json():
    ev = make_eval(8)
    ev.terms["x_nan"] = float("nan")
    ev.terms["x_inf"] = float("-inf")
    ev.metrics.scalars["f_break_h_hz"] = float("nan")
    meta, _ = build_record(ev, TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID)
    assert meta["terms"]["x_nan"] is None and meta["terms"]["x_inf"] is None
    assert meta["metrics_scalars"]["f_break_h_hz"] is None
    validate_record(meta)

    def refuse(tok):
        raise AssertionError(f"bare {tok} token in JSON")

    line = dumps_strict(meta)
    assert "NaN" not in line and "Infinity" not in line
    assert json.loads(line, parse_constant=refuse) == meta
    with pytest.raises(ValueError):
        json.dumps({"a": float("nan")}, allow_nan=False)    # the writer would have refused it too


def test_real_compute_metrics_output_with_nan_ripple_serialises_strictly():
    resp = make_fake_response()
    resp.spl_h_db = resp.spl_h_db.copy()
    ms = compute_metrics(resp, TARGET)
    ms_nan = int(np.isnan(ms.ripple_h_db).sum() + np.isnan(ms.ripple_v_db).sum())
    # force a NaN regardless of what the fake cardioid happens to give
    ms.ripple_h_db = ms.ripple_h_db.copy()
    ms.ripple_h_db[0] = np.nan
    mesh = MeshResult("x.msh", 100, 60, "1", "yz+xz", {"throat": 3, "mouth": 6, "rear": 6},
                      (0, 0, 0, .1, .1, .1), 1.0)
    ev = Evaluation("a" * 12, Design("OSSE", {"r0_mm": 12.7}), "b" * 12, "c" * 12, 1.0,
                    {"total": 1.0}, ms, mesh, SolveOutcome(True, resp, 4.0, 1000.0))
    meta, arrays = build_record(ev, TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID)
    validate_record(meta)
    assert np.isnan(arrays["ripple_h_db"][0])                 # arrays keep NaN (npy handles it)
    assert meta["metrics_scalars"]["di_source"] == "balloon"
    json.loads(dumps_strict(meta), parse_constant=lambda t: (_ for _ in ()).throw(AssertionError(t)))
    assert ms_nan >= 0


# record content: enough to retrain without the original run (CP-5a)
def test_record_carries_everything_needed_to_interpret_it():
    meta, arrays = _built()
    assert meta["family"] == "OSSE" and "r0_mm" in meta["params"]
    assert meta["target"]["coverage_h_deg"] == 90.0 and meta["target"]["freq_weights"] == {"1000.0": 2.0, "4000.0": 1.0}
    assert meta["mesh"]["n_dof"] == 2369 and meta["mesh"]["quadrants"] == "1"
    assert meta["mesh"]["res_mm"] == {"throat": 3.0, "mouth": 6.0, "rear": 6.0}
    assert meta["mesh"]["area_m2"] == 0.125 and len(meta["mesh"]["bbox_m"]) == 6
    s = meta["solve"]
    assert s["backend"] == "beat_cuda" and s["mode"] == "screen" and len(s["freqs_hz"]) == 12
    assert s["observation"] == {"distance_m": 2.0, "angle_count": 73, "balloon": True, "balloon_points": 512}
    assert s["gmres_tol"] == 1e-5 and s["n_dof"] == 2369 and s["seconds"] == 5.0
    assert set(meta["lib_shas"]) == set(REQUIRED_LIB_SHAS)
    assert {"bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db", "on_axis_db",
            "freqs_hz", "spl_balloon_db", "balloon_dirs", "z_throat"} <= set(arrays)
    assert arrays["z_throat"].dtype == np.complex128


def test_solve_block_falls_back_to_the_response_when_no_spec_is_given():
    meta, _ = build_record(make_eval(4), TARGET, LIB_SHAS)
    assert meta["solve"]["backend"] == "fake" and meta["solve"]["mode"] is None
    assert len(meta["solve"]["freqs_hz"]) == 12
    assert meta["solve"]["observation"]["angle_count"] == 73
    validate_record(meta)


def test_traces_block_and_sample_fraction():
    meta, _ = build_record(make_eval(1), TARGET, LIB_SHAS)
    assert meta["traces"] == {"captured": False, "path": None, "kind": None,
                              "sample_fraction": DEFAULT_TRACE_FRACTION}
    meta, _ = build_record(make_eval(1), TARGET, LIB_SHAS, trace_sample_fraction=0.1,
                           traces={"path": "traces/abc.npz", "kind": "p1_pressure+dp0_neumann"})
    assert meta["traces"] == {"captured": True, "path": "traces/abc.npz",
                              "kind": "p1_pressure+dp0_neumann", "sample_fraction": 0.1}
    validate_record(meta)


def test_should_capture_traces_is_deterministic_and_close_to_the_fraction():
    hashes = [hashlib.sha256(str(i).encode()).hexdigest()[:12] for i in range(4000)]
    picks = [should_capture_traces(h, 0.05) for h in hashes]
    assert picks == [should_capture_traces(h, 0.05) for h in hashes]
    assert 0.03 < sum(picks) / len(picks) < 0.07
    assert not should_capture_traces("abcdef012345", 0.0) and should_capture_traces("abcdef012345", 1.0)


def test_to_jsonable_converts_and_rejects():
    out = to_jsonable({"a": np.array([[1.0, np.nan]]), 3: (np.int32(2), np.bool_(False)),
                       "t": {1, 2}, "n": None})
    assert out == {"a": [[1.0, None]], "3": [2, False], "t": [1, 2], "n": None}
    with pytest.raises(TypeError, match=r"\$\.x"):
        to_jsonable({"x": object()})
    with pytest.raises(TypeError):
        to_jsonable({"z": np.array([1j])})
    assert math.isfinite(to_jsonable(1e308))


# objective_version (M3 carry-over): explicit on every new record, absence-tolerant on reads
def test_default_v1_write_records_objective_version_1():
    meta, _ = _built()
    assert meta["objective_version"] == 1
    assert record_objective_version(meta) == 1
    validate_record(meta)


def test_a_v2_evaluation_writes_objective_version_2():
    meta, _ = _built(objective_version=2)
    assert meta["objective_version"] == 2
    assert record_objective_version(meta) == 2
    validate_record(meta)


def test_a_record_missing_objective_version_still_validates_as_v1():
    meta, _ = _built()
    del meta["objective_version"]
    validate_record(meta)                                    # absence is legal...
    assert "objective_version" not in meta                   # ...and the stored data is not mutated
    assert record_objective_version(meta) == 1


def test_a_v3_evaluation_writes_objective_version_3():
    """v3 (2026-10-26: per-plane f0_v + the K-law f0 mask) is a dispatched objective since
    ``search/evaluate.py`` routes to it; its records must validate, not be rejected."""
    meta, _ = _built(objective_version=3)
    assert meta["objective_version"] == 3
    assert record_objective_version(meta) == 3
    validate_record(meta)
    assert is_supported_objective_version(3)


def test_validate_rejects_an_unknown_objective_version():
    meta, _ = _built()
    # 6 is loading_smooth (2026-11-05), so the first UNKNOWN version is now 7.
    for bad in (0, 7, 99, "2", True):
        with pytest.raises(ValueError, match="objective_version"):
            validate_record(dict(meta, objective_version=bad))
    for bad in (0, 7, 99, "2", True):
        assert not is_supported_objective_version(bad)


def test_objective_versions_are_one_source_of_truth_with_the_scorer():
    """The record validator and ``search/evaluate.py`` dispatch must read the same tuple. If a
    future v4 adds a scorer without updating the tuple (or vice versa), evaluate's import-time
    check raises instead of half-landing."""
    from hornlab_search.search.evaluate import _OBJECTIVE_SCORERS

    assert tuple(sorted(_OBJECTIVE_SCORERS)) == SUPPORTED_OBJECTIVE_VERSIONS
    for version in SUPPORTED_OBJECTIVE_VERSIONS:
        meta, _ = _built(objective_version=version)
        validate_record(meta)
        assert record_objective_version(meta) == version


def test_v2_brief_evaluation_writes_objective_version_2_to_the_record(smoke_cfg, tmp_path, monkeypatch):
    """End to end: the context that drives ``_score`` dispatch is the one that stamps the record."""
    import dataclasses

    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.search.evaluate import evaluate, make_context
    from test_search_support import LIBS, SyntheticBackend, install_fakes

    cfg = dataclasses.replace(smoke_cfg, objective_version=2)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    space = DesignSpace.from_config(cfg)
    evaluate(space.seed, space, cfg, "screen", tmp_path / "run", store, be,
             ctx=make_context(cfg, store, lib_shas=LIBS))
    meta, _ = next(store.iter_records(with_arrays=True))
    assert meta["objective_version"] == 2
    validate_record(meta)


def test_v3_evaluation_actually_writes_a_dataset_record(smoke_cfg, tmp_path, monkeypatch):
    """End to end regression: before 2026-10-27 the record writer refused v3, so every objective-v3
    evaluation silently wrote NO dataset record (the exception is caught and logged). Proves the
    record now lands, with the version stamped."""
    import dataclasses

    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.search.evaluate import evaluate, make_context
    from test_search_support import LIBS, SyntheticBackend, install_fakes

    cfg = dataclasses.replace(smoke_cfg, objective_version=3)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    space = DesignSpace.from_config(cfg)
    evaluate(space.seed, space, cfg, "screen", tmp_path / "run", store, be,
             ctx=make_context(cfg, store, lib_shas=LIBS))
    meta, _ = next(store.iter_records(with_arrays=True))
    assert meta["objective_version"] == 3
    validate_record(meta)
