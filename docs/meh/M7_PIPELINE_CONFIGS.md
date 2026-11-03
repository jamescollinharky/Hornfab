# M7: evaluate pipeline MEH branch + configs and briefs

Model: Sonnet. Wave 2 (after M3, M4, M5, M6 are merged). Read `00_MEH_CONTRACTS.md` fully, then
`hornlab_search/search/evaluate.py`, an existing CAD typology config
(`examples/typologies/cone_plughorn_2026-10-28/cone_plughorn__morph_narrow_10in.yaml`) and its brief.

## Owns

The MEH branch in `search/evaluate.py`; `examples/typologies/meh_2026-10-30/`, `examples/briefs/meh_2026-10-30/`;
`tests/test_search_meh_*.py`, `tests/test_end_to_end_meh.py`.

## Build steps

1. `evaluate.py`: when the brief has `meh:` -> mesh via the `meh` CAD tool -> solve with
   `extra.source_tags = [2, 10]` (from the brief groups) -> `meh.inner.optimise_network(resp, derived, brief, drivers,
   score=objective_meh.inner_score)` -> `meh.synthesis.system_response` -> `metrics.compute` on the synthesised
   response -> `objective_meh` (version 5) -> record (per-channel arrays + Z + NetworkSolution + layout derived).
   Non-MEH briefs: byte-identical behaviour (the existing tests prove it).
2. Briefs (paste-ready drafts below; adjust only key spellings that the M6 validator enforces).
3. Typology configs: T2-A, T2-B (fill), T1 seeds from `calc/layout_out.md` "Final seeds"; generator `meh`,
   `seed_policy: explicit`, searchable = `cov_h_deg cov_v_deg z_frac across_frac port_along_mm slide_mm` with the C9
   ranges; everything else fixed from the driver files; mesh quadrants "1"; screen grid 120 Hz-12 kHz at 1/6 octave.

```yaml
# examples/briefs/meh_2026-10-30/meh_home_90x60_t2.yaml (draft)
name: meh_home_90x60_t2
description: Mini MEH top, home hi-fi / DJ booth, 90x60, 16 in square face, 1.4 in CD + 2 x 6.5 in, HP 120 Hz to the bass box
driver: {exit_radius_mm: 17.9, exit_angle_deg: 0.0}
envelope: {max_mouth_w_mm: 370.0, max_mouth_h_mm: 370.0, max_depth_mm: 380.0}
symmetry: hv
source: {cap: auto}
target:
  coverage_h_deg: 90.0
  coverage_v_deg: 60.0
  band_lo_hz: 120.0
  band_hi_hz: 12000.0
  di_target_db: null
  di_slope_target: 0.0
  z_min: 0.0
  f0_hz: 850.0
weights: {cov: 1.0, rip: 0.5, di: 0.0, dislope: 0.3, flat: 0.0, load: 0.0, distd: 0.5, diag: 0.0,
          lw_resid: 0.5, notch: 1.0, xo_lob: 1.0, headroom: 1.0}
objective: {version: 5, cov_narrow_ratio: 2.0, cov_below_f0: one_sided}
meh:
  groups:
    cd:  {tag: 2,  drivers: [faitalpro_hf1440]}
    mid: {tag: 10, count: 2, drivers: [bc_6ndl38, faitalpro_6pr160]}
  hp_hz: 120
  xo_hz: {lo: 650, hi: 1100}
  xo_orders: [2, 4]
  delay_ms: {lo: -1.0, hi: 2.0}
  v_front_fill: {lo: 0.0, hi: 0.7}
  v_rear_l: {lo: 0.8, hi: 6.0}
  amp_v_rms: 40.0
  port_air_mps_max: 17.0
  max_boost_db: 6.0
  spl_target: [[120, 114], [250, 120], [12000, 120]]
  listening_window: {h_deg: [0, 10, 20, 30], v_deg: [10]}
```

T1 brief = the same with `driver.exit_radius_mm: 12.7`, groups cd `[faitalpro_hf108, bc_dh450]`, mid count 4
`[bc_4ndf34, faitalpro_4fe32]`, `hp_hz: 160`, `xo_hz: {lo: 1000, hi: 1500}`,
`spl_target: [[160, 112], [300, 118], [12000, 118]]`.

## Tests

- Fake-solver end-to-end (synthetic per-channel data + a symmetric Z): evaluate returns a finite J, a
  NetworkSolution, and a record with the per-channel arrays; re-scoring the stored record with another driver stem
  needs no solve.
- Every new config and brief loads and validates; existing config tests unchanged.
- GPU/real-solver tests marked `slow` + `gpu` (deselected in CI).

## Checkpoint

New tests + the full offline suite; a CPU mesh check of the three seeds (dofs, tags, layout) with `tools/shape_check.py`.
