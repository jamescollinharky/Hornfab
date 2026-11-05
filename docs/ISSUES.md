# ISSUES

Mirror of the GitHub issues at https://github.com/llevaachingada/Hornfab/issues. ID, title, status, owner, plan reference.
Updated in the same commit as `docs/CONTINUITY.md` on every push. Last synced 2026-10-25 (M6/WP12 pushed: enclosure mounting plumbed end-to-end (`brief.mounting` → the mesher's OWN keys; `-mnt-` cache keys; mesh_meta/ndjson/record echoes; absent = byte-for-bit) and MEASURED on two finalists — dofs +199.4 %/+106.5 %, both under the UNCHANGED caps, enclosure J improves (a different objective landscape — never rank across mountings), reference parity 2.91e-06 dB; **WP13 axisymmetric backend OWNER-DEFERRED** ("don't know how necessary that is"); suite **1372/0/0/0**; focused 71/0/0; evidence `docs/evidence/M6_WP12_2026-10-25.md`, byte-check 21/21; no GitHub issue state changed).

| ID | Title | Status | Owner | Plan ref |
|---|---|---|---|---|
| #1 | [04] Design space and mesh | closed, CP-2 green | 04 | `docs/plan/04_TASK_DESIGN_MESH.md` |
| #2 | [05] Solve backends and warm worker | closed, CP-3 green | 05 | `docs/plan/05_TASK_SOLVE.md` |
| #3 | [06] Metrics and targets | closed, CP-4 green (3 conventions ruled by senior) | 06 | `docs/plan/06_TASK_METRICS.md` |
| #4 | [07] Dataset record and store | closed, CP-5 green | 07 | `docs/plan/07_TASK_DATASET.md` |
| #5 | [08] Objective, search, report, CLI | closed, CP-6 green (5 items ruled by senior) | 08 | `docs/plan/08_TASK_PIPELINE.md` |
| #6 | [09] Physics checkpoints CP-7a to CP-7f | **closed, CP-7 green** (noise floor 0.039 dB) | 09 | `docs/plan/09_CHECKPOINTS.md` |
| #7 | [Q] Collin: is a Robin/admittance BC planned for BEAT? | closed (answered: bempp-only, later phase) | user | `docs/plan/02_TASK_ENV.md` C3 |
| #8 | [Q] Collin: surface_traces ordering and bempp field recovery | closed (answered by test) | user | `docs/plan/02_TASK_ENV.md` C2b |
| #9 | [Q] Collin: can build_point_grid be public API? | closed (use privately, keep pin + guard test) | user | `docs/plan/02_TASK_ENV.md` C4 |
| #10 | [Q] Collin: confirm BEAT driver excitation on tag 2 | closed (confirmed tag 2 / unit-acceleration) | user | `docs/plan/02_TASK_ENV.md` C5 |
| #11 | [Q] Collin: OK with the hornlab-search name? | closed (keep until objection) | user | `docs/plan/README.md` |
| #13 | hardening-review: Stage A surrogate gate-integrity and real-data traps | **open — fixes MERGED to main** (FF to 6d1d5c7 on 2026-10-22 carries e0b9b61 + 11304f6 + cloud reconciliation 152a829 verbatim; oracle pre-merge sign-off; full offline suite 533 PASS at the merged tree; awaiting owner close) | phase-2 (cloud) | `docs/plan/11_PHASE2_SURROGATE.md` §4 |

Local-only, updated 2026-11-05 (**CI param-catalog fix on PR #22; no GitHub issue state changed**):
- Fixed `test_param_catalog` failures: `mid_ports` NATIVE_KNOBS, native-count/CAD-only gates, regenerated param catalog.

Local-only, updated 2026-11-05 (**objective v6 loading_smooth; no GitHub issue state changed**):
- **Landed:** `objective.version: 6` (`load_near`, `z_smooth`, `cov_pat`, `di_rise`) for Le Cléac'h / rollback; dossier + briefs + offline tests. Open: re-score full records that carry `z_throat` so load_near/z_smooth dominance can be confirmed; calibrate `di_slope_target` (seed slopes ~8 dB/dec vs default +5).

Local-only, updated 2026-11-03 (**PR to main; no GitHub issue state changed**):
- Opening PR `feat/solana-sawmod-wg-bench` → `main` (Solana/SAWMOD, mid_ports, cloud tooling, UMAP evidence + GUI Design cloud).

Local-only, updated 2026-11-03 (**GUI design-cloud view; no GitHub issue state changed**):
- **Landed:** run explorer **Design cloud** (`/api/umap`, `#/run/<id>/umap`) — PCA always, UMAP if umap-learn installed.

Local-only, updated 2026-11-03 (**UMAP HTML param panel fix; no GitHub issue state changed**):
- **Fix:** UMAP evidence HTML embeds `window.UMAP_DATA`, 18-knob dropdown, full param table on click.

Local-only, updated 2026-11-03 (**UMAP evidence HTML for CMA-1000; no GitHub issue state changed**):
- **Landed:** `docs/evidence/UMAP_SOLANA_OSSE_MEH_SF_CMA1000.{html,md}` — interactive param/J-colored UMAP of run `20261103T053926Z-screen-8b32a1` (htmlpreview link in the md).

Local-only, updated 2026-11-03 (**Ath OSSE+SF mid_ports fork + solana_osse_meh_sf; no GitHub issue state changed**):
- **Mesher fork landed:** `hornlab-search/osse-midports` @ `55da4f4` (tag-10 L1 flush on native OSSE); pin in pyproject/TOOLCHAIN.
- **Solana MEH-context path:** `solana_osse_meh_sf`; 4090 screen **J=39.604**; CMA live best **J≈22.3** (`20261103T052647Z-screen-cd22a5`). Flat CAD MEH = fallback. CMA-1000 `20261103T053926Z-screen-8b32a1` still LIVE (~gen 70+, best **7.75**).
- **Solana owed:** finish/pull CMA-1000; mouth-matched CD (`gcurve_off`) verify; enclosure/LF.
- **SAWMOD owed:** Ath knuckle+ports (not flat MEH), LF 10″, BL refine.

Local-only, updated 2026-11-02 evening (**Solana/SAWMOD + RunPod path on `feat/solana-sawmod-wg-bench`; no GitHub issue state changed**):
- **Cloud landed:** `tools/cloud/*`, `docs/CLOUD_GPU_RUNBOOK.md`, POSIX orphan-julia cleanup; **4090 CP-9a 0.020/0.039 dB**; Solana CUDA screen; `osse_baseline_4090` CMA in flight / owed finish+pull.
- **Solana landed:** Ath WG + evidence; MEH CAD `solana_meh` / `solana_meh_search` + brief; mouth probes `_solana_mouth_probes/`.
- **Solana owed:** mouth-matched CD (`gcurve_off`) 4090 screen+verify; Ath midports; enclosure/LF.
- **SAWMOD landed:** control WG + knuckle + `walls: lr` MEH probe; CAD/`step_build` accept `lr`.
- **SAWMOD owed:** Ath knuckle+ports (not flat MEH), LF 10″, BL refine.

Local-only, added 2026-11-01 late afternoon (**Solana 2.0 phase 1 + SAWMOD phase-2 probes; no GitHub issue state changed**):
- **Solana landed:** DIY Guide + `athscript.cfg` snapshot, dossier, `solana_osse` / `solana_control_1in_90x90`, Metal screen 4284 dofs J=41.9
- **Solana caveats:** freestanding; `a_deg` inferred 45; SF mouth ~450 vs Ath morph 353 / STL ~376.
- **Solana owed:** mid ports + 4×6NDL38 MEH, enclosure/LF, mouth-delta diagnosis. (MEH CAD seed landed evening 2026-11-02; Ath midports still owed.)
- **SAWMOD phase-2 probes landed:** knuckle Metal J=241 (`3c1938`); MEH lr2 multi-source path exercised.
- **SAWMOD still owed:** Ath knuckle+ports (not flat MEH), LF 10″, BL refine; SAWMOD MEH follow-ups.

Local-only, added 2026-11-01 afternoon (**SAWMOD control WG bench phase 1; no GitHub issue state changed**):
- **Landed:** whitepaper PDF snapshot, dossier, pinned `sawmod_control_osse` + brief.
- **Still owed:** Ath knuckle+ports, LF 10″ slot, Boundary Lab `Multi_region_SAWMOD` refine.

Local-only, added 2026-11-01 (**PR #17 merged to main + the hardware-neutrality rule; no GitHub issue state changed**):
- **Merged (squash):** Metal backend + Mac path, Hansen budget hint, staged A/B harness, CMA
  covariance dump, CMA pin plan, restart controls (jamescollinharky's PR #17). Two merge defects
  fixed before landing: spawn-free `auto_backend()` (Apple Silicon -> Metal, else `None`, never a
  silent CPU swap) and `--backend` applied before config validation (drops `cuda_fused` off CUDA,
  so `config_sha` / snapshot / `run.json.backend` agree).
- **Rule (owner):** results and data must not depend on the solver backend. No silent backend
  swaps; the backend is explicit, hashed into `SolveSpec`, and recorded in `run.json.backend` and
  dataset provenance; cross-backend pooling only after a measured parity check.
- **Owed:** (a) GPU-box staged A/B (`tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both`,
  paste COMPARE.md); (b) Mac<->4060 Metal parity <=0.2 dB before Metal enters campaign/compare;
  (c) a cross-backend parity test (one design, CPU vs CUDA vs Metal) behind a marker, plus a
  comparison view that surfaces the backend; (d) move `gui.data.sensitivity` out of the GUI layer
  (`pin-plan` imports it).
- **CI:** unblocked main's red Actions run (a collection error from `tests/test_gui_preview_shape.py`
  when the optional mesher is absent under `--no-deps`). The suite now skips in that environment
  instead of aborting the whole run; a changed mesher pin still fails.
- **CI (part 2):** the remaining ~24 red tests were un-gated optional-dep users (`hornlab_mesher`,
  `hornlab_beat_bem`, `ribs`) plus 3 Windows-only assertions. All gated/fixed; a missing dep now
  skips instead of failing. Re-enable real coverage for those areas by installing the pins in CI
  (or a second job) when that is worth the runner cost.

Local-only, added 2026-10-31 (**staged search A/B protocol + chaining harness; no GitHub issue state changed**):
- **Landed:** `examples/typologies/staged_ab_2026-10-31/` (joint 60 vs A/B/C 20+20+20 on crease__core_law),
  `tools/run_staged_search.py`, `tests/test_tools_staged_search.py`, evidence
  `docs/evidence/STAGED_SEARCH_AB_2026-10-31.md`.
- **Synthetic coupled A/B:** staged+polish wins (J 0.100 vs joint 0.302) — keep the tools/ harness;
  do **not** change the default `search` path until the GPU acoustic A/B runs on the CUDA box.
- **Owed (GPU box):** `python tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both`
  (one job at a time); paste COMPARE.md numbers into the evidence doc.
- **Still higher leverage than staging:** objective term normalisation (smoke night); diagonal
  balloon scoring for crease knobs.

Local-only, added 2026-10-31 evening (**CMA pin-plan; no GitHub issue state changed**):
- **Landed:** `pin_from_cma` + `hornlab-search pin-plan` + run-detail Pin plan table
  (recommend-only; optional `--write-config`).

Local-only, added 2026-10-31 evening (**CMA covariance dump; no GitHub issue state changed**):
- **Landed:** `cma_covariance` on `run.json` + run-detail GUI table (σ√Cᵢᵢ shares + eigen loadings).
  Complements Spearman sensitivity; not a Sobol acoustic decomposition.

Local-only, added 2026-10-31 evening (**staged knob schedule in COMPARE/plan; no GitHub issue state changed**):
- **Landed:** `plan.json` / `COMPARE.md` list active vs fixed knobs per staged arm.

Local-only, added 2026-10-31 evening (**Mac .venv + Metal; no GitHub issue state changed**):
- **Landed:** project `.venv` + `[dev,crosscheck]`; Metal ready; dry-runs + budget-5 Metal
  smokes (tractrix / freeform_hv / conical); GUI auto `--backend beat_metal` when CUDA absent.
- **Still owed:** Mac↔4060 A/B (<0.2 dB) before mixing Metal into CUDA datasets; doctor still
  FAILs the CUDA checks on Mac (expected).

Local-only, added 2026-10-31 evening (**Hansen budget heuristic; no GitHub issue state changed**):
- **Landed:** `search/budget_heuristic.py` + `GET /api/budget-hint`; Launch/Compose suggest
  `max(150, 100·N)` (Hansen) with IPOP/BIPOP restart inflation; GUI cap 5000.

Local-only, added 2026-10-31 evening (**Launch IPOP/BIPOP controls; no GitHub issue state changed**):
- **Landed:** Launch + Compose search forms — CMA restarts mode (config default / off / IPOP / BIPOP)
  + max; CLI `--restarts-mode` / `--restarts-max`; `jobs.py` allow-list. Run detail still shows
  the schedule read-only after the fact.

Local-only, added 2026-10-31 later (**beat_metal + Mac staged path; no GitHub issue state changed**):
- **Landed:** `beat_metal` in `BACKEND_NAMES` / `BeatBackend` / CLI; staged harness `--backend auto`
  → Metal on Darwin (clears `cuda_fused`). See staged README + evidence doc Mac section.
- **Owed on this Mac:** create `.venv` with Python 3.12/3.13, `pip install -e ".[dev,crosscheck]"`,
  `doctor`, then the staged A/B; Mac↔4060 A/B (<0.2 dB) before mixing Metal into CUDA datasets
  (P3 remainder).

Local-only items (no GitHub issue): band edges capped by the measured dof cap (confirmed, user "keep lowered edges"); task 07 test-17 disk-latency flake risk (do not loosen); residual CP-7 risks (epw=6 above 2.5 kHz unmeasured; f11 unexercised; DI-vs-beamwidth not a regression test) — see `NOTES_FOR_SENIOR.md` task-09 block and CONTINUITY 06:20.

Local-only, 2026-11-01 (**hardware decision study; no GitHub issue state changed**):
- **DONE (decision study, not rental benchmarks):** owner clarified theoretical rent-versus-buy scope; $0 rental spend. `docs/evidence/HARDWARE_2026-11-01.md` audits stored timings and backend/lane code and gives current rates with labeled cost scenarios.
- **MEASURED (CPU mesh sizing):** fixed T2 seed first globally validates at 12 kHz among tested sizes at 33,959 dofs / 67,245 triangles (EPW 8.4). EPW 6 gives 33,938 triangles but only 8.58 kHz global validity. This does not establish acoustic convergence or a universal minimum.
- **SOURCE-DERIVED capacity constraint:** unchanged standard CUDA multi-channel path requires at least 85.410 GiB for operators+identities+LHS at that full-wall seed, before additional workspace. The 80 GB tier cannot fit that path. H200 141 GB is a test candidate, not a measured solution; cheaper 24/32 GB coarse-screen tests answer a different fidelity question.
- **OPEN:** successful exact 41-frequency request on candidate hardware, root cause of CUDA 719, actual billed cold/warm costs, unified-backend C4 parity and 1/2/4/8-lane results. Flat `nvidia-smi` peaks do not establish invariant live workspace. Historical seed/winner mesh attribution and current overwritten/unknown-baseline VRAM trace limitations are corrected in the study.
- **OPEN (implementation if shared-host lanes are selected):** per-device locks/monitoring, owned-host-only cleanup, private registries/cache staging, parent-only dataset writes and deterministic CMA coordination. Existing evaluator has side effects; the current one-writer/global-cleanup code is unsafe for naive concurrent workers. Separate machines, one brief each, are the simpler future deployment test.

Local-only, 2026-10-31 (**3D evolution transparency, re-landed on `meh/integration`**):
- **Recurring owner report (run `20261031T202159Z-screen-ba7648`): mesh renders as see-through triangles.**
  Not a renderer regression: the hole-free decimation fix (`64ccb20`) lived only on
  `feat/hardened-plan-2026-10-29`; this worktree is `meh/integration`, whose `gui/data.py` still stride-sampled
  (`M3D_VERSION=1`, cap 6000 -> 11.5k-tri frames cut to 5.8k). Code files cherry-picked here, cache key bumped
  to `[2,30000]`, stale per-run cache regenerated (`decimated:false`). The long-running GUI on :8765 must be
  restarted after any such change; a branch switch also silently reverts the working tree. 131 GUI tests pass.
  Detail: CONTINUITY 20:28Z.

Local-only, pushed 2026-10-30 late (**chief-implementer hand-off; no GitHub issue state changed**):
- **OPEN:** owner/lead agent to pull branch `ccr-4978c80b-tvvcgv` locally and run `docs/meh/CHIEF_IMPLEMENTER_HANDOFF.md`.

Local-only, not pushed 2026-10-31 (**MEH wave 1 merging into `meh/integration`; no GitHub issue state changed**):
- **DONE:** M4 network layer (merged, `meh/M4-network` parts 1+2: drivers, network, dsp, limits, synthesis).
- **DONE:** M4 inner optimiser (`hornlab_search/meh/inner.py`; merged `meh/M4c-inner`, commit `0cdfd7a`).
- **DONE (M8 step 1):** solver fork validated on CPU and CUDA - superposition, reciprocity, single-tag parity,
  reduced-vs-full symmetry all pass. The M2 Julia testset needed three fixture fixes (commit `93ef848`/`1efdc6f`);
  properties and tolerances unchanged.
- **DONE (M8 step 2):** single-tag parity vs the current pin <= 5.91e-5 dB on two finalists (floor 0.039 dB).
- **DONE (M8 screen):** T2 40-eval CMA + verify -> J 9.530 -> 11.894 (best `ed11d2cd3acc`); T1 40-eval CMA + verify
  -> J 13.228 -> 14.512 (best `704051ae928c`). Runs `20261101T004552Z-screen-427d57` and
  `20261101T015657Z-screen-fc1d24`; evidence `docs/evidence/MEH_M8_2026-10-31.md` s8.
- **BLOCKED on this hardware (screen band):** the contracted 120-12,000 Hz 1/6-octave grid has no legal operating
  point on the 8 GB card. A 12 kHz-resolving mesh needs >= ~8,600 dofs (7.9/8.19 GB peak; the 41-frequency sweep dies -
  CUDA 719 / worker_exit, measured); the smallest legal mesh (epw 4.05, 8,044 dofs) leaves CMA neighbours at
  8,296-8,485 dofs, over any cap that keeps VRAM safe. `cuda_fused` refuses multi-channel by design. Resolving the band
  needs a >= 12 GB card. Stopped by owner direction.
- **DONE (docs accuracy):** the M8 evidence doc and its INDEX line now state the full result set (links 1/2/5/6 PASS, link 4 FAIL, link 3 PARTIAL, screens verified, blocks); no number changed.
- **CI FIXED (PR #18):** `tests/test_solve_worker_restart.py` now gates `hornlab_beat_bem` with
  `pytest.importorskip`, so CI (which does not install the solver) skips it instead of failing at collection.
- **MERGED main (2026-11-01):** `origin/main` merged into `meh/integration`; 16 MEH-touched files normalized to
  LF (main is LF), logs unioned so no entry from either side was dropped, and main's Metal/backend-override work
  coexists with the MEH config changes. PR conflicts resolved.
- **PACKAGED (handoff, PR #18):** `docs/meh/MEH_QUICKSTART.md`, `tools/meh/run_screen.ps1`, and
  `docs/evidence/meh_2026-11-01/` (both verified winners + README). No production code changed.

- **PR OPENED (wrap-up):** `meh/integration` -> `main`, carrying the full MEH implementation, the owner-approved
  pin bump, both verified screens, the six-line readiness proof, and the hardware audit/hand-off. Final offline
  suite green at the tip (exit 0). Open items inside the PR body: 8 GB band ceiling, M9 blocked, step 3 blocked,
  link 4 budget decision.
- **TIDIED (hand-off):** the withdrawn VRAM reading no longer appears as fact in s5/s5b; both now carry the
  source-derived operator-storage statement and point at the s2a corrections. Duplicate table row removed.
- **CORRECTED (hand-off):** four claims withdrawn after the audit - wrong mesh attribution (winners are
  5,872/6,249 dofs), the 12x scaling claim, the flat-VRAM reading (and its backing CSV was overwritten), the
  25-35k element sizing (first valid whole-wall mesh is 33,959 dofs, ~85 GiB), and 'lanes are one line'.
  The audit's rent-first conclusion and 141 GB tier stand.
- **UPDATED (compute brief):** the hand-off now carries the measured baseline (3.6 vs ~45 s/frequency;
  ~12x for 1.44x elements) and an explicit unified-memory section (GH200/GB200, Apple Metal, MI300A ROCm,
  APU negative control, CPU-only) with a required validation gate for any non-CUDA recommendation.
- **OPEN (next agent, compute/hardware):** `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` - fit the s/frequency and
  VRAM scaling laws, benchmark bandwidth vs compute tiers, measure candidate-level lanes on rented GPUs, and
  return a machine table in candidates/hour and $/candidate. Nothing in the MEH code blocks that work.
- **OPERATIONAL NOTE:** stale BEAT hosts from an earlier fused probe were adopted by a later run and produced a
  misleading fused/multi-channel error. Kill Julia hosts before launching a screen (`gpu-clean`).
- **DONE (worker recycling):** opt-in `solve.worker_restart_every` (fake-tested), set to 8 in both MEH search
  configs; it does not rescue the 8 GB ceiling but is committed for larger cards.
- **OPEN (verify fidelity):** `verify` reports that the verify mesh equals the screen mesh at the current band/caps;
  only the frequency count and balloon size change. A true higher-fidelity mesh needs a raised dof cap or a lower band.
- **DONE (readiness, measured on the stored T2 winner):** link 1 PASS, link 2 PASS, link 5 PASS, link 6 PASS (J
  9.530 -> 9.727 with a different mid driver and hp_hz, cached, no new solve).
- **FAIL (readiness link 4):** the inner optimiser takes 6.58 s for 1,224 CMA evaluations on the shipped T2 brief,
  3.3x the hand-off's < 2 s gate. Per-evaluation cost is 5.4 ms, so this is an evaluation-budget/combo decision.
- **PARTIAL (readiness link 3):** with the mid drive muted, a 9.19 dB notch appears between 1200 and 1300 Hz
  (+18.7 % to +28.6 % of the 1-D 1.0108 kHz), so the +-20 % gate is met only at the lower edge of that interval. A
  25 Hz sweep over 1150-1350 Hz is needed to place the centre.
- **BLOCKED (M8 step 3):** the meh CAD tool refuses a full model (quarter open shell only), so quarter-vs-full cannot
  be measured without extending the tool.
- **BLOCKED (M9):** Boundary Lab is not present in this workspace; it needs its own environment (pins BEAT 0.6.0).
- **OPEN (M8 step 4):** L0 vs L1 notch comparison is not run.
- **DONE (M10):** bass box - 7 woofer files, `tools/bassbox.py`, 65 tests, `BASSBOX_2026-10-31.md`. Recommendation:
  1 x FaitalPRO 18XL1800 sealed 55 L net + LT; pair = +6 dB; smallest = 1 x 15XL1400 sealed 38 L.
- **OPEN (task text):** M10's "B4 (fs = fb, Qts 0.383, alpha 1) is -3 dB at fs" is wrong for the lossless vented
  box (alpha = 1 gives 0.0 dB at fs; the B4 constant is alpha = sqrt(2)). The test asserts both; amend the task file.
- **OPEN (datasheets):** 15TBX100 (7.8 %) and 18NLW9601 (4.5 %) Vas/Mms vs Fs are internally inconsistent; Beyma
  15LX60V2 Xmax 8 mm vs +/-9 mm. Files follow C8 and say so in `notes`.
- **DONE:** M6 objective v5 + brief `meh:` block (merged, `meh/M6-objective-v5`).
- **OPEN (M7):** `search/evaluate.py` currently only bridges version 5 (params class + scorer registration); the MEH
  evaluation branch that builds `meh_ctx`, runs the inner optimiser and synthesises the response is M7's.
- **OPEN (M1/M5):** cone `frame_od_mm` / `motor_od_mm` / `dish_mm` and CD `duct_mm` are not in the s8 table; M5 keeps
  the C9 [inferred] placeholders (CD duct 40 / 25 / 25 mm) until a drawing is read or M8 measures it.
- **DONE:** M3 multi-tag solve adapter (merged, `meh/M3-solve-adapter`).
- **OPEN (M8 gate):** the installed `hornlab-beat-bem` has no `SolveConfig.impedance_matrix`; every multi-tag solve
  raises ConfigError until M2's fork branch is validated on the GPU and the pin is bumped (owner approves the bump).
- **OPEN (M5 follow-up):** seed renders not produced - `hornlab-render` needs `pyvista`, absent from the venv and no
  installs are permitted. `cd_duct_mm = 0` is not modelled (no disc face without a bore). Unknown cone
  (cutout, depth) pairs are refused until M1's driver files land.
- **OPEN (local, not mine to commit):** the integrator's checkout carried unrelated regenerated catalog work
  (cone_plughorn_2026-10-28 entries typed 2026-10-31 in `examples/catalog.yaml`, `docs/reference/PARAMETERS.md`,
  `TYPOLOGIES.md`, `param-catalog.v1.json`); preserved as a patch outside the MEH branch.

Local-only, pushed 2026-10-30 18:10 EDT (**MEH integration started on the owner's box; no GitHub issue state changed**):
- **IN PROGRESS:** `meh/integration` created from `origin/ccr-4978c80b-tvvcgv` (hand-off section 0); baseline suite
  green after fixing two pre-existing reds (stale sandbox.js dispose pin, CRLF-committed `param-catalog.v1.json`).
- **OPEN (blocker, GPU):** night queue `n2_gapfill_2026-10-30` occupies the only GPU; M8 GPU validation/pin bump waits
  for it to finish (CLAUDE.md: never start GPU work while a night queue runs).
- **OPEN (owner):** confirm the 380 mm box depth assumption (M8 readiness step 1 + layout feasibility depend on it).

Local-only, pushed 2026-10-30 (**MEH implementation hand-off; no GitHub issue state changed**):
- **OPEN (wave 1, dispatch-ready):** M1 driver files, M2 solver fork multi-tag + impedance matrix, M3 solve adapter,
  M4 network + inner optimiser, M5 CAD tool + multi-label STEP, M6 objective v5 + brief block, M10 bass box
  (`docs/meh/README.md`).
- **OPEN (wave 2/3):** M7 pipeline + configs; M8 GPU validation, pin bump, first screen (owner's box); M9 Boundary Lab.
- **OPEN (owner):** confirm the 380 mm box depth assumption.
- **CLOSED:** dossier s13 questions answered by the owner 2026-10-30 (dossier s14).

Local-only, pushed 2026-10-29 20:15 EDT (**mini MEH research pass complete for this round; no GitHub issue state changed**):
- **OPEN (owner decisions):** mini MEH targets - bass route (top + sub / one-box PR-vent ~106 dB / 3-way), size number, use and
  coverage, 4 x 4-inch vs 2 x 6.5-inch, DSP per channel, new J terms, commercial intent (Synergy patent)
  (`docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` s13).
- **OPEN (senior, `NOTES_FOR_SENIOR.md` 2026-10-29):** attribution fix in `docs/DRIVER_MODEL.md:42` (issue #78 is
  timini/horn-simulation); frozen-plan MEH tag note; BL symmetry note.
- **CLOSED (research):** web-lane findings folded into the dossier s7-s8 with orchestrator spot-checks.
- **FINDING:** compression-driver internal depth sets the mid ceiling in a mini MEH (1-D); any MEH model must include it.

Local-only, pushed 2026-10-29 18:45 EDT (**mini MEH research pass, draft; no GitHub issue state changed**):
- **OPEN (owner decisions):** mini multiple-entry horn targets - separate sub vs bass in the box, size number, use case /
  coverage, 4 x 4-inch vs 2 x 6.5-inch mids, DSP per channel, new J terms
  (`docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` s13).
- **CLOSED 2026-10-29 20:15:** web-lane findings folded into the dossier s7-s8.
- **FINDING / correction:** the mesher has MEH tag names 8-12 only, no builder; MEH geometry needs the CAD -> STEP route
  (multi-label) or a new builder. Python `SolveConfig` refuses more than one source tag although the engine supports it.

Local-only, pushed 2026-10-28 20:50 EDT (**cone mid horn typology + research; no GitHub issue state changed**; 8 commits to origin/main):
- **OPEN:** `cone_plughorn` never solved on the GPU; first screen should use `source_motion: axial` and a CPU cross-check of the
  2.4 mm axe-head/throat gap (thin-gap risk).
- **OPEN (handoff):** paper-cone driver T/S unknown (Funktion-One publishes none); axe-head cone fill not modelled (front-chamber
  cut-off estimate too low); see `docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md`.
- **OPEN:** compression-driver library lacks Sd/Mmd for every driver (absolute sensitivity model cannot run on them yet).
- **LOCAL ONLY:** `third_party/` (LibreDWG, ODA File Converter) and `reference/` (Funktion-One CAD) are gitignored by design.

Local-only, added 2026-10-28 17:45 EDT (**no GitHub issue state changed**):
- **OPEN:** round-throat `rt__b1t__rosse_morph` and `rt__b2t__rosse_morph` scored J 1000 on every eval (infeasible); diagnose before re-queueing.
- **OPEN:** verify slips 0.9-2 J for ATH 2in core / ridge and Salmon / Le Cleac'h tall shapes vs screen; screen ranking of those is optimistic.

Local-only, added 2026-10-28 afternoon (**skills + tools, no GitHub issue state changed**):
- **OPEN:** `tools/night_queue/queue.ps1` and `launch_detached.ps1` are parse-checked only; first live use should be the next queue launched
  when no night is running (watch the log and the controller's parent process).

Local-only, pushed 2026-10-28 15:05 EDT (**render sheets for the day's solved styles, no GitHub issue state changed**):
- **OPEN (owner decision):** the new b3a leader `hy__osse_flare_curl` J 1.113 wins on pattern but is weakly loaded (output gap at f0
  11.5 dB, loaded from 1.76 kHz) and `objective.load` is weighted 0 in that brief, so J cannot see loading. Decide: accept EQ, or add a
  load-weighted re-score of the day's top designs before the verify night.
- **OPEN:** screen-only. None of the 2026-10-28 winners has been through `verify`; the D_verify night has not started.
- **FINDING:** non-square mouths (60x40, 72x44) score 11.9-21.6 J on the 90x90 brief (3 of the 4 worst results of the day) - drop that lane
  unless the brief changes. Four-petal Salmon quatrefoils land in the chanterelle band (9-12), not the hybrid band.
- **OPEN:** full offline suite not re-run since the `osse_rollback` / `fc_fold` / `fc_union` changes (blocked by the live GPU night).

Local-only, pushed 2026-10-28 11:36 EDT (**shape work + night queue, no GitHub issue state changed**; 9 commits to origin/unified-typologies):
- **OPEN, first result:** constant-directivity hybrid `hybrid__os_ruffle` J 3.83 (b3a 90x90, 40 solves) vs best Salmon chanterelle 10.73. Refined
  petal/lobe horns (`examples/typologies/petal_os_2026-10-28_v4/`) queued in night `v4_day_H2_hybrids_2026-10-28`; not yet solved.
- **OPEN:** the full offline suite has not been re-run since the osse_rollback / fc_fold / fc_union changes; run it when no GPU night is live.
- **OPEN (owner):** round-throat A/B cells (`examples/typologies/round_throat_2026-10-28_v4/`) queued; the non-round effect is still unmeasured.
- **LEFT ALONE:** `hornlab_search/gui/static/sandbox.js` and `view3d.js` carry uncommitted changes not made in this session.

Local-only, added 2026-10-27 late evening (**P12 senior pass, zero GPU - no GitHub issue state changed; to-dos are P0 in `docs/NEXT_DEV_PRIORITIES.md`**):
- **OPEN, owner inputs:** driver list per brief + use case (tube-amp hi-fi / PA); gate levels (hi-fi sensitivity floor at 1 W / 1 m,
  PA max-SPL target); scoring decisions (output-at-f0 term, stricter hi-fi pattern, 10 m, half weight above f11); woofer block per brief.
- **DEFECT (new):** OSSE / R-OSSE `aspect_ratio` stretches the driver coupling plane (24x36 ... 50x36 mm on 36 mm briefs; 8 of 30
  winners). Owner rule decided: round coupling plane at the exit size, no adapter. Fix: lock `aspect_ratio = 1` in the next night's
  OSSE/R-OSSE copies, then a pre-mesh refusal via `mesh/throat_check.py` (after the night).
- **IN PROGRESS:** ripple/ridge night stopped after 6/10 jobs (runner killed from outside ~20:08 EDT, job 7 at 87/100); re-run
  night `v4_ripple_rerun_2026-10-27` launched 21:27 EDT, detached via WMI (resume job 7 + the three flute jobs that never started).
- **FIXED 2026-10-28:** the night runner now takes over a dead holder's `runs/.gpu.lock` (`gpu-clean` still does not).
- **OPEN (owner challenge):** how much a non-round driver coupling matters is unmeasured; round-throat A/B cells run 2026-10-28;
  a one-design A/B with a round source + built-in transition section is owed (new geometry option).
- **FINDING:** the b3a 90x90 / 400 Hz brief has no acceptable horn yet (leading cells 11-13 dB short of loading; 1.4" OS-type throats
  cannot load there) - needs loading-capable families or a 2" exit, not a re-rank.
- **OWED:** calibration night (band-split screen, 10 m vs 2 m, epw 6 vs 9 presence band, verify-grid rank check); new screen grid
  (low band to 0.7 f0, ~7 presence-band points); budget = valid solves; reduced knobs / two stages / successive halving; CMA-ME shape
  axes; `report --driver` in `cli.py`.
- **Small bug (pre-existing):** `tools/gen_param_catalog.py --check` prints its `committed=` / `fresh=` labels swapped (line 108).

Local-only, added 2026-10-26 (**campaign Phase 0 Steps 2C/3/4/5 LANDED — CPU only, no GPU/Julia; no GitHub issue state changed**):
- **What is now in the tree**: six lane reports (`docs/research/campaign_2026-10-26/`), 14 briefs (`examples/briefs/campaign_2026-10-26/`), 23 configs (`examples/typologies/campaign_2026-10-26/`), and `docs/evidence/CAMPAIGN_DRYRUN_2026-10-26.md`. All 23 cells dry-run green; dofs 921–9,871; envelope 0; mouth within 10 % of K-law on tall/square and inside-envelope on wide; LHS invalid 0–37.5 %; grids 12/29/36; no cell dropped.
- **Open items for the campaign owner/gates (unchanged, now with measured seeds):** (1) the one BEM verify seed per portrait morph/rows class before a long campaign (geometry is proven, coverage is not); (2) `beat_bem` rejects the xz native symmetry plane, so `native__lecleach_asym_odd` keeps `span: full` / quadrants `'1234'` and the `half_xz` 2× saving stays unused on GPU (ISSUES entry in the Phase-0 code commit); (3) Phase B items 1–4 still own the fused s/candidate and the >15,984-dof go/no-go; (4) the D-11 option (a)/(b) choice is now encoded per cell (tall cells strict K-law, wide cells commercial convention) but remains the owner's ruling if the campaign is re-frozen; (5) `cov_band_hz` (D-3) is not implemented and is not needed by these cells (f11 is disclosed per brief instead).
- **Non-blocking residuals recorded in the evidence doc:** LHS invalid rates of 31–37.5 % on four cells (below the >40 % narrowing trigger) are envelope/geometry refusals, not crashes; one `b3bt__rosse_morph` LHS corner is above 12,000 dofs and is graded infeasible; the biradial/hypex generator rows print a pre-existing H/V throat-tangent warning while meshing validly.


Local-only, added 2026-10-27 (**campaign smoke night LANDED - report only, no code/config change; no GitHub issue state changed**):
- **Report:** `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md` - 41 jobs, 376 evaluations, 252 valid / 124 refused (33 %), 157.8 valid evals/hour, T0 26/27, crease A/B at equal budget 60, WALLS, the 8 kHz fused ladder, and the observer phase split.
- **Crease class confirmed on GPU:** `crease__core_law` J 19.022 -> 2.784 (-85 %) keeping the crease (a(45) - mean(a0,a90) = +9.97 deg); `crease__osse_b1w` no gain; control -46 %. One seed each - no typology-vs-typology claim yet.
- **DEFECTS / OWED (new):**
  - `gcurve__osse_b1w` seed was **outside its brief envelope** (783 x 581 vs 380 x 300 mm) -> invalid, its T1 found 0 valid designs. **FIXED 2026-10-27:** the curve station now sits at the mouth (`gcurve_dist 1.0`, width 335; dist box 0.2-1.0, width box 100.5-368.5). Full mirrored mouth **335.2 x 291.5 mm**, T0 **J 9.85253, 1,855 dofs, 3,543 triangles**, v3 dataset record written. A dist-0.5/width-130 workaround was measured valid (367 x 292, J 6.289) but rejected because it changed the intended mouth scale. **Still open:** it pins `aspect_ratio 1.0` while the control runs 1.15, so it is not a clean A/B; and J sees only H/V planes.
  - **The objective terms are not normalised**, so weights do not mean influence: `load 0.5` is 2 % of J on `native__lecleach_rollback` while flat is 45 %. Four of eight scored cells are single-term >70 %. Normalise before any weight tuning.
  - `f_load_hz` = 500 Hz on that seed is the **grid floor**, not a measurement (screen grid starts at 500 Hz).
  - Per-frequency assembly dominates (73-96 % of one frequency's cost), so **frequency count is the throughput knob**; the 8 kHz ceiling binds just above 14k dofs (13,999 = 88 % VRAM, 16,960 = 96 % unusable).
- **Open gates unchanged:** BEM verify seed for the portrait morph/rows cells; T3 diagonal-balloon check for crease vs control (queued); full offline suite; LHS audit of the widened boxes; `tools/expand_walls.py`; sandbox law card browser check; catalog generator recursion into campaign folders; `osse_baseline` 803 x 643 vs its own 750 x 600 envelope; parked `make_shape_variants.py`.
- **Throughput (observer, to be re-measured):** over a ~6-minute search window the GPU solved only ~33 % of the time (`between_evals` 39 %, `refusal_or_mesh` 24 %), median utilisation 24 % at 931 MiB / 19 W, while the ladder rungs were GPU-bound at 100 %. The window is too short to schedule pipeline work from; relaunch `tools/observe_run.py` with the next full search night.

Local-only, added 2026-10-26 (**read-only run observer added - `tools/observe_run.py`; no GitHub issue state changed**):
- Samples GPU util / VRAM / power / clocks, CPU per process, the running job and the newest run's eval rows to `runs/nights/<night>/observe.ndjson`, then writes `observe_summary.md` (phase shares, utilisation histogram). Read-only: no solver launch, no writes into run dirs.
- **First measured facts (smoke night):** GPU is at 100 % during solves but idle through the CPU phases; the card was using 695 MiB at a 4.8k-dof cell while `python.exe` (128 %) and `julia.exe` (144 %) ran the mesh/metrics side at 22.6 % total CPU. Feeds the "2x faster" analysis: pipeline ceiling, concurrency headroom, VRAM per cell size.

Local-only, added 2026-10-26 (**senior scoring review of the native campaign briefs - text only; no GitHub issue state changed**):
- **Changed:** `native_ath_core_2in` and `native_twinray_380_14in` -> objective v3 with K-law f0 (1280 Hz; 743 / 1397 Hz per plane, computed from the published mouth dimensions); `native_lecleach_1200_1in` -> scored on loading (cov 0.3, load 0.5, z_min 0.7; dislope 0). **J on those three brief names is not comparable with earlier results.**
- **Deliberately unchanged:** all B1/B2/B3 briefs (already v3 + f0, wide ones with f0_v), the `*_rows` briefs (dislope 0), the B3b briefs (load 0.5 / z_min 0.7).
- **Known scoring limits, no code change tonight:** H/V planes only (diagonal crease/X-shape effects invisible); the screen grid starts at 500 Hz so the 400 Hz "loads to" claim is only judged at verify; the loading term is band-averaged and diluted by the always-loaded high end; coverage still graded to 8 kHz past the 1.4-inch driver's ~5.6 kHz cross-mode (owner's choice). A T3 diagonal-balloon check for the best crease vs best control is **queued, not run**.
- **DEFECT found during the smoke run (FIXED 2026-10-27): objective-v3 runs wrote no dataset records.** `hornlab_search/dataset/record.py` rejected `objective_version` 3 (`'objective_version' must be 1 or 2, got 3`), logged by **all 27** T0 jobs. `search.ndjson`, `best.json` and reports were unaffected; the phase-2 surrogate data was what was lost. Fixed by moving the allowed set to `hornlab_search/objective/versions.py::SUPPORTED_OBJECTIVE_VERSIONS`, shared with the `search/evaluate.py::_score` dispatch (import-time table check); records now reject anything outside it (`99`, `0`, `4`, `"2"`, `True`) and still treat a missing field as v1. Tests: `tests/test_dataset_record.py` (v3 write/validate/read + dispatch-table equality + end-to-end store), offline **1689 passed, 20 deselected, 1 warning**. A live v3 T0 wrote `dataset/shard-0030.jsonl`. **Records lost on the smoke night are NOT reconstructable from `runs/nights/smoke_2026-10-27/`** (logs + job-level `summary.jsonl` only); the per-eval `search.ndjson`/`metrics.json` survive in the referenced run dirs, so a bespoke backfill is possible from those, but no tool was written.

Local-only, added 2026-10-26 (**campaign boxes re-opened + 4 crease cells ADDED - config/text only, no GPU/Julia; no GitHub issue state changed**):
- **Owner ruling on record:** a search box is never the binding constraint; the brief envelope + mesh validity are. 180 searched knob boxes across the 23 Phase-0 cells were widened to physical ranges (never narrowing an existing edge, seeds byte-identical 23/23, 25 pins intact, `infeasible_penalty: graded` everywhere). Tool: `tools/widen_campaign_boxes.py` (`--dry-run` table / `--write`); table + rationale: `docs/evidence/CAMPAIGN_DRYRUN_2026-10-26.md` §8.
- **New crease class:** `crease__core_law`, `crease__osse_b1w` (per-direction `az_*` law) and `gcurve__osse_b1w` (superellipse guiding curve) against the existing `control__osse_morph_b1w`, all native OSSE with fused CUDA / 12,000 caps / Morph rect at the seed mouth. **Aspect-ratio divergence is an open interpretation:** 1.0 for CORE + gcurve (mesher requirement / circular), b1w's 1.15 for the two b1w cells (1.0 would break the 300 mm envelope). Senior to adjudicate.
- **Open gates:** the widened boxes are **NOT re-audited** - the invalid rate will show in the mini-T1; a T3 diagonal-balloon check (crease vs control, same budget) is **queued but not run**; the crease cells still need a BEM verify seed before any long campaign (same rule as the portrait morph/rows cells).
- **Still owed from Phase 0:** LHS audit of the widened boxes; `tools/expand_walls.py` (auto-widen a box edge best designs press against); the shipped `osse_baseline` 803 x 643 mm vs its 750 x 600 envelope (reseed or widen the brief - owner decision); `tools/make_shape_variants.py` + `examples/typologies/shape_variants/` stay parked and uncommitted ("pre-research ranges; superseded by the campaign crease cells"); campaign-folder configs get no catalog tooltips until `gen_param_catalog.py` recurses.

Local-only, added 2026-10-26 (**per-direction OSSE law LANDED - `az_*` knobs; no GitHub issue state changed**):
- **In the tree:** `design/families.py` folds 11 `az_*` knobs into the mesher's own `p`-expressions for `a`/`n`/`s` (the T0 validity gate for tonight's crease cells), `tests/test_design_azlaw.py` (6 pins), the sandbox law card, and ATH dossier section 5b. Focused gate 125/0/0/0; catalog `--check` OK (no regeneration); `node --check` OK.
- **Open, low priority:** the sandbox law card is committed **unverified in a browser** (owner deferred GUI click-testing); the full offline suite is **deferred** (owner: no CPU time on a night that has GPU work queued); `tools/gen_param_catalog.py` does not recurse into `examples/typologies/campaign_*/`, so campaign cells still have no parameter tooltips; `az_sf_m` is limited to multiples of 4 for quarter symmetry (a `half`/`full` model would need the mirror restriction relaxed deliberately, not silently).

Local-only, added 2026-10-25 (**PLANNED ONLY — nothing started, no code/config/bound touched**; owner-directed; filed as `docs/NEXT_DEV_PRIORITIES.md` **P9**, decision record in `NOTES_FOR_SENIOR.md`):
- **Defect on record (to fix)**: search time-lapse page — the `3D` checkbox renders **checked** while the canvas prints `3D off — flip the 3D toggle above.` Control state and render state disagree, or the render throws into the off-state placeholder. Exact grep anchor is that placeholder string. Not yet confirmed in code (code-map lane still running when recorded).
  **LANDED 2026-10-25 on `unified-typologies` @ cd71c1c** — root cause was a duplicate DOM id (checkbox and 3D container both `id="evo-3d"`); the checkbox is now `evo-3d-toggle` (container id untouched — an existing source pin pins the container markup), box state made coherent, and the stranded `_dispose3d`-on-the-input leak closed; `tests/test_gui_evolution_3d_toggle.py` (4 pins + verified negative control) added; the GUI trio 107/0/0/0 + node --check + compileall green. WebGL painting itself remains an owner eyes-on confirm (headless cannot render).
- **Owner ask 1 — per-parameter descriptions as hover text** on BOTH the Run page and the Typologies page, phrased as *what the parameter does to the geometry/acoustics* (the equation term it moves and the physical effect), grounded in the research dossiers rather than invented. Verified gap: `gui/static/glossary.js` has objective/metric terms only and **zero** geometry-knob entries; `app.js` has brief-field labels only.
  **LANDED 2026-10-25 on `unified-typologies` @ 711b856 (designer lane)** — `gui/static/paramtips.js` reads the committed catalog (graceful raw-key fallback everywhere, never a wrong-family guess); wired onto evolution knob rows, run-detail sensitivity table, seed-derivation card, compose seed preview, and the Typologies cards (knob chips); `tests/test_gui_param_tips.py` 10/10 + GUI trio 118/0/0/0 + node --check green.
- **Owner ask 2 — an interactive typology sandbox**: click a typology → a page that draws the H/V wall section AND the 3D shape, where the owner drags knobs by hand and both views update live (replacing the run page's read-only "evolution" scrub for this purpose). Each slider shows the parameter name beside it, an editable **min and max on either side** of the track, and can **save those min/max as that typology's default**.
  **SPIKE PASSED 2026-10-25 (fix-5, measured):** live-drag 3D is real for generator/grid/native kinds (8-35 ms per full tick); rows kinds are march-bound (148-580 ms -> honest `slow: true` + release-debounce); `multicell_3x3` (CAD) is the only hard `available:false`; one silent-wrong-geometry hazard pinned (the preview entry point builds a default OSSE for unrecognized params - the endpoint must branch on kind first). Endpoint sketch + seam-module rule-2 compliance path recorded in CONTINUITY.
  **LANDED 2026-10-25 on `unified-typologies` @ 8715d88 (backend) + d5e3363 (page)** — full offline suite 1593/0/0/0 + node --check x8 + compileall + catalog --check green; details, timings and honest limits: `docs/CONTINUITY.md` sandbox entry.
  **Owner-screenshot follow-up (fixed):** the quarter mouth ring is now mirrored into a closed outline (both pages), the evolution frame-player's mm-vs-metre rig mismatch that left the 3D panel blank is fixed, and rollback meridians keep their own point order instead of being z-sorted (the striped vertical-plane fringe). Pins added for the ring quadrants and the rollback order.
- **Owner ask 3 — one findable source of truth** joining *typology → design → formula → parameter → min/max → design characteristic → the code that implements it*, for users and agents both. Proposed as an annotation layer over the existing authorities (`families.KeySpec` hard limits, `registry.DEFAULT_KNOBS`, `examples/typologies/*.yaml` bounds) plus a generated reference doc and a drift-gate test — explicitly **not** a hand-written fourth copy of the numbers (`AGENTS.md` line 29).
  **LANDED 2026-10-25 on `unified-typologies`** (P9, commits 4005e8a + bf20807 + 19cad0a): `hornlab_search/design/params/` (generators 26 / rows 36 base names / native 63 knob docs; 39 typologies; zero authored horn numbers), `tools/gen_param_catalog.py --write/--check`, the FAIL-not-warn both-ways drift gate (`tests/test_param_catalog.py`, 37 tests), the generated `docs/reference/{PARAMETERS,TYPOLOGIES}.md`, and the GUI wire contract `gui/static/param-catalog.v1.json` served through the existing static handler. Every knob carries `bounds_source = {file, key}` — the exact home a saved bounds edit must target. Details + honest contract gaps: `docs/CONTINUITY.md` 2026-10-25 parameter-SSOT entry.
- **Verified inputs for it**: 36 catalog ids in `examples/catalog.yaml`; 4 mesher families; 11 generator types; overloaded knob names `n`, `q`, `a_deg`, `T`, `stop_deg`/`max_wall_deg`; open doc/code mismatch `exponent` default 2.0 (`12_RESEARCH_BASIS.md:158`) vs 4.0 (`registry.DEFAULT_KNOBS`).
- **Hard dependency / guard**: the sandbox shows real bounds and must NOT let a "save as default" widen one. Bounds widen only via **W8** (per-typology search-box audit), per config, measured — consistent with the owner's recorded over-constraint remark and the oracle's S1/S5 tables.
- **Still owner-decided** (updated as of the parameter-SSOT landing): metadata package location — **resolved: `design/params/`** (built and landed there; import-light, numpy-blocked proven); whether saved slider bounds are a personal preference or an owner-gated edit to `examples/typologies/*.yaml` — **owner ruled 2026-10-25: edits save to where the bounds live** (to be built safely in the sandbox lane: write only the exact `bounds_source` key, validate against the hard `KeySpec` clamps, never touch a frozen contract, config_sha churn on resume is expected and honest); whether the sandbox may render an out-of-envelope design (and with what marker) — still open, will reuse the run page's at-limit red-marker language + `registry.envelope_overshoot_estimate`; which `exponent` default is canonical — **deferred, not blocking**: tooltips state each typology's actual seed instead, and the 2.0-vs-4.0 mismatch is surfaced with both claims, no winner picked.
- **Brief-set correction (2026-10-26, from the owner's killed run):** the 90° brief was paired with a non-CD Le Cléac'h and with an envelope smaller than its K-law mouth, and the Freeform narrow brief was unreachable because `mouthAngleDeg` is bounded ≥35°. Corrected briefs saved at 500–10,000 Hz; the 10 kHz dof ceiling (largest mouth 284 mm at the 5,000-dof screen cap / 379 mm at the 8,900 hard ceiling) makes most low-f0 briefs infeasible at that top. Full table + reasoning: `docs/CONTINUITY.md` 2026-10-26 entry. Open owner decision: whether the wide/narrow design briefs should keep a 10 kHz top (verify-only / mostly `mesh_too_large`), drop to 2–4 kHz for screen work, or move to a larger-VRAM card.
- **MEASURED GPU ceiling (2026-10-26, stress ladder, real VRAM):** 8 kHz is safe to **474 mm** mouth (5.8 GB peak, 2.4 GB headroom); 500 mm works at 7.2 GB (under 1 GB headroom, too tight for a search); ≥550 mm saturates the card. At 10 kHz: safe to **353 mm** (4.9 GB), edge at 403 mm (7.3 GB), ≥424 mm saturated. **No crash occurred** — the failure mode is CUDA OOM / host-backed pool oversubscription (pool reserved 15.9 GiB), logged as `Out of GPU memory … 100.00% (7.996 GiB)` at the top rungs, with hosts cleared afterwards. Three cap-500 briefs saved (`cap500_90x90_650hz_1p4in` — 90x90 at f0 650 Hz, 434 mm mouth; `cap500_90x60_850hz_1p4in`; `cap500_60x40_1270hz_1in`) plus the owner-override `narrow_60x40_800hz_1in` (794 mm mouth, no cap, may exceed the card at 8 kHz — accepted); practical home is a 5.5–6 kHz screen + 8 kHz verify. Superseded: `cap500_100x100_500hz_1p4in`, `cap500_90x90_565hz_1p4in`, `narrow_60x40_880hz_1in`. Details + full ladders: `docs/CONTINUITY.md` 2026-10-26 MEASURED GPU CEILING entry.

Local-only, added 2026-10-25 (typology pass completion + GPU smoke matrix + Phase-D baseline/R9 audit + GUI hybrid seeds; 6 lanes, exact-path commits; offline 1461/0/0/0 + BYTE-CHECK 24/24 + node/compileall gates):
- **Orphaned WIP landed** (docs-only commit): the prior pass's §16.7/§16.8 + INDEX line — validated against the committed dossiers (append-only, honest labels, no contradiction), prior author's voice preserved.
- **GPU smoke matrix** (the S1a configs' first GPU evidence, M4 pattern, one job at a time): biradial_keele GREEN (J 22.9837, 2086 dofs, 1301→2427 MiB), qtw_waveguide GREEN (J 37.4656, 1616, 1334→2104), lecleach_asym_odd FULL-RING GREEN (J 60.1446, 2815, 1337→3147); salmon_x_signed seed FAILS mesh_too_large (14,414 tris > 11,275; envelope overshoot 0.2201 pinned by the new test file), salmon_ripple12 seed FAILS (5,358 dofs > 5,000 screen cap) — both = owner-gated PROPOSALS (reseed / verify-tier), machinery healthy. Evidence `docs/evidence/TYPOLOGY_SMOKE_MATRIX_2026-10-25.md`, bytecheck `tools/evidence_bytecheck_typology_smoke.py` (24/24 PASS + negative control).
- **Phase-D baseline settings**: `docs/TYPOLOGY_BASELINE_SETTINGS_2026-10-25.md` — five new configs' knobs/bounds/seeds verified per dossier + tier recipe + measured findings; **PROPOSAL-ONLY** default flips (rear_res_factor 1.5 AXI, balloon screen→1024); objective-v3 DECISION CAPSULE for the owner (opt-in today; nothing flipped).
- **R9 audit**: `docs/research/typologies/R9_AUDIT_2026-10-25.md` — all 36 names walked (15 published / 18 labeled / 3 utility) + the do-not-cite ledger + five owner-gated PROPOSALS (lecleach_iwata_ar name, biradial_keele year suffix, C4 prose-vs-entries, §13.4 label hygiene, salmon_x pairing). No silent edits.
- **GUI**: /api/configs + generator_block/seed_params (verbatim); Compose hybrid captions from block shape ("hybrid — A + B"; rows kinds captioned "rows — {types}" after the orchestrator copy-fix) + per-pick seed preview (display-only, payload-fidelity pinned); objective-v3/mixed-key warn surfaces verified landed (4b42862). New test file: signed/ripple config pins (8/8).
- **Still owner-decided**: C4 catalog block (backend); the two smoke-matrix reseed proposals; the five R9 proposals; `examples/briefs/user/` gitignore-or-keep.

Local-only, added 2026-10-25 (evening; 3D render settings LANDED — owner screenshot → fixer lane; brief_authoring 21/21 + node + compileall):
- **Landed**: persisted `hl-v3d-render` (surface satin/matte/metallic/studio · ridges on/thin/off · light ×0.5–2.0), shared `applyRenderLook`/`applyRenderControls` on both `init3d` and `init3dFrames`, clickable overlay chip (pointer-events:auto), immediate apply + global persistence ("swap easily in the 3D view or globally"); defaults = today's look byte-for-byte (existing captures/pins hold); disposal intact; no new hex; app.js untouched.
- **Honest limits**: WebGL cannot run headless — runtime paths source-pinned; chip interaction + cross-surface persistence in a live page await the owner's eyes-on pass.

Local-only, added 2026-10-25 (evening; S1a DRIVER PASS LANDED — oracle-decided/owner-directed; suite 1509/0/0/0; dry-run matrix 15/15; BYTE-CHECK 29/29):
- **Landed**: the brief family `{hifi_90x60, organic_rollback, lecleach_rollback} × {1in, 14in, 2in}` (all f0 + v3, honest f0 derivations in-header); config research: `config.py` closure-aware biradial derivation (rm floored at r0 + tan(a)·L; the ONE owner-directed `widened_to_closure` exception, flagged + test-pinned) + the envelope−2×wall margin; reseeds (biradial L 195 + rm 210/230 bounds; x_signed stop 150/amp −0.15 — the 180° asymptote crossing; ripple12 stop 150; lecleach eps 0.20 + own family brief; elliptical stop 150 = the same recipe from my 4-test triage); C4 catalog (five entries incl. `symmetry: full`); decision record preserved verbatim (`S1A_DRIVER_PASS_ORACLE_FINAL_2026-10-25.md`) + research basis §16.9 pointer + NOTES_FOR_SENIOR.
- **Test-premise repairs (dated, nothing weakened)**: the salmon family's f0 briefs made three fixtures derivation-active — restored via derivation-inert fixture briefs with original assertions/tolerances intact; the salmon_elliptical derived-seed overshoot fixed by the measured reseed; derived-seed invariant drift (saddle 1.129 / x_shape 1.3025 report-only) disclosed — the seed-derivation card shows the clamps.
- **Solve-side**: the OWNER's own screen campaign (pid 14484, `user/7040use.yaml` × the five families) ran against the repaired tree — the queued GPU re-smokes defer behind it / are superseded by its run evidence; J values non-comparable with the pre-repair matrix (new record groups).
- **Still owner-decided**: W8 the per-typology search-box audit (owner-directed, from the at-limit finding; bounds widen per-config only after the audit + cap checks); lecleach_iwata_ar naming (the owner's campaign runs it — the name decision remains open); stale user-brief descriptions (samonrip/75x35) — owner's files; `examples/briefs/user/` tracking decision.

Local-only, added 2026-10-25 (GUI S1a + G6 pass LANDED, re-grounded @ abcbebf; 114 offline tests green (+7) + compileall + node checks ×5; two disjoint fixer lanes, orchestrator reconciliation in place of Oracle per standing owner directive):
- **Landed (objective v3 / S1a)**: brief editor + Compose wizard expose objective version 3 ("scoring floor f0 — cov + dislope score only f ≥ f0"); run-detail KPI "Scoring floor" (target.f0_hz, present-only) explains the below-f0 mask; the seed-derivation card renders the K-law feasibility record from the run's committed config.yaml (per-knob derived/applied, `clamped to bound` pills, below-f0 solved-freq counts). The `J v3` badge is the already-generic `objective_version` renderer — verified, no edit.
- **Landed (G6 mounting)**: badge data verified live pre-edit on both WP12 enclosure runs (`solve_group.mounting` = the normalized block); `mesh_surface` now serves `mounting` additively from `mesh_meta.json`; `view3d.js` draws the dashed enclosure outline from the mirrored mesh's own bounding box (no invented geometry) + an on-canvas themed chip with the real depth/edge/margin values (chip is position:absolute over the canvas — the lanes' after-canvas caption would have been clipped by the fixed-height containers); compare gains the explicit "never rank across mountings" warn when `mixed_keys` includes mounting.
- **Verified-not-built**: axisymmetric-refuses-hv compat refusal already renders readably (campaign reader carries skip_reason; typologies compat reasons per brief) — pinned by a fixture test, no change needed. G5 (P6b owner gate), WP13 (owner-deferred), W7 (backend-gated), C4 catalog picker (pending backend) all stay gated.
- **Plan-doc addendum** appended to `docs/GUI_INTEGRATION_PLAN_2026-10-25.md` (§14): WP12/14/16/17 DONE, W6 landed, §3.8 `source_plug` naming resolved (GUI contract = `source_profile*` diagnostics), §3.11 mounting editor scaffolding superseded by the full-schema briefs editor.
- **Cross-lane note**: the backend stream's docs WIP (`docs/INDEX.md`, `docs/plan/12_RESEARCH_BASIS.md` §16.7/16.8) stayed unstaged/uncommitted here; `examples/briefs/user/` still untracked (owner decides keep vs ignore).

Local-only, added 2026-10-25 (GUI kill-current pass; owner screenshot markers; 107 offline tests green + compileall + node gates; orchestrator direct implementation per "just code it yourself"):
- **Kill run control for EXTERNALLY-started runs** (owner marker A: sidebar pill; marker B: Home running-card action row — both carry it now): two-step armed `■ Kill run` → `POST /api/stop-current` → `jobs.stop_external()` kills exactly the pid recorded in OUR gpu lock file + its child tree, then gpu-clean (never an arbitrary pid; refuses while a GUI-started GPU job runs — the two stop paths never race; refuses killing the GUI's own pid). Safety contract changed by owner direction: the old "GUI only stops its own jobs" rule is superseded for the lock-holder pid our own lock file records.
- **Pill now ALWAYS visible**: idle renders a muted "no run in progress" indicator (owner: "I don't see it" — the old idle rendered literally nothing); external = `■ Kill run`; stopped search = `▶ Resume search`; GUI GPU job = `■ Stop`.
- **Removed**: the transient footer-holder guess (pre-observer) — the markers pointed at the sidebar pill and the Home card; plus the branch-order crash in `toolbarPillHtml(null)` (idle evaluated after the job read) — now node-tested.
- **Kill-safety contract on record**: the kill targets the pid+command OUR lock file records (whoever took our GPU lock wrote it), so the web GUI can never kill an arbitrary process — only the holder of our own lock; the lock file is bounded to the runs dir.

Local-only, added 2026-10-25 (GUI run-controls pass LANDED: Stop + Resume; owner-directed; 103 offline tests green ×2 + compileall + node gates; orchestrator review in place of Oracle per standing owner directive):
- **Landed**: Status-card Stop (three-state ownership rule: GUI-job two-step armed button / external-lock pill naming the pid / nothing; startup-window card), always-visible left-toolbar pill (app.js-injected `#nav-runctl`, 10 s poll, shared two-step arm, all four states), and the GUI `search --resume` plumbing (`resume: <run_id>` → `search --resume <abs dir>`; config optional — the run dir's config.yaml is reused unless `--allow-config-change`; budget omitted = the run's own cfg.search.budget; mode passed from the run's record because the CLI's resume default is screen and rewrites run.json mode; `resume: true` bare-flag refused — the CLI contract takes a DIRECTORY).
- **Semantics on record**: Stop is a hard kill + gpu-clean (no graceful pause exists on Windows — "pause" = stop + resume, which is lossless for searches thanks to deterministic resume: cached rows replay free); budget is PER-INVOCATION, not auto-remaining — deliberate top-ups stay an owner action, never a pill side-effect (the pill guards budget-exhausted runs as finished); resumable markers = run.json status "running" (stale after GUI stop — no "stopped" value exists) / "interrupted"; "finished"/"aborted" not auto-resumed.
- **Honesty engineering on record**: every resume previews first (`POST /api/preview`) and the confirm click is blocked unless the previewed argv carries `--resume*` ("…would start a FRESH search, not aResume; nothing was started"); resume id sourcing = the stopped job's own log_tail, validated against /api/runs (exists + budget not exhausted); Launch-row Resume deliberately skipped (Launch's 2 s re-render wipes a row-level arm mid-confirm — the always-visible pill covers it).
- **Owner visibility note**: the run-controls work was tree-uncommitted when first reported invisible (editable install serves static live but the Python process needs a restart for jobs.py) — after this commit, restart the GUI (`tools/launch_gui.ps1`) and the pill appears in the left toolbar on every page.

Local-only, added 2026-10-25 (GUI deferred-provenance pass LANDED, grounded @ 26a1de1; 93 offline tests green ×2 + compileall + node gates; orchestrator review in place of Oracle per standing owner directive):
- **Landed** (the four deferred items from the CAD-hold deferral): CAD STEP inventory projection onto the chip contract from `mesh_meta.json["cad"]` (verified against the CURRENT step_build keys incl. the WP12 WIP's non-change to the provenance block; sidecar wins; band{k}/meta fallback for WP8 designs added beyond the original spec), `cad_route` solve-group marker via the best-objective-row proxy, `cma_files` run_detail key + restart-card direct log chips, and the `source_profile_alpha` fingerprint pin test.
- **Verified-not-stale**: run-export STEP naming re-confirmed on disk (`<cfg.name>_<rank|seed>_<hash12>.step`; matcher covers both; the listed `STEP_NAME` contract unchanged) — the earlier draft regex would have missed `seed` exports.
- **W6 balloon integration verified already-wired** (the balloon commit's own route/button/back-links) and pinned by a test; zero overlap with the provenance/chips regions.
- **Future G6 note**: the in-flight WP12 mounting WIP was read read-only (brief.mounting normalized block; `mounting_key()` freestanding-safe; `mesh_meta.provenance.mounting` echo) — the mounting badge/preview builds when WP12 lands; nothing pinned against uncommitted code.

Local-only, added 2026-10-25 (docs pass: BL balloon research recorded + density TODO + CAD deferral; docs-only, no code touched):
- **Boundary Lab balloon rendering/resolution/frequency facts recorded** as the owner-directed append-only §12 in `docs/plan/12_RESEARCH_BASIS.md` (sources: committed BL extraction `research/boundary_lab_0.5/bl_inventory.md` + the W6 source recon; GPL-3.0 attribution carried): BL freq defaults 41 log-spaced 200–20 kHz (+ van-der-Corput non-monotonic GUI ordering quirk), balloon = equal-area Fibonacci sphere at `round(41253/angle²)` points from a 0.5–15° precision dial (2.5° default ≈ 6 600 pts), DI as a plain mean over the equal-area balloon, dB-to-radius blob rendering with tubed isobars/radar slicer/octave-smoothed slice.
- **W7 priority recorded** (`docs/NEXT_DEV_PRIORITIES.md`, mirrored in `NOTES_FOR_SENIOR.md`): raise verify/final-tier density — `balloon_points_verify` 512→1024→2592 ladder into 1 000–6 600, verify freqs 25 → ~41 log-spaced — gated on the M3/WP5 ΔDI ladder + 8 GB GPU cost disclosure; feeds the W6 balloon view.
- **CAD deferral on record** (owner directive "GUI-only round"): my CAD reader lane cancelled, its partial code removed from the working tree (verified: `gui/data.py` diff carries only the parallel agent's balloon work); deferred design preserved verbatim in `NOTES_FOR_SENIOR.md` (cad block real key names, filename→hash regex, `cad_route` proxy, cma-files direct-chip listing). The backend M5/M6 CAD stream belongs to the parallel orchestrator session — its live edits in `config.py`/`design/families.py`/`mesh/build.py` untouched; the STOP record in NOTES_FOR_SENIOR is the cross-session signal.
- **Encoding-hygiene lesson**: PowerShell 5.1 `Add-Content` writes the ANSI default codepage — it silently corrupted NOTES_FOR_SENIOR.md's UTF-8 (cp1252 bytes, lossy special chars); caught by byte-level decode check; restored to HEAD (the append-only rule protects committed blocks only) and re-appended ASCII-safe via explicit-UTF-8 Python. All doc files byte-verified valid UTF-8 before commit.

Local-only, added 2026-10-25 (GUI 3D pass: inline run-page 3D + 3D evolution time-lapse LANDED; owner requests; 72 offline tests green ×2 + compileall + node gates; orchestrator review in place of Oracle per owner directive):
- **Commit-hygiene disclosure**: `599997d` (the GUI 3D commit) unintentionally swept in the M5B lane's staged-but-uncommitted files (35 files) — the M5B landing was mid-shared-index at commit time; its authoritative record is `94243df` + its CONTINUITY entry + evidence (bytecheck 33/33). Post-sweep tree verified coherent: offline suite **1335/0/0/0** at HEAD (`runs/m5b_rectify/suite.xml`), `test_mesh_pin` RESOLVED. Lesson recorded: verify `git diff --cached --stat` per-file before every commit when lanes share an index.
- **Landed**: inline ~300px 3D on run detail (lazy fetch, shared persisted shadows toggle, full 3D tab unchanged), `data-v3d` disposal sweep in route() + `isConnected` source-bails (no renderer leaks), `view3d.js::init3dFrames` frame player (union-bounds camera, lazy per-frame geometry build + hot-swap, decimation disclosure, 2D CDN fallback), evolution "3D time-lapse" with the disclosed RULE3D (3D ⟺ improvements-only; "every candidate" stays 2D), `GET /api/evolution/<id>/frames3d` (shared `_improvement_flags` rule with the 2D reader — the two players cannot disagree; cache keyed incl. cap + per-frame mesh mtimes; mesh-less improvements SKIPPED + disclosed in `note`).
- **Open small items**: (a) frame count gaps between 2D "every candidate" and 3D are explained on screen by the reader's skip note — if the owner later wants mesh-less improvements rendered as interpolated ghosts, that is new work; (b) theme/resize re-render resets evolution playback to 2D (pre-existing control-state behavior; disclosed); (c) animation frames are improvement-chain only by design (every-candidate 3D would fetch every evaluated design's mesh — a deliberate honesty/payload trade).

Local-only, added 2026-10-25 (GUI integration plan G1-G4 phase LANDED; owner decision to start now; 63 offline tests green ×2 + compileall + node gates; orchestrator review in place of Oracle per owner directive):
- **Landed**: provenance badge strip on run detail (single source `solve_group`, tooltips = key path, f11 caveat conditional), restart schedule card + QD provenance caption (atlas canvas untouched), compare solve-group banners + DI-guard twin, `verify` GPU job kind (engine-true directory contract), C-5 raw pycma log serving (strict regex + containment), C-2 compare fingerprints (backend + freqs_hz identity always; WP16/WP12 keys read defensively for when their lanes land).
- **Deviation on record**: C-1's `step_files` stays a byte-identical string list (frozen test) — inventory rides the additive `step_files_detail` [{name, inventory|null}]; the GUI plan §5's "entries gain inventory" wording is thus implemented additively. `qd_algorithm` joined the fingerprint beyond §3.9's parenthetical (mixing CMA vs CMA-ME warns — judged correct, disclosed). The plan's "`GPU_KINDS` gain nothing" line predates G-1 and is superseded by the phase spec.
- **Open small items left to later passes**: (a) restart-log direct file chips need a file listing endpoint (C-5 serves files only; the card caption names the URL shape today); (b) STEP-inventory sidecars will populate chips only when the WP14 lane deploys its writer (plain-chip absence is the honest default); (c) `mounting`/`source_profile_alpha` fingerprints fire when WP12/WP16 land their config keys.

Local-only, added 2026-10-25 (GUI Compose wizard pass; owner UX direction "typology first"; LANDED on #/compose — 48 offline tests green, compileall + node --check clean, orchestrator review in place of Oracle per owner directive):
- **`#/compose` wizard landed** (app.js +534/−16 + one nav line + tests): typology-group multi-select first (per-group select-all; disabled configs visible-marked-unselectable with the engine seed-gate reason; uncatalogued configs selectable only as the sole pick, auto-deselected with a stated reason otherwise) → brief step reusing the committed editor (new-from-scratch / typology brief_file / existing-brief-as-is; save-before-launch gate mirrors `jobs._repo_file` refusing non-existent paths) → run step (1 config: dry-run/run/search; 2+: campaign tier + --families verbatim; preview shows the exact command; gpu_busy disables launch with server's reason; job id links to #/launch).
- **Pinned honesty finding**: campaign `--seeds`/`--budget` exist in the CLI but `jobs.build_argv("campaign")` reads only brief/families/tier — values passed via /api/jobs would silently vanish; the wizard therefore ships NO override fields (engine-default budget captions shown) and `test_campaign_budget_and_seeds_are_not_gui_plumbed` pins the pairing. If the CLI flags are ever plumbed into build_argv, BOTH must change together.
- **Disclosed UX behaviors on record**: re-picking a brief source restarts the editor (unsaved edits replaced, not merged); verify_only briefs remain selectable as existing-brief with the "only verify --brief" warning; family compat is never re-implemented client-side — the preview command + per-entry engine skips are the truth.
- **Open small item**: campaign seeds/budget plumbing into `jobs.build_argv` (owner-gated when wanted; the tests above are the guardrail).

Local-only, added 2026-10-25 (GUI briefs pass = c7d2bbf + hardening 95306db; user request + owner UX direction; editor LANDED — 39 offline tests green at the editor commit, 48 after the wizard; compileall clean):
- **Brief-authoring editor landed** (app.js + tests/test_gui_brief_authoring.py): New-brief-from-scratch, start-from-typology picker, every `load_brief` schema key exposed (symmetry/throat_angle_policy/objective/verify_only/description/z_min/freq_weights), payload fidelity (nothing silently dropped), and the GUI-invented 5500 Hz band clamp REMOVED (blamed to 77aac53b with no authored intent; the 8 GB dof-cap hardware note stays as an always-visible hint). Consequence worth knowing: band_hi can now be saved at any value (e.g. 12 kHz verify-only briefs are created from the GUI); search/run/campaign refuse verify_only briefs regardless — server-validated, GUI never clamps.
- **RESOLVED by the Compose wizard pass (block above)**: the typology-first wizard owner direction — shipped as `#/compose` in the next commit; campaign seeds/budget plumbing remains the only open small item (see above).
- **Post-commit Oracle read (returned after c7d2bbf was pushed; verdict GO-with-fixes, all applied in the follow-up commit 95306db)**: remaining suggestions on record — (a) `examples/briefs/user/` is untracked and NOT gitignored: the GUI creates real user briefs there at runtime; a `.gitignore` entry (or an explicit keep-with-sample decision) belongs to the 03-owning lane; (b) `z_min` input accepts values above 1 (spinner-only bound; `Target.from_dict` does not bound it; harmless, hint explains semantics).
- **Oracle waiver on record**: owner directive 2026-10-25 "no more new Oracle passes this round" — the editor's verification was the pasted test output + orchestrator diff read + live schema-fidelity save checks; the already-in-flight read DID land post-commit and its verdict + fixes were incorporated (see the 95306db commit + CONTINUITY).

Local-only, added 2026-10-25 (GUI 3D-quadrant fix pass; user-reported "3D views render just a quarter slice"; fixed + tested — tests/test_gui_mesh_quadrants.py 6/6, tests/test_gui.py 35/35, compileall clean):
- **GRID route writes no `mesh_meta.json`** (by design, `mesh/build.py:273` build_mesh docstring refers to the GRID route): the 3D route (`gui/data.py::mesh_surface`) previously defaulted those designs to `quadrants="1234"` (full model) and so rendered the raw meshed wedge instead of reconstructing the full horn. FIXED GUI-side (fallback chain meta → search.ndjson row → config.yaml → "1234"); the DATA-SIDE follow-up stands open: the GRID route SHOULD write mesh_meta.json for provenance parity (`search/evaluate.py:500-516` logs absence only at debug) — ask for the grid lane.
- **2D mouth doubling covers only `'1'`** (data.py:873-884): for GRID half-models ('14'/'12') the mouth/front-view outline shows the meshed half only — same semantics class as the 3D bug; small follow-up, NOT fixed here.
- **Briefs page: user request RESOLVED (delivered across the briefs + Compose wizard passes, blocks above)** — create a NEW brief from scratch with asymmetric envelopes (w≠h legal for every symmetry value — the engine only refuses axisymmetric briefs with unequal COVERAGE), symmetry control with the verbatim server rule shown, and typology-first picking; the confusing "symmetric horns" behaviour of the old editor was the missing symmetry control + the silent axisymmetric-coverage carry — both fixed.

Local-only, added 2026-10-25 (M5B pass; evidence `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md`, byte-check `tools/evidence_bytecheck_m5b.py` **33/33**; nothing flipped — every new key opt-in, absent = bit-for-bit):

**DEFERRED WP14 physics (owner ruling 2026-10-25 — "table the multicell horn thing for now; landing the category is cool"). The category IS landed (CAD→STEP route, tests green); THE PHYSICS IS NOT TRUSTED YET. The full resume recipe:**
1. **Focal-pair gate result (preserved, NOT to be used for trust decisions):** same mesh both arms (byte-identical `mesh.msh`, `mesh_hash 79c17524af5d`, 4501 dofs, 12 freqs 500–4000, 73-pt balloon): CUDA J=172.566 (17.3 s) vs CPU near+double J=471.984 (314.1 s); compare = **on-axis 11.28 dB / DI 14.59 dB / bw_v 159.1° max diffs** (re-captured `runs/m6_fork/compare_focal.log`) → official gate **NOT ALLOWED** (bar 0.2 dB) on this fixture. bw_h = 180.0° saturated in BOTH arms (no information).
2. **ora-2's diagnosis (the reframe):** (F1, dominant) the fixture's mouth is a rigid `wall` and the driver is the REAR disk facing −z → the exterior BEM solve measures **diffraction around a closed body, not horn radiation**: throat impedance matches a FREE UNBAFFLED DISK within 2–8% in BOTH arms (analytic (ka)²/4), DI is NEGATIVE in both arms (4λ apertures cannot; self-shadowing signature) — **no far-field metric of this fixture is horn evidence until the mouth radiates** (open-mouth wall-shell topology like the OSSE lane, or an explicit mouth BC). (Gate restatement) the 4 kHz gate is unanswerable on this mesh — the validator's own global ceiling is **2891.68 Hz**; re-gate ONLY in the valid band and ONLY on non-threshold metrics (bw_v's 180° readings are −6.0206 dB threshold flips, verified `metrics/polar.py:17-34`; the 1287 Hz valley sits 1.05 dB from the crossing). (Attribution, ranked) #1 = arm-A's **near-correction omission** over ~O(10⁵) septa/second-ring pairs (the library's own refusal names this silent-wrong mode) → **WP17 stage 1 (now LANDED + GPU-validated) is required, not optional, for any multicell GPU screen**; #2 mesh under-resolution near the driver (walls valid 3085.11 Hz vs 4000 requested; DistMax-400 rebuild = 12,694 tris / 6,349 dofs > the 5,000 screen cap — cap raise owner-gated, NOT made); #3 metric amplification (bw_v flips + dislope 597 vs 98); #4 FP32-vs-FP64 unlikely primary; #5 per-frequency-vs-single-call granularity unresolved (arm D never ran).
3. **Resume recipe (in order):** [a] fix the fixture topology: the mouth must radiate (export with the mouth `wall` faces REMOVED from the solid — open aperture — or an explicit treatment; re-prove closed/manifold + the solver's exterior contract for open-aperture geometry per the enclosure route); [b] optionally rebuild the mesh at DistMax 400 mm; [c] run the four CPU arms (plain-single, plain-double, near-single, near-double per-freq) on the SAME mesh + band-restricted (≤2892 Hz) per-frequency table (on-axis/DI; NOT bw_v/dislope); [d] IF #1 attribution confirmed → CPU-near arm re-validated vs the analytic/crosscheck references; [e] then the real gate: CUDA-fused-with-near (WP17) vs CPU with near, < 0.2 dB in the valid band → ONLY THEN are multicell GPU screens allowed. Evidence preserved: `runs/m5_wp14_focal/*` (4 configs: cuda / cpu_near / cpu_plain [arm C ran — read `cpu_plain.log`; NO conclusions drawn], cpu_near_single [arm-D config only]) + the 2 focal run dirs `20261025T112316Z-screen-b22f31` (cuda) / `20261025T112519Z-screen-c6b2d8` (cpu near) + `mesh_meta.json` frequency-validation blocks + `run.json` bodies (cad echo + grid-honesty verified `available:false` in both arms).
4. **WP17 stage 2** (fused CUDA + per-image symmetry near caches): future fork work, refused by design until built (stage 1 = no-symmetry only).
5. **`near_correction*`/`solve_precision`/`source_profile_alpha` are NOT echoed per-row into `Response.meta`/records yet** (the GUI-planning pass's G-3/G-4 gap): the keys ride solve-spec `extra` (hash-distinct) and the WP16/17 diagnostics prove the path in the result — but per-row provenance parity remains a small follow-up lane (echo the set keys into the record's provenance solve block like `mesh_policy` does). GUI reads config.yaml meanwhile (per the GUI plan's disclosed contract).
6. **WP16/17 fork branches + pin state (landed, for reference):** `hornlab-search/wp16-source-profile` @ `f4ef05c`, `hornlab-search/wp17-cuda-near` @ `760a1ec` (test-env tip `a40a204` = CUDA@6.2.0 in the JULIA TEST project only) — pin on main = `760a1ec` (installed == pinned; `test_mesh_pin` green). Fork hosted: github.com/llevaachingada/hornlab-beat-bem (public, GPL-3.0). The pre-existing dev-pin note (`dev/fused-cuda-pin` @ `65c03de`) is SUPERSEDED by the hosted pin.

Local-only, added 2026-10-25 (GUI-integration planning pass; deliverable `docs/GUI_INTEGRATION_PLAN_2026-10-25.md`; docs-only, no GUI code, no GPU, nothing flipped):
- **In-flight WIP disclosed at planning time (owner lanes, untouched by this pass)**: WP14 + M4-debts WIP uncommitted on main (`config.py`, `solve/beat.py`, `gui/data.py` seed-gate memoize, `mesh/grid_build.py` EOF mesh-cache sketch, `pyproject.toml`, `tests/conftest.py`, test files, `examples/typologies/salmon_saddle.yaml`; untracked `tools/cad/` + `tests/test_cad_multicell.py` landed in-tree mid-pass; plus GUI-runtime untracked `examples/briefs/user/7040.yaml` — disclosed, left alone). FORK STATE RE-VERIFIED mid-pass: WP16 **committed** (`f4ef05c` on `hornlab-search/wp16-source-profile`, 7 files) and **pushed** to `ourfork/hornlab-search/wp16-source-profile` (github.com/llevaachingada/hornlab-beat-bem); fork checkout now on `hornlab-search/wp17-cuda-near` (at f4ef05c, zero WP17 commits) with fresh uncommitted WIP in 3 files — the WP17 lane's scope; owner gate B ("fork hosting") is an owner call, not asserted. Lanes own their commits (fix-3/fix-6 pattern; work lands late).
- **G-1** — `verify` missing from the GUI job allow-list (`gui/jobs.py:113-141`): verify runs are only reachable via CLI today; GUI plan G4 adds the (GPU) kind, contained to the allow-list + tests.
- **G-2** — `run.json.restarts`/`qd` written since M5 but never read by any view; GUI plan G2 surfaces them (reader additive keys + restart strip + raw `cma/restart_k/*` download route).
- **G-3** — `solve.near_correction*`/`solve_precision` ride `SolveSpec.extra` (solve-hash-distinct) but are NOT echoed into `Response.meta` (beat.py WIP emits only cuda_fused/mesh_policy/source_motion): per-row provenance parity gap; GUI reads config.yaml meanwhile, per-row echo is a WP14-lane ask.
- **G-4** — handoff's `source_plug` provenance field does NOT exist (rg = 0 hits): WP16 lane must add it to dataset `provenance` or confirm the GUI keys on the fork's `source_profile*` diagnostics; GUI plan adopts the diagnostics as contract (no invented keys).
- **G-5** — WP17 condition: fused-CUDA near-corrected records need a discriminative near-correction-path diagnostic (assembly_path="fused_cuda" alone is ambiguous with WP15); lane note, not GUI work.
- GUI-integration plan itself: P5 W4 `compare --bar` judge still MISSING in cli.py (planned hook, W4 owner-gated); WP6 demo-sheet searches confirmed ABANDONED (owner: 12 kHz capability banked via WP15) — the plan does not carry it.

Local-only, added 2026-10-25 (M5 WP11 pass; evidence `docs/evidence/M5_WP11_2026-10-25.md`; nothing flipped — all new keys opt-in, absent = bit-for-bit):
- **VRAM per-job baseline/peak MISSING for the first three GPU screens** (ipop/bipop/cma_me): the screen lane ran the jobs correctly (durable run.json artifacts carry their proof) but never started its external VRAM sampler; only the fired-restarts screen has the [measured] pair (baseline 430 MiB / peak 2305 MiB). M4 precedent (peak-per-job disclosed MISSING) applies; re-runs cost ~4 min GPU each on FRESH cache dirs (owner's call).
- **QD atlas browser render not exercised live**: route tests (34/0/0) + reader tests + `node --check` cover the served contract; a one-minute manual GUI check on `runs/20261025T080717Z-screen-fd13a7` (has atlas artifacts) remains owner-side.
- **`tools/launch_gui.ps1` — untracked stray predating this pass** (present in the tree before the first WP11 lane): NOT committed, NOT deleted; owner decides commit/delete/leave.
- **`qd` extra transitive weight**: `ribs==0.12.0` pulls numba/pandas/scikit-learn — confined to the optional `qd` extra; noted at Oracle review (exact pin justified: archive semantics are version-sensitive).
- **BIPOP schedule divergences from pycma documented in `_RestartSchedule` docstring** (small-run maxiter cap omitted — the global eval budget governs; our `max` counts all restarts incl. small ones, pycma's counts non-small only): behavior deliberate, next reader diffing against pycma should read the docstring first.
- Resume determinism caveat (inherited, not regressed): `solve_failed` rows are never memoised → a resume after a solver-unhealthy abort re-solves them and may legitimately diverge from the uninterrupted replay (docstring caveat per Oracle; behavior unchanged from cma.py).

Local-only, added 2026-10-25 (M4 pass; evidence `docs/evidence/M4_SMOKE_2026-10-25.md`; Proposals owner-gated — nothing flipped): 
- **P-M4-1** — matched-sampling GRID-vs-FREEFORM equality run before the strict WP10-step-5 J-equivalence claim: the zero-modulation compare (grid_ellipse 1298 dofs vs conical 1319 dofs) is between two DIFFERENT design hashes (`d0dc9b5a8999` vs `f8b94e104f80` — same yaml seed, different surface authorings); measured deltas ≤ 0.110 dB on-axis / ≤ 3.45° bw / ≤ 0.071 dB DI; construction-level equality is proven offline (closed forms ≤ 1e-9); the run-level equality needs GRID n_phi/n_s matched to the FREEFORM mesher segmentation (owner-gated).
- **P-M4-2** — rows-route `stop_deg` bounds [120, 240] include graded-infeasible stops near the Salmon 180° cap-area asymptote (the march refuses 180°; seeds hand-tuned to avoid the zone; lecleach_f90 feasibility sweep: 57/224 knob combos graded `_generator_error`). Consider narrowing (owner gate).
- **P-M4-3** — legacy internal rows kinds (`lecleach_mod`, `lecleach_ar`, plain-lecleach `g_r_lip_mm`) remain in `design/generators/grid.py` unlisted/unconfigured (the shipped contract is the list-harmonic kinds + iwata_ar/toroidal_rollback); a cleanup pass may delete them.
- GRID-route mesh-cache absence (documented `mesh/grid_build.py`): every GRID/rows evaluation re-meshes (screen-size meshes are 0.2–1.2 s — acceptable for smokes, real for searches); a cache keyed on the design recipe + mesh hash is the follow-up if GRID enters search campaigns.
- GRID STEP export unwired (`export_step` → `families.to_mesher_config` KeyError on a grid design; contained per-design by the CLI catch; failure = clean "FAILED: KeyError" line); SHOULD: a clean refusal raising `GeometryInvalidError` instead.
- GUI `list_configs` latency: the data-driven disabled gate materializes every config's seed per refresh (rows marches are brentq loops — saddle ~25 rows); memoize on (path, mtime) + pin the gate with a test.
- salmon_saddle emits the mesher outer-shell clearance warning (wants 3.866 mm on 6 of 33 rings, holding at 5.197 mm) — inner acoustic surface unaffected; seed uses epw 6 to fit the 5,000 screen cap.
- Final offline suite 1194/0/1/0 — the single failure is the intended `tests/test_mesh_pin` tripwire (installed beat-bem fork `fa99ee594087` vs main pin `38544d214ba2`); +226 tests additive-only; never hand-fixed (resolves when the owner hosts the fork pin, docs/FORKS.md).

Local-only, added 2026-10-24 (GUI contrast/visibility pass, docs-only): the local web GUI's rendered dark-theme state fails WCAG in spots — primary button text 2.07:1 on `--accent`, hairlines 1.36:1, chart micro-labels dim, `wallSection` "filled" legend a no-op (fill ≡ plot bg, dashed start profile ~90 % occluded), 3D horn shadow side merges into the canvas, isobar white contours lost on warm bands, budget-over-limit unflagged, theme-toggle first-click no-op + stale SVG after toggle. Full measured list + six-phase fix plan (tokens, theme boot + `?theme=` capture, charts, wallSection, 3D light-gray horn + lighting/shadows, semantics/tests): `docs/GUI_CONTRAST_PLAN.md` (designer-authored, Oracle-reviewed — all MUST/SHOULD/NICE applied). Owner approved implementation 2026-10-24: Phase 1 (tokens/type tiers) landed + verified (`tests/test_gui.py` 30/30; both dark CSS blocks in sync); Phase 2 (theme-boot first-click fix + `?theme=` capture override + async route/scroll/filter restore on toggle) landed + verified (30/30; both themes pixel-checked via the override); Phase 3 (chart contrast: two-pass isobar halo contours, brighter dots/hlines, `--label` target lines + legend swatches, seed strokes 1.7) landed + verified (30/30); Phase 4 (wallSection redesign: even-odd wall-band fill, dashed-start last, throat dots, plain labels) + Phase 5 (3D light-grey horn, 4-light rig, themed canvas, toggleable shadows + light-tone wireframe retained per owner) landed + pixel-verified in both themes. Phase 6 (over-budget flag + literal text at all three readouts, rank/leader/noise text badges, timeline-dot shape+color redundancy, `evolution.js` in the syntax gate) landed + verified (`tests/test_gui.py` 31/31). ALL SIX PLAN PHASES IMPLEMENTED 2026-10-24. Unrelated observed failure: `test_mesh_pin` fails on the WP15 fork lane's in-flight install (hornlab-beat-bem `fa99ee594087` vs pinned `38544d214ba2`) — outside GUI scope, that lane to reconcile per FORKS.md. No GitHub issue opened.

Local-only, added 2026-10-13 (cloud): Phase 2 Stage A code complete but gates unvalidated on real data (needs >= 500 held-out multi-family BEM records, GPU box); widen `a_deg`/`exponent` bounds and run the other 4 configs (GPU box); ISMO selection + `surrogate` CLI built (synthetic-tested); solving proposals with BEM and Stage B-D not started.

Local-only, added 2026-10-13 (local GPU box, data digest): `osse_baseline` bound-pinning follow-up — **corrected per senior review** — the best designs sit at the LOWER bound of `n` (2.0; top-6 6/6 — the strong signal), while `q` is attracted to its lower bound (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but is top-6 0/6 (an earlier "5/6" here was the in-flight 13:40 snapshot, not final data); `a_deg`/`exponent` are interior. The mesher only needs `n > 0`, `q > 0` while `s != 0`, so a future widening of `n`/`q` is indicated (CP-8b handled `a_deg`/`exponent` only). Evidence: `docs/evidence/CP-8c_data_summary.md`.

Local-only, added 2026-10-13 (local GPU box): CP-8 evidence lives in `docs/evidence/` — verbatim checkpoint output (`CP-8a.md`, `CP-8b.md`, `CP-8c_*.md`), live monitor logs (`logs/`), and `manifest.sha256` (SHA-256 + size of the metadata-layer artifacts (run books/ndjson/store JSONLs; label .npz covered by dataset verify, not bit-identity)). Raw `dataset/`, `runs/`, `cache/` stay local and gitignored by design (dataset already 180.6 MB at 1128 records; CP-5 projects 0.78-1.4 GB at 10k) — verify against the manifest instead of committing blobs; use a data branch/release asset to move raw data.

CP-8a..d (local GPU box, see `docs/HANDOFF_LOCAL.md`): CP-8a PASS (480 offline + 18 GPU-marked tests, doctor 10/10, outputs pasted); CP-8b PASS (bounds widened a_deg 25->5 / exponent 2->1, rerun no longer pinned); CP-8c CLOSED - PARTIAL on the literal criterion, verify OK: four runs done - osse_baseline 1500 (best J 6.106 vs seed 22.592, -73%), icw_termination 800 (12.201 vs 55.736, -78%), freeform_hv 722/800 on cma: tolfun (30.543 vs 33.309, -8.3%, low-diversity plateau, 3 searchable keys), throat_adapter 400/400 with ZERO failures (5.983 vs 9.159, -35%); final dataset 3556 records / 8 shards / 587.2 MB, dataset verify OK (0 bad, 0 bad arrays); families OSSE 2034 + ICW 800 + FREEFORM 722 = 3 of 4 (R-OSSE has no example config; the literal all-four-families criterion is unsatisfiable - amended criterion in evidence). Campaign wall ~14.9 h, GPU solve 13.0 h. CP-8d next (indicative): OSSE pool kept 1501 of 1634 -> held-out 225 < 500 -> expect GATES REFUSED (indicative only); propose runs with --allow-unvalidated. **CP-8d OUTCOME (2026-10-14 ~01:10 local): FAILED — GATES FAILED twice** (epochs 300: topk 5/20 + bw_mae 2.110 fail; epochs 600: 5/6 gates pass incl. Spearman 0.9861 / topk 15 / bw 1.704 / di 0.232 / inv 0.952, but monotonic_flips 1 (needs 0)); held-out 285 < 500; model NOT used (propose/round not run); hard rule 8 stop + NOTES_FOR_SENIOR `2026-10-14 cp-8d` block (questions: approve ~10.2 h OSSE top-up to clear the 500 floor; classify monotonic_flips=1). Tables: `docs/evidence/CP-8d.md`. **Flip diagnosis (addendum)**: seed-stable 2-4 % flip rate (seeds 0-5: flips 1/1/1/2/2/2 of 50); three causes — invalid-transition degeneracy, genuine 1-3.7 J undulation on fully-valid lines, and flat-tolerance wiggle sensitivity (tol 0.021-0.023 J); marginal, not a hard defect; NOTES cp-8d ADDENDUM wants owner rulings on sweep-tolerance semantics / invalid-crossing category (thresholds untouched).

Local-only, added 2026-10-13 (local GPU box, icw run): (a) ICW mesher warning "outer wall self-intersects / normal flip near azimuth row 0" — 24 warning LINES, all timestamped 17:06:25, plausibly ONE design of 800 (per-design attribution not recorded); zero new after 17:06; rows still validate and the acoustic (inner) surface is unaffected — caveat on ICW records; senior/oracle pass warranted before trusting ICW exterior physics beyond the inner surface. (b) ICW bound-pinning follow-up: best designs fully pinned at the `hold_end` LOWER bound (0.55, top-6 6/6) and 4/6 near `kappa0` lo = 0.0 (median 0.0016); candidate `hold_end` widening subject to the repo's `hold_start < hold_end` rule + mesher validation. (c) OSSE bound-pinning follow-up from run 1 — **corrected per senior review**: `n` fully pinned at lo 2.0 (top-6 6/6; the strong signal); `q` strongly attracted to lo (23 % of ok rows within 2 % of 0.9, Spearman +0.49) but top-6 0/6 (an earlier "5/6" was a stale in-flight snapshot); mesher needs only `n>0, q>0` while `s≠0`. Both (b)/(c) recorded, NOT changed mid-campaign.

Local-only, added 2026-10-22 (local merge lane, glm-5.3 oracle pre-merge review): follow-ups recorded, none blocking the merge —
(a) `cli.py::_cmd_compare` would raise an uncaught `IndexError` (`ma.freqs_hz[0]`) on the unrealistic empty-frequency-set edge (cosmetic traceback risk only);
(b) the `exponent` alias resolves to the FIRST superellipse station only — pre-existing design-layer semantics; document in config-template comments before any future multi-station FREEFORM config;
(c) `docs/BOUNDARY_LAB_*` + `docs/research/boundary_lab_0.5/` are PROPOSED research awaiting user approval — do not treat as accepted backlog.

Local-only, added 2026-10-22 (local merge lane, user request): GPU-run summary layer committed at `docs/evidence/runs/` — for each of the 7 local `beat_cuda` run dirs (seed screen d627d9, resume smoke 7e6e5b, CP-8b smoke 9e5a5c, CP-8c runs 1-4 ca15be/6bdcbd/ff569c/852be3), the summarized metadata+log layer (run.json, config.yaml, best.json, search.ndjson, cma/*, verify; 108 files, ~16.6 MB) is now IN GIT (previously only in gitignored `runs/`), with index README + `runs/manifest.sha256`. Raw `designs/` blobs, `dataset/`, `cache/` remain gitignored by design; this is an approved exception to the evidence-README "never the data itself" rule (noted in `docs/evidence/runs/README.md`).

Local-only, added 2026-10-13 (senior read-only review of CP-8c/CP-8d readiness, glm-5.3 oracle, branch claude/wave-3-implementation-review-2dk4qe):

**(a) CP-8c yields THREE families, not four** — `examples/throat_adapter.yaml` is `family: OSSE`,
so after run 4 the store holds OSSE+ICW+FREEFORM and R-OSSE stays 0. HANDOFF_LOCAL §5's pass
criterion ("all four families present") is unsatisfiable as planned, and `stats()`'s family
warning (fires only when one family >80%) will never flag a MISSING family (OSSE ≈56% after
run 4). Fix: re-scope the criterion to "OSSE+ICW+FREEFORM present; R-OSSE deliberately absent
(no example config)"; add `missing_families` to `dataset stats` (store.py:441-446, 658).

**(b) CP-8d misreading guards (14-item list in the review)** — (1) CLI must distinguish
"GATES REFUSED (indicative only): held-out 225 < 500" from "GATES FAILED" (cli.py:675 vs
gates.py:115); (2) `round_report`'s `random_true_J` = CMA gen-0 samples, not random, and J=1000
penalty rows inflate medians — pass solved rows only and print the baseline provenance
(ismo.py:56-72); (3) print exploit vs explore medians separately; (4) print the proposals'
parameter spread (the 30 exploits are near-clones of one basin); (5) freeze `pred_J` from
proposals.json and record bundle/config_sha/store count at train; (6) write `ismo_round1.json`
into a run dir and paste it into a new `docs/evidence/CP-8d.md`. Items overlapping #13
(skipped-count printing, verdict persistence, dedupe-by-hash before the holdout split) LANDED
in commit e0b9b61 — none of CP-8d's numbers are quoted before that.

**(c) Data-pipeline integrity at 10k — IMPLEMENTED (commit 11304f6; full offline suite 498 PASS)** —
`verify_store` now checks metric array shapes vs each record's own `solve.freqs_hz` (reported as
`bad_arrays`; `dataset verify` exits 1 on `bad` OR `bad_arrays`); `dataset stats` gained
`n_duplicate_designs` + a `missing families` line in `stats_report` (R-OSSE expected); `search
--resume` compares `run.json["config_sha"]` and REFUSES on mismatch unless `--allow-config-change`;
`surrogate train` splits `GATES FAILED: <names>` from `GATES REFUSED (indicative only): held-out
<X> < 500`; new `surrogate round` subcommand solves proposals through the normal `evaluate` path
into a fresh run dir with its own ndjson and writes atomic `ismo_round1.json` (report + rows +
`random_true_J` provenance + exploit/explore medians + exploit spread + store counts + bundle gate
status + config_sha). `manifest.sha256` README reworded (metadata layer only) and line 3 indent
fixed for `sha256sum -c`.

**(d) Evidence corrections** — CP-8c_osse_baseline.md "5/6 near q lo" contradicted its own table
(fixed: top-6 0/0, median 0.9033 — stale snapshot claim); the 13:11 snapshot's "seed J 22.07" was
the smoke seed (fixed: 22.592); ICW warning "~a few % of designs" unsupported (fixed: 24 lines,
one timestamp, plausibly one design of 800); `data_summary.json` `generated_local` lacks a
timezone (add `generated_utc`).

CP-9a..d (cloud GPU pod proof, cap study, campaign, train/gate; see `docs/CLOUD_GPU_REPORT.md` section 6): proposed, awaiting user decisions on provider and spend cap; no GitHub issue yet.

CP-10a..d (high-frequency options, 12 kHz; see `docs/HIGH_FREQUENCY_OPTIONS.md` section 6): proposed, none run; CP-10d needs the user to approve contacting Collin.

Added 2026-10-14 (cloud): **#13 fixes F1-F6 ready on `ccr-455d2184-yj5zk4` (draft PR #14). Merge into this branch AFTER CP-8c, BEFORE CP-8d.** #13 stays open until then.
**[SUPERSEDED locally, 2026-10-13 ~23:00: the SAME issue-#13 fixes are already on this branch — local commits e0b9b61 (8 items) + 11304f6 (store/CLI follow-ups), full offline suite WITH the mesher: 498 PASS / 0 failures. Do NOT merge PR #14 on top — that would double-apply overlapping changes in `surrogate/**`. Cloud owner: diff e0b9b61+11304f6 against PR #14 and adopt ONE set. CP-8d proceeds on this branch's fixed code either way; `propose` here refuses unvalidated bundles by default with `--allow-unvalidated` for the runbook's indicative round.]**

Added 2026-10-14 ~05:00 UTC (cloud): PR #14 REBUILT on `622776a` — local issue-#13 set (e0b9b61/11304f6) adopted, cloud duplicates dropped; adds FREEFORM sculpt config, FREEFORM training-export fix (dotted keys were NaN), `compare`, DI-provenance guard, NaN refusal, FREEFORM throat radius. Merge, then HANDOFF section 6b. Open, no GitHub issue: FREEFORM full-vs-quarter GPU check + bar ruling; mesher wall-port feature request; HornLab author naming (user to confirm).

Added 2026-10-21 (cloud): Boundary Lab 0.5.0 integration PROPOSED (`docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`; research `docs/BOUNDARY_LAB_0.5_RESEARCH.md`). No GitHub issue yet; open decisions: phase order A->B->C, ownership rows, BL env on the GPU box, contacting JW Sound / HornLab author.

Added 2026-10-22 (cloud): senior architecture report `docs/SENIOR_ARCHITECTURE_REPORT_2026-10-22.md` (Boundary Lab: sidechain, plugin parked; priority and to-do list). On `main` (`2311f92` + this commit).

Local-only, added 2026-10-22 (local GPU box, HANDOFF 6b): FREEFORM quarter-vs-full symmetry check PASSED (max 0.0043 dB, beamwidth 0.051 deg; bar 0.1 dB / 1 deg, not frozen - owner may freeze it); `freeform_sculpt` 60-eval search 0 failures, J 30.945 -> 24.213. Follow-ups (non-blocking): (1) `compare` header prints `quadrants None` for both runs although they solved 451 vs 1636 dofs (reads the wrong field; cosmetic); (2) dry-run throughput estimate 2 s/candidate vs measured 6.7 s for `freeform_sculpt` (TOOLCHAIN M3 extrapolation under-predicts; affects budget planning only); (3) watch `profileH.mouthAngleDeg` (2/6 at hi 70) and `profileV.points.3.1` (2/6 at lo 108) on any longer sculpt run before widening. CP-8d must not be re-run before the OSSE top-up (CONTINUITY Next action corrected). Evidence `docs/evidence/HANDOFF_6b.md`.

Local-only, added 2026-10-22 ~11:40 (local GPU box): follow-up (1) `compare` quadrants label FIXED (regression test). New `export-step` CLI (senior report s3 item 4) DONE. Sculpt budget 400: J 30.945 -> 16.789, **3 wall anchors PINNED** (`profileH/V.points.3.1` at lo, `profileV.points.4.1` at hi) - the disjoint per-anchor radius boxes now bind; options for the owner: widen/overlap the boxes with a mesher monotonicity check, or reparametrise as positive increments. Bound-limited families awaiting a widening decision: OSSE `n` (6/6 lo), ICW `hold_end` (6/6 lo) + `kappa0` (4/6 lo), throat_adapter `throat_ext_angle_deg`/`k` (6/6 hi) + `a0_deg` (6/6 lo), FREEFORM sculpt anchors above. No widening done (user OK required).

Added 2026-10-22 PM (cloud): Boundary Lab learnings implemented (`docs/BL_LEARNINGS_IMPLEMENTATION.md`): pre-solve topology + symmetry-domain checks, `solve/phasor.py`, runtime provenance, report-only SPDI / beam shape. 

**NEXT DEVELOPMENT ROUND, TOP PRIORITY (user decision 2026-10-22): read `docs/NEXT_DEV_PRIORITIES.md`.**
- [ ] **P1 Fused / direct CUDA Burton-Miller assembly** in the exterior driver (post-beta; Magnus's OK or a pinned fork). Fused path is CPU/Metal only (`hornlab_beat_bem/julia/BeatEngineDriver.jl` ~l.1215); the CUDA single-matrix assembler `assemble_burton_miller_neumann_system_cuda` (`julia/src/BeatEngineCudaBurtonMiller.jl:350`) is called only by `runtests.jl`. Engine work, not a flag flip. Expected: 8 GB ceiling ~9k -> ~20k quarter dofs (~12.6 kHz at epw 6 on the large OSSE seed) [inferred]. Validate with selftest --analytic, --crosscheck (< 0.2 dB) and an A/B vs today's CUDA path before any data counts. NOT enabled for the 2026-10-22/23 overnight queue (one solver for the compare tier and surrogate top-up).
- [x] **P2 12 kHz finalist verify pass on the 4060**: DONE 2026-10-23 (see the item below and `docs/evidence/HF12K_VERIFY_2026-10-23.md`).
- [ ] **P3 `beat_metal` backend** for the collaborator's Apple Silicon MacBook (fused path on, unified memory); Mac selftests + 3-design A/B vs the 4060 before mixing data.

TO-DO (no GitHub issue yet; owner / plan ref):
- [x] Merge the learnings PR, run its section-4 test plan on the GPU box: DONE 2026-10-22 (FF to 265133f; `docs/evidence/BL_LEARNINGS_GPU.md`).
- [x] Early rejection offline replay: DONE 2026-10-22 (`docs/evidence/EARLY_REJECTION_REPLAY.md`): < 0.1 % GPU saved at K = 4 / 25 % margin, no top-20 lost; recommend NOT implementing as specified (owner ruling).
- [x] (closed 2026-10-23 by the failure cache) Search budget counts uncached failures: a re-run with the same CMA seed replays cached successes for free but re-evaluates every earlier failure, which consumes budget without solving (OSSE budget 40 -> 0 new solves, 2026-10-22). Options for the owner: cache failures by design hash, or count only solver-reaching evaluations (task 08; `search/cma.py`).
- [ ] CPU-vs-CUDA qualification screen per pinned-library change (GPU box; frozen CP-7b rule; s2 item 8). Note: beat_cuda vs bempp_cpu re-run 2026-10-22: 0.039 dB (`docs/evidence/SOLVER_VERIFY_2026-10-22.md`).
- [x] Typology plan v2 implemented 2026-10-22 (generators, hybrids, briefs, `families`/`campaign`, failure cache, loading metrics). GPU checks V4/V5/V7 in progress.
- [ ] Le Cléac'h / spherical-wave generator DISABLED (R9): implement only from a verifiable published construction (ETF 2010 lecture PDF too large to fetch, diyaudio thread 403, sphericalhorns.net calculator disclaims fidelity to JMLC). Needs a human-supplied reference.
- [ ] Brief `source.cap: auto` not applied: FREEFORM keys in `families.py` do not expose the mesher's source-cap radius/auto-angle; every design uses the mesher default cap (consistent within a campaign). Add the keys (task 04) and tie to the brief.
- [ ] Generated horns use a 3 mm outer shell (mesher FREEFORM curvature guard); Magnus-family configs use the mesher default shell. Outer-shell thickness differs between the two groups; small acoustic effect at the mouth rim, recorded per design.
- [ ] `search_smoke` (legacy) cannot be dry-run under a 5.5 kHz brief (seed exceeds its dof cap); harmless, legacy only.
- [x] `search --brief/--cma-seed` were silently ignored (fixed 2026-10-22; first campaign's native-family entries invalid and re-run).
- [x] Campaign fairness: cached replays gave native configs 6-15x more search; `--max-evals` caps all evaluations (fixed 2026-10-22).
- [x] Hygiene left BEAT `worker_host` processes (which respawn julia) alive; now cleared with their julia children (fixed 2026-10-22).
- [ ] `perturbed_osse_hv`: 36 % invalid in the screen run and `L_mm` pinned; revisit its bounds/u_max before a compare run (widening needs user OK).
- [x] Brief size envelope now enforced for every family (outer mesh bbox); native configs sized for other targets (osse_baseline, freeform_sculpt under the 400x300 brief) have no valid design and are labelled so in the leaderboard. Beta users: use typology configs or size a native config for the brief.
- [ ] Mesher upstream 4573bc90 is 57 commits past our pin b922e807 (FREEFORM corner topology `d740c28`, `68ed646`, joins `967db56`; ATH import; new geometry keys). Signatures and the 0.4 curvature guard unchanged. Owner 2026-10-22: keep the pin for the beta; post-beta bump candidate with its own verification ladder.
- [x] R8 brief provenance: dataset records carry optional `provenance` {config, brief, brief_hash, generator} (2026-10-22).
- [x] C2 epw 6 vs 8: axi seed DI 0.124 dB > 0.1 -> axi typologies at epw 8 (owner); H/V within 0.05 dB stays epw 6.
- [x] GPU lock + `gpu-clean` (2026-10-22); overnight queue + watchdog in `tools/overnight/`.
- [x] GPU lock liveness on Windows: `os.kill(pid, 0)` made a live holder in another console look stale (takeover / gpu-clean would hit a running solve). Fixed 2026-10-23 with OpenProcess/GetExitCodeProcess + tests.
- [ ] OSSE `exponent` presses its upper bound (7.9 of 8) in the 2026-10-23 top-up (seen in the time-lapse): bound decision for the owner, like the other pinned bounds.
- [x] **Search does not recover a dead BEAT worker host** (2026-10-23; FIXED 2026-10-23 ~14:30, offline-tested: root cause = `hornlab_beat_bem.worker.get_worker` caches a `HostedBeatWorker` that keeps its dead socket after a send fails, so every later solve wrote to it; `recover_after_failure` now also calls `detach_workers` (drops the cache), `BeatBackend` re-warms and retries a `worker_exit` candidate once, and `search` stops RESUMABLY (status aborted, `SolverUnhealthyError`) after 3 consecutive `solve_failed` instead of ending on `tolflatfitness`; `to_training_arrays` drops `solve_failed` records from labels (`meta.skipped_solve_failed`). Tests `tests/test_solve_beat_recovery.py`, `test_search_cma.py`, `test_dataset_store.py`. The host death itself is still unexplained, GPU rule 7. Original report: OSSE top-up seed 4101 lost its host at 03:58:48 EDT (`ConnectionResetError` 10054, `solve_failed [worker_exit]`); every later candidate failed in ~3 s (21 rows), J went flat at the 1000 penalty and CMA-ES stopped on `tolflatfitness` at 411 of 950 evaluations. Cause of the reset unknown (second unexplained reset tonight; first in the C2 check 21:46, not reproduced from clean, CLAUDE.md GPU rule 7). Fix proposal (task 05/08): on `worker_exit`, re-warm the host once and retry the candidate before scoring a failure; never let a run of solver failures end a search. The 21 `solve_failed` dataset records are failures of the solver, not of the designs (non-deterministic kind, never failure-cached); exclude `solve_failed` from the surrogate's validity labels.
- [x] Local web GUI `hornlab-search gui` (2026-10-23, `docs/GUI_PLAN.md`). Open: macOS untested; 3D view needs the three.js CDN. Launch GPU-busy state now LIVE (polls `/api/status` every ~6 s, toggles note / Start button, toast; 2026-10-23 14:30; the server still re-checks on launch). Senior UX pass done 2026-10-23; typology picker, Typologies page and graphics pass done 2026-10-23 (09:00); search time-lapse player 2026-10-23 (10:40); beta hardening + Boundary Lab-style isobars 2026-10-23 (11:30, d0a04ea).
- [x] Wire `surrogate.features.require_surrogate_config` into `cli._cmd_surrogate`: done 2026-10-23 (merged).
- [x] Beta-readiness pass per `docs/HANDOFF_BETA.md` (F timed rehearsal DONE 2026-10-23 16:30, 8 friction points fixed, `docs/evidence/BETA_READINESS.md` F; G session plan refreshed with measured timings; A-G; A-D done (D3 Ctrl-C PASS on the GPU 2026-10-23 after a campaign fix; D5 paths PASS); E running overnight; F, G pending): upstream audit, R8 brief provenance in dataset records, epw convergence above 2.5 kHz, GPU lock / gpu-clean, rehearsal, session pack.
- [x] `compare` tier (2 CMA seeds) on the leaders: DONE 2026-10-23 (`docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`).
- [ ] Bound proposals from the compare tier (osse_axi `h_s`, hypex/exponential `L_mm` lo, perturbed_osse_hv `L_mm`/`v_a_deg`, hybrid `v_rm_mm`): owner decision; NOT applied.
- [ ] rosse_baseline is seed-sensitive (12.3 vs 14.3): more seeds or budget before any ranking claim.
- [x] Failure cache: deterministic failures cached by design+mesh+solve key across runs (fixes the OSSE seed-replay budget burn).
- [ ] Stage 2 transient analysis (impulse, step, CSD waterfall, group delay, dense throat impedance) on finalists: research + design in `docs/research/TIME_DOMAIN_RINGING.md`; needs a dense uniform frequency list per evaluation (today only 12/25/36-point log grids, too sparse: Magnus's `plot_impulse_response` interpolates over resonances). After the typology campaign; not in the search loop.
- [x] R-OSSE: `examples/rosse_baseline.yaml` added 2026-10-22 and run in the hifi screen + compare campaigns (seed-sensitive: 12.3 vs 14.3, see below).
- [ ] ICW rollback termination never exercised (categorical; needs its own config). In the typology plan.
- [ ] `freeform_hv.yaml` solves the full domain although FREEFORM quarter == full within 0.0043 dB (4x dofs wasted). In the typology plan.
- [x] STEP-export CLI: DONE locally 2026-10-22 (`hornlab-search export-step`, b822dd5).
- [x] OSSE data top-up for the surrogate gates: DONE 2026-10-23 (user OK 22:14): seed 4101 411 evals (host death 03:58), seed 4102 951 evals. Retrain + CP-8d gates next (CPU).
- [ ] Boundary Lab BL-1 export (cloud; `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`).
- [x] `compare` IndexError on empty frequency list: fixed 2026-10-23 (merged).
- [x] `verify --brief` was parsed and silently IGNORED (found 2026-10-23 preparing P2; would have re-verified at 5.5 kHz). Fixed: the brief is applied and the results go to their own run dir `runs/<ts>-verify-<id>` (listed by the GUI; `run.json.verify_of`); `verify` without `--brief` unchanged. Test `tests/test_search_verify_brief.py`.
- [ ] Collaborator pulling `main` 2026-10-23 evening: `docs/HANDOFF_COLLABORATOR_2026-10-23.md` (branch + PR; owner merges after the GPU jobs).
- [x] P2 12 kHz finalist verify pass: DONE 2026-10-23 16:07 (`docs/evidence/HF12K_VERIFY_2026-10-23.md`): 14 designs, 0 failures; epw converged at 12 kHz (<= 0.058 dB, <= 0.31 deg); rankings as in the compare tier; peak VRAM 7,360 MiB above baseline at 6,049 dofs (edge of 8 GB). 8-12 kHz compares geometries, not drivers (f11 7,914 Hz).

- [x] Docs index `docs/INDEX.md` and code map `docs/CODE_MAP.md` added 2026-10-22, linked from CLAUDE.md / AGENTS.md / .claude/CLAUDE.md; keep them current.
- [x] Campaign Ctrl-C and host hygiene (2026-10-23): `run_job` killed a Ctrl-C'd child mid clean-up and skipped the leaderboard; a campaign never cleared its Julia/BEAT hosts (snapshots only). Fixed (grace period, partial INTERRUPTED leaderboard, exit 130, hosts cleared after every job); D3 PASS live (`docs/evidence/BETA_READINESS.md` D).
- [ ] Surrogate retrain 2026-10-23 (`docs/evidence/CP-8d_retrain_2026-10-23.md`): GATES FAILED (topk 11/20, invalid_accuracy 0.80, monotonic_flips 4) at 600 epochs; held-out 463 < 500 (indicative). Model NOT used. Owner: ~250 more OSSE records for the floor; flips semantics; why the ranking/validity gates got worse with more data.
- [x] `*_12k` verify-only briefs were accepted by search/run/campaign and offered by Launch (2026-10-23 rehearsal): `verify_only: true` brief key; search/run/campaign refuse (exit 2), Launch hides them; tests in `tests/test_search_verify_brief.py`.
- [ ] Live demo on a shipped brief replays from the cache (~1 min, same CMA seed): use a saved brief copy (5.5 min measured). A `--cma-seed` option for `campaign` would make fresh live runs possible on shipped briefs (owner, task 08).

Local-only, added 2026-10-24 (senior pass): implementation backlog WP1-WP17 in `docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md` (objective v2, driver pinning, fused CUDA in our fork, 12 kHz screens, GRID shapes, multicell); owner gates: WP13 third-party axisymmetric solver, GitHub hosting of forks, v2 as default.

Local-only, added 2026-10-24 evening (orchestrator, M1 implemented + Oracle-verified; pushed): WP1, WP2, WP3, WP4 (offline parts) and WP15 repo-side plumbing LANDED (see `docs/CONTINUITY.md` 2026-10-24 entry; Oracle verdict GO, all 3 must-fixes in the push commit; 933 offline tests pass, no test loosened).
- [x] WP1 objective v2 + offline re-score: DONE (`docs/evidence/OBJECTIVE_V2_RESCORE.md`; rho 0.989, claims survive, v1 drift 0; v2 stays OPT-IN — making it the brief default is an owner decision).
- [x] WP2 driver pins with embedded-brief grandfather: DONE (2 pre-WP2 runs with an embedded 12.7 brief on a 17.78 OSSE config now load byte-for-byte; new `--brief`/`brief_file:` runs enforce; `osse_baseline` is skipped under 1-inch briefs by the campaign compat check).
- [x] WP3 shape-only perturb + pre-mesh `invalid_envelope` + graded penalty (opt-in `search: {infeasible_penalty: graded}`): DONE; all shipped typology seeds estimate 0.0.
- [x] WP4 `freq_weights` (v2-only, v1 warns once) + `verify_points_per_octave` HF verify grid: DONE.
- [x] WP15 repo side (`solve.cuda_fused`, env gating, `assembly_path == "fused_cuda"` proof + refusal): DONE offline; fork branch `hornlab-search/fused-cuda` @ fa99ee5 (Julia tests green). Gpu ladder + ceiling measurement NOT RUN yet (M2; owner: do not pin a file:// URL on main).
- [ ] Oracle non-blocking follow-ups (recorded, none urgent): (1) `invalid_envelope` not failure-memoized (brief-dependent; revisit with a brief-aware marker key in M2); (2) envelope estimator adds full wall thickness radially — conservative by ~2.5 mm at 80 deg mouths (documented; no shipped seed affected); (3) dataset record lacks an explicit `objective_version` field (config_sha covers it today — add in M2); (4) solve-cache/`ctx.known` reuse keys exclude the objective version — never flip objective version on a resume; start a new run; (5) v2 solve-cache hits re-score with the CURRENT weights like v1 (documented behaviour, unchanged by design); (6) `_verify_only_precheck` precedence note for the CLI docs (verify_only wins over a broken config — intended); (7) `tools/rescore` duplicates the balloon-collapse block of `metrics_from_response` (drift-0 verified; keep in sync); (8) cosmetic tautology in `test_solve_fused_flag.py` last assert.
- [ ] `tools/launch_gui.ps1` (pre-existing untracked, benign): owner decides; kept out of the M1 commit.
- [ ] Owner decisions queued from M2 onward: fork GitHub hosting + push; v2 default; WP13.

Local-only, added 2026-10-24 late (orchestrator, M2 executed; pushed): WP15 fused CUDA **validated on the GPU** (see `docs/CONTINUITY.md` 2026-10-24 M2 entry; evidence `docs/evidence/FUSED_CUDA_2026-10-24.md`; raw logs gitignored under `runs/m2_fused_cuda/`).
- [x] WP15 install + validation ladder: DONE — analytic **0.020 dB** (bar 0.5; = base reference), crosscheck **0.0390 dB** (bar 0.2; = base reference), from clean GPU states.
- [x] WP15 3-arm A/B vs the base pin's stored runs (flag OFF): osse_axi seed `d04e8697a87d`, perturbed_osse_hv best `fed761193da7`, freeform_sculpt seed `892bb3551903` re-solved with FRESH scratch cache dirs (**finding: the solve cache is NOT keyed by lib SHA** — stale cache entries would otherwise have silently served old-SHA responses as "A/B") then `hornlab-search compare`: design hashes match; max diffs **≤ 2.9e-6 dB / ≤ 2.1e-05 deg** (bars 0.039 dB / 1°). This is the step-8 old-path reproduction proof; A/B run dirs confirm `lib_shas.hornlab_beat_bem == fa99ee5…` and `meta.cuda_fused == False`/absent everywhere.
- [x] WP15 fused GPU test: DONE — `[measured]` fused-vs-default @ 2 kHz: on-axis max diff **0.0000 dB** (bar 0.01), bw H 76.65→76.65 / V 84.18→84.18 deg (bar 0.1), z_throat rel **3.35e-07** (rtol 1e-3); the stale-host fused REQUEST (env flipped on a host spawned before it) was REFUSED. **Determinism finding (rule-7 trail):** the test's zero-tolerance bit-identity assertion FAILED on the fork **AND identically on the BASE PIN 38544d2** after a rollback reinstall — two identical CUDA requests differ at one Float32 ulp (order-varying reductions; worst observed **1.74e-05 dB**); pre-existing upstream property, not a fork regression. Rebarred to a documented **1e-4 dB** floor with the measured evidence in the docstring + a `[measured]` print (NOTES_FOR_SENIOR 2026-10-24 block); the fused-vs-default bars themselves are untouched; **Oracle adjudicated: rebar PASS (base-pin reproduction decisive; all three measurements now in the docstring; full rulings in CONTINUITY)**.
- [x] WP15 ceiling re-measure (owner capped the sweep — no 24k point; the clean-state 20k confirm was interrupted): fused **FITS 15,984 dofs** (peak−baseline **7,637 MiB**; assembly already memory-pressured at **437 s/freq**); **FAILS 20,237** (BEAT worker-host death on the attempt AND the in-process re-warm retry; peak 7,831 MiB — recorded **provisional**, clean-confirm not completed per owner). Old path on the SAME 8,919-dof mesh: **7,389 MiB / 59.6 s** vs fused **2,217 MiB / 9.1 s**. The "~20k inferred" did NOT materialize on this card/protocol. Measured SAFE caps: **verify/final 12,000 dofs** (measured 12,183: 4,744 MiB, 13.72 s/freq). Harness `tools/measure_fused_ceiling.py` (fresh process, threaded external nvidia-smi poll, verified shutdown; `--mesh-only` calibration — note: TOOLCHAIN M1's res→dof table was measured on a SMALLER horn: the osse_baseline seed at 3/1.5 mm is 43,993 dofs, so the sweep calibrated mouth-res 6.72/5.74/5.02/4.45 mm).
- [x] `_fusedcuda` configs: DONE — 4 NEW files (`osse_baseline`, `osse_axi`, `perturbed_osse_hv`, `freeform_sculpt`), caps 5000/**12000/12000** + `solve.cuda_fused: true`, provenance headers; originals untouched (`git diff -- examples/` empty on the originals).
- [x] 12 kHz verify on the flag: DONE — ONE verify job `runs/20261025T013051Z-verify-be4adb`: osse_axi seed via the fused config's run dir + `verify --brief axi_90x90_1in_12k`: verify J **17.0339** (not comparable with screen J — different band/grid), **4,438 dofs** / 8,626 tris (below the raised 12,000 cap — the epw rule chose the mesh), **52.89 s / 25 freqs ≈ 2.1 s/freq**, response.npz `cuda_fused: True` + **25× `assembly_path: fused_cuda`**; **f11 = 7,914 Hz caveat applies (8–12 kHz compares GEOMETRIES, not drivers)**.
- [x] Suite: dev-pin tree = **938 passed / 0 failed / 0 errors / 20 deselected** (junitxml `runs/m2_fused_cuda/suite_dev.xml`, 217.9 s; total collected 958). Main tree (base pin vs installed fork): same selection, exactly 1 failure = `test_mesh_pin` — the INTENDED pinned-SHA tripwire until the owner lands a hosted pin (expected state, documented in CONTINUITY + TOOLCHAIN). Selection +3 vs M1's 935 = the new `_fusedcuda` configs in parametrized config sweeps + the concurrently-landed GUI-contrast lane's tests. Nothing loosened.
- [x] Pin policy: `pyproject.toml` + `TOOLCHAIN.md` pin @ `fa99ee5` committed ONLY on **`dev/fused-cuda-pin` (65c03de, LOCAL ONLY — not pushed, not merged)**; a file:// pin must never reach main. **Owner asks: host the fork on GitHub + push, then replace the dev pin; then M3 (WP5–WP8).**
- Deferred to M3+ for time: M1 follow-up (3) explicit dataset-record `objective_version` field (config_sha covers it today); M1 follow-up (1) `invalid_envelope` memoization (revisit with a brief-aware marker key — Oracle: the fix is one line, add brief_hash to the marker's replay-validity; the graded penalty already recomputes on replay so only the stale *verdict* is the hazard). **BOTH DONE in M3 (commit `1dda493`, 2026-10-25): explicit `objective_version` written by every record + absence-tolerant v1 reads; the `invalid_envelope` marker stores + requires `brief_hash` on replay (graded penalty unchanged; test where a different brief re-evaluates).**
- ~~Owner advisory (pre-existing on origin/main): the 2026-10-24 night entries reference `docs/NEXT_DEV_PRIORITIES.md` section "P4", which exists only in the owner's local uncommitted note — commit it separately or treat those references as pointing to the local note.~~ **RESOLVED (~00:30 2026-10-25): the P4 note is now committed verbatim** (in the same commit that adds the P5 easy-wins section: W1 rank audit / W2 dense finalist net = P4a scheduled / W3 named screen-grid group, gated / W4 `compare --bar` / W5 freq-weights emphasis); the night references resolve to actual file content now.
- Handoffs issued for the next two passes (2026-10-24 late, owner directive: the shipped demo briefs are NOT their design intent — never GPU-search demo sheets): (1) **M3 execution** (full text in chat, owner holds it): carry-over fixes (`objective_version` field; `invalid_envelope` brief_hash marker) + WP5 calibration + WP7/WP8 speed checks on STORED designs, ZERO new searches, ~15–20 GPU solves; (2) **brief design** committed as `docs/HANDOFF_BRIEF_DESIGN_2026-10-24.md`: study list → 10-question owner interview (verbatim capture) → real-driver web grounding → 2–4 real briefs + baseline settings, offline-validated → GPU = ONLY the owner-approved POC (budget 20 + one fused 12 kHz verify). Sequence: M3 first, then brief design. Band stays 700–12,000 (14 kHz+ screens would blow the 5,000 cap and ~2× per-candidate cost above f11 with no realism gain; a screen-cap raise for band_hi > 12,000 is OWNER-GATED). Handoff GROUNDED (same evening): full capability map (§2b) of what the later plan lands — M3 in flight (carry-overs `1dda493` + WP5 proposals + WP7 rear factor + WP8 band-split), M4 (WP9 generators, WP9b JMLC/Kugelwellen/organic/X T1–T7, WP10 GRID Fourier sections, WP12 mounting), M5 (WP11 restarts, WP16 >f11 realism, WP17 near-correction, WP14 multicell CPU-first) — plus four forward-compatibility rules for the briefs (landed keys only; stated family-allow-list assumption; variant briefs pre-planned for curl/organic appetite; every future-dependent item marked "awaiting WPxx").

- **OWNER ITEM (agent-tooling, 2026-10-25 early):** THREE opencode project skills landed after Oracle hardening passes — `.opencode/skills/hornlab-gpu-job/` (per-GPU-job hygiene/capture recipe; exit-3 + FORKS-tripwire semantics; fresh-measurement + fresh-cache rules), `.opencode/skills/hornlab-evidence/` (evidence assembly + pre-publish byte-check of EVERY quoted block) and `.opencode/skills/hornlab-typology-research/` (the horn-design grounding protocol: sourced dossiers + R9/rename-gate discipline before typology/shape work; AGENTS.md + CLAUDE.md carry the block). Applied on the next opencode run (config-time files). **Owner config decision:** the slim preset gates skills per role (`orchestrator: ["*"]`, but fixer/explorer/librarian/designer/council: `[]`) — lane sessions never see the skills; either add the three names to those roles' arrays in `.opencode/oh-my-opencode-slim.json` (one-line each) or keep embedding the ceremony in dispatch prompts.
- **W6 balloon GUI view: LANDED (2026-10-25, ~01:10):** the Balloon 3D view + radar slicer + isobar slice are implemented in the web GUI (own implementation of BL's display grammar; GPL attribution in code; server routes read-only + path-safe; `tests/test_gui_balloon.py` +9; gui tests 44/0; both-theme screenshots under `runs/gui_balloon/`). Ships with today's stored balloon densities (screen 16×32; verify 23×45); the verify-balloon density upgrade stays gated on the M3/WP5 ΔDI ladder (W7 in NEXT_DEV_PRIORITIES).

Local-only, added 2026-10-24 night (user request, docs-only; full write-up: `docs/NEXT_DEV_PRIORITIES.md` section "P4"):
- [ ] **Narrow-resonance blind spot + dense finalist check (P4a, idea)**: the screen grid is 12 log-spaced points
  (500 Hz–~5.5 kHz), verify 25 points — a horn defect narrower than the ~1/3-octave gap (mouth-reflection
  resonance, organ-pipe mode, narrow cancellation) can fall entirely between solved frequencies; nothing is
  simulated between grid points, interpolated plots render smoothly over the defect, and the objective cannot
  score it, so a peaky horn can outrank a clean one. Proposed safety net: re-solve the FINALIST shortlist only on
  a dense uniform in-band grid (24–48 points or the WP4 8/octave pattern over the whole band) and diff vs sparse
  metrics; auto-flag families whose dense J degrades. No contract change needed; cheap (a handful of designs).
- [ ] **Perceptually weighted non-uniform frequency grid (P4b, idea; FROZEN-CONTRACT matter)**: extra solved
  points at hearing-critical/problematic regions (~2–3 kHz, ~4–5.5 kHz, possibly the 0.5–1 kHz mouth-reflection
  onset) instead of even log spacing. Requires an owner-approved amendment of the frozen 01_CONTRACTS §8 grid
  (2026-10-13 ruling declined per-user YAML grid keys; a changed grid changes the solve hash and cannot train/
  cache with existing grids) — must be a NEW NAMED grid group with the point list fixed in the contract (the
  `*_12k` brief / WP4 `verify_hf` pattern), not a free-form key. Related: WP4's `verify_points_per_octave`
  (verify-only, >5 kHz) and v2 `freq_weights` (reweights solved points only) already landed.

Local-only, added 2026-10-25 (orchestrator, M3 executed; pushed): carry-overs + WP5/WP7/WP8 calibration on EXISTING stored designs, ZERO new searches (owner directive). Evidence `docs/evidence/MEASUREMENT_PACK_2026-10-24.md` (17 GPU jobs, 728 s GPU wall, no crash/OOM); harness `tools/m3_measurement_pack.py`. Oracle verdict GO-with-fixes — ALL applied (MUST: `rear_res_factor` also keys the solve cache/failure markers/resume memo via solve-spec `extra`; the evidence doc's counter wording fixed; SHOULD: §5.1 Band-2-dofs + seam-walls honesty notes, row-echo pinned by tests; NICE: a failed seam solve is recorded in `meta["seam_check"][edge]["error"]`, pre-M3 marker backcompat docstring).
- [x] M3 carry-overs: dataset-record explicit `objective_version` field + `invalid_envelope` brief_hash-scoped failure marker (commit `1dda493`; 6 tests) — DONE.
- [x] M3 framework keys (opt-in, absent = byte-identical config/mesh/solve hashes, tested): `solve.source_motion`, `mesh.rear_res_factor` (rear-only scale; READ-FIRST honored — MeshDensity `rear_res_mm` drives ONLY outer shell + rear cap), `mesh.band_split {edges_hz}` + `stack_responses` (exact tiling) + verify-only seam check + `mesh_policy: band_split_v1` provenance — DONE (24 tests).
- [ ] **Owner-gated PROPOSALS (nothing adopted, no default flipped):** (1) `distance_m: 10` for v2 briefs — 2→50 m |Δbw| > 1° in-band on ALL THREE finalists; max |ΔDI| 2→50: AXI 1.61 / HV 0.59 / RO 0.54 dB (residual 2→10 m up to 8.66°/0.86 dB — better, not converged); (2) raise the screen balloon 512 → 1024 — max |ΔDI| 0.1545 dB (AXI @ 7,567 Hz) / 0.1110 (HV @ 12 kHz), fires 2/3 (1035→2592 ≤ 0.0407); (3) `mesh.rear_res_factor: 2.0` — AXI screen dofs 1,397 → 1,060 (**−24.1 %**), J −0.00697, top-5.5 kHz CP-7f bars all pass (1.5 also passes, −18.8 %; 3.0 unmeasured); (4) `source_motion: axial` measured only (AXI/HV ≤ 0.007°; RO up to 0.4331° bw @ 12 kHz, above the f11 = 7,914 Hz caveat) — no proposal mechanism, default stays "normal".
- [ ] **WP8 band-split verdict: FAILS the CP-7f acceptance gate on BOTH designs** (in-band maxima AXI 1.2476°/1.2166°/0.1529 dB/0.4218 dB raw on-axis, HV 1.0957°/0.9259°/0.1021/0.4041; failure concentrated in band 0, band 2 bit-identical to the single mesh; seam deltas −0.237/−0.111 dB AXI, −0.271/−0.043 dB HV in `meta["seam_check"]`) despite measured walls **−53.5 %** (AXI, 29.64 vs 63.68 s) / **−28.2 %** (HV, 33.82 vs 47.08 s) vs the same-code single-mesh solve. Machinery + provenance landed opt-in only; the band-0 fidelity issue must be addressed before any adoption (owner decision).
- [ ] Suites at the final state: focused post-fix subset 68/0/0/0 (`runs/m3_code/suite_oracle_fixes.xml`), full offline **968 tests / 1 failure (= the expected `test_mesh_pin` tripwire) / 0 errors / 0 skipped** (`runs/m3_code/suite_final.xml`); compileall clean.

Local-only, added 2026-10-25 (orchestrator, M3 executed; pushed): carry-overs + WP5/WP7/WP8 calibration on EXISTING stored designs, ZERO new searches (owner directive; WP6 cut). Evidence `docs/evidence/MEASUREMENT_PACK_2026-10-24.md` (17 GPU jobs / 728 s GPU wall, no crash, no OOM, verbatim logs, MISSING cells disclosed); harness `tools/m3_measurement_pack.py`; raw logs gitignored under `runs/m3_wp5a|wp5b|wp5c|wp7|wp8/`. Oracle verdict **GO-with-fixes — ALL applied** (MUST-1: `rear_res_factor` also keys the solve cache/failure markers/resume memo via solve-spec `extra`; MUST-2: the evidence doc's stale "no junitxml counters" claim replaced with the real suite files/counters; SHOULD: §5.1 Band-2-dofs ambiguity closed + seam-inclusive-walls honesty note + row-echo pinned by tests; NICE: a failed seam solve records `{"error": ...}` in `meta["seam_check"]`, pre-M3-marker backcompat docstring).
- [x] M3 carry-overs: explicit dataset-record `objective_version` field + brief_hash-scoped `invalid_envelope` failure marker (commit `1dda493`, 6 offline tests) — DONE.
- [x] M3 framework keys (opt-in; ABSENT = byte-identical config/mesh/solve hashes, tested): `solve.source_motion`, `mesh.rear_res_factor`, `mesh.band_split {edges_hz}` + new `stack_responses` (exact-tiling assertions) + verify-ONLY seam check + provenance `mesh_policy: band_split_v1` in ndjson rows + records — DONE (24 offline tests).
- [ ] **Owner-gated PROPOSALS from M3 (NOTHING adopted; every flip is the owner's):** (1) `distance_m: 10` for v2 briefs — 2→50 m |Δbw| > 1° in-band on ALL THREE finalists (max |ΔDI| 1.61/0.59/0.54 dB; residual 2→10 m up to 8.66°/0.86 dB — better, not converged); (2) raise the screen balloon 512 → 1024 — max |ΔDI| 0.1545 dB (AXI @ 7,567 Hz) / 0.1110 (HV @ 12 kHz); 1035→2592 ≤ 0.0407 (fires 2/3); (3) `mesh.rear_res_factor: 2.0` — AXI screen dofs 1,397 → 1,060 (**−24.1 %**), J −0.00697, top-5.5 kHz bars all pass (1.5: −18.8 %; 3.0 unmeasured); (4) source_motion axial measured ONLY (AXI/HV ≤ 0.007°; RO up to 0.4331° @ 12 kHz, above the f11 = 7,914 Hz caveat) — no proposal mechanism.
- [ ] **WP8 band-split verdict: FAILS the CP-7f acceptance gate on BOTH designs** (in-band maxima AXI 1.2476°/1.2166°/0.1529 dB/0.4218 dB on-axis; the failure concentrates in band 0; band 2 is bit-identical to the single mesh) despite wall −53.5 % (AXI, 29.64 vs 63.68 s) / −28.2 % (HV, 33.82 vs 47.08 s) vs the SAME-CODE single-mesh solve. Machinery + provenance landed opt-in; adoption and any band-0 fidelity fix are owner decisions.
- [ ] Suites at the pass's final state: focused post-fix subset 68 / 0 / 0 / 0 (`runs/m3_code/suite_oracle_fixes.xml`); full offline **968 tests / 0 errors / 1 failure / 0 skipped** — the single failure is exactly the expected `tests/test_mesh_pin.py` tripwire (installed fork `fa99ee5` vs main's base pin `38544d2`; clears via the dev pin when the owner hosts) (`runs/m3_code/suite_final.xml`).

Local-only, added 2026-10-25 (docs-only, owner request, follow-through): the P6 research was hardened into a **full implementation plan v1.0** via two parallel web-research lanes — `docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md` REWRITTEN (dossier folded in). **P6a basis now evidence-grade:** quarter-domain superformula rules (m ∈ {4, 8, 12} integer multiple-of-4; m1 = m2 mandatory for quarter meshes [derived]; non-integer m = open curves; the `n1 < 2 ∧ max(n2,n3) > 10` degeneracy guard from Symmetry 2022; a/b ratio-only search; canonical Ath reference values quoted incl. User Guide §6.4.2; mouth-theory record: no published non-elliptical-mouth→HOM claim, gradual axial shape change is the defensible rule, Dong JASA 2024 enclosure masking; **no public repo searches superformula horn parameters — verified GitHub-wide, a genuine first**). **P6b basis:** fixed-budget primary (anytime-slice {100,200,400}), gap-closed normalization, 30 surrogate / 10-15 real-GPU seeds with honest power framing, Wilcoxon rank-sum + Holm + Â12 with ONE pre-registered endpoint; **GSA library audit → own ~120-line module + 8 named tests + 10 pitfall requirements** (no maintained GSA exists: nevergrad/mealpy/pagmo = no, NiaPy = retuned variant, canonical MATLAB port = unlicensed; GSA-NGC = unverifiable, still barred from configs/docs); the crippled-GSA budget trap handled by a mandatory offline N/g0 tuning stage; decision rule D17 pre-registered. Plan structure: work packages WP-P6a-1/2 + WP-P6b-1/2/3 + WP-P6-GUI-1/2 (mouth-outline SVG preview + `#/bakeoff` view) + WP-P6-4 senior pass; FOUR parallel Wave-1 lanes with zero file overlap + verbatim dispatch prompts; checkpoints CP-P6-0..4. **Execution gates unchanged (both required): WP1-WP17 complete + owner GO (P6a/P6b independently runnable).** Still open: the collaborator's "AVE" spelling. No code, configs, tests, or GPU touched; committed and pushed with this commit (owner directive, 2026-10-25).

Added 2026-10-25 (typology-expansion + scoring full-repair pass, CLOSE OF ROUND - see CONTINUITY entry same date):

- [ ] **Open (next handoff): C4 catalog completion** - add the 5 new configs (biradial_keele / qtw_waveguide / salmon_x_signed / salmon_ripple12 / lecleach_asym_odd) + the salmon_saddle_v2 + the iwata_ar-2in + the toroidal JMLC-350 variants to examples/catalog.yaml (the header/fields already document them; lecleach_asym_odd = the NEW symmetry value full, quadrants 1234).
- [ ] **Open: C3 the Tritonia-law rows kind** (the published alpha(theta) power laws over the OS-SE base, amplitudes as genes; fully specified in 12_RESEARCH_BASIS 13.7 - primary pages fetched + verified) + the segmentizing genes (seg-horn eqs 2-4) as the follow-on.
- [ ] **Open: P8b owner decision - the diagonal-consistency objective term** (45/135 vs H/V from the stored balloon; no new solves) - the only scoring change that DIRECTLY rewards the figure-8/puckered class.
- [ ] **Open: GPU smoke matrix** for the 5 new configs (M4 pattern: ONE job machine-wide, runs/.gpu.lock, gpu-clean before/after, fresh cache-dir, external VRAM poll; bytecheck evidence per the m4/m5b template).
- [ ] **Open: Phase D baseline tables** - per-typology K-law default knobs + default briefs carrying target.f0_hz + objective v3 (the landed axi_2in_large.yaml = the template).
- [ ] **Open: GUI hybridization (P8d)** - compose-wizard multi-typology hybrid runs + the seed-gate fixed to the SELECTED brief (gui/data.py:958-969 finding) + feasibility/derived-mouth in the compose preview.
- [ ] **Open: Oracle physics review** of the new typology claims (the house norm for typology code).
- [x] LANDED this round: biradial + qtw_waveguide generator types (R9-sourced) + the splice C1 fix (0.5-deg bar) + signed x_amp v2 + the lecleach_asym odd-cosine full-ring rows kind (mesh-proven on the real adapter) + the even-lobe mouth ripple + the full span + objective v3 (the below-f0 mask + freq-weighted cov) + the K-law feasibility preflight + the brief-derived seed/bounds (clamp-only) + the axi-brief compat refusal + graded penalty on the organic configs + the stale-Le-Cleac'h/docstring catalog fixes + 5 research dossiers + 12_RESEARCH_BASIS 13.1-13.8 + NEXT_DEV_PRIORITIES P8 + NOTES record. Suite 1461/0/0/0 (runs/s1a_suite/suite_final.xml).
- [ ] **Infra: opencode restart needed** - the subagent provider fallback (.opencode/oh-my-opencode-slim.json flipped to ollama-cloud primary after the deepseek outage killed 5 launches with empty results) binds at the next opencode start.

Added 2026-10-25 (ATH framework pass, local-only):
- [x] Native morph_* (incl. morph_exponent, target 3) on OSSE / R-OSSE / ICW / FREEFORM; generator opt-in through the same knobs; absent target = byte-identical.
- [x] `ath_core` (native OSSE, 15 searchable knobs incl. Morph target/exponent/width/height/corner/rate/fixed) + `ath_twinray_380` (published-dimension superellipse reconstruction, 12 knobs); catalog + briefs + catalog/param artifacts.
- [x] First GPU seeds + dry-runs + 1606/0/0/0 offline suite; evidence docs/evidence/ATH_TYPOLOGIES_2026-10-25.md; dossier docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md.
- [ ] Open: exact CORE a(phi) law (needs a rows/generator extension); FREEFORM rectangle morph on an elliptical H/V base trips the mesher non-convex guard (measured); Mesh.Roundover / Ath Rollback / enclosure fidelity; an owner-approved morph campaign.
- [x] Senior review 2026-10-26: morph_target 0..3 guard (R-3) + test; ATH lane committed; suite 1607/0/0/0.
- [ ] Open (campaign 2026-10-26): Phase 0 code fixes (seed_policy explicit, target.f0_v_hz, ICW nested r0 pin, rows span half_xz), campaign briefs/configs, night runner, smoke night - handed off to another agent.

Added 2026-10-26 (campaign Phase 0, implementation lane code-1):
- [x] `generator.seed_policy: explicit`: skips the f0 seed/bounds derivation while keeping the K-law feasibility block; `derive`/absent is byte-identical (config_sha + derived seeds pinned). Validation refuses any other value as `generator.seed_policy`. Directive stripped before materialize/mesher. Tests `tests/test_config_seed_policy.py` (10/10); gate 1626/0/0/0 (`runs/step2a/suite.xml`).
- [ ] Open (this lane next): ICW nested `icw_seed.r0_mm` WP2 driver pin (Step 2C). Other Phase 0 items (target.f0_v_hz, rows span half_xz, campaign configs, night runner) remain with their owning lanes.
- [x] ICW nested driver pin: `icw_seed.r0_mm` is now forced/refused by the same WP2 `_force_pin` rule as root `r0_mm`; new `tests/test_config_icw_driver_pin.py` (4/4); gate 1630/0/0/0 (`runs/step2c/suite.xml`). Remaining Phase 0 items stay with their owning lanes.

Added 2026-10-26 (campaign Phase 0, implementation lane code-2):
- [x] Objective v3 amendment: optional per-plane `target.f0_v_hz` (owner-directed). When set, cov is the sum of the H error over `f >= f0_hz` and the V error over `f >= f0_v_hz` (freq_weights restricted per mask); `dislope` keeps the H/f0 mask. Validation refuses `f0_v_hz < f0_hz` or `> band_hi_hz`, naming `target.f0_v_hz`. Absent = the pre-amendment expression verbatim (config_sha/seed/solve-spec/J goldens pinned bit-identical; dataset/feasibility records emit the key only when set). New `tests/test_objective_v3_f0v.py` (9/9); gate 1639/0/0/0 (`runs/step2b/suite.xml`). `docs/plan/01_CONTRACTS.md` untouched (frozen); dated amendment in CONTINUITY + NOTES_FOR_SENIOR.
- [ ] Open (this lane next): Phase 0 Step 2D (`span: half_xz` rows model for `lecleach_asym_odd`) and Step 2E doc fixes; the GPU half-vs-full equivalence A/B stays Phase B item 5.

- [x] Overnight campaign night runner landed (RUNNER lane files, committed by impl-code2): `tools/run_campaign_night.py` + `tests/test_tools_night_runner.py` (9/9). Sequential one-GPU protocol (julia kill + `gpu-clean` + lock wait + VRAM baseline, per-job timeout/tee, ndjson eval accounting instead of `--budget`, `summary.jsonl` + `SUMMARY.md`, no retries). Gate 1639/0/0/0 (`runs/step2-runner/suite.xml`).

- [x] Phase 0 Step 2D `span: half_xz`: rows span phi 0..180 (ODD n_phi >= 25, upper half across xz, quadrants `'12'`) for `lecleach_asym` (its `cos(phi)` term is even under the up/down mirror; plain `span: half` stays refused). `_GRID_SYMMETRY_AXES` now derives `'12' -> ('y',)` from `sizing.SYMMETRY_PLANE`; `grid_outer_points(half_xz=True)`; mesh/outer-shell call sites updated. Measured CPU: half mirrors the full ring to 1.7e-13 mm, 1,485 tris vs 3,036 (2.04x). New `tests/test_design_generators_grid_halfxz.py` (5/5); param catalog regenerated; gate 1644/0/0/0 (`runs/step2d/suite.xml`).
- [ ] Open: Phase B item 5 GPU half-vs-full A/B (<=0.05 dB / <=1 deg) before switching `lecleach_asym_odd` from `span: full` to `half_xz` in campaign cells. **Backend gap found while landing 2D:** `hornlab_beat_bem` rejects `native_symmetry_plane='xz'` (BEAT mirrors x=0 / x+y only) while `hornlab_bempp_bem` accepts it, so the A/B needs the bempp route or a pinned-fork change; no solver code was changed here. Step 2E doc fixes remain for this lane.

- [x] Phase 0 Step 2E doc fixes: dated correction at the TOP of the S1A verbatim oracle record (the biradial `widened_to_closure` widening is K-law-driven, reached 396.9/352.8 mm, past closure; body unchanged). CONTINUITY records that the scalar `n_in_band` is the COV-SCORED point count (screen 9 / verify 21 for an f0-850 brief), not the band count, and that the field is NOT renamed (stored records + frozen terms key set); with `f0_v_hz` set it is the H-mask count. INDEX/CODE_MAP untouched (no new doc/module). Gate 1644/0/0/0 (`runs/step2e/suite.xml`). No GPU/Julia work.
- [x] GUI discovery 2026-10-26: configs/briefs at any depth, no run cap, auto per-brief leaderboards from run folders, night runner on the Status page.
- [ ] Campaign config lane: b1t__lecleach_iwata_ar.yaml spells a retired product name (neutral-naming test fails) - fix before the smoke night.
- [x] Sandbox 2026-10-26: free/search-limits switch, explore ranges, fixed-knob sliders, Morph card + save-as-search-rows, refused shapes drawn, measured size/envelope, 3D fold tolerance; self-approach chord-vs-arc false refusal fixed.
- [ ] Param catalog generator scans examples/typologies/*.yaml only - campaign subfolder configs get no tooltips until it recurses (sandbox falls back to the config file).
- [x] Ath crease class: OS-SE guiding curve exposed in the sandbox (OSSE); mesher config refusals shown, not 500.
- [ ] Open: native-OSSE TwinRay/CORE typology that searches gcurve_* + Morph (the crease class); per-azimuth a(p) expression knobs.
- [x] README rewrite with GUI screenshots; main fast-forwarded (2026-10-26).
- [x] 2026-10-26 learnings recorded (docs/research/LEARNINGS_2026-10-26.md).


Local-only, added 2026-10-27 (no GitHub issue state changed): objective v4 implemented + two v4 GPU nights (first + resume); open: re-run crease__osse_b1w (resume startup failure), biradial_keele cells refuse ~90 % of candidates, HF data sync tabled (P11), merge of unified-typologies to main.

Local-only, added 2026-10-27 (evening; no GitHub issue state changed): resume night done; ripple/ridge night running (10 jobs); P12 sim-vs-real investigation opened (loading weight 0 on most briefs, ideal source, generous cov) with the SIM_VS_REAL research report; pushed to main.

Local-only, added 2026-11-02 (no GitHub issue state changed): GUI frequency-axis band + scoring-floor f0 marker landed with offline pins (37 tests pass across the three GUI test files); MEH CPU-vs-CUDA benchmark scripts committed under tools/bench/.
Local-only, added 2026-11-02 (no GitHub issue state changed): **P11 HF data sync DONE** - public dataset repo <https://huggingface.co/datasets/chingadalleva/hornlab-search-data> (7 tar shards, 10.77 GB packed: text/solve/dataset; meshes not uploaded), `tools/hf_sync.py` corrected to `hf upload`. Owner-machine finding: Xet uploads stall here; upload with `HF_HUB_DISABLE_XET=1`. Still open in P11: merge to `main` (which branches) and the two v4 re-runs.
