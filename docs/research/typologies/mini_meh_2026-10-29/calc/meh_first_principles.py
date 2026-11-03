"""First-principles numbers for a mini multiple-entry horn (research sketch, not wired).

Prints markdown tables:
  1. displacement-limited SPL vs frequency for cone complements (the bass ceiling)
  2. Hofmann's iron law: reference efficiency / sensitivity vs box volume and f3
  3. Keele K-law: mouth size needed to hold a pattern, and the pattern-control floor of small mouths
  4. quarter-wavelength entry distance vs the entry's upper crossover
  5. front chamber + port (Helmholtz) acoustic low-pass corner
  6. conical (flat-wall) horn geometry: wall size at the entry, mouth size vs depth

Constants match hornlab_search/constants.py (C_AIR 343, RHO_AIR 1.204, KEELE_K 25400).
"""
import math

C = 343.0
RHO = 1.204
KEELE_K = 25400.0
P_REF = 20e-6


def db(p_rms):
    return 20 * math.log10(p_rms / P_REF)


def spl_displacement(sd_cm2_total, xmax_mm, f, q=2.0, r=1.0):
    """Peak-excursion-limited SPL (rms) at r for a compact source: p = rho w^2 Vd Q / (4 pi r)."""
    vd = sd_cm2_total * 1e-4 * xmax_mm * 1e-3
    w = 2 * math.pi * f
    p_pk = RHO * w * w * vd * q / (4 * math.pi * r)
    return db(p_pk / math.sqrt(2))


def table1():
    # class-typical cone values [inferred, not specific products]: Sd cm^2 each, Xmax mm (one way)
    sets = [
        ("4 x 4-inch mid", 4, 55, 3.0),
        ("2 x 6.5-inch mid", 2, 135, 4.0),
        ("2 x 6.5-inch midbass", 2, 135, 6.0),
        ("2 x 8-inch woofer", 2, 220, 6.0),
        ("2 x 10-inch woofer", 2, 350, 7.0),
        ("1 x 12-inch woofer", 1, 530, 7.0),
        ("1 x 15-inch woofer", 1, 880, 8.0),
        ("1 x 18-inch sub", 1, 1200, 10.0),
        ("2 x 18-inch sub", 2, 1200, 10.0),
    ]
    freqs = [40, 50, 63, 80, 100, 125, 160, 200]
    print("### 1. Excursion-limited SPL, dB at 1 m, half space (2 pi), sealed-equivalent\n")
    print("| Complement | Vd (cm^3) | " + " | ".join(f"{f} Hz" for f in freqs) + " |")
    print("|---|---|" + "---|" * len(freqs))
    for name, n, sd, xm in sets:
        vd = n * sd * xm / 10.0
        row = [f"{spl_displacement(n * sd, xm, f):.0f}" for f in freqs]
        print(f"| {name} | {vd:.0f} | " + " | ".join(row) + " |")
    # volume displacement needed for a target
    print("\nVd needed (cm^3) for a target SPL at 1 m half space:\n")
    targets = [105, 110, 115, 120, 125]
    print("| f | " + " | ".join(f"{t} dB" for t in targets) + " |")
    print("|---|" + "---|" * len(targets))
    for f in [40, 50, 63]:
        cells = []
        for t in targets:
            p_pk = P_REF * 10 ** (t / 20) * math.sqrt(2)
            w = 2 * math.pi * f
            vd = p_pk * 4 * math.pi / (RHO * w * w * 2.0)
            cells.append(f"{vd * 1e6:.0f}")
        print(f"| {f} Hz | " + " | ".join(cells) + " |")
    print()


def table2():
    # Small's relations: eta0 = (4 pi^2 / c^3) fs^3 Vas / Qes.
    # B4 vented (alpha = 1, fs = f3, Qts = 0.383 ~ Qes): k = 9.78e-7 / 0.383
    # sealed Qtc 0.707 with alpha -> large: k -> 9.78e-7 / 0.707 (alpha = 3 gives 0.75 of that)
    base = 4 * math.pi ** 2 / C ** 3
    k_vented = base / 0.383
    k_sealed = base * 3 / (0.707 * 4)  # alpha = 3
    print("### 2. Iron law: half-space sensitivity (dB 1 W 1 m) vs box volume and f3\n")
    print(f"k (vented B4) = {k_vented:.3g}, k (sealed Qtc 0.707, alpha 3) = {k_sealed:.3g}; "
          "SPL_1W = 112.1 + 10 log10(eta0) (half space)\n")
    vols = [10, 20, 30, 50, 80]
    f3s = [40, 50, 60, 80, 100]
    for label, k in (("vented B4", k_vented), ("sealed", k_sealed)):
        print(f"**{label}**\n")
        print("| f3 | " + " | ".join(f"{v} L" for v in vols) + " |")
        print("|---|" + "---|" * len(vols))
        for f3 in f3s:
            cells = []
            for v in vols:
                eta = k * f3 ** 3 * v / 1000.0
                cells.append(f"{112.1 + 10 * math.log10(eta):.1f}")
            print(f"| {f3} Hz | " + " | ".join(cells) + " |")
        print()


def table3():
    print("### 3. K-law: mouth dimension (mm) to hold a coverage angle down to f\n")
    angles = [40, 60, 75, 90, 105]
    freqs = [250, 300, 400, 500, 700, 1000]
    print("| f | " + " | ".join(f"{a} deg" for a in angles) + " |")
    print("|---|" + "---|" * len(angles))
    for f in freqs:
        print(f"| {f} Hz | " + " | ".join(f"{KEELE_K / (a * f) * 1000:.0f}" for a in angles) + " |")
    print("\nPattern-control floor (Hz) of a given mouth dimension:\n")
    mouths = [200, 250, 300, 350, 400, 500]
    print("| mouth | " + " | ".join(f"{a} deg" for a in angles) + " |")
    print("|---|" + "---|" * len(angles))
    for m in mouths:
        print(f"| {m} mm | " + " | ".join(f"{KEELE_K / (a * m / 1000):.0f}" for a in angles) + " |")
    print("\nMouth-loading rough floor (circumference = wavelength, f = c / (pi D_eq)):\n")
    print("| mouth W x H (mm) | D_eq (mm) | f (Hz) |")
    print("|---|---|---|")
    for w, h in [(250, 180), (300, 200), (350, 230), (400, 250), (500, 290), (700, 400)]:
        d = 2 * math.sqrt(w * h / math.pi)
        print(f"| {w} x {h} | {d:.0f} | {C / (math.pi * d / 1000):.0f} |")
    print()


def table4():
    print("### 4. Quarter-wavelength entry rule: max path from the acoustic apex, d = c / (4 f)\n")
    print("| entry upper crossover | d_max (mm) | eighth-wave (mm) |")
    print("|---|---|---|")
    for f in [4000, 3000, 2000, 1500, 1200, 1000, 800, 600, 400, 300, 200, 150]:
        print(f"| {f} Hz | {C / (4 * f) * 1000:.0f} | {C / (8 * f) * 1000:.0f} |")
    print()


def helmholtz(v_cm3, s_cm2, l_mm, flanged_ends=2):
    s = s_cm2 * 1e-4
    r = math.sqrt(s / math.pi)
    l_eff = l_mm / 1000 + flanged_ends * 0.85 * r
    v = v_cm3 * 1e-6
    return C / (2 * math.pi) * math.sqrt(s / (v * l_eff)), l_eff


def table5():
    print("### 5. Front chamber + port corner, f = c/(2 pi) sqrt(S / (V L_eff)), L_eff = L + 2 x 0.85 r\n")
    print("Port neck length 12 mm (horn wall + spacer). Rows: front chamber volume; columns: port area.\n")
    areas = [5, 10, 15, 20, 30, 45]
    vols = [10, 20, 40, 60, 100, 160, 250]
    print("| V_front | " + " | ".join(f"{a} cm^2" for a in areas) + " |")
    print("|---|" + "---|" * len(areas))
    for v in vols:
        print(f"| {v} cm^3 | " + " | ".join(f"{helmholtz(v, a, 12)[0]:.0f}" for a in areas) + " |")
    print("\nCompression ratio Sd/S_port for reference: 4-inch (55 cm^2) / 10 cm^2 = 5.5; "
          "6.5-inch (135 cm^2) / 20 cm^2 = 6.8.\n")


def table6():
    print("### 6. Flat-wall conical horn (apex at origin): sizes vs axial distance z\n")
    print("| coverage (deg) | z (mm) | wall width W x H at z (mm) | throat z for 1-inch exit (mm) |")
    print("|---|---|---|---|")
    for ch, cv in [(90, 60), (90, 90), (80, 50), (60, 40)]:
        th, tv = math.tan(math.radians(ch / 2)), math.tan(math.radians(cv / 2))
        omega = 4 * th * tv
        z_t = math.sqrt(5.07e-4 / omega) * 1000
        for z in [50, 75, 100, 150, 200, 250, 300]:
            print(f"| {ch}x{cv} | {z} | {2 * z * th:.0f} x {2 * z * tv:.0f} | {z_t:.1f} |")
    print()


if __name__ == "__main__":
    table1()
    table2()
    table3()
    table4()
    table5()
    table6()
