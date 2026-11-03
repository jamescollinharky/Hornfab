"""Allow-listed CLI launcher for the GUI.

Every job is an ordinary ``hornlab-search`` command run as a subprocess, so the GPU lock, hygiene, failure
cache, dataset records and run folders are exactly the CLI's. Nothing here builds a shell string: argv is
assembled from validated fields only. Logs go to ``runs/gui_jobs/<id>.log``.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from . import data as D

GPU_KINDS = {"run", "search", "campaign", "verify"}    # campaign dry-run tier is not a GPU job
TIERS = {"dry-run", "screen", "compare"}
SEARCH_MODES = ("screen", "verify", "final")           # cli.py's `search --mode` choices
RESTART_MODES = ("ipop", "bipop", "off")               # cli.py's `search --restarts-mode`
BACKENDS = ("beat_cuda", "beat_metal", "beat_cpu", "bempp_cpu")  # cli.py `--backend`
RESTARTS_MAX_CAP = 64                                  # mirrors config._validate_restarts
MAX_EVALS_CAP = 1_000_000                              # GUI sanity cap for --max-evals
FAMILIES = re.compile(r"^[a-z0-9_]+(,[a-z0-9_]+)*$")
CLI_BOOT = "import sys; from hornlab_search.cli import main; sys.exit(main(sys.argv[1:]))"


def auto_backend() -> str | None:
    """Platform-derived Metal default, with no hardware probing and no process spawns.

    Returns ``"beat_metal"`` only on Apple Silicon (``darwin`` + ``arm64``/``aarch64``); ``None``
    everywhere else (Windows/Linux/Intel Mac). ``None`` means "leave the config alone": the config's
    own ``solve.backend`` wins, so a silent backend swap can never change solve provenance.
    """
    if sys.platform != "darwin":
        return None
    if platform.machine().lower() not in {"arm64", "aarch64"}:
        return None
    return "beat_metal"


class JobError(ValueError):
    """A launch request that is refused (bad argument, GPU busy, ...); the message is shown to the user."""


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


@dataclass
class Job:
    id: str
    kind: str
    argv: list[str]
    log: Path
    gpu: bool
    started: str = field(default_factory=_now)
    ended: str | None = None
    status: str = "running"
    returncode: int | None = None
    proc: subprocess.Popen | None = None

    def view(self, tail: int = 40) -> dict:
        return {"id": self.id, "kind": self.kind, "argv": self.argv, "gpu": self.gpu,
                "command": "hornlab-search " + " ".join(_quote(a) for a in self.argv),
                "status": self.status, "returncode": self.returncode,
                "started": self.started, "ended": self.ended, "log_tail": D.tail_text(self.log, tail)}


def _quote(a: str) -> str:
    return f'"{a}"' if (" " in a or not a) else a


class JobManager:
    QUEUE_POLL_S = 5.0                     # lazy pump thread: how often a queued resume re-checks the GPU

    def __init__(self, root: Path, runs: Path):
        self.root, self.runs = root.resolve(), runs.resolve()
        self.dir = self.runs / "gui_jobs"
        self.jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pump_thread: threading.Thread | None = None
        self._load_past()

    def _load_past(self, keep: int = 30) -> None:
        """Jobs from earlier GUI sessions (their logs survive a restart). Their final state is not
        known to this process: status 'ended (GUI restarted)' unless the log says otherwise."""
        if not self.dir.is_dir():
            return
        for meta in sorted(self.dir.glob("*.json"))[-keep:]:
            m = D._read_json(meta) or {}
            jid = meta.stem
            if not m or jid in self.jobs:
                continue
            log = self.dir / f"{jid}.log"
            status = m.get("status")
            if status in (None, "running"):              # the GUI stopped before the job did
                status = "ended (GUI restarted)"
            elif status == "queued":                     # never started; this session must not start it
                status = "cancelled (GUI restarted before start)"
            job = Job(jid, m.get("kind", "?"), list(m.get("argv") or []), log, bool(m.get("gpu")),
                      started=m.get("started") or "", ended=m.get("ended"), status=status,
                      returncode=m.get("returncode"))
            self.jobs[jid] = job

    # ------------------------------------------------------------------ validation

    def _repo_file(self, rel: str, suffix: str = ".yaml") -> str:
        if not isinstance(rel, str) or not rel.strip():
            raise JobError("a config/brief path is required")
        p = (self.root / rel.strip()).resolve()
        if self.root not in p.parents or p.suffix.lower() != suffix or not p.is_file():
            raise JobError(f"not a {suffix} file inside the repository: {rel!r}")
        return p.relative_to(self.root).as_posix()

    def _run_id(self, rid: str) -> str:
        if not isinstance(rid, str) or not D.RUN_ID.match(rid) or not (self.runs / rid).is_dir():
            raise JobError(f"unknown run: {rid!r}")
        return str(self.runs / rid)

    def _backend_argv(self, a: dict) -> list[str]:
        """Explicit ``backend`` arg, else the platform-derived Metal default (Apple Silicon only)."""
        b = a.get("backend")
        if b in (None, ""):
            b = auto_backend()
        if b in (None, ""):
            return []
        if b not in BACKENDS:
            raise JobError(f"backend must be one of {list(BACKENDS)}")
        return ["--backend", str(b)]

    @staticmethod
    def _int(v, lo: int, hi: int, name: str) -> str:
        try:
            i = int(v)
        except (TypeError, ValueError):
            raise JobError(f"{name} must be an integer") from None
        if not lo <= i <= hi:
            raise JobError(f"{name} must be in [{lo}, {hi}]")
        return str(i)

    def build_argv(self, kind: str, a: dict) -> tuple[list[str], bool]:
        """(argv after 'hornlab-search', needs_gpu) for an allow-listed kind, or JobError."""
        a = a or {}
        brief = ["--brief", self._repo_file(a["brief"])] if a.get("brief") else []
        seed = ["--cma-seed", self._int(a["cma_seed"], 0, 2**31 - 1, "cma_seed")] if a.get("cma_seed") not in (None, "") else []
        if kind == "dry-run":
            return ["run", "--config", self._repo_file(a.get("config")), "--dry-run", *brief], False
        if kind == "run":
            argv = ["run", "--config", self._repo_file(a.get("config")), *brief, *seed]
            argv += self._backend_argv(a)
            return argv, True
        if kind == "search":
            # Resume is an ADDITIVE option on the same kind, so GPU classification, the one-GPU
            # launch lock, cancel and past-job reload stay exactly the search kind's. The CLI's
            # ``--resume`` takes a DIRECTORY (cli.py:641-646,1322), not a bare flag: a GUI run id
            # is resolved to runs/<id> with the same validation every other run arg uses. On a
            # resume the config is optional in the CLI (run_dir/config.yaml is used when absent),
            # so only an explicit config is emitted. A resume omits --budget unless given, letting
            # the CLI use the run's own config budget; a fresh search keeps the 60 default.
            resume = a.get("resume")
            if resume is True:
                raise JobError("resume needs a run id: the CLI's --resume takes a run directory, "
                               "so a bare true cannot identify the run")
            resume_dir = (self._run_id(resume) if resume not in (None, "", False) else None)
            if a.get("config"):
                cfg = self._repo_file(a["config"])
            elif resume_dir is None:
                raise JobError("a config/brief path is required")   # same refusal as _repo_file
            else:
                cfg = None
            argv = ["search"]
            if cfg is not None:
                argv += ["--config", cfg]
            budget = a.get("budget")
            if resume_dir is None:
                argv += ["--budget", self._int(60 if budget in (None, "") else budget,
                                               1, 5000, "budget")]
            elif budget not in (None, ""):
                argv += ["--budget", self._int(budget, 1, 5000, "budget")]
            if a.get("max_evals") not in (None, ""):
                argv += ["--max-evals", self._int(a["max_evals"], 1, MAX_EVALS_CAP, "max_evals")]
            mode = a.get("mode")
            if mode not in (None, ""):
                if mode not in SEARCH_MODES:
                    raise JobError(f"mode must be one of {list(SEARCH_MODES)}")
                argv += ["--mode", mode]
            if resume_dir is not None:
                argv += ["--resume", resume_dir]
            if a.get("allow_config_change"):
                if resume_dir is None:
                    raise JobError("allow_config_change only applies to a resume")
                argv.append("--allow-config-change")
            # WP11a restarts override (Launch / Compose). Absent = leave the config YAML alone.
            rmode = a.get("restarts_mode")
            rmax = a.get("restarts_max")
            if rmode not in (None, ""):
                if rmode not in RESTART_MODES:
                    raise JobError(f"restarts_mode must be one of {list(RESTART_MODES)}")
                argv += ["--restarts-mode", str(rmode)]
                if rmode == "off" and rmax not in (None, ""):
                    raise JobError("restarts_max is meaningless when restarts_mode is off")
                if rmode in ("ipop", "bipop"):
                    # Default 2 when the UI leaves max blank — mirrors the CLI default.
                    argv += ["--restarts-max",
                             self._int(2 if rmax in (None, "") else rmax,
                                       0, RESTARTS_MAX_CAP, "restarts_max")]
            elif rmax not in (None, ""):
                raise JobError("restarts_max requires restarts_mode (ipop|bipop|off)")
            argv = [*argv, *brief, *seed]
            argv += self._backend_argv(a)
            return argv, True
        if kind == "campaign":
            f = a.get("families", "")
            fams = (",".join(str(x) for x in f) if isinstance(f, (list, tuple)) else str(f)).replace(" ", "") or "all"
            if not FAMILIES.match(fams):
                raise JobError("families: comma-separated names or groups (letters, digits, _)")
            tier = a.get("tier", "dry-run")
            if tier not in TIERS:
                raise JobError(f"tier must be one of {sorted(TIERS)}")
            if not brief:
                raise JobError("campaign needs a brief")
            return ["campaign", *brief, "--families", fams, "--tier", tier], tier != "dry-run"
        if kind == "export-step":
            return ["export-step", "--run", self._run_id(a.get("run")),
                    "--top", self._int(a.get("top", 3), 1, 10, "top")], False
        if kind == "verify":
            # G-1: re-solve this run's top designs at verify fidelity; GPU (one-GPU lock via launch()).
            return ["verify", "--run", self._run_id(a.get("run")),
                    "--top", self._int(a.get("top", 5), 1, 25, "top"), *brief], True
        if kind == "report":
            return ["report", self._run_id(a.get("run"))], False
        raise JobError(f"unknown job kind: {kind!r}")

    # ------------------------------------------------------------------ lifecycle

    def gpu_busy(self) -> str | None:
        from hornlab_search.search.gpulock import _lock_path, _pid_alive, _read_lock
        lk = _read_lock(_lock_path(self.runs))
        if lk and lk.get("pid") and _pid_alive(int(lk["pid"])):
            return (f'GPU busy: {lk.get("user", "?")} running "{lk.get("command", "?")}" '
                    f'(pid {lk["pid"]}) since {lk.get("start_time", "?")}')
        return None

    @staticmethod
    def _is_resume_search(kind: str, args: dict) -> bool:
        """Only a search resume may wait in the GPU queue; every fresh launch keeps the hard refusal."""
        resume = (args or {}).get("resume")
        return kind == "search" and resume not in (None, "", False, True)

    def launch(self, kind: str, args: dict) -> Job:
        argv, gpu = self.build_argv(kind, args)
        with self._lock:
            if gpu:
                # Strict FIFO: a continuation already waiting has first claim on the GPU even when
                # the lock looks free (the pump may simply not have ticked yet), so a fresh launch
                # must never jump it and a later resume joins the queue behind it.
                if any(j.status == "queued" for j in self.jobs.values()):
                    if not self._is_resume_search(kind, args):
                        raise JobError("a queued continuation is waiting — it starts when the GPU is free")
                    job = self._new_job(kind, argv, gpu, status="queued")
                    self.jobs[job.id] = job
                    self._save_meta(job)                   # started = enqueue time; no log yet
                    self._ensure_pump_locked()
                    return job
                busy = ("a GPU job started from this GUI is still running"
                        if any(j.gpu and j.status == "running" for j in self.jobs.values())
                        else self.gpu_busy())
                if busy:
                    if not self._is_resume_search(kind, args):
                        raise JobError(busy)
                    job = self._new_job(kind, argv, gpu, status="queued")
                    self.jobs[job.id] = job
                    self._save_meta(job)                   # started = enqueue time; no log yet
                    self._ensure_pump_locked()
                    return job
            job = self._new_job(kind, argv, gpu)
            self.jobs[job.id] = job
            self._start_locked(job)
            return job

    def _new_job(self, kind: str, argv: list[str], gpu: bool, status: str = "running") -> Job:
        self.dir.mkdir(parents=True, exist_ok=True)
        jid = _dt.datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        return Job(jid, kind, argv, self.dir / f"{jid}.log", gpu, status=status, proc=None)

    def _start_locked(self, job: Job) -> None:
        """Spawn one job (the caller holds ``_lock``). A Popen failure is recorded, never raised: the
        pump path must survive it and move on to the next queued job."""
        fh = None
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            fh = job.log.open("w", encoding="utf-8")
            kw = {"cwd": str(self.root), "stdout": fh, "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL,
                  "env": {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}}
            if os.name == "nt":
                kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kw["start_new_session"] = True
            proc = subprocess.Popen([sys.executable, "-c", CLI_BOOT, *job.argv], **kw)
        except (OSError, subprocess.SubprocessError):
            if fh is not None:
                try:
                    fh.close()
                except OSError:
                    pass
            job.status, job.ended = "failed", _now()
            self._save_meta(job)
            return
        job.status, job.started, job.proc = "running", _now(), proc
        self._save_meta(job)
        threading.Thread(target=self._wait, args=(job, fh), daemon=True).start()

    def _wait(self, job: Job, fh) -> None:
        rc = job.proc.wait()
        try:
            fh.close()
        except OSError:
            pass
        with self._lock:
            job.returncode, job.ended = rc, _now()
            if job.status == "running":
                job.status = "done" if rc == 0 else "failed"
            self._save_meta(job)
            self._pump_locked()                            # the GPU is free: start the next queued job now

    # ------------------------------------------------------------------ queue

    def pump(self) -> Job | None:
        """Deterministic trigger for the same check the lazy thread runs (tests call this)."""
        with self._lock:
            return self._pump_locked()

    def _pump_locked(self) -> Job | None:
        if any(j.gpu and j.status == "running" for j in self.jobs.values()):
            return None
        if self.gpu_busy():
            return None
        job = next((j for j in self.jobs.values() if j.status == "queued"), None)   # dict = insertion order
        if job is None:
            return None
        self._start_locked(job)
        return job

    def _ensure_pump_locked(self) -> None:
        if self._pump_thread is None or not self._pump_thread.is_alive():
            self._pump_thread = threading.Thread(target=self._pump_loop, daemon=True)
            self._pump_thread.start()

    def _pump_loop(self) -> None:
        while True:
            time.sleep(self.QUEUE_POLL_S)
            with self._lock:
                if not any(j.status == "queued" for j in self.jobs.values()):
                    self._pump_thread = None
                    return
                try:
                    self._pump_locked()
                except Exception:  # noqa: BLE001 - never let the pump thread die while work is queued
                    pass

    def queue_position(self, job: Job) -> int:
        with self._lock:
            return self._position_locked(job)

    def _position_locked(self, job: Job) -> int:
        if job.status != "queued":
            return 0
        n = 0
        for j in self.jobs.values():
            if j.status == "queued":
                n += 1
                if j is job:
                    return n
        return 0

    def view(self, jid: str, tail: int = 40) -> dict:
        with self._lock:
            job = self.jobs.get(jid)
            if job is None:
                raise KeyError(jid)
            return {**job.view(tail), "queue_position": self._position_locked(job)}

    def _save_meta(self, job: Job) -> None:
        try:
            (self.dir / f"{job.id}.json").write_text(json.dumps(
                {k: v for k, v in job.view(0).items() if k != "log_tail"}), encoding="utf-8")
        except OSError:
            pass

    def cancel(self, jid: str, only_queued: bool = False) -> Job:
        with self._lock:
            job = self.jobs.get(jid)
            if job is None:
                raise JobError(f"unknown job {jid!r}")
            if only_queued and job.status != "queued":
                # The UI's queued card/list is poll-driven: the job may have auto-started between
                # the poll and the click. A queued-only cancel must never kill a running job.
                raise JobError("this request already started — use its Stop control")
            if job.status == "queued":
                job.status, job.ended = "cancelled", _now()
                self._save_meta(job)
                return job                                  # it never started: no kill, no gpu-clean
            if job.status != "running" or job.proc is None:
                return job
            job.status = "cancelled"
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(job.proc.pid), "/T", "/F"], capture_output=True)
            else:
                try:
                    os.killpg(job.proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            if job.gpu:
                try:
                    job.proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
                self.run_cli(["gpu-clean"], timeout=120)   # same cleanup the CLI uses; lock holder is now dead
            return job

    def stop_external(self) -> dict:
        """Owner 2026-10-25: kill the run that holds the GPU lock even when this GUI did not start
        it. The lock file is this repo's own (pid + command recorded by whoever is using our GPU),
        so the kill targets exactly that recorded pid (+ its child tree) and then a gpu-clean pass
        -- never an arbitrary pid. Refuses when a GUI-started GPU job is running: that is the Stop
        control's path (cancel), and the two paths must never race."""
        running = [j for j in self.jobs.values() if j.gpu and j.status == "running"]
        if running:
            raise JobError("a GPU job started from this GUI is running — use its Stop control instead")
        from hornlab_search.search.gpulock import _lock_path, _pid_alive, _read_lock
        lk = _read_lock(_lock_path(self.runs))
        if not (lk and lk.get("pid") and _pid_alive(int(lk["pid"]))):
            return {"ok": False, "error": "no live GPU lock to stop"}
        pid = int(lk["pid"])
        if pid == os.getpid():
            raise JobError("refusing to kill this GUI's own process")
        cmd = lk.get("command", "?")
        self._kill_tree(pid)
        rc, out = self.run_cli(["gpu-clean"], timeout=120)   # the holder is dead; same cleanup cancel() uses
        return {"ok": True, "killed": pid, "command": cmd, "gpu_clean_rc": rc, "gpu_clean_tail": out[-200:]}

    def _kill_tree(self, pid: int) -> None:
        """Kill one pid + its child tree (the GPU-lock holder and the Julia children it spawned). A
        method of its own so tests can monkeypatch the kill and assert on the pid, never really
        killing anything. POSIX: SIGTERM to the recorded pid (its own children are not in a known
        process group, so the tree kill is best-effort there; the Windows path is the exact one)."""
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def list(self) -> list[dict]:
        with self._lock:
            return [{**j.view(12), "queue_position": self._position_locked(j)}
                    for j in sorted(self.jobs.values(), key=lambda j: j.id, reverse=True)]

    def run_cli(self, argv: list[str], timeout: int = 120) -> tuple[int, str]:
        """A short, synchronous CLI call (families, gpu-clean); returns (exit code, combined output)."""
        p = subprocess.run([sys.executable, "-c", CLI_BOOT, *argv], cwd=str(self.root), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        return p.returncode, (p.stdout or "") + (p.stderr or "")
