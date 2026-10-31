"""GUI integration phases G1-G4 (reader/route layer): the frozen contracts from
``docs/GUI_INTEGRATION_PLAN_2026-10-25.md`` §5, exercised offline (no browser, no GPU, no CLI jobs).

  C-1  ``GET /api/run/<id>`` additive ``restarts``/``qd``/``restart_dirs`` + ``step_files`` inventory.
  C-2  ``GET /api/compare`` additive ``group_a``/``group_b``/``mixed_keys`` (solve-group fingerprint).
  C-5  ``GET /runs/<id>/cma[/restart_k]/<name>`` raw pycma log serving by strict name allow-list.
  G-1  jobs ``verify`` kind (argv shape, bounds, GPU lock inheritance).

Fixture conventions mirror ``tests/test_gui.py``: synthetic run dirs under ``tmp_path`` and a real
``ThreadingHTTPServer`` bound to 127.0.0.1:0; the app.js ES-module ``node --check`` gate is copied so
the view lane's syntax stays gated.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import numpy as np
import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui import jobs as J
from hornlab_search.gui.server import App, make_handler

ROOT = Path(__file__).resolve().parents[1]

RUN_A = "20261025T000000Z-screen-aaa111"       # restarts/qd/restart dirs/STEP sidecar
RUN_B = "20261025T000001Z-screen-bbb222"       # plain run (no WP11 keys, no sidecar)
RUN_C = "20261025T000002Z-screen-ccc333"       # identical to B except mesh.rear_res_factor
RUN_D = "20261025T000003Z-screen-ddd444"       # identical to B (empty mixed_keys)
STOP_RID = "20261025T000004Z-screen-eee555"    # run.json carries a stop_reason

HASH = "aaaaaaaaaaaa"
STEP = "fake_rank1_aaaaaaaaaaaa.step"
F = [500.0, 1000.0, 2000.0, 4000.0, 5500.0]

RESTARTS = [{"index": 0, "popsize": 8, "sigma0": 0.25, "n_new_in_restart": 5,
             "evals_in_restart": 5, "stop": "small_run"}]
QD = {"algorithm": "cma_me", "descriptors": {"h": "mean_bw_h_deg", "v": "mean_bw_v_deg"},
      "bins": [4, 3], "coverage": {"occupied": 1, "total": 12}}
INVENTORY = {"tool": "tools/cad/multicell.py", "tool_sha": "deadbeef",
             "faces": [{"label": "driver", "count": 1}, {"label": "wall", "count": 4}],
             "solids": 1, "closed": True, "grid": ["3x3"]}
# The REAL ``mesh_meta.json["cad"]`` block as ``mesh/step_build.py`` writes it on the current tree:
# ``face_inventory`` is a label->count mapping, the tool hash key is ``tool_sha256``, and the solid
# summary is the CAD tool's own dict under ``solid`` (solids/all_shells_closed live there).
CAD_BLOCK = {
    "tool": "tools/cad/multicell.py",
    "tool_path": "C:/repo/tools/cad/multicell.py",
    "tool_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "recipe": {"tool": "multicell", "n_h": 3, "n_v": 3, "alpha_total_deg": 90.0,
               "beta_total_deg": 90.0, "length_mm": 120.0, "z_s_mm": 30.0,
               "r_throat_mm": 12.7, "septum_mm": 2.0, "throat_wall_mm": 3.0, "flare_hz": 0.0},
    "derived": {"throat_w_mm": 12.7, "throat_h_mm": 12.7},
    "solid": {"faces": 25, "solids": 1, "volume_mm3": 123456.0, "valid": True,
              "all_shells_closed": True, "degenerate_faces": 0, "driver_faces": 1,
              "min_face_area_mm2": 1.25},
    "step_path": "C:/repo/runs/RUN/designs/aaaaaaaaaaaa/cad/multicell.step",
    "step_sha256": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
    "step_bytes": 98765,
    "face_inventory": {"driver": 1, "wall": 24},
    "gmsh_surfaces": 25,
    "driver_surfaces": 1,
    "wall_surfaces": 24,
    "physical_tags": {"1": "SD1G0", "2": "SD1D1001"},
    "frequency_validation": {"status": "valid", "per_source": {"driver": {}}},
    "repair": {"ok": True},
    "topology": {"ok": True},
}

# --- 3D evolution time-lapse fixtures (separate run ids from the C-1/G-1 ones) ---------------
EVO_RID = "20261026T000000Z-screen-aaa111"
EVO_SKIP_RID = "20261026T000001Z-screen-bbb222"
EVO_NOMESH_RID = "20261026T000002Z-screen-ccc333"
EVO_NOROWS_RID = "20261026T000003Z-screen-ddd444"
EVO_Q_META_RID = "20261026T000004Z-screen-eee555"
EVO_Q_ROW_RID = "20261026T000005Z-screen-fff666"
EVO_Q_CFG_RID = "20261026T000006Z-screen-aaa777"
EVO_Q_NONE_RID = "20261026T000007Z-screen-bbb888"
H0, H1, H2 = "111111111111", "222222222222", "333333333333"


def _cfg(mesh_extra: dict | None = None, solve_extra: dict | None = None,
         search_extra: dict | None = None) -> dict:
    cfg = {
        "name": "fake", "family": "FREEFORM",
        "mesh": {"epw": 8.0, "quadrants": "1", "dof_cap_screen": 5000, "dof_cap_verify": 7000,
                 "dof_cap_final": 8900, "dof_per_triangle": 0.51, "max_triangle_slack": 1.15},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73, "balloon": True,
                  "balloon_points_screen": 512, "balloon_points_verify": 1024,
                  "gmres_tol": 1e-5, "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 60,
                   "popsize": None, "tolfun": 1e-3},
        "target": {"band_lo_hz": 300, "band_hi_hz": 12000, "coverage_h_deg": 90,
                   "coverage_v_deg": 60, "di_target_db": None, "di_slope_target": 0, "z_min": 0},
        "weights": {"cov": 1.0},
    }
    cfg["mesh"].update(mesh_extra or {})
    cfg["solve"].update(solve_extra or {})
    cfg["search"].update(search_extra or {})
    return cfg


def _metrics(shift: float = 0.0) -> dict:
    n = len(F)
    return {"freqs_hz": F, "bw_h_deg": [90.0 + shift] * n, "bw_v_deg": [60.0] * n,
            "di_db": [9.0] * n, "di_source": "balloon",
            "on_axis_db": [1.0, 2.0, 3.0, 2.0, 1.5], "ripple_h_db": [0.5] * n,
            "ripple_v_db": [0.4] * n, "z_throat_real": [0.5] * n, "scalars": {}}


def _write_run(runs: Path, rid: str, *, mesh_extra: dict | None = None,
               solve_extra: dict | None = None, search_extra: dict | None = None,
               run_json_extra: dict | None = None, restart_dirs: tuple[str, ...] = (),
               inventory: dict | None = None, with_step: bool = True) -> Path:
    run = runs / rid
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(
        yaml.safe_dump(_cfg(mesh_extra, solve_extra, search_extra)))
    design = run / "designs" / HASH
    design.mkdir(parents=True)
    (design / "metrics.json").write_text(json.dumps(_metrics()))
    row = {"n": 0, "design_hash": HASH, "ok": True, "objective": 9.0, "mode": "screen",
           "family": "FREEFORM", "error": None, "metrics": _metrics()}
    (run / "search.ndjson").write_text(json.dumps(row) + "\n")
    run_json = {"backend": "beat_cuda", "mode": "screen"}
    run_json.update(run_json_extra or {})
    (run / "run.json").write_text(json.dumps(run_json))
    for name in restart_dirs:
        (run / "cma" / name).mkdir(parents=True)
        (run / "cma" / name / "fit.dat").write_text("1 2 3\n")
    if with_step:
        step = run / "step"
        step.mkdir()
        (step / STEP).write_text("ISO-10303-21;")
        if inventory is not None:
            (step / (Path(STEP).stem + ".inventory.json")).write_text(json.dumps(inventory))
    return run


def _write_mesh_meta(run: Path, h: str, meta: dict) -> None:
    """Write one design's mesh_meta.json (the cad-route fallback source)."""
    dd = run / "designs" / h
    dd.mkdir(parents=True, exist_ok=True)
    (dd / "mesh_meta.json").write_text(json.dumps(meta))


def _write_rows(run: Path, rows: list[dict]) -> None:
    """Replace search.ndjson with an ordered row list (provenance proxy tests)."""
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _row(n: int, h: str, j: float | None, *, ok: bool = True) -> dict:
    return {"n": n, "design_hash": h, "ok": ok, "objective": j if ok else None,
            "mode": "screen", "family": "FREEFORM", "error": None if ok else "solve_failed: x"}


def _mesh_text(extra_node: bool = False, grid: int = 0) -> str:
    """Tiny gmsh 2.2 ASCII: 3 triangles (4 nodes, or 5 with an unused extra node), or — when
    ``grid`` is set — a flat ``grid``x``grid`` square of 2*(grid-1)**2 triangles."""
    if grid:
        nodes = [f"{i * grid + j + 1} {i / (grid - 1) * 0.1:.6f} {j / (grid - 1) * 0.1:.6f} 0.0"
                 for i in range(grid) for j in range(grid)]
        elems = []
        for i in range(grid - 1):
            for j in range(grid - 1):
                a = i * grid + j + 1
                b, c, d = a + 1, a + grid, a + grid + 1
                elems.append(f"{len(elems) + 1} 2 2 1 1 {a} {b} {d}")
                elems.append(f"{len(elems) + 1} 2 2 1 1 {a} {d} {c}")
        return ("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n" + str(len(nodes)) + "\n"
                + "\n".join(nodes) + "\n$EndNodes\n$Elements\n" + str(len(elems)) + "\n"
                + "\n".join(elems) + "\n$EndElements\n")
    nodes = ["1 0 0 0", "2 0.1 0 0", "3 0 0.1 0", "4 0.1 0.1 0"]
    if extra_node:
        nodes.append("5 0 0 0.1")
    return ("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n" + str(len(nodes)) + "\n"
            + "\n".join(nodes) + "\n$EndNodes\n$Elements\n3\n"
            "1 2 2 1 1 1 2 3\n2 2 2 1 1 2 3 4\n3 2 2 1 1 1 3 4\n$EndElements\n")


def _evo_row(n: int, h: str, j: float | None, *, ok: bool = True,
             quadrants: str | None = None) -> dict:
    row = {"n": n, "design_hash": h, "ok": ok, "objective": j if ok else None,
           "mode": "screen", "family": "FREEFORM", "error": None if ok else "invalid_geometry: x"}
    if quadrants:
        row["quadrants"] = quadrants
    return row


def _evo_run(runs: Path, rid: str, rows: list[dict], *,
             cfg_quadrants: str | None = "1") -> Path:
    run = runs / rid
    run.mkdir(parents=True)
    cfg = _cfg()
    if cfg_quadrants is None:
        cfg["mesh"].pop("quadrants", None)
    else:
        cfg["mesh"]["quadrants"] = cfg_quadrants
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return run


def _evo_design(run: Path, h: str, *, mesh: bool = True, quadrants_meta: str | None = None,
                extra_node: bool = False, grid: int = 0) -> Path:
    dd = run / "designs" / h
    dd.mkdir(parents=True, exist_ok=True)
    if mesh:
        (dd / "mesh.msh").write_text(_mesh_text(extra_node, grid))
    if quadrants_meta is not None:
        (dd / "mesh_meta.json").write_text(json.dumps({"result": {"quadrants": quadrants_meta}}))
    return dd


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    _write_run(runs, RUN_A, run_json_extra={"restarts": RESTARTS, "qd": QD},
               restart_dirs=("restart_0",), inventory=INVENTORY,
               mesh_extra={"rear_res_factor": 2.0},
               solve_extra={"cuda_fused": True, "near_correction": True,
                            "near_correction_cutoff": 500.0, "near_correction_order": 6,
                            "solve_precision": "double"},
               search_extra={"restarts": {"mode": "ipop", "max": 3}})
    _write_run(runs, RUN_B)
    _write_run(runs, RUN_C, mesh_extra={"rear_res_factor": 2.0})
    _write_run(runs, RUN_D)
    examples = root / "examples"
    (examples / "briefs").mkdir(parents=True)
    shutil.copy(ROOT / "examples" / "briefs" / "axi_90x90_1in.yaml", examples / "briefs")
    (examples / "cfg.yaml").write_text("name: x\n")
    return root


# ------------------------------------------------------------------ C-1 run_detail


def test_run_detail_carries_wp11_provenance_and_step_inventory(repo):
    d = D.run_detail(repo / "runs", RUN_A)
    assert d["restarts"] == RESTARTS                       # the array as written, verbatim
    assert d["qd"] == QD
    assert d["restart_dirs"] == ["cma/restart_0"]          # run-relative directory names, sorted
    assert d["step_files"] == [STEP]                       # legacy name list stays byte-identical
    [step] = d["step_files_detail"]
    assert step["name"] == STEP and step["inventory"] == INVENTORY
    # WP11a schedule read from config.yaml (the run.json restart rows stay a separate key).
    assert d["search_restarts"] == {"mode": "ipop", "max": 3}
    # G1 badge strip: the compare fingerprint is on every run detail; this run's non-defaults show.
    g = d["solve_group"]
    assert g["backend"] == "beat_cuda" and "freqs_hz" in g
    assert g["rear_res_factor"] == 2.0 and g["cuda_fused"] is True
    assert g["near_correction"] is True and g["near_correction_cutoff"] == 500.0
    assert g["near_correction_order"] == 6 and g["solve_precision"] == "double"
    json.dumps(d, allow_nan=False)                         # honesty: JSON-safe end to end


def test_run_detail_omits_absent_provenance_and_null_inventory(repo):
    d = D.run_detail(repo / "runs", RUN_B)
    assert "restarts" not in d and "qd" not in d           # absent in run.json -> absent here
    assert d["restart_dirs"] == []                         # no cma/restart_* dirs
    assert d["step_files"] == [STEP]
    [step] = d["step_files_detail"]
    assert step["name"] == STEP and step["inventory"] is None   # no sidecar -> null, never invented
    assert "search_restarts" not in d                      # no search.restarts block -> absent
    # solve_group is always present, but carries no non-default keys for this plain run.
    assert set(d["solve_group"]) == {"backend", "freqs_hz"}
    assert d["solve_group"]["backend"] == "beat_cuda"
    json.dumps(d, allow_nan=False)


def test_run_detail_never_fabricates_a_malformed_search_restarts_block(repo):
    run = repo / "runs" / RUN_B
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    cfg["search"]["restarts"] = {"mode": "ipop"}           # missing `max`: invalid -> absent
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))
    assert "search_restarts" not in D.run_detail(repo / "runs", RUN_B)


def test_run_detail_passes_stop_reason_through(repo):
    """A run.json stop_reason is passed through verbatim for the continue-run card's honest note.
    run.json["mode"] (LAST invocation) is preferred over summary.mode (rows[0], original mode), so a
    verify/final resume is never silently continued at the CLI's screen default."""
    _write_run(repo / "runs", STOP_RID, run_json_extra={"stop_reason": "budget", "mode": "verify"})
    d = D.run_detail(repo / "runs", STOP_RID)
    assert d["stop_reason"] == "budget" and d["mode"] == "verify"
    assert d["summary"]["mode"] == "screen"          # rows[0] keeps the original mode


def test_run_detail_omits_absent_stop_reason(repo):
    """No stop_reason in run.json -> the key is absent here too (no shape invention)."""
    d = D.run_detail(repo / "runs", RUN_B)
    assert "stop_reason" not in d


def test_run_detail_route_serves_the_additive_keys(server):
    code, body = _req(server + f"/api/run/{RUN_A}")
    assert code == 200 and body["restarts"] == RESTARTS and body["qd"] == QD
    assert body["restart_dirs"] == ["cma/restart_0"]
    assert body["step_files_detail"][0]["inventory"] == INVENTORY
    assert body["search_restarts"] == {"mode": "ipop", "max": 3}
    assert body["solve_group"]["rear_res_factor"] == 2.0 and body["solve_group"]["backend"] == "beat_cuda"
    code, body = _req(server + f"/api/run/{RUN_B}")
    assert "restarts" not in body and "qd" not in body and body["restart_dirs"] == []
    assert body["step_files_detail"][0]["inventory"] is None
    assert "search_restarts" not in body and body["solve_group"]["backend"] == "beat_cuda"


# ------------------------------------------------------------------ C-5 raw pycma logs


def _get_raw(url):
    with urllib.request.urlopen(url, timeout=20) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def test_cma_log_route_serves_pycma_logs_by_strict_name(server, repo):
    run = repo / "runs" / RUN_A
    (run / "cma").mkdir(exist_ok=True)
    (run / "cma" / "version.txt").write_bytes(b"3.3.0\n")
    (run / "cma" / "x0.q").write_text("q\n")
    (run / "cma" / "restart_0").mkdir(exist_ok=True)
    (run / "cma" / "restart_0" / "parameters.json2").write_text('{"a": 1}')

    status, body, headers = _get_raw(server + f"/runs/{RUN_A}/cma/restart_0/parameters.json2")
    assert status == 200 and body == b'{"a": 1}'
    assert headers["Content-Type"].startswith("text/plain") and headers["Cache-Control"] == "no-store"
    assert "attachment" in headers["Content-Disposition"]
    assert _get_raw(server + f"/runs/{RUN_A}/cma/version.txt")[:2] == (200, b"3.3.0\n")
    assert _get_raw(server + f"/runs/{RUN_A}/cma/x0.q")[0] == 200     # .q is in the whitelist


def test_cma_log_route_refuses_missing_executables_and_traversal(server, repo):
    run = repo / "runs" / RUN_A
    (run / "cma").mkdir(exist_ok=True)
    (run / "cma" / "evil.exe").write_bytes(b"MZ")
    (run / "cma" / "evil.py").write_text("print(1)")
    assert _req(server + f"/runs/{RUN_A}/cma/nope.dat")[0] == 404
    assert _req(server + f"/runs/{RUN_A}/cma/evil.exe")[0] == 404  # exists, but not whitelisted
    assert _req(server + f"/runs/{RUN_A}/cma/evil.py")[0] == 404
    assert _req(server + f"/runs/{RUN_A}/cma/..%2F..%2Fconfig.yaml")[0] in (400, 404)
    assert _req(server + f"/runs/{RUN_A}/cma/restart_0/..%2F..%2Frun.json")[0] in (400, 404)


# ------------------------------------------------------------------ C-2 solve-group fingerprint


def test_compare_groups_flag_exactly_the_differing_mesh_key(server, repo):
    runs = repo / "runs"
    ga, gb, mixed = D.solve_group_fingerprints(runs / RUN_B, runs / RUN_C)
    assert mixed == ["rear_res_factor"]
    assert ga["backend"] == gb["backend"] == "beat_cuda"        # identity key, always present
    assert "rear_res_factor" not in ga and gb["rear_res_factor"] == 2.0
    # every other key is identical (backend + the solved-grid identity are the identity keys)
    assert set(ga) - {"backend", "freqs_hz"} == set()
    assert set(gb) - {"backend", "freqs_hz"} == {"rear_res_factor"}

    code, body = _req(server + f"/api/compare?a={RUN_B}&b={RUN_C}")
    assert code == 200
    assert body["mixed_keys"] == ["rear_res_factor"]
    assert body["group_a"] == ga and body["group_b"] == gb
    assert "rows" in body and "a" in body and "b" in body       # existing response keys intact


def test_compare_groups_are_empty_when_the_configs_match(server, repo):
    runs = repo / "runs"
    assert D.solve_group_fingerprints(runs / RUN_B, runs / RUN_D)[2] == []
    code, body = _req(server + f"/api/compare?a={RUN_B}&b={RUN_D}")
    assert code == 200 and body["mixed_keys"] == []
    assert body["group_a"] == body["group_b"]
    assert body["group_a"]["backend"] == "beat_cuda"


def test_solve_group_fingerprint_reads_the_wip_solve_mesh_and_objective_keys(repo):
    run = repo / "runs" / RUN_B
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    cfg["mesh"]["rear_res_factor"] = 1.5
    cfg["mesh"]["band_split"] = {"edges_hz": [2000.0, 4000.0]}
    cfg["solve"].update({"near_correction": True, "near_correction_cutoff": 500.0,
                         "near_correction_order": 6, "solve_precision": "double"})
    cfg["objective"] = {"version": 2}
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))

    g = D._solve_group_fingerprint(run)
    assert g["backend"] == "beat_cuda"
    assert g["rear_res_factor"] == 1.5
    assert g["mesh_policy"] == "band_split_v1" and g["band_edges_hz"] == [2000.0, 4000.0]
    assert g["near_correction"] is True and g["near_correction_cutoff"] == 500.0
    assert g["near_correction_order"] == 6 and g["solve_precision"] == "double"
    assert g["objective_version"] == 2
    assert "cuda_fused" not in g and "source_motion" not in g   # defaults stay absent
    json.dumps(g, allow_nan=False)


# ------------------------------------------------------------------ G-1 verify job kind


def test_verify_kind_argv_bounds_and_brief(repo):
    jm = J.JobManager(repo, repo / "runs")
    assert "verify" in J.GPU_KINDS
    argv, gpu = jm.build_argv("verify", {"run": RUN_B, "top": 12})
    assert gpu is True
    assert argv == ["verify", "--run", str((repo / "runs").resolve() / RUN_B), "--top", "12"]
    argv, gpu = jm.build_argv("verify", {"run": RUN_B, "top": 5,
                                         "brief": "examples/briefs/axi_90x90_1in.yaml"})
    assert gpu is True and argv[-2:] == ["--brief", "examples/briefs/axi_90x90_1in.yaml"]
    assert argv[:4] == ["verify", "--run", str((repo / "runs").resolve() / RUN_B), "--top"]
    for bad in ({"run": RUN_B, "top": 0}, {"run": RUN_B, "top": 26}, {"run": RUN_B, "top": "x"},
                {"run": "not-a-run", "top": 3},
                {"run": RUN_B, "top": 3, "brief": "../outside.yaml"},
                {"run": RUN_B, "top": 3, "brief": "examples/nope.yaml"}):
        with pytest.raises(J.JobError):
            jm.build_argv("verify", bad)


def test_verify_preview_marks_it_gpu(server):
    code, body = _req(server + "/api/preview", data=json.dumps(
        {"kind": "verify", "args": {"run": RUN_B, "top": 5}}).encode())
    assert code == 200 and body["gpu"] is True and body["gpu_busy"] is None
    assert body["command"].startswith("hornlab-search verify --run ")


def test_verify_is_refused_while_the_gpu_lock_is_held(repo):
    from hornlab_search.search.gpulock import _lock_path
    lk = _lock_path(repo / "runs")
    lk.parent.mkdir(parents=True, exist_ok=True)
    lk.write_text(json.dumps({"pid": os.getpid(), "user": "u", "command": "search x",
                              "start_time": "t"}))
    jm = J.JobManager(repo, repo / "runs")
    with pytest.raises(J.JobError, match="GPU busy"):
        jm.launch("verify", {"run": RUN_B, "top": 3})
    assert not jm.jobs


# ------------------------------------------------------------------ 3D evolution frames


def test_evolution_frames3d_uses_the_evolution_improvement_rule_and_skips_missing_meshes(repo):
    runs = repo / "runs"
    rows = [_evo_row(0, H0, 10.0), _evo_row(1, H1, 12.0), _evo_row(2, H2, 9.0)]
    run = _evo_run(runs, EVO_SKIP_RID, rows)
    _evo_design(run, H0)
    _evo_design(run, H1)                     # meshed but NOT an improvement: never a frame
    _evo_design(run, H2, mesh=False)         # improved, design dir lacks mesh.msh: skipped

    d = D.evolution_frames3d(runs, EVO_SKIP_RID)
    assert d["available"] is True and d["cap"] == D.M3D_DEFAULT_CAP
    [f] = d["frames"]                        # exactly the one improvement with a saved mesh
    assert f["mesh_hash"] == H0 and f["n"] == 0 and f["objective"] == 10.0
    assert f["quadrants"] == "1" and f["n_tris_full"] == 3 and f["decimated"] is False
    assert "1 improved frame(s) skipped" in d["note"]
    # the 2D player agrees on frame selection (2 improvements; one has no geometry)
    assert D.evolution(runs, EVO_SKIP_RID)["n_improvements"] == 2
    json.dumps(d, allow_nan=False)


def test_evolution_frames3d_decimates_hole_free_and_honors_the_cap(repo):
    runs = repo / "runs"
    run = _evo_run(runs, EVO_RID, [_evo_row(0, H0, 10.0)])
    _evo_design(run, H0)

    full = D.evolution_frames3d(runs, EVO_RID)
    f = full["frames"][0]
    assert full["cap"] == D.M3D_DEFAULT_CAP and f["decimated"] is False
    assert f["n_tris_full"] == 3 and len(f["tris"]) == 9 and f["n_verts"] == 4
    assert len(f["verts"]) == 12 and all(isinstance(v, float) for v in f["verts"])

    # A 12x12 grid (242 triangles) forced under a 100-triangle budget must be welded, not
    # stride-sampled: no degenerate faces survive and the sheet stays contiguous (the old
    # tris[::k] sampler punched single-triangle holes across the whole surface).
    rid = "20261026T000010Z-screen-ab1201"
    run2 = _evo_run(runs, rid, [_evo_row(0, H0, 10.0)])
    _evo_design(run2, H0, grid=12)
    dec = D.evolution_frames3d(runs, rid, max_tris_per_frame=100)
    g = dec["frames"][0]
    assert dec["cap"] == 100 and g["decimated"] is True and g["n_tris_full"] == 242
    assert 0 < len(g["tris"]) // 3 <= 100
    tri = np.asarray(g["tris"]).reshape(-1, 3)
    assert not np.any((tri[:, 0] == tri[:, 1]) | (tri[:, 1] == tri[:, 2]) | (tri[:, 0] == tri[:, 2]))
    # symmetry-plane vertices stay exactly on the plane so the mirrored seam has no slit
    assert np.any(np.abs(np.asarray(g["verts"]).reshape(-1, 3)[:, 0]) == 0.0)


def test_evolution_frames3d_available_false_is_honest(repo):
    runs = repo / "runs"
    _evo_run(runs, EVO_NOMESH_RID, [_evo_row(0, H0, 10.0)])       # improved, no design dir
    d = D.evolution_frames3d(runs, EVO_NOMESH_RID)
    assert d["available"] is False and d["frames"] == [] and d["cap"] == D.M3D_DEFAULT_CAP
    assert "skipped: no saved mesh" in d["note"]

    _evo_run(runs, EVO_NOROWS_RID, [])                            # search.ndjson exists, empty
    d = D.evolution_frames3d(runs, EVO_NOROWS_RID)
    assert d["available"] is False and d["frames"] == []
    assert "no evaluations recorded yet" in d["note"]


def test_evolution_frames3d_cache_is_created_and_invalidated_by_a_mesh_change(repo):
    runs = repo / "runs"
    run = _evo_run(runs, EVO_RID, [_evo_row(0, H0, 10.0)])
    _evo_design(run, H0)
    cache = runs / ".gui_cache" / f"evolution_{EVO_RID}_m3d.json"

    first = D.evolution_frames3d(runs, EVO_RID)
    assert cache.exists() and first["frames"][0]["n_verts"] == 4
    key1 = json.loads(cache.read_text(encoding="utf-8"))["key"]
    assert D.evolution_frames3d(runs, EVO_RID) == first          # unchanged: cache hit

    _evo_design(run, H0, extra_node=True)                        # size + mtime_ns bump
    second = D.evolution_frames3d(runs, EVO_RID)
    key2 = json.loads(cache.read_text(encoding="utf-8"))["key"]
    assert key1 != key2 and second["frames"][0]["n_verts"] == 5
    assert second["frames"][0]["n_verts"] != first["frames"][0]["n_verts"]


def test_evolution_frames3d_quadrants_chain_meta_then_row_then_config(repo):
    runs = repo / "runs"
    # mesh_meta.result.quadrants wins
    r = _evo_run(runs, EVO_Q_META_RID, [_evo_row(0, H0, 10.0, quadrants="1")], cfg_quadrants="1234")
    _evo_design(r, H0, quadrants_meta="14")
    assert D.evolution_frames3d(runs, EVO_Q_META_RID)["frames"][0]["quadrants"] == "14"
    # mesh_meta without quadrants -> the ndjson row
    r = _evo_run(runs, EVO_Q_ROW_RID, [_evo_row(0, H0, 10.0, quadrants="12")], cfg_quadrants="1234")
    _evo_design(r, H0)
    assert D.evolution_frames3d(runs, EVO_Q_ROW_RID)["frames"][0]["quadrants"] == "12"
    # neither -> config.yaml mesh.quadrants
    r = _evo_run(runs, EVO_Q_CFG_RID, [_evo_row(0, H0, 10.0)], cfg_quadrants="14")
    _evo_design(r, H0)
    assert D.evolution_frames3d(runs, EVO_Q_CFG_RID)["frames"][0]["quadrants"] == "14"
    # nothing recorded anywhere -> the mesh_surface last resort
    r = _evo_run(runs, EVO_Q_NONE_RID, [_evo_row(0, H0, 10.0)], cfg_quadrants=None)
    _evo_design(r, H0)
    assert D.evolution_frames3d(runs, EVO_Q_NONE_RID)["frames"][0]["quadrants"] == "1234"


def test_evolution_frames3d_route(server, repo):
    runs = repo / "runs"
    run = _evo_run(runs, EVO_RID, [_evo_row(0, H0, 10.0)])
    _evo_design(run, H0)

    code, body = _req(server + f"/api/evolution/{EVO_RID}/frames3d")
    assert code == 200 and body["run_id"] == EVO_RID
    assert body["available"] is True and body["cap"] == D.M3D_DEFAULT_CAP and "note" not in body
    [f] = body["frames"]
    assert f["mesh_hash"] == H0 and len(f["tris"]) == 9 and f["decimated"] is False
    assert _req(server + "/api/evolution/bad-id/frames3d")[0] == 400
    assert _req(server + "/api/evolution/20261026T000099Z-screen-abc999/frames3d")[0] == 404


# ------------------------------------------------------------------ server fixture


@pytest.fixture()
def server(repo):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(App(repo), port))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def _req(url, data=None, ctype="application/json", host=None):
    r = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    if data is not None:
        r.add_header("Content-Type", ctype)
    if host:
        r.add_header("Host", host)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


# ------------------------------------------------------------------ view syntax gate


def test_static_app_js_parses_as_an_es_module(tmp_path):
    """A syntax error in app.js blanks every view; catch it offline (same gate as tests/test_gui.py)."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    src = ROOT / "hornlab_search" / "gui" / "static" / "app.js"
    mjs = tmp_path / "app.mjs"
    mjs.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([node, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]


# ------------------------------------------------------------------ C-5 companion: cma_files

CMA_RID = "20261025T000004Z-screen-eee444"     # isolated cma/ tree for the cma_files cases


def test_cma_files_lists_every_served_pycma_log(repo):
    run = _write_run(repo / "runs", CMA_RID, with_step=False)
    (run / "cma" / "restart_0").mkdir(parents=True)
    (run / "cma" / "restart_1").mkdir()
    (run / "cma" / "version.txt").write_text("3.3\n")
    (run / "cma" / "outcmaes_progress.txt").write_text("progress\n")
    (run / "cma" / "restart_0" / "outcmaes_fit.dat").write_text("1 2\n")
    (run / "cma" / "restart_0" / "parameters.json2").write_text("{}")
    (run / "cma" / "restart_1" / "x0.q").write_text("q")

    files = D.run_detail(repo / "runs", CMA_RID)["cma_files"]
    assert files == [
        {"path": "cma/outcmaes_progress.txt", "name": "outcmaes_progress.txt", "size": 10},
        {"path": "cma/restart_0/outcmaes_fit.dat", "name": "outcmaes_fit.dat", "size": 5},
        {"path": "cma/restart_0/parameters.json2", "name": "parameters.json2", "size": 2},
        {"path": "cma/restart_1/x0.q", "name": "x0.q", "size": 1},
        {"path": "cma/version.txt", "name": "version.txt", "size": 5},
    ]
    assert [f["path"] for f in files] == sorted(f["path"] for f in files)
    json.dumps(D.run_detail(repo / "runs", CMA_RID), allow_nan=False)


def test_cma_files_is_empty_without_a_cma_tree(repo):
    assert D.run_detail(repo / "runs", RUN_D)["cma_files"] == []


def test_cma_files_excludes_extensions_the_raw_route_refuses(repo):
    run = _write_run(repo / "runs", CMA_RID, with_step=False)
    (run / "cma" / "restart_0").mkdir(parents=True)
    for name in ("evil.exe", "evil.py", "notes.md", "archive.bin"):
        (run / "cma" / name).write_text("x")
    (run / "cma" / "restart_0" / "evil.exe").write_text("x")
    assert D.run_detail(repo / "runs", CMA_RID)["cma_files"] == []


# ------------------------------------------------------------------ CAD inventory fallback


def test_step_inventory_resolves_the_design_cad_block(repo):
    run = repo / "runs" / RUN_B
    _write_mesh_meta(run, HASH, {"cad": CAD_BLOCK})
    [step] = D.run_detail(repo / "runs", RUN_B)["step_files_detail"]
    assert step["name"] == STEP
    # The current step_build cad block is projected onto the G4 chip contract, using its REAL
    # key names: face_inventory -> faces, solid.solids -> solids, solid.all_shells_closed -> closed.
    assert step["inventory"] == {
        "faces": [{"label": "driver", "count": 1}, {"label": "wall", "count": 24}],
        "solids": 1,
        "closed": True,
        "tool_sha256": CAD_BLOCK["tool_sha256"],
        "tool_path": CAD_BLOCK["tool_path"],
    }
    assert "tool" not in step["inventory"] and "face_inventory" not in step["inventory"]
    json.dumps(D.run_detail(repo / "runs", RUN_B), allow_nan=False)


def test_step_inventory_fallback_emits_only_the_fields_the_cad_block_carries(repo):
    run = repo / "runs" / RUN_B
    _write_mesh_meta(run, HASH, {"cad": {"face_inventory": {"driver": 1, "wall": 4}}})
    [step] = D.run_detail(repo / "runs", RUN_B)["step_files_detail"]
    assert step["inventory"] == {"faces": [{"label": "driver", "count": 1},
                                           {"label": "wall", "count": 4}]}


def test_step_inventory_sidecar_wins_over_the_design_cad_block(repo):
    run = repo / "runs" / RUN_A                 # already has step/<name>.inventory.json = INVENTORY
    _write_mesh_meta(run, HASH, {"cad": CAD_BLOCK})
    [step] = D.run_detail(repo / "runs", RUN_A)["step_files_detail"]
    assert step["inventory"] == INVENTORY       # sidecar wins even when a cad block exists


def test_step_inventory_is_null_for_a_non_cad_design(repo):
    run = repo / "runs" / RUN_D
    _write_mesh_meta(run, HASH, {"summary": {"area_m2": 1.0},
                                 "mesher_config": {"mesh": {"epw": 8.0}}})
    [step] = D.run_detail(repo / "runs", RUN_D)["step_files_detail"]
    assert step["inventory"] is None


# ------------------------------------------------------------------ cad_route solve-group marker


def test_cad_route_comes_from_the_best_successful_design(repo):
    run = repo / "runs" / RUN_D
    _write_rows(run, [_row(0, H0, 10.0), _row(1, H1, 5.0), _row(2, H2, None, ok=False)])
    _write_mesh_meta(run, H0, {"summary": {}})       # seed is a formula mesh: no cad block
    _write_mesh_meta(run, H1, {"cad": CAD_BLOCK})    # the best successful row is the cad design
    g = D._solve_group_fingerprint(run)
    assert g["cad_route"] is True
    json.dumps(g, allow_nan=False)


def test_cad_route_falls_back_to_the_seed_row_when_nothing_succeeded(repo):
    run = repo / "runs" / RUN_D
    _write_rows(run, [_row(0, H0, None, ok=False)])
    _write_mesh_meta(run, H0, {"cad": CAD_BLOCK})
    assert D._solve_group_fingerprint(run)["cad_route"] is True


def test_cad_route_is_absent_for_non_cad_runs_and_not_read_from_a_non_best_row(repo):
    # plain run: no mesh_meta anywhere -> no marker
    assert "cad_route" not in D._solve_group_fingerprint(repo / "runs" / RUN_B)
    # the proxy is the BEST row: a cad seed does not badge a run whose best row is non-cad
    run = repo / "runs" / RUN_D
    _write_rows(run, [_row(0, H0, 10.0), _row(1, H1, 5.0)])
    _write_mesh_meta(run, H0, {"cad": CAD_BLOCK})
    _write_mesh_meta(run, H1, {"summary": {}})
    assert "cad_route" not in D._solve_group_fingerprint(run)


# ------------------------------------------------------------------ WP16 alpha pin test


def test_solve_group_pins_a_non_default_source_profile_alpha(repo):
    run = repo / "runs" / RUN_D
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    cfg["solve"]["source_profile_alpha"] = 0.3
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))
    g = D._solve_group_fingerprint(run)
    assert g["source_profile_alpha"] == 0.3

    # an explicit 0.0 is the no-op default: still omitted (only-when-non-default)
    cfg["solve"]["source_profile_alpha"] = 0.0
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))
    assert "source_profile_alpha" not in D._solve_group_fingerprint(run)
    # a default run (key absent) omits it too
    assert "source_profile_alpha" not in D._solve_group_fingerprint(repo / "runs" / RUN_B)


# ------------------------------------------------------------------ G-1b search resume


def test_search_resume_argv_shape_carries_every_cli_flag(repo):
    jm = J.JobManager(repo, repo / "runs")
    run_dir = str((repo / "runs" / RUN_B).resolve())
    argv, gpu = jm.build_argv("search", {
        "config": "examples/cfg.yaml", "resume": RUN_B, "budget": 25, "max_evals": 40,
        "mode": "verify", "allow_config_change": True,
        "brief": "examples/briefs/axi_90x90_1in.yaml", "cma_seed": 7})
    assert gpu is True                                     # same GPU kind, same launch lock
    assert argv == ["search", "--config", "examples/cfg.yaml", "--budget", "25",
                    "--max-evals", "40", "--mode", "verify", "--resume", run_dir,
                    "--allow-config-change",
                    "--brief", "examples/briefs/axi_90x90_1in.yaml", "--cma-seed", "7"]


def test_search_resume_config_and_budget_are_optional(repo):
    jm = J.JobManager(repo, repo / "runs")
    run_dir = str((repo / "runs" / RUN_B).resolve())
    # The CLI resumes from <run>/config.yaml when --config is absent (cli.py:646) and falls back
    # to the run's own search.budget when --budget is absent (cli.py:695): both stay omitted.
    argv, gpu = jm.build_argv("search", {"resume": RUN_B})
    assert gpu is True and argv == ["search", "--resume", run_dir]
    # explicit budget/mode pass straight through, before --resume
    argv, _ = jm.build_argv("search", {"resume": RUN_B, "budget": "12", "mode": "screen"})
    assert argv == ["search", "--budget", "12", "--mode", "screen", "--resume", run_dir]


def test_continue_run_argv_is_n_new_evaluations(repo):
    """The exact argv the run-detail Continue card sends: N NEW evals on the stored config.
    No --config (the CLI reuses <run>/config.yaml) and no --max-evals (it counts replays too)."""
    jm = J.JobManager(repo, repo / "runs")
    run_dir = str((repo / "runs" / RUN_B).resolve())
    argv, gpu = jm.build_argv("search", {"resume": RUN_B, "budget": 25, "mode": "verify"})
    assert gpu is True
    assert argv == ["search", "--budget", "25", "--mode", "verify", "--resume", run_dir]
    assert "--config" not in argv
    assert "--max-evals" not in argv


def test_search_non_resume_argv_is_unchanged_and_new_flags_are_additive(repo):
    jm = J.JobManager(repo, repo / "runs")
    argv, gpu = jm.build_argv("search", {"config": "examples/cfg.yaml"})
    assert gpu is True and argv == ["search", "--config", "examples/cfg.yaml",
                                    "--budget", "60"]   # exact pre-resume shape/default
    argv, _ = jm.build_argv("search", {"config": "examples/cfg.yaml",
                                       "max_evals": 100, "mode": "verify"})
    assert argv == ["search", "--config", "examples/cfg.yaml", "--budget", "60",
                    "--max-evals", "100", "--mode", "verify"]


def test_search_resume_preview_reports_the_exact_command_and_gpu(server):
    code, body = _req(server + "/api/preview", data=json.dumps(
        {"kind": "search", "args": {"resume": RUN_B, "budget": 25, "mode": "screen"}}).encode())
    assert code == 200 and body["gpu"] is True and body["gpu_busy"] is None
    assert body["command"].startswith("hornlab-search search ")
    assert "--resume" in body["command"] and RUN_B in body["command"]


def test_continue_run_preview_is_budget_only(server):
    """The Continue card's previewed command carries the new-eval budget and mode only: no
    --config (reused from the run) and no --max-evals."""
    code, body = _req(server + "/api/preview", data=json.dumps(
        {"kind": "search", "args": {"resume": RUN_B, "budget": 25, "mode": "verify"}}).encode())
    assert code == 200 and body["gpu"] is True
    assert "--budget 25" in body["command"]
    assert "--mode verify" in body["command"]
    assert "--config" not in body["command"]
    assert "--max-evals" not in body["command"]


def test_search_resume_queues_under_an_external_gpu_lock(repo, monkeypatch):
    from hornlab_search.search.gpulock import _lock_path
    lk = _lock_path(repo / "runs")
    lk.parent.mkdir(parents=True, exist_ok=True)
    lk.write_text(json.dumps({"pid": os.getpid(), "user": "u", "command": "search x",
                              "start_time": "t"}))
    jm = J.JobManager(repo, repo / "runs")
    jm.QUEUE_POLL_S = 3600                       # the lazy pump must not fire during this test

    def _no_spawn(*a, **k):
        pytest.fail("a queued resume must not spawn before the GPU frees")

    monkeypatch.setattr(J.subprocess, "Popen", _no_spawn)
    # A FRESH launch under the same lock keeps the hard refusal (test_gui.py pins this too).
    with pytest.raises(J.JobError, match="GPU busy"):
        jm.launch("search", {"config": "examples/cfg.yaml", "budget": 5})
    job = jm.launch("search", {"resume": RUN_B})
    assert job.status == "queued" and job.proc is None
    assert not job.log.exists()
    assert jm.queue_position(job) == 1
    jm.cancel(job.id)                            # leave no queued job for the lazy thread
    assert job.status == "cancelled"
    assert not [j for j in jm.jobs.values() if j.status == "queued"]


def test_search_resume_uses_the_one_gui_gpu_slot(repo, monkeypatch):
    jm = J.JobManager(repo, repo / "runs")
    jm.QUEUE_POLL_S = 3600

    def _no_spawn(*a, **k):
        pytest.fail("a queued resume must not spawn while the GUI GPU job is running")

    monkeypatch.setattr(J.subprocess, "Popen", _no_spawn)
    fake = J.Job("fake", "search", ["search", "--resume", "x"],
                 repo / "runs" / "fake.log", True)
    jm.jobs[fake.id] = fake                            # a GPU job from this GUI is still running
    job = jm.launch("search", {"resume": RUN_B})
    assert fake.status == "running" and job.status == "queued"
    assert job.proc is None and not job.log.exists()
    assert jm.queue_position(job) == 1 and job.started
    jm.cancel(job.id)                                  # no queued job left behind
    assert job.status == "cancelled"


class _FakeProc:
    """A Popen stand-in: wait() blocks until release() so the job stays 'running' under test control."""
    _next_pid = 4000

    def __init__(self, *a, **k):
        type(self)._next_pid += 1
        self.pid = type(self)._next_pid
        self.returncode = None
        self.release = threading.Event()

    def wait(self, timeout=None):
        self.release.wait(timeout)
        return 0

    def poll(self):
        return self.returncode


def _fake_spawn(procs):
    def spawn(*a, **k):
        proc = _FakeProc(*a, **k)
        procs.append(proc)
        return proc
    return spawn


def _wait_until(pred, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(0.01)
    return False


def test_queued_resume_starts_when_an_external_gpu_lock_clears(repo, monkeypatch):
    procs = []
    monkeypatch.setattr(J.subprocess, "Popen", _fake_spawn(procs))
    jm = J.JobManager(repo, repo / "runs")
    jm.QUEUE_POLL_S = 3600
    jm.gpu_busy = lambda: "GPU busy: other (pid 1)"
    job = jm.launch("search", {"resume": RUN_B})
    assert job.status == "queued" and job.proc is None and procs == []
    assert jm.queue_position(job) == 1
    jm.gpu_busy = lambda: None
    assert jm.pump() is job
    assert job.status == "running" and job.proc is procs[0]
    assert job.log.exists() and jm.queue_position(job) == 0
    procs[0].release.set()
    assert _wait_until(lambda: job.status == "done")


def test_queued_resumes_start_one_at_a_time_in_fifo_order(repo, monkeypatch):
    procs = []
    monkeypatch.setattr(J.subprocess, "Popen", _fake_spawn(procs))
    jm = J.JobManager(repo, repo / "runs")
    jm.QUEUE_POLL_S = 3600
    jm.gpu_busy = lambda: None
    busy = J.Job("busy", "search", ["search"], repo / "runs" / "busy.log", True)
    jm.jobs[busy.id] = busy
    j1 = jm.launch("search", {"resume": RUN_B})
    j2 = jm.launch("search", {"resume": RUN_C})
    assert (j1.status, j2.status) == ("queued", "queued") and procs == []
    assert (jm.queue_position(j1), jm.queue_position(j2)) == (1, 2)
    busy.status = "done"
    jm.pump()
    assert j1.status == "running" and j1.proc is procs[0] and j2.status == "queued"
    assert (jm.queue_position(j1), jm.queue_position(j2)) == (0, 1)
    procs[0].release.set()                       # j1 finishes -> its _wait thread pumps j2
    assert _wait_until(lambda: j2.status == "running")
    assert j2.proc is procs[1] and procs[0] is not procs[1]
    assert jm.queue_position(j2) == 0
    procs[1].release.set()
    assert _wait_until(lambda: j2.status == "done")


def test_pump_starts_a_queued_resume_when_the_gui_job_finishes(repo, monkeypatch):
    procs = []
    monkeypatch.setattr(J.subprocess, "Popen", _fake_spawn(procs))
    jm = J.JobManager(repo, repo / "runs")
    jm.QUEUE_POLL_S = 3600
    jm.gpu_busy = lambda: None
    running = J.Job("gui-run", "run", ["run"], repo / "runs" / "run.log", True)
    jm.jobs[running.id] = running
    job = jm.launch("search", {"resume": RUN_B})
    assert job.status == "queued" and procs == []
    running.status = "done"                      # the GUI-started GPU job ended
    assert jm.pump() is job
    assert job.status == "running" and job.proc is procs[0]
    procs[0].release.set()
    assert _wait_until(lambda: job.status == "done")


def test_cancel_a_queued_resume_never_spawns_it(repo, monkeypatch):
    procs = []
    monkeypatch.setattr(J.subprocess, "Popen", _fake_spawn(procs))
    jm = J.JobManager(repo, repo / "runs")
    jm.QUEUE_POLL_S = 3600
    jm.gpu_busy = lambda: None
    monkeypatch.setattr(jm, "run_cli",
                        lambda *a, **k: pytest.fail("a queued cancel must not run gpu-clean"))
    busy = J.Job("busy", "search", ["search"], repo / "runs" / "busy.log", True)
    jm.jobs[busy.id] = busy
    job = jm.launch("search", {"resume": RUN_B})
    assert job.status == "queued" and job.proc is None
    out = jm.cancel(job.id)
    assert out is job and job.status == "cancelled" and job.ended and job.proc is None
    assert jm.queue_position(job) == 0
    busy.status = "done"
    assert jm.pump() is None and procs == []


def test_cancel_only_queued_never_kills_a_started_job(repo, monkeypatch):
    """A queued-only cancel is a race guard: it refuses (and touches nothing) once the job started,
    while a genuinely queued job still cancels without spawning."""
    procs = []
    monkeypatch.setattr(J.subprocess, "Popen", _fake_spawn(procs))
    jm = J.JobManager(repo, repo / "runs")
    jm.QUEUE_POLL_S = 3600
    jm.gpu_busy = lambda: None
    monkeypatch.setattr(jm, "run_cli",
                        lambda *a, **k: pytest.fail("a refused cancel must not run gpu-clean"))
    running = jm.launch("search", {"resume": RUN_B})
    assert running.status == "running" and running.proc is procs[0]
    with pytest.raises(J.JobError, match="already started"):
        jm.cancel(running.id, only_queued=True)
    assert running.status == "running" and procs[0].poll() is None
    procs[0].release.set()
    assert _wait_until(lambda: running.status == "done")

    jm.gpu_busy = lambda: "GPU busy: other (pid 1)"
    queued = jm.launch("search", {"resume": RUN_C})
    assert queued.status == "queued" and queued.proc is None
    out = jm.cancel(queued.id, only_queued=True)
    assert out is queued and queued.status == "cancelled" and queued.proc is None
    assert len(procs) == 1                        # the queued cancel spawned nothing


def test_a_free_looking_gpu_cannot_let_a_fresh_launch_jump_the_queue(repo, monkeypatch):
    """Strict FIFO: while a continuation is waiting, a resume joins the back of the queue even when
    the GPU lock looks free (the pump has not ticked), and a fresh launch is refused."""
    procs = []
    monkeypatch.setattr(J.subprocess, "Popen", _fake_spawn(procs))
    jm = J.JobManager(repo, repo / "runs")
    jm.QUEUE_POLL_S = 3600
    jm.gpu_busy = lambda: "GPU busy: other (pid 1)"
    a = jm.launch("search", {"resume": RUN_B})
    assert a.status == "queued" and procs == []
    jm.gpu_busy = lambda: None                 # the lock cleared but the pump has not ticked yet
    b = jm.launch("search", {"resume": RUN_C})
    assert b.status == "queued" and b.proc is None and procs == []
    assert (jm.queue_position(a), jm.queue_position(b)) == (1, 2)
    with pytest.raises(J.JobError, match="queued continuation"):
        jm.launch("search", {"config": "examples/cfg.yaml", "budget": 5})
    assert procs == []                         # nothing was spawned by the refused launch
    assert jm.pump() is a
    assert a.status == "running" and a.proc is procs[0] and b.status == "queued"
    assert len(procs) == 1                     # pump started A only
    jm.cancel(b.id)
    procs[0].release.set()
    assert _wait_until(lambda: a.status == "done")


def test_a_persisted_queued_job_loads_cancelled_and_never_starts(repo, monkeypatch):
    run_dir = str((repo / "runs" / RUN_B).resolve())
    jobs_dir = repo / "runs" / "gui_jobs"
    jobs_dir.mkdir(parents=True)
    jid = "20261025T000000-abcdef"
    (jobs_dir / f"{jid}.json").write_text(json.dumps(
        {"id": jid, "kind": "search", "argv": ["search", "--resume", run_dir], "gpu": True,
         "status": "queued", "started": "t", "ended": None}))

    def _no_spawn(*a, **k):
        pytest.fail("a queued job from the previous session must not start")

    monkeypatch.setattr(J.subprocess, "Popen", _no_spawn)
    jm = J.JobManager(repo, repo / "runs")
    job = jm.jobs[jid]
    assert job.status == "cancelled (GUI restarted before start)"
    assert job.proc is None and not job.log.exists()
    assert jm.queue_position(job) == 0
    assert jm.pump() is None


def test_search_resume_validation_refusals(repo):
    jm = J.JobManager(repo, repo / "runs")
    with pytest.raises(J.JobError, match="run id"):
        jm.build_argv("search", {"resume": True})          # the CLI needs a DIR, not a bare flag
    with pytest.raises(J.JobError):
        jm.build_argv("search", {"resume": "not-a-run"})
    with pytest.raises(J.JobError, match="unknown run"):
        jm.build_argv("search", {"resume": "20261025T000099Z-screen-abc999"})
    with pytest.raises(J.JobError, match="repository"):
        jm.build_argv("search", {"config": "../outside.yaml", "resume": RUN_B})
    with pytest.raises(J.JobError, match="config/brief"):
        jm.build_argv("search", {})
    with pytest.raises(J.JobError, match="allow_config_change"):
        jm.build_argv("search", {"config": "examples/cfg.yaml", "allow_config_change": True})
    for bad in ({"resume": RUN_B, "budget": 0}, {"resume": RUN_B, "budget": 5001},
                {"resume": RUN_B, "max_evals": 0}, {"resume": RUN_B, "max_evals": 1_000_001},
                {"resume": RUN_B, "mode": "fast"}):
        with pytest.raises(J.JobError):
            jm.build_argv("search", bad)


def test_search_resume_argv_survives_a_gui_restart(repo):
    jm = J.JobManager(repo, repo / "runs")
    run_dir = str((repo / "runs" / RUN_B).resolve())
    argv = ["search", "--budget", "12", "--resume", run_dir]
    jobs_dir = repo / "runs" / "gui_jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    (jobs_dir / "20261025T000000-abcdef.json").write_text(json.dumps(
        {"id": "20261025T000000-abcdef", "kind": "search", "argv": argv, "gpu": True,
         "status": "done", "returncode": 0, "started": "t", "ended": "t"}))
    [row] = J.JobManager(repo, repo / "runs").list()
    assert row["kind"] == "search" and row["argv"] == argv and row["gpu"] is True
    assert row["command"] == "hornlab-search search --budget 12 --resume " + run_dir


# ── queued-resume HTTP contract (keeps the App handle so the queue can be forced busy) ─────────


@pytest.fixture()
def server_app(repo):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    app = App(repo)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, port))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{port}", app
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_http_queue_contract_post_list_get_cancel(server_app, monkeypatch):
    base, app = server_app
    procs = []
    monkeypatch.setattr(J.subprocess, "Popen", _fake_spawn(procs))
    app.jobs.QUEUE_POLL_S = 3600
    app.jobs.gpu_busy = lambda: "GPU busy: other (pid 1)"
    code, body = _req(base + "/api/jobs", data=json.dumps(
        {"kind": "search", "args": {"resume": RUN_B}}).encode())
    assert code == 200 and body["status"] == "queued" and body["position"] == 1
    jid = body["id"]
    code, rows = _req(base + "/api/jobs")
    [row] = [r for r in rows if r["id"] == jid]
    assert row["status"] == "queued" and row["queue_position"] == 1
    code, detail = _req(base + f"/api/job/{jid}")
    assert code == 200 and detail["status"] == "queued" and detail["queue_position"] == 1
    code, cancelled = _req(base + f"/api/job/{jid}/cancel", data=json.dumps({}).encode())
    assert code == 200 and cancelled["status"] == "cancelled"
    assert procs == []                                 # it never spawned
    code, detail = _req(base + f"/api/job/{jid}")
    assert code == 200 and detail["queue_position"] == 0
    assert _req(base + "/api/job/does-not-exist")[0] == 404


def test_http_cancel_only_queued_refuses_an_already_started_job(server_app, monkeypatch):
    """The card/list race guard over HTTP: a queued-only cancel still works while queued, but once
    the job auto-started it returns an error and kills nothing."""
    base, app = server_app
    procs = []
    monkeypatch.setattr(J.subprocess, "Popen", _fake_spawn(procs))
    app.jobs.QUEUE_POLL_S = 3600
    app.jobs.gpu_busy = lambda: "GPU busy: other (pid 1)"
    code, body = _req(base + "/api/jobs", data=json.dumps(
        {"kind": "search", "args": {"resume": RUN_B}}).encode())
    assert code == 200 and body["status"] == "queued" and body["position"] == 1
    code, cancelled = _req(base + f"/api/job/{body['id']}/cancel",
                           data=json.dumps({"only_queued": True}).encode())
    assert code == 200 and cancelled["status"] == "cancelled"
    assert procs == []                                 # the queued cancel spawned nothing

    app.jobs.gpu_busy = lambda: None                   # the job now starts before the click lands
    running = app.jobs.launch("search", {"resume": RUN_C})
    assert running.status == "running" and running.proc is procs[0]
    monkeypatch.setattr(app.jobs, "run_cli",
                        lambda *a, **k: pytest.fail("a refused cancel must not run gpu-clean"))
    code, refused = _req(base + f"/api/job/{running.id}/cancel",
                        data=json.dumps({"only_queued": True}).encode())
    assert code == 200 and "already started" in refused["error"]
    assert running.status == "running" and procs[0].poll() is None
    assert len(procs) == 1                             # no second spawn, no kill
    procs[0].release.set()
    assert _wait_until(lambda: running.status == "done")


# ── kill-current (owner 2026-10-25): jobs.stop_external ────────────────────────────────────────
# The externally-started run holding OUR gpu lock is killed by the pid the lock file records
# (+ its child tree), then a gpu-clean pass; the kill is monkeypatched here so no real process
# dies in tests. GUI-started running jobs route through cancel() instead — the refusal test
# pins that the two paths never race.


def test_stop_external_kills_lock_holder_and_cleans(tmp_path, monkeypatch):
    from hornlab_search.gui import jobs as J
    from hornlab_search.search.gpulock import _lock_path
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    jm = J.JobManager(root, root / "runs")
    import sys
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        lk = _lock_path(root / "runs")
        lk.parent.mkdir(parents=True, exist_ok=True)
        lk.write_text(json.dumps({"pid": sleeper.pid, "user": "terminal",
                                  "command": "hornlab-search search --config x.yaml",
                                  "start_time": "t"}))
        killed, cleans = [], []
        monkeypatch.setattr(J.JobManager, "_kill_tree", lambda self, pid: killed.append(pid))
        monkeypatch.setattr(J.JobManager, "run_cli",
                            lambda self, argv, timeout=120: cleans.append(argv) or (0, "gpu-clean out"))
        out = jm.stop_external()
        assert out["ok"] is True and out["killed"] == sleeper.pid
        assert out["command"] == "hornlab-search search --config x.yaml"
        assert killed == [sleeper.pid] and cleans == [["gpu-clean"]]
    finally:
        sleeper.kill()


def test_stop_external_refuses_while_gui_gpu_job_running(tmp_path):
    """A GUI-started running GPU job is the Stop control's path (cancel) - the kill must never race it."""
    from hornlab_search.gui import jobs as J
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    jm = J.JobManager(root, root / "runs")
    jm.jobs["j1"] = J.Job("j1", "search", ["search"], root / "runs" / "j.log", True)  # running GPU job
    with pytest.raises(J.JobError, match="use its Stop control"):
        jm.stop_external()


def test_stop_external_no_live_lock_is_honest(tmp_path):
    from hornlab_search.gui import jobs as J
    from hornlab_search.search.gpulock import _lock_path
    import sys
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    jm = J.JobManager(root, root / "runs")
    # a definitively dead pid: spawn, wait, then record its (now-exited) pid in the lock
    p = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(0)"])
    p.wait()
    lk = _lock_path(root / "runs")
    lk.parent.mkdir(parents=True, exist_ok=True)
    lk.write_text(json.dumps({"pid": p.pid, "user": "u", "command": "x", "start_time": "t"}))
    out = jm.stop_external()
    assert out["ok"] is False and "no live GPU lock" in out["error"]


def test_stop_external_refuses_its_own_pid(tmp_path):
    from hornlab_search.gui import jobs as J
    from hornlab_search.search.gpulock import _lock_path
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    jm = J.JobManager(root, root / "runs")
    lk = _lock_path(root / "runs")
    lk.parent.mkdir(parents=True, exist_ok=True)
    lk.write_text(json.dumps({"pid": os.getpid(), "user": "gui", "command": "gui", "start_time": "t"}))
    with pytest.raises(J.JobError, match="own process"):
        jm.stop_external()


# ── WP12/S1a GUI passthrough: enclosure mounting + feasibility + campaign skip reason ─────────
# All three are committed-block passthroughs: the GUI reader forwards what the writers recorded and
# invents nothing. The views lane renders them generically; these pin the reader contract.

MOUNT_RID = "20261025T000010Z-screen-aaa999"      # mesh_meta.json carries an enclosure mounting
FEAS_RID = "20261025T000011Z-screen-bbb000"       # config.yaml carries an S1a feasibility block
CAMP_RID = "campaign_20261025T000000Z"            # the campaign entry below (skipped, axisymmetric)

MOUNTING = {
    "mesher": {"depth_mm": 250.0, "edge_mm": 18.0, "plan_type": 1,
               "space_l_mm": 25.0, "space_t_mm": 25.0, "space_r_mm": 25.0, "space_b_mm": 25.0},
    "normalized": {"type": "enclosure", "depth_mm": 250.0, "edge_mm": 18.0,
                   "margins_mm": {"l": 25.0, "t": 25.0, "r": 25.0, "b": 25.0},
                   "plan": "rounded_rectangle"},
}
FEASIBILITY = {
    "rule": "k_law", "f0_hz": 1000.0,
    "required_mouth_w_mm": 188.0, "required_mouth_h_mm": 188.0,
    "envelope_mouth_w_mm": 210.0, "envelope_mouth_h_mm": 210.0,
    "held_coverage_w_deg": None, "held_coverage_v_deg": None,
    "feasible_w": True, "feasible_v": True,
    "screen_freqs_below_f0": 0, "screen_freqs_total": 12,
    "verify_freqs_below_f0": 0, "verify_freqs_total": 18,
    "derivation": [{"knob": "rm_mm", "derived_mm": 6.35, "applied": 6.0,
                    "clamped_to_bound": True, "note": "envelope bound"}],
}


def test_mesh_surface_carries_the_wp12_mounting_block(repo):
    run = _write_run(repo / "runs", MOUNT_RID, with_step=False)
    (run / "designs" / HASH / "mesh.msh").write_text(_mesh_text())
    _write_mesh_meta(run, HASH, {"mounting": MOUNTING})
    m = D.mesh_surface(repo / "runs", MOUNT_RID, HASH)
    assert m["mounting"] == MOUNTING                       # both sub-objects, as written
    assert m["mounting"]["normalized"]["margins_mm"]["b"] == 25.0
    json.dumps(m, allow_nan=False)


def test_mesh_surface_omits_mounting_when_the_meta_has_none(repo):
    run = _write_run(repo / "runs", MOUNT_RID, with_step=False)
    (run / "designs" / HASH / "mesh.msh").write_text(_mesh_text())
    _write_mesh_meta(run, HASH, {"result": {"quadrants": "1"}})
    assert "mounting" not in D.mesh_surface(repo / "runs", MOUNT_RID, HASH)


def test_run_detail_passes_the_s1a_feasibility_block_through(repo):
    run = _write_run(repo / "runs", FEAS_RID, with_step=False)
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    cfg["feasibility"] = FEASIBILITY
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))
    d = D.run_detail(repo / "runs", FEAS_RID)
    assert d["feasibility"] == FEASIBILITY                 # verbatim, derivation included
    assert d["feasibility"]["derivation"][0]["clamped_to_bound"] is True
    json.dumps(d, allow_nan=False)


def test_run_detail_omits_absent_feasibility(repo):
    assert "feasibility" not in D.run_detail(repo / "runs", RUN_B)


def test_campaign_detail_keeps_the_axisymmetric_skip_reason_verbatim(repo):
    """The S1a is_compatible refusal (hv entry under an axisymmetric brief) must reach the GUI
    readable, not sanitized: the views render skip_reason generically."""
    reason = ("brief symmetry 'axisymmetric' is incompatible with the 'hv' entry; "
              "the hv sweep cannot satisfy an axisymmetric target")
    camp = repo / "runs" / CAMP_RID
    camp.mkdir(parents=True)
    (camp / "campaign.json").write_text(json.dumps({
        "tier": "compare", "brief_name": "axi_90x90_1in", "seeds": [1],
        "entries": [{"name": "hv", "group": "g", "symmetry": "hv", "skipped": True,
                     "skip_reason": reason, "jobs": []}]}))
    c = D.campaign_detail(repo / "runs", CAMP_RID)
    [e] = c["entries"]
    assert e["skipped"] is True
    assert e["skip_reason"] == reason
    json.dumps(c, allow_nan=False)


# ------------------------------------------------------------------ C-6 compose config payload
# The Compose wizard's hybrid views read ``d[i].generator_block`` and ``d[i].seed_params`` from
# ``/api/configs``. Both are additive verbatim passthroughs of the yaml (absent when the yaml has
# none); these tests pin the contract the views lane codes against.

GENERATOR_BLOCK = {
    "name": "typology",
    "profile_h": {"type": "probe", "first": {"type": "osse"}, "second": {"type": "tractrix"}},
    "profile_v": "same", "n_anchors": 16, "max_wall_deg": 80.0, "mouth": "ellipse",
}
SEED_PARAMS = {"L_mm": 111.5, "h_first_a_deg": 27.5, "h_first_s": 0.35,
               "h_second_fc_hz": 720.0, "h_zs_frac": 0.45}


def _typology_cfg(name: str, **extra) -> dict:
    cfg = {"name": name, "family": "FREEFORM", "brief_file": "../briefs/axi_90x90_1in.yaml",
           "bounds": {"L_mm": {"lo": 1.0, "hi": 2.0}}}
    cfg.update(extra)
    return cfg


def _write_typology_config(examples: Path, name: str, cfg: dict) -> Path:
    (examples / "typologies").mkdir(exist_ok=True)
    p = examples / "typologies" / f"{name}.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return p


def test_configs_payload_carries_the_generator_block_and_seed_params_verbatim(repo, server):
    _write_typology_config(repo / "examples", "hybrid_probe",
                           _typology_cfg("hybrid_probe", generator=GENERATOR_BLOCK,
                                         seed_params=SEED_PARAMS))
    cfg = {c["name"]: c for c in D.list_configs(repo)}["hybrid_probe"]
    assert cfg["generator"] is True
    assert cfg["generator_block"] == GENERATOR_BLOCK           # exactly the yaml content
    assert cfg["seed_params"] == SEED_PARAMS
    assert "seed_bounds_missing" not in cfg
    json.dumps(cfg, allow_nan=False)

    code, body = _req(server + "/api/configs")                 # the route never filters keys
    assert code == 200 and isinstance(body, list)
    served = {c["name"]: c for c in body}["hybrid_probe"]
    assert served["generator_block"] == GENERATOR_BLOCK and served["seed_params"] == SEED_PARAMS


def test_configs_payload_omits_seed_params_when_absent_or_empty(repo):
    ex = repo / "examples"
    _write_typology_config(ex, "empty_seed",
                           _typology_cfg("empty_seed", generator=GENERATOR_BLOCK, seed_params={}))
    _write_typology_config(ex, "no_seed",
                           _typology_cfg("no_seed", generator=GENERATOR_BLOCK))
    _write_typology_config(ex, "empty_generator",
                           _typology_cfg("empty_generator", generator={},
                                         seed_params={"L_mm": 100.0}))
    cfgs = {c["name"]: c for c in D.list_configs(repo)}
    assert "seed_params" not in cfgs["empty_seed"]             # empty dict -> absent, not {}
    assert "seed_params" not in cfgs["no_seed"]
    assert cfgs["empty_seed"]["generator_block"] == GENERATOR_BLOCK
    assert "generator_block" not in cfgs["empty_generator"]    # empty block -> absent, not {}
    assert cfgs["empty_generator"]["seed_params"] == {"L_mm": 100.0}


def test_configs_payload_pins_the_shipped_splice_generator_block(repo):
    """The real committed splice config: its generator block names the spliced parents and the
    seed params are the geometry preview source. The shape below is what yaml.safe_load yields."""
    src = ROOT / "examples" / "typologies" / "splice_osse_tractrix.yaml"
    raw = yaml.safe_load(src.read_text(encoding="utf-8-sig"))
    dest = repo / "examples" / "typologies" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest)

    cfg = {c["name"]: c for c in D.list_configs(repo)}["splice_osse_tractrix"]
    assert cfg["path"] == "examples/typologies/splice_osse_tractrix.yaml"
    gb = cfg["generator_block"]
    assert gb == raw["generator"]                              # verbatim passthrough
    assert gb["name"] == "typology"
    assert gb["profile_h"] == {"type": "splice", "first": {"type": "osse"},
                               "second": {"type": "tractrix"}}
    assert gb["profile_v"] == "same" and gb["n_anchors"] == 16
    assert cfg["seed_params"] == raw["seed_params"]
    assert "seed_bounds_missing" not in cfg
