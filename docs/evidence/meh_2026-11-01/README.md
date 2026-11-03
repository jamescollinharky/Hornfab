# Verified MEH screen winners (2026-11-01)

Machine-readable snapshots of the two best designs from the 500 Hz–10 kHz MEH screens, so a new session can start
from a real winner instead of re-running 40 evaluations. Each JSON carries the CAD recipe, the objective terms,
the inner-network solution (crossover, delay, polarity, rear volume), the CAD layout the optimizer consumed, the
channel tags and the library SHAs.

These are **starting points for the next search**, not finished loudspeakers. Both carry the caveat that the top of
the band is mesh-limited and that `lw_resid` (listening-window flatness) dominates the score.

## The two winners

| | T2 (primary) | T1 (compact) |
|---|---|---|
| label | `t2` | `t1` |
| typology | 2 × 6.5 in on top/bottom + 1.4 in CD | 4 × 4 in, one per wall + 1 in CD |
| brief | `meh_home_90x60_t2` | `meh_home_90x60_t1` |
| run | `20261101T004552Z-screen-427d57` | `20261101T015657Z-screen-fc1d24` |
| best design | `ed11d2cd3acc` | `704051ae928c` |
| screen J | **9.530** | **13.228** |
| verify J | **11.894** | **14.512** |
| quarter dofs | 5,872 | 6,249 |
| CD driver | `faitalpro_hf1440` | `faitalpro_hf108` |
| mid driver | `bc_6ndl38` | `bc_4ndf34` |
| crossover | 651.8 Hz, LR order 4 | 1000.2 Hz, LR order 4 |
| mid delay / polarity | **+0.312 ms**, +1 | **+1.430 ms**, −1 (inverted) |
| rear volume per driver | 4.212 L | 0.806 L |
| coverage (H × V) | 86.10° × 66.89° | 84.56° × 71.83° |
| `z_frac` / `across_frac` | 0.0918 / 0.8767 | 0.261 / 0.847 |
| `port_along_mm` / `slide_mm` | 27.24 / 35.16 | 22.15 / 36.11 |
| dominant terms | `lw_resid` 7.823, `cov` 2.830, `headroom` 1.281, `xo_lob` 0.430, `notch` 0.000 | `lw_resid` 13.090, `cov` 3.101, `headroom` 1.876, `xo_lob` 0.925, `notch` 0.000 |

Both winners push the driver to the top of the `slide_mm` range and the ports low (`z_frac` 0.09 for T2). That is
where the optimiser went, not a design law — treat it as a hypothesis for the next study.

## Files

- `t2_ed11d2cd3acc.json`, `t1_704051ae928c.json` — one record each:
  `params` (CAD recipe), `terms`, `objective`, `network_solution`, `layout_derived`, `channel_tags`, `mesh`,
  `lib_shas`.
- Provenance: the full records (including the per-channel pressure arrays and impedance matrices) live in the local
  dataset store and the run directories named above; those are not committed (size). The evidence doc
  `docs/evidence/MEH_M8_2026-10-31.md` states which numbers are measured and how.

## Do not

- Do not compare these J values to a run on a different frequency grid. The 500 Hz–10 kHz 12-point screen and a
  120 Hz–12 kHz grid are different grid groups.
- Do not read `verify` as a finer mesh: at the current band and dof caps the verify mesh equals the screen mesh;
  only the frequency count and balloon size change.
- Do not treat `notch = 0` as "no resonance": it means no narrow dip was found on this grid's frequencies.
