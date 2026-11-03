# SAWMOD control waveguide (Ath OS-SE + morph) — phase-1 benchmark

2026-11-01. Reconstructs the **control** waveguide from John White’s SAWMOD whitepaper
(same OS-SE guiding curve + rectangular morph as SAWMOD, **no knuckles**). CD-only
exterior BEM. Not a product replica; not the knuckled MEH.

## 1. Sources

| Source | What it gives us | Status |
|---|---|---|
| `sawmod_2026-11-01/SAWMOD_Whitepaper.pdf` (Drive id `1syMFCG_lR-y50MgsxHh2g_IYP4hq_mog`, John White, 2026-04-07) | OS-SE pins, morph rate 4, stations, coverage 100×70, XO 1.6 kHz | primary (author) |
| `sawmod_2026-11-01/SAWMOD_Whitepaper_layout.txt` | pdftotext -layout extract | derived |
| Ath OS-SE / Morph (at-horns.eu; mesher native OSSE + morph_*) | Construction we implement | in-repo / primary Ath |
| Boundary Lab `Multi_region_SAWMOD` | Full MEH refine (phase 2+) | out of scope here |

## 2. Pinned geometry (whitepaper §3.1 / §4.2)

| Key | Value | Our YAML |
|---|---|---|
| `L` | 115 mm | `L_mm: 115` |
| `s` | 0.8 | `s: 0.8` |
| `q` | 0.996 | `q: 0.996` |
| `n` | 4 | `n: 4` |
| `r` | 12.7 mm | `r0_mm: 12.7` |
| `α0` | 0 | `a0_deg: 0` (brief `exit_angle_deg: 0`, policy pin) |
| `k` | 1 | `k: 1` |
| Morph | rectangle, rate 4 | `morph_target: 1`, `morph_rate: 4`, `morph_fixed: 0` |
| Coverage | 100° H × 70° V | brief target |
| Stations | S1 53.5 / S2.5 84.25 / S3 115 mm | evidence checks |
| Mid–high XO | ~1.6 kHz (λ/4 = 53.5 mm) | context only |

## 3. Gaps (honest)

1. **Ath `a` (coverage angle)** is not printed in the text — figure only. Default:
   `a_deg: 50` (half of 100° included H). V coverage is carried by morph aspect 100/70.
2. **Mouth W×H mm** not printed. Default morph extents from conical half-angle estimate:
   `W ≈ 2·L·tan(50°) ≈ 274` → **280 mm**; `H ≈ 2·L·tan(35°) ≈ 161` → **196 mm**
   (aspect 100/70). Measured mesh mouth replaces these in the evidence doc if different.
3. **`s1` / `s2`** not listed → pinned **0**.
4. Paper AKABAK = **half-space infinite baffle**; our default solve is **freestanding** —
   disclose in evidence; do not invent a mounting.
5. **Measured (2026-11-01):** raw OSSE mouth ≈ 395 mm square; morph target 280×196 needs
   `morph_allow_shrinkage: 1`. Mesh bbox after morph: full mouth **280.2 × 196.0** mm,
   L = **115** mm. Screen Metal: 1464 dofs, run `20261101T205918Z-screen-e7b5a2`
   (`docs/evidence/SAWMOD_CONTROL_WG_2026-11-01.md`).

## 4. Benchmark gates

1. Mesh dry-run: L≈115 mm, r0=12.7, morph rate 4, no refuse.
2. One CD-only screen solve; record bw_h/bw_v vs 100/70, Z, dofs, time.
3. Label: **control-waveguide reconstruction**, not “matched SAWMOD”.

## 5. Out of scope (phase 2+)

Knuckles (S2 superformula), mid bandpass ports, dual 10″ / 22 L slot, BL coupled refine.
