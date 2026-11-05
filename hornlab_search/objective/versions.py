"""The objective dispatch versions this build can score - one source of truth.

``search/evaluate.py`` dispatches only on a version in this tuple, and
``dataset/record.py`` refuses to record anything else. Add a new version HERE in the
same commit as its dispatch branch; ``search/evaluate.py`` checks at import that its
dispatch table has exactly these keys, so neither side can drift silently.
"""
from __future__ import annotations

#: 1 = the original objective; 2 = detrended terms (2026-10-24); 3 = per-plane ``f0_v``
#: plus the K-law ``f0`` mask (2026-10-26). 4 = tolerance-normalised terms plus asymmetric
#: coverage, DI standard deviation and the diagonal term (2026-10-27, ``objective/scalar_v4.py``).
#: 5 = the MEH system objective: v4's pattern terms on the synthesised response plus lw_resid,
#: notch, xo_lob and headroom (2026-10-30, ``objective/scalar_meh.py``).
#: 6 = loading_smooth (Le Cléac'h / rollback class): load_near, z_smooth, cov_pat, di_rise
#: (2026-11-05, ``objective/scalar_v6.py``).
SUPPORTED_OBJECTIVE_VERSIONS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)


def is_supported_objective_version(value: object) -> bool:
    """True for a real int in :data:`SUPPORTED_OBJECTIVE_VERSIONS`.

    ``True``/``False`` are rejected even though Python treats them as ints: a bool is not a
    version number, and an accidental ``True`` must not silently validate as v1.
    """
    return (isinstance(value, int) and not isinstance(value, bool)
            and value in SUPPORTED_OBJECTIVE_VERSIONS)
