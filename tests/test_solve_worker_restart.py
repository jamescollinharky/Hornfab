"""Worker recycling inside one solve sweep (MEH contracted-band fix, 2026-10-31).

The 41-frequency 120-12 kHz sweep grows the persistent BEAT host past the 8 GB card's ceiling
(measured: CUDA error 719 at 7,908/8,188 MiB after completing the sweep). ``worker_restart_every``
recycles the host between chunks. This test pinpoints the loop; it uses no Julia and no GPU.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import hornlab_beat_bem as beatlib

from hornlab_search.solve import beat as beatmod
from hornlab_search.solve.beat import BeatBackend
from hornlab_search.types import ObservationSpec, SolveSpec


def _backend():
    return BeatBackend("cuda", track_vram=False)


def _spec(freqs, restart):
    return SolveSpec(
        mode="screen", freqs_hz=tuple(freqs), backend="beat_cuda",
        observation=ObservationSpec(distance_m=2.0, angle_count=5, balloon=False, balloon_points=0),
        gmres_tol=1e-5, extra={"worker_restart_every": restart} if restart else {},
    )


@pytest.fixture
def loop(monkeypatch):
    calls, recycled, marked = [], [], []
    monkeypatch.setattr(beatlib, "solve_frequencies",
                        lambda path, g, cfg: calls.append(tuple(g)) or tuple(g))
    monkeypatch.setattr(beatmod.worker, "shutdown",
                        lambda **kw: recycled.append(tuple(kw.items())))
    monkeypatch.setattr(beatmod.worker, "mark_cold", lambda name=None: marked.append(name))
    monkeypatch.setattr(beatmod, "_stack", lambda raws, freqs: {"calls": raws, "freqs": tuple(freqs)})
    return calls, recycled, marked


def test_every_frequency_is_one_call_and_the_stack_is_complete(loop):
    calls, _, _ = loop
    mesh = SimpleNamespace(path="m.msh")
    freqs = [100.0, 200.0, 300.0]
    out = _backend().solve_raw(mesh, _spec(freqs, 0), cfg=object())
    assert calls == [(100.0,), (200.0,), (300.0,)]
    assert out["freqs"] == tuple(freqs)


def test_the_host_is_recycled_every_n_calls_and_never_after_the_last(loop):
    calls, recycled, marked = loop
    mesh = SimpleNamespace(path="m.msh")
    freqs = [100.0 * (k + 1) for k in range(10)]
    _backend().solve_raw(mesh, _spec(freqs, 4), cfg=object())
    assert len(calls) == 10
    assert len(recycled) == 2                 # after calls 4 and 8, not after 10
    assert len(marked) == 2 and set(marked) == {"beat_cuda"}
    assert recycled[0] == (("verify", True),)


def test_absent_restart_keeps_one_host(loop):
    calls, recycled, marked = loop
    mesh = SimpleNamespace(path="m.msh")
    _backend().solve_raw(mesh, _spec([100.0, 200.0, 300.0, 400.0], 0), cfg=object())
    assert len(calls) == 4 and recycled == [] and marked == []
