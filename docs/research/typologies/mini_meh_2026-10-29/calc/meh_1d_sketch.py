"""1-D multiple-entry horn sketch (research only; NOT wired into hornlab_search).

Model [inferred, textbook lumped + spherical-wave duct]:
  * horn = flat-wall conical (pyramid) duct, area S(x) = Omega x^2 (x from the apex), exact spherical-wave
    transfer matrices between nodes (the only mode a 1-D model keeps);
  * compression driver = ideal volume-velocity source at the throat node (rigid for reflected waves);
  * each entry = N identical cone drivers at one axial station, each: Thevenin pressure Bl e / (Ze Sd)
    behind Z_cone = (Rms + j w Mms + 1/(j w Cms) + Bl^2/Ze)/Sd^2 + rear box 1/(j w Cb), into a front chamber
    (shunt Cf = Vf/(rho c^2)), out through a port neck (mass rho L_eff / Sp, small loss) into the horn wall;
  * mouth = baffled circular piston of the mouth area (Struve impedance); on-axis far field
    p = j w rho U_mouth / (2 pi r), half space.
Valid [inferred]: below the first cross-mode of the duct at each entry, and while ports are small vs
wavelength. It ignores where the port sits around the wall, port-excited higher-order modes, mouth
directivity and the spherical-cap mouth phase. Those are exactly what the BEM stage is for.

Units SI; e^{+j w t}. Drivers are CLASS-TYPICAL ILLUSTRATIONS, not real products.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, replace

import numpy as np
from scipy.special import j1, struve

C = 343.0
RHO = 1.204
Z0 = RHO * C


@dataclass(frozen=True)
class Cone:
    name: str
    re: float      # ohm
    le: float      # H
    bl: float      # T m
    mms: float     # kg
    fs: float      # Hz
    qms: float
    sd: float      # m^2
    xmax: float    # m

    @property
    def cms(self):
        return 1.0 / ((2 * math.pi * self.fs) ** 2 * self.mms)

    @property
    def rms(self):
        return 2 * math.pi * self.fs * self.mms / self.qms

    @property
    def qes(self):
        return 2 * math.pi * self.fs * self.mms * self.re / self.bl ** 2

    @property
    def vas_l(self):
        return Z0 * C * self.sd ** 2 * self.cms * 1000


# class-typical illustrations [inferred]
MID4 = Cone("4-inch pro mid (illustrative)", re=6.0, le=0.10e-3, bl=5.5, mms=4.0e-3, fs=120.0, qms=4.0,
            sd=55e-4, xmax=3e-3)
MID65 = Cone("6.5-inch pro mid (illustrative)", re=5.5, le=0.20e-3, bl=9.0, mms=14e-3, fs=80.0, qms=5.0,
             sd=135e-4, xmax=4e-3)


@dataclass(frozen=True)
class Entry:
    cone: Cone
    n: int            # identical drivers at this station
    z: float          # axial distance from apex, m
    v_front: float    # m^3 per driver
    s_port: float     # m^2 per driver
    l_port: float     # m neck length per driver
    v_rear: float     # m^3 per driver (sealed)
    q_port: float = 10.0

    def norton(self, f, e_volts):
        """(U_sc, Y) for the whole station at the horn wall node; e_volts complex per driver."""
        w = 2 * np.pi * f
        c = self.cone
        ze = c.re + 1j * w * c.le
        zm = c.rms + 1j * w * c.mms + 1.0 / (1j * w * c.cms) + c.bl ** 2 / ze
        z_cone = zm / c.sd ** 2 + 1.0 / (1j * w * self.v_rear / (Z0 * C))
        p_s = c.bl * e_volts / (ze * c.sd)
        z_cf = 1.0 / (1j * w * self.v_front / (Z0 * C))
        r = math.sqrt(self.s_port / math.pi)
        l_eff = self.l_port + 2 * 0.85 * r
        x_port = w * RHO * l_eff / self.s_port
        z_port = 1j * x_port + x_port / self.q_port
        z_par = z_cf * z_cone / (z_cf + z_cone)
        p_th = p_s * z_cf / (z_cf + z_cone)
        z_th = z_port + z_par
        return self.n * p_th / z_th, self.n / z_th

    def cone_velocity(self, f, e_volts, p_horn):
        """Cone velocity (m/s) per driver given the horn pressure at the port."""
        w = 2 * np.pi * f
        c = self.cone
        ze = c.re + 1j * w * c.le
        zm = c.rms + 1j * w * c.mms + 1.0 / (1j * w * c.cms) + c.bl ** 2 / ze
        z_cone = zm / c.sd ** 2 + 1.0 / (1j * w * self.v_rear / (Z0 * C))
        p_s = c.bl * e_volts / (ze * c.sd)
        u_sc, y = self.norton(f, e_volts)
        u_out = (u_sc - p_horn * y) / self.n
        z_cf = 1.0 / (1j * w * self.v_front / (Z0 * C))
        r = math.sqrt(self.s_port / math.pi)
        l_eff = self.l_port + 2 * 0.85 * r
        x_port = w * RHO * l_eff / self.s_port
        z_port = 1j * x_port + x_port / self.q_port
        p_c = p_horn + u_out * z_port
        u_d = (p_s - p_c) / z_cone
        return u_d / c.sd


@dataclass(frozen=True)
class Horn:
    cov_h: float      # deg full angle
    cov_v: float
    depth: float      # apex-to-mouth axial length, m
    s_throat: float = 5.07e-4   # 1-inch exit
    cd_passage: float = 0.0     # m, CD internal duct (exit bore to diaphragm) behind the throat; 0 = rigid throat

    @property
    def omega(self):
        return 4 * math.tan(math.radians(self.cov_h / 2)) * math.tan(math.radians(self.cov_v / 2))

    @property
    def z_throat(self):
        return math.sqrt(self.s_throat / self.omega)

    @property
    def s_mouth(self):
        return self.omega * self.depth ** 2

    def mouth_wh(self):
        return (2 * self.depth * math.tan(math.radians(self.cov_h / 2)),
                2 * self.depth * math.tan(math.radians(self.cov_v / 2)))


def _M(x, k, w, om):
    s = om * x * x
    em, ep = np.exp(-1j * k * x), np.exp(1j * k * x)
    return np.array([[em / x, ep / x],
                     [s / (1j * w * RHO) * em * (1j * k / x + 1 / x ** 2),
                      -s / (1j * w * RHO) * ep * (1j * k / x - 1 / x ** 2)]])


def seg_T(x1, x2, f, om):
    """Maps [p, U] at x2 to [p, U] at x1 (U positive toward the mouth)."""
    w = 2 * np.pi * f
    k = w / C
    return _M(x1, k, w, om) @ np.linalg.inv(_M(x2, k, w, om))


def z_mouth(f, s):
    a = math.sqrt(s / math.pi)
    ka = 2 * np.pi * f / C * a
    return Z0 / s * (1 - j1(2 * ka) / ka + 1j * struve(1, 2 * ka) / ka)


def solve(horn: Horn, entries: list[Entry], f, u_cd, e_entries):
    """Mouth volume velocity and per-node pressures for one frequency.
    u_cd: complex CD throat volume velocity; e_entries: complex drive volts per entry."""
    nodes = sorted([(horn.z_throat, "throat", None)] + [(e.z, "entry", i) for i, e in enumerate(entries)]
                   + [(horn.depth, "mouth", None)], key=lambda t: t[0])
    om = horn.omega
    zm = z_mouth(f, horn.s_mouth)
    a = np.array([zm, 1.0], dtype=complex)   # state = a * U_N + b
    b = np.zeros(2, dtype=complex)
    states = {}
    for idx in range(len(nodes) - 1, 0, -1):
        x2, kind2, i2 = nodes[idx]
        if kind2 == "entry":
            e = entries[i2]
            u_sc, y = e.norton(f, e_entries[i2])
            states[("entry", i2)] = (a.copy(), b.copy())
            a = np.array([a[0], a[1] + y * a[0]])
            b = np.array([b[0], b[1] + y * b[0] - u_sc])
        x1 = nodes[idx - 1][0]
        T = seg_T(x1, x2, f, om)
        a, b = T @ a, T @ b
    if horn.cd_passage > 0:
        # cylindrical CD exit duct of the throat area between the throat plane and the diaphragm
        k = 2 * np.pi * f / C
        zc = Z0 / horn.s_throat
        kl = k * horn.cd_passage
        Tc = np.array([[np.cos(kl), 1j * zc * np.sin(kl)], [1j * np.sin(kl) / zc, np.cos(kl)]])
        a, b = Tc @ a, Tc @ b
    u_n = (u_cd - b[1]) / a[1]
    p_entries = {i: (st[0] * u_n + st[1])[0] for (kind, i), st in states.items()}
    p_throat = a[0] * u_n + b[0]
    return u_n, p_throat, p_entries


def onaxis_db(f, u_n, r=1.0):
    p = 1j * 2 * np.pi * f * RHO * u_n / (2 * np.pi * r)
    return 20 * np.log10(np.abs(p) / np.sqrt(2) / 20e-6 + 1e-30)


def lr4(f, fx, kind):
    s = 1j * f / fx
    bw2 = 1 / (s * s + math.sqrt(2) * s + 1)
    return (bw2 * bw2) if kind == "lp" else (bw2 * s * s) ** 2


def check_conical_impedance():
    """Infinite conical horn: p/U = (rho c / S) j k x / (1 + j k x). Uses a long matched duct."""
    horn = Horn(90, 60, depth=60.0)
    errs = []
    for f in [200.0, 1000.0, 5000.0]:
        k = 2 * np.pi * f / C
        x = horn.z_throat
        s = horn.omega * x * x
        T = seg_T(x, horn.depth, f, horn.omega)
        # terminate the far end with its own outgoing-wave impedance (matched)
        xl = horn.depth
        zl = Z0 / (horn.omega * xl * xl) * 1j * k * xl / (1 + 1j * k * xl)
        st = T @ np.array([zl, 1.0])
        z_num = st[0] / st[1]
        z_an = Z0 / s * 1j * k * x / (1 + 1j * k * x)
        errs.append(abs(z_num / z_an - 1))
    return max(errs)


if __name__ == "__main__":
    print("check: conical-horn throat impedance vs analytic, max rel err", f"{check_conical_impedance():.2e}")
    sys.exit(0)
