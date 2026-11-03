"""Adapter: ``hornlab_beat_bem`` (GPU/CPU BEM) -> our ``Backend`` protocol.

We write no acoustics here. ``beat.solve_frequencies`` does the work; this module sets the
config from the mesh and spec, calls it once PER FREQUENCY, stacks the results, converts them
to our ``Response``, and turns every failure into ``SolveOutcome(ok=False)``.

Facts about the installed ``hornlab-beat-bem`` 0.2.0 (read from its source, not guessed):

* It returns a ``SolveResult`` (not a ``Response``): ``pressure_complex (F, P, N)`` complex128
  with planes ``['horizontal', 'vertical']`` in that order, ``spl_db`` absolute dB re 20 uPa
  (for UNIT NORMAL ACCELERATION of the source tag), ``impedance (F,)``, ``mesh_info``,
  ``sphere_*`` (balloon), ``surface_*`` (traces).
* Its polar range is configurable through ``angle_min_deg/angle_max_deg/angle_count``, so we ask
  for -90..+90 directly instead of mirroring a 0..180 sweep. The Julia driver places
  H sample ``a`` at ``(R sin a, 0, R cos a)`` and V at ``(0, R sin a, R cos a)``: positive angle
  is toward +X (H) and +Y (V), matching 01_CONTRACTS section 3. ``arc_angles_deg`` is the grid
  we return; the solver's Float32 echo is asserted against it, never trusted in its place.
* One multi-frequency CUDA call falls off a performance cliff above ~2.4k dofs on the 8 GB card
  (689 s vs 33 s for 12 single-frequency calls at 5,140 dofs, TOOLCHAIN M3). So on CUDA ``solve``
  calls ``solve_frequencies`` once per frequency and stacks. The CPU backend shows no cliff
  (measured, see ``BeatBackend.__init__``) and makes one call.
* No ``native_diagnostics`` attribute; per-frequency diagnostics live in
  ``solver_log[i]['native_diagnostics']``. ``p1_dof_count == mesh_info.n_vertices``.
* No GMRES-tolerance knob exists in ``SolveConfig``; ``spec.gmres_tol`` is recorded in
  ``Response.meta`` as requested, with ``gmres_tol_applied: None``.
* ``native_symmetry_plane`` supports only None, 'yz' and 'yz+xz' (quadrants 1234, 14, 1).
  'xz' (quadrants '12') raises ``NotImplementedError`` inside the library -> ``ok=False``.
* ``impedance`` is the area-weighted mean source-tag pressure per unit ACCELERATION, in the
  solver's ``exp(-i omega t)`` convention. ``z_throat = impedance * (-i omega) / (rho c)`` is the
  specific acoustic impedance normalised by ``rho*c`` (same convention, so mass-like loading has
  NEGATIVE imaginary part). Only its real part is used by the objective.
"""
from __future__ import annotations

import json
import logging
import os
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ..constants import C_AIR, RHO_AIR
from ..types import MeshResult, Response, SolveOutcome, SolveSpec
from . import base, worker
from .base import ResponseSanityError, arc_angles_deg

log = logging.getLogger("hornlab_search.solve.beat")

SOURCE_TAG = 2        # SD1D1001 (hornlab_mesher.tags.PhysicalGroup.PRIMARY_SOURCE)
PLANES = ["horizontal", "vertical"]
ANGLE_ECHO_TOL_DEG = 1e-3          # solver echoes angles in Float32
Z_CONVENTION = "exp(-i*omega*t); z = Z_specific/(rho*c); mass-like loading has Im < 0"


def _refuse_unsupported_solver_knobs(device: str, extra: dict | None) -> None:
    """WP14+WP16: surface the library's own accelerator refusals EARLY, before any worker/GPU work.

    ``hornlab_beat_bem.SolveConfig`` already refuses ``near_correction`` on CUDA/ROCm/Metal
    (``NEAR_CORRECTION_REFUSALS``, config.py:62-78) and ``solve_precision='double'`` off the CPU
    backend (config.py:544-547). Those are ``NotImplementedError``s raised only once the adapter
    builds a config — after ``get_backend`` has already probed the device. Refuse here with the
    library's own rationale (single-image near cache vs multi-image symmetry) so a misconfigured
    run fails cleanly and actionably before a warm host exists. CPU near correction and double
    precision are the WP14 CPU-validation path; the accelerator port is WP17/fork work.
    ``source_profile_alpha`` (WP16) is refused everywhere but the fused CUDA path, with the
    library's own rationale quoted (see ``_source_profile_kwargs`` for the forward)."""
    from ..config import ConfigError

    extra = extra or {}
    precision = str(extra.get("solve_precision", "single"))
    near = bool(extra.get("near_correction", False))
    label = {"cuda": "CUDA", "rocm": "ROCm", "metal": "Metal"}.get(str(device), str(device).upper())
    if precision == "double" and device != "cpu":
        raise ConfigError(
            f"solve.solve_precision='double' is only available on the BEAT CPU backend "
            f"(hornlab_beat_bem refuses it on {label}); use backend: beat_cpu with "
            f"solve_precision: double (WP14 CPU validation)")
    if near and device != "cpu":
        raise ConfigError(
            f"near_correction is not implemented for the BEAT {label} backend: the CUDA device "
            f"path carries a single image-near cache, so under a multi-image symmetry two of "
            f"three mirror transforms would integrate a near-singular kernel with the plain "
            f"regular rule and say nothing about it; refused rather than silently wrong. "
            f"Near correction is a BEAT CPU feature (backend: beat_cpu, WP14); the accelerator "
            f"port is WP17/fork work, so hornlab-search refuses before starting any GPU work "
            f"instead of after the device probe.")
    # WP16: source_profile_alpha is a fused-CUDA-only feature in hornlab_beat_bem. Surface the
    # library's OWN refusal here (its SolveConfig raises NotImplementedError at construction,
    # after get_backend's device probe) so a misconfigured run fails before any GPU/worker work.
    alpha = extra.get("source_profile_alpha")
    if alpha is not None and float(alpha) != 0.0:
        fused = os.environ.get("HORNLAB_BEAT_FUSED_BM_CUDA", "0") == "1"
        if device != "cuda" or not fused:
            raise ConfigError(
                f"WP16: profile source implemented on the fused path only (branch work in "
                f"progress): source_profile_alpha={float(alpha)!r} needs beat_backend='cuda' and "
                f"HORNLAB_BEAT_FUSED_BM_CUDA=1 in the environment the Julia worker inherits; "
                f"every other path would assemble the uniform drive and report a profile it "
                f"never applied (set solve.cuda_fused: true, which exports "
                f"HORNLAB_BEAT_FUSED_BM_CUDA=1 before the host spawns)")


def _near_precision_kwargs(extra: dict | None) -> dict:
    """WP14: the SolveConfig kwargs for the four CPU-validation keys, named exactly like the
    library's own fields. Absent keys are NOT sent, so an old spec builds today's exact config."""
    extra = extra or {}
    kw: dict = {}
    if "near_correction" in extra:
        kw["near_correction"] = bool(extra["near_correction"])
    if "near_correction_cutoff" in extra:
        kw["near_correction_cutoff"] = float(extra["near_correction_cutoff"])
    if "near_correction_order" in extra:
        kw["near_correction_order"] = int(extra["near_correction_order"])
    if "solve_precision" in extra:
        kw["solve_precision"] = str(extra["solve_precision"])
    return kw


def _source_profile_kwargs(extra: dict | None) -> dict:
    """WP16: the SolveConfig kwarg for the J0 source-profile angle, named exactly like the
    library's own field. Absent key -> NOT sent, so an old spec builds today's exact config."""
    extra = extra or {}
    if "source_profile_alpha" not in extra:
        return {}
    return {"source_profile_alpha": float(extra["source_profile_alpha"])}


def check_symmetry_pairing(mesh: MeshResult) -> None:
    """Silent killer #2: the symmetry flag must be the one ``mesh/sizing.SYMMETRY_PLANE`` derives
    from ``quadrants``. A mismatch is a bug, not a bad candidate, so it RAISES (never becomes a
    penalty row)."""
    from ..mesh.build import SymmetryMismatchError
    from ..mesh.sizing import SYMMETRY_PLANE
    if mesh.quadrants not in SYMMETRY_PLANE:
        raise SymmetryMismatchError(f"unknown quadrants {mesh.quadrants!r}")
    expected = SYMMETRY_PLANE[mesh.quadrants]
    if mesh.symmetry_plane != expected:
        raise SymmetryMismatchError(
            f"mesh.symmetry_plane={mesh.symmetry_plane!r} but quadrants={mesh.quadrants!r} "
            f"requires {expected!r} (mesh/sizing.SYMMETRY_PLANE). Solving would give a clean, "
            f"smooth, wrong polar.")


# ------------------------------------------------------------------ MEH multi-source preflight

#: docs/meh/00_MEH_CONTRACTS.md C4: the fork accepts 1..8 velocity-source tags.
MAX_SOURCE_TAGS = 8
#: SolveConfig field the MEH path needs (C4). It does not exist on the installed pin.
IMPEDANCE_MATRIX_FIELD = "impedance_matrix"


def _source_tags(extra: dict | None) -> tuple[int, ...] | None:
    """``SolveSpec.extra['source_tags']`` -> the sorted tag tuple, or None for a legacy solve.

    Absent = today's single-source solve (``velocity_sources={2: 1.0}``, no new config keys).
    Present = the MEH multi-source path (C4): 1..8 distinct positive integer tags. Raises
    ``ConfigError`` for anything the solver contract would refuse, instead of silently solving a
    different problem.
    """
    from ..config import ConfigError

    raw = (extra or {}).get("source_tags")
    if raw is None:
        return None
    if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple)):
        raise ConfigError(
            f"solve.extra['source_tags'] must be a list of integer physical tags, got {raw!r}")
    values = []
    for t in raw:
        if isinstance(t, bool) or not isinstance(t, (int, np.integer)):
            raise ConfigError(
                f"solve.extra['source_tags'] must contain integer physical tags, got {t!r}")
        values.append(int(t))
    tags = tuple(sorted(values))
    if not tags:
        raise ConfigError("solve.extra['source_tags'] is empty; either omit it (single source) "
                          "or name at least one physical tag")
    if len(set(tags)) != len(tags):
        raise ConfigError(f"solve.extra['source_tags'] contains duplicates: {list(raw)!r}")
    if len(tags) > MAX_SOURCE_TAGS:
        raise ConfigError(
            f"solve.extra['source_tags'] has {len(tags)} tags but the MEH solver contract "
            f"accepts at most {MAX_SOURCE_TAGS}")
    if any(t < 1 for t in tags):
        raise ConfigError(
            f"solve.extra['source_tags'] must be positive physical tags, got {list(tags)!r}")
    return tags


def _solveconfig_has_field(cls, name: str) -> bool:
    """True when ``SolveConfig`` exposes ``name`` (the MEH fork adds it; the old pin does not)."""
    import dataclasses
    import inspect
    try:
        if dataclasses.is_dataclass(cls):
            return any(f.name == name for f in dataclasses.fields(cls))
    except (TypeError, ValueError):
        pass
    try:
        return name in inspect.signature(cls).parameters
    except (TypeError, ValueError):
        return False


def _mesh_tag_ids_from_meta(mesh: MeshResult) -> set[int]:
    """Physical tags present in a CAD mesh, from ``mesh_meta.json`` (M5 writes per-tag areas and
    centroids next to the .msh; step_build's ``summary.tags`` already records element counts).

    Read BEFORE a worker starts, so a request naming a tag the STEP labels never produced fails
    as a configuration error instead of a solver failure or, worse, a silently different model.
    """
    from ..config import ConfigError

    meta_path = Path(mesh.path).with_name("mesh_meta.json")
    if not meta_path.is_file():
        raise ConfigError(
            f"source_tags requested but {meta_path} is missing: a MEH multi-source solve needs "
            f"the CAD mesh metadata (per-tag areas/centroids from task M5) to prove every source "
            f"tag exists before any worker starts")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"source_tags requested but {meta_path} is unreadable: {exc!r}") from exc
    summary = meta.get("summary") if isinstance(meta, dict) else None
    summary = summary if isinstance(summary, dict) else {}
    ids: set[int] = set()
    counts = summary.get("tags")
    if isinstance(counts, dict):
        for k, v in counts.items():
            try:
                if int(v) > 0:
                    ids.add(int(k))
            except (TypeError, ValueError):
                continue
    # M5 additionally echoes per-tag areas (C9); honour them when present.
    for table in (summary.get("tag_areas_m2"),
                  meta.get("tag_areas_m2") if isinstance(meta, dict) else None):
        if isinstance(table, dict):
            for k, v in table.items():
                try:
                    if float(v) > 0.0:
                        ids.add(int(k))
                except (TypeError, ValueError):
                    continue
    if not ids:
        raise ConfigError(
            f"source_tags requested but {meta_path} records no per-tag areas or tag counts; "
            f"cannot prove the source tags exist (task M5 mesh metadata)")
    return ids


def _check_source_tags_in_mesh(mesh: MeshResult, tags: tuple[int, ...]) -> None:
    """Every requested source tag must exist in the mesh before any worker starts."""
    from ..config import ConfigError

    present = _mesh_tag_ids_from_meta(mesh)
    missing = [t for t in tags if t not in present]
    if missing:
        raise ConfigError(
            f"source_tags {list(tags)} but the mesh at {mesh.path} has no elements on tag(s) "
            f"{missing} (tags present: {sorted(present)}); the STEP label -> BEM tag mapping "
            f"(docs/meh/00_MEH_CONTRACTS.md C3) did not produce them")


# ------------------------------------------------------------------ result handling


def _stack(raws: list, freqs: list[float]) -> SimpleNamespace:
    """Stack single-frequency ``SolveResult``s into one object with the same field names."""
    r0 = raws[0]
    angles = np.asarray(r0.observation_angles_deg, dtype=float)
    for i, r in enumerate(raws):
        if list(r.observation_planes) != list(r0.observation_planes):
            raise ResponseSanityError(f"observation planes changed between frequencies at index {i}")
        if not np.array_equal(np.asarray(r.observation_angles_deg, dtype=float), angles):
            raise ResponseSanityError(f"observation angles changed between frequencies at index {i}")

    def cat(name):
        parts = [getattr(r, name, None) for r in raws]
        if any(p is None for p in parts):
            return None
        return np.concatenate([np.atleast_1d(np.asarray(p)) for p in parts], axis=0)

    timings: dict[str, float] = {}
    for r in raws:
        for k, v in (r.timings or {}).items():
            timings[k] = timings.get(k, 0.0) + float(v)
    log_entries = [e for r in raws for e in (r.solver_log or [])]
    n_req = sum(int(getattr(r, "requested_frequency_count", None) or np.asarray(r.frequencies_hz).size)
                for r in raws)
    got = int(sum(np.asarray(r.frequencies_hz).size for r in raws))
    # MEH (C4): per-channel fields are per-frequency stacks; the tag tuple is per solve.
    channel_tags = getattr(r0, "channel_tags", None)
    tag_areas_m2 = getattr(r0, "tag_areas_m2", None)
    for i, r in enumerate(raws):
        if getattr(r, "channel_tags", None) != channel_tags:
            raise ResponseSanityError(f"channel_tags changed between frequencies at index {i}")
        if getattr(r, "tag_areas_m2", None) != tag_areas_m2:
            raise ResponseSanityError(f"tag_areas_m2 changed between frequencies at index {i}")
    return SimpleNamespace(
        frequencies_hz=cat("frequencies_hz"),
        pressure_complex=cat("pressure_complex"),
        spl_db=cat("spl_db"),
        impedance=cat("impedance"),
        observation_angles_deg=angles,
        observation_planes=list(r0.observation_planes),
        config=r0.config,
        mesh_info=r0.mesh_info,
        timings=timings,
        solver_log=log_entries,
        sphere_pressure_complex=cat("sphere_pressure_complex"),
        sphere_theta_deg=getattr(r0, "sphere_theta_deg", None),
        sphere_phi_deg=getattr(r0, "sphere_phi_deg", None),
        channel_tags=channel_tags,
        channel_pressure=cat("channel_pressure"),
        channel_sphere_pressure=cat("channel_sphere_pressure"),
        impedance_matrix=cat("impedance_matrix"),
        tag_areas_m2=tag_areas_m2,
        surface_pressure_complex=cat("surface_pressure_complex"),
        surface_neumann_complex=cat("surface_neumann_complex"),
        cancelled=any(bool(getattr(r, "cancelled", False)) for r in raws),
        requested_frequency_count=n_req,
        is_partial=got < n_req,
    )


def _p1_dof_count(raw) -> int:
    """The solver's own dof count. 0.2.0 reports it per frequency in
    ``solver_log[i]['native_diagnostics']['p1_dof_count']`` (the plan's top-level attribute does not
    exist); ``mesh_info.n_vertices`` (nodes in the file) is the fallback and the two are compared:
    a disagreement is logged, because the dof calibration table rests on them being equal."""
    n_vertices = int(raw.mesh_info.n_vertices)
    counts = set()
    for e in (getattr(raw, "solver_log", None) or []):
        d = e.get("native_diagnostics") if isinstance(e, dict) else None
        if isinstance(d, dict) and d.get("p1_dof_count") is not None:
            counts.add(int(d["p1_dof_count"]))
    if len(counts) > 1:
        raise ResponseSanityError(f"p1_dof_count changed between frequencies: {sorted(counts)}")
    if not counts:
        return n_vertices
    (n,) = counts
    if n != n_vertices:
        log.warning("solver p1_dof_count=%d but the mesh file has %d nodes", n, n_vertices)
    return n


def _native_diagnostics(raw) -> list | None:
    out = []
    for e in (getattr(raw, "solver_log", None) or []):
        d = e.get("native_diagnostics") if isinstance(e, dict) else None
        out.append(base.jsonable(d, max_array=64) if d is not None else None)
    return out if any(d is not None for d in out) else None


def _assert_cuda_fused_path(raw, spec: SolveSpec) -> None:
    """WP15: a ``cuda_fused`` solve must PROVE it ran the fused CUDA path. The driver adds
    ``"assembly_path" => "fused_cuda"`` to every per-frequency ``native_diagnostics`` only when
    that path ran. No diagnostics at all, or a different path, means the solve silently used the
    old 4-operator CUDA path (e.g. a warm host started before
    ``HORNLAB_BEAT_FUSED_BM_CUDA=1`` was set) and is REFUSED here — that data must never be
    presented as a fused solve. Clear the host (``hornlab-search gpu-clean``) and solve again."""
    if not bool((spec.extra or {}).get("cuda_fused")):
        return
    seen = bad = 0
    for e in (getattr(raw, "solver_log", None) or []):
        d = e.get("native_diagnostics") if isinstance(e, dict) else None
        if not isinstance(d, dict):
            continue
        seen += 1
        if str(d.get("assembly_path", "")) != "fused_cuda":
            bad += 1
    if seen == 0 or bad:
        raise ResponseSanityError(
            "solve.cuda_fused was requested but the driver diagnostics do not prove the fused "
            f"CUDA path ran ({seen} per-frequency diagnostic entries, {bad} without "
            "assembly_path == 'fused_cuda'; a warm host started without "
            "HORNLAB_BEAT_FUSED_BM_CUDA=1 must be cleared first: hornlab-search gpu-clean)")


def _to_response(raw, spec: SolveSpec, mesh: MeshResult) -> Response:
    """Build our ``Response`` from a (stacked) beat result. RAISES ``ResponseSanityError`` on any
    array that cannot be right; it never returns a bad Response.

    Mapping (verified against ``BeatEngineDriver.jl`` and ``sweep.py``):
      * ``spl_h_db = raw.spl_db[:, horizontal, :]``, ``spl_v_db = raw.spl_db[:, vertical, :]``;
        absolute dB re 20 uPa, ascending -90..+90, +angle = +X / +Y. No mirroring is applied
        because the solver is asked for the signed range directly.
      * angles are ``arc_angles_deg(angle_count)`` (exact 0); the solver's own echo is asserted
        equal within 1e-3 deg.
    """
    n_ang = int(spec.observation.angle_count)
    want_f = np.asarray(spec.freqs_hz, dtype=float)
    freqs = np.asarray(raw.frequencies_hz, dtype=float)

    if bool(getattr(raw, "cancelled", False)) or bool(getattr(raw, "is_partial", False)):
        raise ResponseSanityError(
            f"partial or cancelled sweep (cancelled={getattr(raw, 'cancelled', None)}, "
            f"is_partial={getattr(raw, 'is_partial', None)}): never usable as a Response")
    if freqs.shape != want_f.shape or not np.allclose(freqs, want_f, rtol=1e-9, atol=0.0):
        raise ResponseSanityError(f"solver frequencies {freqs.tolist()} != requested {want_f.tolist()}")

    planes = list(raw.observation_planes)
    if "horizontal" not in planes or "vertical" not in planes:
        raise ResponseSanityError(f"result planes {planes} lack 'horizontal' and 'vertical'")
    ih, iv = planes.index("horizontal"), planes.index("vertical")

    p = np.asarray(raw.pressure_complex)
    spl = np.asarray(raw.spl_db, dtype=float)
    if p.ndim != 3 or spl.ndim != 3 or p.shape != spl.shape:
        raise ResponseSanityError(f"pressure_complex {p.shape} / spl_db {spl.shape} must be (F, P, N)")
    if p.shape[0] != want_f.size or p.shape[2] != n_ang:
        raise ResponseSanityError(
            f"pressure_complex shape {p.shape} but expected (nf={want_f.size}, P, angle_count={n_ang})")

    angles = arc_angles_deg(n_ang)
    echo = np.asarray(raw.observation_angles_deg, dtype=float)
    if echo.shape != angles.shape or float(np.max(np.abs(echo - angles))) > ANGLE_ECHO_TOL_DEG:
        raise ResponseSanityError(
            f"solver angle grid ({echo.size} pts, {echo.min() if echo.size else 'n/a'}.."
            f"{echo.max() if echo.size else 'n/a'}) is not arc_angles_deg({n_ang}): "
            f"max diff {float(np.max(np.abs(echo - angles))) if echo.shape == angles.shape else 'shape'}")

    spl_h = np.ascontiguousarray(spl[:, ih, :])
    spl_v = np.ascontiguousarray(spl[:, iv, :])
    base.check_cuts(want_f, n_ang, spl_h, spl_v, what="beat result")
    # spl_db must be exactly the absolute level of the complex pressure (catches a stale/mixed field)
    chk = base.spl_from_pressure(p[:, ih, :])
    if float(np.max(np.abs(chk - spl_h))) > 1e-6:
        raise ResponseSanityError("raw.spl_db disagrees with 20*log10(|pressure_complex|/20uPa)")

    # ---- balloon
    want_balloon = bool(spec.observation.balloon) and int(spec.observation.balloon_points) > 0
    dirs = spl_b = p_b = None
    grid = None
    sp = getattr(raw, "sphere_pressure_complex", None)
    if sp is not None:
        sp = np.asarray(sp)
        th = np.asarray(raw.sphere_theta_deg, dtype=float)
        ph = np.asarray(raw.sphere_phi_deg, dtype=float)
        if sp.ndim != 2 or sp.shape != (want_f.size, th.size) or ph.size != th.size:
            raise ResponseSanityError(f"sphere pressure {sp.shape} does not match grid of {th.size} points")
        dirs = base.balloon_dirs_from_angles(th, ph)
        spl_b = base.spl_from_pressure(sp)
        if not np.all(np.isfinite(spl_b)):
            raise ResponseSanityError("balloon contains non-finite SPL")
        p_b = sp.astype(np.complex128)
        sg = getattr(getattr(raw, "config", None), "observation", None)
        sg = getattr(sg, "sphere_grid", None)
        grid = [int(sg[0]), int(sg[1])] if sg is not None else None
    elif want_balloon:
        raise ResponseSanityError("balloon was requested but the solver returned no sphere grid")

    # ---- MEH per-channel fields (C4/C5). Requested only through `source_tags`; a solver that
    # cannot produce them has already been refused in make_config (pin check).
    source_tags = _source_tags(spec.extra)
    channel_tags = channel_pressure = channel_sphere = z_matrix = tag_areas = None
    if source_tags is not None:
        raw_tags = getattr(raw, "channel_tags", None)
        if raw_tags is None or getattr(raw, "channel_pressure", None) is None:
            raise ResponseSanityError(
                f"source_tags {list(source_tags)} requested but the solver returned no "
                f"channel_tags/channel_pressure fields")
        channel_tags = tuple(int(t) for t in raw_tags)
        if channel_tags != source_tags:
            raise ResponseSanityError(
                f"solver channel_tags {list(channel_tags)} != requested source_tags "
                f"{list(source_tags)}")
        channel_pressure = np.asarray(raw.channel_pressure, dtype=np.complex128)
        want_cp = (want_f.size, len(source_tags)) + p.shape[1:]
        if channel_pressure.shape != want_cp:
            raise ResponseSanityError(
                f"channel_pressure shape {channel_pressure.shape} but expected {want_cp} "
                f"(F, C, P, A)")
        # C4: legacy pressure is the channel of the smallest tag (channel 0).
        if not np.allclose(channel_pressure[:, 0, :, :], p, rtol=1e-12, atol=0.0):
            raise ResponseSanityError(
                "legacy pressure_complex is not channel 0 of channel_pressure (smallest tag)")
        raw_matrix = getattr(raw, "impedance_matrix", None)
        if raw_matrix is None:
            raise ResponseSanityError(
                "multi-source solve returned no impedance_matrix although impedance_matrix=True")
        z_matrix = np.asarray(raw_matrix, dtype=np.complex128)
        want_zm = (want_f.size, len(source_tags), len(source_tags))
        if z_matrix.shape != want_zm or not np.all(np.isfinite(z_matrix)):
            raise ResponseSanityError(
                f"impedance_matrix {z_matrix.shape} must be finite {want_zm} (F, C, C)")
        raw_areas = getattr(raw, "tag_areas_m2", None)
        if not isinstance(raw_areas, dict):
            raise ResponseSanityError("multi-source solve returned no tag_areas_m2 dict")
        tag_areas = {int(k): float(v) for k, v in raw_areas.items()}
        if set(tag_areas) != set(source_tags):
            raise ResponseSanityError(
                f"tag_areas_m2 keys {sorted(tag_areas)} != source_tags {list(source_tags)}")
        if any((not np.isfinite(a)) or a <= 0.0 for a in tag_areas.values()):
            raise ResponseSanityError(f"tag_areas_m2 must be positive and finite: {tag_areas}")
        raw_csp = getattr(raw, "channel_sphere_pressure", None)
        if want_balloon:
            if raw_csp is None:
                raise ResponseSanityError(
                    "balloon requested but the multi-source solver returned no "
                    "channel_sphere_pressure")
            channel_sphere = np.asarray(raw_csp, dtype=np.complex128)
            want_cs = (want_f.size, len(source_tags), np.asarray(sp).shape[1])
            if channel_sphere.shape != want_cs or not np.all(np.isfinite(channel_sphere)):
                raise ResponseSanityError(
                    f"channel_sphere_pressure {channel_sphere.shape} must be finite {want_cs}")
        elif raw_csp is not None:
            channel_sphere = np.asarray(raw_csp, dtype=np.complex128)

    # ---- impedance -> z_throat (normalised specific acoustic impedance)
    z = None
    imp = getattr(raw, "impedance", None)
    if imp is not None:
        imp = np.asarray(imp, dtype=complex)
        if imp.shape == want_f.shape and np.all(np.isfinite(imp)):
            cfg = getattr(raw, "config", None)
            rho = float(getattr(cfg, "air_density", RHO_AIR))
            c = float(getattr(cfg, "sound_speed", C_AIR))
            z = imp * (-1j * 2.0 * np.pi * want_f) / (rho * c)

    mi = raw.mesh_info
    n_dof = _p1_dof_count(raw)
    # WP15: when a cuda_fused solve is requested, PROVE the fused path ran before building a
    # Response (refusal above otherwise); meta carries the evidence.
    _assert_cuda_fused_path(raw, spec)
    meta = {
        "device": getattr(getattr(raw, "config", None), "beat_backend", None),
        "is_partial": bool(getattr(raw, "is_partial", False)),
        "cancelled": bool(getattr(raw, "cancelled", False)),
        "requested_frequency_count": getattr(raw, "requested_frequency_count", None),
        "n_vertices": int(mi.n_vertices),
        "n_triangles": int(mi.n_triangles),
        "physical_tag_areas_m2": {str(k): float(v) for k, v in dict(mi.physical_tag_areas_m2).items()},
        "symmetry_plane": mesh.symmetry_plane,
        "quadrants": mesh.quadrants,
        "mesh_scale": 1.0,
        "distance_m": float(spec.observation.distance_m),
        "angle_count": n_ang,
        "angle_convention": "ascending -90..+90 deg; +angle = +X on horizontal, +Y on vertical",
        "spl_reference": "absolute dB re 20 uPa for unit normal acceleration of tag 2",
        "z_throat_convention": Z_CONVENTION,
        "gmres_tol_requested": float(spec.gmres_tol),
        "gmres_tol_applied": None,
        "timings": {k: float(v) for k, v in (raw.timings or {}).items()},
        "balloon_grid": grid,
        "balloon_layout": "theta-major; theta 0..180 from +Z, phi 0..360 from +X toward +Y; "
                          "NOT equal-area: weight by sin(theta)" if sp is not None else None,
        "native_diagnostics": _native_diagnostics(raw),
        "n_dof_source": "solver_log[i].native_diagnostics.p1_dof_count (fallback: mesh_info.n_vertices)",
        "cuda_fused": bool((spec.extra or {}).get("cuda_fused")),
        "mesh_policy": (spec.extra or {}).get("mesh_policy"),
        "source_motion": str((spec.extra or {}).get("source_motion", "normal")),
    }
    if source_tags is not None:
        # MEH provenance is additive: a legacy response's meta is unchanged.
        meta["source_tags"] = list(source_tags)
        meta["channel_tags"] = list(channel_tags)
        meta["tag_areas_m2"] = {str(k): float(v) for k, v in tag_areas.items()}
        meta["impedance_matrix"] = True
    return Response(
        freqs_hz=want_f.copy(),
        h_angles_deg=angles.copy(),
        v_angles_deg=angles.copy(),
        spl_h_db=spl_h,
        spl_v_db=spl_v,
        balloon_dirs=dirs,
        spl_balloon_db=spl_b,
        z_throat=z,
        p_h=np.ascontiguousarray(p[:, ih, :]).astype(np.complex128),
        p_v=np.ascontiguousarray(p[:, iv, :]).astype(np.complex128),
        p_balloon=p_b,
        backend="",                      # filled by the caller (knows its own name)
        n_dof=n_dof,
        meta=base.jsonable(meta),
        channel_tags=channel_tags,
        channel_pressure=channel_pressure,
        channel_sphere_pressure=channel_sphere,
        impedance_matrix=z_matrix,
        tag_areas_m2=tag_areas,
    )


# ------------------------------------------------------------------ the backend


class BeatBackend:
    """``hornlab_beat_bem`` on ``device`` ('cuda', 'metal', or 'cpu'). Satisfies ``solve.base.Backend``.

    ``timeout_s``: wall-clock budget checked between frequencies (the library call itself has no
    cancel hook for a single frequency). ``per_frequency_calls``: one ``solve_frequencies`` call
    per frequency (default True on CUDA/Metal where batching cliffs have been seen or are
    unmeasured, False on CPU; see module docstring and the measurement in ``__init__``).
    """

    def __init__(self, device: str, timeout_s: float | None = None, track_vram: bool = True,
                 per_frequency_calls: bool | None = None, notes_path=None,
                 cuda_fused: bool = False):
        if device not in ("cuda", "metal", "cpu"):
            raise ValueError(f"device must be 'cuda', 'metal', or 'cpu', got {device!r}")
        if cuda_fused and device != "cuda":
            raise ValueError(f"cuda_fused is only implemented for the cuda backend, got {device!r}")
        self.device = device
        self.name = f"beat_{device}"
        self.timeout_s = timeout_s
        # nvidia-smi VRAM polling is CUDA-only; Metal uses unified memory (no separate pool probe).
        self.track_vram = bool(track_vram) and device == "cuda"
        # CUDA: mandatory (689 s vs 33 s at 5,140 dofs). CPU: measured no cliff (4,530 dofs, 4 freqs:
        # one call 18.3 s vs per-frequency 19.2 s; 2,316 dofs, 6 freqs: 7.2 s vs 7.7 s), so one call.
        # Metal: unmeasured on our kit; default to per-frequency like CUDA until a Mac ladder says
        # otherwise (fused Metal assembly is on in the library by default — separate from WP15).
        self.per_frequency_calls = (
            device in ("cuda", "metal") if per_frequency_calls is None else bool(per_frequency_calls))
        self.notes_path = notes_path
        # WP15: opt-in fused CUDA Burton-Miller assembly. The env MUST be set BEFORE the persistent
        # worker host spawns (the host inherits this process's environment); explicit "0" for the
        # default so a flag left over in the process environment can never leak into a run.
        # Metal's fused path is a library default, not this CUDA flag.
        self.cuda_fused = bool(cuda_fused)
        os.environ["HORNLAB_BEAT_FUSED_BM_CUDA"] = "1" if self.cuda_fused else "0"

    # ---- protocol
    def available(self) -> tuple[bool, str]:
        try:
            import hornlab_beat_bem as beat
        except ImportError as exc:
            return False, f"hornlab_beat_bem is not importable: {exc}"
        try:
            st = beat.backend_status(self.device)
        except Exception as exc:
            return False, f"backend_status({self.device!r}) failed: {exc!r}"
        return bool(st.get("available")), str(st.get("reason", ""))

    def warm(self) -> None:
        """Boot the persistent host and JIT the kernels. Use ``solve.worker.warm(backend)`` so
        stale hosts are cleared first and the call is idempotent."""
        worker.start_beat_worker(self.device)

    def release(self) -> None:
        """Stop the host and verify it is gone (``worker.shutdown``). Raises
        ``worker.WorkerReleaseError`` if a Julia process survives."""
        worker.shutdown(verify=True)

    def solve(self, mesh: MeshResult, spec: SolveSpec) -> SolveOutcome:
        return self._solve(mesh, spec, surface_traces=False)[0]

    def solve_traced(self, mesh: MeshResult, spec: SolveSpec) -> tuple[SolveOutcome, dict | None]:
        """One solve with ``surface_traces=True``; returns the outcome and the raw traces
        ``{'pressure': (nf, n_vertices) c128, 'neumann': (nf, n_faces) c128}`` (None on failure)."""
        return self._solve(mesh, spec, surface_traces=True)

    # ---- config
    def make_config(self, mesh: MeshResult, spec: SolveSpec, *, frame_origin_m=None,
                    surface_traces: bool = False):
        # WP14: check the accelerator refusals BEFORE importing the solver / pairing checks, so a
        # CUDA run with near_correction or double precision fails before any GPU/worker work.
        _refuse_unsupported_solver_knobs(self.device, spec.extra)
        import hornlab_beat_bem as beat
        check_symmetry_pairing(mesh)
        # MEH (C4/C5): `source_tags` switches the multi-source path on. Absent = today's exact
        # config (velocity_sources={2: 1.0}, no new keys), so old solve hashes/payloads are
        # byte-for-byte unchanged.
        source_tags = _source_tags(spec.extra)
        if source_tags is None:
            velocity_sources = {SOURCE_TAG: 1.0}
            meh_kwargs: dict = {}
        else:
            if not _solveconfig_has_field(beat.SolveConfig, IMPEDANCE_MATRIX_FIELD):
                from ..config import ConfigError
                raise ConfigError(
                    "MEH multi-source solve requested (solve.extra['source_tags']) but the "
                    "installed hornlab-beat-bem SolveConfig has no 'impedance_matrix' field: "
                    "the solver fork branch hornlab-search/meh-multisource (task M2) is not "
                    "installed. M8 bumps the hornlab-beat-bem pin to that branch after GPU "
                    "validation; this is a pin bump, not a hornlab-search setting.")
            _check_source_tags_in_mesh(mesh, source_tags)
            velocity_sources = {t: 1.0 for t in source_tags}
            meh_kwargs = {IMPEDANCE_MATRIX_FIELD: True}
        obs_kw = {}
        if spec.observation.balloon and int(spec.observation.balloon_points) > 0:
            obs_kw["sphere_grid"] = base.balloon_grid_shape(int(spec.observation.balloon_points))
        observation = beat.ObservationConfig(
            planes=list(PLANES),
            distance_m=float(spec.observation.distance_m),
            angle_min_deg=-90.0,
            angle_max_deg=90.0,
            angle_count=int(spec.observation.angle_count),
            **obs_kw,
        )
        frame = None
        if frame_origin_m is not None:
            frame = beat.ObservationFrame(
                axis=np.array([0.0, 0.0, 1.0]), origin=np.asarray(frame_origin_m, dtype=float),
                u=np.array([1.0, 0.0, 0.0]), v=np.array([0.0, 1.0, 0.0]))
        return beat.SolveConfig(
            beat_backend=self.device,
            native_symmetry_plane=mesh.symmetry_plane,   # FROM THE MESH, never a literal
            # The mesher writes METRES. The beat README's mesh_scale=0.001 example is for a
            # millimetre mesh and does NOT apply here: 0.001 would give a 1000x-too-large horn
            # that solves fine and looks smooth.
            mesh_scale=1.0,
            velocity_sources=velocity_sources,
            # MEH (C4): only present on the multi-source path; absent otherwise.
            **meh_kwargs,
            # WP5: always sent explicitly; 'normal' is the breathing cap (today), 'axial' a rigid
            # piston along +z. The default is in `extra` only when it differs, so old solve hashes
            # are untouched.
            source_motion=str((spec.extra or {}).get("source_motion", "normal")),
            air_density=RHO_AIR,
            # WP14: forwarded under the library's own field names, ONLY when the key is present in
            # `extra` (absent = the SolveConfig default, i.e. today's dict byte-for-byte).
            **_near_precision_kwargs(spec.extra),
            # WP16: forwarded under the library's own field name, ONLY when the key is present in
            # `extra` (absent = the SolveConfig default 0.0, i.e. today's dict byte-for-byte).
            **_source_profile_kwargs(spec.extra),
            sound_speed=C_AIR,
            observation=observation,
            frame_override=frame,
            surface_traces=bool(surface_traces),
        )

    # ---- solving
    def solve_raw(self, mesh: MeshResult, spec: SolveSpec, *, frame_origin_m=None,
                  surface_traces: bool = False, cfg=None):
        """Run the solver and return the stacked raw result (no conversion, no catching).
        Exposed for the asymmetric-design sign test and the trace round trip."""
        import hornlab_beat_bem as beat
        cfg = cfg or self.make_config(mesh, spec, frame_origin_m=frame_origin_m,
                                      surface_traces=surface_traces)
        freqs = [float(f) for f in spec.freqs_hz]
        log.debug("beat SolveConfig: %r", cfg)
        log.debug("beat frequencies_hz: %r  mesh: %s", freqs, mesh.path)
        deadline = None if self.timeout_s is None else time.perf_counter() + float(self.timeout_s)
        groups = [[f] for f in freqs] if self.per_frequency_calls else [freqs]
        # MEH (2026-10-31): a long sweep grows the persistent host's VRAM pool until a CUDA
        # launch failure on the 8 GB card (measured: 41 frequencies peaked 7,908/8,188 MiB and
        # died with code 719 after completing the sweep). ``worker_restart_every`` recycles the
        # host between chunks; absent = today's single host, so no other solve changes.
        restart_every = int((spec.extra or {}).get("worker_restart_every", 0) or 0)
        raws = []
        for index, g in enumerate(groups, start=1):
            if deadline is not None and time.perf_counter() > deadline:
                raise TimeoutError(f"solve exceeded timeout_s={self.timeout_s} after "
                                   f"{len(raws)}/{len(groups)} frequency calls")
            raws.append(beat.solve_frequencies(mesh.path, g, cfg))
            if restart_every and index % restart_every == 0 and index < len(groups):
                try:
                    worker.shutdown(verify=True)
                except Exception as exc:  # noqa: BLE001 - a surviving host is not fatal here
                    log.warning("worker recycle after %d/%d calls could not verify release (%r); "
                                "forcing recovery", index, len(groups), exc)
                    worker.recover_after_failure(self.name)
                worker.mark_cold(self.name)
        return _stack(raws, freqs)

    def _solve(self, mesh: MeshResult, spec: SolveSpec, *, surface_traces: bool):
        """One solve; a dead worker host (``worker_exit``) is recovered, re-warmed and the
        candidate retried ONCE, so a host crash is not scored as the design's failure. OOM and
        other failures are not retried (an OOM would recur on the same mesh)."""
        outcome, traces = self._attempt(mesh, spec, surface_traces=surface_traces)
        if outcome.ok or not outcome.message.startswith("[worker_exit]"):
            return outcome, traces
        log.warning("BEAT worker host died (%s); re-warming once and retrying this candidate",
                    outcome.message.splitlines()[0][:200])
        try:
            worker.warm(self)        # _failure already recovered: clients dropped, hosts killed
        except Exception as exc:     # noqa: BLE001 - a failed re-warm is this candidate's failure
            log.error("re-warm after worker_exit failed: %r", exc)
            return SolveOutcome(False, None, outcome.seconds, outcome.peak_vram_mb,
                                f"{outcome.message}\n(re-warm after worker_exit failed: {exc!r})"), None
        retry, traces = self._attempt(mesh, spec, surface_traces=surface_traces)
        if retry.ok:
            retry.response.meta["worker_exit_retries"] = 1
            return retry, traces
        return SolveOutcome(False, None, outcome.seconds + retry.seconds, retry.peak_vram_mb,
                            f"{retry.message}\n(after one re-warm and retry; first attempt: "
                            f"{outcome.message.splitlines()[0][:300]})"), None

    def _attempt(self, mesh: MeshResult, spec: SolveSpec, *, surface_traces: bool):
        t0 = time.perf_counter()
        check_symmetry_pairing(mesh)         # raises: a bug, not a failed candidate
        mon = worker.VramMonitor() if self.track_vram else None
        raw = None
        try:
            if mon is not None:
                with mon:
                    raw = self.solve_raw(mesh, spec, surface_traces=surface_traces)
            else:
                raw = self.solve_raw(mesh, spec, surface_traces=surface_traces)
            resp = _to_response(raw, spec, mesh)
        except Exception as exc:
            return self._failure(exc, t0, mon, mesh), None
        resp.backend = self.name
        seconds = time.perf_counter() - t0
        vram = None if mon is None else mon.peak_delta_mib
        if mon is not None:
            resp.meta["vram_baseline_mib"] = mon.baseline_mib
            resp.meta["vram_peak_mib"] = mon.peak_mib
        resp.meta["solve_seconds"] = seconds
        resp.meta["per_frequency_calls"] = self.per_frequency_calls
        worker.note_solve_seconds(self.name, seconds)
        traces = None
        if surface_traces:
            traces = {"pressure": np.asarray(raw.surface_pressure_complex),
                      "neumann": np.asarray(raw.surface_neumann_complex)}
        return SolveOutcome(True, resp, seconds, vram, ""), traces

    def _failure(self, exc: BaseException, t0: float, mon, mesh: MeshResult) -> SolveOutcome:
        tb = traceback.format_exc()
        kind = base.classify_failure(f"{type(exc).__name__}: {exc}\n{tb}")
        log.error("beat solve failed [%s]: %s", kind, tb[:2000])
        msg = f"[{kind}] {exc!r}\n{tb[-3000:]}"
        if kind in ("cuda_oom", "worker_exit"):
            if kind == "cuda_oom":
                base.note_failure_for_senior(
                    "cuda_oom", f"{exc!r} on {mesh.path} (n_triangles={mesh.n_triangles}, "
                                f"n_dof={mesh.n_dof}, quadrants={mesh.quadrants})",
                    context=f"{self.name} CUDA out of memory", notes_path=self.notes_path)
            worker.recover_after_failure(self.name)
        return SolveOutcome(False, None, time.perf_counter() - t0,
                            None if mon is None else mon.peak_delta_mib, msg)
