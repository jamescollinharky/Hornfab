"""Recommend which CMA search knobs to pin from a finished run's covariance snapshot.

Rules (plan 2026-10-31): small ``σ√C_ii`` share + below-median std → propose pin at the run's
best value, unless Spearman |ρ| says the knob still drives J. Never auto-mutates a live search;
callers write ``pin_plan.json`` / a patched YAML.
"""
from __future__ import annotations

import copy
import math
from typing import Any

DEFAULT_SHARE_FLOOR = 0.04
DEFAULT_SHARE_FACTOR = 0.5
DEFAULT_STD_RATIO = 0.35
DEFAULT_RHO_KEEP = 0.35
DEFAULT_MIN_KEEP = 2
DEFAULT_MAX_PIN_FRACTION = 0.5


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    m = len(s) // 2
    if len(s) % 2:
        return float(s[m])
    return 0.5 * (float(s[m - 1]) + float(s[m]))


def permanently_pinned_keys(bounds: dict | None) -> set[str]:
    """Keys already ``search: false`` in the config bounds."""
    out: set[str] = set()
    for k, v in _as_dict(bounds).items():
        if isinstance(v, dict) and v.get("search") is False:
            out.add(str(k))
    return out


def recommend_pins(
    cma_covariance: dict,
    *,
    best_params: dict | None = None,
    sens: list[dict] | None = None,
    bounds: dict | None = None,
    share_floor: float = DEFAULT_SHARE_FLOOR,
    share_factor: float = DEFAULT_SHARE_FACTOR,
    std_ratio: float = DEFAULT_STD_RATIO,
    rho_keep: float = DEFAULT_RHO_KEEP,
    min_keep: int = DEFAULT_MIN_KEEP,
    max_pin_fraction: float = DEFAULT_MAX_PIN_FRACTION,
) -> dict[str, Any]:
    """Return a JSON-able pin plan from ``cma_covariance`` (+ optional Spearman / best).

    Each decision: ``{key, action: pin|keep, value?, reasons[], share, std_unit, C_ii?, rho?}``.
    """
    cov = _as_dict(cma_covariance)
    coords = list(cov.get("coordinates") or [])
    if not coords:
        return {
            "decisions": [],
            "pin": [],
            "keep": [],
            "thresholds": {},
            "note": "no cma_covariance.coordinates — nothing to recommend",
        }

    best = {str(k): v for k, v in _as_dict(best_params).items()}
    rho_by_key: dict[str, float | None] = {}
    for row in sens or []:
        if isinstance(row, dict) and row.get("key") is not None:
            rho_by_key[str(row["key"])] = (
                float(row["rho"]) if row.get("rho") is not None else None
            )

    permanent = permanently_pinned_keys(bounds)
    # Only consider knobs that appear in the covariance (searchable at search time).
    rows: list[dict] = []
    stds: list[float] = []
    for c in coords:
        if not isinstance(c, dict) or c.get("key") is None:
            continue
        key = str(c["key"])
        if key in permanent:
            continue
        std = float(c.get("std_unit") or 0.0)
        share = float(c.get("share") or 0.0)
        rows.append({
            "key": key,
            "share": share,
            "std_unit": std,
            "C_ii": float(c["C_ii"]) if c.get("C_ii") is not None else None,
            "rho": rho_by_key.get(key),
        })
        stds.append(std)

    n = len(rows)
    if n == 0:
        return {
            "decisions": [],
            "pin": [],
            "keep": [],
            "thresholds": {},
            "note": "all covariance knobs are already permanently pinned",
        }

    share_thresh = max(float(share_floor), float(share_factor) / float(n))
    med_std = _median(stds)
    std_thresh = float(std_ratio) * med_std
    max_pins = max(0, min(n - int(min_keep), int(math.floor(float(max_pin_fraction) * n))))

    # Rank pin candidates: smallest share first (ties → smaller std_unit, then key).
    candidates = sorted(rows, key=lambda r: (r["share"], r["std_unit"], r["key"]))
    pin_keys: list[str] = []
    reasons_by_key: dict[str, list[str]] = {r["key"]: [] for r in rows}

    for r in candidates:
        key = r["key"]
        reasons: list[str] = []
        eligible = True
        if r["share"] > share_thresh:
            eligible = False
            reasons.append(f"share {r['share']:.4f} > thresh {share_thresh:.4f}")
        else:
            reasons.append(f"share {r['share']:.4f} ≤ thresh {share_thresh:.4f}")
        if r["std_unit"] > std_thresh:
            eligible = False
            reasons.append(f"std_unit {r['std_unit']:.4f} > {std_ratio}×median={std_thresh:.4f}")
        else:
            reasons.append(f"std_unit {r['std_unit']:.4f} ≤ {std_ratio}×median={std_thresh:.4f}")
        rho = r["rho"]
        if rho is not None and abs(float(rho)) >= float(rho_keep):
            eligible = False
            reasons.append(f"|rho|={abs(float(rho)):.3f} ≥ rho_keep={rho_keep} (Spearman veto)")
        elif rho is not None:
            reasons.append(f"|rho|={abs(float(rho)):.3f} < rho_keep={rho_keep}")
        if key not in best:
            eligible = False
            reasons.append("no_best_value")
        if eligible:
            if len(pin_keys) >= max_pins:
                reasons.append(f"cap max_pins={max_pins} reached")
                eligible = False
            else:
                reasons.append("propose pin at best")
                pin_keys.append(key)
        reasons_by_key[key] = reasons

    pin_set = set(pin_keys)
    # Enforce min_keep: if somehow over-pinned, drop highest-share pins first.
    while n - len(pin_set) < int(min_keep) and pin_set:
        drop = max(pin_set, key=lambda k: next(r["share"] for r in rows if r["key"] == k))
        pin_set.remove(drop)
        reasons_by_key[drop].append(f"reverted to keep (min_keep={min_keep})")

    decisions: list[dict] = []
    for r in sorted(rows, key=lambda x: (0 if x["key"] in pin_set else 1, x["share"], x["key"])):
        key = r["key"]
        action = "pin" if key in pin_set else "keep"
        rec: dict[str, Any] = {
            "key": key,
            "action": action,
            "reasons": reasons_by_key[key],
            "share": r["share"],
            "std_unit": r["std_unit"],
            "C_ii": r["C_ii"],
            "rho": r["rho"],
        }
        if action == "pin":
            rec["value"] = float(best[key])
        decisions.append(rec)

    return {
        "decisions": decisions,
        "pin": [d["key"] for d in decisions if d["action"] == "pin"],
        "keep": [d["key"] for d in decisions if d["action"] == "keep"],
        "thresholds": {
            "share_floor": float(share_floor),
            "share_factor": float(share_factor),
            "share_thresh": share_thresh,
            "std_ratio": float(std_ratio),
            "std_thresh": std_thresh,
            "median_std_unit": med_std,
            "rho_keep": float(rho_keep),
            "min_keep": int(min_keep),
            "max_pin_fraction": float(max_pin_fraction),
            "max_pins": max_pins,
            "n_searchable": n,
        },
        "permanently_pinned": sorted(permanent),
        "note": ("Pins are recommendations from the CMA search distribution + Spearman guard; "
                 "not a physical Sobol decomposition. Apply with apply_pins_to_config / CLI."),
    }


def apply_pins_to_config(doc: dict, plan: dict) -> dict:
    """Return a deep copy of ``doc`` with recommended pins applied (``search: false``, lo=hi).

    Also sets ``seed_params[key]`` to the pin value so the seed matches the pinned geometry.
    Keys not marked ``action: pin`` are left unchanged.
    """
    out = copy.deepcopy(doc)
    bounds = dict(_as_dict(out.get("bounds")))
    seed = dict(_as_dict(out.get("seed_params")))
    for d in plan.get("decisions") or []:
        if not isinstance(d, dict) or d.get("action") != "pin":
            continue
        key = str(d["key"])
        if d.get("value") is None:
            continue
        v = float(d["value"])
        bounds[key] = {"lo": v, "hi": v, "search": False}
        seed[key] = v
    out["bounds"] = bounds
    out["seed_params"] = seed
    return out


def format_pin_plan_md(plan: dict, *, run_id: str | None = None) -> str:
    """Markdown table for ``PIN_PLAN.md``."""
    lines = [
        "# CMA pin plan",
        "",
    ]
    if run_id:
        lines.append(f"Run: `{run_id}`")
        lines.append("")
    th = _as_dict(plan.get("thresholds"))
    if th:
        lines += [
            "## Thresholds",
            "",
            f"- share ≤ `{th.get('share_thresh')}` "
            f"(floor `{th.get('share_floor')}`, factor/N `{th.get('share_factor')}`/`{th.get('n_searchable')}`)",
            f"- std_unit ≤ `{th.get('std_ratio')}` × median `{th.get('median_std_unit')}` → `{th.get('std_thresh')}`",
            f"- Spearman veto if `|rho|` ≥ `{th.get('rho_keep')}`",
            f"- min_keep `{th.get('min_keep')}`, max_pins `{th.get('max_pins')}`",
            "",
        ]
    perm = plan.get("permanently_pinned") or []
    if perm:
        lines += ["Permanently pinned (unchanged): " + ", ".join(f"`{k}`" for k in perm), ""]
    lines += [
        "## Decisions",
        "",
        "| Key | Action | Value | share | σ√Cᵢᵢ | ρ | Reasons |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for d in plan.get("decisions") or []:
        val = d.get("value")
        val_s = f"{val:.6g}" if isinstance(val, (int, float)) else "—"
        rho = d.get("rho")
        rho_s = f"{rho:.3f}" if isinstance(rho, (int, float)) else "—"
        reasons = "; ".join(d.get("reasons") or [])
        lines.append(
            f"| `{d.get('key')}` | **{d.get('action')}** | {val_s} | "
            f"{float(d.get('share') or 0):.4f} | {float(d.get('std_unit') or 0):.4f} | "
            f"{rho_s} | {reasons} |"
        )
    pin = plan.get("pin") or []
    keep = plan.get("keep") or []
    lines += [
        "",
        f"**Pin ({len(pin)}):** " + (", ".join(f"`{k}`" for k in pin) if pin else "_(none)_"),
        f"**Keep ({len(keep)}):** " + (", ".join(f"`{k}`" for k in keep) if keep else "_(none)_"),
        "",
    ]
    if plan.get("note"):
        lines += [f"_{plan['note']}_", ""]
    return "\n".join(lines)
