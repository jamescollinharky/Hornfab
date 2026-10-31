"""DSP building blocks for MEH channel drives (contract C11/C12).

Every function here evaluates an **analog prototype in ``s``** with ``s = j f / fc`` (the
``exp(+j omega t)`` network convention of :mod:`hornlab_search.meh.network`), so a complex
drive returned by this module can be multiplied straight into a network volume velocity ``U``.

Filters
-------
``lr``          Linkwitz-Riley of order 2, 4 or 8 = (Butterworth of order ``order/2``) squared.
                An LR4 low-pass plus its high-pass sums to an all-pass of unit magnitude, which
                is the property the DSP tests pin.
``peaking``     a peaking biquad (analog prototype), gain at ``fc`` equal to ``gain_db``.

Housekeeping
------------
``delay``       a physical delay ``tau`` in the ``exp(+j omega t)`` convention: ``exp(-j w tau)``.
``polarity``    +1 / -1 as the trivial ``0`` / ``pi`` phase.
``smooth_oct``  fractional-octave power smoothing on a log grid.
``system_eq``   the C11 system EQ: ``clip(mean(LW) - S3(LW), -inf, max_boost_db)``.

The functions keep the input shape (scalars give 0-d arrays) and always return ``complex128``
for the drive/filter helpers.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "lr",
    "delay",
    "polarity",
    "peaking",
    "smooth_oct",
    "system_eq",
]

_TWO_PI = 2.0 * np.pi


def _freq(f) -> np.ndarray:
    return np.asarray(f, dtype=np.float64)


def _butterworth_poles(order: int) -> np.ndarray:
    """Left-half-plane poles of the normalised analog Butterworth polynomial of ``order``."""
    k = np.arange(order, dtype=np.float64)
    return np.exp(1j * np.pi * (2.0 * k + order + 1.0) / (2.0 * order))


def _lr_split(f: np.ndarray, fc: float, order: int) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(order, bool) or int(order) != order or int(order) < 2 or int(order) % 2:
        raise ValueError(f"lr: order must be an even integer >= 2, got {order!r}")
    if not (np.isfinite(fc) and float(fc) > 0.0):
        raise ValueError(f"lr: fc must be finite and > 0, got {fc!r}")
    order = int(order)
    m = order // 2
    s = 1j * f / float(fc)
    # Monic Butterworth polynomial B(s) = prod(s - p); B(0) = 1 for the normalised poles.
    bw_den = np.ones_like(s, dtype=np.complex128)
    for p in _butterworth_poles(m):
        bw_den = bw_den * (s - p)
    bw_lp = 1.0 / bw_den
    bw_hp = s ** m / bw_den
    # Linkwitz-Riley = the Butterworth section squared (two cascaded identical sections).
    return (bw_lp * bw_lp).astype(np.complex128), (bw_hp * bw_hp).astype(np.complex128)


def lr(f, fc, order, kind) -> np.ndarray:
    """Linkwitz-Riley low/high-pass response at ``f`` for crossover ``fc`` and even ``order``.

    ``kind`` is ``"lp"`` / ``"low"`` or ``"hp"`` / ``"high"``. Orders 2, 4 and 8 are the supported
    Linkwitz-Riley alignments (squared Butterworth of order 1, 2 and 4); LR4 ``lp + hp`` is an
    all-pass of unit magnitude.
    """
    if kind in ("lp", "low", "lowpass"):
        pick = 0
    elif kind in ("hp", "high", "highpass"):
        pick = 1
    else:
        raise ValueError(f"lr: kind must be 'lp' or 'hp', got {kind!r}")
    lp, hp = _lr_split(_freq(f), fc, order)
    return lp if pick == 0 else hp


def delay(f, ms) -> np.ndarray:
    """Complex delay factor ``exp(-j 2 pi f tau)``, ``tau = ms * 1e-3`` (``exp(+j omega t)``).

    Positive ``ms`` is a physical delay; its unwrapped phase slope is ``-2 pi tau`` rad/Hz.
    """
    f = _freq(f)
    if not np.isfinite(ms):
        raise ValueError(f"delay: ms must be finite, got {ms!r}")
    return np.exp(-1j * _TWO_PI * f * (float(ms) * 1e-3)).astype(np.complex128)


def polarity(sign=1.0) -> np.ndarray:
    """Return ``+1`` or ``-1`` (a float or an array of them) after checking each is a polarity.

    ``mid_polarity`` in a :class:`NetworkSolution` is +1 or -1; anything else is a bug, not a gain.
    """
    a = np.asarray(sign, dtype=np.float64)
    if np.any(~np.isfinite(a)) or np.any(np.abs(np.abs(a) - 1.0) > 1e-12):
        raise ValueError(f"polarity: every value must be +1 or -1, got {sign!r}")
    return a


def peaking(f, fc, gain_db, q) -> np.ndarray:
    """Analog peaking biquad: unity at DC/Nyquist, ``gain_db`` at ``fc``, bandwidth set by ``q``.

    ``H(s) = (s^2 + (A/q) s + 1) / (s^2 + s/(A q) + 1)`` with ``A = 10^(gain_db/40)`` and
    ``s = j f/fc``; at ``s = j`` the ratio is ``A^2 = 10^(gain_db/20)``.
    """
    f = _freq(f)
    if not (np.isfinite(fc) and float(fc) > 0.0):
        raise ValueError(f"peaking: fc must be finite and > 0, got {fc!r}")
    if not (np.isfinite(q) and float(q) > 0.0):
        raise ValueError(f"peaking: q must be finite and > 0, got {q!r}")
    if not np.isfinite(gain_db):
        raise ValueError(f"peaking: gain_db must be finite, got {gain_db!r}")
    s = 1j * f / float(fc)
    a = 10.0 ** (float(gain_db) / 40.0)
    num = s * s + (a / float(q)) * s + 1.0
    den = s * s + s / (a * float(q)) + 1.0
    return np.asarray(num / den, dtype=np.complex128)


def smooth_oct(f, db, frac) -> np.ndarray:
    """Fractional-octave smoothing: power average in a ``+-frac/2`` octave window around each ``f``.

    ``frac = 1/3`` is third-octave smoothing. The window is ``[f / 2^(frac/2), f * 2^(frac/2)]``
    (inclusive); samples are power-averaged with equal weight, which is exact on a log grid.
    Non-finite input samples are ignored; a window with no finite sample returns ``nan``.
    """
    f = _freq(f)
    db = np.asarray(db, dtype=np.float64)
    if f.shape != db.shape:
        raise ValueError(f"smooth_oct: f {f.shape} and db {db.shape} must have the same shape")
    if db.ndim != 1:
        raise ValueError(f"smooth_oct: expected 1-D arrays, got {db.ndim}-D")
    if not (np.isfinite(frac) and float(frac) > 0.0):
        raise ValueError(f"smooth_oct: frac must be finite and > 0, got {frac!r}")
    frac = float(frac)
    half = 2.0 ** (frac / 2.0)
    power = 10.0 ** (db / 10.0)
    finite = np.isfinite(power)
    out = np.full(db.shape, np.nan, dtype=np.float64)
    for i, fi in enumerate(f):
        if not np.isfinite(fi) or not finite[i]:
            continue
        sel = finite & (f >= fi / half) & (f <= fi * half)
        if np.any(sel):
            out[i] = 10.0 * np.log10(float(np.mean(power[sel])))
    return out


def system_eq(lw_db, f, max_boost_db) -> np.ndarray:
    """C11 system EQ ``E = clip(mean(LW) - S3(LW), -inf, max_boost_db)``.

    ``S3`` is third-octave smoothing of the listening-window curve ``lw_db`` on the supplied
    frequency grid ``f``; ``mean(LW)`` is the mean of the finite samples. Boost is clipped at
    ``max_boost_db``; cut is unlimited (the FIR-equivalent EQ may pull peaks down without limit).
    The returned array is the dB correction to ADD to the LW curve.
    """
    lw = np.asarray(lw_db, dtype=np.float64)
    f = _freq(f)
    if lw.shape != f.shape or lw.ndim != 1:
        raise ValueError(f"system_eq: lw_db {lw.shape} and f {f.shape} must both be 1-D, equal")
    if not np.isfinite(max_boost_db):
        raise ValueError(f"system_eq: max_boost_db must be finite, got {max_boost_db!r}")
    smooth = smooth_oct(f, lw, 1.0 / 3.0)
    finite = np.isfinite(lw)
    if not np.any(finite):
        return np.full(lw.shape, np.nan, dtype=np.float64)
    ref = float(np.mean(lw[finite]))
    eq = ref - smooth
    return np.minimum(eq, float(max_boost_db)).astype(np.float64)
