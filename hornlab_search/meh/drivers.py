"""Lumped driver models for the MEH network (contracts C7/C8/C12).

Two frozen dataclasses, both built from the keys of an ``examples/drivers/<stem>.yaml`` file:

``ConeDriver``  a cone mid driver (``kind: cone``) with the Thiele-Small parameters C7 needs.
``CDSource``    a compression driver (``kind: compression_meh``); the CD is driven as a mass-controlled
                ideal volume-velocity source, so it needs only its exit area and its own high-pass.

Units: every field named with an explicit SI/datasheet unit keeps that unit (``re_ohm``, ``le_h``,
``sd_m2``, ...). ``mmd_from_mms`` converts a published Mms (which includes the air load) to the DRY moving
mass Mmd that the mechanical impedance must use (C7)::

    Mmd = Mms - 2 * (8/3) * rho * a^3,   a = sqrt(Sd / pi)

``load_cone`` / ``load_cd`` read ``examples/drivers/<stem>.yaml`` (or a ``directory=`` override) and refuse
a file whose ``kind`` is not the requested one. No driver file is committed by this module.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..constants import C_AIR, RHO_AIR

__all__ = ["ConeDriver", "CDSource", "load_cone", "load_cd", "mmd_from_mms"]

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVERS_DIR = REPO_ROOT / "examples" / "drivers"

_AIR_LOAD_FACTOR = 2.0 * (8.0 / 3.0)          # C7: 2*(8/3)*rho*a^3


def _pos(name: str, value, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"driver.{name} must be a number, got {value!r}")
    x = float(value)
    if not math.isfinite(x) or x < 0.0 or (x == 0.0 and not allow_zero):
        raise ValueError(
            f"driver.{name} must be a finite number {'>= 0' if allow_zero else '> 0'}, got {value!r}"
        )
    return x


def _air_load_kg(sd_m2: float) -> float:
    """Mass of the radiation air load on one side of a piston of area ``sd_m2`` (C7)."""
    a = math.sqrt(sd_m2 / math.pi)
    return _AIR_LOAD_FACTOR * RHO_AIR * a ** 3


def mmd_from_mms(mms_g: float, sd_cm2: float) -> float:
    """Dry moving mass [g] from a published Mms [g] and Sd [cm^2] (C7).

    ``Mmd = Mms - 2*(8/3)*rho*a^3`` with ``a = sqrt(Sd/pi)``; the subtracted term is the air load on the
    two faces of the diaphragm. Verified against the references in M4's test list.
    """
    mms = _pos("mms_g", mms_g)
    sd_cm2 = _pos("sd_cm2", sd_cm2)
    return mms - _air_load_kg(sd_cm2 * 1e-4) * 1e3


@dataclass(frozen=True)
class ConeDriver:
    """One cone mid driver, in SI where the network does arithmetic.

    C7 uses ``mmd_eff_kg`` (Mmd when the datasheet gives it, else Mms minus the air load), ``cms_m_per_n``
    and ``rms_kg_s``. ``mms_kg`` is kept for reporting and for the Qms -> Rms derivation in ``from_dict``.
    """

    name: str
    re_ohm: float
    le_h: float
    bl_tm: float
    sd_m2: float
    xmax_m: float
    p_aes_w: float
    fs_hz: float
    rms_kg_s: float
    mms_kg: float
    cms_m_per_n: float
    mmd_kg: float | None = None
    qms: float | None = None
    cutout_mm: float | None = None
    depth_mm: float | None = None
    frame_od_mm: float | None = None
    motor_od_mm: float | None = None
    dish_mm: float | None = None
    sens_db_2v83: float | None = None
    notes: str = ""
    source: str = ""
    kind: str = "cone"
    raw: dict = field(default_factory=dict, compare=False, repr=False)

    # ---------------------------------------------------------------- derived properties
    @property
    def sd_cm2(self) -> float:
        return self.sd_m2 * 1e4

    @property
    def xmax_mm(self) -> float:
        return self.xmax_m * 1e3

    @property
    def mmd_g(self) -> float | None:
        return None if self.mmd_kg is None else self.mmd_kg * 1e3

    @property
    def mms_g(self) -> float:
        return self.mms_kg * 1e3

    @property
    def cms_mm_per_n(self) -> float:
        return self.cms_m_per_n * 1e3

    @property
    def vas_l(self) -> float:
        """Equivalent volume [L] from Cms: Vas = rho c^2 Sd^2 Cms."""
        return RHO_AIR * C_AIR ** 2 * self.sd_m2 ** 2 * self.cms_m_per_n * 1e3

    @property
    def air_load_kg(self) -> float:
        return _air_load_kg(self.sd_m2)

    @property
    def mmd_eff_kg(self) -> float:
        """The mass in Zm (C7): Mmd when published, else Mms minus the air load."""
        if self.mmd_kg is not None:
            return self.mmd_kg
        return self.mms_kg - self.air_load_kg

    # ---------------------------------------------------------------- loading
    @classmethod
    def from_dict(cls, d: dict) -> "ConeDriver":
        if not isinstance(d, dict):
            raise ValueError("cone driver must be a mapping")
        kind = d.get("kind")
        if kind != "cone":
            raise ValueError(f"cone driver: kind must be 'cone', got {kind!r}")

        required = ("name", "re_ohm", "le_mh", "bl_tm", "sd_cm2", "xmax_mm", "p_aes_w", "fs_hz",
                    "cutout_mm", "depth_mm", "source")
        missing = [k for k in required if d.get(k) is None]
        if missing:
            raise ValueError(f"cone driver: missing required key(s) {missing}")
        if d.get("qms") is None and d.get("rms_kg_s") is None:
            raise ValueError("cone driver: give qms or rms_kg_s")
        if d.get("mmd_g") is None and d.get("mms_g") is None:
            raise ValueError("cone driver: give mmd_g (preferred) or mms_g")
        if d.get("cms_mm_per_n") is None and d.get("vas_l") is None:
            raise ValueError("cone driver: give cms_mm_per_n or vas_l")

        sd_m2 = _pos("sd_cm2", d["sd_cm2"]) * 1e-4
        air = _air_load_kg(sd_m2)

        if d.get("mmd_g") is not None:
            mmd_kg = _pos("mmd_g", d["mmd_g"]) * 1e-3
            mms_kg = mmd_kg + air
        else:
            mms_kg = _pos("mms_g", d["mms_g"]) * 1e-3
            mmd_kg = None

        fs_hz = _pos("fs_hz", d["fs_hz"])
        qms = _pos("qms", d["qms"]) if d.get("qms") is not None else None
        if d.get("rms_kg_s") is not None:
            rms_kg_s = _pos("rms_kg_s", d["rms_kg_s"])
        else:
            assert qms is not None  # guarded above: qms or rms_kg_s is required
            rms_kg_s = 2.0 * math.pi * fs_hz * mms_kg / qms

        if d.get("cms_mm_per_n") is not None:
            cms_m_per_n = _pos("cms_mm_per_n", d["cms_mm_per_n"]) * 1e-3
        else:
            vas_m3 = _pos("vas_l", d["vas_l"]) * 1e-3
            cms_m_per_n = vas_m3 / (RHO_AIR * C_AIR ** 2 * sd_m2 ** 2)

        return cls(
            name=str(d["name"]),
            re_ohm=_pos("re_ohm", d["re_ohm"]),
            le_h=_pos("le_mh", d["le_mh"], allow_zero=True) * 1e-3,
            bl_tm=_pos("bl_tm", d["bl_tm"]),
            sd_m2=sd_m2,
            xmax_m=_pos("xmax_mm", d["xmax_mm"]) * 1e-3,
            p_aes_w=_pos("p_aes_w", d["p_aes_w"]),
            fs_hz=fs_hz,
            rms_kg_s=rms_kg_s,
            mms_kg=mms_kg,
            cms_m_per_n=cms_m_per_n,
            mmd_kg=mmd_kg,
            qms=qms,
            cutout_mm=_pos("cutout_mm", d["cutout_mm"], allow_zero=True),
            depth_mm=_pos("depth_mm", d["depth_mm"]),
            frame_od_mm=_pos("frame_od_mm", d["frame_od_mm"], allow_zero=True)
            if d.get("frame_od_mm") is not None else None,
            motor_od_mm=_pos("motor_od_mm", d["motor_od_mm"], allow_zero=True)
            if d.get("motor_od_mm") is not None else None,
            dish_mm=_pos("dish_mm", d["dish_mm"], allow_zero=True)
            if d.get("dish_mm") is not None else None,
            sens_db_2v83=float(d["sens_db_2v83"]) if d.get("sens_db_2v83") is not None else None,
            notes=str(d.get("notes") or ""),
            source=str(d["source"]),
            kind="cone",
            raw=dict(d),
        )

    @classmethod
    def from_yaml(cls, path) -> "ConeDriver":
        with open(Path(path), encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh))


@dataclass(frozen=True)
class CDSource:
    """One compression driver, driven as a mass-controlled ideal volume-velocity source (C7).

    ``exit_mm`` is the exit DIAMETER from the datasheet (C9 uses it as the bore diameter). ``fs_cd_hz``
    defaults to ``min_xo_hz / 1.4`` and ``q_cd`` to 1.0 (C8).
    """

    name: str
    exit_mm: float
    p_aes_w: float
    min_xo_hz: float
    sens_db_1w: float
    body_d_mm: float
    body_len_mm: float
    fs_cd_hz: float
    duct_mm: float = 0.0
    q_cd: float = 1.0
    di_ref_db: float = 10.0
    re_ohm: float | None = None
    notes: str = ""
    source: str = ""
    kind: str = "compression_meh"
    raw: dict = field(default_factory=dict, compare=False, repr=False)

    @property
    def s_exit_m2(self) -> float:
        """Exit area [m^2] from the exit diameter [mm] (C7's S_exit)."""
        r = self.exit_mm * 1e-3 / 2.0
        return math.pi * r * r

    @property
    def duct_m(self) -> float:
        return self.duct_mm * 1e-3

    @property
    def body_d_m(self) -> float:
        return self.body_d_mm * 1e-3

    @property
    def body_len_m(self) -> float:
        return self.body_len_mm * 1e-3

    @classmethod
    def from_dict(cls, d: dict) -> "CDSource":
        if not isinstance(d, dict):
            raise ValueError("compression driver must be a mapping")
        kind = d.get("kind")
        if kind != "compression_meh":
            raise ValueError(f"compression driver: kind must be 'compression_meh', got {kind!r}")

        required = ("name", "exit_mm", "p_aes_w", "min_xo_hz", "sens_db_1w", "body_d_mm",
                    "body_len_mm", "source")
        missing = [k for k in required if d.get(k) is None]
        if missing:
            raise ValueError(f"compression driver: missing required key(s) {missing}")

        min_xo_hz = _pos("min_xo_hz", d["min_xo_hz"])
        fs_cd_hz = (_pos("fs_cd_hz", d["fs_cd_hz"]) if d.get("fs_cd_hz") is not None
                   else min_xo_hz / 1.4)
        return cls(
            name=str(d["name"]),
            exit_mm=_pos("exit_mm", d["exit_mm"]),
            p_aes_w=_pos("p_aes_w", d["p_aes_w"]),
            min_xo_hz=min_xo_hz,
            sens_db_1w=float(d["sens_db_1w"]),
            body_d_mm=_pos("body_d_mm", d["body_d_mm"]),
            body_len_mm=_pos("body_len_mm", d["body_len_mm"]),
            fs_cd_hz=fs_cd_hz,
            duct_mm=_pos("duct_mm", d["duct_mm"], allow_zero=True) if d.get("duct_mm") is not None else 0.0,
            q_cd=_pos("q_cd", d["q_cd"]) if d.get("q_cd") is not None else 1.0,
            di_ref_db=float(d["di_ref_db"]) if d.get("di_ref_db") is not None else 10.0,
            re_ohm=_pos("re_ohm", d["re_ohm"], allow_zero=True) if d.get("re_ohm") is not None else None,
            notes=str(d.get("notes") or ""),
            source=str(d["source"]),
            kind="compression_meh",
            raw=dict(d),
        )

    @classmethod
    def from_yaml(cls, path) -> "CDSource":
        with open(Path(path), encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh))


def _driver_path(stem: str, directory) -> Path:
    p = Path(stem)
    if directory is not None:
        base = Path(directory)
    elif p.is_absolute() or p.suffix == ".yaml" or len(p.parts) > 1:
        return p
    else:
        base = DRIVERS_DIR
    name = p.name if p.suffix == ".yaml" else f"{p.name}.yaml"
    path = base / name
    if not path.is_file():
        raise FileNotFoundError(f"driver file not found: {path}")
    return path


def load_cone(stem: str, *, directory=None) -> ConeDriver:
    """Load ``<directory or examples/drivers>/<stem>.yaml`` as a :class:`ConeDriver` (kind ``cone``)."""
    d = yaml.safe_load(_driver_path(stem, directory).read_text(encoding="utf-8"))
    return ConeDriver.from_dict(d)


def load_cd(stem: str, *, directory=None) -> CDSource:
    """Load ``<directory or examples/drivers>/<stem>.yaml`` as a :class:`CDSource` (kind ``compression_meh``)."""
    d = yaml.safe_load(_driver_path(stem, directory).read_text(encoding="utf-8"))
    return CDSource.from_dict(d)
