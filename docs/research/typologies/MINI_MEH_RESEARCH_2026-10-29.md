# Mini multiple-entry horn (MEH): research dossier and plan seeds

2026-10-29. Owner request (dictated): an internal + external research pass toward designing and optimising a **mini
multiple-entry horn** (Synergy / Unity class), smaller than JW Sound's Solana, one compression driver plus cone mids
on ports (2 x 6-inch or 4 x 4-inch), very small box, solid bass extension for EDM. **Research and plan seeds only: no
code in `hornlab_search/`, no configs, no GPU.** The goal is the parameter set, the measures and the typologies a later
plan will implement, and how the search (CMA-ES over GPU BEM) and a Boundary Lab refinement step fit around them.

Protocol: `hornlab-typology-research` skill (inventory first, then outside research, corrections table, checkable
properties). MEH was **deferred by the owner on 2026-10-24** (senior_pass 02 s6, row G17); this pass reopens it for
research only.

Labels: **[verified]** read in source or primary by the orchestrator; **[lane-verified]** read by the web lane
(through a summariser) and not re-read here; **[measured]** computed by a script in `mini_meh_2026-10-29/calc/`;
**[inferred]** our reasoning; **[practitioner]** builder/forum report; **[snippet]** search excerpt only;
**[unverified]** needs a check.
Raw web survey (Sonnet lane, verbatim, 490 lines): `mini_meh_2026-10-29/appendix_A_web_survey_raw.md`; read it
through s8. Scripts and outputs: `mini_meh_2026-10-29/calc/` (pure numpy/scipy, CPU, research only, imported by
nothing, outside `tests/`).

## 0. The short version

1. **Bass for EDM cannot come from the mid cones of a mini MEH.** Excursion-limited output at 50 Hz, 1 m, half space:
   4 x 4-inch ~93-95 dB, 2 x 6.5-inch ~97-101 dB. 115 dB at 50 Hz needs ~840 cm^3 of volume displacement (one
   18-inch). [measured; the lane's driver-specific numbers agree within 2 dB] Every maker does the same:
   Danley SM-60F high-passes at 50 Hz, SH75 at 60 Hz, JW Solana at 100 Hz with a sub. [verified / lane-verified]
2. **The owner's size class already has a published reference: JW Sound's "DH350-based MEH".** It uses 2 x B&C 6NDL38
   + 1-inch B&C DH350 + 2 passive radiators in 470 x 260 x 200 mm (~15 L net, 6.75 kg). It measures 60 Hz-16 kHz
   +-2 dB at 106 dB max, limited by Xmax, with 75 x 60 coverage. Taps sit a quarter wavelength at the crossover
   (1.0-1.2 kHz) from the CD exit. [verified] It is the natural reference case for typology T2.
3. **Solana** = 4 x 6.5-inch + 1-inch CD, 45 Hz-17 kHz (vented, low-tuned), 109 dB full range / 120 dB with a 100 Hz
   high-pass, 90 x 90 controlled to 700 Hz, GA-optimised waveguide; **no dimensions published**. [verified]
4. **A mini mouth holds a pattern only down to ~1 kHz** (300 mm: 90 deg to ~940 Hz; Solana's 90 x 90 to 700 Hz implies
   roughly a 400 mm mouth). [measured K-law; Solana inferred]
5. **Two different notches govern an MEH**, and the 1-D sketch separates them:
   - **the mid's own reflection notch** (its sound bounces off the closed throat end), which caps each mid's top
     frequency (Synergy patent claim 1);
   - **the CD notch** cut by the passive mid ports, which sits ~1.15-1.4 x the port's own corner.

   In a conical horn the reflection notch is 1.4-1.8x higher than the cylindrical c / 4d rule, **but a compression
   driver's internal duct behind the throat pulls it back down to ~1.6-1.9 kHz**. That matches the practitioners'
   "mids top out near 1.5 kHz" and their advice to use shallow CDs. [measured, 1-D]
6. **Entry distance is the core trade-off.** Close to the throat the mids sum cleanly but notch the CD deeply
   (-18 dB at 20 mm); far out the notch fades and the crossover sum gets rough. The best sum sits near the
   quarter-wave limit, which is also where JW put the DH350 MEH taps. [measured, 1-D; verified]
7. **Our solver can already do most of the hard part.** The Julia engine solves one Neumann column per channel on one
   factorization and returns each channel's complex pressure. Only the Python wrapper refuses more than one source
   tag, and nobody computes the cross-impedance matrix yet. [verified, fork source]
8. **That makes a two-level search natural.** The GA moves geometry (BEM solve); for each solved geometry an inner
   optimiser picks drivers, chamber volumes, crossover, delay and polarity from the stored per-entry transfer
   functions and impedance matrix. That inner step takes milliseconds and needs no new solve. On the 1-D model this
   decomposition equals the direct solve to 6e-16. [measured]
9. **Boundary Lab is the right refinement tool, and v0.5.0 is still current.** It solves several voltage-driven drivers,
   FEM front chambers and several FEM-BEM port interfaces in one coupled system, so the mutual coupling comes from
   the physics. Its `Multi_region_SAWMOD` example (CD + 5-inch mid + 10-inch woofer, 3 FEM regions, quarter
   symmetry, LR4/LR6 channels) is a ready template. It takes Mmd only and has no passive radiators. [verified]
10. **Nobody has published an MEH optimisation method.** The lane found no AES/JASA paper on MEH or on mutual coupling of
   wall-mounted drivers in a horn. Solana's "GA" is a one-line statement and MEH Studio (no licence) is a browser
   design tool. A BEM-in-the-loop MEH search with a stored per-channel dataset would be new. [lane-verified, absence
   claim]

## 1. Reading of the dictated request

| Heard | Read as | Changes the answer? |
|---|---|---|
| "not as large ... the Solana" | smaller than JW Sound's Solana (4 x 6.5-inch; size unpublished) | sets the size class; DH350 MEH (~15 L net) is the published small sibling |
| "your morning driver / I macher driver" | one compression driver | yes: 2-way MEH core |
| "too seccion drivers or maybe 4 in drivers on matsure" | two 6-inch (6.5") drivers, or four 4-inch, "I'm not sure" | two candidate mid complements, both studied |
| "really small, solid good bass extension for EDM" | very small box, strong low end for dance music | yes: forces s5 and the top + sub / 3-way split |
| "boundary lab" | JW Sound's Boundary Lab | the refinement / cross-check tool (s7.4, s10.7) |
| "use the genetic algorithm" | our CMA-ES search (`search/cma.py`) | the parameter-vector design in s10 |

## 2. Source table

Full external table: appendix A. Load-bearing sources:

| Source | What it gives us | Status |
|---|---|---|
| JW Sound, DH350-based MEH, https://www.jwsound.live/designs/dh350based-multiple-entry-horn | drivers, 470 x 260 x 200 mm, ~15 L net, 60 Hz-16 kHz +-2 dB, 106 dB (Xmax), 75 x 60, XO 1.0-1.2 kHz, taps lambda/4 at XO from CD exit; Ath + Hornresp MEH wizard + ABEC + Fusion | primary (author) [verified 2026-10-29] |
| JW Sound, Solana, https://www.jwsound.live/designs/solana-diy | 4 x 6.5 + 1-inch, 45-17k Hz vented, 109/120 dB (10 % THD, 1 m half space calc), 90 x 90 to 700 Hz, GA profile | primary (author) [verified] |
| US 8,284,976 B2 (Danley, Synergy), https://patents.google.com/patent/US8284976B2 | claim 1 (lower driver below its first cancellation notch), 4 (aperture coupling), 5 (entry section <= round with circumference 1 lambda), 6 (expansion rate); notch mechanism; ports = wall thickness; tapered/stepped ports | primary (author, patent) [verified claims 1/4/5/6 + passages] |
| US 6,411,718 B1 (Danley & Skuran, Unity) | claim 1 (lower drivers at a distance corresponding to 1/4 wavelength travel); entry openings sum to the horn area at the entry; out-of-phase notch tuning (notch ~2x crossover) | primary (author, patent) [lane-verified; re-read blocked 503/403] |
| Boundary Lab v0.5.0 + `examples/Multi_region_SAWMOD`, https://github.com/JWSound/boundary-lab | latest release; coupled multi-driver, multi-region, quarter-symmetric example with channels | tool (author) [verified release + example JSON] |
| MEH Studio, https://github.com/mroushdy/MehStudio | browser MEH design tool (2/4/6 mids), exports ABEC/AKABAK/BL meshes, front-chamber LC equations, BEAT topology audit; no project licence | tool [verified repo page] |
| Waslo, Synergy Calc V5 (2014), http://libinst.com/SynergyCalc/Synergy%20Calc%20V5.pdf | only detailed public MEH procedure (Hornresp inputs), CoSyne build, hole spacing <= lambda/4 | secondary (practitioner) [lane-verified raw] |
| Danley spec sheets (SM-60F, SM-96, SH75, SH-Mini, TH-Mini) | small-Synergy and compact-sub numbers | marketing (manufacturer) [lane-verified raw] |
| Manufacturer datasheets (B&C, FaitalPRO, 18 Sound, Celestion) | cone T/S, CD ratings | primary for T/S [lane-verified raw] |
| timini/horn-simulation issue #78, https://github.com/timini/horn-simulation/issues/78 | origin of our Mms-vs-Mmd rule ("10 to 20 percent of the mass term") | secondary [verified] (s8 correction) |
| Internal: senior_pass 02 s6 / G17; `docs/plan/12_RESEARCH_BASIS.md` s3, s9; `constants.py:18-19`; BL 0.5.0 research; `IMPLEMENTATION_PLAN_2026-10-27.md` s9; `DRIVER_MODEL.md`; cone-driver handoff; LANE_E | deferral, frozen-plan MEH notes, quarter-wave constant, BL inventory, Solana flute notes, driver circuit | internal |
| hornlab-beat-bem fork `llevaachingada/hornlab-beat-bem` main (cloned 2026-10-29) | `config.py:462-464` one tag; `capabilities.py:236-242, 380-390`; `BeatEngineDriver.jl:452-536` channel DSP, `:767-800` one Neumann column per channel, `:1030-1055` impedance from the mixed field, `:1590-1680` per-channel rows on the wire | verified (source read) |
| hornlab-waveguide-mesher `m3gnus/hornlab-waveguide-mesher` @ a833a7e | MEH tag names 8-12, `SOURCE_TAGS` = {2, 10, 11}; no MEH builder | verified (source read) |
| `calc/` scripts | first-principles tables; 1-D MEH sketch, sweeps, notch-vs-path, decomposition check | measured |

## 3. What the repo and our forks already know (inventory)

| Topic | Established | Gap |
|---|---|---|
| Owner decision | MEH deferred 2026-10-24 (G17); reopened for research 2026-10-29 | implementation needs an owner go |
| Solver, engine | multiple radiators per channel; per-channel level / polarity / delay / HPF / LPF; one Neumann column per channel, one factorization; fused CUDA builds all columns per frequency in one pass; per-channel complex H / V / diagonal / sphere rows returned [verified] | none at engine level for the far field |
| Solver, Python package | `SolveConfig.velocity_sources` must have exactly one tag (`config.py:462`); README "Not supported: multi-source drive"; coupled FEM-BEM-LEM present in the engine, unreachable from Python [verified + lane] | opt-in fork change: several tags, one unit-drive channel each |
| Entry coupling | `impedance_for_radiators` integrates the MIXED boundary pressure per radiator [verified] | per-channel, per-tag mean pressure = Z matrix (per-channel boundary pressures already exist in memory) |
| Mesh, parametric | horn families build one source (tag 2) | no ports |
| Mesh, CAD route | `mesh/step_build.py` maps `driver` -> 2, `wall` -> 1, refuses anything but exactly one `driver` face (`:274-279, 364`) [verified] | several labelled driven faces |
| Mesher tags | 8 `mid_chamber`, 9 `mid_port_interior`, 10/11 `mid_port_exit_left/right`, 12 `mouth_aperture`; 10/11 in `SOURCE_TAGS`; README: no supported builders for slots, ports, drivers, cabinets [verified + lane] | no builder; names are left/right-specific |
| Driver model | compression-driver circuit (front + rear chamber, conj(z) convention, Mmd rule) | no cone + front chamber + port entry network; no multi-port coupling |
| Boundary Lab | see s7.4 | our exporter covers single-source exterior only (plan) |
| Design checks | K-law, f11, `MEH_ENTRY_FRACTION = 0.25` in `constants.py` | none |

## 4. How a multiple-entry horn works (designer terms, now sourced)

1. **One horn, one apex.** A straight-walled (conical / pyramidal) horn has a near-spherical wavefront centred on the
   apex. Drivers entering near the apex leave the mouth as one wavefront. Unity: HF at the apex, mid/low drivers
   through holes in the sides or corners (US 6,411,718) [lane-verified]. Synergy horns are conical: the "transformation
   zone" ends where the circumference reaches one wavelength; beyond it the horn acts as a waveguide.
2. **Entries close to the apex.** Lower drivers enter at a distance corresponding to a quarter-wavelength travel at
   their top frequency (US 6,411,718 claim 1) [lane-verified]. Each entry also sits where the section is no larger than
   a round section of circumference one wavelength at that driver's top frequency (US 8,284,976 claim 5) [verified].
   JW placed the tap centroid at lambda/4 at the crossover from the CD exit [verified]. Waslo keeps the mid hole
   centres within lambda/4 of each other [lane-verified].
3. **The mid's ceiling is its own reflection notch.** "Sound from the driver, which travels to the closed end of the
   horn, is reflected back ... so as to arrive with 180 deg of phase shift" (US 8,284,976); claim 1 keeps each lower
   driver's upper end below its first cancellation notch [verified]. The patent calls the notch position "an acoustic
   dimension governed by the shape and size of the horn", not a physical distance [lane-verified]. s6.3 quantifies it.
4. **Front chamber + port = an acoustic low-pass.** "The trapped air volume under the cone and the small holes form an
   acoustical 2nd order low pass filter" (Danley, forum) [snippet]. The relayed practice is to put the port's natural
   roll-off at the notch and cross there [snippet]. Lumped form: f_LC = c / 2 pi * sqrt(S / (V L_eff)) (MEH Studio
   doc; our s5 table uses the same form, and MEH Studio's 610.3 Hz reference case reproduces with it) [verified
   arithmetic].
5. **Ports short, small, smooth.** Port length = local wall thickness; cutting 3/4-inch ports to 1/16-inch let 8 ports
   become 4; tapered (frustum) or stepped ports for thick walls (US 8,284,976) [verified]. Entry openings sum to the
   horn area at the entry point (US 6,411,718) [lane-verified]. Tap-area rules from builders conflict (Sd/15 to 25 % of
   Sd) [practitioner], so the tap area is a search knob, not a rule.
6. **The ports are holes in the HF horn.** Seen from the CD, each port + chamber + cone is a side-branch resonator: the
   "CD notch" (12_RESEARCH_BASIS s9: "universal, documented, unsolved"). Builders move entries to corners or "knuckles"
   and use shallow CDs [snippet]. s6.2 quantifies it.
7. **Crossover, polarity, delay.** CD/mid crossovers in practice sit at 1.0-1.5 kHz and mid/low at 315-400 Hz. Danley
   wants overlapping, non-integer-order slopes; the patent's tuning trick is to wire the drivers out of phase and
   sweep, where a notch near 2x the crossover appears, so the crossover is about half that notch. BL's SAWMOD example
   inverts the MF and LF (polarity -1) with +0.10 / -0.15 ms delays. [verified / lane-verified]
8. **Rear chambers sealed, per band** (US 8,284,976; Waslo seals mid backs with stuffed tubes). The bass section may
   be vented (Solana, low-tuned) or use passive radiators (DH350 MEH). [verified / lane-verified]

## 5. Size and bass: the honest numbers [measured, `calc/first_principles.md`]

Formulas: excursion-limited p = rho w^2 Vd Q / (4 pi r) (Q = 2, half space); Small's efficiency
eta0 = (4 pi^2 / c^3) fs^3 Vas / Qes (the lane checked it against four datasheets, within a few %); Keele's K-law
(`constants.KEELE_K`); quarter-wave d = c / 4f; Helmholtz port corner. Cone values in this section are class-typical;
real drivers are in s7.3. The three named-driver rows use datasheet Sd and Xmax (appendix A s8); the lane's own table
agrees to 0.1 dB at 40/50/80/100 Hz.

**Excursion-limited SPL, 1 m, half space (dB):**

| Complement | Vd (cm^3) | 40 Hz | 50 Hz | 63 Hz | 80 Hz | 100 Hz | 125 Hz |
|---|---|---|---|---|---|---|---|
| 4 x 4-inch mid (Xmax 3) | 66 | 89 | 93 | 97 | 101 | 105 | 109 |
| 4 x B&C 4NDF34 (57 cm^2, 3.8 mm) | 87 | 91 | 95 | 99 | 103 | 107 | 111 |
| 2 x 6.5-inch mid (Xmax 4) | 108 | 93 | 97 | 101 | 105 | 109 | 113 |
| 2 x B&C 6NDL38 (132 cm^2, 6 mm) | 158 | 97 | 101 | 105 | 109 | 113 | 116 |
| 4 x 6NDL38 (Solana-like) | 317 | 103 | 107 | 111 | 115 | 119 | 122 |
| 2 x 8-inch woofer | 264 | 101 | 105 | 109 | 113 | 117 | 121 |
| 2 x 10-inch woofer | 490 | 106 | 110 | 114 | 118 | 122 | 126 |
| 1 x 18-inch sub | 1200 | 114 | 118 | 122 | 126 | 130 | 134 |

Volume displacement for **115 dB at 50 Hz**: 841 cm^3; 120 dB: 1,496 cm^3. Vents and passive radiators add a few dB
near tuning only. Solana's published 109 dB full range / 120 dB with a 100 Hz HPF sits within 1.4-2.5 dB of the
4 x 6NDL38 line [lane, inferred]: it is excursion-limited, as physics says.

**Iron law (half-space sensitivity at 1 W, ideal vented B4):** 20 L tuned for f3 50 Hz -> 90 dB; 30 L -> 92 dB;
50 L -> 94 dB. Small boxes can reach 50 Hz; they cannot do it loudly. DH350 MEH (~15 L net, PRs) reaches 60 Hz at a
106 dB ceiling, the realistic top for this size [verified].

**Pattern control vs mouth (K-law floor, Hz):** 250 mm: 1,693 (60 deg) / 1,129 (90 deg); 300 mm: 1,411 / 941;
400 mm: 1,058 / 706; 500 mm: 847 / 564. Waslo's 24-inch, 90 x 60 CoSyne holds to ~385 Hz [lane-verified].

**Entry distance limits (quarter-wave):** 1.5 kHz -> 57 mm; 1.2 kHz -> 71 mm; 1 kHz -> 86 mm; 600 Hz -> 143 mm;
300 Hz -> 286 mm. **Port corners:** a 4-inch with 15-30 cm^3 front chamber and 10-15 cm^2 port sits at ~1.5-2.3 kHz;
a 6.5-inch with 100-160 cm^3 and 20-30 cm^2 at ~0.8-1.2 kHz. So 4-inch mids can cross higher (1.2-1.5 kHz), 6.5-inch
lower (0.8-1.2 kHz). A 1-inch CD at 1.0-1.2 kHz works at modest power (JW: B&C DH350, rated 15 W nominal, 1 kHz
12 dB/oct); for higher SPL at ~1 kHz the candidates are a larger 1-inch rated to 1 kHz or a 1.4-inch (FaitalPRO HF1440,
min 0.7 kHz) [lane-verified datasheets].

**Consequence for typologies:** "really small + EDM bass" means one of three things:
- **A 2-way mini MEH top + a separate sub** (the industry answer).
- **A one-box 2-way with 2 x 6.5-inch on vents or passive radiators**, the DH350 MEH pattern: ~60 Hz at ~106 dB, for
  small rooms, not clubs.
- **A larger 3-way MEH with woofers on the horn walls**: about 105-110 dB at 50 Hz half space with 2 x 8-10-inch in
  roughly 50-80 L. Danley's smallest 3-way Synergy-class boxes are 62 L (SH75, 2 x 8-inch, 80 Hz +-3 dB) to 113 L
  (SM-60F, 66 Hz +-4 dB). [lane-verified]

The owner picks; s13 Q1.

## 6. 1-D sketch: what entry geometry does [measured, 1-D, illustrative drivers]

Model (`calc/meh_1d_sketch.py`):
- **Horn:** flat-wall conical horn as an exact spherical-wave duct, checked against the analytic infinite-cone throat
  impedance to 4e-16.
- **Compression driver:** mass-controlled source with a 700 Hz 2nd-order resonance, plus an optional internal exit duct.
- **Each entry:** N cone drivers (T/S Thevenin + sealed rear box) into a front chamber, through a port neck, out of
  the horn wall.
- **Mouth:** baffled piston.

Horn 90 x 60 deg, 220 mm from apex, mouth 440 x 254 mm, 1-inch throat.

**Limits:** 1-D keeps only the spherical mode. It ignores where the port sits around the wall, port-excited
higher-order modes and mouth directivity. Its job is to show sensitivities and ranges, not final numbers.

![1-D MEH sketch](mini_meh_2026-10-29/calc/meh_1d_cases.png)

### 6.1 Summation (`calc/study_out.md`)

| case | entry path from throat | f_h | XO (LR4) | best delay / polarity | ripple through XO | CD notch |
|---|---|---|---|---|---|---|
| A: CD + 4 x 4-inch, 30 cm^3, 12 cm^2 | 50 mm | 1,624 Hz | 1.5 kHz | -0.04 ms, inverted | 2.3 dB rms | 1,865 Hz, -8.9 dB |
| B: CD + 2 x 6.5-inch, 120 cm^3, 25 cm^2 | 75 mm | 1,018 Hz | 900 Hz | 0.26 ms, normal | 1.2 dB rms | 1,189 Hz, -6.5 dB |

### 6.2 CD notch from passive ports

**Entry position sweep (case A):**

| entry path from throat (mm) | CD notch (dB) | sum ripple through XO (dB rms) |
|---|---|---|
| 20 | -18.2 | 5.2 |
| 35 | -13.8 | 2.6 |
| 50 | -8.9 | 2.3 |
| 70 | -2.4 | 2.5 |
| 95 | -3.1 | 3.0 |
| 125 | -3.5 | 4.5 |
| 165 | -0.7 | 5.2 |

The sweet spot is near the quarter-wave limit (57 mm at 1.5 kHz), not as close as possible, which agrees with JW's
tap placement.

**Front chamber / port sweep:** the notch tracks the port corner (notch / f_h = 1.15-1.4).
- 15 cm^3 chambers give the shallowest notches (-1.8 to -6.3 dB) and the smoothest sum (1.9 dB).
- 60 cm^3 chambers give -7.8 to -13.8 dB and 2.8-4.9 dB ripple.
- Small chambers mean high compression and fast port air, so the limit moves to port velocity (chuffing) and cone
  clearance, which the 1-D model does not see.

### 6.3 The mid's reflection notch (`calc/notch_vs_path.md`)

The notch depends only on the horn: it is identical for the 4-inch and 6.5-inch entries, as the patent says.

| d from throat (mm) | rigid throat: null (Hz) | c / 4d (Hz) | ratio | with a 35 mm CD exit duct: null (Hz) | c / 4(d + 35 mm) (Hz) | ratio |
|---|---|---|---|---|---|---|
| 20 | 5,781 | 4,249 | 1.36 | 1,949 | 1,554 | 1.25 |
| 35 | 3,662 | 2,437 | 1.50 | 1,838 | 1,222 | 1.50 |
| 50 | 2,728 | 1,709 | 1.60 | 1,748 | 1,007 | 1.74 |
| 70 | 2,050 | 1,222 | 1.68 | 1,620 | 815 | 1.99 |
| 95 | 1,571 | 901 | 1.74 | 1,424 | 659 | 2.16 |
| 125 | 1,228 | 685 | 1.79 | 1,181 | 535 | 2.21 |

What this shows:
- **The conical horn puts the notch higher than the cylindrical rule** (supports the practitioner remark in appendix A
  conflict 10).
- **The CD's internal duct dominates for close entries.** With 35 mm behind the throat, every entry within 50 mm has
  its notch at ~1.75-1.95 kHz, so mids must cross by ~1.2-1.5 kHz. That is the practitioners' ceiling, and it is why
  shallow CDs help.
- **For the plan:** the CD's real depth (diaphragm to exit) must be in the model, as mesh geometry behind the throat
  plane or as a duct in the CD's network. A BEM throat patch alone is a rigid reflector at the wrong place.

The 35 mm duct is illustrative; real values come from CD drawings.

### 6.4 Excursion and ranges

With no high-pass, 20 V (66 W into 6 ohm) drives the illustrative 4-inch past Xmax below ~200 Hz and the 6.5-inch
below ~120 Hz. Mids need a high-pass at 120-250 Hz at high level.

**Knob ranges for the search** (s10) [inferred from the sweeps + s7 rules; the BEM stage replaces these]:
- entry path: 0.6-1.3 x the quarter-wave limit of its upper crossover, measured to the CD diaphragm;
- port corner: 0.9-1.6 x the crossover;
- front chamber: 10-60 cm^3 (4-inch), 60-200 cm^3 (6.5-inch);
- tap area: 0.07-0.25 x Sd;
- delay and polarity: free.

## 7. External findings (web lane, 2026-10-29; full text in appendix A)

### 7.1 Reference designs in or near the target size

| Design | Drivers | Size | Band / level | Coverage | Notes | Label |
|---|---|---|---|---|---|---|
| JW DH350 MEH | 2 x B&C 6NDL38 + B&C DH350 (1-inch) + 2 x SB16PFCR PR | 470 x 260 x 200 mm, ~15 L net, 6.75 kg | 60 Hz-16 kHz +-2 dB; 106 dB max (Xmax) | 75 x 60 (goal 60 x 90) | XO 1.0-1.2 kHz; taps lambda/4 at XO from CD exit; Ath vs ABEC mismatch made it narrower | verified |
| JW Solana | 4 x 6.5-inch + 1-inch CD | unpublished | 45 Hz-17 kHz vented; 109 / 120 dB (100 Hz HPF) | 90 x 90 to 700 Hz | GA waveguide; SLA printed; critics: big port, port diffraction | verified (page); critique snippet |
| JW SAWMOD | CD + mids + woofer(s) | unpublished | XO to subs 80-100 Hz | 100 x 70, held to 300 Hz | bandpass ports on the waveguide "knuckles" to limit port/CD interaction | snippet; BL example verified |
| Waslo CoSyne (2014) | Celestion CDX1-1445 + 4 mids + 4 woofers | 610 mm wide 90 x 60 | ~94 dB; ~50 Hz in big ported box | 90 x 60 to ~385 Hz | Synergy Calc procedure; "takes a number of builds" | lane-verified raw |
| diyAudio 2-way MEH | FaitalPRO HF108 + 2 x 4FE35 | 300 x 300 mm mouth | XO 1.3 kHz; subs | 80 deg to ~850 Hz | closest 4-inch-class 2-way | snippet |
| Parts Express Synergy (2017) | 4 x 6.5 + 2 x 4.5 + 1-inch dome | stand-mount | LR4 1.3 kHz / 400 Hz; ~86 dB | 60 x 90 to 400 Hz | | lane-verified |

### 7.2 Danley and other commercial references

No Danley product is a small box with 2 x 6.5-inch or 4 x 4-inch + CD. Smallest Synergy-class:
- **SH75:** 62 L, 2 x 8-inch + 1-inch, 70 x 50, 80 Hz-24 kHz +-3 dB, 116/122 dB, 60 Hz HP.
- **SM-60F:** 113 L, 2 x 8-inch + 5-inch coax, 60 x 60, 66 Hz +-4 dB, 125/131 dB, 50 Hz HP.

**4 x 4-inch mids around a 1-inch CD is Danley's standard mid/high core** in the big boxes (SH50: + 2 x 12-inch,
328 L, 50 Hz; SH46 with a 1.4-inch CD) [lane-verified]. Yorkville U15 (licensed Unity) uses 3 x 5-inch mids in a
60 x 60 horn [snippet]. Compact subs to pair: TH28 103 L 47 Hz, THmini 133 L 48 Hz [lane-verified raw].

### 7.3 Driver shortlist (datasheet T/S in appendix A s8)

| Role | Candidates | Why | Caveat |
|---|---|---|---|
| 4-inch mid | B&C 4NDF34 (Bl 9.0, Mms 6.1 g, Sd 57, Xmax 3.8, EBP 393); FaitalPRO 4FE32 / 4FE35 (Mmd published) | strong motor, light cone; 4FE35 used in a 2-way MEH | low Xmax: HP >= 200 Hz at level |
| 5-inch mid | FaitalPRO 5PR160; B&C 5NDL38; SB NERO 5CCN125D (BL SAWMOD example) | in-between option | |
| 6.5-inch mid | B&C 6NDL38 (JW, Xmax 6); FaitalPRO 6PR160 (Mmd published); 18 Sound 6NMB420; B&C 6MDN44 | 6NDL38 = DH350 MEH reference; 6PR160 balanced | 6MDN44 / 6ND410: Xmax 2-2.5 mm |
| 1-inch CD | B&C DH350 (JW; 15 W nominal), DH450 (SAWMOD; 20 W), FaitalPRO HF108 (60 W, min 1.3 kHz), B&C DE250 (60 W, rec. 1.6 kHz) | shallow / small bodies help the mid notch (s6.3) | **no CD publishes Bl / Mmd / Cms** |
| 1.4-inch CD | FaitalPRO HF1440 (120 W, min 0.7 kHz) | for a ~1 kHz crossover at level | larger, deeper body |

The lane's Mmd = Mms - 2 (8/3) rho a^3 (a = sqrt(Sd / pi)) reproduces Faital's published Mmd. I re-checked it:
6FE100 14.0 - 2.1 = 11.9 g, 4FE32 4.2 - 0.43 = 3.8 g, both matching the datasheets. It is usable for drivers that
publish only Mms [verified arithmetic].

### 7.4 Boundary Lab (v0.5.0 still current; BEAT 0.6.0) [verified release + SAWMOD example; rest lane-verified raw]

- **Many drivers, one solve:** all excitation ports are solved as multiple right-hand sides of one coupled system.
  Mutual coupling is physical (monolithic or Schur-condensed); BEAT exposes a mutual radiation-impedance matrix for
  exterior electrodynamic transducers.
- **Electrodynamic transducer:** `re_ohm, le_h, bl_n_per_a, mmd_kg, cms_m_per_n, rms_n_s_per_m`, motion axis,
  optional semi-inductance and `lumped_sealed_rear_chamber`. Mms is not accepted. Voltage ports use a 2.83 V basis.
- **Channels:** trim, polarity, delay, LR/BW HPF/LPF, applied after the solve. Headless output stays per port.
- **Regions:** FEM `bounded_air` (P1 coupled, ~8 elements per wavelength for ~5 % modal error) + one BEM exterior.
  FEM-BEM interfaces work as ports. There is an output for port air speed (`interface_average_normal_velocity`).
- **Passive radiators:** schema only (rejected).
- **Symmetry:** coupled projects run with symmetry `xy` (the SAWMOD example). Our earlier note "named assemblies require
  symmetry Off" applies to generator-plugin assemblies only (s8).
- **VRAM planning (not hard limits):** 5k elements ~1-1.5 GB, 10k ~4-6 GB, 15k ~8-12 GB.
- **`Multi_region_SAWMOD`:**
  - drivers: DH450 CD + 5CCN125D mid (motion axis tilted ~24 deg, 0.34 L lumped rear) + 10RS430 woofer;
  - regions: 3 FEM (throat, side slot, sealed chamber) + 4 interfaces;
  - channels: HF LR4 1.6 kHz; MF LR6 360 Hz / LR4 1.6 kHz, polarity -1, +0.10 ms; LF LR6 360 Hz, polarity -1,
    -0.15 ms.

  Its CD component values are placeholders.

### 7.5 Modelling practice

- **Builder chain:** Hornresp's MEH wizard + Waslo's Synergy Calc (1-D) to set ports and chambers, Ath + ABEC for the
  waveguide, VituixCAD for crossovers from measurements.
- **MEH Studio** adds a browser workflow with mesh export to BL/ABEC/AKABAK. Its audit recommends one connected FEM
  volume for all front chambers + throat, a shared rear FEM volume, and one BEM exterior joined at the mouth. It has
  no licence, so cite it, don't copy it.
- **No published GA/BEM optimisation of an MEH** besides the Solana statement; no paper on mutual coupling of
  wall-mounted drivers in a horn.

## 8. Corrections

| Claim | Where | Correction | Evidence |
|---|---|---|---|
| "Tags 8 through 11 are multiple-entry-horn structures. The mesher already has MEH scaffolding ... the geometry path is already there" | `docs/plan/12_RESEARCH_BASIS.md` s3, s9; `docs/plan/04_TASK_DESIGN_MESH.md:289` (frozen) | The mesher defines tag NAMES (8-12) and lists 10/11 as source tags; its README says it ships no builders for slots, ports, drivers or cabinets. MEH geometry must come from our CAD -> STEP route (or a new builder) | `hornlab_mesher/tags.py` @ a833a7e; mesher README (lane) |
| "Julia driver already loops several channels on one factorization" | senior_pass 02 s6 | Confirmed and sharpened: one Neumann column per channel; fused CUDA builds all columns per frequency in one pass; per-channel pressure rows returned; impedance from the mixed field only | fork `BeatEngineDriver.jl:767-800, 1030-1055, 1590-1680` |
| "Boundary Lab issue #78: 10-20 % low-frequency error" | `docs/DRIVER_MODEL.md:42` (also "issue #78" in `SIM_VS_REAL_HORN_2026-10-27.md`) | The source is **timini/horn-simulation issue #78** ("Evaluation: JWSound/boundary-lab compared to horn-simulation ..."); BL's own #78 does not exist (404). It says Mms - Mmd is "of order 10 to 20 percent of the mass term". The Mmd rule stands (BL docs: `mmd_kg` only). Attribution fix only | GitHub, fetched 2026-10-29 |
| "Named assemblies require project symmetry Off" read as a BL limit for coupled MEH models | `docs/BOUNDARY_LAB_0.5_RESEARCH.md` s4 / `bl_inventory.md` (our inventory) | Applies to generator-plugin assemblies. A coupled multi-region PROJECT runs with symmetry `xy` (`Multi_region_SAWMOD`) | example JSON, verified |
| "6.5-inch mids ask for a 1.4-inch driver" | this dossier, first draft s5 | A 1-inch works at 1.0-1.2 kHz at modest power (JW DH350 MEH, DH350 rated 15 W); for level at ~1 kHz a 1.4-inch or a larger 1-inch rated to 1 kHz | JW page; B&C / Faital datasheets (lane) |
| Mid notch at c / 4d of the throat-to-port distance | practitioner rule (appendix A conflicts 8, 10) | Conical horn with a rigid throat: notch 1.36-1.79x higher; with a 35 mm CD duct and d measured to the diaphragm: 1.25-2.2x. The rule is conservative; measure to the diaphragm | `calc/notch_vs_path.md` [measured, 1-D] |
| Synergy patent "8248976" | forum list (appendix A conflict 2) | US 8,284,976 B2 | Google Patents, verified |
| Tap-area "rules" (Sd/15 MF, Sd/8 LF; 25 % Sd; 10-12 % of one woofer) | practitioners (appendix A conflict 6) | Conflict by 2-3x; treat as a search range (0.07-0.25 Sd), not a rule | appendix A |
| Lane spot-checks by the orchestrator | appendix A | DH350 MEH page, Solana page, US 8,284,976 claims 1/4/5/6 + notch/port passages, BL releases (v0.5.0 latest), SAWMOD example, MEH Studio page: all match. US 6,411,718 claim text: not re-readable here (503/403) | 2026-10-29 fetches |

## 9. Typology candidates (hypotheses; names neutral until a published geometry is matched)

R9 rename-gate pattern: no published MEH geometry with dimensions exists to match within 1 mm, so every candidate is a
labelled experiment. Published **performance** (DH350 MEH, Solana) serves as a sanity reference, not a geometry gate.

| ID | Name (working) | Drivers | Horn | Entries | Band / crossovers | Box | Bass | Reference |
|---|---|---|---|---|---|---|---|---|
| T1 | `meh2_4x4` | 1-inch CD (shallow) + 4 x 4-inch | conical 90x60 / 80x80 / 90x90, 160-250 mm deep | 4 ports (one per wall, or corners), d 35-70 mm to the diaphragm | mids HP 200-250 Hz, XO 1.2-1.5 kHz | ~12-25 L [inferred] | sub, XO 80-120 Hz | Danley 4 x 4-inch core; diyAudio HF108 + 2 x 4FE35 |
| T2 | `meh2_2x65` | 1-inch (low-XO) or 1.4-inch CD + 2 x 6.5-inch | conical 75x60 / 90x60, 200-300 mm deep | 2 ports on opposite walls (or 4 smaller per driver), d 55-90 mm | mids HP 100-150 Hz (with sub) or full range, XO 0.9-1.2 kHz | ~15-30 L | sub, or T2b | JW DH350 MEH (2 x 6NDL38 + DH350, ~15 L net) |
| T2b | `meh2_2x65_pr` | as T2 + 2 passive radiators or a low-tuned vent | as T2 | as T2 | ~60 Hz-16 kHz at ~106 dB | ~15-25 L net | in-box, small rooms | JW DH350 MEH (measured 60 Hz-16 kHz +-2 dB, 106 dB) |
| T3 | `meh3_compact` | T1 or T2 core + 2 x 8-inch or 2 x 10-inch | conical, 250-350 mm deep | mids as T1/T2; woofers through large openings near the mouth, d <= c / 4 f_w | woofers to ~300-400 Hz | ~50-80 L | ~105-110 dB at 50 Hz half space in-box | Danley SH75 (62 L) / SM-60F class; Solana 4 x 6.5-inch vented |
| T4 | `meh_fluted` (later) | as T1/T2 | lobed / fluted walls, entries between flutes | as T1/T2 | as T1/T2 | as T1/T2 | as T1/T2 | Solana (no geometry published) |

T4 needs the harmonic FREEFORM station or a CAD wall law (IMPLEMENTATION_PLAN_2026-10-27 s9b) and T1/T2 first.
T2b's passive radiators are not in BL (schema only), so PRs stay lumped on our side. A PR or vent radiates outside
the horn, so it needs its own BEM channel (a patch on the box surface).

**Checkable properties (before any typology code ships):**
- **Geometry:** apex, wall angles and mouth W x H match the knobs within 0.2 mm; every port lies wholly on its wall;
  the entry path to the CD diaphragm is reported and checked against `MEH_ENTRY_FRACTION`; the entry section passes
  the claim-5 circumference check.
- **Topology:** quarter symmetry holds (ports mirror-paired); each entry group is one labelled tag; the CD coupling
  plane is round at the exit (owner throat rule); the CD's internal depth is represented.
- **Solver bookkeeping:**
  - superposition: solve the channels separately and together, and get the identical field;
  - reciprocity: Z_ij = Z_ji within solver noise;
  - the symmetry copy factor on Z (the 6.02 dB trap in `impedance_for_radiators`);
  - port-patch sign: a positive drive pushes air into the horn, in phase with the CD at low frequency.
- **Network:** with entries blocked (Y = 0) the CD-only response equals the single-source solve; the 1-D sketch and the
  BEM agree below the first cross-mode at the entry; the mid reflection notch from the BEM matches the 1-D trend
  (s6.3).

## 10. Mapping onto hornlab-search

### 10.1 Solve strategy: one geometry solve, many systems

```
geometry knobs --CAD/STEP--> mesh with tags: CD throat (2), entry group A (e.g. 10), entry group B (e.g. 11), [PR / vent patch]
     |
     v  BEM, one factorization per frequency, one unit-drive channel per group (quarter model)
per-channel complex H / V / diagonal / sphere pressures  +  Z matrix (mean pressure on tag i per unit drive of j)
     |
     v  post-solve network (no BEM): driver T/S + rear box (+ PR / vent) + front chamber + port neck per group
        (Norton U_sc, Y); CD model incl. its internal duct; crossover / gain / delay / polarity / EQ per channel
U = (I + Y Z)^-1 U_sc   ->   p(theta, f) = sum_j H_j(theta, f) U_j   ->   metrics -> J
```

The coupled step `U = (I + Y Z)^-1 U_sc` puts the CD notch, the port loading of the mids and the mid-to-mid
interaction into the result without meshing the chambers (level L1 below). It is the standard BEM + lumped-network
method (AKABAK pattern); BEAT exposes the same mutual radiation-impedance idea for exterior transducers (s7.4).

**Checked on the 1-D model [measured]:** solving the bare horn once per source (unit injection, other sources
rigid), then coupling the lumped networks with the formula above, reproduces the direct solve to 5.6e-16. That holds
for one and two entry groups, 100 Hz-8 kHz, and the bare-horn Z is reciprocal to the same level
(`calc/meh_zmatrix_check.py` -> `calc/zmatrix_check.md`). The decomposition is exact for lumped entries; what L1
approximates is only "uniform velocity across each port patch".

### 10.2 Fidelity ladder

| Level | What is modelled | Cost per design | Use |
|---|---|---|---|
| L0 | analytic + 1-D sketch (this folder), Hornresp-MEH-wizard class | ms | screen ranges, sanity-check BEM, inner-loop warm start |
| L1 | exterior BEM: horn + box + flush port apertures (+ CD duct, + PR/vent patch) as driven patches; chambers, necks, drivers lumped; Z matrix | one screen solve (minutes); extra channels nearly free | the GA's outer loop |
| L2 | exterior BEM with front chambers and port necks meshed, cone faces as driven surfaces inside the cavities | 1.5-3x L1 dofs, thin-gap care | finalists: neck shape, chamber modes, the real notch |
| L3 | Boundary Lab coupled FEM-BEM (SAWMOD template): electrodynamic transducers, voltage ports, FEM front chambers + throat, channel synthesis; symmetry xy allowed | hours | refinement + independent cross-check before printing |
| L4 | prototype measurement | days | truth (s11) |

### 10.3 Parameter vector

Geometry knobs need a BEM solve (outer CMA-ES); network knobs do not (inner optimiser per stored solve).

| Group | Knob | Range (first guess) | Level | Note / source |
|---|---|---|---|---|
| horn | `cov_h_deg`, `cov_v_deg` (wall half-angles) | 35-55, 25-45 | geometry | straight-walled conical (Synergy) |
| horn | `depth_mm` (apex to mouth) | 150-350 | geometry | size vs pattern floor (s5) |
| horn | `throat_exit_mm`, `throat_len_mm`, `throat_blend` | 25.4 / 36; 0-20; 0-1 | geometry | round coupling plane (owner rule) |
| CD | `cd_depth_mm` (diaphragm to exit) | from the CD drawing | geometry (duct) or network | first-order for the mid notch (s6.3) |
| horn | `mouth_roll_mm`, `mouth_corner_mm` | 0-40, 0-30 | geometry | diffraction at a small mouth |
| box | `box_margin_mm`, `baffle_edge_mm` | 10-40, 0-30 | geometry | freestanding vs enclosure mounting (WP12) |
| entry (per group) | `wall` | {side, top/bottom, corner} | geometry, categorical | corners/"knuckles" reduce CD interaction [snippet] |
| entry | `count` | {2, 4} | geometry, categorical | |
| entry | `path_mm` (port centroid to the CD diaphragm, along the axis) | 0.6-1.3 x c / 4 f_x | geometry | s6, claim 1 (Unity) |
| entry | `port_shape`, `port_area_frac` (of Sd), `port_aspect` | {round, slot, multi-hole}; 0.07-0.25; 1-6 | geometry | sum vs horn area at entry (Unity); claim-5 check |
| entry | `port_taper` | {straight, frustum, stepped} | geometry (L2) / network (L1) | US 8,284,976 |
| entry | `port_offset` (across the wall) | -0.3..0.3 of wall width | geometry | non-zero breaks the mirror pairing |
| woofer (T3) | `w_path_mm`, `w_open_area_cm2` | <= c / 4 f_w; 80-400 | geometry | |
| PR / vent (T2b, T3) | patch position, area | box faces | geometry | own channel |
| network | driver per group | shortlist s7.3 (`examples/drivers/`) | inner | categorical; enumerate |
| network | `v_front_cm3`, `l_neck_mm` | 10-200, wall thickness | inner (L1) / geometry (L2) | |
| network | `v_rear_l`; vent tuning or PR mass | 0.3-6 / box | inner | sealed per band (patent) |
| network | crossover type / fc per channel | LR2/LR4/LR6/BW, non-integer allowed; ranges s6 | inner | Danley: overlapping, non-constant slope |
| network | gain, delay, polarity, PEQ (2-4 biquads) per channel | +-12 dB, -1..+2 ms, +-1 | inner | DSP is free; geometry is not |
| network | drive limits (V_max, P_AES per driver, Xmax) | datasheet | inner | BL projects max SPL the same way (Xmax, Pmax) |

### 10.4 Objective terms

Existing v4 terms keep their meaning but are computed on the **summed system** response after the network, not on
one source: coverage (beamwidth vs target), ripple, DI and DI slope, flatness of normalised polars, loading.

New candidate terms (each encodes a new priority, so each needs owner approval before it enters J):

| Term | Measures | Why |
|---|---|---|
| `xo_lobing` | H and V polar consistency through each crossover octave (beamwidth jump, off-axis notch depth) | entries at different positions lobe off axis |
| `notch` | depth and width of narrow dips in the listening window that EQ cannot fix (CD notch, mid reflection notch) | the MEH signature defects |
| `max_spl` | excursion-, thermal- and port-velocity-limited SPL per band, at a drive budget | small boxes run out of excursion first; JW / Danley rate max SPL this way |
| `lf_ext` | frequency where max SPL falls below a target (e.g. 106 or 110 dB) | the "EDM bass" knob, honest in dB |
| `coherence` | group-delay spread across the band and across angles | the claimed point-source benefit (Danley: "much less group delay") |
| `size` | box volume and outer W x H x D vs the brief envelope | "really small" as a hard constraint |

### 10.5 Software changes a later plan will need (seeds, not tasks)

- **Fork (opt-in, default byte-identical):** several `velocity_sources` tags, one unit-drive channel each, no synthesis;
  per-channel per-tag mean pressure -> Z matrix in the result; capability flags updated. Tests: superposition,
  reciprocity, symmetry factor.
- **Mesh:** the STEP route accepts `driver` plus `entry_<group>` labels, each to its own tag; decide the tag namespace
  (reuse mesher 10/11 or new ids); `mesh_meta.json` echoes per-tag area and centroid.
- **CAD tool:** `tools/cad/meh.py` (build123d, like `multicell.py` / `plughorn.py`): conical horn + box + flush port
  apertures + CD duct (L1); later chambers, tapered necks (L2).
- **Network module:** generalise `driver/compression.py` into a multi-port network:
  - cone + rear box (+ PR / vent) + front chamber + neck Norton entries;
  - a CD source with its duct;
  - Z coupling and DSP;
  - the energy-balance test pattern already used there;
  - the Mmd-from-Mms helper (s7.3).
- **Search:** nested optimisation, outer CMA-ES on geometry and an inner fast optimiser on the network. Dataset records
  must keep per-channel pressures and Z, so a new driver or new DSP re-scores old solves for free.
- **Brief:** drivers per group, crossover constraints, drive budget, size envelope, sub crossover.
- **Boundary Lab exporter** for MEH projects built on the SAWMOD template (FEM throat + front chambers, interfaces,
  electrodynamic transducers, channels from our inner optimiser); headless solve; compare per-channel results.

### 10.6 Mesh budget (rough)

A 90 x 60 conical horn 220 mm deep in a freestanding box has ~0.6 m^2 of surface. A quarter model at lambda/6 for
10 kHz (5.7 mm elements) is ~11k triangles, ~5-6k dofs [inferred], under the 12k cap with room for port refinement.
Extra channels are nearly free per frequency (s3). L2 chambers add small cavities and thin gaps (near-correction is
CPU-only today). For L3, BL's planning table puts 10k elements at ~4-6 GB on the 8 GB card.

### 10.7 Hand-off to Boundary Lab

**What we pass:**
- the finalist's mesh in metres (`scale_to_m = 1.0`), BEM exterior with interface openings;
- FEM regions for the throat and front chambers (one connected front FEM volume, per the MEH Studio audit);
- one electrodynamic transducer per driver with datasheet T/S (Mmd, derived if needed);
- lumped sealed rear chambers;
- voltage ports, and channel DSP from our inner optimiser.

**What BL adds:** coupled interior FEM for chambers and necks, port air speed, its own BEAT build as an independent
solver, GUI inspection.

**Rules from our BL research still apply:** phasor conjugation, explicit frequencies via the overlay, and its Julia
host is not shut down by its CLI (GPU hygiene rules 1, 2, 6). PRs are not modelled in BL.

## 11. Measurement plan (when a prototype exists)

1. **Driver T/S:** for every driver (impedance sweep, added mass); Mmd from Mms minus the front air load (s7.3).
2. **Per-channel acoustic transfer:** gated far-field or ground-plane on axis (JW: outdoors, ground plane, 20-cycle
   FDW), polars every 10 deg H and V. Measure **one channel at a time with the others connected but silent** (that is
   the model's Z coupling), then summed.
3. **CD notch check:** CD alone with mid ports open (cones in place) vs ports taped shut. The difference is the
   side-branch effect L1 predicts.
4. **Mid notch:** sweep each mid group alone; compare its first null with s6.3. The patent trick (drivers out of phase,
   notch near 2x the crossover) is a quick field check.
5. **Electrical impedance** per channel in the box (shows port and chamber resonances).
6. **Excursion and max SPL:** excursion at the band bottom; max SPL / compression sweep (10 % THD as JW rates it);
   port air noise.
7. **Group delay** on axis; sum vs prediction through each crossover.

## 12. Plan seeds (not a plan)

| Seed | Content | Gate |
|---|---|---|
| MEH-0 | owner decisions (s13) | none |
| MEH-1 | promote the 1-D sketch to a validated calculator (CD duct, PR/vent, port velocity); cross-check against a published Hornresp MEH case (Waslo's Synergy Calc inputs) and MEH Studio's 610.3 Hz LC case | within 1 dB below the first cross-mode |
| MEH-2 | driver library: s7.3 shortlist into `examples/drivers/` with datasheet URLs; CD depths from drawings; CD T/S by measurement (none published) | every number sourced |
| MEH-3 | fork change: multi-tag, per-channel outputs, Z matrix | superposition + reciprocity + symmetry tests on CPU and CUDA |
| MEH-4 | CAD tool + multi-label STEP route (L1 geometry) | shape checks + quarter-symmetry pairing |
| MEH-5 | network module + inner optimiser | energy balance; 1-D vs network-on-BEM agreement |
| MEH-6 | objective terms + brief (owner approval per term) | T0-style gate on known cases |
| MEH-7 | first GPU screen (owner go): T1 and T2 seeds; T2 compared with the DH350 MEH's published band and level | L0 vs L1 agree in trend |
| MEH-8 | Boundary Lab export (SAWMOD template) + cross-check of one finalist | per-channel results within agreed tolerance |
| MEH-9 | print + measure (s11) | model vs measurement report |

## 13. Open questions for the owner

1. **Bass:** separate sub (2-way mini top), a one-box T2b (~60 Hz at ~106 dB, DH350 MEH class), or a bigger 3-way box?
   What f3 and what SPL at 50 Hz?
2. **Size:** a number for "really small" (outer W x H x D or litres) and weight. For scale: DH350 MEH is 470 x 260 x
   200 mm.
3. **Use:** DJ booth monitor, small club tops, mobile rig, home? Sets coverage (90x60 vs 75x60 vs 90x90) and level.
4. **Mids:** 4 x 4-inch (higher crossover, Danley's core) or 2 x 6.5-inch (more output down low; DH350 MEH)? The search
   can carry both; a brief needs one target at a time.
5. **Processing:** active DSP per channel assumed (it is what makes the inner optimiser free). OK?
6. **New J terms (s10.4):** which ones to add, and their weights.
7. **Commercial intent:** only if you might sell. Google Patents lists the Synergy patent (US 8,284,976) as active to
   about 2029; Unity (US 6,411,718) has expired. This is not legal advice and is irrelevant for DIY.

## 14. Owner decisions 2026-10-30 and the hand-off

Answers to s13: separate bass box (30-120 Hz flat, MEH top from ~120 Hz); the top fits a 16 in (406 mm) square
face, studio-monitor depth (380 mm assumed), corner-hung; home hi-fi / DJ practice / DJ booth, critical listening
first, level "keeps up with a powered 12 in + horn PA"; DSP and FIR on every channel; not for sale.

The orchestrator then fixed the design and wrote the implementation hand-off in `docs/meh/` (contracts + ten work
packages for cheaper agents). New research artefacts behind those decisions:
- `calc/meh_layout.py` -> `calc/layout_out.md`:
  - layout feasibility in the 16 in box: horn ~150 mm long, mouth 330 x 191 at 90x60;
  - the naive knob box is 12-29 % feasible, the reparameterised box with deterministic repair 56-93 %;
  - T2 top/bottom 77 % vs sides 41 %;
  - the 6.5 in front chamber sets the port corner at ~650-950 Hz, so T2 pairs with a 1.4 in CD;
  - seeds T2-A, T2-B, T1.
- `calc/meh_bassbox_sizing.py` -> `calc/bassbox_sizing.md`: 15 in / 18 in long-throw options for 30-120 Hz.

Typologies after the decision: **T2 `meh2_6x2`** (1.4 in CD + 2 x 6.5 in, top/bottom walls, 90x60, XO 650-1100 Hz,
HP 120 Hz) primary; **T1 `meh2_4x4`** (1 in CD + 4 x 4 in, XO 1-1.5 kHz, HP 160 Hz) secondary; T2b and T3 dropped
(bass box is separate); T4 (fluted) stays later.
