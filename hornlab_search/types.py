"""Frozen data contracts. No new fields without a contract change."""
from __future__ import annotations

import hashlib, json
from dataclasses import dataclass, field, asdict
from typing import Literal, Protocol

import numpy as np

Mode = Literal["screen", "verify", "final"]
Family = Literal["OSSE", "R-OSSE", "ICW", "FREEFORM"]


def _hash(obj) -> str:
    """12 hex chars, stable across processes. ALWAYS hashlib, never hash()."""
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=float)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def _canon(d: dict) -> dict:
    out = {}
    for k, v in sorted(d.items()):
        if isinstance(v, (int, float)):
            out[k] = round(float(v), 9)
        elif isinstance(v, dict):
            out[k] = _canon(v)
        elif isinstance(v, (list, tuple)):
            out[k] = [round(float(x), 9) if isinstance(x, (int, float)) else x for x in v]
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------ design

@dataclass(frozen=True)
class Design:
    """One candidate, in the mesher's own parameter names and units.

    family picks which key set is legal. params holds ONLY that family's keys,
    in the mesher's units (mm and deg, per its _mm / _deg suffixes).
    Validation of key legality lives in design/families.py, not here.
    """
    family: Family
    params: dict

    def hash(self) -> str:
        return _hash({"family": self.family, "params": _canon(self.params)})


@dataclass(frozen=True)
class MeshSpec:
    """Everything that changes the mesh for a given Design."""
    epw: float                 # elements per wavelength
    f_max_hz: float            # the frequency the mesh must resolve
    quadrants: str             # "1234" | "12" | "14" | "1"
    max_triangles: int
    allow_large_mesh: bool = False

    def hash(self) -> str:
        return _hash(_canon(asdict(self)))


@dataclass
class MeshResult:
    path: str                  # the .msh on disk, in METRES
    n_triangles: int
    n_dof: int | None          # None until a solve reports p1_dof_count
    quadrants: str
    symmetry_plane: str | None # the matching solver flag
    res_mm: dict               # {throat, mouth, rear}
    bbox_m: tuple              # (xmin, ymin, zmin, xmax, ymax, zmax)
    seconds: float


# ------------------------------------------------------------------ solve

@dataclass(frozen=True)
class ObservationSpec:
    distance_m: float
    angle_count: int           # samples per cut, spanning -90..+90 inclusive
    balloon: bool
    balloon_points: int        # 0 when balloon is False

    def hash(self) -> str:
        return _hash(_canon(asdict(self)))


@dataclass(frozen=True)
class SolveSpec:
    mode: Mode
    freqs_hz: tuple[float, ...]
    backend: str               # "beat_cuda" | "beat_metal" | "beat_cpu" | "bempp_cpu"
    observation: ObservationSpec
    gmres_tol: float
    extra: dict = field(default_factory=dict)

    def hash(self) -> str:
        d = _canon(asdict(self))
        d["freqs_hz"] = [round(float(f), 4) for f in self.freqs_hz]
        return _hash(d)


@dataclass
class Response:
    """What every backend returns. dB arrays are the contract; complex
    pressure is a bonus some backends provide and metrics never require."""
    freqs_hz: np.ndarray                 # (nf,)
    h_angles_deg: np.ndarray             # (na,) ascending, -90..+90, 0 included
    v_angles_deg: np.ndarray             # (na,)
    spl_h_db: np.ndarray                 # (nf, na) absolute dB SPL
    spl_v_db: np.ndarray                 # (nf, na)
    balloon_dirs: np.ndarray | None      # (nb, 3) unit vectors
    spl_balloon_db: np.ndarray | None    # (nf, nb)
    z_throat: np.ndarray | None          # (nf,) complex, normalized by rho*c
    p_h: np.ndarray | None = None        # (nf, na) complex, if available
    p_v: np.ndarray | None = None
    p_balloon: np.ndarray | None = None
    backend: str = ""
    n_dof: int | None = None
    meta: dict = field(default_factory=dict)

    @property
    def axis_index(self) -> int:
        """Index of the 0-degree sample. Both cuts share it."""
        i = int(np.argmin(np.abs(self.h_angles_deg)))
        assert abs(self.h_angles_deg[i]) < 1e-9, "no exact on-axis sample"
        return i


@dataclass
class SolveOutcome:
    ok: bool
    response: Response | None
    seconds: float
    peak_vram_mb: float | None
    message: str = ""


class Backend(Protocol):
    """solve/base.py. Two implementations: beat.py and bempp.py."""
    name: str
    def available(self) -> tuple[bool, str]: ...
    def solve(self, mesh: MeshResult, spec: SolveSpec) -> SolveOutcome: ...
    def warm(self) -> None: ...
    def release(self) -> None: ...


# ------------------------------------------------------------------ metrics

@dataclass
class MetricSet:
    freqs_hz: np.ndarray
    bw_h_deg: np.ndarray
    bw_v_deg: np.ndarray
    di_db: np.ndarray
    di_source: str                 # "balloon" | "cuts_estimate"
    ripple_h_db: np.ndarray
    ripple_v_db: np.ndarray
    on_axis_db: np.ndarray         # normalized to its own band mean
    z_throat_real: np.ndarray | None
    scalars: dict = field(default_factory=dict)


# ------------------------------------------------------------------ search

@dataclass
class Evaluation:
    design_hash: str
    design: Design
    mesh_hash: str
    solve_hash: str
    objective: float
    terms: dict
    metrics: MetricSet | None
    mesh: MeshResult | None
    outcome: SolveOutcome | None
    cached: bool = False
    error: str = ""


class GeometryInvalidError(ValueError): ...
class MeshTooLargeError(ValueError): ...
class BackendUnavailableError(RuntimeError): ...
