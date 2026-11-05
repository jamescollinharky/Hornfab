"""One candidate, end to end. ``evaluate`` NEVER raises (the search loop is never killed by one
bad candidate), with ONE deliberate exception: the mesh consistency errors (units bug, quadrants
vs symmetry flag, 01_CONTRACTS section 15) propagate and stop the run, because a wrong-units
horn solves fine and looks smooth.

Order of side effects for a non-cached candidate (08_TASK_PIPELINE section 3):
  mesh -> solve -> metrics -> objective -> solve cache -> traces -> DATASET RECORD -> ndjson row.
The dataset record is written BEFORE the ndjson append, so a crash between them loses a log line,
never a training record.

Cache semantics (documented choices, see NOTES_FOR_SENIOR):
  * ``ctx.known`` is the in-run memo, preloaded from ``search.ndjson`` on resume. A hit costs
    nothing, writes nothing (not a new ndjson row, not a new dataset record), consumes no budget.
    Successful rows and DETERMINISTIC failures (invalid geometry, mesh too large) are memoized;
    solver failures are not (a retry may succeed).
  * ``ctx.cache_dir/solve/<design>-<mesh>-<solve>/`` is the cross-run solve cache (hit requires
    ``ok: true``). A hit recomputes metrics and the objective from the stored Response with the
    CURRENT target and weights, appends an ndjson row flagged ``cached``, and writes a dataset
    record only if the store has none for that (design, mode) yet.
"""
from __future__ import annotations

import dataclasses
import functools
import json
import logging
import os
import subprocess
import time
import traceback
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

import numpy as np

from .. import config as config_mod
from ..dataset.record import DEFAULT_TRACE_FRACTION, build_record, should_capture_traces, to_jsonable
from ..design import families
from ..design.generators.registry import GeneratorError
from ..mesh.build import MeshConsistencyError, build_mesh, mounting_of
from ..metrics.compute import compute_metrics
from ..metrics.di import di_from_balloon, sin_theta_weights
from ..objective import PENALTY_FAILED, PENALTY_INVALID, objective, penalty_result
from ..objective.scalar_meh import MehParams, objective_meh
from ..objective.scalar_v2 import objective_v2, objective_v3
from ..objective.scalar_v4 import V4Params, objective_v4
from ..objective.scalar_v6 import V6Params, objective_v6
from ..objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
from ..solve import cache as solve_cache
from ..solve.base import stack_responses, theta_deg_from_dirs
from ..targets.spec import Target
from ..types import (Design, Evaluation, GeometryInvalidError, MeshResult, MeshTooLargeError,
                     MetricSet, Response, SolveOutcome)

log = logging.getLogger("hornlab_search.search.evaluate")

KIND_INVALID = "invalid_geometry"
KIND_INVALID_ENV = "invalid_envelope"   # WP3: pre-mesh envelope estimate violated (graded penalty)
KIND_TOO_LARGE = "mesh_too_large"
KIND_SOLVE = "solve_failed"
KIND_METRICS = "metrics_failed"
KIND_EXC = "exception"
#: Pure functions of the (design, brief): worth memoizing, and re-running them is wasted effort.
#: ``invalid_envelope`` is a function of the design params the generator built from a brief, so its
#: marker carries the brief hash as well (replay-validity, see ``_compute``).
DETERMINISTIC_KINDS = (KIND_INVALID, KIND_INVALID_ENV, KIND_TOO_LARGE)

#: WP8: the only band-split mesh policy name (rides SolveSpec.extra and the record provenance).
BAND_SPLIT_POLICY = "band_split_v1"

#: C10: the listening-window defaults used only when a hand-built ``meh:`` block omits them.
MEH_DEFAULT_WINDOW = {"h_deg": [0, 10, 20, 30], "v_deg": [10]}
MEH_DEFAULT_HP_HZ = 120.0
MEH_DEFAULT_MAX_BOOST_DB = 6.0

_FREQ_WEIGHTS_V1_WARNED = False


# ------------------------------------------------------------------ MEH branch (M7)
#
# The MEH path is switched on by the BRIEF's C10 ``meh:`` block, never by a config knob: a
# brief without it keeps every line of the single-source pipeline below byte-identical.  The
# branch meshes the labelled ``meh`` CAD STEP (M5), solves the source tags named by the brief
# groups (M3's ``SolveSpec.extra["source_tags"]``, C5), runs the lumped-network inner
# optimiser on the BEM response (M4), synthesises the system response, scores it with
# objective v5 (M6, C11) and records the BEM per-channel arrays + the chosen NetworkSolution.


def meh_block_of(cfg) -> dict | None:
    """The validated C10 ``meh:`` block of the brief, or None (a non-MEH evaluation)."""
    brief = getattr(cfg, "brief", None)
    if isinstance(brief, dict):
        block = brief.get("meh")
        if isinstance(block, dict):
            return block
    return None


def meh_source_tags(block: dict) -> tuple[int, ...]:
    """The C3 source tags named by the brief groups, sorted (CD = 2, mid entry = 10)."""
    groups = block.get("groups") or {}
    tags = sorted({int(g["tag"]) for g in groups.values()
                   if isinstance(g, dict) and g.get("tag") is not None})
    return tuple(tags)


def _with_meh_source_tags(sspec, block: dict):
    """``SolveSpec`` with ``extra["source_tags"]`` set. Only the MEH branch calls this, so the
    non-MEH solve hash/payload stays byte-identical (C5)."""
    tags = meh_source_tags(block)
    if not tags:
        return sspec
    extra = dict(sspec.extra or {})
    extra["source_tags"] = list(tags)
    return dataclasses.replace(sspec, extra=extra)


def warn_freq_weights_v1(cfg, target: Target) -> None:
    """WP4 (senior pass 2026-10-24): ``Target.freq_weights`` under objective v1 is IGNORED — warn
    once per process so the YAML is never honoured silently, and point at the opt-in. Never in
    the hot path more than once."""
    global _FREQ_WEIGHTS_V1_WARNED
    if _FREQ_WEIGHTS_V1_WARNED or getattr(cfg, "objective_version", 1) != 1 or not target.freq_weights:
        return
    log.warning("Target.freq_weights is set but objective v1 ignores it (WP4): per-frequency "
                "weights apply only under 'objective: {version: 2}' in the brief")
    _FREQ_WEIGHTS_V1_WARNED = True

TRACE_KIND = "p1_pressure_by_node+dp0_neumann_by_element"


# ------------------------------------------------------------------ provenance

_LIB_DISTS = {"hornlab_mesher": "hornlab_waveguide_mesher", "hornlab_beat_bem": "hornlab_beat_bem",
              "hornlab_bempp_bem": "hornlab_bempp_bem", "hornlab_plots": "hornlab_plots"}


def collect_lib_shas() -> dict:
    """The five SHAs every dataset record carries (record.REQUIRED_LIB_SHAS). The four HornLab
    packages come from each distribution's direct_url.json (the pinned git commit); this package's
    own commit from ``git rev-parse HEAD``. ``"unknown"`` when it cannot be determined."""
    out = {}
    for key, dist_name in _LIB_DISTS.items():
        sha = "unknown"
        for name in (dist_name, dist_name.replace("_", "-")):
            try:
                raw = distribution(name).read_text("direct_url.json")
            except PackageNotFoundError:
                continue
            if raw:
                try:
                    sha = (json.loads(raw).get("vcs_info") or {}).get("commit_id") or "unknown"
                except ValueError:
                    pass
            break
        out[key] = sha
    sha = "unknown"
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[2],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            sha = r.stdout.strip()
    except Exception:  # noqa: BLE001 - provenance is best effort
        pass
    out["hornlab_search"] = sha
    return out


# ------------------------------------------------------------------ context


@dataclass
class EvalContext:
    """Everything ``evaluate`` needs besides its contract arguments, shared across a run."""
    target: Target
    weights: dict
    lib_shas: dict
    cache_dir: Path | None = None
    trace_fraction: float = DEFAULT_TRACE_FRACTION
    known: dict = field(default_factory=dict)          # key -> lite Evaluation (resume / in-run)
    store_seen: set = field(default_factory=set)       # {(design_hash, mode, ok)} already in the store
    n_rows: int = 0                                    # rows in search.ndjson (next row number)
    counters: Counter = field(default_factory=Counter)
    write_ndjson: bool = True
    provenance: dict = field(default_factory=dict)     # config / brief identity for dataset records (R8)
    objective_version: int = 1                         # WP1: 2 when the brief/config opts in
    objective_params: object | None = None             # v4: the validated ``V4Params`` (tolerances...)

    @property
    def solve_cache_root(self) -> Path | None:
        return None if self.cache_dir is None else Path(self.cache_dir) / "solve"

    @property
    def mesh_cache_root(self) -> Path | None:
        return None if self.cache_dir is None else Path(self.cache_dir) / "mesh"


def record_provenance(cfg) -> dict:
    """Config name and design-brief identity (plan R8), folded into every dataset record."""
    from ..design.generated import brief_hash
    raw = getattr(cfg, "raw", None) or {}
    brief = raw.get("brief") if isinstance(raw.get("brief"), dict) else None
    return {"config": raw.get("name"), "brief": None if brief is None else brief.get("name"),
            "brief_hash": None if brief is None else brief_hash(brief)}


def make_context(cfg, store=None, *, cache_dir=None, lib_shas=None,
                 trace_fraction: float = DEFAULT_TRACE_FRACTION, ndjson: Path | None = None) -> EvalContext:
    ctx = EvalContext(target=Target.from_dict(cfg.target_raw), weights=dict(cfg.weights),
                      lib_shas=lib_shas if lib_shas is not None else collect_lib_shas(),
                      cache_dir=None if cache_dir is None else Path(cache_dir),
                      trace_fraction=float(trace_fraction))
    ctx.objective_version = int(getattr(cfg, "objective_version", 1))
    block = getattr(cfg, "objective_params", None)
    if block is None:
        ctx.objective_params = None
    elif ctx.objective_version == 5:
        # M6 bridge (M7 owns the MEH context): the v5 block carries the four C11 tolerances that
        # V4Params does not know, so it is validated with its own params class.
        ctx.objective_params = MehParams.from_block(block)
    elif ctx.objective_version == 6:
        ctx.objective_params = V6Params.from_block(block)
    else:
        ctx.objective_params = V4Params.from_block(block)
    ctx.provenance = record_provenance(cfg)
    if store is not None:
        ctx.store_seen = {(e.get("design_hash"), e.get("mode"), bool(e.get("ok"))) for e in store.index}
    if ndjson is not None:
        ctx.known, ctx.n_rows = load_known(ndjson)
    return ctx


# ------------------------------------------------------------------ metrics from a Response


def mouth_dims_m(mesh: MeshResult) -> tuple[float, float]:
    """(width along x, height along y) of the FULL horn, from the solved mesh's bounding box and
    the symmetry plane that reduced it. Includes the freestanding shell, so it is the outer
    envelope; an approximation of the mouth used only for the f_break design check."""
    b = mesh.bbox_m
    sp = mesh.symmetry_plane or ""
    w = (b[3] - b[0]) * (2.0 if "yz" in sp else 1.0)
    h = (b[4] - b[1]) * (2.0 if "xz" in sp else 1.0)
    return float(w), float(h)


#: Allowance on the brief's max depth for the outer shell and the source cap, which the meshed
#: bounding box includes but a generator's inner depth L does not.
ENVELOPE_DEPTH_ALLOWANCE_MM = 15.0


def envelope_violation(mesh: MeshResult, brief: dict | None) -> str:
    """'' if the meshed horn (outer envelope, shell included) fits the brief's size envelope,
    else a message. Applies to EVERY family, so typologies and Magnus's families compete inside
    the same box (a bigger mouth controls directivity lower; comparing across sizes is unfair)."""
    if not brief or mesh is None:
        return ""
    env = brief.get("envelope") or {}
    w, h = mouth_dims_m(mesh)
    b = mesh.bbox_m
    depth = (b[5] - b[2]) * 1000.0
    msgs = []
    if w * 1000.0 > float(env.get("max_mouth_w_mm", 1e9)) + 0.5:
        msgs.append(f"width {w * 1000:.0f} > {env['max_mouth_w_mm']} mm")
    if h * 1000.0 > float(env.get("max_mouth_h_mm", 1e9)) + 0.5:
        msgs.append(f"height {h * 1000:.0f} > {env['max_mouth_h_mm']} mm")
    if depth > float(env.get("max_depth_mm", 1e9)) + ENVELOPE_DEPTH_ALLOWANCE_MM:
        msgs.append(f"depth {depth:.0f} > {env['max_depth_mm']} + {ENVELOPE_DEPTH_ALLOWANCE_MM:.0f} mm")
    return ("outside the brief envelope (" + ", ".join(msgs) + ")") if msgs else ""


def throat_radius_m(design: Design) -> float | None:
    """Throat radius in metres for the f11 throat-mode estimate. FREEFORM has no ``r0_mm``: its
    throat is anchor 0 of the two meridians (the smaller radius bounds the first mode)."""
    r0 = design.params.get("r0_mm")
    if isinstance(r0, (int, float)) and not isinstance(r0, bool) and r0 > 0:
        return float(r0) / 1000.0
    if design.family == "FREEFORM":
        radii = []
        for plane in ("profileH", "profileV"):
            try:
                r = float(design.params[plane]["points"][0][1])
            except (KeyError, IndexError, TypeError, ValueError):
                return None
            radii.append(r)
        r = min(radii)
        return r / 1000.0 if r > 0 else None
    return None


def metrics_from_response(resp: Response, target: Target, *, mesh: MeshResult | None = None,
                          design: Design | None = None) -> MetricSet:
    """``compute_metrics`` with the balloon DI done correctly.

    The solver's balloon is a THETA-PHI grid (``resp.meta['balloon_grid']``), not the equal-area
    set ``compute_metrics`` assumes (equal weights would over-count the poles). compute_metrics
    is not ours to edit, so the sin(theta) quadrature is done HERE with
    ``di_from_balloon(weights=sin_theta_weights(theta))`` and handed to compute_metrics as a
    one-column "balloon" whose single power equals the weighted mean, which makes compute_metrics'
    own equal-weight DI come out as exactly the weighted DI (and keeps di_source == 'balloon',
    its slope, mean and every other scalar consistent). A balloon without ``balloon_grid`` in meta
    is taken to be equal-area (e.g. a Fibonacci set) and passed through untouched.
    """
    kw = {}
    if mesh is not None:
        kw["mouth_h_m"], kw["mouth_v_m"] = mouth_dims_m(mesh)
    if design is not None:
        kw["throat_radius_m"] = throat_radius_m(design)
    raw = resp
    has_balloon = resp.spl_balloon_db is not None and resp.balloon_dirs is not None
    if has_balloon and resp.meta.get("balloon_grid") is not None:
        bal = np.asarray(resp.spl_balloon_db, dtype=float)
        w = sin_theta_weights(theta_deg_from_dirs(np.asarray(resp.balloon_dirs, dtype=float)))
        ax = resp.axis_index
        collapsed = np.empty((bal.shape[0], 1))
        for i in range(bal.shape[0]):
            di = di_from_balloon(bal[i], resp.spl_h_db[i, ax], weights=w)
            # di_from_balloon(collapsed) = -10 log10(10**((collapsed - ax)/10)) = ax - collapsed
            collapsed[i, 0] = float(resp.spl_h_db[i, ax]) - di
        resp = dataclasses.replace(resp, spl_balloon_db=collapsed,
                                   balloon_dirs=np.array([[0.0, 0.0, 1.0]]))
    m = compute_metrics(resp, target, **kw)
    m.scalars.update(directivity_extras(raw, m, target))
    m.scalars.update(loading_extras(m.freqs_hz, m.z_throat_real, target))
    return m


#: Report-only throat-loading scalars (docs/TYPOLOGY_PLAN.md s6). Never weighted into J (the
#: existing ``load`` term does that when a brief asks for it).
LOADING_KEYS = ("f_load_hz", "z_ripple", "z_mean_band")
LOAD_THRESHOLD = 0.7     # Re(z)/rho*c that counts as "loaded" (plane-wave duct = 1.0)


def loading_extras(freqs_hz, z_real, target: Target) -> dict:
    """``f_load_hz``: lowest solved frequency from which Re z stays >= LOAD_THRESHOLD (NaN if it
    never does); ``z_ripple``: std of Re z at and above f_load inside the band (coarse on a 12-point
    grid: a screen for mouth reflections, not a measurement); ``z_mean_band``: mean Re z in the
    band. Never raises."""
    out = {k: float("nan") for k in LOADING_KEYS}
    try:
        if z_real is None:
            return out
        f = np.asarray(freqs_hz, dtype=float)
        z = np.asarray(z_real, dtype=float)
        ok = np.isfinite(z)
        above = (z >= LOAD_THRESHOLD) & ok
        for i in range(len(z)):
            if above[i:].all():
                out["f_load_hz"] = float(f[i])
                break
        band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz) & ok
        if band.any():
            out["z_mean_band"] = float(np.mean(z[band]))
        if np.isfinite(out["f_load_hz"]):
            sel = band & (f >= out["f_load_hz"])
            if sel.sum() >= 2:
                out["z_ripple"] = float(np.std(z[sel]))
    except Exception:  # noqa: BLE001 - report-only
        log.debug("loading extras failed", exc_info=True)
    return out


#: Report-only scalars added by ``directivity_extras`` (never weighted into J).
EXTRA_SCALAR_KEYS = ("spdi_mean_db", "spdi_range_db", "lw_minus_on_axis_mean_db",
                     "beam_p_mean", "beam_p_residual_pct_mean", "beam_p_n_valid",
                     "throat_angle_mismatch_deg")


def _design_throat_angles_deg(design: Design) -> list[float]:
    """The design's throat wall angle(s) in degrees, per plane where it is defined.

    OSSE/R-OSSE/ICW carry one ``a0_deg``; generated and native FREEFORM designs carry
    ``profileH.throatAngleDeg`` / ``profileV.throatAngleDeg``. Empty list when the family exposes
    no throat-angle key (then the mismatch is undefined, not zero)."""
    p = design.params.get("a0_deg")
    if isinstance(p, (int, float)) and not isinstance(p, bool):
        return [float(p)]
    out = []
    for plane in ("profileH", "profileV"):
        v = (design.params.get(plane) or {}).get("throatAngleDeg")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append(float(v))
    return out


def _throat_angle_mismatch_deg(design: Design, brief: dict | None) -> float | None:
    """WP2 report scalar: |throat angle - brief driver exit angle| in degrees, the WORST plane
    for H/V designs. None when there is no brief or the family has no throat angle."""
    if not brief:
        return None
    exit_a = (brief.get("driver") or {}).get("exit_angle_deg")
    if not isinstance(exit_a, (int, float)):
        return None
    angles = _design_throat_angles_deg(design)
    if not angles:
        return None
    return float(max(abs(a - float(exit_a)) for a in angles))


def directivity_extras(resp: Response, m: MetricSet, target: Target) -> dict:
    """CEA-2034 subset (listening window, sound-power DI) and forward beam shape, as REPORT-ONLY
    scalars over the target band (ideas after Boundary Lab 0.5.0; see metrics/spinorama.py and
    metrics/beam_shape.py). Never raises: a failure here must not fail a solve; the keys are then
    NaN. ``beam_p_mean`` is qualitative at screen balloon resolution (it reads low for square
    beams, p > 4); use it to compare designs, not as an absolute."""
    from ..metrics.beam_shape import band_mean, forward_beam_shape
    from ..metrics.spinorama import listening_window_db, spdi_db

    out = {k: float("nan") for k in EXTRA_SCALAR_KEYS}
    f = np.asarray(resp.freqs_hz, dtype=float)
    lo, hi = target.band_lo_hz, target.band_hi_hz
    try:
        ax = resp.axis_index
        on_axis = np.asarray(resp.spl_h_db, dtype=float)[:, ax]
        lw = listening_window_db(resp.h_angles_deg, resp.spl_h_db, resp.v_angles_deg, resp.spl_v_db)
        if m.di_source == "balloon":
            spdi = spdi_db(lw, on_axis, m.di_db)
            band = (f >= lo) & (f <= hi) & np.isfinite(spdi)
            out["spdi_mean_db"] = band_mean(spdi, f, lo, hi)
            out["spdi_range_db"] = float(np.ptp(spdi[band])) if band.any() else float("nan")
        out["lw_minus_on_axis_mean_db"] = band_mean(lw - on_axis, f, lo, hi)
    except Exception:  # noqa: BLE001 - report-only metric; never fail the solve
        log.debug("listening-window/SPDI extras failed", exc_info=True)
    try:
        if resp.spl_balloon_db is not None and resp.balloon_dirs is not None:
            bs = forward_beam_shape(resp.balloon_dirs, resp.spl_balloon_db,
                                    on_axis_db=np.asarray(resp.spl_h_db, dtype=float)[:, resp.axis_index])
            p = np.asarray(bs["p"], dtype=float)
            band = (f >= lo) & (f <= hi) & np.isfinite(p)
            out["beam_p_mean"] = band_mean(p, f, lo, hi)
            out["beam_p_residual_pct_mean"] = band_mean(bs["residual_pct"], f, lo, hi)
            out["beam_p_n_valid"] = float(band.sum())
    except Exception:  # noqa: BLE001 - report-only metric; never fail the solve
        log.debug("beam-shape extras failed", exc_info=True)
    return out


# ------------------------------------------------------------------ rows (search.ndjson)


def _arr(x):
    return None if x is None else np.asarray(x, dtype=float).tolist()


def metrics_to_json(m: MetricSet | None) -> dict | None:
    if m is None:
        return None
    return to_jsonable({"freqs_hz": m.freqs_hz, "bw_h_deg": m.bw_h_deg, "bw_v_deg": m.bw_v_deg,
                        "di_db": m.di_db, "di_source": m.di_source, "ripple_h_db": m.ripple_h_db,
                        "ripple_v_db": m.ripple_v_db, "on_axis_db": m.on_axis_db,
                        "z_throat_real": m.z_throat_real, "scalars": m.scalars})


def _nanarr(x) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in x], dtype=float)


def metrics_from_json(d: dict | None) -> MetricSet | None:
    if not d:
        return None
    return MetricSet(
        freqs_hz=_nanarr(d["freqs_hz"]), bw_h_deg=_nanarr(d["bw_h_deg"]),
        bw_v_deg=_nanarr(d["bw_v_deg"]), di_db=_nanarr(d["di_db"]), di_source=d["di_source"],
        ripple_h_db=_nanarr(d["ripple_h_db"]), ripple_v_db=_nanarr(d["ripple_v_db"]),
        on_axis_db=_nanarr(d["on_axis_db"]),
        z_throat_real=None if d.get("z_throat_real") is None else _nanarr(d["z_throat_real"]),
        scalars=dict(d.get("scalars") or {}))


def error_kind(error: str) -> str:
    return error.split(":", 1)[0] if error else ""


def evaluation_to_row(ev: Evaluation, mode: str, n: int, seconds: dict,
                      objective_version: int = 1) -> dict:
    m = ev.mesh
    out = ev.outcome
    return to_jsonable({
        "n": n, "mode": mode, "key": f"{ev.design_hash}-{ev.mesh_hash}-{ev.solve_hash}",
        "design_hash": ev.design_hash, "mesh_hash": ev.mesh_hash, "solve_hash": ev.solve_hash,
        "family": ev.design.family, "params": ev.design.params,
        "objective_version": int(objective_version),
        "objective": ev.objective, "terms": ev.terms, "ok": not ev.error, "error": ev.error,
        "kind": error_kind(ev.error), "cached": ev.cached, "seconds": seconds,
        "n_dof": None if m is None else m.n_dof,
        "n_triangles": None if m is None else m.n_triangles,
        "quadrants": None if m is None else m.quadrants,
        "symmetry_plane": None if m is None else m.symmetry_plane,
        "bbox_m": None if m is None else list(m.bbox_m),
        "res_mm": None if m is None else m.res_mm,
        "peak_vram_mb": None if out is None else out.peak_vram_mb,
        "metrics": metrics_to_json(ev.metrics),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


def row_to_evaluation(row: dict) -> Evaluation:
    """A lite Evaluation (no Response) from an ndjson row; ``cached`` is True."""
    mesh = None
    if row.get("n_triangles") is not None:
        mesh = MeshResult(path="", n_triangles=int(row["n_triangles"]), n_dof=row.get("n_dof"),
                          quadrants=row.get("quadrants") or "", symmetry_plane=row.get("symmetry_plane"),
                          res_mm=dict(row.get("res_mm") or {}),
                          bbox_m=tuple(row.get("bbox_m") or (0,) * 6),
                          seconds=float((row.get("seconds") or {}).get("mesh") or 0.0))
    ok = bool(row.get("ok"))
    outcome = SolveOutcome(ok, None, float((row.get("seconds") or {}).get("solve") or 0.0),
                           row.get("peak_vram_mb"), "" if ok else str(row.get("error", "")))
    return Evaluation(
        design_hash=row["design_hash"], design=Design(row["family"], dict(row["params"])),
        mesh_hash=row["mesh_hash"], solve_hash=row["solve_hash"], objective=float(row["objective"]),
        terms=dict(row["terms"]), metrics=metrics_from_json(row.get("metrics")), mesh=mesh,
        outcome=outcome, cached=True, error=str(row.get("error") or ""))


def append_ndjson(path: Path, row: dict) -> None:
    """One line, opened in append mode per write, flushed and fsynced: a hard kill leaves every
    earlier line intact and at worst a torn LAST line (which readers skip)."""
    line = json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n"
    with open(path, "ab") as f:
        f.write(line.encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())


def read_ndjson(path: Path) -> list[dict]:
    """Every parseable line; a torn final line (hard kill) is skipped."""
    rows = []
    p = Path(path)
    if not p.exists():
        return rows
    for i, line in enumerate(p.read_bytes().decode("utf-8", errors="replace").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            log.warning("%s line %d is not valid JSON (torn write?); skipped", p, i + 1)
    return rows


def load_known(path: Path) -> tuple[dict, int]:
    """({key: lite Evaluation}, number of rows) from an existing search.ndjson."""
    rows = read_ndjson(path)
    known = {}
    for r in rows:
        if r.get("ok") or r.get("kind") in DETERMINISTIC_KINDS:
            try:
                known[r["key"]] = row_to_evaluation(r)
            except Exception as exc:  # noqa: BLE001 - a bad old row is skipped, not fatal
                log.warning("could not reload ndjson row %s: %s", r.get("n"), exc)
    return known, len(rows)


# ------------------------------------------------------------------ evaluate


#: The small per-record ``cad`` echo (WP14). The FULL block (derived geometry, frequency
#: report, repair/topology) stays on disk in ``<mesh_dir>/mesh_meta.json["cad"]``.
CAD_ECHO_KEYS = ("tool", "tool_sha256", "recipe", "step_sha256", "face_inventory")


def _grid_info(mesh_dir: Path) -> tuple[float | None, dict]:
    """(area_m2 of the solved mesh, mesh.grid block) from build_mesh's mesh_meta.json.

    The mesher's structured surface sampling is ``angular_segments x length_segments`` (defaults 64
    x 32 in hornlab_mesher). ``available`` is True for a formula-route mesh: the grid itself is
    reachable through the mesher's public ``config_builder.build_point_grid`` (TOOLCHAIN C4) and is
    regenerated from the recorded params; it is not stored per record.

    A **cad-route** mesh (``mesh_meta.json`` carries a ``cad`` block) has NO grid recipe: its
    ``available`` is False with null segment counts, and the honest provenance is the additive
    ``cad`` echo in :func:`_cad_info`."""
    area = None
    seg = {"angular_segments": 64, "length_segments": 32}
    cad = False
    try:
        meta = json.loads((Path(mesh_dir) / "mesh_meta.json").read_text(encoding="utf-8"))
        area = float(meta["summary"]["area_m2"])
        cad = isinstance(meta.get("cad"), dict)
        if not cad:
            msec = (meta.get("mesher_config") or {}).get("mesh") or {}
            for k in seg:
                if msec.get(k) is not None:
                    seg[k] = int(msec[k])
    except Exception as exc:  # noqa: BLE001
        log.debug("no mesh_meta.json in %s: %s", mesh_dir, exc)
    if cad:
        return area, {"angular_segments": None, "length_segments": None, "available": False}
    return area, {**seg, "available": True}


def _cad_info(mesh_dir: Path) -> dict | None:
    """Additive cad-route provenance echo for dataset records/ndjson rows, or None.

    Mirrors the WP8 ``mesh_policy`` precedent: only a cad-row carries it, so formula and GRID
    rows stay byte-identical. The subset is deliberately small (recipe + tool sha + step sha +
    face inventory); the full meta remains on disk beside the mesh.
    """
    try:
        meta = json.loads((Path(mesh_dir) / "mesh_meta.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.debug("no mesh_meta.json in %s: %s", mesh_dir, exc)
        return None
    cad = meta.get("cad")
    if not isinstance(cad, dict):
        return None
    return {k: cad.get(k) for k in CAD_ECHO_KEYS}


def _cad_meta(mesh_dir: Path) -> dict | None:
    """The FULL ``mesh_meta.json["cad"]`` block (recipe + derived layout), or None.

    ``_cad_info`` keeps the small record echo; the MEH branch needs the tool's ``derived()``
    (port area, neck, repair log) and the recipe it was built from, which are too large for a
    per-row echo but are exactly what the inner network optimiser consumes (C9/C12)."""
    try:
        meta = json.loads((Path(mesh_dir) / "mesh_meta.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.debug("no mesh_meta.json in %s: %s", mesh_dir, exc)
        return None
    cad = meta.get("cad")
    return cad if isinstance(cad, dict) else None


def _mid_ports_meta(mesh_dir: Path) -> dict | None:
    """``mesh_meta.json["mid_ports"]`` from the OSSE mesher-fork path, or None."""
    try:
        meta = json.loads((Path(mesh_dir) / "mesh_meta.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.debug("no mesh_meta.json in %s: %s", mesh_dir, exc)
        return None
    block = meta.get("mid_ports")
    return block if isinstance(block, dict) else None


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(to_jsonable(obj), indent=1, sort_keys=True), encoding="utf-8")


# ------------------------------------------------------------------ WP8 band split


def band_split_of(cfg) -> dict | None:
    """The validated ``mesh.band_split`` block, or None (today's single-mesh policy)."""
    return getattr(getattr(cfg, "mesh", None), "band_split", None)


def split_freq_bands(freqs_hz, edges_hz) -> list[tuple[float, ...]]:
    """Partition the WHOLE mode grid into bands ``(lo_i, hi_i]`` around strictly increasing edges.

    The first band has no lower edge (it keeps the mode grid's sub-band points) and the last band
    keeps every frequency above the final edge, so the frequency grid and label space are unchanged.
    """
    freqs = [float(f) for f in freqs_hz]
    edges = [float(e) for e in edges_hz]
    if not freqs:
        raise ValueError("band_split: no frequencies to partition")
    if any(b <= a for a, b in zip(edges, edges[1:])):
        raise ValueError(f"band_split: edges must be strictly increasing, got {edges}")
    bounds = [float("-inf"), *edges, float("inf")]
    bands: list[tuple[float, ...]] = []
    for lo, hi in zip(bounds, bounds[1:]):
        band = tuple(f for f in freqs if lo < f <= hi)
        if not band:
            raise ValueError(f"band_split: no frequencies in band ({lo:g}, {hi:g}]")
        bands.append(band)
    return bands


def _first_above(freqs_hz, edge_hz: float) -> float:
    for f in freqs_hz:
        if float(f) > edge_hz:
            return float(f)
    raise ValueError(f"band_split seam check: no frequency above edge {edge_hz:g} Hz")


def _seam_check(design_hash: str, sspec, mesh_specs, meshes, merged: Response, backend,
                ctx) -> dict:
    """Verify-mode only: solve the first frequency above each edge on the LOWER band's mesh and
    record the on-axis / beamwidth difference against the upper band's value (WP8 seam gate)."""
    from ..metrics.polar import beamwidth_deg

    out: dict = {}
    axis = merged.axis_index
    resp_freqs = [float(f) for f in merged.freqs_hz]
    for i, edge in enumerate(sspec.extra["band_edges_hz"]):
        f = _first_above(sspec.freqs_hz, edge)
        seam_spec = dataclasses.replace(sspec, freqs_hz=(f,))
        bkey = solve_cache.key(design_hash, mesh_specs[i].hash(), seam_spec.hash())
        root = ctx.solve_cache_root
        resp = solve_cache.lookup(bkey, root) if root is not None else None
        if resp is None:
            outcome = backend.solve(meshes[i], seam_spec)
            if not outcome.ok or outcome.response is None:
                msg = (outcome.message or "no response")[:300]
                log.warning("band-split seam check at %.0f Hz failed: %s", edge, msg)
                # Oracle NICE (M3): write the failure so an absent seam edge is never ambiguous.
                out[f"{edge:g}"] = {"freq_hz": f, "error": msg}
                continue
            resp = outcome.response
            if root is not None:
                try:
                    solve_cache.store(bkey, root, resp, {"ok": True, "objective": None,
                                                         "n_dof": resp.n_dof, "mode": "verify"})
                except Exception as exc:  # noqa: BLE001 - seam bookkeeping only
                    log.warning("seam solve cache write failed: %s", exc)
        j = resp_freqs.index(f)
        lower_ax = float(np.asarray(resp.spl_h_db, dtype=float)[0, axis])
        upper_ax = float(np.asarray(merged.spl_h_db, dtype=float)[j, axis])
        bw_lh, _ = beamwidth_deg(merged.h_angles_deg, np.asarray(resp.spl_h_db, dtype=float)[0])
        bw_uh, _ = beamwidth_deg(merged.h_angles_deg, np.asarray(merged.spl_h_db, dtype=float)[j])
        bw_lv, _ = beamwidth_deg(merged.v_angles_deg, np.asarray(resp.spl_v_db, dtype=float)[0])
        bw_uv, _ = beamwidth_deg(merged.v_angles_deg, np.asarray(merged.spl_v_db, dtype=float)[j])
        out[f"{edge:g}"] = {
            "freq_hz": f,
            "on_axis_delta_db": lower_ax - upper_ax,
            "bw_h_delta_deg": float(bw_lh - bw_uh),
            "bw_v_delta_deg": float(bw_lv - bw_uv),
        }
    return out


def evaluate(design: Design, space, cfg, mode: str, run_dir, store, backend, *,
             ctx: EvalContext | None = None) -> Evaluation:
    """One candidate, end to end. NEVER raises (except ``MeshConsistencyError``, see module doc).

    ``space`` is accepted for the contract signature (a surrogate evaluator will use it); ``ctx``
    carries the target, weights, caches and counters shared across a run (built on the fly when
    omitted, which is what a one-off call wants).
    """
    # ABSOLUTE: the Julia host resolves a relative mesh path against its own working directory
    # (found live: `--resume runs\<dir>` made every solve fail with "opening file ... No such file").
    run_dir = Path(run_dir).resolve()
    ctx = ctx or make_context(cfg, store)
    warn_freq_weights_v1(cfg, ctx.target)
    t_start = time.perf_counter()
    mspec = config_mod.mesh_spec(mode, cfg)
    sspec = config_mod.solve_spec(mode, cfg)
    meh = meh_block_of(cfg)
    if meh is not None:
        # C5: multi-source solve. The tags ride in SolveSpec.extra, so they are part of the
        # solve hash (cache, resume memo and record provenance) exactly like every other knob.
        sspec = _with_meh_source_tags(sspec, meh)
    dh, mh, sh = design.hash(), mspec.hash(), sspec.hash()
    # WP12: MeshSpec.hash does not know about the rear enclosure, so the normalized mounting block
    # rides in the key itself (run-known memo + solve-cache identity). Absent -> today's key.
    mkey = families.mounting_key(mounting_of(cfg))
    key = f"{dh}-{mh}-{sh}" + (f"-{mkey}" if mkey else "")

    hit = ctx.known.get(key)
    if hit is not None:
        ctx.counters["cache_hits_run"] += 1
        log.info("eval %s J=%.4f cached=True (in-run/resume)", dh, hit.objective)
        return dataclasses.replace(hit, design=design)

    design_dir = run_dir / "designs" / dh
    st: dict = {"mesh": None, "outcome": None, "resp": None, "metrics": None, "kind": "", "err": "",
                "from_disk": False, "area": None, "grid": None, "cad": None, "raw_traces": None,
                "J": None, "terms": None}
    try:
        _compute(design, cfg, mode, mspec, sspec, key, design_dir, backend, ctx, st)
    except MeshConsistencyError:
        raise                                   # units / symmetry bug: stop the run (section 15)
    except Exception as exc:  # noqa: BLE001 - the contract: any unexpected exception is a penalty row
        st["kind"], st["err"] = KIND_EXC, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        log.error("evaluation %s raised: %s", dh, st["err"][:2000])

    kind = st["kind"]
    if kind in DETERMINISTIC_KINDS and not st.get("fail_cached") and not st.get("no_marker"):
        marker = _failure_marker(ctx, key)
        if marker is not None:
            try:
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text(json.dumps({"kind": kind, "error": str(st["err"])[:4000],
                                              "lib_shas": ctx.lib_shas,
                                              "brief_hash": ctx.provenance.get("brief_hash")},
                                             default=str), encoding="utf-8")
            except Exception as exc:  # noqa: BLE001 - bookkeeping only
                log.warning("could not write failure marker %s: %s", marker, exc)
    if hasattr(space, "provenance"):
        try:
            st["generator"] = space.provenance(design)
        except Exception:  # noqa: BLE001 - provenance is bookkeeping
            log.debug("generator provenance failed", exc_info=True)
    if kind:
        err = f"{kind}: {st['err']}"
        J, terms = penalty_result(_failure_penalty(kind, design, cfg))
    else:
        err, J, terms = "", st["J"], st["terms"]
    mesh, outcome = st["mesh"], st["outcome"]
    if outcome is None and kind:
        outcome = SolveOutcome(False, None, 0.0, None, err)
    ev = Evaluation(design_hash=dh, design=design, mesh_hash=mh, solve_hash=sh, objective=float(J),
                    terms=terms, metrics=None if kind else st["metrics"], mesh=mesh, outcome=outcome,
                    cached=bool((st["from_disk"] and not kind) or st.get("fail_cached")), error=err)
    seconds = {"mesh": 0.0 if mesh is None else float(mesh.seconds),
               "solve": 0.0 if (outcome is None or st["from_disk"]) else float(outcome.seconds),
               "total": time.perf_counter() - t_start}
    try:
        _persist(ev, mode, sspec, design_dir, ctx, store, st, seconds)
    except Exception:  # noqa: BLE001 - bookkeeping must not kill a search
        log.error("persisting evaluation %s failed:\n%s", dh, traceback.format_exc()[:2000])

    ctx.counters["cache_hits_disk" if ev.cached else "evaluated"] += 1
    if kind:
        ctx.counters[f"failure:{kind}"] += 1
    ctx.counters["mesh_seconds"] += seconds["mesh"]
    ctx.counters["solve_seconds"] += seconds["solve"]
    log.info("eval %s J=%.4f mesh=%.1fs solve=%.1fs dofs=%s cached=%s%s", dh, ev.objective,
             seconds["mesh"], seconds["solve"], None if mesh is None else mesh.n_dof, ev.cached,
             f" FAILED[{kind}]" if kind else "")
    return ev


def _failure_penalty(kind: str, design: Design, cfg) -> float:
    """The penalty J for an expected-failure kind. WP3 (senior pass 2026-10-24): with
    ``search: {infeasible_penalty: graded}`` a pre-mesh envelope violation (kind invalid_envelope)
    is graded by the generator's relative overshoot capped at 2·PENALTY_INVALID; the default
    'flat' keeps today's flat PENALTY_INVALID. Other kinds are unchanged."""
    from ..design.generated import GENERATOR_OVERSHOOT_KEY
    from ..objective.terms import graded_infeasible_penalty

    if kind == KIND_INVALID_ENV and getattr(cfg, "search", None) is not None and \
            getattr(cfg.search, "infeasible_penalty", "flat") == "graded":
        over = design.params.get(GENERATOR_OVERSHOOT_KEY)
        if isinstance(over, (int, float)) and not isinstance(over, bool) and np.isfinite(float(over)):
            return graded_infeasible_penalty(float(over))
        return graded_infeasible_penalty(0.0)          # == PENALTY_INVALID
    return PENALTY_INVALID if kind in DETERMINISTIC_KINDS else PENALTY_FAILED


def _failure_marker(ctx: EvalContext, key: str) -> Path | None:
    """Where a DETERMINISTIC failure of this exact (design, mesh spec, solve spec) key is
    remembered across runs, so a replay with the same CMA seed does not spend budget re-failing
    it (ISSUES 2026-10-22). The key already includes the mesh spec (mode, epw, dof cap)."""
    root = ctx.solve_cache_root
    return None if root is None else Path(root) / "failures" / f"{key}.json"


#: The objective dispatch table. Its keys MUST equal
#: ``objective.versions.SUPPORTED_OBJECTIVE_VERSIONS`` - the dataset record validator uses the
#: same tuple, so a version cannot be scored without also being recordable (or recorded without
#: being scorable). Checked once, at import, so drift fails loudly.
def _score_v4(metrics, resp, target, weights, params):
    if params is None:
        raise ValueError("objective_version 4 needs the brief's objective block (tolerances); the "
                         "evaluation context carries none")
    return objective_v4(metrics, resp, True, target, weights, params)


def _score_v5(metrics, resp, target, weights, params, meh_ctx=None):
    """Objective v5 (C11). ``meh_ctx`` is built by the MEH branch (M7) from the synthesised
    response + the chosen NetworkSolution. When it is absent (e.g. a v5 brief evaluated through
    the legacy single-source path) the four system terms score their unmeasurable fill while
    the v4 pattern terms stay real - the M6 bridge behaviour, kept for non-MEH callers."""
    if params is None:
        raise ValueError("objective_version 5 needs the brief's objective block; the evaluation "
                         "context carries none")
    if not isinstance(params, MehParams):
        params = MehParams.from_block(params)
    return objective_meh(metrics, resp, True, target, weights, params, meh_ctx)


def _score_v6(metrics, resp, target, weights, params):
    if params is None:
        raise ValueError("objective_version 6 needs the brief's objective block (tolerances); the "
                         "evaluation context carries none")
    if not isinstance(params, V6Params):
        params = V6Params.from_block(params)
    return objective_v6(metrics, resp, True, target, weights, params)


_OBJECTIVE_SCORERS = {
    1: lambda metrics, resp, target, weights, params: objective(metrics, True, target, weights),
    2: lambda metrics, resp, target, weights, params: objective_v2(metrics, resp, True, target, weights),
    3: lambda metrics, resp, target, weights, params: objective_v3(metrics, resp, True, target, weights),
    4: _score_v4,
    5: _score_v5,
    6: _score_v6,
}
if tuple(sorted(_OBJECTIVE_SCORERS)) != SUPPORTED_OBJECTIVE_VERSIONS:
    raise RuntimeError(
        "objective dispatch table and objective.versions.SUPPORTED_OBJECTIVE_VERSIONS "
        f"disagree: {tuple(sorted(_OBJECTIVE_SCORERS))} vs {SUPPORTED_OBJECTIVE_VERSIONS}")


def _stamp_design_fc_hz(metrics: MetricSet, design: Design | None) -> None:
    """Copy the design's area-law cutoff into ``metrics.scalars['fc_hz']`` for objective v6.

    Looks at common knob names used by Le Cléac'h / rows generators. Absent = leave scalars alone
    so ``resolve_fc_hz`` falls back to the brief's ``f0_hz``.
    """
    if metrics is None or design is None:
        return
    params = getattr(design, "params", None) or {}
    for key in ("g_fc_hz", "fc_hz", "h_fc_hz"):
        v = params.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v) > 0.0:
            metrics.scalars["fc_hz"] = float(v)
            return
        # Nested plane blocks (FREEFORM typology knobs).
        if isinstance(v, dict):
            continue
    for plane in ("profileH", "profileV", "h", "v"):
        block = params.get(plane)
        if isinstance(block, dict):
            for key in ("fc_hz", "g_fc_hz"):
                v = block.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v) > 0.0:
                    metrics.scalars["fc_hz"] = float(v)
                    return


def _score(metrics, resp, ctx, meh_ctx=None) -> tuple[float, dict]:
    """The objective dispatch (WP1, senior pass 2026-10-24): version 1 keeps the exact v1 path
    (and every old run reproduces bit-for-bit); version 2 (brief/config``objective: {version: 2}``)
    scores with the detrended terms in ``objective/scalar_v2.py``. Version 3 (2026-10-25,
    owner-approved): freq-weighted cov + the below-f0 (K-law design frequency) mask on
    cov/dislope - see ``objective_v3`` in scalar_v2.py. Version 4 (2026-10-27): tolerance-normalised
    terms plus asymmetric coverage, DI std and the diagonal term - ``objective/scalar_v4.py``.
    Version 6 (2026-11-05): loading_smooth for Le Cléac'h / rollback - ``objective/scalar_v6.py``.

    The allowed versions are the single source of truth in ``objective/versions.py``, shared with
    the dataset record validator. An unsupported version fails loudly instead of silently scoring
    v1, so a future version cannot half-land."""
    scorer = _OBJECTIVE_SCORERS.get(int(ctx.objective_version))
    if scorer is None:
        raise ValueError(f"objective_version {ctx.objective_version!r} is not one of "
                         f"{SUPPORTED_OBJECTIVE_VERSIONS}")
    if int(ctx.objective_version) == 5:
        # M7: the MEH branch supplies the per-candidate meh_ctx (LW, polars, xo_hz, SPL_max).
        # A non-MEH v5 caller passes None and keeps the M6 bridge behaviour.
        return _score_v5(metrics, resp, ctx.target, ctx.weights,
                         getattr(ctx, "objective_params", None), meh_ctx)
    return scorer(metrics, resp, ctx.target, ctx.weights, getattr(ctx, "objective_params", None))


def _compute_band_split(design, cfg, mode, mspec, sspec, design_dir, backend, ctx, st) -> None:
    """WP8: one mesh per band (f_max = the band top), solve that band's frequencies on it, stack.

    The mesh cache key naturally includes each band's MeshSpec hash; each band's solve also gets
    its own solve-cache entry, so a resumed/cross-run candidate only pays for the bands it lacks.
    """
    bands = split_freq_bands(sspec.freqs_hz, cfg.mesh.band_split["edges_hz"])
    # Band i's mesh resolves its UPPER BOUND hi_i (the edge, or the mode grid top for the last
    # band), exactly as the WP8 spec states, not merely its highest solved frequency.
    band_tops = [float(e) for e in cfg.mesh.band_split["edges_hz"]] + [float(sspec.freqs_hz[-1])]
    st["mesh_policy"] = BAND_SPLIT_POLICY
    responses: list[Response] = []
    mesh_specs = []
    meshes: list[MeshResult] = []
    from_disk: list[bool] = []
    solve_seconds = 0.0
    peak_vram = None
    root = ctx.solve_cache_root
    want_traces = store_wants_traces(ctx, design) and hasattr(backend, "solve_traced")
    for i, band in enumerate(bands):
        bdir = design_dir / f"band{i}"
        bmspec = dataclasses.replace(mspec, f_max_hz=band_tops[i])
        bsspec = dataclasses.replace(sspec, freqs_hz=tuple(band))
        try:
            bmesh = build_mesh(design, bmspec, cfg, bdir, mode=mode, cache_dir=ctx.mesh_cache_root)
        except GeometryInvalidError as exc:
            st["kind"], st["err"] = KIND_INVALID, str(exc)
            return
        except MeshTooLargeError as exc:
            st["kind"], st["err"] = KIND_TOO_LARGE, str(exc)
            return
        except GeneratorError as exc:
            # S1b (2026-10-25 R9 audit / campaign finding): the grid route re-derives and
            # re-checks geometry INSIDE build_grid_mesh (self-approach, symmetry pairing),
            # after the recipe-step wrap in mesh/build.py; those generator errors used to
            # escape as generic Exception rows (kind 'exception', flat 1000, un-memoized -
            # a 2026-10-25 salmon campaign burned 29/40 evals that way). Map them onto
            # KIND_INVALID like the recipe step does so they are deterministic, memoized and
            # never re-run. build_grid_mesh itself keeps raising bare GeneratorError
            # (tests/test_mesh_grid_build.py pins that contract).
            st["kind"], st["err"] = KIND_INVALID, f"generator: {exc}"
            return
        why = envelope_violation(bmesh, getattr(cfg, "brief", None))
        if why:
            # Brief-dependent, NOT a pure function of (design, mesh spec): never failure-cached.
            st["kind"], st["err"], st["no_marker"] = KIND_INVALID, why, True
            return
        mesh_specs.append(bmspec)
        meshes.append(bmesh)

        bkey = solve_cache.key(design.hash(), bmspec.hash(), bsspec.hash())
        resp = solve_cache.lookup(bkey, root) if root is not None else None
        cached = resp is not None
        if resp is None:
            # Only the top band carries the (optional) surface-trace capture: traces are tied to
            # one mesh, and the top band is the one the record's mesh block describes.
            if want_traces and i == len(bands) - 1:
                outcome, raw = backend.solve_traced(bmesh, bsspec)
                st["raw_traces"] = raw
                st["trace_spec"] = bsspec
                st["trace_mesh"] = bmesh
            else:
                outcome = backend.solve(bmesh, bsspec)
            if not outcome.ok or outcome.response is None:
                st["kind"], st["err"] = KIND_SOLVE, outcome.message or "solve failed"
                log.error("band solve failed for %s: %s", design.hash(), st["err"][:2000])
                return
            resp = outcome.response
            solve_seconds += float(outcome.seconds)
            if outcome.peak_vram_mb is not None:
                peak_vram = max(peak_vram or 0.0, float(outcome.peak_vram_mb))
            if root is not None:
                try:
                    solve_cache.store(bkey, root, resp, {"ok": True, "objective": None,
                                                         "n_dof": resp.n_dof, "mode": mode})
                except Exception as exc:  # noqa: BLE001 - cache write failure is not a solve failure
                    log.warning("band solve cache write failed for %s: %s", bkey, exc)
        from_disk.append(cached)
        responses.append(resp)

    merged = stack_responses(responses, sspec.freqs_hz)
    if mode == "verify":
        seam = _seam_check(design.hash(), sspec, mesh_specs, meshes, merged, backend, ctx)
        if seam:
            merged.meta["seam_check"] = seam
    st["resp"] = merged
    st["mesh"] = meshes[-1]
    st["area"], st["grid"] = _grid_info(design_dir / f"band{len(bands) - 1}")
    st["cad"] = _cad_info(design_dir / f"band{len(bands) - 1}")
    st["from_disk"] = all(from_disk)
    st["outcome"] = SolveOutcome(True, merged, solve_seconds, peak_vram,
                                 "cache hit" if st["from_disk"] else "")
    if merged.n_dof is not None:
        st["mesh"].n_dof = int(merged.n_dof)
    try:
        st["metrics"] = metrics_from_response(merged, ctx.target, mesh=st["mesh"], design=design)
    except Exception as exc:  # noqa: BLE001
        st["kind"], st["err"] = KIND_METRICS, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        return
    mismatch = _throat_angle_mismatch_deg(design, getattr(cfg, "brief", None))
    if mismatch is not None:
        st["metrics"].scalars["throat_angle_mismatch_deg"] = mismatch
    _stamp_design_fc_hz(st["metrics"], design)
    st["J"], st["terms"] = _score(st["metrics"], st["resp"], ctx)


def _window_curve(spl_h, h_angles, spl_v, v_angles, window) -> np.ndarray:
    """C11 listening-window power average per frequency (dB), from the two cut planes.

    A window angle that is not on the solved grid is skipped; with no matching angle the
    on-axis sample is used (never a silent mean over the whole cut). Same definition as the
    M4 inner optimiser's local context, so the inner and outer scores agree.
    """
    cols = []
    for angles, spl, wanted in ((h_angles, spl_h, (window or {}).get("h_deg", [])),
                                (v_angles, spl_v, (window or {}).get("v_deg", []))):
        angles = np.asarray(angles, dtype=float)
        idx = []
        for a in wanted or []:
            hit = np.flatnonzero(np.abs(angles - float(a)) <= 1e-9)
            if hit.size:
                idx.append(int(hit[0]))
        if idx:
            cols.append(np.asarray(spl, dtype=float)[:, idx])
    if not cols:
        ax = int(np.argmin(np.abs(np.asarray(h_angles, dtype=float))))
        return np.asarray(spl_h, dtype=float)[:, ax].copy()
    stacked = np.concatenate(cols, axis=1)
    power = np.mean(np.power(10.0, stacked / 10.0), axis=1)
    with np.errstate(divide="ignore"):
        return 10.0 * np.log10(power)


def _meh_ctx(system, solution, block: dict, target: Target) -> dict:
    """The C11 ``meh_ctx`` mapping the v5 objective reads (scalar_meh module docstring)."""
    from ..meh.limits import spl_max

    f = np.asarray(system.freqs_hz, dtype=float)
    window = block.get("listening_window") or MEH_DEFAULT_WINDOW
    lw = _window_curve(system.spl_h_db, system.h_angles_deg,
                       system.spl_v_db, system.v_angles_deg, window)
    smax = np.asarray(getattr(solution, "spl_max_db", ()) or (), dtype=float)
    if smax.shape != f.shape:
        smax = np.asarray(spl_max(f, solution, block), dtype=float)
    return {
        "freqs": f,
        "LW": np.asarray(lw, dtype=float),
        "polars": {
            "h": (np.asarray(system.h_angles_deg, dtype=float),
                  np.asarray(system.spl_h_db, dtype=float)),
            "v": (np.asarray(system.v_angles_deg, dtype=float),
                  np.asarray(system.spl_v_db, dtype=float)),
        },
        "xo_hz": [float(solution.xo_hz)],
        "spl_max_db": smax,
        "spl_target_db": block.get("spl_target"),
        "hp_hz": float(block.get("hp_hz", MEH_DEFAULT_HP_HZ)),
        "max_boost_db": float(block.get("max_boost_db", MEH_DEFAULT_MAX_BOOST_DB)),
        "band_lo_hz": float(target.band_lo_hz),
        "band_hi_hz": float(target.band_hi_hz),
    }


def _meh_layout(design: Design, cad: dict | None,
                mid_ports: dict | None = None) -> tuple[dict, dict]:
    """(``layout_derived`` for M4 inner, full derived dict) from mesh provenance.

    Prefer the MEH CAD ``derived()`` block when present. Else accept OSSE
    ``mid_ports`` (mesher fork): one full port rectangle = across_mm × port_along_mm
    (same as CAD ``port_across * port_along``).

    The inner optimiser needs the printed port area and the L1 recipe. We deliberately do NOT
    hand it the tool's ``v_front_cm3``: the front-chamber volume must stay the fill-dependent
    cone-dish model (C7), so the fixed spacer/wall thickness and the driver file's dish are what
    pass through. ``dish_mm`` comes from the driver object when the file carries it, else M4's
    documented 0.2 x cutout placeholder.
    """
    recipe = dict((cad or {}).get("recipe") or (design.params or {}).get("cad") or {})
    derived = dict((cad or {}).get("derived") or {})
    port_area = derived.get("port_area_mm2")
    if port_area is None:
        ports = derived.get("ports") or []
        if ports and isinstance(ports[0], dict):
            port_area = ports[0].get("area_mm2")
    if port_area is None and mid_ports:
        across = mid_ports.get("across_mm")
        along = mid_ports.get("port_along_mm")
        if across is not None and along is not None:
            port_area = float(across) * float(along)
        else:
            port_area = mid_ports.get("expected_area_mm2")
        # Synthetic recipe for the inner optimiser: mid_ports knobs + shell thickness as neck.
        if not recipe:
            recipe = dict((design.params or {}).get("mid_ports") or {})
            wt = (design.params or {}).get("wall_thickness_mm")
            if wt is not None:
                recipe.setdefault("wall_t_mm", float(wt))
            derived = {
                "port_area_mm2": float(port_area) if port_area is not None else None,
                "source": "osse_mid_ports",
                "mid_ports": dict(mid_ports),
            }
    if port_area is None:
        raise ValueError(
            "MEH mesh provenance carries no port area; need either the meh CAD "
            "derived() block in mesh_meta.json[\"cad\"][\"derived\"] or OSSE "
            "mid_ports areas in mesh_meta.json[\"mid_ports\"]")
    neck_mm = recipe.get("wall_t_mm")
    layout = {
        "derived": {
            "port_area_mm2": float(port_area),
            "l_neck_mm": float(neck_mm) if neck_mm is not None else None,
        },
        "params": recipe,
    }
    return layout, derived


def _compute_meh(design, cfg, mode, mspec, sspec, key, design_dir, backend, ctx, st) -> None:
    """C10 MEH branch: CAD mesh -> multi-source solve -> inner network -> synthesis -> v5.

    ``st["resp"]`` is the BEM Response (the per-channel arrays and Z the record stores);
    ``st["metrics"]`` / ``st["J"]`` are computed on the SYNTHESISED response. The solve cache
    holds the BEM response, so re-scoring a stored record with a different driver stem / hp_hz
    re-runs the CPU inner optimiser and needs no new BEM solve.
    """
    from ..meh.drivers import load_cd, load_cone
    from ..meh.inner import optimise_network
    from ..meh.synthesis import system_response
    from ..objective.scalar_meh import inner_score

    block = meh_block_of(cfg) or {}
    brief = getattr(cfg, "brief", None)

    try:
        mesh = build_mesh(design, mspec, cfg, design_dir, mode=mode, cache_dir=ctx.mesh_cache_root)
    except GeometryInvalidError as exc:
        st["kind"], st["err"] = KIND_INVALID, str(exc)
        return
    except MeshTooLargeError as exc:
        st["kind"], st["err"] = KIND_TOO_LARGE, str(exc)
        return
    except GeneratorError as exc:
        st["kind"], st["err"] = KIND_INVALID, f"generator: {exc}"
        return
    st["mesh"] = mesh
    st["area"], st["grid"] = _grid_info(design_dir)
    cad = _cad_meta(design_dir)
    mid_ports = _mid_ports_meta(design_dir)
    st["cad"] = ({k: cad.get(k) for k in CAD_ECHO_KEYS} if cad else _cad_info(design_dir))
    why = envelope_violation(mesh, brief)
    if why:
        st["kind"], st["err"], st["no_marker"] = KIND_INVALID, why, True
        return

    resp = None
    root = ctx.solve_cache_root
    if root is not None:
        resp = solve_cache.lookup(key, root)
        if resp is not None:
            st["from_disk"] = True
            st["outcome"] = SolveOutcome(True, resp, 0.0, None, "cache hit")
    if resp is None:
        outcome = backend.solve(mesh, sspec)
        st["outcome"] = outcome
        if not outcome.ok or outcome.response is None:
            st["kind"], st["err"] = KIND_SOLVE, outcome.message or "solve failed"
            log.error("MEH solve failed for %s: %s", design.hash(), st["err"][:2000])
            return
        resp = outcome.response
    st["resp"] = resp
    if resp.n_dof is not None:
        mesh.n_dof = int(resp.n_dof)
    if getattr(resp, "channel_pressure", None) is None:
        st["kind"], st["err"] = KIND_SOLVE, (
            "MEH solve returned no channel_pressure/impedance_matrix; the solve spec must carry "
            "extra['source_tags'] and the installed solver must expose the C4 fields")
        return

    # C10 groups -> loaded drivers. The inner optimiser enumerates the CD (exactly one in the
    # M6 validator) and every mid candidate named here.
    groups = block.get("groups") or {}
    try:
        cd_stems = list(groups["cd"]["drivers"])
        mid_stems = list(groups["mid"]["drivers"])
        drivers = {"cd": [load_cd(s) for s in cd_stems],
                   "mid": [load_cone(s) for s in mid_stems]}
    except (KeyError, TypeError) as exc:
        raise ValueError(f"meh.groups is malformed: {exc!r}") from None

    layout, derived = _meh_layout(design, cad, mid_ports=mid_ports)
    params = getattr(ctx, "objective_params", None)
    score = inner_score if params is None else functools.partial(inner_score, params=params)
    solution = optimise_network(resp, layout, brief, drivers, score=score)
    system = system_response(resp, solution)

    # The synthesised balloon is on the BEM theta-phi sphere grid. Carry that fact into the
    # metrics so metrics_from_response applies its sin(theta) quadrature (C4/C11) instead of
    # silently treating a theta-phi grid as equal-area.
    grid_meta = (getattr(resp, "meta", None) or {}).get("balloon_grid")
    if grid_meta is not None and system.spl_balloon_db is not None:
        system.meta["balloon_grid"] = grid_meta

    try:
        st["metrics"] = metrics_from_response(system, ctx.target, mesh=mesh, design=design)
    except Exception as exc:  # noqa: BLE001
        st["kind"], st["err"] = KIND_METRICS, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        return
    mismatch = _throat_angle_mismatch_deg(design, brief)
    if mismatch is not None:
        st["metrics"].scalars["throat_angle_mismatch_deg"] = mismatch

    meh_ctx = _meh_ctx(system, solution, block, ctx.target)
    st["J"], st["terms"] = _score(st["metrics"], system, ctx, meh_ctx=meh_ctx)
    st["network_solution"] = solution.to_dict()
    st["meh_layout"] = {"derived": derived, "recipe": dict((cad or {}).get("recipe") or {})}

    if root is not None and not st["from_disk"]:
        # The cache holds the BEM response (not the synthesised one): re-scoring with a new
        # brief re-runs the CPU inner loop on it without another solve.
        try:
            solve_cache.store(key, root, resp, {"ok": True, "objective": st["J"],
                                                "n_dof": resp.n_dof, "mode": mode})
        except Exception as exc:  # noqa: BLE001
            log.warning("MEH solve cache write failed for %s: %s", key, exc)


def _compute(design, cfg, mode, mspec, sspec, key, design_dir, backend, ctx, st) -> None:
    """Mesh, solve, metrics, objective. Fills ``st``; sets st['kind'] on an expected failure.

    Pre-M3 deterministic markers carry no brief_hash: they re-evaluate once, conservatively, then
    are rewritten under configs that carry a brief (so a later brief change is honoured)."""
    from ..design.generated import GENERATOR_ERROR_KEY
    # WP12: every row/record of a mounting run echoes the normalized block, failures included.
    st["mounting"] = mounting_of(cfg)
    marker = _failure_marker(ctx, key)
    if marker is not None and marker.exists():
        try:
            rec = json.loads(marker.read_text(encoding="utf-8"))
            # a marker is only valid for the library versions that produced it (a mesher fix must
            # not keep replaying an old geometry failure) AND for the brief that produced its
            # verdict (the envelope comes from the brief: a different brief must re-evaluate)
            if rec.get("kind") in DETERMINISTIC_KINDS and rec.get("lib_shas") == ctx.lib_shas \
                    and rec.get("brief_hash") == ctx.provenance.get("brief_hash"):
                st["kind"], st["err"], st["fail_cached"] = rec["kind"], str(rec.get("error", "")), True
                return
        except Exception as exc:  # noqa: BLE001 - a bad marker is ignored, the design re-runs
            log.warning("failure marker %s unreadable: %s", marker, exc)
    if GENERATOR_ERROR_KEY in design.params:            # typology knobs gave no legal horn
        gerr = str(design.params[GENERATOR_ERROR_KEY])
        env_kind = KIND_INVALID_ENV if gerr.startswith("invalid_envelope") else KIND_INVALID
        st["kind"], st["err"] = env_kind, f"generator: {gerr}"
        return
    if meh_block_of(cfg) is not None:
        # C10: the MEH pipeline. Same mesh-context expectations as the single-source path;
        # ``_compute_meh`` owns the solve -> inner network -> synthesis -> v5 objective chain.
        _compute_meh(design, cfg, mode, mspec, sspec, key, design_dir, backend, ctx, st)
        return
    if band_split_of(cfg) is not None:
        _compute_band_split(design, cfg, mode, mspec, sspec, design_dir, backend, ctx, st)
        return
    try:
        mesh = build_mesh(design, mspec, cfg, design_dir, mode=mode, cache_dir=ctx.mesh_cache_root)
    except GeometryInvalidError as exc:
        st["kind"], st["err"] = KIND_INVALID, str(exc)
        return
    except MeshTooLargeError as exc:
        st["kind"], st["err"] = KIND_TOO_LARGE, str(exc)
        return
    except GeneratorError as exc:
        # S1b (2026-10-25): same mapping as the band-split path above - the grid route's
        # in-build_grid_mesh re-checks (self-approach guard, rows/symmetry pairing) raised
        # GeneratorError outside the mesh error-mapping and were landing as kind 'exception'
        # (flat, un-memoized, retried). Deterministic generator errors are invalid_geometry.
        st["kind"], st["err"] = KIND_INVALID, f"generator: {exc}"
        return
    st["mesh"] = mesh
    st["area"], st["grid"] = _grid_info(design_dir)
    st["cad"] = _cad_info(design_dir)
    why = envelope_violation(mesh, getattr(cfg, "brief", None))
    if why:
        # Brief-dependent, NOT a pure function of (design, mesh spec): never failure-cached.
        st["kind"], st["err"], st["no_marker"] = KIND_INVALID, why, True
        return

    resp = None
    root = ctx.solve_cache_root
    if root is not None:
        resp = solve_cache.lookup(key, root)
        if resp is not None:
            st["from_disk"] = True
            st["outcome"] = SolveOutcome(True, resp, 0.0, None, "cache hit")
    if resp is None:
        want_traces = (store_wants_traces(ctx, design) and hasattr(backend, "solve_traced"))
        if want_traces:
            outcome, raw = backend.solve_traced(mesh, sspec)
            st["raw_traces"] = raw
        else:
            outcome = backend.solve(mesh, sspec)
        st["outcome"] = outcome
        if not outcome.ok or outcome.response is None:
            st["kind"], st["err"] = KIND_SOLVE, outcome.message or "solve failed"
            log.error("solve failed for %s: %s", design.hash(), st["err"][:2000])
            return
        resp = outcome.response
    st["resp"] = resp
    if resp.n_dof is not None:
        mesh.n_dof = int(resp.n_dof)
    try:
        st["metrics"] = metrics_from_response(resp, ctx.target, mesh=mesh, design=design)
    except Exception as exc:  # noqa: BLE001
        st["kind"], st["err"] = KIND_METRICS, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        return
    brief = getattr(cfg, "brief", None)
    mismatch = _throat_angle_mismatch_deg(design, brief)
    if mismatch is not None:
        # WP2 report-only scalar (senior pass 2026-10-24): never weighted, never fails a solve.
        st["metrics"].scalars["throat_angle_mismatch_deg"] = mismatch
    _stamp_design_fc_hz(st["metrics"], design)
    st["J"], st["terms"] = _score(st["metrics"], st["resp"], ctx)
    if root is not None and not st["from_disk"]:
        try:
            solve_cache.store(key, root, resp, {"ok": True, "objective": st["J"],
                                                "n_dof": resp.n_dof, "mode": mode})
        except Exception as exc:  # noqa: BLE001 - a cache write failure is not a failed candidate
            log.warning("solve cache write failed for %s: %s", key, exc)


def store_wants_traces(ctx: EvalContext, design: Design) -> bool:
    return ctx.trace_fraction > 0 and should_capture_traces(design.hash(), ctx.trace_fraction)


def _record_provenance(ctx: EvalContext, st: dict) -> dict:
    prov = dict(ctx.provenance)
    gen = st.get("generator")
    if gen:
        prov["generator"] = {k: gen.get(k) for k in ("name", "spec", "knobs", "brief", "brief_hash")}
        prov["brief"] = gen.get("brief") or prov.get("brief")
        prov["brief_hash"] = gen.get("brief_hash") or prov.get("brief_hash")
    if st.get("mesh_policy"):
        prov["mesh_policy"] = st["mesh_policy"]      # WP8: keep band-split data out of old groups
    if st.get("cad"):
        prov["cad"] = st["cad"]                      # WP14: cad-route recipe/tool/step echo
    if st.get("mounting"):
        prov["mounting"] = st["mounting"]            # WP12: normalized brief mounting block
    if st.get("meh_layout"):
        # M7/C12: the CAD recipe + derived layout the inner network optimiser consumed.
        prov["meh"] = {"layout": st["meh_layout"]}
    return prov


def _persist(ev: Evaluation, mode: str, sspec, design_dir: Path, ctx: EvalContext, store, st: dict,
             seconds: dict) -> None:
    """design dir files, boundary traces, DATASET RECORD, then the ndjson row (in that order)."""
    design_dir.mkdir(parents=True, exist_ok=True)
    dj = {"family": ev.design.family, "params": ev.design.params, "design_hash": ev.design_hash}
    if st.get("generator"):
        dj["generator"] = st["generator"]
    _write_json(design_dir / "design.json", dj)
    ok = not ev.error
    _write_json(design_dir / "status.json", {
        "ok": ok, "error": ev.error, "kind": error_kind(ev.error), "objective": ev.objective,
        "mode": mode, "key": f"{ev.design_hash}-{ev.mesh_hash}-{ev.solve_hash}", "cached": ev.cached,
        "seconds": seconds, "terms": ev.terms})
    if ok:
        solve_cache.save_response(design_dir / "response.npz", st["resp"])
        _write_json(design_dir / "metrics.json", metrics_to_json(ev.metrics))

    # ---- boundary traces (1 in N, deterministic) and the dataset record
    trace_info = None
    if store is not None and ok and st["raw_traces"] is not None and not st["from_disk"]:
        try:
            from ..solve.traces import package_traces
            trace_spec = st.get("trace_spec")
            trace_mesh = st.get("trace_mesh")
            packaged = package_traces(trace_mesh if trace_mesh is not None else ev.mesh,
                                      trace_spec if trace_spec is not None else sspec,
                                      st["raw_traces"])
            rel = store.append_traces(ev.design_hash, packaged)
            trace_info = {"path": rel, "kind": TRACE_KIND}
        except Exception as exc:  # noqa: BLE001
            log.warning("trace capture for %s failed: %s", ev.design_hash, exc)
    if store is not None:
        seen = (ev.design_hash, mode, ok)
        if st.get("fail_cached"):
            log.debug("failure of %s replayed from the failure cache; no new dataset record", ev.design_hash)
        elif st["from_disk"] and seen in ctx.store_seen:
            log.debug("dataset already holds %s (%s); not duplicating a cache hit", *seen[:2])
        else:
            try:
                meta, arrays = build_record(
                    ev, ctx.target, ctx.lib_shas, solve_spec=sspec, area_m2=st["area"],
                    grid=st["grid"], traces=trace_info, trace_sample_fraction=ctx.trace_fraction,
                    objective_version=ctx.objective_version,
                    provenance=_record_provenance(ctx, st),
                    network_solution=st.get("network_solution"))
                store.append(meta, arrays)
                ctx.store_seen.add(seen)
            except Exception as exc:  # noqa: BLE001 - ValueError from validate_record, or I/O
                log.error("dataset record for %s was NOT written: %s: %s", ev.design_hash,
                          type(exc).__name__, exc)

    # ---- the ndjson row, last
    row = evaluation_to_row(ev, mode, ctx.n_rows, seconds,
                            objective_version=ctx.objective_version)
    if st.get("mounting"):
        # WP12 provenance echo. The row's ``key`` carries the SAME mounting suffix ``evaluate``
        # used for the run-known memo and the solve cache, so a resume reloads this row under the
        # key the next call looks up. Absent on freestanding rows (old rows byte-identical).
        row["mounting"] = to_jsonable(st["mounting"])
        row["key"] = f"{row['key']}-{families.mounting_key(st['mounting'])}"
    if st.get("mesh_policy"):
        # WP8 provenance echo: absent on single-mesh rows (old rows byte-identical).
        row["mesh_policy"] = st["mesh_policy"]
    if st.get("cad"):
        # WP14 provenance echo: absent on formula/GRID rows (old rows byte-identical).
        row["cad"] = to_jsonable(st["cad"])
    if st.get("generator"):
        row["generator"] = to_jsonable(st["generator"])
    if ctx.write_ndjson:
        append_ndjson(design_dir.parent.parent / "search.ndjson", row)
    ctx.n_rows += 1
    if ok or error_kind(ev.error) in DETERMINISTIC_KINDS:
        ctx.known[row["key"]] = row_to_evaluation(row)
