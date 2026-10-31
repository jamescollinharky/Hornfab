"""The frozen training-record schema (01_CONTRACTS.md section 13, schema_version 1).

``build_record`` turns one ``Evaluation`` into (metadata, arrays). ``validate_record`` is the
gatekeeper the store calls before anything touches disk.

Strict JSON, always. Metric arrays and scalars can hold NaN legitimately (ripple with fewer than
five samples, unset design checks). ``to_jsonable`` writes every NaN/Inf as ``null`` so that no
bare ``NaN`` token ever reaches a shard, and ``validate_record`` rejects any non-finite float that
slipped through. A reader may therefore use ``json.loads(..., parse_constant=raise)``.

No numpy types in metadata. ``np.float64`` happens to be a ``float`` subclass and survives
``json.dumps``; ``np.float32``, ``np.int64`` and ``np.bool_`` do not, and the failure would arrive
hours into a search on the one candidate that produced one. Everything is converted at the boundary
and ``validate_record`` walks the result looking for strays.

This module imports only the stdlib, numpy and ``hornlab_search.types``.
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from ..objective.versions import SUPPORTED_OBJECTIVE_VERSIONS, is_supported_objective_version
from ..types import Evaluation, SolveSpec

SCHEMA_VERSION = 1
#: MEH (2026-10-30) adds OPTIONAL record content but does NOT bump the schema version: the
#: additive per-channel arrays below live in ARRAY_KEYS and the matching metadata keys
#: (channel_tags, tag_areas_m2, network_solution) are written only when present, so every
#: older record still validates and loads unchanged (docs/meh/00_MEH_CONTRACTS.md C5/C12).

ARRAY_KEYS = ("freqs_hz", "h_angles_deg", "v_angles_deg",
              "spl_h_db", "spl_v_db", "balloon_dirs", "spl_balloon_db",
              "z_throat", "bw_h_deg", "bw_v_deg", "di_db",
              "ripple_h_db", "ripple_v_db", "on_axis_db",
              # MEH multi-source (C4/C5): complex arrays, absent on single-source records.
              "channel_pressure", "channel_sphere_pressure", "impedance_matrix")

#: Every record carries all five. The four HornLab packages pinned in TOOLCHAIN.md, plus this
#: package's own commit ("unknown" is a legal value when it cannot be determined; absence is not).
REQUIRED_LIB_SHAS = ("hornlab_mesher", "hornlab_beat_bem", "hornlab_bempp_bem",
                     "hornlab_plots", "hornlab_search")

#: 01_CONTRACTS section 13 rule 6: boundary traces on 1 record in 20 by default.
DEFAULT_TRACE_FRACTION = 0.05

#: Cap on the error string stored in a row. The full traceback lives in the run directory.
MAX_ERROR_CHARS = 8000

FAMILIES = ("OSSE", "R-OSSE", "ICW", "FREEFORM")

# Required keys, in schema order. validate_record names the first one missing.
TOP_KEYS = ("schema_version", "design_hash", "mesh_hash", "solve_hash", "family", "params",
            "target", "mesh", "solve", "excitation", "traces", "metrics_scalars", "objective",
            "terms", "ok", "error", "created_utc", "lib_shas")
MESH_KEYS = ("n_triangles", "n_dof", "quadrants", "res_mm", "bbox_m", "area_m2", "seconds", "grid")
GRID_KEYS = ("angular_segments", "length_segments", "available")
SOLVE_KEYS = ("backend", "mode", "freqs_hz", "observation", "gmres_tol", "seconds",
              "peak_vram_mb", "n_dof")
EXCITATION_KEYS = ("port_tag", "port_name", "kind", "amplitude", "units",
                   "frequency_dependent", "notes")
TRACE_KEYS = ("captured", "path", "kind", "sample_fraction")

#: Phase 1 excitation (TOOLCHAIN.md C5): physical tag 2 = SD1D1001, driven as a unit normal
#: velocity basis (velocity_sources={2: 1.0}); not frequency dependent; no way to prescribe a
#: distribution. Written on every row, because it cannot be backfilled.
DEFAULT_EXCITATION = {
    "port_tag": 2,
    "port_name": "SD1D1001",
    "kind": "uniform_normal_velocity",
    "amplitude": 1.0,
    "units": "m/s",
    "frequency_dependent": False,
    "notes": "velocity_sources={2: 1.0}: the solver solves a 1 m/s normal-velocity basis on the "
             "source tag, and hornlab-beat-bem then rescales every stored output to UNIT NORMAL "
             "ACCELERATION (p_accel = p_vel/(-i*omega)); spl_*_db, balloon, traces and z_throat in "
             "this record are in that convention, so absolute levels fall 6 dB per octave versus a "
             "constant-velocity drive (TOOLCHAIN.md C5; senior ruling 2026-10-13)",
}


# ------------------------------------------------------------------ JSON hygiene

def to_jsonable(obj: Any, _path: str = "$") -> Any:
    """Recursively convert to plain JSON types. NaN and +-Inf become None (strict JSON).

    numpy scalars -> int/float/bool, arrays -> nested lists, tuples/sets -> lists,
    dict keys -> str, Path -> str. Anything else raises TypeError naming the path.
    """
    if obj is None or isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        return f if math.isfinite(f) else None
    if isinstance(obj, np.ndarray):
        if obj.dtype == object:
            raise TypeError(f"{_path}: object array cannot be serialised")
        if np.iscomplexobj(obj):
            raise TypeError(f"{_path}: complex array cannot be serialised to metadata")
        return to_jsonable(obj.tolist(), _path)
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v, f"{_path}.{k}") for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        seq = sorted(obj, key=repr) if isinstance(obj, (set, frozenset)) else obj
        return [to_jsonable(v, f"{_path}[{i}]") for i, v in enumerate(seq)]
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"{_path}: cannot serialise {type(obj).__name__} to JSON")


def dumps_strict(obj: Any) -> str:
    """One compact JSON line. allow_nan=False: raises rather than emit a bare NaN token."""
    return json.dumps(obj, allow_nan=False, separators=(",", ":"), ensure_ascii=True)


def _num(x) -> float | None:
    """float() or None. For optional numeric fields; NaN and Inf become None."""
    if x is None:
        return None
    f = float(x)
    return f if math.isfinite(f) else None


def _int(x) -> int | None:
    return None if x is None else int(x)


def record_objective_version(meta: dict) -> int:
    """The objective version a record was scored with. Records written before the field existed
    (schema_version 1, pre-M3) are version 1: absence is not an error and the stored data is never
    rewritten."""
    return int(meta.get("objective_version", 1))


# ------------------------------------------------------------------ sampling

def should_capture_traces(design_hash: str, fraction: float = DEFAULT_TRACE_FRACTION) -> bool:
    """Deterministic, reproducible 1-in-N sampling keyed on the design hash.

    The hash is 12 hex characters of a SHA-256, so it is uniform. Deterministic, so a re-run of
    the same search captures traces for the same designs.
    """
    if fraction <= 0.0:
        return False
    if fraction >= 1.0:
        return True
    return int(design_hash, 16) / float(16 ** len(design_hash)) < fraction


def lib_sha_key(lib_shas: dict) -> str:
    """The label-provenance key stored in the index: mesher + solver, 10 chars each.

    Labels depend on the geometry (mesher) and the field solve (beat). This package's own commit
    changes on every edit and would fragment a dataset whose labels did not change, so it is
    excluded from the key (it is still in every record's lib_shas).
    """
    return f"{str(lib_shas.get('hornlab_mesher', ''))[:10]}+{str(lib_shas.get('hornlab_beat_bem', ''))[:10]}"


# ------------------------------------------------------------------ build

def _target_dict(target) -> dict:
    if dataclasses.is_dataclass(target) and not isinstance(target, type):
        d = dataclasses.asdict(target)
    elif isinstance(target, dict):
        d = dict(target)
    else:
        raise TypeError(f"target must be a dataclass or dict, got {type(target).__name__}")
    # 2026-10-26 objective v3 amendment: f0_v_hz is OPTIONAL and emitted only when set, so a
    # record written without it stays byte-identical to the pre-amendment record.
    if d.get("f0_v_hz", "absent") is None:
        d.pop("f0_v_hz", None)
    return to_jsonable(d, "$.target")


def _solve_block(ev: Evaluation, solve_spec: SolveSpec | None, resp) -> dict:
    out = ev.outcome
    if solve_spec is not None:
        obs = dataclasses.asdict(solve_spec.observation)
        backend, mode = solve_spec.backend, solve_spec.mode
        freqs = list(solve_spec.freqs_hz)
        gmres_tol = solve_spec.gmres_tol
    else:
        # Fallback: only what the Response itself can say. The pipeline should pass solve_spec.
        obs = {"distance_m": None, "angle_count": None, "balloon": None, "balloon_points": None}
        backend = getattr(resp, "backend", "") or ""
        mode = None
        freqs = [] if resp is None else np.asarray(resp.freqs_hz, dtype=float).tolist()
        gmres_tol = None
        if resp is not None:
            obs["angle_count"] = int(np.asarray(resp.h_angles_deg).size)
            obs["balloon"] = resp.spl_balloon_db is not None
            obs["balloon_points"] = (0 if resp.spl_balloon_db is None
                                     else int(np.asarray(resp.spl_balloon_db).shape[-1]))
    n_dof = ev.mesh.n_dof if (ev.mesh is not None and ev.mesh.n_dof is not None) \
        else (None if resp is None else resp.n_dof)
    return to_jsonable({
        "backend": backend,
        "mode": mode,
        "freqs_hz": freqs,
        "observation": obs,
        "gmres_tol": gmres_tol,
        "seconds": None if out is None else out.seconds,
        "peak_vram_mb": None if out is None else out.peak_vram_mb,
        "n_dof": n_dof,
    }, "$.solve")


def _mesh_block(ev: Evaluation, area_m2, grid) -> dict:
    g = {"angular_segments": None, "length_segments": None, "available": False}
    if grid is not None:
        missing = [k for k in GRID_KEYS if k not in grid]
        if missing:
            raise ValueError(f"build_record: grid is missing {missing}")
        g = {k: grid[k] for k in GRID_KEYS}
    m = ev.mesh
    if m is None:
        block = {"n_triangles": None, "n_dof": None, "quadrants": None,
                 "res_mm": {"throat": None, "mouth": None, "rear": None},
                 "bbox_m": None, "area_m2": area_m2, "seconds": None, "grid": g}
    else:
        res = dict(m.res_mm)
        block = {"n_triangles": m.n_triangles, "n_dof": m.n_dof, "quadrants": m.quadrants,
                 "res_mm": {"throat": res.get("throat"), "mouth": res.get("mouth"),
                            "rear": res.get("rear")},
                 "bbox_m": list(m.bbox_m), "area_m2": area_m2, "seconds": m.seconds, "grid": g}
    return to_jsonable(block, "$.mesh")


def _arrays_for(ev: Evaluation) -> dict:
    """Arrays of a successful evaluation. A failure has none."""
    resp = None if ev.outcome is None else ev.outcome.response
    met = ev.metrics
    arrays: dict[str, np.ndarray] = {}
    if resp is not None:
        src = {"freqs_hz": resp.freqs_hz, "h_angles_deg": resp.h_angles_deg,
               "v_angles_deg": resp.v_angles_deg, "spl_h_db": resp.spl_h_db,
               "spl_v_db": resp.spl_v_db, "balloon_dirs": resp.balloon_dirs,
               "spl_balloon_db": resp.spl_balloon_db, "z_throat": resp.z_throat,
               # MEH (C5): None on a single-source response -> absent from the record.
               "channel_pressure": getattr(resp, "channel_pressure", None),
               "channel_sphere_pressure": getattr(resp, "channel_sphere_pressure", None),
               "impedance_matrix": getattr(resp, "impedance_matrix", None)}
        arrays.update({k: v for k, v in src.items() if v is not None})
    if met is not None:
        src = {"bw_h_deg": met.bw_h_deg, "bw_v_deg": met.bw_v_deg, "di_db": met.di_db,
               "ripple_h_db": met.ripple_h_db, "ripple_v_db": met.ripple_v_db,
               "on_axis_db": met.on_axis_db}
        arrays.update({k: v for k, v in src.items() if v is not None})
        if "freqs_hz" not in arrays and met.freqs_hz is not None:
            arrays["freqs_hz"] = met.freqs_hz
    out = {}
    for k in ARRAY_KEYS:
        if k in arrays:
            a = np.array(arrays[k])          # copy: the record must not alias live solver memory
            if a.dtype == object:
                raise TypeError(f"build_record: array '{k}' has dtype object")
            out[k] = a
    return out


def build_record(ev: Evaluation, target, lib_shas: dict, *,
                 solve_spec: SolveSpec | None = None,
                 area_m2: float | None = None,
                 grid: dict | None = None,
                 traces: dict | None = None,
                 trace_sample_fraction: float = DEFAULT_TRACE_FRACTION,
                 excitation: dict | None = None,
                 created_utc: str | None = None,
                 objective_version: int = 1,
                 provenance: dict | None = None,
                 network_solution: dict | None = None) -> tuple[dict, dict]:
    """Returns (metadata_dict, arrays_dict).

    metadata is JSON-serializable with NO numpy types anywhere and no NaN/Inf (those become null).
    arrays maps a key from ARRAY_KEYS to an ndarray, omitting absent ones.

    Records FAILURES too: ok=False, error set, arrays empty. A surrogate needs to learn where the
    invalid region is, and a search needs to know how much of its budget went to failures.

    The required arguments are the task's signature. The keyword-only ones carry facts that are not
    on an Evaluation and that the pipeline already holds:

      solve_spec   the SolveSpec used (mode, observation, gmres_tol, the requested frequencies).
                   Without it those fields are None and only the Response's own values are used.
      area_m2      mesh surface area; None when the mesher result did not report it.
      grid         {"angular_segments", "length_segments", "available"}: the mesher's structured
                   surface sampling, and whether the grid itself was reachable (TOOLCHAIN.md C4).
                   Always written; segment counts are None when the caller does not know them.
      traces       {"path": ..., "kind": ...} from DatasetStore.append_traces, or None.
      trace_sample_fraction  the configured sampling fraction, recorded on every row so a later
                   reader can tell "not sampled" from "capture failed".
      excitation   overrides DEFAULT_EXCITATION (phase 1 never needs to).
       created_utc  ISO-8601 "YYYY-MM-DDTHH:MM:SSZ"; now if omitted.
       objective_version  the objective dispatch version the evaluation was scored with,
                    one of ``objective.versions.SUPPORTED_OBJECTIVE_VERSIONS`` (the same tuple
                    ``search/evaluate.py`` dispatches on). Always written; older records lack it
                    and read as version 1 (``record_objective_version``).
       network_solution  optional, additive (MEH, C12): the JSON form of the chosen
                    ``NetworkSolution`` (M7/objective v5 fills it). Older records lack it.
       provenance   optional, additive (plan R8): {"config", "brief", "brief_hash", "generator"} -
                   which config / design brief scored this record and which typology generator (if
                   any) produced the design. Older records lack it; readers must treat it as optional.
                   The metric curves are target-free; only ``objective``/``terms`` depend on the brief.
    """
    out = ev.outcome
    resp = None if out is None else out.response
    ok = bool(out is not None and out.ok and ev.metrics is not None and not ev.error)

    error = ev.error or ""
    if not ok and not error:
        if out is not None and out.message:
            error = out.message
        elif out is None:
            error = "no solve outcome"
        elif ev.metrics is None:
            error = "no metrics computed"
        else:
            error = "solve failed"
    if ok:
        error = ""
    error = error[:MAX_ERROR_CHARS]

    exc = dict(DEFAULT_EXCITATION)
    if excitation:
        exc.update(excitation)

    if traces:
        trace_block = {"captured": True, "path": str(traces["path"]),
                       "kind": traces.get("kind"), "sample_fraction": trace_sample_fraction}
    else:
        trace_block = {"captured": False, "path": None, "kind": None,
                       "sample_fraction": trace_sample_fraction}

    scalars = {} if (ev.metrics is None or not ok) else ev.metrics.scalars

    meta = {
        "schema_version": SCHEMA_VERSION,
        "design_hash": str(ev.design_hash),
        "mesh_hash": str(ev.mesh_hash),
        "solve_hash": str(ev.solve_hash),
        "family": str(ev.design.family),
        "params": to_jsonable(ev.design.params, "$.params"),
        "target": _target_dict(target),
        "mesh": _mesh_block(ev, _num(area_m2), grid),
        "solve": _solve_block(ev, solve_spec, resp),
        "excitation": to_jsonable(exc, "$.excitation"),
        "traces": to_jsonable(trace_block, "$.traces"),
        "metrics_scalars": to_jsonable(scalars, "$.metrics_scalars"),
        "objective": _num(ev.objective),
        "terms": to_jsonable(ev.terms, "$.terms"),
        "objective_version": int(objective_version),
        "ok": ok,
        "error": error,
        "created_utc": created_utc or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lib_shas": {str(k): str(v) for k, v in lib_shas.items()},
    }
    if provenance:
        meta["provenance"] = to_jsonable(provenance, "$.provenance")
    # MEH (C5/C12): additive, written only when present, so a single-source record is unchanged.
    if resp is not None:
        channel_tags = getattr(resp, "channel_tags", None)
        if channel_tags is not None:
            meta["channel_tags"] = [int(t) for t in channel_tags]
        tag_areas = getattr(resp, "tag_areas_m2", None)
        if tag_areas is not None:
            meta["tag_areas_m2"] = to_jsonable(
                {str(int(k)): float(v) for k, v in tag_areas.items()}, "$.tag_areas_m2")
    if network_solution is not None:
        meta["network_solution"] = to_jsonable(network_solution, "$.network_solution")
    arrays = _arrays_for(ev) if ok else {}
    return meta, arrays


# ------------------------------------------------------------------ validate

def _is_numpy(x) -> bool:
    return isinstance(x, (np.generic, np.ndarray))


def _walk(x, path: str) -> None:
    """Raise ValueError at the first leaf that is not a strict-JSON plain type."""
    if _is_numpy(x):
        raise ValueError(f"numpy type {type(x).__name__} at {path}")
    if x is None or isinstance(x, (str, bool, int)):
        return
    if isinstance(x, float):
        if not math.isfinite(x):
            raise ValueError(f"non-finite float at {path} (must be null in strict JSON)")
        return
    if isinstance(x, dict):
        for k, v in x.items():
            if not isinstance(k, str):
                raise ValueError(f"non-string key {k!r} at {path}")
            _walk(v, f"{path}.{k}")
        return
    if isinstance(x, list):
        for i, v in enumerate(x):
            _walk(v, f"{path}[{i}]")
        return
    raise ValueError(f"unsupported type {type(x).__name__} at {path}")


def _need(d, keys, where: str) -> None:
    if not isinstance(d, dict):
        raise ValueError(f"{where} must be an object, got {type(d).__name__}")
    for k in keys:
        if k not in d:
            raise ValueError(f"missing required key '{k}'" + ("" if where == "record" else f" in {where}"))


def validate_record(meta: dict) -> None:
    """Raise ValueError naming the first problem. Checks every required key, that schema_version
    matches, that lib_shas has all required entries, that no value is a numpy type, that no float
    is non-finite, and that the thing round-trips through strict json unchanged."""
    _need(meta, TOP_KEYS, "record")
    if meta["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version is {meta['schema_version']!r}, expected {SCHEMA_VERSION}")
    _need(meta["mesh"], MESH_KEYS, "mesh")
    _need(meta["mesh"]["grid"], GRID_KEYS, "mesh.grid")
    _need(meta["solve"], SOLVE_KEYS, "solve")
    _need(meta["excitation"], EXCITATION_KEYS, "excitation")
    _need(meta["traces"], TRACE_KEYS, "traces")
    _need(meta["lib_shas"], REQUIRED_LIB_SHAS, "lib_shas")
    for k in REQUIRED_LIB_SHAS:
        v = meta["lib_shas"][k]
        if not isinstance(v, str) or not v:
            raise ValueError(f"lib_shas['{k}'] must be a non-empty string, got {v!r}")

    _walk(meta, "$")

    for k in ("design_hash", "mesh_hash", "solve_hash", "created_utc"):
        if not isinstance(meta[k], str) or not meta[k]:
            raise ValueError(f"'{k}' must be a non-empty string, got {meta[k]!r}")
    if meta["family"] not in FAMILIES:
        raise ValueError(f"family {meta['family']!r} is not one of {FAMILIES}")
    if "objective_version" in meta:                 # absence means v1 (records written before M3)
        ov = meta["objective_version"]
        # One source of truth: the versions the scorer can dispatch (search/evaluate.py).
        # v3 shipped 2026-10-26 (per-plane f0_v + the K-law f0 mask); v4 (term normalisation)
        # must be added there, not hard-coded here.
        if not is_supported_objective_version(ov):
            supported = ", ".join(str(v) for v in SUPPORTED_OBJECTIVE_VERSIONS)
            raise ValueError(f"'objective_version' must be one of ({supported}), got {ov!r}")
    if not isinstance(meta["ok"], bool):
        raise ValueError("'ok' must be a bool")
    if not isinstance(meta["error"], str):
        raise ValueError("'error' must be a string")
    if meta["ok"] and meta["error"]:
        raise ValueError("ok is true but error is set")
    if not meta["ok"] and not meta["error"]:
        raise ValueError("ok is false but error is empty: a failure must say why")
    if not isinstance(meta["params"], dict):
        raise ValueError("'params' must be an object")
    if meta["traces"]["captured"] is True and not isinstance(meta["traces"]["path"], str):
        raise ValueError("traces.captured is true but traces.path is not a string")
    if not isinstance(meta["mesh"]["grid"]["available"], bool):
        raise ValueError("mesh.grid.available must be a bool")

    try:
        text = dumps_strict(meta)
    except (TypeError, ValueError) as e:
        raise ValueError(f"record does not serialise as strict JSON: {e}") from e
    if json.loads(text) != meta:
        raise ValueError("record does not round-trip through JSON unchanged")
