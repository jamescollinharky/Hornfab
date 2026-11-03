"""CMA-ES search (01_CONTRACTS section 12, 08_TASK_PIPELINE section 4).

Unit box [0,1]^k, x0 = normalized seed, sigma0 from the config, seed from the config. Bounds are
clipped inside ``DesignSpace.denormalize``, not by CMA penalties.

Budget semantics: ``budget`` caps NON-CACHED evaluations only (the seed counts); a cache hit
(in-run memo, resumed ndjson row, cross-run solve cache) does not consume it. The cma
``maxfevals`` option is deliberately NOT used, because it counts cached replays too. The budget is
checked before every candidate, so a run can stop part-way through a generation; the partial
generation is not ``tell``-ed (a resume replays it from the cache and finishes it).

Resume is free: the same config and seed regenerate the same candidates, every one already in
``search.ndjson`` is a cache hit, so a re-run performs zero solves for work already done and then
carries on exactly where the uninterrupted run would have been.

Restarts (WP11a, ``search.restarts: {mode: ipop|bipop, max: N}``): up to 1 + ``max`` ES instances
run in sequence with pycma's own IPOP/BIPOP population/sigma schedule (see ``_RestartSchedule``).
The budget semantics above are unchanged and shared by every instance: ``n_new`` counts non-cached
evaluations across all restarts, so the whole run still stops at exactly the budget. Each instance
logs to its own ``cma/restart_k/`` prefix, and a resume replays the earlier instances from the
cache (zero budget spend) before continuing the one that was cut.
"""
from __future__ import annotations

import logging
import math
import os
import time
from collections import Counter
from pathlib import Path

import cma as cma_lib
import numpy as np

from ..dataset.record import DEFAULT_TRACE_FRACTION
from ..design.space import DesignSpace
from ..mesh.build import MeshConsistencyError
from ..metrics import compute as metrics_compute
from ..solve import worker
from ..targets.spec import Target
from ..types import Evaluation
from . import rundir
from .evaluate import (collect_lib_shas, error_kind, evaluate, make_context, read_ndjson)

log = logging.getLogger("hornlab_search.search.cma")

EVALS_PER_PROJECTION = (1000, 10000)


def covariance_summary(
    es,
    keys: list[str],
    *,
    top_eigs: int = 3,
    top_loadings: int = 5,
    include_C: bool = False,
) -> dict:
    """JSON-able snapshot of pycma's covariance ``C`` for knob importance / coupling.

    Coordinates are the unit-box search axes (``DesignSpace.keys()`` order). Diagonal
    ``C_ii`` and ``std_unit = σ√C_ii`` are the sampling scale along each knob; large values
    mean CMA still explores that axis, small means it has collapsed locally. Eigenvectors
    with large eigenvalues are the coupled directions of the local J-landscape — not a
    physical variance decomposition of the acoustics.
    """
    names = [str(k) for k in keys]
    C = np.asarray(getattr(es, "C"), dtype=float)
    if C.ndim != 2 or C.shape[0] != C.shape[1]:
        raise ValueError(f"es.C must be square, got shape {getattr(C, 'shape', None)}")
    n = int(C.shape[0])
    if len(names) != n:
        raise ValueError(f"keys length {len(names)} != C dim {n}")
    sigma = float(getattr(es, "sigma"))
    diag = np.diag(C).astype(float)
    std_unit = sigma * np.sqrt(np.maximum(diag, 0.0))
    total_std = float(std_unit.sum())
    coordinates = []
    for i, k in enumerate(names):
        coordinates.append({
            "key": k,
            "C_ii": float(diag[i]),
            "std_unit": float(std_unit[i]),
            "share": (float(std_unit[i] / total_std) if total_std > 0 else 0.0),
        })
    coordinates.sort(key=lambda r: (-r["C_ii"], r["key"]))
    w, V = np.linalg.eigh(C)
    order = np.argsort(w)[::-1]
    wsum = float(np.maximum(w, 0.0).sum())
    eigenpairs = []
    for rank, j in enumerate(order[: max(0, int(top_eigs))]):
        eig = float(w[j])
        loadings = sorted(
            ({"key": names[i], "loading": float(V[i, j])} for i in range(n)),
            key=lambda r: (-abs(r["loading"]), r["key"]),
        )
        eigenpairs.append({
            "rank": rank + 1,
            "eigenvalue": eig,
            "axis_length": float(math.sqrt(max(eig, 0.0))),
            "fraction": (eig / wsum) if wsum > 0 else 0.0,
            "top_loadings": loadings[: max(0, int(top_loadings))],
        })
    w_max = float(w[order[0]]) if len(order) else 0.0
    w_min = float(w[order[-1]]) if len(order) else 0.0
    out: dict = {
        "keys": names,
        "sigma": sigma,
        "n_dim": n,
        "condition_number": (w_max / w_min) if w_min > 0 else None,
        "coordinates": coordinates,
        "eigenpairs": eigenpairs,
        "note": ("C is the CMA search-distribution covariance in the unit box; "
                 "large C_ii / std_unit ⇒ CMA still explores that knob; "
                 "eigenvectors are coupled search directions for J, not acoustic Sobol indices."),
    }
    if include_C and n <= 16:
        out["C"] = C.tolist()
    return out

# Consecutive non-cached ``solve_failed`` evaluations (each already retried once by the backend
# after a worker-host recovery) that stop a search. A string of solver failures says the solver
# is unhealthy, not that the designs are bad: scoring them as 1000-penalties flattens the landscape
# and CMA-ES then ends on ``tolflatfitness`` (OSSE seed 4101, 2026-10-23). Stopping instead keeps
# the run resumable: ``solve_failed`` rows are never memoised, so ``--resume`` re-solves them.
MAX_CONSECUTIVE_SOLVE_FAILURES = 3


class SolverUnhealthyError(RuntimeError):
    """Too many consecutive solver failures; the run stops (resumable) instead of scoring them."""


def summarize(evals: list[Evaluation], wall_seconds: list[float]) -> dict:
    """The honest answer to "how fast is this": counts, failures by reason, GPU seconds, mean
    seconds per candidate, candidates per hour, projected hours for 1,000 and 10,000."""
    new = [e for e in evals if not e.cached]
    fails = Counter(error_kind(e.error) for e in new if e.error)
    solve_s = sum(float(e.outcome.seconds) for e in new if e.outcome is not None)
    mesh_s = sum(float(e.mesh.seconds) for e in new if e.mesh is not None)
    mean_s = (sum(wall_seconds) / len(wall_seconds)) if wall_seconds else float("nan")
    cph = 3600.0 / mean_s if mean_s and math.isfinite(mean_s) and mean_s > 0 else float("nan")
    return {
        "evaluations": len(evals), "non_cached": len(new), "cache_hits": len(evals) - len(new),
        "failures_by_reason": dict(fails), "failures": int(sum(fails.values())),
        "total_gpu_seconds": solve_s, "total_mesh_seconds": mesh_s,
        "mean_seconds_per_candidate": mean_s, "candidates_per_hour": cph,
        "projected_hours": {str(n): (n / cph if math.isfinite(cph) and cph > 0 else float("nan"))
                            for n in EVALS_PER_PROJECTION},
    }


def summarize_rows(rows: list[dict]) -> dict:
    """The same summary computed from search.ndjson rows, i.e. cumulative over every resume of a
    run directory (``summarize`` only sees the current invocation)."""
    new = [r for r in rows if not r.get("cached")]
    fails = Counter(r.get("kind") or error_kind(r.get("error", "")) for r in rows if not r.get("ok"))
    sec = lambda r, k: float((r.get("seconds") or {}).get(k) or 0.0)       # noqa: E731
    tot = [sec(r, "total") for r in new]
    mean_s = (sum(tot) / len(tot)) if tot else float("nan")
    cph = 3600.0 / mean_s if tot and mean_s > 0 else float("nan")
    return {
        "evaluations": len(rows), "non_cached": len(new), "cache_hits": len(rows) - len(new),
        "failures_by_reason": dict(fails), "failures": int(sum(fails.values())),
        "total_gpu_seconds": sum(sec(r, "solve") for r in new),
        "total_mesh_seconds": sum(sec(r, "mesh") for r in new),
        "mean_seconds_per_candidate": mean_s, "candidates_per_hour": cph,
        "projected_hours": {str(n): (n / cph if math.isfinite(cph) and cph > 0 else float("nan"))
                            for n in EVALS_PER_PROJECTION},
    }


def _prepare(cfg, run_dir: Path, mode: str, backend, store, cache_dir, trace_fraction, command,
             config_path, lib_shas):
    """Shared setup of ``search`` and ``run_once``: directories, backend, warm worker, context."""
    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_compute.reset_warning_state()
    if backend is None:
        from ..solve.base import get_backend
        kw: dict = {"timeout_s": float(cfg.solve.timeout_s)}
        # WP15 cuda_fused is CUDA-only (Metal/CPU must not receive the flag).
        if str(cfg.solve.backend) == "beat_cuda":
            kw["cuda_fused"] = bool(getattr(cfg.solve, "cuda_fused", False))
        backend = get_backend(cfg.solve.backend, **kw)
    worker.warm(backend)                       # once, before the seed; idempotent
    lib_shas = lib_shas or collect_lib_shas()
    ctx = make_context(cfg, store, cache_dir=cache_dir, lib_shas=lib_shas,
                       trace_fraction=trace_fraction, ndjson=run_dir / "search.ndjson")
    first = rundir.read_json(run_dir / "run.json") is None
    rundir.write_config_snapshot(run_dir, cfg)
    base = {"run_id": run_dir.name, "config_name": cfg.name, "family": cfg.family, "mode": mode,
            "config_path": None if config_path is None else str(config_path),
            "config": cfg.raw, "config_sha": rundir.config_sha(cfg.raw),
            "backend": cfg.solve.backend, "lib_shas": lib_shas,
            "objective_version": int(getattr(cfg, "objective_version", 1)),
            "toolchain": rundir.toolchain_snapshot(),
            "runtime": rundir.runtime_provenance(),
            "cma_seed": cfg.search.seed, "trace_fraction": trace_fraction,
            "command": command, "status": "running", "started_utc": rundir.utc_now(),
            "dataset_dir": None if store is None else str(store.root)}
    if first:
        base["created_utc"] = base["started_utc"]
        rundir.write_json_atomic(run_dir / "run.json", base)
    else:
        prev = rundir.read_json(run_dir / "run.json", {}) or {}
        resumes = list(prev.get("resumes", [])) + [base["started_utc"]]
        base.pop("started_utc")
        base["resumes"] = resumes
        rundir.update_run_json(run_dir, **base)
    return run_dir, backend, ctx


def _detach(backend) -> None:
    if str(getattr(backend, "name", "")).startswith("beat"):
        worker.detach()                        # leaves the host warm for the next run


class _RestartSchedule:
    """The population-size / sigma0 schedule of pycma's own restart loop, mirrored exactly.

    Source (read-only, never edited): ``cma/evolution_strategy.py`` in the venv.
    - schedule: lines 5004-5043, ``fmin(...)``'s ``while True:  # restart loop``
    - per-run budget accounting: lines 5218-5230 (``small_i`` / ``large_i``)

    IPOP (``incpopsize=2``, no small restarts, sigma unchanged) — lines 5008-5013.
    BIPOP — while the cumulated SMALL budget is below ``bipop * max(1, cumulated LARGE budget)``
    the restart is a SMALL one: ``popsize = int(popsize0 * m**(U**2))`` with ``U`` uniform in
    [0,1) and ``sigma = sigma0 * 0.01**U`` (lines 5022-5033); otherwise a LARGE one, i.e. IPOP's
    doubling with the small runs subtracted from the exponent (lines 5035-5043). As in pycma, the
    initial run counts as a "small" run for the poptype, but its budget is deliberately NOT added
    to the small cumulation (the ``XXX`` at lines 5220-5224 reproduces the Matlab code).

    Determinism and resume: the draws come from a private rng seeded with ``search.seed`` and are
    taken in restart order (k = 1, 2, ...), and the budgets are the number of *evaluations* each run
    consumed (pycma's ``es.countevals``), so a resume that replays the earlier candidates from the
    cache rebuilds the identical sequence of plan decisions.

    - Note (deliberate divergence from pycma): pycma's small-run iteration cap at its :5032
      (``maxiter = min(maxiter0, 0.5 * sum(large_i) / popsize)``) is deliberately NOT mirrored here:
      the global evaluation budget governs, so a BIPOP small restart may run with no other per-run
      iteration cap and can consume the whole remaining budget.
    - Note (deliberate divergence from pycma): ``search.restarts.max`` here counts ALL restarts,
      including BIPOP small ones; pycma's own restart limit (:~5251) counts only non-small restarts.
    """

    def __init__(self, mode: str, seed: int):
        if mode not in ("ipop", "bipop"):
            raise ValueError(f"unknown restart mode {mode!r}")
        self.mode = str(mode)
        self.rng = np.random.default_rng(int(seed))
        self.base_popsize: int | None = None      # pycma's popsize0, read off the initial run
        self.small_budget: list[int] = []         # pycma's small_i
        self.large_budget: list[int] = []         # pycma's large_i
        self.runs_with_small = 0

    def plan(self, k: int) -> tuple[str, float, int]:
        """(population type, sigma factor, popsize) for restart ``k >= 1``."""
        if self.mode == "ipop":                                       # :5008-5013
            return "large", 1.0, int(self.base_popsize * 2 ** k)
        if sum(self.small_budget) < max(1, sum(self.large_budget)):    # :5022
            self.runs_with_small += 1                                 # :5027
            sigma_factor = 0.01 ** float(self.rng.uniform())          # :5029
            multiplier = 2 ** (k - self.runs_with_small)              # :5030 incpopsize=2
            u2 = float(self.rng.uniform()) ** 2                       # :5031
            return "small", sigma_factor, int(self.base_popsize * multiplier ** u2)
        return "large", 1.0, int(self.base_popsize * 2 ** (k - self.runs_with_small))          # :5040

    def observe(self, k: int, poptype: str, evaluations: int) -> None:
        """Record one finished run's evaluation count into the matching BIPOP cumulation."""
        if k == 0:
            return                             # the initial run is not counted (:5220-5224)
        if poptype == "small":
            self.small_budget.append(int(evaluations))
        elif self.mode == "bipop":
            self.large_budget.append(int(evaluations))


def search(cfg, run_dir, mode="screen", resume=None, *, backend=None, budget: int | None = None,
           store=None, cache_dir=None, trace_fraction: float = DEFAULT_TRACE_FRACTION,
           command: str | None = None, config_path=None, lib_shas: dict | None = None,
           max_evals: int | None = None) -> Evaluation:
    """CMA-ES from the seed. Returns the best Evaluation. Writes into ``run_dir`` (or ``resume``,
    an existing run directory to continue): run.json, search.ndjson, best.json, designs/, cma/.

    ``budget`` caps NEW (non-cached) evaluations. ``max_evals`` additionally caps ALL evaluations
    of this invocation, cached ones included: a campaign comparison must give every family the
    same amount of search, and a replayed CMA seed would otherwise get its cached prefix for free.

    Raises only for things that must stop a run: a mesh units/symmetry bug
    (``MeshConsistencyError``), KeyboardInterrupt, an unusable backend.
    """
    if cfg.search.algorithm == "cma_me":
        # WP11b: quality-diversity runs live in their own module; the import is local so the
        # single-ES/restarts path never pulls ribs in (it is an optional extra).
        from .cma_me import search as cma_me_search
        return cma_me_search(cfg, run_dir, mode, resume, backend=backend, budget=budget,
                             store=store, cache_dir=cache_dir, trace_fraction=trace_fraction,
                             command=command, config_path=config_path, lib_shas=lib_shas,
                             max_evals=max_evals)
    if cfg.search.algorithm != "cma":
        raise ValueError(f"search.algorithm {cfg.search.algorithm!r} is not implemented in "
                         f"phase 1 (cma, cma_me)")
    run_dir = Path(resume if resume is not None else run_dir)
    run_dir, backend, ctx = _prepare(cfg, run_dir, mode, backend, store, cache_dir, trace_fraction,
                                     command, config_path, lib_shas)
    max_new = int(budget if budget is not None else cfg.search.budget)
    space = DesignSpace.from_config(cfg)
    x0 = space.normalize(space.seed)
    restarts = getattr(cfg.search, "restarts", None)
    (run_dir / "cma").mkdir(exist_ok=True)

    def es_options(prefix: Path, seed: int, popsize) -> dict:
        o = {"bounds": [0.0, 1.0], "seed": int(seed), "tolfun": float(cfg.search.tolfun),
             "verb_filenameprefix": str(prefix) + os.sep, "verb_disp": 0, "verbose": -1}
        if popsize:
            o["popsize"] = int(popsize)
        return o

    popsize0 = int(cfg.search.popsize) if cfg.search.popsize else None
    es = None
    if restarts is None:                       # today's single-ES path, bit-for-bit
        es = cma_lib.CMAEvolutionStrategy(list(map(float, x0)), float(cfg.search.sigma0),
                                          es_options(run_dir / "cma", cfg.search.seed, popsize0))

    evals: list[Evaluation] = []
    wall: list[float] = []
    restarts_log: list[dict] = []              # filled only when search.restarts is configured
    state = {"best": None, "best_no": None, "seed_ev": None, "n_new": 0, "stop": "",
             "solve_fail_streak": 0}

    # On a resume the best so far is already on disk in search.ndjson: start from it, so a short
    # (or zero-budget) resume can never overwrite best.json with something worse.
    prior = [e for e in ctx.known.values() if not e.error]
    if prior:
        b0 = min(prior, key=lambda e: e.objective)
        rows0 = read_ndjson(run_dir / "search.ndjson")
        state["best"] = b0
        state["best_no"] = next((r.get("n") for r in rows0 if r.get("design_hash") == b0.design_hash), None)
        rundir.write_best(run_dir, b0, mode, state["best_no"])

    def run_one(design) -> Evaluation:
        t0 = time.perf_counter()
        ev = evaluate(design, space, cfg, mode, run_dir, store, backend, ctx=ctx)
        dt = time.perf_counter() - t0
        evals.append(ev)
        if not ev.cached:
            state["n_new"] += 1
            wall.append(dt)
        b = state["best"]
        if b is None or ev.objective < b.objective or (b.error and not ev.error):
            state["best"], state["best_no"] = ev, len(evals) - 1
            rundir.write_best(run_dir, ev, mode, state["best_no"])      # after EVERY improvement
        if not ev.cached and error_kind(ev.error) == "solve_failed":
            state["solve_fail_streak"] += 1
            if state["solve_fail_streak"] >= MAX_CONSECUTIVE_SOLVE_FAILURES:
                raise SolverUnhealthyError(
                    f"{state['solve_fail_streak']} consecutive solve_failed evaluations (last: "
                    f"{ev.error.splitlines()[0][:200]}); the solver is unhealthy, not the designs. "
                    f"Clear hosts (gpu-clean) and continue with --resume")
        elif not ev.cached:
            state["solve_fail_streak"] = 0
        return ev

    def finish(status: str, *, cov: dict | None = None) -> None:
        last = summarize(evals, wall)
        # run.json["stats"] is CUMULATIVE over every resume (from the ndjson); the numbers of this
        # invocation alone are kept under "last_invocation" (cache hits there include resume replays).
        stats = summarize_rows(read_ndjson(run_dir / "search.ndjson")) if (run_dir / "search.ndjson").exists() else last
        seed_ev = state["seed_ev"]
        best = state["best"]
        upd = {"status": status, "finished_utc": rundir.utc_now(), "stop_reason": state["stop"],
               "stats": stats, "last_invocation": last, "budget": max_new}
        if seed_ev is not None:
            upd["seed"] = {"design_hash": seed_ev.design_hash, "objective": seed_ev.objective,
                           "terms": seed_ev.terms}
        if best is not None:
            upd["best"] = {"design_hash": best.design_hash, "objective": best.objective,
                           "eval_no": state["best_no"]}
        if restarts is not None:               # absent key => run.json schema stays exactly today's
            upd["restarts"] = restarts_log
        if cov is not None:                    # additive; older readers ignore the key
            upd["cma_covariance"] = cov
            try:
                rundir.write_json_atomic(run_dir / "cma" / "covariance.json", cov)
            except Exception:  # noqa: BLE001 - optional sidecar; run.json is the contract
                log.debug("could not write cma/covariance.json", exc_info=True)
        rundir.update_run_json(run_dir, **upd)
        log.info("search %s: %d evaluations (%d new, %d cached), %d failures %s, GPU %.1f s, "
                 "%.1f s/candidate, %.0f candidates/h, 1k evals = %.1f h, 10k = %.1f h",
                 status, stats["evaluations"], stats["non_cached"], stats["cache_hits"],
                 stats["failures"], stats["failures_by_reason"], stats["total_gpu_seconds"],
                 stats["mean_seconds_per_candidate"], stats["candidates_per_hour"],
                 stats["projected_hours"]["1000"], stats["projected_hours"]["10000"])

    try:
        # 1. the seed first: every later number is meaningless without the baseline it must beat
        seed_ev = run_one(space.seed)
        state["seed_ev"] = seed_ev
        log.info("seed J=%.4f terms=%s", seed_ev.objective,
                 {k: round(v, 4) for k, v in seed_ev.terms.items()})
        cap = int(max_evals) if max_evals else None

        def exhausted() -> bool:
            return state["n_new"] >= max_new or (cap is not None and len(evals) >= cap)

        def sweep(es_instance, restart_index: int | None = None) -> str:
            """Generations of ONE ES instance until its own stop criteria or the budget run out.

            Returns the stop reason. A generation cut by the budget is NOT ``tell``-ed (a resume
            replays it from the cache and finishes it), exactly as in the single-ES path."""
            gen = 0
            while not exhausted():
                stop = es_instance.stop()
                if stop:
                    return "cma: " + ", ".join(sorted(stop))
                X = es_instance.ask()
                F = []
                for x in X:
                    if exhausted():
                        break
                    F.append(run_one(space.denormalize(np.asarray(x))).objective)
                if len(F) < len(X):           # budget ran out mid-generation: do not tell
                    return "budget"
                es_instance.tell(X, F)
                try:
                    es_instance.logger.add()
                except Exception:  # noqa: BLE001 - cma's own logging is optional
                    pass
                gen += 1
                where = "" if restart_index is None else f"restart {restart_index} "
                log.info("%sgeneration %d: best this generation %.4f, best overall %.4f "
                         "(%d new evaluations)",
                         where, gen, min(F), state["best"].objective, state["n_new"])
            return "budget"

        keys = space.keys()
        last_cov: dict | None = None
        if restarts is None:
            state["stop"] = sweep(es)
            try:
                last_cov = covariance_summary(es, keys, include_C=True)
            except Exception:  # noqa: BLE001 - never fail a finished search on a diagnostic dump
                log.warning("cma_covariance snapshot failed", exc_info=True)
        else:
            # 2. restarts (WP11a): up to 1 + max ES instances, each with its own cma/restart_k/
            # generation log. The budget accounting above is shared by every instance: n_new counts
            # non-cached evaluations across ALL restarts, and a budget cut stops the whole search.
            sched = _RestartSchedule(str(restarts["mode"]), int(cfg.search.seed))
            max_restarts = int(restarts["max"])
            k = 0
            poptype = "small"                 # pycma's initial run is accounted as a small run
            while True:
                if k == 0:
                    sigma_factor, pop_k = 1.0, popsize0
                else:
                    poptype, sigma_factor, pop_k = sched.plan(k)
                seed_k = int(cfg.search.seed) + k            # pycma: opts['seed'] += 1 per restart
                es_k = cma_lib.CMAEvolutionStrategy(
                    list(map(float, x0)), float(sigma_factor * float(cfg.search.sigma0)),
                    es_options(run_dir / "cma" / f"restart_{k}", seed_k, pop_k))
                if k == 0:
                    # pycma's popsize0: whatever the initial run got, i.e. cma's own default when
                    # search.popsize is unset (never re-derived here).
                    sched.base_popsize = int(es_k.sp.popsize)
                pop_k = int(es_k.sp.popsize)
                n_new_before, n_all_before = state["n_new"], len(evals)
                reason = sweep(es_k, k)
                # pycma's this_evals = es.countevals - base_evals: ALL evaluations of the run,
                # cache replays included, so the BIPOP schedule rebuilds identically on a resume.
                evals_in_restart = len(evals) - n_all_before
                entry = {"index": k, "stop": reason,
                         "n_new_in_restart": state["n_new"] - n_new_before,
                         "evals_in_restart": evals_in_restart,
                         "popsize": pop_k,
                         "sigma0": float(sigma_factor * float(cfg.search.sigma0))}
                try:
                    cov_k = covariance_summary(es_k, keys, include_C=False)
                    entry["covariance"] = {
                        "sigma": cov_k["sigma"],
                        "condition_number": cov_k["condition_number"],
                        "coordinates": cov_k["coordinates"],
                        "eigenpairs": cov_k["eigenpairs"],
                    }
                    last_cov = cov_k
                except Exception:  # noqa: BLE001
                    log.warning("cma_covariance snapshot failed (restart %d)", k, exc_info=True)
                restarts_log.append(entry)
                sched.observe(k, poptype, evals_in_restart)
                if reason == "budget":
                    state["stop"] = "budget"
                    break
                if k >= max_restarts:
                    state["stop"] = "restarts_exhausted"
                    break
                log.info("restart %d stopped (%s) after %d new evaluations; population %d -> next",
                         k, reason, restarts_log[-1]["n_new_in_restart"], pop_k)
                k += 1
        finish("finished", cov=last_cov)
    except KeyboardInterrupt:
        state["stop"] = "interrupted"
        finish("interrupted")
        raise
    except (MeshConsistencyError, SolverUnhealthyError) as exc:
        state["stop"] = f"aborted: {type(exc).__name__}: {exc}"
        finish("aborted")
        raise
    finally:
        _detach(backend)
    return state["best"]


def run_once(cfg, run_dir, mode="screen", *, backend=None, store=None, cache_dir=None,
             trace_fraction: float = DEFAULT_TRACE_FRACTION, command: str | None = None,
             config_path=None, lib_shas: dict | None = None) -> Evaluation:
    """Evaluate the seed design once (``hornlab-search run``): the same machinery as a search
    with a budget of one, without the optimizer."""
    run_dir, backend, ctx = _prepare(cfg, Path(run_dir), mode, backend, store, cache_dir,
                                     trace_fraction, command, config_path, lib_shas)
    space = DesignSpace.from_config(cfg)
    t0 = time.perf_counter()
    try:
        ev = evaluate(space.seed, space, cfg, mode, run_dir, store, backend, ctx=ctx)
        rundir.write_best(run_dir, ev, mode, 0)
        wall = [] if ev.cached else [time.perf_counter() - t0]
        stats = summarize([ev], wall)
        rundir.update_run_json(run_dir, status="finished", finished_utc=rundir.utc_now(), stats=stats,
                               last_invocation=stats,
                               seed={"design_hash": ev.design_hash, "objective": ev.objective,
                                     "terms": ev.terms},
                               best={"design_hash": ev.design_hash, "objective": ev.objective,
                                     "eval_no": 0})
    except MeshConsistencyError as exc:
        rundir.update_run_json(run_dir, status="aborted", stop_reason=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        _detach(backend)
    return ev
