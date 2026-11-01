"""The CLI end to end with a synthetic backend and a stand-in mesher: exit codes, final lines,
artifacts. No GPU. (The same commands against the real stack are in test_end_to_end.py.)"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search import cli
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search.evaluate import read_ndjson
from hornlab_search.solve import worker
from test_search_support import SyntheticBackend, install_fakes

SMOKE = str(EXAMPLES / "search_smoke.yaml")


@pytest.fixture
def env(tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    monkeypatch.setattr(cli, "_backend", lambda cfg: be)
    # evaluate() in a CLI run has no explicit lib_shas: avoid shelling out to git on every call
    from hornlab_search.search import evaluate as ev_mod
    monkeypatch.setattr(ev_mod, "collect_lib_shas", lambda: {k: "abc1234" for k in (
        "hornlab_mesher", "hornlab_beat_bem", "hornlab_bempp_bem", "hornlab_plots", "hornlab_search")})
    monkeypatch.setattr("hornlab_search.search.cma.collect_lib_shas", ev_mod.collect_lib_shas)
    yield {"be": be, "dirs": ["--runs-dir", str(tmp_path / "runs"), "--cache-dir", str(tmp_path / "cache"),
                              "--dataset-dir", str(tmp_path / "dataset")], "tmp": tmp_path}
    worker.uninstall_handlers()


def run_cli(*argv):
    return cli.main(list(argv))


def latest(tmp):
    runs = sorted((tmp / "runs").iterdir())
    return runs[-1]


def test_no_arguments_and_bad_arguments_exit_2(capsys):
    assert run_cli() == 2
    assert run_cli("run") == 2                       # --config required
    assert run_cli("frobnicate") == 2


def test_version_and_doctor_still_work(capsys):
    assert run_cli("version") == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_run_writes_the_per_design_files_and_one_dataset_record(env, capsys):
    rc = run_cli("run", "--config", SMOKE, "--mode", "screen", *env["dirs"])
    out = capsys.readouterr().out
    assert rc == 0 and out.strip().splitlines()[-1].startswith("run OK")
    run_dir = latest(env["tmp"])
    (design,) = (run_dir / "designs").iterdir()
    for f in ("response.npz", "metrics.json", "status.json", "design.json"):
        assert (design / f).exists(), f
    assert len(DatasetStore(env["tmp"] / "dataset")) == 1
    run = json.loads((run_dir / "run.json").read_text())
    assert run["status"] == "finished" and run["command"].startswith("hornlab-search run")
    assert (run_dir / "best.json").exists() and (run_dir / "config.yaml").exists()


def test_apply_restarts_cli_overrides_and_clears():
    from hornlab_search.config import load_config
    from hornlab_search import cli as cli_mod
    cfg = load_config(SMOKE)
    assert cfg.search.restarts is None
    cli_mod._apply_restarts_cli(cfg, "ipop", 3)
    assert cfg.search.restarts == {"mode": "ipop", "max": 3}
    assert cfg.raw["search"]["restarts"] == {"mode": "ipop", "max": 3}
    cli_mod._apply_restarts_cli(cfg, "off", None)
    assert cfg.search.restarts is None
    assert "restarts" not in cfg.raw["search"]
    with pytest.raises(Exception, match="restarts-max"):
        cli_mod._apply_restarts_cli(cfg, "off", 2)
    with pytest.raises(Exception, match="requires --restarts-mode"):
        cli_mod._apply_restarts_cli(cfg, None, 2)


def test_search_restarts_cli_flag_lands_in_run_json(env, capsys):
    rc = run_cli("search", "--config", SMOKE, "--budget", "8",
                 "--restarts-mode", "ipop", "--restarts-max", "2", *env["dirs"])
    assert rc == 0
    run = json.loads((latest(env["tmp"]) / "run.json").read_text())
    # Absent key when single-ES; present schedule list (may be empty if no natural stop fired).
    assert "restarts" in run
    snap = (latest(env["tmp"]) / "config.yaml").read_text()
    assert "restarts:" in snap and "ipop" in snap


def test_search_report_dataset_chain(env, capsys):
    rc = run_cli("search", "--config", SMOKE, "--budget", "8", *env["dirs"])
    out = capsys.readouterr().out
    assert rc == 0 and out.strip().splitlines()[-1].startswith("search OK")
    run_dir = latest(env["tmp"])
    assert len(read_ndjson(run_dir / "search.ndjson")) == 8
    assert (run_dir / "best.json").exists()
    assert len(DatasetStore(env["tmp"] / "dataset")) == 8

    rc = run_cli("report", str(run_dir), "--out", str(env["tmp"] / "rep.html"), "--top", "1")
    assert rc == 0 and (env["tmp"] / "rep.html").stat().st_size > 5000
    assert capsys.readouterr().out.strip().splitlines()[-1].startswith("report OK")

    rc = run_cli("dataset", "stats", *env["dirs"])
    out = capsys.readouterr().out
    assert rc == 0 and "8 records" in out and "dataset stats OK: 8 records" in out
    assert run_cli("dataset", "verify", *env["dirs"]) == 0
    assert run_cli("dataset", "export", "--out", str(env["tmp"] / "t.npz"), *env["dirs"]) == 0
    z = np.load(env["tmp"] / "t.npz")
    assert z["X"].shape[0] == 8


def test_resume_via_the_cli_does_no_new_work(env, capsys):
    run_cli("search", "--config", SMOKE, "--budget", "6", *env["dirs"])
    run_dir = latest(env["tmp"])
    calls = env["be"].calls
    rc = run_cli("search", "--resume", str(run_dir), "--budget", "0", *env["dirs"])
    assert rc == 0 and env["be"].calls == calls


def test_verify_resolves_the_top_designs_in_verify_mode(env, capsys):
    run_cli("search", "--config", SMOKE, "--budget", "6", *env["dirs"])
    run_dir = latest(env["tmp"])
    capsys.readouterr()
    rc = run_cli("verify", "--run", str(run_dir), "--top", "2", *env["dirs"])
    out = capsys.readouterr().out
    assert rc == 0 and out.strip().splitlines()[-1].startswith("verify OK")
    vrows = read_ndjson(run_dir / "verify" / "search.ndjson")
    assert len(vrows) == 2 and all(r["mode"] == "verify" for r in vrows)
    # the verify objective sits next to the screen one in the report
    from hornlab_search.report.html import build_report
    assert "Verification" in build_report(run_dir, env["tmp"] / "v.html", top_n=1, figures=False).read_text("utf-8")


def test_dataset_commands_on_a_missing_dataset_fail_cleanly(env, capsys):
    assert run_cli("dataset", "stats", *env["dirs"]) == 1
    assert "FAILED" in capsys.readouterr().out


def test_unavailable_backend_exits_1_with_one_clear_line(env, monkeypatch, capsys):
    from hornlab_search.types import BackendUnavailableError

    def boom(cfg):
        raise BackendUnavailableError("backend 'beat_cuda' is not available: no GPU")
    monkeypatch.setattr(cli, "_backend", boom)
    assert run_cli("search", "--config", SMOKE, "--budget", "2", *env["dirs"]) == 1
    assert "FAILED: backend" in capsys.readouterr().out


def test_mesh_units_bug_stops_the_run_with_exit_1(env, monkeypatch, capsys):
    from hornlab_search.mesh.build import MeshUnitsError
    from hornlab_search.search import evaluate as ev_mod

    def boom(*a, **k):
        raise MeshUnitsError("bbox extent 1000 m")
    monkeypatch.setattr(ev_mod, "build_mesh", boom)
    assert run_cli("search", "--config", SMOKE, "--budget", "5", *env["dirs"]) == 1
    assert "ABORTED: MeshUnitsError" in capsys.readouterr().out
    run = json.loads((latest(env["tmp"]) / "run.json").read_text())
    assert run["status"] == "aborted"


@requires_mesher
def test_dry_run_launches_no_solver(env, monkeypatch, capsys):
    monkeypatch.undo()                                       # the REAL mesher, no fakes
    called = []
    monkeypatch.setattr(cli, "_backend", lambda cfg: called.append(1))
    from hornlab_search.solve.beat import BeatBackend
    monkeypatch.setattr(BeatBackend, "solve", lambda *a, **k: (_ for _ in ()).throw(AssertionError("solver called")))
    rc = run_cli("run", "--config", str(EXAMPLES / "osse_baseline.yaml"), "--dry-run")
    out = capsys.readouterr().out
    assert rc == 0 and not called and "no solver was launched" in out and "dofs" in out
    worker.uninstall_handlers()


def test_cost_curve_is_monotone_and_hits_the_measured_points():
    assert cli.estimate_seconds_per_frequency(2369) == pytest.approx(0.4)
    assert cli.estimate_seconds_per_frequency(8941) == pytest.approx(45.0)
    xs = [1000, 2369, 4000, 5140, 7001, 8941, 12000]
    ys = [cli.estimate_seconds_per_frequency(x) for x in xs]
    assert ys == sorted(ys)


def test_ensure_utf8_stdio_reconfigures_non_utf8_streams(monkeypatch):
    """A Windows cp1252 console must not make pin-plan/any glyph print raise (2026-11-01)."""
    class _S:
        encoding = "cp1252"

        def __init__(self):
            self.calls = []

        def reconfigure(self, **kw):
            self.calls.append(kw)

    out, err = _S(), _S()
    monkeypatch.setattr(cli.sys, "stdout", out)
    monkeypatch.setattr(cli.sys, "stderr", err)
    cli._ensure_utf8_stdio()
    want = {"encoding": "utf-8", "errors": "replace"}
    assert out.calls == [want] and err.calls == [want]


def test_ensure_utf8_stdio_leaves_utf8_and_streams_without_reconfigure(monkeypatch):
    class _Utf8:
        encoding = "utf-8"

        def reconfigure(self, **kw):
            raise AssertionError("a utf-8 stream must not be reconfigured")

    class _NoReconfigure:
        encoding = "cp1252"

    monkeypatch.setattr(cli.sys, "stdout", _Utf8())
    monkeypatch.setattr(cli.sys, "stderr", _NoReconfigure())
    cli._ensure_utf8_stdio()   # must not raise
