# NOTES FOR SENIOR

**Append only.** Every agent may add to this file; nobody edits or deletes an existing block.
Use this for contract gaps, files you need but do not own, installed-package bugs, and anything
you were blocked on twice (hard rules 1, 3, 5 and 8 in `docs/plan/00_ORCHESTRATOR.md`).

Format for each block:

```
## YYYY-MM-DD  <task id>  <one-line subject>
What I was doing:
What happened (exact error / output):
What I tried:
What I need decided:
```

---

## 2026-10-12  task-02  machine deviation: GPU is RTX 4060 Laptop, not RTX 4070
What I was doing: recording the CP-0 target machine.
What happened: the plan names an RTX 4070 Laptop 8 GB; the machine reports an RTX 4060 Laptop with 8 GB and driver CUDA 13.3.
What I tried: proceeded anyway. VRAM is the same (8 GB), so the dof caps are unchanged; expect slower seconds/candidate.
What I need decided: nothing — recorded as an approved deviation; reflected in TOOLCHAIN.md.

## 2026-10-12  task-03  no YAML key for frequency-grid edges
What I was doing: implementing config.freq_grid / mode_freqs.
What happened: 01_CONTRACTS §8 fixes a log grid per mode but there is no YAML key for the grid edges.
What I tried: used the §8 table (screen 500-10000/12, verify 300-16000/25, final 250-20000/36), with the top edge clipped to target.band_hi_hz so the mesh is never asked to resolve frequencies the objective ignores.
What I need decided: whether a future YAML key should expose the grid edges.

## 2026-10-12  task-03  CP-1 test 3 deviation (angle step)
What I was doing: tests/test_config.py test 3.
What happened: the plan's literal wording "(angle_count - 1) divides 180 evenly" fails for the contracted default 73 (180/72 = 2.5).
What I tried: the test instead asserts 18000 % (n-1) == 0, i.e. the step 180/(n-1) is a whole number of hundredths of a degree (73 -> 2.50 deg) and the -90..+90 grid hits 0 exactly.
What I need decided: confirm the intent is a clean angular step, not literal divisibility of 180.

## 2026-10-12  task-06  cardioid threshold is -6.0206 dB, not -6.0
What I was doing: writing the fake_response cardioid fixture and its assertions.
What happened: (1+cos theta)/2 at +/-90 deg is exactly -6.0206 dB, so a strict -6.0 dB threshold reads about 179.7 deg instead of the contract's 180.0.
What I tried: the fixture asserts the -6 dB total included beamwidth is 180.0 using the exact 20*log10(0.5) value.
What I need decided: task 06 metrics must use the exact cardioid value; flagged for the task 06 issue.

## 2026-10-12  task-03  ICW termination is categorical; coverage_angle convention unconfirmed
What I was doing: writing examples/icw_termination.yaml from the mesher schema.
What happened: the mesher `termination` key is categorical (default flat_baffle) and cannot take a lo/hi bound, so it lives in seed_params only. The `coverage_angle`/`coverage_angle_deg` half-vs-total convention is not confirmed by the schema.
What I tried: kept termination in seed_params; flagged the coverage convention.
What I need decided: confirm coverage_angle is a half-angle or a total included angle.

## 2026-10-12  task-02  solver API drift: SolveResult, not Response
What I was doing: CP-0 step 6 first solve and schema dump.
What happened: plan 02 predicts a `Response` with `p1_dof_count`, `native_diagnostics`, `metal_pipeline`. The installed hornlab-beat-bem 0.2.0 returns a `SolveResult` with `mesh_info.n_vertices` / `n_triangles` (no p1_dof_count / native_diagnostics).
What I tried: confirmed n_vertices IS the P1 dof count; recorded the real schema in TOOLCHAIN.md.
What I need decided: task 05 adapts to SolveResult, not the plan's guessed Response.

## 2026-10-12  task-02  MB2/M6: dense 8N^2 storage OOMs at ~20k dofs on the 8 GB card
What I was doing: M2 VRAM vs dofs and M6 symmetry pairing.
What happened: a single-frequency solve at 20,193 dofs tried to allocate 3.038 GiB and raised "Out of GPU memory ... 100.00% (7.996 GiB/7.996 GiB)". 8 * 20193^2 bytes = 3.04 GiB, confirming dense complex64 8N^2 storage. At the default mouth_res_mm=26 the 8 kHz result is under-resolved: full-vs-quarter agree to <=0.26 dB at 1/2/4 kHz but diverge by up to 22.7 dB at 8 kHz (discretization, not a symmetry bug).
What I tried: measured dof/triangle = 0.50 (full) and ~0.51 (quarter, wall-boundary overhead at coarse res).
What I need decided: the plan's dof caps (verify 16000, final 24000) will OOM; caps must be lowered to the measured ceiling. UNRESOLVED: the exact max dof that fits.

## 2026-10-12  task-02  stale persistent Julia hosts corrupt VRAM measurements and cause crashes
What I was doing: M2 VRAM sweep, one fresh Python process per mesh.
What happened: runs after the first crashed with "Warm BEAT Engine solver exited with code 1 / 4294967295" or OOMed at sizes that fit alone (quarter 5.1k dofs failed in a sweep, then succeeded alone: 25.6 s, assembly 13.1 s). `Get-Process julia` showed several ~1 GB hosts left over from earlier processes, even though each script called `shutdown_workers()`. Earlier full-domain OOMs at 9.2k-20k dofs were measured in this contaminated state and must be re-measured clean.
What I tried: killed all julia.exe between jobs and re-ran (results in TOOLCHAIN.md).
What I need decided: (1) task 05 must make `solve/worker.py` release hosts reliably and test it by process list; contract 01 section 9 assumes shutdown works. (2) The "GPU / Julia hygiene" rules are now in AGENTS.md and CLAUDE.md. (3) Consider a `doctor` check that warns when more than one julia host is alive or VRAM baseline is above 1 GB.

## 2026-10-12  task-06  RESOLVED HERE, please confirm: "-6 dB" is implemented as HALF PRESSURE (-6.0206 dB), not -6.0000 dB
What I was doing: beamwidth_deg against contract tests 1 and 2 (cardioid reads 180.0, dipole reads 120.0, both to 0.05 deg).
What happened: the orchestrator addendum suggested an epsilon of 1e-3 dB around a strict -6.0 dB threshold. That cannot work: (1+cos t)/2 is 20*log10(0.5) = -6.0206 dB at +-90 deg, which is 0.0206 dB below -6.0, i.e. 20x outside a 1e-3 dB epsilon. A strict -6.0 reads the cardioid 179.73 and the dipole 119.83 (both fail the 0.05 tolerance).
What I did: polar._threshold_db maps the conventional labels to their exact amplitude ratios: drop_db=6.0 -> 20*log10(0.5) (half pressure), drop_db=3.0 -> 10*log10(0.5) (half power); any other value is taken literally. No tolerance was loosened, the result is continuous in the pattern (no snapping), and every contract case is exact on any grid. A near-threshold epsilon of ~0.025 dB with snapping was the alternative; I rejected it because it is discontinuous and grid dependent (the piston cases at a 2.5 deg grid would see up to 0.12 deg snap error).
What I need decided: confirm 01_CONTRACTS section 10 "-6 dB" means p = 0.5 (it must, for its own cardioid/dipole numbers). Every later beamwidth in the project inherits this.

## 2026-10-12  task-06  CONTRACT GAP: di_from_cuts formula contradicts tests 14 and 15
What I was doing: contract tests 14 (target_di_db(360, 180) == 0.0) and 15 (di_from_cuts(180, 180) on an omni pattern agrees with the balloon DI, 0 dB, to 0.3).
What happened: Omega = 4*arcsin(sin(bw_h/2)*sin(bw_v/2)) gives 3.01 dB for (180, 180) (a hemisphere) and ~0 solid angle (huge DI) for (360, 180) because sin(180 deg) = 0. Test 13 (75x45 -> 11.26 dB) is fine.
What I did, minimal and documented in di.py: sin(bw/2) is clamped at 1 for bw >= 180 ("no crossing" means "at least that wide"), and if BOTH cuts are >= 180 the pattern is treated as omnidirectional (Omega = 4*pi, DI = 0). Tests 13-16 all pass as written. Consequence to know: an omni source AND a cardioid both read bw = 180/180, so a cuts_estimate DI of 0 is meaningless for them; that is the existing reason di_source must be carried and no checkpoint may pass on cuts_estimate.
What I need decided: confirm the saturation rule, or give the intended formula for bw >= 180.

## 2026-10-12  task-06  ripple_db uses the SAMPLE std (ddof=1); contract says only "standard deviation"
What I was doing: contract test 19 (alternating +1/-1 dB inside coverage -> 1.0 to 1e-9).
What happened: the on-axis sample is inside the coverage set and is exactly 0 after normalization, so with n coverage samples the population std of any +1/-1 alternation is sqrt((n-1)/n) (0.9837 for 31 samples), never 1.0. The sample std (ddof=1) is exactly 1.0 when the other n-1 samples are balanced +-1.
What I did: ddof=1 in ripple_db (documented). band_flatness_db is the plain population std after removing the mean (ddof=0), as its docstring says. Difference between the two conventions is a factor sqrt(n/(n-1)) (about 1.6 % at n=31).
What I need decided: confirm ddof=1, or say whether the earlier tiling study's ripple used ddof=0 (then test 19 needs rewriting, not the code).

## 2026-10-12  task-06  smaller ambiguities, for the pipeline owner
- constants.py quotes f11 = 7914 Hz for "1.0 in" and 3957 Hz for "2.0 in" under a comment that says "radius a". Those numbers are for a throat DIAMETER of 1.0 / 2.0 in (radius 12.7 / 25.4 mm). compute_metrics takes throat_radius_m, so pass the radius; a 1.0 in exit radius (r0 = 25.4 mm) gives 3957 Hz. The comment in constants.py (task 03) should say diameter.
- coverage_from_room: the task file gives `height_m` but no use for it next to ear_height_m and source_height_m. It is the ceiling height and is only used to reject impossible heights. It also needed a band, which the signature lacks: added keyword-only band_lo_hz=700, band_hi_hz=13000 (mirrors examples/osse_baseline.yaml). Vertical coverage assumes the horn is tilted at the middle of the ear-height elevation range.
- compute_metrics: DI uses the balloon only when BOTH spl_balloon_db and balloon_dirs are present, and always with equal weights (equal-area grid). The real solver balloon is a theta-phi grid; metrics.di.sin_theta_weights() and di_from_balloon(..., weights=) exist and are tested, but nothing converts a solver theta-phi balloon to the contract's equal-area form. Task 05/08 must either resample to an equal-area point set or pass weights; compute_metrics does not auto-detect.
- DI quadrature: 512 Fibonacci points are ample for broad patterns (cardioid error 4e-6 dB) but NOT for narrow beams: an unbaffled piston at ka=24 (10.6 deg beamwidth) reads 24.82 dB at 512 points against 24.59 true (+0.23 dB), 24.595 at 4096.

## 2026-10-13  task-04  to_mesher_config is SECTIONED, not flat (task file sketch drops max_triangles)
What I was doing: implementing families.to_mesher_config from the 04 task sketch (flat dict: formula, mode, **params, quadrants, *_res_mm, max_triangles, ... at top level).
What happened: measured against hornlab-waveguide-mesher 0.2.4: a TOP-LEVEL `max_triangles` is silently ignored (default 18000 applies; a quarter mesh was then refused at "effective limit 4,500" although I passed 50000). Unknown profile keys are also silently ignored (`bogus_key` builds fine). Pinned by tests/test_mesh_build.py::test_mesher_defaults_are_not_trusted_flat_dict_drops_max_triangles.
What I tried: emit the mesher's own sectioned form (profile / cross_section / mesh / morph / gcurve + top-level formula, mode, output), routing each key by KeySpec.section. Tests 8 etc. read cfg["mesh"][...].
What I need decided: nothing; recorded so task 08 and anyone reading the DEBUG repr is not surprised.

## 2026-10-13  task-04  contract gap: config.mesh_spec and sizing.max_triangles_for disagree when dof_per_triangle != 0.5
What I was doing: mesh/sizing.py max_triangles_for (task file: ceil(dof_cap / dof_per_triangle * qf * slack)).
What happened: task 03's hornlab_search/config.py mesh_spec uses ceil(2 * cap * qf * slack) (01_CONTRACTS section 6 literal), which ignores dof_per_triangle. With the shipped 0.51 the two differ by 2 percent (72157 vs 73600 for screen/quarter). I cannot edit config.py.
What I tried: build_mesh takes `mode=` (preferred; cap = cfg.mesh.dof_cap(mode)); without it sizing.dof_cap_for infers the mode by matching max_triangles against BOTH formulas, and as a last resort inverts max_triangles_for. Tested in test_mesh_sizing.py.
What I need decided: whether config.mesh_spec should call sizing.max_triangles_for (one source). Task 08 should pass mode= to build_mesh regardless.

## 2026-10-13  task-04  the shipped baseline seed does not fit the plan's dof caps at the screen top frequency
What I was doing: CP-2 table for examples/osse_baseline.yaml.
What happened: this horn is large (bbox 0.401 x 0.321 x 0.26 m, mouth wall area 0.282 m^2 per quarter, 1.129 m^2 full), not the 0.125 m^2 the contracts section 6 table assumed. Measured quarter-domain triangles: 3 kHz 2331, 6 kHz 8819, 9 kHz 19546, 12 kHz 34893 (dofs 1189 / 4498 / 9969 / 17796 est, vertex counts 4530 at 6 kHz). `build_mesh(seed, mesh_spec("screen", cfg), cfg, d, mode="screen")` (f_max 10000, cap 8000) raises MeshTooLargeError (pre-mesh estimate ~13.9k dofs); verify (13000 Hz, cap 16000) is also refused (40,839 triangles); final (13000, cap 24000) builds. f_max_for_dofs (effective c=3.0): screen cap 8000 buys ~7.8 kHz, verify 16000 ~11.0 kHz, final 24000 ~13.5 kHz for this horn.
What I tried: nothing to change; it is a budget decision, and the dof caps themselves are already flagged unsafe on the 8 GB card (TOOLCHAIN M2), so the real caps will be lower still.
What I need decided: with the final caps, either (a) shrink the screen grid top edge / band_hi, (b) lower epw for screen, or (c) accept a smaller seed horn. Search cannot start on the baseline seed as configured.

## 2026-10-13  task-04  decisions on things the examples left open (freeform_hv.yaml, icw_termination.yaml)
What I was doing: DesignSpace.from_config on the shipped YAMLs.
What happened: (1) icw_termination.yaml bounds `kappa0` and `theta1_deg` but its seed_params omit both; they change the geometry (1692 vs 3474 triangles at the same resolution). DesignSpace fills a searchable key that is absent from the seed with the bound midpoint (log-mid for log bounds), logs a WARNING naming the keys, and stores the filled seed (kappa0 0.25, theta1_deg 16.0). (2) freeform_hv.yaml bounds `profileH.mouthAngleDeg`, `profileV.mouthAngleDeg` and a bare `exponent`. Search keys therefore accept dotted paths into the seed (`a.b.0.c`, integers index lists) and, for FREEFORM only, bare `exponent` resolves to the first superellipse station of crossSections. (3) The contract table lists FREEFORM `throatAngleDeg`/`mouthAngleDeg` as keys; in the mesher they live inside profileH/profileV, so those are validated there (top-level use is rejected). (4) The ICW coverage_angle_deg convention (half vs total) is still unconfirmed; I did not touch it.
What I tried: kept every rule in one place (design/families.py param_get/param_set/resolve_path, design/space.py __post_init__) with tests.
What I need decided: confirm midpoint-fill is acceptable, or add kappa0/theta1_deg to the ICW example seed (task 03 owns examples).

## 2026-10-13  task-04  hard-failure exception classes live in mesh/build.py; task 08 must not swallow them
What I was doing: implementing the bbox and symmetry guards.
What happened: types.py has only three exceptions. The bbox-units guard and the quadrants/symmetry-flag guard are not "bad candidate" cases (01_CONTRACTS section 15: units bug, stop the run), so I added MeshConsistencyError(RuntimeError) with subclasses MeshUnitsError and SymmetryMismatchError in mesh/build.py. They deliberately do NOT inherit GeometryInvalidError / MeshTooLargeError.
What I tried: n/a.
What I need decided: search/evaluate.py (task 08) must let MeshConsistencyError propagate (stop the run) rather than turning it into a penalty row. build_mesh also deletes the mesh it just wrote when any post-mesh guard fires, so an unusable .msh is never reachable by a solver.

## 2026-10-13  task-04  note on private-ish mesher API use
What I was doing: the sub-100 ms pre-mesh dof guard (04 test 18).
What happened: the mesher only estimates triangle count after building OCC/gmsh geometry (1.8 s to 17 s before it refuses). The cheap estimate calls hornlab_mesher.config_builder.resolve_geometry (not in public-api.md "Stable") on a 20 mm copy of the config (about 25-60 ms for a quarter domain), sums inner/outer point-grid area, and applies the mesher's own 2.3 tri per A/h^2. It tracks real counts at 0.81x to 1.13x across OSSE / ICW / FREEFORM, 3-12 kHz, so the 1.5x reject margin cannot reject a mesh the cap would accept. It returns None on any exception, in which case only the mesher's checks and the exact post-mesh dof check apply.
What I tried: n/a.
What I need decided: nothing; if resolve_geometry moves in a later mesher SHA the pre-mesh guard silently degrades to the post-mesh one (test_premesh_estimate_tracks_real_counts will fail first).

## 2026-10-13  task-07  dataset: contract gaps and choices the pipeline owner (task 08) must know
What I was doing: implementing dataset/record.py and store.py against 01_CONTRACTS section 13 and 07_TASK_DATASET.
What I decided (all minimal, all documented in the module docstrings; please confirm or rule otherwise):
1. SCHEMA GAP: rule 6 / task item 2b say "the fraction recorded in each record's metadata", but the section 13 metadata schema has no field for it. I added `traces.sample_fraction` (inside the existing `traces` block) and validate_record requires it. No other field was added.
2. lib_shas: the schema example shows 3 entries; task rule 3 says "all four packages plus hornlab_search". validate_record requires FIVE: hornlab_mesher, hornlab_beat_bem, hornlab_bempp_bem, hornlab_plots, hornlab_search (non-empty strings; "unknown" is acceptable for hornlab_search, absence is not). The pipeline must pass all five from TOOLCHAIN.md.
3. ARRAY LAYOUT: I took the task's accepted alternative, ONE uncompressed .npz PER RECORD in `shard-NNNN/rec-RRRR.npz` (plain array names as keys), not 01_CONTRACTS' `shard-NNNN.npz` keyed `<row>/<name>`. Reason: one fsync per record instead of one per array (500 appends in ~3.6 s with three fsyncs each), no zip step, nothing to recover from a crash during shard close. The phase-2 loader must use DatasetStore.read / iter_records / to_training_arrays, not np.load on a shard archive.
4. index.jsonl carries more than {design_hash, shard, row, objective, ok}: also family, backend, mode, lib_sha (= "<mesher10>+<beat10>"), created_utc, solve_seconds, traces (bool). Needed so stats() and the exporter filters read only the index (task rule 6).
5. build_record(ev, target, lib_shas) is the task signature, but an Evaluation does not carry the SolveSpec (mode, observation, gmres_tol, requested freqs), the mesh area_m2, or the mesher grid segment counts / availability. I added keyword-only `solve_spec=`, `area_m2=`, `grid=`, `traces=`, `trace_sample_fraction=`, `excitation=`, `created_utc=`. Task 08 should pass solve_spec, area_m2 and grid on every call; without them those fields are written as null (grid.available False). MeshResult has no area_m2 field and no grid field.
6. DatasetStore.append validates first and RAISES ValueError on an invalid record (nothing is written). The search loop must wrap the call in try/except, log ERROR, and continue: a dataset write must not kill a search.
7. append_traces never overwrites: a second capture for one design_hash goes to traces/<hash>-1.npz and the returned path says so. should_capture_traces(design_hash, fraction) is a deterministic hash-based 1-in-N sampler for the pipeline to use.
8. Single writer: thread lock only, no process lock.
9. Family-imbalance warning fires at >80% one family once the store has >= 10 records (the 10 is mine; a one-record store is trivially 100%).
10. Exporter defaults: X is float32 (as specified); y arrays stay float64. Non-numeric params (ICW termination, FREEFORM point lists) are not X columns and are listed in meta['skipped_keys']; pass keys=DesignSpace.keys() to fix the columns.
What I need decided: items 1, 2 and 3 only; the rest is FYI for task 08.

## 2026-10-13  task-05  solve/: plan-vs-reality mappings the pipeline and metrics owners must know
What I was doing: adapting hornlab_beat_bem 0.2.0 / hornlab_bempp_bem to Backend; all numbers below measured on the RTX 4060 (CP-3 run).
What I decided (read from the installed source, then verified on real solves):
1. ANGLES: the solver takes the signed range directly (ObservationConfig angle_min/max = -90/+90, angle_count=73), H sample a at (R sin a, 0, R cos a), V at (0, R sin a, R cos a) (BeatEngineDriver.jl polar_observation_points). So NO mirroring of a 0..180 sweep; spl_h_db[:, i] is angle -90+2.5*i, +angle = +X (H) / +Y (V). Verified by test 18 (horn shifted to -X / -Y is quieter on the +angle side, 100% of angle pairs, 1-2 dB). Response angles are arc_angles_deg(n) (exact 0); the solver's Float32 echo is asserted equal within 1e-3 deg.
2. LEVELS: spl_h_db/spl_v_db are ABSOLUTE dB re 20 uPa for UNIT NORMAL ACCELERATION of tag 2 (beat spl_db), recomputed from pressure_complex for bempp (whose own spl_db is on-axis normalised). Metrics normalise anyway.
3. z_throat = impedance * (-i*omega) / (rho*c): beat's `impedance` is the area-weighted mean source pressure per unit ACCELERATION in exp(-i omega t); this converts it to specific impedance / rho c in the SAME time convention, so mass-like loading has Im < 0 (the conftest fake uses the opposite sign; only Re is used). Re(z) = 0.075, 0.30, 0.78, 0.97, 1.01 at 500, 1k, 2k, 3k, 4k Hz on the seed, and bempp agrees to 3 digits.
4. n_dof comes from solver_log[i]['native_diagnostics']['p1_dof_count'] (the plan's top-level attribute does not exist); it equals mesh_info.n_vertices and the .msh node count on every mesh tried (2316/2316, 4941/4941).
5. spec.gmres_tol: beat has NO tolerance knob and used a direct dense LU solve ('dense_solve_method': 'lu') on every run, so it is recorded as gmres_tol_requested with gmres_tol_applied=None. bempp takes it.
6. beat refuses native symmetry 'xz' (quadrants '12'). bempp refuses Burton-Miller together with native symmetry, so BemppBackend uses STANDARD on reduced meshes and Burton-Miller on full ones (recorded in meta['formulation']). The cross-check below is therefore Burton-Miller/LU vs STANDARD/bempp: two independent formulations as well as codes.
7. BALLOON: beat's sphere grid is a theta-phi grid (theta 0..180 incl. both poles, phi 0..360 no wrap, theta-major), NOT equal area, and the pole rows are duplicated points. Response.balloon_dirs are built from sphere_theta_deg/phi_deg; Response.meta['balloon_grid']=[n_theta,n_phi] ((16,32) for 512 points; (23,45)=1035 for 1024). DI from it MUST use weights=sin_theta_weights(theta_deg_from_dirs(balloon_dirs)) (task 06); equal weights over-count the poles. I did not resample.
8. CUDA needs one solve_frequencies call per frequency (TOOLCHAIN M3). Measured on beat_cpu: no cliff (4,530 dofs x 4 freqs: one call 18.3 s vs per-frequency 19.2 s; 2,316 dofs x 6: 7.2 vs 7.7 s), so BeatBackend('cpu') makes one call.
9. SEED HORN SIZE vs THE SCREEN BAND (task 04/08/09 should look at this): the osse_baseline seed is 0.80 x 0.64 x 0.27 m. Real builds at epw=6: quarter 4,200 Hz -> 2,316 dofs; 6,000 Hz -> 4,530; the pre-mesh guard estimates 12.6k dofs at 9,528 Hz. So the screen cap (5,000 quarter dofs) resolves the seed only to about 6.3 kHz, not the 10 kHz screen f_max; build_mesh(mode='screen') will raise MeshTooLargeError for the default screen MeshSpec on this seed. My tests mesh at f_max chosen per dof target instead.
10. CUDA OOM / worker-exit handling: BeatBackend turns both into SolveOutcome(ok=False, message='[cuda_oom] ...' / '[worker_exit] ...'), kills the poisoned host (worker.recover_after_failure) and, for cuda_oom, appends one block per process to this file via solve.base.note_failure_for_senior (the dof cap is then suspect; clear stale hosts and reproduce from a clean state first, AGENTS.md rule 7). There is no per-solve timeout hook in the library: timeout_s is checked between frequencies only (CPU makes one call, so it does not apply there).
11. TRACES: beat's traces are in .msh NODE order (pressure, n_vertices) and .msh TRIANGLE order (Neumann, n_faces), no merging. bempp's grid vertices/elements equal those exactly and the symmetry context's reduced P1 space is vertex-ordered, so the dof permutation is the identity (checked by coordinate matching, which refuses unless one-to-one). The plain function_space(grid,'P',1) of an OPEN reduced mesh has FEWER dofs than nodes (2143 vs 2316: free-boundary vertices are constrained), so never use it for a symmetry-reduced solve. Test 19: exact recovery matches the solver far field to 8e-5 dB.
12. PROCESS SHAPE (worker.py): a BEAT host on Windows is venv python -> system python (both `-m hornlab_beat_bem.worker_host`) -> julialauncher.exe -> julia.exe (bare command line). Hosts are found by that marker and killed as a TREE; `taskkill /IM julia.exe` would take anyone's solver. In my runs shutdown_workers() DID stop the host every time (force_killed_roots=[] in all checkpoint runs); the force path is exercised only with a fake process table. A host spawned by a pytest/script process is its child, so killing that process tree (taskkill /T) also ends the host.
What I need decided: nothing blocking; item 9 is the one with consequences.

## 2026-10-13  task-08  pipeline: findings, deviations and decisions for the senior verifier
What I was doing: tasks 1-7 of 08_TASK_PIPELINE and the live CP-6 runs (RTX 4060, exclusive GPU).
FINDINGS (numbers are in the task-08 report):
1. SELFTEST --analytic: the task text assumes the unknown port drive scaling is a CONSTANT. For beat it is not: the port is a unit normal ACCELERATION (TOOLCHAIN C5), so |p| carries 1/omega. Literal constant-velocity R(ka) spread = 24.06 dB (exactly 6.02 dB per octave of ka). run_analytic therefore multiplies |p| by omega first (`drive="acceleration"`, default) and ALWAYS also reports the literal uncorrected spread (`r_spread_raw_db`). With the documented convention: R(ka) spread 0.020 dB (limit 0.5), and independently the ABSOLUTE level matches the unit-acceleration sphere to 0.016-0.036 dB at every ka (rows[].abs_vs_unit_accel_db), omnidirectionality 0.000-0.005 dB, 2 m -> 4 m spreading 6.0205-6.0206 dB, convergence sub3/4/5 = 0.0204 / 0.0051 / 0.0013 dB (sub 5 = 10,242 dofs full domain, solved on beat_cpu in 34 s because it does not fit CUDA). Please confirm the acceleration reading is acceptable for CP-7a #1; it uses only the documented convention and the absolute match is the stronger evidence.
2. The icosphere + gmsh 2.2 writer are in search/selftest.py, the scoped exception the task file grants. Nothing else in the tree writes meshes.
3. LIVE BUG found and fixed: the Julia host resolves a RELATIVE mesh path against its own cwd. `search --resume runs\<dir>` failed every solve ("opening file ... No such file"). evaluate() and cma._prepare now resolve run_dir to an absolute path (test added). The 10 failed records that run wrote to the first dataset were moved aside with that dataset (scratch/polluted/), and the live chain was re-run from empty runs/ cache/ dataset/ directories.
DECISIONS the contract left open (all minimal; rule on them if you disagree):
4. terms in Evaluation.terms are RAW (unweighted); weighted = weights[k]*terms[k] (objective.weighted_terms). Key set is always TERM_KEYS + n_nan, n_in_band, di_estimated. A term whose every in-band value is NaN is set to NAN_TERM_FILL = 30.0 (finite, worse than a working design, far below the 1e3 failure penalty). Out-of-contract number, flagged. Target.freq_weights is not used (the contract defines no semantics for it). n_nan counts in-band FREQUENCIES with an unmeasurable input.
5. DI from the solver's theta-phi balloon: metrics/compute.py is not mine and assumes equal weights. search/evaluate.py:metrics_from_response computes the sin(theta)-weighted DI with di_from_balloon(weights=...) per frequency and hands compute_metrics a one-column balloon holding that weighted power, so every metric/scalar/di_source comes out of compute_metrics unchanged and DI is exactly the weighted one (tested against the exact cardioid DI 4.77 dB; equal weights are off by >0.25 dB). A balloon without meta['balloon_grid'] is treated as equal-area.
6. Cache/resume semantics: (a) in-run memo `ctx.known`, preloaded from search.ndjson, serves successful rows AND deterministic failures (invalid geometry, mesh too large); a hit writes no ndjson row, no dataset record, consumes no budget. Solver failures are not memoized (a retry may succeed). (b) cross-run solve cache cache/solve/<design>-<mesh>-<solve>/ (hit needs ok:true) re-scores the stored Response with the CURRENT weights; it appends an ndjson row flagged cached and a dataset record only if the store has none for (design, mode, ok). (c) --budget counts non-cached evaluations of THIS invocation, the seed included, checked before every candidate, so a run can stop mid-generation (the partial generation is not told to CMA); cma maxfevals is deliberately unused. (d) run.json stats are cumulative over resumes (from the ndjson); the last invocation's own numbers are under last_invocation. A resume starts best from the best row already on disk, so a short resume cannot overwrite best.json with a worse design (live-found, test added).
7. Dataset: one record per NON-CACHED evaluation (failures included); mesh.grid.available is True (the grid is regenerable through hornlab_mesher.config_builder.build_point_grid from the recorded params; it is not stored per record), angular/length segments are read from the mesher config (defaults 64/32). The trace fraction is a CLI flag/argument (--trace-fraction, default record.DEFAULT_TRACE_FRACTION 0.05), not a YAML key (none exists in the contract); traces come from BeatBackend.solve_traced on the ORIGINAL solve.
8. Report: convergence, stacked term bars and beamwidth/DI-vs-frequency (with f_break/f11 marker lines and the target band) are small inline SVGs written in report/html.py because hornlab_plots has no equivalent and the task asks for them; all physics PNGs (heatmaps, polars, DI, impedance) come from hornlab_plots, no matplotlib import. The noise-floor box uses NOISE_FLOOR_INPUTS (idempotence 3.6e-5 dB, full-vs-quarter 0.031 dB, beat-vs-bempp 0.055 dB from the task 05 report; epw=6 discretization error NOT YET MEASURED, CP-7c), overridable via run.json["noise_floor"]. It says the floor is a lower bound until CP-7c is done.
9. OBJECTIVE SCALE (task asked to print the terms and flag a 100x term): osse_baseline seed, raw/weighted: cov 19.22/19.22, rip 1.496/1.496, di 0.286/0.086, dislope 0.193/0.096, flat 3.388/1.694, load 0/0, J = 22.59. cov is 224x the weighted di term. This is the SEED being far from the 75x45 target (bw_h about 95, bw_v about 84 deg), not a wrong divisor; the /100 and /10 are in the frozen contract, so I did NOT change them. If you want di/dislope to matter during the search, raise their YAML weights (they are data, not code).
10. Seed J is reproducible across processes (osse_baseline 22.5921 twice; search_smoke 22.0678 twice and an identical 60-evaluation trajectory in two separate searches): GPU nondeterminism is below anything CMA sees.
11. verify mode: verify and final meshes still equal the screen mesh (bands are clipped to band_hi), so `verify` differs from `screen` only by the 25-point frequency grid and the larger balloon; screen vs verify J differed by 0.04-0.35 on the top 3 designs, which is a measure of how much the 12-point screen grid can mis-rank.
12. search_smoke is much cheaper than the plan assumed: 580-2,880 dofs, 4.2 s/candidate (mesh 0.45 s, solve 4.15 s), 847 candidates/h => 1,000 evaluations = 1.2 h, 10,000 = 11.8 h. osse_baseline's seed alone is 3,850 dofs / 18 s (first solve, includes JIT).
What I need decided: item 1 (acceleration reading), items 4, 5, 6c, 7 as listed.

## 2026-10-13  task-09  Wave 3 senior rulings + CP-7 results (RESOLUTIONS, append-only record)
What I was doing: Wave 3 — the CP-7 physics gate (verifier lane, oracle) and the senior rulings over every open
NOTES_FOR_SENIOR block (rulings lane, oracle). Both ran; the user confirmed/adjusted the rulings. This block is the
durable record so no future agent has to re-derive any of it from chat.
CP-7 results (all PASS, pasted output in the verifier report, mirrored in docs/CONTINUITY.md):
  - CP-7a analytic sphere PASS: R(ka) spread 0.020 dB (<0.5), omnidirectionality <=0.005 dB, spreading 6.0205-6.0206 dB,
    convergence sub3/4/5 = 0.0204/0.0051/0.0013 dB (monotone). Acceleration-drive reading CONFIRMED (the raw
    24.06 dB/octave constant-velocity spread is expected, NOT a failure).
  - CP-7b two solvers PASS: beat_cuda vs bempp_cpu 0.039 dB overall (<0.2 dB).
  - CP-7c mesh convergence PASS on a REDUCED band 500-2500 Hz (quarter, symmetry) because the seed at epw=18 over the
    full band needs ~40k quarter dofs (OOM). GATE met: epw=6 vs epw=18 -> mean|dbw_h|=0.287 deg (<2), mean|dDI|=0.028 dB (<0.3).
  - CP-7d symmetry PASS: max asymmetry 4e-6 dB (imposed symmetry -> solver noise floor); M6 full-vs-quarter on the SEED
    = 0.023 dB (<=3 kHz).
  - CP-7e plausibility PASS (borderline): f0 = 343 Hz (H) / 480 Hz (V) from mesh bbox + measured beamwidth, both below
    the 500 Hz band floor; DI-vs-beamwidth max diff 2.15 dB (slightly over the 1.5 dB guideline, well under the 3 dB
    "computed wrong" threshold); f11 = 5653 Hz sits just ABOVE the clipped 5500 Hz band -> onset NOT resolved.
  - CP-7f noise floor = 0.039 dB (two-solver disagreement dominates; epw=6 DI discretization 0.028 dB just below it;
    idempotence 3.6e-5 and asymmetry 4e-6 are ~1000x smaller). Report's prior "0.055 dB, epw=6 unmeasured" is superseded:
    the floor is NOT mesh-limited and was already the floor.
RULINGS (each block -> outcome -> change applied):
  1. task-08 item 1 (acceleration drive) -> CONFIRM (no waiver; the absolute unit-acceleration match 0.016-0.036 dB is the stronger evidence).
  2. task-06 "-6 dB" half-pressure (-6.0206) -> CONFIRM.
  3. task-06 di_from_cuts clamp (bw>=180 saturation; both>=180 -> omni DI=0) -> CONFIRM.
  4. task-06 ripple ddof=1 (sample std) -> CONFIRM; the earlier tiling study's sigma convention is NOT recorded anywhere (evidence gap, no code change).
  5. task-06 small items -> CONFIRM: constants.py comment now says "throat diameter" (edited); coverage_from_room band kwarg ok; 512-pt DI quadrature bias (narrow-beam +0.23 dB) affects no gate.
  6. task-03 no YAML freq-grid key -> CONFIRM (grid shape is frozen; a user key would silently split the dataset label space).
  7. task-03 CP-1 test 3 angle step (18000 % (n-1) == 0) -> CONFIRM.
  8. task-03 ICW coverage_angle_deg -> CONFIRM HALF-angle (read from mesher source: theta0 < coverage_angle < 90); "UNCONFIRMED" removed from families.py + YAML.
  9. task-04 sectioned to_mesher_config -> CONFIRM (mesher silently ignores top-level max_triangles; tests pin it).
  10. task-04 vs task-03 mesh_spec -> OVERRULE: config.mesh_spec now calls sizing.max_triangles_for (single source, honours dof_per_triangle=0.51). EDITED config.py + docstring (was a 2% drift). Pass mode= to build_mesh -> CONFIRM.
  11. dof caps + band_hi lowered -> CONFIRM (user: "keep the lowered top band edges; override only with a smaller seed or fewer epw").
  12. task-04 midpoint-fill -> USER OVERRULED the silent fill for kappa0/theta1_deg: explicit seeds added to examples/icw_termination.yaml (kappa0 0.25, theta1_deg 16.0 keep geometry); the fill remains only as a defensive net (test rewritten: test_design_space.py).
  13. MeshConsistencyError taxonomy (not swallowed) -> CONFIRM.
  14. task-07 traces.sample_fraction / lib_shas=5 / one-npz-per-record -> all CONFIRM (phase-2 must use DatasetStore).
  15. task-08 raw terms + NAN_TERM_FILL 30.0; sin(theta)-weighted balloon DI; cache/resume/budget semantics; dataset record choices -> all CONFIRM; Target.freq_weights stays unused (contract defines the field with no semantics - gap).
Also applied: record.py excitation note now states the unit-ACCELERATION convention (user edit); new tests/test_mesh_pin.py (fails on a silent HornLab pin bump) and hornlab_search/mesh/grid.py + tests/test_mesh_grid.py (single seam over build_point_grid, issue #9).
RESIDUAL RISKS (recorded, NOT resolved - for phase 2 / post-Wave-3):
  1. epw=6 discretization above ~2.5 kHz is UNMEASURED (the epw=18 reference cannot be built there on this 8 GB card); a
     systematic epw=6 bias in the 2.5-5.5 kHz screening band would bias every ranking, and no test catches it.
  2. The higher-order throat mode f11 (5653 Hz on the 1.4 in seed throat) is never exercised - the screen band clips at 5500 Hz.
  3. DI-vs-beamwidth is NOT a regression test (only the analytic cardioid/dipole closed forms are); the real seed shows
     2.15 dB max balloon-vs-cuts difference, the known non-separable-rectangular signature.
  4. Secondary: the cross-run solve cache did not dedup the seed across separate `run` then `search` invocations (both
     cached:False), so the seed was solved twice and the dataset holds two seed records.
What I need decided: nothing blocking. Phase 2 (11_PHASE2_SURROGATE) is "separately and later"; post-Wave-3 follow-ups
(widen a_deg/exponent bounds, run the other 4 example configs for a multi-family dataset, browser-check report.html) are
the natural next work, not part of Wave 3.

## 2026-10-14  cp-8d (local GPU box)  Stage A train failed twice on real data: epochs 300 then 600; propose/round NOT run
What I was doing: CP-8d step 1 of the runbook — `surrogate train --config examples/osse_baseline.yaml` on the real OSSE
pool (all 8 gate inputs are real BEM records; 5 gate measurements per table). CPU-only torch.
What happened (exact gate tables):
- epochs 300:  spearman 0.96734 PASS | topk_overlap 5 (need >= 12 of 20) FAIL | bw_mae_deg 2.11007 (need < 2.0) FAIL |
  di_mae_db 0.28669 PASS | invalid_accuracy 0.85714 PASS | monotonic_flips 0 PASS. Held-out 285 (< 500). Exit 1.
- epochs 600:  spearman 0.98613 PASS | topk_overlap 15 PASS | bw_mae_deg 1.70415 PASS | di_mae_db 0.23190 PASS |
  invalid_accuracy 0.95238 PASS | monotonic_flips 1 (need == 0) FAIL. Same pool. Exit 1.
Both: pool considered 2034 (all OSSE-family records incl. throat_adapter), selected 1501,
skipped_grid_mismatch 533 (133 search_smoke-grid + 400 throat_adapter-grid records), skipped_bad_arrays 0,
1 duplicate dropped before the cluster holdout, objective delta (recomputed vs stored) 0 — zero weight/target drift.
What I tried: the runbook's own fix list in order — more epochs (300 -> 600: every measured gate IMPROVED, but
monotonic_flips went 0 -> 1); --lib-sha is moot (every record carries one lib_sha, b922e807a5+38544d214b).
`propose` / `surrogate round` were NOT run (runbook: propose only when gates pass; "do NOT use the model" otherwise).
Per hard rule 8 (failed twice on the same step): stopped and appended this block.
What I need decided: (1) approve the remaining runbook fix — an OSSE top-up of ~1900 records
(`search --config examples/osse_baseline.yaml --resume runs/20261013T123136Z-screen-ca15be --budget 1900`,
~10.2 h at the measured 187/h) taking the OSSE pool to ~3400 so held-out clears the 500 floor and the formal
gates can legitimately pass; (2) is monotonic_flips = 1 at 600 epochs expected sweep-boundary/validity-boundary
noise (the oracle's earlier reading of sweep_sign_flips' tolerance vs invalid-region crossings), or a genuine
model defect to fix in code (NOT by touching gates.py thresholds)? Repro command is the epochs-600 line above;
training is seeded/deterministic. (3) Should the built `surrogate round` helper ever be run as a clearly-labelled
DIAGNOSTIC on a gate-failed model, or stay unusable until a formal pass (current behaviour per the runbook)?

## 2026-10-14  cp-8d  ADDENDUM: monotonic_flips diagnosed - mixed causes; the gate is marginal (1-2 of 50), not a hard defect
What I was doing: answering this file's cp-8d question (2) with a read-only sweep replay on the saved epochs-600
bundle (no gates/code touched; throwaway script in temp; CPU only).
What happened (exact numbers): `sweep_sign_flips` seed 0 reproduces flips = 1/50. The flagged sweep (dim 0):
  y    = 18.0778, 17.0189, 16.4122, 16.4233, 17.1195, 18.2263, 18.5035, 16.9034, 1000, 1000, 1000
  p_ok = 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.996, 0.569, 0.021, 0.001, 0.0
  tol = 1.0 (INFLATED to 1 J by the 1000-penalty row scaling max|y|); kept diffs -1.06, +1.11, -1.60, +983
  -> sig [-1, 1, -1, 1] -> 3 sign changes -> flip. The zig-zag happens in the predicted-validity TRANSITION
  band (p_ok 0.996 -> 0.569): the metric predictions degenerate as the line approaches the invalid pocket.
Seed-stability (seeds 1-5, still read-only): flips = 1, 1, 2, 2, 2 of 50 every time. The flagged sweeps are
THREE distinct kinds: (a) invalid-transition degeneracy as above; (b) GENUINE model undulation on fully-valid
lines (p_ok >= 0.98 throughout): +1.35 J / +3.7 J shapes (seed 1 #6: 12.6 -> 15.3 -> 13.0; seed 3 #41:
10.4 -> 11.1 -> 10.0), 1.4-2.2 J (seed 4 #3) — real wiggles worth 10-30 % of the local y range; (c) tiny-wiggle
sensitivity: the tolerance 1e-3 * max(1, max|y|) lands at 0.021-0.023 J on near-flat tails, so +-0.05-0.3 J
undulations count as sign changes (seed 4 #30: 3 changes from wiggles all under 0.35 J).
What I conclude: the failure is NOT purely an invalid-boundary artifact — kinds (b) and (c) are real. The model
is slightly rough on valid lines AND the flat tolerance makes the gate marginal. Flip rate 2-4 % of sweeps; the
gate demands zero. Five of six gates have real margins; this one is a hair over.
What I need decided: (i) confirm "more data + retrain" as the fix for (b) — my recommendation, tied to question
(1) of the prior block (the ~10.2 h OSSE top-up); (ii) a ruling on the sweep-tolerance SEMANTICS for (c) — e.g. a
tolerance based on the sweep's LOCAL y-range rather than the 1e3-inflated global max — that is a gates.py
semantics change (NOT a threshold change) and gates.py is frozen, so it is the owner's call; (iii) whether (a)
should be reported as its own category (invalid-boundary crossing) instead of masquerading as a zig-zag.

## 2026-10-14  senior reviewer (cloud)  FREEFORM sculpt, hardening, mesher feature request, naming question

What happened: user asked (in chat, 2026-10-14) to unlock FREEFORM wall control points, file a wall-port feature
request, and harden before the local merge; user explicitly authorized edits outside phase-2 ownership for this.
Edits outside the reviewer's own paths, made on that authorization (each tested):
  - dataset/store.py (task 07): to_training_arrays read X with params.get(key), so FREEFORM search keys (paths such as
    profileH.points.2.1, and the 'exponent' alias) came back NaN; the surrogate then filled them with 0.5. Now resolved via
    families.param_get. Test: tests/test_dataset_store.py::test_freeform_path_and_alias_keys_fill_X (fails on old code).
  - search/evaluate.py (task 08): throat_radius_m returned None for FREEFORM (no r0_mm) so f11 was never computed; now
    uses anchor 0 of the two meridians (min). Test: tests/test_design_freeform_sculpt.py.
  - cli.py (task 08): new `compare <run_a> <run_b>` (report-only metric differences between two solved runs).
  - surrogate/features.py: unit_matrix raises on NaN instead of filling 0.5 (issue #13 item 10; not in local e0b9b61).
  - surrogate/train.py + cli.py: training refuses ok records whose di_source != 'balloon' (issue #13 item 5; not in
    e0b9b61); propose with 0 designs exits 1. Test: tests/test_surrogate_hardening.py.
  RECONCILIATION: the cloud's own F1-F4/F6/F7 duplicates were DROPPED in favour of local e0b9b61/11304f6 (what CP-8d ran
  on); branch ccr-455d2184-yj5zk4 was rebuilt on top of 622776a with only the non-duplicate items above.
  - examples/ (03/04): new freeform_sculpt.yaml + two symcheck configs. freeform_hv.yaml NOT touched (CP-8c run 3 uses it).
FREEFORM findings (cloud, real mesher b922e807a5 installed, mesh only, no solve):
  1. Dotted-path bounds into profileH/profileV points already worked in DesignSpace; "UNRESOLVED" in freeform_hv.yaml
     was about policy, not mechanics. freeform_sculpt.yaml searches 8 anchor radii + 2 mouth angles + the superellipse
     exponent (11 knobs). z, throat radius and throat angles pinned; anchor radius ranges disjoint and increasing.
  2. Mouth angle 40-90 deg failed 14/41 samples (outer-shell curvature guard at t~1); 35-70 failed 1/41; with throat
     angles pinned 41/41 mesh. Unpinned H/V throat angles trigger the mesher warning "throat tangent angles differ by
     more than 5 degrees; the circular source-cap transition may be inconsistent" -> pinned.
  3. FREEFORM is mirror-symmetric about both planes by construction, so quadrants "1" applies (mesher reports native
     symmetry yz+xz, build.py's check passes). freeform_hv seed: 710 quarter dofs vs 2655 full. freeform_hv.yaml's comment
     "FREEFORM H/V differ; full domain" is a misreading (H != V does not break the mirror symmetry) -- change it only
     after CP-8c and after the GPU symmetry check below. UNMEASURED: full-vs-quarter SOLVE agreement for FREEFORM
     (CP-7d was OSSE: 0.023 dB). Check: examples/freeform_sculpt_symcheck_{quarter,full}.yaml + `hornlab-search compare`.
     No pass threshold is frozen for this; the reviewer proposes "every dB metric max |diff| < 0.1 dB (the ~0.1 dB noise-floor
     scale named in 11_PHASE2_SURROGATE section 3) and beamwidth within 1 deg" as a provisional bar -- USER/SENIOR TO RULE.
FEATURE REQUEST for the mesher author (do not modify the mesher; rule 1): wall ports / side entries (holes in the horn
wall feeding secondary drivers, as in multiple-entry horns such as JW Sound's Solana). The mesher has no such feature,
so multiple-entry designs cannot be modelled. Needs: port position (z, phi), size, shape, and a separate source tag per
port so BEAT can drive it.
NAMING QUESTION (unresolved, flagged by the user): docs call the HornLab author "Collin"; the packages live under GitHub
user m3gnus and the user refers to the author as Magnus, and says a different person (Colin) proposed the NN surrogate.
docs/plan/** is frozen; a correction must go in a non-plan doc. Who is who: USER TO CONFIRM.
What I need decided: (a) the FREEFORM full-vs-quarter bar above; (b) the naming correction.

---

## 2026-10-22  orchestrator-merge-lane  main FF to cloud tip 6d1d5c7; GPU-run summary layer committed
What I was doing: senior inventory of remote branches/PRs (Hornfab; Hrns repo is empty and holds nothing), then sandbox-merge of the Claude Code cloud branch ccr-455d2184-yj5zk4 (6d1d5c7) into main and push.
What happened (exact output): fast-forward 2a7bafb -> 6d1d5c7 (22 commits, +10601/-44... see commit msg); oracle pre-merge review: SIGN OFF (152a829 correct/additive, chain clean, nothing lost: git log --all --not 6d1d5c7 empty); sandbox worktree at 6d1d5c7: compileall clean, pytest 533 passed / 0 failed (436.9 s).
What I tried: normal FF merge only (strict ancestor), no rewrites; PRs #12/#14 closed as superseded.
What I need decided: (a) whether to delete the merged remote branches (claude/wave-3-... and ccr-455d2184-yj5zk4) now that main contains them - defaulting to KEEP; (2) Boundary Lab 0.5.0 integration plan (PROPOSED, docs/BOUNDARY_LAB_INTEGRATION_PLAN.md) awaits user approval; (3) oracle follow-ups recorded in ISSUES 2026-10-22 (compare empty-freqs edge, exponent alias first-station doc note).
NOTE: user-approved exception committed - docs/evidence/runs/ holds the summarized layer of all 7 GPU run dirs (108 files ~16.6 MB + manifest; designs/ raw blobs remain gitignored).

## 2026-10-22  senior reviewer (cloud)  Boundary Lab learnings: edits outside own paths (user-authorized)

User authorized (chat, 2026-10-22: "make these changes in the cloud ... merge into local") edits beyond phase-2 ownership:
- task 04: `mesh/build.py` (read_msh_summary return_arrays; topology checks after read-back and on cache hits), NEW `mesh/topology.py`, `tests/test_mesh_topology.py`.
- task 05: NEW `solve/phasor.py`, `tests/test_solve_phasor.py`.
- task 06: NEW `metrics/spinorama.py`, `metrics/beam_shape.py` (+ tests; written by a Sonnet subagent, reviewed and wired by the reviewer).
- task 08: `search/evaluate.py` (`directivity_extras`, report-only scalars), `search/rundir.py` + `search/cma.py` (runtime provenance), `report/html.py` (one line per design), `tests/test_search_directivity_extras.py`, `tests/test_search_provenance.py`.
Rulings requested: (1) early rejection policy (BL_LEARNINGS s2 item 4) before any implementation; (2) whether `beam_p_mean` / `spdi_*` should ever enter J (reviewer: NO until a verify-resolution balloon validates p).

## 2026-10-24 (orchestrator, senior pass M4 recon / exp-1): point-grid curl acceptance — VERDICT + closure route

Question (WP9b 9b.3 step 3, "first thing to test"): does the pinned mesher's point-grid builder accept a
profile that turns back on itself? Probe `C:\Users\hunte\Hrns\AppData\Local\Temp\opencode\grid_curl_probe.py`
(offline, CPU/gmsh only; explorer lane), exact Le Cleac'h march (jmlc_reference.py), fc 800 Hz, T 0.8, 1"
throat (D_mm 25.4 = DIAMETER), phi0 5 deg half-angle, n_phi 25 quarter rows, dl 1 mm.

- **VERDICT: YES — self-turning (non-monotone x) profiles build. No fork mesher change for acceptance.**
  stop 200 deg: rollback 24.80 mm, OK 0.21 s, 232 verts / 396 tris; stop 240 deg: rollback 29.58 mm, OK
  0.24 s, 243 / 417; monotone control (stop 90): OK 0.90 s, 191 / 322. Surface authoring has no monotone-z
  assumption: `_validated_grid` checks shape/finite only (point_grid_surfaces.py:622-630), bspline patching is
  chord-based (_occ.py:74-101, 528-580), postprocess handles non-monotonic point grids (mesher.py:509-512),
  rollback-aware open-shell orientation in normals.py:80-134.
- **BUT the literal WP10 call is NOT BEM-usable**: `closed=False, symmetry_planes=("x","y"), no outer_points`
  resolves to BARE mode (inner wall + throat cap only; build_mode at geometry.py:322-330) and
  `mesh/topology.check_surface` rejects it for control AND curl (open mouth rim off symmetry planes). This is
  a closure-mode issue, not a curl rejection.
- **Working closure route: FREESTANDING with explicit `outer_points`** (in-plane normal offset of the profile
  by wall_thickness_mm, per Fourcade eqs 28-29: x_d = x + t*cos(phi+90), y_d = y + t*sin(phi+90)) — both
  curled stops build AND pass bbox + yz+xz symmetry + topology (200 deg: 432 verts / 768 tris; 240: 526 / 952).
  `wall_thickness_mm` alone does NOT synthesize an outer shell (point_grid_freestanding.py:283-284 raises
  without outer_points) — WP10 must build the offset grid as the plan's step 4 says.
- infinite_baffle closure (tag 12 mouth_aperture) refuses a rollback: "mouth ring to be the front-most z
  station ... protrudes through the baffle plane to z=24.7959 mm" — curled horns must use freestanding.
- Caller contract measured: `PointGridHornGeometry(inner_points=P_mm (n_phi, n_s, 3) phi-major,
  closed=False, symmetry_planes=("x","y"), wall_thickness_mm=3.0, source_shape=1 (rounded cap),
  source_auto_angle_deg=phi0)` + `build_mesh_with_info(geom, MeshDensity(throat_res_mm, mouth_res_mm,
  rear_res_mm, max_triangles, allow_large_mesh), output_path=..., scale_to_metres=True)`; import
  PointGridHornGeometry/MeshDensity from hornlab_mesher.geometry (not top-level). jmlc_reference returns
  METRES while the grid wants MM (x1000); row k = same arc-length fraction l/L0(phi) for all phi.
- Freestanding outer-ring quirk (non-blocking, candidate future FORKS note): `_outer_wall_axial_ring_indices`
  (point_grid_freestanding.py:116-128) drops rings at the max-z plane = the 90-deg station for a curl, leaving
  a ~1-station chord in the outer return wall there; it still builds and passes topology.
- Self-approach margins measured: min true distance 19.6 mm (200 deg) / 18.5 mm (240 deg) — plan's refuse line
  (2t + 2 mm = 8 mm at t=3) leaves generous room; quality gate "report" flagged 8 slivers (~1%) at
  mouth_res 12 mm (min angle ~5.4 deg) — a quality review/finer mouth res is advisable for T1-T7 configs.
- Installed mesher == fork pin b922e807 (65/65 files byte-identical). Repo bbox band is [0.02, 5.0] m
  (mesh/build.py:37-38), not the plan's 0.1-1 m wording.

## 2026-10-24 (orchestrator, M2 fused-CUDA pass): flag-off CUDA solves are NOT bit-deterministic — even on the base pin; WP15 determinism test rebarred with evidence

Finding during `tests/test_solve_beat_fused_cuda.py` (M2 work order step 3): test 2 asserted
`np.array_equal` (zero tolerance) for two back-to-back flag-off solves of the same spec. It FAILS on the
fork @ fa99ee5 with max |d spl_h_db| ~9e-8 dB — and identically (max ~1.6e-7 dB, same assertion) on the
BASE PIN 38544d2 after a `pip install --force-reinstall` rollback (`runs/m2_fused_cuda/fused_gpu_test.log`,
`runs/m2_fused_cuda/det_check_base_pin.log`). The CUDA assembly/solve runs Float32 with order-varying
reductions: ~1e-7 dB (one float32 ulp at these levels) between identical requests is upstream physics,
pre-existing, not introduced by the fork (the ladder A/Bs, old-vs-new runs days apart, show the same
~1e-6 dB floor). NOT rule 8: diagnosed in one pass with the base-pin reproduction.

Action taken (rule 7 evidence trail): the assertion was replaced by a documented floor
`max |d spl_h_db| <= TOL_DET_DB = 1e-4 dB` with a `[measured]` print of the actual diff
(test_solve_beat_fused_cuda.py::test_flag_off_reproduces_itself_from_a_clean_host; docstring carries
both measurements). 1e-4 dB is 3 orders above the measured floor and ~400x below the CP-7f A/B bar
(0.039 dB), so any real path/cache/host mixup (full-dB moves) still fails. Oracle to adjudicate.

Harness calibration note (fixer lane): the TOOLCHAIN M1 res->dof table came from a SMALLER horn;
`examples/osse_baseline.yaml` seed at quarter 3/1.5 mm meshes to 87,240 tris / 43,993 dofs. The M2
ceiling sweep therefore calibrates mouth-res per target (6.72/5.74/5.02/4.45/4.06 mm for ~8.9k/12k/
15.7k/20k/24k quarter dofs), verified by `--mesh-only` probes (6.655 -> 17,894 tris / 9,117 dofs).
Harness: `tools/measure_fused_ceiling.py`.

## 2026-10-25 (orchestrator, M4 pass): Le Cleac'h stays BLOCKED under R9 (owner ruling) — candidate source on record; nothing improvised

What happened: the M4 work order blocks `lecleach` (T1) — "no implementation without a human-supplied verifiable
published construction reference; the ETF PDF/threads are not usable" (owner ruling 2026-10-25). Per the pass
order this block records the CANDIDATE SOURCE found in the senior-pass research, without acting on it:
Fourcade 2015, "Calcul du Pavillon Le Cléac'h" (16 pp., French;
`unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf`) — construction eqs 10–27, the JMLC 2007
spreadsheet recurrence (eqs 1–8), the offset-profile formula (28–29), and a numerical reference case (fig. 7 +
table p.13). Report 4 §9b.0 scored it "primary/secondary, verifiable; this satisfies the R9 gate", and §9b.2's
validation table (fc 400 Hz, T 0.8, throat Ø25.4 mm, exit half-angle 8°, dl 1 mm, c 344 m/s; L0/S(L0)/width
rows, our reference implementation's numbers quoted) is the ready-made comparison; the known open item is the
0.9 % width gap (9b.2). What I need decided: (a) does the owner accept the Fourcade PDF as the R9 reference
(if yes: T1 `lecleach_exact` may ship in a later pass after the ±2 mm/±2 %/±1 % validation table passes);
(b) whether the owner then also names the 0.5-mm rename gate satisfied (Report 2 §3) vs keeping `spherical_salmon`.

## 2026-10-25 (orchestrator, M4 pass): OWNER DIRECTIVE closes the R9-Le Cleac'h question — lecleach SHIPPED LIVE after R9-J PASSED

Superseeds the block above (kept for the record). Later the same day the owner directed in chat — verbatim:
"I don't really care about the authorship I just wanted to be right and I will definitely want to use it ... I
want to integrate this" — accepting the Fourcade 2015 PDF as the verified construction and waiving the
attribution formality, with the verification bar intact. Actions taken (all in this pass, pre-commit):
(1) librarian lane FETCHED the Fourcade PDF and read fig. 7 with its inputs — finding the senior plan's
§9b.2 premise bug: the 8.0 deg exit is the INCLUDED angle, so phi0 = 4.0 (the 0.9 % width "open item"
closes at exactly 0.00 mm discrepancy; dated corrections in `docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md`).
(2) `lecleach_exact` (exact Fourcade eqs 10–27/42–43) implemented and routed only after the R9-J gate test
PASSED in-lane: width 467.30 mm vs published 467.30 (0.00 mm), 2phi1 8.552 vs 8.55 deg, L0 within ±1 mm
(512/511 at 360 deg), mouth areas ≤1.31 %, length +0.44 mm (`tests/test_design_generators_lecleach.py`).
(3) Rollback ships via the WP10 GRID rows route (stop 120–240), FREEFORM ≤88 deg interim; `spherical_salmon`
(own neutral march) ships as a separate distinct generator. Answers to the two questions above: (a) YES —
Fourcade accepted (owner directive + fetched PDF); (b) BOTH ship: `lecleach` (verified exact) and
`spherical_salmon` (different construction, neutral name). GUI/`__init__` staleness fixed; old gated-stub
`examples/typologies/lecleach.yaml` deleted. Note: the earlier same-day "stays BLOCKED" text in the
`WP9_WP9B_GROUNDING` dossier §5 records the pre-directive state; a dated supersession note is appended there.


## 2026-10-25 (GUI-integration orchestrator) - OWNER DIRECTIVE: ALL CAD work STOPPED + DEFERRED (GUI-only round)

Owner in chat: "stop that agent ... do not work on CAD shit right now -- only touch files related to
the GUI itself." Scope note: this session is GUI-only (hornlab_search/gui/ + GUI tests + GUI docs); the
backend M5/M6 stream belongs to the parallel orchestrator session -- its live CAD/back-end edits in
config.py / design/families.py / mesh/build.py are NOT mine and were not touched; stopping THAT stream
requires its own orchestrator/owner (please read this note).

Deferred items (from my cancelled fixer lane, design finished, code REMOVED from the working tree to
keep file diffs lane-pure -- nothing lost, re-implementable from this note):
1. CAD STEP inventory mapping in run_detail -- step_files_detail[i].inventory should resolve: a
   `<name>.inventory.json` sidecar WINS when present; else `designs/<hash>/mesh_meta.json["cad"]`.
   The cad block's REAL key names (read from mesh/step_build.py at the M5B landing): face_inventory
   = {"driver": 1, "wall": N} (NOT "inventory"), tool_sha256 (NOT tool_sha), tool_path, solid.solids,
   solid.all_shells_closed. Only-present-fields -> {faces: [{label, count}], solids, closed,
   tool_sha256, tool_path}. STEP filename -> design hash via regex `_rank\d+_([0-9a-f]{6,40})\.step$`.
2. cad_route solve-group marker -- the cad recipe is PER DESIGN (Design.params["cad"]; config.yaml
   carries none), so the run-level proxy is the best-objective row's mesh_meta.json["cad"] block
   (seed row if nothing succeeded) -> solve_group.cad_route: true (only-when-non-default).
   Consumers planned: G4 STEP chips + a "cad STEP" G1 badge (both render automatically whenever the
   reader emits them).
3. cma_files run_detail key (NOT CAD -- deferred only because data.py was co-edited): list every
   pycma log the C-5 route serves (top-level cma/ + each cma/restart_k/, CMA_LOG_NAME-matched,
   {path (run-relative), name, size}, sorted) -> restart-card DIRECT file chips in app.js. A full
   working implementation existed and was removed with the sweep; trivial to restore.
4. source_profile_alpha pin test only remaining -- the solve-group fingerprint ALREADY picks up
   solve.source_profile_alpha from the M5B config (real runs badge "source plug a=..." automatically);
   only the dedicated fixture test was pending (NOT CAD-related; queue with the next GUI pass).

Everything above is GUI-side display work over committed M5B artifacts -- zero solver/mesher changes.
Deferred at owner direction 2026-10-25; resume whenever the owner lifts the CAD hold.

## 2026-10-25 (GUI-integration orchestrator) - TODO: denser balloons + denser frequency grids on
higher-tier runs (W7 in docs/NEXT_DEV_PRIORITIES.md; research basis 12_RESEARCH_BASIS.md section 12)

Owner priority 2026-10-25: raise verify/final-tier data density toward Boundary Lab-class fidelity.
BL reference numbers (docs/research/boundary_lab_0.5/bl_inventory.md): balloon_angle_precision_deg
default 2.5 deg clamped 0.5-15; equal-area Fibonacci point count = round(41253/angle^2) (~6,600 points
at 2.5 deg, ~41,253 at 1 deg); freq_count 41 log-spaced 200-20,000 Hz; spherical DI =
-10*log10(mean(10^(SPL_rel/10))) over that equal-area balloon (a plain mean ONLY because the sampling
is equal-area). Our targets: solve.balloon_points_verify from the M3/WP5 512->1024->2592 ladder into
1,000-6,600; verify-solve frequency count from 25 toward ~41 log-spaced (grid.verify_points_per_octave
/ a NEW named grid group per the W3 contract rule if the solve-spec hash changes). Gates: the M3/WP5
measured delta-DI ladder decides how much density buys accuracy; GPU cost -- balloon points bill field
evaluation (not dofs), freq count bills linearly per solve; stays OFF the 8 GB 4060 search tiers
(screen keeps 12 freqs / light balloon). Feeds the W6 web Balloon view: its sin(theta) unequal-area
layout must be interpolated on the sphere, not the index grid, at any density. Full write-up:
12_RESEARCH_BASIS.md section 12 (owner-directed appendix; BL source recon; GPL-3.0 attribution carried).

2026-10-25 (owner-directed diagnosis + record request): why the puckered/figure-8/bullet outline
shapes never appeared in the owners own search passes, and how the machinery actually works.

The owner asked: I thought the software randomly tweaked knobs with a GA and could reach those shapes without
layers - why have I never seen them? Answer recorded verbatim-detailed in 12_RESEARCH_BASIS section 13.8 +
P8 in NEXT_DEV_PRIORITIES. Compact form:

1. The owners mental model is correct: ONE CMA-ES run, all knobs as simultaneous genes, sampled inside the
   configs bounds, scored on balloon/beamwidth/DI - no layering is needed. The shapes knob families exist
   (the per-azimuth stop/fc harmonic laws, the G8/G9 terms; and the 2026-10-25 additions: signed x_amp,
   the odd-cosine eps_m (full ring), the even-lobe mouth ripple).
2. Why the passes still returned smooth shapes, three stacked causes (all measured 2026-10-25):
   (a) the coverage terms equal-weight mean over the screen band let the physically-uncontrollable low band
       dominate (61-87 percent of cov loss below the K-law break; dislope took another 30-42 percent) - the
       search could not reduce it and optimized the wrong margins instead. FIXED 2026-10-25: objective v3
       (the below-f0 mask + freq-weighted cov) + the K-law feasibility preflight recorded per brief.
   (b) every shipped typology seed sat at x_amp/bend/ripple = 0 with tight bounds: a short screen run is a
       seed lottery around a smooth seed (40-110 evals never reach a figure-8 outline combination).
   (c) no objective term reads the 45/135-degree diagonal directions where the puckered outlines act (the
       balloon stores them; P8b is the pending scoring decision).
3. The collaborators staged-gene document (verified against Tritonia/seg-horn primaries, section 13.7) is an
   OPTIONAL refinement (two sequentially-seeded campaigns), never a requirement; recorded as the owners
   direction: no layers.
Investigation items: P8a pucker-hunting demo campaign; P8b the diagonal-consistency term (owner
decision pending); P8c the Tritonia-law rows kind + the segmentizing genes; P8d the GUI surfacing.
Also recorded 2026-10-25: three writing-hygiene incidents this session (two chat-prose pastes into
config.py/12_RESEARCH_BASIS tails; one eaten section header twice) - all caught and repaired same-turn;
lesson: NEVER anchor an edit on a section HEADER alone; re-run section-header greps after every
doc-structure edit (the 13.6/13.7/14 header greps) and byte-check tails after appends.

## 2026-10-25 (later) - S1a driver pass: oracle decision record + the owner's over-constraint remark (append-only pointer)

The owner directed an oracle decision pass for the typology-completion repair (briefs, per-config
parameters, driver classes). The complete oracle output is preserved verbatim in
`docs/research/typologies/S1A_DRIVER_PASS_ORACLE_FINAL_2026-10-25.md` (provenance header + the
full decision tables, brief YAML texts, derivation hunks, validation plan, risks ledger); the
applied state is documented in `docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md` + the research basis
S16.9 pointer + the smoke-matrix evidence addendum. Decisions applied: brief-driven driver classes
({hifi_90x60, organic_rollback, lecleach_rollback} x {1in, 14in, 2in}, all f0 + objective v3);
biradial seed L 195 + closure-aware derivation (rm = max(K-law d/2, r0 + tan(a)L), the ONE
owner-directed widened_to_closure exception to clamp-only — dated in config.py, flagged per note,
test-pinned); the salmon demos reseeded (stop 150, x_amp -0.15 — the 180 deg cap-area asymptote
was crossed at the shipped seed) + lecleach eps 0.20 onto its own family brief; C4 catalog landed.
**Owner remark on record:** the owner believes some min/max parameters may still be OVER-CONSTRAINING
the designs — deliberately deferred to a later round (not acted on; the landed bounds are the
oracle's measured decisions). Anyone revisiting bounds must start from the oracle doc S1/S5 tables
and re-measure, not widen by hand.

## 2026-10-25  orchestrator (GUI param-reference / typology-sandbox pass)  CONTRACT GAP: there is no parameter reference — GUI knob tooltips have no source, and the three typology vocabularies are unjoined

**Status: PROPOSAL ONLY.** Nothing was started; no code, config, bound, or frozen file was touched. Owner directive: record it, do not implement it. Filed as `docs/NEXT_DEV_PRIORITIES.md` **P9** and mirrored in `docs/ISSUES.md`.

**What I was doing:** scoping three owner GUI asks that arrived together — (a) hover descriptions of every parameter on the Run page and the Typologies page, (b) a clickable per-typology sandbox page with manually draggable knobs, live H/V wall section + live 3D, parameter name beside each slider, editable min/max on both sides, and "save as this typology's default min/max", (c) one findable source of truth for typology → design → formula → parameter → min/max → design characteristic → the code that implements it.

**What happened (all verified this pass):**

1. **No geometry-knob description layer exists anywhere.** `gui/static/glossary.js` defines objective/metric terms only; it contains **zero** geometry-knob entries. `gui/static/app.js` carries labels/hints for the brief fields only (`coverage_h/v_deg`, `band_*`, `envelope.*`, `driver.exit_radius_mm`, `driver.exit_angle_deg`, `throat_angle_policy`). The only accurate parameter prose in the tree lives in **code docstrings** (`design/generators/profiles.py`, `grid.py`, `registry.py`) and in the research docs. So ask (a) has no existing source to render — the copy must be authored once and then owned.

2. **Three typology vocabularies, no join.** 4 mesher families (`design/families.py` `FAMILY_KEYS`), 11 generator types (`design/generators/registry.py` `TYPES`), 36 catalog ids (`examples/catalog.yaml`, counted this pass). The GUI's Typologies page speaks catalog ids; the code speaks families/generator types; nothing maps between them. `docs/CODE_MAP.md` maps modules, not *typologies*, so neither a user nor an agent can get from "salmon_elliptical" to the code that builds it without reading four files.

3. **Knob names are overloaded, so a per-name reference would emit WRONG tooltips.** Verified overloads: `n` (OSSE superellipse termination exponent vs biradial flare-rate exponent, claim 14 `[2,8]`); `q` (OSSE termination saturation ≈0.995 vs R-OSSE blend exponent 1.0); `a_deg` (OSSE coverage half-angle vs biradial initial-wall half-angle, which has its own default 25 in `registry.py`, vs QTW half-dispersion angle); `T`; and `stop_deg` vs `max_wall_deg` — `registry.py:37-38` already records, from the 2026-10-25 R9 audit, that `spherical_salmon` uses `{p}_max_wall_deg` and **not** `{p}_stop_deg`. Any reference keyed on knob name alone is unsafe; it must be keyed on `(catalog typology, knob)`.

4. **One open doc/code mismatch, not to be resolved by a lane.** `docs/plan/12_RESEARCH_BASIS.md:158` states the superellipse cross-section `exponent` default as **2.0**; `registry.DEFAULT_KNOBS["mouth_exponent"]` is **4.0** and the shipped configs use 4.0. `families.py` only imposes the hard `[2,16]` limit. No source wins on its own.

5. **The bounds question is already load-bearing elsewhere.** `examples/typologies/*.yaml` `bounds:` are what the run page's "parameter limits" bars display, W8 exists precisely because those boxes bind designs at their ceiling, and this file already records the owner's remark that some min/max values may still be over-constraining. Ask (b)'s "save as default min/max" therefore edits a surface the search depends on, not a cosmetic slider range.

6. **Observed GUI defect, exact anchor:** on the search time-lapse page the `3D` checkbox renders **checked** while the canvas prints `3D off — flip the 3D toggle above.` Either the control's visual state is not the state the render path reads, or the render fails and the off-state placeholder is reused instead of an error state. Recorded as a defect (not diagnosed — the code-map lane was still running).

**What I tried (analysis only, no writes):** designed the reference as an **annotation layer over the existing authorities** rather than a new table of numbers, because a hand-written master table would become a fourth stale copy and would collide with `AGENTS.md` line 29 ("Every horn number is a YAML default in `examples/` — hardcoded horn numbers are bugs"):
- hard limits read from `families.KeySpec.lo/.hi` (which `families.py:12-13` defines as schema limits only);
- defaults read from `registry.DEFAULT_KNOBS`;
- bounds read from `examples/typologies/*.yaml`;
- prose/formulas derived from the existing docstrings and dossiers, never newly invented (hard rule 3);
- the doc (`tools/gen_param_reference.py` → `docs/reference/PARAMETERS.md`, `TYPOLOGIES.md`) **generated**, with symbol-anchored code refs;
- a FAIL-not-warn drift test so metadata cannot silently diverge from `DEFAULT_KNOBS`, `KeySpec`, the catalog, or the code symbols.
Proposed precedence for the sandbox sliders: hard `KeySpec` clamp (always wins) → `examples/typologies/*.yaml` bounds → a user-saved override **outside** `examples/` → session tweak.

**What I need decided:**

1. **Package location.** `hornlab_search/design/params/` (next to the code it annotates; one copy for GUI + docs + tests) vs under `gui/` (import-light, but the GUI would own design facts). I recommend `design/params/` with an import-light `__init__` (no mesher/numpy/search imports, never raises on an unknown typology or knob).
2. **What "save as default min/max" is allowed to write.** Two very different things: (i) a **non-authoritative personal preference** in a user-scope file that only the sandbox respects, or (ii) an **owner-gated edit to `examples/typologies/*.yaml`**. Hard rule 3 and the "horn numbers are YAML defaults" rule point at (ii) requiring your explicit sign-off and per-config measurement under W8 — never a GUI side effect. Please rule on which, and if (ii), the approval path.
3. **Does the sandbox render designs the search would reject?** If a user drags a knob outside the brief envelope, does the sandbox refuse, or render with a visible "outside envelope" marker? The run page already has established at-limit language (red marker = pressed against a limit); the sandbox should reuse it rather than invent a second vocabulary.
4. **Which `exponent` default is canonical** (2.0 prose vs 4.0 shipped) — needed before that knob can carry a tooltip that states a default.
5. **Scope confirmation.** I did not enter W8, did not touch any bound, and did not open the frozen plan. If P9 should also produce the generated reference doc in the same pass as the GUI tooltips, say so; otherwise the doc is the cheap first slice and the GUI consumes it afterwards.




## 2026-10-26  task-05  runtime cuda_oom: beat_cuda CUDA out of memory
What happened: RuntimeError('Out of GPU memory trying to allocate 660.150 MiB\nEffective GPU memory usage: 100.00% (7.996 GiB/7.996 GiB)\nMemory pool usage: 15.965 GiB (15.969 GiB reserved)\n') on C:\Users\hunte\AppData\Local\Temp\opencode\pass40\rungs\mesh_635\mesh.msh (n_triangles=18236, n_dof=None, quadrants=1)
What it means: the dof cap in TOOLCHAIN.md / the YAML is wrong for this GPU state (or a stale Julia host held VRAM; run solve.worker.clear_stale_hosts and re-test from a clean state before changing the cap, AGENTS.md hygiene rule 7).
(Appended automatically by hornlab_search.solve.base.note_failure_for_senior.)

## 2026-10-26  task-05  runtime cuda_oom: beat_cuda CUDA out of memory
What happened: RuntimeError('Out of GPU memory trying to allocate 631.512 MiB\nEffective GPU memory usage: 100.00% (7.996 GiB/7.996 GiB)\nMemory pool usage: 15.889 GiB (15.906 GiB reserved)\n') on C:\Users\hunte\AppData\Local\Temp\opencode\pass40\rungs\10k\mesh_500\mesh.msh (n_triangles=17832, n_dof=None, quadrants=1)
What it means: the dof cap in TOOLCHAIN.md / the YAML is wrong for this GPU state (or a stale Julia host held VRAM; run solve.worker.clear_stale_hosts and re-test from a clean state before changing the cap, AGENTS.md hygiene rule 7).
(Appended automatically by hornlab_search.solve.base.note_failure_for_senior.)

## 2026-10-26 objective v3 amendment (Phase 0 item 2B, impl-code2)
objective v3 amendment 2026-10-26: optional per-plane f0_v_hz, owner-directed. `target.f0_v_hz` (appended after `f0_hz`; Target stays positional) masks the vertical coverage error to f >= f0_v_hz while the horizontal error keeps f >= f0_hz; cov is the sum of the two masked means (freq_weights restricted per mask). `dislope` keeps the H/f0 mask. Absent = the pre-amendment expression verbatim, bit-identical (config_sha / seed hash / solve-spec hash / J pinned). Validation refuses f0_v_hz < f0_hz or > band_hi_hz with a message naming target.f0_v_hz. `docs/plan/01_CONTRACTS.md` is frozen and was not edited.

## 2026-10-26  campaign-bounds audit (orchestrator)  campaign search boxes are narrow by construction; owner flags wider over-constraint
What I was doing: reviewing the 23 campaign cells authored by the BRIEFS lane against the handoff's own
PASS gate ("mouth within 10 % of the brief's K-law mouth"), to answer the owner's question of whether
the boxes leave the solver enough room.

What happened (measured by reading all 23 configs in examples/typologies/campaign_2026-10-26/):

| cell | searched dims | pinned | narrowest searched windows (relative width) |
|---|---:|---:|---|
| b1w__biradial_keele | 7 | 0 | v_rm 4 %, h_rm 4 %, L 5 %, h_a 11 % |
| b2w__hyb_osse_h_hypex_v | 5 | 0 | v_rm 4 %, h_a 14 %, L 16 % |
| b3a__lecleach_rollback | 3 | 0 | g_T 2 %, g_fc 16 %, g_stop 20 % |
| native__lecleach_rollback | 3 | 0 | g_fc 18 %, g_stop 25 %, g_T 40 % |
| b1t__rosse_morph | 17 | 3 | morph_width 7 %, morph_height 6 %, aspect 9 %, R 10 % |
| b1t__lecleach_iwata_ar | 5 | 0 | g_ar_m 12 %, g_T 17 %, g_fc 17 % |
| b3a__ath_core_14in | 15 | 5 | q 1 %, morph_w/h 7 %, a 12 % |

Across all 23 cells: 3-17 searched dimensions, 0-6 pinned, and many narrowest windows sit at 2-12 %
relative width. Cause: the 10 % K-law PASS criterion forces the mouth knobs to ~+/-10 %, because
mouth ~ K/fc (rows) and mouth ~ f(R) (R-OSSE). The narrow bounds are a consequence of the acceptance
gate, not of the lane improvising. Structural constraints (cannot widen without breaking the brief):
driver pin r0 18.0; the envelope; the 10 % gate; morph_target pinned (categorical gene, measured
15.8 % flip rate). Discretionary constraints worth flagging: morph_width/height at 5-7 % means the
Morph A/B can barely morph, so it may UNDERSTATE Morph's value; 3-dim JMLC cells with g_T at 2 %
effectively fix T; biradial/hypex rm at 4-5 % means those cells tune angles/depth only.
Why narrowing was defensible: the audit lanes measured heavy invalidity outside these windows
(salmon_x_signed 24-41 % envelope refusals even inside recommended boxes; biradial closure guard;
saddle 22.7 s/candidate). Wider boxes mostly buy invalid candidates.
What decides it: the Step-5 LHS invalid-% per cell (in production at time of writing). ~0-10 % invalid
means widening is affordable; 25-40 % means the window is justified.
Consequence for interpretation: results read as "best each family achieves inside a buildable envelope
near the K-law mouth", not "what the family can do". Cross-family J spreads will be small and
comparable to seed noise, which makes the >=3-seed / pooled-variance rule load-bearing before any
"family A beats B" claim.

Owner's broader observation (recorded as stated): through their own testing, a lot of the CURRENT
minimum/maximum parameter values in the shipped configs are already somewhat over-constrained and
have prevented the solver from finding more. This campaign inherits that tendency, and its narrow
boxes make it visible.

What I tried: nothing changed. The BRIEFS lane was still running; by owner instruction no changes were
sent to it and no file of its was edited.

What I need decided:
1. After the smoke night: an explicit over-constraint audit of the shipped KeySpec/bounds (which lo/hi
   are physical vs arbitrary), using per-cell LHS invalid-% as the widening evidence; widening stays
   owner-gated per the plan's rule ("never widen a box to make results look good").
2. Whether to add a small EXPLORATION set (wide boxes, no 10 % PASS gate, excluded from the per-brief
   comparison leaderboards) instead of loosening the 23 comparison cells.
3. Whether the 10 % K-law gate should itself become a per-cell knob (10 % for comparison cells,
   ~25 % for exploration cells), so the PASS criterion and the bounds cannot drift apart again.

(Uncommitted at time of writing; append-only block, stage with the next docs commit that touches this file.)

## 2026-10-26 senior pass learnings
See docs/research/LEARNINGS_2026-10-26.md (Ath crease mechanism, over-constrained boxes, per-type scoring, driver realism, fused ceiling). Build on it rather than re-deriving.

## 2026-10-27 objective v4 implementation (orchestrator)
Files outside the usual ownership touched by the owner-directed v4 pass: `hornlab_search/metrics/diagonal.py` (new; 45/135 deg beamwidths from the balloon, pure numpy/scipy), `hornlab_search/config.py` (`_validate_objective_block` accepts v4, `Config.objective_params`, penalty-ordering refusal at load), `hornlab_search/search/evaluate.py` (dispatch table gains 4; scorers take the validated `V4Params`), `hornlab_search/objective/versions.py`. `tests/test_dataset_record.py` and `tests/test_config.py` each had one assertion updated because their subject changed (4 is now a supported version; `objective_params` is optional like `grid`); no tolerance loosened. v1-v3 behaviour and config hashes are unchanged.

## 2026-10-27 (late) owner concern: do the sims behave like a built horn? (orchestrator, append-only)
Owner: "I don't want to be running these simulations if it isn't going to behave like it would if we built one and tested it." Investigation is queued as **P12** in `docs/NEXT_DEV_PRIORITIES.md` (read it first). Summary for the senior pass:
- **Loading is weighted only on b3bt/b3bw/native_lecleach** (0.5, z_min 0.7). The J 1.31 best horn (`b3a__rosse_morph`, b3a brief, load weight 0) has Re z_throat 0.04-0.12 below ~830 Hz and only fully loads near 3 kHz, with excellent-looking polars from 500 Hz up. `load_term` is a whole-band mean (diluted) and the screen grid starts at 500 Hz.
- **Ideal source:** `solve/beat.py` drives unit normal acceleration on tag 2 and normalises polars to on-axis; no driver model, so level/efficiency/excursion/cutoff peaks of a real compression driver are not modelled and poor loading is invisible to the pattern terms.
- **Scoring generosity (v4 as shipped):** cov is `err^2/100` with tolerances 2.0/4.5 (about 14/21 deg RMS per unit); cov masked below f0 for class A.
- **Asks of the senior pass:** (1) review whether an ideal-source BEM is an adequate predictor for these horns or whether a driver/throat model is required before further campaigns; (2) pick a measured reference horn to validate against (polars, DI, throat impedance); (3) approve the loading-on / stricter-cov re-score (P12a, no new solves); (4) decide whether to gate further campaign nights on that.
- Nothing in scoring was changed for this note; the v4 nights and the queued ripple/ridge night run on the existing v4 scoring.

### 2026-10-27 (evening) P12 research result (append)
Outside research is in `docs/research/SIM_VS_REAL_HORN_2026-10-27.md` and `docs/plan/12_RESEARCH_BASIS.md` section 17: ideal-source BEM is a sound relative tool for pattern shape above cutoff, not for level/loading/distortion. Ranked actions are in `docs/NEXT_DEV_PRIORITIES.md` P12. Decision requested from the senior pass: approve P12a (free re-score with loading ON + stricter cov), the lumped-driver-over-BEM-throat-impedance add, and which published measured horn to validate against. The ripple/ridge night was launched 2026-10-27 17:23 on the existing v4 scoring at the owner's direction.

## 2026-10-29 mini multiple-entry horn research pass (orchestrator, append-only)
Dossier: `docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` (s8 corrections table). Three corrections touch files
this pass does not own; nothing in them was edited:
1. `docs/plan/12_RESEARCH_BASIS.md` s3/s9 and `docs/plan/04_TASK_DESIGN_MESH.md:289` (frozen) say the mesher already has
   the MEH geometry path (tags 8-11). Verified 2026-10-29 at mesher a833a7e: tag NAMES only (8-12; 10/11 in
   `SOURCE_TAGS`); no builder, and the mesher README says it ships no builders for slots, ports, drivers or cabinets.
   MEH geometry needs our CAD -> STEP route with several driven labels, or a new builder.
2. `docs/DRIVER_MODEL.md:42` cites "Boundary Lab issue #78: 10-20 % low-frequency error". The source is
   timini/horn-simulation issue #78 ("Evaluation: JWSound/boundary-lab compared to horn-simulation ..."; BL's own #78
   is a 404); it says Mms - Mmd is "of order 10 to 20 percent of the mass term". Suggested edit: "(timini/horn-simulation
   issue #78, evaluating Boundary Lab: Mms - Mmd is of order 10-20 % of the mass term)". The Mmd rule itself stands.
3. `docs/BOUNDARY_LAB_0.5_RESEARCH.md` s4 / `docs/research/boundary_lab_0.5/bl_inventory.md`: "named assemblies require
   symmetry Off" is a generator-plugin limit; a coupled multi-region BL project runs with symmetry `xy`
   (`examples/Multi_region_SAWMOD`, verified). Suggested: add that sentence where the limit is quoted.
Also for the senior pass: the hornlab-beat-bem Python package refuses more than one source tag (`config.py:462`) while
its engine already solves several channels on one factorization; an opt-in fork change (multi-tag + per-tag
impedance matrix) is MEH seed MEH-3. MEH implementation stays owner-deferred.
## 2026-10-31 staged search A/B (collaborator Mac)

What happened: implemented the staged-search recommendation as an equal-budget protocol
(macro 20 → shape 20 → polish 20 vs joint 60) on crease__core_law, with
`tools/run_staged_search.py` chaining stages from `best.json`. Offline suite green.
Synthetic coupled landscape: staged+polish wins (J 0.100 vs 0.302). Acoustic GPU A/B could
not run here (no CUDA / no project venv). Decision recorded in
`docs/evidence/STAGED_SEARCH_AB_2026-10-31.md`: keep the tools/ harness; do not promote into
`hornlab_search/search/` until the CUDA-box run; term normalisation remains higher leverage.

What I need decided: nothing blocking — GPU-box owner should run
`tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both` when free and paste
COMPARE.md into the evidence doc.
