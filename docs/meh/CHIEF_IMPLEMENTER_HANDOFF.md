# Chief implementer hand-off: finish the MEH plan on the owner's machine

2026-10-30. For ONE lead agent (Sonnet or better) running in `C:\Users\hunte\Hrns\hornlab-search` on the owner's
GPU box. You coordinate sub-agents for M1-M10 (`docs/meh/README.md`), integrate, test, and run the GPU work yourself.
Read in order: this file, `docs/meh/README.md`, `docs/meh/00_MEH_CONTRACTS.md`, `CLAUDE.md`, `docs/CONTINUITY.md`.

## 0. Pull the work in (owner or you)

```
cd C:\Users\hunte\Hrns\hornlab-search
git status                                   # commit or stash local work first; do not lose it
git fetch origin
git switch -c meh/integration origin/ccr-4978c80b-tvvcgv
git merge origin/main                        # pick up anything newer than the hand-off; keep all CONTINUITY/ISSUES entries
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -q   # baseline must be green before any MEH code
```

Check the research scripts still reproduce (CPU, seconds):

```
cd docs\research\typologies\mini_meh_2026-10-29\calc
..\..\..\..\..\.venv\Scripts\python.exe -I meh_1d_sketch.py        # conical-horn check ~4e-16
..\..\..\..\..\.venv\Scripts\python.exe -I meh_zmatrix_check.py    # decomposition ~6e-16
..\..\..\..\..\.venv\Scripts\python.exe -I meh_layout.py           # must match layout_out.md
```

## 1. Run the waves

| Step | Do | Gate before the next step |
|---|---|---|
| A | Dispatch wave 1 in parallel: M1, M2, M3, M4, M5, M6, M10 (dispatch prompt in README, one branch each) | each WP's checkpoint output pasted, tests green |
| B | Merge in order M1, M6, M4, M5, M3, M10 into `meh/integration`; full offline suite after each | green after every merge |
| C | M2 fork validation on this GPU box (M8 steps 1-2), then pin bump | single-tag parity <= 0.039 dB; owner approves the pin |
| D | Dispatch M7 (pipeline + configs + briefs) | fake-solver end-to-end green |
| E | You run M8 steps 3-6 (real-mesh checks, L0 vs L1, screen, verify) with the `hornlab-gpu-job` skill | evidence doc written with `hornlab-evidence` |
| F | Dispatch M9 (Boundary Lab) on the finalists | per-channel agreement table |

Rules: one GPU job at a time; never start GPU work while a night queue runs (`tools/night_status.py`); every push
updates CONTINUITY + ISSUES; blocked twice -> `NOTES_FOR_SENIOR.md` and stop that line.

## 2. Readiness proof: "can this MEH actually be optimised with our software?"

Before the screen, prove each link once on the T2-A seed, in this order. Each is a pass/fail line in the M8
evidence doc.

1. **Geometry:** `meh` CAD tool builds T2-A, T2-B, T1; tags {1, 2, 10} present; dofs under cap at 12 kHz; quarter
   pairing test passes.
2. **Solve:** one multi-tag solve returns `channel_pressure` (F, 2, P, A) and a symmetric force matrix.
3. **Physics sanity:** with mids passive, the CD response shows the port notch near the 1-D prediction (+-20 %);
   the mid channel's first null sits near `calc/notch_vs_path.md`'s trend for the seed's CD duct.
4. **Network:** inner optimiser returns a NetworkSolution in < 2 s; summed listening window within the boost limit.
5. **Search moves:** a 10-evaluation CMA smoke run changes J and at least 3 geometry knobs, with no infeasible
   repeats (layout repair working).
6. **Re-score for free:** re-score the stored smoke-run records with the alternate mid driver and a different
   `hp_hz` WITHOUT any new solve; J changes and is finite.

If all six pass, the optimiser is real. Run the screen.

## 3. What makes this optimisation interesting (run these after the basic screen)

| Study | How | What it answers |
|---|---|---|
| Port position vs notch trade-off | screen records: plot J terms `notch`, `xo_lob` vs `z_frac` | where the entry sweet spot really is in 3-D (1-D says near the quarter-wave limit) |
| Driver bake-off without new solves | re-score every stored geometry with each cone x CD combination | best driver pair per geometry; whether the winner geometry depends on the driver |
| Front-chamber filler | inner knob `fill` 0-0.7: compare winners with and without | whether a printed cone filler is worth building |
| Bass-box crossover | re-score at `hp_hz` 100 / 120 / 150 | headroom vs localisation trade, no solves |
| Size vs output Pareto | rerun the layout + screen with `env_d_mm` 300 / 380 and face 356 / 406 mm | what the 16 in limit costs in dB and pattern |
| T2 vs T1 | same brief family, both typologies | 2 x 6.5 in vs 4 x 4 in in one table |
| Later: fluted walls (T4) | only if T2 wins cleanly | the Solana lineage |

Report each as a table plus renders (`hornlab-render`), every number labelled measured/inferred.

## 4. Done

PR from `meh/integration` to `main` with: all WP tests green, M8 evidence (readiness six + screen + verify),
the top-2 T2 and T1 designs with their NetworkSolutions, renders, and a build sheet for the winner (drivers, port
sizes, chamber volumes, crossover/delay/EQ, bass box from M10). Owner merges.
