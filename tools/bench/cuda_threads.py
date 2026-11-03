"""Does multi-threaded Julia help the CUDA BEM path? (owner question, 2026-11-03)

One fixed mesh in the slow CUDA regime (8,044 quarter dofs), two frequencies, and
`SolveConfig.julia_threads` = 1, 8, 24. The solver host is cleared between settings so each
thread count gets a fresh host. The first solve of a setting includes host startup; the second
frequency is the warm comparison. If all three settings agree, the CUDA path is GPU-bound and
threads buy nothing (which is the useful finding).

Usage:  .venv\\Scripts\\python.exe tools\\bench\\cuda_threads.py
Output: runs/bench_cuda_threads_<UTC>/{log.txt, summary.json}
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from hornlab_beat_bem import ObservationConfig, SolveConfig
from hornlab_beat_bem.sweep import solve_frequencies

ROOT = Path(__file__).resolve().parents[2]
MESH = ROOT / "runs" / "bench_fullrange_20261103T022309Z" / "mesh" / "mesh.msh"
OUT = ROOT / "runs" / f"bench_cuda_threads_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "log.txt"
SUMMARY = OUT / "summary.json"
FREQS = (1000.0, 5000.0)
THREADS = (1, 8, 24)
T0 = time.monotonic()
LINES: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.monotonic() - T0:7.1f}s] {msg}"
    LINES.append(line)
    print(line, flush=True)
    LOG.write_text("\n".join(LINES) + "\n", encoding="utf-8", newline="\n")


def kill_hosts() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "julia.exe"], capture_output=True)
    time.sleep(2)


def main() -> int:
    if not MESH.exists():
        log(f"mesh missing: {MESH}")
        return 2
    log(f"mesh {MESH} | threads {THREADS} | frequencies {FREQS}")
    obs = ObservationConfig(distance_m=2.0, angle_count=37, planes=["horizontal", "vertical"])
    rows = []
    for n in THREADS:
        kill_hosts()
        log(f"--- julia_threads={n}: fresh host ---")
        cfg = SolveConfig(velocity_sources={2: 1.0, 10: 1.0}, impedance_matrix=True,
                          beat_backend="cuda", julia_threads=int(n), observation=obs)
        for f in FREQS:
            t0 = time.perf_counter()
            try:
                res = solve_frequencies(str(MESH), [f], cfg)
                dt = time.perf_counter() - t0
                spl0 = float(np.asarray(res.spl_db).reshape(-1)[0])
                rows.append({"threads": n, "freq": f, "ok": True, "seconds": round(dt, 3), "spl0": spl0})
                log(f"threads={n:2d} {f:7.0f} Hz {dt:7.2f}s spl0={spl0:.4f}")
            except Exception as exc:  # noqa: BLE001
                dt = time.perf_counter() - t0
                rows.append({"threads": n, "freq": f, "ok": False, "seconds": round(dt, 3),
                             "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
                log(f"threads={n:2d} {f:7.0f} Hz FAILED after {dt:.1f}s: {str(exc)[:160]}")
        kill_hosts()

    warm = {}
    for n in THREADS:
        hit = [r for r in rows if r["threads"] == n and r["ok"] and r["freq"] == FREQS[-1]]
        if hit:
            warm[n] = hit[0]["seconds"]
    base = warm.get(THREADS[0])
    summary = {"mesh": str(MESH), "frequencies_hz": list(FREQS), "threads": list(THREADS),
               "rows": rows,
               "warm_seconds_by_threads": warm,
               "speedup_vs_1_thread": {str(n): (round(base / v, 3) if base else None)
                                       for n, v in warm.items()},
               "elapsed_s": round(time.monotonic() - T0, 1), "log": str(LOG)}
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    log("SUMMARY " + json.dumps({"warm_seconds_by_threads": warm,
                                "speedup_vs_1_thread": summary["speedup_vs_1_thread"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
