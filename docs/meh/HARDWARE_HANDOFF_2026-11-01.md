# Hand-off: compute and hardware for the MEH optimisation campaign

2026-11-01. For the next agent (or owner) whose job is to work out **what hardware to run this on**, how to
configure it, and how to buy or rent it without guessing. This document is the whole context needed: how the
solver works, what is currently fast or slow (all measured on the owner's box), what the real bottlenecks are,
and the experiments that turn "which GPU" into a number.

Read next, in this order: `TOOLCHAIN.md` (pinned SHAs, machine numbers), `docs/evidence/MEH_M8_2026-10-31.md`
(this campaign's measured results), `docs/FORKS.md` (solver fork rules), `docs/meh/00_MEH_CONTRACTS.md` (C4 is
the solver contract). Raw data for the numbers below lives under `runs/meh_m8/` (local, gitignored).

## 1. How the solver actually works

`hornlab-search` is a search layer; it does not contain a BEM solver. One candidate evaluation is:

1. **Geometry (CPU, build123d).** A labelled STEP: `wall` (tag 1), `driver` (tag 2), `entry_mid` (tag 10).
   The MEH tool emits a QUARTER open shell (x >= 0, y >= 0); the symmetry planes are not BEM faces.
2. **Mesh (CPU, gmsh, single process).** Sized from the band's top frequency `f_max` at `epw` elements per
   wavelength. Measured: 2.2-2.6 s, 11.8k-17k triangles, 6.0k-8.6k quarter dofs. The mesher hard-fails when a
   driven face cannot resolve `f_max` (that gate, not the user, sets the mesh floor).
3. **BEM solve (GPU, Julia host).** `hornlab_beat_bem` wraps a Julia engine. Per **frequency**, it assembles the
   Burton-Miller boundary operators and solves the exterior Neumann problem; with C source tags it does C
   unit-drive Neumann solves per frequency and returns per-channel pressure, the C x C impedance matrix and the
   tag areas. Per **frequency per position**, the field is evaluated at the observation cuts (73 angles) and the
   balloon (512 directions at screen fidelity). Nothing is shared between frequencies except the mesh and
   geometry.
4. **Inner network optimiser (CPU).** For one solved geometry it re-scores a lumped CD + mid-port network
   (crossover, delay, polarity, fill, rear volume) with CMA-ES. Measured **6.58 s** for 1,224 candidate networks
   on the shipped T2 brief. It is pure numpy and needs no GPU.
5. **Objective + record (CPU, negligible).** Metrics on the synthesised response, objective v5, one ndjson row
   plus arrays in the dataset.

The outer loop is **CMA-ES over 6 geometry knobs**, evaluated **one candidate at a time**; the app takes a GPU
lock so only one solve runs machine-wide. `search/evaluate.py` is written as a pure function per candidate,
which is what makes candidate-level parallelism possible later (see s4).

Worker lifecycle matters for memory: the Julia host is **persistent** (`HORNLAB_BEAT_PERSISTENT_HOST=1`), one
host per package fingerprint, holding CUDA context + a growing memory pool. `hornlab-search gpu-clean` kills
stray hosts. A stale host from a different experiment can be adopted and produce misleading errors (it did,
see ISSUES).

## 2. What is measured today (owner's box: RTX 4060 Laptop, 8 GB, ~256 GB/s, Windows)

| job | frequencies | dofs | wall time | VRAM peak |
|---|---|---|---|---|
| T2 screen candidate (500-10k grid) | 12 | 6,032 | **52.0 s** (mesh 2.18 + solve 43.2) | ~7.87 GB |
| T1 screen candidate (500-10k grid) | 12 | 6,009 | **60.9 s** (mesh 2.60 + solve 51.9) | ~7.92 GB |
| 5-frequency multi-tag solve, 12 kHz mesh | 5 | 8,625 | 360 s incl. cold start (~36-45 s/freq) | ~7.9 GB |
| dense multi-tag sweep, 12 kHz mesh | 10 | 8,625 | 680 s (~45-68 s/freq) | ~7.9 GB |
| contracted-band sweep (120-12k, 1/6 oct) | 41 | 8,625 | 1,851 s then **CUDA 719** | **7,908 / 8,188 MiB** |
| 10-frequency multi-tag sweep, cold host | 10 | 8,625 | 680 s | ~7.9 GB |
| inner network optimiser only | - | - | 6.58 s (1,224 evaluations) | 0 |

Derived per-frequency rates (cold-start amortisation is why the short runs look slower):

| mesh | elements | dofs | s/frequency (warm-ish) |
|---|---|---|---|
| 10 kHz screen | 11,776 | 6,032 | ~3.6 |
| 12 kHz | 16,909 | 8,625 | ~40-53 |

That is a **~12x cost increase for a 1.44x element increase**. Do not assume a clean exponent: it is
consistent with assembly scaling with elements squared PLUS a change of solver path (dense factorisation
memory/time) between those sizes. Separating those two terms is the first measurement in s4.1, and it is
the single most consequential number for hardware choice.

Two facts dominate everything else:

- **Observed device use sits at ~7.9 GB near the ceiling on short sweeps and long ones alike.** The original
  reading of this - "a flat per-frequency workspace, independent of dof count" - is WITHDRAWN (s2a): that is
  total device use with CUDA.jl caching, not live working set. What is established is narrower: this card is
  within ~300 MiB of its ceiling whenever it solves a 12 kHz MEH mesh, so a long sweep is many draws against a
  thin margin, and it failed twice.
- **Wall time scales with frequencies and elements, and the mesh floor is set by the top frequency.** Going from
  the 10 kHz screen grid (11.8k elements) to the 12 kHz grid (16.9k elements) roughly tripled solve time per
  frequency; element-level assembly is O(E^2) and the operator inversion adds its own super-linear term.

### 2a. CORRECTIONS (2026-11-01, after the audit in `docs/evidence/HARDWARE_2026-11-01.md`)

The audit is right and this section is kept only as the record of what was believed when it was written.
Five claims above were wrong or unsupported:

- **Mesh attribution.** The screen winners' own stored responses report **5,872 (T2) and 6,249 (T1) dofs**
  (`response.npz` -> `n_dof`). The 6,032 / 6,009 figures are the SEED meshes, which CMA did not select. The
  wall times were measured correctly but paired with the wrong mesh.
- **The "~12x for 1.44x elements" scaling claim is withdrawn.** It divided a FAILED 41-frequency sweep
  (1,851.7 s, CUDA 719) by 41 and mixed in cold-start guesses. There is no valid seconds/frequency observation
  at 8.6k dofs. The only solid stage data is at 5.9-6.2k dofs, from the winners' `meta.timings`:
  **assembly 23.72 s, solve 2.38 s, field 0.19 s, total 35.54 s over 12 frequencies** (1.98 / 0.199 / 0.016 /
  2.96 per frequency). Assembly is ~67 % of engine time at that size; field evaluation is negligible.
- **"VRAM is a flat ~7.9 GB workspace" is withdrawn.** `nvidia-smi` reports total device use and CUDA.jl caches
  freed allocations, so a flat trace does not prove a flat live working set. Worse, the CSV that backed the
  quote was overwritten by a later poller run: the file now holds 558 samples starting at 5,643 MiB with no
  idle baseline (peak 7,897). The 880-sample trace no longer exists on disk. CUDA error 719 is a launch
  failure, not the allocation-OOM code, so memory pressure is a hypothesis, not a diagnosis.
- **Whole-wall 12 kHz sizing.** The audit's diagnostic meshes put the first globally valid T2 mesh at
  **33,959 dofs / 67,245 triangles** (nominal epw 8.4), and source-derived static storage for the pinned CUDA
  path at **~85 GiB before any workspace**. A 24/32/48/80 GB card cannot run that mesh on that path; the
  141 GB H200 is the first listed tier worth testing. The "25-35k elements" guess in s4.5 is wrong.
- **Lanes are not a one-line change.** The audit names five concrete surfaces (CMA generation barrier,
  evaluator side effects, cache publication, GPU-lock ownership, worker-host tracking). The cheap honest route
  is two isolated rentals, one brief each. Also: 64 GB system RAM is not established as sufficient for the
  full-wall mesh; size it from measured host RSS.

What survives unchanged: the pipeline description, the stage attribution at screen size, the fused-path
single-channel refusal, the four measured 12-frequency screen numbers, the 6.58 s inner optimiser, and the
conclusion that capacity and throughput are separate problems.

## 3. The two bottlenecks, stated separately

**B1 - capacity (blocks the contracted band).** The 120 Hz-12 kHz 1/6-octave grid (41 frequencies) needs a mesh
that resolves 12 kHz on the driven patches: >= ~8,600 dofs, which peaks at 7.9 of 8.19 GB. It dies mid-sweep
(measured twice). Shrinking the mesh hits the 12 kHz patch gate (epw 4.0 resolves only 11.93 kHz), and the
smallest legal mesh (8,044 dofs) leaves the optimiser's own neighbours at 8,296-8,485 dofs - over any cap that
keeps VRAM safe. The fused CUDA path, the documented high-dof route, **refuses more than one channel**, so it is
not an option for a MEH solve at any dof count.

**B2 - throughput (the bigger cost, even once B1 is solved).** One 41-frequency candidate is roughly
30-45 min on this box (45 s/freq measured, 41 frequencies), so a 40-evaluation screen is on the order of
**20-30 h per brief**, and the campaign wants two briefs plus verify. Extra VRAM fixes B1 but does **not** fix
B2: the same card with 24 GB would still take the same wall time per frequency. B2 needs faster per-frequency
work and/or many candidates in flight at once.

Secondary, measured, not currently binding: the inner network optimiser (6.6 s CPU per geometry) is 3.3x its
own 2 s budget but is ~2 % of a candidate; gmsh is 2-3 s; dataset I/O is negligible.

## 4. How to find the right hardware (the actual assignment)

Do not pick a card by marketing numbers. Do this:

1. **Fit the scaling law first (CPU + one rented GPU, a few hours).** On a fixed geometry, measure
   `seconds_per_frequency` and `peak_VRAM` for element counts ~6k, 12k, 17k, 25k, 35k (vary `f_max`/`epw`
   through the legally accepted range) and for channel counts 1, 2, 4. Separate three cost terms: assembly
   (expect ~E^2), operator solve (expect N^2 memory, N^3-ish time until the engine switches to an iterative
   path), and field evaluation (expect ~freqs x (cuts + balloon)). The engine has an adaptive dense solve and a
   GMRES Burton-Miller path; find out **which path a MEH mesh takes** and where the switch is - that single fact
   changes the hardware ranking.
2. **Measure bandwidth sensitivity, not just capacity.** Run the same benchmark on one memory-bandwidth tier and
   one compute tier (e.g. RTX 4090 24 GB/1 TB/s vs A100 80 GB/2 TB/s vs H100 80 GB/3.3 TB/s). If s/freq tracks
   bandwidth, buy bandwidth; if it tracks FP32 and the matrix is compute-bound, buy compute. Report the ratio.
3. **Measure candidate-level throughput, not one solve.** The product number that matters is
   **candidates per hour per dollar** at the fidelity the campaign needs (41 frequencies, 2 channels,
   >= 8.6k dofs). Build a one-page table per candidate machine.
4. **Test concurrency explicitly.** The pipeline is serial per candidate today. Two routes:
   (a) one GPU, several solves queued - no help for wall time; (b) **several GPUs, one candidate each**, which
   needs a small, contained change: evaluate a CMA generation's candidates in parallel, one worker host and one
   GPU per lane, and keep the existing GPU lock per device. Measure 1, 2, 4, 8 lanes on rented hardware; this is
   the only lever that scales B2 without a solver rewrite. `search/evaluate.py` was left a pure function for
   exactly this.
5. **Size for the mesh you actually need.** The contract asks 120 Hz-12 kHz at 1/6 octave; the current mesh floor
   is set by the 12 kHz driven-patch gate (~8.6k dofs at epw 4.2). Confirm the element count needed for a
   defensible 12 kHz mesh (rigid walls at 6 elements/wavelength, not just the source patches) - today the walls
   resolve only to ~6 kHz at the dof cap, which is a physics caveat independent of hardware. If a defensible
   12 kHz mesh is 25-35k elements, the capacity target is much higher than "just enough to stop the OOM".

## 5. Hardware axes worth pricing (2026-11)

| axis | why it matters here | what to check |
|---|---|---|
| VRAM | B1 is capacity. Observed device use is ~7.9 GB at 6-8.6k dofs (not a live working-set figure, see s2a), so 24 GB is the smallest tier with plausible headroom; whole-wall 12 kHz needs the 141 GB tier | live-vs-reserved memory per frequency at 17k and 35k dofs |
| memory bandwidth | assembly and field evaluation stream large arrays; likely the dominant scalar for s/freq | measure s/freq vs BW across tiers |
| FP32 throughput | the engine runs Float32 on CUDA; do not pay for FP64 | s/freq vs TFLOPS at matched BW |
| CPU cores | gmsh per candidate, the inner optimiser, and N parallel lanes each need a core set | 16-32 cores for 4-8 lanes |
| system RAM | records/arrays are small; mesh + dataset per lane is < 1 GB | 64 GB is plenty |
| multi-GPU chassis | the throughput answer is lanes, not one big card | PCIe lanes/power for 4 GPUs |
| vendor/backend | CUDA is the validated path; ROCm exists in the engine but is untested here | do not buy AMD before testing |
| OS | everything measured is Windows + PowerShell 5.1 + a venv | Linux is untested for this stack |

Candidate classes to price (not to buy yet): RTX 4090 24 GB / 5090 32 GB (cheap bandwidth), RTX 6000 Ada or
L40S 48 GB (capacity + ECC, blower), A100 80 GB / H100 80 GB (bandwidth, rented), H200 141 GB (only if the
scaling fit says memory is the wall). Rent first: Lambda, RunPod, Vast, Paperspace, or a cloud A100/H100;
compare $/candidate-hour at the campaign's fidelity, not $/hour.

### 5b. Unified and coherent-memory configurations (evaluate explicitly)

Unified memory looks attractive here because the observed device use sits near the card's ceiling at the
sizes we run. Be precise about what that means: it is a device-use trace, not a measured live working set
(the audit in `docs/evidence/HARDWARE_2026-11-01.md` is right about this, and s2a records the correction).
What the source does establish is that the pinned CUDA path holds several N x N and N x E complex64
operators plus identity caches per frequency, so the working set grows with N and E and reaches ~85 GiB at
the first globally valid whole-wall 12 kHz mesh. Spilling that over a PCIe-class link is the failure mode
to test for; BEM assembly and the operator solve are bandwidth-bound, not capacity-bound. Spilling that working set over a PCIe-class link (~32-64 GB/s) instead of
GPU memory (~256-3,300 GB/s) does not make a solve slower by a little, it makes it 5-50x slower.

So the test for any unified machine is not capacity, it is **bandwidth through the spill path**. Evaluate:

| configuration | unified memory | practical bandwidth | what it would prove |
|---|---|---|---|
| NVIDIA GH200 / GB200 (Grace + Hopper/Blackwell, NVLink-C2C) | up to 480-960 GB | ~900 GB/s C2C, HBM3e 3-8 TB/s | the only unified option on the already-validated CUDA path; could hold 20-35k element meshes and very large sweeps |
| Apple Silicon M3/M4 Max/Ultra (Metal backend exists in the engine) | 36-192 GB shared | ~270-800 GB/s | capacity is a non-issue and the working set fits; the question is whether the Metal path is complete and correct for MULTI-CHANNEL BEM, and whether Apple's GPU keeps up on assembly. Our stack has never run on macOS: venv, gmsh wheels and the Julia host all need a port check before any benchmark |
| AMD MI300A (APU, 128 GB HBM3 unified) | 128 GB | ~5 TB/s HBM | attractive on paper; the engine has a ROCm path that this project has never exercised (TOOLCHAIN reports rocm 'no-hardware'). Only worth testing if a ROCm box can be rented cheaply, and it must be validated against the CUDA answers first |
| Strix Halo class APU (128 GB LPDDR5X) | 128 GB | ~256 GB/s | capacity without bandwidth: expect it to be slower than a discrete card that simply fits. Useful as the negative control for the "unified memory helps" hypothesis |
| CPU-only / out-of-core | system RAM | ~50-100 GB/s | the engine has a CPU backend; it is a correctness reference, not a campaign machine. Measure once so the comparison is honest |

For each, the benchmark is the same as s4: the 41-frequency, 2-channel, >=8.6k dof job, reported as
seconds/frequency, peak memory (and whether it spilled), candidates/hour and $/candidate. Add one extra
column: **does it complete the contracted band at all**, because on the 8 GB card the answer today is no.

Portability caveat to state in the deliverable: the pinned solver fork `1efdc6f` is validated on CUDA only.
Metal and ROCm paths exist in the engine but are unvalidated for multi-channel work here, so any non-CUDA
recommendation carries a validation task (single-tag parity <= 0.039 dB against the CUDA answers, plus the
four multi-tag properties from the M2 testset) before it can be trusted for a campaign.

## 6. Deliverable for this hand-off

A short decision document, `docs/evidence/HARDWARE_2026-11-<date>.md`, containing:

1. The measured scaling law: s/freq and peak VRAM as functions of elements, dofs, channels and frequencies, with
   the engine path named (dense vs GMRES) for each size.
2. A table: machine, VRAM, BW, cores, s/freq at 41 freqs / 2 channels / >= 8.6k dofs, peak VRAM, candidates/hour,
   $/hour, $/candidate.
3. A lane-scaling table (1, 2, 4, 8 concurrent candidates) and the exact code change it needs.
4. A recommendation: the smallest configuration that runs the contracted band, and the cheapest configuration
   that makes a two-brief screen finish inside one night. These are different machines and the owner should see
   both numbers.
5. Anything that changes the MEH plan itself (e.g. if a defensible 12 kHz mesh needs 35k elements, say so).

## 7. Rules that still bind

- Never modify an installed HornLab/BEAT package; solver changes go through the pinned fork per `docs/FORKS.md`.
  The fork is `github.com/llevaachingada/hornlab-beat-bem`, branch `hornlab-search/meh-multisource` at
  `1efdc6f` (the current pin, owner-approved, validated to 1.1e-5 / 5.9e-5 dB single-tag parity).
- One GPU job at a time on a shared box; `hornlab-search gpu-clean` before and after; record VRAM baseline next
  to every peak (CLAUDE.md GPU hygiene, rules 1-7).
- Every push updates `docs/CONTINUITY.md` and `docs/ISSUES.md`; evidence numbers come from decoded log bytes
  (`hornlab-evidence`), never from memory.
- Do not rank results across different frequency grids or fidelity modes; the 500-10k screens and any 120-12k
  run are different grid groups.
- Owner decisions already taken: system = MEH top + separate bass box; 380 mm depth stands; solver pin bumped;
  contracted band = 120 Hz-12 kHz.
