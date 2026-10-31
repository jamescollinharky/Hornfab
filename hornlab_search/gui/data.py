"""Read-only views of run folders, campaigns, briefs and machine state for the local GUI.

Nothing here solves, meshes or writes: every number comes from files the CLI already wrote
(``search.ndjson``, ``config.yaml``, ``designs/<hash>/{metrics.json,response.npz,mesh.msh}``,
``campaign.json``, ``leaderboard.md``). Values are JSON-safe (NaN/Inf -> None).
"""
from __future__ import annotations

import copy
import json
import math
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z]+-[0-9a-f]{6}$")
CAMPAIGN_ID = re.compile(r"^campaign_[0-9]{8}T[0-9]{6}Z$")
HASH = re.compile(r"^[0-9a-f]{6,40}$")
STEP_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,80}_rank\d+_[0-9a-f]{6,40}\.step$")
#: Design hash at the end of an exported STEP (``<config name>_rankN_<hash>.step`` for a run,
#: ``<config name>_seed_<hash>.step`` for a config). The suffix is the loader's own 12-hex hash
#: (``types._hash``), so the trailing group is unambiguous.
STEP_HASH = re.compile(r"_([0-9a-f]{6,40})\.step$")
BRIEF_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
#: pycma's own verbose-log files (``cma/*`` and ``cma/restart_k/*``), served raw/download-only.
#: Extensions are the ones pycma writes; anything executable or unknown is refused by the route.
CMA_LOG_NAME = re.compile(r"^(?!.*\.\.)[A-Za-z0-9_][A-Za-z0-9_.\-]{0,79}\.(?:txt|dat|json2|q)$")
CMA_RESTART_DIR = re.compile(r"^restart_[0-9]+$")
TOP_K = 6                       # "pinned" = most of the TOP_K best designs within 2 % of a bound
PIN_FRAC = 0.02


# ---------------------------------------------------------------------------- helpers


def clean(x: Any) -> Any:
    """Recursively make a value JSON-safe: numpy -> python, NaN/Inf -> None."""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, (np.floating, float)):
        f = float(x)
        return f if math.isfinite(f) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def _rnd(a, n=3):
    arr = np.asarray(a, dtype=float)
    return [None if not math.isfinite(v) else round(v, n) for v in arr.ravel().tolist()]


def _read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _as_dict(v: Any) -> dict:
    """A mapping or an empty one (read-only readers must tolerate a wrong type, never crash)."""
    return v if isinstance(v, dict) else {}


def read_ndjson(p: Path) -> list[dict]:
    rows = []
    try:
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:      # a row being written right now
                        pass
    except OSError:
        pass
    return rows


def tail_text(p: Path, n: int = 40) -> list[str]:
    """Last n lines of a log; handles the UTF-16 files PowerShell's Tee-Object writes."""
    try:
        raw = p.read_bytes()
    except OSError:
        return []
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or raw[1:2] == b"\x00":
        txt = raw.decode("utf-16", errors="replace")
    else:
        txt = raw.decode("utf-8", errors="replace")
    return [ln.rstrip("\r") for ln in txt.lstrip("﻿").splitlines()][-n:]


def _flat(d: Any, prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flat(v, f"{prefix}{k}."))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.update(_flat(v, f"{prefix}{i}."))
    elif isinstance(d, (int, float)) and not isinstance(d, bool):
        out[prefix[:-1]] = float(d)
    return out


def _err_kind(row: dict) -> str | None:
    e = row.get("error")
    return None if not e else str(e).split(":", 1)[0]


def _spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 5 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    c = np.corrcoef(rx, ry)[0, 1]
    return float(c) if math.isfinite(c) else None


# ---------------------------------------------------------------------------- runs


def _run_dirs(runs: Path) -> list[Path]:
    if not runs.is_dir():
        return []
    return sorted((p for p in runs.iterdir() if p.is_dir() and RUN_ID.match(p.name)),
                  key=lambda p: p.name, reverse=True)


def _config(run_dir: Path) -> dict:
    try:
        return yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def horn_dims(row: dict | None) -> dict | None:
    """Outer size of a solved design in mm (mouth width x height, depth), shell included, from the mesh
    bounding box the search recorded. The meshed domain is a quarter for quadrants '1' (x >= 0, y >= 0),
    so the full mouth is twice the extent there."""
    if not row or not row.get("bbox_m"):
        return None
    x0, y0, z0, x1, y1, z1 = (float(v) for v in row["bbox_m"])
    q = str(row.get("quadrants") or "1234")
    w = 2 * x1 if q in ("1", "14") else x1 - x0
    h = 2 * y1 if q in ("1", "12") else y1 - y0
    return {"mouth_w_mm": round(w * 1000, 1), "mouth_h_mm": round(h * 1000, 1),
            "depth_mm": round((z1 - z0) * 1000, 1), "includes_shell": True}


_FLAG = re.compile(r"--(budget|max-evals|cma-seed)\s+(\d+)")


def _command_flags(run_dir: Path) -> dict:
    cmd = (_read_json(run_dir / "run.json") or {}).get("command") or ""
    return {k.replace("-", "_"): int(v) for k, v in _FLAG.findall(cmd)} | {"command": cmd}


def _ts(s: str | None):
    import datetime as dt
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def run_summary(run_dir: Path) -> dict:
    """Memoized on the run's search.ndjson stamp: list_runs and the auto campaigns both summarize
    every run on each refresh, and a finished run's summary never changes."""
    try:
        st = (run_dir / "search.ndjson").stat()
        stamp = (st.st_mtime_ns, st.st_size)
    except OSError:
        stamp = None
    key = str(run_dir.resolve())
    hit = _RUN_SUMMARY_CACHE.get(key)
    if stamp is not None and hit is not None and hit[0] == stamp:
        return hit[1]
    out = _run_summary(run_dir)
    if stamp is not None:
        _RUN_SUMMARY_CACHE[key] = (stamp, out)
    return out


#: ``resolved run dir -> ((ndjson mtime_ns, size), run_summary dict)``.
_RUN_SUMMARY_CACHE: dict[str, tuple] = {}


def _run_summary(run_dir: Path) -> dict:
    rows = read_ndjson(run_dir / "search.ndjson")
    cfg = _config(run_dir)
    ok = [r for r in rows if r.get("ok")]
    best = min(ok, key=lambda r: r["objective"]) if ok else None
    brief = cfg.get("brief") if isinstance(cfg.get("brief"), dict) else None
    return clean({
        "id": run_dir.name,
        "name": cfg.get("name"),
        "family": cfg.get("family") or (rows[0].get("family") if rows else None),
        "generator": (cfg.get("generator") or {}).get("name") if isinstance(cfg.get("generator"), dict) else None,
        "brief": brief.get("name") if brief else None,
        "mode": rows[0].get("mode") if rows else None,
        "n": len(rows),
        "n_ok": len(ok),
        "n_cached": sum(1 for r in rows if r.get("cached")),
        "failures": dict(Counter(k for k in map(_err_kind, rows) if k)),
        "seed_j": rows[0].get("objective") if rows else None,
        "best_j": best["objective"] if best else None,
        "best_hash": best["design_hash"] if best else None,
        "started": rows[0].get("created_utc") if rows else None,
        "last": rows[-1].get("created_utc") if rows else None,
        "has_report": (run_dir / "report.html").exists(),
        "dims": horn_dims(best),
        "budget": _command_flags(run_dir).get("max_evals") or _command_flags(run_dir).get("budget"),
        "cma_seed": _command_flags(run_dir).get("cma_seed"),
    })


def list_runs(runs: Path, limit: int | None = None) -> list[dict]:
    """Every run under ``runs`` (no cap: anything a search wrote must show up)."""
    dirs = _run_dirs(runs)
    return [run_summary(d) for d in (dirs if limit is None else dirs[:limit])]


def _resolve_run(runs: Path, run_id: str) -> Path:
    if not RUN_ID.match(run_id):
        raise ValueError(f"not a run id: {run_id!r}")
    d = runs / run_id
    if not (d / "search.ndjson").exists():
        raise FileNotFoundError(run_id)
    return d


def _norm_polar(spl: np.ndarray) -> np.ndarray:
    c = spl.shape[1] // 2
    return np.maximum(spl - spl[:, c:c + 1], -40.0)


def mesh_nodes_tris(msh: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Nodes (m) and triangles (0-based) from a gmsh 2.2 ASCII file, as the mesher writes it."""
    try:
        txt = msh.read_text(errors="ignore")
    except OSError:
        return None
    mn = re.search(r"\$Nodes\s*\n(\d+)\n(.*?)\$EndNodes", txt, re.S)
    me = re.search(r"\$Elements\s*\n(\d+)\n(.*?)\$EndElements", txt, re.S)
    if not mn:
        return None
    ids, pts = [], []
    for ln in mn.group(2).strip().splitlines():
        a = ln.split()
        ids.append(int(a[0]))
        pts.append([float(a[1]), float(a[2]), float(a[3])])
    index = {nid: i for i, nid in enumerate(ids)}
    tris = []
    if me:
        for ln in me.group(2).strip().splitlines():
            a = ln.split()
            if len(a) > 3 and a[1] == "2":                     # 3-node triangle
                ntags = int(a[2])
                tris.append([index[int(v)] for v in a[3 + ntags:6 + ntags]])
    return np.asarray(pts, float), np.asarray(tris, int).reshape(-1, 3)


def _plane_chains(pts: np.ndarray, tris: np.ndarray, ax: int, tol: float = 1e-6) -> list[list[int]]:
    """Ordered node chains along the symmetry plane where coordinate (1 - ax) == 0 and coordinate ax >= 0.
    In a quarter-model mesh the symmetry planes are open boundaries, so the mesh edges lying in a plane
    form the horn's cross-section outline (throat cap, acoustic wall, mouth lip, outer shell, rear)."""
    on = (np.abs(pts[:, 1 - ax]) < tol) & (pts[:, ax] >= -tol)
    adj: dict[int, set[int]] = {}
    for t in tris:
        for i, j in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if on[i] and on[j]:
                adj.setdefault(int(i), set()).add(int(j))
                adj.setdefault(int(j), set()).add(int(i))
    chains, seen = [], set()
    starts = [n for n, nb in adj.items() if len(nb) == 1] + list(adj)
    for s0 in starts:
        if s0 in seen:
            continue
        chain, prev, cur = [s0], None, s0
        seen.add(s0)
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            chain.append(cur)
        if len(chain) > 2:
            chains.append(chain)
    return chains


def _profile_from_mesh(msh: Path) -> dict:
    """Wall cross-section in the H (x-z) and V (y-z) planes, in mm as [z, r] points.
    kind 'section': ordered outline from the plane's boundary edges (quarter meshes);
    kind 'nodes': unordered plane nodes (full meshes, where the planes are not mesh boundaries)."""
    nt = mesh_nodes_tris(msh)
    if nt is None:
        return {}
    pts, tris = nt
    prof: dict = {}
    for key, ax in (("h", 0), ("v", 1)):
        chains = _plane_chains(pts, tris, ax) if len(tris) else []
        if chains:
            chain = max(chains, key=len)
            prof[key] = [[round(float(pts[i, 2]) * 1000, 2), round(float(pts[i, ax]) * 1000, 2)] for i in chain]
            prof["kind"] = "section"
        else:
            sel = pts[np.abs(pts[:, 1 - ax]) < 1e-4]
            sel = sel[np.argsort(sel[:, 2])]
            prof[key] = [[round(float(z) * 1000, 2), round(float(a) * 1000, 2)] for a, z in zip(sel[:, ax], sel[:, 2])]
            prof.setdefault("kind", "nodes")
    return prof


def design_curves(run_dir: Path, h: str) -> dict | None:
    """Per-frequency metrics, normalised polar maps and the wall profile of one solved design."""
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    d = run_dir / "designs" / h
    m = _read_json(d / "metrics.json")
    if m is None:
        return None
    out = {
        "hash": h,
        "freqs": _rnd(m["freqs_hz"], 1),
        "bw_h": _rnd(m["bw_h_deg"], 2), "bw_v": _rnd(m["bw_v_deg"], 2),
        "di": _rnd(m["di_db"], 3), "di_source": m.get("di_source"),
        "on_axis": _rnd(np.asarray(m["on_axis_db"], float) - np.nanmean(m["on_axis_db"]), 3),
        "rip_h": _rnd(m["ripple_h_db"], 3), "rip_v": _rnd(m["ripple_v_db"], 3),
        "z_re": _rnd(m["z_throat_real"], 3) if m.get("z_throat_real") is not None else None,
        "scalars": m.get("scalars") or {},
    }
    try:
        with np.load(d / "response.npz", allow_pickle=False) as z:
            out["angles"] = _rnd(z["h_angles_deg"], 1)
            out["polar_h"] = [_rnd(r, 2) for r in _norm_polar(np.asarray(z["spl_h_db"], float))]
            out["polar_v"] = [_rnd(r, 2) for r in _norm_polar(np.asarray(z["spl_v_db"], float))]
            if "z_throat" in z.files:
                zt = np.asarray(z["z_throat"], dtype=complex)
                out["z_re"], out["z_im"] = _rnd(zt.real, 3), _rnd(zt.imag, 3)   # exp(-i w t): mass-like < 0
    except (OSError, KeyError, ValueError):
        pass
    out["profile"] = _profile_from_mesh(d / "mesh.msh")
    dj = _read_json(d / "design.json") or {}
    out["params"] = dj.get("params")
    out["generator"] = dj.get("generator")
    return clean(out)


def _knob_values(row: dict) -> dict[str, float]:
    gen = row.get("generator")
    if isinstance(gen, dict) and isinstance(gen.get("knobs"), dict):
        return {k: float(v) for k, v in gen["knobs"].items() if isinstance(v, (int, float))}
    return _flat(row.get("params") or {})


def sensitivity(rows: list[dict], bounds: dict) -> list[dict]:
    """Spearman rho of each searched knob with J over successful rows, and bound pinning of the best K."""
    ok = [r for r in rows if r.get("ok") and r.get("objective") is not None]
    if not ok or not isinstance(bounds, dict):
        return []
    vals = [_knob_values(r) for r in ok]
    J = np.array([r["objective"] for r in ok], float)
    top = np.argsort(J)[:TOP_K]
    out = []
    for key, b in bounds.items():
        if not isinstance(b, dict) or "lo" not in b or "hi" not in b or b.get("search") is False:
            continue
        x = np.array([v.get(key, np.nan) for v in vals], float)
        fin = np.isfinite(x)
        if fin.sum() < 2:
            continue
        lo, hi = float(b["lo"]), float(b["hi"])
        tol = PIN_FRAC * (hi - lo)
        xt = x[top][np.isfinite(x[top])]
        out.append({"key": key, "lo": lo, "hi": hi,
                    "rho": _spearman(x[fin], J[fin]),
                    "best": float(x[int(np.argmin(np.where(fin, J, np.inf)))]),
                    "at_lo": int(np.sum(xt <= lo + tol)), "at_hi": int(np.sum(xt >= hi - tol))})
    out.sort(key=lambda s: -abs(s["rho"] or 0))
    return clean(out)


def _band_meta_paths(design_dir: Path) -> list[Path]:
    """A design's top-level ``mesh_meta.json`` plus any WP8 band meshes, in band order.

    A band-split design (``mesh.band_split``) writes one mesh per band under ``band{k}/`` and no
    top-level meta; both routes put the same ``cad`` provenance block in each meta.
    """
    def _band_index(p: Path) -> int:
        m = re.match(r"band(\d+)$", p.parent.name)
        return int(m.group(1)) if m else 10 ** 9

    bands = sorted(design_dir.glob("band*/mesh_meta.json"),
                   key=lambda p: (_band_index(p), p.as_posix()))
    return [design_dir / "mesh_meta.json", *bands]


def _design_cad_block(design_dir: Path) -> dict | None:
    """The ``mesh_meta.json["cad"]`` provenance block of one design, or None.

    Read verbatim from what ``mesh/step_build.py`` wrote; no key is renamed or invented. A
    non-cad design (formula/GRID) has no ``cad`` block, so its answer is None (never fabricated).
    """
    for meta_path in _band_meta_paths(design_dir):
        cad = _as_dict(_read_json(meta_path)).get("cad")
        if isinstance(cad, dict):
            return cad
    return None


def _cad_inventory(cad: dict) -> dict | None:
    """Project the current ``mesh_meta.json["cad"]`` block onto the G4 chip inventory contract.

    The block on disk today (``mesh/step_build.py``) is:
    ``face_inventory`` = ``{label: count}`` (NOT a ``faces`` list), ``tool_sha256`` (NOT
    ``tool_sha``), ``tool_path``, and ``solid.solids`` / ``solid.all_shells_closed``. The chip
    consumer takes the sidecar-shaped ``{faces: [{label, count}], solids, closed, tool_sha256,
    tool_path}``; only fields the block actually carries are emitted (nothing invented, no empty
    key), and a block with none of them answers None.
    """
    out: dict[str, Any] = {}
    face_inventory = cad.get("face_inventory")
    if isinstance(face_inventory, dict) and face_inventory:
        out["faces"] = [{"label": str(label), "count": count}
                        for label, count in sorted(face_inventory.items())]
    solid = _as_dict(cad.get("solid"))
    if solid.get("solids") is not None:
        out["solids"] = solid["solids"]
    if solid.get("all_shells_closed") is not None:
        out["closed"] = solid["all_shells_closed"]
    for key in ("tool_sha256", "tool_path"):
        if cad.get(key) is not None:
            out[key] = cad[key]
    return out or None


def _step_inventory(step_dir: Path, p: Path) -> Any:
    """Inventory for one exported STEP: the ``<name>.inventory.json`` sidecar WINS when present
    (parsed as-is), else the design's ``mesh_meta.json["cad"]`` block projected onto the chip
    contract, else None.

    The design hash is the trailing component of the exporter's name (``<name>_<tag>_<hash>.step``,
    ``cli.py export-step``), so a formula-route STEP resolves to its design but stays null unless
    that design was meshed on the cad route.
    """
    sidecar = step_dir / f"{p.stem}.inventory.json"
    if sidecar.is_file():
        return _read_json(sidecar)
    m = STEP_HASH.search(p.name)
    if m is None:
        return None
    cad = _design_cad_block(step_dir.parent / "designs" / m.group(1))
    return None if cad is None else _cad_inventory(cad)


def _cma_files(run_dir: Path) -> list[dict]:
    """Every pycma log the C-5 route serves: ``cma/`` plus each ``cma/restart_k/`` directory.

    The same ``CMA_LOG_NAME`` allow-list the serving route applies, so this list and the downloadable
    files cannot disagree. Records are run-relative POSIX paths sorted by path; an absent ``cma/``
    tree is ``[]``, never an invented row.
    """
    cma = run_dir / "cma"
    if not cma.is_dir():
        return []
    dirs = [cma]
    try:
        dirs += sorted((p for p in cma.iterdir()
                        if p.is_dir() and CMA_RESTART_DIR.match(p.name)),
                       key=lambda p: p.name)
    except OSError:
        pass
    out = []
    for base in dirs:
        try:
            entries = list(base.iterdir())
        except OSError:
            continue
        for p in entries:
            if not p.is_file() or not CMA_LOG_NAME.match(p.name):
                continue
            try:
                size = int(p.stat().st_size)
            except OSError:
                continue
            out.append({"path": p.relative_to(run_dir).as_posix(),
                        "name": p.name, "size": size})
    return sorted(out, key=lambda f: f["path"])


def run_detail(runs: Path, run_id: str) -> dict:
    d = _resolve_run(runs, run_id)
    rows = read_ndjson(d / "search.ndjson")
    cfg = _config(d)
    run_json = _read_json(d / "run.json") or {}
    summ = run_summary(d)
    best_hash, seed_hash = summ["best_hash"], (rows[0]["design_hash"] if rows else None)
    seed_ok = bool(rows and rows[0].get("ok"))
    best_row = next((r for r in rows if r.get("design_hash") == best_hash and r.get("ok")), None)
    # C-1/G4: STEP files stay the existing list of names (a frozen consumer contract) and the
    # inventory is exposed additively per file; without a sidecar it falls back to the design's own
    # mesh_meta cad block, and without either it is null, never fabricated. ``step_files_detail``
    # mirrors ``step_files`` 1:1 in sorted order.
    step_dir = d / "step"
    step_files = []
    step_files_detail = []
    if step_dir.is_dir():
        for p in sorted(step_dir.glob("*.step")):
            if STEP_NAME.match(p.name):
                step_files.append(p.name)
                step_files_detail.append(
                    {"name": p.name, "inventory": _step_inventory(step_dir, p)})
    out = clean({
        "summary": summ,
        "target": cfg.get("target") or (cfg.get("brief") or {}).get("target"),
        "weights": cfg.get("weights") or (cfg.get("brief") or {}).get("weights"),
        "brief": cfg.get("brief"),
        "J": [r.get("objective") if r.get("ok") else None for r in rows],
        "terms_seed": rows[0].get("terms") if seed_ok else None,
        "terms_best": best_row.get("terms") if best_row else None,
        "sens": sensitivity(rows, cfg.get("bounds") or {}),
        "best": design_curves(d, best_hash) if best_hash else None,
        "seed": design_curves(d, seed_hash) if seed_ok and seed_hash and seed_hash != best_hash else None,
        "command": run_json.get("command"),
        "step_files": step_files,
        "step_files_detail": step_files_detail,
    })
    # Continue-run control: the last invocation's stop reason tells the run detail whether a budget
    # top-up is likely to do work (budget/interrupted) or the optimizer stopped on its own terms.
    # Same convention as below: present in run.json = pass it through, absent stays absent.
    if run_json.get("stop_reason") is not None:
        out["stop_reason"] = run_json["stop_reason"]
    # run.json["mode"] is the LAST invocation's fidelity (cma._prepare rewrites it on every resume),
    # while summary.mode (rows[0]) keeps the run's original mode. The continue control must carry the
    # current mode, or the CLI's "screen" default silently rewrites a verify/final run.
    if run_json.get("mode") is not None:
        out["mode"] = run_json["mode"]
    # C-1: WP11 provenance is written by the search only for the runs that have it. Present in
    # run.json = pass it through verbatim; absent = the key is absent here too (no shape invention).
    if isinstance(run_json.get("restarts"), list):
        out["restarts"] = clean(run_json["restarts"])
    if isinstance(run_json.get("qd"), dict):
        out["qd"] = clean(run_json["qd"])
    # G1 badge strip: the same solve-group fingerprint /api/compare exposes, always present for a
    # run (backend + solved-grid identity; every other key only when non-default).
    out["solve_group"] = _solve_group_fingerprint(d)
    # WP11a schedule from the committed config.yaml. Same validation rules as config.py
    # ``_validate_restarts`` (mode ipop|bipop, max int 0..64, both keys required); a malformed
    # block is disclosed as absent, never guessed.
    restarts_cfg = _as_dict(_as_dict(cfg.get("search")).get("restarts"))
    if set(restarts_cfg) == {"mode", "max"}:
        mode, mx = restarts_cfg.get("mode"), restarts_cfg.get("max")
        if (isinstance(mode, str) and mode in ("ipop", "bipop")
                and isinstance(mx, int) and not isinstance(mx, bool) and 0 <= mx <= 64):
            out["search_restarts"] = {"mode": mode, "max": int(mx)}
    cma_dir = d / "cma"
    out["restart_dirs"] = sorted(p.relative_to(d).as_posix() for p in cma_dir.glob("restart_*")
                                 if p.is_dir()) if cma_dir.is_dir() else []
    # C-5 companion: the exact pycma log files the raw route can serve, for direct restart-card
    # file chips. Sorted run-relative paths; [] when the run has no cma/ tree.
    out["cma_files"] = _cma_files(d)
    # S1a: the K-law feasibility preflight rides in the committed config.yaml (the merged cfg.raw
    # ``search/rundir.py::write_config_snapshot`` dumps). Pure passthrough — a truthy dict is
    # forwarded verbatim; an absent block stays absent (no shape invention).
    feasibility = cfg.get("feasibility")
    if isinstance(feasibility, dict) and feasibility:
        out["feasibility"] = clean(feasibility)
    return out


def _solve_group_fingerprint(run_dir: Path) -> dict:
    """The solve group a comparison must never silently mix (GUI plan §3.9), read from the run's
    committed ``config.yaml`` + ``run.json``.

    Identity keys are always present when derivable: ``backend`` (always) and ``freqs_hz`` (the solved
    grid identity: mode + target band + verify points-per-octave). Every other key appears ONLY when
    the run deviates from the default (``rear_res_factor`` 1.0, ``cuda_fused`` false,
    ``source_motion`` normal, objective v1, ...). Nothing is parsed from solver output and no value is
    invented: an absent config key stays absent here.
    """
    cfg = _config(run_dir)
    rj = _as_dict(_read_json(run_dir / "run.json"))
    solve = _as_dict(cfg.get("solve"))
    mesh = _as_dict(cfg.get("mesh"))
    target = _as_dict(cfg.get("target"))
    grid = _as_dict(cfg.get("grid"))

    g: dict[str, Any] = {"backend": rj.get("backend") or solve.get("backend")}
    if solve.get("cuda_fused") is True:
        g["cuda_fused"] = True
    if solve.get("source_motion") not in (None, "normal"):
        g["source_motion"] = solve["source_motion"]
    alpha = solve.get("source_profile_alpha")            # WP16 ride key (committed in config.py)
    if isinstance(alpha, (int, float)) and not isinstance(alpha, bool) and float(alpha) != 0.0:
        g["source_profile_alpha"] = alpha
    # WP14: near_correction is one group key set by ANY of the three knobs; the two numbers stay
    # separate so two near-corrected runs with different cutoffs/orders still mix-warn.
    nc, nc_cut, nc_ord = (solve.get("near_correction"), solve.get("near_correction_cutoff"),
                          solve.get("near_correction_order"))
    if nc is not None or nc_cut is not None or nc_ord is not None:
        g["near_correction"] = bool(nc) if nc is not None else True
        if nc_cut is not None:
            g["near_correction_cutoff"] = nc_cut
        if nc_ord is not None:
            g["near_correction_order"] = nc_ord
    if solve.get("solve_precision") is not None:
        g["solve_precision"] = solve["solve_precision"]
    rear = mesh.get("rear_res_factor")
    try:
        rear_f = None if rear is None else float(rear)
    except (TypeError, ValueError):
        rear_f = None
    if rear_f is not None and rear_f != 1.0:
        g["rear_res_factor"] = rear
    bs = mesh.get("band_split")
    if isinstance(bs, dict) and isinstance(bs.get("edges_hz"), list) and bs["edges_hz"]:
        g["mesh_policy"] = "band_split_v1"                # the mesher's own provenance token (WP8)
        g["band_edges_hz"] = bs["edges_hz"]
    brief = _as_dict(cfg.get("brief"))
    mounting = cfg.get("mounting") or brief.get("mounting")   # WP12 key (absent until it lands)
    if isinstance(mounting, dict) and mounting:
        g["mounting"] = mounting
    obj = _as_dict(cfg.get("objective"))
    version = obj.get("version", rj.get("objective_version"))
    try:
        version_i = None if version is None else int(version)
    except (TypeError, ValueError):
        version_i = None
    if version_i is not None and version_i != 1:          # v1 is the unlabelled default
        g["objective_version"] = version_i
    mode = rj.get("mode")
    if mode is None:                                      # older run.json / fixtures: the id names it
        bits = run_dir.name.split("-")
        mode = bits[1] if len(bits) >= 3 else None
    ident: dict[str, Any] = {}
    if mode is not None:
        ident["mode"] = mode
    for key in ("band_lo_hz", "band_hi_hz"):
        if target.get(key) is not None:
            ident[key] = target[key]
    if grid.get("verify_points_per_octave") is not None:
        ident["verify_points_per_octave"] = grid["verify_points_per_octave"]
    if ident:
        g["freqs_hz"] = ident
    # WP14: a cad recipe is PER DESIGN (``Design.params["cad"]``; config.yaml carries none), so a
    # run-level marker cannot come from the config. Proxy: the cad block of the best-objective
    # SUCCESSFUL row's mesh_meta.json, or of the seed row when nothing succeeded. A non-cad run has
    # no such block, so the key stays absent (only-when-non-default).
    rows = read_ndjson(run_dir / "search.ndjson")
    wins = [r for r in rows if r.get("ok") and r.get("objective") is not None]
    proxy = min(wins, key=lambda r: r["objective"]) if wins else (rows[0] if rows else None)
    proxy_hash = str((proxy or {}).get("design_hash") or "")
    if HASH.match(proxy_hash) and _design_cad_block(run_dir / "designs" / proxy_hash) is not None:
        g["cad_route"] = True
    qd = rj.get("qd")
    if isinstance(qd, dict) and qd.get("algorithm"):
        g["qd_algorithm"] = qd["algorithm"]
    return clean(g)


def solve_group_fingerprints(run_a: Path, run_b: Path) -> tuple[dict, dict, list[str]]:
    """(``group_a``, ``group_b``, ``mixed_keys``) for ``GET /api/compare`` (C-2). ``mixed_keys`` is
    the sorted set of fingerprint keys whose values differ (a key absent on one side counts)."""
    ga, gb = _solve_group_fingerprint(run_a), _solve_group_fingerprint(run_b)
    mixed = sorted(k for k in set(ga) | set(gb) if ga.get(k) != gb.get(k))
    return ga, gb, mixed


def run_archive(runs: Path, run_id: str) -> dict:
    """The CMA-ME quality-diversity atlas of a run (WP11b), read from the search-written
    ``archive_heatmap.json``: ``{"bins": [bins_h, bins_v], "ranges": {"h": [lo, hi], "v": [lo, hi]},
    "descriptors": {"h": name, "v": name},
    "cells": [{"h_center", "v_center", "objective", "design_hash"}]}``.

    Only OCCUPIED bins appear in ``cells``; a cell centre is the descriptor mean over the solve band
    (``mean_bw_h_deg`` on the h axis, ``mean_bw_v_deg`` on the v axis) and ``objective`` is the run's
    J (lower is better). The raw ``archive.json`` is never parsed and nothing is solved. A run without
    an atlas (every plain cma run) gets the empty pattern, exactly like a run with no evaluations.
    Additive keys the file may carry (legacy ``rows``/``axis`` aliases) are ignored, not echoed."""
    d = _resolve_run(runs, run_id)
    heat = _read_json(d / "archive_heatmap.json")
    if (not isinstance(heat, dict) or not isinstance(heat.get("bins"), list)
            or not isinstance(heat.get("ranges"), dict) or not isinstance(heat.get("cells"), list)):
        return {"run_id": run_id, "available": False, "bins": None, "ranges": None, "cells": [],
                "stats": None}
    out = {"run_id": run_id, "available": True, "bins": heat["bins"], "ranges": heat["ranges"],
           "cells": heat["cells"],
           "descriptors": heat["descriptors"] if isinstance(heat.get("descriptors"), dict) else None,
           "stats": heat.get("stats") if isinstance(heat.get("stats"), dict) else None}
    for key in ("descriptor_h", "descriptor_v"):        # optional labels, absent from the pinned file
        if isinstance(heat.get(key), str):
            out[key] = heat[key]
    return clean(out)


def mesh_surface(runs: Path, run_id: str, h: str, max_tris: int = 60000) -> dict:
    """Triangle surface of a solved design (mm), the meshed domain only (a quarter for quadrants '1',
    an x/y half for '14'/'12')."""
    d = _resolve_run(runs, run_id)
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    nt = mesh_nodes_tris(d / "designs" / h / "mesh.msh")
    if nt is None:
        raise FileNotFoundError(f"{run_id}/{h}/mesh.msh")
    pts, tris = nt
    meta = _read_json(d / "designs" / h / "mesh_meta.json") or {}
    q = (meta.get("result") or {}).get("quadrants") or _row_quadrants(d, h) \
        or (_config(d).get("mesh") or {}).get("quadrants")
    snap_axes = {"1": (0, 1), "14": (0,), "12": (1,)}.get(str(q), ())
    out_pts, out_tris, decimated = _cluster_decimate(pts, tris, max_tris, snap_axes)
    out = {"quadrants": str(q or "1234"), "n_tris": int(len(tris)),
           "verts": np.round(out_pts * 1000, 2).ravel().tolist(),
           "tris": out_tris.ravel().tolist()}
    if decimated:
        out["decimated"] = True
    # WP12: ``mesh_meta.json["mounting"]`` (the mesher + normalized blocks) is served additively so
    # the 3D view can draw the solved mesh's own outline. Absent on every non-enclosure run — the
    # key then stays absent, never fabricated.
    mounting = meta.get("mounting")
    if isinstance(mounting, dict) and mounting:
        out["mounting"] = clean(mounting)
    return out


def _row_quadrants(run_dir: Path, h: str) -> str | None:
    """The quadrant string the search recorded for one design (mesh_meta.json may be absent — the
    GRID route writes none, see the build_mesh docstring in mesh/build.py:273 — but every evaluated
    row carries it)."""
    nd = run_dir / "search.ndjson"
    if not nd.is_file():
        return None
    for row in read_ndjson(nd):
        if row.get("design_hash") == h and row.get("quadrants"):
            return str(row["quadrants"])
    return None


# ---------------------------------------------------------------------------- balloon (W6)

#: Normalised window of the balloon display (design follows Boundary Lab's
#: JWSound/boundary-lab Balloon Plot, GPL-3.0; the implementation here is our own): 0 dB sits on
#: the on-axis direction, and anything below this floor collapses onto it.
BALLOON_MIN_DB = -30.0


def _balloon_label(design_dir: Path) -> str:
    """Short human label of one design: family, plus the wall kind the generator derived."""
    dj = _read_json(design_dir / "design.json") or {}
    fam = str(dj.get("family") or "?")
    gen = _as_dict(dj.get("generator"))
    kind = _as_dict(_as_dict(gen.get("derived")).get("h")).get("type")
    return f"{fam} · {kind}" if kind else fam


def balloon_designs(runs: Path, run_id: str) -> dict:
    """Design-picker payload for the balloon view: the run's successful designs ranked by
    objective (best first, TOP_K at most), each disclosing whether a stored-balloon
    ``response.npz`` is actually on disk. Read-only: file-existence probes only."""
    d = _resolve_run(runs, run_id)
    rows = [r for r in read_ndjson(d / "search.ndjson")
            if r.get("ok") and HASH.match(str(r.get("design_hash") or ""))]
    rows.sort(key=lambda r: float(r["objective"]) if r.get("objective") is not None else math.inf)
    seen, designs = set(), []
    for r in rows:
        h = str(r["design_hash"])
        if h in seen:
            continue
        seen.add(h)
        designs.append({"hash": h, "objective": r.get("objective"), "n": r.get("n"),
                        "has_balloon": (d / "designs" / h / "response.npz").is_file()})
        if len(designs) >= TOP_K:
            break
    return clean({"run_id": run_id, "name": _config(d).get("name"), "designs": designs})


def balloon(runs: Path, run_id: str, h: str) -> dict:
    """One design's stored balloon (W6) for the GUI's three.js Balloon view.

    Reads only the ``response.npz`` the search already wrote. The per-direction order is
    theta-major exactly as stored (``balloon_layout``: index = i*nP + j; theta rows 0..180
    INCLUSIVE from +Z — both pole rows present, each holding the same direction for every phi;
    phi columns 0..360 counterclockwise from +X toward +Y, NO stored wrap column — the viewer
    closes the seam). Levels are relative to on-axis (the theta = 0 pole row), Float32-rounded
    and clipped to ``[BALLOON_MIN_DB, 0]`` dB — the Balloon display's window. Nothing is solved
    or interpolated here; bilinear interpolation on the grid is a viewer concern.
    """
    d = _resolve_run(runs, run_id)
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    p = d / "designs" / h / "response.npz"
    if not p.is_file():
        raise FileNotFoundError(f"{run_id}/{h}/response.npz")
    try:
        with np.load(p, allow_pickle=False) as z:
            freqs = np.asarray(z["freqs_hz"], float)
            spl = np.asarray(z["spl_balloon_db"], float)
            try:
                meta = json.loads(str(z["meta"]))
            except (ValueError, TypeError):
                meta = {}
            n_dof = int(z["n_dof"]) if "n_dof" in z.files else None
    except (OSError, KeyError) as exc:
        raise ValueError(f"unreadable balloon payload: {exc}") from exc
    grid = meta.get("balloon_grid")
    if not (isinstance(grid, list) and len(grid) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in grid)):
        raise ValueError(f"balloon_grid {grid!r} does not match spl_balloon_db shape {spl.shape}")
    if spl.shape != (len(freqs), grid[0] * grid[1]):
        raise ValueError(f"balloon_grid {grid!r} does not match spl_balloon_db shape {spl.shape}")
    nT, nP = int(grid[0]), int(grid[1])
    ref = spl[:, 0:nP].mean(axis=1)                      # on-axis pole row (all phi, one direction)
    rel = np.clip(spl - ref[:, None], BALLOON_MIN_DB, 0.0).astype(np.float32)
    return clean({
        "run_id": run_id, "design": h, "label": _balloon_label(d / "designs" / h),
        "freqs_hz": _rnd(freqs, 1),
        "balloon_grid": [nT, nP],
        "layout": str(meta.get("balloon_layout") or ""),
        "n_dof": n_dof,
        "distance_m": meta.get("distance_m") if isinstance(meta.get("distance_m"), (int, float)) else None,
        "min_db": BALLOON_MIN_DB,
        "spl": rel.tolist(),
    })


# ---------------------------------------------------------------------------- campaigns


@dataclass
class _Snapshot:
    """One request's worth of campaign/brief filesystem reads, each performed at most once.

    One ``/api/leaders`` call used to re-walk every run dir ~43 times and re-parse every brief
    YAML ~48 times, because each campaign in the list rebuilt the auto groups and the brief list
    from scratch.  This object is built at the public entry point and threaded down
    (``list_campaigns`` -> ``_auto_groups`` -> ``_auto_campaign_detail`` -> ``campaign_detail``),
    so the walks/parses/globs happen once per call.  Every field is filled lazily, so an entry
    point that needs only the briefs never pays for the run summaries.

    Deliberately NOT cached at module level: it lives for exactly one call, so a campaign
    directory written between two requests is always seen by the next one, and a live search's
    growing ``search.ndjson`` is re-read through ``run_summary``'s own per-file stamp memo.
    """

    runs: Path
    root: Path
    _briefs: list[dict] | None = field(default=None, repr=False)
    _claimed: set[str] | None = field(default=None, repr=False)
    _run_list: list[tuple[Path, dict]] | None = field(default=None, repr=False)
    _auto: dict[str, list[tuple[Path, dict]]] | None = field(default=None, repr=False)
    _evidence: set[str] | None = field(default=None, repr=False)

    def briefs(self) -> list[dict]:
        if self._briefs is None:
            self._briefs = list_briefs(self.root)
        return self._briefs

    def brief(self, name: str | None) -> dict:
        """The raw YAML body of the brief called ``name`` ({} when no brief has that name)."""
        return next((b["brief"] for b in self.briefs() if b["name"] == name), {})

    def claimed(self) -> set[str]:
        if self._claimed is None:
            self._claimed = _campaign_run_ids(self.runs)
        return self._claimed

    def run_list(self) -> list[tuple[Path, dict]]:
        if self._run_list is None:
            self._run_list = [(d, run_summary(d)) for d in _run_dirs(self.runs)]
        return self._run_list

    def auto_groups(self) -> dict[str, list[tuple[Path, dict]]]:
        if self._auto is None:
            self._auto = _group_auto_runs(self.run_list(), self.claimed())
        return self._auto

    def evidence(self) -> set[str]:
        if self._evidence is None:
            self._evidence = _evidence_campaigns(self.runs)
        return self._evidence


def _snapshot(runs: Path, root: Path | None = None) -> _Snapshot:
    """A fresh per-request snapshot.  Never stored by the module (see ``_Snapshot``)."""
    return _Snapshot(runs=runs, root=runs.parent if root is None else root)


def _evidence_campaigns(runs: Path) -> set[str]:
    """Campaign ids committed as evidence (docs/evidence/campaigns/<id>.campaign.json)."""
    d = runs.parent / "docs" / "evidence" / "campaigns"
    return {p.name.split(".")[0] for p in d.glob("campaign_*.campaign.json")} if d.is_dir() else set()


def superseded(runs: Path, cid: str, snap: _Snapshot | None = None) -> bool:
    """A campaign is superseded if it is older than the newest committed evidence campaign and is not
    itself committed evidence. The committed set is the reviewed record (campaigns before the
    2026-10-22 fixes scored native configs on their own targets without the size envelope; see
    docs/evidence/TYPOLOGY_SCREEN_2026-10-22.md); anything newer was run with the current code.

    ``snap`` supplies the precomputed evidence set (the glob ran per campaign before)."""
    if AUTO_ID.match(cid):
        return False
    ev = snap.evidence() if snap is not None else _evidence_campaigns(runs)
    return bool(ev) and cid not in ev and cid < max(ev)


def list_campaigns(runs: Path, snap: _Snapshot | None = None) -> list[dict]:
    """Every campaign of ``runs``: the real ones (campaign.json) newest first, then the auto
    campaigns for runs no campaign.json claims.  ``snap`` is one request's shared reads."""
    snap = snap if snap is not None else _snapshot(runs)
    out = []
    if not runs.is_dir():
        return out
    for p in sorted((p for p in runs.iterdir() if p.is_dir() and CAMPAIGN_ID.match(p.name)),
                    key=lambda p: p.name, reverse=True):
        c = _read_json(p / "campaign.json")
        if not c:
            continue
        out.append(clean({"id": p.name, "tier": c.get("tier"), "brief": c.get("brief_name"),
                          "superseded": superseded(runs, p.name, snap),
                          "seeds": c.get("seeds"), "n_entries": len(c.get("entries", [])),
                          "families": [e.get("name") for e in c.get("entries", [])]}))
    # Runs that no campaign.json claims (the night runner, a hand-launched or GUI-launched search)
    # still get a per-brief leaderboard: grouped by brief and mode, listed AFTER the real
    # campaigns so a real campaign of the same tier keeps precedence in leaders().
    for cid, members in sorted(snap.auto_groups().items()):
        names = sorted({s.get("name") or d.name for d, s in members})
        out.append(clean({"id": cid, "tier": members[0][1].get("mode") or "screen",
                          "brief": members[0][1].get("brief"), "superseded": False, "seeds": None,
                          "n_entries": len(names), "families": names, "auto": True,
                          "n_runs": len(members)}))
    return out


#: Auto campaign ids: ``auto_<brief name>__<mode>`` (brief names are BRIEF_NAME-safe).
AUTO_ID = re.compile(r"^auto_([A-Za-z0-9_.\-]+)__(screen|verify|final)$")


def _campaign_run_ids(runs: Path) -> set[str]:
    """Run ids already listed by some campaign.json (those runs belong to that campaign)."""
    out: set[str] = set()
    for p in (runs.iterdir() if runs.is_dir() else ()):
        if p.is_dir() and CAMPAIGN_ID.match(p.name):
            for e in (_read_json(p / "campaign.json") or {}).get("entries", []):
                for j in e.get("jobs") or []:
                    if j.get("run_dir"):
                        out.add(Path(j["run_dir"]).name)
    return out


def _group_auto_runs(run_list: list[tuple[Path, dict]],
                     claimed: set[str]) -> dict[str, list[tuple[Path, dict]]]:
    """Group the already-summarized runs (newest first) by ``auto_<brief>__<mode>``, skipping the
    runs a campaign.json claims and the runs without a brief (they stay in the run list only).
    Pure: the walks live on ``_Snapshot``."""
    groups: dict[str, list[tuple[Path, dict]]] = {}
    for d, s in run_list:
        if d.name in claimed:
            continue
        brief, mode = s.get("brief"), s.get("mode") or "screen"
        if not brief or not s.get("n"):
            continue
        cid = f"auto_{brief}__{mode}"
        if AUTO_ID.match(cid):
            groups.setdefault(cid, []).append((d, s))
    return groups


def _auto_groups(runs: Path, snap: _Snapshot | None = None) -> dict[str, list[tuple[Path, dict]]]:
    """Every run not claimed by a campaign.json, grouped by (brief, mode).

    ``snap`` is the request's shared reads; without one this builds its own, exactly as before."""
    if snap is None:
        snap = _snapshot(runs)
    return snap.auto_groups()


def _auto_campaign_detail(runs: Path, cid: str, snap: _Snapshot | None = None,
                          curves: bool = True) -> dict:
    """One auto campaign's entries.  ``curves=False`` is the leaderboard path: it drops the
    per-design curve payload (``best``) that ``leaders()`` never reads, keeping the standings."""
    snap = snap if snap is not None else _snapshot(runs)
    members = snap.auto_groups().get(cid)
    if not members:
        raise FileNotFoundError(cid)
    by_name: dict[str, list[tuple[Path, dict]]] = {}
    for d, s in members:
        by_name.setdefault(s.get("name") or d.name, []).append((d, s))
    entries = []
    for name, rs in by_name.items():
        js = [s["best_j"] for _, s in rs if s.get("best_j") is not None]
        best_d, best_s = min(((d, s) for d, s in rs if s.get("best_j") is not None),
                             key=lambda t: t[1]["best_j"], default=(None, None))
        best = (design_curves(best_d, best_s["best_hash"])
                if curves and best_s and best_s.get("best_hash") else None)
        entries.append({
            "name": name, "group": None, "symmetry": None, "skipped": False, "skip_reason": None,
            "family": rs[0][1].get("family"),
            "best_j": min(js) if js else None,
            "median_j": float(np.median(js)) if js else None,
            "spread": (max(js) - min(js)) if len(js) > 1 else None,
            "evals": sum(s.get("n") or 0 for _, s in rs),
            "failures": dict(sum((Counter(s.get("failures") or {}) for _, s in rs), Counter())),
            "pinned": [],
            "jobs": [{"seed": s.get("cma_seed") if s.get("cma_seed") is not None else d.name[-6:],
                      "best_j": s.get("best_j"), "run_id": d.name,
                      "returncode": None, "wall_min": None} for d, s in rs],
            "best": best, "dims": best_s.get("dims") if best_s else None,
            "best_run_id": best_d.name if best_d is not None else None,
        })
    entries.sort(key=lambda e: (e["best_j"] is None, e["median_j"] if e["median_j"] is not None else 0))
    brief = members[0][1].get("brief")
    brief_raw = snap.brief(brief)
    return clean({"id": cid, "tier": members[0][1].get("mode") or "screen", "brief": brief,
                  "seeds": None, "superseded": False, "auto": True,
                  "target": (brief_raw or {}).get("target"), "entries": entries,
                  "leaderboard_md": None})


def campaign_detail(runs: Path, cid: str, snap: _Snapshot | None = None,
                    curves: bool = True) -> dict:
    """One campaign's entries and brief target.  ``curves=False`` skips the per-design curve
    payload (``best`` stays None) for the leaderboard, which reads standings only; the detail
    views keep the default full payload."""
    snap = snap if snap is not None else _snapshot(runs)
    if AUTO_ID.match(cid):
        return _auto_campaign_detail(runs, cid, snap, curves)
    if not CAMPAIGN_ID.match(cid):
        raise ValueError(f"not a campaign id: {cid!r}")
    c = _read_json(runs / cid / "campaign.json")
    if c is None:
        raise FileNotFoundError(cid)
    entries = []
    for e in c.get("entries", []):
        jobs = e.get("jobs") or []
        js = [j.get("best_j") for j in jobs if j.get("best_j") is not None]
        best_job = min((j for j in jobs if j.get("best_j") is not None), key=lambda j: j["best_j"], default=None)
        best, dims, best_run = None, None, None
        if best_job and best_job.get("run_dir"):
            rd = Path(best_job["run_dir"])
            if rd.parent.resolve() == runs.resolve() and RUN_ID.match(rd.name):
                s = run_summary(rd)
                dims, best_run = s.get("dims"), rd.name
                if curves and s.get("best_hash"):
                    best = design_curves(rd, s["best_hash"])
        entries.append({
            "name": e.get("name"), "group": e.get("group"), "symmetry": e.get("symmetry"),
            "skipped": e.get("skipped"), "skip_reason": e.get("skip_reason"),
            "best_j": min(js) if js else None,
            "median_j": float(np.median(js)) if js else None,
            "spread": (max(js) - min(js)) if len(js) > 1 else None,
            "evals": sum((j.get("stats") or {}).get("evaluations", 0) for j in jobs),
            "failures": dict(sum((Counter((j.get("stats") or {}).get("failures_by_reason") or {}) for j in jobs),
                                 Counter())),
            "pinned": sorted({k for j in jobs for k in (j.get("pinned_bounds") or [])}),
            "jobs": [{"seed": j.get("seed"), "best_j": j.get("best_j"),
                      "run_id": Path(j["run_dir"]).name if j.get("run_dir") else None,
                      "returncode": j.get("returncode"), "wall_min": (j.get("wall_seconds") or 0) / 60}
                     for j in jobs],
            "best": best, "dims": dims, "best_run_id": best_run,
        })
    entries.sort(key=lambda e: (e["best_j"] is None, e["median_j"] if e["median_j"] is not None else 0))
    brief_raw = snap.brief(c.get("brief_name"))
    lb = runs / cid / "leaderboard.md"
    return clean({"id": cid, "tier": c.get("tier"), "brief": c.get("brief_name"), "seeds": c.get("seeds"),
                  "superseded": superseded(runs, cid, snap),
                  "target": (brief_raw or {}).get("target"),       # from the brief file named by the campaign
                  "entries": entries,
                  "leaderboard_md": lb.read_text(encoding="utf-8") if lb.exists() else None})


# ---------------------------------------------------------------------------- briefs


def brief_dirs(root: Path) -> tuple[Path, Path]:
    return root / "examples" / "briefs", root / "examples" / "briefs" / "user"


def list_briefs(root: Path, cached: list[dict] | None = None) -> list[dict]:
    """Every brief under examples/briefs/ at any depth: kind ``shipped`` (top level), ``user``
    (briefs/user/) or the subfolder path (e.g. a campaign folder).

    ``cached`` lets a per-request ``_Snapshot`` hand down its one parse; there is deliberately no
    module-level cache (a brief saved between two requests must show up on the next one)."""
    if cached is not None:
        return cached
    shipped, _user = brief_dirs(root)
    out = []
    files = sorted(p for p in shipped.rglob("*.yaml") if not p.name.startswith(".")) \
        if shipped.is_dir() else []
    for p in files:
        parent = p.parent.relative_to(shipped).as_posix()
        kind = "shipped" if parent == "." else ("user" if parent == "user" else parent)
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raw = {"_error": str(exc)}
        out.append(clean({"name": p.stem, "kind": kind,
                          "path": p.relative_to(root).as_posix(), "brief": raw}))
    return out


def save_user_brief(root: Path, name: str, brief: dict) -> Path:
    """Write a NEW brief to examples/briefs/user/<name>.yaml after the CLI's own validation.
    Never overwrites a shipped brief; refuses names that collide with one."""
    from hornlab_search.config import load_brief
    if not BRIEF_NAME.match(name or ""):
        raise ValueError("brief name: letters, digits, _ and - only (max 64)")
    shipped, user = brief_dirs(root)
    if (shipped / f"{name}.yaml").exists():
        raise ValueError(f"{name!r} is a shipped brief; choose another name")
    user.mkdir(parents=True, exist_ok=True)
    body = dict(brief)
    body["name"] = name
    import tempfile
    p = user / f"{name}.yaml"
    text = yaml.safe_dump(body, sort_keys=False)
    with tempfile.TemporaryDirectory() as td:          # validate under the real name, outside the repo
        probe = Path(td) / f"{name}.yaml"
        probe.write_text(text, encoding="utf-8")
        load_brief(probe)                               # the CLI's own schema check; raises ConfigError
    tmp = user / f".{name}.yaml.tmp"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(p)                                      # atomic: never a half-written brief
    return p


# ---------------------------------------------------------------------------- machine state


def status(root: Path, runs: Path) -> dict:
    import shutil
    from hornlab_search.search import hygiene
    from hornlab_search.search.gpulock import _lock_path, _pid_alive, _read_lock
    lock = _read_lock(_lock_path(runs))
    if lock:
        lock = dict(lock)
        lock["alive"] = bool(lock.get("pid") and _pid_alive(int(lock["pid"])))
    try:
        procs = hygiene.list_project_julia()
    except Exception:  # noqa: BLE001 - status must never fail on a probe
        procs = []
    try:
        vram = hygiene.vram_used_mib()
    except Exception:  # noqa: BLE001
        vram = None
    disk = None
    try:
        u = shutil.disk_usage(runs if runs.exists() else root)
        disk = {"free_gb": round(u.free / 1e9, 1), "total_gb": round(u.total / 1e9, 1)}
    except OSError:
        pass
    ov = runs / "overnight"
    queue_logs = sorted(ov.glob("queue_*.log")) if ov.is_dir() else []
    return clean({
        "gpu_lock": lock, "vram_mib": vram, "julia_procs": len(procs), "disk": disk,
        "queue_log": {"name": queue_logs[-1].name, "tail": tail_text(queue_logs[-1], 30),
                      "steps": queue_steps(queue_logs[-1])} if queue_logs else None,
        "current": run_progress(cur) if (lock and lock.get("alive") and (cur := current_run(runs))) else None,
        "watchdog_log": tail_text(ov / "watchdog.log", 10) if ov.is_dir() else [],
    })


# ---------------------------------------------------------------------------- configs and catalog


def catalog(root: Path) -> list[dict]:
    try:
        raw = yaml.safe_load((root / "examples" / "catalog.yaml").read_text(encoding="utf-8-sig")) or {}
    except (OSError, yaml.YAMLError):
        return []
    return [clean(e) for e in raw.get("entries", []) if isinstance(e, dict)]


def _config_seed_materializes(p: Path) -> bool:
    """True when the config's own seed materializes (the honest runnable gate).

    The old heuristic keyed on ``"lecleach" in p.stem``; lecleach is now a verified,
    live generator, so a name substring is simply wrong.  A config whose seed cannot be
    materialized is the only thing the GUI should grey out.
    """
    try:
        from hornlab_search.config import load_config
        from hornlab_search.design.space import DesignSpace
        DesignSpace.from_config(load_config(p))
        return True
    except Exception:  # noqa: BLE001 - an unloadable/unmaterializable seed is disabled
        return False


#: In-process memo for the disabled gate (ISSUES M4 local-only "GUI ``list_configs`` latency").
#: ``_config_seed_materializes`` runs the REAL generator march, and the rows kinds are brentq
#: loops (the saddle is ~25 rows), so re-materializing every seed on every refresh is the
#: visible latency the issue records.  The gate's whole input is the config file PLUS the brief
#: it names (the brief supplies the driver exit radius/angle the march starts from), so the key
#: is both files' (path, mtime_ns, size): an edited config -- or an edited brief -- re-materializes
#: on the next refresh, while an untouched pair is served from memory.  Deliberately process-local
#: (no on-disk staleness to clean up; a generator code change needs a GUI restart, exactly like
#: every other import).  Bounded by the number of config files.
_SEED_GATE_CACHE: dict[tuple, bool] = {}


def _file_stamp(p: Path | None) -> tuple | None:
    if p is None:
        return None
    try:
        st = p.stat()
    except OSError:
        return None
    return (str(p.resolve()), st.st_mtime_ns, st.st_size)


def _seed_gate_key(p: Path, raw: dict, root: Path) -> tuple:
    """Memo key for one config: its own stamp + the stamp of the brief file it names."""
    brief = raw.get("brief_file") if isinstance(raw, dict) else None
    brief_p = None
    if isinstance(brief, str) and brief:
        for cand in (p.parent / brief, root / brief):      # cfg.load_config resolution order
            if cand.exists():
                brief_p = cand
                break
    return (_file_stamp(p), _file_stamp(brief_p))


def list_configs(root: Path) -> list[dict]:
    """Every runnable config under examples/ (not briefs, not the catalog), with its catalog entry."""
    cat = {e.get("config"): e for e in catalog(root)}
    ex = root / "examples"
    out = []
    for p in sorted(ex.rglob("*.yaml")):
        if (p.name == "catalog.yaml" or p.name.startswith(".")
                or p.relative_to(ex).parts[0] in ("briefs", "drivers")):
            continue
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8-sig")) or {}
        except yaml.YAMLError:
            continue
        rel = p.relative_to(ex).as_posix()
        e = cat.get(rel, {})
        bounds = raw.get("bounds") or {}
        # honest gate: the seed materializes (never a name substring; lecleach is live).
        # Memoized on the config+brief stamps -- the march is the refresh's whole cost.
        key = _seed_gate_key(p, raw, root)
        disabled = _SEED_GATE_CACHE.get(key)
        if disabled is None:
            disabled = not _config_seed_materializes(p)
            _SEED_GATE_CACHE[key] = disabled
        entry = clean({
            "path": p.relative_to(root).as_posix(), "name": raw.get("name") or p.stem,
            "family": raw.get("family"), "generator": isinstance(raw.get("generator"), dict),
            "brief_file": raw.get("brief_file"), "catalog_name": e.get("name"), "group": e.get("group"),
            "symmetry": e.get("symmetry"), "description": e.get("description"),
            "n_knobs": sum(1 for b in bounds.values() if isinstance(b, dict) and b.get("search", True)),
            "morph_capable": morph_capable(raw),
            "gcurve_capable": gcurve_capable(raw),
            "morph_searched": any(str(k).startswith("morph_") and isinstance(b, dict)
                                  and b.get("search", True) for k, b in bounds.items()),
            "disabled": disabled})
        # Additive, honest passthrough for the Compose wizard's hybrid views: the config's REAL
        # generator block (splice/blend/grid shapes exactly as yaml.safe_load yields) and the seed
        # geometry it previews from. Absent when the yaml has none -- never fabricated.
        gen = raw.get("generator")
        if isinstance(gen, dict) and gen:
            entry["generator_block"] = clean(gen)
        seed = raw.get("seed_params")
        if isinstance(seed, dict) and seed:
            entry["seed_params"] = clean(seed)
        if bounds:              # the sandbox's fallback when the param catalog has no entry yet
            entry["bounds"] = clean(bounds)
        out.append(entry)
    return out


# ---------------------------------------------------------------------------- live progress


def run_progress(run_dir: Path) -> dict:
    """Evaluations done vs budget, best so far, rate and ETA from the run's own timestamps."""
    s = run_summary(run_dir)
    rows = read_ndjson(run_dir / "search.ndjson")
    t = [_ts(r.get("created_utc")) for r in rows[-40:]]
    t = [x for x in t if x]
    rate = None
    if len(t) >= 2 and (t[-1] - t[0]).total_seconds() > 0:
        rate = (len(t) - 1) / (t[-1] - t[0]).total_seconds() * 3600
    left = (s["budget"] - s["n"]) if s.get("budget") else None
    return clean({**s, "rate_per_h": rate,
                  "eta_min": (left / rate * 60) if (rate and left is not None and left > 0) else None})


def current_run(runs: Path, max_age_s: float = 1800) -> Path | None:
    """The run folder written most recently (within max_age_s), i.e. the search in progress."""
    import time
    best, best_t = None, 0.0
    for d in _run_dirs(runs)[:30]:
        f = d / "search.ndjson"
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        if m > best_t:
            best, best_t = d, m
    return best if best and time.time() - best_t < max_age_s else None


_STEP = re.compile(r"^=== (\S+) (START|END|SKIP) (\S+)(?: : (.*?))?(?: exit (-?\d+))?(?: \(.*\))?$")


def queue_steps(log: Path) -> list[dict]:
    """START/END/SKIP lines of an overnight queue log as a timeline."""
    steps: dict[str, dict] = {}
    order = []
    for ln in tail_text(log, 100000):
        m = _STEP.match(ln.strip())
        if not m:
            continue
        ts, kind, name, cmd, rc = m.groups()
        if name not in steps:
            steps[name] = {"name": name, "started": None, "ended": None, "exit": None, "command": None,
                           "skipped": False}
            order.append(name)
        st = steps[name]
        if kind == "START":
            st["started"], st["command"] = ts, cmd
        elif kind == "END":
            st["ended"], st["exit"] = ts, int(rc) if rc is not None else None
        else:
            st["skipped"] = True
    return [steps[n] for n in order]


# ---------------------------------------------------------------------------- leaders

TIER_RANK = {"compare": 2, "screen": 1}


def leaders(runs: Path, snap: _Snapshot | None = None) -> list[dict]:
    """Per brief, the leading family of the latest campaign of the strongest tier (compare beats
    screen; dry-run has no scores). 'clearly_ahead' applies the ranking rule: the leader's median beats
    the runner-up's by more than both spreads (screen tier has one repeat: never 'clearly').

    One snapshot for the whole call, and the per-campaign details are read with ``curves=False``:
    the leaderboard only reads standings, so the curve payloads (the bulk of the old 18 s) are
    never built.  Both are per-call, so a campaign dir created between two calls is seen by the
    second one."""
    snap = snap if snap is not None else _snapshot(runs)
    chosen: dict[str, dict] = {}
    for c in list_campaigns(runs, snap):                 # newest first
        tier, brief = c.get("tier"), c.get("brief")
        if not brief or tier not in TIER_RANK or c.get("superseded"):
            continue
        cur = chosen.get(brief)
        if cur is None or TIER_RANK[tier] > TIER_RANK[cur["tier"]]:
            chosen[brief] = c
    out = []
    for brief, c in sorted(chosen.items()):
        try:
            d = campaign_detail(runs, c["id"], snap, curves=False)
        except (FileNotFoundError, ValueError):
            continue
        scored = [e for e in d["entries"] if e.get("median_j") is not None and not e.get("skipped")]
        scored.sort(key=lambda e: e["median_j"])
        if not scored:
            continue
        lead, nxt = scored[0], (scored[1] if len(scored) > 1 else None)
        gap = (nxt["median_j"] - lead["median_j"]) if nxt else None
        sp = [x for x in ((lead.get("spread"), nxt.get("spread")) if nxt else ()) if x is not None]
        clearly = bool(nxt and d["tier"] == "compare" and len(sp) == 2 and gap > max(sp))
        out.append(clean({"brief": brief, "campaign_id": c["id"], "tier": d["tier"],
                          "family": lead["name"], "group": lead.get("group"), "median_j": lead["median_j"],
                          "best_j": lead.get("best_j"), "spread": lead.get("spread"), "dims": lead.get("dims"),
                          "best_run_id": lead.get("best_run_id"), "runner_up": nxt["name"] if nxt else None,
                          "gap": gap, "clearly_ahead": clearly, "n_families": len(scored)}))
    return out


# ---------------------------------------------------------------------------- typologies


def typologies(root: Path, runs: Path, snap: _Snapshot | None = None) -> list[dict]:
    """Every catalog family (classical, hybrid, Magnus-native, legacy) with: parameter count, brief
    compatibility (the CLI's own ``campaign.is_compatible``), the budgets a campaign would give it
    (``campaign.budget_for_tier``), and its best result in the latest campaign of the strongest tier per
    brief, with the best design's size and wall cross-section.

    One snapshot for the whole call; the per-campaign details keep their curve payloads (the
    profiles are part of this view)."""
    from hornlab_search.search.campaign import budget_for_tier, is_compatible
    snap = snap if snap is not None else _snapshot(runs, root)
    briefs = snap.briefs()
    cfgs = {c["catalog_name"]: c for c in list_configs(root) if c.get("catalog_name")}
    # per family: its result in the newest campaign of each scored tier per brief THAT CONTAINS IT
    # (a later campaign that re-ran only some families must not hide the others' last result)
    results: dict[str, list[dict]] = {}
    seen: set[tuple] = set()
    for c in list_campaigns(runs, snap):                 # newest first
        tier, brief = c.get("tier"), c.get("brief")
        if not brief or tier not in TIER_RANK or c.get("superseded"):
            continue
        try:
            d = campaign_detail(runs, c["id"], snap)
        except (FileNotFoundError, ValueError):
            continue
        ranked = sorted((e for e in d["entries"] if e.get("median_j") is not None), key=lambda e: e["median_j"])
        for e in d["entries"]:                           # ran, but nothing valid under this brief
            key = (e["name"], brief, tier)
            if e.get("median_j") is None and not e.get("skipped") and key not in seen:
                seen.add(key)
                results.setdefault(e["name"], []).append({
                    "brief": brief, "tier": d["tier"], "campaign_id": c["id"], "rank": None, "of": len(ranked),
                    "median_j": None, "no_valid": True, "failures": e.get("failures")})
        for rank, e in enumerate(ranked, 1):
            key = (e["name"], brief, tier)
            if key in seen:
                continue
            seen.add(key)
            results.setdefault(e["name"], []).append({
                "brief": brief, "tier": d["tier"], "campaign_id": c["id"], "rank": rank, "of": len(ranked),
                "median_j": e["median_j"], "spread": e.get("spread"), "dims": e.get("dims"),
                "best_run_id": e.get("best_run_id"), "pinned": e.get("pinned"),
                "profile": (e.get("best") or {}).get("profile"),
                # measured wall time per evaluation in that campaign (includes cache hits and failures)
                "s_per_eval": (sum((j.get("wall_min") or 0) for j in e.get("jobs") or []) * 60 / e["evals"])
                              if e.get("evals") else None})
    for v in results.values():
        v.sort(key=lambda r: (r["brief"], -TIER_RANK[r["tier"]]))
    out = []
    for e in catalog(root):
        cfg = cfgs.get(e.get("name"), {})
        k = int(cfg.get("n_knobs") or 0)
        compat = {}
        for b in briefs:
            ok, why = is_compatible(e, b["brief"])
            compat[b["name"]] = {"ok": ok, "reason": why}
        out.append(clean({
            "name": e.get("name"), "group": e.get("group"), "symmetry": e.get("symmetry"),
            "description": e.get("description"), "config": cfg.get("path"), "n_knobs": k,
            "disabled": bool(cfg.get("disabled")),
            "morph_capable": bool(cfg.get("morph_capable")),
            "morph_searched": bool(cfg.get("morph_searched")),
            "budget": {"screen": budget_for_tier("screen", k), "compare": budget_for_tier("compare", k)},
            "compat": compat, "results": results.get(e.get("name"), [])}))
    order = {"classical": 0, "hybrid": 1, "magnus": 2, "legacy": 3}
    out.sort(key=lambda t: (order.get(t["group"], 9), t["name"] or ""))
    return out


# ---------------------------------------------------------------------------- evolution (time-lapse)

EVO_VERSION = 2
M3D_VERSION = 2
M3D_DEFAULT_CAP = 30000


def _improvement_flags(rows: list[dict]) -> list[bool]:
    """Best-so-far transitions over the evaluation rows -- the ONE frame-selection rule shared by
    ``evolution()`` (2D) and ``evolution_frames3d()`` (3D), so the two players never disagree."""
    flags: list[bool] = []
    best = None
    for r in rows:
        ok = bool(r.get("ok")) and r.get("objective") is not None
        j = float(r["objective"]) if ok else None
        improved = False
        if j is not None:
            improved = best is None or j < best
            if improved:
                best = j
        flags.append(improved)
    return flags


def _decimate(pts: list, n: int) -> list:
    if len(pts) <= n:
        return pts
    step = (len(pts) - 1) / (n - 1)
    return [pts[round(i * step)] for i in range(n)]


def _cluster_once(pts: np.ndarray, tris: np.ndarray, cell: float,
                  snap_axes: tuple[int, ...]):
    """One vertex-clustering pass at grid size ``cell`` (metres): every occupied grid cell becomes
    one vertex at its members' centroid, indices are rebuilt, degenerate and duplicate triangles are
    dropped, and unused cells are compacted away. ``snap_axes`` holds the symmetry-plane axes of a
    quarter/half mesh; a cell that contains a vertex lying on such a plane keeps that coordinate at
    exactly zero, so the mirror seam stays gap-free."""
    keys = np.floor(pts / cell).astype(np.int64)
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    inv = inv.ravel()
    ncell = int(inv.max()) + 1 if inv.size else 0
    sums = np.zeros((ncell, 3), dtype=float)
    np.add.at(sums, inv, pts)
    counts = np.bincount(inv, minlength=ncell).astype(float)
    reps = sums / counts[:, None]
    for ax in snap_axes:
        on = np.abs(pts[:, ax]) <= 1e-12
        if np.any(on):
            hit = np.zeros(ncell, dtype=bool)
            hit[inv[on]] = True
            reps[hit, ax] = 0.0

    t = inv[tris]
    keep = (t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])
    t = t[keep]
    if not t.size:
        return reps[:0], np.zeros((0, 3), dtype=np.int64)
    # Dedupe by sorted corner set: a collapsed quad would otherwise render as two coincident,
    # oppositely wound faces (z-fighting reads as flickering holes).
    _, first = np.unique(np.sort(t, axis=1), axis=0, return_index=True)
    t = t[np.sort(first)]
    used = np.unique(t)
    remap = -np.ones(len(reps), dtype=np.int64)
    remap[used] = np.arange(len(used))
    return reps[used], remap[t]


def _cluster_decimate(pts: np.ndarray, tris: np.ndarray, cap: int,
                      snap_axes: tuple[int, ...] = ()):
    """Hole-free triangle decimation toward ``cap`` triangles.

    Stride subsampling (``tris[::k]``) keeps every k-th triangle of a connected sheet, so half or
    more of the surface is punched out as scattered single-triangle holes — exactly the "randomly
    transparent triangles" the owner saw. Vertex clustering instead welds neighbouring vertices,
    which coarsens the sheet but keeps it continuous. The grid size is bisected on the surface's
    own area so the result lands just under ``cap`` (and never zero unless the budget is absurd).
    Returns ``(pts, tris, decimated)``; untouched when ``len(tris) <= cap``."""
    n_full = int(len(tris))
    if n_full <= cap:
        return pts, tris, False
    a, b, c = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
    area = float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum()) * 0.5
    diagonal = float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0)))
    if not np.isfinite(area) or area <= 0 or diagonal <= 0:
        return pts, tris, False
    # A sheet occupies ~area/cell^2 cells; seed loosely around the count the budget implies.
    seed = math.sqrt(area / max(1.0, cap / 2.0))
    lo = max(seed * 1e-3, diagonal * 1e-6)   # fine grid: ~everything survives
    hi = max(seed * 3.0, diagonal)           # coarse grid: ~nothing survives
    best = None
    smallest = None
    for _ in range(20):
        cell = math.sqrt(lo * hi)
        rp, rt = _cluster_once(pts, tris, cell, snap_axes)
        if len(rt) > cap:
            lo = cell
            if smallest is None or len(rt) < len(smallest[1]):
                smallest = (rp, rt)
        else:
            if len(rt) and (best is None or len(rt) > len(best[1])):
                best = (rp, rt)
            hi = cell
        if hi / lo < 1.02:
            break
    rp, rt = best if best is not None else (smallest if smallest is not None else (pts, tris))
    return rp, rt, True


def _hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convex hull (Andrew's monotone chain), counter-clockwise."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def mouth_outline(pts: np.ndarray, quadrants: str) -> list[list[float]] | None:
    """Front view of the mouth (mm): the convex outline of the mesh nodes within 1.5 % of the depth of the
    mouth plane, mirrored to the full mouth when the mesh is a quarter. Outer rim, shell included.
    (Mouths in these families are convex: round, elliptical or rounded-rectangular.)"""
    if pts is None or not len(pts):
        return None
    z0, z1 = float(pts[:, 2].min()), float(pts[:, 2].max())
    rim = pts[pts[:, 2] >= z1 - 0.015 * max(z1 - z0, 1e-9)]
    if len(rim) < 3:
        return None
    xy = [(float(x), float(y)) for x, y in rim[:, :2]]
    if str(quadrants) == "1":
        xy = xy + [(-x, y) for x, y in xy] + [(-x, -y) for x, y in xy] + [(x, -y) for x, y in xy]
    return [[round(x * 1000, 1), round(y * 1000, 1)] for x, y in _hull([(round(a, 6), round(b, 6)) for a, b in xy])]


def _frame_geometry(design_dir: Path) -> dict | None:
    nt = mesh_nodes_tris(design_dir / "mesh.msh")
    if nt is None:
        return None
    pts, tris = nt
    meta = _read_json(design_dir / "mesh_meta.json") or {}
    q = ((meta.get("result") or {}).get("quadrants")) or "1234"
    sec: dict = {}
    for key, ax in (("h", 0), ("v", 1)):
        chains = _plane_chains(pts, tris, ax) if len(tris) else []
        if chains:
            ch = max(chains, key=len)
            sec[key] = _decimate([[round(float(pts[i, 2]) * 1000, 1), round(float(pts[i, ax]) * 1000, 1)] for i in ch], 90)
            sec["kind"] = "section"
    return {"section": sec or None, "mouth": mouth_outline(pts, q)}


def evolution(runs: Path, run_id: str) -> dict:
    """Every evaluation of a run in order, for the time-lapse player: score, failure kind, normalised shape
    parameters, and (when the design was meshed) its wall cross-section and mouth outline. Geometry comes
    only from the meshes the search saved. Cached in runs/.gui_cache (GUI-owned), keyed on the run's
    search.ndjson size + mtime, so a running search is re-read as it grows."""
    d = _resolve_run(runs, run_id)
    nd = d / "search.ndjson"
    st = nd.stat()
    cache = runs / ".gui_cache" / f"evolution_{run_id}.json"
    old = _read_json(cache) if cache.exists() else None
    key = [EVO_VERSION, st.st_size, int(st.st_mtime)]
    if old and old.get("key") == key:
        return old["data"]
    rows = read_ndjson(nd)
    cfg = _config(d)
    bounds = {k: b for k, b in (cfg.get("bounds") or {}).items()
              if isinstance(b, dict) and "lo" in b and "hi" in b and b.get("search", True)}
    same_version = bool(old) and (old.get("key") or [None])[0] == EVO_VERSION
    prev = ({f["hash"]: f for f in old["data"].get("frames", []) if f.get("geo")}       # reuse geometry while
            if same_version else {})                                                    # the search grows
    frames, best = [], None
    flags = _improvement_flags(rows)
    geo_by_hash: dict[str, dict | None] = {}
    for i, r in enumerate(rows):
        h = r.get("design_hash")
        ok = bool(r.get("ok")) and r.get("objective") is not None
        j = float(r["objective"]) if ok else None
        improved = flags[i]
        if improved and j is not None:
            best = j
        kv = _knob_values(r)
        knobs = {k: (None if k not in kv else round((kv[k] - float(b["lo"])) / ((float(b["hi"]) - float(b["lo"])) or 1), 4))
                 for k, b in bounds.items()}
        if h not in geo_by_hash:
            if h in prev:
                geo_by_hash[h] = prev[h]["geo"]
            elif HASH.match(h or "") and (d / "designs" / h / "mesh.msh").exists():
                geo_by_hash[h] = _frame_geometry(d / "designs" / h)
            else:
                geo_by_hash[h] = None
        frames.append({"n": r.get("n"), "hash": h, "j": j, "ok": ok, "improved": bool(improved), "best_j": best,
                       "kind": None if ok else _err_kind(r), "cached": bool(r.get("cached")),
                       "knobs": knobs, "geo": geo_by_hash[h]})
    # fixed axes for the whole run, so motion on screen is the design changing, not the scale
    ext = {"rmax": 1.0, "z0": float("inf"), "z1": float("-inf"), "mmax": 1.0}
    for f in frames:
        g = f["geo"] or {}
        for k in ("h", "v"):
            for z, r_ in ((g.get("section") or {}).get(k) or []):
                ext["rmax"] = max(ext["rmax"], abs(r_)); ext["z0"] = min(ext["z0"], z); ext["z1"] = max(ext["z1"], z)
        for x, y in (g.get("mouth") or []):
            ext["mmax"] = max(ext["mmax"], abs(x), abs(y))
    data = clean({"run_id": run_id, "name": cfg.get("name"), "bounds": {k: [b["lo"], b["hi"]] for k, b in bounds.items()},
                  "extent": ext, "frames": frames,
                  "n_improvements": sum(1 for f in frames if f["improved"])})
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps({"key": key, "data": data}), encoding="utf-8")
        tmp.replace(cache)
    except OSError:
        pass
    return data


def evolution_frames3d(runs: Path, run_id: str, max_tris_per_frame: int = M3D_DEFAULT_CAP) -> dict:
    """Per-improved-frame triangle geometry for the 3D time-lapse.

    Frame selection is EXACTLY ``evolution()``'s rule, shared through ``_improvement_flags``: a row
    is a frame when it is ok and sets a new best-so-far J. Only frames whose ``designs/<hash>/mesh.msh``
    the search actually saved are returned; an improved row without a saved mesh is skipped (never
    invented) and disclosed in ``note``. A frame above ``cap`` triangles is decimated hole-free by
    vertex clustering (``_cluster_decimate``); ``decimated`` is true exactly when that happened.

    Cache: ``runs/.gui_cache/evolution_<id>_m3d.json``, keyed on ``search.ndjson`` (size, mtime) plus
    every improved frame's ``mesh.msh`` (path, mtime_ns, size) -- a grown search or a (re)written/
    deleted mesh invalidates. ``mesh_meta.json``/``config.yaml`` are static run artifacts and stay
    outside the key (the same discipline as ``evolution()``'s geometry cache). The ndjson is always
    re-read so the key can be computed; the cache saves the expensive mesh parsing. Atomic write.
    """
    d = _resolve_run(runs, run_id)
    nd = d / "search.ndjson"
    cap = max(1, int(max_tris_per_frame))
    st = nd.stat()
    rows = read_ndjson(nd)
    cfg = _config(d)
    cfg_q = _as_dict(cfg.get("mesh")).get("quadrants")
    flags = _improvement_flags(rows)
    improved = [(i, r) for i, (r, imp) in enumerate(zip(rows, flags)) if imp]

    # Cache key: search.ndjson stamp + each improved hash's mesh stamp (None tuple when absent, so a
    # mesh appearing later invalidates too). Row order is stable for an unchanged ndjson.
    stamps: list[list] = []
    for _, r in improved:
        h = r.get("design_hash")
        p = d / "designs" / str(h) / "mesh.msh" if HASH.match(h or "") else None
        try:
            ms = p.stat() if p is not None else None
        except OSError:
            ms = None
        stamps.append([str(h) if h is not None else None,
                       ms.st_mtime_ns if ms else None, ms.st_size if ms else None])

    cache = runs / ".gui_cache" / f"evolution_{run_id}_m3d.json"
    key = [M3D_VERSION, cap, st.st_size, int(st.st_mtime), stamps]
    old = _read_json(cache) if cache.exists() else None
    if isinstance(old, dict) and old.get("key") == key:
        return old["data"]

    frames: list[dict] = []
    skipped: list[str] = []
    for _, r in improved:
        h = r.get("design_hash")
        if not HASH.match(h or ""):
            skipped.append(str(h))
            continue
        design_dir = d / "designs" / str(h)
        nt = mesh_nodes_tris(design_dir / "mesh.msh")
        if nt is None:
            skipped.append(str(h))
            continue
        pts, tris = nt
        meta = _as_dict(_read_json(design_dir / "mesh_meta.json"))
        q = (_as_dict(meta.get("result")).get("quadrants") or r.get("quadrants")
             or cfg_q or "1234")
        n_full = int(len(tris))
        snap_axes = {"1": (0, 1), "14": (0,), "12": (1,)}.get(str(q), ())
        out_pts, out_tris, decimated = _cluster_decimate(pts, tris, cap, snap_axes)
        frames.append(clean({
            "n": r.get("n"),
            "objective": float(r["objective"]) if r.get("objective") is not None else None,
            "mesh_hash": h,
            "quadrants": str(q),
            "verts": np.round(out_pts * 1000, 2).ravel().tolist(),
            "tris": out_tris.ravel().tolist(),
            "n_tris_full": n_full,
            "decimated": bool(decimated),
            "n_verts": int(len(pts)),
        }))

    available = bool(frames)
    if not rows:
        note = "no evaluations recorded yet"
    elif not improved:
        note = "no successful evaluation to animate (no improved frame)"
    elif not available or skipped:
        note = f"{len(skipped)} improved frame(s) skipped: no saved mesh"
    else:
        note = None
    data = clean({"run_id": run_id, "available": available, "cap": cap, "frames": frames})
    if note:
        data["note"] = note
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps({"key": key, "data": data}), encoding="utf-8")
        tmp.replace(cache)
    except OSError:
        pass
    return data


# ---------------------------------------------------------------------------- sandbox preview

#: Coarse density the 2026-10-25 sandbox spike measured for the formula/native preview route
#: (65 angular x 24 axial): 17-35 ms including 3D on the idle machine. Grid/rows kinds use the
#: config's own march arrays instead (their resolution is part of the construction).
PREVIEW_ANGULAR_SEGMENTS = 65
PREVIEW_LENGTH_SEGMENTS = 24
PREVIEW_NOTES_ENVELOPE_NATIVE = (
    "envelope estimator has FREEFORM-anchor and GRID branches only; OSSE/R-OSSE/ICW params return None"
)
PREVIEW_NOTES_CAD = (
    "CAD/STEP recipe - geometry authored by tools/cad/multicell.py; no on-demand preview in the mesher"
)


def _preview_config(root: Path, name: str) -> dict:
    """Resolve a config NAME through ``list_configs`` (never a client path); 404 when unknown.

    Process-local memo on the two config-directory stamps: a live sandbox drag calls this on
    every tick, and re-parsing ~46 YAML files per tick (measured 0.7 s under cProfile) would
    swamp the 20-30 ms geometry. Adding/removing a config file changes a directory mtime and
    rebuilds the index; file CONTENT edits do not change name -> path resolution (the seed gate
    keeps its own per-file stamp cache).
    """
    key = str(root.resolve())
    try:
        ex = root / "examples"
        signature = tuple(
            d.stat().st_mtime_ns for d in [ex, *sorted(q for q in ex.rglob("*") if q.is_dir())]
            if d.relative_to(ex).parts[:1] != ("briefs",))
    except OSError:
        signature = None
    cached = _PREVIEW_CONFIG_CACHE.get(key)
    if cached is None or signature is None or cached[0] != signature:
        cached = (signature, list_configs(root))
        _PREVIEW_CONFIG_CACHE[key] = cached
    for entry in cached[1]:
        if entry.get("name") == name:
            return entry
    # A TYPOLOGY LINK carries the catalog name (`#/typology/<catalog name>` from /api/typologies),
    # which differs from the config's own `name:` whenever examples/catalog.yaml renames it - all
    # five cone_plughorn configs are like that (catalog `cone_plughorn_7sh` vs config
    # `cone_plughorn__evo7sh_narrow`), so the link used to 404 and the page showed "preview endpoint
    # unavailable". Exact config name wins; the catalog name is the fallback.
    for entry in cached[1]:
        if entry.get("catalog_name") == name:
            return entry
    raise FileNotFoundError(f"unknown config {name!r}")


#: ``root -> (directory stamps, list_configs entries)``; see ``_preview_config``.
_PREVIEW_CONFIG_CACHE: dict[str, tuple] = {}


def _preview_brief_path(root: Path, name: str) -> Path:
    for entry in list_briefs(root):
        if entry.get("name") == name:
            return root / entry["path"]
    raise FileNotFoundError(f"unknown brief {name!r}")


def _build_viewport(mcfg: dict) -> dict:
    """The one viewport call the preview makes (monkeypatched by the silent-OSSE pin test)."""
    from hornlab_mesher.viewport import build_viewport_geometry_from_config
    return build_viewport_geometry_from_config(mcfg, point_lists=False)


#: Native families whose mesher branch takes the Ath Morph section.
MORPH_FAMILIES = ("OSSE", "R-OSSE", "ICW", "FREEFORM")


def morph_capable(raw: dict) -> bool:
    """Can this config take native Morph? Native OSSE / R-OSSE / ICW / FREEFORM (not a CAD
    recipe), or a generated typology with an elliptical mouth (the generator refuses Morph on a
    superellipse / rounded-rectangle mouth: two outline mechanisms). Rows/grid typologies make
    their mouth from the per-azimuth law, so Morph does not apply to them."""
    gen = raw.get("generator")
    if isinstance(gen, dict):
        return gen.get("name") not in ("grid",) and gen.get("mouth", "ellipse") == "ellipse"
    seed = raw.get("seed_params") or {}
    return str(raw.get("family", "")) in MORPH_FAMILIES and "cad" not in seed


try:  # the mesher's config refusal type (absent mesher -> nothing to catch)
    from hornlab_mesher.config_parser import ConfigError as _MesherConfigError
except Exception:  # noqa: BLE001
    class _MesherConfigError(Exception):
        pass


def gcurve_capable(raw: dict) -> bool:
    """Ath's OS-SE guiding curve (superellipse / superformula mouth law that sets a different
    coverage angle in every direction -- the source of Ath's creased CORE / TwinRay walls) is an
    OSSE-only mesher feature."""
    return (not isinstance(raw.get("generator"), dict) and str(raw.get("family", "")) == "OSSE"
            and "cad" not in (raw.get("seed_params") or {}))


def _preview_extra_keys(cfg) -> set[str]:
    """Knobs the sandbox may set although the config neither seeds nor bounds them: every
    numeric key the native family accepts (Morph, wall, ...), and the generator's opt-in Morph
    knobs. Rows/grid blocks take only their own keys (their mouth IS the per-azimuth law)."""
    from hornlab_search.design import families
    from hornlab_search.design.generators import registry
    gen = cfg.generator if isinstance(cfg.generator, dict) else None
    if gen is None:
        if "cad" in cfg.seed_params:
            return set()
        keys = families.FAMILY_KEYS.get(str(cfg.family), {})
        return {k for k, spec in keys.items() if spec.kind in (int, float)}
    if gen.get("name") == "grid":
        return set()
    if gen.get("name") == "plughorn":                 # every key of the CAD tool is a knob
        from hornlab_search.mesh import step_build
        return set(step_build.load_cad_tool(tool=step_build.PLUGHORN_TOOL).KEYS)
    return {k for k in registry.DEFAULT_KNOBS if k.startswith("morph_")}


def _preview_knobs(cfg, overrides: dict) -> tuple[dict, list[str]]:
    """Merge requested knobs per key: valid names win, unknown names are named and ignored."""
    allowed = set(cfg.bounds_raw) | set(cfg.seed_params) | _preview_extra_keys(cfg)
    effective = copy.deepcopy(cfg.seed_params)
    notes: list[str] = []
    for key, value in overrides.items():
        if key not in allowed:
            notes.append(f"unknown knob {key!r} ignored (not in bounds or seed_params)")
            continue
        effective[key] = value
    return effective, notes


def _closest_row(angles, target: float) -> int:
    arr = np.asarray(angles, dtype=float)
    delta = np.abs(np.angle(np.exp(1j * (arr - float(target)))))
    return int(np.argmin(delta))


def _rows_angles(meta: dict, n_phi: int) -> np.ndarray:
    span = str(meta.get("row_span") or meta.get("span") or
               ("half" if meta.get("half_model") else "quarter"))
    if span == "half":
        return np.linspace(-0.5 * math.pi, 0.5 * math.pi, n_phi)
    if span == "half_xz":
        return np.linspace(0.0, math.pi, n_phi)
    if span == "full":
        return np.linspace(0.0, 2.0 * math.pi, n_phi, endpoint=False)
    return np.linspace(0.0, 0.5 * math.pi, n_phi)


def _meridian(row) -> list[list[float]]:
    arr = np.asarray(row, dtype=float)
    z = arr[:, 2]
    r = np.hypot(arr[:, 0], arr[:, 1])
    return [[round(float(a), 3), round(float(b), 3)] for a, b in zip(z, r)]


def _ring(row) -> list[list[float]]:
    arr = np.asarray(row, dtype=float)
    return [[round(float(a), 3), round(float(b), 3)] for a, b in zip(arr[:, 0], arr[:, 1])]


def _sections(inner, outer, angles) -> tuple[dict, dict]:
    """H/V meridians at phi=0 and phi=90, plus the mouth ring from the last station.

    The rows are chosen by ANGLE, not by index: the spike's aspect-ratio finding requires the
    section to come from the REAL grid row (a half model's first row is -90, and a full ring's
    last row is not the V plane). Quarter/half grids therefore give exactly row 0/last row.
    """
    inner = np.asarray(inner, dtype=float)
    outer_arr = None if outer is None else np.asarray(outer, dtype=float)
    h = _closest_row(angles, 0.0)
    v = _closest_row(angles, 0.5 * math.pi)
    section = {
        "h": {"inner": _meridian(inner[h]),
              "outer": [] if outer_arr is None else _meridian(outer_arr[h])},
        "v": {"inner": _meridian(inner[v]),
              "outer": [] if outer_arr is None else _meridian(outer_arr[v])},
    }
    mouth = {
        "inner": _ring(inner[:, -1, :]),
        "outer": [] if outer_arr is None else _ring(outer_arr[:, -1, :]),
    }
    return section, mouth


def _rows_overshoot_from_arrays(inner, meta: dict, wall_mm: float, brief: dict | None) -> float:
    """Reuse the rows march already built instead of re-marching (the spike measured 570 ms).

    The arithmetic is the same one ``registry._grid_overshoot_estimate`` applies to
    ``grid.envelope_extents``: outer width/height include the shell in full, and the depth is the
    grid's own axial span (the bend is already inside it) plus the shell. Limits are the
    registry's own constants, not copies of a number.
    """
    from hornlab_search.design.generators.registry import _ENVELOPE_MOUTH_TOLERANCE_MM
    from hornlab_search.search.evaluate import ENVELOPE_DEPTH_ALLOWANCE_MM

    env = (brief or {}).get("envelope") or {}
    if not env:
        return 0.0
    arr = np.asarray(inner, dtype=float)
    lim_w = float(env.get("max_mouth_w_mm", 1e9)) + _ENVELOPE_MOUTH_TOLERANCE_MM
    lim_h = float(env.get("max_mouth_h_mm", 1e9)) + _ENVELOPE_MOUTH_TOLERANCE_MM
    lim_d = float(env.get("max_depth_mm", 1e9)) + float(ENVELOPE_DEPTH_ALLOWANCE_MM)
    if not (lim_w > 0.0 and lim_h > 0.0 and lim_d > 0.0):
        return 0.0
    width = 2.0 * float(np.max(np.abs(arr[..., 0]))) + 2.0 * wall_mm
    height = 2.0 * float(np.max(np.abs(arr[..., 1]))) + 2.0 * wall_mm
    depth = float(np.max(arr[..., 2]) - np.min(arr[..., 2])) + wall_mm
    return max(width / lim_w - 1.0, height / lim_h - 1.0, depth / lim_d - 1.0, 0.0)


def _preview_response(*, config: str, brief: str | None, kind: str, quadrants: str,
                      available: bool, knobs: dict, section: dict, mouth: dict,
                      envelope: dict, shape3d: dict, slow: bool, timings: dict,
                      notes: list[str], rejected: list[str] | None = None,
                      dims: dict | None = None, morph_capable: bool = False,
                      gcurve_capable: bool = False) -> dict:
    return clean({
        "version": 1,
        "config": config,
        "brief": brief,
        "kind": kind,
        "units": "mm",
        "quadrants": str(quadrants),
        "available": bool(available),
        "knobs": knobs,
        "section": section,
        "mouth": mouth,
        "envelope": envelope,
        "shape3d": shape3d,
        "slow": bool(slow),
        "timings_ms": {k: round(float(v), 3) for k, v in timings.items()},
        "notes": notes,
        # Why a search would refuse this shape (envelope / self-approach). The geometry is
        # still drawn: the sandbox is for seeing what a knob does, not only what is legal.
        "rejected": list(rejected or []),
        # The full horn's measured size (outer shell when present), mm.
        "dims": dims,
        "morph_capable": bool(morph_capable),
        "gcurve_capable": bool(gcurve_capable),
    })


def _preview_dims(inner, outer) -> dict | None:
    """Full-horn width / height / depth (mm) from the preview grid, mirror-aware: a quarter or
    half model is symmetric about the planes it omits, so a one-sided extent counts twice."""
    pts = np.asarray(outer if outer is not None else inner, dtype=float).reshape(-1, 3)
    if pts.size == 0 or not np.all(np.isfinite(pts)):
        return None

    def span(v):
        lo, hi = float(v.min()), float(v.max())
        # one-sided (a mirror model) unless the far side reaches 2 % of the near side
        return hi - lo if -lo > 0.02 * max(hi, 1.0) else 2.0 * max(hi, -lo)

    return {"w": round(span(pts[:, 0]), 1), "h": round(span(pts[:, 1]), 1),
            "d": round(float(pts[:, 2].max() - pts[:, 2].min()), 1)}


def _measured_envelope(dims: dict | None, brief: dict | None) -> dict:
    """Overshoot of the measured size against the brief's envelope (native families, which
    have no estimator branch)."""
    env = (brief or {}).get("envelope") or {}
    if not dims:
        return {"available": False, "reason": "no preview geometry to measure"}
    ratios = [dims[k] / float(env[e]) for k, e in (("w", "max_mouth_w_mm"), ("h", "max_mouth_h_mm"),
                                                   ("d", "max_depth_mm"))
              if env.get(e) and float(env[e]) > 0]
    if not ratios:
        return {"available": False, "reason": "the brief has no size envelope"}
    return {"available": True, "overshoot": round(max(0.0, max(ratios) - 1.0), 6),
            "source": "measured from the preview geometry"}


def preview_shape(root: Path, config_name: str, q: dict) -> dict:
    """On-demand 2D/3D preview geometry for one typology config (sandbox backend).

    GET ``/api/preview-shape/<config>?brief=<name>&detail=2d|3d&knobs=<urlencoded JSON>``.
    Dispatch branches on the params KIND FIRST (the spike's silent-OSSE hazard): a grid block
    never reaches ``build_preview_geometry``/``to_mesher_config``; a CAD recipe returns
    ``available:false`` before ``to_mesher_config`` (which raises a bare ``KeyError: 'cad'``).
    Nothing is written and nothing is meshed: geometry only.

    ``detail=2d`` keeps the ``shape3d`` block present but ``{"available": false, "reason":
    "detail=2d"}``, so the response shape never changes with the detail flag.
    """
    from hornlab_search.config import ConfigError, load_config, mesh_spec
    from hornlab_search.design import families
    from hornlab_search.design.generators import grid as grid_gen
    from hornlab_search.design.generators import registry
    from hornlab_search.mesh.build import res_mm_for_spec
    from hornlab_search.types import Design, GeometryInvalidError
    from . import preview as seam

    started = time.perf_counter()
    t_params = t_section = t_shape = 0.0

    entry = _preview_config(root, config_name)
    cfg_path = root / entry["path"]
    detail_raw = q.get("detail") or ["2d"]
    detail = str(detail_raw[0] if isinstance(detail_raw, (list, tuple)) else detail_raw).lower()
    if detail not in ("2d", "3d"):
        raise ValueError("detail must be '2d' or '3d'")
    brief_p = None
    brief_q = q.get("brief")
    if brief_q:
        brief_name_raw = brief_q[0] if isinstance(brief_q, (list, tuple)) else brief_q
        brief_p = _preview_brief_path(root, str(brief_name_raw))

    try:
        cfg = load_config(cfg_path, brief=brief_p)
    except ConfigError as exc:
        # e.g. a config that pins its throat radius under a brief with another driver size:
        # say so on the page instead of a server error that blanks the sandbox.
        reason = f"this config cannot load under this brief: {exc}"
        return _preview_response(
            config=config_name, brief=brief_p.stem if brief_p else None, kind="native",
            quadrants="1", available=False, knobs={},
            section={"h": {"inner": [], "outer": []}, "v": {"inner": [], "outer": []}},
            mouth={"inner": [], "outer": []}, envelope={"available": False, "reason": reason},
            shape3d={"available": False, "reason": reason}, slow=False,
            timings={"total": (time.perf_counter() - started) * 1000.0}, notes=[reason])
    brief_name = (cfg.brief or {}).get("name")
    quadrants = str(cfg.mesh.quadrants)

    raw_knobs = q.get("knobs")
    knob_text = raw_knobs[0] if isinstance(raw_knobs, (list, tuple)) else raw_knobs
    if knob_text in (None, ""):
        overrides = {}
    else:
        try:
            overrides = json.loads(str(knob_text))
        except json.JSONDecodeError as exc:
            raise ValueError(f"knobs must be a JSON object: {exc}") from None
        if not isinstance(overrides, dict):
            raise ValueError("knobs must be a JSON object")

    effective, notes = _preview_knobs(cfg, overrides)
    gen = cfg.generator if isinstance(cfg.generator, dict) else None
    is_grid = bool(gen and gen.get("name") == "grid")
    is_rows = bool(is_grid and isinstance(gen.get("rows"), dict))
    kind = "rows" if is_rows else ("grid" if is_grid else
                                   ("native" if not gen else "generator"))
    slow = bool(is_rows)

    def unavailable(reason: str, *, envelope: dict | None = None) -> dict:
        timings = {"params": t_params, "section": t_section, "shape3d": t_shape,
                   "total": (time.perf_counter() - started) * 1000.0}
        return _preview_response(
            config=config_name, brief=brief_name, kind=kind, quadrants=quadrants,
            available=False, knobs=effective,
            section={"h": {"inner": [], "outer": []}, "v": {"inner": [], "outer": []}},
            mouth={"inner": [], "outer": []},
            envelope=envelope or {"available": False, "reason": reason},
            shape3d={"available": False, "reason": reason},
            slow=slow, timings=timings, notes=notes + [reason])

    # (1b) cone mid horn + axe head (tools/cad/plughorn.py): the CAD tool's own sections and solid.
    if gen and gen.get("name") == "plughorn":
        return _plughorn_preview(cfg, effective, notes, detail, config_name, brief_name, quadrants,
                                 started, unavailable)

    # (1) CAD recipe: no on-demand preview in the mesher; stop BEFORE to_mesher_config.
    if "cad" in cfg.seed_params:
        return unavailable(PREVIEW_NOTES_CAD,
                           envelope={"available": False, "reason": PREVIEW_NOTES_CAD})

    mesh = mesh_spec("screen", cfg)
    res_mm = res_mm_for_spec(mesh, cfg)
    envelope: dict
    section: dict
    mouth: dict
    rejected: list[str] = []
    inner = outer = angles = None
    t_coords = phi_coords = None
    closed_phi = False

    try:
        if is_grid:
            # (2) GRID/ROWS: the config's own march arrays. NO grid block into the preview.
            gspec = gen
            wall_mm = float(gspec.get("wall_thickness_mm", 3.0))
            inner, meta = grid_gen.grid_points(gspec, effective, cfg.brief)
            half = bool(meta.get("half_model", False))
            half_xz = str(meta.get("row_span") or meta.get("span") or "") == "half_xz"
            closed_phi = ((not bool(meta.get("quarter", True))) and not half
                          and not half_xz)
            outer = grid_gen.grid_outer_points(inner, wall_mm, half=half,
                                               half_xz=half_xz, full=closed_phi, check=False)
            try:
                grid_gen.check_self_approach(inner, outer, wall_mm)
            except registry.GeneratorError as exc:
                rejected.append(str(exc))
            angles = _rows_angles(meta, int(inner.shape[0]))
            t_params = (time.perf_counter() - started) * 1000.0
            if is_rows:
                overshoot = _rows_overshoot_from_arrays(inner, meta, wall_mm, cfg.brief)
                envelope = {"available": True, "overshoot": round(float(overshoot), 6)}
            else:
                block = grid_gen.design_params(gspec, effective, cfg.brief)
                overshoot = registry.envelope_overshoot_estimate(block, cfg.brief)
                envelope = ({"available": False,
                             "reason": "envelope estimator returned None for this grid"}
                            if overshoot is None
                            else {"available": True, "overshoot": round(float(overshoot), 6)})
            if envelope.get("available") and float(envelope["overshoot"]) > 0.0:
                rejected.append(
                    "invalid_envelope: estimated outside the brief envelope "
                    f"(max relative overshoot {float(envelope['overshoot']):.4f})")
        else:
            # (3) GENERATOR vs (4) NATIVE: materialize the mesher config, then the viewport.
            if gen:
                params = registry.materialize(gen, effective, cfg.brief)
            else:
                params = copy.deepcopy(cfg.seed_params)
                for key, value in overrides.items():
                    if key not in effective:        # an unknown name was named in notes
                        continue
                    if key in cfg.seed_params:
                        families.param_set(cfg.family, params, key, value)
                    elif "." in key:
                        notes.append(f"knob {key!r} has no resolvable seed path; ignored")
                    else:
                        params[key] = value
                effective = params
            design = Design("FREEFORM" if gen else cfg.family, params)
            mcfg = families.to_mesher_config(
                design, mesh, res_mm, Path(os.environ.get("TEMP", ".")) / "hornlab-preview.msh")
            mcfg_coarse = copy.deepcopy(mcfg)
            mesh_sec = dict(mcfg_coarse.get("mesh") or {})
            mesh_sec["angular_segments"] = PREVIEW_ANGULAR_SEGMENTS
            mesh_sec["length_segments"] = PREVIEW_LENGTH_SEGMENTS
            mcfg_coarse["mesh"] = mesh_sec
            if gen:
                overshoot = registry.envelope_overshoot_estimate(params, cfg.brief)
                envelope = ({"available": False,
                             "reason": "envelope estimator returned None for these params"}
                            if overshoot is None
                            else {"available": True, "overshoot": round(float(overshoot), 6)})
            else:
                envelope = {"available": False, "reason": PREVIEW_NOTES_ENVELOPE_NATIVE}
            t_params = (time.perf_counter() - started) * 1000.0
            if envelope.get("available") and float(envelope["overshoot"]) > 0.0:
                rejected.append(
                    "invalid_envelope: estimated outside the brief envelope "
                    f"(max relative overshoot {float(envelope['overshoot']):.4f})")
            viewport = _build_viewport(mcfg_coarse)
            grid_data = viewport["grid"]
            inner = np.asarray(grid_data["inner_grid"], dtype=float)
            outer = (None if grid_data.get("outer_grid") is None
                     else np.asarray(grid_data["outer_grid"], dtype=float))
            closed_phi = bool(grid_data.get("full_circle", True))
            angles = grid_data.get("angle_list")
            t_coords = np.asarray(grid_data["slice_map"], dtype=float)
            phi_grid = grid_data.get("phi_grid")
            phi_coords = (np.asarray(phi_grid, dtype=float).T if phi_grid is not None
                          else np.broadcast_to(np.asarray(angles, dtype=float),
                                               inner.shape[1::-1]))
    except (registry.GeneratorError, GeometryInvalidError, ConfigError, _MesherConfigError) as exc:
        # the mesher's own config refusals (e.g. a guiding curve on a non-circular cross-section)
        # are explained on the page like ours, never a server error that blanks the sandbox
        t_params = t_params or (time.perf_counter() - started) * 1000.0
        return unavailable(str(exc))

    if angles is None:
        angles = _rows_angles({}, int(np.asarray(inner).shape[0]))
    dims = _preview_dims(inner, outer)
    if kind == "native":
        envelope = _measured_envelope(dims, cfg.brief)

    t0 = time.perf_counter()
    section, mouth = _sections(inner, outer, angles)
    t_section = (time.perf_counter() - t0) * 1000.0

    if detail == "3d":
        if outer is None:
            shape3d = {"available": False,
                       "reason": "no outer shell for this design (wall_thickness_mm=0?)"}
        else:
            t0 = time.perf_counter()
            try:
                soup = seam.tessellate(
                    inner, outer, t_coordinates=t_coords, phi_coordinates=phi_coords,
                    closed_phi=closed_phi)
            except ValueError as exc:
                t_shape = (time.perf_counter() - t0) * 1000.0
                shape3d = {"available": False, "reason": str(exc)}
            else:
                t_shape = (time.perf_counter() - t0) * 1000.0
                shape3d = {
                    "available": True,
                    "warnings": list(soup.get("warnings") or []),
                    "roles": list(soup["roles"]),
                    "verts": np.round(np.asarray(soup["positions"], dtype=float), 3).ravel().tolist(),
                    "tris": np.asarray(soup["indices"], dtype=np.int64).ravel().tolist(),
                }
    else:
        shape3d = {"available": False, "reason": "detail=2d"}

    timings = {"params": t_params, "section": t_section, "shape3d": t_shape,
               "total": (time.perf_counter() - started) * 1000.0}
    return _preview_response(
        config=config_name, brief=brief_name, kind=kind, quadrants=quadrants,
        available=True, knobs=effective, section=section, mouth=mouth,
        envelope=envelope, shape3d=shape3d, slow=slow, timings=timings, notes=notes,
        rejected=rejected, dims=dims, morph_capable=morph_capable(cfg.raw),
        gcurve_capable=gcurve_capable(cfg.raw))


def _tessellate_part(part, tol: float = 1.0, ang: float = 0.3):
    """(points, triangles, skipped_faces) for the 3D preview; never raises for a valid solid.

    ``build123d``'s ``Shape.tessellate`` walks every face and assumes each one comes back with a
    triangulation, so a SINGLE face without one kills the whole payload with
    ``AttributeError: 'NoneType' object has no attribute 'NbNodes'``. That happens on a valid,
    gmsh-meshable solid: ``cone_plughorn__morph_wide_8in`` has one planar boolean-remnant face
    (634 mm^2) that no deflection/sag tolerance triangulates, while the same STEP meshes fine.
    The preview is a visual, so tessellate face by face and report what could not be drawn
    instead of blanking the viewport.
    """
    try:
        verts, tris = part.tessellate(tol, ang)
        return [[p.X, p.Y, p.Z] for p in verts], [list(t) for t in tris], 0
    except Exception:  # noqa: BLE001 - fall through to the per-face path
        pass
    pts: list[list[float]] = []
    idx: list[list[int]] = []
    skipped, base = 0, 0
    for face in part.faces():
        try:
            fv, ft = face.tessellate(tol, ang)
        except Exception:  # noqa: BLE001 - one un-triangulable face is not a blank viewport
            skipped += 1
            continue
        pts.extend([[p.X, p.Y, p.Z] for p in fv])
        idx.extend([[base + int(i) for i in tri] for tri in ft])
        base += len(fv)
    return pts, idx, skipped


def _plughorn_preview(cfg, effective, notes, detail, config_name, brief_name, quadrants, started,
                      unavailable) -> dict:
    """Sandbox preview of a ``plughorn`` design: H/V wall sections and the front opening from the
    tool's own section geometry; 3D = the tessellated CAD solid (horn + axe head + bowl), mm.

    The 3D tessellation builds the full OCC solid (~1-3 s), so the payload is marked ``slow``."""
    from hornlab_search.design.generated import plughorn_params
    from hornlab_search.mesh import step_build
    t0 = time.perf_counter()
    try:
        cad = plughorn_params(cfg.generator, effective, None)["cad"]     # envelope is reported, not refused
        tool = step_build.load_cad_tool(tool=step_build.PLUGHORN_TOOL)
        p = tool.params_from_recipe(cad)
    except (ValueError, RuntimeError) as exc:
        return unavailable(str(exc))
    t_params = (time.perf_counter() - t0) * 1000.0
    L = p.L
    h_in, v_in = [], []
    for i in range(41):
        z = L * i / 40
        sec = p.horn_section(z)
        if sec is None or len(sec) < 3:
            continue
        sec = np.asarray(sec, dtype=float)
        h_in.append([round(float(z), 3), round(float(np.abs(sec[:, 0]).max()), 3)])
        v_in.append([round(float(z), 3), round(float(np.abs(sec[:, 1]).max()), 3)])
    section = {"h": {"inner": h_in, "outer": []}, "v": {"inner": v_in, "outer": []}}
    mouth = {"inner": [[round(x, 3), round(y, 3)] for x, y, _z in p.front_octagon()], "outer": []}
    d = p.derived()
    rejected = []
    env = (cfg.brief or {}).get("envelope") or {}
    for key, val in (("max_mouth_w_mm", d["outer_w_mm"]), ("max_mouth_h_mm", d["outer_h_mm"]),
                     ("max_depth_mm", d["depth_total_mm"])):
        if key in env and val > float(env[key]) + 0.5:
            rejected.append(f"invalid_envelope: outer {key[4:-3]} {val:.0f} mm > {env[key]} mm")
    envelope = {"available": True, "overshoot": 0.0 if not rejected else 1.0}
    notes = list(notes) + [f"{k}: {v}" for k, v in d.items() if k in (
        "compression_ratio", "min_channel_area_cm2", "side_wall_angle_deg", "top_wall_angle_deg",
        "plug_clearance_mm", "rear_chamber_gross_l")]
    t_section = (time.perf_counter() - t0) * 1000.0 - t_params
    t_shape = 0.0
    if detail == "3d":
        t1 = time.perf_counter()
        try:
            part = tool.build_body(p)
            pts, idx, skipped = _tessellate_part(part)
            if not idx:
                raise RuntimeError("the solid tessellated to no triangles")
            warn = ([f"{skipped} face(s) could not be triangulated (degenerate boolean remnant) "
                     f"and are not drawn; the solid itself is valid and meshes"]
                    if skipped else [])
            shape3d = {"available": True, "warnings": warn, "roles": ["horn.inner"],
                       "verts": np.round(np.asarray(pts, dtype=float), 3).ravel().tolist(),
                       "tris": np.asarray(idx, dtype=np.int64).ravel().tolist()}
        except Exception as exc:  # noqa: BLE001 - a CAD failure is explained, never a server error
            shape3d = {"available": False, "reason": f"CAD build failed: {exc}"}
        t_shape = (time.perf_counter() - t1) * 1000.0
    else:
        shape3d = {"available": False, "reason": "detail=2d"}
    dims = {"w": d["outer_w_mm"], "h": d["outer_h_mm"], "d": d["depth_total_mm"]}
    timings = {"params": t_params, "section": t_section, "shape3d": t_shape,
               "total": (time.perf_counter() - started) * 1000.0}
    return _preview_response(
        config=config_name, brief=brief_name, kind="plughorn", quadrants=quadrants, available=True,
        knobs=effective, section=section, mouth=mouth, envelope=envelope, shape3d=shape3d, slow=True,
        timings=timings, notes=notes, rejected=rejected, dims=dims)


# ---------------------------------------------------------------------------- bounds writer


def _fmt_bound(v: float) -> str:
    return repr(float(v))


def _append_block_lines(text: str, block: str, new_lines: list[str]) -> str:
    """Append ``new_lines`` as entries at the END of the top-level ``block:`` mapping, at its own
    indentation (comment-preserving; nothing else moves). A missing block is created at the end."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines)
                  if re.match(rf"^{re.escape(block)}\s*:\s*(#.*)?(\r?\n)?$", ln)), None)
    if start is None:
        body = "".join(f"  {ln}{nl}" for ln in new_lines)
        sep = "" if text.endswith(("\n", "\r\n")) or not text else nl
        return text + sep + f"{block}:{nl}" + body
    indent, last = 2, start
    for j in range(start + 1, len(lines)):
        st = lines[j].strip()
        if not st or st.startswith("#"):
            continue
        if not lines[j][:1].isspace():
            break
        if last == start:
            indent = len(lines[j]) - len(lines[j].lstrip())
        last = j
    if not lines[last].endswith(("\n", "\r\n")):
        lines[last] += nl
    ins = [" " * indent + ln + nl for ln in new_lines]
    return "".join(lines[:last + 1] + ins + lines[last + 1:])


def _patch_bounds_lines(text: str, updates: dict) -> tuple[str, set[str]]:
    """Comment-preserving, indentation-aware patch of ONLY the ``lo:``/``hi:`` lines.

    No YAML round trip (ruamel is not installed): the rest of the file stays byte-identical.
    Handles both block mappings (``lo: 1.0``) and a flow mapping (``{lo: 1.0, hi: 2.0}``) in a
    bounds block, because only the value token changes either way.
    """
    lines = text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^bounds\s*:\s*(#.*)?(\r?\n)?$", line):
            start = i
            break
    if start is None:
        return text, set()

    key_indent = None
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            break
        key_indent = len(line) - len(line.lstrip())
        break
    if key_indent is None:
        return text, set()

    patched: set[str] = set()
    key_line = re.compile(
        r"^(?P<indent>\s*)(?P<q>['\"]?)(?P<key>[^:'\"]+)(?P=q)\s*:(?P<rest>.*)$")
    leaf = re.compile(r"^(?P<lead>\s*)(?P<kind>lo|hi)\s*:\s*(?P<val>[^\s#]+)(?P<trail>.*)$")

    i = start + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                break
            if indent < key_indent:
                break
        if not stripped or stripped.startswith("#") or (len(line) - len(line.lstrip())) != key_indent:
            i += 1
            continue
        m = key_line.match(line)
        if not m:
            i += 1
            continue
        key = m.group("key")
        if key not in updates:
            i += 1
            continue
        lo, hi = updates[key]
        rest = m.group("rest")
        if "{" in rest:
            new_rest = re.sub(r"(lo\s*:\s*)([^,}\s]+)", lambda mm: mm.group(1) + _fmt_bound(lo),
                              rest, count=1)
            new_rest = re.sub(r"(hi\s*:\s*)([^,}\s]+)", lambda mm: mm.group(1) + _fmt_bound(hi),
                              new_rest, count=1)
            if new_rest != rest:
                lines[i] = line[:m.start("rest")] + new_rest
                patched.add(key)
            i += 1
            continue
        found = set()
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            nxt_stripped = nxt.strip()
            nxt_indent = len(nxt) - len(nxt.lstrip())
            if nxt_stripped and not nxt_stripped.startswith("#") and nxt_indent <= key_indent:
                break
            lm = leaf.match(nxt)
            if lm and lm.group("kind") not in found:
                value = lo if lm.group("kind") == "lo" else hi
                lines[j] = (nxt[:lm.start("val")] + _fmt_bound(value) + nxt[lm.end("val"):])
                found.add(lm.group("kind"))
            j += 1
        if found == {"lo", "hi"}:
            patched.add(key)
        i = j
    return "".join(lines), patched


def save_bounds(root: Path, body: dict) -> dict:
    """Write edited search bounds back to their YAML home (owner ruling 2026-10-25).

    Resolves the config through ``list_configs``; only ``examples/typologies/**`` is writable in
    this pass (root-level ``examples/*.yaml`` is reported, never written). Every key is validated
    as a whole (all-or-nothing): unknown key, non-finite value, lo > hi, or a value outside the
    parameter catalog's hard schema limit rejects the entire request and writes nothing.
    """
    from hornlab_search.design.params import bounds_for

    if not isinstance(body, dict):
        raise ValueError("JSON object expected")
    name = body.get("config")
    updates = body.get("bounds")
    if not isinstance(name, str) or not name:
        raise ValueError("body needs a non-empty 'config' name")
    adds = body.get("add") or {}
    if updates is None:
        updates = {}
    if not isinstance(updates, dict) or not isinstance(adds, dict) or not (updates or adds):
        raise ValueError("body needs a non-empty 'bounds' or 'add' object")
    entry = _preview_config(root, name)
    rel = entry["path"]
    path = (root / rel).resolve()
    typologies = (root / "examples" / "typologies").resolve()
    notes = [
        "config_sha changes for this config; resume needs --allow-config-change",
        "a RUNNING search using this config keeps its own snapshot (run config.yaml); "
        "bounds edits apply to the next launch",
    ]
    if typologies not in path.parents:
        return {"ok": False, "applied": [],
                "rejected": [{"key": "-",
                              "reason": f"config_not_writable: {rel} is not under "
                                        "examples/typologies/; nothing written"}]}

    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text) or {}
    known = doc.get("bounds") if isinstance(doc.get("bounds"), dict) else {}

    rejected: list[dict] = []
    accepted: dict[str, tuple[float, float]] = {}
    applied: list[dict] = []
    for raw_key, raw_value in updates.items():
        key = str(raw_key)
        if key not in known:
            rejected.append({"key": key, "reason": "unknown_key"})
            continue
        if not isinstance(raw_value, dict) or "lo" not in raw_value or "hi" not in raw_value:
            rejected.append({"key": key, "reason": "missing_lo_hi"})
            continue
        lo_raw, hi_raw = raw_value.get("lo"), raw_value.get("hi")
        if isinstance(lo_raw, bool) or isinstance(hi_raw, bool):
            rejected.append({"key": key, "reason": "not_a_finite_number"})
            continue
        try:
            lo, hi = float(lo_raw), float(hi_raw)
        except (TypeError, ValueError):
            rejected.append({"key": key, "reason": "not_a_finite_number"})
            continue
        if not (math.isfinite(lo) and math.isfinite(hi)):
            rejected.append({"key": key, "reason": "not_a_finite_number"})
            continue
        if lo > hi:
            rejected.append({"key": key, "reason": "lo_above_hi"})
            continue
        hard = {}
        try:
            hard = (bounds_for(name, key) or {}).get("hard") or {}
        except Exception:  # noqa: BLE001 - the catalog is advisory here, never a crash
            hard = {}
        hard_lo = hard.get("lo") if isinstance(hard, dict) else None
        hard_hi = hard.get("hi") if isinstance(hard, dict) else None
        if (hard_lo is not None and lo < float(hard_lo)) or \
                (hard_hi is not None and hi > float(hard_hi)):
            lo_s = "-inf" if hard_lo is None else f"{float(hard_lo):g}"
            hi_s = "inf" if hard_hi is None else f"{float(hard_hi):g}"
            rejected.append({"key": key, "reason": f"exceeds_hard_limit {lo_s}..{hi_s}"})
            continue
        if hard_lo is None and hard_hi is None:
            notes.append(f"no hard schema limit known for {key!r}; "
                         "the config schema validates at build time")
        accepted[key] = (lo, hi)
        old = known[key] if isinstance(known[key], dict) else {}
        applied.append({"key": key,
                        "from": {"lo": old.get("lo"), "hi": old.get("hi")},
                        "to": {"lo": lo, "hi": hi}})

    added_bounds: list[str] = []
    added_seeds: list[str] = []
    if adds:
        from hornlab_search.config import ConfigError, load_config
        try:
            legal = _preview_extra_keys(load_config(path))
        except ConfigError as exc:
            legal = set()
            notes.append(f"config does not load on its own: {exc}")
        seeds = doc.get("seed_params") if isinstance(doc.get("seed_params"), dict) else {}
        for raw_key, raw_value in adds.items():
            key = str(raw_key)
            if key in known:
                rejected.append({"key": key, "reason": "already_a_bound_row (edit it instead)"})
                continue
            if key not in legal:
                rejected.append({"key": key, "reason": "not_a_legal_key_for_this_typology"})
                continue
            v = raw_value if isinstance(raw_value, dict) else {}
            try:
                lo, hi = float(v.get("lo")), float(v.get("hi"))
                seed = float(v.get("seed", (lo + hi) / 2.0))
            except (TypeError, ValueError):
                rejected.append({"key": key, "reason": "not_a_finite_number"})
                continue
            if not all(math.isfinite(x) for x in (lo, hi, seed)) or lo > hi or not lo <= seed <= hi:
                rejected.append({"key": key, "reason": "need finite lo <= seed <= hi"})
                continue
            is_int = key in ("morph_target", "morph_allow_shrinkage")
            fmt_v = (lambda x: str(int(round(x)))) if is_int else (lambda x: repr(round(x, 6)))
            pinned = bool(v.get("pinned")) or lo == hi
            added_bounds.append(f"{key}: {{lo: {fmt_v(lo)}, hi: {fmt_v(hi)}"
                                + (", search: false}" if pinned else "}"))
            if key not in seeds:
                added_seeds.append(f"{key}: {fmt_v(seed)}")
            applied.append({"key": key, "from": None,
                            "to": {"lo": lo, "hi": hi, "seed": seed, "pinned": pinned}})

    if rejected:
        return {"ok": False, "rejected": rejected, "applied": [], "notes": notes}

    new_text, patched = _patch_bounds_lines(text, accepted)
    if added_bounds:
        new_text = _append_block_lines(new_text, "bounds", added_bounds)
    if added_seeds:
        new_text = _append_block_lines(new_text, "seed_params", added_seeds)
    if adds:
        # the whole config must still load (family keys, generator rules, the brief) before a
        # single byte is written
        from hornlab_search.config import ConfigError, load_config
        probe = path.with_name("." + path.stem + ".probe.yaml")
        try:
            probe.write_text(new_text, encoding="utf-8")
            load_config(probe)
        except ConfigError as exc:
            return {"ok": False, "applied": [],
                    "rejected": [{"key": k, "reason": f"config would not load: {exc}"}
                                 for k in adds],
                    "notes": notes}
        finally:
            if probe.exists():
                probe.unlink()
        notes.append("added rows: regenerate the parameter catalog "
                     "(tools/gen_param_catalog.py --write) so every page lists them")
    missing = sorted(set(accepted) - patched)
    if missing:
        return {"ok": False, "applied": [],
                "rejected": [{"key": key,
                              "reason": "bounds lines could not be located in the YAML"} for key in missing],
                "notes": notes}
    try:
        check = (yaml.safe_load(new_text) or {}).get("bounds") or {}
        for key, (lo, hi) in accepted.items():
            if float(check[key]["lo"]) != lo or float(check[key]["hi"]) != hi:
                raise ValueError(key)
    except Exception:  # noqa: BLE001 - never leave a half-valid file behind
        return {"ok": False, "applied": [],
                "rejected": [{"key": key, "reason": "patched text did not re-parse"}
                             for key in sorted(accepted)],
                "notes": notes}

    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return {"ok": True, "file": rel, "applied": applied, "notes": notes}
