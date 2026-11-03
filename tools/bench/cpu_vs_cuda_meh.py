"""CUDA vs CPU for the MEH (multi-entry) solve, and CPU high-resolution feasibility.

What this does NOT repeat (already measured, see TOOLCHAIN.md s"M4 cuda vs cpu" and
docs/evidence/MEH_M8_2026-10-31.md): single-source cuda-vs-cpu timings, the bempp cross-check,
and every MEH solve so far (CUDA only). The gap this fills is:
  A. can the BEAT CPU backend do a MULTI-TAG (radiators) solve at all, and what does it cost;
  B. the production MEH mesh (2 tags) solved on CPU vs CUDA at one frequency, SPL parity;
  C. whether a mesh that resolves 16 kHz (which the 8 GB card cannot hold) is solvable on CPU,
     and how long one frequency takes.

Hard wall-clock budget (default 900 s). Every step checks the remaining budget and skips rather
than overrunning; the log and the summary say exactly which steps completed. Logs land in
runs/bench_cpu_cuda_<UTC>/log.txt + summary.json.

Usage:  .venv\\Scripts\\python.exe tools\\bench\\cpu_vs_cuda_meh.py [--budget 900]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import hornlab_beat_bem as beat
from hornlab_beat_bem import ObservationConfig, SolveConfig
from hornlab_beat_bem.sweep import solve_frequencies

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "runs" / f"bench_cpu_cuda_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG = LOG_DIR / "log.txt"
SUMMARY = LOG_DIR / "summary.json"
T0 = time.monotonic()
BUDGET_S = 900.0
LOG_LINES: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.monotonic() - T0:7.1f}s] {msg}"
    LOG_LINES.append(line)
    print(line, flush=True)
    LOG.write_text("\n".join(LOG_LINES) + "\n", encoding="utf-8", newline="\n")


def remaining() -> float:
    return BUDGET_S - (time.monotonic() - T0)


def vram_used_mib() -> int | None:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"],
                         capture_output=True, text=True)
    try:
        return int("".join(ch for ch in out.stdout if ch.isdigit()))
    except ValueError:
        return None


class VramPeak:
    """Poll from a separate thread (CLAUDE.md rule 5)."""

    def __init__(self, period=2.0):
        self.period, self.peak, self._stop = period, vram_used_mib(), threading.Event()

    def __enter__(self):
        def loop():
            while not self._stop.is_set():
                v = vram_used_mib()
                if v is not None:
                    self.peak = max(self.peak, v)
                self._stop.wait(self.period)
        self._t = threading.Thread(target=loop, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()


def kill_hosts() -> None:
    """Clear BEAT hosts between arms; only julia carries our solves on this box."""
    subprocess.run(["taskkill", "/F", "/IM", "julia.exe"], capture_output=True)
    time.sleep(2)


def write_tetra(path: Path) -> Path:
    """Two driven faces (tags 2 and 10) of a regular tetrahedron - smallest 2-tag mesh."""
    s, h, z = 0.2, 0.2 * np.sqrt(3) / 2, 0.2 * np.sqrt(2 / 3)
    verts = [(0.0, 0.0, 0.0), (s, 0.0, 0.0), (s / 2, h, 0.0), (s / 2, h / 3, z)]
    faces = [((1, 3, 2), 1), ((1, 2, 4), 2), ((2, 3, 4), 10), ((3, 1, 4), 1)]
    with open(path, "w", encoding="ascii", newline="\n") as io:
        io.write("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n3\n")
        io.write('2 1 "wall"\n2 2 "entry"\n2 10 "entry_right"\n$EndPhysicalNames\n')
        io.write(f"$Nodes\n{len(verts)}\n")
        for k, v in enumerate(verts, 1):
            io.write(f"{k} {v[0]:.9f} {v[1]:.9f} {v[2]:.9f}\n")
        io.write(f"$EndElements\n" if False else "$EndNodes\n")
        io.write(f"$Elements\n{len(faces)}\n")
        for k, ((a, b, c), tag) in enumerate(faces, 1):
            io.write(f"{k} 2 2 {tag} {tag} {a} {b} {c}\n")
        io.write("$EndElements\n")
    return path


def observation() -> ObservationConfig:
    return ObservationConfig(distance_m=2.0, angle_count=37, planes=["horizontal", "vertical"])


def solve(mesh: Path, freqs, *, backend: str, tags, balloon=True):
    cfg = SolveConfig(
        velocity_sources={t: 1.0 for t in tags},
        impedance_matrix=True,
        beat_backend=backend,
        observation=observation(),
    )
    t0 = time.perf_counter()
    with VramPeak() as peak:
        result = solve_frequencies(str(mesh), list(freqs), cfg)
    return result, time.perf_counter() - t0, peak.peak


def spl_delta(a, b) -> float:
    sa, sb = np.asarray(a.spl_db), np.asarray(b.spl_db)
    return float(np.nanmax(np.abs(sa - sb)))


def build_meh(epw: float, f_max: float, out: Path, cap: int = 8900):
    """Build the T2 seed quarter mesh via the app's own route (no solve).

    ``cap`` is the app's dof ceiling - a SETTING, not a hardware limit. The high-resolution arm
    raises it to size the mesh that the 8 GB card cannot hold.
    """
    from hornlab_search.config import load_config
    from hornlab_search.mesh import sizing, step_build
    from hornlab_search.types import MeshSpec

    tool = step_build.load_cad_tool(tool=step_build.MEH_TOOL)
    recipe = {"tool": step_build.MEH_TOOL, **tool.defaults()}
    cfg = load_config(ROOT / "examples" / "typologies" / "multicell_3x3.yaml")
    # the cap that step_build enforces is the CONFIG's, so raise it for the diagnostic arm too
    cfg.mesh.dof_cap_screen = int(cap)
    cfg.mesh.dof_cap_verify = int(cap)
    cfg.mesh.dof_cap_final = int(cap)
    max_tri = sizing.max_triangles_for(cap, "1", 0.51, 1.15)
    spec = MeshSpec(epw=epw, f_max_hz=f_max, quadrants="1", max_triangles=max_tri,
                    allow_large_mesh=True)
    t0 = time.perf_counter()
    res = step_build.build_mesh_from_cad(recipe, spec, cfg, out, mode="final")
    return res, time.perf_counter() - t0


def main() -> int:
    global BUDGET_S
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=900.0, help="hard wall-clock budget, seconds")
    args = ap.parse_args()
    BUDGET_S = float(args.budget)

    statuses = beat.beat_backend_statuses()
    log(f"log: {LOG}")
    log(f"backend cuda: {statuses['cuda']['state']} | cpu: {statuses['cpu']['state']}")
    if statuses["cpu"]["state"] != "ready":
        log("CPU backend is not ready - run: python -m hornlab_beat_bem.provision --backend cpu")
        return 2
    summary: dict = {"budget_s": BUDGET_S, "started_utc": datetime.now(timezone.utc).isoformat(),
                     "backend_status": {k: v["state"] for k, v in statuses.items()}, "steps": {}}

    # ---------- A. does the CPU backend support multi-tag at all? ---------------------
    log("A: multi-tag capability probe (2 tags, tetrahedron, 1 kHz)")
    tetra = write_tetra(LOG_DIR / "tetra_2tag.msh")
    kill_hosts()
    try:
        res, dt, peak = solve(tetra, [1000.0], backend="cpu", tags=(2, 10))
        log(f"A: CPU multi-tag OK in {dt:.1f}s | SPL shape {np.asarray(res.spl_db).shape} "
            f"| tags {res.channel_tags} | VRAM(host) {peak} MiB")
        summary["steps"]["A_cpu_multitag"] = {"ok": True, "seconds": round(dt, 2),
                                              "channel_tags": list(res.channel_tags)}
        cpu_multitag = True
    except Exception as exc:  # noqa: BLE001 - a refusal is the finding
        log(f"A: CPU multi-tag REFUSED: {type(exc).__name__}: {str(exc)[:300]}")
        summary["steps"]["A_cpu_multitag"] = {"ok": False, "error": str(exc)[:600]}
        cpu_multitag = False
    kill_hosts()

    # ---------- B. production MEH mesh, 2 tags, 1 kHz: CUDA then CPU -----------
    if remaining() > 240:
        log("B: building the production T2 mesh (epw 4.05, 12 kHz request)")
        mesh_dir = LOG_DIR / "meh12k"
        try:
            res_mesh, mesh_s = build_meh(4.05, 12_000.0, mesh_dir)
            meta = json.loads((mesh_dir / "mesh_meta.json").read_text(encoding="utf-8"))
            dofs = meta["summary"]["n_nodes"]
            log(f"B: mesh {meta['summary']['n_triangles']} tris / {dofs} dofs in {mesh_s:.1f}s "
                f"| planes {res_mesh.symmetry_plane}")
            summary["steps"]["B_mesh"] = {"dofs": dofs, "triangles": meta["summary"]["n_triangles"],
                                          "seconds": round(mesh_s, 2),
                                          "symmetry_plane": res_mesh.symmetry_plane}
            kill_hosts()
            freqs = [1000.0, 5000.0]
            log("B: CUDA, 2 tags: one warm-up call, then the same 2-frequency call TWICE "
                "(the second is the warm rate; a two-call subtraction is invalid when call 1 absorbs startup)")
            cu1, cu_t1, cu_p1 = solve(res_mesh.path, [freqs[0]], backend="cuda", tags=(2, 10))
            cuA, cu_tA, _ = solve(res_mesh.path, freqs, backend="cuda", tags=(2, 10))
            cu, cu_tB, cu_p2 = solve(res_mesh.path, freqs, backend="cuda", tags=(2, 10))
            cu_warm = cu_tB / len(freqs)
            log(f"B: CUDA warm-up {cu_t1:.1f}s, repeat A {cu_tA:.1f}s, repeat B {cu_tB:.1f}s "
                f"-> warm {cu_warm:.2f}s/freq")
            log(f"B: CUDA peak VRAM {max(cu_p1, cu_p2)} MiB | tags {cu.channel_tags}")
            summary["steps"]["B_cuda"] = {"warmup_s": round(cu_t1, 2), "repeat_a_s": round(cu_tA, 2),
                                          "repeat_b_s": round(cu_tB, 2),
                                          "warm_per_freq_s": round(cu_warm, 2),
                                          "peak_vram_mib": max(cu_p1, cu_p2)}
            kill_hosts()
            if cpu_multitag and remaining() > 120:
                log("B: CPU, same mesh and tags, same two-call shape (budget-capped)")
                try:
                    cpu1, cpu_t1, _ = solve(res_mesh.path, [freqs[0]], backend="cpu", tags=(2, 10))
                    cpuA, cpu_tA, _ = solve(res_mesh.path, freqs, backend="cpu", tags=(2, 10))
                    cpu_res, cpu_tB, _ = solve(res_mesh.path, freqs, backend="cpu", tags=(2, 10))
                    cpu_warm = cpu_tB / len(freqs)
                    log(f"B: CPU warm-up {cpu_t1:.1f}s, repeat A {cpu_tA:.1f}s, repeat B {cpu_tB:.1f}s "
                        f"-> warm {cpu_warm:.2f}s/freq")
                    log(f"B: warm CPU/CUDA ratio {cpu_warm / cu_warm:.2f}x | "
                        f"SPL |dCUDA-CPU| {spl_delta(cu, cpu_res):.4e} dB")
                    summary["steps"]["B_cpu"] = {"warmup_s": round(cpu_t1, 2),
                                                 "repeat_a_s": round(cpu_tA, 2),
                                                 "repeat_b_s": round(cpu_tB, 2),
                                                 "warm_per_freq_s": round(cpu_warm, 2),
                                                 "warm_ratio_vs_cuda": round(cpu_warm / cu_warm, 2),
                                                 "spl_max_abs_delta_db": spl_delta(cu, cpu_res)}
                except Exception as exc:  # noqa: BLE001
                    log(f"B: CPU arm failed/limited: {type(exc).__name__}: {str(exc)[:300]}")
                    summary["steps"]["B_cpu"] = {"error": str(exc)[:600]}
                kill_hosts()
            else:
                log("B: CPU arm skipped (capability or budget)")
        except Exception as exc:  # noqa: BLE001
            log(f"B: failed: {type(exc).__name__}: {str(exc)[:400]}")
            summary["steps"]["B_mesh"] = {"error": str(exc)[:600]}
    else:
        log("B: skipped (budget)")

    # ---------- C. 16 kHz mesh on CPU (the CUDA card cannot hold it) -----------
    if remaining() > 120:
        log("C: 16 kHz mesh - find the smallest epw the validator accepts, then one CPU frequency")
        for epw in (5.4, 5.6, 5.8, 6.0):
            if remaining() < 90:
                log("C: budget exhausted before a passing mesh")
                break
            out = LOG_DIR / f"meh16k_epw{epw}"
            try:
                res16, s16 = build_meh(epw, 16_000.0, out, cap=45_000)
                m16 = json.loads((out / "mesh_meta.json").read_text(encoding="utf-8"))
                dofs16 = m16["summary"]["n_nodes"]
                log(f"C: epw {epw} PASSES at 16 kHz (cap {45_000}): {m16['summary']['n_triangles']} tris / "
                    f"{dofs16} dofs in {s16:.1f}s")
                summary["steps"]["C_mesh_16k"] = {"epw": epw, "dofs": dofs16,
                                                  "triangles": m16["summary"]["n_triangles"],
                                                  "seconds": round(s16, 2)}
                kill_hosts()
                if cpu_multitag and remaining() > 60:
                    log(f"C: CPU solve at 16 kHz, 1 kHz, 2 tags (cap {min(remaining() - 40, 420):.0f}s)")
                    c16, c16_dt, c16_peak = solve(res16.path, [1000.0], backend="cpu", tags=(2, 10))
                    log(f"C: CPU 16 kHz solved in {c16_dt:.1f}s | SPL shape "
                        f"{np.asarray(c16.spl_db).shape}")
                    summary["steps"]["C_cpu_16k"] = {"seconds": round(c16_dt, 2)}
                else:
                    log("C: CPU 16 kHz solve skipped (capability/budget)")
                break
            except Exception as exc:  # noqa: BLE001 - the validator refusing is information
                log(f"C: epw {epw} refused: {str(exc)[:200]}")
                summary["steps"].setdefault("C_refused_epw", []).append({"epw": epw, "error": str(exc)[:300]})
    else:
        log("C: skipped (budget)")

    log(f"done in {time.monotonic() - T0:.1f}s (budget {BUDGET_S:.0f}s)")
    summary["elapsed_s"] = round(time.monotonic() - T0, 1)
    summary["log"] = str(LOG)
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    log(f"summary: {SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
