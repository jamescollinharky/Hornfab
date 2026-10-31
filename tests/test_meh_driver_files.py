"""C8 MEH driver-file contract tests (work package M1).

Every file under ``examples/drivers/`` listed here is transcribed from
``docs/research/typologies/mini_meh_2026-10-29/appendix_A_web_survey_raw.md`` section 8
(rows labelled ``V`` = manufacturer datasheet PDF read 2026-10-29).  A value that the
extracted table does not publish is omitted and named in ``notes``; it is never guessed.
The frozen key list is ``docs/meh/00_MEH_CONTRACTS.md`` C8.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from hornlab_search.constants import RHO_AIR

REPO = Path(__file__).resolve().parents[1]
DRIVERS = REPO / "examples" / "drivers"

# C8 "cone": every key required, with the "or" alternatives as groups.
CONE_REQUIRED = (
    "name", "kind", "re_ohm", "le_mh", "bl_tm", "sd_cm2", "xmax_mm", "p_aes_w",
    "fs_hz", "cutout_mm", "depth_mm", "source",
)
CONE_ALTERNATIVES = (
    ("qms", "rms_kg_s"),
    ("mmd_g", "mms_g"),
    ("cms_mm_per_n", "vas_l"),
)
CONE_OPTIONAL = ("frame_od_mm", "motor_od_mm", "dish_mm", "sens_db_2v83", "notes")

# C8 "compression_meh": required, then optional. `duct_mm` is from the drawing; when the
# appendix table does not show it the file must say so in `notes`.
CD_REQUIRED = (
    "name", "kind", "exit_mm", "p_aes_w", "min_xo_hz", "sens_db_1w",
    "body_d_mm", "body_len_mm", "source",
)
CD_OPTIONAL = ("duct_mm", "fs_cd_hz", "q_cd", "di_ref_db", "re_ohm", "notes")

# The eight stems this task owns (M1_DRIVER_DATA.md "Owns").
STEMS = {
    "bc_6ndl38": "cone",
    "faitalpro_6pr160": "cone",
    "eighteensound_6nmb420": "cone",
    "bc_4ndf34": "cone",
    "faitalpro_4fe32": "cone",
    "faitalpro_hf1440": "compression_meh",
    "faitalpro_hf108": "compression_meh",
    "bc_dh450": "compression_meh",
}

STRING_KEYS = ("name", "kind", "source", "notes")

# A derived key must carry this exact formula text in `notes` (M1 step 1).
DERIVED_FORMULAS = {
    "mmd_g": "Mmd = Mms - 2*(8/3)*rho*a^3",
    "cms_mm_per_n": "Cms = Vas/(rho*c^2*Sd^2)",
}

CONES = sorted(stem for stem, kind in STEMS.items() if kind == "cone")
CDS = sorted(stem for stem, kind in STEMS.items() if kind == "compression_meh")


def _load(stem: str) -> dict:
    path = DRIVERS / f"{stem}.yaml"
    assert path.is_file(), f"missing driver file {path}"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), f"{stem}: file did not parse to a mapping"
    return data


@pytest.mark.parametrize("stem", sorted(STEMS))
def test_file_parses_and_satisfies_c8_required_keys(stem: str) -> None:
    data = _load(stem)
    kind = STEMS[stem]
    assert data.get("kind") == kind, f"{stem}: kind must be {kind!r}"
    required = CONE_REQUIRED if kind == "cone" else CD_REQUIRED
    missing = [key for key in required if data.get(key) is None]
    assert not missing, f"{stem}: missing C8 required key(s) {missing}"
    if kind == "cone":
        for group in CONE_ALTERNATIVES:
            assert any(data.get(key) is not None for key in group), (
                f"{stem}: needs at least one of {group}")
    for key in STRING_KEYS:
        assert isinstance(data.get(key), str) and data[key].strip(), (
            f"{stem}: {key!r} must be a non-empty string")
    assert data["source"].startswith("http"), (
        f"{stem}: source must be the datasheet URL")


@pytest.mark.parametrize("stem", sorted(STEMS))
def test_values_are_positive_finite_and_keys_are_known(stem: str) -> None:
    data = _load(stem)
    kind = STEMS[stem]
    required = CONE_REQUIRED if kind == "cone" else CD_REQUIRED
    optional = CONE_OPTIONAL if kind == "cone" else CD_OPTIONAL
    allowed = set(required) | set(optional) | {"kind", "derived"}
    if kind == "cone":
        for group in CONE_ALTERNATIVES:
            allowed.update(group)
    unknown = sorted(set(data) - allowed)
    assert not unknown, f"{stem}: key(s) outside the C8 contract: {unknown}"

    for key, value in data.items():
        if key in STRING_KEYS or key == "derived":
            continue
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (
            f"{stem}: {key!r} must be numeric, got {value!r}")
        assert math.isfinite(float(value)) and float(value) > 0.0, (
            f"{stem}: {key!r} must be positive and finite, got {value!r}")

    derived = data.get("derived", [])
    assert isinstance(derived, list), f"{stem}: derived must be a list of keys"
    for key in derived:
        assert key in data, f"{stem}: derived key {key!r} has no value"
        assert key in DERIVED_FORMULAS, f"{stem}: no recorded formula for derived {key!r}"
        assert DERIVED_FORMULAS[key] in data["notes"], (
            f"{stem}: notes must state {DERIVED_FORMULAS[key]!r} for derived {key!r}")


@pytest.mark.parametrize("stem", CONES)
def test_cone_fs_mms_cms_are_consistent(stem: str) -> None:
    """T/S identity: Fs = 1 / (2*pi*sqrt(Mms*Cms)).

    Mms is used when published (it includes the air load); otherwise Mms is reconstructed
    from the published Mmd with Mms = Mmd + 2*(8/3)*rho*a^3, a = sqrt(Sd/pi), the same
    relation appendix A s8 uses.
    """
    data = _load(stem)
    fs = float(data["fs_hz"])
    cms_mm_per_n = float(data["cms_mm_per_n"])
    if data.get("mms_g") is not None:
        mms_g = float(data["mms_g"])
    else:
        a = math.sqrt(float(data["sd_cm2"]) * 1e-4 / math.pi)
        mms_g = float(data["mmd_g"]) + 2.0 * (8.0 / 3.0) * RHO_AIR * a ** 3 * 1e3
    cms_from_ts_mm_per_n = 1e3 / ((2.0 * math.pi * fs) ** 2 * mms_g * 1e-3)
    rel = abs(cms_from_ts_mm_per_n - cms_mm_per_n) / cms_mm_per_n
    assert rel <= 0.03, (
        f"{stem}: Fs/Mms/Cms inconsistent: Cms(Fs,Mms)={cms_from_ts_mm_per_n:.5f} mm/N "
        f"vs Cms={cms_mm_per_n:.5f} mm/N ({100.0 * rel:.2f}% > 3%)")


@pytest.mark.parametrize("stem", CONES)
def test_cone_missing_mechanical_values_are_stated_in_notes(stem: str) -> None:
    data = _load(stem)
    for key in ("frame_od_mm", "motor_od_mm", "dish_mm"):
        if data.get(key) is None:
            assert key in data["notes"], (
                f"{stem}: {key} omitted but not mentioned in notes")


@pytest.mark.parametrize("stem", CDS)
def test_cd_duct_is_published_or_its_absence_is_stated(stem: str) -> None:
    data = _load(stem)
    if data.get("duct_mm") is None:
        assert "duct depth not published" in data["notes"], (
            f"{stem}: no duct_mm and notes do not say 'duct depth not published'")
