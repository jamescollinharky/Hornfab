"""MEH multi-source adapter (docs/meh/00_MEH_CONTRACTS.md C4-C5) against a fake beat module.

No solver, Julia, GPU or mesher: ``hornlab_beat_bem`` is replaced in ``sys.modules`` by a fake
whose ``SolveConfig`` optionally exposes the fork's ``impedance_matrix`` field and whose
``solve_frequencies`` returns a 2-channel SolveResult-shaped object. That exercises the REAL
adapter: the unchanged single-source config, the multi-source config, the old-pin refusal, the
pre-flight tag check against ``mesh_meta.json``, result conversion and the cache round trip.

Red line (AGENTS.md rule 1): the installed ``hornlab_beat_bem`` has no ``impedance_matrix`` yet
(M2 builds it, M8 bumps the pin), so nothing here imports the real library.
"""
from __future__ import annotations

import dataclasses
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import cardioid_mag, make_fake_response
from hornlab_search.config import ConfigError, solve_spec
from hornlab_search.constants import C_AIR, REF_P, RHO_AIR
from hornlab_search.solve import base, cache, worker
from hornlab_search.solve import beat as beat_mod
from hornlab_search.solve.base import ResponseSanityError, arc_angles_deg
from hornlab_search.types import MeshResult, Response, SolveSpec

#: Golden solve hash of examples/osse_baseline.yaml + solve_spec("screen", cfg), computed from
#: the adapter BEFORE the MEH fields existed. Absent `source_tags` must never change it.
GOLDEN_LEGACY_SOLVE_HASH = "cfdb0910d126"


def _mesh(tmp_path, tags=(1, 2, 10), *, meta=True):
    """A MeshResult whose directory holds the mesh_meta.json task M5 writes (per-tag areas)."""
    path = tmp_path / "mesh.msh"
    path.write_bytes(b"")                       # the fake solver never reads it
    if meta:
        import json
        (tmp_path / "mesh_meta.json").write_text(json.dumps({
            "summary": {"tags": {str(t): 10 for t in tags},
                        "tag_areas_m2": {str(t): 0.001 * (i + 1) for i, t in enumerate(tags)}},
        }), encoding="utf-8")
    return MeshResult(path=str(path), n_triangles=2400, n_dof=1234, quadrants="1",
                      symmetry_plane="yz+xz", res_mm={"throat": 3.0, "mouth": 6.0, "rear": 6.0},
                      bbox_m=(0.0, 0.0, 0.0, 0.2, 0.15, 0.3), seconds=0.1)


def _meh_spec(cfg, tags=(2, 10)) -> SolveSpec:
    spec = solve_spec("screen", cfg)
    return dataclasses.replace(spec, extra={"source_tags": list(tags)})


# ------------------------------------------------------------------ fake hornlab_beat_bem


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
class FOldSolveConfig:
    """The installed pin's SolveConfig shape: no ``impedance_matrix`` field."""
    beat_backend: str = "cpu"
    native_symmetry_plane: str | None = None
    mesh_scale: float = 1.0
    velocity_sources: dict = None
    source_motion: str = "normal"
    air_density: float = 1.2041
    sound_speed: float = 343.0
    observation: FObservationConfig = None
    frame_override: object = None
    surface_traces: bool = False


@dataclasses.dataclass
class FNewSolveConfig(FOldSolveConfig):
    """The M2 fork's SolveConfig shape: the same fields plus the opt-in matrix."""
    impedance_matrix: bool = False


Z_TRUE = lambda f: 1.1 + 0.4j * np.sin(f / 3000.0)        # noqa: E731


def _fake_meh_result(freqs, cfg):
    """A 2+-channel SolveResult-shaped object; legacy fields == channel 0 (C4)."""
    obs = cfg.observation
    ang = np.linspace(obs.angle_min_deg, obs.angle_max_deg, obs.angle_count).astype(np.float32).astype(float)
    tags = tuple(sorted(int(t) for t in cfg.velocity_sources))
    nf, nch = len(freqs), len(tags)
    mag = cardioid_mag(np.cos(np.radians(ang)))
    amp = REF_P * 10 ** (94.0 / 20) * mag
    phase = np.exp(1j * np.linspace(0, 1, ang.size))
    row = amp * phase

    channels = []
    for c in range(nch):
        scale = 1.0 if c == 0 else 0.4 + 0.1 * c
        h = np.tile(scale * row, (nf, 1))
        v = h.copy()
        h[:, obs.angle_count // 2] = v[:, obs.angle_count // 2]
        channels.append(np.stack([h, v], axis=1))
    channel_pressure = np.stack(channels, axis=1)          # (F, C, P, A)
    p = channel_pressure[:, 0]                             # legacy = smallest tag
    f = np.asarray(freqs, dtype=float)
    imp = np.array([Z_TRUE(x) * RHO_AIR * C_AIR / (-1j * 2 * np.pi * x) for x in f])
    matrix = np.empty((nf, nch, nch), dtype=np.complex128)
    for i in range(nch):
        for j in range(nch):
            matrix[:, i, j] = (0.5 + i + j) * imp

    sp = th = ph = None
    channel_sphere = None
    if obs.sphere_grid is not None:
        nt, nphi = obs.sphere_grid
        th = np.repeat(np.linspace(0.0, 180.0, nt), nphi)
        ph = np.tile(np.arange(nphi) * 360.0 / nphi, nt)
        base_sp = np.tile(
            REF_P * 10 ** (94 / 20) * cardioid_mag(np.cos(np.radians(th))).astype(complex), (nf, 1))
        channel_sphere = np.stack(
            [base_sp * (1.0 if c == 0 else 0.4 + 0.1 * c) for c in range(nch)], axis=1)
        sp = channel_sphere[:, 0]

    nv, nfc = 1234, 2400
    return SimpleNamespace(
        frequencies_hz=f, pressure_complex=p, spl_db=20 * np.log10(np.abs(p) / REF_P),
        impedance=imp, observation_angles_deg=ang,
        observation_planes=["horizontal", "vertical"], config=cfg,
        mesh_info=SimpleNamespace(n_vertices=nv, n_triangles=nfc,
                                  physical_tag_areas_m2={1: 0.1, 2: 0.002, 10: 0.001}),
        timings={"assembly_s": 0.1, "solve_s": 0.2, "field_s": 0.05},
        solver_log=[{"native_diagnostics": {"convergence_info": 0,
                                            "message": "Julia direct dense solve"}} for _ in range(nf)],
        channel_tags=tags, channel_pressure=channel_pressure,
        channel_sphere_pressure=channel_sphere, impedance_matrix=matrix,
        tag_areas_m2={2: 0.002, 10: 0.001},
        sphere_pressure_complex=sp, sphere_theta_deg=th, sphere_phi_deg=ph,
        surface_pressure_complex=None, surface_neumann_complex=None,
        cancelled=False, requested_frequency_count=nf, is_partial=False)


class FakeBeat(types.ModuleType):
    def __init__(self):
        super().__init__("hornlab_beat_bem")
        self.calls: list = []
        self.SolveConfig = FNewSolveConfig
        self.ObservationConfig = FObservationConfig
        self.ObservationFrame = FObservationFrame

    def solve_frequencies(self, path, freqs, cfg):
        self.calls.append((str(path), tuple(freqs), cfg))
        return _fake_meh_result(freqs, cfg)

    def backend_status(self, backend):
        return {"available": backend == "cuda", "reason": f"fake status for {backend}"}


@pytest.fixture
def fakebeat(monkeypatch):
    fb = FakeBeat()
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", fb)
    monkeypatch.setattr(worker, "recover_after_failure",
                        lambda name, **k: fb.__dict__.setdefault("recovered", []).append(name))
    monkeypatch.setattr(worker, "vram_used_mib", lambda: None)
    monkeypatch.setattr(worker, "list_processes", lambda: [
        worker.ProcInfo(100, 1, "python.exe", "python.exe -m hornlab_beat_bem.worker_host --key k")])
    base.reset_noted()
    worker.mark_cold()
    yield fb
    base.reset_noted()
    worker.mark_cold()


def _backend(tmp_path):
    notes = tmp_path / "NOTES_FOR_SENIOR.md"
    notes.write_text("# notes\n", encoding="utf-8")
    return beat_mod.BeatBackend("cuda", notes_path=notes, track_vram=False)


# ------------------------------------------------------------------ config


def test_legacy_config_is_exactly_todays_config(fakebeat, tmp_path, cfg):
    fakebeat.SolveConfig = FOldSolveConfig           # the installed pin: no new field at all
    mesh = _mesh(tmp_path)
    spec = solve_spec("screen", cfg)
    c = _backend(tmp_path).make_config(mesh, spec)
    expected = {
        "beat_backend": "cuda",
        "native_symmetry_plane": "yz+xz",
        "mesh_scale": 1.0,
        "velocity_sources": {2: 1.0},
        "source_motion": "normal",
        "air_density": RHO_AIR,
        "sound_speed": C_AIR,
        "observation": dataclasses.asdict(FObservationConfig(
            planes=["horizontal", "vertical"], distance_m=spec.observation.distance_m,
            angle_min_deg=-90.0, angle_max_deg=90.0,
            angle_count=spec.observation.angle_count,
            sphere_grid=base.balloon_grid_shape(spec.observation.balloon_points))),
        "frame_override": None,
        "surface_traces": False,
    }
    assert dataclasses.asdict(c) == expected
    assert "impedance_matrix" not in dataclasses.asdict(c)     # absence, not False


def test_legacy_solve_hash_is_unchanged_and_source_tags_change_it(cfg):
    spec = solve_spec("screen", cfg)
    assert spec.hash() == GOLDEN_LEGACY_SOLVE_HASH
    meh = dataclasses.replace(spec, extra={"source_tags": [2, 10]})
    assert meh.hash() != GOLDEN_LEGACY_SOLVE_HASH


def test_multi_tag_config_carries_all_tags_and_the_matrix(fakebeat, tmp_path, cfg):
    mesh = _mesh(tmp_path)
    c = _backend(tmp_path).make_config(mesh, _meh_spec(cfg, (10, 2)))   # order is normalised
    assert c.velocity_sources == {2: 1.0, 10: 1.0}
    assert c.impedance_matrix is True
    assert c.beat_backend == "cuda" and c.native_symmetry_plane == "yz+xz"
    assert c.mesh_scale == 1.0


def test_old_pin_refusal_names_the_m8_pin_bump(fakebeat, tmp_path, cfg):
    fakebeat.SolveConfig = FOldSolveConfig
    with pytest.raises(ConfigError) as ei:
        _backend(tmp_path).make_config(_mesh(tmp_path), _meh_spec(cfg))
    msg = str(ei.value)
    assert "impedance_matrix" in msg and "M8" in msg and "pin" in msg
    assert "hornlab-search/meh-multisource" in msg
    assert fakebeat.calls == []


@pytest.mark.parametrize("tags", (["2", 10], [2, True], [2.0, 10], [], [2, 2], [2, 10, 11, 1, 2],
                                  list(range(10, 20))))
def test_bad_source_tags_are_refused(fakebeat, tmp_path, cfg, tags):
    spec = dataclasses.replace(solve_spec("screen", cfg), extra={"source_tags": tags})
    with pytest.raises(ConfigError):
        _backend(tmp_path).make_config(_mesh(tmp_path), spec)


def test_missing_source_tag_is_refused_before_any_solve(fakebeat, tmp_path, cfg):
    mesh = _mesh(tmp_path, tags=(1, 2))              # the mesh has no entry_mid (tag 10)
    with pytest.raises(ConfigError, match=r"tag\(s\) \[10\]"):
        _backend(tmp_path).make_config(mesh, _meh_spec(cfg))
    assert fakebeat.calls == []


def test_missing_mesh_meta_is_refused(fakebeat, tmp_path, cfg):
    mesh = _mesh(tmp_path, meta=False)
    with pytest.raises(ConfigError, match="mesh_meta.json"):
        _backend(tmp_path).make_config(mesh, _meh_spec(cfg))


# ------------------------------------------------------------------ result conversion


def test_two_channel_result_lands_in_response(fakebeat, tmp_path, cfg):
    mesh = _mesh(tmp_path)
    spec = _meh_spec(cfg)
    out = _backend(tmp_path).solve(mesh, spec)
    assert out.ok, out.message
    assert len(fakebeat.calls) == len(spec.freqs_hz) == 12      # CUDA still loops per frequency
    r = out.response
    assert isinstance(r, Response)
    assert r.channel_tags == (2, 10)
    assert r.channel_pressure.shape == (12, 2, 2, 73)
    assert r.channel_pressure.dtype == np.complex128
    assert r.channel_sphere_pressure.shape == (12, 2, 512)
    assert r.impedance_matrix.shape == (12, 2, 2)
    assert r.impedance_matrix.dtype == np.complex128
    assert r.tag_areas_m2 == {2: 0.002, 10: 0.001}
    # C4: legacy fields are channel 0 (the smallest tag, the CD)
    assert np.array_equal(r.p_h, r.channel_pressure[:, 0, 0, :])
    assert np.array_equal(r.p_v, r.channel_pressure[:, 0, 1, :])
    assert np.array_equal(r.p_balloon, r.channel_sphere_pressure[:, 0, :])
    assert r.spl_h_db.shape == (12, 73) and r.p_h.dtype == np.complex128
    assert r.meta["source_tags"] == [2, 10] and r.meta["impedance_matrix"] is True
    assert base.meta_roundtrips(r.meta)


def _raw_and_spec(fakebeat, tmp_path, cfg, tags=(2, 10)):
    mesh = _mesh(tmp_path)
    spec = _meh_spec(cfg, tags)
    raw = _backend(tmp_path).solve_raw(mesh, spec)
    return raw, spec, mesh


def test_channel_pressure_wrong_shape_raises(fakebeat, tmp_path, cfg):
    raw, spec, mesh = _raw_and_spec(fakebeat, tmp_path, cfg)
    raw.channel_pressure = raw.channel_pressure[:, :1]
    with pytest.raises(ResponseSanityError, match=r"channel_pressure shape"):
        beat_mod._to_response(raw, spec, mesh)


def test_channel_tags_that_disagree_with_the_request_raise(fakebeat, tmp_path, cfg):
    raw, spec, mesh = _raw_and_spec(fakebeat, tmp_path, cfg)
    raw.channel_tags = (2,)
    with pytest.raises(ResponseSanityError, match="channel_tags"):
        beat_mod._to_response(raw, spec, mesh)


def test_legacy_pressure_must_be_channel_zero(fakebeat, tmp_path, cfg):
    raw, spec, mesh = _raw_and_spec(fakebeat, tmp_path, cfg)
    raw.pressure_complex = np.asarray(raw.channel_pressure[:, 1])   # channel 1, not the CD
    raw.spl_db = 20 * np.log10(np.abs(raw.pressure_complex) / REF_P)
    with pytest.raises(ResponseSanityError, match="channel 0"):
        beat_mod._to_response(raw, spec, mesh)


def test_missing_channel_fields_raise(fakebeat, tmp_path, cfg):
    raw, spec, mesh = _raw_and_spec(fakebeat, tmp_path, cfg)
    raw.channel_pressure = None
    with pytest.raises(ResponseSanityError, match="channel_pressure"):
        beat_mod._to_response(raw, spec, mesh)


def test_missing_impedance_matrix_raises(fakebeat, tmp_path, cfg):
    raw, spec, mesh = _raw_and_spec(fakebeat, tmp_path, cfg)
    raw.impedance_matrix = None
    with pytest.raises(ResponseSanityError, match="impedance_matrix"):
        beat_mod._to_response(raw, spec, mesh)


def test_missing_channel_balloon_raises(fakebeat, tmp_path, cfg):
    raw, spec, mesh = _raw_and_spec(fakebeat, tmp_path, cfg)
    raw.channel_sphere_pressure = None
    with pytest.raises(ResponseSanityError, match="channel_sphere_pressure"):
        beat_mod._to_response(raw, spec, mesh)


def test_bempp_refuses_source_tags_before_any_work(cfg):
    from hornlab_search.solve.bempp import BemppBackend
    mesh = MeshResult(path="fake.msh", n_triangles=1, n_dof=1, quadrants="1",
                      symmetry_plane="yz+xz", res_mm={}, bbox_m=(0, 0, 0, 1, 1, 1), seconds=0.0)
    with pytest.raises(ConfigError, match="source_tags"):
        BemppBackend().solve(mesh, _meh_spec(cfg))
    with pytest.raises(ConfigError, match="source_tags"):
        BemppBackend().make_config(mesh, _meh_spec(cfg))


def test_cache_round_trips_the_meh_fields(fakebeat, tmp_path, cfg):
    mesh = _mesh(tmp_path)
    r = _backend(tmp_path).solve(mesh, _meh_spec(cfg)).response
    cache.save_response(tmp_path / "response.npz", r)
    got = cache.load_response(tmp_path / "response.npz")
    assert got.channel_tags == r.channel_tags
    assert got.tag_areas_m2 == r.tag_areas_m2
    for name in ("channel_pressure", "channel_sphere_pressure", "impedance_matrix"):
        a, b = getattr(r, name), getattr(got, name)
        assert a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes(), name


def test_legacy_response_cache_still_has_every_field_key(tmp_path):
    r = make_fake_response()
    cache.save_response(tmp_path / "legacy.npz", r)
    got = cache.load_response(tmp_path / "legacy.npz")
    assert got.channel_tags is None and got.channel_pressure is None
    assert got.channel_sphere_pressure is None and got.impedance_matrix is None
    assert got.tag_areas_m2 is None
