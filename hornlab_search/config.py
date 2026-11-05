"""YAML -> Config.

Wave 0 keeps the design space and target as raw dicts (03_TASK_SCAFFOLD step 4, "the dict
approach"). The only Wave-1 import is `mesh.sizing` (a pure numpy/math module) so the triangle
ceiling has a single source of truth (senior ruling 2026-10-13); the pipeline (task 08) builds
the typed DesignSpace and Target from `bounds_raw` and `target_raw`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .mesh import sizing
from .types import MeshSpec, Mode, ObservationSpec, SolveSpec

log = logging.getLogger("hornlab_search.config")

# 01_CONTRACTS section 6: max_triangles = ceil(2 * dof_cap * quadrant_factor * 1.15)
QUADRANT_FACTOR = sizing.QUADRANT_FACTOR  # one source (silent-killer rule)

# 01_CONTRACTS section 8: frozen grid shape per mode (f_low, f_high, points).
FREQ_GRIDS: dict[str, tuple[float, float, int]] = {
    "screen": (500.0, 10_000.0, 12),
    "verify": (300.0, 16_000.0, 25),
    "final": (250.0, 20_000.0, 36),
}

MODES = ("screen", "verify", "final")

# WP11b: the search algorithms this config knows how to run. The CLI entry (``search.cma.search``)
# dispatches on this value; anything else is refused at load time with a ``search.algorithm`` prefix.
SEARCH_ALGORITHMS = ("cma", "cma_me")

# WP11b: the descriptor functions shipped for CMA-ME quality-diversity runs. Each is the MEAN of a
# MetricSet beamwidth over the in-band frequency indices (cfg.target.band_lo_hz..band_hi_hz),
# NaN-safe. Names are part of the ``search.qd`` schema; extend here and in search/cma_me.py together.
QD_DESCRIPTORS = ("mean_bw_h_deg", "mean_bw_v_deg")

# WP4 (senior pass 2026-10-24): the verify grid's HF-density extension starts at 5 kHz — below
# that the frozen 25-point verify grid is already dense enough for every measured epw decision.
HF_VERIFY_LO_HZ = 5000.0


def freq_grid(lo: float, hi: float, n: int) -> tuple[float, ...]:
    return tuple(round(float(f), 2) for f in np.geomspace(lo, hi, n))


# ------------------------------------------------------------------ settings

@dataclass
class MeshSettings:
    epw: float
    quadrants: str
    dof_cap_screen: int
    dof_cap_verify: int
    dof_cap_final: int
    dof_per_triangle: float
    max_triangle_slack: float = 1.15
    rear_res_factor: float = 1.0       # WP7: scale ONLY the outer shell/rear-cap resolution
    band_split: dict | None = None     # WP8: {"edges_hz": [...]} -> one mesh per band (absent = today)

    def dof_cap(self, mode: str) -> int:
        return int(getattr(self, f"dof_cap_{mode}"))


@dataclass
class SolveSettings:
    backend: str
    distance_m: float
    angle_count: int
    balloon: bool
    balloon_points_screen: int
    balloon_points_verify: int
    gmres_tol: float
    timeout_s: float
    cuda_fused: bool = False   # WP15: opt-in fused CUDA Burton-Miller assembly (beat_cuda only)
    source_motion: str = "normal"   # WP5: 'normal' (breathing cap, today) | 'axial' (rigid piston)
    # WP14: CPU-validation knobs that mirror hornlab_beat_bem's own SolveConfig field names
    # (config.py: near_correction/cutoff/order/solve_precision). None = absent = today, bit-for-bit.
    # near_correction + solve_precision='double' are BEAT CPU features; the library refuses every
    # accelerator (NEAR_CORRECTION_REFUSALS) and double precision off the CPU backend.
    near_correction: bool | None = None
    near_correction_cutoff: float | None = None
    near_correction_order: int | None = None
    solve_precision: str | None = None
    # WP16: J0 source-profile angle (radians), mirroring hornlab_beat_bem's own SolveConfig field
    # name. None = absent = today. 0.0 is an explicit no-op; the sign flips the profile phase.
    # The library validates the rest and REFUSES every path but fused CUDA
    # (source_profile_alpha is a fused-CUDA-only feature).
    source_profile_alpha: float | None = None

    def balloon_points(self, mode: str) -> int:
        if not self.balloon:
            return 0
        return int(self.balloon_points_screen if mode == "screen" else self.balloon_points_verify)


@dataclass
class SearchSettings:
    algorithm: str
    sigma0: float
    seed: int
    budget: int
    popsize: int | None
    tolfun: float
    infeasible_penalty: str = "flat"   # WP3: 'flat' (default, today) | 'graded'
    restarts: dict | None = None       # WP11a: {"mode": ipop|bipop, "max": N} (absent = today)
    qd: dict | None = None             # WP11b: CMA-ME descriptors/bins (absent = today)


@dataclass
class Config:
    name: str
    family: str
    seed_params: dict
    bounds_raw: dict            # key -> {lo, hi, search, log}
    target_raw: dict
    weights: dict
    mesh: MeshSettings
    solve: SolveSettings
    search: SearchSettings
    raw: dict
    brief: dict | None = None        # design brief (docs/TYPOLOGY_PLAN.md s3), if one was applied
    generator: dict | None = None    # typology generator block (s4); family is then FREEFORM
    objective_version: int = 1       # WP1: brief/config `objective: {version: 2}` -> v2 objective
    grid: dict | None = None         # WP4: brief `grid: {verify_points_per_octave: N}` -> HF verify grid
    mounting: dict | None = None     # WP12: brief `mounting` (normalized); absent = freestanding
    objective_params: dict | None = None  # v4: the normalised objective block (tolerances...)


# ------------------------------------------------------------------ briefs

BRIEF_SYMMETRY = ("hv", "axisymmetric")

# WP12: the SEARCH-side ``mounting`` block. The only mounting model this build supports is the
# mesher's rear enclosure; the only plan token is the rounded rectangle, because that is the ONLY
# plan with a watertight enclosure builder on closed/reduced domains (plan_type 2/3 are refused by
# hornlab_mesher). The normalized dict this module stores/broadcasts carries the mesher's own
# defaults for absent optional keys (margins 25 mm, edge 18 mm), so downstream code never invents
# a default of its own.
MOUNTING_TYPES = ("enclosure",)
MOUNTING_PLANS = {"rounded_rectangle": 1}
MOUNTING_KEYS = ("type", "depth_mm", "margins_mm", "edge_mm", "plan")
MOUNTING_MARGIN_SIDES = ("l", "t", "r", "b")
MOUNTING_DEFAULT_MARGIN_MM = 25.0    # hornlab_mesher HornEnclosure.space_*_mm default
MOUNTING_DEFAULT_EDGE_MM = 18.0      # hornlab_mesher HornEnclosure.edge_mm default


def _resolve_path(p, *bases) -> Path:
    p = Path(p)
    if p.is_absolute() or p.exists():
        return p
    for b in bases:
        if b is not None and (Path(b) / p).exists():
            return Path(b) / p
    return p


def load_brief(path) -> dict:
    """A design brief: driver exit, size envelope, symmetry class, source cap, target and weights
    (docs/TYPOLOGY_PLAN.md s3). It makes J comparable across typologies. Raises ConfigError."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    where = f"brief {path.name}"
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: top level must be a mapping")
    allowed = {"name", "description", "driver", "envelope", "symmetry", "source", "target", "weights",
               "verify_only", "objective", "grid", "mounting", "meh"}
    unknown = set(raw) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {sorted(unknown)}")
    for k in ("name", "driver", "envelope", "symmetry", "target", "weights"):
        _require(raw, k, where)
    drv, env = raw["driver"], raw["envelope"]
    for k in ("exit_radius_mm", "exit_angle_deg"):
        if not isinstance(drv.get(k), (int, float)):
            raise ConfigError(f"{where}: driver.{k} must be a number")
    if not 0 < float(drv["exit_radius_mm"]) < 100 or not 0 <= float(drv["exit_angle_deg"]) < 45:
        raise ConfigError(f"{where}: driver exit radius must be in (0, 100) mm and angle in [0, 45) deg")
    pol = drv.get("throat_angle_policy")
    if pol is not None and pol not in ("pin", "free"):
        raise ConfigError(f"{where}: driver.throat_angle_policy must be 'pin' or 'free', got {pol!r}")
    if "objective" in raw and raw["objective"] is not None:
        _validate_objective_block(raw["objective"], where)
    if "grid" in raw and raw["grid"] is not None:
        _validate_grid_block(raw["grid"], where)
    if "mounting" in raw and raw["mounting"] is not None:
        _validate_mounting_block(raw["mounting"], where)
    meh_cfg = None
    if "meh" in raw and raw["meh"] is not None:
        meh_cfg = _validate_meh_block(raw["meh"], f"{where}:meh")
    for k in ("max_mouth_w_mm", "max_mouth_h_mm", "max_depth_mm"):
        if not isinstance(env.get(k), (int, float)) or not float(env[k]) > 0:
            raise ConfigError(f"{where}: envelope.{k} must be a positive number")
    if not isinstance(raw.get("verify_only", False), bool):
        raise ConfigError(f"{where}: verify_only must be true or false")
    if raw["symmetry"] not in BRIEF_SYMMETRY:
        raise ConfigError(f"{where}: symmetry must be one of {list(BRIEF_SYMMETRY)}")
    cap = (raw.get("source") or {}).get("cap", "auto")
    if not (cap == "auto" or (isinstance(cap, (int, float)) and float(cap) > 0)):
        raise ConfigError(f"{where}: source.cap must be 'auto' or a positive radius in mm")
    from .targets.spec import Target
    try:
        t = Target.from_dict(dict(raw["target"]))
    except ValueError as exc:
        raise ConfigError(f"{where}: {exc}") from None
    if raw["symmetry"] == "axisymmetric" and t.coverage_h_deg != t.coverage_v_deg:
        raise ConfigError(f"{where}: an axisymmetric brief needs coverage_h_deg == coverage_v_deg")
    out = dict(raw)
    out["source"] = {"cap": cap}
    out["path"] = str(path)
    if meh_cfg is not None:
        out["meh"] = meh_cfg
    return out


# ------------------------------------------------------------------ loading

class ConfigError(ValueError):
    """A YAML config is missing a required key or has an illegal value."""


def _require(section: dict, key: str, where: str):
    if key not in section or section[key] is None:
        raise ConfigError(f"{where}: missing required key '{key}'")
    return section[key]


# ------------------------------------------------------------------ WP1/WP4 blocks (senior pass)

def _validate_objective_block(block, where: str) -> dict:
    """Brief/config ``objective: {version: 2|3|4|5|6}`` (WP1; v3 = the 2026-10-25 owner-approved
    K-law-masked coverage scoring - see objective/scalar_v2.py objective_v3; v4 = the 2026-10-27
    tolerance-normalised objective, whose block also carries ``tolerances`` and the optional
    ``cov_narrow_ratio`` / ``cov_below_f0`` / ``diag_reference`` - see objective/scalar_v4.py;
    v5 = the MEH system objective, whose block is v4's shape with the C11 defaults when
    ``tolerances`` is omitted - see objective/scalar_meh.py;
    v6 = loading_smooth for Le Cléac'h / rollback - see objective/scalar_v6.py). Default 1.
    Unknown keys are refused so a YAML typo is never silent."""
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: objective must be a mapping")
    v = block.get("version", 1)
    if isinstance(v, bool) or not isinstance(v, int) or v not in (1, 2, 3, 4, 5, 6):
        raise ConfigError(f"{where}: objective.version must be 1, 2, 3, 4, 5 or 6, got {v!r}")
    if v == 4:
        from .objective.scalar_v4 import V4Params
        try:
            return V4Params.from_block(block).to_block()
        except ValueError as e:
            raise ConfigError(f"{where}: {e}") from None
    if v == 5:
        from .objective.scalar_meh import MehParams
        try:
            return MehParams.from_block(block).to_block()
        except ValueError as e:
            raise ConfigError(f"{where}: {e}") from None
    if v == 6:
        from .objective.scalar_v6 import V6Params
        try:
            return V6Params.from_block(block).to_block()
        except ValueError as e:
            raise ConfigError(f"{where}: {e}") from None
    unknown = set(block) - {"version"}
    if unknown:
        raise ConfigError(f"{where}: objective unknown key(s) {sorted(unknown)} (allowed: version)")
    return {"version": int(v)}


def _validate_grid_block(block, where: str) -> dict:
    """Brief ``grid: {verify_points_per_octave: N}`` (WP4): build the verify grid as the frozen
    grid PLUS extra log points in [5 kHz, band_hi] at that density. It forms a NEW grid group:
    records carry it via their own solve.freqs_hz, and comparisons against runs with a different
    grid refuse (intended separation)."""
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: grid must be a mapping")
    unknown = set(block) - {"verify_points_per_octave"}
    if unknown:
        raise ConfigError(f"{where}: grid unknown key(s) {sorted(unknown)} "
                          f"(allowed: verify_points_per_octave)")
    ppo = block.get("verify_points_per_octave")
    if isinstance(ppo, bool) or not isinstance(ppo, (int, float)) or not ppo > 0:
        raise ConfigError(f"{where}: grid.verify_points_per_octave must be a positive number")
    return {"verify_points_per_octave": float(ppo)}


# ------------------------------------------------------------------ WP12 mounting block


def _mounting_mm(value, where: str, *, positive: bool) -> float:
    """One finite number from a mounting block. ``positive`` -> strictly > 0, else >= 0."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not np.isfinite(float(value)):
        bound = "> 0" if positive else ">= 0"
        raise ConfigError(f"{where} must be a finite number {bound} (mm), got {value!r}")
    v = float(value)
    if (positive and v <= 0.0) or (not positive and v < 0.0):
        bound = "> 0" if positive else ">= 0"
        raise ConfigError(f"{where} must be a finite number {bound} (mm), got {value!r}")
    return v


def _validate_mounting_block(block, where: str) -> dict:
    """Brief ``mounting: {type: enclosure, depth_mm, margins_mm, edge_mm, plan}`` (WP12).

    The block is the SEARCH-side schema; it is translated onto the mesher's own top-level
    ``enclosure`` keys in ``design/families.to_mesher_config`` (one shared helper, no invented
    mesher keys). Exact keys, so a YAML typo is never silent:

    * ``type`` is REQUIRED and must be ``enclosure``. An absent block is freestanding (today);
      there is deliberately no ``type: freestanding`` spelling.
    * ``depth_mm`` is REQUIRED and > 0 (mm); <= 0 would mean "no enclosure" to the mesher, which
      is exactly what an absent block already says.
    * ``margins_mm`` is a positive scalar OR a mapping with any subset of ``l/t/r/b`` (each > 0);
      omitted sides are the mesher's own 25 mm default. It is always normalized to
      ``{"l": x, "t": y, "r": z, "b": w}`` here.
    * ``edge_mm`` >= 0 (0 = sharp), defaulting to the mesher's 18 mm.
    * ``plan`` is a token from ``MOUNTING_PLANS`` (only ``rounded_rectangle``): the mesher refuses
      plan_type 2/3 on closed/reduced domains, so a search brief never silently picks one.

    The returned dict is the normalized block stored on ``Config.mounting`` and echoed in run
    provenance/config.yaml + the mesh cache key.
    """
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: mounting must be a mapping")
    unknown = set(block) - set(MOUNTING_KEYS)
    if unknown:
        raise ConfigError(f"{where}: mounting unknown key(s) {sorted(unknown)} "
                          f"(allowed: {list(MOUNTING_KEYS)})")
    kind = block.get("type")
    if kind not in MOUNTING_TYPES:
        raise ConfigError(
            f"{where}: mounting.type must be one of {list(MOUNTING_TYPES)} (omit the block for a "
            f"freestanding horn), got {kind!r}")
    if "depth_mm" not in block:
        raise ConfigError(f"{where}: missing required key 'mounting.depth_mm'")
    depth_mm = _mounting_mm(block["depth_mm"], f"{where}: mounting.depth_mm", positive=True)

    margins_raw = block.get("margins_mm", MOUNTING_DEFAULT_MARGIN_MM)
    if isinstance(margins_raw, dict):
        unknown = set(margins_raw) - set(MOUNTING_MARGIN_SIDES)
        if unknown:
            raise ConfigError(f"{where}: mounting.margins_mm unknown side(s) {sorted(unknown)} "
                              f"(allowed: {list(MOUNTING_MARGIN_SIDES)})")
        margins = {
            side: _mounting_mm(margins_raw.get(side, MOUNTING_DEFAULT_MARGIN_MM),
                              f"{where}: mounting.margins_mm.{side}", positive=True)
            for side in MOUNTING_MARGIN_SIDES
        }
    else:
        v = _mounting_mm(margins_raw, f"{where}: mounting.margins_mm", positive=True)
        margins = {side: v for side in MOUNTING_MARGIN_SIDES}

    edge_mm = _mounting_mm(block.get("edge_mm", MOUNTING_DEFAULT_EDGE_MM),
                           f"{where}: mounting.edge_mm", positive=False)
    plan = block.get("plan", "rounded_rectangle")
    if not isinstance(plan, str) or plan not in MOUNTING_PLANS:
        raise ConfigError(
            f"{where}: mounting.plan must be one of {sorted(MOUNTING_PLANS)} (the only enclosure "
            f"plan hornlab_mesher builds on closed/reduced domains), got {plan!r}")
    return {
        "type": "enclosure",
        "depth_mm": depth_mm,
        "margins_mm": margins,
        "edge_mm": edge_mm,
        "plan": plan,
    }


# ------------------------------------------------------------------ MEH brief block (C10)

#: The C10 ``meh:`` brief block: every key is required (M7's inner optimiser and limits read all
#: of them, and a missing one has no honest default at the brief level).
MEH_KEYS = ("groups", "hp_hz", "xo_hz", "xo_orders", "delay_ms", "v_front_fill", "v_rear_l",
            "amp_v_rms", "port_air_mps_max", "max_boost_db", "spl_target", "listening_window")
MEH_GROUP_KEYS = ("cd", "mid")
#: C3: the only MEH tags this build knows. ``cd`` is the driver tag, ``mid`` the entry_mid tag.
MEH_GROUP_TAGS = {"cd": 2, "mid": 10}
#: C8: the driver-file kind each group must reference (M1 creates those files).
MEH_GROUP_KINDS = {"cd": "compression_meh", "mid": "cone"}
MEH_XO_ORDERS = (2, 4, 8)


def _meh_number(value, where: str, lo: float | None = None, hi: float | None = None) -> float:
    """One finite number, optionally inside the inclusive [lo, hi] range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not np.isfinite(float(value)):
        raise ConfigError(f"{where} must be a finite number, got {value!r}")
    v = float(value)
    if lo is not None and v < float(lo):
        raise ConfigError(f"{where} must be >= {lo:g}, got {v!r}")
    if hi is not None and v > float(hi):
        raise ConfigError(f"{where} must be <= {hi:g}, got {v!r}")
    return v


def _meh_range(block, key: str, where: str, lo: float, hi: float, *,
               strict: bool = False) -> dict:
    """A ``{lo, hi}`` sub-block, both endpoints in [lo, hi], with ``lo`` < (or <=) ``hi``."""
    sub = block.get(key)
    if not isinstance(sub, dict):
        raise ConfigError(f"{where}.{key} must be a mapping with keys lo and hi")
    unknown = set(sub) - {"lo", "hi"}
    if unknown:
        raise ConfigError(f"{where}.{key} unknown key(s) {sorted(unknown)} (allowed: lo, hi)")
    for edge in ("lo", "hi"):
        if edge not in sub:
            raise ConfigError(f"{where}.{key} missing required key '{edge}'")
    a = _meh_number(sub["lo"], f"{where}.{key}.lo", lo, hi)
    b = _meh_number(sub["hi"], f"{where}.{key}.hi", lo, hi)
    if (a >= b) if strict else (a > b):
        cmp = "lo < hi" if strict else "lo <= hi"
        raise ConfigError(f"{where}.{key} needs {cmp}, got lo={a:g}, hi={b:g}")
    return {"lo": a, "hi": b}


def _meh_driver_files(block: dict, where: str, drivers_dir) -> None:
    """Check every driver stem's file and kind. A MISSING file is a warning until M1 lands."""
    root = Path(drivers_dir) if drivers_dir is not None \
        else Path(__file__).resolve().parents[1] / "examples" / "drivers"
    for group_name, group in block.items():
        expected = MEH_GROUP_KINDS[group_name]
        for stem in group["drivers"]:
            stem_path = Path(str(stem))
            candidates = ([stem_path] if stem_path.is_absolute()
                          else [root / f"{stem_path}.yaml", root / f"{stem_path}.yml"])
            found = next((p for p in candidates if p.exists()), None)
            if found is None:
                # M1 runs in parallel with M6: a missing stem must not make every MEH brief
                # unloadable while the driver files have not landed yet.  The warning names the
                # exact path so a typo is still visible in the log.
                log.warning("%s.groups.%s: driver file %s is missing; MEH validation continues "
                            "(M1 has not landed)", where, group_name, candidates[0])
                continue
            try:
                raw = yaml.safe_load(found.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                raise ConfigError(f"{where}.groups.{group_name}: cannot read driver file "
                                  f"{found}: {exc}") from None
            kind = raw.get("kind") if isinstance(raw, dict) else None
            if kind != expected:
                raise ConfigError(
                    f"{where}.groups.{group_name}: driver file {found.name!r} has kind {kind!r}, "
                    f"expected {expected!r} for the {group_name} group")


def _validate_meh_block(block, where: str, drivers_dir=None) -> dict:
    """Validate the C10 ``meh:`` brief block. Exact keys, types and ranges; unknown keys refuse.

    Ranges are the task's (M6 brief): hp_hz 60-250; xo lo < hi inside 300-3000; xo_orders a
    subset of {2, 4, 8}; delay -3..3 ms; fill 0..0.9; rear chamber 0.2..20 L; amp 5..200 V RMS;
    port air 5..40 m/s; boost 0..12 dB; spl_target sorted by frequency with dB 80..140.  Driver
    stems are checked against ``examples/drivers/`` (kind from C8); a missing file is a warning,
    never a failure, while M1 has not landed.
    """
    if not isinstance(block, dict):
        raise ConfigError(f"{where} must be a mapping")
    unknown = set(block) - set(MEH_KEYS)
    if unknown:
        raise ConfigError(f"{where} unknown key(s) {sorted(unknown)} (allowed: {list(MEH_KEYS)})")
    missing = [k for k in MEH_KEYS if k not in block or block[k] is None]
    if missing:
        raise ConfigError(f"{where} missing required key(s) {missing}")

    # groups: cd (tag 2, exactly one driver) and mid (tag 10, count >= 1, one or more candidates).
    groups = block["groups"]
    if not isinstance(groups, dict):
        raise ConfigError(f"{where}.groups must be a mapping with keys cd and mid")
    unknown = set(groups) - set(MEH_GROUP_KEYS)
    if unknown:
        raise ConfigError(f"{where}.groups unknown key(s) {sorted(unknown)} "
                          f"(allowed: {list(MEH_GROUP_KEYS)})")
    missing = [k for k in MEH_GROUP_KEYS if k not in groups]
    if missing:
        raise ConfigError(f"{where}.groups missing required key(s) {missing}")
    clean_groups = {}
    for name in MEH_GROUP_KEYS:
        g = groups[name]
        if not isinstance(g, dict):
            raise ConfigError(f"{where}.groups.{name} must be a mapping")
        allowed = {"tag", "drivers"} if name == "cd" else {"tag", "count", "drivers"}
        unknown = set(g) - allowed
        if unknown:
            raise ConfigError(f"{where}.groups.{name} unknown key(s) {sorted(unknown)} "
                              f"(allowed: {sorted(allowed)})")
        for key in allowed:
            if key not in g:
                raise ConfigError(f"{where}.groups.{name} missing required key '{key}'")
        tag = g["tag"]
        expected_tag = MEH_GROUP_TAGS[name]
        if isinstance(tag, bool) or not isinstance(tag, int) or tag != expected_tag:
            raise ConfigError(f"{where}.groups.{name}.tag must be {expected_tag} "
                              f"(C3's only MEH mapping), got {tag!r}")
        drivers = g["drivers"]
        if not isinstance(drivers, (list, tuple)) or not drivers:
            raise ConfigError(f"{where}.groups.{name}.drivers must be a non-empty list of stems")
        stems = []
        for stem in drivers:
            if not isinstance(stem, str) or not stem.strip():
                raise ConfigError(f"{where}.groups.{name}.drivers must contain non-empty strings, "
                                  f"got {stem!r}")
            stems.append(stem)
        if name == "cd" and len(stems) != 1:
            raise ConfigError(f"{where}.groups.cd.drivers must name exactly one CD file, "
                              f"got {len(stems)}")
        clean = {"tag": int(tag), "drivers": stems}
        if name == "mid":
            count = g["count"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise ConfigError(f"{where}.groups.mid.count must be an integer >= 1, got {count!r}")
            clean["count"] = int(count)
        clean_groups[name] = clean

    hp_hz = _meh_number(block["hp_hz"], f"{where}.hp_hz", 60.0, 250.0)
    xo_hz = _meh_range(block, "xo_hz", where, 300.0, 3000.0, strict=True)

    orders = block["xo_orders"]
    if not isinstance(orders, (list, tuple)) or not orders:
        raise ConfigError(f"{where}.xo_orders must be a non-empty list of Linkwitz-Riley orders")
    clean_orders = []
    for order in orders:
        if isinstance(order, bool) or not isinstance(order, int) or order not in MEH_XO_ORDERS:
            raise ConfigError(f"{where}.xo_orders must be a subset of {list(MEH_XO_ORDERS)}, "
                              f"got {order!r}")
        if order in clean_orders:
            raise ConfigError(f"{where}.xo_orders contains duplicate order {order}")
        clean_orders.append(int(order))

    delay = _meh_range(block, "delay_ms", where, -3.0, 3.0)
    fill = _meh_range(block, "v_front_fill", where, 0.0, 0.9)
    rear = _meh_range(block, "v_rear_l", where, 0.2, 20.0)
    amp = _meh_number(block["amp_v_rms"], f"{where}.amp_v_rms", 5.0, 200.0)
    port_air = _meh_number(block["port_air_mps_max"], f"{where}.port_air_mps_max", 5.0, 40.0)
    boost = _meh_number(block["max_boost_db"], f"{where}.max_boost_db", 0.0, 12.0)

    spl = block["spl_target"]
    if not isinstance(spl, (list, tuple)) or len(spl) < 2:
        raise ConfigError(f"{where}.spl_target must be a list of at least two [Hz, dB] points")
    clean_spl = []
    for i, point in enumerate(spl):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ConfigError(f"{where}.spl_target[{i}] must be a [Hz, dB] pair, got {point!r}")
        f_hz = _meh_number(point[0], f"{where}.spl_target[{i}][0]", 1e-9, None)
        db = _meh_number(point[1], f"{where}.spl_target[{i}][1]", 80.0, 140.0)
        if clean_spl and f_hz <= clean_spl[-1][0]:
            raise ConfigError(f"{where}.spl_target must be strictly increasing in frequency, "
                              f"got {clean_spl[-1][0]:g} then {f_hz:g} Hz")
        clean_spl.append([f_hz, db])

    window = block["listening_window"]
    if not isinstance(window, dict):
        raise ConfigError(f"{where}.listening_window must be a mapping with h_deg and v_deg")
    unknown = set(window) - {"h_deg", "v_deg"}
    if unknown:
        raise ConfigError(f"{where}.listening_window unknown key(s) {sorted(unknown)} "
                          f"(allowed: h_deg, v_deg)")
    clean_window = {}
    for axis in ("h_deg", "v_deg"):
        if axis not in window:
            raise ConfigError(f"{where}.listening_window missing required key '{axis}'")
        angles = window[axis]
        if not isinstance(angles, (list, tuple)) or not angles:
            raise ConfigError(f"{where}.listening_window.{axis} must be a non-empty list of degrees")
        clean_window[axis] = [
            _meh_number(a, f"{where}.listening_window.{axis}") for a in angles
        ]

    _meh_driver_files(clean_groups, where, drivers_dir)

    return {
        "groups": clean_groups,
        "hp_hz": hp_hz,
        "xo_hz": xo_hz,
        "xo_orders": clean_orders,
        "delay_ms": delay,
        "v_front_fill": fill,
        "v_rear_l": rear,
        "amp_v_rms": amp,
        "port_air_mps_max": port_air,
        "max_boost_db": boost,
        "spl_target": clean_spl,
        "listening_window": clean_window,
    }


# ------------------------------------------------------------------ WP5/WP7/WP8 blocks

def _validate_rear_res_factor(value, where: str) -> float:
    """WP7: ``mesh.rear_res_factor`` scales ONLY the rear/outer-shell resolution. Any positive
    finite factor is legal (values > 1 coarsen); 1.0 is today's mesh."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not np.isfinite(float(value)) or float(value) <= 0.0:
        raise ConfigError(f"{where}: rear_res_factor must be a finite positive number, got {value!r}")
    return float(value)


def _validate_band_split(block, where: str, band_lo: float, band_hi: float) -> dict | None:
    """WP8: ``mesh.band_split: {edges_hz: [...]}``. Edges are strictly increasing and lie strictly
    inside the target band; at least one edge. Absent/None keeps today's single-mesh policy."""
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: band_split must be a mapping")
    unknown = set(block) - {"edges_hz"}
    if unknown:
        raise ConfigError(f"{where}: band_split unknown key(s) {sorted(unknown)} (allowed: edges_hz)")
    edges = block.get("edges_hz")
    if not isinstance(edges, (list, tuple)) or not edges:
        raise ConfigError(f"{where}: band_split.edges_hz must be a non-empty list of numbers")
    vals = []
    for e in edges:
        if isinstance(e, bool) or not isinstance(e, (int, float)) or not np.isfinite(float(e)):
            raise ConfigError(f"{where}: band_split.edges_hz must contain finite numbers, got {e!r}")
        vals.append(float(e))
    if any(b <= a for a, b in zip(vals, vals[1:])):
        raise ConfigError(f"{where}: band_split.edges_hz must be strictly increasing, got {vals}")
    for e in vals:
        if not (band_lo < e < band_hi):
            raise ConfigError(
                f"{where}: band_split edge {e:g} Hz is outside the open target band "
                f"({band_lo:g}, {band_hi:g}) Hz")
    return {"edges_hz": vals}


def _validate_restarts(block, where: str) -> dict | None:
    """WP11a: ``search.restarts: {mode: ipop|bipop, max: N}`` runs CMA-ES with pycma's own
    IPOP/BIPOP restart schedule (``max`` restarts after the initial attempt). It is a SEARCH-ONLY
    key: it never enters the solve-spec hash, and absent/None keeps today's single-ES behaviour
    bit-for-bit. Unknown sub-keys and missing ones are refused so a YAML typo is never silent."""
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: restarts must be a mapping with keys mode and max")
    unknown = set(block) - {"mode", "max"}
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {sorted(unknown)} (allowed: mode, max)")
    for key in ("mode", "max"):
        if key not in block:
            raise ConfigError(f"{where}: missing required key '{key}'")
    mode = block["mode"]
    if not isinstance(mode, str) or mode not in ("ipop", "bipop"):
        raise ConfigError(f"{where}: mode must be 'ipop' or 'bipop', got {mode!r}")
    mx = block["max"]
    if isinstance(mx, bool) or not isinstance(mx, int) or not (0 <= mx <= 64):
        raise ConfigError(f"{where}: max must be an integer in [0, 64], got {mx!r}")
    return {"mode": mode, "max": int(mx)}


def _validate_qd(block, where: str) -> dict | None:
    """WP11b: ``search.qd`` selects the two CMA-ME descriptors and the archive's bin counts.

    Exact sub-keys: ``descriptor_h``, ``descriptor_v`` (each a name from ``QD_DESCRIPTORS``) and
    ``bins_h``, ``bins_v`` (integers in [2, 64]). ALL FOUR are required when the block is present;
    there is deliberately no silent default. It is a SEARCH-ONLY key: it never enters the
    solve-spec hash. Unknown sub-keys, unknown descriptor names and mis-typed bins are refused with
    a ``search.qd`` prefix so a YAML typo is never silent."""
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: qd must be a mapping with keys "
                          f"descriptor_h, descriptor_v, bins_h, bins_v")
    unknown = set(block) - {"descriptor_h", "descriptor_v", "bins_h", "bins_v"}
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {sorted(unknown)} "
                          f"(allowed: descriptor_h, descriptor_v, bins_h, bins_v)")
    names = {}
    for key in ("descriptor_h", "descriptor_v"):
        if key not in block:
            raise ConfigError(f"{where}: missing required key '{key}'")
        v = block[key]
        if not isinstance(v, str) or v not in QD_DESCRIPTORS:
            raise ConfigError(f"{where}: {key} must be one of {list(QD_DESCRIPTORS)}, got {v!r}")
        names[key] = v
    out = dict(names)
    for key in ("bins_h", "bins_v"):
        if key not in block:
            raise ConfigError(f"{where}: missing required key '{key}'")
        v = block[key]
        if isinstance(v, bool) or not isinstance(v, int) or not (2 <= v <= 64):
            raise ConfigError(f"{where}: {key} must be an integer in [2, 64], got {v!r}")
        out[key] = int(v)
    return out


def _validate_near_correction(solve, where: str) -> None:
    """WP14: validate ``solve.near_correction*`` / ``solve.solve_precision`` BEFORE the library
    sees them. The bounds mirror hornlab_beat_bem's own SolveConfig (near_correction_cutoff finite
    and > 0; near_correction_order an integer >= 4; solve_precision in {'single','double'}), so a
    typo is refused here with a clear message instead of after a worker/host is built. ``None``
    (key absent) leaves today's behaviour byte-for-byte untouched.

    near-singular correction and double precision are BEAT features: only the CPU device path
    implements them. A non-beat backend with a non-default value is refused loudly, exactly like
    ``source_motion`` below."""
    nc = solve.near_correction
    if nc is not None and not isinstance(nc, bool):
        raise ConfigError(f"{where}: near_correction must be a boolean, got {nc!r}")
    cutoff = solve.near_correction_cutoff
    if cutoff is not None:
        try:
            cutoff = float(cutoff)
        except (TypeError, ValueError, OverflowError):
            raise ConfigError(
                f"{where}: near_correction_cutoff must be a finite number > 0, got {cutoff!r}") from None
        if not np.isfinite(cutoff) or cutoff <= 0.0:
            raise ConfigError(
                f"{where}: near_correction_cutoff must be finite and greater than zero "
                f"(hornlab_beat_bem's own SolveConfig requires it), got {cutoff!r}")
        solve.near_correction_cutoff = cutoff
    order = solve.near_correction_order
    if order is not None:
        ok = not isinstance(order, bool) and isinstance(order, (int, float)) and float(order).is_integer()
        if not ok or int(order) < 4:
            raise ConfigError(
                f"{where}: near_correction_order must be an integer >= 4 "
                f"(hornlab_beat_bem's own minimum; it validates too), got {order!r}")
        solve.near_correction_order = int(order)
    precision = solve.solve_precision
    if precision is not None and precision not in ("single", "double"):
        raise ConfigError(
            f"{where}: solve_precision must be 'single' or 'double', got {precision!r}")
    backend = str(solve.backend)
    near_requested = (bool(nc) or solve.near_correction_cutoff is not None
                      or solve.near_correction_order is not None)
    precision_requested = precision is not None and precision != "single"
    if (near_requested or precision_requested) and not backend.startswith("beat_"):
        raise ConfigError(
            f"{where}: near_correction/solve_precision are only implemented for the beat backends "
            f"(beat_cpu/beat_cuda), got backend {backend!r} (near-singular correction and double "
            f"precision are BEAT CPU features)")


def _validate_source_profile_alpha(solve, where: str) -> None:
    """WP16: validate ``solve.source_profile_alpha`` BEFORE the library sees it.

    The only rule mirrored here is the library's own: the value must be a finite float. Any finite
    value is accepted -- 0.0 is an explicit no-op, and a negative angle is meaningful (the sign
    flips the J0 source profile's phase); no magnitude cap is invented. The library validates the
    remainder (fused-CUDA-only refusal) and ``BeatBackend.make_config`` surfaces that refusal
    early. ``None`` (key absent) leaves today's behaviour byte-for-byte untouched.

    The knob is a BEAT feature (the fused CUDA path): a non-beat backend with a non-zero value is
    refused loudly, in the same tone as ``near_correction``/``solve_precision`` above."""
    alpha = solve.source_profile_alpha
    if alpha is None:
        return
    if isinstance(alpha, bool):
        raise ConfigError(f"{where}: source_profile_alpha must be a finite number, got {alpha!r}")
    try:
        alpha = float(alpha)
    except (TypeError, ValueError, OverflowError):
        raise ConfigError(
            f"{where}: source_profile_alpha must be a finite number, got {alpha!r}") from None
    if not np.isfinite(alpha):
        raise ConfigError(
            f"{where}: source_profile_alpha must be finite "
            f"(hornlab_beat_bem's own SolveConfig requires it), got {alpha!r}")
    solve.source_profile_alpha = alpha
    backend = str(solve.backend)
    if alpha != 0.0 and not backend.startswith("beat_"):
        raise ConfigError(
            f"{where}: source_profile_alpha is only implemented for the beat backends "
            f"(beat_cuda, fused path), got backend {backend!r} (the profile source is a "
            f"fused-CUDA feature)")


def _validate_source_motion(value, backend: str, where: str) -> str:
    """WP5: ``solve.source_motion`` is 'normal' (today) or 'axial' (rigid piston). Only the beat
    adapter implements it; a non-beat backend with a non-default value is refused loudly."""
    if not isinstance(value, str) or value not in ("normal", "axial"):
        raise ConfigError(f"{where}: source_motion must be 'normal' or 'axial', got {value!r}")
    if value != "normal" and not str(backend).startswith("beat_"):
        raise ConfigError(
            f"{where}: source_motion={value!r} is only implemented for the beat backends "
            f"(beat_cuda/beat_metal/beat_cpu), got backend {backend!r}")
    return value


# ------------------------------------------------------------------ WP2 driver fairness

_PIN_FAMILIES = ("OSSE", "R-OSSE", "ICW")
_DRIVER_PIN_TOL = 0.01


def _force_pin(key: str, value: float, seed: dict, bounds: dict, where: str, unit: str,
               nested: bool = False) -> None:
    """WP2: force one design parameter onto the brief's driver value.

    A config that already PINS the parameter (``search: false``) at a different value raises
    ConfigError — silently rescaling a horn is worse. A searching bound is replaced by
    lo=hi=value, search: false, and the seed param is set to the same value so the seed design
    matches the brief's driver. For nested FREEFORM keys (``profileH.throatAngleDeg``) the bound
    keeps its flat dotted-path form and the seed param is set inside its plane node."""
    b = bounds.get(key)
    if isinstance(b, dict) and not b.get("search", True):
        lo, hi = float(b.get("lo", value)), float(b.get("hi", value))
        if abs(lo - value) > _DRIVER_PIN_TOL or abs(hi - value) > _DRIVER_PIN_TOL:
            raise ConfigError(
                f"{where}: bounds.{key} is pinned at [{lo}, {hi}] {unit} but the applied brief "
                f"pins the driver at {value} {unit}; rescale the horn explicitly or drop the pin "
                f"(WP2 driver fairness, senior pass 2026-10-24)")
        return
    bounds[key] = {"lo": value, "hi": value, "search": False}
    if nested:
        plane, _, leaf = key.partition(".")
        node = seed.get(plane)
        if isinstance(node, dict):
            node[leaf] = value
    else:
        seed[key] = value


def _apply_brief_driver_pins(raw: dict, brief_d: dict | None, where: str,
                             embedded: bool = False) -> None:
    """WP2 (senior pass 2026-10-24, fairness): when a brief is applied to a NATIVE family config
    (no ``generator:``), pin the horn's throat to the brief's driver, so every family competes on
    the same objective instead of each searching its own throat. Generator typologies already do
    this inside registry.materialize; their configs are untouched here.

    - OSSE / R-OSSE / ICW: ``r0_mm`` is pinned to ``driver.exit_radius_mm`` (always; the brief
      defines the throat size a design is allowed to use), and ``a0_deg`` is pinned to
      ``driver.exit_angle_deg`` ONLY when the brief says ``driver.throat_angle_policy: pin``.
      ICW keeps its throat in the nested ``icw_seed`` block (``icw_seed.r0_mm`` in seed_params,
      the flat dotted key in bounds), so that path is pinned by the same rule too.
    - Native FREEFORM: under ``pin``, ``profileH/V.throatAngleDeg`` are pinned to the exit angle.
    - A brief WITHOUT the policy key behaves exactly as before on throat angles, so every
      existing run reproduces bit-for-bit.
    - Oracle M1 ruling: ``embedded=True`` (a run directory's own merged config.yaml, the
      resume/verify/report path) SKIPS the pins entirely — a pre-WP2 run whose embedded brief
      conflicts with its pinned throat must stay loadable (bit-for-bit contract on old runs);
      fairness is enforced where the brief is applied fresh (``--brief`` or ``brief_file:``,
      including a NEW run's subprocess, which passes the brief freshly)."""
    if brief_d is None or embedded or raw.get("generator") is not None:
        return
    drv = brief_d.get("driver") or {}
    if not isinstance(drv.get("exit_radius_mm"), (int, float)):
        return  # a malformed driver was already refused inside load_brief
    exit_r = float(drv["exit_radius_mm"])
    exit_a = float(drv["exit_angle_deg"])
    policy = drv.get("throat_angle_policy")
    family = str(raw.get("family", ""))
    seed = raw.setdefault("seed_params", {})
    bounds = raw.setdefault("bounds", {})
    if family in _PIN_FAMILIES and ("r0_mm" in seed or "r0_mm" in bounds):
        _force_pin("r0_mm", exit_r, seed, bounds, where, "mm")
        if policy == "pin" and ("a0_deg" in seed or "a0_deg" in bounds):
            _force_pin("a0_deg", exit_a, seed, bounds, where, "deg")
    if family == "ICW":
        # Campaign 2026-10-26 Phase 0: ICW's throat is nested (seed icw_seed.r0_mm; bounds
        # carries the flat dotted key), so the root-only check above silently missed it.
        icw_seed = seed.get("icw_seed")
        if ((isinstance(icw_seed, dict) and "r0_mm" in icw_seed)
                or "icw_seed.r0_mm" in bounds):
            _force_pin("icw_seed.r0_mm", exit_r, seed, bounds, where, "mm", nested=True)
    if family == "FREEFORM" and policy == "pin":
        for plane in ("profileH", "profileV"):
            node = seed.get(plane)
            if isinstance(node, dict) and "throatAngleDeg" in node:
                _force_pin(f"{plane}.throatAngleDeg", exit_a, seed, bounds, where, "deg",
                           nested=True)


def _build(cls, section: dict, where: str, optional: tuple[str, ...] = ()):
    kwargs = {}
    for name in cls.__dataclass_fields__:
        if name in optional:
            if name in section:
                kwargs[name] = section[name]
            continue
        kwargs[name] = _require(section, name, where)
    unknown = set(section) - set(cls.__dataclass_fields__)
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {sorted(unknown)}")
    return cls(**kwargs)


def load_config(path, *, brief=None, cma_seed: int | None = None,
                backend: str | None = None) -> Config:
    """YAML -> Config. ``brief`` (a path; or the config's own ``brief:`` key) replaces the target
    and weights with the brief's and records the brief in ``raw`` so ``config_sha`` covers it.
    ``cma_seed`` overrides ``search.seed``. A ``generator:`` block makes this a typology config
    (family must be FREEFORM; ``seed_params``/``bounds`` then hold generator knobs).

    ``backend`` applies a CLI ``--backend`` override BEFORE validation and records it in ``raw`` so
    ``config_sha`` and the run snapshot match what actually ran. ``cuda_fused`` is CUDA-only and is
    dropped from ``raw`` when the effective backend is not ``beat_cuda`` (it must not survive an
    override and then trip ``solve.beat._assert_cuda_fused_path`` at the first solve)."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    where = path.name

    if backend is not None:
        solve_raw = raw.get("solve")
        if not isinstance(solve_raw, dict):
            raise ConfigError(f"{where}: solve block must be a mapping to apply the backend override")
        solve_raw["backend"] = str(backend)
        if str(solve_raw["backend"]) != "beat_cuda":
            solve_raw.pop("cuda_fused", None)

    brief_path = brief if brief is not None else raw.get("brief_file")
    brief_d = None
    embedded_brief = False
    if brief is None and isinstance(raw.get("brief"), dict):
        # A run directory's config.yaml already holds the merged brief (target/weights applied and
        # the brief embedded); use it as is, so resume/verify/report reproduce the run exactly.
        brief_d = dict(raw["brief"])
        brief_path = None
        embedded_brief = True
    obj_cfg = None
    if raw.get("objective") is not None:
        obj_cfg = _validate_objective_block(raw["objective"], where)
    if brief_path is not None:
        bp = _resolve_path(brief_path, path.parent, Path(__file__).resolve().parents[1])
        if not Path(bp).exists():
            raise ConfigError(
                f"{where}: brief_file {brief_path!r} could not be found; "
                f"tried relative to config dir ({path.parent}) and repo root. "
                f"Use an absolute path or a path relative to the config file."
            )
        brief_d = load_brief(bp)
        raw["target"] = dict(brief_d["target"])
        raw["weights"] = dict(brief_d["weights"])
        raw["brief"] = {k: v for k, v in brief_d.items() if k != "path"}
    if brief_d is not None and brief_d.get("objective") is not None:
        # A brief's objective version wins over the config's own block (the brief replaces the
        # target/weights pair it belongs to); recorded in raw so config_sha covers it.
        raw["objective"] = dict(brief_d["objective"])
    elif obj_cfg is not None:
        raw["objective"] = obj_cfg
    if brief_d is not None and brief_d.get("grid") is not None:
        raw["grid"] = dict(brief_d["grid"])
    grid_cfg = _validate_grid_block(raw["grid"], where) if raw.get("grid") is not None else None
    # WP12: a brief's mounting block is re-validated here (a run directory's embedded brief goes
    # through this path too) and normalized into raw so config_sha covers it; absent = freestanding.
    mounting_cfg = None
    if brief_d is not None and brief_d.get("mounting") is not None:
        mounting_cfg = _validate_mounting_block(brief_d["mounting"], f"{where}:mounting")
        raw["mounting"] = dict(mounting_cfg)
    # C10: the MEH block lives in the brief.  A fresh brief was already validated by load_brief;
    # an embedded run-directory brief goes through the same validator here (so a resume cannot
    # smuggle an unvalidated block), and the normalized form is stored in raw for config_sha.
    if brief_d is not None and brief_d.get("meh") is not None:
        meh_cfg = (_validate_meh_block(brief_d["meh"], f"{where}:meh")
                   if embedded_brief else dict(brief_d["meh"]))
        raw["brief"] = dict(raw.get("brief") or brief_d)
        raw["brief"]["meh"] = meh_cfg
    if cma_seed is not None:
        raw.setdefault("search", {})
        raw["search"] = dict(raw["search"], seed=int(cma_seed))
    gen = raw.get("generator")
    if gen is not None:
        if not isinstance(gen, dict) or "name" not in gen:
            raise ConfigError(f"{where}: generator must be a mapping with a 'name'")
        if raw.get("family") != "FREEFORM":
            raise ConfigError(f"{where}: a generator config must have family: FREEFORM")
        if brief_d is None:
            raise ConfigError(f"{where}: a generator config needs a brief (brief_file: or --brief)")
        # Opt-out from the f0 seed derivation (campaign 2026-10-26). ABSENT stays "derive",
        # which is exactly today's behaviour and leaves config_sha byte-identical.
        policy = gen.get("seed_policy", "derive")
        if policy not in ("derive", "explicit"):
            raise ConfigError(
                f"{where}: generator.seed_policy must be 'derive' or 'explicit', got {policy!r}")

    _apply_brief_driver_pins(raw, brief_d, where, embedded=embedded_brief)
    if not embedded_brief:
        raw = _brief_preflight_and_derive(raw, brief_d, where)

    mesh = _build(MeshSettings, _require(raw, "mesh", where), f"{where}:mesh",
                  optional=("max_triangle_slack", "rear_res_factor", "band_split"))
    solve_section = dict(_require(raw, "solve", where))
    if solve_section.get("freq_grid") is not None:
        _validate_freq_grid(solve_section["freq_grid"], f"{where}:solve")
        solve_section.pop("freq_grid")
    if "worker_restart_every" in solve_section:
        try:
            _restart = int(solve_section["worker_restart_every"])
        except (TypeError, ValueError):
            raise ConfigError(f"{where}:solve: worker_restart_every must be an integer") from None
        if _restart < 1:
            raise ConfigError(f"{where}:solve: worker_restart_every must be >= 1 (got {_restart})")
        solve_section.pop("worker_restart_every")
    solve = _build(SolveSettings, solve_section, f"{where}:solve",
                   optional=("cuda_fused", "source_motion", "near_correction",
                             "near_correction_cutoff", "near_correction_order",
                             "solve_precision", "source_profile_alpha"))
    if solve.cuda_fused and str(solve.backend) != "beat_cuda":
        raise ConfigError(f"{where}: solve.cuda_fused is only implemented for backend: beat_cuda "
                          f"(got {solve.backend!r})")
    mesh.rear_res_factor = _validate_rear_res_factor(mesh.rear_res_factor, f"{where}:mesh")
    if mesh.band_split is not None:                    # absent = today, no target keys touched
        try:
            band_lo = float(raw["target"]["band_lo_hz"])
            band_hi = float(raw["target"]["band_hi_hz"])
        except (KeyError, TypeError, ValueError):
            raise ConfigError(f"{where}: target.band_lo_hz/band_hi_hz are required numbers") from None
        mesh.band_split = _validate_band_split(mesh.band_split, f"{where}:mesh", band_lo, band_hi)
    solve.source_motion = _validate_source_motion(
        solve.source_motion, str(solve.backend), f"{where}:solve")
    _validate_near_correction(solve, f"{where}:solve")
    _validate_source_profile_alpha(solve, f"{where}:solve")
    search = _build(SearchSettings, _require(raw, "search", where), f"{where}:search",
                    optional=("popsize", "infeasible_penalty", "restarts", "qd"))
    if "popsize" not in raw["search"]:
        search.popsize = None
    if search.infeasible_penalty not in ("flat", "graded"):
        raise ConfigError(f"{where}: search.infeasible_penalty must be 'flat' or 'graded', "
                          f"got {search.infeasible_penalty!r}")
    if search.algorithm not in SEARCH_ALGORITHMS:
        raise ConfigError(f"{where}: search.algorithm must be one of {list(SEARCH_ALGORITHMS)}, "
                          f"got {search.algorithm!r}")
    search.restarts = _validate_restarts(search.restarts, f"{where}:search.restarts")
    search.qd = _validate_qd(search.qd, f"{where}:search.qd")
    if search.algorithm == "cma_me":
        if search.qd is None:
            raise ConfigError(f"{where}:search.qd: search.qd is required for "
                              f"search.algorithm: cma_me (bins_h/bins_v have no default)")
        if search.restarts is not None:
            raise ConfigError(f"{where}:search.restarts: search.restarts is not supported with "
                              f"search.algorithm: cma_me")
    elif search.qd is not None:
        raise ConfigError(f"{where}:search.qd: search.qd is only used with "
                          f"search.algorithm: cma_me")
    objective_version = int((raw.get("objective") or {}).get("version", 1))
    objective_params = None
    if objective_version == 4:
        # Penalty-ordering invariant (plan 3d.2 / 3f): a valid design with every term unmeasurable
        # must still score far below the refusal penalty. Checked per brief, at load.
        from .objective.scalar_v4 import V4Params, worst_valid_j
        from .objective.terms import PENALTY_INVALID
        objective_params = _validate_objective_block(raw["objective"], where)
        worst = worst_valid_j(V4Params.from_block(objective_params), raw.get("weights"))
        if worst > 0.5 * PENALTY_INVALID:
            raise ConfigError(
                f"{where}: objective v4 tolerances/weights let an all-unmeasurable valid design score "
                f"J = {worst:.0f}, above half the refusal penalty ({PENALTY_INVALID:g}); raise the "
                f"tolerances or lower the weights so refused designs always rank below valid ones")
    elif objective_version == 5:
        # Same penalty-ordering invariant as v4, with the v5 term set and C11 defaults.
        from .objective.scalar_meh import MehParams, worst_valid_meh_j
        from .objective.terms import PENALTY_INVALID
        objective_params = _validate_objective_block(raw["objective"], where)
        worst = worst_valid_meh_j(MehParams.from_block(objective_params), raw.get("weights"))
        if worst > 0.5 * PENALTY_INVALID:
            raise ConfigError(
                f"{where}: objective v5 tolerances/weights let an all-unmeasurable valid design score "
                f"J = {worst:.0f}, above half the refusal penalty ({PENALTY_INVALID:g}); raise the "
                f"tolerances or lower the weights so refused designs always rank below valid ones")
    elif objective_version == 6:
        from .objective.scalar_v6 import V6Params, worst_valid_v6_j
        from .objective.terms import PENALTY_INVALID
        objective_params = _validate_objective_block(raw["objective"], where)
        worst = worst_valid_v6_j(V6Params.from_block(objective_params), raw.get("weights"))
        if worst > 0.5 * PENALTY_INVALID:
            raise ConfigError(
                f"{where}: objective v6 tolerances/weights let an all-unmeasurable valid design score "
                f"J = {worst:.0f}, above half the refusal penalty ({PENALTY_INVALID:g}); raise the "
                f"tolerances or lower the weights so refused designs always rank below valid ones")

    if mesh.quadrants not in QUADRANT_FACTOR:
        raise ConfigError(f"{where}: mesh.quadrants must be one of {list(QUADRANT_FACTOR)}")
    if solve.angle_count % 2 != 1:
        raise ConfigError(f"{where}: solve.angle_count must be odd (exact on-axis sample)")

    bounds = _require(raw, "bounds", where)
    for k, b in bounds.items():
        if "lo" not in b or "hi" not in b:
            raise ConfigError(f"{where}: bounds.{k} needs lo and hi")

    return Config(
        name=str(_require(raw, "name", where)),
        family=str(_require(raw, "family", where)),
        seed_params=dict(_require(raw, "seed_params", where)),
        bounds_raw=dict(bounds),
        target_raw=dict(_require(raw, "target", where)),
        weights=dict(_require(raw, "weights", where)),
        mesh=mesh,
        solve=solve,
        search=search,
        raw=raw,
        brief=brief_d,
        generator=None if gen is None else {
            k: v for k, v in gen.items() if k != "seed_policy"},
        objective_version=objective_version,
        grid=grid_cfg,
        mounting=mounting_cfg,
        objective_params=objective_params,
    )


# ------------------------------------------------------------------ specs

def _validate_freq_grid(block, where: str) -> tuple[float, float, float]:
    """``solve.freq_grid`` -> (lo_hz, hi_hz, points_per_octave). Opt-in, additive."""
    if not isinstance(block, dict):
        raise ConfigError(f"{where}: freq_grid must be a mapping {{lo_hz, hi_hz, points_per_octave}}")
    unknown = set(block) - {"lo_hz", "hi_hz", "points_per_octave"}
    if unknown:
        raise ConfigError(f"{where}: freq_grid has unknown key(s) {sorted(unknown)} "
                          f"(allowed: lo_hz, hi_hz, points_per_octave)")
    try:
        lo = float(block["lo_hz"]); hi = float(block["hi_hz"]); ppo = float(block["points_per_octave"])
    except (KeyError, TypeError, ValueError):
        raise ConfigError(f"{where}: freq_grid.lo_hz, hi_hz and points_per_octave are required numbers") from None
    if not (np.isfinite(lo) and np.isfinite(hi) and np.isfinite(ppo)):
        raise ConfigError(f"{where}: freq_grid values must be finite")
    if lo <= 0.0 or hi <= lo:
        raise ConfigError(f"{where}: freq_grid needs 0 < lo_hz < hi_hz (got {lo} -> {hi})")
    if not (1.0 <= ppo <= 48.0):
        raise ConfigError(f"{where}: freq_grid.points_per_octave must be in 1..48 (got {ppo})")
    return lo, hi, ppo


def mode_freqs(mode: str, cfg: Config) -> tuple[float, ...]:
    """The mode's frozen log grid, with its top edge clipped to the target band's upper
    edge so the mesh is never asked to resolve frequencies the objective ignores.

    WP4 (senior pass 2026-10-24): a brief with ``grid: {verify_points_per_octave: N}`` extends the
    VERIFY grid with extra log points in [5 kHz, band_hi] at that density. That is a NEW grid
    group — records carry it through their own solve.freqs_hz (and the solve-spec hash), so a
    comparison against runs on the frozen grid refuses rather than mixing grids."""
    lo, hi, n = FREQ_GRIDS[mode]
    band_hi = cfg.target_raw.get("band_hi_hz")
    if band_hi is not None and float(band_hi) < hi:
        hi = float(band_hi)
    override = (getattr(cfg, "raw", None) or {}).get("solve", {}).get("freq_grid") \
        if isinstance((getattr(cfg, "raw", None) or {}).get("solve"), dict) else None
    if override is not None:
        o_lo, o_hi, ppo = _validate_freq_grid(override, "solve.freq_grid")
        hi_eff = min(o_hi, float(band_hi)) if band_hi is not None else o_hi
        if hi_eff > o_lo:
            n_pts = max(2, int(round(float(np.log2(hi_eff / o_lo)) * ppo)) + 1)
            return tuple(round(float(f), 2) for f in np.geomspace(o_lo, hi_eff, n_pts))
    base = [round(float(f), 2) for f in freq_grid(lo, hi, n)]
    if mode == "verify":
        ppo = ((cfg.grid or {}).get("verify_points_per_octave"))
        if ppo is not None and hi > HF_VERIFY_LO_HZ:
            n_oct = float(np.log2(hi / HF_VERIFY_LO_HZ))
            n_pts = max(1, int(round(n_oct * float(ppo))))
            extra = [round(float(f), 2) for f in np.geomspace(HF_VERIFY_LO_HZ, hi, n_pts + 1)]
            return tuple(sorted(set(base) | set(extra)))
    return tuple(base)


def mesh_spec(mode: Mode, cfg: Config) -> MeshSpec:
    if mode not in MODES:
        raise ConfigError(f"unknown mode {mode!r}")
    cap = cfg.mesh.dof_cap(mode)
    # Single source of truth for the triangle ceiling (senior ruling 2026-10-13): the section-6
    # literal ceil(2*cap*qf*slack) assumes dof_per_triangle == 0.5; the measured value is 0.51
    # (quarter), so use sizing.max_triangles_for to honour it instead of drifting 2% away.
    max_tri = sizing.max_triangles_for(
        cap, cfg.mesh.quadrants, cfg.mesh.dof_per_triangle, cfg.mesh.max_triangle_slack)
    return MeshSpec(
        epw=float(cfg.mesh.epw),
        f_max_hz=float(max(mode_freqs(mode, cfg))),
        quadrants=cfg.mesh.quadrants,
        max_triangles=max_tri,
        allow_large_mesh=False,
    )


def solve_spec(mode: Mode, cfg: Config) -> SolveSpec:
    if mode not in MODES:
        raise ConfigError(f"unknown mode {mode!r}")
    s = cfg.solve
    obs = ObservationSpec(
        distance_m=float(s.distance_m),
        angle_count=int(s.angle_count),
        balloon=bool(s.balloon),
        balloon_points=s.balloon_points(mode),
    )
    # WP15: cuda_fused rides in `extra` so the solve-spec hash (cache key, dataset provenance)
    # changes ONLY when the opt-in is actually set; absent leaves every old hash untouched.
    extra: dict = {"cuda_fused": True} if bool(getattr(s, "cuda_fused", False)) else {}
    _restart_every = (getattr(cfg, "raw", None) or {}).get("solve", {}).get("worker_restart_every") \
        if isinstance((getattr(cfg, "raw", None) or {}).get("solve"), dict) else None
    if _restart_every is not None:
        extra["worker_restart_every"] = int(_restart_every)
    # WP5: 'normal' is today's beat source and must NOT enter `extra` (old hashes unchanged).
    if str(getattr(s, "source_motion", "normal")) != "normal":
        extra["source_motion"] = str(s.source_motion)
    # WP14: CPU-validation knobs. They ride in `extra` under the library's OWN field names and
    # ONLY when non-None, so every old solve-spec hash is untouched (absent = today).
    for _key in ("near_correction", "near_correction_cutoff", "near_correction_order",
                 "solve_precision"):
        _val = getattr(s, _key, None)
        if _val is not None:
            extra[_key] = _val
    # WP16: J0 source-profile angle rides in `extra` under the library's OWN field name and ONLY
    # when explicitly set, so every old solve-spec hash is untouched (absent = today).
    _alpha = getattr(s, "source_profile_alpha", None)
    if _alpha is not None:
        extra["source_profile_alpha"] = float(_alpha)
    # WP8: band-split rides in `extra` too (solve hash + Response.meta provenance via beat).
    band_split = getattr(cfg.mesh, "band_split", None)
    if band_split is not None:
        extra["mesh_policy"] = "band_split_v1"
        extra["band_edges_hz"] = [float(e) for e in band_split["edges_hz"]]
    # WP7: a non-1.0 rear_res_factor changes the MESH, so it must change the solve-spec hash too
    # (solve cache + failure markers + resume memo key off it); absent/1.0 leaves old hashes untouched.
    if float(getattr(cfg.mesh, "rear_res_factor", 1.0)) != 1.0:
        extra["rear_res_factor"] = float(cfg.mesh.rear_res_factor)
    return SolveSpec(
        mode=mode,
        freqs_hz=mode_freqs(mode, cfg),
        backend=str(s.backend),
        observation=obs,
        gmres_tol=float(s.gmres_tol),
        extra=extra,
    )


# ------------------------------------------------------------------ S1a brief preflight + derivation

_KEELE_MM_DEG_HZ = 25400.0 * 1000.0     # KEELE_K (m-deg-Hz) -> mm-deg-Hz
_ROWS_MOUTH_FC_INVARIANT = 1.88e5       # W * fc ~= 1.88e5 mm-Hz (lib-2 s4.3, both throat sizes)


def _keele_required_mouth_mm(f0_hz: float, coverage_deg: float) -> float:
    """``d = KEELE_K / (f0 * coverage)`` in mm: the mouth the K-law needs to hold a
    coverage angle down to f0 (the same rule targets/venue.required_mouth_m applies)."""
    return _KEELE_MM_DEG_HZ / (float(f0_hz) * float(coverage_deg))


def _clamp_to_bounds(key: str, value: float, bounds: dict) -> tuple[float, bool]:
    """Clamp ``value`` into the key's EXISTING bounds (never widen). (value, clamped)"""
    b = bounds.get(key)
    if not isinstance(b, dict) or "lo" not in b or "hi" not in b:
        return float(value), False
    lo, hi = float(b["lo"]), float(b["hi"])
    v = min(max(float(value), lo), hi)
    return v, abs(v - float(value)) > 1e-12


def _derive_generator_geometry(raw: dict, target: dict, feas: dict) -> list:
    """Per-family seed/bounds derivation from the brief's coverage (CLAMP-ONLY).

    Applies when a generator typology/grid config meets an f0_hz-carrying brief: the
    seed's mouth knobs are set from the K-law requirement (d = KEELE_K/(f0*cov)), first
    clamped to the BRIEF ENVELOPE (a target larger than the envelope cannot be built)
    and then to each knob's EXISTING bounds (a clamp hitting a bound is flagged as
    "clamped_to_bound" - widening stays owner-gated and is never automatic).
    Formula and native-family configs get an honest no-rule note; the feasibility
    record itself is family-independent.

    ``generator.seed_policy: explicit`` skips the derivation entirely (the campaign uses
    hand-measured seeds): seed_params and bounds are left untouched and one note records
    the opt-out. Absent (or ``derive``) is the behaviour above, byte-for-byte.
    """
    notes: list = []
    gen = raw.get("generator")
    if isinstance(gen, dict) and str(gen.get("seed_policy", "derive")) == "explicit":
        notes.append({"knob": "-", "note": "seed_policy explicit: derivation skipped"})
        return notes
    seed = raw.setdefault("seed_params", {})
    bounds = raw.setdefault("bounds", {})
    env_w = float(feas["envelope_mouth_w_mm"])
    env_h = float(feas["envelope_mouth_h_mm"])
    req_w = float(feas["required_mouth_w_mm"])
    req_h = float(feas["required_mouth_h_mm"])
    # S1a repair (2026-10-25, owner-directed driver pass): the derived mouth is capped at
    # the envelope MINUS the two wall thicknesses (the generator block's own
    # wall_thickness_mm, mesher default 3.0). registry.envelope_overshoot_estimate counts
    # the freestanding shell, so a derived mouth AT the envelope made the seed
    # invalid_envelope by 2*wt - 0.5 mm whenever the envelope was the binding side
    # (measured on this pass). An envelope too small to hold its own shell falls back to
    # the bare envelope (the overshoot is then honest grading, never a refusal).
    wt = float(gen.get("wall_thickness_mm", 3.0)) if isinstance(gen, dict) else 3.0

    def _env_cap(env_mm: float, req_mm: float) -> float:
        if env_mm <= 0.0:
            return req_mm
        capped = env_mm - 2.0 * wt
        return min(req_mm, capped) if capped > 0.0 else min(req_mm, env_mm)

    target_w = _env_cap(env_w, req_w)
    target_h = _env_cap(env_h, req_h)

    def set_seed(key: str, value, note: str) -> None:
        if value is None:
            notes.append({"knob": key, "note": "no target (zero envelope axis?)", "applied": None})
            return
        v, clamped = _clamp_to_bounds(key, value, bounds)
        seed[key] = float(v)
        notes.append({"knob": key, "derived_mm": float(value), "applied": float(v),
                      "clamped_to_bound": bool(clamped), "note": note})

    def cov_of(axis: str) -> float:
        return float(target["coverage_h_deg" if axis == "w" else "coverage_v_deg"])

    if isinstance(gen, dict):
        name = gen.get("name")
        if name == "typology":
            prof_h = gen.get("profile_h")
            prof_v = gen.get("profile_v", "same")
            explicit_v = prof_v != "same"
            for prefix, prof, axis in (("h", prof_h, "w"), ("v", prof_v, "h")):
                if not explicit_v and prefix == "v":
                    continue                      # profile_v: same -> the H derivation rules
                if not isinstance(prof, dict):
                    continue
                ptype = prof.get("type")
                if ptype == "biradial":
                    # S1a repair (2026-10-25, owner-directed driver pass): the biradial
                    # contour law REFUSES rm < r0 + tan(a)*L (the power-series term would
                    # need c < 0; design/generators/profiles.py biradial_contour), and the
                    # K-law mouth alone can sit far below that line (measured under
                    # axi_2in_large: derived rm 141.1 vs the 192 mm closure need at r0
                    # 25.4). The derived rm is therefore the MAX of the K-law mouth and
                    # the closure line; when the knob's own hi bound cannot hold the
                    # closure value the bound WIDENS to exactly it (note flag
                    # "widened_to_closure") - a clamped-only rule would re-create the
                    # un-closeable seed this repair removes. This widening is the one
                    # owner-directed exception (dated here) to the clamp-only contract.
                    # The seed's initial wall angle follows the patent's own sizing
                    # sentence ("empirically on the order of ninety percent" of the half
                    # coverage; US4308932A) - quoted in the config headers, never a new
                    # constant.
                    a_key = f"{prefix}_a_deg"
                    a_patent = 0.9 * cov_of(axis) / 2.0
                    a_val, a_clamped = _clamp_to_bounds(a_key, a_patent, bounds)
                    seed[a_key] = float(a_val)
                    notes.append({"knob": a_key, "derived_deg": float(a_patent),
                                  "applied": float(a_val),
                                  "clamped_to_bound": bool(a_clamped),
                                  "note": "US4308932A: a ~ 0.9 x half-coverage"})
                    L_seed = float(seed.get(
                        "L_mm", (bounds.get("L_mm") or {}).get("hi", 190.0)))
                    r0 = float(((raw.get("brief") or {}).get("driver") or {})
                               .get("exit_radius_mm", 0.0))
                    closure = r0 + float(np.tan(np.radians(float(a_val)))) * L_seed
                    rm_key = f"{prefix}_rm_mm"
                    rm_k = (target_w if axis == "w" else target_h) / 2.0
                    rm_derived = max(rm_k, closure)
                    b = bounds.get(rm_key)
                    widened = False
                    if isinstance(b, dict) and float(b.get("hi", rm_derived)) < rm_derived - 1e-9:
                        b["hi"] = float(rm_derived)
                        widened = True
                    v, clamped = _clamp_to_bounds(rm_key, rm_derived, bounds)
                    seed[rm_key] = float(v)
                    note = {"knob": rm_key, "derived_mm": float(rm_derived),
                            "applied": float(v), "clamped_to_bound": bool(clamped),
                            "note": "K-law mouth radius (d/2), floored at the closure "
                                    "line rm = r0 + tan(a)*L (the biradial refusal guard)"}
                    if widened:
                        note["widened_to_closure"] = True
                    notes.append(note)
                elif ptype in ("conical", "exponential", "hypex"):
                    set_seed(f"{prefix}_rm_mm", (target_w if axis == "w" else target_h) / 2.0,
                             "K-law mouth radius (d/2)")
                elif ptype == "osse":
                    set_seed(f"{prefix}_a_deg", min(cov_of(axis) / 2.0, 45.0),
                             "OSSE a_deg is a HALF-angle: coverage/2")
                elif ptype == "qtw_waveguide":
                    set_seed(f"{prefix}_a_deg", cov_of(axis) / 2.0,
                             "the arc rule: arc turn == half the dispersion angle")
                else:
                    notes.append({"knob": f"{prefix}_* {ptype}",
                                  "note": "no derivation rule for this profile type (v1)"})
        elif name == "grid" and isinstance(gen.get("rows"), dict):
            rtype = gen["rows"].get("type")
            fc_w = _ROWS_MOUTH_FC_INVARIANT / target_w if target_w > 0 else None
            fc_v = _ROWS_MOUTH_FC_INVARIANT / target_h if target_h > 0 else None
            geo = (target_w * target_h) ** 0.5 if target_w * target_h > 0 else 0.0
            if rtype in ("salmon_elliptical", "salmon_axisym"):
                set_seed("g_fc_h_hz", fc_w, "K-law inverse of the W*fc invariant")
                if rtype == "salmon_elliptical":
                    set_seed("g_fc_v_hz", fc_v, "K-law inverse of the H*fc invariant")
            elif rtype in ("lecleach", "lecleach_asym", "toroidal_rollback"):
                set_seed("g_fc_hz", _ROWS_MOUTH_FC_INVARIANT / geo if geo > 0 else None,
                         "K-law inverse at the geometric-mean mouth")
            elif rtype == "iwata_ar":
                set_seed("g_fc_hz", _ROWS_MOUTH_FC_INVARIANT / geo if geo > 0 else None,
                         "K-law inverse at the geometric-mean mouth")
                if target_h > 0 and target_w > 0:
                    set_seed("g_ar_m", target_w / target_h, "AR target = W/H")
            else:
                notes.append({"knob": f"rows {rtype}", "note": "no derivation rule (v1)"})
        else:
            notes.append({"knob": "-", "note":
                          "no generator block (formula/native family): feasibility "
                          "recorded; derivation lands with the baseline-settings pass"})
    else:
        notes.append({"knob": "-", "note": "no generator block in this config"})
    return notes


def _brief_preflight_and_derive(raw: dict, brief_d: dict | None, where: str) -> dict:
    """S1a (2026-10-25, owner-approved full-repair pass): when the brief's target carries
    ``target.f0_hz``, (a) record the K-law feasibility (required vs envelope mouth per
    axis, the held coverage at the envelope's limit, the per-mode screen-frequency count
    below f0 - the part the objective can never honestly control) and (b) derive the
    typology's seed/bounds mouth from the coverage (clamped to the envelope and to the
    config's own bounds; every clamp flagged).  Briefs without f0_hz are untouched:
    absent = byte-for-byte (the embedded-brief resume path never calls this)."""
    if brief_d is None:
        return raw
    t = dict(brief_d.get("target") or {})
    f0 = t.get("f0_hz")
    if f0 is None:
        return raw
    f0 = float(f0)
    cov_h = float(t["coverage_h_deg"])
    cov_v = float(t["coverage_v_deg"])
    env = brief_d.get("envelope") or {}
    env_w = float(env.get("max_mouth_w_mm", 0.0))
    env_h = float(env.get("max_mouth_h_mm", 0.0))
    band_hi = float(t["band_hi_hz"])
    req_w = _keele_required_mouth_mm(f0, cov_h)
    req_h = _keele_required_mouth_mm(f0, cov_v)
    feas = {
        "rule": "d = KEELE_K / (f0 * coverage) mm (KEELE_K = 25,400 m-deg-Hz)",
        "f0_hz": f0,
        "required_mouth_w_mm": req_w,
        "required_mouth_h_mm": req_h,
        "envelope_mouth_w_mm": env_w,
        "envelope_mouth_h_mm": env_h,
        "held_coverage_w_deg": (_KEELE_MM_DEG_HZ / (f0 * env_w)) if env_w > 0 else None,
        "held_coverage_v_deg": (_KEELE_MM_DEG_HZ / (f0 * env_h)) if env_h > 0 else None,
        "feasible_w": bool(env_w > 0.0 and req_w <= env_w + 1e-9),
        "feasible_v": bool(env_h > 0.0 and req_h <= env_h + 1e-9),
    }
    # 2026-10-26 objective v3 amendment: only emitted when the brief opts in, so a brief
    # without f0_v_hz keeps its pre-amendment feasibility-record bytes.
    if t.get("f0_v_hz") is not None:
        feas["f0_v_hz"] = float(t["f0_v_hz"])
    for mode in ("screen", "verify"):
        lo, hi, n = FREQ_GRIDS[mode]
        hi_eff = min(hi, band_hi)
        if hi_eff <= lo:
            continue
        freqs = np.geomspace(lo, hi_eff, n)
        feas[f"{mode}_freqs_below_f0"] = int(np.count_nonzero(freqs < f0))
        feas[f"{mode}_freqs_total"] = int(n)
    raw["feasibility"] = feas
    feas["derivation"] = _derive_generator_geometry(raw, t, feas)
    return raw
