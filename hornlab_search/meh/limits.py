"""Maximum-SPL limits for a synthesised MEH system (contract C11).

``spl_max(f, solution, brief_meh)`` answers: how loud can the system play before the FIRST physical
limit is hit? All channels scale linearly with input, so every constraint is a maximum admissible
global scale factor and the smallest one wins at each frequency. The five C11 limits are:

``excursion``  per-driver cone peak excursion <= ``Xmax``
``power``      per-driver electrical power ``|e|^2 / Re`` <= ``p_aes_w``
``port``       per-port peak particle velocity <= ``port_air_mps_max``
``amp``        per-driver RMS drive voltage <= ``amp_v_rms``
``cd_power``   CD output <= ``sens_db_1w + 10 log10(p_aes_w) + (DI_ours - di_ref_db)``

The per-frequency nominal state (SPL, cone velocity, port velocity, drive voltage at the solution's
own gains) is cached on the solution by :func:`hornlab_search.meh.synthesis.nominal_state`; if it is
absent but ``solution.response`` is set, it is computed here. ``return_limits=True`` also returns the
binding label per frequency, so a run can report which limit governs each band.
"""
from __future__ import annotations

import numpy as np

from .synthesis import nominal_state, solution_drivers

__all__ = ["spl_max", "binding_limits", "LIMIT_NAMES"]

#: The five C11 limit names, in the order they are evaluated (CD last).
LIMIT_NAMES = ("excursion", "power", "port", "amp", "cd_power")

_MISSING = object()


def _get(obj, name, default=_MISSING):
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


def _brief(brief, name, default=_MISSING):
    """Read a ``meh:`` block value (dict or object attribute)."""
    return _get(brief, name, default)


def _scale(num, den) -> np.ndarray:
    """``num/den`` with a non-positive or non-finite denominator meaning 'no constraint'."""
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.asarray(num, dtype=np.float64) / np.asarray(den, dtype=np.float64)
    return np.where(np.isfinite(s) & (s >= 0.0), s, np.inf)


def _resample_state(state: dict, f: np.ndarray) -> dict:
    """Linearly interpolate a nominal state in log-frequency onto the requested grid."""
    src = np.asarray(state["freqs_hz"], dtype=np.float64)
    if src.shape == f.shape and np.allclose(src, f):
        return state
    if np.any(f <= 0.0) or np.any(src <= 0.0):
        raise ValueError("spl_max: frequencies must be > 0")
    lf = np.log(f)
    out = {"freqs_hz": f}
    for key in ("spl_ref_db", "spl_channel_db", "excursion_peak_mm", "electrical_power_w",
                "port_velocity_mps", "drive_v_rms"):
        a = np.asarray(state[key], dtype=np.float64)
        if a.ndim == 1:
            out[key] = np.interp(lf, np.log(src), a)
        else:
            out[key] = np.column_stack(
                [np.interp(lf, np.log(src), a[:, j]) for j in range(a.shape[1])])
    return out


def _combine(state: dict, solution, brief_meh) -> tuple[np.ndarray, np.ndarray]:
    cd, mid = solution_drivers(solution)
    spl_ref = np.asarray(state["spl_ref_db"], dtype=np.float64)
    spl_ch = np.asarray(state["spl_channel_db"], dtype=np.float64)
    n_f, n_c = spl_ch.shape

    amp_v = float(_brief(brief_meh, "amp_v_rms", 40.0))
    port_max = float(_brief(brief_meh, "port_air_mps_max", 17.0))

    scales: list[np.ndarray] = []
    labels: list[str] = []

    if n_c > 1:
        exc = np.asarray(state["excursion_peak_mm"], dtype=np.float64)
        power = np.asarray(state["electrical_power_w"], dtype=np.float64)
        port_v = np.asarray(state["port_velocity_mps"], dtype=np.float64)
        drive_v = np.asarray(state["drive_v_rms"], dtype=np.float64)
        for c in range(1, n_c):
            scales.append(_scale(mid.xmax_mm, exc[:, c]))
            labels.append("excursion")
            scales.append(_scale(np.sqrt(mid.p_aes_w), np.sqrt(power[:, c])))
            labels.append("power")
            scales.append(_scale(port_max, port_v[:, c]))
            labels.append("port")
            scales.append(_scale(amp_v, drive_v[:, c]))
            labels.append("amp")

    # CD power: the estimate is already an SPL, so its scale follows from the CD channel's own
    # on-axis contribution at the nominal drive.
    di = _get(solution, "di_db", None)
    if di is None:
        di_arr = np.full(n_f, float(cd.di_ref_db), dtype=np.float64)
    else:
        di_arr = np.asarray(di, dtype=np.float64).ravel()
        if di_arr.size != n_f:
            di_arr = np.full(n_f, float(cd.di_ref_db), dtype=np.float64)
    cd_limit_db = (float(cd.sens_db_1w) + 10.0 * np.log10(float(cd.p_aes_w))
                   + (di_arr - float(cd.di_ref_db)))
    scales.append(10.0 ** ((cd_limit_db - spl_ch[:, 0]) / 20.0))
    labels.append("cd_power")

    stack = np.column_stack(scales).astype(np.float64)
    stack = np.where(np.isfinite(stack) & (stack > 0.0), stack, np.inf)
    pick = np.argmin(stack, axis=1)
    scale = stack[np.arange(n_f), pick]
    with np.errstate(divide="ignore"):
        db = spl_ref + 20.0 * np.log10(scale)
    return db, np.asarray(labels, dtype=object)[pick]


def spl_max(f, solution, brief_meh, *, return_limits: bool = False):
    """Maximum SPL [dB re 20 uPa] per frequency before the first C11 limit, and its label.

    ``f`` is the requested frequency grid. Every channel is assumed to scale together (the C11
    input-level definition); the result is the nominal system SPL plus ``20 log10(s_min)`` where
    ``s_min`` is the smallest admissible global scale over all channels and limits. With
    ``return_limits=True`` returns ``(db, labels)`` where ``labels[i]`` is one of
    :data:`LIMIT_NAMES`; otherwise returns just ``db``.
    """
    f = np.asarray(f, dtype=np.float64)
    if f.ndim != 1 or f.size == 0:
        raise ValueError(f"spl_max: f must be a non-empty 1-D array, got {f.shape}")

    state = _get(solution, "nominal_state", None)
    if state is None:
        resp = _get(solution, "response", None)
        if resp is None:
            raise ValueError(
                "spl_max: solution has neither a cached nominal_state nor a solved response")
        state = nominal_state(resp, solution)
    else:
        if "freqs_hz" not in state:
            raise ValueError("spl_max: a cached nominal_state must carry 'freqs_hz'")

    state = _resample_state(state, f)
    db, labels = _combine(state, solution, brief_meh)
    if return_limits:
        return db, labels
    return db


def binding_limits(f, solution, brief_meh) -> np.ndarray:
    """The C11 limit that binds at each frequency (shorthand for ``spl_max(..., return_limits)``)."""
    return spl_max(f, solution, brief_meh, return_limits=True)[1]
