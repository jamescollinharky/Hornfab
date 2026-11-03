"""Equal-budget staged (macro → shape → joint polish) vs joint CMA-ES A/B harness.

Import-light (stdlib + PyYAML). Does not import the search loop: every stage is an ordinary
``hornlab-search search`` subprocess, so GPU lock / hygiene / ndjson contracts stay the CLI's.

Stages (plan: staged search refinement)::

    A  macro keys only          budget N/3   sigma0 from base
    B  shape keys only          budget N/3   seed+pins from A's best.json
    C  A∪B, boxes ±frac around B  budget N/3   sigma0 small (covariance recovery)
    joint control               budget N     same seed lineage

Example::

    python tools/run_staged_search.py --dry-run
    python tools/run_staged_search.py --out runs/staged_ab_2026-10-31 --both
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = (
    ROOT / "examples" / "typologies" / "staged_ab_2026-10-31" / "joint__crease_core_law.yaml"
)
DEFAULT_STAGE_A = (
    ROOT / "examples" / "typologies" / "staged_ab_2026-10-31" / "stageA_macro__crease_core_law.yaml"
)
DEFAULT_STAGE_B = (
    ROOT / "examples" / "typologies" / "staged_ab_2026-10-31" / "stageB_shape__crease_core_law.yaml"
)

#: Coverage / size knobs (Stage A). ``aspect_ratio`` joins when it is searchable on the joint base.
MACRO_KEYS = frozenset({"L_mm", "a_deg", "n", "s", "k", "aspect_ratio"})

#: Shape / crease knobs (Stage B). Permanently pinned keys (az_sf_m, morph_target, …) stay pinned.
SHAPE_KEYS = frozenset({
    "az_a_sf_amp", "az_sf_n1", "az_sf_n2", "az_sf_n3", "az_sf_b",
    "az_a_cos_amp", "az_a_cos_pow", "az_n_cos2_amp", "az_s_cos2_amp",
    "morph_corner_mm", "morph_rate", "morph_fixed",
})

POLISH_FRAC = 0.12
POLISH_SIGMA0 = 0.06
BACKENDS = ("auto", "beat_cuda", "beat_metal", "beat_cpu", "bempp_cpu")
_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def resolve_backend(choice: str) -> str:
    """Map ``auto`` → ``beat_metal`` on macOS, else ``beat_cuda``. Explicit names pass through."""
    c = str(choice or "auto").strip().lower()
    if c == "auto":
        return "beat_metal" if sys.platform == "darwin" else "beat_cuda"
    if c not in BACKENDS[1:]:
        raise ValueError(f"backend must be one of {list(BACKENDS)}, got {choice!r}")
    return c


def apply_solve_backend(doc: dict, backend: str) -> dict:
    """Rewrite ``solve.backend``; clear ``cuda_fused`` unless the backend is ``beat_cuda``.

    Staged configs ship as CUDA/fused for the Windows GPU box. On a Mac the same YAML must
    not keep ``cuda_fused: true`` (config refuses it off ``beat_cuda``).
    """
    out = copy.deepcopy(doc)
    solve = dict(_as_dict(out.get("solve")))
    solve["backend"] = backend
    if backend == "beat_cuda":
        solve.setdefault("cuda_fused", True)
    else:
        solve["cuda_fused"] = False
    out["solve"] = solve
    return out


# ------------------------------------------------------------------ pure helpers


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def searchable_keys(doc: dict) -> set[str]:
    """Keys whose bounds allow search (absent ``search: false``)."""
    out: set[str] = set()
    for k, v in _as_dict(doc.get("bounds")).items():
        if not isinstance(v, dict):
            continue
        if v.get("search") is False:
            continue
        out.add(k)
    return out


def pin_bound(bound: dict, value: float) -> dict:
    """Return a pinned bound ``{lo: v, hi: v, search: false}`` (other keys dropped)."""
    v = float(value)
    return {"lo": v, "hi": v, "search": False}


def apply_active_set(doc: dict, active: set[str], *, joint_full_bounds: dict) -> dict:
    """Pin every joint-searchable key not in ``active``; restore full boxes for active keys.

    Permanently pinned keys (not in ``joint_full_bounds`` as searchable on the joint base) are
    left alone. Active keys get the joint arm's full ``lo``/``hi`` so Stage B does not inherit
    a Stage-A pin width.
    """
    out = copy.deepcopy(doc)
    bounds = _as_dict(out.get("bounds"))
    seed = _as_dict(out.get("seed_params"))
    for key, full in joint_full_bounds.items():
        cur = _as_dict(bounds.get(key))
        if key in active:
            restored = copy.deepcopy(full)
            restored.pop("search", None)
            bounds[key] = restored
        else:
            if key in seed:
                bounds[key] = pin_bound(cur, float(seed[key]))
            else:
                mid = 0.5 * (float(full["lo"]) + float(full["hi"]))
                bounds[key] = pin_bound(cur, mid)
    out["bounds"] = bounds
    return out


def seed_from_best(doc: dict, best_params: dict) -> dict:
    """Copy every overlapping key from ``best_params`` into ``seed_params``."""
    out = copy.deepcopy(doc)
    seed = dict(_as_dict(out.get("seed_params")))
    for k, v in best_params.items():
        if k in seed or k in _as_dict(out.get("bounds")):
            seed[k] = v
    out["seed_params"] = seed
    return out


def pin_keys_to_seed(doc: dict, keys: set[str]) -> dict:
    """Force ``search: false`` with lo=hi=seed for each key in ``keys`` that has a seed value."""
    out = copy.deepcopy(doc)
    bounds = _as_dict(out.get("bounds"))
    seed = _as_dict(out.get("seed_params"))
    for key in keys:
        if key not in seed:
            continue
        bounds[key] = pin_bound(_as_dict(bounds.get(key)), float(seed[key]))
    out["bounds"] = bounds
    return out


def narrow_boxes(
    doc: dict,
    center: dict,
    active: set[str],
    joint_full_bounds: dict,
    *,
    frac: float = POLISH_FRAC,
) -> dict:
    """Shrink active boxes to ±frac of the joint full width, clipped to the full range.

    Seed is set to ``center`` and clamped inside each new box.
    """
    out = seed_from_best(doc, center)
    bounds = _as_dict(out.get("bounds"))
    seed = dict(_as_dict(out.get("seed_params")))
    for key in active:
        full = joint_full_bounds.get(key)
        if full is None:
            continue
        flo, fhi = float(full["lo"]), float(full["hi"])
        width = fhi - flo
        if width <= 0:
            bounds[key] = pin_bound({}, flo)
            seed[key] = flo
            continue
        c = float(center.get(key, seed.get(key, 0.5 * (flo + fhi))))
        half = frac * width
        lo = max(flo, c - half)
        hi = min(fhi, c + half)
        if hi <= lo:
            lo, hi = flo, fhi
        c = min(hi, max(lo, c))
        seed[key] = c
        bounds[key] = {"lo": lo, "hi": hi}
    # Non-active joint keys stay pinned at center.
    for key, full in joint_full_bounds.items():
        if key in active:
            continue
        if key in center:
            bounds[key] = pin_bound({}, float(center[key]))
            seed[key] = float(center[key])
    out["bounds"] = bounds
    out["seed_params"] = seed
    return out


def set_search(doc: dict, *, budget: int, sigma0: float, name: str | None = None) -> dict:
    out = copy.deepcopy(doc)
    search = dict(_as_dict(out.get("search")))
    search["budget"] = int(budget)
    search["sigma0"] = float(sigma0)
    out["search"] = search
    if name is not None:
        out["name"] = name
    return out


def joint_full_bounds(joint_doc: dict) -> dict[str, dict]:
    """Map of jointly searchable key → full bound dict (lo/hi, no search:false)."""
    out: dict[str, dict] = {}
    for k in searchable_keys(joint_doc):
        b = dict(_as_dict(_as_dict(joint_doc.get("bounds")).get(k)))
        b.pop("search", None)
        out[k] = b
    return out


def macro_active(joint_doc: dict) -> set[str]:
    return searchable_keys(joint_doc) & MACRO_KEYS


def shape_active(joint_doc: dict) -> set[str]:
    return searchable_keys(joint_doc) & SHAPE_KEYS


def permanently_pinned_keys(doc: dict) -> set[str]:
    """Keys present in ``bounds`` with ``search: false`` (never jointly searchable)."""
    out: set[str] = set()
    for k, v in _as_dict(doc.get("bounds")).items():
        if isinstance(v, dict) and v.get("search") is False:
            out.add(k)
    return out


def stage_knob_schedule(joint_doc: dict) -> dict[str, Any]:
    """Active vs fixed (pinned) jointly-searchable keys per stage — for plan.json / COMPARE.md.

    ``fixed`` = jointly searchable on the joint arm but pinned for that stage
    (``search: false``, lo=hi). Permanently pinned keys are listed separately; they never
    enter the active set.
    """
    joint = searchable_keys(joint_doc)
    macro = macro_active(joint_doc)
    shape = shape_active(joint_doc)
    return {
        "joint_searchable": sorted(joint),
        "permanently_pinned": sorted(permanently_pinned_keys(joint_doc)),
        "stage_A_macro": {
            "active": sorted(macro),
            "fixed": sorted(joint - macro),
        },
        "stage_B_shape": {
            "active": sorted(shape),
            "fixed": sorted(joint - shape),
        },
        "stage_C_polish": {
            "active": sorted(joint),
            "fixed": [],
            "note": ("all jointly searchable keys reopened in ±polish_frac boxes around "
                     "Stage B's best; permanently_pinned stay pinned"),
        },
    }


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def read_best(run_dir: Path) -> dict:
    best = json.loads((run_dir / "best.json").read_text(encoding="utf-8"))
    params = best.get("params")
    if not isinstance(params, dict):
        raise ValueError(f"{run_dir}/best.json has no params dict")
    return best


def count_ndjson(run_dir: Path) -> tuple[int, int]:
    """(n_rows, n_ok) from search.ndjson; missing file → (0, 0). ``ok`` is the row contract."""
    p = run_dir / "search.ndjson"
    if not p.is_file():
        return 0, 0
    n = n_ok = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("ok") is True:
            n_ok += 1
    return n, n_ok


def crease_angles(params: dict) -> dict[str, float] | None:
    """a(0/45/90) from the CORE az-law knobs.

    Prefers ``families.azlaw_values`` when importable; otherwise mirrors that formula
    (report-only, not a mesher call). Returns None when ``a_deg`` is missing.
    """
    if "a_deg" not in params:
        return None
    try:
        from hornlab_search.design.families import azlaw_values  # type: ignore

        def a_of(p: float) -> float:
            return float(azlaw_values(params, p)["a_deg"])
    except Exception:  # noqa: BLE001 — offline / missing package: use the local mirror
        need = ("az_a_sf_amp", "az_sf_m", "az_sf_n1", "az_sf_n2", "az_sf_n3",
                "az_sf_a", "az_sf_b", "az_a_cos_amp", "az_a_cos_pow")
        if any(k not in params for k in need):
            return None

        def a_of(p: float) -> float:
            m4 = float(params["az_sf_m"]) / 4.0
            base = (abs(math.cos(m4 * p) / float(params["az_sf_a"])) ** float(params["az_sf_n2"])
                    + abs(math.sin(m4 * p) / float(params["az_sf_b"])) ** float(params["az_sf_n3"]))
            a = float(params["a_deg"])
            a += float(params["az_a_sf_amp"]) * base ** (-1.0 / float(params["az_sf_n1"]))
            a += float(params["az_a_cos_amp"]) * abs(math.cos(p)) ** float(params["az_a_cos_pow"])
            return a

    a0, a45, a90 = a_of(0.0), a_of(math.pi / 4.0), a_of(math.pi / 2.0)
    return {
        "a0_deg": a0,
        "a45_deg": a45,
        "a90_deg": a90,
        "crease_strength_deg": a45 - 0.5 * (a0 + a90),
    }


# ------------------------------------------------------------------ build derived configs


def build_stage_b(
    stage_b_template: dict,
    joint_doc: dict,
    best_params: dict,
    *,
    budget: int,
) -> dict:
    full = joint_full_bounds(joint_doc)
    active = shape_active(joint_doc)
    doc = seed_from_best(stage_b_template, best_params)
    # Pin macro (+ anything not in shape active) at the Stage-A best; restore shape boxes.
    doc = apply_active_set(doc, active, joint_full_bounds=full)
    # apply_active_set pins non-active from seed — ensure seed already has best_params.
    doc = pin_keys_to_seed(doc, set(full) - active)
    return set_search(doc, budget=budget, sigma0=float(_as_dict(joint_doc.get("search")).get("sigma0", 0.15)),
                      name="stageB_shape__crease_core_law")


def build_stage_c(
    joint_doc: dict,
    best_params: dict,
    *,
    budget: int,
    frac: float = POLISH_FRAC,
    sigma0: float = POLISH_SIGMA0,
) -> dict:
    full = joint_full_bounds(joint_doc)
    active = set(full)  # reopen all jointly searchable keys
    doc = copy.deepcopy(joint_doc)
    doc = narrow_boxes(doc, best_params, active, full, frac=frac)
    return set_search(doc, budget=budget, sigma0=sigma0, name="stageC_polish__crease_core_law")


# ------------------------------------------------------------------ subprocess runner


def find_python() -> Path:
    """Prefer the project venv interpreter; fall back to sys.executable."""
    for rel in (".venv/Scripts/python.exe", ".venv/bin/python"):
        p = ROOT / rel
        if p.is_file():
            return p
    return Path(sys.executable)


def run_search(
    python: Path,
    config: Path,
    out_parent: Path,
    *,
    dry_run: bool,
    mode: str = "screen",
    backend: str | None = None,
) -> dict[str, Any]:
    """Launch ``hornlab-search search``; return a result dict (run_dir may be None on failure)."""
    argv = [str(python), "-m", "hornlab_search.cli", "search",
            "--config", str(config), "--mode", mode]
    if backend:
        argv += ["--backend", backend]
    # Force run root under out_parent via cwd? The CLI writes under repo runs/. We pass
    # nothing extra; the COMPARE report records whichever run_dir the CLI printed.
    meta: dict[str, Any] = {
        "config": str(config.relative_to(ROOT)) if config.is_relative_to(ROOT) else str(config),
        "argv": argv,
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if dry_run:
        meta["dry_run"] = True
        meta["exit_code"] = 0
        return meta
    log_path = out_parent / f"{config.stem}.log"
    out_parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(argv, cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, text=True)
    meta["exit_code"] = int(proc.returncode)
    meta["seconds"] = round(time.time() - t0, 1)
    meta["log"] = str(log_path.relative_to(ROOT)) if log_path.is_relative_to(ROOT) else str(log_path)
    run_dir = _parse_run_dir(log_path)
    meta["run_dir"] = run_dir
    if run_dir:
        rd = Path(run_dir)
        if not rd.is_absolute():
            rd = ROOT / rd
        meta["run_dir"] = str(rd)
        try:
            best = read_best(rd)
            meta["best_J"] = best.get("objective")
            meta["best_params"] = best.get("params")
            meta["ok"] = best.get("ok")
            n, n_ok = count_ndjson(rd)
            meta["n_evals"] = n
            meta["n_valid"] = n_ok
            angles = crease_angles(best.get("params") or {})
            if angles:
                meta["crease"] = angles
        except (OSError, ValueError, json.JSONDecodeError) as e:
            meta["best_error"] = str(e)
    return meta


_RUN_DIR_RES = (
    re.compile(r"(?:^|[\s(])output:\s*(.+?)\s*\)?\s*$"),
    re.compile(r"(?:^|\s)output\s+(.+?)\s*$"),
    re.compile(r"partial results in\s+(.+?)\s*\)?\s*$"),
)


def _parse_run_dir(log_path: Path) -> str | None:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    for line in reversed(text.splitlines()):
        for rx in _RUN_DIR_RES:
            m = rx.search(line.strip())
            if m:
                return m.group(1).strip().strip("'\"")
    return None


def _fmt_keys(keys: object) -> str:
    if not keys:
        return "_(none)_"
    if isinstance(keys, (list, tuple, set)):
        return ", ".join(f"`{k}`" for k in keys)
    return str(keys)


def write_compare(
    out_dir: Path,
    staged: list[dict],
    joint: dict | None,
    *,
    knob_schedule: dict | None = None,
) -> Path:
    lines = [
        "# Staged vs joint A/B",
        "",
        f"Written: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
    ]
    if knob_schedule:
        lines += [
            "## Knob schedule",
            "",
            f"- Joint searchable: {_fmt_keys(knob_schedule.get('joint_searchable'))}",
            f"- Permanently pinned (never searched): "
            f"{_fmt_keys(knob_schedule.get('permanently_pinned'))}",
            "",
            "| Stage | Active (searched) | Fixed / pinned this stage |",
            "|---|---|---|",
        ]
        for label, key in (
            ("A macro", "stage_A_macro"),
            ("B shape", "stage_B_shape"),
            ("C polish", "stage_C_polish"),
        ):
            block = knob_schedule.get(key) or {}
            lines.append(
                f"| {label} | {_fmt_keys(block.get('active'))} | "
                f"{_fmt_keys(block.get('fixed'))} |"
            )
        note = (knob_schedule.get("stage_C_polish") or {}).get("note")
        if note:
            lines += ["", f"_Stage C: {note}_"]
        lines.append("")

    lines += [
        "## Staged arms",
        "",
        "| Stage | best J | evals | valid | crease a0/a45/a90 | strength | seconds |",
        "|---|---:|---:|---:|---|---:|---:|",
    ]
    for s in staged:
        crease = s.get("crease") or {}
        a = ""
        if crease:
            a = (f"{crease.get('a0_deg', float('nan')):.1f} / "
                 f"{crease.get('a45_deg', float('nan')):.1f} / "
                 f"{crease.get('a90_deg', float('nan')):.1f}")
        lines.append(
            f"| {s.get('name', s.get('config', '?'))} | {s.get('best_J', '—')} | "
            f"{s.get('n_evals', '—')} | {s.get('n_valid', '—')} | {a or '—'} | "
            f"{crease.get('crease_strength_deg', '—') if crease else '—'} | "
            f"{s.get('seconds', '—')} |"
        )
    lines += ["", "## Joint control", ""]
    if joint is None:
        lines.append("_not run_")
    else:
        crease = joint.get("crease") or {}
        lines += [
            f"- best J: `{joint.get('best_J')}`",
            f"- evals / valid: `{joint.get('n_evals')}` / `{joint.get('n_valid')}`",
            f"- crease strength: `{crease.get('crease_strength_deg')}`",
            f"- run_dir: `{joint.get('run_dir')}`",
            f"- seconds: `{joint.get('seconds')}`",
        ]
        if staged and joint.get("best_J") is not None:
            final = next((s for s in reversed(staged) if s.get("best_J") is not None), None)
            if final is not None and final.get("best_J") is not None:
                sj, jj = float(final["best_J"]), float(joint["best_J"])
                verdict = "staged+polish wins" if sj < jj else (
                    "joint wins" if jj < sj else "tie")
                lines += ["", f"## Verdict (lower J is better)", "",
                          f"**{verdict}** — staged final J={sj:.4f} vs joint J={jj:.4f}."]
    path = out_dir / "COMPARE.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ------------------------------------------------------------------ synthetic coupled A/B (no GPU)


def coupled_objective(x: list[float], *, n_macro: int, m_star: list[float],
                      s_star: list[float], coupling: float) -> float:
    """J = ||m-m*||^2 + ||s - (s* + c(m-m*))||^2 — shape optimum depends on macro."""
    m = x[:n_macro]
    s = x[n_macro:]
    j_m = sum((mi - si) ** 2 for mi, si in zip(m, m_star))
    j_s = sum((si - (ssi + coupling * (mi - msi))) ** 2
              for si, ssi, mi, msi in zip(s, s_star, m, m_star))
    return j_m + j_s


def _clip01(v: float) -> float:
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def _es_block(
    x: list[float],
    active: list[int],
    budget: int,
    sigma: float,
    rng: "object",
    objective,
) -> tuple[list[float], float, int]:
    """(1+1)-ES on the active coordinates only. Returns (best_x, best_j, n_evals)."""
    best = list(x)
    best_j = float(objective(best))
    n = 1  # counted the seed evaluation
    for _ in range(max(0, budget - 1)):
        cand = list(best)
        for i in active:
            cand[i] = _clip01(best[i] + sigma * float(rng.gauss(0.0, 1.0)))
        j = float(objective(cand))
        n += 1
        if j <= best_j:
            best, best_j = cand, j
    return best, best_j, n


def run_synthetic_ab(
    *,
    n_macro: int = 5,
    n_shape: int = 12,
    budget_total: int = 60,
    seed: int = 1234,
    coupling: float = 0.7,
    polish_sigma: float = POLISH_SIGMA0,
) -> dict:
    """Equal-budget staged vs joint on a coupled toy landscape (stdlib only).

    Not a substitute for the GPU acoustic A/B — it only checks whether the
    macro→shape→polish schedule beats joint search when the optimum is coupled.
    """
    import random

    rng = random.Random(seed)
    dim = n_macro + n_shape
    m_star = [rng.random() for _ in range(n_macro)]
    s_star = [rng.random() for _ in range(n_shape)]
    x0 = [0.5] * dim

    def obj(x: list[float]) -> float:
        return coupled_objective(x, n_macro=n_macro, m_star=m_star, s_star=s_star,
                                 coupling=coupling)

    ba, bb, bc = resolve_budgets(budget_total)
    macro_idx = list(range(n_macro))
    shape_idx = list(range(n_macro, dim))
    all_idx = list(range(dim))

    # Staged
    x = list(x0)
    x, j_a, n_a = _es_block(x, macro_idx, ba, 0.15, random.Random(seed + 1), obj)
    x, j_b, n_b = _es_block(x, shape_idx, bb, 0.15, random.Random(seed + 2), obj)
    x, j_c, n_c = _es_block(x, all_idx, bc, polish_sigma, random.Random(seed + 3), obj)
    staged_evals = n_a + n_b + n_c

    # Joint
    xj, j_joint, n_joint = _es_block(
        list(x0), all_idx, budget_total, 0.15, random.Random(seed + 10), obj)

    verdict = ("staged+polish wins" if j_c < j_joint else
               ("joint wins" if j_joint < j_c else "tie"))
    return {
        "kind": "synthetic_coupled",
        "n_macro": n_macro,
        "n_shape": n_shape,
        "coupling": coupling,
        "budget_total": budget_total,
        "staged": {"J_A": j_a, "J_B": j_b, "J_C": j_c, "n_evals": staged_evals,
                   "budgets": {"A": ba, "B": bb, "C": bc}},
        "joint": {"J": j_joint, "n_evals": n_joint},
        "verdict": verdict,
        "seed_J": obj(x0),
    }


# ------------------------------------------------------------------ main


def resolve_budgets(total: int) -> tuple[int, int, int]:
    a = total // 3
    b = total // 3
    c = total - a - b
    return a, b, c


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE,
                    help="joint control YAML (also supplies full boxes)")
    ap.add_argument("--stage-a", type=Path, default=DEFAULT_STAGE_A)
    ap.add_argument("--stage-b-template", type=Path, default=DEFAULT_STAGE_B)
    ap.add_argument("--out", type=Path, default=None,
                    help="output directory under the repo (default runs/staged_ab_<utc>)")
    ap.add_argument("--budget-total", type=int, default=None,
                    help="override joint budget; stages get floor(N/3), remainder to C")
    ap.add_argument("--polish-frac", type=float, default=POLISH_FRAC)
    ap.add_argument("--polish-sigma0", type=float, default=POLISH_SIGMA0)
    ap.add_argument("--dry-run", action="store_true",
                    help="write derived YAMLs and the plan; do not launch searches")
    ap.add_argument("--synthetic", action="store_true",
                    help="run the coupled-toy staged vs joint A/B (no GPU); write SYNTHETIC.json")
    ap.add_argument("--backend", default="auto", choices=BACKENDS,
                    help="solve backend for emitted configs and CLI override "
                         "(auto: beat_metal on macOS, beat_cuda elsewhere)")
    ap.add_argument("--staged-only", action="store_true")
    ap.add_argument("--joint-only", action="store_true")
    ap.add_argument("--both", action="store_true",
                    help="run staged arms and the joint control (default when neither *-only)")
    ap.add_argument("--python", type=Path, default=None)
    args = ap.parse_args(argv)
    backend = resolve_backend(args.backend)

    if args.staged_only and args.joint_only:
        print("refuse: --staged-only and --joint-only together", file=sys.stderr)
        return 2
    do_staged = args.staged_only or args.both or not args.joint_only
    do_joint = args.joint_only or args.both or not args.staged_only
    if not args.both and not args.staged_only and not args.joint_only:
        do_staged = do_joint = True

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out if args.out else ROOT / "runs" / f"staged_ab_{stamp}"
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    synthetic_result: dict | None = None
    if args.synthetic:
        total_syn = int(args.budget_total or 60)
        synthetic_result = run_synthetic_ab(
            budget_total=total_syn, polish_sigma=args.polish_sigma0)
        (out_dir / "SYNTHETIC.json").write_text(
            json.dumps(synthetic_result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(synthetic_result, indent=2))
        (out_dir / "COMPARE_SYNTHETIC.md").write_text(
            "\n".join([
                "# Synthetic coupled A/B (no GPU)",
                "",
                f"Verdict: **{synthetic_result['verdict']}**",
                f"- staged final J: `{synthetic_result['staged']['J_C']:.6f}` "
                f"(A={synthetic_result['staged']['J_A']:.6f}, "
                f"B={synthetic_result['staged']['J_B']:.6f})",
                f"- joint J: `{synthetic_result['joint']['J']:.6f}`",
                f"- seed J: `{synthetic_result['seed_J']:.6f}`",
                f"- coupling: `{synthetic_result['coupling']}`",
                "",
                "This is not the acoustic GPU A/B. Run without `--synthetic` on the CUDA box.",
                "",
            ]),
            encoding="utf-8",
        )
        # Default: synthetic-only. Pass --dry-run to also emit acoustic stage YAMLs;
        # pass --both/--staged-only/--joint-only to launch real searches after.
        want_acoustic = args.dry_run or args.both or args.staged_only or args.joint_only
        if not want_acoustic:
            return 0

    base = args.base if args.base.is_absolute() else ROOT / args.base
    stage_a_path = args.stage_a if args.stage_a.is_absolute() else ROOT / args.stage_a
    stage_b_tmpl_path = (args.stage_b_template if args.stage_b_template.is_absolute()
                         else ROOT / args.stage_b_template)
    joint_doc = apply_solve_backend(load_yaml(base), backend)
    stage_a_doc = apply_solve_backend(load_yaml(stage_a_path), backend)
    stage_b_tmpl = apply_solve_backend(load_yaml(stage_b_tmpl_path), backend)

    total = int(args.budget_total or _as_dict(joint_doc.get("search")).get("budget") or 60)
    ba, bb, bc = resolve_budgets(total)
    joint_doc = set_search(joint_doc, budget=total,
                           sigma0=float(_as_dict(joint_doc.get("search")).get("sigma0", 0.15)))

    cfg_dir = out_dir / "configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    # Materialise Stage A with the resolved budget.
    stage_a_doc = set_search(stage_a_doc, budget=ba,
                             sigma0=float(_as_dict(stage_a_doc.get("search")).get("sigma0", 0.15)),
                             name="stageA_macro__crease_core_law")
    path_a = cfg_dir / "stageA_macro__crease_core_law.yaml"
    dump_yaml(path_a, stage_a_doc)

    path_joint = cfg_dir / "joint__crease_core_law.yaml"
    dump_yaml(path_joint, joint_doc)

    knobs = stage_knob_schedule(joint_doc)
    plan = {
        "out": str(out_dir),
        "budget_total": total,
        "budgets": {"A": ba, "B": bb, "C": bc, "joint": total},
        "backend": backend,
        "backend_choice": args.backend,
        "macro_active": knobs["stage_A_macro"]["active"],
        "shape_active": knobs["stage_B_shape"]["active"],
        "knob_schedule": knobs,
        "polish_frac": args.polish_frac,
        "polish_sigma0": args.polish_sigma0,
        "dry_run": bool(args.dry_run),
        "synthetic": bool(args.synthetic),
        "do_staged": do_staged,
        "do_joint": do_joint,
    }
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2))

    if args.dry_run and not (args.both or args.staged_only or args.joint_only):
        # Emit derived B/C configs from the seed (or synthetic path) and stop.
        best_a_params = dict(_as_dict(stage_a_doc.get("seed_params")))
        stage_b_doc = build_stage_b(stage_b_tmpl, joint_doc, best_a_params, budget=bb)
        dump_yaml(cfg_dir / "stageB_shape__crease_core_law.yaml", stage_b_doc)
        stage_c_doc = build_stage_c(
            joint_doc, dict(_as_dict(stage_b_doc.get("seed_params"))),
            budget=bc, frac=args.polish_frac, sigma0=args.polish_sigma0)
        dump_yaml(cfg_dir / "stageC_polish__crease_core_law.yaml", stage_c_doc)
        write_compare(out_dir, [], None, knob_schedule=knobs)
        return 0

    python = args.python or find_python()
    staged_metas: list[dict] = []
    joint_meta: dict | None = None

    if do_staged:
        # --- Stage A ---
        meta_a = run_search(python, path_a, out_dir, dry_run=args.dry_run, backend=backend)
        meta_a["name"] = "stageA_macro"
        staged_metas.append(meta_a)
        if args.dry_run:
            # Synthetic best = seed, so B/C configs still materialise for inspection.
            best_a_params = dict(_as_dict(stage_a_doc.get("seed_params")))
        else:
            if not meta_a.get("best_params"):
                print("Stage A produced no best.json; stopping staged chain", file=sys.stderr)
                write_compare(out_dir, staged_metas, None, knob_schedule=knobs)
                return meta_a.get("exit_code") or 1
            best_a_params = meta_a["best_params"]

        # --- Stage B ---
        stage_b_doc = build_stage_b(stage_b_tmpl, joint_doc, best_a_params, budget=bb)
        path_b = cfg_dir / "stageB_shape__crease_core_law.yaml"
        dump_yaml(path_b, stage_b_doc)
        meta_b = run_search(python, path_b, out_dir, dry_run=args.dry_run, backend=backend)
        meta_b["name"] = "stageB_shape"
        staged_metas.append(meta_b)
        if args.dry_run:
            best_b_params = dict(_as_dict(stage_b_doc.get("seed_params")))
        else:
            if not meta_b.get("best_params"):
                print("Stage B produced no best.json; stopping staged chain", file=sys.stderr)
                write_compare(out_dir, staged_metas, None, knob_schedule=knobs)
                return meta_b.get("exit_code") or 1
            best_b_params = meta_b["best_params"]

        # --- Stage C ---
        stage_c_doc = build_stage_c(
            joint_doc, best_b_params, budget=bc,
            frac=args.polish_frac, sigma0=args.polish_sigma0)
        path_c = cfg_dir / "stageC_polish__crease_core_law.yaml"
        dump_yaml(path_c, stage_c_doc)
        meta_c = run_search(python, path_c, out_dir, dry_run=args.dry_run, backend=backend)
        meta_c["name"] = "stageC_polish"
        staged_metas.append(meta_c)

    if do_joint:
        joint_meta = run_search(python, path_joint, out_dir, dry_run=args.dry_run, backend=backend)
        joint_meta["name"] = "joint"

    compare = write_compare(out_dir, staged_metas, joint_meta, knob_schedule=knobs)
    summary = {"plan": plan, "staged": staged_metas, "joint": joint_meta,
               "compare": str(compare)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n",
                                          encoding="utf-8")
    print(f"wrote {compare}")
    if args.dry_run:
        return 0
    codes = [m.get("exit_code", 1) for m in staged_metas]
    if joint_meta is not None:
        codes.append(joint_meta.get("exit_code", 1))
    return 0 if all(c == 0 for c in codes) else 1


if __name__ == "__main__":
    sys.exit(main())
