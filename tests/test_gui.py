"""Local web GUI (hornlab_search/gui): readers, launcher allow-list, server safety. Offline, no GPU,
no real CLI jobs (the launcher is pointed at a harmless sleep script)."""
from __future__ import annotations

import json
import os
import shutil
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui import jobs as J
from hornlab_search.gui.server import App, make_handler

ROOT = Path(__file__).resolve().parents[1]
RID = "20261023T010250Z-screen-abc123"
CID = "campaign_20261023T024453Z"
F = [500.0, 1000.0, 2000.0, 4000.0, 5500.0]


def _design(run: Path, h: str, shift: float) -> None:
    d = run / "designs" / h
    d.mkdir(parents=True)
    n = len(F)
    m = {"freqs_hz": F, "bw_h_deg": [90 + shift] * n, "bw_v_deg": [60.0] * n, "di_db": [9.0] * n,
         "di_source": "balloon", "on_axis_db": [1.0, 2.0, 3.0, 2.0, float("nan")],
         "ripple_h_db": [0.5] * n, "ripple_v_db": [0.4] * n, "z_throat_real": [0.5] * n, "scalars": {}}
    (d / "metrics.json").write_text(json.dumps(m))
    ang = np.linspace(-90, 90, 5)
    np.savez(d / "response.npz", freqs_hz=np.array(F), h_angles_deg=ang, v_angles_deg=ang,
             spl_h_db=np.zeros((n, 5)) - np.abs(ang) / 10, spl_v_db=np.zeros((n, 5)))
    (d / "mesh.msh").write_text("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n3\n"
                                "1 0 0 0\n2 0.1 0 0.05\n3 0 0.08 0.05\n$EndNodes\n"
                                "$Elements\n1\n1 2 2 1 1 1 2 3\n$EndElements\n")
    (d / "design.json").write_text(json.dumps({"family": "FREEFORM", "params": {"a": 1}}))


def _row(n, h, ok, J_, knob):
    return {"n": n, "design_hash": h, "ok": ok, "objective": J_ if ok else 1000.0, "mode": "screen",
            "family": "FREEFORM", "error": None if ok else "invalid_geometry: x",
            "created_utc": f"2026-10-23T00:00:{n:02d}Z", "terms": {"cov": J_},
            "generator": {"knobs": {"L_mm": knob}}}


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    run = runs / RID
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump({
        "name": "fake", "family": "FREEFORM", "bounds": {"L_mm": {"lo": 90.0, "hi": 140.0}},
        "target": {"coverage_h_deg": 90}, "weights": {"cov": 1.0}}))
    rows = [_row(0, "aaaaaaaaaaaa", True, 20.0, 100.0)] + \
           [_row(i, f"{i:012x}", True, 20.0 - i, 139.9) for i in range(1, 8)] + \
           [_row(8, "ffffffffffff", False, 0, 120.0)]
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    _design(run, "aaaaaaaaaaaa", 0.0)
    _design(run, f"{7:012x}", 2.0)
    camp = runs / CID
    camp.mkdir()
    (camp / "campaign.json").write_text(json.dumps({"tier": "compare", "brief_name": "b", "seeds": [1, 2],
        "entries": [{"name": "fam", "group": "g", "jobs": [
            {"seed": 1, "best_j": 10.0, "run_dir": str(run), "stats": {"evaluations": 5}},
            {"seed": 2, "best_j": 10.5, "run_dir": str(run), "stats": {"evaluations": 5}}]}]}))
    briefs = root / "examples" / "briefs"
    briefs.mkdir(parents=True)
    shutil.copy(ROOT / "examples" / "briefs" / "axi_90x90_1in.yaml", briefs)
    (root / "examples" / "cfg.yaml").write_text("name: x\n")
    return root


# ------------------------------------------------------------------ readers


def test_run_summary_and_detail(repo):
    runs = repo / "runs"
    [s] = D.list_runs(runs)
    assert s["id"] == RID and s["n"] == 9 and s["n_ok"] == 8
    assert s["best_j"] == 13.0 and s["best_hash"] == f"{7:012x}" and s["failures"] == {"invalid_geometry": 1}
    d = D.run_detail(runs, RID)
    assert d["J"][-1] is None and d["J"][0] == 20.0
    [sens] = d["sens"]
    assert sens["key"] == "L_mm" and sens["at_hi"] == 6        # top-6 designs all at 139.9 >= 140 - 2 %
    assert d["best"]["on_axis"][-1] is None                     # NaN -> None, never invented
    assert d["best"]["profile"]["h"] and len(d["best"]["polar_h"]) == len(F)
    json.dumps(d, allow_nan=False)


def test_ids_are_validated(repo):
    with pytest.raises(ValueError):
        D.run_detail(repo / "runs", "../../etc")
    with pytest.raises(ValueError):
        D.campaign_detail(repo / "runs", "campaign_x/../..")


def test_campaign_median_and_spread(repo):
    c = D.campaign_detail(repo / "runs", CID)
    [e] = c["entries"]
    assert e["median_j"] == pytest.approx(10.25) and e["spread"] == pytest.approx(0.5) and e["evals"] == 10
    assert e["best"]["hash"] == f"{7:012x}"


def test_mesh_surface(repo):
    m = D.mesh_surface(repo / "runs", RID, "aaaaaaaaaaaa")
    assert m["n_tris"] == 1 and m["tris"] == [0, 1, 2] and m["verts"][3] == 100.0


def test_tail_text_reads_utf16(tmp_path):
    p = tmp_path / "q.log"
    p.write_bytes("a\nb\nc\n".encode("utf-16"))
    assert D.tail_text(p, 2) == ["b", "c"]


def test_user_brief_saved_validated_and_shipped_protected(repo):
    shipped = yaml.safe_load((repo / "examples/briefs/axi_90x90_1in.yaml").read_text())
    p = D.save_user_brief(repo, "my_brief", shipped)
    assert p == repo / "examples/briefs/user/my_brief.yaml" and yaml.safe_load(p.read_text())["name"] == "my_brief"
    with pytest.raises(ValueError, match="shipped"):
        D.save_user_brief(repo, "axi_90x90_1in", shipped)
    with pytest.raises(ValueError):
        D.save_user_brief(repo, "../evil", shipped)
    bad = dict(shipped, envelope={"max_mouth_w_mm": -1})
    with pytest.raises(Exception):
        D.save_user_brief(repo, "bad_brief", bad)
    assert not (repo / "examples/briefs/user/bad_brief.yaml").exists()
    assert not list((repo / "examples/briefs/user").glob(".*.tmp"))


# ------------------------------------------------------------------ launcher


def test_argv_allow_list(repo, monkeypatch):
    monkeypatch.setattr(J, "auto_backend", lambda: None)  # pin CUDA-host behaviour in CI
    jm = J.JobManager(repo, repo / "runs")
    argv, gpu = jm.build_argv("campaign", {"brief": "examples/briefs/axi_90x90_1in.yaml",
                                           "families": "conical, exponential", "tier": "dry-run"})
    assert argv == ["campaign", "--brief", "examples/briefs/axi_90x90_1in.yaml", "--families",
                    "conical,exponential", "--tier", "dry-run"] and gpu is False
    assert jm.build_argv("search", {"config": "examples/cfg.yaml", "budget": 40})[1] is True
    argv, _ = jm.build_argv("search", {"config": "examples/cfg.yaml", "budget": 40})
    assert "--backend" not in argv
    argv, _ = jm.build_argv("search", {"config": "examples/cfg.yaml", "budget": 40,
                                       "backend": "beat_metal"})
    assert argv[argv.index("--backend") + 1] == "beat_metal"
    argv, _ = jm.build_argv("search", {"config": "examples/cfg.yaml", "budget": 40,
                                       "restarts_mode": "ipop", "restarts_max": 3})
    assert argv[argv.index("--restarts-mode") + 1] == "ipop"
    assert argv[argv.index("--restarts-max") + 1] == "3"
    argv, _ = jm.build_argv("search", {"config": "examples/cfg.yaml", "restarts_mode": "bipop"})
    assert argv[argv.index("--restarts-max") + 1] == "2"          # UI/CLI default when max blank
    argv, _ = jm.build_argv("search", {"config": "examples/cfg.yaml", "restarts_mode": "off"})
    assert "--restarts-mode" in argv and argv[argv.index("--restarts-mode") + 1] == "off"
    assert "--restarts-max" not in argv
    for kind, a in [("search", {"config": "../outside.yaml"}),
                    ("search", {"config": "examples/cfg.yaml", "budget": 0}),
                    ("search", {"config": "examples/cfg.yaml", "backend": "cuda"}),
                    ("search", {"config": "examples/cfg.yaml", "restarts_mode": "ipopx"}),
                    ("search", {"config": "examples/cfg.yaml", "restarts_mode": "off",
                                "restarts_max": 2}),
                    ("search", {"config": "examples/cfg.yaml", "restarts_max": 2}),
                    ("campaign", {"brief": "examples/briefs/axi_90x90_1in.yaml", "families": "a;rm -rf"}),
                    ("campaign", {"brief": "examples/briefs/axi_90x90_1in.yaml", "families": "a", "tier": "x"}),
                    ("export-step", {"run": "nope", "top": 1}),
                    ("shell", {})]:
        with pytest.raises(J.JobError):
            jm.build_argv(kind, a)


def test_auto_backend_injected_when_no_cuda(repo, monkeypatch):
    monkeypatch.setattr(J, "auto_backend", lambda: "beat_metal")
    jm = J.JobManager(repo, repo / "runs")
    argv, _ = jm.build_argv("search", {"config": "examples/cfg.yaml", "budget": 40})
    assert argv[argv.index("--backend") + 1] == "beat_metal"
    argv, _ = jm.build_argv("run", {"config": "examples/cfg.yaml"})
    assert argv[argv.index("--backend") + 1] == "beat_metal"


def test_gpu_job_refused_while_lock_held(repo):
    from hornlab_search.search.gpulock import _lock_path
    lk = _lock_path(repo / "runs")
    lk.parent.mkdir(parents=True, exist_ok=True)
    lk.write_text(json.dumps({"pid": os.getpid(), "user": "u", "command": "search x", "start_time": "t"}))
    jm = J.JobManager(repo, repo / "runs")
    with pytest.raises(J.JobError, match="GPU busy"):
        jm.launch("search", {"config": "examples/cfg.yaml", "budget": 5})
    assert not jm.jobs


def test_queued_resume_is_listed_with_status_and_position(repo, monkeypatch):
    """A resume queued behind the GPU is visible (status + 1-based queue_position) without spawning."""
    jm = J.JobManager(repo, repo / "runs")
    jm.QUEUE_POLL_S = 3600
    monkeypatch.setattr(jm, "gpu_busy", lambda: "GPU busy: other (pid 1)")
    monkeypatch.setattr(J.subprocess, "Popen",
                        lambda *a, **k: pytest.fail("a queued resume must not spawn"))
    job = jm.launch("search", {"config": "examples/cfg.yaml", "resume": RID})
    assert job.status == "queued" and job.proc is None and not job.log.exists()
    [row] = jm.list()
    assert row["id"] == job.id and row["status"] == "queued" and row["queue_position"] == 1
    assert jm.view(job.id)["queue_position"] == 1
    with pytest.raises(KeyError):
        jm.view("missing")
    jm.cancel(job.id)
    assert jm.view(job.id)["status"] == "cancelled" and jm.view(job.id)["queue_position"] == 0


def test_launch_log_and_cancel(repo, monkeypatch):
    monkeypatch.setattr(J, "CLI_BOOT", "import sys, time; print('hello', sys.argv[1:], flush=True); time.sleep(60)")
    jm = J.JobManager(repo, repo / "runs")
    job = jm.launch("dry-run", {"config": "examples/cfg.yaml"})
    for _ in range(100):
        if "hello" in "".join(D.tail_text(job.log)):
            break
        time.sleep(0.1)
    assert "hello" in "".join(D.tail_text(job.log)) and job.status == "running"
    jm.cancel(job.id)
    job.proc.wait(timeout=20)
    for _ in range(50):
        if job.ended:
            break
        time.sleep(0.1)
    assert job.status == "cancelled" and job.proc.poll() is not None


# ------------------------------------------------------------------ server


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


def test_api_runs_and_errors(server):
    code, body = _req(server + "/api/runs")
    assert code == 200 and body[0]["id"] == RID
    assert _req(server + f"/api/run/{RID}")[0] == 200
    assert _req(server + "/api/run/bad-id")[0] == 400
    assert _req(server + "/api/nothing")[0] == 404


def test_api_budget_hint_hansen(server):
    code, body = _req(server + "/api/budget-hint?n_knobs=5&restarts_mode=off")
    assert code == 200 and body["recommended"] == 500 and body["hansen_100n"] == 500
    code, body = _req(server + "/api/budget-hint?n_knobs=5&restarts_mode=ipop&restarts_max=15")
    assert code == 200 and body["recommended"] == 800
    assert _req(server + "/api/budget-hint")[0] == 400
    assert _req(server + "/api/budget-hint?n_knobs=x")[0] == 400


def test_server_rejects_foreign_host_and_non_json_posts(server):
    assert _req(server + "/api/runs", host="evil.example:80")[0] == 403
    assert _req(server + "/api/gpu-clean", data=b"x=1", ctype="application/x-www-form-urlencoded")[0] == 415


def test_static_path_traversal_is_404(server):
    assert _req(server + "/../../pyproject.toml")[0] in (400, 404)
    assert _req(server + "/runs/x/../../config.yaml")[0] == 404


def test_post_job_with_bad_args_returns_error(server):
    code, body = _req(server + "/api/jobs", data=json.dumps({"kind": "shell", "args": {}}).encode())
    assert code == 200 and "unknown job kind" in body["error"]


# ------------------------------------------------------------------ designer-facing additions


def test_horn_dims_quarter_and_full():
    q = {"bbox_m": [0, 0, -0.003, 0.18, 0.15, 0.14], "quadrants": "1"}
    assert D.horn_dims(q) == {"mouth_w_mm": 360.0, "mouth_h_mm": 300.0, "depth_mm": 143.0, "includes_shell": True}
    f = {"bbox_m": [-0.2, -0.1, 0.0, 0.2, 0.1, 0.3], "quadrants": "1234"}
    assert D.horn_dims(f)["mouth_w_mm"] == 400.0 and D.horn_dims(f)["mouth_h_mm"] == 200.0
    assert D.horn_dims(None) is None and D.horn_dims({"bbox_m": None}) is None


def test_budget_from_run_command_and_progress(repo):
    run = repo / "runs" / RID
    (run / "run.json").write_text(json.dumps({"command": "hornlab-search search --config x.yaml --budget 40 --max-evals 30 --cma-seed 7"}))
    s = D.run_summary(run)
    assert s["budget"] == 30 and s["cma_seed"] == 7          # --max-evals caps all evaluations
    p = D.run_progress(run)
    assert p["n"] == 9 and p["rate_per_h"] == pytest.approx(3600.0) and p["eta_min"] == pytest.approx(21 / 60)


def test_queue_steps_timeline(tmp_path):
    log = tmp_path / "queue.log"
    log.write_bytes(("=== 2026-10-22T22:16:38 START axi : campaign --tier screen\nnoise\n"
                     "=== 2026-10-22T22:44:51 END axi exit 0\n"
                     "=== 2026-10-23T15:46:00 SKIP late (past start cutoff)\n"
                     "=== 2026-10-23T02:19:19 START s1 : search --budget 950\n").encode("utf-16"))
    steps = D.queue_steps(log)
    assert [s["name"] for s in steps] == ["axi", "late", "s1"]
    assert steps[0]["exit"] == 0 and steps[0]["command"] == "campaign --tier screen"
    assert steps[1]["skipped"] and steps[2]["ended"] is None


def test_list_configs_reads_catalog(repo):
    ex = repo / "examples"
    (ex / "typologies").mkdir()
    (ex / "typologies" / "conical.yaml").write_text(yaml.safe_dump({"name": "conical", "family": "FREEFORM",
        "generator": {"name": "typology"}, "bounds": {"a": {"lo": 0, "hi": 1}, "b": {"lo": 0, "hi": 1, "search": False}}}))
    (ex / "catalog.yaml").write_text(yaml.safe_dump({"entries": [{"name": "conical", "config": "typologies/conical.yaml",
        "group": "classical", "symmetry": "axisymmetric", "description": "d"}]}))
    cfgs = {c["name"]: c for c in D.list_configs(repo)}
    c = cfgs["conical"]
    assert c["group"] == "classical" and c["generator"] is True and c["n_knobs"] == 1
    assert c["path"] == "examples/typologies/conical.yaml"
    assert "catalog" not in cfgs


def test_list_configs_seed_gate_memoizes_and_invalidates(repo, monkeypatch):
    """ISSUES M4: the disabled gate materialized every seed on every refresh (rows marches are
    brentq loops - the saddle is ~25 rows).  Two refreshes of untouched files must march ONCE,
    and an edited config must re-march and serve the new content."""
    typ = repo / "examples" / "typologies"
    typ.mkdir()
    cfg = typ / "conical.yaml"
    shutil.copy(ROOT / "examples" / "typologies" / "conical.yaml", cfg)
    marches = []
    real = D._config_seed_materializes
    monkeypatch.setattr(D, "_config_seed_materializes", lambda p: (marches.append(p), real(p))[1])
    cfgs = {c["name"]: c for c in D.list_configs(repo)}
    assert cfgs["conical"]["disabled"] is False          # the shipped seed materializes
    first = len(marches)
    assert first >= 1
    D.list_configs(repo)                                # unchanged state: served from the memo
    assert len(marches) == first
    cfg.write_text(yaml.safe_dump({"name": "conical_edited", "family": "FREEFORM"}))   # now unloadable
    cfgs = {c["name"]: c for c in D.list_configs(repo)}
    assert len(marches) == first + 1                    # invalidated: re-marched, and only this one
    assert cfgs["conical_edited"]["disabled"] is True and "conical" not in cfgs


def test_past_jobs_reload_after_restart(repo, monkeypatch):
    monkeypatch.setattr(J, "CLI_BOOT", "import sys; print('dry-run OK: done', flush=True)")
    jm = J.JobManager(repo, repo / "runs")
    job = jm.launch("dry-run", {"config": "examples/cfg.yaml"})
    job.proc.wait(timeout=30)
    for _ in range(50):
        if job.ended:
            break
        time.sleep(0.1)
    jm2 = J.JobManager(repo, repo / "runs")           # a new GUI process
    assert job.id in jm2.jobs and jm2.jobs[job.id].status == "done"
    assert jm2.jobs[job.id].argv[:2] == ["run", "--config"]


def test_leaders_prefer_compare_tier_and_apply_the_ranking_rule(repo):
    runs = repo / "runs"
    run = str(runs / RID)
    def camp(cid, tier, entries):
        (runs / cid).mkdir()
        (runs / cid / "campaign.json").write_text(json.dumps({"tier": tier, "brief_name": "b", "seeds": [1, 2],
            "entries": [{"name": n, "group": "g", "jobs": [{"seed": i, "best_j": j, "run_dir": run,
                         "stats": {"evaluations": 5}} for i, j in enumerate(js)]} for n, js in entries]}))
    camp("campaign_20261024T000000Z", "screen", [("newer_screen_winner", [1.0])])       # newer but weaker tier
    camp("campaign_20261023T100000Z", "compare", [("a", [10.0, 10.2]), ("b", [11.0, 11.1])])
    [l] = D.leaders(runs)
    assert l["campaign_id"] == "campaign_20261023T100000Z" and l["family"] == "a"
    assert l["median_j"] == pytest.approx(10.1) and l["gap"] == pytest.approx(0.95) and l["clearly_ahead"] is True
    camp("campaign_20261025T000000Z", "compare", [("a", [10.0, 11.0]), ("b", [10.6, 10.7])])   # gap < spread
    [l] = D.leaders(runs)
    assert l["campaign_id"] == "campaign_20261025T000000Z" and l["clearly_ahead"] is False


@pytest.mark.parametrize("name", ["app.js", "charts.js", "glossary.js", "view3d.js", "evolution.js", "balloon.js", "paramtips.js", "sandbox.js"])
def test_static_js_parses_as_an_es_module(name, tmp_path):
    """A syntax error anywhere in app.js blanks every view ("Loading..." forever); catch it offline."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    import subprocess
    src = ROOT / "hornlab_search" / "gui" / "static" / name
    mjs = tmp_path / (name + ".mjs")                    # .mjs: parse as a module (import/export), not CommonJS
    mjs.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([node, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]


def test_campaign_families_list_or_blank_and_preview(server, repo):
    jm = J.JobManager(repo, repo / "runs")
    argv, _ = jm.build_argv("campaign", {"brief": "examples/briefs/axi_90x90_1in.yaml",
                                         "families": ["conical", "hypex"], "tier": "screen"})
    assert argv[argv.index("--families") + 1] == "conical,hypex"
    argv, _ = jm.build_argv("campaign", {"brief": "examples/briefs/axi_90x90_1in.yaml", "families": "", "tier": "dry-run"})
    assert argv[argv.index("--families") + 1] == "all"
    code, body = _req(server + "/api/preview", data=json.dumps({"kind": "dry-run", "args": {"config": "examples/cfg.yaml"}}).encode())
    assert code == 200 and body["command"] == "hornlab-search run --config examples/cfg.yaml --dry-run" and body["gpu"] is False
    code, body = _req(server + "/api/preview", data=json.dumps({"kind": "campaign", "args": {"brief": "axi_90x90_1in"}}).encode())
    assert "error" in body                      # a brief NAME is not a path: the GUI must send the path


def test_section_outline_from_quarter_mesh_boundary():
    """Plane boundary edges of a quarter mesh give an ordered cross-section chain."""
    # a strip of 2 triangles in the x-z plane (y = 0) plus one off-plane triangle
    pts = np.array([[0, 0, 0], [0.01, 0, 0.0], [0.02, 0, 0.05], [0.03, 0, 0.10], [0.02, 0.02, 0.05]], float)
    tris = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4]])
    [chain] = D._plane_chains(pts, tris, 0)
    assert chain in ([0, 1, 2, 3], [3, 2, 1, 0])


def test_superseded_campaigns_are_excluded(repo):
    runs = repo / "runs"
    ev = repo / "docs" / "evidence" / "campaigns"
    ev.mkdir(parents=True)
    (ev / f"{CID}.campaign.json").write_text("{}")
    old = "campaign_20261022T000000Z"
    (runs / old).mkdir()
    (runs / old / "campaign.json").write_text(json.dumps({"tier": "compare", "brief_name": "b", "seeds": [1],
        "entries": [{"name": "bogus", "jobs": [{"seed": 1, "best_j": 0.1, "run_dir": str(runs / RID), "stats": {"evaluations": 1}}]}]}))
    flags = {c["id"]: c["superseded"] for c in D.list_campaigns(runs)}
    assert flags == {CID: False, old: True}
    assert all(l["family"] != "bogus" for l in D.leaders(runs))


def test_typologies_compat_uses_the_cli_rule(repo):
    shutil.copy(ROOT / "examples" / "briefs" / "hifi_90x60_1in.yaml", repo / "examples" / "briefs")
    (repo / "examples" / "catalog.yaml").write_text(yaml.safe_dump({"entries": [
        {"name": "axi_one", "config": "cfg.yaml", "group": "classical", "symmetry": "axisymmetric", "description": "d"}]}))
    [t] = D.typologies(repo, repo / "runs")
    assert t["compat"]["axi_90x90_1in"]["ok"] is True
    assert t["compat"]["hifi_90x60_1in"]["ok"] is False and "axisymmetric" in t["compat"]["hifi_90x60_1in"]["reason"]
    assert t["budget"] == {"screen": 40, "compare": 150}


def test_mouth_outline_is_the_convex_rim_mirrored_from_a_quarter():
    # quarter rim of a 200 x 100 mm (outer) rectangle-ish mouth at z = 0.1 m, plus deeper wall nodes
    rim = [[0.1, 0.0, 0.1], [0.1, 0.03, 0.1], [0.08, 0.05, 0.1], [0.0, 0.05, 0.1], [0.095, 0.02, 0.1]]   # last: inside
    deep = [[0.01, 0.0, 0.0], [0.0, 0.01, 0.0]]
    out = D.mouth_outline(np.array(rim + deep, float), "1")
    xs, ys = [p[0] for p in out], [p[1] for p in out]
    assert max(xs) == 100.0 and min(xs) == -100.0 and max(ys) == 50.0 and min(ys) == -50.0
    assert [95.0, 20.0] not in out                              # interior rim node is not on the outline


def test_evolution_frames_cache_and_growth(repo):
    runs = repo / "runs"
    e = D.evolution(runs, RID)
    assert len(e["frames"]) == 9 and e["n_improvements"] == 8   # start + 7 strictly better rows
    f0, f7 = e["frames"][0], e["frames"][7]
    assert f0["improved"] and f0["geo"] is not None   # 1-triangle fixture: too small for a section or rim outline
    assert f7["knobs"]["L_mm"] == pytest.approx((139.9 - 90) / 50, abs=1e-4)
    assert e["frames"][8]["ok"] is False and e["frames"][8]["kind"] == "invalid_geometry"
    assert (runs / ".gui_cache" / f"evolution_{RID}.json").exists()
    with open(runs / RID / "search.ndjson", "a") as fh:            # the search grows -> cache refreshes
        fh.write(json.dumps(_row(9, "aaaaaaaaaaaa", True, 1.0, 120.0)) + "\n")
    e2 = D.evolution(runs, RID)
    assert len(e2["frames"]) == 10 and e2["frames"][9]["improved"] and e2["frames"][9]["best_j"] == 1.0


def test_archive_reader_empty_pattern_without_an_atlas(server, repo):
    """A plain cma run writes no archive_heatmap.json: the route says so instead of 404ing."""
    a = D.run_archive(repo / "runs", RID)
    assert a["available"] is False and a["cells"] == [] and a["bins"] is None
    assert a["ranges"] is None and a["stats"] is None
    code, body = _req(server + f"/api/archive/{RID}")
    assert code == 200 and body["available"] is False and body["cells"] == []


def test_archive_reader_serves_the_pinned_heatmap(server, repo):
    """The pinned archive_heatmap.json contract: bins/ranges/descriptors/cells, occupied bins only."""
    heat = {"bins": [4, 3], "ranges": {"h": [0, 180], "v": [0, 180]},
            "descriptors": {"h": "mean_bw_h_deg", "v": "mean_bw_v_deg"},
            "cells": [{"h_center": 67.5, "v_center": 150.0, "objective": 3.5,
                       "design_hash": "aaaaaaaaaaaa"}]}
    (repo / "runs" / RID / "archive_heatmap.json").write_text(json.dumps(heat), encoding="utf-8")
    a = D.run_archive(repo / "runs", RID)
    assert a["available"] is True and a["bins"] == [4, 3] and a["ranges"] == heat["ranges"]
    assert a["descriptors"] == {"h": "mean_bw_h_deg", "v": "mean_bw_v_deg"}
    assert a["cells"][0]["h_center"] == 67.5 and a["cells"][0]["objective"] == 3.5
    assert "rows" not in a and "axis" not in a            # legacy aliases are ignored, not echoed
    code, body = _req(server + f"/api/archive/{RID}")
    assert code == 200 and body["available"] is True
    assert body["descriptors"] == a["descriptors"]
    assert body["cells"][0]["design_hash"] == "aaaaaaaaaaaa"


def test_archive_reader_tolerates_additive_aliases_and_a_half_written_file(repo):
    path = repo / "runs" / RID / "archive_heatmap.json"
    path.write_text("{not json", encoding="utf-8")        # a file being written right now
    assert D.run_archive(repo / "runs", RID)["available"] is False
    heat = {"bins": [2, 2], "ranges": {"h": [0, 180], "v": [0, 180]}, "cells": [],
            "rows": [{"bin": [0, 0]}], "axis": {"h": [0, 180], "v": [0, 180]}}
    path.write_text(json.dumps(heat), encoding="utf-8")
    a = D.run_archive(repo / "runs", RID)
    assert a["available"] is True and a["cells"] == [] and "rows" not in a
    assert a["descriptors"] is None                       # no label contract in this file -> honest None


def test_step_files_listed_and_served_only_by_strict_name(server, repo):
    step = repo / "runs" / RID / "step"
    step.mkdir()
    (step / "fake_rank1_aaaaaaaaaaaa.step").write_text("ISO-10303-21;")
    (step / "notes.txt").write_text("x")
    code, body = _req(server + f"/api/run/{RID}")
    assert body["step_files"] == ["fake_rank1_aaaaaaaaaaaa.step"]
    with urllib.request.urlopen(server + f"/runs/{RID}/step/fake_rank1_aaaaaaaaaaaa.step", timeout=10) as r:
        assert r.status == 200 and r.read() == b"ISO-10303-21;" and "attachment" in r.headers["Content-Disposition"]
    assert _req(server + f"/runs/{RID}/step/notes.txt")[0] == 404
    assert _req(server + f"/runs/{RID}/step/..%2F..%2Fconfig.yaml")[0] == 404
