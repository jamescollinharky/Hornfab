"""Drive hornlab_mesher: Design -> .msh in METRES on disk, with the guards.

We never write a mesher, a gmsh writer or a triangulation. ``hornlab_mesher.build_from_config``
does the geometry and the meshing; this module builds its config, enforces the dof budget,
checks the mesh came back in metres, and caches by hash.

Guards, in the order they can fire:
  * ``families.validate``                          -> GeometryInvalidError   (no mesher call)
  * cache lookup                                   -> hit returns, no mesher call
  * pre-mesh triangle estimate over the dof cap    -> MeshTooLargeError      (no mesh written)
  * mesher ConfigError / ValueError / MesherError  -> GeometryInvalidError   (message verbatim)
  * mesher TriangleBudgetExceeded                  -> MeshTooLargeError
  * mesh bbox extent outside [0.02, 5.0] m         -> MeshUnitsError         (units bug, HARD)
  * mesher's symmetry flag != sizing.SYMMETRY_PLANE-> SymmetryMismatchError  (silent killer #2)
  * source tag 2 (SD1D1001) empty                  -> GeometryInvalidError
  * estimated/vertex dofs over the mode cap        -> MeshTooLargeError      (mesh deleted)
"""
from __future__ import annotations

import copy
import json
import logging
import shutil
import time
from pathlib import Path

import numpy as np

from ..types import (Design, GeometryInvalidError, MeshResult, MeshSpec, MeshTooLargeError)
from . import sizing, topology
from ..design import families

log = logging.getLogger("hornlab_search.mesh.build")

# bbox sanity band for the largest extent of the solved mesh, metres (01_CONTRACTS section 3 /
# 04 step 8). A 1000x error in either direction lands far outside it.
BBOX_MIN_M = 0.02
BBOX_MAX_M = 5.0

SOURCE_TAG = 2          # SD1D1001, hornlab_mesher.tags.PhysicalGroup.PRIMARY_SOURCE
MID_PORT_TAG = 10       # mid_port_exit_left (OSSE mid_ports / MEH entry_mid)

# Pre-mesh estimate: a coarse geometry resolve (cheap, no gmsh) gives the wall areas.
_COARSE_RES_MM = 20.0
# Reject before meshing only when the area-based estimate is this many times over the cap. The
# estimate runs 0.81x to 1.13x of the real count (measured, 4 horns, 3-12 kHz), so 1.5x cannot
# reject a mesh the cap would accept (1.13 * 1.15 slack < 1.5); the exact
# post-mesh check below is the authoritative one.
PREMESH_MARGIN = 1.5
# Effective throat->mouth element size as a fraction of the mouth size, for a throat that is
# half the mouth resolution (calibrated against real builds, see CP-2).
_H_INNER_FRACTION = 0.75


class MeshConsistencyError(RuntimeError):
    """The mesher's output contradicts what we asked for. A bug or a units error, NOT a bad
    candidate: do not swallow it as an invalid design."""


class MeshUnitsError(MeshConsistencyError):
    """Mesh bounding box outside [0.02, 5.0] m: ``scale_to_metres`` / ``mesh_scale`` mismatch."""


class SymmetryMismatchError(MeshConsistencyError):
    """Quadrants and the native symmetry flag disagree."""


# ------------------------------------------------------------------ .msh reader


def read_msh_summary(path: Path, *, return_arrays: bool = False):
    """{'n_triangles', 'n_nodes', 'n_nodes_used', 'bbox_m', 'area_m2', 'tags': {id: count},
        'tag_names': {id: name}, 'format'}

    Parses the gmsh ASCII v2.2 $Nodes and $Elements blocks. Read only. We never write a .msh.
    ``return_arrays=True`` returns ``(summary, xyz, triangles)`` (node coordinates and zero-based
    triangle rows into ``xyz``) for the surface checks in ``mesh/topology.py``.
    ``bbox_m`` is (xmin, ymin, zmin, xmax, ymax, zmax) over the nodes the triangles use.
    """
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = {ln.strip(): i for i, ln in enumerate(lines) if ln.startswith("$")}
    for need in ("$MeshFormat", "$Nodes", "$EndNodes", "$Elements", "$EndElements"):
        if need not in idx:
            raise ValueError(f"{path}: missing {need} (not a gmsh ASCII .msh)")
    fmt = lines[idx["$MeshFormat"] + 1].split()
    if not fmt[0].startswith("2") or fmt[1] != "0":
        raise ValueError(f"{path}: only ASCII MSH 2.x is supported, got {' '.join(fmt)}")

    tag_names: dict[int, str] = {}
    if "$PhysicalNames" in idx:
        i0 = idx["$PhysicalNames"]
        for ln in lines[i0 + 2: i0 + 2 + int(lines[i0 + 1])]:
            dim, tag, name = ln.split(None, 2)
            if int(dim) == 2:
                tag_names[int(tag)] = name.strip().strip('"')

    i0 = idx["$Nodes"]
    n_nodes = int(lines[i0 + 1])
    raw = np.array([ln.split() for ln in lines[i0 + 2: i0 + 2 + n_nodes]], dtype=float)
    node_ids = raw[:, 0].astype(np.int64)
    xyz = raw[:, 1:4]
    row_of = np.full(int(node_ids.max()) + 1, -1, dtype=np.int64)
    row_of[node_ids] = np.arange(n_nodes)

    i0 = idx["$Elements"]
    n_el = int(lines[i0 + 1])
    tris: list[list[int]] = []
    phys: list[int] = []
    for ln in lines[i0 + 2: i0 + 2 + n_el]:
        f = ln.split()
        if int(f[1]) != 2:               # 3-node triangle only; lines/points are ignored
            continue
        nt = int(f[2])
        phys.append(int(f[3]) if nt >= 1 else 0)
        tris.append([int(v) for v in f[3 + nt: 6 + nt]])
    tri = row_of[np.array(tris, dtype=np.int64).reshape(-1, 3)]
    phys_a = np.array(phys, dtype=np.int64)

    p0, p1, p2 = xyz[tri[:, 0]], xyz[tri[:, 1]], xyz[tri[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1).sum()
    used = np.unique(tri)
    pts = xyz[used]
    bbox = tuple(float(v) for v in (*pts.min(axis=0), *pts.max(axis=0)))
    ids, counts = np.unique(phys_a, return_counts=True)
    summary = {
        "n_triangles": int(tri.shape[0]),
        "n_nodes": int(n_nodes),
        "n_nodes_used": int(used.size),
        "bbox_m": bbox,
        "area_m2": float(area),
        "tags": {int(i): int(c) for i, c in zip(ids, counts)},
        "tag_names": tag_names,
        "format": " ".join(fmt),
    }
    return (summary, xyz, tri) if return_arrays else summary


# ------------------------------------------------------------------ pre-mesh estimate


def _quad_grid_area(P: np.ndarray) -> float:
    a, b, c, d = P[:-1, :-1], P[1:, :-1], P[1:, 1:], P[:-1, 1:]
    return float(0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=-1).sum()
                 + 0.5 * np.linalg.norm(np.cross(c - a, d - a), axis=-1).sum())


def estimate_triangles_premesh(mcfg: dict) -> float | None:
    """Solved-domain triangle estimate from wall AREAS, without gmsh.

    A coarse (20 mm) geometry resolve is a few tens of ms and gives the inner/outer wall point
    grids; ``N ~= 2.3 * sum(A / h^2)`` with the mesher's own constant. Returns None when the
    estimate cannot be made (any exception), in which case the mesher's own checks apply.
    """
    try:
        from hornlab_mesher.config_builder import resolve_geometry
        coarse = copy.deepcopy(mcfg)
        coarse["mesh"].update(throat_res_mm=_COARSE_RES_MM, mouth_res_mm=_COARSE_RES_MM,
                              rear_res_mm=_COARSE_RES_MM, allow_large_mesh=True)
        geom = resolve_geometry(coarse).geometry
        a_in = _quad_grid_area(np.asarray(geom.inner_points, dtype=float))
        out = getattr(geom, "outer_points", None)
        a_out = _quad_grid_area(np.asarray(out, dtype=float)) if out is not None else 0.0
    except Exception as exc:          # estimator is advisory; never let it kill a candidate
        log.debug("pre-mesh estimate unavailable: %r", exc)
        return None
    m = mcfg["mesh"]
    h_in = _H_INNER_FRACTION * float(m["mouth_res_mm"])
    h_out = float(m["rear_res_mm"])
    c = sizing.TRIANGLES_PER_AREA_OVER_H2
    return c * (a_in / (h_in * h_in) + a_out / (h_out * h_out))


# ------------------------------------------------------------------ cache


def _meta_path(d: Path) -> Path:
    return d / "mesh_meta.json"


def _result_to_json(r: MeshResult) -> dict:
    return {"path": r.path, "n_triangles": r.n_triangles, "n_dof": r.n_dof,
            "quadrants": r.quadrants, "symmetry_plane": r.symmetry_plane,
            "res_mm": r.res_mm, "bbox_m": list(r.bbox_m), "seconds": r.seconds}


def _result_from_json(d: dict, path: Path, seconds: float) -> MeshResult:
    return MeshResult(path=str(path), n_triangles=int(d["n_triangles"]), n_dof=d.get("n_dof"),
                      quadrants=d["quadrants"], symmetry_plane=d["symmetry_plane"],
                      res_mm=dict(d["res_mm"]), bbox_m=tuple(d["bbox_m"]), seconds=seconds)


def _load_cached(d: Path, key: str) -> dict | None:
    mp, msh = _meta_path(d), d / "mesh.msh"
    if not (mp.is_file() and msh.is_file()):
        return None
    try:
        meta = json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return meta if meta.get("key") == key else None


def _copy_entry(src: Path, dst: Path) -> None:
    """Copy, never symlink: symlinks on Windows need elevation (01_CONTRACTS section 14)."""
    dst.mkdir(parents=True, exist_ok=True)
    if src.resolve() == dst.resolve():
        return
    shutil.copyfile(src / "mesh.msh", dst / "mesh.msh")
    shutil.copyfile(_meta_path(src), _meta_path(dst))


# ------------------------------------------------------------------ guards


def _check_dofs(n_tri: int, n_nodes_used: int, mesh: MeshSpec, cfg, mode: str | None) -> int:
    dpt = float(cfg.mesh.dof_per_triangle)
    cap = sizing.dof_cap_for(mesh, cfg.mesh, mode)
    est = max(sizing.estimate_dofs(n_tri, mesh.quadrants, dpt), int(n_nodes_used))
    if est > cap:
        raise MeshTooLargeError(
            f"{est} dofs ({n_tri} triangles, {n_nodes_used} vertices) exceeds the dof cap {cap}"
            f" for quadrants {mesh.quadrants!r}; lower f_max or epw")
    return est


def _check_bbox(bbox_m: tuple) -> None:
    extent = max(bbox_m[3] - bbox_m[0], bbox_m[4] - bbox_m[1], bbox_m[5] - bbox_m[2])
    if not BBOX_MIN_M <= extent <= BBOX_MAX_M:
        raise MeshUnitsError(
            f"mesh bounding box largest extent {extent:.6g} m is outside "
            f"[{BBOX_MIN_M}, {BBOX_MAX_M}] m; bbox={bbox_m}. This is a UNITS bug "
            "(scale_to_metres / SolveConfig mesh_scale), not a bad candidate. The mesher must "
            "write metres (scale_to_metres=True) and the solve must use mesh_scale=1.0.")


# ------------------------------------------------------------------ build


def rear_res_factor(cfg) -> float:
    """WP7's ``mesh.rear_res_factor``; 1.0 when the caller has no such setting (old configs)."""
    return float(getattr(getattr(cfg, "mesh", None), "rear_res_factor", 1.0))


def mounting_of(cfg) -> dict | None:
    """WP12: the run's normalized ``brief.mounting`` block; ``None`` = freestanding (today).

    Single accessor for the mesh/evaluate routes, so a caller without the attribute (an old
    Config-like object) is freestanding rather than an AttributeError.
    """
    m = getattr(cfg, "mounting", None)
    return m if isinstance(m, dict) else None


def res_mm_for_spec(mesh: MeshSpec, cfg) -> dict:
    """``sizing.res_mm_for`` with the WP7 rear/outer-shell coarsening applied."""
    res = sizing.res_mm_for(mesh.epw, mesh.f_max_hz)
    # rear_res_mm drives the outer shell + rear cap only (MeshDensity read-first 2026-10-24);
    # acoustic bore/mouth/throat cap untouched.
    res["rear"] = res["rear"] * rear_res_factor(cfg)
    return res


def mesh_cache_key(design: Design, mesh: MeshSpec, cfg) -> str:
    """The mesh cache key. Factor 1.0 keeps TODAY'S string exactly; a non-default factor gets a
    suffix so it can never collide with (or invalidate) a factor-1.0 cache entry.

    WP12: a set ``brief.mounting`` adds a stable mounting suffix to the base (MeshSpec.hash does
    not know about the enclosure). Absent mounting -> every existing key is byte-identical.
    """
    base = f"{design.hash()}-{mesh.hash()}"
    factor = rear_res_factor(cfg)
    if factor != 1.0:
        base = f"{base}-rear{factor:g}"
    mkey = families.mounting_key(mounting_of(cfg))
    return f"{base}-{mkey}" if mkey else base


def build_mesh(design: Design, mesh: MeshSpec, cfg, out_dir: Path, *, mode: str | None = None,
               cache_dir: Path | None = None) -> MeshResult:
    """Design + MeshSpec -> ``out_dir/mesh.msh`` (metres) + ``out_dir/mesh_meta.json``.

    ``cfg`` is a ``hornlab_search.config.Config`` (dof caps and dof_per_triangle come from
    ``cfg.mesh``). ``mode`` ("screen"|"verify"|"final") selects the cap; if omitted it is
    inferred from ``mesh.max_triangles`` (see ``sizing.dof_cap_for``). ``cache_dir`` adds a
    shared cache at ``cache_dir/<design hash>-<mesh hash>/``; hits are COPIED into ``out_dir``.

    WP10: a FREEFORM design whose params carry ``"grid"`` takes the point-grid adapter route
    (``mesh/grid_build.py``). Same guards and the SAME ``MeshTooLargeError`` class, so
    ``search/evaluate.py``'s ``mesh_too_large`` mapping applies unchanged. That route has no mesh
    cache yet (grid_build.py documents why) and writes no ``mesh_meta.json``.

    WP14: a FREEFORM design whose params carry ``"cad"`` takes the labelled-STEP route
    (``mesh/step_build.py``): the CAD tool generates the STEP from the recipe, gmsh meshes it,
    the twin mesh is written in metres and ``mesh_meta.json`` carries the ``cad`` provenance
    echo. Same guard classes; no formula-path call.
    """
    import hornlab_mesher as hm
    from hornlab_mesher.config_parser import ConfigError
    from hornlab_mesher.mesher import MesherError, TriangleBudgetExceeded

    t0 = time.perf_counter()
    out_dir = Path(out_dir)
    mounting = mounting_of(cfg)
    families.validate(design)
    if isinstance(design.params, dict) and "grid" in design.params:
        return _build_grid_mesh(design, mesh, cfg, out_dir, mode=mode, mounting=mounting)
    if isinstance(design.params, dict) and "cad" in design.params:
        from . import step_build
        return step_build.build_mesh_from_cad(
            design.params["cad"], mesh, cfg, out_dir, mode=mode, design_hash=design.hash())
    res = res_mm_for_spec(mesh, cfg)
    out_path = out_dir / "mesh.msh"
    mcfg = families.to_mesher_config(design, mesh, res, out_path, mounting=mounting)
    # Copy-pasteable at 2 a.m.: paste into a REPL and call hornlab_mesher.build_from_config.
    log.debug("mesher config for %s: %r", design.hash(), mcfg)

    key = mesh_cache_key(design, mesh, cfg)

    # ---- cache (local, then shared)
    hit = _load_cached(out_dir, key)
    if hit is None and cache_dir is not None:
        shared = Path(cache_dir) / key
        if _load_cached(shared, key) is not None:
            _copy_entry(shared, out_dir)
            hit = _load_cached(out_dir, key)
    if hit is not None:
        _check_dofs(int(hit["result"]["n_triangles"]), int(hit["summary"]["n_nodes_used"]),
                    mesh, cfg, mode)
        # Cached meshes predating the surface checks are checked too (cheap, CPU, no rebuild).
        _, xyz, tri = read_msh_summary(out_path, return_arrays=True)
        topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE[mesh.quadrants])
        log.info("mesh cache hit %s", key)
        return _result_from_json(hit["result"], out_path, time.perf_counter() - t0)

    # ---- cheap pre-mesh guard: no mesh written, no gmsh started
    cap = sizing.dof_cap_for(mesh, cfg.mesh, mode)
    est_tri = estimate_triangles_premesh(mcfg)
    if est_tri is not None:
        est_dof = est_tri * float(cfg.mesh.dof_per_triangle)
        if est_dof > PREMESH_MARGIN * cap:
            raise MeshTooLargeError(
                f"pre-mesh estimate ~{int(est_tri)} triangles (~{int(est_dof)} dofs) is over "
                f"{PREMESH_MARGIN}x the dof cap {cap} at f_max={mesh.f_max_hz:g} Hz, "
                f"epw={mesh.epw:g}, quadrants={mesh.quadrants!r}; no mesh was generated")

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        built = hm.build_from_config(mcfg, out_path)
    except TriangleBudgetExceeded as exc:
        raise MeshTooLargeError(str(exc)) from exc
    except (ConfigError, ValueError, MesherError) as exc:
        raise families.wrap_mesher_error(exc) from exc

    # ---- read back and verify
    summary, xyz, tri = read_msh_summary(out_path, return_arrays=True)
    try:
        _check_bbox(summary["bbox_m"])
        if built.quadrants != mesh.quadrants:
            raise SymmetryMismatchError(
                f"asked for quadrants {mesh.quadrants!r}, mesher built {built.quadrants!r}")
        want = sizing.SYMMETRY_PLANE[mesh.quadrants]
        if built.native_symmetry_plane != want:
            raise SymmetryMismatchError(
                f"quadrants {mesh.quadrants!r} requires native_symmetry_plane={want!r} "
                f"(sizing.SYMMETRY_PLANE) but the mesher reports {built.native_symmetry_plane!r}")
        if built.n_triangles != summary["n_triangles"]:
            raise MeshConsistencyError(
                f"mesher reports {built.n_triangles} triangles, the .msh holds "
                f"{summary['n_triangles']}")
        if summary["tags"].get(SOURCE_TAG, 0) <= 0:
            raise GeometryInvalidError(
                f"mesh has no elements on physical tag {SOURCE_TAG} (SD1D1001, the source); "
                f"tags present: {summary['tags']}")
        if isinstance(design.params, dict) and design.params.get("mid_ports"):
            if summary["tags"].get(MID_PORT_TAG, 0) <= 0:
                raise GeometryInvalidError(
                    f"mid_ports requested but mesh has no elements on tag {MID_PORT_TAG} "
                    f"(mid_port_exit_left); tags present: {summary['tags']}")
        _check_dofs(summary["n_triangles"], summary["n_nodes_used"], mesh, cfg, mode)
        # Closed/manifold surface, no unwelded seams, reduced mesh inside its symmetry domain.
        topology.check_surface(xyz, tri, want)
    except (MeshConsistencyError, GeometryInvalidError, MeshTooLargeError):
        out_path.unlink(missing_ok=True)     # never leave an unusable mesh to be picked up later
        raise

    result = MeshResult(
        path=str(out_path), n_triangles=summary["n_triangles"], n_dof=None,
        quadrants=mesh.quadrants, symmetry_plane=sizing.SYMMETRY_PLANE[mesh.quadrants],
        res_mm=dict(res), bbox_m=tuple(summary["bbox_m"]),
        seconds=time.perf_counter() - t0)
    meta = {"key": key, "result": _result_to_json(result), "summary": summary,
            "mesher_config": mcfg, "rear_res_factor": rear_res_factor(cfg)}
    if mounting is not None:
        # WP12 additive echo (the mesher_config precedent): the normalized search-side block, the
        # mesher keys actually emitted, and the counts from THIS result. Absent on freestanding
        # meshes, so every older mesh_meta.json stays byte-identical.
        meta["mounting"] = {
            "normalized": dict(mounting),
            "mesher": families.enclosure_section(mounting),
            "n_triangles": int(result.n_triangles),
            "n_dof": result.n_dof,
        }
    mid_ports_meta = (getattr(built, "metadata", None) or {}).get("midPorts")
    if mid_ports_meta is not None:
        # Echo mesher midPorts report + tag-10 triangle count into mesh_meta.json.
        meta["mid_ports"] = {
            **dict(mid_ports_meta),
            "tag10_triangles": int(summary["tags"].get(MID_PORT_TAG, 0)),
        }
    _meta_path(out_dir).write_text(json.dumps(meta, indent=1, sort_keys=True), encoding="utf-8")
    if cache_dir is not None:
        _copy_entry(out_dir, Path(cache_dir) / key)
    log.info("mesh %s: %d triangles, %d vertices, %.2f s", key, result.n_triangles,
             summary["n_nodes_used"], result.seconds)
    return result


# ------------------------------------------------------------------ grid (WP10)


def _build_grid_mesh(design: Design, mesh: MeshSpec, cfg, out_dir: Path, *,
                     mode: str | None = None, mounting: dict | None = None) -> MeshResult:
    """Point-grid route: re-derive the grid from the Design's recipe and mesh it.

    ``design.params["grid"]`` carries the compact surface spec plus the flat knobs (the recipe);
    the brief supplies the driver exit and the envelope. ``grid_build.build_grid_mesh`` owns the
    mesher call and the post-mesh guards; this function only reconstructs the grid geometry.

    WP12: ``mounting`` (the normalized brief block) selects the enclosure topology on the same
    point grid: ``grid_build`` then builds NO outer shell and passes ``enclosure`` instead.
    """
    from ..design.generators import grid as grid_mod
    from ..design.generators.registry import GeneratorError
    from . import grid_build

    block = design.params["grid"]
    brief = getattr(cfg, "brief", None)
    if not brief:
        raise ValueError(
            "a grid design needs cfg.brief (driver exit + envelope) to re-derive its geometry; "
            "the config that produced this design was loaded without an embedded brief")
    knobs = block.get("knobs") or {}
    try:
        if "rows" in block:
            # WP9b rows kind: per-azimuth Salmon marches; depth comes from the march, so
            # L_mm is not part of (and is not required by) the recipe.
            spec = {k: v for k, v in block.items() if k != "knobs"}
            inner, meta = grid_mod.rows_grid_points(spec, knobs, brief)
        else:
            spec = {k: block[k] for k in grid_mod.GRID_SPEC_KEYS if k in block}
            inner, meta = grid_mod.grid_points(spec, knobs, brief)
    except GeneratorError as exc:      # recipe + brief no longer agree = an invalid candidate
        raise GeometryInvalidError(str(exc)) from exc
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return grid_build.build_grid_mesh(
        {"inner_points": inner, "meta": meta,
         "wall_thickness_mm": float(block.get("wall_thickness_mm", 3.0))},
        mesh, out_dir / "mesh.msh", cfg, mode=mode, mounting=mounting)


# ------------------------------------------------------------------ STEP


def export_step(design: Design, mesh: MeshSpec, cfg, out: Path):
    """Closed B-rep solid in millimetres (driver membrane removed, symmetry-reduced designs
    expanded to all four quadrants). Returns ``(path, info)``; ``info`` is the mesher's CadInfo
    with ``.body`` and ``.volume_mm3``.

    FORMULA PATH ONLY. The export below rides ``families.to_mesher_config`` -> the mesher's
    ``write_step_from_config``, which renders the OSSE/R-OSSE/ICW/FREEFORM-anchor formulas. A
    GRID design's geometry (point grid + explicit outer shell) and a cad design's solid are
    authored OUTSIDE that formula path, so both are refused here with a clean
    ``GeometryInvalidError`` instead of a ``KeyError`` from the formula dict -- and for a cad
    design the CAD tool (``tools/cad/multicell.py``) IS the STEP exporter:
    ``mesh/step_build.py`` writes the labelled STEP beside every mesh it builds.
    """
    import hornlab_mesher as hm
    from hornlab_mesher.config_parser import ConfigError
    from hornlab_mesher.mesher import MesherError

    families.validate(design)
    if isinstance(design.params, dict) and "grid" in design.params:
        raise GeometryInvalidError(
            "STEP export is not defined for a GRID design: it rides the formula mesher path "
            "(families.to_mesher_config -> write_step_from_config), and a point-grid horn has "
            "no formula geometry to render. Mesh it with build_mesh (mesh/grid_build.py) or "
            "export the point grid through the generator's own CAD path.")
    if isinstance(design.params, dict) and "cad" in design.params:
        raise GeometryInvalidError(
            "STEP export is not defined for a cad design: the CAD tool "
            "(tools/cad/multicell.py) is its STEP exporter, and mesh/step_build.py already "
            "writes the labelled STEP next to the mesh it builds (<out_dir>/cad/*.step). "
            "Call build_mesh; do not re-export through the formula path.")
    res = res_mm_for_spec(mesh, cfg)
    out = Path(out)
    mcfg = families.to_mesher_config(design, mesh, res, out, mounting=mounting_of(cfg))
    log.debug("mesher config for STEP %s: %r", design.hash(), mcfg)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        path, info = hm.write_step_from_config(mcfg, out, open_throat=True, full_model=True)
    except (ConfigError, ValueError, MesherError) as exc:
        raise families.wrap_mesher_error(exc) from exc
    return Path(path), info
