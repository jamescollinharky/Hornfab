# M6: objective version 5 ("meh") + the brief `meh:` block

Model: Sonnet. Wave 1. Read `00_MEH_CONTRACTS.md` C10-C11, then `hornlab_search/objective/scalar_v4.py`,
`objective/terms.py`, `objective/versions.py`, and the brief validation in `hornlab_search/config.py`.

## Owns

`hornlab_search/objective/scalar_meh.py`, version 5 in `objective/versions.py`, the `meh:` block validation in
`config.py` (additive; v1-v4 configs and hashes byte-identical), `tests/test_objective_meh_*.py`,
`tests/test_config_meh.py`.

## Build steps

1. `scalar_meh.py`: `objective_meh(metrics, resp, ok, target, weights, params, meh_ctx)`:
   - the v4 terms via the v4 functions on the synthesised response (do not duplicate their maths);
   - `lw_resid`, `notch`, `xo_lob`, `headroom` per C11, using `meh_ctx` = {freqs, LW (dB), polars (H, V dB),
     xo_hz list, spl_max_db, spl_target_db} built by M7 (keep this module free of network code);
   - tolerances/weights from the brief's `objective:` block (v4 pattern), defaults = the C11 table;
   - never raises, never returns nan/inf (v4 rule); graded penalty for infeasible.
2. Also export a cheap `inner_score(meh_ctx, weights)` that M4's inner optimiser calls through M7 (same terms, no
   balloon terms).
3. `versions.py`: add 5; `search/evaluate.py` dispatch is M7's.
4. `config.py`: validate the C10 block (exact keys, types, ranges: hp_hz 60-250, xo lo < hi within 300-3000, orders
   subset of {2, 4, 8}, delay -3..3 ms, fill 0..0.9, v_rear 0.2..20 L, amp 5..200 V, port air 5..40 m/s, boost 0..12 dB,
   spl_target sorted by f with dB 80..140, driver stems exist with the right kind once M1 has landed (warn, do not
   fail, while a stem is missing)). Unknown keys refuse.

## Tests

- `lw_resid` = 0 for a flat LW; = the RMS of an injected broad tilt that exceeds the boost limit (analytic).
- `notch`: an injected 10 dB, 1/12-octave dip scores >= 2.5 dB; a smooth 3 dB shelf scores < 0.3 dB.
- `xo_lob`: polars that vary log-linearly across the window score < 0.1 dB; an injected 6 dB off-axis lobe at fx
  scores > 1.5 dB.
- `headroom`: 0 when SPL_max >= target everywhere; analytic value for a uniform 4 dB shortfall.
- J composition: sum of w_k * term_k / tol_k plus penalty; stored terms are normalised (v4 convention).
- Config: the C10 example validates; each bad key/range refuses with a clear message; existing brief tests unchanged.

## Checkpoint

New tests + `tests/test_config.py` + objective tests + the full offline suite (paste outputs).
