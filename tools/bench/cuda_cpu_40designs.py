"""40 existing designs, one identical solve each, CUDA vs CPU, per-design logging.

Design set: 40 STORED designs (no CAD, no re-meshing), chosen deterministically:
  - 30 single-source designs stratified across the dof range (tags {1,2} -> drive tag 2)
  - 10 multi-entry designs (tags {1,2,10} -> drive tags 2 and 10)
Same frequency (1 kHz), same observation (2 m, 37 angles, 2 planes), same impedance-matrix flag
for both arms. Each arm runs in its own pass with the solver host cleared first, so the first
design in an arm is the cold-start datapoint and the rest are warm.

Usage:  .venv\\Scripts\\python.exe tools\\bench\\cuda_cpu_40designs.py [--designs 40] [--max-seconds 2400]
Output: runs/bench_40designs_<UTC>/log.txt, results.jsonl, summary.json
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import hornlab_beat_bem as beat
from hornlab_beat_bem import ObservationConfig, SolveConfig
from hornlab_beat_bem.sweep import solve_frequencies

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs" / f"bench_40designs_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "log.txt"
RESULTS = OUT / "results.jsonl"
SUMMARY = OUT / "summary.json"
FREQ = 1000.0
T0 = time.monotonic()
LINES: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.monotonic() - T0:7.1f}s] {msg}"
    LINES.append(line)
    print(line, flush=True)
    LOG.write_text("\n".join(LINES) + "\n", encoding="utf-8", newline="\n")


def vram_mib() -> int | None:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"],
                         capture_output=True, text=True)
    try:
        return int("".join(c for c in out.stdout if c.isdigit()))
    except ValueError:
        return None


class Peak:
    def __init__(self, period=2.0):
        self.peak, self._stop, self._period = (vram_mib() or 0), threading.Event(), period

    def __enter__(self):
        def loop():
            while not self._stop.is_set():
                v = vram_mib()
                if v is not None:
                    self.peak = max(self.peak, v)
                self._stop.wait(self._period)
        self._t = threading.Thread(target=loop, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()


def kill_hosts() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "julia.exe"], capture_output=True)
    time.sleep(2)


def candidate_designs(limit: int) -> list[dict]:
    """Stored mesh + tags, stratified by dof; MEH designs (tag 10) get priority for their slots."""
    rows = []
    for meta_path in glob.glob(str(ROOT / "runs" / "*" / "designs" / "*" / "mesh_meta.json")):
        mesh = Path(meta_path).with_suffix("").with_name("mesh.msh")
        if not mesh.exists():
            continue
        try:
            meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
            summary = meta.get("summary") or {}
            n = summary.get("n_nodes")
            tags = sorted(int(t) for t in (summary.get("tags") or {}))
        except Exception:
            continue
        if not n or 2 not in tags:
            continue
        rows.append({"mesh": str(mesh), "dofs": int(n), "tags": tags,
                     "run": Path(meta_path).parents[2].name,
                     "design": Path(meta_path).parent.name})
    rows.sort(key=lambda r: r["dofs"])
    meh = [r for r in rows if 10 in r["tags"]]
    plain = [r for r in rows if 10 not in r["tags"]]
    n_meh = min(len(meh), max(0, limit - 30))
    rand = random.Random(20261103)
    picked = meh[:n_meh] if len(meh) <= n_meh else rand.sample(meh, n_meh)
    # stratify the rest across the dof range so the timing curve is covered
    n_plain = limit - len(picked)
    if n_plain > 0 and plain:
        step = max(1, len(plain) // n_plain)
        chunk = plain[::step][:n_plain]
        picked += chunk
    return sorted(picked, key=lambda r: r["dofs"])


def observation() -> ObservationConfig:
    return ObservationConfig(distance_m=2.0, angle_count=37, planes=["horizontal", "vertical"])


def run_one(design: dict, backend: str) -> dict:
    tags = [2, 10] if 10 in design["tags"] else [2]
    cfg = SolveConfig(velocity_sources={t: 1.0 for t in tags}, impedance_matrix=True,
                      beat_backend=backend, observation=observation())
    t0 = time.perf_counter()
    try:
        with Peak() as peak:
            res = solve_frequencies(design["mesh"], [FREQ], cfg)
        dt = time.perf_counter() - t0
        spl0 = float(np.asarray(res.spl_db).reshape(-1)[0])
        return {"ok": True, "seconds": round(dt, 3), "spl0": spl0,
                "peak_vram_mib": peak.peak if backend == "cuda" else None,
                "channel_tags": list(res.channel_tags)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "seconds": round(time.perf_counter() - t0, 3),
                "error": f"{type(exc).__name__}: {str(exc)[:300]}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", type=int, default=40)
    ap.add_argument("--max-seconds", type=float, default=2400.0)
    args = ap.parse_args()

    statuses = beat.beat_backend_statuses()
    for name in ("cuda", "cpu"):
        if statuses[name]["state"] != "ready":
            log(f"{name} is not ready ({statuses[name]['state']})")
            return 2
    log(f"output: {OUT}")
    log(f"cuda: {statuses['cuda']['state']} | cpu: {statuses['cpu']['state']} | frequency {FREQ} Hz")

    designs = candidate_designs(args.designs)
    log(f"design set: {len(designs)} stored designs "
        f"({sum(1 for d in designs if 10 in d['tags'])} multi-entry), "
        f"dofs {designs[0]['dofs']}..{designs[-1]['dofs']}")

    arm_totals: dict[str, list[float]] = {"cuda": [], "cpu": []}
    table: dict[str, dict] = {d["mesh"]: {"dofs": d["dofs"], "tags": d["tags"],
                                          "run": d["run"], "design": d["design"]} for d in designs}
    for backend in ("cuda", "cpu"):
        log(f"--- arm {backend}: clearing hosts, then {len(designs)} solves ---")
        kill_hosts()
        log(f"arm {backend} VRAM baseline {vram_mib()} MiB")
        for i, d in enumerate(designs, 1):
            if time.monotonic() - T0 > args.max_seconds:
                log(f"budget reached ({args.max_seconds:.0f}s) before {backend} design {i}")
                break
            r = run_one(d, backend)
            table[d["mesh"]][backend] = r
            if r["ok"]:
                arm_totals[backend].append(r["seconds"])
            with open(RESULTS, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"backend": backend, "i": i, **d, **r}) + "\n")
            log(f"{backend:4s} {i:02d}/{len(designs)} dofs={d['dofs']:5d} tags={d['tags']} "
                f"{r['seconds']:7.2f}s" + (f" spl0={r['spl0']:.3f}" if r.get("ok") else f" FAILED {r.get('error','')[:80]}"))
        kill_hosts()

    # ---------- comparison ----------
    rows = [{"mesh": m, **v} for m, v in table.items()]
    both = [r for r in rows if r.get("cuda", {}).get("ok") and r.get("cpu", {}).get("ok")]
    ratios = [r["cpu"]["seconds"] / r["cuda"]["seconds"] for r in both if r["cuda"]["seconds"] > 0]
    deltas = [abs(r["cuda"]["spl0"] - r["cpu"]["spl0"]) for r in both]
    cold = {b: (arm_totals[b][0] if arm_totals[b] else None) for b in arm_totals}
    warm = {b: (arm_totals[b][1:] or []) for b in arm_totals}
    summary = {
        "designs": len(designs), "paired": len(both),
        "frequency_hz": FREQ,
        "cuda_total_s": round(sum(arm_totals["cuda"]), 1),
        "cpu_total_s": round(sum(arm_totals["cpu"]), 1),
        "cold_first_call_s": cold,
        "cuda_warm_mean_s": round(float(np.mean(warm["cuda"])), 3) if warm["cuda"] else None,
        "cpu_warm_mean_s": round(float(np.mean(warm["cpu"])), 3) if warm["cpu"] else None,
        "cpu_over_cuda_ratio": {
            "median": round(float(np.median(ratios)), 3) if ratios else None,
            "mean": round(float(np.mean(ratios)), 3) if ratios else None,
            "min": round(float(np.min(ratios)), 3) if ratios else None,
            "max": round(float(np.max(ratios)), 3) if ratios else None,
        },
        "spl_parity_abs_db": {"max": max(deltas), "median": float(np.median(deltas))} if deltas else None,
        "ratio_lt_1_cpu_faster": sum(1 for r in ratios if r < 1.0),
        "budget_s": args.max_seconds, "elapsed_s": round(time.monotonic() - T0, 1),
        "log": str(LOG), "results": str(RESULTS),
    }
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    log("SUMMARY " + json.dumps({k: v for k, v in summary.items() if k not in ("log", "results")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
