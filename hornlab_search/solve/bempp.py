"""Adapter: ``hornlab_bempp_bem`` (CPU, Burton-Miller) -> our ``Backend`` protocol.

Thin by design. Its job is to be an INDEPENDENT second opinion for the cuts (a different
language, quadrature and linear algebra from the Julia solver), and the backend that returns
complex pressure for phase 2. Where it differs from ``hornlab_beat_bem`` (the reason
``base.py`` exists):

* ``spl_db`` is NORMALISED (0 dB on axis). We recompute absolute SPL from ``pressure_complex``
  so both backends share one definition (dB re 20 uPa, unit normal acceleration).
* It infers an observation frame from the mesh unless given one; beat always observes around the
  global mesh origin. We pass an explicit axis-aligned frame at the origin so both measure the
  same arc.
* The polar grid is a plain ``linspace(angle_min, angle_max, angle_count)``; the signed range
  -90..+90 is supported directly, +angle toward +X (H) / +Y (V) (``build_observation_points``).
* ``gmres_tol`` IS a config field here (beat has none); passed from ``spec.gmres_tol``.
* ``native_symmetry_plane`` accepts 'yz', 'xz' and 'yz+xz' (beat refuses 'xz', quadrants '12'),
  BUT only with the STANDARD or COMPLEX_K formulation ("Burton-Miller is not implemented" under
  native symmetry; ``reject_unsupported_native_symmetry``). So this adapter uses Burton-Miller on
  full-domain meshes (what beat uses) and STANDARD on symmetry-reduced meshes. STANDARD has
  fictitious interior-resonance frequencies in principle, but the body of a freestanding horn is a
  6 mm shell whose interior Dirichlet modes sit far above the band. The formulation actually used
  is recorded in ``Response.meta['formulation']``; a reader comparing against beat must know it.
* Assembly is OpenCL-on-CPU by default; ``assembly_backend='auto'`` falls back to numba.
* ``impedance_sources`` (Robin wall BCs) exist here and not in beat. NOT wired in (phase 2).
* Open-mesh results differ across backends because of the P1 space choice. Our meshes are closed
  (freestanding with wall thickness), so the closed-mesh path is the one used and tested.
* No persistent worker: ``warm`` and ``release`` are no-ops.
"""
from __future__ import annotations

import logging
import time
import traceback

import numpy as np

from ..constants import C_AIR, RHO_AIR
from ..types import MeshResult, Response, SolveOutcome, SolveSpec
from . import base
from .base import ResponseSanityError, arc_angles_deg
from .beat import PLANES, SOURCE_TAG, Z_CONVENTION, check_symmetry_pairing

log = logging.getLogger("hornlab_search.solve.bempp")

ANGLE_TOL_DEG = 1e-9


def _refuse_source_tags(spec: SolveSpec) -> None:
    """MEH multi-source solves are BEAT-only for now (C4 is the fork's contract); bempp has no
    channel_pressure / impedance_matrix path, so refuse before any assembly rather than return a
    silent single-source cross-check of a multi-source design."""
    tags = (spec.extra or {}).get("source_tags")
    if tags is None:
        return
    from ..config import ConfigError
    raise ConfigError(
        f"bempp_cpu does not support solve.extra['source_tags']={list(tags)!r}: multi-source "
        f"(MEH) solves are implemented only by the hornlab-beat-bem fork (task M2), so the "
        f"bempp cross-check cannot verify this design yet. Run the MEH solve on beat_cuda/"
        f"beat_cpu, or omit source_tags for a single-source cross-check.")


def _to_response(raw, spec: SolveSpec, mesh: MeshResult, formulation: str = "unknown") -> Response:
    """Build a ``Response`` from a bempp ``SolveResult``. Raises ``ResponseSanityError``."""
    n_ang = int(spec.observation.angle_count)
    want_f = np.asarray(spec.freqs_hz, dtype=float)
    freqs = np.asarray(raw.frequencies_hz, dtype=float)
    if freqs.shape != want_f.shape or not np.allclose(freqs, want_f, rtol=1e-9, atol=0.0):
        raise ResponseSanityError(f"solver frequencies {freqs.tolist()} != requested {want_f.tolist()}")
    planes = list(raw.observation_planes)
    if "horizontal" not in planes or "vertical" not in planes:
        raise ResponseSanityError(f"result planes {planes} lack 'horizontal' and 'vertical'")
    ih, iv = planes.index("horizontal"), planes.index("vertical")
    p = np.asarray(raw.pressure_complex)
    if p.ndim != 3 or p.shape[0] != want_f.size or p.shape[2] != n_ang:
        raise ResponseSanityError(f"pressure_complex {p.shape} but expected (nf={want_f.size}, P, {n_ang})")
    angles = arc_angles_deg(n_ang)
    echo = np.asarray(raw.observation_angles_deg, dtype=float)
    if echo.shape != angles.shape or float(np.max(np.abs(echo - angles))) > 1e-6:
        raise ResponseSanityError(f"solver angle grid is not arc_angles_deg({n_ang})")
    ph = np.ascontiguousarray(p[:, ih, :]).astype(np.complex128)
    pv = np.ascontiguousarray(p[:, iv, :]).astype(np.complex128)
    spl_h, spl_v = base.spl_from_pressure(ph), base.spl_from_pressure(pv)
    base.check_cuts(want_f, n_ang, spl_h, spl_v, what="bempp result")

    dirs = spl_b = p_b = None
    grid = None
    sp = getattr(raw, "sphere_pressure_complex", None)
    want_balloon = bool(spec.observation.balloon) and int(spec.observation.balloon_points) > 0
    if sp is not None:
        sp = np.asarray(sp)
        th = np.asarray(raw.sphere_theta_deg, dtype=float)
        phi = np.asarray(raw.sphere_phi_deg, dtype=float)
        if sp.shape != (want_f.size, th.size):
            raise ResponseSanityError(f"sphere pressure {sp.shape} does not match {th.size} grid points")
        dirs = base.balloon_dirs_from_angles(th, phi)
        spl_b = base.spl_from_pressure(sp)
        if not np.all(np.isfinite(spl_b)):
            raise ResponseSanityError("balloon contains non-finite SPL")
        p_b = sp.astype(np.complex128)
        g = getattr(raw.config.observation, "sphere_grid", None)
        grid = [int(g[0]), int(g[1])] if g is not None else None
    elif want_balloon:
        raise ResponseSanityError("balloon was requested but the solver returned no sphere grid")

    z = None
    imp = getattr(raw, "impedance", None)
    if imp is not None:
        imp = np.asarray(imp, dtype=complex)
        if imp.shape == want_f.shape and np.all(np.isfinite(imp)):
            z = imp * (-1j * 2.0 * np.pi * want_f) / (RHO_AIR * C_AIR)

    mi = raw.mesh_info
    meta = {
        "device": "cpu", "solver": "bempp-cl",
        "n_vertices": int(mi.n_vertices), "n_triangles": int(mi.n_triangles),
        "symmetry_plane": mesh.symmetry_plane, "quadrants": mesh.quadrants, "mesh_scale": 1.0,
        "distance_m": float(spec.observation.distance_m), "angle_count": n_ang,
        "angle_convention": "ascending -90..+90 deg; +angle = +X on horizontal, +Y on vertical",
        "spl_reference": "absolute dB re 20 uPa for unit normal acceleration of tag 2 "
                         "(recomputed from pressure_complex; bempp's own spl_db is on-axis normalised)",
        "z_throat_convention": Z_CONVENTION,
        "gmres_tol_requested": float(spec.gmres_tol), "gmres_tol_applied": float(spec.gmres_tol),
        "formulation": formulation, "closed_mesh_mode": True,
        "timings": {k: float(v) for k, v in (getattr(raw, "timings", None) or {}).items()},
        "balloon_grid": grid,
        "balloon_layout": "theta-major; theta 0..180 from +Z, phi 0..360 from +X toward +Y; "
                          "NOT equal-area: weight by sin(theta)" if sp is not None else None,
    }
    return Response(
        freqs_hz=want_f.copy(), h_angles_deg=angles.copy(), v_angles_deg=angles.copy(),
        spl_h_db=spl_h, spl_v_db=spl_v, balloon_dirs=dirs, spl_balloon_db=spl_b, z_throat=z,
        p_h=ph, p_v=pv, p_balloon=p_b, backend="bempp_cpu", n_dof=int(mi.n_vertices),
        meta=base.jsonable(meta))


class BemppBackend:
    """``hornlab_bempp_bem`` on the CPU. Satisfies ``solve.base.Backend``."""

    name = "bempp_cpu"

    def __init__(self, timeout_s: float | None = None, track_vram: bool = False,
                 formulation: str | None = None):
        """``formulation``: 'burton_miller' | 'standard' | 'complex_k', or None for the default
        (Burton-Miller without native symmetry, STANDARD with it; see module docstring)."""
        self.timeout_s = timeout_s     # accepted for get_backend symmetry; not enforced (no cancel hook)
        if formulation not in (None, "burton_miller", "standard", "complex_k"):
            raise ValueError(f"unknown formulation {formulation!r}")
        self.formulation = formulation

    def formulation_for(self, mesh: MeshResult) -> str:
        if self.formulation is not None:
            return self.formulation
        return "burton_miller" if mesh.symmetry_plane is None else "standard"

    def available(self) -> tuple[bool, str]:
        try:
            import hornlab_bempp_bem  # noqa: F401
            import bempp_cl  # noqa: F401
        except ImportError as exc:
            return False, f"hornlab_bempp_bem / bempp_cl not importable: {exc}"
        return True, "hornlab_bempp_bem importable (assembly_backend='auto': OpenCL on CPU, numba fallback)"

    def warm(self) -> None:
        return None

    def release(self) -> None:
        return None

    def make_config(self, mesh: MeshResult, spec: SolveSpec):
        _refuse_source_tags(spec)
        import hornlab_bempp_bem as bempp
        check_symmetry_pairing(mesh)
        obs_kw = {}
        if spec.observation.balloon and int(spec.observation.balloon_points) > 0:
            obs_kw["sphere_grid"] = base.balloon_grid_shape(int(spec.observation.balloon_points))
        origin = np.zeros(3)
        frame = bempp.ObservationFrame(
            axis=np.array([0.0, 0.0, 1.0]), origin=origin.copy(),
            u=np.array([1.0, 0.0, 0.0]), v=np.array([0.0, 1.0, 0.0]),
            mouth_center=origin.copy(), source_center=origin.copy())
        return bempp.SolveConfig(
            formulation=bempp.BIEFormulation(self.formulation_for(mesh)),
            gmres_tol=float(spec.gmres_tol),
            native_symmetry_plane=mesh.symmetry_plane,
            mesh_scale=1.0,                       # the mesher writes metres
            velocity_sources={SOURCE_TAG: 1.0},
            air_density=RHO_AIR,
            assembly_backend="auto",
            frame_override=frame,
            observation=bempp.ObservationConfig(
                planes=list(PLANES), distance_m=float(spec.observation.distance_m),
                angle_min_deg=-90.0, angle_max_deg=90.0,
                angle_count=int(spec.observation.angle_count), **obs_kw),
        )

    def solve(self, mesh: MeshResult, spec: SolveSpec) -> SolveOutcome:
        _refuse_source_tags(spec)          # raises: never a silent single-source cross-check
        t0 = time.perf_counter()
        check_symmetry_pairing(mesh)
        try:
            import hornlab_bempp_bem as bempp
            cfg = self.make_config(mesh, spec)
            log.debug("bempp SolveConfig: %r", cfg)
            raw = bempp.solve_frequencies(mesh.path, [float(f) for f in spec.freqs_hz], cfg)
            resp = _to_response(raw, spec, mesh, self.formulation_for(mesh))
        except Exception as exc:
            tb = traceback.format_exc()
            log.error("bempp solve failed: %s", tb[:2000])
            return SolveOutcome(False, None, time.perf_counter() - t0, None, f"{exc!r}\n{tb[-3000:]}")
        seconds = time.perf_counter() - t0
        resp.meta["solve_seconds"] = seconds
        return SolveOutcome(True, resp, seconds, None, "")
