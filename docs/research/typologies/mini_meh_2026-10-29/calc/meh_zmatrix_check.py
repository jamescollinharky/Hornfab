"""Check (research only): the L1 decomposition of dossier s10.1 is exact for lumped entries.

Direct: solve the 1-D horn with the entry's Norton network attached (meh_1d_sketch.solve).
Decomposed: solve the BARE horn once per source with a unit volume-velocity injection (the BEM analogue: one
channel per tag, other tags rigid), record the pressure at every source node (Z matrix) and the mouth volume
velocity (transfer H); then couple the network afterwards: U_e = (I + Y Z_ee)^-1 (U_sc - Y Z_et U_cd),
U_mouth = H_t U_cd + H_e . U_e. Both must agree to round-off.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meh_1d_sketch import MID4, MID65, Entry, Horn, seg_T, solve, z_mouth  # noqa: E402


def bare_injection(horn: Horn, nodes_z, j, f):
    """Bare horn, unit volume velocity injected at node j (throat = node 0, rigid when undriven).
    Returns (pressures at every node, mouth volume velocity)."""
    xs = sorted(nodes_z)
    om = horn.omega
    zm = z_mouth(f, horn.s_mouth)
    a = np.array([zm, 1.0], dtype=complex)
    b = np.zeros(2, dtype=complex)
    pts = [horn.z_throat] + xs + [horn.depth]
    states = {}
    for idx in range(len(pts) - 1, 0, -1):
        x2 = pts[idx]
        if 1 <= idx <= len(xs):
            k = idx - 1
            states[k] = (a.copy(), b.copy())
            if k + 1 == j:            # injection U into the horn: U_upstream = U_downstream - U_inj
                b = b - np.array([0.0, 1.0])
        T = seg_T(pts[idx - 1], x2, f, om)
        a, b = T @ a, T @ b
    u_throat = 1.0 if j == 0 else 0.0
    u_n = (u_throat - b[1]) / a[1]
    p = [a[0] * u_n + b[0]] + [(states[k][0] * u_n + states[k][1])[0] for k in range(len(xs))]
    return np.array(p), u_n


def check(horn, entries, freqs, e_volts=2.83, u_cd=1e-4):
    zs = [e.z for e in entries]
    order = np.argsort(zs)
    entries = [entries[i] for i in order]
    zs = [e.z for e in entries]
    worst = 0.0
    for f in freqs:
        n = len(entries) + 1
        Z = np.zeros((n, n), dtype=complex)
        H = np.zeros(n, dtype=complex)
        for j in range(n):
            Z[:, j], H[j] = bare_injection(horn, zs, j, f)
        u_sc = np.array([e.norton(f, e_volts)[0] for e in entries])
        Y = np.diag([e.norton(f, e_volts)[1] for e in entries])
        z_ee, z_et = Z[1:, 1:], Z[1:, 0]
        u_e = np.linalg.solve(np.eye(len(entries)) + Y @ z_ee, u_sc - Y @ z_et * u_cd)
        u_dec = H[0] * u_cd + H[1:] @ u_e
        u_dir, _, _ = solve(horn, entries, f, u_cd, [e_volts] * len(entries))
        worst = max(worst, abs(u_dec / u_dir - 1))
        # reciprocity of the bare-horn impedance matrix (volume-velocity / pressure pairs)
        worst_recip = np.max(np.abs(Z - Z.T)) / np.max(np.abs(Z))
        worst = max(worst, worst_recip)
    return worst


if __name__ == "__main__":
    horn = Horn(90, 60, depth=0.22)
    a4 = Entry(MID4, n=4, z=0.065, v_front=30e-6, s_port=12e-4, l_port=0.012, v_rear=1.0e-3)
    w = Entry(MID65, n=2, z=0.15, v_front=120e-6, s_port=25e-4, l_port=0.012, v_rear=4.0e-3)
    freqs = np.geomspace(100, 8000, 25)
    print(f"one entry group: max rel diff direct vs decomposed (and Z reciprocity) = {check(horn, [a4], freqs):.2e}")
    print(f"two entry groups: max rel diff direct vs decomposed (and Z reciprocity) = {check(horn, [a4, w], freqs):.2e}")
