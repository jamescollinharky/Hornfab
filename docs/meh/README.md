# MEH implementation handoff (mini multiple-entry horn top + bass box)

2026-10-30. Owner un-deferred MEH for implementation ("you control labels, architecture, design, typologies, solves
and scoring; hand the rest to cheaper sub-agents"). This folder is the hand-off: one frozen contracts file plus one
task file per work package. **A sub-agent reads `00_MEH_CONTRACTS.md` and its own task file, nothing else is
required.** Design basis and every number's provenance: `docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md`
and its `mini_meh_2026-10-29/calc/` scripts (the reference implementations the tasks port and test against).

## What is decided (and why, in one line each)

| Decision | Value | Basis |
|---|---|---|
| System | MEH top from 120-160 Hz up + separate bass box 30-120 Hz flat | owner; mids cannot do EDM bass (dossier s5) |
| Envelope | 406.4 x 406.4 mm face (16 in), 380 mm deep, corner-hung | owner; depth = orchestrator assumption |
| Primary typology T2 `meh2_6x2` | 1.4 in CD + 2 x 6.5 in on the top/bottom walls, 90x60, XO 650-1100 Hz, HP 120 Hz | only complement with ~116 dB at 125 Hz; 6.5 in front chamber puts the port corner near 700-950 Hz (cross there); top/bottom 77 % layout-feasible vs 41 % sides (`calc/layout_out.md`) |
| Secondary T1 `meh2_4x4` | 1 in CD + 4 x 4 in (one per wall), 90x60, XO 1-1.5 kHz, HP 160 Hz | compact hi-fi variant; ~5 dB less at 125-150 Hz |
| Geometry route | new CAD tool `tools/cad/meh.py` -> labelled STEP -> existing `step_build` (tags 2 CD, 10 mid ports) | mesher has MEH tag names but no builder |
| Fidelity L1 | ports = flush driven patches; chambers, necks, drivers lumped; one BEM solve per geometry gives per-channel transfers + impedance matrix | decomposition exact for lumped entries (6e-16, `calc/zmatrix_check.md`) |
| Search | outer CMA-ES on 6 geometry knobs (reparameterised box, deterministic repair); inner optimiser on drivers, xo, delay, polarity, front-chamber fill, rear volume | random box was 12-29 % feasible; reparameterised 56-93 % |
| Scoring | objective v5 = v4 pattern terms on the summed system + `lw_resid`, `notch`, `xo_lob`, `headroom`; `flat` off (FIR makes on-axis free) | owner: DSP + FIR on every channel; score what EQ cannot fix |
| Refinement | Boundary Lab coupled FEM-BEM from its `Multi_region_SAWMOD` template | BL v0.5.0 does multi-driver coupled solves |

## Work packages and waves

| WP | Task file | Model | Wave | Depends on | Runs where |
|---|---|---|---|---|---|
| M1 | `M1_DRIVER_DATA.md` | Sonnet (Haiku ok for transcription) | 1 | - | cloud |
| M2 | `M2_SOLVER_FORK_MULTISOURCE.md` | Sonnet | 1 | - | cloud (code + Python tests); Julia/CUDA in M8 |
| M3 | `M3_SOLVE_ADAPTER.md` | Sonnet | 1 | contracts (fakes) | cloud |
| M4 | `M4_NETWORK_SYNTHESIS.md` | Sonnet | 1 | contracts | cloud |
| M5 | `M5_CAD_MESH.md` | Sonnet | 1 | contracts (M1 values optional) | cloud if build123d + gmsh install; else GPU box |
| M6 | `M6_OBJECTIVE_BRIEF.md` | Sonnet | 1 | contracts | cloud |
| M10 | `M10_BASS_BOX.md` | Sonnet (Haiku ok for the datasheet table) | 1 | - | cloud |
| M7 | `M7_PIPELINE_CONFIGS.md` | Sonnet | 2 | M3, M4, M5, M6 merged | cloud |
| M8 | `M8_GPU_VALIDATION_SCREEN.md` | Sonnet + owner | 3 | M2, M7 | owner's GPU box |
| M9 | `M9_BOUNDARY_LAB_EXPORT.md` | Sonnet | 3 | M8 finalists | owner's box (BL in its own env) |

Wave 1 is seven independent agents. File ownership (contracts C13) keeps them out of each other's files; the shared
hot files are split by package (`types.py` M3 only, `config.py` M6 only, `step_build.py` M5 only, `evaluate.py` M7
only).

## Branches and merging

- Each WP works on `meh/<WP>-<slug>` from `main` (M2 works in the fork repo). One PR per WP, draft until green.
- Every push updates `docs/CONTINUITY.md` and `docs/ISSUES.md` (repo rule). Parallel branches will conflict at the
  top of those two files: the integrator keeps **all** entries, newest first, and never drops one.
- Merge order: M1, M6, M4, M5, M3, M10, then M7 (rebased on all of them), then the M8 pin bump.
- An integrator agent (Sonnet) does the merges, re-runs the full offline suite after each, and stops on the first red.

## Running tests (all WPs)

- On the owner's GPU box: `.venv\Scripts\python.exe -m pytest ...` (`TOOLCHAIN.md`).
- In a cloud container: install exactly as `.github/workflows/ci.yml` does, then
  `python -m pytest -m "not slow and not gpu and not crosscheck"`.
- Paste complete, unedited output (no summaries). Never loosen a tolerance, skip a test or widen an assertion.

## Dispatch prompt (the repo's template, filled for MEH; paste verbatim, set the bracket)

```
You are implementing one task in the hornlab-search project (the mini multiple-entry horn effort).

Read these completely, in this order, before writing any code:
  1. docs/meh/00_MEH_CONTRACTS.md
  2. docs/meh/[YOUR TASK FILE]
  3. TOOLCHAIN.md
  4. The "Hard rules for every agent" section of docs/plan/00_ORCHESTRATOR.md, and CLAUDE.md

Your task file lists the exact files you own. Create and edit only those.
Do not edit any file owned by another task. Do not modify any installed
HornLab, Boundary Lab, BEAT or Julia file (the solver fork is changed only by
task M2, on its own branch, per docs/FORKS.md). Do not write a solver, a mesher,
a gmsh writer, or a plotting library: all of those already exist in the
stack and your task file says which function to call instead. Do not invent
a parameter name, config key, tag number, or unit; every one you need is in
00_MEH_CONTRACTS.md.

Work through your task file's Build steps in order. Where the task file or the
contracts give code or equations, use them. The research scripts in
docs/research/typologies/mini_meh_2026-10-29/calc/ are reference implementations:
port their logic, test against them, never import them from package code.

At your checkpoint, run every command listed and paste the complete, unedited
terminal output into your report. Do not summarize it. If a test fails,
report the failure with its full traceback. Do not loosen a tolerance, skip a
test, or widen an assertion to make something pass.

Every push updates docs/CONTINUITY.md and docs/ISSUES.md in the same commit.
Work on the branch meh/[WP]-[slug]; open a draft PR.

Blocked twice on the same error: stop, append a dated block to
NOTES_FOR_SENIOR.md saying what you tried and what the error was, and report.
Do not design an alternative architecture.

Your final report contains, in this order:
  1. Every file you created, with its line count.
  2. The complete output of every checkpoint command.
  3. Anything in your task file you did not finish, and why.
  4. Anything you appended to NOTES_FOR_SENIOR.md.
```

## Known unknowns (each owned by a WP; none blocks wave 1)

| Unknown | Owner | Fallback until resolved |
|---|---|---|
| CD duct depth (diaphragm to exit) for HF1440 / HF108 / DH450 | M1 (drawings) / M8 (measure) | contract defaults 40 / 25 / 25 mm [inferred] |
| Cone frame OD, motor OD, dish depth | M1 | cutout + 12 mm, 0.6 x cutout, 0.2 x cutout [inferred] |
| CD Bl / Mmd / Cms (unpublished by every maker) | not needed at L1 | mass-controlled source + published power / sensitivity (C7, C11) |
| Box depth 380 mm | owner | change `env_d_mm`; layout tool reports feasibility |
| L1 accuracy of flush port patches vs real necks | M8 (L0 vs L1), M9 (BL coupled) | front-chamber filler and neck shape move to L2/L3 for finalists |

## What the orchestrator already verified (do not redo)

Solver engine multi-channel + one factorization (fork source); Python wrapper single-tag (`config.py:462`); mesher
tag names only; BL v0.5.0 coupled multi-driver + SAWMOD template; conical-duct model exact (4e-16); decomposition +
reciprocity (6e-16); layout feasibility and seeds (`calc/layout_out.md`); bass box sizing (`calc/bassbox_sizing.md`).
