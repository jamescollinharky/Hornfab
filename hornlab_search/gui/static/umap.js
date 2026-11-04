// umap.js — 2-D cloud of OK search designs (UMAP when installed, else PCA) for one run.
// AGPL-3.0-or-later. Data: GET /api/umap/<run>?method=auto|umap|pca (gui/data.py::run_umap_cloud).
import { NS } from "./charts.js";

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[c]));
const fmt = (v, d = 2) => (v == null || !isFinite(v) ? "–" : Number(v).toFixed(d));

const TONES = [
  { id: "b0", css: "var(--best)" },
  { id: "b1", css: "var(--accent)" },
  { id: "b2", css: "var(--seed)" },
  { id: "b3", css: "var(--muted, #888)" },
];
const J_THRESH = [
  { id: "lt9", lo: 0, hi: 9, label: "J < 9" },
  { id: "9_12", lo: 9, hi: 12, label: "9 ≤ J < 12" },
  { id: "12_16", lo: 12, hi: 16, label: "12 ≤ J < 16" },
  { id: "ge16", lo: 16, hi: 1e9, label: "J ≥ 16" },
];

function phys(bounds, key, u) {
  const b = bounds[key];
  return b.lo + u * (b.hi - b.lo);
}

function paramBands(data, key) {
  const edges = data.unit_edges || [0, 0.25, 0.5, 0.75, 1.0001];
  const labels = data.band_labels || [];
  const bands = [];
  for (let i = 0; i < edges.length - 1; i++) {
    const ulo = edges[i], uhi = edges[i + 1];
    bands.push({
      id: "b" + i,
      ulo, uhi,
      tone: TONES[i % TONES.length].css,
      label: `${fmt(phys(data.bounds, key, ulo), 2)}–${fmt(phys(data.bounds, key, Math.min(uhi, 1)), 2)} (${labels[i] || ("band " + i)})`,
    });
  }
  return bands;
}

function bandIdParam(p, key, bands) {
  const u = p.u[key];
  for (const b of bands) {
    if (u >= b.ulo && u < b.uhi) return b.id;
  }
  return bands[bands.length - 1].id;
}

function bandIdJ(p) {
  for (const b of J_THRESH) {
    if (p.J >= b.lo && p.J < b.hi) return b.id;
  }
  return J_THRESH[J_THRESH.length - 1].id;
}

export async function viewUmap(root, runId) {
  root.innerHTML = `<p class="muted">Building design cloud (PCA always; UMAP if umap-learn is installed)…</p>`;
  let data;
  try {
    const r = await fetch("/api/umap/" + encodeURIComponent(runId) + "?method=auto");
    if (!r.ok) throw new Error(r.status + " " + (await r.text()));
    data = await r.json();
  } catch (e) {
    root.innerHTML = `<div class="alert error">Could not load: ${esc(e.message)}</div>`;
    return;
  }

  const keys = data.keys || [];
  if (!keys.length) {
    root.innerHTML = `<div class="stack" style="gap:12px">
      <div><div class="eyebrow">Design cloud</div><h2>${esc(data.name || runId)}</h2>
      <p class="muted">${esc(data.note || "No searchable knobs on this run.")}
        <a href="#/run/${esc(runId)}">← back to the run</a></p></div></div>`;
    return;
  }

  const defaultKey = keys.includes(data.default_key) ? data.default_key : keys[0];
  root.innerHTML = `<div class="stack umap-view" style="gap:16px">
    <div>
      <div class="eyebrow">Design cloud</div>
      <h2>${esc(data.name || runId)}</h2>
      <p class="muted" style="margin:2px 0 0">
        ${data.n_ok} OK designs · ${data.n_plot} plotted · method <span class="mono">${esc(data.method)}</span>
        ${data.note ? " · " + esc(data.note) : ""}.
        Color by a searchable knob’s unit quartiles or by total J.
        <a href="#/run/${esc(runId)}">← back to the run</a>
      </p>
    </div>
    <div class="card evo-controls" style="display:flex;flex-wrap:wrap;gap:12px 16px;align-items:end">
      <label class="evo-opt">Parameter
        <select id="umap-param" aria-label="Parameter">${keys.map(k =>
          `<option value="${esc(k)}"${k === defaultKey ? " selected" : ""}>${esc(k)}</option>`
        ).join("")}</select>
      </label>
      <label class="evo-opt">Color by
        <select id="umap-mode" aria-label="Color mode">
          <option value="param" selected>Parameter quartiles</option>
          <option value="J">Total J thresholds</option>
        </select>
      </label>
      <label class="evo-opt">Embed
        <select id="umap-method" aria-label="Embedding method">
          <option value="auto" selected>auto</option>
          <option value="umap">UMAP</option>
          <option value="pca">PCA</option>
        </select>
      </label>
    </div>
    <p class="cap" id="umap-hint"></p>
    <div class="legend" id="umap-legend" style="display:flex;flex-wrap:wrap;gap:10px 14px"></div>
    <div class="grid2" style="align-items:start">
      <div class="fig">
        <h3>Cloud</h3>
        <div class="cap">Each point is one OK design in the searchable unit box. Ring = best J so far among OK rows.</div>
        <svg id="umap-svg" role="img" aria-label="Design cloud scatter" style="width:100%;height:440px;background:var(--viz-canvas);border-radius:6px;border:1px solid var(--rule)"></svg>
      </div>
      <div class="fig">
        <h3>Selected design</h3>
        <div class="cap">Click a point for every searchable param (physical + unit).</div>
        <div id="umap-detail"><p class="muted">No point selected.</p></div>
      </div>
    </div>
  </div>`;

  const paramSel = root.querySelector("#umap-param");
  const modeSel = root.querySelector("#umap-mode");
  const methodSel = root.querySelector("#umap-method");
  const hint = root.querySelector("#umap-hint");
  const legend = root.querySelector("#umap-legend");
  const svg = root.querySelector("#umap-svg");
  const detail = root.querySelector("#umap-detail");
  let selected = -1;
  let cloud = data;
  methodSel.value = "auto";

  function showDetail(p) {
    const key = paramSel.value;
    const rows = (cloud.keys || []).map(k => {
      const val = (p.params && p.params[k] != null) ? p.params[k] : phys(cloud.bounds, k, p.u[k]);
      return `<tr><td>${esc(k)}</td><td class="mono" style="text-align:right">${fmt(val, 4)}</td>
        <td class="mono" style="text-align:right">${fmt(p.u[k], 3)}</td></tr>`;
    }).join("");
    detail.innerHTML = `<p class="cap">${p.hash ? "hash " + esc(p.hash) + " · " : ""}J=${fmt(p.J, 3)}${p.b ? " · best" : ""}
      · color channel ${esc(key)}=${fmt((p.params && p.params[key]) ?? phys(cloud.bounds, key, p.u[key]), 3)}</p>
      <div class="tbl-wrap"><table>
        <thead><tr><th>param</th><th style="text-align:right">value</th><th style="text-align:right">unit</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div>`;
  }

  function setLegend(bands, counts) {
    legend.innerHTML = bands.map((b, i) =>
      `<span><i style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${b.tone || TONES[i % TONES.length].css};margin-right:6px"></i>${esc(b.label)} (${counts[b.id] || 0})</span>`
    ).join("") + `<span><i style="display:inline-block;width:10px;height:10px;border-radius:50%;border:2px solid var(--best);margin-right:6px"></i>best (ring)</span>`;
  }

  function paint() {
    const key = paramSel.value;
    const mode = modeSel.value;
    const b = cloud.bounds[key];
    hint.textContent = `${key} bounds ${fmt(b.lo, 2)}–${fmt(b.hi, 2)} · ${cloud.keys.length} searchable params · embed ${cloud.method}`;

    const bands = mode === "param"
      ? paramBands(cloud, key)
      : J_THRESH.map((t, i) => ({ ...t, tone: TONES[i].css }));
    const toneById = Object.fromEntries(bands.map(band => [band.id, band.tone]));
    const counts = Object.fromEntries(bands.map(band => [band.id, 0]));
    cloud.points.forEach(p => {
      p._band = mode === "param" ? bandIdParam(p, key, bands) : bandIdJ(p);
      counts[p._band] = (counts[p._band] || 0) + 1;
    });
    setLegend(bands, counts);

    const W = Math.max(320, svg.clientWidth || 640);
    const H = 440;
    const margin = { top: 20, right: 16, bottom: 40, left: 44 };
    const pts = cloud.points || [];
    const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const y0 = Math.min(...ys), y1 = Math.max(...ys);
    const padX = (x1 - x0) * 0.08 || 0.1;
    const padY = (y1 - y0) * 0.08 || 0.1;
    const xScale = v => margin.left + ((v - (x0 - padX)) / (((x1 + padX) - (x0 - padX)) || 1)) * (W - margin.left - margin.right);
    const yScale = v => H - margin.bottom - ((v - (y0 - padY)) / (((y1 + padY) - (y0 - padY)) || 1)) * (H - margin.top - margin.bottom);

    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);

    const g = document.createElementNS(NS, "g");
    svg.appendChild(g);

    // axes
    const axis = document.createElementNS(NS, "g");
    axis.setAttribute("class", "umap-axis");
    const xAxis = document.createElementNS(NS, "line");
    xAxis.setAttribute("x1", margin.left); xAxis.setAttribute("x2", W - margin.right);
    xAxis.setAttribute("y1", H - margin.bottom); xAxis.setAttribute("y2", H - margin.bottom);
    xAxis.setAttribute("stroke", "var(--rule)");
    const yAxis = document.createElementNS(NS, "line");
    yAxis.setAttribute("x1", margin.left); yAxis.setAttribute("x2", margin.left);
    yAxis.setAttribute("y1", margin.top); yAxis.setAttribute("y2", H - margin.bottom);
    yAxis.setAttribute("stroke", "var(--rule)");
    axis.appendChild(xAxis); axis.appendChild(yAxis);
    const xl = document.createElementNS(NS, "text");
    xl.textContent = cloud.method === "umap" ? "UMAP 1" : "PC 1";
    xl.setAttribute("x", W / 2); xl.setAttribute("y", H - 10);
    xl.setAttribute("text-anchor", "middle"); xl.setAttribute("fill", "var(--muted)");
    xl.setAttribute("font-size", "11");
    const yl = document.createElementNS(NS, "text");
    yl.textContent = cloud.method === "umap" ? "UMAP 2" : "PC 2";
    yl.setAttribute("transform", `rotate(-90 14 ${H / 2})`);
    yl.setAttribute("x", 14); yl.setAttribute("y", H / 2);
    yl.setAttribute("text-anchor", "middle"); yl.setAttribute("fill", "var(--muted)");
    yl.setAttribute("font-size", "11");
    axis.appendChild(xl); axis.appendChild(yl);
    svg.appendChild(axis);

    const ordered = pts.map((p, i) => ({ p, i })).sort((a, b) => b.p.J - a.p.J);
    ordered.forEach(({ p, i }) => {
      if (p.b) return;
      const c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", xScale(p.x));
      c.setAttribute("cy", yScale(p.y));
      c.setAttribute("r", i === selected ? 6 : 4);
      c.setAttribute("fill", toneById[p._band] || "var(--accent)");
      c.setAttribute("opacity", "0.9");
      c.style.cursor = "pointer";
      c.appendChild(document.createElementNS(NS, "title")).textContent =
        `${key}=${fmt((p.params && p.params[key]) ?? phys(cloud.bounds, key, p.u[key]), 3)} · J ${fmt(p.J, 2)}`;
      c.addEventListener("click", () => {
        selected = i;
        showDetail(p);
        paint();
      });
      g.appendChild(c);
    });

    const best = pts.find(p => p.b);
    if (best) {
      const c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", xScale(best.x));
      c.setAttribute("cy", yScale(best.y));
      c.setAttribute("r", 5);
      c.setAttribute("fill", toneById[best._band] || "var(--best)");
      c.style.cursor = "pointer";
      c.appendChild(document.createElementNS(NS, "title")).textContent = `best · J ${fmt(best.J, 2)}`;
      c.addEventListener("click", () => {
        selected = pts.indexOf(best);
        showDetail(best);
        paint();
      });
      g.appendChild(c);
      const ring = document.createElementNS(NS, "circle");
      ring.setAttribute("cx", xScale(best.x));
      ring.setAttribute("cy", yScale(best.y));
      ring.setAttribute("r", 9);
      ring.setAttribute("fill", "none");
      ring.setAttribute("stroke", "var(--best)");
      ring.setAttribute("stroke-width", "2");
      ring.setAttribute("pointer-events", "none");
      g.appendChild(ring);
    }
    if (selected >= 0 && pts[selected]) showDetail(pts[selected]);
  }

  async function reload() {
    hint.textContent = "Recomputing…";
    try {
      const r = await fetch("/api/umap/" + encodeURIComponent(runId) +
        "?method=" + encodeURIComponent(methodSel.value));
      if (!r.ok) throw new Error(r.status + " " + (await r.text()));
      cloud = await r.json();
      selected = -1;
      detail.innerHTML = `<p class="muted">No point selected.</p>`;
      // keep param selection if still present
      if (![...paramSel.options].some(o => o.value === paramSel.value) && cloud.keys?.length) {
        paramSel.value = cloud.default_key || cloud.keys[0];
      }
      paint();
    } catch (e) {
      hint.textContent = "Reload failed: " + e.message;
    }
  }

  paramSel.addEventListener("change", paint);
  modeSel.addEventListener("change", paint);
  methodSel.addEventListener("change", reload);
  window.addEventListener("resize", paint);
  paint();
}
