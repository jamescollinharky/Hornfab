// charts.js — hornlab-search GUI
// AGPL-3.0-or-later.  Adapted from tools/review/review_template.html (same author).
// Exports: el, chart, heat, cmap, niceTicks, diFromCuts

export const NS = "http://www.w3.org/2000/svg";

/** Monotonic id source for per-instance SVG clip paths (one counter per module load). */
let _clipSeq = 0;

/** CSS variable helper */
export const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/** SVG element factory */
export function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

/** Compute ideal tick positions */
export function niceTicks(lo, hi, n = 5) {
  const step0 = (hi - lo) / n;
  const p = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map(k => k * p).find(s => s >= step0);
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

/**
 * Log-frequency ticks: the 1/2/5 x decade values strictly inside [lo, hi], plus the exact
 * endpoints when neither is already within ~2 % of an included tick. Sorted, deduped, finite.
 * logTicks(120, 12000) -> [120, 200, 500, 1000, 2000, 5000, 10000, 12000]
 */
export function logTicks(lo, hi) {
  lo = Number(lo); hi = Number(hi);
  if (!isFinite(lo) || !isFinite(hi) || lo <= 0 || hi <= 0) return [];
  if (hi < lo) { const t = lo; lo = hi; hi = t; }
  if (hi === lo) return [lo];
  const out = [];
  for (let d = Math.floor(Math.log10(lo)); d <= Math.ceil(Math.log10(hi)); d++) {
    for (const m of [1, 2, 5]) {
      const v = m * Math.pow(10, d);
      if (v > lo && v < hi) out.push(v);
    }
  }
  const near = v => out.some(t => Math.abs(t - v) <= 0.02 * v);
  if (!near(lo)) out.push(lo);
  if (!near(hi)) out.push(hi);
  return [...new Set(out.filter(v => isFinite(v) && v > 0).map(v => +v.toFixed(6)))]
    .sort((a, b) => a - b);
}

/**
 * Generic 2-D SVG chart.
 * series: [{pts:[[x,y],...], color, dash, dots, r, w, opacity}]
 * hlines: [{y, color, dash}]
 * vlines: [{x, color, dash, label}]  — full-height marker lines with a top label
 * band: [x0, x1] — filled background strip
 */
/** Pixel width an SVG will be drawn at (so text and strokes render 1:1, never scaled up). */
export function measuredWidth(svg, fallback) {
  const w = Math.round(svg.getBoundingClientRect().width || svg.parentElement?.getBoundingClientRect().width || 0);
  return w >= 120 ? w : fallback;
}

export function chart(svg, { W = 460, H = 240, xlog = false, xlim, ylim,
    xticks, yticks, xlabel, ylabel, band, hlines = [], vlines = [], series, fill }) {
  svg.innerHTML = "";
  W = measuredWidth(svg, W);
  const m = { l: 44, r: 12, t: ylabel ? 20 : 10, b: 32 };   // unit label sits above the plot, clear of the top tick
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";                      // re-drawn on resize (app.js)
  const tx = xlog ? v => Math.log10(v) : v => v;
  const [x0, x1] = xlim.map(tx), [y0, y1] = ylim;
  const X = v => m.l + (tx(v) - x0) / (x1 - x0) * (W - m.l - m.r);
  const Y = v => H - m.b - (v - y0) / (y1 - y0) * (H - m.t - m.b);
  if (xlog && !xticks) xticks = logTicks(xlim[0], xlim[1]);   // span-derived; explicit callers win
  // Clip every plot mark (band, fills, series, marker lines) so nothing draws past the domain
  // into the margins — the old band-rect bleed is gone.
  const clipId = "hl-clip-" + (++_clipSeq);
  const defs = el("defs", {}, svg);
  el("rect", { x: m.l, y: m.t, width: Math.max(0, W - m.l - m.r), height: Math.max(0, H - m.t - m.b) },
     el("clipPath", { id: clipId }, defs));
  const plot = el("g", { "clip-path": `url(#${clipId})` }, svg);
  if (fill) for (const f of fill)
    el("rect", { x: m.l, width: W - m.l - m.r, y: Y(Math.min(f.y1, ylim[1])), height: Math.max(0, Y(Math.max(f.y0, ylim[0])) - Y(Math.min(f.y1, ylim[1]))), fill: f.color, opacity: f.opacity ?? 0.12 }, plot);
  if (band) el("rect", { x: X(band[0]), y: m.t, width: Math.max(0, X(band[1]) - X(band[0])), height: H - m.t - m.b, fill: css("--band") }, plot);
  const g = el("g", { class: "grid" }, svg);
  for (const t of (yticks || [])) {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t) }, g);
    const tt = el("text", { x: m.l - 6, y: Y(t) + 3, "text-anchor": "end" }, svg);
    tt.textContent = t;
  }
  for (const t of (xticks || [])) {
    el("line", { x1: X(t), x2: X(t), y1: m.t, y2: H - m.b }, g);
    const tt = el("text", { x: X(t), y: H - m.b + 13, "text-anchor": "middle" }, svg);
    tt.textContent = t >= 1000 ? (t / 1000) + "k" : t;
  }
  if (xlabel) { const t = el("text", { x: W - m.r, y: H - 3, "text-anchor": "end" }, svg); t.textContent = xlabel; }
  if (ylabel) { const t = el("text", { x: m.l - 6, y: 11, "text-anchor": "end" }, svg); t.textContent = ylabel; }
  for (const h of hlines)
    el("line", { x1: m.l, x2: W - m.r, y1: Y(h.y), y2: Y(h.y), stroke: h.color, "stroke-width": 1.5, "stroke-dasharray": h.dash ? "5 4" : "none" }, svg);
  const vlineColor = v => v.color || css("--label");
  for (const v of vlines) {
    if (!isFinite(v.x)) continue;
    const lx = X(v.x);
    el("line", { x1: lx, x2: lx, y1: m.t, y2: H - m.b, stroke: vlineColor(v),
                 "stroke-width": 1.5, "stroke-dasharray": v.dash ? "5 4" : "none" }, plot);
  }
  const clipY = v => Math.min(Math.max(v, y0), y1);
  for (const s of series) {
    const pts = s.pts.filter(p => p[1] != null && isFinite(p[1]));
    if (!pts.length) continue;
    if (s.dots) {
      for (const p of pts)
        el("circle", { cx: X(p[0]), cy: Y(clipY(p[1])), r: s.r || 2.0, fill: s.color, opacity: s.opacity ?? 0.8 }, plot);
    } else {
      el("path", { d: pts.map((p, i) => (i ? "L" : "M") + X(p[0]).toFixed(1) + "," + Y(clipY(p[1])).toFixed(1)).join(""),
        fill: "none", stroke: s.color, "stroke-width": s.w || 1.8,
        "stroke-dasharray": s.dash ? "5 4" : "none", "stroke-linejoin": "round" }, plot);
    }
  }
  // marker labels sit at the top of the plot; switch anchor near an edge so they never clip
  const pw = W - m.l - m.r;
  for (const v of vlines) {
    if (!isFinite(v.x) || !v.label) continue;
    const lx = X(v.x);
    const anchor = (lx - m.l) < 0.12 * pw ? "start" : (lx > W - m.r - 0.12 * pw) ? "end" : "middle";
    const dx = anchor === "start" ? 4 : anchor === "end" ? -4 : 0;
    const col = vlineColor(v);
    const tt = el("text", { x: lx + dx, y: m.t + 11, "text-anchor": anchor,
      style: `fill:${col};paint-order:stroke;stroke:${css("--surface")};stroke-width:3px;stroke-linejoin:round` }, svg);
    tt.textContent = v.label;
  }
}

/** Perceptual colour ramp: dark navy → teal → pale yellow. -6 dB lands in yellow-green. */
const STOPS = [[0,[18,22,48]],[0.35,[36,70,120]],[0.6,[24,134,140]],[0.85,[120,196,120]],[0.95,[230,220,110]],[1,[255,248,200]]];
export function cmap(t) {
  t = Math.min(1, Math.max(0, t));
  for (let i = 1; i < STOPS.length; i++) {
    if (t <= STOPS[i][0]) {
      const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i], u = (t - a) / (b - a);
      return ca.map((c, k) => Math.round(c + (cb[k] - c) * u));
    }
  }
  return STOPS[STOPS.length - 1][1];
}

/**
 * Draw polar heatmap on canvas.
 * rows: freq×angle dB matrix (null → −40 dB).  Scale: −40..0 dB.
 */
export function heat(canvas, rows) {
  if (!rows || !rows.length) return;
  const nf = rows.length, na = rows[0].length;
  canvas.width = na; canvas.height = nf;
  const ctx = canvas.getContext("2d"), img = ctx.createImageData(na, nf);
  for (let fi = 0; fi < nf; fi++) for (let a = 0; a < na; a++) {
    const v = rows[fi][a] == null ? -40 : rows[fi][a];
    const c = cmap((v + 40) / 40), o = ((nf - 1 - fi) * na + a) * 4;
    img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
}

/** Draw the colorbar into a canvas. */
export function drawCbar(canvas) {
  canvas.width = 400; canvas.height = 10;
  const ctx = canvas.getContext("2d");
  for (let i = 0; i < 400; i++) { const c = cmap(i / 399); ctx.fillStyle = `rgb(${c})`; ctx.fillRect(i, 0, 1, 10); }
}

/** Estimate DI* from target coverage angles. */
export function diFromCuts(h, v) {
  if (h >= 180 && v >= 180) return 0;
  const sh = Math.sin(Math.min(h, 180) * Math.PI / 360), sv = Math.sin(Math.min(v, 180) * Math.PI / 360);
  const om = 4 * Math.asin(Math.min(Math.max(sh * sv, 1e-12), 1));
  return 10 * Math.log10(4 * Math.PI / om);
}

/** Format number with d decimals; show "–" for null/NaN. */
export const fmt = (v, d = 2) => (v == null || !isFinite(v)) ? "–" : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

/** Common log-x frequency tick positions */
export const FT = [500, 1000, 2000, 5000];

/** Standard objective terms */
export const TERMS = ["cov", "rip", "di", "dislope", "flat", "load"];
export const DEFW  = { cov: 1, rip: 1, di: 0.3, dislope: 0.5, flat: 0.5, load: 0 };

/** Deterministic group colour palette (8 slots). */
const GROUP_COLORS = ["#0d6e7a","#a3713a","#2f7d3b","#b23a3a","#7a4a9a","#2a6d9a","#9a6a2a","#5a7a3a"];
const _gidx = {};
export function groupColor(g) {
  if (!(g in _gidx)) _gidx[g] = Object.keys(_gidx).length % GROUP_COLORS.length;
  return GROUP_COLORS[_gidx[g]];
}


/** Find where a level is crossed walking outward from the centre column, per side; null if never.
 *  Linear interpolation between the two samples that bracket the level. */
function edgeAngle(row, angles, level, dir) {
  const c = Math.floor(row.length / 2);
  for (let i = c; i + dir >= 0 && i + dir < row.length; i += dir) {
    const a = row[i], b = row[i + dir];
    if (a == null || b == null) return null;
    if (a >= level && b < level) return angles[i] + (angles[i + dir] - angles[i]) * (a - level) / (a - b);
  }
  return null;
}

/** Polar map (directivity sonogram): level rel. on-axis vs angle (x) and frequency (y, rows low -> high),
 *  with angle / frequency axes and isobar lines at the given levels (default -3, -6, -10 dB).
 *  rows: [nf][na] dB (clipped at -40), angles: [na] deg, freqs: [nf] Hz. */
export function polarMap(svg, rows, angles, freqs, { H = 230, isobars = [-3, -6, -10], fmtF } = {}) {
  svg.innerHTML = "";
  if (!rows || !rows.length || !angles) return;
  const W = measuredWidth(svg, 320);
  const m = { l: 46, r: 8, t: 8, b: 30 };
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";
  const pw = W - m.l - m.r, ph = H - m.t - m.b, nf = rows.length, na = rows[0].length;
  const a0 = angles[0], a1 = angles[angles.length - 1];
  const X = a => m.l + (a - a0) / (a1 - a0) * pw;
  const Yrow = fi => m.t + ph - (fi + 0.5) / nf * ph;          // row centre, low frequency at the bottom
  // raster: one pixel per sample, scaled smoothly into the plot box
  const cv = document.createElement("canvas"); cv.width = na; cv.height = nf;
  const ctx = cv.getContext("2d"), img = ctx.createImageData(na, nf);
  for (let fi = 0; fi < nf; fi++) for (let a = 0; a < na; a++) {
    const v = rows[fi][a] == null ? -40 : rows[fi][a];
    const c = cmap((v + 40) / 40), o = ((nf - 1 - fi) * na + a) * 4;
    img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  el("image", { href: cv.toDataURL(), x: m.l, y: m.t, width: pw, height: ph, preserveAspectRatio: "none",
                style: "image-rendering:auto" }, svg);
  // axes
  const g = el("g", { class: "grid" }, svg);
  for (const a of [-90, -60, -30, 0, 30, 60, 90]) {
    if (a < a0 || a > a1) continue;
    el("line", { x1: X(a), x2: X(a), y1: m.t + ph, y2: m.t + ph + 4, stroke: css("--muted") }, svg);
    const t = el("text", { x: X(a), y: m.t + ph + 15, "text-anchor": "middle" }, svg); t.textContent = a + "°";
  }
  const step = nf > 8 ? 2 : 1, f = fmtF || (v => v >= 1000 ? +(v / 1000).toFixed(1) + "k" : Math.round(v));
  for (let fi = 0; fi < nf; fi += step) {
    const t = el("text", { x: m.l - 5, y: Yrow(fi) + 3, "text-anchor": "end" }, svg); t.textContent = f(freqs[fi]);
  }
  const xl = el("text", { x: m.l + pw, y: H - 2, "text-anchor": "end" }, svg); xl.textContent = "angle";
  const yl = el("text", { x: 2, y: m.t + 2, "dominant-baseline": "hanging" }, svg); yl.textContent = "Hz";
  // isobars (directivity contours): the outermost crossing of each level, left and right of axis
  const styles = { "-3": "2 3", "-6": "none", "-10": "6 3" };
  for (const lev of isobars) {
    for (const dir of [-1, 1]) {
      const pts = [];
      for (let fi = 0; fi < nf; fi++) {
        const ang = edgeAngle(rows[fi], angles, lev, dir);
        if (ang != null) pts.push([X(ang), Yrow(fi)]);
        else if (pts.length) { drawIso(pts); pts.length = 0; }
      }
      drawIso(pts);
      function drawIso(p) {
        if (p.length < 2) return;
        const d = p.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + "," + q[1].toFixed(1)).join("");
        el("path", { d, fill: "none", stroke: "#000", "stroke-opacity": 0.35, "stroke-width": lev === -6 ? 3.2 : 2.4 }, svg);
        el("path", { d, fill: "none", stroke: "#fff", "stroke-width": lev === -6 ? 1.6 : 1.1,
                     "stroke-dasharray": styles[String(lev)] || "none" }, svg);
      }
    }
  }
  el("line", { x1: X(0), x2: X(0), y1: m.t, y2: m.t + ph, stroke: "#fff", "stroke-opacity": 0.25 }, svg);
}

/** Family palette: distinct hues by index (not by group), readable on light and dark backgrounds. */
export const FAMILY_COLORS = ["#2a9db0", "#d98a2b", "#7fb43a", "#c9566e", "#8b6fd1", "#3b7dd8", "#b8a23a", "#5fb8a0", "#d46a3c", "#9a9a9a"];
export function familyColor(i) { return FAMILY_COLORS[i % FAMILY_COLORS.length]; }

/** Wall cross-section, true aspect: H plane to the right (+r), V plane mirrored left (−r), depth z up.
 *  designs: [{profile: {h: [[z, r]...], v: [...], kind}, color, label, filled}]. Section outlines
 *  (kind 'section') are drawn as closed shapes; node clouds (kind 'nodes') as small dots. */
/**
 * Complete a symmetry-reduced mouth ring for display. The mesh payload is a QUARTER (quadrants
 * "1"), a HALF, or already FULL, and the frames payload does not always say which — so decide
 * from the points themselves: an arc living in one quadrant is mirrored into all four (order
 * preserved, so the drawn ring never self-intersects); a ring spanning one axis is mirrored
 * across that axis; a ring already spanning both axes is returned untouched. Pure. Used by the
 * evolution front view and the typology sandbox.
 */
export function mirrorRing(pts) {
  const p = (pts || []).filter(q => Array.isArray(q) && q.length >= 2 && isFinite(q[0]) && isFinite(q[1]));
  if (p.length < 2) return p;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const [x, y] of p) {
    minX = Math.min(minX, x); maxX = Math.max(maxX, x);
    minY = Math.min(minY, y); maxY = Math.max(maxY, y);
  }
  const eps = 1e-6 * Math.max(1, Math.abs(maxX), Math.abs(minX), Math.abs(maxY), Math.abs(minY));
  const spansX = minX < -eps && maxX > eps, spansY = minY < -eps && maxY > eps;
  if (spansX && spansY) return p;                                        // already a full ring
  const rev = a => a.slice().reverse();
  if (spansX) return p.concat(rev(p).map(([x, y]) => [x, -y]));          // half: mirror across x
  if (spansY) return p.concat(rev(p).map(([x, y]) => [-x, y]));          // half: mirror across y
  // quarter arc -> closed ring around all four quadrants, traversed CCW
  return p
    .concat(rev(p).map(([x, y]) => [-x, y]))
    .concat(p.map(([x, y]) => [-x, -y]))
    .concat(rev(p).map(([x, y]) => [x, -y]));
}

export function wallSection(svg, designs, { H = 300, compact = false, extent = null } = {}) {
  svg.innerHTML = "";
  const W = measuredWidth(svg, compact ? 150 : 460);
  const m = compact ? { l: 4, r: 4, t: 4, b: 4 } : { l: 46, r: 10, t: 10, b: 34 };
  let rmax = 1, z0 = Infinity, z1 = -Infinity;
  for (const d of designs) for (const k of ["h", "v"]) for (const [z, r] of (d.profile?.[k] || [])) {
    rmax = Math.max(rmax, Math.abs(r)); z0 = Math.min(z0, z); z1 = Math.max(z1, z);
  }
  if (extent) ({ rmax, z0, z1 } = extent);              // shared scale across several drawings
  if (!isFinite(z0)) { svg.setAttribute("viewBox", `0 0 ${W} ${H}`); return; }
  const pw = W - m.l - m.r, ph = H - m.t - m.b;
  const noDash = W < 260;                               // dashed strokes read as texture mush below 260px
  const sc = Math.min(pw / (2 * rmax * 1.02), ph / ((z1 - z0) * 1.02));        // equal mm per pixel, true aspect
  const cx = m.l + pw / 2, by = m.t + ph - (ph - (z1 - z0) * sc) / 2;
  const X = r => cx + r * sc, Y = z => by - (z - z0) * sc;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";
  const outline = (d, k, sgn) => {
    const pts = (d.profile || {})[k] || [];
    if (pts.length < 3) return null;
    return pts.map(([z, r], i) => (i ? "L" : "M") + X(sgn * r).toFixed(1) + "," + Y(z).toFixed(1)).join("") + "Z";
  };

  // pass 1: grid, ticks, axis labels, centerline
  if (!compact) {
    const g = el("g", { class: "grid" }, svg);
    for (const t of niceTicks(-rmax, rmax, 6)) {
      el("line", { x1: X(t), x2: X(t), y1: m.t, y2: m.t + ph }, g);
      const tt = el("text", { x: X(t), y: m.t + ph + 14, "text-anchor": "middle" }, svg); tt.textContent = Math.abs(t);
    }
    for (const t of niceTicks(z0, z1, 4)) {
      el("line", { x1: m.l, x2: m.l + pw, y1: Y(t), y2: Y(t) }, g);
      const tt = el("text", { x: m.l - 5, y: Y(t) + 3, "text-anchor": "end" }, svg); tt.textContent = t;
    }
    // plane labels live in the true-aspect slack beside the drawing, at mid-height
    const a = el("text", { x: W - m.r, y: m.t + ph / 2, "text-anchor": "end" }, svg); a.textContent = "horizontal plane →";
    const b = el("text", { x: m.l + 2, y: m.t + ph / 2, "text-anchor": "start" }, svg); b.textContent = "← vertical plane";
    const c = el("text", { x: 2, y: m.t + 2, "dominant-baseline": "hanging" }, svg); c.textContent = "depth z (mm)";
  }
  if (W >= 200) el("line", { x1: cx, x2: cx, y1: m.t, y2: m.t + ph, stroke: css("--label"),
                             "stroke-dasharray": "3 3", "stroke-opacity": 0.6, "stroke-width": 1 }, svg);

  // pass 2: ALL fills beneath every stroke; even-odd fills the wall band, bore stays background
  for (const d of designs) {
    if (!d.filled || (d.profile || {}).kind !== "section") continue;
    for (const [k, sgn] of [["h", 1], ["v", -1]]) {
      const path = outline(d, k, sgn);
      if (!path) continue;
      el("path", { d: path, fill: d.color, "fill-rule": "evenodd", "fill-opacity": compact ? 0.32 : 0.30, stroke: "none" }, svg);
    }
  }

  // pass 3: strokes, with the dashed (start) outline LAST so it reads over any fill
  const drawStroke = d => {
    const p = d.profile || {};
    for (const [k, sgn] of [["h", 1], ["v", -1]]) {
      const pts = p[k] || [];
      if (!pts.length) continue;
      if (p.kind === "section") {
        const path = outline(d, k, sgn);
        if (!path) continue;
        // H solid / V dashed on the drawing itself; a design-level dash (start) dashes both planes
        const dash = (!noDash && (d.dash || k === "v")) ? "6 4" : "none";
        el("path", { d: path, fill: "none", stroke: d.color,
                     "stroke-width": compact ? 1.6 : (k === "h" ? 2.25 : 2.0),
                     "stroke-dasharray": dash, "stroke-linejoin": "round" }, svg);
      } else {
        for (const [z, r] of pts) el("circle", { cx: X(sgn * r), cy: Y(z), r: compact ? 0.8 : 1.4, fill: d.color, opacity: 0.7 }, svg);
      }
    }
  };
  const dashed = designs.filter(d => d.dash), solid = designs.filter(d => !d.dash);
  for (const d of solid) drawStroke(d);
  for (const d of dashed) drawStroke(d);

  // throat landmark: the outline's min-z point with |r| > 0 (the aperture's axis end); else min z
  for (const d of designs) {
    const p = d.profile || {};
    for (const [k, sgn] of [["h", 1], ["v", -1]]) {
      const pts = p[k] || [];
      if (!pts.length) continue;
      const withR = pts.filter(pt => pt[1] != null && Math.abs(pt[1]) > 1e-9);
      const pool = withR.length ? withR : pts;
      let tz = pool[0][0], tr = pool[0][1];
      for (const [z, r] of pool) if (z < tz) { tz = z; tr = r; }
      el("circle", { cx: X(sgn * Math.abs(tr)), cy: Y(tz), r: compact ? 1.5 : 2.5, fill: d.color, stroke: "none" }, svg);
    }
  }
}

// ── Isobar (directivity) plot in the Boundary Lab style ───────────────────────────────────────────
// Frequency on a log x-axis, angle on y, level relative to on-axis in DISCRETE 3 dB colour bands from
// -30 to 0 dB (10 bands, navy -> dark red), white contour lines every 3 dB (-6 dB drawn heavier: the
// beamwidth edge), a labelled colour bar, and a hover crosshair that reads frequency / angle / dB.
export const ISOBAR_COLORS = ["#00008F", "#0000FF", "#006FFF", "#00DFFF", "#4FFFBF",
                              "#BFFF4F", "#FFDF00", "#FF6F00", "#FF0000", "#8F0000"];
export const ISOBAR_MIN = -30, ISOBAR_MAX = 0, ISOBAR_STEP = 3;

function bandColor(v) {
  const n = ISOBAR_COLORS.length;
  const t = (Math.min(Math.max(v, ISOBAR_MIN), ISOBAR_MAX - 1e-9) - ISOBAR_MIN) / (ISOBAR_MAX - ISOBAR_MIN);
  return ISOBAR_COLORS[Math.min(n - 1, Math.floor(t * n))];
}
function hexRgb(h) { const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; }

/** Bilinear sample of rows[fi][ai] at fractional indices (fi, ai). */
function sample(rows, fi, ai) {
  const f0 = Math.max(0, Math.min(rows.length - 1, Math.floor(fi))), f1 = Math.min(rows.length - 1, f0 + 1);
  const a0 = Math.max(0, Math.min(rows[0].length - 1, Math.floor(ai))), a1 = Math.min(rows[0].length - 1, a0 + 1);
  const tf = fi - f0, ta = ai - a0;
  const g = (f, a) => { const v = rows[f][a]; return v == null ? ISOBAR_MIN - 10 : v; };
  return (g(f0, a0) * (1 - ta) + g(f0, a1) * ta) * (1 - tf) + (g(f1, a0) * (1 - ta) + g(f1, a1) * ta) * tf;
}

// Marching-squares segment table: which cell edges a contour crosses for each corner pattern.
const MS = { 1: ["l", "t"], 2: ["t", "r"], 3: ["l", "r"], 4: ["r", "b"], 5: ["l", "t", "r", "b"], 6: ["t", "b"], 7: ["l", "b"],
             8: ["l", "b"], 9: ["t", "b"], 10: ["t", "r", "l", "b"], 11: ["r", "b"], 12: ["l", "r"], 13: ["t", "r"], 14: ["l", "t"] };

export function isobarMap(svg, rows, angles, freqs, { H = 300, title = "", angleTicks = null, xlim, f0 } = {}) {
  svg.innerHTML = "";
  if (!rows || !rows.length || !angles || !angles.length || !freqs || freqs.length < 2) return;
  const W = measuredWidth(svg, 520);
  const m = { l: 46, r: 64, t: title ? 22 : 10, b: 34 };
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";
  const pw = W - m.l - m.r, ph = H - m.t - m.b;
  // Axis domain: the brief-band union when supplied; otherwise the solved grid. Invalid/zero
  // values fall back to the data domain, never to a guessed range.
  const dataLo = Number(freqs[0]), dataHi = Number(freqs[freqs.length - 1]);
  let dLo = dataLo, dHi = dataHi;
  if (Array.isArray(xlim) && xlim.length >= 2) {
    const a = Number(xlim[0]), b = Number(xlim[1]);
    if (isFinite(a) && isFinite(b) && a > 0 && b > 0 && b > a) { dLo = a; dHi = b; }
  }
  if (!(isFinite(dataLo) && isFinite(dataHi) && dataLo > 0 && dataHi > dataLo)) return;
  if (!(isFinite(dLo) && isFinite(dHi) && dLo > 0 && dHi > dLo)) { dLo = dataLo; dHi = dataHi; }
  const lf = freqs.map(Math.log10), lf0 = lf[0], lf1 = lf[lf.length - 1];
  const xlo = Math.log10(dLo), xhi = Math.log10(dHi);
  const a0 = angles[0], a1 = angles[angles.length - 1];
  const X = f => m.l + (Math.log10(f) - xlo) / (xhi - xlo) * pw;
  const Y = a => m.t + (a1 - a) / (a1 - a0) * ph;                     // +90 at the top
  // fractional row index of a log-frequency (rows are on the solved, log-spaced grid)
  const fIndex = l => { let i = 0; while (i < lf.length - 2 && l > lf[i + 1]) i++; return i + Math.max(0, Math.min(1, (l - lf[i]) / (lf[i + 1] - lf[i]))); };
  const aIndex = a => (a - a0) / (a1 - a0) * (angles.length - 1);
  // raster: smooth (bilinear) data shown in discrete colour bands, one canvas pixel per ~2 screen pixels
  const cw = Math.max(80, Math.round(pw / 2)), chh = Math.max(60, Math.round(ph / 2));
  const cv = document.createElement("canvas"); cv.width = cw; cv.height = chh;
  const ctx = cv.getContext("2d"), img = ctx.createImageData(cw, chh);
  const vals = new Float32Array(cw * chh);
  // Only the solved data domain carries colour; band margins stay transparent and carry a NaN
  // sentinel so marching squares skips them (never extrapolate the edge colours into the margins).
  const tol = 1e-9 * Math.max(1, Math.abs(lf0), Math.abs(lf1));
  for (let py = 0; py < chh; py++) {
    const ai = aIndex(a1 - (py + 0.5) / chh * (a1 - a0));
    for (let px = 0; px < cw; px++) {
      const lg = xlo + (px + 0.5) / cw * (xhi - xlo);
      if (lg < lf0 - tol || lg > lf1 + tol) { vals[py * cw + px] = NaN; continue; }
      const v = sample(rows, fIndex(lg), ai);
      vals[py * cw + px] = v;
      const c = hexRgb(bandColor(v)), o = (py * cw + px) * 4;
      img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  const clipId = "hl-iso-clip-" + (++_clipSeq);
  const defs = el("defs", {}, svg);
  el("rect", { x: m.l, y: m.t, width: pw, height: ph }, el("clipPath", { id: clipId }, defs));
  const clipped = el("g", { "clip-path": `url(#${clipId})` }, svg);
  el("image", { href: cv.toDataURL(), x: m.l, y: m.t, width: pw, height: ph, preserveAspectRatio: "none" }, clipped);
  // contour lines every 3 dB (marching squares on the raster grid), white as in Boundary Lab
  const sx = pw / cw, sy = ph / chh;
  for (let L = ISOBAR_MIN + ISOBAR_STEP; L < ISOBAR_MAX; L += ISOBAR_STEP) {
    let d = "";
    for (let py = 0; py < chh - 1; py++) for (let px = 0; px < cw - 1; px++) {
      const v0 = vals[py * cw + px], v1 = vals[py * cw + px + 1], v2 = vals[(py + 1) * cw + px + 1], v3 = vals[(py + 1) * cw + px];
      if (!isFinite(v0) || !isFinite(v1) || !isFinite(v2) || !isFinite(v3)) continue;   // unsolved margin cell
      const c = (v0 > L) | ((v1 > L) << 1) | ((v2 > L) << 2) | ((v3 > L) << 3);
      if (c === 0 || c === 15) continue;
      const it = (va, vb) => (L - va) / (vb - va);
      const P = { t: () => [px + it(v0, v1), py], r: () => [px + 1, py + it(v1, v2)],
                  b: () => [px + it(v3, v2), py + 1], l: () => [px, py + it(v0, v3)] };
      const segs = MS[c];
      for (let k = 0; k < segs.length; k += 2) {
        const p1 = P[segs[k]](), p2 = P[segs[k + 1]]();
        d += "M" + (m.l + (p1[0] + 0.5) * sx).toFixed(1) + "," + (m.t + (p1[1] + 0.5) * sy).toFixed(1) +
             "L" + (m.l + (p2[0] + 0.5) * sx).toFixed(1) + "," + (m.t + (p2[1] + 0.5) * sy).toFixed(1);
      }
    }
    if (d) {
      // dark halo first (under), white core second (over): the 0.55-opaque halo composites
      // ≈ 3.7:1 over #FFDF00 and the white core on it ≈ 5:1 — legible on every colormap band
      el("path", { d, fill: "none", stroke: "#10181d", "stroke-opacity": 0.55,
                   "stroke-width": L === -6 ? 3.4 : 2.6 }, clipped);
      el("path", { d, fill: "none", stroke: "#ffffff", "stroke-opacity": L === -6 ? 0.98 : 0.8,
                   "stroke-width": L === -6 ? 1.8 : 1.1 }, clipped);
    }
  }
  // grid and axes (angleTicks: optional — the balloon view passes 0..180 theta ticks over a
  // 0..180 polar-angle slice; default keeps the ±90° behaviour all other callers rely on)
  const g = el("g", {}, svg);
  for (const t of logTicks(dLo, dHi)) {
    el("line", { x1: X(t), x2: X(t), y1: m.t, y2: m.t + ph, stroke: "#808080", "stroke-opacity": 0.7, "stroke-width": 1.0 }, g);
    el("text", { x: X(t), y: m.t + ph + 14, "text-anchor": "middle" }, svg).textContent = t >= 1000 ? t / 1000 + "k" : t;
  }
  for (const a of (angleTicks || [-90, -60, -30, 0, 30, 60, 90])) {
    if (a < a0 || a > a1) continue;
    el("line", { x1: m.l, x2: m.l + pw, y1: Y(a), y2: Y(a), stroke: "#808080", "stroke-opacity": a === 0 ? 0.9 : 0.7, "stroke-width": 1.0 }, g);
    el("text", { x: m.l - 6, y: Y(a) + 3, "text-anchor": "end" }, svg).textContent = (a > 0 ? "+" : "") + a + "°";
  }
  el("rect", { x: m.l, y: m.t, width: pw, height: ph, fill: "none", stroke: css("--rule") }, svg);
  // scoring floor: dashed vertical marker inside the plot, edge-aware label at the top
  // (drawn after the grid so the marker and its halo label stay on top)
  const f0n = Number(f0);
  if (isFinite(f0n) && f0n > 0 && f0n >= dLo && f0n <= dHi) {
    const lx = X(f0n);
    el("line", { x1: lx, x2: lx, y1: m.t, y2: m.t + ph, stroke: css("--warn"),
                 "stroke-width": 1.5, "stroke-dasharray": "5 4" }, clipped);
    const anchor = (lx - m.l) < 0.12 * pw ? "start" : (lx > m.l + pw - 0.12 * pw) ? "end" : "middle";
    const dx = anchor === "start" ? 4 : anchor === "end" ? -4 : 0;
    const tt = el("text", { x: lx + dx, y: m.t + 11, "text-anchor": anchor,
      style: `fill:${css("--warn")};paint-order:stroke;stroke:${css("--surface")};stroke-width:3px;stroke-linejoin:round` }, svg);
    tt.textContent = `f0 ${Number.isInteger(f0n) ? f0n : +f0n.toFixed(1)} Hz`;
  }
  el("text", { x: m.l + pw / 2, y: H - 4, "text-anchor": "middle" }, svg).textContent = "Frequency (Hz)";
  if (title) el("text", { x: m.l, y: 14, class: "iso-title" }, svg).textContent = title;
  // colour bar: the same discrete bands, 3 dB ticks
  const bx = m.l + pw + 12, bw = 12, bandH = ph / ISOBAR_COLORS.length;
  ISOBAR_COLORS.forEach((c, i) => el("rect", { x: bx, y: m.t + ph - (i + 1) * bandH, width: bw, height: bandH + 0.5, fill: c }, svg));
  for (let L = ISOBAR_MIN; L <= ISOBAR_MAX; L += ISOBAR_STEP) {
    const y = m.t + ph - (L - ISOBAR_MIN) / (ISOBAR_MAX - ISOBAR_MIN) * ph;
    el("line", { x1: bx + bw, x2: bx + bw + 3, y1: y, y2: y, stroke: css("--muted") }, svg);
    el("text", { x: bx + bw + 5, y: y + 3 }, svg).textContent = String(L);
  }
  el("text", { x: bx, y: m.t - 3 }, svg).textContent = "dB";
  // hover crosshair with a frequency / angle / level readout (Boundary Lab has the same)
  const cross = el("g", { style: "pointer-events:none;display:none" }, svg);
  const vl = el("line", { stroke: "#fff", "stroke-width": 1, "stroke-dasharray": "3 2" }, cross);
  const hl = el("line", { stroke: "#fff", "stroke-width": 1, "stroke-dasharray": "3 2" }, cross);
  const box = el("rect", { rx: 3, fill: "rgba(0,0,0,0.78)" }, cross);
  const txt = el("text", { style: "fill:#fff;font-size:11px" }, cross);
  const hit = el("rect", { x: m.l, y: m.t, width: pw, height: ph, fill: "transparent", style: "cursor:crosshair" }, svg);
  const move = ev => {
    const r = svg.getBoundingClientRect(), k = W / r.width;
    const x = (ev.clientX - r.left) * k, y = (ev.clientY - r.top) * k;
    if (x < m.l || x > m.l + pw || y < m.t || y > m.t + ph) { cross.style.display = "none"; return; }
    const f = Math.pow(10, xlo + (x - m.l) / pw * (xhi - xlo)), a = a1 - (y - m.t) / ph * (a1 - a0);
    const lg = Math.log10(f), solved = lg >= lf0 - tol && lg <= lf1 + tol;
    const v = solved ? sample(rows, fIndex(lg), aIndex(a)) : null;
    vl.setAttribute("x1", x); vl.setAttribute("x2", x); vl.setAttribute("y1", m.t); vl.setAttribute("y2", m.t + ph);
    hl.setAttribute("x1", m.l); hl.setAttribute("x2", m.l + pw); hl.setAttribute("y1", y); hl.setAttribute("y2", y);
    txt.textContent = (f >= 1000 ? (f / 1000).toFixed(2) + " kHz" : Math.round(f) + " Hz") + " · " +
      (a >= 0 ? "+" : "") + a.toFixed(0) + "° · " +
      (solved ? (v < ISOBAR_MIN ? "below " + ISOBAR_MIN : v.toFixed(1)) + " dB" : "no solved data");
    const tx = x + 190 > m.l + pw ? x - 188 : x + 10, ty = y < m.t + 24 ? y + 22 : y - 8;
    txt.setAttribute("x", tx + 6); txt.setAttribute("y", ty);
    box.setAttribute("x", tx); box.setAttribute("y", ty - 13); box.setAttribute("width", 178); box.setAttribute("height", 18);
    cross.style.display = "";
  };
  hit.addEventListener("mousemove", move);
  hit.addEventListener("mouseleave", () => { cross.style.display = "none"; });
}
