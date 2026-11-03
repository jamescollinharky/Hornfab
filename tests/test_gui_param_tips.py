"""P9 ask 1 (owner): every geometry parameter shown in the GUI says what it does on hover,
grounded in the GENERATED parameter catalog — never invented.

Offline reader-level pins (same source-pin / node-execution patterns as
tests/test_gui_brief_authoring.py):

  (a) hornlab_search/gui/static/paramtips.js is a pure, importable ES module over the committed
      catalog: cached load (with direct data injection for offline tests), per-(config, key)
      docFor with a nested-path fallback to the base knob, graceful raw-key degradation for a
      network failure / unknown typology / unknown key (never guesses across typologies — knob
      names are overloaded, so an unknown config must NOT borrow another family's meaning),
      tip()-shaped title assembly (`label [unit]: summary` + `Search range lo..hi unit.`, capped),
      and the typology-card surfaces. Executed for real by node against the REAL committed
      param-catalog.v1.json.
  (b) the five wired render sites stay wired: evolution knob rows (title text), run-detail
      sensitivity table, run-detail seed-derivation card rows (post-pass — the template's
      seedDerivationHtml(d.feasibility) call site is pinned verbatim by
      tests/test_gui_brief_authoring.py, so the card self-identifies via data-seedknob and the
      view attaches titles with sum.name), compose seed preview rows, and the typologies card
      (name hover + searched-parameter chips).
  (c) the catalog is served by the EXISTING static handler only: no new route, no server edit;
      paramtips.js fetches it by the same relative convention as the page's own JS assets.

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
PARAMTIPS = STATIC / "paramtips.js"
CATALOG = STATIC / "param-catalog.v1.json"
APPJS = STATIC / "app.js"
EVOJS = STATIC / "evolution.js"
APP_CSS = STATIC / "app.css"
SERVER_PY = ROOT / "hornlab_search" / "gui" / "server.py"
TEST_GUI_PY = ROOT / "tests" / "test_gui.py"


# ── (1) syntax gate: the new ES module parses (same offline catch as test_gui.py) ──────────

def test_paramtips_js_parses_as_an_es_module(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    mjs = tmp_path / "paramtips.mjs"
    mjs.write_text(PARAMTIPS.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([node, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]


def test_paramtips_js_is_in_the_static_gate_list():
    """The test_gui.py node --check parametrize (a literal list) now includes paramtips.js —
    the additive extension the syntax gate requires, nothing else in that list touched."""
    src = TEST_GUI_PY.read_text(encoding="utf-8")
    m = re.search(r"@pytest\.mark\.parametrize\(\"name\", \[([^\]]+)\]\)", src)
    assert m, "the parametrize list shape changed"
    names = re.findall(r'"([a-z0-9_.]+\.js)"', m.group(1))
    assert "paramtips.js" in names
    # every existing gate entry is untouched (additive only)
    for pre in ("app.js", "charts.js", "glossary.js", "view3d.js", "evolution.js", "balloon.js"):
        assert pre in names


# ── (2) behaviour, executed for real by node against the REAL committed catalog ────────────

# paramtips.js is DOM-free at import (the only import is charts.js, also import-safe), so the
# node script imports it directly — no shim needed. A "?fresh=1" import creates a second module
# instance with an empty cache to pin the graceful no-catalog fallback.
_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const [SRC, CATALOG] = process.argv.slice(2);
const SRC_URL = pathToFileURL(SRC).href;
const m = await import(SRC_URL);
const cat = JSON.parse(readFileSync(CATALOG, "utf8"));
await m.loadParamCatalog({ data: cat });          // inject the committed catalog (no network in node)

// ── docFor: exact hit ──────────────────────────────────────────────────────────────────
const d = m.docFor("salmon_elliptical", "g_fc_h_hz");
assert.ok(d && typeof d === "object");
assert.equal(d.label, "Salmon H cutoff (rows)");
assert.equal(d.unit, "Hz");
assert.equal(d.summary, "Horizontal endpoint of the per-azimuth Salmon cutoff blend.");
assert.equal(d.search.lo, 600); assert.equal(d.search.hi, 1200);
assert.equal(d.bounds_source.key, "bounds.g_fc_h_hz");

// ── docFor: nested-path fallback to the base knob's entry ──────────────────────────────
const b = m.docFor("freeform_sculpt", "profileH.points.9.9");   // the point itself is not catalogued
assert.ok(b, "path fallback");
assert.equal(b.label, "Control-point radii are the search dimensions");
assert.equal(b.knob, "profileH");

// ── docFor: unknown config / key -> null (NEVER guesses across typologies) ─────────────
assert.equal(m.docFor("no_such_typology", "L_mm"), null);
assert.equal(m.docFor(null, "L_mm"), null);
assert.equal(m.docFor("salmon_elliptical", "no_such_knob"), null);
assert.equal(m.docFor("salmon_elliptical", ""), null);
assert.equal(m.docFor("salmon_elliptical", null), null);

// ── graceful no-catalog degradation (fresh module instance, empty cache) ───────────────
const m2 = await import(SRC_URL + "?fresh=1");
assert.equal(m2.docFor("salmon_elliptical", "g_fc_h_hz"), null);
assert.equal(m2.paramTipHtml("salmon_elliptical", "g_fc_h_hz", "g_fc_h_hz"),
  '<span class="term" tabindex="0" title="g_fc_h_hz">g_fc_h_hz</span>');

// ── formatSearchRange: the second sentence, repo formatting (charts.js::fmt) ───────────
const DOC = { label: "Salmon H cutoff (rows)", unit: "Hz",
              summary: "Horizontal endpoint of the per-azimuth Salmon cutoff blend.",
              search: { lo: 600, hi: 1200 } };
assert.equal(m.formatSearchRange(DOC), "Search range 600.00..1,200.00 Hz.");
assert.equal(m.formatSearchRange({}), "");                       // no bounds -> no sentence
assert.equal(m.formatSearchRange({ search: { lo: 0, hi: Infinity } }), "");

// ── formatParamTitle: the exact assembled sentence (tip() shape + bounds line) ─────────
assert.equal(m.formatParamTitle(DOC, "g_fc_h_hz", null),
  "Salmon H cutoff (rows) [Hz]: Horizontal endpoint of the per-azimuth Salmon cutoff blend. " +
  "Search range 600.00..1,200.00 Hz.");
// the raw key is never lost: when the visible text is NOT the key, the title carries it
assert.equal(m.formatParamTitle(DOC, "g_fc_h_hz", "Salmon H cutoff"),
  "Salmon H cutoff (rows) [Hz] (g_fc_h_hz): Horizontal endpoint of the per-azimuth Salmon " +
  "cutoff blend. Search range 600.00..1,200.00 Hz.");
// no unit -> no bracket; no summary -> no dangling colon; both sentences still assemble
assert.equal(m.formatParamTitle({ label: "Row span", search: { lo: 0.5, hi: 2.5 } }, "span", null),
  "Row span: Search range 0.50..2.50.");
// ~300-char cap keeps titles readable
const longy = m.formatParamTitle({
  label: "L", summary: "S".repeat(400), search: { lo: 0, hi: 1 } }, "k", null);
assert.ok(longy.length <= 300, longy.length);
assert.ok(longy.endsWith("…"));

// ── paramTipHtml: the DOM-shape precedent (glossary.js::tip), grounded in the catalog ──
assert.equal(m.paramTipHtml("salmon_elliptical", "g_fc_h_hz", "g_fc_h_hz"),
  '<span class="term" tabindex="0" title="Salmon H cutoff (rows) [Hz]: Horizontal endpoint of ' +
  'the per-azimuth Salmon cutoff blend. Search range 600.00..1,200.00 Hz.">g_fc_h_hz</span>');
// without an override the catalog label is the visible text and the raw key stays in the title
const labelled = m.paramTipHtml("salmon_elliptical", "g_fc_h_hz");
assert.ok(labelled.includes(">Salmon H cutoff (rows)<"), labelled);
assert.ok(labelled.includes("(g_fc_h_hz):"), labelled);
// no doc anywhere -> today's behaviour: raw key as text AND title
assert.equal(m.paramTipHtml(null, "zzz", null),
  '<span class="term" tabindex="0" title="zzz">zzz</span>');
// hostile key text is escaped in BOTH the title attribute and the label text
assert.equal(m.paramTipHtml(null, 'a"b<c', null),
  '<span class="term" tabindex="0" title="a&quot;b&lt;c">a&quot;b&lt;c</span>');

// ── typology chips: the card's searched knob names, each with its enriched tooltip ─────
const chips = m.typologyChipsHtml("salmon_elliptical");
assert.ok(chips.startsWith('<div class="typ-knobs"'), chips);
for (const k of ["g_T", "g_fc_h_hz", "g_fc_v_hz", "g_stop_deg"]) assert.ok(chips.includes(`>${k}</span>`), k);
assert.ok(chips.includes("Search range 600.00..1,200.00 Hz."), chips);
assert.ok(!chips.includes("n_phi"), "only the SEARCHED knobs are chips (n_knobs coherence)");
assert.ok(chips.includes('class="term typ-knob" tabindex="0"'), "keyboard-focusable chips");
assert.equal(m.typologyChipsHtml("multicell_3x3"), "");   // CAD-only typology: no chips, no box
assert.equal(m.typologyChipsHtml("not_a_typology"), "");  // unknown: nothing renders

// ── typology name hover: the catalog's description + knob count ───────────────────────
const CAT_DESC = "per-azimuth spherical_salmon rows (fc_h 800 / fc_v 1100 seed), rollback stop; 4 knobs; labeled hypothesis";
const tip1 = m.typologyTipHtml({ name: "salmon_elliptical", description: "api description", n_knobs: 4 });
assert.ok(tip1.includes(CAT_DESC), tip1);              // the catalog's own description wins
assert.ok(tip1.includes(" · 4 shape parameters"), tip1);
assert.ok(!tip1.includes("api description"), tip1);
const tip2 = m.typologyTipHtml({ name: "not_a_typology", description: "api fallback", n_knobs: 2 });
assert.ok(tip2.includes("api fallback · 2 shape parameters"), tip2);   // graceful API fallback
assert.equal(m.typologyTipHtml({ name: "" }), "");

// ── report the assembled tooltips for the human eyes checking this lane ───────────────
console.log("EVO  :", m.paramTitle("salmon_elliptical", "g_fc_h_hz"));
console.log("SENS :", m.formatParamTitle(m.docFor("osse_axi", "L_mm"), "L_mm", "L_mm"));
console.log("SEED :", m.formatParamTitle(m.docFor("osse_axi", "h_a_deg"), "h_a_deg", "h_a_deg"));
const cp = m.docFor("freeform_sculpt", "profileH.points.1.1");
console.log("SEED2:", cp ? m.formatParamTitle(cp, "profileH.points.1.1", "profileH.points.1.1")
                           : "(profileH.points.1.1 not in freeform_sculpt)");
console.log("COMP :", m.formatParamTitle(m.docFor("splice_osse_tractrix", "L_mm"), "L_mm", "L_mm"));
console.log("CHIP :", m.typologyChipsHtml("salmon_elliptical").slice(0, 220));

console.log("PARAMTIPS OK");
'''


def test_paramtips_behaviour_offline(tmp_path):
    """Executes the pure helpers for real via node: docFor exact/base-fallback/unknown, the
    title sentence assembly with its bounds line and cap, the tip() DOM shape, the graceful
    fallbacks, and the typology surfaces — all against the committed param-catalog.v1.json."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")   # same environment gate as test_gui.py's ES-module check
    script = tmp_path / "paramtips_behaviour.mjs"
    script.write_text(_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(PARAMTIPS), str(CATALOG)],
                       capture_output=True, text=True)
    assert "PARAMTIPS OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
    assert "EVO  : Salmon H cutoff (rows) [Hz]:" in r.stdout   # the real example sentence


# ── (3) wiring pins, one per render site (source-pin style) ────────────────────────────────

def test_wired_evolution_knob_rows():
    """Site 1 — evolution knob rows: raw key stays the visible text; the native title gains the
    catalog's assembled sentence (`paramTitle` falls back to the key it shows today)."""
    src = EVOJS.read_text(encoding="utf-8")
    assert 'import { loadParamCatalog, paramTitle } from "./paramtips.js";' in src
    assert 'await loadParamCatalog();' in src                          # loaded before the rows build
    assert 'title="${esc(paramTitle(E.name, k) ?? k)}"' in src        # E.name = the config name
    assert src.count("paramTitle(E.name, k)") == 1                    # one wiring, the knob row


def test_wired_run_detail_sensitivity_table():
    """Site 2 — sens table: columns untouched; the Parameter cell keeps the raw key visible and
    gains the catalog tooltip for the run's config name."""
    src = APPJS.read_text(encoding="utf-8")
    assert "${paramTipHtml(sum.name, p.key, p.key)}" in src
    assert '<td class="r">${fmt(p.lo, 3)}</td><td class="r">${fmt(p.hi, 3)}</td>' in src  # lo/hi columns unchanged


def test_wired_seed_derivation_card():
    """Site 3 — seed-derivation rows: the pinned call site stays literal; the card marks its knob
    cells (data-seedknob) and the run-detail view attaches catalog titles with sum.name."""
    src = APPJS.read_text(encoding="utf-8")
    assert "${seedDerivationHtml(d.feasibility, d.objective)}" in src   # the pinned template
    assert 'data-seedknob="${esc(r.knob ?? "")}"' in src
    assert 'paramTipHtml(sum.name, td.dataset.seedknob, td.dataset.seedknob)' in src
    assert '.seed-derivation-card td[data-seedknob]' in src           # scoped to this one card


def test_wired_compose_seed_preview():
    """Site 4 — compose seed preview rows: the naming follows the panel heading (catalog_name
    wins); the raw key stays visible; each row gains the enriched tooltip."""
    src = APPJS.read_text(encoding="utf-8")
    assert "${paramTipHtml(nm, k, k)}" in src
    assert 'const nm = (typeof cfg.catalog_name === "string" && cfg.catalog_name) ||' in src


def test_wired_typologies_card():
    """Site 5 — typologies card: the name hover carries the catalog description + knob count and
    the card renders the searched knob names as mono chips, each with its enriched tooltip."""
    src = APPJS.read_text(encoding="utf-8")
    assert '<div class="typ-name">${typologyTipHtml(t)}</div>' in src
    assert "${typologyChipsHtml(t.name)}" in src
    # all four views that show parameters await the (never-throwing) catalog load first
    assert src.count("await loadParamCatalog();") == 3                # run detail + compose + typologies
    assert 'import { loadParamCatalog, paramTipHtml, typologyTipHtml, typologyChipsHtml } from "./paramtips.js";' in src


def test_typology_chip_styling_uses_theme_tokens_only():
    """The new .typ-knob class follows app.css tokens — no new raw hex in the added rules."""
    css = APP_CSS.read_text(encoding="utf-8")
    m = re.search(r"\.typ-knob \{[^}]*\}", css)
    assert m, "the chip rule is missing"
    block = m.group(0)
    for token in ("var(--f-mono)", "var(--rule)", "var(--bg)", "var(--muted)",
                  "cursor:help", "border-radius:999px"):
        assert token in block, token
    # hover + focus carry the accent affordance, like .term's own focus ring
    hover_at = css.find(".typ-knob:hover {")
    focus_at = css.find(".typ-knob:focus {")
    assert hover_at != -1 and focus_at != -1
    assert "var(--accent)" in css[hover_at:hover_at + 200] and "var(--accent)" in css[focus_at:focus_at + 200]
    for rule in (block, css[hover_at:hover_at + 200], css[focus_at:focus_at + 200]):
        assert "#" not in rule                                       # no raw hex in the added rules


def test_catalog_served_by_the_existing_static_handler_only():
    """No new route, no server edit: the fetch uses the same relative-asset convention as the
    page's own JS (index.html serves at /, the static handler passes any static file through),
    and neither server.py mentions the catalog or the helper."""
    src = PARAMTIPS.read_text(encoding="utf-8")
    assert 'fetch("param-catalog.v1.json")' in src
    assert CATALOG.is_file()
    srv = SERVER_PY.read_text(encoding="utf-8")
    assert "param-catalog" not in srv and "paramtips" not in srv
    # the catalog JSON is still exactly what the generator committed (version marker intact)
    assert '"catalog_version"' in CATALOG.read_text(encoding="utf-8")