# Next development round: priorities (after the beta)

Written 2026-10-22 22:35 EDT by the local orchestrator, at the user's request. **Read this before planning any work
after the beta session.** Items are in priority order. Background: `docs/HIGH_FREQUENCY_OPTIONS.md` (2026-10-13),
`docs/CLOUD_GPU_REPORT.md`, `TOOLCHAIN.md` M2/M3.

## P0 (added 2026-10-27 late evening, owner-directed: TOP OF THE LIST). P12 follow-through - make a high-ranked horn a horn that measures well when printed

Source: `docs/research/SENIOR_PASS_SCORING_SEARCH_REALITY_2026-10-27.md` (the plan, numbers, owner decisions s7),
`docs/DRIVER_MODEL.md`, `docs/research/THROAT_COUPLING_2026-10-27.md`. Built this evening (report-only, zero GPU):
horn loudness readout, compression-driver model, round-throat check, `tools/loudness_report.py`. Rules that still
bind: no pytest solver tests / GPU / Julia while a night runs; scoring and brief changes need the owner's approval;
do not edit configs a running night uses.

**Owner inputs needed first (block the items marked [owner]):**
- [ ] [owner] **Driver list per brief** and use case (tube-amp hi-fi / PA / both); fill `examples/drivers/<maker>_<model>.yaml`
  from datasheets (URL in `source`, dry moving mass Mmd, published sensitivity + condition) - template `examples/drivers/_template.yaml`.
- [ ] [owner] **Gate levels:** sensitivity floor at 1 W / 1 m for tube-amp hi-fi briefs; maximum-SPL target for PA briefs.
- [ ] [owner] **Scoring decisions** (senior pass s2): output-at-f0 term in dB (worst case from 0.95 f0, 3 dB = one unit,
  weight 1.0 PA / 0.5 hi-fi); stricter pattern scoring for hi-fi only for now (cov tolerance 2 -> 1, presence band 3x,
  one-sided below f0); score at 10 m; half weight above the driver's f11.
- [ ] [owner] **Woofer system block** per brief: woofer size, crossover, mouth-over-woofer overlap allowed (s1.5, s2.3).
- [x] **Decided 2026-10-27: no separate throat adapter; only the driver coupling plane must be round at the exit size;**
  morph / ridges / non-round shapes are allowed right after it (confirmed by the outside research).

**Do next (in order):**
1. [ ] **Throat rule in the configs (next night's copies only):** lock `aspect_ratio = 1` in every OSSE / R-OSSE cell
   (it stretches the coupling plane: 24x36, 26x36, 41x36, 50x36 mm measured on 36 mm briefs) and shape the mouth with the
   morph. After the night: pre-mesh refusal of a non-round or wrong-size coupling plane (`search/evaluate.py`, using
   `mesh/throat_check.py`). Optional fork change: an aspect ramp from 1 at the throat. Then measure how fast the horn
   may leave round with a small `morph_fixed` sweep (research gives no number; 20-30 % of length is a guess to test).
2. [ ] **Calibration night** (~3-4 h, first GPU job after the ripple/ridge night), on 6 stored finalists: band-split
   screen vs single mesh (accept: Re z +-0.03, beamwidth +-2 deg, DI +-0.2 dB); 10 m vs 2 m; epw 6 vs 9 in 2.5-5.5 kHz;
   verify grid on the top 5 per brief - does the screen ranking survive?
3. [ ] **New screen grid** (after 2 passes): band split at 2 kHz; low band adds 0.7 f0 .. f0 (~6 points/octave);
   ~7 points in 2.5-5.5 kHz instead of 3 (a coarse grid missed the narrowest beam there by up to 12 deg); estimated
   ~0.9x today's time per design. Settle grid, distance and mesh BEFORE big nights - they are the only things that
   invalidate the solve cache.
4. [ ] **Search changes:** budget counts valid solves only (refusals are 23 % of every budget today); reduced knobs +
   two stages (1-4 knobs carry ~80 % of J; lock table s3.2); successive halving per brief; on the 400-600 Hz PA briefs
   move budget to loading-capable families (Le Cleac'h, ATH core law, hypex hybrids, salmon-X) - 1.4" OS-type throats
   cannot load there (cone rule, s1.1); seeds from physics + the re-ranked stored designs; lq-CMA-ES A/B on 1-2 cells.
5. [ ] **Gates, not weights, for "does it work"** (s6): round coupling plane, woofer spacing, output at f0, and per
   use case sensitivity (hi-fi) or max SPL (PA) on at least one listed driver. Pattern stays the score.
6. [ ] **Organic galleries:** CMA-ME with shape axes (mouth non-roundness, ridge/flute amplitude, azimuthal lobing,
   depth) so each organic family returns the best design per "look", all passing the gates.
7. [ ] **Plumbing after the night:** `hornlab-search report --driver <yaml>` (needs `cli.py`); run
   `tests/test_report_html.py` and the full offline suite; optional loudness columns in `tools/export_campaign_tables.py`.
8. [ ] **Reality:** validate the driver model against each driver's published sensitivity; run one published measured
   horn through the pipeline (P12b; accept beamwidth +-5 deg, +-3 deg in the presence band, DI +-1 dB); print a small
   hi-fi horn first, then today's PA winner and the loading-aware winner for one brief; measure free-standing, rotating
   about the throat plane, mic at 2 m (senior pass s5), plus the driver's electrical impedance on the horn.

## P1 (top priority). Fused / direct CUDA Burton-Miller assembly in the exterior driver

**Why it matters.** The 8 GB RTX 4060 runs out of memory between 8.9k (works, 74 s per frequency under memory
pressure) and 15.7k (OOM) quarter-domain dofs (`TOOLCHAIN.md` M2). That ceiling, not the card, is what holds screening
at 5.5 kHz for large horns. The solver already has a memory-saving path that forms the Burton-Miller combination in
one matrix (about 6x less operator memory), but it is switched off for CUDA. Turning on an equivalent for CUDA should
lift the ceiling to about 20k quarter dofs [inferred], i.e. about 12.6 kHz at epw 6 even on the large OSSE seed, and
make 7k–9k-dof solves much faster (less memory pressure).

**Evidence (pinned `hornlab_beat_bem` 0.2.0, installed under `.venv\Lib\site-packages\hornlab_beat_bem`).**
- `julia/BeatEngineDriver.jl` ~line 1215: `fused_burton_miller = beat_backend in (:cpu, :metal) && near_selection
  === nothing && ...` — the fused path is CPU and Metal only.
- A CUDA single-matrix assembler exists: `julia/src/BeatEngineCudaBurtonMiller.jl:350`,
  `assemble_burton_miller_neumann_system_cuda` (re-exported in `julia/src/BeatEngineCore.jl:85, 1357`). Only
  `julia/tests/runtests.jl` (lines ~1214, ~1300) calls it; the exterior driver never does.
- The package states its CUDA path was never run by its authors (no NVIDIA hardware); our 4060 is its only
  real-world validation. `hornlab_beat_bem/config.py` also documents a CUDA-specific silent-error hazard (single
  image-near cache under multi-image symmetry), so CUDA changes need extra care.

**It is NOT a flag flip.** Adding `:cuda` to that condition routes into the fused pair-kernel path, which is not the
CUDA assembler. The work is to call the CUDA direct-system assembler from the exterior driver and make sure it:
1. handles our quarter-domain symmetry images (`yz+xz`) exactly as the current CUDA path does;
2. applies the same singular corrections (near-correction stays refused on CUDA, as today);
3. keeps the same excitation (unit acceleration on tag 2) and output conventions (exp(−iωt));
4. keeps the per-frequency call pattern our adapter uses (`solve/beat.py`, TOOLCHAIN M3).

**Ownership (updated 2026-10-24, owner decision).** We do this ourselves in our pinned fork of `hornlab-beat-bem`
(`C:\Users\hunte\Hrns\forks\hornlab-beat-bem`, branch `hornlab-search/fused-cuda`), following `docs/FORKS.md`;
`doctor`'s pin check already accepts fork URLs. Offering the change upstream to Magnus is still welcome, but we do not
wait for it. Exact patch plan: `docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md` WP15. Finding from
the 2026-10-24 read: the CUDA direct assembler already handles symmetry images (`symmetry_image_transforms`, image
singular cache, orbit row weights) and is tested against the 4-operator path on `sample_quarter.msh` in
`julia/tests/runtests.jl`, so the work is mostly driver wiring.
~~(a) ask Magnus … (b) with his OK, a pinned fork …~~ (superseded).

**Validation before any data from it counts (all on the GPU, from a clean state).**
1. `hornlab-search selftest --analytic`: spread ≤ 0.5 dB (today 0.020 dB).
2. `hornlab-search selftest --crosscheck` vs `bempp_cpu`: < 0.2 dB (frozen CP-7b rule; today 0.039 dB).
3. A/B against today's CUDA path on the same meshes (osse_axi seed, perturbed_osse_hv best, freeform_sculpt seed):
   `hornlab-search compare` within the 0.039 dB noise floor and ≤ 1° beamwidth.
4. Memory ceiling re-measured as in `TOOLCHAIN.md` M2 (VRAM baseline recorded, one solve per fresh process).
5. Records carry the new library SHA, so old and new solver data never mix silently (`lib_shas` filter).

**Decision recorded 2026-10-22.** The overnight queue of 2026-10-22/23 (epw-8 screen, compare tier, OSSE top-up,
sculpt searches) stays on the current verified CUDA path, so the compare tier and the surrogate data come from one
solver. Do not enable P1 mid-campaign.

## P2. High-frequency finalist pass at 12 kHz on the 4060 (no solver change)

Typology horns are small: measured 700–1,400 quarter dofs at 5.5 kHz, so about 3.3k–6.8k at 12 kHz (dofs scale with
f²), inside the 8.9k ceiling. Add 12 kHz briefs and a `verify` pass for the top designs only (about 1–5 min per
design). Prerequisite: the epw-convergence check above 2.5 kHz (`docs/HANDOFF_BETA.md` item C2; the overnight queue's
epw-8 screen feeds it). Physics caveat for every report: above the throat's first cross mode (about 7.9 kHz for a
1-inch exit) a real compression driver is not a uniform cap, so 8–12 kHz results compare geometries, not drivers.
A 12 kHz brief is a separate frequency grid: its records form their own group (already kept apart by the grid check).

## P3. Apple Silicon (Metal) backend for the collaborator's MacBook

`hornlab_beat_bem` supports `metal` (`config.py` `BEAT_BACKENDS`), with the fused path ON, and unified memory holds
dense systems far beyond 8 GB. Our layer only exposes `beat_cuda`, `beat_cpu`, `bempp_cpu`: add a `beat_metal`
backend option, macOS process hygiene (`search/hygiene.py` POSIX branch), then on the Mac: `doctor`, both selftests,
and the same 3-design A/B against the 4060 (< 0.2 dB) before mixing data. Metal has no near-correction (same as CUDA
under symmetry).

## P4 (IDEA, recorded 2026-10-24, owner decision required — not approved for work). Frequency-grid density and a narrow-resonance "safety net"

**Why it matters.** The screen grid is 12 log-spaced points from 500 Hz to the brief's band top (~5.5 kHz on this
card); verify is 25 log points (300 Hz–12 kHz). A narrow-band horn defect (a mouth-reflection resonance, an
organ-pipe/quarter-wave mode, a narrow cancellation or dispersion spike — e.g. a collapse at 550 Hz) that is
NARROWER than the grid gap (about 1/3 octave on screen) can fall entirely BETWEEN two solved frequencies. Nothing
is simulated between grid points: the plotted polar/beamwidth curves are interpolations that render smoothly
straight through the defect, and the objective cannot score what was never solved. A horn whose narrow defect
hides between grid points can therefore OUTRANK an equally good clean horn whose defect happens to land on a grid
point. This is the one accuracy hazard a designer most plausibly cares about.

**Existing partial mitigations (already in the repo; do not re-derive):** WP4 (landed 2026-10-24) added
`grid: {verify_points_per_octave: N}` (denser VERIFY grid above 5 kHz only) and objective-v2 `freq_weights`
(rewrites the importance of points the grid already solves — neither adds new solved frequencies on screen);
`f11` and `z_ripple` markers exist but are sampled at the same sparse points; `docs/research/
TIME_DOMAIN_RINGING.md` covers the time-domain alternative.

**Sub-idea P4a — dense finalist resonance net (recommended first; no contract change).** After screen/verify,
take the short-listed finalists ONLY and re-solve each on a dense uniform in-band grid (e.g. 24–48 in-band
points, or the WP4 8-points-per-octave pattern extended over the whole band) as a flagged resonance check. Diff
the dense-grid beamwidth/ripple/on-axis/DI against the sparse-grid values: a large diff means a narrow feature
the coarse grid missed. Cost is bounded (seconds-to-a-minute per design, a handful of designs). Could also auto-
flag horn FAMILIES whose dense J degrades vs their screen J, so the search brief for that family can be weighted
or the grid refined locally. Fits the existing `verify --brief`-style run-dir seam.

**Sub-idea P4b — perceptually weighted non-uniform frequencies (idea only; FROZEN-CONTRACT matter).** Instead of
even log spacing, add extra solved points in the regions most problematic to human hearing — roughly 2–3 kHz
(maximum hearing sensitivity / harshness region), the 4–5.5 kHz transition where beamwidth and harshness
concentrate, and possibly the 0.5–1 kHz mouth-reflection onset region — at the cost of points somewhere broad and
predictable. IMPORTANT constraint (01_CONTRACTS §8 is FROZEN; senior ruling 2026-10-13 declined per-user YAML
grid keys): a changed grid changes the solve hash and creates a RECORD GROUP that cannot train or cache with the
existing grids (`to_training_arrays` drops grid mismatches). The only clean path is a owner-approved contract
amendment that defines the non-uniform grid as a NEW NAMED grid group (the `*_12k` brief / WP4 `verify_hf`
pattern), with its exact point list fixed in the contract so every record in the group shares it.

Both sub-ideas are recorded so they are not lost; neither is scheduled. P4a is cheap and self-contained; P4b
should ride the next contract revision window if wanted at all.

## P5 (added 2026-10-24 late, owner-approved after the M2 pass): easy wins for BUILD-DECISION accuracy/value — NOT in the WP plan

**The lens (owner):** "less concerned about outright speed — the tool should actually guide which horn designs to
build in real life." Ranked by value per effort. None of these exist in `04_IMPLEMENTATION_PLAN.md`; none
replace it. GPU cost is small everywhere; W1 is free.

- [ ] **W1 — screen-vs-verify rank-consistency audit (offline, ZERO GPU; do first).** The search loop trusts the
  12-point screen tier to pick finalists; verify (25 points, more dofs) re-scores survivors. Every stored campaign
  already holds BOTH scores (dataset + runs/) — compute per campaign/family the rank agreement (winner agreement +
  the dB/dof gap at every rank flip). Deliverable: `tools/rank_audit/` (the rescore_v2 pattern) + a small evidence
  doc. Answers: how much to trust a screen ranking before spending verify GPU, and where search budget is
  misallocated.
- [ ] **W2 — the dense finalist resonance net = P4a above (tiny GPU).** Before committing to BUILD: re-solve the
  top 3–5 finalists only, on a dense uniform in-band grid (~24–48 points), and diff beamwidth/ripple/on-axis/DI
  vs the sparse-grid values — a large diff means a narrow feature the grid missed (the plotting interpolates
  straight through it). Minutes per design on the fused path. Scheduling note: fold into the brief-design pass as
  the build-gate on its POC winner (its handoff already plans one fused 12 kHz verify; this rides the same job
  family with the owner's go).
- [ ] **W3 — denser screen grid as a NEW NAMED grid group (small code; OWNER-GATED contract matter).** +4 screen
  points (12→16) ≈ +33 % screen time (small at today's sizes) with better beamwidth/ripple fidelity on exactly
  the decision-bearing frequencies. Frozen-contract rule (P4b's reasoning applies to screen too): a changed grid
  must land as a NEW NAMED grid group (the `*_12k`-brief / WP4 `verify_hf` pattern) with its exact point list
  fixed in the contract; needs the owner's OK in a contract-revision window.
- [ ] **W4 — `compare --bar` judge mode (mechanical, ~20 lines).** `hornlab-search compare` prints diff tables but
  never judges; every fork validation ladder eyeballs them. A `--bar` flag that exits nonzero when the CP-7f bars
  (0.039 dB / 1 deg) are crossed removes a recurring human-error surface (hit three times in the M2 pass); offline
  tests only.
- [ ] **W5 — perceptual/frequency emphasis via the LANDED v2 `freq_weights` (configuration only, zero code).** When
  real owner briefs exist (the brief-design pass), set weight where perception lives (roughly 2–5 kHz: beamwidth
  and harshness) and down-weight broad, predictable regions — the machinery is already built for exactly this
  (WP4). Also record the M3/WP5 calibration outcomes (distance_m, screen balloon, source_motion) as adopted
  baseline defaults with owner sign-off (`docs/HANDOFF_BRIEF_DESIGN_2026-10-24.md` plans this).

Suggested homes: W1 + W2 + W5 → the brief-design pass (its deliverables are exactly the baseline-settings doc and
the POC build-gate); W4 → any small offline commit (e.g. alongside the in-flight M3/M4 lanes); W3 → the next
contract-revision window or skip.

- [ ] **W6 — a Boundary Lab-class balloon view in the GUI (designer lane, no GPU).** Owner showed BL's Balloon
  Plot (2026-10-24): a smooth continuously-shaded 3D sphere colored by normalized SPL (0 → −30 dB) with white
  isobar rings ON the surface, labeled On-Axis/Horizontal/Vertical axes + a measurement-domain wireframe; a
  "radar slicer" (angle slider → polar cut at any azimuth/frequency); and a smooth log-frequency × angle
  (±180°) filled-contour slice. **Recon of BL's actual source (GitHub, done 2026-10-24):** the balloon is NOT a
  textured sphere — it is a **dB-to-radius BLOB** (radius = max(spl − floor, 0); shape AND color both encode
  level), PyVista/VTK `smooth_shading` + turbo, isobars = tubed white contour rings offset ~0.2 % of extent,
  radar slicer = barycentric interpolation along a great-circle meridian, isobar slice = fractional-octave
  smoothed + resampled freq×angle heatmap. Port of the DESIGN into our web GUI (three.js r160, vanilla JS) is
  the implementation (designer lane dispatched); GPL attribution carried. We solve and STORE the full balloon
  per design already (`response.npz`: `spl_balloon_db` + `balloon_grid`/`balloon_layout` + the sin-θ weighting
  note) — a viewer is a rendering feature, not new computation. Prerequisite chain: data density first —
  M3/WP5's running 512→1024→2592 ΔDI check decides the verify-balloon upgrade; note the sin(θ) unequal-area
  layout when shading (interpolate on the sphere, not the index grid).

- [ ] **W7 — denser balloons + denser frequency grids on higher-tier runs (owner priority, 2026-10-25; research basis: `12_RESEARCH_BASIS.md` §12).** Raise verify/final-tier data density toward BL-class fidelity (`balloon_angle_precision_deg` 2.5° ⇒ equal-area Fibonacci count `round(41253/angle²)` ≈ **6 600 points** at BL defaults; `freq_count` **41 log-spaced** 200–20 kHz): targets (a) `solve.balloon_points_verify` from the current 512→1024→2592 ladder into the **1 000–6 600** range, (b) verify-solve frequency count from **25** toward **~41 log-spaced** (via `grid.verify_points_per_octave` / a denser verify grid group — a NEW named grid group per the W3 contract rule if it changes the solve-spec hash). Gates: the M3/WP5 measured ΔDI ladder (512→1024→2592) decides how much balloon density actually buys accuracy; GPU cost — balloon points bill field evaluation (not dofs), freq count bills linearly per solve; stays OFF the 8 GB 4060 search tiers (screen keeps 12 freqs / light balloon). Feeds the W6 web Balloon view (its sin(θ) unequal-area interpolation note applies at any density).

## P6 (added 2026-10-25, PROPOSALS from the collaborator conversation — owner decision required; **FULL IMPLEMENTATION PLAN v1.0 written 2026-10-25: `docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md`** — research basis §2, settled decisions §3 (D1–D20), work packages §4, waves + verbatim dispatch prompts §5, checkpoints §6; execution gates: WP1–WP17 complete + owner GO; research basis summarized in `docs/plan/12_RESEARCH_BASIS.md` §11)

- [ ] **P6a — featured superformula (guiding-curve) search campaign (config-only; realizes the plan README's frozen quick-fork #2).** The OSSE guiding-curve superformula keys (`gcurve_type: 2`, `gcurve_sf_a/b/m1/m2/n1..n3`, `gcurve_se_n`) are mesher-native AND already searchable design-space rows (`design/families.py` gcurve section; `tests/test_design_families.py` "table rows"); superellipse exponents are searched today (`rosse_baseline` 2–8, `freeform_sculpt`). Missing: a catalog family + `examples/` config that SEARCHES the SF knobs, bounds anchored to a verified Ath reference case (a User Guide `GCurve.SF` example or the ATH CORE `sf()` wall-angle script), then one screen-tier campaign. Grounding (typology-research minimum bar): Gielis 2003 + the Ath User Guide — R9 satisfied; `12_RESEARCH_BASIS.md` §11 is the dossier. Cost: config + one screen campaign. Value: star/organic/azimuthally-varying mouth shapes no current config expresses.
- [ ] **P6b — GSA vs CMA-ES bake-off (owner-gated experiment; NOT scheduled, NOT in any WP).** No published head-to-head exists (`12_RESEARCH_BASIS.md` §11.5); CMA-ES stays the default regardless of outcome; WP11 restarts + CMA-ME atlas remain the scheduled search upgrades. If run: fixed EVALUATION budget (200–400 sims, NOT iterations), identical bounds/graded penalties/initial seed, 5–10 repeats, Latin-hypercube/random baseline, report best-so-far + median per budget; cheapest on the 2-knob exponential family, or after the metric surrogate makes evaluations ~ms (§11.5 protocol).

## P8 (added 2026-10-25, owner-directed: "why did those shapes never show up in my passes — investigate, record, and set up the next investigation"). The puckered/figure-8/bullet outline class as a SEARCH TARGET, not a layered build

**The honest diagnosis (research basis §13.8, all measured this pass):** the machinery for those shapes has been
in the search layer (the per-azimuth stop/fc laws, the G8/G9 harmonics, the x-amp; the signed-x/one-sided-eps/
mouth-ripple families landed 2026-10-25) — but the owner's passes could never SEE them rewarded, for three
stacking reasons: (a) the coverage objective was an equal-weight mean over the screen band whose low half is
physically uncontrollable in the envelope (61–87% of the cov loss; the v3 mask + the K-law feasibility preflight
fix this); (b) `dislope`'s slope-0 target fought coverage for 30–42% of J; (c) no objective term ever read the
DIAGONAL directions (45/135 deg) where the figure-8/puckered outlines do their work — the balloon data stores
them already. Also every shipped typology seed sat at x_amp/bend/ripple = 0 with tight bounds, so short runs
(sample lottery) started and stayed smooth.

**Owner direction recorded: no extra "layers" required — one-run CMA-ES search with fixed objectives/bounds is
the model; the collaborator's staged-gene plan is an OPTIONAL refinement (two sequentially-seeded campaigns;
the seeds machinery exists), not a requirement.**

- [ ] **P8a — the pucker-hunting demo campaign** (gated on the v3/derivation machinery landed 2026-10-25):
  the campaign configs whose seeds/bounds AIM at the figure-8/bullet outline class (the signed-x/eps/ripple
  families + the harmonic laws), verified first by the GPU smoke, then one compare-tier pair (smooth parent vs
  puckered family) to SEE the difference the class makes in OUR scoring.
- [ ] **P8b — the diagonal-consistency objective term** (45/135-balloon vs H/V; no new solves; owner decision
  pending from the 2026-10-25 gate) — the only scoring change that can DIRECTLY reward the class.
- [ ] **P8c — the Tritonia-law rows kind** (the published alpha(theta) power laws = 12_RESEARCH_BASIS §13.7's
  verified formulas, amplitudes as genes) as the dedicated "pucker-discovery" geometry family; and the
  segmentizing genes (eqs 2-4, seg-horn page) as the follow-on candidate. R9: the laws are published
  (primary author); the per-azimuth assembly labels itself a reconstruction.
- [ ] **P8d — GUI: show the candidate class** — the compose wizard surfaces the new families + the
  feasibility record (§13.5/§14.4's GUI integration; designer lane).

- [ ] **W8 — per-typology search-box audit (owner-directed 2026-10-25 evening, from the run-page at-limit finding).** The owner's `perturbed_osse_hv` run under a 680×500×600 envelope showed the config's own `L_mm` box (90–140 mm) binding 4/6 best designs at its ceiling while the brief allowed 3× more depth — the knob boxes (config `bounds:`), not the brief envelopes, cap size ambition. Audit EVERY typology config's bounds against the realistic brief envelopes + the measured mesher caps, surface the over-constrained knobs (at-limit saturation across stored runs is the signal), and propose the widening table (owner-gated per config, never automatic). Guide reference: `docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md` §4 (the three-layer size-limit model). Related deferred note: the owner earlier suspected "some min/max parameters may be over-constraining" (S1A_DRIVER_PASS_ORACLE_FINAL header note).

## P9 (recorded 2026-10-25, OWNER-DIRECTED; **PROPOSAL ONLY — nothing started, no code written, no config or bound touched**). GUI parameter reference, an interactive typology sandbox, and one findable source of truth for *typology → design → formula → parameter → min/max → design characteristic → the code that implements it*

**Why it matters.** Four gaps surfaced in one sitting and they share one root cause: the parameter knowledge exists, but it is scattered across five documents and four code files with nothing joining it.

1. **No descriptions exist for the typology knobs.** A user reading `g_fc_h_hz`, `g_T`, `g_stop_deg` on a run page cannot learn what they move. Verified negative findings: `hornlab_search/gui/static/glossary.js` defines objective/metric terms only and carries **no** geometry-knob entries; `gui/static/app.js` carries labels/hints for the **brief** fields only (`coverage_h/v_deg`, `band_*`, `envelope.*`, `driver.exit_radius_mm`, `driver.exit_angle_deg`, `throat_angle_policy`). Nothing covers the typology knobs on the Run page or the Typologies page.
2. **There is no way to explore a typology's shape space by hand.** The only geometry views are read-only playback of a *finished* search (the search time-lapse page, and the run-detail shape cards whose parameter bars are status indicators, not controls). The owner wants a sandbox: drag a knob, watch the horizontal/vertical wall section and the 3D view update.
3. **Nothing joins the three typology vocabularies**, so a user or an agent must reconstruct the join from raw sources every time (table below).
4. **A live defect**: on the search time-lapse page the `3D` checkbox renders **checked** while the canvas prints `3D off — flip the 3D toggle above.` Either the checkbox's visual state is not the state the render path reads, or the render throws and reuses the off-state placeholder instead of an error state. Not yet confirmed in code (the code-map lane was still running when this was recorded) — grep the string above; it is the exact anchor.

**What already exists — do not rebuild it.** The repo already has the two authoritative parameter layers, and they are correct:

| Authority | File | Owns |
|---|---|---|
| `KeySpec` / `FAMILY_KEYS` | `design/families.py` | the mesher's legal keys, their **hard schema limits** `lo`/`hi`, one-line notes, refusal hints. `families.py:12-13` is explicit: these are **schema limits only**, never plausibility limits |
| `TYPES` / `DEFAULT_KNOBS` | `design/generators/registry.py` | the generator vocabulary (11 names), the knob defaults, and every knob read by `build_meridian`/`materialize` |
| catalog + configs | `examples/catalog.yaml`, `examples/typologies/*.yaml` | the catalog ids, seeds, and **search bounds** — `AGENTS.md` line 29: *"Every horn number is a YAML default in `examples/` — hardcoded horn numbers are bugs."* |
| research | `docs/research/typologies/MESHER_TYPOLOGIES.md`, `docs/plan/12_RESEARCH_BASIS.md`, `docs/TYPOLOGY_PLAN.md`, per-typology dossiers | the formulas and their sources |

**What is missing is the JOIN plus the human-facing text**: display label, unit, plain-language physical meaning, formula, and a symbol cross-reference to the code that reads it — and one entry point that returns all of it.

**The three-vocabulary problem — why a flat table cannot work:**

| Layer | Authority | Count | Example |
|---|---|---|---|
| mesher families | `families.FAMILY_KEYS` | 4 | `OSSE`, `R-OSSE`, `ICW`, `FREEFORM` |
| generator types | `registry.TYPES` | 11 | `lecleach`, `biradial`, `qtw_waveguide` |
| catalog typologies | `examples/catalog.yaml` | **36** (verified 2026-10-25) | `salmon_elliptical`, `lecleach_rollback` |

The Typologies page shows catalog ids; a tooltip there must resolve `salmon_elliptical → FREEFORM → grid rows → g_fc_h_hz`. A Run-page tooltip must resolve a run back to its catalog entry. Keying on **catalog id and resolving downward** is the only arrangement that does not duplicate knob facts.

**Knob names are overloaded across typologies, so a per-name lookup would emit WRONG tooltips.** Verified instances:

| Knob | Meaning A | Meaning B / C |
|---|---|---|
| `n` | OSSE superellipse termination exponent | biradial flare-rate exponent (patent claim 14, `[2,8]`) |
| `q` | OSSE termination saturation (≈0.995) | R-OSSE blend exponent (1.0) |
| `a_deg` | OSSE coverage half-angle | biradial initial-wall half-angle (its own default 25) / QTW half-dispersion angle |
| `stop_deg` vs `max_wall_deg` | — | `registry.py:37-38` already records that `spherical_salmon` uses `{p}_max_wall_deg` and **not** `{p}_stop_deg`; the R9 audit flagged it |
| `exponent` | cross-section superellipse exponent | `12_RESEARCH_BASIS.md:158` says default **2.0**; `registry.DEFAULT_KNOBS["mouth_exponent"]` ships **4.0** — an open doc/code mismatch, not for a lane to silently resolve |

**Proposed arrangement (annotate, never restate).** A new `hornlab_search/design/params/` package that *reads* the authorities above at import time and adds only the join and the prose:

- `descriptors.py` — one entry per distinct knob **name** holding shared facts (label, unit, summary ≤120 chars, detail, formula, physical effect, symbol cross-ref, doc anchor), with an explicit `contexts` sub-mapping for the overloads in the table above.
- `typologies.py` — one entry per **catalog id** (all 36, plus any config present in `examples/typologies/` but uncatalogued): family, generator type or grid kind, one-line summary, R9/source status, knob list, and per-typology overrides only where the meaning differs.
- `bounds.py` — the precedence chain for the sandbox sliders (below).
- `__init__.py` — `resolve(id)`, `knobs_for(id)`, `describe(id, knob)`, `bounds_for(id, knob)`, `all_typologies()`, `validate_metadata()`. Import-light (no mesher/numpy/search imports) and **never raises** on an unknown typology or knob — the GUI must degrade to a plain label, not crash.
- `tools/gen_param_reference.py` → generates `docs/reference/PARAMETERS.md` + `docs/reference/TYPOLOGIES.md` with a "GENERATED — do not edit" header and **symbol-anchored** code references (verified to resolve before emitting), never line numbers.
- `tests/test_param_reference.py` → the drift gate.

**Bounds precedence for the sandbox sliders (lowest → highest authority):**
1. `families.KeySpec.lo/.hi` — hard schema clamp, **always wins** as the final clamp (`families.py:12-13`).
2. `examples/typologies/*.yaml` — the search bounds, which is also what the run page's "parameter limits" bars already display.
3. A **user-saved override** file outside `examples/` — this is the "save as the default min/max for this typology" ask.
4. A session/sandbox tweak — caller-supplied, never persisted.

**Drift gate (this is what keeps it a source of truth instead of a fifth stale copy).** The test FAILS (never warns) when: a name in `DEFAULT_KNOBS` has no metadata; a knob read by `build_meridian`/`materialize`/`grid.py` has no metadata for the typologies that read it; a catalog id has no entry; a metadata default disagrees with `DEFAULT_KNOBS`; a metadata hard limit disagrees with `KeySpec`; a code symbol or doc anchor does not resolve; a summary is missing or over-length.

**Explicitly NOT in P9 scope:** no new typology, no new search, no new solver or mesher code, no change to `docs/plan/**` (frozen), no GPU work, no automatic widening of any bound. This is a read-only view over existing authority plus a GUI surface — the R9 research-grounding rule (`AGENTS.md` §Research grounding) does not bind because nothing ships under a new published name; a sandbox must *cite* the existing dossiers rather than make new claims.

**Interaction with W8 (must not be worked around).** W8 (per-typology search-box audit) exists because the owner found config `bounds:` binding 4/6 best designs at their ceiling, and `NOTES_FOR_SENIOR.md` records the owner's remark that some min/max parameters may still be **over-constraining**. The sandbox MUST display the real bounds and MUST NOT let a saved override masquerade as an authoritative default. Bounds are widened only through W8, per config, with measurement — never as a side effect of a GUI save.

**Open decisions for the owner before any code (see also `NOTES_FOR_SENIOR.md`):**
- Does the metadata package belong in `design/params/` (near the code it annotates) or under `gui/`? The former keeps one copy for GUI + docs + tests; the latter is import-light by construction and risks the GUI owning design facts.
- Where do user-saved slider bounds persist, and are they a *personal preference* (never authoritative, never committed) or an *owner-gated config edit* to `examples/typologies/*.yaml`? Hard rule 3 and the "every horn number is a YAML default in `examples/`" rule both point at the latter only with the owner's explicit sign-off.
- Is a sandbox geometry page allowed to render a design that the search would reject (outside the brief envelope), and if so does it carry a visible "outside envelope" marker? Precedent: the run page already distinguishes at-limit parameters with a red marker; the sandbox should reuse that language rather than invent one.
- `exponent` 2.0 (prose) vs 4.0 (shipped): which is the documented default? A lane must not pick a winner.

## P10 (added 2026-10-27, owner-directed). After the campaign smoke night: data-integrity fixes, objective v4, then the search sequence

**Full plan: `docs/IMPLEMENTATION_PLAN_2026-10-27.md`.** In order: (1) `dataset/record.py` accepts the scorer's
objective versions (v3 records were silently not written); (2) reseed `gcurve__osse_b1w` (`gcurve_dist` 1.0);
(3) objective v4 with per-term tolerances from the brief (owner picks the tolerances; T0 re-run on 27 cells);
(4) T3 diagonal balloons on same-brief crease/control pairs; then (5) second seeds, (6) compare tier, (7) polish,
all scored v4. Section 9 records the fluted/lobed-wall idea from JW Sound's Solana (harmonic FREEFORM station,
fork change), gated on v4 results.

## P11 (added 2026-10-27, owner-directed, TABLED). Share campaign data with the collaborator, then merge to main

- **Hugging Face sync.** Data (~22 GB: `runs/` 11.4, `cache/` 7.9, `dataset/` 2.4) is git-ignored and too big for GitHub.
  `tools/hf_sync.py` (`pack` / `upload` / `pull`) is written but never run for real. Needs the owner to run
  `hf auth login` (write token) and to pick the repo (suggested `chingadalleva/hornlab-search-data`, private by default).
  Start with groups `text,solve,dataset` (~7.2 GB); `meshes` (~10 GB) is optional. Pack only after the GPU night has
  finished writing. The solve cache is what lets a no-CUDA collaborator re-score offline.
- **Merge to main.** Open question: which branches ("everything" = `unified-typologies` only, or also `beta-fixes`, which
  says "merge after overnight queue"; exclude `dev/fused-cuda-pin`). Work tree has uncommitted v4 changes; the repo rule
  says CONTINUITY.md and ISSUES.md must be updated in the same commit as any push.
- **Also pending from the v4 nights:** re-run `crease__osse_b1w` (resume job failed at startup), check why
  `b1w__biradial_keele` stops at ~10 evals, update CONTINUITY.md for the 100-per-cell and resume nights.

## P12 (added 2026-10-27, owner-directed, TOP PRIORITY BEFORE MORE SOLVE NIGHTS). Do the simulations behave like a built-and-measured horn? Loading, the ideal source, and scoring honesty

**Owner's concern (verbatim intent):** "I don't want to be running these simulations if it isn't going to behave like it would if we built one and tested it." Investigate first; do not queue large campaigns on a scoring/model basis that has not been checked against reality.

**What was found 2026-10-27 (evidence: stored `z_throat` of the v4 best designs, `hornlab_search/objective/terms.py::load_term`, briefs under `examples/briefs/campaign_2026-10-26_v4/`):**
1. **Loading is weighted on only 4 briefs** (`b3bt_*`, `b3bw_*`, `native_lecleach_1200_1in`; weight 0.5, `z_min` 0.7). Every other brief, **including the b3a 90x90 PA cells and their best horn `b3a__rosse_morph` (J 1.31)**, has `load` weight 0.
2. **The J 1.31 winner is essentially unloaded:** Re z_throat = 0.04 / 0.12 / 0.37 / 0.82 at 500 / 827 / 1370 / 2268 Hz, yet its H and V polars look excellent down to 500 Hz. `native__lecleach_rollback`: 0.03 at 500 Hz. `b3bt__rosse_morph` (loading brief) 0.08-0.14 at 500-643 Hz.
3. **The model drives an ideal source** (unit normal acceleration on tag 2; `spl_reference` in `solve/beat.py` meta), with NO driver (no T/S model, diaphragm, phase plug, rear cavity) and polars normalised to on-axis. So pattern SHAPE is credible, but level, efficiency, excursion/distortion and cutoff peaks of a real compression driver on a poorly loaded horn are NOT represented, and a horn that is nearly silent at 500 Hz can still look perfect in the polar plots.
4. **`load_term` is `mean_f(max(0, z_min - Re z))` over the whole scored band**, so sub-cutoff deficits are diluted by many well-loaded points; the screen grid starts at 500 Hz, below which big-PA loading is never solved (verify tier goes to 300 Hz).
5. Related scoring-honesty observations (same day): cov is `err^2/100` with tolerances 2.0 (A) / 4.5 (B, C), i.e. about 14 / 21 deg RMS per "1 unit", so J is generous; cov is MASKED below f0 for class A (twinray V is 120 deg at 500 Hz and still scores 3.0); loading, flatness and presence-band weights are mild.

**Research report (2026-10-27, outside sources):** `docs/research/SIM_VS_REAL_HORN_2026-10-27.md`; summary in `docs/plan/12_RESEARCH_BASIS.md` section 17. Ranked actions from it: P12a re-score (free) > lumped compression-driver model over the BEM throat impedance (cheap, no new solves) > validate against ONE published measured horn > load ON for PA/low-reach (max or sub-f0 aggregation; weights 0.3-0.5 CD, 0.8-1.0 PA, 1.0 low-reach) > report-only 200-300 Hz solve > print and measure two finalists. Also: keep `distd`, down-weight `dislope` on constant-directivity briefs; add polar cross-correlation as a report metric.

**Senior pass (2026-10-27 evening, zero GPU):** `docs/research/SENIOR_PASS_SCORING_SEARCH_REALITY_2026-10-27.md` - P12a
offline re-score done there (loading in dB + stricter pattern), knob importance per cell, woofer spacing / DI match at the
crossover (new: no brief knows about the woofer), 2 m vs 10 m, reduced-knob two-stage search, a calibration night, the
print-and-measure protocol, and six owner decisions.

**To do (in order; owner approval needed before changing scoring or queuing new campaigns):**
- [ ] **P12a - quantify the gap.** Re-score the existing cached responses (no new solves) with loading ON (weight 0.5-1.0, `z_min` high, scored from f0 upward) on the PA/low-reach briefs and show the rank change (expect `b3a__rosse_morph` to drop). Also a stricter-cov variant (tolerances 2->1, 4.5->2; one-sided below f0 for every class; presence band 2x->3x).
- [ ] **P12b - real-world validation.** Pick a measured reference horn (published CD horn or a collaborator's measured prints, e.g. a known 90x60 with polars and impedance/FR) and check our solver + objective reproduce its measured polars, DI and throat loading; document the error. Quantify the ideal-source assumption: add a simple driver model (compression-driver diaphragm + rear cavity + phase plug equivalent circuit, or the BEM throat impedance into a Thiele-Small-style driver) so on-axis level / FR and excursion can be predicted, and add an `absolute level` or `efficiency` term (not just on-axis-normalised patterns).
- [ ] **P12c - fix the model/scoring gaps found:** loading on for all low-reach and PA briefs; verify-tier (300 Hz) loading check for finalists; consider a report-only low-frequency solve (200 Hz) so cutoff behaviour is visible; throat cross-mode (f11) already noted in the fused-CUDA evidence.
- [ ] **P12d - build-and-measure loop.** Print 1-2 finalists (see the print-service notes in the 2026-10-27 chat: PLA/PETG prototypes, 4 pieces, 4-6 perimeters, gyroid, resin-backed) and measure polars/impedance to calibrate the objective before the next big campaign. A first print of a "scoring-honest" winner vs a "J-winner" would show whether J predicts real behaviour.
- **Gate:** no new multi-hour solve nights beyond the already queued ripple/ridge night until P12a (and ideally P12b) results are reviewed; the queued night is cheap, comparison-oriented geometry exploration, but its J values inherit these caveats.

## Not recommended (recorded so nobody re-proposes it without new evidence)
- Half precision or other "quantization" of the BEM system: the solver is Float32 with a Float64 Krylov space; dense
  high-frequency BEM systems are poorly conditioned.
- Lowering epw below 6 without a measured convergence check.
- GPU memory oversubscription to system RAM: Linux-only, and a dense factorisation over PCIe crawls.
- Fewer high-frequency sample points: saves time, not peak memory.

## Fallback
Cloud RTX 4090 (24 GB, about $0.34–0.69/h) or L40S (48 GB, about $0.79/h): `docs/CLOUD_GPU_REPORT.md` CP-9a pod proof
first (Linux CUDA never run with this solver).

## P13 (added 2026-10-30, owner-directed). Mini multiple-entry horn: implement through the `docs/meh/` hand-off

Owner un-deferred MEH (deferred 2026-10-24, G17) and set the targets: MEH top in a 16 in square face for home hi-fi /
DJ practice / booth, separate bass box 30-120 Hz, DSP + FIR on every channel. The orchestrator fixed the architecture,
typologies (T2 `meh2_6x2` primary, T1 `meh2_4x4`), solve strategy (per-channel BEM + impedance matrix + lumped network)
and scoring (objective v5). Ten work packages for cheaper agents: `docs/meh/README.md` (waves, models, dispatch prompt),
`docs/meh/00_MEH_CONTRACTS.md`. Research basis: `docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md`.
GPU work is M8 only, on the owner's box, after the fork change (M2) and the pipeline (M7).
