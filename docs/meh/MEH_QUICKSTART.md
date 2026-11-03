# MEH quickstart — pick this up with no extra setup

2026-11-01. Everything needed to run the multiple-entry-horn (MEH) search on a GPU box: the pinned stack, the
configs, the launcher, the two verified winners, and the traps that cost this pass time. Read
`docs/evidence/HARDWARE_2026-11-01.md` before buying or renting anything, and `docs/evidence/MEH_M8_2026-10-31.md`
for the measured results behind every number here.

## 1. Install (Windows, one venv)

```powershell
cd <repo>
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m pip install pytest
.venv\Scripts\hornlab-search.exe doctor          # expect every check green
```

`pyproject.toml` pins the four HornLab packages by SHA. The acoustic solver is
`hornlab-beat-bem @ git+https://github.com/llevaachingada/hornlab-beat-bem.git@1efdc6f...` — that is the
multi-tag fork (up to 8 driven tags + an impedance matrix). If `doctor` reports a missing/unpinned solver,
check `TOOLCHAIN.md` before anything else.

## 2. Test before you trust anything

```powershell
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck"
```

That is the CI gate (~1,900 tests, no GPU). GPU/solver tests are marked `slow`/`gpu`/`crosscheck` and are run
deliberately, one job at a time.

## 3. Dry-run first (no GPU, seconds)

```powershell
.venv\Scripts\hornlab-search.exe run --config examples\typologies\meh_2026-10-30\meh_t2a_search.yaml --mode screen --dry-run
```

It prints the mesh size, dof count against the cap, the frequency grid and a cost estimate. If the mesh is
refused (`GeometryInvalidError` naming a face and a frequency), the requested band is above what the mesh resolves —
lower `mesh.epw`, raise `mesh.dof_cap_screen`, or lower `solve.freq_grid.hi_hz`. Never widen a tolerance.

## 4. Run a screen and verify the winners

```powershell
.\tools\meh\run_screen.ps1 -Tag t2 -Config examples\typologies\meh_2026-10-30\meh_t2a_search.yaml -Budget 40
```

The launcher clears stray solver hosts, runs the CMA screen, logs under `runs\nights\`, then re-solves the top 2 at
`verify` fidelity and writes a summary line. Use `-Tag t1` with `meh_t1_search.yaml` for the second brief.
Manual equivalent:

```powershell
.venv\Scripts\hornlab-search.exe gpu-clean
.venv\Scripts\hornlab-search.exe search --config <cfg> --budget 40 --mode screen
.venv\Scripts\hornlab-search.exe verify --run <the run dir it printed> --top 2
```

Measured cost on an RTX 4060 Laptop (8 GB): **52–61 s per 12-frequency candidate**, so 40 evaluations ≈ 35–40 min
per brief, plus verify. The 41-frequency 120 Hz–12 kHz grid is **not runnable on 8 GB** — see §6.

## 5. What is already done (do not redo)

Two 40-evaluation screens were run and their top two verified. The winners are committed as machine-readable
records in [`docs/evidence/meh_2026-11-01/`](../evidence/meh_2026-11-01/README.md) — geometry knobs, objective
terms, the inner-network solution (crossover, delay, polarity, rear volume) and the CAD layout:

| brief | typology | best design | screen J | verify J |
|---|---|---|---|---|
| T2 | 2 × 6.5 in + 1.4 in CD | `ed11d2cd3acc` | 9.530 | 11.894 |
| T1 | 4 × 4 in + 1 in CD | `704051ae928c` | 13.228 | 14.512 |

They are **starting points for the next search**, not finished loudspeakers: the bandwidth's HF end is
mesh-limited, the flatness term dominates (the CD/mid network is not yet delivering a flat system), and the
`notch` term is 0 in both.

## 6. Traps that cost this pass time

1. **8 GB is not enough for the contracted band.** A mesh that resolves 12 kHz on the driven patches needs
   ≥ ~8,600 dofs; the 41-frequency sweep peaks at 7.9 of 8.19 GB and dies (CUDA 719, twice). The fused CUDA path
   refuses more than one channel, so it cannot rescue a multi-driver solve. Options are in the hardware audit.
2. **Frequency grids are not comparable.** The screens above used the frozen 12-point 500 Hz–10 kHz grid; a
   120 Hz–12 kHz run is a different grid group. Never rank across them.
3. **Stale solver hosts lie.** A persistent Julia host from another experiment can be adopted and produce a
   misleading error (this pass saw a "fused, one channel only" error from a leftover host). `gpu-clean` before any
   job, and check `nvidia-smi` is near idle.
4. **Line endings**: this repo is LF. Editing on Windows with an editor that writes CRLF turns whole files into
   merge conflicts and breaks the byte-identical param-catalog test on Linux CI.
5. **`fill` is not carried in the record** for these winners (None); the front-chamber filler stays a search knob.
6. The MEH CAD tool emits a **quarter** open shell only; a full model is refused. Do not "fix" that by widening
   `quadrants`.

## 7. Where things live

| what | where |
|---|---|
| typology configs (searchable) | `examples/typologies/meh_2026-10-30/meh_t{2a,1}_search.yaml` |
| CAD-authored seeds | same folder, `meh_t{2a,2b,1}.yaml` |
| briefs (band, XO range, SPL target, `meh:` block) | `examples/briefs/meh_2026-10-30/` |
| drivers (T1/T2 mids + CDs, bass-box woofers) | `examples/drivers/` |
| CAD + mesh route | `tools/cad/meh.py`, `hornlab_search/mesh/step_build.py` |
| network / DSP / limits / inner optimiser | `hornlab_search/meh/` |
| objective v5 + brief block | `hornlab_search/objective/scalar_meh.py`, `hornlab_search/config.py` |
| verified winners (JSON) | `docs/evidence/meh_2026-11-01/` |
| measured M8 results and readiness proof | `docs/evidence/MEH_M8_2026-10-31.md` |
| hardware decision and benchmark plan | `docs/evidence/HARDWARE_2026-11-01.md`, `docs/meh/HARDWARE_HANDOFF_2026-11-01.md` |
