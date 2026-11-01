"""Sandbox as an exploration tool (2026-10-26, owner: "the sandbox idea was just to see what the
sliders do"; "enable Morph for all the typologies that can take it, everywhere in the GUI").

Backend behaviour pinned here: Morph knobs reach every Morph-capable config; a shape a search
would refuse is still DRAWN with the reason; every shape reports its measured size; natives get
a measured envelope; save-bounds can ADD a Morph search row; the self-approach guard no longer
refuses ordinary lip curvature. Offline, no GPU.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
import pytest
import yaml

from conftest import requires_mesher
from hornlab_search.config import load_config
from hornlab_search.design.generators import grid as G
from hornlab_search.gui import data as D

ROOT = Path(__file__).resolve().parents[1]


def _q(brief: str, detail: str = "2d", **knobs) -> dict:
    q = {"brief": [brief], "detail": [detail]}
    if knobs:
        q["knobs"] = [json.dumps(knobs)]
    return q


# ------------------------------------------------------------------ Morph capability

def test_morph_capability_rule():
    assert D.morph_capable({"family": "OSSE", "seed_params": {}})
    assert D.morph_capable({"family": "R-OSSE"})
    assert D.morph_capable({"family": "FREEFORM", "generator": {"name": "typology"}})
    assert not D.morph_capable({"family": "FREEFORM",
                                "generator": {"name": "typology", "mouth": "superellipse"}})
    assert not D.morph_capable({"family": "FREEFORM", "generator": {"name": "grid", "rows": {}}})
    assert not D.morph_capable({"family": "FREEFORM", "seed_params": {"cad": {}}})
    by = {c["name"]: c for c in D.list_configs(ROOT)}
    assert by["biradial_keele"]["morph_capable"] is True
    assert by["rosse_baseline"]["morph_capable"] is True
    assert by["salmon_x_shape"]["morph_capable"] is False
    assert by["ath_twinray_380"]["morph_capable"] is False


@requires_mesher
def test_morph_knobs_reach_a_native_config_that_does_not_declare_them():
    base = D.preview_shape(ROOT, "osse_baseline", _q("osse_75x45"))
    assert base["morph_capable"] is True
    shrunk = D.preview_shape(ROOT, "osse_baseline", _q(
        "osse_75x45", morph_target=1, morph_width_mm=300, morph_height_mm=200,
        morph_corner_mm=30, morph_rate=3, morph_allow_shrinkage=1))
    assert not any("morph" in n for n in shrunk["notes"]), shrunk["notes"]
    assert shrunk["dims"]["w"] == pytest.approx(300, abs=8)          # target width honoured
    assert shrunk["dims"]["w"] < base["dims"]["w"] - 50


@requires_mesher
def test_rows_typologies_do_not_take_morph():
    out = D.preview_shape(ROOT, "lecleach_rollback", _q("lecleach_rollback_14in", morph_target=1))
    assert out["morph_capable"] is False
    assert any("morph_target" in n and "ignored" in n for n in out["notes"])


# ------------------------------------------------------------------ draw what a search refuses

@requires_mesher
def test_a_shape_outside_the_envelope_is_still_drawn_with_the_reason():
    out = D.preview_shape(ROOT, "salmon_elliptical", _q("organic_rollback_14in", g_fc_h_hz=600,
                                                        g_fc_v_hz=600))
    assert out["available"] is True
    assert out["section"]["h"]["inner"]                              # geometry is there
    if out["envelope"].get("overshoot", 0) > 0:
        assert any(r.startswith("invalid_envelope") for r in out["rejected"])


@requires_mesher
def test_every_shape_reports_its_measured_size_and_natives_get_a_measured_envelope():
    ath = D.preview_shape(ROOT, "ath_core", _q("ath_core_2in"))
    assert ath["dims"]["w"] == pytest.approx(397, abs=10)            # the published CORE mouth
    assert ath["envelope"]["available"] is True
    assert ath["envelope"]["source"] == "measured from the preview geometry"
    half = D.preview_shape(ROOT, "salmon_saddle", _q("organic_rollback_14in"))
    assert half["quadrants"] == "14" and half["dims"]["h"] > 0


@requires_mesher
def test_brief_that_conflicts_with_a_pinned_driver_explains_instead_of_crashing():
    out = D.preview_shape(ROOT, "osse_baseline", _q("hifi_90x60_2in"))
    assert out["available"] is False
    assert "cannot load under this brief" in out["notes"][0]


def test_preview_dims_mirror_rule():
    quarter = np.array([[[0.0, 0.0, 0.0], [100.0, 0.0, 50.0], [0.0, 60.0, 50.0]]])
    assert D._preview_dims(quarter, None) == {"w": 200.0, "h": 120.0, "d": 50.0}
    full = np.array([[[-90.0, -40.0, 0.0], [110.0, 60.0, 30.0]]])
    assert D._preview_dims(full, None) == {"w": 200.0, "h": 100.0, "d": 30.0}


# ------------------------------------------------------------------ self-approach guard

def test_guard_accepts_a_smooth_bend_and_refuses_a_tight_fold():
    def arc(radius, sweep_deg, n=400):
        th = np.linspace(0.0, math.radians(sweep_deg), n)
        return np.stack([radius * np.cos(th), np.zeros(n), radius * np.sin(th)], axis=1)
    limit = 8.0
    # radius 10 mm (gentler than a U-turn of 8 mm width): the old arc>=limit rule read ~7.8 mm
    assert G._row_min_nonadjacent_gap(arc(10.0, 180.0), limit) >= limit
    # a hairpin: 30 mm leg, radius-3 U-turn, 30 mm leg back -> the legs sit 6 mm apart, a real
    # fold, still refused
    leg = np.stack([np.full(60, 3.0), np.zeros(60), np.linspace(-30.0, 0.0, 60)], axis=1)
    back = leg[::-1] * np.array([-1.0, 1.0, 1.0])
    hairpin = np.concatenate([leg, arc(3.0, 180.0)[1:-1], back])
    assert G._row_min_nonadjacent_gap(hairpin, limit) < limit


# ------------------------------------------------------------------ save-bounds can add a Morph row

@pytest.fixture()
def examples_root(tmp_path: Path) -> Path:
    examples = tmp_path / "examples"
    (examples / "typologies").mkdir(parents=True)
    for name in ("biradial_keele.yaml", "salmon_x_shape.yaml"):
        shutil.copy2(ROOT / "examples" / "typologies" / name, examples / "typologies" / name)
    shutil.copytree(ROOT / "examples" / "briefs", examples / "briefs")
    (examples / "catalog.yaml").write_text("entries: []\n", encoding="utf-8")
    return tmp_path


def test_save_bounds_adds_morph_search_rows_and_pins_the_target(examples_root):
    path = examples_root / "examples" / "typologies" / "biradial_keele.yaml"
    before = path.read_text(encoding="utf-8")
    r = D.save_bounds(examples_root, {"config": "biradial_keele", "add": {
        "morph_target": {"lo": 1, "hi": 1, "seed": 1, "pinned": True},
        "morph_width_mm": {"lo": 300, "hi": 500, "seed": 400},
        "morph_height_mm": {"lo": 200, "hi": 400, "seed": 300},
    }})
    assert r["ok"] is True, r
    after = path.read_text(encoding="utf-8")
    for line in before.splitlines():                                  # nothing existing moved
        assert line in after
    cfg = load_config(path)
    assert cfg.bounds_raw["morph_target"]["search"] is False
    assert (cfg.bounds_raw["morph_width_mm"]["lo"], cfg.bounds_raw["morph_width_mm"]["hi"]) == (300, 500)
    assert cfg.seed_params["morph_width_mm"] == 400 and cfg.seed_params["morph_target"] == 1


def test_save_bounds_refuses_morph_on_a_rows_typology_and_writes_nothing(examples_root):
    path = examples_root / "examples" / "typologies" / "salmon_x_shape.yaml"
    before = path.read_bytes()
    r = D.save_bounds(examples_root, {"config": "salmon_x_shape",
                                      "add": {"morph_width_mm": {"lo": 1, "hi": 2}}})
    assert r["ok"] is False
    assert r["rejected"][0]["reason"] == "not_a_legal_key_for_this_typology"
    assert path.read_bytes() == before


def test_append_block_lines_keeps_comments_and_indent():
    text = "a: 1\nbounds:\n  # c\n  x: {lo: 1, hi: 2}\nsearch:\n  budget: 3\n"
    out = D._append_block_lines(text, "bounds", ["y: {lo: 0, hi: 1}"])
    assert out == "a: 1\nbounds:\n  # c\n  x: {lo: 1, hi: 2}\n  y: {lo: 0, hi: 1}\nsearch:\n  budget: 3\n"
    assert yaml.safe_load(out)["bounds"]["y"] == {"lo": 0, "hi": 1}


# ------------------------------------------------------------------ page helpers (node)

_PAGE_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
const m = await import(pathToFileURL(process.argv[2]).href);

// explore range: the box widened by its span, positive quantities kept positive
assert.deepEqual(m.exploreRange({ lo: 600, hi: 1200 }, null, 800, "g_fc_h_hz"), { lo: 120, hi: 1800 });
assert.deepEqual(m.exploreRange({ lo: 120, hi: 240 }, null, 160, "g_stop_deg"), { lo: 30, hi: 350 });
assert.deepEqual(m.exploreRange({ lo: -0.4, hi: 0.4 }, null, 0, "g_x_amp"), { lo: -1.2, hi: 1.2 });
assert.ok(m.exploreRange({ lo: 30, hi: 50 }, null, 40, "a_deg").hi <= 89, "angles stay below 90");
assert.deepEqual(m.exploreRange({ lo: 0, hi: 10 }, { lo: 2, hi: 6 }, 5, "k"), { lo: 0, hi: 10 }, "box always kept");
// no box: built around the value, never around 0
assert.deepEqual(m.exploreRange(null, null, 3, "wall_thickness_mm"), { lo: 0.6, hi: 6 });
// band + outside-the-box decisions
assert.equal(m.bandStyle({ lo: 600, hi: 1200 }, { lo: 120, hi: 1800 }), "--band-lo:28.6%;--band-hi:64.3%");
assert.equal(m.outsideBox(300, { lo: 600, hi: 1200 }), true);
assert.equal(m.outsideBox(800, { lo: 600, hi: 1200 }), false);
// captions and size text
assert.ok(m.shapeCaption("14").startsWith("Half model"));
assert.ok(m.shapeCaption("1234").startsWith("Full-ring"));
assert.equal(m.dimsText({ w: 433.6, h: 252.4, d: 213.7 }), "mouth 434 × 252 mm · depth 214 mm");
// a Morph knob's search box is ±25 % inside its range
assert.deepEqual(m.morphSearchBox(400, 0, 1500), { lo: 300, hi: 500 });
// free mode -> a typeable value box; limited (no explore) -> the original row, byte for byte
const free = m.sliderRowHtml({ key: "L_mm", catalog: { lo: 80, hi: 140 }, bounds: { lo: 80, hi: 140 },
  value: 160, explore: { lo: 20, hi: 200 } });
assert.ok(free.includes('class="sbox-num sbox-valin"') && free.includes('min="20" max="200"'), free);
assert.ok(free.includes(">outside search</span>"), free);
const lim = m.sliderRowHtml({ key: "L_mm", catalog: { lo: 80, hi: 140 }, bounds: { lo: 80, hi: 140 }, value: 110 });
assert.ok(!lim.includes("sbox-valin") && lim.includes('min="80" max="140"'), lim);
// fixed rows lock under search limits
assert.ok(m.fixedRowHtml({ key: "w", pinned: 3, value: 3, explore: { lo: 1, hi: 6 }, locked: true }).includes(" disabled"));
assert.ok(!m.fixedRowHtml({ key: "w", pinned: 3, value: 3, explore: { lo: 1, hi: 6 } }).includes(" disabled"));
// a config the catalog does not list yet is read from its own file
const t = m.typologyFromConfigEntry({ name: "c", path: "examples/typologies/x/c.yaml", family: "R-OSSE",
  generator: false, seed_params: { a_deg: 30, wall_thickness_mm: 5 },
  bounds: { a_deg: { lo: 25, hi: 35 }, morph_target: { lo: 1, hi: 1, search: false } } });
assert.equal(t.kind, "native");
assert.deepEqual(t.bounds_index.a_deg.lo, 25);
assert.equal(t.bounds_index.morph_target.search, false);
assert.deepEqual(t.knobs.map(k => k.knob).sort(), ["a_deg", "morph_target", "wall_thickness_mm"]);
console.log("EXPLORE OK");
'''


def test_sandbox_explore_helpers_offline(tmp_path):
    import shutil as _sh
    import subprocess
    node = _sh.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "explore.mjs"
    script.write_text(_PAGE_SCRIPT, encoding="utf-8")
    sandbox = ROOT / "hornlab_search" / "gui" / "static" / "sandbox.js"
    r = subprocess.run([node, str(script), str(sandbox)], capture_output=True, text=True)
    assert "EXPLORE OK" in r.stdout, f"stdout: {r.stdout}\nstderr: {r.stderr}"


# ------------------------------------------------------------------ guiding curve (Ath OS-SE creases)

@requires_mesher
def test_guiding_curve_is_offered_on_osse_only():
    assert D.gcurve_capable({"family": "OSSE"})
    assert not D.gcurve_capable({"family": "R-OSSE"})
    assert not D.gcurve_capable({"family": "FREEFORM", "generator": {"name": "typology"}})
    out = D.preview_shape(ROOT, "ath_core", _q("ath_core_2in"))
    assert out["gcurve_capable"] is True


@requires_mesher
def test_superformula_guiding_curve_makes_the_coverage_vary_with_direction():
    plain = D.preview_shape(ROOT, "ath_core", _q("ath_core_2in", morph_target=0))
    lobed = D.preview_shape(ROOT, "ath_core", _q(
        "ath_core_2in", morph_target=0, gcurve_type=2, gcurve_width_mm=400, gcurve_aspect_ratio=0.7,
        gcurve_dist=0.6, gcurve_sf_a=1, gcurve_sf_b=1, gcurve_sf_m1=4, gcurve_sf_m2=4,
        gcurve_sf_n1=0.5, gcurve_sf_n2=1, gcurve_sf_n3=1))

    def spread(o):
        m = np.array(o["mouth"]["inner"])
        r = np.hypot(m[:, 0], m[:, 1])
        return float(r.max() / r.min())
    assert spread(plain) < 1.02                      # CORE alone: one coverage angle, round mouth
    assert spread(lobed) > 1.5                       # pinched lobes: the radius swings with azimuth


@requires_mesher
def test_mesher_config_refusal_is_explained_not_a_server_error():
    out = D.preview_shape(ROOT, "osse_baseline", _q(
        "osse_75x45", gcurve_type=1, gcurve_width_mm=380, gcurve_aspect_ratio=0.8, gcurve_dist=0.6,
        gcurve_se_n=4, exponent=4))
    assert out["available"] is False
    assert "guiding curve cannot be combined with a non-circular cross_section" in out["notes"][0]
