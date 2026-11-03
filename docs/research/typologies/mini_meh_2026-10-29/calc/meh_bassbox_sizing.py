"""Bass box sizing sketch for the owner's split (MEH top from ~120 Hz; separate bass box 30-120 Hz flat).

Excursion-limited SPL (sine, 1 m, half space, before room/corner gain) for class-typical woofers, and the iron-law
sensitivity of an ideal vented B4 box with f3 = 30 Hz. Class values [inferred]; real drivers via M10.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meh_first_principles import spl_displacement  # noqa: E402

C = 343.0
sets = [("1 x 12-inch long-throw (Sd 530, Xmax 9)", 1, 530, 9.0),
        ("1 x 15-inch long-throw (Sd 880, Xmax 9)", 1, 880, 9.0),
        ("1 x 15-inch high-excursion (Sd 880, Xmax 13)", 1, 880, 13.0),
        ("1 x 18-inch (Sd 1200, Xmax 10)", 1, 1200, 10.0),
        ("2 x 12-inch long-throw (Sd 530, Xmax 9)", 2, 530, 9.0)]
print("| woofer | Vd (cm^3) | 30 Hz | 40 Hz | 50 Hz | 63 Hz | 80 Hz | 120 Hz |")
print("|---|---|---|---|---|---|---|---|")
for name, n, sd, xm in sets:
    print(f"| {name} | {n*sd*xm/10:.0f} | " + " | ".join(f"{spl_displacement(n*sd, xm, f):.0f}" for f in (30, 40, 50, 63, 80, 120)) + " |")
k = 4 * math.pi ** 2 / C ** 3 / 0.383
print("\nIdeal vented B4, f3 = 30 Hz: half-space sensitivity at 1 W (dB):",
      ", ".join(f"{v} L {112.1 + 10*math.log10(k*30**3*v/1000):.1f}" for v in (60, 90, 120, 150, 200)))
