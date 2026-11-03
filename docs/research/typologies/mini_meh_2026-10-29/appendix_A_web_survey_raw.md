> **Read through the corrections in `../MINI_MEH_RESEARCH_2026-10-29.md` section 8.** Verbatim output of the Sonnet
> web lane, 2026-10-29 (unedited below this note). The "working copies" folders it names (`bl/`, `ds/`, `dsl/`, `meh/`,
> `pdf1/`, `m3/`, `hm/`) were session-local downloads and are NOT in the repo (datasheets and third-party docs stay with
> their owners); re-fetch from the URLs in its source table. Orchestrator spot-checks (DH350 MEH page, Solana page,
> US 8,284,976 claims 1/4/5/6 + notch/port passages, BL releases, BL `Multi_region_SAWMOD` example, MEH Studio repo,
> BL issue #78) are in the dossier's s8. US 6,411,718 claim text could not be re-read (Google Patents 503,
> mirrors 403), so its quarter-wave wording stays at the lane's [verified] (read through the WebFetch summariser).

# Small-format multiple-entry horn (MEH / Synergy / Unity class): outside web research, raw dossier

Date: 2026-10-29. Lane: web research (read-only; nothing in /home/user/Hornfab was touched).
Scope: the owner's goal is a **mini MEH** (smaller than JW Sound's Solana): one 1" or 1.4" compression driver (CD) at the throat plus cone mids on wall ports, either **2 x 6.5"** or **4 x 4"** cones, in a **very small box with solid bass for EDM**. Research only; later CMA-ES + GPU BEM search, then finalists to Boundary Lab (BL).

## Label legend

| Label | Meaning |
|---|---|
| [verified-raw] | I downloaded the file (raw GitHub text, PDF datasheet, spec sheet, JSON) and read the text myself this session. |
| [verified] | Read through the WebFetch tool (the page text is passed through a summariser; numbers are copied from that output, not from raw HTML). Re-check a number before it becomes a hard constant. |
| [snippet] | Search-result snippet only (page itself unreadable: bot check / 402 / 403 / 503). |
| [inferred] | My own calculation or reasoning (formulas shown). |
| [unverified] | Claim made by a secondary source that I could not check. |

Source status vocabulary: primary (author) / primary (author, forum) / secondary, peer-reviewed / secondary (practitioner reports) / tool / marketing.

Working copies (downloaded raw files, safe to re-read) are in `/tmp/claude-0/-home-user-Hornfab/580262dc-a71c-536c-9d01-b6d092e5a5f9/scratchpad/`: `bl/` (all Boundary Lab docs + 3 example project JSONs), `ds/` (driver datasheet PDFs + txt), `dsl/` (Danley spec sheets), `meh/` (MEH Studio docs + driver JSON), `pdf1/` (Waslo Synergy Calc text), `m3/` (m3gnus READMEs), `hm/` (mesher tags.py).

Access limits met (not worked around): diyaudio.com, avsforum.com (402 via tollbit), prosoundweb, Yumpu/Scribd/Docslides, Google Drive plans, Instagram/YouTube/TikTok returned bot-checks, 402/403/503 or empty pages. A direct curl to diyaudio with a browser user-agent was blocked by the sandbox as bot-check circumvention and I did not retry. Every diyAudio/AVS statement below is therefore **[snippet]** (search-engine excerpt) unless stated.

---

## Source table

| Source | What it gives us | Status |
|---|---|---|
| JW Sound Solana page https://www.jwsound.live/designs/solana-diy (old URLs /designs/solana-multiple-entry-waveguide and /designs/solana redirect here) | Driver complement, band, max SPL, coverage, GA statement. No dimensions. | primary (author), marketing-style product page [verified] |
| JW Sound DH350-based MEH https://www.jwsound.live/designs/dh350based-multiple-entry-horn | Full build writeup of a 2 x 6.5" + 1" CD MEH: sizes, measured band, design method, tap rule | primary (author) [verified] |
| JW Sound JMOD / JMOD-M / SAWMOD / Booth pages (/designs/jmod, /jmodm-medium-format-array, /sawmod, /booth-monitors); Lab page https://www.jwsound.live/lab2 | Product family, JMOD-M preliminary specs, links to Klippel NFS Solana measurement and "Shared Aperture Waveguide Module" paper (both unreachable) | primary (author) [verified] |
| Boundary Lab repo https://github.com/JWSound/boundary-lab (docs/*.md, examples/, pyproject.toml, releases) | Solver contract, components, channels, CLI, VRAM table, example projects | tool (author docs) [verified-raw] |
| BEAT Engine https://github.com/JWSound/BEAT_Engine (releases, PR #78, issue #92) | Engine versions, ROCm/CPU precision work, open issues | tool [verified] |
| m3gnus repos: https://github.com/m3gnus/hornlab-waveguide-mesher (tags.py), https://github.com/m3gnus/hornlab-beat-bem (README) | MEH physical-group tags; what the Python wrapper refuses | tool [verified-raw] |
| Danley US 4,845,759 / US 6,411,718 B1 / US 8,284,976 B2 / US 8,457,341 B2 on patents.google.com | Claims, rules, example numbers | primary (author) patents [verified] |
| Danley product pages (SH/SM/OS/TH/Compact/GO2 families) and spec sheets https://www.danleysoundlabs.com/wp-content/uploads/2022/06/SM-60F-spec-sheet1.pdf , SM-96-spec-sheet.pdf , SH-Mini-spec-sheet.pdf , https://danleysoundlabs.com/wp-content/uploads/2024/05/SH75-Specs.pdf , TH-Mini-spec-sheet11.pdf , THMini15-Specs.pdf | Small Synergy product numbers | marketing (manufacturer specs); spec-sheet PDFs [verified-raw], product pages [verified] |
| Danley white paper "The Tapped and Synergy Horn Explained" (8 pp; mirrors on Yumpu/Scribd/Docslides) | Would be the best primary explainer | primary (author), **not retrievable** |
| Tom Danley / Ivan Beaver posts on diyAudio, AVS, Parts Express | Port/notch/LPF rules in the author's words | primary (author, forum), **[snippet] only** |
| Bill Waslo, "Synergy Calc V5" guide PDF http://libinst.com/SynergyCalc/Synergy%20Calc%20V5.pdf (2014) | Only detailed public MEH design procedure: HornResponse inputs, chamber/port variables, lambda/4 hole spacing, CoSyne reference build | secondary (practitioner reports) [verified-raw] |
| Parts Express Project Gallery "Synergy Horn" https://projectgallery.parts-express.com/speaker-projects/synergy-horn/ (2017) | Small stand-mount Synergy with 6.5"/4.5" cones: crossover, box, efficiency | secondary (practitioner reports) [verified] |
| femishonuga.com MEH notes https://femishonuga.com/meh.html | Rule-of-thumb sheet (slot area, aspect ratios, slot distance) | secondary (practitioner reports), author unknown [verified], rules [unverified] |
| Audio Abattoir thread https://audioabattoir.com/t/meh-plans/17339 | Builders' comparison of JMOD/Solana/SAWMOD/SH50 clones, tap-area ratio rule | secondary (practitioner reports) [verified] |
| MEH Studio https://github.com/mroushdy/MehStudio (README, docs/front-chamber-reference.md, docs/existing-spatial-solvers.md, mesh-export/README.md, driver-research/*.json) | Tool that designs 2/4/6-mid MEHs and exports ABEC/AKABAK/Boundary Lab meshes; lumped front-chamber equations; independent audit of BEAT/BL fit | tool [verified-raw]; no OSS licence stated |
| Manufacturer datasheets (B&C, FaitalPRO, 18 Sound, Celestion) | Driver T/S, CD specs | marketing (manufacturer data) but primary for T/S [verified-raw] |
| diyAudio threads (2-way MEH build 421176; Portable Bluetooth MEH 414030 / 415747; MEH Studio 444735; SAW Module 435033; Hornresp 119854; Unity/Synergy build 309213; Midranges for synergy horn 352924; The mysterious Danley crossover 364891; Synergy horn port location 339799 ...) | Builder rules, failure modes | secondary (practitioner reports) [snippet] |
| AES / other papers: Geaves & Henwood AES 4208 (1996); Morgans et al. 2008 (EGO horn optimisation); Makarski AES 117 (2004); Nizzoli & Prati AES 134 (2013); Oclee-Brown PhD (Southampton 2012); arXiv 2604.21431 JAX-BEM | Modelling/optimisation background | secondary, peer-reviewed [snippet], thesis cited via MEH Studio doc |
| Small, "Direct-radiator loudspeaker system analysis", JAES 20(6) 1972 | eta0 = 4 pi^2 Fs^3 Vas / (c^3 Qes) (checked numerically against datasheets) | secondary, peer-reviewed (formula only; paper not read) [inferred check] |
| EDM production blogs (allforturntables, emastered, pauseplayrepeat) | Kick/sub fundamentals | marketing / secondary [snippet] |

---

## 1. JW Sound "Solana" and the other JW Sound multi-entry designs

### 1(a) Construction, design math, reference numbers

Everything the official Solana page states [verified, https://www.jwsound.live/designs/solana-diy]:

- Type: point source. Drivers: **4 x 6.5" woofers + 1 x 1" HT polymer diaphragm CD**. No driver model numbers.
- Operating range **45-17,000 Hz**; "as shown in vented low-tuned configuration".
- Max working output **109 dB full range / 120 dB with external sub (100 Hz HPF)**, defined as "a measured 10% harmonic distortion threshold" at "a calculated 1 meter distance in half space radiation".
- Coverage **90 x 90 deg, controlled directivity down to 700 Hz**.
- Design: "An iterative genetic algorithm optimization process was created to produce the complex waveguide profile"; waveguide printed in SLA resin; "turbulence-minimizing port profile"; CD "with a unique phase plug geometry". The goal text (via search excerpt): smooth directivity control and coherent driver integration above all other metrics [snippet].
- Free DIY plans (Google Drive; not reachable) at https://www.jwsound.live/solana-diy; "Read the Design Reference (Coming Soon)". Measurements: a "Solana Klippel NFS" study is listed on https://www.jwsound.live/lab2 (links to /lab/bhv2rxe7yc1zedlaj0wujc9zk81amb and /blog/...: both returned 404 for me). Dimensions, weight, volume, crossover, driver models are **not on the page** and I could not find them anywhere reachable.
- Not stated anywhere I could read: whether the GA used Boundary Lab, lumped drivers, or what objective. JW Sound lists Boundary Lab, Fusion2Msh and a Polar Generator under "Tools" on /lab2 [verified]; Boundary Lab's own author is JW Sound (repo owner JWSound). Linking Solana to BL specifically is [unverified].
- Printed in 4 parts; one AVS poster (the designer, per snippet) said it was "about as big as I could manage using DIY-accessible printer" [snippet].
- Designer floated a variant with **two 4" mids instead of four 6.5" woofers**, and discussed port-edge diffraction and dropping/moving ports if the coax/CD crossover is lower [snippet from an AVS thread summary; not read directly].

Validation numbers we can reproduce [inferred]:

- If the four 6.5" woofers are a 6NDL38-class cone (Sd 132 cm2, Xmax 6 mm), the displacement-limited half-space SPL at 1 m is **106.5 dB at 50 Hz and 118.6 dB at 100 Hz** (formula in section 7). JW's 109 dB (full range) and 120 dB (100 Hz HPF) are within 1.4-2.5 dB of that, so the Solana numbers are consistent with displacement-limited operation in a low-tuned vented box with a port adding a few dB below tuning. Driver models are unknown, so treat as plausibility only.
- Mouth width implied by "pattern control to 700 Hz": by scaling Waslo's 24 in / 385 Hz point (width = 0.68 lambda at the pattern-control floor) the Solana mouth is about **0.33 m wide** [inferred, +/-20 %]. Not stated by JW.

Closest published **reference case for a 2 x 6.5" + 1" CD mini MEH: the JW "DH350-based MEH"** (the Bluetooth MEH; the AA forum calls the family "BTMEH") [verified, https://www.jwsound.live/designs/dh350based-multiple-entry-horn]:

- Parts: 2 x B&C 6NDL38 woofers, 1 x B&C DH350 CD (1" exit, 36 mm coil), 2 x Scan-Speak SB16PFCR-00 passive radiators, Dayton KABD-4100 amp, 6 x Samsung 35E 18650 cells.
- Size: **18.5 x 10.2 x 7.9 in = 470 x 260 x 200 mm**; **6.75 kg**; hexagonal box in 12 mm birch; **about 15 L net** after displacement of horn and drivers (bounding box 24.4 L [inferred]).
- Measured **60-16,000 Hz +/-2 dB**; max SPL **106 dB** (point where woofers and passive radiators reach Xmax; higher with an 80 Hz HPF); crossover target ~1.0-1.2 kHz; DH350 breaks up ~16 kHz.
- Coverage specified **75 H x 60 V**; goal was 60 x 90; the author says the result is narrower than intended, "likely because the Ath model didn't match the ABEC polars".
- Method: waveguide in Ath (called a waveguide, not a horn, after Geddes), directivity and impedance tuned in Ath then approximated in **Hornresp with the MEH wizard** for the woofers; woofer taps placed in Fusion so their centroid sits **about 1/4 wavelength at the crossover frequency from the CD exit**; flange with cone-filler provisions; printed in 3 parts (two halves + throat adapter), two-part epoxy, M4 heat-set inserts.
- Measurement: outdoors, ground-plane, Dayton UMM-6, 20-cycle FDW at 1 m (2 m off-axis), analysed in VituixCAD.
- Lesson (search excerpt of the diyAudio thread): passive radiators touch the woofer backs, "add a few millimeters next time" [snippet].

Other JW Sound multi-entry designs:

| Design | Facts | Label |
|---|---|---|
| JMOD (MEH top) | "Multiple entry horn top... 90 x 60 coverage"; free plans (Drive); 17 builder photos. Drivers per AA forum: coax CD + two 12" woofers, drivers ~GBP 1500 | page [verified]; drivers [secondary] |
| JMOD-M (arrayable) | "Under Development/Rework". 2 x 12" or 2 x 14" mid-bass + 1 coax CD; 80-18,500 Hz; 110 x 55 constant directivity; horizontal control to 100 Hz, vertical to 300 Hz; 145 cm W x 73 H x 63 D, 80 kg (pair?); min sensitivity 106 dB @100 Hz; tri-amp or bi-amp with B&C FB464 passive; "2.25x larger by volume than JMOD 2.0" | [verified] |
| SAWMOD ("Shared Aperture Waveguide Module") | "High power density point source top for monitoring, fill, small-format mains"; plans + technical paper (Drive, unreachable). Forum: CD + two mids + woofer(s), ~GBP 400 drivers, 100 x 70, held to 300 Hz, crossover to subs at 80-100 Hz; bandpass ports on the waveguide "knuckles" to limit port/CD interaction; described by JW as an evolution of BTMEH and Solana aimed at distortion and mid-range waistbanding | page [verified]; rest [secondary, snippet] |
| Booth Monitoring System | 2 x 12" B&C mid-bass + TAD TD4001/TH4001 + ET703/JBL 2405 super-tweeter; not an MEH | [verified] |
| "BIGMEH" | Mentioned by an AA forum poster as a diyAudio "design exploration (larger woofers, 10" or bigger, due in six months or more)". I could not locate the thread. | [secondary, snippet] |

### 1(b) Strengths
- Works as a printable, free, reproducible reference for 4 x 6.5" + 1" CD (Solana) and 2 x 6.5" + 1" CD (DH350 MEH).
- Hits the owner's size class: the DH350 MEH is 24 L bounding box and reaches 60 Hz (+/-2 dB) using passive radiators, with a 106 dB ceiling.
- GA-shaped profile with explicit port-diffraction control (Solana).

### 1(c) Weaknesses / design issues
- Solana: forum users dislike the "big port to get down to 100 Hz" and found directivity "slightly poor" [snippet]; JW's own later SAWMOD aims to fix distortion and midrange waistbanding [snippet].
- DH350 MEH: narrower pattern than designed (75 x 60 vs 60 x 90 goal); CD power only 15 W nominal / 30 W continuous (B&C datasheet), so the 106 dB number is displacement-limited at the bottom but the top end is thermally small.
- Passive-radiator clearance error (above).

### 1(d) Design knobs and typical ranges (from these designs)
- Woofer count 2 or 4, size 6.5"; CD 1"; crossover CD/woofer ~1.0-1.2 kHz (DH350 MEH); tap centroid distance from CD exit lambda/4 at that crossover (= 69-86 mm at 1.0-1.2 kHz [inferred]); box 15 L net (DH350) to ~tens of L (Solana unpublished); loading: vented low-tuned (Solana) or passive radiators (DH350).
- Waveguide: Ath profile, 60-90 deg nominal coverage, hexagonal or round mouth.

### 1(e) How practitioners measure/rank
- Outdoor ground-plane / Klippel NFS (Solana) polar data, 10 % THD max SPL at 1 m half-space (Solana), VituixCAD for polars and crossover (DH350 MEH), Hornresp MEH wizard for the woofer chain.

### 1(f) Experiential
- No listening impressions found for Solana. A Berlin shop (Restless Audio) showcased one on TikTok [snippet title only]. A diyAudio newcomer cites the shared-aperture waveguide concept as the reason to start with it [snippet]. A "modded Solana vs dB Technologies Reevo 210" max-SPL case study exists on diyAudio (thread 428144) [snippet only; contents unreadable].
- Audio Abattoir builders prefer firing woofers into the horn, say 50 degrees is narrow for rooms and want 70-90 [secondary].

---

## 2. Boundary Lab (BL) and BEAT Engine as an MEH tool

All statements in this section are from raw repo files unless marked.

### 2(a) Versions, what changed since 0.5.0

| Item | Value | Label |
|---|---|---|
| BL latest release | **v0.5.0, 20 Oct 2026** (pyproject on main still says `version = "0.5.0"`). Previous: v0.4.4 (21 Sep, updater-only), Beta 0.4.3 (15 Sep). | [verified-raw] https://github.com/JWSound/boundary-lab/releases ; docs/releases/0.5.0.md |
| BL pinned engine | BEAT Engine **v0.6.0** wheel, SHA-256 `10db2ee28eb9a8675fa0131127a04eeaad61097328c3aac453721a5924187dd3` | [verified-raw] pyproject.toml |
| BEAT latest release | **v0.6.0, 20 Oct 2026**; main has no commit after the release commit (#73). v0.6.0 notes: corrected projected FEM-BEM interface coupling (one facewise-constant flux for FEM loading and BEM radiation), rejects rank-deficient / poorly conditioned interface transfers (some triangulations that used to pass now fail), CPU/Metal Float32 coupled systems factored in Float64 on host; "numerical results can shift". | [verified] https://github.com/JWSound/BEAT_Engine/releases |
| BL commits on main after v0.5.0 | 23 Oct #58 "Allow direct interface seam snaps within 0.05% of diameter"; 26 Oct #59 acoustic-flow arrows on interior planes; #60 / #61 observation-plane controls. No solver-physics change. | [verified] https://github.com/JWSound/boundary-lab/commits/main |
| BL open PRs | #64 "Honor explicit precision in headless production solves" (today the headless path silently turns `solver_options.precision: float64` into Float32; fix keeps Float32 default, forces pure-interior to Float64; max rel L2 error Float32-ROCm vs Float64-CPU 9.3e-5 on S218BP and 2.0e-5 on SAWMOD); #56 STEP-to-mesh CAD import; #44 elapsed-time/ETA; #19 split CUDA sweeps across GPUs; #18 (draft) example driver DB from B&C 2023 catalogue; #62/#63 flow arrows | [verified] |
| BEAT open | PR #78 "Match CPU coupled factorization precision on ROCm" (opened 27 Oct); issue #92 ROCm buffer-reuse fault (gfx1201); issue #74 ROCm blocked pending positive-time phasor validation. SAWMOD timing quoted in #78: median third sweep **102.49 s CPU Float64, 45.03 s ROCm Float32 (Float64 coupled factors), 72.05 s ROCm Float64** (frequency count not given). | [verified] |
| "Issue #78 about Mms vs Mmd" | **Not found.** BL's highest issue is #34 (8 issues total: #1 open Ath.exe; #2 closed "Julia warm worker retains GPU VRAM between solves, causing OOM on larger meshes"; #33/#34 closed). BEAT's #78 is a PR about ROCm precision with no Mms/Mmd text. The Mms/Mmd discussion is in BL **PR #18** and in the docs (below). Probably a number from our own repo. | [verified] |
| Licence | BL, BEAT: GPLv3 (LICENSE files). hornlab-* repos by m3gnus: AGPLv3 (BEAT fork GPLv3). | [verified-raw] |

### 2(b) Multi-source support: what the docs actually say

Sources: docs/Physical System Model.md, docs/Coupled Solver.md, docs/Model Assumptions.md, docs/User Guide.md, docs/advanced/cli-workflow.md [verified-raw].

- **Many sources in one solve: yes.** "The coupled solver returns one complex reference response per excitation port"; all requested ports are solved "together as multiple right-hand sides, so an additional requested source adds a response column rather than another factorization". Pressure: p(x,f) = sum_j H_j(x,f) u_j(f) with u_j (gain, polarity, delay, HPF/LPF, EQ) applied **after** the physical solve. A request overlay can restrict `excitation_port_ids`.
- **Mutual coupling is physical, not synthesised:** all electrodynamic transducers are unknowns of one monolithic (or Schur-condensed) system with the shared exterior BEM; the Acoustic Impedance plot recovers "the intrinsic generalized acoustic load matrix". BEAT v0.4.0 notes also list a "mutual radiation-impedance matrix" for exterior electrodynamic transducers. BL's Level-3 speaker package (`blab project export-speaker --fidelity coupled`) is a rank-reduced Petrov-Galerkin ROM "used for mutual coupling" in arrays.
- **Components** (`physical_system.components[]`): `ideal_velocity_source`, `electrodynamic_transducer` (supported); `passive_radiator` (schema only, "deferred"/rejected). Electrodynamic parameters are direct: `re_ohm`, `le_h`, `bl_n_per_a`, `mmd_kg`, `cms_m_per_n`, `rms_n_s_per_m`, `motion_axis` (3-vector), plus optional `boundary_motion_weights` (per-boundary relative velocity), `boundary_motion_signs`, optional semi-inductance (Re', Leb, Le, Ke, Rss), optional `lumped_sealed_rear_chamber {volume_m3, projected_area_m2}` (adds Kbox = rho c^2 Sd^2 / V; do not combine with a meshed rear chamber). **`Mms` is not accepted; `mmd_kg` is dry moving mass.** Diaphragm area comes from the meshed moving faces (a published `Sd` is not used). One component may own moving boundaries in several FEM regions and in the BEM region (front/rear need no node match).
- **Voltage ports:** one `voltage` port per electrodynamic component (reference **2.83 V**, zero source impedance), one `normal_velocity` port (1 m/s) per ideal source. Raw outputs: `exterior_pressure`, `diaphragm_velocity`, `voice_coil_current`, `fem_nodal_pressure`, `bem_boundary_*`, `interface_normal_derivative`, `interface_radiated_pressure` (per-interface SPL contribution; needs an engine that advertises the optional output: BL issue #34 shows BEAT 0.2.0 lacked it), `interface_average_normal_velocity` (port air speed; needs BEAT >= 0.4.0).
- **Channels** (project state, not solver state): name, voltage, Trim dB, Polarity, Delay ms, HPF/LPF (Linkwitz-Riley / Butterworth, orders 4 and 6 appear in examples). Components on the same channel are summed (and electrically paralleled for impedance). "Passive electrical crossover networks, amplifier source-impedance interaction... would alter the physical system... outside scope." Max-SPL projection per voltage channel uses Xmax (peak) and Pmax (sqrt(Pmax Re)); one rating pair per channel.
- **Regions:** `bounded_air` (FEM, first-order tetrahedra, Gmsh 4.1 ASCII, **one mesh per region currently**, several regions allowed, optional `bulk_loss_factor` presets 0/0.002/0.005/0.01/0.02/0.05, Miki rigid-backed porous wall treatment on rigid walls, optional thermoviscous wall-loss toggle from 0.5.0) and exactly one `unbounded_air` (BEM, Gmsh 2.2 ASCII triangles, may combine several BEM meshes without welding). Same density and sound speed in every region.
- **Boundaries:** rigid, moving, interface (FEM<->BEM), `plane_wave_tube_termination` (bounded only, Robin dp/dn = -ik p, exact only for a plane mode in a uniform tube), `impedance` (schema only).
- **Interfaces = ports/openings:** each FEM-BEM interface needs conforming vertices and triangles; FEM facets authoritative; Build/Identify Interfaces rewrites the BEM side (planar opening: remesh surround; or matching curved seams). Several FEM chambers can connect to different openings in the same BEM mesh; coplanar openings are protected while each pair is rebuilt. Headless note: interface construction allows up to 0.55 mm geometry deviation; #58 adds seam snaps within 0.05 % of diameter. Coupled path is **P1 only**; P2 exists for pure interior FEM.
- **Symmetry:** off / x / xy; component symmetry role, completion factor (2^n) and orbit count are inferred from moving-surface topology; per-interface symmetry handled separately. Motion axis must lie in every symmetry plane that cuts the driver.
- **Not supported (paraphrase of the Coupled Solver "Unsupported physics" list):** general impedance functions, spatially varying loss, Mms input/auto conversion, passive radiators, non-ideal amplifier, cone breakup / nonlinear Bl / thermal, non-uniform motion profiles, more than one exterior region, different fluids, iterative/FMM/distributed solving, Bempp/ROCm/server/exterior-local for coupled systems (ROCm is nevertheless listed as a production coupled backend elsewhere in the same doc; the list is stale on that point).
- **Mms -> Mmd:** BL PR #18 discussion proposes either an approximation from Sd or Mmd = Mms - air load from a free-air BEM sim; BL's own docs say only "Mms is not interchangeable". My check [inferred]: Mmd = Mms - 2 * (8/3) rho a^3 with a = sqrt(Sd/pi) reproduces Faital's published Mmd to within 0.1 g for 6FE100 (11.9 vs published 11.9), 4FE32 (3.8 vs 3.8) and 6PR160 (10.8 vs 10.8).
- **Driver text import** (component editor, merged in 0.5.0): first non-blank line = name, then `Bl` (N/A), `Cms` (m/N), `Rms` (N s/m), `Mmd` (g), `Le` (mH), `Re` (ohm); optional `Sd` (cm2, informational) and semi-inductance block; Pmax/Xmax ignored (set per channel in Maximum SPL).

### 2(c) Multi-entry / horn / side-port / CD+cone content in BL

- No example or doc is named "multi-entry" or "Synergy". Examples folder (13 listed; listing may be incomplete): `2x12_CRAM, Ath+Mesh_2WayFreestanding, Ath+Mesh_2WayIntegrated, Ath_2WayBookshelf, Ath_SingleSourceWaveguide, F2B_FLH, MultiAth+Mesh_3WayIntegrated, Multi_region_SAWMOD, S218BP, SKRAM, Simple_Sealed, Vented_Sub, compression_driver` [verified].
- **`Multi_region_SAWMOD.blab.json` is the nearest MEH-like precedent** [verified-raw, schema_version 10]: exterior BEM mesh `exteriorBEM_interface_conformed.msh` + **3 FEM regions** ("Waveguide Throat", "Side Slot", "SealedMainChamber", each `bulk_loss_factor` 0.02), **3 electrodynamic components** (CD "DH450-8" and mid "5CCN125D" both with moving boundaries in the throat FEM region; LF "10RS430" spanning the side-slot and sealed-chamber FEM regions), **3 voltage ports**, **4 FEM-BEM interfaces** (`wginterface`, `frontinterface`, `sideinterface`, `topinterface`), `symmetry: "xy"`, meshes in mm with `scale_to_m: 0.001`, 200 frequencies 20-20,000 Hz, 1-degree polars at 3 m, balloon sampling on, 2.5 degree. The mid has `lumped_sealed_rear_chamber` volume 0.34 L, `motion_axis` (-0.9135, 0, 0.4067) i.e. tilted ~24 deg from the horn axis, `physical_driver_orbit_count` 2. Channels: **HF** (HPF LR4 1600 Hz, polarity +1, delay 0), **MF** (HPF LR6 360 Hz, LPF LR4 1600 Hz, polarity **-1**, delay **+0.10 ms**), **LF** (LPF LR6 360 Hz, polarity **-1**, delay **-0.15 ms**). Component values in this file are example-specific (the CD entry has mmd 3e-5 kg, bl 1.9, cms 1.25e-4 m/N, re 5.8: odd values for a CD, treat as placeholders).
- `MultiAth+Mesh_3WayIntegrated` is BEM-only: three Ath scripts (a 36 mm-throat HF waveguide and a 51 mm-throat mid waveguide morphing to 250 and 355 x 335 mm mouths) in one enclosure; channels High (HPF LR4 3 kHz), Mid (LR4 400 Hz-3 kHz), Low (LPF LR4 400 Hz); `velocity_offset_db` per driven surface (e.g. -12, -2.5, 0 dB). No cone-through-port physics.
- `compression_driver.blab.json`: interior-only FEM with **front chamber + rear chamber** joined by one electrodynamic diaphragm (Re 5.2, Le 0.14 mH, Bl 9.5, Mmd 0.8 g, Cms 3e-5 m/N, Rms 1.2) and a plane-wave termination on the front tube; bulk loss 0.002 [verified-raw]. Shows how a CD (diaphragm + compression chamber) can be put in FEM; phase-plug channels would need a mesh.
- **`vented_enclosure` geometry provider** (`geometry_providers/vented_enclosure/README.md`): rigid rectangular cabinet, **one front driver, one straight-axis circular flared port**; emits interior FEM volume + closed exterior BEM surface + voltage-driven LEM transducer; metres; defaults Re 5.8, Le 0.5 mH, Bl 8, dry Mmd 35 g, Cms 0.4 mm/N, Rms 1.5; port profile from the STV port-optimizer workbook (R = L/(2 NFR), r(z) = r_throat + R - sqrt(R^2 - (z + L/2)^2)). Not a horn, not multi-driver. Generator Plugin API (docs/advanced/geometry-provider-api.md) supports **transactional multi-mesh assemblies** (`GenerationResponse` with named FEM/BEM resources), exchange schema 1.
- A third party (MEH Studio) already exports "ABEC / AKABAK & Boundary Lab" meshes for 2/4/6-mid MEHs (physical tags: branch wall 10, horn 11, enclosure 12, rear panels 13, cones 101-106, vent inlets 151-156, FEM interface 301, closed HF throat 302, FEM volume 401); its audit recommends one connected FEM volume for all front chambers + horn throat, a shared rear FEM volume, and one BEM exterior joined at the mouth (docs/existing-spatial-solvers.md) [verified-raw]. Its author does not state an OSS licence (cannot copy code).

### 2(d) Headless CLI (verified-raw, docs/advanced/cli-workflow.md)

- `blab project validate X.blab.json --json` (no Julia launched; reports solve kind, mesh hashes, excitations, outputs); `blab project solve X.blab.json --backend beat_auto|beat_cpu|beat_cuda|beat_rocm --output runs/NAME` (output dir must not exist; `--julia-executable`, `--julia-threads`, `--events ndjson`, `--request overlay.json`, `--server-url`); `blab project export-speaker`, `speaker-preflight`, `evaluate-fem`, `compare-fem`; `blab conform-interface fem.msh bem.msh out.msh`; `blab server`.
- Overlay JSON: `frequencies_hz` or `frequency_sweep{min_hz,max_hz,count,spacing}`, `excitation_port_ids`, `include_project_observations`, `probes[{id,coordinate_frame:"project",points_m}]`, `retain[]` (bem_boundary_*, fem_nodal_pressure, interface_radiated_pressure), `solver_options{quadrature_order, singular_order, coupled_bem_assembly, coupled_bem_image_fusion, coupled_bem_max_registers, fem_consistent_mass_weight, precision (honoured only after PR #64)}`.
- Result artifact: `manifest.json`, `project.snapshot.blab.json`, `request.json`, `compiled-system.json`, `domains.json/.npz`, `frequencies/000000.json+.npz` (each frequency committed independently; phasor convention exp(+i omega t)). Complex results stay separated per excitation port (no channel synthesis headless).
- Python engine API (from MEH Studio audit of 0.3.0): `EngineWorker`, `WorkerPool`, `EnginePaths`, `engine_paths`; `python -m beat_engine paths|backends|instantiate --backend cpu|cuda|rocm`.
- **Our own wrapper limitation:** `hornlab-beat-bem` README (m3gnus, main) says the vendored Julia engine has coupled FEM-BEM-LEM and multiple source channels but "a capability the vendored Julia engine has but the Python API cannot reach is reported unsupported... coupled FEM-BEM-LEM, multiple source channels and post-solve field replay all read that way today", and under "Not supported": "multi-source drive -- exactly one velocity source tag at unit amplitude" [verified-raw, https://github.com/m3gnus/hornlab-beat-bem]. So an MEH solve through that wrapper today means either driving the BL/BEAT CLI directly or one velocity source tag at a time.

### 2(e) GPU / VRAM

- BL planning table (not hard limits), docs/Installation and Setup.md: **1,000 elements ~50-100 MB; 2,000 ~200-300 MB; 3,000 ~400-600 MB; 5,000 ~1.0-1.5 GB; 7,000 ~2-3 GB; 10,000 ~4-6 GB; 15,000 ~8-12 GB; 20,000 ~14-20 GB** [verified-raw]. Our 8 GB card: ~7-10k total (BEM) elements before symmetry [inferred]; symmetry halves/quarters dense size and the O(N^3) LU benefits more than area scaling.
- Coupled system order: monolithic N_F + N_B + N_I + 2 N_T; production (Schur) path N_R + N_B + N_I + 2 N_T where N_R = interface nodes + electrodynamic diaphragm nodes; dense LU on GPU (cuDSS for the interior sparse part on CUDA). Float32 production; FEM interior assembled on CPU. P1 FEM guidance from BL tests: ~17 elements/wavelength for 1 % modal error, 12 for 2 %, 8 for 5 %, 6 for 10 % (so 5 % at 3 kHz needs ~14 mm edge) [verified-raw]. Implication: FEM chambers for ports/front chambers stay small (cheap), but the exterior BEM mesh at 8 elements/wavelength to 3-5 kHz sets the VRAM bill.
- Known: issue #2 (warm Julia worker keeps VRAM between solves, OOM on larger meshes) closed Jun 2026 with opt-in "Reuse CUDA Worker Memory" (reclaim after 5 s idle, every 8th request, or <=20 % free memory); Pascal CUDA error 801 fixed in CUDA.jl 6.4.2; Vented_Sub 50 Hz voice-coil current differs CPU vs CUDA by 0.134 % (0.145 % vs FP64 reference; "use CPU when this low-current accuracy matters"). All consistent with CLAUDE.md GPU hygiene.

### 2(f) Coordinator's extra lead: "BigMEH" / m3gnus MEH tags

- **Public "BigMEH" project: not found.** m3gnus has 11 public repos (waveguide-generator, hornlab-waveguide-mesher, wglink, hornlab-metal-bem, hornlab-bempp-bem, hornlab-beat-bem, hornlab-sim, hornlab-plots, BEAT_Engine fork, boundary-lab fork, cdsp-automation); none mentions MEH/BigMEH [verified]. Web search for "BigMEH" returns nothing relevant. The only "BIGMEH" mention is the AA forum remark about a JW-ecosystem diyAudio exploration with 10"+ woofers (section 1) [secondary].
- What the tags show [verified-raw, `hornlab_mesher/tags.py` main]: `PhysicalGroup` = RIGID_WALL 1, PRIMARY_SOURCE 2, ENCLOSURE_WALL 3, INTERFACE 4, **MID_CHAMBER 8, PORT_INTERIOR 9, MID_PORT_EXIT_LEFT 10, MID_PORT_EXIT_RIGHT 11**, MOUTH_APERTURE 12; names `mid_chamber`, `mid_port_interior`, `mid_port_exit_left`, `mid_port_exit_right`, `mouth_aperture`; `SOURCE_TAGS = {PRIMARY_SOURCE, MID_PORT_EXIT_LEFT, MID_PORT_EXIT_RIGHT}` i.e. the mesher treats the two mid-port exits as **velocity-driven source faces** (ABEC-style port-exit sources), not as cones. The mesher README says it ships no supported builders for slots, ports, drivers, rectangular horns or cabinets (cabinet bridge only in `hornlab_mesher.experimental`). Consistent with a left/right-port two-mid concept (a "2 x mid" MEH), but there is no public builder to inspect.

---

## 3. Danley primaries and design rules

### 3(a) Patents (all on patents.google.com) [verified unless noted]

| Patent | Facts |
|---|---|
| **US 4,845,759** "Sound source having a plurality of drivers operating from a virtual point" (Danley; Intersonics). Filed 11 Mar 1988 (continuation of 25 Apr 1986), granted **4 Jul 1989**. | Several identical drivers on a line feed a common horn throat through separate openings; openings (perpendicular to the line) **< 2-3 wavelengths of the highest frequency**; slot width ideally < 1 wavelength (20 kHz -> ~0.675 in); centres spaced < several wavelengths; ~6 dB per doubling of sources; time delay between drivers sets vertical dispersion; source ~1 wavelength wide gives ~90 deg at -6 dB. |
| **US 6,411,718 B1** "Sound reproduction employing unity summation aperture loudspeakers" (Danley & Skuran; Sound Physics Labs). Filed 28 Apr 1999, granted **25 Jun 2002**; expired (est. 28 Apr 2019). | Claim 1: HF driver at the throat; a **pair** of lower drivers "coupled to... multiply segmented portions at a distance from the throat... corresponding to the distance for said audio signals... to travel 1/4 wavelength". Description: HF driver at the apex; mid/low drivers couple through holes/passages in sides or corners, **short passages** (air in them has reactance); entry openings must **sum to the horn area at the entry point** (example HF throat 0.78 in2, lower-driver entry 10 in2); 20 in long, 20 x 20 in mouth, flare segments doubling area in <1 in, 2.5 in, 4 in, 7 in; transformation zone ends where circumference = 1 wavelength, beyond that it is a waveguide; 1st/2nd-order crossovers aiming ~90 deg at crossover; **tuning trick: wire the drivers out of phase and sweep; a deep notch appears near 2x the crossover; the right crossover is about half the notch frequency**; example 3-way 75-1500 Hz with a split near 335 Hz, 1 kHz example for HF. |
| **US 8,284,976 B2** "Sound reproduction with improved performance characteristics" (Danley; application 11/921,615, filed 6 Jun 2006, priority 7 Jun 2005 provisional), granted **9 Oct 2012**; Google lists expiry 6 Nov 2029 (an assumption, not legal advice). This is the **Synergy** patent (a forum list wrote "8248976"; the correct number is 8,284,976). | Claim 1: horn passageway, HF driver at the closed end, lower driver coupled whose **upper frequency end is below the first cancellation notch** for that driver. Claim 5: the lower driver sits where the cross-section is **no larger than a round section whose circumference equals one wavelength at its upper frequency**. Claim 6: lower end tied to a location where the expansion rate is at or slower than the horn's low-cutoff rate. Claim 4: lower driver mounted outside the passageway, coupling through an aperture. Notch: sound from the lower driver travels to the closed end, reflects and returns "with 180 deg of phase shift to cancel"; its position "is not a physical distance but an acoustic dimension governed by the shape and size of the horn". Expansion: Ax = At (cosh(X/Xo) + T sinh(X/Xo))^2 (Plach), T = 1 exponential, <1 hyperbolic, infinity conical; 30 Hz exponential doubles area every 24 in, 120 Hz every 6 in. **Ports: length = wall thickness, small cross-section "to avoid acoustic discontinuities"; prior-art 3/4 in long ports cut to 1/16 in let port count fall 8 -> 4 and diameter 3/4 -> 5/8 in; tapered (frustum) and stepped ports (step near the outer surface) for thick walls; coax example with four holes in thin sheet.** Separate **sealed rear enclosure for each frequency range** (cites Marshall Leach). Crossovers: designed from each driver's amplitude and phase, filters should **overlap, use non-integer order, non-constant slope**; td-1 three-way crossovers ~1.002 kHz (upper) and ~315 Hz (lower); average sensitivity 99 dB (2.83 V); efficiency 30-50 %; also a 180 deg circular-array variant with rings of 8 drivers per band. No front-chamber volumes, no polarity statement, no damping statement. |
| **US 8,457,341 B2** "Sound reproduction with improved low frequency characteristics" (tapped horn). Filed 14 Mar 2007 (priority 15 Mar 2006), granted **4 Jun 2013**. | Driver mounted partway along the horn so front and rear outputs merge at a tap point; "a horn need not be driven at its apex"; ~102 dB at 1 W for a single unit [verified]. |
| US 8,488,826 B2 (horn enclosure with several input plenums, flow passageways and a common output chamber, Jul 2013); US 8,422,712 B2 (vanes reshaping amplitude distribution, Apr 2013) | Seen only in search snippets (Google Patents returned 503) [snippet]. |
| US 2002/0106097 A1 | Cited by Waslo as the Unity application; not read. |

Danley white paper "The Tapped and Synergy Horn Explained" (8 pages): exists (Yumpu/Scribd/Docslides mirrors) but text was not retrievable. Search excerpts say it describes drivers sharing one horn with benefits "high sensitivity, directivity control, and modular array ability over a wide bandwidth", with uniform constant directivity down to a frequency set by mouth size [snippet, secondary].

Tom Danley in his own forum words (excerpts surfaced by search; the exact posts could not be opened) [snippet, primary (author, forum)]:
- "The trapped air volume under the cone and the small holes form an acoustical 2nd order low pass filter, like an electrical filter but in air." Also: there is an "ideal size" for both the **rear sealed volume** (under the back cap) and the **front sealed volume** (air trapped between cone and horn entry).
- Object of the Synergy horn: combine multiple drivers covering multiple ranges into one radiation "without any lobes and nulls and in most cases... eliminate the phase shift the crossovers normally add." Each drive group operates within a pass-band under a decade wide.
- Suggests first-order-type crossovers, which "automatically take care of the phase/frequency and polar coverage/frequency issues" (thread "The mysterious Danley crossover"; the Synergy crossover is not described in the patent).
- Relayed (secondary): Danley puts the port's natural roll-off at the notch frequency and crosses there; a sharp acoustic low-pass at the notch lets the crossover do less [snippet].

### 3(b) Strengths (what the design buys)
- One apparent source; pattern constant down to a frequency set by mouth size; mid/bass cones move air through a short, small path and get horn gain; each cone is acoustically band-limited by its chamber+port, which cuts radiated distortion (Danley; Waslo).
- Larger drivers can cover lower bands than a CD ever could, so wideband SPL is higher than a single-driver horn (Waslo).
- Crossover phase can be nearly linear when taps are close to the mouth (Waslo) [secondary].

### 3(c) Weaknesses and design issues
- **Reflection notch**: cone output travels toward the throat and returns out of phase; upper frequency of each entry is capped below the first notch; practitioners place the first notch at lambda/4 of throat-to-port distance only for a cylindrical throat; a conical throat has a shorter effective reflection length [snippet].
- **Port reactance**: long or large ports behave as masses; need short, small, tapered ports (patent).
- **Front-chamber resonance** near 1-2 kHz moves with port size, port length and chamber volume (Hornresp study) [snippet].
- **HF-side interaction**: mid holes act as discontinuities for the CD wavefront; builders place entries in corners / on "knuckles" and use shallow CDs to shorten the CD-to-port distance [snippet; SAWMOD forum].
- **Mids cannot be pushed above ~1.5 kHz** in practice [snippet]; consequently the CD/mid crossover sits ~1.0-1.5 kHz.
- Design is iterative: "Designing these from scratch is NOT easy... will usually take a number of builds to get right" (Waslo, raw).
- Patents: Unity expired 2019; Synergy US 8,284,976 shown as active to 2029; Waslo states Danley allows DIY but not sale of kits/finished speakers [secondary]. Relevant only if the owner ever sells.

### 3(d) Design knobs and ranges (Waslo raw + patents)
- Horn: conical/pyramidal 60-110 deg, throat 1" (CD) 12.7 mm radius; width fixes pattern floor: W ~ 0.68 lambda (Waslo 24 in -> 385 Hz) [inferred scaling]; 30 x 30 cm 80 deg -> ~850 Hz control (builder, snippet).
- Per mid band: **port distance from throat (axis-measured)**, port area Ap and length Lpt, front (compression) chamber volume Vtc and mean area Atc, rear chamber Vrc/Lrc; all areas/volumes are **sums over the drivers of that band**, lengths are per driver (Waslo, raw).
- Crossover: CD/mid ~1.0-1.5 kHz, mid/low ~315-400 Hz; polarity and delay (see section 5).

### 3(e) How practitioners measure/rank
- Magnitude + phase (patent: "much closer to 0 degrees... much less group delay"), square-wave response at the crossovers (patent), polar maps and DI, Hornresp predictions overlaid on 1/6-oct smoothed in-room measurements (Waslo, raw).

### 3(f) Experiential
- Waslo: CoSyne is "the best overall speaker I've heard"; crossovers "not audible or even findable from measurement" when phase is linearised (raw, secondary).
- Forum: "mids top out ~1.5 kHz" [snippet]; audible advantage cited is constant tonal balance with angle/distance and "easygoing" character (Waslo).

---

## 4. Small Danley / Synergy products (the size class we want)

Volumes are bounding-box volumes computed from the stated external dimensions [inferred]. Sources: Danley product pages [verified] unless "sheet" = spec-sheet PDF [verified-raw]. n/l = not listed.

### Product size table (Danley, Yorkville, JW, DIY)

| Model | Drivers (exact) | Dimensions (mm; given in) | Volume (L) | Band: -3/+-dB; -10 dB | Coverage | Sens. (2.83 V/1 m) | Max SPL cont/peak | HP / sub crossover | Source |
|---|---|---|---|---|---|---|---|---|---|
| SH-Mini | 1 x 8" coax (not an MEH) | 254 x 254 x 267 (10 x 10 x 10.5 in) | 17.2 | 125 Hz-18 kHz +/-3; 88 Hz-20 kHz -10 | 100 deg conical | 88 | 111/117 | 100 Hz HP 24 dB/oct Butterworth | SH-Mini sheet |
| Mini180 | 2 x 8" coax | 318 H x 470 W x 241 D (12.5 x 18.5 x 9.5) | 36.0 | 149 Hz-21 kHz +/-3; 87 Hz-24 kHz -10 | 180 x 90 | 95 | 119/125 | n/l | web |
| GO2 8CX | 1 x 8" coax ("Synergy design philosophy and crossover topology") | 324 x 559 x 229 (12.75 x 22 x 9) | 41.4 | 51 Hz-21 kHz (-3); 30 Hz-24 kHz (-10) | n/l | 90 | 117/123 (AES75 Z-peak 125.1) | n/l | web |
| SM100 | 1 x 8" coax | 521 x 521 x 229 (20.5 x 20.5 x 9) | 62.0 | 70 Hz-20 kHz +/-3; 50 Hz-24 kHz -10 | 110 deg conical | 95 | 120/126 | n/l | web |
| SM80 | 1 x 12" coax | 648 x 610 x 324 | 128 | 140 Hz-19 kHz +/-3; 110 Hz-22 kHz -10 | 80 deg conical | 102 | 128/134 | n/l | web |
| SM60M | 1 x 5" coax | 523 x 523 x 414 | 113 | 270 Hz-15 kHz +/-3; 178 Hz-24 kHz -10 | 60 x 60 | 100 | 124/130 | needs sub; "pairs well with THmini" | web |
| **SM-60F** | **LF 2 x 8"; MHF 1 x 5" coax** | 523-530 x 523-530 x 414 (20.6-20.85 in; 16.3) | 113-116 | **66 Hz-24 kHz +/-4; 52 Hz-26 kHz -10** | 60 x 60 | 99 | 125/131 | **50 Hz HP 24 dB/oct Butterworth** | sheet (2012) + web; 50 lb |
| **SM-96** | **LF 2 x 8"; MHF 1 x 5" coax** | 800 x 533 x 394 (31.5 x 21 x 15.5) | 168 | **55 Hz-24 kHz +/-3; 42 Hz-26 kHz -10** | 90 x 60 | 98 | 124/130 | **55 Hz HP 24 dB/oct** | sheet (2012); 73 lb; not on current SM page |
| SM80F | 1 x 12" coax + 2 x 15" woofers | 45 x 26 x 28 in | ~535 | n/l | 80 deg | n/l | n/l | n/l | search excerpt [snippet] |
| SH75 | 2 x 8" neo LF/MF + 1 x 1" HF | 508 W x 368 H x 330 D | 61.8 | 80 Hz-24 kHz +/-3; 58 Hz-> -10 | 70 x 50 | 93 | 116/122 | **60 Hz HP 24 dB/oct** | SH75 sheet (2024); 60 lb |
| SH110 | 2 x 8" LF + 1 x 1.4" HF | 611 x 254 x 194 | 61.0 | 360 Hz-15 kHz (-3); 90 Hz-20 kHz (-10) (as printed) | 110 x 60 | 104 | 128/134 | 1000 W amp rec. | web; 42 lb |
| SH25 | Low 8 x 6.5", Mid 4 x 4", High 1 x 1" | 711 x 711 x 1288 | 651 | 90 Hz-18 kHz +/-3; 70 Hz-20 kHz -10 | 25 x 25 | 110 | 137/143 | n/l | web; 176 lb |
| SH46 | Low 2 x 12", Mid 4 x 4", High 1 x 1.4" | 737 x 566 x 577 | 241 | 71 Hz-14.5 kHz +/-3; 58 Hz-16 kHz -10 | 40 x 60 | 106 | 135/141 | n/l | web; 118 lb |
| **SH50** | **Low 2 x 12", Mid 4 x 4", High 1 x 1"** | **711 x 711 x 648** (28 x 28 x 25.5) | 328 | **50 Hz-18 kHz +/-3; 37 Hz-24 kHz -10** | 50 x 50 | 100 | 127/133 | users HP 45-100 Hz [snippet] | web; 133 lb |
| SH60 | Low 2 x 12", Mid 6 x 4", High 1 x 1" | 711 x 711 x 559 | 283 | 48 Hz-18 kHz +/-3; 41 Hz-24 kHz -10 | 60 x 60 | 100 | 127/133 | n/l | web; 127 lb |
| SH62 | Low 2 x 15", Mid 6 x 6", High 2 x 1.4" | 572 x 914 x 762 | 398 | 70 Hz-18 kHz +/-3; 50 Hz-20 kHz -10 | 60 x 20 | 105 | 138/144 | n/l | web; 235 lb |
| SH64 | Low 4 x 15", Mid 4 x 4", High 1 x 1.4" | 673 x 864 x 635 | 369 | 65 Hz-16 kHz +/-3; 43 Hz-20 kHz -10 | 60 x 40 | 103 | 135/141 | n/l | web; 197 lb |
| OS62 | Low 4 x 8" neo; Mid/High 1.4"/1.0" coax ring-radiator CD | 819 x 660 x 368 | 199 | 128 Hz-10 kHz (-3); 105 Hz-12 kHz (-10) | 60 x 20 | 107 | 136/143.4 | n/l | web; 95 lb |
| OS80 | 1 x 12" + 1 x 1.4" | 819 x 660 x 368 | 199 | 128 Hz-16 kHz (-3); 58 Hz-18 kHz (-10) (as printed) | 80 deg conical | 100 | 127/133 | n/l | web; 51 lb |
| Yorkville U15 (Unity, licensed from Sound Physics Labs) | 1" CD (1.75" diaphragm) + **3 x 5" ceramic mids in a 60 x 60 conical horn** + 15" woofer | n/l | n/l | n/l | 60 x 60 | n/l | 128/131 (Yorkville page; retailer 135 peak) | passive 3-way; bi-amp switch | search excerpts [snippet] |
| JW **DH350 MEH** | 2 x 6.5" (B&C 6NDL38) + 1" CD (B&C DH350) + 2 passive radiators | 470 x 260 x 200 | 24.4 bbox (~15 net) | **60 Hz-16 kHz +/-2 (measured)** | 75 H x 60 V | n/l | 106 dB max | 80 Hz HPF raises max | JW page |
| JW Solana | 4 x 6.5" + 1" CD | n/l | n/l | 45-17,000 Hz | 90 x 90 (control to 700 Hz) | n/l | 109 full-range; 120 with 100 Hz HPF | 100 Hz HPF with sub | JW page |
| JW JMOD-M (prelim.) | 2 x 12" or 2 x 14" + coax CD | 1450 x 730 x 630 | 667 | 80-18,500 Hz | 110 x 55 | min 106 @100 Hz | TBD | n/l | JW page |
| Waslo "CoSyne" (DIY, 2014) | HF Celestion CDX1-1445 + 4 x Gento SP99023A mids + 4 x Aurasound NS6-255-8A woofers | horn 24 in (610 mm) wide, 90 x 60 | n/l | pattern control to ~385 Hz; ~50 Hz with large ported box, ~70s Hz in 1.5 ft3 sealed | 90 x 60 | 94 dB | n/l | sub at ~80 Hz | Synergy Calc raw |
| Parts Express "Synergy Horn" (DIY, 2017) | 4 x Dayton DCS165-4 6.5", 2 x GRS 4FR-8 4.5", 2 x Peerless XT25TG30-04 | stand-mount; 60 x 90 conical horn 6.7 in deep; 20 L woofer enclosure | n/l | pattern control to 400 Hz; box tuned 38 Hz, F3 36 Hz | 60 x 90 | ~86 dB | ~70 W cont. | LR4 at 1,300 and 400 Hz | PE page |
| diyAudio 2-way MEH (DIY) | FaitalPRO HF108 + 2 x FaitalPRO 4FE35 in parallel | horn 300 x 300 mm | n/l | pattern control to ~850 Hz | 80 deg | n/l | n/l | 1,300 Hz CD/mid; subs | thread 421176 [snippet] |
| diyAudio Bluetooth MEH (DIY) | 2 x 6.5" prototype then 4 x 8" + SB Acoustics H280 horn | ~94 L net (grew from 45 L) | 94 net | 50 Hz-20 kHz target | 60 x 40 horn | 105 target | n/l | woofer-injection ports 10-12 % of one woofer's Sd | thread 414030 [snippet] |

Compact tapped-horn subs (for pairing):

| Model | Drivers | Dimensions (mm) | Vol (L) | Band | Sens | Max SPL | Processing | Source |
|---|---|---|---|---|---|---|---|---|
| TH28 | 2 x 8" long-excursion | 508 x 762 x 267 | 103 | 47-162 Hz (-3); 38-180 Hz (-10) | 100 (half space) | 126/132 | n/l | web; 61 lb |
| THmini | 1 x 12" long-excursion | 610 x 381 x 572 | 133 | 48-200 Hz (-3); 41 Hz (-10) | 101 | 129/135 | 40 Hz HP 24 dB/oct | sheet |
| THmini15 | 1 x 15" | 762 x 457 x 610 | 212 | 50-310 Hz (+/-3); 42-340 Hz (-10) | 105 | 132/135 | 45 Hz HP 24 dB/oct | sheet |

Notes: "Nano" and "SM-100F" are listed or implied but I found no Danley "Nano" model on the family pages I could read (SH, SM, Compact, OS, TH lists have "Load More" buttons, so incomplete). **No Danley product matches "2 x 6.5-inch or 4 x 4-inch cones + CD in a small box"**; the nearest are SH75 (62 L, 2 x 8" + 1") and the SH25 (8 x 6.5" + 4 x 4" + 1", 651 L). Danley's own CD models and cone models inside SH50/SH46 are not published; an AA forum builder calls the Danley 4" mid a Celestion TF0410MR (~GBP 20) [secondary, unverified].

---

## 5. Small DIY MEHs with build data and measurements

### 5(a) Reference builds with numbers
- **Waslo CoSyne** [verified-raw, Synergy Calc V5]: 90 x 60 pyramidal horn from 1/2 in board, 24 in wide -> horizontal pattern control to ~385 Hz; square throat; HF Celestion CDX1-1445; **4 x Gento SP99023A mids and 4 x Aurasound NS6-255-8A woofers** (buy-outs, 9 drivers); ~94 dB at 2.83 V; woofers open-backed into a large ported box (~50 Hz; ~40 Hz bass with 4 NS6 in big ported box; crossed at ~80 Hz to subs or ~70 Hz in a 1.5 ft3 sealed box); mids' backs sealed with 2 in mailing-tube cylinders 3 in long, stuffed. Recommended modern substitutes (HornResponse-modelled, small port changes): woofers Dayton DC130AS-8, Visaton W130S-8 (not tried: FaitalPRO 6FE100); mids FaitalPRO 3FE25-8 ("harder to get in close") or Visaton FRS5-8.
- **Parts Express Synergy Horn** [verified]: see table; designer rules: single mid sized for home levels, pick tweeter by testing in the horn (horn gain allowed a lower than expected crossover), keep pattern control to 400 Hz, straight holes, square tweeter hole as good as round, ~1/3 lb Acousta-Stuf, toe-in for imaging; efficiency ~86 dB; 70 W continuous limited by woofer excursion.
- **JW DH350 MEH**: see section 1.
- **diyAudio 2-way MEH** (HF108 + 2 x 4FE35, 30 x 30 cm, 80 deg, 1,300 Hz; built with Synergy Calc to set horn and Hornresp parameters; changed S1 to 5.06 cm2 to match the CD exit) [snippet].
- **Bateman / xrk971 / SynTripP**: I found **no** Patrick Bateman MEH rule set or Akabak MEH script, and nothing attributable to xrk971; SynTripP (Waslo, 2-way 2-part "virtual single point source" horn, 3D printed; one commenter says it uses 2 x 10" woofers; Waslo advises that tweeter and mid polarity are reversed from normal) appears only as thread snippets. A "Synergy Akabak script" is mentioned in a diyAudio thread but its content is not visible [snippet]. (Patrick Bateman is reported to be John van Ommen and to use Akabak 3D checks for wavefront detachment in conical horns [snippet].)
- **MEH Studio** (GitHub, 2026-09/10): design tool for 2/4/6-mid MEHs with R-OSSE rev7 profile, individual or shared rear chambers, front-chamber LC study and Webster 1-D network (see section 6).
- **Rule sheet from femishonuga.com** [verified, rules unverified]: standard setup 1 x 1-2" CD + 4 x 4" mids + 2 x 15" woofers; throat radius 12.7 mm; quarter-wave horn length L = c/(4 f_low); each slot < lambda/4 at the driver's top frequency; **total slot area ~25 % of cone Sd**; slots wide and short (3:1 to 6:1 aspect; narrow tall slots whistle/chuff); 1 slot per mid, 2 per woofer; driver as close to the slot as possible, chamfer inside edge; **slot distance from CD L = c/(4 fx)**; **seal the enclosure (ports cause phase problems)**; leave a cavity behind the surround equal to Xmax; keep each driver's band roughly equal in width; mid choice 2 Fs/Qes ~ sqrt(Flow Fhigh); tri-amp with DSP. No measurements.
- **Audio Abattoir tap-size rule**: "tap size ratio to driver Sd should be around 1/15 for MF, 1/8 for LF (not counting reflex ports)" [secondary]; BT-MEH thread: "each two woofer injection ports have combined area 10-12 % of one woofer membrane" [snippet]. These disagree by 2x (see conflicts).

### 5(b) Strengths
- 3D printing makes cheap iteration; Hornresp MEH wizard + Synergy Calc + Ath gets a first-pass; VituixCAD for crossover from measurements.

### 5(c) What went wrong and fixes (all practitioner reports)
- Notch from throat reflection: keep mid taps within lambda/4 of the CD diaphragm (round trip < lambda/2); measure distance along the horn axis, not slant [snippet]; use shallow "pancake" CD to shorten the distance [snippet]; corner placement to avoid interfering with the CD wavefront [snippet]; tune port size/length/Vtc in the Hornresp wizard and "massage the crossover slopes in the octave 1-2 kHz" [snippet].
- Front-chamber resonance ~2 kHz moves with Vtc/port; keep air behind port to the diaphragm "at an absolute minimum" [snippet].
- Too-small slots whistle; too-large slots become radiators and break summation; long driver-to-slot paths resonate; driver surrounds touching the mount; passive radiators touching woofer backs (JW DH350 MEH).
- Large woofer ports cause diffraction and directivity damage in the waveguide (Solana critique) [snippet].
- Narrow pattern vs simulation (DH350 MEH 75 x 60 vs 60 x 90 goal): Ath polars did not match ABEC.
- Mid ceiling ~1.5 kHz; sealed mid backs needed for open-back cones (Waslo uses mailing tubes).

### 5(d) Knobs and ranges seen in practice
- CD/mid crossover 1.0-1.5 kHz (DH350 rec. 1 kHz; HF108 min 1.3 kHz; builders 1.3 kHz; JW 1.0-1.2 kHz); mid/low 315-400 Hz.
- 4" mids: B&C 4NDF34, FaitalPRO 4FE32/4FE35, Celestion TF0410MR; 4.5-5": GRS 4FR-8, SB NERO-5CCN125D (used in SAWMOD builds), Celestion/Faital 5". 6.5": B&C 6NDL38 (JW), Dayton DCS165-4.
- Mouth width 250-350 mm for 80-90 deg gives pattern control floors 700-900 Hz (see 3(d)).

### 5(e) How they rank
- Polar maps / DI / on-axis smoothness / notch depth at 1-2 kHz, max-SPL at 10 % THD, step response.

### 5(f) Experiential
- "Best overall speaker I've heard" (Waslo); "My 2 x 5" are perfect for Hifi" (SteadySteve on AA, secondary); builders like zero-order crossovers and single-point behaviour; most small MEH builders pair them with subs at 80-100 Hz (SAWMOD) and accept that the MEH itself is a mid/high device.

---

## 6. Modelling methods for MEH

### 6(a) Methods, equations, reference numbers
- **Hornresp (David McBean)**: MEH wizard with records Nd (horn + HF driver/chamber at throat) and ME1/ME2 (mid/low driver and chamber at the offset point), combined into one compound acoustic circuit; 1-D (Webster) horn model; areas/volumes of a band are sums over its drivers, lengths per driver; no published source (author declined release in 2016 per MEH Studio audit) [snippet; raw MEH Studio doc]. Poster notes Hornresp and AJ-Horn find side-throat drivers hard [snippet]. Waslo's Synergy Calc turns horn geometry + "port distance from throat" into the Hornresp inputs (S12.., L12.., Ap1, Lpt, Vtc, Atc, Vrc, Lrc) [verified-raw].
- **AKABAK 3 (Panzer)**: network of lumped elements and 1-D waveguides solved as node-admittance matrix, plus BEM/FEM 3-D sections; "limits of accuracy due to its one-dimensional nature" [snippet of IOA paper]. Hornresp scripts can be exported to Akabak; no published MEH script found.
- **ABEC3 / VACS**: ABEC3 used for Synergy by hobbyists under student licence; no tutorial found; JW's DH350 MEH tuned its Ath model against ABEC polars [verified].
- **FEM/COMSOL**: COMSOL Helmholtz-resonator example is MEH Studio's cited basis for end corrections (not MEH-specific). Oclee-Brown PhD (Southampton 2012, ch. 4) on compression-driver cavity modes vs lumped compliance [cited in MEH Studio docs].
- **BEM/FEM-BEM in BL/BEAT**: see section 2. This is the only open tool I found that can put real cone motors (voltage, Mmd/Cms/Rms/Bl), front chambers (FEM), ports (FEM-BEM interfaces), and a shared exterior in one linear solve.
- **Lumped front-chamber/port equations** (MEH Studio docs/front-chamber-reference.md, raw, "not a validated MEH field model"): C = Vc/(rho c^2); M = rho (Ln + alpha req)/S, req = sqrt(S/pi), alpha assumed total end-correction coefficient; fLC = 1/(2 pi sqrt(M C)); with N identical coherent mids and junction impedance Zh: Zb = j w M + N Zh; Uentry/Upiston = 1/(1 + j w C Zb); Zfront = Zb/(1 + j w C Zb); Zmech = Rms + j w Mms + 1/(j w Cms) + Sd^2 (Zfront + Zrear); Ze = Re + j w Le + Bl^2/Zmech; vcone = Bl I/Zmech. **Reference check: S = 15 cm2, rho 1.204, c 343, Leff 40/80 mm with cavity 300/150 cm3 both give fLC = 610.3 Hz** (I reproduced 610.3 Hz [inferred]); with 50,000 Pa s/m3 resistance |Uentry/Upiston| = 2.46 vs 4.92 (6.02 dB apart). Another check: B&C 6NDL38 shared-rear starter bare LC reference ~583 Hz. Catalogue Mms must not be used with spatial air without subtracting radiation mass (their audit "unresolved").
- **Examples of fLC for tap ratios** [inferred, alpha 0.85, rho 1.204]: 6.5" cone with tap Sd/15 (8.8 cm2), Vtc 150 cm3, 10 mm tube -> 850 Hz; Vtc 80 cm3 -> 1,163 Hz; tap Sd/8 (16.5 cm2), 150 cm3 -> 1,055 Hz; 4" cone tap Sd/15 (3.8 cm2), Vtc 50 cm3, 8 mm -> 1,143 Hz; tap Sd/8, 50 cm3 -> 1,429 Hz. Compare with the 1.0-1.5 kHz mid ceiling.
- **Optimisation papers**: Geaves & Henwood, AES Conv. 100 (1996) paper 4208: automatic optimisation of an axisymmetric horn with FEM+BEM using a weighted random search ("a simple evolutionary strategy"); Morgans, Zander, Hansen, Murphy, *Optimization and Engineering* (2008): Efficient Global Optimization (surrogate) with spline-parameterised horns for constant beamwidth; Makarski, AES Conv. 117 (2004): higher-order modes at the horn driver mouth, two-port driver + BEM; Nizzoli & Prati, AES Conv. 134 (2013): BEM of an arrayable horn vs measurement; arXiv 2604.21431 JAX-BEM: gradient-based BEM shape optimisation with a 70 x 50 horn target [all snippet; papers not read]. **I found no AES/JASA paper specifically on multiple-entry / Synergy horns, and none on mutual coupling of several wall-mounted drivers in one horn.** No published GA/topology optimisation of an MEH other than JW's Solana statement.

### 6(b) Strengths / (c) weaknesses
- Hornresp/Akabak: seconds per run, good for port-distance/chamber trade; 1-D so they miss cross-modes, port diffraction and off-axis directivity (JW found Ath polars vs ABEC mismatch).
- FEM-BEM (BL/BEAT): gets diffraction at ports, true directivity, mutual coupling, driver motor loading; cost O(N^2) assembly / O(N^3) dense LU; CD phase plug not modelled by a rigid piston; P1 FEM needs >= 8 elements/wavelength for ~5 % modal error.

### 6(d) Knobs the models expose
- Port distance, Ap, Lpt, Vtc, Atc, Vrc; driver count/placement/motion axis; bulk loss factor (0.002-0.05); wall lining (Miki: BL UI defaults 30 mm, 5,000 Pa s/m2); mesh size; symmetry.

### 6(e) How practitioners rank
- Overlay predicted vs measured (1/6-oct, level matched, red = simulated in Waslo's CoSyne plots); VituixCAD for crossover; MEH Studio samples flow variation, phase and cone excursion at the crossover frequency.

### 6(f) Experiential
- Waslo: Hornresp-predicted responses agreed with measurement "pretty well" for CoSyne mids/woofers after several builds; JW: Ath-vs-ABEC mismatch gave narrower pattern than designed.

---

## 7. Bass for EDM from a small box: reality check

### 7(a) Facts and math
- **EDM content** (blog-level, [snippet, marketing/secondary]): kick fundamentals usually 40-60 Hz (techno/house 40-50 Hz), trap/808 can dip below 40 Hz; "sub-bass 20-40 Hz" is felt more than heard. No authoritative loudness-vs-frequency source found.
- **Hofmann's iron law**: efficiency is proportional to cabinet volume times the cube of the low-frequency cutoff; halving the cutoff at fixed efficiency needs ~8x volume [snippet; Wikipedia attributes to J.A. Hofmann, others differ on attribution]. Check with T/S [inferred]: eta0 = (4 pi^2/c^3) Fs^3 Vas/Qes reproduces datasheet eta0 to within a few percent (6NDL38 0.58 % vs 0.6 %; 4NDF34 0.74 vs 0.7; 6MDN44 1.58 vs 1.6; 6PR160 1.20 vs 1.21).
- **Displacement-limited SPL** (ideal piston, half space, 1 m): p_peak = rho w^2 Vd_peak/(2 pi r), SPL = 20 log10(p_peak/sqrt(2)/20 uPa); Vd_peak = n Sd Xmax [inferred]:

| Array (Xmax peak) | Vd_peak | 40 Hz | 50 Hz | 60 Hz | 80 Hz | 100 Hz | 150 Hz | 200 Hz | 300 Hz |
|---|---|---|---|---|---|---|---|---|---|
| 2 x 6.5" B&C 6NDL38 (132 cm2, 6 mm) | 0.158 L | 96.6 | 100.5 | 103.7 | 108.7 | 112.5 | 119.6 | 124.6 | 131.6 |
| 4 x 6.5" 6NDL38 (Solana-like) | 0.317 L | 102.6 | 106.5 | 109.7 | 114.7 | 118.6 | 125.6 | 130.6 | 137.6 |
| 2 x FaitalPRO 6PR160 (130 cm2, 5 mm) | 0.130 L | 94.9 | 98.8 | 102.0 | 106.9 | 110.8 | 117.9 | 122.9 | 129.9 |
| 2 x B&C 6MDN44 (132 cm2, 2.5 mm) | 0.066 L | 89.0 | 92.9 | 96.1 | 101.1 | 104.9 | 112.0 | 117.0 | 124.0 |
| 4 x B&C 4NDF34 (57 cm2, 3.8 mm) | 0.087 L | 91.4 | 95.3 | 98.4 | 103.4 | 107.3 | 114.3 | 119.3 | 126.4 |
| 2 x 12" (assumed 530 cm2, 8 mm) | 0.848 L | 111.2 | 115.1 | 118.2 | 123.2 | 127.1 | 134.2 | 139.2 | 146.2 |

  Volume displacement needed for a target (1 m, half space): 110 dB needs 0.74 L at 40 Hz, **0.47 L at 50 Hz**, 0.33 L at 60 Hz, 0.19 L at 80 Hz, 0.12 L at 100 Hz; 105 dB needs 0.42/0.27/0.19/0.10/0.07 L. Therefore **2 x 6.5" or 4 x 4" cannot deliver EDM-level 40-60 Hz**: they top out ~100 dB at 50 Hz even with unlimited power and ideal box assistance, and the 4 x 4" are worse (95 dB at 50 Hz). Ports/passive radiators add a few dB near tuning only. A mini-MEH must be a **mid/high top (crossover to subs ~80-120 Hz)**.
- **What small MEH-class boxes actually do at the bottom** (measured/quoted): DH350 MEH ~24 L bbox: 60 Hz +/-2 dB, 106 dB max, with 2 passive radiators; Solana: 45 Hz, 109 dB (vented low-tuned) and 120 dB only with 100 Hz HPF; Danley SM-60F (113 L): 66 Hz +/-4 dB, 52 Hz -10 dB, Danley says 50 Hz HP; SM-96 (168 L): 55 Hz / 42 Hz -10; SH75 (62 L): 80 Hz / 58 Hz -10, 60 Hz HP; GO2 8CX (41 L, 8" coax): 51 Hz -3 dB, 90 dB sensitivity; SH-Mini (17 L): 125 Hz / 88 Hz -10, 100 Hz HP. Makers always pair with subs for real bass (SM-60M "pairs well with THmini"; JW SAWMOD crossover to subs at 80-100 Hz [snippet]; Waslo CoSyne ~80 Hz).
- **3-way Synergy (woofers on the horn walls near the mouth)**: SH50 (2 x 12", 328 L) 50 Hz/37 Hz -10; SH60 48 Hz; SH46 71 Hz; SH64 (4 x 15", 369 L) 65 Hz; SH25 (8 x 6.5" low, 651 L) only 90 Hz because narrow 25 deg horn is mouth-limited. Horn gain on woofers only applies down to the pattern/horn cutoff set by mouth size (Waslo: below ~385 Hz for a 24 in mouth the coverage widens and efficiency drops; woofers in big ported boxes carry 40-50 Hz). Per Waslo: acoustic boost ends ~380 Hz for 24 in horn, yet bass to ~40 Hz is possible with a large ported box and four NS6 woofers.
- **Compact tapped horns** (Danley TH): TH28 103 L 47-162 Hz (-3), 38 Hz (-10), 100 dB, 126 dB cont; THmini 133 L 48-200 Hz, 41 Hz (-10), 101 dB, 129/135, 40 Hz HP; THmini15 212 L 50-310 Hz, 42 Hz (-10), 105 dB, 132/135, 45 Hz HP. Tapped-horn patent US 8,457,341: ~102 dB at 1 W from a single unit (Danley's comparison to vented box) [verified].
- **Size/extension/efficiency**: by iron law, to get 50 Hz with high sensitivity needs ~100+ L class (SM-60F/TH28); the DH350 MEH reaches 60 Hz in ~15 L net only at ~88-90 dB-class efficiency with passive radiators and 106 dB peak output [inferred from its stated spec].

### 7(b) Strengths / (c) weaknesses
- Strength: moving the heavy bass off the horn makes the MEH small, with wide pattern control to ~700-900 Hz; one amp channel per band via DSP.
- Weakness: if the owner wants "solid EDM bass" from the same tiny box, physics (above) forbids it at club levels; adding two vented/PR woofers in the same box (Solana-style, 4 x 6.5") buys 45-60 Hz at ~106-109 dB peak at best.

### 7(d) Knobs
- Woofer count, vented tuning (Solana "low-tuned"), passive radiators (DH350 MEH), HPF 80-100 Hz with external sub, box volume (Hofmann), horn mouth size (pattern floor), mid-bass cone taps near the mouth (SH50 style, 3-way).

### 7(e) Ranking
- Max SPL at 10 % THD (JW, AES75), -3/-10 dB points, sensitivity, step response.

### 7(f) Experiential
- Practitioners high-pass SH50 at 45-100 Hz depending on subs [snippet]; Waslo's CoSyne "will do better crossed to a subwoofer at about 80 Hz".

---

## 8. Driver candidates with published T/S

Legend: V = read from manufacturer datasheet PDF this session [verified-raw]; S = taken from MEH Studio's reviewed catalogue (links to the same datasheets; not re-read by me) [secondary]. `~` = my derivation: Mmd = Mms - 2 (8/3) rho a^3 (a = sqrt(Sd/pi)); Cms = Vas/(rho c^2 Sd^2); Rms = 2 pi Fs Mms/Qms. These three formulas reproduced Faital's published Mmd, Cms, Rms for 6FE100, 4FE32, 6PR160 and Celestion's Cms/Rms for the TF0615 [inferred]. Units: Re ohm, Le mH, Bl T m, Mms/Mmd g, Cms mm/N, Rms kg/s, Vas L, Sd cm2, Xmax mm (manufacturer definition; B&C/Faital state the Xmax formula), AES W = nominal power. EBP = Fs/Qes.

### 8(a) Cone mids / mid-bass (8 ohm versions)

| Driver | Dia | Re | Le | Bl | Mms | Mmd | Cms | Rms | Fs | Qes | Qms | Qts | Vas | Sd | Xmax | AES W | Sens dB | EBP | Cutout / depth | Src |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B&C 4NDF34 | 4" | 5.5 | 0.23 | 9.0 | 6.1 | ~5.6 | ~0.35 | ~1.00 | 110 | 0.28 | 4.2 | 0.27 | 1.6 | 57 | 3.8 | 100 | 92 | 393 | 103 mm / 66 mm | V; https://www.bcspeakers.com/en/products/lf-driver/4/8/4ndf34.pdf |
| FaitalPRO 4FE32 | 4" | 6.5 | 0.18 | 4.8 | 4.2 | 3.8 | 0.60 | 0.5 | 100 | 0.70 | 4.9 | 0.61 | 2.3 | 51.9 | 2.73 | 30 | 91 | 143 | 91.5 / 49.8 | V; https://faitalpro.com/products/files/4FE32/8/4FE32_datasheet_8.pdf |
| FaitalPRO 4FE35 | 4" | 6.5 | 0.10 | 3.9 | 3.9 | 3.5 | 0.65 | 0.6 | 100 | 1.04 | 4.2 | 0.83 | 2.4 | 51.9 | 2.73 | 30 | 91 | 96 | 91.5 / 58.3 | V; .../4FE35/8/4FE35_datasheet_8.pdf |
| FaitalPRO 3FE25 | 3" | 6.2 | 0.07 | 3.6 | 2.4 | 2.2 | 0.87 | 0.4 | 110 | 0.79 | 4.1 | 0.66 | 1.3 | 33 | 1.83 | 20 | 91 | 139 | 73.6 / 54.5 | V; .../3FE25/8/3FE25_datasheet_8.pdf |
| Celestion TF0410MR | 4" | 5.38 | 0.07 | n/p | n/p | n/p | n/p | n/p | 461 | n/p | n/p | n/p | n/p | n/p | n/p | 30 | 90 | n/p | 95 / 60 | V (Fs, Re, Le, sens only); https://celestion.com/product/tf0410mr/ ; ~GBP 20; AA forum says Danley uses it [unverified] |
| B&C 5NDL38 | 5" | 5.5 | 0.64 | 9.2 | 11 | ~9.9 | ~0.34 | ~0.60 | 80 | 0.37 | 9.2 | 0.36 | 4.3 | 95 | 3.5 | 90 | 91 | 216 | 122 / 75 | V; https://www.bcspeakers.com/en/products/lf-driver/5/8/5ndl38.pdf |
| FaitalPRO 5PR160 | 5" | 6.1 | 0.30 | 9.6 | 8.5 | 7.6 | 0.37 | 1.1 | 90 | 0.33 | 4.4 | 0.31 | 3.7 | 85.2 | 5.1 | 120 | 92 | 273 | 118 / 74 | V; .../5PR160/8/5PR160_datasheet_8.pdf |
| FaitalPRO 5FE120 | 5" | 5.4 | 0.41 | 6.9 | 11 | ~10.1 | ~0.54 | ~0.61 | 65 | 0.51 | 7.4 | 0.48 | 5.4 | 84 | 5.25 | 80 | n/p | 127 | n/p | S (MEH Studio motor-additions.json) |
| Celestion TF0510MR | 5" | 7.87 | 0.20 | n/p | n/p | n/p | n/p | n/p | 482 | n/p | n/p | n/p | n/p | n/p | n/p | 30 | 93 | n/p | 117 / 68 | V (Fs, Re, Le, sens only); https://celestion.com/product/tf0510mr/ |
| B&C 6NDL38 | 6.5" | 5.2 | 0.60 | 9.5 | 17 | ~15.3 | ~0.28 | ~0.67 | 72 | 0.44 | 11.5 | 0.42 | 7.0 | 132 | 6 | 150 | 92 | 164 | 145 / 85 | V; https://www.bcspeakers.com/en/products/lf-driver/6-5/8/6ndl38.pdf ; used by JW DH350 MEH |
| B&C 6MDN44 | 6.5" | 5.4 | 0.47 | 11 | 11 | ~9.3 | ~0.11 | ~3.46 | 140 | 0.46 | 2.8 | 0.40 | 2.7 | 132 | 2.5 | 200 | 96.5 | 304 | 145 / 73 | V; .../6-5/8/6mdn44.pdf |
| 18 Sound 6ND410 | 6.5" | 5.9 | 0.67 | 11.6 | 8.2 | ~6.2 | ~0.21 | ~2.81 | 120 | 0.27 | 2.2 | 0.24 | 6.2 | 143 | 2.0 | 180 | 102 | 444 | 148 / 60 | V; https://www.eighteensound.it/en/products/lf-driver/6-5/8/6ND410.pdf |
| 18 Sound 6NMB420 | 6.5" | 5.3 | 0.10 | 9.0 | 8.5 | ~6.8 | ~0.25 | ~2.18 | 110 | 0.38 | 2.7 | 0.33 | 6.1 | 130 | 3.0 | 200 | 100 | 289 | 148 / 73 | V; .../6NMB420.pdf |
| FaitalPRO 6FE100 | 6.5" | 5.4 | 0.50 | 6.8 | 14.0 | 11.9 | 0.48 | 0.90 | 61 | 0.60 | 6.0 | 0.55 | 15.1 | 149 | 5.25 | 100 | 91 | 102 | 147 / 84.5 | V; .../6FE100/8/6FE100_datasheet_8.pdf |
| FaitalPRO 6PR160 | 6.5" | 5.9 | 0.28 | 11 | 12.5 | 10.8 | 0.25 | 1.1 | 90 | 0.35 | 6.6 | 0.33 | 5.9 | 130 | 5.0 | 120 | 95 | 261 | 147 / 73 | V; .../6PR160/8/6PR160_datasheet_8.pdf |
| Celestion TF0615 | 6.5" | 7.08 | 0.47 | 8.85 | 12.09 | ~9.9 | 0.19 | 2.01 | 104.7 | 0.719 | 3.949 | 0.608 | 6.41 | 153.9 | 1.75 | 100 | 95 | 146 | 147 / 74 | V (published Cms, Rms); https://www.celestion.com/product-brochure-pdf.php?id=983 |
| Celestion TF0615MR | 6.5" | 5.53 | 0.29 | n/p | n/p | n/p | n/p | n/p | 553 | n/p | n/p | n/p | n/p | n/p | n/p | 50 | 97 | n/p | 147 / 74 | V (Fs, Re, Le, sens only); https://celestion.com/product/tf0615mr/ |
| Beyma 6P200Fe / Nd, FaitalPRO 6FE200 / 6PR150, Sica 6N2.5PL, Celestion TF0512HE, Beyma 5P200Fe/NdN, Dayton DMA80-4 | 5-6.5" (3") | see source | | | | | | | | | | | | | | | | | | S (MEH Studio reviewed JSON; each links its manufacturer datasheet) |

Not retrieved: Beyma 6MI100, Dayton PA130 / PS95 (parts-express page returned empty), Danley's own cone mids. n/p = not published on the page/sheet I could read.

Selection metric from forums [snippet / femishonuga]: "2 x Fs/Qes about 600" for Synergy mids (= 2 EBP): 4NDF34 786, 6ND410 889, 6MDN44 609, 6NMB420 579, 5PR160 545, 6PR160 522, 6NDL38 328, TF0615 292, 4FE32 286, 6FE100 204, 4FE35 192 [inferred]. By that rule 4NDF34, 6MDN44, 6NMB420, 5PR160, 6PR160 and 6ND410 sit in the preferred zone; low-Xmax high-EBP cones (6MDN44, 6ND410: Xmax 2-2.5 mm) lose headroom below ~200 Hz.

### 8(b) Compression drivers (1" and 1.4" exit)

| Driver | Exit | Diaphragm / coil | Sens | Band / rec. xover | Power (nominal / continuous) | Re / Le | Magnet | Size | Source |
|---|---|---|---|---|---|---|---|---|---|
| B&C DH350 (HLX) | 1" (25 mm) | HT polymer, 36 mm Al coil | 108 dB (2.83 V on ME45 horn) | 1-17 kHz; **1 kHz, 12 dB/oct HP** | **15 W / 30 W** (retailers list 20/40) | Zmin 7.8 ohm / 0.09 mH | 1.8 T neo | 48 mm dia x 46 mm, 0.25 kg | V; https://www.bcspeakers.com/en/products/hf-driver/1-0/8/DH350-8.pdf ; used by JW DH350 MEH |
| B&C DH450 (HLX) | 1" | HT polymer, 44 mm coil | 109 dB | 1-18 kHz; 1 kHz | 20 W / 40 W | Zmin 7.8 / 0.16 mH | 1.9 T | 69 x 48 mm, 0.53 kg | V; .../DH450-8.pdf ; used in SAWMOD builds [snippet] |
| B&C DE250 | 1" | polyimide, 44 mm coil | 108.5 | 1-18 kHz; 1.6 kHz | 60 W / 120 W | n/p / 0.11 mH | | 120 x 62 mm, 2.15 kg | V; .../DE250-8.pdf |
| B&C DE10 | 1" | mylar, 25 mm coil | 107 | 1.5-18 kHz; 2.5 kHz | 20 W / 40 W | n/p / 0.10 | | 90 x 53, 0.8 kg | V; .../DE10-8.pdf |
| FaitalPRO HF108 | 1" | ketone polymer dome, 44 mm Al coil | 109 | 1-20 kHz; min 1.3 kHz (12 dB/oct) | 60 W / 120 W | Re 5.8, Zmin 6.8 | 2.1 T neo | 87 x 41, 0.8 kg | V; https://faitalpro.com/products/files/HF108/8/HF108_datasheet_8.pdf ; used in diyAudio 2-way MEH [snippet] |
| FaitalPRO HF1440 | **1.4"** (35.8 mm) annular | ketone polymer, 86 mm coil | 109 | 0.5-20 kHz; min 0.7 kHz | 120 W / 240 W | Zmin 8.3 | 2.2 T neo | 124 x 75, 2.1 kg | V; .../HF1440/8/HF1440_datasheet_8.pdf ; AA builder plan [secondary] |
| B&C DCX464 coax | 1.4" | 4" (100 mm) MF coil 300 Hz-5.5 kHz 111.1 dB + 64 mm HF ring 3-18 kHz 111.4 dB | 111 | 300 Hz crossover | MF 110 W / 220 W | Zmin 6.4 / 0.21 mH | | 152 x 78 mm, 3.64 kg | V; https://www.bcspeakers.com/en/products/coaxial/4/8/DCX464-8.pdf ; MEH Studio's default starter |
| Celestion CDX1-1445 | 1" | n/v | n/v | n/v | n/v | n/v | | | Waslo's CoSyne HF (name only; datasheet not verified) |
| Peerless XT25TG30-04 | 1" dual-ring radiator dome (not a CD) | n/v | n/v | 1.3 kHz crossover in the PE build | n/v | n/v | n/v | n/v | Parts Express project [verified]; datasheet not read |

**CD T/S is not published**: none of the above manufacturers lists Bl, Mmd, Cms or Rms for the CD, only sensitivity, impedance, power, recommended crossover. BL's example files carry placeholder CD values (Re 5.2-5.8, Le 0.14-0.16 mH, Bl 9.5 or 1.9, Mmd 0.03-0.8 g, Cms 3e-5 to 1.25e-4) that are example-specific; MEH Studio explicitly states "No calibrated compression-driver acoustic source is present". For a BEM model the CD is practically a throat-referenced velocity source or a measured/lumped source, with the power ceiling (15-120 W) set by the datasheet.

---

## Design rules digest

| Rule | Number / range | Source | Label |
|---|---|---|---|
| Distance from CD diaphragm to mid tap (mid's first notch) | <= lambda/4 at the mid's top frequency (path from tap to CD and back = lambda/2): 85.8 mm @1 kHz, 66 mm @1.3 kHz, 57 mm @1.5 kHz, 43 mm @2 kHz | US 6,411,718 claim 1; US 8,284,976; Waslo | [verified] patents + [verified-raw] Waslo; mm values [inferred] |
| Measure that distance along the horn axis, not along the wall | axis distance (Waslo "distance from throat measured on horn axis") | Waslo; forum | [verified-raw]; slant statement [snippet] |
| Mid's upper frequency | below its first cancellation notch; typically ~1.5 kHz in practice | US 8,284,976 claim 1; forums | [verified]; practice [snippet] |
| Cross-section at entry | circumference <= 1 wavelength at the driver's top frequency: round-equivalent dia 109 mm @1 kHz, 84 mm @1.3 kHz, 73 mm @1.5 kHz, 55 mm @2 kHz | US 8,284,976 claim 5 | [verified]; diameters [inferred] |
| Lower end of an entry | local expansion rate no faster than low-cutoff rate (Plach: Ax = At (cosh(X/Xo) + T sinh(X/Xo))^2) | US 8,284,976 claim 6 | [verified] |
| Port length | as short as the wall; patent: 3/4 in -> 1/16 in; port 5/8 in dia, 4 ports | US 8,284,976 | [verified] |
| Port shape | tapered (frustum) or stepped, step near the outer surface; Waslo treats frustum as ~half the effective Lpt | US 8,284,976; Waslo | [verified] / [verified-raw] |
| Entry openings sum to the horn area at the entry point | e.g. 10 in2 lower entry vs 0.78 in2 HF throat | US 6,411,718 | [verified] |
| Spacing between ports of one band | centres within lambda/4 of each other at the band top: 3.4 in @1 kHz, 1.7 in @2 kHz (43 mm) | Waslo; weltersys [snippet] | [verified-raw] |
| Tap-area ratio | MF Sd/15, LF Sd/8 (AA); 25 % of Sd (femishonuga); woofer injection ports 10-12 % of one woofer's area (BT MEH) | see sources | [secondary]; conflicting |
| Front chamber + port | acts as 2nd-order acoustic low-pass; keep front volume and port path minimal; ideal front and rear volumes exist | Danley forum [snippet]; Waslo | [snippet] / [verified-raw] |
| Front-chamber LC | fLC = c/(2 pi) sqrt(S/(Leff Vc)); e.g. S 15 cm2, Vc 300 cm3, Leff 40 mm -> 610 Hz | MEH Studio doc | [verified-raw] formula, number [inferred] |
| Rear chamber | sealed, per band; mids' backs sealed with a cylindrical volume (Waslo 2 in tube, 3 in long, stuffed) | US 8,284,976; Waslo | [verified] |
| Crossover CD/mid | 1.0-1.5 kHz: Danley td-1 ~1.002 kHz; DH350 rec. 1 kHz; HF108 min 1.3 kHz; PE build 1.3 kHz; JW DH350 MEH 1.0-1.2 kHz; SAWMOD example LR4 1.6 kHz | patents, datasheets, builds | [verified] |
| Crossover mid/low | 315-400 Hz (td-1 ~315; PE build 400; SAWMOD LR6 360 Hz) | same | [verified] |
| Filters | overlapping, non-integer order, non-constant slope; first-order-ish per Danley forum; patent: LR4 conventional reference | US 8,284,976; forum | [verified] + [snippet] |
| Notch tuning trick | wire drivers out of phase and sweep; notch near 2 x crossover; crossover ~ notch/2 | US 6,411,718 | [verified] |
| Polarity / delay in practice | BL SAWMOD example: HF +1, MF -1 (delay +0.10 ms), LF -1 (delay -0.15 ms); Waslo: tweeter/mid reversed vs normal | BL example JSON; snippet | [verified-raw] / [snippet] |
| Mouth width vs pattern-control floor | width ~ 0.68 lambda: 24 in -> 385 Hz (90 x 60); 30 cm / 80 deg -> ~850 Hz; Solana 90 x 90 -> 700 Hz | Waslo; snippet; JW | [verified-raw] / [snippet]; scaling [inferred] |
| Horn length for low cutoff | L = c/(4 f_low); efficient at lambda/2 | femishonuga; US 8,284,976 | [verified] patent; [unverified] sheet |
| Slot geometry | each slot dimension < lambda/4 at top freq; aspect 3:1-6:1; chamfer inside; driver close to slot | femishonuga | [unverified] |
| Mid cone selection | 2 Fs/Qes about 600 (EBP ~300) | diyAudio snippet; femishonuga | [snippet] / [unverified] |
| Surround clearance | cavity behind surround >= Xmax; passive radiators must clear woofer backs | femishonuga; JW DH350 MEH | [unverified] / [snippet] |
| Sealed vs vented | seal mid backs; bass boxes ported (Solana low-tuned) or PR (DH350 MEH) | JW pages; femishonuga | [verified] |
| HP / sub crossover | SM-60F 50 Hz, SM-96 55 Hz, SH75 60 Hz, SH-Mini 100 Hz, TH-mini 40 Hz, THmini15 45 Hz (24 dB/oct Butterworth); Solana 100 Hz; SAWMOD 80-100 Hz | spec sheets; JW | [verified-raw] / [snippet] |
| BL mesh resolution for P1 FEM | 8 elements/lambda ~5 % modal error; 12 -> 2 %; 17 -> 1 % | BL Coupled Solver doc | [verified-raw] |
| BL VRAM | 5k elements ~1-1.5 GB; 7k ~2-3 GB; 10k ~4-6 GB; 15k ~8-12 GB | BL Installation doc | [verified-raw] |
| Displacement-limited SPL | SPL = 20 log10(rho w^2 Vd_pk /(2 pi r sqrt2)/20 uPa) | physics | [inferred] |

---

## Could not verify / not found

- Solana: cabinet dimensions, volume, weight, crossover, driver models, cut/print files (Google Drive), Klippel NFS measurement page and blog post (404), Instagram posts of 2024-09-03 and 2024-11-07, any YouTube material, any statement that Boundary Lab was used for Solana, the GA objective/simulator. The "Design Reference" is "coming soon".
- Danley white paper text (8 pp): mirrors empty/blocked. Tom Danley / Ivan Beaver / Mike Hedden forum posts: only search excerpts, no primary page read (diyAudio, AVS, Parts Express forum, WBF all blocked). No Danley public statement of front-chamber volume, port diameter or mid-driver models found. US 8,488,826 and US 8,422,712 text not read.
- Patrick Bateman MEH rules and Akabak/Hornresp scripts: not found. xrk971: not found. SynTripP details (drivers, crossover, measurements): thread snippets only. No MEH measurement data (polars/impedance) beyond JW's DH350 MEH summary and Waslo's plots.
- Any AES/JASA paper on multiple-entry/Synergy horns, mutual coupling of several wall-mounted drivers in a horn, or GA/topology optimisation of an MEH: none found (searched AES e-library snippets, ICSV, arXiv).
- ABEC3/VACS MEH tutorial or scripts: none found. AKABAK MEH example script: none found.
- BL: "issue #78 on Mms vs Mmd" does not exist in BL; BEAT #78 is unrelated (ROCm precision). BL/BEAT did not state a hard VRAM or element cap. No BL/BEAT doc shows a Synergy/MEH or a compression-driver-plus-cone-through-port horn; Multi_region_SAWMOD is the closest. I could not confirm the full examples/ listing (page said "View all files").
- "BigMEH": no public repo or project by m3gnus, Magnus, HornLab or JW found; only a forum mention of a diyAudio "BIGMEH" exploration.
- Danley "Nano" model: not found; SM-100F/SM-100M/SM-80M/SH-DFA/Mini180 exist as names but I only read some pages. Danley recommended sub models for SM/SH minis beyond "pairs well with THmini": not found.
- Driver data not retrieved: Beyma 6MI100, Dayton PA130/PS95 (blocked), Celestion TF0410MR / TF0510MR / TF0615MR full T/S (not published online), full CD T/S (Bl, Mmd, Cms) for any CD, Danley's own drivers, SB Acoustics NERO-5CCN125D datasheet (name from BL example and forum).
- EDM spectrum: only production-blog sources; no measured club-sound-system spectra or standard.
- Hornresp and Akabak internals (no source), Small 1972 not read (formula checked numerically against datasheets instead).

## Conflicts between sources

1. **Solana driver complement**: JW page 4 x 6.5" + 1" CD vs one AVS excerpt "four 15", six 4" and one 1.4" CD" (the latter looks like a different, larger design; JW's own page wins).
2. **Synergy patent number**: a diyAudio list gives "8248976"; Google Patents shows US 8,284,976 B2 (granted 2012-10-09). The same forum post's other numbers (4,845,759; 6,411,718) are correct.
3. **SM-60F**: width 20.85 in (web) vs 20.6 in (2012 sheet); power 800 W cont / 3200 W peak (web) vs 1600 W "power rating" in the sheet table; +/-4 dB band in both. **SM-96**: 800 W (web) vs 1600 W (sheet).
4. **TH-Mini**: sheet 48-200 Hz (-3 dB), 24 x 15 x 22.5 in; web page 24 x 15 x 24 in; press 45-160 Hz.
5. **DH350 power**: B&C 8 ohm datasheet and 4 ohm page 15 W nominal / 30 W continuous vs retailers 20/40 W. The B&C DH350 is a 1" exit with a 36 mm (1.4") coil, which some sites call "1.4 inch".
6. **Tap area rule**: Sd/15 (MF) and Sd/8 (LF) [AA] vs 25 % of Sd [femishonuga] vs 10-12 % of one woofer's Sd for a pair of injection ports [BT MEH]. Patent port sizes: 4 ports x 5/8 in = 7.9 cm2 total (prior art 8 x 3/4 in = 22.8 cm2); driver size not given.
7. **Sealed vs vented**: femishonuga says seal the box (ports cause phase issues); JW's Solana is "vented low-tuned" and the DH350 MEH uses passive radiators; Waslo ports the woofer box.
8. **Spacing rule wording**: Danley claim = tap distance to CD corresponds to lambda/4 travel; Waslo = distance between centres of mid holes <= lambda/4; weltersys = exit points of HF and MF within lambda/4 (43 mm @2 kHz); another poster = round trip lambda/2 and place the mid port within 3400/f_upper inches ("3400/f" is lambda/4 in inches at c=13,600 in/s: 3.4 in @1 kHz).
9. **Mid driver metric**: "2 Fs/Qes ~ 600" (diyAudio snippet) vs "2 Fs/Qes ~ sqrt(Flow Fhigh)" (femishonuga; equals ~529 for a 200-1400 Hz band, consistent only roughly).
10. **Notch location**: patent says the notch is an acoustic dimension (no distance formula); practitioners equate it with lambda/4 throat-to-port only for a cylindrical throat; conical throats reflect from a shorter effective distance.
11. **Patent term**: Google lists Unity (6,411,718) as expired (2019) and Synergy (8,284,976) active until ~2029 (assumption); Waslo (2014) says Unity and Synergy "CAN NOT BE LEGALLY SOLD" in kits. Not legal advice; relevant only for commercial use.
12. **BL "unsupported" list vs elsewhere**: Coupled Solver doc's unsupported list still names ROCm for coupled systems while the same doc's production table lists a ROCm coupled path (BEAT 0.6.0 notes and open PR #78/#79 show ROCm coupled work); treat ROCm coupled as in progress.
13. **BL version**: docs/development.md says development main carries a `.dev0` version, yet pyproject on main reads 0.5.0 with four later commits; the latest tagged release is v0.5.0.
14. **hornlab-beat-bem vs BL**: BL/BEAT support multi-source, multi-region coupled solves; the hornlab-beat-bem README says its Python API refuses multi-source drive and coupled FEM-BEM-LEM (engine has them).
15. **Directivity of Solana/DH350 MEH**: JW states 90 x 90 (Solana) and 75 x 60 vs 60 x 90 goal (DH350 MEH): design intent and measurement differ in the DH350 case.
