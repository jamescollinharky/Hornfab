# M4: lumped network, coupling, DSP, limits, inner optimiser (`hornlab_search/meh/`)

Model: Sonnet. Wave 1. Depends on contracts only (uses synthetic data and the 1-D reference; M3's real fields arrive
later with the same names). Read `00_MEH_CONTRACTS.md` C5-C8, C10-C12. Reference code to port and test against:
`docs/research/typologies/mini_meh_2026-10-29/calc/meh_1d_sketch.py` (entry Norton, cone velocity, conical duct),
`calc/meh_zmatrix_check.py` (decomposition), `calc/meh_1d_study.py` (LR4, alignment search). Import those by file
path in tests only (`importlib.util.spec_from_file_location`); never import them from package code.

## Owns

`hornlab_search/meh/{__init__,drivers,network,dsp,limits,synthesis,inner}.py`, `tests/test_meh_network_*.py`,
`tests/test_meh_inner_*.py`.

## Build steps

1. `drivers.py`: `ConeDriver` and `CDSource` frozen dataclasses from the C8 keys, SI-derived properties (Cms, Rms,
   Mmd_eff with `mmd_from_mms`), loaders `load_cone(stem)` / `load_cd(stem)` reading `examples/drivers/<stem>.yaml`
   (refuse a wrong `kind`). Until M1 lands, tests use fixture YAMLs in `tmp_path`.
2. `network.py`: `from_bem`, `entry_norton`, `cd_volume_velocity`, `couple`, `cone_excursion_peak_mm`,
   `port_velocity_peak` exactly per C6/C7. Vectorised over frequency (numpy), complex128.
3. `dsp.py`: Linkwitz-Riley (orders 2, 4, 8 via squared Butterworth), Butterworth, delay, polarity, a peaking biquad
   (analog prototype in s), and `system_eq` per C11 (1/3-octave smoothing on a log grid; boost clipped at
   `max_boost_db`, unlimited cut). Helper `smooth_oct(f, db, frac)` (power average in a +-frac/2 octave window).
4. `synthesis.py`: `system_response(resp, solution) -> Response`: per channel complex drive (DSP x network U), sum
   `H_net * U` per plane/angle (and sphere), convert back to the BEM convention (conj, per-unit-acceleration basis is
   NOT needed: store absolute Pa at the solve distance for 1 V input) so `metrics/compute.py` can run unchanged;
   `impedance` = nan array.
5. `limits.py`: `spl_max(f, solution, brief_meh)` per C11 (all channels scale linearly with input; per frequency the
   first limit wins). Report which limit binds per band (for the record).
6. `inner.py`: `optimise_network(...)`:
   - enumerate driver combinations from the brief (<= 9), xo order in `xo_orders`, mid polarity +-1;
   - for each, `cma` (already a dependency) over [log xo_hz, mid_delay_ms, mid_gain_db, fill, v_rear_l] within the
     brief ranges, popsize 8, <= 160 evals, seed fixed (brief or 1234);
   - inner score = the C11 terms that depend on the network (`lw_resid`, `notch`, `xo_lob`, `headroom`, plus `rip`
     and `cov` on the synthesised polars) with the brief weights, computed via a callable passed in by M7 (so M4
     does not import objective code; default = a local proxy of `lw_resid + notch + xo_lob + headroom` for tests);
   - return the best `NetworkSolution` (C12) with `n_evals`, timing.
   Budget target: < 2 s per candidate on CPU for 60 frequencies x 2 planes x 37 angles x 2 channels.

## Tests (checkable properties)

- `entry_norton(n_end=2)` == the sketch's `Entry.norton` for the sketch's MID4 / MID65 to 1e-12 (60 frequencies).
- `couple` reproduces the sketch's direct `solve` when fed the bare-horn H/Z of `meh_zmatrix_check.bare_injection`
  (one and two entry groups), rel 1e-9.
- Energy: for one entry into a purely resistive load, electrical power in = Re-loss + Rms-loss + port-loss + acoustic
  power out, rel 1e-9.
- `from_bem`: synthetic Response with known per-acceleration values -> expected conj/scale; a symmetric force
  matrix gives a symmetric Z_net.
- `mmd_from_mms`: FaitalPRO 6FE100 (Mms 14.0 g, Sd 149 cm^2) -> 11.9 +- 0.1 g; 4FE32 (4.2 g, 51.9 cm^2) -> 3.8 +- 0.1 g.
- LR4 low + high sum to unit magnitude (all-pass) within 1e-9; delay gives the right phase slope.
- `system_eq` never boosts more than `max_boost_db`.
- Inner optimiser on synthetic channels (two ideal band-limited sources with a known 0.3 ms offset and polarity -1)
  recovers delay within 0.02 ms and polarity, xo within 5 %.

## Checkpoint

`pytest tests/test_meh_network_*.py tests/test_meh_inner_*.py -q` and the full offline suite
`-m "not slow and not gpu and not crosscheck"` with the interpreter from README "Running tests" (paste both outputs).
