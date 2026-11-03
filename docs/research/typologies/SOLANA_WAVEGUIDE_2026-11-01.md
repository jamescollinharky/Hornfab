# Solana 2.0 waveguide — Ath OS-SE + SF + morph reconstruction

2026-11-01. Reconstructs the **Solana 2.0** waveguide from John White’s DIY Guide
Rev 2.0 and the published `Advanced/athscript.cfg`. Phase 1 = **CD-only** exterior
BEM (freestanding). Not a product replica with mids / enclosure / LF; those are phase 2+.

## 1. Sources

| Source | What it gives us | Status |
|---|---|---|
| `solana_2026-11-01/Solana_DIY_Guide.pdf` (Drive `1-JxZ-kiKPOWCt2scCjO30Zmw2UrZ6M3o`, John White, Rev 2.0 2026-08-31) | Specs 90×90, box 41×41×34 cm, drivers 4×6NDL38 + DH450, acoustic XO 1200 Hz LR6, GA narrative | primary (author) |
| `solana_2026-11-01/Solana_DIY_Guide_layout.txt` | `pdftotext -layout` extract | derived |
| Required-files zip Drive `151N2rq4G5uEsQWhfzuLptj0D8ulQ8oLd` → `Advanced/athscript.cfg` | **Verbatim Ath4 pins** for the WG | primary (author) |
| Same zip → Waveguide Quarter/Half STL | Mouth/L bbox cross-check (not committed; re-fetch) | primary (author), measured locally |
| Official page https://www.jwsound.live/designs/solana-diy | Marketing specs (older copy; Rev 2.0 supersedes dims) | primary (author), marketing-style |
| Mini-MEH appendix A (`mini_meh_2026-10-29/`) | Prior Solana survey when plans were unreachable | secondary / superseded for geometry |
| `IMPLEMENTATION_PLAN_2026-10-27.md` §9 | Flute expressibility limits in our mesher | secondary (repo) |

## 2. Pinned geometry (`athscript.cfg`)

| Key | Ath | Our YAML |
|---|---|---|
| Profile | OS-SE (`Throat.Profile = 1`) | `family: OSSE` |
| `Throat.Diameter` | 25.4 mm | `r0_mm: 12.7` |
| `Throat.Angle` | 0 | `a0_deg: 0` |
| `Length` | 140 mm | `L_mm: 140` |
| `Term.s` / `q` / `n` | 1.165551339 / 0.8006927592 / 4.948341464 | `s` / `q` / `n` |
| `OS.k` | 2.326215907 | `k` |
| `GCurve.Type` | 2 (superformula) | `gcurve_type: 2` |
| `GCurve.Width` | 64.69512195 mm | `gcurve_width_mm` |
| `GCurve.Dist` | 0.2776715106 | `gcurve_dist` (~38.9 mm) |
| `GCurve.SF` | a,b,m,n1,n2,n3 = 1.376, 1.438, **8**, 2.153, 5.245, 3.015 | `gcurve_sf_*` (`m1=m2=8`) |
| `GCurve.AspectRatio` | 1 | `gcurve_aspect_ratio: 1` |
| Morph target | rounded rect 353×353, corner 14, rate 3.694, fixed 0.346, shrinkage 1 | `morph_*` |
| DIY Guide coverage | 90° × 90° CD | brief target |
| DIY Guide box | 41×41×34 cm; Ath enclosure Spacing 29 mm → 353+2×29≈411 | context |
| Drivers | 4× B&C 6NDL38 + B&C DH450 | phase 2+ MEH |
| Acoustic XO | 1200 Hz LR6 | context |

## 3. Gaps (honest)

1. **`a` / coverage angle is not in `athscript.cfg`.** Default `a_deg: 45` (half of Guide 90°). Morph owns the square mouth; raw OS-SE may differ.
2. **`Morph.Exponent`** absent in Ath script (target shape 1 = rounded rectangle; our `morph_exponent` unused for target 1).
3. Ath script sets `Mesh.Quadrants = 1234` and an **enclosure** block (Spacing 29, Depth 330). Our phase-1 solve is **freestanding quarter** (`quadrants: "1"`, no enclosure) — disclose in evidence; do not invent a mounting.
4. Mid **entry ports** are not in the Ath WG script (they live in Fusion / print STLs). Phase 1 is CD-only.
5. Guide Rev 2.0 supersedes earlier web copy (109/120 dB, 45–17 kHz marketing) — use Guide + athscript for geometry; treat old web SPL as secondary.

## 4. STL + mesh cross-check (local, 2026-11-01)

Waveguide Quarter.stl bbox ≈ **188 × 188 × 156.8 mm** (acoustic L = 140 mm + rear flange ~17 mm).
Full outer mouth ≈ **376 mm**; Ath morph acoustic target **353 mm**.

Dry-run mouth (quarter bbox → full):

| Variant | Full mouth (mm) | Notes |
|---|---|---|
| athscript pins (gcurve + morph_fixed 0.346) | **~450 × 450** | L bbox z≈146 mm |
| same, `morph_fixed=0` | ~389 × 389 | closer, still >353 |
| gcurve off, morph on | **~356 × 356** | matches morph 353 |

**Finding:** with SF m=8 engaged, our mesher’s acoustic mouth exceeds Ath’s morph target and the printed STL outer (~376). Morph-only (no gcurve) lands on 353. Treat phase-1 numbers as **athscript-keyed reconstruction with a known mesher/Ath mouth delta**, not byte-matched Ath geometry. Do not silently shrink `gcurve_width` to hide it.

## 5. Benchmark gates (phase 1)

1. Mesh dry-run: L≈140 mm, morph 353×353, SF m=8, no refuse.
2. One CD-only screen Metal solve; record bw_h/bw_v vs 90/90, Z, dofs, time.
3. Label: **Solana 2.0 Ath-script reconstruction**, not “matched Solana product”.

## 6. Phase 2 MEH configs (2026-11-03)

Landed (MEH CAD pyramid + ports — **not** Ath morph WG):

| File | Role |
|---|---|
| `examples/briefs/solana_meh_1in_90x90.yaml` | DIY drivers (DH450 + 4×6NDL38), 90×90, XO ~1200 Hz, HP 100 Hz |
| `examples/typologies/solana_meh.yaml` | CAD seed |
| `examples/typologies/solana_meh_search.yaml` | C9 searchable knobs |

**Disclosures:** (1) MEH `xo_orders` ∈ {2,4,8} — DIY acoustic LR6 approximated by searching [4,8]. (2) DIY rear chamber ~25 L vs MEH `v_rear_l` max 20 L. (3) DIY outer face **410 mm** refuses `drivers_collide` for 4×6.5 tblr @ 90×90 in `tools/cad/meh.py`; seed uses **450 mm** face (same depth 340 mm) with empty `layout_reasons`. Phase 1 `solana_osse` remains the Ath-script CD-only WG.

Still out of scope: enclosure / rear-port LF, Boundary Lab refine, Ath morph + mid ports as one solid.

## 7. WG estimate in MEH context (midports on)

Freestanding Ath CD-only (`solana_osse`) is **not** the MEH-context estimate. In MEH
context the waveguide is the horn body **with mid entry ports driven** (CD tag 2 +
mid tag 10), scored under the MEH brief (XO / HP / multi-driver).

| Config | Role |
|---|---|
| `examples/typologies/solana_osse_meh_sf.yaml` | **Primary MEH-context estimate** — Ath OSSE+SF/gcurve+morph + L1 `mid_ports` (tag 10) via mesher fork `hornlab-search/osse-midports` @ `55da4f4`; brief `solana_meh_1in_90x90` |
| `examples/typologies/solana_meh_wg.yaml` | Flat CAD MEH **fallback** — pyramid + tblr ports (no Ath SF surface) |
| `examples/typologies/solana_meh.yaml` | Same CAD solid, search budget 40 |
| `examples/typologies/solana_osse.yaml` | Ath `athscript.cfg` CD-only freestanding (no midports) |
| `examples/typologies/solana_osse_sf_search.yaml` | Ath SF CMA, CD-only (no midports) |

Mesher pin: `jamescollinharky/hornlab-waveguide-mesher` @ `55da4f46…` (opt-in `mid_ports`;
absent = byte-identical). Research grounding: this dossier + `ATH_SUPERFORMULA_AND_GSA`
+ `docs/meh/00_MEH_CONTRACTS.md` C3/C9 (flush exits only; no mid chambers).

Shape-check `solana_osse_meh_sf` [measured 2026-11-03]: ~2900 dofs / 14000, mouth
**450 × 450**, depth **152**, round coupling. MEH CAD fallback mouth bbox **450 × 450**,
depth **340**, dofs **~6981 / 12000**.
