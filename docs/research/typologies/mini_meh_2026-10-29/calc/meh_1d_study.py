"""Studies on the 1-D MEH sketch (research only). Prints markdown, writes PNGs next to this file."""
from __future__ import annotations

import math
import os
import sys
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meh_1d_sketch import MID4, MID65, Entry, Horn, lr4, onaxis_db, solve  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
F = np.geomspace(100, 10000, 400)

HORN = Horn(90, 60, depth=0.22)          # mouth 440 x 254 mm
A4 = Entry(MID4, n=4, z=0.065, v_front=30e-6, s_port=12e-4, l_port=0.012, v_rear=1.0e-3)
B65 = Entry(MID65, n=2, z=0.090, v_front=120e-6, s_port=25e-4, l_port=0.012, v_rear=4.0e-3)
CASES = {"A: CD + 4 x 4-inch": (A4, 1500.0), "B: CD + 2 x 6.5-inch": (B65, 900.0)}


CD_FS, CD_Q = 700.0, 1.0   # illustrative 1-inch CD resonance on its rear chamber [inferred]


def cd_u(fi, a=1.0):
    """CD throat volume velocity: mass-controlled above fs (flat acceleration, as the BEM drives it),
    2nd-order high-pass at the driver's own resonance."""
    s = 1j * fi / CD_FS
    hp2 = s * s / (s * s + s / CD_Q + 1)
    return a * 5.07e-4 / (1j * 2 * np.pi * fi) * hp2


def responses(horn, entry, fx, delay_s=0.0, pol=1.0, cd_gain=1.0, f=F, passive=True):
    """dB on axis: (cd_alone_with_passive_entry, cd_alone_no_entry, mid_alone, sum) and the complex sum."""
    out = {k: [] for k in ("cd_pass", "cd_bare", "mid", "sum")}
    c_sum = []
    for fi in f:
        u_cd = cd_gain * cd_u(fi) * lr4(fi, fx, "hp")
        e = 2.83 * lr4(fi, fx, "lp") * pol * np.exp(-1j * 2 * np.pi * fi * delay_s)
        u_cd_only, _, _ = solve(horn, [entry], fi, u_cd, [0.0])
        u_bare, _, _ = solve(horn, [], fi, u_cd, [])
        u_mid, _, _ = solve(horn, [entry], fi, 0.0, [e])
        out["cd_pass"].append(u_cd_only)
        out["cd_bare"].append(u_bare)
        out["mid"].append(u_mid)
        out["sum"].append(u_cd_only + u_mid)
    return {k: onaxis_db(f, np.array(v)) for k, v in out.items()}, np.array(out["sum"])


def unfiltered(horn, entry, f=F):
    """Full-range CD (flat U) with the passive entry and without; mids full range at 2.83 V."""
    cd_p, cd_b, mid = [], [], []
    for fi in f:
        cd_p.append(solve(horn, [entry], fi, cd_u(fi), [0.0])[0])
        cd_b.append(solve(horn, [], fi, cd_u(fi), [])[0])
        mid.append(solve(horn, [entry], fi, 0.0, [2.83])[0])
    return onaxis_db(f, np.array(cd_p)), onaxis_db(f, np.array(cd_b)), onaxis_db(f, np.array(mid))


def band(f, lo, hi):
    return (f >= lo) & (f <= hi)


def match_gain(horn, entry, fx):
    cd_p, cd_b, mid = unfiltered(horn, entry)
    lvl_mid = np.mean(mid[band(F, fx / 4, fx / 2)])
    lvl_cd = np.mean(cd_b[band(F, 2 * fx, 4 * fx)])
    return 10 ** ((lvl_mid - lvl_cd) / 20)


def best_alignment(horn, entry, fx, gain):
    best = None
    for pol in (1.0, -1.0):
        for d_ms in np.arange(-0.4, 1.21, 0.02):
            r, _ = responses(horn, entry, fx, delay_s=d_ms / 1000, pol=pol, cd_gain=gain,
                             f=np.geomspace(fx / 2, 2 * fx, 60))
            s = r["sum"]
            # flatness of the sum through the crossover octave pair, relative to the matched level
            ref = np.mean(s)
            rip = float(np.sqrt(np.mean((s - ref) ** 2)))
            if best is None or rip < best[0]:
                best = (rip, pol, d_ms, ref)
    return best


def notch(horn, entry, lo=300, hi=10000):
    """Deepest dip of (CD with passive entry) minus (bare CD), and its frequency."""
    f = np.geomspace(lo, hi, 500)
    cd_p, cd_b = [], []
    for fi in f:
        cd_p.append(solve(horn, [entry], fi, cd_u(fi), [0.0])[0])
        cd_b.append(solve(horn, [], fi, cd_u(fi), [])[0])
    d = onaxis_db(f, np.array(cd_p)) - onaxis_db(f, np.array(cd_b))
    i = int(np.argmin(d))
    return f[i], d[i]


def helm(e):
    r = math.sqrt(e.s_port / math.pi)
    l_eff = e.l_port + 2 * 0.85 * r
    return 343.0 / (2 * math.pi) * math.sqrt(e.s_port / (e.v_front * l_eff))


def excursion(horn, entry, fx, gain, volts, freqs):
    out = []
    for fi in freqs:
        e = volts * lr4(fi, fx, "lp")
        _, _, p_e = solve(horn, [entry], fi, gain * cd_u(fi) * lr4(fi, fx, "hp"), [e])
        v = entry.cone_velocity(fi, e, p_e[0])
        out.append(abs(v) * math.sqrt(2) / (2 * math.pi * fi) * 1000)  # peak mm
    return out


def main():
    w, h = HORN.mouth_wh()
    print(f"Horn: {HORN.cov_h:.0f} x {HORN.cov_v:.0f} deg flat-wall conical, depth {HORN.depth*1000:.0f} mm "
          f"from apex, mouth {w*1000:.0f} x {h*1000:.0f} mm, throat z {HORN.z_throat*1000:.1f} mm (1-inch).\n")
    plots = {}
    print("### Baseline cases\n")
    print("| case | entry z (mm) | path from throat (mm) | quarter-wave limit at fx (mm) | port corner f_h (Hz) | "
          "LR4 fx (Hz) | best polarity | best mid delay (ms) | ripple through XO (dB rms) | CD notch (Hz, dB) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name, (e, fx) in CASES.items():
        g = match_gain(HORN, e, fx)
        rip, pol, d_ms, ref = best_alignment(HORN, e, fx, g)
        fn, dn = notch(HORN, e)
        print(f"| {name} | {e.z*1000:.0f} | {(e.z-HORN.z_throat)*1000:.0f} | {343/(4*fx)*1000:.0f} | "
              f"{helm(e):.0f} | {fx:.0f} | {'+' if pol > 0 else '-'} | {d_ms:.2f} | {rip:.2f} | "
              f"{fn:.0f}, {dn:.1f} |")
        r, _ = responses(HORN, e, fx, delay_s=d_ms / 1000, pol=pol, cd_gain=g)
        cd_p, cd_b, mid = unfiltered(HORN, e)
        plots[name] = (r, cd_p + 20 * np.log10(g), cd_b + 20 * np.log10(g), mid, fx, pol, d_ms)
    print()

    print("### Sweep: entry position z (case A, 4 x 4-inch, LR4 1.5 kHz)\n")
    print("| z (mm) | path from throat (mm) | ripple through XO (dB rms) | best delay (ms) | pol | CD notch (Hz, dB) |")
    print("|---|---|---|---|---|---|")
    for z in [0.035, 0.05, 0.065, 0.085, 0.11, 0.14, 0.18]:
        e = replace(A4, z=z)
        g = match_gain(HORN, e, 1500.0)
        rip, pol, d_ms, _ = best_alignment(HORN, e, 1500.0, g)
        fn, dn = notch(HORN, e)
        print(f"| {z*1000:.0f} | {(z-HORN.z_throat)*1000:.0f} | {rip:.2f} | {d_ms:.2f} | {'+' if pol>0 else '-'} | "
              f"{fn:.0f}, {dn:.1f} |")
    print()

    print("### Sweep: front chamber and port (case A geometry), CD notch vs port corner\n")
    print("| V_front (cm^3) | S_port (cm^2) | f_h (Hz) | CD notch f (Hz) | depth (dB) | ripple through XO (dB rms) |")
    print("|---|---|---|---|---|---|")
    for vf in [15e-6, 30e-6, 60e-6]:
        for sp in [6e-4, 12e-4, 24e-4]:
            e = replace(A4, v_front=vf, s_port=sp)
            fn, dn = notch(HORN, e)
            g = match_gain(HORN, e, 1500.0)
            rip, *_ = best_alignment(HORN, e, 1500.0, g)
            print(f"| {vf*1e6:.0f} | {sp*1e4:.0f} | {helm(e):.0f} | {fn:.0f} | {dn:.1f} | {rip:.2f} |")
    print()

    print("### Cone excursion (peak mm) with the LR4 low-pass only (no high-pass), at 2.83 V and at 20 V\n")
    fq = [60, 80, 100, 150, 200, 300]
    print("| case | volts | " + " | ".join(f"{x} Hz" for x in fq) + " | Xmax |")
    print("|---|---|" + "---|" * len(fq) + "---|")
    for name, (e, fx) in CASES.items():
        g = match_gain(HORN, e, fx)
        for v in (2.83, 20.0):
            ex = excursion(HORN, e, fx, g, v, fq)
            print(f"| {name} | {v} | " + " | ".join(f"{x:.2f}" for x in ex) + f" | {e.cone.xmax*1000:.0f} |")
    print()

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, (name, (r, cd_p, cd_b, mid, fx, pol, d_ms)) in zip(axes, plots.items()):
        ax.semilogx(F, cd_b, color="#999999", lw=1, label="CD full range (level-matched), no ports")
        ax.semilogx(F, cd_p, color="#c0392b", lw=1, label="CD full range (level-matched), mid ports passive")
        ax.semilogx(F, mid, color="#2471a3", lw=1, ls=":", label="mids full range (2.83 V)")
        ax.semilogx(F, r["sum"], color="#111111", lw=2, label=f"sum, LR4 {fx:.0f} Hz, pol {'+' if pol>0 else '-'}, "
                    f"delay {d_ms:.2f} ms")
        ax.set_title(name)
        ax.set_xlabel("Hz")
        ax.grid(True, which="both", alpha=0.3)
        ax.set_xlim(100, 10000)
        ax.set_ylim(70, 130)
        ax.legend(fontsize=7, loc="lower center")
    axes[0].set_ylabel("dB on axis, 1 m, half space (1-D sketch)")
    fig.suptitle("1-D MEH sketch: 90x60 conical horn, 220 mm deep (mouth 440 x 254). Illustrative drivers.", fontsize=10)
    fig.tight_layout()
    out = os.path.join(HERE, "meh_1d_cases.png")
    fig.savefig(out, dpi=110)
    print(f"plot: {out}")


if __name__ == "__main__":
    main()
