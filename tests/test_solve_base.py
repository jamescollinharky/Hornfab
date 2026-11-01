"""solve/base.py: angles, balloon helpers, sanity checks, failure classification. Offline."""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.solve import base
from hornlab_search.solve.base import (ResponseSanityError, arc_angles_deg, balloon_dirs_from_angles,
                                       balloon_grid_shape, check_cuts, classify_failure, get_backend,
                                       jsonable, stack_responses, theta_deg_from_dirs)
from hornlab_search.types import BackendUnavailableError


# 1
def test_arc_angles_73_is_ascending_exact_and_has_exact_zero():
    a = arc_angles_deg(73)
    assert a.shape == (73,)
    assert np.all(np.diff(a) > 0)
    assert a[0] == -90.0 and a[-1] == 90.0
    assert a[36] == 0.0
    assert np.all(np.abs(np.diff(a) - 2.5) < 1e-12)
    assert np.array_equal(a, -a[::-1])                    # exactly antisymmetric


@pytest.mark.parametrize("n", [3, 5, 37, 61, 75, 181])
def test_arc_angles_any_odd_count_has_exact_end_points_and_zero(n):
    a = arc_angles_deg(n)
    assert a.size == n and a[0] == -90.0 and a[-1] == 90.0 and a[(n - 1) // 2] == 0.0
    assert np.all(np.diff(a) > 0)


# 2
@pytest.mark.parametrize("n", [72, 2, 0, -1, 1])
def test_arc_angles_even_or_tiny_count_raises(n):
    with pytest.raises(ValueError):
        arc_angles_deg(n)


# 3
def test_get_backend_nonsense_raises_backend_unavailable():
    with pytest.raises(BackendUnavailableError, match="nonsense"):
        get_backend("nonsense")


def test_get_backend_reports_the_reason_when_unavailable(monkeypatch):
    from hornlab_search.solve import beat as beat_mod
    monkeypatch.setattr(beat_mod.BeatBackend, "available", lambda self: (False, "no GPU today"))
    with pytest.raises(BackendUnavailableError, match="no GPU today"):
        get_backend("beat_cuda")


def test_get_backend_names_are_the_contract_names():
    assert base.BACKEND_NAMES == ("beat_cuda", "beat_metal", "beat_cpu", "bempp_cpu")


# ------------------------------------------------------------------ balloon helpers

def test_balloon_grid_shape_matches_measured_512_shape():
    assert balloon_grid_shape(512) == (16, 32)
    nt, nph = balloon_grid_shape(1024)
    assert abs(nt * nph - 1024) / 1024 < 0.05 and nph >= nt
    with pytest.raises(ValueError):
        balloon_grid_shape(3)


def test_balloon_dirs_are_unit_vectors_with_the_solver_convention():
    nt, nph = 5, 8
    theta = np.repeat(np.linspace(0.0, 180.0, nt), nph)
    phi = np.tile(np.arange(nph) * 360.0 / nph, nt)
    d = balloon_dirs_from_angles(theta, phi)
    assert d.shape == (nt * nph, 3)
    assert np.allclose(np.linalg.norm(d, axis=1), 1.0)
    assert np.allclose(d[0], [0, 0, 1])                         # theta=0 is +Z
    assert np.allclose(d[-nph], [0, 0, -1], atol=1e-12)         # theta=180 is -Z
    i = nph * 2 + 2                                             # theta=90, phi=90 -> +Y
    assert np.allclose(d[i], [0, 1, 0], atol=1e-12)
    i = nph * 2 + 0                                             # theta=90, phi=0 -> +X
    assert np.allclose(d[i], [1, 0, 0], atol=1e-12)
    assert np.allclose(theta_deg_from_dirs(d), theta, atol=1e-6)


def test_balloon_dirs_shape_mismatch_raises():
    with pytest.raises(ValueError):
        balloon_dirs_from_angles(np.zeros(4), np.zeros(5))


# ------------------------------------------------------------------ sanity

def _cuts(nf=3, n=73):
    h = 90.0 + np.zeros((nf, n))
    return h.copy(), h.copy()


def test_check_cuts_accepts_a_good_pair():
    h, v = _cuts()
    check_cuts([1, 2, 3], 73, h, v)


def test_check_cuts_wrong_shape_message_is_readable():
    h, v = _cuts()
    with pytest.raises(ResponseSanityError, match=r"shape .*expected \(3, 73\)"):
        check_cuts([1, 2, 3], 73, h.T, v)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_check_cuts_non_finite_raises(bad):
    h, v = _cuts()
    h[1, 5] = bad
    with pytest.raises(ResponseSanityError, match="non-finite"):
        check_cuts([1, 2, 3], 73, h, v)


def test_check_cuts_on_axis_mismatch_raises():
    h, v = _cuts()
    v[2, 36] += 2e-6
    with pytest.raises(ResponseSanityError, match="on-axis"):
        check_cuts([1, 2, 3], 73, h, v)


def test_check_cuts_on_axis_off_axis_difference_is_allowed():
    h, v = _cuts()
    v[:, 0] += 3.0                                    # cuts may differ off axis
    check_cuts([1, 2, 3], 73, h, v)


def test_check_cuts_implausible_level_raises():
    h, v = _cuts()
    h += 500.0
    v += 500.0
    with pytest.raises(ResponseSanityError, match="plausible"):
        check_cuts([1, 2, 3], 73, h, v)


# ------------------------------------------------------------------ failure classification

@pytest.mark.parametrize("msg,kind", [
    ("CUDA error: Out of GPU memory", "cuda_oom"),
    ("RuntimeError('Out of GPU memory: asked for 644.8 MiB')", "cuda_oom"),
    ("CUDA_ERROR_OUT_OF_MEMORY (code 2)", "cuda_oom"),
    ("Warm BEAT Engine solver exited with code 1", "worker_exit"),
    ("worker exited with code 4294967295", "worker_exit"),
    ("ConnectionResetError(10054)", "worker_exit"),
    ("ValueError: frequencies must be finite", "other"),
])
def test_classify_failure(msg, kind):
    assert classify_failure(msg) == kind


def test_note_failure_appends_once_per_kind_and_never_raises(tmp_path):
    base.reset_noted()
    notes = tmp_path / "NOTES_FOR_SENIOR.md"
    notes.write_text("# notes\n", encoding="utf-8")
    assert base.note_failure_for_senior("cuda_oom", "boom", context="t", notes_path=notes) is True
    assert base.note_failure_for_senior("cuda_oom", "boom2", context="t", notes_path=notes) is False
    text = notes.read_text(encoding="utf-8")
    assert text.startswith("# notes\n") and text.count("task-05") == 1 and "boom" in text
    assert "dof cap" in text
    assert base.note_failure_for_senior("cuda_oom", "x", notes_path=tmp_path / "missing.md",
                                        once_per_process=False) is False
    base.reset_noted()


# ------------------------------------------------------------------ json

def test_jsonable_handles_numpy_complex_and_big_arrays():
    out = jsonable({"a": np.float64(1.5), "b": np.arange(3), "c": (1, 2), "d": 1 + 2j,
                    "e": np.zeros(10_000), "f": float("nan"), "g": {"k": np.int32(7)}})
    assert out["a"] == 1.5 and out["b"] == [0, 1, 2] and out["c"] == [1, 2]
    assert out["d"] == {"real": 1.0, "imag": 2.0}
    assert isinstance(out["e"], str) and "ndarray" in out["e"]
    assert out["f"] is None and out["g"] == {"k": 7}
    assert base.meta_roundtrips(out)

# ------------------------------------------------------------------ WP8 stack_responses

def _synth(freqs):
    from test_search_support import synthetic_response
    return synthetic_response({"a_deg": 37.5, "aspect_ratio": 1.25, "n": 4.0, "s": 0.7},
                              freqs, 73, 64)


def test_stack_responses_equals_one_solve_on_the_whole_grid():
    whole = _synth([500.0, 1000.0, 2000.0, 4000.0])
    stacked = stack_responses([_synth([500.0, 1000.0]), _synth([2000.0, 4000.0])],
                              whole.freqs_hz)
    for name in ("freqs_hz", "h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db",
                 "balloon_dirs", "spl_balloon_db", "z_throat"):
        assert np.array_equal(getattr(stacked, name), getattr(whole, name)), name
    assert stacked.backend == whole.backend and stacked.n_dof == whole.n_dof


def test_stack_responses_refuses_a_gap_overlap_or_wrong_order():
    a, b = _synth([500.0, 1000.0]), _synth([2000.0, 4000.0])
    with pytest.raises(ValueError, match="tile"):
        stack_responses([a, b], [500.0, 1000.0, 1500.0, 2000.0])          # gap
    with pytest.raises(ValueError, match="tile"):
        stack_responses([a, b], [500.0, 1000.0, 2000.0])                  # dropped frequency
    with pytest.raises(ValueError, match="strictly increasing"):
        stack_responses([a, b], [500.0, 1000.0, 2000.0, 2000.0])          # repeated frequency
