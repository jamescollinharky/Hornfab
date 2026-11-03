# M8: GPU validation, pin bump, first screen (owner's GPU box)

Model: Sonnet on the owner's Windows GPU machine (or the owner). Wave 3, after M2 and M7. Skills: `hornlab-gpu-job`
(every job), `hornlab-evidence` (the evidence doc), `hornlab-render` (pictures). Rules: CLAUDE.md GPU hygiene,
`docs/FORKS.md` validation ladder. One GPU job at a time; no pytest solver tests while a night runs.

## Steps (each gated on the previous)

1. **Fork validation:** install the M2 branch SHA into a scratch venv per `docs/FORKS.md`; run the fork's Python
   tests and the Julia testsets (CPU, then CUDA): superposition, reciprocity, single-tag parity, symmetry.
2. **Pin bump:** single-tag parity on two existing finalists (dB difference vs the current pin <= the 0.039 dB noise
   floor) -> bump the pin in `pyproject.toml` / `TOOLCHAIN.md` (the owner approves; owners 03/02 per CLAUDE.md, or
   the orchestrator), full offline suite green.
3. **Real-mesh MEH checks (T2-A seed, 5 frequencies 200 Hz-4 kHz):** force matrix symmetric (rel < 1e-3);
   quarter vs full model Z and per-channel polars agree (rel < 1e-3 / < 0.05 dB); channel 0 equals a CD-only solve of
   the same mesh with the port faces as wall.
4. **L0 vs L1:** the CD notch frequency with passive mids (network on BEM data) within 20 % of the 1-D sketch for the
   same seed geometry (`calc/meh_1d_sketch.py` with the seed's z_c, port z, V_front, port area; n_end = 2 in 1-D,
   1 on BEM data). A larger gap is a finding to investigate, not a tolerance to widen.
5. **Screen:** T2 brief, CMA-ES 40 evaluations from T2-A; T1 brief, 40 from the T1 seed; record inner-optimiser
   time per candidate. Then `verify` (higher fidelity, balloon on, to 16 kHz if the dof cap allows) on the top 2 of
   each.
6. **Evidence:** `docs/evidence/MEH_M8_<date>.md` with real terminal bytes, VRAM baseline + peak pairs, J and every
   term of the winners, their NetworkSolution (drivers, xo, delay, fill, rear volume), spl_max curves, renders.

## Stop conditions

Any check in steps 1-3 fails twice from a clean GPU state -> stop, append to `NOTES_FOR_SENIOR.md`, report.
