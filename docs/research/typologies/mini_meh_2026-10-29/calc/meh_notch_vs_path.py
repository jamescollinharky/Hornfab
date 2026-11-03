"""Mid reflection notch vs entry path in a conical horn (research only, 1-D).

The Synergy patent (US 8,284,976 claim 1) caps each lower driver below its first cancellation notch: its own
sound runs back to the closed (throat) end, reflects and returns 180 deg out of phase. Practitioners estimate the
notch from the cylindrical-pipe rule f = c / (4 d); some report conical throats put it higher (shorter effective
length; web survey conflict 10). This script finds the first null of the mids-only response in the 1-D sketch and
compares it with c / (4 d) for d measured from the throat and from the apex.
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meh_1d_sketch import MID4, Entry, Horn, onaxis_db, solve  # noqa: E402

C = 343.0


def first_null(horn, entry, lo=300.0, hi=20000.0):
    f = np.geomspace(lo, hi, 1500)
    u = np.array([solve(horn, [entry], fi, 0.0, [2.83])[0] for fi in f])
    d = onaxis_db(f, u)
    # first local minimum at least 15 dB below the running max
    run_max = np.maximum.accumulate(d)
    for i in range(1, len(f) - 1):
        if d[i] < d[i - 1] and d[i] <= d[i + 1] and run_max[i] - d[i] > 15:
            return f[i]
    return float("nan")


if __name__ == "__main__":
    horn = Horn(90, 60, depth=0.22)
    a4 = Entry(MID4, n=4, z=0.065, v_front=30e-6, s_port=12e-4, l_port=0.012, v_rear=1.0e-3)
    print(f"Horn 90x60, 220 mm from apex, throat at z = {horn.z_throat*1000:.1f} mm (1-inch).\n")
    horn_cd = replace(horn, cd_passage=0.035)
    print("The null depends only on the horn (identical for both mid complements), so one table. "
          "Right-hand columns: the same horn with a 35 mm cylindrical CD exit duct behind the throat "
          "(diaphragm-side reflection) [illustrative length].\n")
    print("| z from apex (mm) | d from throat (mm) | first mid null, rigid throat (Hz) | c/(4 d) (Hz) | "
          "ratio | null with 35 mm CD duct (Hz) | c/(4 (d + 35 mm)) (Hz) | ratio |")
    print("|---|---|---|---|---|---|---|---|")
    for z in (0.035, 0.05, 0.065, 0.085, 0.11, 0.14):
        e = replace(a4, z=z)
        fn = first_null(horn, e)
        fc = first_null(horn_cd, e)
        d = z - horn.z_throat
        dc = d + 0.035
        print(f"| {z*1000:.0f} | {d*1000:.0f} | {fn:.0f} | {C/(4*d):.0f} | {fn/(C/(4*d)):.2f} | "
              f"{fc:.0f} | {C/(4*dc):.0f} | {fc/(C/(4*dc)):.2f} |")
