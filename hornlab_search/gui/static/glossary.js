// glossary.js — plain-language meaning of every number the GUI shows, for a speaker designer.
// Single source for labels, units and tooltips. Definitions follow hornlab_search/objective/scalar.py,
// metrics/ and docs/BETA_SESSION_PLAN.md; keep them in sync if those change.

export const TERMS = {
  // ---- the score
  J:        { label: "Score", unit: "", short: "Lower is better",
              long: "One number that summarises how far a horn is from the brief's target: a weighted sum of the six error terms below, averaged over the scored band. 0 would be a perfect match. A failed design (does not mesh, too big, solver failure) scores 1000. Scores are only comparable between runs scored with the same brief." },
  cov:      { label: "Coverage error", unit: "", short: "Beamwidth vs target angle",
              long: "How far the −6 dB beamwidth misses the target coverage, horizontal and vertical: (1/100) × mean over frequency of (error in degrees)². 10° off everywhere in one plane ≈ 1.0." },
  rip:      { label: "Polar ripple", unit: "dB", short: "Lumpiness inside the coverage",
              long: "Standard deviation (dB) of the level across angles inside the target coverage, normalised to on-axis, H plus V, averaged over frequency. Low = smooth, even polar response." },
  di:       { label: "DI error", unit: "", short: "Directivity vs target DI",
              long: "(1/10) × mean of (DI − target DI)², DI from the full-sphere balloon. The target DI follows from the target coverage angles unless the brief sets it." },
  dislope:  { label: "DI slope error", unit: "", short: "Constant directivity?",
              long: "(slope − target slope)², slope of DI against log frequency in dB/decade. Target 0 = constant directivity across the band." },
  flat:     { label: "On-axis flatness", unit: "dB", short: "On-axis response spread",
              long: "Standard deviation (dB) of the on-axis level across the scored band. It says nothing about EQ-ability; a smooth tilt counts against it." },
  load:     { label: "Throat loading", unit: "", short: "Re Z below z_min",
              long: "Mean shortfall of the real part of the normalised throat impedance below 0.7 (an arbitrary threshold). Penalises poor acoustic loading at the low end. Off (weight 0) unless the brief turns it on." },
  penalty:  { label: "Failure penalty", unit: "", short: "1000 if the design failed", long: "Added when the design could not be meshed or solved." },

  // ---- per-frequency results
  bw:       { label: "Beamwidth (−6 dB)", unit: "°", short: "Total included angle where the level is 6 dB down",
              long: "Total angle between the two −6.02 dB points of the polar cut. It can jump where a side lobe crosses −6 dB." },
  di_db:    { label: "Directivity index", unit: "dB", short: "On-axis vs average over the sphere",
              long: "10·log10(on-axis power / mean power over a 512-point sphere). Higher = more directional." },
  on_axis:  { label: "On-axis response", unit: "dB", short: "Relative level at 2 m, mean removed",
              long: "Pressure on axis at 2 m for constant diaphragm acceleration, shown relative to its own mean. Not a calibrated SPL." },
  z_re:     { label: "Throat resistance", unit: "×ρc", short: "Re Z at the throat, normalised",
              long: "Real part of the specific acoustic impedance at the throat over ρc. Near 1 = the horn loads the driver like an infinite tube; it falls toward 0 below the horn's cut-off." },
  polar:    { label: "Directivity isobars", unit: "dB", short: "Level vs frequency and angle",
              long: "Level relative to on-axis at 2 m: frequency across (log), angle up (+90° to −90°). Colours are 3 dB bands from −30 dB (navy) to 0 dB (dark red), and white lines mark every 3 dB; the heavier white line is −6 dB, the beamwidth edge. Hover for frequency / angle / level. Values between the solved frequencies are interpolated, so narrow features between them are not shown. Same style as Boundary Lab's isobar plots." },

  // ---- search vocabulary
  knob:     { label: "Shape parameter", unit: "", short: "A number the search varies",
              long: "Each horn family is described by a few numbers (length, mouth size, flare rate, …). The search varies only these, within limits set in the config." },
  pinned:   { label: "At search limit", unit: "", short: "Best designs sit at a parameter limit",
              long: "Most of the 6 best designs are within 2 % of a parameter's lower or upper limit: the limit, not acoustics, stopped the search. Widening a limit is a deliberate decision (it changes the comparison) and needs the owner's OK." },
  rho:      { label: "Influence", unit: "", short: "Rank correlation with the score",
              long: "Spearman rank correlation between a parameter and the score across all solved designs: +1 = larger value, worse score; −1 = larger value, better score; near 0 = little effect (or a non-monotonic one)." },
  seed:     { label: "Starting design", unit: "", short: "Where the search began",
              long: "The hand-set design in the config. The search reports how much it improved on it." },
  cma_seed: { label: "Random seed", unit: "", short: "Repeat number of the search",
              long: "CMA-ES is a randomised search. Two runs with different random seeds show how repeatable a result is." },
  median:   { label: "Median score", unit: "", short: "Middle score over repeats", long: "Median of each repeat's best score." },
  spread:   { label: "Spread", unit: "", short: "Best minus worst repeat",
              long: "Max − min of the repeats' best scores. Family A beats family B only where the medians differ by more than both spreads; two repeats is a small sample." },
  tier:     { label: "Campaign tier", unit: "", short: "How much search per family",
              long: "dry-run: meshes each starting design, no solving (seconds). screen: one search per family, budget max(40, 10 × parameters) — a coarse first ranking (minutes per family). compare: two repeats, budget max(150, 25 × parameters) — needed to claim one family beats another (hours; never run it live)." },
  budget:   { label: "Budget", unit: "evaluations", short: "Designs the search may try",
              long: "Cached designs count toward a campaign's budget so families get equal search. Launch suggests max(150, 100·N) from Hansen's ~100·N hard-problem floor (c-cmaes), floored by this repo's compare tier; IPOP/BIPOP inflate by (1+max)×screen so leftover evals can fund restarts. GUI allow-list caps at 5000." },
  cma_cov:  { label: "CMA covariance", unit: "", short: "Learned search ellipsoid at the end of the run",
              long: "Snapshot of pycma's C (and σ) when the ES stopped. Describes the local shape of the objective landscape in the unit-box search coordinates — which knobs CMA still explores and which directions are coupled — not a physical variance decomposition of the acoustics." },
  cma_Cii:  { label: "Cᵢᵢ", unit: "", short: "Diagonal of the CMA covariance",
              long: "Variance CMA assigns to that knob's unit-box axis. Larger ⇒ the search distribution is still broad on that coordinate." },
  cma_std:  { label: "σ√Cᵢᵢ", unit: "unit box", short: "Sampling scale along one knob",
              long: "Effective standard deviation of new samples along that axis (step-size σ times √Cᵢᵢ). Compare across knobs: large means still exploring; small means locally collapsed — a candidate to pin in a later stage." },
  pin_plan: { label: "Pin plan", unit: "", short: "Which knobs to freeze from CMA + Spearman",
              long: "Recommendation only: pin when σ√Cᵢᵢ share and std are both small, unless |Spearman ρ| is high (still drives J). Values come from best.json. Write artifacts with hornlab-search pin-plan --run <id>; optional --write-config emits a patched YAML." },
  restarts: { label: "CMA restarts", unit: "", short: "IPOP / BIPOP after a natural stop",
              long: "When CMA-ES stops early (flat fitness / tolfun) before the budget is spent, restarts start a fresh ES on leftover evals. Off = single CMA (config default for most YAMLs). IPOP doubles population each restart. BIPOP mixes small-σ local restarts with large-pop ones. Prefer on longer budgets (compare / 150+); short screens often burn the rest in one restart." },
  restarts_max: { label: "Max restarts", unit: "", short: "How many fresh ES instances after the first",
              long: "Number of restarts after the initial CMA run (0–64). Total ES instances ≤ 1 + max. Shared across the whole budget — not per stage." },
  failures: { label: "Failures", unit: "", short: "Designs that could not be scored",
              long: "invalid_geometry: the shape is impossible or outside the brief's size envelope (costs mesh time only). mesh_too_large: too many elements for the 8 GB GPU. solve_failed: the solver crashed (rare; not the design's fault)." },
  epw:      { label: "Mesh density", unit: "elements per wavelength", short: "Mesh resolution",
              long: "Elements per wavelength at the top scored frequency. Axisymmetric typologies use 8 (checked against 6: within 0.12 dB DI), H/V horns use 6 (within 0.05 dB)." },
  dims:     { label: "Horn size", unit: "mm", short: "Outer mouth width × height × depth",
              long: "From the solved mesh, outer surface including the 3–6 mm shell. Depth runs from the throat to the mouth plane." },
  lock:     { label: "GPU lock", unit: "", short: "Who is using the GPU",
              long: "Only one GPU job runs at a time. Any other GPU command is refused with 'GPU busy' until the holder finishes." },
  julia:    { label: "Solver hosts", unit: "", short: "Background solver processes",
              long: "The GPU solver runs in Julia worker processes. 1–2 while a job runs is normal; any left after all jobs end hold GPU memory: use gpu-clean." },
  band:     { label: "Scored band", unit: "Hz", short: "Frequencies that count",
              long: "Only frequencies inside the band enter the score. On an 8 GB GPU nothing above 5.5 kHz is solved." },
};

/** HTML for a label with a hover/focus tooltip, e.g. tip("cov"). */
export function tip(key, labelOverride) {
  const t = TERMS[key];
  if (!t) return labelOverride ?? key;
  const label = labelOverride ?? t.label;
  const title = `${t.label}${t.unit ? " [" + t.unit + "]" : ""}: ${t.long}`.replace(/"/g, "&quot;");
  return `<span class="term" tabindex="0" title="${title}">${label}</span>`;
}

/** Order and labels of the objective terms, for tables and bar charts. */
export const TERM_ORDER = ["cov", "rip", "di", "dislope", "flat", "load"];
