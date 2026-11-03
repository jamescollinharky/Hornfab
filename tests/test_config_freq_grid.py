"""Opt-in ``solve.freq_grid`` (MEH, 2026-10-31): the brief's own band at a stated density.

The frozen ``FREQ_GRIDS`` per mode must stay byte-identical for every config that does not set the
block, so these tests pin both sides: absent = today's 12-point 500-10,000 screen grid, present =
the contracted 120-12,000 Hz 1/6-octave grid, and the mesh f_max follows the grid.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import ConfigError, load_config, mesh_spec, mode_freqs, solve_spec

BASE = EXAMPLES / "typologies" / "meh_2026-10-30" / "meh_t2a_search.yaml"
FROZEN = (500.0, 10_000.0)


def _with_grid(tmp_path, block, name="cfg"):
    raw = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    raw["solve"]["freq_grid"] = block
    # the copy lives in tmp_path, so the relative brief_file must become absolute
    raw["brief_file"] = str((BASE.parent / raw["brief_file"]).resolve())
    p = tmp_path / f"{name}.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return p


def test_absent_block_keeps_the_frozen_screen_grid(tmp_path):
    raw = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    raw["solve"].pop("freq_grid", None)
    raw["brief_file"] = str((BASE.parent / raw["brief_file"]).resolve())
    p = tmp_path / "plain.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    freqs = mode_freqs("screen", load_config(p))
    assert len(freqs) == 12
    assert freqs[0] == pytest.approx(FROZEN[0]) and freqs[-1] == pytest.approx(FROZEN[1])


def test_the_block_gives_the_contracted_band_at_the_stated_density():
    cfg = load_config(BASE)
    freqs = mode_freqs("screen", cfg)
    assert len(freqs) == 41                       # log2(100) * 6 + 1
    assert freqs[0] == pytest.approx(120.0) and freqs[-1] == pytest.approx(12_000.0)
    ratios = np.diff(np.log2(np.asarray(freqs)))
    assert np.allclose(ratios, 1.0 / 6.0, atol=1e-3)   # 1/6 octave throughout
    assert mesh_spec("screen", cfg).f_max_hz == pytest.approx(12_000.0)


def test_the_grid_changes_the_solve_hash(tmp_path):
    base = load_config(BASE)
    other = load_config(_with_grid(tmp_path, {"lo_hz": 120, "hi_hz": 12_000, "points_per_octave": 3}))
    assert solve_spec("screen", base).hash() != solve_spec("screen", other).hash()


@pytest.mark.parametrize("block,match", [
    ({"lo_hz": 120, "hi_hz": 12_000}, "required numbers"),
    ({"lo_hz": 0, "hi_hz": 12_000, "points_per_octave": 6}, "0 < lo_hz < hi_hz"),
    ({"lo_hz": 500, "hi_hz": 200, "points_per_octave": 6}, "0 < lo_hz < hi_hz"),
    ({"lo_hz": 120, "hi_hz": 12_000, "points_per_octave": 0}, "points_per_octave"),
    ({"lo_hz": 120, "hi_hz": 12_000, "points_per_octave": 6, "extra": 1}, "unknown key"),
    ("120-12000", "must be a mapping"),
])
def test_a_bad_block_refuses(tmp_path, block, match):
    with pytest.raises(ConfigError, match=match):
        load_config(_with_grid(tmp_path, block))
