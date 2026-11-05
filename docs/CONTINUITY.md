# CONTINUITY

Newest entry first. Every push updates this file and `docs/ISSUES.md` in the same commit.

## 2026-11-05 - CI fix: native param catalog for mid_ports + Solana/SAWMOD natives

- PR #22 CI failed `tests/test_param_catalog.py` (4): `OSSE.mid_ports` missing from
  `NATIVE_KNOBS`; hard-coded "10 natives" broke after Solana/SAWMOD YAMLs; CAD-only
  `sawmod_meh_lr2` / `solana_meh*` empty-knob gate; stale `param-catalog.v1.json`.
- **Fix:** document `mid_ports` (not_a_knob); core-native floor + CAD-only set in the
  test; regenerate catalog / PARAMETERS / TYPOLOGIES.

## 2026-11-05 - Objective v6 (loading_smooth) for Le Cléac'h / rollback

- **Why:** CD-shaped v4 remapping (`dislope:0`, `load:0.5`) kept the wrong math — band-mean
  `load` was ~2 % of J; coverage still punished natural narrowing. JMLC fc is a loading corner;
  pattern control starts ~1.5–1.8×fc; DI rises smoothly (ETF 2010 / LANE_A).
- **Landed:** `objective.version: 6` — `load_near`, `z_smooth`, `cov_pat`, `di_rise`, plus
  `flat`/`rip`/`distd`/`diag`. Module `hornlab_search/objective/scalar_v6.py`; dispatch in
  `versions.py` / `evaluate.py` / `config.py`. Design `g_fc_hz` stamped into metrics for
  `f_pattern`. Dossier `docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md`.
- **Briefs:** `examples/briefs/campaign_2026-10-26_v6/native_lecleach_1200_1in_v6.yaml`,
  `examples/briefs/lecleach_rollback_1in_v6.yaml` (v4 briefs untouched; J not comparable).
- **Tests:** `tests/test_objective_v6.py` — 14 offline pins green (constant-Z load_near≈0,
  sinusoidal z_smooth↑, DI+5 dB/dec → di_rise≈0, cov errors below f_pattern ignored).
- **Re-score [measured]:** campaign `docs/data/campaign_v4_2026-10-27/evals.csv` lecleach cells
  (no `z_throat` in export → `load_near`/`z_smooth` take NAN fill). On available pattern terms,
  seed shares are live — e.g. `native__lecleach_rollback` n=209: di_rise raw≈9.1 (slope ~8 vs
  target +5), cov_pat raw≈7.0; `b1t__lecleach_iwata_ar` n=198: di_rise 36 % / cov_pat 6 % of
  pattern-term J. Full load-dominance check needs records with throat impedance.

## 2026-11-03 - PR: feat/solana-sawmod-wg-bench → main

- Opening PR for Solana/SAWMOD bench path, mid_ports mesher pin, RunPod cloud tooling,
  UMAP evidence HTML, and GUI **Design cloud** (`/api/umap`, `#/run/<id>/umap`).
- Keele CMA-100 synced locally (`20261104T021231Z-screen-4347f5`, best J=13.17); sample
  PCA on 34 OK designs (not shipped as a code change).

## 2026-11-03 - Design cloud (UMAP/PCA) in the local GUI

- **Landed:** `GET /api/umap/<run>?method=auto|umap|pca` (`data.run_umap_cloud`), run page
  button **Design cloud** → `#/run/<id>/umap` (`static/umap.js`). PCA always (numpy); UMAP when
  `umap-learn` is installed. Color by param unit quartiles or total J; click for full param table.
  Cached in `runs/.gui_cache/`. Offline `tests/test_gui_umap.py`.

## 2026-11-03 - UMAP HTML: full param table + safer embed

- **Fix:** `UMAP_SOLANA_OSSE_MEH_SF_CMA1000.html` now embeds data as `window.UMAP_DATA`,
  populates all 18 searchable knobs in the dropdown, and shows a side panel with every
  physical + unit value on point click (not just the active color channel).

## 2026-11-03 - Interactive UMAP of solana_osse_meh_sf CMA-1000 (GitHub-viewable)

- **Artifact:** `docs/evidence/UMAP_SOLANA_OSSE_MEH_SF_CMA1000.html` (+ `.md`) — standalone
  D3 page of OK designs from run `20261103T053926Z-screen-8b32a1`, color by parameter
  unit quartiles or total-J bands; click for values. Open via htmlpreview link in the
  evidence md (GitHub file view is source-only).
- **Method note:** UMAP on unit-box searchable knobs (not per-term loss); subsample of OK evals.

## 2026-11-03 - Ath OSSE+SF mid_ports mesher fork + solana_osse_meh_sf

- **Mesher fork:** `jamescollinharky/hornlab-waveguide-mesher` branch
  `hornlab-search/osse-midports` @ `55da4f46d662d8dcd7a9f94a609eeea4009fcd62`
  (base `b922e807`). Opt-in top-level `mid_ports` re-tags inner-wall triangles to
  tag 10 (flush L1 exits); absent = byte-identical. Pinned in `pyproject.toml` +
  `TOOLCHAIN.md`; `docs/FORKS.md` updated. Mac checkout:
  `~/Desktop/projects/forks/hornlab-waveguide-mesher`.
- **Search wiring:** `families.to_mesher_config` emits `mid_ports` for OSSE when
  present; `mesh/build.py` requires tag 10 and echoes `midPorts` into
  `mesh_meta.json`. Offline tests `tests/test_design_mid_ports.py` +
  `tests/test_mesh_mid_ports.py`; `test_mesh_pin` / doctor pinned-shas green.
- **Config:** `examples/typologies/solana_osse_meh_sf.yaml` — Ath SF seed (same as
  `solana_osse_sf_search`) + `mid_ports` tblr + brief `solana_meh_1in_90x90`.
  Shape-check [measured] Mac+4090: ~2900 dofs / 14000, mouth 450×450, depth 152,
  round coupling. Flat CAD MEH (`solana_meh*`) remains the fallback; Ath+SF+MEH
  is now the Solana MEH-context estimate path.
- **MEH evaluate:** OSSE mid_ports path supplies port area via
  `mesh_meta.json["mid_ports"]` (`_meh_layout`); CAD `derived` still preferred when present.
- **4090 [measured]:** screen `20261103T052310Z-screen-ce9d4f` seed **J=39.604** (2921 dofs,
  solve 38.5 s). CMA `20261103T052647Z-screen-cd22a5` live on pod `kt44oly5cdlaps` — early
  best **J≈22.3** (was 39.6); Mac GUI pull-loop syncs that run into local `runs/`.

## 2026-11-02 (evening) - Solana/SAWMOD bench + RunPod cloud path landed on branch

- **Branch:** `feat/solana-sawmod-wg-bench` rebased onto `origin/main` @ `0fb7d98` (PR #21
  hardware decision). WIP stashed → FF → restored; INDEX/ISSUES conflict merge kept main +
  Solana/SAWMOD/cloud rows.
- **Cloud GPU path:** `tools/cloud/` (`runpod_ctl.py`, `bootstrap_linux.sh`, `run_job.sh`,
  `runpod_env.example`) + `docs/CLOUD_GPU_RUNBOOK.md`. Secrets stay local (`.env.local`
  gitignored). POSIX BEAT orphan cleanup: bare `julia … solver.jl --worker` hosts now
  match in `solve/worker.py` (not only Windows `julialauncher*`); test in
  `tests/test_solve_worker.py`.
- **RunPod [measured]:** RTX 4090 pod bootstrapped; CP-9a selftest deltas **0.020 / 0.039 dB**;
  Solana CD screen J≈41.9 on CUDA; `examples/osse_baseline_4090.yaml` (fused BM, band/dof
  raises for 24 GB) queued for ~200-eval CMA. One GPU at a time; hosts cleared via
  `run_job.sh`.
- **Solana:** phase-1 Ath WG (`solana_osse` + brief) + evidence; phase-2 MEH CAD seed
  `solana_meh` / `solana_meh_search` + brief `solana_meh_1in_90x90` from DIY Guide Rev 2.0
  (DH450 + 4×6NDL38, face 450 mm vs DIY 410 disclosed). Mouth probes under
  `examples/typologies/_solana_mouth_probes/` (athscript / morph_fixed_0 / gcurve_off —
  SF mouth ~450 vs morph-only ~356).
- **SAWMOD:** control WG + knuckle + `walls: lr` MEH probe; CAD/`step_build` accept `lr`.
- **Still owed:** stop/finish live OSSE search as needed; Solana CD mouth-matched
  (`gcurve_off`) screen+verify on 4090; Ath midports MEH path; SAWMOD Ath knuckle+ports /
  LF / BL refine.

## 2026-11-02 - P11 TURNED ON: PUBLIC HF DATASET REPO PUBLISHED FOR THE COLLABORATOR

- **Owner directive:** set up Hugging Face storage so the GitHub collaborator can pull "the solves we've done".
  Owner chose **public** (collaborator needs no HF account/token) and the **core groups** `text,solve,dataset`.
- **Live:** <https://huggingface.co/datasets/chingadalleva/hornlab-search-data> — public dataset repo, created
  with `hf repos create ... --repo-type dataset --public`, 7 tar shards + `.gitattributes`, **11.56 GB /
  10.76 GiB** (11,556,730,880 B), **197,581 source files**, packed 2026-11-02 ~20:53 local from this worktree
  at `task/hardware-decision-2026-11-01`. Remote sizes verified byte-identical to the local tars
  (`text-000` 731,473,920 B; `solve-000..002` 2.03 GB each, `solve-003` 8,550,400 B; `dataset-000` 2.04 GB,
  `dataset-001` 1.95 GB). Seven per-shard commits (`bfbe708`, `75cf749`, `50aa0b1`, `fbcc6e4`, `42611f3`,
  `d51b17d`, `701f568`).
- **Safety gate before packing [measured]:** julia host PID 17056 idle (CPU 954.859 -> unchanged over 8 min),
  VRAM 706 MiB of 8188, newest `runs/` write 20:44 vs pack start 20:53, so no GPU night was writing.
- **Collaborator path verified end to end:** anonymous `curl -r 0-2047` on `solve-003.tar` returns **206** with
  2048 bytes (no auth), and `hf download ... --repo-type dataset --include "solve-003.tar" --local-dir .hf_stage`
  + in-place untar reproduced `cache/solve/<key>/{response.npz,status.json}` (32 cache dirs). Instructions live in
  `docs/HANDOFF_COLLABORATOR_2026-10-27.md` section 4; P11 marked done.
- **`tools/hf_sync.py` corrected** against huggingface_hub docs checked 2026-11-02: `upload` now runs
  `hf upload <repo> <dir> . --repo-type dataset` (`hf upload-large-folder` is deprecated and absent from the
  2.4.0 CLI reference; `hf_transfer`/`HF_HUB_ENABLE_HF_TRANSFER` are gone in hub v1), `pull` filters
  `--include "*.tar"`. Local CLI/hub is 1.17.0 with `hf_xet` 1.5.0.
- **Measured network finding [owner machine]:** the **Xet upload path stalls here** — two `hf upload` runs held
  0.1-1.2 MB/s with zero commits after 25+ min while the same link measured 8.3 MB/s upstream
  (`speed.cloudflare.com/__up`, 20 MB) and 9.7 MB/s down from `huggingface.co`; `HF_HUB_DISABLE_XET=1` then
  pushed 2.04 GB in 3.4 min. Uploads from this box must set `HF_HUB_DISABLE_XET=1`. Downloads were unaffected.
- **Not uploaded:** `cache/mesh/**` + `runs/**/*.msh` (16.81 GB) — pack with `--groups meshes` if the collaborator
  needs stored meshes rather than rebuilding them with the CPU mesher. Anything written after 20:53 local needs
  a re-pack.
- **Collaborator runbook added:** `docs/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md` — agent-executable
  (clone → `hf download` → verify sha256 per shard → extract in place → verify counts 124,681 / 48,817 /
  24,083 → load one `response.npz`), plus the offline re-score entry points, a troubleshooting table and the
  rules for an agent working in the checkout (never commit the data, never touch `.venv`, no GPU solves, push
  rule). Linked from `docs/INDEX.md`, `docs/HANDOFF_COLLABORATOR_2026-10-27.md` section 4 and P11.
- **Shipped as PR #20 into `main`** (`task/p11-hf-sync`, cherry-picked off `origin/main` so the PR carries
  only this work, not the 47 unrelated commits on `task/hardware-decision-2026-11-01`). Files: `tools/hf_sync.py`,
  the new runbook, `docs/HANDOFF_COLLABORATOR_2026-10-27.md`, `docs/NEXT_DEV_PRIORITIES.md`, `docs/INDEX.md`,
  this entry and the `docs/ISSUES.md` note. No solves, configs, pins, tolerances or tests touched.
- **Process note:** two docs were briefly damaged by a PowerShell `Get-Content -Raw | Set-Content` round-trip
  (PS 5.1 re-encoded UTF-8 as ANSI, mangling em dashes and quotes) and were restored from git and re-edited with
  a UTF-8-safe editor before the commit; the committed diff contains no replacement characters.


## 2026-11-02 - Cloud GPU runner (RunPod-first tooling)

- Added `tools/cloud/`: `runpod_ctl.py` (GraphQL create/status/ssh/stop/terminate),
  `bootstrap_linux.sh`, `run_job.sh` (force-clear BEAT hosts → CLI with explicit
  `--backend beat_cuda` → `shutdown(verify=True)` → `runs/cloud_job_*.json`),
  `runpod_env.example`. Secrets stay out of git (`.env.local` gitignored).
- Runbook: `docs/CLOUD_GPU_RUNBOOK.md` (CP-9a gates, Solana screen first, ~$50 pilot
  suggestion). Research still in `CLOUD_GPU_REPORT.md`.
- POSIX worker hygiene: `beat_host_roots` now finds orphaned bare `julia … solver.jl
  --worker` hosts (Linux/macOS), not only Windows `julialauncher*`. Test added in
  `tests/test_solve_worker.py`. Offline worker tests green.
- Superseded same evening: first paid 4090 pod ran CP-9a + Solana screen (see evening
  entry above).

## 2026-11-01 (late afternoon) - Solana 2.0 WG reconstruction (phase 1) + SAWMOD phase-2 probes

- **Solana:** DIY Guide Rev 2.0 + `Advanced/athscript.cfg` snapshotted under
  `docs/research/typologies/solana_2026-11-01/` (Drive guide `1-JxZ-…`, files
  `151N2rq4…`). Dossier `SOLANA_WAVEGUIDE_2026-11-01.md`. Config `solana_osse` +
  brief `solana_control_1in_90x90` (verbatim Ath pins: L=140, SF m=8, morph 353×353).
- Dry-run **4284 dofs**; mouth with SF **~450 mm** vs Ath morph 353 / STL outer ~376
  (morph-only ~356 — mesher/Ath delta disclosed). Screen Metal:
  `runs/20261101T211314Z-screen-72f3bd` — **J=41.9**, 27.9 s, `di_source=balloon`.
  Evidence `docs/evidence/SOLANA_WG_2026-11-01.md`. Phase 2+: mid ports / MEH / mouth delta.
- **SAWMOD phase-2 probes (same session):** knuckle CD-only
  `sawmod_knuckle_osse` (SF digitized) Metal `20261101T210541Z-screen-3c1938` J=241 /
  2948 dofs; flat-wall MEH `sawmod_meh_lr2` (`walls: lr`, cone 103/66, hp_hz 250) dry-run
  3950 dofs + multi-source Metal `20261101T210635Z-screen-ab4075` J=21.5 (v5; `n_nan=12`,
  `load=100`, z_throat null — provisional). beat-bem bumped to pin `1efdc6f` for MEH path.
  CAD `tools/cad/meh.py` + `step_build` accept `walls: lr`. LF/BL still later.

## 2026-11-01 (afternoon) - SAWMOD control-waveguide benchmark (phase 1)

- Whitepaper snapshot + dossier: `docs/research/typologies/sawmod_2026-11-01/`,
  `SAWMOD_CONTROL_WAVEGUIDE_2026-11-01.md`. Config `sawmod_control_osse` + brief
  `sawmod_control_1in_100x70` (pinned OS-SE L=115, morph rate 4, no knuckles).
- Mesh: L=115 mm, mouth after morph **280×196** mm (`morph_allow_shrinkage: 1` required;
  raw OSSE ~395 mm). Screen Metal solve OK: **1464 dofs**, J=345.2, 5.4 s —
  `runs/20261101T205918Z-screen-e7b5a2`. Evidence
  `docs/evidence/SAWMOD_CONTROL_WG_2026-11-01.md` (freestanding vs paper baffle caveat).
- Phase 2+ still owed: knuckles, mid ports, LF slot, BL SAWMOD refine.

## 2026-11-01 (10:20 EDT) - PACKAGED FOR HANDOFF: QUICKSTART, SCREEN LAUNCHER, BOTH VERIFIED WINNERS

- **`docs/meh/MEH_QUICKSTART.md`**: install (pinned stack, `doctor`), the CI gate, a no-GPU `run --dry-run`, the
  screen + verify commands, what is already done, and the six traps that cost this pass time (8 GB band ceiling,
  non-comparable frequency grids, stale solver hosts producing misleading errors, LF-only repo, `fill` not carried in
  the record, quarter-only CAD).
- **`tools/meh/run_screen.ps1`**: one-brief launcher - clears stray solver hosts, runs the CMA screen, finds the run
  directory, re-solves the top N at verify fidelity, and writes `runs/nights/meh_<tag>_*.log` plus a summary line.
  Parameterised by tag/config/budget/mode; replaces the session-local `scratch/meh/*.ps1` helpers, which are
  gitignored.
- **`docs/evidence/meh_2026-11-01/`**: the two verified winners as JSON (geometry knobs, objective terms, the
  inner-network solution, the CAD layout, channel tags, library SHAs) plus a README that states the numbers and the
  caveats. Extracted from the dataset records, not retyped: T2 `ed11d2cd3acc` (screen 9.530 / verify 11.894, HF1440 +
  6NDL38, XO 651.8 Hz LR4, +0.312 ms, 4.21 L rear) and T1 `704051ae928c` (13.228 / 14.512, HF108 + 4NDF34,
  XO 1000.2 Hz LR4, +1.430 ms inverted, 0.81 L rear).
- Purpose: the next session (owner's friend or an agent) can reproduce and extend the MEH work without rebuilding the
  launchers, re-running the screens, or hunting for the winners.

## 2026-11-01 (09:40 EDT) - CI FIX ON THE PR: OPTIONAL SOLVER DEP GATED IN THE NEW TEST

- PR #18's first CI run failed at **collection**, not in a test: `tests/test_solve_worker_restart.py` imported
  `hornlab_beat_bem` at module scope, and CI does not install that package (main's 546926d deliberately gated
  optional-dependency tests). The import is now `pytest.importorskip(...)`, matching the repo's existing pattern, so
  the file skips cleanly where the solver is absent and still runs on the owner's box.
- Nothing else in the failure list was ours: the run stopped at that one collection error (3 skips, 21 deselected).
  The merge itself is already on `meh/integration` (`08f04bf`) and the focused gate over every touched area passed
  (config, solve/adapter, GUI sandbox, param catalog, all MEH/objective/bassbox tests: exit 0).

## 2026-11-01 (09:05 EDT) - MERGED origin/main INTO meh/integration: LF NORMALIZED, LOGS UNIONED

- `origin/main` had moved (46 files: the staged-search A/B work, Metal device support in `solve/beat.py`, a
  `load_config(backend=...)` override, and the same ridgeCache test fix we made independently).
- **Line endings:** main is LF; this branch had CRLF in 16 MEH-touched files, which turned every shared file into a
  whole-file conflict and would have broken the byte-identical param-catalog test on Linux CI. All 16 are now LF
  (a9720d2), so the merge is semantic rather than 100 whole-file rewrites.
- **Conflicts resolved:** `CONTINUITY` and `NOTES_FOR_SENIOR` are unions (nothing dropped: 11 main entries and one main
  block added); `tests/test_gui_sandbox_page.py` keeps this branch's version (identical assertion); `config.py` and
  `beat.py` auto-merged cleanly once the EOLs matched, so main's Metal support and this branch's freq_grid/recycling
  changes coexist.

## 2026-11-01 - HARDWARE DECISION STUDY: RENTAL FIRST; FULL-WALL MESH IS MUCH LARGER

- Owner clarified this is a theoretical rent-versus-buy decision; no rental machines configured. Rental spend $0, no new BEM solves/screens. `docs/evidence/HARDWARE_2026-11-01.md` records the study, current published rates and explicitly conditional costs.
- Four CPU-only diagnostic builds on the fixed T2 seed: EPW 4.2 => 8,625 dofs / 16,909 triangles, global valid-to 6,015 Hz; EPW 6 => 17,211 / 33,938, global 8,583 Hz; EPW 8.4 => **33,959 / 67,245, global 12,009 Hz, valid**; EPW 9 => 38,819 / 76,919, global 12,864 Hz, valid. This is validator sizing, not acoustic convergence or a proven minimum over all geometries. Shipped configs untouched.
- Source audit of unchanged pin `1efdc6f`: standard CUDA uses fixed dense direct solves, repeating LHS/refactorization per channel; CPU/Metal GMRES cost model is not the CUDA route. At N=33,959/E=67,245 the concurrently live operators+identities+LHS alone require **85.410 GiB** before extra workspace. A 24/32 GB card is a coarse-mesh test candidate; the first requested full-wall discrete tier worth testing is H200 141 GB. No fit/runtime claim was measured on it.
- Historical NPZ/NDJSON extraction corrects the handoff's seed/winner attribution: T2 winner is N=5,872/E=11,456 with baseline/peak 513/7,575 MiB; T1 winner N=6,249/E=12,205 with baseline/peak 330/7,840 MiB. Across 69 successful historical screen candidates, assembly is the largest reported engine stage (~2 s/frequency, versus ~0.2 s solve). No 12 kHz throughput inference follows.
- Flat device-use peaks do not prove constant workspace; CUDA 719 does not uniquely establish OOM. Current `vram_41f.csv` differs from the earlier trace described in M8 and has no verified idle baseline. These refine the older capacity diagnosis; the recorded failures and prior screen winners remain unchanged.
- Shared-host multi-GPU work is not a one-line change: evaluator/persistence side effects, global lock, all-host cleanup and worker registry identity need isolation. Two separate single-GPU machines, one brief each, are a simpler future deployment test. All cross-card, unified-memory, lane-scaling and overnight measurements remain open. `doctor`: 11/11 checks passed; evidence excerpts checked against decoded bytes. No production code/pins/tolerances changed.

## 2026-11-01 (08:20 EDT) - WRAP-UP: FULL OFFLINE SUITE GREEN AT THE TIP; PR TO `main` OPENED

- **Final gate [measured]:** `.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -q`
  at `task/hardware-decision-2026-11-01` -> **exit 0**, no failures. This is the first full run since the last config
  edits (epw 4.05 / screen cap 8,200 / `solve.freq_grid` / `worker_restart_every`), so the tip is gated, not just the
  code merges.
- **Contents of the PR:** the complete MEH implementation (M1-M7, M10), the solver fork pin bump to `1efdc6f` with its
  validation evidence, both 40-evaluation screens with their verified top-2 arms (T2 9.530 -> 11.894, T1 13.228 ->
  14.512), the six-line readiness proof with its one FAIL and one PARTIAL stated plainly, the hardware audit and
  hand-off, and the honest record of the three blocks (8 GB band ceiling, CAD quarter-only, Boundary Lab absent).
- PR base `main`, head `meh/integration`, which now carries the hardware branch (fast-forward; the hardware branch is
  a descendant of the integration tip). Background job board: all sessions reconciled, none active.

## 2026-11-01 (07:55 EDT) - HAND-OFF TIDIED: WITHDRAWN VRAM CLAIM REMOVED FROM THE AXES AND UNIFIED-MEMORY SECTIONS

- The s2a corrections block covered s2, but s5 (axes table) and s5b (unified memory) still asserted the withdrawn
  "flat per-frequency workspace" reading as fact. Both now state what is actually established (device use sits within
  ~300 MiB of the ceiling whenever a 12 kHz MEH mesh solves; the pinned CUDA path holds several N x N and N x E
  complex64 operators plus identity caches, ~85 GiB at the first globally valid whole-wall mesh) and point at s2a.
- Removed a duplicated 5-frequency row my earlier table patch had introduced. No measured value changed.

## 2026-11-01 (07:40 EDT) - HARDWARE AUDIT REVIEWED; FOUR OF MY CLAIMS CORRECTED IN THE HAND-OFF

- The fresh-eyes audit (`docs/evidence/HARDWARE_2026-11-01.md`, Codex session) is sound. I reproduced its two
  load-bearing numbers from the stored data: the screen winners are **5,872 / 6,249 dofs** (not the 6,032 / 6,009
  seed meshes I paired with their timings), and the winners' `meta.timings` give **assembly 23.72 s, solve 2.38 s,
  field 0.19 s, total 35.54 s over 12 frequencies** - assembly is ~67 % of engine time, as the audit says.
- **Withdrawn from my hand-off:** the "~12x for 1.44x elements" scaling claim (it divided a FAILED sweep by 41 and
  used cold-start guesses - there is no valid seconds/frequency at 8.6k dofs); the "flat ~7.9 GB workspace" reading
  (`nvidia-smi` total use + CUDA.jl caching is not live working set, and the CSV that backed it was overwritten by a
  later poller run, now 558 samples starting at 5,643 MiB with no idle baseline); the "25-35k elements" full-wall
  guess (the first globally valid T2 mesh is **33,959 dofs / 67,245 triangles**, ~85 GiB static on the pinned CUDA
  path, so 141 GB is the first viable tier); and "lanes are a one-line change" (five concrete surfaces).
- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` now carries a s2a corrections block so the repo does not hold two
  contradictory records. The audit's conclusion stands: rent a short pilot before buying, and the full-wall 12 kHz
  target is much larger than this pass assumed.

## 2026-11-01 (07:05 EDT) - HARDWARE HAND-OFF EXTENDED: UNIFIED MEMORY + THE MEASURED BASELINE

- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` gained two things the next agent needs:
  1. **The measured baseline table** with every data point this campaign produced, plus the derived
     per-frequency rates: ~3.6 s/frequency at 6,032 dofs and ~40-53 s/frequency at 8,625 dofs. That is a
     **~12x cost for a 1.44x element increase**, which is not a clean exponent - it is consistent with
     elements-squared assembly PLUS a change of solver path between those sizes. Separating those terms is
     named as the first measurement of the assignment.
  2. **A unified/coherent-memory section** with the configurations worth testing and the reason the test is
     bandwidth, not capacity: the per-frequency working set is a flat ~7.9 GB, so spilling it over a
     PCIe-class link would cost 5-50x, while NVLink-C2C (GH200/GB200) and Apple's shared memory have real
     bandwidth. Table covers GH200/GB200, Apple M3/M4 Max/Ultra (Metal path), MI300A (ROCm), Strix-Halo-class
     APUs as the negative control, and CPU-only. Every non-CUDA option carries a validation task: the pinned
     fork `1efdc6f` is CUDA-validated only, so Metal/ROCm must clear single-tag parity (<= 0.039 dB) and the
     four multi-tag properties before a campaign may use them.

## 2026-11-01 (06:50 EDT) - EVIDENCE DOC AND INDEX CORRECTED TO MATCH THEIR OWN CONTENT

- `docs/evidence/MEH_M8_2026-10-31.md` was still titled "readiness links 1-2 (partial)" although it had grown to the
  six-line readiness proof, both screen pairs with verify arms, the two hard blocks and the band finding. Title
  corrected (with a dated note) and the `docs/INDEX.md` entry rewritten to state the actual verdicts: links 1/2/5/6
  PASS, link 4 FAIL, link 3 PARTIAL, screens verified, blocks listed. No measured number changed.

## 2026-11-01 (06:40 EDT) - HARDWARE HAND-OFF WRITTEN (next agent: compute configuration)

- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` (INDEX updated) is the whole brief for whoever works out what to run
  this on: the solver pipeline end to end, the measured performance table from this campaign, the two bottlenecks
  stated separately (**B1 capacity** - the contracted 41-frequency band needs >= ~8.6k dofs at a 7.9/8.19 GB peak and
  dies; **B2 throughput** - ~45 s per frequency, so ~20-30 h per 40-evaluation brief even with unlimited VRAM), the
  five measurements that turn "which GPU" into candidates-per-hour-per-dollar, the hardware axes worth pricing, and
  the deliverable (`docs/evidence/HARDWARE_2026-11-<date>.md`).
- Key measured fact for sizing: **VRAM is flat at ~7.9 GB from 6,032 to 8,625 dofs**, so the peak is a per-frequency
  workspace, and 24 GB gives ~3x headroom while 48 GB allows a defensible 12 kHz mesh (the current mesh resolves the
  walls only to ~6 kHz). Throughput needs candidate-level parallelism (one GPU per lane), not a bigger card - the
  pipeline is serial per candidate today and `search/evaluate.py` was left a pure function for exactly that change.

## 2026-11-01 (06:10 EDT) - CONTRACTED BAND RELAUNCH STOPPED: the CMA neighbours break the VRAM-safe cap

- The epw 4.05 relaunch was stopped after its first rows. Two distinct failures, both recorded:
  1. One candidate hit `HORNLAB_BEAT_FUSED_BM_CUDA supports exactly one channel` - a **stale fused worker host** from
     the earlier fused probe was adopted by the run (same package fingerprint). The config carries no `cuda_fused`;
     killing hosts before a run is the fix, not a config change.
  2. The real blocker: CMA neighbours need **8,296-8,485 dofs**, over the 8,200 screen cap, so they fail as
     `mesh_too_large`. Raising the cap to admit them puts the mesh back at ~7.7-7.9 GB - the ceiling that killed the
     sweep in the first place.
- **Conclusion [measured]:** on this 8 GB card the contracted 120-12,000 Hz 1/6-octave band has no legal operating
  point. A mesh that resolves 12 kHz on the source patches needs >= ~8,600 dofs (7.9/8.19 GB peak, sweep dies); the
  smallest legal mesh (epw 4.05, 8,044 dofs) leaves the CMA population's larger neighbours over any cap that keeps
  VRAM safe. `cuda_fused`, the documented high-dof path, refuses multi-channel by design.
- **Delivered state is unchanged and valid:** the full MEH implementation (M1-M7, M10), the owner-approved pin bump,
  and the 500-10,000 Hz screens with their verified winners (T2 9.530 -> 11.894, T1 13.228 -> 14.512). The
  contracted-band work (opt-in `solve.freq_grid`, `worker_restart_every`, epw/cap experiments) is committed and the
  offline suite is green; only the run itself is not possible here.



- **`cuda_fused` is NOT an option for the MEH**: `HORNLAB_BEAT_FUSED_BM_CUDA supports exactly one channel`, so the
  fused path can never do a multi-tag solve at any dof count (the queue failed 3 candidates in 90 s; stopped).
- **The 12 kHz source-patch gate sets the mesh floor.** Measured with `run --dry-run`: epw 4.2 -> 8,625 dofs (7.9/8.19 GB
  peak, sweep dies); 3.8 -> entry_mid resolves only 11.28 kHz (refused); 4.0 -> driver 11.93 kHz (refused);
  **4.05 -> 8,044 dofs (T2) / 7,977 (T1), patches valid above 12 kHz, ~15 % less VRAM.** Both configs now dry-run OK
  with the full contracted grid: **41 frequencies, 120-12,000 Hz at 1/6 octave**.
- **Screen relaunched** on that configuration (log `runs/nights/meh_{t2,t1}_screen_120_12k.log`); the estimator says
  853 s / 803 s per candidate, i.e. a multi-hour run per brief - the measured first-candidate time goes in the evidence
  doc. Wall-resolution caveat stands and is now slightly worse: at epw 4.05 the rigid walls resolve to ~5.9 kHz, so
  the top of the band is driven-patch-accurate but wall-coarse.

## 2026-11-01 (05:10 EDT) - CONTRACTED 41-FREQUENCY BAND DOES NOT FIT THE 8 GB CARD (measured twice)

- **Run 1 (plain):** one 41-frequency sweep on the T2-A seed (8,625 dofs) ran 1,851 s and died with
  `CUDA error: unspecified launch failure (code 719)`; VRAM peaked **7,908 of 8,188 MiB** (2 s poller,
  880 samples). The screen queue then failed every candidate the same way, so it was stopped.
- **Run 2 (with the new opt-in worker recycling):** `solve.worker_restart_every: 8` restarts the host every
  8 solved frequencies. The sweep still died (`[worker_exit] ConnectionResetError`) at a **7,897 MiB** peak.
- **Interpretation [measured]:** the ceiling is **per-frequency transient**, not cumulative - the 12-frequency
  500-10,000 Hz screens also peak 7.87-7.92 GB and survive only because they make fewer draws, while 41 draws
  sit close enough to the edge that one crossing kills the sweep. Recycling cannot buy margin it does not have.
- **Committed anyway (green, useful on a larger card):** `worker_restart_every` (validated at load, forwarded
  into the solve `extra` only when set, fake-tested in `tests/test_solve_worker_restart.py`), set to 8 in both
  MEH search configs; full offline suite green.
- **Blocked decision for the owner:** (A) lower the dof cap for the contracted band (about 7,000 dofs gives
  ~35 % VRAM headroom but pushes the wall-resolution floor to ~4.7 kHz); (B) run the contracted band on a
  card with more VRAM; (C) keep the 500-10,000 Hz 12-point screen and record the band gap. The 500-10k
  screens and their verified winners stand; never rank across the two grids.
- **Not yet tried:** `solve.cuda_fused: true` (WP15 fused single-matrix assembler, documented as reaching
  ~20k quarter dofs on this 8 GB card). It is the one remaining way to fit 41 frequencies at 8,625 dofs
  without coarsening the mesh; it changes the solve hash and costs a small numeric difference (M5B parity
  0.020 / 0.039 dB).

## 2026-11-01 (03:45 EDT) - CONTRACTED 120 Hz-12 kHz BAND: OPT-IN solve.freq_grid, SCREEN RELAUNCHED

- **Owner decision:** screen over the contracted 120 Hz-12 kHz band (not the frozen 500-10,000 screen grid).
- **New opt-in `solve.freq_grid: {lo_hz, hi_hz, points_per_octave}`** (config.py). It is read from `cfg.raw`, not a
  new dataclass field, because the existing invariant test forbids a `None` in any `SolveSettings` field; the block
  is validated at load (missing key, lo >= hi, density outside 1..48, unknown key all refuse) and stripped before
  `_build`. Absent = the frozen `FREQ_GRIDS`, so no other config's solve hash moves. `mesh_spec` already takes
  `max(mode_freqs(...))`, so the mesh f_max follows to 12 kHz.
- **Both MEH search configs set it** (`120 -> 12000` at 6 points/octave = **41 frequencies**). `tests/test_config_freq_grid.py`
  (9 tests) pins: absent block = the frozen 12-point grid, present = 41 points at exactly 1/6 octave with f_max 12 kHz,
  the solve hash changes, and six bad blocks refuse. Full offline suite green after the change.
- **Two test repairs on the way** (both mine, both correct additions rather than loosened assertions):
  `tests/test_end_to_end_meh.py` maps a `*_search` config to its CAD-authored sibling's reference row.
- **Contracted-band screen relaunched** (`scratch/meh/run_meh_screen_120_12k.ps1`, logs
  `runs/nights/meh_{t2,t1}_screen_120_12k.log`, summary `meh_screen_120_12k_summary.txt`); the 500-10k run and its
  evidence are untouched. Dry-run at the new grid: 8,625 dofs (cap 9,000), 41 frequencies, tool estimate
  1,420 s/candidate; the measured per-candidate time is recorded when the first evaluations land.

## 2026-11-01 (01:45 EDT) - READINESS LINK 3 MEASURED: PASSIVE-MID NOTCH FOUND, PARTIAL AGAINST +-20 %

- The CD-only BEM sweep cannot show the port notch (an undriven L1 port is a rigid patch), so the check was redone
  properly: dense MULTI-TAG solve on the T2-A seed (10 frequencies 700-1800 Hz, 679.8 s), inner optimiser on that
  response (4.82 s, xo 673.7 Hz, order 2), mid channel muted to -300 dB, then `system_response`.
- **Result [measured]:** on axis, SPL 27.08 dB at 1000 Hz, 26.18 at 1100, 24.93 at 1200, then 34.12 at 1300 - a
  9.19 dB notch whose centre lies between 1200 and 1300 Hz. That is **+18.7 % to +28.6 %** of the 1-D 1010.8 Hz
  prediction, so the +-20 % gate is met only at the very bottom of that interval; the likely centre (~1250 Hz,
  +23.7 %) is outside. **PARTIAL, not a clean pass.** Placing it needs a 25 Hz sweep over 1150-1350 Hz.
- Logs: `runs/meh_m8/readiness3_coupled.log`, `readiness3_verdict.log`; arrays
  `runs/meh_m8/link3_muted_mid.npz`. Evidence doc section 9 row 3 updated.

## 2026-11-01 (01:20 EDT) - READINESS PROOF MEASURED ON THE STORED T2 WINNER: 4 PASS, 1 FAIL, 1 NOT PROVEN

- **Link 1 geometry PASS** (tags 1/2/10, 8,625 nodes, quarter planes; seed repairs slide 10 -> 32; walls resolve to
  ~6.1 kHz at the 12 kHz request). **Link 2 solve PASS** (channel fields + force reciprocity <= 3.2e-4).
- **Link 3 physics sanity NOT PROVEN.** The dense CD-only sweep rises to 1250 Hz then falls monotonically; no notch
  in the +-20 % window around the 1-D 1010.8 Hz. At L1 the entry port is a rigid patch unless the lumped network is
  coupled, so the check needs the network-coupled response with zero mid drive - not run.
- **Link 4 network < 2 s FAILS: 6.58 s.** `optimise_network` did 1,224 CMA evaluations (5.4 ms each) for the shipped
  T2 brief (2 mid drivers x 2 xo orders x 2 polarities x up to 160). Per-evaluation budget is met; the whole-call gate
  is missed 3.3x. Fix is a budget/combo decision, not a solver change. A cache-hit evaluate is 9.31 s wall.
- **Link 5 search moves PASS.** Two 40-evaluation screens; all six knobs moved (T2 spreads: cov_h 13.3 deg, cov_v
  23.9 deg, z_frac 0.329, across 0.388, port_along 9.9 mm, slide 25.4 mm); 38/40 T2 and 31/40 T1 OK, the rest genuine
  `invalid_geometry`; no crash.
- **Link 6 re-score for free PASS.** The stored winner `ed11d2cd3acc` re-scored with `faitalpro_6pr160` and
  `hp_hz 160` without a new solve: J 9.530280 -> 9.727026, `cached True`, both finite.
- **Blocked, recorded:** M8 step 3's quarter-vs-full comparison is impossible today - `tools/cad/meh.py` refuses a
  full model (`quadrants '1234'` -> GeometryInvalidError, quarter open shell only). M8 step 4 needs link 3's coupled
  response. **M9 is blocked:** Boundary Lab is not in this workspace (`forks/` has only beat-bem and the mesher).

## 2026-11-01 (00:45 EDT) - MEH SCREEN DONE: T2 J 9.53 -> 11.89 verified, T1 J 13.23 -> 14.51 verified

- **Two 40-evaluation CMA screens + verify top 2 each, all on the new pin on the owner's GPU** [measured]:
  T2 `runs/20261101T004552Z-screen-427d57` best `ed11d2cd3acc` screen J **9.530** (second `719aeb7a4ff0` 9.550),
  verify **11.894 / 11.804**; T1 `runs/20261101T015657Z-screen-fc1d24` best `704051ae928c` screen J **13.228**
  (second `9b6548cc2a6c` 13.556), verify **14.512 / 14.636**. Details in `docs/evidence/MEH_M8_2026-10-31.md` s8.
- **T2 beats T1 on its own brief's J** (9.53 vs 13.23 screen, 11.89 vs 14.51 verify). `lw_resid` dominates both
  (7.8 / 13.1 of J); `notch` is 0.0 in both, so the listening-window penalty is broad-band. Both winners push the
  driver to the top of the slide range (T2 `slide 35.2`, T1 36.1) and the ports low (`z_frac` 0.09 / 0.26).
- **One T2 verify design failed on a VRAM-ceiling worker reset** (7.9 GB of 8 GB) and the auto re-warm failed; after
  killing the stale BEAT host and confirming 1.36 GB idle, `verify --top 2` gave `2 designs, 0 failed`. The retry is
  recorded in the evidence doc; no tolerance changed.
- **`n_nan 12` in the winning record is not a metric failure:** `on_axis_db` is finite at all 12 frequencies and
  `n_nan_ripple 0`; the 12 NaNs are the synthesis's deliberately-NaN impedance array.
- **Two gaps opened by the screen (ISSUES):** (1) the solved grid was 12 frequencies 500-10,000 Hz, not the brief's
  120-12,000 Hz, so the objective scored `n_in_band 10` and never saw 120-500 Hz or 10-12 kHz; (2) `verify`'s own
  line says the verify mesh equals the screen mesh - only the frequency count and balloon size change, so it is a
  re-score, not a finer mesh.

## 2026-11-01 (later) - CI unblock part 2: optional-dep gates + OS-independent assertions

- Remaining pre-existing red: ~24 tests assumed optional deps that CI does not install
  (`hornlab_mesher`, `hornlab_beat_bem`, `ribs`) and 3 tests only passed on Windows. Now gated with
  the existing `requires_mesher` / `requires_beat` markers (per-test `pytest.importorskip("ribs")`
  for the three QD tests, since no `requires_ribs` marker exists).
- OS fixes, no assertion loosened: `test_cma_files_lists_every_served_pycma_log` writes fixture
  bytes and expects `len(bytes)` (Windows text mode was CRLF-inflating `version.txt` to 5 bytes);
  `test_parse_run_dir_variants_and_best_j` builds `tmp_path` paths instead of `C:/work/...`; the
  sandbox hot-swap pin now matches the shipped `if (curGeo) { ridgeCache.delete(curGeo);
  curGeo.dispose(); }`.
- Local: the 11 affected modules run 248 passed; with the three deps simulated absent, 165 passed /
  41 skipped / 0 failed. No product code changed.

## 2026-11-01 (later) - CI unblock: the preview-shape suite skips when the optional mesher is absent

- main's GitHub Actions run had been red since 2026-10-29 with a **collection error**, not a test
  failure: `tests/test_gui_preview_shape.py` imports `gui.preview`, which raises RuntimeError when
  `hornlab_mesher.preview` is not importable, and CI installs the package with `--no-deps` (the
  mesher pin is deliberately not installed there). One module-level guard now skips only when the
  mesher is absent; a **present** mesher whose pinned preview API changed still fails loudly.
- No product code changed; locally (mesher installed) the file still runs its 12 tests.

## 2026-11-01 - MERGED: PR #17 (Metal, budget hint, staged A/B, CMA covariance + pin plan) + the hardware-neutrality rule

- **Merged:** jamescollinharky's PR #17 (`36c6712`, 4 commits, 32 files, +3135/-40) squashed onto `main`: `beat_metal` backend + Mac path, Hansen `max(150, 100*N)` budget hint (`GET /api/budget-hint`), staged MACRO->SHAPE A/B harness (`tools/run_staged_search.py`), end-of-run `cma_covariance` (`run.json` + `cma/covariance.json` + GUI table), CMA-driven `pin-plan` (CLI + run-detail table), `--restarts-mode` / `--restarts-max` (CLI + Launch/Compose).
- **Docs:** all three conflicts were append-only logs. `CODE_MAP.md` was curated (took the PR's `solve/*` row; kept main's newer `metrics/`, `driver/compression`, `mesh/throat_check` rows that the PR copy would have erased); `CONTINUITY.md` ordered newest-first; `NOTES_FOR_SENIOR.md` unioned chronologically.
- **Two merge defects found by the merged test suite, fixed before landing:** (1) `auto_backend()` probed `hornlab_beat_bem` (spawning `nvidia-smi`) inside `build_argv`, so merely enqueueing a queued resume did hardware I/O and 11 GUI tests failed that pass on main; it is now platform-only - Apple Silicon -> `beat_metal`, otherwise `None`, never a silent CPU swap. (2) `--backend` was applied *after* config validation, so `cuda_fused: true` stayed in `raw` / `SolveSpec.extra` and a Metal override died at the first solve while `run.json.backend` disagreed with the snapshot; `load_config(..., backend=...)` now applies the override before validation and drops `cuda_fused` for non-CUDA backends, so `config_sha`, the snapshot and `run.json.backend` agree.
- **Owner rule (2026-11-01): results must be hardware-neutral.** The endpoint is the same data regardless of the host's solver backend (CUDA / Metal / CPU / Julia). Enforced from now on: no silent backend swapping (backend is explicit, hashed into `SolveSpec`, recorded in `run.json.backend` and dataset provenance); pooling across backends only after a measured parity check; `beat_metal` stays a lab backend until Mac<->4060 <=0.2 dB is measured.
- **Verification:** full offline suite green apart from the same 2 pre-existing environment failures as pristine `main` (`test_mesh_pin` pinned-dist mismatch; `tests/test_gui_sandbox_page.py::test_3d_hot_swap_never_scenes_per_frame`). Optimizer A/B (`osse_baseline`, budget 4, seed 1234): identical `design_hash` sequence (`8443a5763be5`, `c54661892c59`, `16905720dfc2`, `8f7d77bd7bfd`) and identical best params; J differs by <=3.0e-06 while the seed candidate - bit-identical input by construction - alone differs by 2.1e-06, i.e. solver noise, not an optimizer change. `run.json` gains only `cma_covariance` (+ `cma/covariance.json`).
- **Owed:** GPU-box `python tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both`, then paste COMPARE.md into `docs/evidence/STAGED_SEARCH_AB_2026-10-31.md`; Mac<->4060 Metal parity before Metal rows enter any campaign/compare.

## 2026-10-31 (20:28Z) - 3D EVOLUTION TRANSPARENCY: FIX RE-LANDED ON meh/integration + LIVE SERVER RESTARTED

- **Owner report (run `20261031T202159Z-screen-ba7648`, 2 improvement frames):** the 3D time-lapse still
  showed shredded / see-through triangles, caption "mesh decimated to 5781 tris".
- **Root cause was not a new renderer bug.** The hole-free decimation fix (`64ccb20`, authored on
  `feat/hardened-plan-2026-10-29`) had never reached the branch the GUI runs from: this worktree is on
  `meh/integration` (merge-base `a6bb725`), whose `gui/data.py` still had `M3D_VERSION=1`,
  `M3D_DEFAULT_CAP=6000` and the stride sampler `tris[::k]`. The live GUI (PID 7176 on 127.0.0.1:8765)
  had imported that old module, and `runs/.gui_cache/evolution_20261031T202159Z-screen-ba7648_m3d.json`
  was still `key=[1,6000]` -> 11,562-tri frames cut to 5,781/5,902 (k=2), i.e. half the surface deleted
  as scattered single-triangle holes.
- **Fix re-landed here:** cherry-picked the two code files from `64ccb20`
  (`hornlab_search/gui/data.py` `_cluster_decimate`/`_cluster_once`, `tests/test_gui_integration_phases.py`
  hole-free contract). `M3D_VERSION` 2 / `M3D_DEFAULT_CAP` 30000; stale cache regenerated for the run and
  now reads back **11,562 / 11,804 tris, `decimated:false`** (no decimation, complete surface).
  131 GUI/reader tests pass.
- **Live server:** the old `:8765` process is being restarted so it loads this module; the new process
  re-reads the regenerated cache (version 2 key) instead of the stride one.
- **Process lesson:** a code fix is not live until the long-running GUI process restarts, and a branch
  switch silently reverts the working tree. Check `D.M3D_VERSION`/cache key, not just the branch log.

## 2026-10-31 (20:45 EDT) - MEH SCREEN LAUNCHED (T2 then T1, 40 evals each, then verify top 2)

- `examples/typologies/meh_2026-10-30/meh_t1_search.yaml` added (the T1 seed through the `meh` generator; seed
  `slide_mm 14` = the repaired value for the HF108 body). Dry-run [measured]: 11,730 triangles, 6,009 dofs, 12
  frequencies 500-10,000 Hz, ~58 s/candidate, ~39 min for 40 evaluations.
- **Screen running detached** (`scratch/meh/run_meh_screen.ps1`, logs `runs/nights/meh_{t2,t1}_screen.log` +
  `meh_{t2,t1}_verify.log`, summary `runs/nights/meh_screen_summary.txt`). First T2 run
  `runs/20261101T004552Z-screen-427d57`; 4 records after ~4 min, VRAM 2.9 GB idle / 7.8 GB during assembly (8 GB
  card), one GPU job at a time.
- `tests/test_end_to_end_meh.py` now accepts BOTH seed shapes (a CAD-authored seed and a `generator: meh` seed) via
  `_seed_recipe`; the generator search config is checked against the same T2-A reference row. The old two tests
  assumed every MEH config carried `seed_params.cad`, which stopped being true when the searchable config landed.
- Full offline suite after the generator dispatch and both test fixes: exit 0.

## 2026-10-31 - MEH SEARCH UNBLOCKED: `generator: meh` DISPATCH + SEARCHABLE T2-A CONFIG

- **`design/generated.py`** gains `meh_params()` and its `materialize` dispatch (the gap M7 flagged). Recipe = the
  CAD tool's C9 defaults, then `generator.fixed`, then the knobs; `derived()` runs the layout check and the
  deterministic slide repair, a non-empty `reasons` list is `invalid_geometry`, and the mouth/depth are checked against
  the brief envelope. `tests/test_design_meh_generator.py` (5 tests) covers the knob set, the repaired seed, the three
  corner knob vectors, unknown keys and an illegal envelope.
- **`examples/typologies/meh_2026-10-30/meh_t2a_search.yaml`**: the T2-A seed authored through the generator, with
  `cov_h_deg cov_v_deg z_frac across_frac port_along_mm slide_mm` searchable (C9/T2 ranges) and everything else fixed.
  The seed carries `slide_mm 32` (the repaired value from M8 link 1), so it starts legal.
- **Cost measured by `run --dry-run` [measured]:** 11,776 triangles, 6,032 dofs (cap 9,000), mesh 5.8 s, 12
  frequencies 500-10,000 Hz with 73-angle cuts and a 512-point balloon; the tool's TOOLCHAIN estimate is 4.7 s per
  frequency = 62 s per candidate, i.e. a 40-evaluation search in ~41 min plus a 30 s cold start. The MEH screen is a
  ~41 min/brief GPU run, not a night.

## 2026-10-31 - MEH WAVE 2: M7 PIPELINE + BRIEFS + CAD SEED CONFIGS

- **`search/evaluate.py` (+283/-8)**: a brief `meh:` block takes the MEH path - mesh the `meh` CAD STEP ->
  `SolveSpec.extra.source_tags = [2, 10]` -> `meh.inner.optimise_network(..., score=objective_meh.inner_score)` ->
  `meh.synthesis.system_response` -> `metrics.compute` on the SYNTHESISED response -> objective v5 with a real
  `meh_ctx` (LW, polars, xo_hz, spl_max_db, spl_target_db, hp/boost). The record stores the BEM per-channel arrays +
  impedance matrix + `network_solution` + CAD layout. The non-MEH path is untouched (suite proves it).
- **Examples:** `examples/briefs/meh_2026-10-30/meh_home_90x60_t{2,1}.yaml`;
  `examples/typologies/meh_2026-10-30/meh_t{2a,2b,1}.yaml` (CAD recipes from `layout_out.md` final seeds).
- **CPU shape check [measured]:** t2a 6032 / 9000 dofs, t2b 5998 / 9000, t1 6009 / 9000; mouth 406 x 406 mm, depth
  380 mm, driver coupling round and matching the exit.
- **Tests:** fake mesh + fake multi-channel solver end-to-end (finite J, NetworkSolution, per-channel record arrays);
  re-scoring with another mid stem and `hp_hz` hits the solve cache (no new solve) and changes J; every new config and
  brief validates; the real CAD+BEM run is `slow`+`gpu`. Focused MEH 192 passed.
- **Deliberate adjustments:** brief envelopes use the C0 outer box (406.4 x 406.4 x 380) rather than the draft's 370;
  the T1 brief lists one CD (the M6 validator allows exactly one); T2-B uses the T2 brief's HF1440, so its port
  centroid is 39.9 mm vs the layout table's 41 mm (an HF108 T2-B needs its own brief).
- **Open gap (not M7's file):** `design/generated.py` has no `name: meh` materialize branch, so the seeds are
  CAD-native (`seed_params.cad`, `bounds: {}`) and not CMA-searchable until that ~20-line dispatch lands.

## 2026-10-31 - M8 EVIDENCE DOC WRITTEN; READINESS LINKS 1-2 PROVEN, 3-6 NOT RUN

- `docs/evidence/MEH_M8_2026-10-31.md` (INDEX updated) records, with quoted logs from `runs/meh_m8/`: the fork
  validation (CPU and CUDA), the three test-defect fixes, the pin bump, the single-tag parity table, readiness link 1
  (geometry) and link 2 (multi-tag solve), plus an explicit NOT-RUN list.
- **Link 1 caveats [measured]:** tags {1, 2, 10}, 8,625 nodes (cap 8,900), no non-manifold edges, quarter planes x0/y0
  - but the C9 T2-A seed is repaired from `slide_mm` 10 to 32 mm (`driver_hits_cd`, eleven 2 mm steps), and at the
  12 kHz request the driven patches resolve to 12.99-13.47 kHz while the rigid walls resolve only to ~6.1 kHz
  (`global_warn_source_hard`). The screen band's upper half therefore runs on underresolved walls at the dof cap.
- **Link 2 [measured]:** `channel_pressure (5, 2, 2, 37)`, force matrix symmetric to <= 3.2e-4 at 4 kHz, legacy
  fields = channel 0. An earlier 22-38 % reciprocity "failure" was MY error (quarter mesh solved with symmetry off);
  the app adapter derives the flag from the mesh and the check passes. The area-mean pressure matrix is correctly
  asymmetric by the area ratio (4.77).
- **Link 3 is PARTIAL only:** the CD-only sweep (500-4000 Hz, 8 points) shows the response still rising through the
  1-D port quarter-wave (1010.8 Hz) and peaking at 1250 Hz; the +-20 % notch check needs a denser 700-1600 Hz sweep.

## 2026-10-31 - M8 STEP 2b [owner-approved]: SOLVER PIN BUMPED TO 1efdc6f

- **Pin:** `pyproject.toml` and `TOOLCHAIN.md` now name `hornlab-beat-bem @ 1efdc6f934e16f288880b6d68e8dce8480b7a421`
  (branch `hornlab-search/meh-multisource`, pushed to `github.com/llevaachingada/hornlab-beat-bem` so the SHA is
  fetchable). Reinstalled with `pip install --force-reinstall --no-deps`; `SolveConfig` now has `impedance_matrix`
  and `source_tags` returns `(2, 10)` for a two-tag request.
- **Owner decision recorded:** the bump was approved after the M8 step-2 evidence (single-tag parity
  1.12e-5 / 5.91e-5 dB vs the 0.039 dB floor, request payload byte-identical, fork suites green on CPU and CUDA).
- **Gate:** full offline suite after the reinstall -> exit 0, no failures.

## 2026-10-31 - MEH WAVE 1 MERGE 7/7: M10 BASS BOX (7 woofer files, lumped model, build sheet)

- **`tools/bassbox.py`**: lumped sealed/vented box from a C8 cone file (C7 port branch: `L_eff`, `Q_port = 10`,
  `n_end = 2`, `Ql = 7`), electrical `Z_in`, SPL at 2.83 V and at the limit, cone excursion, port peak velocity, DSP
  (LR4 15 Hz + Linkwitz transform + five PEQ bands), `spl_max(f)` from Xmax / P_AES / 17 m/s; deterministic grids and
  a "smallest meeting the targets" search; CLI/JSON.
- **7 new `examples/drivers/*.yaml`** (`kind: cone`): bc_15tbx100, bc_18tbw100, bc_18sw115, faitalpro_15xl1400,
  faitalpro_18xl1800, eighteensound_18nlw9601, beyma_15lx60v2. Mmd/Cms derived only where the maker does not print
  them; the Beyma 8 mm vs +/-9 mm Xmax conflict and the 15TBX100 / 18NLW9601 Vas-vs-Fs inconsistencies are recorded
  in `notes` instead of being smoothed over.
- **Recommendation** (`BASSBOX_2026-10-31.md`): 1 x FaitalPRO 18XL1800, sealed 54.9 L net / 61.8 L gross
  (516 x 516 x 304 mm), LT 64.6/0.89 -> 26/0.71, five PEQ, +12.2 dB max boost; 116.4 dB at 40 Hz and
  123.1-126.6 dB at 63-120 Hz, flat 30-120 within 0.44 dB; stereo pair = +6 dB. Smallest that meets: 1 x 15XL1400
  sealed 38.0 L (113.3 dB @ 40, 119.3 dB @ 63).
- **Task-text correction:** "B4 (fs = fb, Qts 0.383, alpha 1) is -3 dB at fs" is wrong for the lossless vented box
  (alpha = 1 gives 0.0 dB at fs); the B4 constant is alpha = Vas/Vb = sqrt(2). The test asserts -3.01 dB at the
  sqrt(2) alignment (tolerance unchanged) and separately pins the literal alpha = 1 case at 0.0 dB, so the arithmetic
  is auditable. Task text should be amended.
- **Tests:** `tests/test_bassbox.py` 65 tests; full offline suite 2021 passed, 2 skipped, 20 deselected.

## 2026-10-31 - M8 STEPS 1-2 [measured]: FORK VALIDATED CPU+CUDA, SINGLE-TAG PARITY 1.1e-5 / 5.9e-5 dB

- **Step 1, fork validation (branch `hornlab-search/meh-multisource`, fork working tree
  `C:\Users\hunte\Hrns\forks\hornlab-beat-bem`):** the fork's Python suite 329 passed / 1 skipped. The full Julia
  suite (`julia --project=.../julia tests/runtests.jl`) exits 0; the CUDA-gated testsets report "broken" there
  because `julia/Project.toml` has no CUDA dependency (by design, the CUDA project is separate).
- **The M2 Julia testset had never been executed and did not pass.** Three defects, all in the test, fixed in
  commits `93ef848` + `1efdc6f`: the wire blocks are nested per channel and per plane (flatten before comparing),
  two comparisons broadcast `abs` over a `Vector`, and the hand-built request forced
  `quadrature_order=1, singular_order=1` - coarser than the app's payload - which destroyed reciprocity on the
  4-triangle fixture. Measured: 3.7e-4 reciprocity error at 100 Hz with the coarse orders and 2.2e-7 with the app's
  defaults through the real Python payload; 31.6 % in-test before the fix. Tolerances and the four properties are
  unchanged.
- **Step 1 result [measured]:** the same four properties (superposition, reciprocity, single-tag parity with the
  legacy impedance, reduced-vs-full symmetry) pass on the CPU backend (14.3 s) and on the CUDA backend (28.4 s,
  `CUDA.functional() = true`, RTX 4060 Laptop). Driver-level reciprocity 7/7 both arms.
- **Step 2, single-tag parity [measured]:** same meshes, same config, pin `760a1ec` vs fork `1efdc6f`, 5 frequencies
  200 Hz-4 kHz, 2 planes x 37 angles, CUDA. max |dSPL| = **1.12e-5 dB** (atlas finalist 92bb8946b380) and
  **5.91e-5 dB** (elite 0ae06187dc7d); max relative |dP| = 1.3e-6 / 6.9e-6. Both far inside the 0.039 dB noise floor.
  Not bitwise identical (separate GPU runs, reduction order); the request payload IS byte-identical (fork golden
  test). Pin bump awaits the owner's approval.
- **GPU hygiene:** worker hosts cleared between the pin and fork runs; baseline VRAM recorded (1.5 GB before, 0.43 GB
  after clearing); one solve at a time; `HORNLAB_BEAT_PERSISTENT_HOST=0` for the two one-off measurements.

## 2026-10-31 - MEH WAVE 1 MERGE 6/7: M4 PART 3 (INNER OPTIMISER)

- **`hornlab_search/meh/inner.py`**: `optimise_network(resp, layout_derived, brief, drivers, score=None)` enumerates
  the brief's CD x mid combinations (capped at 9), every `xo_orders` value and both mid polarities; CMA-ES
  (popsize 8, <= 160 evals, seed = brief / `search.seed` / 1234) over
  `[log xo_hz, mid_delay_ms, mid_gain_db, fill, v_rear_l]` inside the brief ranges. Default score = a local proxy of
  the C11 `lw_resid + notch + xo_lob + headroom`; `score=` receives M7's `objective_meh.inner_score` with the same
  `meh_ctx`; `inner.py` imports no objective code. Returns the C12 `NetworkSolution` (stems, xo, delay, polarity,
  gains, volumes, EQ and spl_max curves, inner_J, n_evals, seed), deterministic for a fixed seed, `ValueError` on
  hostile input.
- **Tests:** `tests/test_meh_inner_optimiser.py` (8): synthetic sources recover 0.3 ms delay (<= 0.02 ms), polarity
  -1, xo within 5 % (measured 908.58 Hz, +0.95 %, delay 0.3037 ms, 306 evals); determinism; JSON round trip;
  caller-score integration; enumeration; hostile inputs; one 60f x 2 planes x 37 angles x 2 channels candidate in
  0.0025 s (< 2 s budget). Suite: 1964 passed, 2 skipped, 20 deselected.
- **Known gap for M7:** `derived()` does not echo `dish_mm`/`spacer_mm`/`wall_t_mm`, so inner falls back to the
  reference dish placeholder `0.2 x cutout_mm`; passing them through makes `V_front` exact.

## 2026-10-31 - MEH WAVE 1 MERGE 5/7: M4 NETWORK LAYER (drivers, lumped network, DSP, limits, synthesis)

- **`hornlab_search/meh/drivers.py`**: `ConeDriver`, `CDSource`, `load_cone`, `load_cd`, `mmd_from_mms`; SI C7
  derivations; wrong-`kind` refusal; defaults for CD `fs_cd_hz`/`q_cd`/`di_ref_db` per C8.
- **`hornlab_search/meh/network.py`**: `from_bem` (exp(-iwt) per-acceleration -> exp(+iwt) per-volume-velocity),
  `entry_norton` (C7, incl. `Mmd_eff`, `L_eff`, `Q_port`, `n_end`), `cd_volume_velocity`, `couple` (the C6 Norton
  solve), `cone_excursion_peak_mm`, `port_velocity_peak`. Parity [measured, re-run by the integrator]:
  `entry_norton(n_end=2)` == `calc/meh_1d_sketch.py::Entry.norton` for MID4/MID65 at rtol 1e-12 over 60 frequencies;
  `couple` reproduces `calc/meh_zmatrix_check.py`'s direct solve at 1e-9 for one and two entry groups; `mmd_from_mms`
  gives 11.9 g (6FE100) and 3.8 g (4FE32); one-entry resistive-load energy balance at 1e-9.
- **`hornlab_search/meh/dsp.py`**: Linkwitz-Riley (orders 2/4/8 via squared Butterworth), Butterworth, delay,
  polarity, peaking biquad, `smooth_oct`, `system_eq` (1/3-octave power smoothing, boost clipped at `max_boost_db`,
  unlimited cut). LR4 low+high sum to unit magnitude within 1e-9.
- **`hornlab_search/meh/limits.py`**: `spl_max` with the five C11 limits (Xmax, cone P_AES, port air 17 m/s, amp
  volts, CD P_AES via sens + DI delta), first limit wins per frequency, binding limit reported.
- **`hornlab_search/meh/synthesis.py`**: `system_response` sums `H_net * U` per plane/angle (+ sphere), returns a
  `Response` `metrics/compute.py` consumes unchanged, `impedance` = nan.
- **Not yet in this layer:** `inner.py` (CMA inner optimiser) is a separate follow-up branch; M7 must not be blocked
  on it for the config/brief work, but the end-to-end path needs it.

## 2026-10-31 - MEH WAVE 1 MERGE 4/7: M6 OBJECTIVE v5 ("meh") + THE BRIEF `meh:` BLOCK

- **`objective/scalar_meh.py`**: `objective_meh(metrics, resp, ok, target, weights, params, meh_ctx)` = the v4 pattern
  terms on the SYNTHESISED response (re-using the v4 functions, no duplicated maths) plus `lw_resid`, `notch`,
  `xo_lob`, `headroom` per C11; tolerances/weights from the brief block, defaults = the C11 table; graded penalty,
  never nan/inf. `inner_score(meh_ctx, weights)` is the cheap same-terms call M4's inner optimiser uses via M7.
- **`objective/versions.py`**: 5 registered in `SUPPORTED_OBJECTIVE_VERSIONS`.
- **`config.py`**: additive `meh:` block validation (exact keys/types, the C10 ranges, unknown keys refuse, driver
  stems that do not exist yet warn instead of failing while M1 is landing). v1-v4 briefs and hashes unchanged.
- **Coupled touch points in `search/evaluate.py`** (M7's file, unavoidable for the version/scorer gate):
  `_OBJECTIVE_SCORERS` gains 5 and `MehParams` is the v5 params class. The MEH evaluation BRANCH (building
  `meh_ctx`, synthesis, inner optimiser, recording) is still M7's; until it lands, `_score_v5` raises when no
  `meh_ctx` is available rather than silently scoring a half-empty context.
- **Tests:** `tests/test_objective_meh_terms.py`, `tests/test_objective_meh_scalar.py`, `tests/test_config_meh.py`;
  `tests/test_dataset_record.py` updated only where version 5 becomes a supported value.

## 2026-10-31 - MEH WAVE 1 MERGE 3/7: M1 DRIVER FILES (8 files, C8)

- **`examples/drivers/`**: 8 new files (5 `cone`: bc_6ndl38, faitalpro_6pr160, eighteensound_6nmb420, bc_4ndf34,
  faitalpro_4fe32; 3 `compression_meh`: faitalpro_hf1440, faitalpro_hf108, bc_dh450) + `tests/test_meh_driver_files.py`
  (29 tests). Every number transcribed from the repo's own datasheet extraction
  (`docs/research/typologies/mini_meh_2026-10-29/appendix_A_web_survey_raw.md` s8, rows read from the maker PDFs and
  labelled `V`); `mmd_g`/`cms_mm_per_n` are marked `derived` with the formula in `notes`; unpublished mechanicals
  (`frame_od_mm`, `motor_od_mm`, `dish_mm`, CD `duct_mm`) are omitted and named, never guessed.
- **Deviation recorded:** M1's task file says to open each datasheet PDF. This lane had no web access, so it
  transcribed the repo's verified s8 table instead. The CD duct depths stay at the C9 [inferred] 40/25/25 mm until a
  drawing read or the M8 measurement.
- **Tests:** `tests/test_meh_driver_files.py` 29/29 (re-run by the integrator).

## 2026-10-31 - MEH WAVE 1 MERGE 2/7: M3 SEVERAL-SOURCE-TAG SOLVE ADAPTER

- **`types.py::Response`** gains the five optional C5 fields (`channel_tags`, `channel_pressure`,
  `channel_sphere_pressure`, `impedance_matrix`, `tag_areas_m2`), default `None`; no existing field changed.
- **`solve/beat.py`**: `SolveSpec.extra["source_tags"]` -> `velocity_sources = {t: 1.0}` + `impedance_matrix=True`;
  absent key keeps today's config byte-for-byte (golden solve-hash test); an installed `SolveConfig` without
  `impedance_matrix` raises ConfigError naming M8's pin bump; per-tag mesh pre-flight from `mesh_meta.json`;
  `channel_*` copied into `Response` with legacy fields = channel 0. `solve/bempp.py` refuses `source_tags`.
- **`dataset/record.py`** stores the three MEH complex arrays plus `channel_tags`/`tag_areas_m2`/`network_solution`
  (schema stays 1; old records load unchanged). `solve/cache.py` npz round trip extended because its module-level
  field assertion would otherwise fail at import - a required coupled change, no test fixture edited.
- **Tests:** `tests/test_solve_meh_fake.py` (golden single-tag config + hash, multi-tag payload, old-pin refusal,
  tag pre-flight, 2-channel -> Response shapes, bempp refusal, cache round trip) and
  `tests/test_dataset_meh_record.py`.
- **Carried (ISSUES):** multi-tag solves raise ConfigError until M8 bumps the solver pin to M2's fork branch.

## 2026-10-31 - MEH WAVE 1 MERGE 1/7: M5 MEH L1 CAD TOOL + MULTI-LABEL STEP ROUTE

- **New `tools/cad/meh.py` (822 lines)**: ports `calc/meh_layout.py` (`geometry`, `_wall_frame`, `check`,
  `from_fractions`, `_narrowest`) with identical numbers; the deterministic slide repair is logged in
  `derived()["repairs"]`; T2-A and T1 `derived()` match the reference for z_c, z_m, mouth W x H, port z, path to
  diaphragm and f_h within 0.2 mm / 1 Hz [agent-reported, tests re-run below].
- **L1 solid**: outer box minus horn air (planar-quad frustum + mouth roundover) minus the CD bore; full port
  outlines imprinted as flush coplanar patches, then quarter-cut at x = 0 / y = 0 and exported as an OPEN shell (the
  symmetry planes are not BEM faces). Quarter inventory: T2 driver 1 + entry_mid 1; T1 driver 1 + entry_mid 2.
- **`mesh/step_build.py`**: `meh` registry entry, `entry_mid` -> tag 10 / `entry_aux` -> 11, quarter import with
  `quadrants="1"`, fine sizing near every driven face, frequency hard-fail on every driven face, per-tag area +
  centroid in `mesh_meta.json`. `multicell`/`plughorn` paths unchanged.
- **Known gaps (carried to ISSUES):** seed renders not produced (`pyvista` absent from the venv, no installs
  permitted); `cd_duct_mm = 0` refused (no disc face without a bore); unknown cone (cutout, depth) pairs refused
  until M1 lands.

## 2026-10-31 (evening) - CMA-driven knob pin recommendations

- `search/pin_from_cma.py`: pin when `σ√C_ii` share and std are small, unless Spearman
  `|ρ|` vetoes; values from `best.json`. CLI `hornlab-search pin-plan --run <id>` writes
  `pin_plan.json` + `PIN_PLAN.md` (+ optional `--write-config`). Run detail shows the table
  under CMA covariance. Offline: `tests/test_pin_from_cma.py`.

## 2026-10-31 (evening) - CMA covariance dump + GUI table

- End of each CMA search writes `run.json` `cma_covariance` (+ `cma/covariance.json`):
  per-knob `C_ii` / `σ√C_ii` shares and top eigenpair loadings (unit-box search distribution).
  Restart arms carry a compact `covariance` block. GUI run detail shows the table when present.
  Offline: `tests/test_cma_covariance.py`.

## 2026-10-31 (evening) - Staged A/B knob schedule disclosure

- `tools/run_staged_search.py` writes **active vs fixed/pinned** knobs per stage into
  `plan.json` (`knob_schedule`) and a **Knob schedule** section at the top of `COMPARE.md`.
  Stage B `fixed` is where macros show as pinned to A's best. Offline tests updated.

## 2026-10-31 (evening) - Mac .venv + Metal smoke + GUI auto-backend

- Project `.venv` (Python 3.12.4) with `pip install -e ".[dev,crosscheck]"` — mesher, beat,
  plots, bempp all import; Metal `ready` via Julia. Doctor: 9 PASS / 2 FAIL (expected: no
  nvidia-smi / beat_cuda).
- Dry-run OK: freeform_hv, conical, tractrix. Short `--backend beat_metal --budget 5` searches
  OK: tractrix 137→111, freeform_hv 33.3→30.8, conical 154.7→35.0.
- GUI `jobs.py`: when CUDA is unavailable, search/run auto-append `--backend beat_metal` (else
  `beat_cpu` if that is ready). Launch on this Mac no longer dies on YAML `beat_cuda`.
- GUI restarted on `.venv/bin/python`. Mac↔4060 A/B still owed before mixing Metal into CUDA
  leaderboards.

## 2026-10-31 (evening) - Hansen budget heuristic for Launch/Compose

- **`search/budget_heuristic.py`:** suggested evals = `max(150, 100·N)` from Hansen's
  hard-problem floor (~100·N … 300·N² in c-cmaes; we keep the linear end for GPU BEM).
  IPOP/BIPOP add `(1+max)×screen` leftover room (BIPOP +25 %). Cap 5000 (GUI allow-list).
- **`GET /api/budget-hint`:** `n_knobs=` or `config=` + optional `restarts_mode`/`restarts_max`.
- Launch auto-fills when config/restarts change (until the user edits); Compose offers
  "Use suggested". Glossary updated. Offline: `tests/test_budget_heuristic.py` + GUI API test.

## 2026-10-31 (evening) - Launch/Compose IPOP/BIPOP controls

- CLI: `search --restarts-mode {ipop,bipop,off}` + `--restarts-max N` (overrides config;
  updates `cfg.raw` so the run snapshot matches). GUI Launch + Compose search forms expose the
  same via allow-listed `jobs.py` args. Glossary tips added. Offline: argv allow-list + CLI apply
  helper + search smoke with `--restarts-mode ipop`.

## 2026-10-31 (later) - beat_metal + Mac path for staged A/B

- **P3 slice:** `beat_metal` added to `BACKEND_NAMES` / `BeatBackend` / CLI `--backend` /
  `source_motion` allow-list. No nvidia-smi VRAM poll on Metal; `cuda_fused` stays CUDA-only
  (Metal's fused assembly is the library default).
- **Staged harness:** `--backend auto|beat_cuda|beat_metal|beat_cpu|bempp_cpu` — on Darwin
  `auto` → `beat_metal` and clears `cuda_fused` on emitted configs. README has Mac install +
  run steps. Offline tests cover the rewrite.
- Still owed: project `.venv` + `pip install -e ".[dev,crosscheck]"` on this Mac, then
  `doctor` + the staged A/B; Mac↔4060 A/B before mixing Metal into CUDA leaderboards.

## 2026-10-31 - STAGED SEARCH A/B PROTOCOL + CHAINING HARNESS

- **Why:** refine CMA on high-dim typologies (macro → shape → joint polish vs one joint run).
- **Configs:** `examples/typologies/staged_ab_2026-10-31/` — joint budget 60 vs stages 20+20+20 on
  `crease__core_law` (same seed lineage / brief as the smoke cell).
- **Harness:** `tools/run_staged_search.py` — seeds Stage B from A's `best.json`, builds Stage C
  with ±12 % boxes and `sigma0=0.06`, writes `COMPARE.md`. Offline tests:
  `tests/test_tools_staged_search.py` (10 passed).
- **Synthetic coupled A/B (no GPU):** staged final J **0.100** vs joint **0.302** (seed 1.262,
  coupling 0.7, budget 60) → **staged+polish wins**. Evidence:
  `docs/evidence/STAGED_SEARCH_AB_2026-10-31.md`.
- **Acoustic GPU A/B:** blocked on this Mac (no CUDA / no project venv / `cma` missing). GPU-box
  command recorded in the evidence doc. Do **not** promote into `hornlab_search/search/` until
  that run lands. Parallel priority unchanged: objective term normalisation.
- Docs: INDEX, CODE_MAP, ISSUES updated this entry.

## 2026-10-30 (18:10 EDT) - MEH INTEGRATION BRANCH PULLED; BASELINE GREEN AFTER TWO PRE-EXISTING REDS

- **Local work preserved first.** `feat/hardened-plan-2026-10-29` had uncommitted night-result work (CONTINUITY
  16:04Z entry, INDEX rows, `HANDOFF_NEXT_RUNS_2026-10-30.md`, `SWARM_PLAN_2026-10-30.md`,
  `examples/typologies/atlas_2026-10-30/atlas__osse_ext_throat.yaml`) -> committed as `97f1490` before switching.
- **Hand-off section 0 done.** `meh/integration` created from `origin/ccr-4978c80b-tvvcgv`; `origin/main` merge was
  already up to date (no CONTINUITY/ISSUES entries lost).
- **Baseline was RED on two tests unrelated to MEH** (both pre-existing at the hand-off commit):
  1. `test_gui_sandbox_page.py::test_3d_hot_swap_never_scenes_per_frame` pinned the pre-1bdd1b7 one-liner
     `if (curGeo) curGeo.dispose();`; the ridge-overlay commit folded the ridge-cache eviction into that statement.
     The assertion now pins the current, stricter contract (evict `ridgeCache` **and** dispose) - not a loosening.
  2. `test_param_catalog.py::test_committed_json_is_byte_identical_to_a_fresh_build` failed on CRLF vs LF: this
     checkout had `core.autocrlf=true` while the generator writes LF. Fixed by setting `core.autocrlf=false` locally
     and re-checking-out the tree (index content unchanged, 0 tracked files with CRLF), not by touching the test.
- **Baseline after the fixes [measured]:** `.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not
  crosscheck" -q` -> exit 0, 100 % (no failures). Research scripts reproduce: `meh_1d_sketch.py` conical-horn check
  4.45e-16; `meh_zmatrix_check.py` 4.44e-16 (one group) / 5.86e-16 (two groups); `meh_layout.py` prints the
  layout_out.md seed table (T2-A/HF1440 and T1 OK, the three known-bad seeds unchanged).
- **GPU is busy:** night queue `n2_gapfill_2026-10-30` (started 16:56, 7 jobs, no cutoff) is running
  `search --resume runs/20261030T111108Z-screen-377bbe` with a live Julia host. Per CLAUDE.md no MEH GPU job starts
  until that queue finishes - wave 1 (CPU/cloud code) proceeds meanwhile.

## 2026-10-30 (late) - MEH CHIEF-IMPLEMENTER HAND-OFF

- `docs/meh/CHIEF_IMPLEMENTER_HANDOFF.md`: pull steps for `C:\Users\hunte\Hrns\hornlab-search`, wave order with gates,
  a six-link readiness proof that the MEH is optimisable end to end, and the follow-on optimisation studies.

## 2026-10-30 - MEH UN-DEFERRED BY OWNER; DESIGN FIXED; IMPLEMENTATION HAND-OFF IN `docs/meh/` (zero GPU, no package code)

- **Owner decisions:** MEH top + separate bass box (30-120 Hz flat); top fits a 16 in square face (406 mm), corner-hung,
  studio-monitor depth (380 mm assumed); home hi-fi / DJ practice / booth, critical listening, level of a powered 12 in
  PA; DSP + FIR on every channel; not for sale. Owner gave the orchestrator architecture, labels, typologies, solves and
  scoring, with the rest handed to cheaper sub-agents.
- **Design fixed:** T2 `meh2_6x2` primary (1.4 in CD + 2 x 6.5 in on top/bottom walls, 90x60, XO 650-1100 Hz, HP 120 Hz);
  T1 `meh2_4x4` secondary (1 in CD + 4 x 4 in, XO 1-1.5 kHz, HP 160 Hz). L1 solve = flush port patches as driven tags
  (2 CD, 10 mids), one BEM solve gives per-channel transfers + impedance matrix, drivers/xo/delay/fill/rear volume
  optimised per geometry by an inner optimiser. Objective v5 = v4 pattern terms on the summed system + `lw_resid`,
  `notch`, `xo_lob`, `headroom`; `flat` off (FIR).
- **New research [measured]:** `calc/meh_layout.py` layout feasibility in the 16 in box (horn ~150 mm, mouth 330 x 191;
  reparameterised knob box 56-93 % feasible vs 12-29 % naive; seeds T2-A/T2-B/T1); `calc/meh_bassbox_sizing.py`
  (15 in / 18 in long-throw for 30-120 Hz).
- **Hand-off:** `docs/meh/README.md` (waves, models, dispatch prompt, merge order) + `00_MEH_CONTRACTS.md` + M1-M10 task
  files. Wave 1 (parallel, cloud): M1 drivers, M2 solver fork, M3 adapter, M4 network, M5 CAD, M6 objective, M10 bass box;
  wave 2: M7 pipeline; wave 3 (owner GPU box): M8 validation + screen, M9 Boundary Lab.
- `CLAUDE.md` gained one ownership pointer to contracts C13; `NEXT_DEV_PRIORITIES.md` P13.

## 2026-10-29 (20:15 EDT) - MINI MEH RESEARCH: WEB LANE FOLDED IN, CLAIMS SPOT-CHECKED (zero GPU, no code)

- **Web lane (Sonnet) returned:** raw survey kept verbatim as `docs/research/typologies/mini_meh_2026-10-29/appendix_A_web_survey_raw.md`
  (sources, 8 targets, design-rules digest, product-size and driver tables, conflicts). Dossier s0-s13 rewritten around it.
- **Orchestrator spot-checks (all match):** JW DH350 MEH page, Solana page, US 8,284,976 claims 1/4/5/6 + notch/port passages,
  Boundary Lab releases (v0.5.0 still latest) and its `Multi_region_SAWMOD` example, MEH Studio repo. US 6,411,718 claim text
  not re-readable here (503/403); kept at the lane's label.
- **Key external facts:** JW DH350 MEH = the owner's size class (2 x 6.5-inch + 1-inch CD + 2 PR, 470 x 260 x 200 mm, ~15 L net,
  60 Hz-16 kHz +-2 dB, 106 dB, taps lambda/4 at the 1.0-1.2 kHz XO); Solana 4 x 6.5-inch + 1-inch, 109/120 dB, 90 x 90 to 700 Hz,
  no dimensions; no Danley box in this size class (SH75 62 L, SM-60F 113 L); Boundary Lab solves several voltage-driven drivers +
  FEM chambers + port interfaces in one coupled system (Mmd only, no passive radiators); no AES/JASA paper on MEH found.
- **New 1-D result [measured]:** the mid's own reflection notch depends only on the horn; in a cone it sits 1.4-1.8x above
  c/4d, but a 35 mm compression-driver duct pulls it to ~1.6-1.9 kHz for close entries (the practitioners' ~1.5 kHz ceiling):
  the CD's internal depth must be modelled (`calc/notch_vs_path.md`).
- **Corrections (dossier s8; owner-file items appended to `NOTES_FOR_SENIOR.md`):** frozen plan's "MEH geometry path exists"
  (tag names only); `DRIVER_MODEL.md` "Boundary Lab issue #78" is timini/horn-simulation issue #78 (rule unchanged); BL
  "symmetry Off" applies to plugin assemblies, coupled projects run with symmetry xy; draft's "6.5-inch needs a 1.4-inch CD".
- **Still open:** owner decisions in dossier s13 (bass route, size number, use/coverage, mid complement, DSP, J terms).

## 2026-10-29 (18:45 EDT) - MINI MULTIPLE-ENTRY HORN: RESEARCH PASS, DRAFT PUSHED (zero GPU, no code)

- **Owner request:** internal + external research toward a mini multiple-entry horn (Synergy/Unity class, smaller than
  JW Sound's Solana): one compression driver + 2 x 6.5-inch or 4 x 4-inch mids on ports, very small box, strong EDM bass.
  Research and plan seeds only; nothing wired. MEH was owner-deferred 2026-10-24 (G17); reopened for research only.
- **Dossier (draft):** `docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` + folder `mini_meh_2026-10-29/`
  (`calc/` = CPU research scripts and outputs, not imported anywhere). Sections 7-8 (external findings, corrections)
  wait on the Sonnet web lane (Danley primaries, JW Sound Solana, current Boundary Lab, small DIY MEHs, driver T/S).
- **Findings so far [measured / verified]:** mids cannot do EDM bass (4 x 4-inch ~93 dB, 2 x 6.5-inch ~97-101 dB at 50 Hz,
  1 m half space; 115 dB needs ~840 cm^3 Vd) -> 2-way mini top + sub, or compact 3-way with woofers; a 300 mm mouth holds
  90 deg only to ~940 Hz; 1-D MEH sketch: the CD notch sits ~1.15-1.4 x the port corner and deepens as entries move toward
  the throat (-18 dB at 20 mm, -2 dB at 70 mm), best sum near the quarter-wave limit; per-source solve + impedance
  matrix + lumped drivers equals the direct solve to 6e-16 (the plan's core decomposition).
- **Solver/mesher inventory (fork source read 2026-10-29):** the Julia engine already solves several channels on one
  factorization and returns per-channel pressures; the Python package refuses more than one tag (`config.py:462`);
  no mutual impedance matrix yet. The mesher has MEH tag names 8-12 but no MEH builder (corrects the frozen plan's
  "geometry path is already there").
- **Owner questions:** separate sub or bass in the box; a size number; use case and coverage; 4 x 4-inch vs 2 x 6.5-inch;
  DSP per channel; which new J terms (dossier s13).

## 2026-11-02 - GUI: FREQUENCY-AXIS RANGE FROM THE BRIEF BAND + SCORING-FLOOR f0 MARKER; MEH BENCH SCRIPTS

- **Landed (was uncommitted in this tree):** `charts.js` now clips every plot mark to the domain (the band
  rectangle no longer bleeds into the margins), derives 1/2/5 x decade ticks plus the exact endpoints
  (`logTicks`), takes its axis domain from the brief-band union with honest fallbacks (never a guessed
  range), keeps the isobar raster blank in the band margins (NaN sentinel so marching squares cannot
  extrapolate edge colour), and marks the objective scoring floor `f0` as an edge-aware dashed vertical
  marker drawn after the grid.
- `app.js`: new `freqAxisLimits` (union of the brief band and the solved grid); every run-detail frequency
  chart, the campaign overlay and compare route through it (no hardcoded FT tick list); c-bw and c-di carry
  the `f0` marker; `isobarMap` receives `xlim`/`f0`; `seedDerivationHtml(feas, objective)` names the
  objective actually in play, and the one-argument call keeps the original v3 wording.
- `gui/data.py`: `run_detail` passes the committed `objective` block through additively — absent stays absent,
  no shape invention.
- New offline pins `tests/test_gui_freq_range.py` (checks (a)-(d) in its docstring); the two existing pinned
  call-site assertions were updated to the new signature.
- **Verification [measured]:** `python -m compileall -q hornlab_search/gui tools/bench tests/test_gui_freq_range.py`
  -> OK; `.venv\Scripts\python.exe -m pytest tests/test_gui_freq_range.py tests/test_gui_brief_authoring.py
  tests/test_gui_param_tips.py -q` -> **37 passed**.
- `tools/bench/` committed (`cpu_vs_cuda_meh`, `cuda_cpu_40designs`, `cuda_threads`, `full_range_cuda_cpu`):
  the CPU-vs-CUDA MEH benchmark scripts behind the 2026-11-02 bench runs. `__pycache__` stays git-ignored.
- No solver, config, pin or tolerance changes.

## 2026-11-01 - HARDWARE DECISION STUDY: RENTAL FIRST; FULL-WALL MESH IS MUCH LARGER

- Owner clarified this is a theoretical rent-versus-buy decision; no rental machines configured. Rental spend $0, no new BEM solves/screens. `docs/evidence/HARDWARE_2026-11-01.md` records the study, current published rates and explicitly conditional costs.
- Four CPU-only diagnostic builds on the fixed T2 seed: EPW 4.2 => 8,625 dofs / 16,909 triangles, global valid-to 6,015 Hz; EPW 6 => 17,211 / 33,938, global 8,583 Hz; EPW 8.4 => **33,959 / 67,245, global 12,009 Hz, valid**; EPW 9 => 38,819 / 76,919, global 12,864 Hz, valid. This is validator sizing, not acoustic convergence or a proven minimum over all geometries. Shipped configs untouched.
- Source audit of unchanged pin `1efdc6f`: standard CUDA uses fixed dense direct solves, repeating LHS/refactorization per channel; CPU/Metal GMRES cost model is not the CUDA route. At N=33,959/E=67,245 the concurrently live operators+identities+LHS alone require **85.410 GiB** before extra workspace. A 24/32 GB card is a coarse-mesh test candidate; the first requested full-wall discrete tier worth testing is H200 141 GB. No fit/runtime claim was measured on it.
- Historical NPZ/NDJSON extraction corrects the handoff's seed/winner attribution: T2 winner is N=5,872/E=11,456 with baseline/peak 513/7,575 MiB; T1 winner N=6,249/E=12,205 with baseline/peak 330/7,840 MiB. Across 69 successful historical screen candidates, assembly is the largest reported engine stage (~2 s/frequency, versus ~0.2 s solve). No 12 kHz throughput inference follows.
- Flat device-use peaks do not prove constant workspace; CUDA 719 does not uniquely establish OOM. Current `vram_41f.csv` differs from the earlier trace described in M8 and has no verified idle baseline. These refine the older capacity diagnosis; the recorded failures and prior screen winners remain unchanged.
- Shared-host multi-GPU work is not a one-line change: evaluator/persistence side effects, global lock, all-host cleanup and worker registry identity need isolation. Two separate single-GPU machines, one brief each, are a simpler future deployment test. All cross-card, unified-memory, lane-scaling and overnight measurements remain open. `doctor`: 11/11 checks passed; evidence excerpts checked against decoded bytes. No production code/pins/tolerances changed.

## 2026-10-31 (20:28Z) - 3D EVOLUTION TRANSPARENCY: FIX RE-LANDED ON meh/integration + LIVE SERVER RESTARTED

- **Owner report (run `20261031T202159Z-screen-ba7648`, 2 improvement frames):** the 3D time-lapse still
  showed shredded / see-through triangles, caption "mesh decimated to 5781 tris".
- **Root cause was not a new renderer bug.** The hole-free decimation fix (`64ccb20`, authored on
  `feat/hardened-plan-2026-10-29`) had never reached the branch the GUI runs from: this worktree is on
  `meh/integration` (merge-base `a6bb725`), whose `gui/data.py` still had `M3D_VERSION=1`,
  `M3D_DEFAULT_CAP=6000` and the stride sampler `tris[::k]`. The live GUI (PID 7176 on 127.0.0.1:8765)
  had imported that old module, and `runs/.gui_cache/evolution_20261031T202159Z-screen-ba7648_m3d.json`
  was still `key=[1,6000]` -> 11,562-tri frames cut to 5,781/5,902 (k=2), i.e. half the surface deleted
  as scattered single-triangle holes.
- **Fix re-landed here:** cherry-picked the two code files from `64ccb20`
  (`hornlab_search/gui/data.py` `_cluster_decimate`/`_cluster_once`, `tests/test_gui_integration_phases.py`
  hole-free contract). `M3D_VERSION` 2 / `M3D_DEFAULT_CAP` 30000; stale cache regenerated for the run and
  now reads back **11,562 / 11,804 tris, `decimated:false`** (no decimation, complete surface).
  131 GUI/reader tests pass.
- **Live server:** the old `:8765` process is being restarted so it loads this module; the new process
  re-reads the regenerated cache (version 2 key) instead of the stride one.
- **Process lesson:** a code fix is not live until the long-running GUI process restarts, and a branch
  switch silently reverts the working tree. Check `D.M3D_VERSION`/cache key, not just the branch log.

## 2026-11-01 (08:20 EDT) - WRAP-UP: FULL OFFLINE SUITE GREEN AT THE TIP; PR TO `main` OPENED

- **Final gate [measured]:** `.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -q`
  at `task/hardware-decision-2026-11-01` -> **exit 0**, no failures. This is the first full run since the last config
  edits (epw 4.05 / screen cap 8,200 / `solve.freq_grid` / `worker_restart_every`), so the tip is gated, not just the
  code merges.
- **Contents of the PR:** the complete MEH implementation (M1-M7, M10), the solver fork pin bump to `1efdc6f` with its
  validation evidence, both 40-evaluation screens with their verified top-2 arms (T2 9.530 -> 11.894, T1 13.228 ->
  14.512), the six-line readiness proof with its one FAIL and one PARTIAL stated plainly, the hardware audit and
  hand-off, and the honest record of the three blocks (8 GB band ceiling, CAD quarter-only, Boundary Lab absent).
- PR base `main`, head `meh/integration`, which now carries the hardware branch (fast-forward; the hardware branch is
  a descendant of the integration tip). Background job board: all sessions reconciled, none active.

## 2026-11-01 (07:55 EDT) - HAND-OFF TIDIED: WITHDRAWN VRAM CLAIM REMOVED FROM THE AXES AND UNIFIED-MEMORY SECTIONS

- The s2a corrections block covered s2, but s5 (axes table) and s5b (unified memory) still asserted the withdrawn
  "flat per-frequency workspace" reading as fact. Both now state what is actually established (device use sits within
  ~300 MiB of the ceiling whenever a 12 kHz MEH mesh solves; the pinned CUDA path holds several N x N and N x E
  complex64 operators plus identity caches, ~85 GiB at the first globally valid whole-wall mesh) and point at s2a.
- Removed a duplicated 5-frequency row my earlier table patch had introduced. No measured value changed.

## 2026-11-01 (07:40 EDT) - HARDWARE AUDIT REVIEWED; FOUR OF MY CLAIMS CORRECTED IN THE HAND-OFF

- The fresh-eyes audit (`docs/evidence/HARDWARE_2026-11-01.md`, Codex session) is sound. I reproduced its two
  load-bearing numbers from the stored data: the screen winners are **5,872 / 6,249 dofs** (not the 6,032 / 6,009
  seed meshes I paired with their timings), and the winners' `meta.timings` give **assembly 23.72 s, solve 2.38 s,
  field 0.19 s, total 35.54 s over 12 frequencies** - assembly is ~67 % of engine time, as the audit says.
- **Withdrawn from my hand-off:** the "~12x for 1.44x elements" scaling claim (it divided a FAILED sweep by 41 and
  used cold-start guesses - there is no valid seconds/frequency at 8.6k dofs); the "flat ~7.9 GB workspace" reading
  (`nvidia-smi` total use + CUDA.jl caching is not live working set, and the CSV that backed it was overwritten by a
  later poller run, now 558 samples starting at 5,643 MiB with no idle baseline); the "25-35k elements" full-wall
  guess (the first globally valid T2 mesh is **33,959 dofs / 67,245 triangles**, ~85 GiB static on the pinned CUDA
  path, so 141 GB is the first viable tier); and "lanes are a one-line change" (five concrete surfaces).
- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` now carries a s2a corrections block so the repo does not hold two
  contradictory records. The audit's conclusion stands: rent a short pilot before buying, and the full-wall 12 kHz
  target is much larger than this pass assumed.

## 2026-11-01 (07:05 EDT) - HARDWARE HAND-OFF EXTENDED: UNIFIED MEMORY + THE MEASURED BASELINE

- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` gained two things the next agent needs:
  1. **The measured baseline table** with every data point this campaign produced, plus the derived
     per-frequency rates: ~3.6 s/frequency at 6,032 dofs and ~40-53 s/frequency at 8,625 dofs. That is a
     **~12x cost for a 1.44x element increase**, which is not a clean exponent - it is consistent with
     elements-squared assembly PLUS a change of solver path between those sizes. Separating those terms is
     named as the first measurement of the assignment.
  2. **A unified/coherent-memory section** with the configurations worth testing and the reason the test is
     bandwidth, not capacity: the per-frequency working set is a flat ~7.9 GB, so spilling it over a
     PCIe-class link would cost 5-50x, while NVLink-C2C (GH200/GB200) and Apple's shared memory have real
     bandwidth. Table covers GH200/GB200, Apple M3/M4 Max/Ultra (Metal path), MI300A (ROCm), Strix-Halo-class
     APUs as the negative control, and CPU-only. Every non-CUDA option carries a validation task: the pinned
     fork `1efdc6f` is CUDA-validated only, so Metal/ROCm must clear single-tag parity (<= 0.039 dB) and the
     four multi-tag properties before a campaign may use them.

## 2026-11-01 (06:50 EDT) - EVIDENCE DOC AND INDEX CORRECTED TO MATCH THEIR OWN CONTENT

- `docs/evidence/MEH_M8_2026-10-31.md` was still titled "readiness links 1-2 (partial)" although it had grown to the
  six-line readiness proof, both screen pairs with verify arms, the two hard blocks and the band finding. Title
  corrected (with a dated note) and the `docs/INDEX.md` entry rewritten to state the actual verdicts: links 1/2/5/6
  PASS, link 4 FAIL, link 3 PARTIAL, screens verified, blocks listed. No measured number changed.

## 2026-11-01 (06:40 EDT) - HARDWARE HAND-OFF WRITTEN (next agent: compute configuration)

- `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` (INDEX updated) is the whole brief for whoever works out what to run
  this on: the solver pipeline end to end, the measured performance table from this campaign, the two bottlenecks
  stated separately (**B1 capacity** - the contracted 41-frequency band needs >= ~8.6k dofs at a 7.9/8.19 GB peak and
  dies; **B2 throughput** - ~45 s per frequency, so ~20-30 h per 40-evaluation brief even with unlimited VRAM), the
  five measurements that turn "which GPU" into candidates-per-hour-per-dollar, the hardware axes worth pricing, and
  the deliverable (`docs/evidence/HARDWARE_2026-11-<date>.md`).
- Key measured fact for sizing: **VRAM is flat at ~7.9 GB from 6,032 to 8,625 dofs**, so the peak is a per-frequency
  workspace, and 24 GB gives ~3x headroom while 48 GB allows a defensible 12 kHz mesh (the current mesh resolves the
  walls only to ~6 kHz). Throughput needs candidate-level parallelism (one GPU per lane), not a bigger card - the
  pipeline is serial per candidate today and `search/evaluate.py` was left a pure function for exactly that change.

## 2026-11-01 (06:10 EDT) - CONTRACTED BAND RELAUNCH STOPPED: the CMA neighbours break the VRAM-safe cap

- The epw 4.05 relaunch was stopped after its first rows. Two distinct failures, both recorded:
  1. One candidate hit `HORNLAB_BEAT_FUSED_BM_CUDA supports exactly one channel` - a **stale fused worker host** from
     the earlier fused probe was adopted by the run (same package fingerprint). The config carries no `cuda_fused`;
     killing hosts before a run is the fix, not a config change.
  2. The real blocker: CMA neighbours need **8,296-8,485 dofs**, over the 8,200 screen cap, so they fail as
     `mesh_too_large`. Raising the cap to admit them puts the mesh back at ~7.7-7.9 GB - the ceiling that killed the
     sweep in the first place.
- **Conclusion [measured]:** on this 8 GB card the contracted 120-12,000 Hz 1/6-octave band has no legal operating
  point. A mesh that resolves 12 kHz on the source patches needs >= ~8,600 dofs (7.9/8.19 GB peak, sweep dies); the
  smallest legal mesh (epw 4.05, 8,044 dofs) leaves the CMA population's larger neighbours over any cap that keeps
  VRAM safe. `cuda_fused`, the documented high-dof path, refuses multi-channel by design.
- **Delivered state is unchanged and valid:** the full MEH implementation (M1-M7, M10), the owner-approved pin bump,
  and the 500-10,000 Hz screens with their verified winners (T2 9.530 -> 11.894, T1 13.228 -> 14.512). The
  contracted-band work (opt-in `solve.freq_grid`, `worker_restart_every`, epw/cap experiments) is committed and the
  offline suite is green; only the run itself is not possible here.



- **`cuda_fused` is NOT an option for the MEH**: `HORNLAB_BEAT_FUSED_BM_CUDA supports exactly one channel`, so the
  fused path can never do a multi-tag solve at any dof count (the queue failed 3 candidates in 90 s; stopped).
- **The 12 kHz source-patch gate sets the mesh floor.** Measured with `run --dry-run`: epw 4.2 -> 8,625 dofs (7.9/8.19 GB
  peak, sweep dies); 3.8 -> entry_mid resolves only 11.28 kHz (refused); 4.0 -> driver 11.93 kHz (refused);
  **4.05 -> 8,044 dofs (T2) / 7,977 (T1), patches valid above 12 kHz, ~15 % less VRAM.** Both configs now dry-run OK
  with the full contracted grid: **41 frequencies, 120-12,000 Hz at 1/6 octave**.
- **Screen relaunched** on that configuration (log `runs/nights/meh_{t2,t1}_screen_120_12k.log`); the estimator says
  853 s / 803 s per candidate, i.e. a multi-hour run per brief - the measured first-candidate time goes in the evidence
  doc. Wall-resolution caveat stands and is now slightly worse: at epw 4.05 the rigid walls resolve to ~5.9 kHz, so
  the top of the band is driven-patch-accurate but wall-coarse.

## 2026-11-01 (05:10 EDT) - CONTRACTED 41-FREQUENCY BAND DOES NOT FIT THE 8 GB CARD (measured twice)

- **Run 1 (plain):** one 41-frequency sweep on the T2-A seed (8,625 dofs) ran 1,851 s and died with
  `CUDA error: unspecified launch failure (code 719)`; VRAM peaked **7,908 of 8,188 MiB** (2 s poller,
  880 samples). The screen queue then failed every candidate the same way, so it was stopped.
- **Run 2 (with the new opt-in worker recycling):** `solve.worker_restart_every: 8` restarts the host every
  8 solved frequencies. The sweep still died (`[worker_exit] ConnectionResetError`) at a **7,897 MiB** peak.
- **Interpretation [measured]:** the ceiling is **per-frequency transient**, not cumulative - the 12-frequency
  500-10,000 Hz screens also peak 7.87-7.92 GB and survive only because they make fewer draws, while 41 draws
  sit close enough to the edge that one crossing kills the sweep. Recycling cannot buy margin it does not have.
- **Committed anyway (green, useful on a larger card):** `worker_restart_every` (validated at load, forwarded
  into the solve `extra` only when set, fake-tested in `tests/test_solve_worker_restart.py`), set to 8 in both
  MEH search configs; full offline suite green.
- **Blocked decision for the owner:** (A) lower the dof cap for the contracted band (about 7,000 dofs gives
  ~35 % VRAM headroom but pushes the wall-resolution floor to ~4.7 kHz); (B) run the contracted band on a
  card with more VRAM; (C) keep the 500-10,000 Hz 12-point screen and record the band gap. The 500-10k
  screens and their verified winners stand; never rank across the two grids.
- **Not yet tried:** `solve.cuda_fused: true` (WP15 fused single-matrix assembler, documented as reaching
  ~20k quarter dofs on this 8 GB card). It is the one remaining way to fit 41 frequencies at 8,625 dofs
  without coarsening the mesh; it changes the solve hash and costs a small numeric difference (M5B parity
  0.020 / 0.039 dB).

## 2026-11-01 (03:45 EDT) - CONTRACTED 120 Hz-12 kHz BAND: OPT-IN solve.freq_grid, SCREEN RELAUNCHED

- **Owner decision:** screen over the contracted 120 Hz-12 kHz band (not the frozen 500-10,000 screen grid).
- **New opt-in `solve.freq_grid: {lo_hz, hi_hz, points_per_octave}`** (config.py). It is read from `cfg.raw`, not a
  new dataclass field, because the existing invariant test forbids a `None` in any `SolveSettings` field; the block
  is validated at load (missing key, lo >= hi, density outside 1..48, unknown key all refuse) and stripped before
  `_build`. Absent = the frozen `FREQ_GRIDS`, so no other config's solve hash moves. `mesh_spec` already takes
  `max(mode_freqs(...))`, so the mesh f_max follows to 12 kHz.
- **Both MEH search configs set it** (`120 -> 12000` at 6 points/octave = **41 frequencies**). `tests/test_config_freq_grid.py`
  (9 tests) pins: absent block = the frozen 12-point grid, present = 41 points at exactly 1/6 octave with f_max 12 kHz,
  the solve hash changes, and six bad blocks refuse. Full offline suite green after the change.
- **Two test repairs on the way** (both mine, both correct additions rather than loosened assertions):
  `tests/test_end_to_end_meh.py` maps a `*_search` config to its CAD-authored sibling's reference row.
- **Contracted-band screen relaunched** (`scratch/meh/run_meh_screen_120_12k.ps1`, logs
  `runs/nights/meh_{t2,t1}_screen_120_12k.log`, summary `meh_screen_120_12k_summary.txt`); the 500-10k run and its
  evidence are untouched. Dry-run at the new grid: 8,625 dofs (cap 9,000), 41 frequencies, tool estimate
  1,420 s/candidate; the measured per-candidate time is recorded when the first evaluations land.

## 2026-11-01 (01:45 EDT) - READINESS LINK 3 MEASURED: PASSIVE-MID NOTCH FOUND, PARTIAL AGAINST +-20 %

- The CD-only BEM sweep cannot show the port notch (an undriven L1 port is a rigid patch), so the check was redone
  properly: dense MULTI-TAG solve on the T2-A seed (10 frequencies 700-1800 Hz, 679.8 s), inner optimiser on that
  response (4.82 s, xo 673.7 Hz, order 2), mid channel muted to -300 dB, then `system_response`.
- **Result [measured]:** on axis, SPL 27.08 dB at 1000 Hz, 26.18 at 1100, 24.93 at 1200, then 34.12 at 1300 - a
  9.19 dB notch whose centre lies between 1200 and 1300 Hz. That is **+18.7 % to +28.6 %** of the 1-D 1010.8 Hz
  prediction, so the +-20 % gate is met only at the very bottom of that interval; the likely centre (~1250 Hz,
  +23.7 %) is outside. **PARTIAL, not a clean pass.** Placing it needs a 25 Hz sweep over 1150-1350 Hz.
- Logs: `runs/meh_m8/readiness3_coupled.log`, `readiness3_verdict.log`; arrays
  `runs/meh_m8/link3_muted_mid.npz`. Evidence doc section 9 row 3 updated.

## 2026-11-01 (01:20 EDT) - READINESS PROOF MEASURED ON THE STORED T2 WINNER: 4 PASS, 1 FAIL, 1 NOT PROVEN

- **Link 1 geometry PASS** (tags 1/2/10, 8,625 nodes, quarter planes; seed repairs slide 10 -> 32; walls resolve to
  ~6.1 kHz at the 12 kHz request). **Link 2 solve PASS** (channel fields + force reciprocity <= 3.2e-4).
- **Link 3 physics sanity NOT PROVEN.** The dense CD-only sweep rises to 1250 Hz then falls monotonically; no notch
  in the +-20 % window around the 1-D 1010.8 Hz. At L1 the entry port is a rigid patch unless the lumped network is
  coupled, so the check needs the network-coupled response with zero mid drive - not run.
- **Link 4 network < 2 s FAILS: 6.58 s.** `optimise_network` did 1,224 CMA evaluations (5.4 ms each) for the shipped
  T2 brief (2 mid drivers x 2 xo orders x 2 polarities x up to 160). Per-evaluation budget is met; the whole-call gate
  is missed 3.3x. Fix is a budget/combo decision, not a solver change. A cache-hit evaluate is 9.31 s wall.
- **Link 5 search moves PASS.** Two 40-evaluation screens; all six knobs moved (T2 spreads: cov_h 13.3 deg, cov_v
  23.9 deg, z_frac 0.329, across 0.388, port_along 9.9 mm, slide 25.4 mm); 38/40 T2 and 31/40 T1 OK, the rest genuine
  `invalid_geometry`; no crash.
- **Link 6 re-score for free PASS.** The stored winner `ed11d2cd3acc` re-scored with `faitalpro_6pr160` and
  `hp_hz 160` without a new solve: J 9.530280 -> 9.727026, `cached True`, both finite.
- **Blocked, recorded:** M8 step 3's quarter-vs-full comparison is impossible today - `tools/cad/meh.py` refuses a
  full model (`quadrants '1234'` -> GeometryInvalidError, quarter open shell only). M8 step 4 needs link 3's coupled
  response. **M9 is blocked:** Boundary Lab is not in this workspace (`forks/` has only beat-bem and the mesher).

## 2026-11-01 (00:45 EDT) - MEH SCREEN DONE: T2 J 9.53 -> 11.89 verified, T1 J 13.23 -> 14.51 verified

- **Two 40-evaluation CMA screens + verify top 2 each, all on the new pin on the owner's GPU** [measured]:
  T2 `runs/20261101T004552Z-screen-427d57` best `ed11d2cd3acc` screen J **9.530** (second `719aeb7a4ff0` 9.550),
  verify **11.894 / 11.804**; T1 `runs/20261101T015657Z-screen-fc1d24` best `704051ae928c` screen J **13.228**
  (second `9b6548cc2a6c` 13.556), verify **14.512 / 14.636**. Details in `docs/evidence/MEH_M8_2026-10-31.md` s8.
- **T2 beats T1 on its own brief's J** (9.53 vs 13.23 screen, 11.89 vs 14.51 verify). `lw_resid` dominates both
  (7.8 / 13.1 of J); `notch` is 0.0 in both, so the listening-window penalty is broad-band. Both winners push the
  driver to the top of the slide range (T2 `slide 35.2`, T1 36.1) and the ports low (`z_frac` 0.09 / 0.26).
- **One T2 verify design failed on a VRAM-ceiling worker reset** (7.9 GB of 8 GB) and the auto re-warm failed; after
  killing the stale BEAT host and confirming 1.36 GB idle, `verify --top 2` gave `2 designs, 0 failed`. The retry is
  recorded in the evidence doc; no tolerance changed.
- **`n_nan 12` in the winning record is not a metric failure:** `on_axis_db` is finite at all 12 frequencies and
  `n_nan_ripple 0`; the 12 NaNs are the synthesis's deliberately-NaN impedance array.
- **Two gaps opened by the screen (ISSUES):** (1) the solved grid was 12 frequencies 500-10,000 Hz, not the brief's
  120-12,000 Hz, so the objective scored `n_in_band 10` and never saw 120-500 Hz or 10-12 kHz; (2) `verify`'s own
  line says the verify mesh equals the screen mesh - only the frequency count and balloon size change, so it is a
  re-score, not a finer mesh.

## 2026-10-31 (20:45 EDT) - MEH SCREEN LAUNCHED (T2 then T1, 40 evals each, then verify top 2)

- `examples/typologies/meh_2026-10-30/meh_t1_search.yaml` added (the T1 seed through the `meh` generator; seed
  `slide_mm 14` = the repaired value for the HF108 body). Dry-run [measured]: 11,730 triangles, 6,009 dofs, 12
  frequencies 500-10,000 Hz, ~58 s/candidate, ~39 min for 40 evaluations.
- **Screen running detached** (`scratch/meh/run_meh_screen.ps1`, logs `runs/nights/meh_{t2,t1}_screen.log` +
  `meh_{t2,t1}_verify.log`, summary `runs/nights/meh_screen_summary.txt`). First T2 run
  `runs/20261101T004552Z-screen-427d57`; 4 records after ~4 min, VRAM 2.9 GB idle / 7.8 GB during assembly (8 GB
  card), one GPU job at a time.
- `tests/test_end_to_end_meh.py` now accepts BOTH seed shapes (a CAD-authored seed and a `generator: meh` seed) via
  `_seed_recipe`; the generator search config is checked against the same T2-A reference row. The old two tests
  assumed every MEH config carried `seed_params.cad`, which stopped being true when the searchable config landed.
- Full offline suite after the generator dispatch and both test fixes: exit 0.

## 2026-10-31 - MEH SEARCH UNBLOCKED: `generator: meh` DISPATCH + SEARCHABLE T2-A CONFIG

- **`design/generated.py`** gains `meh_params()` and its `materialize` dispatch (the gap M7 flagged). Recipe = the
  CAD tool's C9 defaults, then `generator.fixed`, then the knobs; `derived()` runs the layout check and the
  deterministic slide repair, a non-empty `reasons` list is `invalid_geometry`, and the mouth/depth are checked against
  the brief envelope. `tests/test_design_meh_generator.py` (5 tests) covers the knob set, the repaired seed, the three
  corner knob vectors, unknown keys and an illegal envelope.
- **`examples/typologies/meh_2026-10-30/meh_t2a_search.yaml`**: the T2-A seed authored through the generator, with
  `cov_h_deg cov_v_deg z_frac across_frac port_along_mm slide_mm` searchable (C9/T2 ranges) and everything else fixed.
  The seed carries `slide_mm 32` (the repaired value from M8 link 1), so it starts legal.
- **Cost measured by `run --dry-run` [measured]:** 11,776 triangles, 6,032 dofs (cap 9,000), mesh 5.8 s, 12
  frequencies 500-10,000 Hz with 73-angle cuts and a 512-point balloon; the tool's TOOLCHAIN estimate is 4.7 s per
  frequency = 62 s per candidate, i.e. a 40-evaluation search in ~41 min plus a 30 s cold start. The MEH screen is a
  ~41 min/brief GPU run, not a night.

## 2026-10-31 - MEH WAVE 2: M7 PIPELINE + BRIEFS + CAD SEED CONFIGS

- **`search/evaluate.py` (+283/-8)**: a brief `meh:` block takes the MEH path - mesh the `meh` CAD STEP ->
  `SolveSpec.extra.source_tags = [2, 10]` -> `meh.inner.optimise_network(..., score=objective_meh.inner_score)` ->
  `meh.synthesis.system_response` -> `metrics.compute` on the SYNTHESISED response -> objective v5 with a real
  `meh_ctx` (LW, polars, xo_hz, spl_max_db, spl_target_db, hp/boost). The record stores the BEM per-channel arrays +
  impedance matrix + `network_solution` + CAD layout. The non-MEH path is untouched (suite proves it).
- **Examples:** `examples/briefs/meh_2026-10-30/meh_home_90x60_t{2,1}.yaml`;
  `examples/typologies/meh_2026-10-30/meh_t{2a,2b,1}.yaml` (CAD recipes from `layout_out.md` final seeds).
- **CPU shape check [measured]:** t2a 6032 / 9000 dofs, t2b 5998 / 9000, t1 6009 / 9000; mouth 406 x 406 mm, depth
  380 mm, driver coupling round and matching the exit.
- **Tests:** fake mesh + fake multi-channel solver end-to-end (finite J, NetworkSolution, per-channel record arrays);
  re-scoring with another mid stem and `hp_hz` hits the solve cache (no new solve) and changes J; every new config and
  brief validates; the real CAD+BEM run is `slow`+`gpu`. Focused MEH 192 passed.
- **Deliberate adjustments:** brief envelopes use the C0 outer box (406.4 x 406.4 x 380) rather than the draft's 370;
  the T1 brief lists one CD (the M6 validator allows exactly one); T2-B uses the T2 brief's HF1440, so its port
  centroid is 39.9 mm vs the layout table's 41 mm (an HF108 T2-B needs its own brief).
- **Open gap (not M7's file):** `design/generated.py` has no `name: meh` materialize branch, so the seeds are
  CAD-native (`seed_params.cad`, `bounds: {}`) and not CMA-searchable until that ~20-line dispatch lands.

## 2026-10-31 - M8 EVIDENCE DOC WRITTEN; READINESS LINKS 1-2 PROVEN, 3-6 NOT RUN

- `docs/evidence/MEH_M8_2026-10-31.md` (INDEX updated) records, with quoted logs from `runs/meh_m8/`: the fork
  validation (CPU and CUDA), the three test-defect fixes, the pin bump, the single-tag parity table, readiness link 1
  (geometry) and link 2 (multi-tag solve), plus an explicit NOT-RUN list.
- **Link 1 caveats [measured]:** tags {1, 2, 10}, 8,625 nodes (cap 8,900), no non-manifold edges, quarter planes x0/y0
  - but the C9 T2-A seed is repaired from `slide_mm` 10 to 32 mm (`driver_hits_cd`, eleven 2 mm steps), and at the
  12 kHz request the driven patches resolve to 12.99-13.47 kHz while the rigid walls resolve only to ~6.1 kHz
  (`global_warn_source_hard`). The screen band's upper half therefore runs on underresolved walls at the dof cap.
- **Link 2 [measured]:** `channel_pressure (5, 2, 2, 37)`, force matrix symmetric to <= 3.2e-4 at 4 kHz, legacy
  fields = channel 0. An earlier 22-38 % reciprocity "failure" was MY error (quarter mesh solved with symmetry off);
  the app adapter derives the flag from the mesh and the check passes. The area-mean pressure matrix is correctly
  asymmetric by the area ratio (4.77).
- **Link 3 is PARTIAL only:** the CD-only sweep (500-4000 Hz, 8 points) shows the response still rising through the
  1-D port quarter-wave (1010.8 Hz) and peaking at 1250 Hz; the +-20 % notch check needs a denser 700-1600 Hz sweep.

## 2026-10-31 - M8 STEP 2b [owner-approved]: SOLVER PIN BUMPED TO 1efdc6f

- **Pin:** `pyproject.toml` and `TOOLCHAIN.md` now name `hornlab-beat-bem @ 1efdc6f934e16f288880b6d68e8dce8480b7a421`
  (branch `hornlab-search/meh-multisource`, pushed to `github.com/llevaachingada/hornlab-beat-bem` so the SHA is
  fetchable). Reinstalled with `pip install --force-reinstall --no-deps`; `SolveConfig` now has `impedance_matrix`
  and `source_tags` returns `(2, 10)` for a two-tag request.
- **Owner decision recorded:** the bump was approved after the M8 step-2 evidence (single-tag parity
  1.12e-5 / 5.91e-5 dB vs the 0.039 dB floor, request payload byte-identical, fork suites green on CPU and CUDA).
- **Gate:** full offline suite after the reinstall -> exit 0, no failures.

## 2026-10-31 - MEH WAVE 1 MERGE 7/7: M10 BASS BOX (7 woofer files, lumped model, build sheet)

- **`tools/bassbox.py`**: lumped sealed/vented box from a C8 cone file (C7 port branch: `L_eff`, `Q_port = 10`,
  `n_end = 2`, `Ql = 7`), electrical `Z_in`, SPL at 2.83 V and at the limit, cone excursion, port peak velocity, DSP
  (LR4 15 Hz + Linkwitz transform + five PEQ bands), `spl_max(f)` from Xmax / P_AES / 17 m/s; deterministic grids and
  a "smallest meeting the targets" search; CLI/JSON.
- **7 new `examples/drivers/*.yaml`** (`kind: cone`): bc_15tbx100, bc_18tbw100, bc_18sw115, faitalpro_15xl1400,
  faitalpro_18xl1800, eighteensound_18nlw9601, beyma_15lx60v2. Mmd/Cms derived only where the maker does not print
  them; the Beyma 8 mm vs +/-9 mm Xmax conflict and the 15TBX100 / 18NLW9601 Vas-vs-Fs inconsistencies are recorded
  in `notes` instead of being smoothed over.
- **Recommendation** (`BASSBOX_2026-10-31.md`): 1 x FaitalPRO 18XL1800, sealed 54.9 L net / 61.8 L gross
  (516 x 516 x 304 mm), LT 64.6/0.89 -> 26/0.71, five PEQ, +12.2 dB max boost; 116.4 dB at 40 Hz and
  123.1-126.6 dB at 63-120 Hz, flat 30-120 within 0.44 dB; stereo pair = +6 dB. Smallest that meets: 1 x 15XL1400
  sealed 38.0 L (113.3 dB @ 40, 119.3 dB @ 63).
- **Task-text correction:** "B4 (fs = fb, Qts 0.383, alpha 1) is -3 dB at fs" is wrong for the lossless vented box
  (alpha = 1 gives 0.0 dB at fs); the B4 constant is alpha = Vas/Vb = sqrt(2). The test asserts -3.01 dB at the
  sqrt(2) alignment (tolerance unchanged) and separately pins the literal alpha = 1 case at 0.0 dB, so the arithmetic
  is auditable. Task text should be amended.
- **Tests:** `tests/test_bassbox.py` 65 tests; full offline suite 2021 passed, 2 skipped, 20 deselected.

## 2026-10-31 - M8 STEPS 1-2 [measured]: FORK VALIDATED CPU+CUDA, SINGLE-TAG PARITY 1.1e-5 / 5.9e-5 dB

- **Step 1, fork validation (branch `hornlab-search/meh-multisource`, fork working tree
  `C:\Users\hunte\Hrns\forks\hornlab-beat-bem`):** the fork's Python suite 329 passed / 1 skipped. The full Julia
  suite (`julia --project=.../julia tests/runtests.jl`) exits 0; the CUDA-gated testsets report "broken" there
  because `julia/Project.toml` has no CUDA dependency (by design, the CUDA project is separate).
- **The M2 Julia testset had never been executed and did not pass.** Three defects, all in the test, fixed in
  commits `93ef848` + `1efdc6f`: the wire blocks are nested per channel and per plane (flatten before comparing),
  two comparisons broadcast `abs` over a `Vector`, and the hand-built request forced
  `quadrature_order=1, singular_order=1` - coarser than the app's payload - which destroyed reciprocity on the
  4-triangle fixture. Measured: 3.7e-4 reciprocity error at 100 Hz with the coarse orders and 2.2e-7 with the app's
  defaults through the real Python payload; 31.6 % in-test before the fix. Tolerances and the four properties are
  unchanged.
- **Step 1 result [measured]:** the same four properties (superposition, reciprocity, single-tag parity with the
  legacy impedance, reduced-vs-full symmetry) pass on the CPU backend (14.3 s) and on the CUDA backend (28.4 s,
  `CUDA.functional() = true`, RTX 4060 Laptop). Driver-level reciprocity 7/7 both arms.
- **Step 2, single-tag parity [measured]:** same meshes, same config, pin `760a1ec` vs fork `1efdc6f`, 5 frequencies
  200 Hz-4 kHz, 2 planes x 37 angles, CUDA. max |dSPL| = **1.12e-5 dB** (atlas finalist 92bb8946b380) and
  **5.91e-5 dB** (elite 0ae06187dc7d); max relative |dP| = 1.3e-6 / 6.9e-6. Both far inside the 0.039 dB noise floor.
  Not bitwise identical (separate GPU runs, reduction order); the request payload IS byte-identical (fork golden
  test). Pin bump awaits the owner's approval.
- **GPU hygiene:** worker hosts cleared between the pin and fork runs; baseline VRAM recorded (1.5 GB before, 0.43 GB
  after clearing); one solve at a time; `HORNLAB_BEAT_PERSISTENT_HOST=0` for the two one-off measurements.

## 2026-10-31 - MEH WAVE 1 MERGE 6/7: M4 PART 3 (INNER OPTIMISER)

- **`hornlab_search/meh/inner.py`**: `optimise_network(resp, layout_derived, brief, drivers, score=None)` enumerates
  the brief's CD x mid combinations (capped at 9), every `xo_orders` value and both mid polarities; CMA-ES
  (popsize 8, <= 160 evals, seed = brief / `search.seed` / 1234) over
  `[log xo_hz, mid_delay_ms, mid_gain_db, fill, v_rear_l]` inside the brief ranges. Default score = a local proxy of
  the C11 `lw_resid + notch + xo_lob + headroom`; `score=` receives M7's `objective_meh.inner_score` with the same
  `meh_ctx`; `inner.py` imports no objective code. Returns the C12 `NetworkSolution` (stems, xo, delay, polarity,
  gains, volumes, EQ and spl_max curves, inner_J, n_evals, seed), deterministic for a fixed seed, `ValueError` on
  hostile input.
- **Tests:** `tests/test_meh_inner_optimiser.py` (8): synthetic sources recover 0.3 ms delay (<= 0.02 ms), polarity
  -1, xo within 5 % (measured 908.58 Hz, +0.95 %, delay 0.3037 ms, 306 evals); determinism; JSON round trip;
  caller-score integration; enumeration; hostile inputs; one 60f x 2 planes x 37 angles x 2 channels candidate in
  0.0025 s (< 2 s budget). Suite: 1964 passed, 2 skipped, 20 deselected.
- **Known gap for M7:** `derived()` does not echo `dish_mm`/`spacer_mm`/`wall_t_mm`, so inner falls back to the
  reference dish placeholder `0.2 x cutout_mm`; passing them through makes `V_front` exact.

## 2026-10-31 - MEH WAVE 1 MERGE 5/7: M4 NETWORK LAYER (drivers, lumped network, DSP, limits, synthesis)

- **`hornlab_search/meh/drivers.py`**: `ConeDriver`, `CDSource`, `load_cone`, `load_cd`, `mmd_from_mms`; SI C7
  derivations; wrong-`kind` refusal; defaults for CD `fs_cd_hz`/`q_cd`/`di_ref_db` per C8.
- **`hornlab_search/meh/network.py`**: `from_bem` (exp(-iwt) per-acceleration -> exp(+iwt) per-volume-velocity),
  `entry_norton` (C7, incl. `Mmd_eff`, `L_eff`, `Q_port`, `n_end`), `cd_volume_velocity`, `couple` (the C6 Norton
  solve), `cone_excursion_peak_mm`, `port_velocity_peak`. Parity [measured, re-run by the integrator]:
  `entry_norton(n_end=2)` == `calc/meh_1d_sketch.py::Entry.norton` for MID4/MID65 at rtol 1e-12 over 60 frequencies;
  `couple` reproduces `calc/meh_zmatrix_check.py`'s direct solve at 1e-9 for one and two entry groups; `mmd_from_mms`
  gives 11.9 g (6FE100) and 3.8 g (4FE32); one-entry resistive-load energy balance at 1e-9.
- **`hornlab_search/meh/dsp.py`**: Linkwitz-Riley (orders 2/4/8 via squared Butterworth), Butterworth, delay,
  polarity, peaking biquad, `smooth_oct`, `system_eq` (1/3-octave power smoothing, boost clipped at `max_boost_db`,
  unlimited cut). LR4 low+high sum to unit magnitude within 1e-9.
- **`hornlab_search/meh/limits.py`**: `spl_max` with the five C11 limits (Xmax, cone P_AES, port air 17 m/s, amp
  volts, CD P_AES via sens + DI delta), first limit wins per frequency, binding limit reported.
- **`hornlab_search/meh/synthesis.py`**: `system_response` sums `H_net * U` per plane/angle (+ sphere), returns a
  `Response` `metrics/compute.py` consumes unchanged, `impedance` = nan.
- **Not yet in this layer:** `inner.py` (CMA inner optimiser) is a separate follow-up branch; M7 must not be blocked
  on it for the config/brief work, but the end-to-end path needs it.

## 2026-10-31 - MEH WAVE 1 MERGE 4/7: M6 OBJECTIVE v5 ("meh") + THE BRIEF `meh:` BLOCK

- **`objective/scalar_meh.py`**: `objective_meh(metrics, resp, ok, target, weights, params, meh_ctx)` = the v4 pattern
  terms on the SYNTHESISED response (re-using the v4 functions, no duplicated maths) plus `lw_resid`, `notch`,
  `xo_lob`, `headroom` per C11; tolerances/weights from the brief block, defaults = the C11 table; graded penalty,
  never nan/inf. `inner_score(meh_ctx, weights)` is the cheap same-terms call M4's inner optimiser uses via M7.
- **`objective/versions.py`**: 5 registered in `SUPPORTED_OBJECTIVE_VERSIONS`.
- **`config.py`**: additive `meh:` block validation (exact keys/types, the C10 ranges, unknown keys refuse, driver
  stems that do not exist yet warn instead of failing while M1 is landing). v1-v4 briefs and hashes unchanged.
- **Coupled touch points in `search/evaluate.py`** (M7's file, unavoidable for the version/scorer gate):
  `_OBJECTIVE_SCORERS` gains 5 and `MehParams` is the v5 params class. The MEH evaluation BRANCH (building
  `meh_ctx`, synthesis, inner optimiser, recording) is still M7's; until it lands, `_score_v5` raises when no
  `meh_ctx` is available rather than silently scoring a half-empty context.
- **Tests:** `tests/test_objective_meh_terms.py`, `tests/test_objective_meh_scalar.py`, `tests/test_config_meh.py`;
  `tests/test_dataset_record.py` updated only where version 5 becomes a supported value.

## 2026-10-31 - MEH WAVE 1 MERGE 3/7: M1 DRIVER FILES (8 files, C8)

- **`examples/drivers/`**: 8 new files (5 `cone`: bc_6ndl38, faitalpro_6pr160, eighteensound_6nmb420, bc_4ndf34,
  faitalpro_4fe32; 3 `compression_meh`: faitalpro_hf1440, faitalpro_hf108, bc_dh450) + `tests/test_meh_driver_files.py`
  (29 tests). Every number transcribed from the repo's own datasheet extraction
  (`docs/research/typologies/mini_meh_2026-10-29/appendix_A_web_survey_raw.md` s8, rows read from the maker PDFs and
  labelled `V`); `mmd_g`/`cms_mm_per_n` are marked `derived` with the formula in `notes`; unpublished mechanicals
  (`frame_od_mm`, `motor_od_mm`, `dish_mm`, CD `duct_mm`) are omitted and named, never guessed.
- **Deviation recorded:** M1's task file says to open each datasheet PDF. This lane had no web access, so it
  transcribed the repo's verified s8 table instead. The CD duct depths stay at the C9 [inferred] 40/25/25 mm until a
  drawing read or the M8 measurement.
- **Tests:** `tests/test_meh_driver_files.py` 29/29 (re-run by the integrator).

## 2026-10-31 - MEH WAVE 1 MERGE 2/7: M3 SEVERAL-SOURCE-TAG SOLVE ADAPTER

- **`types.py::Response`** gains the five optional C5 fields (`channel_tags`, `channel_pressure`,
  `channel_sphere_pressure`, `impedance_matrix`, `tag_areas_m2`), default `None`; no existing field changed.
- **`solve/beat.py`**: `SolveSpec.extra["source_tags"]` -> `velocity_sources = {t: 1.0}` + `impedance_matrix=True`;
  absent key keeps today's config byte-for-byte (golden solve-hash test); an installed `SolveConfig` without
  `impedance_matrix` raises ConfigError naming M8's pin bump; per-tag mesh pre-flight from `mesh_meta.json`;
  `channel_*` copied into `Response` with legacy fields = channel 0. `solve/bempp.py` refuses `source_tags`.
- **`dataset/record.py`** stores the three MEH complex arrays plus `channel_tags`/`tag_areas_m2`/`network_solution`
  (schema stays 1; old records load unchanged). `solve/cache.py` npz round trip extended because its module-level
  field assertion would otherwise fail at import - a required coupled change, no test fixture edited.
- **Tests:** `tests/test_solve_meh_fake.py` (golden single-tag config + hash, multi-tag payload, old-pin refusal,
  tag pre-flight, 2-channel -> Response shapes, bempp refusal, cache round trip) and
  `tests/test_dataset_meh_record.py`.
- **Carried (ISSUES):** multi-tag solves raise ConfigError until M8 bumps the solver pin to M2's fork branch.

## 2026-10-31 - MEH WAVE 1 MERGE 1/7: M5 MEH L1 CAD TOOL + MULTI-LABEL STEP ROUTE

- **New `tools/cad/meh.py` (822 lines)**: ports `calc/meh_layout.py` (`geometry`, `_wall_frame`, `check`,
  `from_fractions`, `_narrowest`) with identical numbers; the deterministic slide repair is logged in
  `derived()["repairs"]`; T2-A and T1 `derived()` match the reference for z_c, z_m, mouth W x H, port z, path to
  diaphragm and f_h within 0.2 mm / 1 Hz [agent-reported, tests re-run below].
- **L1 solid**: outer box minus horn air (planar-quad frustum + mouth roundover) minus the CD bore; full port
  outlines imprinted as flush coplanar patches, then quarter-cut at x = 0 / y = 0 and exported as an OPEN shell (the
  symmetry planes are not BEM faces). Quarter inventory: T2 driver 1 + entry_mid 1; T1 driver 1 + entry_mid 2.
- **`mesh/step_build.py`**: `meh` registry entry, `entry_mid` -> tag 10 / `entry_aux` -> 11, quarter import with
  `quadrants="1"`, fine sizing near every driven face, frequency hard-fail on every driven face, per-tag area +
  centroid in `mesh_meta.json`. `multicell`/`plughorn` paths unchanged.
- **Known gaps (carried to ISSUES):** seed renders not produced (`pyvista` absent from the venv, no installs
  permitted); `cd_duct_mm = 0` refused (no disc face without a bore); unknown cone (cutout, depth) pairs refused
  until M1 lands.

## 2026-10-30 (18:10 EDT) - MEH INTEGRATION BRANCH PULLED; BASELINE GREEN AFTER TWO PRE-EXISTING REDS

- **Local work preserved first.** `feat/hardened-plan-2026-10-29` had uncommitted night-result work (CONTINUITY
  16:04Z entry, INDEX rows, `HANDOFF_NEXT_RUNS_2026-10-30.md`, `SWARM_PLAN_2026-10-30.md`,
  `examples/typologies/atlas_2026-10-30/atlas__osse_ext_throat.yaml`) -> committed as `97f1490` before switching.
- **Hand-off section 0 done.** `meh/integration` created from `origin/ccr-4978c80b-tvvcgv`; `origin/main` merge was
  already up to date (no CONTINUITY/ISSUES entries lost).
- **Baseline was RED on two tests unrelated to MEH** (both pre-existing at the hand-off commit):
  1. `test_gui_sandbox_page.py::test_3d_hot_swap_never_scenes_per_frame` pinned the pre-1bdd1b7 one-liner
     `if (curGeo) curGeo.dispose();`; the ridge-overlay commit folded the ridge-cache eviction into that statement.
     The assertion now pins the current, stricter contract (evict `ridgeCache` **and** dispose) - not a loosening.
  2. `test_param_catalog.py::test_committed_json_is_byte_identical_to_a_fresh_build` failed on CRLF vs LF: this
     checkout had `core.autocrlf=true` while the generator writes LF. Fixed by setting `core.autocrlf=false` locally
     and re-checking-out the tree (index content unchanged, 0 tracked files with CRLF), not by touching the test.
- **Baseline after the fixes [measured]:** `.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not
  crosscheck" -q` -> exit 0, 100 % (no failures). Research scripts reproduce: `meh_1d_sketch.py` conical-horn check
  4.45e-16; `meh_zmatrix_check.py` 4.44e-16 (one group) / 5.86e-16 (two groups); `meh_layout.py` prints the
  layout_out.md seed table (T2-A/HF1440 and T1 OK, the three known-bad seeds unchanged).
- **GPU is busy:** night queue `n2_gapfill_2026-10-30` (started 16:56, 7 jobs, no cutoff) is running
  `search --resume runs/20261030T111108Z-screen-377bbe` with a live Julia host. Per CLAUDE.md no MEH GPU job starts
  until that queue finishes - wave 1 (CPU/cloud code) proceeds meanwhile.

## 2026-10-30 (late) - MEH CHIEF-IMPLEMENTER HAND-OFF

- `docs/meh/CHIEF_IMPLEMENTER_HANDOFF.md`: pull steps for `C:\Users\hunte\Hrns\hornlab-search`, wave order with gates,
  a six-link readiness proof that the MEH is optimisable end to end, and the follow-on optimisation studies.

## 2026-10-30 - MEH UN-DEFERRED BY OWNER; DESIGN FIXED; IMPLEMENTATION HAND-OFF IN `docs/meh/` (zero GPU, no package code)

- **Owner decisions:** MEH top + separate bass box (30-120 Hz flat); top fits a 16 in square face (406 mm), corner-hung,
  studio-monitor depth (380 mm assumed); home hi-fi / DJ practice / booth, critical listening, level of a powered 12 in
  PA; DSP + FIR on every channel; not for sale. Owner gave the orchestrator architecture, labels, typologies, solves and
  scoring, with the rest handed to cheaper sub-agents.
- **Design fixed:** T2 `meh2_6x2` primary (1.4 in CD + 2 x 6.5 in on top/bottom walls, 90x60, XO 650-1100 Hz, HP 120 Hz);
  T1 `meh2_4x4` secondary (1 in CD + 4 x 4 in, XO 1-1.5 kHz, HP 160 Hz). L1 solve = flush port patches as driven tags
  (2 CD, 10 mids), one BEM solve gives per-channel transfers + impedance matrix, drivers/xo/delay/fill/rear volume
  optimised per geometry by an inner optimiser. Objective v5 = v4 pattern terms on the summed system + `lw_resid`,
  `notch`, `xo_lob`, `headroom`; `flat` off (FIR).
- **New research [measured]:** `calc/meh_layout.py` layout feasibility in the 16 in box (horn ~150 mm, mouth 330 x 191;
  reparameterised knob box 56-93 % feasible vs 12-29 % naive; seeds T2-A/T2-B/T1); `calc/meh_bassbox_sizing.py`
  (15 in / 18 in long-throw for 30-120 Hz).
- **Hand-off:** `docs/meh/README.md` (waves, models, dispatch prompt, merge order) + `00_MEH_CONTRACTS.md` + M1-M10 task
  files. Wave 1 (parallel, cloud): M1 drivers, M2 solver fork, M3 adapter, M4 network, M5 CAD, M6 objective, M10 bass box;
  wave 2: M7 pipeline; wave 3 (owner GPU box): M8 validation + screen, M9 Boundary Lab.
- `CLAUDE.md` gained one ownership pointer to contracts C13; `NEXT_DEV_PRIORITIES.md` P13.

## 2026-10-29 (20:15 EDT) - MINI MEH RESEARCH: WEB LANE FOLDED IN, CLAIMS SPOT-CHECKED (zero GPU, no code)

- **Web lane (Sonnet) returned:** raw survey kept verbatim as `docs/research/typologies/mini_meh_2026-10-29/appendix_A_web_survey_raw.md`
  (sources, 8 targets, design-rules digest, product-size and driver tables, conflicts). Dossier s0-s13 rewritten around it.
- **Orchestrator spot-checks (all match):** JW DH350 MEH page, Solana page, US 8,284,976 claims 1/4/5/6 + notch/port passages,
  Boundary Lab releases (v0.5.0 still latest) and its `Multi_region_SAWMOD` example, MEH Studio repo. US 6,411,718 claim text
  not re-readable here (503/403); kept at the lane's label.
- **Key external facts:** JW DH350 MEH = the owner's size class (2 x 6.5-inch + 1-inch CD + 2 PR, 470 x 260 x 200 mm, ~15 L net,
  60 Hz-16 kHz +-2 dB, 106 dB, taps lambda/4 at the 1.0-1.2 kHz XO); Solana 4 x 6.5-inch + 1-inch, 109/120 dB, 90 x 90 to 700 Hz,
  no dimensions; no Danley box in this size class (SH75 62 L, SM-60F 113 L); Boundary Lab solves several voltage-driven drivers +
  FEM chambers + port interfaces in one coupled system (Mmd only, no passive radiators); no AES/JASA paper on MEH found.
- **New 1-D result [measured]:** the mid's own reflection notch depends only on the horn; in a cone it sits 1.4-1.8x above
  c/4d, but a 35 mm compression-driver duct pulls it to ~1.6-1.9 kHz for close entries (the practitioners' ~1.5 kHz ceiling):
  the CD's internal depth must be modelled (`calc/notch_vs_path.md`).
- **Corrections (dossier s8; owner-file items appended to `NOTES_FOR_SENIOR.md`):** frozen plan's "MEH geometry path exists"
  (tag names only); `DRIVER_MODEL.md` "Boundary Lab issue #78" is timini/horn-simulation issue #78 (rule unchanged); BL
  "symmetry Off" applies to plugin assemblies, coupled projects run with symmetry xy; draft's "6.5-inch needs a 1.4-inch CD".
- **Still open:** owner decisions in dossier s13 (bass route, size number, use/coverage, mid complement, DSP, J terms).

## 2026-10-29 (18:45 EDT) - MINI MULTIPLE-ENTRY HORN: RESEARCH PASS, DRAFT PUSHED (zero GPU, no code)

- **Owner request:** internal + external research toward a mini multiple-entry horn (Synergy/Unity class, smaller than
  JW Sound's Solana): one compression driver + 2 x 6.5-inch or 4 x 4-inch mids on ports, very small box, strong EDM bass.
  Research and plan seeds only; nothing wired. MEH was owner-deferred 2026-10-24 (G17); reopened for research only.
- **Dossier (draft):** `docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` + folder `mini_meh_2026-10-29/`
  (`calc/` = CPU research scripts and outputs, not imported anywhere). Sections 7-8 (external findings, corrections)
  wait on the Sonnet web lane (Danley primaries, JW Sound Solana, current Boundary Lab, small DIY MEHs, driver T/S).
- **Findings so far [measured / verified]:** mids cannot do EDM bass (4 x 4-inch ~93 dB, 2 x 6.5-inch ~97-101 dB at 50 Hz,
  1 m half space; 115 dB needs ~840 cm^3 Vd) -> 2-way mini top + sub, or compact 3-way with woofers; a 300 mm mouth holds
  90 deg only to ~940 Hz; 1-D MEH sketch: the CD notch sits ~1.15-1.4 x the port corner and deepens as entries move toward
  the throat (-18 dB at 20 mm, -2 dB at 70 mm), best sum near the quarter-wave limit; per-source solve + impedance
  matrix + lumped drivers equals the direct solve to 6e-16 (the plan's core decomposition).
- **Solver/mesher inventory (fork source read 2026-10-29):** the Julia engine already solves several channels on one
  factorization and returns per-channel pressures; the Python package refuses more than one tag (`config.py:462`);
  no mutual impedance matrix yet. The mesher has MEH tag names 8-12 but no MEH builder (corrects the frozen plan's
  "geometry path is already there").
- **Owner questions:** separate sub or bass in the box; a size number; use case and coverage; 4 x 4-inch vs 2 x 6.5-inch;
  DSP per channel; which new J terms (dossier s13).

## 2026-10-28 (15:05 EDT) - PUSHED: SOLVED-STYLE RENDER SHEETS + THE DAY'S WINNER (J 1.11)

- **Renders (4 PNG, `docs/renders/2026-10-28/`):** `typologies_solved_2026-10-28.png` (best design of each typology solved today, one row each),
  `hybrids_solved_2026-10-28.png` (the 6 CD-throat hybrids, best first), `petal_os_solved_2026-10-28.png` (6 refined petal/lobe horns),
  `osse_flare_curl_card.png` (design card: two views + full-width H/V dispersion). Folder README and the INDEX line updated with them.
  Made with `tools/render/render_views.py` + `tools/render/compose.py` (the `hornlab-render` skill), from each run's solved `best.json`.
- **Day-queue results (b3a 90x90 / 400 Hz, screen, quarter):** `hy__osse_flare_curl` **J 1.113** (best on this brief so far; prior 1.307
  `b3a__rosse_morph` 10-27) > `hy__sf_x4` 3.31 > `petal__x4_mild` 3.62 > `hy__sf_star6` 3.74 > `hy__os_ruffle` 3.83 > `po__star6_mild` 4.48 >
  `hy__os_curl` 4.59 > `po__rosette12` 4.64 > `po__union_soft` 5.18 > `po__union_soft_flute` 5.53 > `po__clover` 5.71 > Salmon chanterelle
  10.73-13.12 > `qf__union` 11.17 > `hy__ns_72x44` 11.89 > `hy__ns_60x40_deep` 20.46 > `po__ns_60x40_deep_soft` 21.58.
- **Signal:** non-square mouths (60x40, 72x44) are 3 of the 4 worst results of the day on the 90x90 brief; the four-petal Salmon
  quatrefoils land in the chanterelle band (9-12), not the hybrid band. The CD-throat `osse_rollback` lane is the only one reaching 1.x.
- **Caveat (owner):** the winner is pattern-clean but weakly loaded - output gap at f0 11.5 dB, loaded (Re z >= 0.5) from 1.76 kHz - and
  `objective.load` has weight 0 in the brief, so J cannot see loading. Decide before verify: accept EQ, or re-score the day's top designs
  with a load-weighted brief.
- **Live state at push time:** H2 queue on `qf__fold_xout` (after `qf__union` 11.17); 17:30 cutoff; screen-only, no design verified yet;
  the full offline suite still has not been re-run since the `osse_rollback` / `fc_fold` / `fc_union` changes (no pytest solver tests
  during a live GPU night).
- **Also carried up in this push:** `e0ea198` (skills + tools, committed by the afternoon session, previously unpushed on `main`).

## 2026-10-28 (20:50 EDT) - PUSHED: 8 COMMITS TO origin/main

- `cb09147`..this commit: top-2-per-typology renders + day-queue status; compression-driver library; cone mid horn research,
  corrections and the CAD-based `cone_plughorn` typology (tool, GUI preview, configs, tests, morph knobs); driver handoff.
- Not pushed by design: `third_party/`, `reference/` (gitignored). Nothing GPU ran for this work.

## 2026-10-28 (21:00 EDT) - CONE PLUGHORN: HORN-THEORY MORPH KNOBS, GUI, HANDOFF (zero GPU)

- `tools/cad/plughorn.py` gained a morph layer: 14 `m_*` knobs (compression ratio, axe-head base, wall angles, mouth corner,
  roll-out, axe head relative to the horn, plate margin, bowl-from-cone) that derive the raw CAD dimensions; seeds reproduce
  the Evo 7SH / Evo 2SH CAD within 0.3-0.5 mm; a 12-inch variant regrows the throat at the same compression ratio.
  `derived()` adds first-order theory diagnostics. Rationale table: CONE_MIDHORN_AXEHEAD_2026-10-28.md section 5e.
- 3 morph configs (`cone_plughorn__morph_*`), source_motion axial; 27-29 of 40 random knob vectors legal; mesh 5.8k-10.7k dofs.
- Evo 2SH corrected to Funktion-One's spec: 8-inch mid, 50 x 25 (brief vertical 25).
- GUI sandbox previews plughorn configs (all tool keys are knobs; out-of-envelope shapes are drawn and flagged).
- Handoff for the driver work: `docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md` (F1 publishes no T/S; targets 112 dB/1 W
  Evo 7SH 10-inch, 111 dB/1 W Evo 2SH 8-inch).
- Tried and removed: an axe-head "cone fill" knob (OCC booleans left the chamber as a detached shell); handed to the driver work.
- Tests: plughorn + step_build + catalog 68 pass (CPU). Not solved on the GPU.

## 2026-10-28 (20:10 EDT) - CONE MID HORN + AXE HEAD TYPOLOGY FROM FUNKTION-ONE CAD (zero GPU)

- Owner supplied Funktion-One's 3D models (Evo 7SH narrow 40x20, Evo 2SH wide 50) as DWG. LibreDWG could not decode the
  3D solid (AC1027 data-storage SAB); the ODA File Converter (signed, extracted locally to `third_party/oda`, gitignored)
  rewrote them as DXF R2000 and `tools/cad/sat_dump.py` read every vertex/edge/face. CAD files stay local
  (`reference/`, gitignored, Funktion-One copyright).
- Both horns share one topology: throat octagon in front of the cone, flat top/side walls, ruled corner panels, rolled
  mouth, a planar convex axe head whose base sits in the throat (2.4-2.7 mm gap at the throat diagonals = the compression
  ring, Sd/min channel 5.0 Evo 7SH, 7.5 Evo 2SH). `tools/cad/plughorn.py` builds it with the CAD numbers as defaults
  (overlays coincide: `docs/renders/2026-10-28/cone_plughorn/`). Outside simplified per owner: plate + convex shell +
  moulded driver bowl (gross 6.1 / 2.8 L).
- Wired: `step_build` CAD-tool registry, `generator: {name: plughorn}`, GUI sandbox preview (sections + 3D CAD solid,
  slow ~5-7 s), shape_check. Configs `examples/typologies/cone_plughorn_2026-10-28/` (2), briefs
  `examples/briefs/cone_midhorn_2026-10-28/` (2). Mesh: 9,421 / 5,976 dofs (cap 12k), one driver face each.
- Tests: `tests/test_mesh_plughorn.py` + `test_mesh_step_build.py` 29 pass (CPU). Not solved on the GPU yet.
- Open: cone size not in the CAD (10-inch r 105 assumed on 7SH; r 90 on 2SH to fit its bowl); 2.4 mm throat gap is a
  BEM thin-gap risk; Evo 2SH vertical coverage target 30 is a placeholder; parameter set still = raw CAD dimensions.

## 2026-10-28 (19:10 EDT) - CONE MID HORN / AXE-HEAD RESEARCH + PLAN (zero GPU)

- Owner: model large cones in a mid horn with a central plug (Funktion-One "axe heads"). Dossier
  `docs/research/typologies/CONE_MIDHORN_AXEHEAD_2026-10-28.md`: the three Andrews patents (US6557664 axe-head 1992,
  US6650760 F1 loaded low-mid 75-750 Hz 1999, US4836327 Turbosound coax 1986), practitioner rules, and a plan:
  WP-M0 1-D calculator (Hornresp-style), M1 cone driver files, M2 build123d CAD generator via the existing STEP route,
  M3 brief + coherence term (owner approval), M4 first GPU (owner go), M5 print + measure.
- The coax HF-through-the-plug variant stays out (multi-entry class, owner-deferred 2026-10-24) unless reopened.

## 2026-10-28 (18:10 EDT) - COMPRESSION DRIVER LIBRARY (research, zero GPU)

- Owner wants horn loading to ~600 Hz (can't afford more DCX464). Sonnet research agent wrote
  `docs/research/COMPRESSION_DRIVER_LIBRARY_2026-10-28.md`: 17 drivers in three price brackets, by exit and use.
- Low-crossover candidates: Beyma CP800/Ti (2", 500 Hz rated), BMS 4592-MID (2", 300 Hz), RCF ND850-2.0, Eminence PSD3006 (fs 511 Hz).
- **Gap:** no driver has Sd + Mmd published in the data found, so the absolute driver model (`driver/compression.py`) cannot run on any
  of them yet; driver files were not added to `examples/drivers/`. Needs the full datasheet PDFs or owner measurements.
- Pending owner decisions: loading term in the score; 90x60 vs 90x90 for the 600 Hz low-crossover brief; which driver.

## 2026-10-28 (17:45 EDT) - DAY QUEUE STATUS; TOP-2-PER-TYPOLOGY SHEETS

- **Queue:** H2 hybrids 15/15 done (15:24); C round-throat 6/6 done (16:44); D verify running (10 of 12 at 17:45); E extend will not
  start (17:30 cutoff). Controller and runner unchanged.
- **Round-throat A/B (b3a / b3bt):** locking the R-OSSE throat round did NOT cost score - b3a 1.034 (new best on that brief; was 1.307
  non-round), b3bt 3.22 (was 3.75). `rt__b1t` / `rt__b2t` rosse_morph returned J 1000 on all 13 evals (infeasible - not yet diagnosed).
- **Verify (higher fidelity, balloon DI):** screen J holds within ~0.1-0.3 for R-OSSE b3a (1.31 -> 1.41), ATH 14in (2.05 -> 2.33),
  biradial (1.96 -> 2.25); it slips ~0.9-2 for ATH core 2in (1.60 -> 2.54), core_law (1.70 -> 2.60), ridge law8 (2.81 -> 3.87),
  salmon_x_signed b3bt (4.02 -> 6.04), lecleach_iwata b3bt (5.45 -> 7.56). Screen under-reads the narrow/ridged shapes.
- **H2 results (b3a):** hy__sf_x4 3.31, po__x4_mild 3.62, hy__sf_star6 3.74, po__star6_mild 4.48, rosette12 4.64; quatrefoil Salmon
  9.3-11.2; ns_72x44 11.9 and the deep 60x40 pair 20-22 (poor). Best hybrid still hy__osse_flare_curl 1.113.
- **Renders:** `docs/renders/2026-10-28/top2_per_typology/` (11 typologies).

## 2026-10-28 (afternoon) - REUSABLE CLAUDE SKILLS + THE TOOLS BEHIND THEM (zero GPU)

- **Why:** the last two days spent many turns re-deriving the same recipes (detached launch, keep-awake, live-night rules, mesh checks,
  render layouts). Each is now one tool plus one short skill, so the next session runs it instead of rebuilding it.
- **Tools:** `tools/shape_check.py` (CPU mesh-only check: dofs/cap, mouth W x H, depth, envelope, round coupling; safe during a night),
  `tools/render/render_views.py` + `tools/render/compose.py` (views; `stack` = the owner's card), `tools/night_queue/queue.ps1` +
  `launch_detached.ps1` (multi-night queue, keep-awake, cutoff, wait-on-runner), `tools/night_status.py` (status + best per brief).
- **Skills** in `.claude/skills/` (Claude Code loads only this folder): `hornlab-night-queue`, `hornlab-shape-check`, `hornlab-render`, plus
  copies of the three `.opencode` skills (edit the originals, re-copy).
- **Verified:** shape_check on trumpet / clover / rosse_morph_round; render + compose on ruffled (run dir) and clover (mesh); night_status on
  today's nights. **Not live-tested:** `queue.ps1` / `launch_detached.ps1` (parse-checked only - starting a runner would kill the live
  H2 night's Julia host); the running day queue is still the earlier hand-written controller.
- **Live state:** H2 night 7 of 15 done; best so far `po__x4_mild` 3.62 (b3a); `po__ns_60x40_deep_soft` 21.6 (deep 60x40 brief).

## 2026-10-28 (11:36 EDT) - PUSHED: 9 COMMITS TO origin/unified-typologies (shape work + night queue)

- **Pushed:** `d27ac6f`..`78fbd19` (9 commits, fast-forward, 0 behind upstream). Contents: chanterelle cells; round-throat A/B configs;
  night runner takes over a dead GPU-lock holder (test added); `osse_rollback` hybrid rows kind (constant-directivity OS throat, flute
  ripple, curled lip, superformula morph, four-petal angle law `a_fold` / `a_union` / `union_blend_deg`); Salmon `fc_fold` / `fc_union`;
  quatrefoil, hybrid, petal_os and deep-60x40 brief configs; render sheets in `docs/renders/2026-10-28/`.
- **Not pushed / left alone:** `hornlab_search/gui/static/sandbox.js` and `view3d.js` have modifications made by someone else; they were
  deliberately kept out of every commit.
- **Live state at push time:** day queue controller v3 waiting on the hybrid night (`v4_day_H_hybrids_2026-10-28`, 3 of 4 done, best so
  far `hy__os_ruffle` 3.83). Next night `v4_day_H2_hybrids_2026-10-28` (15 jobs; refined petal/lobe horns first). 17:30 start cutoff.
- **Test status:** grid, rows, osse_rollback and catalog suites pass (CPU only); the full offline suite was NOT re-run after today's
  grid changes because a GPU night is live (rule: no pytest solver tests during a night).

## 2026-10-28 (11:45 EDT) - REFINED PETAL/LOBE HORNS ON THE CD THROAT; FIRST HYBRID RESULT 3.83

- **First result of the CD-throat hybrid idea:** `hybrid__os_ruffle` best J **3.83** on the b3a 90x90 brief (40 solves) vs 10.73 for the
  best Salmon chanterelle (ruffled) on the same brief.
- `osse_rollback` gained the four-petal options on its angle law: `a_fold` 4 (a_h on both axes, a_v on the diagonals), `a_union` 1
  (union with the 90 deg copy) and `union_blend_deg` (a smooth |x| so the diagonal join is a rounded hump, not a crease). 3 new tests
  (osse_rollback tests now 19).
- **Refined set** (owner: "acoustically more sense") `examples/typologies/petal_os_2026-10-28_v4/`: clover, union_soft, union_soft_flute,
  x4_mild, star6_mild, rosette12 (the six-star joined with its 30 deg copy as a soft 12-lobe edge), ns_60x40_deep_soft. Common rules: CD
  throat instead of the Salmon march, K-law-ish mouths (577-705 mm on the 740 envelope), moderate petal contrast (walls 35-45 deg), soft
  joins, shallow late flutes or none, curled lip. 4.0-6.9k dofs, all round at the exit.
- H2 night rewritten before it started: the 7 refined horns first (30 each), then sf/60x40 (40), then the Salmon quatrefoils (40). With
  the 17:30 cutoff the verify night will likely not start today.
- Render sheets saved in `docs/renders/2026-10-28/` (indexed).

## 2026-10-28 (11:30 EDT) - SUPERFORMULA + 60x40 HYBRIDS, FOUR-PETAL "ROTATE-AND-JOIN" SALMON; QUEUE v3

- `osse_rollback` gained a superformula mouth morph (Gielis, n2 = n3; fades in from `sf_start`, coupling plane stays round). Configs in
  `examples/typologies/chanterelle_hybrid_2026-10-28_v4/`: `sf_x4` (4-lobe X, 688 mm, 6,751 dofs), `sf_star6`, `ns_72x44` (OS walls
  36/22 deg, tall K-law mouth 363 x 509, 300 mm) and `ns_60x40_deep` (OS k 5 uses the depth: 368 x 529 mouth, 420 mm) on a new brief copy
  `b2t_pa_60x40_1200_tall_deep_v4.yaml` (only max_depth 300 -> 600; owner dropped the depth cap).
- Salmon rows gained `fc_fold` (4 = the two-fold fc law in 2 phi: four petals on the axes) and `fc_union` (1 = the union of the shape and its
  90 deg copy: each azimuth takes the law at max(psi, 90 - psi), so the diagonal joins are the original 45 deg rows - an X of creases).
  Defaults keep every existing design's geometry and hash. Configs `examples/typologies/quatrefoil_2026-10-28_v4/` seeded from the
  ripple X-flute8 winner: fold_xin (clover), fold_xout (petals + humped joins), union, union_noflute; 2.2-4.5k dofs, round at 36 mm.
- Tests: osse_rollback 12 (superformula added), salmon fold/union 3 new; grid + catalog suites pass.
- Queue v3 (`runs/nights/day_queue_2026-10-28_v3.ps1`): after the running hybrid night -> H2 (sf/60x40 x4 + quatrefoil x4, 40 each) ->
  round-throat A/B -> verify -> extend; no night after 17:30.

## 2026-10-28 (10:50 EDT) - NEW HYBRID ROW KIND `osse_rollback` (CD throat + flutes + curled lip); QUEUE RE-ORDERED

- **Why (owner):** the Salmon chanterelles beam (ruffled ~120 deg below 1.5 kHz -> ~55 deg at 8 kHz; across 670 stored Salmon designs even
  the most even goes ~111 -> 70 -> 43 deg): the roll-back march is a loading profile. Owner asked for a hybrid with a constant-
  directivity throat from another horn, paired with the rollback + fluted rim, flutes into the throat but not to the driver.
- **Built:** rows type `osse_rollback` in `design/generators/grid.py` - per-azimuth OS/OSSE wall from Magnus's `profile_points`
  (a(phi) = a_h cos^2 + a_v sin^2), the existing even-lobe flute ripple opening at `ripple_start`, and the existing tangent-continuous
  curled lip with optional `wrap_cos_amp` (wrap follows the flutes = ruffled margin). Additive only: existing grid generator / mesh /
  config tests pass; 9 new tests (`tests/test_design_generators_grid_osse_rollback.py`); param catalog + variants tests pass.
  LABELED HYPOTHESIS-SHAPE EXPERIMENT (no published name).
- **Configs** `examples/typologies/chanterelle_hybrid_2026-10-28_v4/` (b3a 90x90 brief, quarter model): os_curl, os_ruffle,
  os_deepflute, osse_flare_curl. Mesh-only: 5,018-5,884 dofs, mouths 598-697 mm, depth 213-246 mm, all couple round at 36 mm.
- **Queue v2** (`runs/nights/day_queue_2026-10-28_v2.ps1`, WMI, keep-awake, same log, no night after 17:30): old controller stopped
  (its running chanterelle runner kept going), new one waits for it, then hybrids (4 x 40) -> round-throat A/B -> verify -> extend.

## 2026-10-28 (09:12 EDT) - OVERNIGHT STALLED BY SLEEP; DAY QUEUE TO ~7 PM LAUNCHED (owner); THROAT RULE SOFTENED

- **Overnight:** Windows went to sleep at 22:21 (Kernel-Power 42) and woke 09:00. Ripple re-run: job 7 resumed and finished (100,
  best 11.19), `salmon_flute10_s125` 9.82, `salmon_x_flute6_s125` stalled at 66/100 by the sleep and was killed on its timeout at wake;
  `salmon_x_flute8_s125` then waited on the dead job's lock (removed by hand) and is solving. The chanterelle waiter gave up (6 h
  wall-clock deadline crossed during sleep) - nothing started.
- **Runner fix:** `tools/run_campaign_night.py` now takes over a GPU lock whose holder is gone (a timed-out job left one behind and the
  next job would have waited out lock_wait_s and failed); test added (`tests/test_tools_night_runner.py`, 11 pass).
- **Day queue** (`runs/nights/day_queue_2026-10-28.ps1`, WMI-detached, keeps Windows awake via SetThreadExecutionState, log
  `runs/nights/day_queue_2026-10-28.log`; no night starts after 17:30): after the ripple re-run -> A finish `salmon_x_flute6_s125`
  (+34) -> chanterelles (3 seeds + 40-solve searches around ruffled, golden, trumpet) -> C round-coupling A/B of six OSSE/R-OSSE
  winners (`examples/typologies/round_throat_2026-10-28_v4/`: aspect_ratio locked 1, R-OSSE exponent locked 2 because exponent alone
  made the coupling plane a rounded square; seeded from each winner; budget 80) -> D verify grid on the top 5 of 12 leading cells
  (screen-vs-verify rank check) -> E +100 on `ridge__ath_core_law8` and `b3bt__salmon_x_signed`.
- **Throat rule softened (owner challenge, 2026-10-28):** ATH-style settings can give non-round throats (our mesher follows ATH's
  rules and applies aspect/exponent down to the throat); the research's "ATH always couples round" rested on summaries. Certain: the
  8 flagged winners were simulated with a source shaped like their throat, not a round driver exit. Unmeasured: how much a non-round
  coupling matters. Round coupling = the default for prints; the round-throat cells run as an A/B, not a replacement. Owed: a
  one-design A/B with a round source + a built-in transition section (needs a new geometry option).

## 2026-10-27 (22:00 EDT) - CHANTERELLE CELLS QUEUED BEHIND THE RIPPLE RE-RUN (owner "yes, queue them")

- **Owner art direction:** horns that look like chanterelle mushrooms (round funnel, curled-back wavy lip, "false gill" ridges
  down to the throat). Renders (scratch, local): 3 stored Salmon-flute designs picked by look (scores 15-18, not winners) and 3 NEW
  shapes. New configs `examples/typologies/chanterelle_2026-10-27_v4/`: `golden` (6 flutes 26 mm, lip 160 deg), `ruffled`
  (10 flutes 14 mm, lip 145 deg), `trumpet` (8 flutes 20 mm, lip 200 deg; scaled 520 -> 570 Hz because the first mesh was
  12,346 dofs > the 12,000 cap) as seed-only cells, plus `ruffled_search` (40 solves, boxed to keep the look: round within
  ~11 %, lip 135-165 deg, 10 flutes 10-20 mm). LABELED EXPERIMENT on the existing Salmon rows + ripple construction (no new
  typology, no published name). Brief b3a 90x90 PA (the envelope they were drawn in; its 400 Hz f0 is below what a 1.4" exit
  can load - read loading with the loudness readout). Mesh-only checks: 10,672 / 6,573 / 10,316 dofs; all couple round to 36 mm.
- **Queue:** `runs/nights/v4_chanterelle_2026-10-27.yaml` starts via a detached waiter (`runs/nights/v4_chanterelle_waiter.ps1`,
  launched by WMI, log `runs/nights/v4_chanterelle_waiter.log`) only after the ripple re-run runner (pid 32496, matched by command
  line) exits; it clears the GPU lock only if its holder is dead and gives up after 6 h. Estimated ~30-40 min of solves.
- **Safety note:** do not use `hornlab-search run --dry-run` while a night runs - `_cmd_run` calls `worker.install_handlers()`
  before the dry-run branch; mesh-only checks here called `mesh.build.build_mesh` directly.

## 2026-10-27 (21:27 EDT) - RIPPLE RE-RUN NIGHT LAUNCHED (owner "re-run them"), DETACHED VIA WMI

- `runs/nights/v4_ripple_rerun_2026-10-27.yaml`: job 7 RESUMED in its run dir for the last 13 new solves (budget 13), then
  `salmon_flute10_s125`, `salmon_x_flute6_s125`, `salmon_x_flute8_s125` fresh at budget 100 each (~1.5-2 h). Hygiene: no Julia, stale
  `runs/.gpu.lock` (pid 35548 dead) removed by hand because the runner waits for the file to disappear and `gpu-clean` does not clear a
  dead holder's lock; VRAM baseline 1,263 MiB. **Launched through `Win32_Process.Create` (WMI)**, so the runner's parent is
  `WmiPrvSE`, not a Claude session: closing the app no longer kills a night. Confirmed solving (row 88 written, Julia host up). Logs:
  `runs/nights/v4_ripple_rerun_runner_{stdout,stderr}.log`, `runs/nights/v4_ripple_rerun_2026-10-27/`. Launcher kept in scratch only.
- Renders (scratch, local): `scratch/ripple_gallery/` (the 4 finished ripple/ridge winners) and `scratch/best5_gallery/` (the 5
  lowest-J cell winners), each with the loading line and the driver coupling-plane check.

## 2026-10-27 (late evening) - SENIOR PASS P12 (ZERO GPU): SCORING/SEARCH/REALITY PLAN, LOUDNESS + DRIVER MODEL, THROAT RULE; RIPPLE NIGHT STOPPED AT 6/10

- **Ripple/ridge night STOPPED after 6 of 10 jobs** (all 6 exit 0: crease re-run 4.57, b2t R-OSSE re-run 5.58, salmon_flute8 9.85,
  salmon_x_flute8 9.41, `ridge__ath_core_law8` **2.81**, salmon_flute6_s125 10.08). Job 7 (`salmon_flute8_s125`, run dir
  `runs/20261027T235118Z-screen-094cd0`) started 19:51 EDT and was killed at ~20:08 EDT after **87 of 100** evaluations (64 valid,
  best J 11.40; the runner buffers the job log, so the log showed only the argv line). The runner wrote no exit line and its process was
  gone; a failed job would have been logged and the runner would have moved on, so it was killed from outside (most likely the
  session that launched it closing); not a code fault. Jobs 8-10 never started. **Re-run launched 21:27 EDT - see the entry above.**
- **This entry** touched no search-path module, brief, config or GPU (`cli.py` untouched). **Next steps are now P0 at the top of
  `docs/NEXT_DEV_PRIORITIES.md`.**
- **Plan doc:** `docs/research/SENIOR_PASS_SCORING_SEARCH_REALITY_2026-10-27.md` (from ~5,100 stored rows, 4,094 stored responses).
  Key numbers: PA winners are 8-14 dB short of a loaded throat at 500-830 Hz; the b3a 90x90/400 Hz winner (J 1.31) loads
  (Re z >= 0.5) only from ~1.6 kHz, and its three leading cells contain **no** design within 3 dB of loading - a cone rule
  (x0 = r0/tan a) reproduces the BEM Re z within ~0.02, so 1.4" OS-type throats cannot load there; P12a offline re-score
  (exact reproduction, max |err| 0.0) changes the cell winner in 10-13 of 27 cells, mostly to near neighbours; 1-4 knobs
  carry ~80 % of J in 9-17-knob cells; refusals are 23 % of every budget; the presence band has 3 screen points and a coarse
  grid missed the narrowest beam there by up to 12 deg on 15 stored pairs; the 2 m arc is centred on the throat (near-field
  for big mouths); woofer spacing puts the first vertical null inside coverage for crease core law, ath core, native
  Le Cleac'h and the fluted cells; horn DI exceeds a woofer's at the crossover by 2-6 dB. Six owner decisions + gates (s7).
- **Built (report-only):** `hornlab_search/metrics/loudness.py` (output gap at f0, loaded-from frequency, on-axis level per
  1 m/s), `hornlab_search/driver/compression.py` (lumped compression driver over the BEM throat impedance: SPL at 2.83 V and
  1 W, excursion, efficiency, impedance, max SPL), `hornlab_search/mesh/throat_check.py`, `tools/loudness_report.py`,
  `examples/drivers/_template.yaml` (no real driver yet - owner to supply), loudness chart + line in the per-run HTML report,
  GUI config list skips `examples/drivers/`. Stored-data check: throat power = balloon power within 0.0-0.4 dB, 500 Hz-8 kHz,
  four horns. Tests: `tests/test_driver_compression.py`, `tests/test_metrics_loudness.py`, `tests/test_mesh_throat_check.py`
  (24 pass, offline). After the night stopped, the full offline suite (CI selection) ran: **1,736 passed**, one pre-existing
  failure deselected - `test_param_catalog::test_committed_json_is_byte_identical_to_a_fresh_build`: fa9a5a6 raised
  `ROWS_MAX_RIPPLE_AMP_MM` 6 -> 50 without regenerating the param catalog, so the GUI showed a 6 mm ripple cap; regenerated
  in the follow-up commit (`tools/gen_param_catalog.py --write`). Docs:
  `docs/DRIVER_MODEL.md`; INDEX and CODE_MAP updated.
- **Throat finding + owner rule:** OSSE / R-OSSE `aspect_ratio` stretches the coupling plane (24x36, 26x36, 41x36, 50x36 mm on
  36 mm briefs; 8 of 30 winners). Owner rule: no separate adapter; only the coupling plane must be round at the driver exit;
  morph/ridges allowed right after. Outside research (`docs/research/THROAT_COUPLING_2026-10-27.md`, Sonnet subagent, reviewed:
  one cross-mode figure corrected) confirms the round coupling plane; the transition rate has no published number.
- **Scratch (local only):** `scratch/p12_senior_pass/` (scripts + `p12a_rows.csv`).

## 2026-10-27 (evening) - RESUME NIGHT DONE; RIPPLE/RIDGE NIGHT RUNNING; SIM-VS-REAL RESEARCH (P12); PUSHED TO MAIN

- **Resume night finished (27/27 exit 0, +~100 solves per cell).** Biggest gains (best J before -> after): `b3a__rosse_morph` 3.17 -> **1.31**
  (lowest J anywhere), twinray 4.44 -> 3.00, `b2w__osse_baseline` 5.49 -> 3.78, gcurve 5.22 -> 3.86, `b1w__osse_baseline` 7.01 -> 5.47,
  `native__ath_core` 1.91 -> 1.60, `b3bt__rosse_morph` 4.42 -> 3.75, `b3a__ath_core_14in` 5.76 -> 2.05 (132 rows). Flat (near floor):
  `crease__core_law` 1.70, rollback/asym_odd. Scoring cross-check: J == sum(w x term) + penalty for all 3,676 first-night valid rows.
  `crease__osse_b1w` (startup failure) and `b2t__rosse_morph` (its Julia host was killed by a test run - **never run pytest solver tests during a
  night**) are re-run in the next night.
- **Ripple/ridge night LAUNCHED 17:23 EDT** (`runs/nights/v4_ripple_ridge_2026-10-27.yaml`, 10 jobs, owner "go ahead"): 2 re-runs, then flute
  cells (`examples/typologies/ripple_ridge_2026-10-27_v4/`): Salmon rows + 8 deep flutes (Solana-style, from near the throat, depth 8-45 mm;
  `ROWS_MAX_RIPPLE_AMP_MM` 6 -> 50 in `design/generators/grid.py`, test updated), X-pucker + flutes, ATH CORE law with 8 lobes
  (`ridge__ath_core_law8`, scored on the `_diag_v4` briefs: diag weight 1.0), and 5 s125 variants (6/8/10 flutes, X 6/8). Throat longer/deeper
  (T 0.4), roll-over 110-125 deg. These use the b1t brief (850 Hz, 360x520 mm), so they are NOT sized for 500-600 Hz loading; a b3bt-brief twin set was
  proposed, not built.
- **P12 - do the sims behave like a built horn? (owner concern, top priority, gate on further big nights).** Findings: loading weighted only on
  b3bt/b3bw/native_lecleach; the J 1.31 winner has Re z_throat 0.04-0.12 below 830 Hz; ideal source, no driver model; cov err^2/100 with tolerances
  2/4.5 is generous and masked below f0 for class A. Outside research pass: `docs/research/SIM_VS_REAL_HORN_2026-10-27.md` and a new section 17 in
  `docs/plan/12_RESEARCH_BASIS.md`. Conclusion: ideal-source BEM is a sound RELATIVE tool for pattern shape above cutoff, not for level/loading/
  distortion. Ranked actions: (1) free P12a re-score of cached responses with load ON + stricter cov, (2) lumped compression-driver model over the BEM
  throat impedance, (3) validate against one published measured horn, (4) load on for PA/low-reach, (5) report-only 200-300 Hz solve, (6) print and
  measure a J-winner and a loading-aware winner. Nothing in scoring has changed yet.
- **Other additions today:** `tools/export_campaign_tables.py` + `docs/data/campaign_v4_2026-10-27/` (collaborator tables, refreshed),
  `docs/HANDOFF_COLLABORATOR_2026-10-27.md`, `_diag_v4` brief copies, `tools/hf_sync.py` (tabled P11). Renders and story images are scratch only
  (`scratch/v4_gallery`, `scratch/seed_gallery`, `scratch/story`; pyvista in `scratch/vizenv`).

## 2026-10-27 (midday) - v4 NIGHTS DONE/RUNNING; RESUME NIGHT; DATA TABLES FOR THE COLLABORATOR; MERGE TO MAIN

- **First v4 night (100 evals/cell, 27 cells, ~5.1 h): finished, 27/27 exit 0.** Budgets were revised from the earlier 9.5 h
  plan to 100 per cell (60 for two slow cells, 30 for `b3a__ath_core_14in`). Best J lowest: `native__ath_core` 1.60,
  `crease__core_law` 1.70, `b3a__biradial_keele` 1.98. `b1w__biradial_keele` / `b3bw__biradial_keele` ran only 10 evals
  (90 % refused): their scores rest on one or two valid designs.
- **Resume night** `runs/nights/v4_resume_2026-10-27.yaml` (27 jobs, 100 MORE non-cached solves each, same run dirs via
  `hornlab-search search --resume`). `tools/run_campaign_night.py` gained a `resume:` job field. Confirmed: budget counts only
  new solves (control 112 -> 212 rows, gcurve 101 -> 201). Gains: gcurve 5.22 -> 3.86, b1w osse_baseline 7.01 -> 5.47,
  control 5.91 -> 5.32; crease__core_law and rollback/asym_odd flat (near floor). **`crease__osse_b1w` failed at startup
  (Julia host exit 3221225786, runner logged exit 0) and still needs a re-run** after the night ends.
- **Data for the collaborator (no CUDA needed):** `tools/export_campaign_tables.py` -> `docs/data/campaign_v4_2026-10-27/`
  (`cells_summary.csv`, `evals.csv` ~4.5 MB with J, normalised terms, scalar metrics, per-eval design parameters;
  `best_designs.json`; README with column meanings). Re-run it after the resume night for the final numbers. The solve cache
  (~22 GB incl. runs) is NOT in git; the Hugging Face route (`tools/hf_sync.py`, needs the owner's `hf auth login`) is
  tabled as P11 in `docs/NEXT_DEV_PRIORITIES.md`.
- **Images:** scratch only (`scratch/v4_gallery/`, pyvista in `scratch/vizenv`); not committed.
## 2026-10-27 (overnight) - v4 T0 GATE PASSED; OVERNIGHT v4 SCREEN CAMPAIGN RUNNING

- **v4 twins of the whole campaign:** `tools/make_v4_campaign.py` writes `examples/briefs/campaign_2026-10-26_v4/`
  (14 briefs) and `examples/typologies/campaign_2026-10-26_v4/` (27 configs); `--check` reports drift. Only `name` and
  `brief_file` differ from the v3 cells. Classes: A waveguide (b1*, b2*, ath core, twinray), B loading (b3b*, native
  lecleach; diag 0.15 and no presence weighting on the native lecleach), C low-reach PA (b3a*: one-sided below f0).
- **T0 gate (27 cells, budget 1, screen): 27/27 valid, 0 failed.** Most jobs took ~20 s because the solve cache is keyed
  on geometry + solver settings, not the objective: seeds were re-scored under v4 from the smoke night's stored
  responses (so the v4 scorer, including the diagonal term from the real stored balloons, ran on 27 real designs;
  only one row needed a fresh solve). Night folder `runs/nights/v4_t0_2026-10-27/`.
- **Dominance check (the point of v4):** median top-term share of seed J is **53 %** (v3: four of eight scored cells at
  82-92 % one term); 4 of 27 cells exceed 60 %, max 75 % (`cov`). `load` is 7-12 % on the loading briefs (v3: 2 %).
  Cov is still the largest term on most cells, as it should be for a coverage brief.
- **Diagonal check (offline, stored best designs, 512-pt balloons):** the crease seed's 45/135 beam is 4-12 deg
  NARROWER than the H/V mean across 1.7-4.8 kHz, the control's is 5-10 deg WIDER above 3.7 kHz, `crease__core_law` is
  narrower around 1.4-2.3 kHz. So the crease does not widen the diagonal here; the `diag` term (round reference,
  narrow side 2x) will penalise the crease seed in the presence band. One seed per cell; a verify-resolution
  (1024-pt) run on finalists would firm it up. Script: `scratch/v4_impl/diag_check.py`.
- **Overnight run:** `runs/nights/v4_overnight_2026-10-27.yaml`, 27 jobs, 1,770 evaluations, ~9.5 h estimated
  (budgets from measured s/eval: 100 fast / 60 medium / 40 slow / 30 for `b3a__ath_core_14in`; heavy B3a cells LAST).
  Launched detached 00:59 EDT with the observer (`tools/observe_run.py`, 13 h cap). Outputs:
  `runs/nights/v4_overnight_2026-10-27/{SUMMARY.md,summary.jsonl,observe.ndjson}`; logs
  `runs/nights/v4_overnight_runner_stdout.log`. A first launch from the tool shell was stopped within seconds (a
  foreground-style timeout could have killed a 9 h run); its orphan job/Julia worker were killed and the stale
  `.gpu.lock` removed; one empty stub run dir `runs/20261027T045803Z-screen-5845fa` is left from it.
- **Not run:** ladder rungs, verify/final tiers, second seeds, the low-frequency report-only grid, epw 5-vs-6.

## 2026-10-27 (late) - OBJECTIVE v4 IMPLEMENTED (owner decisions: Option A, round diagonal, DI std alongside dislope, presence band via freq_weights)

- **What shipped (uncommitted, no GPU):** `objective/scalar_v4.py`, `metrics/diagonal.py`, dispatch + version 4,
  config parsing of the `objective:` block (`tolerances` required, no defaults; `cov_narrow_ratio`,
  `cov_below_f0: mask|one_sided`, `diag_reference: round`). Stored `terms` are the NORMALISED values (raw =
  term x tolerance), so `w * terms[k]` sums to `total` and the GUI/report need no change. New weights `distd`,
  `diag` default 0, so a v4 brief with only tolerances is "v3, normalised".
- **Penalty ordering enforced at load:** config refuses a brief whose all-unmeasurable valid J exceeds half the
  refusal penalty (the Option B failure mode). The three new briefs score 61 / 94 / 111.
- **Briefs (new files, v3 briefs untouched):** `examples/briefs/campaign_2026-10-26/b1w_hifi_90x60_850_wide_v4.yaml`
  (class A: narrow side 2x, presence band x2), `b3bw_pa_90x60_600_load_wide_v4.yaml` (class B: symmetric, loose
  dislope, load live), `b3a_pa_90x90_400_square_v4.yaml` (class C: one-sided below f0, narrow 2x, presence x2).
  Class numbers are proposals [E]; Option A numbers are the review's.
- **Tests:** `tests/test_objective_v4.py` (24 cases: validation, neutral v4 == v3, tolerance scaling, asymmetry,
  one-sided, DI std, diagonal on a synthetic round beam, penalty ordering, config + dispatch end to end).
  Offline suite exit 0, no failures. Two assertions updated because their subject changed (see NOTES_FOR_SENIOR).
- **Diagonal term cost:** ~50-130 ms per evaluation (interpolates the stored balloon), negligible vs 7+ s solves.
  Rank effect still unverified: `crease__osse_b1w` has no stored balloon record; the queued T3 diagonal check
  (plan item 4) is the GPU step that settles it.
- **Not done, owner-gated:** the box-widening table (review appendix A), the low-frequency report-only grid
  extension (verify 200 Hz / final 125 Hz), the epw 5-vs-6 test, and re-running the 27 T0 cells under v4.

## 2026-10-27 (v4 scoring review, investigation only - NO code/config/GPU) - NORMALISATION CHANGES THE WINNER

- **Docs:** `docs/research/V4_SCORING_REVIEW_2026-10-27.md` (findings), `docs/evidence/OBJECTIVE_V4_TOLERANCES.md`
  (two tolerance options for the owner), both indexed; the orchestrator's `V4_TOLERANCE_RESEARCH_2026-10-27.md`
  indexed too. Read-only analysis scripts in `scratch/v4_review/`. No v1-v3 code/brief/config touched, no GPU.
- **Offline recompute verified exact:** rebuilding Response/MetricSet/Target from stored arrays reproduces the
  stored objective to max |err| 2.8e-14 over all 50 ok v3 records. Only 54 v3 records exist (50 ok: lecleach 43,
  crease 5, gcurve 2) - the smoke night's were lost - but the search.ndjson trajectories survived (100+ cells,
  term-level) and carry the rank-correlation work.
- **Finding 1 (load-bearing):** v4 normalisation is not cosmetic. Global Spearman(v3, v4-physical) ~0.93, but the
  argmin design changes in ~40% of cells, top-5 overlap is routinely 0-3/5, and loading briefs collapse
  (`native__lecleach_rollback` Spearman 0.10 n=74, -0.01 on the 43 records, top-5 0/5). The tolerance choice is
  real and must be made per class, not defaulted.
- **Findings 2-5:** six-term normalisation is necessary but not sufficient - add DI-std (independent of dislope,
  ρ -0.37..+0.90) and a presence-band (2.5-5.5 kHz = 3/12 screen points) asymmetric-narrow cov penalty; the
  balloon already drives 9-77% of J via DI but never reads diagonal SHAPE; data-median tolerances break penalty
  ordering (worst valid J 1572 > 1000 on lecleach) while physical tolerances hold (79-117); the 33% refusal rate
  is `invalid_geometry` (89/124, a geometry-law limit), NOT a box-width problem.
- **Hypotheses tested (tolerance-research note):** asymmetric cov (survives, class-gated), one-sided cov below f0
  (survives for low-reach PA), DI-std vs dislope (survives, not redundant), presence band (survives, 3/12 points,
  reshuffles loading cells). Class-specific tolerance blocks supported.
- **Owner decisions:** the tolerance set (Option A physical recommended); diagonal reference (round recommended);
  DI-std replace-or-supplement dislope; asymmetric-cov ratio+classes; presence-band grid vs freq_weights; the
  box-widening table (appendix, owner-gated). **Could NOT verify:** the diagonal term's rank effect - the one
  asymmetric-diagonal cell (`crease__osse_b1w`) has no stored balloon; needs the queued T3 balloons (GPU).

## 2026-10-27 (gcurve follow-up) - THE GUIDING CURVE NOW SITS AT THE MOUTH (`dist 1.0`), T0 VALID

- **Supersedes the width-130 workaround below.** That seed was valid (367 x 292, J 6.289) but it
  changed the intended mouth scale to pull the envelope back. The real defect was the curve
  **station**: at `gcurve_dist 0.5` the 335 mm outline sat halfway down the horn and the flare kept
  growing to the mouth (783 x 581 mm). At **`gcurve_dist 1.0` the outline is the mouth**, so width
  335 is the mouth width again. Box change: `gcurve_dist` hi 0.9 -> 1.0; the width box returns to
  the campaign 0.3-1.1x335 = 100.5-368.5 mm (39-143 was the workaround's box). `families.KeySpec`
  has no lo/hi clamp on `gcurve_dist`, and the mesher's own formula accepts `0 < dist <= 1.0` as a
  fraction of L, so 1.0 is allowed. The cell header now explains the station fix and both attempts.
- **Measured geometry:** dry-run bbox 0.1676 x 0.1457 m after the quarter mirror -> full mouth
  **335.2 x 291.5 mm**, depth 146 mm, inside the 380 x 300 brief envelope.
- **T0, budget 1, screen:** `seed J = 9.85253`, **1,855 dofs**, 3,543 triangles, 1 new / 0 cached,
  7.1 s/candidate, objective v3. The v3 dataset record landed (`dataset/shard-0030.jsonl`).
- **Trade-off, stated plainly:** the dist-1.0 seed (9.853) is structurally correct and beats the
  control seed 15.045, but it is **worse** than the width-130 workaround (6.289) and the crease seed
  (8.407). One seed each; J sees only H and V, and this cell still pins `aspect_ratio 1.0` while the
  control runs 1.15, so it is not a clean A/B. The guiding curve still needs a real T1/diagonal
  check before any ranking claim.
- **Verification:** `.venv\Scripts\python.exe .venv\Scripts\hornlab-search.exe search --config
  examples\typologies\campaign_2026-10-26\gcurve__osse_b1w.yaml --budget 1 --mode screen` (one
  geometry dry-run + one T0, ~6 s of GPU). No code change.

## 2026-10-27 (dataset v3 follow-up) - OBJECTIVE VERSIONS NOW HAVE ONE SOURCE OF TRUTH

- **Follow-up to the entry below.** The first fix widened the validator with a literal `(1, 2, 3)`;
  that would need editing again for v4 (term normalisation), which is exactly the drift the task
  called out. The allowed set now lives in
  `hornlab_search/objective/versions.py::SUPPORTED_OBJECTIVE_VERSIONS`.
  `search/evaluate.py::_score` dispatches through a table whose keys are checked against that tuple
  at import (RuntimeError on drift), and `dataset/record.py::validate_record` rejects anything
  outside it.
- **Adding v4** is now one edit to the tuple plus its scorer in the same commit; the import check
  refuses a half-landed version. The bool rejection and "missing field means v1" are unchanged.
- **Tests:** a v3 record writes/validates/reads back; `99` (plus `0`, `4`, `"2"`, `True`) still
  reject; a new test pins the dispatch-table/tuple equality. Offline suite:
  `pytest -m "not slow and not gpu and not crosscheck"` -> **1689 passed, 20 deselected, 1 warning**
  (317.66 s, exit 0).
- **Live confirmation:** a budget-1 v3 T0 wrote `dataset/shard-0030.jsonl` with
  `objective_version: 3, ok: true` and did not log `dataset record ... NOT written`.
- **Reconstruction of the smoke night's lost records: NO from the night folder.** It holds only the
  41 job logs and `summary.jsonl` (job-level `best_J`, `evals_ndjson`, `run_dir`) - no
  per-evaluation rows. Full `search.ndjson` rows and `metrics.json`/`response.npz` do survive in the
  referenced `runs/<timestamp>-screen-*` dirs, so a bespoke backfill is possible from those, but it
  would need a replay tool (not written) and is not a read of
  `runs/nights/smoke_2026-10-27/`.

## 2026-10-27 (after the report) - `gcurve__osse_b1w` RESEEDED AND VALID (and the best b1w seed of the night)

- **Two mistakes, not one.** The cell's `gcurve_width 335` was copied from b1w's *mouth* width, but
  (a) the curve's width is not the mouth width and (b) **the brief envelope is checked on the FULL
  mirrored mouth, not the quarter bbox** - so a quarter bbox of 336 mm is a 673 mm mouth. The first
  reseed attempt (280 mm) still failed for exactly that reason, having been calibrated off the
  quarter bbox.
- **Measured calibration** (`run --mode screen --dry-run` for the geometry, then a budget-1 T0 for
  the envelope verdict): width 150 -> full mouth 408 x 316; 192 -> 494 x 376; 280 -> 673 x 503;
  140 -> 388 x 294 (8 mm over); **130 -> 367 x 292 = valid**. The relationship is strongly
  non-linear near the top: a candidate at width 142 already measures 433 x 420, so the usable band
  is roughly **110-138 mm** and the top half of the 39-143 box mostly refuses - tighten after an
  LHS audit (the widening table's 0.6-1.15x rule does not hold for this knob).
- **Result at the corrected seed:** `seed J = 6.289`, 2,047 dofs, 3,925 triangles, mesh 1.8 s,
  solve 9.5 s. That is **the best b1w-based seed of the night** - better than `crease__osse_b1w`'s
  8.407 and the control's 15.045 (and better than either of their best results, 8.407 / 8.064). Terms
  are spread (cov 3.38, rip 0.14, di 0.73, dislope 1.93, flat 3.18), not single-term dominated.
  **One seed, so a lead not a verdict** - the guiding curve now deserves a real T1.
- **Artifacts:** the cell's header carries the calibration table and both mistakes; the report's
  section 3/7 record the fix; a `_probe_gcurve.yaml` used for the sweep was deleted.
- No code change; two T0s plus five geometry-only dry-runs, ~3 minutes of GPU.

## 2026-10-27 (after the smoke report) - OBJECTIVE-v3 DATASET RECORDS FIXED

- **The defect:** `dataset/record.py` accepted only `objective_version` 1 or 2, but v3 is a
  dispatched objective (`search/evaluate.py` routes to it since the 2026-10-26 amendment). Every
  objective-v3 evaluation therefore wrote **no dataset record** - the `ValueError` is caught and only
  logged, so it was invisible until the smoke night logged it in all 27 T0 jobs. `search.ndjson`,
  `best.json` and reports were unaffected; the phase-2 surrogate data was.
- **The fix:** the validator now accepts `(1, 2, 3)`, with a comment naming when v3 shipped. The
  docstring follows.
- **Tests:** `tests/test_dataset_record.py` - the stale reject-list dropped `3` (it now rejects
  `0, 4, "2", True`), a meta-level `v3` validation case was added, and an **end-to-end** case runs a
  real `evaluate(..., objective_version=3)` through the store and asserts the record lands with
  `objective_version 3`. That end-to-end case is the one that would have caught this. **45 passed /
  0 failed / 0 skipped**.
- Not a loosened test: the assertion's subject changed because the objective gained a v3. The
  rejects for `0`, `4`, `"2"` and `True` are intact.
- No GPU work.

## 2026-10-27 (smoke night, report) - CAMPAIGN SMOKE: 41 jobs, the crease class works, four scoring findings

- **Run:** `runs\nights\smoke_2026-10-27.yaml` (27 T0 + 9 mini-T1 + 5 ladder), 376 evaluations,
  **252 valid / 124 refused (33 %)** - `invalid_geometry` 89, `invalid_envelope` 26,
  `mesh_too_large` 9. **157.8 valid evaluations per hour.** Report:
  `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md`.
- **T0 gate: 26/27 pass.** `gcurve__osse_b1w` is **invalid**: `outside the brief envelope (width
  783 > 380.0 mm, height 581 > 300.0 mm)` - the guiding curve's width setting is not the mouth
  width, and at `gcurve_width 335` on an L 140 body the mouth doubles. Its T1 spent 11 of 30
  evaluations and found 0 valid designs (flat J = 1000 -> CMA flat-fitness stop). Reseed owed.
- **The crease class works.** `crease__core_law` at budget 60: **J 19.022 -> 2.784 (-85 %)**, 39/61
  valid, and it **kept the diagonal crease**: a(0/45/90) = 25.0/33.8/23.4 -> 18.0/34.7/31.5 deg,
  crease strength +9.56 -> **+9.97 deg**, while moving 13 of its 17 searched knobs (`a_deg` 5 -> 15.1,
  `az_sf_n1` 12 -> 21.9, `az_sf_n2` 15 -> 10.3, `morph_corner` 16.5 -> 5.9). The A/B at equal budget
  60 is `crease__osse_b1w` 8.407 -> 8.407 (**no gain**, the seed is a local optimum) vs
  `control__osse_morph_b1w` 15.045 -> 8.064 (-46 %) - indicative only, one seed each, and J cannot
  see the diagonals. A T3 diagonal-balloon check is queued.
- **Scoring findings (four, all actionable):** (1) **four of the eight scored cells are single-term
  dominated** (`cov` 82-92 % of J on `b1t__rosse_morph`, `b2t__lecleach_iwata_ar`,
  `b3bt__salmon_x_signed`, `control`; the crease seed was 80 % `dislope`); (2) **the Le Cleac'h
  loading experiment did not work** - `load 0.5` contributes 0.11 of 5.60 J (**2 %**) because the raw
  load term is 0.02-0.22 against flat ~5, so the weights do not mean influence; **normalise the
  terms** before any further weight work; (3) `f_load_hz` reads 500 Hz on the Le Cleac'h seed, which
  is the grid floor, not a measurement; (4) the screen grid starts at 500 Hz, so the 300 Hz band
  floor is a verify-only promise.
- **Ladder (8 kHz, fused):** 5,106 dofs 2.55 s/freq at 21 % VRAM / 8,919 6.62 s at 41 % / 12,183
  11.0 s at 73 % / 13,999 13.78 s at **88 %** / 16,960 96 % **unusable**. The 90 % rule binds just
  above 14k: a 706 mm B3a (~10k dofs) is fine at 8 kHz, a 90x60 at 400 Hz (~17k) is not.
  **Cost model corrected:** inside one frequency **assembly is 73-96 % of the cost** and the solve is
  0.07-0.94 s; a campaign eval at ~11,967 dofs logs 9.5 s/frequency, matching the standalone 12,183
  number, so **the assembly is paid per frequency**. The frequency count, not the dof count, is the
  throughput knob.
- **Observer (`tools/observe_run.py`, new):** 384 samples at 5 s, **read the two phases
  separately**. Ladder rungs: 92 % `gpu_solve`, median util 100 % (GPU-bound). **Search jobs** (75
  samples, ~6 min): `gpu_solve` 33 %, `between_evals` 39 %, `refusal_or_mesh` 24 %, `cpu_idle` 4 %,
  **median GPU utilisation 24 %**, VRAM 931 MiB, 19 W - the card is idle-waiting, not working. The
  search window is short (one 31-eval cell) so the pipeline opening is promising but **must be
  re-measured over a full search window** before scheduling the work.
- **Owed:** gcurve reseed; term normalisation; the `dataset/record.py` v3 rejection (no dataset
  records from any v3 run tonight); full offline suite; LHS audit of the widened boxes +
  `tools/expand_walls.py`; per-frequency timing instrumentation + the concurrency A/B; sandbox law
  card browser check; catalog generator recursion into campaign folders; `osse_baseline` 803 x 643
  vs its 750 x 600 envelope; parked `make_shape_variants.py`.

## 2026-10-26 (late) - LEARNINGS RECORDED

- docs/research/LEARNINGS_2026-10-26.md: 13 durable findings (Ath creases = per-direction law; guiding-curve rules; plausible crease shapes; FREEFORM Morph target; self-approach fix; boxes vs CMA; per-type scoring; J blind spots; driver realism; drivers per brief; fused ceiling; GUI). Indexed in docs/INDEX.md; pointer appended to NOTES_FOR_SENIOR.md.

## 2026-10-26 (night, during the smoke run) - READ-ONLY RUN OBSERVER (`tools/observe_run.py`)

- **Why:** the first pass at "can we run twice as fast" had to infer the GPU/CPU phase split from
  ndjson timestamps. This records it directly, once per 5 s, for any night: GPU utilisation, VRAM
  used/total, power, temperature, SM clock vs max, total CPU % and the per-process CPU of
  `python.exe` / `julia.exe` / `hornlab-search.exe`, the running job (newest job log), and the
  newest run's eval count, last row's mesh/solve seconds, dof count and error kind. One JSON line
  per sample to `runs/nights/<night>/observe.ndjson`; on exit it writes
  `observe_summary.md` (phase shares, utilisation histogram, VRAM/power stats).
- **Read-only by construction:** `nvidia-smi` queries, `psutil` counters, and reads of
  `summary.jsonl` / the newest job log / the newest `search.ndjson`. It never launches a solver and
  never writes into a run directory.
- **First samples (smoke_2026-10-27, `t1__b3bt__salmon_x_signed`):** GPU 100 % util at 695 MiB VRAM
  of 8,188, 77 W, 70 degC, SM clock 2,550 of a 3,105 MHz max, total CPU 22.6 % while `python.exe`
  is 128 % and `julia.exe` 144 % - the mesh/metrics side uses ~2.7 cores while most cores idle.
  That is the pipelining headroom the speed-up analysis was looking for.
- **How to use it later:** phase shares give the CPU/GPU pipeline ceiling (`1 / gpu_solve_share`);
  the utilisation histogram gives the concurrency headroom; `evals` deltas vs dofs give a
  throughput model; the VRAM column gives the two-way-parallel budget per cell size.
- Docs + one tool; no code path the campaign uses was touched.

## 2026-10-26 (night) - README rewrite + GUI screenshots; main fast-forwarded

- Owner: friendlier README with screenshots, no personal names. New intro/pitch, docs/images/*.jpg (sandbox crease, 8-lobe mouth, live status, runs, run charts); technical sections kept below. main fast-forwarded to unified-typologies.

## 2026-10-26 (night, during the smoke run) - README REFRESHED TO THE CURRENT TREE

- **Status block** (was 2026-10-22): 41 typologies in `examples/catalog.yaml`; **Le Cléac'h is enabled** (the README still said "disabled until a verifiable published construction is available" - it was re-enabled 2026-10-25 with its dossier); the per-direction `az_*` law and the OS-SE guiding curve as searchable mechanisms; objective-v3 K-law f0 (plus f0_v on wide horns); the overnight runner.
- **Known limits corrected:** "nothing above 5.5 kHz is scored on an 8 GB GPU" is superseded by the measured ladder - coverage graded to 8 kHz at 12,000-dof caps, 8 kHz safe to a ~474 mm mouth, 10 kHz to ~353 mm, ≥550 mm at 8 kHz memory-saturated. Added the real blind spot: **the objective reads only the H and V planes**, so diagonal (45°/135°) behaviour - what a creased wall changes - is not scored.
- **Dataset caveat recorded where users will see it:** objective-v3 runs write `search.ndjson` + `best.json` but **not** dataset records (`dataset/record.py` accepts v1/v2 only). Found tonight in all 27 T0 jobs; fix owed (see ISSUES).
- **Name:** "Collin's HornLab packages" -> "the HornLab mesher and BEM solvers" (owner request: no personal name in the README).
- **Commands/docs:** the `gui` row now names the typology sandbox and generated tooltips; a sentence covers `tools/run_campaign_night.py`; the docs list gains the generated `docs/reference/{PARAMETERS,TYPOLOGIES}.md` pair and `docs/evidence/`.
- Docs only - no code or config change, and the running night is unaffected.

## 2026-10-26 (night, pre-smoke) - SENIOR SCORING REVIEW: each native control scored for its own job

- **Why:** the native campaign controls were all on objective v2 (no f0 mask) except Le Cleac'h. For `crease__core_law` and the two ATH natives that means the score was dominated by low-frequency coverage error no shape can fix, so the search would chase that instead of the crease parameters. A Le Cleac'h was being scored as if it were a constant-directivity horn, i.e. penalised for narrowing by design.
- **Three briefs changed (text only, `examples/briefs/campaign_2026-10-26/`):**
  - `native_ath_core_2in.yaml` - `objective.version` 2 -> **3**, `target.f0_hz` **1280**: CORE's measured 397 mm mouth holds 50 deg from 25,400,000 / (397 x 50) = 1,280 Hz. It is not a K-law design; the f0 only masks coverage below what the mouth can hold.
  - `native_twinray_380_14in.yaml` - version 2 -> **3**, `target.f0_hz` **743** and `target.f0_v_hz` **1397**: the published 380 x 303 mm mouth holds 90 deg from 25,400,000 / (380 x 90) = 743 Hz and 60 deg from 25,400,000 / (303 x 60) = 1,397 Hz.
  - `native_lecleach_1200_1in.yaml` - `weights.cov` 1.0 -> **0.3**, `weights.load` 0.0 -> **0.5**, `target.z_min` 0.0 -> **0.7** (dislope already 0, f0 1200 / v3 unchanged): a Le Cleac'h narrows ~180 -> ~54 deg across a 90 deg target, so coverage is secondary and loading is what it is for.
- **Not changed:** every B1/B2/B3 brief is already v3 with f0 (wide ones with f0_v), the `*_rows` briefs already carry dislope 0, and the B3b briefs already carry load 0.5 / z_min 0.7.
- **J is NOT comparable with earlier results** on those three brief names - said outright in each brief's header and in tonight's night-file comment.
- **Night reordered and re-budgeted** (`runs/nights/smoke_2026-10-27.yaml`, runtime only): T0 (27 jobs, budget 1) -> mini-T1 (9 jobs) -> fused-ceiling ladder LAST, 17k last of all. The **crease A/B runs at equal budget 60** (`crease__core_law`, `crease__osse_b1w`, `control__osse_morph_b1w`; ~17 searched knobs, ~12 designs/CMA round, ~40 min each); `gcurve__osse_b1w` joins at budget 30; the other five stay at 30. Dry-run resolves **41 jobs**. Rationale for the ladder last: 15,984 dofs measured 458 s/freq and 20,237 killed the worker host, so a hang there cannot cost horn data.
- **Known scoring limits to state in the morning report (no code change tonight):** the score reads only the H and V planes (diagonal crease / X-shape benefit invisible); screen solves start at 500 Hz so "loads to 400 Hz" is judged at verify (300 Hz floor) only; the loading term is averaged over the whole band and diluted by the always-loaded high end; coverage is still graded to 8 kHz, past the 1.4-inch driver's ~5.6 kHz cross-mode (owner's choice).
- **Verification:** all three briefs `load_brief` clean with the intended values (v3, f0 1280 / 743+1397 / 1200, z_min 0.7, weights cov 0.3 load 0.5), night `--dry-run` prints 41 jobs in the stated order. No GPU/Julia work in this commit.

## 2026-10-26 (night, after the az law) - CAMPAIGN BOXES RE-OPENED + THE ATH CREASE CLASS

- **Owner ruling applied:** a search box is never the binding constraint - the brief envelope plus mesh validity are. The campaign lane had narrowed boxes to hold the invalid rate under 40 %, which left searched knobs boxed at 1-10 % of their seed (b1w biradial `L` 5 %, `h_rm` 4 %; b3bt salmon `g_fc_h` 7 %; b3a rollback `g_T` 2 %; every `*__rosse_morph` `R_mm` 8-11 %, aspect 6-9 %). **180 searched knob boxes across the 23 cells** now sit on physical ranges: wall half-angles 10-80 deg, OSSE n/s/k/q 1-10 / 0-1.5 / 0.3-5 / 0.90-1.0, exponent 2-10, `L_mm` 0.4x seed -> the brief's `max_depth_mm`, mouth-size knobs 0.6-1.15x seed, rows cutoffs 0.7-2.0x seed, rows T/stop/x_amp/x_fc 0.3-1.0 / 90-175 / -0.4-0.4 / 0-0.3, R-OSSE tmax/m/r/b/q, morph rate/corner/fixed 0.5-8 / 0-80 / 0-0.6, `gcurve_*`, and the `az_*` law row. Each box is intersected with the `families.KeySpec` hard limits, still contains its seed, and **no edge was ever narrowed** (a current wider edge wins - e.g. `b1t` stop keeps 158, `native__lecleach_*` stop keeps 200). Exceptions kept narrower for measured physics: `g_stop_deg` 90-150 on the two `salmon_x_signed` cells; `native__ath_twinray_380` takes the widest of {current, table, the ATH lane's originals}. `search.infeasible_penalty: graded` is now set on all 23. **Seeds are byte-identical 23/23**, all 25 `search: false` pins intact, a second run is a no-op, every searched box contains its seed, and the diff touches only `lo:`/`hi:` values plus the 14 penalty insertions (header comments and formatting preserved by a targeted line patch, the `save-bounds` precedent). Left alone because the handoff table has no row for them: `a0_deg`, `g_ar_p`, `g_eps_m`, `g_eps_start`, `s1`, `s2`.
- **Not re-audited (owner: no CPU time):** the widened invalid rate is unknown by design; tonight's mini-T1 is the measurement. Recorded in `docs/evidence/CAMPAIGN_DRYRUN_2026-10-26.md` §8 with the full before -> after table.
- **The Ath crease class - 4 new cells** in `examples/typologies/campaign_2026-10-26/`, all native OSSE, `cuda_fused: true`, caps 12,000, epw 6, `morph_target 1` / `exponent 2` / `morph_allow_shrinkage 0` / `az_sf_m` / `gcurve_type` pinned, penalty graded:
  - `crease__core_law` - the PUBLISHED CORE law exactly (a_deg 5, sf amp 35, m 4, n1/n2/n3 12/15/16, a 1, b 0.618, cos amp -15 pow 10, n 6 + 1.5 cos^2, s 0.6 + 0.23 cos^2), Morph rect at the measured 399x399 mouth, 17 searched dims.
  - `crease__osse_b1w` - "crease this horn" on b1w: amp 30 / cos amp -10 / n1 12 / n2 15 / n3 16 / b 0.618 / pow 10, `a_deg` base 10 = b1w's 30 - 20 so **a(0) is unchanged** (10 + 30 - 10 = 30), L 140 and the rest from `b1w__osse_baseline`, 14 searched dims.
  - `gcurve__osse_b1w` - the guiding curve instead of the law: type 1 (superellipse), rot 0, dist 0.5, se_n 4, aspect 0.7, width = b1w's 335 mm mouth, 9 searched dims.
  - `control__osse_morph_b1w` - the A/B control: b1w's seed + Morph rect at 335 x 291.3, no law, no curve, 8 searched dims.
  - **Aspect-ratio call (for the senior to adjudicate):** pinned at 1.0 for `crease__core_law` (CORE is circular) and `gcurve__osse_b1w` (the mesher requires a circular section with a guiding curve), but left at b1w's **1.15** for `crease__osse_b1w` / `control__osse_morph_b1w`, because their cell rows say "the rest from b1w__osse_baseline" and aspect 1.0 would push the V mouth to 335 mm - past the brief's 300 mm envelope.
- **Verified without meshing (owner: no CPU passes):** all four load through `load_config`, and `to_mesher_config` on each seed emits the folded `profile.a_deg` expression, the `gcurve` section, and the Morph block; `config_sha` computes. Geometry/coverage validity is what tonight's T0 gate is for.
- **The night file** (`runs/nights/smoke_2026-10-27.yaml`, runtime only, not committed) resolves to **40 jobs**: 5 fused-ceiling rungs at 8 kHz (~5k / 8.9k / 12k / 14k / 17k dofs), the 27-cell T0 validity gate at budget 1, and 8 mini-T1 jobs at budget 30. `--dry-run` prints all 40 and launches nothing.
- **Owed:** the widened-box LHS audit; `test_design_azlaw.py`'s siblings are green but the full offline suite is still deferred; the T3 diagonal-balloon check for crease vs control (queued, not run); campaign-folder configs still have no catalog tooltips (the generator does not recurse into subfolders); the shipped `osse_baseline` still measures 803 x 643 mm against its own 750 x 600 envelope.
- No GPU/Julia work in this commit.

## 2026-10-26 (night, latest) - PER-DIRECTION OSSE LAW: ATH CORE's a(p)/n(p)/s(p) as searchable knobs

- **Why:** the CORE/TwinRay creases are not a guiding curve and not Morph alone - the published script (at-horns.eu/core.html) writes the wall angle and the termination as expressions of the azimuth: `a(p) = a_deg + az_a_sf_amp*SF(p) + az_a_cos_amp*|cos p|^az_a_cos_pow`, `n(p) = n + az_n_cos2_amp*cos^2 p`, `s(p) = s + az_s_cos2_amp*cos^2 p`, with the Gielis superformula `SF(p) = (|cos(m p/4)/a|^n2 + |sin(m p/4)/b|^n3)^(-1/n1)`. Every previous typology used one coverage angle (the constant-azimuth reduction), so no shape in the tree could crease on the diagonals.
- **What landed (`design/families.py`):** 11 `az_*` knobs (section `azlaw`) on native OSSE, `AZLAW_DEFAULTS`, `azlaw_expressions` / `azlaw_values`, and `to_mesher_config` folding them into the mesher's OWN p-expressions for `profile.a_deg` / `profile.n` / `profile.s` (the `az_*` names never reach the mesher; the emitted a-expression falls back to the numeric base when `a_deg` is absent). Validation refuses a non-multiple-of-4 `az_sf_m` (quarter-model mirror symmetry), any sampled `a(p)` outside (0.5, 89.5) deg (every 3 deg over the quarter), and `n(p) <= 0` while `s != 0`; each refusal names the knob that caused it. **Absent or zero = byte-identical:** `json.dumps(sort_keys=True)` of the mesher config equals the no-az-keys call and carries no `az_` token anywhere.
- **Measured (the published recipe reproduces):** CORE values (a_deg 5, amp 35, m 4, n1 12, n2 15, n3 16, a 1, b 0.618, cos amp -15 pow 10, n 6 + 1.5 cos^2, s 0.6 + 0.23 cos^2) give **a = 25.0 / 33.8 / 23.4 deg at p = 0 / 45 / 90**, n 7.5 / 6.0, s 0.83 / 0.60 - the H/V numbers match the earlier `ath_core` midpoints exactly, and the diagonals open ~9 deg wider.
- **Sandbox (`gui/static/sandbox.js`):** a "Per-direction law (Ath CORE)" card on every OSSE typology (11 sliders + a CORE preset + a "crease this horn" preset that moves `a_deg` so `a(0)` is unchanged). **Committed unverified in a browser** (owner: no GUI click-testing tonight) - an owner eyes-on item, not a test result.
- **Docs:** `docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md` gains section "5b. Per-direction law (the exact CORE construction)" with the published expressions and the measured table.
- **Tests:** new `tests/test_design_azlaw.py` (6): the published a/n/s table, byte-inequality-free absence (no `az_` token anywhere), `az_sf_m 6` refused by name, `a(p) <= 0.5` refused, the folded expression in `profile.a_deg`, and the expression still emitted when the base key is absent. Focused gate **125 passed / 0 failed / 0 errors / 0 skipped** (`tests/test_design_azlaw.py`, `test_design_families.py`, `test_param_catalog.py`, `test_typology_ath_morph.py`, `test_design_generators_grid_variants.py`); `tools/gen_param_catalog.py --check` **OK** with **no regeneration needed** (the generator scans `examples/typologies/*.yaml`, and no committed typology carries `az_*` - the `az_*` knob docs are in `knobs_native.py` and reach the wire only for configs that use them); `node --check sandbox.js` **OK**.
- **Deferred (owner: no CPU time tonight):** the full offline suite. **Owed:** the sandbox law card's browser check, and campaign-folder configs still get no catalog tooltips because the generator does not recurse into subfolders.
- No GPU/Julia work in this commit.

## 2026-10-26 (night, later) - SANDBOX LAYOUT: 3D stays on screen while you drag

- Owner: "adjust sliders and still see the 3D view", "3D larger", "more sliding space, less text on either side". The 3D figure is sticky (desktop: the larger left column, height max(340 px, 100vh - 150 px); narrow: pinned on top at max(240 px, 45vh)); sliders sit in their own column; side/front views below the 3D. One line per knob (name | long slider | value | reset), ~25 px instead of ~60; the min/max search-box inputs hide behind an 'edit search boxes' toggle (remembered); help paragraphs fold into 'how ... works' toggles; guiding-curve presets on their own line. Static-only change (refresh the page).

## 2026-10-26 (night) - WHY NO ATH-STYLE CREASES, AND THE FIX: the OS-SE guiding curve in the sandbox

- **Owner question:** none of our typologies (incl. the TwinRay / CORE reconstructions) ever showed the puckered, lofted ridges of at-horns.eu's CORE / TwinRay / Opus; Morph was expected to make them and does not.
- **Diagnosis:** the creases come from a coverage angle that changes with DIRECTION around the axis. Ath gets it from the OS-SE **guiding curve** (superellipse / superformula, CORE's `sf()` script) and per-azimuth `a(p)` expressions; Morph only pulls the mouth outline to a rectangle. Our `ath_core` uses one coverage angle (the constant-azimuth reduction), `ath_twinray_380` is a FREEFORM generator with only H/V profiles, and NO config ever set a guiding curve although the search layer already carries `gcurve_*` (OSSE only) and the mesher supports it. Measured: CORE's mouth radius is 198 mm at every angle; with a pinched superformula curve (m1=m2=4, n1=0.5, n2=n3=1) it swings 407 -> 212 mm with azimuth, and with CORE's rectangle Morph the walls fold into throat-to-corner creases (seen in the sandbox 3D).
- **Sandbox:** a Guiding-curve card on every OSSE typology (off / superellipse / superformula; width, height/width, position along the length, rotation, se_n, sf a/b/m1/m2/n1/n2/n3; presets pinched 4-lobe / diamond / soft square / rectangle; per-knob 'search' ticks saved as search rows like Morph). The mesher requires a circular cross-section with a guiding curve, so the card holds exponent 2 / aspect 1 while it is on. A TwinRay-like OSSE (L 192, a 35, a0 5, pinched curve, rectangle Morph 380x303) previews at 383 x 306 x 188 mm vs the published 380 x 303 x 192.
- **Bug fixed:** a mesher config refusal (e.g. guiding curve + non-circular section) escaped the preview as a server error; it is now shown as the page's reason.
- **Next (owner):** a native-OSSE TwinRay / CORE typology that searches the guiding curve (+ Morph), replacing the H/V-only reconstructions for the crease class; optionally `a(p)` expression knobs. Suite 1663/1664 (remaining: campaign-config naming).

## 2026-10-26 (evening, later) - SANDBOX IS A REAL SANDBOX + MORPH EVERYWHERE + SELF-APPROACH FALSE-REFUSAL FIX

- **Owner asks:** "the sandbox idea was just to see what the sliders are doing" (it was boxed to the search bounds); "enable Morph for all the typologies that can take it, everywhere in the GUI"; "a switch on the sandbox page for each typology" between free and limited.
- **Free / search-limits switch (per typology, remembered):** FREE (default) - sliders span a wide explore range (catalog hard limits, else the search box widened by its span; positive quantities stay positive, angles < 90, stop 30..350) with the search box drawn as a band on the track, an 'outside search' chip, and a typeable value box (any number). SEARCH LIMITS - sliders stay inside each box and fixed knobs lock at the run's values. Fixed knobs (search:false / no bounds row: saddle amounts, wall thickness, ...) now have sliders; rows are two lines so the slider gets the full width.
- **Morph everywhere it applies:** one rule `gui/data.py::morph_capable` (native OSSE/R-OSSE/ICW/FREEFORM, generated typologies with an elliptical mouth; NOT rows/grid - their mouth is the per-azimuth law; NOT superellipse/rounded-rect mouths - the generator refuses two outline mechanisms). The sandbox shows a Morph card (target dropdown, width/height/corner/exponent/rate/fixed, allow-shrinking) with a per-knob 'search' tick; Save writes new search rows via save-bounds `add` (target + shrink pinned search:false, +-25 % boxes), validated by loading the patched config before any byte is written. Typologies and Launch pages show 'Morph' / 'Morph searched' pills.
- **Shapes a search would refuse are DRAWN** (red) with the reason (`rejected` list), instead of a blank; every preview reports measured `dims` (mouth W x H, depth; mirror-aware) and natives get an envelope measured from the geometry (the estimator still has no native branch). A brief whose driver conflicts with a pinned throat now explains itself instead of a server error. 3D: a folding inner wall is drawn with the mesher's own `wind_folds_individually` repair (count reported); a failing mouth-rim face is left out and reported. Caption follows the model's symmetry (quarter/half/full).
- **Uncatalogued configs (e.g. the campaign folder) open in the sandbox** from the config file itself (`/api/configs` now carries `bounds`).
- **Self-approach guard false refusals fixed (`design/generators/grid.py`):** stations count as non-adjacent at arc separation >= pi/2 x (2t+2) (a U-turn of that width), not >= (2t+2): the old rule compared a chord with an equal arc, and a chord is always shorter on a curved wall, so ordinary lip curvature was refused at 7.998 / 8.000 mm (salmon_saddle's own seed under 7040use; salmon_x_signed at x_amp 0.4). Real folds still refuse (hairpin test). Search validity changes for rows designs near that edge (fewer false invalid_geometry); `tests/test_mesh_build_grid.py`'s boundary test now forces the refusal (its fixture WAS the false positive).
- **Observed:** shipped `osse_baseline` measures 803 x 643 mm against its own `osse_75x45` 750 x 600 envelope (+7.3 %).
- **Tests:** new `tests/test_gui_sandbox_explore.py` (backend + node page helpers); preview/sandbox-page/mesh tests updated where they pinned the replaced behaviour. Suite 1660/1661 (the one failure: the uncommitted campaign config spelling a retired product name). Restart the GUI (`tools/launch_gui.ps1`) to pick this up.

## 2026-10-26 (evening) - GUI DISCOVERY: anything a search writes shows up (owner: "I don't want AI wiring every campaign")

- **Configs + briefs at any depth:** `gui/data.py::list_configs` scans every `examples/**.yaml` (except `briefs/` and `catalog.yaml`); `list_briefs` scans `examples/briefs/**` with kind `shipped` / `user` / the subfolder name. The sandbox's config index stamp now covers every config folder. Campaign folders (`typologies/campaign_*`, `briefs/campaign_*`) need no wiring.
- **No run cap:** `list_runs` returned the newest 300 only (233 on disk today); now all, with `run_summary` memoized on the ndjson stamp.
- **Auto campaigns:** runs that no `campaign.json` claims are grouped per (brief, mode) into `auto_<brief>__<mode>` leaderboards (listed after real campaigns, never superseded; `campaign_detail` builds them from the run folders). On today's tree: 13 groups that had no leaderboard before (e.g. user briefs 7040use, 75x35).
- **Night runner on the Status page:** `tools/run_campaign_night.py` also appends `=== <time> START/END <job>` lines to `runs/overnight/queue_<night>.log` (the format `queue_steps` already parses).
- **Tests:** `tests/test_gui_discovery.py` (5). Full offline suite 1648/1649: the one failure is the uncommitted campaign config `typologies/campaign_2026-10-26/b1t__lecleach_iwata_ar.yaml` spelling a retired product name (neutral-naming test) - the campaign-config lane's to fix, not this change. Restart the GUI to pick this up.

## 2026-10-26 (campaign Phase 0) - campaign briefs + 23 cells + CPU dry-run/LHS evidence LANDED (Steps 2C/3/4/5)

- **What landed (one commit, CPU only, no GPU/Julia):** the six lane reports copied into `docs/research/campaign_2026-10-26/` (A/B/C/D/E + orchestrator findings, no job json copied); 14 campaign briefs in `examples/briefs/campaign_2026-10-26/`; 23 campaign configs in `examples/typologies/campaign_2026-10-26/`; the measured evidence doc `docs/evidence/CAMPAIGN_DRYRUN_2026-10-26.md`; INDEX lines for every new doc.
- **Briefs:** b1t/b1w (90x60 @850), b2t/b2w (60x40 @1200), b3bt/b3bw (90x60 @600 loading), b3a (90x90 @400), four `*_rows` non-CD variants (dislope 0 + not-ranked note), and three native controls (Le Cleac'h 1200, CORE 2in, TwinRay 380). All carry band 300-8000, objective v3 (natives keep v2 / no f0), `grid.verify_points_per_octave: 6`, `source.cap: auto`, the campaign weight set, symmetry hv, and a header with purpose / K-law arithmetic / driver class / f11 disclosure. Wide cells use the D-11 option (b) commercial convention: H keeps the K-law mouth, V narrows to the envelope with `target.f0_v_hz` 1411 / 2117 / 941 Hz masking the V plane below the frequency the envelope can hold.
- **Configs:** every cell is a copy of its shipped config renamed `<brief-id>__<typology>.yaml`, with `brief_file` relative, `mesh.epw 6`, caps 12,000 all tiers, `solve.backend beat_cuda` + `cuda_fused: true`, `search cma sigma0 0.15 seed 1234 tolfun 1e-3`, and budget `max(100, 12*searched_dims)` (100-204). Generator cells use `generator.seed_policy: explicit` and the lane reports' per-brief seeds/bounds; R-OSSE+morph cells carry `wall_thickness_mm: 5` explicit, `morph_target` pinned (`search:false`), `morph_fixed <= 0.1`, `morph_allow_shrinkage: 0`. Every 1.4in native/generator cell is on r0 18.0. Full per-cell sources/changes are in each config header and in the evidence doc.
- **Step 5.1 (dry-run):** 23/23 `run --mode screen --dry-run` OK (log `runs/step3_5/dryrun_log.txt`). dofs 921-9,871 (all under 12,000), mesh 0.2-14.3 s, triangles 1,706-19,332; envelope overshoot 0.00 % on every seed. The mouth is within 10 % of the K-law on every tall/square cell (worst +4.9 %) and inside the envelope on every wide cell. **No cell dropped.** Three seeds were fixed by reseeding (never by widening): b1w OSSE L 169 -> 140, b2w OSSE L 135 -> 178, b3bw hypex L 210 -> 203.
- **Step 5.2 (LHS):** 16 points per cell (32 for the rosse_morph and salmon cells) through the real mesher with caps raised to 1e6 **in memory**; per-cell deterministic Latin hypercube. Invalid % (generator/mesher refusal + pre/post-mesh envelope + >12k dofs): 0.0-37.5 %. Four boxes were narrowed only after a >40 % invalid audit and only for a physical reason (recorded in the headers and the evidence doc): b1w biradial 62.5 -> 37.5 %, b2w hypex 62.5 -> 18.8 % (also reseeded L 215), b3bw hypex 62.5 -> 25.0 %, b3bt salmon_x 59.4 -> 25.0 %. No box was widened. The 31-37 % cells are reported as-is (below the narrowing trigger).
- **Step 5.3 (grids):** `mode_freqs` for `b1t__rosse_morph` prints **screen 12 / verify 29 / final 36** points (500..8000 / 300..8000 / 250..8000) — the expected frozen-grid counts with ppo 6. Verbatim list in the evidence doc.
- **Gate fix during this pass:** the first offline suite run caught the neutrality test on uppercase `IWATA` in three new config headers; changed to lowercase `iwata` (the shipped-row identifier). The seed/campaign data were unaffected.
- **Verification:** standard offline gate green - `compileall -q hornlab_search tests` clean, `tools/gen_param_catalog.py --check` OK, `node --check` x8 OK, offline suite **1664 passed / 0 failed / 0 errors / 0 skipped** (`runs/step3_5/suite.xml`; the count is +20 over the recorded 1644 baseline because ANOTHER lane's concurrent uncommitted `families.py`/`knobs_native.py` add dynamically-parametrized family keys - this commit adds no tests and stages none of those files). No GPU/Julia work.

## 2026-10-26 (campaign Phase 0) - doc fixes: S1A `widened_to_closure` correction + `n_in_band` meaning (impl-code2, Step 2E)

- **S1A verbatim record:** added a dated correction note at the TOP of `docs/research/typologies/S1A_DRIVER_PASS_ORACLE_FINAL_2026-10-25.md` (the body is unchanged): **"the biradial `widened_to_closure` widening is K-law-driven (reached 396.9/352.8 mm, past closure)"**. The old "widening only ever reaches the closure line" line inside the record is superseded by this note, not rewritten.
- **`n_in_band` meaning:** the scalar result field `n_in_band` is the **COV-SCORED point count**, not the count of solved points inside the band: for an f0-850 brief the screen grid scores **9** and the verify grid **21** of its solved points (`objective_v3` reports `score.sum()`; the full in-band set still drives rip/di/flat/load and the NaN bookkeeping). The field is **NOT renamed** - stored records and the frozen terms key set keep `n_in_band`; read it as "points that actually scored cov/dislope". With `target.f0_v_hz` set, the reported count is the H mask (`f >= f0_hz`).
- **INDEX/CODE_MAP:** untouched - this step added neither a doc nor a module.
- **Verification:** standard offline gate green - `compileall` clean, `tools/gen_param_catalog.py --check` OK, `node --check` x8 OK, offline suite **1644 passed / 0 failed / 0 errors / 0 skipped** (`runs/step2e/suite.xml`; docs-only, count unchanged). No GPU/Julia work.

## 2026-10-26 (campaign Phase 0) - rows `span: half_xz` LANDED (impl-code2; lecleach_asym upper-half `'12'` model, 2x dof saving)

- **What it does:** a fourth rows span, `half_xz` = phi 0..180 inclusive (ODD n_phi >= 25), the upper half across the xz mirror plane (y >= 0), quadrants `'12'`. `lecleach_asym` now accepts it: its `cos(phi)` asymmetry is even under the up/down mirror phi -> -phi, so the left-right asymmetry is intact and only a vertical mirror is used. Plain `span: half` (x >= 0) stays refused for `lecleach_asym`; `half_xz` is refused for the other rows kinds in this pass. The phi = 0/180 endpoint rows are pinned to y = 0 and the phi = 90 row to x = 0.
- **Mesh machinery:** `_GRID_SYMMETRY_AXES['12'] = ('y',)` (the mesher's y=0/xz axis), now DERIVED from `sizing.SYMMETRY_PLANE` instead of a second hand-maintained quadrant table; `build_grid_mesh` expects quadrants `'12'` for a `half_xz` span and builds the outer shell with `grid_outer_points(..., half_xz=True)`. `sizing.py` needed no change (`'12' -> xz`, QUADRANT_FACTOR 2 already present). The GUI preview's outer-shell call was updated to pass the same flag.
- **Measured (CPU, real `hornlab_mesher`):** the shipped `lecleach_asym_odd` seed's half_xz grid mirrors the full ring to **1.7e-13 mm** (direct upper half 1.4e-14 mm); meshing at a 2 kHz top gives **1,485 tris (half) vs 3,036 (full 48-row mirror-equivalent ring)**, ratio 2.04, symmetry plane xz, all 93 open edges on the plane, 0 non-manifold. `lecleach_asym_odd.yaml` is deliberately NOT switched to half_xz yet: the GPU equivalence A/B (<=0.05 dB / <=1 deg) is Phase B item 5.
- **Backend gap recorded (not fixed here):** `hornlab_beat_bem` rejects `native_symmetry_plane='xz'` (`reject_unsupported_native_symmetry`: BEAT mirrors x=0 and optionally y=0 only), while the CPU `hornlab_bempp_bem` backend accepts it. A `beat_cuda` half_xz campaign cell therefore needs a pinned-fork change or the bempp route; Phase B item 5 must decide. The mesh side is complete and CPU-validated here.
- **Artifacts:** a knob source changed (`ROWS_SPANS` feeds the span choice), so `tools/gen_param_catalog.py --write` regenerated `gui/static/param-catalog.v1.json`; `--check` is green and the `docs/reference` bytes were unchanged.
- **Tests:** new `tests/test_design_generators_grid_halfxz.py` (5/5): point mirror vs the full ring, outer-shell endpoints, symmetry-table derivation from sizing, validation/kind scope, and the mesher-gated triangle count + xz plane.
- **Verification:** standard offline gate green - `compileall` clean, `tools/gen_param_catalog.py --check` OK, `node --check` x8 OK, offline suite **1644 passed / 0 failed / 0 errors / 0 skipped** (`runs/step2d/suite.xml`; 1639 + 5 new). No GPU/Julia work.

## 2026-10-26 (campaign Phase 0) - overnight campaign runner LANDED (impl-code2; the RUNNER lane's written files, committed)

- **What landed:** the other lane's written-but-uncommitted `tools/run_campaign_night.py` (730 lines) and `tests/test_tools_night_runner.py` (9 tests), staged by explicit path only.
- **Protocol:** reads a runtime night YAML (`runs/nights/<night>.yaml`, not committed) and runs jobs STRICTLY SEQUENTIALLY (one GPU): pre-hygiene kills only `julia.exe` (PIDs logged first), runs `hornlab-search gpu-clean`, waits for `runs/.gpu.lock` to disappear, records the `nvidia-smi` VRAM baseline; each job is a subprocess with a per-job timeout (search 3 h / command 2 h) teed to `runs/nights/<night>/<id>.log`; post-hygiene runs `gpu-clean` again and records peak/after VRAM. The evaluation count is read from the run's `search.ndjson` (never from `--budget`), the best J is parsed from the search tool's final summary line, one JSON line per job goes to `summary.jsonl`, and a short `SUMMARY.md` table is written. A failed or timed-out job is recorded and skipped - never retried. Import-light (stdlib + PyYAML) with pure parsing/accounting helpers.
- **Verification:** the tool imports by path (module registered in `sys.modules`, `REPO_ROOT` correct); focused `tests/test_tools_night_runner.py` **9/9**; standard offline gate green - `compileall` clean, `tools/gen_param_catalog.py --check` OK, `node --check` x8 OK, offline suite **1639 passed / 0 failed / 0 errors / 0 skipped** (`runs/step2-runner/suite.xml`). The 9 runner tests were already part of the recorded 1630 baseline as an untracked file (see the seed_policy entry), so committing them does not raise the count. No GPU/Julia work.

## 2026-10-26 (campaign Phase 0) - objective v3 amendment: optional per-plane `target.f0_v_hz` LANDED (impl-code2; absent = bit-identical)

- **What it does:** `target.f0_v_hz` (appended after `f0_hz`; `Target` stays positional) makes the coverage term the SUM of two separately masked means: the horizontal squared error over `f >= f0_hz` and the vertical squared error over `f >= f0_v_hz`, with `freq_weights` restricted to each mask. `dislope` keeps the H/f0 mask; `n_in_band` reports the H-mask count. Validation: `0 < f0_v_hz <= band_hi_hz` and, when `f0_hz` is set, `f0_v_hz >= f0_hz`; every refusal names `target.f0_v_hz`.
- **Absent = bit-identical:** the pre-amendment expression is kept verbatim inside the `f0_v_hz is None` branch. Goldens captured before the edit are unchanged on the landed tree: `lecleach_asym_odd` `config_sha d153b1dd96d1`, seed hash `103316ebbfeb`, screen solve-spec hash `cfdb0910d126`, J `9.526627218934914` (`n_in_band 10`). Dataset records emit `f0_v_hz` only when set; the config feasibility record does the same, so absent-key record bytes are unchanged.
- **Contract:** `docs/plan/01_CONTRACTS.md` is FROZEN and was not edited. Dated amendment recorded here: **"objective v3 amendment 2026-10-26: optional per-plane f0_v_hz, owner-directed"**; the same text is appended to `NOTES_FOR_SENIOR.md`.
- **Where it needed no change:** the in-run memo key (`search/evaluate.py:660-667`) and the GUI compare fingerprint (`gui/data.py:619-621`) do not carry `f0_hz` either (they key design/mesh/solve and band edges), so there is no `f0_v_hz` key to add; `report/html.py` rebuilds `Target` from `cfg.target_raw` and needs no field handling.
- **Tests:** new `tests/test_objective_v3_f0v.py` (9/9): absent path `==` a verbatim copy of the pre-change function on both plain and freq-weighted cases; a vertical error below `f0_v` leaves J exactly unchanged while a horizontal error between `f0` and `f0_v` counts (and a vertical error at/above `f0_v` counts); validation refusals; `load_brief` + config feasibility emission.
- **Verification:** standard offline gate green - `compileall` clean, `tools/gen_param_catalog.py --check` OK, `node --check` x8 OK, offline suite **1639 passed / 0 failed / 0 errors / 0 skipped** (`runs/step2b/suite.xml`; 1630 baseline + 9 new). No GPU/Julia work.

## 2026-10-26 (campaign Phase 0) - ICW nested driver pin LANDED (impl-code1; `icw_seed.r0_mm`)

- **Bug:** the WP2 driver pin only looked for ROOT `r0_mm`. Every ICW config keeps its throat at `seed_params.icw_seed.r0_mm` (bounds carries the flat dotted key `icw_seed.r0_mm`), so the pin silently missed ICW entirely and a campaign brief could pair an 18 mm driver with a 12.7 mm horn.
- **Fix:** `_apply_brief_driver_pins` now pins `icw_seed.r0_mm` for `family: ICW` whenever the nested seed key or the dotted bound exists, using the SAME `_force_pin` semantics and error shape as the root path: a mismatching pinned bound is refused (`ConfigError` naming `bounds.icw_seed.r0_mm`), an unpinned one becomes `lo=hi=driver`, `search: false`, and the nested seed is forced. The embedded-brief resume grandfather is untouched.
- **Tests:** new `tests/test_config_icw_driver_pin.py` (4/4) - a copy with a searchable nested bound under an 18 mm brief gets seed 18 + bound 18 (and the `DesignSpace` seed reads 18); the shipped 12.7 pin under an 18 mm brief is refused; the shipped config under a matching 12.7 brief is unchanged; an embedded 18 mm brief still loads the old run grandfather.
- **Verification:** focused 75/75; standard gate green - compileall, catalog `--check`, `node --check` x8, offline suite **1630/0/0/0** (`runs/step2c/suite.xml`). No GPU/Julia work.

## 2026-10-26 (campaign Phase 0) - `generator.seed_policy` opt-out LANDED (impl-code1; absent = byte-identical)

- **Why:** `_derive_generator_geometry` overwrites generator seeds from `target.f0_hz` on every campaign brief. Its rows constants are wrong for Salmon (1.88e5 vs measured 3.23e5 at stop 150) and its JMLC rule (geometric-mean mouth then fc-floor clamp) collapses Le Cleac'h seeds to ~313 mm round horns. The campaign needs hand-measured seeds without disabling the honest K-law feasibility record.
- **Contract:** new optional `generator.seed_policy`, value `derive` (default; absent behaves exactly as today) or `explicit`. With `explicit`, `_derive_generator_geometry` returns before touching `seed_params` or `bounds`, keeps the feasibility block, and appends `{"knob": "-", "note": "seed_policy explicit: derivation skipped"}`. Anything else is a `ConfigError` naming `generator.seed_policy`. The directive stays in `raw` (so `config_sha` covers it) but is filtered out of `Config.generator` and defensively stripped in `registry.materialize`, so it can never reach a mesher config.
- **Byte-identity:** `tests/test_config_seed_policy.py` pins the pre-change goldens for `salmon_elliptical` and `lecleach_rollback` under `examples/briefs/organic_rollback_14in.yaml` (seed_params, derivation notes, `config_sha` `9b5cc34de453` / `f2e29be7c418`); explicit keeps every YAML seed/bound and refuses bad values; a materializer spy proves the key is never passed through.
- **Verification:** focused 10/10, adjacent config/derivation/design 90/90; standard gate green - compileall, catalog `--check`, `node --check` x8, offline suite **1626/0/0/0** (`runs/step2a/suite.xml`; 1607 baseline + 10 new + 9 from a concurrently-added untracked lane file, never staged). No GPU/Julia work.

## 2026-10-26 - MEASURED GPU CEILING AT 8 kHz AND 10 kHz (owner-requested stress ladder; real VRAM numbers replace the earlier estimates)

- **Owner ask:** "what about 8,000 hertz - can we do that? why don't you run a test and see if it crashes my card", then "if we can actually fit it at 10,000 it's not going to crash the car". Also: cap the mouth at 500 mm and use whatever dispersion that supports.
- **Method (one GPU job at a time, repo hygiene followed):** pure-OSSE seeds (`s=0, k=1, aspect=1` so the analytic L->mouth relation is exact), `epw 6`, quarter domain, dof caps set to 200,000 so the PHYSICAL limit is what shows; each rung meshes, then solves ONE frequency at the ladder's top; `BeatBackend(track_vram=True)` reports peak; `worker.shutdown()` after each rung; Julia cleared before and after. Harness `%TEMP%\opencode\pass40\rung_test.py` (parameterised by band top); raw results in `rungs\8k|ladder.json` and `rungs\10k\ladder.json`.
- **8 kHz ladder (mouth / tris / solve / peak VRAM / headroom of 8,188 MB):**
  293 mm / 4,208 / 31.9 s / **1,219 MB** / 6,969 · 353 / 5,972 / 28.7 s / **2,193** / 5,995 · 403 / 7,644 / 29.5 s / **3,340** / 4,848 · 474 / 10,402 / 29.4 s / **5,797** / 2,391 · 500 / 11,516 / 29.7 s / **7,212** / 976 · 550 / 13,866 / 24.7 s / 7,397 / 791 · 635 / 18,236 / 25.3 s / 7,501 / 687.
- **10 kHz ladder:**
  293 / 6,476 / 21.6 s / **2,541** / 5,647 · 353 / 9,232 / 29.1 s / **4,853** / 3,335 · 403 / 11,816 / 30.9 s / **7,333** / 855 · 424 / 13,060 / 31.0 s / 7,545 / 643 · 448 / 14,428 / 35.4 s / 7,330 / 858 · 474 / 16,068 / 64.0 s / 7,516 / 672 · 500 / 17,832 / 25.6 s / 7,442 / 746.
- **No crash - confirmed, and the failure mode is understood.** The card never died; at the top rungs the peaks PLATEAU at ~7.3-7.5 GB (the physical 8,188 MB limit) and stderr carries `RuntimeError: Out of GPU memory trying to allocate ~630-660 MiB / Effective GPU memory usage: 100.00% (7.996 GiB)` with `Memory pool usage: 15.9 GiB reserved`. That pool figure is the giveaway: BEAT is oversubscribing past VRAM into host memory (WDDM), which is why a 474 mm 10 kHz solve still "completes" while taking 64 s instead of 31 s. **So "ok" is not "fits"** - the usable rule is PEAK + ~800 MB headroom (the GUI baseline alone is ~350-500 MB), not "did the solve return".
- **Verdict (the numbers that govern future briefs):**
  - **8 kHz: safe to ~474 mm** (5.8 GB, 2.4 GB headroom). 500 mm works but leaves under 1 GB - too tight for a long search. >=550 mm is memory-saturated and must be treated as unavailable.
  - **10 kHz: safe to ~353 mm** (4.9 GB, 3.3 GB headroom). 403 mm is the edge (7.3 GB, 855 MB); >=424 mm is saturated. 500 mm at 10 kHz is not viable.
  - Converting to dofs (measured tris x 0.51): 8 kHz safe ~5,300 dofs; 10 kHz safe ~4,700 dofs, edge ~6,000. **The shipped 5,000-dof screen cap and 8,900 verify cap were therefore well-judged** - this ladder says the physical ceiling is not far above them.
- **Owner brief set as of 2026-10-26 (saved in `examples/briefs/user/`):**
  - `cap500_90x90_650hz_1p4in` - 90x90 at **f0 650** (owner corrected 565 -> 650), mouth 434.2 mm inside the 500 mm cap. ~8.2k tris / ~4 GB at 8 kHz: the comfortable one.
  - `cap500_90x60_850hz_1p4in` - 90x60 at f0 850 (a 90x60 pattern at a 500 mm mouth requires >=847 Hz), mouth 332 x 498 mm.
  - `cap500_60x40_1270hz_1in` - the cap-compliant narrow brief: 40 deg at 500 mm requires >=1270 Hz, mouth 333 x 500 mm.
  - `narrow_60x40_800hz_1in` - **owner override, cap deliberately not applied**: 60x40 down to **800 Hz** needs 529.2 x 793.8 mm. At an 8 kHz top that extrapolates to ~28-29k tris, well past the 8,188 MB card; the owner accepted that it may fail ("it's gonna run on my card"). At a ~4 kHz top it is ~7.3k tris / ~3 GB and viable.
  - `wide_90x60_500hz_1p4in` (f0 500, 564 x 847 mm) stays as the unconstrained wide reference; `lecleach_90x90_1200hz_1in` (235 mm) stays as the Le Cleac'h brief.
  - Deleted as superseded: `cap500_100x100_500hz_1p4in` (owner: too wide), `cap500_90x90_565hz_1p4in` (f0 moved to 650), `narrow_60x40_880hz_1in` (replaced by the 800 Hz narrow).
- **Practical home:** the 434-500 mm briefs run best at a 5,500-6,000 Hz screen (~3.2-4 GB) with an 8 kHz verify on finalists; 10 kHz is only reachable at <=353 mm (measured).
- **Correction on record:** my earlier "a 500 Hz horn analysable to 10 kHz must be >=150-180 deg wide" line was arithmetic from forcing the mesh budget, not acoustics; a 500 mm mouth is 14.6 wavelengths at 8 kHz and cannot hold a 100 deg pattern there, let alone 180. The measured ladder supersedes that reasoning - the constraint is VRAM, and the honest fix is band-limiting what `cov` scores, not widening the horn into an impossible shape.
- **Follow-ups this unlocks:** (1) set `solve.cuda_fused: true` + `dof_cap_verify: 12000` for the 500 mm briefs since fused CUDA is the shipped path to the 12,000 caps; (2) add `target.cov_band_hz` so coverage is scored over the band the horn can actually hold while ripple/flat/DI score to 8-10 kHz; (3) the cap-500 briefs' dispersion table (f0 vs max coverage at 500 mm): 500 Hz -> 101.6 deg, 700 -> 72.6, 850 -> 59.8, 1000 -> 50.8, 1270 -> 40.0, 1450 -> 35.0.

## 2026-10-25 (late) - ATH FRAMEWORK PASS: native Morph on every family, `ath_core` + `ath_twinray_380`

- **Morph surface:** `morph_*` (including `morph_exponent`, target 3) is legal for OSSE, R-OSSE, ICW and FREEFORM. The old FREEFORM `morph_target` refusal is gone; the mesher already supported it. Generated typologies opt in through the same knobs; an absent `morph_target` emits no morph keys and is byte-identical. The generator requires `mouth: ellipse` when native morph is active.
- **`ath_core`:** native OSSE generalization of the published 2-inch CORE recipe (constant-azimuth reduction; a 24.2 / n 6.75 / s 0.715 / q .996 / L 260 / s1 1.14 / s2 .025). Native Ath Morph is searched: target shape (1-3), exponent, width, height, corner, rate and fixed part. Brief `ath_core_2in` (50x50, 650x650x520, no K-law f0).
- **`ath_twinray_380`:** published-dimension reconstruction of the 1.4-inch 380 Suite (380x303x192, 90x60 target, 700x600x320 envelope). Measured: the mesher's FREEFORM rectangle-morph guard rejects a rounded-rect target on this elliptical H/V base (non-convex at t≈0.75 for every corner tried); target 2/3-exp-2 mesh but are not the product. The config therefore uses the generator's searchable superellipse cross-section (`mouth_exponent`), with the native morph route documented as available for compatible bases.
- **Search counts:** `ath_core` 15, `ath_twinray_380` 12; wide boxes anchored on the published value near the middle, envelope is the outer constraint.
- **Evidence:** `docs/evidence/ATH_TYPOLOGIES_2026-10-25.md`. Dry-runs: CORE 6,174 tri / 3,232 dof / mouth 397 mm; TwinRay 3,796 tri / 1,987 dof / mouth 380x303 mm. First GPU seeds: CORE J 42.448 / 3,232 dof / 15.3 s; TwinRay J 38.357 / 1,987 dof / 8.3 s (scratch dirs, one job at a time, GPU cleaned). Offline suite **1606/0/0/0** (`runs/ath_morph_suite_final3.xml`); param catalog `--check` green.
- **Docs:** dossier `docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md`; INDEX/CODE_MAP updated. NOT modelled: exact CORE `a(φ)` law, `Mesh.Roundover`, rear/enclosure, TwinRay rim frame/rollback.
- **Senior review + commit (2026-10-26):** code reviewed hunk-by-hunk; one fix (R-3): `morph_target` now has a hard 0..3 schema limit on every morph family, so an out-of-range code is refused by the search layer instead of the mesher (test `test_morph_target_out_of_range_is_refused_by_the_search_layer`); param artifacts regenerated (`--check` OK); ISSUES control-character typos fixed. Offline suite **1607/0/0/0** (`runs/ath_commit/suite.xml`). Committed by explicit paths only; `NOTES_FOR_SENIOR.md` (auto OOM notes) and `perturbed_osse_hv.yaml` (owner GUI edit) left uncommitted. Campaign plan v2 + senior readiness review (section 12) committed alongside: `docs/SOLVE_CAMPAIGN_PLAN_2026-10-26.md`.

## 2026-10-25 (late) - OWNER SCREENSHOT PASS: mouth ring mirrored, evolution 3D un-clipped, rollback section order preserved (three real bugs, each root-caused before editing)

- **What the owner saw** (two screenshots): the Front view drew the mouth as a single quarter fan anchored at the origin instead of a closed outline; the evolution time-lapse's 3D panel was completely blank (render chip and "mesh decimated to 15856 tris" both present, zero geometry); and the sandbox's vertical-plane section was a striped fringe instead of a wall band. The same mouth bug appeared on both pages, so it was one defect seen twice.
- **Fix 1 - mouth ring never mirrored** (`charts.js::mirrorRing`, new pure helper; wired into `evolution.js::mouthPath` and `sandbox.js::mouthBandPath` + the inner-ring stroke). Both pages received a symmetry-reduced ring from the payload and drew it verbatim, so a quarter payload rendered as one quadrant. The helper decides from the points themselves (the frames payload does not always carry `quadrants`): an arc inside one quadrant is mirrored into all four with traversal order preserved, a ring spanning one axis is mirrored across that axis, and a ring already spanning both axes is returned untouched (so full-ring/half payloads are never double-drawn).
- **Fix 2 - evolution 3D blank = a unit mismatch, not a renderer failure** (`view3d.js::init3dFrames`). Frame vertices are millimetres and `buildGeo` scales each geometry by 0.001 onto the metre stage, but the camera rig, lights and shadow ground were derived from the UNSCALED mm bounds: the horn occupied ~0.4 units while the camera sat ~600 units away with `near 0.001 / far 100`, so everything was beyond the far plane. The rig now computes its centre and `maxDim` in metres (`CENTRE_SCALE`), matching the geometry and matching `init3d`'s existing metre convention; the shadow-ground line already used `u.y0 * 0.001`, which is what exposed the inconsistency. `prepareFrames` is untouched, so the existing frame-preparation pins still hold.
- **Fix 3 - striped vertical plane = an invalid sort** (`sandbox.js::combinedSectionLoop`). The builder z-sorted `outer` ascending and `inner` descending to close the band loop, which is only valid for monotone meridians. Rollback rows typologies (`salmon_elliptical` at `g_stop_deg` 150 - the config in the screenshot) fold BACK in z near the mouth, so sorting scrambled the polygon and the even-odd fill broke into horizontal strips. The loop now preserves each plane's own point order (outer as given, inner reversed) and closes normally, which is valid for monotone and rollback meridians alike.
- **Verification:** `node --check` on charts.js / evolution.js / sandbox.js / view3d.js / app.js all green; `tests/test_gui_sandbox_page.py` + `test_gui_evolution_3d_toggle.py` + `test_gui_brief_authoring.py` + `test_gui.py` + `test_gui_param_tips.py` all pass. New pins in the sandbox node suite: a quarter ring must reach the -x and -y quadrants (mouth fix) and a non-monotone rollback meridian must come out in its original order, asserted exactly (sort fix).
- **Owner eyes-on:** reload the GUI (`tools/launch_gui.ps1`) and check the three views - the evolution 3D horn should now be visible and hittable with the camera/orbit, and both front views should show a closed mouth outline instead of a fan.

## 2026-10-25 (evening) - TYPOLOGY SANDBOX LANDED - P9 ASKS COMPLETE (backend fix-6 @ 8715d88 + page des-2 @ d5e3363; full offline suite 1593/0/0/0; node --check x8 + compileall + param-catalog --check all green)

- **The owner's ask, now live:** click any typology on the Typologies page -> `#/typology/<name>`; the page draws the H/V wall section and the mouth outline live while you DRAG any knob's slider, with a hot-swap 3D horn (quarter payload mirrored client-side, camera/orbit stable, `hl-v3d-render` prefs applied); each slider row shows the raw key + the editable min/max inputs on BOTH sides + the value + red at-limit / out-of-envelope chips; edited bounds SAVE to the bounds' own YAML home via a two-click armed `POST /api/save-bounds` (kill-run arm precedent, 5 s auto-disarm), rendering applied from-to rows and every backend note verbatim (the config_sha/resume honesty).
- **Backend (fix-6):** `GET /api/preview-shape/<config>?brief=&detail=2d|3d&knobs=` with the kind-first dispatch (grid rows -> the existing march + reuse of its envelope; superellipse grid -> march + estimator; CAD -> `available:false` BEFORE `to_mesher_config`; generators -> `registry.materialize` -> viewport at 65x24; native -> `Design(family)` -> viewport) + the FIVE-name seam module `gui/preview.py` over the mesher's own preview primitives (pinned FAIL-not-hasattr; no hand-written triangle loops anywhere = rule-2 compliant); frozen response shape with `slow`/`available` honesty per block; warm ticks measured 19-21 ms (generator), 8.9 ms (grid), 21.9 ms (native), `salmon_elliptical` honestly `slow:true` at ~585 ms. `POST /api/save-bounds`: all-or-nothing, comment-preserving targeted line patch (proof: every other line byte-identical + all 40 comments preserved on `salmon_elliptical.yaml`), each rejection reason surfaced (`unknown_key`, `lo_above_hi`, `exceeds_hard_limit` from the catalog's KeySpec column, `not_a_finite_number`, `config_not_writable` for root-level configs).
- **Page (des-2, sandbox.js 636-1,196-line module with a node-tested pure core):** `timingDecision` (fast = rAF-coalesced live 2D + hot-swap 3D on release/~450 ms idle; slow/sched rows = release-debounce 250 ms + an amber "updating..." chip - never fake-live), `mergedKnobTitle` (label + summary + the detail physics sentence + range, paramtips fallback), URL-state round-trip so theme/resize `route()` re-runs never wipe slider state, in-flight-merging fetch (newest wins, no queueing), graceful degradation with the endpoints dark (sliders still work from the catalog; save honestly disabled). One deliberate mirror: `applyRenderControls` stayed module-private in view3d.js, so sandbox.js REPLICATES the render-look recipe with the same tokens and the same `hl-v3d-render` key - values are mirrored, not imported (a view3d preset change needs a matching touch-up; recorded as the known coupling).
- **Integration verification (this tree, after both lanes settled):** FULL offline suite (gpu/slow/crosscheck deselected per conftest) **1593/0/0/0** (junitxml runs/sandbox_final/suite.xml; ~10.6 min), `node --check` x8 (app/sandbox/paramtips/evolution/view3d/charts/glossary/balloon), `compileall` clean, `tools/gen_param_catalog.py --check` OK. The one transient red during the concurrent lanes (a page-lane pin + a past-jobs reload) was cross-lane edit timing, not a defect - both pass on the settled tree.
- **Honest limits on record:** the FIRST tick on a cold process pays the one-time config index (~2-5 s; fix-6 memoized `list_configs` per process, warmed ticks are the numbers above) - a future caching pass can hide it; the render-pref recipe mirror (above); root-level `examples/*.yaml` configs are honestly refused by save-bounds (they are config surfaces, not typology files); native families' envelope marker is honestly `available:false` (the estimator has no native branch); rows 2D during drag is value-local only with the "updating..." disclosure.
- **Owner eyes-on list (WebGL/headless boundary, unchanged):** sandbox drag feel on a fast kind + a rows kind (updating chip), the 3D hot-swap camera stability, save-bounds round trip + the config_sha note, and the earlier evolution 3D toggle check.
- **P9 arc complete in this branch:** SSOT layer (4005e8a + bf20807 + 19cad0a) -> tooltips (711b856) -> spike gate (fix-5) -> backend (8715d88) -> page (d5e3363). Remaining open items are owner-decision/UX only.

## 2026-10-25 (evening) - SANDBOX FEASIBILITY SPIKE: GATE PASSED (fix-5 lane; prove-or-kill probe, zero repo writes; per-kind measured timings, one silent-wrong-geometry hazard found)

- **Verdict: the sandbox is livable for every resolved kind, and the 3D path is NOT gmsh and NOT the adaptive preview.** Measured on the idle machine, geometry only: **generator typologies** (`osse_axi` / `biradial_keele` / `conical`) 17-30 ms for a full 2D tick, **22-35 ms including 3D triangles** (live during the drag); **grid** (`grid_ellipse`) 3.7 / 8.0 ms (live); **native families** (`osse_baseline`, `rosse_baseline`, `icw_rollback`, `freeform_sculpt`) 5.4-11.6 ms / +3D 10.5-16.6 ms (live); **rows kinds** are march-bound - `lecleach_rollback` ~148 ms, `salmon_elliptical` ~580 ms (stable-run median ~242 ms with known spikes; `n_phi` cannot go below 13 by law, and `n_s` scaling does not rescue the salmon march) - so rows get an honest `slow: true` flag and a release-debounce, never a fake-live pretend. Coarse **gmsh** builds measured 380-2267 ms (correctly rejected as the path); the versioned `build_preview_geometry(lod="coarse")` is the honest public fallback at 29-54 ms but silently CANNOT serve grid/rows blocks (it builds a default OSSE - see hazard). Payload costs: 2D JSON ~2.9 KB; quarter 3D soup ~71 KB / 1 ms to serialize; the client mirrors 4x (quarter `quadrants:"1"`) instead of paying 4x on the wire.
- **The route the endpoint will take (proven by the probes):** `params -> families.to_mesher_config -> hornlab_mesher.viewport.build_viewport_geometry_from_config(..., point_lists=False)` at coarse density (65 angular x 24 length) gives the H/V meridian sections + mouth ring from the point grid; the 3D add-on tessellates that same grid with the mesher's own preview primitives (`preview.primitives._surface_grid / _grid_surface_from_selection / _smooth_mouth_rim`, `preview.horn._outer_shell_surfaces`, `preview.fidelity.analytic_grid_normals`) - every surface comes back as `PreviewSurfaceV1` with winding-vs-normal validated by the mesher itself, not assumed. GRID/rows kinds take the existing search-side march (`grid.grid_points` / `rows_grid_points`) and tessellate it the same way. The per-kind dispatch MUST branch on the params kind FIRST: `generator.name == "grid"` -> GRID route, other generators -> `registry.materialize`, `"cad" in seed_params` -> `available:false` BEFORE `families.to_mesher_config` (measured: cad raises a bare `KeyError: 'cad'`, and a bare/cad params dict handed to the preview entry point silently builds a default OSSE horn, 12,800 tris, mouth radius 210 mm for a design whose real mouth is 120 mm - the silent-wrong-geometry trap, now documented and pinned for the endpoint lane). Multicell `cad` is the only hard `available:false` kind: "the geometry is authored by `tools/cad/multicell.py`; there is no on-demand preview geometry in the mesher".
- **Hard-rule compliance path (decided):** composing the mesher's underscore preview helpers is sanctioned PRIVATE USE only through ONE seam module with a pin+guard test that fails loudly if any of the five names moves - the exact closed-issue-#9 pattern `mesh/grid_build.py` already uses for `build_point_grid`. Hand-writing triangle-index loops in `data.py` would BE writing a tessellator (rule 2); the seam keeps the assembly inside Magnus's code. The pin test must fail on absence, never soften to `hasattr`.
- **Envelope marker (measured):** `registry.envelope_overshoot_estimate` is 0.005-0.13 ms for generator + superellipse-grid params (positive controls verified: mouth x1.6 -> 0.193, `L_mm` 400 over a 220 envelope -> 0.715) and serves the GRID/rows branch genuinely - but it re-marches every row for rows kinds (570 ms for `salmon_elliptical`), so the rows endpoint must reuse the march it already did (cache the recipe block per config; `design/generated.py::design_from_knobs` costs the march TWICE - materialize + re-march - so the sandbox must not call it per tick). For NATIVE families the marker is honestly `available:false`: the estimator only has FREEFORM-anchor and GRID branches; OSSE/R-OSSE/ICW params return None.
- **Endpoint shape (design, ready to implement):** `GET /api/preview-shape/<config>?brief=<name>&detail=2d|3d&knobs=<urlencoded JSON>` dispatched in `server.py::App.get` next to the `mesh` branch, implemented in `gui/data.py::preview_shape` resolved through `list_configs`/`list_briefs` (never a client path); response `{version, config, brief, kind, units:"mm", quadrants, available, knobs, section:{h,v}(inner+outer), mouth, envelope, shape3d:{available,roles,verts,tris}, slow, timings_ms, notes}` with the house `available:false` honesty for each sub-block; invalid knobs (`GeneratorError`, envelope breach) return the generator's OWN message verbatim - never a fabricated shell.
- **Cost: zero GPU, zero `runs/` writes, zero repo writes** (probes under the orchestrator temp dir; coarse gmsh `.msh` scratch files written to Temp only). Probe outputs quoted verbatim in the lane report; timings tables above are the real medians from those runs.

## 2026-10-25 (evening) - PARAMETER TOOLTIPS LANDED (P9 ask 1; designer lane des-1 @ 711b856; catalog-grounded hover docs on every surface that renders a geometry knob)

- **The owner-visible change:** hovering ANY geometry parameter in the GUI now says what it physically does, in one line, with its search range - sourced from the committed parameter catalog (`gui/static/param-catalog.v1.json`), never invented. Examples (executed by the lane's node run): evolution `g_fc_h_hz` on `salmon_elliptical` reads `Salmon H cutoff (rows) [Hz]: Horizontal endpoint of the per-azimuth Salmon cutoff blend. Search range 600.00..1,200.00 Hz.`; the sens table's `L_mm` reads `Depth [mm]: Axial depth shared by both meridians, throat to mouth. Search range 80.00..140.00 mm.`
- **Mechanism (new `gui/static/paramtips.js`, 174 lines, ES module):** `loadParamCatalog()` (async cache fill, fetched the same relative way as the page's own JS; NEVER throws/rejects - a failed load is uncached so the next view retries), `docFor(configName, key)` (exact knob -> nested-path fallback `profileH.points.1.1` -> `profileH` -> `null`; never guesses ACROSS typologies - `h_a_deg` has three family-specific meanings and an unknown config never borrows another's), `formatSearchRange` / `formatParamTitle` (the `tip()` sentence shape + a 300-char cap), `paramTipHtml` / `paramTitle`, and the typology-card helpers. Visible text stays the raw key on data surfaces (the owner's cross-surface vocabulary: the same parameter reads identically in evolution/sens/compose/YAML, and long labels would flood 120 px mono cells); the hover carries `label [unit]: summary + Search range lo..hi` with the raw key named inside the title.
- **Five surfaces wired:** evolution knob rows (`evolution.js` - title-only on the truncated grid cell, no visual shift), run-detail sensitivity table, run-detail seed-derivation card (the call is pinned verbatim by an existing test, so the lane added a scoped `data-seedknob` marker + a `viewRunDetail` post-pass instead - no assertion touched, the pin itself re-asserted in the new tests), compose seed-preview rows, and the Typologies cards (knob chips: only `search: true` entries become chips so the count matches the card's own "N shape parameters"; name hover = description + knob count; `multicell_3x3` renders exactly as before).
- **Honest degradation, pinned by tests (10/10 new + suites green):** unknown key/type wrong family/nested-path-missing -> the pre-catalog raw-key behavior, word for word; pinned single-value bounds are stated honestly (`Search range 110.00..110.00 mm.` on `splice_osse_tractrix`'s `L_mm`); network failure degrades site-wide without breaking a page; legacy runs whose config name is outside the catalog degrade the same way (hard rule 3: never an invented word).
- **Verification:** `node --check` app.js/evolution.js/paramtips.js all green; `tests/test_gui_param_tips.py` 10/0/0/0; the GUI trio 118/0/0/0; `compileall hornlab_search/gui/` clean. Zero Python edits, zero payload-shape changes, no new route, theme tokens only (no new hex).

## 2026-10-25 (evening) - PARAMETER SSOT LANDED (P9; lanes fix-4 native authoring + fix-3 machinery/rows/native wiring; commits 4005e8a + bf20807 + 19cad0a; 125 knob docs / 39 typologies; zero authored horn numbers)

- **What the owner gets:** one findable answer, for users and agents, to "what does this knob do, what is it called, what are its bounds, and where does the code live" — for every typology in the catalog. This is the foundation the GUI tooltips and the typology sandbox consume (both still to come on this branch).
- **Design held from P9:** ANNOTATE the authorities, never re-home them. Hard limits are read live from `families.KeySpec`, defaults from `registry.DEFAULT_KNOBS` + the `grid.py` constants, per-typology seeds/bounds from the `examples/**.yaml` via `families.param_get` (nested FREEFORM/ICW-seed paths resolve to the ROOT doc while emitting one entry per exact YAML key), catalog identity from `examples/catalog.yaml`. The authored surface is prose + structure ONLY — every numeric value is read at build time (`AGENTS.md` line 29 enforced by a gate). Overloaded names (`n`, `q`, `a_deg`, `T`, `stop_deg`/`max_wall_deg`, `exponent`) carry per-domain contexts so a tooltip can never show the wrong family's meaning; the generator/rows/native meanings are authored separately and `exponent`'s 2.0-vs-4.0 dispute is flagged `doc_mismatch` with both claims cited, no winner picked.
- **What landed (three commits):** `4005e8a` the machinery (`design/params/`: schema.py frozen docs, knobs_generators.py 26 entries covering all 18 `DEFAULT_KNOBS` + block keys, import-light `__init__.py` that NEVER raises, `tools/gen_param_catalog.py --write/--check`, the FAIL-not-warn drift gate, the first generated artifacts) · `bf20807` the rows domain (`knobs_rows.py` 36 base names — every knob the 11 rows/grid configs can search incl. the G8 `a{k}_throat/a{k}_mouth` pattern keys — plus 25 per-typology overrides carrying the salmon-vs-Fourcade stop semantics, the signed `x_amp` convention, the ripple delivered-at-widest-station rule, R9 labels quoted from the dossiers) · `19cad0a` the native domain (`knobs_native.py` 63 entries with full two-way coverage against `families.FAMILY_KEYS` — OSSE 40/40, R-OSSE 19/19, ICW 20/20, FREEFORM 6/6 — plus 7 typology note groups; catalog wiring: bare-name lookup, root-of-path resolution, live KeySpec hard limits/choices, per-config seed defaults, `multicell_3x3` honestly resolved as CAD-only with `knobs: []` + `non_native_keys: ["cad"]`).
- **Artifact discipline:** `gui/static/param-catalog.v1.json` (718 KB) is the wire contract the vanilla-JS GUI consumes through the EXISTING static handler — zero new routes, zero frozen-payload changes. `--check` rebuilds and byte-compares; proven twice green, and a negative control (byte tampered) fails exit 1 with a diff line. Both markdown references (`docs/reference/PARAMETERS.md` + `TYPOLOGIES.md`) carry the GENERATED header; every `code_ref` is symbol-anchored and verified to resolve before emitting (no line numbers to rot).
- **The bounds contract the sandbox will need:** every knob entry carries `bounds_source = {file, key}` pointing at the exact YAML key a bounds edit must target (e.g. `{"file": "examples/typologies/conical.yaml", "key": "bounds.h_rm_mm"}`, and `{"file": "examples/osse_baseline.yaml", "key": "bounds.a_deg"}`), plus a published `validation_authority` block stating the search box vs hard schema limits distinction outright (the waveguide-generator lesson adopted).
- **Verification (pasted by the lanes, re-run across the three merges):** the gate 37/37 (`tests/test_param_catalog.py`), gui+config+grid_rows 91/0/0/0, families 45/0/0/0, the GUI trio 107/0/0/0, `node --check` ×6, `compileall` clean, and the numpy-blocked import-light subprocess proof (pinned in-suite): `design/params` imports with numpy absent and never touches mesher/search/GUI imports.
- **Honest contract gaps recorded (never invented):** catalog.yaml R9 provenance is comment-only so `source_status` records file provenance, not PASS labels; `wall_thickness_mm` has no YAML default for most generator typologies (the registry's fallback is stated, no number emitted); `perturb.mode`'s `legacy` default lives in `registry.materialize`, not YAML; several grid hard floors (`pnorm` lower bound, `x_fc`/`ripple_amp_mm` non-negative floors, `n_phi`/`n_s` parity minima) are validator literals rather than named constants, so their hard columns stay `null` with the rule stated in prose; `stop_deg`'s hard window is kind-specific (Salmon vs verified Fourcade) and is documented as prose, not one number; `dkappa_ds_abs_max`'s unit is ambiguous in the mesher's own docstring so `unit` is `None`; LOOKUP has no family table and no config, so it gets module-docstring coverage only; `exponent`/`morph_target`-code-3 doc/code mismatches are surfaced, unsilenced.
- **Next on the branch (in plan order):** the designer lane wires tooltips onto every surface that renders a raw knob name (fetching the committed JSON, using the existing `glossary.tip()` pattern); the sandbox spike proves or kills on-demand preview geometry; then the `#/typology/<name>` sandbox page with the inline editable min/max that writes back to the `bounds_source` home.

## 2026-10-25 (evening) - EVOLUTION 3D TOGGLE FIXED (fix-2 lane; branch `unified-typologies` @ cd71c1c; docs wording refreshed here)

- **The owner-visible bug:** ticking `3D` on the search time-lapse page left the canvas showing `3D off - flip the 3D toggle above.` while the checkbox rendered checked.
- **Root cause (as diagnosed in the entry below):** duplicate DOM id - the checkbox and the 3D container BOTH carried `id="evo-3d"`, so `getElementById` at the build/disable sites resolved the `<input>`; `init3dFrames` appended its WebGL canvas into a checkbox, the visible div kept the template placeholder, and `container._dispose3d` landed on the input while `data-v3d` sat on the div - so `route()`'s disposal sweep never disposed the player (context/rAF leak on navigation).
- **The fix (evolution.js +8/-2, no view3d.js change):** the CHECKBOX was renamed to `evo-3d-toggle`, keeping the container as `evo-3d`. Deliberate deviation from the diagnose-then-rename-the-container wording, and justified on record: an existing source pin (`tests/test_gui_brief_authoring.py:867`) pins the container markup as `id="evo-3d" data-v3d`; renaming the container would have forced edits to a green test, while renaming the checkbox achieves the identical unique-id fix with a smaller diff and zero pin churn. `build3d`/`disable3d` now genuinely resolve the `data-v3d` div (the marker element IS the player/disposal node, so the sweep disposes the real scene); the box state is coherent (starts unchecked matching the renderer, `disable3d` unchecks it again and restores the placeholder to the container); both directions of the improvements-only rule are untouched (`mode==="all"` forces 3D off; `enable3d()` forces `mode="best"`); the placeholder remains the genuine off-state text on the container only. `init3d`'s two other callers (`app.js` run-detail + 3D page) verified untouched.
- **Regression pin (new file `tests/test_gui_evolution_3d_toggle.py`, 4 tests):** source pins chosen over a node import because `evolution.js` is a browser ES module needing `document`/`fetch`/`CSS.escape` with no DOM shim in this env (the repo already pins evolution wiring this way). Asserts the two ids differ + exactly one `data-v3d` tag on the container; the player node is the marked node; the container id is never read as a checkbox and vice versa; box starts unchecked, placeholder appears exactly twice (template + restore), both rule directions present. **Negative control verified:** reverting only the checkbox id fails 3 of 4 tests.
- **Verification (pasted by the lane):** new test 4/4 (junit errors=0 failures=0) + the full GUI trio `test_gui.py`/`test_gui_brief_authoring.py`/`test_gui_integration_phases.py` 107/0/0/0 untouched + `node --check` evolution.js and view3d.js green + `compileall hornlab_search/gui/` green.
- **Residual eyes-on item (WebGL cannot render headlessly):** open `#/run/<id>/evolution`, tick 3D -> canvas visible inside the bordered box with the note "N improvement frames in 3D...", untick -> placeholder restored + box unchecked, switch to "every candidate" -> 3D turns off with its disclosure, navigate away/back a few times -> no rAF/WebGL growth. The pins prove the canvas lands in the right node and the placeholder cycles; three.js painting itself remains the owner's visual confirm.
- **Docs carried in this commit:** the plan entry below still described the checkbox as `evo-3d` (true at diagnosis time); this entry is now the record of the landed state.

## 2026-10-25 (evening) - PLAN LANDED (no code): unified typologies / parameter single-source-of-truth + GUI param descriptions + typology sandbox; branch `unified-typologies` opens from here

- **Owner ask:** hover descriptions of every parameter on the Run page AND the Typologies page; a clickable per-typology sandbox with manually draggable knobs showing the H/V wall section plus 3D; the parameter name beside each slider; editable min/max on both sides of each slider, saved to the place those bounds actually live; and one findable source of truth joining typology -> design -> formula -> parameter -> min/max -> design characteristic -> the implementing code. Also: fix the dead 3D toggle on the search time-lapse page.
- **Reference-repo research done first (owner-directed):** `m3gnus/waveguide-generator` (full architecture read) and `JWSound/boundary-lab` (public; full model read). Decisive finding: **Boundary Lab has no typology system and no parameter schema at all** - horn geometry is an opaque Ath `.cfg` text blob or an untyped `dict[str, JsonValue]`, its host GUI does no schema introspection, and its only parameter table is hand-coded inside one example plugin - so BL is a cautionary reference, not a model. **waveguide-generator is the model**: a typed schema plus one flat `families:[...]`-gated parameter registry, a committed GENERATED parameter catalog (`parameter-catalog.v1.json`, 176 params) with a `--check` staleness gate, and a published `validation_authority` note distinguishing editor bounds from hard solver validity. Two WG patterns are explicitly NOT adopted: its 689-line hand-written parameter literal and its untested hand-maintained markdown tables (both drift sources in its own tree).
- **Architecture decision (recorded at senior level, approved):** ANNOTATE the existing authorities, do not re-home them. Hard limits stay in `design/families.py::KeySpec`; defaults + generator vocabulary stay in `design/generators/registry.py`; grid/rows knob sets stay in `grid.py`; seeds/bounds stay in `examples/typologies/*.yaml`; catalog identity stays in `examples/catalog.yaml`. New `hornlab_search/design/params/` supplies only the missing JOIN plus prose (label/unit/summary/detail/formula/symbol ref/doc ref), keyed on config `name` with the catalog entry as an overlay, disambiguating overloaded names (`n`, `q`, `a_deg`, `T`, `stop_deg` vs `max_wall_deg`) by family/kind context. **No authored number anywhere** - every numeric value is read from an authority at build time (`AGENTS.md` line 29). A generated `gui/static/param-catalog.v1.json` is the contract for both Python and the vanilla-JS GUI (served by the existing static handler = zero frozen-payload changes), and a FAIL-not-warn drift gate keeps it honest in both directions.
- **Verified inputs for it:** 36 catalog ids; 4 mesher families; 11 generator types; ~115 distinct knob names to author; the implemented bounds precedence chain has **13 silent override points** (driver pins, S1a clamps, the biradial `widened_to_closure`, midpoint fills, DEFAULT_KNOBS fallbacks) - so "effective bounds for a run" is not "bounds in the source YAML", and the catalog must label that honestly rather than present source bounds as final.
- **3D toggle defect DIAGNOSED (not yet fixed):** duplicate DOM id - `evolution.js:45` gives the checkbox `id="evo-3d"` and `:53` gives the canvas container the SAME id, so `getElementById` at `:186`/`:242` returns the `<input>`; the WebGL canvas is built into the checkbox while the visible div keeps the template placeholder `3D off - flip the 3D toggle above.` Same collision puts `_dispose3d` on the input while `data-v3d` is on the div, so `route()`'s disposal sweep never disposes it (context/rAF leak on navigation). Small isolated fix, queued as the first lane on the new branch.
- **Sandbox feasibility risk recorded:** arbitrary-knob geometry does not exist today (the evolution 3D replays STORED meshes). Planned route is an on-demand preview that materializes params and uses the mesher's own `build_point_grid` (private use already sanctioned with pin + guard test per closed issue #9), with `available:false` + reason for families that have no preview path - ahead of any sandbox UI work.
- **Open ruling carried (not blocking):** `exponent` has two conflicting default claims - prose `12_RESEARCH_BASIS.md:158` says 2.0, `registry.DEFAULT_KNOBS["mouth_exponent"]` and the shipped configs use 4.0. Resolved FOR TOOLTIPS by stating each typology's actual seed value instead of a global default; the doc/code mismatch itself stays recorded, unsilenced.
- **Docs-only push:** `docs/NEXT_DEV_PRIORITIES.md` gains **P9** (the full proposal, scope, precedence chain, drift-gate design, W8 dependency, open decisions); `docs/ISSUES.md` gains the defect + three owner asks + verified inputs; `NOTES_FOR_SENIOR.md` gains the contract-gap block with five questions for the senior/owner. **No code, config, bound, or frozen file touched by the plan itself.**

## 2026-10-25 (evening) - 3D RENDER SETTINGS LANDED: owner screenshot → fixer lane; per-view controls + global persistence (presets solve the wireframe-drown + flat-lighting findings)

- **Owner screenshot (observed directly, the rollback-rows horn on the dark theme):** the always-on near-white ridgeline wireframe at rows-mesh density (~10k tris) read as a noisy wireframe screen over a washed-out pale matte — no tonal depth in the concave interior, no user control (only the persisted shadow toggle).
- **fixer lane (view3d.js + brief_authoring pins):** a persisted `hl-v3d-render` preference ({surface: satin|matte|metallic|studio, ridges: on|thin|off, light: 0.5–2.0}); pure exported `normalizeRenderPrefs` (defaults/corrupt-J/out-of-range honest); `RENDER_PRESETS` + shared `applyRenderLook` (in-place material + ridge opacity/removal + directional-light multiplier; hemi ambient-relative) and `applyRenderControls` — a clickable overlay chip (labeled selects + range + numeric ×-readout; pointer-events:auto, deliberately unlike the pointer-events:none enclosure chip) on BOTH `init3d` and `init3dFrames`; changes apply immediately AND persist globally ("swap them easily in the 3D view or globally"); DEFAULTS are byte-for-byte today's look (satin 0.28 ridges / 1.15-0.35-0.85 rig) so existing captures and pins hold; no new raw hex (existing constants named; matte = 0xdfe4e8 ×0.88); disposal untouched (`wireGeo/wireMat` disposed whether attached or removed); app.js unedited (the shadow-toggle re-init flows re-create the chip with persisted prefs — verified read-only).
- **Verification:** brief_authoring 21/21 (+2: prefs-normalize node tests + wiring pin), node --check view3d.js + compileall clean; WebGL runtime paths source-pinned honestly (headless cannot render; chip interaction + cross-surface persistence in a live page remain the owner's eyes-on items).

## 2026-10-25 (evening) - S1a DRIVER PASS LANDED: brief family per driver class + closure-aware biradial + salmon reseeds + C4 catalog (oracle-decided, owner-directed); suite 1509/0/0/0; dry-run matrix 15/15 green

- **Owner complaint → diagnosis (measured):** "half the new typologies won't even run" — the owner's user briefs (17.2–17.4 mm drivers, 500–680×390–500×300–600 envelopes) REFUSED `biradial_keele`'s seeded contour ("rm=195 cannot close tan(40.5 deg)·210 from r0=17.2, needs ≥197" — profiles.py closure guard) and the salmon demos overshoot/mesh-fail (x_signed 0.2201 / 14,414 tris; ripple12 5,358 dofs > 5,000). My 25-cell march probe + corner analysis re-anchored everything; the earlier full 2^k probe timed out (rows marches are heavy) — replaced by the oracle's targeted corners probe.
- **Oracle decision pass (owner-directed):** the complete final design preserved VERBATIM at `docs/research/typologies/S1A_DRIVER_PASS_ORACLE_FINAL_2026-10-25.md` (provenance header + the owner's over-constraint remark on record); pointer sections added to 12_RESEARCH_BASIS §16.9 (append-only) + NOTES_FOR_SENIOR + INDEX/CODE_MAP.
- **The driver story (brief-driven, uniform):** shipped brief family `{hifi_90x60, organic_rollback, lecleach_rollback} × {1in, 14in, 2in}` — every brief f0-carrying + objective v3 with each f0's honest derivation stated in-header (hifi = the K-law break of the binding V axis at its envelope → 1450/1450/1000; organic = the measured 1.8× rollback-extent rule → 1900/1800/1550; lecleach = the dof-honest full-ring floor → 1200/1200/1200); custom = copy the nearest family brief (verified 12.7→25.4 mm; the biradial derivation even handles a 50 mm custom via the flagged widened_to_closure). WP2 pins the throat from the brief; no config clones; no catalog driver ties (all measured multi-driver).
- **config.py derivation repair (2 hunks, fixer-applied verbatim + 4 tree-faithful adaptations — all dated, none weakening):** (1) the derived mouth caps at envelope − 2×wall_thickness (registry counts the freestanding shell; an at-envelope derived seed graded over by exactly that margin — measured); (2) the biradial branch: derived a = the patent's own 0.9×half-coverage rule; rm = max(K-law d/2, r0 + tan(a)·L) with the ONE owner-directed exception to the clamp-only contract (bound hi widens to exactly the closure line when the driver demands it, flagged widened_to_closure in the derivation note + pinned by test). An f0 brief can no longer produce an un-closeable biradial seed.
- **Config reseeds (the measured recipes):** biradial_keele L 210→195 (one seed closes at every driver class) + rm bounds widened for the 2in class (h 197→210, v 146→230); salmon_x_signed stop 170→150 + x_amp −0.25→−0.15 (the cardinal rows crossed the 180° cap-area asymptote at the shipped seed; −0.25 at 150 also meshes defectively — x=0-plane triangles); salmon_ripple12 stop 170→150 (5,358→2,567 derived dofs); lecleach_asym_odd eps 0.25→0.20 (the full-ring curl self-approach window at r0 ≥ 17.2; a thinner wall does NOT fix it) + its brief_file → the NEW lecleach_rollback_1in; qtw unchanged (green everywhere).
- **C4 catalog LANDED:** the five entries (incl. lecleach_asym_odd `symmetry: full`; the campaign test tuple + catalog membership tests extended) — closes R9-audit P3; the five leave the Compose uncatalogued sole-pick rule (the rule itself stays for future configs; app.js untouched).
- **My 4-test triage (the driver-pass suite run first exposed them):** ALL four were the salmon family's briefs becoming derivation-active at load: `salmon_elliptical`'s derived seed graded 4.2% over its depth envelope (fixed properly — given the same measured stop-150 reseed as its siblings; derived invariant ratio 1.0016 ✓) and three tests pinned premises written in the pre-f0 world (the saddle's tuned datasheet seed/invariant + the self-approach fixture): fixed by making those fixture briefs derivation-inert (f0/objective stripped, dated comments, every original assertion + tolerance unchanged — never weakened); the derived layer is pinned separately in `tests/test_s1a_driver_briefs.py`. Disclosure on record: under f0-1900 the saddle/x_shape DERIVED seeds drift their report-only invariant ratios (1.129/1.3025 — the fc clamp + stop-harmonic interplay); the tuned ratios (0.9962) govern in the derivation-inert world; the seed-derivation card shows the clamps.
- **Verification:** offline suite **1509/0/0/0** (`runs/driver_pass/suite2.xml`; fixer-side 126/0/0 + brief_authoring 21) + node --check ×6 + compileall + **BYTE-CHECK 29/29** (24 original + 5 dry-run checks covering 15 cells) + the **15× gmsh dry-run matrix all under the 5,000 screen cap** (biradial 1846/2023/2532 · qtw 1616/1764/1990 · x_signed 1792/1887/2504 · ripple 2567/2751/3636 · lecleach 4190/4152/4141 — matches the oracle's measured matrix; evidence addendum appended).
- **Solve-side:** the OWNER launched their own screen campaign (pid 14484, `--brief user/7040use.yaml --families salmon_elliptical,salmon_x_signed,salmon_saddle,salmon_ripple12,lecleach_iwata_ar`) against the repaired tree — the one-GPU rule held (gpu-clean refused while the owner's lock is held); the queued GPU re-smokes are superseded by the campaign's own run evidence + deferred behind it; J values are NOT comparable with the old smoke matrix (new f0/v3 record groups).
- **W8 priority added** (owner-directed): the per-typology search-box audit — the owner's perturbed_osse_hv run showed the config `L_mm` box (90–140) binding 4/6 best designs while the brief allowed 600 mm depth; guide §4 explains the three-layer size-limit model plainly; the audit + widening table is owner-gated per config.

## 2026-10-25 (local, later) - TYPOLOGY PASS COMPLETED: orphaned WIP landed, GPU smoke matrix ran, Phase-D baseline settings + R9 audit + GUI hybrid seeds LANDED (5 lanes + orchestrator)

- **S2 ORPHANED WIP landed first (305b87b, docs-only):** the prior pass left `12_RESEARCH_BASIS.md` §16.7/§16.8 + the INDEX line uncommitted; validated (append-only placement between the committed §16.6 sources and the git trailer; honest [verified]/[open]/do-not-cite labels; consistent with the three committed Phase-A dossiers - no contradiction; prior author's voice preserved) and committed. Suite on that tree 1448/0/0/0 - later reconciled EXACTLY: the count difference was the five lanes' unlanded tests (3+8+2 = +13 -> 1461 = the historic count, zero failures).
- **INVENTORY (exp-1):** the catalog is 31 entries; the handoff's "32" was wrong and matters: NONE of the five new configs (biradial_keele / qtw_waveguide / lecleach_asym_odd / salmon_x_signed / salmon_ripple12) is catalogued - all five self-declare "catalog lands in the C4 batch" (C4 STILL PENDING backend-side; the catalog.yaml prose mentioning biradial/QTW has no entries - R9-audit PROPOSAL P3). The expansion's landed code: biradial + qtw_waveguide generator kinds + lecleach_asym rows + signed g_x_amp + even-lobe mouth ripple + span full, all test-pinned (biradial 96-line test file, qtw, grid_full_ring 12 tests incl. 2 real-CPU-adapter probes; the rows kinds in the rows/full-ring suites).
- **GPU SMOKE MATRIX (M4 pattern) - the five configs' first GPU evidence:** one `run --mode screen` seed smoke each, fresh cache-dir per job, gpu-clean before/after every job, one-at-a-time (CLI lock; no force), external 2 s VRAM sampler to csv, cmd /c log capture: (1) biradial_keele GREEN - J 22.9837, 2086 dofs, 13.1 s, VRAM 1301->2427; (2) qtw_waveguide GREEN - J 37.4656, 1616 dofs, 11.5 s, 1334->2104; (3) lecleach_asym_odd (FULL RING) GREEN - J 60.1446, 2815 dofs, 10.6 s, 1337->3147 (the S1a capability claim measured on the GPU; the ring bills ~4x the quarter as predicted and still fits); (4) salmon_x_signed RUN FAILED mesh_too_large at the SEED - 14,414 tris > 11,275 effective limit + the wall-clearance warning (the corner-in demo seed); (5) salmon_ripple12 RUN FAILED mesh_too_large - 5358 dofs > 5000 screen cap for quadrants '14' (12 lobe / half span seed). The machinery is healthy; rows 4-5 are HONEST CAP/BSEED findings -> PROPOSALS (reseed or verify-tier treatment), never silent fixes. Full table + findings: docs/evidence/TYPOLOGY_SMOKE_MATRIX_2026-10-25.md; bytecheck tools/evidence_bytecheck_typology_smoke.py **24/24 PASS** (exact tree re-derivation: run.json/ndjson/config yaml/log/VRAM csv incl. the failure rows; negative control verified failing) - exit-code discipline per the m4/m5b/m6 template (exit 0 here, 1 on mismatch).
- **OFFLINE TEST GAP closed (fix-4, new file tests/test_design_generators_grid_signed_and_ripple_configs.py, 8/8 offline fast):** salmon_x_signed + salmon_ripple12 config-load/brief-resolution/seed-march/envelope/graded-penalty pins (the only two new configs no test loaded). FINDING pinned honestly: salmon_x_signed's demo seed overshoots the brief envelope (z-span 332.47 vs 260+15 = 275 mm; overshoot 0.2201) - matches the smoke row; ripple12 is envelope-true with the exact 4.0 samples-per-lobe bar.
- **PHASE-D BASELINE SETTINGS (owner ask):** docs/TYPOLOGY_BASELINE_SETTINGS_2026-10-25.md - per-config knobs/bounds/seed-rationale/recommended-treatment for the five new configs (all shipped defaults verified sensible per dossier), the measured tier recipe (grids/caps/budget_for_tier/VRAM guidance), the 2-inch template brief section, the cross-cutting measured findings table (rear_res_factor 1.5 AXI measured-inside-bars PROPOSAL, balloon 512->1024 owner-gated, band_split gate FAILED stays opt-in, source_motion normal, weights, mounting dof multipliers + never-rank rule, M5 screen reality), the existing-configs audit paragraph (defaults stay; §13.6 direction intact), and the OBJECTIVE V3 DECISION CAPSULE (v3 = opt-in today; landed surfaces + test coverage; owner decides default status - NON-flipped).
- **R9 AUDIT ("make sure all typologies make sense"):** docs/research/typologies/R9_AUDIT_2026-10-25.md - all 31 catalog entries + 5 uncatalogued walked (claim -> source -> status): 15 PASS-published, 18 PASS-labeled, 3 UTILITY; the do-not-cite/STOP ledger restated; FIVE owner-gated PROPOSALS surfaced (lecleach_iwata_ar name decision carried from §13.4 #2; biradial_keele year-suffix option; C4 prose-vs-entries; §13.4 label hygiene still live (osse_baseline 10-vs-9 knobs, throat_adapter symmetry, organic-grouped axisymmetric lecleach pair); salmon_x_shape/x_signed same-family seed-sign pairing documented) - NO rename/label edit made by the audit.
- **GUI HYBRID SEEDS (designer lane des-1 + fixer reader fix-3, owner §4d):** /api/configs gains additive `generator_block` + `seed_params` (verbatim passthrough; absent = absent; server returns list_configs verbatim); Compose step 1 captions real mixes from the generator block SHAPE (splice parents / blend section / different per-plane laws; orchestrator copy-fix: grid-rows configs caption "rows — {types}" - a rows kind is one construction, not a hybrid; empty-rows -> "rows — grid"); a per-pick SEED panel previews the config's own seed_params (8-row cap + "+N more" honesty; display-only); the payload-fidelity rule PINNED (compose POST bodies byte-identical; test_compose_hybrid_and_seed_views_are_wired asserts the exact currentJob field set); uncatalogued sole-pick rule byte-identical (the five new configs ride it).
- **GUI wiring verified already-landed (4b42862):** objective v3 select/option, the f0 "Scoring floor" KPI, the "J v3" generic badge, compare's mixed-key warn + the never-rank-across-mountings line - all live; the five new configs selectable in Compose (uncatalogued sole-pick; catalogued workflow when C4 lands).
- **VERIFICATION (final tree):** offline suite **1461/0/0/0** (junitxml runs/typology_complete/suite.xml; the two smoke failures are RUN failures inside the GPU matrix, not suite tests) + the fix-4 file 8/8 + brief_authoring 19 + integration_phases 50 by lanes + node --check all six static JS + compileall hornlab_search/gui/ + BYTE-CHECK 24/24. GPU discipline: no solve with another job's lock held (the matrix started only after the other lane's julia exited + the lock freed).
- **SCOPE/hygiene:** fix-3 = gui/data.py + integration tests; des-1 = app.js + brief_authoring; fix-4/fix-5 = their own new files; docs = orchestrator. Exact-path staging per-commit; cross-lane files never staged by another lane. GATES unchanged: G5 (P6b), WP13 (owner-deferred), W7 (backend), C4 picker (backend pending).

## 2026-10-25 (local, later) - GUI: objective v3 + G6 mounting surfaces LANDED (re-grounded @ abcbebf; two disjoint fixer lanes + orchestrator reconciliation)

- **Grounding:** plan doc `GUI_INTEGRATION_PLAN_2026-10-25.md` was written at M5 and its WP table is stale; everything re-anchored against the HEAD tree (function names, not line numbers). Baseline FIRST: the five GUI test files ran 107/0/0/0 (junitxml `runs/gui_baseline/suite.xml`) - the S1a landing (abcbebf) did not regress the GUI suite. Live probe BEFORE building: both WP12 enclosure runs (`20261025T130119Z-screen-39f561`, `20261025T125911Z-screen-77e443`) already carry `solve_group.mounting` (the normalized block: type enclosure, depth 250, edge 18, margins 25 all round) - the G6 badge data was live before any edit; `run_detail.target` f0 passthrough needed no reader change (config target rides verbatim).
- **fix-1 views lane (app.js + tests/test_gui_brief_authoring.py):** (1) Objective select (`brf-obj`, now rendered by the pure exported `objectiveVersionOptionsHtml`) exposes exactly 1|2|3 with v3 labeled "3 - scoring floor f0 (cov + dislope score only f >= f0)"; hint updated; save path + newBriefDraft default (v1) unchanged; Compose wizard inherits (it mounts the same editor - single select in the file); solve_group's `J v${n}` badge was already generic, verified rendering "J v3" with no edit. (2) Run-detail KPI `f0KpiHtml(t)`: "Scoring floor" (+ mono `f>=` suffix, value = `fmtHz(f0)`, tooltip names target.f0_hz and the v3 mask) spliced right after Band, rendered ONLY when target.f0_hz is present. (3) Compare `mountingRankWarnHtml(mixed)`: under the generic mixed-keys banner, mounting differences get the explicit warn "mounting differs - a different objective landscape (J improves under the enclosure); never rank across mountings" (the owner-measured M6 finding; the generic banner already listed `mounting` as a mixed key - the fingerprint vocabulary needed no edit). (4) `seedDerivationHtml(d.feasibility)`: the S1a brief-driven seed card on run detail (after the restart schedule): the K-law rule code + the clamp-only caption + below-f0 solved-freq counts "(masked under v3)" + per-knob table (derived mm / applied / "clamped to bound" warn pill or "seeded"); absent `feasibility` renders literally nothing.
- **fix-2 reader/3D lane (gui/data.py + view3d.js + tests/test_gui_integration_phases.py):** `run_detail` gains additive `feasibility` (verbatim passthrough of the committed config.yaml block; absent = absent); `mesh_surface` gains additive `mounting` (the design's `mesh_meta.json["mounting"]` with mesher + normalized sub-blocks, absent on every free run); `view3d.js::init3d` draws the enclosure outline ONLY when `meshData.mounting` is present: a dashed outline box sized exactly from the mirrored mesh's own bounding box (never invented enclosure geometry) in the `--rule` theme token + a themed overlay chip (position-absolute over the canvas - the orchestrator's reconcile fix: both host containers are fixed-height/overflow-hidden, so the lane's after-canvas caption would have been clipped) carrying "enclosure outline = the solved mesh's extent" + the real mounting values read defensively (normalized block first, mesher keys as fallback); `mountEdges`/`mountLineMat` disposed in `container._dispose3d`; no `data-v3d` marker on the caption. Both app.js init3d call sites verified (read-only) to pass the /api/mesh payload through, and `server.py` returns `mesh_surface` verbatim - no caller change.
- **S1a compat refusal UX (verified, no change needed):** the campaign reader already carries `skipped`/`skip_reason` per entry (gui/data.py) and the Typologies view renders `is_compatible` reasons per brief; the new axisymmetric-refuses-hv reason (campaign.py 2026-10-25 wording) now pinned by a fixture test that the reader returns it verbatim; the Compose wizard's preview hint already states "entries that don't fit the brief are skipped per-entry with the reason printed".
- **Still NOT built (gates unchanged):** G5 bake-off (P6b owner gate), WP13 (owner-deferred), W7 balloon density (backend-gated), C4 catalog picker changes (catalog entries pending backend-side; GROUP_LABEL coverage to re-check when they land), P8d (the other lane's item, coordinated not claimed).
- **Verification (jointly, post-reconciliation):** five GUI test files **114/0/0/0** (junitxml `runs/gui_s1a_g6/suite.xml`; 107 baseline + 7 new = brief_authoring 17, integration_phases 45, test_gui 36, balloon 8, mesh_quadrants 6) + `node --check` all five static JS files + `compileall hornlab_search/gui/` - all green, pasted by the lanes and re-run by the orchestrator.
- **Cross-lane hygiene:** the shared tree also carries the backend stream's live docs WIP (`docs/INDEX.md` + `docs/plan/12_RESEARCH_BASIS.md` §16.7/§16.8 librarian record) - read-only here, NOT staged, NOT committed by this pass; `examples/briefs/user/` stays untracked (owner decides keep-with-sample vs .gitignore). Per-file staging discipline held throughout.
- **Plan-doc record:** dated §14 addendum appended to `GUI_INTEGRATION_PLAN_2026-10-25.md` - WP12/14/16/17 DONE, W6 landed, G5/G6 gates/status, the §3.8 `source_plug` naming RESOLVED (GUI contract = the `source_profile*` diagnostics; no `source_plug` field needed), the §3.11 brief-editor mounting scaffolding superseded by the full-schema briefs editor.

## 2026-10-25 (typology-expansion + scoring full-repair pass - owner-directed; solo-orchestrator round, no subagents after the deepseek provider outage)

- **Gate (owner picks, recorded in chat):** build biradial + Tritonia/CORE + QTW + mouth ripples + the asymmetric Le Clec'h; keep the `iwata_ar` NAME (labeled reconstruction); FULL scoring/seed repair; all 7 config-only v2s (the batch lands next round - 2 of them = the 2-inch variants need the new `axi_2in_large` brief, shipped here); the X direction = the AudioHorn reading RESEARCHED fully (dossier) with the build decision parked (P8).
- **Research waves (all dossiers in docs/research/typologies/, append-only, indexed):** BIRADIAL_IWATA_300 (US4308932A = the Keele/JBL primary: two-section series horn, exponential connector + ~23:1 slot + power-series walls; reference case checked; Iwata-300 = R9-STOP datasource; Crowe ES = self-published; premise correction: Crowe sells NO Iwata kits); SHAPE_DISCOVERY_SWEEP (70+ shapes; SIBINIC proven DEAD - the real Batik asymmetric formulas = Tritonia + ATH CORE; QTW white paper read); SALMON_X_HORN_EXPANSION (Salmon JASA 1946 primaries + Freehafer + Olson-codifier; the three X readings; P-M4-2 sharpened: the salmon mod stop window (120,240) is DEFINED BUT NEVER ENFORCED); MOUTH_RIPPLE_SERRATION (the owner's "pleats": segmented roundover facets, not documented corrugation; the microwave corrugated-horn transfer + our ripple formula) - the latter two recovered by the orchestrator directly (the librarian lane errored on the outage); X_SHAPE_AUDIOHORN (9 maker pages: family constants W/H 1.60-1.65 etc. + the diagonal claim + the measurement-hygiene warnings); obs-1 image analysis of the TwinRay/Opus renders (the planar rim frame + the smooth pucker approach + the figure-8 rosette + the bullet squircle).
- **12_RESEARCH_BASIS.md: new dated append-only sections (nothing settled edited):** 13.1-13.6 (the four lanes' consolidated records + the R9 audit of every typology: the verified core PASSES; R9-J rerun green; the defects list: the splice C1 overclaim - FIXED below; six stale "Le Cleac'h disabled" sites - corrected; the salmon_axisym knob trap - flagged) + **13.7** (the owner-provided azimuthal-modulation/segmentizing synthesis VERIFIED at source: alpha(theta) = 48.5-7cos^5(2theta)-16sin^12(theta) + the seg-horn eqs 1-4 verbatim + the corrections: Tritonia's base is OS-SE not R-OSSE, the law is the author's "purely empirical" recipe) + **13.8** (the owner-directed diagnosis: WHY the puckered shapes never appeared in their passes: the objective could not reward the class (the below-f0 dominance 61-87% + dislope 30-42% + no diagonal term), the seeds/bounds sat at zero, no layering required - one-run CMA-ES is the model; the staged genes = an optional refinement). Sections 14-16 in the file = the parallel lane's own owner-directed records (corner horns / BL Deploy / typology map) - reconciled read-only, not touched by this commit's other work, disclosed here.
- **C1 - NEW GENERATOR TYPES (owner-approved):** `biradial` (US4308932A power-series contour per plane, r = r0 + tan(a)z + c z^n, c solved to rm; claim-14 n range 2-8 enforced; the documented H-plane inward-turn case REFUSED with the swept-frame message; the K-rule helper `biradial_mouth_mm` with the patent's own 25,000 constant next to the repo's KEELE_K 25,400 - both quoted, never swapped); `qtw_waveguide` (the Hughes/Peavey arc rule VERBATIM: wall parallel at the throat, arc turn = a_deg = half the dispersion, straight bell at the same angle, rm DERIVED; "per the published rule, not a claimed replica" - the quadratic coefficients are unpublished). Configs: typologies/biradial_keele.yaml + qtw_waveguide.yaml (brief hifi_90x60_1in; honest labels + "catalog lands in C4").
- **SPLICE FIX (R9-audit finding):** `_SPLICE_MATCH_TOL_DEG` 2.0 -> 0.5: the shipped configs/labels claim C1 with a < 0.5 deg joint bar, but the old 2-deg direct band shipped C0 kinks up to 1.876 deg (measured on the shipped seed at zs_frac 0.425-0.575). Now: |dtheta| <= 0.5 = direct; else the C1 Hermite bridge (P1 holds on the whole shipped range; the exact cone-cone direct case + the branch-agnostic P1 test added).
- **C2 - GRID ROWS (owner-approved; full-360 CAPABILITY PROVEN on the real CPU mesher):** signed `g_x_amp` in [-0.4, 0.4] (+ = diagonal-out/literal X, - = corner-in; magnitude cap unchanged; x_fc applies when amp != 0); NEW rows kind `lecleach_asym` (the verified Fourcade march + the odd-cosine single-sided asymmetry r *= 1 + eps_m w(s) cos(phi); eps forces the FULL ring; the throat stays exact; validator + label ROWS_ASYM_LABEL); the even-lobe MOUTH RIPPLE (`g_ripple_lobes` 6-24 even / `g_ripple_amp_mm` <= 6 constant-mm ridge height delivered at each row's widest station / `g_ripple_start` 0.7-0.95 window; a >= 4 samples-per-lobe honest-resolution guard); NEW span `full` (phi 0..360 endpoint-exclusive, n_phi >= 25, quadrants '1234', no mirror planes - the mesher's native closed/full mode; mesh/grid_build accepts it + refuses full+encyclopedia?? (full+enclosure refused this pass) + the mismatch message updated; the bbox guard unchanged - an extent-based check). Configs: lecleach_asym_odd.yaml / salmon_x_signed.yaml / salmon_ripple12.yaml (all labeled + graded-penalty enabled). Tests: test_design_generators_grid_full_ring.py 12/12 incl. the two real-adapter probes.
- **S1a - THE SCORING/SEED FULL REPAIR (owner-approved; the 75x35 complaint root cause):** (1) `Target.f0_hz` (additive, validated in (0, band_hi]; absent = band_lo = byte-for-byte); (2) objective **v3** (`objective_v3` in scalar_v2.py: cov JOINs WP4's freq_weight_vector + BOTH cov and dislope score only f >= f0 - the below-f0 mask; v1/v2 untouched; the same key set; band-based n_nan contract kept; never-raise kept; _score dispatch + the objective-block validator accepts 3); (3) the K-law FEASIBILITY PREFLIGHT in load_config (`raw["feasibility"]`: required vs envelope mouth per axis, the HELD coverage at the envelope's limit, the per-mode below-f0 freq counts, derivable only when target.f0_hz present; absent-f0 briefs = byte-for-byte; the embedded-brief resume path NEVER re-derives); (4) the BRIEF-DERIVED SEED/BOUNDS (clamped to the envelope AND to the config's own bounds; every clamp flagged as clamped_to_bound; widening never automatic): rm-families (rm = d/2), OSSE (a_deg = coverage/2), QTW (a_deg = coverage/2 per the arc rule), the rows fc's via the verified W*fc ~ 1.88e5 invariant (per-axis for elliptical; geometric-mean for single-fc kinds) + iwata_ar's g_ar_m = W/H (the AR law's exact interpretation). Formula/native families + profile-less configs: honest no-rule notes (derivation lands with the baseline-settings pass). Tests: test_brief_derivation.py 9/9.
- **Other fixes landed this round (the R9-audit items):** campaign `is_compatible` now REFUSES hv entries under an axisymmetric brief (the 7040 finding: 458x240 mm mouths under a symmetric target; the two pinned tests updated with the dated rationale); graded penalty enabled on the six organic configs; the stale "Le Cleac'h disabled" lines corrected (catalog:6 + spherical_salmon.yaml:7); the registry docstring's stop_deg/max_wall_deg mismatch fixed; the new 2-inch baseline brief examples/briefs/axi_2in_large.yaml (K-law-consistent, f0_hz 1000 + objective v3 - the Phase D template).
- **Owner-directed records saved (no code):** the "puckered shapes never showed up" diagnosis (13.8) + P8 in NEXT_DEV_PRIORITIES (P8a the pucker-hunting demo campaign / P8b the diagonal-consistency term DECISION PENDING / P8c the Tritonia-law rows kind + segmentizing genes / P8d the GUI surfacing) + NOTES_FOR_SENIOR (incl. the session's writing-hygiene lesson: two chat-prose pastes into file tails + one section header eaten twice by anchored edits - all caught/repaired same-turn; lesson recorded).
- **Infra incident, recorded:** the deepseek provider died for every NEW subagent session mid-pass (5 launches with empty "Session error" results); the fallback chain in .opencode/oh-my-opencode-slim.json flipped to ollama-cloud primary (BINDS AT THE NEXT OPENCODE RESTART; not verified live - the owner should restart opencode); the ollama-cloud lanes (designer/oracle/observer) ran HEALTHY all day; the affected research lanes were recovered by direct orchestrator fetches. Errored sessions are not resumable (board).
- **Suite: 1461/0/0/0** (junitxml runs/s1a_suite/suite_final.xml; up from 1372: +89 = the new typology/objective/derivation/compatibility tests + the two 2 GUI commits' tests by the parallel lane). NOT DONE (next handoff): the catalog entry block for the 5 new configs (C4), the 2-inch v2 variants + salmon_saddle_v2 + the 3 frozen-plan-named hybrids (rides C4 + the landed brief), the Tritonia-law rows kind (C3/P8c, now fully specified by 13.7), the GPU smoke matrix (M4 pattern), the Phase D baseline tables, the GUI hybridization (P8d), the evidence/bytecheck scripts (m4/m5b template), Oracle review of the new physics claims.
- **Parallel-lane note:** the GUI kill-run/stop/resume commits (03529ff, 4bb7da4) are the other lane's work (not staged here; their docs entries stay). Shared-index hygiene held: per-file staging only.

## 2026-10-25 (local, later) - GUI: KILL RUN control for externally-started runs (owner's screenshot markers) + always-visible idle pill

- **Owner screenshot markers (read via @observer) redefined the ask:** the running job holding the GPU was STARTED FROM A TERMINAL (external — the sidebar pill "external GPU run · pid 192…" was already rendering; the GUI showed no button for it by the old "only stops its own jobs" rule). Marker A = at that pill in the sidebar; marker B = on the Home dashboard's RUNNING card action row (right of the Open run/Status buttons). Owner: "code it yourself" — implemented directly by the orchestrator, no designer lane.
- **Kill run control (external state):** in the sidebar pill, the Status card AND the Home running card, the external state now renders a two-step armed danger **`■ Kill run`** → `POST /api/stop-current` → `jobs.stop_external()`: kills exactly the pid recorded in OUR gpu lock file (+ its child tree — that lock is this repo's own, written by whoever is using our GPU; never an arbitrary pid), then the same gpu-clean pass cancel() uses. Server guard: refuses while a GUI-started GPU job is running (that is the Stop path — the two never race) and refuses killing the GUI's own process.
- **Pill is now ALWAYS visible** (owner report "I don't see it"): the idle state renders a muted "no run in progress" indicator instead of an empty holder — the toolbar control is a visible location at all times. External = `■ Kill run`; stopped search + idle GPU = `▶ Resume search`; GUI GPU job = `■ Stop`.
- **Cross-checks:** the branch-order bug that crashed `toolbarPillHtml(null)` (idle evaluated after the job read) is fixed and now node-tested (`toolbarPillHtml(null)` → the honest idle face); the old "the GUI only stops its own jobs" copy was REMOVED everywhere and its test pins updated to the kill semantics (one invented test sentence was caught by the test suite itself and replaced with the app.js's real copy; two indentation slips in the test file caught by LSP/pytest and fixed). The interim footer-holder guess was removed — the markers pointed at the sidebar pill AND the Home card, both of which carry the control now.
- **Verification:** 107 passed across the five GUI test files (brief_authoring 15 + integration_phases 38 + test_gui 36 + balloon 8 + mesh_quadrants 6) + node --check + compileall. Scope: gui/jobs.py (+stop_external/_kill_tree), gui/server.py (+POST /api/stop-current), gui/static/app.js, two GUI test files + docs. The parallel agent's WP12 mounting WIP untouched/unstaged.

## 2026-10-25 (local, later) - GUI: STOP + RESUME run controls LANDED (owner) — Status card + always-visible left-toolbar pill + `search --resume` GUI plumbing

- **Owner requests (chat):** "add a button somewhere that will stop the current run"; "put that button on the left hand toolbar as well... kill run, then pause and then resume run maybe." Engine reality (disclosed to owner, confirmed via a targeted question): Windows has no practical graceful pause — the honest control set is **Stop (kill process tree + gpu-clean)** and **Resume (`search --resume`, deterministic: cached rows replay at zero spend)**. Stop+Resume chosen.
- **Status-card Stop (designer lane):** the current-run card on `#/status` gains the Stop affordance with a three-state ownership rule (`stopAffordanceFor` — pure, node-tested over 12 cases): (1) GUI-started GPU job running → two-step armed danger button (`■ Stop` → `Confirm stop`, auto-disarm 5 s; no browser `confirm()` — stated pattern) firing the committed `POST /api/job/<id>/cancel`, post-action line "stop requested — the run dir records the stop…"; (2) gpu lock held by an EXTERNAL process → informational pill naming the lock pid ("run started outside the GUI (terminal) — the GUI only stops its own jobs"), never a button; (3) nothing running → nothing rendered. One-GPU-at-a-time makes "newest running GUI GPU job" unambiguous; multiple disclose it. Launch rows keep their existing cancel (retitled `Stop run`). Startup-window honesty: GUI job running but no run folder yet → minimal card with the button ("no run folder written yet") instead of a blinking-out control.
- **Toolbar pill (designer lane, app.js-only — nav injected below the links via `<div id="nav-runctl">`, desktop column and mobile top bar):** always-visible compact control driven by a dedicated 10 s poll (skipped when `document.hidden`, immediate first tick, DOMContentLoaded-timed; stateless-idempotent renders; sig-skip keeps an armed click alive; no `[data-v3d]` marker so the 3D disposal sweep ignores it): (1) running GUI GPU job → compact `■ Stop` (shared two-step arm `wireTwoStepArm` reused from Status); (2) external lock → muted pill naming the pid (no button); (3) **Resume** when idle GPU + a stopped GUI search job (status `cancelled` or failed-nonzero; `"ended (GUI restarted)"` deliberately excluded) → `▶ Resume search` firing the new resume POST behind the preview gate. Idle renders literally nothing (zero layout residue).
- **Resume plumbing (fixer lane, `gui/jobs.py` — verified against the CLI contract on disk):** the CLI's `--resume` takes a **DIRECTORY** (`metavar="DIR"` — a bare flag is refused), so the GUI `search` job kind gains an optional `resume: <run_id>` arg resolved via `_run_id` → `search --resume <abs runs/<id>>` (config optional on resume: the CLI reuses `<run>/config.yaml`, so a config edited after the stop can't poison replay unless `--allow-config-change` is explicitly passed; `budget` omitted → the run's own `cfg.search.budget`; **budget is a per-invocation NEW-eval cap, not auto-remaining** — disclosed to the owner in the contract update; `mode` omitted → CLI default `screen` which REWRITES run.json mode — the UI passes the run's recorded mode). GPU kind, one-GPU lock, gpu-busy refusal, cancel, past-jobs reload all inherited (ordinary search job). Resumable markers on disk: `run.json status` `"running"` (stale after a GUI hard-stop — no `"stopped"` value exists in the writer) / `"interrupted"`; `"finished"` → deliberate budget top-ups only; `"aborted"` retryable.
- **Honesty engineering:** Resume id sourcing from the stopped job's own `log_tail` (`runs/<id>` lines) validated against `/api/runs` summaries (exists + `budget == null || n < budget` — an exhausted run is finished; top-ups stay an owner action, never a pill side-effect); every resume runs `POST /api/preview` FIRST (server-side validation, zero side effects) and the confirm click is **blocked** if the previewed argv lacks `--resume*` ("…would start a FRESH search, not a resume; nothing was started") — the pill's degrade ladder (missing run folder, exhausted budget, refused preview, launch error) always shows the real reason and re-arms. Launch-row Resume placement deliberately skipped: Launch's 2 s full-list re-render would wipe a row-level arm mid-confirm; the always-visible pill covers it.
- **Verification:** **103 passed** across the five GUI files (brief_authoring 15 + integration_phases 38 + test_gui 36 + balloon 8 + mesh_quadrants 6) by the lanes and the orchestrator + compileall + node --check (app.js/balloon.js/view3d.js/evolution.js). The owner-reported invisibility was diagnosed honestly: the run-controls work was tree-uncommitted at the time (editable install serves static live, but the Python process needs a restart for jobs.py) — this commit is that landing; after it: restart the GUI (tools/launch_gui.ps1) and the pill appears in the left toolbar on every page.
- **Cross-lane notes:** des-3's initially-built `resume: true` bare-flag shape was superseded mid-task by the landed jobs.py (which refuses it) — reworked to run-id sourcing + `/api/runs` validation; `/api/runs` summaries carry no status/config fields (disclosed → budget-exhaustion guard substitutes), and the Status poll feeds the pill without `/api/runs` (honest interim degrade until the pill's own first tick). A transient cross-lane fixture failure (hash-route regex) was fixed by its own lane before the clean combined run. The WP12 mounting WIP by the other agent landed/left the tree during the pass — untouched throughout.

## 2026-10-25 (local, later) - GUI: deferred provenance items LANDED (grounded @ 26a1de1) — CAD STEP inventory, cad_route badge, cma_files log chips, source_profile_alpha pin

- **State verified before starting (owner: "grounded in the current repo state, not something old"):** HEAD = `26a1de1` — the parallel agent's W6 Balloon view landed as a proper `feat(gui)` commit; the remaining uncommitted WIP is the M5/M6 agent's WP12 mounting backend (`config.py`, `design/families.py`, `mesh/*`, `search/evaluate.py`, `test_mounting.py`, `enclosure_1in.yaml`) — `gui/data.py` + `gui/server.py` were CLEAN (no hunk surgery this round; every WP12 backend file untouched). CAD hold lifted by owner ("the other agents stopped working on that CAD stuff").
- **Deferred items landed (from NOTES_FOR_SENIOR's deferral record), reader/route layer grounded against the CURRENT tree — every key re-verified from `mesh/step_build.py`/`cli.py` as on disk, not from older summaries:**
  - **CAD STEP inventory** → `run_detail.step_files_detail[i].inventory`: sidecar `<name>.inventory.json` WINS; else the design's `mesh_meta.json["cad"]` block PROJECTED onto the chip contract `{faces: [{label, count}], solids, closed, tool_sha256, tool_path}` (the projection deviation is deliberate — the committed view layer renders exactly that contract; verified current cad keys from step_build: `tool_sha256` NOT tool_sha, `face_inventory` {driver:1, wall:N}, `solid.solids`, `solid.all_shells_closed` — and the WP12 WIP diff adds only a mounting refusal to `build_mesh_from_cad`, it does NOT change the provenance block). Band-split designs: `band{k}/mesh_meta.json` fallback added beyond the original spec (WP8 shapes have no top-level meta).
  - **STEP file → design hash**: verified on disk that run exports are `<cfg.name>_<rank|seed>_<hash12>.step` (`cli.py` export-step) — the matcher is `_([0-9a-f]{6,40})\.step$` (covers `rank1` AND `seed` names; the listed `STEP_NAME` contract unchanged).
  - **cad_route solve-group marker** (per-design recipe confirmed: `mesh/build.py` routes `Design.params["cad"]`; config.py carries none) → `solve_group.cad_route: true` via a best-objective-row proxy (seed-row fallback; documented) — G1/compare badges render "cad STEP" automatically.
  - **cma_files** run_detail key (NOT CAD): every pycma log the C-5 route serves, `{path (run-relative posix), name, size}` — restart-card chips link the LIVE raw log downloads.
  - **source_profile_alpha pin test**: fixture asserts `solve_group.source_profile_alpha: 0.3` exactly when α≠0 (key real since M5B).
- **Views layer (parallel designer lane):** pycma chips (three honest states: chips / empty-listing caption / key-absent legacy caption), generalized cad chip renderer (every `{label, count}` face pair — no invented segments; `solid ✓/✗`/`solids N` when they arrive; `tool_sha256`→`tool_sha` legacy fallback), `cad STEP` badge pass-through, and the W6-integration check: the parallel agent's balloon commit ALREADY wired its own entry points (route `#/run/<id>/balloon`, run-detail button, balloon.js back-links) — verified zero overlap and pinned by `test_balloon_entry_point_already_wired` so it cannot regress silently. WP12 mounting keys read read-only from the WIP (brief.mounting normalized block; `mounting_key()` freestanding-safe; provenance echo `mesh_meta.provenance.mounting`) and recorded WITHOUT pinning anything against uncommitted code — the future G6 badge/preview builds when WP12 lands (my mounting badge already renders from `solve_group.mounting` whenever that reader key arrives).
- **Verification:** 93 passed across the five GUI files (test_gui 36 + balloon 8 + brief_authoring 13 + integration_phases 30 + mesh_quadrants 6) run by both lanes and the orchestrator + compileall + node --check (app.js/balloon.js/view3d.js/evolution.js). One transient cross-lane test failure (the designer's fixture regex expected `/^\/run\//` for a hash route `#\/run\//`) was fixed by its own lane before the clean combined run; documented, not hidden.
- **Exact-path commit:** only `gui/data.py` (+129/−3), `gui/static/app.js`, `tests/test_gui_integration_phases.py`, `tests/test_gui_brief_authoring.py` + docs — the WP12 backend WIP and `examples/briefs/user/` stay unstaged. Owner's standing directive held: GUI-only, other agents' files untouched. A fresh fixer session was used because the cancelled one is permanently unusable (board error state).

## 2026-10-25 (local, ~01:10 EDT) - W6 LANDED: BL-class Balloon view in the web GUI (owner-directed; BL recon → own render)

- **What shipped** (designer lane, gui/** scope, GPL-3 attribution to `JWSound/boundary-lab` carried as comments; BL = design reference, zero BL code): server `GET /api/balloon/<run-id>/<design-hash>` (JSON: freqs, `balloon_grid`, layout verbatim, per-frequency SPL **normalised to on-axis (θ=0 pole), Float32, clipped [−30, 0]**, NaN→null never fabricated) + `GET /api/balloon/<run-id>` (design picker with `has_balloon`) — strict paths, 404/400 semantics; run page "◉ Balloon 3D" + route `#/run/<id>/balloon`; NEW `static/balloon.js` (~590 lines): the **dB-to-radius blob** (radius = max(spl+30, 0) — shape AND colour encode level; floor vertices pinned at 2 % so −30 dB dimples can't hole the shell), pole-row welding (verified live: pole rows identical), phi seam closed (verified: phi is 0..360 EXCLUSIVE — no stored wrap column), per-frequency in-place position/colour updates (rAF-throttled, no rebuild), a turbo-family ramp interpolated from the house isobar palette (documented divergence: hot end lifted off the paper `#8F0000` so a LIT 3D object reads hot), marching-squares isobar rings (−6/−12/−18/−24 dB at level-radius ×1.018, white), labeled On-axis/Horizontal/Vertical rays + protractor, nearest-ray hover readout, radar slicer (great-circle cut at any −180..180 azimuth, dB rings, `--balloon-cut` accent), and the freq×angle slice panel via `charts.js::isobarMap` (+ additive optional `angleTicks` param, default-preserving for existing callers). Frequency slider defaults to band-top.
- **Validation (current mixed tree, all green):** `compileall` data/server OK; `node --check` balloon/app/charts/view3d (+ others) OK; `pytest tests/test_gui.py tests/test_gui_balloon.py` → **44 passed / 0 failed / 0 skipped** (was 35; +9 balloon tests: endpoint 200/404/400 + payload shape); extended gui set (brief authoring, integration phases, mesh quadrants) 81 passed; live endpoints: designs list 200, verify balloon 200 (23×45, 25×1035, 485 KB), screen balloon 200 (16×32), missing design 404; both-theme screenshots (**`runs/gui_balloon/balloon_w6_light.png` / `balloon_w6_dark.png`**, 0 console errors).
- **Reconciled against the moving tree:** the commit carries ONLY the gui set + this file pair as one commit; the concurrent WP12/mounting lane's in-flight files (`config/families/mesh/step_build/evaluate + mounting tests + enclosure/user briefs`) and its `12_RESEARCH_BASIS.md` §12 append (BL balloon facts, owner-directed) are NOT staged here — they ride the other lane's own push. The balloon view ships with today's stored densities and upgrades itself when the verify balloon is densified (WP5 ΔDI ladder → W7).

## 2026-10-25 (local, later) - docs: BL balloon rendering + resolution facts recorded (12_RESEARCH_BASIS §12 owner-directed appendix); W7 density TODO recorded; CAD work stopped + deferred (owner directive)

- **Owner directive (chat): GUI-only round; ALL CAD work stopped + deferred.** My in-flight CAD reader lane was cancelled and its partial code REMOVED from the working tree after classification; the deferred design is preserved verbatim in `NOTES_FOR_SENIOR.md` (the cad block's real key names `face_inventory`/`tool_sha256`/`tool_path`/`solid.solids`/`solid.all_shells_closed` read from `mesh/step_build.py`, the `_rank\d+_([0-9a-f]{6,40})\.step$` filename→hash regex, the per-design `Design.params["cad"]` → run-level `cad_route` proxy, and the cma-files direct-chip listing). `gui/data.py`'s working diff was then verified to carry ONLY the parallel agent's live balloon (W6) work, so no misattribution sweep can recur. The backend M5/M6 CAD stream belongs to the OTHER orchestrator session (its live edits in `config.py`/`design/families.py`/`mesh/build.py` untouched — the STOP record in NOTES_FOR_SENIOR is the cross-session mechanism; that session must be stopped by its own owner/operator).
- **§12 appendix (owner-directed, append-only per the §10/§11 precedent) in `docs/plan/12_RESEARCH_BASIS.md`:** Boundary Lab's balloon rendering, resolution, and frequency handling — [verified] BL freq defaults (200–20 000 Hz, `freq_count` 41 log-spaced) + the data-handling quirks GUIs must know (non-monotonic van-der-Corput GUI-frequency ordering → sort by value, never by index); [verified] balloon resolution = `balloon_angle_precision_deg` 2.5° (clamped 0.5–15°) → equal-area **Fibonacci point count `round(41253/angle²)`** (~6 600 pts at 2.5°, ~41 253 at 1°) — the equal-area property is what makes BL's spherical DI a plain mean of `10^(SPL_rel/10)`; superellipse −6 dB-contour shape fitting recorded as maths-not-code (BL's module is Qt-importing); [verified, W6 source recon] rendering = dB-to-radius blob (radius = max(spl−floor, 0) — shape AND colour encode level), smooth shading + turbo, white tubed isobar rings offset ≈0.2 % of extent, radar slicer via barycentric great-circle interpolation, freq×angle pane = fractional-octave smoothed filled contour, `BALLOON_EXPORT_SCHEMA_VERSION = 2` payload shape; [inferred] our stored balloons are ~8–27× coarser than BL's default sphere — the density TODO below follows directly. Sources: committed BL extraction `docs/research/boundary_lab_0.5/bl_inventory.md` + the W6 record in NEXT_DEV_PRIORITIES; GPL-3.0 attribution carried.
- **W7 recorded in `docs/NEXT_DEV_PRIORITIES.md`** (owner priority 2026-10-25): raise verify/final-tier data density — `solve.balloon_points_verify` from the M3/WP5 512→1024→2592 ladder into **1 000–6 600** points, verify frequency count from **25** toward **~41 log-spaced** (via `grid.verify_points_per_octave` / a NEW named grid group per the W3 contract rule if the solve-spec hash changes). Gates: the M3/WP5 measured ΔDI ladder decides the accuracy buy; GPU cost disclosed (balloon points bill field evaluation, not dofs; freq count bills linearly per solve); stays OFF the 8 GB 4060 search tiers. **Same TODO mirrored in `NOTES_FOR_SENIOR.md`** with the BL reference numbers.
- **Encoding-hygiene lesson applied:** my first append to `NOTES_FOR_SENIOR.md` used PowerShell `Add-Content` (writes the ANSI default codepage on PS 5.1) and silently corrupted the file's encoding (cp1252 bytes; lossy Δ/θ/em-dash characters); caught by a byte-level UTF-8 check, the file was restored to HEAD (invalidating only the uncommitted append — the append-only rule protects committed blocks) and BOTH notes were re-written ASCII-safe via explicit-UTF-8 Python. All doc files byte-verified valid UTF-8 before commit.
- Docs-only pass: no code touched; the parallel agent's live WIP (balloon view, backend CAD stream) stays unstaged in the shared tree — exact-path staging only.

## 2026-10-25 (local, later) - GUI: inline 3D on every run page + 3D evolution time-lapse (owner requests) — frames3d reader + frame player + disposal sweep

- **Owner requests (chat):** "put a (smaller) 3D model view on each run page without clicking the 3D tab" and "set the evolution animation up for the 3D model view as well." Built across two disjoint lanes on top of G1-G4: fixer = reader/route, designer = views; then integrated (72 offline tests green: brief_authoring 12 + integration_phases 19 + test_gui 35 + mesh_quadrants 6; compileall clean; node --check OK on app.js/evolution.js/view3d.js — run by lanes and orchestrator).
- **Reader/route (fixer lane):** new `GET /api/evolution/<id>/frames3d` → `data.evolution_frames3d` — improvement frames ONLY, the rule SHARED with the 2D `evolution()` via a new `_improvement_flags(rows)` refactor (the two players literally cannot disagree about which frames animate). Frame record `{n, objective, mesh_hash, quadrants, verts (mm, 2-dec), tris, n_tris_full, decimated, n_verts}`; stride decimation `k = ceil(n_tris_full/cap)` capped at 6000 tris/frame; quadrants chain meta → ndjson row → config.yaml → "1234" (same as mesh_surface); improved row with missing/invalid mesh → SKIPPED, disclosed in a top-level `note` ("N improved frame(s) skipped: no saved mesh"); `available:false` + honest notes for no-rows/no-improvements/no-meshes cases. Cache `runs/.gui_cache/evolution_<id>_m3d.json` keyed `[M3D_VERSION, cap, ndjson size/mtime, per-frame mesh mtime/size]` — invalidates on ndjson growth or any improved mesh appearing/changing/disappearing (cap in the key deliberately, so reader-level calls with different caps cannot collide); atomic write. Route dispatched next to /api/evolution/<id> with house 400/404/500 mapping. Real-run sanity at cap 50: run 20261025T081346Z-screen-30c0ae → available, 4 frames, n_tris_full 5010 → decimated.
- **Views (designer lane):** **inline 3D on run detail** — below the wall cross-sections, a ~300px canvas for the BEST design, lazy-fetched after render (page never blocked), reusing `init3d`'s camera-fit + the SAME persisted `hl-v3d-shadows` toggle as the 3D page; full 3D tab unchanged and remains the only auto-loaded scene per page. **Disposal sweep:** every scene container now carries `data-v3d` (`#view3d-wrap`, inline `#inline-3d`, evolution `#evo-3d`) and `route()` disposes ALL of them before the DOM swap; the detached-container race (scene starting after its page was replaced) is closed at the source — the inline loader and `enable3d` bail on `isConnected` after their awaits. **3D frame player** (`view3d.js::init3dFrames`, + pure `prepareFrames`): ONE scene, camera/lights/shadow rig fitted to the UNION of all frames' mirrored bounds (no per-frame camera jumps); per-frame mirrored geometry built LAZILY on first show and cached, hot-swapped via `mesh.geometry =` (no scene rebuild); decimated frames disclose "mesh decimated to N tris" on-canvas; shape-gates junk (whole xyz triples, ≥1 triangle, whole index triples — skipped, never fabricated); CDN failure degrades to the existing 2D wall-profile fallback and honestly resolves null. **Evolution 3D mode:** an `evo-3d` checkbox lazy-fetches frames3d only when selected; the rule is stated once as `RULE3D` and disclosed 4× — **3D ⟺ improvements-only**: checking 3D flips the frame-mode select to "improvements only"; selecting "every candidate" turns 3D off with the disclosure "'every candidate' plays in 2D — 3D shows improvement frames only." Score/knobs/side/front panels keep drawing in either mode; frames are matched by the reader's eval number `n` (unmapped eval holds the current mesh rather than guessing); the reader's skip-note is surfaced to explain 3D-vs-2D frame-count gaps.
- **Deviations on record (all accepted):** `prepareFrames` is the node-tested core while the WebGL hot-swap paths are source-pinned (WebGL cannot run headless); the inline viewer shares the persisted shadows key (one preference, two surfaces); the reader's `note` key was additive to the dispatch contract and the view surfaces it; theme/resize re-renders reset evolution playback to 2D (pre-existing control-state behavior, disclosed).
- **Commit hygiene:** the seed-gate lane had COMMITTED its `list_configs` WIP before this integration (data.py's remaining diff was frames3d-only at old starts 989/1071/1112 — verified before staging, no hunk surgery needed this time); this commit's data.py/server.py diffs carry exactly the frames3d work. Owner directive stands: no Oracle pass this round — verification by the pasted test output + orchestrator's diff read (improvement-rule sharing and the disposal sweep reviewed).

## 2026-10-25 (local, later) - GUI integration plan PHASES G1-G4 LANDED (G5/G6 stay owner-gated): provenance badge matrix, restarts/QD surfaces, compare solve-group warns, verify job kind + raw pycma logs

- **Owner decision (chat):** start the GUI integration plan (GUI_INTEGRATION_PLAN_2026-10-25.md §8) NOW — only G5 (bake-off, P6 gate) and G6 (mounting, WP12 gate) wait; G1-G4 build from committed run artifacts alone (no solver/mesher dependency). Parallel lanes with disjoint scopes: fixer = reader/route layer (data.py/server.py/jobs.py + new offline test file), designer = views (app.js + view-wiring tests), then two small resume rounds to close the seam (`solve_group`/`search_restarts` onto run detail; views rewired onto the live keys, dead guarded paths DELETED not layered).
- **Reader/route layer (fixer lane):** **C-1** `run_detail` += `restarts`/`qd` (verbatim from run.json, keys ABSENT when unset), `restart_dirs` (sorted `cma/restart_*` names, `[]` when none), `step_files_detail` [{name, inventory|null}] (parsed `<step>.inventory.json` sidecar or null; `step_files` stays byte-identical — its frozen test pins shape, deviation accepted); `solve_group` (the non-default solve-group fingerprint: `backend` + `freqs_hz` identity ALWAYS, others only when non-default — same vocabulary as compare), `search_restarts` {mode, max} only for a valid config.yaml `search.restarts` block (mirrors `_validate_restarts`; malformed → absent, never fabricated). **C-2** /api/compare += `group_a`/`group_b`/`mixed_keys` via `_solve_group_fingerprint` (backend+freqs identity always; cuda_fused/source_motion/source_profile_alpha/near_correction*/solve_precision/rear_res_factor/mesh_policy+band_edges/mounting/objective_version/qd_algorithm when non-default — WP16/WP12 keys read defensively, absent = absent). **C-5** `GET /runs/<id>/cma[/restart_k]/<log>` raw serving: strict regex `^(?!.*\.\.)[A-Za-z0-9_][A-Za-z0-9_.\-]{0,79}\.(txt|dat|json2|q)$`, resolved-path containment inside the run's cma/ tree, text/plain+attachment+no-store+nosniff; 404 otherwise. **G-1** jobs.py gains the `verify` GPU kind (`verify --run <dir> --top 1..25 [--brief]` — verified engine-true against `_verify_body` which takes a DIRECTORY), `/api/preview` marks it GPU, GPU-busy refusal inherited.
- **Views layer (designer lane):** **G1** provenance badge strip on run detail — single vocabulary/source `solve_group.<key>` (tooltips literally name the key path; identity baseline `beat_cuda · grid screen …` always visible; fused CUDA / near-corrected · double / source plug α / band-split / rear ×2 / enclosure / J v2 / CMA-ME / source motion exactly when non-default; restarts badge `IPOP ×N`/`BIPOP ×N` from run.json.restarts count + search_restarts mode) + f11 caveat sentence rendered ONLY when band_hi > f11 and f11 known. **G2** restart schedule card (per-restart popsize/σ0/evals/stop pills; honest fallback when search_restarts absent; empty-state card for restart_dirs-without-restarts; pycma-log caption naming the live C-5 URLs) + QD provenance caption on the atlas view (the pinned canvas code is byte-untouched). **G3** compare renders A/B badge rows from the SAME builder + "These runs differ in: …" banner (empty ⇒ no banner) + DI guard twin ("DI: cuts estimate — not comparable"). **G4** STEP chips upgrade to the face-label inventory view (`3×3 STEP · driver=1 wall=9 · tool <sha>`) when a sidecar exists — silent plain-chip absence is the honest default (no sidecar deployed yet).
- **Test discipline:** new `tests/test_gui_integration_phases.py` (13 offline tests: C-1 present/absent/malformed honesty, C-5 allow-list/serving/traversal/404, C-2 one-key-differs + identical + fingerprint vocabulary, G-1 argv/bounds/brief/GPU/preview, app.js ES-module gate); `test_gui_brief_authoring.py` gained §15-18 (6 view-wiring tests; the six badge helpers are pure functions EXECUTED in node via a DOM-shim wrapper — every badge branch honestly asserted, not grepped). Final: **63 passed** (brief_authoring 9 + integration_phases 13 + test_gui 35 + mesh_quadrants 6) run by lanes and orchestrator + compileall clean + node --check OK.
- **Cross-lane reconciliation notes:** the C-1 `step_files` shape deviation (reader kept the frozen string list; inventory rides `step_files_detail` — views matched by name; the literal contract would have required editing a frozen test) and the GPU_KINDS `verify` addition (the plan's "gain nothing" line predates G-1 — verify is a real GPU solve, plan line superseded by the phase spec). `qd_algorithm` IS in the fingerprint (plan §3.9 didn't list it — mixing CMA vs CMA-ME now warns; judged correct, disclosed). Restart-log DIRECT file chips are infeasible from directory names only — the card caption names the live URL shape instead of inventing filenames.
- **Commit hygiene:** `gui/data.py` staged by content-selected hunks ONLY (CMA regexes/_as_dict/run_detail/fingerprint regions) — the STILL-uncommitted seed-gate WIP region (~:626+ list_configs memoize, another lane's) stays unstaged/unowned; all other staged files carry only this phase's changes. Owner directive stands: no Oracle pass this round — verification by the pasted test output + orchestrator's line-level read of the security-sensitive diffs (C-5 regex/containment reviewed byte-by-byte; `verify --run` directory contract checked against `_verify_body`; the seed-gate WIP hunks verified disjoint).

- **Commit-hygiene disclosure (2026-10-25, written as a follow-up docs edit):** commit `599997d` (this entry's build) unintentionally carried the M5B lane's STAGED files alongside the 3D GUI pass (35 files): the M5B landing (`94243df`, WP14 category + WP16/17 fork stack + hosted-fork pin + M4 debts) had staged-but-uncommitted files in the shared index when the GUI integrator committed, and the sweep went unnoticed at commit time (the GUI commit's message therefore describes only the GUI scope). The authoritative M5B record is `94243df` + its own CONTINUITY entry below + `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md` (bytecheck 33/33). Post-sweep tree verified coherent at HEAD: offline suite **1335 / 0 fail / 0 err / 0 skipped** (junitxml `runs/m5b_rectify/suite.xml`) — the historic `test_mesh_pin` tripwire is RESOLVED (main pins == installed). Process lesson recorded for multi-orchestrator sessions: verify `git diff --cached --stat` scope per-file BEFORE every commit when lanes share an index. No content lost or misattributed in CONTINUITY; no history rewritten (no force-push).

## 2026-10-25 (local, ~10:00 EDT) - multicell COMPILATION DOSSIER ADDED (docs-only; NOT an implementation plan — owner-requested compile of what exists, what was planned, how the first attempt failed, and the open questions)

- **`docs/research/typologies/MULTICELL_HORN_RESEARCH_2026-10-25.md`** — the compilation dossier the owner asked for ("start building a document for researching... adding info from the repo... use your own context"): [1] the BANKED WP14 category (tool/route/keys/tests/GUI surfaces — all landed, all committed); [2] the prior planning verbatim (WP14 + Report-2 §4/§5 — free septa on symmetry planes, the three solver traps, the dofs gift); [3] the FULL honest record of the deferred first attempt (the closed-solid mouth-cap fixture measured diffraction around the body — throat impedance = a free unbaffled disk in BOTH arms, DI negative in both = the rear-source signature; the gate NOT-ALLOWED at 11.28 dB / 14.59 dB / bw_v 159.1°; the mesh-valid ceiling 2891.68 Hz means the 4 kHz gate is unanswerable; the ranked attribution with #1 = the un-corrected CUDA arm's ~O(10⁵) thin-gap pairs and #5 unresolved); [4] the acoustic picture compiled (WE/Altec practice, odd-cell centring, split-lobe behavior, the simulator-relevant reading of septa/thickness/near-correction); [5] the constraints ledger; [6] **the SIX OPEN QUESTIONS** (mouth treatment FIRST — open aperture vs wall-shell vs enclosure-style; septum-edge refinement economics; symmetry/stage-2 timing; metric choice incl. valley-depths-not-bw_v; the brief/search-key question; per-exit phase reality vs the landed WP16 J0 plug) — explicitly NOT an implementation plan and explicitly not decided.
- Cross-links: INDEX research-table line added; dated COMPILATION POINTER appended to `docs/research/senior_pass_2026-10-24/02_TYPOLOGIES_AND_MULTICELL.md` (append-only; that doc's §4/§5 planning text stands); the deferred-evidence registry + resume recipe remain in `docs/ISSUES.md`'s deferred-WP14 block. WP12 DONE; **WP13 OWNER-DEFERRED ("don't know how necessary that is", 2026-10-25)**; docs-only: no code, no configs, no GPU; suite state unchanged 1372/0/0/0.


## 2026-10-25 (local, ~10:00 EDT) - M6/WP12 LANDED: enclosure mounting plumbed + MEASURED on two finalists (dofs +199%/+107%; enclosure J improves but is a different landscape); WP13 OWNER-DEFERRED; suite 1372/0/0/0

- **Owner rulings (chat, 2026-10-25):** "follow the implementation plan" (WP12 authorized); **"defer WP13 — I don't really know how necessary that is in the first place"** (the axisymmetric backend is OUT of the active plan; it remains in the work order for whoever resumes it).
- **Plumbing (all opt-in, ABSENT = bit-for-bit, tested):** `brief.mounting {type: enclosure, depth_mm > 0, margins_mm (scalar or {l,t,r,b}, default 25), edge_mm ≥ 0 (default 18), plan: "rounded_rectangle" (the only buildable token)}` → normalized on `Config.mounting` → ONE shared translator → the mesher's OWN keys (formula route: `mode: enclosure` + top-level `enclosure` block; GRID route: `HornEnclosure` + `outer_points=None` + `wall_thickness_mm=0`; CAD/STEP route: clean `GeometryInvalidError` deferral). Cache identity appends `-mnt-<12hex>` (mesh/evaluate/solve/run-known + the ndjson row key — resume memo verified); `mesh_meta.json["mounting"]` + ndjson `row["mounting"]` + dataset `provenance.mounting` echoes; `export_step` carries the mounting too. No mesher-side change (pin stays b922e807); no GUI edits (the dormant badge goes live via the brief schema). Focused **71/0/0** + single quarter enclosure build green (0.54 s; tags incl. ENCLOSURE).
- **Measurements ([measured]; doctor 11/11 pins green; one GPU job at a time; `runs/m6_wp12/`):**
  - osse_axi (seed d04e8697a87d): dofs 1013 → **3033 (+199.4 %)**; J 19.8072 → 11.6605; wall 10.07 → 16.26 s; VRAM peak 3177 MiB.
  - freeform_sculpt (seed 892bb3551903): dofs 1362 → **2813 (+106.5 %)**; J 30.9448 → 22.9889; wall 8.66 → 17.89 s; VRAM peak 2966 MiB.
  - BOTH under the unchanged caps (5,000 screen) — no cap raised anywhere; meshing did NOT slow (cold-start dominated).
  - Freestanding reference parity on the SAME solver SHA (760a1ec): worst **2.08e-05 deg / 2.91e-06 dB** vs the stored base-pin runs.
  - Honesty rules: J across mountings = a DIFFERENT objective landscape — never rank designs across mounting modes (provenance/caches prevent silent mixing); the enclosure briefs widened the designer's own envelope (220→300 / 450×450×300) as the envelope guard demands; the per-record `peak_vram_mb` probe stays untrustworthy (external sampler is authoritative — pre-existing gap).
- **Offline suite (final tree, everything committed): 1372 / 0 / 0 / 0.**
- **Evidence:** `docs/evidence/M6_WP12_2026-10-25.md` — byte-check `tools/evidence_bytecheck_m6.py` **21/21 PASS**; provenance note inside (the measurement run used the editable install while the plumbing was uncommitted; the same commit resolves it).

## 2026-10-25 (local, later) - GUI: typology-first COMPOSE wizard landed (#/compose) — pick shape → brief constraints → run + launch

- **Owner UX direction (chat, 2026-10-25, "the workflow seems backwards"):** typologies should be picked FIRST, then brief constraints, then run shape. Built as the **Compose wizard** (designer lane, session-reused from the briefs-editor build; same three-file scope: `app.js` +534/−16, one nav line in `index.html`, tests extended in `tests/test_gui_brief_authoring.py`.
- **`#/compose` (nav: ⊕ Compose between Typologies and Launch), three fieldset steps on one page:**
  - **Step 1 Shape:** multi-select typology rows from `/api/configs` grouped by catalog group with per-group "select all"; each row captioned family · symmetry · knob count · brief_file stem; disabled configs VISIBLE, pill-marked "disabled — the starting design does not materialize (engine seed gate)", unselectable, skipped by select-all; live summary line names the emergent mode ("single-config run" vs "campaign — --families a,b,c"). **Uncatalogued configs** (no `catalog_name`: e.g. `*_fusedcuda`, `multicell_3x3`, `salmon_saddle`) get their own group "Uncatalogued — single-config runs only": selectable only as the SOLE pick (campaign resolves catalog names only; a second pick auto-deselects with the reason shown on the page).
  - **Step 2 Brief:** (a) new from scratch (`newBriefDraft()` reused verbatim incl. the provenance note), (b) one typology's `brief_file` as starting point (stem-matching loader refactored to shared `briefFileStem()`/`findBriefByFile()`, now also used by the Briefs picker — behavior identical), (c) an existing brief used AS-IS (path passed straight through; campaigns don't require saving a copy). Editors (a)/(b) are LAUNCHABLE ONLY AFTER ONE SAVE through the reused editor (`showBriefDetail` gained `opts.mount`/`opts.onSaved`/`opts.hideFamilies` — the Briefs page's defaults/behaviour are untouched) — the gate mirrors engine truth (`jobs._repo_file` refuses non-existent brief paths); the gate text "save the brief first — the run needs a file path" disables preview and launch. Engine-fact caption shown: the brief does not name the typology — the run binds them.
  - **Step 3 Run + launch:** 1 pick → dry-run (mesh only, no GPU) / run / search radio + budget/seed (blank = engine default, disclosed); 2+ picks → campaign tier dry-run/screen/compare + `--families` comma list shown verbatim + per-family engine-default budget captions (`budget_for_tier`); debounced `POST /api/preview` renders the EXACT command in a `<pre>`; `gpu_busy` disables launch with the server's reason (text, not color-only); `POST /api/jobs` → job id + link to #/launch. The wizard never builds argv itself and never solves in-process — both endpoints allow-listed server-side.
- **Honesty findings pinned as tests:** `campaign --seeds/--budget` exist in the CLI but `jobs.build_argv("campaign")` reads ONLY brief/families/tier — fields sent via /api/jobs would SILENTLY VANISH, so the wizard ships NO override fields (payload-fidelity rule) with engine-default budget captions; `test_campaign_budget_and_seeds_are_not_gui_plumbed` pins the pairing. Also pinned: every POST body the wizard sends maps 1:1 onto `build_argv` output for all four kinds (`test_compose_wizard_argv_shapes`) and the route/nav/view/mount wiring (`test_compose_view_is_wired`).
- **Process disclosure (designer lane, verified clean):** mid-task a first insertion contained broken draft fragments and briefly ate the "View 6: Launch" header — caught by the lane itself, whole block rewritten and spliced line-exact; the orchestrator's targeted re-read confirms View 6 intact (`app.js:2448`), route order (compose registered before launch :61-62), nav line, and the preview/launch POST flow (:2411/:2434).
- **Verification (owner directive: no Oracle passes this round — orchestrator review + tests stand in):** pytest `test_gui_brief_authoring.py + test_gui.py + test_gui_mesh_quadrants.py` → **48 passed** (7 + 35 + 6; run by lane AND orchestrator); `compileall hornlab_search/gui/` clean; `node --check` OK on app.js AND evolution.js. Working tree at commit time carries the still-landing lanes' WIP (`config.py`, `families.py`, `build.py`, `grid_build.py`, `evaluate.py`, `beat.py`, `step_build.py` + tests + `pyproject.toml`/`conftest.py`) — none touched, none staged.
- Known small behavior, disclosed by the lane: re-picking a brief source restarts the editor (fresh draft/loaded typology) — unsaved edits in the previous draft are replaced, not merged.

## 2026-10-25 (local, later) - GUI briefs: author new briefs from scratch, every schema key exposed, typology-first wizard chosen (owner UX direction)

- **User request (2026-10-25, chat):** "the briefs page should let us create a new brief entirely from scratch … wider horizontally than vertically … pick these new typologies … there are controls under briefs that should be exposed that aren't." Discovery pass (read-only) established: w≠h envelopes are ALREADY legal for every symmetry value (shipped 400×300 hv brief + user 500×400 axisymmetric) — the only symmetry rule is axisymmetric ⇒ coverage_h == coverage_v; the old editor silently carried `symmetry`/`throat_angle_policy`/`objective`/`verify_only`/`description`/`z_min` with NO controls and silently DROPPED `verify_only`, `objective`, `grid`, `throat_angle_policy`, `target.freq_weights` on save (saving a 12 kHz brief corrupted it to 5.5 kHz via a GUI-invented clamp).
- **Built (designer lane on `app.js` + new `tests/test_gui_brief_authoring.py`; server/data/jobs untouched):** (a) **New brief** button — from-scratch draft defaulting to the shipped `axi_90x90_1in.yaml` values (cov 1, rip 1, di 0.3, dislope 0.5, flat 0.5, load 0.5; 500×400×250 envelope = wider than tall) with an honest provenance note; (b) **Start-from-typology picker** fed by `/api/configs` (catalog groups, disabled configs visible-but-marked; brief_file matched by stem; honest empty states); (c) the editor now exposes EVERY `load_brief` schema key: symmetry select (server refusal rule quoted verbatim), throat_angle_policy (absent = pre-WP2 behaviour, sent as explicit null — live-verified `save_user_brief` accepts and round-trips it), objective v1/v2, verify_only, description, z_min, and a collapsed freq_weights row editor (client-side pre-check only; server re-validates); (d) payload fidelity: nothing silently dropped, `grid` carried through, band values saved as typed and (e) **the GUI-invented 5500 Hz clamp was REMOVED** (git blame: authored in 77aac53b "designer-first UX hardening pass" with NO authored intent in its message; the schema has no such cap and the shipped *_12k briefs run 12000) — the real 8 GB dof-cap hardware note survives as an always-visible hint ("beyond the 8 GB GPU dof cap: verify-only territory"), never a clamp.
- **Tests:** new offline `tests/test_gui_brief_authoring.py` — full-payload round-trip through the REAL `load_brief` (verify_only + objective v2 + pin + freq_weights + axisymmetric with the 500×400 w≠h envelope, mirroring user/7040.yaml), shipped-collision/bad-name refusals, list_briefs visibility, node ES-module syntax gate; live-verified the explicit-null throat policy save. `pytest tests/test_gui_brief_authoring.py tests/test_gui.py -q` → **39 passed** (4 + 35, run twice incl. after final edits); `compileall hornlab_search\gui\` clean. Launch-page `GROUP_LABEL` gained the missing `organic` label (mechanical parity with the briefs picker).
- **Owner UX decision (chat, 2026-10-25): typology-first compose wizard** — pick typology/group(s) first, then brief constraints, then tier + preview + launch (maps to the engine: single config → dry-run/run/search; group/multi → campaign tier dry-run/screen/compare with brief required). The existing page-silo order was called out as backwards by the owner; wizard build is next (separate commit).
- **Process note:** owner directive in chat — **no more new Oracle passes this round** (waiver noted here; the already-running read of this diff is the round's last and is incorporated post-hoc when it lands). Verification for this commit is the pasted test/compileall output above + the full diff read by the orchestrator (the schema-fidelity risk surface was closed by the live null-policy save check). The other lanes' WIP in the tree continues landing (`evaluate.py`, `families.py`, `build.py`, `step_build.py`, `test_mesh_step_build.py`, `multicell_3x3.yaml` appeared mid-pass) and is untouched by this commit.
- **Oracle read returned post-commit: GO-with-fixes, applied as a follow-up commit.** Its process MUSTs were already handled in c7d2bbf (docs in-commit; explicit-path staging — `examples/briefs/user/` NOT swept in; its `gitignore` suggestion recorded in ISSUES for the 03-owning lane). Its code MUST is fixed here: `renderBriefs`-side `addFwRow` interpolated raw `yaml.safe_load` values unescaped and a non-array `band_hz` broke the form mid-render — now `esc()`-wrapped (rows stringified) with an `Array.isArray` guard that DISCLOSES a non-list `band_hz` ("not editable here — fix the YAML") instead of throwing; SHOULD applied: the new-brief provenance note now discloses that band top 5500 follows the shipped brief while band low 500 Hz is the compose default (the one previous undisclosed divergence). Tests re-run after the fixes: **45 passed** (brief_authoring 4 + test_gui 35 + mesh_quadrants 6); compileall clean. Schema-fidelity audit of the whole payload vs HEAD `load_brief`/`Target.from_dict`: PASS (default draft save throws nothing — `null` throat-policy gate, `{}` source, numeric coercions checked).

## 2026-10-25 (local, later) - GUI fix: 3D views rendered only the meshed wedge (quarter/half slice) — root-caused and fixed; briefs-page request taken

- **User report:** 3D views render "just a quarter slice", not the whole horn (screenshot: `salmon_elliptical` 3D view, run `20261025T105841Z-screen-7e8b47`, design `75afac11ac93`, 2930 tris, dark theme; @observer analysis: one ~90° wedge with two straight cut edges, no mirrored copy present).
- **Root cause — THREE bugs compounding, all verified in the tree:**
  1. `gui/data.py::mesh_surface` fell back to `quadrants="1234"` (full model, DO NOT mirror) whenever `mesh_meta.json` was absent — and the GRID route writes NO mesh_meta.json by design (`mesh/build.py:273` build_mesh docstring, referring to the GRID route; the run's design dir has design.json/mesh.msh/metrics.json/response.npz/status.json but no mesh_meta.json). Result: every GRID/rows design (the M4 typologies — salmon_elliptical/x_shape, iwata_ar, toroidal_rollback, lecleach rows…) rendered its raw meshed wedge. `search/evaluate.py:500-516` only logs the missing meta at debug level.
  2. `gui/static/view3d.js::mirrorMesh` handles ONLY `quadrants === "1"` (both-plane mirror); GRID half-models ("14" = +x half, "12" = +y half — semantics per `gui/data.py::horn_dims:141-142`) were never mirrored at all (latent bug independent of 1).
  3. The 3D-view label at `app.js:1371` hardcodes "(mirrored from quarter model)" for EVERY run — visually contradicting what rendered (the screenshot's own subtitle claimed mirroring happened while showing one wedge).
- **Fix (all artifact-derived, no invented keys):**
  - `data.py::mesh_surface` quadrants now resolves as a CHAIN: `mesh_meta.result.quadrants` → the design's `search.ndjson` row quadrant string (new `_row_quadrants` helper — every evaluated row carries `quadrants`, the same source `horn_dims` already trusts) → `config.yaml` `mesh.quadrants` → `"1234"` last resort (render as-is = the only honest default when nothing records the domain).
  - `view3d.js::mirrorMesh` generalized: `'1'` → 4 copies (unchanged behavior), `'14'` → 2 copies mirrored across x=0, `'12'` → 2 copies across y=0, anything else passthrough; exported for testing; winding-flip rule (single reflection flips handedness, `sx*sy < 0`) preserved from the original code.
  - `app.js` label now quadrants-aware and honest: "quarter model mirrored to the full horn" / "half model mirrored to the full horn" / "full model, no mirroring", triangle count labelled "in the meshed domain".
- **Tests (offline, no browser automation; new file `tests/test_gui_mesh_quadrants.py`, additive — avoids the uncommitted test_gui.py WIP):** 5 reader tests pin the fallback chain (meta wins; row fallback; config fallback; honest "1234" default; ignores other designs' rows) + a REAL node-import unit test of `mirrorMesh` (tmp .mjs wrapper resolving the static file by absolute file URL via `pathToFileURL`; asserts 12 verts/4 tris for '1', 6/2 with the exact flipped triangle [3,5,4] for '14' AND '12', passthrough for '1234'/unknown/undefined, mirrored extents balance around both axes). Result: 6/6 new tests PASS; `pytest tests/test_gui.py -q` 35/35 PASS (incl. the node ES-module syntax gate); `compileall hornlab_search/gui/` clean.
- **Commit hygiene:** `hornlab_search/gui/data.py` also carries ANOTHER lane's uncommitted WIP (list_configs seed-gate memoize, ~:611-690) — the fix commit stages ONLY the mesh_surface hunk (hunk-extracted patch → `git apply --cached`, LF-exact, em-dash integrity verified at byte level in the staged blob; the WIP hunks stay unstaged/unowned). Also mid-pass the in-flight set grew (`design/families.py`, `mesh/build.py`, `search/evaluate.py` now modified too — the WP14/debts lane is still landing; none touched here).
- **Follow-up recorded (ISSUES):** the GRID route SHOULD write mesh_meta.json for provenance parity (evaluate.py:500-516 tolerates absence at debug log level; GUI now tolerates it too) — an ask for the grid lane, not fixed here. Also 2D `mouth_outline` doubling only covers `'1'` (data.py:886-899) — for '14'/'12' half-models the mouth/front-view outline is the meshed half only; small follow-up, same semantics as this fix.
- **User request taken (briefs):** Briefs page must support creating a NEW brief from scratch — asymmetric mouth envelopes (user wants wider-h-than-tall), symmetry handling that errors informatively instead of confusingly, and picking the new M4 typologies as templates with the controls currently hidden. Discovery lane dispatched (read-only); build follows after this fix lands.
- **Oracle pre-push review of this fix: GO-with-fixes, both must-fixes applied** (mesh_meta-writer anchor corrected to `mesh/build.py:273` in code + both docs; node-availability gate changed from a silent vacuous pass to `pytest.skip` mirroring test_gui.py's ES-module gate; optionals applied: quarter/half header phrasing in view3d.js + mesh_surface docstring, mouth_outline anchor corrected, test-file trailing newline). Verified-clean list included the exact [3,5,4] handedness math, horn_dims semantics match, staged-vs-WIP hunk separation.

## 2026-10-25 (local, later) - GUI-integration PLANNING pass: docs/GUI_INTEGRATION_PLAN_2026-10-25.md (docs-only; no GUI code, no GPU)

- **Scope (handoff after M5 WP11 @ 298b56f):** plan the GUI integration of EVERY capability the implementation plan (`docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md`, WP1-WP17 + P6a/P6b) adds by its end — routes, API contracts, views, workflows, provenance displays, phased build order. No implementation except the doc itself.
- **Inventory method:** three read-only explorer lanes (verifying, never trusting the handoff): (A) GUI surface map @ 298b56f (all routes/readers/views/tests with line anchors; confirmed the GUI reads only run-summary/artifact subsets — `run.json.restarts/qd`, `best.json`, `cma/restart_k/*` are written but NEVER read by any view); (B) per-WP status against CONTINUITY/ISSUES + the plan (WP1-5/7-11/15 DONE; WP6 ABANDONED by owner; WP14/16 LANDING; WP12/13/17/P6 PLANNED-OWNER-GATED; P5 W4 `compare --bar` still MISSING in cli.py); (C) provenance/data contracts (types/records/run.json blocks/fork pins/jobs allow-list/verify-tier artifacts).
- **In-flight disclosed (M4 lesson 4 — reconciled, never re-dispatched, touched nothing):** WP14 lane WIP uncommitted on main (near_correction/solve_precision keys in config.py+solve/beat.py, `tools/cad/multicell.py` + `tests/test_cad_multicell.py` landed untracked mid-pass, pyproject/conftest edits, seed-gate memoize in gui/data.py, grid_build.py EOF mesh-cache sketch). Fork state re-verified during the pass: WP16 is **committed** (`f4ef05c` on `hornlab-search/wp16-source-profile`, 7 files incl. Julia tests) and **pushed** to `ourfork` = github.com/llevaachingada/hornlab-beat-bem; the fork checkout now sits on `hornlab-search/wp17-cuda-near` (at f4ef05c, zero WP17 commits) with fresh uncommitted WIP in 3 files — that lane's scope. Both lanes' file scopes untouched by this pass; commit is docs-only.
- **Key planning facts surfaced:** (a) provenance field `source_plug` does NOT exist anywhere (rg = 0 hits) — GUI contract adopts the fork's real diagnostics (`source_profile="j0_radial"`, `source_profile_alpha`, `source_profile_path`, `source_profile_face_count`, `assembly_path`); naming decision logged as an ISSUES item for the WP16 lane. (b) `solve.near_correction*`/`solve_precision` ride `SolveSpec.extra` (solve-hash-distinct) but are NOT echoed into `Response.meta` — GUI reads config.yaml meanwhile; per-row echo is a WP14-lane ask. (c) mesher enclosure keys verified in the fork at the real names (HornEnclosure `depth_mm`, `space_l/t/r/b_mm`, `edge_mm`, `edge_type`, `plan_type/plan_n`, enc front/back resolution) — brief-mounting scaffolding will be speced against these, never invented. (d) `verify` is NOT a GUI job kind (allow-list gap) — planned addition, contained in jobs.py:113-141.
- **Deliverable:** `docs/GUI_INTEGRATION_PLAN_2026-10-25.md` — §2 per-WP capability/status table; §3 feature-by-feature GUI hooks (restarts strip, provenance badge matrix = visibility-distinct solve-group fingerprint `(backend, mesh_policy, near_correction, solve_precision, source_profile, mounting, objective_version, grid identity)`, compare mixed-key warns, STEP face-label inventory + tool SHA, bake-off view per ATH D20 spec verbatim); §5 API contracts C-1..C-6 keyed to `run_archive`'s `available:false` honesty pattern; §8 phased build order G1-G6 with per-phase offline test recipes (test_gui.py fixture/server/_req conventions + node --check); §10 GUI_CONTRAST_PLAN compliance inheritance; §13 in-flight disclosure. INDEX/CODE_MAP lines + ISSUES local-only block in the same commit set.
- **Oracle pre-commit review: GO-with-fixes, all applied** (6 MUSTs: fork-state correction — WP16 committed+pushed `f4ef05c`, checkout moved to wp17-cuda-near with fresh WIP; f11 caveat sentence re-attributed to the brief-header/CONTINUITY rule, not report/html.py; WP14 STEP face labels are presentation-style only — tag mapping is the adapter lane's, sidecar "tag" field removed; mixed-grid refusal anchor corrected to `cli.py:1037-1041`; §13 disclosure completed incl. `tests/test_design_generators_grid_half.py` + untracked `examples/briefs/user/7040.yaml` + this commit's docs set; INDEX "Oracle-reviewed" phrasing fixed to chronology; 7 SHOULDs also applied: `run.json.config` key name, save_user_brief file naming + schema-tolerance lane condition, C-6 reader-extension note, bake-off wall-clock rule attributed to this plan, C-5 extension whitelist, WP16 repo-side ride-key absence verified-rg=0, verify-kind refusal-path test note).
- Docs-only: no code, no configs, no tests, no GPU; suite state unchanged from M5 (1234/0/1/0, intended `test_mesh_pin` tripwire).

## 2026-10-25 (local, ~09:00 EDT) - M5B LANDED: WP14 multicell CATEGORY (CAD→STEP route) + WP16/17 fork branches validated on the GPU + fork HOSTED + pin moved there (the test_mesh_pin tripwire RESOLVED) + M4 debts finished; multicell physics DEFERRED (owner)

- **Owner gates (chat, 2026-10-25):** "do WP14" + "do whatever we need to do for WP16/17 — push the fork to our GitHub" + autonomy ("skip overconstrictive fork rules; best practices") + "table the multicell troubleshooting for now; landing the category is cool" + briefs deferred. WP12 proceeds per plan; **WP13/P6 stay explicitly owner-gated (not covered by any of the above).**
- **Fork hosted:** `https://github.com/llevaachingada/hornlab-beat-bem` (public, GPL-3.0, full history; gh auth `llevaachingada`). Branches: `hornlab-search/base` @ `38544d2` · `hornlab-search/fused-cuda` @ `fa99ee5` (WP15) · `main` @ `38544d2` · tag `v0.2.0` · `hornlab-search/wp16-source-profile` @ `f4ef05c` (WP16, linear on fa99ee5 — documented ladder deviation: the fused driver path lives below) · `hornlab-search/wp17-cuda-near` @ `760a1ec` = **THE PIN** (WP15+16+17 stack); branch tip `a40a204` = test-env-only CUDA@6.2.0 registration (NOT pinned — the runtime Project.toml must not drag CUDA into the CPU backend). Fork validation commit + pushes owner-delegated (FORKS.md updated).
- **WP16 — `source_profile_alpha`** (fork `f4ef05c` + search-side key this pass): per-face `1 + α·J0(j01·r/r0)` on tag 2, j01 = `J0_FIRST_ZERO` = 2.4048255576957728, volume-velocity-normalized, fused-CUDA only (two gates + loud refusals + path-proof diagnostics), α=0 = bit-for-bit. Search side: `solve.source_profile_alpha` optional key → solve-spec `extra` when set → `SolveConfig(source_profile_alpha=…)`; non-beat/non-fused use refused pre-import with the library's rationale; absent = byte-for-bit. `cuda fused WP16 source profile driver path | 9 9 1.5s` green on GPU.
- **WP17 stage 1 — near-singular correction on the fused CUDA path** (fork `760a1ec`, THE PIN): allowed ONLY cuda + fused flag + NO symmetry/ground (single-image-near hazard refused otherwise, rationale quoted); wire-through `near_correction_enabled/cutoff/order` + the assembler's pre-existing `near_correction_cache`/`device_near_correction_cache`; diagnostics `near_correction_applied/pair_count/…` + `assembly_path="fused_cuda"`; off = no keys anywhere. End-to-end spot on the installed wheel: **11,276 near pairs**, VRAM 1100→1343 MiB. `WP17 near-correction gate | 155` + thin-septum parity `12` + `cuda fused WP17 near-correction driver path | 10` green. Stage 2 (fused + per-image symmetry caches) = designed-out, refused until built.
- **WP14 category LANDED (offline; build123d 0.13.0, extra `cad`):** `tools/cad/multicell.py` (closed air-volume solid; labels via OCC `STYLED_ITEM` styles — build123d's own writer measurably CANNOT carry them; round-trip proven 54/54 through the mesher's own parsers + a real gmsh import); `mesh/step_build.py` (recipe → labelled STEP → gmsh OCC import → `driver`→tag 2 / `wall`→tag 1 → 2D mesh → mesher repair + frequency validation → metres `.msh` → our topology/bbox/tag/dof guards); `build_mesh` third route + strict `FREEFORM.cad` 11-key recipe branch (septum ≥ 1.5 mm); GRID/cad `export_step` → clean `GeometryInvalidError` (M4 debt); `solve.{near_correction, near_correction_cutoff, near_correction_order, solve_precision}` keys (CPU-arm plumbing, absent = bit-for-bit, beat-only with surfaced refusals); record honesty (cad rows: `grid.available=false` + additive small `cad` echo — tool sha + recipe + step sha + face inventory); `examples/typologies/multicell_3x3.yaml` (+ cad `cad_3x3_probe` artifacts). Focused: CAD 5/0 · STEP 108/0 · echo 38/0 · near-keys 56/0 · WP16+CLI 89/0.
- **M4 debts finished** (this pass): GRID STEP-export refusal (clean `GeometryInvalidError`); GUI `list_configs` seed-gate memoize (measured cold 1830.9 ms → warm 110.8 ms, 37 configs, byte-identical, invalidation tested); GRID mesh-cache design sketch at EOF of `mesh/grid_build.py`; saddle mesher-warning recorded in `examples/typologies/salmon_saddle.yaml`'s header + asserted by test.
- **CLI bug fix:** `_cmd_selftest`'s GPU-refusal path no longer force-kills other jobs' BEAT hosts (`worker.shutdown` only when the lock body was entered; success path unchanged per rule 6). Tests: refusal = exit 3 with ZERO shutdowns.
- **Validation ladder on the landed pin (all [measured], one GPU job at a time):** Julia full suite **46/46 testsets** on the RTX 4060 incl. ALL FOUR CUDA testsets (production 27, fused driver 6, WP16 9, WP17 10) — 0 Fail/Err/Broken/Skip; `selftest --analytic` **PASS** (R(ka) spread **0.020 dB**, bar 0.5; the CPU convergence level "not demonstrated" — the reinstall invalidated beat_cpu readiness, the M2-form caveat, disclosed; re-provision = cheap follow-up); `selftest --crosscheck` **0.0390 dB** (= the M2 base reference, bar 0.2); 3-arm A/B vs stored base-pin runs worst **4.94e-06 dB / 3.56e-05 deg** (bar 0.039 dB / 1° — 4 orders inside; arms `osse_axi seed d04e8697a87d`, `fed761193da7`, `sculpt 892bb3551903` vs `2002c3`/`fed761.ndjson`/`03d787`); offline suite **1325 / 0 / 0 / 0 — the FIRST fully-green suite: `tests/test_mesh_pin` 1 passed** (installed == pinned; the documented resolution moment per docs/FORKS.md); compileall clean.
- **Multicell physics DEFERRED (owner)** — the focal pair (CPU near+double vs CUDA, same mesh, 4501 dofs, 12 freqs) gated **NOT ALLOWED** (on-axis 11.28 dB / DI 14.59 dB / bw_v 159.1° vs the 0.2 dB bar) and the deferred diagnosis reframes it: the fixture's mouth is a rigid `wall` + the driver is a REAR disk facing −z → the pipeline measured **diffraction around a closed body** (throat impedance = free unbaffled disk in BOTH arms; DI negative in both = the rear-facing signature) — no far-field metric of this fixture is horn evidence; the 4 kHz gate is unanswerable (mesh validator's global ceiling 2891.68 Hz); re-gate = mouth-topology fix + valid-band, non-threshold metrics (bw_v 180° saturations are −6.0206 dB threshold flips). Attribution ranked (#1 = arm-A's near-correction omission ~O(10⁵) septa pairs → WP17, now landed, is required for multicell GPU screens). Evidence preserved: `runs/m5_wp14_focal/*` + re-captured compares + the ISSUES deferred block with the full resume recipe. The isolation lane was cancelled mid-run at the owner's request (arm C's logs exist, arm D config only — no conclusions drawn).
- **Housekeeping of record:** the owner's own GUI campaign (75x35, 4 organic families) was killed at their explicit request after GPU-lock contention (lock holder + children + 2 BEAT hosts; GUI left running; dirs stand as interrupted); one A/B compare and two selftests were re-captured under the ceremony for bytecheck sources.
- **Evidence:** `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md` — byte-check `tools/evidence_bytecheck_m5b.py` **33/33 PASS**; INDEX/CODE_MAP updated here.

## 2026-10-25 (local, ~08:20 EDT) - M5 WP11 LANDED: restarts (IPOP/BIPOP) + CMA-ME QD atlas, offline-first + 4 GPU screens; owner gate "M5 go - WP11 only" in chat; Oracle GO-with-fixes applied

- **Owner gate:** "M5 go — WP11 only" answered in chat 2026-10-25 (gate A met at 0ee5a28). The brief-design consultation + owner-POC search stays the owner's call (deferred this session). WP16/17/13/14 NOT started this pass (WP16/17 gate B still unmet: fork GitHub hosting pending).
- **WP11a — `search.restarts: {mode: ipop|bipop, max: N}`** (search-only optionality key; ABSENT = single-ES bit-for-bit, tested incl. no `restart_*` dirs + unchanged run.json schema): manual restart loop around pycma's `CMAEvolutionStrategy` in `search/cma.py` — `_RestartSchedule` mirrors pycma's OWN schedule (installed-source line citations in the docstring; two deliberate divergences documented per Oracle: pycma's small-run maxiter cap omitted — the global eval budget governs; our `max` counts ALL restarts, pycma's counts only non-small). Each instance logs to its own `cma/restart_k/`; `n_new` (non-cached) is the SINGLE global budget: exhausted() before every candidate, partial batch never told, `stop="budget"` / all-natural → `restarts_exhausted`. Deterministic resume: cached rows re-told at zero spend; schedule decisions rebuild identically (tests pin row-sequence + schedule-tuple equality + no-double-spend vs the uninterrupted run). Offline suite + budget-exactness pinned (`1+10+20+40` accounting).
- **WP11b — `search.algorithm: cma_me`** via `ribs` 0.12.0 (PyPI distribution name is `ribs`; the `pyribs` pip name intentionally errors; optional extra `qd = ["ribs==0.12.0"]`): new `search/cma_me.py` dispatched from `search/cma.py` (cli.py UNTOUCHED; `search/evaluate.py` UNTOUCHED — stays pure dispatch). GridArchive + EvolutionStrategyEmitter (`es="cma_es", ranker="2imp"`, objectives told as -J since ribs maximizes), measures = NaN-safe in-band means of `MetricSet.bw_h_deg/bw_v_deg` over `cfg.target.band_lo_hz..band_hi_hz`, ranges pinned (0,180)° (the metrics' own units — data-independent/resumable). Artifacts: `archive.json` (full) + `archive_heatmap.json` (GUI-ready, EXACT pinned contract `{"bins","ranges","descriptors","cells":[{"h_center","v_center","objective","design_hash"}]}`, exact-key-tested) + `run.json` `qd` stats (cma_me only). Same budget semantics as cma.py (n_new global, no double-spend, deterministic replay resume). SolverUnhealthyError parity (streak 3).
- **Read-only GUI atlas view:** `server.py` GET `/api/archive/<id>` → `data.py::run_archive` (`available:false` empty pattern like `evolution()`; tolerates half-written files; ignores legacy aliases); `app.js` route `#/run/<id>/archive` + run-detail "QD atlas" button + plain-canvas 2D descriptor grid (axes labelled from `descriptors`, honest empty states); browser render NOT exercised live (route/reader tests + `node --check` only — owner 1-min check pending, ISSUES).
- **Config validation:** `search.algorithm` ∈ {cma, cma_me} (strict); `search.qd` optional block (descriptors from the shipped 2-name set, bins 2..64, all sub-keys required when present); `qd` REQUIRED with cma_me (refused loudly otherwise), `restarts` refused with cma_me; neither key touches solve-spec hashing (asserted). Both optional fields registered in `tests/test_config.py::OPTIONAL_FIELDS` (strictness-increasing registration).
- **Acceptance (WP11 bar: >50% of the cells a grid scan reaches), verbatim:** `ACCEPTANCE coverage: 49/64 scan-reachable cells = 76.6% (archive 49/64 bins, 160 non-cached evals)` — cheap 2-knob family, the test's 11×11 grid scan and the cma_me run share the same fake/bins (scan archive built cache-clean).
- **GPU screens (WP11 GPU half, after offline green):** 4 sequential real-GPU `search` screens on `examples\search_smoke.yaml` copies (only the `search:` block changed; no horn number is new; screen spec 3000 dofs / 73 angles / 700–4500 Hz): ipop 60/60 non-cached exact, bipop 60/60 exact, cma_me 60/60 exact (best J 9.31571; machinery proof — the atlas-quality claim stays the OFFLINE acceptance bar); **bipop_fired** (`tolfun` forced so natural stops fire): 4 ES instances (`restart_0..3`; BIPOP schedule visible on real solves: popsize/sigma {10, 0.25} → {10, 0.00278} → {20, 0.25} → {10, 0.00356}), 50 new-in-restarts + 1 seed = 51 = non_cached = rows, 9 evals correctly unspent at `restarts_exhausted` — the no-double-spend proof across multiple ES instances on the real solver. VRAM [measured] (rules 2/3/5, external sampler): baseline 430 MiB → peak 2305 MiB (fired job; post-job gpu-clean killed 2 BEAT hosts, rule-6 verified, 429 MiB idle after). **iper/bipop/cma_me per-job VRAM: MISSING — disclosed** (the screen lane never started its sampler; durable run.json artifacts carry their proof; re-run = ~4 min GPU each, owner's call).
- **Suite:** final tree (post-Oracle-fixes) full offline **1234 / 0 err / 1 fail (the intended `test_mesh_pin` tripwire: installed fork `fa99ee5` vs main pin `38544d2` — never hand-fixed) / 0 skipped** (`runs/m5_wp11/suite_final.xml|log`); compileall clean; +40 additive tests over M4's 1194.
- **Evidence:** `docs/evidence/M5_WP11_2026-10-25.md` (multi-lane interrupted-session chronology disclosed; every quoted block scripted by `tools/evidence_bytecheck_m5.py` — **30/30 PASS**).
- **Oracle pre-push review: GO-with-fixes** — docstring divergences + resume caveat applied in-pass; no frozen contract touched; `evaluate.py`/`cli.py`/`types.py`/`record.py` byte-identical; no test weakened/skipped. Process items: docs-in-same-commit (this commit) + `tools/launch_gui.ps1` stray decision (owner pending, left untracked).


## 2026-10-25 (local, day, later) - P6 implementation plan v1.0 written (docs-only; two deep research lanes; execution gated on WP1-WP17 completion + owner GO)

- **Two further research passes** ran in parallel (librarian lanes, web-only): (1) **superformula math + horn mouth theory** — quarter-domain symmetry rules (m integer and a multiple of 4 only; m1 = m2 required for quarter meshes [derived]; non-integer m = open/self-intersecting curves; odd m closes only if a = b and n2 = n3); the documented degeneracy to guard (`n1 < 2 AND max(n2, n3) > 10` = radiating-lines regime, Symmetry 2022); a/b are degenerate once width is normalized (fix a = 1, search the ratio); canonical Ath values quoted (User Guide §6.4.2 `GCurve.SF = 0.95,0.82,4,0.8,7,1.9`, Width 68 mm, Dist 0.5; CORE `sf(4,12,15,16,1,0.618,p)`; HornLab fixtures sf1/sf2); NO published claim that non-elliptical mouths raise HOMs (the defensible statement is gradual shape change along the axis); NO public repo searches superformula horn parameters anywhere (verified GitHub-wide — **a genuine first**); published superformula optimizations (QPSO antenna TAP 2025; GA shape search) show a local-minimum-riddled map → campaigns start from 3 hand-picked seed shapes. (2) **bake-off methodology + GSA implementation path** — fixed-budget primary endpoint with anytime-slice budgets {100, 200, 400} (one run, sliced); gap-closed normalization; 30 seeds surrogate-backed / 10-15 real-GPU (COCO power warnings stated); Wilcoxon rank-sum + Holm + Vargha-Delaney A12, ONE pre-registered endpoint; **GSA library audit: no maintained GSA in nevergrad/mealpy/pagmo, NiaPy ships a retuned variant, the canonical MATLAB port has no license → write our own ~120-line module with an 8-test suite and 10 pitfall requirements (each a named test)**; the crippled-GSA budget trap (canonical N=50/T=1000 at a 400-eval budget = 8 generations, Kbest un-annealed) handled by a mandatory offline N/g0 tuning stage; pre-registered decision rule (GSA replaces CMA-ES only on median + Holm p<0.05 + A12 ≥ 0.64 + feasible-best not worse + beats the LHS baseline, on ≥2 of 3 families); direct head-to-head evidence: none published (verified absence).
- `docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md` **REWRITTEN at the owner's request into P6 implementation plan v1.0** (dossier folded in, nothing lost): §0 executor read-me (file-ownership table, seam checks S1-S4, wave map, verification recipe) · §1 plain-language stories · §2 research basis (labels) · §3 settled design decisions D1-D20 (search boxes, guards, GSA config defaults, bake-off matrix, GUI behavior) · §4 work packages (WP-P6a-1/2, WP-P6b-1/2/3, WP-P6-GUI-1/2, WP-P6-4) · §5 verbatim dispatch prompts for FOUR parallel Wave-1 lanes with zero file overlap · §6 checkpoints CP-P6-0..CP-P6-4 · §7 risks/traps. GUI bits: mouth-outline polar preview on run pages (pure math from the design's gcurve params) + a `#/bakeoff/<id>` view (race curves median+IQR, final-best ECDF, box plots per budget, budget-normalized table, stats footnote).
- **Execution gates (both required):** WP1-WP17 complete (M5 + real owner briefs) + **owner GO** (P6a/P6b independently runnable). INDEX, NEXT_DEV_PRIORITIES P6, 12_RESEARCH_BASIS §11 companion line, ISSUES updated in this commit set. Docs-only: no code, no configs, no GPU. Committed and pushed with this commit (owner directive, 2026-10-25).

## 2026-10-25 (local, day) - docs-only research: ATH superformula + GSA-vs-CMA-ES added to 12_RESEARCH_BASIS §11 (owner-directed; collaborator conversation)

- **`docs/plan/12_RESEARCH_BASIS.md` gains §11** ("ATH, the Gielis superformula, and GSA vs CMA-ES") — the §10 dated-appendix precedent, **append-only, owner-directed; no frozen content touched** (the plan/ freeze protects parallel task agents; none read §11). Content: what the collaborator's "super equation by ATH" is (the **Gielis superformula**, verified against Batík's OS-SE paper + the Ath 4.8.2 User Guide: `GCurve.Type = 2` / `GCurve.SF` guiding curve, plus the ATH CORE `sf()` azimuthal wall-angle script; our mesher's OSSE `gcurve_sf_*` keys = the same knobs, ALREADY searchable design-space rows — the plan README's quick fork #2 now source-verified) + the OS-SE paper's eq. 5 (hyperbola + superellipse flare = the mesher's OSSE knobs) + the GSA-vs-CMA-ES evidence (**no published head-to-head [verified absence]**; GSA's documented premature-convergence/diversity weaknesses vs CMA-ES's small-budget strengths; Hansen §B.5 penalty guidance = our WP3 graded penalty; **CMA-ES stays the default**; fair fixed-budget bake-off protocol written down). §11 sources appended to the Sources list.
- **Companion dossier** (plain-language summary, repo code pointers, protocol detail): `docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md` (INDEX line added; cross-linked both ways). **Two PROPOSALS recorded as `docs/NEXT_DEV_PRIORITIES.md` P6 (owner-gated, NOT scheduled): P6a featured superformula campaign (config-only); P6b fixed-budget GSA-vs-CMA-ES bake-off.** ISSUES local-only block added with the open items: [1] ask the collaborator to spell **"AVE"** (nothing credible; likely ABEC/Ath4/Gielis); [2] OSSE name-expansion check (paper: Oblate Spheroidal + SuperEllipse vs MESHER_TYPOLOGIES.md's "Oblique Spherical Surface Element" — verify and date-correct); [3] Ath GCurve/Morph vs mesher `crossSection` surface equivalence (`beat_compat.md` node-cloud round-trip test) before any Ath-export claim.
- Docs-only: no code, no configs, no tests, no GPU. Committed and pushed with this commit (owner directive, 2026-10-25).

## 2026-10-25 (local, ~00:55 EDT) - M3 LANDED: carry-overs + WP5/WP7/WP8 calibration on STORED designs; ZERO new searches (owner directive); Oracle GO-with-fixes applied

- **Scope (owner directive 2026-10-24/25):** two carry-over fixes + WP5 calibration + WP7/WP8 speed checks, all measured on EXISTING stored designs in `runs/` — NO new searches (WP6 demo-sheet searches CUT; the proof-of-concept search on the OWNER'S OWN brief is the NEXT pass's first job); no M4+/fork work. Total GPU 728 s (~12 min), 17 jobs, no crash/OOM.
- **Carry-overs (commit `1dda493`):** dataset records carry an explicit top-level `objective_version` (absence-tolerant reads = v1; validation rejects non-int/unknown); the `invalid_envelope` deterministic-failure marker now STORES and REQUIRES `brief_hash` alongside `lib_shas` (the graded penalty already recomputed on replay — only the stale VERDICT was the hazard; proven by a new test where a different brief's envelope re-evaluates). +6 offline tests.
- **Framework keys (this commit; every key opt-in, ABSENT = byte-identical config/mesh/solve hashes, tested):** `solve.source_motion` (default "normal" = today; "axial" rides `extra` + is always sent to beat's SolveConfig; `Response.meta["source_motion"]`; bempp path raises a clear ConfigError); `mesh.rear_res_factor` (default 1.0; rear-ONLY scale at the `res_mm_for` caller — READ-FIRST honored: MeshDensity's `rear_res_mm` drives ONLY the outer shell + rear cap, acoustic bore/mouth/throat untouched; mesh-cache suffix `-rearN` + solve-spec `extra` when != 1.0); `mesh.band_split {edges_hz: [...]}` (per-band meshes via per-band `MeshSpec.f_max`, per-band solves, new `stack_responses` in solve/base.py with exact tiling assertions, verify-ONLY seam check into `Response.meta["seam_check"]`, provenance `mesh_policy: band_split_v1` in ndjson rows + record provenance). +24 offline tests.
- **WP5(a) distance (one traced solve per finalist, offline field eval):** traces ANSWER the arbitrary-distance question (validated vs the solver's own cuts at r=2 m: 1.3e-4/2.4e-4/2.0e-4 dB); |Δ beamwidth| 2→50 m > 1° in-band on ALL THREE (AXI/HV/RO bests 59f57bc457cb / fed761193da7 / 47e1259ad615); max |ΔDI| 2→50 m: 1.61 / 0.59 / 0.54 dB. **PROPOSE `distance_m: 10` for v2 briefs (owner gate)** — residual 2→10 m up to 8.66° / 0.86 dB (better, NOT converged).
- **WP5(b) balloon:** stored verify baselines are 23×45 = 1035 points (NOT 512 — the doc states this honestly). 512→1035 max |ΔDI|: **0.1545 dB** (AXI @ 7,567 Hz) / **0.1110** (HV @ 12 kHz) / 0.0786 (RO); 1035→2592 ≤ 0.0407. **PROPOSE raising the screen balloon to 1024 (owner gate)** — fires on AXI + HV.
- **WP5(c) source_motion axial:** AXI ≤ 0.0070° / HV ≤ 0.0036° above 5 kHz (≈5° throats ⇒ practically identical); RO (12.37° throat) up to 0.4331°/0.1647° bw + 0.0428 dB DI + 0.0406 dB on-axis @ 12 kHz (0.0016 dB over the on-axis bar, above f11). Measurement only, NO proposal mechanism; default stays "normal". **f11 = 7,914 Hz caveat printed at every 12 kHz number: 8–12 kHz compares GEOMETRIES, not drivers** (rigid uniform-velocity spherical cap).
- **WP7 rear_res_factor (AXI, screen spec, STORED 1.0 baseline reused — no new 1.0 solve):** 1.5 → 1,135 dofs (**−18.8 %**) PASS; 2.0 → 1,060 dofs (**−24.1 %**) PASS (top-5.5 kHz deltas 0.0989°/0.0431°/0.0116 dB/0.0106 dB — all inside the CP-7f bars 0.039 dB / 1° / 0.1 dB; J −0.00246/−0.00697). **PROPOSE `mesh.rear_res_factor: 2.0` (owner gate); 3.0 unmeasured.**
- **WP8 band_split edges [3000,6000] (AXI + HV, 12 kHz verify spec):** wall −53.5 % (29.64 vs 63.68 s) and −28.2 % (33.82 vs 47.08 s) vs the SAME-CODE single-mesh solve (band walls include the seam solves — the saving is understated); band dofs AXI 497/1,636/6,049 (band 2 IS the single mesh), HV 435/1,202/4,540. **BOTH FAIL the CP-7f acceptance bar** — in-band maxima AXI 1.2476°/1.2166°/0.1529 dB/0.4218 dB on-axis, HV 1.0957°/0.9259°/0.1021/0.4041; the failure concentrates in band 0 (band 2 is identical to the single mesh); seam deltas −0.237/−0.111 dB (AXI), −0.271/−0.043 dB (HV) live in `meta["seam_check"]`. **NO proposal, no config edit** — band-split stays opt-in machinery; adoption is an owner decision (band-0 fidelity must be addressed first).
- **Oracle verification (read-only, GO-with-fixes — ALL applied in this commit):** MUST-1 `rear_res_factor` now also rides the solve-spec `extra` so solve cache/failure markers/resume memo can never replay across factors (absent = byte-identical; tested incl. a bare extra-hash byte-identity assert); MUST-2 the evidence doc's false "no junitxml counters" claim replaced with the real suite files/counters; SHOULD §5.1 Band-2-dofs ambiguity closed + a seam-solves honesty note; SHOULD the `_persist` row echo pinned by tests; NICE a failed seam solve records `{"error": ...}` in meta (absence unambiguous) + a pre-M3-marker backcompat docstring line. Rulings: carry-overs PASS (brief_hash chain proven end-to-end); WP5 rules honest + costed, NO disguised default flip (examples/ diff empty); WP7 read-before-write honored, proposal-vs-adoption handled; WP8 seam/provenance/CP-7f wall-time PASS; evidence verbatim integrity PASS (~12 blocks byte-checked against the UTF-16 logs).
- **Suites:** focused post-fix subset **68 passed / 0 failed** (`runs/m3_code/suite_oracle_fixes.xml`); full offline at the FINAL state **968 tests / 0 errors / 1 failure (exactly the expected `test_mesh_pin` tripwire: installed fork `fa99ee5` vs main's base pin `38544d2`) / 0 skipped** (`runs/m3_code/suite_final.xml`); compileall clean.
- **Evidence:** `docs/evidence/MEASUREMENT_PACK_2026-10-24.md` (every table + verbatim log bytes; MISSING cells disclosed); raw logs `runs/m3_wp5a|wp5b|wp5c|wp7|wp8/` (gitignored); harness `tools/m3_measurement_pack.py` (INDEX/CODE_MAP updated).
- **Owner-gated proposals awaiting decisions:** `distance_m: 10` for v2 briefs; screen balloon → 1024; `mesh.rear_res_factor: 2.0`; NOT band_split. Plus standing: fork GitHub hosting + pin replacement; v2 default.

## 2026-10-25 (local, ~00:15 EDT) - two agent SKILLS landed (opencode project skills, after an Oracle hardening pass)

- `.opencode/skills/hornlab-gpu-job/SKILL.md`: the per-GPU-job operational recipe — concurrent-lane scan; stale-host/orphan rules; GPU-lock + exit-3 "GPU busy" semantics (refuse + exit 3, wait/never --force); fresh MEASUREMENT per process (searches legitimately reuse their warm worker) + the fresh-cache-dir rule (solve/mesh caches are NOT lib-SHA-keyed — stale entries silently serve old-solver responses as "new"); doctor preflight incl. the FORKS tripwire expectations (pinned-shas WARNING + test_mesh_pin failure = intended guard on fork lanes, never hand-fix); PS 5.1 Tee UTF-16 + the pytest count-line gotcha (junitxml counters; marker expressions for offline/GPU suites); generous timeouts (cold Julia start; memory-pressured assembly); post-job verified shutdown + rule-7 clean-state reproduce.
- `.opencode/skills/hornlab-evidence/SKILL.md`: evidence assembly — honesty labels ([measured]/[inferred]/PROVISIONAL), decode UTF-16 logs, junitxml counters, RECONSTRUCTED-invocation + elision labeling, baseline+peak pairing, caveat quote-through, fork-ladder SHA provenance, docs/evidence/README.md commit rules, and the pre-publish BYTE-CHECK: EVERY quoted block scripted against its source log, unverified blocks disclosed.
- `.opencode/skills/hornlab-typology-research/SKILL.md` (third skill, oracle-hardened GO with 9 edits applied): the horn-DESIGN grounding protocol — outside research on a typology itself (primary white papers; construction math + a numerical reference case; strengths/weaknesses/design issues; optimization knobs + ranges; practitioner ranking practice; designer/user experiential reports) into a 9b.0-style sourced dossier BEFORE typology/shape code. Anti-overconstraint devices (the owner's explicit worry): inventory-before-fetch with a CITATION outcome when WP9b/appendix research already covers the family; a MINIMUM-viable dossier bar (one primary + one reference case + knob ranges; 9b.0–9b.5 is the ceiling, not the floor); named exemptions (routine config keys, GPU/evidence/orchestration, WP10 ADAPTER mechanics, bounds tweaks re-anchored to the dossier's ranges); corrections culture preserved (raw appendices byte-for-byte; corrections dated in the CONSUMING doc per 02 s7); R9 clarified (Le Cléac'h-specific; the rename gate is its general form) and hypothesis shapes allowed as labeled experiments (the x_shape/T5 precedent). Triggers: typology/generator/grid-shape-law/mounting/multicell/septa/brief-for-new-typology work + new-acoustic-priority objective terms. AGENTS.md + CLAUDE.md both carry the "Research grounding" block (own section after the three silent killers) incl. the lane-role fallback (lane agents without skill access apply the paragraph + the WP9b 9b.0 standard inline) and the two sibling skills' names.
- Both Oracle-hardened (GO): ONE must-fix applied (the "one solve per fresh process" line was WRONG — one MEASUREMENT per fresh process; a search/campaign legitimately reuses its warm worker; obeying the draft would break every search loop) + one weakening removed (byte-check ">= 3 blocks" → EVERY block scripted). No machine numbers in either skill (TOOLCHAIN.md owns them) — rot-resistant; the fused-specific knowledge stayed out except the generic refusal pattern (a solve refusal naming gpu-clean = stale-host instruction, clean + re-run once).
- Registration: opencode project skills auto-discover `.opencode/skills/<name>/SKILL.md` (verified via customize-opencode); applied on the NEXT opencode run (running sessions keep loaded config).
- **OWNER FLAG (slim-preset gating):** `.opencode/oh-my-opencode-slim.json` gives the ORCHESTRATOR `skills: ["*"]` but fixer/explorer/librarian/designer/council roles `[]` — lane sessions never see these skills when they run as non-orchestrator roles. Options: add `hornlab-gpu-job` (and `hornlab-evidence`) to those roles' arrays (one-line config change each) or keep embedding the ceremony in dispatch prompts. Owner config decision; mirrored in ISSUES.
- **NEXT_DEV_PRIORITIES updated (owner request, ~00:30):** new **P5 section** — the build-decision easy wins NOT in the WP plan: W1 screen-vs-verify rank-consistency audit (offline, zero GPU; the rescore pattern), W2 the dense finalist resonance net (= P4a, now SCHEDULED as the brief-design pass's POC build-gate), W3 denser screen grid as a NEW NAMED grid group (frozen-contract; owner-gated), W4 `compare --bar` judge mode (~20 lines, removes the eyeball step hit 3× in M2), W5 perceptual `freq_weights` emphasis + M3/WP5 calibration defaults in the owner baseline doc (config-only). The same commit carries the OWNER's P4 note verbatim (its first commit) — the "dangling P4 reference" advisory in ISSUES is RESOLVED. **W6 (added late, then corrected by recon):** a BL-class balloon VIEW in the GUI; the owner directed "study BL's newest balloon-display source on GitHub and follow it" — recon done: BL's balloon is a **dB-to-radius BLOB** (radius = max(spl−floor, 0); shape AND color encode level), PyVista/VTK smooth-shading + turbo, white tubed isobar rings, protractor, a radar slicer (barycentric meridian interpolation) and an isobar freq×angle slice; ours will be an OWN web implementation (three.js r160, vanilla JS, GPL attribution) — designer lane dispatched (gui/** scope only, no conflict with the in-flight M3 lane).

## 2026-10-24 (local, ~23:59 EDT) - NEXT TWO PASSES HANDED OFF: M3 reshaped (zero searches, owner directive) + brief-design consultation committed

- **Owner ruling (late 2026-10-24): the shipped demo briefs are NOT their design intent — never spend GPU searching demo sheets.** M3 RESHAPED accordingly, handoff text issued VERBATIM IN CHAT (the owner holds it): two carry-over fixes (dataset-record `objective_version` field; `invalid_envelope` memoization = brief_hash into the failure marker's replay-validity, Oracle-ruled one-liner) + WP5 measurement pack (2/10/50 m via ONE surface_traces solve per finalist + offline math; balloon 1024/2592; source_motion axial — PROPOSALS ONLY, owner gates every flip) + WP7 rear-shell check (1.5/2.0 vs the stored 1.0 baseline on osse_axi best; READ-FIRST the mesher's MeshDensity rear surfaces) + WP8 band-split check (2 designs vs STORED single-mesh responses; seam checks; `mesh_policy: band_split_v1`) — ~15–20 GPU solves on STORED designs, zero new searches. WP6 demo-sheet searches CUT: the 12 kHz capability is banked (M2's fused verify); screen economics: 12 kHz screens just fit the 5,000 cap (~45 s/candidate), 14 kHz blows it and ~2× per candidate above f11 with no realism gain (band stays 700–12,000; a screen-cap raise for band_hi > 12,000 is OWNER-GATED).
- **Brief-design pass handoff committed as a file: `docs/HANDOFF_BRIEF_DESIGN_2026-10-24.md`** — the study list (every doc with what it teaches, incl. the white-paper appendix chain + the CORRECTION that the Boundary Lab source checkout `JWSound/boundary-lab` is no longer on disk — BL knowledge lives in the committed `docs/research/boundary_lab_0.5/*` + integration docs); the machinery-in-one-page explainer table; the 10-question OWNER INTERVIEW protocol (verbatim capture into `docs/BRIEF_SESSION_<date>.md`); the real-driver web-grounding lane (spec sheets → brief keys → f11 per driver → `docs/DRIVERS_<date>.md`); deliverable = 2–4 owner briefs + a baseline-settings doc, offline-validated (loads → compatibility → dry-run → CPU sample meshes → owner approval sheet); GPU = ONLY the owner-approved POC (budget 20 + one fused 12 kHz verify).
- **Sequence: M3 (GPU) runs first; the brief-design pass follows** (its WP5 calibration proposals feed the baseline settings). **GROUNDING AMENDMENT (same evening):** the handoff now carries the full capability map — section 2b: what each remaining pass (M3 in flight → M4 → M5) adds to the machine (WP9 generators, WP9b T1–T7 JMLC/Kugelwellen/organic/X, WP10 GRID Fourier sections, WP12 mounting, WP11/14/16/17) and what each BRIEF must anticipate now (briefs are family-agnostic — allow-lists live at launch; envelope variants for curls designed ahead; `mounting:`/`>12 kHz realism`/multicell are owner-appetite NOTES today, real brief keys only when their WP lands); four hard forward-compatibility rules (landed keys only — no invented keys; stated allow-list assumption; future-pass brief updates pre-planned; numeric claims re-grounded against the freshest evidence). §0 updated to the in-flight reality: study immediately, interview/commit ONLY after M3's GPU chain ends (`1dda493` carry-overs already landed).
- Note: `12_RESEARCH_BASIS.md` EXISTS (older INDEX/glob quirk this session); Boundary Lab + Magnus's repos referenced with verified paths (forks on disk; BL source checkout missing — owner to restore if wanted).

## 2026-10-24 (local, ~23:00 EDT) - M2 LANDED: WP15 fused CUDA validated on the GPU; measured ceiling 15,984 (safe 12,000); 12 kHz verify on the flag

- **Install (FORKS.md step 4):** the fork branch `hornlab-search/fused-cuda` @ `fa99ee5` installed by SHA into `.venv` (`direct_url.json` verified); re-provision not required (backend cuda ready); first GPU job recompiled the Julia caches (minutes, expected). Doctor 11/11 with the EXPECTED `pinned-shas` WARNING (installed fork ≠ main's base `38544d2` pin) until the dev-branch pin.
- **Validation ladder** (clean GPU state per job, `gpu-clean` before/after): `selftest --analytic` R(ka) spread **0.020 dB** (bar ≤ 0.5; identical to the base-pin reference 0.020); `selftest --crosscheck` overall max **0.0390 dB** (bar < 0.2; identical to the reference 0.039). Both at the fork's default (flag off) — upstream behavior intact.
- **3-arm A/B vs the base pin's stored runs (flag off):** osse_axi seed `d04e8697a87d`, perturbed_osse_hv best `fed761193da7`, freeform_sculpt seed `892bb3551903` re-solved via `run` + FRESH per-arm scratch cache dirs (**recon finding: the solve/mesh caches are NOT keyed by lib SHA — a plain run would have been a silent cache hit serving old-SHA responses**), then `hornlab-search compare` vs the stored runs: design hashes match, max diffs ≤ **2.9e-6 dB** / ≤ **2.1e-05 deg** (ladder bars 0.039 dB / 1°). A/B arms proved `lib_shas.hornlab_beat_bem = fa99ee5…` + `cuda_fused False/absent` in config, run.json and every response.npz meta. This IS the work-order step 8 old-path proof.
- **Fused GPU test** (`tests/test_solve_beat_fused_cuda.py -m "slow and gpu"`): `[measured]` fused-vs-default on the CP seed quarter mesh @ 2 kHz: on-axis max diff **0.0000 dB** (bar 0.01), bw H 76.65→76.65 / V 84.18→84.18 (bar 0.1), z_throat rel **3.35e-07** (rtol 1e-3); the **stale-host fused REQUEST** (fused ask against a host spawned before the env) was **REFUSED** with a `fused`-named message. First run FAILED only on the second test's zero-tolerance assertion — see next line.
- **Determinism finding (rule-7 evidence trail):** `np.array_equal` bit-identity between two flag-off solves is UNATTAINABLE on this stack — reproduced on the fork (~9e-8 dB) **and identically on the BASE PIN `38544d2`** after a rollback reinstall + rerun (~1.6e-7 dB), worst observed across runs **1.74e-05 dB** (Float32 CUDA reductions, order-varying). Pre-existing upstream physics — NOT introduced by the fork (consistent with the A/B arms' ~1e-6 floor). The assertion was rebarred to a documented floor: **max |Δ spl_h_db| ≤ 1e-4 dB** with a `[measured]` print and the full evidence in the docstring (NOTES_FOR_SENIOR 2026-10-24 block). The fused-vs-default bars (0.01 dB / 0.1° / rtol 1e-3) are untouched. Oracle adjudication recorded below.
- **Ceiling re-measure** (TOOLCHAIN M2 protocol via `tools/measure_fused_ceiling.py`: one solve per fresh process, threaded external nvidia-smi poll, baseline recorded, verified shutdown, `gpu-clean` between points; @ 1 kHz, 73 angles, no balloon): **fused FITS 15,984 dofs** (peak−baseline **7,637 MiB** — assembly already memory-pressured at **437 s/freq**) and **FAILS 20,237** (BEAT worker-host DEATH on the attempt AND the in-process re-warm retry; peak 7,831 MiB — the clean-state re-confirm was interrupted and the sweep capped per owner: **no 24k point**; the 20,237 failure stands PROVISIONAL). Old path on the SAME 8,919-dof mesh: **7,389 MiB / 59.6 s** vs fused **2,217 MiB / 9.1 s** per frequency. The "~20k inferred" did NOT materialize on this card/protocol (inference vs measurement noted honestly). Measured SAFE value → **verify/final dof caps 12,000** (12,183 dofs measured: 4,744 MiB, 13.72 s/freq — fast, ~3.4 GB headroom). Calibration caveat: TOOLCHAIN M1's res→dof table measured a SMALLER horn (its full-domain 12/6 = 5,524 tris); the `osse_baseline` seed at quarter 3/1.5 mm meshes to 87,240 tris / **43,993 dofs**, so the sweep calibrated mouth-res per target: 6.72/5.74/5.02/4.45 mm (verified via `--mesh-only` probes).
- **New configs (nothing edited; all load, verified):** `examples/osse_baseline_fusedcuda.yaml`, `examples/typologies/osse_axi_fusedcuda.yaml`, `examples/typologies/perturbed_osse_hv_fusedcuda.yaml`, `examples/freeform_sculpt_fusedcuda.yaml` — caps **5000/12000/12000** + `solve.cuda_fused: true` (hash only moves when the flag is set) + provenance headers.
- **12 kHz verify on the flag** (ONE verify job; runs `20261025T012944Z-screen-f576b4` → `20261025T013051Z-verify-be4adb`): osse_axi seed via the fused config; `verify --brief examples/briefs/axi_90x90_1in_12k.yaml --top 1` → verify J **17.0339** (balloon DI; NOT comparable with screen J — different band/grid), **4,438 dofs / 8,626 tris** (epw rule chose the size; finished below the raised 12,000 cap), **52.89 s solve / 25 freqs ≈ 2.1 s/freq**, response.npz `cuda_fused: True` + **25× `assembly_path: "fused_cuda"`**. **f11 = 7,914 Hz caveat (mandatory): 8–12 kHz compares GEOMETRIES, not drivers** (rigid uniform-velocity spherical cap source).
- **Suite:** on the dev-pin tree `pytest -m "not slow and not gpu and not crosscheck"` = **938 passed / 0 failed / 0 errors / 20 deselected** (junitxml `suite_dev.xml`, 217.9 s; total collected 958). On the main tree (base pin) the same selection shows exactly the INTENDED tripwire failure `test_mesh_pin` (937 passing + the pinned-SHA guard; observed in every run this pass) — it goes green when the owner lands a hosted pin (or the base pin is reinstalled). Selection vs M1's 935: +3 = the four new `_fusedcuda` configs' parametrized sweeps + the concurrently-landed GUI-contrast lane's tests. Nothing loosened; known capture artifact: this console's `2>&1 | Tee` drops pytest's final count line (junitxml + short-summary lines are the authoritative counters; noted in NOTES_FOR_SENIOR).
- **Pin policy (owner rule):** `pyproject.toml` + `TOOLCHAIN.md` pinned to the fork URL @ `fa99ee5` committed ONLY on **`dev/fused-cuda-pin`** (commit `65c03de`, parent = main's `5875fde`; **LOCAL ONLY — not pushed, not merged**). A `file://` pin must never reach `main`. **GitHub fork hosting + replacing the dev pin = OWNER ACTION — asked below.**
- **Concurrent lane note:** the GUI-contrast implementation lane landed + pushed its six phases (`main` `3f6aa16..5875fde`) DURING this pass (owner-approved; zero solver-code overlap; my uncommitted M2 tree never conflicted; suites reflect the merged tree).
- **Evidence:** `docs/evidence/FUSED_CUDA_2026-10-24.md` (every number pasted from `runs/m2_fused_cuda/*.log`); CODE_MAP/INDEX updated (harness + evidence + configs).
- **Oracle verification pass (pre-push, in this commit): GO.** Must-fixes (all doc-only) applied: (1) docs/INDEX verify line was stale ("12 kHz verify pending" → DONE); (2) the evidence doc's self-contradicting "not in this document / PENDING" pointer removed; (3) this verdict block; (4) the determinism docstring now carries ALL THREE measurements (fork ~9e-8, base-pin ~1.6e-7, rerun 1.74e-05 = worst) and the honest margin wording (~5.7x above worst, not "three orders"). Rulings: **ladder SUFFICIENT** for WP15 acceptance at the chosen caps (the provisional 20,237 failure sits 66 % above the 12,000 cap and does not gate it; only if >12k data is ever wanted: a clean-state 20k confirm + the hosted pin; M3 watch-item: one balloon-on probe near the cap — the ceiling points ran balloon=False); **ceiling honesty PASS** (no overclaim; provisional status + interrupted clean-confirm + no-24k all stated); **determinism rebar PASS** (base-pin reproduction decisive; not rule 8; no better alternative on this stack); **dev-branch pin confirmed ISOLATED** (diff touches ONLY pyproject.toml + TOOLCHAIN.md on `dev/fused-cuda-pin`; main's copies unmodified; the pin cannot reach the M2 commit; branch not on origin); **evidence byte-check PASS** (every quoted block faithful against the UTF-16 logs; elision/advisory notes applied to §6.2/§9); **`invalid_envelope` memoization correctly DEFERRED** (mechanism verified in evaluate.py: verdicts are failure-marked with lib_shas-only replay validity — M3 fix: add brief_hash to the marker's replay-validity, one line; the graded penalty is recomputed with the current cfg on replay so J stays consistent); **deferred-to-M3 items carried correctly** (both named in ISSUES + Next). Owner advisory from this pass (pre-existing on origin/main): the night entries reference `docs/NEXT_DEV_PRIORITIES.md` section P4, which exists only in the owner's local uncommitted note.

## 2026-10-24 (local, night) - frequency-grid blind spot + two grid-density ideas recorded (docs-only, no code)

- **User concern confirmed:** the screen grid solves only 12 log-spaced frequencies (500 Hz–~5.5 kHz on this card), verify 25 — a horn with a NARROW-band defect (mouth-reflection resonance, organ-pipe mode, narrow cancellation, e.g. a collapse at 550 Hz) can fall entirely BETWEEN two solved test tones; nothing is simulated between grid points, the interpolated polar/beamwidth plots render smoothly through the defect, and the objective cannot score what was never solved — so a peaky horn can outrank a clean one. Written to `docs/ISSUES.md` (local-only TO-DO) and `docs/NEXT_DEV_PRIORITIES.md` as new section **P4** with two sub-ideas:
  - **P4a dense finalist resonance net** (recommended first, no contract change): re-solve the short-list only on a dense in-band grid and diff vs the sparse metrics; auto-flag families whose dense J degrades.
  - **P4b perceptually weighted non-uniform grid** (idea only, FROZEN-CONTRACT matter): extra solved points at ear-critical regions (~2–3 kHz, ~4–5.5 kHz, possibly 0.5–1 kHz onset); requires an owner-approved amendment of frozen 01_CONTRACTS §8 as a NEW NAMED grid group (the `*_12k`/WP4 `verify_hf` pattern), never a free-form YAML key (2026-10-13 ruling; mixed-grid records can't train together).
- Related landed work NOT to be re-derived: WP4 `verify_points_per_octave` (verify-only, >5 kHz), WP4 v2 `freq_weights` (reweights solved points only), `docs/research/TIME_DOMAIN_RINGING.md` (time-domain alternative). Both P4 items are UNSCHEDULED and await an owner decision; no code, no contract, no planned-work text was changed.

## 2026-10-24 (local, evening) - GUI contrast & form-visibility plan proposed (docs-only, no code)

- **Audit:** the GUI's visual surface was audited against rendered dark-theme screenshots (headless Edge + SwiftShader captures of Home/Runs/Run-detail/3D/Campaign/Typologies at 1440×900 and a full-height run-detail capture; exact pixels sampled). Measured failures: dark-theme primary button text 2.07:1 (WCAG fail); hairline rules 1.36:1 (table separators/card borders invisible); the wall cross-section's "filled" legend is a no-op (fill renders identical to plot background; the merged H+V stroke ribbon hides outer shell / inner wall / rear as one clump) and the dashed amber start profile is ~90 % occluded beneath it; the micro-label tier (table headers, stat labels, chart ticks/legends) is the least readable text in the app; the 3D horn's unlit side merges into the near-black canvas (flat single-key lighting, no fill/rim, no shadows, orphaned `seedCol`); isobar white contours vanish over warm colormap bands; budget-over-limit (`151/150`) renders without a warning while AT LIMIT is flagged; theme-toggle first click is a no-op on dark-OS and chart-bearing pages keep stale theme colors after a toggle.
- **Plan:** `docs/GUI_CONTRAST_PLAN.md` — six independently committable phases (1 tokens/type tiers → 2 theme-boot fixes + `?theme=` deterministic-capture override → 6 semantics/over-budget flag/test widening → 3 chart-contrast pass → 4 `wallSection` redesign (three-pass z-order, real wall fill, throat marker, readable axes) → 5 3D light-gray horn (`#dfe4e8` MeshStandardMaterial) + hemi/key/fill/rim rig + optional shadow-mapping toggle; ≈ 3.75 agent-days). Per phase: measured acceptance criteria, implementation notes with file:line + do-not-touch lists, rollback notes; plus a 10-item risk register, edge cases, the verification recipe (`?theme=light|dark` headless-Edge captures + pixel sampling, `pytest tests/test_gui.py -q`, node --check + `evolution.js` added to the parametrization), and a WCAG acceptance table. Constraints honored: no new runtime deps, no build step, Three.js stays r160 via the pinned import map, the 2D SVG fallback stays functional, zero changes to server.py/jobs.py/data.py.
- **Process:** designer authored the plan from the screenshot evidence, then hardened it (added acceptance/rollback/risk/edge-cases; fixed a latent v1 bug — light-theme 3D canvas `#ffffff` would have scored ≈1.2:1 against the pale horn, replaced with `#e9edf0`). Oracle independently re-verified ~40 file:line anchors and recomputed every WCAG ratio by hand: verdict COMMIT-READY after 5 MUST fixes (self-failing `--band` alphas, a phantom "conditional localStorage write", restore-after-async-route, missing shadow `normalBias`, a self-contradictory even-odd fallback rule) + 11 SHOULD + 7 NICE — all applied.
- **Status:** implementation underway on owner approval (docs/research WP15 steps 8-12 runs concurrently in a disjoint code surface; pushes sequenced).
- **Phase 1 landed (this commit):** token/type tiers in `app.css` — new `--label` (#46535e/#b3bfc6, 11 label-tier selectors moved off `--muted`, 0.66rem floor), `--rule` #a9b4bb/#40505b (1.36:1 → ~2.1), `--band` rgba .32/.30 (was .08/.09), `--on-accent` (#fff dark #0e1418 — dark primary button 2.07:1 → 9.0), `--accent-strong` hover replacing `opacity:.88`, `--warn-soft`/`--bad-soft` tokens replacing the rgba(168,102,27,…) orphans in `.alert.warn`/`.alert.error`/`.gpu-busy-note`/`button.danger:hover`, plus the Phase 6 CSS one-liner `.progress-bar.bad`. Both dark blocks (prefers-color-scheme + `[data-theme=dark]`) kept character-identical; braces balanced 284/284. Evidence: `pytest tests/test_gui.py -q` 30/30 (baseline 30/30 before any edit).
- **Phase 2 landed (this commit):** theme boot + capture correctness — boot order now `?theme=light|dark` URL override → stored pref (try/catch) → OS prefers-color-scheme fallback; the toggle flips from the *effective* theme (first-click no-op fixed) and always writes `data-theme` + localStorage; `route()` returns the view promise; theme-change observers snapshot scroll + filter inputs, `await route()`, restore with one rAF retry (async views render after the route returns); the `matchMedia` handler is skipped when `data-theme` is pinned; every localStorage access wrapped in try/catch. Evidence: joint pixel check — `?theme=light#/home` header bg `244,246,247` (`--bg` light) and `?theme=dark#/home` header `14,20,24` (`--bg` dark): the override deterministically renders both themes; `pytest tests/test_gui.py -q` 30/30. Manual click-path checks (first-click switch, per-view recolor, scroll/filter restore) left for the owner's next GUI session.
- **Phase 3 landed (this commit):** chart-graphics contrast — isobar contours now two-pass (dark `#10181d` halo @0.55 under white 0.98/0.8 cores; widths 3.4/1.8 for −6 dB, 2.6/1.1 for −3 dB; halo composite ≈3.7:1 over #FFDF00, white core ≈5:1); isobar gridlines kept theme-independent `#808080` @0.7, width 1.0; `chart()` dots r 2.0 @0.8, hlines 1.5; seed strokes 1.7 everywhere (doc-named sites + DI/on-axis siblings app.js 1048/1063); convergence eval-dot opacity 0.3 → 0.8 (was near-invisible — audit finding); target/reference hlines `--muted` → `--label` (7 call sites) + matching HTML legend swatches (target/target·H+V/DI); "show the starting design" checkbox label inked (interactive control, not annotation). Evidence: `pytest tests/test_gui.py -q` 30/30.
- **Phase 4 landed (this commit, with phase 5):** `wallSection` redesign (charts.js:229-317) — three-pass z-order (grid → all fills → ALL strokes, dashed start drawn LAST: amber outline readable along the FULL perimeter in both themes, 44/44 + 46/46 sampled slices); real even-odd wall-band fill 0.30/0.32 — measured composites EXACTLY on spec (light `rgb(182,211,215)` over #ffffff, dark `rgb(42,79,87)` over #151d23); bore stays plot background BY DESIGN per the doc's fill spec (band ≠ bg ≥1.6:1; the R1 fallback trigger band≡bore did NOT fire); strokes best 2.25/2.0 (V dashed 6-4), start dashed 2.0, compact 1.6 with dash suppression <260px; margins 46/34 + pad 1.02; plain-word plane labels ("horizontal plane →" / "← vertical plane" / "depth z (mm)") at mid-height; throat landmark dots r2.5/1.5 on BOTH mirrored halves at min-z-with-|r|>0; caption extended with the band/bore/amber/dot sentence (`app.js:960`). Pixel evidence: batched observer scanline pass, both themes.
- **Phase 5 landed (this commit, with phase 4):** 3D form/lighting — `MeshStandardMaterial` 0xdfe4e8 (roughness .55, metalness .05, DoubleSide, opaque, polygonOffset so the wire wins the depth test) replaces the translucent teal phong; **wireframe overlay RETAINED at the owner's request, light-toned**: `LineSegments(WireframeGeometry(geo))`, `LineBasicMaterial` 0xf4f7f9 @ 0.28, always on (not shadow-gated), disposed in `_dispose3d` (the original black-wireframe removal is superseded); 4-light rig (hemi .45 / key 1.15 / fill .35 / rim .85 at center+dir×maxDim); themed canvas token `--viz-canvas` (#e9edf0 light / #1d272e dark, all three blocks) with `--surface` fallback; toggleable shadow rig (PCFSoft 1024², ortho ±0.8×maxDim, `normalBias` 0.01×maxDim + bias 0 — the MUST fix, ShadowMaterial ground 0.22 at y=min−0.02×maxDim) behind the persisted `v3d-shadows` checkbox (default on); `init3d(..., seedProfile?, shadows?)` — the orphaned `seedCol` is finally used: seed dashed drawn UNDER best solid in the SVG fallback (which also merges the seed extent) + empty-mesh guard routes there. Pixel evidence (batched observer, both themes): canvas tokens EXACT, horn neutral grey (lit 184,188,191 / shadow 80,85,89 — not teal), full silhouette traceable on both flanks, wireframe clearly visible and NOT overwhelming, no z-fight/clipping artifacts. Known minor: contact shadow detected in dark, not in light — headless SwiftShader proxy; owner to eyeball live (real GPU).
- **Phase 6 landed (this commit — all six phases implemented):** semantics/state redundancy — over-budget flagged at all three budget readouts (home GPU card, status running card, run-detail KPI strip): value class `.bad` (`.warn` at ≥90 %) + literal "over budget" text next to the number (the real 151/150 run now flags); campaign family rows gain text redundancy beside the rank borders: `+X %` (next rank worse by X %) or `leader` when clearly ahead, `within noise` when not separated; timeline dots gain shape+color redundancy (`.tl-dot.skip` transparent + 2px `--muted` border, `.tl-dot.failed` square + `--bad`); `evolution.js` added to the node --check parametrize (5 static files gated). Evidence: `tests/test_gui.py` 31/31; full offline suite (`-m "not slow and not gpu and not crosscheck"`): exactly 1 failure — `test_mesh_pin` (installed hornlab-beat-bem `fa99ee594087` != pinned `38544d214ba2`): that is the concurrently-running WP15 fork lane's mid-flight install state (fused-cuda fork @ fa99ee5 per the M1 note above), NOT GUI work — this plan's diff touches zero Python/solver code outside the test_gui.py parametrize widening. GUI plan complete: phases 1-6 implemented, each phase pixel-verified in both themes; remaining manual item = owner's click-path check of the theme toggle + scroll/filter restore.

## 2026-10-24 (local, evening) - M1 LANDED: objective v2 + re-score; driver fairness; graded infeasibility; HF grid weights; fused-CUDA plumbing; Oracle GO

- **WP1 objective v2** (opt-in `objective: {version: 2}` in brief/config; default 1 = bit-for-bit): `metrics/smoothness.py` +`ripple_detrended_db` (even-quartic detrend, ddof 3) +`band_flatness_detrended_db` (log2 detrend, ddof 2); `metrics/di.py` +`target_di_gaussian_db` (10.3301/11.9084/13.7564 for 90x90/90x60/75x45); NEW `objective/scalar_v2.py` (same key set/never-raise contract, `freq_weight_vector`); dispatch in `search/evaluate.py::_score` by `ctx.objective_version`; `objective_version` recorded in every ndjson row + run.json. **Offline re-score** (`tools/rescore/rescore_v2.py` -> `docs/evidence/OBJECTIVE_V2_RESCORE.md`): 18,059 records / 12,590 designs / 27 families / 123 runs; Spearman ρ 0.9891 (records) / 0.9886 (unique); v1 medians reproduce `TYPOLOGY_COMPARE_2026-10-23.md` to 3 decimals, both claims SURVIVE; v1-vs-status drift 0; compare-tier v2 best medians: osse_axi 5.841 < blend_osse_tractrix 5.985; perturbed_osse_hv 7.222 < rosse 9.638 < hyb 11.826. The 12.3 MB per-record CSV stays LOCAL (evidence rule; regenerate with the tool).
- **WP2 fairness pins** (`config.py::_apply_brief_driver_pins`): on a FRESH `--brief`/`brief_file:` applied to a native (OSSE/R-OSSE/ICW) config, `r0_mm` is pinned to the brief driver (conflicting pinned value = ConfigError, silent rescale refused); `a0_deg` (and native FREEFORM `profileH/V.throatAngleDeg`) pinned only under `driver.throat_angle_policy: pin` (absent = old behaviour). `campaign.is_compatible` skips entries tied to their own driver (`catalog.yaml`: osse_baseline 17.78 mm -> SKIP under 1-inch briefs with reason). Report scalar `throat_angle_mismatch_deg` on every family. **Oracle must-fix implemented:** embedded run-dir briefs (resume/verify/report path) are grandfathered — no pins are applied and the raw is never mutated; regression-tested (`tests/test_config_driver_pin.py::test_old_embedded_brief_run_config_grandfathered`). Note: exactly 2 of 123 old run configs carry r0 17.78 + an embedded 12.7 brief; before this fix they refused to load; now they load byte-for-byte.
- **WP3** `profiles.perturb_increments_shape` (mouth radius preserved; `perturb: {mode: shape}`, legacy default bit-for-bit) + pre-mesh envelope estimate (`registry.envelope_overshoot_estimate`): a generator design estimated outside the brief envelope becomes `invalid_envelope` with `_generator_overshoot` (never on legal designs); penalty flat (1e3, J-identical to today) or graded `min(2e3, 1e3 + 100*overshoot)` under `search: {infeasible_penalty: graded}`. All shipped seeds estimate 0.0.
- **WP4** `freq_weights` validated and applied to the v2 ripple mean (v1 keeps ignoring it with a ONE-TIME WARNING); brief `grid: {verify_points_per_octave: N}` builds the verify grid as the frozen 25-point grid PLUS log points in [5 kHz, band_hi] — its own grid group (solve hash); dated note in `docs/TYPOLOGY_PLAN.md`.
- **WP15 repo side** (plumbing only; GPU ladder deferred to M2): `solve.cuda_fused` (config, beat_cuda only) rides `SolveSpec.extra` (hash unchanged when absent); `BeatBackend.__init__` sets `HORNLAB_BEAT_FUSED_BM_CUDA` "1"/"0" before any host spawn; `beat.py::_assert_cuda_fused_path` refuses unless every per-frequency diagnostic proves `assembly_path == "fused_cuda"`; meta["cuda_fused"] recorded. Fork branch `hornlab-search/fused-cuda` @ `fa99ee594087507c2808b9e7db09b38d8d4dcc20` (from base 38544d2): fused CUDA driver path, Julia testset green flag-off 27/27 + flag-on 6/6, CPU testsets green.
- **Recon for M4** (`NOTES_FOR_SENIOR.md` 2026-10-24 block): the point-grid builder ACCEPTS self-turning (rollback) profiles — no fork-mesher change; BARE mode is not BEM-usable (open rim), infinite-baffle refuses rollback; **freestanding + explicit outer_points offset is the WP10/9b route**.
- Tests: +120 offline tests (new: smoothness_v2, objective_v2, targets_freq_weights, config_driver_pin, solve_fused_flag, design_generators_perturb_shape, design_envelope_estimate; updated: test_config no_none, test_design_generated fixtures, test_search_verify_brief brief copy). No test loosened (Oracle-checked: the changes are contract updates forced by WP2). Suite: **933 passed, 20 deselected, exit 0 (222.6 s)**.
- Oracle verification (1 call, GO conditional -> all 3 must-fixes implemented in the push commit): (1) grandfathered embedded pins + evidence-correction note in OBJECTIVE_V2_RESCORE.md; (2) rescore CSV local (gitignored) + regression note; (3) this CONTINUITY/ISSUES/CODE_MAP/INDEX update. Non-blocking follow-ups -> `docs/ISSUES.md` 2026-10-24 section.

## 2026-10-24 (local, ~18:35 EDT) - senior investigative pass; fork policy; pin parser accepts fork URLs

- Reports in `docs/research/senior_pass_2026-10-24/`: 01 audit (ripple term scores beam taper, flat term scores source tilt, DI target 2.5 dB low, `freq_weights` ignored, briefs don't pin the driver for native families, 2 m near-field, coarse grid), 02 typologies + multicell (point-grid door, JMLC-type construction), 03 12 kHz (CUDA footprint ~80 N^2 bytes; fused path ~20k dofs), 04 implementation plan WP1-WP17. Two Sonnet literature surveys as appendices with corrections.
- Owner amendment: Magnus's packages may be changed via pinned forks (`C:\Users\hunte\Hrns\forks\`, `docs/FORKS.md`); hard rule 1 amended in CLAUDE.md / AGENTS.md / CONTRIBUTING.md / README. Forks cloned at the pinned SHAs (byte-identical to installed). P1 fused CUDA is now our WP15.
- `cli.py` pin regex accepts any git URL (upstream, GitHub fork, file://); `tests/test_cli_pin_urls.py` added. Synergy/MEH horns out of scope (owner).
- Offline suite (`-m "not slow and not gpu and not crosscheck"`): exit 0, all passed. Commit 95b45d1 (this entry follows in the next commit).

## 2026-10-23 (local, ~16:35 EDT) - F timed rehearsal DONE (CLI + GUI); 8 friction points fixed; G refreshed

- CLI quickstart verbatim in a fresh PowerShell: doctor 5 s (11 checks OK), families 1 s, campaign dry-run 8 s, dry-run 2 s, search 60 7.3 min (J 30.94 -> 15.74), report 5 s, export-step 74 s. GUI path Home -> Typologies -> Launch -> campaign -> run -> Evolution -> Export STEP all work, 0 console errors; the shipped-brief screen replays from the cache in 51 s; a live screen on a new 80 x 80 brief copy takes 5.5 min (48 new solves). Table and friction list: `docs/evidence/BETA_READINESS.md` F.
- Fixed: quickstart (doctor 11 checks, gpu-clean instead of taskkill / Get-Process, cache-reuse counts explained, dry-run estimate caveat, rename `name:`, 12 kHz verify line); `verify_only` brief key (the `*_12k` briefs) refused by search/run/campaign and hidden from Launch; session plan live step on a saved brief copy + 12 kHz readings; surrogate limit line.
- Offline suite: **813 passed, 18 deselected, exit 0**.

## 2026-10-23 (local, ~16:20 EDT) - P2 12 kHz verify DONE; surrogate retrain GATES FAILED; D3 PASS after a campaign fix

- **Overnight queue** finished 15:49:36 (QUEUE DONE; sculpt seeds 5101-5125 all exit 0; gpu-clean left no host, VRAM 631 MiB).
- **P2 12 kHz verify** (`docs/evidence/HF12K_VERIFY_2026-10-23.md`): 6 GPU jobs 15:49-16:06, 14 finalist designs + 2 epw checks, 0 failures, gpu-clean between jobs, nothing left (VRAM 327 MiB). epw converged at 12 kHz (osse_axi 6 vs 8: <= 0.058 dB DI, <= 0.31 deg; perturbed_osse_hv 6 vs 7: <= 0.007 dB, 0.06 deg). Rankings as in the compare tier (osse_axi > blend_osse_tractrix; perturbed_osse_hv > rosse_baseline). perturbed_osse_hv V is 11-22 deg wider than 60 deg at every band; rosse narrows to 59-60 deg H at 12 kHz. Peak VRAM 7,360 MiB above baseline at 6,049 dofs: 12 kHz verify is at the edge of the 8 GB card. f11 = 7,914 Hz: 8-12 kHz compares geometries, not drivers. GUI shows the verify runs (isobars to 12 kHz, 0 console errors).
- **Surrogate retrain** on a verified dataset snapshot (14,091 records, 0 bad), torch on CPU: 3080 OSSE records (21 solve_failed excluded), held out **463 < 500** (indicative). 600 epochs: spearman 0.963 PASS, topk 11/20 FAIL, bw 1.48 PASS, di 0.21 PASS, invalid_accuracy 0.80 FAIL, flips 4 FAIL; 300 epochs worse (topk 0). GATES FAILED, model NOT used. `docs/evidence/CP-8d_retrain_2026-10-23.md`.
- **D3 Ctrl-C**: code read first found two bugs in `search/campaign.py`: `subprocess.run` killed the Ctrl-C'd child mid clean-up and the leaderboard was never written; a campaign never cleared its Julia/BEAT hosts (snapshot only, contrary to GPU rule 6 and to the 2026-10-22 docs). Fixed + offline tests (`tests/test_search_campaign_interrupt.py`). Live: real CTRL_C_EVENT into a screen campaign's console after 7 rows: exit 130 in 1.4 s, lock gone, partial leaderboard + campaign.json (interrupted: true), child run.json `interrupted`, hosts cleared, no julia / worker_host left. `docs/evidence/BETA_READINESS.md` D.
- Offline suite: **811 passed, 18 deselected, exit 0**.

## 2026-10-23 (local, ~15:10 EDT) - sculpt fill summary; collaborator handoff

- Overnight sculpt fill (freeform_sculpt, 150 evals each, cma seeds 5101-5120 finished, 5121 running at 15:00): every seed improved on the seed design (J 30.945) to 17.23-22.01 (best 17.234, seed 5112; median ~18.5); failures only 0-2 `invalid_geometry` per run, **no solver failures**. Pinned at the best design (within 2 % of a bound): `profileH/V.points.3.1` at lo in 14 of 20 runs; `mouthAngleDeg` at hi (H or V) in 4; `points.1.1` at lo in 5; `points.4.1` at hi in 2. Same picture as the 400-eval run (disjoint per-anchor boxes bind): bound / reparametrisation decision stays with the owner.
- `docs/HANDOFF_COLLABORATOR_2026-10-23.md` for the collaborator pulling tonight; status block refreshed.

## 2026-10-23 (local, ~14:35 EDT) - GUI Launch GPU state live; beta session plan GUI-first; 12 kHz pre-mesh

- GUI Launch: the GPU-busy state is re-read from `/api/status` every ~6 s while the page is open (note, search-form warning and Start button follow it; toast on change). Checked in the browser against the live queue (busy shown) and with `/api/status` stubbed free in the page (note cleared, toast, then busy again on the real status); 0 console errors. GUI tests 30 passed, exit 0.
- `docs/BETA_SESSION_PLAN.md` refreshed: GUI first (doctor 11 checks incl. disk, Typologies, Campaigns, Launch, Evolution, Export STEP, Compare), 12 kHz verify slot and its caveat; CLI quickstart as fallback.
- P2 pre-mesh (CPU only, gmsh, under the `*_12k` briefs, verify mode, caps unchanged): all 12 finalist designs (top 3 of osse_axi, blend_osse_tractrix, perturbed_osse_hv, rosse_baseline) mesh within the 7,000-dof verify cap: 8,743-11,810 triangles (~4.5k-6.0k dofs; largest osse_axi rank 1). The epw+2 variants do NOT fit (axi epw 10: 16,720-18,400 triangles > 15,784 limit; hifi epw 8: 7,884 dofs / 16,256 triangles) -> the 12 kHz epw check compares DOWN (axi epw 8 vs 6, hifi epw 6 vs 7) instead; no cap raised. GPU jobs queued behind the overnight queue (one at a time, gpu-clean between).

## 2026-10-23 (local, ~14:30 EDT) - dead-worker-host recovery fixed (root cause found); `verify --brief` bug fixed; 12 kHz briefs

- **Root cause of the OSSE seed-4101 cascade (03:58)**: after the host died, `hornlab_beat_bem.worker.get_worker` kept handing out the SAME cached `HostedBeatWorker`, whose `submit` releases its slot on a send error but keeps the dead socket in `_connection`; our `recover_after_failure` killed hosts and marked cold but never dropped that client, so all 21 later candidates failed in ~1 s with `ConnectionResetError` at `BeatSolveSession(...)` (row tracebacks, `worker_client.py:122`). Fix (our layer only, no library edit): recovery calls `detach_workers` first (empties the library cache); `BeatBackend._solve` re-warms and retries a `worker_exit` candidate once (OOM / other not retried); `search` raises `SolverUnhealthyError` after 3 consecutive non-cached `solve_failed` -> run `aborted`, resumable (`solve_failed` rows are never memoised, so `--resume` re-solves them); a campaign records that entry as a failed job. Why the host died is still unknown (GPU rule 7).
- **Surrogate labels**: `to_training_arrays` drops `solve_failed` records (solver crash, not the design) and reports `meta.skipped_solve_failed`; deterministic failures stay as validity labels.
- **Bug: `verify --brief` was parsed and ignored** (same class as the 2026-10-22 search bug); a 12 kHz verify would have silently re-solved at 5.5 kHz. Now applied; with `--brief` the results go to a new run dir `runs/<ts>-verify-<id>` (config/run.json with `verify_of`/ndjson/best.json; the GUI lists it), without it the old `run/verify/` behaviour.
- New VERIFY-only briefs `examples/briefs/axi_90x90_1in_12k.yaml`, `hifi_90x60_1in_12k.yaml` (copies, `band_hi_hz: 12000`, P2 comment + cross-mode caveat); verify grid 300-12,000 Hz, 25 points, config verify dof cap (7,000) unchanged.
- The overnight queue's later sculpt seeds (new subprocess per seed) import these modules; each edit was compile-checked before saving and only failure paths change.
- `tests/test_report_html.py` zero-success test: setup now expects the resumable stop (3 failure rows instead of 10); its assertions are unchanged plus one on the row count.
- Offline suite: **808 passed, 18 deselected, exit 0**.

## 2026-10-23 (local, ~11:30 EDT) - GUI beta hardening: Boundary Lab-style isobars, every control exercised, navigation race fixed

- **Directivity isobars** now follow Boundary Lab's renderer (read from `JWSound/boundary-lab` `src/blab/plotting.py` / `ui/plots.py`, ideas only): frequency on a log x-axis, angle on y, level re on-axis in 10 DISCRETE 3 dB colour bands from -30 to 0 dB (its default clip and palette), white contour lines every 3 dB (marching squares; -6 dB heavier), labelled dB colour bar, hover crosshair reading frequency / angle / dB. Best design H + V; starting design on a toggle. Checked against the beamwidth curves (H -6 dB edge ~+-45 deg at the 90 deg target).
- **Every control exercised in the browser** (scripted): run actions, isobar toggle, compare-with prefill, campaign H/V toggle, runs filter + sort, compare, brief select / invalid-name refusal / families, launch select-all + server preview + GPU-busy disable, evolution play / pause / keys / mode, 3D canvas; Generate report and Export STEP end to end through the API (report 5.2 MB served; 3 STEP solids written and downloadable).
- **Bugs fixed**: a slow view finishing after navigation painted over the new page (views now keep their own container; helpers bail if superseded); report / STEP export used alert() and jumped to Launch (now inline progress, download links for STEP files, Open report); caption used a variable before definition (run page blank); remaining alert()s replaced with toasts; download glyph.
- Home: "How to use this" four-step guide (collapsible, remembered). STEP files and report are the only run files the server serves (strict names, tested).
- Offline suite: 795 passed, 18 deselected, exit 0 (before the final glyph-only change); GUI tests after it: 30 passed (the d0a04ea message says 31: miscount).

## 2026-10-23 (local, ~10:40 EDT) - GUI: search time-lapse ("Evolution") player

- `#/run/<id>/evolution` (`static/evolution.js`, `/api/evolution/<run>`): plays a search back evaluation by evaluation, synchronised side view (wall cross-section, true scale, fixed axes for the whole run, last 4 best designs as fading ghosts, best-so-far dashed), front view (mouth outline = convex hull of the mesh nodes within 1.5 % of the mouth plane, mirrored from the quarter; the brief's size envelope dashed), score chart with playhead (failures as red ticks), and each shape parameter as a marker inside its limits (red = within 2 % of a limit, the run page's "at limit" rule). Modes: improvements only / every candidate; play, step, scrub, speed, loop, keyboard (space, arrows, Home/End); shareable `?f=<n>|last&mode=all`. Geometry is only what the search meshed; designs without a saved mesh say so.
- Data: extracted once per run from `designs/<hash>/mesh.msh` (17 ms each; 450 evals 2.3 s, 951 evals 23 s, then cached 0.02 s) into `runs/.gui_cache/evolution_<run>.json` (GUI-owned, gitignored with runs/), keyed on search.ndjson size + mtime + format version, so a running search refreshes and reuses geometry already extracted.
- Prior art consulted: Abaqus optimization time-history animation, the `cmaes` library's animated search distribution, Optiscope / Optuna optimization-history pages.
- Observed in the OSSE top-up time-lapse: `exponent` presses its upper limit (7.9 of 8) as the mouth grows; perturbed_osse_hv `L_mm` at 139.8 of 140 (consistent with the compare evidence).
- Offline suite: **794 passed, 18 deselected, exit 0**.

## 2026-10-23 (local, ~09:00 EDT) - GUI: typology/hybrid picker, Typologies page, correct graphics; 3 real launch/data bugs fixed

- **Typologies page** (`#/typologies`, `/api/typologies`): every catalog family (classical, hybrid, Magnus-native, legacy) with parameter count, screen/compare budgets (`campaign.budget_for_tier`), brief compatibility from the CLI's own `campaign.is_compatible`, its rank/median/size in the newest valid campaign of each tier that contains it, a true-scale cross-section, and one-click "Screen on <brief>". **Launch** families are a grouped checkbox picker (incompatible greyed with the CLI's reason; evaluations and a time estimate from the slowest measured campaign per family); the command preview comes from the server (`POST /api/preview`, same validation as a launch).
- **Graphics**: charts render 1:1 at their measured width (no scaled-up text); one convention (H solid, V dashed; start amber, best teal; target +-10 % shaded); polar maps as SVG with angle/frequency axes and -3/-6/-10 dB isobars (Boundary Lab-style directivity isobars); wall **cross-section** from the quarter mesh's symmetry-plane boundary edges (ordered outline incl. shell; correct for rollbacks), true scale, shared scale across families on the campaign page; throat impedance resistance + reactance (engineering sign, X = -Im Z in the solver's exp(-i w t)); per-family colours; DI overlay; 3D view now mirrors the quarter mesh.
- **Bugs fixed** (all would have reached the beta): GUI campaign launch always refused (brief name sent instead of its path, families as a list); dry-run command preview invented (`dry-run --config`, not a CLI command); campaign overlays drew the vertical beamwidth against 90 deg (campaign.json has no target; now read from the brief file); 3D view showed one quadrant (quadrants "1" string vs number); superseded pre-fix campaigns could rank (osse_baseline 6.82 on the hifi brief from a campaign that ignored the brief): campaigns older than the newest committed evidence campaign and not themselves committed are flagged `superseded` and excluded from Home / Typologies / leaders; families with no valid design under a brief say so.
- Checked: headless-Edge screenshots of every page; browser sweep 14 routes at 1366 and 8 at 400 px (dark/light): 0 console errors, no NaN/undefined/raw HTML, no horizontal overflow. GUI campaign dry-run (conical + hyb_osse_h_hypex_v) launched via the API and finished exit 0; screen tier refused while the GPU lock is live.
- Offline suite: **792 passed, 18 deselected, exit 0**.

## 2026-10-23 (local, ~08:30 EDT) - GUI senior UX hardening pass (designer-first); OSSE seed-1 worker-host crash found

- GUI rework for a speaker designer: new Home (live job progress n/budget, best so far, rate, ETA; overnight queue timeline; best horn per brief from `/api/leaders` = latest campaign of the strongest tier, median-ranked, "clearly ahead" only by the ranking rule); run page leads with coverage target, band, horn size W x H x D (outer, incl. shell, from the mesh bbox), score change ("40 % better"), then beamwidth vs target, DI, on-axis, throat resistance Re Z (1.0 ref, 0.7 threshold), polar maps, wall profile; then search diagnostics. Launch uses pickers from `/api/configs` / `/api/catalog`, GPU actions disabled while the lock is live (server re-checks). Plain-language labels + tooltips from `static/glossary.js` (definitions follow `objective/scalar.py`); Glossary view. New API: `/api/leaders`, `/api/configs`, `/api/catalog`; status gains `current` progress and `queue_log.steps`; summaries gain `dims`, `budget`, `cma_seed`; GUI jobs persist their final status across GUI restarts.
- Bugs fixed during review: Home "best per brief" scanned raw runs and showed an out-of-envelope pre-fix OSSE design (677 x 402 mm) for the 400 x 300 hifi brief -> server-side leaders; queue SKIP lines unparsed; raw tooltip HTML inside an SVG axis; failure-ratio NaN; stray brace from an edit blanked every view (new test module-checks all static JS with node); phone-width overflow from fixed-width SVGs and select tracks; amber text 3.9:1 -> 5.9:1 and group pills to ink text; brief error message leaked a temp filename; clickable rows keyboard-reachable.
- Checked in the browser: 13 routes at 1366 x 850 and 10 at 400 x 800 (dark and light): 0 console errors, no NaN / undefined / raw HTML, no horizontal overflow. Brief save validated by the CLI's own check (an axisymmetric brief with H != V refused; shipped names protected).
- **OSSE top-up seed 4101: worker host died 03:58:48 EDT**, 21 `solve_failed` in 63 s, CMA-ES stopped on flat penalties at 411/950 (best J 6.28). Not the test suite (seed 4102 ran through two later suite runs with 0 solver failures). ISSUES entry with the recovery fix proposal; exclude `solve_failed` from surrogate validity labels before the retrain.
- Offline suite: **788 passed, 18 deselected, exit 0**.

## 2026-10-23 (local, ~04:15 EDT) - local web GUI built; GPU-lock liveness bug found and fixed (queue untouched)

- **Bug (serious, fixed):** `gpulock._pid_alive` used `os.kill(pid, 0)`; on Windows signal 0 is CTRL_C_EVENT, so for a lock holder in another console it raised and the live holder looked STALE: a second GPU job from any other terminal would have taken over the lock, and `gpu-clean` would have killed the queue's julia mid-solve. Found because the new GUI showed the running queue as "stale". Now `OpenProcess` + `GetExitCodeProcess` (sends nothing). Verified: queue search pid 4916 alive=True and still writing rows; tests `tests/test_search_gpulock_pid.py` (incl. a guard that `os.kill` is never called on Windows). The running queue step loaded the old module but never re-checks the lock; the next steps import the fix.
- **GUI** (`docs/GUI_PLAN.md`, `hornlab-search gui`, http://127.0.0.1:8765): stdlib server + vanilla JS, no build step; views status / campaigns / runs / run detail (curves, polar maps, sensitivity, pinned bounds) / compare / briefs (save NEW user briefs only, validated with `load_brief`) / launch (allow-listed CLI argv, GPU-busy refusal) / 3D (three.js CDN, quarter mesh mirrored, 2D fallback). Prior art surveyed: waveguide-generator (FastAPI + React/Vite), Boundary Lab (PySide6). Backend by the orchestrator, frontend by a Sonnet subagent, integrated and fixed here (SVG className crash, hash-query routing, unescaped URL in innerHTML, compare table fields, early-reply socket abort on Windows). Checked in the browser: every view, 0 console errors, no horizontal overflow at 400 px; live checks: lock shown alive, GPU search and gpu-clean refused while the queue runs, a dry-run launched and finished (exit 0).
- Offline suite: **778 passed, 18 deselected, exit 0** (`-o addopts="" -m "not slow and not gpu and not crosscheck"`). Correction: the "711" / "712 passed" counts in the 22:47 and 03:36 entries were undercounts from counting progress dots under the doubled `-q`; both runs had exit 0 and no failures.

## 2026-10-23 (local, ~03:50 EDT) - compare tier DONE unattended; OSSE top-up running; compare evidence + review page

- Overnight queue phase 1 all exit 0, watchdog idle: axi screen epw 8 (22:16-22:44), axi compare (-00:33), hifi compare (-02:19). OSSE top-up seed 4101 running (275/950 at 03:20, ~265/h); then seed 4102, then sculpt fill to the 15:45 start cutoff.
- `docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`: axi osse_axi 9.63 (spread 0.02) < blend_osse_tractrix 10.05 (0.03) < exponential 11.37 ~ hypex 11.40 (not separated; both pinned at L_mm lo / h_rm_mm hi = envelope corner). Hifi perturbed_osse_hv 10.31 (0.03) beats rosse_baseline 13.33 (2.0) and hyb_osse_h_hypex_v 15.13 (0.12); rosse vs hybrid not separated. Bound proposals tabled, NOT applied (owner decision). Leaderboards + campaign.json copied to `docs/evidence/campaigns/`.
- Review page rebuilt and republished (version 4, same URL): compare campaigns, C2 mesh row, new findings, updated next steps.
- D5 PASS: families / campaign dry-run / report / export-step from another cwd with absolute paths.
- Branch `beta-fixes` MERGED to main ~03:36 while the OSSE top-up search was mid-run (its modules already loaded; the changes do not touch the search path); offline suite on the merged tree 712 passed, exit 0: surrogate refusal wired into `surrogate train/propose/round`; `compare` empty-frequency-list ValueError; tests pass.
- Alongside the queue (no GPU): D3 Ctrl-C test on the CPU backend with a separate runs dir; F rehearsal CPU steps; surrogate retrain + CP-8d gates on a dataset snapshot after OSSE seed 4102 ends (~09:40), torch forced to CPU. Only the F screen step needs the GPU (after ~16:15).
- Local web GUI planned and in progress: `docs/GUI_PLAN.md`.
- OWNER 03:26: do NOT republish the review page until the owner says so (version 4 stays). After the beta, start from `docs/NEXT_DEV_PRIORITIES.md`.

## 2026-10-22 (local, ~22:45 EDT) — docs index and code map

- New `docs/INDEX.md` (every doc, one line each) and `docs/CODE_MAP.md` (every module, config folder, external dependency); pointers added to `CLAUDE.md` (Start here, step 0), `AGENTS.md` and a new `.claude/CLAUDE.md`. Rule: a new doc or module gets a line in the index/map in the same commit.

## 2026-10-22 (local, ~22:35 EDT) — NEXT DEVELOPMENT ROUND PRIORITIES recorded (docs only)

- New `docs/NEXT_DEV_PRIORITIES.md` (user decision): **P1 fused / direct CUDA Burton-Miller assembly** in the exterior driver (fused path is CPU/Metal only at `hornlab_beat_bem/julia/BeatEngineDriver.jl` ~l.1215; the CUDA single-matrix assembler at `julia/src/BeatEngineCudaBurtonMiller.jl:350` is only exercised by `runtests.jl`); engine work in Magnus's package (his OK or a pinned fork), expected 8 GB ceiling ~9k -> ~20k quarter dofs [inferred], validation ladder listed. **Not enabled for the 2026-10-22/23 overnight queue** (one solver for the compare tier and the surrogate top-up). P2 12 kHz finalist verify pass on the 4060; P3 `beat_metal` backend for the collaborator's MacBook. ISSUES TO-DO and HANDOFF_BETA point to it.

## 2026-10-22 (local, ~22:17 EDT) - beta pass in progress; OVERNIGHT GPU QUEUE RUNNING (UNCOMMITTED WORK)

- Detached queue `runs/overnight/queue_20261022.ps1` (log `runs/overnight/queue_20261022.log`), no step starts after 2026-10-23 15:45: axi screen at epw 8 -> axi compare (osse_axi, blend_osse_tractrix, hypex, exponential) -> hifi compare (perturbed_osse_hv, hyb_osse_h_hypex_v, rosse_baseline) -> OSSE top-up 2 x 950 (cma seeds 4101/4102; owner asked for surrogate data 22:14) -> freeform_sculpt 150-eval searches from seed 5101 until the cutoff. Holds `runs/.gpu.lock`.
- COMMITTED 22:47 (offline suite `-m "not slow and not gpu and not crosscheck"` exit 0; GPU-lock diff reviewed by orchestrator; watchdog `tools/overnight/watchdog.ps1` running beside the queue, kills a search after 30 min with no write under runs/, keeps Windows awake): A1/A2 audit, A3 guard test, B1-B4 (backup, verify OK, R8 provenance, surrogate refusal), C1-C7 incl. C2 measured, owner decisions (axi typologies epw 8, H/V epw 6; keep mesher pin), D1/D2 lock + gpu-clean (+ doctor disk check?) by subagent, README status, `docs/BETA_SESSION_PLAN.md`, `docs/evidence/BETA_READINESS.md`.
- Next: review the cli.py/gpulock diff, run the full offline suite, commit + push with ISSUES; after the queue, write TYPOLOGY_COMPARE evidence, rebuild the review page, retrain the surrogate (CP-8d gates), then F rehearsal.

## 2026-10-22 (local, ~21:40 EDT) — HANDOFF for the beta-readiness pass

- `docs/HANDOFF_BETA.md`: next agent runs as Opus (medium effort), orchestrator and decision maker, with at most 2 Haiku/Sonnet subagents at a time for menial work (repo ingest, tests, small coding, docs, read-only review). Work items A-G: dependency/upstream grounding audit, data integrity (R8 brief provenance in records), physics audit (incl. the unmeasured epw-6 resolution above 2.5 kHz), GPU lock + `gpu-clean` + Ctrl-C safety for two testers on one GPU, compare tier on the screen leaders, timed beta rehearsal, beta session pack. Stop conditions listed. Docs only.

## 2026-10-22 (local, ~21:30 EDT) — first FAIR typology screen campaigns; pre-beta hardening done; review page updated

- More fixes after the 20:30 entry: brief size envelope enforced for EVERY family on the outer mesh bbox (brief-dependent, never failure-cached); `campaign --budget/--seeds < 1` refused; knob counts read from YAML bounds (no silent fallback); failure markers bound to library SHAs; generator provenance last-wins; leaderboard says "NO VALID DESIGN" when a native seed is outside the brief. Pre-beta bug hunt (Sonnet): truncated incompat reasons, duplicate "campaign OK", unclear missing brief_file error - fixed with tests. Correctness review (Sonnet, read-only): 3 findings, all fixed.
- Clean screen campaigns (`campaign_20261023T005133Z` axi, `…T010225Z` hifi; superseding all earlier ones): `docs/evidence/TYPOLOGY_SCREEN_2026-10-22.md`. Axi 90x90 (load-weighted): osse_axi 10.71, blend_osse_tractrix 11.04 (DI slope 4x flatter), hypex 12.27, exponential 12.59, blend_conical_exponential 12.98, freeform_sculpt 15.81, icw_termination 21.45, icw_rollback 25.22, conical 28.21, perturbed_tractrix 89.75, tractrix 103.72. Hifi 90x60: perturbed_osse_hv 11.22 (new hybrid; L_mm pinned), hyb_osse_h_hypex_v 15.78, freeform_hv 18.80, rosse_baseline 19.41, hyb_osse_h_tractrix_v 46.40; freeform_sculpt and osse_baseline seeds are outside the 400x300 envelope (no valid design). Screen tier = coarse ranking; compare tier next.
- Review page republished with a campaign section (leaderboards, best-design profiles, beamwidth overlays); overflow at desktop width fixed.
- GPU end state: no julia, no worker host, VRAM ~550 MiB.

## 2026-10-22 (local, ~20:30 EDT) — screen campaigns reviewed: 3 bugs found and fixed; native-family entries re-running

- First screen campaigns finished (axi 17:31-18:16, hifi 18:16-18:54). Review found:
  1. **`search` ignored `--brief` / `--cma-seed`** (only `run` used the brief-aware loader). Generator configs were unaffected (they name their brief in the YAML), but the Magnus-family entries were scored on their OWN targets (ICW 100x100, sculpt 90x90 under the 90x60 brief, OSSE 75x45, no load weight). Fixed in `_cmd_search`; `load_config` now reuses the brief embedded in a run's saved `config.yaml` (resume/verify/report reproduce the run). Regression tests added.
  2. **Unequal search**: native configs reuse CMA seed 1234, so they replayed 600-850 cached evaluations for free vs 40-180 for typologies. New `search --max-evals` caps ALL evaluations of an invocation (cached included); `campaign` passes it = budget. Test added.
  3. **Hygiene left the BEAT `worker_host` python processes alive** (they respawn julia). `search/hygiene.py` now lists/kills `hornlab_beat_bem.worker_host` too, with taskkill /T.
- Valid from the first campaigns (typology entries, correct brief, equal budgets, 1 CMA seed, screen tier = coarse ranking only): axi 90x90 brief: osse_axi 10.71, blend_osse_tractrix 11.04, hypex 12.27, exponential 12.59, blend_conical_exponential 12.98, conical 28.21, perturbed_tractrix 89.75, tractrix 103.72 (tractrix: DI slope term 71 - a 180 mm mouth cannot hold 90 deg down to 700 Hz, then beams); hifi 90x60 brief: perturbed_osse_hv 11.22 (65/180 invalid, L_mm pinned), hyb_osse_h_hypex_v 15.78, hyb_osse_h_tractrix_v 46.40.
- Native entries (icw_termination, icw_rollback, freeform_sculpt; rosse_baseline, freeform_sculpt, osse_baseline) re-running with the fixes.

## 2026-10-22 (local, ~17:45 EDT) — typology V4/V5 PASS on GPU; screen campaigns RUNNING (results not yet reviewed)

- `docs/evidence/TYPOLOGY_VERIFY.md`: V4 16 vs 48 anchors: dB metrics within 0.1 dB, beamwidth <= 1.1 deg; V5 exponential / conical / tractrix match textbook loading and beamwidth behaviour. Julia cleared after each solve.
- V7 screen campaigns launched 17:31 (axi brief: 10 families; hifi 90x60 brief: 6 families; script `campaign` x2, hygiene per search). **Not reviewed or committed yet**: outputs in `runs/campaign_*` (leaderboard.md). Next session: read both leaderboards, confirm no julia left, commit a summary to evidence, then `compare` tier on the top 3 families + top 2 hybrids.
- `docs/BETA_QUICKSTART.md`: typology selection with `families` / `campaign`.

## 2026-10-22 (local, ~17:35 EDT) — TYPOLOGY_PLAN implemented (generators, hybrids, briefs, campaign); offline + mesher checks green; GPU checks next

- **Lane A (Sonnet)**: `design/generators/profiles.py`: conical, exponential, hypex, tractrix (Voigt), blend, anchor selection, monotone-increment perturbation, Hermite reference; 69 tests (defining properties; anchor fidelity max 0.036 mm). **Le Cléac'h / spherical-wave DISABLED** (R9 gate: primary sources unreachable; `GeneratorUnavailable` with citations).
- **Lane B (Sonnet)**: `families` and `campaign` CLI (`--families name,group,all`, tiers dry-run/screen/compare, budgets max(40,10k) / max(150,25k), 1 / 2 CMA seeds, subprocess per search, GPU/Julia hygiene before/after via `search/hygiene.py`, leaderboard + campaign.json), `--brief` / `--cma-seed` on run/search/verify, 3 briefs (`examples/briefs/`), `rosse_baseline.yaml` (first R-OSSE config), `icw_rollback.yaml` (via `icw_seed` from R-OSSE), `freeform_hv` -> quarter domain, catalog; 63 tests.
- **Orchestrator**: `config.load_config(path, brief=, cma_seed=)` + `load_brief` (one schema; brief replaces target/weights and enters `raw`, so config_sha covers it); `generator:` configs (family stays FREEFORM, frozen contract untouched); `design/generated.py` GeneratedSpace (knobs -> FREEFORM design; bad knobs -> `invalid_geometry`, never a crash); `design/generators/registry.py` (typology specs, H/V hybrids, blends, perturbation, OSSE meridians sampled from Magnus's `profile_points`, envelope enforcement, common z span, 3 mm generated shell); provenance `generator` block in rows/design.json; report-only loading scalars `f_load_hz`, `z_ripple`, `z_mean_band`; **failure cache** (deterministic failures remembered by design+mesh+solve key across runs -> replays do not burn budget); 11 typology configs in `examples/typologies/` + catalog entries (classical, hybrid).
- **Verification so far**: V1 unit properties pass; **V2 Magnus's own FREEFORM evaluator reproduces the analytic conical/exponential/hypex/tractrix/OSSE meridians within 0.2 mm**; V3 all 11 enabled typology seeds mesh (dry-run campaign 18/19 entries; `search_smoke` legacy seed exceeds the cap under a 5.5 kHz brief, correctly refused). Random-sample mesh yield per space 63-100 % after tightening OSSE-based bounds to the 90-deg design point.
- Findings: the mesher's FREEFORM outer-shell curvature guard (thickness x concave curvature < 0.4) rejects an OS throat (5 -> 45 deg in ~13 mm) with the default shell -> generated horns use a 3 mm shell (recorded per design); tractrix walls near 80 deg trip it in H/V hybrids -> that hybrid uses a 75 deg cap and f_c 450-1000 Hz so its depth matches the OS horizontal. Source-cap `auto` from the brief is not yet applied (FREEFORM does not expose the cap keys; every design uses the mesher default, consistent across a campaign).
- Offline suite: 721 passed after updating two example-sweep tests for the new optional Config fields and `catalog.yaml` (no assertion loosened). Ownership: touches task 03/04/05/08 paths, user-authorised.

## 2026-10-22 (local, ~17:00 EDT) — research note: time-domain ringing / waterfalls (docs only)

- `docs/research/TIME_DOMAIN_RINGING.md`: our 3-D BEM already contains mouth reflections, higher-order modes and edge diffraction (complex p and z_throat are stored), but only on 12 log-spaced screen frequencies, which is far too sparse for an impulse response. Magnus's `hornlab_plots.complex_analysis.plot_impulse_response` / `plot_group_delay` exist but interpolate over resonances on a sparse grid. Driver internals (compression chamber, phase plug) are not modelled: the source is a uniform-velocity spherical cap. Proposed stage 2 `hornlab-search transient` on finalists (uniform ~25 Hz grid, ~1.5-4 GPU min per design; impulse, step, CSD waterfall, group delay, dense impedance; late-energy and decay-time metrics; closed-form + convergence checks). Cheap in-loop proxies (impedance ripple, f11, multilobe) stay in the typology plan. Linked from TYPOLOGY_PLAN s6 and ISSUES.

## 2026-10-22 (local, ~15:45 EDT) — TYPOLOGY_PLAN v2 after a senior adversarial review (docs only)

- 12 findings against v1, each resolved in `docs/TYPOLOGY_PLAN.md` s2. Blockers/high: a new `TYPOLOGY` family would break the frozen `Family` literal (`01_CONTRACTS.md:168`) -> typologies become **generators** that emit ordinary FREEFORM designs with a provenance block; cross-typology comparison needs a shared **design brief** (driver exit, size envelope, target, symmetry) and fixed-size parametrisations; classical horns must also be judged on **throat loading** (`z_throat_real` exists and is physical: OSSE seed Re z 0.08 -> 1.0) -> report-only loading metrics, optional `load` weight; axisymmetric typologies vs asymmetric targets refused or routed to H/V hybrids; throat junction tied to the driver exit angle and the mesher's spherical source cap (`auto` = r0/sin theta, ATH convention); fidelity measured on the mesher's own sampled profile; budget-40 comparisons replaced by tiers (screen / compare with 2 CMA seeds, budgets scaled by knob count); failure cache keyed by design + mesh spec; Le Cléac'h gated on an independent reference.
- Added: non-goals, briefs (3 to start), curated hybrid list, verification ladder V1-V7 with acceptance, risk register, lanes with done-criteria. No code changed.

## 2026-10-22 (local GPU box, ~14:50 EDT) — solver re-verified on GPU; typology research; TYPOLOGY_PLAN (classical horns + hybrids + family selection) for the next turn

- **Solver verification** (`docs/evidence/SOLVER_VERIFY_2026-10-22.md`): GPU-marked tests 18/18 PASS; `selftest --analytic` PASS (0.020 dB); `selftest --crosscheck` beat_cuda vs bempp 0.039 dB (< 0.2 dB rule). Julia cleared after each.
- **Research (2 Sonnet subagents, read-only, cited file:line)**: `docs/research/typologies/MESHER_TYPOLOGIES.md` (mesher formulas: OSSE, R-OSSE, ICW, FREEFORM, LOOKUP; morph, guiding curve, azimuth expressions, throat stretch/extension, ICW seeding from OSSE/R-OSSE; NO conical/exponential/tractrix/Le Cléac'h/hypex family; NO profile -> FREEFORM converter) and `docs/research/typologies/SEARCH_LAYER_GAPS.md` (R-OSSE has no config and 0 records; FREEFORM disjoint boxes pin anchors; morph/gcurve unused; ICW rollback unused; freeform_hv on the full domain; no seeding from typologies).
- **User request**: classical typologies (conical, exponential, tractrix, Le Cléac'h, hyperbolic, spherical, axisymmetric), hybrids, and controls to choose which families run on the GPU. **Plan written: `docs/TYPOLOGY_PLAN.md`** - classical profiles computed from textbook formulas and handed to Magnus's FREEFORM as exact `[z, r, angle]` anchors (LOOKUP tables for verification); hybrids (H/V, convex blend, monotone-increment perturbation, cross-section stations); new TYPOLOGY family; `campaign --families ...` + shared targets; failure-cache budget fix; R-OSSE and ICW-rollback configs; verification ladder (unit properties, mesher acceptance, FREEFORM-vs-LOOKUP acoustic check, textbook physics sanity). Implementation next turn (2 Sonnet lanes + orchestrator). Nothing implemented yet; no bounds changed.

## 2026-10-22 (local GPU box, ~12:50 EDT) — PR #15 merged (FF to 265133f) and its GPU test plan run; early-rejection replay; seed-replay budget finding

- `main` fast-forwarded b822dd5 -> 265133f (PR #15 tip, cloud suite 558) and pushed; `pip install -e .`.
- Step 1 offline suite **559 passed, 0 skipped, exit 0**. Step 2 doctor **10/10**.
- Steps 3-4 as written (`--budget 40`, config seed 1234) replayed the cache: sculpt 459 cached + 40 new (continues the 400 trajectory, J -> 16.421); **OSSE solved 0 new designs** - its 40 budget slots re-evaluated the 40 uncached failures in the replayed prefix (38 mesh_too_large + 2 invalid_geometry; GPU 0.0 s). Re-ran both from scratch config copies with ONLY `search.seed: 777` (1-line diff): sculpt 40 new, 0 failures, J 30.945 -> 24.291; OSSE 40 new, 10 failures (8 mesh_too_large, 2 invalid_geometry - mesher messages, not the new topology check), J 22.592 -> 8.940.
- Checks: (a) `run.json` `runtime` block present (RTX 4060 Laptop, 610.62, 8188 MiB; Julia 1.12.7; platform/python/sources); (b) report-only SPDI / listening-window / beam-p line per design, six scalars on every ok row (0 NaN); (c) failure character unchanged vs CP-8c / 6b; (d) not within 1 % - FASTER: mesh step 0.85 s vs 0.86 s (unchanged), solve 2.9 vs 4.2 ms/dof at equal dofs (solver untouched by the PR -> machine state).
- Beam p best vs seed: OSSE 2.05 -> 1.91; sculpt 2.40 -> 2.34 (fresh) / 2.06 (continuation). Qualitative at screen balloon.
- Sculpt anchors after 40-candidate runs: continuation (top 50) PINNED `profileH.points.3.1` lo 42/50, `profileV.points.3.1` lo 40/50, `profileV.points.4.1` hi 38/50, `profileV.mouthAngleDeg` lo 26/50, `profileH.points.4.1` hi 25/50; fresh seed-777 (top 5): no anchor, `profileH.mouthAngleDeg` hi 4/5. **No bound widened.**
- Item 4 replay (Sonnet subagent, offline, read-only): J recomputed exactly (max diff 0); K = 4, 25 % margin rejects 1 of 3,818 candidates (< 0.1 % GPU); K = 6 ~0.5 % on OSSE; no top-20 lost. Bound is too loose (dislope/flat unbounded, 60 % of band unsolved). Recommend not implementing as specified.
- Evidence: `docs/evidence/BL_LEARNINGS_GPU.md`, `docs/evidence/EARLY_REJECTION_REPLAY.md`, 4 run summary layers + manifest. Julia cleared after every search; end state no julia, 618 MiB.

## 2026-10-22 (cloud, PM) — Boundary Lab 0.5.0 learnings IMPLEMENTED: pre-solve mesh checks, symmetry-domain check, phasor module, live runtime provenance, CEA-2034 subset + beam shape (report-only) (senior reviewer: Claude + 1 Sonnet subagent)

> **LOCAL AGENT:** merge this PR (into `main`), then run `docs/BL_LEARNINGS_IMPLEMENTATION.md` section 4 (tonight's test plan). No objective, gate, threshold, plan file or contract field changed.

- New `hornlab_search/mesh/topology.py` wired into `mesh/build.py` (after read-back and on cache hits): open edges off symmetry planes / non-manifold / near-coincident vertices -> `GeometryInvalidError`; reduced mesh outside x>=0 / y>=0 -> `SymmetryMismatchError`. Measured on real meshes of 6 configs: all pass (0 bad edges, closest vertex pair ~1.5 mm vs ~0.3 um tolerance).
- New `hornlab_search/solve/phasor.py` (ours exp(-i w t) + unit acceleration vs Boundary Lab exp(+i w t) + 1 m/s velocity), tested against time-domain signals.
- `run.json` gains a live `runtime` block (Python, platform, nvidia-smi GPU/driver/memory, julia --version, source fingerprints of hornlab_beat_bem / hornlab_mesher / hornlab_bempp_bem).
- New `metrics/spinorama.py` (listening window, SPDI; honest subset, cuts stop at +-90 deg) and `metrics/beam_shape.py` (superellipse fit of the forward -6 dB balloon contour). Six REPORT-ONLY scalars via `search/evaluate.py::directivity_extras` (never in J, never fail a solve, ~0.07 s/candidate) and one report line per design.
- Deferred with direction + required rulings: coarse-to-fine early rejection (largest GPU saver; offline replay first) and a CPU-vs-CUDA qualification screen (frozen CP-7b rule).
- Offline suite (cloud, mesher installed): **553 passed, 1 skipped, 18 deselected, exit 0**.

## 2026-10-22 (local GPU box, ~11:40 EDT) — sculpt 400 (J -45.7 %, 3 anchors PINNED); `export-step` CLI; compare quadrants fix; beta quickstart; review page tooling

- **Sculpt 400** (user: "be aggressive and continue"): `runs/20261022T142919Z-screen-1db72d`, 400 new + 60 cached, 1 failure (invalid_geometry), seed J 30.945 -> **16.789**, 6.9 s/candidate. PINNED: `profileH.points.3.1` lo (28/46), `profileV.points.3.1` lo (39/46), `profileV.points.4.1` hi (32/46) - the disjoint anchor boxes now limit the search (wants slower mid-flare, larger V mouth). Not widened (needs user OK). Evidence `docs/evidence/HANDOFF_6b.md` follow-up section; summary layer + manifest in `docs/evidence/runs/`.
- **New CLI `hornlab-search export-step --run DIR [--top N] | --config YAML`** (senior report s3 item 4): wraps the existing `mesh/build.py::export_step` (closed solid, mm, full model, throat open). Exported top 3 of both sculpt runs (~1.07-1.15 L solids). Tests `tests/test_search_export_step.py` (2 offline + 2 mesher).
- **Fix:** `compare` read `quadrants` from a nested `mesh` key; real rows carry it top-level, so it printed `None`. Now reads both; regression test added.
- **Docs:** `docs/BETA_QUICKSTART.md` (target -> dry-run -> search -> report -> STEP); README command list updated.
- **Review tooling:** `tools/review/` builds a self-contained review page (objective in math notation, validation table, per-run convergence / beamwidth / DI / polar maps / profiles / Spearman sensitivity, open questions) from the local `runs/`; outputs gitignored.
- Offline suite **520 passed, 0 skipped, exit 0** (515 + 5 new). GPU end state: no julia, 578 MiB.
- Ownership note: touches `cli.py`, `tests/test_search_*` (task 08), `README.md` (03), `.gitignore` (03), new `tools/review/`; user-authorized local lane, flag for cloud review.

## 2026-10-22 (local GPU box, ~10:30 EDT) — HANDOFF 6b run: offline 515 PASS, doctor 10/10, FREEFORM symmetry consistent, sculpt 60 J -21.8 %; CP-8c reports generated; Next-action line corrected

- On `main` `f3704a3`. Evidence: `docs/evidence/HANDOFF_6b.md`; summary layers of the 3 new runs in `docs/evidence/runs/` (manifest appended).
- Corrected the Status "Next action": CP-8d already ran and FAILED (2026-10-14); not re-run, and must not be before the OSSE top-up.
- `hornlab-search report` generated for the four CP-8c runs (ca15be, 6bdcbd, ff569c, 852be3) - local `runs/<dir>/report.html`, gitignored.
- 6b step 1: offline suite **515 passed, 0 skipped, exit 0**. Step 2: doctor **10/10**. Step 3: dry-runs 1362 / 451 / 1636 dofs (cloud 1354 / ~452 / ~1638).
- 6b step 4: quarter (451 dofs, J 41.7813) vs full (1636 dofs, J 41.7537): max |diff| di 0.0043 dB, on-axis 0.0042, ripple 0.0042, beamwidth 0.051 deg -> **consistent** (bar 0.1 dB / 1 deg; OSSE CP-7d ref 0.023 dB).
- 6b step 5: `freeform_sculpt` budget 60, 0 failures, seed J 30.945 -> best 24.213 (-21.8 %, eval 26) vs freeform_hv -8.3 % over 722 evals; 6.7 s/candidate (541/h); no key pinned (max 2/6: profileH.mouthAngleDeg at hi, profileV.points.3.1 at lo). Dataset 3618 records (FREEFORM 784).
- GPU hygiene each step: julia none before, killed after (one host per step), VRAM baseline 546-627 MiB; end state: no julia, 613 MiB.
- Not started (needs user OK): Boundary Lab work, OSSE top-up, any bound widening, sculpt budget 400.

## 2026-10-22 (local merge lane) — main fast-forwarded to cloud tip 6d1d5c7 (oracle-approved); GPU-run summary layer committed to docs/evidence/runs/ (orchestrator)

- **Senior inventory:** the GitHub repo `llevaachingada/Hrns` (the outer working folder's remote) is EMPTY and holds nothing; the real project repo is `llevaachingada/Hornfab`. Remotes held exactly 3 branches — `main` (2a7bafb), `claude/wave-3-implementation-review-2dk4qe` (622776a), `ccr-455d2184-yj5zk4` (6d1d5c7, the Claude Code cloud branch, force-pushed by the cloud session) — plus two open DRAFT PRs: #12 (wave-3→main) and #14 (ccr→wave-3). No other work exists anywhere on the remote: `git log --all --not ccr-455d2184-yj5zk4` is empty, so a fast-forward of `main` to 6d1d5c7 loses nothing.
- **Merge executed:** `main` fast-forwarded 2a7bafb -> 6d1d5c7 (22 commits, 55 files, +10,061/−44): Phase-2 Stage A surrogate + NSGA-II, CP-8 campaign evidence, issue-#13 hardening, CP-8d diagnostics (docs), and the cloud's 152a829 (FREEFORM sculpt config, FREEFORM training-export fix, `compare`, DI guard) + 6d1d5c7 (Boundary Lab 0.5.0 research, docs-only, PROPOSED). Zero conflicts (strict ancestry).
- **Oracle sign-off (pre-merge review, glm-5.3):** PASSED. The only new code (152a829) reviewed line-by-line: `_param_value` FREEFORM path-key resolution correct and backward-compatible; `unit_matrix` NaN refusal and DI-provenance guard are fail-fast hardening (not regressions); `throat_radius_m` millimetre conversion correct; `compare` command self-contained, refuses mismatched grids/missing metrics; sculpt config bounds disciplined (disjoint anchor ranges; 41/41 mesh in the cloud). Chain integration clean: 152a829's parent is exactly 622776a (local head); store record/shard format unchanged (additive only).
- **Validation at the merged tree (sandbox worktree at 6d1d5c7, repo venv):** `compileall hornlab_search/` clean; **full offline suite 533 passed, 0 failed/errors/skipped, 436.9 s, exit 0** (only an upstream bempp_cl SciPy DeprecationWarning). Local main worktree untouched during testing.
- **GPU-run summary layer preserved (this commit):** all 7 local `beat_cuda` run dirs (d627d9 seed screen, 7e6e5b resume smoke, 9e5a5c CP-8b smoke, ca15be/6bdcbd/ff569c/852be3 = CP-8c runs 1-4) previously lived ONLY in gitignored `runs/`. Their summarized layer (run.json, config.yaml, best.json, search.ndjson, cma/*, verify; 108 files, ~16.6 MB, designs/ raw blobs excluded) is now committed at `docs/evidence/runs/` with an index README and `runs/manifest.sha256` (SHA-256 + bytes per file), per explicit user request 2026-10-22 — an admitted, user-approved exception to the parent evidence README's "never the data itself" rule (noted in files; raw data still never committed).
- **Superseded PRs:** #12 and #14 both MERGEABLE drafts whose heads are ancestors of 6d1d5c7; closed as superseded by the direct FF (no PR bodies needed — evidence already committed in the chain).
- **Oracle non-blocking follow-ups recorded in ISSUES:** (1) `_cmd_compare` uncaught IndexError if freqs_hz empty (cosmetic realism edge); (2) `exponent` alias resolves to the FIRST superellipse station only — pre-existing design-layer semantics, document before any multi-station config; (3) Boundary Lab docs are PROPOSED, not accepted scope — do not treat as backlog.
- No plan files touched; no thresholds changed; nothing rewound — every historical commit is in main's history.

## 2026-10-22 (cloud) — senior architecture report: sidechain Boundary Lab, do not become a plugin; status + to-do (senior reviewer: Claude)

- New `docs/SENIOR_ARCHITECTURE_REPORT_2026-10-22.md` (read first): where hornlab-search sits vs Boundary Lab / HornLab; decision: use Boundary Lab as is in its own environment (export projects, optional headless cross-check), keep Magnus's libraries as our engine, park the plugin; revised priority; CP-8c results table; to-do list (view reports, merge PR #14, HANDOFF 6b, STEP-export CLI, OSSE top-up, BL-1).
- Pushed to `main` on top of the local merge lane's `2311f92` (main already carried the Boundary Lab research/plan via the 6d1d5c7 fast-forward). Report section 3 corrects the stale "Next action" (CP-8d already ran and failed; do not re-run before the OSSE top-up).
- No code changed.

## 2026-10-21 (cloud) — Boundary Lab 0.5.0 research + integration plan (docs only; senior reviewer: Claude, 2 research subagents)

- Boundary Lab (JWSound) **0.5.0 released 2026-10-20**: adds Generator Plugins (geometry-provider API 1, `provider.json` in `<BL>/geometry_providers/`), plugin host services (queue solves, read results; GUI-only), a headless `blab project validate|solve`, project schema 10, BEAT Engine pinned (hard) to 0.6.0.
- New `docs/BOUNDARY_LAB_0.5_RESEARCH.md` (findings, conventions table, spot checks) + appendices `docs/research/boundary_lab_0.5/{bl_inventory,beat_compat}.md`; new `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md` (PROPOSED: BL-0 env, BL-1 `.blab.json` export, BL-2 BL-headless cross-check via the frozen CP-7b rule, BL-3 hornlab geometry-provider plugin; checkpoints CP-11a..d; D/E/F deferred).
- Key facts: our mesher's MSH 2.2 + Ath names (`SD1D1001` driven) already match BL; BL defaults mesh scale to 0.001 (silent killer 1); BL symmetry `xy/x/off` maps from `sizing.SYMMETRY_PLANE` (quadrants `12` unsupported); BL phasor `exp(+i wt)` vs our vendored engine `exp(-i wt)`; BL port is 1 m/s velocity vs our unit acceleration (normalized metrics comparable, absolute level/phase need conversion); BL CLI never shuts down its Julia worker (hygiene wrapper required); BL must not be installed in our venv (BEAT pin).
- Correction recorded (plan files frozen): `blab project solve` now IS Boundary Lab's CLI (12_RESEARCH_BASIS s1 / plan README row 3 predate it).
- No code changed. Decisions for the user in the plan, section 5.

## 2026-10-14 (cloud, ~05:00 UTC) — PR #14 REBUILT on the local head (622776a): local issue-#13 set adopted, cloud duplicates dropped; FREEFORM sculpt + export fix + `compare` added (senior reviewer: Claude)

> **LOCAL AGENT:** PR #14 is NO LONGER superseded. Branch `ccr-455d2184-yj5zk4` was rebuilt ON TOP of this branch's head `622776a`; it contains your e0b9b61/11304f6 code unchanged plus only non-duplicate additions. Merge it now (no GPU job running), then follow `docs/HANDOFF_LOCAL.md` section **6b**.

- Reconciliation: the cloud's F1-F4/F6/F7 duplicates of the local issue-#13 set are DROPPED (the local set is what CP-8d ran on). Kept from the cloud, each with a test: DI-provenance guard in `train_surrogate` (#13 item 5; ok records with di_source != balloon refuse); `unit_matrix` refuses NaN instead of filling 0.5 (#13 item 10); `propose` with 0 designs exits 1.
- **Bug fixed:** `to_training_arrays` read X with `params.get`, so every FREEFORM search key (paths like `profileH.points.2.1`, alias `exponent`) was NaN; the CP-8c run-3 FREEFORM records (722) would have trained on invented inputs. Now resolved via `families.param_get`. Raw data was never affected.
- **New `examples/freeform_sculpt.yaml`:** FREEFORM with 11 searched knobs (8 wall-anchor radii, 2 mouth angles, superellipse exponent) vs 3 in `freeform_hv` (whose low yield, J -8.3 % on a razor plateau, the local agent traced to the pinned point lists). 90x90 deg, 700-5500 Hz, ~37 cm mouth, 195 mm deep. z, throat radius, throat angles pinned; anchor ranges disjoint and increasing. Real mesher in the cloud: 41/41 samples mesh; quarter domain 1354 dofs at 5.5 kHz.
- FREEFORM quarter domain is valid by construction (mesher agrees, yz+xz); GPU agreement UNMEASURED -> `freeform_sculpt_symcheck_{quarter,full}.yaml` + new `hornlab-search compare` (report only; bar not frozen, proposal in NOTES).
- `throat_radius_m` handles FREEFORM (f11 was never computed for it). Mesher wall-port feature request and the HornLab-author naming question recorded in NOTES.
- Offline suite (cloud, mesher installed, torch CPU): **514 passed, 1 skipped, 18 deselected, exit 0**. No gate threshold, plan file or `freeform_hv.yaml` changed.

## 2026-10-14 (cloud, ~02:05 UTC) — NOTICE: surrogate fixes waiting on `ccr-455d2184-yj5zk4`; merge AFTER CP-8c, BEFORE CP-8d (senior reviewer: Claude)

> **LOCAL AGENT: do not run CP-8d (`surrogate train` / `propose`) on this branch's current code.** Issue #13 fixes F1-F6 are on `ccr-455d2184-yj5zk4` (draft PR #14 into this branch), with offline suite 455 passed / 30 skipped. They touch only `surrogate/**`, `_cmd_surrogate`, surrogate tests and `HANDOFF_LOCAL.md`, so the running CP-8c search is unaffected. **Do not pull mid-run.** When CP-8c is closed and julia is cleared:
> 1. `git fetch origin ccr-455d2184-yj5zk4` then `git merge origin/ccr-455d2184-yj5zk4` (conflicts expected in `docs/CONTINUITY.md` / `docs/ISSUES.md` only: keep every entry, newest first).
> 2. Run `pytest -m "not slow and not gpu and not crosscheck"` (expect ~485 with the mesher), paste it, push.
> 3. Then CP-8d. Note: `propose` now refuses a gate-failing bundle, so with ~225 held-out CP-8d stops after `train` ("indicative only"), as HANDOFF already says.
> Review: `docs/SENIOR_REVIEW_2026-10-14.md` (on the fix branch). This entry is docs-only.
>
> **LOCAL AGENT RECONCILIATION (2026-10-13, ~20:30 local): the SAME issue-#13 fixes were independently implemented on THIS branch (commit 567ec8b, next entry) before this notice arrived** — the hardening lane was user-authorized, ran offline/CPU-only, and was discovered colliding with this notice only during the push rebase. Commit 567ec8b covers EIGHT items (this notice lists six: F1-F6) and the full offline suite WITH the mesher passed 488/0-deselected-other on this branch. **Do NOT merge `ccr-455d2184-yj5zk4` on top** — that would double-apply overlapping changes in `surrogate/**`. Cloud owner: diff 567ec8b against PR #14 and adopt ONE set (drop the other). CP-8d proceeds on this branch's fixed code either way. Note one deliberate difference: `propose` here refuses by default but has `--allow-unvalidated`, so the runbook's "indicative only" CP-8d (held-out 225 < 500) can still propose and solve round 1 — which HANDOFF intends — while the notice's wording suggests CP-8d stops after `train`.

## 2026-10-13 (local GPU box, ~23:10) — store/CLI pipeline fixes + CP-8d glue implemented; full offline suite 498 PASS (fixer lane, CPU-only; fix queued by the senior review)

- Implemented all five queued items (offline/CPU-only while run 3 flew): (1) `dataset stats` now reports **`missing families`** (R-OSSE will be listed, by design) + **`duplicate designs`** count; (2) `verify_store` checks Y-metric array **shapes** vs the record's own `solve.freqs_hz` and reports `bad_arrays` separately — exactly what `to_training_arrays` would otherwise silently drop; `dataset verify` exits 1 on either `bad` or `bad_arrays`; (3) **resume guard**: `search --resume` compares `run.json["config_sha"]` to the current config and REFUSES on mismatch (naming both SHAs) unless `--allow-config-change` is passed — the mid-campaign weight/bound edits recorded as follow-ups can no longer silently mix old-J and new-J rows; (4) `surrogate train` headline split: `GATES FAILED: <names>` vs `GATES REFUSED (indicative only): all <N> measured gates pass; held-out <X> < 500 formal floor`; (5) **new `surrogate round` subcommand** (`hornlab_search/surrogate/round.py` + CLI): loads proposals.json, solves each through the normal `evaluate` path into a FRESH run dir with its own ndjson, computes `round_report`, and writes atomic `ismo_round1.json` with report + per-proposal rows + `random_true_J` provenance + exploit/explore-medians + exploit parameter spread + store counts before/after + bundle gate status + config_sha — the CP-8d honesty artifact the reviews demanded.
- **Behaviour changes (mid-campaign callers):** resume of a run whose `config_sha` mismatches now REFUSES (escape hatch `--allow-config-change`; known false-positive edge: a run started with `--backend` override — see its report); `dataset verify` exit code now includes bad array shapes (new failure class if legacy data has any; current store is clean); `dataset stats` prints an extra line; `surrogate train` headline wording changed; `surrogate` gained the `round` action (solve-per-proposal only when invoked). Ownership note: touches `dataset/**` + `cli.py` beyond `_cmd_surrogate` — user-authorized, flagged for cloud review like the #13 lane.
- Tests: lane's own 88 + 11 targeted pass, compileall clean; **full offline suite 498 passed, 18 deselected, exit 0** (84.83 s, alongside the GPU run). Scope check: only `dataset/store.py`, `cli.py`, `surrogate/round.py` (new), two test files; no docs/plan/examples/conftest, no GPU, no runs/dataset/cache writes.
- With this, every prerequisite the senior reviews set for CP-8d is landed: verdict persistence + propose refusal, config freeze, dedup, meta prints, NaN conventions, atomic writes, duplicate/missing-family visibility, array-shape verification, resume guard, and the persisted round artifact.
- Addendum (corrective commit, same hour): commit 11304f6 touched CONTINUITY but missed the matching `docs/ISSUES.md` update (my oldString mismatch) — the push rule was broken once; this corrective commit restores it. ISSUES now carries the (c)-IMPLEMENTED status, the second stale "5/6 at q lo" statement (line 25, digest note) corrected, and the same PR-#14 supersession annotation the cloud notice carries in CONTINUITY.

## 2026-10-13 (local GPU box, ~22:40) — senior pipeline/plan review reconciled; evidence corrections applied (glm-5.3 oracle + local agent)

- The second senior review (store/evaluate/report at scale, CP-8d plan-vs-API, evidence audit) returned 17 findings while run 3 flew. Docs corrections applied NOW (full block in ISSUES): **(1) CP-8c yields THREE families, not four** — `throat_adapter.yaml` is `family: OSSE`, so R-OSSE stays 0 and `dataset stats`' family warning (fires only above an 80 % share) will NEVER flag a MISSING family; HANDOFF §5's "all four families present" criterion is unsatisfiable as written → amended CP-8c criterion recorded in evidence: **verify OK + OSSE/ICW/FREEFORM present** (R-OSSE deliberately absent; adding a config is the cloud owner's call). HANDOFF_LOCAL.md itself left untouched (not mine to edit — the correction lives in evidence + ISSUES). (2) **OSSE `q` pinning corrected**: final data shows `q` top-6 **0/6** near lo (23 % of ok rows within 2 % of 0.9, Spearman +0.49 — attracted, NOT pinned; the earlier "5/6" was the in-flight 13:40 snapshot); `n` stays 6/6. (3) run-1 snapshot "seed J 22.07" corrected to **22.592** (22.07 was the smoke seed). (4) ICW warning scope restated: 24 warning LINES all at one timestamp → plausibly ONE design of 800; per-design attribution is not recorded. (5) `manifest.sha256` wording corrected: it hashes the METADATA layer (run books/ndjson/index/shard JSONLs), NOT the per-record `.npz` labels or `traces/` (covered by `dataset verify` as existence/validity, not bit-identity); line-3 indent fixed so `sha256sum -c` parses. (6) the digest stamps `generated_utc` from now on.
- **CP-8d misreading guards adopted verbatim** (14-item list in ISSUES): refusal-vs-failure headline with `n_heldout` vs the 500 floor; solved-only medians AND exploit/explore reported separately; `random_true_J` provenance (CMA gen-0 samples, penalty-row convention); proposals' parameter spread (the 30 exploits are near-clones of one NSGA basin); frozen `pred_J` + bundle/config_sha/store count recorded; results persisted as `ismo_round1.json` + `docs/evidence/CP-8d.md`.
- **Next implementation lane dispatched (store/CLI small fixes, CPU-only):** `n_duplicate_designs` + `missing_families` in `stats()`/`stats_report`, Y-array shape check in `verify_store` (report `bad_arrays` separately), `config_sha` comparison on `--resume` (unmissable warning → refuse unless overridden), the refusal-vs-failure headline split in `surrogate train`, and the CP-8d round helper writing `ismo_round1.json`. These cross task-ownership lines (dataset/**, search/**, cli.py) — implemented under the user's explicit authorization, flagged for cloud review exactly like the #13 lane.
- Checked clean at scale (no action): append cost, shard roll, in-memory index, trace sampling (4.1 % vs 5 % set), torn-line recovery, ndjson durability, digest arithmetic (2434 = 1500+1+130 smoke+3 older OSSE + 800 ICW; `skipped_grid_mismatch` 133 = the 4500 Hz-grid records; held-out 225.2 = 15 % × 1501).

## 2026-10-13 (local GPU box, ~23:30) — CP-8c run 3/4 COMPLETE (freeform_hv): CMA converged at 722/800 (`tolfun`), best J 30.54 (-8.3 %); dataset now three families + new stats lines live (local agent)

- Run `runs/20261013T234724Z-screen-ff569c`, **stop: `cma: tolfun`** (convergence, not budget): **722 rows = 721 ok + 1 failed** (`invalid_geometry`), torn 0, ok metrics null 0, zero in-run dups. **Seed J 33.3086 → best J 30.5434 (-8.3 %)**; median ok-J 30.545; best `n_dof` 2747.
- **Low-yield finding (recorded as a dataset caveat):** `freeform_hv` exposes only 3 searchable keys (the profile point lists are pinned) and its objective is 87 % coverage term → CMA converged onto a razor-thin plateau (ok J p5/p95 = 30.544/30.760). FREEFORM contributes family *presence* and low-diversity labels only; the yaml's own "control-point mapping UNRESOLVED" note is the root cause. Workers self-cleared (watchdog end state `julia=0`), VRAM 290 MiB, `ff_stderr.log` empty (zero mesher warnings). Digest limitation noted: per-key/pinning tables skip FREEFORM (dotted keys into nested containers).
- Dataset: **3156 records (3032 ok, 124 failed), 7 shards, 513.6 MB** — OSSE 1634 + ICW 800 + FREEFORM 722; the new `dataset stats` lines are live and say `missing families ['R-OSSE'], duplicate designs 14` (0.44 % — run/search seed double-solves; train-side dedup from e0b9b61 keeps them out of the gate arithmetic). Zero mesher warnings on FREEFORM.
- Evidence: new `docs/evidence/CP-8c_freeform_hv.md`; digest/log/manifest refreshed (digest generator hardened for container params: `__unique_count` instead of enumerating 721 reprs).
- **Next: run 4/4 `throat_adapter --budget 400`** (quarter domain, band 2000–6500 Hz, weights {flat 1.0, load 0.5}; est ~1.5-2 h at ~13-17 s/candidate), then the CP-8c close: final `dataset stats` + `dataset verify` + digest + commit; then CP-8d (indicative) with the `surrogate round` helper.

## 2026-10-13 (local GPU box, ~01:10 Oct 14) — CP-8d: Stage A train FAILED twice on the real pool; model NOT used; runbook fixes exhausted down to "more records" (local agent)

- CP-8d step 1 (`surrogate train --config examples/osse_baseline.yaml`, CPU torch, real BEM records): **epochs 300** → spearman 0.9673 PASS / topk_overlap 5 of 20 **FAIL** / bw_mae 2.110° **FAIL** / di_mae 0.287 dB PASS / invalid_acc 0.8571 PASS / monotonic_flips 0 PASS → `GATES FAILED`, exit 1. **Epochs 600** (the runbook's own retry) → spearman **0.9861** / topk **15 of 20** / bw_mae **1.704** / di_mae **0.232** / invalid_acc **0.952** — ALL PASS, but `monotonic_flips` went 0→**1** (needs 0) → `GATES FAILED` again, exit 1 (tables verbatim in `docs/evidence/CP-8d.md`).
- Both runs: pool considered 2034 (every OSSE-family record incl. throat_adapter), selected **1501**, `skipped_grid_mismatch` **533** (133 smoke-grid + 400 throat_adapter-grid records), `skipped_bad_arrays` 0 (the new array-shape verify clean), 1 duplicate dropped pre-split, **objective delta (recomputed vs stored) = 0** — the current weights are exactly the collection weights. **Held-out 285 < 500** (the cluster holdout overshoots 15 % on clumped CMA data, as the review predicted).
- **Runbook verdicts applied:** exit 1 ⇒ **do NOT use the model** — `propose` and the new `surrogate round` helper were NOT run; `round_report['working']` was never measured → **CP-8d = FAIL** (not merely "indicative"). Twice-failed on the same step ⇒ hard rule 8: stopped and appended the dated block **`2026-10-14 cp-8d`** to `NOTES_FOR_SENIOR.md` (both tables; the three decisions needed).
- Honest reading (labelled as such): the Stage A machinery WORKS on real data — five measured gates improve monotonically with epochs and four of the gate numbers sit at or near their thresholds; what blocks a formal pass is record quantity (held-out 285 vs 500; pool 1501) plus the single `monotonic_flips=1` whose cause (sweep invalid-boundary vs genuine non-monotonicity) is NOTES question (2). `--lib-sha` is moot (one lib_sha everywhere). The remaining runbook fix needs the user: an OSSE top-up of ~1900 records via `search --resume runs\20261013T123136Z-screen-ca15be --budget 1900` ≈ **10.2 h** at the measured 187/h (or the CP-9 cloud path).
- No gate threshold touched; no GPU hygiene issues (VRAM 290 MiB idle, no workers). CP-8d evidence: `docs/evidence/CP-8d.md` (attempt-1/2 tables + decision + next path). Issues/ISSUES.md updated.
- **Next: the user decides the top-up and the two NOTES questions; then retrain → (if gates pass) propose → `surrogate round` → `round_report['working']`.** Session's remaining deliverable: the master PASS/PARTIAL report.
- Addendum (~01:40): **`monotonic_flips` DIAGNOSED** (read-only sweep replay on the saved bundle; no code touched). Seed 0 reproduces 1/50; seeds 1-5 give **1, 1, 2, 2, 2 of 50** — a 2-4 % flip rate, NOT a hard defect. Three causes: (a) invalid-transition degeneracy (the flagged sweep's zig-zag sits at `p_ok` 0.996→0.569, tol inflated to 1 J by the 1000-penalty row); (b) genuine 1-3.7 J model undulation on fully-valid lines (p_ok ≥ 0.98); (c) tiny-wiggle sensitivity — the flat tolerance `1e-3·max(1,max|y|)` = 0.021-0.023 J on near-flat tails counts ±0.05-0.3 J wiggles. Details in `docs/evidence/CP-8d.md` + the `2026-10-14 cp-8d ADDENDUM` NOTES block (owner rulings wanted on tolerance semantics / invalid-crossing category; thresholds untouched).

## 2026-10-13 (local GPU box, ~01:00 Oct 14) — CP-8c CLOSED: run 4/4 (throat_adapter) complete; final stats/verify OK; campaign totals (local agent)

- Run `runs\20261014T025335Z-screen-852be3`, budget stop **400 rows = 400 ok + 0 failed** — the campaign's only zero-failure run (throat_adapter pins `a_deg`/`L`/`exponent`/`aspect_ratio`, so no too-large meshes; `ta_stderr.log` EMPTY). **Seed J 9.1592 → best J 5.9834 (-35 %)**; median solve 11.78 s; best `n_dof` 3216 with `a0_deg` 2.06. Workers clean; VRAM 290 MiB.
- **CP-8c close-out:** final `dataset stats` — **3556 records (3432 ok, 124 failed), 8 shards, 587.2 MB**, families OSSE 2034 / ICW 800 / FREEFORM 722, `missing families ['R-OSSE'], duplicate designs 14`, traces 4.3 %, **GPU solve 46,930.8 s (13.0 h)**; final `dataset verify` **OK: 3556 re-read, 0 bad, 0 bad arrays** (the new shape check covers the whole store). Campaign wall ≈ **14.9 h** across the four runs (osse 8.02 + icw 2.9 + ff 2.55 + throat 1.42).
- **Honest CP-8c verdict: PARTIAL on the runbook's literal criterion** ("all four families" is unsatisfiable — `throat_adapter.yaml` is `family: OSSE`; R-OSSE has no example config): **verify OK + 3 of 4 families present** under the amended criterion recorded in the evidence (senior review finding (a)). Adding an R-OSSE config is the cloud owner's call, not mine.
- Issue-#13 store arithmetic (printed by the tooling now): OSSE pool kept 1501 of 1634 (`skipped_grid_mismatch` 133), held-out **225 < 500** → CP-8d's formal gate will print `GATES REFUSED (indicative only)`.
- Evidence: new `docs/evidence/CP-8c_throat_adapter.md` (incl. the close-out table for all four runs); digest (7 runs) + logs + manifest refreshed.
- **Next: CP-8d (indicative)** on the fixed code: `surrogate train --config examples\osse_baseline.yaml --out surrogate_osse.pt` (CPU; expect the REFUSED headline + exit 1), `propose --allow-unvalidated`, then `surrogate round` (40 real BEM solves, one at a time) → `ismo_round1.json` + `docs/evidence/CP-8d.md`, then the master PASS/PARTIAL report.

## 2026-10-13 (local GPU box, ~20:15) — issue #13 hardening IMPLEMENTED; full offline suite 488 PASS (local agent; fixer lane, CPU-only while run 3 flies)

- **All eight hardening items from the issue #13 review are implemented** (offline/CPU-only, alongside the GPU campaign): the Stage A bundle now (1) persists the gate verdict (per-gate value/threshold/pass, `n_heldout`, warnings) and (2) freezes the config contract (family / ordered keys / per-key bounds {lo,hi,log} / freqs); `surrogate propose` **refuses** a bundle with no verdict, a failing verdict, or a family/keys/bounds/freqs mismatch — `--allow-unvalidated` is the explicit escape hatch for the CP-8d indicative flow; the gate report is evaluated BEFORE saving (atomic tmp+os.replace) and a failed retrain **keeps an existing PASSING bundle** instead of clobbering it; rank-gate labels are recomputed from the metric arrays with the CURRENT weights/target (stored objective only feeds `objective_delta_max/mean`); `surrogate train` prints the `to_training_arrays` meta (`n_considered/n_selected/skipped_grid_mismatch/skipped_bad_arrays/skipped_keys`) with a loud WARN on drops; duplicate `design_hash` rows are deduped before the cluster holdout (`n_duplicates_dropped`); `round_report` coerces `true_J >= PENALTY_FAILED` to NaN (failed proposals excluded from the median, counted in `n_solved_failed`); NSGA-II maps non-finite objectives to `PENALTY_FAILED` (NaN can never rank as non-dominated); bundle/`proposals.json`/`pareto.json` writes are atomic. **`gates.py` thresholds untouched (0 diff lines).**
- **Behaviour changes a caller must know:** `propose` now refuses by default (it previously proposed from any bundle); `train` reports `kept_existing_bundle`, `n_duplicates_dropped`, `objective_delta_max/mean`; bundle `meta` gains `gate_report` + `bounds`.
- Tests: 22 focused surrogate/ISMO/NSGA tests pass (12.15 s); compileall clean; **full offline suite 488 passed, 18 deselected, exit 0** (85.93 s) — run while the freeform_hv GPU run was active. Scope check: only `surrogate/**`, `search/nsga.py`, `cli.py` (_cmd_surrogate + parser + one supporting import), and the three test files changed; no docs/plan files, no GPU, no runs/dataset/cache writes, nothing committed until this gate passed.
- This closes the gate-integrity prerequisite the two senior reviews set for CP-8d: none of CP-8d's numbers were quotable until this landed — it now has (pending the cloud owner's review of the diff).

## 2026-10-13 (local GPU box, ~19:50) — CP-8c run 2/4 COMPLETE (icw_termination 800): best J 12.20 (-78 % vs seed); dataset now two families (local agent)

- Run `runs/20261013T204408Z-screen-6bdcbd`, budget stop: **800 rows = 787 ok + 13 failed** (`invalid_geometry` 5, `mesh_too_large` 8), torn 0, ok rows with metrics null 0, zero in-run dups. **Seed J 55.7357 → best J 12.2009 (-78 %)**; median ok-J 12.87; best `n_dof` 2823.
- Throughput: **13.0 s/candidate (278/h)**, GPU solve 8688 s (~2.4 h), wall 2.9 h; VRAM never exceeded ~2 GiB on this family. Zero monitoring alarms; post-run reaped BOTH idle worker hosts (incl. one `julialauncher.exe`), VRAM 411 MiB.
- Dataset: **2434 records (2311 ok, 123 failed), 5 shards, 395.3 MB** — OSSE 1634 + **ICW 800**; the single-family warning is GONE (2 of 4 families present). `dataset verify` re-runs after runs 3-4.
- **ICW data-quality note (bounded):** mesher warning `outer wall self-intersects ... normal flip near azimuth row 0 ... the acoustic (inner) surface is unaffected` — 24 occurrences, ZERO new after 17:06 local (a few % of designs; rows still validate). Recorded as a caveat on ICW records; senior/oracle pass warranted before trusting ICW exterior physics beyond the inner surface. `termination` is categorical (`flat_baffle` in all ok rows) — the digest generator now handles categorical params (was crashing on `float('flat_baffle')`; fixed and re-run).
- **ICW bound pinning (new finding, follow-up):** best designs **fully pinned at the `hold_end` LOWER bound 0.55** (top-6 6/6, Spearman vs J +0.64) and 4/6 near `kappa0` lo = 0.0 (median 0.0016 — the search wants κ₀ ≈ 0; 0.0 is already the schema floor). Candidate: widen `hold_end` lo below 0.55 subject to the repo's `hold_start < hold_end` rule + mesher validation. Recorded, NOT changed mid-campaign.
- Issue #13 note: CP-8d trains on OSSE, so the ICW pool does not enter the OSSE gate arithmetic (digest OSSE pool unchanged: kept 1501 of 1634, held-out 225.2 < 500 → Stage A remains "indicative only").
- Evidence: new `docs/evidence/CP-8c_icw_termination.md`; digest/log/manifest copies refreshed (manifest includes the icw run's ndjson/json files).
- **Next: run 3/4 `freeform_hv --budget 800`** (full H/V domain — expect a slower candidate), then `throat_adapter` 400, then final stats/verify + digest to close CP-8c; then CP-8d.

## 2026-10-13 (local GPU box, ~16:50) — CP-8c run 1/4 COMPLETE (`osse_baseline` 1500): best J 6.106 (-73 % vs seed); `dataset verify` OK (local agent)

- Run `runs/20261013T123136Z-screen-ca15be`, budget stop: **1500 rows = 1405 ok + 95 failed** (`mesh_too_large` 93, `invalid_geometry` 2), torn 0, ok rows with metrics null 0, zero in-run duplicate designs. **Seed J 22.5921 → best J 6.10609 (-73 %)**; median ok-J 6.45.
- Throughput: **19.2 s/candidate (187/h)**, GPU solve 26,067 s (~7.2 h), wall 8.0 h. Live monitoring: 5-min watchdog + 30-min review ticks (11 ticks); **zero alarms the whole run** — no stall, no junk, exactly one `julia` host, VRAM cycles 511 MiB–4.3 GiB on the 8 GB card. Post-run: idle host reaped, VRAM 419 MiB.
- Dataset: **1634 records (1524 ok, 110 failed), 4 shards, 273.4 MB**, 100 % OSSE. **`dataset verify` OK — 1634 records re-read, 0 bad** (will re-run after runs 2-4).
- Bound pinning on the final data: best designs fully pinned at the `n` lower bound (2.0) and 5/6 near `q` lo (0.9); `a_deg`/`exponent` interior — the CP-8b widening held, and the active constraints for this objective are `n`/`q` (follow-up: widen `n`/`q`, mesher needs only `> 0`; recorded in ISSUES, NOT changed mid-campaign).
- Issue #13 arithmetic, final: OSSE pool kept **1501** of 1634 (`skipped_grid_mismatch` **133** = the 4500 Hz smoke records), held-out at 15 % = **225.2** < 500 → the CP-8d OSSE gate will refuse → reported as **indicative only**, as predicted. A formal OSSE pass would need ~3,400 osse_baseline-grid records (~17 h more GPU).
- Evidence refreshed and pushed this commit: `docs/evidence/{CP-8c_data_summary.md, data_summary.json, logs/*, manifest.sha256}` + the final block in `CP-8c_osse_baseline.md`.
- **Next: run 2/4 `icw_termination --budget 800`** (est ~4-4.5 h at icw's expected ~20 s/candidate), then `freeform_hv` 800, `throat_adapter` 400, then `dataset stats` + `verify` close CP-8c, then CP-8d.

## 2026-10-13 (local GPU box, ~13:40) — agent-readable data digest committed; new `n`/`q` pinning finding (local agent)

- **New: `docs/evidence/CP-8c_data_summary.md` (12 KB) + `data_summary.json` (56 KB)** — a read-only digest of every run dir + the dataset, so a cloud agent with no access to the gitignored blobs can understand the outputs: per-run row/ok/fail/torn counts; J stats (min/median/mean/max, seed vs best); a per-key table (seed/lo/hi/min/median/max, **Spearman vs J**, fraction within 2% of each bound, **top-6 pinning**); objective-term medians; failure kinds with a sample message and the median params of the refused designs; timing/throughput; `di_source`/quadrants; and a dataset section with the pool composition. Generator: temp `data_summary.py` (read-only, CPU; regenerate at the end of CP-8c).
- **Issue #13's trap, quantified:** OSSE pool considered 1170 → kept **1037**, `skipped_grid_mismatch` **133** (the smoke runs' 4500 Hz grid), majority grid = 5500 Hz / 12 pts; held-out at 15% = **155.5** vs the formal floor **500** → the Stage A OSSE gate will REFUSE (indicative only), as predicted.
- **New finding (snapshot of the still-running `osse_baseline` search, ~1036 rows):** the best designs are now INTERIOR in `a_deg`/`exponent` (CP-8b fix works), but **fully pinned at the LOWER bound of `n`** (top-6 6/6 at `n` lo = 2.0) and 5/6 at `q` lo = 0.9; Spearman vs J: `n` **+0.75**, `q` **+0.56** — both want to be *smaller*. So for this objective the active constraints are `n` and `q`, not `a_deg`/`exponent`. Mesher limits: `n > 0` and `q > 0` while `s != 0` (`families.py::_validate_osse_like`), so both could be widened downward. **Recorded as a follow-up, not changed now** (a mid-flight bound change would break the running run's consistency and the surrogate's unit cube).
- Digest data-quality facts: torn lines 0 in all runs; ok rows with all-NaN metrics 0; X NaN fractions 0; one duplicated `design_hash` (the seed, expected).

## 2026-10-13 (local GPU box, ~13:20) — CP-8 evidence committed to git; CP-8c run 1 progress (local agent)

- **New: `docs/evidence/`** — durable checkpoint evidence in git (user request): `CP-8a.md`, `CP-8b.md`, `CP-8c_osse_baseline.md` (verbatim terminal output), `logs/` (copies of the live monitor logs: 5-min watchdog + 30-min review ticks), and **`manifest.sha256`** (SHA-256 + byte size of every raw local artifact: both run dirs' `search.ndjson`/`best.json`/`config.yaml`/`run.json`, the CP-8b `report_cp8b.html`, and the dataset `index.jsonl` + 3 shards).
- **Raw-data policy (why not everything is in git):** `dataset/`, `runs/`, `cache/` are gitignored by design (`.gitignore` lines 4-6) and now large — `dataset/` is 1069 files / **180.6 MB / 1128 records** (~160 KB per record; CP-5 projected 0.78-1.4 GB at 10k records). Committing the blobs would bloat the repo and break the convention; the manifest makes them verifiable without committing them. To move raw data, use a data branch / release asset, not the code branch.
- **CP-8c run 1 of 4 (`osse_baseline`, budget 1500) — snapshot 13:11 local** (`runs/20261013T123136Z-screen-ca15be`, still running): 988 rows, ok 893 / failed 95 (`mesh_too_large` 93, `invalid_geometry` 2), torn 0, ok rows with `metrics=null` 0, no duplicate design hashes, best J **6.11** (seed 22.07, -72%), median solve 18.05 s, 213 rows/h. Live monitoring: 5-min watchdog + 30-min ticks (ticks 1-3 all clear: no stall, no junk, single `julia` host, VRAM ≤ 4.3 GiB).
- Dataset at 13:13 local: 1128 records (1018 ok, 110 failed), 3 shards, 100 % OSSE. Remaining runs: `icw_termination` 800, `freeform_hv` 800, `throat_adapter` 400.

## 2026-10-13 (local GPU box) — CP-8a PASS, CP-8b PASS, bounds widened; hardening review filed as #13 (local agent)

**CP-8a PASS (real box, mesher tests unskipped):**
- `pytest -m "not slow and not gpu and not crosscheck"`: **480 passed, 18 deselected** in 164.42 s, `$LASTEXITCODE=0` (the cloud suite's 30 skips were mesher-gated → all unskipped here, matching the expected ~480).
- `hornlab-search doctor`: **10/10 PASS** (python 3.12.10, pinned SHAs, gpu check, beat_cuda ready, config round-trip, gpu-hygiene 0 hosts, VRAM 395 MiB).
- `pytest -m "slow or gpu or crosscheck"` (hygiene first: no julia, VRAM 395 MiB): **18 passed, 480 deselected** in 500.62 s, exit 0. Post-run: stray julia host killed (`taskkill /F /IM julia.exe`, PID 28464), VRAM back to 395 MiB. Consistent with CP-7: beat vs bempp ≤ 0.055 dB on the 2,316-dof quarter mesh; full-vs-quarter ≤ 0.031 dB ≤ 3 kHz.
- `dataset stats` before CP-8b: 134 records (119 ok, 15 failed), 100 % OSSE, traces 3.7 %, GPU solve 566.9 s total.

**CP-8b PASS — widen from the mesher's own limits (empirically verified, not guessed):**
- Acceptance probe (`hornlab_mesher` 0.2.4, profile level + REAL `build_mesh` at search_smoke screen settings): `a_deg` = 0.0/2.0/5.0/10.0/15.0/25.0 all mesh (crossing `a0=30` fine; radius monotone); `exponent` 1.0/1.5/2.0/4.0 mesh, 0.5 refuses (azimuth chord). Worst combined corner → clean `MeshTooLargeError`/`GeometryInvalidError` (refusal OK, no consistency crash). **Correction to the handoff:** "must keep `a_deg > a0_deg`" is NOT enforced anywhere — the OSSE radicand can only fail with a NEGATIVE `a0` steeper than `a`; repo bounds keep `a0_deg ≥ 2` so it cannot fire. Mesher floors: `a_deg ≥ 0` (coverage_angle non-negative, `profile_formulas.py:1231`), OSSE `exponent` unvalidated (clamp max(e,1e-6) at `profile_sampling.py:481`; itself overflow-broken at 1e-6), FREEFORM-station `exponent` hard [2,16] (`freeform.py:968`, mirrored `families.py:389-392`).
- Edits (`examples/search_smoke.yaml`, `examples/osse_baseline.yaml`): `a_deg` lo 25.0 → **5.0**, `exponent` lo 2.0 → **1.0** (5 has margin over the degenerate ~0 floor; 1.0 is 2× the empirically refused 0.5). `freeform_hv.yaml` exponent stays 2.0 (mesher hard [2,16] for FREEFORM stations — widening below would only produce rejected designs); `throat_adapter.yaml` stays pinned.
- Dry-run both configs: seed still meshes (search_smoke 2,598/3,000 screen dofs; osse_baseline 3,850/5,000).
- Rerun `search_smoke --budget 60` (`runs\20261013T121958Z-screen-9e5a5c`): 60 new evals in 254.5 s GPU (5.2 s/candidate, 690/h), seed J=22.0678 → best J=10.7776, failures {invalid_geometry: 1, mesh_too_large: 7} (classified, no crash); julia host killed after.
- Report bounds table: **no key pinned** — `a_deg` best 33.54 (0/6 of top-6 near lo 5), `exponent` best 4.67 (0/6 near lo 1). Old pins (a_deg=25.0, exponent=2.0) gone → pass criterion met with one widening.
- Honest caveat: this rerun's best J (10.78) is HIGHER than the old run's (9.66) at equal budget — 60-eval CMA variance, not a regression; the actionable outcome is the bounds are no longer active constraints.

**Hardening review (senior reviewer/oracle, read-only) → filed as issue #13; circle-back before/with CP-8d.** Top risks (full table + ready-to-paste fixes in #13): 1) gate verdict not persisted — `surrogate propose` accepts a failed/never-rated bundle and a failed retrain silently overwrites a passing `--out`; 2) rank gate compares stored objectives (solve-time weights) against predictions under current weights; 3) bundle does not freeze the bounds/family/keys/freqs it was trained under (bounds edited TODAY — commit before training); 4) pooling `search_smoke` (500-4500 grid) with `osse_baseline` (500-5500) silently drops all search_smoke records in `to_training_arrays` without printed counts — the ≥ 500 held-out arithmetic must use the printed post-filter count; 5) no `di_source` guard on the surrogate path; 6) duplicate seed rows can straddle the cluster holdout. **Do NOT weaken any gate threshold.**

## 2026-10-13 (cloud, high-frequency research) — options for 12 kHz on the 8 GB card (orchestrator: Claude)

- `docs/HIGH_FREQUENCY_OPTIONS.md`. Findings: (1) the 5.5 kHz ceiling is our 5,000-dof throughput cap on a LARGE seed horn (quarter area 0.282 m2), not the card's limit (8.9k quarter dofs fit); a smaller horn reaches 12 kHz inside existing caps. (2) In the pinned beat source the memory-saving fused Burton-Miller path is enabled for `:cpu` and `:metal` only; the CUDA exterior driver assembles four dense operators, and a unit-tested CUDA direct-system assembler is never called. Wiring it in would roughly 2.45x the GPU dof ceiling [inferred]; needs Collin's OK or a pinned fork (rule 1). (3) CPU backend (fused on, 32 GB RAM) can do a 19k-dof high-band finalist check at about 5 to 15 min per frequency [inferred]. (4) GPU-to-RAM swap is not viable on Windows. (5) Review of the local agent's explanation: mostly accurate, but its "memory needed" column is an upper bound including the memory pool, and it omits the horn-size and fused-path levers.
- Proposed CP-10a..d (size check, epw 4/5 accuracy test, high-band verify prototype on CPU, upstream question). None run. Caveat: above f11 (~5.65 kHz) the uniform throat source is not a real driver exit.

## 2026-10-13 (cloud, research) — cloud GPU rental report (orchestrator: Claude)

- `docs/CLOUD_GPU_REPORT.md`: web and code research on renting GPUs. Verdict: feasible, moderate effort, cheap (RTX 4090 about $0.34 to $0.69 per hour; L40S 48 GB about $0.79; A100/H100 poor value for a Float32 solver). Campaign estimate 5 to 40 GPU-hours, roughly $3 to $30 [inferred, unmeasured].
- Key risks: CUDA on Linux unverified by us or the beat authors; `solve/worker.py` host cleanup is Windows-tuned (POSIX branch never run on a real host). New proposed checkpoints CP-9a..d (pod proof, optional cap study, campaign, train/gate). No code changed. Needs user decisions: provider, spend cap, whether an agent may drive a pod.

## 2026-10-13 (cloud, handoff) — local-agent handoff written; CP-8 defined (orchestrator: Claude)

- `docs/HANDOFF_LOCAL.md`: step-by-step for the Windows GPU agent. Defines the next checkpoints: **CP-8a** run the full suite on the real box (mesher tests unskipped) + `doctor`; **CP-8b** widen `a_deg`/`exponent` bounds within mesher limits and re-run `search_smoke`; **CP-8c** multi-family dataset (`dataset verify` OK, all four families); **CP-8d** train and gate Stage A, solve proposals with BEM, `round_report` working.
- Finding for planning: the held-out set is 15 % of a family's records and the gate needs >= 500, so one family needs ~3,400 records (~4 h of `search_smoke`-rate GPU time) before a gate can pass.

## 2026-10-13 (cloud, later) — ISMO selection + `surrogate` CLI (orchestrator: Claude)

- `surrogate/ismo.py`: `propose` (NSGA-II on the surrogate; top-30 exploit + 10 highest-ensemble-variance explore, deduped) and `round_report` (plan step 5: do BEM-solved proposals beat random designs, rank correlation on them; `working` False otherwise).
- CLI: `hornlab-search surrogate train|propose --config ...`. `train` exits 1 unless every gate passes (and says do not use the model); `propose` writes `proposals.json` for real-BEM solving. Tests on synthetic data; offline suite green.
- Still GPU-box only: solve the proposals, feed `round_report`, retrain. Stage B/C/D not started.

## 2026-10-13 (cloud session) — Wave-3 review, report fixes, Phase 2 Stage A code (orchestrator: Claude, Haiku helpers)

**Environment:** Linux cloud container, NO GPU, NO mesher/beat installed. Offline suite: 447 passed, 30 skipped (mesher-gated), 18 deselected. Nothing GPU-side was run or claimed.

**Review of 73548a5 / 2a7bafb:** CP-7 numbers in docs are internally consistent with NOTES task-09. One finding fixed: `config.QUADRANT_FACTOR` duplicated `sizing.QUADRANT_FACTOR` (silent-killer rule: one source) -> now aliases it. Not fixable here: residual risks 1-4 (need GPU).

**Done**
- Report: noise-floor box refreshed to CP-7 values (floor 0.039 dB, two-solver; epw=6 above 2.5 kHz still flagged unmeasured). Browser check (Chromium, fake-backend run, 1280 and 390 px): no console errors, 24/24 images load, noise box first. Fixed: tables overflowed on phones (now scroll), `f11` label clipped at chart edge, numbers wrapping. Left as is (cosmetic/by design): convergence y-limit clips early outliers (p90), hornlab_plots PNGs small on narrow screens, unrounded table values, dark mode and empty-run render unchecked.
- Phase 2 Stage A (`hornlab_search/surrogate/`): `gates.py` (6 plan gates; refuses to pass with < 500 held-out), `features.py` (unit-cube encoding, cluster holdout), `model.py` (MLP + frozen save/load), `train.py` (ensemble, masked Huber, validity head, gate report), `predict.py` (batched surrogate evaluator). `search/nsga.py`: real NSGA-II + `search_pareto` (was a stub). Tests: `test_search_nsga.py`, `test_surrogate_stage_a.py` (SYNTHETIC labels: proves plumbing only; scrambled labels correctly fail the rank gate). CI now installs CPU torch.
- NOT done / honest limits: the real gates are untested (dataset is 74 single-family records; plan wants >= 500 held-out, multi-family). Superposition test not applicable to Stage A. No CLI subcommand yet. ISMO active-learning loop, Stage B/C/D not started.

**Next action:** on the GPU box, follow `docs/HANDOFF.md` runbook, then `to_training_arrays(..., ok_only=False, keys=space.keys())` -> `train_surrogate`.

## 2026-10-13 (06:20) — Wave 3 complete: CP-7a-f all PASS, rulings applied (orchestrator: OpenCode)

**Done**
- **CP-7 physics gate GREEN** (senior verifier, oracle, high-reasoning). All six checkpoints PASS with pasted output:
  - CP-7a analytic sphere: R(ka) spread **0.020 dB** (<0.5), omnidirectionality ≤0.005 dB, spreading 6.0205–6.0206 dB, convergence sub3/4/5 = 0.0204/0.0051/0.0013 dB monotone. Acceleration-drive reading confirmed (raw constant-velocity spread 24.06 dB/octave is expected, not a failure).
  - CP-7b two solvers: beat_cuda vs bempp_cpu **0.039 dB** (<0.2 → "both very likely right").
  - CP-7c mesh convergence **PASS on reduced band 500–2500 Hz** (the epw=18 full-band reference needs ~40k quarter dofs → OOM): epw=6 vs epw=18 mean|Δbw_h| **0.287°** (<2), mean|ΔDI| **0.028 dB** (<0.3).
  - CP-7d symmetry: max asymmetry **4e-6 dB**; M6 full-vs-quarter on the seed **0.023 dB** (≤3 kHz).
  - CP-7e plausibility: f0 = 343 Hz (H) / 480 Hz (V) below the 500 Hz band floor; DI-vs-beamwidth max **2.15 dB** (borderline vs the 1.5 dB guideline, far under the 3 dB "wrong" threshold); f11 (5653 Hz) sits just above the clipped 5500 Hz band → onset unresolved.
  - CP-7f **noise floor = 0.039 dB** (two-solver disagreement dominates; epw=6 DI discretization 0.028 dB just below it). The report's prior "0.055 dB, epw=6 not measured" is superseded — the floor is NOT mesh-limited.
- **Senior rulings** (verifier + rulings lane + user confirmations) recorded verbatim in a `NOTES_FOR_SENIOR.md` task-09 block. One code change: `config.mesh_spec` now calls `sizing.max_triangles_for` (was a 2% drift vs the contract-literal `ceil(2·cap·qf·slack)`).
- **Collin questions #7–#11 answered by the user and closed** (bempp-only Robin BC; trace ordering answered by test; use build_point_grid privately + pin; excitation is tag 2 / unit-acceleration; keep the name).
- Code/doc edits applied this session: `constants.py` throat-diameter comment; `families.py` + `examples/icw_termination.yaml` ICW wall-half-angle convention + explicit `kappa0`/`theta1_deg` seeds; `record.py` unit-acceleration note; `test_design_space.py` rewritten to pin the explicit-seed convention (fill demoted to defensive net); new `tests/test_mesh_pin.py` (fails on a silent HornLab pin bump) and `hornlab_search/mesh/grid.py` + `tests/test_mesh_grid.py` (single seam over `build_point_grid`).
- Full offline suite green (462+ tests; the earlier "71 records" is now 74: the verify run added three).

**Residual risks (phase-2 / post-Wave-3, not resolved here)**
1. epw=6 discretization above ~2.5 kHz unmeasured (epw=18 reference cannot be built there on 8 GB).
2. f11 (higher-order throat mode) never exercised — screen band clips below it.
3. DI-vs-beamwidth is not a regression test; real seed shows 2.15 dB balloon-vs-cuts (non-separable-rectangular signature).
4. Cross-run solve cache does not dedup the seed across separate `run` then `search` (two seed records, both cached:False).

**Next action:** post-Wave-3 follow-ups (widen `a_deg`/`exponent` bounds, run the other 4 example configs, browser-check `report.html`), then phase 2 (`11_PHASE2_SURROGATE`) if wanted. Awaiting the user's go-ahead.

- Addendum 06:45: `docs/HANDOFF.md` rewritten for the post-Wave-3 state (wave ladder complete,
  CP-7 numbers, rulings applied, all issues closed, residual risks, BEAT stale-registry hazard,
  next-work list). No code changes in that doc commit.



- Per user request, work stopped after Wave 2. Final state: Waves 0-2 done (CP-0..CP-6 green), CI green on b5bc811 (the task-08 push first failed because CI lacked `hornlab_plots`; fixed by installing the pinned package rather than skipping the report tests).
- GitHub: issues #1-#5 closed; #6 (Wave 3 senior checkpoints) open and unblocked; #7-#11 are questions for Collin. `docs/ISSUES.md` is synced.
- No Julia host or solver process left running; VRAM idle (~0.28 GB).
- `docs/HANDOFF.md` rewritten: next agent runs CP-7a-f (issue #6) and rules on the `NOTES_FOR_SENIOR.md` items.
- Not done: CP-7c/7e/7f, browser check of the report, senior rulings, Collin questions.

**Next action:** read `docs/HANDOFF.md`, then run Wave 3 (issue #6) with a high-reasoning verifier.

## 2026-10-13 (05:40) — task 08 done, CP-6 green (orchestrator: Claude)

**Done**
- Task 08 (objective, search, report, CLI) DONE: 479 tests pass (462 offline). Files: `objective/{terms,scalar}.py`, `search/{evaluate,cma,selftest,rundir,nsga}.py`, `report/html.py`, `cli.py` (doctor, version, run, search, verify, report, selftest, dataset), 8 test files. `doctor` has a real round-trip check and a new `gpu-hygiene` check.
- Live checkpoints on the RTX 4060 (agent report; logs in local `scratch/`):
  - `selftest --analytic` PASS: pulsating sphere, R(ka) spread 0.020 dB (limit 0.5), omnidirectionality <= 0.005 dB, spreading 6.0206 dB; convergence sub 3/4/5 = 0.0204/0.0051/0.0013 dB. Needed a port-drive correction (beat drives unit *acceleration*, so pressure carries 1/omega): needs senior confirmation (NOTES item 1).
  - `selftest --crosscheck` PASS: beat_cuda vs bempp_cpu 0.039 dB max (2,396 dofs).
  - `run` screen: seed J = 22.59, 3,850 dofs, solve 18 s (first solve). Coverage term dominates (seed ~95 x 84 deg vs 75 x 45 target): not a wrong divisor.
  - `search` (search_smoke): 60 new evaluations in 4 m 28 s (4.25 s/candidate, ~847/h); seed J 22.07 -> best 9.66 (-56%), resume extension to 7.36 (-67%); reproducible; 5 `mesh_too_large` + 1 `invalid_geometry` rows. `a_deg` and `exponent` sit near their lower bounds: widen.
  - Resume: zero re-solves for cached rows, first 60 ndjson rows byte-identical.
  - `verify`: screen vs verify J differ by up to 0.4 (12-point grid mis-ranks).
  - `report`: HTML written (5.3 MB), noise-floor box first (0.055 dB, limited by beat vs bempp; epw=6 discretization not yet measured). Not viewed in a browser.
  - `dataset`: 71 records (64 ok, 7 failed), 100% OSSE, 5.6% with traces; verify OK.
- Live bug found and fixed by the agent: the Julia host resolved relative mesh paths against its own cwd, so `search --resume runs\<dir>` failed; paths are now absolute with a test.
- Cleaned up a leftover BEAT worker host after the agent finished (hygiene rule 6 in practice).

**Open issues**
1. Senior rulings needed (NOTES_FOR_SENIOR, task-08 block): item 1 acceleration-drive reading of the analytic test; 4 (raw terms, 30.0 for unmeasurable terms, `Target.freq_weights` unused); 5 (DI from theta-phi balloon with sin(theta) weights); 6c (budget counts only non-cached evaluations); 7 (dataset choices).
2. CP-7c (epw=6 discretization error on a real horn) not measured; the report's noise floor is a lower bound.
3. verify/final meshes equal the screen mesh (band clipped); revisit with a smaller seed or higher cap.
4. Dataset is single-family; run the other example configs before any surrogate work.
5. Questions #7-#11 are for the user to send to Collin.

**Next action:** Wave 3: run the senior physics checkpoints CP-7a..f (issue #6) with a high-effort verifier; then summarize for the user.

## 2026-10-13 (01:10) — GitHub live (orchestrator: Claude)

- `gh` authenticated (account llevaachingada). Repo: https://github.com/llevaachingada/Hornfab. Labels created (wave-1, wave-2, senior-review, phase-2, blocked, question).
- Issues created: #1-#4 (tasks 04-07, closed with CP results), #5 (task 08, open, in progress), #6 (task 09, blocked by #5), #7-#11 (questions for Collin). Mirror in `docs/ISSUES.md`.
- CI: green on the latest commit (0a96c58). Two earlier red runs were my broken commits (missing `hornlab_search/dataset` because of an unanchored `.gitignore`; a test tied to the old frequency grid), both fixed. Lesson: always check the pytest exit code before committing (a `| tail` hid a failure once).
- Task 08 dispatched with exclusive GPU use; no solver jobs run by the orchestrator meanwhile.

**Next action:** when task 08 reports, commit it, run/verify CP-6 numbers, then hand CP-7a-f (issue #6) to the senior verifier. Questions #7-#11 are for the user to send to Collin.

## 2026-10-13 (01:00) — task 05 done, example bands capped (orchestrator: Claude)

**Done**
- Task 05 (solve) DONE, CP-3 green. 86 offline + 28 worker tests; slow (10), crosscheck (2) and trace (5) tests pass on the RTX 4060. Backends: `beat_cuda` (loops ONE frequency per `solve_frequencies` call because of the multi-frequency cliff), `beat_cpu` (single multi-frequency call; no cliff seen at 4.5k dofs), `bempp_cpu` (gated; Burton-Miller is refused with native symmetry, so it runs STANDARD formulation). Worker hygiene (stale Julia host detection/clear, verified release, SIGINT/atexit) implemented and tested in `solve/worker.py`.
- Numbers: cold 17.6 s / warm 0.80 s / post-detach 0.63 s; full vs quarter 0.031 dB (<= 3 kHz); beat vs bempp <= 0.055 dB; boundary-trace recovery 8e-5 dB; idempotence 3.6e-5 dB; mismatch (quarter without flag) 29.9 dB max, ~11 dB on axis; asymmetry sign check 100%.
- Resolved the "seed horn too large for the cap" decision (flagged by 04 and 05): all five `examples/*.yaml` failed at screen resolution (seed horn 0.80 x 0.64 x 0.27 m). Set `band_hi_hz` per config from the measured caps: osse_baseline 5500, throat_adapter 6500, icw_termination 7000, freeform_hv 5500, search_smoke 4500. All 15 config x mode combinations now build (2.5k-3.8k est. dofs). **User may override**: raising a band edge requires a smaller seed or fewer elements per wavelength, not a higher cap.
  Consequence: verify/final grids are also clipped to band_hi, so verify and final meshes equal the screen mesh; they differ only in frequency count and balloon size until a larger cap or a smaller seed is chosen.
- Fixed `.gitignore`: `dataset/` ignored the source package; anchored to `/dataset/` (commit d70ba06).

**Open issues**
1. Task 08 must call `solve.worker.install_handlers()` and `worker.warm(backend)` from the CLI.
2. Balloon is a theta-phi grid: DI needs `weights=sin_theta_weights(...)` (grid shape in `Response.meta['balloon_grid']`); not equal-area.
3. `timeout_s` is checked between frequencies only (CPU makes one call).
4. beat uses direct dense LU; `gmres_tol` recorded as requested, not applied.
5. The `gh`-gated GitHub labels/issues are still not created.
6. Senior-review items: tasks 04, 05, 06, 07 `NOTES_FOR_SENIOR.md` blocks.

**Next action:** dispatch task 08 (pipeline) with the verbatim template; then CP-6/7 live runs (`selftest`, `run`, `search`) one GPU job at a time.

## 2026-10-13 (00:25) — task 07 done (orchestrator: Claude)

**Done**
- Task 07 (dataset) DONE: 64 tests pass (CP-5). Files: `dataset/record.py` (415), `dataset/store.py` (694), 3 test files. Layout: one uncompressed `.npz` per record in `shard-NNNN/` + `shard-NNNN.jsonl` + `index.jsonl` (deviates from contract section 13's single `shard-NNNN.npz`; the phase-2 loader must go through `DatasetStore`). Crash recovery tested (torn index line, torn shard line, uncommitted row).
- Disk projection for 10,000 screen records: 0.78 GB without traces, 1.40 GB with traces at 1 in 20.
- Contract gaps to rule on (NOTES_FOR_SENIOR): added `traces.sample_fraction`; `lib_shas` requires 5 entries; NaN written as JSON null.
- Test `test_append_500_typical_records_is_fast` (5 s limit) measured 1.4-1.7 s on a quiet disk but failed at 6-9 s when the disk was loaded. Not loosened; may flake under load (recorded).
- Wiring for task 08: pass `solve_spec=`, `area_m2=`, `grid=` to `build_record`; catch `ValueError` from `append`; call `reset_warning_state()` at startup; subcommand hooks `stats_report`, `verify_store`, `export_training_npz`.

**Next action:** task 05 (solve) running; when it lands, dispatch task 08 (pipeline) using the verbatim template.

## 2026-10-13 (00:15) — task 04 done, caps set, CPU provisioned (orchestrator: Claude)

**Done**
- Task 04 (design + mesh) DONE: 87 offline tests + 27 mesher-gated tests pass (CP-2). Files: `design/{families,space,custom}.py`, `mesh/{sizing,build}.py` + 4 test files. Contract deviations (all in NOTES_FOR_SENIOR): `to_mesher_config` returns a *sectioned* dict (the mesher silently ignores a top-level `max_triangles`); pre-mesh dof estimate added so over-cap designs are refused in <100 ms; new exceptions `MeshConsistencyError/MeshUnitsError/SymmetryMismatchError` that task 08 must not swallow.
- I edited one task-04 test (`test_over_cap_but_inside_mesher_slack_is_caught_after_meshing`) so it reads the screen cap from the config instead of the hard-coded plan value 8000; same intent, no tolerance loosened.
- **dof caps replaced** (quarter domain): screen 5,000 / verify 7,000 / final 8,900; full-domain (`freeform_hv`) 3,000 / 4,500 / 5,400. Basis: per-frequency cost 0.4 s @2.4k, 2.8 s @5.1k, 7.5 s @7.0k, 45 s @8.9k; 15.7k quarter and 9.2k full OOM.
- **Finding for task 05**: one multi-frequency `solve_frequencies` call falls off a cliff above ~2.4k dofs (689 s at 5.1k; 1,151 s with pipelining off) while 12 separate single-frequency calls take 33 s. The CUDA adapter must loop one frequency per call.
- M4 done: cuda 0.8 s vs cpu 1.45 s per frequency at 2.4k dofs; CPU cold start 3.7 s vs CUDA 29 s. `HORNLAB_BEAT_FORCE_CPU` does not redirect an explicit cuda request.
- First push done: https://github.com/llevaachingada/Hornfab (commit ef30d36).

**Open issues**
1. **Decision needed (task 04 finding):** the baseline seed horn is large (quarter area 0.282 m^2, bbox 0.40 x 0.32 x 0.26 m, vs the plan's 0.125 m^2 assumption). With a 5,000-dof cap, `screen` at f_max 10 kHz is refused (`MeshTooLargeError`); 5,000 quarter dofs buys roughly 6 kHz for this horn. Options: lower `band_hi_hz`/screen grid top, use fewer elements per wavelength in screen (epw 4), or a smaller seed. Not decided; `osse_baseline.yaml` unchanged beyond caps.
2. `config.mesh_spec` uses `ceil(2*cap*qf*slack)` and ignores `dof_per_triangle`, while `sizing.max_triangles_for` uses it (2% apart at 0.51). Task 03 file; fix pending.
4. Task 06 conventions awaiting senior review (half-pressure -6 dB threshold; `di_from_cuts` clamp; ddof=1 ripple).
6. Mesh time: 0.3 s -> 12 s over the f_max range for the baseline horn (task 04 table); mesh fraction of a screening candidate is small versus solve above 5k dofs.

**Next action:** collect task 07; dispatch task 05 (solve) now that the GPU is free of measurements; then task 08 once 04-07 are in.

## 2026-10-12 (night) — clean GPU measurements, Wave 1 started (orchestrator: Claude)

**Done**
- Single session now (a duplicate session had collided on the GPU; it stood down). Added "GPU / Julia hygiene" rules to `AGENTS.md` and `CLAUDE.md` after finding that stale persistent Julia hosts (~1 GB VRAM each) cause false OOMs and worker crashes.
- Clean-state M2/M3/M5/M6 and C1/C2b/C3/C4/C5 measured; `TOOLCHAIN.md` rewritten (see it for every table).
- Remote set: `origin` = https://github.com/llevaachingada/hornfab.git (package/CLI keep the names `hornlab_search` / `hornlab-search`).
- Per user instruction (23:47), Wave 1 started in parallel with the last GPU measurements. Interpretation: "task one" = Wave 1 task 04 and onward. CP-0 gate waived in part: M4 (cpu) and the dof caps are still being settled; recorded as a deviation.
- Task 06 (metrics + targets): DONE, 78 tests pass, CP-4 analytic tables in agent report. Decisions needing senior review (also in `NOTES_FOR_SENIOR.md`): -6 dB threshold implemented as half pressure (-6.0206 dB); `di_from_cuts` clamps sin(bw/2) at 1 and treats saturated cuts as omni; `ripple_db` uses ddof=1.
- Tasks 04 (design+mesh) and 07 (dataset) dispatched; 05 (solve) waits for the GPU job to finish.

**Key measured numbers**
- dof/triangle 0.500 full, ~0.51 quarter.
- Symmetry pairing (clean): full vs quarter max 0.058 dB up to 4 kHz, 0.497 dB at 6 kHz; mismatched run is 12 dB wrong on axis, 54.9 dB max.
- VRAM: operator is dense 8N^2 but the real footprint is 20-40x that. Clean OOM ceilings on the 8 GB RTX 4060 Laptop: full domain 5.5k ok / 9.2k OOM; quarter 8.9k ok (74 s) / 15.7k OOM. **The plan's dof caps (8000/16000/24000) do not hold.**
- Throughput (warm worker, quarter): 2,369 dofs, 12 frequencies + 512-point balloon = **5.0 s**; 5,140 dofs same job = **689 s** (assembly 672 s), and 1,151 s with `BLAB_METAL_PIPELINE=0`; one warm frequency at 5,140 dofs is 3.2 s. A cliff, not a smooth curve. Per-frequency looping test in progress.
- Worker: cold 27 s, warm 1.4 s, after detach 0.84 s.
- Traces: 111,280 bytes per frequency at 2,369 dofs. Balloon grid theta 0-180, phi 0-348.75, shape (F, 512).
- Impedance BC: bempp only.

**Open issues / blockers**
1. `gh` is not authenticated: labels and GitHub issues cannot be created yet. Issue bodies are drafted in `.github/issues/`. (`git push` may work through the credential manager.)
2. M4 (CPU vs CUDA): CPU backend unprovisioned; to attempt once the GPU is free.
3. dof caps in the YAMLs (8000/16000/24000) are unsafe; provisional replacement pending the per-frequency loop result.
4. Plan drift: `SolveResult` (not `Response`) and `mesh_info.n_vertices` (not `p1_dof_count`): task 05 must adapt.
5. Mesh time and mesh fraction of a candidate not yet measured.

**Next action:** collect agent reports for 04 and 07; run M4 CPU provisioning; dispatch task 05 (solve) when the GPU is free; set dof caps; commit and push.

## 2026-10-12 — Wave 0 scaffold + CP-1 green (session 2)

**Done**
- `gh` installed (v2.102.0); **not** authenticated.
- Wrote owner-03 files: `pyproject.toml` (real SHAs, `pythonpath=["."]`), `.gitignore`, `README.md`, `hornlab_search/__init__.py`, `hornlab_search/cli.py` (`doctor`+`version`), `examples/icw_termination.yaml`, `examples/freeform_hv.yaml`, `examples/search_smoke.yaml`, `.github/workflows/ci.yml`.
- `pip install -e ".[dev,crosscheck]"` succeeds (pytest 9.1.1, pyyaml, cma, jinja2 present).
- First mesh + solve: 1419 verts / 2834 tris; cold 24.618 s, warm 0.494 s. Real schema is `SolveResult` (not the plan's `Response`).
- M1 calibration, M6 symmetry, M7 max_triangles measured (see `TOOLCHAIN.md`). C1–C5 answered from source.

**Pasted CP-1 output**

`pytest -q`:
```
..................                                                       [100%]
```

`hornlab-search doctor`:
```
PASS  python-version    Python 3.12.10 in [3.11, 3.14)
PASS  core-imports      numpy, scipy, cma, yaml, jinja2
PASS  hornlab-imports   mesher, beat, plots; bempp yes
PASS  pinned-shas       all installed SHAs match pyproject.toml
PASS  toolchain         TOOLCHAIN.md present, dof_per_triangle=0.51
PASS  gpu               nvidia-smi exits 0
PASS  backend           beat_cuda functional (state=ready)
PASS  configs           all 5 example configs load
PASS  round-trip        reserved for task 04
```

`hornlab-search version`:
```
0.1.0
```

**Open CP-0 items:** M2 (VRAM vs dofs + dof ceiling), M3 (s/person-candidate), M4 (cuda vs cpu), M5 (after-detach). All blocked on exclusive GPU access.

**Next action:** dispatch the Wave 1 issues in parallel using the prompt template in `docs/plan/00_ORCHESTRATOR.md` — **only after** CP-0 is completed on a clean GPU and the repo is pushed.
## Status
- **Phase:** senior-pass implementation (owner directive 2026-10-24; WP1–WP17, no Synergy/MEH). **M1 DONE and pushed** (WP1–WP4 offline parts + WP15 repo-side plumbing; Oracle GO). **M2 DONE: WP15 fused CUDA validated on the GPU** — ladder, fused GPU test, measured ceiling, 12 kHz verify; Oracle GO recorded in the M2 entry. **M3 DONE** (carry-overs + WP5/WP7/WP8 calibration, zero new searches; Oracle GO-with-fixes ALL applied). **M4 DONE (2026-10-25): WP9 generators (splice/throat_blend/spherical_salmon) + WP9b GRID rows (organic/elliptical/X-shape as labeled hypotheses + HALF models) + `lecleach` SHIPPED after R9-J PASSED (owner chat directive, Fourcade verified, 0.00 mm width) + WP10 GRID adapter** — 12 typology smokes green on the GPU, full-vs-quarter PASS, suites 1194/0/1/0 (intended tripwire only), Oracle GO-with-fixes (doc-only) applied. **M5 WP11 DONE (2026-10-25): restarts (IPOP/BIPOP mirroring pycma) + CMA-ME QD atlas (ribs 0.12.0 — offline-first, +40 tests, 4 GPU screens proving budget exactness incl. a fired 4-ES BIPOP run; Oracle GO-with-fixes applied; evidence `docs/evidence/M5_WP11_2026-10-25.md`, byte-check 30/30). M5B DONE (2026-10-25): WP14 multicell CATEGORY (CAD→STEP route: `tools/cad/multicell.py` + `mesh/step_build.py` + the `cad` recipe/echo/example + `solve.near_correction*`/`solve_precision`/`source_profile_alpha` keys) + WP16/17 fork branches LANDED AND GPU-VALIDATED (Julia 46/46 testsets incl. all four CUDA testsets; selftests 0.020/0.0390 dB; 3-arm A/B worst 4.94e-06 dB) + FORK HOSTED (github.com/llevaachingada/hornlab-beat-bem) + PIN MOVED THERE (`760a1ec`) — the test_mesh_pin tripwire RESOLVED, suite 1325/0/0/0; M4 debts finished; multicell PHYSICS DEFERRED (owner — mouth-topology defect diagnosed, evidence preserved); CLI selftest lock-kill fix; evidence `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md`, byte-check 33/33. M6/WP12 DONE (2026-10-25): enclosure mounting plumbed (brief.mounting → the mesher's OWN keys, −mnt- cache keys, all echoes) AND MEASURED on two finalists — dofs +199.4 % / +106.5 %, both under the unchanged caps, enclosure J improves (a different objective landscape — never rank across mountings), reference parity 2.91e-06 dB; **WP13 OWNER-DEFERRED** ("don't know how necessary that is"); suite 1372/0/0/0; evidence `docs/evidence/M6_WP12_2026-10-25.md`, byte-check 21/21.** Waves 0–3 + CP-7 complete; CP-8a/b PASS, CP-8c CLOSED, CP-8d still FAILED (surrogate retrain pending more OSSE data — unchanged).
- **Done 2026-10-24:** M1: objective v2 (opt-in, offline re-score over 18,059 records: Spearman ρ(v1,v2) = 0.989, both compare-tier claims SURVIVE, v1 drift 0 — `docs/evidence/OBJECTIVE_V2_RESCORE.md`); WP2 driver pins with the embedded-brief grandfather; WP3 shape-only perturb + graded infeasibility; WP4 `freq_weights` + HF verify grid. WP15 repo side: `solve.cuda_fused` flag, env gating, diagnostics proof + refusal (fork branch `hornlab-search/fused-cuda` @ `fa99ee5` in `..\forks\hornlab-beat-bem`; Julia tests green). **M2 (late evening):** fork installed by SHA; ladder analytic **0.020 dB** / crosscheck **0.0390 dB** (both = base references); 3-arm A/B vs stored base-pin runs ≤ 2.9e-6 dB / 2.1e-05 deg (bars 0.039 dB / 1°); fused GPU test green ([measured] on-axis 0.0000 dB, bw 0.01-deg print precision, z_throat 3.35e-07; stale-host refusal); flag-off bit-determinism finding rebarred to a measured 1e-4 dB floor (base-pin reproduction logged); ceiling measured: fused **fits 15,984 / fails 20,237, SAFE = 12,000** (old path same mesh: 7,389 vs 2,217 MiB, 59.6 vs 9.1 s/freq); four `*_fusedcuda` configs (caps 5000/12000/12000); 12 kHz verify on the flag (4,438 dofs, 2.1 s/freq, 25× fused proven). Evidence `docs/evidence/FUSED_CUDA_2026-10-24.md`; pin on `dev/fused-cuda-pin` ONLY (never main; GitHub hosting = owner action). **M3 (2026-10-25):** carry-overs @ `1dda493` + `solve.source_motion` / `mesh.rear_res_factor` / `mesh.band_split` (+ `stack_responses`, verify-only seam, `mesh_policy: band_split_v1` provenance) + the 17-job measurement pack on the stored WP5 finalists (`tools/m3_measurement_pack.py`); evidence `docs/evidence/MEASUREMENT_PACK_2026-10-24.md`; details in the M3 entry above.
- **Next (next agent):** The implementation plan's NON-OWNER-GATED work is COMPLETE as of M6/WP12: the machine carries the brief-agnostic shape surface (classical + splice/throat-blend/salmon + GRID + organic rows + rollback lecleach/iwata_ar/toroidal + saddle halves) + restarts schedules + the QD-atlas contract + the CAD→STEP multicell category + the enclosure-mounting route (measured: dofs +199 %/+107 %, both under the unchanged caps) + the WP16 source plug + WP17 fused-CUDA near correction (stage 1) on the hosted fork's pinned stack (`760a1ec`; installed == pinned — the mesh-pin tripwire is green). **Everything remaining needs the owner: [a] the brief-design consultation (deferred) — 2–4 real briefs turn the machinery from "calibrated" into "aimed"; [b] resume-or-park the deferred WP14 multicell PHYSICS (the fixture's mouth-topology defect + the full resume recipe live in `docs/ISSUES.md`'s deferred-WP14 block; WP17 stage 1 is ready for it); [c] P6a superformula campaign + P6b GSA-vs-CMA-ES bake-off (owner-gated); [d] the small parked proposals (W7 balloon density, the M3/5 calibration proposals); [e] WP17 stage 2 (fused + per-image symmetry near caches) only when symmetric-drive multicells need the GPU. WP13 axisymmetric backend = OWNER-DEFERRED ("don't know how necessary that is" 2026-10-25).** Nothing else runs without the owner.
- **Open owner decisions:** v2 objective as brief DEFAULT (today opt-in); bound proposals (`docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`); mesher bump (post-beta); surrogate OSSE top-up; GUI contrast owner click-path check remains; **P6a/P6b + W7 + the brief-design consultation + resume-or-park the deferred WP14 multicell physics (all owner-gated — see Next). RESOLVED 2026-10-25: fork hosting + pin (hosted fork; `760a1ec` pinned; installed == pinned — tripwire green); WP13 = OWNER-DEFERRED.**
- **Blockers:** none (owner gate on the pin hosting only).

