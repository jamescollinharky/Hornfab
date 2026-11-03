# CLAUDE.md — hornlab-search

## Start here

0. **Find anything:** `docs/INDEX.md` (every doc, what it is) and `docs/CODE_MAP.md` (every module and config
   folder). Keep both current: a new doc or module gets a line there in the same commit.
1. **Read `docs/CONTINUITY.md` first.** It says which wave we are in, the last checkpoint passed,
   what is next, open blockers, and the measured numbers.
2. Read `docs/plan/01_CONTRACTS.md` completely (frozen), then **only your own task file**.
3. Read `TOOLCHAIN.md` for interpreter paths, pinned SHAs, and measured machine numbers.
4. Read `CONTRIBUTING.md` for branch / commit / PR rules and the 8 hard rules.

## RULE FOR EVERY PUSH, forever

**Every commit that is pushed updates `docs/CONTINUITY.md` and `docs/ISSUES.md` in that same commit.**
CONTINUITY gets a new dated entry at the top (newest first) and its status block refreshed;
ISSUES mirrors the open GitHub issues (ID, title, status, owner, plan reference). A push that
does not touch both is wrong.

## What this is

`hornlab-search` finds horn-loudspeaker geometry **by objective**: state a target (coverage, band,
ripple, throat size, a room), generate candidate geometry, solve each with GPU boundary-element
acoustics, score it, iterate (CMA-ES). It is a **search layer over Collin's HornLab packages**:
`hornlab_mesher` (geometry + gmsh), `hornlab_beat_bem` (GPU BEM), `hornlab_bempp_bem` (CPU BEM
cross-check), `hornlab_plots` (figures). We never write a solver, mesher, gmsh writer, Green's
function or plotting library from scratch, and never hand-edit the *installed* copies in `.venv`.
**Owner amendment 2026-10-24:** changing Magnus's packages (Python or Julia) IS allowed through our
pinned forks in `C:\Users\hunte\Hrns\forks\` — branch, commit, install by SHA, pin, validate — exactly
as `docs/FORKS.md` says. This supersedes hard rule 1 wherever it is quoted (AGENTS.md, CONTRIBUTING.md,
the frozen plan).
License: AGPL-3.0-or-later. Every horn number is a YAML default in `examples/`, never hardcoded.

Interpreter: always `.venv\Scripts\python.exe` (absolute path in `TOOLCHAIN.md`), never bare `python`.

## Wave plan

```
WAVE 0   02 env  ->  03 scaffold                               serial, one agent      (CP-0, CP-1)
WAVE 1   04 design+mesh | 05 solve | 06 metrics | 07 dataset    four agents, parallel  (CP-2..CP-5)
WAVE 2   08 pipeline                                            one agent              (CP-6, CP-7)
WAVE 3   09 checkpoints                                         senior, verify only
```

A wave starts only after the previous wave's checkpoints pass. Parallelism = writing code in
parallel. **One GPU, one solve at a time.** Dispatch prompts: verbatim template in
`docs/plan/00_ORCHESTRATOR.md`.

## File ownership

Create and edit **only** your own paths. Read anything.

| Path | Owner |
|---|---|
| `TOOLCHAIN.md` | 02 |
| `pyproject.toml`, `.gitignore`, `README.md` | 03 |
| `hornlab_search/__init__.py`, `types.py`, `constants.py`, `config.py` | 03 |
| `hornlab_search/cli.py` | 03 until Wave 2, then 08 |
| `tests/conftest.py`, `tests/test_config.py` | 03 |
| `examples/*.yaml` | 03 creates; 04 may add family examples |
| `hornlab_search/design/**`, `mesh/**` | 04 |
| `hornlab_search/solve/**` | 05 |
| `hornlab_search/metrics/**`, `targets/**` | 06 |
| `hornlab_search/dataset/**` | 07 |
| `hornlab_search/surrogate/**`, `tests/test_surrogate_*.py` | phase 2 (orchestrator) |
| `hornlab_search/objective/**`, `search/**`, `report/**` | 08 |
| `tests/test_design_*.py`, `test_mesh_*.py` | 04 |
| `tests/test_solve_*.py` | 05 |
| `tests/test_metrics_*.py`, `test_targets_*.py` | 06 |
| `tests/test_dataset_*.py` | 07 |
| `tests/test_objective_*.py`, `test_search_*.py`, `test_report_*.py`, `test_end_to_end.py` | 08 |
| `NOTES_FOR_SENIOR.md` | everyone, **append only** |
| `docs/CONTINUITY.md`, `docs/ISSUES.md` | everyone, on every push |
| `docs/plan/**` | frozen; nobody edits |
| `CLAUDE.md`, `CONTRIBUTING.md`, `.github/**` | orchestrator |

**MEH effort (owner, 2026-10-30):** tasks M1-M10 own the paths in `docs/meh/00_MEH_CONTRACTS.md` C13 (additive to the
table above); `docs/meh/**` is orchestrator-owned and frozen for the effort.

Need a file you do not own? Do not edit it. Append the exact change to `NOTES_FOR_SENIOR.md`.

## The three silent killers

- **`mesh_scale`**: the mesher writes **metres** → `SolveConfig(mesh_scale=1.0)`. The beat README's
  `0.001` is for its mm example mesh. `mesh/build.py` asserts bbox is 0.1–1 m.
- **Quadrants vs symmetry flag** must derive from one source and be tested together.
- **DI provenance**: `MetricSet.di_source` is `"balloon"` or `"cuts_estimate"`; no checkpoint passes on
`cuts_estimate`.

## Research grounding (before typology/shape work)

Work that ADDS or CHANGES a typology, generator, grid/point-grid shape law, mounting model, multicell/septa
geometry, brief-for-a-new-typology, or an objective/directivity term that encodes a NEW acoustic priority runs
the `hornlab-typology-research` skill (project) FIRST: outside research on the typology itself — primary
sources in a source table, corrected claims, a validatable construction, experiential reports — before code;
if the senior-pass research already covers it, cite it and proceed. Lane roles that cannot load skills apply
this paragraph plus the WP9b 9b.0 standard (docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md).
The R9 gate binds: nothing ships under a published name without a verifiable published reference. Routine
config/GPU/evidence work skips it (see also hornlab-gpu-job, hornlab-evidence).

## Tests

`pytest` offline tests run in CI (Python 3.12). Tests that need a real solver/GPU/mesher run are
marked (see `tests/conftest.py`) and deselected in CI; they are run locally and pasted into PRs.

## GPU / Julia hygiene (measured 2026-10-12; applies to every agent)

`hornlab_beat_bem` runs solves in a **persistent Julia host** (`HORNLAB_BEAT_PERSISTENT_HOST=1`, idle
timeout 1800 s). Each host holds ~1 GB of VRAM (CUDA context) plus its memory pool. Measured on the
8 GB RTX 4060: `shutdown_workers()` does **not** reliably end the host, so hosts from earlier
processes pile up, and a later solve then crashes with `Warm BEAT Engine solver exited with code
1 / 4294967295`, or OOMs at a dof count that fits fine alone. Several "OOM" numbers were this, not
the real ceiling.

Rules:
1. **Before any GPU measurement, benchmark, or checkpoint run**, list and clear stale hosts, and confirm
   VRAM is near idle (the desktop alone uses ~0.3-0.5 GB):
   `Get-Process julia` then `taskkill /F /IM julia.exe`, then `nvidia-smi --query-gpu=memory.used --format=csv`.
   Only Julia processes this project started may be killed. On a shared machine, check the
   command line first.
2. **One measurement per fresh process, with Julia cleared between jobs.** Never compare VRAM or
   timings across solves of different meshes inside one warm worker (the pool keeps growing).
3. **Record the baseline** (`memory.used` before the solve) next to every peak-VRAM number.
4. **Never run two GPU jobs at once**, and don't run provisioning while measuring.
5. **Poll `nvidia-smi` from a separate process or thread.** A Python-side poll that reads 0 is a bug in
   the probe, not a result.
6. Every run script ends by clearing its workers. Task 05 (`solve/worker.py`) must verify the host
   really exits (check the process list) and test it. `detach_workers()` leaving a host warm is
   intended inside a search; it is not acceptable at the end of a measurement or checkpoint.
7. A solver crash or OOM is only a finding once it reproduces from a clean state (rule 1).
