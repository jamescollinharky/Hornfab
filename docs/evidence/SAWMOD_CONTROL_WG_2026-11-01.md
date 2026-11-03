# Evidence: SAWMOD control-waveguide benchmark (phase 1)

2026-11-01 · Mac `.venv` · `beat_metal` · branch `meh/integration`.

**Label:** control-waveguide reconstruction (Ath OS-SE + morph). **Not** a matched
SAWMOD product; **no knuckles / mid ports / LF**.

Dossier: `docs/research/typologies/SAWMOD_CONTROL_WAVEGUIDE_2026-11-01.md`.
Config: `examples/typologies/sawmod_control_osse.yaml`.
Brief: `examples/briefs/sawmod_control_1in_100x70.yaml`.

## Caveats (bind)

1. Paper AKABAK = half-space infinite baffle; this solve is **freestanding** (stack default).
2. Ath `a` and mouth W×H are **not** in the whitepaper text — defaults `a_deg=50`,
   morph 280×196 (aspect 100/70). Measured mouth after morph matches that target.
3. Raw OSSE mouth before morph ≈ 395 mm; `morph_allow_shrinkage: 1` is required for the
   280×196 target (Ath default 0 floors the morph up).

## Dry-run (mesh gate)

```
dry-run [screen] sawmod_control_osse: mesh 2774 triangles, 1464 dofs (estimate 1415, cap 5000), quadrants '1' <-> symmetry 'yz+xz'
  mesh built in 0.9 s; f_max 8000 Hz at epw 6; res_mm {'throat': 3.5729..., 'mouth': 7.1458..., 'rear': 7.1458...}; bbox_m (0.0, 0.0, -0.006, 0.1401, 0.098, 0.115)
dry-run OK: no solver was launched (mode screen, 1464 of 5000 dofs)
```

| Check | Expected | Measured |
|---|---|---|
| Axial length | 115 mm | bbox z_max **0.115 m** |
| Mouth (full, from quarter bbox) | ~280 × 196 mm | **280.2 × 196.0 mm** |
| Throat / r0 | 12.7 mm | pinned; source present |
| Stations S1 / S2.5 / S3 | 53.5 / 84.25 / 115 mm | all on `[0, L]` axis |
| Morph rate | 4 | pinned `search: false` |

## Screen solve (CD-only)

```
run OK: seed J=345.246, 1464 dofs, solve 5.4 s; output runs/20261101T205918Z-screen-e7b5a2
  terms (raw): cov=33.99  rip=0.9145  di=2.621  dislope=612.8  flat=6.264  load=0  penalty=0  total J=345.246  DI source=balloon
```

Backend: `beat_metal`. Frequencies (12): 500 … 8000 Hz.

| f (Hz) | bw_h (°) | bw_v (°) | DI (dB) | Re(Z) |
|---:|---:|---:|---:|---:|
| 500 | 180.0 | 180.0 | 3.80 | 0.014 |
| 643 | 139.4 | 152.5 | 5.28 | 0.067 |
| 828 | 113.1 | 132.3 | 6.73 | 0.089 |
| 1065 | 90.5 | 115.1 | 8.22 | 0.074 |
| 1370 | 72.0 | 94.5 | 9.97 | 0.122 |
| 1763 | 60.6 | 75.7 | 11.57 | 0.298 |
| 2269 | 80.1 | 56.1 | 12.23 | 0.527 |
| 2919 | 68.9 | 42.0 | 13.22 | 0.747 |
| 3756 | 80.3 | 37.3 | 11.99 | 0.964 |
| 4832 | 99.4 | 77.6 | 10.41 | 1.191 |
| 6218 | 108.6 | 118.9 | 6.56 | 1.187 |
| 8000 | 148.5 | 178.3 | -2.42 | 1.164 |

Target coverage **100° H × 70° V**. Midband (~1.7–2.3 kHz near XO 1.6 kHz): H is
narrow of target (~60–80°); V near ~56–76°. DI rises strongly below `f0_hz` 1850 → large
`dislope` under v3 (expected for a short freestanding OSSE; paper §4.3 is qualitative /
baffled). Loading Re(Z) climbs through the midband (paper notes radiation impedance
behavior for the knuckled twin; control is “largely similar”).

## vs whitepaper §4.3 (qualitative only)

| Paper claim (control vs knuckled) | This reconstruction |
|---|---|
| Pattern control intent 100×70 | Mesh mouth aspect OK; beamwidths not constant-CD yet |
| Compensatory widening 3–7 kHz is a **knuckle** degree of freedom | Out of scope (no knuckles) |
| Wavefront stations at 53.5 / 84.25 / 115 mm | Geometry length matches; field slices not re-exported here |

## First refuse (recorded)

`morph_allow_shrinkage: 0` → mouth 395×395 > brief envelope → `invalid_geometry` run
`20261101T205859Z-screen-2ca9a5`. Fixed by shrinkage=1 + envelope 420×420.

## Phase 2+

Knuckles (superformula params from figures), mid ports / multi-source, LF slot, BL
`Multi_region_SAWMOD` refine.
