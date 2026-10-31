"""Lumped MEH network: BEM conversion, entry Norton equivalents, coupling (contracts C6/C7/C12).

Conventions (C6)
---------------
* Network math is **exp(+j omega t)** and **SI rms**; every array is ``numpy.complex128`` and vectorised
  over frequency.
* A BEM ``Response`` is exp(-i omega t) and per unit normal **acceleration**. For channel ``c`` with
  full-domain area ``A_c``::

      X_v  = X_a * (-1j * omega)              per unit normal velocity
      X_U  = X_v / A_c                        per unit volume velocity
      X_net = conj(X_U)                       exp(+j omega t)

  so ``H_net[f,c,p,a] = conj(channel_pressure[f,c,p,a] * (-1j*w) / A_c)`` (Pa per m^3/s) and
  ``Z_net[f,i,j] = conj(impedance_matrix[f,i,j] * (-1j*w) / A_j)`` (Pa per m^3/s).
* Channel 0 is the CD (tag 2); channels 1..E are entry groups. Coupling is exact for lumped entries::

      U_e = solve(I + Y_ee Z_ee, u_sc - Y_ee Z_e0 U_cd)
      U   = [U_cd, U_1, ..., U_E]

The reference implementations are ``calc/meh_1d_sketch.py`` (Entry.norton) and
``calc/meh_zmatrix_check.py`` (bare-horn decomposition); the tests import those by file path.
"""
from __future__ import annotations

import numpy as np

from ..constants import C_AIR, RHO_AIR

__all__ = [
    "from_bem",
    "entry_norton",
    "cd_volume_velocity",
    "couple",
    "cone_velocity_rms",
    "cone_excursion_peak_mm",
    "port_velocity_peak",
]

RHO_C2 = RHO_AIR * C_AIR ** 2


def _entry_parts(w, cone, v_front_m3, s_port_m2, l_neck_m, v_rear_m3, n_end, q_port):
    """The frequency-dependent impedances of one driver (C7), shared by the public entry functions."""
    ze = cone.re_ohm + 1j * w * cone.le_h
    zm = (cone.rms_kg_s + 1j * w * cone.mmd_eff_kg + 1.0 / (1j * w * cone.cms_m_per_n)
          + cone.bl_tm ** 2 / ze)
    z_cone = zm / cone.sd_m2 ** 2 + 1.0 / (1j * w * v_rear_m3 / RHO_C2)
    z_cf = 1.0 / (1j * w * v_front_m3 / RHO_C2)
    r_eq = np.sqrt(s_port_m2 / np.pi)
    l_eff = l_neck_m + n_end * 0.85 * r_eq
    x_port = w * RHO_AIR * l_eff / s_port_m2
    z_port = 1j * x_port + x_port / q_port
    return ze, z_cone, z_cf, z_port


def entry_norton(f, cone, n, v_front_m3, s_port_m2, l_neck_m, v_rear_m3, e_volts,
                 n_end=1, q_port=10.0):
    """Norton equivalent ``(u_sc, y)`` of ``n`` identical drivers at one entry station (C7).

    ``u_sc`` [m^3/s] is the short-circuit volume velocity and ``y`` [m^3/(s Pa)] the admittance seen by the
    horn at the port. ``e_volts`` is the per-driver drive voltage (complex, after DSP); it may be a scalar
    or an array broadcastable to ``f``. ``n_end=1`` when the horn-side radiation mass is already in
    ``Z_net`` (BEM); ``n_end=2`` reproduces the 1-D sketch, whose horn node has no radiation mass.
    """
    f = np.asarray(f, dtype=np.float64)
    e = np.asarray(e_volts, dtype=np.complex128)
    f, e = np.broadcast_arrays(f, e)
    w = 2.0 * np.pi * f

    ze, z_cone, z_cf, z_port = _entry_parts(
        w, cone, v_front_m3, s_port_m2, l_neck_m, v_rear_m3, n_end, q_port
    )
    p_s = cone.bl_tm * e / (ze * cone.sd_m2)
    z_par = z_cf * z_cone / (z_cf + z_cone)
    p_th = p_s * z_cf / (z_cf + z_cone)
    z_th = z_port + z_par
    u_sc = np.asarray(n * p_th / z_th, dtype=np.complex128)
    y = np.asarray(n / z_th, dtype=np.complex128)
    return u_sc, y


def cd_volume_velocity(f, cd, gain):
    """CD throat volume velocity [m^3/s] (C7): ``gain * S_exit / (j w) * HP2(f; fs_cd, q_cd)``.

    ``gain`` is the CD channel gain (DSP) in the same acceleration basis the BEM uses; ``HP2`` is the
    second-order high-pass ``s^2/(s^2 + s/q + 1)``, ``s = j f / fs_cd`` (``calc/meh_1d_study.py::cd_u``).
    """
    f = np.asarray(f, dtype=np.float64)
    w = 2.0 * np.pi * f
    s = 1j * f / cd.fs_cd_hz
    hp2 = s * s / (s * s + s / cd.q_cd + 1.0)
    return np.asarray(gain * cd.s_exit_m2 / (1j * w) * hp2, dtype=np.complex128)


def from_bem(resp):
    """Convert a BEM ``Response`` to network quantities ``(H_net, Z_net, freqs)`` (C6).

    ``H_net`` has shape ``(F, C, P, A)`` in Pa per m^3/s; ``Z_net`` has shape ``(F, C, C)`` in Pa per
    m^3/s with ``Z_net[f,i,j]`` the pressure at channel ``i`` due to volume velocity at channel ``j``.
    Requires the C5 fields ``channel_pressure``, ``impedance_matrix``, ``channel_tags`` and
    ``tag_areas_m2`` (all present on the MEH path of ``Response``).
    """
    cp = getattr(resp, "channel_pressure", None)
    im = getattr(resp, "impedance_matrix", None)
    tags = getattr(resp, "channel_tags", None)
    areas = getattr(resp, "tag_areas_m2", None)
    if cp is None or im is None or tags is None or areas is None:
        raise ValueError(
            "from_bem: the response has no MEH channel fields "
            "(channel_pressure, impedance_matrix, channel_tags, tag_areas_m2)"
        )

    freqs = np.asarray(resp.freqs_hz, dtype=np.float64)
    cp = np.asarray(cp, dtype=np.complex128)
    im = np.asarray(im, dtype=np.complex128)
    tags = tuple(int(t) for t in tags)
    n_f, n_c = freqs.size, len(tags)
    if cp.ndim != 4 or cp.shape[0] != n_f or cp.shape[1] != n_c:
        raise ValueError(f"from_bem: channel_pressure must be (F={n_f}, C={n_c}, P, A), got {cp.shape}")
    if im.shape != (n_f, n_c, n_c):
        raise ValueError(f"from_bem: impedance_matrix must be ({n_f}, {n_c}, {n_c}), got {im.shape}")
    try:
        area_c = np.asarray([float(areas[t]) for t in tags], dtype=np.float64)
    except KeyError as exc:
        raise ValueError(f"from_bem: tag_areas_m2 has no area for tag {exc.args[0]}") from None
    if np.any(~np.isfinite(area_c)) or np.any(area_c <= 0.0):
        raise ValueError(f"from_bem: every channel area must be finite and > 0, got {area_c}")

    w = 2.0 * np.pi * freqs
    factor = -1j * w
    # H_net[f,c,p,a] = conj(channel_pressure * (-j w) / A_c)
    h_net = np.conj(cp * factor[:, None, None, None] / area_c[None, :, None, None])
    # Z_net[f,i,j] = conj(impedance_matrix * (-j w) / A_j)
    z_net = np.conj(im * factor[:, None, None] / area_c[None, None, :])
    return h_net.astype(np.complex128), z_net.astype(np.complex128), freqs


def _as_fx(value, n_f: int, n_e: int) -> np.ndarray:
    """Broadcast a scalar / ``(E,)`` / ``(F,E)`` value to ``(F, E)`` complex128."""
    arr = np.asarray(value, dtype=np.complex128)
    if arr.ndim == 0:
        return np.full((n_f, n_e), arr, dtype=np.complex128)
    return np.array(np.broadcast_to(arr, (n_f, n_e)), dtype=np.complex128)


def couple(Z_net, u_sc, y, u_cd):
    """Couple the CD and entry Norton sources to the bare-horn impedance (C6).

    ``Z_net`` is ``(F, C, C)`` (channel 0 = CD), ``u_sc`` and ``y`` are the entry-group Norton values,
    shaped ``(E,)`` or ``(F, E)``, and ``u_cd`` is ``(F,)`` or a scalar. Returns ``U`` of shape ``(F, C)``
    with ``U[:, 0] = u_cd`` and the solved entry volume velocities in the remaining columns.
    """
    z = np.asarray(Z_net, dtype=np.complex128)
    if z.ndim == 2:
        z = z[None, ...]
    if z.ndim != 3 or z.shape[1] != z.shape[2] or z.shape[1] < 1:
        raise ValueError(f"couple: Z_net must be (F, C, C) with C >= 1, got {z.shape}")
    n_f, n_c = z.shape[0], z.shape[1]
    n_e = n_c - 1

    ucd = np.asarray(u_cd, dtype=np.complex128)
    if ucd.ndim == 0:
        ucd = np.full(n_f, ucd, dtype=np.complex128)
    else:
        ucd = np.array(np.broadcast_to(ucd, (n_f,)), dtype=np.complex128)

    u = np.zeros((n_f, n_c), dtype=np.complex128)
    u[:, 0] = ucd
    if n_e:
        u_sc = _as_fx(u_sc, n_f, n_e)
        y = _as_fx(y, n_f, n_e)
        z_ee = z[:, 1:, 1:]
        z_e0 = z[:, 1:, 0]
        a_mat = np.eye(n_e, dtype=np.complex128)[None, :, :] + y[:, :, None] * z_ee
        rhs = u_sc - y * z_e0 * ucd[:, None]
        u[:, 1:] = np.linalg.solve(a_mat, rhs[..., None])[..., 0]
    return u


def cone_velocity_rms(f, cone, n, v_front_m3, s_port_m2, l_neck_m, v_rear_m3, e_volts, p_horn,
                      n_end=1, q_port=10.0):
    """RMS diaphragm velocity [m/s] per driver given the horn pressure at the port (C7).

    Mirrors ``calc/meh_1d_sketch.py::Entry.cone_velocity``: the port volume velocity is
    ``U_out = (u_sc - p_horn * y) / n``, the cone-front pressure ``p_c = p_horn + U_out * Zport`` and the
    diaphragm velocity ``v = (p_s - p_c) / Zcone / Sd``.
    """
    f = np.asarray(f, dtype=np.float64)
    e = np.asarray(e_volts, dtype=np.complex128)
    p_horn = np.asarray(p_horn, dtype=np.complex128)
    f, e, p_horn = np.broadcast_arrays(f, e, p_horn)
    w = 2.0 * np.pi * f

    ze, z_cone, _z_cf, z_port = _entry_parts(
        w, cone, v_front_m3, s_port_m2, l_neck_m, v_rear_m3, n_end, q_port
    )
    p_s = cone.bl_tm * e / (ze * cone.sd_m2)
    u_sc, y = entry_norton(f, cone, n, v_front_m3, s_port_m2, l_neck_m, v_rear_m3, e,
                           n_end=n_end, q_port=q_port)
    u_out = (u_sc - p_horn * y) / n
    p_c = p_horn + u_out * z_port
    u_d = (p_s - p_c) / z_cone
    return np.asarray(u_d / cone.sd_m2, dtype=np.complex128)


def cone_excursion_peak_mm(f, v_rms_mps):
    """Peak (0-to-peak) diaphragm excursion [mm] from an RMS velocity [m/s] (C11 limitation)."""
    f, v = np.broadcast_arrays(
        np.asarray(f, dtype=np.float64),
        np.asarray(v_rms_mps, dtype=np.complex128),
    )
    w = 2.0 * np.pi * f
    return np.asarray(np.sqrt(2.0) * np.abs(v) / w * 1e3, dtype=np.float64)


def port_velocity_peak(u_rms_m3_s, s_port_m2):
    """Peak particle velocity [m/s] in one port from its RMS volume velocity [m^3/s] and area [m^2]."""
    u = np.asarray(u_rms_m3_s, dtype=np.complex128)
    return np.asarray(np.sqrt(2.0) * np.abs(u) / float(s_port_m2), dtype=np.float64)
