# TOOLCHAIN

Recorded by task 02 on 2026-10-12. **Status: PARTIAL — M2/M3/M4 and M5-after-detach are UNRESOLVED** because a second, concurrent agent session was running BEM solves on the same single GPU during this session (see *Anything surprising*). A clean, exclusive-GPU re-run is required to finish CP-0. `UNRESOLVED` is recorded rather than an invented number (hard rule 3).

## Machine
- OS: Microsoft Windows 11 Pro 10.0.26200, build 26200
- CPU: Intel(R) Core(TM) i7-14650HX, 16 cores / 24 threads
- RAM: 31.7 GB
- GPU: NVIDIA GeForce RTX 4060 Laptop, 8 GB (8188 MiB) **— DEVIATION: the plan names an RTX 4070 Laptop 8 GB; this machine is the 4060. Same VRAM, so the dof caps are unchanged, but expect slower s/candidate.**
- NVIDIA driver: 610.62; CUDA UMD version 13.3

## Interpreters
- Python: `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe` 3.12.10
- Julia: `C:\Users\hunte\AppData\Local\Microsoft\WindowsApps\julia.EXE` (shim → juliaup 1.12.7+0)
- venv: `C:\Users\hunte\Hrns\hornlab-search\.venv`
- System Python also present: `C:\Users\hunte\AppData\Local\Programs\Python\Python312\python.exe` (used internally by the beat worker host)

## Pinned dependencies (40-char SHAs)
- hornlab-waveguide-mesher: `55da4f46d662d8dcd7a9f94a609eeea4009fcd62` (fork `jamescollinharky/hornlab-waveguide-mesher` branch `hornlab-search/osse-midports`; base `b922e807`; opt-in `mid_ports` L1 flush tag-10 patches on native OSSE(+SF) walls; absent = byte-identical. 2026-11-03)
- hornlab-beat-bem:           `1efdc6f934e16f288880b6d68e8dce8480b7a421`
- hornlab-plots:              `9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44`
- hornlab-bempp-bem:          `8e6910602ece9abb2e9ce0db7a637f4bedf17f53` (installed OK, with bempp-cl 0.4.2 and numba 0.68.0)

Pin history:
- 2026-10-31: beat-bem pin → `1efdc6f` (branch `hornlab-search/meh-multisource`, cut from 760a1ec): opt-in multi-tag
  `velocity_sources` (1..8, unit amplitude), opt-in `impedance_matrix`, `channel_*` result fields, `tag_areas_m2`;
  one tag with no matrix is byte-identical (golden payload). Validated in M8: fork Python suite 329 pass; Julia
  superposition/reciprocity/single-tag-parity/symmetry pass on CPU and CUDA; single-tag SPL parity vs 760a1ec
  1.12e-5 dB / 5.91e-5 dB on two finalists (floor 0.039 dB). Owner approved the bump. Pushed to
  `https://github.com/llevaachingada/hornlab-beat-bem`.
- 2026-10-25: beat-bem pin → levaachingada fork @ 760a1ec (WP15 fused + WP16 source plug + WP17 fused-CUDA near correction, stage 1); fork hosted public GPL-3.0; WP16/17 branches hornlab-search/wp16-source-profile@f4ef05c / wp17-cuda-near@760a1ec — branch tip a40a204 only registers CUDA@6.2.0 in `hornlab_beat_bem/julia/Project.toml` (+ Manifest) so the WP16/17 CUDA-gated Julia testsets run on this GPU; the pinned install SHA is unchanged.

## Backends
- `beat_engine_status()`: `{'available': True, 'reason': 'NVIDIA GPU detected and Julia CUDA.functional() confirmed a usable device', 'state': 'ready', 'version': '0.2.0', 'backend': 'cuda'}`
- `beat_backend_statuses()`: cuda `ready`; **cpu `unprovisioned`**; rocm/metal `no-hardware`.
- Working default: `cuda` — because the CUDA runtime is provisioned and `CUDA.functional()` is true.
- bempp available: **yes** (bempp-cl 0.4.2; numba fallback present).

## Response object schema
The installed hornlab-beat-bem 0.2.0 returns a **`SolveResult`**, NOT the plan's `Response`. Full `dir(r)` at 1000 Hz, `ObservationConfig(distance_m=2.0, angle_count=37)` (37 angles, 0..180°, planes horizontal+vertical):
```
cancelled: bool = False
config: SolveConfig
directivity_db: ndarray dtype=float64 shape=(1, 2, 37)          # property
directivity_reference_deg: float = 0.0                          # property
directivity_reference_index: int = 0                            # property
frequencies_hz: ndarray dtype=float64 shape=(1,)
impedance: ndarray dtype=complex128 shape=(1,)
is_partial: bool = False                                        # property
mesh_info: MeshInfo(n_vertices=1419, n_triangles=2834, physical_tag_areas_m2={1: ..., 2: ...})
observation_angles_deg: ndarray dtype=float64 shape=(37,)
observation_planes: list = ['horizontal', 'vertical']
pressure_complex: ndarray dtype=complex128 shape=(1, 2, 37)
requested_frequency_count: int = 1
solver_log: list
sphere_phi_deg: None            # populated only when ObservationConfig.sphere_grid is set
sphere_pressure_complex: None
sphere_theta_deg: None
spl_db: ndarray dtype=float64 shape=(1, 2, 37)
spl_norm_db: ndarray dtype=float64 shape=(1, 2, 37)             # property alias of directivity_db
surface_neumann_complex: None   # populated only when SolveConfig.surface_traces=True
surface_pressure_complex: None  # populated only when SolveConfig.surface_traces=True
timings: dict = {'assembly_s': 12.17, 'solve_s': 3.54, 'field_s': 1.35, 'total_s': 24.50}
```
**No `p1_dof_count`, no `native_diagnostics`, no `metal_pipeline`** (those were plan guesses). `p1_dof_count == mesh_info.n_vertices` (P1 ⇒ one dof per vertex; verified 1419 == 1419).
Complex pressure exposed: **yes, as `pressure_complex` (F, P, N).**

## M1 dof calibration
Meshed `osse-freestanding` (OSSE, freestanding, wall_thickness 6 mm) with `max_triangles=200000`.

| quadrants | mouth_res_mm | throat_res_mm | triangles | p1_dof (vertices) | dof/tri |
|---|---|---|---|---|---|
| 1234 | 12 | 6 | 5524 | 2764 | 0.5004 |
| 1234 | 8 | 4 | 10988 | 5496 | 0.5002 |
| 1234 | 6 | 3 | 18382 | 9193 | 0.5001 |
| 1234 | 4 | 2 | 40382 | 20193 | 0.5000 |
| 1234 | 3 | 1.5 | 70460 | 35232 | 0.5000 |
| 1 | 12 | 6 | 1384 | 741 | 0.5354 |
| 1 | 8 | 4 | 2752 | 1438 | 0.5225 |
| 1 | 6 | 3 | 4586 | 2369 | 0.5166 |
| 1 | 4 | 2 | 10070 | 5140 | 0.5104 |
| 1 | 3 | 1.5 | 17613 | 8941 | 0.5076 |

Measured dof/triangle: `dof_per_triangle: 0.51 (quarter domain at screen resolution; converges to 0.5000 as the mesh refines; full domain is a flat 0.5000)`. The quarter ratio is inflated at coarse resolutions by the symmetry-plane boundary vertices; this replaces the plan's `dof ≈ tri/2` initial guess.

## M2 VRAM
Clean-state measurements: every job in a **fresh Python process with all `julia.exe` killed first**, nvidia-smi polled externally, baseline recorded (rule: AGENTS.md "GPU / Julia hygiene"). Single frequency, 1 kHz. `peak` is nvidia-smi total minus baseline, so it includes the CUDA memory pool the worker reserves, i.e. an **upper bound** on need, not the matrix size.

| domain | dofs | predicted 8N^2 (MB) | baseline MB | peak MB | peak-baseline MB | result |
|---|---|---|---|---|---|---|
| full | 2,764 | 58 | 358 | 2,076 | 1,718 | ok |
| full | 5,496 | 230 | 332 | 6,746 | 6,414 | ok (26 s) |
| full | 9,193 | 645 | 346 | 7,831 | - | **OOM** (asked for 644.8 MiB = 8N^2) |
| full | 13,235 | 1,336 | 293 | 7,792 | - | **OOM** |
| quarter | 2,369 | 43 | 372 | 1,642 | 1,270 | ok |
| quarter | 5,140 | 202 | 368 | 5,948 | 5,580 | ok (29 s cold) |
| quarter | 8,941 | 611 | 366 | 7,841 | 7,475 | ok but **74 s** (solve 31 s, memory pressure) |
| quarter | 15,739 | 1,886 | 318 | 7,779 | - | **OOM** |

Verdict: **dense 8N^2 is the size of the operator that fails to allocate, but it is NOT the footprint.** Other buffers (assembly intermediates, solve workspace, memory pool) take 20-40x the operator at 5k dofs, so the plan's "8N^2 therefore 28,500 dofs" ceiling is wrong for this stack. Measured ceiling on the 8 GB RTX 4060 Laptop: **full domain between 5.5k and 9.2k dofs; quarter domain between 8.9k and 15.7k dofs**, and both are in memory-pressure territory above ~5k.
A 12-frequency batch with 512-point balloon on the 5,140-dof quarter mesh took **689 s** (assembly 672 s) versus 3.2 s for one warm frequency: see M3.
dof caps in force: see M3 (provisional, set from the throughput cliff).
Earlier contaminated numbers (concurrent session, stale Julia hosts) were discarded.

## M3 throughput
Warm worker, quarter meshes (`native_symmetry_plane="yz+xz"`), observation 73 angles, balloon `sphere_grid=(16,32)` = 512 points, solve only (mesh time below).

| case | dofs | frequencies | wall seconds | assembly | solve |
|---|---|---|---|---|---|
| first solve (cold, includes JIT) | 2,369 | 1 | 27.2 | 14.3 | 3.9 |
| second solve (warm) | 2,369 | 1 | 1.42 | 0.61 | 0.02 |
| **screen-like** | 2,369 | 12 + balloon | **5.04** | 3.85 | 0.20 |
| second solve (warm) | 5,140 | 1 | 3.21 | 1.65 | 0.07 |
| screen-like (pipelining ON, default) | 5,140 | 12 + balloon | **688.9** | 672.4 | 14.8 |
| screen-like, `BLAB_METAL_PIPELINE=0` | 5,140 | 12 + balloon | **1,151** | 1,126 | 23.7 |
| **12 single-frequency calls in a loop** | 5,140 | 12 x 1 + balloon | **33.3** (2.3-3.0 s each) | | |
| 3-4 single-frequency calls | 7,001 | 3 | 7.5 s each | | |
| 4 single-frequency calls | 8,941 | 4 | 45 s each | | |

**Finding: a multi-frequency `solve_frequencies` sweep falls off a cliff above ~2.4k dofs on this card (689 s at 5.1k), and `BLAB_METAL_PIPELINE=0` does not help. The same work as one call per frequency takes 33 s.** Task 05's CUDA adapter must loop one frequency per call.
Per-frequency cost, quarter meshes, warm worker, one call per frequency: 2,369 dofs 0.4 s; 5,140 dofs 2.8 s; 7,001 dofs 7.5 s; 8,941 dofs 45 s (memory pressure).
seconds per screening candidate (12 frequencies + balloon, solve only, looped per frequency): **5.0 s at ~2.4k dofs (sweep call), 33 s at ~5.1k dofs**; candidates per hour: **~700 at 2.4k, ~110 at 5.1k**
mesh time: meshing the 2.4k-dof quarter horn is a few seconds of CPU (not separately timed this pass; see CONTINUITY open items)
mesh fraction of that: small versus solve at >= 5k dofs
verify-like (16k dofs, 25 freqs): **not runnable** (15.7k quarter dofs OOM, M2). Verify at the 7,000 cap: 25 x 7.5 s ~ 3 min per candidate.

**dof caps in force (quarter domain, set from the per-frequency cost curve): screen 5,000 / verify 7,000 / final 8,900.** Full-domain meshes cannot exceed ~5,500 solved dofs, so full-domain verify/final are not available on this card. The plan's 8,000 / 16,000 / 24,000 are withdrawn.

## M4 cuda vs cpu
CPU runtime provisioned this session (`python -m hornlab_beat_bem.provision --backend cpu`, ready).
Quarter mesh, 2,369 dofs, one frequency per call, warm worker (i7-14650HX, 24 threads):

| backend | cold first solve | warm per frequency |
|---|---|---|
| cuda | 29.0 s | 0.78-0.82 s (1.4 s at 500 Hz) |
| cpu | 3.7 s | 1.42-1.53 s |
| cuda + `HORNLAB_BEAT_FORCE_CPU=1` | 28.7 s | 0.84-0.86 s |

cuda: 0.8 s   cpu: 1.45 s   ratio cpu/cuda: **~1.8x** at this size.
**`HORNLAB_BEAT_FORCE_CPU=1` does not redirect an explicit `beat_backend="cuda"` request** (the run above still used CUDA); the variable only makes `beat_engine_status()` report CPU available without a provisioning record. To use CPU, pass `beat_backend="cpu"`.
CPU at larger dofs (quarter meshes, one frequency per call, warm; no VRAM limit):

| dofs | cpu warm per frequency | cuda warm per frequency |
|---|---|---|
| 2,369 | 1.45 s | 0.8 s |
| 5,140 | 6.6-7.6 s | 2.8 s |
| 7,001 | 12.6-37.4 s (rising run to run) | 7.5 s |
| 8,941 | 56.6-57.8 s | 45 s |

CUDA is faster than the CPU backend at every size measured (about 1.3x at 8.9k, 2.3x at 5.1k, 1.8x at 2.4k). The CPU backend has no OOM limit and would run meshes beyond the CUDA ceiling (full-domain 9.2k+, quarter 15.7k+), but at roughly 1 minute per frequency from 9k dofs up; not measured above 8.9k.


## M5 worker warmth
First / second / after `detach_workers()` (quarter mesh, 2,369 dofs, 1 kHz, one process): **27.2 s / 1.42 s / 0.84 s**. The persistent host survives `detach_workers()`, so a later solve in the same process pays no cold start. A *new* process connects to a surviving host in about the same way (see hygiene note: that is also how stale hosts accumulate).

## M6 symmetry pairing
Same horn, full (`quadrants=1234`, `native_symmetry_plane=None`, 5,496 dofs) vs quarter (`quadrants=1`, `native_symmetry_plane="yz+xz"`, 1,438 dofs), mouth_res 8 mm, 73 angles, clean GPU:
- max |dB| difference by frequency: **500 Hz 0.039, 1 kHz 0.036, 2 kHz 0.045, 4 kHz 0.058, 6 kHz 0.497**. Overall max **0.497 dB** (at 6 kHz, where an 8 mm mouth is at the edge of the 6 elements-per-wavelength rule, 7.1 kHz).
- full vs quarter max difference (resolved band, <= 4 kHz): **0.058 dB**
- deliberately mismatched (quarter mesh, no flag): max **54.9 dB**; on axis at 1 kHz **12.11 dB** wrong.
- Earlier coarse-mesh run (mouth_res 26 mm): 0.25 dB up to 4 kHz and 22.7 dB at 8 kHz; that was under-resolution, not a mapping bug.

## M7 max_triangles
Largest mesh built with `allow_large_mesh=False`: **70,460 triangles** (full-domain equivalent) with `max_triangles=200000`.
Error if refused (default `max_triangles=18000`):
`hornlab-waveguide: error: mesh build failed: generated mesh contains 18,382 triangles, exceeding the effective limit 18,000; the wall-clearance guard refines the freestanding shell below the requested ...`
The quarter effective limit is `18000/4 = 4500` (the ceiling is full-domain-equivalent). **18,000 is a default, not a hard check** — no second hard check appeared up to ~70k; `allow_large_mesh=True` bypasses the limit entirely.

## C1 balloon grid
Field name and values: `ObservationConfig.sphere_grid = (n_theta, n_phi)` (beat and bempp). `n_theta ≥ 2`, `n_phi ≥ 3`, `n_theta*n_phi ≤ 100000`; `sphere_theta_max_deg` default `180.0` (full sphere).
Returned shape and convention: `sphere_pressure_complex (F, n_theta*n_phi)` with `sphere_theta_deg` and `sphere_phi_deg`; **theta-major, theta in [0, sphere_theta_max_deg] relative to +Z, phi in [0, 360) with no wrap column.** Vector deps: complex128.
Status: **AVAILABLE**

## C2 complex pressure
- beat: **yes** — `pressure_complex`, shape (F, P, N), complex128.
- bempp: **yes** — `pressure_complex`, shape (F, P, N_angles), complex128.

## C2b boundary surface traces
- beat `surface_traces`: **available** — `SolveConfig.surface_traces=True` populates
  `surface_pressure_complex (F, n_vertices)` = P1 pressure **by node/vertex**, and
  `surface_neumann_complex (F, n_faces)` = DP0 normal derivative **by face/element**.
  Under a reduced-mesh symmetry solve these cover the fundamental domain only.
- Ordering: pressure **by node**, neumann **by element** (ordering vs `.msh` order is a question for Collin, see issue q-surface-traces).
- Size per design at screen resolution: **measured 111,280 bytes per frequency at 2,369 dofs** (pressure (F,2369) + neumann (F,4586), both complex128); about **1.3 MB for 12 frequencies**. 1-in-20 sampling therefore costs ~65 KB per design on average.
- `hornlab_bempp_bem.evaluate_exterior_from_traces(mesh_or_grid, frequency_hz, k_real, pressure_p1, neumann_dp0, points_xyz, *, symmetry_plane=None, ground_plane=None, assembly_backend="auto", precision="double", opencl_device="cpu", vectorization_mode="auto", restrict_neumann_space=True) -> NDArray[complex128]` — returns complex exterior pressure at `points_xyz (N,3)`. bempp also exposes `surface_pressure_complex (F, n_p1_dofs)`.
Status: **AVAILABLE**

## C3 impedance boundary conditions
- **beat: NO.** `SolveConfig` exposes only rigid walls plus a single unit velocity source; the coupled-FEM doc explicitly lists "general impedance boundary kinds or arbitrary impedance functions" as not supported for the BEM solve.
- **bempp: YES.** `SolveConfig.impedance_sources: dict[int, complex]` (tag → β); the Robin BC `∂p/∂n = i·k·β·p` is applied on the impedance tags via `_build_robin_contribution` / `_assemble_and_solve_impedance` (`hornlab_bempp_bem/bie.py`). Caveat quoted in source: "Robin/impedance BC + Burton-Miller formulation is not ..." — the two cannot be combined (check the exact limitation before relying on it).
- Evidence: `hornlab_bempp_bem/bie.py:261` (`impedance_sources`), `:337`, `:397`, `:431`, `:467`; beat `docs/coupled-solver.md:626`.

## C4 structured surface grid
Reachable through public API: **yes** — `hornlab_mesher.config_builder.build_point_grid` is documented in `docs/public-api.md:194` ("Point grid for sizing and symmetry; reads `grid_n_phi`, `grid_n_length`, `inner_points`, `outer_points` (flat lists, phi-major)"). `hornlab_mesher.geometry.PointGridHornGeometry` is documented at `:200`/`:285`.
Array shape and ordering: **flat, phi-major**; `viewport.build_viewport_geometry_from_config` reshapes `inner_points` to `(grid_n_phi, grid_n_length + 1, 3)` (`public-api.md:196`).
Azimuthal axis wraps: **yes** (full-circle phi-major grid).
- Caveat: the preview overwrites `mesh.angular_segments`/`length_segments`; the point grid reads `grid_n_phi`/`grid_n_length` (`public-api.md:218`).

## C5 driver excitation
Definition on tag SD1D1001: the source is physical tag **2 = `SD1D1001`** ("Primary source surface", `docs/architecture.md:121`, `docs/builder-invariants.md:147`). beat drives it via `velocity_sources={2: 1.0}` (unit normal **acceleration** output convention; 1 m/s normal-velocity basis rescaled by 1/(−iω)); `source_motion` is `"normal"` (breathing cap) or `"axial"` (rigid piston along +z).
Frequency-dependent: **no** (unit amplitude).
Can the distribution be prescribed: **no** — exactly one source tag with a real unit amplitude; complex amplitudes are refused.

## Mesher examples directory
`C:\Users\hunte\AppData\Local\Temp\claude\C--Users-hunte-Hrns\a6d40e1e-5753-40e0-bc82-45dfdc35e6c1\scratchpad\src\hornlab-waveguide-mesher\examples` (source clone; NOT installed under site-packages). Console script: `hornlab-waveguide` → `hornlab_mesher.cli:main`; usage `hornlab-waveguide <config.toml> -o <out.msh>`.

## Anything surprising
- **A second agent session ran concurrent BEM solves on the same GPU and the same BEAT worker registry during this session** (a `.claude/shell-snapshots` bash running `m2_driver2.py`/`m2_one.py`, holding ~6.3 GiB and writing `m2_*_out.txt`). This caused `Out of GPU memory` at modest dof counts, `ConnectionResetError` on warm-worker reuse, and orphaned Julia worker processes. **All M2/M3/M4 numbers taken while it was active are invalid.** The plan's "one GPU, one BEM solve at a time" was violated by the environment, not by this task.
- The beat persistent worker **reserves a large CUDA memory pool** (~1.7 GB observed on a solve that only needs ~60 MB), so `nvidia-smi memory.used` is a poor proxy for the matrix footprint.
- `solve_frequencies` on a reused worker after the parent process is killed can leave a stale registry entry that makes the next process OOM/reset; set `HORNLAB_BEAT_WORKER_DIR` to a fresh directory, or kill stray `julia.exe`/`julia_beat` worker hosts.
