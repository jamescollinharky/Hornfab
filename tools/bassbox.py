"""Lumped sealed / vented bass-box model with DSP and limit-based maximum SPL (work package M10).

What it is
----------
A small-signal lumped model of one woofer (C8 ``kind: cone`` file) in a sealed or vented box,
plus the DSP block (infrasonic LR4 high-pass, Linkwitz transform, peaking EQ), the electrical input
impedance, the on-axis SPL at 2.83 V and at the limit, cone excursion, port air velocity, and the
maximum SPL per frequency from three limits: cone excursion = Xmax, voice-coil power = P_AES
(``V^2 / Re``), and port peak air velocity = 17 m/s (contract C11's practitioner limit).

Conventions and where the maths comes from
------------------------------------------
* ``exp(+j omega t)``, SI rms phasors, exactly like :mod:`hornlab_search.meh.network` (C6). The port
  branch is that module's C7 model: ``Z_port = x/Q_port + j x`` with ``x = omega rho L_eff / S_port``,
  ``L_eff = l_neck + n_end * 0.85 r_eq``, ``r_eq = sqrt(S_port/pi)``. ``n_end = 2`` here because a
  free-standing box radiates from both port mouths (the C7 default ``n_end = 1`` is for the MEH,
  where the horn-side radiation mass is already inside ``Z_net``). ``Q_port = 10``, leakage ``Ql = 7``.
* Box compliance ``C_ab = V_b / (rho c^2)``; leakage resistance ``R_al = Ql / (omega C_ab)``.
  The acoustic load on the cone is the box compliance in parallel with the leak and the port.
* The cone is driven by ``Bl e / (Ze Zm)``; front-side radiation resistance is **not** added to the
  mechanical load (standard T/S practice: it is ~1 % of ``Rms`` for these drivers and the published
  ``Mms`` already carries the air mass). The radiated pressure is the monopole sum of the cone and
  port volume velocities into half space: ``p = j omega rho (U_d + U_p) / (2 pi r)`` at 1 m.
  This is why the model's input power equals Joule + mechanical + port + leakage loss exactly
  (``energy_balance`` in the tests) while the acoustic output is reported separately.
* ``Mms`` (published, or ``Mmd + 2*(8/3) rho a^3``) is used as the moving mass; ``Cms`` and ``Rms``
  come from :class:`hornlab_search.meh.drivers.ConeDriver` (``Rms = omega_s Mms / Qms``).
* DSP blocks use :mod:`hornlab_search.meh.dsp` (``lr``, ``peaking``), so a complex drive can be
  multiplied straight into the network.

The three limits (C11)
----------------------
``x_peak <= Xmax`` uses the C7 ``cone_excursion_peak_mm`` (``sqrt(2)|v|/omega``, one-way peak);
``|e|^2 / Re <= P_AES``; ``sqrt(2)|U_port| / S_port <= 17 m/s``. The maximum SPL at a frequency is
``SPL(1 V) + 20 log10 e_lim(f)`` with ``e_lim`` the smallest of the three voltage ceilings, and
``limiting`` names which one binds. EQ does not change it (it changes the relative level per
frequency, not the driver ceiling), so a flat programme can be played up to
``min_f spl_max(f)`` over its band.

Design search
-------------
``design_vented`` / ``design_sealed`` sweep a deterministic grid (box volume relative to Vas, tuning,
slot-port height / Linkwitz-transform corner), keep only candidates that hit the owner targets
(>= 112 dB at 40 Hz and >= 118 dB at 63-120 Hz, 1 m half space, before room gain) and flatten the
30-120 Hz response with up to four PEQ bands; the smallest box that passes wins. ``design_best``
runs both families for one driver, ``recommend`` runs every short-listed driver and ranks them.

CLI
---
``python tools/bassbox.py --all`` prints the design table used by
``docs/research/typologies/mini_meh_2026-10-29/BASSBOX_2026-10-31.md`` (CPU only, no GPU, no
Julia, no solver).
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from hornlab_search.constants import C_AIR, REF_P, RHO_AIR
from hornlab_search.meh import dsp
from hornlab_search.meh.drivers import ConeDriver, load_cone
from hornlab_search.meh.network import cone_excursion_peak_mm, port_velocity_peak

__all__ = [
    "Box",
    "State",
    "box_compliance",
    "port_effective_length",
    "port_tuning_hz",
    "port_velocity_peak",
    "cone_excursion_peak_mm",
    "evaluate",
    "energy_balance",
    "linkwitz_transform",
    "dsp_response",
    "dsp_db",
    "fit_peq",
    "max_spl",
    "box_dimensions_mm",
    "design_vented",
    "design_sealed",
    "design_best",
    "recommend",
    "SHORTLIST",
]

#: The seven M10 woofer files (C13: new cone files live in examples/drivers).
SHORTLIST = (
    "bc_15tbx100",
    "bc_18tbw100",
    "bc_18sw115",
    "faitalpro_15xl1400",
    "faitalpro_18xl1800",
    "eighteensound_18nlw9601",
    "beyma_15lx60v2",
)

TARGET_40_DB = 112.0          # >= 112 dB at 40 Hz, sine, 1 m, half space, before room gain
TARGET_BAND_DB = 118.0        # >= 118 dB anywhere in 63-120 Hz
BAND_HZ = (63.0, 120.0)
FLAT_BAND_HZ = (30.0, 120.0)
FLAT_TOL_DB = 2.0             # max |residual| after DSP over 30-120 Hz
FLAT_RMS_DB = 1.0             # RMS residual after DSP over 30-120 Hz
HP_HZ = 15.0                  # infrasonic LR4 high-pass corner
MAX_PEQ_BOOST_DB = 6.0        # PEQ boost ceiling (the Linkwitz transform is a targeting filter, not EQ)
PORT_AIR_MPS_MAX = 17.0       # C11 port peak particle velocity
Q_LEAK = 7.0                  # C7 leakage Q
Q_PORT = 10.0                 # C7 port Q
N_END = 2.0                   # free-standing box: two radiating mouths
DRIVE_SPL_V = 2.83            # the datasheet sensitivity reference voltage (rms)
MIC_DISTANCE_M = 1.0
HALF_SPACE = 2.0 * math.pi    # solid angle


# --------------------------------------------------------------------------- box primitives

def box_compliance(vb_m3: float) -> float:
    """Acoustic compliance ``C_ab = V_b / (rho c^2)`` [m^3/Pa]."""
    if not (np.isfinite(vb_m3) and vb_m3 > 0.0):
        raise ValueError(f"box volume must be finite and > 0, got {vb_m3!r}")
    return float(vb_m3) / (RHO_AIR * C_AIR ** 2)


def port_effective_length(vb_m3: float, fb_hz: float, s_port_m2: float) -> float:
    """Effective port length [m] that tunes ``vb_m3`` to ``fb_hz`` with port area ``s_port_m2``.

    From ``fb = c/(2 pi) sqrt(S_port / (V_b L_eff))``: ``L_eff = S_port / (rho C_ab (2 pi fb)^2)``.
    """
    if not (np.isfinite(fb_hz) and fb_hz > 0.0):
        raise ValueError(f"fb_hz must be finite and > 0, got {fb_hz!r}")
    if not (np.isfinite(s_port_m2) and s_port_m2 > 0.0):
        raise ValueError(f"port area must be finite and > 0, got {s_port_m2!r}")
    cab = box_compliance(vb_m3)
    return float(s_port_m2 / (RHO_AIR * cab * (2.0 * math.pi * float(fb_hz)) ** 2))


def port_tuning_hz(vb_m3: float, s_port_m2: float, l_eff_m: float) -> float:
    """Helmholtz tuning ``fb = c/(2 pi) sqrt(S_port / (V_b L_eff))`` [Hz] (the inverse of the above)."""
    if not (np.isfinite(l_eff_m) and l_eff_m > 0.0):
        raise ValueError(f"effective port length must be finite and > 0, got {l_eff_m!r}")
    return C_AIR / (2.0 * math.pi) * math.sqrt(float(s_port_m2) / (float(vb_m3) * float(l_eff_m)))


@dataclass(frozen=True)
class Box:
    """One enclosure. ``kind`` is ``"sealed"`` or ``"vented"``; volumes are NET acoustic volumes.

    ``port_area_cm2`` and ``port_length_mm`` describe the neck of a vented box; the effective length
    adds ``n_end * 0.85 * r_eq``. ``q_leak`` and ``q_port`` are C7's Ql and Q_port.
    """

    kind: str
    vb_l: float
    fb_hz: float | None = None
    port_area_cm2: float | None = None
    port_length_mm: float | None = None
    q_leak: float = Q_LEAK
    q_port: float = Q_PORT
    n_end: float = N_END

    def __post_init__(self) -> None:
        if self.kind not in ("sealed", "vented"):
            raise ValueError(f"box kind must be 'sealed' or 'vented', got {self.kind!r}")
        if not (np.isfinite(self.vb_l) and self.vb_l > 0.0):
            raise ValueError(f"Vb must be finite and > 0 L, got {self.vb_l!r}")
        if self.kind == "vented":
            if self.fb_hz is None or self.port_area_cm2 is None or self.port_length_mm is None:
                raise ValueError("vented box needs fb_hz, port_area_cm2 and port_length_mm")
            if not (np.isfinite(self.fb_hz) and self.fb_hz > 0.0):
                raise ValueError(f"fb_hz must be finite and > 0, got {self.fb_hz!r}")
            if not (np.isfinite(self.port_area_cm2) and self.port_area_cm2 > 0.0):
                raise ValueError(f"port area must be finite and > 0, got {self.port_area_cm2!r}")
            if not (np.isfinite(self.port_length_mm) and self.port_length_mm > 0.0):
                raise ValueError(f"port length must be finite and > 0, got {self.port_length_mm!r}")
        if not (np.isfinite(self.q_leak) and self.q_leak > 0.0):
            raise ValueError(f"Ql must be finite and > 0, got {self.q_leak!r}")
        if not (np.isfinite(self.q_port) and self.q_port > 0.0):
            raise ValueError(f"Q_port must be finite and > 0, got {self.q_port!r}")

    # -- geometry -------------------------------------------------------------------------------
    @property
    def vb_m3(self) -> float:
        return self.vb_l * 1e-3

    @property
    def s_port_m2(self) -> float:
        return 0.0 if self.port_area_cm2 is None else self.port_area_cm2 * 1e-4

    @property
    def r_eq_m(self) -> float:
        return math.sqrt(self.s_port_m2 / math.pi) if self.s_port_m2 else 0.0

    @property
    def l_eff_m(self) -> float:
        if self.kind == "sealed":
            return 0.0
        assert self.port_length_mm is not None
        return float(self.port_length_mm) * 1e-3 + self.n_end * 0.85 * self.r_eq_m

    @property
    def tuning_hz(self) -> float | None:
        if self.kind == "sealed":
            return None
        return port_tuning_hz(self.vb_m3, self.s_port_m2, self.l_eff_m)

    # -- acoustics ------------------------------------------------------------------------------
    def z_port(self, f) -> np.ndarray:
        """C7 port impedance [Pa s/m^3]: ``x/Q + j x``, ``x = omega rho L_eff / S_port``."""
        f = np.asarray(f, dtype=np.float64)
        w = 2.0 * np.pi * f
        x = w * RHO_AIR * self.l_eff_m / self.s_port_m2
        return (x / self.q_port + 1j * x).astype(np.complex128)

    def z_box(self, f) -> np.ndarray:
        """Acoustic impedance seen by the cone [Pa s/m^3]: compliance || leak (|| port)."""
        f = np.asarray(f, dtype=np.float64)
        w = 2.0 * np.pi * f
        cab = box_compliance(self.vb_m3)
        r_leak = self.q_leak / (w * cab)
        y = 1j * w * cab + 1.0 / r_leak
        if self.kind == "vented":
            y = y + 1.0 / self.z_port(f)
        return (1.0 / y).astype(np.complex128)

    def leakage_resistance(self, f) -> np.ndarray:
        """``R_al = Ql / (omega C_ab)`` [Pa s/m^3]."""
        f = np.asarray(f, dtype=np.float64)
        return (self.q_leak / (2.0 * np.pi * f * box_compliance(self.vb_m3))).astype(np.float64)


# --------------------------------------------------------------------------- response

@dataclass
class State:
    """Per-volt small-signal state of one driver in one box (all arrays over ``f``).

    Every quantity is **per volt rms** of driver input, so ``spl_db + 20 log10(V)`` is the SPL at
    ``V`` and the limit voltages are simply ``limit / per_volt_quantity``.
    """

    f: np.ndarray
    z_in_ohm: np.ndarray
    i_a: np.ndarray
    v_mps: np.ndarray
    u_d_m3s: np.ndarray
    u_p_m3s: np.ndarray
    p_b_pa: np.ndarray
    x_peak_mm: np.ndarray
    port_v_peak_mps: np.ndarray
    spl_db: np.ndarray
    p_rms_pa: np.ndarray
    powers_w: dict = field(default_factory=dict)

    @property
    def spl_at_2v83_db(self) -> np.ndarray:
        return self.spl_db + 20.0 * math.log10(DRIVE_SPL_V)


def _freq(f) -> np.ndarray:
    f = np.asarray(f, dtype=np.float64)
    if f.ndim == 0:
        f = f[None]
    if np.any(~np.isfinite(f)) or np.any(f <= 0.0):
        raise ValueError("frequencies must be finite and > 0")
    return f


def evaluate(f, cone: ConeDriver, box: Box, volts: float = 1.0) -> State:
    """Full small-signal state of ``cone`` in ``box`` at ``volts`` rms (default: per volt)."""
    f = _freq(f)
    w = 2.0 * np.pi * f
    e = float(volts) * np.ones(f.shape, dtype=np.complex128)

    ze = cone.re_ohm + 1j * w * cone.le_h
    zm0 = (cone.rms_kg_s + 1j * w * cone.mms_kg + 1.0 / (1j * w * cone.cms_m_per_n)
           + cone.bl_tm ** 2 / ze)
    zb = box.z_box(f)
    sd = cone.sd_m2
    zm = zm0 + sd ** 2 * zb

    v = cone.bl_tm * e / (ze * zm)
    i = (e - cone.bl_tm * v) / ze
    u_d = sd * v
    p_b = -u_d * zb
    if box.kind == "vented":
        zp = box.z_port(f)
        u_p = p_b / zp
        p_port_w = np.abs(p_b) ** 2 * (zp.real / np.abs(zp) ** 2)
    else:
        u_p = np.zeros_like(v)
        p_port_w = np.zeros_like(f)

    p_tot = 1j * w * RHO_AIR * (u_d + u_p) / (HALF_SPACE * MIC_DISTANCE_M)
    spl = 20.0 * np.log10(np.maximum(np.abs(p_tot) / REF_P, 1e-30))

    r_leak = box.leakage_resistance(f)
    powers = {
        "electrical": np.real(e * np.conj(i)),
        "joule": np.abs(i) ** 2 * cone.re_ohm,
        "mechanical": cone.rms_kg_s * np.abs(v) ** 2,
        "port": p_port_w,
        "leakage": np.abs(p_b) ** 2 / r_leak,
        "radiated": RHO_AIR * w ** 2 * np.abs(u_d + u_p) ** 2 / (4.0 * math.pi * C_AIR),
    }
    return State(
        f=f,
        z_in_ohm=(1.0 / i).astype(np.complex128),
        i_a=i,
        v_mps=v,
        u_d_m3s=u_d,
        u_p_m3s=u_p,
        p_b_pa=p_b,
        x_peak_mm=cone_excursion_peak_mm(f, v),
        port_v_peak_mps=port_velocity_peak(u_p, box.s_port_m2) if box.kind == "vented"
        else np.zeros_like(f),
        spl_db=spl,
        p_rms_pa=np.abs(p_tot),
        powers_w=powers,
    )


def energy_balance(state: State, rtol: float = 1e-9) -> float:
    """Largest relative error of ``P_elec = P_joule + P_mech + P_port + P_leak`` over the sweep.

    The lumped circuit is passive, so this is an exact identity; a nonzero value means a sign or a
    topology error, not rounding (the test asserts < 1e-9).
    """
    p = state.powers_w
    lhs = p["electrical"]
    rhs = p["joule"] + p["mechanical"] + p["port"] + p["leakage"]
    denom = np.maximum(np.abs(lhs), 1e-18)
    return float(np.max(np.abs(lhs - rhs) / denom))


# --------------------------------------------------------------------------- DSP

def linkwitz_transform(f, f0, q0, fc, qc) -> np.ndarray:
    """Linkwitz transform from the box's own ``(f0, Q0)`` to the target ``(fc, Qc)`` (``exp(+jwt)``).

    ``H(s) = (s^2 + (w0/Q0) s + w0^2) / (s^2 + (wc/Qc) s + wc^2)`` with ``s = j 2 pi f``; unit
    magnitude at high frequency, boosting the low end when ``fc < f0``.
    """
    f = _freq(f)
    if not (f0 > 0 and q0 > 0 and fc > 0 and qc > 0):
        raise ValueError("linkwitz_transform: f0, q0, fc, qc must all be > 0")
    s = 1j * 2.0 * np.pi * f
    w0, wc = 2.0 * np.pi * float(f0), 2.0 * np.pi * float(fc)
    num = s * s + (w0 / float(q0)) * s + w0 * w0
    den = s * s + (wc / float(qc)) * s + wc * wc
    return (num / den).astype(np.complex128)


def dsp_response(f, *, hp_hz: float = HP_HZ, lt=None, peqs=()) -> np.ndarray:
    """Complex DSP response at ``f``: LR4 high-pass, optional Linkwitz transform, then PEQ bands.

    ``lt`` is ``(f0, q0, fc, qc)``; ``peqs`` is a sequence of ``(fc, Q, gain_db)``. The DSP block is
    linear, so the box response is multiplied by ``dsp_response`` to get the EQ'd response.
    """
    f = _freq(f)
    h = dsp.lr(f, hp_hz, 4, "hp")
    if lt is not None:
        h = h * linkwitz_transform(f, *lt)
    for fc, q, gain_db in peqs:
        h = h * dsp.peaking(f, fc, gain_db, q)
    return h.astype(np.complex128)


def dsp_db(f, **kwargs) -> np.ndarray:
    """``20 log10 |dsp_response|`` [dB]."""
    return 20.0 * np.log10(np.maximum(np.abs(dsp_response(f, **kwargs)), 1e-30))


def _eq_db(f, peqs) -> np.ndarray:
    h = np.ones(f.shape, dtype=np.complex128)
    for fc, q, gain_db in peqs:
        h = h * dsp.peaking(f, fc, gain_db, q)
    return 20.0 * np.log10(np.maximum(np.abs(h), 1e-30))


def fit_peq(f, spl_db, *, centers=(30.0, 38.0, 50.0, 65.0, 90.0),
            qs=(0.9, 1.2, 1.2, 1.2, 1.0),
            band=FLAT_BAND_HZ, max_boost_db=MAX_PEQ_BOOST_DB, n_iter=80) -> list[tuple[float, float, float]]:
    """Least-squares PEQ gains that flatten ``spl_db`` over ``band``.

    Centres and Qs are fixed (a real DSP preset); the four gains are the unknowns, bounded to
    ``[-12, max_boost_db]`` dB. The reference level is the mean of ``spl_db`` over the band, so the
    fit neither raises nor lowers the overall level.
    """
    f = _freq(f)
    r = np.asarray(spl_db, dtype=np.float64)
    if r.shape != f.shape:
        raise ValueError("fit_peq: f and spl_db must have the same shape")
    mask = (f >= band[0]) & (f <= band[1])
    if np.count_nonzero(mask) < 8:
        raise ValueError("fit_peq: the band needs at least 8 samples")
    fm, rm = f[mask], r[mask]
    target = float(np.mean(rm))
    boost = float(max_boost_db)

    def residual(gains):
        return _eq_db(fm, [(fc, q, g) for fc, q, g in zip(centers, qs, gains)]) - (target - rm)

    sol = least_squares(residual, np.zeros(len(centers)), bounds=(-12.0, boost),
                        xtol=1e-10, ftol=1e-10, gtol=1e-10, max_nfev=n_iter)
    gains = np.clip(sol.x, -12.0, boost)
    return [(float(fc), float(q), float(g)) for fc, q, g in zip(centers, qs, gains)]


# --------------------------------------------------------------------------- limits

def max_spl(f, cone: ConeDriver, box: Box, eq_db=None) -> dict:
    """Maximum SPL per frequency from Xmax, P_AES and the 17 m/s port limit (C11).

    Returns a dict with ``spl_max_db`` (per frequency, before DSP EQ), ``e_lim_v`` (the driver
    voltage ceiling), ``limiting`` (one of ``"xmax"``, ``"p_aes"``, ``"port"`` per frequency),
    ``spl_max_eq_db`` (the same ceiling with the fixed DSP EQ applied).
    """
    st = evaluate(f, cone, box, volts=1.0)
    f = st.f
    with np.errstate(divide="ignore", invalid="ignore"):
        e_x = np.where(st.x_peak_mm > 0.0, cone.xmax_mm / st.x_peak_mm, np.inf)
        e_p = np.full_like(f, math.sqrt(cone.p_aes_w * cone.re_ohm))
        e_v = np.where(st.port_v_peak_mps > 0.0,
                       PORT_AIR_MPS_MAX / st.port_v_peak_mps, np.inf)
    stack = np.vstack([e_x, e_p, e_v])
    idx = np.argmin(stack, axis=0)
    e_lim = stack[idx, np.arange(f.size)]
    names = np.array(["xmax", "p_aes", "port"])
    spl_max_db = st.spl_db + 20.0 * np.log10(np.maximum(e_lim, 1e-30))
    out = {
        "f": f,
        "spl_max_db": spl_max_db,
        "spl_max_eq_db": spl_max_db if eq_db is None else spl_max_db + np.asarray(eq_db, float),
        "e_lim_v": e_lim,
        "limiting": names[idx],
        "p_aes_v": math.sqrt(cone.p_aes_w * cone.re_ohm),
    }
    return out


def _band_min(f, spl, lo, hi, n=400) -> float:
    """Minimum of ``spl`` over ``[lo, hi]`` on a dense grid (linear interpolation)."""
    f = np.asarray(f, float)
    spl = np.asarray(spl, float)
    grid = np.geomspace(lo, hi, n)
    return float(np.min(np.interp(grid, f, spl)))


def _f3_hz(f, spl_db, ref_lo=63.0, ref_hi=120.0) -> float:
    """-3 dB point below the passband: where the curve falls 3 dB under its 63-120 Hz mean."""
    f = np.asarray(f, float)
    spl = np.asarray(spl_db, float)
    ref = float(np.mean(spl[(f >= ref_lo) & (f <= ref_hi)]))
    grid = np.geomspace(f.min(), 200.0, 2000)
    curve = np.interp(grid, f, spl)
    below = curve <= ref - 3.0
    if not np.any(below):
        return float("nan")
    # the corner is the lowest-frequency upward crossing (-3 dB from the passband)
    for i in range(len(grid) - 1):
        if below[i] and not below[i + 1]:
            x0, x1 = math.log(grid[i]), math.log(grid[i + 1])
            y0, y1 = curve[i] - (ref - 3.0), curve[i + 1] - (ref - 3.0)
            return float(math.exp(x0 + (x1 - x0) * y0 / (y0 - y1)))
    return float("nan")


# --------------------------------------------------------------------------- geometry

@dataclass(frozen=True)
class Cabinet:
    """Internal / external dimensions [mm] for a net volume, driver on the front, slot port on the floor.

    ``w_int x h_int`` is set by the driver frame (``frame_od_mm`` when published, else
    ``cutout_mm + 60``) plus 20 mm of internal clearance; the gross volume (net + port + an
    estimated driver displacement of ``0.25 Sd depth``) sets the depth. The port runs along the
    depth, so the required neck length has to fit inside it.
    """

    w_int_mm: float
    h_int_mm: float
    d_int_mm: float
    gross_l: float
    driver_volume_l: float
    port_volume_l: float
    wall_mm: float = 18.0

    @property
    def ext_mm(self) -> tuple[float, float, float]:
        return (self.w_int_mm + 2 * self.wall_mm,
                self.h_int_mm + 2 * self.wall_mm,
                self.d_int_mm + 2 * self.wall_mm)

    @property
    def max_port_length_mm(self) -> float:
        return max(0.0, self.d_int_mm - 60.0)


def box_dimensions_mm(cone: ConeDriver, box: Box, *, wall_mm: float = 18.0) -> Cabinet:
    """Cabinet for ``box``: driver-size footprint, depth set by the gross volume."""
    frame = float(cone.frame_od_mm) if cone.frame_od_mm is not None else cone.cutout_mm + 60.0
    w = frame + 20.0
    h = frame + 20.0
    driver_l = 0.25 * cone.sd_m2 * (cone.depth_mm * 1e-3) * 1e3
    port_l = 0.0
    if box.kind == "vented":
        assert box.port_length_mm is not None
        port_l = box.s_port_m2 * (float(box.port_length_mm) * 1e-3) * 1e3
    gross = box.vb_l + driver_l + port_l
    d = gross * 1e6 / (w * h)
    return Cabinet(w, h, d, gross, driver_l, port_l, wall_mm=wall_mm)


# --------------------------------------------------------------------------- designs

@dataclass
class Design:
    """One evaluated design (JSON-serialisable) with its numbers of record."""

    stem: str
    driver: str
    kind: str
    vb_l: float
    gross_l: float
    cabinet_mm: tuple
    fb_hz: float | None = None
    port_area_cm2: float | None = None
    port_height_mm: float | None = None
    port_length_mm: float | None = None
    port_l_eff_mm: float | None = None
    f3_hz: float | None = None
    f3_natural_hz: float | None = None
    hp_hz: float = HP_HZ
    lt: tuple | None = None
    peq: tuple = ()
    eq_boost_db: float = 0.0
    ripple_rms_db: float = float("nan")
    ripple_max_db: float = float("nan")
    flat_min_db: float = float("nan")     # lowest SPL in the flat band relative to the mean
    natural_ripple_db: float = float("nan")  # 30-120 Hz deviation BEFORE the peaking EQ
    spl_2v83_db: dict = field(default_factory=dict)
    spl_max_db: dict = field(default_factory=dict)
    margin_40_db: float = float("nan")
    margin_63_120_db: float = float("nan")
    limiting_40: str = ""
    limiting_63_120: str = ""
    flat_max_spl_db: float = float("nan")
    e_target_v: float = float("nan")
    peq_boost_db: float = 0.0
    note: str = ""

    @property
    def meets(self) -> bool:
        return (np.isfinite(self.margin_40_db) and np.isfinite(self.margin_63_120_db)
                and self.margin_40_db >= 0.0 and self.margin_63_120_db >= 0.0)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["cabinet_mm"] = tuple(round(float(v), 1) for v in self.cabinet_mm)
        d["peq"] = [tuple(round(float(v), 3) for v in band) for band in self.peq]
        return d


KEY_FREQS = (30.0, 40.0, 50.0, 63.0, 80.0, 100.0, 120.0)
_F = np.geomspace(20.0, 200.0, 241)
_F_FIT = np.geomspace(25.0, 160.0, 161)


def _assess(cone, box, stem, lt, peqs):
    """Evaluate one candidate; returns (Design, passes_flatness) or None if it cannot be built."""
    try:
        cab = box_dimensions_mm(cone, box)
    except ValueError:
        return None
    if box.kind == "vented" and box.port_length_mm > cab.max_port_length_mm:
        return None
    if cab.d_int_mm < cone.depth_mm + 20.0:
        return None

    st = evaluate(_F, cone, box, volts=1.0)
    lim = max_spl(_F, cone, box)
    spl = st.spl_db

    eq_db = dsp_db(_F, hp_hz=HP_HZ, lt=lt, peqs=peqs)
    curve = spl + eq_db
    mask = (_F >= FLAT_BAND_HZ[0]) & (_F <= FLAT_BAND_HZ[1])
    ref = float(np.mean(curve[mask]))
    resid = curve[mask] - ref
    ripple_rms = float(np.sqrt(np.mean(resid ** 2)))
    ripple_max = float(np.max(np.abs(resid)))
    boost = float(np.max(eq_db[mask]))
    peq_boost = max([g for _, _, g in peqs], default=0.0)
    natural = spl + dsp_db(_F, hp_hz=HP_HZ, lt=lt)
    natural_ripple = float(np.max(np.abs(natural[mask] - np.mean(natural[mask]))))

    smax = lim["spl_max_db"]
    m40 = _spl_at(_F, smax, 40.0) - TARGET_40_DB
    m63 = _band_min(_F, smax, *BAND_HZ) - TARGET_BAND_DB
    lim40 = str(lim["limiting"][int(np.argmin(np.abs(_F - 40.0)))])
    band_mask = (_F >= BAND_HZ[0]) & (_F <= BAND_HZ[1])
    lim_band = str(lim["limiting"][band_mask][int(np.argmin(smax[band_mask]))])

    design = Design(
        stem=stem,
        driver=cone.name,
        kind=box.kind,
        vb_l=float(box.vb_l),
        gross_l=float(cab.gross_l),
        cabinet_mm=cab.ext_mm,
        fb_hz=None if box.fb_hz is None else float(box.fb_hz),
        port_area_cm2=None if box.port_area_cm2 is None else float(box.port_area_cm2),
        port_height_mm=None,
        port_length_mm=None if box.port_length_mm is None else float(box.port_length_mm),
        port_l_eff_mm=None if box.kind == "sealed" else float(box.l_eff_m * 1e3),
        f3_hz=_f3_hz(_F, curve),
        f3_natural_hz=_f3_hz(_F, natural),
        hp_hz=HP_HZ,
        lt=None if lt is None else tuple(float(v) for v in lt),
        peq=tuple((float(fc), float(q), float(g)) for fc, q, g in peqs),
        eq_boost_db=boost,
        ripple_rms_db=ripple_rms,
        ripple_max_db=ripple_max,
        flat_min_db=float(np.min(curve[mask]) - np.mean(curve[mask])),
        natural_ripple_db=natural_ripple,
        spl_2v83_db={f"{q:g}": float(_spl_at(_F, st.spl_at_2v83_db, q)) for q in KEY_FREQS},
        spl_max_db={f"{q:g}": float(_spl_at(_F, smax, q)) for q in KEY_FREQS},
        margin_40_db=float(m40),
        margin_63_120_db=float(m63),
        limiting_40=lim40,
        limiting_63_120=lim_band,
        flat_max_spl_db=float(_band_min(_F, smax, *FLAT_BAND_HZ)),
        e_target_v=float(_e_for_spl(_F, st, TARGET_BAND_DB)),
        peq_boost_db=float(peq_boost),
        note="",
    )
    flat_ok = (ripple_max <= FLAT_TOL_DB and ripple_rms <= FLAT_RMS_DB
               and peq_boost <= MAX_PEQ_BOOST_DB)
    return design, flat_ok


def _spl_at(f, spl, f0) -> float:
    return float(np.interp(math.log(f0), np.log(f), spl))


def _e_for_spl(f, st: State, spl_db: float) -> float:
    return float(10.0 ** ((spl_db - float(_spl_at(f, st.spl_db, 63.0))) / 20.0))


def _first_by_volume(candidates):
    """Smallest net volume that passes flatness; ties by the natural response, then EQ boost."""
    ok = [c for c in candidates if c[1] and c[0].meets]
    if not ok:
        return None
    best_vb = min(c[0].vb_l for c in ok)
    same = [c for c in ok if c[0].vb_l <= best_vb * 1.02]
    same.sort(key=lambda c: (-min(c[0].margin_40_db, c[0].margin_63_120_db),
                             c[0].peq_boost_db, c[0].natural_ripple_db,
                             c[0].ripple_max_db))
    return same[0][0]


# --------------------------------------------------------------------------- design families

def design_vented(cone: ConeDriver, stem: str = "", *, vb_grid=None, fb_grid=None,
                  port_height_grid=(22.0, 25.0, 30.0, 35.0, 42.0, 50.0, 60.0),
                  verbose=False) -> Design | None:
    """Smallest vented box that meets the targets with a slot port on the cabinet floor.

    Grid: ``Vb / Vas`` in ``[0.30, 1.60]``, tuning 24-40 Hz, slot height 22-60 mm. Port width is the
    internal cabinet width minus 50 mm of side clearance; the neck length follows from the tuning
    formula, so a candidate is only kept if the neck fits inside the cabinet depth.
    """
    vas = cone.vas_l
    if vb_grid is None:
        vb_grid = vas * np.geomspace(0.30, 1.60, 10)
    if fb_grid is None:
        fb_grid = np.arange(24.0, 40.5, 1.0)

    frame = float(cone.frame_od_mm) if cone.frame_od_mm is not None else cone.cutout_mm + 60.0
    port_width_mm = frame + 20.0 - 50.0

    candidates = []
    for vb in vb_grid:
        for hp in port_height_grid:
            s_port_cm2 = port_width_mm * hp / 100.0     # mm^2 -> cm^2
            s_port_m2 = s_port_cm2 * 1e-4
            for fb in fb_grid:
                l_eff = port_effective_length(vb * 1e-3, fb, s_port_m2)
                r_eq = math.sqrt(s_port_m2 / math.pi)
                l_neck_mm = (l_eff - N_END * 0.85 * r_eq) * 1e3
                if l_neck_mm < 20.0:
                    continue
                box = Box("vented", float(vb), float(fb), float(s_port_cm2), float(l_neck_mm))
                cab = box_dimensions_mm(cone, box)
                if l_neck_mm > cab.max_port_length_mm:
                    continue
                # pre-filter on headroom before paying for the EQ fit
                lim = max_spl(_F, cone, box)
                if _spl_at(_F, lim["spl_max_db"], 40.0) < TARGET_40_DB:
                    continue
                if _band_min(_F, lim["spl_max_db"], *BAND_HZ) < TARGET_BAND_DB:
                    continue
                # natural response in the fit band, then fit the PEQ preset
                pre = dsp_db(_F_FIT, hp_hz=HP_HZ)
                spl_fit = evaluate(_F_FIT, cone, box).spl_db + pre
                peqs = fit_peq(_F_FIT, spl_fit)
                assessed = _assess(cone, box, stem, None, peqs)
                if assessed is None:
                    continue
                d, flat_ok = assessed
                d.port_height_mm = float(hp)
                candidates.append((d, flat_ok))
                if verbose and flat_ok and d.meets:
                    print(f"  vented Vb={vb:6.1f} L fb={fb:4.1f} h={hp:4.1f} mm "
                          f"Lneck={l_neck_mm:5.1f} mm ripple={d.ripple_max_db:4.2f} dB "
                          f"m40={d.margin_40_db:+4.1f} m63={d.margin_63_120_db:+4.1f}")

    best = _first_by_volume(candidates)
    if best is None:
        # no size meets the owner targets: report the largest-margin attempt for the record
        ranked = sorted(candidates, key=lambda c: (-c[0].margin_63_120_db, c[0].vb_l))
        if ranked:
            fallback = ranked[0][0]
            fallback.note = "no candidate met the owner targets; this is the best-margin attempt"
            return fallback
        return None
    return best


def design_sealed(cone: ConeDriver, stem: str = "", *, vb_grid=None,
                  fc_grid=(26.0, 28.0, 30.0, 32.0), qc=0.707, verbose=False) -> Design | None:
    """Smallest sealed box + Linkwitz transform that meets the targets.

    The transform is designed from the box's own second-order parameters
    ``f0 = fs sqrt(1 + Vas/Vb)`` and ``Q0 = Qts sqrt(1 + Vas/Vb)`` with ``Qts`` from the published
    ``Qms`` and the derived ``Qes = 2 pi fs Mms Re / Bl^2``. After the LT a 4-band PEQ preset trims
    the residual.
    """
    vas = cone.vas_l
    if vb_grid is None:
        vb_grid = vas * np.geomspace(0.25, 1.20, 10)

    # The box resonance and Q are taken from the model's own Mms/Cms/Rms, not from the published
    # fs: the C8 rule derives Cms from Vas, and for a few files the published fs disagrees with the
    # derived pair (see the driver-file notes). Using the model's f0/Q0 keeps the LT consistent with
    # the response it is flattening.
    r_total = cone.rms_kg_s + cone.bl_tm ** 2 / cone.re_ohm

    candidates = []
    for vb in vb_grid:
        alpha = vas / vb
        c_total = cone.cms_m_per_n / (1.0 + alpha)     # driver Cms in series with the box spring
        f0 = 1.0 / (2.0 * math.pi * math.sqrt(cone.mms_kg * c_total))
        q0 = 2.0 * math.pi * f0 * cone.mms_kg / r_total
        for fc in fc_grid:
            box = Box("sealed", float(vb))
            lt = (f0, q0, float(fc), float(qc))
            lim = max_spl(_F, cone, box)
            if _spl_at(_F, lim["spl_max_db"], 40.0) < TARGET_40_DB:
                continue
            if _band_min(_F, lim["spl_max_db"], *BAND_HZ) < TARGET_BAND_DB:
                continue
            spl_fit = evaluate(_F_FIT, cone, box).spl_db + dsp_db(
                _F_FIT, hp_hz=HP_HZ, lt=lt)
            peqs = fit_peq(_F_FIT, spl_fit)
            assessed = _assess(cone, box, stem, lt, peqs)
            if assessed is None:
                continue
            d, flat_ok = assessed
            candidates.append((d, flat_ok))
            if verbose and flat_ok and d.meets:
                print(f"  sealed Vb={vb:6.1f} L LT {f0:4.1f}/{q0:4.2f} -> {fc:4.1f}/{qc:4.2f} "
                      f"ripple={d.ripple_max_db:4.2f} dB m40={d.margin_40_db:+4.1f} "
                      f"m63={d.margin_63_120_db:+4.1f}")

    best = _first_by_volume(candidates)
    if best is None:
        ranked = sorted(candidates, key=lambda c: (-c[0].margin_63_120_db, c[0].vb_l))
        if ranked:
            fallback = ranked[0][0]
            fallback.note = "no candidate met the owner targets; this is the best-margin attempt"
            return fallback
        return None
    return best


def design_best(cone: ConeDriver, stem: str = "", verbose: bool = False) -> dict:
    """Best vented and best sealed+LT design for one driver."""
    return {
        "vented": design_vented(cone, stem, verbose=verbose),
        "sealed": design_sealed(cone, stem, verbose=verbose),
    }


def recommend(stems=SHORTLIST, verbose: bool = False) -> list[dict]:
    """Run both families for every short-listed driver; return rows sorted by the outcome.

    Sorting: designs that meet the targets first, then by net volume, because the owner asked for
    the smallest box that meets the targets.
    """
    rows = []
    for stem in stems:
        cone = load_cone(stem)
        if verbose:
            print(f"\n{cone.name} ({stem}): model Fs {cone.fs_hz:.2f} Hz, Vas {cone.vas_l:.1f} L")
        designs = design_best(cone, stem, verbose=verbose)
        for kind, d in designs.items():
            if d is None:
                continue
            rows.append({
                "stem": stem,
                "driver": cone.name,
                "kind": kind,
                "design": d,
                "meets": d.meets,
            })

    def key(row):
        d = row["design"]
        slack = min(d.margin_40_db, d.margin_63_120_db) if d.meets else -1e9
        return (0 if row["meets"] else 1, d.vb_l, -slack)

    rows.sort(key=key)
    return rows


# --------------------------------------------------------------------------- CLI

def _fmt(value, spec=".1f", dash="-"):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return dash
    return format(float(value), spec)


def _print_design(d: Design) -> None:
    print(f"  {d.kind:6s} Vb {d.vb_l:6.1f} L (gross {d.gross_l:6.1f} L) "
          f"cabinet {d.cabinet_mm[0]:.0f} x {d.cabinet_mm[1]:.0f} x {d.cabinet_mm[2]:.0f} mm")
    if d.kind == "vented":
        width_cm = None
        if d.port_area_cm2 is not None and d.port_height_mm:
            width_cm = d.port_area_cm2 * 10.0 / float(d.port_height_mm)
        print(f"         fb {_fmt(d.fb_hz)} Hz, slot {_fmt(d.port_height_mm)} mm high x "
              f"{_fmt(width_cm)} cm wide, S {_fmt(d.port_area_cm2)} cm2, "
              f"neck {_fmt(d.port_length_mm)} mm (L_eff {_fmt(d.port_l_eff_mm)} mm)")
    if d.lt:
        f0, q0, fc, qc = d.lt
        print(f"         LT {f0:.1f} Hz / {q0:.2f} -> {fc:.1f} Hz / {qc:.2f}")
    print("         PEQ " + ", ".join(f"{fc:g} Hz Q{q:g} {g:+.1f} dB" for fc, q, g in d.peq)
          + f"; total DSP boost {d.eq_boost_db:+.1f} dB")
    print(f"         f3 {_fmt(d.f3_hz)} Hz (alignment {_fmt(d.f3_natural_hz)} Hz), ripple 30-120: "
          f"rms {d.ripple_rms_db:.2f} dB, max {d.ripple_max_db:.2f} dB "
          f"(natural {d.natural_ripple_db:.2f} dB)")
    print("         SPL 2.83 V  " + "  ".join(f"{k}:{v:.1f}" for k, v in d.spl_2v83_db.items()))
    print("         SPL max     " + "  ".join(f"{k}:{v:.1f}" for k, v in d.spl_max_db.items()))
    print(f"         margin 40 Hz {d.margin_40_db:+.1f} dB (limit {d.limiting_40}), "
          f"63-120 Hz {d.margin_63_120_db:+.1f} dB (limit {d.limiting_63_120}), "
          f"flat-program max {d.flat_max_spl_db:.1f} dB")
    if d.note:
        print(f"         NOTE: {d.note}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="M10 lumped bass-box designer (CPU only)")
    ap.add_argument("--driver", action="append", default=None, metavar="STEM",
                    help="driver file stem (repeatable); default: the seven M10 woofers")
    ap.add_argument("--all", action="store_true", help="run every short-listed driver")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    stems = tuple(args.driver) if args.driver else SHORTLIST
    if args.json:
        rows = []
        for stem in stems:
            cone = load_cone(stem)
            for kind, d in design_best(cone, stem).items():
                if d is not None:
                    rows.append(d.as_dict())
        print(json.dumps(rows, indent=2))
        return 0

    for row in recommend(stems, verbose=args.verbose):
        status = "MEETS" if row["meets"] else "misses"
        print(f"\n{row['driver']}  [{row['kind']}]  {status}")
        _print_design(row["design"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
