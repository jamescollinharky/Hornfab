"""Frequency-axis range and scoring-floor wiring (run detail / campaign / compare).

The brief band (120 Hz – 12 kHz in the reported run) must always be visible on every frequency
chart, ticks must come from that actual span, and the objective's scoring floor f0 must be marked.
Nothing outside the solved grid may be fabricated: the isobar raster stays blank in the band
margins and the hover readout says "no solved data" there.

Offline pins:
  (a) charts.js::logTicks derives 1/2/5 x decade ticks plus the exact endpoints (and only those);
  (b) app.js::freqAxisLimits is the union of the brief band and the solved grid, with honest
      fallbacks;
  (c) every run-detail frequency chart, the campaign overlay and compare use that helper (and no
      hardcoded FT tick list), c-bw/c-di carry the f0 marker, isobarMap receives xlim/f0, and the
      seed card receives the objective block;
  (d) the K-law feasibility summary (498 mm short, "does not fit") and the objective-name suffix
      render through seedDerivationHtml, while the one-argument call keeps "(masked under v3)".
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"
CHARTS = ROOT / "hornlab_search" / "gui" / "static" / "charts.js"

# Import-time DOM shim, copied from tests/test_gui_brief_authoring.py (app.js touches
# document/window at module scope; location stays on a synchronous view so no fetch happens).
_APP_SHIM = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const fake = () => ({ className: "", id: "", style: {}, dataset: {}, innerHTML: "", textContent: "",
  setAttribute() {}, getAttribute: () => null, replaceWith() {}, appendChild() {},
  addEventListener() {}, removeEventListener() {}, closest: () => null,
  classList: { toggle() {}, add() {}, remove() {} }, querySelector: () => null, querySelectorAll: () => [] });
globalThis.document = {
  getElementById: () => fake(), createElement: () => fake(), createElementNS: () => fake(),
  querySelector: () => null, querySelectorAll: () => [], addEventListener() {},
  documentElement: { hasAttribute: () => true, setAttribute() {}, getAttribute: () => null, style: {} },
  body: { appendChild() {} },
};
globalThis.window = { innerWidth: 1280, addEventListener() {}, scrollTo() {} };
globalThis.matchMedia = () => ({ matches: true, addEventListener() {} });
globalThis.MutationObserver = class { observe() {} };
globalThis.location = { hash: "#/glossary" };
globalThis.requestAnimationFrame = () => 0;
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline shim"));

const app = await import(pathToFileURL(process.argv[2]).href);
'''

_CHARTS_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const charts = await import(pathToFileURL(process.argv[2]).href);
const { logTicks } = charts;

// 120 Hz – 12 kHz: both endpoints plus every decade/2/5 tick inside the span.
const t = logTicks(120, 12000);
for (const v of [120, 1000, 2000, 5000, 10000, 12000]) assert.ok(t.includes(v), `missing ${v}: ${t}`);
for (const v of [100, 20000]) assert.ok(!t.includes(v), `outside tick ${v}: ${t}`);
assert.equal(t[0], 120);
assert.equal(t[t.length - 1], 12000);
assert.deepEqual([...t].sort((a, b) => a - b), t);                 // sorted
assert.equal(new Set(t).size, t.length);                           // deduped
for (const v of t) assert.ok(isFinite(v) && v > 0, `bad tick ${v}`);

// A lower span must not inherit 120 Hz.
const s = logTicks(500, 10000);
assert.ok(!s.includes(120), `120 leaked into 500–10000: ${s}`);
assert.ok(s.includes(500) && s.includes(10000) && s.includes(1000));

// Invalid input is empty, never a guessed range.
assert.deepEqual(logTicks(0, 1000), []);
assert.deepEqual(logTicks(NaN, 1000), []);

console.log("FREQ CHARTS OK");
'''

_FREQ_SCRIPT = _APP_SHIM + r'''
const { freqAxisLimits } = app;
assert.equal(typeof freqAxisLimits, "function");

// The brief band already contains the solved grid.
assert.deepEqual(freqAxisLimits([120, 12000], [500, 800, 1000, 2000, 5000, 10000]), [120, 12000]);
// A solved point above the brief band must not overflow the axis.
assert.deepEqual(freqAxisLimits([120, 12000], [300, 800, 1000, 2000, 5000, 16000]), [120, 16000]);
// Empty grid -> the band; no band either -> the honest fallback.
assert.deepEqual(freqAxisLimits([120, 12000], []), [120, 12000]);
assert.deepEqual(freqAxisLimits(null, []), [100, 10000]);
// Non-finite endpoints are ignored, not propagated.
assert.deepEqual(freqAxisLimits([120, NaN], [500, Infinity]), [120, 500]);
const degenerate = freqAxisLimits([500, 500], [500]);
assert.ok(degenerate[1] > degenerate[0], `zero-width axis: ${degenerate}`);

console.log("FREQ AXIS OK");
'''

_SEED_SCRIPT = _APP_SHIM + r'''
const { seedDerivationHtml } = app;
assert.equal(typeof seedDerivationHtml, "function");

const K = {
  rule: "d = KEELE_K / (f0 * coverage) mm",
  f0_hz: 850,
  required_mouth_w_mm: 332.0261437908497,
  required_mouth_h_mm: 498.03921568627453,
  envelope_mouth_w_mm: 406.4,
  envelope_mouth_h_mm: 406.4,
  held_coverage_w_deg: 73.52941176470588,
  held_coverage_v_deg: 73.52941176470588,
  feasible_w: true,
  feasible_v: false,
  screen_freqs_below_f0: 2, screen_freqs_total: 12,
  derivation: [{ knob: "-", note: "seed_policy explicit: derivation skipped" }],
};

const h = seedDerivationHtml(K);
assert.ok(h.includes("f0 850 Hz"), h);
assert.ok(h.includes("K-law mouth 332 × 498 mm"), h);
assert.ok(h.includes("envelope 406 × 406 mm"), h);
assert.ok(h.includes("held at f0 by the envelope: H 74° / V 74°"), h);
assert.ok(h.includes("H fits"), h);
assert.ok(h.includes("498") && h.includes("does not fit"), h);
assert.match(h, /class="pill warn" title="does not fit the envelope"/);
assert.ok(!h.includes("76°"), "held coverage must round to the stored 74°");

// One argument keeps the historical suffix verbatim.
assert.ok(h.includes("(masked under v3)"), h);
assert.ok(!h.includes("score only f ≥ f0"), h);

// v3 / mask names the rule; one_sided names the forgiveness rule instead.
const hv3 = seedDerivationHtml(K, { version: 3 });
assert.ok(hv3.includes("(masked under v3: cov + dislope score only f ≥ f0)"), hv3);
const hmask = seedDerivationHtml(K, { version: 1, cov_below_f0: "mask" });
assert.ok(hmask.includes("(masked under v3: cov + dislope score only f ≥ f0)"), hmask);
const hone = seedDerivationHtml(K, { version: 5, cov_below_f0: "one_sided" });
assert.ok(hone.includes("(one_sided: below f0 a wider pattern is forgiven, a narrower one still scores)"), hone);
assert.ok(!hone.includes("(masked under v3)"), hone);

// Missing K-law values dash, never invent a number.
const partial = seedDerivationHtml({ f0_hz: 850, derivation: [] });
assert.ok(partial.includes("K-law mouth – × – mm"), partial);
assert.ok(partial.includes("envelope – × – mm"), partial);
assert.ok(partial.includes('<span class="muted">–</span>'), partial);
// No K-law keys and no derivation -> the same empty result as before.
assert.equal(seedDerivationHtml({ rule: "k_law", derivation: [] }), "");

console.log("FREQ SEED OK");
'''


def _run_node(script: str, target: Path, tmp_path: Path, name: str, marker: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")   # same environment gate as the other GUI node tests
    path = tmp_path / name
    path.write_text(script, encoding="utf-8")
    r = subprocess.run([node, str(path), str(target)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert marker in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


def test_log_ticks_cover_the_brief_band(tmp_path):
    """1/2/5 x decade ticks inside the span plus the exact endpoints; 120/20000 excluded outside."""
    _run_node(_CHARTS_SCRIPT, CHARTS, tmp_path, "freq_charts_under_test.mjs", "FREQ CHARTS OK")


def test_freq_axis_limits_union_band_and_data(tmp_path):
    """The axis is the union of the brief band and the solved grid, with honest fallbacks."""
    _run_node(_FREQ_SCRIPT, APPJS, tmp_path, "freq_axis_under_test.mjs", "FREQ AXIS OK")


def test_feasibility_summary_and_objective_suffix(tmp_path):
    """K-law facts render (498 mm short / does not fit); one_sided names itself; one arg is stable."""
    _run_node(_SEED_SCRIPT, APPJS, tmp_path, "freq_seed_under_test.mjs", "FREQ SEED OK")


def test_frequency_charts_and_floor_marker_are_wired():
    """View call sites: full-band xlim, span-derived ticks, f0 markers, isobar xlim, objective."""
    src = APPJS.read_text(encoding="utf-8")
    charts_src = CHARTS.read_text(encoding="utf-8")
    assert "export function freqAxisLimits(band, freqs)" in src
    # run detail (c-bw / c-di / c-axis / c-zre) and compare share the union helper
    assert "const xlim = freqAxisLimits(band, F);" in src
    assert src.count("const xlim = freqAxisLimits(band, F);") >= 2
    assert "const xlim = freqAxisLimits(band, freqsRef);" in src       # campaign overlay
    assert "(cmp.group_a && cmp.group_a.freqs_hz)" in src             # compare takes the real band
    # the old solved-grid-only domain and the fixed tick list are gone
    assert "xlim: [F[0], F[F.length - 1]]" not in src
    assert "xticks: FT" not in src
    # c-bw and c-di mark the scoring floor; c-axis / c-zre do not
    marker = 'vlines: f0Finite ? [{ x: f0Finite, color: css("--warn"), dash: true, label: "f0 " + fmtHz(f0Finite) }] : [],'
    assert src.count(marker) == 2
    assert "isobarMap(sv, rows, D2.angles || [], D2.freqs || F, { title: lbl, H: 300, xlim, f0: f0Finite })" in src
    assert "${seedDerivationHtml(d.feasibility, d.objective)}" in src
    # charts.js: span-derived default ticks, marker lines, and a per-instance clip path
    assert "if (xlog && !xticks) xticks = logTicks(xlim[0], xlim[1]);" in charts_src
    assert "vlines = []" in charts_src
    assert "hl-clip-" in charts_src and "clipPath" in charts_src
    assert "for (const t of logTicks(dLo, dHi))" in charts_src      # isobar axis ticks
    assert "no solved data" in charts_src                           # hover outside the solved grid
    # captions: the band panel is the brief band, and the isobar margins are explicit
    assert "Panel: the brief band. Dashed marker: the scoring floor f0." in src
    assert "Axis spans the brief band; the colour map is drawn only across the solved frequencies." in src
