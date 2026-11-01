// app.js — hornlab-search GUI   AGPL-3.0-or-later
// Single-page app with hash routing. No build step, vanilla ES modules.

import { chart, heat, cmap, drawCbar, niceTicks, diFromCuts, groupColor,
         el, NS, css, fmt, FT, DEFW, polarMap, wallSection, familyColor, measuredWidth, isobarMap } from "./charts.js";
import { TERMS as GLOSSARY, TERM_ORDER, tip } from "./glossary.js";
import { loadParamCatalog, paramTipHtml, typologyTipHtml, typologyChipsHtml } from "./paramtips.js";
import { init3d } from "./view3d.js";
import { viewEvolution } from "./evolution.js";
import { viewBalloon } from "./balloon.js";
import { viewTypologySandbox } from "./sandbox.js";

// ── XSS helper ─────────────────────────────────────────────────────
function esc(s) {
  return (s == null ? "–" : String(s))
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── Number / unit helpers ───────────────────────────────────────────
// fmt(v, d) is imported from charts.js (2 decimals default)
const fmtHz  = v => v == null ? "–" : v >= 1000 ? (v/1000).toFixed(1) + " kHz" : Math.round(v) + " Hz";
const fmtDeg = v => v == null ? "–" : Number(v).toFixed(0) + "°";
const fmtMm  = v => v == null ? "–" : Math.round(v) + " mm";
const fmtDb  = v => v == null ? "–" : Number(v).toFixed(1) + " dB";
const fmtPct = v => v == null ? "–" : Number(v).toFixed(0) + "%";

// ── API helpers ────────────────────────────────────────────────────

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) { const t = await r.text().catch(() => ""); throw new Error(`${r.status} ${t}`); }
  return r.json();
}

async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({ error: "invalid response" }));
  return j;
}

// ── Routing ────────────────────────────────────────────────────────

// The view container is REPLACED on every navigation: a slow view that finishes after the user has
// moved on then writes into a detached element instead of painting over the current page.
let ROOT = document.getElementById("view-root");
const currentRoot = () => ROOT;

const ROUTES = [
  { re: /^#\/$|^#\/home$/,              fn: () => viewHome() },
  { re: /^#\/status$/,                  fn: () => viewStatus() },
  { re: /^#\/campaigns$/,               fn: () => viewCampaignsList() },
  { re: /^#\/campaign\/(.+)$/,          fn: m => viewCampaignDetail(m[1]) },
  { re: /^#\/runs$/,                    fn: () => viewRunsList() },
  { re: /^#\/run\/(.+)\/3d$/,           fn: m => viewRun3D(m[1]) },
  { re: /^#\/run\/(.+)\/balloon$/,      fn: m => viewBalloon(ROOT, m[1]) },     // W6: BL-style balloon
  { re: /^#\/run\/(.+)\/evolution$/,    fn: m => viewEvolution(ROOT, m[1]) },
  { re: /^#\/run\/(.+)\/archive$/,      fn: m => viewRunArchive(m[1]) },
  { re: /^#\/run\/(.+)$/,               fn: m => viewRunDetail(m[1]) },
  { re: /^#\/compare$/,                 fn: () => viewCompare() },
  { re: /^#\/briefs$/,                  fn: () => viewBriefs() },
  { re: /^#\/compose$/,                 fn: () => viewCompose() },
  { re: /^#\/launch$/,                  fn: () => viewLaunch() },
  { re: /^#\/typologies$/,              fn: () => viewTypologies() },
  { re: /^#\/typology\/([^\/?#]+)$/,    fn: m => viewTypologySandbox(ROOT, m[1]) },
  { re: /^#\/glossary$/,                fn: () => viewGlossary() },
];

function route() {
  // Dispose any 3D scene: every init3d-tagged container carries [data-v3d] (the 3D page's
  // #view3d-wrap, the run page's inline viewer, the evolution player). Sweeping the marker — rather
  // than only the old #view3d-wrap id — kills every live renderer and rAF loop while its container
  // is still attached, so no WebGL context or animation loop outlives its view.
  document.querySelectorAll("[data-v3d]").forEach(el => { if (el._dispose3d) el._dispose3d(); });
  // Clear status timer if navigating away
  if (!location.hash.startsWith("#/status") && location.hash !== "" && location.hash !== "#/") {
    clearStatusTimer();
  }
  // The nav run-control pill: #view-root is replaced but the nav never is, so re-invoking it here
  // keeps wiring fresh on every route/theme-observer re-render; the sig-skip keeps an armed click
  // alive when nothing changed (stateless-idempotent; never tagged [data-v3d]).
  renderNavPill();

  const fresh = document.createElement("div");
  fresh.id = "view-root"; fresh.className = ROOT.className; fresh.setAttribute("role", "main");
  ROOT.replaceWith(fresh); ROOT = fresh;
  const hash = location.hash || "#/home";
  const path = hash.split("?")[0];
  for (const { re, fn } of ROUTES) {
    const m = path.match(re);
    if (m) { updateNav(path); return fn(m); }
  }
  ROOT.innerHTML = "";
  const p = document.createElement("p"); p.className = "muted";
  p.textContent = "Unknown view: " + hash;  // textContent: never inject URL as HTML
  ROOT.appendChild(p);
}

function updateNav(hash) {
  document.querySelectorAll("#app-nav ul li a").forEach(a => {
    const h = a.getAttribute("href");
    const isActive =
      (h === "#/home" && (hash === "#/" || hash === "#/home")) ||
      (h === "#/status" && hash === "#/status") ||
      (h === "#/campaigns" && (hash === "#/campaigns" || hash.startsWith("#/campaign/"))) ||
      (h === "#/runs" && (hash === "#/runs" || (hash.startsWith("#/run/") && !hash.endsWith("/3d")))) ||
      (h === "#/compare" && hash === "#/compare") ||
      (h === "#/briefs" && hash === "#/briefs") ||
      (h === "#/compose" && hash === "#/compose") ||
      (h === "#/launch" && hash === "#/launch") ||
      (h === "#/typologies" && (hash === "#/typologies" || hash.startsWith("#/typology/"))) ||
      (h === "#/glossary" && hash === "#/glossary");
    a.classList.toggle("active", isActive);
  });
}

window.addEventListener("hashchange", route);

// ── Shared helpers ─────────────────────────────────────────────────

function skel(msg = "") {
  ROOT.innerHTML = `<div class="stack skeleton" style="gap:18px;opacity:0.6">
    <div class="skeleton-block" style="height:2.2rem;width:min(260px,60%)"></div>
    <div class="skeleton-block" style="height:1rem;width:min(400px,80%)"></div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:6px;overflow:hidden">
      ${[0,0,0,0].map(()=>`<div class="skeleton-block" style="height:64px"></div>`).join("")}
    </div>
    <div class="skeleton-block" style="height:180px"></div>
    ${msg ? `<p class="muted" style="opacity:0.5;font-size:0.82rem">${esc(msg)}</p>` : ""}
  </div>`;
}

function errBanner(msg) {
  return `<div class="alert error" role="alert"><b>Error:</b> ${esc(msg)}</div>`;
}

/** "40 % better" / "3 % worse" / "–": score change from the starting design (lower score = better).
 *  A start that failed (1000 penalty) has no meaningful percentage. */
const CMP_LABEL = {
  bw_h_deg: "Beamwidth, horizontal", bw_v_deg: "Beamwidth, vertical", di_db: "Directivity index",
  on_axis_db: "On-axis response", ripple_h_db: "Polar ripple, horizontal", ripple_v_db: "Polar ripple, vertical",
};

function betterPct(seed, best) {
  if (best == null || !seed || seed >= 900) return "–";
  const p = (1 - best / seed) * 100;
  if (Math.abs(p) < 0.05) return "no change";
  return `${Math.abs(p).toFixed(0)} % ${p > 0 ? "better" : "worse"}`;
}

/** Brief, non-blocking message in the corner (replaces alert()). */
function showToast(msg, kind = "info") {
  let box = document.getElementById("toasts");
  if (!box) { box = document.createElement("div"); box.id = "toasts"; box.setAttribute("aria-live", "polite"); document.body.appendChild(box); }
  const t = document.createElement("div"); t.className = "toast " + kind; t.textContent = msg;
  box.appendChild(t); setTimeout(() => t.remove(), kind === "error" ? 9000 : 4500);
}

function pill(text, cls) {
  return `<span class="pill ${cls}">${esc(text)}</span>`;
}

function timeSince(iso) {
  if (!iso) return "–";
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function failurePills(obj) {
  return Object.entries(obj || {})
    .filter(([, v]) => v > 0)
    .map(([k, v]) => `<span class="pill bad">${esc(v + "× " + k.replace(/_/g, " "))}</span>`)
    .join(" ") || pill("none", "good");
}

function dimStr(dims) {
  if (!dims) return "–";
  return `${fmtMm(dims.mouth_w_mm)} × ${fmtMm(dims.mouth_h_mm)} × ${fmtMm(dims.depth_mm)}`;
}

// ── View HOME ──────────────────────────────────────────────────────

async function viewHome() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel("Loading dashboard…");
  let statusData, campaigns, runs, leaders;
  try {
    [statusData, campaigns, runs, leaders] = await Promise.all([
      api("/api/status"),
      api("/api/campaigns").catch(() => []),
      api("/api/runs").catch(() => []),
      api("/api/leaders").catch(() => []),
    ]);
  } catch (e) {
    ROOT.innerHTML = errBanner("Could not load home: " + e.message);
    return;
  }

  const cur = statusData.current;
  const lock = statusData.gpu_lock;
  const steps = (statusData.queue_log || {}).steps || [];

  // GPU / running card
  let gpuCard;
  if (cur && lock && lock.alive) {
    const budget = cur.budget || 1;
    const pct = Math.min(100, Math.round((cur.n / budget) * 100));
    const over = !!(cur.budget && cur.n > cur.budget);
    const budgetCls = over ? "bad" : pct >= 90 ? "warn" : "";
    const nFail = Object.values(cur.failures || {}).reduce((a, v) => a + v, 0);
    const barCls = over ? "bad" : nFail / Math.max(cur.n, 1) > 0.3 ? "warn" : "";
    const eta = cur.eta_min != null ? `~${Math.round(cur.eta_min)} min left` : "";
    const rate = cur.rate_per_h != null ? `${cur.rate_per_h.toFixed(0)}/h` : "";
    gpuCard = `<div class="card status-card running-card">
      <div class="label">▶ Running: ${esc(cur.name || cur.id)}</div>
      <div style="margin:6px 0">
        <div class="progress-wrap"><div class="progress-bar ${barCls}" style="width:${pct}%"></div></div>
        <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:0.8rem;color:var(--muted)">
          <span><b class="${budgetCls}">${cur.n.toLocaleString()} / ${budget.toLocaleString()} evals (${pct}%)${over ? " over budget" : ""}</b></span>
          <span>${eta}</span>
        </div>
      </div>
      <div class="kpis" style="margin-top:4px">
        <div class="kpi"><span>Best score</span><b>${fmt(cur.best_j)}</b></div>
        <div class="kpi"><span>Started score</span><b>${fmt(cur.seed_j && cur.seed_j < 900 ? cur.seed_j : null)}</b></div>
        <div class="kpi"><span>Rate</span><b>${rate || "–"}</b></div>
        <div class="kpi"><span>Failures</span><b>${esc(Object.values(cur.failures || {}).reduce((a, v) => a + v, 0))}</b></div>
      </div>
      <div class="btn-row" style="margin-top:8px">
        <a class="btn primary" href="#/run/${esc(cur.id)}">Open run →</a>
        <a class="btn" href="#/status">Status</a>
      </div>
    </div>`;
  } else {
    gpuCard = `<div class="card status-card gpu-idle-card">
      <div class="label">GPU</div>
      <div class="value">Idle</div>
      <div class="btn-row" style="margin-top:8px">
        <a class="btn primary" href="#/launch">Launch a dry-run →</a>
        <a class="btn" href="#/status">Status</a>
      </div>
    </div>`;
  }

  // Queue timeline
  let timelineHtml = "";
  if (steps.length) {
    timelineHtml = `<div class="card" style="min-width:0">
      <div class="eyebrow" style="margin-bottom:10px">Overnight queue — ${esc((statusData.queue_log || {}).name || "")}</div>
      <div class="timeline">
        ${steps.slice(-20).map(s => {
          const dot = s.skipped ? "skip" : s.exit == null ? "run" : s.exit === 0 ? "done" : "failed";
          const dur = (s.started && s.ended)
            ? (() => { const ms = new Date(s.ended) - new Date(s.started); return ms > 60000 ? (ms/60000).toFixed(1)+"m" : (ms/1000).toFixed(0)+"s"; })()
            : s.skipped ? "skipped" : s.started ? "running" : "";
          const exitNote = s.exit != null && s.exit !== 0 ? `<span class="tl-exit-bad">exit ${s.exit}</span>` : "";
          return `<div class="tl-row">
            <div class="tl-dot ${dot}" title="${dot}"></div>
            <span class="tl-name">${esc(s.name)}</span>
            <span class="tl-time">${esc(dur)} ${exitNote}</span>
          </div>`;
        }).join("")}
      </div>
    </div>`;
  }

  // Best horn per brief: from /api/leaders (latest campaign of the strongest tier per brief, ranked by
  // median score; never from raw runs, which include superseded and out-of-envelope designs)
  let bestBriefHtml = "";
  if (leaders.length) {
    const rows = leaders.map(l => {
      const verdict = l.tier === "compare"
        ? (l.clearly_ahead ? pill("clearly ahead", "good") : pill("not separated", "warn"))
        : pill("screen only", "warn");
      const link = l.best_run_id ? `href="#/run/${esc(l.best_run_id)}"` : "";
      return `<a class="best-brief-row" ${link}>
        <div>
          <div class="bbr-name">${esc(l.brief)}</div>
          <div class="bbr-meta">${esc(l.family)} · ${esc(l.dims ? dimStr(l.dims) : "–")} · ${verdict}</div>
          <div class="bbr-meta muted">${esc(l.tier)} campaign, ${esc(l.n_families)} families${l.runner_up ? `; next: ${esc(l.runner_up)} (+${fmt(l.gap)})` : ""}</div>
        </div>
        <div class="bbr-score" title="median score over repeats (lower is better)">${fmt(l.median_j)}</div>
      </a>`;
    }).join("");
    bestBriefHtml = `<div class="card">
      <div class="eyebrow" style="margin-bottom:10px">Best horn per brief</div>
      <p class="muted" style="margin:0 0 8px;font-size:0.82rem">Median score of the leading family in the latest campaign for each brief (lower is better). Size is the outer mouth width × height × depth of its best design.</p>
      <div class="best-brief-grid">${rows}</div>
    </div>`;
  } else {
    bestBriefHtml = `<div class="card"><div class="eyebrow">Best horn per brief</div><p class="muted">No scored campaigns yet. Run a screen campaign from Launch.</p></div>`;
  }

  const guideHtml = `<details class="card guide" ${(() => { try { return localStorage.getItem("hl-guide-seen") ? "" : "open"; } catch { return "open"; } })()} id="guide">
    <summary><b>How to use this</b> <span class="muted">— four steps from a target to a printable horn</span></summary>
    <ol class="guide-steps">
      <li><b>Pick a brief</b> (<a href="#/briefs">Briefs</a>): the target coverage, frequency band and maximum size. Save a copy to change it.</li>
      <li><b>Choose horn families</b> (<a href="#/typologies">Typologies</a>): classical horns, hybrids and mesher families. Families that cannot meet the brief are greyed out.</li>
      <li><b>Run a search</b> (<a href="#/launch">Launch</a>): start with <i>dry-run</i> (checks the shapes mesh, seconds), then <i>screen</i> (minutes per family). Only one GPU job runs at a time.</li>
      <li><b>Read the results</b> (<a href="#/campaigns">Campaigns</a> → a family → its run): beamwidth and directivity against the target, the horn's size and cross-section, the time-lapse of the search, then <i>Export STEP for CAD</i>.</li>
    </ol>
    <p class="muted" style="margin:6px 0 0">Lower score = closer to the brief. Hover any underlined label for what it means, or open the <a href="#/glossary">Glossary</a>.</p>
  </details>`;

  const quickLinks = `<div class="btn-row">
    <a class="btn" href="#/runs">Browse runs</a>
    <a class="btn" href="#/campaigns">Campaigns</a>
    <a class="btn" href="#/briefs">Briefs</a>
  </div>`;

  ROOT.innerHTML = `<div class="stack" style="gap:22px">
    <div>
      <div class="eyebrow">Dashboard</div>
      <h2>Home</h2>
    </div>
    ${guideHtml}
    ${gpuCard}
    ${bestBriefHtml}
    ${timelineHtml}
    ${quickLinks}
  </div>`;
  document.getElementById("guide")?.addEventListener("toggle", e => {
    try { if (!e.target.open) localStorage.setItem("hl-guide-seen", "1"); else localStorage.removeItem("hl-guide-seen"); } catch {}
  });
}

// ── View 1: Status ─────────────────────────────────────────────────

let _statusTimer = null;
let _statusRendered = false;

function clearStatusTimer() {
  if (_statusTimer) { clearInterval(_statusTimer); _statusTimer = null; }
  _statusRendered = false;
}

async function viewStatus() {
  const ROOT = currentRoot();     // this view's own container (see route())
  if (!_statusRendered) skel("Loading status…");
  let data, jobs;
  try {
    [data, jobs] = await Promise.all([
      api("/api/status"),
      api("/api/jobs").catch(() => []),   // the stop affordance correlates the GUI's own jobs
    ]);
  } catch (e) {
    if (!_statusRendered) ROOT.innerHTML = errBanner("Could not load status: " + e.message);
    return;
  }

  if (!_statusRendered) {
    if (ROOT !== currentRoot()) return;   // the user navigated away while this loaded
  renderStatus(data, jobs);
    _statusRendered = true;
  } else {
    updateStatusInPlace(data, jobs);
  }

  if (!_statusTimer) {
    _statusTimer = setInterval(() => {
      const h = location.hash;
      if (h !== "#/status" && h !== "" && h !== "#/") { clearStatusTimer(); return; }
      if (document.hidden) return;
      viewStatus();
    }, 10000);
  }
}

function renderStatus(data, jobs = []) {
  const lock = data.gpu_lock;
  const disk = data.disk || {};
  const ql = data.queue_log || {};
  const wl = data.watchdog_log || [];
  const steps = ql.steps || [];
  const cur = data.current;
  const aff = stopAffordanceFor(jobs, lock);

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">System</div>
        <h2>Status</h2>
      </div>
      <div class="status-grid" id="st-cards">
        <div id="st-lock">${lockCardHtml(lock)}</div>
        <div class="status-card">
          <div class="label">${tip("dims", "VRAM used")}</div>
          <div class="value num" id="st-vram">${data.vram_mib != null ? data.vram_mib.toFixed(0) : "–"} <small style="font-size:1rem">MiB</small></div>
        </div>
        <div class="status-card">
          <div class="label">${tip("julia", "Solver hosts")}</div>
          <div class="value num" id="st-julia">${data.julia_procs ?? "–"}</div>
        </div>
        <div class="status-card">
          <div class="label">Disk free</div>
          <div class="value num" id="st-disk-val">${disk.free_gb != null ? disk.free_gb.toFixed(1) : "–"} <small style="font-size:1rem">GB</small></div>
          <div class="sub" id="st-disk-sub">${disk.total_gb != null ? disk.total_gb.toFixed(0) + " GB total · " + (100 - disk.free_gb / disk.total_gb * 100).toFixed(0) + "% used" : ""}</div>
        </div>
      </div>
      <div id="st-current-card">${currentRunCard(cur, aff)}</div>
      <div class="btn-row">
        <button id="btn-refresh">↻ Refresh</button>
        <button id="btn-gpuclean" class="danger" ${lock && lock.alive ? "disabled title='A live job holds the GPU lock'" : ""}>gpu-clean</button>
      </div>
      <div class="stack" style="gap:8px">
        <div class="eyebrow">Queue log — ${esc(ql.name || "")}</div>
        ${steps.length ? queueTimelineHtml(steps) : ""}
        <div class="log-tail" id="queue-tail" aria-label="queue log">${esc((ql.tail || []).join("\n"))}</div>
      </div>
      <div class="stack" style="gap:8px">
        <div class="eyebrow">Watchdog log</div>
        <div class="log-tail" id="watchdog-tail" aria-label="watchdog log">${esc(wl.join("\n"))}</div>
      </div>
    </div>`;

  document.getElementById("btn-refresh").onclick = () => { _statusRendered = false; viewStatus(); };
  wireStopButton(aff);
  pillFeed(data, jobs);   // the nav pill shares this poll's look (no extra fetch on this view)
  document.getElementById("btn-gpuclean").onclick = async () => {
    if (!confirm("Run gpu-clean? This kills stale Julia/BEAT processes.")) return;
    const r = await post("/api/gpu-clean", {});
    if (r.error) showToast(r.error, "error");
    else showToast("gpu-clean: " + (r.text || "done").trim().split(String.fromCharCode(10)).slice(-1)[0], "good");
    _statusRendered = false;
    viewStatus();
  };
}

function lockCardHtml(lock) {
  if (lock) {
    const ago = timeSince(lock.start_time);
    const alivePill = lock.alive ? pill("alive", "good") : pill("stale", "warn");
    return `<div class="status-card gpu-lock-card" aria-label="GPU lock">
      <div class="label">${tip("lock", "GPU lock")}</div>
      <div class="value">${esc(lock.user || "–")}</div>
      <div class="sub" title="${esc(lock.command)}" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:30ch">${esc(lock.command || "–")}</div>
      <div class="sub">PID ${esc(lock.pid)} · started ${esc(ago)} ${alivePill}</div>
    </div>`;
  }
  return `<div class="status-card gpu-idle-card" aria-label="GPU lock">
    <div class="label">${tip("lock", "GPU lock")}</div>
    <div class="value good-text">Free</div>
  </div>`;
}

/** The stop-run affordance for the Status page (pure): JobManager only tracks GUI-started jobs, so
 *  the GUI's honest correlation is by job ownership. One GPU job at a time makes "a GUI-started GPU
 *  job is running" unambiguous — that job IS the current run, labelled with its kind + argv tail.
 *  A lock held with NO GUI GPU job = a run started outside the GUI (terminal): never a button.
 *  Nothing running => idle => nothing rendered (absence is honest).
 *  Returns {state: "gui-cancel"|"external"|"idle", job?, note?, lock?}. */
function stopAffordanceFor(jobs, lock) {
  const list = Array.isArray(jobs) ? jobs : [];
  const runningGpu = list.filter(j => j && j.status === "running" && j.gpu === true);
  if (runningGpu.length) {
    const j = runningGpu[runningGpu.length - 1];   // the newest one owns the GPU (one GPU at a time)
    return { state: "gui-cancel", job: j,
             note: runningGpu.length > 1 ? `${runningGpu.length} GUI GPU jobs are running — the newest one owns the GPU lock` : "" };
  }
  const l = (lock && typeof lock === "object") ? lock : null;
  if (l && l.alive) return { state: "external", lock: l };
  return { state: "idle" };
}

/** One stop-region state as HTML (pure): gui-cancel => the danger Stop button + what it targets;
 *  external => the danger Kill run button (owner 2026-10-25: the GUI MAY kill the externally-
 *  started run that holds OUR gpu lock — the lock file records exactly which pid holds it, so the
 *  kill is pid-targeted + gpu-clean, never arbitrary); idle => nothing. */
function stopRegionHtml(aff) {
  if (!aff || aff.state === "idle") return "";
  if (aff.state === "external") {
    const l = aff.lock || {};
    const pid = l.pid != null ? l.pid : "?";
    return `<div style="margin-top:8px">
      <div class="btn-row" style="flex-wrap:wrap;gap:8px;align-items:center">
        <button class="btn danger" id="btn-kill-run" title="Kills the externally-started run that holds our GPU lock: pid ${esc(pid)} with its child tree, then a gpu-clean pass">Kill run</button>
        <span class="mono muted" style="font-size:0.75rem">external run · pid ${esc(pid)}</span>
      </div>
      <div class="hint" id="st-kill-msg" role="status" style="margin:4px 0 0"></div>
    </div>`;
  }
  const j = aff.job || {};
  const tail = String(Array.isArray(j.argv) ? j.argv.slice(1).join(" ") : "").slice(0, 90);
  return `<div style="margin-top:8px">
    <div class="btn-row" style="flex-wrap:wrap;gap:8px;align-items:center">
      <button class="btn danger" id="btn-stop-run" title="Stops the run: the job's process tree is killed and a gpu-clean pass runs after GPU jobs">Stop run</button>
      <span class="mono muted" style="font-size:0.75rem" id="st-stop-what">GUI job ${esc(j.id || "")} · ${esc(j.kind || "")}${tail ? " · " + esc(tail) : ""}</span>
    </div>
    ${aff.note ? `<div class="hint" style="margin:4px 0 0">${esc(aff.note)}</div>` : ""}
    <div class="hint" id="st-stop-msg" role="status" style="margin:4px 0 0"></div>
  </div>`;
}

/** Shared two-step arm for dangerous one-liner buttons (no confirm() dialogs): click 1 arms — the
 *  button reads opts.armLabel, opts.armedMsgHtml (HTML) states what the second click does, and the
 *  arm clears itself after 5 s; click 2 restores the face label and runs opts.fire(btn, msgEl). The
 *  message element is looked up by id at click time, so re-renders may replace it. Shared by the
 *  Status stop button, the nav pill's stop and the nav pill's resume. */
function wireTwoStepArm(btn, msgId, opts) {
  if (!btn) return;
  const face = btn.textContent;
  let armed = false, timer = null;
  const msg = () => (typeof msgId === "string" ? document.getElementById(msgId) : msgId);
  const disarm = () => {
    armed = false;
    if (timer) { clearTimeout(timer); timer = null; }
    if (btn.isConnected) {
      btn.textContent = face;
      btn.removeAttribute("aria-pressed");
      const m = msg();
      if (m) m.innerHTML = "";
    }
  };
  btn.onclick = async () => {
    if (!armed) {
      armed = true;
      btn.textContent = opts.armLabel;
      btn.setAttribute("aria-pressed", "true");
      const m = msg();
      if (m) m.innerHTML = opts.armedMsgHtml || "";
      if (opts.onArm) opts.onArm(m);
      timer = setTimeout(disarm, 5000);
      return;
    }
    if (timer) { clearTimeout(timer); timer = null; }
    armed = false;
    btn.textContent = face;
    btn.removeAttribute("aria-pressed");
    await opts.fire(btn, msg());
  };
}

/** Two-step arm for the Status Stop button (no confirm() dialogs): the first click arms ("Confirm
 *  stop", auto-disarms after 5 s), the second sends the cancel and shows the honest post-action
 *  status. Called on every status render/refresh — the current state always comes from the last
 *  poll. */
function wireStopButton(aff) {
  const btn = document.getElementById("btn-stop-run");
  if (btn && aff && aff.state === "gui-cancel" && aff.job) {
    wireTwoStepArm(btn, "st-stop-msg", {
      armLabel: "Confirm stop",
      armedMsgHtml: `<span class="warn-text">click again to confirm — the job's process tree is killed and a gpu-clean pass runs</span>`,
      fire: async (b, m) => {
        b.disabled = true;
        if (m) m.textContent = "stop requested — the run dir records the stop; wait for the job to exit + a gpu-clean pass";
        const r = await post("/api/job/" + aff.job.id + "/cancel", {});
        if (r && r.error && m) m.innerHTML = `<span class="warn-text">${esc(r.error)}</span>`;
        else showToast("Stop requested — the job is killed and a gpu-clean pass runs after GPU jobs.", "info");
      }
    });
    return;
  }
  // External state (owner 2026-10-25): the run holding our GPU lock was NOT started by the GUI —
  // the kill targets exactly the pid the lock file records (+ its child tree), then gpu-clean.
  const kill = document.getElementById("btn-kill-run");
  const lock = aff && aff.state === "external" ? aff.lock : null;
  if (kill && lock) {
    const pid = lock.pid != null ? lock.pid : "?";
    wireTwoStepArm(kill, "st-kill-msg", {
      armLabel: "Confirm kill",
      armedMsgHtml: `<span class="warn-text">click again to confirm — kills the externally-started process holding the GPU lock (pid ${esc(pid)}) with its child tree, then a gpu-clean pass</span>`,
      fire: async (b, m) => {
        b.disabled = true;
        if (m) m.textContent = "kill requested…";
        const r = await post("/api/stop-current", {});
        if (r && r.error) { b.disabled = false; if (m) m.innerHTML = `<span class="warn-text">${esc(r.error)}</span>`; }
        else {
          if (m) m.textContent = `killed pid ${r && r.killed != null ? r.killed : "?"} — gpu-clean pass ran`;
          showToast("Run killed — a gpu-clean pass ran after it.", "info");
        }
      }
    });
  }
}

// ── Toolbar run-control pill (left nav, every view) ─────────────────────────────────────────
// Owner decision: the run Stop control ALSO lives in the left nav as a compact pill on every view,
// plus a Resume affordance for stopped GUI search runs. The nav markup is a static file served
// verbatim (server.py::_static — not rendered per request), so app.js owns the pill end to end and
// index.html stays untouched. Data: the Status page's existing /api/status + /api/jobs poll feeds
// the pill, and a small dedicated poll (10 s, skipped while the tab is hidden; /api/jobs +
// /api/status + /api/runs) covers every other route. The holder is injected once below the nav
// links; every re-render is content-only and stateless-idempotent (route() / theme MutationObserver
// simply redraw it), carries no 3D disposal marker (route()'s sweep ignores it), styled with the
// existing theme vars only.

/** The run-dir line pattern the search log carries (same shape renderJobs keys its "Open run" link
 *  on; data.py RUN_ID modulo the anchors). */
const RUN_IN_LOG = /[0-9]{8}T[0-9]{6}Z-[a-z]+-[0-9a-f]{6}/g;

/** Pure: the POST /api/preview + /api/jobs args to resume a stopped search job under the LANDED
 *  contract — the CLI's --resume takes a run directory and jobs.py refuses a bare switch, so the
 *  run id is sourced from the job's OWN log (the run-dir lines it printed) and validated against
 *  the /api/runs summaries: the run must exist and must not have exhausted its recorded budget
 *  (an exhausted run is finished — budget top-ups stay a deliberate owner action, never a pill
 *  side-effect). Omitted on purpose: --config (the CLI reuses run_dir/config.yaml, so a config
 *  edited after the stop can never poison the replay) and --budget (a per-invocation NEW-eval cap;
 *  omitting reuses the run's own config budget). mode rides through from the run's summary rows —
 *  the CLI's resume default is screen and run.json["mode"] gets rewritten, so a verify/final run
 *  would silently drop its mode without it. null when no resumable run can be sourced: the pill
 *  degrades to an honest note instead of a button. */
function resumeArgsFor(job, runs) {
  if (!job || job.kind !== "search" || !Array.isArray(job.log_tail)) return null;
  const byId = new Map((Array.isArray(runs) ? runs : []).filter(r => r && r.id).map(r => [r.id, r]));
  const seen = new Set();
  for (const line of job.log_tail) {
    const m = String(line).match(RUN_IN_LOG);
    if (m) m.forEach(id => seen.add(id));
  }
  const cands = [...seen].map(id => byId.get(id)).filter(Boolean)
    .filter(r => r.budget == null || r.n < r.budget)
    .sort((a, b) => String(a.id).localeCompare(String(b.id)));
  const r = cands.slice(-1)[0];
  if (!r) return null;                                   // nothing in the runs list backs the log line
  const args = { resume: r.id };
  if (r.mode) args.mode = r.mode;                        // never let the screen default rewrite a mode
  return args;
}

/** Pure: may the run-detail "Continue this run" control be shown? Only a run whose stored command
 *  was a search: the CLI then loads <run>/config.yaml on --resume, so the same configuration is
 *  reused. A missing/null command (or any other command) renders no card at all. */
function continueRunAvailable(d) {
  return !!(d && typeof d.command === "string" && d.command.trim().startsWith("hornlab-search search"));
}

/** Pure: the POST /api/jobs args for adding N NEW evaluations to an opened search run. Mirrors
 *  resumeArgsFor's contract: no --config (the CLI reuses the run's stored config.yaml), no
 *  --max-evals (it counts replays too; --budget is the NEW-evaluation cap), and mode only when the
 *  run declares one (otherwise the CLI's screen default would rewrite the run's mode). Returns
 *  {args, n} on valid input, {error} on blank id / non-integer / out-of-range nonsense. */
function continueRunArgs(run, rawN) {
  const id = run && typeof run.id === "string" ? run.id.trim() : "";
  if (!id) return { error: "this run has no id to resume" };
  let n;
  if (typeof rawN === "number") {
    n = rawN;
  } else if (typeof rawN === "string" && /^[0-9]+$/.test(rawN.trim())) {
    n = Number(rawN.trim());
  } else {
    return { error: "enter a whole number of evaluations between 1 and 5000" };
  }
  if (!Number.isInteger(n) || n < 1 || n > 5000)
    return { error: "enter a whole number of evaluations between 1 and 5000" };
  const args = { resume: id, budget: n };
  if (run.mode) args.mode = run.mode;                    // never let the screen default rewrite a mode
  return { args, n };
}

/** Pure: is this job a stopped GUI search run a Resume affordance may target? Cancelled by the
 *  GUI, or failed with a real exit code. "ended (GUI restarted)" is deliberately excluded: whether
 *  that subprocess still runs is unknown to this GUI session, and resuming it could double-run a
 *  solver. */
function resumeableSearchJob(j) {
  return !!j && j.kind === "search" &&
    (j.status === "cancelled" || (j.status === "failed" && j.returncode != null && j.returncode !== 0));
}

/** Pure decision for the nav pill: the Status page's stop rule first (a GUI GPU job running →
 *  stop; a foreign lock → external), then the newest stopped search worth resuming; otherwise idle,
 *  which renders nothing (absence honest). Returns {state: "stop"|"external"|"resume"|"idle",
 *  job?, args?, lock?, note?}. External beats resume: with the GPU held the launch would only be
 *  refused, so the pill stays quiet about it. */
function toolbarPillFor(jobs, lock, runs) {
  const stop = stopAffordanceFor(jobs, lock);
  if (stop.state === "gui-cancel") return { state: "stop", job: stop.job, note: stop.note };
  if (stop.state === "external") return { state: "external", lock: stop.lock };
  const list = Array.isArray(jobs) ? jobs : [];
  const cands = list.filter(resumeableSearchJob);
  if (cands.length) {
    const job = cands.slice().sort((a, b) => String(a.id).localeCompare(String(b.id))).slice(-1)[0];
    return { state: "resume", job, args: resumeArgsFor(job, runs) };
  }
  return { state: "idle" };
}

/** Pure HTML for one pill state (compact, nav-width, existing theme classes/vars only): stop → the
 *  danger button + what it targets; external → the danger KILL run button (owner 2026-10-25: the
 *  GUI MAY kill the externally-started run that holds OUR gpu lock — the lock file records exactly
 *  which pid holds it, so the kill is pid-targeted + gpu-clean, never arbitrary); resume → the
 *  primary button + what it resumes (an honest note instead of a button when the argv carries no
 *  --config); idle → a small always-visible "no run in progress" indicator (owner directive: the
 *  pill is a VISIBLE toolbar control at all times, not honest-absence). */
function toolbarPillHtml(pill) {
  const state = pill ? pill.state : "idle";
  const wrap = inner =>
    `<div class="nav-runctl" style="padding:6px 16px 4px;display:grid;gap:4px;margin-top:2px">${inner}</div>`;
  const BTN = "width:100%;padding:5px 10px;font-size:0.8rem;line-height:1.25";
  const SUB = "font-size:0.64rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap";
  const MSG = "font-size:0.66rem;line-height:1.3;white-space:normal";
  if (state === "external") {
    const l = pill.lock || {};
    const pid = l.pid != null ? l.pid : "?";
    return wrap(`<button class="btn danger" id="tb-kill-run" style="${BTN}" title="Kills the externally-started run that holds our GPU lock: pid ${esc(pid)} with its child tree, then a gpu-clean pass">■ Kill run</button>
      <span class="mono muted" style="${SUB}">external run · pid ${esc(pid)}</span>
      <span id="tb-kill-msg" role="status" style="${MSG}"></span>`);
  }
  if (state === "idle") {
    return wrap(`<span class="pill" style="display:block;${SUB};color:var(--muted)" title="No run in progress — start one from Compose or Launch">no run in progress</span>`);
  }
  const j = pill.job || {};
  if (state === "stop") {
    return wrap(`<button class="btn danger" id="tb-stop-run" style="${BTN}" title="Stops the run: process tree killed + gpu-clean">■ Stop</button>
      <span class="mono muted" style="${SUB}">job ${esc(j.id || "?")} · ${esc(j.kind || "?")}</span>
      ${pill.note ? `<span class="warn-text" style="${MSG}">${esc(pill.note)}</span>` : ""}
      <span id="tb-stop-msg" role="status" style="${MSG}"></span>`);
  }
  if (state === "idle") {
    return wrap(`<span class="pill" style="display:block;${SUB};color:var(--muted)" title="No run in progress — start one from Compose or Launch">no run in progress</span>`);
  }
  if (!pill.args) {
    return wrap(`<span class="pill warn" style="display:block;${SUB}" title="The stopped search's log names no resumable run folder (or its budget is exhausted) — a resume needs that run directory">stopped search — no resumable run folder</span>
      <span class="mono muted" style="${SUB}">job ${esc(j.id || "?")} · no resume from here</span>`);
  }
  return wrap(`<button class="btn primary" id="tb-resume-run" style="${BTN}" title="Relaunches the stopped search from its run folder — cached evals replay free; budget is per invocation">▶ Resume search</button>
    <span class="mono muted" style="${SUB}">job ${esc(j.id || "?")} · resume ${esc(pill.args.resume)}</span>
    <span id="tb-resume-msg" role="status" style="${MSG}"></span>`);
}

/** The resume contract probe: /api/preview runs jobs.build_argv with the SAME validation a launch
 *  would (and zero side effects), so the resume can only fire when the server's OWN previewed
 *  command really carries a --resume* flag. If the landed jobs.py names its switch differently (or
 *  an older build ignores args.resume), the probe returns not-ok and the button degrades to an
 *  honest note — never a silently started fresh search. */
async function resumePreview(pill) {
  const r = await post("/api/preview", { kind: "search", args: pill.args });
  if (r.error) return { ok: false, why: `the server refused the resume: ${r.error}` };
  const toks = String(r.command || "").split(" ");
  if (!toks.some(t => t.startsWith("--resume")))
    return { ok: false, why: "this server build adds no --resume flag — a launch would start a FRESH search, not a resume; nothing was started" };
  return { ok: true, command: String(r.command || "") };
}
/** Wires the pill's one button, stateless per render: each re-render rebuilds content and re-arms
 *  from scratch, so an armed state never fires at a stale job. `root` scopes the queries so the
 *  duplicated holders (links column + nav-footer circle) wire independently. The resume arm probes
 *  the server's contract on the ARM click and blocks the confirm click (with the honest reason)
 *  when the previewed argv shows no resume flag. */
function wireToolbarPill(pill, root = document, idsuf = "") {
  const stopBtn = root.querySelector(`#tb-stop-run${idsuf}`);
  if (stopBtn && pill.state === "stop" && pill.job) {
    wireTwoStepArm(stopBtn, root.querySelector(`#tb-stop-msg${idsuf}`), {
      armLabel: "Confirm stop",
      armedMsgHtml: `<span class="warn-text">click again to confirm — process tree killed + gpu-clean</span>`,
      fire: async (b, m) => {
        b.disabled = true;
        if (m) m.textContent = "stop requested — wait for the job to exit + the gpu-clean pass";

        const r = await post("/api/job/" + pill.job.id + "/cancel", {});
        if (r && r.error) { if (m) m.innerHTML = `<span class="warn-text">${esc(r.error)}</span>`; }
        else {
          showToast("Stop requested — the job is killed and a gpu-clean pass runs after GPU jobs.", "info");
          if (m) m.textContent = "stop requested";
          pollNavOnce();
        }
      }
    });
    return;
  }
  // External state (owner 2026-10-25): the pill's Kill run targets exactly the pid recorded in OUR
  // gpu lock file (the externally-started run + its child tree) and then gpu-clean.
  const killBtn = root.querySelector(`#tb-kill-run${idsuf}`);
  if (killBtn && pill.state === "external") {
    wireTwoStepArm(killBtn, root.querySelector(`#tb-kill-msg${idsuf}`), {
      armLabel: "Confirm kill",
      armedMsgHtml: `<span class="warn-text">click again to confirm — kills the externally-started process holding our GPU lock (its pid is in the tooltip) with its child tree, then a gpu-clean pass</span>`,
      fire: async (b, m) => {
        b.disabled = true;
        if (m) m.textContent = "kill requested…";
        const r = await post("/api/stop-current", {});
        if (r && r.error) { b.disabled = false; if (m) m.innerHTML = `<span class="warn-text">${esc(r.error)}</span>`; }
        else {
          if (m) m.textContent = `killed pid ${r && r.killed != null ? r.killed : "?"} — gpu-clean pass ran`;
          showToast("Run killed — a gpu-clean pass ran after it.", "info");
          pollNavOnce();
        }
      }
    });
    return;
  }
  const rsBtn = root.querySelector(`#tb-resume-run${idsuf}`);
  if (rsBtn && pill.state === "resume") wireResumeArm(rsBtn, root.querySelector(`#tb-resume-msg${idsuf}`), pill);
}

function wireResumeArm(btn, msg, pill) {
  let probe = null;
  wireTwoStepArm(btn, msg, {
    armLabel: "Confirm resume",
    armedMsgHtml: `<span class="warn-text">checking the server's resume contract…</span>`,
    onArm: m => {
      resumePreview(pill).then(res => {
        probe = res;
        if (!m || !m.isConnected) return;
        if (res.ok) {
          m.innerHTML = `<span class="warn-text">click again to confirm — resumes from its run folder; cached evals replay free, budget is per invocation</span>
            <span class="mono muted" style="font-size:0.62rem;line-height:1.3;white-space:normal;word-break:break-all">${esc(res.command)}</span>`;
        } else {
          m.innerHTML = `<span class="warn-text">${esc(res.why)}</span>`;
        }
      });
    },
    fire: async (b, m) => {
      if (!probe || !probe.ok) {
        if (m) m.innerHTML = `<span class="warn-text">${esc(probe ? probe.why : "the server's resume check has not returned — nothing was launched")}</span>`;
        return;
      }
      b.disabled = true;
      if (m) m.textContent = "launching…";
      const r = await post("/api/jobs", { kind: "search", args: pill.args });
      if (r && r.error) {
        b.disabled = false;
        if (m) m.innerHTML = `<span class="warn-text">${esc(r.error)}</span>`;
      } else {
        if (m) m.textContent = `resume launched — job ${r && r.id ? r.id : "?"}`;
        showToast("Resume launched — cached evals replay free; the budget cap applies to its new evals.", "good");
        pollNavOnce();
      }
    }
  });
}

let _pillJobs = null, _pillStatus = null, _pillRuns = null, _pillTimer = null, _pillSig = "";

/** Injects the pill holder once, directly below the nav links (after #app-nav ul, before the
 *  .nav-spacer). The nav is never re-rendered by route() (only #view-root is), but the guard makes
 *  the injection idempotent under any future re-render path. */
function ensureNavRunCtl() {
  let holder = document.getElementById("nav-runctl");
  if (holder && holder.isConnected) return holder;
  const nav = document.getElementById("app-nav");
  if (!nav) return null;
  holder = document.createElement("div");
  holder.id = "nav-runctl";
  const ul = nav.querySelector("ul");
  if (ul) ul.after(holder); else nav.appendChild(holder);
  return holder;
}

function renderNavPill() {
  const holder = ensureNavRunCtl();
  if (!holder) return;
  const pill = toolbarPillFor(_pillJobs, _pillStatus ? _pillStatus.gpu_lock : null, _pillRuns);
  const sig = JSON.stringify(pill);
  if (sig === _pillSig && holder.firstElementChild) return;   // unchanged: keep the wired DOM (an armed click survives the poll)
  _pillSig = sig;
  holder.innerHTML = toolbarPillHtml(pill);
  wireToolbarPill(pill, holder);
}

async function pollNavOnce() {
  const [jobs, st, runs] = await Promise.all([
    api("/api/jobs").catch(() => null),
    api("/api/status").catch(() => null),
    api("/api/runs").catch(() => null),   // run summaries: the resume run-id validation (mode/budget/n)
  ]);
  if (jobs) _pillJobs = jobs;
  if (st) _pillStatus = st;
  if (runs) _pillRuns = runs;
  renderNavPill();
}

/** The Status page's own /api/status + /api/jobs poll feeds the pill too (one shared look, no
 *  extra fetch while that view is open). */
function pillFeed(data, jobs) {
  if (data) _pillStatus = data;
  if (Array.isArray(jobs)) _pillJobs = jobs;
  renderNavPill();
}

function startNavRunPill() {
  renderNavPill();
  pollNavOnce();                      // immediate feed: the resume state should not wait one tick
  if (_pillTimer) return;
  _pillTimer = setInterval(() => { if (!document.hidden) pollNavOnce(); }, 10000);
}

function currentRunCard(cur, aff = null) {
  if (!cur) {
    // the current-run card with no run folder yet: a GUI GPU job is running (startup window) —
    // honest minimal card, no invented progress numbers
    if (!aff || aff.state !== "gui-cancel") return "";
    const j = aff.job || {};
    const tail = String(Array.isArray(j.argv) ? j.argv.slice(1).join(" ") : "").slice(0, 90);
    return `<div class="card running-card" style="margin-top:-4px">
      <div class="eyebrow" style="margin-bottom:6px">Running now</div>
      <div style="font-weight:500">GPU job ${esc(j.kind || "")}${tail ? ` — ${esc(tail)}` : ""}</div>
      <p class="muted" style="font-size:0.82rem;margin:6px 0 0">no run folder written yet — evaluations appear here once the search starts writing.</p>
      ${stopRegionHtml(aff)}
    </div>`;
  }
  const budget = cur.budget || 1;
  const pct = Math.min(100, Math.round((cur.n / budget) * 100));
  const over = !!(cur.budget && cur.n > cur.budget);
  const budgetCls = over ? "bad" : pct >= 90 ? "warn" : "";
  const eta = cur.eta_min != null ? `~${Math.round(cur.eta_min)} min left` : "";
  return `<div class="card running-card" style="margin-top:-4px">
    <div class="eyebrow" style="margin-bottom:6px">Running now</div>
    <div style="font-weight:500">${esc(cur.name || cur.id)}</div>
    <div class="progress-wrap" style="margin:8px 0 4px"><div class="progress-bar ${over ? "bad" : ""}" style="width:${pct}%"></div></div>
    <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:var(--muted)">
      <span><b class="${budgetCls}">${cur.n.toLocaleString()} / ${budget.toLocaleString()} (${pct}%)${over ? " over budget" : ""}</b></span>
      <span>${eta}</span>
    </div>
    <div class="kpis" style="margin-top:8px">
      <div class="kpi"><span>Score: best</span><b>${fmt(cur.best_j)}</b></div>
      <div class="kpi"><span>Score: start</span><b>${fmt(cur.seed_j && cur.seed_j < 900 ? cur.seed_j : null)}</b></div>
      <div class="kpi"><span>Rate</span><b>${cur.rate_per_h ? cur.rate_per_h.toFixed(0) + "/h" : "–"}</b></div>
    </div>
    ${stopRegionHtml(aff)}
  </div>`;
}

function queueTimelineHtml(steps) {
  const shown = steps.slice(-15);
  return `<div class="timeline" style="margin-bottom:8px">
    ${shown.map(s => {
      const dot = s.skipped ? "skip" : s.exit == null ? "run" : s.exit === 0 ? "done" : "failed";
      let dur = "";
      if (s.started && s.ended) {
        const ms = new Date(s.ended) - new Date(s.started);
        dur = ms > 60000 ? (ms / 60000).toFixed(1) + "m" : (ms / 1000).toFixed(0) + "s";
      } else if (s.skipped) { dur = "skipped"; } else if (s.started) { dur = "running"; }
      const exitNote = s.exit != null && s.exit !== 0 ? ` <span class="tl-exit-bad">exit ${s.exit}</span>` : "";
      return `<div class="tl-row">
        <div class="tl-dot ${dot}" title="${dot}"></div>
        <span class="tl-name">${esc(s.name)}</span>
        <span class="tl-time">${esc(dur)}${exitNote}</span>
      </div>`;
    }).join("")}
  </div>`;
}

function updateStatusInPlace(data, jobs = []) {
  const lock = data.gpu_lock;
  const disk = data.disk || {};
  const ql = data.queue_log || {};
  const wl = data.watchdog_log || [];
  const aff = stopAffordanceFor(jobs, lock);

  const sl = document.getElementById("st-lock");
  if (sl) sl.innerHTML = lockCardHtml(lock);

  // the current-run card goes live on the poll: progress numbers refresh, the card appears when a
  // run starts, and the stop affordance always reflects the last poll's jobs/lock state
  const cc = document.getElementById("st-current-card");
  if (cc) { cc.innerHTML = currentRunCard(data.current, aff); wireStopButton(aff); }

  const sv = document.getElementById("st-vram");
  if (sv) sv.innerHTML = `${data.vram_mib != null ? data.vram_mib.toFixed(0) : "–"} <small style="font-size:1rem">MiB</small>`;

  const sj = document.getElementById("st-julia");
  if (sj) sj.textContent = data.julia_procs ?? "–";

  const sd = document.getElementById("st-disk-val");
  if (sd) sd.innerHTML = `${disk.free_gb != null ? disk.free_gb.toFixed(1) : "–"} <small style="font-size:1rem">GB</small>`;

  const ss = document.getElementById("st-disk-sub");
  if (ss) ss.textContent = disk.total_gb != null ? `${disk.total_gb.toFixed(0)} GB total · ${(100 - disk.free_gb / disk.total_gb * 100).toFixed(0)}% used` : "";

  const qt = document.getElementById("queue-tail");
  if (qt) qt.textContent = (ql.tail || []).join("\n");

  const wt = document.getElementById("watchdog-tail");
  if (wt) wt.textContent = wl.join("\n");

  const gc = document.getElementById("btn-gpuclean");
  if (gc) gc.disabled = !!(lock && lock.alive);
  pillFeed(data, jobs);   // the nav pill shares this poll's look (no extra fetch on this view)
}

// ── View 2: Campaigns list ─────────────────────────────────────────

async function viewCampaignsList() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let camps;
  try { camps = await api("/api/campaigns"); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }

  if (!camps.length) {
    ROOT.innerHTML = `<div class="stack" style="gap:20px">
      <div><div class="eyebrow">All campaigns</div><h2>Campaigns</h2></div>
      <p class="muted">No campaigns found. <a href="#/launch">Launch a campaign →</a></p>
    </div>`;
    return;
  }

  let rows = camps.map(c => `<tr class="clickable ${c.superseded ? "superseded" : ""}" onclick="location.hash='#/campaign/${esc(c.id)}'">
    <td><b>${esc(c.id)}</b>${c.superseded ? ` ${pill("superseded", "warn")}` : ""}</td>
    <td>${pill(c.tier || "–", c.tier === "compare" ? "warn" : c.tier === "screen" ? "info" : "good")}</td>
    <td>${esc(c.brief || "–")}</td>
    <td class="r">${esc(c.n_entries)}</td>
    <td class="r">${esc((c.seeds || []).join(", "))}</td>
    <td class="muted" style="font-size:0.82rem">${esc((c.families || []).slice(0, 4).join(", ")) + (c.families && c.families.length > 4 ? " …" : "")}</td>
  </tr>`).join("");

  ROOT.innerHTML = `
    <div class="stack" style="gap:20px">
      <div>
        <div class="eyebrow">All campaigns</div>
        <h2>Campaigns</h2>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>ID</th><th>Tier</th><th>Brief</th><th class="r">Entries</th><th class="r">Seeds</th><th>Families</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

// ── View 2 detail: Campaign detail ────────────────────────────────

const TIER_DESC = {
  "dry-run": "Meshes each starting design only — no solving. Takes seconds. Checks the geometry is valid.",
  "screen":  "One search per family, budget max(40, 10 × parameters). A coarse first ranking in minutes per family. Enough to pick the top 2–3 families.",
  "compare": "Two repeats, budget max(150, 25 × parameters). The minimum to claim one family beats another. Takes hours — never run during a live search.",
};

async function viewCampaignDetail(id) {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let camp;
  try { camp = await api("/api/campaign/" + id); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }

  const entries = camp.entries || [];

  // Compute common scale for wall profiles
  let allR = [], allZ = [];
  entries.forEach(e => {
    const p = ((e.best || {}).profile) || {};
    [["h", 1], ["v", -1]].forEach(([k]) => {
      (p[k] || []).forEach(pt => { allR.push(Math.abs(pt[1])); allZ.push(pt[0]); });
    });
  });
  const sharedRmax = allR.length ? Math.max(...allR) * 1.1 : 200;
  const sharedZmin = allZ.length ? Math.min(...allZ) - 5 : 0;
  const sharedZmax = allZ.length ? Math.max(...allZ) + 5 : 220;

  // Separation analysis
  function isSeparated(a, b) {
    if (a.median_j == null || b.median_j == null) return null;
    const diff = b.median_j - a.median_j;
    const thresh = Math.max(a.spread || 0, b.spread || 0);
    return diff > thresh;
  }

  // Leaderboard rows
  let lbRows = entries.map((e, i) => {
    const gc = groupColor(e.group || "");
    const gpill = `<span class="pill" style="border-color:${gc};box-shadow:inset 3px 0 0 ${gc}">${esc(e.group || "–")}</span>`;
    const pinnedPills = (e.pinned || []).map(k => `<span class="pill bad">${esc(k)}</span>`).join(" ") || "";
    const failCount = Object.values(e.failures || {}).reduce((a, v) => a + v, 0);
    const seedLinks = (e.jobs || []).map(j => j.run_id
      ? `<a href="#/run/${esc(j.run_id)}">${esc("s" + j.seed)}</a>` : `s${esc(j.seed)}`).join(" ");

    // Use best_run_id if available (new API field)
    const bestLink = e.best_run_id
      ? `onclick="location.hash='#/run/${esc(e.best_run_id)}'" style="cursor:pointer"`
      : "";
    const dimCell = e.dims ? dimStr(e.dims) : "–";

    // Separation from next: row tint stays, plus a text badge (state not by colour alone)
    let rowCls = "", rankNote = "";
    if (i < entries.length - 1) {
      const next = entries[i + 1];
      const sep = isSeparated(e, next);
      if (sep === true) {
        rowCls = "row-ahead";
        const pctDelta = e.median_j ? ((next.median_j - e.median_j) / e.median_j) * 100 : null;
        rankNote = (pctDelta != null && isFinite(pctDelta) && pctDelta > 0)
          ? `+${Math.round(pctDelta)} %` : "leader";
      } else if (sep === false) {
        rowCls = "row-not-sep";
        rankNote = "within noise";
      }
    }

    return `<tr class="${rowCls}" ${bestLink}>
      <td class="r mono">${i + 1}${rankNote ? ` <small class="muted">${esc(rankNote)}</small>` : ""}</td>
      <td><b>${esc(e.name)}</b></td>
      <td>${gpill}</td>
      <td class="r">${fmt(e.best_j)}</td>
      <td class="r">${fmt(e.median_j)}</td>
      <td class="r">${fmt(e.spread)}</td>
      <td class="muted" style="font-size:0.8rem;white-space:normal">${esc(dimCell)}</td>
      <td class="r">${esc(e.evals || "–")}</td>
      <td class="r">${failCount > 0 ? `<span class="warn-text">${failCount}</span>` : "0"}</td>
      <td>${pinnedPills}</td>
      <td style="font-size:0.8rem">${seedLinks}</td>
    </tr>`;
  }).join("");

  const tierDesc = TIER_DESC[camp.tier] || "";

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Campaign · ${esc(camp.tier || "")}</div>
        <h2>${esc(camp.id)}</h2>
        <p class="muted" style="font-size:0.85rem">Brief: ${esc(camp.brief || "–")} · Seeds: ${esc((camp.seeds || []).join(", "))}</p>
        ${tierDesc ? `<p class="muted" style="font-size:0.82rem;margin-top:4px">${esc(tierDesc)}</p>` : ""}
        ${camp.superseded ? `<div class="alert warn" style="margin-top:8px"><b>Superseded.</b> This campaign ran before the 22 Oct fixes (native configs were scored on their own targets and the brief's size envelope was not enforced). Kept for the record; it is excluded from Home, Typologies and rankings.</div>` : ""}
      </div>
      <div>
        <p class="muted" style="font-size:0.78rem;margin-bottom:8px">
          <span style="display:inline-flex;align-items:center;gap:5px"><span style="width:10px;height:10px;background:var(--good);border-radius:50%;display:inline-block"></span> Green left border = clearly ahead of next rank</span> ·
          <span style="display:inline-flex;align-items:center;gap:5px"><span style="width:10px;height:10px;background:var(--warn);border-radius:50%;display:inline-block"></span> Orange = not separated from next</span>
        </p>
        <div class="tbl-wrap">
          <table>
            <thead><tr>
              <th class="r">#</th><th>Name</th><th>Group</th>
              <th class="r">${tip("J", "Best score")}</th>
              <th class="r">${tip("median", "Median")}</th>
              <th class="r">${tip("spread", "Spread")}</th>
              <th>${tip("dims", "Horn size W×H×D")}</th>
              <th class="r">Evals</th>
              <th class="r">${tip("failures", "Failures")}</th>
              <th>${tip("pinned", "At limit")}</th>
              <th>Seeds</th>
            </tr></thead>
            <tbody>${lbRows}</tbody>
          </table>
        </div>
      </div>
      <div>
        <h3 style="margin-bottom:10px">Wall profiles — best design per family</h3>
        <p class="muted" style="font-size:0.82rem">H right (positive r), V mirrored left. Shared mm scale. Click a card to open the run.</p>
        <div class="camp-grid" id="wall-profiles"></div>
      </div>
      <div>
        <h3 style="margin-bottom:8px">Best design of each family</h3>
        <div class="legend" id="bw-legend" style="margin-bottom:8px"></div>
        <div class="grid2">
          <div class="fig">
            <div class="fig-head"><h3>Beamwidth (−6 dB) vs target</h3>
              <div class="toggle-row" id="bw-toggle">
                <button aria-pressed="true" id="btn-bw-h">Horizontal</button>
                <button aria-pressed="false" id="btn-bw-v">Vertical</button>
              </div></div>
            <div class="cap">Shaded: target ±10 %. Lighter panel: scored band.</div>
            <svg id="bw-chart"></svg>
          </div>
          <div class="fig">
            <h3>Directivity index vs target</h3>
            <div class="cap">Dashed: target DI from the brief's coverage angles.</div>
            <svg id="di-overlay"></svg>
          </div>
        </div>
      </div>
    </div>`;

  // Wall cross-sections, one card per family, all on ONE shared mm scale so sizes compare directly
  const profGrid = document.getElementById("wall-profiles");
  let ext = { rmax: 1, z0: Infinity, z1: -Infinity };
  entries.forEach(e => { const p = (e.best || {}).profile || {};
    for (const k of ["h", "v"]) for (const [z, r] of (p[k] || [])) {
      ext.rmax = Math.max(ext.rmax, Math.abs(r)); ext.z0 = Math.min(ext.z0, z); ext.z1 = Math.max(ext.z1, z); } });
  entries.forEach((e, idx) => {
    const cell = document.createElement("div"); cell.className = "camp-prof";
    if (e.best_run_id) { cell.onclick = () => { location.hash = "#/run/" + e.best_run_id; }; cell.tabIndex = 0; cell.setAttribute("role", "link"); }
    const col = familyColor(idx);
    cell.innerHTML = `<h4><span class="swatch" style="background:${col}"></span>${esc(e.name)}</h4>`;
    const sv = document.createElementNS(NS, "svg"); sv.setAttribute("class", "camp-sec");
    cell.appendChild(sv);
    const cap = document.createElement("div"); cap.className = "camp-dims";
    cap.textContent = e.dims ? `${Math.round(e.dims.mouth_w_mm)} × ${Math.round(e.dims.mouth_h_mm)} × ${Math.round(e.dims.depth_mm)} mm` : "no solved design";
    cell.appendChild(cap);
    profGrid.appendChild(cell);
    requestAnimationFrame(() => wallSection(sv, (e.best && e.best.profile) ? [{ profile: e.best.profile, color: col, filled: true }] : [],
                                            { H: 130, compact: true, extent: isFinite(ext.z0) ? ext : null }));
  });

  // Overlays of each family's best design: beamwidth (H or V) and DI, one colour per family
  const target = camp.target || (entries.find(e => e.best && e.best.target) || {}).target || {};
  let bwPlane = "h";
  function drawBW() {
    const bwSvg = document.getElementById("bw-chart"), diSvg = document.getElementById("di-overlay");
    const legDiv = document.getElementById("bw-legend");
    if (!bwSvg) return;
    const freqsRef = (entries.find(e => e.best && e.best.freqs) || { best: { freqs: [] } }).best.freqs || [];
    if (!freqsRef.length) { bwSvg.innerHTML = "<text x='10' y='20'>No frequency data</text>"; return; }
    const tgtH = target.coverage_h_deg, tgtV = target.coverage_v_deg;
    const tgt = bwPlane === "h" ? tgtH : tgtV;
    const allBW = [];
    entries.forEach(e => { const b = e.best || {}; (bwPlane === "h" ? (b.bw_h || []) : (b.bw_v || [])).forEach(v => v != null && allBW.push(v)); });
    if (tgt) allBW.push(tgt);
    const bwmax = Math.min(200, Math.ceil(Math.max(...allBW) * 1.08 / 10) * 10) || 180;
    const band = [target.band_lo_hz || freqsRef[0], target.band_hi_hz || freqsRef[freqsRef.length - 1]];
    const xlim = [freqsRef[0], freqsRef[freqsRef.length - 1]];
    chart(bwSvg, {
      H: 260, xlog: true, xlim, ylim: [0, bwmax], xticks: FT, yticks: niceTicks(0, bwmax, 5),
      xlabel: "Hz", ylabel: "deg", band,
      fill: tgt ? [{ y0: tgt * 0.9, y1: tgt * 1.1, color: css("--best"), opacity: 0.10 }] : [],
      hlines: tgt ? [{ y: tgt, color: css("--label"), dash: true }] : [],
      series: entries.map((e, idx) => { const b = e.best || {}, F2 = b.freqs || freqsRef;
        const arr = bwPlane === "h" ? (b.bw_h || []) : (b.bw_v || []);
        return { pts: F2.map((f, i) => [f, arr[i] ?? null]), color: familyColor(idx), w: idx === 0 ? 2.4 : 1.6 }; }),
    });
    if (diSvg) {
      const dit = target.di_target_db ?? (tgtH && tgtV ? diFromCuts(tgtH, tgtV) : null);
      const dall = []; entries.forEach(e => ((e.best || {}).di || []).forEach(v => v != null && dall.push(v)));
      if (dit != null) dall.push(dit);
      const dlo = Math.floor(Math.min(...dall) - 1), dhi = Math.ceil(Math.max(...dall) + 1);
      chart(diSvg, {
        H: 260, xlog: true, xlim, ylim: [dlo, dhi], xticks: FT, yticks: niceTicks(dlo, dhi, 5),
        xlabel: "Hz", ylabel: "dB", band,
        hlines: dit != null ? [{ y: dit, color: css("--label"), dash: true }] : [],
        series: entries.map((e, idx) => { const b = e.best || {}, F2 = b.freqs || freqsRef;
          return { pts: F2.map((f, i) => [f, (b.di || [])[i] ?? null]), color: familyColor(idx), w: idx === 0 ? 2.4 : 1.6 }; }),
      });
    }
    legDiv.innerHTML = entries.map((e, idx) => `<span><i style="color:${familyColor(idx)};border-top-color:${familyColor(idx)}"></i>${esc(e.name)}${idx === 0 ? " (rank 1)" : ""}</span>`).join("")
      + `<span><i style="color:var(--label)" class="dash"></i>target</span>`;
  }
  drawBW();
  document.getElementById("btn-bw-h").onclick = () => {
    bwPlane = "h";
    document.getElementById("btn-bw-h").setAttribute("aria-pressed", "true");
    document.getElementById("btn-bw-v").setAttribute("aria-pressed", "false");
    drawBW();
  };
  document.getElementById("btn-bw-v").onclick = () => {
    bwPlane = "v";
    document.getElementById("btn-bw-h").setAttribute("aria-pressed", "false");
    document.getElementById("btn-bw-v").setAttribute("aria-pressed", "true");
    drawBW();
  };
}

// ── View 3: Runs list ──────────────────────────────────────────────

async function viewRunsList() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let runs;
  try { runs = await api("/api/runs"); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }
  if (ROOT !== currentRoot()) return;   // the user navigated away while this loaded
  renderRunsList(runs);
}

function renderRunsList(allRuns) {
  // Collect unique briefs and families for filter dropdowns
  const briefs = [...new Set(allRuns.map(r => r.brief).filter(Boolean))].sort();
  const families = [...new Set(allRuns.map(r => r.family).filter(Boolean))].sort();

  ROOT.innerHTML = `
    <div class="stack" style="gap:20px">
      <div>
        <div class="eyebrow">All runs</div>
        <h2>Runs</h2>
        <p class="muted" style="font-size:0.85rem">${allRuns.length} total · newest first</p>
      </div>
      <div class="filter-bar">
        <input id="run-filter" type="search" placeholder="Filter by name / family / brief…" aria-label="filter runs">
        <select id="run-filter-brief" aria-label="filter by brief">
          <option value="">All briefs</option>
          ${briefs.map(b => `<option value="${esc(b)}">${esc(b)}</option>`).join("")}
        </select>
        <select id="run-filter-family" aria-label="filter by family">
          <option value="">All families</option>
          ${families.map(f => `<option value="${esc(f)}">${esc(f)}</option>`).join("")}
        </select>
        <select id="run-sort" class="sort-sel" aria-label="sort runs">
          <option value="date">Newest first</option>
          <option value="best_j">${tip("J", "Score")} (best first)</option>
          <option value="name">Name</option>
        </select>
      </div>
      <div class="tbl-wrap">
        <table id="runs-table">
          <thead><tr>
            <th>Date</th><th>Name</th><th>Family</th><th>Brief</th>
            <th class="r">${tip("J", "Score start → best")}</th>
            <th class="r">Change</th>
            <th>${tip("dims", "Horn size W×H×D")}</th>
            <th class="r">Evals</th>
            <th class="r">${tip("failures", "Fail %")}</th>
          </tr></thead>
          <tbody id="runs-tbody"></tbody>
        </table>
      </div>
    </div>`;

  function render() {
    const q = document.getElementById("run-filter").value.toLowerCase();
    const bf = document.getElementById("run-filter-brief").value;
    const ff = document.getElementById("run-filter-family").value;
    const sort = document.getElementById("run-sort").value;
    let filtered = allRuns.filter(r =>
      (!bf || r.brief === bf) &&
      (!ff || r.family === ff) &&
      (!q || (r.name || "").toLowerCase().includes(q) ||
             (r.family || "").toLowerCase().includes(q) ||
             (r.brief || "").toLowerCase().includes(q))
    );
    if (sort === "best_j") filtered.sort((a, b) => (a.best_j ?? 999) - (b.best_j ?? 999));
    else if (sort === "name") filtered.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    else filtered.sort((a, b) => (b.started || "").localeCompare(a.started || ""));

    const tbody = document.getElementById("runs-tbody");
    if (!filtered.length) {
      tbody.innerHTML = `<tr><td colspan="9" class="muted" style="text-align:center;padding:24px">No matching runs. <a href="#/launch">Launch a search →</a></td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(r => {
      const nf = r.n - r.n_ok;
      const ch = betterPct(r.seed_j, r.best_j);
      const chCls = ch.endsWith("better") ? "good-text" : "";
      const failPct = r.n > 0 ? ((nf / r.n) * 100).toFixed(0) + "%" : "–";
      const isRunning = !r.last || (Date.now() - new Date(r.last).getTime()) < 120000;
      return `<tr class="clickable" onclick="location.hash='#/run/${esc(r.id)}'" ${isRunning ? 'style="background:var(--accent-soft)"' : ""}>
        <td class="muted mono" style="font-size:0.76rem;white-space:nowrap">${timeSince(r.started)}</td>
        <td><b>${esc(r.name)}</b><br><span class="mono muted" style="font-size:0.72rem">${esc(r.id)}</span></td>
        <td>${esc(r.family || "–")}</td>
        <td>${esc(r.brief || "–")}</td>
        <td class="r num">${r.seed_j != null && r.seed_j < 900 ? fmt(r.seed_j) : "–"} → <b>${fmt(r.best_j)}</b></td>
        <td class="r ${chCls}">${ch}</td>
        <td style="font-size:0.82rem">${r.dims ? esc(dimStr(r.dims)) : "–"}</td>
        <td class="r">${r.n.toLocaleString()}</td>
        <td class="r">${nf > 0 ? `<span class="warn-text">${esc(failPct)}</span>` : failPct}</td>
      </tr>`;
    }).join("");
  }

  render();
  document.getElementById("run-filter").addEventListener("input", render);
  document.getElementById("run-filter-brief").addEventListener("change", render);
  document.getElementById("run-filter-family").addEventListener("change", render);
  document.getElementById("run-sort").addEventListener("change", render);
}

// ── View 3 detail: Run detail ──────────────────────────────────────

// -- WP11b: CMA-ME quality-diversity atlas (read-only, plain canvas) -----------
// Data: GET /api/archive/<run> (data.py::run_archive) over the pinned archive_heatmap.json:
//   {bins: [bins_h, bins_v], ranges: {h: [lo, hi], v: [lo, hi]},
//    cells: [{h_center, v_center, objective, design_hash}],
//    descriptors: {h: name, v: name}}   (occupied bins only; descriptors may be absent)
// A plain cma run has no such file: the endpoint reports available:false and this view says so.
async function viewRunArchive(id) {
  const ROOT = currentRoot();     // this view's own container (see route())
  ROOT.innerHTML = `<p class="muted">Loading the quality-diversity atlas…</p>`;
  let A;
  try { A = await api("/api/archive/" + encodeURIComponent(id)); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }
  if (!A.available) {
    ROOT.innerHTML = `<div class="stack" style="gap:12px">
      <div class="eyebrow">Quality-diversity atlas</div><h2>${esc(id)}</h2>
      <p class="muted">This run has no atlas. Only a CMA-ME search (<code>search.algorithm: cma_me</code>)
        writes <code>archive_heatmap.json</code>; a plain cma run never does.</p>
      <p><a href="#/run/${esc(id)}">← back to the run</a></p></div>`;
    return;
  }
  const bins = A.bins || [1, 1], rng = A.ranges || {};
  const nbH = Math.max(1, Math.trunc(bins[0]) || 1), nbV = Math.max(1, Math.trunc(bins[1]) || 1);
  const axH = Array.isArray(rng.h) ? rng.h.map(Number) : [0, 180];
  const axV = Array.isArray(rng.v) ? rng.v.map(Number) : [0, 180];
  const cells = (A.cells || []).filter(c => c && isFinite(c.h_center) && isFinite(c.v_center)
                                            && isFinite(c.objective));
  if (!cells.length) {
    ROOT.innerHTML = `<div class="stack" style="gap:12px">
      <div class="eyebrow">Quality-diversity atlas</div><h2>${esc(id)}</h2>
      <p class="muted">The archive has no occupied bins yet.</p>
      <p><a href="#/run/${esc(id)}">← back to the run</a></p></div>`;
    return;
  }
  const totalBins = nbH * nbV, coverage = totalBins ? cells.length / totalBins : 0;
  const evals = A.stats && A.stats.total_evals != null ? A.stats.total_evals : null;
  // G2 (plan §3.1): the atlas header surfaces the run's run.json.qd provenance (algorithm,
  // descriptor meanings, coverage, non-cached evals) from the C-1 run payload. An absent qd
  // block (older CMA-ME runs) keeps the header exactly as committed — and the canvas code below
  // is untouched by this addition.
  let QD = null;
  try { QD = (await api("/api/run/" + encodeURIComponent(id))).qd || null; } catch { QD = null; }
  const jmin = Math.min(...cells.map(c => c.objective)), jmax = Math.max(...cells.map(c => c.objective));
  const labH = (A.descriptors && A.descriptors.h) || "descriptor (h)";
  const labV = (A.descriptors && A.descriptors.v) || "descriptor (v)";
  ROOT.innerHTML = `<div class="stack" style="gap:16px">
    <div><div class="eyebrow">Quality-diversity atlas · CMA-ME</div><h2>${esc(id)}</h2>
      <p class="muted" style="margin:2px 0 0">${cells.length} of ${totalBins} bins occupied
        (${fmtPct(coverage * 100)}${evals != null ? ", " + esc(evals) + " evaluations" : ""}).
        Axes: <code>${esc(labH)}</code> (horizontal) × <code>${esc(labV)}</code> (vertical), degrees.
        Hollow cells never held an evaluated design.
        <a href="#/run/${esc(id)}">← back to the run</a></p>
      ${qdProvenanceCaption(QD)}</div>
    <div class="fig"><h3>Archive: best objective per descriptor bin</h3>
      <div class="cap">Colour: objective J (lower is better, brightest). Hover a cell for its descriptor
        centre, objective and design hash.</div>
      <canvas id="qd-canvas" width="720" height="540" style="max-width:100%"></canvas>
      <div class="legend" style="align-items:center">
        <span class="mono">worst J ${fmt(jmax, 3)}</span>
        <canvas id="qd-cbar" style="width:180px;height:10px;border:1px solid var(--rule)"></canvas>
        <span class="mono">best J ${fmt(jmin, 3)}</span>
      </div>
      <div id="qd-hover" class="mono muted" style="min-height:1.2em"></div></div>
  </div>`;
  drawCbar(document.getElementById("qd-cbar"));
  const cv = document.getElementById("qd-canvas"), g = cv.getContext("2d");
  const padL = 78, padB = 58, padT = 16, padR = 20;
  const W = cv.width - padL - padR, H = cv.height - padT - padB;
  const cw = W / nbH, ch = H / nbV;
  // descriptor value -> bin index, clamped: a cell centre at the top edge lands in the last bin
  const binOf = (v, ax, n) => {
    if (!(ax[1] > ax[0])) return 0;
    return Math.max(0, Math.min(n - 1, Math.floor((v - ax[0]) / (ax[1] - ax[0]) * n)));
  };
  const byBin = new Map();
  for (const c of cells) {
    const key = binOf(c.h_center, axH, nbH) + "," + binOf(c.v_center, axV, nbV);
    const old = byBin.get(key);                       // one elite per bin by contract; keep the best anyway
    if (!old || c.objective < old.objective) byBin.set(key, c);
  }
  g.fillStyle = css("--surface") || "#15181c"; g.fillRect(padL, padT, W, H);
  g.strokeStyle = css("--rule") || "#333"; g.lineWidth = 1;
  for (let i = 0; i <= nbH; i++) {
    const x = padL + i * cw; g.beginPath(); g.moveTo(x, padT); g.lineTo(x, padT + H); g.stroke();
  }
  for (let j = 0; j <= nbV; j++) {
    const y = padT + j * ch; g.beginPath(); g.moveTo(padL, y); g.lineTo(padL + W, y); g.stroke();
  }
  for (const [key, c] of byBin) {
    const [i, j] = key.split(",").map(Number);
    const t = jmax > jmin ? (c.objective - jmin) / (jmax - jmin) : 0.5;
    const [rr, gg, bb] = cmap(1 - t);                 // t = 0 (best objective) -> bright/warm end
    g.fillStyle = `rgb(${rr},${gg},${bb})`;
    g.fillRect(padL + i * cw + 1, padT + H - (j + 1) * ch + 1, cw - 2, ch - 2);
  }
  g.fillStyle = css("--label") || "#aaa"; g.font = "11px monospace";
  g.textAlign = "center"; g.textBaseline = "top";
  const stepH = Math.max(1, Math.round(nbH / 6)), stepV = Math.max(1, Math.round(nbV / 5));
  for (let i = 0; i < nbH; i += stepH) {
    const c = axH[0] + (i + 0.5) * (axH[1] - axH[0]) / nbH;
    g.fillText(fmtDeg(c), padL + (i + 0.5) * cw, padT + H + 6);
  }
  g.textAlign = "right"; g.textBaseline = "middle";
  for (let j = 0; j < nbV; j += stepV) {
    const c = axV[0] + (j + 0.5) * (axV[1] - axV[0]) / nbV;
    g.fillText(fmtDeg(c), padL - 6, padT + H - (j + 0.5) * ch);
  }
  g.textAlign = "center"; g.textBaseline = "alphabetic";
  g.fillText(labH, padL + W / 2, cv.height - 10);
  g.save(); g.translate(14, padT + H / 2); g.rotate(-Math.PI / 2);
  g.fillText(labV, 0, 0); g.restore();
  const hover = document.getElementById("qd-hover");
  cv.onmousemove = ev => {
    const b = cv.getBoundingClientRect();
    const x = (ev.clientX - b.left) * cv.width / b.width - padL;
    const y = padT + H - (ev.clientY - b.top) * cv.height / b.height;
    const i = Math.floor(x / cw), j = Math.floor(y / ch);
    if (i < 0 || j < 0 || i >= nbH || j >= nbV) { hover.textContent = ""; return; }
    const c = byBin.get(i + "," + j);
    hover.textContent = c
      ? `bin [${i}, ${j}] · ${labH} ${fmtDeg(c.h_center)} · ${labV} ${fmtDeg(c.v_center)} · J ${fmt(c.objective, 4)} · design ${String(c.design_hash || "").slice(0, 12)}`
      : `bin [${i}, ${j}] · empty`;
  };
  cv.onmouseleave = () => { hover.textContent = ""; };
}

// ── Provenance strips · GUI plan phases G1–G4 (contracts C-1/C-2, badge matrix §7) ──────
// Honesty rules: a badge renders ONLY when its source key exists in the payload (identity keys
// backend + freqs_hz are always present and show the baseline group, exactly like /api/compare;
// every other key renders only when the run is non-default — never an empty shell, never a
// default claim); every number is traceable through the badge's title tooltip, which names the
// exact key path the value was read from (solve_group.* / run.json.restarts /
// run_detail.search_restarts.*). These helpers are pure (no DOM) and exported for offline node
// tests (tests/test_gui_brief_authoring.py), mirroring the view3d.js::mirrorMesh precedent.

function _trimNum(v) {                      // 3000 -> "3", 2500 -> "2.5", 2.0 -> "2", 0.25 -> "0.25"
  const n = Number(v);
  if (!isFinite(n)) return String(v);
  return Number.isInteger(n) ? String(n) : String(+n.toFixed(2));
}

function _jsonish(v) {                      // tooltip value: scalar as text, objects/arrays as JSON
  if (v == null || typeof v !== "object") return String(v);
  try { return JSON.stringify(v); } catch { return String(v); }
}

/** One provenance badge row (pure). `group` holds only non-default provenance keys, in the C-2
 *  fingerprint vocabulary of data.py::_solve_group_fingerprint, so the run-detail extractor and
 *  the compare view's server groups share this builder. `prefix`/`tips` name the source paths in
 *  the tooltips ("group_a." for compare sides; explicit paths for run detail). */
function renderProvenanceBadges(group, prefix = "", tips = {}) {
  const g = (group && typeof group === "object") ? group : {};
  const src = (tips && typeof tips === "object") ? tips : {};
  const out = [];
  const bad = (key, text) => out.push(
    `<span class="pill" title="${esc(prefix + (src[key] || key) + " = " + _jsonish(g[key]))}">${esc(text)}</span>`);
  // Order follows the plan §7 badge matrix, with the C-2 identity keys (backend, freqs_hz) at the
  // front: the compare sides always carry both, so their badge row shows the baseline group.
  if (g.backend) bad("backend", String(g.backend));
  if (g.freqs_hz && typeof g.freqs_hz === "object") {
    const idt = g.freqs_hz, parts = [];
    if (idt.mode) parts.push(String(idt.mode));
    if (idt.band_lo_hz != null && idt.band_hi_hz != null) parts.push(`${_trimNum(idt.band_lo_hz)}–${_trimNum(idt.band_hi_hz)} Hz`);
    if (idt.verify_points_per_octave != null) parts.push(`${idt.verify_points_per_octave}/oct verify`);
    if (parts.length) bad("freqs_hz", `grid ${parts.join(" ")}`);
  }
  if (g.cuda_fused === true) bad("cuda_fused", "fused CUDA");
  if (g.near_correction && g.solve_precision != null) bad("near_correction", `near-corrected · ${g.solve_precision}`);
  else if (g.near_correction) bad("near_correction", "near-corrected");
  else if (g.solve_precision != null) bad("solve_precision", `${g.solve_precision} precision`);
  if (g.source_profile_alpha != null && Number(g.source_profile_alpha) !== 0) {
    bad("source_profile_alpha", `source plug α=${_trimNum(g.source_profile_alpha)}${g.source_profile ? ` (${g.source_profile})` : ""}`);
  }
  if (g.source_motion && g.source_motion !== "normal") bad("source_motion", `source motion ${g.source_motion}`);
  if (g.mesh_policy) {
    const e = Array.isArray(g.band_edges_hz) ? g.band_edges_hz : [];
    const tail = e.length
      ? (e.every(x => Number(x) >= 1000)
          ? e.map(x => _trimNum(Number(x) / 1000)).join("/") + " k"
          : e.map(x => fmtHz(Number(x))).join("/"))
      : "";
    bad("mesh_policy", tail ? `band-split ${tail}` : String(g.mesh_policy));
  }
  if (g.rear_res_factor != null && Number(g.rear_res_factor) !== 1) bad("rear_res_factor", `rear ×${_trimNum(g.rear_res_factor)}`);
  if (g.mounting) {
    const mnt = (typeof g.mounting === "object" && g.mounting) || { type: String(g.mounting) };
    if (mnt.type) bad("mounting", `${mnt.type}${mnt.depth_mm != null ? ` d=${_trimNum(mnt.depth_mm)} mm` : ""}`);
  }
  if (g.cad_route === true) bad("cad_route", "cad STEP");   // geometry source: the mesh came from a CAD STEP body
  if (g.objective_version != null && Number(g.objective_version) !== 1) bad("objective_version", `J v${_trimNum(g.objective_version)}`);
  if (g.qd_algorithm) bad("qd_algorithm", g.qd_algorithm === "cma_me" ? "CMA-ME" : String(g.qd_algorithm));
  if (g.restarts_count != null && Number(g.restarts_count) > 0) {
    const mode = typeof g.restarts_mode === "string" ? g.restarts_mode.toUpperCase() : "";
    bad("restarts_count", `${mode || "restarts"} ×${_trimNum(g.restarts_count)}`);
  }
  return out.join(" ");
}

/** The provenance group of one /api/run/<id> payload (pure): read straight from the reader's
 *  `solve_group` (data.py::run_detail) — the same fingerprint /api/compare exposes as
 *  group_a/group_b — so run detail and the compare view share one badge vocabulary and one set
 *  of tooltip paths. The restart count rides the C-1 restarts array; restart mode/max ride the
 *  reader's `search_restarts` (absent when config.yaml carries no valid search.restarts — then
 *  the badge never claims a mode). Returns {group, tips}; tips[key] names the exact key path. */
function runProvenanceGroup(d) {
  const g = {}, tips = {};
  const sg = (d && typeof d.solve_group === "object" && d.solve_group) || null;
  if (sg) for (const k of Object.keys(sg)) { g[k] = sg[k]; tips[k] = "solve_group." + k; }
  if (Array.isArray(d && d.restarts) && d.restarts.length) {
    g.restarts_count = d.restarts.length; tips.restarts_count = "run.json.restarts";
    const sr = (d && typeof d.search_restarts === "object" && d.search_restarts) || null;
    if (sr && sr.mode) {
      g.restarts_mode = sr.mode; tips.restarts_mode = "run_detail.search_restarts.mode";
      if (sr.max != null) { g.restarts_max = sr.max; tips.restarts_max = "run_detail.search_restarts.max"; }
    }
  }
  return { group: g, tips };
}

/** The restart schedule card (G2, plan §3.2): one text-pill row per entry of the C-1 `restarts`
 *  array (as-is), the honest empty state when only older pycma logs exist, and nothing at all for
 *  a non-restart run (absence stays honest). Pure; returns HTML. */
function restartScheduleHtml(d, id) {
  const runs = Array.isArray(d && d.restarts) ? d.restarts : [];
  const dirs = Array.isArray(d && d.restart_dirs) ? d.restart_dirs.filter(x => typeof x === "string" && x) : [];
  if (!runs.length && !dirs.length) return "";   // absence = not a restart run — render nothing
  const runId = String(id || (d && d.summary && d.summary.id) || "");
  // pycma logs: when the reader lands its cma_files listing (contract [{path, name, size}], sorted,
  // [] when none) the caption becomes clickable chips on the LIVE C-5 raw log route — every name is
  // a listed file, none invented. Listing absent (reader not landed) => the URL-shape caption with
  // its parenthetical; listing present but empty => the honest "no files there" caption, no note.
  const hasCmaListing = !!(d && Array.isArray(d.cma_files));
  const cmaFiles = hasCmaListing
    ? d.cma_files.filter(f => f && typeof f === "object" && typeof f.path === "string" && f.path) : [];
  const logChips = cmaFiles.map(f =>
    `<a class="pill" href="/runs/${esc(runId)}/${esc(f.path)}" download` +
    ` title="pycma log · ${esc(f.path)}${f.size != null ? " · " + esc(f.size) + " bytes" : ""}">↓ ${esc(f.name || f.path.split("/").pop())}</a>`)
    .join(" ");
  const logs = logChips
    ? `<div class="hint" style="margin:6px 0 0">pycma logs (raw, never parsed; each file serves by its exact name): ` +
      `<span class="pill-row" style="display:inline-flex;vertical-align:middle">${logChips}</span></div>`
    : (dirs.length
      ? `<p class="hint" style="margin:6px 0 0">pycma logs: ${dirs.map(x => `<code>${esc(x)}</code>`).join(", ")} — raw, never parsed. Each file downloads at <code>/runs/${esc(runId)}/cma/restart_k/&lt;file&gt;</code>${hasCmaListing ? "" : " (raw log route; the API lists the directories, not the file names)"}</p>`
      : "");
  if (!runs.length) {
    // pycma logs listed but this run.json predates the restarts block: the honest empty state
    return `<div class="fig restart-schedule-card"><h3>Restart schedule</h3>
      <p class="muted" style="font-size:0.85rem;margin:6px 0 0">pycma logs available, run.json predates the restarts block — nothing to schedule.</p>${logs}</div>`;
  }
  const sr = (d && typeof d.search_restarts === "object" && d.search_restarts) || null;
  const head = sr && sr.mode
    ? `<div class="cap">mode ${esc(sr.mode)} · max ${esc(sr.max ?? "–")} — run_detail.search_restarts (the run's config search.restarts)</div>`
    : `<div class="cap">restart rows read <code>run.json.restarts</code> as-is — the run's config carries no valid <code>search.restarts</code> block</div>`;
  const rows = runs.map((r, i) => {
    const rr = (r && typeof r === "object") ? r : {};
    const k = rr.index != null ? rr.index : i;
    const pillHtml = (key, txt) => txt == null ? ""
      : `<span class="pill" title="run.json.restarts[${esc(k)}].${esc(key)} = ${esc(_jsonish(rr[key]))}">${esc(txt)}</span>`;
    return `<div class="pill-row" style="margin:4px 0">` +
      pillHtml("index", `restart ${k}`) +
      pillHtml("popsize", rr.popsize != null ? `popsize ${rr.popsize}` : null) +
      pillHtml("sigma0", rr.sigma0 != null ? `σ0 ${rr.sigma0}` : null) +
      pillHtml("evals_in_restart", rr.evals_in_restart != null ? `evals ${rr.evals_in_restart}` : null) +
      pillHtml("stop", rr.stop != null ? `stop ${rr.stop}` : null) +
      `</div>`;
  }).join("");
  return `<div class="fig restart-schedule-card"><h3>Restart schedule</h3>${head}${rows}${logs}</div>`;
}

/** The C-1/step-detail lookup (pure): `step_files_detail` entries ({name, inventory|null} — the
 *  parsed step/<name>.inventory.json sidecar next to the UNCHANGED step_files name list) matched
 *  by name. Unmatched entries are ignored (no fabricated chips); an absent list means no chip
 *  carries sidecar data. */
function stepInvByName(detail) {
  const m = new Map();
  for (const e of (Array.isArray(detail) ? detail : [])) {
    if (e && typeof e === "object" && typeof e.name === "string" && e.name) {
      m.set(e.name, (e.inventory && typeof e.inventory === "object" && e.inventory !== null) ? e.inventory : null);
    }
  }
  return m;
}

/** One STEP chip in the run-detail files row (G4's chip half). `name` comes from the unchanged
 *  C-1 `step_files` list; `inv` is the matched `step_files_detail` inventory (null when the
 *  sidecar is absent). With a sidecar the chip renders ONLY the facts it carries — the WP14
 *  exporter's tool/tool_sha/grid fields or the CAD contract's faces/solids/closed/tool_sha256/
 *  tool_path (chip summary e.g. "driver=1 · wall=9 · solid ✓ · tool <sha8>") — a segment absent
 *  from the sidecar renders nothing, nothing is invented; the tooltip names every present key
 *  with its value. Without a sidecar the chip is unchanged (silent absence). Pure; returns HTML. */
function stepChipHtml(name, inv, id) {
  name = typeof name === "string" ? name : String((name && name.name) || "");
  if (!name) return "";
  const href = `/runs/${esc(id)}/step/${encodeURIComponent(name)}`;
  const rank = name.replace(/^.*_(rank\d+)_.*$/, "$1");
  inv = (inv && typeof inv === "object" && inv !== null) ? inv : null;
  if (!inv) return `<a class="pill" href="${href}" download>↓ ${esc(rank)}</a>`;
  const bits = [];                                       // chip face segments (rendered joined " · ")
  if (Array.isArray(inv.grid) && inv.grid.length)
    bits.push(inv.grid.map(x => String(x).replace(/x/g, "×")).join(" + ") + " STEP");
  const faces = (Array.isArray(inv.faces) ? inv.faces : []).filter(x => x && typeof x.label === "string");
  if (faces.length)
    bits.push(faces.map(x => `${x.label}=${x.count == null ? "–" : x.count}`).join(" · "));
  if (inv.closed != null)
    bits.push(inv.closed ? "solid ✓" : "solid ✗");
  else if (inv.solids != null)
    bits.push(`solids ${_trimNum(inv.solids)}`);
  const shaKey = inv.tool_sha256 != null ? "tool_sha256" : (inv.tool_sha != null ? "tool_sha" : null);
  const shaRaw = shaKey ? String(inv[shaKey]).trim() : "";
  if (shaRaw) bits.push(`tool ${shaRaw.slice(0, 8)}`);
  if (!bits.length) return `<a class="pill" href="${href}" download>↓ ${esc(rank)}</a>`;
  // tooltip: every present key with its exact value
  const tipBits = [`step/${name}`, `step/${name}.inventory.json`];
  if (inv.tool_path != null) tipBits.push(`tool_path=${_jsonish(inv.tool_path)}`);
  else if (inv.tool != null) tipBits.push(`tool=${_jsonish(inv.tool)}`);
  if (shaRaw) tipBits.push(`${shaKey}=${shaRaw}`);
  if (faces.length) tipBits.push(`faces=${_jsonish(faces)}`);
  if (inv.solids != null) tipBits.push(`solids=${_jsonish(inv.solids)}`);
  if (inv.closed != null) tipBits.push(`closed=${_jsonish(inv.closed)}`);
  if (Array.isArray(inv.grid)) tipBits.push(`grid=${_jsonish(inv.grid)}`);
  return `<a class="pill" href="${href}" download title="${esc(tipBits.join(" · "))}">↓ ${esc(bits.join(" · "))} <span class="muted">(${esc(rank)})</span></a>`;
}

/** The run.json.qd provenance caption for the atlas header (G2, plan §3.1). Renders each key that
 *  exists, descriptor meanings as code tooltips, and nothing when the block is absent/partial.
 *  Pure; returns HTML. */
function qdProvenanceCaption(qd) {
  if (!qd || typeof qd !== "object") return "";
  const parts = [];
  if (qd.algorithm) parts.push(`algorithm <code title="run.json.qd.algorithm">${esc(qd.algorithm)}</code>`);
  const dh = qd.descriptors && qd.descriptors.h, dv = qd.descriptors && qd.descriptors.v;
  if (dh || dv) {
    const one = (name, meaning, path) => name
      ? `<code title="${esc((meaning ? meaning + " — " : "") + path)}">${esc(name)}</code>` : "–";
    parts.push(`descriptors H ${one(dh, qd.descriptor_h_meaning, "run.json.qd.descriptors.h")}` +
               ` · V ${one(dv, qd.descriptor_v_meaning, "run.json.qd.descriptors.v")}`);
  }
  if (qd.occupied_bins != null && qd.total_bins != null) {
    parts.push(`coverage ${esc(qd.occupied_bins)}/${esc(qd.total_bins)} bins`);
  }
  if (qd.total_evals != null) {
    parts.push(`${esc(qd.total_evals)} evaluations${qd.non_cached != null ? ` (${esc(qd.non_cached)} non-cached)` : ""}`);
  }
  if (!parts.length) return "";
  return `<p class="hint" style="margin:4px 0 0" role="note">atlas provenance (run.json.qd): ${parts.join(" · ")}</p>`;
}

/** The f11 caveat sentence (§3.4): any band whose top frequency sits above f11 compares geometry
 *  only there — the driver no longer behaves like a real one. Shown ONLY when BOTH numbers are
 *  known in the run-detail payload (f11 from the best design's metrics scalars; band_hi from the
 *  resolved target). Pure; returns HTML or "". */
function f11CaveatHtml(d) {
  const t = (d && d.target) || {};
  const sc = ((d && d.best && d.best.scalars) || {});
  const f11 = sc.f11_hz != null ? sc.f11_hz : sc.n_hz;      // n_hz = the same J1′-root formula (older scalars)
  if (f11 == null || !isFinite(Number(f11)) ||
      t.band_hi_hz == null || !(Number(t.band_hi_hz) > Number(f11))) return "";
  const f11Path = sc.f11_hz != null ? "best.scalars.f11_hz" : "best.scalars.n_hz";
  return `<p class="muted" style="font-size:0.82rem;margin:6px 0 0" role="note">` +
    `<span class="warn-text">8–12 kHz compares GEOMETRIES, not drivers (above f11 the source is an idealized rigid cap)</span> ` +
    `<span class="muted">(f11 = ${esc(fmtHz(f11))}, band_hi = ${esc(fmtHz(t.band_hi_hz))} — ${f11Path} vs target.band_hi_hz)</span></p>`;
}

/** The scoring-floor KPI (objective v3): rendered ONLY when target.f0_hz is present — v3's cov and
 *  dislope terms score only f >= f0, everything below is masked. Nothing is rendered when the
 *  brief carries no f0 (absence stays honest, no "–" placeholder). Pure; returns one KPI div or "". */
function f0KpiHtml(t) {
  const f0 = (t && t.f0_hz != null) ? Number(t.f0_hz) : null;
  if (f0 == null || !isFinite(f0)) return "";
  const title = "target.f0_hz — cov and dislope score only frequencies f ≥ f0; everything below is masked (objective v3)";
  return `<div class="kpi" title="${esc(title)}"><span>Scoring floor ` +
    `<small style="font-family:var(--f-mono);font-size:0.6rem;color:var(--muted)">f≥</small></span>` +
    `<b>${esc(fmtHz(f0))}</b></div>`;
}

/** The compare mounting warn: a mounting difference is a different objective landscape (J improves
 *  under the enclosure), so it is never rankable across. Rendered under the generic mixed banner
 *  ONLY when mixed_keys carries "mounting". Pure; returns HTML or "". */
function mountingRankWarnHtml(mixed) {
  const keys = Array.isArray(mixed) ? mixed : [];
  if (!keys.includes("mounting")) return "";
  return `<p class="hint" role="note" style="margin:0"><span class="warn-text">mounting differs — ` +
    `a different objective landscape (J improves under the enclosure); never rank across mountings.</span></p>`;
}

/** The brief-driven seed derivation card (S1a feasibility record, written to the run's config.yaml
 *  under `feasibility`). Rendered ONLY when feasibility.derivation is a non-empty array; every
 *  sub-key may be absent (never crashes, "–" for missing numbers), and a missing feasibility block
 *  renders literally nothing. Pure; returns HTML or "". */
function seedDerivationHtml(feas) {
  if (!feas || typeof feas !== "object") return "";
  const rows = (Array.isArray(feas.derivation) ? feas.derivation : []).filter(r => r && typeof r === "object");
  if (!rows.length) return "";
  const rule = (feas.rule != null && feas.rule !== "")
    ? `<code>${esc(feas.rule)}</code>` : `<span class="muted">–</span>`;
  const cap = `${rule} — derived values clamped into the brief envelope and each knob's existing ` +
    `bounds; widening never automatic`;
  // below-f0 counts: only the groups whose screen_/verify_ keys arrived; the mask sentence stays
  const count = (n, total) =>
    `${n != null ? esc(n) : "–"}/${total != null ? esc(total) : "–"}`;
  const groups = [];
  if (feas.screen_freqs_below_f0 != null || feas.screen_freqs_total != null)
    groups.push(`screen: ${count(feas.screen_freqs_below_f0, feas.screen_freqs_total)} solved freqs below f0`);
  if (feas.verify_freqs_below_f0 != null || feas.verify_freqs_total != null)
    groups.push(`verify: ${count(feas.verify_freqs_below_f0, feas.verify_freqs_total)}`);
  const counts = groups.length
    ? `<p class="hint" style="margin:6px 0 0" role="note">${groups.join(" · ")} (masked under v3)</p>` : "";
  const body = rows.map(r => {
    const knob = (r.knob != null && r.knob !== "") ? esc(r.knob) : "–";
    // derived: the number in mm; when it was not derived AND nothing was applied, the entry's own
    // note explains why (never an invented number); otherwise "–"
    let derived;
    if (r.derived_mm != null && isFinite(Number(r.derived_mm)))
      derived = esc(_trimNum(r.derived_mm) + " mm");
    else if (r.applied == null && r.note)
      derived = `<span class="muted">${esc(r.note)}</span>`;
    else
      derived = "–";
    const applied = r.applied == null ? "–" : (r.applied ? "applied" : "not applied");
    const flag = r.clamped_to_bound === true
      ? `<span class="pill warn">clamped to bound</span>`
      : `<span class="muted">seeded</span>`;
    return `<tr><td data-seedknob="${esc(r.knob ?? "")}">${knob}</td><td class="r">${derived}</td><td>${esc(applied)}</td><td>${flag}</td></tr>`;
  }).join("");
  return `<div class="fig seed-derivation-card"><h3>Seed derivation (brief-driven, clamp-only)</h3>
      <div class="cap">${cap}</div>${counts}
      <div class="tbl-wrap"><table>
        <thead><tr><th>Knob</th><th class="r">Derived</th><th>Applied</th><th>Result</th></tr></thead>
        <tbody>${body}</tbody>
      </table></div></div>`;
}

/** The brief editor's objective-version options (v3 = the below-f0 scoring floor). Pure; returns
 *  the three <option> tags, selected per the brief's own objective.version. */
function objectiveVersionOptionsHtml(sel) {
  return [
    [1, "1 — default scoring"],
    [2, "2 — opt-in updated scoring"],
    [3, "3 — scoring floor f0 (cov + dislope score only f ≥ f0)"],
  ].map(([v, label]) => `<option value="${v}" ${sel === v ? "selected" : ""}>${esc(label)}</option>`)
    .join("\n                ");
}

// Exported pure helpers for offline node tests (tests/test_gui_brief_authoring.py) — the
// view3d.js::mirrorMesh precedent; unused by the browser module graph.
export { runProvenanceGroup, renderProvenanceBadges, restartScheduleHtml, stepChipHtml,
         stepInvByName, qdProvenanceCaption, f11CaveatHtml,
         stopAffordanceFor, stopRegionHtml, currentRunCard,
         toolbarPillFor, toolbarPillHtml, resumeArgsFor, resumeableSearchJob };


export { f0KpiHtml, mountingRankWarnHtml, seedDerivationHtml, objectiveVersionOptionsHtml };

export { continueRunAvailable, continueRunArgs };


/** Compact run-detail card: top up an opened search run with N NEW evaluations while reusing the
 *  run's stored configuration. Rendered only when continueRunAvailable(d); validation, the POST and
 *  the job poll live in viewRunDetail's wiring below. Pure; returns HTML ("" when not available). */
function continueRunCardHtml(d, sum) {
  if (!continueRunAvailable(d)) return "";
  const total = sum && sum.n != null ? Number(sum.n).toLocaleString() : "–";
  const reason = d && d.stop_reason != null ? String(d.stop_reason) : "";
  const doubtful = !!reason && reason !== "budget" && reason !== "interrupted";
  const warn = doubtful
    ? `<p class="muted" role="note" style="font-size:0.78rem;margin:6px 0 0">This run stopped on ` +
      `<span class="mono">${esc(reason)}</span> — a top-up may add no new work.</p>`
    : "";
  return `<div class="card" id="continue-run-card" style="margin-top:-8px">
    <div class="eyebrow">Run control</div>
    <h3 style="margin:4px 0 0">Continue this run</h3>
    <p class="muted" style="font-size:0.85rem;margin:6px 0 0">${esc(total)} evaluations so far.
      Continuing uses this run's saved configuration.</p>
    <div class="btn-row continue-run-row">
      <label for="continue-run-n">Additional evaluations</label>
      <input id="continue-run-n" type="number" min="1" max="5000" step="1" inputmode="numeric"
             placeholder="50" aria-describedby="continue-run-help">
      <button class="primary" id="continue-run-btn">Continue run</button>
      <button class="btn" id="continue-run-cancel" hidden
              title="Removes this request from the queue — nothing has started yet">Cancel queued request</button>
    </div>
    <p class="muted" id="continue-run-help" style="font-size:0.78rem;margin:6px 0 0">
      Adds N new evaluations — one candidate solve each, the search's iteration unit.
      Candidates already solved replay free; the run keeps its saved configuration.</p>
    ${warn}
    <span class="muted" id="continue-run-status" role="status" style="display:block;font-size:0.8rem;margin:4px 0 0"></span>
  </div>`;
}


async function viewRunDetail(id) {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let d;
  try { d = await api("/api/run/" + id); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }
  await loadParamCatalog();       // P9: catalog-grounded geometry-knob hover docs; failure degrades to raw keys

  const sum = d.summary || d;
  const t = d.target || {};
  const S = d.seed || {};
  const B = d.best || {};
  const w = Object.assign({}, DEFW, d.weights || {});

  const nf = sum.n - sum.n_ok;
  const failPct = sum.n > 0 ? ((nf / sum.n) * 100).toFixed(1) : "–";
  const ch = betterPct(sum.seed_j, sum.best_j);
  const pinnedSens = (d.sens || []).filter(s => Math.max(s.at_lo, s.at_hi) >= 4);
  const coverTarget = `${fmtDeg(t.coverage_h_deg)} × ${fmtDeg(t.coverage_v_deg)}`;
  const bandStr = `${fmtHz(t.band_lo_hz)} – ${fmtHz(t.band_hi_hz)}`;
  const dimsStr = sum.dims ? dimStr(sum.dims) : "–";

  // G1 provenance strip (plan §7, re-read from the reader's solve_group): the identity baseline
  // (backend + grid) always shows, plus every non-default key the run carries — read-and-show
  // straight from run_detail, tooltip naming solve_group.<key>.
  const prov = runProvenanceGroup(d);
  const provBadges = renderProvenanceBadges(prov.group, "", prov.tips);
  const provStripHtml = provBadges ? `<div class="pill-row" style="margin:8px 0 0">${provBadges}</div>` : "";

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Run · ${esc(sum.generator ? "typology generator" : "mesher family")} · ${esc(sum.family || "")} mesh · ${esc(sum.mode || "")} fidelity${sum.brief ? " · brief " + esc(sum.brief) : ""}${sum.cma_seed != null ? " · random seed " + esc(sum.cma_seed) : ""}</div>
        <h2>${esc(sum.name || id)}</h2>
        <p class="mono muted" style="font-size:0.78rem">${esc(id)}</p>
        ${provStripHtml}
        ${f11CaveatHtml(d)}
      </div>

      <!-- Designer header: key facts -->
      <div class="kpis" id="kpi-strip"></div>

      ${restartScheduleHtml(d, id)}

      ${seedDerivationHtml(d.feasibility)}

      <!-- Actions -->
      <div class="btn-row">
        <a class="btn primary" href="#/run/${esc(id)}/evolution">▶ Evolution time-lapse</a>
        <a class="btn" href="#/run/${esc(id)}/archive" title="Quality-diversity atlas: objective per descriptor bin (CMA-ME runs only)">QD atlas</a>
        <a class="btn" href="#/run/${esc(id)}/balloon" title="W6 Balloon: the stored directivity balloon in 3D — shape + colour = SPL, white isobar rings, radar slicer, freq × angle slice">◉ Balloon 3D</a>
        <a class="btn" href="#/run/${esc(id)}/3d">3D view</a>
        <a class="btn" href="#/compare?a=${esc(id)}">Compare with…</a>
        <span id="report-slot">${sum.has_report
          ? `<a class="btn" href="/runs/${esc(id)}/report.html" target="_blank" rel="noopener">Open full report ↗</a>`
          : `<button id="btn-gen-report" title="Builds the detailed HTML report (about 30 s)">Make full report</button>`}</span>
        <button id="btn-step" title="Writes closed STEP solids (mm) of the 3 best designs for CAD or 3D printing">Export STEP for CAD (top 3)</button>
      </div>
      ${continueRunCardHtml(d, sum)}
      <div id="run-files" class="run-files"></div>

      <!-- Acoustic performance charts (designer order) -->
      <div class="grid2">
        <div class="fig">
          <h3>${tip("bw", "Beamwidth (−6 dB)")} vs target</h3>
          <div class="cap">Total angle between the −6 dB points. Shaded: target ±10 %; lighter panel: the scored band.</div>
          <div class="legend">
            <span><i style="color:var(--best)"></i>best, horizontal</span>
            <span><i style="color:var(--best)" class="dash"></i>best, vertical</span>
            <span><i style="color:var(--seed)"></i>start H</span>
            <span><i style="color:var(--seed)" class="dash"></i>start V</span>
            <span><i style="color:var(--label)"></i>target H</span>
            <span><i style="color:var(--label)" class="dash"></i>target V</span>
          </div>
          <svg id="c-bw"></svg>
        </div>
        <div class="fig">
          <h3>${tip("di_db", "Directivity index")} vs target</h3>
          <div class="legend">
            <span><i style="color:var(--seed)"></i>start</span>
            <span><i style="color:var(--best)"></i>best</span>
            <span><i style="color:var(--label)" class="dash"></i>DI target</span>
          </div>
          <svg id="c-di"></svg>
        </div>
        <div class="fig">
          <h3>${tip("on_axis", "On-axis response")} (mean removed)</h3>
          <div class="legend">
            <span><i style="color:var(--seed)"></i>start</span>
            <span><i style="color:var(--best)"></i>best</span>
          </div>
          <svg id="c-axis"></svg>
        </div>
        <div class="fig">
          <h3>${tip("z_re", "Throat impedance")}</h3>
          <div class="cap">Normalised to ρc. Resistance near 1 = the horn loads the driver well; below 0.7 counts as poor loading. Reactance: + = mass-like.</div>
          <div class="legend">
            <span><i style="color:var(--best)"></i>resistance (best)</span>
            <span><i style="color:var(--best)" class="dash"></i>reactance (best)</span>
            <span><i style="color:var(--seed)"></i>start</span>
            <span><i style="color:var(--warn)" class="dash"></i>0.7 threshold</span>
          </div>
          <svg id="c-zre"></svg>
        </div>
      </div>

      <!-- Polar maps -->
      <div class="fig">
        <div class="fig-head"><h3>${tip("polar", "Directivity (isobars)")}</h3>
          <label class="evo-opt" style="color:var(--ink)"><input type="checkbox" id="iso-start"> also show the starting design</label></div>
        <div class="cap">Level relative to on-axis at 2 m, in 3 dB colour bands from −30 to 0 dB, with white contour lines every 3 dB (the heavier line is −6 dB: the beamwidth edge). Frequency across, angle up. Hover for a readout. Interpolated between the ${((d.best || {}).freqs || []).length} solved frequencies.</div>
        <div class="maps iso-maps" id="polar-maps"></div>
      </div>

      <!-- Wall profile -->
      <div class="fig">
        <h3>Wall cross-section</h3>
        <div class="cap">Section through the solved mesh, true scale in mm: horizontal plane to the right, vertical plane mirrored to the left, throat at the bottom. Includes the outer shell and rear. Band = horn wall, interior = sound bore; dashed amber = starting design; dot = throat.</div>
        <div class="legend">
          <span><i style="color:var(--best)"></i>best (filled)</span>
          <span><i style="color:var(--seed)" class="dash"></i>start</span>
        </div>
        <svg id="c-prof"></svg>
      </div>

      <!-- Inline 3D (lazy): the best design rendered right here — the dedicated 3D page stays -->
      <div class="fig run-3d-fig">
        <div class="fig-head"><h3>Best design in 3D</h3>
          <label class="evo-opt" style="color:var(--ink)"><input type="checkbox" id="inline3d-shadows"> wall shadows</label></div>
        <div class="cap">The solved mesh of the best design, loaded in place after the page settles (no tab click needed). Drag to orbit · scroll to zoom · right-drag to pan. Full-screen version on the <a href="#/run/${esc(id)}/3d">3D view</a>.</div>
        <div id="inline-3d" data-v3d style="position:relative;height:300px;border:1px solid var(--rule);border-radius:6px;overflow:hidden;background:var(--viz-canvas,#e9edf0)">
          <div class="view3d-fallback">Loading 3D…</div>
        </div>
        <div class="hint" id="inline3d-note" role="status"></div>
      </div>

      <hr class="sep">

      <!-- Search history -->
      <h3>How the search went</h3>
      <div class="grid2">
        <div class="fig"><h3>Convergence</h3>
          <div class="cap">Every eval (dots) and running best (line). Failures excluded.</div>
          <svg id="c-conv"></svg>
        </div>
        <div class="fig"><h3>${tip("J", "Score")} breakdown: start vs best</h3>
          <div class="cap">Weighted contribution per term. Upper bar = start, lower = best.</div>
          <svg id="c-terms"></svg>
        </div>
      </div>

      <!-- Sensitivity -->
      <div class="fig">
        <h3>${tip("knob", "Shape parameters")}</h3>
        <div class="cap">${tip("rho", "Influence")} = Spearman ρ. ${tip("pinned", "At-limit")} = of the 6 best designs how many sit at each bound.</div>
        <div class="tbl-wrap"><table id="sens-table"></table></div>
      </div>

      <!-- CMA covariance (search distribution; absent on older runs) -->
      <div class="fig" id="cma-cov-block" style="display:none">
        <h3>${tip("cma_cov", "CMA covariance")}</h3>
        <div class="cap" id="cma-cov-cap">Unit-box search scales from the final ES. Large ${tip("cma_std", "σ√Cᵢᵢ")} ⇒ still exploring that knob; eigenvectors are coupled J-directions, not acoustic Sobol indices.</div>
        <div class="tbl-wrap"><table id="cma-cov-table"></table></div>
        <div id="cma-eig-wrap" class="stack" style="gap:8px;margin-top:10px"></div>
        <div id="pin-plan-wrap" style="display:none;margin-top:14px">
          <h3 style="margin:0 0 6px">${tip("pin_plan", "Pin plan")}</h3>
          <div class="cap">Recommendations from CMA scales + Spearman guard. Does not change the config — run <code>hornlab-search pin-plan --run ${esc(sum.id || id)}</code> to write <code>PIN_PLAN.md</code> / a patched YAML.</div>
          <div class="tbl-wrap"><table id="pin-plan-table"></table></div>
        </div>
      </div>

      <!-- Failures -->
      <div class="stack" style="gap:6px">
        <h3>${tip("failures", "Failures")}</h3>
        <div class="pill-row">${failurePills(sum.failures)}</div>
      </div>

      ${d.command ? `<div class="stack" style="gap:6px"><h3>Command</h3><div class="log-tail" style="max-height:60px">${esc(d.command)}</div></div>` : ""}
    </div>`;

  // KPI strip (designer-first order)
  const budgetPct = sum.budget ? Math.round(((sum.n || 0) / sum.budget) * 100) : 0;
  const overBudget = !!(sum.budget && sum.n > sum.budget);
  const kpis = [
    [`${tip("bw", "Coverage target")}`, coverTarget],
    [`${tip("band", "Band")}`, bandStr],
    [`${tip("dims", "Horn size")} <small style="font-family:var(--f-mono);font-size:0.6rem;color:var(--muted)">W×H×D outer</small>`, dimsStr],
    [`${tip("J", "Score: start")}`, fmt(sum.seed_j && sum.seed_j < 900 ? sum.seed_j : null)],
    [`${tip("J", "Score: best")}`, fmt(sum.best_j)],
    ["Change vs start", ch],
    [`${tip("budget", "Budget used")}`,
     `${(sum.n || 0).toLocaleString()}${sum.budget ? " / " + sum.budget.toLocaleString() : ""}${overBudget ? " over budget" : ""}`,
     overBudget ? "bad" : budgetPct >= 90 ? "warn" : ""],
    [`${tip("failures", "Failures")}`, `${nf} (${failPct}%)`],
    [`${tip("pinned", "At limit")}`, pinnedSens.length > 0 ? `<b class="bad">${pinnedSens.length}</b>` : pill("0", "good")],
  ].map(([k, v, cls]) => `<div class="kpi"><span>${k}</span><b${cls ? ` class="${cls}"` : ""}>${v}</b></div>`);
  kpis.splice(2, 0, f0KpiHtml(t));          // right after Band; "" when the brief carries no f0
  document.getElementById("kpi-strip").innerHTML = kpis.filter(Boolean).join("");

  const F = S.freqs || B.freqs || [];
  const band = [t.band_lo_hz || 700, t.band_hi_hz || 5500];

  // One convention on every chart: horizontal plane solid, vertical plane dashed; start amber, best teal.
  const series2 = (key, w) => [
    ...(S[key + "_h"] ? [{ pts: F.map((f, i) => [f, S[key + "_h"][i] ?? null]), color: css("--seed"), w: 1.7 }] : []),
    ...(S[key + "_v"] ? [{ pts: F.map((f, i) => [f, S[key + "_v"][i] ?? null]), color: css("--seed"), w: 1.7, dash: true }] : []),
    ...(B[key + "_h"] ? [{ pts: F.map((f, i) => [f, B[key + "_h"][i] ?? null]), color: css("--best"), w }] : []),
    ...(B[key + "_v"] ? [{ pts: F.map((f, i) => [f, B[key + "_v"][i] ?? null]), color: css("--best"), w, dash: true }] : []),
  ];

  // Beamwidth vs target, target ±10 % shaded per plane
  if (F.length && (S.bw_h || B.bw_h)) {
    const th = t.coverage_h_deg, tv = t.coverage_v_deg;
    const bwAll = [...(S.bw_h || []), ...(S.bw_v || []), ...(B.bw_h || []), ...(B.bw_v || []), th, tv].filter(v => v != null);
    const bmax = Math.min(200, Math.ceil(Math.max(...bwAll) * 1.08 / 10) * 10) || 180;
    const fill = [], hlines = [];
    if (th) { fill.push({ y0: th * 0.9, y1: th * 1.1, color: css("--best"), opacity: 0.10 }); hlines.push({ y: th, color: css("--label") }); }
    if (tv && tv !== th) { fill.push({ y0: tv * 0.9, y1: tv * 1.1, color: css("--best"), opacity: 0.07 }); hlines.push({ y: tv, color: css("--label"), dash: true }); }
    chart(document.getElementById("c-bw"), {
      xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [0, bmax], fill,
      xticks: FT, yticks: niceTicks(0, bmax, 5), xlabel: "Hz", ylabel: "deg", band, hlines,
      series: series2("bw", 2.2),
    });
  }

  // DI vs target
  if (F.length && (S.di || B.di)) {
    const dit = t.di_target_db ?? diFromCuts(t.coverage_h_deg || 90, t.coverage_v_deg || 90);
    const dall = [...(S.di || []), ...(B.di || []), dit].filter(v => v != null);
    const dlo = Math.floor(Math.min(...dall) - 1), dhi = Math.ceil(Math.max(...dall) + 1);
    chart(document.getElementById("c-di"), {
      xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [dlo, dhi],
      xticks: FT, yticks: niceTicks(dlo, dhi, 5), xlabel: "Hz", ylabel: "dB", band,
      hlines: [{ y: dit, color: css("--label"), dash: true }],
      series: [
        { pts: F.map((f, i) => [f, (S.di || [])[i] ?? null]), color: css("--seed"), w: 1.7 },
        { pts: F.map((f, i) => [f, (B.di || [])[i] ?? null]), color: css("--best"), w: 2.2 },
      ],
    });
  }

  // On-axis (relative, mean removed)
  if (F.length && (S.on_axis || B.on_axis)) {
    const aall = [...(S.on_axis || []), ...(B.on_axis || [])].filter(v => v != null);
    const alo = Math.floor(Math.min(...aall, -3) - 1), ahi = Math.ceil(Math.max(...aall, 3) + 1);
    chart(document.getElementById("c-axis"), {
      xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [alo, ahi],
      xticks: FT, yticks: niceTicks(alo, ahi, 5), xlabel: "Hz", ylabel: "dB", band,
      hlines: [{ y: 0, color: css("--label") }],
      series: [
        { pts: F.map((f, i) => [f, (S.on_axis || [])[i] ?? null]), color: css("--seed"), w: 1.7 },
        { pts: F.map((f, i) => [f, (B.on_axis || [])[i] ?? null]), color: css("--best"), w: 2.2 },
      ],
    });
  }

  // Throat impedance, normalised to rho*c: resistance (solid) and reactance (dashed, engineering sign:
  // + = mass-like). The solver works in exp(-i w t), so reactance X = -Im Z here.
  if (F.length && (S.z_re || B.z_re)) {
    const X = d => (d.z_im || []).map(v => v == null ? null : -v);
    const zall = [...(S.z_re || []), ...(B.z_re || []), ...X(B), ...X(S)].filter(v => v != null);
    const zlo = Math.min(0, Math.floor(Math.min(...zall) * 10) / 10), zhi = Math.max(1.2, Math.ceil(Math.max(...zall) * 10) / 10);
    chart(document.getElementById("c-zre"), {
      xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [zlo, zhi],
      xticks: FT, yticks: niceTicks(zlo, zhi, 5), xlabel: "Hz", ylabel: "×ρc", band,
      hlines: [{ y: 1.0, color: css("--label"), dash: true }, { y: 0.7, color: css("--warn"), dash: true }, { y: 0, color: css("--label") }],
      series: [
        { pts: F.map((f, i) => [f, (S.z_re || [])[i] ?? null]), color: css("--seed"), w: 1.7 },
        { pts: F.map((f, i) => [f, X(S)[i] ?? null]), color: css("--seed"), w: 1.7, dash: true },
        { pts: F.map((f, i) => [f, (B.z_re || [])[i] ?? null]), color: css("--best"), w: 2.2 },
        { pts: F.map((f, i) => [f, X(B)[i] ?? null]), color: css("--best"), w: 1.8, dash: true },
      ],
    });
  }

  // Wall cross-section (true aspect): best filled, start as an outline
  wallSection(document.getElementById("c-prof"), [
    ...(S.profile ? [{ profile: S.profile, color: css("--seed"), dash: true }] : []),
    ...(B.profile ? [{ profile: B.profile, color: css("--best"), filled: true }] : []),
  ], { H: 320 });

  // Inline 3D for the best design (no tab click needed). Lazy by design: the page has rendered,
  // only now does the mesh fetch start — and if the user navigated away in the meantime the build
  // is skipped, because route() disposes [data-v3d] containers while they are still attached and
  // a scene must never start inside a detached container (that is how renderers leak). The inline
  // viewer is the only AUTO-loaded 3D scene for this design; the dedicated 3D page stays click-only.
  const inline3d = document.getElementById("inline-3d");
  const inlineNote = document.getElementById("inline3d-note");
  if (inline3d) {
    const inlineHash = B.hash || sum.best_hash;
    const shBox = document.getElementById("inline3d-shadows");
    let inlineShadows = true;
    try { inlineShadows = localStorage.getItem("hl-v3d-shadows") !== "0"; } catch {}   // same toggle as the 3D page
    if (shBox) shBox.checked = inlineShadows;
    if (!inlineHash) {
      inline3d.innerHTML = `<div class="view3d-fallback">No best design hashed yet — nothing to render in 3D.</div>`;
    } else {
      api("/api/mesh/" + id + "/" + inlineHash).then(meshD => {
        if (!inline3d.isConnected) return;               // navigated away while the mesh was loading
        const qNote = String((meshD || {}).quadrants || "") === "1" ? "quarter model mirrored to the full horn"
          : ((meshD || {}).quadrants === "14" || (meshD || {}).quadrants === "12") ? "half model mirrored to the full horn"
          : "full model, no mirroring";
        if (inlineNote) inlineNote.textContent =
          `${((meshD || {}).n_tris != null ? meshD.n_tris : "?")} triangles in the meshed domain (${qNote}).`;
        const start = () => init3d(inline3d, meshD, B.profile, S.profile, shBox.checked).catch(() => {
          if (inline3d.isConnected && inlineNote) inlineNote.textContent =
            "3D could not start (three.js did not load) — the wall cross-section above carries the geometry.";
        });
        start();
        if (shBox) shBox.onchange = () => {
          try { localStorage.setItem("hl-v3d-shadows", shBox.checked ? "1" : "0"); } catch {}
          if (inline3d._dispose3d) inline3d._dispose3d();
          start();
        };
      }).catch(() => {
        if (inline3d.isConnected) inline3d.innerHTML =
          `<div class="view3d-fallback">Could not load the mesh for this design — the 2D wall cross-section above carries the geometry.</div>`;
        if (inline3d.isConnected && inlineNote) inlineNote.textContent = "";
      });
    }
  }

  // Directivity isobars (Boundary Lab style): best design H and V; the start design on request
  const mapsEl = document.getElementById("polar-maps");
  function drawIsobars() {
    mapsEl.innerHTML = "";
    const withStart = document.getElementById("iso-start")?.checked && S.polar_h;
    const plots = [["Best design · horizontal", B.polar_h, B], ["Best design · vertical", B.polar_v, B]];
    if (withStart) plots.push(["Starting design · horizontal", S.polar_h, S], ["Starting design · vertical", S.polar_v, S]);
    for (const [lbl, rows, D2] of plots) {
      if (!rows) continue;
      const sv = document.createElementNS(NS, "svg"); sv.setAttribute("class", "polar");
      sv.setAttribute("role", "img"); sv.setAttribute("aria-label", lbl + " isobar plot");
      mapsEl.appendChild(sv);
      // drawn after layout, so each plot is measured at its real width
      requestAnimationFrame(() => isobarMap(sv, rows, D2.angles || [], D2.freqs || F, { title: lbl, H: 300 }));
    }
  }
  drawIsobars();
  document.getElementById("iso-start").onchange = drawIsobars;

  // Convergence
  if (d.J && F.length) {
    const Js = (d.J || []).map((j, i) => [i, j]).filter(p => p[1] != null);
    let rb = Infinity; const runBest = Js.map(p => [p[0], (rb = Math.min(rb, p[1]))]);
    const ymax = Math.max((sum.seed_j || 0) * 1.6, (sum.best_j || 0) * 2, 1);
    const svg = document.getElementById("c-conv");
    chart(svg, {
      xlim: [0, sum.n || Js.length], ylim: [0, ymax],
      xticks: niceTicks(0, sum.n || Js.length, 5), yticks: niceTicks(0, ymax, 5),
      xlabel: "evaluation", ylabel: "score",
      series: [
        { pts: Js, color: css("--muted"), dots: true, opacity: 0.8 },
        { pts: runBest, color: css("--best"), w: 2.2 },
      ],
      hlines: [{ y: sum.seed_j, color: css("--seed"), dash: true }],
    });
  }

  // Terms bar chart
  if (d.terms_seed && d.terms_best) {
    const svgT = document.getElementById("c-terms");
    svgT.innerHTML = "";
    const W = 460, rowH = 32, H = TERM_ORDER.length * rowH + 30;
    svgT.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const vals = TERM_ORDER.map(k => [w[k] * (d.terms_seed[k] || 0), w[k] * (d.terms_best[k] || 0)]);
    const vmax = Math.max(...vals.flat(), 1e-9);
    const L = 90, R = 54, X = v => L + v / vmax * (W - L - R);
    TERM_ORDER.forEach((k, i) => {
      const y = 6 + i * rowH;
      const gEntry = GLOSSARY[k];
      const label = gEntry ? gEntry.label : k;
      const lab = el("text", { x: L - 8, y: y + 15, "text-anchor": "end" }, svgT);
      lab.textContent = label + (w[k] ? "" : " (w=0)");
      [[vals[i][0], "--seed", 0], [vals[i][1], "--best", 12]].forEach(([v, c, dy]) => {
        el("rect", { x: L, y: y + dy, width: Math.max(0.5, X(v) - L), height: 10, rx: 2, fill: css(c) }, svgT);
        const tv = el("text", { x: X(v) + 4, y: y + dy + 9 }, svgT); tv.textContent = v.toFixed(3);
      });
    });
    const lg = el("text", { x: L, y: H - 4 }, svgT); lg.textContent = "upper = start · lower = best · weighted";
  }

  // Sensitivity table
  const sensT = document.getElementById("sens-table");
  if (d.sens && d.sens.length) {
    let s = `<thead><tr>
      <th>Parameter</th><th class="r">Low limit</th><th class="r">High limit</th>
      <th class="r">Best value</th><th class="r">${tip("rho", "Influence ρ")}</th><th></th>
      <th class="r">${tip("pinned", "Top-6 at low")}</th><th class="r">at high</th></tr></thead><tbody>`;
    for (const p of d.sens) {
      const bar = `<svg width="90" height="10" viewBox="0 0 90 10" aria-hidden="true">
        <rect x="45" y="0" width="0.8" height="10" fill="${css("--muted")}"/>
        <rect x="${p.rho < 0 ? 45 + p.rho * 45 : 45}" y="2" width="${Math.abs(p.rho || 0) * 45}" height="6" rx="1"
          fill="${css(p.rho > 0 ? "--seed" : "--best")}"/></svg>`;
      const flag = v => v >= 4 ? `<span class="pill bad">${v}/6</span>` : v >= 2 ? `<span class="pill warn">${v}/6</span>` : `${v}/6`;
      const atHi = p.at_hi != null ? p.at_hi : 0;
      // P9: the raw key stays the visible text (it is the vocabulary the rest of the page uses);
      // hover now carries the catalog's label [unit], meaning and search range for run <sum.name>.
      s += `<tr><td class="mono">${paramTipHtml(sum.name, p.key, p.key)}</td>
        <td class="r">${fmt(p.lo, 3)}</td><td class="r">${fmt(p.hi, 3)}</td>
        <td class="r">${fmt(p.best, 3)}</td>
        <td class="r">${p.rho != null ? p.rho.toFixed(2) : "–"}</td>
        <td>${bar}</td><td class="r">${flag(p.at_lo || 0)}</td><td class="r">${flag(atHi)}</td></tr>`;
    }
    sensT.innerHTML = s + "</tbody>";
  } else {
    sensT.innerHTML = "<tr><td class='muted'>No sensitivity data.</td></tr>";
  }

  // CMA covariance (final ES; from run.json cma_covariance)
  const cov = d.cma_covariance;
  const covBlock = document.getElementById("cma-cov-block");
  if (covBlock && cov && Array.isArray(cov.coordinates) && cov.coordinates.length) {
    covBlock.style.display = "";
    const cond = cov.condition_number != null ? Number(cov.condition_number).toFixed(1) : "–";
    const cap = document.getElementById("cma-cov-cap");
    if (cap) {
      cap.innerHTML = `σ=${esc(cov.sigma != null ? Number(cov.sigma).toFixed(3) : "–")} · cond(C)=${esc(cond)} · `
        + `large ${tip("cma_std", "σ√Cᵢᵢ")} ⇒ still exploring that knob; `
        + `eigenvectors are coupled J-directions, not acoustic Sobol indices.`;
    }
    const maxStd = Math.max(...cov.coordinates.map(r => Number(r.std_unit) || 0), 1e-12);
    let ct = `<thead><tr>
      <th>Parameter</th><th class="r">${tip("cma_Cii", "Cᵢᵢ")}</th>
      <th class="r">${tip("cma_std", "σ√Cᵢᵢ")}</th><th class="r">Share</th><th></th></tr></thead><tbody>`;
    for (const r of cov.coordinates) {
      const std = Number(r.std_unit) || 0;
      const share = r.share != null ? Number(r.share) : 0;
      const w = Math.max(0, Math.min(100, (std / maxStd) * 100));
      ct += `<tr><td class="mono">${paramTipHtml(sum.name, r.key, r.key)}</td>
        <td class="r">${fmt(r.C_ii, 4)}</td><td class="r">${fmt(std, 4)}</td>
        <td class="r">${(100 * share).toFixed(0)}%</td>
        <td><svg width="90" height="10" viewBox="0 0 90 10" aria-hidden="true">
          <rect x="0" y="2" width="${w * 0.9}" height="6" rx="1" fill="${css("--best")}"/></svg></td></tr>`;
    }
    const covT = document.getElementById("cma-cov-table");
    if (covT) covT.innerHTML = ct + "</tbody>";
    const eigWrap = document.getElementById("cma-eig-wrap");
    if (eigWrap && Array.isArray(cov.eigenpairs) && cov.eigenpairs.length) {
      eigWrap.innerHTML = cov.eigenpairs.map(ep => {
        const loads = (ep.top_loadings || []).slice(0, 5)
          .map(L => `<code>${esc(L.key)}</code>&nbsp;${Number(L.loading).toFixed(2)}`)
          .join(" · ");
        const frac = ep.fraction != null ? `${(100 * Number(ep.fraction)).toFixed(0)}%` : "–";
        return `<div class="cap"><b>Eigen ${esc(ep.rank)}</b> · λ=${esc(fmt(ep.eigenvalue, 4))} · `
          + `${esc(frac)} of trace · top loadings: ${loads || "–"}</div>`;
      }).join("");
    }
    const pinPlan = d.pin_plan;
    const pinWrap = document.getElementById("pin-plan-wrap");
    const pinT = document.getElementById("pin-plan-table");
    if (pinWrap && pinT && pinPlan && Array.isArray(pinPlan.decisions) && pinPlan.decisions.length) {
      pinWrap.style.display = "";
      let pt = `<thead><tr><th>Key</th><th>Action</th><th class="r">Value</th>
        <th class="r">share</th><th class="r">σ√Cᵢᵢ</th><th class="r">ρ</th><th>Reasons</th></tr></thead><tbody>`;
      for (const row of pinPlan.decisions) {
        const act = row.action === "pin"
          ? `<span class="pill warn">pin</span>`
          : `<span class="pill">keep</span>`;
        const rho = row.rho != null ? Number(row.rho).toFixed(2) : "–";
        pt += `<tr><td class="mono">${paramTipHtml(sum.name, row.key, row.key)}</td>
          <td>${act}</td><td class="r">${row.value != null ? fmt(row.value, 4) : "–"}</td>
          <td class="r">${fmt(row.share, 4)}</td><td class="r">${fmt(row.std_unit, 4)}</td>
          <td class="r">${rho}</td>
          <td class="muted" style="font-size:0.8rem">${esc((row.reasons || []).join("; "))}</td></tr>`;
      }
      pinT.innerHTML = pt + "</tbody>";
    }
  }

  // P9 (catalog hover docs): the seed-derivation call site is pinned as seedDerivationHtml(d.feasibility)
  // with no config-name argument, so the card's knob cells identify themselves via data-seedknob and
  // this pass attaches the catalog-grounded tooltip using sum.name. Missing docs keep the raw cell.
  for (const td of ROOT.querySelectorAll(".seed-derivation-card td[data-seedknob]"))
    if (td.dataset.seedknob) td.innerHTML = paramTipHtml(sum.name, td.dataset.seedknob, td.dataset.seedknob);

  // Files the user can take away: STEP downloads (after an export) and the full report.
  // `step_files` is the unchanged name list; the C-1 `step_files_detail` sidecar data is matched
  // by name and each chip flows through stepChipHtml: with an inventory it gains the face/tool
  // provenance inline, without one it stays exactly the download pill it always was.
  function renderFiles(files, detail) {
    const box = document.getElementById("run-files");
    if (!box) return;
    const invOf = stepInvByName(detail);
    box.innerHTML = files && files.length
      ? `<span class="muted">STEP solids (mm, full horn, throat open; add the driver flange in CAD):</span> ` +
        files.map(f => stepChipHtml(f, invOf.get(String(typeof f === "object" ? (f && f.name) || "" : f)) || null, id)).join(" ")
      : "";
  }
  renderFiles(d.step_files, d.step_files_detail);

  // Run a CPU job (report / STEP export) in place: progress on the button, result on this page.
  async function runInline(btn, kind, args, busyLabel, onDone) {
    const label = btn.textContent;
    btn.disabled = true;
    const r = await post("/api/jobs", { kind, args });
    if (r.error) { btn.disabled = false; btn.textContent = label; showToast("Could not start: " + r.error, "error"); return; }
    const t0 = Date.now();
    while (ROOT === currentRoot()) {
      btn.textContent = `${busyLabel} ${Math.round((Date.now() - t0) / 1000)} s`;
      await new Promise(res => setTimeout(res, 1500));
      let j; try { j = await api("/api/job/" + r.id); } catch { continue; }
      if (j.status === "running") continue;
      btn.disabled = false; btn.textContent = label;
      if (j.status === "done") onDone(j); else showToast(`${kind} failed: ` + ((j.log_tail || []).slice(-1)[0] || j.status), "error");
      return;
    }
  }
  document.getElementById("btn-step").onclick = e => runInline(e.currentTarget, "export-step", { run: id, top: 3 }, "Exporting…",
    async () => { const dd = await api("/api/run/" + id); renderFiles(dd.step_files, dd.step_files_detail); showToast("STEP files ready: download them below the buttons.", "good"); });
  const rBtn = document.getElementById("btn-gen-report");
  if (rBtn) rBtn.onclick = e => runInline(e.currentTarget, "report", { run: id }, "Building report…", () => {
    document.getElementById("report-slot").innerHTML = `<a class="btn" href="/runs/${esc(id)}/report.html" target="_blank" rel="noopener">Open full report ↗</a>`;
    showToast("Report ready.", "good");
  });

  // Continue an opened search run: N NEW evaluations on the same stored configuration. The pure
  // helper owns validation/args; this block only touches the DOM and polls the job. A job that
  // queues behind the GPU's current run stays cancellable until it actually starts.
  const contBtn = document.getElementById("continue-run-btn");
  if (contBtn) {
    const contInput = document.getElementById("continue-run-n");
    const contStatus = document.getElementById("continue-run-status");
    const contCancel = document.getElementById("continue-run-cancel");
    const say = (msg, cls = "muted") => {
      if (!contStatus) return;
      contStatus.textContent = msg;
      contStatus.className = cls;
    };
    const setBusy = busy => {
      contBtn.disabled = busy;
      if (contInput) contInput.disabled = busy;
    };
    const showCancel = on => {
      if (contCancel) contCancel.hidden = !on;
    };
    let activeJobId = null;
    let queued = false;
    let stopped = false;         // set by Cancel queued request: the poll loop must not overwrite its message
    const startContinue = async () => {
      if (contBtn.disabled) return;
      const checked = continueRunArgs({ id, mode: d.mode || sum.mode }, contInput ? contInput.value : "");
      if (checked.error) {
        say(checked.error, "error-text");
        if (contInput) { contInput.setAttribute("aria-invalid", "true"); contInput.focus(); }
        return;
      }
      if (contInput) contInput.removeAttribute("aria-invalid");
      stopped = false;
      queued = false;
      activeJobId = null;
      showCancel(false);
      setBusy(true);
      say("Starting…");
      let r;
      try { r = await post("/api/jobs", { kind: "search", args: checked.args }); }
      catch (e) { setBusy(false); say("Could not start: " + e.message, "error-text"); return; }
      if (r.error) { setBusy(false); say("Could not start: " + r.error, "error-text"); return; }
      activeJobId = r.id;
      if (r.status === "queued") {
        queued = true;
        showCancel(true);
        say(`Queued behind the current run (position ${r.position}) — starts automatically when the GPU is free.`);
      } else {
        say(`Started job ${r.id} — ${checked.n} more evaluation${checked.n === 1 ? "" : "s"}.`);
      }
      while (ROOT === currentRoot() && !stopped) {
        await new Promise(res => setTimeout(res, 2000));
        if (ROOT !== currentRoot() || stopped) return;
        let j;
        try { j = await api("/api/job/" + r.id); }
        catch {
          if (stopped) return;
          say(queued
            ? "Still waiting in queue — starts automatically when the GPU is free."
            : `Running ${r.id}…`);
          continue;
        }
        if (stopped) return;         // a cancel landed while this poll was in flight
        if (j.status === "queued") {
          queued = true;
          showCancel(true);
          say(`Waiting in queue (position ${j.queue_position}) — starts automatically when the GPU is free.`);
          continue;
        }
        if (j.status === "running") {
          queued = false;
          showCancel(false);
          say(`Running ${r.id}…`);
          continue;
        }
        if (j.status === "done") {
          showCancel(false);
          say("Done — reloading this run.");
          await viewRunDetail(id);
          return;
        }
        setBusy(false);
        showCancel(false);
        queued = false;
        const tail = Array.isArray(j.log_tail) && j.log_tail.length ? j.log_tail[j.log_tail.length - 1] : "";
        say(`Job ${r.id} ${j.status}${tail ? " — " + tail : ""}.`, "error-text");
        return;
      }
    };
    contBtn.onclick = startContinue;
    if (contInput) contInput.addEventListener("keydown", e => {
      if (e.key === "Enter") { e.preventDefault(); startContinue(); }
    });
    if (contCancel) contCancel.onclick = async () => {
      if (!activeJobId || !queued) return;
      contCancel.disabled = true;
      let r;
      try { r = await post("/api/job/" + activeJobId + "/cancel", { only_queued: true }); }
      catch (e) { contCancel.disabled = false; say("Could not cancel: " + e.message, "error-text"); return; }
      if (r.error) {
        // The job auto-started between the poll and this click. Never kill it here: keep the poll
        // running (the next tick shows "Running…"), hide the queued-only affordance, and leave the
        // Continue input disabled.
        contCancel.disabled = false;
        say("Could not cancel: " + r.error, "error-text");
        queued = false;
        showCancel(false);
        return;
      }
      stopped = true;              // the queued request never started; leave its message in place
      queued = false;
      activeJobId = null;
      showCancel(false);
      contCancel.disabled = false;
      setBusy(false);
      say("Queued request cancelled.");
    };
  }
}

// ── View 3 / 7: 3D view ────────────────────────────────────────────

async function viewRun3D(id) {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let runD, meshD;
  try { runD = await api("/api/run/" + id); }
  catch (e) { ROOT.innerHTML = errBanner("Could not load run: " + e.message); return; }
  const hash = (runD.summary || runD).best_hash || ((runD.best || {}).hash);
  if (!hash) { ROOT.innerHTML = errBanner("No best design hash for this run."); return; }
  try { meshD = await api("/api/mesh/" + id + "/" + hash); }
  catch (e) { ROOT.innerHTML = errBanner("Could not load mesh: " + e.message); return; }

  const sum = runD.summary || runD;
  const qNote = (() => { const q = String(meshD.quadrants || "1234");
    if (q === "1") return "quarter model mirrored to the full horn";
    if (q === "14" || q === "12") return "half model mirrored to the full horn";
    return "full model, no mirroring"; })();
  ROOT.innerHTML = `
    <div class="stack" style="gap:16px">
      <div>
        <div class="eyebrow">3D view</div>
        <h2>${esc(sum.name || id)}</h2>
        <p class="muted" style="font-size:0.82rem">Hash: <span class="mono">${esc(hash)}</span> · ${esc(meshD.n_tris || "?")} triangles in the meshed domain (${esc(qNote)})</p>
      </div>
      <div class="btn-row">
        <a class="btn" href="#/run/${esc(id)}">← Back to run</a>
        <a class="btn" href="#/run/${esc(id)}/balloon">◉ Balloon 3D</a>
      </div>
      <div class="fig-head">
        <label class="evo-opt" style="color:var(--ink)"><input type="checkbox" id="v3d-shadows" ${(() => { try { return localStorage.getItem("hl-v3d-shadows") === "0" ? "" : "checked"; } catch { return "checked"; } })()}> wall shadows</label>
      </div>
      <div id="view3d-wrap" data-v3d><div class="view3d-fallback">Loading 3D…</div></div>
      <p class="muted" style="font-size:0.8rem">Drag to orbit · scroll to zoom · right-drag to pan.</p>
    </div>`;

  const wrap = document.getElementById("view3d-wrap");
  const profile = (runD.best || {}).profile;
  const seedProfile = (runD.seed || {}).profile;      // dashed under best in the 2D fallback
  const shadowsBox = document.getElementById("v3d-shadows");
  let shadows = true;
  try { shadows = localStorage.getItem("hl-v3d-shadows") !== "0"; } catch {}
  if (shadowsBox) shadowsBox.checked = shadows;
  await init3d(wrap, meshD, profile, seedProfile, shadows);
  if (shadowsBox) shadowsBox.onchange = () => {
    try { localStorage.setItem("hl-v3d-shadows", shadowsBox.checked ? "1" : "0"); } catch {}
    if (wrap._dispose3d) wrap._dispose3d();
    init3d(wrap, meshD, profile, seedProfile, shadowsBox.checked).catch(() => {});
  };
}

// ── View 4: Compare ────────────────────────────────────────────────

async function viewCompare() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let allRuns = [];
  try { allRuns = await api("/api/runs"); } catch {}

  const hash = location.hash;
  const qaMatch = hash.match(/[?&]a=([^&]+)/);
  const qbMatch = hash.match(/[?&]b=([^&]+)/);
  const preA = qaMatch ? qaMatch[1] : "";
  const preB = qbMatch ? qbMatch[1] : "";

  const opts = allRuns.map(r =>
    `<option value="${esc(r.id)}">${esc(r.name)} — ${esc(r.id.slice(0, 20))}… (Score=${fmt(r.best_j)})</option>`
  ).join("");

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Compare two runs</div>
        <h2>Compare</h2>
      </div>
      <div class="compare-pickers">
        <div class="form-group">
          <label for="cmp-a">Run A</label>
          <select id="cmp-a" aria-label="run A">
            <option value="">— select —</option>${opts}
          </select>
        </div>
        <div class="form-group">
          <label for="cmp-b">Run B</label>
          <select id="cmp-b" aria-label="run B">
            <option value="">— select —</option>${opts}
          </select>
        </div>
      </div>
      <div><button id="btn-compare" class="primary">Compare</button></div>
      <div id="compare-result"></div>
    </div>`;

  if (preA) document.getElementById("cmp-a").value = preA;
  if (preB) document.getElementById("cmp-b").value = preB;

  async function doCompare() {
    const a = document.getElementById("cmp-a").value;
    const b = document.getElementById("cmp-b").value;
    const res = document.getElementById("compare-result");
    if (!a || !b) { res.innerHTML = `<div class="alert warn">Select both runs.</div>`; return; }
    if (a === b) { res.innerHTML = `<div class="alert warn">Select two different runs.</div>`; return; }
    res.innerHTML = `<p class="muted">Loading…</p>`;
    let cmp;
    try { cmp = await api(`/api/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`); }
    catch (e) { res.innerHTML = errBanner(e.message); return; }
    if (cmp.error) { res.innerHTML = errBanner(cmp.error); return; }

    const rowData = Object.entries(cmp.rows || {});
    const metricTable = rowData.length ? `
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>Metric</th><th>Unit</th>
            <th class="r">max |A − B|</th><th class="r">mean |A − B|</th><th class="r">n freqs</th></tr></thead>
          <tbody>${rowData.map(([k, v]) => `<tr>
            <td>${esc(CMP_LABEL[k] || k)} <small class="mono muted">${esc(k)}</small></td><td class="mono muted">${esc(v.unit || "")}</td>
            <td class="r">${fmt(v.max, 3)}</td><td class="r">${fmt(v.mean, 3)}</td><td class="r">${esc(v.n ?? "")}</td>
          </tr>`).join("")}</tbody>
        </table>
      </div>` : "<p class='muted'>No metric data.</p>";

    const dA = cmp.a || {}, dB = cmp.b || {};
    const FA = dA.freqs || [], FB = dB.freqs || [];
    const F = FA.length ? FA : FB;
    const band = [700, 5500];

    // G3: solve-group distinction (C-2 additive keys). group_a/group_b carry the non-default
    // fingerprint keys (backend always included); mixed_keys lists where the sides differ — when
    // empty, no banner renders (absence = clean). The DI guard twin (plan §3.9; the CLI's own
    // refusal lives at cli.py:1065-1068): a side whose DI is not balloon-verified prints the
    // estimate note instead of implying a real balloon DI. Older responses without C-2/G-2 keys
    // simply render no group rows.
    const gA = (cmp.group_a && typeof cmp.group_a === "object") ? cmp.group_a : null;
    const gB = (cmp.group_b && typeof cmp.group_b === "object") ? cmp.group_b : null;
    const mixed = Array.isArray(cmp.mixed_keys) ? cmp.mixed_keys : [];
    const sideBadgeRow = (label, grp, prefix) => grp
      ? `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="font-family:var(--f-mono);font-size:0.78rem;color:var(--muted);min-width:1.2rem">${esc(label)}</span><span class="pill-row">${renderProvenanceBadges(grp, prefix)}</span></div>`
      : "";
    const badgeRows = (gA || gB)
      ? [sideBadgeRow("A", gA, "group_a."), sideBadgeRow("B", gB, "group_b.")].filter(Boolean).join("")
      : "";
    const mixedBanner = mixed.length
      ? `<div class="alert warn" role="alert"><b>These runs differ in: ${mixed.map(k => `<code class="mono">${esc(k)}</code>`).join(", ")}.</b> The J values below are shown as-is, but ranking one run over the other is not comparable when the solve groups differ.</div>`
      : "";
    const dsA = dA.di_source, dsB = dB.di_source;
    const diNote = (dsA === "cuts_estimate" || dsB === "cuts_estimate")
      ? `<p class="hint" role="note" style="margin:0"><span class="warn-text">DI: cuts estimate — not comparable</span></p>`
      : (dsA !== "balloon" || dsB !== "balloon")
        ? `<p class="hint" role="note" style="margin:0"><span class="warn-text">DI source unknown on at least one side — not comparable</span></p>`
        : "";
    const provBlock = [badgeRows, mixedBanner, mountingRankWarnHtml(mixed), diNote].filter(Boolean).join("");

    res.innerHTML = `
      <div class="stack" style="gap:20px">
        ${provBlock ? `<div class="stack" style="gap:8px" id="compare-provenance">${provBlock}</div>` : ""}
        <h3>Metric comparison</h3>
        <p class="muted" style="font-size:0.83rem">Per-frequency |A − B| on the shared grid.</p>
        ${metricTable}
        <div class="grid2">
          <div class="fig"><h3>${tip("bw", "Beamwidth")} H</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-bwh"></svg></div>
          <div class="fig"><h3>${tip("bw", "Beamwidth")} V</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-bwv"></svg></div>
          <div class="fig"><h3>${tip("di_db", "DI")}</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-di"></svg></div>
          <div class="fig"><h3>${tip("on_axis", "On-axis")}</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-axis"></svg></div>
        </div>
      </div>`;

    if (!F.length) return;

    function cmpChart(svgId, keyA, keyB, ylabel) {
      const svg = document.getElementById(svgId);
      if (!svg) return;
      const allV = [...(dA[keyA] || []), ...(dB[keyB] || [])].filter(v => v != null);
      if (!allV.length) return;
      const lo = Math.floor(Math.min(...allV) - 1), hi = Math.ceil(Math.max(...allV) + 1);
      chart(svg, {
        xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [lo, hi],
        xticks: FT, yticks: niceTicks(lo, hi, 5), xlabel: "Hz", ylabel, band,
        series: [
          { pts: F.map((f, i) => [f, (dA[keyA] || [])[i] ?? null]), color: css("--seed"), w: 1.8 },
          { pts: F.map((f, i) => [f, (dB[keyB] || [])[i] ?? null]), color: css("--best"), w: 1.8 },
        ],
      });
    }
    cmpChart("cmp-bwh", "bw_h", "bw_h", "°");
    cmpChart("cmp-bwv", "bw_v", "bw_v", "°");
    cmpChart("cmp-di", "di", "di", "dB");
    cmpChart("cmp-axis", "on_axis", "on_axis", "dB");
  }

  document.getElementById("btn-compare").onclick = doCompare;
  if (preA && preB) doCompare();
}

// ── View 5: Briefs ─────────────────────────────────────────────────

// Catalog group labels, shared by the Briefs picker, the Compose wizard (step 1) and the
// Launch family picker so the same group is always capioned the same way.
const CATALOG_GROUP_LABEL = { classical: "Classical horns", hybrid: "Hybrids", organic: "Organic horns",
                              magnus: "Magnus mesher families", legacy: "Utility / legacy" };

/** "…/briefs/axi_90x90_1in.yaml" -> "axi_90x90_1in" (configs spell brief_file relative to their
 *  own directory, e.g. "../briefs/axi_90x90_1in.yaml", so matching goes by the file stem). */
function briefFileStem(f) {
  return String(f || "").replace(/\\/g, "/").split("/").pop().replace(/\.(yaml|yml)$/, "");
}

/** The /api/briefs entry a config's brief_file points at (stem match first, path fallback). */
function findBriefByFile(briefs, briefFile) {
  const stem = briefFileStem(briefFile);
  return briefs.find(x => x.name === stem) ||
         briefs.find(x => x.path === String(briefFile || "").replace(/\\/g, "/")) || null;
}

// Starting values for a brand-new brief. They mirror the shipped brief
// examples/briefs/axi_90x90_1in.yaml (coverage angles, scoring weights, 1-inch driver) with a
// wider-than-tall envelope; everything else is the schema default in config.py::load_brief.
const NEW_BRIEF_DEFAULTS = {
  target: { coverage_h_deg: 90, coverage_v_deg: 90, band_lo_hz: 500, band_hi_hz: 5500,
            di_target_db: null, di_slope_target: 0, z_min: 0 },
  weights: { cov: 1.0, rip: 1.0, di: 0.3, dislope: 0.5, flat: 0.5, load: 0.5 },
  envelope: { max_mouth_w_mm: 500, max_mouth_h_mm: 400, max_depth_mm: 250 },
  driver: { exit_radius_mm: 12.7, exit_angle_deg: 0, throat_angle_policy: "free" },
  symmetry: "hv", objective_version: 1, verify_only: false,
};

function newBriefDraft() {
  return { name: "", kind: "new", path: "", brief: {
    name: "", description: "",
    driver: { ...NEW_BRIEF_DEFAULTS.driver },
    envelope: { ...NEW_BRIEF_DEFAULTS.envelope },
    symmetry: NEW_BRIEF_DEFAULTS.symmetry,
    source: {},
    target: { ...NEW_BRIEF_DEFAULTS.target },
    weights: { ...NEW_BRIEF_DEFAULTS.weights },
    verify_only: NEW_BRIEF_DEFAULTS.verify_only,
    objective: { version: NEW_BRIEF_DEFAULTS.objective_version },
  } };
}

async function viewBriefs() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let briefs, configs = [];
  try {
    [briefs, configs] = await Promise.all([
      api("/api/briefs"),
      api("/api/configs").catch(() => []),   // the typology picker; its absence must not kill the page
    ]);
  } catch (e) { ROOT.innerHTML = errBanner(e.message); return; }

  if (!briefs.length) {
    ROOT.innerHTML = `<div class="stack" style="gap:20px">
      <div><div class="eyebrow">Briefs &amp; families</div><h2>Briefs</h2></div>
      <p class="muted">No briefs found.</p>
    </div>`;
    return;
  }

  // Typology picker options: grouped by catalog group, captioned with the family, disabled
  // entries kept visible (marker + disabled attribute) so their existence is never hidden.
  const byGroup = {};
  for (const c of configs) (byGroup[c.group || "Other"] = byGroup[c.group || "Other"] || []).push(c);
  let pickOpts = `<option value="">— pick a typology's brief —</option>`;
  for (const [grp, list] of Object.entries(byGroup)) {
    pickOpts += `<optgroup label="${esc(CATALOG_GROUP_LABEL[grp] || grp)}">`;
    for (const c of list) {
      const desc = c.description ? ` — ${c.description.slice(0, 60)}` : "";
      pickOpts += `<option value="${esc(c.path)}" ${c.disabled ? "disabled" : ""}>${esc(c.catalog_name || c.name)} · ${esc(c.family || "—")}${esc(desc)}${c.disabled ? " (disabled)" : ""}</option>`;
    }
    pickOpts += `</optgroup>`;
  }

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Briefs &amp; families</div>
        <h2>Briefs</h2>
        <p class="muted" style="font-size:0.85rem">Select a brief to view or edit its parameters. Save a modified copy under a new name, start a new brief from scratch, or start from a typology's brief.</p>
      </div>
      <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px" role="toolbar" aria-label="Brief authoring">
        <button id="btn-new-brief" title="Open the editor with schema-safe defaults">New brief</button>
        <label for="typo-pick" class="form-label" style="font-family:var(--f-mono);font-size:0.8rem;color:var(--muted)">Start from typology</label>
        <select id="typo-pick" style="font:inherit;font-size:0.88rem;background:var(--bg);color:var(--ink);border:1px solid var(--rule);border-radius:5px;padding:6px 10px;min-width:260px;max-width:100%">${pickOpts}</select>
        <span id="typo-pick-msg" class="hint" role="status"></span>
      </div>
      ${configs.length ? "" : `<p class="hint">Typology list unavailable — New brief still works.</p>`}
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px" id="briefs-list"></div>
      <div id="brief-detail"></div>
    </div>`;

  const listEl = document.getElementById("briefs-list");
  briefs.forEach(b => {
    const btn = document.createElement("button");
    btn.className = "card";
    btn.style.cssText = "text-align:left;cursor:pointer;";
    btn.innerHTML = `<div style="font-weight:500">${esc(b.name)}</div>
      <div class="muted mono" style="font-size:0.75rem">${esc(b.kind)}</div>`;
    btn.onclick = () => showBriefDetail(b, briefs);
    listEl.appendChild(btn);
  });

  document.getElementById("btn-new-brief").onclick = async () => {
    await showBriefDetail(newBriefDraft(), briefs, { mode: "new", scroll: true });
  };

  const pickSel = document.getElementById("typo-pick");
  const pickMsg = document.getElementById("typo-pick-msg");
  pickSel.onchange = async e => {
    pickMsg.textContent = "";
    const c = configs.find(c => c.path === e.target.value);
    if (!c) return;
    if (!c.brief_file) {
      pickMsg.textContent = `${c.catalog_name || c.name} has no brief_file configured — use New brief instead.`;
      e.target.value = "";
      return;
    }
    const br = findBriefByFile(briefs, c.brief_file);
    if (!br) {
      pickMsg.textContent = `Brief file ${c.brief_file} was not found among the briefs on this page.`;
      e.target.value = "";
      return;
    }
    await showBriefDetail(br, briefs, { mode: "typology", origin: c, scroll: true });
  };

  if (briefs.length) showBriefDetail(briefs[0], briefs);
}

async function showBriefDetail(b, allBriefs, opts = {}) {
  const isNew = opts.mode === "new";
  // Briefs page mounts into #brief-detail; the Compose wizard reuses this exact form via opts.mount.
  const det = opts.mount ? document.getElementById(opts.mount) : document.getElementById("brief-detail");
  if (!det) return;
  det.innerHTML = `<p class="muted">Loading…</p>`;
  const br = b.brief || {};
  const tgt = br.target || {};
  const wt = br.weights || {};
  const env = br.envelope || {};
  const drv = br.driver || {};

  // 5500 Hz is the search ceiling on the 8 GB RTX 4060 (mesh dof cap, TOOLCHAIN.md) — a practical
  // hardware note, NOT a schema rule: the schema accepts any band_hi above band_lo, and the
  // verify-only *_12k briefs run at 12000. Values are saved as typed, never clamped.
  const bandHiOver = (tgt.band_hi_hz || 0) > 5500;
  const bandHiWarn = bandHiOver
    ? `<span class="warn-text">⚠ band_hi above 5500 Hz — beyond the 8 GB GPU dof cap: verify-only territory (like the *_12k briefs), not search</span>` : "";

  const pol = drv.throat_angle_policy;                    // "pin" | "free" | absent
  const objVer = (br.objective || {}).version ?? 1;
  // band_hz must be an array of rows; a hand-edited brief may carry anything (list_briefs does no
  // validation) — a non-array is disclosed, never allowed to break the form mid-render.
  const fwRaw = (tgt.freq_weights || {}).band_hz;
  const fwRows = Array.isArray(fwRaw) ? fwRaw.filter(r => Array.isArray(r) && r.length >= 1).map(r => r.map(v => v == null ? "" : String(v))) : [];
  const fwBadNote = !Array.isArray(fwRaw) ? `<div class="hint" style="margin-bottom:6px"><span class="warn-text">⚠ this brief's target.freq_weights.band_hz is not a list of rows — not editable here (fix the YAML)</span></div>` : "";

  const headTitle = isNew ? "New brief" : esc(b.name);
  const kindLabel = isNew ? "new (unsaved)" : b.kind;
  const provenance = (opts.mode === "typology" && opts.origin)
    ? `<p class="hint" style="font-size:0.8rem;margin:4px 0 0" role="note">Starting point loaded: <b>${esc(opts.origin.catalog_name || opts.origin.name)}</b> names this brief as its brief_file — catalog group ${esc(opts.origin.group || "—")}, family ${esc(opts.origin.family || "—")}. The typology itself is unchanged; saving below writes your own copy.</p>`
    : "";

  const INPUT_CSS = "font:inherit;font-size:0.88rem;background:var(--bg);color:var(--ink);border:1px solid var(--rule);border-radius:5px;padding:6px 10px;max-width:100%";

  det.innerHTML = `
    <div class="stack" style="gap:20px">
      <hr class="sep">
      <div>
        <h3>${headTitle} <span class="pill" style="font-size:0.7rem;border-color:var(--muted);color:var(--muted)">${esc(kindLabel)}</span></h3>
        ${isNew ? "" : `<p class="muted" style="font-size:0.85rem">${esc(br.description || "")}</p>`}
        ${isNew ? "" : `<p class="muted mono" style="font-size:0.75rem">${esc(b.path || "")}</p>`}
        ${provenance}
      </div>
      <form id="brief-form" class="stack" style="gap:20px">

        <fieldset>
          <legend>Identity &amp; symmetry</legend>
          <div class="form-grid">
            <label for="brf-desc">Description</label>
            <div><input id="brf-desc" type="text" value="${esc(br.description || "")}" placeholder="what this brief is for"
              style="${INPUT_CSS};width:min(420px,100%)">
              <div class="hint">Stored in the brief YAML (free text, may be empty)</div></div>
            <label for="brf-sym">Symmetry</label>
            <div><select id="brf-sym" style="${INPUT_CSS};width:220px">
                <option value="hv" ${br.symmetry !== "axisymmetric" ? "selected" : ""}>hv — H and V may differ</option>
                <option value="axisymmetric" ${br.symmetry === "axisymmetric" ? "selected" : ""}>axisymmetric — body of revolution</option>
              </select>
              <div class="hint">The server refuses axisymmetric briefs with unequal coverage: "an axisymmetric brief needs coverage_h_deg == coverage_v_deg"</div></div>
            <label for="brf-verify-only">verify_only</label>
            <div><input id="brf-verify-only" type="checkbox" ${br.verify_only ? "checked" : ""}>
              <div class="hint">verify_only briefs are refused by search/run/campaign — only <code>verify --brief</code> uses them (the 12 kHz briefs work this way)</div></div>
            <label for="brf-obj">Objective version</label>
            <div><select id="brf-obj" style="${INPUT_CSS};width:220px">
                ${objectiveVersionOptionsHtml(objVer)}
              </select>
              <div class="hint">Version 1 ships everywhere; 2 is the opt-in update; 3 additionally masks everything below the brief's scoring floor f0 (target.f0_hz)</div></div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Target</legend>
          <div class="form-grid">
            <label for="brf-cov-h">${tip("bw", "Coverage H")} °</label>
            <div><input id="brf-cov-h" type="number" step="1" min="5" max="180" value="${tgt.coverage_h_deg ?? 90}">
              <div class="hint">Horizontal −6 dB coverage angle in degrees (5–180)</div></div>
            <label for="brf-cov-v">${tip("bw", "Coverage V")} °</label>
            <div><input id="brf-cov-v" type="number" step="1" min="5" max="180" value="${tgt.coverage_v_deg ?? 90}">
              <div class="hint">Vertical −6 dB coverage angle in degrees</div></div>
            <label for="brf-blo">${tip("band", "Band low")} Hz</label>
            <div><input id="brf-blo" type="number" step="10" min="100" value="${tgt.band_lo_hz ?? 700}">
              <div class="hint">Lowest scored frequency</div></div>
            <label for="brf-bhi">${tip("band", "Band high")} Hz</label>
            <div>
              <input id="brf-bhi" type="number" step="100" value="${tgt.band_hi_hz ?? 5500}">
              <div class="hint" id="bhi-warn">${bandHiWarn || "5500 Hz is the practical search ceiling on the 8 GB RTX 4060; higher values are saved as typed and belong to verify-only passes"}</div>
            </div>
            <label for="brf-di">${tip("di_db", "DI target")} dB</label>
            <div><input id="brf-di" type="number" step="0.1" value="${tgt.di_target_db ?? ""}" placeholder="auto from coverage">
              <div class="hint">Leave blank to derive from coverage angles</div></div>
            <label for="brf-dislope">${tip("dislope", "DI slope target")}</label>
            <div><input id="brf-dislope" type="number" step="0.01" value="${tgt.di_slope_target ?? 0}">
              <div class="hint">0 = constant directivity</div></div>
            <label for="brf-zmin">${tip("load", "Loading threshold")} z_min</label>
            <div><input id="brf-zmin" type="number" step="0.05" min="0" max="1" value="${tgt.z_min ?? 0}">
              <div class="hint">Lowest scored frequency loading threshold — the throat-impedance floor the load term scores below (classical briefs use 0.7, default 0)</div></div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Weights <span class="muted" style="font-size:0.72rem;font-weight:400;text-transform:none;letter-spacing:0">(relative importance — 0 turns a term off)</span></legend>
          <div class="form-grid">
            ${TERM_ORDER.map(k => `<label for="brf-w-${k}">${tip(k)}</label>
              <div><input id="brf-w-${k}" type="number" step="0.1" min="0" value="${wt[k] ?? DEFW[k]}">
                <div class="hint" style="font-size:0.72rem">${GLOSSARY[k]?.short || ""}</div></div>`).join("")}
          </div>
        </fieldset>

        <fieldset>
          <legend>Size envelope</legend>
          <div class="form-grid">
            <label for="brf-mw">Max mouth width mm</label>
            <input id="brf-mw" type="number" step="1" value="${env.max_mouth_w_mm ?? 360}">
            <label for="brf-mh">Max mouth height mm</label>
            <input id="brf-mh" type="number" step="1" value="${env.max_mouth_h_mm ?? 360}">
            <label for="brf-md">Max depth mm</label>
            <input id="brf-md" type="number" step="1" value="${env.max_depth_mm ?? 220}">
            <span class="form-label" style="color:var(--muted)">Note</span>
            <div class="hint">Width and height are independent — a wider-than-tall mouth is legal for every symmetry value</div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Driver</legend>
          <div class="form-grid">
            <label for="brf-er">Exit radius mm</label>
            <div><input id="brf-er" type="number" step="0.1" value="${drv.exit_radius_mm ?? 12.7}">
              <div class="hint">Radius of the driver's throat exit</div></div>
            <label for="brf-ea">Exit angle °</label>
            <div><input id="brf-ea" type="number" step="0.1" value="${drv.exit_angle_deg ?? 5.0}">
              <div class="hint">Half-angle of the exit cone</div></div>
            <label for="brf-pol">Throat angle policy</label>
            <div><select id="brf-pol" style="${INPUT_CSS};width:340px;max-width:100%">
                <option value="" ${pol == null ? "selected" : ""}>— not set (each family keeps its own throat behaviour) —</option>
                <option value="free" ${pol === "free" ? "selected" : ""}>free — throat angle stays searchable</option>
                <option value="pin" ${pol === "pin" ? "selected" : ""}>pin — throat angle pinned to the driver exit angle</option>
              </select>
              <div class="hint">pin exists so every family competes on the same throat; absent key = exactly the pre-pin behaviour</div></div>
          </div>
        </fieldset>

        <details id="brf-advanced" style="border:1px solid var(--rule);border-radius:6px;padding:10px 14px">
          <summary style="cursor:pointer;font-family:var(--f-mono);font-size:0.78rem;color:var(--accent)">Advanced — frequency weights${br.grid ? " · grid carried through" : ""}</summary>
          <div class="stack" style="gap:8px;margin-top:10px">
            <div>
              ${fwBadNote}
              <div class="hint" style="margin-bottom:6px"><code>target.freq_weights</code> — one row per frequency slice: lo_hz, hi_hz, weight. A frequency gets the product of every slice containing it; empty means no weighting. Checked here (non-negative numbers, lo &lt; hi), then re-validated by the server on save.</div>
              <div id="brf-fw-rows" class="stack" style="gap:6px"></div>
              <button type="button" id="brf-fw-add" style="margin-top:8px">+ Add frequency-weight row</button>
              <div id="brf-fw-msg" style="margin-top:6px"></div>
            </div>
            ${br.grid ? `<div class="hint">grid: verify_points_per_octave ${esc(String(br.grid.verify_points_per_octave ?? "—"))} — carried through unchanged (edit the YAML for another value)</div>` : ""}
            <div class="hint">source: cap ${esc(String((br.source || {}).cap ?? "auto"))} — carried through unchanged</div>
          </div>
        </details>

        <div>
          <div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
            <input id="brf-save-name" type="text" placeholder="new-brief-name"
              pattern="[A-Za-z0-9_-]{1,64}" title="Letters, digits, _ and - only (max 64)"
              aria-label="save as name"
              style="${INPUT_CSS};width:180px">
            <button type="button" id="btn-save-brief" class="primary">Save as new brief</button>
          </div>
          <div class="hint">Name: letters, digits, _ and - only (max 64 characters)</div>
          <div id="brief-save-msg" style="margin-top:8px"></div>
        </div>

        ${isNew ? `<p class="hint" style="margin:0" role="note">Starting values follow the shipped brief <code>examples/briefs/axi_90x90_1in.yaml</code> (coverage angles, scoring weights, band top 5500); the 500 × 400 × 250 mm envelope is wider than tall like your own briefs and band low 500 Hz is the compose default; every other field is the schema default. All of it is editable.</p>` : ""}

      </form>

      ${(isNew || opts.hideFamilies) ? "" : `
      <div>
        <h4 style="margin-bottom:8px">Families compatible with this brief</h4>
        <button id="btn-families">Show compatible families</button>
        <pre class="families-out" id="families-out" style="display:none"></pre>
      </div>`}
    </div>`;

  // Frequency-weight rows (target.freq_weights). Collapsed by default; values persist as typed.
  const fwBox = document.getElementById("brf-fw-rows");
  function addFwRow(r = ["", "", ""]) {
    const div = document.createElement("div");
    div.className = "fw-row";
    div.style.cssText = "display:flex;gap:8px;align-items:center;flex-wrap:wrap";
    div.innerHTML = `
      <input type="number" class="fw-lo" min="0" step="1" aria-label="freq weight lo_hz" placeholder="lo_hz" style="${INPUT_CSS};width:104px" value="${esc(r[0] ?? "")}">
      <span class="muted" aria-hidden="true">–</span>
      <input type="number" class="fw-hi" min="0" step="1" aria-label="freq weight hi_hz" placeholder="hi_hz" style="${INPUT_CSS};width:104px" value="${esc(r[1] ?? "")}">
      <span class="muted" aria-hidden="true">×</span>
      <input type="number" class="fw-w" min="0" step="0.1" aria-label="freq weight weight" placeholder="weight" style="${INPUT_CSS};width:84px" value="${esc(r[2] ?? "")}">
      <button type="button" class="fw-del" aria-label="Remove this frequency-weight row" title="Remove this row">✕</button>`;
    div.querySelector(".fw-del").onclick = () => div.remove();
    fwBox.appendChild(div);
  }
  fwRows.forEach(r => addFwRow(r));
  document.getElementById("brf-fw-add").onclick = () => addFwRow();

  // Band-hi note (honest, no clamp): the value is saved exactly as typed.
  document.getElementById("brf-bhi").addEventListener("input", e => {
    const v = +e.target.value;
    const warnEl = document.getElementById("bhi-warn");
    if (v > 5500) {
      warnEl.innerHTML = `<span class="warn-text">⚠ band_hi above 5500 Hz — beyond the 8 GB GPU dof cap (verify-only territory); saved as typed, no clamp</span>`;
    } else {
      warnEl.textContent = "5500 Hz is the practical search ceiling on the 8 GB RTX 4060; higher values are saved as typed and belong to verify-only passes";
    }
  });

  // Save brief
  document.getElementById("btn-save-brief").onclick = async () => {
    const name = document.getElementById("brf-save-name").value.trim();
    const msg = document.getElementById("brief-save-msg");
    if (!name) { msg.innerHTML = `<div class="alert warn">Enter a brief name.</div>`; return; }
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(name)) {
      msg.innerHTML = `<div class="alert error">Name must be letters, digits, _ and - only (max 64).</div>`; return;
    }
    // Frequency-weight rows: numbers, non-negative, lo < hi — client-side only; the server
    // (config.load_brief) re-validates for real and its error is shown verbatim below.
    const fw = [];
    let fwErr = "";
    for (const row of document.querySelectorAll("#brf-fw-rows .fw-row")) {
      const lo = row.querySelector(".fw-lo").value.trim(),
            hi = row.querySelector(".fw-hi").value.trim(),
            w  = row.querySelector(".fw-w").value.trim();
      if (lo === "" && hi === "" && w === "") continue;
      const L = +lo, H = +hi, W = +w;
      if (lo === "" || hi === "" || w === "" || !Number.isFinite(L) || !Number.isFinite(H) || !Number.isFinite(W))
        fwErr = "Every frequency-weight row needs numbers for lo_hz, hi_hz and weight.";
      else if (L < 0 || H < 0 || W < 0)
        fwErr = "Frequency-weight rows must be non-negative.";
      else if (L >= H)
        fwErr = "lo_hz must be below hi_hz in every frequency-weight row.";
      else fw.push([L, H, W]);
    }
    const fwMsg = document.getElementById("brf-fw-msg");
    if (fwErr) {
      fwMsg.innerHTML = `<span class="warn-text">⚠ ${esc(fwErr)}</span>`;
      msg.innerHTML = `<div class="alert warn">Fix the advanced frequency-weight rows before saving.</div>`;
      document.getElementById("brf-advanced").open = true;
      return;
    }
    fwMsg.textContent = "";
    const newBrief = {
      name,
      description: document.getElementById("brf-desc").value.trim(),
      driver: { exit_radius_mm: +document.getElementById("brf-er").value,
                exit_angle_deg: +document.getElementById("brf-ea").value,
                throat_angle_policy: document.getElementById("brf-pol").value || null },
      envelope: { max_mouth_w_mm: +document.getElementById("brf-mw").value,
                  max_mouth_h_mm: +document.getElementById("brf-mh").value,
                  max_depth_mm: +document.getElementById("brf-md").value },
      symmetry: document.getElementById("brf-sym").value,
      source: br.source || {},
      target: {
        coverage_h_deg: +document.getElementById("brf-cov-h").value,
        coverage_v_deg: +document.getElementById("brf-cov-v").value,
        band_lo_hz: +document.getElementById("brf-blo").value,
        band_hi_hz: +document.getElementById("brf-bhi").value,     // no clamp: the server validates for real
        di_target_db: document.getElementById("brf-di").value === "" ? null : +document.getElementById("brf-di").value,
        di_slope_target: +document.getElementById("brf-dislope").value,
        z_min: +document.getElementById("brf-zmin").value,
        ...(fw.length ? { freq_weights: { band_hz: fw } } : {}),   // absent = no weighting (schema default)
      },
      weights: Object.fromEntries(TERM_ORDER.map(k => [k, +document.getElementById(`brf-w-${k}`).value])),
      verify_only: document.getElementById("brf-verify-only").checked,
      objective: { version: +document.getElementById("brf-obj").value },
      ...(br.grid ? { grid: br.grid } : {}),                       // carried through, never silently dropped
    };
    const r = await post("/api/brief", { name, brief: newBrief });
    if (r.error) msg.innerHTML = `<div class="alert error">${esc(r.error)}</div>`;
    else {
      msg.innerHTML = `<div class="alert info">Saved to ${esc(r.path || name)}</div>`;
      if (opts.onSaved) opts.onSaved(r.path || "", name);   // Compose wizard holds the saved path
    }
  };

  if (!isNew && !opts.hideFamilies) {
    // Show families
    document.getElementById("btn-families").onclick = async () => {
      const pre = document.getElementById("families-out");
      pre.style.display = "block";
      pre.textContent = "Loading…";
      try {
        const r = await api("/api/families?brief=" + encodeURIComponent(b.name));
        pre.textContent = r.text || "(no output)";
      } catch (e) { pre.textContent = "Error: " + e.message; }
    };
  }

  if (opts.scroll) det.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── View 5b: Compose — typology-first run builder ──────────────────
// Owner UX direction (2026-10-25): pick the shapes first, then the brief constraints, then the
// run shape. The wizard never builds the argv itself — POST /api/preview returns the exact
// command jobs.py would run and POST /api/jobs launches it (both allow-listed server-side).

const COMPOSE_KIND_HINTS = {
  "dry-run": "Meshes the starting design only — no solve, no GPU. The cheap check that the brief + typology combo loads.",
  "run": "One GPU solve of the starting design — minutes.",
  "search": "CMA-ES optimization on the GPU — needs the GPU free. Blank budget = the engine default of 60 evaluations.",
};

const COMPOSE_TIER_HINTS = {
  "dry-run": "Meshes each picked family's starting design only — no solve, no GPU. Seconds.",
  "screen": "One search per family — budget max(40, 10×searchable knobs), 1 seed. Minutes.",
  "compare": "Two seeds per family — budget max(150, 25×searchable knobs). Needed to claim one family beats another. Hours.",
};

const EDITOR_SELECT_CSS = "font:inherit;font-size:0.88rem;background:var(--bg);color:var(--ink);border:1px solid var(--rule);border-radius:5px;padding:6px 10px;max-width:100%;min-width:280px";

// ── Compose hybrid disclosure + seed preview (owner ask 2026-10-25, display-only) ─────────────
// The additive /api/configs keys (gui/data.py list_configs, verbatim yaml passthroughs) are
//   generator_block — the config's real generator dict/list (absent when the config has none)
//   seed_params     — the config's seed geometry dict (absent when empty)
// Both are read defensively in the view and rendered DISPLAY-ONLY: the compose POST body keeps
// exactly the field set jobs.build_argv reads (config/brief/budget/cma_seed for single runs,
// brief/families/tier for campaigns) — the pairing pinned by
// tests/test_gui_brief_authoring.py::test_campaign_budget_and_seeds_are_not_gui_plumbed.
// Pure helpers, exported for offline node tests (same precedent as renderProvenanceBadges).

// Composite generator families, detected from the block's OWN generator name key — never from
// config names, catalog titles or descriptions.
const COMPOSITE_GENERATOR_NAMES = ["splice", "blend", "throat_blend", "hybrid"];

/** The distinct contributing generators a composite generator block names (["osse", "tractrix"],
 *  ["grid rows (lecleach)"]), or [] when the block is absent / an unexpected shape / one same-type
 *  profile. Reads SHAPES only; nothing derivable means nothing is captioned. Order of the
 *  contributors follows the block's own section order (H before V, base before blend). */
function hybridContributors(gb) {
  const isObj = x => !!x && typeof x === "object" && !Array.isArray(x);
  const typeOf = s => isObj(s) && typeof s.type === "string" ? s.type : "";
  if (!isObj(gb) && !Array.isArray(gb)) return "";                    // absent / unexpected shape: caption nothing

  const out = [];
  const push = t => { if (t && !out.includes(t)) out.push(t); };      // distinct + order-stable

  if (Array.isArray(gb)) {                     // generator given as a list: each entry is a section
    gb.forEach(e => { if (isObj(e)) push(typeof e.name === "string" ? e.name : typeOf(e)); });
    if (out.length >= 2 ||
        (out.length === 1 && COMPOSITE_GENERATOR_NAMES.includes(out[0])))
      return out;
    return [];                                 // one nondescript section: not a mix
  }

  const gname = typeof gb.name === "string" ? gb.name : "";
  const h = isObj(gb.profile_h) ? gb.profile_h : null;
  const v = isObj(gb.profile_v) ? gb.profile_v : null;
  const hType = typeOf(h), vType = typeOf(v);

  // grid rows block: the row definitions ARE the contributors
  if (gb.rows != null) {
    const parts = [];
    if (Array.isArray(gb.rows))
      gb.rows.forEach(r => { if (isObj(r)) { const t = typeof r.name === "string" ? r.name : typeOf(r); if (t && !parts.includes(t)) parts.push(t); } });
    else if (isObj(gb.rows) && typeof gb.rows.type === "string") parts.push(gb.rows.type);
    push(parts.length ? `grid rows (${parts.join(" + ")})` : "grid rows");
  }
  // splice profile: the spliced parents are named under first/second
  const sp = (hType === "splice" && h) || (vType === "splice" && v) || null;
  if (sp) {
    push(typeOf(sp.first)); push(typeOf(sp.second));
    if (!out.length) push("splice");               // splice named without parents: the profile itself
  }
  // blend section beside a profile: base profile + blend profile name the two mixed generators
  const blend = (isObj(gb.blend_h) ? gb.blend_h : null) || (isObj(gb.blend_v) ? gb.blend_v : null) || null;
  if (blend) {
    push(hType); push(typeOf(blend));
    if (!out.length) push(gname);                  // blend without a typed base: the name says it
  }
  // per-plane hybrid: two DIFFERENT profile laws; same-type planes are one construction, not a mix
  if (hType && vType && hType !== vType) { push(hType); push(vType); }

  // composite-family name with no other derivable contributor: prefer the profile it does name,
  // fall back to the family name itself — never caption nothing silently for a named composite
  if (!out.length && COMPOSITE_GENERATOR_NAMES.includes(gname)) push(hType || vType || gname);
  return out;
}

/** The step-1 row caption for a config whose generator block is a composite, or "" plainly
 *  (absent / unexpected block / single-profile construction keeps the row exactly as today). */
/**
 * The step-1 caption for one generator block, honest by construction: a real MIX
 * (splice parents / blend section / two different plane laws) captions "hybrid — A + B";
 * a single-construction rows kind captions "rows — {types}" (a rows kind is one
 * construction on shaped stations, not a hybrid of generators). Or [] when the block is
 * absent / an unexpected shape / one same-type construction — never invented wording. */
function hybridCaptionFromBlock(gb) {
  const c = hybridContributors(gb);
  if (!c.length) return "";
  if (typeof gb === "object" && gb && gb.rows != null) {
    // a grid rows kind is ONE construction on shaped stations, not a hybrid of generators —
    // caption it "rows — {types}"; strip the redundant "grid rows (...)" wrapper the
    // contributors push (the empty-rows case captions "rows — grid").
    const types = c.map(s => String(s).replace(/^grid rows(?: \((.+)\))?$/, "$1"))
      .filter(Boolean).join(" + ");
    return types ? `rows — ${types}` : "rows — grid";
  }
  return `hybrid — ${c.join(" + ")}`;
}

/** One seed-preview value: numbers through the house trim, scalars as text, nested values
 *  compacted to JSON — never "[object Object]". Pure. */
function seedPreviewValue(v) {
  if (typeof v === "number") return _trimNum(v);
  if (v == null || typeof v !== "object") return String(v);
  try { return JSON.stringify(v); } catch { return String(v); }
}

const SEED_PREVIEW_MAX_ROWS = 8;

/** The seed-preview knob rows for ONE config (pure; "" when the config carries no seed_params
 *  — the panel appears only when the config really has seed geometry). Caps the listing at
 *  SEED_PREVIEW_MAX_ROWS with a literal "+N more" honesty tail. */
function seedRowsHtml(config) {
  const cfg = (config && typeof config === "object" && !Array.isArray(config)) ? config : null;
  const sp = cfg ? cfg.seed_params : null;
  if (!sp || typeof sp !== "object" || Array.isArray(sp)) return "";
  const knobs = Object.keys(sp);
  if (!knobs.length) return "";
  // naming matches the panel heading (catalog_name wins); the raw key stays the visible cell
  // text, hover carries the catalog's label [unit], meaning and search range (P9).
  const nm = (typeof cfg.catalog_name === "string" && cfg.catalog_name) ||
             (typeof cfg.name === "string" ? cfg.name : "");
  return knobs.slice(0, SEED_PREVIEW_MAX_ROWS).map(k =>
    `<tr><td>${paramTipHtml(nm, k, k)}</td><td class="r">${esc(seedPreviewValue(sp[k]))}</td></tr>`
  ).join("") + (knobs.length > SEED_PREVIEW_MAX_ROWS
    ? `<tr><td colspan="2">+${knobs.length - SEED_PREVIEW_MAX_ROWS} more seed knobs — the config's own yaml carries them</td></tr>`
    : "");
}

/** The compose seed panel for ONE config (pure; "" when it carries no seed_params): knob/value
 *  table + the honest caption. Preview only — renders the config's own seed_params, alters no
 *  payload (see the display-only rule above). */
function seedPanelHtml(config) {
  const rows = seedRowsHtml(config);
  if (!rows) return "";
  const cfg = (config && typeof config === "object" && !Array.isArray(config)) ? config : {};
  const nm = (typeof cfg.catalog_name === "string" && cfg.catalog_name) ||
             (typeof cfg.name === "string" ? cfg.name : "");
  return `<div class="card" style="border:1px solid var(--rule);padding:8px 10px" role="note">
    <h4 style="margin:0 0 6px">Seed preview — ${esc(nm)}</h4>
    <table class="compact" aria-label="config seed geometry (preview only)"><thead><tr><th>seed knob</th><th class="r">value</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="hint" style="margin:6px 0 0">the seed the search starts from — bounds stay the config's own. Preview from the config's own seed_params — display-only, nothing here is sent.</p>
  </div>`;
}

export { hybridContributors, hybridCaptionFromBlock, seedPreviewValue, seedRowsHtml, seedPanelHtml };

async function viewCompose() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel("Loading typologies and briefs…");
  let briefs = [], configs = [], statusData = null, configsOk = true;
  try {
    statusData = await api("/api/status");
    briefs = await api("/api/briefs");
    configs = await api("/api/configs").catch(() => (configsOk = false, []));
  } catch (e) { ROOT.innerHTML = errBanner(e.message); return; }
  if (ROOT !== currentRoot()) return;
  await loadParamCatalog();       // P9: seed-preview knob hover docs; failure degrades to raw keys
  const gpuLock = (statusData && statusData.gpu_lock) || null;
  const gpuBusy = !!(gpuLock && gpuLock.alive);

  const S = {
    picks: new Set(),              // config paths
    briefMode: null,               // null | "new" | "typology" | "existing"
    briefPath: null,               // repo-relative brief path or null until saved/chosen
    briefLabel: "",
    runKind: "dry-run",            // single-config run type
    tier: "dry-run",               // campaign tier
    busyReason: null,              // server's gpu_busy string from the latest preview
  };

  const FAM_RE = /^[a-z0-9_]+(,[a-z0-9_]+)*$/;   // jobs.py FAMILIES (client pre-check only)
  const symLabel = c => c.symmetry === "axisymmetric" ? "axisymmetric" : "H/V";

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Compose</div>
        <h2>Compose a run</h2>
        <p class="muted" style="font-size:0.85rem">Shape first (which typologies), then the brief (the objective they are scored against), then the run. Every choice shows its exact command before anything executes — nothing is launched from here without a preview.</p>
      </div>

      <fieldset>
        <legend>1 · Shape — pick the typologies</legend>
        <div class="stack" style="gap:10px">
          <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px">
            <span id="cmp-shape-summary" class="hint" role="status">0 picked — pick at least one typology.</span>
            <span id="cmp-shape-note" class="hint" role="status"></span>
            <button type="button" id="cmp-clear" hidden>Clear picks</button>
          </div>
          ${configsOk ? `<div id="cmp-shapes" class="fam-picker"></div><div id="cmp-seed-panel" class="stack" style="gap:10px" aria-live="polite"></div>`
                      : `<p class="muted">Typology list unavailable — compose on the Briefs page or reuse an existing brief in step 2.</p>`}
        </div>
      </fieldset>

      <fieldset>
        <legend>2 · Brief — the objective the shape is scored against</legend>
        <div class="stack" style="gap:12px">
          <div class="btn-row" role="radiogroup" aria-label="brief source">
            <button type="button" class="job-type-btn" data-src="new" aria-pressed="false">New from scratch</button>
            <button type="button" class="job-type-btn" data-src="typology" aria-pressed="false">From a typology's brief</button>
            <button type="button" class="job-type-btn" data-src="existing" aria-pressed="false">Reuse an existing brief</button>
          </div>
          <div class="form-grid" id="cmp-brief-picker"></div>
          <div id="compose-editor"></div>
          <div id="cmp-brief-status" class="hint" role="status"></div>
          <div class="hint">The brief does not name the typology — the run binds them: a single run gets <code>--config &lt;path&gt; --brief &lt;path&gt;</code>; a campaign gets <code>--brief</code> and resolves the families you picked in step 1.</div>
        </div>
      </fieldset>

      <fieldset>
        <legend>3 · Run — what will actually execute</legend>
        <div class="stack" style="gap:12px">
          <div id="cmp-run-mode"></div>
          <div class="gpu-busy-note" id="cmp-busy" style="display:none" role="status"></div>
          <pre id="cmp-cmd" style="white-space:pre-wrap;word-break:break-all;font-size:0.82rem;background:var(--bg);border:1px solid var(--rule);border-radius:6px;padding:10px 12px;color:var(--ink)">— fill steps 1 and 2 to see the exact command</pre>
          <div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px">
            <button type="button" id="btn-cmp-launch" class="primary">Launch</button>
            <span id="cmp-launch-msg" class="hint" role="status"></span>
          </div>
          <div id="cmp-launch-error"></div>
        </div>
      </fieldset>
    </div>`;

  // ── Step 1: shape multi-select ─────────────────────────────────
  // Rules (stated, not hidden): disabled configs stay VISIBLE, marked and unselectable
  // (never pretend a capability does not exist). Uncatalogued configs (no catalog_name) are
  // selectable only as the SOLE pick — they launch as one --config run and cannot appear in a
  // campaign's --families (campaign resolves catalog names only); a second pick drops them with
  // the reason shown. Real family-vs-brief compatibility is NOT re-implemented here: the
  // campaign skips per-entry with the reason printed; the preview command is the truth.
  const shapesEl = document.getElementById("cmp-shapes");
  const shapeNote = document.getElementById("cmp-shape-note");

  function shapeNoteMsg(msg = "") {
    shapeNote.innerHTML = msg
      ? `<span class="warn-text">⚠ ${msg}</span>` : "";
  }

  function pickAllowed(c) {
    if (c.disabled) return false;                       // seed gate: never launchable
    if (!c.catalog_name) return S.picks.size === 0 || S.picks.has(c.path);
    return true;
  }

  function addPick(c, inputEl) {
    if (c.disabled) {
      if (inputEl) inputEl.checked = false;
      shapeNoteMsg(`${esc(c.name)} is disabled — the starting design does not materialize, so it cannot launch.`);
      return;
    }
    if (!pickAllowed(c)) {
      if (inputEl) inputEl.checked = false;
      shapeNoteMsg(`${esc(c.name)} is uncatalogued — campaign resolves catalog names only, so it launches alone: clear the other picks first.`);
      return;
    }
    if (!S.picks.has(c.path) && S.picks.size >= 1) {    // dropping a sole uncatalogued pick
      const sole = configs.find(x => x.path === [...S.picks][0]);
      if (sole && !sole.catalog_name) {
        S.picks.delete(sole.path);
        shapeNoteMsg(`${esc(sole.name)} deselected — campaign resolves catalog names only, so it cannot join the picks.`);
      }
    }
    S.picks.add(c.path);
  }

  function renderShapes() {
    const groups = {}, uncatalogued = [];
    for (const c of configs) {
      if (c.catalog_name) (groups[c.group || "Other"] = groups[c.group || "Other"] || []).push(c);
      else uncatalogued.push(c);
    }
    const row = c => {
      const stem = c.brief_file ? "brief: " + briefFileStem(c.brief_file) : "no brief_file";
      const off = c.disabled || (!c.catalog_name && S.picks.size >= 1 && !S.picks.has(c.path));
      const why = c.disabled ? "disabled — the starting design does not materialize (engine seed gate)"
                : off ? "campaign resolves catalog names only — pick this config alone (clear the other picks first)"
                : (c.description || "");
      // Composite disclosure: a caption ONLY when the additive generator_block really names a
      // mix (splice parents / blend section / per-plane laws / grid rows) — an absent or
      // unexpected block keeps the row byte-identical to before.
      const cap = hybridCaptionFromBlock(c.generator_block);
      return `<label class="fam-row ${off ? "off" : ""}" title="${esc(why)}">
        <input type="checkbox" value="${esc(c.path)}" ${off ? "disabled" : ""} ${S.picks.has(c.path) ? "checked" : ""}>
        <span class="fam-name">${esc(c.catalog_name || c.name)}${c.disabled ? ` <span class="pill bad" style="font-size:0.66rem">disabled</span>` : ""}</span>
        <span class="fam-meta">${esc(c.family || "—")} · ${symLabel(c)} · ${c.n_knobs} params${morphPill(c)}${cap ? `<br>${esc(cap)}` : ""}</span>
        <span class="fam-best">${esc(stem)}</span>
      </label>`;
    };
    let html = "";
    for (const [g, list] of Object.entries(groups)) {
      html += `<fieldset class="fam-group"><legend>${esc(CATALOG_GROUP_LABEL[g] || g)}
        <button type="button" class="linkish" data-all="${esc(g)}">select all in group</button></legend>
        ${list.map(row).join("")}</fieldset>`;
    }
    if (uncatalogued.length) {
      html += `<fieldset class="fam-group"><legend>Uncatalogued — single-config runs only</legend>
        <div class="hint" style="margin:0 0 6px 2px">No catalog entry: one <code>--config</code> dry-run/run/search, and a campaign cannot list them (--families resolves catalog names only). Selectable only when nothing else is picked.</div>
        ${uncatalogued.map(row).join("")}</fieldset>`;
    }
    shapesEl.innerHTML = html;

    shapesEl.querySelectorAll("[data-all]").forEach(b => b.onclick = () => {
      const grp = b.closest("fieldset");
      grp.querySelectorAll("input[type=checkbox]:not(:disabled)").forEach(cb => {
        const c = configs.find(x => x.path === cb.value);
        if (c) addPick(c, cb);
      });
      syncShapes(); refreshBriefAndRun();
    });

    shapesEl.onchange = e => {
      const input = e.target;
      if (input.type !== "checkbox") return;
      const c = configs.find(x => x.path === input.value);
      if (!c) return;
      if (input.checked) addPick(c, input);
      else S.picks.delete(c.path);
      syncShapes(); refreshBriefAndRun();
    };

    syncShapes();
  }

  function syncShapes() {
    shapesEl.querySelectorAll("input[type=checkbox]").forEach(cb => {
      const c = configs.find(x => x.path === cb.value);
      if (!c) return;
      const disallowed = !pickAllowed(c);
      cb.disabled = disallowed;
      cb.checked = S.picks.has(c.path);
      cb.closest(".fam-row")?.classList.toggle("off", disallowed || c.disabled);
    });
    document.getElementById("cmp-clear").hidden = S.picks.size === 0;
    document.getElementById("cmp-shape-summary").textContent = shapeSummary();
    // Seed preview: every picked config that carries seed_params gets one labelled panel —
    // each panel names its config, so a campaign's picks stay attributable. Display-only.
    const sp = document.getElementById("cmp-seed-panel");
    if (sp) sp.innerHTML = pickedConfigs().map(seedPanelHtml).filter(Boolean).join("");
  }

  function pickedConfigs() {
    return [...S.picks].map(p => configs.find(x => x.path === p)).filter(Boolean);
  }

  function familiesArg() {
    const names = pickedConfigs().filter(c => c.catalog_name).map(c => c.catalog_name);
    return [...new Set(names)].join(",");
  }

  function shapeSummary() {
    const n = S.picks.size;
    if (!n) return "0 picked — pick at least one typology.";
    if (n === 1) {
      const c = pickedConfigs()[0];
      return `1 picked · single-config run (${c.catalog_name || c.name}) — choose dry-run / run / search in step 3`;
    }
    const fams = familiesArg();
    return `${n} picked · campaign over ${fams ? fams.split(",").length : 0} catalog families — --families ${fams || "(none resolvable)"}`;
  }

  document.getElementById("cmp-clear").onclick = () => {
    S.picks.clear();
    shapeNoteMsg("");
    syncShapes(); refreshBriefAndRun();
  };

  function setLaunchMsg(html) {
    document.getElementById("cmp-launch-msg").innerHTML = html;
  }

  // ── Step 2: brief source ───────────────────────────────────────
  // (a) NEW from scratch — the schema-safe draft; (b) one typology's brief_file as the starting
  // point; (c) an existing brief used AS-IS (no copy needed). (a)/(b) only become launchable
  // after a save — a brief that was never saved has no path, and jobs.py resolves --brief to a
  // real file, so preview/launch honestly wait for the one-click save.
  const pickerEl = document.getElementById("cmp-brief-picker");
  const editorEl = document.getElementById("compose-editor");
  const statusEl = document.getElementById("cmp-brief-status");
  const srcBtns = [...document.querySelectorAll(".job-type-btn[data-src]")];
  srcBtns.forEach(btn => btn.onclick = () => setBriefSource(btn.dataset.src));

  async function setBriefSource(mode) {
    S.briefMode = mode;
    S.briefPath = null;
    S.briefLabel = "";
    srcBtns.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.src === mode)));
    if (mode === "typology") {
      const cands = configs.filter(c => c.brief_file && !c.disabled);
      pickerEl.innerHTML = cands.length ? `
        <label for="cmp-typo-brief">Typology</label>
        <select id="cmp-typo-brief" style="${EDITOR_SELECT_CSS}">
          <option value="">— pick a typology to load its brief_file —</option>
          ${cands.map(c => `<option value="${esc(c.path)}">${esc(c.catalog_name || c.name)} · ${esc(c.family || "—")} — brief_file ${esc(briefFileStem(c.brief_file))}</option>`).join("")}
        </select>
        <div class="hint">Loads the typology's own brief into the editor below as your starting point (provenance caption included); saving a copy under your name binds it to the run.</div>`
        : `<span class="form-label">Typology</span><div class="hint">No catalogued typology carries a brief_file.</div>`;
      document.getElementById("cmp-typo-brief")?.addEventListener("change", async e => {
        const c = configs.find(x => x.path === e.target.value);
        if (!c) return;
        const br = findBriefByFile(briefs, c.brief_file);
        if (!br) {
          editorEl.innerHTML = `<p class="hint">Brief file <code>${esc(c.brief_file)}</code> was not found among the briefs — it names no loadable brief.</p>`;
          return;
        }
        await showBriefDetail(br, briefs, { mode: "typology", origin: c, mount: "compose-editor",
                                            hideFamilies: true, onSaved: briefSaved });
      });
      editorEl.innerHTML = `<p class="muted">Pick a typology above — its brief loads here for editing.</p>`;
    } else if (mode === "existing") {
      pickerEl.innerHTML = `
        <label for="cmp-exist-brief">Existing brief</label>
        <select id="cmp-exist-brief" style="${EDITOR_SELECT_CSS}">
          <option value="">— pick a brief —</option>
          ${briefs.map(b => `<option value="${esc(b.path)}">${esc(b.name)} (${esc(b.kind)}) — ${esc(b.path)}${b.brief?.verify_only ? " · verify_only" : ""}</option>`).join("")}
        </select>
        <div class="hint">Used AS-IS for the run — campaigns don't require saving a copy. verify_only briefs are refused by run/campaign — only <code>verify --brief</code> uses them.</div>`;
      document.getElementById("cmp-exist-brief")?.addEventListener("change", e => {
        const br = briefs.find(x => x.path === e.target.value);
        if (!br) { S.briefPath = null; S.briefLabel = ""; editorEl.innerHTML = `<p class="muted">Pick a brief above.</p>`; }
        else {
          S.briefPath = br.path; S.briefLabel = br.name;
          editorEl.innerHTML = `<p class="hint">Using <code>${esc(br.path)}</code> as-is — no editor here. Copy and modify it on the <a href="#/briefs">Briefs page</a> if you want changes.</p>`;
        }
        refreshBriefStatus(); refreshRunMode(); updatePreview();
      });
      editorEl.innerHTML = `<p class="muted">Pick a brief above — it is used as-is, without editing.</p>`;
    } else {                                          // new from scratch
      pickerEl.innerHTML = "";
      await showBriefDetail(newBriefDraft(), briefs, { mode: "new", mount: "compose-editor",
                                                       hideFamilies: true, onSaved: briefSaved });
    }
    refreshBriefStatus(); refreshRunMode(); updatePreview();
  }

  function briefSaved(path, name) {
    S.briefPath = path;
    S.briefLabel = name;
    refreshBriefStatus(); refreshRunMode(); updatePreview();
  }

  function refreshBriefStatus() {
    if (!S.briefMode) { statusEl.textContent = "Pick a source above — the step-1 shapes are scored against the brief you settle on here."; return; }
    if (S.briefMode === "existing" && S.briefPath) {
      statusEl.innerHTML = `✓ using <code>${esc(S.briefPath)}</code> as-is — no copy needed.`;
    } else if (!S.briefPath) {
      statusEl.innerHTML = `<span class="warn-text">⚠ not saved yet — a run needs a real file path: set a name and press "Save as new brief" in the editor above.</span>`;
    } else {
      statusEl.innerHTML = `✓ saved to <code>${esc(S.briefPath)}</code> — the run uses this file as-is.`;
    }
  }

  // ── Step 3: run + launch ───────────────────────────────────────
  const busyEl = document.getElementById("cmp-busy");
  const cmdEl = document.getElementById("cmp-cmd");
  const errEl = document.getElementById("cmp-launch-error");
  const launchBtn = document.getElementById("btn-cmp-launch");

  function showBusy() {
    const reason = S.busyReason ||
      (gpuBusy ? `GPU busy: ${gpuLock.user || "?"} running ${gpuLock.command || "?"}` : null);
    busyEl.style.display = reason ? "" : "none";
    if (reason) busyEl.textContent = `⚠ ${reason} — GPU jobs are refused while a job runs; dry-run kinds stay available and the server re-checks on every launch.`;
  }

  function refreshBriefAndRun() {
    refreshBriefStatus(); refreshRunMode(); updatePreview();
  }

  function renderKindRow() {
    return `
      <div class="form-grid">
        <span class="form-label">Run</span>
        <div class="btn-row" role="radiogroup" aria-label="run type">
          ${["dry-run", "run", "search"].map(k =>
            `<button type="button" class="job-type-btn" data-kind="${k}" aria-pressed="${S.runKind === k}">${k}</button>`).join("")}
        </div>
        <span class="form-label">What it does</span>
        <div class="hint">${esc(COMPOSE_KIND_HINTS[S.runKind] || "")}</div>
        ${S.runKind === "search" ? `
          <label for="cmp-budget">Budget</label>
          <div><input id="cmp-budget" type="number" min="1" max="5000" placeholder="60" style="width:120px">
            <div class="hint" id="cmp-budget-hint">Suggested from Hansen ~100·N (blank = engine default 60)</div>
            <button type="button" class="linkish" id="cmp-budget-apply" style="display:none">Use suggested</button></div>
          <label for="cmp-seed">CMA seed</label>
          <div><input id="cmp-seed" type="number" min="0" step="1" placeholder="optional" style="width:120px">
            <div class="hint">Change for a different random search path; blank = engine default</div></div>
          <label for="cmp-restarts-mode">${tip("restarts", "CMA restarts")}</label>
          <div>
            <select id="cmp-restarts-mode">
              <option value="" selected>— config default —</option>
              <option value="off">off — single CMA-ES</option>
              <option value="ipop">IPOP</option>
              <option value="bipop">BIPOP</option>
            </select>
            <div class="hint">Fresh ES on leftover budget after an early stop; useful on longer searches</div>
          </div>
          <label for="cmp-restarts-max">${tip("restarts_max", "Max restarts")}</label>
          <div><input id="cmp-restarts-max" type="number" value="2" min="0" max="64" disabled style="width:120px">
            <div class="hint">0–64; ignored when mode is off / config default</div></div>` : ""}
      </div>`;
  }

  function renderTierRow() {
    const scr = c => Math.max(40, 10 * (c.n_knobs || 0));       // campaign.budget_for_tier
    const cmp = c => Math.max(150, 25 * (c.n_knobs || 0));
    const est = pickedConfigs().map(c =>
      `${esc(c.catalog_name || c.name)} · ${scr(c)} evals (screen) / 2 × ${cmp(c)} (compare)`).join(" · ") || "—";
    return `
      <div class="form-grid">
        <span class="form-label">Tier</span>
        <div class="btn-row" role="radiogroup" aria-label="campaign tier">
          ${["dry-run", "screen", "compare"].map(t =>
            `<button type="button" class="job-type-btn" data-tier="${t}" aria-pressed="${S.tier === t}">${t}</button>`).join("")}
        </div>
        <span class="form-label">What it does</span>
        <div class="hint">${esc(COMPOSE_TIER_HINTS[S.tier] || "")}</div>
        <span class="form-label">Families</span>
        <div><code>--families ${esc(familiesArg() || "")}</code>
          <div class="hint">The campaign resolves these catalog names; entries that don't fit the brief are skipped per-entry with the reason printed (the real compat gate lives engine-side). The per-entry skips show up in the campaign's results.</div></div>
        <span class="form-label">Budget</span>
        <div class="hint">Engine default per picked family (campaign <code>budget_for_tier</code>): ${est}</div>
      </div>`;
  }

  function currentJob() {
    if (!S.picks.size || !S.briefPath) return null;
    if (S.picks.size === 1) {
      const config = [...S.picks][0];
      const seedRaw = S.runKind === "dry-run" ? "" : String(document.getElementById("cmp-seed")?.value ?? "").trim();
      const seed = seedRaw === "" ? {} : { cma_seed: seedRaw };
      if (S.runKind === "search") {
        const budRaw = String(document.getElementById("cmp-budget")?.value ?? "").trim();
        const rmode = document.getElementById("cmp-restarts-mode")?.value || "";
        const rmaxEl = document.getElementById("cmp-restarts-max");
        const restarts = !rmode ? {}
          : rmode === "off" ? { restarts_mode: "off" }
          : { restarts_mode: rmode,
              restarts_max: rmaxEl && String(rmaxEl.value).trim() !== "" ? rmaxEl.value : "2" };
        return { kind: "search", args: { config, brief: S.briefPath,
                                         ...(budRaw === "" ? {} : { budget: budRaw }),
                                         ...seed, ...restarts } };
      }
      if (S.runKind === "run") return { kind: "run", args: { config, brief: S.briefPath, ...seed } };
      return { kind: "dry-run", args: { config, brief: S.briefPath } };
    }
    const fams = familiesArg();
    if (!fams || !FAM_RE.test(fams)) return null;
    return { kind: "campaign", args: { brief: S.briefPath, families: fams, tier: S.tier } };
  }

  function gateReason() {
    if (!S.picks.size) return "pick at least one typology in step 1";
    if (!S.briefPath) return "save the brief first (step 2) — a run needs a file path";
    if (S.picks.size > 1 && !FAM_RE.test(familiesArg()))
      return "the picked configs resolve no catalog family names for a campaign";
    if (S.picks.size === 1) {
      if (S.runKind !== "dry-run" && S.busyReason) return "GPU is busy — only dry-run is available";
    } else if (S.busyReason && S.tier !== "dry-run") {
      return "GPU is busy — only the dry-run tier is available";
    }
    return null;
  }

  function refreshRunMode() {
    const modeEl = document.getElementById("cmp-run-mode");
    const n = S.picks.size;
    if (!n) {
      modeEl.innerHTML = `<p class="hint" role="note">pick at least one typology in step 1 — nothing runs until one is picked.</p>`;
    } else if (n === 1) {
      const c = pickedConfigs()[0];
      modeEl.innerHTML = renderKindRow() +
        (c.catalog_name
          ? `<div class="hint">Single catalogued config — one <code>--config ${esc(c.path)}</code> run. Need several shapes at once? Pick more in step 1 to switch to a campaign.</div>`
          : `<div class="hint">Uncatalogued config — launches as a single <code>--config ${esc(c.path)}</code> run; it cannot join a campaign (campaign resolves catalog names only).</div>`);
    } else {
      modeEl.innerHTML = `<h4 style="margin:0 0 6px">Campaign across ${n} typologies</h4>` + renderTierRow();
    }
    modeEl.querySelectorAll("[data-kind]").forEach(b => b.onclick = () => {
      S.runKind = b.dataset.kind;
      refreshRunMode(); updatePreview();
    });
    modeEl.querySelectorAll("[data-tier]").forEach(b => b.onclick = () => {
      S.tier = b.dataset.tier;
      refreshRunMode(); updatePreview();
    });
    ["cmp-budget", "cmp-seed", "cmp-restarts-max"].forEach(id =>
      document.getElementById(id)?.addEventListener("input", updatePreview));
    const syncCmpRestarts = () => {
      const mode = document.getElementById("cmp-restarts-mode")?.value || "";
      const maxEl = document.getElementById("cmp-restarts-max");
      if (maxEl) maxEl.disabled = !(mode === "ipop" || mode === "bipop");
    };
    async function refreshCmpBudgetHint({ apply = false } = {}) {
      const hint = document.getElementById("cmp-budget-hint");
      const applyBtn = document.getElementById("cmp-budget-apply");
      const bud = document.getElementById("cmp-budget");
      if (!hint || S.runKind !== "search" || S.picks.size !== 1) return;
      const path = [...S.picks][0];
      const mode = document.getElementById("cmp-restarts-mode")?.value || "";
      const rmax = document.getElementById("cmp-restarts-max")?.value || "2";
      const q = new URLSearchParams({
        config: path,
        restarts_mode: mode || "config",
        restarts_max: rmax,
      });
      const h = await api("/api/budget-hint?" + q).catch(e => ({ error: String(e.message || e) }));
      if (h.error) {
        hint.textContent = "Could not suggest budget: " + h.error;
        if (applyBtn) applyBtn.style.display = "none";
        return;
      }
      hint.textContent =
        `Suggested ${h.recommended} · N=${h.n_knobs} · λ≈${h.popsize_default} · ` +
        `screen ${h.screen} / compare ${h.compare} (blank field still = engine 60)`;
      hint.title = h.rationale || "";
      if (applyBtn) {
        applyBtn.style.display = "";
        applyBtn.onclick = () => {
          if (bud) bud.value = h.recommended;
          updatePreview();
        };
      }
      if (apply && bud && String(bud.value || "").trim() === "") {
        bud.value = h.recommended;
        updatePreview();
      }
    }
    document.getElementById("cmp-restarts-mode")?.addEventListener("change", () => {
      syncCmpRestarts();
      refreshCmpBudgetHint({ apply: false });
      updatePreview();
    });
    document.getElementById("cmp-restarts-max")?.addEventListener("change", () => {
      refreshCmpBudgetHint({ apply: false });
    });
    syncCmpRestarts();
    refreshCmpBudgetHint({ apply: true });
    syncGate();
    showBusy();
  }

  function syncGate() {
    const gate = gateReason();
    launchBtn.disabled = !!gate;
    launchBtn.title = gate || "";
    setLaunchMsg(gate ? `⚠ ${esc(gate)}.` : "");
  }

  // Preview: asked from the server, which builds the exact argv a launch would run
  let _pvTimer = null;
  function updatePreview() {
    clearTimeout(_pvTimer);
    _pvTimer = setTimeout(async () => {
      const job = currentJob();
      if (!job) {
        cmdEl.textContent = S.picks.size
          ? "— save the brief first (step 2) — the run needs a file path"
          : "— fill steps 1 and 2 to see the exact command";
        return;
      }
      const r = await post("/api/preview", job);
      if (ROOT !== currentRoot()) return;
      cmdEl.textContent = r.error ? "— " + r.error : r.command;
      S.busyReason = (r.gpu && r.gpu_busy) ? r.gpu_busy : null;
      syncGate();
      showBusy();
    }, 150);
  }

  // Launch: POST /api/jobs — the wizard never builds solver commands itself
  launchBtn.onclick = async () => {
    errEl.innerHTML = "";
    const gate = gateReason();
    const job = currentJob();
    if (!job || gate) {
      errEl.innerHTML = `<div class="alert warn" role="status">⚠ ${esc(gate || "nothing to launch yet")}.</div>`;
      return;
    }
    if (S.busyReason) {
      errEl.innerHTML = `<div class="alert warn" role="status">⚠ ${esc(S.busyReason)} — a GPU launch is refused while a job runs. dry-run stays available.</div>`;
      return;
    }
    if (S.picks.size > 1 && S.tier === "compare" && !confirm("Compare tier takes hours. Run it now?")) return;
    const r = await post("/api/jobs", job);
    if (ROOT !== currentRoot()) return;
    if (r.error) {
      errEl.innerHTML = `<div class="alert error" role="alert"><b>Error:</b> ${esc(r.error)}</div>`;
    } else {
      errEl.innerHTML = `<div class="alert info">Job started: ${esc(r.id)} — follow it on the <a href="#/launch">Launch page</a> (its job monitor lives there).</div>`;
    }
  };

  renderShapes();
  refreshBriefStatus();
  refreshRunMode();
}

// ── View 6: Launch ─────────────────────────────────────────────────

let _launchPollTimer = null;

async function viewLaunch() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let briefs = [], jobs = [], configs = [], statusData = null;
  try {
    [briefs, jobs, configs, statusData] = await Promise.all([
      api("/api/briefs"),
      api("/api/jobs"),
      api("/api/configs").catch(() => []),
      api("/api/status").catch(() => null),
    ]);
  } catch (e) { ROOT.innerHTML = errBanner(e.message); return; }
  const typs = await api("/api/typologies").catch(() => []);
  if (ROOT !== currentRoot()) return;   // the user navigated away while this loaded
  renderLaunch(briefs, jobs, configs, statusData, typs);
}

function renderLaunch(briefs, jobs, configs, statusData, typs = []) {
  const lock = (statusData || {}).gpu_lock;
  // Live: re-read from /api/status while the page is open (the server re-checks on every launch).
  let gpuBusy = !!(lock && lock.alive);
  const ROOT_LAUNCH = currentRoot();
  const busyNoteHtml = (lk) => (lk && lk.alive)
    ? `<div class="gpu-busy-note" role="status">
        ⚠ GPU busy: ${esc(lk.user || "")} running <em>${esc(lk.command || "")}</em> since ${esc(timeSince(lk.start_time))}.
        GPU actions disabled. Dry-run always available.
      </div>` : "";
  const busyNote = busyNoteHtml(lock);

  // verify_only briefs (12 kHz, P2) are for `verify --brief` only: the CLI refuses them for search/campaign
  const briefOpts = briefs.filter(b => !(b.brief && b.brief.verify_only)).map(b => `<option value="${esc(b.path)}" data-name="${esc(b.name)}">${esc(b.name)}${b.kind === "user" ? " (yours)" : ""}</option>`).join("");
  const pre = new URLSearchParams((location.hash.split("?")[1]) || "");

  // Build config select options grouped by catalog group
  const byGroup = {};
  for (const c of configs) {
    const g = c.group || "Other";
    if (!byGroup[g]) byGroup[g] = [];
    byGroup[g].push(c);
  }
  let configSelectOpts = `<option value="">— select a config —</option>`;
  for (const [grp, cfgs] of Object.entries(byGroup)) {
    configSelectOpts += `<optgroup label="${esc(grp)}">`;
    for (const c of cfgs) {
      const desc = c.description ? ` — ${c.description.slice(0, 60)}` : "";
      const disabled = c.disabled ? "disabled" : "";
      configSelectOpts += `<option value="${esc(c.path)}" ${disabled}>${esc(c.catalog_name || c.name)}${esc(desc)}${c.disabled ? " (disabled)" : ""}</option>`;
    }
    configSelectOpts += `</optgroup>`;
  }

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Launch jobs</div>
        <h2>Launch</h2>
        <div id="launch-busy">${busyNote}</div>
      </div>
      <div class="card stack" style="gap:16px">
        <h3>Job type</h3>
        <div class="btn-row" role="radiogroup" aria-label="job type">
          <button class="job-type-btn" data-type="campaign" aria-pressed="true">Campaign</button>
          <button class="job-type-btn" data-type="search" aria-pressed="false">Search</button>
          <button class="job-type-btn" data-type="dry-run" aria-pressed="false">Dry-run <span class="muted" style="font-size:0.75rem">(always available)</span></button>
        </div>

        <!-- Campaign form -->
        <div id="launch-form-campaign" class="launch-form stack" style="gap:12px">
          <div class="form-grid">
            <label for="lf-brief">Brief</label>
            <select id="lf-brief">${briefOpts}</select>

            <label for="lf-tier">${tip("tier", "Tier")}</label>
            <div>
              <select id="lf-tier">
                <option value="dry-run">dry-run — mesh only, seconds</option>
                <option value="screen" selected>screen — one search per family, minutes</option>
                <option value="compare">compare — two repeats, hours</option>
              </select>
              <div class="hint" id="tier-hint">One search per family; coarse first ranking.</div>
            </div>

            <span class="form-label">Families</span>
            <div>
              <div id="fam-picker" class="fam-picker" role="group" aria-label="Horn families"></div>
              <div class="hint" id="fam-summary"></div>
            </div>
          </div>
          <div class="alert warn" id="compare-warn" style="display:none" role="alert">
            ⚠ <b>Compare tier</b> takes hours. Never run during a live GPU session.
          </div>
        </div>

        <!-- Search form -->
        <div id="launch-form-search" class="launch-form stack" style="display:none;gap:12px" ${gpuBusy ? "aria-disabled='true'" : ""}>
          <div id="search-busy" class="alert warn" ${gpuBusy ? "" : "style='display:none'"}>GPU busy — search disabled while a job is running.</div>
          <div class="form-grid">
            <label for="lf-config">Config</label>
            <select id="lf-config">${configSelectOpts}</select>
            <label for="lf-budget">${tip("budget", "Budget")}</label>
            <div><input id="lf-budget" type="number" value="200" min="1" max="5000">
              <div class="hint" id="lf-budget-hint">Pick a config — suggested budget uses Hansen ~100·N (GUI cap 5000).</div>
              <button type="button" class="linkish" id="lf-budget-apply" style="display:none">Use suggested</button></div>
            <label for="lf-seed">${tip("cma_seed", "CMA seed")}</label>
            <div><input id="lf-seed" type="number" value="1234">
              <div class="hint">Change to get a different random search path</div></div>
            <label for="lf-restarts-mode">${tip("restarts", "CMA restarts")}</label>
            <div>
              <select id="lf-restarts-mode">
                <option value="" selected>— config default —</option>
                <option value="off">off — single CMA-ES</option>
                <option value="ipop">IPOP — larger population each restart</option>
                <option value="bipop">BIPOP — small-σ + large-pop mix</option>
              </select>
              <div class="hint">When CMA stops early, spend leftover budget on a fresh ES. Best on longer budgets.</div>
            </div>
            <label for="lf-restarts-max">${tip("restarts_max", "Max restarts")}</label>
            <div><input id="lf-restarts-max" type="number" value="2" min="0" max="64" disabled>
              <div class="hint">Restarts after the first run (0–64). Ignored when mode is off / config default.</div></div>
            <label for="lf-sbrief">Brief</label>
            <select id="lf-sbrief"><option value="">— use config default —</option>${briefOpts}</select>
          </div>
        </div>

        <!-- Dry-run form -->
        <div id="launch-form-dry-run" class="launch-form stack" style="display:none;gap:12px">
          <div class="form-grid">
            <label for="lf-drconfig">Config</label>
            <select id="lf-drconfig">${configSelectOpts}</select>
          </div>
        </div>

        <!-- Command preview -->
        <div class="card" style="background:var(--bg)">
          <div class="eyebrow" style="margin-bottom:6px">Command preview</div>
          <code id="cmd-preview" style="white-space:pre-wrap;word-break:break-all;font-size:0.82rem">hornlab-search campaign …</code>
        </div>
        <div class="btn-row">
          <button id="btn-launch" class="primary" ${gpuBusy && true ? "" : ""}>Start</button>
        </div>
        <div id="launch-error"></div>
      </div>

      <!-- Job list -->
      <div>
        <div class="section-header">
          <h3>Jobs</h3>
          <button id="btn-refresh-jobs">↻ Refresh</button>
        </div>
        <div id="jobs-list" class="stack" style="gap:8px"></div>
      </div>
    </div>`;

  const TIER_HINTS = {
    "dry-run": "Meshes each starting design only — no solving. Takes seconds.",
    "screen": "One search per family, budget max(40, 10×parameters). Coarse ranking in minutes.",
    "compare": "Two repeats, budget max(150, 25×parameters). Needed to claim one family beats another. Hours.",
  };

  // Type toggle
  let currentType = "campaign";
  document.querySelectorAll(".job-type-btn").forEach(btn => {
    btn.onclick = () => {
      currentType = btn.dataset.type;
      document.querySelectorAll(".job-type-btn").forEach(b => b.setAttribute("aria-pressed", "false"));
      btn.setAttribute("aria-pressed", "true");
      document.querySelectorAll(".launch-form").forEach(f => f.style.display = "none");
      document.getElementById(`launch-form-${currentType}`).style.display = "grid";
      // Disable launch if GPU busy and not dry-run
      const launchBtn = document.getElementById("btn-launch");
      launchBtn.disabled = gpuBusy && currentType !== "dry-run";
      if (launchBtn.disabled) launchBtn.title = "GPU busy — only dry-run is available";
      else launchBtn.title = "";
      if (currentType === "search") refreshBudgetHint({ apply: false });
      updatePreview();
    };
  });

  // Tier hint update
  const tierSel = document.getElementById("lf-tier");
  tierSel.addEventListener("change", () => {
    document.getElementById("tier-hint").textContent = TIER_HINTS[tierSel.value] || "";
    document.getElementById("compare-warn").style.display = tierSel.value === "compare" ? "" : "none";
    updatePreview();
  });

  // Family picker: grouped by kind, incompatible families disabled with the CLI's own reason
  const GROUP_LABEL = CATALOG_GROUP_LABEL;   // shared with the Briefs picker + Compose wizard
  const selected = new Set((pre.get("families") || "").split(",").filter(Boolean));
  if (pre.get("brief")) {
    const o = [...document.getElementById("lf-brief").options].find(x => x.dataset.name === pre.get("brief"));
    if (o) document.getElementById("lf-brief").value = o.value;
  }
  if (pre.get("tier")) document.getElementById("lf-tier").value = pre.get("tier");
  const briefName = () => document.getElementById("lf-brief").selectedOptions[0]?.dataset.name || "";
  function estMinutes(t, tier) {
    // slowest measured campaign for this family: replayed (cached) campaigns run far faster than fresh
    // ones, so the maximum is the honest upper estimate; ignore near-zero all-cached campaigns
    const ms = (t.results || []).map(x => x.s_per_eval).filter(v => v != null && v >= 0.5);
    if (!ms.length) return null;
    const n = tier === "compare" ? 2 * t.budget.compare : tier === "screen" ? t.budget.screen : 0;
    return n * Math.max(...ms) / 60;
  }
  function renderFamPicker() {
    const bn = briefName(), tier = document.getElementById("lf-tier").value;
    const groups = {};
    for (const t of typs) (groups[t.group] = groups[t.group] || []).push(t);
    const box = document.getElementById("fam-picker");
    box.innerHTML = Object.entries(groups).map(([g, list]) => `
      <fieldset class="fam-group"><legend>${esc(GROUP_LABEL[g] || g)}
        <button type="button" class="linkish" data-all="${esc(g)}">select all that fit</button></legend>
        ${list.map(t => {
          const c = (t.compat || {})[bn] || { ok: true };
          const off = !c.ok || t.disabled;
          const best = (t.results || []).find(r => r.brief === bn);
          const est = estMinutes(t, tier);
          return `<label class="fam-row ${off ? "off" : ""}" title="${esc(off ? (c.reason || "disabled") : (t.description || ""))}">
            <input type="checkbox" value="${esc(t.name)}" ${off ? "disabled" : ""} ${selected.has(t.name) && !off ? "checked" : ""}>
            <span class="fam-name">${esc(t.name)}</span>
            <span class="fam-meta">${esc(t.symmetry === "axisymmetric" ? "axisymmetric" : "H/V")} · ${t.n_knobs} params ·
              ${tier === "compare" ? "2 × " + t.budget.compare : tier === "screen" ? t.budget.screen : "–"} evals${est != null && tier !== "dry-run" ? ` · ≈ ${est < 90 ? Math.round(est) + " min" : (est / 60).toFixed(1) + " h"}` : ""}</span>
            <span class="fam-best">${off ? `<em>${esc(t.disabled ? "disabled" : "does not fit this brief")}</em>` : !best ? "not run on this brief" : best.no_valid ? `<em class="warn-text">no valid design here (${esc(best.tier)})</em>` : `${esc(best.tier)} #${best.rank}/${best.of} · score ${fmt(best.median_j)}`}</span>
          </label>`;
        }).join("")}
      </fieldset>`).join("");
    box.querySelectorAll("input[type=checkbox]").forEach(cb => cb.onchange = () => {
      cb.checked ? selected.add(cb.value) : selected.delete(cb.value); summary(); updatePreview();
    });
    box.querySelectorAll("[data-all]").forEach(b => b.onclick = () => {
      box.querySelectorAll(`fieldset input:not(:disabled)`).forEach(cb => {
        if (cb.closest("fieldset").querySelector("[data-all]") === b) { cb.checked = true; selected.add(cb.value); }
      });
      summary(); updatePreview();
    });
    // drop selections that no longer fit the brief
    for (const n of [...selected]) {
      const cb = box.querySelector(`input[value="${CSS.escape(n)}"]`);
      if (!cb || cb.disabled) selected.delete(n);
    }
    summary();
  }
  function summary() {
    const tier = document.getElementById("lf-tier").value;
    const chosen = typs.filter(t => selected.has(t.name));
    const evals = chosen.reduce((a, t) => a + (tier === "compare" ? 2 * t.budget.compare : tier === "screen" ? t.budget.screen : 0), 0);
    const mins = chosen.map(t => estMinutes(t, tier));
    const known = mins.filter(m => m != null);
    document.getElementById("fam-summary").textContent = !chosen.length
      ? "Nothing selected = every family that fits the brief."
      : `${chosen.length} selected · ${evals.toLocaleString()} evaluations` +
        (tier !== "dry-run" && known.length ? ` · ≈ ${Math.round(known.reduce((a, b) => a + b, 0))} min measured on this machine` +
         (known.length < chosen.length ? ` (+ ${chosen.length - known.length} never timed)` : "") : "");
  }
  const famArg = () => [...selected].join(",");

  // Command preview: asked from the server, which builds the exact argv a launch would run
  let _pv = null;
  function currentJob() {
    if (currentType === "campaign")
      return { kind: "campaign", args: { brief: document.getElementById("lf-brief").value, families: famArg(),
                                         tier: document.getElementById("lf-tier").value } };
    if (currentType === "search") {
      const rmode = document.getElementById("lf-restarts-mode")?.value || "";
      const rmaxEl = document.getElementById("lf-restarts-max");
      const restarts = !rmode ? {}
        : rmode === "off" ? { restarts_mode: "off" }
        : { restarts_mode: rmode,
            restarts_max: rmaxEl && rmaxEl.value !== "" ? rmaxEl.value : "2" };
      return { kind: "search", args: { config: document.getElementById("lf-config").value,
                                       budget: +document.getElementById("lf-budget").value,
                                       cma_seed: document.getElementById("lf-seed").value,
                                       brief: document.getElementById("lf-sbrief").value || undefined,
                                       ...restarts } };
    }
    return { kind: "dry-run", args: { config: document.getElementById("lf-drconfig").value } };
  }
  function updatePreview() {
    clearTimeout(_pv);
    _pv = setTimeout(async () => {
      const out = document.getElementById("cmd-preview");
      if (!out) return;
      const r = await post("/api/preview", currentJob());
      out.textContent = r.error ? "— " + r.error : r.command;
      out.classList.toggle("muted", !!r.error);
    }, 150);
  }

  function syncRestartsMax() {
    const mode = document.getElementById("lf-restarts-mode")?.value || "";
    const maxEl = document.getElementById("lf-restarts-max");
    if (!maxEl) return;
    maxEl.disabled = !(mode === "ipop" || mode === "bipop");
  }

  // Hansen-grounded budget hint (/api/budget-hint). Auto-fills unless the user typed a budget.
  let _budgetManual = false;
  async function refreshBudgetHint({ apply = false } = {}) {
    const path = document.getElementById("lf-config")?.value || "";
    const hint = document.getElementById("lf-budget-hint");
    const applyBtn = document.getElementById("lf-budget-apply");
    const bud = document.getElementById("lf-budget");
    if (!hint) return;
    if (!path) {
      hint.textContent = "Pick a config — suggested budget uses Hansen ~100·N (GUI cap 5000).";
      if (applyBtn) applyBtn.style.display = "none";
      return;
    }
    const mode = document.getElementById("lf-restarts-mode")?.value || "";
    const rmax = document.getElementById("lf-restarts-max")?.value || "2";
    const q = new URLSearchParams({
      config: path,
      restarts_mode: mode || "config",
      restarts_max: rmax,
    });
    const h = await api("/api/budget-hint?" + q).catch(e => ({ error: String(e.message || e) }));
    if (ROOT_LAUNCH !== currentRoot()) return;
    if (h.error) {
      hint.textContent = "Could not suggest budget: " + h.error;
      if (applyBtn) applyBtn.style.display = "none";
      return;
    }
    const capNote = h.capped ? " (capped at 5000)" : "";
    hint.textContent =
      `Suggested ${h.recommended}${capNote} · N=${h.n_knobs} knobs · λ≈${h.popsize_default} · ` +
      `screen ${h.screen} / compare ${h.compare} / Hansen 100·N=${h.hansen_100n}`;
    hint.title = h.rationale || "";
    if (applyBtn) {
      applyBtn.style.display = "";
      applyBtn.onclick = () => {
        if (bud) bud.value = h.recommended;
        _budgetManual = false;
        updatePreview();
      };
    }
    if (apply && !_budgetManual && bud) {
      bud.value = h.recommended;
      updatePreview();
    }
  }

  document.getElementById("lf-restarts-mode")?.addEventListener("change", () => {
    syncRestartsMax();
    refreshBudgetHint({ apply: true });
    updatePreview();
  });
  syncRestartsMax();

  // Wire inputs to preview
  ["lf-brief", "lf-config", "lf-budget", "lf-seed", "lf-sbrief", "lf-drconfig",
   "lf-restarts-max"].forEach(id => {
    const el2 = document.getElementById(id);
    if (el2) el2.addEventListener("input", updatePreview);
    if (el2) el2.addEventListener("change", updatePreview);
  });
  document.getElementById("lf-budget")?.addEventListener("input", () => { _budgetManual = true; });
  document.getElementById("lf-config")?.addEventListener("change", () => {
    _budgetManual = false;
    refreshBudgetHint({ apply: true });
  });
  document.getElementById("lf-restarts-max")?.addEventListener("change", () => {
    refreshBudgetHint({ apply: true });
  });
  document.getElementById("lf-brief").addEventListener("change", renderFamPicker);
  document.getElementById("lf-tier").addEventListener("change", renderFamPicker);
  renderFamPicker();
  refreshBudgetHint({ apply: false });
  updatePreview();

  // Initial launch button state
  document.getElementById("btn-launch").disabled = false; // campaign is default, no GPU gate for dry-run tier

  // Launch
  document.getElementById("btn-launch").onclick = async () => {
    const errEl = document.getElementById("launch-error");
    errEl.innerHTML = "";
    let kind, args;
    if (currentType === "campaign") {
      const tier = document.getElementById("lf-tier").value;
      if (gpuBusy && tier !== "dry-run") {
        errEl.innerHTML = `<div class="alert error">GPU is busy. Only dry-run tier is available while a job is running.</div>`;
        return;
      }
      if (tier === "compare" && !confirm("Compare tier takes hours. Run it now?")) return;
      ({ kind, args } = currentJob());
    } else if (currentType === "search") {
      if (gpuBusy) { errEl.innerHTML = `<div class="alert error">GPU is busy. Wait for the current job to finish.</div>`; return; }
      ({ kind, args } = currentJob());
    } else {
      ({ kind, args } = currentJob());
    }
    const r = await post("/api/jobs", { kind, args });
    if (r.error) {
      errEl.innerHTML = `<div class="alert error" role="alert"><b>Error:</b> ${esc(r.error)}</div>`;
    } else {
      errEl.innerHTML = `<div class="alert info">Job started: ${esc(r.id)}</div>`;
      refreshJobs();
    }
  };

  renderJobs(jobs);

  document.getElementById("btn-refresh-jobs").onclick = refreshJobs;

  // Poll running jobs every 2s
  clearInterval(_launchPollTimer);
  let tick = 0;
  _launchPollTimer = setInterval(async () => {
    if (!location.hash.startsWith("#/launch")) { clearInterval(_launchPollTimer); _launchPollTimer = null; return; }
    refreshJobs();
    if (++tick % 3) return;                               // GPU state every ~6 s
    const st = await api("/api/status").catch(() => null);
    if (!st || ROOT_LAUNCH !== currentRoot()) return;
    const lk = st.gpu_lock, busy = !!(lk && lk.alive);
    if (busy === gpuBusy) return;
    gpuBusy = busy;
    const nb = document.getElementById("launch-busy");
    if (nb) nb.innerHTML = busyNoteHtml(lk);
    const sb = document.getElementById("search-busy");
    if (sb) sb.style.display = busy ? "" : "none";
    const lb = document.getElementById("btn-launch");
    if (lb) { lb.disabled = busy && currentType === "search"; lb.title = lb.disabled ? "GPU busy — only dry-run is available" : ""; }
    showToast(busy ? "GPU is now busy: GPU actions disabled" : "GPU is free: GPU actions available", busy ? "info" : "good");
  }, 2000);
}

async function refreshJobs() {
  let jobs;
  try { jobs = await api("/api/jobs"); } catch { return; }
  renderJobs(jobs);
}

function renderJobs(jobs) {
  const el2 = document.getElementById("jobs-list");
  if (!el2) return;
  if (!jobs.length) { el2.innerHTML = `<p class="muted">No jobs yet.</p>`; return; }

  el2.innerHTML = jobs.slice().reverse().map(j => {
    const sc = `job-status-${j.status || "done"}`;
    const qpos = Number(j.queue_position) > 0 ? Number(j.queue_position) : null;
    const dur = j.started && j.ended
      ? " · " + ((new Date(j.ended) - new Date(j.started)) / 60000).toFixed(1) + "m"
      : j.status === "running" ? " · running…"
      : j.status === "queued" ? (qpos ? ` · queued (position ${qpos})` : " · queued")
      : "";

    const logLines = (j.log_tail || []).join("\n");
    const cancelBtn = j.status === "running"
      ? `<button class="btn danger cancel-job-btn" data-job-id="${esc(j.id)}" title="Stops the run: the job's process tree is killed and a gpu-clean pass runs after GPU jobs">Stop run</button>`
      : j.status === "queued"
        ? `<button class="btn danger cancel-job-btn" data-job-id="${esc(j.id)}" data-queued="1" title="Removes this request from the queue — nothing has started yet">Cancel queued</button>`
        : "";

    // Try to extract run ID from log
    let runLink = "";
    if (j.log_tail) {
      const logText = j.log_tail.join(" ");
      const rm = logText.match(/runs[/\\]([0-9]{8}T[0-9]{6}Z-[a-z]+-[0-9a-f]{6})/);
      if (rm) runLink = `<a class="btn" href="#/run/${esc(rm[1])}" style="font-size:0.8rem">Open run →</a>`;
    }

    return `<div class="job-row">
      <div class="job-head">
        <div>
          <span class="job-title">${esc(j.kind || "")} · <span class="mono">${esc(j.id || "")}</span></span>
          <span class="${sc}"> ${esc(j.status || "")}${esc(dur)}</span>
        </div>
        <div class="btn-row" style="gap:6px">${cancelBtn}${runLink}</div>
      </div>
      <div class="mono muted" style="font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc((j.command || j.argv || []).join?.(" ") || j.command || "")}</div>
      ${logLines ? `<div class="log-tail" style="max-height:100px">${esc(logLines)}</div>` : ""}
    </div>`;
  }).join("");

  // Attach cancel event via delegation (avoids XSS risk from inline onclick)
  el2.querySelectorAll(".cancel-job-btn").forEach(btn => {
    btn.onclick = async () => {
      const wasQueued = btn.dataset.queued === "1";
      if (!wasQueued && !confirm("Cancel this job?")) return;
      const r = await post("/api/job/" + btn.dataset.jobId + "/cancel",
                           wasQueued ? { only_queued: true } : {});
      if (r.error) showToast(r.error, "error");
      else if (wasQueued) showToast("Queued request cancelled — nothing had started.", "info");
      else showToast("Stop requested — the job is killed and a gpu-clean pass runs after GPU jobs.", "info");
      refreshJobs();
    };
  });
}

// ── View G: Glossary ───────────────────────────────────────────────

function viewGlossary() {
  const ROOT = currentRoot();     // this view's own container (see route())
  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Reference</div>
        <h2>Glossary</h2>
        <p class="muted" style="font-size:0.85rem">Plain-language meaning of every number the GUI shows. Hover any underlined term in the app to see a tooltip.</p>
      </div>
      <div class="glossary-list">
        ${Object.entries(GLOSSARY).map(([key, t]) => `
          <div class="glossary-entry">
            <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap">
              <span class="g-key">${esc(key)}</span>
              <span class="g-label">${esc(t.label)}</span>
              ${t.unit ? `<span class="g-unit">[${esc(t.unit)}]</span>` : ""}
            </div>
            <div class="g-long">${esc(t.long)}</div>
          </div>
        `).join("")}
      </div>
    </div>`;
}

// ── Init ───────────────────────────────────────────────────────────

route();
// The nav pill's dedicated 10 s poll starts once the page has loaded. Modules run before
// DOMContentLoaded fires, so the event always lands after boot; the listener keeps the offline
// node import of this module timer-free (its shim's addEventListener is a no-op).
document.addEventListener("DOMContentLoaded", startNavRunPill, { once: true });

// Redraw charts on theme change. route() replaces #view-root, so snapshot scroll and
// filter/form state, re-render, then restore once the async view has settled. The one
// requestAnimationFrame retry catches views that render in stages (wallSection cards).
function snapshotViewState() {
  const snap = { y: window.scrollY, fields: [] };
  document.querySelectorAll(".filter-bar input, .form-grid input, .form-grid select, textarea")
    .forEach(el => snap.fields.push([el, el.value]));
  return snap;
}

function restoreViewState(snap) {
  if (!snap) return;
  window.scrollTo(0, snap.y);
  snap.fields.forEach(([el, v]) => {
    if (el.isConnected && el.value !== v) el.value = v;
  });
}

async function routeAndRestore() {
  const snap = snapshotViewState();
  await route();
  restoreViewState(snap);
  requestAnimationFrame(() => restoreViewState(snap));
}

matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
  // A pinned preference (explicit data-theme) wins; re-rendering here is pure waste.
  if (document.documentElement.hasAttribute("data-theme")) return;
  routeAndRestore();
});
new MutationObserver(() => { routeAndRestore(); })
  .observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

// ── Keyboard access for clickable table rows (rows use onclick for navigation) ──────────────────
new MutationObserver(() => {
  document.querySelectorAll("tr.clickable:not([tabindex]), tr[onclick]:not([tabindex])")
    .forEach(tr => { tr.tabIndex = 0; tr.setAttribute("role", "link"); });
}).observe(document.body, { childList: true, subtree: true });
document.addEventListener("keydown", e => {
  const tr = e.target.closest && e.target.closest("tr[role=link]");
  if (tr && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); tr.click(); }
});

// ── Charts are drawn 1:1 at their measured width: re-render the view after a real width change ──
let _lastW = window.innerWidth, _rsz = null;
window.addEventListener("resize", () => {
  clearTimeout(_rsz);
  _rsz = setTimeout(() => {
    if (Math.abs(window.innerWidth - _lastW) < 40 || !document.querySelector("svg[data-chart]")) return;
    _lastW = window.innerWidth;
    const y = window.scrollY; route(); setTimeout(() => window.scrollTo(0, y), 600);
  }, 350);
});


// ── View: Typologies (every classical horn, hybrid and mesher family) ─────────────────────────────
const TYP_GROUP = {
  classical: ["Classical horns", "Textbook profiles (conical, exponential, hyperbolic-exponential, tractrix, OS) built from their formulas and handed to Magnus's FREEFORM mesher as exact wall anchors."],
  hybrid: ["Hybrids", "Combinations: a different profile in each plane (H/V), a convex blend of two profiles, or small monotone perturbations of a classical wall."],
  magnus: ["Magnus mesher families", "OSSE, R-OSSE, ICW and FREEFORM as Magnus's mesher defines them."],
  legacy: ["Utility / legacy", "Test and adapter configs, not meant for typology comparison."],
};

/** Morph status pill: "Morph searched" when the config searches Ath Morph knobs, "Morph" when it
 *  can take Morph (enable it in the shape sandbox), nothing for rows/grid typologies. */
function morphPill(c) {
  if (!c || !c.morph_capable) return "";
  return c.morph_searched
    ? ` <span class="pill good" style="font-size:0.66rem" title="this config searches Ath Morph knobs">Morph searched</span>`
    : ` <span class="pill" style="font-size:0.66rem" title="can take Ath Morph — turn it on in the shape sandbox (and tick search to add it to runs)">Morph</span>`;
}

async function viewTypologies() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let typs, briefs;
  try { [typs, briefs] = await Promise.all([api("/api/typologies"), api("/api/briefs")]); }
  catch (e) { ROOT.innerHTML = errBanner("Could not load typologies: " + e.message); return; }
  await loadParamCatalog();       // P9: typology descriptions + knob-name chips with hover docs
  const groups = {};
  for (const t of typs) (groups[t.group] = groups[t.group] || []).push(t);
  ROOT.innerHTML = `<div class="stack" style="gap:26px">
    <div>
      <div class="eyebrow">Horn families</div>
      <h2>Typologies</h2>
      <p class="muted prose">Every family the search can run. Pick one or more to screen against a brief; a family that cannot meet a brief (an axisymmetric horn on a 90 × 60° brief) is greyed out there. Results are the latest campaign of each tier per brief; the outline is that family's best design so far. Le Cléac'h is disabled until a verifiable published construction is available.</p>
    </div>
    ${Object.entries(groups).map(([g, list]) => `
      <section class="stack" style="gap:12px">
        <div><h3>${esc((TYP_GROUP[g] || [g])[0])}</h3><p class="muted" style="margin:2px 0 0">${esc((TYP_GROUP[g] || ["", ""])[1])}</p></div>
        <div class="typ-grid">${list.map(t => typCard(t, briefs)).join("")}</div>
      </section>`).join("")}
  </div>`;
  requestAnimationFrame(() => {
    ROOT.querySelectorAll("svg.typ-prof").forEach(sv => {
      const t = typs.find(x => x.name === sv.dataset.name);
      const r = (t.results || []).find(x => x.profile);
      if (r) wallSection(sv, [{ profile: r.profile, color: css("--best"), filled: true }], { H: 120, compact: true });
    });
  });
  // Card-level sandbox navigation: a click anywhere on the card (or Enter/Space on the focused
  // card) opens #/typology/<name>, while every existing affordance inside — the screen-on pills,
  // run links, the open-sandbox link, tooltip terms — still receives its own event first.
  ROOT.querySelectorAll(".typ-card[data-open]").forEach(card => {
    const go = () => { location.hash = card.dataset.open; };
    card.addEventListener("click", e => {
      if (e.target.closest("a, button, input, select, label, .term")) return;
      go();
    });
    card.addEventListener("keydown", e => {
      if (e.target !== card) return;
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); }
    });
  });
}

function typCard(t, briefs) {
  const res = (t.results || []).map(r => r.no_valid
    ? `<tr><td>${esc(r.brief)}</td><td>${esc(r.tier)}</td><td colspan="3" class="warn-text">no valid design under this brief (starting design outside its size envelope)</td></tr>`
    : `<tr>
      <td>${esc(r.brief)}</td><td>${esc(r.tier)}</td>
      <td class="r">${r.rank}/${r.of}</td>
      <td class="r">${r.best_run_id ? `<a href="#/run/${esc(r.best_run_id)}" title="open the best run">${fmt(r.median_j)}</a>` : fmt(r.median_j)}</td>
      <td class="r">${r.dims ? esc(Math.round(r.dims.mouth_w_mm) + "×" + Math.round(r.dims.mouth_h_mm) + "×" + Math.round(r.dims.depth_mm)) : "–"}</td></tr>`).join("");
  const fits = briefs.map(b => {
    const c = (t.compat || {})[b.name] || { ok: true };
    return c.ok && !t.disabled
      ? `<a class="pill good" href="#/launch?brief=${encodeURIComponent(b.name)}&families=${encodeURIComponent(t.name)}&tier=screen" title="Screen ${esc(t.name)} on ${esc(b.name)}">▶ ${esc(b.name)}</a>`
      : `<span class="pill" title="${esc(c.reason || "disabled")}" style="opacity:0.55">${esc(b.name)}</span>`;
  }).join(" ");
  const hasProf = (t.results || []).some(r => r.profile);
  // The whole card opens the typology's shape sandbox (owner ask 2). The affordance is an
  // honest small link (works without the click handler, keeps its own href); the card itself
  // is focusable + keyboard-activatable, and every existing link/button inside still wins.
  return `<article class="card typ-card" data-open="#/typology/${esc(t.name)}" tabindex="0"
      role="link" aria-label="open the ${esc(t.name)} shape sandbox">
    <div class="typ-head">
      <div><div class="typ-name">${typologyTipHtml(t)}</div>
        <a class="typ-open" href="#/typology/${esc(t.name)}" title="open the shape sandbox for this typology">open sandbox →</a>
        <div class="muted typ-meta">${esc(t.symmetry === "axisymmetric" ? "axisymmetric" : "H/V (different planes)")} · ${t.n_knobs} shape parameters · screen ${t.budget.screen} / compare 2 × ${t.budget.compare} evals${morphPill(t)}</div></div>
      ${hasProf ? `<svg class="typ-prof" data-name="${esc(t.name)}" aria-label="best design cross-section"></svg>` : `<div class="typ-prof empty muted">no solved design yet</div>`}
    </div>
    <p class="typ-desc">${esc(t.description || "")}</p>
    ${typologyChipsHtml(t.name)}
    ${res ? `<div class="tbl-wrap"><table class="compact"><thead><tr><th>Brief</th><th>Tier</th><th class="r">Rank</th><th class="r">Score</th><th class="r">W×H×D mm</th></tr></thead><tbody>${res}</tbody></table></div>`
          : `<p class="muted" style="margin:0">Not run in any campaign yet.</p>`}
    <div class="typ-fits"><span class="muted">Screen on:</span> ${fits}</div>
  </article>`;
}
