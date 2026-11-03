"""``load_config(..., backend=...)``: the CLI override is applied before validation and recorded in
``raw`` (so ``config_sha``/run snapshots match), and CUDA-only ``cuda_fused`` is dropped for a
non-CUDA backend."""
from __future__ import annotations

from pathlib import Path

import pytest

from hornlab_search.config import ConfigError, load_config, solve_spec

REPO = Path(__file__).resolve().parents[1]
STAGED = (REPO / "examples" / "typologies" / "staged_ab_2026-10-31"
          / "joint__crease_core_law.yaml")


def test_staged_joint_config_is_cuda_fused_by_default():
    cfg = load_config(STAGED)
    assert cfg.solve.backend == "beat_cuda"
    assert cfg.solve.cuda_fused is True


def test_backend_override_to_metal_drops_cuda_fused_everywhere():
    cfg = load_config(STAGED, backend="beat_metal")
    assert cfg.solve.backend == "beat_metal"
    assert cfg.solve.cuda_fused is False
    assert cfg.raw["solve"]["backend"] == "beat_metal"
    assert "cuda_fused" not in cfg.raw["solve"]
    spec = solve_spec("screen", cfg)
    assert spec.backend == "beat_metal"
    assert "cuda_fused" not in spec.extra


def test_backend_override_to_cuda_keeps_cuda_fused():
    cfg = load_config(STAGED, backend="beat_cuda")
    assert cfg.solve.backend == "beat_cuda"
    assert cfg.solve.cuda_fused is True
    assert cfg.raw["solve"]["cuda_fused"] is True
    spec = solve_spec("screen", cfg)
    assert spec.backend == "beat_cuda"
    assert spec.extra["cuda_fused"] is True


def test_omitting_backend_reproduces_plain_load():
    plain = load_config(STAGED)
    again = load_config(STAGED)
    assert again.solve.backend == plain.solve.backend
    assert again.solve.cuda_fused == plain.solve.cuda_fused
    assert again.raw == plain.raw
    for mode in ("screen", "verify"):
        assert solve_spec(mode, again).hash() == solve_spec(mode, plain).hash()


def test_backend_override_requires_a_solve_block(tmp_path):
    p = tmp_path / "nosolve.yaml"
    p.write_text("name: x\nfamily: OSSE\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="solve block must be a mapping"):
        load_config(p, backend="beat_metal")
