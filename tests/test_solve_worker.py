"""solve/worker.py: host discovery, stale-host clearing, verified release, handlers. Offline.

Everything goes through a fake process table: no Julia, no taskkill, no nvidia-smi.
"""
from __future__ import annotations

import logging
import signal

import pytest

from hornlab_search.solve import worker
from hornlab_search.solve.worker import ProcInfo, WorkerReleaseError

HOSTCMD = "python.exe -m hornlab_beat_bem.worker_host --key C:\\w\\{k}.key.json --dir C:\\w"


class Table:
    """A mutable fake process table with a kill that removes the whole tree."""

    def __init__(self, procs):
        self.procs = list(procs)
        self.killed: list[int] = []
        self.kill_works = True
        self.listed = 0

    def lister(self):
        self.listed += 1
        return list(self.procs)

    def killer(self, pid):
        self.killed.append(pid)
        if not self.kill_works:
            return False
        dead = {pid}
        changed = True
        while changed:
            changed = False
            for p in self.procs:
                if p.ppid in dead and p.pid not in dead:
                    dead.add(p.pid)
                    changed = True
        self.procs = [p for p in self.procs if p.pid not in dead]
        return True

    def remove(self, pids):
        self.procs = [p for p in self.procs if p.pid not in set(pids)]


def host(base_pid: int, key: str, parent: int = 1):
    """One Windows BEAT host: venv launcher -> system python -> julialauncher -> julia.exe."""
    cmd = HOSTCMD.format(k=key)
    return [
        ProcInfo(base_pid, parent, "python.exe", cmd),
        ProcInfo(base_pid + 1, base_pid, "python.exe", cmd),
        ProcInfo(base_pid + 2, base_pid + 1, "julialauncher.exe",
                 r"julia.EXE --project=C:\v\hornlab_beat_bem\julia solver.jl --worker"),
        ProcInfo(base_pid + 3, base_pid + 2, "julia.exe", r"C:\julia\bin\julia.exe"),
    ]


BYSTANDERS = [
    ProcInfo(4, 0, "System", ""),
    ProcInfo(900, 4, "explorer.exe", "explorer.exe"),
    ProcInfo(901, 900, "julia.exe", r"C:\julia\bin\julia.exe"),                        # someone else's julia
    ProcInfo(902, 900, "python.exe", "python.exe -m pytest tests"),
]
nosleep = lambda s: None  # noqa: E731


def test_host_roots_find_only_the_top_of_each_host_and_ignore_bystanders():
    t = Table(BYSTANDERS + host(100, "a") + host(200, "b"))
    roots = worker.beat_host_roots(t.lister())
    assert [r.pid for r in roots] == [100, 200]
    assert worker.host_tree_pids(t.procs) == {100, 101, 102, 103, 200, 201, 202, 203}
    assert 901 not in worker.host_tree_pids(t.procs)


def test_orphaned_julialauncher_without_parent_is_found():
    orphan = ProcInfo(300, 99999, "julialauncher.exe", r"julia.EXE --project=C:\v\hornlab_beat_bem\julia solver.jl --worker")
    child = ProcInfo(301, 300, "julia.exe", r"C:\julia\bin\julia.exe")
    t = Table(BYSTANDERS + [orphan, child])
    assert [r.pid for r in worker.beat_host_roots(t.lister())] == [300]
    assert {300, 301} <= worker.host_tree_pids(t.procs)


def test_orphaned_posix_julia_solver_worker_is_found():
    """Linux/macOS persistent host: bare ``julia`` + solver.jl --worker, parent gone."""
    orphan = ProcInfo(
        400, 99999, "julia",
        "/home/u/.julia/juliaup/julia --project=/opt/venv/lib/python3.12/site-packages/"
        "hornlab_beat_bem/julia_cuda /opt/venv/lib/python3.12/site-packages/"
        "hornlab_beat_bem/julia/solver.jl --worker",
    )
    bystander = ProcInfo(401, 1, "julia", "/usr/bin/julia -e '1+1'")  # not our package
    t = Table(BYSTANDERS + [orphan, bystander])
    assert [r.pid for r in worker.beat_host_roots(t.lister())] == [400]
    assert 401 not in worker.host_tree_pids(t.procs)


def test_no_hosts_means_nothing_to_clear():
    t = Table(BYSTANDERS)
    assert worker.clear_stale_hosts(lister=t.lister, killer=t.killer, vram_probe=lambda: 9999, sleep=nosleep) == []
    assert t.killed == []


def test_one_host_on_a_quiet_gpu_is_kept_for_adoption():
    t = Table(BYSTANDERS + host(100, "a"))
    assert worker.clear_stale_hosts(lister=t.lister, killer=t.killer, vram_probe=lambda: 2200.0, sleep=nosleep) == []
    assert t.killed == [] and len(t.procs) == len(BYSTANDERS) + 4


def test_one_host_with_unknown_vram_is_kept():
    t = Table(host(100, "a"))
    assert worker.clear_stale_hosts(lister=t.lister, killer=t.killer, vram_probe=lambda: None, sleep=nosleep) == []


def test_more_than_one_host_clears_all_of_them_but_not_bystanders():
    t = Table(BYSTANDERS + host(100, "a") + host(200, "b"))
    killed = worker.clear_stale_hosts(lister=t.lister, killer=t.killer, vram_probe=lambda: 1000.0, sleep=nosleep)
    assert killed == [100, 200] and t.killed == [100, 200]
    assert {p.pid for p in t.procs} == {p.pid for p in BYSTANDERS}            # bystander julia survives
    assert worker.list_beat_hosts(t.lister) == []


def test_one_host_but_high_vram_baseline_is_cleared():
    t = Table(host(100, "a"))
    assert worker.clear_stale_hosts(lister=t.lister, killer=t.killer, vram_probe=lambda: 6500.0,
                                    vram_high_mib=4000, sleep=nosleep) == [100]


def test_force_clears_a_single_quiet_host():
    t = Table(host(100, "a"))
    assert worker.clear_stale_hosts(lister=t.lister, killer=t.killer, vram_probe=lambda: 10.0, force=True,
                                    sleep=nosleep) == [100]


def test_a_host_that_survives_the_kill_raises():
    t = Table(host(100, "a") + host(200, "b"))
    t.kill_works = False
    with pytest.raises(WorkerReleaseError, match="survived"):
        worker.clear_stale_hosts(lister=t.lister, killer=t.killer, timeout_s=0.0, sleep=nosleep)


# ------------------------------------------------------------------ verified release


def test_shutdown_verifies_when_the_library_stops_the_host():
    t = Table(BYSTANDERS + host(100, "a"))
    forced = worker.shutdown(lister=t.lister, killer=t.killer, sleep=nosleep,
                             stop_fn=lambda: t.remove([100, 101, 102, 103]))
    assert forced == [] and t.killed == []
    assert worker.list_beat_hosts(t.lister) == []


def test_shutdown_kills_a_host_the_library_failed_to_stop_and_verifies():
    t = Table(BYSTANDERS + host(100, "a"))
    forced = worker.shutdown(lister=t.lister, killer=t.killer, sleep=nosleep, timeout_s=0.0,
                             stop_fn=lambda: None)                         # shutdown_workers did nothing
    assert forced == [100] and t.killed == [100]
    assert worker.list_beat_hosts(t.lister) == []
    assert {p.pid for p in t.procs} == {p.pid for p in BYSTANDERS}


def test_shutdown_raises_if_the_host_cannot_be_killed():
    t = Table(host(100, "a"))
    t.kill_works = False
    with pytest.raises(WorkerReleaseError, match="still alive"):
        worker.shutdown(lister=t.lister, killer=t.killer, sleep=nosleep, timeout_s=0.0, stop_fn=lambda: None)


def test_shutdown_survives_the_library_raising():
    t = Table(host(100, "a"))

    def boom():
        raise RuntimeError("worker refused")
    forced = worker.shutdown(lister=t.lister, killer=t.killer, sleep=nosleep, timeout_s=0.0, stop_fn=boom)
    assert forced == [100] and worker.list_beat_hosts(t.lister) == []


def test_shutdown_with_nothing_running_is_a_no_op():
    t = Table(BYSTANDERS)
    assert worker.shutdown(lister=t.lister, killer=t.killer, sleep=nosleep, stop_fn=lambda: None) == []


def test_shutdown_resets_warm_state():
    worker._WARM.add("beat_cuda")
    worker.shutdown(lister=Table([]).lister, killer=lambda p: True, sleep=nosleep, stop_fn=lambda: None)
    assert not worker.is_warm("beat_cuda")


# ------------------------------------------------------------------ warm / solve-time log


class CountingBackend:
    def __init__(self, name="beat_cuda"):
        self.name = name
        self.n = 0

    def warm(self):
        self.n += 1


def test_warm_is_idempotent_per_backend_and_clears_stale_hosts_first(monkeypatch):
    worker.mark_cold()
    order = []
    monkeypatch.setattr(worker, "clear_stale_hosts", lambda **k: order.append("clear") or [])
    be = CountingBackend()
    be.warm = lambda: order.append("warm")
    worker.warm(be)
    worker.warm(be)
    assert order == ["clear", "warm"] and worker.is_warm("beat_cuda")
    other = CountingBackend("beat_cpu")
    other.warm = lambda: order.append("warm2")
    worker.warm(other)
    assert order == ["clear", "warm", "clear", "warm2"]
    worker.mark_cold()


def test_warm_does_not_look_for_beat_hosts_for_a_non_beat_backend(monkeypatch):
    worker.mark_cold()
    monkeypatch.setattr(worker, "clear_stale_hosts", lambda **k: pytest.fail("must not clear"))
    be = CountingBackend("bempp_cpu")
    worker.warm(be)
    assert be.n == 1
    worker.mark_cold()


def test_first_and_second_solve_times_are_logged_at_info(caplog):
    worker.mark_cold()
    t = Table(BYSTANDERS + host(100, "a"))
    with caplog.at_level(logging.INFO, logger="hornlab_search.solve.worker"):
        worker.note_solve_seconds("beat_cuda", 27.2, lister=t.lister)
        worker.note_solve_seconds("beat_cuda", 1.4, lister=t.lister)
    text = caplog.text
    assert "first solve: 27.20 s (host pid 100)" in text and "second solve: 1.40 s" in text
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    worker.mark_cold()


def test_a_host_that_changed_between_solve_1_and_2_warns_not_reused(caplog):
    worker.mark_cold()
    t = Table(host(100, "a"))
    with caplog.at_level(logging.INFO, logger="hornlab_search.solve.worker"):
        worker.note_solve_seconds("beat_cuda", 30.0, lister=t.lister)
        t.procs = host(200, "a")                       # the worker was restarted
        worker.note_solve_seconds("beat_cuda", 25.0, lister=t.lister)
    assert any("not being reused" in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)
    worker.mark_cold()


def test_no_host_found_at_the_second_solve_warns(caplog):
    worker.mark_cold()
    t = Table(host(100, "a"))
    with caplog.at_level(logging.INFO, logger="hornlab_search.solve.worker"):
        worker.note_solve_seconds("beat_cuda", 3.0, lister=t.lister)
        t.procs = []
        worker.note_solve_seconds("beat_cuda", 2.8, lister=t.lister)
    assert any("not being reused" in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)
    worker.mark_cold()


def test_a_long_solve_twice_on_the_same_host_does_not_warn(caplog):
    """A 19 s CPU solve twice must not be mistaken for a cold start paid twice."""
    worker.mark_cold()
    t = Table(host(100, "a"))
    with caplog.at_level(logging.INFO, logger="hornlab_search.solve.worker"):
        worker.note_solve_seconds("beat_cpu", 18.3, lister=t.lister)
        worker.note_solve_seconds("beat_cpu", 19.2, lister=t.lister)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    worker.mark_cold()


def test_non_beat_backends_never_read_the_process_table(caplog):
    worker.mark_cold()
    boom = lambda: pytest.fail("must not list processes")          # noqa: E731
    worker.note_solve_seconds("bempp_cpu", 10.0, lister=boom)
    worker.note_solve_seconds("bempp_cpu", 10.0, lister=boom)
    worker.mark_cold()


def test_recover_after_failure_drops_warm_state_and_force_clears(monkeypatch):
    worker._WARM.add("beat_cuda")
    t = Table(host(100, "a"))
    worker.recover_after_failure("beat_cuda", lister=t.lister, killer=t.killer)
    assert not worker.is_warm("beat_cuda") and t.killed == [100]


# ------------------------------------------------------------------ handlers, vram monitor


def test_install_handlers_registers_atexit_and_sigint_and_is_idempotent(monkeypatch):
    registered = []
    monkeypatch.setattr(worker.atexit, "register", lambda fn: registered.append(fn))
    prev = signal.getsignal(signal.SIGINT)
    worker.uninstall_handlers()
    try:
        worker.install_handlers()
        worker.install_handlers()
        assert registered == [worker._atexit_detach]
        assert signal.getsignal(signal.SIGINT) is worker._sigint
    finally:
        worker.uninstall_handlers()
        signal.signal(signal.SIGINT, prev)


def test_sigint_handler_detaches_then_reraises_keyboardinterrupt(monkeypatch):
    calls = []
    monkeypatch.setattr(worker, "detach", lambda: calls.append("detach"))
    monkeypatch.setattr(worker, "_PREV_SIGINT", signal.default_int_handler)
    with pytest.raises(KeyboardInterrupt):
        worker._sigint(signal.SIGINT, None)
    assert calls == ["detach"]


def test_detach_is_safe_with_nothing_running(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", None)         # not importable
    worker.detach()                                                    # must not raise


def test_vram_monitor_reports_baseline_and_peak_delta():
    vals = iter([300.0, 900.0, 2500.0, 1800.0] + [1800.0] * 50)
    m = worker.VramMonitor(interval_s=0.01, probe=lambda: next(vals))
    with m:
        import time
        time.sleep(0.08)
    assert m.baseline_mib == 300.0
    assert m.peak_mib == 2500.0 and m.peak_delta_mib == 2200.0


def test_vram_monitor_without_nvidia_smi_is_none_not_zero():
    m = worker.VramMonitor(interval_s=0.01, probe=lambda: None)
    with m:
        pass
    assert m.baseline_mib is None and m.peak_mib is None and m.peak_delta_mib is None
