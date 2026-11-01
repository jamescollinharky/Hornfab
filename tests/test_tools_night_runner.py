"""Offline tests for tools/run_campaign_night.py (the overnight campaign runner).

Hermetic: no GPU, no Julia, no ``hornlab-search`` subprocess. The tool is loaded by path (it is a
script, not a package module) and its real subprocess/hygiene layer is replaced with a fake.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

from conftest import REPO

TOOL = REPO / "tools" / "run_campaign_night.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("run_campaign_night_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


night = _load_tool()

NIGHT_NAME = "smoke_2026-10-27"


# ------------------------------------------------------------------ helpers


def _night_doc(*, brief: str | None = None) -> dict:
    search = {
        "id": "t0__b1t__rosse_morph",
        "kind": "search",
        "config": "examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml",
        "budget": 1,
        "mode": "screen",
    }
    if brief:
        search["brief"] = brief
    return {
        "night": NIGHT_NAME,
        "jobs": [
            {
                "id": "phaseB_ladder",
                "kind": "command",
                "argv": [".venv\\Scripts\\python.exe", "tools\\measure_fused_ceiling.py",
                         "--mouth-res", "3.0"],
            },
            search,
        ],
    }


def _write_night(tmp_path: Path, doc: dict | None = None) -> Path:
    path = tmp_path / "night.yaml"
    path.write_text(yaml.safe_dump(doc or _night_doc(), sort_keys=False), encoding="utf-8")
    return path


class FakeRunner:
    """Stands in for NightRunner's subprocess/hygiene layer."""

    def __init__(self, *, codes=None, logs=None, baseline=321.0, after=456.0, peak=999.0):
        self.codes = dict(codes or {})
        self.logs = dict(logs or {})
        self.baseline = baseline
        self.after = after
        self.peak = peak
        self.events: list[tuple[str, str]] = []

    def pre_hygiene(self, job, log_path):
        self.events.append(("pre", job.id))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"=== fake pre-hygiene {job.id}\n", encoding="utf-8")
        return {"baseline_mb": self.baseline, "note": ""}

    def run(self, job, log_path):
        self.events.append(("run", job.id))
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(self.logs.get(job.id, f"fake job {job.id}\n"))
        return int(self.codes.get(job.id, 0)), False

    def post_hygiene(self, job, log_path):
        self.events.append(("post", job.id))
        return {"after_mb": self.after, "peak_mb": self.peak, "note": ""}


def _rows(night_dir: Path) -> list[dict]:
    text = (night_dir / "summary.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# ------------------------------------------------------------------ (a) parse


def test_parse_night_preserves_order_ids_and_resolves_search_argv(tmp_path):
    path = _write_night(tmp_path, _night_doc(brief="examples/briefs/foo.yaml"))
    plan = night.load_night(path, repo_root=tmp_path)

    assert plan.night == NIGHT_NAME
    assert [job.id for job in plan.jobs] == ["phaseB_ladder", "t0__b1t__rosse_morph"]

    command, search = plan.jobs
    assert command.kind == "command"
    assert command.argv == (
        ".venv\\Scripts\\python.exe", "tools\\measure_fused_ceiling.py",
        "--mouth-res", "3.0")
    assert command.timeout_s == night.COMMAND_TIMEOUT_S

    assert search.kind == "search"
    assert search.argv[0] == str(tmp_path / ".venv" / "Scripts" / "hornlab-search.exe")
    assert search.argv[1:] == (
        "search",
        "--config", "examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml",
        "--budget", "1",
        "--mode", "screen",
        "--brief", "examples/briefs/foo.yaml",
    )
    assert search.budget == 1 and search.mode == "screen"
    assert search.timeout_s == night.SEARCH_TIMEOUT_S


def test_no_brief_flag_unless_the_job_sets_one(tmp_path):
    plan = night.load_night(_write_night(tmp_path), repo_root=tmp_path)
    assert "--brief" not in plan.jobs[1].argv


def test_invalid_night_file_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("night: two/jobs\njobs: []\n", encoding="utf-8")
    try:
        night.load_night(path, repo_root=tmp_path)
    except ValueError as exc:
        assert "night" in str(exc)
    else:  # pragma: no cover - the assertion above is the test
        raise AssertionError("invalid night name was accepted")


# ------------------------------------------------------------------ (b) dry-run


def test_dry_run_prints_jobs_and_launches_nothing(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(night, "REPO_ROOT", tmp_path)

    class BoomRunner:
        def __init__(self, *args, **kwargs):  # pragma: no cover - must not run
            raise AssertionError("dry-run must not construct the real runner")

    monkeypatch.setattr(night, "NightRunner", BoomRunner)

    rc = night.main(["--night", str(_write_night(tmp_path)), "--dry-run"])
    assert rc == 0

    out = capsys.readouterr().out
    assert "phaseB_ladder" in out
    assert "t0__b1t__rosse_morph" in out
    assert "kind=command" not in out          # the documented format is "[command]"
    assert "[command]" in out and "[search]" in out
    assert "--config" in out and "--budget" in out

    night_dir = tmp_path / "runs" / "nights" / NIGHT_NAME
    assert not (night_dir / "summary.jsonl").exists()
    assert not (night_dir / "SUMMARY.md").exists()


# ------------------------------------------------------------------ (c) failure isolation


def test_nonzero_job_is_recorded_and_the_next_job_still_runs(tmp_path):
    doc = {
        "night": NIGHT_NAME,
        "jobs": [
            {"id": "first", "kind": "command", "argv": ["echo", "first"]},
            {"id": "second", "kind": "command", "argv": ["echo", "second"]},
        ],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    runner = FakeRunner(codes={"first": 7})
    runs_root = tmp_path / "runs"

    results = night.run_night(
        plan, repo_root=tmp_path, runs_root=runs_root, runner=runner)

    assert [result.id for result in results] == ["first", "second"]
    assert [result.exit_code for result in results] == [7, 0]
    assert "exit code 7" in results[0].note
    assert results[1].note.startswith("ok")

    run_ids = [jid for action, jid in runner.events if action == "run"]
    assert run_ids == ["first", "second"]

    rows = _rows(runs_root / "nights" / NIGHT_NAME)
    assert [row["id"] for row in rows] == ["first", "second"]
    assert [row["exit_code"] for row in rows] == [7, 0]
    assert rows[0]["vram_baseline_mb"] == 321.0
    assert rows[0]["vram_after_mb"] == 456.0
    assert "peak 999 MiB" in rows[0]["note"]
    assert (runs_root / "nights" / NIGHT_NAME / "SUMMARY.md").is_file()


# ------------------------------------------------------------------ (d) accounting


def test_evals_come_from_search_ndjson_not_the_budget(tmp_path):
    run_dir = tmp_path / "runs" / "20261027T000000Z-screen-abc123"
    run_dir.mkdir(parents=True)
    (run_dir / "search.ndjson").write_text(
        '{"objective": 1.0}\n\n{"objective": 0.5}\n{"objective": 0.25}\n', encoding="utf-8")

    doc = {
        "night": NIGHT_NAME,
        "jobs": [{
            "id": "budget_99_but_three_rows",
            "kind": "search",
            "config": "examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml",
            "budget": 99,
            "mode": "screen",
        }],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    assert plan.jobs[0].budget == 99

    log_text = (
        "search: t0 mode screen, budget 99 new evaluations, 4 bounded keys, "
        f"output {run_dir}\n"
        "  seed J=1.0  best J=0.42 (improved on the seed); stop: budget\n"
    )
    runner = FakeRunner(logs={"budget_99_but_three_rows": log_text})

    results = night.run_night(
        plan, repo_root=tmp_path, runs_root=tmp_path / "runs", runner=runner)

    assert results[0].run_dir == str(run_dir)
    assert results[0].evals_ndjson == 3
    assert results[0].evals_ndjson != plan.jobs[0].budget
    assert results[0].best_J == 0.42

    row = _rows(tmp_path / "runs" / "nights" / NIGHT_NAME)[0]
    assert row["evals_ndjson"] == 3
    assert row["best_J"] == 0.42
    assert row["run_dir"] == str(run_dir)


def test_missing_summary_and_bad_run_dir_degrade_to_null(tmp_path):
    doc = {
        "night": NIGHT_NAME,
        "jobs": [{"id": "no_log_output", "kind": "search",
                  "config": "examples/foo.yaml", "budget": 1}],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    results = night.run_night(
        plan, repo_root=tmp_path, runs_root=tmp_path / "runs",
        runner=FakeRunner(logs={"no_log_output": "nothing useful\n"}))

    assert results[0].run_dir is None
    assert results[0].evals_ndjson == 0
    assert results[0].best_J is None
    assert "run dir not parsed" in results[0].note
    assert "best J not in log" in results[0].note


# ------------------------------------------------------------------ (e) --only


def test_only_filters_to_one_job(tmp_path):
    doc = {
        "night": NIGHT_NAME,
        "jobs": [
            {"id": "alpha", "kind": "command", "argv": ["echo", "alpha"]},
            {"id": "beta", "kind": "command", "argv": ["echo", "beta"]},
            {"id": "gamma", "kind": "command", "argv": ["echo", "gamma"]},
        ],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    runner = FakeRunner()

    results = night.run_night(
        plan, only="beta", repo_root=tmp_path,
        runs_root=tmp_path / "runs", runner=runner)

    assert [result.id for result in results] == ["beta"]
    assert [jid for action, jid in runner.events if action == "run"] == ["beta"]
    rows = _rows(tmp_path / "runs" / "nights" / NIGHT_NAME)
    assert [row["id"] for row in rows] == ["beta"]


# ------------------------------------------------------------------ pure parsers


def test_parse_run_dir_variants_and_best_j(tmp_path):
    r1 = tmp_path / "work" / "runs" / "r1"
    r2 = tmp_path / "work" / "runs" / "r2"
    assert night.parse_run_dir(f"search: x output {r1}\n") == r1
    assert night.parse_run_dir(f"search FAILED: boom (output: {r2})\n") == r2
    assert night.parse_run_dir(
        f"search ABORTED: boom (partial results in {r2})\n") == r2
    assert night.parse_run_dir("search: nothing here\n") is None
    assert night.parse_best_j("seed J=3.0  best J=1.25 (improved)") == 1.25
    assert night.parse_best_j("best J=9.0\nbest J=2.5\n") == 2.5
    assert night.parse_best_j("no summary") is None


def test_stale_lock_helpers(tmp_path):
    # 2026-10-28: a job killed on timeout leaves runs/.gpu.lock; the runner takes it over when the
    # recorded holder is gone instead of waiting out lock_wait_s and failing the next job.
    import os
    lock = tmp_path / ".gpu.lock"
    lock.write_text(json.dumps({"pid": 999999, "command": "x"}), encoding="utf-8")
    assert night._lock_holder_pid(lock) == 999999
    assert night._pid_alive(999999) is False
    assert night._pid_alive(os.getpid()) is True
    lock.write_text("not json", encoding="utf-8")
    assert night._lock_holder_pid(lock) is None
