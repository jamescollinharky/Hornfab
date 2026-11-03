#!/usr/bin/env bash
# Run one hornlab-search CUDA job on a cloud pod with local GPU hygiene.
#
# Usage (from repo root on the pod):
#   bash tools/cloud/run_job.sh -- run --config examples/typologies/solana_osse.yaml --mode screen
#   bash tools/cloud/run_job.sh -- selftest --analytic
#
# Forces --backend beat_cuda unless already present in argv.
# Writes runs/cloud_job_<utc>.json provenance next to the usual run dir.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

WORKSPACE="${HORNLAB_CLOUD_WORKSPACE:-}"
if [[ -z "$WORKSPACE" ]]; then
  if [[ -d /workspace ]]; then WORKSPACE=/workspace; else WORKSPACE="$REPO_ROOT"; fi
fi
export JULIA_DEPOT_PATH="${JULIA_DEPOT_PATH:-$WORKSPACE/julia-depot}"
export HORNLAB_BEAT_RUNTIME_DIR="${HORNLAB_BEAT_RUNTIME_DIR:-$WORKSPACE/hornlab-beat-runtime}"

# Match Julia/BLAS threads to the pod's *allotted* vCPUs. Bare `nproc` on RunPod
# often returns the whole host (64+), which oversubscribes a 12-vCPU allotment.
_cloud_vcpus() {
  local max period
  if [[ -r /sys/fs/cgroup/cpu.max ]]; then
    read -r max period < /sys/fs/cgroup/cpu.max || true
    if [[ -n "${max:-}" && "$max" != "max" && -n "${period:-}" && "$period" -gt 0 ]]; then
      echo $(( (max + period - 1) / period ))
      return
    fi
  fi
  if [[ -r /sys/fs/cgroup/cpu/cpu.cfs_quota_us && -r /sys/fs/cgroup/cpu/cpu.cfs_period_us ]]; then
    max=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us)
    period=$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us)
    if [[ "$max" -gt 0 && "$period" -gt 0 ]]; then
      echo $(( (max + period - 1) / period ))
      return
    fi
  fi
  if command -v nproc >/dev/null 2>&1; then nproc; else echo 8; fi
}
if [[ -z "${JULIA_NUM_THREADS:-}" ]]; then
  export JULIA_NUM_THREADS="$(_cloud_vcpus)"
fi
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-$JULIA_NUM_THREADS}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-$JULIA_NUM_THREADS}"
echo "run_job: JULIA_NUM_THREADS=$JULIA_NUM_THREADS OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"

VENV="${HORNLAB_VENV:-$REPO_ROOT/.venv}"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "run_job: missing $VENV/bin/python — run tools/cloud/bootstrap_linux.sh first" >&2
  exit 1
fi
PY="$VENV/bin/python"

DRY_RUN=0
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-preflight) DRY_RUN=1; shift ;;
    --) shift; ARGS=("$@"); break ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
if [[ ${#ARGS[@]} -eq 0 ]]; then
  echo "usage: $0 [--dry-preflight] -- <hornlab-search subcommand and args>" >&2
  exit 2
fi

HAS_BACKEND=0
for a in "${ARGS[@]}"; do
  if [[ "$a" == "--backend" ]]; then HAS_BACKEND=1; break; fi
done
if [[ $HAS_BACKEND -eq 0 ]]; then
  ARGS+=(--backend beat_cuda)
fi

UTC_START="$(date -u +%Y%m%dT%H%M%SZ)"
PROV_PATH="$REPO_ROOT/runs/cloud_job_${UTC_START}.json"
ARGV_JSON="$(mktemp)"
mkdir -p "$REPO_ROOT/runs"
printf '%s\0' "${ARGS[@]}" | "$PY" -c '
import json, sys
args = [a.decode() for a in sys.stdin.buffer.read().split(b"\0") if a]
json.dump(args, open(sys.argv[1], "w", encoding="utf-8"))
' "$ARGV_JSON"

gpu_name=""; vram_total=""; vram_used_before=""
if command -v nvidia-smi >/dev/null 2>&1; then
  IFS=, read -r gpu_name vram_total vram_used_before < <(
    nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader,nounits | head -1
  )
  gpu_name="$(echo "$gpu_name" | xargs)"
  vram_total="$(echo "$vram_total" | xargs)"
  vram_used_before="$(echo "$vram_used_before" | xargs)"
fi

echo "run_job: listing BEAT / julia hosts before clear"
pgrep -af 'hornlab_beat_bem|julia' || echo "(none)"

echo "run_job: clear_stale_hosts(force=True)"
"$PY" - <<'PY'
from hornlab_search.solve.worker import clear_stale_hosts, list_beat_hosts
killed = clear_stale_hosts(force=True)
print("killed roots:", killed)
left = list_beat_hosts()
print("hosts after clear:", [p.pid for p in left])
if left:
    raise SystemExit("run_job: BEAT hosts survived force clear")
PY

if pgrep -f 'hornlab_beat_bem/.*/solver\.jl --worker' >/dev/null 2>&1; then
  echo "run_job: SIGKILL leftover solver.jl --worker julia processes"
  pkill -9 -f 'hornlab_beat_bem/.*/solver\.jl --worker' || true
  sleep 1
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "run_job: VRAM after clear:"
  nvidia-smi --query-gpu=memory.used --format=csv
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo "run_job: dry-preflight only; would run:"
  echo "  $PY -m hornlab_search.cli ${ARGS[*]}"
  rm -f "$ARGV_JSON"
  exit 0
fi

GIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
START_EPOCH="$(date -u +%s)"
set +e
"$PY" -m hornlab_search.cli "${ARGS[@]}"
RC=$?
set -e
END_EPOCH="$(date -u +%s)"
UTC_END="$(date -u +%Y%m%dT%H%M%SZ)"

vram_used_after=""
if command -v nvidia-smi >/dev/null 2>&1; then
  vram_used_after="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | xargs)"
fi

echo "run_job: verified shutdown"
"$PY" - <<'PY'
from hornlab_search.solve.worker import shutdown, list_beat_hosts
shutdown(verify=True)
left = list_beat_hosts()
print("hosts after shutdown:", [p.pid for p in left])
if left:
    raise SystemExit("run_job: BEAT hosts survived shutdown(verify=True)")
PY
if pgrep -f 'hornlab_beat_bem/.*/solver\.jl --worker' >/dev/null 2>&1; then
  echo "run_job: WARNING leftover solver.jl after shutdown; force-killing" >&2
  pkill -9 -f 'hornlab_beat_bem/.*/solver\.jl --worker' || true
fi

export PROV_PATH UTC_START UTC_END START_EPOCH END_EPOCH RC GIT_SHA
export gpu_name vram_total vram_used_before vram_used_after ARGV_JSON
"$PY" - <<'PY'
import json, os
argv = json.load(open(os.environ["ARGV_JSON"], encoding="utf-8"))
def _int(s):
    s = (s or "").strip()
    return int(s) if s.isdigit() else None
doc = {
    "schema": "hornlab_cloud_job/v1",
    "started_utc": os.environ["UTC_START"],
    "ended_utc": os.environ["UTC_END"],
    "duration_s": int(os.environ["END_EPOCH"]) - int(os.environ["START_EPOCH"]),
    "returncode": int(os.environ["RC"]),
    "git_sha": os.environ.get("GIT_SHA"),
    "pod_id": os.environ.get("HORNLAB_CLOUD_POD_ID") or os.environ.get("RUNPOD_POD_ID"),
    "gpu_name": os.environ.get("gpu_name") or None,
    "vram_total_mib": _int(os.environ.get("vram_total")),
    "vram_used_before_mib": _int(os.environ.get("vram_used_before")),
    "vram_used_after_mib": _int(os.environ.get("vram_used_after")),
    "backend": "beat_cuda",
    "argv": argv,
    "julia_depot": os.environ.get("JULIA_DEPOT_PATH"),
    "beat_runtime_dir": os.environ.get("HORNLAB_BEAT_RUNTIME_DIR"),
}
path = os.environ["PROV_PATH"]
open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=2) + "\n")
print("wrote", path)
PY
rm -f "$ARGV_JSON"
exit "$RC"
