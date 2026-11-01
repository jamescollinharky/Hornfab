"""The Backend protocol, the backend factory, and the helpers every adapter shares.

The protocol is the expansion seam (05_TASK_SOLVE): a third backend is a new file plus one
line in ``get_backend``. Nothing here imports a solver at module level, so this module is
importable (and its tests run) with nothing installed but numpy.

Conventions every adapter must produce (01_CONTRACTS sections 7 and 9):

* cuts are in dB, ascending ``-90..+90`` with an EXACT 0 (``arc_angles_deg``);
* ``+angle`` on the horizontal cut is toward ``+X``, on the vertical cut toward ``+Y``
  (verified in ``BeatEngineDriver.jl::polar_observation_points``: H = (R sin a, 0, R cos a),
  V = (0, R sin a, R cos a));
* the balloon is a theta-major (theta from +Z, phi from +X) grid. A theta-phi grid is NOT an
  equal-area grid: ``Response.meta['balloon_grid']`` carries ``[n_theta, n_phi]`` and every
  consumer must weight by ``sin(theta)`` (``metrics.di.sin_theta_weights``).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from ..constants import REF_P
from ..types import Backend as _ContractBackend
from ..types import BackendUnavailableError, Response

log = logging.getLogger("hornlab_search.solve.base")

BACKEND_NAMES: tuple[str, ...] = ("beat_cuda", "beat_metal", "beat_cpu", "bempp_cpu")

#: Plausible absolute SPL band for any cut sample. Outside it the array is mis-sliced,
#: mis-scaled or silent, never a real horn. (05_TASK_SOLVE `_to_response` assertion 4.)
SPL_PLAUSIBLE_DB = (-200.0, 200.0)

#: Two evaluations of the SAME physical point (H and V cut at 0 deg) must agree to this.
ON_AXIS_AGREE_DB = 1e-6


@runtime_checkable
class Backend(_ContractBackend, Protocol):
    """``types.Backend`` made ``runtime_checkable`` so ``isinstance(x, Backend)`` works.

    Members: ``name: str``, ``available() -> (bool, str)``, ``warm()``,
    ``solve(mesh, spec) -> SolveOutcome``, ``release()``.
    """


class ResponseSanityError(ValueError):
    """An adapter was about to return a Response that cannot be right. Raised, never returned."""


# ------------------------------------------------------------------ angles


def arc_angles_deg(angle_count: int) -> np.ndarray:
    """Ascending, -90 to +90 inclusive, with an EXACT 0 at index ``(angle_count-1)//2``.

    Raises ``ValueError`` if ``angle_count`` is even (no on-axis sample) or below 3.
    The end points are set exactly (not by multiplication) so ``a[0] == -90.0`` and
    ``a[-1] == 90.0`` hold for every odd count, and the grid is exactly antisymmetric.
    """
    n = int(angle_count)
    if n != angle_count:
        raise ValueError(f"angle_count must be an integer, got {angle_count!r}")
    if n % 2 == 0:
        raise ValueError(f"angle_count must be odd so 0 deg is an exact sample, got {n}")
    if n < 3:
        raise ValueError(f"angle_count must be at least 3 to span -90..+90, got {n}")
    half = (n - 1) // 2
    step = 90.0 / half
    a = np.arange(-half, half + 1, dtype=float) * step
    a[0], a[-1], a[half] = -90.0, 90.0, 0.0
    return a


# ------------------------------------------------------------------ balloon


def balloon_grid_shape(points: int) -> tuple[int, int]:
    """(n_theta, n_phi) for a theta-major grid of about ``points`` samples, n_phi ~ 2 n_theta.

    512 -> (16, 32) exactly (the shape TOOLCHAIN M3 measured); 1024 -> (23, 45) = 1035 points.
    The achieved count is ``n_theta * n_phi`` and is recorded in ``Response.meta``.
    """
    p = int(points)
    if p < 6:
        raise ValueError(f"balloon_points must be at least 6, got {points!r}")
    n_theta = max(2, int(round(np.sqrt(p / 2.0))))
    n_phi = max(3, int(round(p / n_theta)))
    return n_theta, n_phi


def balloon_dirs_from_angles(theta_deg: np.ndarray, phi_deg: np.ndarray) -> np.ndarray:
    """(n, 3) unit vectors; theta from +Z, phi from +X toward +Y (the solver's own convention)."""
    t = np.radians(np.asarray(theta_deg, dtype=float).ravel())
    p = np.radians(np.asarray(phi_deg, dtype=float).ravel())
    if t.shape != p.shape:
        raise ValueError(f"theta {t.shape} and phi {p.shape} must have the same shape")
    d = np.column_stack([np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)])
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def theta_deg_from_dirs(dirs: np.ndarray) -> np.ndarray:
    """Polar angle from +Z in degrees for (n, 3) unit vectors. Feed to ``sin_theta_weights``."""
    d = np.asarray(dirs, dtype=float)
    return np.degrees(np.arccos(np.clip(d[:, 2], -1.0, 1.0)))


def spl_from_pressure(p: np.ndarray) -> np.ndarray:
    """Absolute dB SPL re 20 uPa of a complex pressure array. -inf where p == 0 (caller checks)."""
    with np.errstate(divide="ignore"):
        return 20.0 * np.log10(np.abs(np.asarray(p)) / REF_P)


# ------------------------------------------------------------------ band-split stacking

def stack_responses(responses: list[Response], freqs_hz) -> Response:
    """Concatenate per-band ``Response``s into one, in strictly increasing frequency order.

    WP8 requirement: ``freqs_hz`` is the WHOLE mode grid, and the concatenated band frequencies
    must equal it exactly once (no gap, no overlap). Per-band arrays are concatenated along the
    frequency axis; the observation grids and balloon directions must agree. Optional arrays are
    either present on every band or on none. ``meta`` is the first band's, with timings summed and
    the partial/cancelled/requested-count flags made conservative.
    """
    if not responses:
        raise ValueError("stack_responses: no responses")
    want = np.asarray(list(freqs_hz), dtype=float)
    if want.ndim != 1 or want.size == 0:
        raise ValueError("stack_responses: freqs_hz must be a non-empty 1-D sequence")
    if not np.all(np.diff(want) > 0):
        raise ValueError("stack_responses: freqs_hz must be strictly increasing")

    first = responses[0]
    h_ang = np.asarray(first.h_angles_deg, dtype=float)
    v_ang = np.asarray(first.v_angles_deg, dtype=float)
    parts = []
    for i, r in enumerate(responses):
        f = np.asarray(r.freqs_hz, dtype=float)
        if f.ndim != 1 or f.size == 0:
            raise ValueError(f"stack_responses: band {i} has no frequencies")
        if not np.array_equal(np.asarray(r.h_angles_deg, dtype=float), h_ang) or \
                not np.array_equal(np.asarray(r.v_angles_deg, dtype=float), v_ang):
            raise ValueError(f"stack_responses: band {i} observation grid differs from band 0")
        if np.asarray(r.spl_h_db).shape != (f.size, h_ang.size) or \
                np.asarray(r.spl_v_db).shape != (f.size, v_ang.size):
            raise ValueError(f"stack_responses: band {i} cut arrays do not match its frequencies")
        parts.append(f)
    got = np.concatenate(parts)
    if not np.array_equal(got, want):
        raise ValueError(
            f"stack_responses: band frequencies {got.tolist()} do not tile the requested grid "
            f"{want.tolist()} exactly once (gap, overlap or wrong order)")

    def cat(name):
        vals = [getattr(r, name) for r in responses]
        if all(v is None for v in vals):
            return None
        if any(v is None for v in vals):
            raise ValueError(f"stack_responses: '{name}' is present on some bands only")
        return np.concatenate([np.asarray(v) for v in vals], axis=0)

    dirs = first.balloon_dirs
    for i, r in enumerate(responses):
        if (dirs is None) != (r.balloon_dirs is None):
            raise ValueError(f"stack_responses: band {i} balloon availability differs")
        if dirs is not None and not np.array_equal(np.asarray(r.balloon_dirs), np.asarray(dirs)):
            raise ValueError(f"stack_responses: band {i} balloon directions differ")

    backends = {str(r.backend) for r in responses if r.backend}
    if len(backends) > 1:
        raise ValueError(f"stack_responses: mixed backends {sorted(backends)}")
    n_dofs = [r.n_dof for r in responses if r.n_dof is not None]

    meta = dict(first.meta or {})
    timings: dict[str, float] = {}
    for r in responses:
        for k, v in ((r.meta or {}).get("timings") or {}).items():
            timings[k] = timings.get(k, 0.0) + float(v)
    if timings:
        meta["timings"] = timings
    meta["requested_frequency_count"] = int(sum(
        int((r.meta or {}).get("requested_frequency_count") or np.asarray(r.freqs_hz).size)
        for r in responses))
    meta["is_partial"] = any(bool((r.meta or {}).get("is_partial")) for r in responses)
    meta["cancelled"] = any(bool((r.meta or {}).get("cancelled")) for r in responses)

    return Response(
        freqs_hz=want.copy(),
        h_angles_deg=h_ang.copy(),
        v_angles_deg=v_ang.copy(),
        spl_h_db=cat("spl_h_db"),
        spl_v_db=cat("spl_v_db"),
        balloon_dirs=None if dirs is None else np.asarray(dirs).copy(),
        spl_balloon_db=cat("spl_balloon_db"),
        z_throat=cat("z_throat"),
        p_h=cat("p_h"),
        p_v=cat("p_v"),
        p_balloon=cat("p_balloon"),
        backend=next(iter(backends), ""),
        n_dof=max(n_dofs) if n_dofs else None,
        meta=meta,
    )


# ------------------------------------------------------------------ sanity


def check_cuts(freqs_hz, angle_count: int, spl_h: np.ndarray, spl_v: np.ndarray,
               *, what: str = "response") -> None:
    """The `_to_response` assertions that apply to any backend. Raises ``ResponseSanityError``.

    * shapes are ``(nf, angle_count)``
    * no NaN, no inf
    * within ``SPL_PLAUSIBLE_DB``
    * the on-axis samples of the two cuts agree to ``ON_AXIS_AGREE_DB`` (same physical point)
    """
    nf = len(freqs_hz)
    want = (nf, int(angle_count))
    for name, a in (("spl_h_db", spl_h), ("spl_v_db", spl_v)):
        a = np.asarray(a)
        if a.shape != want:
            raise ResponseSanityError(
                f"{what}: {name} has shape {a.shape}, expected {want} "
                f"(n_freqs, angle_count): a transposed or mis-sliced array")
        if not np.all(np.isfinite(a)):
            bad = int(np.count_nonzero(~np.isfinite(a)))
            raise ResponseSanityError(f"{what}: {name} has {bad} non-finite value(s) (NaN or inf)")
        lo, hi = SPL_PLAUSIBLE_DB
        if a.min() < lo or a.max() > hi:
            raise ResponseSanityError(
                f"{what}: {name} range [{a.min():.3g}, {a.max():.3g}] dB is outside the "
                f"plausible [{lo:.0f}, {hi:.0f}] dB band")
    ax = (int(angle_count) - 1) // 2
    d = float(np.max(np.abs(np.asarray(spl_h)[:, ax] - np.asarray(spl_v)[:, ax])))
    if d > ON_AXIS_AGREE_DB:
        raise ResponseSanityError(
            f"{what}: on-axis sample of the H and V cuts disagree by {d:.3e} dB "
            f"(> {ON_AXIS_AGREE_DB:g}); they are the same physical point, so a cut is "
            f"mis-sliced, mis-ordered or evaluated at a different point")


# ------------------------------------------------------------------ failure classification

_OOM = re.compile(r"out of (gpu )?memory|CUDA_ERROR_OUT_OF_MEMORY|OutOfGPUMemory|OOM\b|"
                  r"failed to allocate|cannot allocate", re.I)
_WORKER_EXIT = re.compile(r"solver exited|worker exited|exited with code|ConnectionReset|"
                          r"BrokenPipe|worker host|stream ended without|EOF", re.I)


def classify_failure(message: str) -> str:
    """'cuda_oom' | 'worker_exit' | 'other', from an exception's text."""
    m = str(message)
    if _OOM.search(m):
        return "cuda_oom"
    if _WORKER_EXIT.search(m):
        return "worker_exit"
    return "other"


_NOTED: set[str] = set()


def default_notes_path() -> Path:
    return Path(__file__).resolve().parents[2] / "NOTES_FOR_SENIOR.md"


def note_failure_for_senior(kind: str, detail: str, *, context: str = "",
                            notes_path: Path | None = None, once_per_process: bool = True) -> bool:
    """Append a dated block to NOTES_FOR_SENIOR.md (append only). 01_CONTRACTS section 15:
    a CUDA OOM means the dof cap in TOOLCHAIN.md is wrong, and a human must hear about it.

    Returns True if a block was written. Never raises: a notes failure must not kill a search.
    Written at most once per (process, kind) so a run that OOMs a hundred times writes one block.
    """
    try:
        if once_per_process and kind in _NOTED:
            return False
        path = Path(notes_path) if notes_path is not None else default_notes_path()
        if not path.exists():
            return False
        _NOTED.add(kind)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        text = (f"\n## {stamp}  task-05  runtime {kind}: {context or 'solve failure'}\n"
                f"What happened: {detail[:1500]}\n"
                + ("What it means: the dof cap in TOOLCHAIN.md / the YAML is wrong for this GPU state "
                   "(or a stale Julia host held VRAM; run solve.worker.clear_stale_hosts and re-test "
                   "from a clean state before changing the cap, AGENTS.md hygiene rule 7).\n"
                   if kind == "cuda_oom" else "")
                + "(Appended automatically by hornlab_search.solve.base.note_failure_for_senior.)\n")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(text)
        return True
    except Exception:  # pragma: no cover - best effort by design
        log.exception("could not append the failure note")
        return False


def reset_noted() -> None:
    """Forget which failure kinds were already written (tests)."""
    _NOTED.clear()


# ------------------------------------------------------------------ json helpers


def jsonable(obj, *, max_array: int = 4096):
    """Recursively turn numpy scalars/arrays and tuples into JSON-native types.

    Arrays longer than ``max_array`` elements are replaced by a short descriptor string, so a
    stray big array can never bloat ``Response.meta`` or break its JSON round trip.
    """
    if isinstance(obj, dict):
        return {str(k): jsonable(v, max_array=max_array) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v, max_array=max_array) for v in obj]
    if isinstance(obj, np.ndarray):
        if obj.size > max_array:
            return f"<ndarray shape={obj.shape} dtype={obj.dtype}>"
        if np.iscomplexobj(obj):
            return {"real": obj.real.tolist(), "imag": obj.imag.tolist()}
        return obj.tolist()
    if isinstance(obj, np.generic):
        return jsonable(obj.item())
    if isinstance(obj, complex):
        return {"real": obj.real, "imag": obj.imag}
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    if isinstance(obj, Path):
        return str(obj)
    return repr(obj)


def meta_roundtrips(meta: dict) -> bool:
    """True if ``meta`` survives json dumps/loads unchanged (what cache.store requires)."""
    try:
        return json.loads(json.dumps(meta)) == meta
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------------ factory


def get_backend(name: str, **kwargs) -> Backend:
    """'beat_cuda' | 'beat_metal' | 'beat_cpu' | 'bempp_cpu'. Raises ``BackendUnavailableError``
    with the reason from ``available()`` if the backend cannot run, and for an unknown name.

    Extra keyword arguments (``timeout_s``, ``track_vram``, ``cuda_fused``) are passed to the
    beat adapter when applicable.
    """
    if name not in BACKEND_NAMES:
        raise BackendUnavailableError(f"unknown backend {name!r}; expected one of {list(BACKEND_NAMES)}")
    if name in ("beat_cuda", "beat_metal", "beat_cpu"):
        from .beat import BeatBackend
        be = BeatBackend(name.split("_", 1)[1], **kwargs)
    else:
        from .bempp import BemppBackend
        be = BemppBackend(**kwargs)
    ok, why = be.available()
    if not ok:
        raise BackendUnavailableError(f"backend {name!r} is not available: {why}")
    return be
