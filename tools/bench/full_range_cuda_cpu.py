"""One brief + one mesh, the FULL contracted frequency grid, CUDA vs CPU, per-frequency timing.

Fixed design: the T2 search config (`examples/typologies/meh_2026-10-30/meh_t2a_search.yaml`) -> its
brief (`meh_home_90x60_t2`) and its seed mesh at the production screen settings. Frequencies come from
the config's own `solve.freq_grid` (120 Hz - 12 kHz at 1/6 octave, 41 points) so this is the band the
screens are supposed to cover.

Each frequency is solved as its own call, so a failure is attributable to a frequency, not a whole arm.
A warm-up call at 1 kHz is made first and excluded from the timings. An arm stops at its first failure
and records the frequency (the CUDA arm is expected to hit the 8 GB ceiling somewhere in the sweep; that
is a result, not an error to hide).

Usage:  .venv\\Scripts\\python.exe tools\\bench\\full_range_cuda_cpu.py [--max-seconds 3600]
Output: runs/bench_fullrange_<UTC>/{log.txt, results.jsonl, summary.json}
"""
from __future__ import annotations

import argparse
import json
import statistics
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
CONFIG = ROOT / "examples" / "typologies" / "meh_2026-10-30" / "meh_t2a_search.yaml"
OUT = ROOT / "runs" / f"bench_fullrange_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "log.txt"
RESULTS = OUT / "results.jsonl"
SUMMARY = OUT / "summary.json"
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
        threading.Thread(target=loop, daemon=True).start()
        return self

    def __exit__(self, *a):
        self._stop.set()


def kill_hosts() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "julia.exe"], capture_output=True)
    time.sleep(2)


def build_production_mesh() -> tuple[Path, dict]:
    from hornlab_search.config import load_config, mesh_spec
    from hornlab_search.mesh import step_build
    from hornlab_search.design.generated import GeneratedSpace

    cfg = load_config(CONFIG)
    space = GeneratedSpace.from_config(cfg)
    tool = step_build.load_cad_tool(tool=step_build.MEH_TOOL)
    recipe = {"tool": step_build.MEH_TOOL, **tool.defaults()}
    spec = mesh_spec("screen", cfg)
    out = OUT / "mesh"
    res = step_build.build_mesh_from_cad(recipe, spec, cfg, out, mode="screen")
    meta = json.loads((out / "mesh_meta.json").read_text(encoding="utf-8"))
    return res.path, {"dofs": meta["summary"]["n_nodes"],
                      "triangles": meta["summary"]["n_triangles"],
                      "symmetry_plane": res.symmetry_plane,
                      "seed_slide_mm": space.seed.params["cad"]["slide_mm"]}


def frequencies(config_path=CONFIG) -> list[float]:
    """The grid comes from the config's own solve settings: the search config carries the contracted
    41-point 120-12k grid, the CAD-authored seed config carries the frozen 12-point 500-10k screen grid."""
    from hornlab_search.config import load_config, mode_freqs
    return [float(f) for f in mode_freqs("screen", load_config(config_path))]


def one(mesh: Path, freq: float, backend: str) -> dict:
    cfg = SolveConfig(velocity_sources={2: 1.0, 10: 1.0}, impedance_matrix=True,
                      beat_backend=backend,
                      observation=ObservationConfig(distance_m=2.0, angle_count=37,
                                                    planes=["horizontal", "vertical"]))
    t0 = time.perf_counter()
    try:
        with Peak() as peak:
            res = solve_frequencies(str(mesh), [freq], cfg)
        return {"ok": True, "seconds": round(time.perf_counter() - t0, 3),
                "spl0": float(np.asarray(res.spl_db).reshape(-1)[0]),
                "peak_vram_mib": peak.peak if backend == "cuda" else None}
    except Exception as exc:  # noqa: BLE001 - a failure at a frequency is the finding
        return {"ok": False, "seconds": round(time.perf_counter() - t0, 3),
                "error": f"{type(exc).__name__}: {str(exc)[:240]}",
                "peak_vram_mib": vram_mib() if backend == "cuda" else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-seconds", type=float, default=3600.0)
    ap.add_argument("--mesh", default="", help="stored mesh.msh to use instead of building one")
    ap.add_argument("--grid-config", default=str(CONFIG),
                    help="config whose solve grid is used (search config = 41 pts, seed config = 12 pts)")
    args = ap.parse_args()

    statuses = beat.beat_backend_statuses()
    for name in ("cuda", "cpu"):
        if statuses[name]["state"] != "ready":
            log(f"{name} not ready ({statuses[name]['state']})")
            return 2

    log(f"output: {OUT}")
    if args.mesh:
        mesh = Path(args.mesh).resolve()   # the solver worker opens this path itself: must be absolute
        meta = json.loads((mesh.parent / "mesh_meta.json").read_text(encoding="utf-8"))
        mesh_info = {"dofs": meta["summary"]["n_nodes"], "triangles": meta["summary"]["n_triangles"],
                     "symmetry_plane": "stored mesh", "seed_slide_mm": None}
        log(f"using stored mesh {mesh}")
    else:
        mesh, mesh_info = build_production_mesh()
    freqs = frequencies(args.grid_config)
    log(f"mesh {mesh_info['triangles']} tris / {mesh_info['dofs']} dofs "
        f"(seed slide {mesh_info['seed_slide_mm']} mm) | grid {len(freqs)} points "
        f"{freqs[0]:.0f}-{freqs[-1]:.0f} Hz")
    log(f"backends cuda={statuses['cuda']['state']} cpu={statuses['cpu']['state']}")

    results: dict[str, list[dict]] = {"cuda": [], "cpu": []}
    for backend in ("cuda", "cpu"):
        log(f"--- arm {backend} ---")
        kill_hosts()
        baseline = vram_mib()
        log(f"arm {backend} VRAM baseline {baseline} MiB")
        warm = one(mesh, freqs[0], backend)
        log(f"arm {backend} warm-up at {freqs[0]:.0f} Hz: "
            f"{warm['seconds']:.2f}s" + ("" if warm["ok"] else f" FAILED {warm.get('error','')[:120]}"))
        if not warm["ok"]:
            results[backend].append({"freq": freqs[0], "warmup": True, **warm})
        for freq in freqs:
            if time.monotonic() - T0 > args.max_seconds:
                log(f"budget reached before {backend} {freq:.0f} Hz")
                break
            r = one(mesh, freq, backend)
            results[backend].append({"freq": freq, **r})
            with open(RESULTS, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"backend": backend, "freq": freq, **r}) + "\n")
            if r["ok"]:
                log(f"{backend:4s} {freq:8.1f} Hz {r['seconds']:7.2f}s spl0={r['spl0']:8.3f}"
                    + (f" vram {r['peak_vram_mib']}" if backend == "cuda" else ""))
            else:
                log(f"{backend:4s} {freq:8.1f} Hz FAILED after {r['seconds']:.1f}s: "
                    f"{r.get('error','')[:200]}")
                break
        kill_hosts()

    # ---------- comparison ----------
    cu = {r["freq"]: r for r in results["cuda"] if r["ok"]}
    cp = {r["freq"]: r for r in results["cpu"] if r["ok"]}
    both = sorted(set(cu) & set(cp))
    deltas = [abs(cu[f]["spl0"] - cp[f]["spl0"]) for f in both]
    ratios = [cp[f]["seconds"] / cu[f]["seconds"] for f in both if cu[f]["seconds"] > 0]
    cu_fail = next((r for r in results["cuda"] if not r["ok"]), None)
    cp_fail = next((r for r in results["cpu"] if not r["ok"]), None)
    summary = {
        "mesh": mesh_info, "grid_points": len(freqs),
        "grid_hz": [freqs[0], freqs[-1]],
        "cuda_completed": len(cu), "cpu_completed": len(cp),
        "cuda_failed_at_hz": None if cu_fail is None else cu_fail["freq"],
        "cpu_failed_at_hz": None if cp_fail is None else cp_fail["freq"],
        "cuda_total_s": round(sum(r["seconds"] for r in results["cuda"]), 1),
        "cpu_total_s": round(sum(r["seconds"] for r in results["cpu"]), 1),
        "cuda_max_vram_mib": max((r.get("peak_vram_mib") or 0) for r in results["cuda"]) or None,
        "paired_frequencies": len(both),
        "spl_parity_abs_db": {"max": max(deltas), "median": float(np.median(deltas))} if deltas else None,
        "cpu_over_cuda": {"median": round(float(np.median(ratios)), 3),
                          "min": round(float(np.min(ratios)), 3),
                          "max": round(float(np.max(ratios)), 3)} if ratios else None,
        "elapsed_s": round(time.monotonic() - T0, 1),
        "budget_s": args.max_seconds, "log": str(LOG), "results": str(RESULTS),
    }
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    log("SUMMARY " + json.dumps({k: v for k, v in summary.items() if k not in ("log", "results")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
