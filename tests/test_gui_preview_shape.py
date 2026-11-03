"""Sandbox preview backend: GET /api/preview-shape/<config> (offline, geometry only).

Pins the FROZEN response contract the sandbox page builds against, the per-kind dispatch
(generator / grid / rows / native / cad), the spike's silent-OSSE hazard (a grid block must
NEVER reach ``build_preview_geometry``), the cad-before-``to_mesher_config`` ordering, and the
five-name seam pin. No GPU, no meshing, no writes.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# CI installs the package with --no-deps (the offline suite needs only numpy/scipy/pyyaml/cma),
# so the optional mesher is simply absent there. Absent = nothing to check; a PRESENT mesher whose
# pinned preview API changed must still fail loudly (that is what the seam pin below is for).
try:
    _have_mesher = importlib.util.find_spec("hornlab_mesher") is not None
except (ImportError, ValueError):  # a broken/absent parent package is the same "not installed"
    _have_mesher = False
if not _have_mesher:
    pytest.skip("optional dependency hornlab_mesher is not installed in this environment",
                allow_module_level=True)

from hornlab_search.gui import data as D
from hornlab_search.gui import preview as seam
from hornlab_search.gui.server import App

ROOT = Path(__file__).resolve().parents[1]


def _q(**kwargs) -> dict:
    """Query dict shaped like ``urllib.parse.parse_qs`` (every value is a list)."""
    return {key: [value] for key, value in kwargs.items()}


# ------------------------------------------------------------------ per-kind contracts

def test_generator_kind_osse_axi_sections_mouth_3d_and_timings():
    out = D.preview_shape(ROOT, "osse_axi", _q(detail="3d"))
    assert out["version"] == 1
    assert out["config"] == "osse_axi"
    assert out["kind"] == "generator"
    assert out["units"] == "mm"
    assert out["quadrants"] == "1"
    assert out["available"] is True
    assert out["brief"] == "axi_90x90_1in"
    assert out["slow"] is False

    h = out["section"]["h"]
    v = out["section"]["v"]
    assert len(h["inner"]) >= 2 and len(h["outer"]) == len(h["inner"])
    assert len(v["inner"]) >= 2 and len(v["outer"]) == len(v["inner"])
    # (z, r) pairs, z strictly increasing on this OSSE meridian
    assert all(b[0] > a[0] for a, b in zip(h["inner"], h["inner"][1:]))
    assert all(row[1] > 0.0 for row in h["inner"])
    assert len(out["mouth"]["inner"]) >= 3
    assert len(out["mouth"]["outer"]) == len(out["mouth"]["inner"])

    shape = out["shape3d"]
    assert shape["available"] is True
    assert shape["roles"] == ["horn.inner", "horn.outer", "mouth_rim"]
    assert len(shape["verts"]) % 3 == 0 and len(shape["verts"]) > 0
    assert len(shape["tris"]) % 3 == 0 and len(shape["tris"]) > 0
    assert all(0 <= i < len(shape["verts"]) // 3 for i in shape["tris"])

    timings = out["timings_ms"]
    assert set(timings) == {"params", "section", "shape3d", "total"}
    assert all(value >= 0.0 for value in timings.values())
    assert timings["total"] >= max(timings["params"], timings["section"], timings["shape3d"])
    assert out["envelope"] == {"available": True, "overshoot": 0.0}


def test_rows_kind_salmon_elliptical_is_slow_and_has_own_march_sections():
    out = D.preview_shape(ROOT, "salmon_elliptical", _q(detail="2d"))
    assert out["kind"] == "rows"
    assert out["slow"] is True
    assert out["available"] is True
    assert out["quadrants"] == "1"
    assert len(out["section"]["h"]["inner"]) == 33
    assert len(out["section"]["v"]["inner"]) == 33
    assert len(out["mouth"]["inner"]) == 15
    assert out["envelope"]["available"] is True
    assert isinstance(out["envelope"]["overshoot"], float)
    assert out["shape3d"] == {"available": False, "reason": "detail=2d"}


def test_grid_kind_uses_the_configs_own_arrays():
    out = D.preview_shape(ROOT, "grid_ellipse", _q(detail="2d"))
    assert out["kind"] == "grid"
    assert out["slow"] is False
    assert out["available"] is True
    assert len(out["section"]["h"]["inner"]) == 33
    assert len(out["mouth"]["inner"]) == 13
    assert out["envelope"]["available"] is True


def test_native_kind_measures_its_envelope_from_the_preview_geometry():
    # 2026-10-26: the estimator still has no native branch, so the sandbox MEASURES the drawn
    # shape against the brief instead of leaving the envelope blank.
    bare = D.preview_shape(ROOT, "osse_baseline", _q(detail="2d"))      # no brief: nothing to measure against
    assert bare["envelope"] == {"available": False, "reason": "the brief has no size envelope"}
    out = D.preview_shape(ROOT, "osse_baseline", _q(detail="2d", brief="osse_75x45"))
    assert out["kind"] == "native"
    assert out["available"] is True
    assert out["envelope"]["available"] is True
    assert out["envelope"]["source"] == "measured from the preview geometry"
    assert out["envelope"]["overshoot"] >= 0.0
    assert out["dims"]["w"] > 0 and out["dims"]["h"] > 0 and out["dims"]["d"] > 0
    assert len(out["section"]["h"]["inner"]) >= 2


def test_cad_kind_is_hard_unavailable_with_the_mesher_gap_reason():
    out = D.preview_shape(ROOT, "multicell_3x3", _q(detail="3d"))
    assert out["available"] is False
    assert out["kind"] == "native"
    assert out["section"]["h"]["inner"] == [] and out["mouth"]["inner"] == []
    assert out["shape3d"]["available"] is False
    assert out["envelope"]["available"] is False
    assert any("CAD/STEP recipe" in note and "tools/cad/multicell.py" in note
               for note in out["notes"])


# ------------------------------------------------------------------ silent-OSSE pin

def test_grid_and_rows_blocks_never_reach_the_viewport(monkeypatch):
    """The spike's silent-OSSE hazard: a grid block must never hit build_preview_geometry.

    A ``build_preview_geometry`` call with an unrecognized params dict silently builds a
    default OSSE shell (measured: mouth radius 210 mm for a real 120 mm design). The grid/rows
    route therefore may not call the viewport at all.
    """
    calls: list[dict] = []

    def sentinel(mcfg):
        calls.append(mcfg)
        raise AssertionError("a grid/rows block reached build_viewport_geometry_from_config")

    monkeypatch.setattr(D, "_build_viewport", sentinel)
    for name in ("grid_ellipse", "salmon_elliptical"):
        out = D.preview_shape(ROOT, name, _q(detail="2d"))
        assert out["available"] is True
    assert calls == []


def test_generator_route_does_call_the_viewport_at_the_spike_coarse_density(monkeypatch):
    """Positive control for the pin above: the formula route DOES use the viewport."""
    real = D._build_viewport
    calls: list[dict] = []

    def spy(mcfg):
        calls.append(mcfg)
        return real(mcfg)

    monkeypatch.setattr(D, "_build_viewport", spy)
    out = D.preview_shape(ROOT, "osse_axi", _q(detail="2d"))
    assert out["available"] is True
    assert len(calls) == 1
    mesh = calls[0]["mesh"]
    assert mesh["angular_segments"] == D.PREVIEW_ANGULAR_SEGMENTS == 65
    assert mesh["length_segments"] == D.PREVIEW_LENGTH_SEGMENTS == 24


def test_cad_is_refused_before_to_mesher_config(monkeypatch):
    """``families.to_mesher_config`` raises a bare ``KeyError: 'cad'``; the dispatch must stop first."""
    from hornlab_search.design import families

    def boom(*_args, **_kwargs):
        raise AssertionError("to_mesher_config reached for a cad design")

    monkeypatch.setattr(families, "to_mesher_config", boom)
    out = D.preview_shape(ROOT, "multicell_3x3", _q(detail="2d"))
    assert out["available"] is False
    assert any("CAD/STEP" in note for note in out["notes"])


# ------------------------------------------------------------------ seam pin

def test_seam_pins_the_five_mesher_preview_names():
    """FAIL (never a soft hasattr skip) if any mesher preview primitive moves."""
    expected = (
        "_surface_grid",
        "_grid_surface_from_selection",
        "_smooth_mouth_rim",
        "_outer_shell_surfaces",
        "analytic_grid_normals",
    )
    assert seam.PINNED_NAMES == expected
    for name in expected:
        if not hasattr(seam, name):
            pytest.fail(f"hornlab_mesher preview primitive {name!r} moved; update gui/preview.py")
        if getattr(seam, name) is None:
            pytest.fail(f"hornlab_mesher preview primitive {name!r} is None")


# ------------------------------------------------------------------ knobs / errors / dispatch

def test_knobs_are_per_key_unknown_names_are_named_not_guessed():
    out = D.preview_shape(ROOT, "osse_axi", _q(detail="2d", knobs=json.dumps(
        {"L_mm": 100.0, "not_a_knob": 3.0})))
    assert out["available"] is True
    assert out["knobs"]["L_mm"] == 100.0
    assert any("not_a_knob" in note for note in out["notes"])


def test_bad_knobs_json_and_unknown_config_are_client_errors():
    with pytest.raises(ValueError):
        D.preview_shape(ROOT, "osse_axi", _q(knobs="{not json"))
    with pytest.raises(FileNotFoundError):
        D.preview_shape(ROOT, "no_such_config", _q(detail="2d"))


def test_server_dispatch_and_unknown_route_head():
    app = App(ROOT)
    out = app.get("/api/preview-shape/osse_axi", _q(detail="2d"))
    assert out["config"] == "osse_axi"
    with pytest.raises(FileNotFoundError):
        app.get("/api/not-a-route", {})
