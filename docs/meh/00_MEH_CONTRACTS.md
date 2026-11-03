# MEH contracts (frozen for the MEH effort; only the orchestrator edits this file)

2026-10-30. Every name, key, tag, unit, array shape and signature an MEH work package (M1-M10) needs. Do not invent
one that is not here; if you need one, stop and append the request to `NOTES_FOR_SENIOR.md`.
Design basis: `docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md` (the dossier) and its `calc/` scripts,
which are the **reference implementations** you port and test against.

## C0. Owner decisions (2026-10-30)

| Decision | Value |
|---|---|
| System | MEH top from ~120 Hz up + a SEPARATE bass box 30-120 Hz flat (M10). The MEH never plays below its high-pass |
| Size | front face fits a 16 in square: 406.4 x 406.4 mm; depth 380 mm (orchestrator assumption, studio-monitor class); corner-hung |
| Use | home hi-fi, DJ practice, DJ booth; critical listening first; level "keeps up with a powered 12 in + horn PA box" |
| DSP | active DSP on every channel; FIR allowed |
| Commercial | no (patents irrelevant) |

## C1. Typologies (labelled experiments; neutral names, no "Synergy")

| ID | Config name stem | CD | Mids | Walls | Coverage target | XO CD/mid | MEH high-pass |
|---|---|---|---|---|---|---|---|
| T2 (primary) | `meh2_6x2` | 1.4 in (FaitalPRO HF1440 class) | 2 x 6.5 in (B&C 6NDL38 / FaitalPRO 6PR160) | top + bottom (`tb`) | 90 H x 60 V | 650-1100 Hz | 100-150 Hz (brief `hp_hz`, default 120) |
| T1 (secondary) | `meh2_4x4` | 1 in (FaitalPRO HF108 / B&C DH450 class) | 4 x 4 in (B&C 4NDF34) | all four (`tblr`) | 90 H x 60 V | 1000-1500 Hz | 140-200 Hz (default 160) |

Why: s5/s6 of the dossier and `calc/layout_out.md`. T2 is the only complement with ~116 dB at 125 Hz (2 x 6NDL38,
excursion-limited, 1 m half space); its 6.5 in front chamber puts the port corner at ~650-950 Hz, so it pairs with a
1.4 in CD crossed near the port roll-off. T1 is the compact hi-fi variant. Side-wall mounting for T2 is 41 %
layout-feasible vs 77 % top/bottom, and has the wider port spacing (more horizontal lobing): top/bottom is fixed.

## C2. Frame, units, symmetry

- CAD recipe in **mm**, coupling plane (CD exit) at **z = 0**, **+z toward the mouth**, x horizontal, y vertical (same
  as `tools/cad/plughorn.py`). The horn is a flat-wall pyramid with its virtual apex at z = -z_c,
  z_c = sqrt(A_exit / (4 tan(h/2) tan(v/2))).
- Mesh in **metres** (step_build converts; `SolveConfig(mesh_scale=1.0)`: silent killer 1).
- **Quarter model** (x >= 0, y >= 0), quadrants `"1"`, symmetry from `mesh/sizing.py::SYMMETRY_PLANE` only
  (silent killer 2). Every entry is mirror-paired, so the quarter holds for the symmetric drive we use.

## C3. STEP labels -> BEM tags (the only mapping)

| STEP label | Tag | Physical name (mesher `tags.py`) | Surface |
|---|---|---|---|
| `wall` | 1 | `SD1G0` | every rigid face |
| `driver` | 2 | `SD1D1001` | CD diaphragm disc at the BOTTOM of the CD bore, z = -`cd_duct_mm` (z = 0 if `cd_duct_mm` = 0) |
| `entry_mid` | 10 | `mid_port_exit_left` | every mid-port aperture: a face IMPRINTED on the horn's inner wall (flush patch, no hole, no chamber) at level L1 |
| `entry_aux` | 11 | `mid_port_exit_right` | reserved (not used by T1/T2 v1) |

The physical names are the mesher's for those tag numbers (ABEC / Boundary Lab compatible); "left/right" carries no
meaning here. Existing CAD tools (`multicell`, `plughorn`) keep their `driver`/`wall` contract unchanged.

## C4. Solver contract (fork `hornlab-beat-bem`, branch `hornlab-search/meh-multisource`, task M2)

`SolveConfig` (Python, fork):
- `velocity_sources: dict[int, float]` accepts **1..8** tags; every amplitude must be exactly `1.0` (the existing
  complex / non-unit refusals stay). **With one tag the request payload and every output are byte-identical to today.**
- New field `impedance_matrix: bool = False`.
- With >= 2 tags the payload carries `config["radiators"] = [{"name": f"tag{t:03d}", "tag": t, "channel":
  f"tag{t:03d}"} for t in sorted(tags)]` (zero-padded so the engine's lexicographic channel sort equals tag order) and
  no `"channels"` (unit drive per channel). `tag_throat` stays = the smallest tag (legacy key).
- `impedance_matrix=True` adds `config["impedance_matrix_enabled"] = true`; the engine emits `"impedance_matrix"`:
  `[j][i] = [Re(F)/2, -Im(F)/2]` (the existing impedance packing, x10 display factor included) = full-domain force on
  radiator i from channel j's boundary pressure at unit channel drive. Absent flag = key absent (byte-identical).
- New `SolveResult` fields (all `None` with one tag and no matrix):
  - `channel_tags: tuple[int, ...]` sorted;
  - `channel_pressure: complex128 (F, C, P, A)`: per channel, per plane, per angle; **per unit normal ACCELERATION** on
    that tag (same basis as `pressure`);
  - `channel_sphere_pressure: complex128 (F, C, N_sphere)` when a sphere grid is requested;
  - `impedance_matrix: complex128 (F, C, C)`: `[f, i, j]` = area-mean pressure on tag i (full-domain area) per unit
    normal acceleration on tag j; same unpacking as the existing impedance (`force / (_BEAT_IMPEDANCE_FORCE_FACTOR *
    symmetry_factor * area_i_reduced)`, times the acceleration scale);
  - `tag_areas_m2: dict[int, float]`: FULL-domain area per tag (reduced area x symmetry factor).
- Legacy `pressure`, `spl`, `impedance` with >= 2 tags = the channel of the smallest tag (the CD).
- All fields use the solver's `exp(-i omega t)` convention, unchanged.

## C5. hornlab-search response contract (task M3)

`hornlab_search/types.py::Response` gains optional fields with the SAME names, shapes and bases as C4
(`channel_tags`, `channel_pressure`, `channel_sphere_pressure`, `impedance_matrix`, `tag_areas_m2`), default `None`.
`SolveSpec.extra["source_tags"]` (list of int) switches the MEH path on in `solve/beat.py`; absent = today's config and
solve hash byte-for-byte.

## C6. Network conventions (task M4; reference `calc/meh_1d_sketch.py`, `calc/meh_zmatrix_check.py`)

Network math uses **exp(+j omega t)** and SI rms quantities (like `driver/compression.py`). From a BEM `Response`
(exp(-i omega t), per unit acceleration) to network quantities, for channel c with full-domain area A_c:

```
per unit normal velocity   : X_v = X_a * (-1j * omega)          (exp(-iwt): a = -i w v)
per unit volume velocity   : X_U = X_v / A_c
network convention         : X_net = conj(X_U)
H_net[f, c, p, a] = conj(channel_pressure[f, c, p, a] * (-1j*w) / A_c)   # Pa per (m^3/s), at the solve distance
Z_net[f, i, j]    = conj(impedance_matrix[f, i, j] * (-1j*w) / A_j)       # Pa per (m^3/s), reciprocal: Z_net = Z_net.T
```

Coupling (exact for lumped entries; proved to 6e-16 on the 1-D model):

```
channel 0 = CD (tag 2): prescribed volume velocity U_cd (ideal source; its own admittance 0)
entry groups e (tag 10, ...): Norton (U_sc_e, Y_e) from the entry network (C7), N drivers of a group in parallel
U_e   = solve(I + Y_ee Z_ee,  U_sc - Y_ee Z_e0 U_cd)
p[f, p, a] = H_net[f, 0] U_cd + sum_e H_net[f, e] U_e
```

## C7. Entry network (one group = N identical cones, each behind its own port; per driver)

```
Ze      = Re + j w Le
Zm      = Rms + j w Mmd_eff + 1/(j w Cms) + Bl^2 / Ze           Mmd_eff = Mmd (preferred) else Mms - 2*(8/3)*rho*a^3, a = sqrt(Sd/pi)
Zcone   = Zm / Sd^2 + 1/(j w Cb),  Cb = V_rear / (rho c^2)       sealed rear chamber per driver
p_s     = Bl e / (Ze Sd)                                         e = per-driver drive voltage (complex, after DSP)
Zcf     = 1/(j w Cf),  Cf = V_front / (rho c^2)
Zport   = x / Q_port + j x,   x = w rho L_eff / S_port,   Q_port = 10
L_eff   = l_neck + n_end * 0.85 r_eq,  r_eq = sqrt(S_port / pi)
          n_end = 1 with BEM data (the horn-side radiation mass is already in Z_net); n_end = 2 only to reproduce the
          1-D sketch, whose horn node has no radiation mass
Zth     = Zport + Zcf || Zcone ;  p_th = p_s * Zcf / (Zcf + Zcone)
U_sc    = N * p_th / Zth ;  Y = N / Zth
cone velocity per driver = (p_s - p_c) / Zcone / Sd,  p_c = p_horn + U_out Zport,  U_out = (U_sc - p_horn Y) / N
```

V_front from the cone dish model (layout reference): V_front = Sd * (spacer + wall_t + (1 - fill) * dish / 3);
`fill` is the inner optimiser's front-chamber filler fraction (a printed insert the CAD adds at level L2).

CD source (no CD publishes T/S): `U_cd(f) = g_cd * S_exit / (j w) * HP2(f; fs_cd, q_cd)` (mass-controlled, as the
BEM drives it), `fs_cd`, `q_cd` from the driver file, `g_cd` = the CD channel gain (DSP).

## C8. Driver files (task M1; `examples/drivers/`)

New files only; existing files untouched. Required keys by kind (datasheet units; every number from the maker's
datasheet with its URL in `source`; never guess; a derived value carries `derived: [key, ...]`):

| kind | required | optional |
|---|---|---|
| `cone` | name, kind, re_ohm, le_mh, bl_tm, sd_cm2, xmax_mm, p_aes_w, fs_hz, qms (or rms_kg_s), mmd_g or mms_g, cms_mm_per_n or vas_l, cutout_mm, depth_mm, source | frame_od_mm, motor_od_mm, dish_mm, sens_db_2v83, notes |
| `compression_meh` | name, kind, exit_mm, p_aes_w, min_xo_hz, sens_db_1w (and its reference horn in notes), body_d_mm, body_len_mm, source | duct_mm (diaphragm to exit, from the drawing), fs_cd_hz (default = min_xo_hz / 1.4), q_cd (default 1.0), di_ref_db (default 10), re_ohm |

`compression_meh` is a NEW kind so `driver/compression.py` (which needs Bl/Mmd) never loads these files.

## C9. CAD tool `tools/cad/meh.py` (task M5; reference `calc/meh_layout.py`)

`KEYS` (every key required in the recipe, like plughorn):

| key | unit | role | T2 default | search range |
|---|---|---|---|---|
| `cov_h_deg`, `cov_v_deg` | deg (full) | geometry | 90, 60 | 75-95, 50-80 |
| `z_frac` | 0-1 | port centroid between z_lo = 5 + port_along/2 and z_hi = z_m - 10 - port_along/2 | 0.25 | T2 0-0.7, T1 0-0.6 |
| `across_frac` | 0-1 | port width = frac x (NARROWEST used wall width at the port's near end - 6 mm) | 0.8 | 0.35-0.9 |
| `port_along_mm` | mm | port length along the wall slant | 30 | 12-35 |
| `slide_mm` | mm | driver centre offset along the slant from the port centroid; deterministically REPAIRED in 2 mm steps (toward the mouth while the flange hits the CD body, back while it passes the mouth); the repair is logged in `mesh_meta.json` | 10 | -10..40 |
| `walls` | str | `tb` (T2) or `tblr` (T1) | `tb` | fixed |
| `env_w_mm`, `env_h_mm`, `env_d_mm`, `box_t_mm` | mm | envelope | 406.4, 406.4, 380, 18 | fixed |
| `roll_mm` | mm | mouth roundover radius | 20 | fixed v1 |
| `wall_t_mm`, `spacer_mm` | mm | layout only at L1 | 6, 3 | fixed |
| `exit_mm`, `cd_duct_mm`, `cd_body_d_mm`, `cd_body_len_mm` | mm | from the CD file | HF1440: 35.8, 40*, 124, 75 | fixed per CD |
| `cone_cutout_mm`, `cone_depth_mm` | mm | from the cone file | 6NDL38: 145, 85 | fixed per cone |
| `clearance_mm` | mm | min gap | 3 | fixed |

`*` = [inferred] until M1 reads the drawing. The horn length is derived: the longest whose mouth + roll fits the face
(`calc/meh_layout.py::geometry`). L1 solid: the box (env_w x env_h x depth) minus the horn air (pyramid frustum from
z = 0 to the mouth, roundover at the mouth) minus the CD bore (cylinder of `exit_mm` from z = -cd_duct_mm to 0); port
outlines imprinted on the inner walls and labelled `entry_mid`; quarter cut at x = 0 and y = 0 (symmetry planes are not
BEM faces). The tool also returns `derived()`: z_c, z_m, mouth W x H, per-port centroid/area/path-to-diaphragm
(z_port + cd_duct_mm), quarter-wave f, layout reasons (empty = OK), repairs applied.

## C10. Brief `meh:` block (task M6 validates; M7 consumes)

```yaml
meh:
  groups:
    cd:  {tag: 2,  drivers: [faitalpro_hf1440]}                 # files in examples/drivers/ (stem)
    mid: {tag: 10, count: 2, drivers: [bc_6ndl38, faitalpro_6pr160]}
  hp_hz: 120                 # LR4 high-pass on every MEH channel (crossover to the bass box)
  xo_hz: {lo: 650, hi: 1100} # CD/mid crossover search range
  xo_orders: [2, 4]          # Linkwitz-Riley orders the inner optimiser may pick
  delay_ms: {lo: -1.0, hi: 2.0}
  v_front_fill: {lo: 0.0, hi: 0.7}   # front-chamber filler fraction (V_front from the cone dish model)
  v_rear_l: {lo: 0.8, hi: 6.0}
  amp_v_rms: 40.0            # per-channel amplifier ceiling
  port_air_mps_max: 17.0     # chuffing limit, peak particle velocity in the port [practitioner]
  max_boost_db: 6.0          # FIR-equivalent system EQ boost limit
  spl_target: [[120, 114], [250, 120], [12000, 120]]   # [Hz, dB] sine, 1 m, half space; log-f linear
  listening_window: {h_deg: [0, 10, 20, 30], v_deg: [10]}
```

## C11. Objective version 5 ("meh") (task M6)

`J = sum_k w_k term_k / tol_k + penalty`, k over the v4 keys (`cov rip di dislope flat load distd diag`, computed by
the v4 functions on the SYNTHESISED system response, i.e. the pattern terms are unchanged in meaning) plus:

| key | definition (band = brief band; LW = power average over the listening window angles) | tol | T2 weight |
|---|---|---|---|
| `lw_resid` | RMS of S6(LW + E) - mean, where E = clip(mean(LW) - S3(LW), -inf, max_boost_db) is the system EQ (FIR-equivalent, applied to all angles) and Sk = 1/k-octave smoothing | 1.0 dB | 0.5 |
| `notch` | mean of the 3 largest values of max(0, S3(LW) - LW) over the band (narrow dips EQ cannot fill) | 3.0 dB | 1.0 |
| `xo_lob` | for each CD/mid crossover fx: RMS over f in [fx/sqrt2, fx*sqrt2] and angles H in [-45, 45], V in [-30, 30] of N(theta, f) - R(theta, f), N = SPL - SPL(0 deg), R = log-f linear interpolation of N between fx/2 and 2 fx | 1.5 dB | 1.0 |
| `headroom` | mean over the band of max(0, spl_target(f) - SPL_max(f)) | 2.0 dB | 1.0 |

Bass-box crossover rule: `lw_resid` and `notch` use the band [max(band_lo, 1.5 x hp_hz), band_hi] (the MEH's own
high-pass is intended; bass integration is tuned at the listening position). `spl_target` is the SYSTEM target; the
MEH must reach `spl_target(f) + 20 log10 |LR4_HP(f; hp_hz)|`, and `headroom` compares SPL_max against that.

`SPL_max(f)`: input level scaled until the first limit is hit, limits = cone excursion = Xmax (peak), cone electrical
power = p_aes_w (V^2 / Re), port peak air velocity = `port_air_mps_max`, amplifier `amp_v_rms`, CD power = p_aes_w
estimated as `sens_db_1w + 10 log10(P) + (DI_ours(f) - di_ref_db)`. Weights for T2/T1 briefs: cov 1.0 (narrow ratio
2.0, `cov_below_f0: one_sided`, f0 = K-law floor of the mouth width), rip 0.5, distd 0.5, dislope 0.3, diag 0 (screen
has no balloon), di 0, flat 0 (FIR makes on-axis flatness free), load 0, lw_resid 0.5, notch 1.0, xo_lob 1.0,
headroom 1.0. Band: 120 Hz-12 kHz (screen, dof cap); verify to 16 kHz later.

## C12. Module names, signatures (task M4)

```
hornlab_search/meh/__init__.py
hornlab_search/meh/drivers.py   load_cone(stem) -> ConeDriver ; load_cd(stem) -> CDSource ; mmd_from_mms(mms_g, sd_cm2) -> g
hornlab_search/meh/network.py   from_bem(resp) -> (H_net, Z_net, freqs) ;
                                entry_norton(f, cone, n, v_front_m3, s_port_m2, l_neck_m, v_rear_m3, e_volts,
                                             n_end=1, q_port=10.0) -> (u_sc, y)
                                cd_volume_velocity(f, cd, gain) -> U_cd ; couple(Z_net, u_sc, y, u_cd) -> U[f, C]
                                cone_excursion_peak_mm(...) ; port_velocity_peak(...)
hornlab_search/meh/dsp.py       lr(f, fc, order, kind) ; delay(f, ms) ; system_eq(lw_db, f, max_boost_db) -> E_db
hornlab_search/meh/limits.py    spl_max(f, solution, brief_meh) -> dB
hornlab_search/meh/synthesis.py system_response(resp, solution) -> Response   (pressure/sphere synthesised, impedance nan)
hornlab_search/meh/inner.py     optimise_network(resp, layout_derived, brief, drivers) -> NetworkSolution
```

`NetworkSolution` (dataclass, JSON-serialisable): cd stem, mid stem, xo_hz, xo_order, mid_delay_ms, mid_polarity,
gains_db per channel, v_front_m3, v_rear_m3, eq_db curve, spl_max_db curve, inner_J, n_evals, seed.

## C13. File ownership for the MEH effort (adds to CLAUDE.md's table)

| Task | Owns |
|---|---|
| M1 | new `examples/drivers/*.yaml` files with kind `cone` / `compression_meh`; `tests/test_meh_driver_files.py` |
| M2 | the fork branch `hornlab-search/meh-multisource`; `docs/evidence/MEH_M2_FORK_*.md` |
| M3 | additive fields in `hornlab_search/types.py`; the MEH path in `solve/beat.py`; additive fields in `dataset/record.py`; `tests/test_solve_meh_*.py`, `tests/test_dataset_meh_*.py` |
| M4 | `hornlab_search/meh/**`; `tests/test_meh_network_*.py`, `tests/test_meh_inner_*.py` |
| M5 | `tools/cad/meh.py`; the `meh` registry entry + multi-label mapping in `mesh/step_build.py`; `tests/test_mesh_meh_*.py` |
| M6 | `hornlab_search/objective/scalar_meh.py`; version 5 in `objective/versions.py`; the `meh:` block in `config.py`; `tests/test_objective_meh_*.py`, `tests/test_config_meh.py` |
| M7 | the MEH branch in `search/evaluate.py`; `examples/typologies/meh_2026-10-30/`, `examples/briefs/meh_2026-10-30/`; `tests/test_search_meh_*.py`, `tests/test_end_to_end_meh.py` |
| M8 | `docs/evidence/MEH_M8_*.md` (GPU box; owner runs) |
| M9 | `tools/bl_export_meh.py`; `tests/test_bl_export_meh.py`; `docs/evidence/MEH_M9_*.md` |
| M10 | `tools/bassbox.py`; new woofer files (kind `cone`) in `examples/drivers/`; `tests/test_bassbox.py`; `docs/research/typologies/mini_meh_2026-10-29/BASSBOX_*.md` |
| everyone | `docs/CONTINUITY.md`, `docs/ISSUES.md` (on every push), `NOTES_FOR_SENIOR.md` (append only) |
