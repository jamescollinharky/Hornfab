"""MEH network synthesis package (contracts C6/C7/C12).

This package is the lumped, CPU-side model that sits on top of a multi-source BEM ``Response``.
Part 1 (``drivers`` + ``network``) provides driver loading, the BEM -> network convention conversion,
entry Norton equivalents, the CD source and the exact coupling. Part 2 adds ``dsp`` (Linkwitz-Riley,
delay, peaking, smoothing, system EQ), ``synthesis`` (the summed metrics-ready ``Response``) and
``limits`` (SPL_max per C11). Part 3 adds ``inner``, the CMA inner optimiser over the network knobs.
"""
from .drivers import CDSource, ConeDriver, load_cd, load_cone, mmd_from_mms
from .dsp import delay, lr, peaking, polarity, smooth_oct, system_eq
from .inner import optimise_network
from .limits import binding_limits, spl_max
from .network import (
    cd_volume_velocity,
    cone_excursion_peak_mm,
    cone_velocity_rms,
    couple,
    entry_norton,
    from_bem,
    port_velocity_peak,
)
from .synthesis import NetworkSolution, channel_drives, nominal_state, system_response

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
    "lr",
    "delay",
    "polarity",
    "peaking",
    "smooth_oct",
    "system_eq",
    "NetworkSolution",
    "channel_drives",
    "nominal_state",
    "system_response",
    "spl_max",
    "binding_limits",
    "optimise_network",
]
