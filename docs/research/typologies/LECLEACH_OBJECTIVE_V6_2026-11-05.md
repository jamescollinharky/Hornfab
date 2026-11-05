# Le Cléac'h / loading_smooth — objective v6

2026-11-05. Scope: an honest scalar objective for **loading / rollback** horns (Le Cléac'h /
JMLC family first; Salmon rollback and similar class-B cells next), distinct from the
constant-directivity scorer used for Keele / OSSE waveguides. Research before code
(`hornlab-typology-research`). Status vocabulary is 9b.0's.

## 0. Bottom line

**Ship `objective.version: 6` (`loading_smooth`).** Briefs opt in; no silent typology→scorer
switch. Keele/OSSE stay on v4. Same BEM `Response` / metrics — different term definitions so
J ranks resistive loading, impedance smoothness, and a **natural DI rise**, not flat beamwidth.

Do **not** compare raw J across v4 and v6 briefs.

## 1. Source table

| Source | What it gives us | Status |
|---|---|---|
| J.-M. Le Cléac'h, **ETF 2010** lecture (Horn_Profiles / measurements decks) | Equidistant wall-normal wavefronts; T family; mouth rollback lowers reflectance / diffraction; DI rises with frequency; "good horn = less reflected/diffracted energy + HOMs" | **primary (author)** |
| J. Fourcade, "Calcul du Pavillon Le Cléac'h", 2015 | Exact construction eqs 10–27, 42–43; reference case | **primary/secondary, verifiable** — see [JMLC_LECLEACH_RESEARCH_2026-10-25.md](JMLC_LECLEACH_RESEARCH_2026-10-25.md) |
| Jmmlc diyAudio (thread 140190) | T≈0.7–0.8 for midrange CDs; group-delay use-above-X; E-JMLC not called CD | **primary (author, forum)** |
| Kolbrek, audioXpress Part 2 | Principle summary (equidistant fronts + Salmon law) | secondary |
| jhsaudio LeCleac'h vs conical | Smooth rising DI (~4→12 dB) preferred over conical DI wobble for imaging / XO | secondary (practitioner) |
| Ath4 diyAudio discussion of JMLC | "Smoothness of the pressure field" + resistive load; polar beaming is the trade | secondary (practitioner reports) |
| [LANE_A_LECLEACH.md](../campaign_2026-10-26/LANE_A_LECLEACH.md) | fc = loading corner; pattern ~1.5–1.8×fc; **dislope must be 0**; load+z_min honest | **[measured] in-repo** |
| [SIM_VS_REAL_HORN_2026-10-27.md](../SIM_VS_REAL_HORN_2026-10-27.md) | Band-mean `load` dilutes near-cutoff deficit; recommend integral/max near f0 | **[inferred] + [measured]** |
| [V4_SCORING_REVIEW_2026-10-27.md](../V4_SCORING_REVIEW_2026-10-27.md) | Loading brief ranking collapse under CD-shaped normalisation | **[measured]** |
| [V4_TOLERANCE_RESEARCH_2026-10-27.md](../V4_TOLERANCE_RESEARCH_2026-10-27.md) | Class B block: looser DI slope, load on | proposal [E] |

## 2. Corrected claims vs CD scoring

| Claim | Correction | Label |
|---|---|---|
| Score Le Cléac'h with flat `cov` + `dislope→0` like Keele | Flat beamwidth is the Keele/OS goal. JMLC **narrows by design**; demanding constant cov across the band fights the construction. | [verified] ETF2010 + LANE_A |
| Brief remapping (`dislope:0`, `load:0.5`) is enough | Intent correct; band-mean `load` was ~**2 % of J** on the class-B seed — HF loaded points dilute the cutoff deficit. Need a near-corner aggregator. | [measured] campaign / SIM_VS_REAL |
| `f0_hz` is a Keele pattern-control frequency for JMLC | For this family **f0 is the loading corner** (fc). Pattern control starts ~1.5–1.8×fc. | [measured] LANE_A §0.3 |
| Flat DI is preferred (Toole/Olive CD literature) | Preference literature supports smooth DI for *speakers*; JMLC's published virtue is smooth **rising** DI + loading, not CD plateau. Class-B must not inherit CD `dislope`/`distd` defaults blindly. | [inferred] from primaries |

## 3. Term math (v6)

Reuse v4 tolerance normalisation:

```
J = Σ_k  w_k · term_k / tol_k  + penalty
```

Stored `terms[k]` are the **normalised** values (`term_k / tol_k`).

### 3.1 Frequency anchors

- `fc_hz` = design knob `g_fc_hz` or `fc_hz` if present, else `objective.fc_hz` if set, else
  `target.f0_hz` (loading corner for this class).
- `f_load_hi = max(f0, load_alpha · fc_hz)` with default `load_alpha = 1.0`.
- `f_pattern = pattern_beta · fc_hz` with default `pattern_beta = 1.6`.

### 3.2 Weighted terms

| Key | Raw term | Default w | Default tol | Notes |
|---|---|---|---|---|
| `load_near` | Frequency-weighted **mean** of `max(0, z_min − Re z)` on `band ∩ [band_lo, f_load_hi]`, plus `max(0, (f_loaded − f0)/f0)` when `f_loaded_hz` / `f_load_hz` is known | 1.0 | 0.25 | Integral-style: each in-band point counted; a dead zone near fc cannot hide among HF. Missing z → `NAN_TERM_FILL`. |
| `z_smooth` | `std(Re z)` on `band ∩ (f ≥ f0)` (finite samples; need ≥2) | 0.8 | 0.15 | Mouth-reflectance proxy (ETF spectrograms / in-repo `z_ripple`). |
| `flat` | Detrended on-axis roughness when Response allows; else `std(on_axis)` | 0.5 | 1.5 | Same spirit as v2 flat. |
| `rip` | Mean of detrended H+V in-coverage ripple when Response allows; else v1 ripples | 0.8 | 2.0 | Natural beam taper not punished. |
| `cov_pat` | Same squared beamwidth error as v3/v4 cov, but scored only for `f ≥ f_pattern` (plus optional one-sided narrow-only below via `cov_below_f0`) | 0.3 | 15.0 | Pattern honesty above the control band. |
| `di_rise` | `(di_slope_db_per_decade − di_slope_target)²` on `f ≥ f0` | 0.4 | 4.0 | Brief sets `target.di_slope_target` ≈ **+5** dB/decade (class mid of +4..+6). |
| `distd` | `std(DI)` on `f ≥ f0` | 0.3 | 2.0 | Smooth rise yes; jagged DI no. |
| `diag` | v4 diagonal term (round reference); off unless weighted | 0.0 | 4.5 | Asymmetric / petal variants. |

Legacy CD keys (`cov`, `load`, `dislope`, `di`) are **not** in the v6 weighted set (superseded by
`cov_pat` / `load_near` / `di_rise`).

### 3.3 Out of scope (do not invent)

- Time-domain mouth reflectance / group delay from BEM without a validated IFFT path.
- Driver-coupled efficiency (P12 lumped driver over Z_throat) — follow-on.

## 4. Validation plan

1. **Unit:** closed-form fixtures in `tests/test_objective_v6.py` (constant Re z → `load_near` 0;
   sinusoidal Re z → `z_smooth`↑; DI +5 dB/dec → `di_rise`≈0; beamwidth wrong only below
   `f_pattern` → `cov_pat`≈0).
2. **Re-score:** cached `native__lecleach_*` / rollback records — `load_near`+`z_smooth` should
   dominate (≥20–40 % of weighted J on loading seeds).
3. **Physics spot-check:** small-mouth/high-fc vs large-mouth/low-fc — v6 prefers the better-loaded
   design even if HF beamwidth is narrower.
4. Keele under a **v4** brief remains bit-comparable to prior v4 runs.

## 5. Wiring

- `hornlab_search/objective/scalar_v6.py` — `V6Params`, `objective_v6`, defaults.
- `objective/versions.py` adds `6`; `search/evaluate.py` dispatch; `config.py` block validation +
  penalty-ordering gate (same invariant as v4/v5).
- Briefs: `examples/briefs/**/*_v6.yaml` for Le Cléac'h class-B; leave v4 untouched.
