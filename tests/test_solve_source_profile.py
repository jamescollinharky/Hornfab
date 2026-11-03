"""WP16: ``solve.source_profile_alpha`` (J0 source-profile angle) search-side plumbing.

Offline only (NO GPU, NO Julia, NO solve): the library's ``SolveConfig`` is only CONSTRUCTED
where a forwarding/refusal check needs it, and constructing it starts nothing.

What is proven:
- absent leaves today's config, solve-spec `extra` and hash byte-for-byte untouched, and
  `BeatBackend.make_config` passes no ``source_profile_alpha`` kwarg at all;
- set rides in ``SolveSpec.extra`` under the library's OWN field name
  (``source_profile_alpha``) and changes the solve-spec hash;
- config validation mirrors the library's only local rule (finite float; 0.0 allowed as a no-op,
  negative allowed, NO invented magnitude cap) and refuses a non-beat backend loudly;
- `BeatBackend.make_config` surfaces the library's own fused-CUDA-only refusal EARLY, before
  ``import hornlab_beat_bem``, with the library's text fragments;
- on the fused path (``HORNLAB_BEAT_FUSED_BM_CUDA=1`` + backend ``cuda``) the value reaches the
  real library ``SolveConfig`` field.
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

ALPHA_KEY = "source_profile_alpha"


def _variant(tmp_path, backend="beat_cuda", **solve_keys):
    """The example config with the given ``solve:`` keys injected (same mechanism as WP14/WP15)."""
    raw = yaml.safe_load((EXAMPLES / "osse_baseline.yaml").read_text(encoding="utf-8"))
    raw["solve"]["backend"] = backend
    raw["solve"].update(solve_keys)
    p = tmp_path / "cfg_source_profile.yaml"
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

def test_absent_is_none_and_leaves_extra_and_hash_untouched():
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    assert cfg.solve.source_profile_alpha is None
    spec = solve_spec("screen", cfg)
    assert ALPHA_KEY not in spec.extra, "an absent WP16 key must not enter the solve spec"
    # The old hash is exactly the hash of an extra={} spec (cache keys / dataset provenance).
    same = SolveSpec(mode=spec.mode, freqs_hz=spec.freqs_hz, backend=spec.backend,
                     observation=spec.observation, gmres_tol=spec.gmres_tol, extra={})
    assert spec.hash() == same.hash()


def test_set_changes_the_hash_and_rides_in_extra(tmp_path):
    p = _variant(tmp_path, backend="beat_cuda", source_profile_alpha=0.5)
    cfg = load_config(p)
    assert cfg.solve.source_profile_alpha == 0.5
    spec = solve_spec("screen", cfg)
    assert spec.extra[ALPHA_KEY] == 0.5
    base = solve_spec("screen", load_config(EXAMPLES / "osse_baseline.yaml"))
    assert spec.hash() != base.hash()


def test_explicit_zero_rides_but_is_a_no_op_for_the_library(tmp_path):
    cfg = load_config(_variant(tmp_path, backend="bempp_cpu", source_profile_alpha=0.0))
    assert cfg.solve.source_profile_alpha == 0.0          # accepted everywhere: 0.0 is today
    assert solve_spec("screen", cfg).extra[ALPHA_KEY] == 0.0


# ------------------------------------------------------------------ validation

def test_negative_alpha_is_accepted(tmp_path):
    cfg = load_config(_variant(tmp_path, backend="beat_cuda", source_profile_alpha=-0.7))
    assert cfg.solve.source_profile_alpha == -0.7          # sign flips the profile phase
    assert solve_spec("screen", cfg).extra[ALPHA_KEY] == -0.7


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_alpha_is_refused(tmp_path, value):
    with pytest.raises(ConfigError, match="source_profile_alpha must be finite"):
        load_config(_variant(tmp_path, source_profile_alpha=value))


def test_non_numeric_alpha_is_refused(tmp_path):
    with pytest.raises(ConfigError, match="source_profile_alpha must be a finite number"):
        load_config(_variant(tmp_path, source_profile_alpha="steep"))


def test_boolean_alpha_is_refused(tmp_path):
    with pytest.raises(ConfigError, match="source_profile_alpha must be a finite number"):
        load_config(_variant(tmp_path, source_profile_alpha=True))


def test_non_beat_backend_refuses_a_nonzero_alpha(tmp_path):
    with pytest.raises(ConfigError, match="only implemented for the beat backends"):
        load_config(_variant(tmp_path, backend="bempp_cpu", source_profile_alpha=0.5))


# ------------------------------------------------------------------ make_config refusals

def test_beat_cpu_alpha_refused_before_the_solver_import(monkeypatch):
    """A non-fused backend with alpha set is refused with the library's own fused-only text, and
    BEFORE ``import hornlab_beat_bem`` (no device probe can have happened)."""
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", None)   # a truthy import would raise
    be = BeatBackend("cpu")
    with pytest.raises(ConfigError) as exc:
        be.make_config(_mesh(), _spec_with(source_profile_alpha=0.5))
    msg = str(exc.value)
    # Fragments of hornlab_beat_bem's own NotImplementedError text (its config.py __post_init__).
    assert "profile source implemented on the fused path only" in msg
    assert "HORNLAB_BEAT_FUSED_BM_CUDA=1" in msg
    assert "uniform drive and report a profile it never applied" in msg


def test_beat_cuda_without_the_fused_flag_refuses_with_the_library_text(monkeypatch):
    """cuda backend but no fused request: the library would raise NotImplementedError at
    SolveConfig construction; hornlab-search surfaces it early as a ConfigError."""
    be = BeatBackend("cuda")            # __init__ exports HORNLAB_BEAT_FUSED_BM_CUDA="0"
    assert be.cuda_fused is False
    monkeypatch.setenv("HORNLAB_BEAT_FUSED_BM_CUDA", "0")
    with pytest.raises(ConfigError) as exc:
        be.make_config(_mesh(), _spec_with(source_profile_alpha=0.25))
    msg = str(exc.value)
    assert "fused path only" in msg
    assert "HORNLAB_BEAT_FUSED_BM_CUDA=1" in msg
    assert "beat_backend='cuda'" in msg


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


def test_make_config_passes_nothing_when_absent(monkeypatch):
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", _FakeBeat)
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    be = BeatBackend("cpu")
    be.make_config(_mesh(), solve_spec("screen", cfg))
    assert ALPHA_KEY not in _FakeBeat.SolveConfig.seen
    assert _FakeBeat.SolveConfig.seen["source_motion"] == "normal"


def test_make_config_forwards_the_library_field_name_when_set(monkeypatch):
    monkeypatch.setitem(sys.modules, "hornlab_beat_bem", _FakeBeat)
    be = BeatBackend("cuda")             # __init__ exports the (default) fused flag "0"
    monkeypatch.setenv("HORNLAB_BEAT_FUSED_BM_CUDA", "1")     # the one path the library allows
    be.make_config(_mesh(), _spec_with(source_profile_alpha=-0.4))
    assert _FakeBeat.SolveConfig.seen[ALPHA_KEY] == -0.4


@requires_beat
def test_fused_path_reaches_the_real_library_config(monkeypatch):
    """Construct the REAL library SolveConfig on the fused CUDA path (no GPU, no solve): the
    library's validation only needs the backend string and the inherited env var."""
    be = BeatBackend("cuda")
    monkeypatch.setenv("HORNLAB_BEAT_FUSED_BM_CUDA", "1")
    lib_cfg = be.make_config(_mesh(), _spec_with(source_profile_alpha=0.5))
    assert lib_cfg.source_profile_alpha == 0.5
    # And the absent path leaves the library's own default untouched.
    default_cfg = be.make_config(_mesh(), _spec_with())
    assert default_cfg.source_profile_alpha == 0.0
