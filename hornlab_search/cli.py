"""Command-line entry point (owned by task 08 since Wave 2; task 03 wrote doctor and version).

    hornlab-search doctor | version
    hornlab-search selftest --analytic [--tol-db 0.5] [--subdivisions 3] | --crosscheck
    hornlab-search run      --config <yaml> [--mode screen|verify|final] [--dry-run]
    hornlab-search search   --config <yaml> [--budget N] [--mode screen] [--resume DIR]
    hornlab-search verify   --run <dir> [--top 5]
    hornlab-search report   <run_dir> [--out report.html] [--top 5]
    hornlab-search pin-plan --run <dir|id> [--write-config PATH]
    hornlab-search dataset  stats|verify|export
    hornlab-search compare  <run_a> <run_b>       (report metric differences, e.g. full vs quarter)

Every command exits 0 or 1 and prints one clear final line saying what happened and where the
output is (argparse usage errors exit 2). Heavy imports are lazy so doctor/version stay cheap.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples"
TOOLCHAIN_MD = REPO / "TOOLCHAIN.md"

EXAMPLE_NAMES = ("osse_baseline", "throat_adapter", "icw_termination",
                 "freeform_hv", "search_smoke")

CORE_IMPORTS = ("numpy", "scipy", "cma", "yaml", "jinja2")
HORNLAB_IMPORTS = ("hornlab_mesher", "hornlab_beat_bem", "hornlab_plots")

# pyproject dependency git SHAs: package name -> 40-char commit. Any git URL is accepted (Magnus's
# upstream, a GitHub fork, or a local file:// fork; docs/FORKS.md), keyed by the dependency name.
_GIT_URL_RE = re.compile(
    r"(hornlab-(?:waveguide-mesher|beat-bem|plots|bempp-bem))\s*@\s*git\+[^\s\"']+@([0-9a-f]{40})")


def _have(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _version() -> str:
    from hornlab_search import __version__
    return __version__


def _expected_shas() -> dict[str, str]:
    """{package name -> 40-char SHA} parsed from pyproject.toml dependencies."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = _GIT_URL_RE.search(line)
        if m:
            repo, sha = m.group(1), m.group(2)
            out[repo] = sha
    return out


def _installed_shas() -> dict[str, str]:
    """{package name -> installed commit SHA} from each dist's direct_url.json.

    Returns "" for a package whose commit cannot be determined (editable checkouts,
    non-git installs)."""
    out: dict[str, str] = {}
    for repo in ("hornlab-waveguide-mesher", "hornlab-beat-bem",
                 "hornlab-plots", "hornlab-bempp-bem"):
        name = repo.replace("hornlab-", "hornlab_")
        try:
            dist = distribution(name)
        except PackageNotFoundError:
            out[repo] = ""
            continue
        raw = dist.read_text("direct_url.json")
        sha = ""
        if raw:
            try:
                data = json.loads(raw)
                vcs = data.get("vcs_info") or {}
                sha = vcs.get("commit_id") or data.get("commit_id") or ""
            except (ValueError, TypeError):
                sha = ""
        out[repo] = sha
    return out


def _python_ok() -> tuple[bool, str]:
    v = sys.version_info
    if (3, 11) <= (v.major, v.minor) < (3, 14):
        return True, f"Python {v.major}.{v.minor}.{v.micro} in [3.11, 3.14)"
    return False, f"Python {v.major}.{v.minor}.{v.micro} outside [3.11, 3.14)"


def _backend_status():
    try:
        import hornlab_beat_bem as beat
        return beat.beat_backend_statuses()
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"__error__": str(exc)}


def _configured_backend() -> tuple[str, str]:
    """(configured backend token, bare backend name) from osse_baseline.yaml."""
    from hornlab_search.config import load_config
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    token = cfg.solve.backend            # e.g. "beat_cuda"
    bare = token.removeprefix("beat_") if token.startswith("beat_") else token
    return token, bare


class Doctor:
    """One check at a time; each returns (ok, reason)."""

    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def run(self, label: str, fn):
        ok = True
        reason = ""
        try:
            ok, reason = fn()
        except Exception as exc:  # noqa: BLE001 - a doctor must never crash
            ok, reason = False, f"unexpected error: {exc!r}"
        self.results.append((label, ok, reason))

    def check_python(self):
        self.run("python-version", _python_ok)

    def check_core_imports(self):
        missing = [m for m in CORE_IMPORTS if not _have(m)]
        if missing:
            self.run("core-imports", lambda: (False, f"missing: {', '.join(missing)}"))
        else:
            self.run("core-imports", lambda: (True, "numpy, scipy, cma, yaml, jinja2"))

    def check_hornlab_imports(self):
        missing = [m for m in HORNLAB_IMPORTS if not _have(m)]
        bempp = "yes" if _have("hornlab_bempp_bem") else "no (optional)"
        if missing:
            self.run("hornlab-imports", lambda: (False, f"missing: {', '.join(missing)}; bempp {bempp}"))
        else:
            self.run("hornlab-imports", lambda: (True, f"mesher, beat, plots; bempp {bempp}"))

    def check_shas(self):
        expected = _expected_shas()
        installed = _installed_shas()
        problems = []
        for repo, want in expected.items():
            got = installed.get(repo, "")
            if not got:
                problems.append(f"{repo}: installed SHA UNKNOWN (expected {want[:12]})")
            elif got != want:
                problems.append(f"{repo}: installed {got[:12]} != expected {want[:12]}")
        if problems:
            # Mismatch is a WARNING, not a failure (03 step 7).
            self.results.append(("pinned-shas", True, "WARNING: " + "; ".join(problems)))
        else:
            self.results.append(("pinned-shas", True, "all installed SHAs match pyproject.toml"))

    def check_toolchain(self):
        def fn():
            if not TOOLCHAIN_MD.exists():
                return False, "TOOLCHAIN.md missing"
            text = TOOLCHAIN_MD.read_text(encoding="utf-8")
            m = re.search(r"dof_per_triangle\s*[:=]\s*([0-9.]+)", text)
            if not m:
                return False, "TOOLCHAIN.md has no dof_per_triangle value"
            if float(m.group(1)) == 0.5:
                return False, "dof_per_triangle is still the 0.5 placeholder"
            return True, f"TOOLCHAIN.md present, dof_per_triangle={m.group(1)}"
        self.run("toolchain", fn)

    def check_gpu(self):
        def fn():
            nv = shutil.which("nvidia-smi")
            if not nv:
                return False, "nvidia-smi not on PATH"
            r = subprocess.run([nv], capture_output=True, timeout=30)
            if r.returncode == 0:
                return True, "nvidia-smi exits 0"
            return False, f"nvidia-smi exits {r.returncode}"
        self.run("gpu", fn)

    def check_backend(self):
        def fn():
            token, bare = _configured_backend()
            statuses = _backend_status()
            entry = statuses.get(bare)
            if not isinstance(entry, dict):
                return False, f"backend {bare!r} not in statuses: {list(statuses)}"
            if entry.get("available"):
                return True, f"{token} functional (state={entry.get('state')})"
            return False, f"{token} not functional: {entry.get('reason', entry)}"
        self.run("backend", fn)

    def check_configs(self):
        def fn():
            from hornlab_search.config import load_config
            bad = []
            for name in EXAMPLE_NAMES:
                try:
                    load_config(EXAMPLES / f"{name}.yaml")
                except Exception as exc:  # noqa: BLE001
                    bad.append(f"{name}: {exc}")
            if bad:
                return False, "; ".join(bad)
            return True, f"all {len(EXAMPLE_NAMES)} example configs load"
        self.run("configs", fn)

    def check_roundtrip(self):
        """Mesh round trip: mesh the seed design small, read the .msh back, check units, the
        source tag and the quadrants <-> symmetry-flag pairing (silent killers 1 and 2)."""
        def fn():
            if not _have("hornlab_mesher"):
                return False, "hornlab_mesher not importable"
            import tempfile
            from hornlab_search.config import load_config
            from hornlab_search.design.space import DesignSpace
            from hornlab_search.mesh import build, sizing
            from hornlab_search.types import MeshSpec
            cfg = load_config(EXAMPLES / "osse_baseline.yaml")
            design = DesignSpace.from_config(cfg).seed
            spec = MeshSpec(epw=cfg.mesh.epw, f_max_hz=1500.0, quadrants=cfg.mesh.quadrants,
                            max_triangles=10 ** 6)
            with tempfile.TemporaryDirectory(prefix="hs-doctor-") as td:
                m = build.build_mesh(design, spec, cfg, Path(td), mode="final")
                s = build.read_msh_summary(Path(m.path))
            ext = max(m.bbox_m[3] - m.bbox_m[0], m.bbox_m[4] - m.bbox_m[1], m.bbox_m[5] - m.bbox_m[2])
            want = sizing.SYMMETRY_PLANE[cfg.mesh.quadrants]
            if m.symmetry_plane != want:
                return False, f"symmetry flag {m.symmetry_plane!r} != {want!r}"
            if s["tags"].get(2, 0) <= 0:
                return False, f"no triangles on source tag 2: {s['tags']}"
            return True, (f"seed meshed at 1.5 kHz: {s['n_triangles']} tris, {s['n_nodes_used']} nodes, "
                          f"largest extent {ext:.3f} m (metres), source tag 2 present, "
                          f"quadrants {m.quadrants!r} <-> symmetry {m.symmetry_plane!r}")
        self.run("round-trip", fn)

    def check_gpu_hygiene(self):
        """Informational: stale BEAT hosts and VRAM baseline (AGENTS.md GPU / Julia hygiene)."""
        def fn():
            from hornlab_search.solve import worker
            hosts = worker.list_beat_hosts()
            vram = worker.vram_used_mib()
            txt = f"{len(hosts)} BEAT host(s) alive, VRAM used {vram if vram is not None else 'n/a'} MiB"
            if hosts or (vram is not None and vram > 1000):
                txt = "WARNING: " + txt + " (a search starts by clearing stale hosts)"
            return True, txt
        self.run("gpu-hygiene", fn)


    def check_disk_space(self):
        """Report free GB for the drives holding runs/, cache/, dataset/."""
        def fn():
            import shutil as _shutil
            dirs = {
                "runs": REPO / "runs",
                "cache": REPO / "cache",
                "dataset": REPO / "dataset",
            }
            seen: dict[str, float] = {}  # device root -> free GB
            msgs: list[str] = []
            warn = False
            for name, d in dirs.items():
                d.mkdir(parents=True, exist_ok=True)
                usage = _shutil.disk_usage(d)
                free_gb = usage.free / 1e9
                # Identify the drive root (Windows: drive letter, POSIX: mountpoint approximation)
                drive = Path(d).anchor
                if drive in seen:
                    continue
                seen[drive] = free_gb
                tag = "WARNING: " if free_gb < 10 else ""
                msgs.append(f"{tag}{name}({drive}) {free_gb:.1f} GB free")
                if free_gb < 10:
                    warn = True
            detail = "; ".join(msgs)
            return True, detail
        self.run("disk-space", fn)


def _cmd_doctor() -> int:
    d = Doctor()
    d.check_python()
    d.check_core_imports()
    d.check_hornlab_imports()
    d.check_shas()
    d.check_toolchain()
    d.check_gpu()
    d.check_backend()
    d.check_configs()
    d.check_roundtrip()
    d.check_gpu_hygiene()
    d.check_disk_space()
    any_fail = False
    for label, ok, reason in d.results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            any_fail = True
        print(f"{mark:4}  {label:16}  {reason}")
    n_bad = sum(1 for _, ok, _ in d.results if not ok)
    print(f"doctor {'FAILED' if any_fail else 'OK'}: {len(d.results)} checks, {n_bad} failed")
    return 1 if any_fail else 0


def _cmd_version() -> int:
    print(_version())
    return 0




# ====================================================================== Wave 2 (task 08)

import argparse
import logging
import math

log = logging.getLogger("hornlab_search.cli")

#: Warm per-frequency solve cost versus dofs, quarter-domain meshes, one call per frequency, RTX 4060
#: Laptop 8 GB (TOOLCHAIN.md M3). Used only by ``run --dry-run`` to estimate wall time; the real
#: numbers come from run.json after a run.
COST_CURVE_DOFS_S = ((2369, 0.4), (5140, 2.8), (7001, 7.5), (8941, 45.0))
COLD_START_S = 30.0


def estimate_seconds_per_frequency(n_dof: float) -> float:
    """Log-log interpolation (and extrapolation) of TOOLCHAIN M3's per-frequency cost."""
    xs = [math.log(d) for d, _ in COST_CURVE_DOFS_S]
    ys = [math.log(t) for _, t in COST_CURVE_DOFS_S]
    x = math.log(max(float(n_dof), 1.0))
    if x <= xs[0]:
        i = 0
    elif x >= xs[-1]:
        i = len(xs) - 2
    else:
        i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
    slope = (ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i])
    return math.exp(ys[i] + slope * (x - xs[i]))


def _setup_logging(verbose: int) -> None:
    level = logging.WARNING if verbose <= 0 else (logging.INFO if verbose == 1 else logging.DEBUG)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                        datefmt="%H:%M:%S", force=True)
    logging.getLogger("matplotlib").setLevel(logging.ERROR)


def _dirs(args) -> dict:
    return {"runs": Path(args.runs_dir or REPO / "runs"), "cache": Path(args.cache_dir or REPO / "cache"),
            "dataset": Path(args.dataset_dir or REPO / "dataset")}


def _load_cfg(args):
    from hornlab_search.config import load_config
    kwargs = {}
    brief = getattr(args, "brief", None)
    cma_seed = getattr(args, "cma_seed", None)
    if brief is not None:
        kwargs["brief"] = Path(brief)
    if cma_seed is not None:
        kwargs["cma_seed"] = int(cma_seed)
    backend = getattr(args, "backend", None)
    if backend is not None:
        kwargs["backend"] = backend
    return load_config(args.config, **kwargs)


def _command_string(argv) -> str:
    return "hornlab-search " + " ".join(argv)


def _apply_restarts_cli(cfg, mode, max_n) -> None:
    """Apply ``--restarts-mode`` / ``--restarts-max`` onto a loaded Config (mutates in place).

    Absent both flags: leave ``cfg.search.restarts`` alone (config YAML wins).
    ``mode='off'``: clear restarts (single CMA-ES), ignoring max.
    ``mode`` in {ipop,bipop}: set ``{mode, max}``; max defaults to the config's existing max,
    else 2. Updates ``cfg.raw['search']`` so the run snapshot / config_sha match what ran.
    Refuses when ``search.algorithm`` is ``cma_me`` (same rule as config validation).
    """
    from hornlab_search.config import ConfigError, _validate_restarts

    if mode is None and max_n is None:
        return
    if str(getattr(cfg.search, "algorithm", "cma")) == "cma_me":
        raise ConfigError("search.restarts is not supported with search.algorithm: cma_me "
                          "(CLI --restarts-* refused)")
    raw_search = cfg.raw.setdefault("search", {})
    if not isinstance(raw_search, dict):
        raise ConfigError("config search block must be a mapping to apply --restarts-*")
    if mode in ("off", "none"):
        if max_n is not None:
            raise ConfigError("--restarts-max is meaningless with --restarts-mode off")
        cfg.search.restarts = None
        raw_search.pop("restarts", None)
        return
    if mode is None:
        raise ConfigError("--restarts-max requires --restarts-mode ipop|bipop|off")
    existing = getattr(cfg.search, "restarts", None) or {}
    if max_n is None:
        max_n = int(existing["max"]) if isinstance(existing, dict) and "max" in existing else 2
    block = _validate_restarts({"mode": mode, "max": int(max_n)}, "cli:--restarts")
    cfg.search.restarts = block
    raw_search["restarts"] = dict(block)


def _backend(cfg):
    from hornlab_search.solve.base import get_backend
    kw = {"timeout_s": float(cfg.solve.timeout_s)}
    # WP15 cuda_fused is CUDA-only; never pass it for metal/cpu (BeatBackend refuses otherwise).
    if str(cfg.solve.backend) == "beat_cuda":
        kw["cuda_fused"] = bool(getattr(cfg.solve, "cuda_fused", False))
    return get_backend(cfg.solve.backend, **kw)


def _print_terms(ev) -> None:
    from hornlab_search.objective import WEIGHTED_KEYS
    t = ev.terms
    print("  terms (raw): " + "  ".join(f"{k}={t.get(k, 0.0):.4g}" for k in WEIGHTED_KEYS)
          + f"  penalty={t.get('penalty', 0.0):.4g}  total J={ev.objective:.6g}"
          + f"  n_nan={t.get('n_nan', 0)}  DI source={ev.metrics.di_source if ev.metrics else 'n/a'}")


# ---------------------------------------------------------------------- gpu-clean


def _cmd_gpu_clean(args) -> int:
    from hornlab_search.search import hygiene
    from hornlab_search.search.gpulock import GpuBusyError, _lock_path, _pid_alive, _read_lock
    import os

    d = _dirs(args) if hasattr(args, "runs_dir") else {"runs": REPO / "runs"}
    runs_root = d["runs"]
    lock_path = _lock_path(runs_root)

    # Check if GPU lock is held by a live other process
    if not getattr(args, "force", False):
        lock_data = _read_lock(lock_path)
        if lock_data:
            holder_pid = lock_data.get("pid")
            my_pid = os.getpid()
            if holder_pid and holder_pid != my_pid and _pid_alive(holder_pid):
                user = lock_data.get("user", "?")
                cmd = lock_data.get("command", "?")
                start = lock_data.get("start_time", "?")
                print(
                    f'GPU busy: {user} running "{cmd}" (pid {holder_pid}) since {start}',
                    file=sys.stderr,
                )
                return 3

    procs = hygiene.list_project_julia()
    killed = hygiene.clear_julia(procs)
    if killed:
        print(f"gpu-clean: killed {len(killed)} process(es): {killed}")
    else:
        print("gpu-clean: no project Julia/BEAT processes found")

    vram = hygiene.vram_used_mib()
    if vram is None:
        print("gpu-clean: nvidia-smi not available (VRAM usage unknown)")
    else:
        print(f"gpu-clean: VRAM used {vram:.0f} MiB")
    return 0


# ---------------------------------------------------------------------- selftest


def _cmd_selftest(args) -> int:
    from hornlab_search.config import load_config
    from hornlab_search.search import selftest
    from hornlab_search.search.gpulock import GpuBusyError, gpu_lock
    from hornlab_search.solve import worker
    cfg = load_config(args.config or EXAMPLES / "osse_baseline.yaml",
                      backend=getattr(args, "backend", None))
    worker.install_handlers()
    d = _dirs(args) if hasattr(args, "runs_dir") else {"runs": REPO / "runs"}
    entered_locked_body = False
    try:
        with gpu_lock(_command_string(["selftest"] + sys.argv[1:]), runs_root=d["runs"]):
            entered_locked_body = True
            return _selftest_body(args, cfg, selftest)
    except GpuBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    finally:
        # A self-test is a measurement: leave no Julia host holding VRAM behind it (AGENTS.md rule
        # 6) - but ONLY when this process actually entered the locked body. A GpuBusyError refusal
        # means the lock was never acquired and this process started no worker: calling
        # worker.shutdown() there would force-kill BEAT hosts belonging to the live job that holds
        # the lock (observed 2026-10-25: a lock-refused selftest killed another campaign's host).
        if entered_locked_body:
            try:
                worker.shutdown(verify=True)
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: could not verify the BEAT host is gone: {exc}")


def _selftest_body(args, cfg, selftest) -> int:
    if args.analytic:
        levels = () if args.no_convergence else tuple(int(v) for v in args.convergence.split(","))
        res = selftest.run_analytic(cfg, tol_db=args.tol_db, subdivisions=args.subdivisions,
                                    convergence_levels=levels)
        print(selftest.format_analytic(res))
        ok = bool(res["passed"])
        print(f"selftest --analytic: {'PASS' if ok else 'FAIL'} (R(ka) spread {res['r_spread_db']:.3f} dB "
              f"vs {args.tol_db} dB; convergence monotone: {res['convergence']['monotone_decreasing']})")
        return 0 if ok else 1
    res = selftest.run_crosscheck(cfg, n_freqs=args.n_freqs)
    print(selftest.format_crosscheck(res))
    if not res.get("available", False):
        print("selftest --crosscheck: NOT RUN (" + str(res.get("reason", "")) + ")")
        return 1
    print(f"selftest --crosscheck: done, overall max normalized difference {res['overall_max_db']:.4f} dB")
    return 0


# ---------------------------------------------------------------------- run


def _dry_run(cfg, mode: str) -> int:
    from hornlab_search.config import mesh_spec, solve_spec
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.mesh import build, sizing
    import tempfile
    space = DesignSpace.from_config(cfg)
    mspec, sspec = mesh_spec(mode, cfg), solve_spec(mode, cfg)
    cap = cfg.mesh.dof_cap(mode)
    with tempfile.TemporaryDirectory(prefix="hs-dry-") as td:
        try:
            m = build.build_mesh(space.seed, mspec, cfg, Path(td), mode=mode)
        except Exception as exc:  # noqa: BLE001
            print(f"dry-run FAILED: seed cannot be meshed in {mode} mode: {type(exc).__name__}: {exc}")
            return 1
        s = build.read_msh_summary(Path(m.path))
    n_dof = s["n_nodes_used"]
    nf = len(sspec.freqs_hz)
    per_f = estimate_seconds_per_frequency(n_dof)
    per_cand = nf * per_f + m.seconds
    print(f"dry-run [{mode}] {cfg.name}: mesh {m.n_triangles} triangles, {n_dof} dofs "
          f"(estimate {sizing.estimate_dofs(m.n_triangles, m.quadrants, cfg.mesh.dof_per_triangle)}, "
          f"cap {cap}), quadrants {m.quadrants!r} <-> symmetry {m.symmetry_plane!r}")
    print(f"  mesh built in {m.seconds:.1f} s; f_max {mspec.f_max_hz:g} Hz at epw {mspec.epw:g}; "
          f"res_mm {m.res_mm}; bbox_m {tuple(round(v, 4) for v in m.bbox_m)}")
    print(f"  {nf} frequencies {sspec.freqs_hz[0]:g}..{sspec.freqs_hz[-1]:g} Hz, "
          f"{sspec.observation.angle_count}-angle cuts, balloon {sspec.observation.balloon_points} points")
    print(f"  estimated solve {per_f:.1f} s per frequency -> {per_cand:.0f} s per candidate "
          f"({3600 / per_cand:.0f} candidates/hour); a {cfg.search.budget}-evaluation search = "
          f"{cfg.search.budget * per_cand / 60:.0f} min plus a {COLD_START_S:.0f} s cold start "
          f"(estimate from TOOLCHAIN M3, not a measurement of this design)")
    print(f"dry-run OK: no solver was launched (mode {mode}, {n_dof} of {cap} dofs)")
    return 0


def _verify_only_refusal(brief: dict | None, command: str) -> str | None:
    """A brief marked ``verify_only`` (the 12 kHz briefs, NEXT_DEV_PRIORITIES P2) exceeds what a search can
    mesh on the 8 GB card; only ``verify --brief`` may use it."""
    if brief and brief.get("verify_only"):
        return (f"{command} REFUSED: brief {brief.get('name')!r} is verify_only (its band exceeds what a search "
                f"can solve on this GPU). Use it with `verify --run <run> --brief <file>` only.")
    return None


def _verify_only_precheck(args, command: str) -> int | None:
    """Ordering (senior pass 2026-10-24, WP2): a verify_only brief passed as ``--brief`` is refused
    BEFORE the config is loaded, so the shipped exit-2 contract for the 12 kHz briefs wins even
    when the WP2 driver pins would also reject the config/brief pair. A malformed brief path is
    not pre-checked here; load_config's own loader reports it with its full message."""
    from hornlab_search.config import load_brief
    brief_path = getattr(args, "brief", None)
    if not brief_path:
        return None
    try:
        b = load_brief(brief_path)
    except Exception:
        return None
    why = _verify_only_refusal(b, command)
    if why:
        print(why)
        return 2
    return None


def _cmd_run(args, argv) -> int:
    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.search import cma, rundir
    from hornlab_search.search.gpulock import GpuBusyError, gpu_lock
    from hornlab_search.solve import worker
    from hornlab_search.types import BackendUnavailableError
    pre = _verify_only_precheck(args, "run")            # WP2 ordering: BEFORE config validation
    if pre is not None:
        return pre
    cfg = _load_cfg(args)
    worker.install_handlers()
    if args.dry_run:
        return _dry_run(cfg, args.mode)
    why = _verify_only_refusal(cfg.brief, "run")
    if why:
        print(why)
        return 2
    d = _dirs(args)
    try:
        with gpu_lock(_command_string(argv), runs_root=d["runs"]):
            return _run_body(args, argv, cfg)
    except GpuBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 3


def _run_body(args, argv, cfg) -> int:
    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.search import cma, rundir
    from hornlab_search.solve import worker
    from hornlab_search.types import BackendUnavailableError
    d = _dirs(args)
    try:
        backend = _backend(cfg)
    except BackendUnavailableError as exc:
        print(f"run FAILED: {exc}")
        return 1
    store = DatasetStore(d["dataset"])
    run_dir = rundir.new_run_dir(d["runs"], args.mode)
    worker.warm(backend)
    ev = cma.run_once(cfg, run_dir, args.mode, backend=backend, store=store, cache_dir=d["cache"],
                      trace_fraction=args.trace_fraction, command=_command_string(argv),
                      config_path=args.config)
    _print_terms(ev)
    if ev.error:
        print(f"run FAILED: {ev.error.splitlines()[0][:200]} (output: {run_dir})")
        return 1
    secs = ev.outcome.seconds if ev.outcome else float("nan")
    print(f"run OK: seed J={ev.objective:.6g}, {ev.mesh.n_dof} dofs, solve {secs:.1f} s; output {run_dir}")
    return 0


# ---------------------------------------------------------------------- search


def _cmd_search(args, argv) -> int:
    from hornlab_search.config import load_config
    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.search import cma, rundir
    from hornlab_search.search.evaluate import read_ndjson
    from hornlab_search.search.gpulock import GpuBusyError, gpu_lock
    from hornlab_search.solve import worker
    from hornlab_search.types import BackendUnavailableError
    d = _dirs(args)
    try:
        with gpu_lock(_command_string(argv), runs_root=d["runs"]):
            return _search_body(args, argv, d)
    except GpuBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 3


def _search_body(args, argv, d) -> int:
    from hornlab_search.config import load_config
    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.search import cma, rundir
    from hornlab_search.search.evaluate import read_ndjson
    from hornlab_search.solve import worker
    from hornlab_search.types import BackendUnavailableError
    pre = _verify_only_precheck(args, "search")         # WP2 ordering: BEFORE config validation
    if pre is not None:
        return pre
    if args.resume:
        run_dir = Path(args.resume)
        if not run_dir.is_dir():
            print(f"search FAILED: --resume {run_dir} is not a directory")
            return 1
        cfg_path = args.config or run_dir / "config.yaml"
    else:
        if not args.config:
            print("search FAILED: --config is required (or --resume DIR)")
            return 2
        cfg_path = args.config
        run_dir = rundir.new_run_dir(d["runs"], args.mode)
    # --brief / --cma-seed must reach the search exactly as they reach `run` (found 2026-10-22: a
    # plain load_config here silently dropped them, so native-family campaign runs kept their own
    # target). On a resume of a run without --config, run_dir/config.yaml already holds the merged raw.
    kw = {}
    if getattr(args, "brief", None) is not None:
        kw["brief"] = Path(args.brief)
    if getattr(args, "cma_seed", None) is not None:
        kw["cma_seed"] = int(args.cma_seed)
    if getattr(args, "backend", None) is not None:
        kw["backend"] = args.backend
    cfg = load_config(cfg_path, **kw)
    why = _verify_only_refusal(cfg.brief, "search")
    if why:
        if not args.resume:
            run_dir.rmdir()                      # created above, still empty
        print(why)
        return 2
    try:
        _apply_restarts_cli(cfg, getattr(args, "restarts_mode", None),
                            getattr(args, "restarts_max", None))
    except Exception as exc:  # ConfigError / ValueError — refuse before any GPU work
        print(f"search FAILED: {exc}")
        return 2
    if args.resume:
        # A resume replays the CMA sequence from search.ndjson and the solve cache; if the config
        # (weights, bounds, target, ...) changed, the replayed work and the stored rows no longer
        # share one J. Refuse unless the caller explicitly accepts the mix.
        prev = rundir.read_json(run_dir / "run.json", {}) or {}
        stored_sha = prev.get("config_sha")
        current_sha = rundir.config_sha(cfg.raw)
        if stored_sha and stored_sha != current_sha:
            if not args.allow_config_change:
                print(f"search REFUSED: --resume {run_dir} was created with config_sha {stored_sha}, "
                      f"but the current config ({cfg_path}) has config_sha {current_sha}. Resuming a "
                      "run with a DIFFERENT config mixes old-J and new-J rows (the CMA replay and "
                      "the cache would be invalid). Pass --allow-config-change to override.")
                return 1
            print(f"search WARNING: resuming {run_dir} with a CHANGED config "
                  f"(stored config_sha {stored_sha} != current config_sha {current_sha}) because "
                  "--allow-config-change was given; old and new rows may not be comparable.")
    worker.install_handlers()
    try:
        backend = _backend(cfg)
    except BackendUnavailableError as exc:
        print(f"search FAILED: {exc}")
        return 1
    store = DatasetStore(d["dataset"])
    worker.warm(backend)
    budget = args.budget if args.budget is not None else cfg.search.budget
    print(f"search: {cfg.name} mode {args.mode}, budget {budget} new evaluations, "
          f"{len(cfg.bounds_raw)} bounded keys, output {run_dir}")
    try:
        best = cma.search(cfg, run_dir, args.mode, backend=backend, budget=budget, store=store,
                          cache_dir=d["cache"], trace_fraction=args.trace_fraction,
                          command=_command_string(argv), config_path=cfg_path,
                          max_evals=getattr(args, "max_evals", None))
    except KeyboardInterrupt:
        print(f"search INTERRUPTED: partial results are in {run_dir} (resume with --resume)")
        return 1
    except Exception as exc:  # noqa: BLE001 - MeshConsistencyError and friends: stop, say why
        print(f"search ABORTED: {type(exc).__name__}: {exc} (partial results in {run_dir})")
        return 1
    run = rundir.read_json(run_dir / "run.json", {}) or {}
    st = run.get("stats", {})
    seed = (run.get("seed") or {}).get("objective")
    def g(v, spec=".1f"):
        return "n/a" if v is None else format(v, spec)
    ph = st.get("projected_hours") or {}
    print(f"  evaluations {st.get('evaluations')} ({st.get('non_cached')} new, {st.get('cache_hits')} cached), "
          f"failures {st.get('failures_by_reason')}, GPU {g(st.get('total_gpu_seconds'))} s, "
          f"{g(st.get('mean_seconds_per_candidate'))} s/candidate, "
          f"{g(st.get('candidates_per_hour'), '.0f')}/h, projected 1,000 = {g(ph.get('1000'))} h, "
          f"10,000 = {g(ph.get('10000'))} h")
    if seed is not None and best is not None:
        verdict = ("improved on the seed" if best.objective < seed - 1e-12 else "did NOT improve on the seed")
        print(f"  seed J={seed:.6g}  best J={best.objective:.6g} ({verdict}); stop: {run.get('stop_reason')}")
    rows = read_ndjson(run_dir / "search.ndjson")
    print(f"search OK: {len(rows)} rows in {run_dir / 'search.ndjson'}; best in {run_dir / 'best.json'}; "
          f"report with: hornlab-search report {run_dir}")
    return 0


# ---------------------------------------------------------------------- verify


def _cmd_verify(args, argv) -> int:
    from hornlab_search.search.gpulock import GpuBusyError, gpu_lock
    d = _dirs(args)
    try:
        with gpu_lock(_command_string(argv), runs_root=d["runs"]):
            return _verify_body(args, argv, d)
    except GpuBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 3


def _verify_body(args, argv, d) -> int:
    from hornlab_search.config import load_config
    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.search.evaluate import evaluate, make_context, read_ndjson
    from hornlab_search.solve import worker
    from hornlab_search.types import BackendUnavailableError, Design
    run_dir = Path(args.run)
    rows = read_ndjson(run_dir / "search.ndjson")
    if not (run_dir / "config.yaml").exists() or not rows:
        print(f"verify FAILED: {run_dir} has no config.yaml / search.ndjson")
        return 1
    # --brief was parsed but never applied (found 2026-10-23, same class as the 2026-10-22 search
    # bug): a 12 kHz verify (NEXT_DEV_PRIORITIES P2) would have re-solved at 5.5 kHz.
    brief = getattr(args, "brief", None)
    cfg = load_config(run_dir / "config.yaml", brief=Path(brief) if brief else None,
                      backend=getattr(args, "backend", None))
    d = _dirs(args)
    seen, top = set(), []
    for r in sorted((r for r in rows if r.get("ok")), key=lambda r: r["objective"]):
        if r["design_hash"] not in seen:
            seen.add(r["design_hash"])
            top.append(r)
    top = top[: args.top]
    if not top:
        print("verify FAILED: no successful evaluation to verify")
        return 1
    worker.install_handlers()
    try:
        backend = _backend(cfg)
    except BackendUnavailableError as exc:
        print(f"verify FAILED: {exc}")
        return 1
    store = DatasetStore(d["dataset"])
    worker.warm(backend)
    if brief:
        # Another brief = another frequency grid / target: its own run directory (listed by the
        # GUI like any run), never mixed into the source run's verify/ rows.
        from hornlab_search.search import rundir
        from hornlab_search.search.evaluate import collect_lib_shas
        vdir = rundir.new_run_dir(d["runs"], "verify")
        rundir.write_config_snapshot(vdir, cfg)
        rundir.write_json_atomic(vdir / "run.json", {
            "run_id": vdir.name, "config_name": cfg.name, "family": cfg.family, "mode": "verify",
            "config": cfg.raw, "config_sha": rundir.config_sha(cfg.raw), "backend": cfg.solve.backend,
            "lib_shas": collect_lib_shas(), "toolchain": rundir.toolchain_snapshot(),
            "runtime": rundir.runtime_provenance(), "command": _command_string(argv),
            "verify_of": {"run": str(run_dir.resolve()), "top": len(top), "brief": str(brief)},
            "status": "running", "started_utc": rundir.utc_now(), "dataset_dir": str(store.root)})
    else:
        vdir = run_dir / "verify"
        vdir.mkdir(exist_ok=True)
    ctx = make_context(cfg, store, cache_dir=d["cache"], trace_fraction=args.trace_fraction,
                       ndjson=vdir / "search.ndjson")
    space = DesignSpace.from_config(cfg)
    if brief:
        print(f"verify: re-solving the top {len(top)} designs of {run_dir.name} under brief {brief} "
              f"(band {cfg.target_raw.get('band_lo_hz')}-{cfg.target_raw.get('band_hi_hz')} Hz); "
              f"J is NOT comparable with the source run's J (different band and grid)")
    else:
        print("verify: re-solving the top designs at verify fidelity "
              "(note: with the current band/caps the verify mesh equals the screen mesh; only the "
              "frequency count and balloon size differ)")
    print("  design        screen J     verify J    DI source")
    bad, best, best_no = 0, None, None
    for i, r in enumerate(top):
        ev = evaluate(Design(r["family"], dict(r["params"])), space, cfg, "verify", vdir, store, backend,
                      ctx=ctx)
        bad += bool(ev.error)
        if not ev.error and (best is None or ev.objective < best.objective):
            best, best_no = ev, i
        print(f"  {r['design_hash']}  {r['objective']:10.5f}  "
              f"{('FAILED: ' + ev.error.splitlines()[0][:60]) if ev.error else format(ev.objective, '10.5f')}"
              f"  {ev.metrics.di_source if ev.metrics else 'n/a'}")
    if brief:
        if best is not None:
            rundir.write_best(vdir, best, "verify", best_no)
        rundir.update_run_json(vdir, status="finished", finished_utc=rundir.utc_now(),
                               stop_reason=f"verify: {len(top)} designs, {bad} failed",
                               best=None if best is None else {"design_hash": best.design_hash,
                                                              "objective": best.objective,
                                                              "eval_no": best_no})
    print(f"verify {'FAILED' if bad else 'OK'}: {len(top)} designs, {bad} failed; output {vdir}")
    return 1 if bad else 0


# ---------------------------------------------------------------------- report


def _cmd_report(args) -> int:
    from hornlab_search.report.html import build_report
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"report FAILED: {run_dir} is not a directory")
        return 1
    out = build_report(run_dir, args.out, top_n=args.top)
    print(f"report OK: {out} ({Path(out).stat().st_size / 1e6:.2f} MB)")
    return 0


def _resolve_run_dir(raw: str, runs_root: Path) -> Path | None:
    """Accept an absolute/relative run directory or a bare run id under ``runs_root``."""
    p = Path(raw)
    if p.is_dir() and (p / "run.json").is_file():
        return p.resolve()
    cand = runs_root / raw
    if cand.is_dir() and (cand / "run.json").is_file():
        return cand.resolve()
    return None


def _cmd_pin_plan(args) -> int:
    """Recommend CMA knobs to pin from a finished run's ``cma_covariance`` (+ Spearman)."""
    import yaml

    from hornlab_search.gui.data import sensitivity
    from hornlab_search.search.evaluate import read_ndjson
    from hornlab_search.search.pin_from_cma import (
        apply_pins_to_config, format_pin_plan_md, recommend_pins,
    )
    from hornlab_search.search.rundir import read_json, write_json_atomic

    d = _dirs(args)
    run_dir = _resolve_run_dir(args.run, d["runs"])
    if run_dir is None:
        print(f"pin-plan FAILED: run not found: {args.run!r}")
        return 1
    run_json = read_json(run_dir / "run.json", {}) or {}
    cov = run_json.get("cma_covariance")
    if not isinstance(cov, dict):
        print(f"pin-plan FAILED: {run_dir}/run.json has no cma_covariance "
              "(re-run search after the covariance dump landed)")
        return 1
    best = read_json(run_dir / "best.json", {}) or {}
    best_params = best.get("params") if isinstance(best.get("params"), dict) else {}
    cfg_path = run_dir / "config.yaml"
    cfg = {}
    if cfg_path.is_file():
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    bounds = cfg.get("bounds") if isinstance(cfg.get("bounds"), dict) else {}
    rows = read_ndjson(run_dir / "search.ndjson") if (run_dir / "search.ndjson").is_file() else []
    sens = sensitivity(rows, bounds) if rows and bounds else []
    plan = recommend_pins(cov, best_params=best_params, sens=sens, bounds=bounds)
    plan["run_dir"] = str(run_dir)
    plan["run_id"] = run_dir.name
    write_json_atomic(run_dir / "pin_plan.json", plan)
    md = format_pin_plan_md(plan, run_id=run_dir.name)
    (run_dir / "PIN_PLAN.md").write_text(md, encoding="utf-8")
    n_pin = len(plan.get("pin") or [])
    print(f"pin-plan OK: {n_pin} pin / {len(plan.get('keep') or [])} keep → "
          f"{run_dir / 'pin_plan.json'} and {run_dir / 'PIN_PLAN.md'}")
    if args.write_config:
        out_cfg = Path(args.write_config)
        if not cfg:
            print("pin-plan FAILED: no config.yaml in the run; cannot --write-config")
            return 1
        patched = apply_pins_to_config(cfg, plan)
        out_cfg.parent.mkdir(parents=True, exist_ok=True)
        out_cfg.write_text(yaml.safe_dump(patched, sort_keys=False), encoding="utf-8")
        print(f"pin-plan wrote config: {out_cfg}")
    return 0


# ---------------------------------------------------------------------- dataset


def _cmd_dataset(args) -> int:
    from hornlab_search.dataset import store as dstore
    d = _dirs(args)
    if not d["dataset"].exists():
        print(f"dataset FAILED: {d['dataset']} does not exist yet (run `search` first)")
        return 1
    store = dstore.DatasetStore(d["dataset"])
    s = store.stats()
    code = 0
    if args.action == "stats":
        print(dstore.stats_report(store))
        line = f"dataset stats OK: {s['n']} records ({s['n_ok']} ok, {s['n_failed']} failed) in {d['dataset']}"
    elif args.action == "verify":
        rep = dstore.verify_store(store)
        for b in rep["bad"][:20]:
            print(f"  BAD shard {b['shard']} row {b['row']} {b['design_hash']}: {b['problem']}")
        for b in rep["bad_arrays"][:20]:
            print(f"  BAD-ARRAY shard {b['shard']} row {b['row']} {b['design_hash']}: {b['problem']}")
        code = 1 if (rep["n_bad"] or rep["n_bad_arrays"]) else 0
        line = (f"dataset verify {'FAILED' if code else 'OK'}: {rep['n']} records re-read, "
                f"{rep['n_bad']} bad, {rep['n_bad_arrays']} bad arrays")
    else:
        out = Path(args.out)
        kw = {}
        if args.family:
            kw["family"] = args.family
        if args.lib_sha:
            kw["lib_sha"] = args.lib_sha
        res = dstore.export_training_npz(store, out, **kw)
        n = int(res["X"].shape[0])
        line = f"dataset export OK: {n} records x {res['X'].shape[1]} design keys -> {out}"
        if n == 0:
            line = f"dataset export FAILED: nothing matched the filters (output {out})"
            code = 1
    if s["family_warning"] and args.action != "stats":      # stats_report already prints it
        print("WARNING: " + s["family_warning"])
    print(line)
    return code


# ---------------------------------------------------------------------- surrogate (phase 2, stage A)


def _cmd_surrogate(args) -> int:
    try:
        import torch  # noqa: F401
    except ImportError:
        print('surrogate FAILED: torch is not installed (pip install -e ".[surrogate]")')
        return 1
    from hornlab_search.config import load_config, mode_freqs
    from hornlab_search.dataset import store as dstore
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.objective.scalar import resolve_weights
    from hornlab_search.surrogate import gates as gates_mod
    from hornlab_search.surrogate import ismo
    from hornlab_search.surrogate.predict import Surrogate
    from hornlab_search.surrogate.train import train_surrogate
    from hornlab_search.targets.spec import Target
    from hornlab_search.surrogate.features import UnsupportedConfigError, require_surrogate_config
    cfg = load_config(args.config)
    try:
        require_surrogate_config(cfg)
    except UnsupportedConfigError as exc:
        print(f"surrogate {args.action} FAILED: {exc}")
        return 1
    space, target = DesignSpace.from_config(cfg), Target.from_dict(cfg.target_raw)
    weights = resolve_weights(cfg.weights)
    out = Path(args.out)
    if args.action == "round":
        from hornlab_search.search.gpulock import GpuBusyError, gpu_lock
        from hornlab_search.surrogate.round import run_round
        if not args.out_dir:
            print("surrogate round FAILED: --out-dir is required")
            return 1
        props = Path(args.proposals)
        if not props.is_file():
            print(f"surrogate round FAILED: --proposals {props} does not exist")
            return 1
        d = _dirs(args)
        store = dstore.DatasetStore(d["dataset"]) if d["dataset"].exists() else None
        try:
            with gpu_lock(f"hornlab-search surrogate round", runs_root=d["runs"]):
                result = run_round(props, cfg, mode=args.mode, out_dir=Path(args.out_dir),
                                   bundle_path=out, store=store, cache_dir=d["cache"],
                                   random_run=args.random_run, trace_fraction=args.trace_fraction)
        except GpuBusyError as exc:
            print(str(exc), file=sys.stderr)
            return 3
        except ValueError as exc:
            print(f"surrogate round FAILED: {exc}")
            return 1
        print(f"  round report working={result['report']['working']}; "
              f"ismo_round1.json under {args.out_dir}")
        return 0
    if args.action == "train":
        d = _dirs(args)
        if not d["dataset"].exists():
            print(f"surrogate train FAILED: {d['dataset']} does not exist")
            return 1
        arrays = dstore.to_training_arrays(dstore.DatasetStore(d["dataset"]), family=cfg.family,
                                           keys=space.keys(), ok_only=False, lib_sha=args.lib_sha)
        ameta = arrays.get("meta", {})
        skipped = int(ameta.get("skipped_grid_mismatch", 0) or 0)
        print(f"  training arrays: considered {ameta.get('n_considered')}, selected "
              f"{ameta.get('n_selected')}, skipped_grid_mismatch {skipped}, "
              f"skipped_bad_arrays {ameta.get('skipped_bad_arrays')}, "
              f"skipped_keys {ameta.get('skipped_keys')}")
        if skipped > 0:
            print(f"  WARNING: {skipped} record(s) were dropped for a DIFFERENT frequency grid "
                  "than the training grid; concatenating them would train on a lie "
                  "(see to_training_arrays).")
        n = int(arrays["X"].shape[0])
        if n < 50:
            print(f"surrogate train FAILED: only {n} {cfg.family} records (need data first)")
            return 1
        try:
            _, rep = train_surrogate(arrays, space, target, weights, ensemble=args.ensemble,
                                     epochs=args.epochs, out_path=out, lib_sha=args.lib_sha)
        except ValueError as e:          # DI provenance / unresolved keys: refuse, never guess
            print(f"surrogate train FAILED: {e}")
            return 1
        for k, g in rep["gates"].items():
            print(f"  {'PASS' if g['pass'] else 'FAIL'}  {k:18s} {g['value']!s:>10}  need {g['threshold']}")
        for w in rep["warnings"]:
            print("  WARNING: " + w)
        if rep["n_duplicates_dropped"]:
            print(f"  dropped {rep['n_duplicates_dropped']} duplicate design(s) before the "
                  "cluster holdout split")
        print(f"  objective delta (recomputed vs stored): max {rep['objective_delta_max']:.4g}, "
              f"mean {rep['objective_delta_mean']:.4g}")
        if rep.get("kept_existing_bundle"):
            print(f"  KEPT the existing passing bundle at {out}; this run FAILED its gates and was "
                  "NOT written over it.")
        if rep["pass"]:
            headline = "GATES PASSED"
        else:
            failing = [k for k, g in rep["gates"].items() if not g["pass"]]
            if failing:
                headline = "GATES FAILED: " + ", ".join(failing)
            else:
                headline = (f"GATES REFUSED (indicative only): all {len(rep['gates'])} measured "
                            f"gates pass; held-out {rep['n_heldout']} < {gates_mod.MIN_HELDOUT} "
                            "formal floor")
        print(f"surrogate train {headline}: {n} records, {rep['n_heldout']} held out -> {out}")
        return 0 if rep["pass"] else 1
    # -- propose: the bundle must match the config it is proposed with, and must carry a verdict.
    sur = Surrogate.load(out)
    mismatch = sur.config_mismatch(space, freqs_hz=mode_freqs(args.mode, cfg))
    if mismatch is not None:
        print(f"surrogate propose REFUSED: {out} does not match --config: {mismatch}")
        return 1
    gr = sur.meta.get("gate_report")
    if not args.allow_unvalidated:
        if gr is None:
            print(f"surrogate propose REFUSED: {out} has no gate verdict in its meta; retrain with "
                  "'surrogate train' (or pass --allow-unvalidated to propose anyway).")
            return 1
        if not gr.get("gates_passed"):
            print(f"surrogate propose REFUSED: {out} did NOT pass its acceptance gates "
                  "(gates_passed=False). Pass --allow-unvalidated to propose anyway; those "
                  "predictions are NOT validated.")
            return 1
    elif gr is not None and not gr.get("gates_passed"):
        print(f"  WARNING: {out} did not pass its gates; proposing anyway (--allow-unvalidated)")
    props = ismo.propose(sur, space, target, weights, n_top=args.n_top, n_var=args.n_var)
    if not props:
        print("surrogate propose FAILED: 0 designs (everything predicted invalid?)")
        return 1
    dest = Path(args.proposals)
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps([{"family": p["design"].family, "params": p["design"].params,
                        "kind": p["kind"], "pred_J": p["pred_J"], "std": p["std"]}
                       for p in props], indent=1, default=float)
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, dest)
    print(f"surrogate propose OK: {len(props)} designs -> {dest}. Solve each with real BEM "
          "(a surrogate prediction is not a result) and run ismo.round_report on the outcome.")
    return 0


# ---------------------------------------------------------------------- compare (two solved runs)

_COMPARE_KEYS = (("bw_h_deg", "deg"), ("bw_v_deg", "deg"), ("di_db", "dB"),
                 ("on_axis_db", "dB"), ("ripple_h_db", "dB"), ("ripple_v_db", "dB"))


def _first_ok_metrics(path: Path):
    from hornlab_search.search.evaluate import metrics_from_json, read_ndjson
    f = path / "search.ndjson" if path.is_dir() else path
    for row in read_ndjson(f):
        if row.get("metrics"):
            return row, metrics_from_json(row["metrics"])
    return None, None


def compare_metrics(a, b) -> dict:
    """Per-metric max and mean |a - b| on a shared frequency grid (curves of two MetricSets)."""
    import numpy as np
    fa, fb = np.asarray(a.freqs_hz, float), np.asarray(b.freqs_hz, float)
    if fa.shape != fb.shape or not np.allclose(fa, fb, rtol=1e-6, atol=1e-3):
        raise ValueError(f"frequency grids differ: {fa.tolist()} vs {fb.tolist()}")
    if fa.size == 0:
        raise ValueError("both runs have an empty frequency list; nothing to compare")
    out = {}
    for k, unit in _COMPARE_KEYS:
        d = np.abs(np.asarray(getattr(a, k), float) - np.asarray(getattr(b, k), float))
        d = d[np.isfinite(d)]
        out[k] = {"unit": unit, "max": float(d.max()) if d.size else float("nan"),
                  "mean": float(d.mean()) if d.size else float("nan"), "n": int(d.size)}
    return out


def _cmd_compare(args) -> int:
    """Report how far two solved runs disagree, e.g. the same design meshed as a quarter and as
    the full domain. Report only: it does not judge. Reference (CP-7d, OSSE seed, <= 3 kHz):
    full vs quarter agreed to 0.023 dB."""
    rows = []
    for p in (Path(args.run_a), Path(args.run_b)):
        row, m = _first_ok_metrics(p)
        if m is None:
            print(f"compare FAILED: no solved row with metrics in {p}")
            return 1
        rows.append((p, row, m))
    (pa, ra, ma), (pb, rb, mb) = rows
    if ma.di_source != "balloon" or mb.di_source != "balloon":
        print(f"compare FAILED: DI must come from the balloon in both runs "
              f"({ma.di_source!r} / {mb.di_source!r})")
        return 1
    try:
        res = compare_metrics(ma, mb)
    except ValueError as e:
        print(f"compare FAILED: {e}")
        return 1
    qa = ra.get("quadrants") or (ra.get("mesh") or {}).get("quadrants")
    qb = rb.get("quadrants") or (rb.get("mesh") or {}).get("quadrants")
    print(f"compare A={pa} (design {ra.get('design_hash')}, quadrants {qa!r})")
    print(f"        B={pb} (design {rb.get('design_hash')}, quadrants {qb!r})")
    if ra.get("design_hash") != rb.get("design_hash"):
        print("  NOTE: the two rows are different designs")
    print(f"  {len(ma.freqs_hz)} frequencies {ma.freqs_hz[0]:g}..{ma.freqs_hz[-1]:g} Hz")
    for k, r in res.items():
        print(f"  {k:12s} max |diff| {r['max']:.4g} {r['unit']:3s}  mean {r['mean']:.4g}  (n={r['n']})")
    print("compare OK (report only; reference: OSSE full vs quarter 0.023 dB, CP-7d)")
    return 0


# ---------------------------------------------------------------------- export-step


def _cmd_export_step(args) -> int:
    """Write closed STEP solids (millimetres, full model, throat open) for CAD and 3D printing:
    the top N distinct successful designs of a run, or the seed of a config. No solver."""
    from hornlab_search.config import load_config, mesh_spec
    from hornlab_search.mesh.build import export_step
    from hornlab_search.search.evaluate import read_ndjson
    from hornlab_search.types import Design
    if bool(args.run) == bool(args.config):
        print("export-step FAILED: give exactly one of --run or --config")
        return 1
    if args.run:
        run_dir = Path(args.run)
        rows = read_ndjson(run_dir / "search.ndjson") if (run_dir / "search.ndjson").exists() else []
        if not (run_dir / "config.yaml").exists() or not rows:
            print(f"export-step FAILED: {run_dir} has no config.yaml / search.ndjson")
            return 1
        cfg = load_config(run_dir / "config.yaml")
        seen, picks = set(), []
        for r in sorted((r for r in rows if r.get("ok")), key=lambda r: r["objective"]):
            if r["design_hash"] not in seen:
                seen.add(r["design_hash"])
                picks.append((f"rank{len(picks) + 1}", r["design_hash"], r["family"], r["params"],
                              r["objective"]))
        picks = picks[: args.top]
        out_dir = Path(args.out) if args.out else run_dir / "step"
    else:
        cfg = load_config(args.config)
        d = Design(cfg.family, dict(cfg.seed_params))
        picks = [("seed", d.hash(), cfg.family, dict(cfg.seed_params), None)]
        out_dir = Path(args.out) if args.out else Path("step") / cfg.name
    if not picks:
        print("export-step FAILED: no successful design to export")
        return 1
    ms = mesh_spec(args.mode, cfg)
    bad = 0
    for tag, h, fam, params, J in picks:
        out = out_dir / f"{cfg.name}_{tag}_{h}.step"
        try:
            path, info = export_step(Design(fam, dict(params)), ms, cfg, out)
        except Exception as exc:  # noqa: BLE001 - report per design, keep going
            bad += 1
            print(f"  {tag:6s} {h}  FAILED: {type(exc).__name__}: {str(exc).splitlines()[0][:80]}")
            continue
        jtxt = "" if J is None else f"J {J:.4f}  "
        print(f"  {tag:6s} {h}  {jtxt}volume {getattr(info, 'volume_mm3', float('nan')) / 1000:.1f} cm3  {path}")
    print(f"export-step {'FAILED' if bad else 'OK'}: {len(picks) - bad} of {len(picks)} written to {out_dir}")
    return 1 if bad else 0


# ---------------------------------------------------------------------- families


def _cmd_families(args) -> int:
    from hornlab_search.search.campaign import (
        load_brief, load_catalog, is_compatible, _count_keys,
    )
    catalog_path = EXAMPLES / "catalog.yaml"
    if not catalog_path.exists():
        print(f"families FAILED: {catalog_path} not found")
        return 1
    try:
        catalog = load_catalog(catalog_path)
    except Exception as exc:  # noqa: BLE001
        print(f"families FAILED: {exc}")
        return 1

    brief = None
    brief_path = getattr(args, "brief", None)
    if brief_path:
        try:
            brief = load_brief(brief_path)
        except Exception as exc:  # noqa: BLE001
            print(f"families FAILED: could not load brief {brief_path}: {exc}")
            return 1

    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace

    print(f"{'Name':<22} {'Group':<10} {'Sym':<14} {'Keys':>4}  {'Description'}")
    print("-" * 90)
    for entry in catalog:
        name = entry["name"]
        group = entry.get("group", "")
        sym = entry.get("symmetry", "")
        desc = entry.get("description", "")

        # Count searchable keys
        try:
            cfg_path = EXAMPLES / entry["config"]
            cfg = load_config(cfg_path)
            space = DesignSpace.from_config(cfg)
            n_keys = len(space.keys())
            keys_str = str(n_keys)
        except Exception as exc:  # noqa: BLE001
            keys_str = "?"
            desc = f"[load error: {exc!s:.40}] {desc}"

        compat_note = ""
        if brief is not None:
            ok, reason = is_compatible(entry, brief)
            if not ok:
                compat_note = f"  [INCOMPAT: {reason}]"

        print(f"  {name:<20} {group:<10} {sym:<14} {keys_str:>4}  {desc}{compat_note}")

    print(f"\nfamilies OK: {len(catalog)} entries in {catalog_path}")
    return 0


# ---------------------------------------------------------------------- campaign


def _cmd_campaign(args) -> int:
    from hornlab_search.search.campaign import (
        run_campaign, print_compact_table,
    )
    from hornlab_search.search.gpulock import GpuBusyError, gpu_lock
    brief_path = Path(args.brief)
    if not brief_path.exists():
        print(f"campaign FAILED: --brief {brief_path} not found")
        return 1
    if args.budget is not None and args.budget < 1:
        print(f"campaign FAILED: --budget must be a positive number of evaluations, got {args.budget}")
        return 2
    if args.seeds is not None and args.seeds < 1:
        print(f"campaign FAILED: --seeds must be at least 1, got {args.seeds}")
        return 2
    runs_dir = Path(args.runs_dir or REPO / "runs")
    if args.tier != "dry-run":
        from hornlab_search.config import ConfigError, load_brief
        try:
            why = _verify_only_refusal(load_brief(brief_path), "campaign")
        except ConfigError as exc:
            print(f"campaign FAILED: {exc}")
            return 1
        if why:
            print(why)
            return 2
    # dry-run tier does no GPU work; all other tiers need the lock
    if args.tier != "dry-run":
        try:
            # Campaign spawns subprocesses that each acquire the lock via env-var reentrancy
            cmd = f"hornlab-search campaign --tier {args.tier} --brief {args.brief} --families {args.families}"
            lock_ctx = gpu_lock(cmd, runs_root=runs_dir)
        except Exception:  # noqa: BLE001
            lock_ctx = None
        if lock_ctx is not None:
            try:
                with lock_ctx:
                    return _campaign_body(args, runs_dir, run_campaign, print_compact_table)
            except GpuBusyError as exc:
                print(str(exc), file=sys.stderr)
                return 3
        return _campaign_body(args, runs_dir, run_campaign, print_compact_table)
    return _campaign_body(args, runs_dir, run_campaign, print_compact_table)


def _campaign_body(args, runs_dir, run_campaign, print_compact_table) -> int:
    try:
        results = run_campaign(
            brief_path=Path(args.brief),
            families_spec=args.families,
            tier=args.tier,
            runs_dir=runs_dir,
            n_seeds=args.seeds,
            budget_override=args.budget,
        )
    except KeyboardInterrupt as exc:
        print(f"campaign INTERRUPTED: partial campaign.json + leaderboard.md in {exc}; "
              f"the interrupted search can be continued with search --resume")
        return 130
    except ValueError as exc:
        print(f"campaign FAILED: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        log.debug("campaign unhandled", exc_info=True)
        print(f"campaign FAILED: {type(exc).__name__}: {exc}")
        return 1
    print_compact_table(results)
    campaign_dir = results["campaign_dir"]
    print(f"campaign OK: campaign.json + leaderboard.md in {campaign_dir}")
    return 0


# ---------------------------------------------------------------------- parser / main


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="count", default=0, help="-v INFO, -vv DEBUG")
    common.add_argument("--runs-dir", help="default <repo>/runs")
    common.add_argument("--cache-dir", help="default <repo>/cache")
    common.add_argument("--dataset-dir", help="default <repo>/dataset")
    common.add_argument("--backend", choices=("beat_cuda", "beat_metal", "beat_cpu", "bempp_cpu"),
                        help="override solve.backend in the config")
    common.add_argument("--trace-fraction", type=float, default=0.05,
                        help="fraction of designs that also record boundary traces (default 0.05)")
    p = argparse.ArgumentParser(prog="hornlab-search", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("doctor", parents=[common])
    sub.add_parser("version", parents=[common])
    s = sub.add_parser("selftest", parents=[common], help="compare against physics")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--analytic", action="store_true", help="pulsating sphere vs its exact solution")
    g.add_argument("--crosscheck", action="store_true", help="beat vs bempp on one mesh")
    s.add_argument("--config", help="default examples/osse_baseline.yaml")
    s.add_argument("--tol-db", type=float, default=0.5)
    s.add_argument("--subdivisions", type=int, default=3)
    s.add_argument("--convergence", default="3,4,5", help="icosphere levels for the convergence check")
    s.add_argument("--no-convergence", action="store_true")
    s.add_argument("--n-freqs", type=int, default=5)
    r = sub.add_parser("run", parents=[common], help="evaluate the seed design once")
    r.add_argument("--config", required=True)
    r.add_argument("--mode", choices=("screen", "verify", "final"), default="screen")
    r.add_argument("--dry-run", action="store_true", help="mesh and estimate; launch no solver")
    r.add_argument("--brief", metavar="PATH",
                   help="brief YAML; overrides config target/weights and is folded into config_sha")
    r.add_argument("--cma-seed", type=int, metavar="INT",
                   help="override search.seed in the config")
    q = sub.add_parser("search", parents=[common], help="CMA-ES from the seed")
    q.add_argument("--config")
    q.add_argument("--budget", type=int, help="cap on NON-CACHED evaluations (the seed counts)")
    q.add_argument("--max-evals", type=int, dest="max_evals",
                   help="cap on ALL evaluations incl. cache hits (fair comparisons; campaign sets it)")
    q.add_argument("--mode", choices=("screen", "verify", "final"), default="screen")
    q.add_argument("--resume", metavar="DIR")
    q.add_argument("--allow-config-change", action="store_true",
                   help="resume even if the run's config_sha differs from the current config "
                        "(mixes old-J and new-J rows; off by default)")
    q.add_argument("--brief", metavar="PATH",
                   help="brief YAML; overrides config target/weights and is folded into config_sha")
    q.add_argument("--cma-seed", type=int, metavar="INT",
                   help="override search.seed in the config")
    q.add_argument("--restarts-mode", choices=("ipop", "bipop", "off"),
                   help="override search.restarts.mode (off = single CMA-ES; "
                        "absent = leave the config's search.restarts alone)")
    q.add_argument("--restarts-max", type=int, metavar="N",
                   help="override search.restarts.max (0..64); required with "
                        "--restarts-mode ipop|bipop unless the config already has max "
                        "(default 2 when the config has no restarts block)")
    v = sub.add_parser("verify", parents=[common], help="re-solve a run's top designs at verify fidelity")
    v.add_argument("--run", required=True)
    v.add_argument("--top", type=int, default=5)
    v.add_argument("--brief", metavar="PATH",
                   help="brief YAML; overrides config target/weights")
    v.add_argument("--cma-seed", type=int, metavar="INT",
                   help="override search.seed (informational; verify does not run CMA)")
    rp = sub.add_parser("report", parents=[common], help="HTML report of a run directory")
    rp.add_argument("run_dir")
    rp.add_argument("--out")
    rp.add_argument("--top", type=int, default=5)
    pp = sub.add_parser("pin-plan", parents=[common],
                        help="recommend knobs to pin from a run's CMA covariance (+ Spearman)")
    pp.add_argument("--run", required=True, metavar="DIR|ID",
                    help="run directory or id under --runs-dir")
    pp.add_argument("--write-config", metavar="PATH",
                    help="optional: write a patched YAML with recommended pins applied")
    ds = sub.add_parser("dataset", parents=[common])
    ds.add_argument("action", choices=("stats", "verify", "export"))
    ds.add_argument("--out", default="train.npz")
    ds.add_argument("--family")
    ds.add_argument("--lib-sha")
    cp = sub.add_parser("compare", parents=[common],
                        help="report metric differences between two solved runs")
    cp.add_argument("run_a", help="run directory (or its search.ndjson)")
    cp.add_argument("run_b", help="run directory (or its search.ndjson)")
    xs = sub.add_parser("export-step", parents=[common],
                        help="STEP solids (mm) of a run's top designs or a config's seed, for CAD / 3D printing")
    xg = xs.add_mutually_exclusive_group(required=True)
    xg.add_argument("--run", help="run directory: export its top distinct designs")
    xg.add_argument("--config", help="config: export its seed design")
    xs.add_argument("--top", type=int, default=3)
    xs.add_argument("--mode", choices=("screen", "verify", "final"), default="screen")
    xs.add_argument("--out", help="output directory (default <run>/step or step/<config name>)")
    sg = sub.add_parser("surrogate", parents=[common], help="phase 2 stage A: train / propose / round")
    sg.add_argument("action", choices=("train", "propose", "round"))
    sg.add_argument("--config", required=True)
    sg.add_argument("--out", default="surrogate.pt")
    sg.add_argument("--lib-sha")
    sg.add_argument("--ensemble", type=int, default=5)
    sg.add_argument("--epochs", type=int, default=300)
    sg.add_argument("--n-top", type=int, default=30)
    sg.add_argument("--n-var", type=int, default=10)
    sg.add_argument("--proposals", default="proposals.json")
    sg.add_argument("--out-dir", help="round: directory for the fresh round1/ run and ismo_round1.json")
    sg.add_argument("--random-run", help="round: search run dir whose early SOLVED evaluations are "
                                         "the random_true_J baseline (default: --out-dir if it "
                                         "holds a search.ndjson)")
    sg.add_argument("--mode", choices=("screen", "verify", "final"), default="screen",
                    help="frequency grid the config would solve on; propose checks it against the "
                         "bundle's frozen training grid")
    sg.add_argument("--allow-unvalidated", action="store_true",
                    help="propose even if the bundle failed (or lacks) its gate verdict")
    # ---------------------------------------------------------------------- families
    fam = sub.add_parser("families", parents=[common],
                         help="list catalog entries with key counts; mark brief-incompatible entries")
    fam.add_argument("--brief", metavar="PATH",
                     help="brief YAML; marks entries incompatible with this brief")
    # ---------------------------------------------------------------------- campaign
    cmp = sub.add_parser("campaign", parents=[common],
                         help="multi-family typology search campaign (TYPOLOGY_PLAN.md s7)")
    cmp.add_argument("--brief", required=True, metavar="PATH",
                     help="brief YAML that every family search is compared under")
    cmp.add_argument("--families", required=True, metavar="SPEC",
                     help="comma-separated list of names/groups or 'all'")
    cmp.add_argument("--tier", required=True, choices=("dry-run", "screen", "compare"),
                     help="dry-run: mesh only; screen: max(40,10k) budget 1 seed; "
                          "compare: max(150,25k) budget 2 seeds")
    cmp.add_argument("--seeds", type=int, metavar="N",
                     help="override the number of CMA seeds (default: 1 for screen, 2 for compare)")
    cmp.add_argument("--budget", type=int, metavar="N",
                     help="override the per-search budget for this campaign")
    # ---------------------------------------------------------------------- gpu-clean
    gc = sub.add_parser("gpu-clean", parents=[common],
                        help="kill stale Julia/BEAT processes and report VRAM usage")
    gc.add_argument("--force", action="store_true",
                    help="DANGEROUS: skip the GPU-lock check and kill Julia even if a search is running")
    gui = sub.add_parser("gui", parents=[common], help="local web GUI (127.0.0.1) over runs, briefs and jobs")
    gui.add_argument("--port", type=int, default=8765)
    gui.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    return p


def _ensure_utf8_stdio() -> None:
    """Windows consoles default to cp1252; human-facing output uses sigma/arrow/rho glyphs.

    Without this, `pin-plan` (and anything else printing the plan) raises UnicodeEncodeError on a
    plain Windows cmd/PowerShell. Streams without ``reconfigure`` (pytest's capsys) are skipped.
    """
    for stream in (sys.stdout, sys.stderr):
        enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "").replace("_", "")
        if enc.startswith("utf"):
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not argv:
        parser.print_usage(sys.stderr)
        return 2
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:                       # argparse: 0 for --help, 2 for a usage error
        return int(e.code or 0)
    _setup_logging(args.verbose)
    if args.cmd == "doctor":
        return _cmd_doctor()
    if args.cmd == "version":
        return _cmd_version()
    try:
        if args.cmd == "selftest":
            return _cmd_selftest(args)
        if args.cmd == "run":
            return _cmd_run(args, argv)
        if args.cmd == "search":
            return _cmd_search(args, argv)
        if args.cmd == "verify":
            return _cmd_verify(args, argv)
        if args.cmd == "report":
            return _cmd_report(args)
        if args.cmd == "pin-plan":
            return _cmd_pin_plan(args)
        if args.cmd == "dataset":
            return _cmd_dataset(args)
        if args.cmd == "surrogate":
            return _cmd_surrogate(args)
        if args.cmd == "compare":
            return _cmd_compare(args)
        if args.cmd == "export-step":
            return _cmd_export_step(args)
        if args.cmd == "families":
            return _cmd_families(args)
        if args.cmd == "campaign":
            return _cmd_campaign(args)
        if args.cmd == "gpu-clean":
            return _cmd_gpu_clean(args)
        if args.cmd == "gui":
            from hornlab_search.gui.server import serve
            return serve(REPO, args.port, not args.no_browser,
                         runs=Path(args.runs_dir) if args.runs_dir else None)
    except KeyboardInterrupt:
        print(f"{args.cmd} INTERRUPTED")
        return 1
    except Exception as exc:  # noqa: BLE001 - one clear final line, exit 1
        log.debug("unhandled", exc_info=True)
        print(f"{args.cmd} FAILED: {type(exc).__name__}: {exc}")
        return 1
    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
