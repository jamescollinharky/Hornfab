"""WP14: CPU-validation plumbing — ``solve.near_correction`` / ``solve.solve_precision``.

Offline only (NO GPU, NO Julia, NO fork install): the library's ``SolveConfig`` is only
CONSTRUCTED where a refusal must be proven, and constructing it starts nothing.

What is proven:
- absent keys leave today's config, solve-spec `extra` and hash byte-for-byte untouched;
- each opt-in key rides in `SolveSpec.extra` under the library's OWN field names
  (near_correction, near_correction_cutoff, near_correction_order, solve_precision) only when set,
  and changes the solve-spec hash only then;
- config validation mirrors the library: precision in {'single','double'}, cutoff finite and > 0,
  order an integer >= 4; a non-beat backend is refused loudly;
- `BeatBackend.make_config` forwards the four names only when present and refuses beat_cuda +
  near_correction / precision='double' with the library's own rationale, BEFORE importing the
  solver (so before any GPU/worker work).
"""
from __future__ import annotations

import dataclasses
import sys

import pytest
import yaml

from conftest import EXAMPLES, requires_beat
from hornlab_search.config import ConfigError, load_config, solve_spec
from hornlab_search.solve.beat import BeatBackend
from hornlab_search.types import MeshResult, SolveSpec

NEAR_KEYS = ("near_correction", "near_correction_cutoff", "near_correction_order",
             "solve_precision")


def _variant(tmp_path, backend="beat_cpu", **solve_keys):
    """The example config with the given ``solve:`` keys injected (same mechanism as WP15's test)."""
    raw = yaml.safe_load((EXAMPLES / "osse_baseline.yaml").read_text(encoding="utf-8"))
    raw["solve"]["backend"] = backend
    raw["solve"].update(solve_keys)
    p = tmp_path / "cfg_near.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return p


def _mesh() -> MeshResult:
    return MeshResult(path="", n_triangles=1, n_dof=None, quadrants="1",
                      symmetry_plane="yz+xz", res_mm={}, bbox_m=(0.0, 0.0, 0.0, 0.1, 0.1, 0.1),
                      seconds=0.0)


def _spec_with(**extra):
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    return dataclasses.replace(solve_spec("screen", cfg), extra=extra)


# ------------------------------------------------------------------ absent = today

def test_absent_keys_are_none_and_leave_extra_and_hash_untouched():
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    for key in NEAR_KEYS:
        assert getattr(cfg.solve, key) is None, key
    spec = solve_spec("screen", cfg)
    assert spec.extra == {}, "absent WP14 keys must not enter the solve spec"
    # The old hash is exactly the hash of an extra={} spec (cache keys / dataset provenance).
    same = SolveSpec(mode=spec.mode, freqs_hz=spec.freqs_hz, backend=spec.backend,
                     observation=spec.observation, gmres_tol=spec.gmres_tol, extra={})
    assert spec.hash() == same.hash()


@pytest.mark.parametrize("key,value", [
    ("near_correction", True),
    ("near_correction_cutoff", 3.0),
    ("near_correction_order", 12),
    ("solve_precision", "double"),
])
def test_each_key_changes_the_hash_only_when_set(tmp_path, key, value):
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    base = solve_spec("screen", cfg)
    set_spec = dataclasses.replace(base, extra={key: value})
    assert set_spec.hash() != base.hash()
    assert key not in base.extra


def test_all_four_load_and_ride_in_extra(tmp_path):
    p = _variant(tmp_path, near_correction=True, near_correction_cutoff=3.0,
                 near_correction_order=12, solve_precision="double")
    cfg = load_config(p)
    assert cfg.solve.near_correction is True
    assert cfg.solve.near_correction_cutoff == 3.0
    assert cfg.solve.near_correction_order == 12
    assert cfg.solve.solve_precision == "double"
    spec = solve_spec("screen", cfg)
    assert spec.extra == {"near_correction": True, "near_correction_cutoff": 3.0,
                          "near_correction_order": 12, "solve_precision": "double"}


# ------------------------------------------------------------------ validation

def test_precision_must_be_single_or_double(tmp_path):
    with pytest.raises(ConfigError, match="solve_precision"):
        load_config(_variant(tmp_path, solve_precision="half"))


def test_order_must_be_an_integer_at_least_four(tmp_path):
    with pytest.raises(ConfigError, match="near_correction_order"):
        load_config(_variant(tmp_path, near_correction=True, near_correction_order=3))
    with pytest.raises(ConfigError, match="near_correction_order"):
        load_config(_variant(tmp_path, near_correction=True, near_correction_order=6.5))


def test_cutoff_must_be_finite_and_positive(tmp_path):
    with pytest.raises(ConfigError, match="near_correction_cutoff"):
        load_config(_variant(tmp_path, near_correction=True, near_correction_cutoff=0.0))
    with pytest.raises(ConfigError, match="near_correction_cutoff"):
        load_config(_variant(tmp_path, near_correction=True, near_correction_cutoff=-1.5))


def test_near_correction_must_be_boolean(tmp_path):
    with pytest.raises(ConfigError, match="near_correction must be a boolean"):
        load_config(_variant(tmp_path, near_correction="yes"))


def test_non_beat_backend_refuses_near_and_precision(tmp_path):
    with pytest.raises(ConfigError, match="only implemented for the beat backends"):
        load_config(_variant(tmp_path, backend="bempp_cpu", near_correction=True))
    with pytest.raises(ConfigError, match="only implemented for the beat backends"):
        load_config(_variant(tmp_path, backend="bempp_cpu", solve_precision="double"))


def test_beat_cpu_accepts_near_and_double(tmp_path):
    cfg = load_config(_variant(tmp_path, near_correction=True, solve_precision="double"))
    assert cfg.solve.backend == "beat_cpu"
    assert solve_spec("screen", cfg).extra["solve_precision"] == "double"


# ------------------------------------------------------------------ beat_cuda refusal surfacing

def test_beat_cuda_near_correction_refused_with_library_rationale():
    be = BeatBackend("cuda")
    with pytest.raises(ConfigError) as exc:
        be.make_config(_mesh(), _spec_with(near_correction=True))
    msg = str(exc.value)
    # The library's own NEAR_CORRECTION_REFUSALS[cuda] rationale (loose fragments).
    assert "single image-near cache" in msg
    assert "multi-image symmetry" in msg
    assert "refused rather than silently wrong" in msg
    assert "beat_cpu" in msg


def test_beat_cuda_double_precision_refused_with_library_text():
    be = BeatBackend("cuda")
    with pytest.raises(ConfigError) as exc:
        be.make_config(_mesh(), _spec_with(solve_precision="double"))
    assert "only available on the BEAT CPU backend" in str(exc.value)


def test_beat_cuda_refusal_happens_before_the_solver_import(monkeypatch):
    """The pre-flight is before ``import hornlab_beat_bem``: no device probe can have happened."""
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", None)   # a truthy import would raise
    be = BeatBackend("cuda")
    with pytest.raises(ConfigError, match="single image-near cache"):
        be.make_config(_mesh(), _spec_with(near_correction=True))
    with pytest.raises(ConfigError, match="only available on the BEAT CPU backend"):
        be.make_config(_mesh(), _spec_with(solve_precision="double"))


# ------------------------------------------------------------------ make_config forwarding

class _FakeBeat:
    """Records SolveConfig kwargs so the ABSENT path can be proven to pass NOTHING."""

    class ObservationConfig:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class ObservationFrame:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class SolveConfig:
        seen: dict = {}

        def __init__(self, **kw):
            type(self).seen = dict(kw)
            self.__dict__.update(kw)


def test_make_config_passes_nothing_when_keys_absent(monkeypatch):
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", _FakeBeat)
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    be = BeatBackend("cpu")
    be.make_config(_mesh(), solve_spec("screen", cfg))
    for key in NEAR_KEYS:
        assert key not in _FakeBeat.SolveConfig.seen, key
    assert _FakeBeat.SolveConfig.seen["source_motion"] == "normal"


@requires_beat
def test_make_config_forwards_the_library_field_names():
    """Construct the REAL loudspeaker library config on the CPU backend (no GPU/Julia needed)."""
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    spec = dataclasses.replace(solve_spec("screen", cfg), extra={
        "near_correction": True,
        "near_correction_cutoff": 3.0,
        "near_correction_order": 12,
        "solve_precision": "double",
    })
    be = BeatBackend("cpu")             # beat_backend="cpu": the library accepts both opt-ins
    lib_cfg = be.make_config(_mesh(), spec)
    assert lib_cfg.near_correction is True
    assert lib_cfg.near_correction_cutoff == 3.0
    assert lib_cfg.near_correction_order == 12
    assert lib_cfg.solve_precision == "double"
    # And the absent path leaves the library's own defaults untouched.
    default_cfg = be.make_config(_mesh(), solve_spec("screen", cfg))
    assert default_cfg.near_correction is False
    assert default_cfg.near_correction_cutoff == 2.0
    assert default_cfg.near_correction_order == 8
    assert default_cfg.solve_precision == "single"
