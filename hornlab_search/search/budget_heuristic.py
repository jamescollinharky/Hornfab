"""Hansen-grounded search-budget suggestions for expensive BEM evaluations.

Literature anchors (Nikolaus Hansen / CMA-ES / BBOB):

* Default population ``λ = 4 + ⌊3 ln N⌋`` (Hansen CMA-ES defaults).
* On considerably hard problems a **single** CMA run is expected to take about
  ``100·N`` … ``300·N²`` evaluations
  (`c-cmaes` ``doc.txt``: https://github.com/CMA-ES/c-cmaes/blob/master/doc.txt).
  The ``N²`` end is unreachable for GPU BEM; we keep the linear ``100·N`` floor.
* BBOB “expensive” studies often use ``~10³·N``; full IPOP/BIPOP benches go up to
  ``10⁶·N`` (Hansen BIPOP BBOB-2009). Neither fits an overnight GPU queue, so we
  stay near this repo's campaign anchors instead of BBOB's full budget.
* IPOP/BIPOP need **leftover** evaluations after the first natural stop; otherwise
  ``max`` restarts never fire.

Repo anchors ([``campaign.budget_for_tier``](campaign.py)):

* screen: ``max(40, 10·N)``
* compare (per CMA seed): ``max(150, 25·N)``

The GUI suggestion is the campaign compare scale floored by Hansen's ``100·N``,
with a restart multiplier when IPOP/BIPOP is on.
"""
from __future__ import annotations

import math
from typing import Any

GUI_BUDGET_CAP = 5000  # matches hornlab_search.gui.jobs search budget allow-list


def default_popsize(n_knobs: int) -> int:
    """Hansen default λ = 4 + ⌊3 ln N⌋ (N = searchable dimension)."""
    n = max(1, int(n_knobs))
    return 4 + int(3 * math.log(n))


def screen_budget(n_knobs: int) -> int:
    """Campaign screen tier: ``max(40, 10·N)``."""
    return max(40, 10 * max(1, int(n_knobs)))


def compare_budget(n_knobs: int) -> int:
    """Campaign compare tier per seed: ``max(150, 25·N)``."""
    return max(150, 25 * max(1, int(n_knobs)))


def suggest_budget(
    n_knobs: int,
    *,
    restarts_mode: str | None = None,
    restarts_max: int = 2,
) -> dict[str, Any]:
    """Return a JSON-able budget suggestion for Launch / Compose.

    ``restarts_mode``: ``None``/``""``/``config`` → treat as single CMA (config may still
    enable restarts in YAML). ``off`` → single CMA. ``ipop``/``bipop`` → inflate for restarts.
    """
    n = max(1, int(n_knobs))
    pop = default_popsize(n)
    screen = screen_budget(n)
    compare = compare_budget(n)
    hansen_100n = 100 * n
    # Hansen ~100·N lower end for hard problems, floored by campaign compare's absolute 150.
    single = max(150, hansen_100n)

    mode = (restarts_mode or "").strip().lower()
    if mode in ("", "none", "default", "config"):
        mode_key = "config_default"
        recommended = single
        rationale = (
            f"Single CMA (config default): max(150, Hansen ~100·N={hansen_100n}) = {single} "
            f"(campaign compare scale max(150, 25·N)={compare}; default λ={pop})."
        )
        rmax_out: int | None = None
    elif mode == "off":
        mode_key = "off"
        recommended = single
        rationale = (
            f"Single CMA (restarts off): max(150, 100·N={hansen_100n}) = {single}; λ={pop}."
        )
        rmax_out = None
    elif mode in ("ipop", "bipop"):
        rmax = max(0, min(64, int(restarts_max)))
        # Leftover room for `rmax` restarts: each at least one screen-tier chunk.
        # BIPOP also spends on small-σ runs — 25 % uplift on the single-CMA base.
        restart_floor = (1 + rmax) * screen
        base = single
        if mode == "bipop":
            base = max(base, int(math.ceil(1.25 * single)))
        recommended = max(base, restart_floor)
        mode_key = mode
        rmax_out = rmax
        rationale = (
            f"{mode.upper()} max={rmax}: max(base={base}, (1+{rmax})×screen={restart_floor}) "
            f"= {recommended}. Screen chunk max(40, 10·N)={screen}; λ={pop}. "
            "IPOP/BIPOP only help when the first ES stops before the budget is spent."
        )
    else:
        raise ValueError(
            f"restarts_mode must be config/off/ipop/bipop (or empty), got {restarts_mode!r}")

    capped = int(min(GUI_BUDGET_CAP, max(1, recommended)))
    return {
        "n_knobs": n,
        "popsize_default": pop,
        "screen": screen,
        "compare": compare,
        "hansen_100n": hansen_100n,
        "restarts_mode": mode_key,
        "restarts_max": rmax_out,
        "recommended": capped,
        "uncapped": int(recommended),
        "capped": capped < int(recommended),
        "rationale": rationale + (
            f" Capped at {GUI_BUDGET_CAP} (GUI allow-list)." if capped < int(recommended) else ""
        ),
        "sources": [
            "Hansen c-cmaes doc.txt: hard problems ~100·N … 300·N² evals (use 100·N)",
            "Hansen BIPOP BBOB-2009: full benches up to 1e6·D; expensive regime often ~1e3·D",
            "hornlab campaign.budget_for_tier: screen max(40,10·N), compare max(150,25·N)",
        ],
    }
