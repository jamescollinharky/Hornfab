"""Brief authoring (GUI Briefs page: new-brief-from-scratch + exposed controls) and the
Compose wizard (typology-first run builder).

Offline reader-level pins:
  (a) the server's own ``load_brief`` (via D.save_user_brief) accepts EVERY key the new editor
      saves — verify_only, objective.version, driver.throat_angle_policy, target.freq_weights,
      and axisymmetric with a w != h envelope (mirroring examples/briefs/user/7040.yaml) — and
      nothing the editor sends is silently dropped on the round trip;
  (b) the shipped-name collision and bad-name refusals still hold;
  (c) list_briefs sees the saved user brief;
  (d) the Compose wizard's POST bodies map 1:1 onto jobs.build_argv's allow-listed kinds, and
      the campaign kind's budget/seeds reality (the GUI allow-list plumbs neither) is pinned so
      the wizard's no-override-fields choice stays honest.

Plus the app.js ES-module syntax gate, copied from tests/test_gui.py
(test_static_js_parses_as_an_es_module) so a syntax error is caught offline.

Also appended: the provenance-strip view layer of the GUI integration plan phases G1-G4
(docs/GUI_INTEGRATION_PLAN_2026-10-25.md, contracts C-1/C-2) - badge builder + run extractor +
restarts card + STEP inventory chips + qd caption + f11 caveat, executed for real via node (the
app.js import runs under the same DOM-shim pattern the mesh-quadrants tests use for view3d.js),
plus the view call-site wiring pinned by source checks (test_compose_view_is_wired style).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from hornlab_search.gui import jobs as J
from hornlab_search.gui.data import list_briefs, save_user_brief

ROOT = Path(__file__).resolve().parents[1]

# The exact shape the reworked Briefs editor builds (app.js ::showBriefDetail save payload):
# every schema key the form carries, left at defaults or edited, round-trips through the
# server-authoritative validation in config.py::load_brief.
FULL_EDITOR_PAYLOAD = {
    "name": "authoring_check",              # save_user_brief re-sets it from the name argument
    "description": "editor-built authoring smoke",
    "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 0, "throat_angle_policy": "pin"},
    "envelope": {"max_mouth_w_mm": 500, "max_mouth_h_mm": 400, "max_depth_mm": 250},  # w != h
    "symmetry": "axisymmetric",
    "source": {},
    "target": {
        "coverage_h_deg": 50, "coverage_v_deg": 50,
        "band_lo_hz": 500, "band_hi_hz": 12000,     # no 5500 clamp anywhere in the schema
        "di_target_db": None, "di_slope_target": 0, "z_min": 0,
        "freq_weights": {"band_hz": [[700.0, 1200.0, 1.5], [2000.0, 4000.0, 2.0]]},
    },
    "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.5},
    "verify_only": True,
    "objective": {"version": 2},
}


@pytest.fixture()
def brief_root(tmp_path):
    root = tmp_path / "repo"
    (root / "examples" / "briefs").mkdir(parents=True)
    return root


def test_save_user_brief_round_trips_every_editor_key(brief_root):
    """(a) The schema accepts ALL the editor keys — including axisymmetric with a w != h envelope
    like the shipped examples/briefs/user/7040.yaml — and nothing is silently dropped."""
    p = save_user_brief(brief_root, "authoring_check", FULL_EDITOR_PAYLOAD)
    assert p == brief_root / "examples" / "briefs" / "user" / "authoring_check.yaml"
    # save_user_brief validated the bytes through the CLI's real load_brief; assert the file
    # also lists and reads back key-for-key through the GUI reader.
    [saved] = [b for b in list_briefs(brief_root) if b["name"] == "authoring_check"]
    br = saved["brief"]
    assert saved["kind"] == "user"
    assert br["name"] == "authoring_check"
    assert br["description"] == "editor-built authoring smoke"
    assert br["verify_only"] is True
    assert br["objective"] == {"version": 2}
    assert br["driver"] == {"exit_radius_mm": 12.7, "exit_angle_deg": 0, "throat_angle_policy": "pin"}
    assert br["envelope"]["max_mouth_w_mm"] == 500 and br["envelope"]["max_mouth_h_mm"] == 400
    assert br["symmetry"] == "axisymmetric"          # legal with the w != h envelope above
    assert br["target"]["band_hi_hz"] == 12000       # saved exactly as typed, never clamped
    assert br["target"]["freq_weights"] == {"band_hz": [[700.0, 1200.0, 1.5], [2000.0, 4000.0, 2.0]]}
    assert br["target"]["z_min"] == 0 and br["target"]["di_target_db"] is None


def test_list_briefs_sees_the_saved_user_brief(brief_root):
    """(c) A brief saved through the editor's payload appears in the Briefs list as a user brief."""
    save_user_brief(brief_root, "authoring_check", FULL_EDITOR_PAYLOAD)
    names = {b["name"]: b for b in list_briefs(brief_root)}
    assert "authoring_check" in names
    assert names["authoring_check"]["kind"] == "user"
    assert names["authoring_check"]["path"] == "examples/briefs/user/authoring_check.yaml"
    assert names["authoring_check"]["brief"]["verify_only"] is True


def test_save_user_brief_refusals_still_hold(brief_root):
    """(b) Shipped-name collision and illegal names are refused; nothing is written."""
    shutil.copy(ROOT / "examples" / "briefs" / "axi_90x90_1in.yaml",
                brief_root / "examples" / "briefs" / "axi_90x90_1in.yaml")
    with pytest.raises(ValueError, match="is a shipped brief"):
        save_user_brief(brief_root, "axi_90x90_1in", dict(FULL_EDITOR_PAYLOAD, name="axi_90x90_1in"))
    with pytest.raises(ValueError, match="brief name"):
        save_user_brief(brief_root, "bad name!", dict(FULL_EDITOR_PAYLOAD))
    user_dir = brief_root / "examples" / "briefs" / "user"
    assert not user_dir.exists() or not list(user_dir.iterdir())


@pytest.mark.parametrize("name", ["app.js"])
def test_static_js_parses_as_an_es_module(name, tmp_path):
    """Same offline gate as test_gui.py: a syntax error in app.js blanks every view."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    src = ROOT / "hornlab_search" / "gui" / "static" / name
    mjs = tmp_path / (name + ".mjs")                    # .mjs: parse as a module, not CommonJS
    mjs.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([node, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]


def _job_root(tmp_path):
    """A minimal repo: one loadable config, one loadable brief (build_argv resolves --config and
    --brief to real files inside the repository — a path that does not exist is refused)."""
    root = tmp_path / "repo"
    (root / "examples" / "briefs").mkdir(parents=True)
    (root / "examples" / "typologies").mkdir(parents=True)
    (root / "examples" / "cfg.yaml").write_text("name: cfg\n")
    (root / "examples" / "typologies" / "conical.yaml").write_text("name: conical\n")
    shutil.copy(ROOT / "examples" / "briefs" / "axi_90x90_1in.yaml",
                root / "examples" / "briefs" / "axi_90x90_1in.yaml")
    return root, "examples/typologies/conical.yaml", "examples/briefs/axi_90x90_1in.yaml"


def test_compose_wizard_argv_shapes(tmp_path):
    """(d) The compose wizard's POST bodies map 1:1 onto the allow-listed kinds it uses
    (single config: dry-run/run/search; 2+ picks: campaign), read back from jobs.build_argv."""
    root, cfg, brf = _job_root(tmp_path)
    jm = J.JobManager(root, root / "runs")
    # single-config dry-run: {config, brief} -> run --config ... --dry-run --brief ... ; no GPU
    argv, gpu = jm.build_argv("dry-run", {"config": cfg, "brief": brf})
    assert argv == ["run", "--config", cfg, "--dry-run", "--brief", brf] and gpu is False
    # single-config run with an optional seed: {config, brief, cma_seed}
    argv, gpu = jm.build_argv("run", {"config": cfg, "brief": brf, "cma_seed": "7"})
    assert argv == ["run", "--config", cfg, "--brief", brf, "--cma-seed", "7"] and gpu is True
    # single-config search: {config, budget?, brief, cma_seed?} (blank budget -> engine default 60)
    argv, gpu = jm.build_argv("search", {"config": cfg, "brief": brf})
    assert argv == ["search", "--config", cfg, "--budget", "60", "--brief", brf] and gpu is True
    argv, _ = jm.build_argv("search", {"config": cfg, "budget": "120", "brief": brf})
    assert argv == ["search", "--config", cfg, "--budget", "120", "--brief", brf]
    # campaign: {brief, families, tier}; families come from the picked CATALOG names, comma-joined
    argv, gpu = jm.build_argv("campaign", {"brief": brf, "families": "conical,hypex", "tier": "screen"})
    assert argv == ["campaign", "--brief", brf, "--families", "conical,hypex", "--tier", "screen"] and gpu is True
    argv, gpu = jm.build_argv("campaign", {"brief": brf, "families": "conical", "tier": "dry-run"})
    assert gpu is False and argv[-2:] == ["--tier", "dry-run"]
    # engine refusals the wizard surfaces verbatim: bad families spec, missing brief
    with pytest.raises(J.JobError, match="families"):
        jm.build_argv("campaign", {"brief": brf, "families": "Conical X", "tier": "screen"})
    with pytest.raises(J.JobError, match="campaign needs a brief"):
        jm.build_argv("campaign", {"families": "conical", "tier": "screen"})


def test_campaign_budget_and_seeds_are_not_gui_plumbed(tmp_path):
    """Pins the allow-list reality behind the wizard's UI choice: jobs.build_argv("campaign")
    plumbs ONLY brief/families/tier, so --seeds/--budget overrides CANNOT reach the engine from
    the GUI — campaign runs use the engine's budget_for_tier defaults. The compose wizard
    therefore ships budget_for_tier captions and NO override fields (fields that silently
    vanish would lie). If a later lane plumbs seeds/budget, update this pin and the wizard
    together."""
    root, cfg, brf = _job_root(tmp_path)
    jm = J.JobManager(root, root / "runs")
    argv, _ = jm.build_argv("campaign", {"brief": brf, "families": "conical", "tier": "screen",
                                         "budget": 99, "seeds": 3, "cma_seed": 5})
    assert argv == ["campaign", "--brief", brf, "--families", "conical", "--tier", "screen"]
    assert not any(v in {"--budget", "--seeds", "--cma-seed"} for v in argv)


def test_compose_view_is_wired():
    """The wizard is reachable: route + nav item + view function all exist in the static files."""
    app = (ROOT / "hornlab_search" / "gui" / "static" / "app.js").read_text(encoding="utf-8")
    idx = (ROOT / "hornlab_search" / "gui" / "static" / "index.html").read_text(encoding="utf-8")
    assert "function viewCompose" in app
    assert re.search(r"re: /\^#\\/compose\$/", app)          # route registered
    assert 'href="#/compose"' in idx and 'aria-label="Compose"' in idx
    assert re.search(r'h === "#/compose" && hash === "#/compose"', app)   # nav highlight
    # the wizard reuses the briefs editor (mount) and the stem-matching loader, not copies
    assert "opts.mount" in app and "function findBriefByFile" in app and "function newBriefDraft" in app


# ── Provenance strips (GUI plan phases G1–G4; contracts C-1/C-2) ─────────────────────────
# app.js renders the badge matrix (§7 badges, non-default only, key-path tooltips), the restart
# schedule card (C-1 restarts/restart_dirs), the qd atlas caption (C-1 qd), the compare mixed_keys
# banner + DI guard twin (C-2 group_a/group_b) and the STEP inventory chips (C-1 step_files_detail).
# Branch behavior is executed for real by node (below), the same module-import pattern
# tests/test_gui_mesh_quadrants.py uses for view3d.js::mirrorMesh; the view call sites are pinned
# by source checks (test_compose_view_is_wired style) since the views need the browser DOM.

APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"


def test_provenance_views_are_wired():
    """Every strip lives inside its committed view — no new nav item, no new route, index.html
    untouched by these phases."""
    src = APPJS.read_text(encoding="utf-8")
    # G1 run detail: header badge strip fed by the reader's solve_group + f11 caveat (§3.4)
    assert "function runProvenanceGroup(d)" in src and "function renderProvenanceBadges(group" in src
    assert 'renderProvenanceBadges(prov.group, "", prov.tips)' in src
    assert "typeof d.solve_group" in src and 'tips[k] = "solve_group." + k' in src
    assert "typeof d.search_restarts" in src and '"run_detail.search_restarts.mode"' in src
    assert "f11CaveatHtml(d)" in src and "best.scalars.f11_hz" in src
    # G2: restart card below the KPIs, header reads search_restarts, honest empty state kept
    assert "restartScheduleHtml(d, id)" in src
    assert "run.json predates the restarts block" in src
    assert "carries no valid" in src                      # fallback only for the absent case
    # G2 atlas: qd caption read from the run payload, rendered in the header (canvas untouched)
    assert "qdProvenanceCaption(QD)" in src
    assert '"/api/run/" + encodeURIComponent(id)' in src
    # G3 compare: server group objects through the same builder, mixed banner, DI guard twin
    assert "renderProvenanceBadges(grp, prefix)" in src
    assert 'sideBadgeRow("A", gA, "group_a.")' in src and 'sideBadgeRow("B", gB, "group_b.")' in src
    assert "const mixedBanner = mixed.length" in src and "These runs differ in:" in src
    assert "const dsA = dA.di_source, dsB = dB.di_source;" in src
    assert 'dsA !== "balloon"' in src and 'dsB !== "balloon"' in src
    assert "DI: cuts estimate — not comparable" in src
    # G4 chips: the UNCHANGED step_files name list + step_files_detail matched by name
    assert "function stepInvByName(detail)" in src and "function stepChipHtml(name, inv, id)" in src
    assert "stepInvByName(detail)" in src and "renderFiles(d.step_files, d.step_files_detail)" in src
    # deferred items (this round): CAD provenance + direct pycma-log chips — reader-coupled adds
    assert 'g.cad_route === true' in src and "cad STEP" in src           # geometry-source badge
    assert "tool_sha256" in src and 'tool_path' in src                   # CAD chip contract fields
    assert "d.cma_files" in src                                          # reader listing read defensively
    assert "pycma logs (raw, never parsed; each file serves by its exact name):" in src
    # the pure helpers are exported for the offline node test (view3d.js::mirrorMesh precedent)
    assert "export { runProvenanceGroup, renderProvenanceBadges, restartScheduleHtml, stepChipHtml," in src
    assert "stopAffordanceFor, stopRegionHtml, currentRunCard," in src
    assert "toolbarPillFor, toolbarPillHtml, resumeArgsFor, resumeableSearchJob };" in src


def test_stop_run_affordance_is_wired():
    """Owner request "a button that stops the current run": Status page — the decision is by job
    OWNERSHIP (JobManager only knows GUI jobs; one GPU at a time), the two-step arm runs without a
    confirm() dialog and states the honest post-action truth; the Launch row keeps its existing
    behavior with matching copy; the current-run card refreshes on the poll."""
    src = APPJS.read_text(encoding="utf-8")
    jobs_fetch_ct = src.count("/api/jobs")
    assert src.count("[data, jobs] = await Promise.all([") >= 1 and jobs_fetch_ct >= 2
    assert "renderStatus(data, jobs)" in src and "updateStatusInPlace(data, jobs)" in src
    # the decision helper + the region builder are pure, wired, and node-tested via the export
    assert "function stopAffordanceFor(jobs, lock)" in src and "function stopRegionHtml(aff)" in src
    assert "stopAffordanceFor(jobs, lock)" in src          # called at render AND refresh
    assert 'cc.innerHTML = currentRunCard(data.current, aff); wireStopButton(aff);' in src  # live poll
    assert "currentRunCard(cur, aff)" in src               # card renders inside, layout unchanged
    assert 'id="st-current-card"' in src
    # three states, exact text (Confirm stop is the arm-state literal, not an HTML fragment)
    assert ">Stop run</button>" in src and '"Confirm stop"' in src
    assert "click again to confirm — the job's process tree is killed and a gpu-clean pass runs" in src
    assert "stop requested — the run dir records the stop; wait for the job to exit + a gpu-clean pass" in src
    assert "Kills the externally-started run that holds our GPU lock" in src   # external = pid-targeted kill (owner 2026-10-25)
    assert "no run folder written yet" in src              # startup-window card, no invented numbers
    # the cancel actually targets the live endpoint; no browser confirm() on the status page
    assert '"/api/job/" + aff.job.id + "/cancel"' in src
    assert "wireStopButton" in src and "aria-pressed" in src
    # Launch row: same semantics, existing behavior kept (confirm() dialog stays; copy aligned)
    assert 'title="Stops the run: the job\'s process tree is killed and a gpu-clean pass runs after GPU jobs">Stop run</button>' in src
    assert "Stop requested — the job is killed and a gpu-clean pass runs after GPU jobs." in src
    assert 'confirm("Cancel this job?")' in src            # Launch behavior untouched


def test_balloon_entry_point_already_wired():
    """W6 (26a1de1) surfaces the balloon where the owner needs it — verified, nothing added this
    round: the run-detail buttons row carries the entry next to QD atlas / 3D view, the dedicated
    3D page links it, and the route is registered — so no second entry point was built."""
    src = APPJS.read_text(encoding="utf-8")
    assert "import { viewBalloon } from \"./balloon.js\";" in src
    assert re.search(r"re: /\^#\\/run\\/\(\.\+\)\\/balloon\$/", src)          # route registered
    assert 'href="#/run/${esc(id)}/balloon" title="W6 Balloon:' in src           # run-detail entry
    assert src.count('href="#/run/${esc(id)}/balloon"') >= 2                     # + the 3D view page
    assert "◉ Balloon 3D" in src


# The node script: imports app.js under an import-time DOM shim (app.js touches document/window at
# module scope; location stays on the synchronous view so no fetch happens), then executes every
# badge/card/chip branch. Same wrapper approach as tests/test_gui_mesh_quadrants.py.
_PROV_SCRIPT = r'''
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
const { runProvenanceGroup, renderProvenanceBadges, restartScheduleHtml, stepChipHtml,
        stepInvByName, qdProvenanceCaption, f11CaveatHtml,
        stopAffordanceFor, stopRegionHtml, currentRunCard,
        toolbarPillFor, toolbarPillHtml, resumeArgsFor, resumeableSearchJob,
        continueRunAvailable, continueRunArgs } = app;
assert.equal(typeof stopAffordanceFor, "function");
assert.equal(typeof stopRegionHtml, "function");
assert.equal(typeof renderProvenanceBadges, "function");
assert.equal(typeof toolbarPillFor, "function");
assert.equal(typeof toolbarPillHtml, "function");
assert.equal(typeof resumeArgsFor, "function");
assert.equal(typeof resumeableSearchJob, "function");

// badge builder: non-default only + exact key-path tooltips
assert.equal(renderProvenanceBadges({}), "");
assert.equal(renderProvenanceBadges(null), "");
let h = renderProvenanceBadges({ backend: "bempp_cpu" });
assert.ok(h.includes(">bempp_cpu</span>"), h);
assert.ok(h.includes(`title="backend = bempp_cpu"`), h);
h = renderProvenanceBadges({ backend: "beat_cuda" }, "group_a.");
assert.ok(h.includes(`title="group_a.backend = beat_cuda"`), h);
// C-2 identity baseline: backend + freqs_hz always render on compare group sides
h = renderProvenanceBadges({ backend: "beat_cuda", freqs_hz: { mode: "screen", band_lo_hz: 300, band_hi_hz: 12000 } }, "group_b.");
assert.match(h, /grid screen 300–12000 Hz/);
assert.ok(h.includes("group_b.freqs_hz = ") && h.includes("&quot;mode&quot;:&quot;screen&quot;"), h);
h = renderProvenanceBadges({ freqs_hz: { mode: "screen", band_lo_hz: 300, band_hi_hz: 12000, verify_points_per_octave: 8 } });
assert.match(h, /8\/oct verify/);
assert.equal(renderProvenanceBadges({ freqs_hz: {} }), "");       // partial identity: no badge
h = renderProvenanceBadges({ cuda_fused: true });
assert.ok(h.includes(">fused CUDA</span>") && h.includes(`title="cuda_fused = true"`), h);
h = renderProvenanceBadges({ near_correction: true, solve_precision: "double" });
assert.match(h, /near-corrected · double/);
h = renderProvenanceBadges({ near_correction: true });
assert.match(h, /near-corrected/);
assert.ok(!h.includes("· double"));                  // precision never claimed when absent
h = renderProvenanceBadges({ solve_precision: "double" });
assert.match(h, /double precision/);
h = renderProvenanceBadges({ source_profile_alpha: 0.5, source_profile: "j0_radial" });
assert.match(h, /source plug α=0\.5 \(j0_radial\)/);
assert.ok(h.includes(`title="source_profile_alpha = 0.5"`), h);
assert.equal(renderProvenanceBadges({ source_profile_alpha: 0 }), "");  // α=0 is the default
h = renderProvenanceBadges({ mesh_policy: "band_split_v1", band_edges_hz: [3000, 6000] });
assert.match(h, /band-split 3\/6 k/);
assert.ok(h.includes(`title="mesh_policy = band_split_v1"`), h);
h = renderProvenanceBadges({ rear_res_factor: 2 });
assert.match(h, /rear ×2/);
assert.equal(renderProvenanceBadges({ rear_res_factor: 1 }), "");   // default: no badge
h = renderProvenanceBadges({ mounting: { type: "enclosure", depth_mm: 250 } });
assert.match(h, /enclosure d=250 mm/);
h = renderProvenanceBadges({ objective_version: 2 });
assert.match(h, /J v2/);
assert.equal(renderProvenanceBadges({ objective_version: 1 }), ""); // v1 default: unlabelled
h = renderProvenanceBadges({ qd_algorithm: "cma_me" });
assert.match(h, /CMA-ME/);
h = renderProvenanceBadges({ restarts_count: 3, restarts_mode: "bipop" });
assert.match(h, /BIPOP ×3/);
h = renderProvenanceBadges({ restarts_count: 3 });
assert.match(h, /restarts ×3/);
assert.ok(!h.includes("IPOP"));                      // the mode is never invented when unknown
assert.match(renderProvenanceBadges({ source_motion: "axial" }), /source motion axial/);

// run-provenance extraction: read straight from the reader's solve_group (the same fingerprint
// /api/compare exposes) + the C-1 restarts array + the live search_restarts schedule
let p = runProvenanceGroup({});
assert.deepEqual(p.group, {});                       // older payload / no solve_group: nothing fabricated
assert.deepEqual(p.tips, {});
const RE = { index: 0, popsize: 10, sigma0: 0.25, n_new_in_restart: 59, evals_in_restart: 59, stop: "budget" };
// identity-only solve_group (a plain beat_cuda run): exactly the two baseline keys
const IDENTITY = { backend: "beat_cuda", freqs_hz: { mode: "screen", band_lo_hz: 300, band_hi_hz: 12000 } };
p = runProvenanceGroup({ solve_group: { backend: IDENTITY.backend, freqs_hz: IDENTITY.freqs_hz } });
assert.deepEqual(Object.keys(p.group), ["backend", "freqs_hz"]);
assert.equal(p.group.backend, "beat_cuda");
assert.deepEqual(p.group.freqs_hz, IDENTITY.freqs_hz);
assert.equal(p.tips.backend, "solve_group.backend");
assert.equal(p.tips.freqs_hz, "solve_group.freqs_hz");
// the schedule: restarts array -> count; search_restarts -> mode/max (absent = no invented mode)
p = runProvenanceGroup({ solve_group: IDENTITY, restarts: [RE], search_restarts: { mode: "ipop", max: 3 } });
assert.equal(p.group.restarts_count, 1);
assert.equal(p.group.restarts_mode, "ipop");
assert.equal(p.group.restarts_max, 3);
assert.equal(p.tips.restarts_mode, "run_detail.search_restarts.mode");
assert.equal(p.tips.restarts_count, "run.json.restarts");
p = runProvenanceGroup({ solve_group: IDENTITY, restarts: [RE] });
assert.equal(p.group.restarts_count, 1);
assert.ok(!("restarts_mode" in p.group) && !("restarts_max" in p.group));
// qd_algorithm arrives inside solve_group now (the raw qd block stays the atlas caption's source)
p = runProvenanceGroup({ solve_group: { backend: "beat_cuda", qd_algorithm: "cma_me" } });
assert.equal(p.group.qd_algorithm, "cma_me");
// every non-default fingerprint key reaches the badge group, tooltip naming solve_group.<key>:
p = runProvenanceGroup({ solve_group: { backend: "beat_cpu", cuda_fused: true, source_motion: "axial",
                       source_profile_alpha: 0.5, near_correction: true, solve_precision: "double",
                       rear_res_factor: 2, mesh_policy: "band_split_v1", band_edges_hz: [3000, 6000],
                       mounting: { type: "enclosure", depth_mm: 250 }, objective_version: 2,
                       qd_algorithm: "cma_me" } });
const rg2 = p.group;
assert.equal(rg2.backend, "beat_cpu");
assert.equal(rg2.cuda_fused, true);
assert.equal(rg2.source_motion, "axial");
assert.equal(rg2.source_profile_alpha, 0.5);
assert.equal(rg2.near_correction, true);
assert.equal(rg2.solve_precision, "double");
assert.equal(rg2.rear_res_factor, 2);
assert.equal(rg2.mesh_policy, "band_split_v1");
assert.deepEqual(rg2.band_edges_hz, [3000, 6000]);
assert.deepEqual(rg2.mounting, { type: "enclosure", depth_mm: 250 });
assert.equal(rg2.objective_version, 2);
assert.equal(rg2.qd_algorithm, "cma_me");
for (const k of Object.keys(rg2)) assert.ok(p.tips[k].startsWith("solve_group."), k);

// restart schedule card branches (honest empty states; nothing invented)
assert.equal(restartScheduleHtml({}, "R"), "");
assert.equal(restartScheduleHtml({ restart_dirs: [] }, "R"), "");
let c = restartScheduleHtml({ id: "R", restart_dirs: ["cma/restart_0"] }, "R");
assert.match(c, /Restart schedule/);
assert.match(c, /run\.json predates the restarts block/);
assert.match(c, /cma\/restart_0/);
assert.match(c, /\/runs\/R\/cma\//);
c = restartScheduleHtml({ id: "R", restarts: [RE] }, "R");
assert.match(c, /restart 0/);
assert.match(c, /popsize 10/);
assert.match(c, /σ0 0\.25/);
assert.match(c, /evals 59/);
assert.match(c, /stop budget/);
assert.match(c, /run\.json\.restarts/);              // rows named with their source path
assert.match(c, /carries no valid/);                 // absent search_restarts: the honest fallback
assert.ok(!c.includes("mode ipop"));                 // no invented mode/max
c = restartScheduleHtml({ id: "R", restarts: [RE], search_restarts: { mode: "ipop", max: 2 } }, "R");
assert.match(c, /mode ipop · max 2/);
assert.match(c, /search_restarts/);                  // header names its read path
assert.ok(!c.includes("carries no valid"));
assert.match(c, /run\.json\.restarts\[0\]\.popsize/);

// STEP chips: step_files stays the name list; inventory matched by name from step_files_detail
const INV = { tool: "tools/cad/multicell.py", tool_sha: "0123456789abcdef0123456789abcdef01234567",
              faces: [{ label: "driver", count: 1 }, { label: "wall", count: 9 }],
              solids: 2, closed: true, grid: ["3x3"] };
assert.equal(stepInvByName(undefined).size, 0);
assert.equal(stepInvByName(null).size, 0);
const mInv = stepInvByName([{ name: "horn_rank1_0001.step", inventory: INV },
                            { name: "plain.step", inventory: null }, { junk: 1 }]);
assert.equal(mInv.get("horn_rank1_0001.step"), INV);
assert.equal(mInv.get("plain.step"), null);
assert.equal(mInv.size, 2);
const plain = stepChipHtml("horn_rank1_0001.step", null, "R");
assert.ok(plain.includes('href="/runs/R/step/horn_rank1_0001.step"'), plain);
assert.match(plain, /↓ rank1/);
assert.ok(!plain.includes("driver="));               // no inventory: chip unchanged (silent absence)
const chip = stepChipHtml("horn_rank1_0001.step", INV, "R");
assert.match(chip, /3×3 STEP/);
assert.match(chip, /driver=1/);
assert.match(chip, /wall=9/);
assert.match(chip, /tool 01234567/);                 // short sha on the face
assert.ok(chip.includes('href="/runs/R/step/horn_rank1_0001.step"'), chip);
assert.ok(chip.includes("horn_rank1_0001.step.inventory.json"), chip);  // tooltip names the sidecar

// qd provenance caption: every known key, meanings as tooltips, honest absences
assert.equal(qdProvenanceCaption(null), "");
assert.equal(qdProvenanceCaption(undefined), "");
assert.equal(qdProvenanceCaption({}), "");
const QD = { algorithm: "cma_me", bins: [16, 16], coverage: 0.05078125,
             descriptors: { h: "mean_bw_h_deg", v: "mean_bw_v_deg" },
             descriptor_h_meaning: "mean of MetricSet.bw_h_deg",
             descriptor_v_meaning: "mean of MetricSet.bw_v_deg",
             non_cached: 60, occupied_bins: 13, ranges: { h: [0, 180], v: [0, 180] },
             total_bins: 256, total_evals: 60 };
const cap = qdProvenanceCaption(QD);
assert.match(cap, /atlas provenance \(run\.json\.qd\)/);
assert.match(cap, /cma_me/);
assert.match(cap, /coverage 13\/256 bins/);
assert.match(cap, /60 evaluations \(60 non-cached\)/);
assert.ok(cap.includes("mean of MetricSet.bw_h_deg"), cap);

// f11 caveat: the fixed sentence, ONLY when band_hi > f11 AND f11 is known; n_hz fallback named
assert.equal(f11CaveatHtml({ target: { band_hi_hz: 12000 } }), "");
assert.equal(f11CaveatHtml({ target: { band_hi_hz: 5500 }, best: { scalars: { f11_hz: 7914 } } }), "");
let note = f11CaveatHtml({ target: { band_hi_hz: 12000 }, best: { scalars: { f11_hz: 7914 } } });
assert.ok(note.includes("8–12 kHz compares GEOMETRIES, not drivers (above f11 the source is an idealized rigid cap)"), note);
assert.match(note, /7\.9 kHz/);
assert.ok(note.includes("best.scalars.f11_hz"), note);
assert.ok(note.includes("target.band_hi_hz"), note);
note = f11CaveatHtml({ target: { band_hi_hz: 12000 }, best: { scalars: { n_hz: 7914 } } });
assert.ok(note.includes("best.scalars.n_hz"), note);
assert.ok(!note.includes("f11_hz"), note);

// cad badge (deferred item, reader lands solve_group.cad_route): renders exactly when the key
// arrives, geometry-source slot, same key-path tooltip as every other badge
h = renderProvenanceBadges({ cad_route: true });
assert.match(h, /cad STEP/);
assert.ok(h.includes(`title="cad_route = true"`), h);
assert.equal(renderProvenanceBadges({}), "");

// CAD-era STEP chip (contract inventory {faces, solids, closed, tool_sha256, tool_path}):
// renders ONLY the facts that arrive, joined " · " like the badge summary spec
const CAD = { faces: [{ label: "driver", count: 1 }, { label: "wall", count: 9 }],
              solids: 2, closed: true, tool_sha256: "fedcba9876543210fedcba9876543210fedcba98",
              tool_path: "tools/cad/multicell.py" };
const cadChip = stepChipHtml("horn_rank1_0001.step", CAD, "R");
assert.match(cadChip, /driver=1 · wall=9 · solid ✓ · tool fedcba98/);
assert.ok(!cadChip.includes("STEP"), cadChip);              // no grid field -> no invented segment
assert.ok(cadChip.includes("tool_sha256=fedcba9876543210fedcba9876543210fedcba98"), cadChip);
assert.ok(cadChip.includes("tool_path=tools/cad/multicell.py"), cadChip);
assert.ok(cadChip.includes("faces="), cadChip);             // tooltip names every present key
// open/not-closed solids disclose as solid ✗; closed absent + solids present -> solids N
assert.match(stepChipHtml("a.step", { closed: false }, "R"), /solid ✗/);
assert.match(stepChipHtml("a.step", { solids: 3 }, "R"), /solids 3/);
// an inventory object carrying nothing renderable stays the plain chip (silent, honest)
assert.equal(stepChipHtml("horn_rank1_0001.step", {}, "R"), plain);

// restart card gains the per-FILE pycma-log chips when the reader's cma_files listing arrives
const CMA = [
  { path: "cma/restart_0/outcmaes_progress.txt", name: "outcmaes_progress.txt", size: 12345 },
  { path: "cma/restart_1/outcmaes_xrecentbest.dat", name: "outcmaes_xrecentbest.dat", size: 640 },
];
const withLogs = restartScheduleHtml({ id: "R", restarts: [RE], cma_files: CMA }, "R");
assert.match(withLogs, /pycma logs \(raw, never parsed; each file serves by its exact name\):/);
assert.match(withLogs, /href="\/runs\/R\/cma\/restart_0\/outcmaes_progress\.txt"/);   // live C-5 route
assert.match(withLogs, /href="\/runs\/R\/cma\/restart_1\/outcmaes_xrecentbest\.dat"/);
assert.match(withLogs, />↓ outcmaes_progress\.txt</);        // the listed file name, not a guess
assert.match(withLogs, /12345 bytes/);                       // size in the tooltip
// junk/absent listings never fabricate chip links: bad records filtered, absent/[] keep the caption
assert.ok(!restartScheduleHtml({ id: "R", restarts: [RE], cma_files: [{ junk: 1 }, {}, { path: "", name: "x" }] }, "R")
          .includes('href="/runs/R/'), "bad cma_files records must not produce chips");
// listing present but empty: the reader RAN — honest "nothing in the cma tree" caption, no stale note
const emptyList = restartScheduleHtml({ id: "R", restarts: [RE], restart_dirs: ["cma/restart_0"], cma_files: [] }, "R");
assert.match(emptyList, /pycma logs:/);
assert.ok(!emptyList.includes("the API lists the directories"), emptyList);   // listing exists now
// listing absent (reader not landed yet): the committed URL-shape caption, parenthetical kept
assert.match(restartScheduleHtml({ id: "R", restarts: [RE], restart_dirs: ["cma/restart_0"] }, "R"),
             /the API lists the directories, not the file names/);
// the empty state (logs present, no schedule entries) shows the chips too
const olderLogs = restartScheduleHtml({ id: "R", restart_dirs: ["cma/restart_0"], cma_files: CMA }, "R");
assert.match(olderLogs, /run\.json predates the restarts block/);
assert.match(olderLogs, /href="\/runs\/R\/cma\/restart_0\/outcmaes_progress\.txt"/);

// stop-run affordance (Status page): the ownership rule and the exact copy of all three states
const JGUI = { id: "job1", kind: "search", argv: ["search", "--config", "a.yaml", "--budget", "60"], gpu: true, status: "running" };
const JGPU2 = { id: "job0", kind: "run", argv: ["run", "--config", "x.yaml"], gpu: true, status: "running" };
const JCPU = { id: "job2", kind: "report", argv: ["report", "--run", "r"], gpu: false, status: "running" };
const JDONE = { id: "job3", kind: "run", argv: ["run", "--config", "b.yaml"], gpu: true, status: "done" };
let aff = stopAffordanceFor([JGUI], null);
assert.equal(aff.state, "gui-cancel");                  // a GUI GPU job IS the current run (one GPU at a time)
assert.equal(aff.job.id, "job1");
assert.equal(aff.note, "");
assert.equal(stopAffordanceFor([JCPU], null).state, "idle");      // a running CPU job is not the GPU run
assert.equal(stopAffordanceFor([JDONE], null).state, "idle");    // done/cancelled jobs are ignored
assert.equal(stopAffordanceFor([], null).state, "idle");
assert.equal(stopAffordanceFor(undefined, undefined).state, "idle");  // nothing running: absence is honest
aff = stopAffordanceFor(null, { pid: 4242, command: "hornlab-search search --config c.yaml", alive: true });
assert.equal(aff.state, "external");                    // lock held, no GUI GPU job = a terminal run
assert.equal(aff.lock.pid, 4242);
aff = stopAffordanceFor([null, { id: "x", kind: "run", gpu: false, status: "running" }, JGPU2, JGUI], null);
assert.equal(aff.state, "gui-cancel");
assert.equal(aff.job.id, "job1");                       // the newest running GPU job owns the GPU
assert.ok(aff.note.includes("2 GUI GPU jobs"), aff.note);
// the region copy — gui-cancel is the Stop button; external (owner 2026-10-25) is a pid-targeted
// KILL run button: the GUI now kills exactly the pid recorded in OUR gpu lock file, never arbitrary
assert.equal(stopRegionHtml({ state: "idle" }), "");
assert.equal(stopRegionHtml(null), "");
const extStop = stopRegionHtml({ state: "external", lock: { pid: 4242, command: "hornlab-search search --config c.yaml" } });
assert.match(extStop, /<button class="btn danger" id="btn-kill-run"/);
assert.match(extStop, />Kill run<\/button>/);
assert.match(extStop, /Kills the externally-started run that holds our GPU lock: pid 4242/);
assert.ok(extStop.includes("external run · pid 4242"), extStop);   // the kill is pid-targeted, traceable
assert.match(extStop, /id="st-kill-msg"/);
const guiStop = stopRegionHtml({ state: "gui-cancel", job: JGUI });
assert.match(guiStop, /<button class="btn danger" id="btn-stop-run"/);
assert.match(guiStop, />Stop run<\/button>/);           // face label
assert.match(guiStop, /GUI job job1 · search · --config a\.yaml --budget 60/);  // kind + argv tail
assert.ok(guiStop.includes("Stops the run: the job's process tree is killed"), guiStop);
// the card without a run folder yet (startup window): minimal, no invented progress numbers
const card0 = currentRunCard(null, { state: "gui-cancel", job: JGUI });
assert.match(card0, /Running now/);
assert.match(card0, /GPU job search — --config a\.yaml --budget 60/);
assert.match(card0, /no run folder written yet/);
assert.ok(!card0.includes("progress-bar"), card0);
assert.equal(currentRunCard(null, { state: "idle" }), "");
assert.equal(currentRunCard(null, null), "");

// toolbar run-control pill (nav, every view): the decision matrix behind toolbarPillFor
// Resume contract (landed jobs.py): --resume takes a RUN ID (a bare true is refused), so the run id
// is sourced from the stopped job's own log and validated against the /api/runs summaries.
const JRUN = { id: "j9", kind: "run", argv: ["run", "--config", "r.yaml"], gpu: true, status: "running" };
const JST1 = { id: "a1", kind: "search", argv: ["search", "--config", "examples/briefs/x.yaml", "--budget", "500"], gpu: true,
               status: "cancelled", log_tail: ["run dir: runs/20261025T090000Z-search-abc123", "eval 99 ok"] };
const JST2 = { id: "b2", kind: "search", argv: ["search", "--config", "y.yaml"], gpu: true, status: "failed", returncode: 1,
               log_tail: ["run dir: runs/20261025T090000Z-search-abc123", "run dir: runs/20261024T010000Z-search-789abc"] };
const JRS = { id: "c3", kind: "search", argv: ["search", "--config", "z.yaml"], gpu: true, status: "ended (GUI restarted)" };
const JOKD = { id: "d4", kind: "search", argv: ["search", "--config", "o.yaml"], gpu: true, status: "done" };
const RUNV = { id: "20261025T090000Z-search-abc123", mode: "verify", budget: 500, n: 99 };
const RUNF = { id: "20261025T090000Z-search-abc123", mode: "screen", budget: 100, n: 100 };   // budget exhausted: finished
const RUNNB = { id: "20261024T010000Z-search-789abc", budget: null, n: 7 };                    // no budget recorded
assert.equal(toolbarPillFor([], null, []).state, "idle");
assert.equal(toolbarPillFor(undefined, undefined, undefined).state, "idle");   // nothing known: renders nothing
assert.equal(toolbarPillFor([JOKD], null, [RUNV]).state, "idle");              // finished normally: no offer
assert.equal(toolbarPillFor([JRS], null, [RUNV]).state, "idle");               // post-restart state unknown: never offered
assert.equal(resumeableSearchJob(JOKD), false);
assert.equal(resumeableSearchJob(null), false);
assert.equal(resumeableSearchJob({ kind: "run", status: "cancelled" }), false);
assert.equal(resumeableSearchJob(JST2), true);
let tp = toolbarPillFor([JST1], null, [RUNV]);
assert.equal(tp.state, "resume");
assert.equal(tp.job.id, "a1");
assert.deepEqual(tp.args, { resume: "20261025T090000Z-search-abc123", mode: "verify" });   // mode carried: no screen rewrite
assert.equal(toolbarPillFor([JST1], null, []).args, null);          // runs list empty: cannot validate a run id
assert.equal(toolbarPillFor([JST1], null, undefined).args, null);   // runs not polled yet: degrade, never guess
assert.equal(toolbarPillFor([JST1], null, [RUNF]).args, null);      // budget exhausted = finished: pill offers nothing
tp = toolbarPillFor([JST2, JST1], null, [RUNV, RUNNB]);
assert.equal(tp.job.id, "b2");                     // the newest stopped search wins, list-order-independent
assert.deepEqual(tp.args, { resume: "20261025T090000Z-search-abc123", mode: "verify" });  // log names two IDs: newest-backed wins
assert.deepEqual(resumeArgsFor(JST1, [{ id: "20261025T090000Z-search-abc123" }]), { resume: "20261025T090000Z-search-abc123" });
assert.deepEqual(resumeArgsFor(JST2, [RUNNB]), { resume: "20261024T010000Z-search-789abc" });  // budget null: still resumable
assert.equal(resumeArgsFor(JST1, [RUNF]), null);
assert.equal(resumeArgsFor(null, [RUNV]), null);
assert.equal(resumeArgsFor(JRUN, [RUNV]), null);   // resume is search-only
assert.equal(resumeArgsFor(JRS, [RUNV]), null);    // "ended (GUI restarted)" is never resumeable
assert.equal(resumeArgsFor({ kind: "search", log_tail: ["no run id here"] }, [RUNV]), null);
assert.equal(resumeArgsFor(JST1, undefined), null);
assert.equal(toolbarPillFor([JRUN], null, [RUNV]).state, "stop");      // a running GUI GPU job beats resume
assert.equal(toolbarPillFor([JST1, JRUN], null, [RUNV]).state, "stop");
assert.equal(toolbarPillFor([JST1, JRUN], null, [RUNV]).job.id, "j9");
assert.equal(toolbarPillFor([JST1], { alive: true, pid: 7, command: "x" }, [RUNV]).state, "external");  // foreign lock beats resume
assert.equal(toolbarPillFor([JST1, JCPU], null, [RUNV]).state, "resume");   // only a CPU job running: resume still holds
// pill HTML: exact faces + ids + honest absences; a foreign run is never a button
assert.match(toolbarPillHtml({ state: "idle" }), /no run in progress/);   // ALWAYS-visible pill: idle is a visible indicator, never an empty holder
assert.doesNotMatch(toolbarPillHtml({ state: "idle" }), /<button/);       // and idle offers no button
assert.match(toolbarPillHtml(null), /no run in progress/);   // null-safe: same honest idle face
const extPill = toolbarPillHtml({ state: "external", lock: { pid: 4242, command: "hornlab-search search --config c.yaml" } });
assert.match(extPill, /<button class="btn danger" id="tb-kill-run"/);
assert.match(extPill, />■ Kill run<\/button>/);
assert.match(extPill, /Kills the externally-started run that holds our GPU lock: pid 4242/);
assert.ok(extPill.includes("external run · pid 4242"), extPill);
assert.ok(extPill.includes('id="tb-kill-msg"'), extPill);
const stopPill = toolbarPillHtml({ state: "stop", job: JRUN });
assert.match(stopPill, /<button class="btn danger" id="tb-stop-run"/);
assert.match(stopPill, />■ Stop<\/button>/);
assert.ok(stopPill.includes("Stops the run: process tree killed + gpu-clean"), stopPill);
assert.match(stopPill, /job j9 · run/);
assert.ok(stopPill.includes('id="tb-stop-msg"'), stopPill);
assert.match(toolbarPillHtml({ state: "stop", job: JRUN, note: "2 GUI GPU jobs are running" }), /2 GUI GPU jobs are running/);
const resPill = toolbarPillHtml({ state: "resume", job: JST1, args: { resume: "20261025T090000Z-search-abc123", mode: "verify" } });
assert.match(resPill, /<button class="btn primary" id="tb-resume-run"/);
assert.match(resPill, />▶ Resume search<\/button>/);
assert.match(resPill, /job a1 · resume 20261025T090000Z-search-abc123/);
assert.ok(resPill.includes('id="tb-resume-msg"'), resPill);
assert.match(resPill, /budget is per invocation/);
const degPill = toolbarPillHtml({ state: "resume", job: { id: "f6", kind: "search" }, args: null });
assert.ok(!degPill.includes("<button"), degPill);          // degraded: a note, not a broken button
assert.match(degPill, /no resumable run folder/);

// Continue-run helpers (run-detail "Continue this run"): availability requires a search command;
// the args builder adds N NEW evals on the stored config — no --config, no --max-evals, mode only
// when the run declares one, and the input run is never mutated.
assert.equal(typeof continueRunAvailable, "function");
assert.equal(typeof continueRunArgs, "function");
assert.equal(continueRunAvailable({ command: "hornlab-search search --config x --budget 40" }), true);
assert.equal(continueRunAvailable({ command: "  hornlab-search search --config x --budget 40" }), true);
assert.equal(continueRunAvailable({ command: "hornlab-search search --config x --budget 40\t\n" }), true);
assert.equal(continueRunAvailable({ command: "hornlab-search run --config x" }), false);
assert.equal(continueRunAvailable({}), false);
assert.equal(continueRunAvailable(null), false);
assert.equal(continueRunAvailable(undefined), false);
assert.equal(continueRunAvailable({ command: 5 }), false);

const CRID = "20261025T090000Z-search-abc123";
// strings and numbers both accepted; the numeric string is trimmed, the result is {args, n}
assert.deepEqual(continueRunArgs({ id: CRID, mode: "verify" }, "25"),
                 { args: { resume: CRID, budget: 25, mode: "verify" }, n: 25 });
assert.deepEqual(continueRunArgs({ id: CRID }, 25), { args: { resume: CRID, budget: 25 }, n: 25 });
assert.deepEqual(continueRunArgs({ id: CRID }, " 12 "), { args: { resume: CRID, budget: 12 }, n: 12 });
// boundaries are inclusive
assert.deepEqual(continueRunArgs({ id: CRID }, 1), { args: { resume: CRID, budget: 1 }, n: 1 });
assert.deepEqual(continueRunArgs({ id: CRID }, 5000), { args: { resume: CRID, budget: 5000 }, n: 5000 });
// a falsy mode is omitted, never defaulted in
for (const r of [{ id: CRID, mode: "" }, { id: CRID, mode: null }, { id: CRID, mode: undefined },
                 { id: CRID }]) {
  const ok = continueRunArgs(r, "5");
  assert.deepEqual(ok, { args: { resume: CRID, budget: 5 }, n: 5 });
  assert.ok(!("mode" in ok.args));
}
// rejections: {error} only — never a half-built args payload
for (const badN of [0, 5001, 12.5, "12.5", "abc", "", null, true, false, undefined]) {
  const bad = continueRunArgs({ id: CRID }, badN);
  assert.ok(typeof bad.error === "string" && bad.error.length > 0, String(badN));
  assert.ok(!("args" in bad), String(badN));
}
for (const badRun of [null, undefined, {}, { id: "" }, { id: "   " }, { id: 5 }]) {
  const bad = continueRunArgs(badRun, "5");
  assert.ok(typeof bad.error === "string" && bad.error.length > 0);
  assert.ok(!("args" in bad));
}
// contract: exactly resume/budget (+mode); never config/max_evals, and extra run keys are not
// forwarded. The input run object is never mutated.
const extraRun = { id: CRID, mode: "screen", config: "examples/poison.yaml", max_evals: 999 };
const extraBefore = JSON.stringify(extraRun);
const extra = continueRunArgs(extraRun, "8");
assert.deepEqual(extra, { args: { resume: CRID, budget: 8, mode: "screen" }, n: 8 });
assert.deepEqual(Object.keys(extra.args).sort(), ["budget", "mode", "resume"]);
assert.ok(!("config" in extra.args) && !("max_evals" in extra.args));
assert.equal(JSON.stringify(extraRun), extraBefore);
assert.deepEqual(Object.keys(continueRunArgs({ id: CRID }, "8").args).sort(), ["budget", "resume"]);

console.log("PROV OK");
'''


def test_provenance_helpers_behave_offline(tmp_path):
    """Executes every badge/card/chip/caption branch of app.js's provenance layer for real:
    badges appear only for non-default keys with key-path tooltips, absences stay silent, the
    restart card has its honest empty states, STEP chips upgrade only with a matched sidecar
    inventory, and the f11 caveat needs BOTH numbers (C-1/C-2 view contract)."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")   # same environment gate as test_gui.py's ES-module check
    script = tmp_path / "prov_under_test.mjs"
    script.write_text(_PROV_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "PROV OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


# ── S1a objective v3 surfaces: scoring-floor KPI, mounting rank warn, seed derivation ──────
# Same node/import-time-DOM-shim pattern as the provenance block above: the four new builders are
# pure, exported, and executed for real. The view call sites are pinned by source checks (the views
# themselves need the browser DOM), test_compose_view_is_wired style.

_S1A_SCRIPT = r'''
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
const { objectiveVersionOptionsHtml, f0KpiHtml, mountingRankWarnHtml, seedDerivationHtml } = app;
assert.equal(typeof objectiveVersionOptionsHtml, "function");
assert.equal(typeof f0KpiHtml, "function");
assert.equal(typeof mountingRankWarnHtml, "function");
assert.equal(typeof seedDerivationHtml, "function");

// 1. objective select: exactly three options, value 3 present, honest v3 description
const opts1 = objectiveVersionOptionsHtml(1);
assert.equal((opts1.match(/<option /g) || []).length, 3);
for (const v of ["1", "2", "3"]) assert.ok(opts1.includes(`value="${v}"`), v);
assert.ok(opts1.includes("scoring floor f0"), opts1);
assert.ok(opts1.includes("cov + dislope score only f ≥ f0"), opts1);
assert.match(opts1, /value="1" selected/);            // an existing v1 brief still selects 1
assert.ok(!/value="3" selected/.test(opts1));
const opts3 = objectiveVersionOptionsHtml(3);
assert.match(opts3, /value="3" selected/);            // a v3 brief selects 3
assert.ok(!/value="1" selected/.test(opts3));

// 2. scoring-floor KPI: nothing without f0; the fmtHz floor + the honest title with f0
assert.equal(f0KpiHtml({}), "");
assert.equal(f0KpiHtml({ f0_hz: null }), "");
assert.equal(f0KpiHtml(null), "");
assert.equal(f0KpiHtml(undefined), "");
const kpi = f0KpiHtml({ f0_hz: 1000 });
assert.match(kpi, /Scoring floor/);
assert.match(kpi, /f≥/);
assert.ok(kpi.includes(">1.0 kHz<"), kpi);
assert.ok(kpi.includes('title="target.f0_hz — cov and dislope score only frequencies f ≥ f0; everything below is masked (objective v3)"'), kpi);
assert.ok(f0KpiHtml({ f0_hz: 500 }).includes(">500 Hz<"));
assert.ok(!f0KpiHtml({ f0_hz: null }).includes("–"), "absent f0 must render nothing, never a dash KPI");

// 3. compare mounting warn: only with the mounting key in mixed_keys, never a generic duplicate
assert.equal(mountingRankWarnHtml([]), "");
assert.equal(mountingRankWarnHtml(["backend", "freqs_hz"]), "");
assert.equal(mountingRankWarnHtml(null), "");
assert.equal(mountingRankWarnHtml(undefined), "");
const mw = mountingRankWarnHtml(["backend", "mounting"]);
assert.ok(mw.includes("mounting differs"), mw);
assert.ok(mw.includes("never rank across mountings"), mw);
assert.ok(mw.includes("J improves under the enclosure"), mw);
assert.match(mw, /<span class="warn-text">/);

// 4. seed derivation: no feasibility -> nothing; happy path -> knob + clamp pill + below-f0
assert.equal(seedDerivationHtml(undefined), "");
assert.equal(seedDerivationHtml(null), "");
assert.equal(seedDerivationHtml({}), "");
assert.equal(seedDerivationHtml({ rule: "k_law", derivation: [] }), "");
assert.equal(seedDerivationHtml({ rule: "k_law", derivation: "nope" }), "");
const FEAS = {
  rule: "k_law_feasibility_v1",
  screen_freqs_below_f0: 4, screen_freqs_total: 9,
  verify_freqs_below_f0: 2, verify_freqs_total: 6,
  derivation: [
    { knob: "mouth_w_mm", derived_mm: 320.0, applied: true, clamped_to_bound: true, note: "envelope" },
    { knob: "a_deg", derived_mm: 32.5, applied: true, clamped_to_bound: false, note: "coverage/2" },
    { knob: "fc_hz", applied: null, clamped_to_bound: false, note: "no target fc" },
    { knob: "g_ar_m", derived_mm: null, applied: false, clamped_to_bound: false, note: "" },
  ],
};
const sd = seedDerivationHtml(FEAS);
assert.match(sd, /Seed derivation \(brief-driven, clamp-only\)/);
assert.ok(sd.includes("k_law_feasibility_v1"), sd);
assert.ok(sd.includes("widening never automatic"), sd);
assert.ok(sd.includes("screen: 4/9 solved freqs below f0"), sd);
assert.ok(sd.includes("verify: 2/6"), sd);
assert.ok(sd.includes("(masked under v3)"), sd);
for (const knob of ["mouth_w_mm", "a_deg", "fc_hz", "g_ar_m"]) assert.ok(sd.includes(knob), knob);
assert.ok(sd.includes("320 mm"), sd);                 // derived_mm through the house _trimNum
assert.ok(sd.includes("32.5 mm"), sd);
assert.ok(sd.includes("clamped to bound"), sd);       // the pill for the clamped knob
assert.ok(sd.includes("seeded"), sd);                 // the plain cell for the unclamped knob
assert.ok(sd.includes("no target fc"), sd);           // applied null + no number -> the note says why
assert.match(sd, /<td class="r">–<\/td>/, sd);        // absent derived + applied false -> honest dash
// partial record: only the screen counts arrived; no invented verify line, missing rule still renders
const partial = seedDerivationHtml({ screen_freqs_below_f0: 1, screen_freqs_total: 3,
  derivation: [{ knob: "depth_mm" }] });
assert.ok(partial.includes("screen: 1/3"), partial);
assert.ok(!partial.includes("verify:"), partial);
assert.ok(partial.includes("depth_mm"), partial);
assert.match(partial, /<span class="muted">–<\/span>/, partial);

console.log("S1A OK");
'''


def test_s1a_helpers_behave_offline(tmp_path):
    """Executes the objective-v3 surfaces' pure builders for real: the three-option objective select
    (value 3 + honest floor-f0 description), the f0 KPI (nothing without f0, fmtHz floor with it),
    the mounting rank warn (only on mixed_keys mounting), and the seed-derivation card (nothing
    without feasibility.derivation, knob/derived/applied/clamp rows, below-f0 counts, honest
    dashes/notes for the entries with no target)."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "s1a_under_test.mjs"
    script.write_text(_S1A_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "S1A OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


def test_s1a_views_are_wired():
    """The committed views call the executed builders: the KPI lands right after Band, the mounting
    warn under the generic banner, the seed card after the restart schedule and before Actions.
    Also pins the single brief-editor mount (the Compose wizard inherits v3; no second select) and
    the unchanged new-brief default objective_version 1."""
    src = APPJS.read_text(encoding="utf-8")
    # task 1: ONE editor select in app.js (the wizard mounts showBriefDetail, it does not copy it)
    assert src.count('id="brf-obj"') == 1
    assert "objectiveVersionOptionsHtml(objVer)" in src
    assert "3 additionally masks everything below the brief's scoring floor f0 (target.f0_hz)" in src
    assert 'objective: { version: +document.getElementById("brf-obj").value },' in src   # save path unchanged
    # task 1: the new-brief draft default stays v1
    assert 'symmetry: "hv", objective_version: 1, verify_only: false,' in src
    assert "objective: { version: NEW_BRIEF_DEFAULTS.objective_version }," in src
    # task 2: the pure KPI builder is spliced in right after Band (index 2), absent -> ""
    assert "kpis.splice(2, 0, f0KpiHtml(t));" in src
    assert 'kpis.filter(Boolean).join("")' in src
    # task 3: the mounting warn rides with the generic banner (kept) and the DI guard
    assert "[badgeRows, mixedBanner, mountingRankWarnHtml(mixed), diNote]" in src
    # task 4: seed card between the restart schedule and the Actions row, fed d.feasibility
    assert "${restartScheduleHtml(d, id)}\n\n      ${seedDerivationHtml(d.feasibility, d.objective)}\n\n      <!-- Actions -->" in src


# ── Inline 3D + 3D time-lapse (owner requests, views only) ───────────────────────────────
# Run detail carries a lazy embedded 3D viewer for the best design (data-v3d tagged, disposed by
# route()'s marker sweep); the evolution page gains a lazy "3D" mode playing the frames3d
# improvement frames through view3d.js::init3dFrames. Source wiring here; the pure per-frame
# preparation runs for real in node below.

def test_inline_3d_and_disposal_are_wired():
    """The inline viewer exists below the wall cross-section, is lazy (fetch after render, staleness
    guard, failure note), carries the [data-v3d] marker, and route() sweeps every marked container."""
    src = APPJS.read_text(encoding="utf-8")
    # route() disposal: the marker sweep replaces the old single-id dispose
    assert 'document.querySelectorAll("[data-v3d]")' in src
    assert 'if (el._dispose3d) el._dispose3d();' in src
    assert re.search(r'querySelectorAll\("\[data-v3d\]"\)\.forEach\(el => \{ if \(el\._dispose3d\) el\._dispose3d\(\); \}\);', src)
    # the dedicated 3D page container is marked too (same sweep covers it)
    assert 'id="view3d-wrap" data-v3d' in src
    # inline viewer inside viewRunDetail: marked container + lazy loader
    assert 'id="inline-3d" data-v3d' in src
    assert 'api("/api/mesh/" + id + "/" + inlineHash)' in src      # fetched only after render
    assert "if (!inline3d.isConnected) return;" in src             # navigated away -> no scene
    assert "init3d(inline3d" in src                                # existing init3d, container-fitted
    assert "Could not load the mesh for this design" in src        # fetch failure -> honest note
    assert "No best design hashed yet" in src                      # no best design -> honest note
    # shadows default on, persisted with the SAME toggle key as the 3D page
    assert src.count('localStorage.getItem("hl-v3d-shadows")') >= 2
    assert "inline3d-shadows" in src
    # no second auto-loaded scene for the same design: the inline loader's start() serves both its
    # initial build and its shadow re-init, so app.js holds exactly three init3d call sites
    # (3D page: initial + shadow toggle; inline: start, shared by its initial build and toggle)
    assert src.count("init3d(") == 3


def test_evolution_3d_mode_is_wired():
    """The evolution page gains the lazy 3D toggle: frames3d fetched ONLY on use, improvements-only
    rule enforced both ways and disclosed, player container marked [data-v3d], honest unavailable
    branches, and view3d.js exports the frame player."""
    evo = (ROOT / "hornlab_search" / "gui" / "static" / "evolution.js").read_text(encoding="utf-8")
    v3d = (ROOT / "hornlab_search" / "gui" / "static" / "view3d.js").read_text(encoding="utf-8")
    # toggle + container + player wiring
    assert 'id="evo-3d"' in evo and 'id="evo-3d" data-v3d' in evo
    assert 'fetch("/api/evolution/" + encodeURIComponent(runId) + "/frames3d")' in evo
    assert "init3dFrames(cv, frames3d" in evo and 'import { init3dFrames } from "./view3d.js";' in evo
    # lazy: the fetch lives inside the enable path, not at view load
    assert "async function enable3d" in evo and "Loading 3D time-lapse" in evo
    # the single rule: one source-of-truth constant, disclosed 3+ places (toggle note, build note,
    # re-enable note, mode-select note)
    assert 'const RULE3D = "3D shows improvement frames only' in evo
    assert evo.count("RULE3D") >= 4
    assert 'mode !== "best"' in evo                     # checking 3D forces improvements-only
    assert "'every candidate' plays in 2D" in evo       # selecting every-candidate turns 3D off
    # honest branches: no frames / fetch failure / CDN failure all stay on 2D
    assert "R.available === false" in evo and "the 2D time-lapse stays." in evo
    assert "staying on the 2D panels." in evo
    assert 'if (!root.isConnected) return;' in evo      # navigation during the lazy build bails
    # view3d.js: exported player + disposal contract + lazy THREE (no top-level WebGL need)
    assert "export async function init3dFrames" in v3d
    assert "container._dispose3d = dispose" in v3d
    assert "mesh.geometry = built.geo;" in v3d          # hot-swap, no scene rebuild


# Node-exercisable core of the frame player (view3d.js top level stays DOM/THREE-free — the same
# direct-import pattern as tests/test_gui_mesh_quadrants.py; the WebGL scene assembly itself needs
# a browser, so prepareFrames is the executed part and the swap paths are source-wired above).
_FRAMES_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
const v3d = await import(pathToFileURL(process.argv[2]).href);
const { prepareFrames, init3dFrames, mirrorMesh } = v3d;
assert.equal(typeof prepareFrames, "function");
assert.equal(typeof init3dFrames, "function");          // exported; scene half needs a browser
assert.equal(typeof mirrorMesh, "function");            // the per-frame mirroring it reuses
// improvement frames as the reader keys them: eval number n, objective, hash, quadrants, decimation
const quarter = { n: 3, objective: 22.5, mesh_hash: "aaaa11112222", quadrants: "1",
  verts: [0, 0, 0, 1, 0, 0, 0, 1, 0], tris: [0, 1, 2], decimated: true, n_tris_full: 400 };
const half = { n: 7, objective: 18.4, quadrants: "14",
  verts: [0, 0, 0, 1, 0, 0, 0, 1, 0], tris: [0, 1, 2], decimated: false, n_tris_full: 3 };
const empty = { n: 9, objective: null, quadrants: "", verts: [], tris: [] };   // no mesh saved
const pf = prepareFrames([quarter, half, empty, null]);
assert.equal(pf.length, 2, "mesh-less frames are skipped, never fabricated");
// frame 1: quarter '1' -> 4 mirrored copies (12 verts); bounds extend symmetric to -1
assert.equal(pf[0].verts.length, 36);                   // 12 mirrored verts x 3 floats
assert.equal(pf[0].tris.length, 12);                    // 4 copies of the one triangle
assert.deepEqual([pf[0].bounds.x0, pf[0].bounds.x1, pf[0].bounds.y0, pf[0].bounds.y1,
                  pf[0].bounds.z0, pf[0].bounds.z1], [-1, 1, -1, 1, 0, 0]);
assert.equal(pf[0].n, 3);                               // eval identity carried for playback mapping
assert.equal(pf[0].objective, 22.5);
assert.equal(pf[0].mesh_hash, "aaaa11112222");
assert.equal(pf[0].decimated, true);                    // disclosure flag rides the frame
assert.equal(pf[0].n_tris_full, 400);
// frame 2: half '14' -> 2 copies, one reflection = winding flip, exactly like mirrorMesh
assert.equal(pf[1].verts.length, 18);                   // 6 mirrored verts x 3 floats
assert.deepEqual([...pf[1].tris], [0, 1, 2, 3, 5, 4]);
assert.equal(pf[1].decimated, false);
assert.equal(pf[1].objective, 18.4);
// union bounds across frames (the player's fixed camera) is derivable, and garbage never throws
const union = [-Math.min(pf[0].bounds.x0, pf[1].bounds.x0), Math.max(pf[0].bounds.x1, pf[1].bounds.x1)];
assert.deepEqual(union, [1, 1]);
assert.deepEqual(prepareFrames(undefined), []);
assert.deepEqual(prepareFrames({}), []);
assert.deepEqual(prepareFrames([{ n: 1, verts: [0, 0, 0], tris: [0, 0, 0] }]).length, 0);  // degenerate
console.log("FRAMES OK");
'''


def test_3d_frames_prepare_offline(tmp_path):
    """Executes the pure per-frame core of init3dFrames: mirrorMesh per frame (quarter/half handedness
    bounds), the honest skips (no mesh saved), the decimation disclosure flags and the eval-identity
    carry that the playback mapping keys on."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "frames_under_test.mjs"
    script.write_text(_FRAMES_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(ROOT / "hornlab_search" / "gui" / "static" / "view3d.js")],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "FRAMES OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


# ── Persisted 3D render settings (surface / ridges / light) ──────────────────────────────────────
# One localStorage key feeds every 3D surface. The pure normalizer runs for real in node (same
# direct-import pattern as prepareFrames); the scene half is pinned in source below because WebGL
# needs a browser. Defaults are exactly the pre-settings look, so existing captures still pin.

_RENDER_PREFS_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
const v3d = await import(pathToFileURL(process.argv[2]).href);
const { normalizeRenderPrefs } = v3d;
assert.equal(typeof normalizeRenderPrefs, "function");
const defaults = { surface: "satin", ridges: "on", light: 1.0 };
// absent / corrupt / junk never throw, always default
assert.deepEqual(normalizeRenderPrefs(null), defaults);
assert.deepEqual(normalizeRenderPrefs(undefined), defaults);
assert.deepEqual(normalizeRenderPrefs(""), defaults);
assert.deepEqual(normalizeRenderPrefs("{not json"), defaults);
assert.deepEqual(normalizeRenderPrefs(42), defaults);
assert.deepEqual(normalizeRenderPrefs([]), defaults);
assert.deepEqual(normalizeRenderPrefs({}), defaults);
// a valid persisted object round-trips
assert.deepEqual(normalizeRenderPrefs('{"surface":"metallic","ridges":"thin","light":1.4}'),
  { surface: "metallic", ridges: "thin", light: 1.4 });
assert.deepEqual(normalizeRenderPrefs({ surface: "studio", ridges: "off", light: 0.7 }),
  { surface: "studio", ridges: "off", light: 0.7 });
// light is clamped into 0.5..2.0; non-finite falls back to 1.0
assert.equal(normalizeRenderPrefs({ light: 9 }).light, 2.0);
assert.equal(normalizeRenderPrefs({ light: 0.1 }).light, 0.5);
assert.equal(normalizeRenderPrefs({ light: 0.5 }).light, 0.5);
assert.equal(normalizeRenderPrefs({ light: 2 }).light, 2.0);
assert.equal(normalizeRenderPrefs({ light: "1.4" }).light, 1.4);
assert.equal(normalizeRenderPrefs({ light: "wat" }).light, 1.0);
assert.equal(normalizeRenderPrefs({ light: NaN }).light, 1.0);
assert.equal(normalizeRenderPrefs({ light: Infinity }).light, 1.0);
// unknown enums fall back per-field, never invent a surface/ridge mode
assert.equal(normalizeRenderPrefs({ surface: "chrome" }).surface, "satin");
assert.equal(normalizeRenderPrefs({ ridges: "glow" }).ridges, "on");
assert.deepEqual(normalizeRenderPrefs({ surface: "matte", ridges: "nope", light: 1.5 }),
  { surface: "matte", ridges: "on", light: 1.5 });
// returned object is a fresh value (callers mutate/compare it without aliasing stored junk)
const src = { surface: "matte", ridges: "off", light: 1.2 };
const norm = normalizeRenderPrefs(src);
assert.notEqual(norm, src);
console.log("RENDER PREFS OK");
'''


def test_3d_render_prefs_normalize_offline(tmp_path):
    """Executes the pure render-settings normalizer: defaults for absent/corrupt JSON, per-field
    fallbacks for unknown enums, and the 0.5..2.0 light clamp with a non-finite fallback to 1.0."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "render_prefs_under_test.mjs"
    script.write_text(_RENDER_PREFS_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(ROOT / "hornlab_search" / "gui" / "static" / "view3d.js")],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "RENDER PREFS OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


def test_3d_render_settings_are_wired():
    """The settings object + shared controls helper + the new persistence key exist, both 3D entry
    points add the chip, and the defaults still describe today's look (satin, ridges on, 1.0x)."""
    v3d = (ROOT / "hornlab_search" / "gui" / "static" / "view3d.js").read_text(encoding="utf-8")
    # persistence: exactly one new key, read on init and written on every control change
    assert 'const RENDER_PREF_KEY = "hl-v3d-render";' in v3d
    assert 'localStorage.getItem(RENDER_PREF_KEY)' in v3d
    assert 'localStorage.setItem(RENDER_PREF_KEY, JSON.stringify(p))' in v3d
    # pure normalizer exported for the offline test; load/save are internal helpers
    assert "export function normalizeRenderPrefs(raw)" in v3d
    assert "function loadRenderPrefs()" in v3d and "function saveRenderPrefs(prefs)" in v3d
    # shared material/lighting helper + the clickable overlay chip builder
    assert "function applyRenderLook(ctx, prefs)" in v3d
    assert "function applyRenderControls(container, onChange)" in v3d
    assert v3d.count("applyRenderControls(container, p => applyRenderLook(") == 2   # init3d + init3dFrames
    assert v3d.count("loadRenderPrefs()") >= 3                                       # def + both init paths
    # the chip stays clickable unlike the pointer-events:none enclosure caption
    assert "pointer-events:auto" in v3d
    # immediate in-place changes: wire removed/added by the ridges mode, opacity thinned to 0.12
    assert 'p.ridges === "off"' in v3d and "scene.remove(wire)" in v3d and "scene.add(wire)" in v3d
    assert 'p.ridges === "thin" ? 0.12' in v3d
    # light multiplier scales the three directional lights only (hemi stays ambient-relative)
    assert "preset.light.key * p.light" in v3d
    assert "preset.light.fill * p.light" in v3d
    assert "preset.light.rim * p.light" in v3d
    assert "lights.hemi.intensity = preset.light.hemi" in v3d
    # defaults preserve today's look: satin material numbers and the 0.28 ridge opacity
    assert "satin:    { colorScale: 1.0,  roughness: 0.55, metalness: 0.05, wireOpacity: 0.28" in v3d
    assert "light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } }" in v3d
    # disposal contract unchanged: both wire resources are still released
    assert "wireGeo.dispose(); wireMat.dispose();" in v3d
    assert "mat.dispose(); wireMat.dispose();" in v3d


# ── Toolbar run-control pill + resume affordance (owner decision, chat 2026-10-25) ───────────────
# The Status page's Stop ALSO lives in the left nav on every view, and stopped GUI search runs get a
# Resume affordance. The nav markup is a static file served verbatim (server.py::_static, not
# rendered per request), so app.js injects the pill holder itself and index.html stays untouched.

def test_toolbar_run_pill_is_wired():
    """app.js-only nav placement (holder injected below the nav links, after #app-nav ul), the pure
    decision helper + pill HTML node-tested via the exports, the shared two-step arm reused by
    status stop + toolbar stop + resume, the pill fed by the status poll AND its own 10 s poll,
    route() re-invocation, and the resume POST contract defended by a /api/preview probe."""
    src = APPJS.read_text(encoding="utf-8")
    idx = (ROOT / "hornlab_search" / "gui" / "static" / "index.html").read_text(encoding="utf-8")
    # placement: injected by app.js, index.html untouched, below the nav links (after #app-nav ul)
    assert "nav-runctl" not in idx
    assert 'holder.id = "nav-runctl"' in src and "ul.after(holder)" in src
    # route() re-invokes the pill statelessly (sig-skip keeps an armed click alive)
    route_body = src.split("function route() {", 1)[1].split("\n}\n", 1)[0]
    assert "renderNavPill();" in route_body
    assert "_pillSig" in src and "holder.firstElementChild" in src
    # the shared two-step arm is reused, not duplicated: definition + status stop + toolbar stop + resume
    assert "function wireTwoStepArm(btn, msgId, opts)" in src
    assert src.count("wireTwoStepArm(") >= 4
    # data: the status page's poll feeds the pill (render + refresh), plus a small dedicated poll
    assert src.count("pillFeed(data, jobs)") >= 2
    assert "async function pollNavOnce()" in src
    assert "setInterval(() => { if (!document.hidden) pollNavOnce(); }, 10000)" in src
    assert 'document.addEventListener("DOMContentLoaded", startNavRunPill, { once: true });' in src
    # copy: grounded, one line, existing --bad/--accent classes (consistent with the Status page)
    assert ">■ Stop</button>" in src and ">▶ Resume search</button>" in src
    assert 'title="Stops the run: process tree killed + gpu-clean"' in src
    assert '"Confirm stop"' in src and '"Confirm resume"' in src
    assert "click again to confirm — process tree killed + gpu-clean" in src
    assert "stop requested — wait for the job to exit + the gpu-clean pass" in src
    assert ">■ Kill run</button>" in src and "external run · pid" in src
    assert "Kills the externally-started run that holds our GPU lock" in src
    assert "cached evals replay free" in src and "budget is per invocation" in src
    # resume POST contract (LANDED jobs.py): --resume takes a RUN ID — sourced from the stopped
    # job's own log and validated against /api/runs summaries; the preview probe still gates the
    # launch on the server's own --resume* flag in its previewed argv
    assert 'post("/api/preview", { kind: "search", args: pill.args })' in src
    assert 'post("/api/jobs", { kind: "search", args: pill.args })' in src
    assert 't.startsWith("--resume")' in src
    assert 'api("/api/runs")' in src                    # the run-id validation data source
    assert "const args = { resume: r.id };" in src      # a run id, never a bare boolean
    assert "if (r.mode) args.mode = r.mode;" in src     # screen default would rewrite run.json mode
    assert "r.budget == null || r.n < r.budget" in src  # an exhausted run is finished: no pill offer
    # honest degrade when no resumable run can be sourced (never a silently fresh search)
    assert "would start a FRESH search, not a resume" in src
    assert "no resumable run folder" in src
    # the pill section carries no WebGL code and nothing the [data-v3d] disposal sweep touches
    pill_block = src.split("Toolbar run-control pill (left nav", 1)[1].split("function currentRunCard", 1)[0]
    assert pill_block.count("data-v3d") == 0
    assert 'id="tb-stop-run"' in pill_block and 'id="tb-resume-run"' in pill_block
    assert 'id="tb-stop-msg"' in pill_block and 'id="tb-resume-msg"' in pill_block
    # the KILL run control (owner 2026-10-25): the externally-started run holding OUR gpu lock is
    # killed by pid + child tree + gpu-clean via POST /api/stop-current — in the pill AND the cards
    assert 'id="tb-kill-run"' in pill_block and 'id="tb-kill-msg"' in pill_block
    assert 'id="btn-kill-run"' in src and 'id="st-kill-msg"' in src
    assert 'post("/api/stop-current", {})' in src and '"Confirm kill"' in src
    # note: the kill itself lives server-side (jobs.stop_external) — pinned in
    # tests/test_gui_integration_phases.py, not in this app.js source check


# ── Run-detail "Continue this run" card (search top-up) ──────────────────────────────────────────
# The card renders only for a search run, POSTs {kind:"search", args:{resume,budget[,mode]}}, and the
# wiring re-renders the detail page after the job is done. The pure helpers are node-tested above via
# the PROV script; here the generated HTML ids/attributes and the launch contract are source-pinned.

def test_continue_run_control_is_wired():
    """The card builder exists and is rendered in the run-detail template, its five ids and the
    numeric bounded/labelled input are present, the launch POST carries exactly the helper's args,
    the helper builds only resume/budget(+mode), and the wiring polls the job and re-renders the
    detail page on done (no --config/max-evals, no blocking dialogs)."""
    src = APPJS.read_text(encoding="utf-8")
    # the card builder exists and is rendered in the run-detail template
    assert "function continueRunCardHtml(d, sum) {" in src
    assert "${continueRunCardHtml(d, sum)}" in src
    assert 'if (!continueRunAvailable(d)) return "";' in src      # only a search run gets a card
    # the five stable ids + a numeric, labelled, bounded input and a live status region
    for i in ("continue-run-card", "continue-run-n", "continue-run-help",
              "continue-run-btn", "continue-run-status"):
        assert f'id="{i}"' in src, i
    assert '<label for="continue-run-n">Additional evaluations</label>' in src
    assert ('id="continue-run-n" type="number" min="1" max="5000" step="1" '
            'inputmode="numeric"') in src
    assert 'id="continue-run-status" role="status"' in src
    # launch POST: the exact shape the CLI/JobManager expects (kind search + the helper's args)
    assert 'post("/api/jobs", { kind: "search", args: checked.args })' in src
    # helper contract: N new evals only; no config, no max-evals, mode only when declared
    helper = src.split("function continueRunArgs(run, rawN) {", 1)[1].split("\n}\n", 1)[0]
    assert "const args = { resume: id, budget: n };" in helper
    assert "if (run.mode) args.mode = run.mode;" in helper
    assert "--config" not in helper
    assert "max_evals" not in helper and "max-evals" not in helper
    # the wiring block: polls the job, re-renders the detail page on done, no blocking dialogs
    cont = src.split('const contBtn = document.getElementById("continue-run-btn");', 1)[1]
    cont = cont.split("// ── View 3 / 7: 3D view", 1)[0]
    assert 'api("/api/job/" + r.id)' in cont
    assert "setTimeout(res, 2000)" in cont
    assert "await viewRunDetail(id);" in cont
    assert "--config" not in cont
    assert "max_evals" not in cont and "max-evals" not in cont
    assert "confirm(" not in cont and "alert(" not in cont


def test_continue_run_queue_states_are_wired():
    """A resume job queues when the GPU is busy: the launch response and the poll surface the
    queued state honestly (never as "running"), a queued-only cancel button posts /cancel and stops
    the poll without its message being overwritten, and renderJobs marks queued rows with the warn
    colour plus a Cancel queued action (the Stop run button stays running-only)."""
    src = APPJS.read_text(encoding="utf-8")
    css = (ROOT / "hornlab_search" / "gui" / "static" / "app.css").read_text(encoding="utf-8")

    cont = src.split('const contBtn = document.getElementById("continue-run-btn");', 1)[1]
    cont = cont.split("// ── View 3 / 7: 3D view", 1)[0]

    # launch response: queued shows the FIFO position + that it starts itself; running keeps
    # the existing "Started job" copy
    assert 'if (r.status === "queued")' in cont
    assert "Queued behind the current run (position ${r.position})" in cont
    assert "starts automatically when the GPU is free." in cont
    assert 'say(`Started job ${r.id}' in cont

    # poll: queued is handled BEFORE running, uses queue_position, and offers the cancel affordance
    assert cont.index('if (j.status === "queued")') < cont.index('if (j.status === "running")')
    assert "Waiting in queue (position ${j.queue_position})" in cont
    assert "showCancel(true);" in cont
    # running hides the cancel affordance and says running, never "waiting"
    assert "showCancel(false);" in cont
    assert "contCancel.hidden = !on;" in cont

    # card markup: the queued-only cancel button is hidden by default with an honest title
    assert 'id="continue-run-cancel" hidden' in src
    assert 'title="Removes this request from the queue — nothing has started yet"' in src
    assert ">Cancel queued request</button>" in src
    # clicking it posts a QUEUED-ONLY cancel for the active job, reports success, and stops the
    # poll locally
    assert 'post("/api/job/" + activeJobId + "/cancel", { only_queued: true })' in cont
    assert "Queued request cancelled." in cont
    assert "let stopped = false;" in cont
    assert "stopped = true;" in cont
    assert "if (stopped) return;" in cont
    # the job may have auto-started between the poll and the click: the error path must hide the
    # queued-only affordance and keep polling (never kill, never re-enable the input)
    cancel = cont.split("if (contCancel) contCancel.onclick = async () => {", 1)[1]
    err = cancel.split("if (r.error) {", 1)[1].split("return;", 1)[0]
    assert 'say("Could not cancel: " + r.error, "error-text");' in err
    assert "queued = false;" in err
    assert "showCancel(false);" in err
    assert "setBusy(false);" not in err      # the input/Continue stay disabled for the running job
    assert "stopped = true;" not in err      # the next poll must surface "Running…"

    # no blocking dialogs added, and the launch args still carry no --config / max-evals
    assert "confirm(" not in cont and "alert(" not in cont
    assert "--config" not in cont
    assert "max_evals" not in cont and "max-evals" not in cont

    # status page: queued has its own status class (existing --warn colour) and a queued-only
    # Cancel queued that reuses the .cancel-job-btn / data-job-id mechanism
    assert re.search(r"\.job-row \.job-status-queued\s*\{\s*color:var\(--warn\);\s*\}", css)
    jobs = src.split("function renderJobs(jobs) {", 1)[1].split("// ── View G: Glossary", 1)[0]
    assert 'j.status === "queued"' in jobs
    assert " · queued (position ${qpos})" in jobs
    assert '>Cancel queued</button>' in jobs
    assert 'data-queued="1"' in jobs
    assert 'title="Removes this request from the queue — nothing has started yet"' in jobs
    # Stop run stays running-only, and the shared handler posts cancel for both with no new dialog;
    # a queued row sends the same queued-only guard so a race cannot kill an auto-started job
    assert ">Stop run</button>" in jobs
    assert 'post("/api/job/" + btn.dataset.jobId + "/cancel",' in jobs
    assert "wasQueued ? { only_queued: true } : {}" in jobs
    assert "wasQueued" in jobs
    assert 'if (!wasQueued && !confirm("Cancel this job?")) return;' in jobs
    assert 'showToast("Queued request cancelled — nothing had started.", "info")' in jobs

    # no design/CSS additions for this hardening: the card still relies on the hidden attribute
    assert "continue-run-cancel" not in css


# ── Compose hybrid disclosure + seed preview (owner ask, 2026-10-25) ─────────────────────────
# The additive /api/configs keys generator_block / seed_params (gui/data.py list_configs, verbatim
# yaml passthroughs, C-6 in tests/test_gui_integration_phases.py) are rendered DISPLAY-ONLY in the
# Compose wizard: a "hybrid — <contributors>" row caption when the block names a composite
# (splice parents / blend section / per-plane laws / grid rows — by shapes, never title greps),
# and a seed table for a picked config carrying seed_params. The helpers are pure + exported;
# the same import-time-DOM-shim node pattern as the provenance block above runs every branch.
# The view call sites are pinned by source checks (test_compose_view_is_wired style), and the
# payload-fidelity pairing (no seed/generator fields in the compose POST body) stays pinned.

_COMPOSE_HYBRID_SCRIPT = r'''
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
const { hybridContributors, hybridCaptionFromBlock, seedPreviewValue, seedRowsHtml, seedPanelHtml } = app;
assert.equal(typeof hybridContributors, "function");
assert.equal(typeof hybridCaptionFromBlock, "function");
assert.equal(typeof seedPreviewValue, "function");
assert.equal(typeof seedRowsHtml, "function");
assert.equal(typeof seedPanelHtml, "function");

// caption: honest absences / unexpected shapes caption NOTHING (rows keep today's wording)
assert.equal(hybridCaptionFromBlock(undefined), "");
assert.equal(hybridCaptionFromBlock(null), "");
assert.equal(hybridCaptionFromBlock({}), "");
assert.equal(hybridCaptionFromBlock(42), "");
assert.equal(hybridCaptionFromBlock("splice"), "");
assert.equal(hybridCaptionFromBlock([]), "");

// plain single-profile generators stay uncaptioned — never invented wording
assert.equal(hybridCaptionFromBlock({ name: "typology", profile_h: { type: "conical" }, profile_v: "same" }), "");
// same-type planes are ONE construction, not a mix (biradial_keele / qtw_waveguide shapes)
assert.equal(hybridCaptionFromBlock({ name: "typology",
  profile_h: { type: "biradial" }, profile_v: { type: "biradial" } }), "");
// a perturbation of ONE law, both planes (perturbed_osse_hv shape)
assert.equal(hybridCaptionFromBlock({ name: "typology",
  profile_h: { type: "osse" }, profile_v: { type: "osse" }, perturb: { u_max: 0.25 } }), "");
// grid adapter WITHOUT a rows section (grid_ellipse shape): not a mix either
assert.equal(hybridCaptionFromBlock({ name: "grid", profile_h: { type: "conical" },
  profile_v: "same", n_phi: 13 }), "");

// the committed splice block: parents straight from the block content
const SPLICE = { name: "typology",
  profile_h: { type: "splice", first: { type: "osse" }, second: { type: "tractrix" } },
  profile_v: "same", n_anchors: 16, max_wall_deg: 80.0, mouth: "ellipse" };
assert.equal(hybridCaptionFromBlock(SPLICE), "hybrid — osse + tractrix");
assert.deepEqual(hybridContributors(SPLICE), ["osse", "tractrix"]);
// blend block (blend_osse_tractrix shape): base profile + blend profile
assert.equal(hybridCaptionFromBlock({ name: "typology", profile_h: { type: "osse" },
  blend_h: { type: "tractrix" }, profile_v: "same" }), "hybrid — osse + tractrix");
// per-plane hybrid (hyb_osse_h_tractrix_v shape): the two plane laws
assert.equal(hybridCaptionFromBlock({ name: "typology", profile_h: { type: "osse" },
  profile_v: { type: "tractrix" } }), "hybrid — osse + tractrix");
// grid rows blocks (lecleach_rollback / salmon_x_signed shapes): the rows carry the types —
// a rows kind is ONE construction on shaped stations, so the caption is "rows —", not "hybrid —"
assert.equal(hybridCaptionFromBlock({ name: "grid", rows: { type: "lecleach" }, n_phi: 15 }),
             "rows — lecleach");
assert.equal(hybridCaptionFromBlock({ name: "grid",
  rows: [{ type: "salmon_elliptical" }, { type: "lecleach" }] }),
             "rows — salmon_elliptical + lecleach");
assert.equal(hybridCaptionFromBlock({ name: "grid", rows: {} }), "rows — grid");
// composite-family generator NAME with no derivable sections: the name itself stays honest
assert.equal(hybridCaptionFromBlock({ name: "throat_blend" }), "hybrid — throat_blend");
assert.equal(hybridCaptionFromBlock({ name: "hybrid", profile_h: { type: "osse" },
  profile_v: "same" }), "hybrid — osse");
// list-shaped block (the reader allows lists): distinct sections joined; one section = not a mix
assert.equal(hybridCaptionFromBlock([{ type: "osse" }, { type: "hypex" }]), "hybrid — osse + hypex");
assert.equal(hybridCaptionFromBlock([{ name: "typology" }, { name: "typology" }]), "");
// duplicate section mentions collapse, section order is kept
assert.deepEqual(hybridContributors({ name: "typology", profile_h: { type: "osse" },
  profile_v: { type: "tractrix" }, blend_h: { type: "osse" } }), ["osse", "tractrix"]);

// seed preview value rendering: numbers through the house trim, nested values as JSON
assert.equal(seedPreviewValue(110), "110");
assert.equal(seedPreviewValue(110.5), "110.5");
assert.equal(seedPreviewValue(-0.03), "-0.03");
assert.equal(seedPreviewValue("n"), "n");
assert.equal(seedPreviewValue(null), "null");
assert.equal(seedPreviewValue([0.25]), "[0.25]");
assert.equal(seedPreviewValue(true), "true");

// seed panel: absent stays absent, honestly
assert.equal(seedPanelHtml(null), "");
assert.equal(seedPanelHtml(undefined), "");
assert.equal(seedPanelHtml([]), "");
assert.equal(seedPanelHtml({ name: "conical" }), "");
assert.equal(seedPanelHtml({ seed_params: {} }), "");
assert.equal(seedPanelHtml({ seed_params: [] }), "");

// present: knob/value rows + the honest caption; catalog_name absent -> the config's own name
const UNCAT = { name: "splice_osse_tractrix", catalog_name: null,     // the sole-pick shape
                generator_block: SPLICE,
                seed_params: { L_mm: 110.0, h_first_a_deg: 25.0, h_first_s: 0.4,
                               h_second_fc_hz: 750.0, h_zs_frac: 0.5 } };
const panel = seedPanelHtml(UNCAT);
assert.ok(panel.startsWith("<div"), panel);
assert.ok(panel.includes("Seed preview — splice_osse_tractrix"), panel);
for (const k of ["L_mm", "h_first_a_deg", "h_first_s", "h_second_fc_hz", "h_zs_frac"])
  assert.ok(panel.includes(`>${k}<`), k);
assert.ok(panel.includes(">110<") && panel.includes(">750<") && panel.includes(">0.4<") &&
          panel.includes(">0.5<"), panel);
assert.ok(panel.includes("the seed the search starts from — bounds stay the config's own"), panel);
assert.ok(panel.includes("nothing here is sent"), panel);
assert.ok(panel.includes("config seed geometry (preview only)"), panel);
// naming prefers the catalog name when one exists
const catPanel = seedPanelHtml({ name: "x", catalog_name: "y", seed_params: { L_mm: 1.25 } });
assert.ok(catPanel.includes("Seed preview — y"), catPanel);
assert.ok(catPanel.includes(">1.25<"), catPanel);

// long listing caps with the literal "+N more" honesty tail (no hidden rows invented)
const longParams = Object.fromEntries([...Array(10).keys()].map(i => [`knob_${i}`, i]));
const lp = seedPanelHtml({ name: "long", seed_params: longParams });
assert.ok(lp.includes("Seed preview — long"), lp);
assert.match(lp, /\+2 more seed knobs/);
assert.ok(lp.includes(">knob_7<"), lp);
assert.ok(!lp.includes("knob_8") && !lp.includes("knob_9"), lp);

// hostile strings never land raw — knob names AND values are escaped
const wp = seedPanelHtml({ name: "x",
  seed_params: { "<a>": "<img src=x onerror=alert(1)>", g_stop_cos2k: [0.25] } });
assert.ok(wp.includes("&lt;a&gt;"), wp);
assert.ok(wp.includes("&lt;img"), wp);
assert.ok(!wp.includes("<img") && !wp.includes("<a>"), wp);
assert.ok(wp.includes("[0.25]"), wp);

console.log("COMPOSE HYBRID OK");
'''


def test_compose_hybrid_and_seed_helpers_behave_offline(tmp_path):
    """Executes the compose hybrid/seed builders for real: only a generator block that SHAPES a
    composite (splice parents, blend section, different per-plane profiles, grid rows, or a
    composite-family generator name) earns a "hybrid — <contributors>" caption; absent/unexpected
    blocks and same-type planes caption nothing; the seed panel exists only when the config
    carries seed_params (knob/value rows through the house trim, capped with a literal "+N more"
    tail, everything escaped), and states it is the config's seed geometry, display-only."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")   # same environment gate as test_gui.py's ES-module check
    script = tmp_path / "compose_hybrid_under_test.mjs"
    script.write_text(_COMPOSE_HYBRID_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "COMPOSE HYBRID OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


def test_compose_hybrid_and_seed_views_are_wired():
    """The compose view references the executed builders and NOTHING leaks into the payloads:
    the step-1 row builder carries the hybrid caption call (absent key -> no caption), the seed
    panel holder renders per picked config, the POST bodies still come only from currentJob's
    build_argv field set (the pinned pairing test), the run-summary semantics strings and the
    uncatalogued sole-pick rule stay byte-identical (the rule itself remains for any
    future uncatalogued config; the five S1a expansion names left it with the 2026-10-25
    C4 catalog batch), and the
    helpers are exported for the offline node test."""
    src = APPJS.read_text(encoding="utf-8")
    compose = src.split("View 5b: Compose", 1)[1].split("View 6: Launch", 1)[0]
    # wiring: the caption inside the row builder; the panel holder + per-pick render (step 1)
    assert "hybridCaptionFromBlock(c.generator_block)" in compose
    assert 'id="cmp-seed-panel"' in compose
    assert "pickedConfigs().map(seedPanelHtml)" in compose
    # payload fidelity: the compose POST args still flow through currentJob, which names ONLY the
    # build_argv field set — no generator_block/seed_params FIELD is constructed anywhere (the
    # regex below matches key-construction positions: `x.seed_params : y` ternary reads pass)
    assert 'post("/api/preview", job)' in compose and 'post("/api/jobs", job)' in compose
    assert not re.search(r"(?<![.\w])(generator_block|seed_params)\s*:", compose)
    body = compose.split("function currentJob() {", 1)[1].split("\n  function gateReason()", 1)[0]
    for f in ("cma_seed: seedRaw", "budget: budRaw", "families: fams", "tier: S.tier",
              'args: { config, brief: S.briefPath', 'args: { brief: S.briefPath'):
        assert f in body, f
    assert not re.search(r"seed_params|generator_block|hybridContributors|seedPanelHtml", body)
    # run-summary semantics unchanged (0/1/campaign wording byte-identical)
    assert ("1 picked · single-config run (${c.catalog_name || c.name}) — "
            "choose dry-run / run / search in step 3") in src
    assert "${n} picked · campaign over" in src
    # the uncatalogued sole-pick rule, untouched by the hybrid/seed additions
    assert "if (!c.catalog_name) return S.picks.size === 0 || S.picks.has(c.path);" in src
    assert ("is uncatalogued — campaign resolves catalog names only, so it launches alone: "
            "clear the other picks first.") in src
    assert "Uncatalogued — single-config runs only" in src
    # the honest seed caption lives in the panel builder
    assert "the seed the search starts from — bounds stay the config's own" in src
    # the pure helpers are exported for the offline node test (renderProvenanceBadges precedent)
    assert "export { hybridContributors, hybridCaptionFromBlock, seedPreviewValue, seedRowsHtml, seedPanelHtml };" in src