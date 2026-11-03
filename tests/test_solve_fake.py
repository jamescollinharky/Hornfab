"""The Backend protocol is usable, and the beat adapter is correct against a fake beat module.

Nothing here needs hornlab_beat_bem, Julia or a GPU: ``hornlab_beat_bem`` is replaced in
``sys.modules`` by a small fake whose ``solve_frequencies`` returns SolveResult-shaped objects
built from the conftest cardioid. That exercises the REAL adapter code: per-frequency looping,
stacking, config construction, ``_to_response`` assertions, failure mapping, VRAM monitor.
"""
from __future__ import annotations

import dataclasses
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import cardioid_mag, make_fake_response
from hornlab_search.config import solve_spec
from hornlab_search.constants import C_AIR, REF_P, RHO_AIR
from hornlab_search.solve import base, worker
from hornlab_search.solve import beat as beat_mod
from hornlab_search.solve.base import Backend, ResponseSanityError, arc_angles_deg
from hornlab_search.types import MeshResult, Response, SolveOutcome

MESH = MeshResult(path="fake.msh", n_triangles=2400, n_dof=1234, quadrants="1",
                  symmetry_plane="yz+xz", res_mm={"throat": 3.0, "mouth": 6.0, "rear": 6.0},
                  bbox_m=(0.0, 0.0, 0.0, 0.2, 0.15, 0.3), seconds=0.1)
Z_TRUE = lambda f: 1.1 + 0.4j * np.sin(f / 3000.0)        # noqa: E731  (a made-up throat impedance)


# ------------------------------------------------------------------ the protocol with a fake backend


class FakeBackend:
    name = "fake"

    def __init__(self):
        self.warmed = 0
        self.released = 0

    def available(self):
        return True, "fake"

    def warm(self):
        self.warmed += 1

    def solve(self, mesh, spec):
        return SolveOutcome(True, make_fake_response(), 0.01, None, "")

    def release(self):
        self.released += 1


# 9
def test_fakebackend_satisfies_the_runtime_checkable_protocol():
    fb = FakeBackend()
    assert isinstance(fb, Backend)
    for attr in ("name", "available", "warm", "solve", "release"):
        assert hasattr(fb, attr)


def test_object_missing_a_method_is_not_a_backend():
    class Half:
        name = "half"

        def available(self):
            return True, ""
    assert not isinstance(Half(), Backend)


def test_fake_backend_solve_returns_a_valid_response(cfg):
    out = FakeBackend().solve(MESH, solve_spec("screen", cfg))
    assert out.ok and out.response.axis_index == 36 and out.response.spl_h_db.shape == (12, 73)


def test_real_adapters_satisfy_the_protocol():
    assert isinstance(beat_mod.BeatBackend("cuda"), Backend)
    assert isinstance(beat_mod.BeatBackend("cpu"), Backend)
    assert isinstance(beat_mod.BeatBackend("metal"), Backend)
    from hornlab_search.solve.bempp import BemppBackend
    assert isinstance(BemppBackend(), Backend)
    assert beat_mod.BeatBackend("cuda").name == "beat_cuda"
    assert beat_mod.BeatBackend("cpu").name == "beat_cpu"
    assert beat_mod.BeatBackend("metal").name == "beat_metal"
    assert beat_mod.BeatBackend("metal").track_vram is False
    assert beat_mod.BeatBackend("metal").per_frequency_calls is True
    with pytest.raises(ValueError, match="cuda_fused"):
        beat_mod.BeatBackend("metal", cuda_fused=True)


# ------------------------------------------------------------------ a fake hornlab_beat_bem


@dataclasses.dataclass
class FObservationConfig:
    planes: list = None
    distance_m: float = 2.0
    angle_min_deg: float = 0.0
    angle_max_deg: float = 180.0
    angle_count: int = 37
    sphere_grid: tuple | None = None


@dataclasses.dataclass
class FObservationFrame:
    axis: object = None
    origin: object = None
    u: object = None
    v: object = None


@dataclasses.dataclass
class FSolveConfig:
    beat_backend: str = "cpu"
    native_symmetry_plane: str | None = None
    mesh_scale: float = 1.0
    velocity_sources: dict = None
    source_motion: str = "normal"          # real beat SolveConfig field (WP5)
    air_density: float = 1.2041
    sound_speed: float = 343.0
    observation: FObservationConfig = None
    frame_override: object = None
    surface_traces: bool = False


def _fake_result(freqs, cfg, *, asym=None):
    """A SolveResult-shaped object for ``freqs`` and ``cfg`` (observation = cfg.observation)."""
    obs = cfg.observation
    ang = np.linspace(obs.angle_min_deg, obs.angle_max_deg, obs.angle_count).astype(np.float32).astype(float)
    nf = len(freqs)
    mag = cardioid_mag(np.cos(np.radians(ang)))
    amp = REF_P * 10 ** (94.0 / 20) * mag
    phase = np.exp(1j * np.linspace(0, 1, ang.size))
    row = amp * phase
    h = np.tile(row, (nf, 1))
    v = np.tile(row, (nf, 1))
    if asym is not None:
        h = h * (1.0 + asym * np.sign(ang))               # +angle louder on H when asym > 0
    h[:, obs.angle_count // 2] = v[:, obs.angle_count // 2]
    p = np.stack([h, v], axis=1)
    f = np.asarray(freqs, dtype=float)
    imp = np.array([Z_TRUE(x) * RHO_AIR * C_AIR / (-1j * 2 * np.pi * x) for x in f])
    sp = th = ph = None
    if obs.sphere_grid is not None:
        nt, nphi = obs.sphere_grid
        th = np.repeat(np.linspace(0.0, 180.0, nt), nphi)
        ph = np.tile(np.arange(nphi) * 360.0 / nphi, nt)
        sp = np.tile(REF_P * 10 ** (94 / 20) * cardioid_mag(np.cos(np.radians(th))).astype(complex), (nf, 1))
    nv, nfc = 1234, 2400
    return SimpleNamespace(
        frequencies_hz=f, pressure_complex=p, spl_db=20 * np.log10(np.abs(p) / REF_P), impedance=imp,
        observation_angles_deg=ang, observation_planes=["horizontal", "vertical"], config=cfg,
        mesh_info=SimpleNamespace(n_vertices=nv, n_triangles=nfc, physical_tag_areas_m2={1: 0.1, 2: 0.002}),
        timings={"assembly_s": 0.1, "solve_s": 0.2, "field_s": 0.05}, solver_log=[
            {"native_diagnostics": {"convergence_info": 0, "message": "Julia direct dense solve"}}
            for _ in range(nf)],
        sphere_pressure_complex=sp, sphere_theta_deg=th, sphere_phi_deg=ph,
        surface_pressure_complex=(np.ones((nf, nv), complex) if cfg.surface_traces else None),
        surface_neumann_complex=(np.ones((nf, nfc), complex) if cfg.surface_traces else None),
        cancelled=False, requested_frequency_count=nf, is_partial=False)


class FakeBeat(types.ModuleType):
    def __init__(self):
        super().__init__("hornlab_beat_bem")
        self.calls: list = []
        self.fail_at: int | None = None
        self.fail_with: Exception | None = None
        self.asym: float | None = None
        self.SolveConfig = FSolveConfig
        self.ObservationConfig = FObservationConfig
        self.ObservationFrame = FObservationFrame

    def solve_frequencies(self, path, freqs, cfg):
        self.calls.append((str(path), tuple(freqs), cfg))
        if self.fail_at is not None and len(self.calls) - 1 == self.fail_at:
            raise self.fail_with
        return _fake_result(freqs, cfg, asym=self.asym)

    def backend_status(self, backend):
        return {"available": backend == "cuda", "reason": f"fake status for {backend}"}


@pytest.fixture
def fakebeat(monkeypatch, tmp_path):
    fb = FakeBeat()
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", fb)
    monkeypatch.setattr(worker, "recover_after_failure", lambda name, **k: fb.__dict__.setdefault("recovered", []).append(name))
    monkeypatch.setattr(worker, "vram_used_mib", lambda: None)
    monkeypatch.setattr(worker, "list_processes", lambda: [
        worker.ProcInfo(100, 1, "python.exe", "python.exe -m hornlab_beat_bem.worker_host --key k")])
    base.reset_noted()
    worker.mark_cold()
    yield fb
    base.reset_noted()
    worker.mark_cold()


def _backend(tmp_path, **kw):
    notes = tmp_path / "NOTES_FOR_SENIOR.md"
    notes.write_text("# notes\n", encoding="utf-8")
    kw.setdefault("track_vram", False)
    return beat_mod.BeatBackend("cuda", notes_path=notes, **kw)


# ------------------------------------------------------------------ adapter behaviour


def test_solve_makes_one_call_per_frequency_and_returns_a_valid_response(fakebeat, tmp_path, cfg):
    spec = solve_spec("screen", cfg)
    out = _backend(tmp_path).solve(MESH, spec)
    assert out.ok, out.message
    assert len(fakebeat.calls) == len(spec.freqs_hz) == 12                      # the CUDA cliff workaround
    assert [c[1] for c in fakebeat.calls] == [(f,) for f in spec.freqs_hz]      # in spec order
    r = out.response
    assert isinstance(r, Response) and r.backend == "beat_cuda"
    assert r.spl_h_db.shape == r.spl_v_db.shape == (12, 73)
    assert np.array_equal(r.h_angles_deg, arc_angles_deg(73)) and r.axis_index == 36
    assert r.n_dof == 1234                                                       # always captured
    assert np.allclose(r.freqs_hz, spec.freqs_hz)                                # follows the config grid (band_hi_hz is a YAML default)
    assert r.p_h.shape == (12, 73) and r.p_h.dtype == np.complex128
    assert np.all(np.isfinite(r.spl_h_db)) and r.meta["n_dof_source"]
    assert r.meta["native_diagnostics"][0]["message"] == "Julia direct dense solve"
    assert r.meta["gmres_tol_requested"] == spec.gmres_tol and r.meta["gmres_tol_applied"] is None
    assert base.meta_roundtrips(r.meta)


def test_cpu_backend_makes_one_multi_frequency_call_and_cuda_loops(fakebeat, tmp_path, cfg):
    spec = solve_spec("screen", cfg)
    cpu = beat_mod.BeatBackend("cpu", track_vram=False)
    assert cpu.per_frequency_calls is False and beat_mod.BeatBackend("cuda").per_frequency_calls is True
    out = cpu.solve(MESH, spec)
    assert out.ok, out.message
    assert len(fakebeat.calls) == 1 and fakebeat.calls[0][1] == tuple(spec.freqs_hz)
    assert fakebeat.calls[0][2].beat_backend == "cpu"
    assert out.response.backend == "beat_cpu" and out.response.spl_h_db.shape == (12, 73)
    assert out.response.meta["per_frequency_calls"] is False
    forced = beat_mod.BeatBackend("cpu", track_vram=False, per_frequency_calls=True)
    fakebeat.calls.clear()
    assert forced.solve(MESH, spec).ok and len(fakebeat.calls) == 12


def test_solveconfig_takes_symmetry_from_the_mesh_scale_one_and_the_spec(fakebeat, tmp_path, cfg):
    spec = solve_spec("screen", cfg)
    _backend(tmp_path).solve(MESH, spec)
    c = fakebeat.calls[0][2]
    assert c.beat_backend == "cuda"
    assert c.native_symmetry_plane == MESH.symmetry_plane == "yz+xz"
    assert c.mesh_scale == 1.0                                  # metres, NOT the README's 0.001
    assert c.velocity_sources == {2: 1.0}
    assert c.source_motion == "normal"                         # WP5: always explicit
    assert (c.air_density, c.sound_speed) == (RHO_AIR, C_AIR)
    o = c.observation
    assert o.distance_m == spec.observation.distance_m
    assert o.angle_count == spec.observation.angle_count
    assert (o.angle_min_deg, o.angle_max_deg) == (-90.0, 90.0)
    assert o.planes == ["horizontal", "vertical"]
    assert o.sphere_grid == base.balloon_grid_shape(spec.observation.balloon_points) == (16, 32)
    assert c.surface_traces is False and fakebeat.calls[0][0] == "fake.msh"


def test_full_domain_mesh_gets_no_symmetry_flag(fakebeat, tmp_path, cfg):
    mesh = dataclasses.replace(MESH, quadrants="1234", symmetry_plane=None)
    _backend(tmp_path).solve(mesh, solve_spec("screen", cfg))
    assert fakebeat.calls[0][2].native_symmetry_plane is None


@pytest.mark.parametrize("quadrants,plane", [("1", None), ("1234", "yz+xz"), ("14", "xz"), ("12", "yz")])
def test_symmetry_flag_that_disagrees_with_quadrants_raises_not_penalises(fakebeat, tmp_path, cfg, quadrants, plane):
    from hornlab_search.mesh.build import SymmetryMismatchError
    mesh = dataclasses.replace(MESH, quadrants=quadrants, symmetry_plane=plane)
    with pytest.raises(SymmetryMismatchError):
        _backend(tmp_path).solve(mesh, solve_spec("screen", cfg))
    assert fakebeat.calls == []                                          # nothing reached the solver


def test_balloon_arrays_and_grid_in_meta(fakebeat, tmp_path, cfg):
    r = _backend(tmp_path).solve(MESH, solve_spec("screen", cfg)).response
    assert r.balloon_dirs.shape == (512, 3) and r.spl_balloon_db.shape == (12, 512)
    assert np.allclose(np.linalg.norm(r.balloon_dirs, axis=1), 1.0)
    assert r.meta["balloon_grid"] == [16, 32] and "sin(theta)" in r.meta["balloon_layout"]
    assert r.p_balloon.shape == (12, 512)
    theta = base.theta_deg_from_dirs(r.balloon_dirs)
    assert theta[0] == pytest.approx(0.0, abs=1e-6) and theta[-1] == pytest.approx(180.0, abs=1e-6)


def test_no_balloon_requested_gives_none(fakebeat, tmp_path, cfg):
    spec = solve_spec("screen", cfg)
    spec = dataclasses.replace(spec, observation=dataclasses.replace(spec.observation, balloon=False,
                                                                       balloon_points=0))
    r = _backend(tmp_path).solve(MESH, spec).response
    assert r.balloon_dirs is None and r.spl_balloon_db is None and r.p_balloon is None
    assert fakebeat.calls[0][2].observation.sphere_grid is None


def test_z_throat_is_normalised_specific_impedance(fakebeat, tmp_path, cfg):
    spec = solve_spec("screen", cfg)
    r = _backend(tmp_path).solve(MESH, spec).response
    expect = np.array([Z_TRUE(f) for f in spec.freqs_hz])
    assert np.allclose(r.z_throat, expect, rtol=1e-9)


def test_failure_becomes_outcome_not_exception(fakebeat, tmp_path, cfg):
    fakebeat.fail_at, fakebeat.fail_with = 4, ValueError("mesh has no source triangles")
    out = _backend(tmp_path).solve(MESH, solve_spec("screen", cfg))
    assert out.ok is False and out.response is None
    assert "ValueError" in out.message and "mesh has no source triangles" in out.message
    assert out.message.startswith("[other]")
    assert out.seconds >= 0
    assert "recovered" not in fakebeat.__dict__                           # no host recovery for a plain error


@pytest.mark.parametrize("text,kind", [("Out of GPU memory: asked for 644.8 MiB", "cuda_oom"),
                                       ("Warm BEAT Engine solver exited with code 1", "worker_exit")])
def test_oom_and_worker_crash_are_classified_recovered_and_noted(fakebeat, tmp_path, cfg, text, kind):
    fakebeat.fail_at, fakebeat.fail_with = 0, RuntimeError(text)
    be = _backend(tmp_path)
    out = be.solve(MESH, solve_spec("screen", cfg))
    assert out.ok is False and out.message.startswith(f"[{kind}]") and text in out.message
    assert fakebeat.recovered == ["beat_cuda"]                            # poisoned host dropped
    notes = be.notes_path.read_text(encoding="utf-8")
    if kind == "cuda_oom":
        assert "task-05" in notes and "dof cap" in notes
    else:
        assert "task-05" not in notes


def test_timeout_is_checked_between_frequencies(fakebeat, tmp_path, cfg):
    be = _backend(tmp_path, timeout_s=-1.0)
    out = be.solve(MESH, solve_spec("screen", cfg))
    assert out.ok is False and "TimeoutError" in out.message and fakebeat.calls == []


def test_solve_times_are_recorded_for_the_warm_worker_log(fakebeat, tmp_path, cfg):
    be = _backend(tmp_path)
    be.solve(MESH, solve_spec("screen", cfg))
    be.solve(MESH, solve_spec("screen", cfg))
    assert len(worker.solve_seconds("beat_cuda")) == 2


def test_available_reports_the_library_status(fakebeat):
    assert beat_mod.BeatBackend("cuda").available() == (True, "fake status for cuda")
    assert beat_mod.BeatBackend("cpu").available() == (False, "fake status for cpu")


def test_available_is_false_when_beat_is_not_importable(monkeypatch):
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", None)           # makes `import` raise ImportError
    ok, why = beat_mod.BeatBackend("cuda").available()
    assert ok is False and "hornlab_beat_bem" in why


def test_get_backend_returns_an_available_beat_backend(fakebeat):
    be = base.get_backend("beat_cuda", track_vram=False)
    assert isinstance(be, Backend) and be.name == "beat_cuda"
    with pytest.raises(base.BackendUnavailableError, match="fake status for cpu"):
        base.get_backend("beat_cpu")


# ------------------------------------------------------------------ 10: _to_response assertions fire


def _raw_and_spec(fakebeat, cfg, **kw):
    spec = solve_spec("screen", cfg)
    be = beat_mod.BeatBackend("cuda", track_vram=False)
    raw = be.solve_raw(MESH, spec)
    return raw, spec


def test_to_response_accepts_the_good_stacked_result(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    r = beat_mod._to_response(raw, spec, MESH)
    assert r.spl_h_db.shape == (12, 73)


def test_to_response_wrong_shape_raises_readable(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.pressure_complex = raw.pressure_complex[:, :, :-2]
    raw.spl_db = raw.spl_db[:, :, :-2]
    with pytest.raises(ResponseSanityError, match=r"expected \(nf=12, P, angle_count=73\)"):
        beat_mod._to_response(raw, spec, MESH)


def test_to_response_transposed_array_raises(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.pressure_complex = np.swapaxes(raw.pressure_complex, 0, 2).copy()
    raw.spl_db = np.swapaxes(raw.spl_db, 0, 2).copy()
    with pytest.raises(ResponseSanityError):
        beat_mod._to_response(raw, spec, MESH)


def test_to_response_nan_raises(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.spl_db[2, 0, 10] = np.nan
    with pytest.raises(ResponseSanityError, match="non-finite"):
        beat_mod._to_response(raw, spec, MESH)


def test_to_response_silent_pressure_gives_inf_and_raises(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.pressure_complex[1, 0, 5] = 0.0
    raw.spl_db = base.spl_from_pressure(raw.pressure_complex)
    with pytest.raises(ResponseSanityError, match="non-finite"):
        beat_mod._to_response(raw, spec, MESH)


def test_to_response_mismatched_on_axis_raises(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.pressure_complex[:, 1, 36] *= 1.001                       # ~0.009 dB apart
    raw.spl_db = base.spl_from_pressure(raw.pressure_complex)
    with pytest.raises(ResponseSanityError, match="on-axis"):
        beat_mod._to_response(raw, spec, MESH)


def test_to_response_reversed_angle_grid_raises(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.observation_angles_deg = raw.observation_angles_deg[::-1].copy()
    with pytest.raises(ResponseSanityError, match="arc_angles_deg"):
        beat_mod._to_response(raw, spec, MESH)


def test_to_response_a_0_to_180_grid_is_refused(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.observation_angles_deg = np.linspace(0, 180, 73)
    with pytest.raises(ResponseSanityError, match="arc_angles_deg"):
        beat_mod._to_response(raw, spec, MESH)


def test_to_response_spl_that_disagrees_with_pressure_raises(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.spl_db = raw.spl_db + np.linspace(0, 0.5, 73)[None, None, :]
    raw.spl_db[:, :, 36] = base.spl_from_pressure(raw.pressure_complex)[:, :, 36]
    with pytest.raises(ResponseSanityError, match="disagrees"):
        beat_mod._to_response(raw, spec, MESH)


@pytest.mark.parametrize("flag", ["cancelled", "is_partial"])
def test_to_response_partial_or_cancelled_is_never_usable(fakebeat, cfg, flag):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    setattr(raw, flag, True)
    with pytest.raises(ResponseSanityError, match="partial or cancelled"):
        beat_mod._to_response(raw, spec, MESH)


def test_to_response_wrong_frequencies_raises(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.frequencies_hz = raw.frequencies_hz[::-1].copy()
    with pytest.raises(ResponseSanityError, match="requested"):
        beat_mod._to_response(raw, spec, MESH)


def test_to_response_missing_balloon_when_requested_raises(fakebeat, cfg):
    raw, spec = _raw_and_spec(fakebeat, cfg)
    raw.sphere_pressure_complex = None
    with pytest.raises(ResponseSanityError, match="balloon"):
        beat_mod._to_response(raw, spec, MESH)


def test_sanity_failure_inside_solve_becomes_a_failed_outcome(fakebeat, tmp_path, cfg, monkeypatch):
    orig = fakebeat.solve_frequencies

    def broken(path, freqs, c):
        r = orig(path, freqs, c)
        r.spl_db[:, 0, 3] = np.nan
        return r
    monkeypatch.setattr(fakebeat, "solve_frequencies", broken)
    out = _backend(tmp_path).solve(MESH, solve_spec("screen", cfg))
    assert out.ok is False and "ResponseSanityError" in out.message and "non-finite" in out.message


# ------------------------------------------------------------------ traces plumbing (no solver)


def test_solve_traced_returns_both_trace_vectors(fakebeat, tmp_path, cfg):
    out, tr = _backend(tmp_path).solve_traced(MESH, solve_spec("screen", cfg))
    assert out.ok and tr["pressure"].shape == (12, 1234) and tr["neumann"].shape == (12, 2400)
    assert fakebeat.calls[0][2].surface_traces is True


def test_frame_origin_is_passed_through_to_the_solver_config(fakebeat, tmp_path, cfg):
    spec = solve_spec("screen", cfg)
    _backend(tmp_path).solve_raw(MESH, spec, frame_origin_m=(0.1, 0.0, 0.0))
    fr = fakebeat.calls[0][2].frame_override
    assert np.allclose(fr.origin, [0.1, 0, 0]) and np.allclose(fr.axis, [0, 0, 1])
    assert np.allclose(fr.u, [1, 0, 0]) and np.allclose(fr.v, [0, 1, 0])

def test_response_meta_records_source_motion(fakebeat, tmp_path, cfg):
    """WP5 provenance: the beat Response.meta states which source motion was solved."""
    spec = dataclasses.replace(solve_spec("screen", cfg), extra={"source_motion": "axial"})
    out = _backend(tmp_path).solve(MESH, spec)
    assert out.ok, out.message
    assert out.response.meta["source_motion"] == "axial"
    assert fakebeat.calls[0][2].source_motion == "axial"
