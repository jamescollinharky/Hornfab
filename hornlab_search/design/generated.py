"""GeneratedSpace: the search box over TYPOLOGY GENERATOR knobs (docs/TYPOLOGY_PLAN.md s5).

Same interface as ``DesignSpace`` (``family``, ``seed``, ``bounds``, ``keys``, ``normalize``,
``denormalize``), so CMA-ES and the pipeline are unchanged. The search vector holds generator
knobs (alphabetical, like DesignSpace); ``denormalize`` materialises them into an ordinary FREEFORM
``Design`` via the module dispatch in :func:`materialize` (``generators.registry.materialize`` for
typologies, ``generators.grid.design_params`` for ``name: grid``). The design hash is the geometry
(the recipe for a grid), so equal shapes from different knobs deduplicate.

``denormalize`` never raises for bad knobs: a knob vector that gives no legal horn (envelope,
tractrix mouth smaller than the throat, ...) becomes a Design carrying ``_generator_error``, which
``search/evaluate.py`` scores as ``invalid_geometry`` (CMA-ES must not crash on a corner).
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging

import numpy as np

from ..types import Design, GeometryInvalidError
from .generators import grid as grid_gen
from .generators import registry
from .space import Bound, _ROUND_DECIMALS

log = logging.getLogger("hornlab_search.design.generated")

GENERATOR_ERROR_KEY = "_generator_error"
#: Relative pre-mesh envelope overshoot carried alongside an ``invalid_envelope`` error.
#: ABSENT on every legal design (and on non-envelope generator errors): search/evaluate.py
#: reads ``params.get(GENERATOR_OVERSHOOT_KEY)`` only to grade the penalty.
GENERATOR_OVERSHOOT_KEY = "_generator_overshoot"
#: Cap on the stored overshoot.  ``graded_infeasible_penalty`` saturates at 2e3 for an
#: overshoot of 10, so larger values carry no extra ranking information.
_MAX_STORED_OVERSHOOT = 10.0


def brief_hash(brief: dict) -> str:
    body = {k: v for k, v in brief.items() if k != "path"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]


def materialize(gen: dict, knobs: dict, brief: dict) -> dict:
    """Generator block + knobs -> Design params, dispatching on the block's ``name``.

    ``name: grid`` is the WP10 point-grid adapter: its params are the compact surface spec plus the
    knob recipe (``{"grid": {...}}``), NOT FREEFORM anchors, because the grid is evaluated at mesh
    time by ``mesh/grid_build.py``. Every other name keeps the typology path (FREEFORM anchors).
    """
    if str(gen.get("name", "")) == "grid":
        return grid_gen.design_params(gen, knobs, brief)
    if str(gen.get("name", "")) == "plughorn":
        return plughorn_params(gen, knobs, brief)
    if str(gen.get("name", "")) == "meh":
        return meh_params(gen, knobs, brief)
    return registry.materialize(gen, knobs, brief)


def plughorn_params(gen: dict, knobs: dict, brief: dict) -> dict:
    """``name: plughorn`` -> ``{"cad": recipe}`` for ``tools/cad/plughorn.py`` (2026-10-28).

    Recipe = the tool's documented DEFAULTS, overridden by ``generator.fixed`` and then by the knobs
    (knob names ARE the tool's keys, e.g. ``h_angle2_deg``). Every key is written, so the recipe is
    explicit and the design hash is the geometry. The tool's own validation (ranges, plug clearance)
    runs here, and the outer size is checked against the brief envelope, so an illegal knob vector
    becomes ``invalid_geometry`` / ``invalid_envelope`` before any mesh.
    """
    from dataclasses import asdict

    from ..mesh import step_build                   # lazy: mesh imports the design package
    tool = step_build.load_cad_tool(tool=step_build.PLUGHORN_TOOL)
    recipe = dict(asdict(tool.DEFAULTS))
    fixed = dict(gen.get("fixed") or {})
    for src in (fixed, knobs):
        unknown = sorted(set(src) - set(recipe))
        if unknown:
            raise ValueError(f"plughorn: unknown key(s) {unknown}")
        recipe.update({k: float(v) for k, v in src.items()})
    for k in tool.INT_KEYS:
        recipe[k] = int(round(recipe[k]))
    params = tool.params_from_recipe(recipe)          # raises ValueError on a bad shape
    d = params.derived()
    env = (brief or {}).get("envelope") or {}
    for key, val in (("max_mouth_w_mm", d["outer_w_mm"]), ("max_mouth_h_mm", d["outer_h_mm"]),
                     ("max_depth_mm", d["depth_total_mm"])):
        if key in env and val > float(env[key]) + 0.5:
            raise ValueError(f"plughorn: outer {key[4:-3]} {val:.0f} mm exceeds the brief's {env[key]} mm")
    return {"cad": {"tool": step_build.PLUGHORN_TOOL, **recipe}}


def meh_params(gen: dict, knobs: dict, brief: dict) -> dict:
    """``name: meh`` -> ``{"cad": recipe}`` for ``tools/cad/meh.py`` (MEH, 2026-10-30).

    Recipe = the tool's documented defaults (C9), overridden by ``generator.fixed`` and then by
    the knobs (knob names ARE the tool's keys). Every key is written, so the design hash is the
    geometry. The tool's own ``derived()`` runs the layout check and the deterministic slide
    repair here; a non-empty ``reasons`` list is an illegal horn (``invalid_geometry`` before any
    mesh). The mouth and depth are checked against the brief envelope.
    """
    from ..mesh import step_build                   # lazy: mesh imports the design package
    tool = step_build.load_cad_tool(tool=step_build.MEH_TOOL)
    recipe = dict(tool.defaults())
    fixed = dict(gen.get("fixed") or {})
    for src in (fixed, knobs):
        unknown = sorted(set(src) - set(recipe))
        if unknown:
            raise ValueError(f"meh: unknown key(s) {unknown}")
        recipe.update(src)
    for key in ("cov_h_deg", "cov_v_deg", "z_frac", "across_frac", "port_along_mm", "slide_mm"):
        recipe[key] = float(recipe[key])
    for key in ("env_w_mm", "env_h_mm", "env_d_mm", "box_t_mm", "roll_mm", "wall_t_mm",
                "spacer_mm", "exit_mm", "cd_duct_mm", "cd_body_d_mm", "cd_body_len_mm",
                "cone_cutout_mm", "cone_depth_mm", "clearance_mm"):
        recipe[key] = float(recipe[key])
    recipe["walls"] = str(recipe["walls"])
    d = tool.derived(recipe)                        # the tool's own validation + repair
    reasons = list(d.get("reasons") or [])
    if reasons:
        raise ValueError(f"meh: layout infeasible: {reasons}")
    env = (brief or {}).get("envelope") or {}
    for key, val in (("max_mouth_w_mm", float(d["mouth_w"])), ("max_mouth_h_mm", float(d["mouth_h"])),
                     ("max_depth_mm", float(recipe["env_d_mm"]))):
        if key in env and val > float(env[key]) + 0.5:
            raise ValueError(f"meh: {key[4:-3]} {val:.1f} mm exceeds the brief's {env[key]} mm")
    return {"cad": {"tool": step_build.MEH_TOOL, **recipe}}


class GeneratedSpace:
    family = "FREEFORM"

    def __init__(self, gen: dict, brief: dict, seed_knobs: dict, bounds: dict[str, Bound]):
        self.gen = dict(gen)
        self.brief = dict(brief)
        self.bounds = dict(bounds)
        # Harmonic stop-law knobs are JSON lists of floats (grid rows); every other
        # generator knob is a scalar. Keep both forms (a list must not be float()ed).
        knobs = {}
        for k, v in (seed_knobs or {}).items():
            if isinstance(v, (list, tuple)):
                knobs[k] = [float(x) for x in v]
            else:
                knobs[k] = float(v)
        for k in sorted(self.bounds):
            b = self.bounds[k]
            if b.search and k not in knobs:
                knobs[k] = b.midpoint()
                log.warning("generator seed lacks knob %s; filled with the bound midpoint", k)
        self.seed_knobs = knobs
        try:
            params = materialize(self.gen, knobs, self.brief)
        except Exception as exc:  # the SEED must be legal: stop with a clear message
            raise GeometryInvalidError(f"generator seed is not a legal horn: {exc}") from exc
        self.seed = Design("FREEFORM", params)
        self._knobs_by_hash = {self.seed.hash(): dict(knobs)}

    @classmethod
    def from_config(cls, cfg) -> "GeneratedSpace":
        bounds = {str(k): Bound(lo=float(b["lo"]), hi=float(b["hi"]), search=bool(b.get("search", True)),
                                log=bool(b.get("log", False))) for k, b in cfg.bounds_raw.items()}
        return cls(cfg.generator, cfg.brief, dict(cfg.seed_params), bounds)

    def keys(self) -> list[str]:
        return sorted(k for k, b in self.bounds.items() if b.search)

    def knobs_from_unit(self, x) -> dict:
        x = np.clip(np.asarray(x, dtype=float).reshape(-1), 0.0, 1.0)
        keys = self.keys()
        if x.size != len(keys):
            raise ValueError(f"expected a vector of length {len(keys)}, got {x.size}")
        knobs = dict(self.seed_knobs)
        for k, xi in zip(keys, x):
            knobs[k] = round(self.bounds[k].from_unit(float(xi)), _ROUND_DECIMALS)
        return knobs

    def design_from_knobs(self, knobs: dict) -> Design:
        try:
            params = materialize(self.gen, knobs, self.brief)
        except Exception as exc:  # noqa: BLE001 - scored as invalid_geometry in evaluate
            params = {GENERATOR_ERROR_KEY: f"{type(exc).__name__}: {exc}",
                      "_knobs": {k: knobs[k] for k in sorted(knobs)}}
        else:
            # Pre-mesh envelope estimate. ``materialize`` checks the INNER mouth; this catches
            # the outer shell offset the post-mesh bounding box includes, so an envelope
            # violation is scored (invalid_envelope) without paying for a mesh. The happy path
            # adds nothing: no overshoot key is present when the estimate is 0.
            try:
                overshoot = registry.envelope_overshoot_estimate(params, self.brief)
            except Exception:  # noqa: BLE001 - an estimate must never turn a legal knob invalid
                log.debug("pre-mesh envelope estimate failed", exc_info=True)
                overshoot = None
            if overshoot is not None and overshoot > 0.0:
                value = min(max(float(overshoot), 0.0), _MAX_STORED_OVERSHOOT)
                params = {**params,
                          GENERATOR_ERROR_KEY: (
                              "invalid_envelope: estimated outside the brief envelope "
                              f"(max relative overshoot {value:.4f})"),
                          GENERATOR_OVERSHOOT_KEY: float(value),
                          "_knobs": {k: knobs[k] for k in sorted(knobs)}}
        d = Design("FREEFORM", params)
        # last-wins: provenance then names the knobs of the candidate actually being evaluated
        # (two knob vectors can round to the same anchors); CMA never normalizes loop candidates.
        self._knobs_by_hash[d.hash()] = dict(knobs)
        return d

    def denormalize(self, x) -> Design:
        return self.design_from_knobs(self.knobs_from_unit(x))

    def normalize(self, d: Design) -> np.ndarray:
        """Design -> [0,1]^k for a design this space produced (the seed or a denormalized
        vector). Geometry cannot be inverted to knobs, so any other design raises."""
        knobs = self._knobs_by_hash.get(d.hash())
        if knobs is None:
            raise ValueError("GeneratedSpace.normalize: design was not produced by this space "
                             "(generator knobs cannot be recovered from geometry)")
        return np.array([self.bounds[k].to_unit(float(knobs[k]))[0] for k in self.keys()], dtype=float)

    def knobs_for(self, d: Design) -> dict | None:
        k = self._knobs_by_hash.get(d.hash())
        return None if k is None else copy.deepcopy(k)

    def provenance(self, d: Design) -> dict | None:
        knobs = self.knobs_for(d)
        if knobs is None:
            return None
        return {"name": self.gen.get("name", "typology"), "spec": copy.deepcopy(self.gen),
                "knobs": knobs, "brief": self.brief.get("name"), "brief_hash": brief_hash(self.brief),
                "derived": registry.info(self.gen, knobs, self.brief)}
