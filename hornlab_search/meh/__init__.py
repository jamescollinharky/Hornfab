"""MEH network synthesis package (contracts C6/C7/C12).

This package is the lumped, CPU-side model that sits on top of a multi-source BEM ``Response``. Part 1
(``drivers`` + ``network``) provides driver loading, the BEM -> network convention conversion, entry
Norton equivalents, the CD source and the exact coupling. Later parts add ``dsp``, ``limits``,
``synthesis`` and ``inner``.
"""
from .drivers import CDSource, ConeDriver, load_cd, load_cone, mmd_from_mms
from .network import (
    cd_volume_velocity,
    cone_excursion_peak_mm,
    cone_velocity_rms,
    couple,
    entry_norton,
    from_bem,
    port_velocity_peak,
)

__all__ = [
    "ConeDriver",
    "CDSource",
    "load_cone",
    "load_cd",
    "mmd_from_mms",
    "from_bem",
    "entry_norton",
    "cd_volume_velocity",
    "couple",
    "cone_velocity_rms",
    "cone_excursion_peak_mm",
    "port_velocity_peak",
]
