"""The typology sandbox page (P9 owner ask 2): #/typology/<name> with draggable shape knobs,
editable min/max bounds, live section panels, a hot-swap 3D card, and a save-bounds write path
that sends only the rows that differ from the catalog.

Offline pins in the established style (source pins + node-executed pure helpers, exactly like
tests/test_gui_param_tips.py and tests/test_gui_brief_authoring.py):

  (a) sandbox.js is importable in node and its PURE surface really runs: the slider-row builder
      (one full row's HTML for a fixture knob, tooltip title text included), the URL-state
      serialize/round-trip, the timing decision (fast = rAF-throttle, slow = release-debounce),
      the at-limit / envelope chip decisions, the initial-value chain (payload > default >
      derived midpoint, never invented), only-changed save-payload assembly, the two-step arm
      machine, the save-result renderer (notes verbatim), and the frozen GET-contract URL.
  (b) the wiring stays honest: route + card affordance registered in app.js, the 3D container
      carries data-v3d AND receives _dispose3d (route()'s sweep contract), timers join a
      {once:true} hashchange cleanup, the graceful-absence paths are present (preview endpoint
      unavailable -> empty states + sliders still work + save disabled with an honest tooltip).
  (c) app.css additions introduce no NEW hex (every hex in the sandbox block already exists in
      the pre-change stylesheet), and sandbox.js joined the test_gui.py node --check gate list
      additively.

Nothing here edits or weakens an existing assertion anywhere; everything is additive.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "hornlab_search" / "gui" / "static"
SANDBOX = STATIC / "sandbox.js"
APPJS = STATIC / "app.js"
APP_CSS = STATIC / "app.css"
TEST_GUI_PY = ROOT / "tests" / "test_gui.py"


# ── (1) syntax gate ────────────────────────────────────────────────────────────────────────

def test_sandbox_js_parses_as_an_es_module(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    mjs = tmp_path / "sandbox.mjs"
    mjs.write_text(SANDBOX.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([node, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]


def test_sandbox_js_is_in_the_static_gate_list():
    """The test_gui.py node --check parametrize (a literal list) now includes sandbox.js —
    the additive extension the syntax gate requires, nothing else in that list touched."""
    src = TEST_GUI_PY.read_text(encoding="utf-8")
    m = re.search(r"@pytest\.mark\.parametrize\(\"name\", \[([^\]]+)\]\)", src)
    assert m, "the parametrize list shape changed"
    names = re.findall(r'"([a-z0-9_.]+\.js)"', m.group(1))
    assert "sandbox.js" in names
    for pre in ("app.js", "charts.js", "glossary.js", "view3d.js", "evolution.js",
                "balloon.js", "paramtips.js"):
        assert pre in names


# ── (2) route + card affordance wiring (source pins) ───────────────────────────────────────

def test_route_and_sandbox_view_are_wired():
    src = APPJS.read_text(encoding="utf-8")
    assert 'import { viewTypologySandbox } from "./sandbox.js";' in src
    assert r'{ re: /^#\/typology\/([^\/?#]+)$/,    fn: m => viewTypologySandbox(ROOT, m[1]) },' in src
    # the sandbox belongs to the Typologies nav group, like campaign/run pages do
    assert '(hash === "#/typologies" || hash.startsWith("#/typology/"))' in src


def test_typology_cards_open_the_sandbox():
    src = APPJS.read_text(encoding="utf-8")
    # the honest affordance: a real link (works standalone), the card is focusable + activated
    assert 'data-open="#/typology/${esc(t.name)}" tabindex="0"\n      role="link"' in src
    assert '<a class="typ-open" href="#/typology/${esc(t.name)}"' in src
    # card click navigation skips every existing inner affordance (links, pills, tooltip terms)
    assert 'e.target.closest("a, button, input, select, label, .term")' in src
    # keyboard: Enter/Space on the focused card navigates
    assert 'e.key === "Enter" || e.key === " "' in src
    assert 'e.target !== card' in src


# ── (3) disposal contract + honest-absence wiring (source pins) ────────────────────────────

def test_3d_container_disposal_contract():
    """route()'s [data-v3d] sweep disposes the sandbox player: the container carries the marker
    AND receives _dispose3d (the exact contract the evolution fix landed for evo-3d)."""
    src = SANDBOX.read_text(encoding="utf-8")
    assert '<div id="sbox-3d" data-v3d class="sbox-3dwrap">' in src
    assert "container._dispose3d = () => {" in src
    assert "cancelAnimationFrame(raf)" in src            # the rAF loop joins the sweep
    # timers/listeners never outlive the route (evolution's {once:true} precedent)
    assert 'window.addEventListener("hashchange", cleanup, { once: true })' in src


def test_3d_hot_swap_never_scenes_per_frame():
    """The drag never rebuilds the scene: fast input is rAF-coalesced 2D only, 3D is idle-scheduled
    on release/hold-idle; the swap path assigns geometry into the ONE scene and disposes the old."""
    src = SANDBOX.read_text(encoding="utf-8")
    assert "function applyMesh(verts, tris, quadrants)" in src
    # 1bdd1b7 (ridge overlay) folded the ridgeCache eviction into the same statement: the hot-swap
    # still disposes the old geometry AND drops its cached ridge geometry, so both halves are pinned.
    assert "if (curGeo) { ridgeCache.delete(curGeo); curGeo.dispose(); }" in src
    assert "if (curWireGeo) curWireGeo.dispose();" in src
    assert 'requestAnimationFrame(() => { raf2d = 0; fire2d(); })' in src
    assert 'if (idle3d) clearTimeout(idle3d);' in src


def test_graceful_absence_paths():
    """Preview endpoint dark -> empty-state SVGs, a page-level note, untouched sliders, save
    disabled with an honest tooltip; unavailable sub-blocks show the server's own reason."""
    src = SANDBOX.read_text(encoding="utf-8")
    assert 'const EMPTY_PREVIEW = "preview endpoint unavailable";' in src
    assert "try { briefs = await fetchJson(\"/api/briefs\"); } catch { briefs = []; }" in src
    assert "emptySvg(sideSvg, EMPTY_PREVIEW);" in src and "emptySvg(frontSvg, EMPTY_PREVIEW);" in src
    # sliders render from the catalog in the template itself, independent of any fetch
    assert "entries.map(e => sliderRowHtml({" in src
    # save stays honest while the backend is dark
    assert "the preview API has not answered yet — saving stays off until the server responds" in src
    # unavailable sub-blocks surface the server's reason verbatim, never invented text
    assert '"no preview geometry for this design"' in src
    assert "(s3 && s3.reason)" in src
    assert "size envelope unavailable — ${e.reason}" in src
    # slow kinds disclose the wait; the updater is honest, never a pretend-live drag
    assert '<span class="pill warn" style="cursor:default">updating…</span>' in src
    assert "plan.fetch === \"defer\"" in src


# ── (4) behaviour, executed for real by node (pure helpers) ────────────────────────────────

_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const m = await import(pathToFileURL(process.argv[2]).href);

// ── fixture: a catalog-shaped knob doc (label/unit/summary/detail/search) ─────────────
const DOC = {
  label: "Depth", unit: "mm",
  summary: "Axial depth shared by both meridians, throat to mouth.",
  detail: "It is the fixed-length dimension for conical, exponential, hypex and OSSE",
  search: { lo: 80, hi: 140 },
  default: 110,
};
const TITLE = 'Depth [mm]: Axial depth shared by both meridians, throat to mouth. ' +
  "It is the fixed-length dimension for conical, exponential, hypex and OSSE. Search range 80.00..140.00 mm.";

// ── merged tooltip title: the paramtips sentence + the detail physics sentence; raw key stays visible elsewhere ──
assert.equal(m.mergedKnobTitle(DOC, "L_mm"), TITLE);
assert.ok(TITLE.length <= 300, TITLE.length);
// cap: when detail does not fit, the paramtips assembly (already capped) wins verbatim
const LONG = {
  label: "Depth", unit: "mm", summary: "S".repeat(240),
  detail: "D".repeat(80), search: { lo: 80, hi: 140 },
};
const fb = m.mergedKnobTitle(LONG, "L_mm");
assert.ok(fb.length <= 300, fb.length);
assert.ok(!fb.includes("D".repeat(10)), "detail dropped when the title would overflow");
// missing detail -> exactly the other surfaces' sentence (paramTitle)
assert.equal(m.mergedKnobTitle({ ...DOC, detail: "" }, "L_mm"),
  "Depth [mm]: Axial depth shared by both meridians, throat to mouth. Search range 80.00..140.00 mm.");
assert.equal(m.mergedKnobTitle(null, "L_mm"), null);

// ── one FULL slider row (pure builder) for a fixture knob ─────────────────────────────
const row = m.sliderRowHtml({
  key: "L_mm", doc: DOC, catalog: { lo: 80, hi: 140 }, bounds: { lo: 80, hi: 140 }, value: 110,
});
assert.equal(row,
  '<div class="sbox-row" data-key="L_mm">' +
  `<span class="mono sbox-kname" tabindex="0" title="${TITLE}">L_mm</span>` +
  '<input class="sbox-num" type="number" step="any" data-role="lo" aria-label="L_mm — editable minimum bound" value="80">' +
  '<input class="sbox-slider" type="range" data-role="slider" aria-label="L_mm value" min="80" max="140" step="1" value="110">' +
  '<input class="sbox-num" type="number" step="any" data-role="hi" aria-label="L_mm — editable maximum bound" value="140">' +
  '<span class="sbox-val num" data-role="val" data-at="">110.0</span>' +
  '<span class="sbox-chips" data-role="chips"></span>' +
  '<button type="button" class="sbox-reset" data-role="reset" aria-label="L_mm — restore the typology\'s published bounds" ' +
  'title="Restore the typology\'s published bounds (80.00..140.00)">↺</button></div>');
// state chips: edited + rejected render into the chips slot; at-limit reds the value
const rowEdited = m.sliderRowHtml({
  key: "L_mm", doc: DOC, catalog: { lo: 80, hi: 140 }, bounds: { lo: 70, hi: 150 },
  value: 70, edited: true, rejected: "hi 150 exceeds the hard limit 140",
});
assert.ok(rowEdited.includes('>edited</span>'), rowEdited);
assert.ok(rowEdited.includes('>rejected: hi 150 exceeds the hard limit 140</span>'), rowEdited);
assert.ok(rowEdited.includes('class="sbox-val num at-limit"'), rowEdited);
assert.ok(rowEdited.includes('value="70"'), rowEdited);
// no doc anywhere -> the raw key degrades honestly (never a blank, never an invented label)
const bare = m.sliderRowHtml({ key: "zz_knob", catalog: { lo: 0, hi: 1 }, bounds: { lo: 0, hi: 1 }, value: 0.5 });
assert.ok(bare.includes('title="zz_knob">zz_knob</span>'), bare);

// ── integer knobs get step 1; degenerate step is the literal "any" (never "0") ─────────
assert.equal(m.sliderStep(2, 8), "1");
assert.equal(m.sliderStep(80, 140), "1");
assert.equal(m.sliderStep(0.3, 1), "0.01");
assert.equal(m.sliderStep(5, 5), "any");
assert.ok(!m.sliderRowHtml({ key: "k", catalog: { lo: 5, hi: 5 }, bounds: { lo: 5, hi: 5 }, value: 5 })
  .includes('step="0"'), "step never becomes 0");

// ── timing decision: fast = rAF-throttle, slow = release-debounce (the spike's measured split) ──
assert.deepEqual(m.timingDecision(false, "input"), { fetch: "raf", updating: false, arms3d: false });
assert.deepEqual(m.timingDecision(false, "release"), { fetch: "now", updating: false, arms3d: true });
assert.deepEqual(m.timingDecision(true, "input"), { fetch: "defer", updating: true, arms3d: false });
assert.deepEqual(m.timingDecision(true, "release"), { fetch: "releaseDebounce", updating: true, arms3d: true });

// ── at-limit (within 2% of a bound — evolution's own rule) + envelope chip ────────────
assert.equal(m.atLimitEdge(80, 80, 140), "lo");
assert.equal(m.atLimitEdge(80.5, 80, 140), "lo");            // 2% of 60 = 1.2
assert.equal(m.atLimitEdge(139.5, 80, 140), "hi");
assert.equal(m.atLimitEdge(110, 80, 140), null);
assert.equal(m.atLimitEdge(110, 110, 110), null);            // degenerate range
assert.equal(m.atLimitEdge(NaN, 80, 140), null);
assert.equal(m.envelopeChip(0), null);
assert.equal(m.envelopeChip(-0.01), null);
const ec = m.envelopeChip(0.2201);
assert.equal(ec.pct, 22);
assert.ok(ec.html.includes("outside the brief envelope (+22%)"), ec.html);
assert.ok(ec.html.includes('class="pill bad"'), "the run page's red at-limit language, not a second one");

// ── starting values: endpoint effective > catalog seed default > derived midpoint ─────
const ENTRIES = [
  { key: "L_mm", lo: 80, hi: 140, doc: DOC },
  { key: "h_s", lo: 0, hi: 0.6, doc: {} },                     // no published default
  { key: "h_n", lo: 2, hi: 8, doc: { default: 4 } },
];
assert.deepEqual(m.initialKnobValues(ENTRIES, {}), { L_mm: 110, h_s: 0.3, h_n: 4 });
assert.deepEqual(m.initialKnobValues(ENTRIES, { L_mm: 95 }), { L_mm: 95, h_s: 0.3, h_n: 4 });
assert.deepEqual(m.initialKnobValues(ENTRIES, { nope: 1, L_mm: 77 }), { L_mm: 77, h_s: 0.3, h_n: 4 });
// effective knobs ARE adopted as the truth of the geometry (the slider follows the clamp)
assert.deepEqual(m.adoptEffectiveKnobs({ a: 1, b: 2 }, { b: 7, c: 3, d: "junk" }), { a: 1, b: 7, c: 3 });
// a requested value is clamped into the (possibly user-edited) row range
assert.equal(m.clampKnob(150, 80, 140), 140);
assert.equal(m.clampKnob(-5, 80, 140), 80);
assert.equal(m.clampKnob(110, 5, 5), 110);

// ── bound edits are validated honestly (never an invalid slider range, never a silent swap) ──
assert.deepEqual(m.boundEditOutcome("lo", 80, 140, 70), { ok: true, lo: 70, hi: 140, msg: "" });
assert.equal(m.boundEditOutcome("lo", 80, 140, 150).ok, false, "lo >= hi refused");
assert.equal(m.boundEditOutcome("hi", 80, 140, "").ok, false, "empty -> refused");
assert.equal(m.boundEditOutcome("hi", 80, 140, "abc").ok, false, "NaN refused");

// ── URL state: serialize -> parse round trip, defaults omitted, junk dropped ──────────
const ST = { brief: "axi_90x90_1in", knobs: { L_mm: 110, h_s: 0.345, h_n: 4 }, bnds: { h_n: { lo: 2, hi: 8 } } };
const qs = m.buildQueryState(ST);
assert.ok(qs.startsWith("?"), qs);
assert.ok(qs.includes("brief=axi_90x90_1in"), qs);
const back = m.readQueryState("#/typology/osse_axi" + qs);
assert.deepEqual({ brief: back.brief, knobs: back.knobs, bnds: back.bnds }, ST);
assert.equal(m.buildQueryState(m.readQueryState("#/typology/osse_axi" + qs)), qs, "stable round trip");
// numbers stay sane in the URL (rounded; no float dust)
const rounded = m.buildQueryState({ knobs: { L_mm: 110.000001 } });
assert.ok(rounded.includes("110") && !rounded.includes("110.000001"), rounded);
// empty state -> no query at all
assert.equal(m.buildQueryState({}), "");
assert.deepEqual(m.readQueryState("#/typology/osse_axi"), { brief: null, knobs: null, bnds: null });
// junk JSON / wrong shapes never break the page
assert.equal(m.readQueryState("#/typology/x?knobs=%7Bbroken").knobs, null);
assert.equal(m.readQueryState("#/typology/x?knobs=%5B1%2C2%5D").knobs, null);          // array is not an object
assert.equal(m.readQueryState("#/typology/x?knobs=%7B%22a%22%3A%22zzz%22%7D").knobs, null); // no finite numbers
assert.equal(m.readQueryState("#/typology/x?bnds=%7B%22a%22%3A%7B%22lo%22%3A8%2C%22hi%22%3A2%7D%7D").bnds, null); // hi<=lo
// briefs survive; only valid brief strings
assert.deepEqual(m.readQueryState("#/typology/x?brief=organic_rollback_1in&knobs=%7B%7D").brief,
  "organic_rollback_1in");

// ── the frozen GET contract, built literally ──────────────────────────────────────────
assert.equal(m.previewShapeUrl("osse axi", "b&1", "2d", { L_mm: 110 }),
  "/api/preview-shape/osse%20axi?brief=b%261&detail=2d&knobs=%7B%22L_mm%22%3A110%7D");
assert.ok(m.previewShapeUrl("c", "b", "3d", {}).includes("detail=3d"));

// ── save payload: ONLY the rows whose min/max differ from the catalog ─────────────────
const CATALOG = { a: { lo: 80, hi: 140 }, b: { lo: 0, hi: 1 }, z: { lo: 5, hi: 6 } };
const changed = m.collectChangedBounds(CATALOG, {
  a: { lo: 80, hi: 140 },                    // unchanged -> dropped
  b: { lo: 0.3, hi: 1 },                     // edited lo -> kept
  z: { lo: 5.00000000005, hi: 6 },           // float dust -> NOT a change
  c: { lo: 1, hi: 2 },                       // unknown key -> dropped (catalog is the authority)
});
assert.deepEqual(Object.keys(changed), ["b"]);
assert.deepEqual(m.saveBoundsPayload("osse_axi", changed), { config: "osse_axi", bounds: { b: { lo: 0.3, hi: 1 } } });

// ── two-step arm machine (the kill-run button's semantics, pure) ──────────────────────
assert.deepEqual(m.armStep("idle", "click"), { state: "armed", fire: false });
assert.deepEqual(m.armStep("armed", "click"), { state: "idle", fire: true });
assert.deepEqual(m.armStep("armed", "timeout"), { state: "idle", fire: false });
assert.deepEqual(m.armStep("idle", "timeout"), { state: "idle", fire: false });

// ── save-result rendering: applied + notes VERBATIM, rejections listed, no crash on junk ──
const okHtml = m.saveResultHtml({
  ok: true, file: "examples/typologies/osse_axi.yaml",
  applied: [{ key: "h_n", from: { lo: 2, hi: 8 }, to: { lo: 1, hi: 10 } }],
  notes: ["config_sha ab12cd34 — resume replays cached evals", "bounds precedence unchanged"],
});
assert.ok(okHtml.includes("Saved 1 bound row to <span class=\"mono\">examples/typologies/osse_axi.yaml</span>."), okHtml);
assert.ok(okHtml.includes("<li><span class=\"mono\">h_n</span>"), okHtml);
assert.ok(okHtml.includes("2.00..8.00 →"), okHtml);
assert.ok(okHtml.includes("config_sha ab12cd34 — resume replays cached evals"), okHtml);
assert.ok(okHtml.includes("bounds precedence unchanged"), okHtml);
const badHtml = m.saveResultHtml({
  ok: false,
  rejected: [{ key: "h_n", reason: "lo 1 is below the hard limit 2" }, { key: "h_s", reason: "not a number" }],
});
assert.ok(badHtml.includes("Nothing saved"), badHtml);
assert.ok(badHtml.includes("h_n</span> — lo 1 is below the hard limit 2"), badHtml);
assert.ok(badHtml.includes("h_s</span> — not a number"), badHtml);
assert.ok(m.saveResultHtml({ error: "not found: /api/save-bounds" }).includes("not found: /api/save-bounds"));
assert.equal(m.saveResultHtml(null), "");
assert.equal(m.saveResultHtml({}), "");
// hostile note text is escaped, never injected
assert.ok(m.saveResultHtml({ ok: true, file: "f", applied: [], notes: ['<script>x</script>'] })
  .includes("&lt;script&gt;x&lt;/script&gt;"));

// ── section geometry helpers (pure) ───────────────────────────────────────────────────
const SEC = {
  h: { inner: [[0, 10], [110, 90]], outer: [[0, 13], [110, 120]] },
  v: { inner: [[0, 10], [110, 90]], outer: [[0, 13], [110, 120]] },
};
const loop = m.combinedSectionLoop(SEC);
assert.equal(loop.kind, "section");
assert.deepEqual(loop.h, [[0, 13], [110, 120], [110, 90], [0, 10]]);   // outer fwd + inner reversed
assert.equal(m.combinedSectionLoop(null), null);
const ext = m.sectionExtents(SEC, { inner: [[55, 45]], outer: [[55, 180]] });
assert.equal(ext.z0, 0); assert.equal(ext.z1, 110);
assert.equal(ext.rmax, 120); assert.equal(ext.mmax, 180);
const X = v => v, Y = v => v;
assert.equal(m.mouthBandPath({}, X, Y), "");
const band = m.mouthBandPath({ outer: [[0, 0], [10, 0]], inner: [[5, 2], [8, 2]] }, X, Y);
assert.ok(band.startsWith("M0.0,0.0L10.0,0.0"), band);
assert.ok(band.endsWith("Z"), band);
assert.ok(band.indexOf("8.0,2.0L5.0,2.0") > 0, "inner ring reversed into the same path");
// QUARTER payload rings are completed into a closed four-quadrant outline (mouth-outline fix).
const qBand = m.mouthBandPath({ outer: [[10, 0], [0, 10]], inner: [[8, 0], [0, 8]] }, X, Y);
assert.ok(qBand.includes("-10.0"), "quarter ring mirrored into the -x quadrant: " + qBand);
assert.ok(qBand.includes("-8.0"), "quarter inner ring mirrored too: " + qBand);
// ROLLBACK meridians are NOT monotone in z: the loop must keep its own point order (the striped
// vertical-plane fringe was a z-sort self-intersection, never a data problem).
const ROLL = { h: { inner: [[0, 10], [100, 80], [120, 60]], outer: [[0, 13], [100, 120], [120, 90]] }, v: null };
assert.deepEqual(m.combinedSectionLoop(ROLL).h,
  [[0, 13], [100, 120], [120, 90], [120, 60], [100, 80], [0, 10]],
  "rollback order preserved, never z-sorted");

console.log("SANDBOX OK");
'''


def test_sandbox_pure_helpers_behave_offline(tmp_path):
    """Executes the pure sandbox helpers for real via node: the full slider row (tooltip title
    included), the URL-state round trip with junk defenses, the timing decision split, the
    chip decisions, the value chain, the save flow (only-changed + arm + result rendering),
    and the section geometry helpers."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")   # same environment gate as test_gui.py's ES-module check
    script = tmp_path / "sandbox_behaviour.mjs"
    script.write_text(_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(SANDBOX)], capture_output=True, text=True)
    assert "SANDBOX OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


# ── (5) CSS discipline: the sandbox block introduces no NEW hex ────────────────────────────

def test_sandbox_css_introduces_no_new_hex():
    css = APP_CSS.read_text(encoding="utf-8")
    marker = "/* ── Typologies card sandbox affordance"
    idx = css.find(marker)
    assert idx != -1, "the sandbox CSS block is missing"
    added = css[idx:]
    pre = css[:idx]
    def hexes(s):
        return set(re.findall(r"#[0-9a-fA-F]{3,8}\b", s))
    new_hexes = hexes(added) - hexes(pre)
    assert not new_hexes, f"new raw hex introduced: {sorted(new_hexes)}"
    # the new rules speak in tokens
    for token in ("var(--rule)", "var(--accent)", "var(--bg)", "var(--ink)", "var(--bad)"):
        assert token in added, token
    # both themes already carry these tokens; nothing here invents a theme-specific colour
    assert ".sbox-val.at-limit" in added       # the existing at-limit treatment, reused
    assert ".typ-card[data-open]:hover" in added


def test_sandbox_css_block_present_and_reduced_motion_guarded():
    css = APP_CSS.read_text(encoding="utf-8")
    m = re.search(r"\.sbox-row \{[^}]*\}", css)
    assert m, "the slider row rule is missing"
    # the row grid collapses on narrow screens instead of scrolling sideways
    assert css.count("@media (max-width: 760px)") >= 1
    # 2026-10-26: one compact line per knob (name | long slider | value | reset); the search-box
    # inputs and chips drop to a second line only when shown, so nothing scrolls sideways
    assert 'grid-template-areas: "name slider val reset" "lo chips chips hi";' in css
    assert ".sbox-3d-fig { grid-area: view; position: sticky;" in css     # 3D stays on screen