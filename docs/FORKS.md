# Forks of Magnus's packages: how we change the solver or mesher

**Owner decision, 2026-10-24:** we may fork and change Magnus's HornLab packages (`hornlab-beat-bem` including its
Julia code, `hornlab-waveguide-mesher`, `hornlab-plots`, `hornlab-bempp-bem`) whenever it buys us something,
first of all higher-frequency solves on the 8 GB RTX 4060. This supersedes hard rule 1 of the frozen
`docs/plan/00_ORCHESTRATOR.md` as quoted in `CLAUDE.md`, `AGENTS.md` and `CONTRIBUTING.md`. Upstreaming a change to
Magnus stays welcome, but we no longer wait for it.

What did **not** change: we still never hand-edit the *installed copies* under `.venv\Lib\site-packages` (pip would
silently overwrite them and the SHA in every record would lie); and every solver change is validated before its data
counts.

## Where the forks live

| Package | Fork checkout | Base branch (= current pin) |
|---|---|---|
| `hornlab-beat-bem` | `C:\Users\hunte\Hrns\forks\hornlab-beat-bem` | `hornlab-search/base` @ `38544d214ba2e8a4977bb82170d2fb4a3f9fa8b0` |
| `hornlab-waveguide-mesher` | `C:\Users\hunte\Hrns\forks\hornlab-waveguide-mesher` (Mac: `~/Desktop/projects/forks/hornlab-waveguide-mesher`) | `hornlab-search/osse-midports` @ `55da4f46d662d8dcd7a9f94a609eeea4009fcd62` (base `b922e807`; hosted `github.com/jamescollinharky/hornlab-waveguide-mesher`) |

Both were cloned from `github.com/m3gnus/*` on 2026-10-24 and verified byte-identical to the installed packages
(apart from one non-packaged README). Plots and bempp are not forked yet; clone them the same way when needed.

## The workflow (every change, every time)

1. **Branch in the fork** from `hornlab-search/base`: `git checkout -b hornlab-search/<topic>`. Keep each change opt-in
   behind a flag or environment variable that defaults to today's behaviour, so the fork at its default is identical
   to upstream.
2. **Commit in the fork.** Never install uncommitted work for real runs: provenance comes from the commit SHA.
3. **Run the fork's own tests** that cover the change (for Julia: `julia/tests/runtests.jl`, the CUDA testsets on this
   machine; follow the GPU hygiene in `CLAUDE.md`).
4. **Install by commit**, not editable (an editable install has no SHA in `direct_url.json`, so records would
   say `unknown`):
   ```powershell
   .\.venv\Scripts\python.exe -m pip install --no-deps --force-reinstall "git+file:///C:/Users/hunte/Hrns/forks/hornlab-beat-bem@<sha>"
   ```
   Re-provision afterwards if the package asks (`python -m hornlab_beat_bem.provision --backend cuda`); the first
   solve recompiles Julia caches (minutes).
5. **Pin it**: change the dependency line in `pyproject.toml` to the same URL and SHA, and add a line in `TOOLCHAIN.md`
   (SHA, branch, what changed, date). `doctor` and `tests/test_mesh_pin.py` accept any git URL since 2026-10-24.
   - A `file:///C:/...` pin works **only on this machine**. Anything merged to `main` that a collaborator pulls must
     pin a URL they can reach. **Landed 2026-10-25:** the fork is hosted at
     `https://github.com/llevaachingada/hornlab-beat-bem` (owner-authorized 2026-10-25, `gh auth` account
     `llevaachingada`), public, GPL-3.0, and `pyproject.toml` pins it. Pushed topic branches:
     `hornlab-search/fused-cuda` (WP15), `hornlab-search/wp16-source-profile` @ `f4ef05c` (WP16),
     `hornlab-search/wp17-cuda-near` (WP15+16+17 linear; pin `760a1ec`, test-env tip `a40a204`), plus
     `hornlab-search/base` @ `38544d2`. Future pushes are owner-delegated through the same `gh auth`.
6. **Validate before data counts** (solver changes; from a clean GPU state, one job at a time):
   1. `hornlab-search selftest --analytic`: spread ≤ 0.5 dB (reference 0.020 dB).
   2. `hornlab-search selftest --crosscheck` vs `bempp_cpu`: < 0.2 dB (reference 0.039 dB).
   3. A/B against the previous SHA on the same meshes (osse_axi seed, perturbed_osse_hv best, freeform_sculpt seed):
      `hornlab-search compare` within 0.039 dB and ≤ 1° beamwidth.
   4. For memory changes: re-measure the ceiling as in `TOOLCHAIN.md` M2 (VRAM baseline recorded, one solve per fresh
      process).
   Paste the outputs into `docs/evidence/`.
7. **Data separation is automatic**: every record carries `lib_shas`, so old and new solver data never mix silently.
   Keep it that way: never reuse a SHA for different code.
8. **Roll back** by reinstalling the previous pin (`git+https://github.com/m3gnus/hornlab-beat-bem.git@38544d2…`) and
   restoring the `pyproject.toml` line.

## Planned fork changes

| Topic branch | Package | What | Why | Plan |
|---|---|---|---|---|
| `hornlab-search/fused-cuda` | beat-bem (Julia driver) | route CUDA through the existing single-matrix Burton-Miller assembler | ~9k → ~20k quarter dofs on 8 GB; 12 kHz for large horns | `research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md` WP15 |
| later | beat-bem | non-uniform source velocity on the source tag | phase-plug exit above f11 | WP16 |
| later | beat-bem | near-singular correction on CUDA | thin septa (multicell) on the GPU | WP17 |
| `hornlab-search/osse-midports` | mesher | opt-in `mid_ports` L1 flush tag-10 patches on native OSSE(+SF) walls | Ath OSSE+SF with MEH multi-source | Ath OSSE MEH ports plan 2026-11-03 |
| later | mesher | only if a GRID/multicell need is found | — | — |
