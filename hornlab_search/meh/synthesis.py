"""MEH system synthesis: network drives -> one absolute-pressure ``Response`` (contracts C6/C12).

The BEM solve gives one channel per source tag (CD = channel 0, entry groups = 1..E) in the
exp(-i omega t), per-unit-acceleration basis. :func:`system_response` converts that to network
quantities (``network.from_bem``), builds each channel's complex drive (DSP times the network
volume velocity, coupled exactly through ``network.couple``), sums ``H_net * U`` per plane/angle
(and over the sphere), and converts the result back to the BEM convention as ABSOLUTE Pa at the
solve distance for the nominal drive (2.83 V mids, the CD channel gain from the solution).

The returned :class:`~hornlab_search.types.Response` therefore runs through
``metrics.compute.compute_metrics`` unchanged. Its throat impedance is not defined on the
synthesised system, so ``z_throat`` is an all-nan array (the contract's "impedance = nan array").

:class:`NetworkSolution` is the C12 record plus the runtime context (drivers, port geometry and,
optionally, the solved response / cached nominal state) that synthesis and limits need. Only the
record fields go to ``to_dict``.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields

import numpy as np

from ..constants import REF_P
from ..types import Response
from .drivers import CDSource, ConeDriver, load_cd, load_cone
from .network import (
    cd_volume_velocity,
    cone_excursion_peak_mm,
    cone_velocity_rms,
    couple,
    entry_norton,
    from_bem,
    port_velocity_peak,
)
from .dsp import delay, lr, polarity

__all__ = [
    "NetworkSolution",
    "NOMINAL_VOLTS",
    "channel_drives",
    "nominal_state",
    "system_response",
    "solution_drivers",
]

#: Per-driver RMS drive voltage at 0 dB channel gain (C7's 2.83 V reference; the same value the
#: 1-D sketch and the driver sensitivity basis use).
NOMINAL_VOLTS = 2.83

_MISSING = object()

#: NetworkSolution fields that are runtime context, not part of the C12 JSON record.
_RUNTIME_FIELDS = frozenset({
    "drivers_dir", "cd", "mid", "response", "nominal_state", "di_db",
})


def _get(obj, name, default=_MISSING):
    """Read ``name`` from a dict or an object; ``default`` also covers an attribute that is None."""
    value = _MISSING
    if isinstance(obj, dict):
        if name in obj:
            value = obj[name]
    elif hasattr(obj, name):
        value = getattr(obj, name)
    if value is _MISSING or (value is None and default is not _MISSING):
        if default is _MISSING:
            raise ValueError(f"solution has no '{name}'")
        return default
    return value


@dataclass
class NetworkSolution:
    """One optimised MEH network (C12) plus the context synthesis/limits need.

    The first block is the JSON record (``to_dict``); the second block is runtime context that
    ``inner`` / ``search.evaluate`` fills after the solve and does not serialise (driver objects,
    the BEM response, the cached per-frequency nominal state and an optional directivity curve).
    """

    # ---- C12 record -----------------------------------------------------------------
    cd_stem: str = ""
    mid_stem: str = ""
    xo_hz: float = 1000.0
    xo_order: int = 4
    mid_delay_ms: float = 0.0
    mid_polarity: int = 1
    gains_db: tuple = (0.0, 0.0)          # per channel, channel 0 = CD
    v_front_m3: float = 0.0               # per driver
    v_rear_m3: float = 0.0                # per driver
    eq_db: tuple = ()
    spl_max_db: tuple = ()
    inner_J: float = float("nan")
    n_evals: int = 0
    seed: int = 1234

    # ---- runtime context ------------------------------------------------------------
    hp_hz: float = 120.0                  # C10: LR4 high-pass on every MEH channel
    mid_count: int = 2                    # drivers in one mid entry group (C7's N)
    s_port_m2: float = 0.0                # one port area
    l_neck_m: float = 0.0                 # physical neck length (L_eff adds the end correction)
    n_end: int = 1                        # C7: 1 with BEM data, 2 to reproduce the 1-D sketch
    q_port: float = 10.0
    drivers_dir: str | None = None
    cd: CDSource | None = field(default=None, repr=False, compare=False)
    mid: ConeDriver | None = field(default=None, repr=False, compare=False)
    response: object | None = field(default=None, repr=False, compare=False)
    nominal_state: dict | None = field(default=None, repr=False, compare=False)
    di_db: object | None = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict:
        """The serialisable C12 record (runtime context excluded)."""
        return {f.name: getattr(self, f.name) for f in fields(self)
                if f.name not in _RUNTIME_FIELDS}


def solution_drivers(solution) -> tuple[CDSource, ConeDriver]:
    """The CD and mid driver for ``solution``: attached objects, else loaded from the stems."""
    cd = _get(solution, "cd", None)
    mid = _get(solution, "mid", None)
    directory = _get(solution, "drivers_dir", None)
    if cd is None:
        stem = str(_get(solution, "cd_stem", "") or "")
        if not stem:
            raise ValueError("solution has neither a 'cd' driver nor a 'cd_stem'")
        cd = load_cd(stem, directory=directory)
    if mid is None:
        stem = str(_get(solution, "mid_stem", "") or "")
        if not stem:
            raise ValueError("solution has neither a 'mid' driver nor a 'mid_stem'")
        mid = load_cone(stem, directory=directory)
    return cd, mid


def _gains(solution, n_c: int) -> np.ndarray:
    gains = np.asarray(_get(solution, "gains_db", ()), dtype=np.float64).ravel()
    if gains.size == 0:
        return np.zeros(n_c, dtype=np.float64)
    if gains.size == 1:
        return np.full(n_c, float(gains[0]), dtype=np.float64)
    if gains.size != n_c:
        raise ValueError(f"solution.gains_db has {gains.size} values for {n_c} channels")
    return gains


def _mid_inputs(solution):
    """Validate and return the per-driver mid port/chamber geometry."""
    counts = {
        "v_front_m3": _get(solution, "v_front_m3", 0.0),
        "v_rear_m3": _get(solution, "v_rear_m3", 0.0),
        "s_port_m2": _get(solution, "s_port_m2", 0.0),
        "l_neck_m": _get(solution, "l_neck_m", 0.0),
    }
    bad = [k for k, v in counts.items() if not (np.isfinite(v) and float(v) > 0.0)]
    if bad:
        raise ValueError(f"solution must give positive mid geometry: {bad}")
    n = int(_get(solution, "mid_count", 2))
    if n < 1:
        raise ValueError(f"solution.mid_count must be >= 1, got {n}")
    return {
        "n": n,
        "v_front_m3": float(counts["v_front_m3"]),
        "v_rear_m3": float(counts["v_rear_m3"]),
        "s_port_m2": float(counts["s_port_m2"]),
        "l_neck_m": float(counts["l_neck_m"]),
        "n_end": int(_get(solution, "n_end", 1)),
        "q_port": float(_get(solution, "q_port", 10.0)),
    }


def channel_drives(resp, solution) -> dict:
    """Per-channel complex volume velocities ``U`` plus the converted network data.

    Returns a dict with ``freqs_hz``, ``U (F,C)``, ``H_net (F,C,P,A)``, ``Z_net (F,C,C)``,
    ``e_volts (F,C)`` (mids only; column 0 is nan) and the mid Norton arrays ``u_sc``/``y``
    ``(F, C-1)``. Channel 0 is the CD; channels 1.. are entry groups (C6).
    """
    h_net, z_net, freqs = from_bem(resp)
    n_f, n_c = h_net.shape[0], h_net.shape[1]
    cd, mid = solution_drivers(solution)
    gains = _gains(solution, n_c)

    hp_hz = float(_get(solution, "hp_hz", 120.0))
    xo_hz = float(_get(solution, "xo_hz", 1000.0))
    xo_order = int(_get(solution, "xo_order", 4))
    delay_ms = float(_get(solution, "mid_delay_ms", 0.0))
    pol = float(np.asarray(polarity(_get(solution, "mid_polarity", 1))).ravel()[0])
    hp = lr(freqs, hp_hz, 4, "hp")

    # CD: mass-controlled volume velocity times its own crossover/gain DSP.
    cd_dsp = 10.0 ** (gains[0] / 20.0) * lr(freqs, xo_hz, xo_order, "hp") * hp
    u_cd = cd_volume_velocity(freqs, cd, cd_dsp)

    volts = np.full((n_f, n_c), np.nan + 0j, dtype=np.complex128)
    volts[:, 0] = np.nan
    n_e = n_c - 1
    if n_e > 0:
        geom = _mid_inputs(solution)
        mid_dsp = pol * delay(freqs, delay_ms) * lr(freqs, xo_hz, xo_order, "lp") * hp
        u_sc = np.zeros((n_f, n_e), dtype=np.complex128)
        y = np.zeros((n_f, n_e), dtype=np.complex128)
        for k in range(n_e):
            e = NOMINAL_VOLTS * 10.0 ** (gains[k + 1] / 20.0) * mid_dsp
            volts[:, k + 1] = e
            u_sc[:, k], y[:, k] = entry_norton(
                freqs, mid, geom["n"], geom["v_front_m3"], geom["s_port_m2"],
                geom["l_neck_m"], geom["v_rear_m3"], e,
                n_end=geom["n_end"], q_port=geom["q_port"],
            )
        u = couple(z_net, u_sc, y, u_cd)
    else:
        u_sc = np.zeros((n_f, 0), dtype=np.complex128)
        y = np.zeros((n_f, 0), dtype=np.complex128)
        u = couple(z_net, u_sc, y, u_cd)

    return {
        "freqs_hz": freqs,
        "U": u,
        "H_net": h_net,
        "Z_net": z_net,
        "e_volts": volts,
        "u_sc": u_sc,
        "y": y,
    }


def _spl_from_pressure(p) -> np.ndarray:
    with np.errstate(divide="ignore"):
        return 20.0 * np.log10(np.abs(np.asarray(p)) / REF_P)


def system_response(resp, solution) -> Response:
    """Synthesise the summed MEH pressure and return a metrics-ready :class:`Response`.

    The output pressure is absolute Pa at the solve distance for the nominal drive, in the BEM
    exp(-i omega t) convention (``conj`` of the network sum). ``spl_*_db`` are re 20 uPa, and
    ``p_h`` / ``p_v`` / ``p_balloon`` carry the complex pressure. ``z_throat`` is all nan.
    """
    drives = channel_drives(resp, solution)
    u = drives["U"]
    h_net = drives["H_net"]
    freqs = drives["freqs_hz"]

    # p_net = sum_c H_net[c] U[c]; back to exp(-i w t) for the Response.
    p_net = np.einsum("fcpa,fc->fpa", h_net, u)
    p_bem = np.conj(p_net)
    spl = _spl_from_pressure(p_bem)

    p_h = np.ascontiguousarray(p_bem[:, 0, :])
    p_v = np.ascontiguousarray(p_bem[:, 1, :])
    spl_h = _spl_from_pressure(p_h)
    spl_v = _spl_from_pressure(p_v)

    csp = getattr(resp, "channel_sphere_pressure", None)
    dirs = getattr(resp, "balloon_dirs", None)
    p_balloon = spl_balloon = None
    if csp is not None and dirs is not None:
        csp = np.asarray(csp, dtype=np.complex128)
        tags = tuple(int(t) for t in resp.channel_tags)
        areas = np.asarray([float(resp.tag_areas_m2[t]) for t in tags], dtype=np.float64)
        if csp.ndim != 3 or csp.shape[:2] != (freqs.size, len(tags)):
            raise ValueError(
                f"system_response: channel_sphere_pressure must be (F={freqs.size}, "
                f"C={len(tags)}, N), got {csp.shape}")
        w = 2.0 * np.pi * freqs
        h_sphere = np.conj(csp * (-1j * w)[:, None, None] / areas[None, :, None])
        p_net_s = np.einsum("fcn,fc->fn", h_sphere, u)
        p_balloon = np.ascontiguousarray(np.conj(p_net_s))
        spl_balloon = _spl_from_pressure(p_balloon)

    meta = {
        "source": "meh.synthesis",
        "spl_reference": ("absolute dB re 20 uPa at the solve distance for the nominal drive "
                          f"({NOMINAL_VOLTS:g} V mids, solution gains)"),
        "channel_tags": [int(t) for t in resp.channel_tags],
        "n_channels": int(h_net.shape[1]),
        "xo_hz": float(_get(solution, "xo_hz", 1000.0)),
        "xo_order": int(_get(solution, "xo_order", 4)),
        "hp_hz": float(_get(solution, "hp_hz", 120.0)),
        "distance_m": (getattr(resp, "meta", None) or {}).get("distance_m"),
    }

    return Response(
        freqs_hz=np.asarray(freqs, dtype=np.float64).copy(),
        h_angles_deg=np.asarray(getattr(resp, "h_angles_deg"), dtype=np.float64).copy(),
        v_angles_deg=np.asarray(getattr(resp, "v_angles_deg"), dtype=np.float64).copy(),
        spl_h_db=spl_h,
        spl_v_db=spl_v,
        balloon_dirs=None if dirs is None else np.asarray(dirs, dtype=np.float64).copy(),
        spl_balloon_db=spl_balloon,
        z_throat=np.full(freqs.size, np.nan, dtype=np.float64),
        p_h=p_h,
        p_v=p_v,
        p_balloon=p_balloon,
        backend="meh_synthesis",
        n_dof=getattr(resp, "n_dof", None),
        meta=meta,
    )


def nominal_state(resp, solution) -> dict:
    """Per-frequency state at the nominal drive, before any global level scaling.

    Keys (all at ``resp.freqs_hz``): ``spl_ref_db`` (F,) total on-axis system SPL,
    ``spl_channel_db`` (F,C) each channel's on-axis contribution, ``excursion_peak_mm`` (F,C)
    per-driver peak excursion, ``electrical_power_w`` (F,C) per-driver ``V^2/Re``,
    ``port_velocity_mps`` (F,C) per-port peak velocity, ``drive_v_rms`` (F,C) per-driver RMS
    voltage. Channel 0 (CD) leaves the physical-limit columns at +inf; its limit is the C11 CD
    power estimate, which uses ``spl_channel_db[:, 0]``.

    Everything scales linearly with input, so ``limits.spl_max`` finds the first hit by taking the
    smallest global scale factor.
    """
    drives = channel_drives(resp, solution)
    freqs = drives["freqs_hz"]
    u = drives["U"]
    h_net = drives["H_net"]
    z_net = drives["Z_net"]
    volts = drives["e_volts"]
    n_f, n_c = u.shape

    ax = int(np.argmin(np.abs(np.asarray(getattr(resp, "h_angles_deg"), dtype=np.float64))))
    contrib = h_net[:, :, 0, ax] * u                       # (F, C) complex on-axis contributions
    spl_channel = _spl_from_pressure(contrib)
    spl_ref = _spl_from_pressure(np.sum(contrib, axis=1))

    exc = np.full((n_f, n_c), np.inf, dtype=np.float64)
    power = np.full((n_f, n_c), np.inf, dtype=np.float64)
    port_v = np.full((n_f, n_c), np.inf, dtype=np.float64)
    drive_v = np.full((n_f, n_c), np.inf, dtype=np.float64)

    if n_c > 1:
        _cd, mid = solution_drivers(solution)
        geom = _mid_inputs(solution)
        p_entry = np.einsum("fij,fj->fi", z_net, u)        # (F, C) pressure at each source tag
        for c in range(1, n_c):
            e = volts[:, c]
            u_out = (drives["u_sc"][:, c - 1] - p_entry[:, c] * drives["y"][:, c - 1]) / geom["n"]
            v = cone_velocity_rms(
                freqs, mid, geom["n"], geom["v_front_m3"], geom["s_port_m2"],
                geom["l_neck_m"], geom["v_rear_m3"], e, p_entry[:, c],
                n_end=geom["n_end"], q_port=geom["q_port"],
            )
            exc[:, c] = cone_excursion_peak_mm(freqs, v)
            port_v[:, c] = port_velocity_peak(u_out, geom["s_port_m2"])
            power[:, c] = np.abs(e) ** 2 / mid.re_ohm
            drive_v[:, c] = np.abs(e)

    return {
        "freqs_hz": freqs,
        "spl_ref_db": spl_ref,
        "spl_channel_db": spl_channel,
        "excursion_peak_mm": exc,
        "electrical_power_w": power,
        "port_velocity_mps": port_v,
        "drive_v_rms": drive_v,
    }
